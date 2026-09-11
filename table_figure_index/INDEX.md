# Table, figure and evidence index

This index maps article-facing tables and figures to scientific records and producer routes in this repository.
The manuscript source is intentionally not part of the reproducibility repository.
Rendered article figures are presentation products; the underlying data and figure-generation sources are retained.

## Main Table 1

Conceptual/non-numerical item; no separate repository evidence file is required.

Producer / verification route:

`Conceptual table: current methods section; not a numerical experiment.`

## Main Table 2

Evidence files:
- `computational/results/inference/paired_intervals.csv`
- `computational/results/inference/primary33_median_draws.npz`
- `computational/results/inference/primary33_draw_columns.json`

Producer / verification route:

`python commands/paper_a.py primary --csv DATA.csv.zip --out NEW_RUN`

## Main Table 4

Evidence files:
- `computational/results/benchmark/summary.csv`
- `computational/results/benchmark/geometric_predictions.csv.gz`
- `computational/results/benchmark/fingerprint_predictions.csv.gz`
- `computational/populations/official33_primary_rows.csv`
- `computational/populations/fingerprint_database_rows.csv`

Producer / verification route:

`python commands/paper_a.py primary --csv DATA.csv.zip --out NEW_RUN`

## Main Table 5

Evidence files:
- `computational/results/geography/summary.csv`
- `computational/results/geography/predictions.csv.gz`
- `computational/populations/geographic_definitions.json`
- `computational/results/geography/primary_intervals.csv`

Producer / verification route:

`python commands/paper_a.py secondary --csv DATA.csv.zip --out NEW_RUN`

## Main Table 6

Evidence files:
- `computational/results/density/across_draw_descriptions.csv`
- `computational/results/density/per_draw_summary.csv`
- `computational/results/density/predictions.csv.gz`
- `computational/populations/removal_definitions.json`

Producer / verification route:

`python commands/paper_a.py secondary --csv DATA.csv.zip --out NEW_RUN`

## Main Table 7

Evidence files:
- `computational/results/benchmark/solver_status_summary.json`
- `computational/results/benchmark/nlls_start_records.csv.gz`
- `computational/results/benchmark/geometric_predictions.csv.gz`

Producer / verification route:

`python commands/paper_a.py primary --csv DATA.csv.zip --out NEW_RUN`

## Main Figure 1

Evidence files:
- `computational/results/benchmark/geometric_predictions.csv.gz`
- `computational/src/secondary/code/make_figures.py`

Producer / verification route:

`python commands/paper_a.py figures --out NEW_FIGURES`

## Main Figure 3

Evidence files:
- `computational/src/secondary/inputs/reception_census.csv`
- `computational/src/secondary/inputs/release_reception_counts.csv`
- `computational/results/join/construction_summary.json`

Producer / verification route:

`python commands/paper_a.py core --csv DATA.csv.zip --json DATA.json.zip --out NEW_RUN; then python commands/paper_a.py figures --out NEW_FIGURES`

## Supplement S1 / F2 Table F2.1

Evidence files:
- `computational/data_products/receiver_crosswalk.csv`
- `computational/data_products/receiver_crosswalk.json`
- `computational/data_products/identities44.json`
- `computational/results/join/column_evidence.csv`
- `computational/results/join/alignment.csv.gz`

Producer / verification route:

`python commands/paper_a.py core --csv DATA.csv.zip --json DATA.json.zip --out NEW_RUN`

## Supplement S2 / F2 Table F2.3

Evidence files:
- `computational/src/primary/code/evaluator_stable.py`
- `computational/src/primary/snapshots/baseline_001_160826.py`
- `computational/environment/executed_environment.json`
- `computational/environment/least_squares_signature_and_version.json`
- `computational/populations/rssfit_receiver_traversal.csv`
- `computational/populations/rssfit_ordered_fit_inputs.csv.gz`

Producer / verification route:

`Source/ordering specification; core verifies receiver-input order; primary replays the coordinate fit.`

## Supplement S3

Evidence files:
- `computational/populations/working_source_ledger.csv.gz`
- `computational/populations/primary_role_ledger.csv.gz`
- `computational/populations/temporal_role_ledger.csv.gz`
- `computational/populations/geographic_definitions.json`

Producer / verification route:

`Core independently checks the primary selections; primary/secondary execute the documented population recipes.`

## Supplement S4 / historical common-27

Evidence files:
- `computational/results/prepared/common27_stable_bridge.csv`
- `computational/results/benchmark/anomaly_decomposition.csv`
- `computational/data_products/metadata_common27.json`
- `computational/data_products/rssfit_common27.json`
- `computational/populations/historical_common27_rows.csv`

Producer / verification route:

`python commands/paper_a.py primary --csv DATA.csv.zip --out NEW_RUN`

## Supplement S5.1

Evidence files:
- `computational/results/join/construction_summary.json`
- `computational/results/join/surplus_json_records.json`

Producer / verification route:

`python commands/paper_a.py core --csv DATA.csv.zip --json DATA.json.zip --out NEW_RUN`

## Supplement S5.2

Evidence files:
- `computational/results/residual_version/matched_links.csv.gz`
- `computational/results/residual_version/summary.json`
- `computational/src/secondary/code/reconcile_residuals.py`

Producer / verification route:

`python commands/paper_a.py secondary --csv DATA.csv.zip --out NEW_RUN`

## Supplement Table S6.1

Evidence files:
- `computational/results/geography/primary_intervals.csv`
- `computational/results/geography/calibration_counts.csv`
- `computational/results/geography/definitions.json`

Producer / verification route:

`python commands/paper_a.py secondary --csv DATA.csv.zip --out NEW_RUN`

## Supplement Table S6.2

Evidence files:
- `computational/results/density/per_draw_summary.csv`
- `computational/results/density/conditional_intervals.csv`
- `computational/results/density/draw_definitions.json`

Producer / verification route:

`python commands/paper_a.py secondary --csv DATA.csv.zip --out NEW_RUN`

## Supplement Table S6.3

Evidence files:
- `computational/results/temporal/summary.csv`
- `computational/results/temporal/predictions.csv.gz`
- `computational/results/temporal/definitions.json`
- `computational/results/inference/paired_intervals.csv`

Producer / verification route:

`python commands/paper_a.py primary --csv DATA.csv.zip --out NEW_RUN`

## Supplement S6.3 matched-map bridge

Evidence files:
- `computational/results/continuity/matched_temporal_bridge_summary.csv`
- `computational/results/continuity/matched_temporal_bridge_predictions.csv.gz`
- `computational/results/continuity/matched_temporal_bridge_block_intervals.csv`
- `computational/src/join_and_continuity/continuity_and_bridge.py`
- `computational/src/join_and_continuity/bridge_block_sensitivity.py`

Producer / verification route:

`python commands/replay_continuity.py --csv DATA.csv.zip --out NEW_RUN`

## Supplement Table S6.4

Evidence files:
- `computational/results/continuity/descriptive_other_temporal_estimands.csv`
- `computational/results/continuity/exploratory_temporal_mean_p90_intervals.csv`
- `computational/src/join_and_continuity/temporal_other_metrics.py`

Producer / verification route:

`python commands/replay_continuity.py --csv DATA.csv.zip --out NEW_RUN`

## Supplement S7

Evidence files:
- `computational/provenance/prior_receipts/primary/validation_results.json`
- `computational/provenance/prior_receipts/secondary/VALIDATION.json`
- `computational/commands/verify_evidence.py`

Producer / verification route:

`python commands/paper_a.py verify --out NEW_CHECK; new replay receipts in checks/ are separately scoped.`

