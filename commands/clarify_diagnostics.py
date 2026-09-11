#!/usr/bin/env python3
"""Verify two diagnostic definitions against unchanged source/data; no estimator fit.

Computes geographic nearest-database distances directly from source CSV positions,
and the zero-centred residual-tail count from saved median-centred residuals.
Writes to a new external directory only. Scientific components remain read-only.
"""
from __future__ import annotations
import argparse, hashlib, io, json, math, platform, zipfile
from pathlib import Path
import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.stats import kurtosis
ROOT=Path(__file__).resolve().parents[1]
CSV_SHA='870abe60a4bd81f31ede6f269b6bc6329e05d2731343dff7015bae1a61218446'
TOL=1e-7

def sha(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()
def nearest(query:np.ndarray, database:np.ndarray)->np.ndarray:
    # Direct differences avoid loss of precision in a squared-dot-product identity.
    result=[]
    for q in np.array_split(query,max(1,math.ceil(len(query)/96))):
        d=q[:,None,:]-database[None,:,:]
        result.extend(np.sqrt(np.sum(d*d,axis=2)).min(axis=1))
    return np.asarray(result)

def main()->None:
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--csv',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    out=a.out.resolve()
    if out.exists() or out.is_relative_to(ROOT):raise ValueError('Output must be new and outside this package.')
    if zipfile.is_zipfile(a.csv):
        with zipfile.ZipFile(a.csv) as z:
            names=[x for x in z.namelist() if x.lower().endswith('.csv') and not x.startswith('__MACOSX/')]
            if len(names)!=1:raise ValueError('Expected one CSV payload')
            payload=z.read(names[0])
    else:payload=a.csv.read_bytes()
    if hashlib.sha256(payload).hexdigest()!=CSV_SHA:raise ValueError('CSV fingerprint mismatch')
    c=ROOT/'computational';checks=[];sources=[]
    def ck(name,ok,detail=None):
        checks.append({'name':name,'pass':bool(ok),'detail':detail})
        if not ok:raise AssertionError(name+': '+str(detail))
    def src(p):sources.append({'path':str(p.relative_to(ROOT)),'sha256':sha(p)})
    out.mkdir(parents=True)
    raw=pd.read_csv(io.BytesIO(payload),usecols=['Latitude','Longitude'])
    x,y=Transformer.from_crs(4326,32631,always_xy=True).transform(raw.Longitude.to_numpy(),raw.Latitude.to_numpy())
    pos=np.column_stack((x,y));ck('CSV_data_record_count',len(pos)==130429)
    summaries=[];all_rows=[]
    def one(f,db_file,label):
        ids=pd.read_csv(db_file).csv_row_index0.to_numpy(int);src(db_file)
        qi=f.csv_row_index0.to_numpy(int);ck(label+'_8000_distinct_database_records',len(ids)==8000 and len(set(ids))==8000)
        ck(label+'_source_positions_match_saved_queries',np.allclose(pos[qi],f[['x','y']],rtol=0,atol=TOL))
        d=nearest(pos[qi],pos[ids]);saved=f.FP_nearest_calibration_m.to_numpy(float)
        error=float(np.max(np.abs(d-saved)));ck(label+'_all_geographic_distances_match',error<=TOL,{'n_queries':len(qi),'max_absolute_difference_m':error})
        # Scalar witness for an independent arithmetic implementation.
        k=len(qi)//2;witness=min(math.hypot(float(pos[qi[k],0]-u),float(pos[qi[k],1]-v)) for u,v in pos[ids]);ck(label+'_scalar_hypot_witness',abs(witness-d[k])<=TOL)
        summaries.append({'experiment':label,'queries':len(qi),'database_records':len(ids),'median_nearest_geographic_distance_m':float(np.median(d)),'max_saved_difference_m':error})
        all_rows.append(pd.DataFrame({'experiment':label,'query_rank0':range(len(qi)),'csv_row_index0':qi,'geographic_min_distance_m':d,'saved_distance_m':saved}))
    fp_path=c/'results/benchmark/fingerprint_predictions.csv.gz';src(fp_path);fp=pd.read_csv(fp_path)
    for ex in ['primary33','no71']:one(fp[fp.experiment==ex].reset_index(drop=True),c/'populations/fingerprint_database_rows.csv',ex)
    gp_path=c/'results/geography/predictions.csv.gz';src(gp_path);g=pd.read_csv(gp_path)
    idx_path=c/'populations/geography_training_index.json';src(idx_path);idx=json.loads(idx_path.read_text())
    lookup={(v['seed'],v['region']):c/'populations'/v['row_file'] for v in idx}
    for (direction,seed,arm,region),f in g.groupby(['direction','seed','calibration_arm','calibration_region'],sort=False):
        one(f.reset_index(drop=True),lookup[(int(seed),region)],f'geo_{direction}_{seed}_{arm}')
    rows=pd.concat(all_rows,ignore_index=True);rows.to_csv(out/'nearest_geographic_distances.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    pd.DataFrame(summaries).to_csv(out/'nearest_geographic_summary.csv',index=False)
    links_path=c/'results/residual_version/matched_links.csv.gz';summ_path=c/'results/residual_version/summary.json';src(links_path);src(summ_path)
    links=pd.read_csv(links_path);old=json.loads(summ_path.read_text());res=[]
    for label,col in [('official_common27','official_residual_db'),('rssfit_stable_common27','rssfit_stable_residual_db')]:
        v=links[col].to_numpy(float);mean=float(np.mean(v));sd=float(np.std(v,ddof=0));ct=int(np.sum(np.abs(v)>3*sd));fraction=ct/len(v)
        record=next(z for z in old['records'] if z['assignment']==label)
        ck(label+'_matched_links',len(v)==69988 and len(links.drop_duplicates(['csv_row_index0','receiver']))==69988)
        ck(label+'_zero_centred_tail_matches',abs(record['beyond_3sd_fraction']-fraction)<1e-15)
        ck(label+'_moments_match',abs(record['sd_db']-sd)<1e-10 and abs(record['excess_kurtosis']-float(kurtosis(v,fisher=True,bias=True)))<1e-10)
        scalar_mean=math.fsum(map(float,v))/len(v);scalar_sd=math.sqrt(math.fsum((float(z)-scalar_mean)**2 for z in v)/len(v))
        ck(label+'_scalar_standard_deviation',abs(scalar_sd-sd)<1e-10 and sum(abs(float(z))>3*scalar_sd for z in v)==ct)
        ck(label+'_receiver_medians_zero',max(abs(float(np.median(f[col]))) for _,f in links.groupby('receiver'))<1e-10)
        res.append({'assignment':label,'n_links':len(v),'pooled_mean_db':mean,'pooled_median_db':float(np.median(v)),'sd_about_pooled_mean_ddof0_db':sd,'threshold_centre_db':0,'strict_threshold_magnitude_db':3*sd,'tail_count_about_zero':ct,'tail_fraction_about_zero':fraction,'excess_kurtosis_fisher_bias_true':float(kurtosis(v,fisher=True,bias=True))})
    (out/'residual_tail_definition.json').write_text(json.dumps({'definition':'count(abs(v)>3*std(v,ddof=0))/N; v has each receiver median removed, no further centring in the threshold; std uses the pooled mean.','records':res},indent=2)+'\n')
    # Record exact source anchors after checking their existence, not inferring intent.
    anchors=[(c/'src/primary/code/benchmark.py','near=np.sqrt(((qy[lo:lo+len(q),None,:]-dy[None,:,:])**2).sum(2)).min(1)'),(c/'src/secondary/code/secondary_controls.py','nearest_database_median_m=float(f.FP_nearest_calibration_m.median())'),(c/'src/secondary/code/reconcile_residuals.py','beyond_3sd_fraction=float(np.mean(abs(v)>3*s))')]
    excerpts=[]
    for p,pattern in anchors:
        src(p);lines=p.read_text().splitlines();hits=[i+1 for i,s in enumerate(lines) if pattern in s];ck('source_definition_'+p.name,len(hits)==1);excerpts.append({'path':str(p.relative_to(ROOT)),'sha256':sha(p),'line':hits[0],'text':lines[hits[0]-1]})
    (out/'SOURCE_DEFINITIONS.json').write_text(json.dumps(excerpts,indent=2)+'\n')
    result={'scope':'Independent diagnostic recomputation from original CSV positions and saved residuals. No RSSI neighbour selection, localization optimizer, RSSFIT fitting, or bootstrap rerun.','absolute_tolerance_m':TOL,'CSV_payload_sha256':CSV_SHA,'geographic_records_checked':len(rows),'residual_values_checked':2*len(links),'source_files':list({v['path']:v for v in sources}.values()),'python':platform.python_version(),'checks':checks,'passed':sum(z['pass'] for z in checks),'failed':sum(not z['pass'] for z in checks)}
    (out/'DIAGNOSTIC_CHECKS.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'checks':result['passed'],'geographic_records':len(rows),'residual_records':2*len(links),'residuals':res,'summaries':summaries},indent=2))
if __name__=='__main__':main()
