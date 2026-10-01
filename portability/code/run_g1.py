#!/usr/bin/env python3
"""G13 frozen parity and G14 differential DAE preparation; no fitting or training.
New output directories only. Raw data are staged temporarily, not redistributed.
"""
from __future__ import annotations
import argparse,gzip,hashlib,io,json,os,platform,resource,shutil,subprocess,sys,tempfile,time,zipfile
from contextlib import contextmanager
from pathlib import Path
import numpy as np
import pandas as pd
import sklearn
from sklearn.model_selection import train_test_split
from pyproj import Transformer
from identity_core import ContractError,RowHandle,reconcile,associate
from adapters import load_antwerp,file_hash
from sidecars import registry_sidecar,verify_partition
ROOT=Path(__file__).resolve().parents[1]
EXPECTED={'csv':'870abe60a4bd81f31ede6f269b6bc6329e05d2731343dff7015bae1a61218446',
 'json':'f2f1fbd478cdef2b76fb8e3aae33751d332b50fc8546684d8e73fdb1505451cb',
 'catalogue':'507f9bb266d23f59fdc2b743447cecf9c909290536e24de3f9483aaa178d374d',
 'notebook':'b3137875da89a4bb5f50426f505772d03d5e2e78d37781802abc263f2a36ef4c',
 'baseline':'97a98dd8cc0f1ba6638b62a546563178bb98ce86c5ff1bc53fce2512c64cdb43'}
