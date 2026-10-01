"""Source-expression audit and prespecified descriptive reliability calibration.

No model or threshold is selected from evaluation errors. All scheduled controls,
calibration levels, retained/omitted cases and denominators are exported.
"""
from __future__ import annotations
from pathlib import Path
import argparse,json
import numpy as np,pandas as pd
from common import *

def read_predictions(root:Path,part:str)->pd.DataFrame:
    return pd.read_csv(root/f'{part}_PREDICTIONS.csv.gz',float_precision='round_trip')

def summaries(e,u):
    e,u=np.asarray(e,float),np.asarray(u,float);s=e-u;under=np.maximum(s,0)
    finite=np.isfinite(u)
    d={'n':len(e),'inclusive_coverage':float((e<=u).mean()),'strict_overestimation_fraction':float((e<u).mean()),'equal_fraction':float((e==u).mean()),'miscovered':int((e>u).sum()),'mean_positive_undercoverage_m':float(under.mean()),'cvar95_positive_undercoverage_m':empirical_cvar(under,.95),'max_positive_undercoverage_m':float(under.max()),'finite_radii':int(finite.sum())}
    if finite.all():
        d.update({'mean_radius_m':float(u.mean()),'mean_absolute_error_estimation_m':float(np.abs(s).mean())})
        for q in [.5,.9,.95,.99]:d[f'radius_q{q}_m']=float(np.quantile(u,q));d[f'positive_undercoverage_q{q}_m']=float(np.quantile(under,q))
    else:d['mean_radius_m']=float('inf')
    return d

