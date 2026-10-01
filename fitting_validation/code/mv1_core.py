"""PA-PR-MV1 full producer primitives; the objective/search contract is unchanged.

The original objective and initializer originate in evaluator_stable.py. This
module adds instrumentation and prescribed domain/start/validation wrappers;
it is not a new optimized coordinate estimator. No I/O or fitting on import.
"""
from __future__ import annotations
from typing import Sequence
import numpy as np
from study_contract import loss_intercept, flatness_bound

DIRECTIONS = ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1))
STEPS = (2000,1000,500,250,125,60)
FRACTIONS = ((.25,.25),(.25,.75),(.75,.25),(.75,.75))
LOSS_TOL = 1e-9
POSITION_TOL = 1e-7


def arrays(xy, rssi, *, empty=False):
    xy, rssi = np.asarray(xy,dtype=float), np.asarray(rssi,dtype=float)
    if rssi.ndim != 1 or xy.shape != (len(rssi),2) or (not empty and not len(rssi)):
        raise ValueError('Expected aligned finite N x 2 positions and N RSSI values')
    if not np.isfinite(xy).all() or not np.isfinite(rssi).all():
        raise ValueError('Nonfinite observation')
    return xy, rssi


def bounds(lower, upper):
    lower,upper=np.asarray(lower,float),np.asarray(upper,float)
    if lower.shape!=(2,) or upper.shape!=(2,) or not np.isfinite([lower,upper]).all() or np.any(lower>upper):
        raise ValueError('Invalid finite rectangular domain')
    return lower,upper


def initializer(xy, rssi):
    xy,rssi=arrays(xy,rssi)
    ix=np.argsort(-rssi,kind='stable')[:min(50,len(rssi))]
    w=np.power(10.0,rssi[ix]/10.0)
    if not np.isfinite(w).all() or float(w.sum())<=0:
        raise ValueError('Nonpositive/nonfinite raw power weights outside valid-input contract')
    return np.array([np.sum(w*xy[ix,0])/np.sum(w),np.sum(w*xy[ix,1])/np.sum(w)],float)


def traced_search(xy, rssi, lower, upper, start, *, steps=STEPS, max_sweeps=40):
    """Immediate strict-improvement/clipped pattern search; records every call.

    Trace columns are call, step, sweep, direction, candidate x/y, loss,
    intercept and accepted. The initial point is call 1 with step/sweep/dir -1.
    A cap flag requires improvement in the last allowed sweep, not just use of
    the last sweep. No initial solution is imported from another domain arm.
    """
    xy,rssi=arrays(xy,rssi);lower,upper=bounds(lower,upper)
    start=np.asarray(start,float)
    if start.shape!=(2,) or not np.isfinite(start).all() or max_sweeps<1:
        raise ValueError('Bad start or sweep budget')
    if not len(steps) or any(not np.isfinite(s) or s<=0 for s in steps):
        raise ValueError('Positive finite step lengths required')
    cur=np.clip(start,lower,upper)
    loss,a=loss_intercept(cur,xy,rssi)
    calls=1
    trace=[(1,-1,-1,-1,float(cur[0]),float(cur[1]),loss,a,True)]
    schedule=[]
    for step in steps:
        improved=True;iteration=0
        while improved and iteration<max_sweeps:
            improved=False;iteration+=1
            for di,(dx,dy) in enumerate(DIRECTIONS):
                candidate=np.clip(cur+np.array([dx*step,dy*step],float),lower,upper)
                value,intercept=loss_intercept(candidate,xy,rssi);calls+=1
                accepted=value<loss
                trace.append((calls,float(step),iteration,di,float(candidate[0]),float(candidate[1]),value,intercept,bool(accepted)))
                if accepted:
                    cur,loss,a=candidate,value,intercept;improved=True
        schedule.append({'step_m':float(step),'sweeps':iteration,'sweep_cap_hit_with_improvement':bool(improved and iteration==max_sweeps)})
    return {'coordinate':cur.copy(),'loss_db':loss,'intercept_db':a,'objective_calls':calls,
            'schedule':schedule,'trace':trace,'start_raw':start.copy(),'start_projected':np.clip(start,lower,upper)}


def scheduled_starts(shared_initializer, footprint_lower, footprint_upper):
    """Unbuffered GLOBAL fitting footprint; fractional starts are common to arms."""
    lo,hi=bounds(footprint_lower,footprint_upper)
    s=np.asarray(shared_initializer,float)
    if s.shape!=(2,) or not np.isfinite(s).all():raise ValueError('Invalid initializer')
    return [s.copy()]+[lo+np.array(f)*(hi-lo) for f in FRACTIONS]


def select_start(outputs):
    """Training loss ONLY. Python min preserves first scheduled exact tie."""
    if not outputs or any(not np.isfinite(o['loss_db']) for o in outputs):
        raise ValueError('Missing/nonfinite run')
    return min(range(len(outputs)),key=lambda i: outputs[i]['loss_db'])


