#!/usr/bin/env python3
"""Verify selected-map decisions, cohort matching and summaries from row outputs.
This does not refit receivers. It deliberately uses statistics.median/mean and
explicit sorted lists rather than the producer's NumPy summary functions.
"""
from pathlib import Path
import argparse,json,hashlib,statistics,math,subprocess,sys
import pandas as pd

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def q90(x):
 y=sorted(x);t=.9*(len(y)-1);k=int(t);u=t-k
 return y[k]*(1-u)+y[min(k+1,len(y)-1)]*u

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 if a.out.exists():raise SystemExit('Refuse existing verification receipt')
 r=a.root/'results/task_selection';s=pd.read_csv(r/'ALL_CANDIDATE_SUMMARIES.csv');pol=pd.read_csv(r/'POLICY_OUTCOMES.csv')
 checks=[]
 def check(name,ok,**extra):
  checks.append({'check':name,'pass':bool(ok),**extra})
  if not ok:raise AssertionError(name)
 for e in json.loads((a.root/'checks/CODE_GATE.json').read_text())['files']:
  check('Code/protocol still matches execution gate '+e['path'],sha(a.root/e['path'])==e['sha256'])
 for split in ['group80','space1000']:
  frozen=json.loads((r/f'{split}_SELECTION_FROZEN.json').read_text())
  for policy,scores in frozen['scores'].items():
   ordered=['NARROW','WIDE','NARROW_MS','WIDE_MS'];low=min(scores.values());chosen=next(x for x in ordered if scores[x]<=low+1e-9)
   check('Deterministic selection '+split+' '+policy,chosen==frozen['selection'][policy])
  for role in ['validation','complement','old_primary']:
   df=pd.read_csv(r/f'{split}_{role}_PREDICTIONS.csv.gz')
   base=df[(df.arm=='CAT')&df.common_complete].csv_row_index0.tolist()
   for arm in ['CAT','NARROW','WIDE','NARROW_MS','WIDE_MS']:
    group=df[df.arm==arm];g=group[group.common_complete]
    check('Matched complete cohort '+split+' '+role+' '+arm,g.csv_row_index0.tolist()==base)
    check('Requests explicit '+split+' '+role+' '+arm,len(group)==int(s[(s.split==split)&(s.role==role)&(s.arm==arm)].iloc[0].requested_n))
    check('Unsupported predictions are missing '+split+' '+role+' '+arm,group.loc[~group.available,['pred_x','pred_y','error_m']].isna().all().all())
    errors=g.error_m.tolist();x=s[(s.split==split)&(s.role==role)&(s.arm==arm)].iloc[0]
    for k,val in [('median_error_m',statistics.median(errors)),('mean_error_m',statistics.fmean(errors)),('p90_error_m',q90(errors))]:
     check('Summary '+split+' '+role+' '+arm+' '+k,abs(float(x[k])-val)<=1e-7)
   if role!='validation':
    for _,row in pol[(pol.split==split)&(pol.role==role)].iterrows():
     check('Recorded policy map '+split+' '+role+' '+row.policy,row.chosen_map==frozen['selection'][row.policy])
     cand=s[(s.split==split)&(s.role==role)&(s.arm==row.chosen_map)].iloc[0]
     check('Policy matches unchanged candidate '+split+' '+role+' '+row.policy,abs(row.median_error_m-cand.median_error_m)<1e-7 and row.common_cohort_sha256==cand.common_cohort_sha256)
  # Target-based and pooled-RSSI policies MUST be reported as identical here.
  check('Pooled-RSSI tie is retained '+split,frozen['selection']['TASK_VAL']==frozen['selection']['VAL_RSSI_POOLED'])
 ledger=pd.read_csv(r/'SOURCE_ROLE_LEDGER.csv.gz')
 outer=ledger[ledger.PR4_role=='complement'];prior=ledger[ledger.PR4_role!='complement']
 for col in ['legacy_content_sha256','serialization_sha256','component_min_csv_row0','csv_row_index0']:
  check('Complement disjoint '+col,not(set(outer[col])&set(prior[col])))
 numerical=json.loads((r/'NUMERICAL_CHECKS.json').read_text())
 receipt={'status':'PASS','checks':len(checks),'failed':0,
 'alternate_scalar_centroid_predictions_checked':sum(x['scalar_predictions_checked'] for x in numerical),
 'max_alternate_centroid_position_difference_m':max(x['max_scalar_position_difference_m'] for x in numerical),
 'scope':'Row-level audit, alternative summary formulas, exact selected-map association, missingness, complement key disjointness and gate preservation; not fresh fitting or external replication.',
 'checks_detail':checks}
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(receipt,indent=2)+'\n');print('PASS',len(checks),'checks')

if __name__=='__main__':main()
