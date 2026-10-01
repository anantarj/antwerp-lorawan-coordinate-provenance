"""Constructed tests for the complete MV1 computation primitives; no real outcomes."""
from __future__ import annotations
import json, random, sys, unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
import mv1_core as m
from study_contract import pattern_search,prepare_observations,fit_box,loss_intercept
from source_reference import estimate_gateway_positions_rssfit,_robust_gateway_loss_and_a0


def fixture(n=220,seed=20):
    rng=np.random.default_rng(seed);xy=rng.normal(0,900,(n,2));g=np.array([100.,-700.])
    r=-30-47*np.log10(np.linalg.norm(xy-g,axis=1)+1)+rng.normal(0,3,n)
    return xy,r

class MV1Tests(unittest.TestCase):
    def test_01_instrumentation_matches_PR1(self):
        for n,seed in [(3,2),(50,8),(220,20),(300,41)]:
            xy,r=fixture(n,seed);lo,hi=fit_box(xy);s=m.initializer(xy,r)
            a=m.traced_search(xy,r,lo,hi,s);b=pattern_search(xy,r,lo,hi,s)
            np.testing.assert_array_equal(a['coordinate'],b['coordinate'])
            self.assertEqual(a['loss_db'],b['loss_db']);self.assertEqual(a['objective_calls'],b['objective_calls'])
            self.assertEqual(a['schedule'],b['schedule'])
    def test_02_source_fitter_multiple_sizes(self):
        for n,seed in [(20,1),(100,3),(200,8),(2200,12)]:
            xy,r=fixture(n,seed)
            messages=[SimpleNamespace(x=float(t[0]),y=float(t[1]),receptions=[SimpleNamespace(gid='1',rssi=float(v))]) for t,v in zip(xy,r)]
            ref,aa=estimate_gateway_positions_rssfit(messages,4.7,seed=1)
            kept,_=prepare_observations([(i,i,float(v)) for i,v in enumerate(r)],random.Random(1));idx=np.array([v[1] for v in kept])
            lo,hi=fit_box(xy[idx]);o=m.traced_search(xy[idx],r[idx],lo,hi,m.initializer(xy[idx],r[idx]))
            np.testing.assert_allclose(o['coordinate'],ref['1'],rtol=0,atol=1e-7)
            self.assertAlmostEqual(o['intercept_db'],aa['1'],places=9)
    def test_03_source_shared_rng_receiver_order(self):
        xy,r=fixture(2101,43)
        msgs=[SimpleNamespace(x=float(t[0]),y=float(t[1]),receptions=[SimpleNamespace(gid='7',rssi=float(v)),SimpleNamespace(gid='2',rssi=float(v-1))]) for t,v in zip(xy,r)]
        ref,_=estimate_gateway_positions_rssfit(msgs,4.7,seed=1);rng=random.Random(1)
        for bs,rr in [('7',r),('2',r-1)]:
            kept,_=prepare_observations([(i,i,float(v)) for i,v in enumerate(rr)],rng);idx=np.array([v[1] for v in kept]);lo,hi=fit_box(xy[idx])
            o=m.traced_search(xy[idx],rr[idx],lo,hi,m.initializer(xy[idx],rr[idx]))
            np.testing.assert_allclose(o['coordinate'],ref[bs],rtol=0,atol=1e-7)
    def test_04_source_objective_direct(self):
        xy,r=fixture(300,32)
        for g in [np.zeros(2),np.array([10000.,-4000.]),m.initializer(xy,r)]:
            np.testing.assert_allclose(loss_intercept(g,xy,r),_robust_gateway_loss_and_a0(g[0],g[1],xy,r,4.7),rtol=0,atol=1e-9)
    def test_05_complete_trace_and_budget(self):
        xy,r=fixture();lo,hi=fit_box(xy);o=m.traced_search(xy,r,lo,hi,m.initializer(xy,r))
        self.assertEqual(o['objective_calls'],len(o['trace']));self.assertEqual([t[0] for t in o['trace']],list(range(1,len(o['trace'])+1)))
        self.assertLessEqual(len(o['trace']),1921)
        selected=[t[6] for t in o['trace'] if t[-1]]
        self.assertTrue(all(b<a for a,b in zip(selected,selected[1:])))
        self.assertEqual(selected[-1],o['loss_db'])
    def test_06_clipped_candidates_count(self):
        xy,r=fixture(10);p=np.array([3.,4.]);o=m.traced_search(xy,r,p,p,[100,200],steps=[2000],max_sweeps=1)
        self.assertEqual(o['objective_calls'],9);self.assertEqual(sum(t[-1] for t in o['trace']),1)
        np.testing.assert_array_equal(o['coordinate'],p)
    def test_07_five_shared_starts_and_order(self):
        starts=m.scheduled_starts([40,30],[0,0],[100,200])
        np.testing.assert_array_equal(starts,np.array([[40,30],[25,50],[25,150],[75,50],[75,150]]))
    def test_08_selector_ties_first(self):
        self.assertEqual(m.select_start([{'loss_db':1,'validation':100},{'loss_db':1,'validation':0}]),0)
    def test_09_selector_only_training(self):
        self.assertEqual(m.select_start([{'loss_db':2,'validation':0},{'loss_db':1,'validation':100}]),1)
    def test_10_selector_rejects_nan(self):
        with self.assertRaises(ValueError):m.select_start([{'loss_db':float('nan')}])
    def test_11_validation_no_recentering(self):
        xy,r=fixture(50);g=np.array([4,9]);_,a=loss_intercept(g,xy,r)
        shift=m.predict(xy,g,a)+20;metrics=m.residual_metrics(shift,m.predict(xy,g,a))
        self.assertAlmostEqual(metrics['median_abs_db'],20);self.assertAlmostEqual(metrics['median_signed_db'],20)
        wrong,_=loss_intercept(g,xy,shift);self.assertAlmostEqual(wrong,0)
    def test_12_const_fitting_only(self):
        pred=m.predict(np.array([[0,0],[100,200],[2,6]]),None,-100)
        np.testing.assert_array_equal(pred,[-100]*3)
        self.assertEqual(m.residual_metrics(np.array([-80,-70,-60]),pred)['median_abs_db'],30)
    def test_13_empty_validation_explicit(self):
        d=m.residual_metrics(np.array([]),np.array([]));self.assertEqual(d['n'],0);self.assertIsNone(d['median_abs_db'])
    def test_14_profiles_exact_shape_and_bound(self):
        xy,r=fixture();lo,hi=fit_box(xy);s=m.initializer(xy,r);p=m.ray_profiles(xy,r,s,lo,hi)
        self.assertEqual(len(p),168);self.assertTrue(all(q['finite_bound_satisfied'] for q in p))
        for di in range(8):
            points=[q for q in p if q['direction_rank0']==di]
            np.testing.assert_allclose([points[0]['x'],points[0]['y']],s,rtol=0,atol=0)
            q=np.array([points[-1]['x'],points[-1]['y']]);self.assertLessEqual(min(abs(np.r_[q-lo,hi-q])),1e-7)
            self.assertTrue(np.all(q>=lo-1e-7) and np.all(q<=hi+1e-7))
    def test_15_profile_does_not_mutate(self):
        xy,r=fixture();lo,hi=fit_box(xy);x0=xy.copy();r0=r.copy();m.ray_profiles(xy,r,m.initializer(xy,r),lo,hi)
        np.testing.assert_array_equal(xy,x0);np.testing.assert_array_equal(r,r0)
    def test_16_receiver_missing_is_not_removed(self):
        g,missing=m.raw_wcl([1,2,71],[-80,-90,-95],{1:[0,0],2:[100,100]})
        self.assertIsNone(g);self.assertEqual(missing,[71])
    def test_17_const_has_no_coordinates(self):
        g,missing=m.raw_wcl([1,2],[-80,-90],{1:None,2:None})
        self.assertIsNone(g);self.assertEqual(missing,[1,2])
    def test_18_centroid_direct_agreement(self):
        g,_=m.raw_wcl([2,1,4],[-80,-90,-83],{1:[10,50],2:[-100,3],4:[9,60]})
        w=np.power(10.,np.array([-80,-90,-83])/10.);coords=np.array([[-100,3],[10,50],[9,60]])
        np.testing.assert_allclose(g,w@coords/w.sum(),rtol=0,atol=1e-10)
    def test_19_weight_shift_invariance(self):
        args=([1,2,3],np.array([-150.,-20.,-120.]),{1:[0,1],2:[100,100],3:[2,5]})
        a,_=m.raw_wcl(*args);b,_=m.raw_wcl(args[0],args[1]+10,args[2])
        np.testing.assert_allclose(a,b,rtol=0,atol=1e-10)
    def test_20_duplicate_receiver_refused(self):
        with self.assertRaises(ValueError):m.raw_wcl([1,1],[-80,-90],{1:[0,0]})
    def test_21_geometry_flags(self):
        d=m.geometry_fields([0,5],[15,5],[0,0],[10,10]);self.assertTrue(d['on_boundary']);self.assertTrue(d['catalogue_outside_domain'])
        self.assertEqual(d['catalogue_outside_distance_m'],5)
    def test_22_bad_shapes_and_finiteness(self):
        for args in [(np.zeros((2,3)),[1,2]),(np.zeros((1,2)),[np.nan])]:
            with self.assertRaises(ValueError):m.initializer(*args)
        with self.assertRaises(ValueError):m.traced_search([[0,0]],[1],[1,1],[0,0],[0,0])
    def test_23_native_multistart_zero_repeat(self):
        xy,r=fixture();lo,hi=fit_box(xy);s=m.initializer(xy,r)
        a=m.traced_search(xy,r,lo,hi,s);b=m.traced_search(xy,r,lo,hi,m.scheduled_starts(s,xy.min(0),xy.max(0))[0])
        self.assertEqual(a['trace'],b['trace'])
    def test_24_synthetic_end_to_end(self):
        models={};rng=np.random.default_rng(451)
        for bs in [1,2,3]:
            xy,r=fixture(150,bs);train=np.arange(100);val=np.arange(100,150)
            lo,hi=fit_box(xy[train]);s=m.initializer(xy[train],r[train]);o=m.traced_search(xy[train],r[train],lo,hi,s)
            pred=m.predict(xy[val],o['coordinate'],o['intercept_db']);q=m.residual_metrics(r[val],pred)
            self.assertEqual(q['n'],50);models[bs]=o['coordinate']
        g,missing=m.raw_wcl([3,1,2],[-80,-95,-87],models)
        self.assertTrue(np.isfinite(g).all());self.assertEqual(missing,[])
    def test_25_even_median_convention(self):
        self.assertEqual(m.residual_metrics([0,2,4,6],[0,0,0,0])['median_abs_db'],3)
        self.assertEqual(m.residual_metrics([0,2,4,6],[0,0,0,0])['p90_abs_db'],5.4)
    def test_26_profiles_wrong_origin_refused(self):
        xy,r=fixture(30);lo,hi=fit_box(xy)
        with self.assertRaises(ValueError):m.ray_profiles(xy,r,hi+100,lo,hi)

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(MV1Tests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    receipt={'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
             'passed':result.wasSuccessful(),'scope':'Constructed source, preprocessing, tracing, starts, fixed validation intercept, finite profile, missingness and centroid tests; no new real-data outcomes.'}
    Path(sys.argv[1]).write_text(json.dumps(receipt,indent=2)+'\n')
    sys.exit(0 if result.wasSuccessful() else 1)
