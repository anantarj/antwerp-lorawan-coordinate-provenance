# A reader can preserve an experiment while changing its data representation

## Research task

An analyst already has a CSV-defined calibration/evaluation cohort. They need catalogue-backed gateway coordinates and must retain exactly the same source rows, receiver dimensions and selection/tie rule. Loading an independent JSON sample instead would not establish the same experiment, even if both samples have the same size.

## Executed chain

1. Check the source payload fingerprints. The existing CSV stays at 130,429 records, with 55,375 working records.
2. Reconstruct the CSV/JSON association using reception metadata and exact receiver RSSI/presence sequences, without using transmitter coordinates to select identities. Respect duplicate occurrence counts and keep the extra JSON record separate.
3. Consult the catalogue only after identity linkage. All 44 active receiver columns are identified; 39 have coordinates, while missing entries remain unavailable.
4. Read the existing ordered 2,495 primary CSV row IDs and the fixed 33-receiver roster. Preserve numerical-BS tie ordering when sorting raw RSSI.
5. Calculate the frozen catalogue-centroid once through CSV columns and once through JSON gateway identifiers, with the same validated row association and coordinate precision.
6. Use the same explicit row contract for interpreting existing receiver-removal outputs.

Results of steps 1–3: `raw_join/core/checks.json` and `raw_join/join/construction_summary.json`.
Results of steps 4–5: `representation_replay/REPLAY_RECEIPT.json` and the complete row-level replay CSV.
Step 6 uses the PR1 position-derived reconstruction, preserved under `../evidence/pr1/results/resource_demo/`.

## What the two representations produce

All 2,495 selected receiver/RSSI lists agree. Maximum difference between CSV-native and JSON-native positions is 0 m in the executed calculation. The metadata-centroid median is 480.08719486250845 m. Maximum displacement from the earlier saved centroid positions is 4.67e-9 m, within the specified numerical tolerance.

The replay uses the crosswalk and fresh alignment to access JSON, so it is a verification of representation consistency, not an independent field experiment. Two primary rows lie in repeated serialization groups. Their JSON row indices are occurrence representatives; no unique physical-event identity is asserted within such a group. Transmitter positions are checked only after alignment, not used to choose it.

This is a deliberately non-superiority result: the resource adds a validated, reproducible way to preserve an existing experiment. It does not make correct JSON-native access less accurate or newly create information absent from the original release.

## A consequential comparison error it makes inspectable

For the retained fingerprint draw `removal_16_4`, 1,276 of 2,495 parent messages survive the comparison eligibility rule:

| Calculation | Median error (m) |
|---|---:|
| Full roster, original parent | 219.29225648 |
| Full roster, exactly those survivors | 59.29562148 |
| Reduced roster, exactly those survivors | 75.77344187 |

The unseparated comparison says -143.51881461 m (apparent improvement). On the same survivors, removal instead changes error by +16.47782038 m (deterioration); the population-selection contribution is -159.99663500 m. These sum to the unseparated difference.

This example is shown alongside an enumeration of every retained reduced-roster draw, not selected as an unreported new hypothesis. Opposite signs occur in 2/32 fingerprint and 6/32 Min-Max point-estimate comparisons. The eight survivor counts are 1,374; 1,438; 1,069; 960; 807; 1,276; 25; and 12. The two tiny strata remain flagged. No inferential significance or general reversal frequency is claimed.

The previously discussed 23-receiver example is also preserved: parent 219.29 m, full-on-survivors 162.61 m, reduced-on-survivors 154.63 m. There the signs do not reverse, but population selection contributes 56.68 m of the 64.66-m apparent improvement.

## What is contributed and what is not

The deliverable is the source/identity/cohort contract and a reproducible use that exposes misleading numerical comparisons. Matching populations and the telescoping algebra are not newly invented statistical principles. This exercise does not show that any named previous publication made the unseparated comparison or that the resource alone clears an editorial novelty threshold.

## Misuse guards

Sixteen constructed tests exercise wrong row order, equal-sized different cohorts, duplicate row IDs, source mismatch, insufficient duplicate multiplicity, inconsistent reception maps, nonbijective identity mapping, leading-zero preservation, tie ordering, missing/nonfinite coordinates and elementary centroid identities. These are deliberately malformed examples/controls, not measurements of how often users make such errors.
