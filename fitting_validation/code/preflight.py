#!/usr/bin/env python3
"""Verify baseline inputs and construct leakage-controlled MV1 split ledgers.

No coordinate fitter or validation scorer is called. Output must be new and
outside the extracted baseline. Raw CSV/JSON can be plain or single-payload ZIPs.
"""
from __future__ import annotations
import argparse, collections, datetime, gzip, hashlib, io, json, platform, random
import sys, zipfile
from pathlib import Path
import numpy as np
import pandas as pd
import pyproj
from study_contract import components, sha_role, prepare_observations, fit_box


def digest(p: Path, algorithm: str = 'sha256') -> str:
    h = hashlib.new(algorithm)
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1<<20),b''): h.update(block)
    return h.hexdigest()


def payload(p: Path) -> bytes:
    if p.suffix.lower() != '.zip': return p.read_bytes()
    with zipfile.ZipFile(p) as z:
        names = [n for n in z.namelist() if not n.endswith('/') and
                 not n.startswith('__MACOSX/') and not Path(n).name.startswith('._')]
        if len(names) != 1: raise ValueError(f'Expected exactly one scientific payload: {p}: {names}')
        return z.read(names[0])


def write_json(p: Path, obj) -> None:
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, allow_nan=False, sort_keys=True)+'\n')


def write_csv(p: Path, frame: pd.DataFrame) -> None:
    raw = frame.to_csv(index=False).encode()
    if p.name.endswith('.gz'):
        with p.open('wb') as target:
            with gzip.GzipFile(fileobj=target, mode='wb', filename='',mtime=0) as f: f.write(raw)
    else: p.write_bytes(raw)


