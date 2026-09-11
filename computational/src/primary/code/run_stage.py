#!/usr/bin/env python3
"""Reproduce this stage in a NEW directory without overwriting its archived results.

python code/run_stage.py --data /path/to/lorawan_antwerp_2019_dataset.csv.zip \
    --out /path/to/new-run --workers 4
"""
from __future__ import annotations
import argparse, hashlib, json, os, platform, shutil, subprocess, sys, tempfile, time, zipfile
from pathlib import Path

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for z in iter(lambda:f.read(1<<20),b''):h.update(z)
    return h.hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--data',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--workers',type=int,default=4);a=ap.parse_args()
    root=Path(__file__).resolve().parents[1];dest=a.out.resolve();data=a.data.resolve()
    if dest.exists():raise FileExistsError('Output must be a new directory: '+str(dest))
    if root==dest or root in dest.parents:raise ValueError('Output must be outside the source bundle')
    if not 1<=a.workers<=64:raise ValueError('workers must be from 1 to 64')
    dest.mkdir(parents=True)
    for sub in ['code','snapshots','inputs','protocol']:
        shutil.copytree(root/sub,dest/sub,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    (dest/'results').mkdir();(dest/'tests').mkdir()
    env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1','PYTHONHASHSEED':'0'}
    started=time.time();records=[]
    with tempfile.TemporaryDirectory(prefix='paper_a_csv_') as temp:
        if data.suffix.lower()=='.zip':
            with zipfile.ZipFile(data) as z:
                if z.testzip() is not None:raise ValueError('ZIP CRC check failed')
                members=[p for p in z.namelist() if not p.startswith('__MACOSX') and Path(p).name=='lorawan_antwerp_2019_dataset.csv']
                if len(members)!=1:raise ValueError('Expected one named scientific CSV member')
                copied=Path(temp)/'lorawan_antwerp_2019_dataset.csv'
                with z.open(members[0]) as src,copied.open('wb') as dst:shutil.copyfileobj(src,dst)
            data=copied
        if sha(data)!='870abe60a4bd81f31ede6f269b6bc6329e05d2731343dff7015bae1a61218446':raise ValueError('CSV SHA256 mismatch')
        steps=[('prepare.py',['--data',str(data)]),('benchmark.py',['--data',str(data),'--workers',str(a.workers)]),('temporal.py',['--data',str(data)]),('inference.py',[]),('validate.py',['--data',str(data)])]
        for name,args in steps:
            cmd=[sys.executable,'-u',str(dest/'code'/name),*args];t=time.time();print('RUN',name,flush=True)
            with (dest/'results'/f'{Path(name).stem}_stdout.txt').open('w') as log:
                run=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
            records.append({'step':name,'returncode':run.returncode,'elapsed_seconds':time.time()-t,'command':cmd})
            (dest/'tests/run_stage_execution.json').write_text(json.dumps({'complete':False,'steps':records},indent=2)+'\n')
            if run.returncode:raise RuntimeError(f'{name} failed; inspect its log')
    (dest/'tests/run_stage_execution.json').write_text(json.dumps({'complete':True,'steps':records,'elapsed_seconds':time.time()-started,'python':sys.version,'platform':platform.platform()},indent=2)+'\n')
    print('COMPLETE',dest,flush=True)
if __name__=='__main__':main()
