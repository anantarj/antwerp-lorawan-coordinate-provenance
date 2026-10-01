from pathlib import Path
import argparse,json
import numpy as np,pandas as pd
from common import *
def check(a,b,out):
 p=load_protocol();checks=[]
 for name in ['MODEL_STATE_IDENTITIES.json','NATIVE_METRIC_TABLES.json','SOURCE_STATEMENT_RECEIPT.json','EXECUTION_RECEIPT.json','SOURCE_EXECUTION_STDOUT.txt']:
  same=(a/name).read_bytes()==(b/name).read_bytes();checks.append({'file':name,'byte_equal':same});assert same
 for part in ['train_1','train_2','val','test']:
  f=part+'_PREDICTIONS.csv.gz';x=pd.read_csv(a/f,float_precision='round_trip');y=pd.read_csv(b/f,float_precision='round_trip')
  assert x.columns.tolist()==y.columns.tolist()
  for c in x:
   if pd.api.types.is_numeric_dtype(x[c]):
    v=float(np.abs(x[c].astype(float)-y[c].astype(float)).max());tol=p['repeat']['positions_atol_degrees'] if c in ['true_lat','true_lon','pred_lat','pred_lon'] else p['repeat']['error_prediction_atol_m'] if c in ['error_m','dd_m','ddl_m'] else 0
    assert v<=tol;checks.append({'file':f,'column':c,'max_abs_difference':v,'tolerance':tol})
   else:assert x[c].equals(y[c])
  checks.append({'file':f,'byte_equal':(a/f).read_bytes()==(b/f).read_bytes()})
 write_json(out,{'passed':True,'checks':checks,'scientific_file_count':9,'runtime_excluded':True})
 print('Repeated native outputs checked')
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--first',type=Path,required=True);a.add_argument('--second',type=Path,required=True);a.add_argument('--out',type=Path,required=True);v=a.parse_args();check(v.first,v.second,v.out)