def main() -> None:
    ap=argparse.ArgumentParser()
    for key in ['baseline','csv','json','catalogue','protocol','out']:
        ap.add_argument('--'+key, required=True, type=Path)
    a=ap.parse_args()
    root=a.baseline.resolve(); out=a.out.resolve()
    if out.is_relative_to(root): raise SystemExit('Output must be outside the baseline')
    out.mkdir(parents=True,exist_ok=False)
    protocol=json.loads(a.protocol.read_text())
    checks=[]
    def check(name: str, condition: bool, **detail):
        checks.append({'check':name,'pass':bool(condition),**detail})
        if not condition:
            write_json(out/'CHECKS_FAILED.json',checks)
            raise AssertionError(f'Preflight failed: {name}')
    identities=[]
    for mname in ['MANIFEST.json','EVIDENCE_MANIFEST.json']:
        m=json.loads((root/mname).read_text()); failures=[]
        for e in m['files']:
            p=root/e['path']; correct=p.is_file() and p.stat().st_size==e.get('size',e.get('bytes')) and digest(p)==e['sha256']
            if not correct: failures.append(e['path'])
        check(mname+' all member bytes match',not failures,entries=len(m['files']),failures=failures)
        identities.append({'role':mname,'sha256':digest(root/mname),'bytes':(root/mname).stat().st_size})
    binding=json.loads((root/'REVIEW_BINDING.json').read_text())
    for e in binding['documents']:
        check('PDF binding '+e['path'],digest(root/e['path'])==e['sha256'])
        identities.append({'role':e['path'],'sha256':e['sha256'],'bytes':e['size']})
    check('Evidence manifest binding',digest(root/'EVIDENCE_MANIFEST.json')==binding['evidence_manifest_sha256'])
    rawcsv=payload(a.csv); rawjson=payload(a.json); rawcatalogue=payload(a.catalogue)
    for name,raw,path in [('csv',rawcsv,a.csv),('json',rawjson,a.json),('catalogue',rawcatalogue,a.catalogue)]:
        h=hashlib.sha256(raw).hexdigest()
        check(name+' payload hash',h==protocol['raw_input_hashes'][name])
        identities.append({'role':name+' payload','sha256':h,'md5':hashlib.md5(raw).hexdigest(),'bytes':len(raw),'container_sha256':digest(path)})
    # Hash JSON only. Identity-join execution is deliberately out of scope.
    del rawjson,rawcatalogue
    df=pd.read_csv(io.BytesIO(rawcsv));del rawcsv
    columns=[f'BS {i}' for i in range(1,73)]
    check('source CSV shape',df.shape==(130429,77))
    vals=df[columns].to_numpy(float)
    valid=np.isfinite(vals)&(vals>=-150)&(vals<=-20)
    rows=np.flatnonzero((valid.sum(axis=1)>=3)&np.isfinite(df.Latitude)&np.isfinite(df.Longitude))
    ledger=pd.read_csv(root/'computational/populations/working_source_ledger.csv.gz').sort_values('working_index0')
    check('working membership and order',len(rows)==55375 and np.array_equal(rows,ledger.csv_row_index0))
    tf=pyproj.Transformer.from_crs(4326,32631,always_xy=True)
    x,y=tf.transform(df.Longitude.iloc[rows].to_numpy(),df.Latitude.iloc[rows].to_numpy())
    xy=np.column_stack([x,y]);oldxy=ledger[['utm_x','utm_y']].to_numpy()
    check('raw projection agrees with ledger',np.max(np.abs(xy-oldxy))<=1e-7,max_absolute_difference_m=float(np.max(np.abs(xy-oldxy))))
    wv=vals[rows];wm=valid[rows]
    legacy=[]; serial=[]
    for wi,rowid in enumerate(rows):
        ids=np.flatnonzero(wm[wi])
        pairs=tuple(sorted((str(j+1),round(float(wv[wi,j]),3)) for j in ids))
        key=(round(float(xy[wi,0]),3),round(float(xy[wi,1]),3),pairs)
        legacy.append(hashlib.sha256(json.dumps(key,separators=(',',':')).encode()).hexdigest())
        row=df.iloc[int(rowid)]
        skey=(str(row['RX Time']),int(row.SF),round(float(row.HDOP),2),tuple(sorted(int(wv[wi,j]) for j in np.flatnonzero(wv[wi]!=-200))))
        serial.append(hashlib.sha256(json.dumps(skey,separators=(',',':')).encode()).hexdigest())
    check('all raw legacy content keys agree',legacy==list(ledger.legacy_content_sha256),n=len(legacy))
    order=list(range(len(rows)));random.Random(1).shuffle(order);ci=order[:16612];pi=order[16612:]
    cal=pd.read_csv(root/'computational/populations/calibration_rows.csv')
    check('calibration row order',np.array_equal(rows[ci],cal.csv_row_index0) and np.array_equal(ci,cal.working_index0))
    metadata=json.loads((root/'computational/data_products/metadata33.json').read_text())
    bslist=sorted(map(int,metadata)); bidx=np.asarray(bslist)-1
    check('primary roster count',len(bslist)==33)
    eligible=[i for i in pi if wm[i,bidx].sum()>=3]
    ckeys={legacy[i] for i in ci};skeys={serial[i] for i in ci}
    sampled=random.Random(9).sample(eligible,2500)
    primary=[i for i in sampled if legacy[i] not in ckeys]
    frozen=pd.read_csv(root/'computational/populations/official33_primary_rows.csv')
    check('primary sample reconstruction',len(primary)==2495 and np.array_equal(rows[primary],frozen.csv_row_index0))
    check('primary legacy content disjoint',not({legacy[i] for i in primary}&ckeys))
    check('primary serialization keys disjoint',not({serial[i] for i in primary}&skeys))
    cirows=list(map(int,rows[ci]));cl=[legacy[i] for i in ci];cs=[serial[i] for i in ci]
    cells=[f'{int(np.floor(xy[i,0]/1000))}:{int(np.floor(xy[i,1]/1000))}' for i in ci]
    duplicate=components([cl,cs],cirows)
    spatial=components([cl,cs,cells],cirows)
    duplicate_counts=collections.Counter(duplicate)
    summaries={}
    for split, groups in [('group80',duplicate),('space1000',spatial)]:
        sr=out/split;sr.mkdir()
        salt=protocol['splits']['primary' if split=='group80' else 'sensitivity']['salt']
        roles=[sha_role(str(g),salt) for g in groups]
        fit_positions=[i for i,r in enumerate(roles) if r=='fitting']
        val_positions=[i for i,r in enumerate(roles) if r=='validation']
        check(split+' both sides nonempty',bool(fit_positions) and bool(val_positions))
        for kind, keys in [('content',cl),('serialization',cs),('component',groups)]+([('spatial_cell',cells)] if split=='space1000' else []):
            check(split+' disjoint '+kind,not({keys[i] for i in fit_positions}&{keys[i] for i in val_positions}))
        fitwi=[ci[i] for i in fit_positions];valwi=[ci[i] for i in val_positions]
        fbox=fit_box(xy[fitwi])
        by=collections.OrderedDict()
        for wi in fitwi:
            ids=np.flatnonzero(wm[wi]);ranked=ids[np.argsort(-wv[wi,ids],kind='stable')]
            for j in ranked:by.setdefault(int(j+1),[]).append((int(rows[wi]),wi,float(wv[wi,j])))
        rng=random.Random(1); prep=[];retained_rows=[]
        for rank,(bs,records) in enumerate(by.items()):
            retained,record=prepare_observations(records,rng)
            pxy=xy[[r[1] for r in retained]];lo,hi=fit_box(pxy)
            check(split+f' BS{bs} nested domains',np.all(fbox[0]<=lo) and np.all(hi<=fbox[1]))
            nval=int(wm[valwi,bs-1].sum())
            rec={'bs':bs,'receiver_rank0':rank,**record,'validation_n':nval,
                 'primary_roster':bs in bslist,'eligible_fit':len(records)>=10,
                 'eligible_validation':nval>0,'distinct_retained_tx':len(np.unique(pxy,axis=0)),
                 'narrow_xmin':float(lo[0]),'narrow_ymin':float(lo[1]),'narrow_xmax':float(hi[0]),'narrow_ymax':float(hi[1]),
                 'wide_xmin':float(fbox[0][0]),'wide_ymin':float(fbox[0][1]),'wide_xmax':float(fbox[1][0]),'wide_ymax':float(fbox[1][1])}
            prep.append(rec)
            for j,(rowid,wi,rssi) in enumerate(retained):retained_rows.append({'bs':bs,'retained_rank0':j,'csv_row_index0':rowid,'working_index0':wi})
        # Explicitly retain primary receivers absent from fitting.
        for bs in bslist:
            if bs not in by:
                prep.append({'bs':bs,'receiver_rank0':None,'pre_filter_n':0,'subsample_n':0,'strong_threshold_dbm':None,'strong_filter_used':False,'retained_n':0,'validation_n':int(wm[valwi,bs-1].sum()),'primary_roster':True,'eligible_fit':False,'eligible_validation':bool(wm[valwi,bs-1].sum()),'distinct_retained_tx':0})
        pf=pd.DataFrame(prep)
        primaryprep=pf.loc[pf.primary_roster].sort_values('bs')
        check(split+' all primary receivers accounted',list(primaryprep.bs)==bslist)
        fit_supported=set(map(int,primaryprep.loc[primaryprep.eligible_fit,'bs']))
        complete=[]
        selected=[]
        for wi in primary:
            ids=bidx[wm[wi,bidx]];ids=ids[np.argsort(-wv[wi,ids],kind='stable')][:10]
            bs=ids+1;ok=set(map(int,bs))<=fit_supported
            selected.append({'csv_row_index0':int(rows[wi]),'working_index0':wi,'selected_receivers':';'.join(map(str,bs)),'map_support_complete':ok})
            if ok:complete.append(wi)
        splitframe=pd.DataFrame({'calibration_rank0':range(len(ci)),'csv_row_index0':cirows,'working_index0':ci,'legacy_content_sha256':cl,'serialization_sha256':cs,'duplicate_component':duplicate,'split_component':groups,'spatial_cell':cells,'role':roles})
        write_csv(sr/'split_rows.csv.gz',splitframe)
        write_csv(sr/'all_receiver_support_and_domains.csv',pf)
        write_csv(sr/'primary33_support.csv',primaryprep)
        write_csv(sr/'retained_fit_rows.csv.gz',pd.DataFrame(retained_rows))
        write_csv(sr/'fixed_primary_selection.csv.gz',pd.DataFrame(selected))
        summaries[split]={'calibration_rows':16612,'fitting_rows':len(fitwi),'validation_rows':len(valwi),'split_components':len(set(groups)),
             'fitting_components':len({groups[i] for i in fit_positions}),'validation_components':len({groups[i] for i in val_positions}),
             'all_fitting_receivers':len(by),'primary_receivers':len(primaryprep),'primary_fit_supported':int(primaryprep.eligible_fit.sum()),'primary_validation_supported':int(primaryprep.eligible_validation.sum()),
             'primary_fit_and_validation_supported':int((primaryprep.eligible_fit&primaryprep.eligible_validation).sum()),
             'primary_min_fitting_receptions':int(primaryprep.pre_filter_n.min()),'primary_min_validation_receptions':int(primaryprep.validation_n.min()),
             'no_validation_receivers':list(map(int,primaryprep.loc[~primaryprep.eligible_validation,'bs'])),
             'fit_unsupported_receivers':list(map(int,primaryprep.loc[~primaryprep.eligible_fit,'bs'])),
             'existing_primary_messages_with_all_selected_coordinates_supported':len(complete),'primary_messages_total':2495,
             'all_retained_fitting_links':len(retained_rows),'primary_retained_fitting_links':int(primaryprep.retained_n.sum()),
             'wide_box':{'lower':fbox[0].tolist(),'upper':fbox[1].tolist()}}
        write_json(sr/'summary.json',summaries[split])
    summary={'scope':'Input/split/support preparation only. No coordinate optimization, model validation scoring or new localization predictions.',
       'protocol_sha256':digest(a.protocol),'source_rows':len(df),'working_rows':len(rows),'calibration_rows':len(ci),'primary_rows':len(primary),
       'calibration_duplicate_components':len(duplicate_counts),'duplicate_components_with_multiple_rows':sum(v>1 for v in duplicate_counts.values()),'rows_in_duplicate_components':sum(v for v in duplicate_counts.values() if v>1),
       'maximum_duplicate_component_size':max(duplicate_counts.values()),'splits':summaries,'input_files':identities,
       'environment':{'python':sys.version.split()[0],'numpy':np.__version__,'pandas':pd.__version__,'pyproj':pyproj.__version__,'platform':platform.platform()},
       'check_count':len(checks),'checks_passed':sum(c['pass'] for c in checks),'checks_failed':sum(not c['pass'] for c in checks)}
    write_json(out/'PREFLIGHT_SUMMARY.json',summary);write_json(out/'CHECKS.json',checks)
    print(json.dumps({k:summary[k] for k in ['scope','calibration_duplicate_components','duplicate_components_with_multiple_rows','splits','check_count','checks_failed']},indent=2))

if __name__=='__main__':main()
