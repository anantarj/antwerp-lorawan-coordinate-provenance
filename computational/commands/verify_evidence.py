#!/usr/bin/env python3
"""Verify copied bytes, generated crosswalks, saved predictions and resample arrays.

This does not rerun a receiver fit, a localization optimizer, or raw CSV/JSON join.
Use paper_a.py core, primary and secondary for those separate execution scopes.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
from _support import ROOT,dump,sha
METHODS=['WCL_raw','WCL_bc','ABS_mean','DIFF_median','HYBRID_mean','NLLS','Trilat','MinMax']
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);checks=[]
 def ck(k,b,detail=None):
  checks.append({'check':k,'pass':bool(b),'detail':detail})
  if not b:raise AssertionError(k+': '+str(detail))
 manifest=json.loads((ROOT/'MANIFEST.json').read_text())
 bad=[r['path'] for r in manifest['files'] if not (ROOT/r['path']).is_file() or sha(ROOT/r['path'])!=r['sha256']]
 ck('package_manifest_all_files',not bad,{'n_files':len(manifest['files']),'bad':bad})
 origins=json.loads((ROOT/'provenance/SOURCE_COPY_INDEX.json').read_text())
 bad=[r['path'] for r in origins if not (ROOT/r['path']).is_file() or sha(ROOT/r['path'])!=r['sha256']]
 ck('copied_source_bytes_unchanged',not bad,{'n_files':len(origins),'bad':bad})
 identities=json.loads((ROOT/'data_products/identities44.json').read_text());cf=json.loads((ROOT/'data_products/calibration_identities41.json').read_text())
 rows=json.loads((ROOT/'data_products/receiver_crosswalk.json').read_text())['records'];table=pd.read_csv(ROOT/'data_products/receiver_crosswalk.csv',dtype={'bs':str,'gateway_id':str})
 off=json.loads((ROOT/'data_products/metadata33.json').read_text());fit=json.loads((ROOT/'data_products/rssfit_stable41.json').read_text());cat=json.loads((ROOT/'data_products/catalogue_backed39.json').read_text())
 ck('all_44_identity_rows_and_bijection',len(rows)==44 and len(set(x['gateway_id'] for x in rows))==44 and {r['bs']:r['gateway_id'] for r in rows}==identities)
 ck('CSV_identity_columns_preserve_strings',table[['bs','gateway_id']].to_dict('records')==[{k:r[k] for k in ['bs','gateway_id']} for r in rows])
 ck('coordinate_coverage_39_and_primary_33',sum(r['catalogue_present'] for r in rows)==39 and {r['bs'] for r in rows if r['in_metadata33']}==set(off))
 ck('calibration_only33_and_missingness_not_invented',all(cf[r['bs']]==r['gateway_id'] for r in rows if r['in_metadata33']) and all(r['catalogue_x_m'] is None and r['catalogue_y_m'] is None for r in rows if not r['catalogue_present']))
 ck('full_primary_projection_exact',{b:fit[b] for b in off}==json.loads((ROOT/'data_products/rssfit33.json').read_text()))
 ck('reference33_is_catalogue_projection',all(off[b]==cat[b] for b in off))
 source=(ROOT/'src/primary/snapshots/deltamesh_antwerp_eval_v10_fixed_080826.py').read_text();stable=(ROOT/'src/primary/code/evaluator_stable.py').read_text()
 ck('only_stable_sort_evaluator_patch',source.count('order = np.argsort(-rssi)')==1 and stable==source.replace('order = np.argsort(-rssi)','order = np.argsort(-rssi, kind="stable")'))
 b=pd.read_csv(ROOT/'results/benchmark/geometric_predictions.csv.gz');fp=pd.read_csv(ROOT/'results/benchmark/fingerprint_predictions.csv.gz');st=pd.read_csv(ROOT/'results/benchmark/nlls_start_records.csv.gz');sm=pd.read_csv(ROOT/'results/benchmark/summary.csv')
 ck('geometric_cases_and_all_starts',len(b)==9976 and len(st)==29928 and st.groupby(['experiment','assignment','csv_row_index0']).selected.sum().eq(1).all())
 poserr=max(float(np.max(np.abs(np.hypot(b[m+'_x']-b.x,b[m+'_y']-b.y)-b[m+'_error_m']))) for m in METHODS)
 ck('all_geometric_saved_errors_match_positions',poserr<1e-7,{'max_difference_m':poserr})
 maxw=0.
 for r in b.itertuples():
  mp=off if r.assignment=='official' else fit;rs=np.array(r.raw_RSSI.split(';'),float);w=np.power(10,(rs-rs.max())/10);g=np.array([mp[i] for i in r.selected_receivers.split(';')]);z=w@g/w.sum();maxw=max(maxw,float(np.linalg.norm(z-[r.WCL_raw_x,r.WCL_raw_y])))
 ck('raw_WCL_formula_from_saved_receptions_all_cases',maxw<1e-7,{'max_position_delta_m':maxw})
 summary_error=0.
 for r in sm.itertuples():
  ff=fp[fp.experiment==r.experiment] if r.method=='FP_k3' else b[(b.experiment==r.experiment)&(b.assignment==r.assignment)]
  v=ff[r.method+'_error_m'];summary_error=max(summary_error,abs(float(v.median())-r.median_m),abs(float(v.quantile(.9))-r.p90_m),abs(float(v.quantile(.95))-r.p95_m))
  if len(v)!=r.n:raise AssertionError('Summary count changed')
 ck('all_primary_summaries_recomputed',summary_error<1e-7,{'max_difference_m':summary_error,'rows':len(sm)})
 for ex in ['primary33','no71']:
  x=b[(b.experiment==ex)&(b.assignment=='official')].sort_values('sample_rank0');y=b[(b.experiment==ex)&(b.assignment=='rssfit_stable')].sort_values('sample_rank0')
  ck(ex+'_row_RSSI_receiver_pairing',np.array_equal(x[['csv_row_index0','raw_RSSI','selected_receivers']],y[['csv_row_index0','raw_RSSI','selected_receivers']]))
 counts=[]
 for (ex,tag),f in b.groupby(['experiment','assignment']):
  starts=st[(st.experiment==ex)&(st.assignment==tag)];selected=starts[starts.selected]
  ck(ex+'_'+tag+'_optimizer_statuses',int((~selected.success).sum())==int((~f.nlls_selected_success).sum()) and int(selected.near_boundary.sum())==int(f.nlls_selected_near_boundary.sum()))
  mask=f.DIFF_empty_fallback;ck(ex+'_'+tag+'_DIFF_empty_policy',np.array_equal(f.loc[mask,'DIFF_median_error_m'],f.loc[mask,'WCL_bc_error_m']))
 # All interval endpoints can be recomputed from the actual saved paired draw arrays.
 iv=pd.read_csv(ROOT/'results/inference/paired_intervals.csv');maxci=0.;nc=0
 for ex,f in iv.groupby('experiment',sort=False):
  labels=json.loads((ROOT/f'results/inference/{ex}_draw_columns.json').read_text())
  with np.load(ROOT/f'results/inference/{ex}_median_draws.npz',allow_pickle=False) as arr:
   for r in f.itertuples():
    z=arr[r.scheme];ia=labels.index(r.numerator_arm);ib=labels.index(r.denominator_arm)
    dl,dh=np.quantile(z[:,ia]-z[:,ib],[.025,.975]);rl,rh=np.quantile(z[:,ia]/z[:,ib],[.025,.975])
    maxci=max(maxci,abs(dl-r.difference_low_m),abs(dh-r.difference_high_m),abs(rl-r.ratio_low),abs(rh-r.ratio_high));nc+=1
 ck('interval_limits_from_saved_paired_draws',maxci<1e-7,{'interval_records':nc,'max_difference':maxci})
 # Secondary saved-position/error checks, and exact per-draw accounting.
 for folder,methods in [('geography',['FP_k3','WCL_raw','WCL_bc','ABS_mean','DIFF_median','MinMax']),('density',['FP_k3','MinMax']),('temporal',['WCL_raw','WCL_bc','ABS_mean','DIFF_median','MinMax'])]:
  frame=pd.read_csv(ROOT/f'results/{folder}/predictions.csv.gz');mx=0.
  for m in methods:
   f=frame[frame[m+'_error_m'].notna()];mx=max(mx,float(np.max(np.abs(np.hypot(f[m+'_x']-f.x,f[m+'_y']-f.y)-f[m+'_error_m']))))
  ck(folder+'_saved_errors_recomputed',mx<1e-7,{'rows':len(frame),'max_difference_m':mx})
 density=pd.read_csv(ROOT/'results/density/per_draw_summary.csv')
 ck('all_removal_selection_decompositions',np.allclose(density.removal_component_m+density.selection_component_m,density.total_displayed_change_m,atol=1e-7,rtol=0),{'draw_method_rows':len(density)})
 from scipy.stats import kurtosis
 res=pd.read_csv(ROOT/'results/residual_version/matched_links.csv.gz');rs=json.loads((ROOT/'results/residual_version/summary.json').read_text())['records']
 ck('residual_link_identity',len(res)==69988 and not res.duplicated(['csv_row_index0','receiver']).any())
 for row,col in zip(rs,['official_residual_db','rssfit_stable_residual_db']):
  ck(row['assignment']+'_moments',abs(kurtosis(res[col],fisher=True,bias=True)-row['excess_kurtosis'])<1e-9 and abs(np.std(res[col])-row['sd_db'])<1e-9)
 index=json.loads((ROOT/'table_figure_index/INDEX.json').read_text())
 ck('every_retained_table_and_figure_path_exists',all((ROOT/path).is_file() for rec in index['records'] for path in rec['evidence_files']))
 dump(a.out/'checks.json',{'all_pass':True,'n_checks':len(checks),'checks':checks,'scope':'Packaged-byte integrity and saved-evidence formula/summary checks. No claim of raw-data replay, new coordinate fit, or optimizer execution in this command.'})
 print('PASS',len(checks),'checks; retained inputs unchanged')
if __name__=='__main__':main()
