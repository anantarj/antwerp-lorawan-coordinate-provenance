# Start here

## 1. Obtain the external data

Download the original Antwerp LoRaWAN v1.3 CSV and message JSON from:

https://doi.org/10.5281/zenodo.3904158

The replay tools verify their expected SHA-256 fingerprints before scientific use.

## 2. Create a Python environment

The recorded environment and package/version evidence are under
`computational/environment/`.

For a lightweight verification environment, install the scientific dependencies
documented there. Do not interpret successful installation on one machine as
independent replication of the deployment.

## 3. Verify packaged evidence

From the repository root:

```bash
python computational/commands/paper_a.py verify --out ../paper_a_verify
python computational/commands/paper_a.py tables --out ../paper_a_tables
```

These routes use saved evidence. They do not refit coordinates or rerun all
localization producers.

## 4. Reconstruct the raw identity join and frozen-map centroid

```bash
python computational/commands/paper_a.py core \
  --csv /path/lorawan_antwerp_2019_dataset.csv.zip \
  --json /path/lorawan_antwerp_2019_dataset.json.txt.zip \
  --out ../paper_a_core
```

The output directory must not already exist and must be outside the repository.

## 5. Full retained producers

```bash
python computational/commands/paper_a.py primary \
  --csv /path/lorawan_antwerp_2019_dataset.csv.zip \
  --out ../paper_a_primary --workers 4

python computational/commands/paper_a.py secondary \
  --csv /path/lorawan_antwerp_2019_dataset.csv.zip \
  --out ../paper_a_secondary
```

Additional temporal/geometry/diagnostic routes are documented in the included
README files and source tree.

## 6. Trace a reported result to evidence

Start with:

`table_figure_index/INDEX.md`

It maps the retained manuscript tables/figures and supplementary groups to the
saved artifacts and producer routes.

## Reproducibility boundary

A saved-output check, a frozen-map replay, a coordinate refit, and a full producer
execution are different scopes. The repository preserves those distinctions.
