"""Execute a pinned source-native M1/DD/DDL specification with explicit compatibility adaptations.

This is not complete notebook execution. Reporting/tuning/unrelated imports are excluded.
The original computational statements are selected as AST nodes without rewriting their bodies.
"""
from __future__ import annotations
from pathlib import Path
import argparse,ast,contextlib,io,json,statistics,time
from collections import OrderedDict
import numpy as np,pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.model_selection import train_test_split
from joblib import parallel_backend
from common import ROOT,array_hash,sha_bytes,write_json,load_protocol,great_circle_km,coordinate_oracle

def selected_body(source,mode):
    t=ast.parse(source);nodes=[]
    for n in t.body:
        if isinstance(n,ast.Assign):nodes.append(n)
        elif isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and n.value.func.attr=='fit':nodes.append(n)
    return nodes

def run(inputs:Path,out:Path):
    protocol=load_protocol()
    if out.exists():raise FileExistsError(out)
    out.mkdir(parents=True);start=time.monotonic()
    nb=json.loads((ROOT/'sources/original/DAE_Benchmarking_Public.ipynb').read_text())
    ns={'np':np,'p':pd,'statistics':statistics,'OrderedDict':OrderedDict,'spearmanr':spearmanr,'haversine':great_circle_km,'ExtraTreesRegressor':ExtraTreesRegressor,'train_test_split':train_test_split,'random_state':42,'units':'lat_lon','dataset':'lorawan','default_NaN':-200}
    source_index=[]
    for name in ['haversine_script.py','DAE_script.py']:
        text=(ROOT/'sources/compat'/name).read_text();tree=ast.parse(text)
        defs=[n for n in tree.body if isinstance(n,ast.FunctionDef)]
        # Loading all definition bodies does not execute NN/tuning/baseline branches.
        exec(compile(ast.Module(body=defs,type_ignores=[]),name,'exec'),ns)
        for n in defs:source_index.append({'file':name,'function':n.name,'ast_sha256':sha_bytes(ast.dump(n,include_attributes=False).encode()),'operation':'definition_loaded; only invoked helpers executed'})
    for p in ['train','val','test']:
        for v in ['x','y']:ns[f'{v}_{p}']=pd.read_csv(inputs/f'files/lorawan/{v}_{p}.csv')
    prep=ast.parse(''.join(nb['cells'][1]['source']))
    selected=[]
    for n in prep.body:
        if isinstance(n,ast.If) and ast.unparse(n.test)=="dataset != 'DSI'":selected.append(n)
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ['y_train','y_val','y_test'] for t in n.targets):selected.append(n)
    capture=io.StringIO()
    with contextlib.redirect_stdout(capture):exec(compile(ast.Module(body=selected,type_ignores=[]),'cell1-preprocessing','exec'),ns)
    splitnodes=[n for n in ast.parse(''.join(nb['cells'][3]['source'])).body if isinstance(n,ast.Assign)]
    exec(compile(ast.Module(body=splitnodes,type_ignores=[]),'cell3-split','exec'),ns)
    first=selected_body(''.join(nb['cells'][5]['source']),'DD')
    second=selected_body(''.join(nb['cells'][7]['source']),'DDL')
    # Statement equality is by original AST node, not hand rewritten model code.
    for cell,nodes in [(1,selected),(3,splitnodes),(5,first),(7,second)]:
        for n in nodes:source_index.append({'cell':cell,'line':n.lineno,'end_line':n.end_lineno,'ast_sha256':sha_bytes(ast.dump(n,include_attributes=False).encode()),'source':ast.get_source_segment(''.join(nb['cells'][cell]['source']),n)})
    write_json(out/'SOURCE_STATEMENT_RECEIPT.json',source_index)
    with parallel_backend('sequential'),contextlib.redirect_stdout(capture):
        exec(compile(ast.Module(body=first,type_ignores=[]),'cell5-DD','exec'),ns);dd=ns['M2']
        exec(compile(ast.Module(body=second,type_ignores=[]),'cell7-DDL','exec'),ns);ddl=ns['M2']
    models={'M1':ns['M1'],'DD':dd,'DDL':ddl};modelstates={}
    for label,m in models.items():
        hs=[]
        for est in m.estimators_:
            state=est.tree_.__getstate__(); hs.append(sha_bytes(b''.join(np.ascontiguousarray(state[k]).tobytes() for k in ['nodes','values'])))
        modelstates[label]={'params':m.get_params(),'tree_hashes':hs,'state_sha256':sha_bytes((''.join(hs)).encode())}
    role=pd.read_csv(inputs/'ROW_ROLE_LEDGER.csv.gz')
    train=role[role.partition=='train'].copy();idx1,idx2=train_test_split(np.arange(len(train)),test_size=.5,random_state=42)
    records=[];checks=[];metrics=[]
    for p in ['train_1','train_2','val','test']:
        y=ns['y_'+p];pred=ns['y_M1_predict_in_'+p];e=np.asarray(ns['y_M1_error_'+p]);h=ns['DAE_in_'+p];hl=ns['DAE_in_'+p+'_M1']
        oracle=coordinate_oracle(y,pred,'lat_lon');diff=float(np.abs(oracle-e).max())
        if diff>protocol['metric']['oracle_tolerance_m']:raise ValueError(f'metric oracle disagreement {diff}')
        ix=idx1 if p=='train_1' else idx2 if p=='train_2' else None
        rr=train.iloc[ix].reset_index(drop=True) if ix is not None else role[role.partition==p].reset_index(drop=True)
        df=rr.copy();df['native_role']=p
        for k,a in [('true_lat',y[:,0]),('true_lon',y[:,1]),('pred_lat',pred[:,0]),('pred_lon',pred[:,1]),('error_m',e),('dd_m',h),('ddl_m',hl)]:df[k]=a
        df['native_partition_rank0']=np.arange(len(df));df.to_csv(out/f'{p}_PREDICTIONS.csv.gz',index=False,float_format='%.17g',compression={'method':'gzip','mtime':0})
        for label,a in [('positions',pred),('error_m',e),('dd_m',h),('ddl_m',hl)]:checks.append({'role':p,'object':label,'shape':list(a.shape),'array_sha256':array_hash(a),'finite':bool(np.isfinite(a).all())})
        checks.append({'role':p,'metric_oracle_max_difference_m':diff})
        for label,a in [('DD',h),('DDL',hl)]:
            with contextlib.redirect_stdout(capture): mm=ns['calculate_DAE_evaluation_metrics'](e,a,label)
            metrics.append({'role':p,**mm})
    # Benign feature/row permutation: restore the authoritative feature names and handles before prediction.
    x=np.asarray(ns['x_test']); perm=np.arange(x.shape[1])[::-1];rowperm=np.random.default_rng(20260922).permutation(len(x))
    restored=x[rowperm][:,perm][np.argsort(rowperm)][:,np.argsort(perm)]
    with parallel_backend('sequential'): p2=ns['M1'].predict(restored)
    checks.append({'operation':'composed_benign_row_feature_restore','input_exact':bool(np.array_equal(restored,x)),'prediction_exact':bool(np.array_equal(p2,ns['y_M1_predict_in_test']))})
    assert checks[-1]['input_exact'] and checks[-1]['prediction_exact']
    write_json(out/'NATIVE_METRIC_TABLES.json',metrics)
    write_json(out/'MODEL_STATE_IDENTITIES.json',modelstates)
    write_json(out/'EXECUTION_RECEIPT.json',{'scope':protocol['scope'],'protocol_sha256':sha_bytes((ROOT/'protocol/EXECUTION_PROTOCOL.json').read_bytes()),'checks':checks,'preprocessing_minimum':ns['minimum'],'model_training_rows':{'M1':len(idx1),'DD':len(idx2),'DDL':len(idx2)},'environment':protocol['execution_environment'],'metric_substitution':protocol['metric'],'native_training_errors_mean_m':float(np.mean(ns['y_M1_error_train_2'])),'native_training_errors_median_m':float(np.median(ns['y_M1_error_train_2']))})
    (out/'SOURCE_EXECUTION_STDOUT.txt').write_text(capture.getvalue())
    write_json(out/'RUNTIME.json',{'elapsed_seconds':time.monotonic()-start})
    print('DONE',out,'elapsed',time.monotonic()-start,flush=True)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--inputs',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();run(a.inputs,a.out)
