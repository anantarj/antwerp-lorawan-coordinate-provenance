import sys, unittest, numpy as np
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
from task_selection import ARMS, select_candidate,select_receptions,predict_wcl,components,summary

class Contracts(unittest.TestCase):
 def test_minimum(self):
  self.assertEqual(select_candidate(dict(zip(ARMS,[4.,3.,2.,1.]))),'WIDE_MS')
 def test_first_tie(self):
  self.assertEqual(select_candidate(dict(zip(ARMS,[1.,1.,1.,1.]))),'NARROW')
 def test_tolerance_tie(self):
  self.assertEqual(select_candidate(dict(zip(ARMS,[1.+1e-10,2.,1.,4.]))),'NARROW')
 def test_nonfinite_refused(self):
  with self.assertRaises(ValueError):select_candidate(dict(zip(ARMS,[1.,np.nan,3.,4.])))
 def test_candidate_omission_refused(self):
  with self.assertRaises(ValueError):select_candidate({'NARROW':1.})
 def test_no_catalogue_candidate(self):
  with self.assertRaises(ValueError):select_candidate({**dict(zip(ARMS,[1.,2.,3.,4.])),'CAT':0.})
 def test_stable_receiver_ties(self):
  r=np.full((1,72),-200.);r[0,[0,1,2]]=-90
  s,v,e=select_receptions(r,[1,2,3]);self.assertEqual(s.tolist(),[[1,2,3]]);self.assertTrue(e[0])
 def test_inclusive_rssi(self):
  r=np.full((1,72),-200.);r[0,:4]=[-150,-20,-100,-151]
  s,v,e=select_receptions(r,[1,2,3,4]);self.assertEqual(s.tolist(),[[2,3,1,-1]])
 def test_at_most_ten(self):
  r=np.full((1,72),-80.);s,v,e=select_receptions(r,list(range(1,34)))
  self.assertEqual(s.tolist(),[list(range(1,11))])
 def test_no_receiver_reselection(self):
  s=np.array([[1,2,3,4]]);v=np.array([[-40.,-50.,-60.,-70.]])
  g,c,m,w=predict_wcl(s,v,{1:[0,0],2:[1,0],3:[0,1]})
  self.assertFalse(c[0]);self.assertTrue(np.isnan(g[0]).all());self.assertEqual(m.tolist(),[[False,False,False,True]])
 def test_no_coordinate_fallback(self):
  g,c,m,w=predict_wcl(np.array([[1,2,3]]),np.full((1,3),-80.),{1:[0,0],2:None,3:[0,1]})
  self.assertFalse(c[0]);self.assertTrue(m[0,1])
 def test_invalid_map_refused(self):
  with self.assertRaises(ValueError):predict_wcl(np.array([[1,2,3]]),np.full((1,3),-80.),{1:[0,0],2:[np.nan,0],3:[0,1]})
 def test_exact_centroid(self):
  g,c,m,w=predict_wcl(np.array([[1,2,3]]),np.full((1,3),-80.),{1:[0,0],2:[3,0],3:[0,3]})
  np.testing.assert_allclose(g,[[1,1]],rtol=0,atol=1e-15)
 def test_padded_no_receiver(self):
  g,c,m,w=predict_wcl(np.array([[1,2,3,-1]]),np.array([[-80.,-80.,-80.,np.nan]]),{1:[0,0],2:[3,0],3:[0,3]})
  self.assertTrue(c[0]);np.testing.assert_allclose(g,[[1,1]])
 def test_insufficient_receptions(self):
  g,c,m,w=predict_wcl(np.array([[1,2,-1]]),np.array([[-80.,-80.,np.nan]]),{1:[0,0],2:[3,0]})
  self.assertFalse(c[0])
 def test_duplicate_receiver_refused(self):
  with self.assertRaises(ValueError):predict_wcl(np.array([[1,1,3]]),np.full((1,3),-80.),{1:[0,0],3:[0,1]})
 def test_transitive_group_closure(self):
  self.assertEqual(components([['a','a','b','c'],['x','y','y','z']],np.array([3,5,7,9])).tolist(),[3,3,3,9])
 def test_duplicate_source_ids_refused(self):
  with self.assertRaises(ValueError):components([['a','b']],np.array([3,3]))
 def test_zero_coverage_not_zero_error(self):
  with self.assertRaises(ValueError):summary(np.array([]))
 def test_opposite_evaluation_does_not_change_selection(self):
  # The selector has no test-score input. Reversing a separate test ranking
  # does not rewrite the already selected map.
  score=dict(zip(ARMS,[4.,3.,2.,1.]));selected=select_candidate(score)
  test1=dict(zip(ARMS,[1.,2.,3.,4.]));test2=dict(zip(ARMS,[4.,3.,2.,1.]))
  self.assertEqual(selected,'WIDE_MS');self.assertNotEqual(test1[selected],test2[selected])

if __name__=='__main__':unittest.main(verbosity=2)
