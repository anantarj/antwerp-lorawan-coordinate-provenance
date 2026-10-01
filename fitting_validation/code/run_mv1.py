#!/usr/bin/env python3
"""Execute the locked Paper A MV1 on one predeclared split.

Outputs must be new and outside every input workspace. All manifests, protocol,
code-gate hashes, fitting ledgers and primary selections are checked. Missing
support is explicit; an unexpected computation error prevents COMPLETE.json.
"""
from __future__ import annotations
import argparse, collections, csv, datetime as dt, gzip, io, json, os, platform
import random, sys, time, traceback
from pathlib import Path
import numpy as np
import pandas as pd
import pyproj
from preflight import digest,payload,write_json,write_csv
from study_contract import prepare_observations,fit_box,loss_intercept,sha_role
from mv1_core import (initializer,traced_search,scheduled_starts,select_start,
                      predict,residual_metrics,ray_profiles,geometry_fields,raw_wcl,
                      LOSS_TOL,POSITION_TOL)

PROTOCOL_SHA='405bf282c73545fe8c00fbccbddcdd099cffdbc0bfb567f926e6cde98010973c'
ARMS=('CAT','CONST','NARROW','WIDE','NARROW_MS','WIDE_MS')
GEOMETRY_ARMS=('CAT','NARROW','WIDE','NARROW_MS','WIDE_MS')


def utc():return dt.datetime.now(dt.timezone.utc).isoformat()


def verify_manifest(root, name='MANIFEST.json'):
    record=json.loads((root/name).read_text())
    failures=[]
    for e in record['files']:
        p=root/e['path']
        if not p.is_file() or p.stat().st_size!=e.get('bytes',e.get('size')) or digest(p)!=e['sha256']:
            failures.append(e['path'])
    if failures:raise ValueError(f'Manifest mismatch {root/name}: {failures}')
    return {'manifest':name,'entries':len(record['files']),'sha256':digest(root/name),'failures':failures}


def verify_gate(gate_path,protocol_path):
    gate=json.loads(gate_path.read_text());root=Path(__file__).resolve().parents[1]
    if gate.get('status')!='READY_FOR_REAL_DATA_EXECUTION':raise ValueError('Scientific execution gate not ready')
    if digest(protocol_path)!=PROTOCOL_SHA or gate['protocol_sha256']!=PROTOCOL_SHA:
        raise ValueError('Protocol mismatch')
    for rel,h in gate['locked_files'].items():
        if digest(root/rel)!=h:raise ValueError(f'Code/resolution gate mismatch: {rel}')
    return gate


