"""Frozen source-component DSI transfer and one chronological LoRaWAN experiment.

No coordinates are fitted. Conventional rank calibration is shared by all fair
implementations. New time-role assignment is a changed task, not native replication.
"""
from __future__ import annotations
from pathlib import Path
import argparse,ast,contextlib,io,json,math,statistics,sys,time,zipfile
from collections import OrderedDict
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.model_selection import train_test_split
from joblib import parallel_backend
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'sources/inherited'))
from common import sha_bytes,array_hash,object_hash,write_json,clean_json,great_circle_km,coordinate_oracle,conformal_quantile,decision_stats,empirical_cvar
from evaluate import summaries
from identity_core import RowHandle,ContractError
from lineage import read_csv,save_csv,ARCHIVE_SHA,RAW_LORA_SHA

def load_protocol():
    f=ROOT/'protocol/FOLLOWUP_PROTOCOL.json'
    if sha_bytes(f.read_bytes())!=(f.with_suffix('.sha256')).read_text().split()[0]:raise ValueError('changed frozen protocol')
    p=json.loads(f.read_text())
    gate=json.loads((ROOT/'checks/PRE_EXECUTION_GATE.json').read_text())
    for rel,h in gate['files'].items():
        if sha_bytes((ROOT/rel).read_bytes())!=h:raise ValueError('changed execution input '+rel)
    return p

def get_data(archive,scenario):
    with zipfile.ZipFile(archive) as z:
        if scenario=='dsi':
            arrays={s:(read_csv(z,f'files/DSI/x_{s}.csv').to_numpy(),read_csv(z,f'files/DSI/y_{s}.csv').to_numpy()) for s in ['train','val','test']}
            i1,i2=train_test_split(np.arange(len(arrays['train'][0])),test_size=.5,random_state=42)
            data={}
            for role,part,ii in [('train1','train',i1),('train2','train',i2),('calibration_reference','val',np.arange(115)),('evaluation','test',np.arange(115))]:
                x,y=arrays[part]
                handles=[RowHandle(sha_bytes(z.read(f'files/DSI/x_{part}.csv')),int(i)) for i in ii]
                data[role]={'x':x[ii],'y':y[ii],'rows':pd.DataFrame({'source_row_index0':ii,'source_payload_sha256':[h.payload_sha256 for h in handles],'source_partition':part}), 'handles':tuple(handles)}
            prep={'transformation':'archived DSI values unchanged, as source dataset=DSI branch','features':[str(i) for i in range(157)],'units':'meters','min_or_sentinel_refit':False}
        else:
            raw=read_csv(z,'files/lorawan/lorawan_dataset_antwerp.csv')
            roles=pd.read_csv(ROOT/'results/input_audit/LORAWAN_TEMPORAL_ROLE_LEDGER.csv.gz')
            data={}
            for role in ['train1','train2','calibration_reference','calibration_recent','evaluation']:
                rows=roles[roles.role==role].reset_index(drop=True).copy();ids=rows.source_row_index0.to_numpy(np.int64)
                data[role]={'x':raw.iloc[ids,:72].to_numpy(), 'y':raw.iloc[ids][['Latitude','Longitude']].to_numpy(),
                            'rows':rows,'handles':tuple(RowHandle(RAW_LORA_SHA,int(i)) for i in ids)}
            # Original source sentinel replacement, restricted to the early training pool.
            both=np.concatenate([data[r]['x'] for r in ['train1','train2']])
            minimum=int(np.where(both==-200,0,both).min()-1)
            for role,d in data.items():
                if role.startswith('train'):
                    d['x']=np.where(np.where(d['x']==-200,0,d['x'])==0,minimum,np.where(d['x']==-200,0,d['x']))
                else:d['x']=np.where(d['x']==-200,minimum,d['x'])
            prep={'transformation':'native training-only sentinel-to-minimum convention; newly chronological roles','minimum':minimum,'features':[f'BS {i}' for i in range(1,73)],'units':'lat_lon'}
    return data,prep

