"""Input-only DSI correspondence and LoRaWAN time-role allocation. No fitted errors.

The DSI association is an observed compatibility relation, not recovery of an
unavailable historical preparation program or of a unique timestamp for duplicates.
"""
from __future__ import annotations
from pathlib import Path
import argparse,hashlib,io,json,math,random,zipfile,sys
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'sources/inherited'))
from common import sha_bytes,write_json,array_hash
ARCHIVE_SHA='0674261d878403af3da744202875ad6c520565a52159605e10fa7632a581803a'
RAW_LORA_SHA='870abe60a4bd81f31ede6f269b6bc6329e05d2731343dff7015bae1a61218446'

def save_csv(d,path):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    kw={'compression':{'method':'gzip','mtime':0}} if path.name.endswith('.gz') else {}
    d.to_csv(path,index=False,float_format='%.17g',**kw)

def read_csv(z,path,header='infer'):
    return pd.read_csv(io.BytesIO(z.read(path)),header=header)

def time_roles(ledger):
    d=ledger[['source_row_index0','group_min_source_index0','rx_time']].copy()
    d['timestamp_utc']=pd.to_datetime(d.rx_time,utc=True)
    d=d.sort_values(['timestamp_utc','source_row_index0'],kind='stable').reset_index(drop=True)
    d['utc_day']=d.timestamp_utc.dt.strftime('%Y-%m-%d')
    dc=d.groupby('utc_day',sort=True).size();cum=dc.cumsum();N=len(d)
    cuts=[str(cum.index[np.flatnonzero(cum.to_numpy()>=math.ceil(f*N))[0]]) for f in (.6,.8,.9)]
    if len(set(cuts))!=3:raise ValueError('insufficient temporal resolution; no adaptive alternative')
    day=d.utc_day.to_numpy()
    d['requested_role']=np.select([day<=cuts[0],day<=cuts[1],day<=cuts[2]],['training_pool','calibration_reference_pool','calibration_recent_pool'],default='evaluation')
    spans=d.groupby('group_min_source_index0').requested_role.nunique()
    crossed=set(map(int,spans[spans>1].index))
    d['role']=d.requested_role
    d.loc[d.group_min_source_index0.isin(crossed),'role']='quarantined_cross_role_group'
    groups=np.sort(d.loc[d.role=='training_pool','group_min_source_index0'].unique())
    g1,g2=train_test_split(groups,test_size=.5,random_state=42)
    d.loc[d.group_min_source_index0.isin(g1)&(d.role=='training_pool'),'role']='train1'
    d.loc[d.group_min_source_index0.isin(g2)&(d.role=='training_pool'),'role']='train2'
    pools={k:d.index[d.role==f'calibration_{k}_pool'].to_numpy() for k in ['reference','recent']}
    m=min(map(len,pools.values()))
    for k,ix in pools.items():
        selected=random.Random(20260922).sample(ix.tolist(),m)
        d.loc[ix,'role']='unused_'+k+'_calibration_budget'
        d.loc[selected,'role']='calibration_'+k
    sizes=d.role.value_counts().to_dict()
    for r in ['train1','train2','calibration_reference','calibration_recent','evaluation']:
        if sizes.get(r,0)<100:raise ValueError(f'predeclared 100-row feasibility floor failed for {r}')
    group_roles=d[~d.role.str.startswith('quarantined')].groupby('group_min_source_index0').role.apply(set)
    # Budget-used/unused calibration labels are one statistical pool, not cross-fit leakage.
    def norm(r):
        if r in ['calibration_reference','unused_reference_calibration_budget']:return 'calibration_reference'
        if r in ['calibration_recent','unused_recent_calibration_budget']:return 'calibration_recent'
        return r
    assert all(len({norm(r) for r in ss})==1 for ss in group_roles)
    info={'source_working_rows':N,'rule':'cumulative message mass 60/80/90 percent; entire UTC cutoff day assigned to earlier pool; no score used',
          'cutoff_days_inclusive':cuts,'raw_day_counts':dc.to_dict(),'cross_role_groups':len(crossed),
          'cross_role_quarantined_rows':int((d.role=='quarantined_cross_role_group').sum()),
          'equal_calibration_budget_per_state':m,'counts':sizes,
          'calibration_sampling':'Random(20260922).sample of each chronological eligible row-index list, same m; no score selection',
          'training_split':'Random state 42 half split of sorted duplicate-component keys; rows expanded in chronological order',
          'ranges':{r:{'first':str(x.timestamp_utc.min()),'last':str(x.timestamp_utc.max()),'n':len(x),'groups':int(x.group_min_source_index0.nunique())} for r,x in d.groupby('role',sort=True)}}
    d['timestamp_utc']=d.timestamp_utc.astype(str)
    return d,info

