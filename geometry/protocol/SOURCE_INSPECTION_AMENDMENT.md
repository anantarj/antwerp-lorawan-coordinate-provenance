# Pre-calculation clarification

The initial F3 protocol described the published 1,908 count as a Euclidean
position-change test. Reading `src/primary/code/validate.py` lines 39–45 before
computing F3 outcomes shows that its actual predicate is the absolute change in
**positional error** >1e-7 m. F3 will recompute that exact predicate and separately
report the position-vector displacement test. This is a source-definition
clarification, not a tolerance or outcome-driven change. The initial protocol
SHA-256 was dceecaba3073ebc42cb557816cec7628699f542d1f62ae57b55fe6ff6ef30a4e.
No F3 numerical outcomes had yet been calculated.
