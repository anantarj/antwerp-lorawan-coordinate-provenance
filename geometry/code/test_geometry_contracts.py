#!/usr/bin/env python3
"""Constructed tests of F3 reporting contracts; not scientific replications."""
import unittest
import math
import numpy as np
from describe_frozen_geometry import box_diagnostic, stats, POSITION_TOL

class ReportingContracts(unittest.TestCase):
    def test_interior_point(self):
        d=box_diagnostic(np.array([3.,4.]),np.array([0.,0.]),np.array([10.,10.]))
        self.assertFalse(d['outside']);self.assertFalse(d['on_boundary'])
        self.assertEqual(d['minimum_signed_margin_m'],3.)
    def test_every_side_and_corner(self):
        for p in [[0,4],[10,4],[4,0],[4,10],[0,0],[10,10]]:
            with self.subTest(point=p):
                d=box_diagnostic(p,[0,0],[10,10]);self.assertTrue(d['on_boundary']);self.assertFalse(d['outside'])
    def test_exterior_corner_distance(self):
        d=box_diagnostic([-3,-4],[0,0],[10,10])
        self.assertEqual(d['distance_to_closed_box_m'],5.);self.assertTrue(d['outside']);self.assertFalse(d['on_boundary'])
    def test_tolerance_is_explicit(self):
        inside_tolerance=box_diagnostic([-0.5*POSITION_TOL,4],[0,0],[10,10])
        outside_tolerance=box_diagnostic([-2*POSITION_TOL,4],[0,0],[10,10])
        self.assertFalse(inside_tolerance['outside']);self.assertTrue(outside_tolerance['outside'])
    def test_near_threshold_not_failure(self):
        self.assertTrue(box_diagnostic([60.,200.],[0,0],[1000,1000])['within_60m_of_boundary'])
        self.assertFalse(box_diagnostic([60.1,200.],[0,0],[1000,1000])['within_60m_of_boundary'])
    def test_invalid_rectangle_and_nonfinite_rejected(self):
        for point,lo,hi in [([1,1],[10,0],[0,10]),([math.nan,1],[0,0],[10,10])]:
            with self.assertRaises(ValueError):box_diagnostic(point,lo,hi)
    def test_fixed_roster_percentile_convention(self):
        d=stats(np.array([0.,10.,20.,30.]));self.assertEqual(d['median_m'],15.);self.assertEqual(d['p90_m'],27.)
    def test_empty_and_nonfinite_distances_rejected(self):
        for v in [[],[1.,math.nan]]:
            with self.assertRaises(ValueError):stats(np.array(v))
    def test_raw_centroid_shift_identity_and_offset_invariance(self):
        meta=np.array([[0.,0.],[10.,20.],[20.,0.]])
        fit=meta+np.array([[3.,4.],[2.,-6.],[-8.,9.]])
        raw=np.array([-60.,-70.,-65.]);w=10**((raw-raw.max())/10);w/=w.sum()
        np.testing.assert_allclose(w@fit-w@meta,w@(fit-meta),rtol=0,atol=1e-12)
        rw=raw+8;w2=10**((rw-rw.max())/10);w2/=w2.sum()
        np.testing.assert_allclose(w2@fit,w@fit,rtol=0,atol=1e-12)
    def test_changed_coordinates_do_not_require_greater_error(self):
        meta=np.array([[3.,0.],[5.,0.],[4.,0.]]);fit=meta-np.array([4.,0.]);w=np.full(3,1/3);target=np.zeros(2)
        self.assertGreater(np.linalg.norm(w@meta-target),np.linalg.norm(w@fit-target))
    def test_radius_convention_is_one_metre(self):
        distance=1000.;q=-47*math.log10(distance+1)
        self.assertAlmostEqual(10**(-q/47)-distance,1.,places=9)
    def test_draw_accounting_and_nonadditive_marginal_medians(self):
        removal=np.array([0.,0.,100.]);selection=np.array([0.,100.,0.])
        total=removal+selection
        self.assertNotEqual(float(np.median(total)),float(np.median(removal)+np.median(selection)))

if __name__=='__main__':unittest.main(verbosity=2)
