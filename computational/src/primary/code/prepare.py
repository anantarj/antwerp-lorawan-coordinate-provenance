#!/usr/bin/env python3
"""Freeze the stable RSSFIT map and primary populations from the pinned CSV."""
from __future__ import annotations
import argparse,random,json,collections
from pathlib import Path
import numpy as np
import pandas as pd
from common import *

def main():
    a=argparse.ArgumentParser();a.add_argument('--data',type=Path,required=True);a=a.parse_args()
    c=context(a.data);out=ROOT/'results/prepared';out.mkdir(parents=True,exist_ok=True)
    off=loadmap(ROOT/'inputs/official33.json');rec=loadmap(ROOT/'inputs/recovered29.json')
    print('Fitting stable RSSFIT once, then repeating same explicit contract',flush=True)
    rf,rf_a0=ev.estimate_gateway_positions_rssfit(c['cal'],assumed_n=4.7,seed=1)
    rf_repeat,_=ev.estimate_gateway_positions_rssfit(c['cal'],assumed_n=4.7,seed=1)
    maxdiff=max(float(np.linalg.norm(rf[g]-rf_repeat[g])) for g in rf)
    if maxdiff!=0:raise ValueError('Stable repeated fit changed')
    priorstable=loadmap(ROOT/'inputs/prior_rssfit_sort_stable_diagnostic_map.json')
    diff_prior=max(float(np.linalg.norm(rf[g]-priorstable[g])) for g in rf)
    if diff_prior>1e-7:raise ValueError('Minimal stable patch disagrees with previous independent stable-policy diagnostic')
    old=loadmap(ROOT/'inputs/prior_rssfit_full_current.json')
    dump(out/'rssfit_stable41.json',serialmap(rf));dump(out/'rssfit_fit_intercepts.json',rf_a0)
    aoff=bl.fit_a0(c['cal'],off,4.7); arss=bl.fit_a0(c['cal'],rf,4.7)
    assert set(off)<=set(rf) and set(off)<=set(aoff) and set(off)<=set(arss)
    dump(out/'official33_intercepts.json',aoff);dump(out/'rssfit41_baseline_intercepts.json',arss)
    elig=[i for i in c['pi'] if get_case(c,i,off,aoff) is not None]
    sampled=random.Random(9).sample(elig,min(2500,len(elig)))
    dropped=[i for i in sampled if c['keys'][i] in c['ckeys']]
    chosen=[i for i in sampled if c['keys'][i] not in c['ckeys']]
    no71={g:v for g,v in off.items() if g!='71'}
    survived=[i for i in chosen if get_case(c,i,no71,aoff) is not None]
    lost=[i for i in chosen if i not in set(survived)]
    pri=pd.read_csv(ROOT/'inputs/prior_common27_paired_errors.csv')
    historic=[c['row_to_work'][int(i)] for i in pri.csv_row_index0]
    common=sorted(set(off)&set(rec),key=int)
    bridge=[]
    for wi in historic:
        g,r,t,ids=get_case(c,wi,{k:off[k] for k in common});w=ev.wcl_estimate(g,r)
        new=ev.wcl_estimate(np.vstack([rf[k] for k in ids]),r)
        oldp=ev.wcl_estimate(np.vstack([old[k] for k in ids]),r)
        bridge.append({**metadata(c,wi),'selected_receivers':';'.join(ids),'official_error_m':float(np.linalg.norm(w-t)),'rssfit_stable_error_m':float(np.linalg.norm(new-t)),'rssfit_prior_default_error_m':float(np.linalg.norm(oldp-t)), 'official_x':w[0],'official_y':w[1],'rssfit_x':new[0],'rssfit_y':new[1]})
    bridge=pd.DataFrame(bridge);csvout(out/'common27_stable_bridge.csv',bridge)
    db=random.Random(33).sample(c['ci'],min(8000,len(c['ci'])))
    roles=[]
    for role,ids in [('calibration',c['ci']),('official33_primary',chosen),('no71_survivor',survived),('official_primary_excluded_cal_content',dropped),('no71_excluded_support',lost),('fingerprint_database',db)]:
        for rank,wi in enumerate(ids):roles.append({'role':role,'rank0':rank,**metadata(c,wi)})
    csvout(out/'execution_populations.csv.gz',pd.DataFrame(roles))
    dump(out/'populations.json',{'primary_working_ids':chosen,'no71_working_ids':survived,'fingerprint_database_working_ids':db,'common27_working_ids':historic})
    counts=collections.Counter(r.gid for m in c['cal'] for r in m.receptions)
    csvout(out/'calibration_receivers.csv',pd.DataFrame([{'bs':g,'calibration_links':counts[g],'official33':g in off,'rssfit41':g in rf,'official_a0':aoff.get(g),'rssfit_a0':arss.get(g)} for g in sorted(rf,key=int)]))
    initialization=[];by=collections.defaultdict(list)
    for wi in c['ci']:
        m=c['msgs'][wi]
        for r in m.receptions:by[r.gid].append((wi,r.rssi,m.x,m.y))
    rng=random.Random(1)
    for gid,recs in by.items():
        if len(recs)>2000:recs=rng.sample(recs,2000)
        v=np.array([r[1] for r in recs]);threshold=np.quantile(v,.75);f=v>=threshold
        if f.sum()>=50:recs=[r for r,yes in zip(recs,f) if yes];v=v[f]
        sorted_ix=sorted(range(len(v)),key=lambda j:(-v[j],j))[:min(50,len(v))]
        assert sorted_ix==list(np.argsort(-v,kind='stable')[:min(50,len(v))])
        for rank,j in enumerate(sorted_ix):
            wi,r,x,y=recs[j];initialization.append({'bs':gid,'initialization_rank0':rank,'retained_array_index0':j,'csv_row_index0':int(c['rows'][wi]),'rssi':r,'tx_x':x,'tx_y':y})
    csvout(out/'rssfit_initialization_records.csv.gz',pd.DataFrame(initialization))
    res={'stable_fit_repeat_max_difference_m':maxdiff,'stable_fit_vs_previous_diagnostic_max_difference_m':diff_prior,
      'counts':{'calibration':len(c['ci']),'eligible_official_complement':len(elig),'sampled':len(sampled),'excluded_calibration_content':len(dropped),'primary_evaluation':len(chosen),'no71_survivors':len(survived),'no71_lost':len(lost),'common27':len(bridge),'fingerprint_database':len(db)},
      'primary_new_vs_historical_common27_overlap':len(set(chosen)&set(historic)),
      'stable_common27':{'official':summary(bridge.official_error_m),'rssfit':summary(bridge.rssfit_stable_error_m),'ratio':float(np.median(bridge.rssfit_stable_error_m)/np.median(bridge.official_error_m)),'estimated_worse_count':int((bridge.rssfit_stable_error_m>bridge.official_error_m).sum())},
      'fitted_map_sha256':sha(out/'rssfit_stable41.json'),'source_note':'fresh documented stable policy; not proof of historical 3683m settings'}
    dump(out/'preparation_checks.json',res)
    print(json.dumps(res,indent=2),flush=True)
if __name__=='__main__':main()
