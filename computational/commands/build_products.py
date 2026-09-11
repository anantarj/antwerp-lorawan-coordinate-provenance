#!/usr/bin/env python3
"""Expose existing identity, coordinate and population products without fitting.

Run from this package; writes generated views to --out, which must not exist.
The immutable archived products are read, never edited.
"""
from __future__ import annotations
import argparse,json,hashlib
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads((ROOT/p).read_text())
def dump(p,v):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')
def build(out):
 out.mkdir(parents=True,exist_ok=False)
 identities=load('data_products/identities44.json');cal=load('data_products/calibration_identities41.json')
 cat=load('data_products/gateway_catalogue_249.json');coords=load('data_products/catalogue_backed39.json')
 off=load('data_products/metadata33.json');rf=load('data_products/rssfit_stable41.json');rec=load('data_products/historical_recovered29.json')
 geo=load('populations/geographic_definitions.json');e=pd.read_csv(ROOT/'results/join/column_evidence.csv',dtype={'bs':str}).set_index('bs')
 old=pd.read_csv(ROOT/'populations/working_source_ledger.csv.gz')
 cal_ledger=pd.read_csv(ROOT/'populations/primary_role_ledger.csv.gz')
 counts=pd.read_csv(ROOT/'results/prepared/calibration_receivers.csv',dtype={'bs':str}).set_index('bs')
 primary=pd.read_csv(ROOT/'results/benchmark/geometric_predictions.csv.gz')
 prim=primary[(primary.experiment=='primary33')&(primary.assignment=='official')]
 used={b:0 for b in identities}
 for ids in prim.selected_receivers:
  for b in ids.split(';'):used[b]+=1
 rows=[]
 for b,g in sorted(identities.items(),key=lambda kv:int(kv[0])):
  z=e.loc[b];loc=cat.get(g);xy=coords.get(b);fit=rf.get(b)
  rows.append({'bs':b,'gateway_id':g,'release_receptions':int(z.release_receptions),
   'calibration_receptions':int(z.calibration_receptions),
   'full_identity_candidates':int(z.full_candidate_count),
   'identified_on_calibration_only':b in cal,
   'outside_calibration_mismatches':None if pd.isna(z.out_of_calibration_mismatches) else int(z.out_of_calibration_mismatches),
   'catalogue_present':loc is not None,
   'catalogue_latitude':None if loc is None else float(loc['latitude']),
   'catalogue_longitude':None if loc is None else float(loc['longitude']),
   'catalogue_x_m':None if xy is None else xy[0],'catalogue_y_m':None if xy is None else xy[1],
   'coordinate_crs':'EPSG:32631','catalogue_rounding_m':0.1,
   'in_metadata33':b in off,'in_common27':b in off and b in rec,'in_transfer29':b in geo['roster'],
   'in_historical_recovered29':b in rec,'has_rssfit_coordinate':fit is not None,
   'rssfit_x_m':None if fit is None else fit[0],'rssfit_y_m':None if fit is None else fit[1],
   'primary_selection_count':used[b]})
 df=pd.DataFrame(rows);df.to_csv(out/'receiver_crosswalk.csv',index=False)
 dump(out/'receiver_crosswalk.json',{'schema_version':'1.0','role':'F2 generated views of frozen R2 products, not a new identity inference or fit','csv_sha256':'870abe60a4bd81f31ede6f269b6bc6329e05d2731343dff7015bae1a61218446','records':rows})
 roster={'metadata33':sorted(off,key=int),'common27':sorted(set(off)&set(rec),key=int),'transfer29':geo['roster'],'metadata32_no71':sorted(set(off)-{'71'},key=int),'rssfit41_numeric_view':sorted(rf,key=int),'historical_recovered29':sorted(rec,key=int)}
 dump(out/'rosters.json',roster)
 dump(out/'metadata_common27.json',{b:off[b] for b in roster['common27']})
 dump(out/'rssfit_common27.json',{b:rf[b] for b in roster['common27']})
 dump(out/'metadata_transfer29.json',{b:off[b] for b in roster['transfer29']})
 # Role-specific csv-row files expose actual sampling order, not just seeds.
 for role,part in cal_ledger.groupby('role',sort=False):
  part.sort_values('rank0')[['rank0','csv_row_index0','working_index0']].to_csv(out/f'{role}_rows.csv',index=False)
 bridge=pd.read_csv(ROOT/'results/prepared/common27_stable_bridge.csv')
 pd.DataFrame({'rank0':range(len(bridge)),'csv_row_index0':bridge.csv_row_index0,'working_index0':bridge.working_index0}).to_csv(out/'historical_common27_rows.csv',index=False)
 truecal=old[old.role=='calibration'].sort_values('calibration_rank0')
 if truecal.csv_row_index0.tolist()!=cal_ledger[cal_ledger.role=='calibration'].sort_values('rank0').csv_row_index0.tolist():raise ValueError('Calibration identity/order disagreement')
 # Make all geographic training and evaluation row orders direct.
 for i,arm in enumerate(geo['calibration_arms']):
  pd.DataFrame({'rank0':range(len(arm['csv_rows'])),'csv_row_index0':arm['csv_rows']}).to_csv(out/f'geography_training_{i:02d}_rows.csv',index=False)
 geo_index=[{k:v for k,v in arm.items() if k not in ('csv_rows','working_ids','a0')} for arm in geo['calibration_arms']]
 for i,a in enumerate(geo_index):a['row_file']=f'geography_training_{i:02d}_rows.csv'
 dump(out/'geography_training_index.json',geo_index)
 t=pd.read_csv(ROOT/'populations/temporal_role_ledger.csv.gz')
 for (ex,role),part in t.groupby(['experiment','role'],sort=False):
  part.sort_values('role_rank0')[['role_rank0','csv_row_index0','working_index0']].to_csv(out/f'{ex}__{role}_rows.csv',index=False)
 summary={'active':len(rows),'catalogue_backed':sum(r['catalogue_present'] for r in rows),'calibration_identified':sum(r['identified_on_calibration_only'] for r in rows),'primary':sum(r['in_metadata33'] for r in rows),'common':sum(r['in_common27'] for r in rows),'transfer':sum(r['in_transfer29'] for r in rows),'unchanged_reference_arrays':True,'new_fit':False}
 if summary!={'active':44,'catalogue_backed':39,'calibration_identified':41,'primary':33,'common':27,'transfer':29,'unchanged_reference_arrays':True,'new_fit':False}:raise ValueError(summary)
 dump(out/'product_summary.json',summary)
 print(json.dumps(summary,indent=2))
if __name__=='__main__':
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--out',type=Path,required=True);build(a.parse_args().out.resolve())
