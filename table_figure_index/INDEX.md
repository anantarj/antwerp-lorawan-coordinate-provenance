# Anonymous S1 table, figure and evidence index

Current figures and resampling terminology follow Anonymous S1; component source and result bytes remain unchanged.

## Main Table 1

Experimental-question inventory

- `manuscript/Manuscript_without_author_details.md`

Conceptual table: current methods section; not a numerical experiment.

## Main Table 2

Primary paired/block assignment sensitivity intervals

- `computational/results/inference/paired_intervals.csv`
- `computational/results/inference/primary33_median_draws.npz`
- `computational/results/inference/primary33_draw_columns.json`

python commands/review_package.py primary --csv DATA.csv.zip --out NEW_RUN

## Main Table 4

Primary implementation benchmark

- `computational/results/benchmark/summary.csv`
- `computational/results/benchmark/geometric_predictions.csv.gz`
- `computational/results/benchmark/fingerprint_predictions.csv.gz`
- `computational/populations/official33_primary_rows.csv`
- `computational/populations/fingerprint_database_rows.csv`

python commands/review_package.py primary --csv DATA.csv.zip --out NEW_RUN

## Main Table 5

Bidirectional equal-budget geography

- `computational/results/geography/summary.csv`
- `computational/results/geography/predictions.csv.gz`
- `computational/populations/geographic_definitions.json`
- `computational/results/geography/primary_intervals.csv`

python commands/review_package.py secondary --csv DATA.csv.zip --out NEW_RUN

## Main Table 6

Receiver removal and availability

- `computational/results/density/across_draw_descriptions.csv`
- `computational/results/density/per_draw_summary.csv`
- `computational/results/density/predictions.csv.gz`
- `computational/populations/removal_definitions.json`

python commands/review_package.py secondary --csv DATA.csv.zip --out NEW_RUN

## Main Table 7

Optimizer and boundary events

- `computational/results/benchmark/solver_status_summary.json`
- `computational/results/benchmark/nlls_start_records.csv.gz`
- `computational/results/benchmark/geometric_predictions.csv.gz`

python commands/review_package.py primary --csv DATA.csv.zip --out NEW_RUN

## Main Figure 1

Raw-WCL empirical error distributions

- `computational/results/benchmark/geometric_predictions.csv.gz`
- `manuscript/figures/F1_assignment_ecdf.pdf`
- `computational/src/secondary/code/make_figures.py`

python commands/review_package.py figures --out NEW_FIGURES

## Main Figure 3

Unchanged CSV reception census

- `computational/src/secondary/inputs/reception_census.csv`
- `computational/src/secondary/inputs/release_reception_counts.csv`
- `computational/results/join/construction_summary.json`
- `manuscript/figures/F2_observed_receptions.pdf`

python commands/review_package.py core --csv DATA.csv.zip --json DATA.json.zip --out NEW_RUN; then python commands/review_package.py figures --out NEW_FIGURES

## Supplement Table S1.2

Complete identity and coverage resource

- `computational/data_products/receiver_crosswalk.csv`
- `computational/data_products/receiver_crosswalk.json`
- `computational/data_products/identities44.json`
- `computational/results/join/column_evidence.csv`
- `computational/results/join/alignment.csv.gz`

python commands/review_package.py core --csv DATA.csv.zip --json DATA.json.zip --out NEW_RUN

## Supplement Tables S2.1–S2.2 / S3.2

Exact execution contracts

- `computational/src/primary/code/evaluator_stable.py`
- `computational/src/primary/snapshots/baseline_001_160826.py`
- `computational/environment/executed_environment.json`
- `computational/environment/least_squares_signature_and_version.json`
- `computational/populations/rssfit_receiver_traversal.csv`
- `computational/populations/rssfit_ordered_fit_inputs.csv.gz`

Source/ordering specification; core verifies receiver-input order; primary replays the coordinate fit.

## Supplement S3

Ordered source populations and exclusions

- `computational/populations/working_source_ledger.csv.gz`
- `computational/populations/primary_role_ledger.csv.gz`
- `computational/populations/temporal_role_ledger.csv.gz`
- `computational/populations/geographic_definitions.json`

Core independently checks the primary selections; primary/secondary execute the documented population recipes.

## Supplement S4 / historical common-27

Historical-population stable-map bridge and exclusion

