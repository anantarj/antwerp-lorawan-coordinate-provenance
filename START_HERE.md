
# Start here

These are the public reproducibility resources for
*Receiver Provenance, Population Selection, and Reliability Trade-offs in RSSI Localization*.

## 1. Verify the packaged public release

From the repository root:

    python release/v2.0.0/verify_public_v2.py

This performs the public manifest check, the retained v1 saved-evidence
verification, and the packaged unit/contract suites. It does not refit every
model or download third-party data.

Saved-output verification receipts produced during release preparation are in:

`release/v2.0.0/verification/`

## 2. Historical Antwerp reconstruction

Original Antwerp LoRaWAN v1.3 measurements are obtained separately from:

DOI `10.5281/zenodo.3904158`

The retained v1 reconstruction route remains:

    python computational/commands/paper_a.py core       --csv /path/lorawan_antwerp_2019_dataset.csv.zip       --json /path/lorawan_antwerp_2019_dataset.json.txt.zip       --out ../paper_a_core

## 3. Post-rejection scientific components

- `representation_population/`
- `resource_validation/`
- `fitting_validation/`
- `map_selection/`
- `portability/`
- `reliability/native/`
- `reliability/transfer_temporal/`
- `reliability/posthoc/`
- `reliability/interfaces/`

Each component preserves the code/results/receipts needed for its public scope.
Where a full reexecution requires third-party inputs, consult the component's
`EXTERNAL_INPUTS.md` and source-identification checks.

## 4. Reproducibility boundary

These are distinct operations:

- validating package hashes;
- checking retained saved outputs;
- executing unit/contract tests;
- replaying a frozen computation;
- reconstructing source relations from raw measurements;
- rerunning a model/calibration experiment.

A successful saved-output or unit-test verification is not described as an
independent empirical replication.

## 5. Release provenance

- exact version DOI: `10.5281/zenodo.23083321`
- concept DOI: `10.5281/zenodo.22143329`
- historical v1 DOI: `10.5281/zenodo.22703158`
- repository: `https://github.com/anantarj/antwerp-lorawan-coordinate-provenance`
- intended tag: `v2.0.0`

See `release/v2.0.0/` for the public release map and provenance.