def audit(archive,out):
    out=Path(out)
    if out.exists():raise FileExistsError(out)
    out.mkdir(parents=True)
    if sha_bytes(Path(archive).read_bytes())!=ARCHIVE_SHA:raise ValueError('wrong archive')
    with zipfile.ZipFile(archive) as z:
        ds={name:read_csv(z,'files/DSI/'+name+'.csv',header=None).to_numpy() for name in ['rm_rss','rm_crd','rm_tms','tj_rss','tj_crd','tj_tms']}
        ex={s:{k:read_csv(z,f'files/DSI/{k}_{s}.csv') for k in ['x','y']} for s in ['train','val','test']}
        identities={f:{'bytes':z.getinfo(f).file_size,'sha256':sha_bytes(z.read(f))} for f in z.namelist() if (f.startswith('files/DSI/') or f=='files/lorawan/lorawan_dataset_antwerp.csv') and not '/.' in f and not f.endswith('/')}
        raw=read_csv(z,'files/lorawan/lorawan_dataset_antwerp.csv')
        assert sha_bytes(z.read('files/lorawan/lorawan_dataset_antwerp.csv'))==RAW_LORA_SHA
    # Verification of complete arrays, not choosing a favorable statistical transformation.
    assert np.max(abs(ds['tj_crd']-ex['train']['y'].to_numpy()))<=1e-10
    assert np.array_equal(np.where(ds['tj_rss']==-150,-98,ds['tj_rss']),ex['train']['x'].to_numpy())
    records=[];coord_sets={};maxdiff=0;mask_ambig=0;first_match=True
    for part in ['train','val','test']:
        prefix='tj' if part=='train' else 'rm';X=ds[prefix+'_rss'];Y=ds[prefix+'_crd'];T=ds[prefix+'_tms'].reshape(-1)
        Xp=ex[part]['x'].to_numpy();Yp=ex[part]['y'].to_numpy();coords=[]
        for j,(xx,yy) in enumerate(zip(Xp,Yp)):
            xy=np.flatnonzero(np.max(np.abs(Y-yy),axis=1)<=1e-10)
            matches=xy[np.all(np.where(X[xy]==-150,-98,X[xy])==xx,axis=1)]
            if len(matches)==0:raise ValueError(('unresolved prepared DSI row',part,j))
            maxdiff=max(maxdiff,float(np.max(abs(Y[matches]-yy))))
            coords.append(tuple(Y[matches[0]]))
            masks=np.unique(X[matches]==-150,axis=0)
            ambig=len(masks)>1;mask_ambig+=int(ambig)
            first_match=first_match and int(xy.min()) in set(map(int,matches))
            rec={'partition':part,'prepared_row_index0':j,'x_payload_sha256':identities[f'files/DSI/x_{part}.csv']['sha256'],
                 'y_payload_sha256':identities[f'files/DSI/y_{part}.csv']['sha256'],
                 'raw_source':prefix,'raw_rss_sha256':identities[f'files/DSI/{prefix}_rss.csv']['sha256'],
                 'compatible_raw_rows':list(map(int,matches)),'all_coordinate_group_rows':list(map(int,xy)),
                 'compatible_occurrences':len(matches),'unique_raw_occurrence':len(matches)==1,
                 'earliest_compatible_timestamp_unix':int(T[matches].min()),'latest_compatible_timestamp_unix':int(T[matches].max()),
                 'absence_mask_unique_over_candidates':not ambig,'first_coordinate_occurrence_compatible':int(xy.min()) in set(map(int,matches)),
                 'present_raw_minus98_cells_first_candidate':int(np.sum(X[matches[0]]==-98)),
                 'canonical_coordinate_group_id':sha_bytes(np.asarray(Y[matches[0]],dtype='<f8').tobytes())}
            records.append(rec)
        coord_sets[part]=set(coords)
    assert coord_sets['val'].isdisjoint(coord_sets['test'])
    assert len(coord_sets['val']|coord_sets['test'])==len(np.unique(ds['rm_crd'],axis=0))==230
    if coord_sets['train']&(coord_sets['val']|coord_sets['test']):raise ValueError('DSI exact coordinate role overlap; pause role claim')
    # The data establish correspondence; the historical generator/order seed remains unauthenticated.
    info={'status':'PASS_FOR_ARCHIVED_PREPARED_INPUTS_AND_COMPATIBLE_RAW_OCCURRENCE_GROUPS',
          'original_preparation_notebook_retrieved':False,'historical_generator_or_seed_authenticated':False,
          'native_prepared_roles_preserved':True,'training_trajectory_order_verified':True,
          'prepared_counts':{p:len(ex[p]['x']) for p in ex},'features':157,
          'raw_counts':{'radio_map':len(ds['rm_rss']),'trajectory':len(ds['tj_rss'])},
          'radio_map_unique_coordinates':230,'prepared_val_test_coordinates_disjoint':True,
          'train_vs_other_exact_coordinate_groups_disjoint':True,'max_coordinate_roundtrip_difference_m':maxdiff,
          'consistent_empirical_value_conversion':'-150 raw absence -> -98; all other values unchanged',
          'raw_present_minus98_count':int(np.sum(ds['rm_rss']==-98)),'ambiguous_absence_mask_prepared_rows':mask_ambig,
          'prepared_rows_with_multiple_compatible_occurrences':sum(r['compatible_occurrences']>1 for r in records),
          'all_prepared_radio_map_rows_compatible_with_first_raw_coordinate_occurrence':first_match,
          'caution':'First-compatible-occurrence is a reconstruction representative, not a proven historical choice. Prepared model inputs are authoritative. Missing MAC IDs are not fabricated. Values -98 do not themselves identify absence.',
          'raw_time_ranges':{p:{'first_unix':int(ds[p+'_tms'].min()),'last_unix':int(ds[p+'_tms'].max()),
                             'first_utc':str(pd.to_datetime(int(ds[p+'_tms'].min()),unit='s',utc=True)),
                             'last_utc':str(pd.to_datetime(int(ds[p+'_tms'].max()),unit='s',utc=True))} for p in ['rm','tj']}}
    write_json(out/'DSI_LINEAGE_RECEIPT.json',info);write_json(out/'DSI_OCCURRENCE_CANDIDATES.json',records)
    compact=[{k:v for k,v in r.items() if not isinstance(v,list)} for r in records]
    save_csv(pd.DataFrame(compact),out/'DSI_LINEAGE.csv')
    ledger=pd.read_csv(ROOT/'sources/inherited/ROW_ROLE_LEDGER.csv.gz')
    assert len(ledger)==55375 and ledger.source_row_index0.nunique()==55375
    # Every inherited timestamp is independently checked against the original payload.
    assert np.array_equal(ledger.rx_time.to_numpy(),raw.iloc[ledger.source_row_index0]['RX Time'].to_numpy())
    r,ri=time_roles(ledger);save_csv(r,out/'LORAWAN_TEMPORAL_ROLE_LEDGER.csv.gz');write_json(out/'TEMPORAL_ROLE_RECEIPT.json',ri)
    write_json(out/'INPUT_MEMBER_IDENTITIES.json',identities)
    print(json.dumps({'DSI':info,'temporal':{k:v for k,v in ri.items() if k!='raw_day_counts'}},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();audit(a.archive,a.out)
