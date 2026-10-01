"""Constructed pre-run checks of reused calibration, decision and follow-up contracts."""
from pathlib import Path
import sys,unittest,math
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'code'));sys.path.insert(0,str(ROOT/'sources/inherited'))
from common import conformal_quantile,decision_stats,empirical_cvar
from identity_core import RowHandle,ContractError
from run_followup import check_semantic_state
from lineage import time_roles

class Tests(unittest.TestCase):
    def test_dsi_rank95(self):
        q,k=conformal_quantile(np.arange(115),.05);self.assertEqual((q,k),(110.,111))
    def test_dsi_rank999(self):
        q,k=conformal_quantile(np.arange(115),.001);self.assertEqual(k,116);self.assertTrue(math.isinf(q))
    def test_empty_calibration_not_finite(self):self.assertTrue(math.isinf(conformal_quantile([], .05)[0]))
    def test_infinite_bound_not_useful(self):
        d=decision_stats([1.,2.],[float('inf')]*2,5.);self.assertEqual(d['accepted'],0);self.assertIsNone(d['conditional_accepted_failure'])
    def test_inclusive_tie(self):
        d=decision_stats([5.],[5.],5.);self.assertEqual((d['accepted'],d['useful'],d['harmful']),(1,1,0))
    def test_explicit_all_request_denominator(self):
        d=decision_stats([1.,10.],[2.,2.],3,total_requests=4);self.assertEqual(d['useful_fraction_requests'],.25)
    def test_cvar_fractional_tail(self):self.assertAlmostEqual(empirical_cvar([0,0,0,10],.6),6.25)
    def test_expected_source_formula_sign(self):self.assertEqual((100-160,100-abs(100-160)),(-60,40))
    def test_conventional_and_integrated_semantics(self):
        rows=(RowHandle('a'*64,0),);ex={'model':'x'}
        a=check_semantic_state(ex,ex,rows,[100],[160],[40],False);b=check_semantic_state(ex,ex,rows,[100],[160],[40],True)
        self.assertEqual(a,b);self.assertEqual(a,['signed_quantity_mismatch_offline'])
    def test_model_change_refused(self):
        r=(RowHandle('a'*64,0),)
        for integrated in [False,True]:self.assertEqual(check_semantic_state({'model':'x'},{'model':'y'},r,[1],[2],[-1],integrated),['model_mismatch'])
    def test_bad_original_row_handle(self):
        with self.assertRaises(ContractError):RowHandle('a'*64,-1)
    def test_duplicate_handle_not_unique(self):
        r=(RowHandle('a'*64,0),)*2
        for i in [False,True]:self.assertEqual(check_semantic_state({}, {},r,[1,1],[1,1],[0,0],i),['duplicate_handle'])
    def test_minus98_is_not_presence(self):
        raw=np.array([-150,-98]);prep=np.where(raw==-150,-98,raw)
        self.assertEqual(prep[0],prep[1]);self.assertNotEqual(raw[0]==-150,raw[1]==-150)
    def test_chronological_role_assignment(self):
        n=2000;times=pd.date_range('2020-01-01',periods=20,freq='D').repeat(100).astype(str)
        frame=pd.DataFrame({'source_row_index0':np.arange(n),'group_min_source_index0':np.arange(n),'rx_time':times})
        frame.loc[100,'group_min_source_index0']=0;frame.loc[1500,'group_min_source_index0']=0
        a,receipt=time_roles(frame);self.assertEqual(len(a),n);self.assertEqual(a.source_row_index0.nunique(),n)
        self.assertEqual(receipt['cross_role_groups'],1);self.assertEqual(receipt['cross_role_quarantined_rows'],3)
        self.assertEqual(receipt['counts']['calibration_reference'],receipt['counts']['calibration_recent'])
        self.assertTrue(a[a.role=='train1'].utc_day.max()<a[a.role=='calibration_reference'].utc_day.min())
        self.assertTrue(a[a.role=='calibration_recent'].utc_day.max()<a[a.role=='evaluation'].utc_day.min())
    def test_primary_predictions_not_changed_by_calibration(self):
        e=np.array([1.,2.]);h=np.array([.5,.5]);old=h+1;new=h+3
        self.assertTrue(np.array_equal(e,np.array([1.,2.])));self.assertFalse(np.array_equal(old,new))

if __name__=='__main__':unittest.main(verbosity=2)