def load_inputs(baseline,pr1,csv_path,protocol_path,split):
    protocol=json.loads(protocol_path.read_text())
    if digest(protocol_path)!=PROTOCOL_SHA:raise ValueError('MV1 protocol is not the locked version')
    verified=[verify_manifest(baseline),verify_manifest(baseline,'EVIDENCE_MANIFEST.json'),verify_manifest(pr1)]
    raw=payload(csv_path)
    import hashlib
    if hashlib.sha256(raw).hexdigest()!=protocol['raw_input_hashes']['csv']:raise ValueError('CSV payload mismatch')
    df=pd.read_csv(io.BytesIO(raw));del raw
    if df.shape!=(130429,77):raise ValueError('CSV schema/shape mismatch')
    vals=df[[f'BS {i}' for i in range(1,73)]].to_numpy(float)
    valid=np.isfinite(vals)&(vals>=-150)&(vals<=-20)
    rows=np.flatnonzero((valid.sum(axis=1)>=3)&np.isfinite(df.Latitude)&np.isfinite(df.Longitude))
    ledger=pd.read_csv(baseline/'computational/populations/working_source_ledger.csv.gz').sort_values('working_index0')
    if len(rows)!=55375 or not np.array_equal(rows,ledger.csv_row_index0):raise ValueError('Working rows changed')
    tf=pyproj.Transformer.from_crs(4326,32631,always_xy=True)
    x,y=tf.transform(df.Longitude.iloc[rows].to_numpy(),df.Latitude.iloc[rows].to_numpy())
    xy=np.column_stack([x,y]);wv=vals[rows];wm=valid[rows]
    if not np.allclose(xy,ledger[['utm_x','utm_y']],rtol=0,atol=1e-7):raise ValueError('Projection changed')
    metadata={int(k):np.asarray(v,float) for k,v in json.loads((baseline/'computational/data_products/metadata33.json').read_text()).items()}
    if len(metadata)!=33:raise ValueError('Metadata roster changed')
    sr=pr1/'results/preflight'/split
    sf=pd.read_csv(sr/'split_rows.csv.gz');sup=pd.read_csv(sr/'primary33_support.csv')
    ret=pd.read_csv(sr/'retained_fit_rows.csv.gz');sel=pd.read_csv(sr/'fixed_primary_selection.csv.gz')
    allsup=pd.read_csv(sr/'all_receiver_support_and_domains.csv')
    summary=json.loads((sr/'summary.json').read_text())
    cal=pd.read_csv(baseline/'computational/populations/calibration_rows.csv')
    pri=pd.read_csv(baseline/'computational/populations/official33_primary_rows.csv')
    if not np.array_equal(sf.csv_row_index0,cal.csv_row_index0) or not np.array_equal(sf.working_index0,cal.working_index0):
        raise ValueError('Calibration order mismatch')
    if not np.array_equal(sel.csv_row_index0,pri.csv_row_index0) or len(sel)!=2495:
        raise ValueError('Primary evaluation identity mismatch')
    spec=protocol['splits']['primary' if split=='group80' else 'sensitivity']
    expected=[sha_role(str(int(v)),spec['salt']) for v in sf.split_component]
    if expected!=sf.role.tolist():raise ValueError('Split role mismatch')
    fit=sf[sf.role=='fitting'];val=sf[sf.role=='validation']
    for field in ['legacy_content_sha256','serialization_sha256','split_component']+(['spatial_cell'] if split=='space1000' else []):
        if set(fit[field])&set(val[field]):raise ValueError('Split leakage: '+field)
    fitwi=fit.working_index0.to_numpy(int);valwi=val.working_index0.to_numpy(int)
    wide=fit_box(xy[fitwi]);unbuffered=(xy[fitwi].min(axis=0),xy[fitwi].max(axis=0))
    if not np.array_equal(wide[0],summary['wide_box']['lower']) or not np.array_equal(wide[1],summary['wide_box']['upper']):
        raise ValueError('Wide fitting-only box mismatch')
    # Reconstruct ALL receiver sampling in first-encounter order before projecting to 33.
    by=collections.OrderedDict()
    for wi in fitwi:
        ii=np.flatnonzero(wm[wi]);ii=ii[np.argsort(-wv[wi,ii],kind='stable')]
        for j in ii:by.setdefault(int(j+1),[]).append((int(rows[wi]),int(wi),float(wv[wi,j])))
    rng=random.Random(1);prepared={};inputs=[]
    for bs,records in by.items():
        kept,info=prepare_observations(records,rng)
        k=np.array([r[1] for r in kept],int)
        old=ret[ret.bs==bs].sort_values('retained_rank0')
        if not np.array_equal(k,old.working_index0) or not np.array_equal(rows[k],old.csv_row_index0):
            raise ValueError(f'Retained fitting order mismatch BS{bs}')
        historical=allsup[allsup.bs==bs].iloc[0]
        if any(info[c]!=historical[c] for c in ['pre_filter_n','subsample_n','retained_n','strong_filter_used','strong_threshold_dbm']):
            raise ValueError(f'Preprocessing mismatch BS{bs}')
        narrow=fit_box(xy[k])
        a=np.array([historical.narrow_xmin,historical.narrow_ymin]);b=np.array([historical.narrow_xmax,historical.narrow_ymax])
        if not np.allclose(narrow[0],a,rtol=0,atol=1e-7) or not np.allclose(narrow[1],b,rtol=0,atol=1e-7):
            raise ValueError(f'Narrow fitting-only box mismatch BS{bs}')
        if np.any(narrow[0]<wide[0]) or np.any(narrow[1]>wide[1]):raise ValueError('Nonnested domain')
        prepared[bs]={'retained':k,'allfit':np.array([r[1] for r in records],int),'info':info,'narrow':narrow}
    # Reconstruct original reception selection, without choosing using a fitted map.
    bslist=sorted(metadata);bidx=np.array(bslist)-1
    supported={bs for bs in metadata if bs in prepared and prepared[bs]['info']['pre_filter_n']>=10}
    for r in sel.itertuples(index=False):
        wi=int(r.working_index0);ids=bidx[wm[wi,bidx]];ids=ids[np.argsort(-wv[wi,ids],kind='stable')][:10]
        selected=';'.join(str(i+1) for i in ids)
        if selected!=r.selected_receivers or bool(set(ids+1)<=supported)!=r.map_support_complete:
            raise ValueError(f'Primary selections or support mismatch row {r.csv_row_index0}')
    for bs in metadata:
        v=valwi[wm[valwi,bs-1]];p=prepared.get(bs)
        original=sup[sup.bs==bs].iloc[0]
        if len(v)!=original.validation_n or (0 if p is None else len(p['allfit']))!=original.pre_filter_n:
            raise ValueError(f'Support discrepancy BS{bs}')
    return {'xy':xy,'wv':wv,'wm':wm,'rows':rows,'metadata':metadata,'fitwi':fitwi,'valwi':valwi,
            'wide':wide,'unbuffered':unbuffered,'prepared':prepared,'selection':sel,'summary':summary,
            'verified_manifests':verified,'preflight_hashes':{p.name:digest(p) for p in sr.iterdir() if p.is_file()},
            'csv_sha256':protocol['raw_input_hashes']['csv']}