def source_models(data,units):
    nb=json.loads((ROOT/'sources/original/DAE_Benchmarking_Public.ipynb').read_text())
    ns={'np':np,'p':pd,'statistics':statistics,'OrderedDict':OrderedDict,'spearmanr':spearmanr,'haversine':great_circle_km,
        'ExtraTreesRegressor':ExtraTreesRegressor,'random_state':42,'units':units}
    for name in ['haversine_script.py','DAE_script.py']:
        text=(ROOT/'sources/original'/name).read_text()
        if name=='haversine_script.py':text=text.expandtabs(4)
        defs=[n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)]
        exec(compile(ast.Module(body=defs,type_ignores=[]),name,'exec'),ns)
    rolemap={'train_1':'train1','train_2':'train2','val':'calibration_reference','test':'evaluation'}
    for source,r in rolemap.items():ns['x_'+source]=data[r]['x'];ns['y_'+source]=data[r]['y']
    statements=[];models={}
    with parallel_backend('sequential'),contextlib.redirect_stdout(io.StringIO()):
        for cell,tag in [(5,'DD'),(7,'DDL')]:
            text=''.join(nb['cells'][cell]['source']);nodes=[]
            for n in ast.parse(text).body:
                if isinstance(n,ast.Assign) or (isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and n.value.func.attr=='fit'):
                    nodes.append(n);statements.append({'cell':cell,'line':n.lineno,'end_line':n.end_lineno,'ast_sha256':sha_bytes(ast.dump(n,include_attributes=False).encode()),'source':ast.get_source_segment(text,n)})
            exec(compile(ast.Module(body=nodes,type_ignores=[]),f'source_cell_{cell}','exec'),ns)
            models[tag]=ns['M2']
    models['M1']=ns['M1'];outputs={}
    for source,r in rolemap.items():
        outputs[r]={'position':ns['y_M1_predict_in_'+source],'error':np.asarray(ns['y_M1_error_'+source]),'DD':ns['DAE_in_'+source], 'DDL':ns['DAE_in_'+source+'_M1']}
    if 'calibration_recent' in data:
        x=data['calibration_recent']['x'];y=data['calibration_recent']['y']
        with parallel_backend('sequential'):
            pos=models['M1'].predict(x);dd=models['DD'].predict(x);ddl=models['DDL'].predict(np.concatenate([x,pos],axis=1))
        e=np.asarray(ns['calculate_pairwise_error_list'](y,pos,units))
        outputs['calibration_recent']={'position':pos,'error':e,'DD':dd,'DDL':ddl}
    # Actual composed restoration, not a repeated label on the original arrays.
    x=data['evaluation']['x'];perm=np.random.default_rng(20260922).permutation(len(x));fp=np.arange(x.shape[1])[::-1]
    transformed=x[perm][:,fp];restored=transformed[np.argsort(perm)][:,np.argsort(fp)]
    assert np.array_equal(x,restored)
    with parallel_backend('sequential'):
        pos=models['M1'].predict(restored);dd=models['DD'].predict(restored);ddl=models['DDL'].predict(np.concatenate([restored,pos],axis=1))
    for k,a in [('position',pos),('DD',dd),('DDL',ddl)]:assert np.array_equal(outputs['evaluation'][k],a)
    return models,outputs,statements,{'row_and_feature_inputs_restored_exactly':True,'position_DD_DDL_predictions_restored_exactly':True}

def state_ids(models):
    out={}
    for label,m in models.items():
        hs=[]
        for est in m.estimators_:
            s=est.tree_.__getstate__();hs.append(sha_bytes(np.ascontiguousarray(s['nodes']).tobytes()+np.ascontiguousarray(s['values']).tobytes()))
        out[label]={'params':m.get_params(),'tree_sha256':hs,'state_sha256':sha_bytes(''.join(hs).encode())}
    return out

