"""G01-G12: fixed conformance transformations and independent exact oracles."""
from __future__ import annotations
import copy
import hashlib
import inspect
import itertools
import json
from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'code'))
from identity_core import *
from adapters import antwerp_frames,synthetic_explicit,exact_integer
from sidecars import registry_sidecar,verify_partition
F=json.loads((ROOT/'fixtures/BASE_FIXTURE.json').read_text())


def fixture():
    p=[];s=[]
    for i,vals in enumerate(F['values']):
        signals={c:{'present':v is not None,'value':v} for c,v in zip(F['channels'],vals)}
        p.append({'source_index':i,'event_key':f'event/{i}','signals':signals})
        s.append({'source_index':i,'event_key':f'event/{i}',
                  'readings':[{'sensor':F['truth'][c],'token':v} for c,v in zip(F['channels'],vals) if v is not None]})
    return p,[s[i] for i in F['secondary_view_order']]


def canonical():
    p,s=fixture()
    return synthetic_explicit(p,s,F['channels'],F['primary_sha256'],F['secondary_sha256'])


def oracle(a: Alignment, recovery=None):
    """Scalar tuple equality, independent of production hashing and vector equality."""
    p,s=a.primary,a.secondary
    rows=range(len(p.rows)) if recovery is None else recovery
    rows=list(rows);out={}
    for j,c in enumerate(p.features):
        sig=tuple((bool(p.present[i,j]),int(p.values[i,j])) for i in rows)
        if not any(seen for seen,_ in sig):out[c]=[];continue
        matches=[]
        for k,g in enumerate(s.features):
            alt=tuple((bool(s.present[a.secondary_indices[i],k]),int(s.values[a.secondary_indices[i],k])) for i in rows)
            if sig==alt:matches.append(g)
        out[c]=sorted(matches)
    return out


def exhaustive_maps(a: Alignment):
    p,s=a.primary,a.secondary
    active=[i for i in range(len(p.features)) if p.present[:,i].any()]
    solutions=[]
    for perm in itertools.permutations(range(len(s.features)),len(active)):
        if all(all((bool(p.present[r,c]),int(p.values[r,c]))==
                   (bool(s.present[a.secondary_indices[r],k]),int(s.values[a.secondary_indices[r],k]))
                   for r in range(len(p.rows))) for c,k in zip(active,perm)):
            solutions.append({p.features[c]:s.features[k] for c,k in zip(active,perm)})
    return solutions


def view(o,ri=None,ci=None):
    ri=list(range(len(o.rows))) if ri is None else ri
    ci=list(range(len(o.features))) if ci is None else ci
    return Observations(tuple(o.rows[i] for i in ri),tuple(o.keys[i] for i in ri),tuple(o.features[i] for i in ci),
                        o.values[np.ix_(ri,ci)],o.present[np.ix_(ri,ci)])


