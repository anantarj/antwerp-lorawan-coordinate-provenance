#!/usr/bin/env python3
"""Run the declared A4b numerical stage into a fresh output directory."""
from pathlib import Path
import argparse,shutil,subprocess,sys,zipfile,hashlib,os

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();src=Path(__file__).resolve().parents[1]
    if a.out.exists():raise SystemExit('Destination exists; refuse to overwrite an archived run.')
    a.out.mkdir(parents=True)
    for n in ['code','snapshots','inputs','protocol']:shutil.copytree(src/n,a.out/n)
    for n in ['results','tests']:(a.out/n).mkdir()
    tmp=a.out/'raw_input';tmp.mkdir();dest=tmp/'lorawan_antwerp_2019_dataset.csv'
    if zipfile.is_zipfile(a.data):
        with zipfile.ZipFile(a.data) as z:
            names=[n for n in z.namelist() if n.endswith('.csv') and '__MACOSX' not in n]
            if len(names)!=1:raise SystemExit('Expected one scientific CSV member.')
            dest.write_bytes(z.read(names[0]))
    else:shutil.copyfile(a.data,dest)
    if hashlib.sha256(dest.read_bytes()).hexdigest()!='870abe60a4bd81f31ede6f269b6bc6329e05d2731343dff7015bae1a61218446':raise SystemExit('Wrong input checksum')
    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
    for script in ['secondary_controls.py','validate_secondary.py']:
        with (a.out/'results'/(script+'.stdout.txt')).open('w') as f:
            subprocess.run([sys.executable,str(a.out/'code'/script),'--data',str(dest)],check=True,stdout=f,stderr=subprocess.STDOUT,env=env)
    shutil.rmtree(tmp);print('Completed numerical stage and validation:',a.out)
if __name__=='__main__':main()
