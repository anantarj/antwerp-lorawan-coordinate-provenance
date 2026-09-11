#!/usr/bin/env python3
"""Apply the previously used spatial/day sensitivity schemes to every bridge arm.
Post-review follow-up, not a prospectively registered confirmatory experiment.
"""
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
from pyproj import Transformer

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--bridge',type=Path,required=True);ap.add_argument('--csv',type=Path,required=True);a=ap.parse_args()
 p=pd.read_csv(a.bridge/'matched_temporal_bridge_predictions.csv.gz');d=pd.read_csv(a.csv,usecols=['Latitude','Longitude','RX Time']);tf=Transformer.from_crs(4326,32631,always_xy=True);x,y=tf.transform(d.Longitude.to_numpy(),d.Latitude.to_numpy());days=pd.to_datetime(d['RX Time'],utc=True,format='mixed').dt.strftime('%Y-%m-%d')
 methods=[s[:-8] for s in p if s.endswith('_error_m')];output=[]
 for mt in sorted(p['map'].unique()):
  e=p[(p['map']==mt)&(p.calibration=='early')].sort_values('rank0');r=p[(p['map']==mt)&(p.calibration=='interleaved')].sort_values('rank0');ids=e.csv_row_index0.to_numpy()
  assert np.array_equal(ids,r.csv_row_index0)
  E=e[[m+'_error_m' for m in methods]].to_numpy();R=r[[m+'_error_m' for m in methods]].to_numpy()
  for scheme in ['spatial500','spatial1000','UTC_day']:
   if scheme=='UTC_day':label=days.iloc[ids].to_numpy()
   else:
    side=500 if scheme=='spatial500' else 1000;gx=np.floor(np.asarray(x)[ids]/side).astype(int);gy=np.floor(np.asarray(y)[ids]/side).astype(int);label=np.array([str(xx)+','+str(yy) for xx,yy in zip(gx,gy)])
   unique,inv=np.unique(label,return_inverse=True);groups=[np.flatnonzero(inv==k) for k in range(len(unique))];rng=np.random.default_rng(20260905);diff=[];rat=[]
   for rep in range(6000):
    ix=np.concatenate([groups[k] for k in rng.integers(0,len(groups),len(groups))]);me=np.median(E[ix],axis=0);mr=np.median(R[ix],axis=0);diff.append(me-mr);rat.append(me/mr)
   ds=np.quantile(diff,[.025,.975],axis=0);rs=np.quantile(rat,[.025,.975],axis=0)
   for j,m in enumerate(methods):output.append({'map':mt,'method':m,'scheme':scheme,'clusters':len(groups),'n':len(ids),'difference_ci_low':float(ds[0,j]),'difference_ci_high':float(ds[1,j]),'ratio_ci_low':float(rs[0,j]),'ratio_ci_high':float(rs[1,j])})
 pd.DataFrame(output).to_csv(a.bridge/'matched_temporal_bridge_block_intervals.csv',index=False);print(pd.DataFrame(output).to_string(index=False))
if __name__=='__main__':main()
