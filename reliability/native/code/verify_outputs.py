"""Independent saved-output checks (no fitting, calibration tuning, or new scientific trials)."""
from __future__ import annotations
from pathlib import Path
from fractions import Fraction
import argparse,json,math
import numpy as np,pandas as pd
from common import ROOT,write_json,sha_bytes,load_protocol,coordinate_oracle

def verify(native:Path,reliability:Path,controls:Path,out:Path):
    protocol=load_protocol();checks=[]
    def chk(name,passed,**details):
        checks.append({'check':name,'passed':bool(passed),**details})
        if not passed:raise AssertionError((name,details))
    dfs={part:pd.read_csv(native/f'{part}_PREDICTIONS.csv.gz',float_precision='round_trip') for part in ['train_1','train_2','val','test']}
    for part,d in dfs.items():
        e=coordinate_oracle(d[['true_lat','true_lon']].to_numpy(),d[['pred_lat','pred_lon']].to_numpy(),'lat_lon')
        delta=float(np.abs(e-d.error_m).max());chk('independent geodesic '+part,delta<=1e-5,n=len(d),max_difference_m=delta)
        chk('finite predictions '+part,np.isfinite(d[['true_lat','true_lon','pred_lat','pred_lon','error_m','dd_m','ddl_m']]).all().all())
        chk('nonnegative '+part,(d[['error_m','dd_m','ddl_m']]>=0).all().all())
    trainset=set(dfs['train_1'].group_min_source_index0)|set(dfs['train_2'].group_min_source_index0)
    cal=dfs['val'][dfs['val'].primary_role_eligible];test=dfs['test'][dfs['test'].primary_role_eligible]
    chk('calibration group disjoint',set(cal.group_min_source_index0).isdisjoint(trainset),n=len(cal))
    chk('test group disjoint',set(test.group_min_source_index0).isdisjoint(trainset|set(dfs['val'].group_min_source_index0)),n=len(test))
    chk('requests retained',len(dfs['test'])==8307 and len(test)==8275 and len(cal)==8286)
    states=json.loads((reliability/'CALIBRATION_STATES.json').read_text());qs={}
    for c in states:
        model,alpha=c['method'],c['alpha'];hs=cal['dd_m' if model=='DD' else 'ddl_m'].tolist() if model!='constant' else [0.]*len(cal)
        scores=sorted(float(e)-float(h) for e,h in zip(cal.error_m,hs));n=len(scores)
        k=math.ceil((n+1)*(1-Fraction(str(alpha))));q=scores[k-1] if k<=n else math.inf
        chk(f'order statistic {model}/{alpha}',c['rank_k']==k and c['q_m']==q,n=n,k=k)
        qs[model,alpha]=q
    rad=pd.read_csv(reliability/'ALL_CALIBRATED_TEST_RADII.csv.gz',float_precision='round_trip')
    for (scope,method,alpha),d in rad.groupby(['scope','method','alpha']):
        df=test if scope=='primary_test' else dfs['test'];model=method.removesuffix('_conformal');h=df['dd_m' if model=='DD' else 'ddl_m'].to_numpy() if model!='constant' else np.zeros(len(df));q=qs[model,float(alpha)]
        expected=np.array([max(0.,float(v)+q) for v in h]);chk(f'radius {scope}/{method}/{alpha}',np.array_equal(expected,d.radius_m.to_numpy()) and np.array_equal(df.source_row_index0.to_numpy(),d.source_row_index0.to_numpy()),n=len(df))
    pts=pd.read_csv(reliability/'POINT_ERROR_SUMMARIES.csv',float_precision='round_trip')
    mean=float(dfs['train_2'].error_m.mean());med=float(dfs['train_2'].error_m.median())
    for _,row in pts.iterrows():
        d=cal if row.scope=='primary_calibration' else test if row.scope=='primary_test' else dfs[row.scope]
        h=d.dd_m.to_numpy() if row.model=='DD' else d.ddl_m.to_numpy() if row.model=='DDL' else np.full(len(d),mean if row.model=='constant_mean' else med)
        e=d.error_m.to_numpy();a=np.abs(e-h)
        chk(f'point MAE {row.scope}/{row.model}',abs(float(a.mean())-row.mean_absolute_error_estimation_m)<=1e-9)
        chk(f'point inclusive {row.scope}/{row.model}',abs(float((e<=h).mean())-row.inclusive_coverage)<=1e-15)
    sums=pd.read_csv(reliability/'UPPER_RADIUS_SUMMARIES.csv',float_precision='round_trip')
    for _,row in sums.iterrows():
        d=rad[(rad.scope==row.scope)&(rad.method==row.model+'_conformal')&(rad.alpha==row.alpha)];e=d.actual_error_m.to_numpy();u=d.radius_m.to_numpy()
        chk(f'coverage {row.scope}/{row.model}/{row.alpha}',int((e>u).sum())==int(row.miscovered) and abs(float((e<=u).mean())-row.inclusive_coverage)<1e-15)
        losses=sorted((max(0.,float(a)-float(b)) for a,b in zip(e,u)),reverse=True);mass=Fraction(1,20)*len(losses);whole=mass.numerator//mass.denominator;fraction=float(mass-whole)
        cvar=(sum(losses[:whole])+(fraction*losses[whole] if fraction else 0))/float(mass)
        chk(f'CVaR {row.scope}/{row.model}/{row.alpha}',abs(cvar-row.cvar95_positive_undercoverage_m)<1e-8,tail_mass=float(mass))
    decisions=pd.read_csv(reliability/'DECISION_LANDMARKS.csv',float_precision='round_trip')
    for idx,row in decisions.iterrows():
        d=test if row.scope=='primary_test' else dfs['test'];e=d.error_m.to_numpy()
        if row.method.endswith('_conformal'):
            model=row.method.removesuffix('_conformal');h=d['dd_m' if model=='DD' else 'ddl_m'].to_numpy() if model!='constant' else np.zeros(len(d));u=np.maximum(0,h+qs[model,float(row.alpha)])
        else:u=d.dd_m.to_numpy() if row.method=='native_DD_point' else d.ddl_m.to_numpy() if row.method=='native_DDL_point' else np.full(len(d),mean if row.method=='train2_constant_mean_point' else med)
        n=good=bad=0
        for error,radius in zip(e,u):
            if math.isfinite(radius) and radius<=row.tau_m:
                n+=1
                if error<=row.tau_m:good+=1
                else:bad+=1
        chk('decision row '+str(idx),n==row.accepted and good==row.useful and bad==row.harmful and row.n_requested==8307 and row.n_scored==len(d))
        if n==0:chk('empty conditional risk '+str(idx),pd.isna(row.conditional_accepted_failure))
        else:chk('conditional denominator '+str(idx),abs(bad/n-row.conditional_accepted_failure)<1e-15)
    audit=json.loads((reliability/'SOURCE_SIGNED_EXPRESSION_AUDIT.json').read_text())
    for item in audit:
        d=dfs['val'] if item['scope']=='source_validation' else dfs['test'];e=d.error_m.to_numpy();h=d.ddl_m.to_numpy();s=e-h;wrong=e-np.abs(e-h)
        chk('source sign change '+item['scope'],int(((s*wrong)<0).sum())==item['opposite_strict_signs'] and int((s<0).sum())==item['correct_DDL_overestimation'])
    cs=json.loads((controls/'CONTROL_CASES.json').read_text())
    for c in cs:
        if 'strong_simple_violations' in c:chk('fair-control equality '+c['case'],c['strong_simple_violations']==c['integrated_violations'])
    chk('no fabricated shared corruption detector',cs[-1]['state']=='out_of_scope')
    write_json(out,{'status':'PASSED','n_checks':len(checks),'checks':checks,'scope':'Independent saved-output recomputation; no new trained model or independent deployment','all_native_prediction_records_checked':sum(map(len,dfs.values())),'all_calibrated_radius_records_checked':len(rad),'all_decision_rows_checked':len(decisions)})
    print('VERIFY PASSED',len(checks),'checks')
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--native',type=Path,required=True);a.add_argument('--reliability',type=Path,required=True);a.add_argument('--controls',type=Path,required=True);a.add_argument('--out',type=Path,required=True);v=a.parse_args();verify(v.native,v.reliability,v.controls,v.out)
