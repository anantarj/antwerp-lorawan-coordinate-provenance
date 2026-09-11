# F3 frozen-artifact description protocol

Date: 6 September 2026. Fixed before calculating the F3 descriptive results.

## Scope and protected inputs

Describe the frozen R3-F2 maps and populations. No RSSFIT optimization, localization
optimization, parameter search, alternative coordinate assignment, or new survey
is undertaken. R2 documents, F2 archive and public raw inputs are read only.
This is a retrospective descriptive audit, not a preregistered scientific trial.

Input authority: the F2 computational supplement, SHA-256
`4dc48ffeed3b80c8aaa6642ca595e81118783d4393954924b204dba78b6eaaea`.
CSV payload SHA-256:
`870abe60a4bd81f31ede6f269b6bc6329e05d2731343dff7015bae1a61218446`.
Frozen RSSFIT41 SHA-256:
`93e4509d1e7300b92a0a6b3dabbfab251237ea686e4cdd786986419b755f57d6`.
The complete F2 manifest is checked, while the exact consumed members are listed
separately in the F3 receipt. This verifies identity, not the scientific truth of
all inherited results.

## 1. Coordinate-discrepancy description

Use the same primary 33 receiver identities, their rounded catalogue-projected
coordinates in EPSG:32631, and the full-precision frozen RSSFIT coordinates.
Compute Euclidean distances receiver by receiver. Report unweighted minimum,
median, p90 (linear interpolation), and maximum. Report the primary 33 and the
explicit 32-receiver subset excluding BS71 separately; neither replaces the other.
Retain calibration support, actual fit-subset size, and all per-receiver values.
Call these discrepancies relative to a catalogue reference, not surveyed physical
position errors. No confidence intervals are appropriate for this fixed roster
census unless a separate sampling target is specified; none is introduced here.

## 2. Receiver-fitting search boxes

Reconstruct calibration membership/order from the raw CSV with the existing
seed-1 shuffle. Reconstruct first-encounter receiver traversal, the shared seeded
subsampling (at most 2,000), and the existing 0.75 quantile/filter branch. Compare
every retained fit record with the F2 ordered-input ledger before computing boxes.
Each box is the minimum/maximum of the actual retained transmitter positions,
expanded by exactly 2,000 m on each side. No coordinate fit is rerun.

Export all 41 fit boxes. Report catalogue membership only where reference
coordinates exist, with the primary 33 distinguished. A point is numerically on a
boundary if its minimum nonnegative margin is <=1e-7 m; outside means a violation
>1e-7 m. Also report fitted points <=60 m from a side (one final axial pattern-search
step), explicitly a descriptive proximity flag and not an optimizer-failure test.
Give exact margins so the flag is not the only evidence. These boxes are NOT the
NLLS transmitter-localization box. References outside a fit box were unavailable
to that constrained fit; this alone does not identify their contribution to the
localization-error contrast. Do not enlarge boxes or refit.

## 3. BS71 factual description

Read identifier and source latitude/longitude from the delivered crosswalk and
catalogue; check projection against the preserved metadata map. Summarize distances
from that fixed catalogue point to: (a) all 16,612 calibration transmitter positions;
(b) calibration records received by BS71; (c) working-census records received by
BS71; (d) all valid-coordinate CSV records received by BS71. Give each population's
exact count and minimum/median/p90/maximum, and the distance to its coordinate mean.
Also give distance to the closed axis-aligned calibration bounding rectangle,
explicitly NOT to an assumed network coverage region. Export the relevant row IDs.
Use these as a new retrospective geometric description, not the recovered historical
flagging rule or proof of catalogue error. Keep the primary reference unchanged.

Recalculate the existing BS71 exclusion summary from saved predictions. Distinguish
lost eligibility from same-survivor changes. Recheck the published count of changed
NLLS results on non-BS71 survivor messages using the producer's >1e-7 m absolute
change in positional error. Also compute the Euclidean prediction-position change
at the same tolerance and state whether the two counts coincide. Do not execute
NLLS or change its return policy.

## 4. Raw-centroid identity and explanatory limits

On all paired primary messages, independently evaluate the normalized raw-RSSI
weights and verify that the saved position shift equals the weighted sum of receiver
coordinate differences within 1e-7 m absolute tolerance. This is an algebra/source
consistency check, not a new localization benchmark or a causal decomposition of
median errors. The triangle inequality may bound displacement; it does not require
localization error to increase.

## 5. Existing removal/selection display

Use every existing reduced-roster draw for fingerprinting and Min-Max (eight draws
at each of 23,16,10,6 receivers). Verify each draw's additive median accounting;
show removal and selection components without pooling messages across draws or
adding medians of different components. Preserve all tiny strata and label plots
as descriptive views of existing outputs. No new subset or inference is selected.

## 6. Validation and deliverables

Use exact comparisons for IDs/RSSI and immutable payloads; absolute 1e-8 m for
reconstructed projection agreement and 1e-7 m for arithmetic/position identities.
Independently check distances with scalar hypot and the box calculations with
constructed inside/on/outside cases. Reject wrong source hashes and overwriting
output. Repeat the F3 descriptor in a new directory and compare its numerical
outputs. Export readable tables, machine-readable rows and summaries, runnable
code, actual receipts and coordinated insertion drafts. Any discrepancy is logged;
tolerances are not increased to force agreement. F4 integration and final external
review access remain separate tasks.
