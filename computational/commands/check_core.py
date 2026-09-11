#!/usr/bin/env python3
"""Independent raw-CSV population and frozen-map WCL replay after a fresh join.

No optimizer or receiver-coordinate fitting runs in this command. The original
CSV row order, original reception ordering and frozen assignments are preserved.
"""
from __future__ import annotations
import argparse,collections,json,random
from pathlib import Path
import numpy as np
import pandas as pd
from pyproj import Transformer
from _support import ROOT,dump,sha,HASHES

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--csv',type=Path,required=True);ap.add_argument('--join',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--mode',choices=['join','core'],default='core');a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 checks=[]
 def ck(name,good,detail=None):
  checks.append({'check':name,'pass':bool(good),'detail':detail})
  if not good:raise AssertionError(name+': '+str(detail))
 for filename in ['rebuilt_full_identities.json','rebuilt_calibration_identities.json','rebuilt_catalogue_all39.json','rebuilt_calibration_ge10_35.json','rebuilt_calibration_ge20_33.json','surplus_json_records.json']:
  x=json.loads((a.join/filename).read_text());y=json.loads((ROOT/'results/join'/filename).read_text());ck('fresh_join_'+filename,x==y)
 e=pd.read_csv(a.join/'column_evidence.csv');prior_e=pd.read_csv(ROOT/'results/join/column_evidence.csv')
 ck('complete_signature_evidence_matches',e.equals(prior_e))
 csum=json.loads((a.join/'construction_summary.json').read_text())
 ck('CSV_JSON_population_and_endpoint',csum['csv_rows']==130429 and csum['json_rows']==130430 and csum['csv_working_ge3']==55375 and csum['json_ge3']==55376 and csum['csv_count_distribution']['10']==2709 and csum['json_count_distribution']['10']==2709)
 off=json.loads((ROOT/'data_products/metadata33.json').read_text());rf=json.loads((ROOT/'data_products/rssfit_stable41.json').read_text())
 full=json.loads((a.join/'rebuilt_catalogue_all39.json').read_text())
 ck('all_frozen33_coordinates_rederived',all(off[b]==full[b] for b in off),{'n':len(off)})
 ck('stable41_map_unchanged',sha(ROOT/'data_products/rssfit_stable41.json')=='93e4509d1e7300b92a0a6b3dabbfab251237ea686e4cdd786986419b755f57d6')
 if a.mode=='join':
  dump(a.out/'checks.json',{'all_pass':True,'checks':checks,'mode':'join only; no localization'});return
 ck('CSV_original_hash',sha(a.csv)==HASHES['csv'])
 d=pd.read_csv(a.csv);raw=d[[f'BS {i}' for i in range(1,73)]].to_numpy(float);valid=np.isfinite(raw)&(raw>=-150)&(raw<=-20)
 wr=np.flatnonzero((valid.sum(1)>=3)&np.isfinite(d.Latitude)&np.isfinite(d.Longitude))
 led=pd.read_csv(ROOT/'populations/working_source_ledger.csv.gz').sort_values('working_index0')
 ck('working_source_rows_exact',np.array_equal(wr,led.csv_row_index0))
 order=list(map(int,wr));random.Random(1).shuffle(order);cal=order[:16612];pool=order[16612:]
 calrows=pd.read_csv(ROOT/'populations/calibration_rows.csv').sort_values('rank0').csv_row_index0.tolist()
 ck('ordered_calibration_exact',cal==calrows)
 tf=Transformer.from_crs(4326,32631,always_xy=True);x,y=tf.transform(d.Longitude.to_numpy(),d.Latitude.to_numpy());xy=np.column_stack([x,y])
 def content(i):return (round(float(x[i]),3),round(float(y[i]),3),tuple(sorted((str(j+1),round(float(raw[i,j]),3)) for j in np.flatnonzero(valid[i]))))
 ckeys={content(i) for i in cal};elig=[i for i in pool if valid[i,np.array(list(off),int)-1].sum()>=3]
 chosen=random.Random(9).sample(elig,2500);primary=[i for i in chosen if content(i) not in ckeys]
 expected=pd.read_csv(ROOT/'populations/official33_primary_rows.csv').sort_values('rank0').csv_row_index0.tolist()
 ck('primary_selection_recipe_and_order',primary==expected,{'eligible_complement':len(elig),'sampled':len(chosen),'after_exclusions':len(primary)})
 db=random.Random(33).sample(cal,8000);saved_db=pd.read_csv(ROOT/'populations/fingerprint_database_rows.csv').sort_values('rank0').csv_row_index0.tolist();ck('fingerprint_database_recipe_and_order',db==saved_db)
 # Exact reception traversal and fitted-input ordering, without fitting coordinates.
 by={}
 for i in cal:
  cols=list(np.flatnonzero(valid[i]));cols.sort(key=lambda j:-raw[i,j])
  for j in cols:by.setdefault(str(j+1),[]).append((i,float(raw[i,j]),float(x[i]),float(y[i])))
 rng=random.Random(1);fitrows=[];initrows=[];trav=[]
 for grank,(b,original) in enumerate(by.items()):
  sample=rng.sample(original,2000) if len(original)>2000 else original
  values=np.array([r[1] for r in sample]);thr=float(np.quantile(values,.75,method='linear'));keep=values>=thr
  retained=[r for r,k in zip(sample,keep) if k] if keep.sum()>=50 else sample
  v=np.array([r[1] for r in retained]);indices=np.argsort(-v,kind='stable')[:min(50,len(v))]
  trav.append({'receiver_rank0':grank,'bs':b,'calibration_receptions':len(original),'subsampled_receptions':len(sample),'quantile_threshold_dbm':thr,'filtered_receptions':len(retained),'strong_filter_used':bool(keep.sum()>=50)})
  for rank,(i,r,xx,yy) in enumerate(retained):fitrows.append({'bs':b,'receiver_rank0':grank,'retained_rank0':rank,'csv_row_index0':i,'rssi':r,'tx_x':xx,'tx_y':yy})
  for rank,j in enumerate(indices):
   i,r,xx,yy=retained[j];initrows.append({'bs':b,'initialization_rank0':rank,'retained_array_index0':int(j),'csv_row_index0':i,'rssi':r,'tx_x':xx,'tx_y':yy})
 init=pd.DataFrame(initrows);oldinit=pd.read_csv(ROOT/'results/prepared/rssfit_initialization_records.csv.gz',dtype={'bs':str})
 ck('initialization_row_and_RSSI_order_exact',np.array_equal(init[['bs','initialization_rank0','retained_array_index0','csv_row_index0','rssi']],oldinit[['bs','initialization_rank0','retained_array_index0','csv_row_index0','rssi']]))
 ck('initialization_projected_coordinates',np.allclose(init[['tx_x','tx_y']],oldinit[['tx_x','tx_y']],atol=1e-8,rtol=0))
 pd.DataFrame(trav).to_csv(a.out/'rssfit_receiver_traversal.csv',index=False)
 pd.DataFrame(fitrows).to_csv(a.out/'rssfit_ordered_fit_inputs.csv.gz',index=False,compression={'method':'gzip','mtime':0})
 # Recompute every raw-WCL case from CSV receptions, never trusting saved receiver strings.
 cases=pd.read_csv(ROOT/'results/benchmark/geometric_predictions.csv.gz');outputs=[];max_delta=0.;max_err=0.;same_map=0.
 for r in cases.itertuples():
  roster=set(off)-({'71'} if r.experiment=='no71' else set());cols=[j for j in np.flatnonzero(valid[r.csv_row_index0]) if str(j+1) in roster];cols.sort(key=lambda j:-raw[r.csv_row_index0,j]);cols=cols[:10]
  ids=[str(j+1) for j in cols];rss=raw[r.csv_row_index0,cols];mp=off if r.assignment=='official' else rf
  if ids!=r.selected_receivers.split(';') or not np.array_equal(rss,np.array(r.raw_RSSI.split(';'),float)):raise AssertionError('Source reception list differs')
  w=np.power(10.,(rss-rss.max())/10.);g=np.array([mp[b] for b in ids]);pos=(g*w[:,None]).sum(0)/w.sum();error=float(np.linalg.norm(pos-xy[r.csv_row_index0]))
  delta=float(np.linalg.norm(pos-[r.WCL_raw_x,r.WCL_raw_y]));max_delta=max(max_delta,delta);max_err=max(max_err,abs(error-r.WCL_raw_error_m))
  same_map=max(same_map,float(np.linalg.norm(pos-(g*w[:,None]).sum(0)/w.sum())))
  outputs.append({'experiment':r.experiment,'assignment':r.assignment,'sample_rank0':r.sample_rank0,'csv_row_index0':r.csv_row_index0,'selected_receivers':';'.join(ids),'WCL_raw_x':pos[0],'WCL_raw_y':pos[1],'WCL_raw_error_m':error})
 ck('raw_WCL_replayed_all_9976_cases',len(outputs)==9976 and max_delta<1e-7 and max_err<1e-7,{'maximum_position_difference_m':max_delta,'maximum_error_difference_m':max_err})
 ck('same_map_control_zero',same_map==0)
 f=pd.DataFrame(outputs);f.to_csv(a.out/'raw_WCL_replay.csv.gz',index=False,compression={'method':'gzip','mtime':0})
 summaries=[]
 for exp,part in f.groupby('experiment',sort=False):
  aa=part[part.assignment=='official'].sort_values('sample_rank0');bb=part[part.assignment=='rssfit_stable'].sort_values('sample_rank0')
  ck(exp+'_paired_row_and_receiver_identity',aa.csv_row_index0.tolist()==bb.csv_row_index0.tolist() and aa.selected_receivers.tolist()==bb.selected_receivers.tolist())
  summaries.append({'experiment':exp,'n':len(aa),'metadata_median_m':float(aa.WCL_raw_error_m.median()),'rssfit_median_m':float(bb.WCL_raw_error_m.median()),'ratio_of_medians':float(bb.WCL_raw_error_m.median()/aa.WCL_raw_error_m.median()),'rssfit_worse_count':int(np.sum(bb.WCL_raw_error_m.to_numpy()>aa.WCL_raw_error_m.to_numpy()))})
 dump(a.out/'replay_summary.json',summaries)
 dump(a.out/'checks.json',{'all_pass':True,'n_checks':len(checks),'checks':checks,'scope':'Fresh identity join/projection, independent population reconstruction, RSSFIT input selection only, frozen-map raw-centroid replay. No coordinate refit or non-WCL optimizer.'})
 print(json.dumps(summaries,indent=2));print('PASS',len(checks))
if __name__=='__main__':main()
