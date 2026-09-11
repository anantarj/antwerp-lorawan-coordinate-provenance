#!/usr/bin/env python3
"""Render R5 views of frozen assignments and all saved removal draws; no fitting.

Use a new directory outside the package. Catalogue and RSSFIT are drawn first/second
with the default Matplotlib cycle in both coordinate views; circles/crosses also
encode identity so the distinction does not depend on colour. Each figure has one
axes object. The original component figures remain unchanged in geometry/.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
ROOT=Path(__file__).resolve().parents[1]

def main(out: Path, show: bool=False) -> None:
    out=Path(out).resolve()
    if out.exists() or out.is_relative_to(ROOT):
        raise ValueError('Output must be new and outside the immutable package.')
    out.mkdir(parents=True)
    src=ROOT/'geometry/results/frozen_geometry'
    g=pd.read_csv(src/'receiver_geometry33.csv',dtype={'bs':str,'gateway_id':str}).sort_values('bs',key=lambda a:a.astype(int))
    cal=pd.read_csv(src/'calibration_locations_for_plot.csv.gz')
    meta=g[['metadata_x_m','metadata_y_m']].to_numpy()/1000
    fitted=g[['fit_x_m','fit_y_m']].to_numpy()/1000
    ids=g.bs.tolist(); local=np.array([k!='71' for k in ids]);i71=ids.index('71')
    receipt={'scope':__doc__,'input_sha256':{},'figures':[]}
    for name in ['receiver_geometry33.csv','calibration_locations_for_plot.csv.gz','existing_density_decomposition.csv']:
        receipt['input_sha256'][name]=hashlib.sha256((src/name).read_bytes()).hexdigest()
    def save(fig, name):
        for ext in ['pdf','png']:
            fig.savefig(out/(name+'.'+ext),dpi=180,bbox_inches='tight')
        if show:plt.show()
        plt.close(fig)
    for overview,name in [(True,'G1_full_coordinate_overview'),(False,'G5_city_coordinate_detail')]:
        mask=np.ones(len(ids),dtype=bool) if overview else local
        fig,ax=plt.subplots(figsize=(6.7,6.8 if overview else 5.6))
        ax.scatter(meta[mask,0],meta[mask,1],s=28,marker='o',label='Catalogue-derived receivers',zorder=4)
        ax.scatter(fitted[:,0],fitted[:,1],s=38,marker='x',label='Frozen RSSFIT receivers',zorder=5)
        if overview:
            ax.scatter(cal.x_m/1000,cal.y_m/1000,s=2,alpha=.16,label='Calibration transmitter positions',rasterized=True,zorder=1)
        segments=np.stack([meta[mask],fitted[mask]],axis=1)
        ax.add_collection(LineCollection(segments,linestyles='dashed',linewidths=.65,alpha=.4,zorder=2))
        if overview:
            ax.annotate('BS71 catalogue',meta[i71],xytext=(7,8),textcoords='offset points',fontsize=9)
            ax.annotate('BS71 fit',fitted[i71],xytext=(-60,-18),textcoords='offset points',fontsize=9)
            box=np.vstack([meta,fitted,cal[['x_m','y_m']].to_numpy()/1000]);lo=box.min(0)-1.8;hi=box.max(0)+1.8
        else:
            for k in ['16','33','44','48']:
                i=ids.index(k);ax.annotate('BS'+k,meta[i],xytext=(4,4),textcoords='offset points',fontsize=8.5)
            ax.annotate('BS71 fitted',fitted[i71],xytext=(8,-14),textcoords='offset points',fontsize=8.5)
            box=np.vstack([meta[mask],fitted]);lo=box.min(0)-.65;hi=box.max(0)+.65
            fig.text(.5,.012,'BS71 catalogue entry is outside this local view; main Figure 2 retains its full extent.',ha='center',fontsize=8)
        ax.set_xlim(lo[0],hi[0]);ax.set_ylim(lo[1],hi[1]);ax.set_aspect('equal',adjustable='box')
        ax.ticklabel_format(style='plain',axis='both',useOffset=False)
        ax.set_xlabel('Easting (km, EPSG:32631)');ax.set_ylabel('Northing (km, EPSG:32631)')
        ax.legend(loc='lower center',bbox_to_anchor=(.5,1.01),fontsize=8.5,frameon=False)
        fig.tight_layout(rect=(0,.035 if not overview else 0,1,1))
        receipt['figures'].append({'name':name,'catalogue_n':int(mask.sum()),'rssfit_n':len(ids),'catalogue_ids':list(g.loc[mask,'bs']), 'rssfit_ids':ids,'bounds_km':[lo.tolist(),hi.tolist()],'encoding':'Catalogue: first default-cycle colour, circles; RSSFIT: second default-cycle colour, crosses.'})
        save(fig,name)
    d=pd.read_csv(src/'existing_density_decomposition.csv')
    ranks={23:0,16:1,10:2,6:3}
    allpoints=[]
    for method,name,title in [('FP_k3','G3_density_FP','Fingerprint (k=3)'),('MinMax','G4_density_MinMax','Min-Max')]:
        z=d[d.method==method].copy();z['group']=z.retained_receivers.map(ranks);z=z.sort_values(['group','draw_index0'])
        assert len(z)==32 and not z[['retained_receivers','draw_index0']].duplicated().any()
        y=np.arange(32,dtype=float)+np.repeat(np.arange(4)*1.2,8)
        fig,ax=plt.subplots(figsize=(6.8,8.9))
        ax.scatter(z.removal_component_m,y-.14,s=30,marker='o',label='Removal: reduced minus full on survivors')
        ax.scatter(z.selection_component_m,y+.14,s=38,marker='x',label='Selection: full on survivors minus parent')
        ax.axvline(0,linewidth=.75,linestyle='--',alpha=.6)
        for boundary in [8.1,17.3,26.5]:ax.axhline(boundary,linewidth=.55,linestyle=':',alpha=.4)
        ax.set_yticks(y,[f'{int(v.retained_receivers):2d}:{int(v.draw_index0)}  (n={int(v.n):,})' for v in z.itertuples()],fontsize=8.8)
        ax.invert_yaxis();ax.set_ylabel('Receivers : draw index (surviving messages)')
        ax.set_xlabel('Difference of median errors (m)');ax.set_title(title+': all saved removal/selection draws',fontsize=11)
        ax.legend(loc='upper center',bbox_to_anchor=(.5,-.065),fontsize=8.1,frameon=False)
        fig.tight_layout(rect=(0,.03,1,1))
        receipt['figures'].append({'name':name,'method':method,'draws':32,'smallest_n':int(z.n.min()),'largest_n':int(z.n.max()),'design_change':False})
        allpoints+=z.drop(columns='group').to_dict(orient='records')
        save(fig,name)
    pd.DataFrame(allpoints).to_csv(out/'PLOTTED_REMOVAL_VALUES.csv',index=False)
    (out/'FIGURE_RECEIPT.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n')
    print('Generated four display figures from unchanged records; 64 method/draw records retained.')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();main(a.out)
