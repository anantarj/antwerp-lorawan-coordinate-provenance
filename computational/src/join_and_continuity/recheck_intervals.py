#!/usr/bin/env python3
"""Recompute six prior message-paired intervals independently from saved errors.
Also report descriptive nonmedian temporal summaries without inferential claims.
"""
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--stage',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 b=pd.read_csv(a.stage/'results/benchmark/geometric_predictions.csv.gz');t=pd.read_csv(a.stage/'results/temporal/predictions.csv.gz');old=pd.read_csv(a.stage/'results/inference/paired_intervals.csv');cases=[]
 f=b[(b.experiment=='primary33')&(b.assignment=='rssfit_stable')].sort_values('sample_rank0');g=b[(b.experiment=='primary33')&(b.assignment=='official')].sort_values('sample_rank0');assert np.array_equal(f.csv_row_index0,g.csv_row_index0)
 cases.append(('primary33','assignment:WCL_raw',f.WCL_raw_error_m.to_numpy(),g.WCL_raw_error_m.to_numpy()))
 f=t[(t.experiment=='temporal_official_matched')&(t.calibration_arm=='early')].sort_values('sample_rank0');g=t[(t.experiment=='temporal_official_matched')&(t.calibration_arm=='interleaved')].sort_values('sample_rank0');assert np.array_equal(f.csv_row_index0,g.csv_row_index0)
 desc=[]
 for m in ['WCL_raw','WCL_bc','ABS_mean','DIFF_median','MinMax']:
  v=f[m+'_error_m'].to_numpy();w=g[m+'_error_m'].to_numpy();cases.append(('temporal_official_matched','early_minus_interleaved:'+m,v,w))
  desc.append({'method':m,'n':len(v),'early_worse_fraction':float(np.mean(v>w)),'mean_early_m':float(v.mean()),'mean_interleaved_m':float(w.mean()),'p90_early_m':float(np.quantile(v,.9)),'p90_interleaved_m':float(np.quantile(w,.9)),'p95_early_m':float(np.quantile(v,.95)),'p95_interleaved_m':float(np.quantile(w,.95)),'no_new_nonmedian_inference':True})
 output=[]
 for ex,name,v,w in cases:
  rng=np.random.default_rng(20260905);dm=[];rr=[]
  for i in range(60):
   ix=rng.integers(len(v),size=(100,len(v)));mv=np.median(v[ix],axis=1);mw=np.median(w[ix],axis=1);dm.extend(mv-mw);rr.extend(mv/mw)
  dl,dh=np.quantile(dm,[.025,.975]);rl,rh=np.quantile(rr,[.025,.975]);saved=old[(old.experiment==ex)&(old.contrast==name)&(old.scheme=='paired_messages')].iloc[0];calculated=np.array([dl,dh,rl,rh]);recorded=saved[['difference_low_m','difference_high_m','ratio_low','ratio_high']].to_numpy(float);delta=float(np.max(np.abs(calculated-recorded)));assert delta<1e-8
  output.append({'experiment':ex,'contrast':name,'max_difference_from_archived_interval':delta,'difference_ci_low':float(dl),'difference_ci_high':float(dh),'ratio_ci_low':float(rl),'ratio_ci_high':float(rh)})
 (a.out/'independently_rechecked_intervals.json').write_text(json.dumps(output,indent=2)+'\n');pd.DataFrame(desc).to_csv(a.out/'descriptive_other_temporal_estimands.csv',index=False);print(pd.DataFrame(output).to_string(index=False));print(pd.DataFrame(desc).to_string(index=False))
if __name__=='__main__':main()
