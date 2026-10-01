#!/usr/bin/env python3
"""Describe all pre-existing receiver-removal draws; no new estimator runs.

Reads PR1's already-verified reconstructed summaries. The sign comparison uses
an explicit numerical-zero tolerance; it is not a significance test or a rate
estimate for independent deployments.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd
from resource_contract import sha256_file


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--pr1',type=Path,required=True); ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args(); out=a.out.resolve()
    if out.is_relative_to(a.pr1.resolve()): raise ValueError('Output inside PR1')
    out.mkdir(parents=True,exist_ok=False)
    p=a.pr1/'results/resource_demo/matched_survivor_reconstruction.csv'
    receipt_path=a.pr1/'results/resource_demo/RESOURCE_DEMO_RECEIPT.json'
    prior=json.loads(receipt_path.read_text())
    if prior['method_draw_summaries_checked']!=66 or prior['summary_mismatches']!=0:
        raise ValueError('Prior evidence receipt differs')
    d=pd.read_csv(p)
    if len(d)!=66 or d[['experiment','method']].duplicated().any(): raise ValueError('Record set differs')
    baseline=d[d.retained_receivers==33]
    if len(baseline)!=2:raise ValueError('Expected two full-roster controls')
    d=d[d.retained_receivers<33].copy()
    tol=1e-7
    def sign(x):return np.where(x>tol,1,np.where(x< -tol,-1,0))
    d['unseparated_sign']=sign(d.unseparated_change_m)
    d['within_survivor_sign']=sign(d.removal_component_m)
    d['sign_reversal']=d.unseparated_sign*d.within_survivor_sign==-1
    d['selection_absolute_exceeds_removal']=np.abs(d.selection_component_m)>np.abs(d.removal_component_m)+tol
    residual=d.unseparated_change_m-d.selection_component_m-d.removal_component_m
    if abs(residual).max()>tol:raise ValueError('Stored telescoping account fails')
    d.to_csv(out/'ALL_64_DIRECTION_RECORDS.csv',index=False)
    reversal=d[d.sign_reversal]
    reversal.to_csv(out/'SIGN_REVERSAL_RECORDS.csv',index=False)
    summary=[]
    for method,g in d.groupby('method',sort=False):
        if len(g)!=32:raise ValueError('Expected 32 draws per method')
        summary.append({'method':method,'draws':len(g),
         'opposite_displayed_and_within_survivor_signs':int(g.sign_reversal.sum()),
         'selection_absolute_exceeds_removal':int(g.selection_absolute_exceeds_removal.sum()),
         'apparent_improvement_with_within_survivor_deterioration':int(((g.unseparated_sign<0)&(g.within_survivor_sign>0)).sum()),
         'apparent_deterioration_with_within_survivor_improvement':int(((g.unseparated_sign>0)&(g.within_survivor_sign<0)).sum())})
    example=d[(d.experiment=='removal_16_4')&(d.method=='FP_k3')].to_dict('records')
    record={'scope':'New descriptive aggregation of all 64 reduced-roster method/draw summaries previously reconstructed and checked in PR1; no new fitting, localization or bootstrap.',
      'numerical_zero_tolerance_m':tol,'method_summaries':summary,
      'total_sign_reversals':int(d.sign_reversal.sum()),
      'reversal_survivor_counts':list(map(int,reversal.survivors)),
      'worked_example_16_4_fingerprint':example,
      'input_hashes':{p.name:sha256_file(p),receipt_path.name:sha256_file(receipt_path)},
      'warning':'Overlapping draws are not independent experiments; sign is not statistical significance. Tiny survivor strata remain explicit, not evidence of general frequency.'}
    (out/'SELECTION_DIRECTION_RECEIPT.json').write_text(json.dumps(record,indent=2,allow_nan=False)+'\n')
    print(json.dumps(record,indent=2))

if __name__=='__main__':main()
