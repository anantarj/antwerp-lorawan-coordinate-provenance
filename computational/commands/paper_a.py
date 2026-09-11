#!/usr/bin/env python3
"""Reader entry point: verify saved evidence or replay specified producers.

Every output directory must be new and outside this package. Inputs are never
rewritten. Use --help on each subcommand. Full numerical replay is distinct from
frozen-map replay and from verification of already-saved output.
"""
from __future__ import annotations
import argparse,json,shutil,sys
from pathlib import Path
from _support import ROOT,newdir,run,payload,dump,compare_results

def main():
 p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='task',required=True)
 for name,help_ in [('verify','Verify bundled identities and recompute saved summaries; no raw data required'),('tables','Generate current numerical table views from saved results'),('self-test','Run unchanged join fixtures in a new writable test layout'),('figures','Regenerate the two figures from saved numerical inputs')]:
  q=s.add_parser(name,help=help_);q.add_argument('--out',type=Path,required=True)
 for name,help_ in [('core','Raw CSV/JSON join plus frozen-map raw-WCL replay (no coordinate fit)'),('join','Raw-to-identity and catalogue projection replay')]:
  q=s.add_parser(name,help=help_);q.add_argument('--csv',type=Path,required=True);q.add_argument('--json',type=Path,required=True);q.add_argument('--catalogue',type=Path,default=ROOT/'data_products/gateway_catalogue_249.json');q.add_argument('--out',type=Path,required=True)
 for name,help_ in [('primary','Unchanged full primary, temporal, inference and validation producer (includes coordinate refitting)'),('secondary','Unchanged geographic/removal and residual producers plus validation')]:
  q=s.add_parser(name,help=help_);q.add_argument('--csv',type=Path,required=True);q.add_argument('--out',type=Path,required=True);q.add_argument('--workers',type=int,default=4)
 a=p.parse_args();out=newdir(a.out)
 try:
  if a.task=='verify':
   run(ROOT/'commands/verify_evidence.py',['--out',out/'evidence'],out/'verify.log',out/'execution.json')
  elif a.task=='tables':
   run(ROOT/'commands/table_views.py',['--out',out/'tables'],out/'tables.log',out/'execution.json')
  elif a.task=='self-test':
   (out/'code').mkdir();(out/'results').mkdir()
   for name in ['rebuild_join.py','test_join_contract.py']:
    shutil.copyfile(ROOT/'src/join_and_continuity'/name,out/'code'/name)
   run(out/'code/test_join_contract.py',[],out/'self_test.log',out/'execution.json')
  elif a.task=='figures':
   (out/'code').mkdir();(out/'inputs').mkdir()
   shutil.copyfile(ROOT/'src/secondary/code/make_figures.py',out/'code/make_figures.py')
   for name in ['base_geometric_predictions.csv.gz','reception_census.csv']:
    shutil.copyfile(ROOT/'src/secondary/inputs'/name,out/'inputs'/name)
   run(out/'code/make_figures.py',[],out/'figures.log',out/'execution.json')
  elif a.task in ('join','core'):
   with payload(a.csv,'csv') as csv,payload(a.json,'json') as js,payload(a.catalogue,'catalogue') as cat:
    run(ROOT/'src/join_and_continuity/rebuild_join.py',['--csv',csv,'--json',js,'--out',out/'join'],out/'join.log',out/'join_execution.json')
    run(ROOT/'src/join_and_continuity/project_rebuilt_maps.py',['--join',out/'join','--catalogue',cat],out/'projection.log',out/'projection_execution.json')
    run(ROOT/'commands/check_core.py',['--csv',csv,'--join',out/'join','--out',out/'core','--mode',a.task],out/'core.log',out/'core_execution.json')
  elif a.task=='primary':
   if not 1<=a.workers<=64:raise ValueError('workers must be 1..64')
   run(ROOT/'src/primary/code/run_stage.py',['--data',a.csv.resolve(),'--out',out/'run','--workers',a.workers],out/'primary.log',out/'execution.json')
   compare_results(out/'run',['prepared','benchmark','temporal','inference'],out/'comparison.json')
  elif a.task=='secondary':
   with payload(a.csv,'csv') as csv:
    run(ROOT/'src/secondary/code/run_a4b.py',['--data',csv,'--out',out/'run'],out/'secondary.log',out/'execution.json')
    run(out/'run/code/reconcile_residuals.py',['--data',csv],out/'residual.log',out/'residual_execution.json')
   compare_results(out/'run',['geography','density','residual_version'],out/'comparison.json')
  dump(out/'COMPLETE.json',{'complete':True,'task':a.task,'package_version':'R3-F2-2026-09-06','interpretation':'A replay/verification receipt, not a new independent deployment or scientific generalization.'})
  print('COMPLETE',a.task,out,flush=True)
 except Exception as e:
  dump(out/'FAILED.json',{'task':a.task,'error':repr(e)});raise
if __name__=='__main__':main()
