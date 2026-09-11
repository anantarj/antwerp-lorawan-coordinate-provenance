#!/usr/bin/env python3
"""Generate R5-numbered full-precision table views from unchanged scientific outputs."""
from pathlib import Path
import argparse, json, subprocess, sys
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 out=a.out.resolve()
 if out.exists() or out.is_relative_to(ROOT):raise ValueError('Output must be new and external.')
 out.mkdir(parents=True);old=out/'prior_views'
 subprocess.run([sys.executable,str(ROOT/'computational/commands/table_views.py'),'--out',str(old)],check=True)
 mapping={'M_Table2_assignment_intervals':'M_Table2_assignment_intervals','M_Table3_benchmark':'M_Table4_benchmark',
          'M_Table4_geography':'M_Table5_geography','M_Table5_receiver_removal':'M_Table6_receiver_removal',
          'M_Table6_solver_status':'M_Table7_solver_status','S_TableS1_identity_crosswalk':'S_TableS1_2_identity_crosswalk',
          'S_reception_census':'S_TableS5_1_reception_census','S_residuals':'S_TableS5_2_residuals',
          'S_TableS6_1_geography_intervals':'S_TableS6_1_geography_intervals',
          'S_TableS6_2_six_receiver_draws':'S_TableS6_2_six_receiver_draws',
          'S_all_draw_removal_selection':'S_all_draw_removal_selection',
          'S_TableS6_3_temporal_medians':'S_TableS6_3_temporal_medians',
          'S_TableS6_4_temporal_other_estimands':'S_TableS6_4_temporal_other_estimands'}
 for src,dst in mapping.items():(out/(dst+'.csv')).write_bytes((old/(src+'.csv')).read_bytes())
 geo=ROOT/'geometry/results/frozen_geometry'
 j=json.loads((geo/'coordinate_summary.json').read_text());pd.DataFrame(j['rosters']).drop(columns=['outside_reference_ids','fit_on_boundary_ids','fit_within_60m_ids']).to_csv(out/'M_Table3_frozen_geometry.csv',index=False)
 d=pd.read_csv(geo/'receiver_geometry33.csv',dtype={'bs':str,'gateway_id':str})
 d[['bs','metadata_x_m','metadata_y_m','fit_x_m','fit_y_m']].to_csv(out/'S_TableS1_3_coordinate_assignments.csv',index=False)
 d.to_csv(out/'S_TableS4_1_receiver_geometry.csv',index=False)
 (out/'S_TableS4_2_BS71_distances.csv').write_bytes((geo/'BS71_distance_summary.csv').read_bytes())
 receipts={'scope':'Saved-output views, not new predictions/fits or bootstrap intervals. Numerical precision retained.',
           'files':[p.name for p in sorted(out.glob('*.csv'))], 'renumbering':mapping}
 (out/'TABLE_RECEIPT.json').write_text(json.dumps(receipts,indent=2)+'\n')
 print('tables',len(receipts['files']))
if __name__=='__main__':main()
