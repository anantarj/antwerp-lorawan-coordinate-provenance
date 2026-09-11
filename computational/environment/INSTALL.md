# Numerical environment

Recorded producer and F2 execution: CPython 3.13.5, NumPy 2.3.5, pandas 2.2.3,
SciPy 1.17.0, pyproj 3.7.2, PROJ 9.5.1. The separately included earlier producer
JSON records remain authoritative for their own execution scope.

```sh
python3.13 -m venv ../paper_a_venv
. ../paper_a_venv/bin/activate
python -m pip install -r environment/requirements-numerical.txt
python commands/paper_a.py verify --out ../paper_a_evidence_check
```

The commands set OPENBLAS_NUM_THREADS, OMP_NUM_THREADS, MKL_NUM_THREADS to 1,
PYTHONHASHSEED to 0, and suppress bytecode writes. The raw-WCL replay tolerance
is an absolute 1e-7 m, fixed before comparison. Byte-equal producer records in
the current environment do not promise bitwise agreement on other systems.

This install recipe has not itself been executed against a fresh package index in
F2; the producers are replayed in the recorded available environment. Numerical
and system-library versions, not just seeds, affect repeatability. No historical
Python 3.11 environment reproduction is claimed. Figure regeneration additionally
uses matplotlib; PDF document builds use Pandoc/XeLaTeX. ReportLab is needed only
to rebuild this programmatically generated resource addendum, not for experiments.
