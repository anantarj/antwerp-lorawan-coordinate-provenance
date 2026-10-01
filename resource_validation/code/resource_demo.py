#!/usr/bin/env python3
"""Reconstruct the matched-survivor example from SAVED predictions.

No localization estimator is run. The deliberately unseparated comparison is
shown alongside matched population accounting, not substituted for it.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    a=argparse.ArgumentParser();a.add_argument('--baseline',required=True,type=Path);a.add_argument('--out',required=True,type=Path);a=a.parse_args()
    r=a.baseline.resolve();o=a.out.resolve()
    if o.is_relative_to(r):raise SystemExit('Output must not be inside baseline')
    o.mkdir(parents=True,exist_ok=False)
    p=r/'computational/results/density/predictions.csv.gz';s=r/'computational/results/density/per_draw_summary.csv'
    predictions=pd.read_csv(p);stored=pd.read_csv(s)
    primary=pd.read_csv(r/'computational/populations/official33_primary_rows.csv')
    expected_rows=list(primary.csv_row_index0)
    output=[];mismatches=[];largest_error=0.;largest_delta=0.
    for exp,g in predictions.groupby('experiment',sort=False):
        if list(g.csv_row_index0)!=expected_rows:raise AssertionError('Parent row/order mismatch: '+exp)
        if g.csv_row_index0.duplicated().any():raise AssertionError('Duplicate parent rows')
        mask=g.geometric_eligible.to_numpy(bool)
        for method in ['FP_k3','MinMax']:
            xyz=g.loc[mask,[method+'_x',method+'_y']].to_numpy()
            target=g.loc[mask,['x','y']].to_numpy()
            err=np.linalg.norm(xyz-target,axis=1)
            efile=g.loc[mask,method+'_error_m'].to_numpy()
            largest_error=max(largest_error,float(np.max(abs(err-efile))))
            if not np.isfinite(err).all():raise AssertionError('Nonfinite eligible position')
            full=g['full_'+method+'_error_m'].to_numpy()
            parent=float(np.median(full));survivor=float(np.median(full[mask]));reduced=float(np.median(err))
            row={'experiment':exp,'method':method,'parent_n':len(g),'survivors':int(mask.sum()),'retained_receivers':int(g.retained_receivers.iloc[0]),
                 'full_parent_median_m':parent,'full_survivor_median_m':survivor,'reduced_survivor_median_m':reduced,
                 'unseparated_change_m':reduced-parent,'selection_component_m':survivor-parent,'removal_component_m':reduced-survivor}
            residual=(row['removal_component_m']+row['selection_component_m'])-row['unseparated_change_m']
            if abs(residual)>1e-9:raise AssertionError('Additivity failure')
            original=stored[(stored.experiment==exp)&(stored.method==method)]
            if len(original)!=1:raise AssertionError('Stored summary not unique')
            original=original.iloc[0]
            fields={'full_parent_median_m':'full_parent_median_m','full_survivor_median_m':'full_survivor_median_m',
                    'reduced_survivor_median_m':'median_m','unseparated_change_m':'total_displayed_change_m',
                    'selection_component_m':'selection_component_m','removal_component_m':'removal_component_m'}
            for outfield,infield in fields.items():
                delta=abs(row[outfield]-float(original[infield]));largest_delta=max(largest_delta,delta)
                if delta>1e-7:mismatches.append({'experiment':exp,'method':method,'field':outfield,'delta':delta})
            if int(original['n'])!=int(mask.sum()):raise AssertionError('Summary survivor count mismatch')
            output.append(row)
    if mismatches:raise AssertionError(mismatches)
    pd.DataFrame(output).to_csv(o/'matched_survivor_reconstruction.csv',index=False)
    examples=[v for v in output if v['experiment']=='removal_23_0']
    receipt={'scope':'Recomputed errors from saved coordinates and all 66 method/draw summaries on original ordered 2495-row parent; no producer rerun.',
       'source_hashes':{'density_predictions':sha(p),'density_summary':sha(s),'primary_rows':sha(r/'computational/populations/official33_primary_rows.csv')},
       'parent_rows':2495,'experiments':int(predictions.experiment.nunique()),'method_draw_summaries_checked':len(output),
       'summary_mismatches':len(mismatches),'max_saved_error_recalculation_difference_m':largest_error,'max_summary_recalculation_difference_m':largest_delta,
       'worked_example':examples}
    (o/'RESOURCE_DEMO_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
