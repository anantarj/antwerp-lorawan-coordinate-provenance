#!/usr/bin/env python3
"""Check all-start prediction summaries and finite-profile ray geometry.

Post-execution verification only: this does not select a start or fit a model.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
from run_mv1 import load_inputs
from preflight import write_json


def main():
    ap=argparse.ArgumentParser()
    for k in ['baseline','pr1','csv','protocol','results','out']:ap.add_argument('--'+k,required=True,type=Path)
    a=ap.parse_args()
    if a.out.exists():raise SystemExit('Refusing overwrite')
    records=[];count=0;maxdiff=0.;maxray=0.
    for split in ['group80','space1000']:
        d=load_inputs(a.baseline,a.pr1,a.csv,a.protocol,split)
        st=pd.read_csv(a.results/split/'all_start_results.csv',float_precision='round_trip')
        for r in st.itertuples(index=False):
            bs=int(r.bs);prep=d['prepared'][bs];keep=prep['retained']
            # Independent prediction expression using stored training-only intercept.
            for name,wi in [('all_fitting',prep['allfit']),('validation',d['valwi'][d['wm'][d['valwi'],bs-1]])]:
                if not len(wi):
                    assert pd.isna(getattr(r,name+'_median_abs_db'))
                    continue
                xy=d['xy'][wi];rss=d['wv'][wi,bs-1]
                distance=np.hypot(xy[:,0]-r.x,xy[:,1]-r.y)
                residual=rss-(r.fitting_intercept_db-47*np.log10(distance+1.))
                vals={'median_abs_db':np.median(abs(residual)),'mean_abs_db':np.mean(abs(residual)),
                      'p90_abs_db':np.quantile(abs(residual),.9),'median_signed_db':np.median(residual)}
                for name2,v in vals.items():maxdiff=max(maxdiff,abs(float(v)-getattr(r,name+'_'+name2)))
            count+=1
        profiles=pd.read_csv(a.results/split/'finite_domain_profiles.csv',float_precision='round_trip')
        directions=[(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]
        lower,upper=d['wide']
        for bs,g in profiles.groupby('bs'):
            prep=d['prepared'][int(bs)];k=prep['retained'];rr=d['wv'][k,int(bs)-1];xy=d['xy'][k]
            ix=np.argsort(-rr,kind='stable')[:50];w=np.power(10.,rr[ix]/10.)
            origin=np.array([np.sum(w*xy[ix,0])/np.sum(w),np.sum(w*xy[ix,1])/np.sum(w)])
            for di,dir0 in enumerate(directions):
                direction=np.asarray(dir0,float);direction/=np.linalg.norm(direction)
                dist=min((upper[j]-origin[j])/direction[j] if direction[j]>0 else (lower[j]-origin[j])/direction[j] for j in range(2) if direction[j])
                endpoint=np.clip(origin+dist*direction,lower,upper)
                h=g[g.direction_rank0==di].sort_values('point_rank0')
                assert np.array_equal(h.point_rank0,range(21))
                expected=origin+np.linspace(0,1,21)[:,None]*(endpoint-origin)
                maxray=max(maxray,float(np.max(abs(expected-h[['x','y']].to_numpy()))))
        records.append({'split':split,'starts_checked':len(st),'ray_points_checked':len(profiles)})
    assert maxdiff<=1e-8 and maxray<=1e-7
    write_json(a.out,{'status':'PASS','all_start_prediction_summaries_checked':count,
        'maximum_absolute_start_metric_difference_db':maxdiff,'maximum_ray_point_coordinate_difference_m':maxray,
        'records':records,'scope':'Additional post-run checking of all starts, including nonwinning starts, and scheduled ray coordinates; no new experiment or model selection.'})
    print(json.dumps(json.loads(a.out.read_text()),indent=2))

if __name__=='__main__':main()
