#!/usr/bin/env python3
"""Bounded post-review receiver-removal and geographic-transfer controls.
Original inputs are read-only. Draw memberships are saved before evaluation.
These are new identified experiments, not purported historical replays.
"""
from __future__ import annotations
import argparse, json, random, time
from pathlib import Path
import numpy as np
import pandas as pd
from common import ROOT, context, dump, csvout, loadmap, metadata, get_case, diff_location, ev, bl, sha
from benchmark import fingerprint
from inference import schemes, median_draws
GEO_METHODS=['FP_k3','WCL_raw','WCL_bc','ABS_mean','DIFF_median','MinMax']

def stats(a):
    a=np.asarray(a,float)
    if not len(a) or not np.isfinite(a).all(): raise ValueError('Empty/nonfinite results')
    return dict(n=len(a),median_m=float(np.median(a)),mean_m=float(a.mean()),p90_m=float(np.quantile(a,.9)),over_1km_fraction=float(np.mean(a>1000)))

def paired(f,cols,pairs,experiment,which):
    values=f[cols].to_numpy(float);point=np.median(values,axis=0);out=[]
    for scheme,groups in schemes(f).items():
        if scheme not in which:continue
        draws,meta=median_draws(values,groups)
        for name,a,b in pairs:
            d=draws[:,a]-draws[:,b];rat=draws[:,a]/draws[:,b]
            lo,hi=np.quantile(d,[.025,.975]);rl,rh=np.quantile(rat,[.025,.975])
            out.append(dict(experiment=experiment,contrast=name,scheme=scheme,replicates=6000,n_messages=len(f),**meta,difference_m=float(point[a]-point[b]),ratio=float(point[a]/point[b]),difference_low_m=float(lo),difference_high_m=float(hi),ratio_low=float(rl),ratio_high=float(rh)))
    return out

def geo_predictions(c,wis,mp,a0):
    records=[]
    for rank,wi in enumerate(wis):
        case=get_case(c,wi,mp,a0)
        if case is None:raise ValueError('Eligible message disappeared')
        g,r,t,gids=case;q=r-np.array([a0[z] for z in gids]);diff,old,npair=diff_location(g,q)
        pred={'WCL_raw':ev.wcl_estimate(g,r),'WCL_bc':ev.wcl_estimate(g,q),'ABS_mean':bl.lattice(ev,g,q,4.7,'abs','mean'),'DIFF_median':diff,'MinMax':bl.minmax(g,q,4.7)}
        rec=dict(sample_rank0=rank,**metadata(c,wi),selected_receivers=';'.join(gids),raw_RSSI=';'.join(map(str,r)),support=len(gids),admitted_pairs=npair,minmax_infeasible=bool(bl.minmax_infeasible(g,q,4.7)),DIFF_empty_pair=npair==0,DIFF_legacy_policy_error_m=float(np.linalg.norm(old-t)))
        for name,pos in pred.items():
            if not np.isfinite(pos).all():raise ValueError('Nonfinite prediction')
            rec.update({name+'_x':float(pos[0]),name+'_y':float(pos[1]),name+'_error_m':float(np.linalg.norm(pos-t))})
        records.append(rec)
    return pd.DataFrame(records)

