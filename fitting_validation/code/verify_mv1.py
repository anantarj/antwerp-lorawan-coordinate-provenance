#!/usr/bin/env python3
"""Post-execution verification of every MV1 output; no outcome/model selection.

Uses the frozen original source functions for objective and native-fit checks,
separate scalar/vector reconstruction for observations/centroids, and stored
immutable populations. Original full-source native replay is a verification run,
not another comparison arm or an independent scientific replication.
"""
from __future__ import annotations
import argparse,collections,json,math,random,sys
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pandas as pd
from preflight import digest,write_json,write_csv
from run_mv1 import load_inputs,verify_manifest,ARMS,GEOMETRY_ARMS,PROTOCOL_SHA
from source_reference import estimate_gateway_positions_rssfit,_robust_gateway_loss_and_a0


def read(p):return pd.read_csv(p,float_precision='round_trip')


def main():
    ap=argparse.ArgumentParser()
    for k in ['baseline','pr1','csv','protocol','results','out']:ap.add_argument('--'+k,required=True,type=Path)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    checks=[];metrics=[];source_receivers=[]
    def check(name,ok,**detail):
        checks.append({'check':name,'pass':bool(ok),**detail})
        if not ok:
            write_json(a.out/'FAILED_CHECKS.json',checks)
            raise AssertionError(name)
    total_calls=0;total_profiles=0;total_source_replayed=0;primary_compared=0;prediction_cells=0;centroid_cases=0
    for split in ['group80','space1000']:
        root=a.results/split
        if json.loads((root/'COMPLETE.json').read_text())['status']!='COMPLETE':raise ValueError('Incomplete split')
        check(split+' scientific-output manifest',not verify_manifest(root,'OUTPUT_MANIFEST.json')['failures'])
        d=load_inputs(a.baseline,a.pr1,a.csv,a.protocol,split)
        xy,wv,wm,rows,cat=(d[k] for k in ['xy','wv','wm','rows','metadata'])
        model=json.loads((root/'models.json').read_text())
        receivers=read(root/'receiver_results.csv');starts=read(root/'all_start_results.csv')
        trace=read(root/'all_objective_calls.csv.gz');profiles=read(root/'finite_domain_profiles.csv')
        obs=read(root/'all_reception_predictions.csv.gz');pred=read(root/'raw_wcl_predictions.csv.gz')
        summary=read(root/'downstream_summary.csv')
        check(split+' six arms x all33 inventory',len(receivers)==198 and set(receivers.bs)==set(cat) and set(receivers.arm)==set(ARMS))
        check(split+' unique receiver-arm rows',not receivers.duplicated(['bs','arm']).any())
        # Re-execute preserved full source against fitting messages in the same order.
        msgs=[]
        for wi in d['fitwi']:
            ids=np.flatnonzero(wm[wi]);ids=ids[np.argsort(-wv[wi,ids],kind='stable')]
            msgs.append(SimpleNamespace(x=float(xy[wi,0]),y=float(xy[wi,1]),receptions=[SimpleNamespace(gid=str(j+1),rssi=float(wv[wi,j])) for j in ids]))
        ref,a0=estimate_gateway_positions_rssfit(msgs,4.7,seed=1)
        total_source_replayed+=len(ref)
        maxsource=0.;maxintercept=0.
        for bs in sorted(cat):
            mm=model['NARROW'][str(bs)]
            if mm is None:continue
            coord=np.array(mm['coordinate']);err=float(np.linalg.norm(coord-ref[str(bs)]));ea=abs(mm['fitting_intercept_or_constant_db']-a0[str(bs)])
            source_receivers.append({'split':split,'bs':bs,'position_difference_m':err,'intercept_difference_db':ea})
            maxsource=max(maxsource,err);maxintercept=max(maxintercept,ea);primary_compared+=1
        check(split+' original source native position agreement',maxsource<=1e-7,maximum_difference_m=maxsource)
        check(split+' original source native intercept agreement',maxintercept<=1e-9,maximum_difference_db=maxintercept)
        # Every stored candidate: formula, clipped schedule, strict accepted state.
        maxloss=maxa=0.;start_checks=0
        for key,g in trace.groupby(['bs','domain','regime','start_rank0'],sort=False):
            bs,domain,regime,rank=key;bs=int(bs);rank=int(rank)
            prep=d['prepared'][bs];keep=prep['retained'];fxy,fr=xy[keep],wv[keep,bs-1]
            lower,upper=prep['narrow'] if domain=='NARROW' else d['wide']
            st=starts[(starts.bs==bs)&(starts.domain==domain)&(starts.regime==regime)&(starts.start_rank0==rank)]
            check(f'{split} BS{bs} {domain} {regime}/{rank} unique start row',len(st)==1)
            st=st.iloc[0];g=g.sort_values('call')
            check(f'{split} BS{bs} {domain} {regime}/{rank} contiguous call budget',np.array_equal(g.call,np.arange(1,len(g)+1)) and len(g)<=1921 and len(g)==st.objective_calls)
            incumbent=None;best=None;accepted_step_count=0
            for q in g.itertuples(index=False):
                candidate=np.array([q.candidate_x,q.candidate_y])
                loss,aa=_robust_gateway_loss_and_a0(*candidate,fxy,fr,4.7)
                maxloss=max(maxloss,abs(loss-q.loss_db));maxa=max(maxa,abs(aa-q.intercept_db))
                if q.call==1:
                    expected=np.clip([st.raw_start_x,st.raw_start_y],lower,upper)
                    ok=q.accepted and q.step_m==-1
                else:
                    direction=((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1))[int(q.direction_rank0)]
                    expected=np.clip(incumbent+np.array(direction)*q.step_m,lower,upper)
                    ok=bool(q.accepted)==bool(q.loss_db<best)
                if not ok or not np.allclose(candidate,expected,rtol=0,atol=1e-7):raise AssertionError(f'Trace inconsistency {key} call{q.call}')
                if q.accepted:incumbent=candidate;best=q.loss_db
            check(f'{split} BS{bs} {domain} {regime}/{rank} final incumbent',np.allclose(incumbent,[st.x,st.y],rtol=0,atol=1e-7) and best==st.training_loss_db)
            schedule=json.loads((root/'all_start_step_schedules.json').read_text()) if start_checks==0 else schedule
            sched=next(s['schedule'] for s in schedule if s['bs']==bs and s['domain']==domain and s['regime']==regime and s['start_rank0']==rank)
            schok=[s['step_m'] for s in sched]==[2000,1000,500,250,125,60]
            for s in sched:
                h=g[g.step_m==s['step_m']]
                schok=schok and len(h)==8*s['sweeps'] and list(h.sweep)==np.repeat(np.arange(1,s['sweeps']+1),8).tolist()
                schok=schok and list(h.direction_rank0)==list(range(8))*s['sweeps']
            check(f'{split} BS{bs} {domain} {regime}/{rank} complete sweep schedule',schok)
            start_checks+=1
        total_calls+=len(trace)
        check(split+' every trace objective matches source',maxloss<=1e-9,maximum_difference_db=maxloss,evaluations=len(trace))
        check(split+' every trace intercept matches source',maxa<=1e-9,maximum_difference_db=maxa)
        # All model choices must be first minimum of TRAINING loss, not validation.
        for bs in sorted(cat):
            for domain in ['NARROW','WIDE']:
                mm=model[domain+'_MS'][str(bs)]
                if mm is None:continue
                s=starts[(starts.bs==bs)&(starts.domain==domain)&(starts.regime=='multistart')].sort_values('start_rank0')
                winner=s.iloc[int(np.argmin(s.training_loss_db.to_numpy()))]
                check(f'{split} BS{bs} {domain} multistart winner is first training minimum',len(s)==5 and mm['selected_start_rank0']==winner.start_rank0 and np.array_equal(mm['coordinate'],[winner.x,winner.y]))
                native=starts[(starts.bs==bs)&(starts.domain==domain)&(starts.regime=='native')].iloc[0]
                check(f'{split} BS{bs} {domain} repeated native start0',np.array_equal(native[['x','y','training_loss_db']].to_numpy(),s.iloc[0][['x','y','training_loss_db']].to_numpy()))
        # Independent vector-form RSSI prediction, no validation recentering.
        maxpred=0.;maxres=0.;maxsummary=0.;srows=[]
        check(split+' observation key uniqueness',not obs.duplicated(['bs','role','csv_row_index0']).any())
        for bs in sorted(cat):
            g=obs[obs.bs==bs];prep=d['prepared'].get(bs);keep=np.array([],int) if prep is None else prep['retained']
            expectedfit=np.array([],int) if prep is None else prep['allfit'];expectedval=d['valwi'][wm[d['valwi'],bs-1]]
            for role,wi in [('fitting',expectedfit),('validation',expectedval)]:
                h=g[g.role==role].sort_values('role_order0')
                check(f'{split} BS{bs} {role} exact observation order',np.array_equal(h.working_index0,wi) and np.array_equal(h.csv_row_index0,rows[wi]))
                if len(h):
                    check(f'{split} BS{bs} {role} raw observations and weights',np.array_equal(h.rssi,wv[wi,bs-1]) and abs(h.within_receiver_role_weight.sum()-1)<1e-12)
                for arm in ARMS:
                    mm=model[arm][str(bs)];rr=receivers[(receivers.bs==bs)&(receivers.arm==arm)].iloc[0]
                    if mm is None:
                        check(f'{split} BS{bs} {role} {arm} unsupported predictions blank',h[arm+'_pred_dbm'].isna().all());continue
                    a0fit=mm['fitting_intercept_or_constant_db'];coord=mm['coordinate']
                    if coord is None:p=np.full(len(wi),a0fit)
                    else:
                        dx=xy[wi,0]-coord[0];dy=xy[wi,1]-coord[1]
                        p=a0fit-47*np.log10(np.sqrt(dx*dx+dy*dy)+1.)
                    if len(wi):
                        maxpred=max(maxpred,float(np.max(abs(p-h[arm+'_pred_dbm'].to_numpy()))))
                        e=wv[wi,bs-1]-p
                        maxres=max(maxres,float(np.max(abs(e-h[arm+'_signed_residual_db'].to_numpy()))));prediction_cells+=len(wi)
                        prefix='all_fitting' if role=='fitting' else 'validation'
                        vals={'median_abs_db':float(np.median(abs(e))),'mean_abs_db':float(np.mean(abs(e))),
                              'p90_abs_db':float(np.quantile(abs(e),.9)),'median_signed_db':float(np.median(e))}
                        for k,v in vals.items():maxsummary=max(maxsummary,abs(v-rr[prefix+'_'+k]))
                        if role=='fitting':
                            ix=[int(np.flatnonzero(wi==kk)[0]) for kk in keep];er=e[ix]
                            maxsummary=max(maxsummary,abs(float(np.median(abs(er)))-mm['retained_training_loss_db']))
                    else:check(f'{split} BS{bs} {arm} zero validation explicit',pd.isna(rr['validation_median_abs_db']))
        check(split+' all reception predictions independently reconstructed',maxpred<=1e-8,maximum_difference_db=maxpred)
        check(split+' all reception residuals independently reconstructed',maxres<=1e-8,maximum_difference_db=maxres)
        check(split+' all receiver RSSI summaries independently reconstructed',maxsummary<=1e-8,maximum_difference_db=maxsummary)
        # Profile formula and finite inequality independently evaluated with scalar extrema.
        maxprofile=0.;pboundfail=0
        for bs,g in profiles.groupby('bs',sort=False):
            keep=d['prepared'][int(bs)]['retained'];fxy=xy[keep];fr=wv[keep,int(bs)-1];mad=float(np.median(abs(fr-np.median(fr))))
            if len(g)!=168:raise AssertionError('Profile schedule length')
            for q in g.itertuples(index=False):
                loss,aa=_robust_gateway_loss_and_a0(q.x,q.y,fxy,fr,4.7)
                dist=np.sqrt((fxy[:,0]-q.x)**2+(fxy[:,1]-q.y)**2)+1.
                bound=47*math.log10(float(dist.max()/dist.min()))
                maxprofile=max(maxprofile,abs(loss-q.training_loss_db),abs(aa-q.fitting_intercept_db),abs(bound-q.range_term_db))
                pboundfail+=abs(loss-mad)>bound+1e-9
        total_profiles+=len(profiles)
        check(split+' all profiles match source and finite bound',maxprofile<=1e-8 and pboundfail==0,maximum_difference_db=maxprofile,points=len(profiles))
        # Every original selection and prediction: scalar summation, no dropped IDs.
        maxwcl=0.;maxerror=0.;dsummary=0.
        sels={int(q.csv_row_index0):q for q in d['selection'].itertuples(index=False)}
        check(split+' all2495 requests per geometry arm',all(len(pred[pred.arm==arm])==2495 for arm in GEOMETRY_ARMS))
        for q in pred.itertuples(index=False):
            sr=sels[int(q.csv_row_index0)];wi=int(q.working_index0)
            selected=list(map(int,sr.selected_receivers.split(';')))
            if q.selected_receivers!=sr.selected_receivers:raise AssertionError('Replaced receiver selection')
            coords=[];missing=[]
            for bs in selected:
                coord=cat[bs] if q.arm=='CAT' else (None if model[q.arm][str(bs)] is None else model[q.arm][str(bs)]['coordinate'])
                if coord is None:missing.append(bs)
                else:coords.append(coord)
            if missing:
                if q.status!='missing_fitted_receiver' or not pd.isna(q.pred_x) or q.common_complete:
                    raise AssertionError('Missing-coordinate handling')
                continue
            w=[10.**(float(wv[wi,bs-1])/10.) for bs in selected];sw=math.fsum(w)
            expected=np.array([math.fsum(weight*float(coord[k]) for weight,coord in zip(w,coords))/sw for k in [0,1]])
            maxwcl=max(maxwcl,float(np.linalg.norm(expected-np.array([q.pred_x,q.pred_y]))))
            err=math.hypot(expected[0]-xy[wi,0],expected[1]-xy[wi,1]);maxerror=max(maxerror,abs(err-q.error_m));centroid_cases+=1
            weights=np.array([float(v) for v in q.normalized_raw_weights.split(';')]);checkweights=np.array(w)/sw
            if not np.allclose(weights,checkweights,rtol=0,atol=1e-12):raise AssertionError('Centroid weights differ')
        check(split+' every finite centroid independently reconstructed',maxwcl<=1e-7,maximum_position_difference_m=maxwcl)
        check(split+' every localization error independently reconstructed',maxerror<=1e-7,maximum_error_difference_m=maxerror)
        catcommon=pred[(pred.arm=='CAT')&pred.common_complete].error_m.to_numpy()
        for q in summary.itertuples(index=False):
            h=pred[pred.arm==q.arm]
            if q.population=='common_complete':h=h[h.common_complete]
            e=h.error_m.to_numpy();delta=abs(float(np.median(e))-q.median_error_m)
            dsummary=max(dsummary,delta,abs(float(e.mean())-q.mean_error_m),abs(float(np.quantile(e,.9))-q.p90_error_m))
            check(f'{split} {q.arm} {q.population} matching downstream N',len(e)==q.scored_n and np.isfinite(e).all())
        check(split+' every downstream summary reconstructed',dsummary<=1e-7,maximum_difference_m=dsummary)
        metrics.append({'split':split,'native_source_primary_n':sum(model['NARROW'][str(bs)] is not None for bs in cat),
            'original_source_fitter_returned_receivers':len(ref),'trace_evaluations_checked':len(trace),'profiles_checked':len(profiles),
            'max_source_native_position_difference_m':maxsource,'max_source_objective_difference_db':maxloss,
            'max_reception_prediction_difference_db':maxpred,'max_receiver_summary_difference_db':maxsummary,
            'max_centroid_position_difference_m':maxwcl,'max_downstream_summary_difference_m':dsummary})
    write_csv(a.out/'NATIVE_SOURCE_AGREEMENT.csv',pd.DataFrame(source_receivers))
    write_csv(a.out/'NUMERICAL_CHECK_LIMITS.csv',pd.DataFrame(metrics))
    write_json(a.out/'CHECKS.json',checks)
    write_json(a.out/'VERIFICATION_RECEIPT.json',{'status':'PASS','checks':len(checks),'failed':sum(not q['pass'] for q in checks),
        'primary_native_fits_compared_to_original_source':primary_compared,'original_source_fit_receivers_in_verification_replays':total_source_replayed,
        'every_logged_search_objective_checked':total_calls,'finite_profile_points_checked':total_profiles,
        'reception_prediction_cells_checked':prediction_cells,'finite_centroid_predictions_checked':centroid_cases,
        'scope':'Post-run formula, state-transition, native-source replay, population, validation and centroid verification. Verification replays are not additional arms, independent replications or statistical confirmation.'})
    print(json.dumps(json.loads((a.out/'VERIFICATION_RECEIPT.json').read_text()),indent=2))

if __name__=='__main__':main()
