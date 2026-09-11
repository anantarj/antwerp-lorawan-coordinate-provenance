#!/usr/bin/env python3
"""Independent row, formula, pairing and draw-contract checks for A4b outputs."""
import argparse,json,random
from pathlib import Path
import numpy as np
import pandas as pd
from common import *
from secondary_controls import GEO_METHODS

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,required=True);args=ap.parse_args();c=context(args.data);mp=loadmap(ROOT/'inputs/official33.json');a0=json.loads((ROOT/'inputs/base_official33_intercepts.json').read_text());pop=json.loads((ROOT/'inputs/base_populations.json').read_text());checks=[]
    def test(name,good,detail=None):
        checks.append(dict(check=name,pass_=bool(good),detail=detail))
        if not good:raise AssertionError(name)
    d=pd.read_csv(ROOT/'results/density/predictions.csv.gz');g=pd.read_csv(ROOT/'results/geography/predictions.csv.gz');defs=json.loads((ROOT/'results/geography/definitions.json').read_text());draws=json.loads((ROOT/'results/density/draw_definitions.json').read_text());sm=pd.read_csv(ROOT/'results/density/per_draw_summary.csv')
    test('census_and_calibration_membership',len(c['rows'])==55375 and len(c['ci'])==16612)
    test('density_33_predeclared_draws',len(draws)==33 and len(d)==33*2495)
    test('density_fp_is_finite_on_all_parent_rows',np.isfinite(d.FP_k3_error_m).all())
    test('density_missing_geometric_predictions_are_exact_ineligible_rows',np.array_equal(d.MinMax_error_m.isna(),~d.geometric_eligible))
    maxmm=0.;maxwcl=0.;maxerr=0.;fpchecks=0;maxfp=0.
    # Every MinMax estimate is re-evaluated from raw CSV RSSI and saved intercepts,
    # independently of the geometric estimator kernel.
    for spec in draws:
        f=d[d.experiment==spec['experiment']];test('density_parent_order_'+spec['experiment'],list(f.working_index0)==pop['primary_working_ids'])
        expected=sorted(mp,key=int) if spec['retained_receivers']==33 else sorted(random.Random(20260905+100*spec['retained_receivers']+spec['draw_index0']).sample(sorted(mp,key=int),spec['retained_receivers']),key=int)
        test('draw_identity_'+spec['experiment'],expected==spec['roster'])
        eligible=f[f.geometric_eligible]
        test('survivor_IDs_'+spec['experiment'],list(eligible.working_index0)==spec['eligible_working_ids'])
        for r in eligible.itertuples():
            ids=r.selected_receivers.split(';');raw=c['vals'][int(r.csv_row_index0),np.array(list(map(int,ids)))-1];xy=np.array([mp[z] for z in ids]);rad=10.**(-(raw-np.array([a0[z] for z in ids]))/47.)
            pred=((xy-rad[:,None]).max(0)+(xy+rad[:,None]).min(0))/2
            maxmm=max(maxmm,float(np.max(np.abs(pred-[r.MinMax_x,r.MinMax_y]))))
        # Independent exact squared-distance check for first and last query of every draw.
        cols=np.array(list(map(int,spec['roster'])))-1;dbrows=c['rows'][pop['fingerprint_database_working_ids']];db=c['vals'][dbrows[:,None],cols[None,:]]
        for r in [f.iloc[0],f.iloc[-1]]:
            q=c['vals'][int(r.csv_row_index0),cols];dist=((db-q)**2).sum(1);idx=np.argsort(dist,kind='stable')[:3]
            expected_rows=dbrows[idx];saved=[int(x) for x in str(r.FP_neighbor_csv_rows).split(';')];test('fingerprint_neighbor_IDs_'+spec['experiment']+'_'+str(int(r.csv_row_index0)),np.array_equal(expected_rows,saved))
            pts=np.array([[c['msgs'][c['row_to_work'][int(i)]].x,c['msgs'][c['row_to_work'][int(i)]].y] for i in expected_rows]);pos=pts.mean(0);maxfp=max(maxfp,float(np.max(np.abs(pos-[r.FP_k3_x,r.FP_k3_y]))));fpchecks+=1
    test('all_eligible_MinMax_positions_independently_recomputed',maxmm<1e-7,{'max_abs_difference_m':maxmm})
    test('independent_FP_positions',maxfp<1e-7,{'queries':fpchecks,'max_abs_difference_m':maxfp})
    test('per_draw_decomposition_identity',np.allclose(sm.removal_component_m+sm.selection_component_m,sm.total_displayed_change_m,atol=1e-7,rtol=0))
    for f,methods in [(d,['FP_k3','MinMax']),(g,GEO_METHODS)]:
        for m in methods:
            valid=f[m+'_error_m'].notna();a=f.loc[valid];err=np.hypot(a[m+'_x']-a.x,a[m+'_y']-a.y);maxerr=max(maxerr,float(np.max(np.abs(err-a[m+'_error_m']))))
    test('all_saved_errors_are_errors_of_saved_positions',maxerr<1e-7,{'maximum_discrepancy_m':maxerr})
    test('geographic_roster_constant_and_not_recovered29',len(defs['roster'])==29 and set(defs['roster'])!=set(loadmap(ROOT/'inputs/recovered29.json')))
    counts=pd.read_csv(ROOT/'results/geography/calibration_counts.csv');shared=set(counts.groupby('receiver').calibration_receptions.min().loc[lambda x:x>=10].index.astype(str));test('geographic_roster_is_calibration_intersection',shared==set(defs['roster']))
    for cal in defs['calibration_arms']:
        ids=cal['working_ids'];pool=c['ci'] if cal['region']=='citywide' else [i for i in c['ci'] if (c['msgs'][i].x<defs['boundary_utm_easting'] if cal['region']=='west' else c['msgs'][i].x>=defs['boundary_utm_easting'])]
        test('calibration_draw_'+str(cal['seed'])+'_'+cal['region'],random.Random(cal['seed']).sample(pool,defs['calibration_budget'])==ids)
        test('calibration_eval_content_disjoint_'+str(cal['seed'])+'_'+cal['region'],not {c['keys'][i] for i in ids}&{c['keys'][i] for v in defs['eval_working_ids'].values() for i in v})
    for (direction,seed),f in g.groupby(['direction','seed']):
        a=f[f.calibration_arm=='opposite'].reset_index(drop=True);b=f[f.calibration_arm=='citywide'].reset_index(drop=True)
        test('geographic_pairing_'+direction+str(seed),a.csv_row_index0.equals(b.csv_row_index0) and a.selected_receivers.equals(b.selected_receivers))
        test('raw_WCL_invariance_'+direction+str(seed),np.array_equal(a[['WCL_raw_x','WCL_raw_y']].to_numpy(),b[['WCL_raw_x','WCL_raw_y']].to_numpy()))
    for r in g.itertuples():
        ids=r.selected_receivers.split(';');raw=c['vals'][int(r.csv_row_index0),np.array(list(map(int,ids)))-1];w=10.**((raw-raw.max())/10.);pred=(w[:,None]*np.array([mp[z] for z in ids])).sum(0)/w.sum();maxwcl=max(maxwcl,float(np.max(np.abs(pred-[r.WCL_raw_x,r.WCL_raw_y]))))
    test('all_geographic_raw_WCL_positions_independently_recomputed',maxwcl<1e-7,{'max_abs_difference_m':maxwcl})
    test('geographic_no_unreported_missing_predictions',all(np.isfinite(g[m+'_error_m']).all() for m in GEO_METHODS))
    from inference import median_draws
    a=np.arange(40.,70.);v=np.column_stack([a+7,a]);dr,_=median_draws(v,None,reps=100);test('paired_additive_offset_control',np.allclose(dr[:,0]-dr[:,1],7,atol=1e-12))
    test('paired_identical_arm_control',np.array_equal(dr[:,1]-dr[:,1],np.zeros(100)))
    result={'passed':len(checks),'failed':sum(not x['pass_'] for x in checks),'checks':checks,'density_records':len(d),'geographic_records':len(g),'note':'Checks of source identity, membership, formulas and finite output. Not independent external replication or all-method reimplementation.'};dump(ROOT/'tests/VALIDATION.json',result);print('PASS',len(checks))
if __name__=='__main__':main()
