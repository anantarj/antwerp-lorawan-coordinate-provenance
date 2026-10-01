"""Bind historical DAE exports to G1 source rows; construct label-blind role exclusions."""
from __future__ import annotations
from pathlib import Path
import argparse,io,json,zipfile
import numpy as np,pandas as pd
from pyproj import Transformer
from common import ROOT,load_protocol,sha_bytes,array_hash,write_json

def build(archive:Path,out:Path)->None:
    protocol=load_protocol()
    if out.exists():raise FileExistsError(out)
    out.mkdir(parents=True)
    if sha_bytes(archive.read_bytes())!=protocol['source_ids']['files.zip']['sha256']:raise ValueError('wrong source archive')
    with zipfile.ZipFile(archive) as z:
        rawbytes=z.read('files/lorawan/lorawan_dataset_antwerp.csv')
        if sha_bytes(rawbytes)!='870abe60a4bd81f31ede6f269b6bc6329e05d2731343dff7015bae1a61218446':raise ValueError('raw payload mismatch')
        raw=pd.read_csv(io.BytesIO(rawbytes))
        for part in ['train','val','test']:
            for typ in ['x','y']:
                rel=f'files/lorawan/{typ}_{part}.csv'
                p=out/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(rel))
    side={p:pd.read_csv(ROOT/f'sources/g1/results/pass1/dae/sidecars/{p}_row_handles.csv.gz') for p in ['train','val','test']}
    ids={p:d.source_row_index0.to_numpy(np.int64) for p,d in side.items()}
    allids=np.concatenate(list(ids.values())); assert len(allids)==55375 and len(np.unique(allids))==55375
    checks=[]
    for p in ids:
        x=pd.read_csv(out/f'files/lorawan/x_{p}.csv');y=pd.read_csv(out/f'files/lorawan/y_{p}.csv')
        xr=raw.iloc[ids[p],:72].to_numpy();yr=raw.iloc[ids[p]][['Latitude','Longitude']].to_numpy()
        assert np.array_equal(x.to_numpy(),xr)
        md=float(np.abs(y.to_numpy()-yr).max());assert md<=1e-12
        checks.append({'partition':p,'rows':len(x),'features':len(x.columns),'feature_exact':True,'target_max_difference_deg':md,'row_sha256':array_hash(ids[p])})
    parent={int(i):int(i) for i in allids}
    def find(i):
        while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
        return i
    def union(a,b):
        a,b=find(a),find(b)
        if a!=b:parent[max(a,b)]=min(a,b)
    rr=raw.iloc[allids]
    tr=Transformer.from_crs(4326,32631,always_xy=True)
    east,north=tr.transform(rr.Longitude.to_numpy(),rr.Latitude.to_numpy())
    measurements=rr.iloc[:,:72].to_numpy();serial_first={};content_first={}
    for k,rid in enumerate(allids):
        a=measurements[k]; observed=np.flatnonzero(a!=-200)
        ser=(str(rr.iloc[k]['RX Time']),int(rr.iloc[k]['SF']),round(float(rr.iloc[k]['HDOP']),2),tuple(sorted(float(v) for v in a[observed])))
        valid=np.flatnonzero(np.isfinite(a)&(a>=-150)&(a<=-20))
        con=(round(float(east[k]),3),round(float(north[k]),3),tuple(sorted((str(int(j+1)),round(float(a[j]),3)) for j in valid)))
        for dic,key in [(serial_first,ser),(content_first,con)]:
            if key in dic:union(int(rid),dic[key])
            else:dic[key]=int(rid)
    group={int(i):find(int(i)) for i in allids}
    train_groups={group[int(i)] for i in ids['train']};val_groups={group[int(i)] for i in ids['val']}
    rec=[]
    for p in ids:
        for rank,i in enumerate(ids[p]):
            g=group[int(i)];keep=True;reason='native_training' if p=='train' else 'retained'
            if p=='val' and g in train_groups:keep=False;reason='group_touches_training'
            if p=='test' and g in train_groups:keep=False;reason='group_touches_training'
            elif p=='test' and g in val_groups:keep=False;reason='group_touches_validation'
            rec.append({'partition':p,'partition_rank0':rank,'source_row_index0':int(i),'group_min_source_index0':g,'primary_role_eligible':keep,'reason':reason,'rx_time':str(raw.iloc[int(i)]['RX Time'])})
    roles=pd.DataFrame(rec);roles.to_csv(out/'ROW_ROLE_LEDGER.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    summaries=roles.groupby(['partition','primary_role_eligible','reason'],sort=True).size().rename('n').reset_index().to_dict('records')
    write_json(out/'INPUT_ROLE_RECEIPT.json',{'checks':checks,'role_counts':summaries,'n_groups':len(set(group.values())),'n_source_rows':len(allids),'native_model_training_unchanged':True,'no_independence_claim':True,'protocol_sha256':sha_bytes((ROOT/'protocol/EXECUTION_PROTOCOL.json').read_bytes()),'role_ledger_sha256':sha_bytes((out/'ROW_ROLE_LEDGER.csv.gz').read_bytes())})
    print(json.dumps(summaries,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();build(a.archive,a.out)
