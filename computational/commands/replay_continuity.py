#!/usr/bin/env python3
"""Replay the retained matched temporal map bridge and exploratory mean/tail work.

Uses the bundled primary records and unchanged bridge producers. Rebuilding the
full primary suite first is available through paper_a.py primary but is not a
hidden dependency. The input-view manifest is newly created here and explicitly
not presented as the historical primary-stage manifest.
"""
from __future__ import annotations
import argparse,shutil,zipfile
from pathlib import Path
from _support import ROOT,newdir,payload,sha,dump,run,compare_files

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--csv',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();out=newdir(a.out)
 stage=out/'input_view';stage.mkdir()
 for n in ['code','snapshots','inputs','protocol']:shutil.copytree(ROOT/'src/primary'/n,stage/n)
 for n in ['prepared','benchmark','temporal']:shutil.copytree(ROOT/'results'/n,stage/'results'/n)
 manifest={p.relative_to(stage).as_posix():{'sha256':sha(p)} for p in stage.rglob('*') if p.is_file()}
 dump(stage/'MANIFEST_SHA256.json',manifest)
 original=out/'original_source';original.mkdir()
 with zipfile.ZipFile(ROOT/'provenance/original_analysis.zip') as z:
  for name in ['baseline_001_160826.py','deltamesh_antwerp_eval_v10_fixed_080826.py']:
   matches=[n for n in z.namelist() if Path(n).name==name and '__MACOSX' not in n]
   if not matches:raise FileNotFoundError('Original source not found: '+name)
   data={z.read(n) for n in matches}
   if len(data)!=1:raise ValueError('Ambiguous original source versions: '+name)
   (original/name).write_bytes(next(iter(data)))
 with payload(a.csv,'csv') as csv:
  run(ROOT/'src/join_and_continuity/continuity_and_bridge.py',['--stage',stage,'--data',csv,'--original',original,'--out',out/'bridge'],out/'bridge.log',out/'bridge_execution.json')
  run(ROOT/'src/join_and_continuity/bridge_block_sensitivity.py',['--bridge',out/'bridge','--csv',csv],out/'blocks.log',out/'blocks_execution.json')
  run(ROOT/'src/join_and_continuity/temporal_other_metrics.py',['--stage',stage,'--csv',csv,'--out',out/'bridge'],out/'other_metrics.log',out/'other_metrics_execution.json')
 records=[]
 for name in ['matched_temporal_bridge_summary.csv','matched_temporal_bridge_predictions.csv.gz','matched_temporal_bridge_protocol.json','matched_temporal_bridge_block_intervals.csv','exploratory_temporal_mean_p90_intervals.csv']:
  ok,kind=compare_files(ROOT/'results/continuity'/name,out/'bridge'/name);records.append({'file':name,'match':ok,'comparison':kind})
 dump(out/'comparison.json',{'compared':len(records),'mismatches':sum(not x['match'] for x in records),'records':records,'note':'The newly created input_view manifest is not the historical primary manifest. Scientific source/prediction bytes are verified by the package source-copy index.'})
 if any(not x['match'] for x in records):raise AssertionError('Retained bridge outputs differ; inspect comparison.json')
 dump(out/'COMPLETE.json',{'complete':True,'scope':'Unchanged matched-map bridge and exploratory temporal mean/p90 producers replayed; no new experimental design.'});print('COMPLETE continuity',out)
if __name__=='__main__':main()
