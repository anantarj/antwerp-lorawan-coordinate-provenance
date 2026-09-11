#!/usr/bin/env python3
"""Describe Paper A's frozen F2 coordinate intervention; never fit coordinates.

Inputs: the exact F2 ZIP (or an unchanged extraction), and the original CSV or CSV
ZIP. Output must not exist. No localization optimizer is called or imported.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import io
import json
import math
import platform
import random
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from contextlib import contextmanager
from typing import Iterator

import numpy as np
import pandas as pd
import pyproj
from pyproj import Transformer

F2_SHA = '4dc48ffeed3b80c8aaa6642ca595e81118783d4393954924b204dba78b6eaaea'
F2_MANIFEST_SHA = 'e8b27917dce9c4e730ec50584dc4bba84b61cbd4dd46cc0eb2bff25c67913aeb'
CSV_SHA = '870abe60a4bd81f31ede6f269b6bc6329e05d2731343dff7015bae1a61218446'
FIT_SHA = '93e4509d1e7300b92a0a6b3dabbfab251237ea686e4cdd786986419b755f57d6'
COORD_TOL = 1e-8
POSITION_TOL = 1e-7
NEAR_M = 60.0


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def dump(p: Path, v: object) -> None:
    p.write_text(json.dumps(v, indent=2, allow_nan=False, ensure_ascii=False)+'\n')


def write_csv(p: Path, d: pd.DataFrame) -> None:
    kwargs = {'compression': {'method': 'gzip', 'mtime': 0}} if p.name.endswith('.gz') else {}
    d.to_csv(p, index=False, **kwargs)


@contextmanager
def f2_root(p: Path) -> Iterator[Path]:
    if p.is_dir():
        if sha_file(p/'MANIFEST.json') != F2_MANIFEST_SHA:
            raise ValueError('F2 directory manifest fingerprint differs from the frozen input.')
        yield p
    else:
        if sha_file(p) != F2_SHA:
            raise ValueError('The F2 archive fingerprint differs from the frozen input.')
        with tempfile.TemporaryDirectory(prefix='paper_a_f3_input_') as t:
            with zipfile.ZipFile(p) as z:
                for item in z.infolist():
                    n = PurePosixPath(item.filename)
                    if n.is_absolute() or '..' in n.parts or (item.external_attr >> 16) & 0o170000 == 0o120000:
                        raise ValueError('Unsafe archive member: '+item.filename)
                z.extractall(t)
            yield Path(t)/'Paper_A_R3_F2_2026-09-06'


def csv_payload(p: Path) -> bytes:
    if zipfile.is_zipfile(p):
        with zipfile.ZipFile(p) as z:
            names = [n for n in z.namelist() if n.endswith('.csv') and '__MACOSX' not in n and not Path(n).name.startswith('._')]
            if len(names) != 1:
                raise ValueError('CSV ZIP must contain one scientific CSV payload.')
            b = z.read(names[0])
    else:
        b = p.read_bytes()
    if sha_bytes(b) != CSV_SHA:
        raise ValueError('CSV payload fingerprint differs from the immutable reproduction baseline.')
    return b


def stats(v: np.ndarray) -> dict:
    a = np.asarray(v, float)
    if not len(a) or not np.isfinite(a).all():
        raise ValueError('A descriptive population is empty or contains nonfinite distances.')
    return {'n': int(len(a)), 'minimum_m': float(a.min()),
            'median_m': float(np.median(a)), 'p90_m': float(np.quantile(a, .9, method='linear')),
            'maximum_m': float(a.max())}


def box_diagnostic(point: np.ndarray, low: np.ndarray, high: np.ndarray) -> dict:
    p, lo, hi = [np.asarray(x, float) for x in (point, low, high)]
    if p.shape != (2,) or lo.shape != (2,) or hi.shape != (2,) or not np.isfinite([p, lo, hi]).all() or np.any(lo > hi):
        raise ValueError('Invalid point or closed rectangle.')
    margins = np.r_[p-lo, hi-p]
    margin = float(margins.min())
    outside = float(np.linalg.norm(np.maximum(np.maximum(lo-p, p-hi), 0)))
    return {'minimum_signed_margin_m': margin, 'distance_to_closed_box_m': outside,
            'outside': bool(outside > POSITION_TOL),
            'on_boundary': bool(outside <= POSITION_TOL and abs(margin) <= POSITION_TOL),
            'within_60m_of_boundary': bool(outside <= POSITION_TOL and margin <= NEAR_M)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--f2', type=Path, required=True)
    ap.add_argument('--csv', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise FileExistsError('Output already exists; nothing was overwritten.')
    if a.f2.is_dir() and a.out.resolve().is_relative_to(a.f2.resolve()):
        raise ValueError('Output cannot be inside immutable F2 input.')
    if a.out.resolve() in [a.csv.resolve(), a.f2.resolve()]:
        raise ValueError('Output cannot replace input.')
    payload = csv_payload(a.csv)  # Refuse an invalid input before creating output.
    with f2_root(a.f2) as r:
        a.out.mkdir(parents=True, exist_ok=False)
        out = a.out
        checks: list[dict] = []
        def ck(name: str, condition: object, detail: object = None) -> None:
            checks.append({'check': name, 'pass': bool(condition), 'detail': detail})
            if not bool(condition):
                dump(out/'FAILED_CHECKS.json', checks)
                raise AssertionError(name+': '+str(detail))
        manifest = json.loads((r/'MANIFEST.json').read_text())
        bad = [v['path'] for v in manifest['files'] if not (r/v['path']).is_file() or sha_file(r/v['path']) != v['sha256']]
        ck('F2_manifest_members_match', not bad, {'members': len(manifest['files']), 'mismatches': bad})
        used: dict[str, dict] = {}
        def member(name: str) -> Path:
            p = r/name
            used[name] = {'sha256': sha_file(p), 'bytes': p.stat().st_size}
            return p
        def js(name: str):
            return json.loads(member(name).read_text())
        def cf(name: str, **kwargs):
            return pd.read_csv(member(name), **kwargs)
        meta = js('data_products/metadata33.json')
        fit = js('data_products/rssfit_stable41.json')
        fit33 = js('data_products/rssfit33.json')
        fullmeta = js('data_products/catalogue_backed39.json')
        cat = js('data_products/gateway_catalogue_249.json')
        cross = cf('data_products/receiver_crosswalk.csv', dtype={'bs': str, 'gateway_id': str}).set_index('bs')
        ck('frozen_fit41_hash', sha_file(member('data_products/rssfit_stable41.json')) == FIT_SHA)
        ck('matched33_views_are_exact_projections', len(meta)==33 and len(fit)==41 and set(meta)==set(fit33) and all(fit33[k]==fit[k] and meta[k]==fullmeta[k] for k in meta))
        source = member('src/primary/code/evaluator_stable.py').read_text()
        mod = ast.parse(source)
        func = next(n for n in mod.body if isinstance(n, ast.FunctionDef) and n.name=='estimate_gateway_positions_rssfit')
        ftext = ast.get_source_segment(source, func)
        ck('operative_fit_box_expression', 'min_xy = np.min(tx_xy, axis=0) - 2000.0' in ftext and 'max_xy = np.max(tx_xy, axis=0) + 2000.0' in ftext)
        (out/'audited_RSSFIT_source.txt').write_text(ftext+'\n')
        d = pd.read_csv(io.BytesIO(payload))
        rv = d[[f'BS {i}' for i in range(1,73)]].to_numpy(float)
        valid = np.isfinite(rv)&(rv>=-150)&(rv<=-20)
        finitepos = np.isfinite(d.Latitude.to_numpy())&np.isfinite(d.Longitude.to_numpy())
        wr = np.flatnonzero((valid.sum(1)>=3)&finitepos)
        ck('immutable_csv_census', len(d)==130429 and len(wr)==55375)
        ledger = cf('populations/working_source_ledger.csv.gz').sort_values('working_index0')
        ck('working_row_identity_exact', np.array_equal(wr,ledger.csv_row_index0.to_numpy()))
        tf = Transformer.from_crs(4326,32631,always_xy=True)
        x,y = tf.transform(d.Longitude.to_numpy(),d.Latitude.to_numpy())
        xy = np.column_stack([x,y])
        projection_error = float(np.max(np.abs(xy[wr]-ledger[['utm_x','utm_y']].to_numpy())))
        ck('working_projection_matches', projection_error<COORD_TOL, {'maximum_component_difference_m': projection_error})
        order = list(map(int,wr));random.Random(1).shuffle(order);cal=order[:16612]
        saved_cal = cf('populations/calibration_rows.csv').sort_values('rank0').csv_row_index0.tolist()
        ck('ordered_calibration_reconstructed', cal==saved_cal)
        calset = set(cal)
        by: dict[str,list] = {}
        for i in cal:
            cols = list(np.flatnonzero(valid[i]));cols.sort(key=lambda j: -rv[i,j])
            for j in cols:
                by.setdefault(str(j+1),[]).append((int(i),float(rv[i,j]),float(x[i]),float(y[i])))
        rng = random.Random(1);retained_rows=[];traversal=[];init_rows=[];boxes=[]
        for rank,(b,records) in enumerate(by.items()):
            selected = rng.sample(records,2000) if len(records)>2000 else records
            vals = np.array([z[1] for z in selected])
            threshold = float(np.quantile(vals,.75,method='linear'));mask=vals>=threshold
            kept = [z for z,yes in zip(selected,mask) if yes] if mask.sum()>=50 else selected
            points = np.array([[z[2],z[3]] for z in kept])
            lo,hi = points.min(0)-2000,points.max(0)+2000
            diag = box_diagnostic(np.array(fit[b]),lo,hi)
            row = {'bs':b,'gateway_id':str(cross.loc[b,'gateway_id']),'in_metadata33':b in meta,
                   'catalogue_available':b in fullmeta,'receiver_rank0':rank,'calibration_receptions':len(records),
                   'subsampled_receptions':len(selected),'quantile_threshold_dbm':threshold,
                   'strong_filter_used':bool(mask.sum()>=50),'fit_receptions':len(kept),
                   'xmin_m':float(lo[0]),'xmax_m':float(hi[0]),'ymin_m':float(lo[1]),'ymax_m':float(hi[1]),
                   'fit_x_m':float(fit[b][0]),'fit_y_m':float(fit[b][1]),
                   **{'fit_'+k:v for k,v in diag.items()}}
            if b in fullmeta:
                mp = np.array(fullmeta[b]);rd=box_diagnostic(mp,lo,hi)
                row.update({'metadata_x_m':float(mp[0]),'metadata_y_m':float(mp[1]),
                            'coordinate_discrepancy_m':float(np.linalg.norm(np.array(fit[b])-mp)),
                            **{'metadata_'+k:v for k,v in rd.items()}})
            boxes.append(row)
            traversal.append({'receiver_rank0':rank,'bs':b,'calibration_receptions':len(records),'subsampled_receptions':len(selected),
                              'quantile_threshold_dbm':threshold,'filtered_receptions':len(kept),'strong_filter_used':bool(mask.sum()>=50)})
            for k,(i,v,xx,yy) in enumerate(kept):
                retained_rows.append({'bs':b,'receiver_rank0':rank,'retained_rank0':k,'csv_row_index0':i,'rssi':v,'tx_x':xx,'tx_y':yy})
            ix=np.argsort(-np.array([z[1] for z in kept]),kind='stable')[:min(50,len(kept))]
            for k,j in enumerate(ix):
                i,v,xx,yy=kept[j]
                init_rows.append({'bs':b,'initialization_rank0':k,'retained_array_index0':int(j),'csv_row_index0':i,'rssi':v,'tx_x':xx,'tx_y':yy})
        actual=pd.DataFrame(retained_rows);old=cf('populations/rssfit_ordered_fit_inputs.csv.gz',dtype={'bs':str})
        idcols=['bs','receiver_rank0','retained_rank0','csv_row_index0','rssi']
        ck('all_retained_fit_rows_and_RSSI_match', actual[idcols].equals(old[idcols]),{'rows':len(actual)})
        fit_xy_error=float(np.max(np.abs(actual[['tx_x','tx_y']].to_numpy()-old[['tx_x','tx_y']].to_numpy())))
        ck('all_retained_fit_projections_match',fit_xy_error<COORD_TOL,{'maximum_component_difference_m':fit_xy_error})
        trav=pd.DataFrame(traversal);savedtrav=cf('populations/rssfit_receiver_traversal.csv',dtype={'bs':str})
        ck('receiver_traversal_and_filter_summary_match',trav.equals(savedtrav))
        newinit=pd.DataFrame(init_rows);oldinit=cf('results/prepared/rssfit_initialization_records.csv.gz',dtype={'bs':str})
        ck('stable_initializer_ids_and_order_match',newinit.drop(columns=['tx_x','tx_y']).equals(oldinit.drop(columns=['tx_x','tx_y'])))
        bdf=pd.DataFrame(boxes)
        ck('all41_fitted_points_inside_own_box',len(bdf)==41 and not bdf.fit_outside.any())
        # Scalar extrema/hypot formulation independent of the vectorized description.
        scalar_error=0.;box_error=0.
        for z in boxes:
            b=z['bs'];kept=actual[actual.bs==b]
            bounds=[min(kept.tx_x)-2000,max(kept.tx_x)+2000,min(kept.tx_y)-2000,max(kept.tx_y)+2000]
            box_error=max(box_error,max(abs(v-z[k]) for v,k in zip(bounds,['xmin_m','xmax_m','ymin_m','ymax_m'])))
            if b in fullmeta:
                scalar=math.hypot(fit[b][0]-fullmeta[b][0],fit[b][1]-fullmeta[b][1])
                scalar_error=max(scalar_error,abs(scalar-z['coordinate_discrepancy_m']))
        ck('independent_scalar_distances_and_box_extrema',scalar_error<COORD_TOL and box_error<COORD_TOL,{'distance_max_difference_m':scalar_error,'box_max_difference_m':box_error})
        bdf=bdf.sort_values('bs',key=lambda v:v.astype(int)).reset_index(drop=True)
        primary=bdf[bdf.in_metadata33].copy()
        primary['primary_selection_count']=primary.bs.map(cross.primary_selection_count).astype(int)
        primary['release_receptions']=primary.bs.map(cross.release_receptions).astype(int)
        description=[]
        for name,frame in [('metadata33',primary),('metadata32_without_BS71',primary[primary.bs!='71'])]:
            v=stats(frame.coordinate_discrepancy_m.to_numpy())
            description.append({'roster':name,**v,'maximum_bs':str(frame.loc[frame.coordinate_discrepancy_m.idxmax(),'bs']),
                'reference_outside_own_fit_box':int(frame.metadata_outside.sum()),
                'outside_reference_ids':frame.loc[frame.metadata_outside.astype(bool),'bs'].tolist(),
                'fit_on_boundary':int(frame.fit_on_boundary.sum()),
                'fit_on_boundary_ids':frame.loc[frame.fit_on_boundary,'bs'].tolist(),
                'fit_within_60m':int(frame.fit_within_60m_of_boundary.sum()),
                'fit_within_60m_ids':frame.loc[frame.fit_within_60m_of_boundary,'bs'].tolist()})
        write_csv(out/'receiver_geometry33.csv',primary)
        write_csv(out/'rssfit_search_boxes41.csv',bdf)
        write_csv(out/'rssfit_receiver_traversal.csv',trav)
        write_csv(out/'reconstructed_fit_inputs.csv.gz',actual)
        dump(out/'coordinate_summary.json',{'metric':'Euclidean catalogue-relative coordinate discrepancy in EPSG:32631 metres; fixed-roster census',
             'quantile_method':'linear','boundary_tolerance_m':POSITION_TOL,'near_boundary_threshold_m':NEAR_M,
             'rosters':description,'full_fit41_boundary_count':int(bdf.fit_on_boundary.sum()),
             'full_fit41_near_boundary_count':int(bdf.fit_within_60m_of_boundary.sum()),
             'comparison_not_physical_truth':True})
        # Retrospective BS71 description, without selecting or changing assignments.
        gid=str(cross.loc['71','gateway_id']);entry=cat[gid]
        projected=np.array(tf.transform(entry['longitude'],entry['latitude']))
        mp=np.array(meta['71'],float)
        ck('BS71_identity_and_catalogue_projection',gid=='004A026B' and np.array_equal(np.round(projected,1),mp))
        rx71=np.flatnonzero(valid[:,70]&finitepos)
        working71=np.array([i for i in wr if valid[i,70]],int)
        cal71=np.array([i for i in cal if valid[i,70]],int)
        p71={'all_calibration':np.array(cal,int),'BS71_calibration_received':cal71,
             'BS71_working_received':working71,'BS71_all_CSV_received':rx71}
        distances=[];rows=[]
        for tag,ids in p71.items():
            v=np.linalg.norm(xy[ids]-mp,axis=1)
            distances.append({'population':tag,**stats(v),'distance_to_mean_position_m':float(np.linalg.norm(xy[ids].mean(0)-mp)),
                              'start_timestamp':str(d.iloc[ids]['RX Time'].min()),'end_timestamp':str(d.iloc[ids]['RX Time'].max())})
            for rank,i in enumerate(ids):
                rows.append({'population':tag,'rank0':rank,'csv_row_index0':int(i),'rx_time':str(d.iloc[i]['RX Time']),
                             'tx_x_m':float(x[i]),'tx_y_m':float(y[i]),'catalogue_distance_m':float(v[rank]),
                             'BS71_RSSI_dbm':float(rv[i,70]) if valid[i,70] else None})
        ck('BS71_reception_counts_match_crosswalk',len(rx71)==int(cross.loc['71','release_receptions']) and len(cal71)==int(cross.loc['71','calibration_receptions']))
        low=xy[cal].min(0);high=xy[cal].max(0)
        boxobs=box_diagnostic(mp,low,high)
        nearest_cal=[{'bs':b,'minimum_distance_to_any_calibration_position_m':float(np.linalg.norm(xy[cal]-np.array(meta[b]),axis=1).min())} for b in sorted(meta,key=int)]
        ck('BS71_scalar_receiver_distances',max(abs(math.hypot(x[i]-mp[0],y[i]-mp[1])-np.linalg.norm(xy[i]-mp)) for i in rx71)<COORD_TOL)
        bs_note={'bs':'71','gateway_id':gid,'catalogue_latitude':entry['latitude'],'catalogue_longitude':entry['longitude'],
            'metadata_rounded_xy_m':mp.tolist(),'projected_unrounded_xy_m':projected.tolist(),'CRS':'EPSG:32631',
            'populations':distances,'calibration_bounding_rectangle':{'xmin_m':float(low[0]),'xmax_m':float(high[0]),'ymin_m':float(low[1]),'ymax_m':float(high[1]),**boxobs},
            'interpretation':'Retrospective geometric description, not recovered historical flagging or proof of physical coordinate error. No coordinate repaired.'}
        dump(out/'BS71_description.json',bs_note)
        write_csv(out/'BS71_distance_summary.csv',pd.DataFrame(distances))
        write_csv(out/'BS71_source_rows_and_distances.csv.gz',pd.DataFrame(rows))
        write_csv(out/'metadata33_calibration_distance_context.csv',pd.DataFrame(nearest_cal))
        # Existing predictions: status-definition and exact raw-centroid shift check.
        preds=cf('results/benchmark/geometric_predictions.csv.gz')
        anomaly=cf('results/benchmark/anomaly_decomposition.csv')
        member('src/primary/code/validate.py')
        exclusions=[];change_records=[]
        for assignment in ['official','rssfit_stable']:
            bef=preds[(preds.experiment=='primary33')&(preds.assignment==assignment)].set_index('csv_row_index0')
            aft=preds[(preds.experiment=='no71')&(preds.assignment==assignment)].set_index('csv_row_index0')
            same=bef.loc[aft.index]
            non=~same.selected_receivers.str.split(';').map(lambda z:'71' in z)
            ep=np.abs(same.NLLS_error_m.to_numpy()-aft.NLLS_error_m.to_numpy())
            pp=np.linalg.norm(same[['NLLS_x','NLLS_y']].to_numpy()-aft[['NLLS_x','NLLS_y']].to_numpy(),axis=1)
            errcount=int(((ep>POSITION_TOL)&non.to_numpy()).sum());poscount=int(((pp>POSITION_TOL)&non.to_numpy()).sum())
            inherited=anomaly[(anomaly.assignment==assignment)&(anomaly.method=='NLLS')].iloc[0]
            ck(assignment+'_source_error_change_count',errcount==int(inherited.prediction_changed_on_non71_messages),{'count':errcount,'predicate':'absolute error difference >1e-7 m'})
            ck(assignment+'_no71_raw_WCL_invariant_without_reception',np.array_equal(same.loc[non,['WCL_raw_x','WCL_raw_y']],aft.loc[non,['WCL_raw_x','WCL_raw_y']]))
            exclusions.append({'assignment':assignment,'primary_n':len(bef),'survivor_n':len(aft),'lost_n':len(bef)-len(aft),
                'survivors_not_receiving_BS71':int(non.sum()),'NLLS_error_changed_non71':errcount,'NLLS_position_changed_non71':poscount,
                'predicate_disagreement_non71':int((((ep>POSITION_TOL)!=(pp>POSITION_TOL))&non.to_numpy()).sum()),
                'full_primary_WCL_median_m':float(bef.WCL_raw_error_m.median()),'before_survivor_WCL_median_m':float(same.WCL_raw_error_m.median()),
                'after_survivor_WCL_median_m':float(aft.WCL_raw_error_m.median())})
            for j,i in enumerate(aft.index):
                change_records.append({'assignment':assignment,'csv_row_index0':int(i),'did_not_receive_BS71':bool(non.iloc[j]),
                                       'NLLS_error_change_abs_m':float(ep[j]),'NLLS_position_change_m':float(pp[j])})
        write_csv(out/'BS71_existing_exclusion_summary.csv',pd.DataFrame(exclusions))
        write_csv(out/'BS71_existing_NLLS_change_records.csv.gz',pd.DataFrame(change_records))
        aa=preds[(preds.experiment=='primary33')&(preds.assignment=='official')].sort_values('sample_rank0').reset_index(drop=True)
        bb=preds[(preds.experiment=='primary33')&(preds.assignment=='rssfit_stable')].sort_values('sample_rank0').reset_index(drop=True)
        ck('primary_pairs_match_rows_and_selected_receptions',aa.csv_row_index0.equals(bb.csv_row_index0) and aa.selected_receivers.equals(bb.selected_receivers) and aa.raw_RSSI.equals(bb.raw_RSSI))
        shifts=[];max_shift=0.;max_position=0.
        for idx,(ra,rb) in enumerate(zip(aa.itertuples(),bb.itertuples())):
            ids=ra.selected_receivers.split(';');rss=np.array(ra.raw_RSSI.split(';'),float)
            sourcecols=[j for j in np.flatnonzero(valid[ra.csv_row_index0]) if str(j+1) in meta]
            sourcecols.sort(key=lambda j:-rv[ra.csv_row_index0,j]);sourcecols=sourcecols[:10]
            if ids!=[str(j+1) for j in sourcecols] or not np.array_equal(rss,rv[ra.csv_row_index0,sourcecols]):
                raise AssertionError('Selected receptions differ from the raw source.')
            weights=10.**((rss-rss.max())/10.);weights/=weights.sum()
            gm=np.array([meta[b] for b in ids]);gf=np.array([fit[b] for b in ids])
            shift=weights@(gf-gm);saved=np.array([rb.WCL_raw_x-ra.WCL_raw_x,rb.WCL_raw_y-ra.WCL_raw_y])
            shift_err=float(np.linalg.norm(shift-saved));max_shift=max(max_shift,shift_err)
            max_position=max(max_position,float(np.linalg.norm(weights@gm-[ra.WCL_raw_x,ra.WCL_raw_y])),float(np.linalg.norm(weights@gf-[rb.WCL_raw_x,rb.WCL_raw_y])))
            shifts.append({'csv_row_index0':int(ra.csv_row_index0),'weighted_coordinate_shift_x_m':float(shift[0]),'weighted_coordinate_shift_y_m':float(shift[1]),
                           'position_shift_m':float(np.linalg.norm(shift)),'weighted_discrepancy_bound_m':float(weights@np.linalg.norm(gf-gm,axis=1)),
                           'identity_residual_m':shift_err})
        ck('weighted_coordinate_shift_identity',max_shift<POSITION_TOL and max_position<POSITION_TOL,{'primary_n':len(aa),'max_shift_residual_m':max_shift,'max_position_residual_m':max_position})
        sh=pd.DataFrame(shifts)
        ck('weighted_shift_triangle_bound',bool((sh.position_shift_m<=sh.weighted_discrepancy_bound_m+POSITION_TOL).all()))
        write_csv(out/'primary_weighted_coordinate_shift.csv.gz',sh)
        dump(out/'primary_identity_summary.json',{'n':len(aa),'metadata_error_median_m':float(aa.WCL_raw_error_m.median()),'RSSFIT_error_median_m':float(bb.WCL_raw_error_m.median()),
             'ratio_of_medians':float(bb.WCL_raw_error_m.median()/aa.WCL_raw_error_m.median()),'RSSFIT_greater_error_count':int((bb.WCL_raw_error_m>aa.WCL_raw_error_m).sum()),
             'maximum_weighted_shift_identity_residual_m':max_shift,'maximum_independent_position_residual_m':max_position})
        density=cf('results/density/per_draw_summary.csv')
        rem=density[density.retained_receivers<33].copy()
        ck('complete_existing_density_draws',len(rem)==64 and len(rem[['retained_receivers','draw_index0']].drop_duplicates())==32 and rem.groupby(['retained_receivers','method']).size().eq(8).all())
        add_err=float(np.max(np.abs(rem.removal_component_m+rem.selection_component_m-rem.total_displayed_change_m)))
        ck('density_per_draw_accounting',add_err<POSITION_TOL,{'maximum_residual_m':add_err})
        write_csv(out/'existing_density_decomposition.csv',rem)
        ds=[]
        for (count,method),f in rem.groupby(['retained_receivers','method'],sort=True):
            ds.append({'receivers_retained':int(count),'method':method,'draws':len(f),'survivors_min':int(f.n.min()),'survivors_max':int(f.n.max()),
                       'removal_min_m':float(f.removal_component_m.min()),'removal_max_m':float(f.removal_component_m.max()),
                       'selection_min_m':float(f.selection_component_m.min()),'selection_max_m':float(f.selection_component_m.max())})
        write_csv(out/'density_component_ranges.csv',pd.DataFrame(ds))
        write_csv(out/'calibration_locations_for_plot.csv.gz',pd.DataFrame({'csv_row_index0':cal,'x_m':x[cal],'y_m':y[cal]}))
        dump(out/'INPUT_RECEIPT.json',{'CSV_payload_sha256':CSV_SHA,'F2_archive_sha256':None if a.f2.is_dir() else F2_SHA,'input_manifest_sha256':sha_file(r/'MANIFEST.json'),'F2_manifest_members_checked':len(manifest['files']),
                                     'consumed_F2_members':used,'script_sha256':sha_file(Path(__file__))})
        dump(out/'ENVIRONMENT.json',{'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'pyproj':pyproj.__version__,'PROJ':pyproj.proj_version_str,
                                    'scope':'Descriptive geometry, raw-data selection reconstruction, saved-output arithmetic. No coordinate or localization optimization.'})
        dump(out/'CHECKS.json',{'all_pass':True,'count':len(checks),'checks':checks,'new_localization_experiments':0,'coordinate_fits_executed':0})
        print(json.dumps({'coordinate_summary':description,'BS71':distances,'exclusion':exclusions,'checks':len(checks)},indent=2))


if __name__=='__main__':
    main()
