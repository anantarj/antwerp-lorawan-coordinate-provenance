import sys,unittest,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
import numpy as np
from common import *
class TestContract(unittest.TestCase):
 def test_quantile_exact_n19(self):self.assertEqual(conformal_quantile(np.arange(19),.05),(18.,19))
 def test_infinite_sparse(self):self.assertTrue(math.isinf(conformal_quantile(np.arange(115),.001)[0]))
 def test_zero_calibration(self):self.assertEqual(conformal_quantile([], .05),(math.inf,1))
 def test_ties(self):self.assertEqual(conformal_quantile([1]*100,.05)[0],1)
 def test_negative_correction(self):self.assertLess(conformal_quantile([-3]*100,.05)[0],0)
 def test_cvar_fractional(self):self.assertAlmostEqual(empirical_cvar(np.arange(11),.95),10)
 def test_cvar_ties(self):self.assertAlmostEqual(empirical_cvar([0,0,1,1],.5),1)
 def test_cvar_weight(self):self.assertAlmostEqual(empirical_cvar([0,1,2,3,4],.7),11/3)
 def test_reject_all(self):self.assertIsNone(decision_stats([1,2],[1,2],10,certified=[False,False])['conditional_accepted_failure'])
 def test_infinite_radius_refused(self):self.assertEqual(decision_stats([1],[math.inf],math.inf)['accepted'],0)
 def test_equality_inclusive(self):self.assertEqual(decision_stats([2],[2],2)['useful'],1)
 def test_subset_denominator(self):self.assertEqual(decision_stats([1],[1],2,total_requests=4)['accepted_fraction_requests'],.25)
 def test_bad_shape(self):
  with self.assertRaises(ValueError):decision_stats([1,2],[1],1)
 def test_bad_quantile(self):
  with self.assertRaises(ValueError):conformal_quantile([math.nan],.05)
 def test_signed_not_absolute(self):self.assertEqual(100-160,-60);self.assertEqual(100-abs(100-160),40)
 def test_identical_metric(self):self.assertEqual(great_circle_km((51,4),(51,4)),0)
 def test_known_package_example(self):self.assertAlmostEqual(great_circle_km((45.7597,4.8422),(48.8567,2.3508)),392.2172595594006,places=8)
 def test_independent_metric(self):
  y=np.array([[51,4],[50,3],[0,0]],float);p=y+.01
  e=np.array([great_circle_km(a,b)*1000 for a,b in zip(y,p)])
  np.testing.assert_allclose(e,coordinate_oracle(y,p,'lat_lon'),atol=1e-5,rtol=0)
 def test_invalid_metric(self):
  with self.assertRaises(ValueError):great_circle_km((100,0),(0,0))
 def test_joint_event(self):
  e=np.array([2,9,6,4]);u=np.array([3,8,4,5]);tau=5
  self.assertTrue(np.all(((u<=tau)&(e>tau)) <= (e>u)))
if __name__=='__main__':unittest.main(verbosity=2)
