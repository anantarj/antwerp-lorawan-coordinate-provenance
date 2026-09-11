#!/usr/bin/env python3
"""Regenerate R1 figures from the saved primary predictions and audited census."""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
def main():
 out=ROOT/'revision/figures';out.mkdir(parents=True,exist_ok=True)
 predictions=pd.read_csv(ROOT/'inputs/base_geometric_predictions.csv.gz')
 primary=predictions[predictions.experiment=='primary33'];fig,ax=plt.subplots(figsize=(7.1,4.1))
 for assignment,label in [('official','Metadata-derived assignment'),('rssfit_stable','RSSFIT assignment')]:
  arm=primary[primary.assignment==assignment];assert len(arm)==2495 and arm.csv_row_index0.nunique()==2495
  values=np.sort(arm.WCL_raw_error_m.to_numpy());ax.step(values,np.arange(1,len(values)+1)/len(values),where='post',label=label)
 ax.set_xscale('log');ax.set_xlabel('Raw weighted-centroid error (m, logarithmic scale)');ax.set_ylabel('Empirical cumulative fraction');ax.set_ylim(0,1);ax.legend(loc='upper left');fig.tight_layout()
 for ext in ['pdf','png']:fig.savefig(out/f'F1_assignment_ecdf.{ext}',dpi=180,bbox_inches='tight')
 plt.close(fig)
 census=pd.read_csv(ROOT/'inputs/reception_census.csv');assert census.messages.sum()==55375 and list(census.available_receptions)==list(range(3,11))
 fig,ax=plt.subplots(figsize=(7.1,4.1));ax.bar(census.available_receptions,census.messages)
 for k,count in zip(census.available_receptions,census.messages):ax.annotate(f'{count:,}',(k,count),xytext=(0,5),textcoords='offset points',ha='center',fontsize=9)
 ax.set_yscale('log');ax.set_ylim(700,42000);ax.set_xticks(census.available_receptions);ax.set_xlabel('Available receptions per message');ax.set_ylabel('Messages (logarithmic scale)');fig.tight_layout()
 for ext in ['pdf','png']:fig.savefig(out/f'F2_observed_receptions.{ext}',dpi=180,bbox_inches='tight')
 plt.close(fig)
if __name__=='__main__':main()
