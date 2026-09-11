#!/usr/bin/env python3
"""Version reconciliation of an existing secondary residual diagnostic.
Uses the already-frozen stable RSSFIT map and fixed historical common27 links.
No new mechanism, selection policy or physical-noise distribution is inferred.
"""
import argparse
import numpy as np
import pandas as pd
from scipy.stats import kurtosis
from common import *

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--data',type=Path,required=True);a=ap.parse_args();c=context(a.data)
 off=loadmap(ROOT/'inputs/official33.json');rec=loadmap(ROOT/'inputs/recovered29.json');fit=loadmap(ROOT/'inputs/rssfit_stable41.json');gids=sorted(set(off)&set(rec)&set(fit),key=int)
 rows=[];summ=[]
 for gid in gids:
  obs=[(wi,rx.rssi) for wi in c['ci'] for rx in c['msgs'][wi].receptions if rx.gid==gid]
  xy=np.array([[c['msgs'][wi].x,c['msgs'][wi].y] for wi,r in obs]);r=np.array([r for wi,r in obs]);cur=[]
  for mp in [off,fit]:
   v=r+47*np.log10(np.linalg.norm(xy-mp[gid],axis=1)+1);cur.append(v-np.median(v))
  for k,(wi,raw) in enumerate(obs):rows.append(dict(csv_row_index0=int(c['rows'][wi]),receiver=gid,official_residual_db=cur[0][k],rssfit_stable_residual_db=cur[1][k]))
 f=pd.DataFrame(rows);out=ROOT/'results/residual_version';out.mkdir(exist_ok=True);csvout(out/'matched_links.csv.gz',f)
 for label,col in [('official_common27','official_residual_db'),('rssfit_stable_common27','rssfit_stable_residual_db')]:
  v=f[col].to_numpy();s=float(np.std(v));summ.append(dict(assignment=label,n_links=len(v),excess_kurtosis=float(kurtosis(v,fisher=True,bias=True)),sd_db=s,beyond_3sd_fraction=float(np.mean(abs(v)>3*s))))
 dump(out/'summary.json',{'link_set_common27':gids,'records':summ,'distinct_links':len(f.drop_duplicates(['csv_row_index0','receiver'])),'rssfit_map_sha256':sha(ROOT/'inputs/rssfit_stable41.json'),'analysis':'Existing diagnostic synchronized to the stable map; calibration residuals only, no inferential or physical-noise claim.'})
 print(summ)
if __name__=='__main__':main()
