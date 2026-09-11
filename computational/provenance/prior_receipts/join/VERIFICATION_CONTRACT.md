# Continuity verification contract

Date: 5 September 2026. This is a post-review verification prompted by the author's questions, not a retrospective preregistration.

1. Preserve the checksum-pinned CSV (130,429 data records; 55,375 working records) and every historical map and output. Do not reconcile the extra JSON record by modifying either representation.
2. Verify source payload checksums against the public v1.3 record and bundle snapshots against uploaded source files.
3. Construct a new column-to-gateway mapping using only CSV and JSON serialization/reception data. Do not load the legacy cleaned mapping, receiver coordinates or localization errors during construction. Use exact full reception-vector correspondence, including missingness, after collision-checked message-group alignment. Also identify assignments from the existing calibration records alone and verify outside them. Freeze this new output before comparing with legacy artifacts. Historical vote counts are not reconstructed by this procedure.
4. Independently recompute primary result summaries, coordinate errors, raw WCL estimates, solver-status counts, source-row timestamps and paired population identities from underlying records. Re-execute a deterministic sample of original optimizer calls to check instrumentation transparency. Do not describe these tests as complete external replication.
5. Resolve temporal comparability with a new bridge: original timestamps, equal calibration budgets, the same 1,200 requested late messages as A4a, a fixed common receiver roster, identical surviving messages, and identical legacy estimator kernels under both reference assignments. Change only the map/intercepts within each fixed calibration treatment. Report both map arms regardless of direction. Preserve original and revised DIFF zero-pair policies separately.
6. Quantify the bridge's early-versus-interleaved median effects with paired message resampling (6,000 draws, seed 20260905). These are conditional, exploratory sensitivity intervals, not simultaneous confirmatory inference or evidence of equivalence.
7. Interpret accuracy, boundary proximity, optimizer termination and computational runtime as distinct quantities. Do not substitute one for another or compare new and old cohorts as the same experiment.

## Uniform dependence-sensitivity follow-up

After the matched bridge's message-level intervals were computed, apply the same pre-existing 500 m, 1,000 m and UTC-day cluster schemes to **all** bridge methods and both maps, not selectively to a favorable arm. Use 6,000 draws and seed 20260905. This timing is explicit: the follow-up is not newly preregistered evidence. Its purpose is to avoid treating a narrow message interval as universal temporal evidence.

## Nonmedian temporal follow-up

The independently rechecked primary temporal predictions show that close medians coexist with increased ABS mean and p90 errors. To avoid the inverse overclaim that there is no temporal deterioration, calculate mean- and p90-error contrasts for every temporal method, using the same four paired/message and spatial/day schemes, 6,000 draws, seed 20260905. This follow-up is explicitly exploratory and initiated after inspecting descriptive nonmedian summaries. Do not present it as an untouched confirmatory test, choose only favorable metrics, or infer physical ageing independent of route/calibration distribution.
