from pathlib import Path
import datetime, hashlib, json
r=Path(__file__).resolve().parent
p={
 'id':'PA-PR4-TASK-SELECT-20260920','version':'1.0',
 'scope':'Retrospective constructive proof of work using unchanged PR3 fitted maps. New task-validation and complementary-cohort scoring; no new coordinate fit.',
 'known_before_design':['All Stage 1/2/3 reports and their original 2495-case downstream outcomes','Grouped/spatial RSSI validation summaries and all candidate map definitions'],
 'not_yet_computed_here':['Localization errors of the four maps on their fitting-held-out calibration messages','Errors on the duplicate-disjoint complement defined below'],
 'candidate_order':['NARROW','WIDE','NARROW_MS','WIDE_MS'],
 'splits':['group80','space1000'],
 'selection':{
  'unit':'one entire map per split; not per-receiver or per-evaluation-message switching',
  'TASK_VAL':'minimize median raw-WCL positional error on common-complete validation messages from the original calibration split',
  'TRAIN_RSSI':'minimize unweighted receiver median of retained-fitting objective values over fit-supported primary receivers',
  'VAL_RSSI_EQUAL':'minimize unweighted receiver median of validation median absolute RSSI prediction errors over common fit-and-validation-supported receivers',
  'VAL_RSSI_POOLED':'minimize pooled validation-reception median absolute RSSI prediction error over the same receiver support',
  'NATIVE_FIXED':'use NARROW, irrespective of scores',
  'tie_rule':'earliest candidate in fixed order among scores at most minimum+1e-9 in that metric units',
  'forbidden':['No use of old or new evaluation errors to choose a map','No catalogue coordinate added to the fitted-map candidate set','No RSSI re-filtering/intercept refitting on validation','No switch after seeing results','No altered candidate coordinates']},
 'validation_message_contract':{'parents':'exact PR1 fitting-held-out calibration rows for the corresponding split',
  'receiver_roster':'unchanged metadata33 roster',
  'valid_rssi':'finite inclusive [-150,-20] dBm',
  'selection':'stable descending raw RSSI with ascending numeric BS tie order, at most ten; minimum three in the original roster',
  'missing':'keep original selected list; no missing-coordinate imputation or reselection; report all requested rows and compare maps only on identical common-complete rows'},
 'evaluation':{
  'old_primary':'unchanged 2495-request PR3 cohort; descriptive reuse only',
  'complement':'all original 55375 working rows in CSV order, excluding every transitive component of equal legacy content key OR equal serialization key that touches the original 16612 calibration rows OR original 2495 primary rows. No random subsampling.',
  'complement_is_not':'not an independent dataset; not certified untouched in earlier development; not spatially isolated from training; larger N does not imply independent observations',
  'same_selection_contract':True,'same_coordinate_maps':True,
  'CAT_reference':'catalogue raw WCL on both its own valid-request population and the exact common-complete population; not a surveyed truth certificate'},
 'record':['all row identities/group keys/exclusion reasons','all candidate/role predictions including unsupported rows','requested/eligible/common-complete counts','validation choices frozen to disk before computing new complementary-cohort errors','median/mean/p90 error and matched difference and ratio of medians','all five selection policies and every candidate outcome','scalar vs vector raw-WCL cross-checks','complete failure and mixed outcome reporting'],
 'interpretation':{
 'constructive_support':'TASK_VAL improving evaluation loss over proxy-selected map is a bounded mitigation among these four fixed candidates, not a new optimizer or universal remedy.',
 'negative':'a tie, worse error, split-dependent benefit, or proxy policy beating task selection must remain reported.',
 'novelty':'validation-based selection, exact cohort pairing, null controls and source provenance are established ideas. Contribution must be the precise resource and demonstrated release-specific capability, not invented general priority.',
 'statistics':'descriptive deterministic comparisons on named cohorts only; no significance/acceptance probability or population generalization',
 'calibration_cost':'TASK_VAL uses held-out transmitter coordinates and validation receptions, already supplied by this benchmark; not label-free or implementable without such positions.'},
 'parents':{'PR1':'46bc701eb4ad5cf929a1bec1ba79ce9c8c34e14ee32472251cf14d885d1a1559','PR2':'5f763a45bd0ba46dba9786595681521370922ccfdc7b459dbbd344498118e7f0','PR3':'3ed84201715a0ffc3e4781aa22fe94c4ad0914a02bddcdd55460b6901c74b089a4'},
 'raw_csv_sha256':'870abe60a4bd81f31ede6f269b6bc6329e05d2731343dff7015bae1a61218446',
 'S1_zip_sha256':'97a98dd8cc0f1ba6638b62a546563178bb98ce86c5ff1bc53fce2512c64cdb43',
 'MV1_protocol_sha256':'405bf282c73545fe8c00fbccbddcdd099cffdbc0bfb567f926e6cde98010973c'
}
# Correct hash transcribed from the actual preserved PR3 archive before any experiment.
p['parents']['PR3']='3ed84201715a0ffc3e4781aa22fe94c4ad0914a02bddc55460b6901c74b089a4'
b=(json.dumps(p,indent=2,sort_keys=True)+'\n').encode();(r/'TASK_SELECTION_PROTOCOL.json').write_bytes(b)
(r/'PROTOCOL_LOCK.json').write_text(json.dumps({'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sha256':hashlib.sha256(b).hexdigest(),'scope':'locked before new task-validation/complement scoring; design informed by known PR3 results, not external preregistration'},indent=2)+'\n')
print(hashlib.sha256(b).hexdigest())
