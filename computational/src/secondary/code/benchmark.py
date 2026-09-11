#!/usr/bin/env python3
"""Primary native-official benchmark, matched RSSFIT and BS71 sensitivity.

Instrumentation observes scipy return objects without altering estimate selection.
All finite returned estimates, including unsuccessful termination, remain in errors.
"""
from __future__ import annotations
import argparse, collections, concurrent.futures, json, math, time
from pathlib import Path
import numpy as np
import pandas as pd
import scipy.optimize as opt
from common import *

METHODS=['WCL_raw','WCL_bc','ABS_mean','DIFF_median','HYBRID_mean','NLLS','Trilat','MinMax']

def scalar(x):
    if x is None:return None
    f=float(x);return f if np.isfinite(f) else None

def near_boundary(x,b):
    xmin,xmax,ymin,ymax=b
    return bool(x[0]<xmin+100 or x[0]>xmax-100 or x[1]<ymin+100 or x[1]>ymax-100)

def nlls_observed(g,q,raw,b):
    calls=[]; original=opt.minimize
    def capture(*args,**kwargs):
        index=len(calls);initial=np.asarray(args[1],float)
        base={'start_index0':index,'initial_x':float(initial[0]),'initial_y':float(initial[1]),'exception':None}
        try:
            res=original(*args,**kwargs)
        except Exception as ex:
            calls.append({**base,'exception':repr(ex),'success':False,'status':None,'loss':None,'finite':False,'x':None,'y':None,'near_boundary':None,'nit':None,'nfev':None,'message':str(ex)})
            raise
        point=np.asarray(res.x,float)
        calls.append({**base,'success':bool(res.success),'status':int(res.status),'loss':scalar(res.fun),'finite':bool(np.isfinite(point).all() and np.isfinite(res.fun)), 'x':float(point[0]),'y':float(point[1]),'near_boundary':near_boundary(point,b),'nit':int(res.nit),'nfev':int(res.nfev),'message':str(res.message)})
        return res
    opt.minimize=capture
    try:
        x,interior,count=ev.robust_nlls_localize(g,q,4.7,ev.wcl_estimate(g,raw),b,huber_c=1.345,n_starts=3,max_iter=120,grad_tol=1e-6,halton_seed=1)
    finally:opt.minimize=original
    best=None;loss=float('inf')
    for call in calls:
        if call['loss'] is not None and call['loss']<loss:
            best=call;loss=call['loss']
    for call in calls:call['selected']=best is call
    if best is not None:
        expected=np.clip([best['x'],best['y']],[b[0],b[2]],[b[1],b[3]])
        if not np.array_equal(x,expected):raise RuntimeError('Observed selection differs from unchanged NLLS selection')
    if bool(interior)==near_boundary(x,b):raise RuntimeError('Boundary flag discrepancy')
    stat={'nlls_selected_success':None if best is None else best['success'], 'nlls_selected_status':None if best is None else best['status'],
          'nlls_selected_loss':None if best is None else best['loss'],'nlls_selected_near_boundary':near_boundary(x,b),
          'nlls_any_start_success':any(z['success'] for z in calls),'nlls_unsuccessful_starts':sum(not z['success'] for z in calls),'nlls_exceptions':sum(z['exception'] is not None for z in calls),
          'nlls_no_selected_optimizer_result':best is None,'nlls_source_boundary_or_exception_start_count':int(count)}
    return x,stat,calls

def trilat_observed(g,q):
    original=ev.least_squares;results=[]
    def capture(*args,**kwargs):
        res=original(*args,**kwargs);results.append(res);return res
    ev.least_squares=capture
    try:x=ev.trilateration_joint_A0(g,q,4.7)
    finally:ev.least_squares=original
    if len(results)!=1:raise RuntimeError('Expected actual scipy trilateration, not hidden fallback')
    res=results[0]
    return x,{'trilat_success':bool(res.success),'trilat_status':int(res.status),'trilat_nfev':int(res.nfev),'trilat_cost':float(res.cost),'trilat_message':str(res.message)}

