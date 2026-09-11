"""Shared post-review execution contracts. No source input is edited."""
from __future__ import annotations
import collections, hashlib, importlib, json, random, sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'snapshots'))
import evaluator_stable as ev
import baseline_001_160826 as bl
bl.TAU=3.0
CSV_SHA='870abe60a4bd81f31ede6f269b6bc6329e05d2731343dff7015bae1a61218446'

def sha(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for z in iter(lambda:f.read(1<<20),b''):h.update(z)
    return h.hexdigest()

def dump(p:Path,obj)->None:
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+'\n')

def csvout(p:Path,df:pd.DataFrame)->None:
    p.parent.mkdir(parents=True,exist_ok=True)
    df.to_csv(p,index=False,compression={'method':'gzip','mtime':0} if p.name.endswith('.gz') else None)

def loadmap(p):return {k:np.asarray(v,dtype=float) for k,v in json.loads(Path(p).read_text()).items()}
def serialmap(mp):return {g:list(map(float,v)) for g,v in mp.items()}
def summary(values):
    x=np.asarray(values,float); finite=np.isfinite(x)
    if not finite.all():raise ValueError('Non-finite output must be explicitly handled, not silently dropped')
    return {'n':len(x),'median_m':float(np.median(x)),'p90_m':float(np.quantile(x,.9)), 'p95_m':float(np.quantile(x,.95)),'over_1km_fraction':float(np.mean(x>1000))}

def context(data:Path):
    if sha(data)!=CSV_SHA:raise ValueError('Raw CSV checksum mismatch')
    df=pd.read_csv(data)
    vals=df[[f'BS {j}' for j in range(1,73)]].to_numpy(float)
    keep=np.isfinite(vals)&(vals>=-150)&(vals<=-20)
    rows=np.flatnonzero((keep.sum(1)>=3)&np.isfinite(df.Latitude)&np.isfinite(df.Longitude))
    msgs=ev.load_antwerp_csv(str(data),min_gws=3)
    prior=pd.read_csv(ROOT/'inputs/prior_population_ledger.csv.gz').sort_values('working_index0')
    if len(msgs)!=len(rows) or not np.array_equal(rows,prior.csv_row_index0):raise ValueError('CSV working row membership changed')
    order=list(range(len(msgs)));random.Random(1).shuffle(order)
    ci=order[:int(.3*len(order))];pi=order[len(ci):]
    if set(ci)!=set(prior.loc[prior.role=='calibration','working_index0']):raise ValueError('Calibration membership changed')
    if list(prior.sort_values('shuffle_rank0').working_index0)!=order:raise ValueError('Calibration/order contract changed')
    keys=[bl.mkey(m) for m in msgs]
    ckeys={keys[i] for i in ci}
    row_to_work={int(r):i for i,r in enumerate(rows)}
    times=pd.to_datetime(df['RX Time'].iloc[rows],utc=True,format='mixed').reset_index(drop=True)
    if times.isna().any():raise ValueError('Unparseable timestamp')
    return dict(df=df,vals=vals,rows=rows,msgs=msgs,prior=prior,order=order,ci=ci,pi=pi,cal=[msgs[i] for i in ci],keys=keys,ckeys=ckeys,row_to_work=row_to_work,times=times)

def get_case(c,wi,mp,a0=None):
    m=c['msgs'][wi]
    rs=[r for r in m.receptions if r.gid in mp and (a0 is None or r.gid in a0)][:10]
    if len(rs)<3:return None
    return np.vstack([mp[r.gid] for r in rs]),np.array([r.rssi for r in rs]),np.array([m.x,m.y]),[r.gid for r in rs]

def bbox(mp,pad=3000):
    g=np.asarray(list(mp.values()));return (float(g[:,0].min()-pad),float(g[:,0].max()+pad),float(g[:,1].min()-pad),float(g[:,1].max()+pad))

def metadata(c,wi):
    m=c['msgs'][wi];rid=int(c['rows'][wi])
    return {'working_index0':int(wi),'csv_row_index0':rid,'x':m.x,'y':m.y,'rx_time':str(c['df'].iloc[rid]['RX Time'])}

def diff_location(g,r):
    i,j=np.triu_indices(len(r),1);k=int(np.sum(np.abs(r[i]-r[j])>=3))
    legacy=bl.lattice(ev,g,r,4.7,'diff','median')
    corrected=ev.wcl_estimate(g,r) if k==0 else legacy
    return corrected,legacy,k