def dump(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n')
def frame_csv(frame,path):
    if str(path).endswith('.gz'):
        with path.open('wb') as f,gzip.GzipFile(fileobj=f,mode='wb',filename='',mtime=0) as g:
            frame.to_csv(io.TextIOWrapper(g,encoding='utf-8',newline=''),index=False)
    else:frame.to_csv(path,index=False)
@contextmanager
def raw_file(path,kind,work):
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            names=[n for n in z.namelist() if not n.endswith('/') and '__MACOSX' not in Path(n).parts and not Path(n).name.startswith('._')]
            if len(names)!=1:raise ContractError('ambiguous_raw_payload',names)
            dest=work/f'input.{kind}'
            with z.open(names[0]) as f,dest.open('wb') as out:shutil.copyfileobj(f,out)
    else:dest=path
    if file_hash(dest)!=EXPECTED[kind]:raise ContractError('payload_hash_differs',kind)
    yield dest

def safe_extract(z,root):
    for info in z.infolist():
        if not (root/info.filename).resolve().is_relative_to(root.resolve()):raise ContractError('archive_traversal',info.filename)
    z.extractall(root)
def check_gate():
    gate=json.loads((ROOT/'checks/EXECUTION_GATE.json').read_text())
    for f in gate['files']:
        if file_hash(ROOT/f['path'])!=f['sha256']:raise ContractError('execution_gate_mismatch',f['path'])
    return file_hash(ROOT/'checks/EXECUTION_GATE.json')

def execute(args):
    out=args.out.resolve()
    if out.exists():raise ContractError('occupied_output',str(out))
    gate_sha=check_gate();before={k:file_hash(getattr(args,k)) for k in ('csv','json','catalogue','notebook','baseline')}
    for k in ('catalogue','notebook','baseline'):
        if before[k]!=EXPECTED[k]:raise ContractError('input_hash_differs',k)
    out.mkdir(parents=True);started=time.perf_counter();checks=[]
    def check(name,condition,detail=None):
        checks.append({'name':name,'passed':bool(condition),'detail':detail})
        if not condition:dump(out/'FAILED_CHECKS.json',checks);raise AssertionError(name)
    with tempfile.TemporaryDirectory(prefix='paper_a_g1_') as tmp:
        work=Path(tmp)
        with raw_file(args.csv,'csv',work) as pc,raw_file(args.json,'json',work) as pj:
            p,s=load_antwerp(pc,pj);alignment=reconcile(p,s);all_result=associate(alignment)
            with zipfile.ZipFile(args.baseline) as z:
                prefix='Computational_Supplement_Anonymous/'
                cal=pd.read_csv(io.BytesIO(z.read(prefix+'computational/populations/calibration_rows.csv'))).sort_values('rank0')
                cal_handles=[RowHandle(EXPECTED['csv'],int(i)) for i in cal.csv_row_index0]
                cal_result=associate(alignment,cal_handles)
                # All inference above precedes loading frozen identity answers.
                saved_full=json.loads(z.read(prefix+'computational/results/join/rebuilt_full_identities.json'))
                saved_cal=json.loads(z.read(prefix+'computational/results/join/rebuilt_calibration_identities.json'))
                saved_alignment=pd.read_csv(io.BytesIO(z.read(prefix+'computational/results/join/alignment.csv.gz')),compression='gzip')
                saved_surplus=json.loads(z.read(prefix+'computational/results/join/surplus_json_records.json'))
                meta=json.loads(z.read(prefix+'computational/data_products/metadata33.json'))
                check('frozen_full_mapping',{str(int(k.split()[-1])):v for k,v in all_result['mapping'].items()}==saved_full)
                check('frozen_calibration_mapping',{str(int(k.split()[-1])):v for k,v in cal_result['mapping'].items()}==saved_cal)
                check('all_full_supported_resolved',all_result['all_supported_uniquely_resolved'])
                check('all_cal_supported_resolved',cal_result['all_supported_uniquely_resolved'])
                check('source_order_and_row_count',[h.source_row_index0 for h in p.rows]==saved_alignment.csv_row_index0.tolist())
                check('exact_occurrence_representatives',np.array_equal(alignment.secondary_indices,saved_alignment.json_index0_occurrence_representative.to_numpy()))
                check('exact_occurrence_multiplicity',list(alignment.group_sizes)==saved_alignment.group_multiplicity.tolist())
                check('surplus_identity',[h.source_row_index0 for h in alignment.surplus_rows]==[q['json_index0'] for q in saved_surplus])
                safe_extract(z,work/'baseline')
            parity=out/'antwerp';parity.mkdir()
            dump(parity/'associations_full.json',all_result);dump(parity/'associations_calibration.json',cal_result)
            frame_csv(pd.DataFrame({'csv_payload_sha256':EXPECTED['csv'],'csv_row_index0':[h.source_row_index0 for h in p.rows],
                'json_payload_sha256':EXPECTED['json'],'json_index0_occurrence_representative':[s.rows[i].source_row_index0 for i in alignment.secondary_indices],
                'group_multiplicity':alignment.group_sizes}),parity/'occurrence_reconciliation.csv.gz')
            dump(parity/'surplus.json',[{'payload_sha256':h.payload_sha256,'source_row_index0':h.source_row_index0} for h in alignment.surplus_rows])
            catalogue=json.loads(args.catalogue.read_text());metadata=registry_sidecar(all_result,catalogue,['latitude','longitude'])
            dump(parity/'registry_sidecar.json',metadata);check('catalogue_availability',sum(x['metadata_available'] for x in metadata)==39)
            tf=Transformer.from_crs(4326,32631,always_xy=True);projected={}
            for row in metadata:
                if row['metadata_available']:
                    g=row['attributes'];x,y=tf.transform(g['longitude'],g['latitude']);projected[str(int(row['feature'].split()[-1]))]=[round(float(x),1),round(float(y),1)]
            check('primary_projection_unchanged',all(projected[b]==coord for b,coord in meta.items()))
            holdout=np.array(sorted(set(range(len(p.rows)))-set(cal.csv_row_index0.astype(int))),dtype=np.int64)
            colidx={c:i for i,c in enumerate(p.features)};ididx={g:i for i,g in enumerate(s.features)};mismatch={}
            for c,g in cal_result['mapping'].items():
                x=colidx[c];y=ididx[g];sj=alignment.secondary_indices[holdout]
                mismatch[c]=int(np.count_nonzero((p.values[holdout,x]!=s.values[sj,y])|(p.present[holdout,x]!=s.present[sj,y])))
            check('calibration_links_outside_calibration',all(n==0 for n in mismatch.values()));dump(parity/'outside_calibration_mismatches.json',mismatch)
            reader_join=parity/'reader_join';reader_join.mkdir()
            dump(reader_join/'rebuilt_full_identities.json',{str(int(c.split()[-1])):g for c,g in all_result['mapping'].items()})
            dump(reader_join/'rebuilt_catalogue_all39.json',projected)
            frame_csv(pd.DataFrame({'csv_row_index0':list(range(len(p.rows))),'json_index0_occurrence_representative':alignment.secondary_indices,'group_multiplicity':alignment.group_sizes}),reader_join/'alignment.csv.gz')
            done=subprocess.run([sys.executable,str(ROOT/'sources/compare_representations.py'),'--baseline',str(work/'baseline'/prefix),
                '--join',str(reader_join),'--csv',str(pc),'--json',str(pj),'--out',str(parity/'frozen_reader_replay')],capture_output=True,text=True)
            (parity/'reader_stdout.txt').write_text(done.stdout);(parity/'reader_stderr.txt').write_text(done.stderr)
            check('unchanged_PR2_reader_exit',done.returncode==0,done.stderr[-2000:])
            replay=json.loads((parity/'frozen_reader_replay/REPLAY_RECEIPT.json').read_text())
            check('cross_representation_tolerance',replay['max_cross_representation_position_delta_m']<=1e-10)
            check('saved_prediction_tolerance',replay['max_saved_position_delta_m']<=1e-7)
            done=subprocess.run([sys.executable,str(ROOT/'sources/rebuild_join.py'),'--csv',str(pc),'--json',str(pj),'--out',str(parity/'original_reference')],capture_output=True,text=True)
            (parity/'original_stdout.txt').write_text(done.stdout);(parity/'original_stderr.txt').write_text(done.stderr)
            check('unchanged_original_join_exit',done.returncode==0,done.stderr[-2000:])
            check('new_core_vs_original_join_full',json.loads((parity/'original_reference/rebuilt_full_identities.json').read_text())==saved_full)
            check('new_core_vs_original_join_cal',json.loads((parity/'original_reference/rebuilt_calibration_identities.json').read_text())==saved_cal)
            oldalign=pd.read_csv(parity/'original_reference/alignment.csv.gz');check('new_core_vs_original_alignment',np.array_equal(oldalign.json_index0_occurrence_representative,alignment.secondary_indices))
            dump(parity/'PARITY_RECEIPT.json',{'status':'PASS','primary_rows':len(p.rows),'secondary_rows':len(s.rows),'feature_columns':len(p.features),
                'unique_full':len(all_result['mapping']),'inactive_full':sum(r['status']=='unsupported' for r in all_result['features']),
                'unique_calibration':len(cal_result['mapping']),'calibration_rows':len(cal_handles),'duplicate_groups':alignment.duplicate_group_count,
                'surplus_count':len(alignment.surplus_rows),'catalogue_available':sum(r['metadata_available'] for r in metadata),
                'catalogue_missing_active':sum(r['identifier'] is not None and not r['metadata_available'] for r in metadata),
                'replay_rows':replay['rows_checked'],'max_CSV_JSON_displacement_m':replay['max_cross_representation_position_delta_m'],
                'max_saved_displacement_m':replay['max_saved_position_delta_m'],'raw_WCL_median_m':replay['metadata_median_error_m'],
                'original_source_reexecuted':True,'saved_mapping_is_inference_input':False})
            # Reference executes unmodified source in its own output sandbox.
            dae=out/'dae';dae.mkdir();ref=work/'dae_reference';(ref/'files/lorawan').mkdir(parents=True)
            shutil.copyfile(pc,ref/'files/lorawan/lorawan_dataset_antwerp.csv');shutil.copyfile(args.catalogue,ref/'files/lorawan/lorawan_antwerp_gateway_locations.json')
            os.chmod(ref/'files/lorawan/lorawan_dataset_antwerp.csv',0o444);os.chmod(ref/'files/lorawan/lorawan_antwerp_gateway_locations.json',0o444)
            done=subprocess.run([sys.executable,str(ROOT/'code/reference_dae.py'),'--notebook',str(args.notebook.resolve()),'--work',str(ref)],capture_output=True,text=True)
            (dae/'reference_stdout.txt').write_text(done.stdout);(dae/'reference_stderr.txt').write_text(done.stderr)
            check('DAE_original_source_exit',done.returncode==0,done.stderr[-2000:])
            ref_order=np.load(ref/'reference_row_orders.npz')
            # Integrated branch reproduces the recipe, never inserts source-ID columns.
            source=pd.read_csv(pc);cols=source.columns;counts=72-(source[cols[:72]]==-200).astype(int).sum(axis=1)
            data=source.drop([i for i,n in enumerate(counts.tolist()) if n<3]);x=data[data.columns[:72]];y=data[data.columns[75:]];hd=np.expand_dims(data['HDOP'],axis=1)
            xt,xvtemp,yt,yvtemp=train_test_split(x.values,y.values,test_size=.3,random_state=42)
            xv,xe,yv,ye=train_test_split(xvtemp,yvtemp,test_size=.5,random_state=42)
            ht,hvtemp,_,_=train_test_split(hd,hd,test_size=.3,random_state=42);hv,he,_,_=train_test_split(hvtemp,hvtemp,test_size=.5,random_state=42)
            it,ivtemp=train_test_split(data.index.to_numpy(),test_size=.3,random_state=42);iv,ie=train_test_split(ivtemp,test_size=.5,random_state=42)
            variants={'train':(xt,yt,ht,it),'val':(xv,yv,hv,iv),'test':(xe,ye,he,ie)}
            target_columns=y.columns.tolist();feature_columns=x.columns.tolist()
            reference_dir=dae/'reference_exports';reference_dir.mkdir();integrated_dir=dae/'integrated_exports';integrated_dir.mkdir();side_dir=dae/'sidecars';side_dir.mkdir();exports=[];parts=[]
            full_x=source[source.columns[:72]].to_numpy();full_y=source[source.columns[75:]].to_numpy();full_h=np.expand_dims(source.HDOP,axis=1)
            for role,(xa,ya,ha,idx) in variants.items():
                check('DAE_independent_order_'+role,np.array_equal(idx,ref_order[role]))
                handles=[RowHandle(EXPECTED['csv'],int(i)) for i in idx]
                verify_partition(handles,EXPECTED['csv'],full_x,full_y,full_h,xa,ya,ha,[RowHandle(EXPECTED['csv'],int(i)) for i in ref_order[role]])
                check('DAE_source_rowwise_values_'+role,True)
                frame_csv(pd.DataFrame({'partition':role,'partition_rank0':np.arange(len(idx)),'source_payload_sha256':EXPECTED['csv'],
                    'source_row_index0':idx,'serialization_group_multiplicity':[alignment.group_sizes[int(i)] for i in idx]}),side_dir/(role+'_row_handles.csv.gz'))
                parts.append({'partition':role,'n':len(idx),'original_row_order_sha256':hashlib.sha256(np.asarray(idx,dtype='<i8').tobytes()).hexdigest()})
                for prefix,arr,names in [('x',xa,feature_columns),('y',ya,target_columns),('HDOP',ha,['HDOP'])]:
                    name=f'{prefix}_{role}.csv';new=integrated_dir/name;old=reference_dir/name
                    pd.DataFrame(arr,columns=names).to_csv(new,index=False);shutil.copyfile(ref/'files'/name,old)
                    a=pd.read_csv(old);b=pd.read_csv(new);byte_equal=file_hash(old)==file_hash(new)
                    value_equal=a.columns.tolist()==b.columns.tolist() and a.shape==b.shape and np.array_equal(a.to_numpy(),b.to_numpy(),equal_nan=True)
                    check('DAE_export_bytes_'+name,byte_equal);check('DAE_export_values_'+name,value_equal)
                    check('DAE_absence_locations_'+name,np.array_equal(a.to_numpy()==-200,b.to_numpy()==-200))
                    exports.append({'file':name,'shape':list(a.shape),'headers':a.columns.tolist(),'sha256_reference':file_hash(old),
                        'sha256_integrated':file_hash(new),'bytes_equal':byte_equal,'values_equal':value_equal})
            side_lookup={r['feature']:r for r in metadata};feature_rows=[{'feature_rank0':i,**side_lookup[c]} for i,c in enumerate(feature_columns)]
            dump(side_dir/'feature_metadata.json',feature_rows)
            check('DAE_72_features_preserved',len(feature_rows)==72 and [r['feature'] for r in feature_rows]==feature_columns)
            check('DAE_partitions_disjoint',len(set(map(int,np.concatenate([it,iv,ie]))))==len(data))
            check('DAE_partition_union_source_order',np.array_equal(np.sort(np.concatenate([it,iv,ie])),data.index.to_numpy()))
            bad=it.copy();j=next(k for k in range(1,len(it)) if not np.array_equal(full_x[it[0]],full_x[it[k]]) or not np.array_equal(full_y[it[0]],full_y[it[k]]))
            bad[0],bad[j]=bad[j],bad[0];reason=None
            try:verify_partition([RowHandle(EXPECTED['csv'],int(i)) for i in bad],EXPECTED['csv'],full_x,full_y,full_h,xt,yt,ht)
            except ContractError as e:reason=e.code
            check('DAE_negative_sidecar_refused',reason=='partition_values_misaligned',reason)
            dump(dae/'NEGATIVE_CONTROL.json',{'operation':'Swap two distinct source-row handles in a copy only','positions':[0,j],
                'original_source_rows':[int(it[0]),int(it[j])],'refusal_code':reason,'original_exports_untouched':True})
            frame_csv(pd.DataFrame(exports),dae/'EXPORT_COMPARISON.csv')
            dump(dae/'INTEGRATION_RECEIPT.json',{'status':'PASS','source_notebook_sha256':EXPECTED['notebook'],'raw_csv_sha256':EXPECTED['csv'],
                'retained_rows':len(data),'partitions':parts,'feature_columns':feature_columns,'target_columns':target_columns,'hdop_columns':['HDOP'],
                'all_nine_export_bytes_equal':all(x['bytes_equal'] for x in exports),'all_nine_export_values_equal':all(x['values_equal'] for x in exports),
                'source_order_reconstructed_independently':True,'sidecar_negative_control':reason,'metadata_feature_count':len(feature_rows),
                'inactive_feature_count':sum(x['association_status']=='unsupported' for x in feature_rows),'located_feature_count':sum(x['metadata_available'] for x in feature_rows),
                'unlocated_active_feature_count':sum(x['identifier'] is not None and not x['metadata_available'] for x in feature_rows),
                'original_DAE_preparation_recipe_preserved':True,'fitted_or_trained_models':0,
                'scope':'Two current executions of separately authored preparation code on one dataset; no historical export authentication, independent adoption, predictor reproduction or duplicate-free split claim'})
            check('reference_staged_csv_unchanged',file_hash(ref/'files/lorawan/lorawan_dataset_antwerp.csv')==EXPECTED['csv'])
            check('reference_staged_catalogue_unchanged',file_hash(ref/'files/lorawan/lorawan_antwerp_gateway_locations.json')==EXPECTED['catalogue'])
    after={k:file_hash(getattr(args,k)) for k in before};check('all_inputs_unchanged',before==after);check('execution_code_gate_unchanged',check_gate()==gate_sha)
    dump(out/'VERIFICATION.json',{'status':'PASS','checks':checks,'checks_count':len(checks),
        'scope':'G13 correspondence/frozen-reader parity and G14 unchanged-versus-integrated DAE preparation. No fitting or predictive-model training.'})
    dump(out/'EXECUTION.json',{'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'scikit_learn':sklearn.__version__,
        'execution_gate_sha256':gate_sha,'inputs':before,'wall_seconds':time.perf_counter()-started,
        'peak_self_rss_platform_units':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'peak_child_rss_platform_units':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        'RSS_units':'KiB on this Linux host; not simultaneous process-tree peak','performance_scope':'Descriptive single-environment execution metadata, not a speed/memory comparison'})
    print(json.dumps({'status':'PASS','checks':len(checks),'out':str(out)},indent=2))
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for key in ('csv','json','catalogue','notebook','baseline','out'):ap.add_argument('--'+key,type=Path,required=True)
    execute(ap.parse_args())
if __name__=='__main__':main()
