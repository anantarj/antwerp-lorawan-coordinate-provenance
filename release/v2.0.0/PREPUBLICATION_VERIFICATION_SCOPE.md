# Prepublication verification scope

The public v2 staging tree is a publication subset, not a byte-for-byte unpacking
of every internal development package.

The following can be rerun from the public subset without third-party raw payloads:
- retained v1 saved-evidence verifier;
- public unit/contract suites;
- map-selection saved-output verifier;
- native reliability saved-output verifier;
- transfer/temporal saved-output verifier.

Other historical verification receipts are retained as evidence but some complete
reexecutions require separately obtained third-party source data or the full
internal parent package. They must not be represented as runnable from the public
subset alone.

The final public manifest, DOI binding, and repository metadata are intentionally
deferred until the Zenodo v2 DOI has been reserved.
