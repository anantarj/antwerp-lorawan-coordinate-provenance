#!/usr/bin/env python3
"""Independent row/summary audit and matched temporal map bridge.

Uses raw CSV for identities, timestamps, RSSI and ground truth; reuses unchanged
legacy localization kernels for the new bridge, not the prior temporal driver.
"""
from __future__ import annotations
import argparse,collections,hashlib,importlib.util,json,random,sys
from pathlib import Path
import numpy as np
import pandas as pd
from pyproj import Transformer

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):Path(p).write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
def load_module(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--stage',type=Path,required=True);ap.add_argument('--data',type=Path,required=True);ap.add_argument('--original',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False);checks={}
 def ck(k,v,detail=None):
  checks[k]={'pass':bool(v),'detail':detail}
  if not v:raise AssertionError(k+': '+str(detail))
 manifest=json.loads((a.stage/'MANIFEST_SHA256.json').read_text());bad=[]
 for p,d in manifest.items():
  if sha(a.stage/p)!=d['sha256']:bad.append(p)
 ck('stage_manifest_matches_archived_content',not bad,{'files':len(manifest),'mismatches':bad})
 for name in ['baseline_001_160826.py','deltamesh_antwerp_eval_v10_fixed_080826.py']:
  candidates=list(a.original.rglob(name));h=sha(a.stage/'snapshots'/name)
  ck('original_uploaded_source_matches_'+name,any(sha(p)==h for p in candidates),{'sha256':h,'candidate_count':len(candidates)})
 source=(a.stage/'snapshots/deltamesh_antwerp_eval_v10_fixed_080826.py').read_text();new=(a.stage/'code/evaluator_stable.py').read_text()
 ck('stable_patch_is_exactly_one_sort_change',new==source.replace('order = np.argsort(-rssi)','order = np.argsort(-rssi, kind="stable")') and source.count('order = np.argsort(-rssi)')==1)
 d=pd.read_csv(a.data);rssi=d[[f'BS {i}' for i in range(1,73)]].to_numpy(float);valid=np.isfinite(rssi)&(rssi>=-150)&(rssi<=-20)
 wr=np.flatnonzero((valid.sum(1)>=3)&np.isfinite(d.Latitude)&np.isfinite(d.Longitude))
 tf=Transformer.from_crs(4326,32631,always_xy=True);x,y=tf.transform(d.Longitude.to_numpy(),d.Latitude.to_numpy());xy=np.column_stack([x,y]);times=pd.to_datetime(d['RX Time'],utc=True,format='mixed')
 order=list(map(int,wr));random.Random(1).shuffle(order);ncal=int(.3*len(order));cal=order[:ncal]
 led=pd.read_csv(a.stage/'results/prepared/execution_populations.csv.gz');actual=led[led.role=='calibration'].sort_values('rank0').csv_row_index0.tolist()
 ck('raw_working_and_calibration_membership',len(wr)==55375 and actual==cal,{'working':len(wr),'calibration':len(cal)})
 # A content key exactly matching the documented legacy exclusion, computed from CSV.
 def content_key(i):return (round(float(x[i]),3),round(float(y[i]),3),tuple(sorted((str(j+1),round(float(rssi[i,j]),3)) for j in np.flatnonzero(valid[i]))))
 keys={i:content_key(i) for i in wr};ckeys={keys[i] for i in cal}
 off={k:np.array(v,float) for k,v in json.loads((a.stage/'inputs/official33.json').read_text()).items()};rec={k:np.array(v,float) for k,v in json.loads((a.stage/'inputs/recovered29.json').read_text()).items()};rf={k:np.array(v,float) for k,v in json.loads((a.stage/'results/prepared/rssfit_stable41.json').read_text()).items()}
 eligible=[i for i in order[ncal:] if sum(valid[i,int(g)-1] for g in off)>=3];sample=random.Random(9).sample(eligible,2500);primary=[i for i in sample if keys[i] not in ckeys]
 b=pd.read_csv(a.stage/'results/benchmark/geometric_predictions.csv.gz');tem=pd.read_csv(a.stage/'results/temporal/predictions.csv.gz');st=pd.read_csv(a.stage/'results/benchmark/nlls_start_records.csv.gz')
 bp=b[(b.experiment=='primary33')&(b.assignment=='official')].sort_values('sample_rank0')
 ck('official_primary_reconstructed_from_CSV',primary==bp.csv_row_index0.tolist(),{'eligible':len(eligible),'sampled':len(sample),'retained':len(primary)})
 ck('benchmark_source_row_ground_truth_and_time',np.allclose(xy[b.csv_row_index0],b[['x','y']].to_numpy(),rtol=0,atol=1e-8) and np.array_equal(d['RX Time'].iloc[b.csv_row_index0].to_numpy(),b.rx_time.to_numpy()))
 methods=[k[:-8] for k in b if k.endswith('_error_m') and k[:-8]+'_x' in b]
 delta={m:float(np.max(np.abs(np.linalg.norm(b[[m+'_x',m+'_y']].to_numpy()-xy[b.csv_row_index0],axis=1)-b[m+'_error_m']))) for m in methods}
 ck('all_geometric_errors_recomputed_from_CSV_ground_truth',max(delta.values())<1e-7,delta)
 maxw=0.;selectionok=True
 for r in b.itertuples():
  mp=off if r.assignment=='official' else rf
  roster=set(off)-({'71'} if r.experiment=='no71' else set())
  ix=[j for j in range(72) if str(j+1) in roster and valid[r.csv_row_index0,j]];ix.sort(key=lambda j:-rssi[r.csv_row_index0,j]);ix=ix[:10]
  gids=[str(j+1) for j in ix];raw=rssi[r.csv_row_index0,ix]
  selectionok &= gids==r.selected_receivers.split(';') and np.array_equal(raw,np.array(r.raw_RSSI.split(';'),float))
  w=10**((raw-max(raw))/10);pred=w@np.array([mp[g] for g in gids])/sum(w)
  maxw=max(maxw,float(np.linalg.norm(pred-[r.WCL_raw_x,r.WCL_raw_y])))
 ck('all_receivers_and_RSSI_rebuilt_from_raw_CSV',selectionok)
 ck('all_rawWCL_predictions_independently_recomputed',maxw<1e-7,{'max_delta_m':maxw,'cases':len(b)})
 sums=[];status=[]
 for (ex,ass),f in b.groupby(['experiment','assignment']):
  for m in methods:sums.append({'experiment':ex,'assignment':ass,'method':m,'n':len(f),'median_m':float(f[m+'_error_m'].median()),'p90_m':float(f[m+'_error_m'].quantile(.9))})
  g=st[(st.experiment==ex)&(st.assignment==ass)];sel=g[g.selected]
  status.append({'experiment':ex,'assignment':ass,'n':len(f),'selected_unsuccessful':int((~sel.success).sum()),'all_starts_unsuccessful':int(g.groupby('csv_row_index0').success.sum().eq(0).sum()),'selected_near_boundary':int(sel.near_boundary.sum())})
  ck('optimizer_status_crosscheck_'+ex+'_'+ass,int((~sel.success).sum())==int((~f.nlls_selected_success).sum()) and int(sel.near_boundary.sum())==int(f.nlls_selected_near_boundary.sum()) and len(g)==3*len(f))
 pd.DataFrame(sums).to_csv(a.out/'independent_benchmark_summary.csv',index=False);pd.DataFrame(status).to_csv(a.out/'independent_solver_counts.csv',index=False)
 # Independently reconstruct true chronological design; ties preserve shuffled order.
 chrono=sorted(order,key=lambda i:times.iloc[i]);late=chrono[int(.6*len(chrono)):];req=random.Random(9).sample(late,1200);ek={keys[i] for i in req};pool=[i for i in chrono if keys[i] not in ek];arms={'early':pool[:ncal],'interleaved':random.Random(4242).sample(pool,ncal)}
 tl=pd.read_csv(a.stage/'results/temporal/population_ledger.csv.gz')
 for arm,ids in arms.items():
  logged=tl[(tl.experiment=='temporal_official_matched')&(tl.role=='calibration_'+arm)].sort_values('role_rank0').csv_row_index0.tolist()
  ck('temporal_original_rows_'+arm,logged==ids and all(keys[i] not in ek for i in ids),{'n':len(ids),'start':str(times.iloc[ids].min()),'end':str(times.iloc[ids].max())})
 ck('all_temporal_timestamps_match_original_rows',np.array_equal(d['RX Time'].iloc[tem.csv_row_index0].to_numpy(),tem.rx_time.to_numpy()))
 # Use unchanged kernels, no import of prior orchestration/common/temporal modules.
 ev=load_module('continuity_original_evaluator',a.stage/'snapshots/deltamesh_antwerp_eval_v10_fixed_080826.py')
 bl=load_module('continuity_original_baseline',a.stage/'snapshots/baseline_001_160826.py');bl.TAU=3.
 a0={};obs={}
 for mt,mp in [('official',off),('recovered',rec)]:
  for arm,ids in arms.items():
   one={};cnt={}
   for g,coord in mp.items():
    ij=[i for i in ids if valid[i,int(g)-1]];cnt[g]=len(ij)
    if len(ij)>=10:one[g]=float(np.median(rssi[ij,int(g)-1]+47*np.log10(np.linalg.norm(xy[ij]-coord,axis=1)+1)))
   a0[mt,arm]=one;obs[mt,arm]=cnt
 common=set(off)&set(rec)
 for key in a0:common&=set(a0[key])
 common=sorted(common,key=int)
 keep=[i for i in req if sum(valid[i,int(g)-1] for g in common)>=3]
 preds=[]
 for mt,mp0 in [('official',off),('recovered',rec)]:
  mp={g:mp0[g] for g in common}
  for arm,ids in arms.items():
   for rank,i in enumerate(keep):
    gids=[g for g in common if valid[i,int(g)-1]];gids.sort(key=lambda g:-rssi[i,int(g)-1]);gids=gids[:10]
    g=np.array([mp[j] for j in gids]);raw=rssi[i,np.array(gids,int)-1];q=raw-np.array([a0[mt,arm][j] for j in gids]);ii,jj=np.triu_indices(len(g),1);npair=int(np.sum(np.abs(q[ii]-q[jj])>=3))
    wc=ev.wcl_estimate(g,q);old=bl.lattice(ev,g,q,4.7,'diff','median')
    pos={'WCL_raw':ev.wcl_estimate(g,raw),'WCL_bc':wc,'ABS_mean':bl.lattice(ev,g,q,4.7,'abs','mean'),'DIFF_legacy':old,'DIFF_revised':wc if npair==0 else old,'MinMax':bl.minmax(g,q,4.7)}
    row={'map':mt,'calibration':arm,'rank0':rank,'csv_row_index0':i,'selected_receivers':';'.join(gids),'empty_pairs':npair==0}
    for m,v in pos.items():row[m+'_error_m']=float(np.linalg.norm(v-xy[i]))
    preds.append(row)
   print('bridge completed',mt,arm,len(keep),flush=True)
 out=pd.DataFrame(preds);out.to_csv(a.out/'matched_temporal_bridge_predictions.csv.gz',index=False,compression={'method':'gzip','mtime':0})
 summ=[]
 for mt in ['official','recovered']:
  e=out[(out['map']==mt)&(out.calibration=='early')].sort_values('rank0');r=out[(out['map']==mt)&(out.calibration=='interleaved')].sort_values('rank0')
  ck('bridge_pairing_'+mt,np.array_equal(e.csv_row_index0,r.csv_row_index0) and np.array_equal(e.selected_receivers,r.selected_receivers))
  ck('bridge_rawWCL_invariant_'+mt,np.array_equal(e.WCL_raw_error_m,r.WCL_raw_error_m))
  for m in pos:
   evv=e[m+'_error_m'].to_numpy();rvv=r[m+'_error_m'].to_numpy();em=float(np.median(evv));rm=float(np.median(rvv));rng=np.random.default_rng(20260905);diff=[];ratio=[]
   for start in range(0,6000,100):
    ind=rng.integers(0,len(keep),size=(100,len(keep)));be=np.median(evv[ind],axis=1);br=np.median(rvv[ind],axis=1);diff.extend(be-br);ratio.extend(be/br)
   lo,hi=np.quantile(diff,[.025,.975]);rl,rh=np.quantile(ratio,[.025,.975]);summ.append({'map':mt,'method':m,'n':len(keep),'early_median_m':em,'interleaved_median_m':rm,'difference_m':em-rm,'percent_change':100*(em/rm-1),'paired_difference_ci_low':float(lo),'paired_difference_ci_high':float(hi),'paired_ratio_ci_low':float(rl),'paired_ratio_ci_high':float(rh)})
 pd.DataFrame(summ).to_csv(a.out/'matched_temporal_bridge_summary.csv',index=False)
 dump(a.out/'matched_temporal_bridge_protocol.json',{'same_calibration_rows_as_A4a':True,'calibration_budget_each':ncal,'requested_late_rows':len(req),'shared_evaluated_rows':len(keep),'shared_receivers':common,'original_kernels_reused':True,'legacy_and_revised_DIFF_both_reported':True,'resamples':6000,'seed':20260905,'interval':'paired message percentile 95%, conditional on fixed calibration/maps','calendar_dates_are_original':True})
 dump(a.out/'verification_checks.json',{'n_checks':len(checks),'all_pass':all(x['pass'] for x in checks.values()),'checks':checks});print(pd.DataFrame(summ).to_string(index=False));print('DONE',len(checks))
if __name__=='__main__':main()
