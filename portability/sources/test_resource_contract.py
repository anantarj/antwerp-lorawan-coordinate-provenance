"""Constructed misuse tests, not new Antwerp scientific experiments."""
from pathlib import Path
import sys,unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
from resource_contract import *

class Contracts(unittest.TestCase):
    def test_equal_count_wrong_order_rejected(self):
        with self.assertRaises(ValueError): require_rows([4,2,3],[2,3,4])
    def test_different_members_same_count_rejected(self):
        with self.assertRaises(ValueError): require_rows([2,3,7],[2,3,4])
    def test_duplicate_row_ids_rejected(self):
        with self.assertRaises(ValueError): require_rows([2,2,3],[2,2,3])
    def test_exact_order_accepted(self): require_rows([7,4,2],[7,4,2])
    def test_wrong_source_hash_rejected(self):
        with self.assertRaises(ValueError): require_source('wrong','expected')
    def test_insufficient_json_multiplicity_rejected(self):
        with self.assertRaises(ValueError): require_multiplicity(['a','a'],['a'])
    def test_surplus_json_not_automatically_appended(self):
        require_multiplicity(['a','a'],['a','a','b'])
    def test_conflicting_group_receptions_rejected(self):
        with self.assertRaises(ValueError): require_same_group_maps([{'00ABC':-90},{'00ABC':-91}])
    def test_identical_duplicate_receptions_accepted(self):
        require_same_group_maps([{'00ABC':-90},{'00ABC':-90}])
    def test_nonbijective_receiver_link_rejected(self):
        with self.assertRaises(ValueError): require_unique_linkage({'1':'00ABC','2':'00ABC'})
    def test_leading_zeros_preserved(self):
        m={'1':'00ABC','2':'00002'};require_unique_linkage(m);self.assertEqual(m['2'],'00002')
    def test_numeric_BS_tie_rule(self):
        self.assertEqual(select_receptions({'10':-90,'2':-90,'1':-91},{'1','2','10'}),[('2',-90.),('10',-90.),('1',-91.)])
    def test_missing_coordinates_rejected(self):
        with self.assertRaises(ValueError): centroid([('1',-80),('2',-90)],{'1':[1.,2.]})
    def test_nonfinite_coordinate_rejected(self):
        with self.assertRaises(ValueError): centroid([('1',-80)],{'1':[float('nan'),2.]})
    def test_hand_computed_centroid(self):
        np.testing.assert_allclose(centroid([('1',-80),('2',-80)],{'1':[0,0],'2':[10,20]}),[5,10])
    def test_RSSI_global_offset_invariance(self):
        c={'1':[0,0],'2':[10,20]}
        np.testing.assert_allclose(centroid([('1',-80),('2',-90)],c),centroid([('1',-70),('2',-80)],c),atol=1e-13)

if __name__=='__main__': unittest.main(verbosity=2)
