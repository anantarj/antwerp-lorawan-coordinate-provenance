#!/usr/bin/env python3
"""Descriptive aggregation of the fixed MV1 outputs; does not select models."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
from preflight import write_csv,write_json


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--results',required=True,type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    allreceivers=[];rss=[];geometry=[];comparisons=[];pairrows=[];down=[];profilesummary=[];runstats=[]
    arms=['CAT','CONST','NARROW','WIDE','NARROW_MS','WIDE_MS']
    compared=[('NARROW','CAT'),('WIDE','CAT'),('NARROW_MS','CAT'),('WIDE_MS','CAT'),
              ('NARROW','CONST'),('WIDE','CONST'),('NARROW_MS','CONST'),('WIDE_MS','CONST'),
              ('WIDE','NARROW'),('NARROW_MS','NARROW'),('WIDE_MS','WIDE'),('WIDE_MS','NARROW_MS')]
    for split in ['group80','space1000']:
        r=a.results/split;d=pd.read_csv(r/'receiver_results.csv',float_precision='round_trip')
        allreceivers.append(d);down.append(pd.read_csv(r/'downstream_summary.csv',float_precision='round_trip'))
        observations=pd.read_csv(r/'all_reception_predictions.csv.gz',float_precision='round_trip')
        for arm in arms:
            g=d[d.arm==arm].set_index('bs')
            for role,prefix in [('retained_fitting','retained_fitting'),('all_fitting','all_fitting'),('validation','validation')]:
                available=g[g[prefix+'_median_abs_db'].notna()]
                if role=='retained_fitting':o=observations[(observations.role=='fitting')&observations.retained_for_fitting]
                else:o=observations[observations.role==('fitting' if role=='all_fitting' else 'validation')]
                absolute=np.abs(o[arm+'_signed_residual_db'].dropna().to_numpy())
                rss.append({'split':split,'arm':arm,'observation_population':role,'receivers_scored':len(available),
                    'unweighted_receiver_median_of_MedAE_db':float(available[prefix+'_median_abs_db'].median()),
                    'unweighted_receiver_median_of_MAE_db':float(available[prefix+'_mean_abs_db'].median()),
                    'unweighted_receiver_median_of_P90AE_db':float(available[prefix+'_p90_abs_db'].median()),
                    'pooled_receptions_scored':len(absolute),'pooled_reception_MedAE_db':float(np.median(absolute)),
                    'pooled_reception_MAE_db':float(np.mean(absolute)),'pooled_reception_P90AE_db':float(np.quantile(absolute,.9)),
                    'minimum_receiver_support':int(available[prefix+'_n'].min()),'maximum_receiver_support':int(available[prefix+'_n'].max())})
            if arm in ['NARROW','WIDE','NARROW_MS','WIDE_MS']:
                g=g[g.fit_status=='available']
                geometry.append({'split':split,'arm':arm,'receivers_fitted':len(g),'catalogue_discrepancy_median_m':float(g.catalogue_discrepancy_m.median()),
                    'catalogue_discrepancy_p90_m':float(g.catalogue_discrepancy_m.quantile(.9)),
                    'boundary_points':int(g.on_boundary.astype(bool).sum()),'catalogue_points_outside_domain':int(g.catalogue_outside_domain.astype(bool).sum()),
                    'median_fitting_range_term_db':float(g.retained_range_term_db.median()),
                    'selected_run_cap_hits':int(g.selected_run_sweep_cap_with_improvement_count.sum())})
        for arm,ref in compared:
            x=d[d.arm==arm].set_index('bs');y=d[d.arm==ref].set_index('bs')
            for metric in ['training_loss_db','all_fitting_median_abs_db','validation_median_abs_db','catalogue_discrepancy_m']:
                shared=x[metric].notna()&y[metric].notna();delta=x.loc[shared,metric]-y.loc[shared,metric]
                if len(delta)==0:continue
                tol=1e-7 if metric.endswith('_m') else 1e-9
                comparisons.append({'split':split,'arm':arm,'reference':ref,'metric':metric,'paired_receivers':len(delta),'lower_n':int((delta<-tol).sum()),
                    'equal_within_tolerance_n':int((abs(delta)<=tol).sum()),'higher_n':int((delta>tol).sum()),
                    'unweighted_median_paired_difference':float(delta.median()),'difference_of_unweighted_medians':float(x.loc[shared,metric].median()-y.loc[shared,metric].median()),
                    'comparison_tolerance':tol,'interpretation':'descriptive; not significance or independent-receiver population inference'})
                for bs,v in delta.items():pairrows.append({'split':split,'bs':int(bs),'arm':arm,'reference':ref,'metric':metric,
                    'value':float(x.loc[bs,metric]),'reference_value':float(y.loc[bs,metric]),'paired_difference':float(v),
                    'validation_n':int(x.loc[bs,'validation_n']),'pre_filter_n':int(x.loc[bs,'pre_filter_n'])})
        p=pd.read_csv(r/'finite_domain_profiles.csv',float_precision='round_trip')
        for bs,g in p.groupby('bs'):
            first=g[g.point_rank0==0];end=g[g.point_rank0==20];origin=float(first.training_loss_db.iloc[0])
            profilesummary.append({'split':split,'bs':int(bs),'profile_points':len(g),'initializer_loss_db':origin,
                'constant_training_MAD_db':float(g.constant_training_mad_db.iloc[0]),'smallest_endpoint_loss_db':float(end.training_loss_db.min()),
                'largest_endpoint_loss_db':float(end.training_loss_db.max()),'lower_loss_endpoints_than_initializer_n':int((end.training_loss_db<origin-1e-9).sum()),
                'smaller_range_term_endpoints_than_initializer_n':int((end.range_term_db<float(first.range_term_db.iloc[0])-1e-9).sum()),
                'smallest_profile_loss_db':float(g.training_loss_db.min()),'all_finite_bounds_satisfied':bool(g.finite_bound_satisfied.all()),
                'scope':'prescheduled finite objective-only profiles; no fitted model is selected from these points'})
        st=pd.read_csv(r/'all_start_results.csv',float_precision='round_trip')
        complete=json.loads((r/'COMPLETE.json').read_text())
        runstats.append({'split':split,**complete,'maximum_calls_per_start':int(st.objective_calls.max()),
            'median_calls_per_start':float(st.objective_calls.median()),'all_runs_sweep_cap_hit_count':int(st.sweep_cap_with_improvement_count.sum()),
            'duplicate_projected_starts':int(st.duplicate_projected_start_of_rank0.notna().sum())})
    for name,data in [('RSSI_SUMMARIES.csv',rss),('GEOMETRY_SUMMARIES.csv',geometry),('PAIRED_ARM_COMPARISONS.csv',comparisons),
                      ('ALL_RECEIVER_COMPARISONS.csv',pairrows),('FINITE_PROFILE_SUMMARIES.csv',profilesummary)]:
        write_csv(a.out/name,pd.DataFrame(data))
    write_csv(a.out/'ALL_DOWNSTREAM_SUMMARIES.csv',pd.concat(down,ignore_index=True))
    write_csv(a.out/'ALL_RECEIVER_RESULTS.csv',pd.concat(allreceivers,ignore_index=True))
    write_json(a.out/'RUN_COUNTS.json',runstats)
    print('DESCRIPTIVE SUMMARIES WRITTEN',a.out)

if __name__=='__main__':main()
