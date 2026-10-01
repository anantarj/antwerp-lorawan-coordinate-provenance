"""Independent read-only verification of follow-up predictions and reporting.

This verifier reconstructs all scalar metrics, ranks and decisions from retained
predictions. It does not refit models and is not an independent field replication.
"""
from pathlib import Path
import argparse,ast,json,math,sys
from fractions import Fraction
import numpy as np,pandas as pd
from pyproj import Geod
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'sources/inherited'))
from common import sha_bytes,write_json

def csv(p):return pd.read_csv(p,float_precision='round_trip')
def independent_tail(a,beta=.95):
    v=np.sort(np.asarray(a,float))[::-1];mass=(1-beta)*len(v)
    if mass==0:return None
    full=int(math.floor(mass));frac=mass-full
    return float((sum(v[:full])+frac*v[full] if full<len(v) else sum(v[:full]))/mass)

def verify(result,out):
    if out.exists():raise FileExistsError(out)
    checks=[]
    def ck(name,condition,detail=None):
        checks.append({'check':name,'pass':bool(condition),'detail':detail})
        if not condition:raise AssertionError((name,detail))
    def close(name,a,b,tol=1e-7):
        aa=float(a);bb=float(b)
        good=(math.isnan(aa) and math.isnan(bb)) or aa==bb or (math.isfinite(aa) and math.isfinite(bb) and abs(aa-bb)<=tol)
        ck(name,good,{'left':a,'right':b})
    p=json.loads((ROOT/'protocol/FOLLOWUP_PROTOCOL.json').read_text())
    gate=json.loads((ROOT/'checks/PRE_EXECUTION_GATE.json').read_text())
    for rel,h in gate['files'].items():ck('execution-input:'+rel,sha_bytes((ROOT/rel).read_bytes())==h)
    total_predictions=0;total_radii=0;total_decisions=0
    for s in ['dsi','lorawan_temporal']:
        b=result/s;dfs={x.name.replace('_PREDICTIONS.csv.gz',''):csv(x) for x in b.glob('*_PREDICTIONS.csv.gz')}
        eval=dfs['evaluation'];N=len(eval);ck(s+':eval-count',N==(115 if s=='dsi' else 4873))
        for role,d in dfs.items():
            yy=d[['true_0','true_1']].to_numpy();pred=d[['pred_0','pred_1']].to_numpy();e=d.error_m.to_numpy()
            if s=='dsi':ref=np.array([math.hypot(float(x[0])-float(y[0]),float(x[1])-float(y[1])) for x,y in zip(yy,pred)])
            else:
                g=Geod(a=6371008.8,b=6371008.8);ref=np.asarray(g.inv(yy[:,1],yy[:,0],pred[:,1],pred[:,0])[2])
            ck(s+':metric:'+role,np.max(abs(e-ref))<=1e-5,float(np.max(abs(e-ref))))
            ck(s+':finite:'+role,np.isfinite(d[['error_m','dd_m','ddl_m']].to_numpy()).all())
            ck(s+':unique-handles:'+role,not d[['source_payload_sha256','source_row_index0']].duplicated().any())
            total_predictions+=len(d)
        states=json.loads((b/'CALIBRATION_STATES.json').read_text());rad=csv(b/'RADII.csv.gz');summary=csv(b/'RADIUS_SUMMARIES.csv');total_radii+=len(rad)
        arrays={}
        for st in states:
            cal=dfs[st['calibration_role']];model=st['method'];alpha=st['alpha'];n=len(cal)
            score=cal.error_m.to_numpy()-(cal.dd_m.to_numpy() if model=='DD' else cal.ddl_m.to_numpy() if model=='DDL' else 0)
            rank=math.ceil(Fraction(n+1)*(1-Fraction(str(alpha))))
            q=float(np.partition(score,rank-1)[rank-1]) if rank<=n else float('inf')
            prefix=f'{s}:{st["calibration_role"]}:{model}:{alpha}'
            ck(prefix+':rank',rank==st['rank_k'])
            sq=float(st['q_m']);close(prefix+':quantile',q,sq)
            h=eval.dd_m.to_numpy() if model=='DD' else eval.ddl_m.to_numpy() if model=='DDL' else np.zeros(N)
            u=np.maximum(0,h+q);er=eval.error_m.to_numpy();a=rad[(rad.calibration_role==st['calibration_role'])&(rad.method==model)&(rad.alpha==alpha)]
            ck(prefix+':records',len(a)==N and np.array_equal(a.prepared_or_source_row_index0,eval.source_row_index0))
            ck(prefix+':all-radii',np.allclose(u,a.radius_m.to_numpy(),atol=1e-8,rtol=0))
            ck(prefix+':events',np.array_equal(er<=u,a.covered.to_numpy()))
            ck(prefix+':state-binding',bool((a.state_hash==st['state_hash']).all()))
            rr=summary[(summary.calibration_role==st['calibration_role'])&(summary.method==model)&(summary.alpha==alpha)].iloc[0]
            close(prefix+':coverage',(er<=u).mean(),rr.inclusive_coverage)
            close(prefix+':exceedances',int((er>u).sum()),rr.miscovered)
            close(prefix+':radius-mean',float(np.mean(u)),rr.mean_radius_m)
            loss=np.maximum(er-u,0)
            close(prefix+':max-undercoverage',float(loss.max()),rr.max_positive_undercoverage_m)
            close(prefix+':expected-shortfall',independent_tail(loss),rr.cvar95_positive_undercoverage_m)
            arrays[(st['calibration_role'],model+'_calibrated',alpha)]=u
        means=dfs['train2'].error_m.mean();median=dfs['train2'].error_m.median()
        arrays.update({('none','DD_point',None):eval.dd_m.to_numpy(),('none','DDL_point',None):eval.ddl_m.to_numpy(),('none','train2_mean_point',None):np.full(N,means),('none','train2_median_point',None):np.full(N,median)})
        for file in ['DECISION_LANDMARKS.csv','DECISION_CURVES.csv.gz']:
            ds=csv(b/file);errs=eval.error_m.to_numpy();total_decisions+=len(ds)
            for k,r in ds.iterrows():
                alpha=None if pd.isna(r.alpha) else float(r.alpha);u=arrays[(r.calibration_role,r.method,alpha)]
                accepted_mask=np.isfinite(u)&(u<=r.tau_m)
                count=int(accepted_mask.sum());good=int(np.count_nonzero(accepted_mask&(errs<=r.tau_m)));bad=count-good
                prefix=f'{s}:{file}:{k}'
                ck(prefix+':counts',int(r.accepted)==count and int(r.useful)==good and int(r.harmful)==bad and int(r.n_requested)==N)
                close(prefix+':conditional',bad/count if count else float('nan'),r.conditional_accepted_failure)
                close(prefix+':useful-all',good/N,r.useful_fraction_requests)
                close(prefix+':harmful-all',bad/N,r.harmful_fraction_requests)
        points=csv(b/'POINT_SUMMARIES.csv')
        for _, r in points.iterrows():
            frame=dfs[r.role]; ee=frame.error_m.to_numpy(); model=r.model
            hh=frame.dd_m.to_numpy() if model=='DD' else frame.ddl_m.to_numpy() if model=='DDL' else np.full(len(ee),means if model=='train2_constant_mean' else median)
            for field,value in [('mean_absolute_error_estimation_m',np.mean(np.abs(ee-hh))),('inclusive_coverage',np.mean(ee<=hh)),('strict_overestimation_fraction',np.mean(ee<hh)),('equal_fraction',np.mean(ee==hh)),('mean_radius_m',np.mean(hh))]:
                close(s+':point:'+r.role+':'+model+':'+field,r[field],value)
        loc=csv(b/'LOCALIZATION_SUMMARIES.csv')
        for _,r in loc.iterrows():
            e=dfs[r.role].error_m.to_numpy();prefix=s+':localization:'+r.role
            for field,expected in [('mean_m',e.mean()),('median_m',np.median(e)),('p90_m',np.quantile(e,.9)),('p95_m',np.quantile(e,.95)),('p99_m',np.quantile(e,.99)),('max_m',e.max())]:close(prefix+':'+field,r[field],expected)
        audits=json.loads((b/'SOURCE_EXPRESSION_AUDIT.json').read_text())
        for a in audits:
            df=dfs[a['role']];ee=df.error_m.to_numpy();hh=df.ddl_m.to_numpy();true=ee-hh;wrong=ee-abs(ee-hh)
            ck(s+':source-signs:'+a['role'],a['opposite_strict_signs']==int((true*wrong<0).sum()))
        controls=json.loads((b/'CONTROL_CASES.json').read_text())
        for c in controls:
            if 'strong_conventional_violations' in c:ck(s+':control-tie:'+c['case'],c['strong_conventional_violations']==c['integrated_violations'])
        ms=json.loads((b/'MODEL_STATES.json').read_text())
        for model,st in ms.items():
            ck(s+':trees:'+model,len(st['tree_sha256'])==100)
            for key,val in p['models'].items():
                if key!='parallel_backend':ck(s+':param:'+model+':'+key,st['params'][key]==val)
        if s=='lorawan_temporal':
            # Same models bind both calibration states; only data and order statistic change.
            ck('fixed-model-across-calibration-states',len({st['position_model'] for st in states})==1)
            ck('equal-calibration-budget',len(dfs['calibration_reference'])==len(dfs['calibration_recent'])==4835)
            for role in ['train1','train2','calibration_reference','calibration_recent']:
                ck('no-future-observations:'+role,pd.to_datetime(dfs[role].timestamp_utc,utc=True,format="ISO8601").max()<pd.to_datetime(eval.timestamp_utc,utc=True,format="ISO8601").min())
            for i,a in enumerate(dfs):
                for bb in list(dfs)[i+1:]:ck('disjoint-component-roles:'+a+':'+bb,set(dfs[a].group_min_source_index0).isdisjoint(set(dfs[bb].group_min_source_index0)))
            daily=csv(b/'ALL_EVALUATION_DAYS.csv')
            for i,r in daily.iterrows():
                ee=eval.error_m.to_numpy();u=arrays[(r.calibration_role,r.method+'_calibrated',.05)];ii=eval.utc_day==r.day
                close('daily-coverage:'+str(i),float(np.mean(ee[ii]<=u[ii])),r.inclusive_coverage)
                ck('daily-count:'+str(i),int(ii.sum())==r.n)
    resultinfo={'scope':'Independent retained-output recomputation; not model refitting or independent external replication','passed':all(c['pass'] for c in checks),'checks':len(checks),'prediction_records':total_predictions,'radius_records':total_radii,'decision_rows':total_decisions,'details':checks}
    write_json(out,resultinfo);print(json.dumps({k:v for k,v in resultinfo.items() if k!='details'},indent=2))

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--results',type=Path,required=True);a.add_argument('--out',type=Path,required=True);v=a.parse_args();verify(v.results,v.out)
