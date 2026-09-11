#!/usr/bin/env python3
"""Rebuild anonymous submission TeX and PDFs from canonical Markdown in a fresh directory."""
from __future__ import annotations
from pathlib import Path
import argparse, json, os, shutil, subprocess
ROOT=Path(__file__).resolve().parents[1]
NAMES=[('Manuscript_without_author_details',True),('Supplementary_material_without_author_details',False)]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    out=a.out.resolve()
    if out.exists() or out.is_relative_to(ROOT):raise ValueError('Output must be new and outside this package.')
    for exe in ['pandoc','xelatex']:
        if not shutil.which(exe):raise RuntimeError('Missing build executable: '+exe)
    out.mkdir(parents=True);work=out/'manuscript';shutil.copytree(ROOT/'manuscript',work)
    for name,_ in NAMES:
        for ext in ['pdf','tex']:(work/(name+'.'+ext)).unlink(missing_ok=True)
    logs=out/'logs';logs.mkdir()
    env={**os.environ,'SOURCE_DATE_EPOCH':'1789084800','PYTHONDONTWRITEBYTECODE':'1'}
    runs=[]
    for name,number in NAMES:
        args=['pandoc',name+'.md','--standalone','-V','mainfont=Liberation Serif','-V','monofont=DejaVu Sans Mono',
              '-V','geometry:margin=2.4cm','-V','fontsize=11pt','-V','secnumdepth=2',
              '--lua-filter',str(ROOT/'commands/wrap_code.lua')]
        if number:args+=['--number-sections']
        for ext in ['tex','pdf']:
            cmd=args+['--pdf-engine=xelatex','-o',name+'.'+ext]
            r=subprocess.run(cmd,cwd=work,env=env,capture_output=True,text=True)
            (logs/(name+'_'+ext+'.log')).write_text('COMMAND: '+repr(cmd)+'\n'+r.stdout+r.stderr)
            runs.append({'file':name+'.'+ext,'returncode':r.returncode})
            if r.returncode:raise RuntimeError(name+' build failed: '+r.stderr)
    versions={tool:subprocess.run([tool,'--version'],capture_output=True,text=True).stdout.splitlines()[0] for tool in ['pandoc','xelatex']}
    (out/'BUILD_RECEIPT.json').write_text(json.dumps({'runs':runs,'versions':versions,
         'scope':'Document generation only; no scientific producer or statistical resampling invoked.'},indent=2)+'\n')
    print(json.dumps({'built':runs,'output':str(work)},indent=2))
if __name__=='__main__':main()