def evaluate(native:Path,inputs:Path,out:Path):
    p=load_protocol()
    if out.exists():raise FileExistsError(out)
    out.mkdir(parents=True)
    dfs={s:read_predictions(native,s) for s in ['train_1','train_2','val','test']}
    counts={s:len(d) for s,d in dfs.items()}
    cal=dfs['val'][dfs['val'].primary_role_eligible].copy();test=dfs['test'][dfs['test'].primary_role_eligible].copy()
    assert len(cal)==8286 and len(test)==8275
    assert set(cal.group_min_source_index0).isdisjoint(set(dfs['train_1'].group_min_source_index0)|set(dfs['train_2'].group_min_source_index0))
    assert set(test.group_min_source_index0).isdisjoint(set(cal.group_min_source_index0))
    point_rows=[];local_rows=[]
    means=float(dfs['train_2'].error_m.mean());med=float(dfs['train_2'].error_m.median())
    for scope,d in list(dfs.items())+[('primary_calibration',cal),('primary_test',test)]:
        e=d.error_m.to_numpy();local={'scope':scope,'n':len(d),'mean_m':float(e.mean()),'max_m':float(e.max())}
        for q in [.5,.9,.95,.99]:local[f'q{q}_m']=float(np.quantile(e,q))
        local_rows.append(local)
        for name,h in [('DD',d.dd_m.to_numpy()),('DDL',d.ddl_m.to_numpy()),('constant_mean',np.full(len(d),means)),('constant_median',np.full(len(d),med))]:
            point_rows.append({'scope':scope,'model':name,**summaries(e,h)})
    pd.DataFrame(point_rows).to_csv(out/'POINT_ERROR_SUMMARIES.csv',index=False,float_format='%.17g')
    pd.DataFrame(local_rows).to_csv(out/'LOCALIZATION_SUMMARIES.csv',index=False,float_format='%.17g')
    calibrations=[];coverage=[];decisions=[];fullcurve=[];radii=[]
    state=json.loads((native/'MODEL_STATE_IDENTITIES.json').read_text())
    calhash=array_hash(cal.source_row_index0.to_numpy(np.int64));featurehash=object_hash([f'BS {i}' for i in range(1,73)])
    for alpha in p['calibration']['alphas']:
        for model in ['DD','DDL','constant']:
            hc=cal['dd_m' if model=='DD' else 'ddl_m'].to_numpy() if model!='constant' else np.zeros(len(cal))
            scores=cal.error_m.to_numpy()-hc;q,k=conformal_quantile(scores,alpha)
            cs={'method':model,'alpha':alpha,'n_calibration':len(cal),'rank_k':k,'q_m':q,'model_M1_sha256':state['M1']['state_sha256'],'error_estimator_sha256':state[model]['state_sha256'] if model!='constant' else 'none_constant_zero','calibration_role_hash':calhash,'metric':p['metric']['id'],'quantity':'actual_error_minus_point_error_estimate','feature_hash':featurehash,'source_scope':'native_M1_DD_DDL_with_group_excluded_calibration','conditional_theorem_only':True}
            cs['calibration_state_sha256']=object_hash(clean_json(cs));calibrations.append(cs)
            for scope,d in [('primary_test',test),('native_all_test',dfs['test'])]:
                e=d.error_m.to_numpy();h=d['dd_m' if model=='DD' else 'ddl_m'].to_numpy() if model!='constant' else np.zeros(len(d))
                u=np.maximum(0,h+q)
                coverage.append({'scope':scope,'model':model,'alpha':alpha,**summaries(e,u)})
                for tau in p['endpoints']['thresholds_m']:
                    decisions.append({'scope':scope,'method':model+'_conformal','alpha':alpha,**decision_stats(e,u,tau,total_requests=len(dfs['test']))})
                if scope=='primary_test' and alpha==.05:
                    for tau in np.r_[0,np.logspace(0,4,201)]:fullcurve.append({'method':model+'_conformal','alpha':alpha,**decision_stats(e,u,float(tau),total_requests=len(dfs['test']))})
                d0=pd.DataFrame({'source_row_index0':d.source_row_index0.to_numpy(),'scope':scope,'method':model+'_conformal','alpha':alpha,'actual_error_m':e,'radius_m':u,'inclusive_covered':e<=u})
                radii.append(d0)
    for scope,d in [('primary_test',test),('native_all_test',dfs['test'])]:
        e=d.error_m.to_numpy()
        for model,h in [('native_DD_point',d.dd_m.to_numpy()),('native_DDL_point',d.ddl_m.to_numpy()),('train2_constant_mean_point',np.full(len(d),means)),('train2_constant_median_point',np.full(len(d),med))]:
            for tau in p['endpoints']['thresholds_m']:decisions.append({'scope':scope,'method':model,'alpha':None,**decision_stats(e,h,tau,total_requests=len(dfs['test']))})
            if scope=='primary_test':
                for tau in np.r_[0,np.logspace(0,4,201)]:fullcurve.append({'method':model,'alpha':None,**decision_stats(e,h,float(tau),total_requests=len(dfs['test']))})
    pd.DataFrame(coverage).to_csv(out/'UPPER_RADIUS_SUMMARIES.csv',index=False,float_format='%.17g')
    pd.DataFrame(decisions).to_csv(out/'DECISION_LANDMARKS.csv',index=False,float_format='%.17g')
    pd.DataFrame(fullcurve).to_csv(out/'DECISION_CURVES.csv.gz',index=False,float_format='%.17g',compression={'method':'gzip','mtime':0})
    pd.concat(radii).to_csv(out/'ALL_CALIBRATED_TEST_RADII.csv.gz',index=False,float_format='%.17g',compression={'method':'gzip','mtime':0})
    write_json(out/'CALIBRATION_STATES.json',calibrations)
    # Execute the source variable expression as written, then compare with the declared signed residual.
    audits=[];arrays=[]
    nb=json.loads((ROOT/'sources/original/DAE_Benchmarking_Public.ipynb').read_text())
    import ast
    nodes=ast.parse(''.join(nb['cells'][35]['source'])).body[:2]
    original=compile(ast.Module(body=nodes,type_ignores=[]),'source_cell35_first_two_assignments','exec')
    for scope,d in [('source_validation',dfs['val']),('new_test_audit',dfs['test'])]:
        e=d.error_m.to_numpy();dd=d.dd_m.to_numpy();ddl=d.ddl_m.to_numpy()
        ns={'np':np,'y_M1_error_val':e,'DAE_in_val':dd,'DAE_miss_val_M1':np.abs(e-ddl)}
        exec(original,ns);wrong=ns['DAE_miss_val_M1_signed'];correct=e-ddl
        signs=np.sign(wrong)!=np.sign(correct)
        audits.append({'scope':scope,'n':len(e),'source_expression':'e - abs(e - DDL)','correct_quantity':'e - DDL','different_values':int((wrong!=correct).sum()),'opposite_strict_signs':int(((wrong*correct)<0).sum()),'sign_category_disagreement':int(signs.sum()),'correct_DDL_overestimation':int((correct<0).sum()),'source_expression_negative':int((wrong<0).sum()),'correct_DDL_underestimation':int((correct>0).sum()),'source_expression_positive':int((wrong>0).sum()),'max_abs_discrepancy_m':float(np.abs(wrong-correct).max()),'native_metric_function_correct_DDL_input':True,'first_plotted_label_in_source':'DD attached to erroneous DDL expression','second_plotted_label_in_source':'DDL attached to DD signed residual','deployment_detector':False,'published_figure_authentication':False})
        arrays.append(pd.DataFrame({'scope':scope,'source_row_index0':d.source_row_index0,'actual_error_m':e,'DD_point_m':dd,'DDL_point_m':ddl,'source_first_plotted_signed_m':wrong,'correct_DDL_signed_m':correct,'correct_DD_signed_m':e-dd}))
    write_json(out/'SOURCE_SIGNED_EXPRESSION_AUDIT.json',audits)
    pd.concat(arrays).to_csv(out/'SIGNED_EXPRESSION_RECORDS.csv.gz',index=False,float_format='%.17g',compression={'method':'gzip','mtime':0})
    n=len(dfs['val']);k=np.arange(1,n)
    write_json(out/'SOURCE_SELECTION_AXIS_AUDIT.json',{'n':n,'native_prefix_counts':[1,n-1],'source_x_first':0,'correct_first_percent':100/n,'max_axis_error_percentage_points':float(np.abs(100*(k-1)/(n-1)-100*k/n).max()),'source_full_N_endpoint_missing':True,'no_new_model_selection':True})
    # Empirical pair differences are descriptive, not independently replicated significance findings.
    write_json(out/'EVALUATION_RECEIPT.json',{'protocol_sha256':sha_bytes((ROOT/'protocol/EXECUTION_PROTOCOL.json').read_bytes()),'native_counts':counts,'primary_calibration_n':len(cal),'primary_test_n':len(test),'original_test_requests':len(dfs['test']),'group_exclusions_calibration':len(dfs['val'])-len(cal),'group_exclusions_test':len(dfs['test'])-len(test),'calibration_states':len(calibrations),'radius_summary_rows':len(coverage),'decision_landmark_rows':len(decisions),'point_summary_rows':len(point_rows),'predictions_not_withheld_by_radio_model':True,'main_conformal_level':.05,'no_deployment_threshold_claim':True,'no_cross_deployment_or_conditional_risk_guarantee':True})
    print('EVALUATION COMPLETE',out)
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--native',type=Path,required=True);a.add_argument('--inputs',type=Path,required=True);a.add_argument('--out',type=Path,required=True);v=a.parse_args();evaluate(v.native,v.inputs,v.out)