def evaluate_job(job):
    meta,g,raw,q,t,b=job
    g=np.asarray(g,float);raw=np.asarray(raw,float);q=np.asarray(q,float);t=np.asarray(t,float)
    estimates={};flags={}
    estimates['WCL_raw']=ev.wcl_estimate(g,raw);estimates['WCL_bc']=ev.wcl_estimate(g,q)
    estimates['ABS_mean']=bl.lattice(ev,g,q,4.7,'abs','mean')
    estimates['DIFF_median'],legacy,pairs=diff_location(g,q)
    flags['admitted_pairs']=pairs;flags['DIFF_empty_fallback']=pairs==0
    flags['DIFF_legacy_empty_error_m']=float(np.linalg.norm(legacy-t)) if pairs==0 else None
    estimates['HYBRID_mean']=bl.lattice(ev,g,q,4.7,'hybrid','mean')
    estimates['MinMax']=bl.minmax(g,q,4.7);flags['minmax_infeasible']=bl.minmax_infeasible(g,q,4.7)
    estimates['NLLS'],ns,starts=nlls_observed(g,q,raw,b);flags.update(ns)
    estimates['Trilat'],ts=trilat_observed(g,q);flags.update(ts)
    if not all(np.isfinite(x).all() for x in estimates.values()):raise ValueError(f'Nonfinite estimate: {meta}')
    out={**meta,**flags}
    for name,x in estimates.items():out[f'{name}_x']=float(x[0]);out[f'{name}_y']=float(x[1]);out[f'{name}_error_m']=float(np.linalg.norm(x-t))
    for row in starts:row.update({k:meta[k] for k in ['experiment','assignment','csv_row_index0','sample_rank0']})
    return out,starts

