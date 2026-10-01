#!/usr/bin/env python3
"""Retrospective task-aligned map-selection proof of work, without new fits.

Consumes unchanged PR1/PR3 and original source inputs. Selection scores contain
no evaluation outcomes. Missing map entries never trigger receiver dropping,
row deletion, re-selection, or a catalogue fallback in the fitted arms.
"""
from __future__ import annotations
import argparse, csv, datetime as dt, gzip, hashlib, io, json, math, platform, sys, zipfile
from pathlib import Path
import numpy as np
import pandas as pd

ARMS = ('NARROW', 'WIDE', 'NARROW_MS', 'WIDE_MS')
PROTOCOL_SHA = '2e647b556c25e562eaac6453bab8a734dc5bab5943ce7825a559efa88e7151f5'


def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()


def save_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+'\n')


def save_frame(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    raw=df.to_csv(index=False,float_format='%.17g').encode()
    if path.name.endswith('.gz'):
        with path.open('wb') as out:
            with gzip.GzipFile(fileobj=out,mode='wb',filename='',mtime=0) as f:f.write(raw)
    else:path.write_bytes(raw)


def select_candidate(scores: dict[str,float], order=ARMS, atol=1e-9) -> str:
    """Only the requested role's scores are accepted; no evaluation data input."""
    if set(scores)!=set(order) or len(set(order))!=len(order):
        raise ValueError('Exact candidate membership required')
    vals=np.array([scores[k] for k in order],float)
    if not np.isfinite(vals).all() or atol<0:raise ValueError('Finite complete scores required')
    best=float(vals.min())
    return next(k for k in order if float(scores[k])<=best+atol)


def select_receptions(rssi: np.ndarray, roster: list[int]) -> tuple[np.ndarray,np.ndarray,np.ndarray]:
    """Fixed numerical-BS order, raw-RSSI stable ties, max ten; -1 means padding."""
    r=np.asarray(rssi,float)
    if r.ndim!=2 or r.shape[1]!=72 or not roster or roster!=sorted(set(roster)) or min(roster)<1 or max(roster)>72:
        raise ValueError('Require N x 72 and sorted unique original roster')
    v=r[:,np.array(roster)-1]
    ok=np.isfinite(v)&(v>=-150)&(v<=-20)
    order=np.argsort(-np.where(ok,v,-np.inf),axis=1,kind='stable')[:,:min(10,len(roster))]
    selected_valid=np.take_along_axis(ok,order,axis=1)
    selected=np.take(np.array(roster),order)
    values=np.take_along_axis(v,order,axis=1)
    return np.where(selected_valid,selected,-1),np.where(selected_valid,values,np.nan),ok.sum(axis=1)>=3


def predict_wcl(selected: np.ndarray, values: np.ndarray, cmap: dict[int,object]):
    selected=np.asarray(selected,int);values=np.asarray(values,float)
    if selected.shape!=values.shape or selected.ndim!=2:raise ValueError('Misaligned selections')
    valid=selected>0
    if np.any(valid&~np.isfinite(values)) or np.any((selected==0)|(selected>72)|(selected< -1)):
        raise ValueError('Malformed selected observations')
    if any(len(set(row[row>0]))!=int(np.sum(row>0)) for row in selected):raise ValueError('Duplicated selected receiver')
    coords=np.full((73,2),np.nan)
    for bs,g in cmap.items():
        if not isinstance(bs,int) or not 1<=bs<=72:raise ValueError('Invalid receiver ID')
        if g is not None:
            g=np.asarray(g,float)
            if g.shape!=(2,) or not np.isfinite(g).all():raise ValueError('Invalid coordinate')
            coords[bs]=g
    g=coords[np.maximum(selected,0)]
    missing=valid&~np.isfinite(g).all(axis=2)
    eligible=valid.sum(axis=1)>=3
    complete=eligible&~missing.any(axis=1)
    weights=np.where(valid,np.power(10.,np.nan_to_num(values,nan=-200)/10.),0.)
    den=weights.sum(axis=1)
    weights=np.divide(weights,den[:,None],out=np.zeros_like(weights),where=den[:,None]>0)
    pred=(np.where(valid[:,:,None],g,0.)*weights[:,:,None]).sum(axis=1)
    pred[~complete]=np.nan
    return pred,complete,missing,weights


def components(key_kinds: list[list[str]], ids: np.ndarray) -> np.ndarray:
    ids=np.asarray(ids,int);parent=np.arange(len(ids))
    if len(set(ids))!=len(ids) or any(len(k)!=len(ids) for k in key_kinds):raise ValueError('Nonunique/misaligned source identities')
    def find(i):
        while parent[i]!=i:
            parent[i]=parent[parent[i]];i=int(parent[i])
        return i
    for keys in key_kinds:
        first={}
        for i,k in enumerate(keys):
            if k in first:
                a,b=find(i),find(first[k]);parent[max(a,b)]=min(a,b)
            else:first[k]=i
    roots=np.array([find(i) for i in range(len(ids))]);mins={}
    for i,r in enumerate(roots):mins[r]=min(mins.get(r,int(ids[i])),int(ids[i]))
    return np.array([mins[r] for r in roots],int)


def summary(errors: np.ndarray) -> dict:
    e=np.asarray(errors,float)
    if e.ndim!=1 or not len(e) or not np.isfinite(e).all():raise ValueError('Invalid scored error cohort')
    return {'scored_n':len(e),'median_error_m':float(np.median(e)),
            'mean_error_m':float(e.mean()),'p90_error_m':float(np.quantile(e,.9))}


def verify_manifest(root: Path):
    m=json.loads((root/'MANIFEST.json').read_text())
    for e in m['files']:
        p=root/e['path']
        if not p.is_file() or p.stat().st_size!=e.get('bytes',e.get('size')) or sha(p)!=e['sha256']:
            raise ValueError('Input changed: '+str(p))
    return len(m['files'])


def s1_read(z: zipfile.ZipFile, suffix: str) -> bytes:
    matches=[n for n in z.namelist() if n.endswith('/'+suffix)]
    if len(matches)!=1:raise ValueError('Ambiguous or missing S1 entry '+suffix)
    return z.read(matches[0])


def load_inputs(args, out):
    p=json.loads(args.protocol.read_text())
    if sha(args.protocol)!=PROTOCOL_SHA:raise ValueError('Protocol differs from locked version')
    if sha(args.s1)!=p['S1_zip_sha256']:raise ValueError('S1 ZIP fingerprint mismatch')
    checks={'PR1_manifest_entries':verify_manifest(args.pr1),'PR3_manifest_entries':verify_manifest(args.pr3)}
    with zipfile.ZipFile(args.csv) as z:
        names=[n for n in z.namelist() if not n.endswith('/') and not n.startswith('__MACOSX/') and not Path(n).name.startswith('._')]
        if len(names)!=1:raise ValueError('Ambiguous raw CSV payload')
        raw=z.read(names[0])
    if hashlib.sha256(raw).hexdigest()!=p['raw_csv_sha256']:raise ValueError('Raw CSV fingerprint mismatch')
    df=pd.read_csv(io.BytesIO(raw));del raw
    with zipfile.ZipFile(args.s1) as z:
        ledger=pd.read_csv(io.BytesIO(s1_read(z,'computational/populations/working_source_ledger.csv.gz')),compression='gzip').sort_values('working_index0')
        cal=pd.read_csv(io.BytesIO(s1_read(z,'computational/populations/calibration_rows.csv')))
        primary=pd.read_csv(io.BytesIO(s1_read(z,'computational/populations/official33_primary_rows.csv')))
        cat={int(k):v for k,v in json.loads(s1_read(z,'computational/data_products/metadata33.json')).items()}
    r=df[[f'BS {i}' for i in range(1,73)]].to_numpy(float)
    valid=np.isfinite(r)&(r>=-150)&(r<=-20)
    rows=np.flatnonzero((valid.sum(axis=1)>=3)&np.isfinite(df.Latitude)&np.isfinite(df.Longitude))
    if len(rows)!=55375 or not np.array_equal(rows,ledger.csv_row_index0):raise ValueError('Working population mismatch')
    xy=ledger[['utm_x','utm_y']].to_numpy(float)
    # Source ledger locations are checked against raw coordinates, not silently trusted.
    import pyproj
    tf=pyproj.Transformer.from_crs(4326,32631,always_xy=True)
    x,y=tf.transform(df.Longitude.iloc[rows].to_numpy(),df.Latitude.iloc[rows].to_numpy())
    if np.max(abs(xy-np.column_stack([x,y])))>1e-7:raise ValueError('Projection mismatch')
    r=r[rows]
    serial=[]
    for rowid,rv in zip(rows,r):
        row=df.iloc[int(rowid)]
        k=(str(row['RX Time']),int(row.SF),round(float(row.HDOP),2),tuple(sorted(int(rv[j]) for j in np.flatnonzero(rv!=-200))))
        serial.append(hashlib.sha256(json.dumps(k,separators=(',',':')).encode()).hexdigest())
    cc=components([ledger.legacy_content_sha256.astype(str).tolist(),serial],rows)
    calrows=set(map(int,cal.csv_row_index0));prows=set(map(int,primary.csv_row_index0))
    blocked=np.isin(rows,list(calrows|prows));badgroups=set(map(int,cc[blocked]));blocked=np.isin(cc,list(badgroups))
    compwi=np.flatnonzero(~blocked)
    if any(set(np.array(k)[compwi])&set(np.array(k)[blocked]) for k in [serial,list(ledger.legacy_content_sha256)]):raise AssertionError('Grouping leaked')
    exclusions=['original_calibration' if int(v) in calrows else 'old_primary' if int(v) in prows else 'duplicate_connected_to_prior_roles' if b else 'complement' for v,b in zip(rows,blocked)]
    pop=ledger[['csv_row_index0','working_index0','legacy_content_sha256']].copy()
    pop['serialization_sha256']=serial;pop['component_min_csv_row0']=cc;pop['PR4_role']=exclusions
    save_frame(out/'SOURCE_ROLE_LEDGER.csv.gz',pop)
    checks.update({'raw_rows':len(df),'working_rows':len(rows),'original_calibration_n':len(calrows),'old_primary_n':len(prows),
                   'complement_request_n':len(compwi),'connected_duplicate_exclusions':exclusions.count('duplicate_connected_to_prior_roles'),
                   'whole_working_components':len(set(cc)),'disjoint_content_and_serialization':True})
    save_json(out/'INPUT_POPULATION_CHECKS.json',checks)
    return p,rows,r,xy,cal,primary,cat,serial,compwi


def evaluate_role(split,role,wi,rows,r,xy,cat,models,out):
    roster=sorted(cat);selected,values,eligible=select_receptions(r[wi],roster)
    maps={'CAT':cat,**{a:{int(bs):(None if m is None else m['coordinate']) for bs,m in models[a].items()} for a in ARMS}}
    outputs={a:predict_wcl(selected,values,m) for a,m in maps.items()}
    common=np.logical_and.reduce([v[1] for v in outputs.values()])
    if any(not np.array_equal(common,outputs[a][1]) for a in ARMS):raise ValueError('Candidate support differs; policy comparison would be confounded')
    cohort_hash=hashlib.sha256(np.asarray(rows[wi][common],dtype='<i8').tobytes()).hexdigest()
    err={};summ=[];frames=[];scalar_count=0;maxdiff=0.
    selected_text=[';'.join(map(str,row[row>0])) for row in selected]
    values_text=[';'.join(map(str,row[np.isfinite(row)])) for row in values]
    for a,(g,available,missing,w) in outputs.items():
        e=np.linalg.norm(g-xy[wi],axis=1);err[a]=e
        row={'split':split,'role':role,'arm':a,'requested_n':len(wi),'eligible_original_roster_n':int(eligible.sum()),
          'available_n':int(available.sum()),'common_n':int(common.sum()),'common_cohort_sha256':cohort_hash,**summary(e[common])}
        summ.append(row)
        frame=pd.DataFrame({'split':split,'role':role,'arm':a,'csv_row_index0':rows[wi],'working_index0':wi,
           'selected_receivers':selected_text,'selected_rssi_dbm':values_text,'eligible_original_roster':eligible,
           'common_complete':common,'available':available,
           'status':np.where(~eligible,'insufficient_original_roster_support',np.where(available,'available','missing_fitted_coordinate')),
           'missing_receivers':[';'.join(map(str,s[m])) for s,m in zip(selected,missing)],
           'reference_x':xy[wi,0],'reference_y':xy[wi,1],'pred_x':g[:,0],'pred_y':g[:,1],'error_m':e})
        frames.append(frame)
        # Alternate scalar expression, math.fsum, every available prediction.
        for j in np.flatnonzero(available):
            s=selected[j];rv=values[j];ss=s[s>0];rr=rv[s>0]
            ws=[10.**(float(v)/10.) for v in rr];den=math.fsum(ws)
            gg=np.array([math.fsum(wi*float(maps[a][int(bs)][k]) for wi,bs in zip(ws,ss))/den for k in (0,1)])
            delta=float(np.linalg.norm(gg-g[j]));maxdiff=max(maxdiff,delta);scalar_count+=1
            if delta>1e-7:raise AssertionError('Alternate WCL sum mismatch')
    save_frame(out/f'{split}_{role}_PREDICTIONS.csv.gz',pd.concat(frames,ignore_index=True))
    save_frame(out/f'{split}_{role}_COMMON_ROWS.csv',pd.DataFrame({'csv_row_index0':rows[wi][common]}))
    return err,common,summ,{'split':split,'role':role,'scalar_predictions_checked':scalar_count,'max_scalar_position_difference_m':maxdiff,
                           'requested_n':len(wi),'eligible_n':int(eligible.sum()),'common_n':int(common.sum()),'cohort_sha256':cohort_hash}


def run(args):
    out=args.out.resolve()
    for src in [args.pr1.resolve(),args.pr3.resolve()]:
        if out.is_relative_to(src):raise ValueError('Output must be separate from input')
    out.mkdir(parents=True,exist_ok=False)
    started=dt.datetime.now(dt.timezone.utc).isoformat()
    p,rows,r,xy,cal,primary,cat,serial,compwi=load_inputs(args,out)
    allsum=[];checks=[];choices=[];policyrows=[];inputs=[]
    for split in p['splits']:
        sr=args.pr3/'results'/split;pf=args.pr1/'results/preflight'/split
        models=json.loads((sr/'models.json').read_text());rdf=pd.read_csv(sr/'receiver_results.csv')
        sd=pd.read_csv(pf/'split_rows.csv.gz')
        if not np.array_equal(sd.csv_row_index0,cal.csv_row_index0):raise ValueError('Original calibration order mismatch')
        if not np.array_equal(np.array(serial)[sd.working_index0],sd.serialization_sha256):raise ValueError('Serialization key mismatch')
        valwi=sd.loc[sd.role=='validation','working_index0'].to_numpy(int)
        fitwi=sd.loc[sd.role=='fitting','working_index0'].to_numpy(int)
        if len(set(valwi)&set(fitwi)):raise ValueError('Fit/validation overlap')
        inputs.extend([{'path':str(x),'sha256':sha(x)} for x in [sr/'models.json',sr/'receiver_results.csv',sr/'all_reception_predictions.csv.gz',pf/'split_rows.csv.gz']])
        ve,vc,sm,ck=evaluate_role(split,'validation',valwi,rows,r,xy,cat,models,out);allsum+=sm;checks.append(ck)
        task_scores={a:float(np.median(ve[a][vc])) for a in ARMS}
        train_scores={a:float(rdf.loc[(rdf.arm==a)&(rdf.fit_status=='available'),'training_loss_db'].median()) for a in ARMS}
        val_rssi_scores={a:float(rdf.loc[(rdf.arm==a)&(rdf.fit_status=='available')&(rdf.validation_n>0),'validation_median_abs_db'].median()) for a in ARMS}
        rec=pd.read_csv(sr/'all_reception_predictions.csv.gz');recs=rec[rec.role=='validation'].copy()
        supported=np.logical_and.reduce([np.isfinite(recs[a+'_signed_residual_db']) for a in ARMS])
        pooled_scores={a:float(np.median(abs(recs.loc[supported,a+'_signed_residual_db']))) for a in ARMS}
        score_by_policy={'TASK_VAL':task_scores,'TRAIN_RSSI':train_scores,'VAL_RSSI_EQUAL':val_rssi_scores,'VAL_RSSI_POOLED':pooled_scores}
        selection={k:select_candidate(v) for k,v in score_by_policy.items()};selection['NATIVE_FIXED']='NARROW'
        freeze={'split':split,'protocol_sha256':PROTOCOL_SHA,'selection':selection,'scores':score_by_policy,
                'selection_uses_evaluation_labels':False,'new_complement_errors_computed_before_freeze':False,
                'known_original_PR3_outcomes_informed_researcher_design':True,'validation_row_sha256':ck['cohort_sha256']}
        dest=out/f'{split}_SELECTION_FROZEN.json';save_json(dest,freeze);selected_sha=sha(dest)
        choices.append({'split':split,'selection_file_sha256':selected_sha,**selection})
        # Only now compute the complementary cohort. Original primary is checked too.
        for role,wi in [('complement',compwi),('old_primary',primary.working_index0.to_numpy(int))]:
            ee,common,sm,ck=evaluate_role(split,role,wi,rows,r,xy,cat,models,out);allsum+=sm;checks.append(ck)
            if sha(dest)!=selected_sha:raise AssertionError('Selection mutated during scoring')
            if role=='old_primary':
                old=pd.read_csv(sr/'raw_wcl_predictions.csv.gz')
                for a in ['CAT',*ARMS]:
                    og=old[old.arm==a]
                    if not np.array_equal(og.csv_row_index0,rows[wi]) or not np.array_equal(og.common_complete,common):raise AssertionError('Primary pairing changed')
                    if not np.allclose(og.error_m.to_numpy(float),ee[a],rtol=0,atol=1e-7,equal_nan=True):raise AssertionError('Primary prediction changed')
            catmed=float(np.median(ee['CAT'][common]));trainmed=float(np.median(ee[selection['TRAIN_RSSI']][common]))
            native=float(np.median(ee['NARROW'][common]))
            for pol,chosen in selection.items():
                stats=summary(ee[chosen][common]);med=stats['median_error_m']
                policyrows.append({'split':split,'role':role,'policy':pol,'chosen_map':chosen,'requested_n':len(wi),
                     'common_cohort_sha256':ck['cohort_sha256'],**stats,'difference_of_medians_vs_TRAIN_RSSI_m':med-trainmed,
                     'relative_median_change_vs_TRAIN_RSSI_pct':100*(med/trainmed-1),
                     'relative_median_change_vs_NATIVE_pct':100*(med/native-1),'ratio_to_matched_CAT':med/catmed})
        print(split,'choices',selection,flush=True)
    save_frame(out/'ALL_CANDIDATE_SUMMARIES.csv',pd.DataFrame(allsum))
    save_frame(out/'POLICY_OUTCOMES.csv',pd.DataFrame(policyrows))
    save_json(out/'FROZEN_CHOICES.json',choices);save_json(out/'NUMERICAL_CHECKS.json',checks)
    save_json(out/'INPUT_IDENTITIES.json',inputs)
    ending={'PR1_manifest_entries':verify_manifest(args.pr1),'PR3_manifest_entries':verify_manifest(args.pr3)}
    if sha(args.protocol)!=PROTOCOL_SHA:raise AssertionError('Protocol changed')
    save_json(out/'COMPLETE.json',{'status':'COMPLETE','protocol_sha256':PROTOCOL_SHA,'started_utc':started,
        'completed_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'argv':sys.argv,'environment':{'python':sys.version,'numpy':np.__version__,'pandas':pd.__version__,'platform':platform.platform()},
        'new_coordinate_fits':0,'new_calibration_validation_WCL':True,'new_complement_WCL':True,
        'original_primary_outputs_reproduced':True,'postrun_preservation':ending,
        'scope':'Retrospective selector proof of work; no independent deployment, no untouched-data certification, no statistical population inference, no new estimator.'})
    print(pd.DataFrame(policyrows).to_string(index=False),flush=True)


def main():
    ap=argparse.ArgumentParser()
    for x in ['pr1','pr3','s1','csv','protocol','out']:ap.add_argument('--'+x,type=Path,required=True)
    args=ap.parse_args()
    try:run(args)
    except Exception as e:
        print(type(e).__name__+': '+str(e),file=sys.stderr);raise

if __name__=='__main__':main()
