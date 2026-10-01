#!/usr/bin/env python3
"""Check a finished PR2 package manifest and its local interpretation invariants.

No raw measurements or baseline tree are needed for this delivery check.
"""
import hashlib,json
from pathlib import Path

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
 r=Path(__file__).resolve().parents[1]
 d=json.loads((r/'MANIFEST.json').read_text())
 bad=[]
 for row in d['files']:
  p=r/row['path']
  if not p.is_file() or p.stat().st_size!=row['bytes'] or digest(p)!=row['sha256']:
   bad.append(row['path'])
 if bad:raise SystemExit('Manifest mismatch: '+str(bad))
 protocol=r/'evidence/pr1/protocol/MECHANISM_VALIDATION_PROTOCOL.json'
 assert digest(protocol)=='405bf282c73545fe8c00fbccbddcdd099cffdbc0bfb567f926e6cde98010973c'
 replay=json.loads((r/'results/representation_replay/REPLAY_RECEIPT.json').read_text())
 assert replay['rows_checked']==2495 and replay['max_cross_representation_position_delta_m']==0
 assert replay['source_files_unchanged'] is True
 direction=json.loads((r/'results/selection_directions/SELECTION_DIRECTION_RECEIPT.json').read_text())
 assert sum(x['draws'] for x in direction['method_summaries'])==64
 assert direction['total_sign_reversals']==8
 assert all(x['pass'] for x in json.loads((r/'results/raw_join/core/checks.json').read_text())['checks'])
 print('PASS',len(d['files']),'manifest entries; protocol and scoped numerical receipts agree')
 print('No new mechanism-validation fit is certified by this package check.')

if __name__=='__main__':main()