def predict(xy, coordinate, intercept):
    xy=np.asarray(xy,float)
    if xy.ndim!=2 or xy.shape[1]!=2 or not np.isfinite(xy).all() or not np.isfinite(intercept):
        raise ValueError('Invalid prediction inputs')
    if coordinate is None:return np.full(len(xy),float(intercept))
    g=np.asarray(coordinate,float)
    if g.shape!=(2,) or not np.isfinite(g).all():raise ValueError('Invalid predicted receiver coordinate')
    return float(intercept)-47*np.log10(np.linalg.norm(xy-g,axis=1)+1.0)


def residual_metrics(rssi, predictions):
    rssi,predictions=np.asarray(rssi,float),np.asarray(predictions,float)
    if rssi.ndim!=1 or rssi.shape!=predictions.shape or not np.isfinite(rssi).all() or not np.isfinite(predictions).all():
        raise ValueError('Invalid residual inputs')
    if not len(rssi):return {'n':0,'median_abs_db':None,'mean_abs_db':None,'p90_abs_db':None,'median_signed_db':None}
    e=rssi-predictions
    return {'n':len(e),'median_abs_db':float(np.median(abs(e))),'mean_abs_db':float(np.mean(abs(e))),
            'p90_abs_db':float(np.quantile(abs(e),.90,method='linear')),'median_signed_db':float(np.median(e))}


def ray_profiles(xy, rssi, shared_initializer, wide_lower, wide_upper):
    """Eight finite WIDE-box rays; 21 points including repeated origin per ray.

    Point evaluations recompute their plug-in fitting intercept only. No point
    is selected to provide a model or a validation-dependent prediction.
    """
    xy,rssi=arrays(xy,rssi);lo,hi=bounds(wide_lower,wide_upper)
    origin=np.asarray(shared_initializer,float)
    if origin.shape!=(2,) or np.any(origin<lo-POSITION_TOL) or np.any(origin>hi+POSITION_TOL):
        raise ValueError('Shared initializer must be inside WIDE')
    mad=float(np.median(abs(rssi-np.median(rssi))))
    result=[]
    for di,vec in enumerate(DIRECTIONS):
        direction=np.array(vec,float);direction/=np.linalg.norm(direction)
        limits=[(hi[k]-origin[k])/direction[k] if direction[k]>0 else
                (lo[k]-origin[k])/direction[k] for k in range(2) if direction[k]!=0]
        distance=max(0.,min(limits));end=np.clip(origin+distance*direction,lo,hi)
        for j,t in enumerate(np.linspace(0.,1.,21)):
            g=origin+t*(end-origin);loss,a=loss_intercept(g,xy,rssi)
            bound=flatness_bound(g,xy)
            result.append({'direction_rank0':di,'point_rank0':j,'fraction':float(t),
                'distance_from_initializer_m':float(np.linalg.norm(g-origin)),
                'x':float(g[0]),'y':float(g[1]),'training_loss_db':loss,'fitting_intercept_db':a,
                'constant_training_mad_db':mad,'loss_minus_constant_db':loss-mad,'range_term_db':bound,
                'finite_bound_satisfied':abs(loss-mad)<=bound+LOSS_TOL})
    return result


def geometry_fields(g, catalogue, lower, upper):
    g,catalogue=np.asarray(g,float),np.asarray(catalogue,float);lo,hi=bounds(lower,upper)
    if g.shape!=(2,) or catalogue.shape!=(2,) or not np.isfinite([g,catalogue]).all():raise ValueError('Invalid geometry')
    margin=float(np.min(np.concatenate([g-lo,hi-g])))
    outside=float(np.linalg.norm(np.maximum(np.maximum(lo-g,g-hi),0)))
    catoutside=float(np.linalg.norm(np.maximum(np.maximum(lo-catalogue,catalogue-hi),0)))
    return {'catalogue_discrepancy_m':float(np.linalg.norm(g-catalogue)),'minimum_side_margin_m':margin,
            'distance_outside_domain_m':outside,'on_boundary':outside<=POSITION_TOL and abs(margin)<=POSITION_TOL,
            'catalogue_outside_domain':catoutside>POSITION_TOL,'catalogue_outside_distance_m':catoutside}


def raw_wcl(selected: Sequence[int], rssi: Sequence[float], coordinate_map: dict):
    """No selection, reordering, receiver dropping or fallback is performed here."""
    selected=list(selected);rssi=np.asarray(rssi,float)
    if len(selected)!=len(rssi) or not len(selected) or len(set(selected))!=len(selected) or not np.isfinite(rssi).all():
        raise ValueError('Invalid immutable selected receptions')
    missing=[bs for bs in selected if bs not in coordinate_map or coordinate_map[bs] is None]
    if missing:return None,missing
    coords=np.asarray([coordinate_map[bs] for bs in selected],float)
    if coords.shape!=(len(selected),2) or not np.isfinite(coords).all():raise ValueError('Nonfinite available coordinate')
    w=np.power(10.0,rssi/10.0)
    if not np.isfinite(w).all() or float(w.sum())<=0:raise ValueError('Invalid centroid power weights')
    return np.array([np.sum(w*coords[:,0])/np.sum(w),np.sum(w*coords[:,1])/np.sum(w)]),[]
