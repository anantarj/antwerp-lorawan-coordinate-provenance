#!/usr/bin/env python3
"""Regenerate inspectable current table values from the frozen result records.

These CSV/Markdown views do not overwrite manuscript source or select a new result.
"""
from pathlib import Path
import argparse,json
import numpy as np
import pandas as pd
from _support import ROOT,dump

def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--out',type=Path,required=True);a=a.parse_args();a.out.mkdir(parents=True,exist_ok=False);made={}
 def put(name,f):
  f.to_csv(a.out/(name+'.csv'),index=False);made[name]=len(f)
 b=pd.read_csv(ROOT/'results/benchmark/summary.csv');iv=pd.read_csv(ROOT/'results/inference/paired_intervals.csv')
 put('M_Table2_assignment_intervals',iv[(iv.experiment=='primary33')&(iv.contrast=='assignment:WCL_raw')])
 primary=b[b.experiment=='primary33'].pivot(index='method',columns='assignment',values='median_m').reset_index();primary['ratio']=primary.rssfit_stable/primary.official
 put('M_Table3_benchmark',primary)
 g=pd.read_csv(ROOT/'results/geography/summary.csv');put('M_Table4_geography',g[g.seed==3101])
 d=pd.read_csv(ROOT/'results/density/across_draw_descriptions.csv');put('M_Table5_receiver_removal',d[['retained_receivers','method','draw_count','n_min_across_draws','n_max_across_draws','median_m_median_across_draws']])
 st=pd.DataFrame(json.loads((ROOT/'results/benchmark/solver_status_summary.json').read_text()));put('M_Table6_solver_status',st[st.experiment=='primary33'])
 rows=json.loads((ROOT/'data_products/receiver_crosswalk.json').read_text())['records'];put('S_TableS1_identity_crosswalk',pd.DataFrame(rows))
 counts=np.array([24117,12260,6540,3862,2603,1926,1358,2709]);put('S_reception_census',pd.DataFrame({'k':np.arange(3,11),'messages':counts,'at_least':np.cumsum(counts[::-1])[::-1]}))
 put('S_residuals',pd.DataFrame(json.loads((ROOT/'results/residual_version/summary.json').read_text())['records']))
 gi=pd.read_csv(ROOT/'results/geography/primary_intervals.csv');put('S_TableS6_1_geography_intervals',gi[gi.scheme=='spatial_1000m'])
 ds=pd.read_csv(ROOT/'results/density/per_draw_summary.csv');put('S_TableS6_2_six_receiver_draws',ds[ds.retained_receivers==6]);put('S_all_draw_removal_selection',ds)
 t=pd.read_csv(ROOT/'results/temporal/summary.csv');put('S_TableS6_3_temporal_medians',t[t.experiment=='temporal_official_matched'])
 put('S_TableS6_4_temporal_other_estimands',pd.read_csv(ROOT/'results/continuity/descriptive_other_temporal_estimands.csv'))
 dump(a.out/'TABLE_VIEW_RECEIPT.json',{'tables':made,'scope':'Reformatted current source values only; no new fitting or scientific selection.'});print(made)
if __name__=='__main__':main()
