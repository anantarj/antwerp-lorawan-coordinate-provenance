import sys,unittest,copy,json,inspect
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'code'))
from claim_contract import validate_dependencies,conventional_reference,audit_derived_quantities,FIELDS
class ContractTests(unittest.TestCase):
 def setUp(self):
  self.t={k:'pinned' for k in FIELDS};self.t['feature_schema']=['a','b'];self.t['ordered_row_handles']=['x:0','x:1']
 def test_clean(self):self.assertEqual(validate_dependencies(self.t,self.t)['violations'],[])
 def test_no_labels_argument(self):self.assertEqual(list(inspect.signature(validate_dependencies).parameters),['trusted','received'])
 def test_same_reference(self):self.assertEqual(validate_dependencies(self.t,self.t),conventional_reference(self.t,self.t))
 def test_missing(self):
  r=copy.deepcopy(self.t);r.pop('population');self.assertIn('received:missing:population',validate_dependencies(self.t,r)['violations'])
 def test_extra(self):
  r=copy.deepcopy(self.t);r['actual_error']=1;self.assertIn('received:unexpected:actual_error',validate_dependencies(self.t,r)['violations'])
 def test_row_order(self):
  r=copy.deepcopy(self.t);r['ordered_row_handles'].reverse();self.assertIn('ordered_row_handles:mismatch',validate_dependencies(self.t,r)['violations'])
 def test_duplicates(self):
  r=copy.deepcopy(self.t);r['ordered_row_handles']=['x:0','x:0'];self.assertTrue(validate_dependencies(self.t,r)['violations'])
 def test_empty_support(self):
  r=copy.deepcopy(self.t);r['ordered_row_handles']=[];self.assertTrue(validate_dependencies(self.t,r)['violations'])
 def test_binding_changes(self):
  for k in FIELDS:
   r=copy.deepcopy(self.t);r[k]=list(reversed(r[k])) if isinstance(r[k],list) else 'changed';self.assertTrue(validate_dependencies(self.t,r)['violations']);self.assertEqual(validate_dependencies(self.t,r),conventional_reference(self.t,r))
 def test_no_input_mutation(self):
  b=json.dumps(self.t,sort_keys=True);validate_dependencies(self.t,self.t);self.assertEqual(b,json.dumps(self.t,sort_keys=True))
 def test_unknown_formula_not_detected(self):self.assertEqual(validate_dependencies(self.t,self.t)['state'],'equivalent_continuation')
 def test_correct_signed(self):self.assertEqual(audit_derived_quantities([100],[160],[-60])['mismatched_records'],0)
 def test_wrong_signed(self):self.assertEqual(audit_derived_quantities([100],[160],[40])['mismatched_records'],1)
 def test_bad_lengths(self):
  with self.assertRaises(ValueError):audit_derived_quantities([1],[1,2],[0])
 def test_nonfinite(self):
  with self.assertRaises(ValueError):audit_derived_quantities([float('nan')],[1],[0])
 def test_tolerance(self):
  self.assertEqual(audit_derived_quantities([1.],[1.],[1e-9])['mismatched_records'],0)
if __name__=='__main__':unittest.main(verbosity=2)
