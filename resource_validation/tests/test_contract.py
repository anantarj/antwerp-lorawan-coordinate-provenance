"""Constructed contract tests. None uses real follow-up outcome data."""
from __future__ import annotations
import ast,json,os,random,sys,unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
from study_contract import *

class ContractTests(unittest.TestCase):
    def test_01_duplicate_transitive_union(self):
        self.assertEqual(components([['a','a','c'],['x','y','y']],[10,20,30]),[10,10,10])
    def test_02_serialization_duplicates_cannot_separate(self):
        g=components([['c1','c2','c3'],['a','a','b']],[5,7,9])
        self.assertEqual(g[0],g[1]);self.assertNotEqual(g[0],g[2])
    def test_03_spatial_cell_union(self):
        self.assertEqual(components([['a','b','c'],['1:1','1:1','2:2']],[9,4,8]),[4,4,8])
    def test_04_group_order_invariance(self):
        r=[17,12,19]; k=[['a','a','b'],['x','y','z']]; g=components(k,r)
        order=[2,0,1];h=components([[v[i] for i in order] for v in k],[r[i] for i in order])
        self.assertEqual(dict(zip(r,g)),dict(zip([r[i] for i in order],h)))
    def test_05_role_determinism(self):
        self.assertEqual(sha_role('123','seed|'),sha_role('123','seed|'))
        self.assertIn(sha_role('123','seed|'),['fitting','validation'])
    def test_06_bad_group_lengths_refused(self):
        with self.assertRaises(ValueError):components([['a']],[1,2])
    def test_07_random_generator_not_consumed_without_subsample(self):
        rng=random.Random(1);before=rng.getstate()
        prepare_observations([(i,i,-100.0) for i in range(20)],rng)
        self.assertEqual(before,rng.getstate())
    def test_08_random_generator_consumed_with_subsample(self):
        rng=random.Random(1);before=rng.getstate()
        prepare_observations([(i,i,-100.0) for i in range(2001)],rng)
        self.assertNotEqual(before,rng.getstate())
    def test_09_strong_filter_fallback(self):
        out,info=prepare_observations([(i,i,float(-150+i)) for i in range(100)],random.Random(1))
        self.assertFalse(info['strong_filter_used']);self.assertEqual(len(out),100)
    def test_10_strong_filter_on_fitting_only(self):
        records=[(i,i,float(-140+i/4)) for i in range(200)]
        out,info=prepare_observations(records,random.Random(1))
        self.assertTrue(info['strong_filter_used']);self.assertEqual(len(out),50)
        self.assertEqual([r[0] for r in out],list(range(150,200)))
    def test_11_domain_nesting(self):
        allxy=np.array([[0,0],[100,200],[300,-400],[9,9]])
        lo,hi=fit_box(allxy[[0,3]]);wl,wh=fit_box(allxy)
        self.assertTrue(np.all(wl<=lo) and np.all(hi<=wh))
    def test_12_validation_coordinates_do_not_define_box(self):
        fit=np.array([[0,0],[1,1]])
        before=fit_box(fit); validation=np.array([[1e9,1e9]])
        after=fit_box(fit)
        np.testing.assert_array_equal(before[0],after[0]);np.testing.assert_array_equal(before[1],after[1])
    def test_13_validation_intercept_not_refitted(self):
        xy=np.array([[10,0],[0,20],[20,20]],float);g=np.zeros(2);a=-30.
        train=a-47*np.log10(np.linalg.norm(xy-g,axis=1)+1)
        val=train+20
        self.assertAlmostEqual(validation_loss(g,a,xy,val),20)
        recentered,_=loss_intercept(g,xy,val)
        self.assertAlmostEqual(recentered,0)
        self.assertGreater(validation_loss(g,a,xy,val)-recentered,19.9)
    def test_14_constant_uses_fitting_median(self):
        self.assertEqual(constant_loss(np.array([-100,-90,-80]),np.array([-80,-70,-60])),20)
    def test_15_finite_bound_random_constructed(self):
        rng=np.random.default_rng(1709)
        for n in [3,4,9,20,31,50]:
            for _ in range(15):
                xy=rng.normal(0,100,(n,2));r=rng.normal(-100,5,n);g=rng.normal(0,300,2)
                loss,_=loss_intercept(g,xy,r);mad=float(np.median(np.abs(r-np.median(r))))
                self.assertLessEqual(abs(loss-mad),flatness_bound(g,xy)+1e-9)
    def test_16_far_distance_limit_fixture(self):
        xy=np.array([[0,0],[10,0],[0,10],[5,5]],float);r=np.array([-100,-103,-97,-98.])
        g=np.array([1e9,1e9]);loss,_=loss_intercept(g,xy,r);mad=np.median(abs(r-np.median(r)))
        self.assertLess(abs(loss-mad),1e-6)
    def test_17_common_rssi_shift_invariance(self):
        xy=np.array([[0,0],[10,0],[0,10]],float);r=np.array([-100,-101,-98.]);g=np.array([2,3])
        l,a=loss_intercept(g,xy,r);l2,a2=loss_intercept(g,xy,r+17)
        self.assertAlmostEqual(l,l2);self.assertAlmostEqual(a2-a,17)
    def test_18_bad_scoring_inputs_refused(self):
        with self.assertRaises(ValueError):loss_intercept([0,0],np.empty((0,2)),np.empty(0))
        with self.assertRaises(ValueError):validation_loss([0,0],float('nan'),np.zeros((2,2)),np.zeros(2))
    def test_19_median_intercept_not_exact_minimizer(self):
        y=np.array([0,1,2,100,101])
        self.assertEqual(np.median(abs(y-np.median(y))),2)
        self.assertEqual(np.median(abs(y-1)),1)
    def test_20_native_source_agreement_constructed(self):
        p=Path(os.environ['PA_SOURCE_EVALUATOR'])
        source=p.read_text();tree=ast.parse(source)
        names={'estimate_gateway_positions_rssfit','_robust_gateway_loss_and_a0'}
        bodies=[ast.get_source_segment(source,n) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
        self.assertEqual(len(bodies),2)
        namespace={'np':np,'random':random}
        exec(compile('from __future__ import annotations\n'+'\n\n'.join(bodies),str(p),'exec'),namespace)
        rng=np.random.default_rng(11)
        xy=rng.normal(0,1000,(220,2));g=np.array([400,-300]);r=-30-47*np.log10(np.linalg.norm(xy-g,axis=1)+1)+rng.normal(0,3,220)
        messages=[SimpleNamespace(x=float(t[0]),y=float(t[1]),receptions=[SimpleNamespace(gid='1',rssi=float(v))]) for t,v in zip(xy,r)]
        actual,aintercept=namespace['estimate_gateway_positions_rssfit'](messages,4.7,seed=1)
        kept,_=prepare_observations([(i,i,float(v)) for i,v in enumerate(r)],random.Random(1))
        ix=[v[1] for v in kept];lo,hi=fit_box(xy[ix]);copy=pattern_search(xy[ix],r[ix],lo,hi)
        np.testing.assert_allclose(copy['coordinate'],actual['1'],rtol=0,atol=1e-7)
        self.assertAlmostEqual(copy['intercept_db'],aintercept['1'],places=9)
        self.assertLessEqual(copy['objective_calls'],1921)
        for point in [g,copy['coordinate'],np.zeros(2)]:
            ref=namespace['_robust_gateway_loss_and_a0'](point[0],point[1],xy,r,4.7)
            np.testing.assert_allclose(loss_intercept(point,xy,r),ref,rtol=0,atol=1e-9)
    def test_21_search_incumbent_never_worsens(self):
        xy=np.array([[0,0],[50,0],[0,50],[25,25]],float);r=np.array([-80,-85,-81,-83.])
        lo,hi=fit_box(xy);out=pattern_search(xy,r,lo,hi)
        losses=[v['loss_db'] for v in out['accepted']]
        self.assertTrue(all(b<a for a,b in zip(losses,losses[1:])))
        self.assertTrue(np.all(out['coordinate']>=lo) and np.all(out['coordinate']<=hi))

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(ContractTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    receipt={'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'passed':result.wasSuccessful(),'scope':'Constructed grouping, preprocessing, frozen-intercept, finite-bound and source-fitter fixtures; no real follow-up fitted or validation outcomes.'}
    target=Path(sys.argv[1]) if len(sys.argv)>1 else Path('SYNTHETIC_TEST_RECEIPT.json')
    target.write_text(json.dumps(receipt,indent=2)+'\n')
    sys.exit(0 if result.wasSuccessful() else 1)