class Conformance(unittest.TestCase):
    def test_G01_two_schema_exact_match(self):
        p,s=fixture();obs=synthetic_explicit(p,s,F['channels'],F['primary_sha256'],F['secondary_sha256'])
        a=reconcile(*obs);r=associate(a);self.assertEqual(r['mapping'],F['truth'])
        self.assertEqual({r['feature']:r['candidates'] for r in r['features']},oracle(a))
        self.assertEqual(exhaustive_maps(a),[F['truth']])
        data=[];msgs=[]
        for i,row in enumerate(F['values']):
            data.append({**{f'BS {j+1}':(-200 if x is None else x) for j,x in enumerate(row)},'RX Time':str(i),'SF':7,'HDOP':.6,'Longitude':10,'Latitude':20})
            msgs.append({'sf':7,'hdop':.6,'longitude':10,'latitude':20,'gateways':[
                {'id':F['truth'][c],'rssi':v,'rx_time':{'time':str(i)}} for c,v in zip(F['channels'],row) if v is not None]})
        a2=reconcile(*antwerp_frames(pd.DataFrame(data),[msgs[i] for i in F['secondary_view_order']],F['primary_sha256'],F['secondary_sha256']))
        got=associate(a2)['mapping']
        self.assertEqual({F['channels'][int(k.split()[-1])-1]:v for k,v in got.items()},r['mapping'])

    def test_G02_independent_views_and_partition(self):
        p,s=canonical();a=reconcile(view(p,[4,0,3,1,2]),view(s,[3,2,0,4,1]))
        self.assertEqual(associate(a)['mapping'],F['truth'])
        wanted=tuple(p.rows[i] for i in F['partition_order']);indices=positions_for_handles(a.primary,wanted)
        self.assertEqual(tuple(a.primary.rows[i] for i in indices),wanted)
        original=reconcile(p,s)
        self.assertEqual({h:original.secondary.rows[j] for h,j in zip(p.rows,original.secondary_indices)},
                         {h:a.secondary.rows[j] for h,j in zip(a.primary.rows,a.secondary_indices)})

    def test_G02_missing_lineage_refused(self):
        p,s=canonical()
        with self.assertRaises(ContractError):positions_for_handles(p,[RowHandle('c'*64,1)])
        with self.assertRaises(ContractError):Observations(tuple(range(5)),p.keys,p.features,p.values,p.present)

    def test_G03_feature_permutation_and_rename(self):
        p,s=canonical();p=view(p,ci=[3,2,0,1]);s=view(s,ci=[2,0,1])
        rename={g:'00renamed/'+g for g in s.features}
        s=Observations(s.rows,s.keys,tuple(rename[g] for g in s.features),s.values,s.present)
        self.assertEqual(associate(reconcile(p,s))['mapping'],{k:rename[v] for k,v in F['truth'].items()})
        self.assertEqual(p.features,('inactive','load','thermal','flow'))

    def test_G04_duplicates_preserved(self):
        p,s=fixture();dup=copy.deepcopy(p[0]);dup['source_index']=8;p.append(dup)
        j=next(x for x in s if x['source_index']==0);dup=copy.deepcopy(j);dup['source_index']=9;s.append(dup)
        a=reconcile(*synthetic_explicit(p,s,F['channels'],F['primary_sha256'],F['secondary_sha256']))
        self.assertEqual(len(a.primary.rows),6);self.assertEqual(a.duplicate_group_count,1)
        self.assertEqual(associate(a)['mapping'],F['truth']);self.assertTrue(a.complete_occurrence_equivalence)
        self.assertEqual(a.group_sizes[0],2);self.assertEqual(a.group_sizes[-1],2)

    def test_G05_ambiguity_full_class_and_inactive(self):
        p,s=canonical();t=Observations(s.rows,s.keys,s.features+('other',),np.column_stack([s.values,s.values[:,0]]),np.column_stack([s.present,s.present[:,0]]))
        a=reconcile(p,t);result=associate(a)
        ambiguous=next(r for r in result['features'] if r['feature']=='load')
        self.assertEqual(ambiguous['status'],'ambiguous');self.assertEqual(ambiguous['candidates'],['0008','other'])
        self.assertFalse(result['all_supported_uniquely_resolved'])
        self.assertEqual(next(r for r in result['features'] if r['feature']=='inactive')['status'],'unsupported')
        self.assertEqual(len(exhaustive_maps(a)),2)

    def test_G05_recovery_subset_does_not_borrow_rows(self):
        h=tuple(RowHandle('a'*64,i) for i in range(2));j=tuple(RowHandle('b'*64,i) for i in range(2))
        p=Observations(h,('a','b'),('x','y'),np.array([[1,1],[2,3]],dtype='int64'),np.ones((2,2),bool))
        s=Observations(j,('a','b'),('00x','00y'),p.values,p.present);a=reconcile(p,s)
        r=associate(a,[h[0]]);self.assertTrue(all(x['status']=='ambiguous' for x in r['features']))
        self.assertEqual(associate(a)['mapping'],{'x':'00x','y':'00y'})
        self.assertFalse(associate(a,[])['all_supported_uniquely_resolved'])

    def test_G06_missing_event_refused(self):
        p,s=canonical()
        with self.assertRaisesRegex(ContractError,'insufficient_secondary'):reconcile(p,view(s,[0,1,2,3]))

    def test_G06_multiplicity_refused(self):
        p,s=fixture();r=copy.deepcopy(p[0]);r['source_index']=8;p.append(r)
        with self.assertRaisesRegex(ContractError,'insufficient_secondary'):reconcile(*synthetic_explicit(p,s,F['channels'],F['primary_sha256'],F['secondary_sha256']))

    def test_G06_conflicting_duplicate_maps_refused(self):
        p,s=fixture();r=copy.deepcopy(s[0]);r['source_index']=8;r['readings'][0]['token']+=1;s.append(r)
        with self.assertRaisesRegex(ContractError,'conflicting_secondary'):reconcile(*synthetic_explicit(p,s,F['channels'],F['primary_sha256'],F['secondary_sha256']))

    def test_G06_many_to_one_not_certified(self):
        p,s=canonical();p=Observations(p.rows,p.keys,p.features+('duplicate',),np.column_stack([p.values,p.values[:,0]]),np.column_stack([p.present,p.present[:,0]]))
        r=associate(reconcile(p,s));self.assertFalse(r['all_supported_uniquely_resolved'])
        self.assertEqual([x['status'] for x in r['features'] if x['feature'] in ('thermal','duplicate')],['noninjective','noninjective'])

    def test_G07_surplus_reported_not_added(self):
        p,s=fixture();r=copy.deepcopy(s[0]);r['source_index']=9;r['event_key']='surplus';s.append(r)
        a=reconcile(*synthetic_explicit(p,s,F['channels'],F['primary_sha256'],F['secondary_sha256']))
        self.assertEqual(len(a.primary.rows),5);self.assertEqual(len(a.surplus_rows),1)
        self.assertFalse(a.complete_occurrence_equivalence);self.assertTrue(associate(a)['all_supported_uniquely_resolved'])

    def test_G08_registry_does_not_select_identity(self):
        p,s=canonical();r=associate(reconcile(p,s));before=json.dumps(r,sort_keys=True)
        a=registry_sidecar(r,{'sensor:Q':{'x':1,'y':2}},['x','y'])
        b=registry_sidecar(r,{'sensor:Q':{'x':999999,'y':-1}},['x','y'])
        self.assertEqual(json.dumps(r,sort_keys=True),before)
        self.assertNotEqual(a[0]['attributes'],b[0]['attributes'])
        self.assertFalse(next(x for x in a if x['feature']=='load')['metadata_available'])

    def test_G09_value_contradiction_and_forced_hash_collision(self):
        p,s=canonical();v=s.values.copy();v[0,0]+=3
        s=Observations(s.rows,s.keys,s.features,v,s.present);a=reconcile(p,s)
        r=associate(a,digest=lambda b:'constant')
        self.assertNotIn('load',r['mapping']);self.assertFalse(r['all_supported_uniquely_resolved'])
        self.assertEqual({x['feature']:x['candidates'] for x in r['features']},oracle(a))

    def test_G09_presence_contradiction(self):
        p,s=canonical();v=s.values.copy();m=s.present.copy();v[0,0]=0;m[0,0]=False
        r=associate(reconcile(p,Observations(s.rows,s.keys,s.features,v,m)))
        self.assertNotIn('load',r['mapping'])

    def test_G10_present_zero_is_not_absence(self):
        p,s=fixture();p[0]['signals']['thermal']['value']=0
        j=next(e for e in s if e['source_index']==0)
        next(g for g in j['readings'] if g['sensor']=='sensor:Q')['token']=0
        a=reconcile(*synthetic_explicit(p,s,F['channels'],F['primary_sha256'],F['secondary_sha256']))
        self.assertTrue(a.primary.present[0,0]);self.assertEqual(a.primary.values[0,0],0)
        self.assertEqual(associate(a)['mapping'],F['truth'])

    def test_G10_reject_lossy_numeric_tokens(self):
        for v in (float('nan'),float('inf'),1.25,2**63,2**54*1.0,True,'12'):
            with self.subTest(v=v),self.assertRaises(ContractError):exact_integer(v)

    def test_G10_antwerp_reject_nonintegral_overflow(self):
        base={'BS 1':-80,'RX Time':'T','SF':7,'HDOP':.5}
        j=[{'sf':7,'hdop':.5,'gateways':[{'id':'001','rssi':-80,'rx_time':{'time':'T'}}]}]
        for v in (-80.5,float('nan'),65536,-201):
            with self.subTest(v=v),self.assertRaises(ContractError):antwerp_frames(pd.DataFrame([{**base,'BS 1':v}]),j,'a'*64,'b'*64)

    def test_G10_duplicate_identifier_in_event(self):
        p,s=fixture();s[0]['readings'].append(copy.deepcopy(s[0]['readings'][0]))
        with self.assertRaisesRegex(ContractError,'duplicate_gateway'):synthetic_explicit(p,s,F['channels'],'a'*64,'b'*64)

    def test_G10_identifier_zero_prefix_and_no_coercion(self):
        p,s=fixture();self.assertIn('0008',associate(reconcile(*canonical()))['mapping'].values())
        s[0]['readings'][0]['sensor']=8
        with self.assertRaises(ContractError):synthetic_explicit(p,s,F['channels'],'a'*64,'b'*64)

    def test_G10_invalid_presence_and_duplicate_handle(self):
        p,s=fixture();p[0]['signals']['thermal']['present']=1
        with self.assertRaises(ContractError):synthetic_explicit(p,s,F['channels'],'a'*64,'b'*64)
        p,s=canonical()
        with self.assertRaises(ContractError):Observations((p.rows[0],)+p.rows[:-1],p.keys,p.features,p.values,p.present)

    def test_G11_outcomes_excluded(self):
        p,s=fixture();a=associate(reconcile(*synthetic_explicit(p,s,F['channels'],'a'*64,'b'*64)))
        for r in p:r.update({'target':99999,'geometry':[-1,1],'error':0})
        for r in s:r.update({'target':-99999,'geometry':[0,0],'error':9})
        b=associate(reconcile(*synthetic_explicit(p,s,F['channels'],'a'*64,'b'*64)))
        self.assertEqual(a,b)
        self.assertEqual(tuple(inspect.signature(associate).parameters),('alignment','recovery_rows','digest'))
        source=(ROOT/'code/identity_core.py').read_text()
        for value in ('55375','130429','FF0107C9','BS71','metadata33'):self.assertNotIn(value,source)

    def test_G11_invalid_recovery_handles_refused(self):
        p,s=canonical();a=reconcile(p,s)
        for rows in ([p.rows[0],p.rows[0]],[RowHandle('c'*64,0)]):
            with self.assertRaises(ContractError):associate(a,rows)

    def test_G12_inputs_immutable_and_repeat(self):
        p,s=canonical();before=hashlib.sha256(p.values.tobytes()+p.present.tobytes()).hexdigest()
        r=associate(reconcile(p,s));r2=associate(reconcile(p,s));self.assertEqual(r,r2)
        self.assertEqual(hashlib.sha256(p.values.tobytes()+p.present.tobytes()).hexdigest(),before)
        with self.assertRaises(ValueError):p.values[0,0]=999

    def test_G12_sidecar_corruption_detected(self):
        sha='a'*64;rows=[RowHandle(sha,0),RowHandle(sha,2)]
        x=np.array([[1,2],[3,4],[5,6]]);y=np.array([[7],[8],[9]]);hd=np.array([[1],[2],[3]])
        verify_partition(rows,sha,x,y,hd,x[[0,2]],y[[0,2]],hd[[0,2]])
        with self.assertRaises(ContractError):verify_partition(rows[::-1],sha,x,y,hd,x[[0,2]],y[[0,2]],hd[[0,2]])


if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Conformance)
    tests=[t.id() for t in suite]
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    report={'scope':'Constructed software conformance cases, not independent datasets',
            'tests_run':result.testsRun,'tests':tests,'failures':[{'test':t.id(),'trace':s} for t,s in result.failures+result.errors],
            'status':'PASS' if result.wasSuccessful() else 'FAIL'}
    if len(sys.argv)>1:Path(sys.argv[1]).write_text(json.dumps(report,indent=2)+'\n')
    raise SystemExit(not result.wasSuccessful())
