#!/usr/bin/env python3
"""Timestamp repair with a preserved legacy replay and an explicit matched design."""
from __future__ import annotations
import argparse, collections, random, time
from pathlib import Path
import numpy as np
import pandas as pd
from pyproj import Transformer
from common import *

METHODS=['WCL_raw','WCL_bc','ABS_mean','DIFF_median','MinMax']

def evaluate(c,indices,mp,a0,experiment,arm,legacy=False):
    rows=[]
    for rank,wi in enumerate(indices):
        case=get_case(c,wi,mp,a0)
        if case is None:continue
        g,raw,t,gids=case;q=raw-np.array([a0[k] for k in gids])
        corrected,old,pairs=diff_location(g,q)
        positions={'WCL_raw':ev.wcl_estimate(g,raw),'WCL_bc':ev.wcl_estimate(g,q),
                   'ABS_mean':bl.lattice(ev,g,q,4.7,'abs','mean'),
                   'DIFF_median':old if legacy else corrected,'MinMax':bl.minmax(g,q,4.7)}
        row={'experiment':experiment,'calibration_arm':arm,'sample_rank0':rank,**metadata(c,wi),
             'selected_receivers':';'.join(gids),'support':len(gids),'admitted_pairs':pairs,'empty_pair':pairs==0,
             'minmax_infeasible':bl.minmax_infeasible(g,q,4.7)}
        for name,x in positions.items():
            if not np.isfinite(x).all():raise ValueError('Nonfinite temporal estimate')
            row[f'{name}_x']=float(x[0]);row[f'{name}_y']=float(x[1]);row[f'{name}_error_m']=float(np.linalg.norm(x-t))
        rows.append(row)
    return rows

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,required=True);a=ap.parse_args()
    t0=time.time();c=context(a.data);out=ROOT/'results/temporal';out.mkdir(parents=True,exist_ok=True)
    order=c['order'];ncal=len(c['ci']);n=len(order)
    # Recreate the source's first-time-at-rounded-position lookup on ALL CSV rows.
    tf=Transformer.from_crs(4326,32631,always_xy=True)
    x,y=tf.transform(c['df'].Longitude.to_numpy(),c['df'].Latitude.to_numpy())
    tmap={}
    for xx,yy,ts in zip(x,y,c['df']['RX Time']):
        if np.isfinite(xx) and np.isfinite(yy):tmap.setdefault((round(float(xx),1),round(float(yy),1)),str(ts))
    assigned=[tmap[(round(float(m.x),1),round(float(m.y),1))] for m in c['msgs']]
    old_order=sorted(order,key=lambda i:assigned[i])
    true_order=sorted(order,key=lambda i:c['times'].iloc[i])
    off=loadmap(ROOT/'inputs/official33.json');rec=loadmap(ROOT/'inputs/recovered29.json')
    allrows=[];ledger=[];definitions=[];a0records=[]
    # Historical bridge: only the timestamp assignment/order changes between these
    # two runs. Original eligibility and old no-pair behavior are preserved.
    for name,chron in [('legacy_position_time_recovered29',old_order),('timestamp_only_recovered29',true_order)]:
        late=chron[int(n*.6):];ev_ids=random.Random(9).sample(late,min(1200,len(late)))
        ek={c['keys'][i] for i in ev_ids};eligible=[i for i in chron if c['keys'][i] not in ek]
        arms={'early':chron[:ncal],'interleaved':random.Random(4242).sample(eligible,ncal)}
        defs={'experiment':name,'evaluation_requested':len(ev_ids),'calibration_budget':ncal,'legacy_method_and_eligibility':True,'arms':{}}
        for tag,calids in arms.items():
            a0=bl.fit_a0([c['msgs'][i] for i in calids],rec,4.7)
            r=evaluate(c,ev_ids,rec,a0,name,tag,legacy=True);allrows.extend(r)
            defs['arms'][tag]={'n_evaluated':len(r),'calibrated_receivers':sorted(a0,key=int),'evaluation_content_overlap':sum(c['keys'][i] in ek for i in calids),'calibration_time_min':str(min(c['times'].iloc[calids])),'calibration_time_max':str(max(c['times'].iloc[calids]))}
            for rank,i in enumerate(calids):ledger.append({'experiment':name,'role':f'calibration_{tag}','role_rank0':rank,**metadata(c,i)})
            for rank,i in enumerate(ev_ids):ledger.append({'experiment':name,'role':f'evaluation_requested_{tag}','role_rank0':rank,**metadata(c,i)})
        definitions.append(defs);print(name,defs['arms'],flush=True)
    # Corrected primary: equal budgets, explicit content exclusion, common receiver
    # calibration support, fixed evaluation membership and selected receptions.
    ev_ids=random.Random(9).sample(true_order[int(n*.6):],1200)
    ek={c['keys'][i] for i in ev_ids};eligible=[i for i in true_order if c['keys'][i] not in ek]
    arms={'early':eligible[:ncal],'interleaved':random.Random(4242).sample(eligible,ncal)}
    aa={tag:bl.fit_a0([c['msgs'][i] for i in ids],off,4.7) for tag,ids in arms.items()}
    counts={tag:collections.Counter(rx.gid for i in ids for rx in c['msgs'][i].receptions) for tag,ids in arms.items()}
    shared=set(off)&set(aa['early'])&set(aa['interleaved'])
    for g in sorted(off,key=int):
        for tag in arms:a0records.append({'receiver':g,'calibration_arm':tag,'observations':counts[tag][g],'intercept':aa[tag].get(g),'in_both_calibration_arms':g in shared})
    base_eval=[i for i in ev_ids if get_case(c,i,{g:off[g] for g in shared}) is not None]
    for name,roster in [('temporal_official_matched',shared),('temporal_official_no71',shared-{'71'})]:
        mp={g:off[g] for g in sorted(roster,key=int)}
        selected=[i for i in base_eval if get_case(c,i,mp) is not None]
        defs={'experiment':name,'evaluation_requested':1200,'n_evaluated_per_arm':len(selected),'calibration_budget':ncal,'roster':sorted(roster,key=int),
              'removed_early_content_overlap':sum(c['keys'][i] in ek for i in true_order[:ncal]),'early_set_added_rows':[int(c['rows'][i]) for i in arms['early'] if i not in set(true_order[:ncal])],
              'evaluation_time_min':str(min(c['times'].iloc[selected])),'evaluation_time_max':str(max(c['times'].iloc[selected])),'arms':{}}
        for tag,calids in arms.items():
            r=evaluate(c,selected,mp,aa[tag],name,tag);allrows.extend(r)
            if len(r)!=len(selected):raise RuntimeError('Temporal matched eligibility changed')
            defs['arms'][tag]={'evaluation_content_overlap':sum(c['keys'][i] in ek for i in calids),
                              'calibration_time_min':str(min(c['times'].iloc[calids])),'calibration_time_max':str(max(c['times'].iloc[calids]))}
            if defs['arms'][tag]['evaluation_content_overlap']:raise RuntimeError('Calibration content overlaps evaluation')
            for rank,i in enumerate(calids):ledger.append({'experiment':name,'role':f'calibration_{tag}','role_rank0':rank,**metadata(c,i)})
        for rank,i in enumerate(selected):ledger.append({'experiment':name,'role':'evaluation','role_rank0':rank,**metadata(c,i)})
        for rank,i in enumerate(ev_ids):
            if i not in set(selected):ledger.append({'experiment':name,'role':'excluded_insufficient_shared_support','role_rank0':rank,**metadata(c,i)})
        definitions.append(defs);print(name,len(selected),sorted(shared,key=int),flush=True)
    frame=pd.DataFrame(allrows);csvout(out/'predictions.csv.gz',frame);csvout(out/'population_ledger.csv.gz',pd.DataFrame(ledger))
    csvout(out/'calibration_receivers.csv',pd.DataFrame(a0records))
    sm=[];contr=[];checks={}
    for (ex,tag),f in frame.groupby(['experiment','calibration_arm'],sort=False):
        for m in METHODS:sm.append({'experiment':ex,'calibration_arm':tag,'method':m,**summary(f[f'{m}_error_m'])})
    for ex,f in frame.groupby('experiment',sort=False):
        early=f[f.calibration_arm=='early'].set_index('csv_row_index0');random_=f[f.calibration_arm=='interleaved'].set_index('csv_row_index0')
        ids=early.index.intersection(random_.index)
        for m in METHODS:
            em=float(early.loc[ids,f'{m}_error_m'].median());rm=float(random_.loc[ids,f'{m}_error_m'].median())
            contr.append({'experiment':ex,'method':m,'n_shared':len(ids),'early_median_m':em,'interleaved_median_m':rm,'difference_m':em-rm,'change_percent':100*(em/rm-1)})
        if ex.startswith('temporal_official'):
            if list(early.index)!=list(random_.index) or not early.selected_receivers.equals(random_.selected_receivers):raise RuntimeError('Temporal pairing/receivers differ')
            delta=np.max(np.abs(early.WCL_raw_error_m-random_.WCL_raw_error_m))
            if delta!=0:raise RuntimeError('Raw WCL depends on calibration in matched control')
            checks[ex]={'same_row_ids':True,'same_selected_receivers':True,'raw_WCL_max_error_delta_m':float(delta)}
    csvout(out/'summary.csv',pd.DataFrame(sm));csvout(out/'contrasts.csv',pd.DataFrame(contr));dump(out/'definitions.json',definitions)
    expected={'early':{'WCL_bc':655,'ABS_mean':775,'DIFF_median':1165},'interleaved':{'WCL_bc':664,'ABS_mean':726,'DIFF_median':1076}}
    for arm,methods in expected.items():
        f=frame[(frame.experiment=='legacy_position_time_recovered29')&(frame.calibration_arm==arm)]
        checks['legacy_'+arm]={'n':len(f),'rounded_matches':{m:int(round(f[f'{m}_error_m'].median()))==v for m,v in methods.items()}}
    checks['no_missing_original_timestamps']=True
    dump(out/'execution_checks.json',checks)
    dump(out/'execution.json',{'elapsed_seconds':time.time()-t0,'prediction_cases':len(frame),'complete':True})
    print(pd.DataFrame(contr).to_string(index=False));print('FINISHED',time.time()-t0,flush=True)
if __name__=='__main__':main()
