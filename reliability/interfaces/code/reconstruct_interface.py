"""Construct trusted input from pinned G2 artifacts; run new isolated checks.
Use a fresh output directory. No model training, calibration or new risk scoring.
"""
from pathlib import Path
import argparse,hashlib,json,copy,subprocess,sys,gzip,csv
from claim_contract import audit_derived_quantities
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()
def run(native:Path,out:Path):
 if out.exists():raise FileExistsError(out)
 out.mkdir(parents=True)
 nr=native/'results/native_run1'; rel=native/'results/reliability'
 states=json.loads((nr/'MODEL_STATE_IDENTITIES.json').read_text())
 cs=json.loads((rel/'CALIBRATION_STATES.json').read_text())
 cal=next(c for c in cs if c['method']=='DD' and c['alpha']==0.05)
 # Original source row handles from the actual saved primary-role predictions.
 with gzip.open(nr/'test_PREDICTIONS.csv.gz','rt') as f:
  rows=[r for r in csv.DictReader(f) if r['primary_role_eligible'].lower()=='true']
 if len(rows)!=8275:raise ValueError('Wrong prediction population')
 payload='870abe60a4bd81f31ede6f269b6bc6329e05d2731343dff7015bae1a61218446'
 handles=[payload+':'+r['source_row_index0'] for r in rows]
 trusted={'source_payload':payload,'feature_schema':[f'BS {i}' for i in range(1,73)],
 'position_model':states['M1']['state_sha256'],'error_model':states['DD']['state_sha256'],
 'coordinate_metric':cal['metric'],'error_units':'metres',
 'calibration_role':cal['calibration_role_hash'], 'calibration_state':hashlib.sha256(canonical(cal)).hexdigest(),
 'score_kind':'actual_error_minus_point_error_estimate',
 'population':hashlib.sha256(canonical(handles)).hexdigest(),'ordered_row_handles':handles}
 cases=[]; expected={}
 def add(name,rec,ok):
  cases.append({'case':name,'trusted':trusted,'received':rec}); expected[name]=ok
 add('clean',copy.deepcopy(trusted),True)
 rec=copy.deepcopy(trusted); rec['ordered_row_handles']=list(reversed(list(reversed(handles))))
 add('reordered_view_restored_with_original_handles',rec,True)
 rec=copy.deepcopy(trusted);rec['ordered_row_handles']=list(reversed(handles));add('unrestored_order',rec,False)
 rec=copy.deepcopy(trusted);rec['feature_schema']=list(reversed(rec['feature_schema']));add('unrestored_features',rec,False)
 for name,key,value in [('stale_position_binding','position_model','different-declared-model'),
                        ('stale_DD_DDL_binding','error_model',states['DDL']['state_sha256']),
                        ('different_metric','coordinate_metric','different-declared-metric'),
                        ('different_calibration_role','calibration_role','different-role'),
                        ('different_units','error_units','kilometres')]:
  rec=copy.deepcopy(trusted);rec[key]=value;add(name,rec,False)
 wire={'cases':cases}
 p=subprocess.run([sys.executable,str(ROOT/'code/dependency_worker.py')],input=json.dumps(wire),text=True,capture_output=True,check=True)
 result=json.loads(p.stdout)
 for c in result['cases']:
  assert c['equal']; assert (c['integrated']['state']=='equivalent_continuation')==expected[c['case']]
 # Wrong unannounced arithmetic is invisible to unchanged metadata.
 from claim_contract import validate_dependencies
 dep=validate_dependencies(trusted,copy.deepcopy(trusted));assert dep['state']=='equivalent_continuation'
 e=[100.,20.,0.];h=[160.,10.,0.]
 correct=audit_derived_quantities(e,h,[a-b for a,b in zip(e,h)])
 wrong=audit_derived_quantities(e,h,[a-abs(a-b) for a,b in zip(e,h)])
 assert correct['mismatched_records']==0 and wrong['mismatched_records']==1
 sources=[nr/'MODEL_STATE_IDENTITIES.json',nr/'test_PREDICTIONS.csv.gz',rel/'CALIBRATION_STATES.json']
 receipt={'status':'R3_EXPLICIT_RECONSTRUCTION_NOT_R2_BYTE_RECOVERY',
 'dependency_cases':len(cases),'label_free_reference_parity':True,'labels_received_by_worker':False,
 'network_file_hooks_disabled_during_checks':True,'not_security_sandbox_proof':True,
 'trusted_manifest_origin':'pinned native G2 predictions, model states and calibration records; not fault-generator verdict',
 'native_inputs':[{'path':str(p.relative_to(native)),'sha256':sha(p)} for p in sources],
 'input_wire_sha256':hashlib.sha256(canonical(wire)).hexdigest(),
 'prediction_rows_bound':len(handles),'no_new_localization_or_reliability_experiment':True,
 'unannounced_formula_dependency_result':dep,'constructed_offline_correct':correct,'constructed_offline_wrong':wrong}
 for fn,obj in [('TRUSTED_MANIFEST.json',trusted),('CASE_RESULTS.json',result),('INTERFACE_RECEIPT.json',receipt)]:
  (out/fn).write_text(json.dumps(obj,indent=2)+'\n')
 print(json.dumps({k:v for k,v in receipt.items() if k not in ('native_inputs',)},indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--native',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();run(a.native,a.out)