def density(c,pop,official,a0,out):
    out.mkdir(exist_ok=True);wis=pop['primary_working_ids'];db=pop['fingerprint_database_working_ids'];allg=sorted(official,key=int);definitions=[]
    for count in [33,23,16,10,6]:
        for draw in range(1 if count==33 else 8):
            roster=allg if count==33 else sorted(random.Random(20260905+100*count+draw).sample(allg,count),key=int)
            keep=[wi for wi in wis if get_case(c,wi,{g:official[g] for g in roster},a0) is not None]
            definitions.append(dict(experiment=f'removal_{count}_{draw}',retained_receivers=count,draw_index0=draw,roster=roster,eligible_working_ids=keep,eligible_csv_rows=[int(c['rows'][i]) for i in keep]))
    dump(out/'draw_definitions.json',definitions)
    b=pd.read_csv(ROOT/'inputs/base_geometric_predictions.csv.gz');b=b[(b.experiment=='primary33')&(b.assignment=='official')].set_index('working_index0').loc[wis]
    fp=pd.read_csv(ROOT/'inputs/base_fingerprint_predictions.csv.gz');fp=fp[fp.experiment=='primary33'].set_index('working_index0').loc[wis]
    original={'MinMax':b.MinMax_error_m.to_numpy(),'FP_k3':fp.FP_k3_error_m.to_numpy()};frames=[];summaries=[];intervals=[];checks=[]
    for spec in definitions:
        roster=spec['roster'];mp={g:official[g] for g in roster};keep=set(spec['eligible_working_ids']);f=fingerprint(c,db,wis,roster)
        f['experiment']=spec['experiment'];f['retained_receivers']=len(roster);f['draw_index0']=spec['draw_index0'];f['selected_receivers']=[';'.join(r.gid for r in c['msgs'][wi].receptions if r.gid in mp) for wi in wis]
        f['support']=[sum(r.gid in mp for r in c['msgs'][wi].receptions) for wi in wis];f['geometric_eligible']=[wi in keep for wi in wis]
        f['MinMax_x']=np.nan;f['MinMax_y']=np.nan;f['MinMax_error_m']=np.nan;f['minmax_infeasible']=False
        for i,wi in enumerate(wis):
            if wi not in keep:continue
            g,r,t,gids=get_case(c,wi,mp,a0);q=r-np.array([a0[z] for z in gids]);pos=bl.minmax(g,q,4.7)
            f.loc[i,['MinMax_x','MinMax_y','MinMax_error_m']]=[*pos,np.linalg.norm(pos-t)];f.loc[i,'minmax_infeasible']=bool(bl.minmax_infeasible(g,q,4.7))
        for m in ['FP_k3','MinMax']:f['full_'+m+'_error_m']=original[m]
        survivor=f[f.geometric_eligible].copy().reset_index(drop=True)
        if len(survivor):
            for method in ['FP_k3','MinMax']:
                small=survivor[method+'_error_m'];full=survivor['full_'+method+'_error_m'];allmed=float(np.median(original[method]));treatment=float(np.median(small)-np.median(full));selection=float(np.median(full)-allmed);direct=float(np.median(small)-allmed)
                checks.append({'check':'median_decomposition','experiment':spec['experiment'],'method':method,'pass':abs(direct-treatment-selection)<1e-8})
                summaries.append(dict(experiment=spec['experiment'],draw_index0=spec['draw_index0'],retained_receivers=len(roster),method=method,parent_n=len(wis),coverage_fraction=len(survivor)/len(wis),n_ineligible=len(wis)-len(survivor),full_parent_median_m=allmed,full_survivor_median_m=float(np.median(full)),removal_component_m=treatment,selection_component_m=selection,total_displayed_change_m=direct,**stats(small),FP_all_parent_median_m=float(np.median(f.FP_k3_error_m)) if method=='FP_k3' else None))
            intervals+=paired(survivor,['FP_k3_error_m','MinMax_error_m','full_FP_k3_error_m','full_MinMax_error_m'],[('FP_removal_on_survivors',0,2),('MinMax_removal_on_survivors',1,3),('MinMax_minus_FP_on_survivors',1,0)],spec['experiment'],['paired_messages','spatial_1000m'])
        if len(roster)==33:
            for m in ['FP_k3','MinMax']:
                same=bool(np.allclose(f[m+'_error_m'],original[m],atol=1e-7,rtol=0));checks.append({'check':'zero_removal_reproduces_prior','method':m,'pass':same})
                if not same:raise AssertionError('Full-roster baseline does not replay')
        frames.append(f);print('density',spec['experiment'],'survivors',len(survivor),flush=True)
    csvout(out/'predictions.csv.gz',pd.concat(frames,ignore_index=True));sm=pd.DataFrame(summaries);csvout(out/'per_draw_summary.csv',sm);csvout(out/'conditional_intervals.csv',pd.DataFrame(intervals));dump(out/'checks.json',checks)
    aggregated=[]
    for (count,method),g in sm.groupby(['retained_receivers','method'],sort=False):
        row={'retained_receivers':int(count),'method':method,'draw_count':len(g)}
        for col in ['n','coverage_fraction','median_m','full_survivor_median_m','removal_component_m','selection_component_m','over_1km_fraction']:
            row[col+'_median_across_draws']=float(g[col].median());row[col+'_min_across_draws']=float(g[col].min());row[col+'_max_across_draws']=float(g[col].max())
        aggregated.append(row)
    csvout(out/'across_draw_descriptions.csv',pd.DataFrame(aggregated))

