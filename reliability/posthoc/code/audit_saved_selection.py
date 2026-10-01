"""Post-hoc selection audit of frozen G2 predictions; no training or policy tuning.

Usage:
 python code/audit_saved_selection.py --native-dir EXTRACTED_NATIVE_ROOT \
   --transfer-dir EXTRACTED_TRANSFER_ROOT --out NEW_OUTPUT_DIRECTORY

Requires NumPy and pandas. Uses saved calibration states and original diagnostic
landmarks. Matched-k tables are exploratory, not deployed threshold policies.
"""
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
import numpy as np
import pandas as pd


def sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def snapshot(root: Path) -> dict[str, str]:
    return {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob('*')) if p.is_file()}


def verify_manifest(root: Path) -> int:
    m = json.loads((root / 'MANIFEST.json').read_text())
    for entry in m['files']:
        p = root / entry['path']
        if not p.is_file() or p.stat().st_size != entry['bytes'] or sha(p) != entry['sha256']:
            raise ValueError(f'Manifest mismatch: {p}')
    return len(m['files'])


def jwrite(p: Path, v: object) -> None:
    p.write_text(json.dumps(v, indent=2, sort_keys=True, allow_nan=False)+'\n')


def main(native: Path, transfer: Path, out: Path) -> None:
    native, transfer, out = native.resolve(), transfer.resolve(), out.resolve()
    if out.exists() or any(out.is_relative_to(p) for p in [native,transfer]):
        raise ValueError('Output must be new and outside protected input roots')
    before = {'native': snapshot(native), 'transfer': snapshot(transfer)}
    verified = {n: verify_manifest(r) for n,r in [('native',native),('transfer',transfer)]}
    out.mkdir(parents=True)
    native_protocol=json.loads((native/'protocol/EXECUTION_PROTOCOL.json').read_text())
    transfer_protocol=json.loads((transfer/'protocol/FOLLOWUP_PROTOCOL.json').read_text())
    configurations=[
        ('lorawan_same_regime', native/'results/native_run1/test_PREDICTIONS.csv.gz',
         native/'results/reliability/CALIBRATION_STATES.json',native_protocol['endpoints']['thresholds_m'],[500.,1000.]),
        ('dsi',transfer/'results/pass1/dsi/evaluation_PREDICTIONS.csv.gz',
         transfer/'results/pass1/dsi/CALIBRATION_STATES.json',transfer_protocol['thresholds_m']['dsi'],[5.,10.]),
        ('lorawan_temporal',transfer/'results/pass1/lorawan_temporal/evaluation_PREDICTIONS.csv.gz',
         transfer/'results/pass1/lorawan_temporal/CALIBRATION_STATES.json',transfer_protocol['thresholds_m']['lorawan_temporal'],[500.,1000.])]
    order_rows=[]; masks=[]; matched=[]; examples=[]; inputs=[]
    for scenario,pred_path,state_path,landmarks,targets in configurations:
        inputs += [{'scenario':scenario,'path':str(p),'sha256':sha(p)} for p in [pred_path,state_path]]
        data=pd.read_csv(pred_path,float_precision='round_trip')
        n_requested=len(data)
        if scenario=='lorawan_same_regime':
            data=data.loc[data.primary_role_eligible].copy()
        data=data.reset_index(drop=True)
        n=len(data);e=data.error_m.to_numpy()
        if not np.isfinite(data[['dd_m','ddl_m','error_m']].to_numpy()).all():
            raise ValueError('Nonfinite input prediction')
        states=json.loads(state_path.read_text())
        dynamic=[s for s in states if s['method'] in ('DD','DDL')]
        for s in dynamic:
            model=s['method'];h=data['dd_m' if model=='DD' else 'ddl_m'].to_numpy()
            q=float(s['q_m']);role=s.get('calibration_role','same_regime_calibration')
            entry={'scenario':scenario,'calibration_role':role,'model':model,'alpha':s['alpha'],
                   'n_scored':n,'n_original_requests':n_requested,'q_m':q if math.isfinite(q) else None,
                   'finite_correction':math.isfinite(q)}
            if not math.isfinite(q):
                entry.update({'stable_sort_identical':None,'zero_clipped_count':None,
                              'interpretation':'Infinite radius; no finite-threshold acceptance. Do not assign a ranking benefit.'})
                order_rows.append(entry)
                for tau in landmarks:
                    masks.append({'scenario':scenario,'calibration_role':role,'model':model,'alpha':s['alpha'],
                                  'tau_m':tau,'accepted':0,'useful':0,'harmful':0,'threshold_equivalence_verified':None,
                                  'finite':False,'shifted_raw_threshold_m':None})
                continue
            u=np.maximum(0,h+q)
            ih=np.argsort(h,kind='stable');iu=np.argsort(u,kind='stable')
            eq=np.array_equal(ih,iu)
            entry.update({'stable_sort_identical':bool(eq),'zero_clipped_count':int(np.sum(u==0)),
                          'rank_positions_disagree':int(np.sum(ih!=iu)),
                          'interpretation':'All same-k sets identical under common saved-row tie order' if eq else 'Inspect tie/rounding differences'})
            order_rows.append(entry)
            for tau in landmarks:
                ma=np.isfinite(u)&(u<=tau);mb=h<=float(tau)-q
                exact=np.array_equal(ma,mb)
                if not exact:
                    raise AssertionError(f'Threshold mismatch {scenario} {model} {role} {tau}')
                masks.append({'scenario':scenario,'calibration_role':role,'model':model,'alpha':s['alpha'],
                              'tau_m':tau,'accepted':int(ma.sum()),'useful':int(np.sum(ma&(e<=tau))),
                              'harmful':int(np.sum(ma&(e>tau))),'threshold_equivalence_verified':bool(exact),
                              'finite':True,'shifted_raw_threshold_m':float(tau)-q})
                if s['alpha']==.05 and tau in targets:
                    raw=h<=tau
                    examples.append({'scenario':scenario,'calibration_role':role,'model':model,'tau_m':tau,
                                     'raw_accepted_at_same_numeric_threshold':int(raw.sum()),
                                     'raw_harmful_at_same_numeric_threshold':int(np.sum(raw&(e>tau))),
                                     'calibrated_accepted':int(ma.sum()),'calibrated_useful':int(np.sum(ma&(e<=tau))),
                                     'calibrated_harmful':int(np.sum(ma&(e>tau))),
                                     'equivalent_raw_score_threshold_m':float(tau)-q,
                                     'equivalent_raw_mask_identical':True})
        # Finite-sample same-k descriptive comparison: no interpolation or label-based ordering.
        for model,col in [('DD','dd_m'),('DDL','ddl_m')]:
            h=data[col].to_numpy();order=np.argsort(h,kind='stable')
            for fraction in [.1,.25,.5,.75,1.]:
                k=max(1,int(math.ceil(n*fraction)));idx=order[:k];selected=e[idx]
                boundary_tie_split=k<n and h[order[k-1]]==h[order[k]]
                for tau in targets:
                    harmful=int(np.sum(selected>tau))
                    matched.append({'scenario':scenario,'model':model,'n_scored':n,'requested_fraction':fraction,
                                    'k':k,'actual_fraction':k/n,'tau_m':tau,'useful':k-harmful,'harmful':harmful,
                                    'conditional_failure':harmful/k,'mean_position_error_m':float(selected.mean()),
                                    'p90_position_error_m':float(np.quantile(selected,.9)),
                                    'tie_split_at_boundary':bool(boundary_tie_split),
                                    'calibrated_same_model_same_k_identical_for_all_finite_states':bool(all(
                                        x['stable_sort_identical'] is True for x in order_rows if x['scenario']==scenario and x['model']==model and x['finite_correction'])),
                                    'scope':'posthoc descriptive batch ranking; not an independently selected deployable threshold'})
    pd.DataFrame(order_rows).to_csv(out/'FINITE_SHIFT_ORDER_AUDIT.csv',index=False,float_format='%.17g')
    pd.DataFrame(masks).to_csv(out/'ORIGINAL_LANDMARK_MASK_AUDIT.csv',index=False,float_format='%.17g')
    pd.DataFrame(examples).to_csv(out/'ORIGINAL_LANDMARK_EXPLANATION.csv',index=False,float_format='%.17g')
    pd.DataFrame(matched).to_csv(out/'POSTHOC_SAME_K_COMPARISONS.csv',index=False,float_format='%.17g')
    after={'native':snapshot(native),'transfer':snapshot(transfer)}
    if after!=before:
        raise AssertionError('Protected input changed')
    jwrite(out/'AUDIT_RECEIPT.json',{
        'status':'POSTHOC_EXISTING_OUTPUT_ANALYSIS_NOT_NEW_MODEL_EXPERIMENT',
        'no_model_fit':True,'no_policy_selection':True,'no_claim_of_new_algorithm':True,
        'original_frozen_g2_protocols_unchanged':True,'input_manifest_entries_verified':verified,
        'finite_dynamic_states':sum(x['finite_correction'] for x in order_rows),
        'finite_states_same_stable_order':sum(x.get('stable_sort_identical') is True for x in order_rows),
        'infinite_dynamic_states':sum(not x['finite_correction'] for x in order_rows),
        'finite_mask_equivalences_verified':sum(x['finite'] for x in masks),
        'landmark_records_total':len(masks),'same_k_comparison_rows':len(matched),
        'finite_dynamic_states_with_clipped_zeros':sum((x.get('zero_clipped_count') or 0)>0 for x in order_rows),
        'source_files':inputs,
        'limits':['Same-k comparison is not matched radius-containment coverage.',
                  'Matching achieved test counts is a retrospective diagnostic, not a test-tuned deployment policy.',
                  'An infinite radius has no finite-threshold acceptance; its artificial stable-sort order is not interpreted.',
                  'Constant-radius rules have no informative ordering; no arbitrary partial constant policy is fabricated.',
                  'Unchanged ranking does not remove the value of magnitude calibration under its stated assumptions.'],
        'all_protected_files_unchanged':True})
    print(json.dumps(json.loads((out/'AUDIT_RECEIPT.json').read_text()),indent=2))

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--native-dir',type=Path,required=True)
    a.add_argument('--transfer-dir',type=Path,required=True)
    a.add_argument('--out',type=Path,required=True)
    v=a.parse_args();main(v.native_dir,v.transfer_dir,v.out)
