#!/usr/bin/env python3
"""Exploratory paired mean/p90 temporal sensitivities, all five methods."""
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
from pyproj import Transformer

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--stage',type=Path,required=True);ap.add_argument('--csv',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 p=pd.read_csv(a.stage/'results/temporal/predictions.csv.gz');d=pd.read_csv(a.csv,usecols=['Latitude','Longitude','RX Time']);tf=Transformer.from_crs(4326,32631,always_xy=True);x,y=tf.transform(d.Longitude.to_numpy(),d.Latitude.to_numpy());days=pd.to_datetime(d['RX Time'],utc=True,format='mixed').dt.strftime('%Y-%m-%d')
 methods=['WCL_raw','WCL_bc','ABS_mean','DIFF_median','MinMax'];e=p[(p.experiment=='temporal_official_matched')&(p.calibration_arm=='early')].sort_values('sample_rank0');r=p[(p.experiment=='temporal_official_matched')&(p.calibration_arm=='interleaved')].sort_values('sample_rank0');ids=e.csv_row_index0.to_numpy();assert np.array_equal(ids,r.csv_row_index0)
 E=e[[m+'_error_m' for m in methods]].to_numpy();R=r[[m+'_error_m' for m in methods]].to_numpy();A=np.column_stack([E,R]);out=[]
 for scheme in ['messages','spatial500','spatial1000','UTC_day']:
  if scheme=='messages':label=np.arange(len(ids))
  elif scheme=='UTC_day':label=days.iloc[ids].to_numpy()
  else:
   side=500 if scheme=='spatial500' else 1000;label=np.array([str(int(np.floor(x[i]/side)))+','+str(int(np.floor(y[i]/side))) for i in ids])
  unique,inv=np.unique(label,return_inverse=True);groups=[np.flatnonzero(inv==k) for k in range(len(unique))];rng=np.random.default_rng(20260905);draws={'mean':[],'p90':[]}
  for rep in range(6000):
   ix=rng.integers(0,len(ids),len(ids)) if scheme=='messages' else np.concatenate([groups[k] for k in rng.integers(0,len(groups),len(groups))])
   aa=A[ix];mean=np.mean(aa,axis=0);p90=np.quantile(aa,.9,axis=0);draws['mean'].append(mean[:5]-mean[5:]);draws['p90'].append(p90[:5]-p90[5:])
  for metric in ['mean','p90']:
   point_e=np.mean(E,axis=0) if metric=='mean' else np.quantile(E,.9,axis=0);point_r=np.mean(R,axis=0) if metric=='mean' else np.quantile(R,.9,axis=0);bounds=np.quantile(draws[metric],[.025,.975],axis=0)
   for j,m in enumerate(methods):out.append({'method':m,'metric':metric,'scheme':scheme,'n':len(ids),'clusters':len(groups),'early':float(point_e[j]),'interleaved':float(point_r[j]),'difference_m':float(point_e[j]-point_r[j]),'percent_change':float(100*(point_e[j]/point_r[j]-1)),'ci_low_m':float(bounds[0,j]),'ci_high_m':float(bounds[1,j]),'exploratory_not_multiplicity_adjusted':True})
 pd.DataFrame(out).to_csv(a.out/'exploratory_temporal_mean_p90_intervals.csv',index=False);print(pd.DataFrame(out).to_string(index=False))
if __name__=='__main__':main()