def gz_csv(path,fieldnames):
    # Context is handled explicitly by the caller; zero mtime makes records repeatable.
    raw=path.open('wb');gz=gzip.GzipFile(fileobj=raw,mode='wb',mtime=0,filename='')
    text=io.TextIOWrapper(gz,encoding='utf-8',newline='')
    writer=csv.writer(text);writer.writerow(fieldnames)
    return raw,text,writer


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ['baseline','pr1','csv','protocol','gate','out']:ap.add_argument('--'+k,required=True,type=Path)
    ap.add_argument('--split',required=True,choices=['group80','space1000'])
    a=ap.parse_args();start=time.perf_counter();started=utc()
    root=Path(__file__).resolve().parents[1];out=a.out.resolve()
    for protected in [a.baseline.resolve(),a.pr1.resolve()]:
        if out.is_relative_to(protected):raise SystemExit('Output must be outside preserved input trees')
    if out.exists():raise SystemExit('Output exists; refusing overwrite: '+str(out))
    gate=verify_gate(a.gate,a.protocol)
    out.mkdir(parents=True,exist_ok=False)
    try:
        data=load_inputs(a.baseline,a.pr1,a.csv,a.protocol,a.split)
        write_json(out/'INPUT_VERIFICATION.json',{'split':a.split,'verified_manifests':data['verified_manifests'],
            'preflight_hashes':data['preflight_hashes'],'csv_sha256':data['csv_sha256'],'protocol_sha256':PROTOCOL_SHA,
            'code_gate_sha256':digest(a.gate),'before_first_fit_utc':utc()})
        write_json(out/'RUNNING.json',{'started':started,'split':a.split,'status':'IN_PROGRESS'})
        xy,wv,wm,rows,metadata=(data[k] for k in ['xy','wv','wm','rows','metadata'])
        models={k:{} for k in ARMS};receiver_records=[];start_records=[];profiles=[];schedules=[];obsframes=[]
        traw,ttext,tw=gz_csv(out/'all_objective_calls.csv.gz',[
            'split','bs','domain','regime','start_rank0','call','step_m','sweep','direction_rank0','candidate_x','candidate_y','loss_db','intercept_db','accepted'])
        new_fit_runs=0;total_calls=0
        for bi,bs in enumerate(sorted(metadata)):
            prep=data['prepared'].get(bs)
            valwi=data['valwi'][wm[data['valwi'],bs-1]]
            allfit=np.array([],int) if prep is None else prep['allfit']
            kept=np.array([],int) if prep is None else prep['retained']
            supported=len(allfit)>=10
            info={} if prep is None else prep['info']
            common={'split':a.split,'bs':bs,'pre_filter_n':len(allfit),'retained_n':len(kept),'validation_n':len(valwi),
                    'eligible_fit':supported,'eligible_validation':bool(len(valwi)),
                    'strong_filter_used':info.get('strong_filter_used',False),'strong_threshold_dbm':info.get('strong_threshold_dbm'),
                    'subsample_n':info.get('subsample_n',0)}
            this={}
            if supported:
                fxy,fr=xy[kept],wv[kept,bs-1];g0=initializer(fxy,fr)
                ls,aa=loss_intercept(metadata[bs],fxy,fr)
                this['CAT']={'coordinate':metadata[bs],'intercept_db':aa,'loss_db':ls,'objective_calls':1,
                             'selected_start_rank0':None,'domain':None,'source':'fixed_catalogue'}
                c=float(np.median(fr))
                this['CONST']={'coordinate':None,'intercept_db':c,'loss_db':float(np.median(abs(fr-c))),
                               'objective_calls':0,'selected_start_rank0':None,'domain':None,'source':'constant_fitting_rssi'}
                starts=scheduled_starts(g0,*data['unbuffered'])
                for domain in ('NARROW','WIDE'):
                    lower,upper=prep['narrow'] if domain=='NARROW' else data['wide']
                    outputs=[];native=None;projected_seen=[]
                    for regime,scheduled in [('native',[g0]),('multistart',starts)]:
                        for si,st in enumerate(scheduled):
                            fitted=traced_search(fxy,fr,lower,upper,st);new_fit_runs+=1;total_calls+=fitted['objective_calls']
                            for trace in fitted['trace']:tw.writerow((a.split,bs,domain,regime,si,*trace))
                            duplicate=None
                            if regime=='multistart':
                                projected=np.clip(st,lower,upper)
                                duplicate=next((j for j,p in enumerate(projected_seen) if np.array_equal(p,projected)),None)
                                projected_seen.append(projected)
                            sr={'split':a.split,'bs':bs,'domain':domain,'regime':regime,'start_rank0':si,
                                'raw_start_x':float(st[0]),'raw_start_y':float(st[1]),
                                'projected_start_x':float(fitted['start_projected'][0]),'projected_start_y':float(fitted['start_projected'][1]),
                                'duplicate_projected_start_of_rank0':duplicate,'x':float(fitted['coordinate'][0]),'y':float(fitted['coordinate'][1]),
                                'training_loss_db':fitted['loss_db'],'fitting_intercept_db':fitted['intercept_db'],
                                'objective_calls':fitted['objective_calls'],'sweep_cap_with_improvement_count':sum(s['sweep_cap_hit_with_improvement'] for s in fitted['schedule']),
                                **geometry_fields(fitted['coordinate'],metadata[bs],lower,upper)}
                            for role,wi in [('all_fitting',allfit),('validation',valwi)]:
                                metrics=residual_metrics(wv[wi,bs-1],predict(xy[wi],fitted['coordinate'],fitted['intercept_db']))
                                sr.update({role+'_'+k:v for k,v in metrics.items()})
                            schedules.append({'split':a.split,'bs':bs,'domain':domain,'regime':regime,'start_rank0':si,'schedule':fitted['schedule']})
                            start_records.append(sr)
                            # The trace is already saved; don't retain it in model memory.
                            fitted.pop('trace')
                            if regime=='native':native=fitted
                            else:outputs.append(fitted)
                    if not np.array_equal(native['coordinate'],outputs[0]['coordinate']) or native['loss_db']!=outputs[0]['loss_db'] or native['objective_calls']!=outputs[0]['objective_calls']:
                        raise AssertionError('Native/start-zero repeat mismatch')
                    winner=select_start(outputs)
                    for arm,result,selected in [(domain,native,0),(domain+'_MS',outputs[winner],winner)]:
                        this[arm]={**result,'selected_start_rank0':selected,'domain':domain,
                                   'source':'native' if arm==domain else 'five_scheduled_starts',
                                   'objective_calls':native['objective_calls'] if arm==domain else sum(o['objective_calls'] for o in outputs)}
                profiles.extend([{'split':a.split,'bs':bs,**p} for p in ray_profiles(fxy,fr,g0,*data['wide'])])
            # All 33 x six rows are kept, including wholly unsupported BS71 in space1000.
            for arm in ARMS:
                model=this.get(arm);r={**common,'arm':arm,'fit_status':'available' if model is not None else 'insufficient_fitting_support'}
                if model is not None:
                    coordinate=model['coordinate'];models[arm][bs]=model
                    r.update({'x':None if coordinate is None else float(coordinate[0]),'y':None if coordinate is None else float(coordinate[1]),
                        'fitting_intercept_or_constant_db':model['intercept_db'],'training_loss_db':model['loss_db'],
                        'objective_calls':model['objective_calls'],'selected_start_rank0':model['selected_start_rank0']})
                    for role,wi in [('retained_fitting',kept),('all_fitting',allfit),('validation',valwi)]:
                        r.update({role+'_'+k:v for k,v in residual_metrics(wv[wi,bs-1],predict(xy[wi],coordinate,model['intercept_db'])).items()})
                    if abs(r['retained_fitting_median_abs_db']-model['loss_db'])>LOSS_TOL:raise AssertionError('Fitting loss/prediction mismatch')
                    if coordinate is not None:
                        r['catalogue_discrepancy_m']=float(np.linalg.norm(coordinate-metadata[bs]))
                        if model['domain']:
                            lower,upper=prep['narrow'] if model['domain']=='NARROW' else data['wide']
                            r.update(geometry_fields(coordinate,metadata[bs],lower,upper))
                            r['selected_run_sweep_cap_with_improvement_count']=sum(s['sweep_cap_hit_with_improvement'] for s in model['schedule'])
                        from study_contract import flatness_bound
                        r['retained_range_term_db']=flatness_bound(coordinate,xy[kept])
                else:
                    models[arm][bs]=None
                receiver_records.append(r)
            # Wide-form reception record contains every fitting + validation reception
            # for the primary receiver, actual prediction/residual for each output arm,
            # and within-receiver equal weights (not independent-observation claims).
            for role,wi in [('fitting',allfit),('validation',valwi)]:
                frame=pd.DataFrame({'split':a.split,'bs':bs,'role':role,'role_order0':np.arange(len(wi)),
                    'csv_row_index0':rows[wi],'working_index0':wi,'tx_x':xy[wi,0],'tx_y':xy[wi,1],
                    'rssi':wv[wi,bs-1],'retained_for_fitting':np.isin(wi,kept) if role=='fitting' else np.zeros(len(wi),bool),
                    'within_receiver_role_weight':np.full(len(wi),1./len(wi) if len(wi) else np.nan)})
                rankmap={int(v):i for i,v in enumerate(kept)}
                frame['retained_fit_rank0']=[rankmap.get(int(v)) if role=='fitting' else None for v in wi]
                for arm in ARMS:
                    model=this.get(arm)
                    pred=np.full(len(wi),np.nan) if model is None else predict(xy[wi],model['coordinate'],model['intercept_db'])
                    frame[arm+'_pred_dbm']=pred;frame[arm+'_signed_residual_db']=wv[wi,bs-1]-pred
                obsframes.append(frame)
            print(f'{a.split} BS{bs} {bi+1}/33 fitting_support={len(allfit)} validation_support={len(valwi)} complete',flush=True)
        ttext.close();traw.close()
        # Export all selected maps and fitting intercepts, without numpy JSON objects.
        serial_models={arm:{str(bs):(None if m is None else {
            'coordinate':None if m['coordinate'] is None else m['coordinate'].tolist(),
            'fitting_intercept_or_constant_db':m['intercept_db'],'retained_training_loss_db':m['loss_db'],
            'selected_start_rank0':m['selected_start_rank0'],'total_objective_calls':m['objective_calls'],'source':m['source']})
            for bs,m in by.items()} for arm,by in models.items()}
        write_json(out/'models.json',serial_models)
        write_json(out/'all_start_step_schedules.json',schedules)
        write_csv(out/'receiver_results.csv',pd.DataFrame(receiver_records))
        write_csv(out/'all_start_results.csv',pd.DataFrame(start_records))
        write_csv(out/'finite_domain_profiles.csv',pd.DataFrame(profiles))
        write_csv(out/'all_reception_predictions.csv.gz',pd.concat(obsframes,ignore_index=True))
        # All primary requests are retained. Comparison cohort is common complete.
        maps={'CAT':metadata}
        for arm in GEOMETRY_ARMS[1:]:maps[arm]={bs:m['coordinate'] for bs,m in models[arm].items() if m is not None}
        predictions=[];commonrows=[]
        for q in data['selection'].itertuples(index=False):
            wi=int(q.working_index0);selected=list(map(int,q.selected_receivers.split(';')));r=wv[wi,np.array(selected)-1]
            weights=np.power(10.,r/10.);weights/=weights.sum()
            outputs={arm:raw_wcl(selected,r,maps[arm]) for arm in GEOMETRY_ARMS}
            complete=all(v[0] is not None for v in outputs.values())
            if complete!=q.map_support_complete:raise AssertionError('Changed common-complete coverage')
            if complete:commonrows.append(int(q.csv_row_index0))
            for arm,(g,missing) in outputs.items():
                predictions.append({'split':a.split,'arm':arm,'csv_row_index0':int(q.csv_row_index0),'working_index0':wi,
                    'selected_receivers':q.selected_receivers,'raw_rssi_dbm':';'.join(map(str,r)),
                    'normalized_raw_weights':';'.join(map(str,weights)),
                    'status':'available' if g is not None else 'missing_fitted_receiver','missing_receivers':';'.join(map(str,missing)),
                    'common_complete':complete,'reference_x':float(xy[wi,0]),'reference_y':float(xy[wi,1]),
                    'pred_x':None if g is None else float(g[0]),'pred_y':None if g is None else float(g[1]),
                    'error_m':None if g is None else float(np.linalg.norm(g-xy[wi]))})
        if len(commonrows)!=data['summary']['existing_primary_messages_with_all_selected_coordinates_supported']:
            raise AssertionError('Common cohort count mismatch')
        pf=pd.DataFrame(predictions);write_csv(out/'raw_wcl_predictions.csv.gz',pf)
        write_csv(out/'common_complete_rows.csv',pd.DataFrame({'csv_row_index0':commonrows}))
        summaries=[];base=pf[(pf.arm=='CAT')&pf.common_complete].error_m.to_numpy()
        for arm in GEOMETRY_ARMS:
            group=pf[(pf.arm==arm)&pf.common_complete];e=group.error_m.to_numpy()
            if len(e)!=len(base) or not np.isfinite(e).all():raise AssertionError('Mismatched downstream cohorts')
            summaries.append({'split':a.split,'arm':arm,'population':'common_complete','requested_n':2495,'scored_n':len(e),
                'available_full_n':int((pf[pf.arm==arm].status=='available').sum()),'median_error_m':float(np.median(e)),
                'mean_error_m':float(np.mean(e)),'p90_error_m':float(np.quantile(e,.9)),
                'difference_of_medians_vs_CAT_m':float(np.median(e)-np.median(base)),
                'ratio_of_medians_vs_CAT':float(np.median(e)/np.median(base)),
                'greater_individual_error_than_CAT_n':int(np.sum(e>base+POSITION_TOL))})
        full=pf[pf.arm=='CAT'].error_m.to_numpy()
        summaries.append({'split':a.split,'arm':'CAT','population':'full_original_reference_only','requested_n':2495,'scored_n':len(full),
            'available_full_n':len(full),'median_error_m':float(np.median(full)),'mean_error_m':float(full.mean()),'p90_error_m':float(np.quantile(full,.9))})
        write_csv(out/'downstream_summary.csv',pd.DataFrame(summaries))
        if not all(p['finite_bound_satisfied'] for p in profiles):raise AssertionError('Finite-data bound failed')
        verify_gate(a.gate,a.protocol)
        ending=[verify_manifest(a.baseline),verify_manifest(a.baseline,'EVIDENCE_MANIFEST.json'),verify_manifest(a.pr1)]
        files=[{'path':str(p.relative_to(out)),'bytes':p.stat().st_size,'sha256':digest(p)} for p in sorted(out.rglob('*')) if p.is_file() and p.name!='RUNNING.json']
        write_json(out/'OUTPUT_MANIFEST.json',{'files':files,'scope':'scientific outputs and input-verification receipt; excludes self and completion/execution metadata'})
        write_json(out/'EXECUTION.json',{'started_utc':started,'completed_utc':utc(),'seconds':time.perf_counter()-start,
            'argv':sys.argv,'cwd':os.getcwd(),'split':a.split,'environment':{'python':sys.version,'numpy':np.__version__,
                'pandas':pd.__version__,'pyproj':pyproj.__version__,'proj':pyproj.proj_version_str,'platform':platform.platform(),
                'thread_environment':{k:os.environ.get(k) for k in ['OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','PYTHONHASHSEED']}},
            'code_gate_sha256':digest(a.gate),'protocol_sha256':PROTOCOL_SHA,'baseline_unchanged_checks':ending})
        write_json(out/'COMPLETE.json',{'status':'COMPLETE','split':a.split,'new_local_search_runs':new_fit_runs,
            'search_objective_calls':total_calls,'primary_receivers_reported':33,'receiver_arm_rows':len(receiver_records),
            'start_rows':len(start_records),'finite_profile_rows':len(profiles),'requested_downstream_rows':2495*len(GEOMETRY_ARMS),
            'common_complete_n':len(commonrows),'scope':'New split-specific receiver fits, frozen-intercept predictions, prescribed finite profiles and raw-WCL predictions; not external replication or population inference.'})
        (out/'RUNNING.json').unlink()
        print('COMPLETE',out,flush=True)
    except Exception as exc:
        write_json(out/'FAILED.json',{'status':'FAILED','error_type':type(exc).__name__,'error':str(exc),'traceback':traceback.format_exc(),'utc':utc()})
        raise

if __name__=='__main__':main()
