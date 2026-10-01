# PR3 implementation resolutions — before new MV1 fits or outcome scoring

The original PA-PR-MV1-20260919 JSON is unchanged. These details operationalize
its existing design; they do not add arms, splits, reselect inputs or tune results.

1. The producer uses the original projected CSV coordinates in the recorded
   numerical environment. CSV bytes, S1/PR1 manifests and saved preflight
   membership/selection/domain records are checked before fitting.
2. The two main local-search arms run once natively and then ALL five scheduled
   starts again, including start zero. Its repeated outcome is checked against
   the native run; duplicate projected starts are retained and identified.
3. Every objective call is recorded, including the initial point and rejected
   clipped candidates. Strict loss acceptance has no tolerance, matching the
   source. Descriptive comparisons use 1e-9 dB; geometry equality and domain
   membership use 1e-7 m, consistent with the baseline geometry diagnostics.
4. Catalogue RSSI predictions require fitting support just like other fitting
   intercepts. Catalogue raw-WCL coordinates nevertheless exist for all 33
   receivers. Primary downstream comparison uses exactly the common-complete
   rows (including a separately rescored catalogue baseline); all 2,495 requests
   and catalogue full-cohort outputs are retained.
5. A validation score requires one observation; its exact count is printed.
   No pooled receiver claim conceals zero validation support or tiny strata.
   Tables summarize retained fitting, all fitting and all validation receptions
   separately. All-fitting/validation intercepts are never recentered.
6. CONST predicts median retained-fitting RSSI, identical across its observations;
   it has no coordinate and is never passed to raw-WCL.
7. Finite profiles include 21 points PER ray, including the duplicated initializer,
   to follow the stated 8 x 21 schedule. Endpoints are exact WIDE intersections.
   These objective-only profiles never supply a fitted model or select a start.
8. Aggregate tables are descriptive. Receiver medians are unweighted and compared
   on matched eligible receivers; pooled reception summaries are separately labeled.
   Downstream summaries are differences/ratios of error medians on identical rows.
   No bootstrap, hypothesis testing, new significance threshold or multiplicity
   claim is introduced. All arm/start outcomes are exported.
9. The source-style search returns a best visited point, not a success certificate.
   Sweep-cap-with-improvement counts and actual calls are retained. A wider domain
   is not silently seeded with the narrow optimum; multistart remains separate.
10. Unexpected computation failures stop the run with a failure receipt and no
    COMPLETE marker; missing fitting/validation support is a scientific status,
    not a crash and not an imputation trigger.

No numerical fitting or validation outcome was used to set these resolutions.
Prior fits and the earlier fixed-coordinate diagnostic are already known. This
is not external preregistration and does not create an untouched dataset.
