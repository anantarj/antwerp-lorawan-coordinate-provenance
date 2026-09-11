#!/usr/bin/env python3
"""Compare deterministic scientific/identity outputs, excluding runtime metadata."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--other',type=Path,required=True);a=ap.parse_args();records=[]
    for sub in ['prepared','benchmark','temporal','inference']:
        for p in sorted((ROOT/'results'/sub).iterdir()):
            if p.name=='execution.json' or not p.is_file():continue
            rel=p.relative_to(ROOT);q=a.other/rel
            if p.suffix=='.npz' and q.exists():
                with np.load(p) as x,np.load(q) as y:
                    equal=set(x.files)==set(y.files) and all(np.array_equal(x[k],y[k]) for k in x.files)
                mode='exact_array_content'
            else:equal=q.exists() and sha(p)==sha(q);mode='SHA256_byte_identity'
            records.append({'file':str(rel),'comparison':mode,'identical':bool(equal),'archived_sha256':sha(p),'rerun_sha256':sha(q) if q.exists() else None})
    p=ROOT/'tests/validation_results.json';q=a.other/'tests/validation_results.json'
    records.append({'file':'tests/validation_results.json','comparison':'SHA256_byte_identity','identical':sha(p)==sha(q),'archived_sha256':sha(p),'rerun_sha256':sha(q)})
    payload={'all_equal':all(r['identical'] for r in records),'compared_files':len(records),'different_files':sum(not r['identical'] for r in records),'excluded':'wall-clock execution.json and stdout logs, pilot outputs; NPZ compared by exact named arrays, not ZIP timestamps','files':records}
    (ROOT/'tests/full_replay_comparison.json').write_text(json.dumps(payload,indent=2)+'\n')
    if not payload['all_equal']:raise RuntimeError('Scientific outputs differ; inspect comparison record')
    print(json.dumps({k:v for k,v in payload.items() if k!='files'},indent=2))
if __name__=='__main__':main()
