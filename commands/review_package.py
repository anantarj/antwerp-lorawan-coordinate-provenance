#!/usr/bin/env python3
"""Anonymous S1 reader entry point. Delegates unchanged scientific producers; never writes inputs.

verify: saved evidence and integration checks; core: raw join plus frozen-map WCL;
primary: existing fit/localization/temporal producers; secondary: existing geographic/
removal producers; geometry: descriptive frozen-map calculations. None is a new design.
"""
from __future__ import annotations
import argparse, json, os, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
C = ROOT / 'computational'
G = ROOT / 'geometry'

def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('task',choices=['verify','tables','documents','core','primary','secondary','continuity','geometry','self-test','figures','diagnostics','receipt'])
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--csv',type=Path)
    p.add_argument('--json',type=Path)
    p.add_argument('--workers',type=int,default=4)
    p.add_argument('--dry-run',action='store_true',help='Print exact dispatch only; do not create output or execute a producer.')
    a=p.parse_args();out=a.out.resolve()
    if out.exists():p.error('Output must not exist; nothing was overwritten.')
    if out.is_relative_to(ROOT):p.error('Output must be outside the immutable review package.')
    if not 1<=a.workers<=64:p.error('workers must be 1..64')
    need_csv=a.task in ['core','primary','secondary','continuity','geometry','diagnostics']
    if need_csv and (a.csv is None or not a.csv.is_file()):p.error('This route requires an existing --csv file.')
    if a.task=='core' and (a.json is None or not a.json.is_file()):p.error('The core route requires an existing --json file.')
    cmds=[]
    if a.task=='receipt':
        cmds=[([sys.executable,str(ROOT/'commands/check_submission.py'),'--out',str(out/'receipt')],ROOT)]
    elif a.task=='diagnostics':
        cmds=[([sys.executable,str(ROOT/'commands/clarify_diagnostics.py'),'--csv',str(a.csv.resolve()),'--out',str(out/'diagnostics')],ROOT)]
    elif a.task=='verify':
        cmds=[([sys.executable,str(C/'commands/paper_a.py'),'verify','--out',str(out/'saved_evidence')],C),
              ([sys.executable,str(G/'code/verify_bundle.py')],G),
              ([sys.executable,str(ROOT/'commands/check_submission.py'),'--out',str(out/'integration')],ROOT)]
    elif a.task=='tables':
        cmds=[([sys.executable,str(ROOT/'commands/make_table_views.py'),'--out',str(out/'tables')],ROOT)]
    elif a.task=='figures':
        cmds=[([sys.executable,str(C/'commands/paper_a.py'),'figures','--out',str(out/'original_figures')],C),
              ([sys.executable,str(ROOT/'commands/make_revision_figures.py'),'--out',str(out/'revision_views')],ROOT)]
    elif a.task=='documents':
        cmds=[([sys.executable,str(ROOT/'commands/build_documents.py'),'--out',str(out/'documents')],ROOT)]
    elif a.task=='geometry':
        cmds=[([sys.executable,str(G/'code/describe_frozen_geometry.py'),'--f2',str(C),'--csv',str(a.csv.resolve()),'--out',str(out/'descriptors')],G)]
    elif a.task=='continuity':
        cmds=[([sys.executable,str(C/'commands/replay_continuity.py'),'--csv',str(a.csv.resolve()),'--out',str(out/'run')],C)]
    else:
        cmd=[sys.executable,str(C/'commands/paper_a.py'),a.task,'--out',str(out/'run')]
        if need_csv:cmd+=['--csv',str(a.csv.resolve())]
        if a.task=='core':cmd+=['--json',str(a.json.resolve())]
        if a.task=='primary':cmd+=['--workers',str(a.workers)]
        cmds=[(cmd,C)]
    routes={'task':a.task,'commands':[{'argv':cmd,'cwd':str(cwd)} for cmd,cwd in cmds],
            'scope':'Dispatch to unchanged supplied scientific producer(s); dry-run is not execution.'}
    if a.dry_run:
        print(json.dumps(routes,indent=2));return
    out.mkdir(parents=True,exist_ok=False)
    (out/'DISPATCH.json').write_text(json.dumps(routes,indent=2)+'\n')
    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONHASHSEED':'0',
         'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}
    outcomes=[]
    for i,(cmd,cwd) in enumerate(cmds):
        log=out/f'step_{i+1:02d}.log'
        with log.open('w') as stream:
            r=subprocess.run(cmd,cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT)
        outcomes.append({'step':i+1,'returncode':r.returncode,'log':log.name})
        if r.returncode:
            (out/'FAILED.json').write_text(json.dumps({'task':a.task,'steps':outcomes},indent=2)+'\n')
            raise SystemExit(f'{a.task} failed; inspect {log}')
    (out/'COMPLETE.json').write_text(json.dumps({'task':a.task,'complete':True,'steps':outcomes,
        'scope':'Executed only the routes listed in DISPATCH.json; not independent external replication.'},indent=2)+'\n')
    print('COMPLETE',a.task,out)
if __name__=='__main__':main()
