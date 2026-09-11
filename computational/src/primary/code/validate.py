#!/usr/bin/env python3
"""Executable integrity, identity, observation and fallback tests for the stage."""
from __future__ import annotations
import argparse, collections, json, random
from pathlib import Path
import numpy as np
import pandas as pd
from common import *
from benchmark import nlls_observed,trilat_observed,near_boundary,METHODS


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,required=True);a=ap.parse_args();checks={}
    def check(name,ok,detail=None):
        checks[name]={'pass':bool(ok),'detail':detail}
        if not ok:raise AssertionError(name+': '+str(detail))
    expected=json.loads((ROOT/'protocol/input_sha256.json').read_text())
    check('source_and_input_copies_unchanged',all(sha(ROOT/p)==h for p,h in expected.items()),{'files':len(expected)})
    source=(ROOT/'snapshots/deltamesh_antwerp_eval_v10_fixed_080826.py').read_text()
    stable=(ROOT/'code/evaluator_stable.py').read_text()
    check('stable_evaluator_is_only_declared_one_line_patch',source.count('order = np.argsort(-rssi)')==1 and stable==source.replace('order = np.argsort(-rssi)','order = np.argsort(-rssi, kind="stable")'))
    b=pd.read_csv(ROOT/'results/benchmark/geometric_predictions.csv.gz')
    fp=pd.read_csv(ROOT/'results/benchmark/fingerprint_predictions.csv.gz')
    t=pd.read_csv(ROOT/'results/temporal/predictions.csv.gz')
    st=pd.read_csv(ROOT/'results/benchmark/nlls_start_records.csv.gz')
    check('all_predicted_errors_finite',np.isfinite(b[[m+'_error_m' for m in METHODS]].to_numpy()).all())
    check('all_solver_starts_retained',len(st)==3*len(b),{'cases':len(b),'starts':len(st)})
    check('one_selected_optimizer_result_per_case',st.groupby(['experiment','assignment','csv_row_index0']).selected.sum().eq(1).all())
    anomaly=[];diags=[]
    for ex in ['primary33','no71']:
        aa=b[(b.experiment==ex)&(b.assignment=='official')].sort_values('sample_rank0')
        bb=b[(b.experiment==ex)&(b.assignment=='rssfit_stable')].sort_values('sample_rank0')
        check(ex+'_assignment_pairing',np.array_equal(aa.csv_row_index0,bb.csv_row_index0) and np.array_equal(aa.selected_receivers,bb.selected_receivers))
        f=fp[fp.experiment==ex]
        check(ex+'_FP_same_population',set(f.csv_row_index0)==set(aa.csv_row_index0))
        if ex=='no71':check('no71_removed_everywhere',not b[b.experiment=='no71'].selected_receivers.str.split(';').map(lambda z:'71' in z).any())
    for tag in ['official','rssfit_stable']:
        bef=b[(b.experiment=='primary33')&(b.assignment==tag)].set_index('csv_row_index0');aft=b[(b.experiment=='no71')&(b.assignment==tag)].set_index('csv_row_index0')
        same=bef.loc[aft.index]
        mask=~same.selected_receivers.str.split(';').map(lambda z:'71' in z)
        check(tag+'_rawWCL_unchanged_without_receiving71',np.array_equal(same.loc[mask,'WCL_raw_error_m'],aft.loc[mask,'WCL_raw_error_m']))
        for m in METHODS:
            s0=float(bef[m+'_error_m'].median());s1=float(same[m+'_error_m'].median());s2=float(aft[m+'_error_m'].median())
            anomaly.append({'assignment':tag,'method':m,'full_n':len(bef),'survivor_n':len(aft),'full_population_median_m':s0,'before_on_survivors_median_m':s1,'after_on_survivors_median_m':s2,'selection_component_m':s1-s0,'treatment_component_m':s2-s1,'total_component_m':s2-s0,
                            'prediction_changed_on_non71_messages':int((np.abs(same.loc[mask,m+'_error_m']-aft.loc[mask,m+'_error_m'])>1e-7).sum())})
    # No-pair revised behavior is checked both synthetically and on observed cases.
    g=np.array([[0.,0.],[1000.,0.],[0.,2000.]])
    q=np.array([-110.,-110.,-110.]);revised,old,pairs=diff_location(g,q)
    check('empty_pair_returns_correctedWCL_not_first_grid_point',pairs==0 and np.array_equal(revised,ev.wcl_estimate(g,q)) and not np.allclose(old,revised),{'legacy_offset':list(map(float,old-revised))})
    q2=np.array([-110.,-115.,-120.]);revised,old,pairs=diff_location(g,q2)
    check('nonempty_pair_preserves_original_kernel',pairs>0 and np.array_equal(revised,old))
    for (ex,tag),f in b.groupby(['experiment','assignment']):
        empty=f.DIFF_empty_fallback
        check(ex+'_'+tag+'_real_empty_pair_fallback',np.array_equal(f.loc[empty,'DIFF_median_error_m'],f.loc[empty,'WCL_bc_error_m']))
        old=f.DIFF_median_error_m.copy();old.loc[empty]=f.loc[empty,'DIFF_legacy_empty_error_m']
        diags.append({'experiment':ex,'assignment':tag,'empty_cases':int(empty.sum()),'revised_median_m':float(f.DIFF_median_error_m.median()),'legacy_empty_policy_median_m':float(old.median()),'revised_p90_m':float(f.DIFF_median_error_m.quantile(.9)),'legacy_empty_policy_p90_m':float(old.quantile(.9))})
    # Independently reconstruct raw-weight formula for every geometric case.
    off=loadmap(ROOT/'inputs/official33.json');rf=loadmap(ROOT/'results/prepared/rssfit_stable41.json');maxerr=0.
    for r in b.itertuples():
        mp=off if r.assignment=='official' else rf
        gids=r.selected_receivers.split(';');g=np.array([mp[k] for k in gids]);rss=np.array([float(v) for v in r.raw_RSSI.split(';')]);w=10**((rss-rss.max())/10)
        x=w@g/w.sum();maxerr=max(maxerr,float(np.linalg.norm(x-[r.WCL_raw_x,r.WCL_raw_y])))
    check('independent_stabilized_rawWCL_formula_all_cases',maxerr<1e-7,{'max_position_delta_m':maxerr})
    # Real-case observation transparency includes unsuccessful and boundary returns.
    chosen=set(b.index[:3]);chosen.update(b.index[~b.nlls_selected_success][:3]);chosen.update(b.index[b.nlls_selected_near_boundary][:3]);chosen.update(b.index[b.DIFF_empty_fallback][:3])
    defs=json.loads((ROOT/'results/benchmark/arm_definitions.json').read_text());bd={(z['experiment'],z['assignment']):z['bbox'] for z in defs}
    obs_delta=0.;trilat_delta=0.
    for k in sorted(chosen):
        r=b.loc[k];mp=off if r.assignment=='official' else rf;g=np.array([mp[v] for v in r.selected_receivers.split(';')]);raw=np.array([float(v) for v in r.raw_RSSI.split(';')]);q=np.array([float(v) for v in r.corrected_RSSI.split(';')]);box=bd[(r.experiment,r.assignment)]
        x,stats,calls=nlls_observed(g,q,raw,box)
        x0,c0,n0=ev.robust_nlls_localize(g,q,4.7,ev.wcl_estimate(g,raw),box,huber_c=1.345,n_starts=3,max_iter=120,grad_tol=1e-6,halton_seed=1)
        obs_delta=max(obs_delta,float(np.linalg.norm(x-x0)),float(np.linalg.norm(x-[r.NLLS_x,r.NLLS_y])))
        y,ts=trilat_observed(g,q);y0=ev.trilateration_joint_A0(g,q,4.7);trilat_delta=max(trilat_delta,float(np.linalg.norm(y-y0)))
    check('optimizer_instrumentation_does_not_change_estimates',obs_delta<1e-7 and trilat_delta==0,{'cases':len(chosen),'NLLS_max_delta_m':obs_delta,'Trilat_max_delta_m':trilat_delta})
    # Conditional pair-resampling control: identical arm IDs must not be sampled
    # independently. Test the actual implementation used by the stage.
    from inference import median_draws
    v=np.linspace(10.,1000.,101);dr,info=median_draws(np.column_stack([v,v,v+7]),None,reps=1000)
    check('same_map_paired_control',np.array_equal(dr[:,0],dr[:,1]))
    check('additive_paired_control',np.allclose(dr[:,2]-dr[:,0],7,atol=1e-12,rtol=0))
    for ex in ['temporal_official_matched','temporal_official_no71']:
        early=t[(t.experiment==ex)&(t.calibration_arm=='early')].sort_values('sample_rank0');rnd=t[(t.experiment==ex)&(t.calibration_arm=='interleaved')].sort_values('sample_rank0')
        check(ex+'_fixed_rows_and_rawWCL_invariant',np.array_equal(early.csv_row_index0,rnd.csv_row_index0) and np.array_equal(early.selected_receivers,rnd.selected_receivers) and np.array_equal(early.WCL_raw_error_m,rnd.WCL_raw_error_m))
    tc=json.loads((ROOT/'results/temporal/execution_checks.json').read_text())
    check('legacy_temporal_numeric_replay',all(all(tc['legacy_'+arm]['rounded_matches'].values()) for arm in ['early','interleaved']))
    c=context(a.data)
    pop=json.loads((ROOT/'results/prepared/populations.json').read_text())
    check('primary_content_exclusion',not any(c['keys'][i] in c['ckeys'] for i in pop['primary_working_ids']))
    check('fingerprint_database_only_calibration',set(pop['fingerprint_database_working_ids'])<=set(c['ci']))
    check('data_unchanged',sha(a.data)==CSV_SHA)
    csvout(ROOT/'results/benchmark/anomaly_decomposition.csv',pd.DataFrame(anomaly))
    csvout(ROOT/'results/benchmark/differential_empty_policy_sensitivity.csv',pd.DataFrame(diags))
    diagnostics=[]
    for (ex,tag),f in st.groupby(['experiment','assignment']):
        for (sel,success,status,message),ss in f.groupby(['selected','success','status','message'],dropna=False):
            diagnostics.append({'experiment':ex,'assignment':tag,'selected':bool(sel),'success':bool(success),'status':int(status),'message':message,'count':len(ss)})
    csvout(ROOT/'results/benchmark/optimizer_status_counts.csv',pd.DataFrame(diagnostics))
    dump(ROOT/'tests/validation_results.json',{'all_pass':all(v['pass'] for v in checks.values()),'n_checks':len(checks),'checks':checks})
    print(json.dumps({'all_pass':True,'n_checks':len(checks),'case_count':len(b)},indent=2))
if __name__=='__main__':main()