def geography(c,pop,official,out):
    out.mkdir(exist_ok=True);ci=c['ci'];wis=pop['primary_working_ids'];boundary=float(np.median([c['msgs'][i].x for i in ci]));pools={'citywide':ci,'west':[i for i in ci if c['msgs'][i].x<boundary],'east':[i for i in ci if c['msgs'][i].x>=boundary]};budget=min(8000,len(pools['west']),len(pools['east']));caldefs=[];fits={};rowcounts=[]
    for seed in [3101,3102,3103]:
        for name,pool in pools.items():
            ids=random.Random(seed).sample(pool,budget);a0=bl.fit_a0([c['msgs'][i] for i in ids],official,4.7);fits[(seed,name)]=(ids,a0);caldefs.append(dict(seed=seed,region=name,working_ids=ids,csv_rows=[int(c['rows'][i]) for i in ids],a0=a0))
            for gid in official:
                n=sum(any(rx.gid==gid for rx in c['msgs'][i].receptions) for i in ids);rowcounts.append(dict(seed=seed,region=name,receiver=gid,calibration_receptions=n,intercept_available=gid in a0))
    common=set(official).intersection(*(set(v[1]) for v in fits.values()));roster=sorted(common,key=int);mp={g:official[g] for g in roster}
    tests={direction:[i for i in wis if (c['msgs'][i].x>=boundary if direction=='east' else c['msgs'][i].x<boundary) and get_case(c,i,mp) is not None] for direction in ['east','west']}
    defs=dict(boundary_utm_easting=boundary,pool_counts={k:len(v) for k,v in pools.items()},calibration_budget=budget,roster=roster,excluded_receiver_ids=sorted(set(official)-common,key=int),eval_working_ids=tests,parent_direction_counts={d:sum((c['msgs'][i].x>=boundary if d=='east' else c['msgs'][i].x<boundary) for i in wis) for d in tests},calibration_arms=caldefs)
    dump(out/'definitions.json',defs);csvout(out/'calibration_counts.csv',pd.DataFrame(rowcounts));frames=[];sm=[];cirows=[];checks=[]
    for seed in [3101,3102,3103]:
        for direction,test in tests.items():
            opposite='west' if direction=='east' else 'east';arms=[]
            for label,calreg in [('citywide','citywide'),('opposite',opposite)]:
                ids,a0=fits[(seed,calreg)]
                if {c['keys'][i] for i in ids}&{c['keys'][i] for i in test}:raise AssertionError('Calibration/evaluation content overlap')
                f=geo_predictions(c,test,mp,a0);fp=fingerprint(c,ids,test,roster)
                if not np.array_equal(f.csv_row_index0,fp.csv_row_index0):raise AssertionError('FP geometry identity mismatch')
                for col in fp.columns:
                    if col.startswith('FP_'):f[col]=fp[col]
                f['direction']=direction;f['seed']=seed;f['calibration_arm']=label;f['calibration_region']=calreg;f['calibration_n']=budget;f['experiment']=f'geo_{direction}_{seed}';frames.append(f);arms.append(f)
                for method in GEO_METHODS:sm.append(dict(experiment=f'geo_{direction}_{seed}',direction=direction,seed=seed,calibration_arm=label,calibration_region=calreg,method=method,calibration_n=budget,receivers=len(roster),parent_direction_n=defs['parent_direction_counts'][direction],coverage_fraction=len(f)/defs['parent_direction_counts'][direction],**stats(f[method+'_error_m']),nearest_database_median_m=float(f.FP_nearest_calibration_m.median()) if method=='FP_k3' else None))
            city,cross=arms
            if not city.csv_row_index0.equals(cross.csv_row_index0) or not city.selected_receivers.equals(cross.selected_receivers):raise AssertionError('Geographic arms not paired')
            same=np.array_equal(city[['WCL_raw_x','WCL_raw_y']].to_numpy(),cross[['WCL_raw_x','WCL_raw_y']].to_numpy());checks.append({'check':'raw_WCL_calibration_invariance','direction':direction,'seed':seed,'pass':same})
            if not same:raise AssertionError('Raw WCL changed with unused calibration')
            if seed==3101:
                joined=cross.copy();cols=[];pairs=[]
                for j,m in enumerate(GEO_METHODS):joined['city_'+m]=city[m+'_error_m'].to_numpy();cols.extend([m+'_error_m','city_'+m]);pairs.append((m+'_opposite_minus_citywide',2*j,2*j+1))
                cirows+=paired(joined,cols,pairs,f'geo_{direction}_{seed}',list(schemes(joined)))
            print('geography',direction,seed,'n',len(city),'roster',len(roster),'budget',budget,flush=True)
    csvout(out/'predictions.csv.gz',pd.concat(frames,ignore_index=True));summ=pd.DataFrame(sm);csvout(out/'summary.csv',summ);csvout(out/'primary_intervals.csv',pd.DataFrame(cirows));dump(out/'checks.json',checks);contrasts=[]
    for (direction,seed,method),f in summ.groupby(['direction','seed','method'],sort=False):
        a=f[f.calibration_arm=='opposite'].iloc[0];b=f[f.calibration_arm=='citywide'].iloc[0]
        contrasts.append(dict(direction=direction,seed=int(seed),method=method,n=int(a.n),citywide_median_m=b.median_m,opposite_median_m=a.median_m,median_change_pct=100*(a.median_m/b.median_m-1),citywide_p90_m=b.p90_m,opposite_p90_m=a.p90_m,p90_change_pct=100*(a.p90_m/b.p90_m-1)))
    csvout(out/'contrasts.csv',pd.DataFrame(contrasts))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,required=True);ap.add_argument('--part',choices=['all','density','geography'],default='all');a=ap.parse_args();start=time.time();protocol_hash=sha(ROOT/'protocol/STAGE_PROTOCOL.json');c=context(a.data);pop=json.loads((ROOT/'inputs/base_populations.json').read_text());official=loadmap(ROOT/'inputs/official33.json');a0=json.loads((ROOT/'inputs/base_official33_intercepts.json').read_text())
    if a.part in ['all','density']:density(c,pop,official,a0,ROOT/'results/density')
    if a.part in ['all','geography']:geography(c,pop,official,ROOT/'results/geography')
    dump(ROOT/'results'/f'execution_{a.part}.json',dict(complete=True,protocol_sha256=protocol_hash,data_sha256=sha(a.data),elapsed_seconds=time.time()-start,part=a.part));print('FINISHED',a.part,time.time()-start,flush=True)
if __name__=='__main__':main()
