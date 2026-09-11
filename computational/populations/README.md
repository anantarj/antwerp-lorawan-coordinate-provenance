# Ordered population identities

The source identity is `(CSV SHA-256, zero-based data-row index)`. The CSV hash is
870abe60a4bd81f31ede6f269b6bc6329e05d2731343dff7015bae1a61218446.
Physical CSV line number = data-row index + 2. `working_index0` instead indexes
the retained 55,375 messages in original CSV order; these indices are not interchangeable.

`working_source_ledger.csv.gz` records every working row, shuffle and historical
selection ranks, content hashes and coordinates. `primary_role_ledger.csv.gz`
contains exact current role order. Separate `*_rows.csv` views expose ordered
calibration, primary evaluation, fingerprint database, exclusions and temporal
memberships. `historical_common27_rows.csv` is a different experiment.

`geographic_definitions.json` contains all nine ordered training samples,
intercepts, support restrictions, and both fixed evaluation populations. Its
`geography_training_*_rows.csv` views have their region/seed in
`geography_training_index.json`. `removal_definitions.json` includes every
retained receiver subset and its exact survivors.

`rssfit_receiver_traversal.csv` and `rssfit_ordered_fit_inputs.csv.gz` are F2
reconstructions of the unchanged sampling/filtering input sequence, checked against
all saved initialization identities and RSSI values. They do not refit coordinates.
Receiver order follows first encounter in the shuffled calibration-message and
stable descending-RSSI reception traversal. It is not numeric receiver order.
The shared random generator is advanced only by receivers requiring subsampling.

`*_rows.csv` files are convenience views, not new scientific populations. The
JSON extra record is not appended to any CSV population.