- `computational/results/prepared/common27_stable_bridge.csv`
- `computational/results/benchmark/anomaly_decomposition.csv`
- `computational/data_products/metadata_common27.json`
- `computational/data_products/rssfit_common27.json`
- `computational/populations/historical_common27_rows.csv`

python commands/review_package.py primary --csv DATA.csv.zip --out NEW_RUN

## Supplement S5.1

Endpoint counts in both source representations

- `computational/results/join/construction_summary.json`
- `computational/results/join/surplus_json_records.json`

python commands/review_package.py core --csv DATA.csv.zip --json DATA.json.zip --out NEW_RUN

## Supplement S5.2

Stable-map matched residual diagnostic

- `computational/results/residual_version/matched_links.csv.gz`
- `computational/results/residual_version/summary.json`
- `computational/src/secondary/code/reconcile_residuals.py`

python commands/review_package.py secondary --csv DATA.csv.zip --out NEW_RUN

## Supplement Table S6.1

Geographic contrasts and dependence sensitivity intervals

- `computational/results/geography/primary_intervals.csv`
- `computational/results/geography/calibration_counts.csv`
- `computational/results/geography/definitions.json`

python commands/review_package.py secondary --csv DATA.csv.zip --out NEW_RUN

## Supplement Table S6.2

Every six-receiver subset

- `computational/results/density/per_draw_summary.csv`
- `computational/results/density/conditional_intervals.csv`
- `computational/results/density/draw_definitions.json`

python commands/review_package.py secondary --csv DATA.csv.zip --out NEW_RUN

## Supplement Table S6.3

Original-timestamp temporal comparison

- `computational/results/temporal/summary.csv`
- `computational/results/temporal/predictions.csv.gz`
- `computational/results/temporal/definitions.json`
- `computational/results/inference/paired_intervals.csv`

python commands/review_package.py primary --csv DATA.csv.zip --out NEW_RUN

## Supplement S6.3 matched-map bridge

Conditional recovered versus metadata reference bridge

- `computational/results/continuity/matched_temporal_bridge_summary.csv`
- `computational/results/continuity/matched_temporal_bridge_predictions.csv.gz`
- `computational/results/continuity/matched_temporal_bridge_block_intervals.csv`
- `computational/src/join_and_continuity/continuity_and_bridge.py`
- `computational/src/join_and_continuity/bridge_block_sensitivity.py`

python commands/review_package.py continuity --csv DATA.csv.zip --out NEW_RUN

## Supplement Table S6.4

Exploratory temporal mean and tail evidence

- `computational/results/continuity/descriptive_other_temporal_estimands.csv`
- `computational/results/continuity/exploratory_temporal_mean_p90_intervals.csv`
- `computational/src/join_and_continuity/temporal_other_metrics.py`

python commands/review_package.py continuity --csv DATA.csv.zip --out NEW_RUN

## Supplement S7

Actual validation records

- `computational/provenance/prior_receipts/primary/validation_results.json`
- `computational/provenance/prior_receipts/secondary/VALIDATION.json`
- `computational/commands/verify_evidence.py`

python commands/review_package.py verify --out NEW_CHECK; new replay receipts in checks/ are separately scoped.

## Supplement S8 / S9

Current/historical execution contracts and source identity.

- `provenance/LEGACY_CORRECTION_RECORD.md`
- `provenance/CODE_ATTRIBUTION.md`
- `provenance/ANONYMIZATION_SCOPE.md`

Full attributed development history is preserved in the editor-only master, not supplied as a journal referee report.

## Main Table 3; Supplement Table S4.1

Frozen matched33 geometry and domain summary

- `geometry/results/frozen_geometry/receiver_geometry33.csv`
- `geometry/results/frozen_geometry/rssfit_search_boxes41.csv`
- `geometry/results/frozen_geometry/coordinate_summary.json`

python commands/review_package.py geometry --csv DATA.csv.zip --out NEW_GEOMETRY

## Main Figure 2

Complete coordinate overview including BS71

- `manuscript/figures/G1_full_coordinate_overview.pdf`
- `geometry/results/frozen_geometry/receiver_geometry33.csv`
- `geometry/results/frozen_geometry/calibration_locations_for_plot.csv.gz`
- `commands/make_revision_figures.py`
- `presentation/FIGURE_RECEIPT.json`

