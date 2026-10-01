#!/usr/bin/env python3
"""Reproduce a named CSV cohort through both CSV-native and JSON-native access.

Requires the baseline S1 extraction and the output of its unchanged `join` route.
Does NOT refit a coordinate, choose a new cohort, run a non-WCL optimizer, or
replicate any external publication. Coordinates are compared at the baseline's
0.1-m catalogue precision. All output is in a new directory outside the baseline.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import json
import platform
import shutil
import tempfile
from pathlib import Path
import zipfile
import numpy as np
import pandas as pd
from pyproj import Transformer
from resource_contract import (centroid, require_rows, require_source,
                               require_unique_linkage, select_receptions, sha256_file)

HASHES = {'csv': '870abe60a4bd81f31ede6f269b6bc6329e05d2731343dff7015bae1a61218446',
          'json': 'f2f1fbd478cdef2b76fb8e3aae33751d332b50fc8546684d8e73fdb1505451cb'}

@contextmanager
def payload(source: Path, kind: str):
    with tempfile.TemporaryDirectory(prefix='pa_pr2_') as td:
        p = source
        if zipfile.is_zipfile(p):
            with zipfile.ZipFile(p) as z:
                choices = [n for n in z.namelist() if not n.endswith('/')
                    and '__MACOSX' not in Path(n).parts and not Path(n).name.startswith('._')
                    and (Path(n).name == 'lorawan_antwerp_2019_dataset.csv' if kind == 'csv'
                         else Path(n).name in ('lorawan_antwerp_2019_dataset.json.txt', 'lorawan_antwerp_2019_dataset.json'))]
                if len(choices) != 1:
                    raise ValueError(f'Ambiguous {kind} scientific payload')
                p = Path(td) / Path(choices[0]).name
                with z.open(choices[0]) as src, p.open('wb') as dest:
                    shutil.copyfileobj(src, dest)
        require_source(sha256_file(p), HASHES[kind])
        yield p


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    for key in ('baseline', 'join', 'csv', 'json', 'out'):
        ap.add_argument('--'+key, type=Path, required=True)
    a = ap.parse_args(); root=a.baseline.resolve(); comp=root/'computational'; out=a.out.resolve()
    if out.is_relative_to(root):
        raise ValueError('Output cannot be inside baseline')
    out.mkdir(parents=True, exist_ok=False)
    paths = {
        'fresh_alignment': a.join/'alignment.csv.gz',
        'fresh_identities': a.join/'rebuilt_full_identities.json',
        'fresh_catalogue39': a.join/'rebuilt_catalogue_all39.json',
        'primary_rows': comp/'populations/official33_primary_rows.csv',
        'metadata33': comp/'data_products/metadata33.json',
        'catalogue249': comp/'data_products/gateway_catalogue_249.json',
        'saved_predictions': comp/'results/benchmark/geometric_predictions.csv.gz',
    }
    before={name:sha256_file(p) for name,p in paths.items()}
    mapping=json.loads(paths['fresh_identities'].read_text()); require_unique_linkage(mapping)
    inverse={e:b for b,e in mapping.items()}; meta=json.loads(paths['metadata33'].read_text())
    roster=set(meta); cat=json.loads(paths['catalogue249'].read_text())
    if len(mapping)!=44 or len(roster)!=33: raise ValueError('Unexpected source or roster')
    freshcat=json.loads(paths['fresh_catalogue39'].read_text())
    if any(meta[b]!=freshcat[b] for b in roster): raise ValueError('Fresh projection differs')
    primary=pd.read_csv(paths['primary_rows']).sort_values('rank0')
    rows=list(map(int,primary.csv_row_index0)); require_rows(rows,rows)
    aligned=pd.read_csv(paths['fresh_alignment'])
    require_rows(list(map(int,aligned.csv_row_index0)),list(range(130429)))
    align=aligned.set_index('csv_row_index0')
    saved=pd.read_csv(paths['saved_predictions'])
    saved=saved[(saved.experiment=='primary33') & (saved.assignment=='official')].sort_values('sample_rank0')
    require_rows(list(map(int,saved.csv_row_index0)),rows)
    saved=saved.set_index('csv_row_index0')
    tf=Transformer.from_crs(4326,32631,always_xy=True)
    by_eui={}
    for b in roster:
        gateway=cat[mapping[b]]
        x,y=tf.transform(gateway['longitude'],gateway['latitude'])
        by_eui[mapping[b]]=[round(float(x),1), round(float(y),1)]
    if any(meta[b]!=by_eui[mapping[b]] for b in roster):
        raise ValueError('JSON-native catalogue projection differs at declared precision')
    with payload(a.csv,'csv') as pc, payload(a.json,'json') as pj:
        d=pd.read_csv(pc); js=json.loads(pj.read_text())
    cols=[f'BS {i}' for i in range(1,73)]; raw=d[cols].to_numpy(float)
    records=[]; largest_cross=0.; largest_saved=0.; max_gps=0.; mismatch=0; multi=0
    for rank, i in enumerate(rows):
        j=int(align.loc[i,'json_index0_occurrence_representative']); msg=js[j]
        csv_recs={str(k+1):float(v) for k,v in enumerate(raw[i]) if v!=-200}
        json_recs={inverse[str(g['id'])]:float(g['rssi']) for g in msg['gateways']}
        if csv_recs!=json_recs:
            raise ValueError(f'All-reception mismatch for CSV row {i}')
        cs=select_receptions(csv_recs,roster); jj=select_receptions(json_recs,roster)
        if cs!=jj: raise ValueError(f'Reception order differs at {i}')
        if len(cs)<3: raise ValueError('Primary row no longer eligible')
        old=saved.loc[i]
        if ';'.join(b for b,_ in cs)!=old.selected_receivers:
            raise ValueError('Declared source order differs from saved prediction')
        axy=centroid(cs,meta)
        # JSON-native coordinate lookup directly by the gateway identifiers.
        jselected=[(mapping[b],r) for b,r in jj]
        bxy=centroid(jselected,by_eui)
        pos_delta=float(np.linalg.norm(axy-bxy));largest_cross=max(largest_cross,pos_delta)
        saved_delta=float(np.linalg.norm(axy-[old.WCL_raw_x,old.WCL_raw_y]));largest_saved=max(largest_saved,saved_delta)
        x,y=tf.transform(float(d.Longitude.iloc[i]),float(d.Latitude.iloc[i]))
        xj,yj=tf.transform(float(msg['longitude']),float(msg['latitude']))
        # GPS is checked AFTER metadata alignment; it never selects an identity.
        gps_delta=float(np.linalg.norm(np.array([xj,yj])-[x,y]));max_gps=max(max_gps,gps_delta)
        if gps_delta>1e-7: mismatch+=1
        error=float(np.linalg.norm(axy-[x,y]))
        if saved_delta>1e-7 or abs(error-float(old.WCL_raw_error_m))>1e-7:
            raise ValueError('Frozen raw-WCL reproduction differs from saved evidence')
        mult=int(align.loc[i,'group_multiplicity']);multi+=mult>1
        records.append({'sample_rank0':rank,'csv_row_index0':i,'json_index0_occurrence_representative':j,
            'group_multiplicity':mult,'selected_BS':';'.join(b for b,_ in cs),
            'selected_gateway_ids':';'.join(mapping[b] for b,_ in cs),
            'csv_native_x':float(axy[0]),'csv_native_y':float(axy[1]),
            'json_native_x':float(bxy[0]),'json_native_y':float(bxy[1]),
            'cross_representation_position_delta_m':pos_delta,
            'csv_reference_error_m':error})
    if len(records)!=2495 or largest_cross>1e-10: raise ValueError('Incomplete representation check')
    pd.DataFrame(records).to_csv(out/'ROW_PRESERVING_REPLAY.csv.gz',index=False,
        compression={'method':'gzip','mtime':0})
    summary={
        'scope':'New CSV/JSON-native frozen-catalogue raw-WCL replay on original 2495 rows, not a coordinate refit or external-paper replication.',
        'rows_checked':len(records),'same_row_order':True,'same_selected_ids_and_RSSI':True,
        'max_cross_representation_position_delta_m':largest_cross,
        'max_saved_position_delta_m':largest_saved,
        'metadata_median_error_m':float(np.median([r['csv_reference_error_m'] for r in records])),
        'primary_rows_in_duplicate_serialization_groups':int(multi),
        'max_post_alignment_GPS_delta_m':max_gps,'post_alignment_GPS_mismatches_gt_1e_minus7_m':mismatch,
        'catalogue_backed_identities':len(freshcat),'active_identities':len(mapping),
        'input_hashes':before,'raw_payload_hashes':HASHES,
        'identity_warning':'JSON indices are occurrence representatives in indistinguishable groups, not certified physical-message identities.',
        'positive_result':'Verified translation preserves the chosen CSV cohort and declared receiver-order contract; it does not improve accuracy relative to correctly aligned JSON-native access.',
        'environment':{'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__},
        'source_files_unchanged':all(sha256_file(paths[n])==h for n,h in before.items()),
    }
    (out/'REPLAY_RECEIPT.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    print(json.dumps(summary,indent=2))

if __name__=='__main__': main()
