"""Pure helpers for the prospectively specified PA-PR-MV1 follow-up.

These functions define grouping, fitting-only preparation, and scoring. Importing
this module does not read source data, fit coordinates, or access a network.
"""
from __future__ import annotations
import hashlib
import random
from collections import defaultdict
from typing import Iterable, Sequence
import numpy as np


def sha_role(component_key: str, salt: str) -> str:
    value = int.from_bytes(hashlib.sha256((salt + component_key).encode()).digest(), 'big')
    return 'validation' if value < (1 << 256) // 5 else 'fitting'


class UnionFind:
    def __init__(self, n: int):
        self.parent = list(range(n))
    def find(self, i: int) -> int:
        while self.parent[i] != i:
            self.parent[i] = self.parent[self.parent[i]]
            i = self.parent[i]
        return i
    def union(self, a: int, b: int) -> None:
        x, y = self.find(a), self.find(b)
        if x != y:
            self.parent[max(x, y)] = min(x, y)


def components(keys_by_kind: Sequence[Sequence[str]], row_ids: Sequence[int]) -> list[int]:
    n = len(row_ids)
    if any(len(keys) != n for keys in keys_by_kind):
        raise ValueError('Grouping key count differs from row count')
    uf = UnionFind(n)
    for keys in keys_by_kind:
        first: dict[str, int] = {}
        for i, key in enumerate(keys):
            if key in first: uf.union(i, first[key])
            else: first[key] = i
    minimum: dict[int, int] = {}
    for i, row in enumerate(row_ids):
        p = uf.find(i)
        minimum[p] = min(minimum.get(p, int(row)), int(row))
    return [minimum[uf.find(i)] for i in range(n)]


def fit_box(xy: np.ndarray, padding: float = 2000.0) -> tuple[np.ndarray, np.ndarray]:
    xy = np.asarray(xy, dtype=float)
    if xy.ndim != 2 or xy.shape[1] != 2 or not len(xy) or not np.isfinite(xy).all():
        raise ValueError('Finite, nonempty N x 2 fitting positions required')
    return xy.min(axis=0) - padding, xy.max(axis=0) + padding


def prepare_observations(records: list[tuple[int, int, float]], rng: random.Random,
                         limit: int = 2000, quantile: float = 0.75,
                         minimum_strong: int = 50) -> tuple[list[tuple[int, int, float]], dict]:
    """Records are (csv_row, working_index, RSSI), already fitting-only and ordered."""
    if not records: raise ValueError('No fitting observations')
    values = records if len(records) <= limit else rng.sample(records, limit)
    r = np.asarray([v[2] for v in values], dtype=float)
    if not np.isfinite(r).all(): raise ValueError('Nonfinite fitting RSSI')
    threshold = float(np.quantile(r, quantile, method='linear'))
    mask = r >= threshold
    use = int(mask.sum()) >= minimum_strong
    kept = [v for v, yes in zip(values, mask) if yes] if use else list(values)
    return kept, {'pre_filter_n':len(records), 'subsample_n':len(values),
                  'strong_threshold_dbm':threshold, 'strong_filter_used':use,
                  'retained_n':len(kept)}


def loss_intercept(g: np.ndarray, xy: np.ndarray, rssi: np.ndarray,
                   exponent: float = 4.7) -> tuple[float, float]:
    g, xy, rssi = np.asarray(g,float), np.asarray(xy,float), np.asarray(rssi,float)
    if len(xy) != len(rssi) or not len(rssi) or xy.shape != (len(rssi),2):
        raise ValueError('Position/RSSI shape mismatch or empty data')
    if not (np.isfinite(g).all() and np.isfinite(xy).all() and np.isfinite(rssi).all()):
        raise ValueError('Nonfinite loss input')
    d = np.linalg.norm(xy-g,axis=1) + 1.0
    a = float(np.median(rssi + 10.0*exponent*np.log10(d)))
    return float(np.median(np.abs(rssi - (a-10.0*exponent*np.log10(d))))), a


def validation_loss(g: np.ndarray, a_fit: float, xy: np.ndarray, rssi: np.ndarray,
                    exponent: float = 4.7) -> float:
    """Predict with the given FITTING intercept; never estimate an intercept here."""
    xy, rssi = np.asarray(xy,float), np.asarray(rssi,float)
    if not len(rssi) or xy.shape != (len(rssi),2): raise ValueError('Empty/misaligned validation')
    if not np.isfinite(a_fit): raise ValueError('Nonfinite fitting intercept')
    pred = a_fit - 10.0*exponent*np.log10(np.linalg.norm(xy-np.asarray(g,float),axis=1)+1.0)
    return float(np.median(np.abs(rssi-pred)))


def constant_loss(fit_rssi: np.ndarray, validation_rssi: np.ndarray) -> float:
    if not len(fit_rssi) or not len(validation_rssi): raise ValueError('Empty constant-control inputs')
    return float(np.median(np.abs(np.asarray(validation_rssi)-np.median(fit_rssi))))


def flatness_bound(g: np.ndarray, xy: np.ndarray, exponent: float = 4.7) -> float:
    d = np.linalg.norm(np.asarray(xy,float)-np.asarray(g,float),axis=1)+1.0
    if not len(d): raise ValueError('Empty geometry')
    return float(10.0*exponent*np.log10(d.max()/d.min()))


def pattern_search(xy: np.ndarray, rssi: np.ndarray,
                   lower: np.ndarray, upper: np.ndarray,
                   initial: np.ndarray | None = None,
                   steps: Sequence[float] = (2000,1000,500,250,125,60),
                   max_sweeps: int = 40) -> dict:
    """Source-style local search; tested here only on constructed fixtures.

    Do not call on real follow-up data until the full producer and protocol gate
    are frozen. Counts are explicit; no claim of global minimization is made.
    """
    xy,rssi=np.asarray(xy,float),np.asarray(rssi,float)
    lower,upper=np.asarray(lower,float),np.asarray(upper,float)
    if len(rssi)==0 or xy.shape!=(len(rssi),2) or np.any(lower>upper):
        raise ValueError('Invalid search arrays or bounds')
    if initial is None:
        ix=np.argsort(-rssi,kind='stable')[:min(50,len(rssi))]
        w=10.0**(rssi[ix]/10.0)
        initial=np.array([np.sum(w*xy[ix,0])/np.sum(w),np.sum(w*xy[ix,1])/np.sum(w)])
    cur=np.clip(np.asarray(initial,float),lower,upper)
    loss,a=loss_intercept(cur,xy,rssi); calls=1; accepted=[]; schedule=[]
    directions=((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1))
    for step in steps:
        improved=True;it=0
        while improved and it<max_sweeps:
            improved=False;it+=1
            for dx,dy in directions:
                candidate=np.clip(cur+np.array([dx*step,dy*step],float),lower,upper)
                value,intercept=loss_intercept(candidate,xy,rssi);calls+=1
                if value<loss:
                    cur,loss,a=candidate,value,intercept;improved=True
                    accepted.append({'call':calls,'x':float(cur[0]),'y':float(cur[1]),'loss_db':loss})
        schedule.append({'step_m':step,'sweeps':it,'sweep_cap_hit_with_improvement':bool(improved and it==max_sweeps)})
    return {'coordinate':cur,'loss_db':loss,'intercept_db':a,'objective_calls':calls,'schedule':schedule,'accepted':accepted}
