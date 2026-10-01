"""Execute received DAE source cells unchanged in an isolated workspace.
The separate index audit does not edit the source cell or call the new matcher.
"""
from __future__ import annotations
import argparse,json,math,os
from pathlib import Path
import numpy as np

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--notebook',type=Path,required=True);ap.add_argument('--work',type=Path,required=True)
    a=ap.parse_args();notebook=a.notebook.resolve();work=a.work.resolve();os.chdir(work)
    cells=json.loads(notebook.read_text())['cells'];env={}
    for i,c in enumerate(cells):
        source=''.join(c.get('source',[]))
        if c['cell_type']=='code' and source.strip():exec(compile(source,str(notebook)+f'#cell-{i}','exec'),env)
    # Reconstruct unstratified source-library split order without train_test_split.
    source_rows=env['file'].index.to_numpy(dtype=np.int64);n=len(source_rows)
    perm=np.random.RandomState(42).permutation(n);n_temp=math.ceil(.3*n)
    train=source_rows[perm[n_temp:]];temp=source_rows[perm[:n_temp]]
    p2=np.random.RandomState(42).permutation(len(temp));n_test=math.ceil(.5*len(temp))
    val=temp[p2[n_test:]];test=temp[p2[:n_test]]
    orig_ix={int(v):i for i,v in enumerate(source_rows)}
    for role,rows in [('train',train),('val',val),('test',test)]:
        q=np.array([orig_ix[int(i)] for i in rows])
        for field,full in [('x',env['x'].values),('y',env['y'].values),('HDOP',env['HDOP'])]:
            if not np.array_equal(env[f'{field}_{role}'],full[q],equal_nan=True):
                raise RuntimeError(f'Independent index reconstruction differs: {field}_{role}')
    np.savez(work/'reference_row_orders.npz',train=train,val=val,test=test)
    (work/'reference_execution.json').write_text(json.dumps({'cells_executed':[0,1],
      'scope':'Original source cells unchanged; no estimator/augmentation. Independent index audit uses NumPy permutations.',
      'retained_n':int(n),'partition_n':{k:int(len(v)) for k,v in [('train',train),('val',val),('test',test)]}},indent=2)+'\n')
if __name__=='__main__':main()
