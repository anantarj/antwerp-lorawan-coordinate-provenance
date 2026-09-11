#!/usr/bin/env python3
"""Compare already-frozen new identities to legacy artifacts; never fit identities."""
import argparse,hashlib,json
from pathlib import Path
import pandas as pd
from pyproj import Transformer

def main():
 p=argparse.ArgumentParser();p.add_argument('--join',type=Path,required=True);p.add_argument('--legacy',type=Path,required=True);p.add_argument('--catalogue',type=Path,required=True);p.add_argument('--direct',type=Path,required=True);a=p.parse_args()
 full=json.loads((a.join/'rebuilt_full_identities.json').read_text());cal=json.loads((a.join/'rebuilt_calibration_identities.json').read_text());old=json.loads(a.legacy.read_text());cat=json.loads(a.catalogue.read_text());direct=json.loads(a.direct.read_text());df=pd.read_csv(a.join/'column_evidence.csv',dtype={'bs':str}).set_index('bs')
 tf=Transformer.from_crs(4326,32631,always_xy=True);derived={};records=[]
 for bs,eui in sorted(full.items(),key=lambda kv:int(kv[0])):
  loc=cat.get(eui);xy=None
  if loc:
   x,y=tf.transform(loc['longitude'],loc['latitude']);xy=[round(x,1),round(y,1)];derived[bs]=xy
  records.append({'bs':bs,'eui':eui,'catalogue_present':loc is not None,'calibration_identity_available':bs in cal,'calibration_receptions':int(df.loc[bs,'calibration_receptions']),'legacy_roster':bs in old,'legacy_identity_matches':old[bs][0]==eui if bs in old else None,'legacy_direct_coordinate_matches':direct[bs]==xy if bs in direct else None})
 r={'frozen_join_sha256':hashlib.sha256((a.join/'rebuilt_full_identities.json').read_bytes()).hexdigest(),'legacy_assignments':len(old),'legacy_matching_identities':sum(old[b][0]==full.get(b) for b in old),'legacy_identities_available_from_calibration_only':sum(old[b][0]==cal.get(b) for b in old),'legacy_direct_coordinates_equal':sum(direct[b]==derived.get(b) for b in direct),'full_catalogue_backed_identities':len(derived),'catalogue_backed_and_calibration_ge10':sum(z['catalogue_present'] and z['calibration_receptions']>=10 for z in records),'catalogue_backed_and_calibration_ge20':sum(z['catalogue_present'] and z['calibration_receptions']>=20 for z in records),'additional_catalogue_backed_columns':sorted(set(derived)-set(old),key=int),'historic_agreement_and_vote_statistics_reproduced':False,'existing_benchmark_roster_changed':False}
 pd.DataFrame(records).to_csv(a.join/'legacy_comparison_and_coverage.csv',index=False)
 (a.join/'rebuilt_catalogue_all_available_not_benchmark_default.json').write_text(json.dumps(derived,indent=2,sort_keys=True)+'\n')
 (a.join/'rebuilt_reference_same_legacy33.json').write_text(json.dumps({b:derived[b] for b in direct},indent=2,sort_keys=True)+'\n')
 (a.join/'legacy_comparison.json').write_text(json.dumps(r,indent=2,sort_keys=True)+'\n');print(json.dumps(r,indent=2));print(pd.DataFrame(records).to_string(index=False))
if __name__=='__main__':main()