def fingerprint(c,db_ids,test_ids,roster):
    # Iteration order is frozen in saved db_ids and roster; no error-based tuning.
    ids=sorted(roster,key=int)
    def arr(wis):
        a=np.full((len(wis),len(ids)),-200.,dtype=float);pos=np.empty((len(wis),2));lookup={g:j for j,g in enumerate(ids)}
        for k,wi in enumerate(wis):
            m=c['msgs'][wi];pos[k]=m.x,m.y
            for rx in m.receptions:
                if rx.gid in lookup:a[k,lookup[rx.gid]]=rx.rssi
        return a,pos
    db,dy=arr(db_ids);qx,qy=arr(test_ids);an=(db**2).sum(1);rows=[]
    for lo in range(0,len(test_ids),100):
        q=qx[lo:lo+100];d=an[None,:]+(q**2).sum(1)[:,None]-2*(q@db.T)
        order=np.argsort(d,axis=1,kind='stable');idx=order[:,:3];xy=dy[idx].mean(1)
        near=np.sqrt(((qy[lo:lo+len(q),None,:]-dy[None,:,:])**2).sum(2)).min(1)
        for j,wi in enumerate(test_ids[lo:lo+len(q)]):
            dist=d[j,idx[j]];cut=dist[-1]
            rows.append({**metadata(c,wi),'FP_k3_x':xy[j,0],'FP_k3_y':xy[j,1],'FP_k3_error_m':float(np.linalg.norm(xy[j]-qy[lo+j])), 'FP_nearest_calibration_m':float(near[j]),
                'FP_neighbor_csv_rows':';'.join(str(int(c['rows'][db_ids[z]])) for z in idx[j]),'FP_neighbor_squared_distances':';'.join(str(float(v)) for v in dist),
                'FP_cutoff_tie_crossing':bool(np.sum(d[j]<cut)<3<np.sum(d[j]<=cut))})
    return pd.DataFrame(rows)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,required=True);ap.add_argument('--workers',type=int,default=4);ap.add_argument('--pilot',type=int,default=0);a=ap.parse_args()
    t0=time.time();c=context(a.data);prep=ROOT/'results/prepared';pop=json.loads((prep/'populations.json').read_text())
    off=loadmap(ROOT/'inputs/official33.json');rf=loadmap(prep/'rssfit_stable41.json');aoff=json.loads((prep/'official33_intercepts.json').read_text());arf=json.loads((prep/'rssfit41_baseline_intercepts.json').read_text())
    jobs=[];armdefs=[]
    for exp,wis,roster in [('primary33',pop['primary_working_ids'],set(off)),('no71',pop['no71_working_ids'],set(off)-{'71'})]:
        for tag,full,a0 in [('official',off,aoff),('rssfit_stable',rf,arf)]:
            mp={g:full[g] for g in sorted(roster,key=int)};b=bbox(mp)
            armdefs.append({'experiment':exp,'assignment':tag,'roster':sorted(roster,key=int),'bbox':b,'n':len(wis)})
            for rank,wi in enumerate(wis):
                g,raw,t,gids=get_case(c,wi,mp,a0);q=raw-np.array([a0[k] for k in gids])
                meta={'experiment':exp,'assignment':tag,'sample_rank0':rank,**metadata(c,wi),'selected_receivers':';'.join(gids),'support':len(gids),'raw_RSSI':';'.join(map(str,raw)),'corrected_RSSI':';'.join(map(str,q))}
                jobs.append((meta,g,raw,q,t,b))
    out=ROOT/'results'/('pilot' if a.pilot else 'benchmark');out.mkdir(parents=True,exist_ok=True)
    dump(out/'arm_definitions.json',armdefs)
    if a.pilot:jobs=jobs[:a.pilot]
    answers=[];starts=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=a.workers) as executor:
        for i,(answer,st) in enumerate(executor.map(evaluate_job,jobs,chunksize=8)):
            answers.append(answer);starts.extend(st)
            if (i+1)%250==0: print(f'{i+1}/{len(jobs)} geometric cases, {time.time()-t0:.1f}s',flush=True)
    frame=pd.DataFrame(answers)
    csvout(out/'geometric_predictions.csv.gz',frame);csvout(out/'nlls_start_records.csv.gz',pd.DataFrame(starts))
    if not a.pilot:
        fp=[]
        for exp,wis,roster in [('primary33',pop['primary_working_ids'],set(off)),('no71',pop['no71_working_ids'],set(off)-{'71'})]:
            f=fingerprint(c,pop['fingerprint_database_working_ids'],wis,roster);f['experiment']=exp;fp.append(f)
        fp=pd.concat(fp,ignore_index=True);csvout(out/'fingerprint_predictions.csv.gz',fp)
        sm=[]
        for (ex,tag),f in frame.groupby(['experiment','assignment'],sort=False):
            for method in METHODS:sm.append({'experiment':ex,'assignment':tag,'method':method,**summary(f[f'{method}_error_m'])})
        for ex,f in fp.groupby('experiment',sort=False):sm.append({'experiment':ex,'assignment':'coordinate_independent','method':'FP_k3',**summary(f.FP_k3_error_m)})
        csvout(out/'summary.csv',pd.DataFrame(sm))
        statuses=[]
        for (ex,tag),f in frame.groupby(['experiment','assignment'],sort=False):
            statuses.append({'experiment':ex,'assignment':tag,'n':len(f),'nlls_selected_unsuccessful':int((f.nlls_selected_success==False).sum()),'nlls_all_starts_unsuccessful':int((f.nlls_any_start_success==False).sum()),'nlls_selected_boundary':int(f.nlls_selected_near_boundary.sum()),'nlls_exception_count':int(f.nlls_exceptions.sum()),'nlls_total_unsuccessful_starts':int(f.nlls_unsuccessful_starts.sum()),'nlls_no_selected_result':int(f.nlls_no_selected_optimizer_result.sum()),'trilat_unsuccessful':int((f.trilat_success==False).sum()),'minmax_infeasible':int(f.minmax_infeasible.sum()),'DIFF_empty_pair_cases':int(f.DIFF_empty_fallback.sum())})
        dump(out/'solver_status_summary.json',statuses)
    dump(out/'execution.json',{'elapsed_seconds':time.time()-t0,'cases':len(answers),'nlls_start_records':len(starts),'workers':a.workers,'pilot':a.pilot,'complete':True})
    print('FINISHED',len(answers),time.time()-t0,flush=True)
if __name__=='__main__':main()
