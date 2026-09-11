# Receiver resource schema

`receiver_crosswalk.json` is the typed version; the CSV has one row per active BS
column. Preserve `bs` and `gateway_id` as strings. The identifier is the exact
released identifier string; do not expand it into an assumed 64-bit EUI, change
case, or remove leading zeroes. All 44 identities are included.

- `release_receptions`: non-missing reception records across all 130,429 CSV rows.
- `calibration_receptions`: records in the fixed 16,612-message calibration set;
  these are **not** the old file's unverified vote counts.
- `full_identity_candidates`: complete matched-sequence identity candidates.
- `identified_on_calibration_only`: a unique active identity is available using
  calibration records only; full-file identities include three sparse columns
  not identifiable there.
- `outside_calibration_mismatches`: mismatches when a calibration-derived identity
  is checked outside calibration; null means no calibration identity to validate,
  not zero evidence of mismatch.
- `catalogue_present`, `catalogue_latitude`, `catalogue_longitude`: membership and
  values from the frozen version-1.3 catalogue. Unavailable coordinates are null
  (empty CSV cells), never zero coordinates.
- `catalogue_x_m`, `catalogue_y_m`: EPSG:32631 easting/northing in metres, projected
  from EPSG:4326 using longitude/latitude axis order and rounded to 0.1 m, matching
  the saved reference. They are catalogue assignments, not resurveyed truth.
- `in_metadata33`, `in_common27`, `in_transfer29`: exact retained analysis-roster
  flags. Transfer29 is metadata-derived and is not historical recovered29.
- `in_historical_recovered29`: membership only, not an assertion that its coordinates
  are the metadata-derived coordinates in this row.
- `rssfit_x_m`, `rssfit_y_m`, `has_rssfit_coordinate`: values from the unchanged
  stable 41-coordinate fit, with full precision in JSON. These may exist even
  when a catalogue coordinate does not.
- `primary_selection_count`: number of the 2,495 primary queries selecting that
  receiver under the fixed metadata33 roster; this descriptive count was not used
  to choose the roster or identity.

`metadata33.json`, `rssfit33.json`, `rssfit_stable41.json`, the no71 maps and
historical_recovered29.json retain the exact copied coordinate values. Derived
common27 and transfer29 JSON views do not change their parent coordinates.

The 33-receiver roster is retained for continuity. Its identities are verified
from calibration metadata and every member has at least 20 calibration receptions.
That observed property does not reconstruct the historical selection rule or
establish a prospective/optimal threshold. The calibrator's 10-reception minimum
is a separate implementation condition. No 35- or 39-receiver benchmark is
silently substituted.
