"""Safe I/O and receipts for the reader-facing F2 commands; no estimator changes."""
from __future__ import annotations
import contextlib,hashlib,json,os,shutil,subprocess,sys,tempfile,zipfile,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
HASHES={'csv':'870abe60a4bd81f31ede6f269b6bc6329e05d2731343dff7015bae1a61218446','json':'f2f1fbd478cdef2b76fb8e3aae33751d332b50fc8546684d8e73fdb1505451cb','catalogue':'507f9bb266d23f59fdc2b743447cecf9c909290536e24de3f9483aaa178d374d'}
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1<<20),b''):h.update(b)
 return h.hexdigest()
def dump(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n')
def newdir(p):
 p=Path(p).resolve()
 if p==ROOT or ROOT in p.parents:raise ValueError('Output must be outside the immutable supplement')
 p.mkdir(parents=True,exist_ok=False);return p
@contextlib.contextmanager
def payload(src,kind):
 """Accept a plain, checksum-pinned payload or one safe scientific ZIP member."""
 src=Path(src).resolve()
 if not src.is_file():raise FileNotFoundError(src)
 with tempfile.TemporaryDirectory(prefix='paper_a_input_') as d:
  p=src
  if zipfile.is_zipfile(src):
   with zipfile.ZipFile(src) as z:
    bad=z.testzip()
    if bad:raise ValueError('Corrupt ZIP member: '+bad)
    def wanted(n):
     if n.startswith('__MACOSX/') or '/__MACOSX/' in n or Path(n).name.startswith('._'):return False
     name=Path(n).name
     return name=='lorawan_antwerp_2019_dataset.csv' if kind=='csv' else name in ('lorawan_antwerp_2019_dataset.json','lorawan_antwerp_2019_dataset.json.txt') if kind=='json' else name=='lorawan_antwerp_gateway_locations.json'
    members=[n for n in z.namelist() if wanted(n)]
    if len(members)!=1:raise ValueError(f'Expected one unambiguous {kind} data member; got {members}')
    p=Path(d)/Path(members[0]).name
    with z.open(members[0]) as a,p.open('wb') as b:shutil.copyfileobj(a,b)
  h=sha(p)
  if h!=HASHES[kind]:raise ValueError(f'{kind} SHA-256 mismatch: {h}')
  yield p

def run(script,args,log,receipt):
 cmd=[sys.executable,'-B','-u',str(script),*map(str,args)]
 env={**os.environ,'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1','PYTHONHASHSEED':'0','PYTHONDONTWRITEBYTECODE':'1'}
 t=time.time();print('RUN',Path(script).name,flush=True)
 with Path(log).open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=env,cwd=Path(log).parent)
 info={'command':cmd,'returncode':r.returncode,'elapsed_seconds':time.time()-t,'log':Path(log).name}
 dump(receipt,info)
 if r.returncode:raise RuntimeError(f'{Path(script).name} failed; see {log}')
 return info

def compare_files(a,b):
 import gzip,numpy as np
 a,b=Path(a),Path(b)
 if not b.is_file():return False,'missing'
 if a.suffix=='.npz':
  with np.load(a,allow_pickle=False) as x,np.load(b,allow_pickle=False) as y:
   ok=set(x.files)==set(y.files) and all(np.array_equal(x[k],y[k],equal_nan=True) for k in x.files)
  return ok,'exact ndarray comparison'
 if a.name.endswith('.gz'):return gzip.decompress(a.read_bytes())==gzip.decompress(b.read_bytes()),'decompressed byte comparison'
 return a.read_bytes()==b.read_bytes(),'exact byte comparison'

def compare_results(target,subdirs,out):
 records=[]
 for sub in subdirs:
  for a in sorted((ROOT/'results'/sub).rglob('*')):
   if not a.is_file() or a.name in ('execution.json','checks.json'):continue
   b=target/'results'/sub/a.relative_to(ROOT/'results'/sub)
   ok,kind=compare_files(a,b);records.append({'path':f'results/{sub}/{a.relative_to(ROOT/"results"/sub)}','match':ok,'comparison':kind})
 dump(out,{'records':records,'compared':len(records),'mismatches':sum(not r['match'] for r in records),'scope':'Identified output records, not elapsed-time logs or a cross-platform guarantee.'})
 if any(not r['match'] for r in records):raise AssertionError('Replay differs; see '+str(out))
 return records
