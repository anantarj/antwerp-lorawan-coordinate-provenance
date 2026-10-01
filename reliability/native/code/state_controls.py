"""Information-matched conventional and G1-handle-integrated state/quantity checks.

Derived-residual numerical checks are offline and use labelled reference records.
These checks are not detectors of arbitrary latent deployment distribution shift.
"""
from __future__ import annotations
from pathlib import Path
import argparse,copy,json,sys
from dataclasses import dataclass
import numpy as np,pandas as pd
from common import *
sys.path.insert(0,str(ROOT/'sources/g1/code'))
from identity_core import RowHandle,ContractError

FIELDS=('source_payload','feature_schema','position_model','error_model','coordinate_metric','error_units','calibration_role','score_kind','population')

def strong_conventional(expected,received,e,h,claimed_signed):
    """Explicit equality and independent arithmetic; no G1 matcher used."""
    problems=[f'{k}_mismatch' for k in FIELDS if expected[k]!=received[k]]
    if len(claimed_signed)!=len(e) or not np.allclose(np.asarray(claimed_signed),np.asarray(e)-np.asarray(h),rtol=0,atol=1e-8):problems.append('signed_quantity_mismatch_offline')
    return sorted(problems)

def integrated(expected,received,rows,e,h,claimed_signed):
    """Frozen G1 handles plus explicit dependency contract and semantic oracle."""
    for row in rows:
        if not isinstance(row,RowHandle):raise ContractError('invalid_row_handle','G1 handles required')
    if len(set(rows))!=len(rows):return ['duplicate_row_handles']
    if any(r.payload_sha256!=received['source_payload'] for r in rows):return ['source_payload_mismatch']
    violations=[]
    for k in FIELDS:
        if object_hash(expected[k])!=object_hash(received[k]):violations.append(f'{k}_mismatch')
    # Scalar reference is independent of the source residual expression.
    target=np.fromiter((float(a)-float(b) for a,b in zip(e,h)),dtype=float,count=len(e))
    if np.shape(claimed_signed)!=target.shape or not np.allclose(claimed_signed,target,atol=1e-8,rtol=0):violations.append('signed_quantity_mismatch_offline')
    return sorted(violations)

