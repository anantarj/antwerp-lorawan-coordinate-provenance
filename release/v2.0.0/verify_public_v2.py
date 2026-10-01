#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "PUBLIC_REPOSITORY_MANIFEST.json"

def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):
            h.update(b)
    return h.hexdigest()

def run(cmd,cwd,env):
    print("+"," ".join(map(str,cmd)),flush=True)
    r=subprocess.run(list(map(str,cmd)),cwd=cwd,env=env)
    if r.returncode:
        raise SystemExit(r.returncode)

m=json.loads(MANIFEST.read_text())
assert m["version"]=="2.0.0"
bad=[]
for rec in m["files"]:
    p=ROOT/rec["path"]
    if not p.is_file():
        bad.append((rec["path"],"missing"))
    elif p.stat().st_size!=rec["bytes"] or sha(p)!=rec["sha256"]:
        bad.append((rec["path"],"identity mismatch"))
if bad:
    for x in bad[:50]:
        print("FAIL",*x)
    raise SystemExit(f"manifest failures: {len(bad)}")
print(f"PASS manifest: {len(m['files'])} files")

with tempfile.TemporaryDirectory(prefix="paper_a_public_v2_") as td:
    work=Path(td)/"repo"
    shutil.copytree(ROOT,work,ignore=shutil.ignore_patterns(".git","__pycache__","*.pyc"))
    env=os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"]="1"
    env["PYTHONPATH"]=str(work)+(os.pathsep+env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    env["PA_SOURCE_EVALUATOR"]=str(work/"computational/src/primary/code/evaluator_stable.py")

    run([sys.executable,"computational/commands/paper_a.py","verify","--out",Path(td)/"v1"],work,env)

    suites=[
      ("resource_validation","tests"),
      ("representation_population","tests"),
      ("fitting_validation","tests"),
      ("map_selection","tests"),
      ("portability","tests"),
      ("portability/sources","."),
      ("reliability/interfaces","tests"),
      ("reliability/native","tests"),
      ("reliability/transfer_temporal","tests"),
    ]
    for d,t in suites:
        print("\n===",d,"===")
        run([sys.executable,"-m","unittest","discover","-s",t,"-p","test*.py","-v"],work/d,env)

print("PASS public v2 packaged verification.")
print("Externally gated full reexecutions require separately obtained third-party inputs.")
