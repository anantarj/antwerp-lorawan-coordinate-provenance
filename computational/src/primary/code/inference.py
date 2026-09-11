#!/usr/bin/env python3
"""Paired conditional percentile intervals and prespecified dependence sensitivities."""
from __future__ import annotations
import argparse, time
import numpy as np
import pandas as pd
from common import *
from benchmark import METHODS

REPS=6000;SEED=20260905

def schemes(f):
    return {'paired_messages':None,
            'spatial_500m':np.array([f'{int(np.floor(x/500))}:{int(np.floor(y/500))}' for x,y in zip(f.x,f.y)]),
            'spatial_1000m':np.array([f'{int(np.floor(x/1000))}:{int(np.floor(y/1000))}' for x,y in zip(f.x,f.y)]),
            'UTC_calendar_day':pd.to_datetime(f.rx_time,utc=True,format='mixed').dt.strftime('%Y-%m-%d').to_numpy()}

def median_draws(values,groups,reps=REPS):
    rng=np.random.default_rng(SEED);n=len(values);nb=None;blocks=None
    if groups is not None:
        keys,inv=np.unique(groups,return_inverse=True);nb=len(keys);blocks=[np.flatnonzero(inv==i) for i in range(nb)]
    draws=np.empty((reps,values.shape[1]));sizes=np.empty(reps,int)
    for i in range(reps):
        idx=rng.integers(0,n,n) if groups is None else np.concatenate([blocks[j] for j in rng.integers(0,nb,nb)])
        draws[i]=np.median(values[idx],axis=0);sizes[i]=len(idx)
    return draws,{'n_units':n if nb is None else nb,'draw_size_min':int(sizes.min()),'draw_size_max':int(sizes.max())}

def compare(ex,f,values,labels,pairs,out):
    if not np.isfinite(values).all() or len(f)!=len(values):raise ValueError('Invalid paired matrix')
    points=np.median(values,axis=0);res=[];saved={}
    for scheme,g in schemes(f).items():
        dr,stats=median_draws(values,g);saved[scheme]=dr
        for name,ia,ib in pairs:
            d=dr[:,ia]-dr[:,ib];r=dr[:,ia]/dr[:,ib];lo,hi=np.quantile(d,[.025,.975]);rl,rh=np.quantile(r,[.025,.975])
            res.append({'experiment':ex,'contrast':name,'numerator_arm':labels[ia],'denominator_arm':labels[ib],'scheme':scheme,'n_messages':len(values),'replicates':REPS,**stats,
                        'numerator_median_m':float(points[ia]),'denominator_median_m':float(points[ib]),'point_difference_m':float(points[ia]-points[ib]),'point_ratio':float(points[ia]/points[ib]),
                        'difference_low_m':float(lo),'difference_high_m':float(hi),'ratio_low':float(rl),'ratio_high':float(rh),
                        'numerator_worse_fraction':float(np.mean(values[:,ia]>values[:,ib])),'exact_ties':int(np.sum(values[:,ia]==values[:,ib])),
                        'nonpositive_difference_draws':int(np.sum(d<=0))})
        print(ex,scheme,flush=True)
    np.savez_compressed(out/f'{ex}_median_draws.npz',**saved)
    dump(out/f'{ex}_draw_columns.json',labels)
    return res

def main():
    ap=argparse.ArgumentParser();ap.parse_args();start=time.time();out=ROOT/'results/inference';out.mkdir(exist_ok=True)
    b=pd.read_csv(ROOT/'results/benchmark/geometric_predictions.csv.gz');fp=pd.read_csv(ROOT/'results/benchmark/fingerprint_predictions.csv.gz');res=[]
    for ex in ['primary33','no71']:
        f=b[(b.experiment==ex)&(b.assignment=='official')].sort_values('sample_rank0').reset_index(drop=True)
        a=b[(b.experiment==ex)&(b.assignment=='rssfit_stable')].sort_values('sample_rank0').reset_index(drop=True)
        p=fp[fp.experiment==ex].set_index('csv_row_index0').loc[f.csv_row_index0]
        if not f.csv_row_index0.equals(a.csv_row_index0) or not f.selected_receivers.equals(a.selected_receivers):raise ValueError('Assignment arms not paired')
        labels=[f'official:{m}' for m in METHODS]+[f'rssfit_stable:{m}' for m in METHODS]+['coordinate_independent:FP_k3']
        values=np.column_stack([f[[m+'_error_m' for m in METHODS]].to_numpy(),a[[m+'_error_m' for m in METHODS]].to_numpy(),p.FP_k3_error_m.to_numpy()])
        pairs=[(f'assignment:{m}',8+i,i) for i,m in enumerate(METHODS)]
        pairs += [(f'official_vs_raw:{m}',i,0) for i,m in enumerate(METHODS) if i>0]
        pairs += [('official_vs_raw:FP_k3',16,0)]
        res.extend(compare(ex,f,values,labels,pairs,out))
    # Stable common27 bridge has its own immutable historical evaluation population.
    f=pd.read_csv(ROOT/'results/prepared/common27_stable_bridge.csv')
    values=f[['rssfit_stable_error_m','official_error_m']].to_numpy()
    res.extend(compare('common27_bridge',f,values,['rssfit_stable:WCL_raw','official:WCL_raw'],[('assignment:WCL_raw',0,1)],out))
    t=pd.read_csv(ROOT/'results/temporal/predictions.csv.gz');tm=['WCL_raw','WCL_bc','ABS_mean','DIFF_median','MinMax']
    for ex in ['temporal_official_matched','temporal_official_no71']:
        f=t[(t.experiment==ex)&(t.calibration_arm=='early')].sort_values('sample_rank0').reset_index(drop=True)
        a=t[(t.experiment==ex)&(t.calibration_arm=='interleaved')].sort_values('sample_rank0').reset_index(drop=True)
        if not f.csv_row_index0.equals(a.csv_row_index0) or not f.selected_receivers.equals(a.selected_receivers):raise ValueError('Temporal arms not paired')
        values=np.column_stack([f[[m+'_error_m' for m in tm]],a[[m+'_error_m' for m in tm]]])
        labels=[f'early:{m}' for m in tm]+[f'interleaved:{m}' for m in tm]
        res.extend(compare(ex,f,values,labels,[(f'early_minus_interleaved:{m}',i,i+5) for i,m in enumerate(tm)],out))
    csvout(out/'paired_intervals.csv',pd.DataFrame(res));dump(out/'paired_intervals.json',res)
    dump(out/'execution.json',{'complete':True,'elapsed_seconds':time.time()-start,'replicates_per_scheme':REPS,'seed':SEED,'interval_records':len(res),
                              'scope':'Conditional on fitted maps/calibration; exploratory post-review comparisons; clusters are a dependence sensitivity, not proven independent sampling units; no multiplicity-adjusted discovery claim.'})
    print('FINISHED',len(res),time.time()-start,flush=True)
if __name__=='__main__':main()
