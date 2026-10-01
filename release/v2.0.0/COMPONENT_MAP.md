# Public v2.0.0 scientific component map

This staging release extends the frozen public v1.0.0 repository with the
post-rejection scientific work that underlies the current manuscript.

Public-facing components:
- `resource_validation/` — objective/resource validation and bounded diagnostics.
- `representation_population/` — representation replay and matched-population evidence.
- `fitting_validation/` — grouped/spatial fitting-validation study.
- `map_selection/` — fixed-candidate map-selection study.
- `portability/` — exact correspondence, conformance tests, and workflow preservation.
- `reliability/native/` — native DAE reliability/calibration execution and saved outputs.
- `reliability/transfer_temporal/` — DSI transfer and chronological LoRaWAN analyses.
- `reliability/posthoc/` — equal-acceptance/post-hoc saved-output audit.
- `reliability/interfaces/` — dependency/interface reconstruction and contract tests.

Historical execution identifiers retained inside individual component evidence
are provenance labels, not the public release title or manuscript version.

Third-party source payloads are not relicensed by Paper A. Where reexecution
requires them, the component's `EXTERNAL_INPUTS.md` gives source DOI and pinned
identity information.
