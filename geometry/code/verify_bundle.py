#!/usr/bin/env python3
"""Fast F3 delivery fingerprint check; not a numerical or scientific replay."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/'MANIFEST.json').read_text())
bad=[]
for entry in manifest['files']:
    path=root/entry['path']
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=entry['sha256']:
        bad.append(entry['path'])
print(json.dumps({'scope':'F3 delivery hashes only','files_checked':len(manifest['files']),'mismatches':bad},indent=2))
if bad:raise SystemExit(1)
