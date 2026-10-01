"""Deterministic utilities for the declared G2 DAE reliability experiment."""
from __future__ import annotations
from pathlib import Path
from decimal import Decimal, ROUND_CEILING
from typing import Any
import hashlib, json, math
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RADIUS_M = 6371008.8

def sha_bytes(x: bytes) -> str:
    return hashlib.sha256(x).hexdigest()

def array_hash(x: Any) -> str:
    a=np.asarray(x)
    if a.dtype.hasobject: raise ValueError('object arrays must be serialized explicitly')
    return sha_bytes(str((a.dtype.str,a.shape)).encode()+np.ascontiguousarray(a).tobytes())

def object_hash(x: Any) -> str:
    return sha_bytes(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode())

def clean_json(x: Any) -> Any:
    if isinstance(x,dict): return {str(k):clean_json(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)): return [clean_json(v) for v in x]
    if isinstance(x,np.ndarray): return clean_json(x.tolist())
    if isinstance(x,np.generic): return clean_json(x.item())
    if isinstance(x,float) and not math.isfinite(x): return 'Infinity' if x>0 else '-Infinity' if x<0 else None
    return x

def write_json(path: Path,x: Any) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(clean_json(x),indent=2,sort_keys=True,allow_nan=False)+'\n')

def load_protocol() -> dict:
    p=ROOT/'protocol/EXECUTION_PROTOCOL.json'
    expected=(ROOT/'protocol/EXECUTION_PROTOCOL.sha256').read_text().split()[0]
    if sha_bytes(p.read_bytes())!=expected: raise ValueError('Changed execution protocol')
    return json.loads(p.read_text())

def great_circle_km(point1: Any,point2: Any) -> float:
    """Explicit metric compatibility adapter; not the installed haversine package."""
    a,b=tuple(map(float,point1)),tuple(map(float,point2))
    if len(a)!=2 or len(b)!=2 or not all(math.isfinite(v) for v in (*a,*b)):
        raise ValueError('finite latitude/longitude pairs required')
    if any(abs(p[0])>90 or abs(p[1])>180 for p in (a,b)): raise ValueError('invalid degrees')
    lat1,lon1,lat2,lon2=map(math.radians,(*a,*b))
    s=math.sin((lat2-lat1)/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return (RADIUS_M/1000)*2*math.asin(math.sqrt(min(1.,max(0.,s))))

def conformal_quantile(scores: Any,alpha: float) -> tuple[float,int]:
    a=np.asarray(scores,dtype=float)
    if a.ndim!=1 or not np.isfinite(a).all(): raise ValueError('finite score vector required')
    if not (0<float(alpha)<1): raise ValueError('alpha must lie in (0,1)')
    k=int((Decimal(len(a)+1)*(1-Decimal(str(alpha)))).to_integral_value(rounding=ROUND_CEILING))
    return (float(np.sort(a)[k-1]) if 1<=k<=len(a) else float('inf')),k

def empirical_cvar(losses: Any,beta: float=.95) -> float | None:
    a=np.asarray(losses,dtype=float)
    if len(a)==0: return None
    if not np.isfinite(a).all() or not 0<beta<1: raise ValueError('invalid losses/beta')
    eta=float(np.quantile(a,beta,method='inverted_cdf'))
    return float(eta+np.maximum(a-eta,0).mean()/(1-beta))

def decision_stats(errors: Any,radii: Any,tau: float,*,certified: Any=None,total_requests: int|None=None) -> dict:
    e,u=np.asarray(errors,float),np.asarray(radii,float)
    if e.shape!=u.shape or e.ndim!=1 or not np.isfinite(e).all() or np.isnan(u).any():raise ValueError('invalid inputs')
    c=np.ones(len(e),bool) if certified is None else np.asarray(certified,bool)
    if c.shape!=e.shape:raise ValueError('certification shape')
    n=len(e); N=n if total_requests is None else int(total_requests)
    if N<n:raise ValueError('request count smaller than evaluation population')
    accept=c & np.isfinite(u) & (u<=tau)
    k=int(accept.sum());bad=int((accept & (e>tau)).sum());good=k-bad
    return {'n_scored':n,'n_requested':N,'tau_m':tau,'accepted':k,'useful':good,'harmful':bad,'accepted_fraction_scored':k/n if n else None,'accepted_fraction_requests':k/N if N else None,'useful_fraction_requests':good/N if N else None,'harmful_fraction_requests':bad/N if N else None,'conditional_accepted_failure':bad/k if k else None,'accepted_error_mean_m':float(e[accept].mean()) if k else None,'accepted_error_max_m':float(e[accept].max()) if k else None}

def coordinate_oracle(y: np.ndarray,pred: np.ndarray,units: str) -> np.ndarray:
    if units=='meters':return np.sqrt(np.sum((y-pred)**2,axis=1))
    from pyproj import Geod
    g=Geod(a=RADIUS_M,b=RADIUS_M)
    return np.asarray(g.inv(y[:,1],y[:,0],pred[:,1],pred[:,0])[2])
