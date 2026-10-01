# MV1: interpretation of the locked protocol

The executable specification is `MECHANISM_VALIDATION_PROTOCOL.json`. Its hash and creation event are in `../checks/PROTOCOL_LOCK.json`. It was locked before the new split-specific coordinate fits and outcome evaluation; it is not an externally registered confirmatory protocol. Existing Paper A outcomes and the 19 September objective diagnostic were already known.

## Question and controls

Does replacing a receiver-specific retained-observation fitting box with the entire fitting-survey box change finite fitted geometry and its downstream usefulness? Does the fitted RSSI model predict internal validation observations better than a fitting-only constant-RSSI control when its intercept is frozen?

The experiment has four main arms: catalogue coordinate with training-only intercept, constant fitting RSSI, original-style local fit in NARROW, and original-style local fit in WIDE. The retained observations and exponent are matched across the three geometric arms. Constant RSSI is a prediction control only; it is never assigned a location or used as a localization benchmark.

Primary validation uses all valid held-out receptions, not just strong receptions selected using validation RSSI. Intercepts and RSSI-selection thresholds are not recomputed there. The supplement will distinguish predictive validation from the training loss used to select a coordinate.

## Why the wider domain is defensible—and limited

For receiver i, NARROW is the bounding box of its retained fitting transmitters plus the inherited 2,000-m margin. WIDE is the bounding box of all fitting-side transmitters, with the same margin. Because retained observations are a subset of fitting messages, WIDE contains NARROW without using held-out locations or catalogue positions to enlarge it.

The comparison asks whether replacing the receiver-specific restricted support envelope with all available fitting-survey support addresses the observed vulnerability. It does NOT test every possible larger box, certify that every true receiver lies inside, or declare catalogue coordinates truth. In particular, no expansion is chosen to include the already-known remote BS71 coordinate. Failure under this rule cannot establish failure under all defensible coordinate-recovery methods.

## Optimization is separately visible

Both domain arms use the same source-style initializer, candidate directions, step schedule and maximum sweep budget. They may use different actual objective counts because stopping is conditional. A secondary scheduled five-start sensitivity is fixed now, not selected after seeing poor outcomes. It is reported separately rather than replacing a native unfavorable result. The protocol does not imply a global search or monotonic relation between domain size and the result returned by a local optimizer.

## Two internal validation populations

`group80` assigns entire duplicate components to approximately 80% fitting/20% validation by a fixed hash rule. `space1000` instead holds out entire 1,000-m spatial cells, with duplicate closure preserved. The latter need not yield exactly 20% of rows because cells have different occupancies.

Both start from the old 16,612 calibration rows. Neither is new field data, an independent deployment or a newly untouched dataset. They are newly withheld from these follow-up fits, not withheld from the entire development history.

## Support and the old 2,495-message evaluation set

Preflight revealed that group80 supports fitting and validation for all 33 primary receivers. space1000 has no fitting observations for BS71 and no validation observations for BS10. These outcomes were not repaired by moving messages or changing the hash salt.

In space1000, all 33 receiver rows remain reported. BS10 can be fitted but cannot receive an RSSI validation score. BS71 has no new fitted coordinate and is not assigned an old/cross-arm/catalogue fallback. Eight of the old primary messages originally selected BS71; holding selections fixed leaves 2,487 messages with complete supported coordinates. This differs from the historical 2,493-survivor experiment that removed BS71 and then used the remaining receptions. No mixing of these definitions is allowed.

The producer must report all requested 2,495 messages and mark the eight unsupported predictions, then compare geometry arms on the same 2,487 common complete rows, including a recalculated catalogue-reference baseline on those rows. A 2,487-row result cannot silently be compared to the full 2,495-row reference median.

## Interpretation rules

- Better fitting loss alone is not a successful diagnostic contribution.
- Fitting gain accompanied by poor validation is a generalization failure under that split, not unique identification of its cause.
- Better prediction but poor geometry/task behavior supports a fit-versus-task distinction for this procedure, subject to catalogue uncertainty.
- Improved localization after expanding the box or changing the start schedule is retained even if it weakens the intended explanation.
- A mixed or opposite spatial-holdout result remains visible.
- None of these outcomes by itself proves that any named previous publication used this faulty procedure.

No validation outcome has been evaluated in PR1. The full multi-arm producer is the Stage 3 implementation task; the included helper implements source-style search and was tested only on constructed data in this checkpoint.
