#!/usr/bin/env python3
"""Regenerate F3 plots from the exported descriptive data; no model fitting."""
from pathlib import Path
import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--results',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    g=pd.read_csv(a.results/'receiver_geometry33.csv',dtype={'bs':str})
    cal=pd.read_csv(a.results/'calibration_locations_for_plot.csv.gz')
    def save(fig,name):
        fig.tight_layout()
        fig.savefig(a.out/(name+'.png'),dpi=180,bbox_inches='tight')
        fig.savefig(a.out/(name+'.pdf'),bbox_inches='tight',metadata={'CreationDate':None,'ModDate':None})
        plt.close(fig)
    # Full overview: remote catalogue BS71 is deliberately not cropped away.
    fig,ax=plt.subplots(figsize=(6.6,6.6))
    ax.scatter(cal.x_m/1000,cal.y_m/1000,s=2,alpha=.15,label='Calibration transmitter positions',rasterized=True)
    for row in g.itertuples():
        ax.plot([row.metadata_x_m/1000,row.fit_x_m/1000],[row.metadata_y_m/1000,row.fit_y_m/1000],
                linewidth=.7,alpha=.45,linestyle='--')
    ax.scatter(g.metadata_x_m/1000,g.metadata_y_m/1000,marker='o',s=30,label='Catalogue-derived receivers')
    ax.scatter(g.fit_x_m/1000,g.fit_y_m/1000,marker='x',s=36,label='Frozen RSSFIT receivers')
    b=g[g.bs=='71'].iloc[0]
    ax.annotate('BS71 catalogue', (b.metadata_x_m/1000,b.metadata_y_m/1000),xytext=(8,8),textcoords='offset points',fontsize=10)
    ax.annotate('BS71 fit',(b.fit_x_m/1000,b.fit_y_m/1000),xytext=(-72,-55),textcoords='offset points',fontsize=9,arrowprops={'arrowstyle':'->'})
    ax.set_xlabel('UTM zone 31N easting (km)');ax.set_ylabel('UTM zone 31N northing (km)')
    ax.set_aspect('equal',adjustable='box');ax.legend(loc='upper center',bbox_to_anchor=(.5,-.14),fontsize=8)
    save(fig,'G1_full_coordinate_overview')
    # Every primary receiver, displayed in stable numerical ID order.
    fig,ax=plt.subplots(figsize=(7.2,8.0))
    ypos=np.arange(len(g));ax.barh(ypos,g.coordinate_discrepancy_m/1000)
    labels=['BS '+b+(' *' if o else '') for b,o in zip(g.bs,g.metadata_outside)]
    ax.set_yticks(ypos,labels,fontsize=9);ax.invert_yaxis()
    ax.set_xlabel('Catalogue-relative coordinate discrepancy (km)')
    ax.text(.98,.02,'* Catalogue point outside its RSSFIT box',transform=ax.transAxes,ha='right',va='bottom',fontsize=9)
    for i,row in enumerate(g.itertuples()):
        if row.bs=='71':ax.annotate(f'{row.coordinate_discrepancy_m/1000:.2f} km',(row.coordinate_discrepancy_m/1000,i),xytext=(3,0),textcoords='offset points',va='center',fontsize=9)
    ax.set_xlim(0,51)
    save(fig,'G2_all33_discrepancies')
    # Paired components for every old draw; no statistical pooling or new draw.
    d=pd.read_csv(a.results/'existing_density_decomposition.csv')
    for method,pretty in [('FP_k3','Fingerprint (k=3)'),('MinMax','Min-Max')]:
        f=d[d.method==method].sort_values(['retained_receivers','draw_index0'],ascending=[False,True]).reset_index(drop=True)
        ix=np.arange(len(f));fig,ax=plt.subplots(figsize=(7.2,4.3))
        ax.scatter(ix-.13,f.removal_component_m,marker='o',s=28,label='Removal: reduced minus full on survivors')
        ax.scatter(ix+.13,f.selection_component_m,marker='x',s=32,label='Selection: full on survivors minus parent')
        ax.axhline(0,linestyle='--',linewidth=.8)
        for bound in [7.5,15.5,23.5]:ax.axvline(bound,linestyle=':',linewidth=.7)
        ax.set_xticks(ix,[f'{r.retained_receivers}:{r.draw_index0}' for r in f.itertuples()],rotation=90,fontsize=8)
        ax.set_xlabel('Retained receivers : pre-existing draw index')
        ax.set_ylabel('Difference of median errors (m)')
        ax.set_title(pretty+' — existing draw-by-draw decomposition',fontsize=11)
        ax.legend(fontsize=8,loc='best')
        save(fig,'G3_density_FP' if method=='FP_k3' else 'G4_density_MinMax')

if __name__=='__main__':main()
