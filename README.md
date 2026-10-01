
# Receiver Provenance, Population Selection, and Reliability Trade-offs in RSSI Localization

Reproducibility resources supporting:

**Receiver Provenance, Population Selection, and Reliability Trade-offs in RSSI Localization**

**Author:** Ananta Ranjan, Independent Researcher  
**ORCID:** https://orcid.org/0000-0002-1105-0666

This repository provides author-created code, derived data products, saved
experimental outputs, provenance records, population definitions, protocols,
and verification tools supporting the article.

Public release: **v2.0.0**  
Exact Zenodo version DOI: **https://doi.org/10.5281/zenodo.23083321**  
Zenodo concept DOI: **https://doi.org/10.5281/zenodo.22143329**

## Scientific scope

The resource examines how receiver attribution, representation continuity,
population selection, quantity semantics, and reliability/calibration choices
affect reported RSSI-localization results.

The principal v2 components are:

- `resource_validation/` — bounded objective/resource diagnostics and validation records.
- `representation_population/` — representation replay and matched-population analyses.
- `fitting_validation/` — grouped and spatial fitting-validation experiments.
- `map_selection/` — fixed-candidate map-selection analysis.
- `portability/` — exact correspondence, ambiguity/refusal tests, and workflow preservation.
- `reliability/native/` — native DAE reliability/calibration execution and saved outputs.
- `reliability/transfer_temporal/` — DSI Wi-Fi transfer and chronological LoRaWAN analyses.
- `reliability/posthoc/` — equal-acceptance/post-hoc analysis.
- `reliability/interfaces/` — dependency and numerical-interface verification.
- `release/v2.0.0/` — release provenance, verification receipts, and release metadata.

The resource does **not** claim a universally superior localizer, a general
coordinate-recovery algorithm, a new general conformal method, physical
authentication of gateway coordinates, or universal transfer of reliability
relationships.

## Start here

See [`START_HERE.md`](START_HERE.md).

The public verification route is:

    python release/v2.0.0/verify_public_v2.py

This checks the current public manifest, the retained v1 saved-evidence route,
and the public unit/contract suites. Saved-output verification receipts for the
post-rejection studies are under `release/v2.0.0/verification/`.

## External inputs

Third-party raw measurements and externally authored source material are not
relicensed by this repository.

Principal external records:

- Antwerp LoRaWAN v1.3 measurements: DOI `10.5281/zenodo.3904158`
- DAE code/resources: DOI `10.5281/zenodo.5589651`
- DSI Wi-Fi dataset: DOI `10.5281/zenodo.3778646`

Exact source identities and execution requirements are recorded in the
component checks and `EXTERNAL_INPUTS.md` files.

## Historical release

The previous exact public release remains immutable at:

- GitHub tag `v1.0.0`
- DOI `https://doi.org/10.5281/zenodo.22703158`

Version 2.0.0 updates release-facing metadata and adds the post-rejection
scientific components. Historical scientific records and filenames are retained
where they are part of provenance.

## Licensing

- Author-created software: **MIT License**.
- Author-created documentation and derived non-code artifacts: **CC BY 4.0**.
- Third-party source data, software, and other external material retain their
  original terms and are not relicensed by this repository.

See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## Funding

No funding was received for this work.

## Citation

See [`CITATION.cff`](CITATION.cff). For exact reproducibility, cite the
version DOI `10.5281/zenodo.23083321` rather than only the concept DOI.
