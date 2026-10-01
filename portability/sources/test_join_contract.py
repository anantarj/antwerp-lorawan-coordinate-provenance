#!/usr/bin/env python3
"""Small discriminating tests for the freshly implemented signature matcher."""
import json
from pathlib import Path
import numpy as np
from rebuild_join import matches,jkey,integral

def main():
 checks={}
 a=np.array([[-100,-110,-200],[-101,-200,-90],[-200,-112,-92]],np.int16)
 b=a[:,[2,0,1]];rows=np.arange(3)
 checks['permuted_identifier_columns_recovered']=matches(a,b,rows)=={0:[1],1:[2],2:[0]}
 corrupt=b.copy();corrupt[1,1]=-102
 checks['one_RSSI_mismatch_rejects_exact_identity']=matches(a,corrupt,rows)[0]==[]
 missing=b.copy();missing[0,1]=-200
 checks['reception_presence_mismatch_rejects_identity']=matches(a,missing,rows)[0]==[]
 tied=np.column_stack([a[:,0],a[:,0]])
 checks['identical_signatures_remain_ambiguous']=matches(a,tied,rows)[0]==[0,1]
 checks['joint_row_permutation_preserves_mapping']=matches(a[[2,0,1]],b[[2,0,1]],rows)=={0:[1],1:[2],2:[0]}
 m={'sf':7,'hdop':.6,'gateways':[{'id':'A','rssi':-110,'rx_time':{'time':'T'}}],'latitude':0,'longitude':0};m2={**m,'latitude':80,'longitude':170}
 checks['transmitter_positions_do_not_enter_alignment']=jkey(m)==jkey(m2)
 try:integral(-110.2);checks['noninteger_RSSI_rejected_not_silently_rounded']=False
 except ValueError:checks['noninteger_RSSI_rejected_not_silently_rounded']=True
 assert all(checks.values()),checks
 dest=Path(__file__).resolve().parents[1]/'results/join_contract_tests.json';dest.write_text(json.dumps({'all_pass':True,'checks':checks},indent=2)+'\n');print(dest.read_text())
if __name__=='__main__':main()