def run(native:Path,reliability:Path,out:Path):
    p=load_protocol()
    if out.exists():raise FileExistsError(out)
    out.mkdir(parents=True)
    states=json.loads((native/'MODEL_STATE_IDENTITIES.json').read_text());cs=json.loads((reliability/'CALIBRATION_STATES.json').read_text())
    ddcal=next(a for a in cs if a['method']=='DD' and a['alpha']==.05);dlcal=next(a for a in cs if a['method']=='DDL' and a['alpha']==.05)
    df=pd.read_csv(native/'test_PREDICTIONS.csv.gz',float_precision='round_trip');df=df[df.primary_role_eligible].copy()
    e=df.error_m.to_numpy();dd=df.dd_m.to_numpy();dl=df.ddl_m.to_numpy()
    ids=df.source_row_index0.to_numpy(np.int64);sha='870abe60a4bd81f31ede6f269b6bc6329e05d2731343dff7015bae1a61218446'
    rows=tuple(RowHandle(sha,int(i)) for i in ids)
    expected={'source_payload':sha,'feature_schema':[f'BS {i}' for i in range(1,73)],'position_model':states['M1']['state_sha256'],'error_model':states['DD']['state_sha256'],'coordinate_metric':p['metric']['id'],'error_units':'metres','calibration_role':ddcal['calibration_role_hash'],'score_kind':'actual_error_minus_point_error_estimate','population':array_hash(ids)}
    # Record case functions and expected behavior in this source, pinned before running.
    cases=[]
    cases.append(('clean','native baseline',copy.deepcopy(expected),dd,e-dd,[]))
    cases.append(('benign_row_reorder_with_handles','controlled benign, restored before checking',copy.deepcopy(expected),dd,e-dd,[]))
    cases.append(('benign_feature_reorder_with_handles','controlled benign, restored before checking',copy.deepcopy(expected),dd,e-dd,[]))
    cases.append(('source_signed_derived_quantity','source-expression replay with correct DDL binding',dict(expected,error_model=states['DDL']['state_sha256']),dl,e-np.abs(e-dl),['signed_quantity_mismatch_offline']))
    cases.append(('source_DD_DDL_label_binding','source DD label attached to DDL quantity',dict(expected,error_model=states['DDL']['state_sha256']),dd,e-dd,['error_model_mismatch']))
    cases.append(('DD_calibration_used_with_DDL','controlled stale calibration dependency',dict(expected,error_model=states['DDL']['state_sha256']),dl,e-dl,['error_model_mismatch']))
    cases.append(('stale_position_model_identity','controlled model identity only; no new model fit',dict(expected,position_model='deliberately-different-position-model-id'),dd,e-dd,['position_model_mismatch']))
    cases.append(('unit_m_vs_km','controlled units substitution',dict(expected,error_units='kilometres'),dd,e-dd,['error_units_mismatch']))
    cases.append(('undeclared_test_population_substitution','controlled different population declaration',dict(expected,population=array_hash(ids[:-1])),dd,e-dd,['population_mismatch']))
    results=[]
    for name,kind,record,h,s,wanted in cases:
        exp=copy.deepcopy(expected)
        if name=='source_signed_derived_quantity':exp['error_model']=states['DDL']['state_sha256']
        b=strong_conventional(exp,record,e,h,s);g=integrated(exp,record,rows,e,h,s)
        assert b==g==wanted,(name,b,g,wanted)
        results.append({'case':name,'evidence_class':kind,'attempted_records':len(df),'strong_simple_violations':b,'integrated_violations':g,'same_information':True,'expected_state':'equivalent_continuation' if not wanted else 'unsupported_original_claim','strong_simple_certified_records':len(df) if not b else 0,'integrated_certified_records':len(df) if not g else 0,'physical_prediction_availability_records':len(df),'numerical_oracle_requires_labels':name=='source_signed_derived_quantity','new_algorithm_superiority':False})
    # Refuse-all and undetectable shared-error are explicit non-success conditions, not wins.
    results.append({'case':'reject_all','attempted_records':len(df),'certified_records':0,'raw_prediction_availability_records':len(df),'useful_certified_coverage':0,'conditional_risk':None,'interpretation':'Not a useful assurance method'})
    results.append({'case':'unknown_shared_consistent_error','state':'out_of_scope','interpretation':'Same-key consistent source error or unannounced distribution change cannot be ruled out by these checks; no false detection credit'})
    # Quantify the one declared stale-state decision case. No use of labels in the decision rule.
    records=[]
    for scenario,u in [('DD_correct',np.maximum(0,dd+ddcal['q_m'])),('DDL_with_stale_DD_q',np.maximum(0,dl+ddcal['q_m'])),('DDL_recalibrated',np.maximum(0,dl+dlcal['q_m']))]:
        for tau in p['endpoints']['thresholds_m']:
            records.append({'scenario':scenario,'scope':'controlled state association, not source-author deployment',**decision_stats(e,u,tau,total_requests=8307)})
    pd.DataFrame(records).to_csv(out/'STALE_STATE_DECISION_OUTCOMES.csv',index=False,float_format='%.17g')
    write_json(out/'CONTROL_CASES.json',results)
    write_json(out/'DEPENDENCY_BINDING.json',{'expected_DD':expected,'expected_DDL':dict(expected,error_model=states['DDL']['state_sha256']),'DD_calibration_state':ddcal,'DDL_calibration_state':dlcal,'G1_scope':'original RowHandle type and verified original sidecars; matcher not needed or reexecuted for fingerprint-only reliability','strong_simple_control_ties':True,'no_runtime_true_label_oracle_claim':True})
    print('STATE/SEMANTIC CONTROLS COMPLETE:',len(results),'cases (two limits, not passed detections)')
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--native',type=Path,required=True);a.add_argument('--reliability',type=Path,required=True);a.add_argument('--out',type=Path,required=True);v=a.parse_args();run(v.native,v.reliability,v.out)
