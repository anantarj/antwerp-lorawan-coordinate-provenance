# Antwerp LoRaWAN coordinate provenance and benchmark audit

Reproducibility resources for:

**Published, Unjoined: Coordinate Provenance and Reception Support in a Public LPWAN Localization Benchmark**

**Author:** Ananta Ranjan, Independent Researcher  
**ORCID:** https://orcid.org/0000-0002-1105-0666

This repository supplies the receiver-identity crosswalk, coordinate assignments,
ordered experimental populations, operative analysis sources, retained numerical
outputs, and scoped verification/replay tools used by Paper A.

## Scientific scope

The repository supports a release-specific audit of the public Antwerp LoRaWAN
v1.3 localization benchmark. Its central reusable product is an explicit bridge
from the tabular `BS` receiver columns to the gateway identifiers and catalogue
coordinates in the released JSON/catalogue representations.

The main coordinate-substitution case study is deliberately bounded: it evaluates
one specified RSSI-fitted coordinate assignment and does **not** claim that its
error is typical, unavoidable, or representative of optimal coordinate recovery.

## Start here

See [`START_HERE.md`](START_HERE.md).

The shortest saved-evidence check is:

```bash
python computational/commands/paper_a.py verify --out ../paper_a_verify
```

With the original LoRaWAN v1.3 CSV and JSON payloads:

```bash
python computational/commands/paper_a.py core \
  --csv /path/lorawan_antwerp_2019_dataset.csv.zip \
  --json /path/lorawan_antwerp_2019_dataset.json.txt.zip \
  --out ../paper_a_core
```

The `core` route reconstructs the raw CSV–JSON identity join and evaluates the
frozen-map raw weighted centroid. It does not refit receiver coordinates.

## External input data

The raw measurement payloads are **not redistributed**.

Source dataset: Aernouts et al., LoRaWAN Antwerp v1.3  
DOI: https://doi.org/10.5281/zenodo.3904158

Expected SHA-256 payloads:

- CSV: `870abe60a4bd81f31ede6f269b6bc6329e05d2731343dff7015bae1a61218446`
- JSON: `f2f1fbd478cdef2b76fb8e3aae33751d332b50fc8546684d8e73fdb1505451cb`
- gateway catalogue: `507f9bb266d23f59fdc2b743447cecf9c909290536e24de3f9483aaa178d374d`

## Repository contents

- `computational/data_products/` — receiver identities, coordinate products, and coverage flags.
- `computational/populations/` — ordered calibration/evaluation/database identities.
- `computational/src/` — operative scientific source code and preserved source snapshots.
- `computational/results/` — saved predictions, solver records, inference arrays, and controls.
- `computational/environment/` — recorded execution environment and installation information.
- `geometry/` — frozen coordinate-domain diagnostics and BS71 sensitivity records.
- `diagnostics/` — definition checks for selected secondary diagnostics.
- `table_figure_index/` — claim/table/figure-to-artifact routes.
- `checks/` — scoped verification receipts preserved from the submission package.

## Zenodo

Paper A concept DOI: https://doi.org/10.5281/zenodo.22143329

The **exact version DOI corresponding to the public repository release must be
inserted here before the public `v1.0.0` tag is frozen.** Do not substitute an
older Paper A version merely because the concept DOI resolves to it.

## Licensing

- Author-created code: **MIT License**.
- Author-created documentation and derived non-code artifacts: **CC BY 4.0**.
- Third-party source data and other third-party materials retain their own terms
  and are not relicensed by this repository.

See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

## Funding

No funding was received for this work.

## AI disclosure

The manuscript contains the author-approved generative-AI disclosure. It is not
reproduced here as a substitute for the article's declaration.

## Citation

See [`CITATION.cff`](CITATION.cff). The exact Zenodo version DOI should be added
after the new Paper A Zenodo version is reserved.