python commands/review_package.py figures --out NEW_RUN (presentation only; original frozen inputs unchanged)

## Supplement Table S1.3

Exact primary assignments; display precision is explicit

- `computational/data_products/metadata33.json`
- `computational/data_products/rssfit33.json`

python commands/review_package.py tables --out NEW_TABLES

## Supplement Table S4.2; Main §5.2

Source-defined BS71 footprint and recorded exclusion

- `geometry/results/frozen_geometry/BS71_description.json`
- `geometry/results/frozen_geometry/BS71_distance_summary.csv`
- `geometry/results/frozen_geometry/BS71_source_rows_and_distances.csv.gz`
- `geometry/results/frozen_geometry/BS71_existing_exclusion_summary.csv`
- `geometry/results/frozen_geometry/BS71_existing_NLLS_change_records.csv.gz`

python commands/review_package.py geometry --csv DATA.csv.zip --out NEW_GEOMETRY

## Supplement Figures S2–S3

Every existing draw, removal and selection components

- `manuscript/figures/G3_density_FP.pdf`
- `manuscript/figures/G4_density_MinMax.pdf`
- `geometry/results/frozen_geometry/existing_density_decomposition.csv`
- `presentation/PLOTTED_REMOVAL_VALUES.csv`
- `commands/make_revision_figures.py`

python commands/review_package.py figures --out NEW_RUN; 64 saved method/draw rows, no new subsets or results

## Supplement Tables S1.1/S1.4/S3.1

Coverage, roster terminology and exact population products

- `computational/data_products/receiver_crosswalk.csv`
- `computational/populations/primary_role_ledger.csv.gz`
- `computational/populations/temporal_role_ledger.csv.gz`
- `manuscript/Supplementary_material_without_author_details.md`

Core checks primary population identities; secondary/temporal source records specify remaining cohorts.

## Current integrated documents

Canonical Markdown, generated TeX/PDF, local version checks

- `manuscript/Manuscript_without_author_details.md`
- `manuscript/Supplementary_material_without_author_details.md`
- `commands/build_documents.py`
- `commands/check_submission.py`

python commands/review_package.py documents --out NEW_BUILD

## Supplement S2.7 / main 5.3 / supplement S6.1

Exact geographic-nearest-database convention and corrected displayed rounding

- `diagnostics/nearest_geographic_summary.csv`
- `diagnostics/nearest_geographic_distances.csv.gz`
- `diagnostics/SOURCE_DEFINITIONS.json`

python commands/review_package.py diagnostics --csv DATA.csv.zip --out NEW_OUTPUT

## Supplement S5.2

Zero-centred residual-tail fraction with pooled-mean standard deviation

- `diagnostics/residual_tail_definition.json`
- `computational/results/residual_version/matched_links.csv.gz`

python commands/review_package.py diagnostics --csv DATA.csv.zip --out NEW_OUTPUT

## Supplement Figure S1

City-scale detail with same catalogue/RSSFIT encoding as the full-extent main Figure 2

- `manuscript/figures/G5_city_coordinate_detail.pdf`
- `presentation/FIGURE_RECEIPT.json`
- `computational/data_products/metadata33.json`
- `computational/data_products/rssfit33.json`
- `commands/make_revision_figures.py`

python commands/review_package.py figures --out NEW_RUN (presentation only; original frozen inputs unchanged)

## Supplement Table S6.2a

All 32 reduced-roster survivor counts

- `geometry/results/frozen_geometry/existing_density_decomposition.csv`

Existing per-draw record; no new receiver subset.

## Supplement Table S1.5; Main Sections 1–2

Resource utility and focused record-level adjacent-artifact comparison

- `sources/ARTIFACT_COMPARISON.md`
- `sources/EXTERNAL_SOURCE_CHECK.json`
- `computational/data_products/receiver_crosswalk.csv`

Primary deposit descriptions and file inventories checked; DAE payload contents unverified. No external code execution.

## Main 3.5, Table 2; Supplement S4 and all resampling captions

Conditional bootstrap sensitivity target; numerical interval arrays unchanged

- `provenance/RESAMPLING_INTERPRETATION.md`
- `computational/results/inference/paired_intervals.csv`

Semantic clarification plus preserved stored arrays; no new resampling scheme.