def check_semantic_state(expected,received,handles,e,h,claimed,integrated=False):
    errors=[]
    if integrated:
        if any(not isinstance(x,RowHandle) for x in handles):raise ContractError('invalid_handle','expected frozen G1 RowHandle')
        if len(set(handles))!=len(handles):errors.append('duplicate_handle')
        for k,v in expected.items():
            if object_hash(v)!=object_hash(received.get(k)):errors.append(k+'_mismatch')
        truth=np.fromiter((float(x)-float(y) for x,y in zip(e,h)),float,count=len(e))
    else:
        # Conventional explicit IDs and numerical checks receive the same information.
        pairs=[(r.payload_sha256,r.source_row_index0) for r in handles]
        if len(set(pairs))!=len(pairs):errors.append('duplicate_handle')
        errors += [k+'_mismatch' for k,v in expected.items() if v!=received.get(k)]
        truth=np.asarray(e)-np.asarray(h)
    if np.shape(claimed)!=truth.shape or not np.allclose(claimed,truth,atol=1e-8,rtol=0):errors.append('signed_quantity_mismatch_offline')
    return sorted(errors)

def scenario_run(archive,scenario,out,p):
    start=time.monotonic();out.mkdir()
    data,prep=get_data(archive,scenario)
    models,outputs,statements,benign=source_models(data,prep['units']);states=state_ids(models)
    write_json(out/'SOURCE_STATEMENTS.json',statements);write_json(out/'MODEL_STATES.json',states)
    pred={};oracle=[]
    for role,d in data.items():
        o=outputs[role];y=d['y'];df=d['rows'].copy()
        df['source_payload_sha256']=[h.payload_sha256 for h in d['handles']]
        df['role']=role;df['true_0']=y[:,0];df['true_1']=y[:,1];df['pred_0']=o['position'][:,0];df['pred_1']=o['position'][:,1]
        df['error_m']=o['error'];df['dd_m']=o['DD'];df['ddl_m']=o['DDL']
        if not np.isfinite(df[['true_0','true_1','pred_0','pred_1','error_m','dd_m','ddl_m']].to_numpy()).all():raise ValueError('nonfinite predictions')
        assert (df[['error_m','dd_m','ddl_m']].to_numpy()>=0).all()
        ref=coordinate_oracle(y,o['position'],prep['units']);delta=float(abs(ref-o['error']).max());assert delta<=p['metric_tolerance_m']
        # A separate scalar Euclidean oracle is additionally used for DSI.
        if prep['units']=='meters':
            scalar=np.array([math.hypot(float(a[0])-float(b[0]),float(a[1])-float(b[1])) for a,b in zip(y,o['position'])]);assert np.max(abs(scalar-o['error']))<=1e-10
        oracle.append({'role':role,'n':len(df),'max_distance_oracle_difference_m':delta,'x_hash':array_hash(d['x']),'y_hash':array_hash(y)})
        save_csv(df,out/(role+'_PREDICTIONS.csv.gz'));pred[role]=df
    e=pred['evaluation'].error_m.to_numpy();N=len(e)
    reftrain=pred['train2'].error_m.to_numpy();constant_mean=float(np.mean(reftrain));constant_med=float(np.median(reftrain))
    point=[];local=[]
    for role,df in pred.items():
        er=df.error_m.to_numpy();local.append({'scenario':scenario,'role':role,'n':len(er),'mean_m':float(er.mean()),'median_m':float(np.median(er)),'p90_m':float(np.quantile(er,.9)),'p95_m':float(np.quantile(er,.95)),'p99_m':float(np.quantile(er,.99)),'max_m':float(er.max())})
        for name,h in [('DD',df.dd_m),('DDL',df.ddl_m),('train2_constant_mean',np.full(len(df),constant_mean)),('train2_constant_median',np.full(len(df),constant_med))]:point.append({'scenario':scenario,'role':role,'model':name,**summaries(er,h)})
    save_csv(pd.DataFrame(point),out/'POINT_SUMMARIES.csv');save_csv(pd.DataFrame(local),out/'LOCALIZATION_SUMMARIES.csv')
    calroles=[r for r in ['calibration_reference','calibration_recent'] if r in pred]
    cov=[];dec=[];curves=[];allrad=[];calstates=[];daily=[]
    landmarks=p['thresholds_m'][scenario]
    grid=np.r_[0,np.logspace(-1,2,121)] if scenario=='dsi' else np.r_[0,np.logspace(0,4,201)]
    for calrole in calroles:
        cal=pred[calrole]
        for alpha in p['alphas']:
            for method in ['DD','DDL','constant']:
                hcal=cal['dd_m' if method=='DD' else 'ddl_m'].to_numpy() if method!='constant' else np.zeros(len(cal))
                h=pred['evaluation']['dd_m' if method=='DD' else 'ddl_m'].to_numpy() if method!='constant' else np.zeros(N)
                q,k=conformal_quantile(cal.error_m.to_numpy()-hcal,alpha);u=np.maximum(0,h+q)
                state={'scenario':scenario,'calibration_role':calrole,'method':method,'alpha':alpha,'n_calibration':len(cal),'rank_k':k,'q_m':q,
                       'position_model':states['M1']['state_sha256'],'error_model':states[method]['state_sha256'] if method!='constant' else 'constant_zero',
                       'score_kind':'actual_error_minus_point_estimate','metric':prep['units'],'feature_hash':object_hash(prep['features']),
                       'calibration_handles_hash':object_hash([(h.payload_sha256,h.source_row_index0) for h in data[calrole]['handles']]),
                       'claim_status':'empirical_only_exchangeability_not_certified','evaluation_handles_hash':object_hash([(h.payload_sha256,h.source_row_index0) for h in data['evaluation']['handles']])}
                state['state_hash']=object_hash(clean_json(state));calstates.append(state)
                cov.append({'scenario':scenario,'calibration_role':calrole,'method':method,'alpha':alpha,**summaries(e,u)})
                for tau in landmarks:dec.append({'scenario':scenario,'calibration_role':calrole,'method':method+'_calibrated','alpha':alpha,**decision_stats(e,u,tau,total_requests=N)})
                if alpha==.05:
                    for tau in grid:curves.append({'scenario':scenario,'calibration_role':calrole,'method':method+'_calibrated','alpha':alpha,**decision_stats(e,u,float(tau),total_requests=N)})
                    if scenario=='lorawan_temporal':
                        for day,ids in pred['evaluation'].groupby('utc_day',sort=True).groups.items():
                            ii=np.asarray(list(ids));daily.append({'scenario':scenario,'day':day,'method':method,'calibration_role':calrole,**summaries(e[ii],u[ii])})
                allrad.append(pd.DataFrame({'scenario':scenario,'calibration_role':calrole,'method':method,'alpha':alpha,'prepared_or_source_row_index0':pred['evaluation'].source_row_index0.to_numpy(),'error_m':e,'radius_m':u,'covered':e<=u,'state_hash':state['state_hash']}))
    for method,h in [('DD_point',pred['evaluation'].dd_m.to_numpy()),('DDL_point',pred['evaluation'].ddl_m.to_numpy()),('train2_mean_point',np.full(N,constant_mean)),('train2_median_point',np.full(N,constant_med))]:
        for tau in landmarks:dec.append({'scenario':scenario,'calibration_role':'none','method':method,'alpha':None,**decision_stats(e,h,tau,total_requests=N)})
        for tau in grid:curves.append({'scenario':scenario,'calibration_role':'none','method':method,'alpha':None,**decision_stats(e,h,float(tau),total_requests=N)})
    save_csv(pd.DataFrame(cov),out/'RADIUS_SUMMARIES.csv');save_csv(pd.DataFrame(dec),out/'DECISION_LANDMARKS.csv');save_csv(pd.DataFrame(curves),out/'DECISION_CURVES.csv.gz');save_csv(pd.concat(allrad,ignore_index=True),out/'RADII.csv.gz')
    write_json(out/'CALIBRATION_STATES.json',calstates)
    if daily:save_csv(pd.DataFrame(daily),out/'ALL_EVALUATION_DAYS.csv')
    # Reuse source expression; this audit is offline and needs labelled errors.
    audits=[]
    for role in ['calibration_reference','evaluation']:
        df=pred[role];er=df.error_m.to_numpy();dd=df.dd_m.to_numpy();dl=df.ddl_m.to_numpy()
        nb=json.loads((ROOT/'sources/original/DAE_Benchmarking_Public.ipynb').read_text());nodes=ast.parse(''.join(nb['cells'][35]['source'])).body[:2]
        ns={'np':np,'y_M1_error_val':er,'DAE_in_val':dd,'DAE_miss_val_M1':np.abs(er-dl)}
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'source_signed_block','exec'),ns)
        wrong=ns['DAE_miss_val_M1_signed'];correct=er-dl
        audits.append({'role':role,'n':len(df),'opposite_strict_signs':int((wrong*correct<0).sum()),'max_absolute_discrepancy_m':float(np.abs(wrong-correct).max()),'published_figure_claim':False,'offline_labels_required':True})
    write_json(out/'SOURCE_EXPRESSION_AUDIT.json',audits)
    h=pred['evaluation'].dd_m.to_numpy();dl=pred['evaluation'].ddl_m.to_numpy()
    handles=data['evaluation']['handles']
    base={'population':object_hash([(r.payload_sha256,r.source_row_index0) for r in handles]),'position_model':states['M1']['state_sha256'],'error_model':states['DD']['state_sha256'],'metric':prep['units'],'quantity':'actual_minus_estimated_error'}
    cases=[('clean_descriptive_evaluation',base,h,e-h,[]),('restored_row_feature_views',base,h,e-h,[]),
           ('source_wrong_signed_quantity',dict(base,error_model=states['DDL']['state_sha256']),dl,e-np.abs(e-dl),['signed_quantity_mismatch_offline']),
           ('incorrect_DD_DDL_binding',dict(base,error_model=states['DDL']['state_sha256']),h,e-h,['error_model_mismatch']),
           ('undeclared_population_drop',dict(base,population='deliberately_incorrect'),h,e-h,['population_mismatch'])]
    controles=[]
    for name,received,hh,claim,expect in cases:
        exp=dict(base)
        if name=='source_wrong_signed_quantity':exp['error_model']=states['DDL']['state_sha256']
        a=check_semantic_state(exp,received,handles,e,hh,claim,False);b=check_semantic_state(exp,received,handles,e,hh,claim,True)
        assert a==b==expect,(name,a,b,expect)
        controles.append({'case':name,'n_requested':N,'strong_conventional_violations':a,'integrated_violations':b,'raw_predictions_available':N,'valid_descriptive_records':N if not a else 0,'offline_reference_uses_labels':name=='source_wrong_signed_quantity'})
    controles.append({'case':'same_digital_contract_cannot_prove_exchangeability','state':'assumption_not_certified','raw_predictions_available':N,'both_routes':'retain descriptive outcomes; do not announce formal arbitrary-shift reliability'})
    if scenario=='lorawan_temporal':controles.append({'case':'truthful_recent_recalibration','state':'valid_changed_experiment','same_position_and_error_models':True,'same_calibration_record_budget':True,'arbitrary_shift_guarantee':False,'note':'Recent recalibration is a disclosed conventional update, not invented shift detection.'})
    write_json(out/'CONTROL_CASES.json',controles)
    write_json(out/'EXECUTION_RECEIPT.json',{'scenario':scenario,'counts':{r:len(d['x']) for r,d in data.items()},'preprocessing':prep,'distance_oracles':oracle,'restoration':benign,'point_train2_mean_m':constant_mean,'point_train2_median_m':constant_med,
              'protocol_hash':sha_bytes((ROOT/'protocol/FOLLOWUP_PROTOCOL.json').read_bytes()),'source_component_execution':True,'full_historical_notebook_replication':False,
              'crosswalk_coordinates_used':False,'radii_count':sum(len(d) for d in allrad),'conventional_integrated_dispositions_equal':True})
    write_json(out/'RUNTIME.json',{'seconds':time.monotonic()-start})
    print('DONE',scenario,'seconds',round(time.monotonic()-start,2),flush=True)

def main(archive,out):
    p=load_protocol()
    if out.exists():raise FileExistsError(out)
    if sha_bytes(archive.read_bytes())!=ARCHIVE_SHA:raise ValueError('wrong archive')
    out.mkdir(parents=True)
    for scenario in ['dsi','lorawan_temporal']:scenario_run(archive,scenario,out/scenario,p)

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--archive',required=True,type=Path);a.add_argument('--out',required=True,type=Path);v=a.parse_args();main(v.archive,v.out)
