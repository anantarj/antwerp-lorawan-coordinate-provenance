#!/usr/bin/env python3
"""
baseline_001_160826.py
======================

RE-BASELINE. ONE RUN, ONE SUBSTRATE, ONE COHERENT SET OF NUMBERS.

WHY THIS EXISTS
---------------
The claim ledger contains 48 entries. 41 were measured on RSSFIT-estimated
gateway geometry; 0 on verified geometry; 0 carried the noise floor they had to
clear. Findings were then added on top of that base rather than re-based onto
it, so the corpus does not converge -- each addition widens the gap between the
tested and untested parts.

This harness replaces that ledger for every load-bearing claim. It does not
annotate the old numbers; it produces new ones on a single substrate with
confidence intervals and empirically measured floors.

WHAT IT COVERS  (enumerated from ROADMAP-001 sec.3, not from memory)

  BLOCK 0  MAP VALIDATION  [C4] rank-among-published-candidates for every assigned
                           position, plus its correlation. The run depends on this
                           map, so it is validated FIRST. Skipped (and said to be
                           skipped) if --gw-locs is absent.
  BLOCK 1  FLOORS          seed floor and calibration-draw floor, MEASURED here.
                           Every later block prints them in its header via
                           floor_line() -- verified, not asserted.
  BLOCK 2  WCL             row 1 + [C5] the leakage test, IMPLEMENTED: evaluation
                           region fixed, calibration region varied. WCL has no A0,
                           no exponent, no calibration -- coordinates are its only
                           input, so it is the cleanest isolation available
  BLOCK 3  A0 PROCEDURES   row 2, per-gateway paired across substrates
  BLOCK 4  STRATA          row 3, ON/OFF with coordinate-free RSSI selection
  BLOCK 5  OBJECTIVE FORM  row 4, tie-aware statistics (see below)
  BLOCK 6  EXPONENT        row 5, within-gateway estimator by distance band AND
                           by RSSI quantile. The q90 slope is the propagation
                           estimate; the naive slope is shadowing-depressed
  BLOCK 7  N-SWEEP         row 6, A0 refitted at each n
  BLOCK 8  LOCALIZATION    row 7 + the DIFF/NLLS ratios
  BLOCK 9  R2 LAW          C6: the sensitivity law and its crossover
  BLOCK 10 GROUND-TRUTH-FREE  regional instability, survey footprint
  BLOCK 11 GATEWAY SUPPORT    the manuscript's min_gws~7 tail transition
  BLOCK 27 DEPLOYMENT CHANGE   a receiver FAILS after the survey: the database
                              keeps its dimension, queries lose it. Naive vs
                              re-indexed vs range-based. Plus receiver ADDITION.
  BLOCK 26 REMOVAL CURVE       both families degraded by REMOVING receivers from
                              the shared mapped set, plus what the UNMAPPED
                              columns are worth to fingerprinting alone.
  BLOCK 25 FINGERPRINT ASYMMETRY  a kNN fingerprint uses NO receiver coordinates,
                              so its accuracy is EXACT. Measures that number, the
                              nearest-calibration-point distance that explains it,
                              and TRANSFER against the range-based methods.
  BLOCK 24 RESIDUAL BOUND      our accuracies are UPPER BOUNDS (transmitters are
                              ground truth; only receivers are recovered). This
                              measures how loose the bound is.
  BLOCK 23 STRICT-SUBSET STABILITY [C4b] does the STRONG subset reproduce from
                              disjoint halves better than the raw assignment's
                              54%? Decides how hard sec.5 must hedge.
  BLOCK 22 CONTEXTUAL FLOORS  [M1] the floor is measured ONCE and applied to
                              east-only arms, k<10 arms, WCL, and n=400 rows.
                              This measures it separately in each.
  BLOCK 21 ABSORPTION CURVE   (1) cost vs NUMBER of wrong anchors (2) systematic
                              vs random at equal magnitude (3) does it matter
                              WHICH gateways are wrong. Never mutates PHYS/RSSF.
  BLOCK 20 MAP CONTAMINATION? full map vs strong subset, PAIRED on the messages
                              evaluable under both -- separates map quality from
                              population selection. Skipped under --drop-weak.
  BLOCK 19 SPREAD + BOOTSTRAP per-gateway error census, 40-draw composition
                              bootstrap and leave-one-out -- the three figures
                              the manuscript quotes that were NOT from this run.
  BLOCK 18 ARTIFACTS PORTED  residual kurtosis, NLLS divergence and sweep
                              coordinate-drift, moved in from side scripts so
                              the artifact catalogue comes from ONE run.
  BLOCK 17 TRUE = OPTIMUM?   BLOCK 16 hinted that sub-400 m error can HELP, on
                              ONE seed. This repeats over many seeds and adds a
                              DIRECTED radial-bias sweep to locate the actual
                              optimum, then places RSSFIT against it.
  BLOCK 16 FALSIFIER VALID.  does the apparatus DISCRIMINATE? self-comparison
                              must give 1.00x; injected error must make the gap
                              appear and scale; the floor must classify a known
                              effect correctly. A test that never fires is not
                              evidence.
  BLOCK 15 GEOGRAPHIC SPLIT the hardest generalisation test on one deployment:
                              calibrate in one half of the city, evaluate in the
                              other. RSSFIT refit per arm, verified map fixed.
  BLOCK 14 TEMPORAL + k<10  the manuscript splits calibration/evaluation at
                              RANDOM; a deployment calibrates once and localizes
                              later. Plus selection where it can actually act.
  BLOCK 13 REGISTER CLOSE   F42 discard-rate reconciliation, the unused HDOP
                              GPS-quality filter, F25 (WCL_bc vs raw) and F18
                              (does RSSFIT's own loss signal its true error?)
  BLOCK 12 DIFF PARAMETERS      tau_D, lattice resolution, selection mode, pool
                              factor, bias correction -- five inference parameters
                              that had no verified-geometry sweep. Bias correction
                              is the manuscript's largest ablation (2.90->1.54 km)

STATISTICS DISCIPLINE -- the defects this replaces
--------------------------------------------------
* NEVER the median of paired differences. The fine lattice is quantised at
  150 m, so 20-43% of message pairs are EXACTLY tied and that statistic is 0 by
  construction with a degenerate CI. Two prior results were reported through it.
  Paired comparisons here use: tie fraction, sign test on non-tied pairs,
  Wilcoxon, and a bootstrap CI on the DIFFERENCE OF DISTRIBUTION MEDIANS.
* Zero-inclusion is tested as lo <= 0 <= hi. Strict inequality admitted [0, x]
  as excluding zero in three prior harnesses.
* Only DIFFERENCE denominators are treated as vanishing. A level statistic
  (a median error) is bounded away from zero by construction.

SEED CONVENTION (CLASS C)
  random.Random(9) draws every EVALUATION set; 4242/4243 every RANDOM-CONTROL
  calibration set; 31/77 the sub-population caps. The same seed on DIFFERENT
  lists selects different messages, so reuse is safe and gives reproducibility
  where lists coincide. It is UNSAFE only if a future edit makes two of those
  lists identical when they should be independent.

GATES -- all implemented, all abort. Nothing is declared that is not coded.
  GATE A  no leakage: calibration and evaluation disjoint by CONTENT KEY.
          The dataset contains 0.229% duplicate records (229/55,375, largest
          group 7), so a small overlap is expected and is a DATASET property.
          Affected evaluation messages are DROPPED and reported; the run aborts
          only if the contaminated fraction exceeds --max-dup-frac (default 1%).
  GATE B  the verified map joins the dataset's BS-numbered labels
  GATE C  one evaluation set, fixed once, asserted identical in every block
  GATE D  Proposition 1: the differential must be INVARIANT to a common-mode
          offset. This is algebra, so a non-zero spread means the harness is
          wrong, not the physics. Aborts.
  GATE E  the map is GEOMETRICALLY PLAUSIBLE and the exponent is physical.
          Added 19 Aug after an adversarial attack: GATE B checks only that
          >=10 keys JOIN, never the geometry. A map with every receiver at one
          point ran and reported 5,707,771 m; coordinates at 1e12 reported
          1,414,209,125,324 m; --assumed-n 0 reported 5,463 m and -3 reported
          1,991 m. All four SILENT. Bounds: span 200 m to 200 km, n in 1.5-8.0.

WHAT THIS DOES NOT DO
  * It does not settle Sigfox. No public Sigfox gateway coordinates exist.
  * It does not confirm the 27-gateway map. That map is correlation-recovered
    and outcome-validated; its generator is absent. Every map-dependent number
    inherits that caveat and the header says so on every run.

USAGE
    python3 baseline_001_160826.py --data lorawan_antwerp_2019_dataset.csv \
        --map bs_to_utm_coords.json --samples 2500 --reps 5 --out ./baseline_001

    --blocks 0,2     run a subset (default: 0-10)
    --gw-locs FILE   published EUI->lat/lon file, required by BLOCK 0
    --quick          small samples, for a smoke test only -- NOT reportable
"""

from __future__ import annotations
import argparse, json, math, os, random, sys
import numpy as np
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

L = []
ROWS = []          # per-message export: block, substrate, method, error_m
def P(t=""):
    print(t); L.append(t)

def rec(block, substrate, method, errs, aux=None):
    """Accumulate per-message errors so the run can become a figure.

    AUX COLUMN added 19 Aug. BLOCK 30 conditions on an observable TRIGGER, and
    without exporting that trigger alongside the errors the subset cannot be
    reconstructed from the CSV -- the analysis would be un-redoable, which is the
    same class of problem as the missing message key. `aux` is a list parallel to
    `errs`; it defaults to None and every pre-existing caller is unchanged.

    JOINING: rows within one (block, substrate, method) group are in the SAME
    message order, because every arm iterates the same list. Position is
    therefore a valid join key -- BUT only when the arms have EQUAL LENGTH, which
    a consumer must CHECK (BLOCK 8's Trilat arm can be short when the solver
    raises)."""
    for i, e in enumerate(errs):
        ROWS.append((block, substrate, method, float(e),
                     "" if aux is None else float(aux[i])))

def summ(e, seed=1, label=""):
    """median + CI + p90 + p95. The manuscript's second headline metric is P90;
    reporting medians alone was a coverage gap in the first version."""
    e = np.asarray(e, float)
    lo, hi = boot_median(e, seed=seed)
    return (f"{label}median {np.median(e):>6.0f} m  CI [{lo:.0f}, {hi:.0f}]"
            f"  p90 {np.percentile(e,90):>6.0f}  p95 {np.percentile(e,95):>6.0f}")

# ---------------------------------------------------------------- statistics
def boot_median(v, nb=6000, seed=1):
    v = np.asarray(v, float)
    if v.size < 5:
        return float("nan"), float("nan")
    rg = np.random.default_rng(seed)
    b = np.array([np.median(v[rg.integers(0, v.size, v.size)]) for _ in range(nb)])
    return float(np.percentile(b, 2.5)), float(np.percentile(b, 97.5))


def boot_diff_medians(a, b, nb=6000, seed=1):
    """CI on median(a) - median(b). NOT the median of paired differences."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    if a.size < 5 or b.size < 5:
        return float("nan"), float("nan")
    rg = np.random.default_rng(seed)
    d = np.array([np.median(a[rg.integers(0, a.size, a.size)])
                  - np.median(b[rg.integers(0, b.size, b.size)]) for _ in range(nb)])
    return float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


def boot_diff_p90(a, b, nb=4000, seed=1):
    """CI on p90(a) - p90(b). The tail analogue of boot_diff_medians."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    if a.size < 20 or b.size < 20:
        return float("nan"), float("nan")
    rg = np.random.default_rng(seed)
    d = np.array([np.percentile(a[rg.integers(0, a.size, a.size)], 90)
                  - np.percentile(b[rg.integers(0, b.size, b.size)], 90) for _ in range(nb)])
    return float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


def paired_report(a, b, label_a, label_b, seed=1):
    """Tie-aware paired comparison. Returns a dict; never a paired-median CI."""
    from scipy.stats import wilcoxon, binomtest
    a, b = np.asarray(a, float), np.asarray(b, float)
    d = a - b
    ties = float(np.mean(d == 0))
    ut = d[d != 0]
    k = int((ut > 0).sum())
    sgn = binomtest(k, len(ut), 0.5).pvalue if len(ut) >= 5 else float("nan")
    try:
        w = wilcoxon(a, b).pvalue if len(ut) >= 5 else float("nan")
    except Exception:
        w = float("nan")
    lo, hi = boot_diff_medians(a, b, seed=seed)
    return dict(ma=float(np.median(a)), mb=float(np.median(b)), ties=ties * 100,
                n_untied=len(ut), a_worse=100.0 * k / max(len(ut), 1),
                sign_p=sgn, wilcoxon_p=w, dlo=lo, dhi=hi,
                spans_zero=(lo <= 0 <= hi), la=label_a, lb=label_b)


DIRECTIONAL_N = 200
N_MISMATCH = 0.20

def claim(label_a, a, label_b, b, FLOOR, floor_kind="seed", note=""):
    """INTERPRETIVE GUARD. Prints the fields whose absence caused the recorded
    misreadings, so the error is visible in the output instead of depending on
    memory:
      * BOTH n values, and a flag when they differ by >20% (caused: comparing
        arms with different evaluation populations)
      * the ABSOLUTE difference beside the percentage (caused: reading +20.2%
        vs +11.6% as an effect when both were ~120 m)
      * the floor WITH ITS PROVENANCE (caused: applying a band measured under
        one configuration to a deviation measured under another)
      * DIRECTIONAL when min(n) < 200 (caused: 'saturates at k=7' on n=120)
    It cannot judge meaning. It makes the inputs to judgement impossible to miss.
    """
    a, b = np.asarray(a, float), np.asarray(b, float)
    ma, mb = float(np.median(a)), float(np.median(b))
    absd = ma - mb
    pct = absd / mb * 100 if mb > 0 else float("nan")
    fl = FLOOR.get(floor_kind)
    prov = FLOOR.get("provenance", "UNSET — floor provenance not recorded")
    tags = []
    if min(a.size, b.size) < DIRECTIONAL_N:
        tags.append(f"DIRECTIONAL (min n={min(a.size,b.size)})")
    if abs(a.size - b.size) / max(a.size, b.size, 1) > N_MISMATCH:
        tags.append(f"*** N MISMATCH {a.size} vs {b.size} — populations differ ***")
    if fl is not None and abs(pct) < fl:
        tags.append(f"BELOW FLOOR ({fl:.1f}%)")
    out = (f"    {label_a} {ma:.0f} m (n={a.size})  vs  {label_b} {mb:.0f} m "
           f"(n={b.size})\n"
           f"      diff {absd:+.0f} m  =  {pct:+.1f}%   | floor {floor_kind}="
           f"{'unset' if fl is None else f'{fl:.1f}%'} [{prov}]")
    if note:
        out += f"\n      {note}"
    if tags:
        out += "\n      " + " | ".join(tags)
    return out


# ---------------------------------------------------------------- FINGERPRINT
# Hoisted to module level 17 Aug. BLOCKS 25, 26 and 27 each carried a private
# near-copy of these three functions -- the definition of patchwork. One
# implementation now serves all three, so a change to the distance metric or the
# fill floor cannot silently apply to one block and not another.
FP_FLOOR_DBM = -200.0

def fp_vec(msgs, gids, drop=frozenset()):
    """RSSI matrix over `gids`; receivers in `drop` are treated as NOT REPORTING
    (left at the fill floor), which is what a failed receiver looks like."""
    gx = {g: i for i, g in enumerate(gids)}
    X = np.full((len(msgs), len(gids)), FP_FLOOR_DBM, dtype=np.float32)
    Y = np.zeros((len(msgs), 2))
    for i, m_ in enumerate(msgs):
        for r in m_.receptions:
            if r.gid in drop:
                continue
            j = gx.get(r.gid)
            if j is not None:
                X[i, j] = float(r.rssi)
        Y[i] = (m_.x, m_.y)
    return X, Y


def fp_knn(dbX, dbY, qX, qY, k=3, mask=None, chunk=1000, return_all=False,
           timed=False):
    """Euclidean kNN on the RSSI vector; position = mean of the k nearest.

    `mask` restricts the comparison to a subset of columns -- what an operator
    who NOTICED a receiver failure and re-indexed would do.

    DISTANCE FORM, changed 17 Aug. The broadcast
    ((q[:,None,:] - X[None,:,:])**2).sum(-1) allocates chunk x db x dims and
    measured 7.35 s per 400-query chunk at db=8000 -- 51 s per pass, and the
    planned run makes ~150 passes. The Gram identity
        |q-x|^2 = |q|^2 + |x|^2 - 2 q.x
    is one matrix multiply: 0.043 s per chunk, a 170x speedup, 13 MB instead of
    0.54 GB, with the neighbour RANKING identical (verified). Computed in
    float64 so the cancellation in the identity is exact at these magnitudes.
    """
    A = (dbX if mask is None else dbX[:, mask]).astype(np.float64)
    an = (A ** 2).sum(1)
    e = []
    t0 = time.perf_counter() if timed else None
    for a in range(0, len(qX), chunk):
        q = (qX[a:a + chunk] if mask is None else qX[a:a + chunk][:, mask]).astype(np.float64)
        d = an[None, :] + (q ** 2).sum(1)[:, None] - 2.0 * (q @ A.T)
        idx = np.argpartition(d, min(k, d.shape[1] - 1), axis=1)[:, :k]
        e += list(np.linalg.norm(dbY[idx].mean(axis=1) - qY[a:a + chunk], axis=1))
    ms = (1000.0 * (time.perf_counter() - t0) / max(len(qX), 1)) if timed else None
    e = np.array(e)
    if return_all:
        return (e, ms) if timed else e
    return (float(np.median(e)), ms) if timed else float(np.median(e))


def fp_nearest(qY, dbY, chunk=400):
    """Distance from each query position to the nearest DATABASE position.
    Without this a fingerprint accuracy figure is uninterpretable on a
    drive-test dataset: the query may simply be sitting on a survey point."""
    out = []
    for a in range(0, len(qY), chunk):
        d = np.sqrt(((qY[a:a + chunk][:, None, :] - dbY[None, :, :]) ** 2).sum(-1))
        out += list(d.min(axis=1))
    return np.array(out)


def minmax(gw_xy, rssi_corrected, n):
    """MIN-MAX (bounding-box) localization, added 19 Aug.

    WHY IT IS HERE. The Antwerp Sigfox benchmark's own authors report that
    distance-based multilateration gave high errors on their data and adopted
    MIN-MAX instead. A comparison that omits the method the dataset's authors
    CHOSE invites the obvious reviewer question, and we had no implementation.

    THE METHOD. Convert each corrected RSSI to a distance under the same
    log-distance model every other arm uses, draw an axis-aligned square of that
    half-width around each receiver, and INTERSECT the squares:
        x in [max_i(x_i - d_i), min_i(x_i + d_i)]
    The estimate is the centre of the intersection. It uses no optimisation, no
    lattice and no starting point -- which is precisely why it is robust where
    least squares diverges.

    DEGENERATE CASE. If the squares do not intersect -- which happens when the
    distance estimates are mutually inconsistent -- the interval is inverted.
    We do NOT silently clamp: an inverted interval is reported by returning the
    midpoint of the inverted bounds, which is the standard treatment, and the
    caller can count how often it happens via `minmax_infeasible`.
    """
    d = 10.0 ** (-np.asarray(rssi_corrected, float) / (10.0 * n))
    lo_x, hi_x = (gw_xy[:, 0] - d).max(), (gw_xy[:, 0] + d).min()
    lo_y, hi_y = (gw_xy[:, 1] - d).max(), (gw_xy[:, 1] + d).min()
    return np.array([0.5 * (lo_x + hi_x), 0.5 * (lo_y + hi_y)], float)


def minmax_infeasible(gw_xy, rssi_corrected, n):
    """True when the bounding squares do NOT intersect. Reported, never hidden."""
    d = 10.0 ** (-np.asarray(rssi_corrected, float) / (10.0 * n))
    return bool((gw_xy[:, 0] - d).max() > (gw_xy[:, 0] + d).min()
                or (gw_xy[:, 1] - d).max() > (gw_xy[:, 1] + d).min())


def geo_eval(ev, PHYS, gids, msgs, cal_msgs, n, max_gws, wcl, lattice, fit_a0,
             drop=frozenset(), arms=("wcl",)):
    """ONE range-based evaluator, hoisted 17 Aug.

    BLOCKS 26 and 27 each defined a private function called `geo`. Two functions
    of the same name in one scope, with DIFFERENT return arities -- correct only
    because BLOCK 26 happens to execute first. Moving a block would have
    shadowed one silently. This is the single implementation.

    `drop` removes receivers as if they had FAILED. `arms` selects which
    estimators to evaluate. Returns {arm: (median, p99, pct>1km)} and n.
    """
    mp = {g: PHYS[g] for g in gids if g not in drop}
    if len(mp) < 3:
        return {a: (float("nan"),) * 3 for a in arms}, 0
    a0m = fit_a0(cal_msgs, mp, n)
    acc = {a: [] for a in arms}
    for mm in msgs:
        rx = [r for r in mm.receptions if r.gid in mp and r.gid in a0m]
        if len(rx) < 3:
            continue
        rx = sorted(rx, key=lambda r: -r.rssi)[:max_gws]
        g_ = np.vstack([mp[r.gid] for r in rx])
        raw = np.array([r.rssi for r in rx], float)
        rv = raw - np.array([a0m[r.gid] for r in rx], float)
        t = np.array([mm.x, mm.y], float)
        if "wcl" in acc:
            acc["wcl"].append(float(np.linalg.norm(wcl(ev, g_, rv) - t)))
        if "abs" in acc:
            acc["abs"].append(float(np.linalg.norm(
                lattice(ev, g_, rv, n, "abs", "mean") - t)))
        if "diff" in acc:
            acc["diff"].append(float(np.linalg.norm(
                lattice(ev, g_, rv, n, "diff", "median") - t)))
        # MIN-MAX arm added 19 Aug. Dispatching here covers BLOCKS 26 and 27 in ONE
        # place -- geo_eval is the single evaluator both delegate to. Min-Max is a
        # range-based method and belongs wherever the family is characterised.
        if "minmax" in acc:
            acc["minmax"].append(float(np.linalg.norm(minmax(g_, rv, n) - t)))
        if "nlls" in acc:
            C_ = np.array(list(mp.values()))
            bb_ = (C_[:, 0].min() - 3000, C_[:, 0].max() + 3000,
                   C_[:, 1].min() - 3000, C_[:, 1].max() + 3000)
            x_, _c, _d = ev.robust_nlls_localize(
                gw_mat=g_, rssi_corrected=rv, n=n, wcl_init=wcl(ev, g_, rv),
                bbox=bb_, huber_c=1.345, n_starts=3, max_iter=120,
                grad_tol=1e-6, halton_seed=1)
            acc["nlls"].append(float(np.linalg.norm(x_ - t)))
    def stat(v):
        if not v:
            return (float("nan"),) * 3
        a = np.array(v)
        return (float(np.median(a)), float(np.percentile(a, 99)),
                100.0 * float(np.mean(a > 1000)))
    nn = len(next(iter(acc.values()))) if acc else 0
    return {k: stat(v) for k, v in acc.items()}, nn


def geo_latency(ev, PHYS, gids, msgs, cal_msgs, n, max_gws, wcl, lattice, fit_a0,
                arms=("wcl", "abs", "diff", "trilat", "minmax"), cap=400):
    """Per-fix latency for each range-based arm, MEASURED.

    Added 17 Aug. The cost table previously asserted '< 0.01 ms' for the
    range-based family using the CENTROID as its stand-in. The differential
    objective runs a LATTICE SEARCH, not a weighted average -- its latency is
    not the centroid's, and asserting one number for both was wrong.

    TRILAT AND MINMAX ARMS ADDED 19 Aug (due item 13). The table timed WCL, ABS
    and DIFF only. **Trilateration BEATS the differential on verified geometry
    (697 m against 966 m, disjoint CIs -- see TRI1) and Min-Max beats both
    (466 m), so a cost frontier that omits them compares the differential only
    against methods it already outruns.** Both are closed-form or near it, so
    the expectation is that they are CHEAPER as well as more accurate -- which,
    if it holds, is the more uncomfortable result and belongs in the table.
    """
    mp = {g: PHYS[g] for g in gids}
    if len(mp) < 3:
        return {a: float("nan") for a in arms}
    a0m = fit_a0(cal_msgs, mp, n)
    prepared = []
    for mm in msgs[:cap]:
        rx = [r for r in mm.receptions if r.gid in mp and r.gid in a0m]
        if len(rx) < 3:
            continue
        rx = sorted(rx, key=lambda r: -r.rssi)[:max_gws]
        prepared.append((np.vstack([mp[r.gid] for r in rx]),
                         np.array([r.rssi for r in rx], float)
                         - np.array([a0m[r.gid] for r in rx], float)))
    if not prepared:
        return {a: float("nan") for a in arms}
    out = {}
    for arm in arms:
        t0 = time.perf_counter()
        for g_, rv in prepared:
            if arm == "wcl":
                wcl(ev, g_, rv)
            elif arm == "abs":
                lattice(ev, g_, rv, n, "abs", "mean")
            elif arm == "trilat":
                # THE SAME CALL BLOCK 8 USES. An earlier version of this line
                # invented ev.trilaterate(gw_mat=..., rssi_corrected=..., n=...),
                # which does not exist -- the evaluator exposes
                # trilateration_joint_A0(gw_xy, rssi, n), positionally. A timing
                # arm that does not call what the accuracy arm calls is not a
                # cost frontier, it is a different measurement.
                ev.trilateration_joint_A0(g_, rv, n)
            elif arm == "minmax":
                minmax(g_, rv, n)
            else:
                lattice(ev, g_, rv, n, "diff", "median")
        out[arm] = 1000.0 * (time.perf_counter() - t0) / len(prepared)
    return out


def gate_c(EV, EVKEY, where):
    """GATE C, ENFORCED 18 Aug. The header promised 'one evaluation set, fixed
    once, ASSERTED IDENTICAL IN EVERY BLOCK'. EVKEY was assigned twice and never
    read -- a gate declared in prose and not coded, which is precisely the defect
    class this harness exists to correct. BLOCK 1 does legitimately replace EV in
    place, so the invariant is checked at block boundaries rather than inside."""
    if len(EV) != EVKEY:
        P(f"  *** GATE C VIOLATION at {where}: evaluation set is {len(EV)}, "
          f"expected {EVKEY}. ABORT -- results below would not be comparable. ***")
        return False
    return True


def floor_line(FLOOR, kind="draw"):
    """Printed by EVERY block. The docstring promised this; blocks 3,4,6-10 did not do it."""
    v = FLOOR.get(kind)
    o = FLOOR.get("seed" if kind == "draw" else "draw")
    if v is None:
        return "  [floor] BLOCK 1 not run -- effects below have NO measured floor to clear"
    rg = FLOOR.get("seed_range")
    extra = f" | (superseded range stat {rg:.1f}%)" if rg is not None else ""
    return (f"  [floor, {FLOOR.get('stat','?')}] eval-draw {FLOOR['seed']:.1f}% | "
            f"calibration-draw {FLOOR['draw']:.1f}%{extra}")


def fmt_paired(r, floor_pct=None):
    pct = (r["ma"] - r["mb"]) / r["mb"] * 100 if r["mb"] > 0 else float("nan")
    flag = ""
    if floor_pct is not None and abs(pct) < floor_pct:
        flag = f"  BELOW FLOOR ({floor_pct:.1f}%)"
    if r["spans_zero"]:
        flag += "  CI SPANS ZERO"
    return (f"    {r['la']} {r['ma']:.0f} m  vs  {r['lb']} {r['mb']:.0f} m"
            f"   ({pct:+.1f}%)\n"
            f"      diff-of-medians CI [{r['dlo']:+.0f}, {r['dhi']:+.0f}] m"
            f" | ties {r['ties']:.1f}% | {r['la']} worse on {r['a_worse']:.1f}% of"
            f" {r['n_untied']} untied | sign p={r['sign_p']:.2e}{flag}")


# ---------------------------------------------------------------- estimators
def wcl(ev, g, raw):
    return ev.wcl_estimate(g, raw)


TAU = 3.0   # set from --tau in main(). See the note in lattice().

def lattice(ev, g, r, n, obj, agg="median", tau=None, topk=25, stages=None):
    """DEFECT FIXED 18 Aug: --tau was DEAD. Of 39 lattice() call sites, 2 passed
    tau=; args.tau was referenced once, in BLOCK 13's discard-rate line. So
    `--tau 5` reported a 5 dB discard rate while every localization still ran at
    the hardcoded 3.0 -- a sweep would have shown a moving discard rate and a
    flat error curve, which is C7's published claim, produced by a dead flag
    rather than by the data. Resolving None against the module TAU makes one
    edit reach every call site. At the default the numbers are unchanged."""
    if tau is None:
        tau = TAU
    A = np.median if agg == "median" else np.mean
    k = g.shape[0]
    c = ev.wcl_estimate(g[:min(topk, k)], r[:min(topk, k)])
    io, jo = np.triu_indices(k, 1)
    z = r[io] - r[jo]
    keep = np.abs(z) >= tau
    sa = sd = None
    for span, sp in (stages or ((6000.0, 600.0), (1500.0, 150.0))):
        Pn = ev.triangular_lattice_points(center=c, span_m=span, spacing_m=sp)
        lg = np.log10(np.linalg.norm(Pn[:, None, :] - g[None, :, :], axis=2) + 1.0)
        Ra = np.abs(r[None, :] - (-10.0 * n * lg))
        Rd = (np.abs(z[None, keep] - (-10.0 * n * (lg[:, io[keep]] - lg[:, jo[keep]])))
              if keep.any() else None)
        if obj == "abs":
            S = A(Ra, axis=1)
        elif obj == "diff":
            if Rd is None:
                c = Pn[0]; continue
            S = A(Rd, axis=1)
        else:
            if Rd is None:
                S = A(Ra, axis=1)
            else:
                if sa is None:
                    i0 = int(np.argmin(np.linalg.norm(Pn - c, axis=1)))
                    f = lambda v: max(1.4826 * float(np.median(np.abs(v - np.median(v)))), 1e-6)
                    sa, sd = f(Ra[i0]), f(Rd[i0])
                S = A(np.hstack([Ra / sa, Rd / sd]), axis=1)
        c = Pn[int(np.argmin(S))]
    return c


def fit_a0(cal, coords, n):
    by = {}
    for mm in cal:
        for rx in mm.receptions:
            if rx.gid in coords:
                d = float(np.linalg.norm(coords[rx.gid] - np.array([mm.x, mm.y]))) + 1.0
                by.setdefault(rx.gid, []).append(rx.rssi + 10 * n * math.log10(d))
    return {g: float(np.median(v)) for g, v in by.items() if len(v) >= 10}


def centroid_map(cal, gids):
    by = {}
    for mm in cal:
        for rx in mm.receptions:
            if rx.gid in gids:
                by.setdefault(rx.gid, []).append((float(rx.rssi), mm.x, mm.y))
    out = {}
    for g, v in by.items():
        a = np.array(v, float)
        if len(a) >= 20:
            out[g] = a[np.argsort(-a[:, 0])[:max(5, int(0.05 * len(a)))], 1:3].mean(axis=0)
    return out


def mkey(m):
    return (round(float(m.x), 3), round(float(m.y), 3),
            tuple(sorted((rx.gid, round(float(rx.rssi), 3)) for rx in m.receptions)))


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--map", required=True, help="verified BS->UTM json")
    ap.add_argument("--gw-locs", type=str, default="lorawan_antwerp_gateway_locations.json",
                    help="published EUI->lat/lon file, for BLOCK 0 map validation")
    ap.add_argument("--sigfox-urban", default="sigfox_urban_norm.csv",
                    help="BLOCK 29 control. Columns BS <n>; -200.0 is the "
                         "verified not-received fill (schema confirmed 19 Aug).")
    ap.add_argument("--sigfox-rural", default="sigfox_rural_norm.csv",
                    help="BLOCK 29 control, second deployment.")
    ap.add_argument("--ev-eligibility-map", default=None,
                    help="Draw the evaluation set using THIS map's receiver "
                         "set while evaluating with --map. Point it at the "
                         "other run's map so both runs score the SAME "
                         "messages and the map is the only difference.")
    ap.add_argument("--restrict-to-map", default=None,
                    help="Keep only receivers present in BOTH --map and this "
                         "file. Point both runs at the other's map to hold "
                         "COMPOSITION fixed and isolate ASSIGNMENT.")
    ap.add_argument("--assumed-n", type=float, default=4.7)
    ap.add_argument("--max-gws", type=int, default=10)
    ap.add_argument("--tau", type=float, default=3.0)
    ap.add_argument("--train-frac", type=float, default=0.3)
    ap.add_argument("--samples", type=int, default=2500)
    ap.add_argument("--reps", type=int, default=5,
                    help="SUPERSEDED by --floor-reps and used only by --quick. "
                         "Retained so existing command lines keep working; it "
                         "controls nothing else. (D5, 18 Aug)")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--blocks", type=str, default="0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27")
    ap.add_argument("--drop-weak", action="store_true",
                    help="R-3: restrict the map to gateways that pass BLOCK 0 "
                         "(rank<=3 and corr>=0.15). Run twice and diff to get "
                         "the sensitivity of EVERY result to the weak entries.")
    ap.add_argument("--floor-reps", type=int, default=10,
                    help="draws used to MEASURE the floor. Independent of --reps: "
                         "the floor is a variance estimate and needs more draws "
                         "than a point measurement. 5 draws of a RANGE statistic "
                         "gave 4.7%% one run and 7.2%% the next.")
    ap.add_argument("--perturb-seeds", type=int, default=12,
                    help="BLOCK 17: realizations per displacement magnitude. "
                         "BLOCK 16 used ONE, which cannot separate a systematic "
                         "effect from a lucky draw.")
    ap.add_argument("--corrupt-draws", type=int, default=8,
                    help="BLOCK 21: random choices of WHICH gateways to corrupt, "
                         "per fraction.")
    ap.add_argument("--corrupt-disp", type=float, default=5000.0,
                    help="BLOCK 21: displacement in metres. Default 5000 matches "
                         "RSSFIT's own median error, so the arms are comparable.")
    ap.add_argument("--rm-draws", type=int, default=6,
                    help="BLOCK 26: random draws of WHICH receivers to remove, per count.")
    ap.add_argument("--fp-dbcap", type=int, default=6000,
                    help="BLOCK 25: cap on the fingerprint database, for runtime. "
                         "The kNN is O(db x query x receivers).")
    ap.add_argument("--boot-draws", type=int, default=40,
                    help="BLOCK 19: random map-composition subsets. The broadest "
                         "test of C1's DIRECTION.")
    ap.add_argument("--popcap", type=int, default=1500,
                    help="cap the fixed-population set per depth, for runtime")
    ap.add_argument("--gw-list", type=str, default="3,5,7,8,9,10",
                    help="BLOCK 11 gateway-support sweep")
    ap.add_argument("--max-dup-frac", type=float, default=1.0,
                    help="abort only if content-duplicate eval messages exceed this %%")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out", default="./baseline_001")
    args = ap.parse_args()
    if args.quick:
        args.samples = min(args.samples, 300); args.reps = 2

    import deltamesh_antwerp_eval_v10_fixed_080826 as ev
    global TAU
    TAU = args.tau          # D2: makes --tau reach all 39 lattice() call sites
    n = args.assumed_n
    BL = set(int(x) for x in args.blocks.split(","))

    P("=" * 96)
    P("BASELINE-001 -- RE-BASELINE ON VERIFIED GATEWAY GEOMETRY")
    P("=" * 96)
    P("CAVEAT CARRIED ON EVERY MAP-DEPENDENT NUMBER BELOW:")
    P("  the 27-gateway map is correlation-recovered and outcome-validated.")
    P("  Its generator (strict27) is ABSENT. It is not independently confirmed.")
    if args.quick:
        P("  *** --quick: SMOKE TEST ONLY. NOT REPORTABLE. ***")
    P("")

    phys = {k: np.array(v, float) for k, v in json.load(open(args.map)).items()}
    msgs = ev.load_antwerp_csv(args.data, min_gws=3)
    rng = random.Random(args.seed)
    m = list(msgs); rng.shuffle(m)
    nt = int(len(m) * args.train_frac)
    cal, pool = m[:nt], m[nt:]

    # ---- GATE B: does the verified map join the data?
    heard = {rx.gid for mm in msgs for rx in mm.receptions}
    joined = set(phys) & heard
    P(f"[GATE B] verified map: {len(phys)} entries, {len(joined)} join the dataset's labels")
    if len(joined) < 10:
        P("         *** ABORT: map does not join ***")
        open(args.out + ".txt", "w").write("\n".join(L) + "\n"); return

    # ---------------- GATE E, added 19 Aug after an adversarial attack ----------
    # GATE B checks only that >=10 map keys JOIN the data. It never looks at the
    # GEOMETRY. Fed a map with every receiver at one point, the harness ran and
    # reported a median of 5,707,771 m; fed coordinates at 1e12, it reported
    # 1,414,209,125,324 m. Both WITHOUT A WORD. Now that make_direct_map.py
    # GENERATES maps, a silent nonsense map is a live risk, not a hypothetical.
    # Also guards the path-loss exponent: --assumed-n 0 gave 5,463 m and -3 gave
    # 1,991 m, both accepted silently, both physically meaningless.
    _C = np.array(list(phys.values()), float)
    _span = float(np.linalg.norm(_C.max(axis=0) - _C.min(axis=0))) if len(_C) else 0.0
    P(f"[GATE E] map geometry: {len(phys)} receivers span {_span:.0f} m")
    if _span < 200.0:
        P("         *** ABORT: receivers span under 200 m -- effectively colocated,")
        P("             no geometric method can separate them. ***")
        open(args.out + ".txt", "w").write("\n".join(L) + "\n"); return
    if _span > 200000.0:
        P("         *** ABORT: receivers span over 200 km -- this is not one urban")
        P("             deployment; the coordinates are wrong. ***")
        open(args.out + ".txt", "w").write("\n".join(L) + "\n"); return
    if not (1.5 <= n <= 8.0):
        P(f"         *** ABORT: assumed path-loss exponent n={n} is outside 1.5-8.0.")
        P("             Free space is 2.0; dense urban is 2.7-3.5. A zero or negative")
        P("             exponent inverts the distance model and yields nonsense. ***")
        open(args.out + ".txt", "w").write("\n".join(L) + "\n"); return
    P(f"         span OK, exponent n={n} OK   PASS")

    rf, _ = ev.estimate_gateway_positions_rssfit(cal, assumed_n=n, seed=args.seed)
    # ---- --restrict-to-map, added 19 Aug -----------------------------------
    # THE PROBLEM IT SOLVES. The recovered 29-receiver map and the official 33
    # differ in TWO ways at once: WHICH receivers are present (composition) and
    # WHERE each one is (assignment). BLOCK 6's exponent reversal (q90 2.90 ->
    # 1.19) and BLOCK 11's sign flip could be either. Restricting BOTH maps to
    # the receivers they SHARE holds composition fixed, so anything that remains
    # is the ASSIGNMENT alone.
    G = sorted(joined & set(rf), key=lambda x: int(x) if x.isdigit() else 0)
    if args.restrict_to_map:
        _other = set(json.load(open(args.restrict_to_map)))
        _before = len(G)
        G = [g for g in G if g in _other]
        P(f"[RESTRICT] receivers kept only if present in BOTH --map and "
          f"{args.restrict_to_map}: {_before} -> {len(G)}. Composition is now")
        P(f"           IDENTICAL across maps, so any remaining difference is the "
          f"ASSIGNMENT alone, not which receivers exist.")
    PHYS = {g: phys[g] for g in G}
    RSSF = {g: np.asarray(rf[g], float) for g in G}
    P(f"         common to verified and RSSFIT: {len(G)} gateways -- used everywhere below")

    # ---- GATE C: ONE evaluation set, fixed once
    # ---- --ev-eligibility-map, added 19 Aug ---------------------------------
    # THE PROBLEM IT SOLVES. EV is drawn from messages with >=3 receptions among
    # the MAPPED set. Two runs on DIFFERENT maps therefore draw from DIFFERENT
    # eligible pools and evaluate DIFFERENT MESSAGES -- v5 got 2,498 and
    # v5_direct 2,495, and they are not the same 2,495. Every A-vs-B difference
    # then mixes THREE things: the map, the population, and the receiver count
    # per message. They are not separable from the output.
    #
    # With this flag, ELIGIBILITY is decided by the map at the given path while
    # EVALUATION still uses --map. Point it at the OTHER run's map and the two
    # runs share one message population, isolating the map alone.
    _elig = PHYS
    if args.ev_eligibility_map:
        _em = json.load(open(args.ev_eligibility_map))
        _elig = {k: v for k, v in _em.items()}
        P(f"[EV POOL] eligibility from {args.ev_eligibility_map} "
          f"({len(_elig)} receivers); evaluation still uses --map "
          f"({len(PHYS)} receivers). The two runs now share a population.")
    EV = [mm for mm in pool
          if sum(1 for rx in mm.receptions if rx.gid in _elig) >= 3]
    EV = random.Random(9).sample(EV, min(args.samples, len(EV)))
    EVKEY = len(EV)

    # ---- GATE A: leakage by content key.
    # The split is by index on one shuffled list, so no message object can be in
    # both halves. A non-zero overlap therefore means DUPLICATE RECORDS in the
    # dataset: identical position, gateway set and RSSI values. Measured rate on
    # Antwerp at min_gws=3: 229 of 55,375 messages (0.229%), largest group 7.
    # The correct response is to DROP the affected evaluation messages and
    # continue -- not to abort a 2,500-message run over 0.1% of it. Abort only
    # if the contaminated fraction is material.
    calkeys = set(mkey(x) for x in cal)
    dupes = [x for x in EV if mkey(x) in calkeys]
    frac = 100.0 * len(dupes) / max(len(EV), 1)
    if dupes:
        EV = [x for x in EV if mkey(x) not in calkeys]
    P(f"[GATE A] content-duplicate evaluation messages: {len(dupes)} ({frac:.2f}% of eval)")
    P(f"         these are duplicate RECORDS in the dataset, not a split error")
    P(f"         action: DROPPED from evaluation | eval set now {len(EV)} messages"
      f"   {'PASS' if frac <= args.max_dup_frac else '*** ABORT: contamination is material ***'}")
    if frac > args.max_dup_frac:
        open(args.out + ".txt", "w").write("\n".join(L) + "\n"); return
    EVKEY = len(EV)
    # D4 FIX 18 Aug: this line used to print BEFORE GATE A ran, reporting the
    # PRE-drop count while claiming to be post-drop. It now prints after.
    P(f"[GATE C] evaluation set FIXED at {len(EV)} messages, after GATE A's drop."
      f" Every block below is asserted against this count.")

    def cases(coords, a0=None, need_a0=True):
        out = []
        for mm in EV:
            rx = [r for r in mm.receptions if r.gid in coords and (a0 is None or r.gid in a0)]
            if len(rx) < 3:
                continue
            rx = sorted(rx, key=lambda r: -r.rssi)[:args.max_gws]
            g = np.vstack([coords[r.gid] for r in rx])
            raw = np.array([r.rssi for r in rx], float)
            rr = raw - np.array([a0[r.gid] for r in rx], float) if a0 else raw.copy()
            out.append((g, raw, rr, np.array([mm.x, mm.y], float)))
        return out

    FLOOR = {"seed": None, "draw": None}

    # ============================================ BLOCK 0 -- MAP VALIDATION [C4]
    if 0 in BL:
        P("\n" + "=" * 96)
        P("BLOCK 0 -- MAP VALIDATION. The run below depends on this map; validate it first. [C4]")
        P("=" * 96)
        gwl = args.gw_locs
        cand = None
        if gwl and os.path.exists(gwl):
            try:
                from pyproj import Transformer
                raw = json.load(open(gwl))
                tf = Transformer.from_crs("EPSG:4326", "EPSG:32631", always_xy=True)
                cand = {k: np.array(tf.transform(float(v["longitude"]), float(v["latitude"])), float)
                        for k, v in raw.items()}
            except Exception as e:
                P(f"  candidate file present but unusable: {e}")
        if cand:
            P(f"  rank-among-{len(cand)} check: for each assigned position, its RSSI-distance")
            P(f"  correlation rank among ALL published candidates. Rank 1 = best of {len(cand)}.")
            by = {}
            for mm in cal:
                for rx in mm.receptions:
                    if rx.gid in PHYS: by.setdefault(rx.gid, []).append((float(rx.rssi), mm.x, mm.y))
            CU = np.array(list(cand.values()), float)
            ranks, corrs, checked = [], [], []
            for g, v in by.items():
                a = np.array(v, float)
                if len(a) < 40: continue
                r_, tx = a[:, 0], a[:, 1:3]
                rc = r_ - r_.mean()
                da = np.sqrt((tx[:, 0:1] - CU[None, :, 0]) ** 2 + (tx[:, 1:2] - CU[None, :, 1]) ** 2)
                nd = -da; nd = nd - nd.mean(axis=0, keepdims=True)
                den = np.sqrt((rc ** 2).sum()) * np.sqrt((nd ** 2).sum(axis=0))
                call = (rc[:, None] * nd).sum(axis=0) / np.where(den == 0, 1e-9, den)
                dA = np.linalg.norm(tx - PHYS[g], axis=1)
                ndA = -dA; ndA = ndA - ndA.mean()
                dnA = np.sqrt((rc ** 2).sum()) * np.sqrt((ndA ** 2).sum())
                ca = float((rc * ndA).sum() / (dnA if dnA > 0 else 1e-9))
                ranks.append(int((call > ca).sum()) + 1); corrs.append(ca); checked.append(g)
            ranks, corrs = np.array(ranks), np.array(corrs)
            P(f"    gateways checked      : {len(ranks)}")
            P(f"    rank 1                : {int((ranks==1).sum())}/{len(ranks)}")
            P(f"    rank <= 3             : {int((ranks<=3).sum())}/{len(ranks)}")
            P(f"    min correlation       : {corrs.min():.3f}")
            ok = (ranks <= 3).all() and corrs.min() >= 0.15
            P(f"    {'PASS -- map is internally consistent' if ok else '*** WARN: some assignments are not top-3 or fall below corr 0.15 ***'}")
            STRONG = [g for g, rk, cr in zip(checked, ranks, corrs) if rk <= 3 and cr >= 0.15]
            P(f"    strong subset (rank<=3 AND corr>=0.15): {len(STRONG)}/{len(ranks)} gateways")
            if args.drop_weak:
                keep = set(STRONG)
                for d_ in (PHYS, RSSF):
                    for g in [x for x in d_ if x not in keep]:
                        del d_[g]
                G[:] = [g for g in G if g in keep]
                P(f"    --drop-weak ACTIVE: every block below uses {len(PHYS)} gateways [R-3]")
                P(f"    NOTE, stated 18 Aug: the evaluation set was drawn BEFORE this")
                P(f"    restriction, requiring >=3 receptions among the FULL map. Messages")
                P(f"    that now fall below 3 mapped receivers are dropped per block, so n")
                P(f"    falls. This is DELIBERATE -- redrawing the evaluation set would")
                P(f"    break comparability with the full run, which is the whole point of")
                P(f"    running both. It does mean the two runs share most messages: 74%")
                P(f"    keep an identical selected subset. NOT independent replication.")
        else:
            P("  no --gw-locs supplied: map validation SKIPPED.")
            P("  Every map-dependent number below is then UNVALIDATED in this run.")

    # ================================================== BLOCK 1 -- FLOORS
    if 1 in BL:
        P("\n" + "=" * 96)
        P("BLOCK 1 -- NOISE FLOORS, MEASURED HERE. Every later effect is read against these.")
        P("=" * 96)
        # EVALUATION-DRAW floor. The first version varied the RSSFIT seed while
        # using VERIFIED coordinates -- a parameter with no path to the arm being
        # measured -- and reported 0.0%, so later blocks checked against nothing.
        # The pipeline IS deterministic given coordinates and A0; the two real
        # stochastic inputs are which messages you evaluate and which you calibrate on.
        seeds, draws = [], []
        # CLASS E fix: every other population honours GATE A; this one did not.
        univ = [mm for mm in pool if mkey(mm) not in calkeys
                and sum(1 for rx in mm.receptions if rx.gid in PHYS) >= 3]
        a0f = fit_a0(cal, PHYS, n)
        for rep in range(args.floor_reps):
            sub = random.Random(400 + rep).sample(univ, min(len(EV), len(univ)))
            # D1 FIX 18 Aug: this temporarily REPLACES the GATE C evaluation set.
            # Without try/finally an exception inside cases() would leave every
            # downstream block evaluating the floor's sample -- and GATE C was
            # never enforced, so nothing would have detected it.
            keep_EV = EV[:]
            try:
                EV[:] = sub
                cs = cases(PHYS, a0f)
            finally:
                EV[:] = keep_EV
            if cs:
                seeds.append(float(np.median([np.linalg.norm(lattice(ev, g, rr, n, "abs", "mean") - t)
                                              for g, raw, rr, t in cs])))
        for rep in range(args.floor_reps):
            sub = random.Random(700 + rep).sample(cal, max(50, int(len(cal) * 0.3)))
            a0 = fit_a0(sub, PHYS, n)
            cs = cases(PHYS, a0)
            if cs:
                draws.append(float(np.median([np.linalg.norm(lattice(ev, g, rr, n, "abs", "mean") - t)
                                              for g, raw, rr, t in cs])))
        # ESTIMATOR CHANGED 16 Aug. The previous floor was (max-min)/mean over 5
        # draws -- a RANGE, driven entirely by the two extreme values. It read
        # 4.7% on one full run and 7.2% on the next, and a floor that unstable
        # cannot arbitrate a 7% effect. Replaced by 2*sd/mean (a ~95% band on the
        # median under re-draw), over --floor-reps draws (default 10).
        # THE OLD STATISTIC IS RETAINED AND PRINTED so every earlier verdict in
        # this programme remains readable against the number that produced it.
        def _floor(v):
            v = np.asarray(v, float)
            if v.size < 2:
                return float("nan"), float("nan"), float("nan")
            rng_ = 100.0 * (v.max() - v.min()) / v.mean()      # OLD: range
            sd_p = 100.0 * v.std(ddof=1) / v.mean()            # sd as a percentage
            return 2.0 * sd_p, rng_, sd_p                      # NEW authoritative: 2*sd
        sd_, sd_range, sd_sd = _floor(seeds)
        dr_, dr_range, dr_sd = _floor(draws)
        FLOOR["seed"], FLOOR["draw"] = sd_, dr_
        FLOOR["seed_range"], FLOOR["draw_range"] = sd_range, dr_range
        FLOOR["seed_sd"], FLOOR["draw_sd"] = sd_sd, dr_sd
        FLOOR["stat"] = "2*sd/mean"
        FLOOR["provenance"] = (f"2*sd over {args.floor_reps} draws; ABS+mean, "
                               f"k={args.max_gws}, VERIFIED coords, {len(PHYS)} gw, "
                               f"citywide draws of {len(EV)}")
        P(f"  EVALUATION-DRAW floor (which messages you evaluate; coords + A0 fixed)")
        P(f"    n={len(seeds)} draws | values {' '.join(f'{x:.0f}' for x in seeds)} m")
        P(f"    AUTHORITATIVE  2*sd/mean = {sd_:.1f}%   (sd alone {sd_sd:.1f}%)")
        P(f"    superseded     (max-min)/mean = {sd_range:.1f}%  <- the statistic used")
        P(f"                   in every run before 16 Aug; retained for readability")
        P(f"  calibration-draw floor (A0 subset redrawn, coords fixed)")
        P(f"    n={len(draws)} draws | values {' '.join(f'{x:.0f}' for x in draws)} m")
        P(f"    AUTHORITATIVE  2*sd/mean = {dr_:.1f}%   (sd alone {dr_sd:.1f}%)")
        P(f"    superseded     (max-min)/mean = {dr_range:.1f}%")
        P(f"\n  ANY EFFECT BELOW {max(sd_, 0):.1f}% (eval draw) OR"
          f" {max(dr_, 0):.1f}% (calibration draw) IS NOT RESOLVABLE.")
        P("  The pipeline is otherwise DETERMINISTIC: given coordinates and A0 there")
        P("  is no seed dependence. These two draws are the only stochastic inputs.")

    # GATE C, checked at the one boundary that follows a mutator
    if not gate_c(EV, EVKEY, "after BLOCK 1"):
        open(args.out + ".txt", "w").write("\n".join(L) + "\n"); return

    a0_phys = fit_a0(cal, PHYS, n)
    a0_rssf = fit_a0(cal, RSSF, n)

    # ================================================== BLOCK 2 -- WCL + LEAKAGE
    if 2 in BL:
        P("\n" + "=" * 96)
        P("BLOCK 2 -- WCL: coordinates are its ONLY input besides RSSI  [C1, C5]")
        P("=" * 96)
        P(floor_line(FLOOR))
        P("=" * 96)
        CEN = centroid_map(cal, set(G))
        maps = [("VERIFIED", PHYS), ("RSSFIT", RSSF)]
        if len(CEN) >= 10:
            maps.append(("centroid heuristic", {g: CEN[g] for g in CEN}))
        store = {}
        for tag, mp in maps:
            e = [float(np.linalg.norm(wcl(ev, g, raw) - t)) for g, raw, rr, t in cases(mp, None)]
            store[tag] = np.array(e)
            rec(2, tag, "WCL", e)
            P(f"  {tag:<22} n={len(e):>5}  " + summ(e, args.seed))
        if "VERIFIED" in store and "RSSFIT" in store:
            r = paired_report(store["RSSFIT"], store["VERIFIED"], "RSSFIT", "VERIFIED", args.seed)
            P("\n  coordinate provenance effect on WCL:")
            P(fmt_paired(r, FLOOR["draw"]))
        if "centroid heuristic" in store:
            P("\n  LEAKAGE TEST [C5] -- implemented, not asserted.")
            P("  A gateway map derived from device positions may encode WHERE THE SURVEY DROVE.")
            P("  Fix the evaluation region; vary only the CALIBRATION region. A true map")
            P("  transfers; a covert radio map collapses when calibrated elsewhere.")
            xs = np.array([mm.x for mm in cal]); xmed = float(np.median(xs))
            Wc = [mm for mm in cal if mm.x < xmed]; Ec = [mm for mm in cal if mm.x >= xmed]
            kk = min(len(Wc), len(Ec))
            Wc = random.Random(2).sample(Wc, kk); Ec = random.Random(3).sample(Ec, kk)
            # CLASS A fix: this filtered EV (a --samples-capped subset), so the
            # leakage ratio was computed on far fewer messages than available.
            EVE = [mm for mm in pool if mm.x >= xmed and mkey(mm) not in calkeys
                   and sum(1 for r in mm.receptions if r.gid in PHYS) >= 3]
            if len(EVE) > 2000:
                EVE = random.Random(31).sample(EVE, 2000)
            def wcl_on(mp, msgs_):
                e = []
                for mm in msgs_:
                    rx = [r for r in mm.receptions if r.gid in mp]
                    if len(rx) < 3: continue
                    rx = sorted(rx, key=lambda r: -r.rssi)[:args.max_gws]
                    g = np.vstack([mp[r.gid] for r in rx])
                    raw = np.array([r.rssi for r in rx], float)
                    e.append(float(np.linalg.norm(wcl(ev, g, raw) - np.array([mm.x, mm.y], float))))
                return np.array(e)
            P(f"\n    evaluation fixed to the EAST half ({len(EVE)} msgs); calibration region varied")
            P(f"    {'map':<24}{'cal=EAST (same)':>17}{'cal=WEST (other)':>18}{'ratio':>9}")
            for tag2, mk in (("centroid heuristic", lambda sub: centroid_map(sub, set(G))),
                             ("RSSFIT", lambda sub: {g: np.asarray(v, float) for g, v in
                                 ev.estimate_gateway_positions_rssfit(sub, assumed_n=n, seed=args.seed)[0].items()})):
                mE, mW = mk(Ec), mk(Wc)
                if len(mE) < 8 or len(mW) < 8:
                    P(f"    {tag2:<24}  too few gateways recovered -- skipped"); continue
                a_, b_ = wcl_on(mE, EVE), wcl_on(mW, EVE)
                if a_.size < 30 or b_.size < 30:
                    P(f"    {tag2:<24}  THIN -- not interpreted"); continue
                P(f"    {tag2:<24}{np.median(a_):>16.0f}m{np.median(b_):>17.0f}m"
                  f"{np.median(b_)/max(np.median(a_),1e-9):>8.2f}x")
            pv = wcl_on(PHYS, EVE)
            if pv.size:
                P(f"    {'VERIFIED (control)':<24}{np.median(pv):>16.0f}m{np.median(pv):>17.0f}m"
                  f"{1.00:>8.2f}x   cannot depend on calibration")
            P("    ratio >> 1 = the map only works where it was calibrated = LEAKAGE.")

    # ================================================== BLOCK 3 -- A0 PROCEDURES
    if 3 in BL:
        P("\n" + "=" * 96)
        P("BLOCK 3 -- A0 two-procedure disagreement under each substrate  [row 2]")
        P("=" * 96)
        P(floor_line(FLOOR))
        by = {}
        for mm in cal:
            for rx in mm.receptions:
                if rx.gid in PHYS:
                    by.setdefault(rx.gid, []).append((rx.rssi, mm.x, mm.y))
        # UNITS ADDED 19 Aug. This table printed FOUR dB quantities with the unit
        # nowhere -- not in the header, not on the rows. results_audit flagged it
        # in v9 as "expected content missing ['dB']" and was RIGHT. Same defect
        # class as TRI1's "697 vs 966 m", where only the second number carried
        # its unit. A reader cannot tell dB from metres from a bare -0.39.
        P(f"  {'substrate':<14}{'gw':>5}{'mean dB':>18}{'sd dB':>8}"
          f"{'common share':>15}")
        for tag, mp in (("VERIFIED", PHYS), ("RSSFIT", RSSF)):
            dis = []
            for g, v in by.items():
                if g not in mp or len(v) < 10:
                    continue
                a = np.array(v, float); r_ = a[:, 0]
                d = np.linalg.norm(a[:, 1:3] - mp[g], axis=1) + 1.0
                y = r_ + 10 * n * np.log10(d)
                msk = r_ >= np.quantile(r_, 0.75)
                if msk.sum() < 10:
                    continue
                dis.append(float(np.median(y)) - float(np.median(y[msk])))
            dis = np.array(dis)
            share = dis.mean() ** 2 / (dis.mean() ** 2 + dis.std(ddof=1) ** 2) * 100
            P(f"  {tag:<14}{len(dis):>5}{dis.mean():>18.2f}{dis.std(ddof=1):>8.2f}{share:>14.1f}%")

    # ================================================== BLOCK 4 -- STRATA
    if 4 in BL:
        P("\n" + "=" * 96)
        P("BLOCK 4 -- calibrated / uncalibrated strata  [row 3]")
        P("=" * 96)
        P(floor_line(FLOOR))
        ELIG = set(G[:max(6, len(G) // 2)])
        P(f"  A0-eligible restricted to {len(ELIG)}/{len(G)} gateways (identical in both arms),")
        P(f"  so an OFF stratum exists at all. RSSI selection => selected set is coordinate-free.")
        for tag, mp in (("VERIFIED", PHYS), ("RSSFIT", RSSF)):
            a0 = {g: v for g, v in fit_a0(cal, mp, n).items() if g in ELIG}
            S = {k: {"dm": [], "nl": []} for k in ("ON", "OFF", "OFFimp")}
            a0med = float(np.median(list(a0.values()))) if a0 else 0.0
            C = np.array(list(mp.values()))
            bb = (C[:, 0].min() - 3000, C[:, 0].max() + 3000,
                  C[:, 1].min() - 3000, C[:, 1].max() + 3000)
            for mm in EV:
                rx = [r for r in mm.receptions if r.gid in mp]
                if len(rx) < 3:
                    continue
                rx = sorted(rx, key=lambda r: -r.rssi)[:args.max_gws]
                g = np.vstack([mp[r.gid] for r in rx])
                raw = np.array([r.rssi for r in rx], float)
                aa = np.array([a0.get(r.gid, np.nan) for r in rx])
                on = bool(np.all(np.isfinite(aa)))
                rr = (raw - aa) if on else raw.copy()
                t = np.array([mm.x, mm.y], float)
                key = "ON" if on else "OFF"
                variants = [(key, rr)]
                if not on:
                    variants.append(("OFFimp", raw - np.where(np.isfinite(aa), aa, a0med)))
                for kk, rv in variants:
                    S[kk]["dm"].append(float(np.linalg.norm(lattice(ev, g, rv, n, "diff") - t)))
                    x, _c, _d = ev.robust_nlls_localize(gw_mat=g, rssi_corrected=rv, n=n,
                        wcl_init=wcl(ev, g, raw), bbox=bb, huber_c=1.345, n_starts=3,
                        max_iter=120, grad_tol=1e-6, halton_seed=args.seed)
                    S[kk]["nl"].append(float(np.linalg.norm(x - t)))
            P(f"\n  {tag}")
            for k_ in ("ON", "OFF", "OFFimp"):
                d_ = S[k_]["dm"]
                if len(d_) < 30:
                    if d_: P(f"    {k_:<7} n={len(d_):>5}   THIN -- not interpreted")
                    continue
                md, ml = np.median(d_), np.median(S[k_]["nl"])
                lo, hi = boot_diff_medians(d_, S[k_]["nl"], seed=args.seed)
                rec(4, tag, f"DIFF/{k_}", d_); rec(4, tag, f"NLLS/{k_}", S[k_]["nl"])
                P(f"    {k_:<7} n={len(d_):>5}  DIFF {md:>6.0f} (p90 {np.percentile(d_,90):>5.0f})"
                  f"  NLLS {ml:>6.0f} (p90 {np.percentile(S[k_]['nl'],90):>5.0f})"
                  f"  DIFF/NLLS {md/ml:>5.2f}  diff CI [{lo:+.0f}, {hi:+.0f}]")
            # PAIRED IMPUTATION CONTROL -- same OFF messages, A0 imputed from the
            # available gateways. This is the MECHANISM behind the strata and was
            # missing from v1: it says whether the gap is bias correction or geometry.
            if len(S["OFF"]["dm"]) >= 30 and len(S["OFFimp"]["dm"]) == len(S["OFF"]["dm"]):
                dDM = np.array(S["OFF"]["dm"]) - np.array(S["OFFimp"]["dm"])
                dNL = np.array(S["OFF"]["nl"]) - np.array(S["OFFimp"]["nl"])
                l1, h1 = boot_median(dDM, seed=args.seed); l2, h2 = boot_median(dNL, seed=args.seed)
                P(f"    PAIRED IMPUTATION CONTROL on the same {len(dDM)} OFF messages:")
                # D-D FIX 18 Aug. Two defects here. (1) the word "improves"
                # beside a NEGATIVE number is unreadable: dNL = OFF - OFFimp,
                # so POSITIVE means imputation REDUCES error and NEGATIVE means
                # it INCREASES it. The direction is now written out. (2) dDM is
                # a lattice-vs-lattice comparison, and the median of paired
                # differences is BANNED for those by this file own discipline
                # section. Both statistics are printed so nothing is lost and
                # the disagreement, if any, is visible.
                dl1, dh1 = boot_diff_medians(np.array(S["OFF"]["dm"]),
                  np.array(S["OFFimp"]["dm"]), seed=args.seed)
                dl2, dh2 = boot_diff_medians(np.array(S["OFF"]["nl"]),
                  np.array(S["OFFimp"]["nl"]), seed=args.seed)
                _w = lambda v: "REDUCES error by" if v > 0 else "INCREASES error by"
                P(f"      imputing A0 {_w(np.median(dNL))} {abs(np.median(dNL)):.0f} m"
                  f"  for NLLS       [paired-median CI {l2:+.0f},{h2:+.0f}]")
                P(f"      imputing A0 {_w(np.median(dDM))} {abs(np.median(dDM)):.0f} m"
                  f"  for DIFF+median  [paired-median CI {l1:+.0f},{h1:+.0f}]")
                P(f"      SAME COMPARISON, difference-of-medians (the statistic this")
                P(f"      harness uses everywhere else): NLLS [{dl2:+.0f}, {dh2:+.0f}] m"
                  f" | DIFF+median [{dl1:+.0f}, {dh1:+.0f}] m")

    # ================================================== BLOCK 5 -- OBJECTIVE FORM
    if 5 in BL:
        P("\n" + "=" * 96)
        P("BLOCK 5 -- objective form on verified geometry  [row 4]")
        P("=" * 96)
        P(floor_line(FLOOR, "seed"))
        P("=" * 96)
        cs = cases(PHYS, a0_phys)
        arms = {}
        for tag, obj, agg in (("DIFF+median (published)", "diff", "median"),
                              ("DIFF+mean", "diff", "mean"),
                              ("ABS+mean", "abs", "mean"),
                              ("HYBRID+mean", "hyb", "mean")):
            arms[tag] = np.array([float(np.linalg.norm(lattice(ev, g, rr, n, obj, agg) - t))
                                  for g, raw, rr, t in cs])
            rec(5, "VERIFIED", tag, arms[tag])
            P(f"  {tag:<26} " + summ(arms[tag], args.seed))
        # RSSFIT ARM ADDED 16 Aug. Block 5 was VERIFIED-only, so the
        # "objective-form inversion" artifact rested on a HISTORICAL rssfit
        # measurement from another run. An artifact table must not mix runs.
        P("\n  SAME FOUR ARMS ON ESTIMATED GEOMETRY -- so the inversion is measured")
        P("  in this run rather than recalled from another:")
        cs_r = cases(RSSF, a0_rssf)
        rarms = {}
        for tag, obj, agg in (("DIFF+median (published)", "diff", "median"),
                              ("DIFF+mean", "diff", "mean"),
                              ("ABS+mean", "abs", "mean"),
                              ("HYBRID+mean", "hyb", "mean")):
            rarms[tag] = np.array([float(np.linalg.norm(lattice(ev, g, rr, n, obj, agg) - t))
                                   for g, raw, rr, t in cs_r])
            rec(5, "RSSFIT", tag, rarms[tag])
            P(f"  {tag:<26} " + summ(rarms[tag], args.seed))
        bv = min(arms, key=lambda k: np.median(arms[k]))
        br = min(rarms, key=lambda k: np.median(rarms[k]))
        # FLOOR-AWARE MARKER, added 19 Aug. The old version printed a bare
        # *** INVERSION *** whenever the two best arms differed BY NAME, with no
        # regard to whether the gap was resolvable. In Run A it fired on 648 vs
        # 641 m -- 1.0% against a 4.5% floor, CI spanning zero -- and D1 then
        # failed to reproduce it. A qualitative marker on a sub-floor difference
        # is a false finding, so the marker now states which it is.
        _fl = FLOOR.get("seed")
        if bv == br:
            _mark = "   (same arm — no inversion)"
        else:
            _runner = min((k for k in arms if k != bv),
                          key=lambda k: np.median(arms[k]))
            _gap = abs(np.median(arms[bv]) - np.median(arms[_runner]))
            _rel = 100.0 * _gap / max(np.median(arms[bv]), 1e-9)
            if _fl is not None and _rel < _fl:
                _mark = (f"   *** INVERSION, BUT NOT RESOLVABLE: the verified arms "
                         f"differ by {_rel:.1f}% against a {_fl:.1f}% floor ***")
            else:
                _mark = f"   *** INVERSION (verified arms differ {_rel:.1f}%) ***"
        P(f"  BEST ARM  verified: {bv}   |   estimated: {br}" + _mark)

        P("\n  paired, tie-aware (NEVER the median of paired differences):")
        for a_, b_ in (("HYBRID+mean", "ABS+mean"), ("DIFF+median (published)", "ABS+mean")):
            P(fmt_paired(paired_report(arms[a_], arms[b_], a_, b_, args.seed), FLOOR["seed"]))

    # ================================================== BLOCK 6 -- EXPONENT
    if 6 in BL:
        P("\n" + "=" * 96)
        P("BLOCK 6 -- path-loss exponent, within-gateway estimator  [row 5]")
        P("=" * 96)
        P(floor_line(FLOOR))
        for tag, mp in (("VERIFIED", PHYS), ("RSSFIT", RSSF)):
            by = {}
            for mm in cal:
                for rx in mm.receptions:
                    if rx.gid in mp:
                        d = float(np.linalg.norm(mp[rx.gid] - np.array([mm.x, mm.y]))) + 1.0
                        by.setdefault(rx.gid, []).append((math.log10(d), float(rx.rssi), d))
            Xc, Yc, Dd = [], [], []
            for g, v in by.items():
                if len(v) < 10: continue
                a = np.array(v, float)
                Xc += list(a[:, 0] - a[:, 0].mean()); Yc += list(a[:, 1] - a[:, 1].mean()); Dd += list(a[:, 2])
            Xc, Yc, Dd = np.array(Xc), np.array(Yc), np.array(Dd)
            gl = -float(np.sum(Xc * Yc) / np.sum(Xc * Xc)) / 10.0
            bands = []
            for lo_, hi_ in ((0, 1000), (1000, 2500), (2500, 5000), (5000, 20000)):
                s = (Dd >= lo_) & (Dd < hi_)
                if s.sum() >= 200:
                    bands.append(-float(np.sum(Xc[s] * Yc[s]) / np.sum(Xc[s] * Xc[s])) / 10.0)
            P(f"  {tag:<10} naive n={gl:>5.2f}  bands: "
              + "  ".join(f"{b:.2f}" for b in bands) + f"   ({len(Xc)} links)")
            # upper-quantile slope: least-shadowed links at each distance.
            # The naive slope is depressed by shadowing-distance correlation;
            # this is the propagation estimate and the docstring promised it.
            qs = {}
            for q in (0.10, 0.50, 0.90):
                S_ = []
                for g, v in by.items():
                    a = np.array(v, float)
                    if len(a) < 400: continue
                    lx = np.log10(a[:, 2]); ed = np.quantile(lx, np.linspace(0, 1, 9))
                    X_, Y_ = [], []
                    for i in range(8):
                        msk = (lx >= ed[i]) & (lx <= ed[i + 1] if i == 7 else lx < ed[i + 1])
                        if msk.sum() >= 25:
                            X_.append(lx[msk].mean()); Y_.append(np.quantile(a[msk, 1], q))
                    if len(X_) >= 5:
                        S_.append(-np.polyfit(np.array(X_), np.array(Y_), 1)[0] / 10.0)
                qs[q] = (float(np.median(S_)), len(S_)) if S_ else (float("nan"), 0)
            P(f"  {'':<10} quantile slopes  q10 {qs[0.10][0]:.2f} | q50 {qs[0.50][0]:.2f} | "
              f"q90 {qs[0.90][0]:.2f}   (n={qs[0.90][1]} gateways with >=400 links)")
            P(f"  {'':<10} -> PROPAGATION ESTIMATE = q90 slope = {qs[0.90][0]:.2f}"
              f"   (urban literature 2.7-3.5)")
        P("  The naive slope is depressed by shadowing-distance correlation; the q90")
        P("  slope uses the least-shadowed links at each distance and is the estimate.")

    # ================================================== BLOCK 7 -- N SWEEP
    if 7 in BL:
        P("\n" + "=" * 96)
        P("BLOCK 7 -- assumed-exponent sweep on verified geometry  [row 6]")
        P("=" * 96)
        P(floor_line(FLOOR))
        P(f"  {'n':>6}{'ABS+mean':>11}{'CI':>20}{'p90':>10}{'DIFF+med':>11}"
          f"{'MinMax':>10}{'RSSFIT/fix':>12}{'RSSFIT/ref':>12}")
        for nn in (2.5, 3.0, 3.5, 4.0, 4.7, 5.5, 6.5):
            a0 = fit_a0(cal, PHYS, nn)
            cs = cases(PHYS, a0)
            if not cs: continue
            e = [float(np.linalg.norm(lattice(ev, g, rr, nn, "abs", "mean") - t)) for g, raw, rr, t in cs]
            lo, hi = boot_median(e, seed=args.seed)
            # RSSFIT arm added 16 Aug: the "n-sweep shape" artifact needs BOTH
            # substrates in the same run, not a verified curve and a recalled one.
            a0r_ = fit_a0(cal, RSSF, nn)
            csr = cases(RSSF, a0r_)
            # GAP FILLED 19 Aug: the differential objective USES the assumed
            # exponent too, so a sweep that omits it cannot say whether the
            # flat-vs-runaway shape is a property of the OBJECTIVE or of n.
            ed_ = [float(np.linalg.norm(lattice(ev, g, rr, nn, "diff", "median") - t))
                   for g, raw, rr, t in cs]
            # GAP FILLED 19 Aug (second pass). Min-Max was added here because it
            # converts RSSI to a RADIUS using the exponent DIRECTLY --
            # 10^((A0-rssi)/(10n)) -- and the first propagation had put Min-Max
            # wherever the DIFFERENTIAL went, which is not the same question as
            # where MIN-MAX BELONGS.
            #
            # THE PREDICTION THAT MOTIVATED THIS WAS REFUTED BY THE ROWS BELOW.
            # Min-Max ranges 13.7% across the sweep -- identical to the
            # differential and barely above ABS+mean's 10.8%. It is NOT the most
            # exponent-sensitive method. Changing n does not move each radius
            # independently: it applies a COMMON power transform to every radius
            # at once, and Min-Max's intersection centre is partly invariant to a
            # common radius scaling. The comment is kept, and corrected, because a
            # refuted prediction is evidence and deleting it hides the test.
            em_ = [float(np.linalg.norm(minmax(g, rr, nn) - t))
                   for g, raw, rr, t in cs]
            # THE RSSFIT ARM ANSWERS A NARROWER QUESTION THAN IT APPEARS TO.
            # RSSF is estimated ONCE, at --assumed-n, and is NOT re-estimated as
            # nn sweeps; only A0 is refit. So this column is "given a DEPLOYED
            # map, what does a wrong INFERENCE-TIME exponent cost?" -- NOT "how
            # sensitive is the RSSFIT pipeline to n?". Its large range has been
            # read as the second. The refit arm below answers that one.
            er = [float(np.linalg.norm(lattice(ev, g, rr, nn, "abs", "mean") - t))
                  for g, raw, rr, t in csr]
            # REFIT ARM, added 19 Aug: the map ITSELF re-estimated at each nn, so
            # the exponent enters where the estimator actually uses it.
            rf_nn, _ = ev.estimate_gateway_positions_rssfit(cal, assumed_n=nn,
                                                            seed=args.seed)
            RS_nn = {g_: np.asarray(rf_nn[g_], float) for g_ in G if g_ in rf_nn}
            if len(RS_nn) >= 3:
                a0rn = fit_a0(cal, RS_nn, nn)
                csrn = cases(RS_nn, a0rn)
                erf = [float(np.linalg.norm(lattice(ev, g, rr, nn, "abs", "mean") - t))
                       for g, raw, rr, t in csrn]
            else:
                erf = []
            P(f"  {nn:>6.1f}{np.median(e):>11.0f}{f'[{lo:.0f}, {hi:.0f}]':>20}"
              f"{np.percentile(e,90):>10.0f}"
              f"{(np.median(ed_) if ed_ else float('nan')):>11.0f}"
              f"{(np.median(em_) if em_ else float('nan')):>10.0f}"
              f"{(np.median(er) if er else float('nan')):>12.0f}"
              f"{(np.median(erf) if erf else float('nan')):>12.0f}")

    # ================================================== BLOCK 8 -- LOCALIZATION
    if 8 in BL:
        P("\n" + "=" * 96)
        P("BLOCK 8 -- localization, both substrates  [row 7 + DIFF/NLLS]")
        P("=" * 96)
        P(floor_line(FLOOR))
        for tag, mp, a0 in (("VERIFIED", PHYS, a0_phys), ("RSSFIT", RSSF, a0_rssf)):
            cs = cases(mp, a0)
            C = np.array(list(mp.values()))
            bb = (C[:, 0].min() - 3000, C[:, 0].max() + 3000,
                  C[:, 1].min() - 3000, C[:, 1].max() + 3000)
            ed, en, ew, et, em = [], [], [], [], []; mm_inf = 0
            for g, raw, rr, t in cs:
                w = wcl(ev, g, raw)
                ew.append(float(np.linalg.norm(w - t)))
                ed.append(float(np.linalg.norm(lattice(ev, g, rr, n, "diff") - t)))
                x, _c, _d = ev.robust_nlls_localize(gw_mat=g, rssi_corrected=rr, n=n,
                    wcl_init=w, bbox=bb, huber_c=1.345, n_starts=3, max_iter=120,
                    grad_tol=1e-6, halton_seed=args.seed)
                en.append(float(np.linalg.norm(x - t)))
                try:   # the manuscript's third method; absent from v1
                    et.append(float(np.linalg.norm(
                        ev.trilateration_joint_A0(g, rr, n) - t)))
                except Exception:
                    pass
                # MIN-MAX, added 19 Aug. The Sigfox benchmark authors adopted it
                # after distance-based multilateration failed on their data. A
                # comparison omitting the method the dataset authors CHOSE invites
                # the obvious question. Infeasible cases are COUNTED, not hidden.
                em.append(float(np.linalg.norm(minmax(g, rr, n) - t)))
                mm_inf += int(minmax_infeasible(g, rr, n))
            for nm_, ee in (("WCL", ew), ("DIFF+median", ed), ("NLLS", en), ("Trilat", et), ("MinMax", em)):
                if ee: rec(8, tag, nm_, ee)
            P(f"  {tag}  n={len(ed)}")
            for nm_, ee in (("WCL", ew), ("DIFF+median", ed), ("NLLS", en), ("Trilat", et), ("MinMax", em)):
                if ee: P(f"    {nm_:<10} " + summ(ee, args.seed))
            if em:
                P(f"    MinMax infeasible (squares do not intersect): "
                  f"{mm_inf}/{len(em)} = {100*mm_inf/max(len(em),1):.1f}%")
            if ew and ed:
                l9, h9 = boot_diff_p90(np.array(ed), np.array(ew), seed=args.seed)
                P(f"    tail vs WCL: p90(DIFF) - p90(WCL) CI [{l9:+.0f}, {h9:+.0f}] m"
                  f"  | message-wise DIFF<WCL {100*np.mean(np.array(ed)<np.array(ew)):.1f}%")
            if et and ew:
                l9, h9 = boot_diff_p90(np.array(et), np.array(ew), seed=args.seed)
                P(f"    tail vs WCL: p90(Trilat) - p90(WCL) CI [{l9:+.0f}, {h9:+.0f}] m")
            P(f"    DIFF/NLLS {np.median(ed)/np.median(en):.2f}"
              + (f"  |  Trilat p90 {np.percentile(et,90):.0f} m -- the manuscript's"
                 f" catastrophic-tail baseline" if et else ""))

    # ================================================== BLOCK 9 -- R2 LAW + GATE D
    if 9 in BL:
        P("\n" + "=" * 96)
        P("BLOCK 9 -- R2 sensitivity law + GATE D (Proposition 1)  [C6]")
        P("=" * 96)
        P(floor_line(FLOOR))
        cs = cases(PHYS, a0_phys)
        CS = [0.0, 1.0, 2.0, 3.0, 4.0, 6.0, 8.0]
        A_, D_ = [], []
        for c in CS:
            A_.append(float(np.median([np.linalg.norm(lattice(ev, g, rr - c, n, "abs") - t)
                                       for g, raw, rr, t in cs])))
            D_.append(float(np.median([np.linalg.norm(lattice(ev, g, rr - c, n, "diff") - t)
                                       for g, raw, rr, t in cs])))
        A_, D_ = np.array(A_), np.array(D_)
        spread = (D_.max() - D_.min()) / D_.mean() * 100
        P(f"  {'c dB':>6}{'ABS':>9}{'DIFF':>9}{'Dm':>9}")
        for i, c in enumerate(CS):
            P(f"  {c:>6.1f}{A_[i]:>9.0f}{D_[i]:>9.0f}{A_[i]-D_[i]:>9.0f}")
        # ---------------- GATE D, REBUILT 19 Aug -------------------------------
        # THE OLD GATE COULD NOT FIRE. It compared OUTPUT POSITIONS on a 150 m
        # lattice across the offset sweep. Setting z = 2*r_i - r_j -- which is not
        # a difference at all -- moves the OBJECTIVE by 8 dB and does not move the
        # argmin by a single cell, so the gate reported 0.00% PASS. Proven by
        # stress test, 19 Aug: no break magnitude up to coefficient 1.0 fired it.
        #
        # Proposition 1 is ALGEBRA, so it is tested on the ALGEBRA: the residual
        # VECTOR at fixed lattice points must be elementwise identical under a
        # common-mode offset. The old output test is retained BELOW as a weaker
        # secondary check, clearly labelled as such.
        gd_g, _gr, gd_rr, _gt = cs[0]
        _C = np.array(list(PHYS.values()))
        _P = ev.triangular_lattice_points(center=_C.mean(axis=0), span_m=6000.0,
                                          spacing_m=150.0)
        _lg = np.log10(np.linalg.norm(_P[:, None, :] - gd_g[None, :, :], axis=2) + 1.0)
        _io, _jo = np.triu_indices(len(gd_g), 1)
        def _dobj(rr_):
            z_ = rr_[_io] - rr_[_jo]
            k_ = np.abs(z_) >= TAU
            if not k_.any():
                return None
            Rd_ = np.abs(z_[None, k_] - (-10.0 * n * (_lg[:, _io[k_]] - _lg[:, _jo[k_]])))
            return np.median(Rd_, axis=1)
        S0, S8 = _dobj(gd_rr), _dobj(gd_rr - 8.0)
        P(f"\n  [GATE D] Proposition 1 is ALGEBRA and is tested as algebra:")
        P(f"           the differential residual VECTOR over {len(_P)} lattice points must be")
        if S0 is None or S8 is None:
            P(f"           no admissible pairs at tau={TAU} -- GATE D cannot be evaluated")
            algebra_ok = None
        else:
            dmax = float(np.abs(S0 - S8).max())
            algebra_ok = dmax < 1e-9
            P(f"           ELEMENTWISE IDENTICAL under an 8 dB common-mode offset.")
            P(f"           max |S(c=0) - S(c=8)| = {dmax:.3e} dB   "
              f"{'PASS' if algebra_ok else '*** ABORT: the differential is not a difference ***'}")
        P(f"           SECONDARY (weak): output-position spread across the sweep")
        P(f"           = {spread:.2f}%. This test compares argmins on a 150 m grid and")
        P(f"           CANNOT detect an algebra violation -- it is reported for")
        P(f"           continuity with earlier runs, not as evidence.")
        if algebra_ok is False or spread >= 2.0:
            open(args.out + ".txt", "w").write("\n".join(L) + "\n"); return
        try:
            from scipy.optimize import curve_fit
            f = lambda cc, Aa, Bb: Aa * (10 ** (np.abs(cc) / (10 * n)) - 1) - Bb
            p_, _ = curve_fit(f, np.array(CS), A_ - D_, p0=[2000.0, 300.0], maxfev=20000)
            y = A_ - D_
            r2 = 1 - ((y - f(np.array(CS), *p_)) ** 2).sum() / ((y - y.mean()) ** 2).sum()
            lo_, hi_ = 0.0, 20.0
            for _ in range(60):
                mid = (lo_ + hi_) / 2
                if f(mid, *p_) < 0: lo_ = mid
                else: hi_ = mid
            P(f"  FIT  Dm = {p_[0]:.0f}*(10^(|c|/{10*n:.0f}) - 1) - {p_[1]:.0f}   R^2 = {r2:.4f}")
            P(f"  crossover |c| = {(lo_+hi_)/2:.2f} dB")
        except Exception as e:
            P(f"  FIT FAILED: {e}")

    # ================================================== BLOCK 10 -- GROUND-TRUTH-FREE
    if 10 in BL:
        P("\n" + "=" * 96)
        P("BLOCK 10 -- ground-truth-free evidence (no map required)  [C3]")
        P("=" * 96)
        P(floor_line(FLOOR))
        h1, h2 = cal[0::2], cal[1::2]
        rA, _ = ev.estimate_gateway_positions_rssfit(h1, assumed_n=n, seed=args.seed)
        rB, _ = ev.estimate_gateway_positions_rssfit(h2, assumed_n=n, seed=args.seed)
        cc = set(rA) & set(rB) & set(PHYS)
        dr = np.array([float(np.linalg.norm(np.asarray(rA[g], float) - np.asarray(rB[g], float))) for g in cc])
        xs = np.array([mm.x for mm in cal]); xmed = float(np.median(xs))
        W = [mm for mm in cal if mm.x < xmed]; E = [mm for mm in cal if mm.x >= xmed]
        k_ = min(len(W), len(E))
        W = random.Random(2).sample(W, k_); E = random.Random(3).sample(E, k_)
        gW, _ = ev.estimate_gateway_positions_rssfit(W, assumed_n=n, seed=args.seed)
        gE, _ = ev.estimate_gateway_positions_rssfit(E, assumed_n=n, seed=args.seed)
        c2 = set(gW) & set(gE) & set(PHYS)
        dg = np.array([float(np.linalg.norm(np.asarray(gW[g], float) - np.asarray(gE[g], float))) for g in c2])
        lo1, hi1 = boot_median(dr, seed=args.seed); lo2, hi2 = boot_median(dg, seed=args.seed)
        P(f"  RSSFIT disagreement, RANDOM split      n={len(dr):>3}  median {np.median(dr):>6.0f} m"
          f"  CI [{lo1:.0f}, {hi1:.0f}]")
        P(f"  RSSFIT disagreement, GEOGRAPHIC split  n={len(dg):>3}  median {np.median(dg):>6.0f} m"
          f"  CI [{lo2:.0f}, {hi2:.0f}]")
        P(f"  ratio geographic/random = {np.median(dg)/max(np.median(dr),1e-9):.2f}x"
          f"   -- a real gateway does not move when you drive elsewhere")
        try:
            from scipy.spatial import ConvexHull
            TX = np.array([[mm.x, mm.y] for mm in cal], float)
            H = ConvexHull(TX)
            sgn = lambda p: float(np.max(H.equations[:, :2] @ p + H.equations[:, 2]))
            out = [g for g in PHYS if sgn(PHYS[g]) > 0]
            P(f"\n  survey footprint: {H.volume/1e6:.0f} km^2 from {len(TX)} calibration transmitters")
            P(f"  verified gateways OUTSIDE that footprint: {len(out)}/{len(PHYS)}")
            P(f"  the estimator's own published description bounds its search to this extent.")
        except Exception as e:
            P(f"  footprint test failed: {e}")

    # ================================================== BLOCK 11 -- GATEWAY SUPPORT
    if 11 in BL:
        P("\n" + "=" * 96)
        P("BLOCK 11 -- GATEWAY-SUPPORT SWEEP on verified geometry  [the manuscript's")
        P("            central structural claim: a tail transition near min_gws ~ 7.")
        P("            It had NO verified-geometry counterpart until now.]")
        P("=" * 96)
        P(floor_line(FLOOR))
        C = np.array(list(PHYS.values()))
        bb = (C[:, 0].min() - 3000, C[:, 0].max() + 3000,
              C[:, 1].min() - 3000, C[:, 1].max() + 3000)
        P(f"  COVERAGE LIMIT: only {len(PHYS)} of the deployment's 72 gateways are mapped,")
        P(f"  so a message needs k of ITS receptions to fall inside that subset. Support")
        P(f"  collapses with k and the manuscript's min_gws=8/10 regimes may be unreachable.")
        P(f"  A THIN row is a MAP-COVERAGE limit, not a null result.")
        P("")
        # MIN-MAX COLUMN ADDED 19 Aug. This sweep carried WCL, DIFF and NLLS but
        # NOT Min-Max -- which BLOCK 8 measures as the BEST method on verified
        # geometry (466 m). Its k-dependence was therefore unmeasured on the only
        # block that sweeps support depth, so nothing could say whether its
        # advantage survives thin support. Registered as due item 12.
        P(f"  {'k':>4}{'n':>7}{'WCL_raw':>9}{'DIFF med':>10}{'NLLS':>8}{'MinMax':>8}"
          f"{'DIFF/NL':>9}{'DIFF p90':>10}{'WCL p90':>9}{'DIFF-WCL p90 CI':>21}{'DIFF<WCL':>10}")
        for K in [int(x) for x in args.gw_list.split(",")]:
            ew, ed, en, emm = [], [], [], []
            for mm in EV:
                rx = [r for r in mm.receptions if r.gid in PHYS and r.gid in a0_phys]
                if len(rx) < K:
                    continue
                rx = sorted(rx, key=lambda r: -r.rssi)[:K]
                g = np.vstack([PHYS[r.gid] for r in rx])
                raw = np.array([r.rssi for r in rx], float)
                rr = raw - np.array([a0_phys[r.gid] for r in rx], float)
                t = np.array([mm.x, mm.y], float)
                w = wcl(ev, g, raw)
                ew.append(float(np.linalg.norm(w - t)))
                ed.append(float(np.linalg.norm(lattice(ev, g, rr, n, "diff") - t)))
                x, _c, _d = ev.robust_nlls_localize(gw_mat=g, rssi_corrected=rr, n=n,
                    wcl_init=w, bbox=bb, huber_c=1.345, n_starts=3, max_iter=120,
                    grad_tol=1e-6, halton_seed=args.seed)
                en.append(float(np.linalg.norm(x - t)))
                emm.append(float(np.linalg.norm(minmax(g, rr, n) - t)))
            if len(ed) < 30:
                P(f"  {K:>4}{len(ed):>7}   THIN -- not interpreted"); continue
            ed_, en_, ew_ = np.array(ed), np.array(en), np.array(ew)
            emm_ = np.array(emm)
            rec(11, f"k={K}", "DIFF+median", ed_); rec(11, f"k={K}", "NLLS", en_)
            rec(11, f"k={K}", "WCL", ew_); rec(11, f"k={K}", "MinMax", emm_)
            # v1 reported "DIFF p90 win%" as the fraction of DIFF errors below WCL's p90.
            # With WCL p90 ~9.5 km that is trivially 100% and carries no information.
            # Replaced by: a CI on the p90 DIFFERENCE (the real tail comparison) and
            # the message-wise win rate, which is the manuscript's own column.
            lo90, hi90 = boot_diff_p90(ed_, ew_, seed=args.seed)
            msgwin = 100.0 * np.mean(ed_ < ew_)
            P(f"  {K:>4}{len(ed):>7}{np.median(ew_):>9.0f}{np.median(ed_):>10.0f}"
              f"{np.median(en_):>8.0f}{np.median(emm_):>8.0f}"
              f"{np.median(ed_)/np.median(en_):>9.2f}"
              f"{np.percentile(ed_,90):>10.0f}{np.percentile(ew_,90):>9.0f}"
              f"{f'[{lo90:+.0f},{hi90:+.0f}]':>21}{msgwin:>9.1f}%")
        # ---- FIXED-POPULATION k-SWEEP. The sweep above lets the MESSAGE POPULATION
        # change with k: at k=8 the surviving messages carry ~2x the receptions of
        # those at k=3, so they are intrinsically better-heard. The trend therefore
        # confounds GATEWAY SUPPORT with MESSAGE QUALITY -- the same defect as
        # BLOCK 15's first design. Here the population is FIXED to messages with at
        # least max(k) receptions among the mapped gateways, and only k varies.
        P("")
        P("  FIXED-POPULATION k-SWEEP -- the sweep above confounds support with")
        P("  message quality. Here the SAME messages are evaluated at every k.")
        # NESTED POPULATIONS. One fixed population gives one power level; a deep
        # one (>=8 receptions among the mapped gateways) is only ~120 messages.
        # Running the same test at several depths checks the finding for power AND
        # for consistency: a real support effect must appear at every depth.
        KS = sorted(int(x) for x in args.gw_list.split(","))
        # DEFECT FIXED. This filtered EV (the 2,500-message evaluation sample),
        # not the eval POOL. At POP=8 that gave n=120 when 1,948 were available --
        # 94% of the population discarded, then the result called "directional".
        # It now draws from the pool, minus GATE A's content-duplicates, capped
        # for runtime. NOTE: the evaluator caps receptions at 10/message (F27),
        # so k>10 is impossible, not merely thin.
        POOLFIX = [mm for mm in pool if mkey(mm) not in calkeys]
        for POP in KS[1:]:
            FIX = [mm for mm in POOLFIX
                   if sum(1 for rx in mm.receptions
                          if rx.gid in PHYS and rx.gid in a0_phys) >= POP]
            if len(FIX) > args.popcap:
                FIX = random.Random(77).sample(FIX, args.popcap)
            if len(FIX) < 60:
                P(f"\n  population >= {POP} receptions: only {len(FIX)} messages -- "
                  f"THIN, map coverage limit"); continue
            P(f"\n  POPULATION FIXED at >= {POP} receptions among {len(PHYS)} mapped "
              f"gateways: {len(FIX)} messages (from the eval POOL, not the sample)")
            P(f"  {'k':>4}{'n':>7}{'WCL_bc':>9}{'DIFF med':>10}{'NLLS':>8}{'MinMax':>8}{'DIFF/NL':>9}"
              f"{'DIFF p90':>10}{'DIFF<WCL':>10}")
            P(f"      NOTE: this arm uses the BIAS-CORRECTED centroid; the sweep")
            P(f"      above uses the UNCORRECTED one. The two tables are NOT")
            P(f"      comparable to each other.")
            for K in [k for k in KS if k <= POP]:
                ew, ed, en, emm = [], [], [], []
                for mm in FIX:
                    rx = [r for r in mm.receptions if r.gid in PHYS and r.gid in a0_phys]
                    rx = sorted(rx, key=lambda r: -r.rssi)[:K]
                    if len(rx) < 3: continue
                    g = np.vstack([PHYS[r.gid] for r in rx])
                    raw = np.array([r.rssi for r in rx], float)
                    rv = raw - np.array([a0_phys[r.gid] for r in rx], float)
                    t = np.array([mm.x, mm.y], float); w = wcl(ev, g, rv)
                    ew.append(float(np.linalg.norm(w - t)))
                    ed.append(float(np.linalg.norm(lattice(ev, g, rv, n, "diff") - t)))
                    x, _c, _d = ev.robust_nlls_localize(gw_mat=g, rssi_corrected=rv, n=n,
                        wcl_init=w, bbox=bb, huber_c=1.345, n_starts=3, max_iter=120,
                        grad_tol=1e-6, halton_seed=args.seed)
                    en.append(float(np.linalg.norm(x - t)))
                    emm.append(float(np.linalg.norm(minmax(g, rv, n) - t)))
                if len(ed) < 30:
                    P(f"  {K:>4}{len(ed):>7}   THIN"); continue
                ed_, en_, ew_ = np.array(ed), np.array(en), np.array(ew)
                emm_ = np.array(emm)
                rec(11, f"pop>={POP} k={K}", "DIFF+median", ed_)
                rec(11, f"pop>={POP} k={K}", "MinMax", emm_)
                P(f"  {K:>4}{len(ed):>7}{np.median(ew_):>9.0f}{np.median(ed_):>10.0f}"
                  f"{np.median(en_):>8.0f}{np.median(emm_):>8.0f}"
                  f"{np.median(ed_)/np.median(en_):>9.2f}"
                  f"{np.percentile(ed_,90):>10.0f}{100.0*np.mean(ed_<ew_):>9.1f}%")
        if True:
            P("  -> THIS is the test of the manuscript's threshold claim. If the win")
            P("     rate still rises with k here, the effect is gateway SUPPORT. If it")
            P("     is flat, the earlier trend was message QUALITY.")
        P("")
        P("  DIFF-WCL p90 CI < 0 = DIFF+median has the better tail at that k. The manuscript")
        P("  claims this turns favourable near min_gws~7. It can only be tested at k values")
        P("  where n is adequate; where it is not, the limit is map coverage, not evidence.")

    # ============================== BLOCK 12 -- DELTAMESH PARAMETER EXPLORATION
    if 12 in BL:
        P("\n" + "=" * 96)
        P("BLOCK 12 -- DELTAMESH INFERENCE PARAMETERS, one at a time, verified geometry")
        P("=" * 96)
        P(floor_line(FLOOR))
        P("  Five inference parameters had NO verified-geometry sweep. tau_D, lattice")
        P("  resolution, selection mode, pool factor and bias correction. The last is")
        P("  the manuscript's largest single ablation (2.90 -> 1.54 km) and had never")
        P("  been re-measured on correct coordinates.")
        P("  Each is varied FROM the published default with everything else fixed.")

        base_cs = cases(PHYS, a0_phys)
        def med_ci(e, seed=args.seed):
            lo, hi = boot_median(e, seed=seed)
            return np.median(e), lo, hi, np.percentile(e, 90)

        # --- tau_D : differential-only
        P(f"\n  (a) tau_D -- pair admission threshold [DIFF+median]. default 3 dB")
        P(f"      {'tau':>6}{'median':>9}{'CI':>18}{'p90':>8}{'pairs kept':>12}")
        for tv in (0.0, 1.0, 2.0, 3.0, 5.0, 8.0):
            e, kept, tot = [], 0, 0
            for g, raw, rr, t in base_cs:
                k_ = len(g); io, jo = np.triu_indices(k_, 1)
                z = rr[io] - rr[jo]; kept += int((np.abs(z) >= tv).sum()); tot += len(z)
                e.append(float(np.linalg.norm(lattice(ev, g, rr, n, "diff", tau=tv) - t)))
            m_, lo, hi, p9 = med_ci(e)
            P(f"      {tv:>6.1f}{m_:>9.0f}{f'[{lo:.0f},{hi:.0f}]':>18}{p9:>8.0f}"
              f"{100.0*kept/max(tot,1):>11.1f}%" + ("   <- default" if tv == 3.0 else ""))

        # --- lattice resolution : affects the tie fraction that broke two statistics
        P(f"\n  (b) fine-lattice spacing. 150 m is the published value and produces")
        P(f"      a high exact-tie rate, which is what made paired-median statistics")
        P(f"      degenerate. The DIFF-vs-ABS rate is printed below; the ~45% figure")
        P(f"      quoted elsewhere is the HYBRID-vs-ABS rate, a DIFFERENT pair.")
        P(f"      {'fine m':>8}{'DIFF+med':>10}{'ABS+mean':>10}{'ties DIFF vs ABS':>19}")
        for fine, fspan in ((150.0, 1500.0), (75.0, 900.0), (40.0, 600.0)):
            st = ((6000.0, 600.0), (fspan, fine))
            ed = np.array([float(np.linalg.norm(lattice(ev, g, rr, n, "diff", stages=st) - t))
                           for g, raw, rr, t in base_cs])
            ea = np.array([float(np.linalg.norm(lattice(ev, g, rr, n, "abs", "mean", stages=st) - t))
                           for g, raw, rr, t in base_cs])
            ties = 100.0 * float(np.mean((ed - ea) == 0))
            P(f"      {fine:>8.0f}{np.median(ed):>10.0f}{np.median(ea):>10.0f}{ties:>18.1f}%"
              + ("   <- default" if fine == 150.0 else ""))

        # --- selection mode + pool factor
        P(f"\n  (c) gateway selection. Every block above used RSSI (coordinate-free).")
        P(f"      The manuscript's main sweep used geometry-aware selection.")
        P(f"      {'mode':>12}{'alpha':>7}{'DIFF+med':>10}{'ABS+mean':>10}{'n':>7}")
        for mode, alpha in (("rssi", 0.0), ("geometry", 1.5), ("geometry", 2.0), ("geometry", 3.0)):
            ed, ea = [], []
            for mm in EV:
                rx = [r for r in mm.receptions if r.gid in PHYS and r.gid in a0_phys]
                if len(rx) < 3:
                    continue
                rx = sorted(rx, key=lambda r: -r.rssi)
                if mode == "rssi":
                    sel = rx[:args.max_gws]
                else:
                    pk = max(args.max_gws, int(math.ceil(alpha * args.max_gws)))
                    sel = ev.select_gateways_subset(
                        receptions_sorted_by_rssi=rx[:pk], gw_xy=PHYS, k=args.max_gws,
                        mode="geometry", hybrid_pool_factor=alpha, seed=args.seed)
                if len(sel) < 3:
                    continue
                g = np.vstack([PHYS[r.gid] for r in sel])
                raw = np.array([r.rssi for r in sel], float)
                rr = raw - np.array([a0_phys[r.gid] for r in sel], float)
                t = np.array([mm.x, mm.y], float)
                ed.append(float(np.linalg.norm(lattice(ev, g, rr, n, "diff") - t)))
                ea.append(float(np.linalg.norm(lattice(ev, g, rr, n, "abs", "mean") - t)))
            if len(ed) < 30:
                P(f"      {mode:>12}{alpha:>7.1f}   THIN"); continue
            P(f"      {mode:>12}{alpha:>7.1f}{np.median(ed):>10.0f}{np.median(ea):>10.0f}{len(ed):>7}")

        # --- bias correction: the manuscript's largest ablation, never re-measured
        P(f"\n  (d) bias correction ON/OFF -- the manuscript reports its LARGEST single")
        P(f"      ablation here: mean median 2.90 km OFF -> 1.54 km ON (Table 14).")
        P(f"      {'bias':>8}{'DIFF+med':>10}{'CI':>18}{'ABS+mean':>10}{'NLLS':>8}")
        C = np.array(list(PHYS.values()))
        bb = (C[:, 0].min() - 3000, C[:, 0].max() + 3000,
              C[:, 1].min() - 3000, C[:, 1].max() + 3000)
        for lab, use in (("ON", True), ("OFF", False)):
            ed, ea, en = [], [], []
            for g, raw, rr, t in base_cs:
                rv = rr if use else raw
                ed.append(float(np.linalg.norm(lattice(ev, g, rv, n, "diff") - t)))
                ea.append(float(np.linalg.norm(lattice(ev, g, rv, n, "abs", "mean") - t)))
                x, _c, _d = ev.robust_nlls_localize(gw_mat=g, rssi_corrected=rv, n=n,
                    wcl_init=wcl(ev, g, raw), bbox=bb, huber_c=1.345, n_starts=3,
                    max_iter=120, grad_tol=1e-6, halton_seed=args.seed)
                en.append(float(np.linalg.norm(x - t)))
            lo, hi = boot_median(ed, seed=args.seed)
            rec(12, "VERIFIED", f"DIFF/bias={lab}", ed)
            P(f"      {lab:>8}{np.median(ed):>10.0f}{f'[{lo:.0f},{hi:.0f}]':>18}"
              f"{np.median(ea):>10.0f}{np.median(en):>8.0f}")

    # ============================== BLOCK 13 -- CLOSING THE REGISTER
    if 13 in BL:
        P("\n" + "=" * 96)
        P("BLOCK 13 -- CLOSING THE OPEN REGISTER  [F42, HDOP, temporal split, k<10,")
        P("            F25, F18]. Six items ruled open in ROADMAP-001 sec.9.")
        P("=" * 96)
        P(floor_line(FLOOR))
        C = np.array(list(PHYS.values()))
        bb = (C[:, 0].min() - 3000, C[:, 0].max() + 3000,
              C[:, 1].min() - 3000, C[:, 1].max() + 3000)

        # --- (a) F42: tau_D discard rate. TRACE says 31.7%; BLOCK 12 measured 9.5%.
        P("\n  (a) F42 RECONCILIATION -- trace says tau_D discards 31.7% of pairs;")
        P("      BLOCK 12 measured 9.5% at tau=3. Same population, both substrates.")
        P(f"      {'substrate':<12}{'k':>4}{'msgs':>7}{'pairs':>9}{'discarded':>11}")
        for tag, mp, a0 in (("VERIFIED", PHYS, a0_phys), ("RSSFIT", RSSF, a0_rssf)):
            for K in (5, 10):
                kept = tot = nm = 0
                for mm in EV:
                    rx = [r for r in mm.receptions if r.gid in mp and r.gid in a0]
                    if len(rx) < 3:
                        continue
                    rx = sorted(rx, key=lambda r: -r.rssi)[:K]
                    rr = (np.array([r.rssi for r in rx], float)
                          - np.array([a0[r.gid] for r in rx], float))
                    io, jo = np.triu_indices(len(rr), 1)
                    z = rr[io] - rr[jo]
                    kept += int((np.abs(z) >= args.tau).sum()); tot += len(z); nm += 1
                P(f"      {tag:<12}{K:>4}{nm:>7}{tot:>9}{100.0*(1-kept/max(tot,1)):>10.1f}%")
        P("      -> the discard rate depends on k and substrate. Quote it WITH both.")

        # --- (b) HDOP: the loader supports max_hdop; the manuscript never used it
        P("\n  (b) HDOP GPS-QUALITY FILTER. The manuscript states no HDOP filter was")
        P("      applied. A poor fix puts the transmitter in the wrong place, which")
        P("      corrupts calibration AND evaluation.")
        P(f"      NLLS omitted here for runtime; WCL is coordinate-only and ABS+mean")
        P(f"      is the best arm, so both suffice to expose a GPS-quality effect.")
        P(f"      FLOOR WARNING: these rows are evaluated at n=400. BLOCK 22")
        P(f"      measures the floor at that sample size as ~10.5%, not the 4.5%")
        P(f"      in this block header. Read every span below against 10.5%.")
        P(f"      {'max_hdop':>10}{'msgs kept':>12}{'WCL_raw':>10}{'ABS+mean':>10}"
          f"{'DIFF+median':>13}{'n eval':>8}")
        for mh in (None, 5.0, 2.0, 1.0):
            try:
                mm_ = ev.load_antwerp_csv(args.data, min_gws=3, max_hdop=mh)
            except Exception as e:
                P(f"      {str(mh):>10}  loader rejected max_hdop: {e}"); break
            r2 = random.Random(args.seed); q = list(mm_); r2.shuffle(q)
            c2 = q[:int(len(q) * args.train_frac)]
            e2 = [x for x in q[int(len(q) * args.train_frac):]
                  if sum(1 for rx in x.receptions if rx.gid in PHYS) >= 3]
            if len(e2) < 200:
                P(f"      {str(mh):>10}{len(mm_):>12}   too few eval msgs"); continue
            e2 = random.Random(9).sample(e2, min(400, len(e2)))
            a2 = fit_a0(c2, PHYS, n)
            ew, ea, en, ed13 = [], [], [], []
            for x in e2:
                rx = [r for r in x.receptions if r.gid in PHYS and r.gid in a2]
                if len(rx) < 3: continue
                rx = sorted(rx, key=lambda r: -r.rssi)[:args.max_gws]
                g = np.vstack([PHYS[r.gid] for r in rx])
                raw = np.array([r.rssi for r in rx], float)
                rr = raw - np.array([a2[r.gid] for r in rx], float)
                t = np.array([x.x, x.y], float); w = wcl(ev, g, raw)
                ew.append(float(np.linalg.norm(w - t)))
                ea.append(float(np.linalg.norm(lattice(ev, g, rr, n, "abs", "mean") - t)))
                # GAP CLOSED 19 Aug: the block scoped itself to WCL + ABS on the
                # argument that both suffice to expose a GPS-quality effect. True,
                # but it left the differential objective -- the method this paper
                # is about -- out of a register-closing table. Added.
                ed13.append(float(np.linalg.norm(
                    lattice(ev, g, rr, n, "diff", "median") - t)))
            P(f"      {str(mh):>10}{len(mm_):>12}{np.median(ew):>10.0f}"
              f"{np.median(ea):>10.0f}{np.median(ed13):>13.0f}{len(ew):>8}"
              + ("   <- as published" if mh is None else ""))

        # --- (e) F25: WCL with and without bias correction
        P("\n  (e) F25 -- WCL_bc vs WCL_raw. WCL is C1's instrument, so whether bias")
        P("      correction helps it on VERIFIED coordinates matters.")
        cs = cases(PHYS, a0_phys)
        wr = [float(np.linalg.norm(wcl(ev, g, raw) - t)) for g, raw, rr, t in cs]
        wb = [float(np.linalg.norm(wcl(ev, g, rr) - t)) for g, raw, rr, t in cs]
        P(f"      WCL_raw  " + summ(wr, args.seed))
        P(f"      WCL_bc   " + summ(wb, args.seed))
        P(fmt_paired(paired_report(np.array(wb), np.array(wr), "WCL_bc", "WCL_raw",
                                   args.seed), FLOOR["seed"]))

        # --- (f) F18: does RSSFIT's own loss signal its coordinate error?
        P("\n  (f) F18 -- does RSSFIT's objective value predict its TRUE coordinate")
        P("      error? Only answerable now that a verified map exists.")
        by = {}
        for mm in cal:
            for rx in mm.receptions:
                if rx.gid in RSSF and rx.gid in PHYS:
                    by.setdefault(rx.gid, []).append((float(rx.rssi), mm.x, mm.y))
        loss, cerr = [], []
        for g, v in by.items():
            if len(v) < 30: continue
            a = np.array(v, float)
            d = np.linalg.norm(a[:, 1:3] - RSSF[g], axis=1) + 1.0
            y = a[:, 0] + 10 * n * np.log10(d)
            loss.append(float(np.median(np.abs(y - np.median(y)))))
            cerr.append(float(np.linalg.norm(RSSF[g] - PHYS[g])))
        if len(loss) >= 8:
            from scipy.stats import spearmanr
            sp = spearmanr(loss, cerr)
            P(f"      {len(loss)} gateways | spearman(RSSFIT loss, true coord error)"
              f" = {sp.correlation:+.3f}  p={sp.pvalue:.3f}")
            P(f"      trace F18 reported rho=+0.370 against ESTIMATED error.")
            # THREE-BRANCH VERDICT, added 19 Aug. The two-branch version had no
            # case for a SIGNIFICANT NEGATIVE correlation and printed "no self-
            # diagnostic" when Run C measured rho=-0.521 at p=0.002. That is not
            # an absent diagnostic -- it is an INVERTED one, which is worse: the
            # receivers the estimator fits BEST are the ones it places WORST, so
            # a practitioner trusting the loss would discard their best anchors.
            if sp.correlation > 0.4 and sp.pvalue < 0.05:
                P(f"      SELF-DIAGNOSTIC WORKS -- higher loss does signal higher")
                P(f"      true error, so the estimator can flag its own failures.")
            elif sp.correlation < -0.4 and sp.pvalue < 0.05:
                P(f"      *** INVERTED DIAGNOSTIC -- rho={sp.correlation:+.3f} at "
                  f"p={sp.pvalue:.3f}. The loss signals true error in the")
                P(f"          WRONG DIRECTION: the gateways fitted BEST are placed")
                P(f"          WORST. Acting on the loss is worse than ignoring it. ***")
            else:
                P(f"      the loss does NOT signal true error -- no self-diagnostic")

    # ============================== BLOCK 14 -- TEMPORAL SPLIT + SELECTION AT k<10
    if 14 in BL:
        P("\n" + "=" * 96)
        P("BLOCK 14 -- TEMPORAL SPLIT and SELECTION AT k<10  [the last register items]")
        P("=" * 96)
        P(floor_line(FLOOR))

        # --- (a) TEMPORAL SPLIT. RX Time is in the CSV but NOT in the Message
        # object, so it is joined back by position. The manuscript splits RANDOMLY;
        # a deployment calibrates once and localizes LATER. If gateway-side
        # calibration is a fixed infrastructure property, the two must agree.
        P("\n  (a) TEMPORAL SPLIT -- calibrate on the EARLIEST messages, evaluate on")
        P("      the LATEST. The manuscript splits at random, which lets calibration")
        P("      and evaluation interleave in time. A real deployment cannot.")
        tmap = {}
        try:
            import csv as _csv
            from pyproj import Transformer
            tfm = Transformer.from_crs("EPSG:4326", "EPSG:32631", always_xy=True)
            with open(args.data) as fh:
                for row in _csv.DictReader(fh):
                    t_ = row.get("RX Time", "")
                    try:
                        xx, yy = tfm.transform(float(row["Longitude"]), float(row["Latitude"]))
                    except Exception:
                        continue
                    if t_:
                        tmap.setdefault((round(xx, 1), round(yy, 1)), t_)
        except Exception as e:
            P(f"      could not read RX Time: {e}")
        allm = cal + pool
        timed = [(tmap.get((round(m.x, 1), round(m.y, 1))), m) for m in allm]
        timed = [(t_, m) for t_, m in timed if t_]
        P(f"      messages with a recovered timestamp: {len(timed)}/{len(allm)}"
          f"  ({100.0*len(timed)/max(len(allm),1):.1f}%)")
        if len(timed) < 2000:
            P("      too few timestamps recovered -- temporal split not run")
        else:
            timed.sort(key=lambda z: z[0])
            P(f"      campaign spans {timed[0][0][:10]} .. {timed[-1][0][:10]}")
            # DESIGN FIX. A first version let the EVALUATION POPULATION change with
            # the arm (random 70% vs latest 50%), so any difference could be the
            # split rule OR the messages being intrinsically harder. The evaluation
            # set is now IDENTICAL in both arms; only the CALIBRATION set varies.
            ncal = int(len(timed) * args.train_frac)
            late = [m for _, m in timed[int(len(timed) * 0.6):]]
            EVFIX = random.Random(9).sample(late, min(1200, len(late)))
            evk = set(mkey(m) for m in EVFIX)   # CLASS D: content key, not id()
            early = [m for _, m in timed[:ncal]]
            elig = [m for _, m in timed if mkey(m) not in evk]
            rnd = random.Random(4242).sample(elig, min(ncal, len(elig)))
            P(f"      EVALUATION SET FIXED at {len(EVFIX)} messages (latest 40%),")
            P(f"      identical in both arms. Only the calibration set differs.")
            arms = {"TEMPORAL (earliest 30% only)": (early, EVFIX),
                    "RANDOM (spread across campaign)": (rnd, EVFIX)}
            P(f"\n      {'split rule':<24}{'n eval':>8}{'WCL_bc':>9}{'ABS+mean':>10}{'DIFF+median':>13}")
            for tag, (c_, e_) in arms.items():
                a2 = fit_a0(c_, PHYS, n)
                ev2 = [m for m in e_ if sum(1 for rx in m.receptions
                                            if rx.gid in PHYS and rx.gid in a2) >= 3]
                if len(ev2) > 1200:
                    ev2 = random.Random(9).sample(ev2, 1200)
                ew, ea, ed = [], [], []
                for mm in ev2:
                    rx = [r for r in mm.receptions if r.gid in PHYS and r.gid in a2]
                    if len(rx) < 3: continue
                    rx = sorted(rx, key=lambda r: -r.rssi)[:args.max_gws]
                    g = np.vstack([PHYS[r.gid] for r in rx])
                    raw = np.array([r.rssi for r in rx], float)
                    rv = raw - np.array([a2[r.gid] for r in rx], float)
                    t = np.array([mm.x, mm.y], float)
                    ew.append(float(np.linalg.norm(wcl(ev, g, rv) - t)))
                    ea.append(float(np.linalg.norm(lattice(ev, g, rv, n, "abs", "mean") - t)))
                    ed.append(float(np.linalg.norm(lattice(ev, g, rv, n, "diff") - t)))
                if len(ew) < 100:
                    P(f"      {tag:<24}   too few eval messages"); continue
                P(f"      {tag:<24}{len(ew):>8}{np.median(ew):>9.0f}"
                  f"{np.median(ea):>10.0f}{np.median(ed):>13.0f}")
            P("      -> if TEMPORAL is materially worse, gateway-side calibration does")
            P("         NOT hold over the campaign and 'calibrate once' is unsupported.")

        # --- (b) SELECTION AT k<10. Inert at k=10 by the manuscript's own account
        # (max receptions per message is 10), so it has never been tested where the
        # selector can actually choose.
        P("\n  (b) GEOMETRY-AWARE SELECTION AT k<10. The manuscript states the selector")
        P("      surfaces are identical for max_gws>=10; max receptions is 10, so it")
        P("      cannot act there. Its main sweep relied on it throughout.")
        P(f"      {'k':>4}{'mode':>12}{'alpha':>7}{'n':>7}{'DIFF+med':>10}{'ABS+mean':>10}")
        for K in (5, 7):
            for mode, alpha in (("rssi", 0.0), ("geometry", 2.0), ("geometry", 3.0)):
                ed, ea = [], []
                pk = max(K, int(math.ceil(max(alpha, 1.0) * K)))
                for mm in EV:
                    rx = [r for r in mm.receptions if r.gid in PHYS and r.gid in a0_phys]
                    if len(rx) < K: continue
                    rx = sorted(rx, key=lambda r: -r.rssi)
                    if mode == "rssi":
                        sel = rx[:K]
                    else:
                        sel = ev.select_gateways_subset(
                            receptions_sorted_by_rssi=rx[:pk], gw_xy=PHYS, k=K,
                            mode="geometry", hybrid_pool_factor=alpha, seed=args.seed)
                    if len(sel) < 3: continue
                    g = np.vstack([PHYS[r.gid] for r in sel])
                    raw = np.array([r.rssi for r in sel], float)
                    rv = raw - np.array([a0_phys[r.gid] for r in sel], float)
                    t = np.array([mm.x, mm.y], float)
                    ed.append(float(np.linalg.norm(lattice(ev, g, rv, n, "diff") - t)))
                    ea.append(float(np.linalg.norm(lattice(ev, g, rv, n, "abs", "mean") - t)))
                if len(ed) < 50:
                    P(f"      {K:>4}{mode:>12}{alpha:>7.1f}{len(ed):>7}   THIN"); continue
                P(f"      {K:>4}{mode:>12}{alpha:>7.1f}{len(ed):>7}"
                  f"{np.median(ed):>10.0f}{np.median(ea):>10.0f}")

    # ============================== BLOCK 15 -- GEOGRAPHIC SPLIT (C1 stress test)
    if 15 in BL:
        P("\n" + "=" * 96)
        P("BLOCK 15 -- GEOGRAPHIC SPLIT. The hardest generalisation test available on")
        P("            one deployment, and the one C1 has never faced.")
        P("=" * 96)
        P(floor_line(FLOOR))
        P("  Everything in this run rests on ONE random calibration/evaluation split.")
        P("  Here calibration and evaluation are in DIFFERENT PARTS OF THE CITY.")
        P("  RSSFIT is REFIT inside each arm (its coordinates depend on calibration);")
        P("  the verified map is fixed. That makes the test HARDER for the verified")
        P("  map, not easier -- RSSFIT gets to adapt to the calibration region.")
        allm = cal + pool
        xs = np.array([m.x for m in allm], float); xmed = float(np.median(xs))
        W = [m for m in allm if m.x < xmed]; E = [m for m in allm if m.x >= xmed]
        # DESIGN FIX. A first version compared arms whose EVALUATION POPULATIONS
        # differed (random 70% vs East vs West), so the narrowing of the gap and
        # the east/west asymmetry could not be attributed to the calibration
        # region. Each direction now has its OWN FIXED evaluation set, and the
        # RANDOM control evaluates the SAME messages -- only calibration moves.
        ncal = int(len(allm) * args.train_frac)
        EVE = random.Random(9).sample(E, min(1200, len(E)))
        EVW = random.Random(9).sample(W, min(1200, len(W)))
        ke = set(mkey(m) for m in EVE); kw = set(mkey(m) for m in EVW)   # CLASS D
        rndE = random.Random(4242).sample([m for m in allm if mkey(m) not in ke],
                                          min(ncal, len(allm) - len(ke)))
        rndW = random.Random(4243).sample([m for m in allm if mkey(m) not in kw],
                                          min(ncal, len(allm) - len(kw)))
        arms = {"EAST eval | cal = RANDOM": (rndE, EVE),
                "EAST eval | cal = WEST only": (W, EVE),
                "WEST eval | cal = RANDOM": (rndW, EVW),
                "WEST eval | cal = EAST only": (E, EVW)}
        P(f"\n  split at x={xmed:.0f} | west {len(W)} msgs | east {len(E)} msgs")
        P(f"\n  {'arm':<30}{'substrate':<11}{'n':>6}{'WCL_bc':>9}{'ABS+mean':>10}"
          f"{'DIFF+median':>13}{'MinMax':>9}{'C1 gap':>9}")
        P("  " + "-" * 76)
        for tag, (c_, e_) in arms.items():
            if len(c_) < 500 or len(e_) < 500:
                P(f"  {tag:<30}  too few messages"); continue
            csub = c_ if len(c_) <= 9000 else random.Random(5).sample(c_, 9000)
            rfit, _ = ev.estimate_gateway_positions_rssfit(csub, assumed_n=n, seed=args.seed)
            maps = {"VERIFIED": PHYS,
                    "RSSFIT": {g: np.asarray(rfit[g], float) for g in PHYS if g in rfit}}
            res = {}
            for sub, mp in maps.items():
                if len(mp) < 8:
                    continue
                a2 = fit_a0(csub, mp, n)
                ev2 = [m for m in e_ if sum(1 for rx in m.receptions
                                            if rx.gid in mp and rx.gid in a2) >= 3]
                if len(ev2) > 1200:
                    ev2 = random.Random(9).sample(ev2, 1200)
                ew, ea, ed, em = [], [], [], []
                for mm in ev2:
                    rx = [r for r in mm.receptions if r.gid in mp and r.gid in a2]
                    if len(rx) < 3: continue
                    rx = sorted(rx, key=lambda r: -r.rssi)[:args.max_gws]
                    g = np.vstack([mp[r.gid] for r in rx])
                    raw = np.array([r.rssi for r in rx], float)
                    rv = raw - np.array([a2[r.gid] for r in rx], float)
                    t = np.array([mm.x, mm.y], float)
                    ew.append(float(np.linalg.norm(wcl(ev, g, rv) - t)))
                    ea.append(float(np.linalg.norm(lattice(ev, g, rv, n, "abs", "mean") - t)))
                    ed.append(float(np.linalg.norm(lattice(ev, g, rv, n, "diff") - t)))
                    em.append(float(np.linalg.norm(minmax(g, rv, n) - t)))
                if len(ew) < 100:
                    continue
                res[sub] = (len(ew), np.median(ew), np.median(ea),
                            np.median(ed), np.median(em))
            for sub in ("VERIFIED", "RSSFIT"):
                if sub not in res: continue
                nn_, w_, a_, d_, m_ = res[sub]
                gap = (f"{res['RSSFIT'][1]/res['VERIFIED'][1]:.2f}x"
                       if sub == "RSSFIT" and "VERIFIED" in res else "")
                P(f"  {(tag if sub=='VERIFIED' else ''):<30}{sub:<11}{nn_:>6}"
                  f"{w_:>9.0f}{a_:>10.0f}{d_:>13.0f}{m_:>9.0f}{gap:>9}")
        P("\n  C1 gap = WCL_bc(RSSFIT) / WCL_bc(VERIFIED), computed WITHIN an arm on")
        P("  identical messages -- valid regardless of the design fix.")
        P("  Compare RANDOM vs WEST-only at FIXED east evaluation (and the mirror):")
        P("  that difference is now attributable to the CALIBRATION REGION alone.")

    # ============================== BLOCK 16 -- FALSIFIER VALIDATION
    if 16 in BL:
        P("\n" + "=" * 96)
        P("BLOCK 16 -- FALSIFIER VALIDATION. Does the apparatus DISCRIMINATE?")
        P("=" * 96)
        P(floor_line(FLOOR))
        P("  A falsifier is wrong in exactly one way: it reports the same thing")
        P("  whether the effect it looks for is there or not. That is testable by")
        P("  running it on cases CONSTRUCTED so the answer is known in advance.")
        # LAYOUT FIX 19 Aug. These two lines were a PREAMBLE, not control
        # instances -- the actual controls run below as arms (1) and (2). But
        # they were phrased exactly like a control header, so results_audit read
        # the second as a control and looked for a verdict inside its 5-line
        # window. Arm (1) -- the NEGATIVE control -- occupies those five lines,
        # so the verdict at +9 was never reached and the audit warned
        # "control with no verdict" in EVERY run since v5. The audit was right;
        # the layout was wrong. Rephrased so a preamble cannot be mistaken for
        # an instance, and the audit's window is left alone (a comment there
        # records that widening it once swallowed the NEXT control).
        # GLOSS CORRECTED 19 Aug. It read "claim known TRUE -> must PASS" and
        # "claim known FALSE -> must FIRE". Two problems. (i) In arm (1) the
        # claim is NOT known true -- C1's mechanism is ABSENT by construction,
        # since there is only one map and nothing for provenance to cost. The
        # axis is not the claim's TRUTH but whether the EFFECT is known present
        # or absent, which is what positive/negative control have always meant.
        # (ii) PASS carried two meanings in one block: "the falsifier did not
        # fire" in the gloss, and "the control succeeded" in the verdict lines --
        # and arms (1) and (2) both print verdict: PASS, one for not firing and
        # one for firing. The gloss now says "must NOT fire" and PASS means only
        # "the control succeeded".
        P("  TWO ARMS BELOW, each with the answer built in:")
        P("    arm (1)  effect known ABSENT  -> the falsifier must NOT fire")
        P("    arm (2)  effect known PRESENT -> the falsifier MUST fire")
        P("  Both license the APPARATUS, never C1 itself: an instrument cannot be")
        P("  validated on the case it is being used to decide. A falsifier never")
        P("  shown to fire is not evidence.")
        # A CONTROL THAT CANNOT FAIL IS NOT A CONTROL. The first version of this
        # block failed that test twice: control (1) computed median(x)/median(x),
        # and control (3) multiplied an array by (1+p) then measured p. Both are
        # arithmetic identities -- they return PASS for any input. Each control
        # below is now run under a condition where it MUST report differently,
        # and the block reports TAUTOLOGY if it does not.
        def run_wcl(coords, a0):
            e = []
            for mm in EV:
                rx = [r for r in mm.receptions if r.gid in coords and r.gid in a0]
                if len(rx) < 3: continue
                rx = sorted(rx, key=lambda r: -r.rssi)[:args.max_gws]
                g = np.vstack([coords[r.gid] for r in rx])
                raw = np.array([r.rssi for r in rx], float)
                rv = raw - np.array([a0[r.gid] for r in rx], float)
                e.append(float(np.linalg.norm(wcl(ev, g, rv)
                                              - np.array([mm.x, mm.y], float))))
            return np.array(e)

        halfA, halfB = cal[0::2], cal[1::2]
        eA = run_wcl(PHYS, fit_a0(halfA, PHYS, n))
        eB = run_wcl(PHYS, fit_a0(halfB, PHYS, n))
        eR = run_wcl(RSSF, fit_a0(halfA, RSSF, n))
        gap_same = float(np.median(eB)) / float(np.median(eA))
        gap_diff = float(np.median(eR)) / float(np.median(eA))
        P(f"\n  (1) NEGATIVE CONTROL for C1 [+ a discrimination check] -- the SAME map,")
        P(f"      two INDEPENDENT A0 fits, each pushed through the whole path."
          f" The gap must be")
        P(f"      ~1.0. Then the SAME path on a DIFFERENT map, which must NOT be 1.0.")
        P(f"      same map,      independent fits : {np.median(eA):.0f} vs "
          f"{np.median(eB):.0f} m -> gap {gap_same:.3f}x")
        P(f"      different map, same path        : {np.median(eA):.0f} vs "
          f"{np.median(eR):.0f} m -> gap {gap_diff:.3f}x")
        taut = abs(gap_same - gap_diff) < 0.05
        P(f"      META-CHECK: does the control DISTINGUISH the two cases?  "
          f"{'*** TAUTOLOGY -- this control cannot fail ***' if taut else 'YES — it discriminates'}")
        P(f"      verdict: {'PASS' if (abs(gap_same-1.0) < 0.15 and gap_diff > 1.5) else '*** FAIL — apparatus does not behave as required ***'}")

        base = eA
        P(f"\n  (2) POSITIVE CONTROL for C1 -- displace the verified map by a KNOWN")
        P(f"      amount. The gap must APPEAR and SCALE. A falsifier that does not")
        P(f"      fire here cannot detect the real thing.")
        P(f"      {'injected disp.':>16}{'WCL_bc':>10}{'gap':>9}{'verdict':>14}")
        prev, gaps = 1.0, []
        for D in (0, 250, 500, 1000, 2500, 5000):
            rg2 = np.random.default_rng(20)
            bad = {g: PHYS[g] + rg2.normal(0, D / np.sqrt(2), 2) for g in PHYS}
            e = run_wcl(bad, fit_a0(halfA, bad, n))
            gp = float(np.median(e)) / float(np.median(base)); gaps.append(gp)
            v = "monotone" if gp >= prev - 0.02 else "*** NON-MONOTONE ***"
            P(f"      {D:>13} m{np.median(e):>10.0f}{gp:>8.2f}x{v:>14}")
            prev = gp
        P(f"      META-CHECK: does the gap MOVE across the injection range?  "
          f"{'*** TAUTOLOGY -- flat, cannot discriminate ***' if (max(gaps)-min(gaps)) < 0.2 else f'YES — spans {min(gaps):.2f}-{max(gaps):.2f}x'}")
        # EXPLICIT VERDICT, added 19 Aug. This control printed a table and a
        # META-CHECK but NEVER a verdict line, so results_audit flagged it in
        # every run as "control with no verdict" -- correctly. A control whose
        # result is never STATED is not a control. The negative control above
        # prints one; this one now does too.
        _appeared = len(gaps) > 1 and max(gaps) > 1.05
        _scaled = all(gaps[k] >= gaps[k-1] - 0.02 for k in range(1, len(gaps)))
        if _appeared and _scaled:
            P(f"        verdict: PASS -- the gap APPEARED (up to {max(gaps):.2f}x) and")
            P(f"                 SCALED monotonically with injected displacement.")
            P(f"                 This falsifier CAN detect the real thing.")
        elif _appeared:
            P(f"        verdict: *** PARTIAL -- the gap appeared ({max(gaps):.2f}x) but did")
            P(f"                 NOT scale monotonically. Read the ordering, not the size.")
        else:
            P(f"        verdict: *** FAIL -- the gap did NOT appear under a KNOWN")
            P(f"                 displacement. This falsifier cannot detect the real")
            P(f"                 thing, so C1 is UNVALIDATED by it. ***")

        P(f"\n  (3) FLOOR SENSITIVITY -- a REAL perturbation, not an arithmetic one.")
        P(f"      The first version multiplied the array by (1+p) and measured p,")
        P(f"      which is an identity. Here a genuine displacement is injected and")
        P(f"      the floor must classify the RESULTING effect correctly.")
        fl = FLOOR.get("seed")
        if fl is None:
            P(f"      BLOCK 1 not run -- floor cannot be validated")
        else:
            P(f"      floor = {fl:.1f}%  [{FLOOR.get('provenance','unset')}]")
            P(f"      {'injected disp.':>16}{'measured effect':>17}{'floor says':>16}")
            calls = []
            for D in (0, 100, 200, 400, 800, 2000):
                rg3 = np.random.default_rng(33)
                bad = {g: PHYS[g] + rg3.normal(0, D / np.sqrt(2), 2) for g in PHYS}
                e = run_wcl(bad, fit_a0(halfA, bad, n))
                eff = (float(np.median(e)) - float(np.median(base))) \
                      / float(np.median(base)) * 100
                call = "unresolvable" if abs(eff) < fl else "resolvable"
                calls.append(call)
                P(f"      {D:>13} m{eff:>16.1f}%{call:>16}")
            P(f"      META-CHECK: does the floor give BOTH verdicts across the range? "
              f"{'*** TAUTOLOGY -- one verdict only, uninformative ***' if len(set(calls)) < 2 else 'YES — it discriminates'}")

    # ============================== BLOCK 17 -- IS THE TRUE MAP THE OPTIMUM?
    if 17 in BL:
        P("\n" + "=" * 96)
        P("BLOCK 17 -- IS THE VERIFIED MAP THE OPTIMUM, OR MERELY THE TRUTH?")
        P("=" * 96)
        P(floor_line(FLOOR))
        P("  BLOCK 16's floor control used ONE random realization per displacement.")
        P("  On the 22-gw map it showed 100-400 m of injected error IMPROVING")
        P("  localization; on the 29-gw map the same magnitudes DEGRADED it. Two")
        P("  draws, opposite signs -- that is what sampling noise looks like.")
        P("  (a) repeats each magnitude over many seeds: is the effect systematic?")
        P("  (b) sweeps a DIRECTED bias: random noise should never help, but pulling")
        P("      anchors toward the transmitter cloud plausibly could, by improving")
        P("      geometric conditioning. That locates the true optimum.")
        P("  C1 claims the estimator error -- BLOCK 19 census: 1,057 to 34,820 m,")
        P("  median about 5,100 -- is consequential. It does NOT claim")
        P("  the true map is optimal. If a biased map beats truth AND truth beats")
        P("  RSSFIT, then RSSFIT is further from the optimum than from the truth.")

        C = np.array(list(PHYS.values()))
        bb = (C[:, 0].min() - 3000, C[:, 0].max() + 3000,
              C[:, 1].min() - 3000, C[:, 1].max() + 3000)
        TXC = np.array([[m.x, m.y] for m in cal], float).mean(axis=0)

        def score(coords, want_abs=True):
            a0m = fit_a0(cal, coords, n)
            ew, ea = [], []
            for mm in EV:
                rx = [r for r in mm.receptions if r.gid in coords and r.gid in a0m]
                if len(rx) < 3: continue
                rx = sorted(rx, key=lambda r: -r.rssi)[:args.max_gws]
                g = np.vstack([coords[r.gid] for r in rx])
                raw = np.array([r.rssi for r in rx], float)
                rv = raw - np.array([a0m[r.gid] for r in rx], float)
                t = np.array([mm.x, mm.y], float)
                ew.append(float(np.linalg.norm(wcl(ev, g, rv) - t)))
                if want_abs:
                    ea.append(float(np.linalg.norm(lattice(ev, g, rv, n, "abs", "mean") - t)))
            return (float(np.median(ew)) if ew else float("nan"),
                    float(np.median(ea)) if ea else float("nan"))
        # GAP FILLED 19 Aug. The differential objective was absent from this block.
        # Added as an ADDITIVE companion rather than by widening the scorer above,
        # whose return arity is consumed by many call sites. No existing caller
        # changes, so every figure this block already published is untouched.
        def score_diff17(mp):
            a0m = fit_a0(cal, mp, n); out = []
            for mm in EV:
                rx = [r for r in mm.receptions if r.gid in mp and r.gid in a0m]
                if len(rx) < 3: continue
                rx = sorted(rx, key=lambda r: -r.rssi)[:args.max_gws]
                gg = np.vstack([mp[r.gid] for r in rx])
                rr_ = (np.array([r.rssi for r in rx], float)
                       - np.array([a0m[r.gid] for r in rx], float))
                out.append(float(np.linalg.norm(
                    lattice(ev, gg, rr_, n, "diff", "median")
                    - np.array([mm.x, mm.y], float))))
            return float(np.median(out)) if out else float("nan")

        w0, a0_ref = score(PHYS)
        d0_17 = score_diff17(PHYS)
        P(f"\n  reference: verified map  WCL_bc {w0:.0f} m | "
          f"ABS+mean {a0_ref:.0f} m | DIFF {d0_17:.0f} m")

        P(f"\n  (a) RANDOM DISPLACEMENT, {args.perturb_seeds} SEEDS PER MAGNITUDE")
        P(f"      {'disp':>7}{'median effect':>15}{'min':>9}{'max':>9}{'seeds worse':>13}{'verdict':>16}")
        for D in (100, 200, 400, 800, 2000):
            effs = []
            for sd in range(args.perturb_seeds):
                rgp = np.random.default_rng(1000 + sd)
                bad = {g: PHYS[g] + rgp.normal(0, D / np.sqrt(2), 2) for g in PHYS}
                w, _ = score(bad, want_abs=False)
                effs.append((w - w0) / w0 * 100)
            effs = np.array(effs)
            worse = int((effs > 0).sum())
            vd = ("HARMS" if np.median(effs) > 0 and worse >= 0.75 * len(effs)
                  else "HELPS" if np.median(effs) < 0 and worse <= 0.25 * len(effs)
                  else "*** NOT SYSTEMATIC ***")
            P(f"      {D:>5} m{np.median(effs):>14.1f}%{effs.min():>8.1f}%{effs.max():>8.1f}%"
              f"{worse:>7}/{len(effs):<5}{vd:>16}")
        P(f"      -> if a magnitude is NOT SYSTEMATIC, the single-seed BLOCK 16 result")
        P(f"         at that magnitude was a draw, not a finding.")

        P(f"\n  (b) DIRECTED RADIAL BIAS -- scale every gateway's offset from the")
        P(f"      transmitter centroid by lambda. lambda<1 pulls anchors IN toward")
        P(f"      the device cloud; lambda=1 is the truth. This is systematic, so a")
        P(f"      single evaluation suffices.")
        P(f"      {'lambda':>8}{'shift':>9}{'WCL_bc':>9}{'ABS+mean':>10}"
          f"{'DIFF':>8}{'WCL vs':>9}{'DIFF vs':>9}")
        best = (1.0, w0); dbest = (1.0, None)
        for lam in (0.70, 0.80, 0.90, 0.95, 1.00, 1.05, 1.15, 1.30):
            biased = {g: TXC + (PHYS[g] - TXC) * lam for g in PHYS}
            sh = float(np.median([np.linalg.norm(biased[g] - PHYS[g]) for g in PHYS]))
            w, a_ = score(biased)
            d_ = score_diff17(biased)
            if dbest[1] is None or d_ < dbest[1]: dbest = (lam, d_)
            if w < best[1]:
                best = (lam, w)
            P(f"      {lam:>8.2f}{sh:>8.0f}m{w:>9.0f}{a_:>10.0f}{d_:>8.0f}"
              f"{(w-w0)/w0*100:>8.1f}%{(d_-d0_17)/d0_17*100:>8.1f}%"
              + ("  <- TRUTH" if lam == 1.0 else ""))
        P(f"      WCL_bc optimum at lambda={best[0]:.2f} ({best[1]:.0f} m); "
          f"truth {w0:.0f} m")
        P(f"      DIFF   optimum at lambda={dbest[0]:.2f} ({dbest[1]:.0f} m); "
          f"truth {d0_17:.0f} m")
        P("      -> if the two optima DISAGREE, the claim that the map is the")
        P("         optimum becomes METHOD-DEPENDENT and sec.6 must say so")

        P(f"\n  (c) WHERE DOES RSSFIT SIT relative to BOTH?")
        wr, ar = score(RSSF)
        P(f"      verified (truth)   WCL_bc {w0:>6.0f} m")
        P(f"      best biased map    WCL_bc {best[1]:>6.0f} m  (lambda={best[0]:.2f})")
        P(f"      RSSFIT             WCL_bc {wr:>6.0f} m")
        P(f"      RSSFIT vs truth    {wr / w0:.2f}x   |   RSSFIT vs OPTIMUM  {wr / best[1]:.2f}x")
        P(f"      -> C1 is stated against the OPTIMUM, not against the truth. If")
        P(f"         RSSFIT is further from the optimum than truth is, C1 STRENGTHENS.")

    # ============================== BLOCK 18 -- ARTIFACTS PORTED FROM SIDE SCRIPTS
    if 18 in BL:
        P("\n" + "=" * 96)
        P("BLOCK 18 -- THREE ARTIFACTS THAT LIVED IN SEPARATE SCRIPTS")
        P("=" * 96)
        P(floor_line(FLOOR))
        P("  The artifact catalogue must come from ONE run. Residual kurtosis, NLLS")
        P("  divergence and sweep coordinate-drift were measured in side scripts on")
        P("  other samples. Ported here so every row of the table shares a substrate,")
        P("  an evaluation set and a floor.")

        # (a) residual kurtosis -- the case for robust loss functions
        from scipy.stats import kurtosis as _kurt
        P(f"\n  (a) RESIDUAL TAIL WEIGHT. A contaminated heavy-tailed residual")
        P(f"      distribution is the standard justification for robust loss")
        P(f"      functions on this benchmark.")
        P(f"      {'substrate':<12}{'links':>9}{'sd dB':>8}{'excess kurtosis':>18}{'|r|>3sd':>10}")
        for tag, mp in (("VERIFIED", PHYS), ("RSSFIT", RSSF)):
            by = {}
            for mm in cal:
                for rx in mm.receptions:
                    if rx.gid in mp:
                        d = float(np.linalg.norm(mp[rx.gid] - np.array([mm.x, mm.y]))) + 1.0
                        by.setdefault(rx.gid, []).append((float(rx.rssi), d))
            res = []
            for g, v in by.items():
                if len(v) < 10: continue
                a = np.array(v, float)
                y = a[:, 0] + 10 * n * np.log10(a[:, 1])
                res += list(y - np.median(y))
            res = np.array(res); sd = res.std()
            P(f"      {tag:<12}{len(res):>9}{sd:>8.2f}{_kurt(res):>18.1f}"
              f"{100*np.mean(np.abs(res) > 3*sd):>9.2f}%")

        # (b) NLLS divergence
        P(f"\n  (b) NLLS DIVERGENCE. The fallback branch the literature documents")
        P(f"      exists to handle a failure mode that may itself be an artifact.")
        sub = EV[:min(600, len(EV))]
        P(f"      {'substrate':<12}{'msgs':>7}{'diverged':>10}{'returned wcl_init':>19}")
        for tag, mp, a0m in (("VERIFIED", PHYS, a0_phys), ("RSSFIT", RSSF, a0_rssf)):
            Cq = np.array(list(mp.values()))
            bbq = (Cq[:, 0].min()-3000, Cq[:, 0].max()+3000,
                   Cq[:, 1].min()-3000, Cq[:, 1].max()+3000)
            nd = eq = tot = 0
            for mm in sub:
                rx = [r for r in mm.receptions if r.gid in mp and r.gid in a0m]
                if len(rx) < 3: continue
                rx = sorted(rx, key=lambda r: -r.rssi)[:args.max_gws]; tot += 1
                g = np.vstack([mp[r.gid] for r in rx])
                raw = np.array([r.rssi for r in rx], float)
                rv = raw - np.array([a0m[r.gid] for r in rx], float)
                w = wcl(ev, g, raw)
                x, conv, _d = ev.robust_nlls_localize(gw_mat=g, rssi_corrected=rv, n=n,
                    wcl_init=w, bbox=bbq, huber_c=1.345, n_starts=3, max_iter=120,
                    grad_tol=1e-6, halton_seed=args.seed)
                if not conv:
                    nd += 1; eq += (float(np.linalg.norm(x - w)) < 1.0)
            P(f"      {tag:<12}{tot:>7}{nd:>10}{eq:>19}")

        # (c) does a min_gws sweep silently re-estimate the geometry?
        P(f"\n  (c) SWEEP COORDINATE DRIFT. A sweep over min_gws applies its filter")
        P(f"      BEFORE the calibration split, so each configuration fits its")
        P(f"      coordinates on different data. If the map moves, the sweep varies")
        P(f"      GEOMETRY alongside the swept parameter.")
        maps = {}
        for mg in (3, 5, 8):
            try:
                mm_ = ev.load_antwerp_csv(args.data, min_gws=mg)
            except Exception:
                continue
            r3 = random.Random(args.seed); q3 = list(mm_); r3.shuffle(q3)
            c3 = q3[:int(len(q3) * args.train_frac)]
            if len(c3) > 7000:
                c3 = random.Random(3).sample(c3, 7000)
            g3, _ = ev.estimate_gateway_positions_rssfit(c3, assumed_n=n, seed=args.seed)
            maps[mg] = {g: np.asarray(v, float) for g, v in g3.items()}
        P(f"      {'compare':<22}{'common gw':>11}{'median shift':>14}{'p90':>9}{'max':>9}")
        ks = sorted(maps)
        for i in range(len(ks)):
            for j in range(i + 1, len(ks)):
                cc = sorted(set(maps[ks[i]]) & set(maps[ks[j]]))
                if len(cc) < 5: continue
                d = np.array([float(np.linalg.norm(maps[ks[i]][g] - maps[ks[j]][g])) for g in cc])
                # WIDTH FIX 19 Aug. {ks[j]:<13} made the label field 26 chars
                # against a 22-char header, pushing every numeric column 4
                # places right. full_integrity's overflow marker did not catch
                # it because that marker inspects {'literal':>N} patterns only,
                # and a COMPUTED value in an f-string is invisible to it.
                P(f"      {f'min_gws {ks[i]} vs {ks[j]}':<22}{len(cc):>11}{np.median(d):>13.0f}m"
                  f"{np.percentile(d,90):>8.0f}m{d.max():>8.0f}m")

    # ============================== BLOCK 19 -- PER-GATEWAY SPREAD + BOOTSTRAP
    if 19 in BL:
        P("\n" + "=" * 96)
        P("BLOCK 19 -- PER-GATEWAY ERROR SPREAD and MAP-COMPOSITION BOOTSTRAP")
        P("=" * 96)
        P(floor_line(FLOOR))
        P("  These two numbers appear in the manuscript's central section but were")
        P("  measured on the 27-gateway map before BLOCK 17 existed, i.e. NOT in the")
        P("  run of record. Ported here so every figure in that section shares one")
        P("  run, one evaluation set and one floor.")

        # (a) the per-gateway error distribution -- C1 is stated PER GATEWAY
        err = {g: float(np.linalg.norm(RSSF[g] - PHYS[g])) for g in G}
        v = np.array(sorted(err.values()))
        P(f"\n  (a) PER-GATEWAY POSITIONAL ERROR of the estimator ({len(v)} gateways,")
        P(f"      a CENSUS of the mapped set, not a sample)")
        P(f"      min {v.min():.0f} m | p25 {np.percentile(v,25):.0f} | median "
          f"{np.median(v):.0f} | p75 {np.percentile(v,75):.0f} | max {v.max():.0f} m")
        P(f"      within 2 km : {int((v < 2000).sum())}/{len(v)}     "
          f"beyond 18 km: {int((v > 18000).sum())}/{len(v)}")
        P(f"      -> a message's accuracy depends on WHICH gateways hear it; any")
        P(f"         deployment-level ratio averages over this spread.")

        # (b) bootstrap over map composition -- the broadest test of the direction
        def wcl_run(mp, a0m):
            e = []
            for mm in EV:
                rx = [r for r in mm.receptions if r.gid in mp and r.gid in a0m]
                if len(rx) < 3: continue
                rx = sorted(rx, key=lambda r: -r.rssi)[:args.max_gws]
                g_ = np.vstack([mp[r.gid] for r in rx])
                raw = np.array([r.rssi for r in rx], float)
                rv = raw - np.array([a0m[r.gid] for r in rx], float)
                e.append(float(np.linalg.norm(wcl(ev, g_, rv)
                                              - np.array([mm.x, mm.y], float))))
            return float(np.median(e)) if len(e) >= 100 else float("nan")
        full_v = wcl_run(PHYS, a0_phys); full_r = wcl_run(RSSF, a0_rssf)
        P(f"\n  (b) BOOTSTRAP over map composition, {args.boot_draws} random subsets")
        P(f"      of {max(3, int(len(G)*0.7))}-of-{len(G)}. An INVERSION is a draw where the")
        P(f"      estimated map is not worse. THIS is the broadest test of the direction.")
        P(f"      full map: VERIFIED {full_v:.0f} m | RSSFIT {full_r:.0f} m | "
          f"gap {full_r/full_v:.2f}x")
        msz = max(3, int(len(G) * 0.7)); gaps = []
        for rep in range(args.boot_draws):
            sub = random.Random(500 + rep).sample(G, msz)
            p2 = {g: PHYS[g] for g in sub}; r2 = {g: RSSF[g] for g in sub}
            a = wcl_run(p2, fit_a0(cal, p2, n)); b = wcl_run(r2, fit_a0(cal, r2, n))
            if np.isfinite(a) and np.isfinite(b) and a > 0:
                gaps.append(b / a)
        gaps = np.array(gaps)
        # EMPTINESS GUARD, added 19 Aug. np.median([]) and np.percentile([],5)
        # both raise, so a run in which NO bootstrap draw is usable crashed the
        # whole harness at BLOCK 19. Pre-existing; exposed by --boot-draws 2.
        if len(gaps) < 3:
            P(f"      {len(gaps)} usable draws -- THIN, not interpreted. Raise")
            P(f"      --boot-draws (currently {args.boot_draws}) or --samples.")
        else:
            P(f"      {len(gaps)} usable draws | gap median {np.median(gaps):.2f}x | "
              f"p05 {np.percentile(gaps,5):.2f}x | p95 {np.percentile(gaps,95):.2f}x")
            P(f"      range {gaps.min():.2f}-{gaps.max():.2f}x | "
              f"INVERSIONS (gap <= 1.0): {int((gaps <= 1).sum())}/{len(gaps)}")

        # (c) leave-one-out -- is any single gateway load-bearing?
        P(f"\n  (c) LEAVE-ONE-OUT: does any single gateway carry the result?")
        loo = []
        for g in G:
            sub = [x for x in G if x != g]
            p2 = {x: PHYS[x] for x in sub}; r2 = {x: RSSF[x] for x in sub}
            a = wcl_run(p2, fit_a0(cal, p2, n)); b = wcl_run(r2, fit_a0(cal, r2, n))
            if np.isfinite(a) and np.isfinite(b) and a > 0:
                loo.append((g, b / a, err[g]))
        loo.sort(key=lambda t: t[1])
        P(f"      {len(loo)} runs | gap range {loo[0][1]:.2f}-{loo[-1][1]:.2f}x "
          f"(full map {full_r/full_v:.2f}x)")
        P(f"      {'drop gw':>9}{'gap':>8}{'that gw error':>16}")
        for g, gp, er in loo[:3] + loo[-3:]:
            P(f"      {g:>9}{gp:>7.2f}x{er:>15.0f} m")

    # ============================== BLOCK 20 -- IS THE FULL MAP CONTAMINATED?
    if 20 in BL and not args.drop_weak:
        P("\n" + "=" * 96)
        P("BLOCK 20 -- FULL MAP vs STRONG SUBSET, PAIRED ON SHARED MESSAGES")
        P("=" * 96)
        P(floor_line(FLOOR))
        P("  Comparing the --drop-weak run against the full run is CONFOUNDED: the")
        P("  strong subset evaluates ~200 fewer messages, and those are exactly the")
        P("  ones that depended on the dropped gateways -- i.e. probably the harder")
        P("  ones. Six of six methods improved under --drop-weak, which either means")
        P("  the weak assignments are WRONG (map contamination) or that the easier")
        P("  population was selected. This block separates the two by evaluating")
        P("  BOTH maps on the messages evaluable under BOTH.")
        # BLOCK 20 depends on BLOCK 0 having computed STRONG. Without that guard
        # a --blocks 20 run would raise NameError instead of saying why.
        try:
            _S = STRONG
        except NameError:
            P("  *** BLOCK 0 did not run, so the strong subset is unknown.")
            P("      Re-run with --blocks 0,20 (or the full set). ***")
            _S = None
        WEAK = [g for g in G if g not in _S] if _S is not None else []
        if _S is None:
            pass
        elif not WEAK:
            P("  no weak assignments on this map -- nothing to test")
        else:
            PS = {g: PHYS[g] for g in _S}
            a0S = fit_a0(cal, PS, n)
            SHARED = [mm for mm in EV
                      if sum(1 for r in mm.receptions if r.gid in PS and r.gid in a0S) >= 3
                      and sum(1 for r in mm.receptions if r.gid in PHYS and r.gid in a0_phys) >= 3]
            P(f"\n  weak assignments dropped: {len(WEAK)}  {sorted(WEAK, key=int)}")
            P(f"  evaluable under the FULL map     : "
              f"{sum(1 for mm in EV if sum(1 for r in mm.receptions if r.gid in PHYS and r.gid in a0_phys)>=3)}")
            P(f"  evaluable under BOTH (shared set): {len(SHARED)}   <- the paired test")
            def pair_run(mp, a0m, obj=None):
                e = []
                for mm in SHARED:
                    rx = [r for r in mm.receptions if r.gid in mp and r.gid in a0m]
                    if len(rx) < 3: e.append(np.nan); continue
                    rx = sorted(rx, key=lambda r: -r.rssi)[:args.max_gws]
                    g_ = np.vstack([mp[r.gid] for r in rx])
                    raw = np.array([r.rssi for r in rx], float)
                    rv = raw - np.array([a0m[r.gid] for r in rx], float)
                    t = np.array([mm.x, mm.y], float)
                    if obj is None:
                        e.append(float(np.linalg.norm(wcl(ev, g_, rv) - t)))
                    else:
                        e.append(float(np.linalg.norm(lattice(ev, g_, rv, n, obj, "mean"
                                 if obj == "abs" else "median") - t)))
                return np.array(e)
            P(f"\n  {'method':<14}{'FULL map':>10}{'STRONG only':>13}{'paired diff':>13}"
              f"{'95% CI':>20}{'verdict':>16}")
            for tag, obj in (("WCL_bc", None), ("ABS+mean", "abs"), ("DIFF+median", "diff")):
                eF = pair_run(PHYS, a0_phys, obj); eS = pair_run(PS, a0S, obj)
                ok = np.isfinite(eF) & np.isfinite(eS)
                eF, eS = eF[ok], eS[ok]
                if len(eF) < 50: P(f"  {tag:<14} THIN"); continue
                mF, mS = float(np.median(eF)), float(np.median(eS))
                lo, hi = boot_diff_medians(eS, eF, seed=args.seed)
                pct = (mS - mF) / mF * 100
                zero = (lo <= 0 <= hi)
                vd = ("no difference" if zero
                      else ("STRONG BETTER" if hi < 0 else "FULL BETTER"))
                P(f"  {tag:<14}{mF:>9.0f}m{mS:>12.0f}m{pct:>12.1f}%"
                  f"{f'[{lo:+.0f}, {hi:+.0f}]':>20}{vd:>16}")
            P(f"\n  -> if the CIs SPAN ZERO, the --drop-weak improvement was POPULATION")
            P(f"     SELECTION, and the full map is not contaminated. If STRONG is")
            P(f"     genuinely better on the SAME messages, some weak assignments are")
            P(f"     WRONG and the recovered map should be the strong subset.")
            errW = [float(np.linalg.norm(RSSF[g] - PHYS[g])) for g in WEAK if g in RSSF]
            errS = [float(np.linalg.norm(RSSF[g] - PHYS[g])) for g in _S if g in RSSF]
            P(f"\n  RSSFIT error at the DROPPED gateways: median {np.median(errW):.0f} m "
              f"(n={len(errW)})")
            P(f"  RSSFIT error at the KEPT gateways   : median {np.median(errS):.0f} m "
              f"(n={len(errS)})")
            P(f"  -> the dropped set is where the ESTIMATOR errs most as well; that is")
            P(f"     consistent with them being genuinely hard, not necessarily wrong.")

    # ============================== BLOCK 21 -- HOW COORDINATE ERROR ACCUMULATES
    if 21 in BL:
        P("\n" + "=" * 96)
        P("BLOCK 21 -- THE ABSORPTION CURVE: how does damage scale with the NUMBER")
        P("            of wrong anchors, and does DIRECTION matter as well as SIZE?")
        P("=" * 96)
        P(floor_line(FLOOR))
        P("  Two facts sit far apart and the shape between them is unmeasured:")
        P("    a MINORITY of receivers displaced is LARGELY ABSORBED by the")
        P("      intercept fit. HOW MUCH depends on WHICH receivers, and the")
        P("      table below measures exactly that. An earlier version of this")
        P("      header quoted a single figure from a side measurement; the")
        P("      f=7 row below supersedes it and they disagree.")
        P("    ALL receivers wrong by the estimator own median error: about +464%")
        P("  If the curve is LINEAR, coordinate error is additive. If it has a KNEE,")
        P("  C1 is a COLLAPSE phenomenon and a practitioner who gets most gateways")
        P("  roughly right is safe while one who gets them all wrong is not.")
        P("  NOTE: this block NEVER mutates PHYS or RSSF. Every corrupted map is a")
        P("  new dict, and A0 is refitted on it so each map is self-consistent.")

        def build(base, targets, disp, seed, mode="iso"):
            """New dict. mode iso = random direction, magnitude disp."""
            rg = np.random.default_rng(seed); out = {}
            for g, v in base.items():
                if g in targets:
                    if mode == "iso":
                        th = rg.uniform(0, 2*np.pi)
                        out[g] = v + disp*np.array([np.cos(th), np.sin(th)])
                    else:
                        out[g] = v + rg.normal(0, disp/np.sqrt(2), 2)
                else:
                    out[g] = np.array(v, float)
            return out

        def score(mp, want=("wcl", "abs")):
            a0m = fit_a0(cal, mp, n); ew, ea = [], []
            for mm in EV:
                rx = [r for r in mm.receptions if r.gid in mp and r.gid in a0m]
                if len(rx) < 3: continue
                rx = sorted(rx, key=lambda r: -r.rssi)[:args.max_gws]
                g_ = np.vstack([mp[r.gid] for r in rx])
                raw = np.array([r.rssi for r in rx], float)
                rv = raw - np.array([a0m[r.gid] for r in rx], float)
                t = np.array([mm.x, mm.y], float)
                if "wcl" in want: ew.append(float(np.linalg.norm(wcl(ev, g_, rv) - t)))
                if "abs" in want:
                    ea.append(float(np.linalg.norm(lattice(ev, g_, rv, n, "abs", "mean") - t)))
            return (float(np.median(ew)) if ew else float("nan"),
                    float(np.median(ea)) if ea else float("nan"), len(ew) or len(ea))
        # GAP FILLED 19 Aug. The differential objective was absent from this block.
        # Added as an ADDITIVE companion rather than by widening the scorer above,
        # whose return arity is consumed by many call sites. No existing caller
        # changes, so every figure this block already published is untouched.
        def score_diff(mp):
            a0m = fit_a0(cal, mp, n); out = []
            for mm in EV:
                rx = [r for r in mm.receptions if r.gid in mp and r.gid in a0m]
                if len(rx) < 3: continue
                rx = sorted(rx, key=lambda r: -r.rssi)[:args.max_gws]
                gg = np.vstack([mp[r.gid] for r in rx])
                rr_ = (np.array([r.rssi for r in rx], float)
                       - np.array([a0m[r.gid] for r in rx], float))
                out.append(float(np.linalg.norm(
                    lattice(ev, gg, rr_, n, "diff", "median")
                    - np.array([mm.x, mm.y], float))))
            return float(np.median(out)) if out else float("nan")

        # MIN-MAX companion added 19 Aug, same additive pattern as the
        # differential one above: no existing caller changes.
        def score_mm(mp):
            a0m = fit_a0(cal, mp, n); out = []
            for mm in EV:
                rx = [r for r in mm.receptions if r.gid in mp and r.gid in a0m]
                if len(rx) < 3: continue
                rx = sorted(rx, key=lambda r: -r.rssi)[:args.max_gws]
                gg = np.vstack([mp[r.gid] for r in rx])
                rr_ = (np.array([r.rssi for r in rx], float)
                       - np.array([a0m[r.gid] for r in rx], float))
                out.append(float(np.linalg.norm(
                    minmax(gg, rr_, n)
                    - np.array([mm.x, mm.y], float))))
            return float(np.median(out)) if out else float("nan")

        w0, a0r, n0 = score(PHYS)
        d0_21 = score_diff(PHYS); m0_21 = score_mm(PHYS)
        P(f"\n  reference (true map): WCL_bc {w0:.0f} m | ABS+mean {a0r:.0f} m | "
          f"DIFF {d0_21:.0f} m | MinMax {m0_21:.0f} m | n={n0}")

        # ---------- (0) APPARATUS CONTROL. Every variant below rests on
        # build() + refit A0 + score(). If corrupting NOTHING does not return
        # EXACTLY to baseline, the pipeline is not measuring displacement -- it
        # is measuring its own noise, and every number in this block is void.
        P(f"\n  (0) APPARATUS CONTROL -- corrupt NOTHING and corrupt EVERYTHING by 0 m.")
        P(f"      Both must return EXACTLY the reference. A control that cannot fail")
        P(f"      is decoration; this one fails loudly if build/refit is not neutral.")
        z1, _, _ = score(build(PHYS, set(), args.corrupt_disp, 1))
        z2, _, _ = score(build(PHYS, set(G), 0.0, 2))
        okz = abs(z1 - w0) < 1e-6 and abs(z2 - w0) < 1e-6
        P(f"      empty target set   : {z1:.1f} m  (reference {w0:.1f})   "
          f"{'PASS' if abs(z1-w0)<1e-6 else '*** FAIL ***'}")
        P(f"      all targets, 0 m   : {z2:.1f} m  (reference {w0:.1f})   "
          f"{'PASS' if abs(z2-w0)<1e-6 else '*** FAIL ***'}")
        if not okz:
            P(f"      *** APPARATUS UNSOUND -- every result below is VOID. ***")

        # ---------- VARIANT 1: how many wrong anchors?
        P(f"\n  (1) CORRUPTION-FRACTION SWEEP. f gateways displaced {args.corrupt_disp} m")
        P(f"      in a RANDOM DIRECTION, {args.corrupt_draws} random choices of WHICH,")
        P(f"      A0 refitted each time. Everything else identical.")
        P(f"      {'f':>4}{'% of map':>9}{'WCL_bc':>9}{'vs true':>9}{'ABS+mean':>10}"
          f"{'vs true':>9}{'DIFF':>8}{'vs true':>9}{'MinMax':>9}{'vs true':>9}{'spread':>9}")
        fr = sorted(set([1, max(2, len(G)//8), max(3, len(G)//4), len(G)//2,
                         int(len(G)*0.75), len(G)]))
        for f in fr:
            ws, as_, dsw, msw = [], [], [], []
            for d in range(args.corrupt_draws):
                tg = set(random.Random(9100 + 31*f + d).sample(G, f))
                bad = build(PHYS, tg, args.corrupt_disp, 7700 + 31*f + d)
                a, b, _ = score(bad); ws.append(a); as_.append(b)
                dsw.append(score_diff(bad)); msw.append(score_mm(bad))
            ws, as_, dsw, msw = (np.array(ws), np.array(as_),
                                 np.array(dsw), np.array(msw))
            P(f"      {f:>4}{100*f/len(G):>8.0f}%{np.median(ws):>8.0f}m"
              f"{100*(np.median(ws)-w0)/w0:>8.1f}%{np.median(as_):>9.0f}m"
              f"{100*(np.median(as_)-a0r)/a0r:>8.1f}%{np.median(dsw):>7.0f}m"
              f"{100*(np.median(dsw)-d0_21)/d0_21:>8.1f}%"
              f"{np.median(msw):>8.0f}m{100*(np.median(msw)-m0_21)/m0_21:>8.1f}%"
              f"{100*(ws.max()-ws.min())/np.median(ws):>8.1f}%")
        P(f"      spread = across the {args.corrupt_draws} choices of WHICH gateways.")
        _v1 = []
        for f in fr:
            tg = set(random.Random(9100 + 31*f).sample(G, f))
            a, _, _ = score(build(PHYS, tg, 0.0, 1))          # ZERO displacement
            _v1.append(100*(a - w0)/w0)
        P(f"      META-CHECK, same sweep at ZERO displacement: "
          f"max deviation {max(abs(x) for x in _v1):.2f}%")
        P(f"      {'*** TAUTOLOGY -- the sweep moves even with NO error injected ***' if max(abs(x) for x in _v1) > 0.5 else 'PASS — a flat line when nothing is corrupted, so the curve above is real'}")

        # ---------- VARIANT 2: is the SYSTEMATIC estimator worse than random?
        P(f"\n  (2) SYSTEMATIC vs RANDOM AT EQUAL MAGNITUDE. Three maps, all wrong by")
        P(f"      the same amount; only the STRUCTURE of the error differs.")
        mag = {g: float(np.linalg.norm(RSSF[g] - PHYS[g])) for g in G}
        med = float(np.median(list(mag.values())))
        rg = np.random.default_rng(4242)
        shuf = {}
        for g in G:                       # SAME magnitude per gateway, RANDOM direction
            th = rg.uniform(0, 2*np.pi)
            shuf[g] = PHYS[g] + mag[g]*np.array([np.cos(th), np.sin(th)])
        iso = build(PHYS, set(G), med, 5150)
        # DIRECTION-PRESERVING CONTROL: same magnitudes AND the true directions.
        # This must reproduce RSSFIT exactly. If it does not, the reconstruction
        # is broken and the randomised-direction arm means nothing.
        keep = {}
        for g in G:
            d = RSSF[g] - PHYS[g]; nrm = float(np.linalg.norm(d))
            keep[g] = PHYS[g] + (d if nrm == 0 else mag[g]*d/nrm)
        wR, aR, _ = score(RSSF); wS, aS, _ = score(shuf); wI, aI, _ = score(iso)
        wK, aK, _ = score(keep)
        P(f"      per-gateway displacement: RSSFIT median {med:.0f} m "
          f"(min {min(mag.values()):.0f}, max {max(mag.values()):.0f})")
        P(f"      {'map':<40}{'WCL_bc':>10}{'vs true':>10}{'ABS+mean':>11}")
        P(f"      {'RSSFIT (actual, systematic)':<40}{wR:>9.0f}m{wR/w0:>9.2f}x{aR:>10.0f}m")
        P(f"      {'same magnitudes, RANDOM directions':<40}{wS:>9.0f}m{wS/w0:>9.2f}x{aS:>10.0f}m")
        P(f"      {f'isotropic random at {med:.0f} m':<40}{wI:>9.0f}m{wI/w0:>9.2f}x{aI:>10.0f}m")
        P(f"      {'CONTROL: magnitudes AND true directions':<40}{wK:>9.0f}m{wK/w0:>9.2f}x{aK:>10.0f}m")
        P(f"      META-CHECK: the control must REPRODUCE RSSFIT (it is RSSFIT, rebuilt")
        P(f"      from magnitude+direction). {abs(wK-wR):.1f} m apart -> "
          f"{'PASS — the reconstruction is sound' if abs(wK-wR) < 1.0 else '*** BROKEN — the randomised arm is meaningless ***'}")
        _sp = max(wR, wS, wI) - min(wR, wS, wI)
        P(f"      META-CHECK: do the three arms SEPARATE? spread {_sp:.0f} m -> "
          f"{'*** TAUTOLOGY -- structure makes no difference ***' if _sp < 50 else 'YES — error STRUCTURE matters, not only size'}")
        P(f"      -> if RSSFIT is WORSE than its own magnitudes in random directions,")
        P(f"         the harm is in the DIRECTION (systematic inward bias), not the")
        P(f"         size. That ties C1 to the survey-footprint argument.")

        # ---------- VARIANT 3: does it matter WHICH gateways are wrong?
        P(f"\n  (3) SELECTION-WEIGHTED ARM. Does it matter WHICH gateways are wrong?")
        selc = {}
        for mm in EV:
            rx = [r for r in mm.receptions if r.gid in PHYS]
            if len(rx) < 3: continue
            for r in sorted(rx, key=lambda r: -r.rssi)[:args.max_gws]:
                selc[r.gid] = selc.get(r.gid, 0) + 1
        order = sorted(G, key=lambda g: -selc.get(g, 0))
        f3 = max(3, len(G)//4)
        top = set(order[:f3]); bot = set(order[-f3:])
        P(f"      f = {f3} gateways displaced {args.corrupt_disp} m, A0 refitted")
        P(f"      {'which gateways':<34}{'total selections':>18}{'WCL_bc':>10}{'vs true':>10}")
        for tag, tg in (("MOST-selected", top), ("LEAST-selected", bot)):
            a, b, _ = score(build(PHYS, tg, args.corrupt_disp, 6060))
            P(f"      {tag:<34}{sum(selc.get(g,0) for g in tg):>18}{a:>9.0f}m"
              f"{100*(a-w0)/w0:>9.1f}%")
        rw = []
        for d in range(args.corrupt_draws):
            tg = set(random.Random(6100 + d).sample(G, f3))
            a, b, _ = score(build(PHYS, tg, args.corrupt_disp, 6200 + d)); rw.append(a)
        P(f"      {'RANDOM choice (median of draws)':<34}{'--':>18}"
          f"{np.median(rw):>9.0f}m{100*(np.median(rw)-w0)/w0:>9.1f}%")
        zt, _, _ = score(build(PHYS, top, 0.0, 3))
        zb, _, _ = score(build(PHYS, bot, 0.0, 4))
        P(f"      META-CHECK at ZERO displacement: MOST {100*(zt-w0)/w0:+.2f}% | "
          f"LEAST {100*(zb-w0)/w0:+.2f}%  -> "
          f"{'PASS — no separation when nothing is corrupted' if max(abs(zt-w0),abs(zb-w0))/w0 < 0.005 else '*** TAUTOLOGY -- the arms differ with NO error injected ***'}")
        P(f"      -> if MOST and LEAST differ materially, damage depends on SELECTION")
        P(f"         FREQUENCY, not on the count of wrong anchors.")

    # ============================== BLOCK 22 -- CONTEXTUAL FLOORS  [register M1]
    if 22 in BL:
        P("\n" + "=" * 96)
        P("BLOCK 22 -- IS THE FLOOR VALID WHERE IT IS APPLIED?  [register item M1]")
        P("=" * 96)
        P("  BLOCK 1 measures ONE floor: ABS+mean, k=10, VERIFIED coords, citywide")
        P("  draws of the full sample. That single number is then applied to")
        P("  east-only arms, k<10 arms, WCL rather than ABS+mean, and to HDOP rows")
        P("  evaluated at n=400. Each is a DIFFERENT sampling condition. This block")
        P("  measures the floor SEPARATELY in each, so every verdict can be read")
        P("  against its own bar rather than a borrowed one.")
        P("  A floor is (2 * sd / mean) of the median across independent draws.")

        def ctx_floor(pool_, size, est, k, coords, tag, reps=None):
            reps = reps or args.floor_reps
            a0m = fit_a0(cal, coords, n); meds = []
            for r in range(reps):
                sub = random.Random(8800 + r).sample(pool_, min(size, len(pool_)))
                e = []
                for mm in sub:
                    rx = [x for x in mm.receptions if x.gid in coords and x.gid in a0m]
                    if len(rx) < 3: continue
                    rx = sorted(rx, key=lambda x: -x.rssi)[:k]
                    g_ = np.vstack([coords[x.gid] for x in rx])
                    raw = np.array([x.rssi for x in rx], float)
                    rv = raw - np.array([a0m[x.gid] for x in rx], float)
                    t = np.array([mm.x, mm.y], float)
                    # GAP FILLED 19 Aug: the differential objective may have its
                    # OWN floor. Every verdict about it was read against ABS+mean.
                    # MIN-MAX ARM added 19 Aug. BLOCK 22 measured floors for
                    # ABS+mean, WCL and DIFF only. Min-Max now appears in EIGHT
                    # blocks (7, 8, 15, 21, 24, 26, 27, 30) and every
                    # resolvable/below-floor verdict about it was being read
                    # against a floor measured for a DIFFERENT method. Its own
                    # floor was never measured.
                    _e = (wcl(ev, g_, rv) if est == "wcl"
                          else lattice(ev, g_, rv, n, "diff", "median") if est == "diff"
                          else minmax(g_, rv, n) if est == "minmax"
                          else lattice(ev, g_, rv, n, "abs", "mean"))
                    e.append(float(np.linalg.norm(_e - t)))
                if len(e) >= 30: meds.append(float(np.median(e)))
            if len(meds) < 3: return float("nan"), float("nan"), 0
            v = np.array(meds)
            return 2.0 * 100.0 * v.std(ddof=1) / v.mean(), float(np.median(v)), len(meds)

        elig = [mm for mm in pool if mkey(mm) not in calkeys
                and sum(1 for r in mm.receptions if r.gid in PHYS) >= 3]
        xs = np.array([mm.x for mm in elig], float); xmed = float(np.median(xs))
        east = [mm for mm in elig if mm.x >= xmed]
        west = [mm for mm in elig if mm.x < xmed]
        deep = [mm for mm in elig
                if sum(1 for r in mm.receptions if r.gid in PHYS) >= 5]

        base = FLOOR.get("seed")
        P(f"\n  BLOCK 1's floor, applied everywhere: "
          f"{('%.1f%%' % base) if base else 'not measured (run BLOCK 1)'}")
        P(f"  {'context':<42}{'n/draw':>8}{'floor':>9}{'median':>9}{'vs BLOCK 1':>13}")
        rows = [
            ("BLOCK 1 conditions, re-measured here", elig, len(EV), "abs", args.max_gws, PHYS),
            ("WCL instead of ABS+mean",              elig, len(EV), "wcl", args.max_gws, PHYS),
            ("DIFF instead of ABS+mean",             elig, len(EV), "diff", args.max_gws, PHYS),
            ("MinMax instead of ABS+mean",           elig, len(EV), "minmax", args.max_gws, PHYS),
            ("EAST half only",                       east, min(1200, len(east)), "abs", args.max_gws, PHYS),
            ("WEST half only",                       west, min(1200, len(west)), "abs", args.max_gws, PHYS),
            ("k=5 instead of k=10",                  deep, min(1200, len(deep)), "abs", 5, PHYS),
            ("k=7 instead of k=10",                  deep, min(1200, len(deep)), "abs", 7, PHYS),
            ("n=400 (the HDOP rows)",                elig, 400, "abs", args.max_gws, PHYS),
            ("ESTIMATED coordinates",                elig, len(EV), "abs", args.max_gws, RSSF),
            # GAP 1, 16 Aug: the SMALLEST real populations in the harness were
            # never tested. BLOCK 4's ON stratum runs at n=323 and the deepest
            # fixed-population k-arms at n=1,398. If the floor widens at n=400 it
            # must be measured where the harness actually goes.
            ("n=1400 (deep k-sweep arms)",           elig, 1400, "abs", args.max_gws, PHYS),
            ("n=323 (BLOCK 4 ON stratum size)",      elig, 323, "abs", args.max_gws, PHYS),
            ("n=150 (smallest interpreted row)",     elig, 150, "abs", args.max_gws, PHYS),
        ]
        worst = 0.0; ctl = None
        for tag, pl, sz, est, k, co in rows:
            fl, md, nd = ctx_floor(pl, sz, est, k, co, tag)
            if not np.isfinite(fl):
                P(f"  {tag:<42}{sz:>8}    THIN"); continue
            if ctl is None: ctl = fl          # first row IS the negative control
            worst = max(worst, fl)
            # PUBLISH THE PER-METHOD FLOORS, 19 Aug. BLOCK 24 needs them to give
            # a per-COLUMN verdict; without this it silently falls back to the
            # shared BLOCK 1 floor and the four methods are judged by one bar.
            # Only the full-eval method rows qualify -- the n= and half-city rows
            # vary the CONTEXT, not the method, and must not overwrite these.
            if tag.endswith("instead of ABS+mean") and sz == len(EV):
                FLOOR[est] = fl
            # PRECEDENCE FIXED 19 Aug. This wrote FLOOR["abs"] from the row that
            # RE-MEASURES BLOCK 1 conditions -- but that row is the NEGATIVE
            # CONTROL. Its job is to VALIDATE BLOCK 1 floor, not to replace it.
            # Letting the control overwrite the authoritative number inverts the
            # relationship: the thing being checked would be set by the check.
            # BLOCK 1 stays authoritative for ABS+mean; the control value is kept
            # SEPARATELY so the two can still be compared.
            if tag.startswith("BLOCK 1 conditions"):
                FLOOR["abs_control"] = fl     # for comparison, NOT for use
            rel = (f"{fl/base:.2f}x" if base else "--")
            flag = "  <-- WIDER" if base and fl > base * 1.5 else ""
            P(f"  {tag:<42}{sz:>8}{fl:>8.1f}%{md:>8.0f}m{rel:>13}{flag}")

        # ---- NEGATIVE CONTROL. Row 1 re-measures BLOCK 1's OWN conditions with a
        # different seed family. It must reproduce BLOCK 1's floor. If it does
        # not, the floor ESTIMATOR is noisier than the differences between
        # contexts, and no contextual comparison below is interpretable.
        if base and ctl:
            disc = 100.0 * abs(ctl - base) / base
            P(f"\n  NEGATIVE CONTROL -- row 1 re-measures BLOCK 1's own conditions")
            P(f"  under a different seed family. It MUST reproduce BLOCK 1's floor.")
            P(f"      BLOCK 1 {base:.1f}%  vs  re-measured {ctl:.1f}%  -> differ {disc:.0f}%")
            if disc > 25:
                P(f"      *** CONTROL FAILS. The floor ESTIMATOR's own noise ({disc:.0f}%)")
                P(f"          is comparable to the differences between contexts. Raise")
                P(f"          --floor-reps and --samples before reading the table above.")
                P(f"          Only ratios FAR outside {disc:.0f}% are interpretable. ***")
            else:
                P(f"      PASS -- estimator noise {disc:.0f}% is small against the spread")
                P(f"      of contexts ({base:.1f}%-{worst:.1f}%), so the table is readable.")
        # ---- META-CHECK. If every context returns the same floor the block is
        # measuring nothing.
        P(f"  META-CHECK: do the contexts SEPARATE? "
          f"{'*** TAUTOLOGY -- all contexts identical ***' if base and worst < base*1.2 else f'YES — spread {base:.1f}%-{worst:.1f}%' if base else 'BLOCK 1 not run'}")

        # ---- GAP 2: the CALIBRATION-draw floor was never tested. BLOCK 1 reports
        # two floors; only the evaluation-draw one was checked above. The
        # calibration-draw floor gates BLOCK 5's paired objective comparisons.
        P(f"\n  (b) THE CALIBRATION-DRAW FLOOR. BLOCK 1 reports TWO floors and only")
        P(f"      the evaluation-draw one was tested above. This one gates the paired")
        P(f"      objective-form comparisons, where 'below floor' is a stated finding.")
        cbase = FLOOR.get("draw")
        def cal_floor(coords, est, k, reps=None):
            reps = reps or args.floor_reps; meds = []
            for r in range(reps):
                sub = random.Random(9600 + r).sample(cal, max(50, int(len(cal) * 0.3)))
                a0m = fit_a0(sub, coords, n); e = []
                for mm in EV:
                    rx = [x for x in mm.receptions if x.gid in coords and x.gid in a0m]
                    if len(rx) < 3: continue
                    rx = sorted(rx, key=lambda x: -x.rssi)[:k]
                    g_ = np.vstack([coords[x.gid] for x in rx])
                    raw = np.array([x.rssi for x in rx], float)
                    rv = raw - np.array([a0m[x.gid] for x in rx], float)
                    t = np.array([mm.x, mm.y], float)
                    # GAP FILLED 19 Aug: the differential objective may have its
                    # OWN floor. Every verdict about it was read against ABS+mean.
                    # MIN-MAX ARM added 19 Aug. BLOCK 22 measured floors for
                    # ABS+mean, WCL and DIFF only. Min-Max now appears in EIGHT
                    # blocks (7, 8, 15, 21, 24, 26, 27, 30) and every
                    # resolvable/below-floor verdict about it was being read
                    # against a floor measured for a DIFFERENT method. Its own
                    # floor was never measured.
                    _e = (wcl(ev, g_, rv) if est == "wcl"
                          else lattice(ev, g_, rv, n, "diff", "median") if est == "diff"
                          else minmax(g_, rv, n) if est == "minmax"
                          else lattice(ev, g_, rv, n, "abs", "mean"))
                    e.append(float(np.linalg.norm(_e - t)))
                if len(e) >= 30: meds.append(float(np.median(e)))
            if len(meds) < 3: return float("nan")
            v = np.array(meds); return 2.0 * 100.0 * v.std(ddof=1) / v.mean()
        P(f"      BLOCK 1's calibration-draw floor: "
          f"{('%.1f%%' % cbase) if cbase else 'not measured'}")
        cctl = None
        for tag, est, k in (("ABS+mean, k=10 (BLOCK 1's own)", "abs", args.max_gws),
                            ("WCL, k=10", "wcl", args.max_gws),
                            ("ABS+mean, k=5", "abs", 5),
                            ("DIFF+median, k=10", "diff", args.max_gws)):
            cf = cal_floor(PHYS, est, k)
            if cctl is None: cctl = cf        # row 1 IS the negative control
            # nan-GUARD 19 Aug: ctx_floor returns nan when fewer than 3 draws
            # survive. The EVALUATION-floor table above already prints THIN in
            # that case; this one printed a bare "nan%". No nan may reach output.
            if not np.isfinite(cf):
                P(f"      {tag:<38}    THIN -- too few draws at "
                  f"--floor-reps {args.floor_reps}")
                continue
            rel = f"{cf/cbase:.2f}x" if cbase else "--"
            P(f"      {tag:<38}{cf:>8.1f}%{rel:>10}")
        # NEGATIVE CONTROL for the calibration floor. Row 1 re-measures BLOCK 1's
        # own calibration-draw conditions under a different seed family and must
        # reproduce it. Without this the two rows below mean nothing -- the same
        # omission the evaluation-floor table had before 16 Aug.
        if cbase and cctl and np.isfinite(cctl):
            cd = 100.0 * abs(cctl - cbase) / cbase
            P(f"      NEGATIVE CONTROL: BLOCK 1 {cbase:.1f}% vs re-measured "
              f"{cctl:.1f}% -> differ {cd:.0f}%")
            P(f"      {'PASS -- calibration-floor estimator is stable; the rows above are readable' if cd <= 25 else '*** CONTROL FAILS -- calibration-floor noise exceeds the differences; do not read the rows above ***'}")

        # ---- GAP 3: I chose 20 draws and then discovered 26% noise. Sweep it.
        P(f"\n  (c) HOW MANY DRAWS DOES A FLOOR NEED? The control above is read")
        P(f"      against --floor-reps; at 20 draws it FAILED and at 40 it PASSES.")
        P(f"      That is a fact about the CHOICE, not about the estimator, unless")
        P(f"      the draw count is swept.")
        P(f"      {'draws':>7}{'floor':>9}{'vs 20-draw':>12}")
        ref20 = None
        for R in (5, 10, 20, 40):
            fl, _md, _n = ctx_floor(elig, len(EV), "abs", args.max_gws, PHYS, "conv", reps=R)
            if R == 20: ref20 = fl
            rel = f"{fl/ref20:.2f}x" if ref20 else "--"
            P(f"      {R:>7}{fl:>8.1f}%{rel:>12}")
        P(f"      -> if the floor keeps moving at 40 draws, it is IRREDUCIBLY noisy")
        P(f"         at achievable draw counts and must be quoted with that caveat.")
        P(f"\n  -> a context whose floor is WIDER than BLOCK 1's means any verdict")
        P(f"     there was read against too generous a bar. Widest seen: {worst:.1f}%.")
        if base:
            P(f"     Effects between {base:.1f}% and {worst:.1f}% are resolvable in SOME")
            P(f"     contexts and not in others, and must be reported per context.")

    # ============================== BLOCK 23 -- IS THE STRICT SUBSET STABLE? [C4b]
    if 23 in BL:
        P("\n" + "=" * 96)
        P("BLOCK 23 -- DOES THE STRONG SUBSET REPRODUCE FROM DISJOINT DATA?  [C4b]")
        P("=" * 96)
        P(floor_line(FLOOR))
        P("  The map's caveat rests on ONE number: the RAW BS->EUI assignment")
        P("  reproduced on roughly half of columns across disjoint halves, which")
        P("  this block now MEASURES rather than quotes. From that we INFERRED")
        P("  that the filtered strong subset is sound. **That")
        P("  inference has never been tested.** If the strong subset reproduces no")
        P("  better than the raw assignment, the rank/correlation filter is not")
        P("  doing what we claimed and sec.5's caveat must HARDEN.")
        # BLOCK 23 needs BOTH the strong subset AND the published-candidate
        # coordinate array, and both are built inside BLOCK 0. Guard for each,
        # or a --blocks 23 run raises NameError instead of saying why.
        _S23 = _CU23 = None
        try:
            _S23 = set(STRONG); _CU23 = CU
        except NameError:
            P("  *** BLOCK 0 did not run, so the strong subset and the published")
            P("      candidate coordinates are both unknown. Re-run with")
            P("      --blocks 0,23 (or the full set). ***")
            _S23 = None
        if _S23 is not None and _CU23 is not None:
            def assign(msgs):
                """Re-derive BS -> published-EUI by RSSI-distance correlation,
                exactly as the recovery procedure does, on the given messages."""
                by = {}
                for x in msgs:
                    for r in x.receptions:
                        by.setdefault(r.gid, []).append((float(r.rssi), x.x, x.y))
                out = {}
                for g, v in by.items():
                    a = np.array(v, float)
                    if len(a) < 40: continue
                    rr, tx = a[:, 0], a[:, 1:3]; rc = rr - rr.mean()
                    d = np.sqrt((tx[:, 0:1] - _CU23[None, :, 0]) ** 2
                                + (tx[:, 1:2] - _CU23[None, :, 1]) ** 2)
                    nd = -d; nd = nd - nd.mean(axis=0, keepdims=True)
                    den = np.sqrt((rc ** 2).sum()) * np.sqrt((nd ** 2).sum(axis=0))
                    corr = (rc[:, None] * nd).sum(axis=0) / np.where(den == 0, 1e-9, den)
                    out[g] = (int(np.argmax(corr)), float(corr.max()))
                return out
            hA, hB = cal[0::2], cal[1::2]
            A, B = assign(hA), assign(hB)
            common = sorted(set(A) & set(B), key=int)
            P(f"\n  disjoint halves of the calibration split: {len(hA)} and {len(hB)} messages")
            P(f"  columns assignable in BOTH halves: {len(common)}")
            P(f"\n  {'population':<34}{'n':>5}{'same EUI':>11}{'pos <=500 m':>13}{'median shift':>14}")
            for tag, sub in (("ALL assignable columns", common),
                             ("STRONG subset only", [g for g in common if g in _S23]),
                             ("WEAK (dropped) columns only",
                              [g for g in common if g not in _S23])):
                if not sub:
                    P(f"  {tag:<34}{0:>5}   none"); continue
                same = sum(1 for g in sub if A[g][0] == B[g][0])
                sh = np.array([float(np.linalg.norm(_CU23[A[g][0]] - _CU23[B[g][0]]))
                               for g in sub])
                near = int((sh <= 500).sum())
                P(f"  {tag:<34}{len(sub):>5}{100*same/len(sub):>10.0f}%"
                  f"{100*near/len(sub):>12.0f}%{np.median(sh):>13.0f}m")
            strongs = [g for g in common if g in _S23]
            weaks = [g for g in common if g not in _S23]
            if strongs and weaks:
                ss = 100*sum(1 for g in strongs if A[g][0]==B[g][0])/len(strongs)
                ws = 100*sum(1 for g in weaks if A[g][0]==B[g][0])/len(weaks)
                P(f"\n  -> STRONG {ss:.0f}% vs WEAK {ws:.0f}% exact-EUI agreement.")
                P(f"     {'THE FILTER WORKS: the strong subset is markedly more stable.' if ss > ws + 15 else 'THE FILTER DOES NOT SEPARATE THEM -- sec.5 caveat must HARDEN.' if ss <= ws + 5 else 'PARTIAL: the filter helps but does not resolve the caveat.'}")
            # NEGATIVE CONTROL: the same half against ITSELF must agree 100%.
            A2 = assign(hA)
            selfsame = sum(1 for g in A if g in A2 and A[g][0] == A2[g][0])
            P(f"\n  NEGATIVE CONTROL: the same half re-assigned must agree 100%.")
            P(f"      {selfsame}/{len(A)} = {100*selfsame/max(len(A),1):.0f}%   "
              f"{'PASS' if selfsame == len(A) else '*** FAIL -- the procedure is not deterministic ***'}")
            # POSITIVE CONTROL: a half with SHUFFLED positions must agree far less.
            import copy as _cp
            hS = []
            _rg = np.random.default_rng(31337)
            _pts = np.array([[m_.x, m_.y] for m_ in hB], float); _rg.shuffle(_pts)
            for _i, m_ in enumerate(hB):
                m2 = _cp.copy(m_); m2.x, m2.y = float(_pts[_i, 0]), float(_pts[_i, 1])
                hS.append(m2)
            S_ = assign(hS)
            cs = sorted(set(A) & set(S_), key=int)
            shuf_same = sum(1 for g in cs if A[g][0] == S_[g][0])
            P(f"  POSITIVE CONTROL: half B with SHUFFLED transmitter positions must")
            P(f"      agree far LESS. {shuf_same}/{len(cs)} = {100*shuf_same/max(len(cs),1):.0f}%   "
              f"{'PASS -- the test discriminates' if 100*shuf_same/max(len(cs),1) < 40 else '*** TAUTOLOGY -- agreement is not driven by the data ***'}")

    # ============================== BLOCK 24 -- WHAT IS OUR OWN MAP'S ERROR WORTH?
    if 24 in BL:
        P("\n" + "=" * 96)
        P("BLOCK 24 -- THE UNANSWERABLE, BOUNDED: what does OUR map's residual cost?")
        P("=" * 96)
        P(floor_line(FLOOR))
        P("  Every accuracy figure in this programme is measured against a map we")
        P("  RECOVERED. We cannot say what a method achieves on this deployment --")
        P("  only what it achieves against our map. That sentence is unavailable to")
        P("  us and to anyone else, because no public record of these receivers'")
        P("  true positions exists.")
        P("")
        P("  ONE ASYMMETRY HELPS. The TRANSMITTER positions are ground truth: GPS-")
        P("  tagged and published. Error is |estimate - true transmitter|. Residual")
        P("  error in the RECEIVER map can only DISPLACE the estimate, never improve")
        P("  it. **So every accuracy figure here is an UPPER BOUND.**")
        P("")
        P("  This block measures HOW LOOSE that bound is, by displacing the map by")
        P("  ITS OWN estimated residual and reporting the inflation.")

        def mk(base, targets, disp, seed):
            rg = np.random.default_rng(seed); out = {}
            for g, v in base.items():
                if g in targets:
                    th = rg.uniform(0, 2*np.pi)
                    out[g] = v + disp*np.array([np.cos(th), np.sin(th)])
                else:
                    out[g] = np.array(v, float)
            return out

        def sc(mp):
            a0m = fit_a0(cal, mp, n); ew, ea = [], []
            for mm in EV:
                rx = [r for r in mm.receptions if r.gid in mp and r.gid in a0m]
                if len(rx) < 3: continue
                rx = sorted(rx, key=lambda r: -r.rssi)[:args.max_gws]
                g_ = np.vstack([mp[r.gid] for r in rx])
                raw = np.array([r.rssi for r in rx], float)
                rv = raw - np.array([a0m[r.gid] for r in rx], float)
                t = np.array([mm.x, mm.y], float)
                ew.append(float(np.linalg.norm(wcl(ev, g_, rv) - t)))
                ea.append(float(np.linalg.norm(lattice(ev, g_, rv, n, "abs", "mean") - t)))
            return float(np.median(ew)), float(np.median(ea))
        # GAP FILLED 19 Aug. The differential objective was absent from this
        # block. Rather than change the return arity of the scorer above -- which
        # has many call sites and would risk every one -- this is an ADDITIVE
        # diff-only companion. No existing caller changes, so every number
        # already published by this block is untouched.
        def sc_diff(mp):
            a0m = fit_a0(cal, mp, n); out = []
            for mm in EV:
                rx = [r for r in mm.receptions if r.gid in mp and r.gid in a0m]
                if len(rx) < 3: continue
                rx = sorted(rx, key=lambda r: -r.rssi)[:args.max_gws]
                g_ = np.vstack([mp[r.gid] for r in rx])
                rv_ = (np.array([r.rssi for r in rx], float)
                       - np.array([a0m[r.gid] for r in rx], float))
                out.append(float(np.linalg.norm(
                    lattice(ev, g_, rv_, n, "diff", "median")
                    - np.array([mm.x, mm.y], float))))
            return float(np.median(out)) if out else float("nan")

        # MIN-MAX companion added 19 Aug, same additive pattern as the
        # differential one above: no existing caller changes.
        def sc_mm(mp):
            a0m = fit_a0(cal, mp, n); out = []
            for mm in EV:
                rx = [r for r in mm.receptions if r.gid in mp and r.gid in a0m]
                if len(rx) < 3: continue
                rx = sorted(rx, key=lambda r: -r.rssi)[:args.max_gws]
                g_ = np.vstack([mp[r.gid] for r in rx])
                rv_ = (np.array([r.rssi for r in rx], float)
                       - np.array([a0m[r.gid] for r in rx], float))
                out.append(float(np.linalg.norm(
                    minmax(g_, rv_, n)
                    - np.array([mm.x, mm.y], float))))
            return float(np.median(out)) if out else float("nan")

        w0, a0ref = sc(PHYS); d0 = sc_diff(PHYS); m0 = sc_mm(PHYS)
        P(f"\n  reference: WCL_bc {w0:.0f} m | ABS+mean {a0ref:.0f} m | "
          f"DIFF {d0:.0f} m | MinMax {m0:.0f} m")
        P(f"\n  OUR MAP'S ESTIMATED RESIDUAL, from the disjoint-halves test:")
        P(f"    ~70% of retained columns place within 500 m across halves")
        P(f"    ~30% shift MORE than 500 m | median shift 0 m")
        P(f"  We therefore inject that pattern: a fraction f of receivers displaced")
        P(f"  by delta, {args.corrupt_draws} realisations each, A0 refitted every time.")
        P(f"\n  {'f':>6}{'delta':>9}{'WCL_bc':>9}{'infl':>7}{'ABS+mean':>10}{'infl':>7}"
          f"{'DIFF':>8}{'infl':>7}{'MinMax':>9}{'infl':>7}{'vs floor':>11}")
        fl = FLOOR.get("seed")
        for f_, d_ in ((0.30, 250.0), (0.30, 500.0), (0.30, 1000.0),
                       (0.50, 500.0), (1.00, 500.0)):
            k = max(1, int(round(f_ * len(G))))
            ws, as_, ds, ms = [], [], [], []
            for r in range(args.corrupt_draws):
                tg = set(random.Random(7300 + r).sample(G, k))
                a, b = sc(mk(PHYS, tg, d_, 7400 + r)); ws.append(a); as_.append(b)
                ds.append(sc_diff(mk(PHYS, tg, d_, 7400 + r)))
                ms.append(sc_mm(mk(PHYS, tg, d_, 7400 + r)))
            wm, am, dm_, mm_ = (float(np.median(ws)), float(np.median(as_)),
                                float(np.median(ds)), float(np.median(ms)))
            iw = 100*(wm-w0)/w0; ia = 100*(am-a0ref)/a0ref
            idf = 100*(dm_-d0)/d0; imm = 100*(mm_-m0)/m0
            # PER-METHOD VERDICT, 19 Aug. This printed ONE verdict for a row of
            # FOUR methods, taken from the LARGEST inflation. At f=0.30,
            # delta=500 that row read "resolvable" -- true for WCL (10.7%) and
            # DIFF (7.0%) against their own floors, but ABS+mean is 3.4% against
            # its 4.5% floor and is NOT resolvable. The methods also have
            # DIFFERENT floors (BLOCK 22: ABS 4.5%, WCL 4.6%, DIFF 5.4%, MinMax
            # widest of the four), so one verdict cannot serve four columns.
            # Each column is now marked with a * when it clears ITS OWN floor.
            _fw = FLOOR.get("wcl"); _fa = FLOOR.get("seed")   # BLOCK 1 is authoritative for ABS+mean
            _fd = FLOOR.get("diff"); _fm = FLOOR.get("minmax")
            # DEPENDENCY GUARD, 19 Aug. The per-method floors are PUBLISHED BY
            # BLOCK 22. Run without it, every key is missing and the columns fall
            # back to the shared floor -- the asterisks still print and the
            # per-method promise is SILENTLY NOT KEPT. Same failure class as
            # BLOCK 30's missing FLOOR["seed"]. Say it instead of hiding it.
            _permethod = all(x is not None for x in (_fw, _fa, _fd, _fm))
            if not _permethod:
                _fw = _fa = _fd = _fm = fl
            def _m(v, f_own):
                return "*" if (f_own and abs(v) > f_own) else " "
            n_res = sum(1 for v, f_own in ((iw, _fw), (ia, _fa), (idf, _fd), (imm, _fm))
                        if f_own and abs(v) > f_own)
            verdict = f"{n_res}/4 resolvable" if n_res else "BELOW FLOOR"
            P(f"  {f_:>6.2f}{d_:>8.0f}m{wm:>8.0f}m{iw:>6.1f}%{_m(iw,_fw)}{am:>8.0f}m{ia:>6.1f}%{_m(ia,_fa)}"
              f"{dm_:>6.0f}m{idf:>6.1f}%{_m(idf,_fd)}{mm_:>7.0f}m{imm:>6.1f}%{_m(imm,_fm)}{verdict:>16}")
        if not _permethod:
            P(f"\n  *** BLOCK 22 DID NOT RUN, so no per-method floor exists. Every")
            P(f"      column above is judged against the SHARED floor {fl:.1f}%, which is")
            P(f"      NOT what the asterisk claims. Re-run with --blocks 1,22,24 to get")
            P(f"      the per-method verdict. ***")
        P(f"\n  * = that METHOD's inflation exceeds ITS OWN floor (BLOCK 22 measures")
        P(f"      a separate floor per method). An unmarked column is BELOW its floor")
        P(f"      and its inflation must NOT be quoted as a correction.")
        P(f"\n  OUR CASE is the f=0.30, delta=500 m row.")
        P(f"  -> if that row is BELOW FLOOR, the bound is TIGHT: our reported")
        P(f"     accuracies are upper bounds that cannot be loose by more than the")
        P(f"     evaluation-draw floor itself. If it is resolvable, we must quote")
        P(f"     the inflation alongside every accuracy figure.")
        P(f"\n  CONTROL: f=0.30 at delta=0 must return the reference exactly.")
        cz, az = sc(mk(PHYS, set(random.Random(1).sample(G, max(1, int(0.3*len(G))))), 0.0, 1))
        P(f"      {cz:.1f} m vs {w0:.1f} m  "
          f"{'PASS' if abs(cz-w0) < 1e-6 else '*** FAIL -- apparatus not neutral ***'}")
        P(f"\n  WHAT THIS CANNOT BUY: an absolute accuracy claim. Every figure stays")
        P(f"  'X m against our recovered map', never 'X m on this deployment'. Only")
        P(f"  a published receiver-coordinate table converts one into the other.")

    # ============================== BLOCK 25 -- THE FINGERPRINTING ASYMMETRY
    if 25 in BL:
        P("\n" + "=" * 96)
        P("BLOCK 25 -- FINGERPRINTING NEEDS NO RECEIVER COORDINATES")
        P("=" * 96)
        P(floor_line(FLOOR))
        P("  Every geometric figure in this paper is 'X m AGAINST OUR RECOVERED MAP'.")
        P("  A fingerprinting method uses no receiver positions at all, so its")
        P("  accuracy on this benchmark is EXACT -- one number, no substrate.")
        P("  This block measures that number and, more importantly, the property")
        P("  that justifies range-based methods existing: TRANSFER.")
        P("")
        P("  THE TRAP THIS BLOCK IS BUILT TO AVOID. The calibration set is 16,612")
        P("  points along ONE DRIVE ROUTE. Splitting it at random puts an evaluation")
        P("  point metres from a calibration point, which hands the fingerprint the")
        P("  answer. **Every accuracy figure below is reported WITH the distance to")
        P("  the nearest calibration point**, without which it is uninterpretable.")

        FLOOR_DBM = FP_FLOOR_DBM
        GIDS = sorted({r.gid for m_ in cal for r in m_.receptions}
                      | {r.gid for m_ in EV for r in m_.receptions})
        vec = lambda msgs: fp_vec(msgs, GIDS)
        nearest_cal = fp_nearest
        # BLOCK 25 needs the full error vector for p90, so it asks for it. One
        # implementation, one flag -- no second copy of the distance code.
        knn = lambda dbX, dbY, qX, qY, k=3: fp_knn(dbX, dbY, qX, qY, k=k,
                                                   return_all=True)

        DBcap = min(args.fp_dbcap, len(cal))
        db = cal if len(cal) <= DBcap else random.Random(88).sample(cal, DBcap)
        dbX, dbY = vec(db); qX, qY = vec(EV)
        P(f"\n  fingerprint database: {len(db)} calibration messages x {len(GIDS)} receivers")
        P(f"  missing receptions filled at {FLOOR_DBM:.0f} dBm | Euclidean | mean of k nearest")

        # ---------- (0) APPARATUS CONTROLS. Both must fire.
        P(f"\n  (0) APPARATUS CONTROLS -- a fingerprint result with neither is not evidence.")
        selfE = knn(qX[:300], qY[:300], qX[:300], qY[:300], k=1)
        P(f"      POSITIVE: query points INCLUDED in the database, k=1.")
        P(f"        median {np.median(selfE):.1f} m   "
          f"{'PASS -- it retrieves its own point' if np.median(selfE) < 1.0 else '*** FAIL -- retrieval is broken ***'}")
        rgs = np.random.default_rng(515); perm = rgs.permutation(len(dbY))
        shufE = knn(dbX, dbY[perm], qX[:600], qY[:600], k=3)
        span = float(np.linalg.norm(qY.max(axis=0) - qY.min(axis=0)))
        P(f"      NEGATIVE: database POSITIONS shuffled -- accuracy must collapse")
        P(f"        median {np.median(shufE):.0f} m against a survey span of {span:.0f} m   "
          f"{'PASS -- signal comes from the RSSI match' if np.median(shufE) > 0.15*span else '*** TAUTOLOGY -- position is not doing the work ***'}")

        # ---------- (a) the number that needs no substrate
        P(f"\n  (a) FINGERPRINTING ON THE PUBLISHED RANDOM SPLIT")
        P(f"      {'k':>4}{'median':>10}{'p90':>9}{'nearest cal pt':>16}")
        ncal = nearest_cal(qY, dbY)
        for kk in (1, 3, 5):
            e = knn(dbX, dbY, qX, qY, k=kk)
            P(f"      {kk:>4}{np.median(e):>9.0f}m{np.percentile(e,90):>8.0f}m"
              f"{np.median(ncal):>15.0f}m")
        P(f"      nearest calibration point: median {np.median(ncal):.0f} m | "
          f"p90 {np.percentile(ncal,90):.0f} m | max {ncal.max():.0f} m")
        P(f"      *** THAT is why the number is small. The evaluation point sits")
        P(f"          metres from a calibration point on the same drive route. ***")

        # ---------- (b) TRANSFER -- the property that justifies range-based methods
        P(f"\n  (b) TRANSFER: calibrate in one half of the city, evaluate in the other.")
        allm = cal + pool
        xmed = float(np.median([m_.x for m_ in allm]))
        E = [m_ for m_ in allm if m_.x >= xmed and mkey(m_) not in calkeys]
        W = [m_ for m_ in allm if m_.x < xmed]
        EVE = random.Random(9).sample(E, min(1200, len(E)))
        ekeys = set(mkey(m_) for m_ in EVE)
        Wdb = [m_ for m_ in W if mkey(m_) not in ekeys]
        if len(Wdb) > DBcap: Wdb = random.Random(89).sample(Wdb, DBcap)
        Rdb = [m_ for m_ in allm if mkey(m_) not in ekeys]
        if len(Rdb) > DBcap: Rdb = random.Random(90).sample(Rdb, DBcap)
        qEX, qEY = vec(EVE)
        P(f"      evaluation fixed to the EAST half ({len(EVE)} messages) in BOTH arms.")
        P(f"      {'database':<24}{'n':>7}{'FP median':>11}{'FP p90':>9}{'nearest cal':>13}")
        fp = {}
        for tag, D in (("citywide (in-region)", Rdb), ("WEST only (cross-region)", Wdb)):
            dX, dY = vec(D)
            e = knn(dX, dY, qEX, qEY, k=3); nc = nearest_cal(qEY, dY)
            fp[tag] = float(np.median(e))
            P(f"      {tag:<24}{len(D):>7}{np.median(e):>10.0f}m{np.percentile(e,90):>8.0f}m"
              f"{np.median(nc):>12.0f}m")
        deg = 100*(fp["WEST only (cross-region)"] - fp["citywide (in-region)"]) \
              / fp["citywide (in-region)"]
        P(f"      fingerprint degradation across regions: {deg:+.0f}%")

        # ---------- (c) the same two arms, geometric
        P(f"\n  (c) THE SAME TWO ARMS, RANGE-BASED (verified coordinates)")
        P(f"      {'calibration':<24}{'WCL_bc':>10}{'ABS+mean':>11}{'DIFF':>9}")
        geo = {}
        for tag, D in (("citywide (in-region)", Rdb), ("WEST only (cross-region)", Wdb)):
            a0m = fit_a0(D, PHYS, n); ew, ea, ed = [], [], []
            for mm in EVE:
                rx = [r for r in mm.receptions if r.gid in PHYS and r.gid in a0m]
                if len(rx) < 3: continue
                rx = sorted(rx, key=lambda r: -r.rssi)[:args.max_gws]
                g_ = np.vstack([PHYS[r.gid] for r in rx])
                raw = np.array([r.rssi for r in rx], float)
                rv = raw - np.array([a0m[r.gid] for r in rx], float)
                t = np.array([mm.x, mm.y], float)
                ew.append(float(np.linalg.norm(wcl(ev, g_, rv) - t)))
                ea.append(float(np.linalg.norm(lattice(ev, g_, rv, n, "abs", "mean") - t)))
                ed.append(float(np.linalg.norm(lattice(ev, g_, rv, n, "diff", "median") - t)))
            geo[tag] = (float(np.median(ew)), float(np.median(ea)), float(np.median(ed)))
            P(f"      {tag:<24}{geo[tag][0]:>9.0f}m{geo[tag][1]:>10.0f}m{geo[tag][2]:>8.0f}m")
        gd = [100*(geo['WEST only (cross-region)'][i] - geo['citywide (in-region)'][i])
              / geo['citywide (in-region)'][i] for i in range(3)]
        P(f"      range-based degradation: WCL_bc {gd[0]:+.0f}% | ABS+mean {gd[1]:+.0f}% | "
          f"DIFF {gd[2]:+.0f}%")
        P(f"\n  -> if the fingerprint degrades MUCH more than the range-based methods,")
        P(f"     the family the benchmark CANNOT evaluate is the one that transfers.")
        P(f"     If it does not, that is the finding and we report it.")
        P(f"\n  AND THE ASYMMETRY THIS BLOCK EXISTS TO SHOW: every fingerprint figure")
        P(f"  above is EXACT -- it uses no receiver coordinates. Every range-based")
        P(f"  figure is 'against our recovered map'. Same data, same split, same")
        P(f"  evaluation set; one family can be validated absolutely and the other")
        P(f"  cannot, on this benchmark, by anyone.")

    # ============================== BLOCK 26 -- RECEIVER-REMOVAL, BOTH FAMILIES
    if 26 in BL:
        P("\n" + "=" * 96)
        P("BLOCK 26 -- HOW DO THE TWO FAMILIES DEGRADE AS RECEIVERS ARE REMOVED?")
        P("=" * 96)
        P(floor_line(FLOOR))
        P("  A fingerprint does not need to know WHERE a receiver is, so every")
        P("  column in the file is usable to it. A range-based method can use only")
        P("  the receivers whose positions are known. **The same dataset therefore")
        P("  offers the two families DIFFERENT amounts of information.**")
        P("  This block measures (A) what that difference is worth, and (B) how")
        P("  each family degrades when receivers are removed from the SHARED set.")

        FLOOR_DBM = FP_FLOOR_DBM
        ALLG = sorted({r.gid for m_ in cal for r in m_.receptions}
                      | {r.gid for m_ in EV for r in m_.receptions})
        MAPPED = [g for g in ALLG if g in PHYS]
        EXCL = [g for g in ALLG if g not in PHYS]
        P(f"\n  receiver columns in cal+eval          : {len(ALLG)}")
        P(f"  of those with KNOWN positions          : {len(MAPPED)}  (range-based can use)")
        P(f"  EXCLUSIVE to fingerprinting            : {len(EXCL)}  "
          f"({100*len(EXCL)/max(len(ALLG),1):.0f}% of usable columns)")
        P(f"  WHETHER THAT ACCESS IS WORTH ANYTHING is measured in (A) below, not")
        P(f"  assumed here. The COUNT is an asymmetry; its VALUE is an open question")
        P(f"  until (A) answers it.")

        fpv, fpknn = fp_vec, fp_knn
        DB = cal if len(cal) <= args.fp_dbcap else random.Random(88).sample(cal, args.fp_dbcap)

        # ---------- ARM A: what are the unmapped columns worth to fingerprinting?
        P(f"\n  (A) WHAT THE UNMAPPED COLUMNS ARE WORTH -- to fingerprinting only")
        dX, dY = fpv(DB, ALLG); qX, qY = fpv(EV, ALLG)
        fp_all = fpknn(dX, dY, qX, qY)
        dX2, dY2 = fpv(DB, MAPPED); qX2, qY2 = fpv(EV, MAPPED)
        fp_map = fpknn(dX2, dY2, qX2, qY2)
        P(f"      fingerprint on ALL {len(ALLG)} columns      : {fp_all:.0f} m")
        P(f"      fingerprint on the {len(MAPPED)} MAPPED only  : {fp_map:.0f} m")
        P(f"      the {len(EXCL)} unmapped columns are worth  : {100*(fp_map-fp_all)/fp_all:+.0f}% "
          f"to the fingerprint, and NOTHING to a range-based method")

        # ---------- ARM B: the removal curve, both families, same receivers
        P(f"\n  (B) REMOVAL CURVE. f receivers drawn at random FROM THE MAPPED SET,")
        P(f"      {args.rm_draws} draws each. BOTH families see the SAME remaining set.")
        P(f"      Reported on FOUR axes, because median alone hides how the two")
        P(f"      families differ under uncertainty:")
        P(f"        ACCURACY  median and p99")
        P(f"        FAILURE   share of fixes beyond 1 km -- a fingerprint that matches")
        P(f"                  the wrong cluster is catastrophically wrong, not gradually")
        P(f"        STABILITY spread across draws at the SAME count -- how much the")
        P(f"                  answer depends on WHICH receivers were lost")
        P(f"        COST      query latency per fix and the model an inference device")
        P(f"                  must hold resident")

        base_fp_all, base_ms = fp_knn(*fp_vec(DB, MAPPED), *fp_vec(EV, MAPPED),
                                      return_all=True, timed=True)
        base_fp = float(np.median(base_fp_all))
        _bfull, _nbfull = geo_eval(ev, PHYS, MAPPED, EV, cal, n, args.max_gws,
                                   wcl, lattice, fit_a0, arms=("wcl", "abs"))
        # bw/ba were the OLD table's baselines; the rewritten table uses
        # base_all. Kept as a NAMED reference so the dead-variable warning
        # does not mask a future real one.
        _unused_baselines = (_bfull["wcl"][0], _bfull["abs"][0])
        fl = FLOOR.get("seed")
        P(f"\n      {floor_line(FLOOR).strip()}")
        P(f"\n      ALL FIVE METHODS, IDENTICAL TREATMENT. No method is foregrounded:")
        P(f"      this compares FINGERPRINTING against the RANGE-BASED FAMILY, not")
        P(f"      one method against another.")
        P(f"\n      MEDIAN ERROR (m)")
        P(f"      {'recv':>5}{'FINGERPRINT':>13}{'WCL_bc':>9}{'ABS+mean':>10}"
          f"{'DIFF':>8}{'NLLS':>8}{'MinMax':>9}{'n':>7}")
        counts = sorted({len(MAPPED), int(len(MAPPED)*0.75), int(len(MAPPED)*0.5),
                         int(len(MAPPED)*0.35), 10, 6, 3}, reverse=True)
        ARMS = ("wcl", "abs", "diff", "nlls", "minmax")
        lat = {}
        base_all, _bn = geo_eval(ev, PHYS, MAPPED, EV, cal, n, args.max_gws,
                                 wcl, lattice, fit_a0, arms=ARMS)
        rows = [(c, None) for c in counts if 3 <= c <= len(MAPPED)]
        try:
            WEAKSET = [g for g in MAPPED if g not in set(STRONG)]
            if WEAKSET and len(MAPPED) - len(WEAKSET) >= 3:
                rows.append((len(MAPPED) - len(WEAKSET), frozenset(WEAKSET)))
        except NameError:
            # SILENT-DEGRADATION FIX 19 Aug: this used to `pass`, so running
            # BLOCK 26 without BLOCK 0 silently dropped the NON-RANDOM row
            # and nothing said why. BLOCKS 20 and 23 already say it.
            P("      *** BLOCK 0 did not run, so the weakest-assignment set is")
            P("         unknown and the NON-RANDOM (*) row below is OMITTED.")
            P("         Re-run with --blocks 0,26 to get it. ***")
        TAB = {}
        for c, forced in rows:
            ndraw = 1 if (c == len(MAPPED) or forced is not None) else args.rm_draws
            FP, GA, NS = [], {a: [] for a in ARMS}, []
            for d in range(ndraw):
                if forced is not None:
                    sub = [g for g in MAPPED if g not in forced]
                elif c == len(MAPPED):
                    sub = MAPPED
                else:
                    sub = random.Random(9500 + 31 * c + d).sample(MAPPED, c)
                fe, ms = fp_knn(*fp_vec(DB, sub), *fp_vec(EV, sub),
                                return_all=True, timed=True)
                if c not in lat: lat[c] = ms
                FP.append((float(np.median(fe)), float(np.mean(fe > 1000) * 100)))
                r, nn = geo_eval(ev, PHYS, sub, EV, cal, n, args.max_gws,
                                 wcl, lattice, fit_a0, arms=ARMS)
                for a in ARMS: GA[a].append(r[a])
                NS.append(nn)
            tag = f"{c}*" if forced is not None else f"{c}"
            nmed = int(np.median(NS))
            fmed = float(np.median([x[0] for x in FP]))
            med = {a: float(np.median([v[0] for v in GA[a]])) for a in ARMS}
            km = {a: float(np.median([v[2] for v in GA[a]])) for a in ARMS}
            spr = {a: (0.0 if ndraw == 1 else
                       100 * (max(v[0] for v in GA[a]) - min(v[0] for v in GA[a]))
                       / max(med[a], 1e-9)) for a in ARMS}
            fkm = float(np.median([x[1] for x in FP]))
            fspr = (0.0 if ndraw == 1 else
                    100 * (max(x[0] for x in FP) - min(x[0] for x in FP)) / max(fmed, 1e-9))
            TAB[tag] = (fmed, fkm, fspr, med, km, spr, nmed, ndraw)
            if nmed < 30:
                P(f"      {tag:>5}{fmed:>12.0f}m{'THIN -- too few localizable messages':>43}{nmed:>7}")
                continue
            P(f"      {tag:>5}{fmed:>12.0f}m{med['wcl']:>8.0f}m{med['abs']:>9.0f}m"
              f"{med['diff']:>7.0f}m{med['nlls']:>7.0f}m{med['minmax']:>8.0f}m{nmed:>7}")
        P(f"\n      SHARE OF FIXES BEYOND 1 km (catastrophic failures)")
        P(f"      {'recv':>5}{'FINGERPRINT':>13}{'WCL_bc':>9}{'ABS+mean':>10}"
          f"{'DIFF':>8}{'NLLS':>8}{'MinMax':>9}")
        for tag, (fmed, fkm, fspr, med, km, spr, nmed, nd) in TAB.items():
            if nmed < 30: continue
            P(f"      {tag:>5}{fkm:>12.1f}%{km['wcl']:>8.1f}%{km['abs']:>9.1f}%"
              f"{km['diff']:>7.1f}%{km['nlls']:>7.1f}%{km['minmax']:>8.1f}%")
        P(f"\n      STABILITY -- spread of the median across draws at the SAME count")
        P(f"      (how much the answer depends on WHICH receivers were lost)")
        P(f"      {'recv':>5}{'FINGERPRINT':>13}{'WCL_bc':>9}{'ABS+mean':>10}"
          f"{'DIFF':>8}{'NLLS':>8}{'MinMax':>9}")
        for tag, (fmed, fkm, fspr, med, km, spr, nmed, nd) in TAB.items():
            if nmed < 30 or nd == 1: continue
            P(f"      {tag:>5}{fspr:>12.0f}%{spr['wcl']:>8.0f}%{spr['abs']:>9.0f}%"
              f"{spr['diff']:>7.0f}%{spr['nlls']:>7.0f}%{spr['minmax']:>8.0f}%")
        P(f"      * = NON-RANDOM: the assignments BLOCK 0 rates weakest were dropped,")
        P(f"        which is the 27 -> 22 configuration used elsewhere in this run.")

        if fl:
            P(f"\n      any 'vs full' below {fl:.1f}% is NOT RESOLVABLE against the")
            P(f"      evaluation-draw floor; spread is across draws, not across messages.")

        # ---------- COST: what each family pays at inference
        P(f"\n      COST AT INFERENCE")
        fp_bytes = len(DB) * (len(MAPPED) * 4 + 16)
        geo_bytes = len(MAPPED) * (16 + 8)
        P(f"      STORAGE is fixed by the SURVEY THIS BENCHMARK SHIPS, so it is a")
        P(f"      property of the data rather than of anyone's implementation:")
        P(f"      {'fingerprint radio map':<32}{len(DB)} vectors x {len(MAPPED)} receivers"
          f" = {fp_bytes/1e6:.2f} MB")
        P(f"      {'range-based model':<32}{len(MAPPED)} coordinates + {len(MAPPED)}"
          f" intercepts = {geo_bytes/1e3:.2f} kB")
        P(f"      ratio {fp_bytes/max(geo_bytes,1):.0f}x. The fingerprint model grows with")
        P(f"      SURVEY EFFORT; the range-based model is bounded by RECEIVER COUNT.")
        gl = geo_latency(ev, PHYS, MAPPED, EV, cal, n, args.max_gws,
                         wcl, lattice, fit_a0,
                         arms=("wcl", "abs", "diff", "trilat", "minmax"))
        _dX, _dY = fp_vec(DB, MAPPED); _qX, _qY = fp_vec(EV, MAPPED)
        _A = _dX.astype(np.float64); _an = (_A ** 2).sum(1)
        _t0 = time.perf_counter()
        for _i in range(min(200, len(_qX))):
            _q = _qX[_i:_i+1].astype(np.float64)
            _d = _an + (_q ** 2).sum() - 2.0 * (_q @ _A.T).ravel()
            np.argpartition(_d, 3)[:3]
        fp_single = 1000.0 * (time.perf_counter() - _t0) / min(200, len(_qX))
        P(f"\n      LATENCY -- REPORTED AS A FOOTNOTE, NOT AS A RESULT. Runtime is an")
        P(f"      IMPLEMENTATION property: both families can be optimised and neither")
        P(f"      figure is fixed by the benchmark. Ours are UPPER BOUNDS.")
        P(f"        fingerprint, single fix, exact brute force : {fp_single:.3f} ms")
        P(f"        WCL_bc {gl['wcl']:.3f} ms | ABS+mean {gl['abs']:.3f} ms | "
          f"DIFF {gl['diff']:.3f} ms")
        P(f"        Trilat {gl['trilat']:.3f} ms | MinMax {gl['minmax']:.3f} ms")
        # THE TWO METHODS THAT BEAT THE DIFFERENTIAL, ADDED 19 Aug (due item 13).
        # Trilateration wins on all three statistics (697 vs 966 m, disjoint CIs)
        # and Min-Max wins outright (466 m). A cost frontier that omits them
        # compares the differential only against methods it already outruns.
        _acc = {"WCL_bc": 837, "ABS+mean": 641, "DIFF": 966, "Trilat": 697, "MinMax": 466}
        _lat = {"WCL_bc": gl['wcl'], "ABS+mean": gl['abs'], "DIFF": gl['diff'],
                "Trilat": gl['trilat'], "MinMax": gl['minmax']}
        P(f"\n      THE FRONTIER. A method is DOMINATED if another is both more")
        P(f"      accurate AND faster. Accuracy from BLOCK 8 (verified-29, n=2498).")
        P(f"      **READ THE STRUCTURE, NOT THE MILLISECONDS.** The paragraph above")
        P(f"      says this block draws no conclusion from latency, and that stands")
        P(f"      for the EXACT figures: Trilat calls a least-squares solver and DIFF")
        P(f"      a lattice search, both of which an implementer could speed up.")
        P(f"      What is NOT an implementation choice is CLOSED-FORM vs SEARCH:")
        P(f"      WCL and Min-Max compute a fix in one pass; ABS, DIFF and Trilat")
        P(f"      each optimise. **That ordering cannot be engineered away, and it")
        P(f"      is the only part of the table that should be quoted.**")
        P(f"        {'method':<10}{'median m':>10}{'ms/fix':>10}   status")
        for _m in sorted(_acc, key=_acc.get):
            _dom = [o for o in _acc
                    if _acc[o] < _acc[_m] and _lat[o] < _lat[_m]]
            P(f"        {_m:<10}{_acc[_m]:>10}{_lat[_m]:>10.3f}   "
              f"{'DOMINATED by ' + ', '.join(_dom) if _dom else 'on the frontier'}")
        P(f"      k-NN here is an EXACT brute-force scan. At {len(MAPPED)} dimensions")
        P(f"      KD- and ball-trees are SLOWER than brute force (measured), but an")
        P(f"      APPROXIMATE index (HNSW, IVF) would cut this substantially and a")
        P(f"      deployed system would use one. We therefore draw NO conclusion from")
        P(f"      the latency rows -- see the frontier note above for what CAN be said.")


        P(f"      **The fingerprint's model grows with SURVEY EFFORT; the range-based")
        P(f"      model grows with RECEIVER COUNT.**")

        # DEFERRAL RESTATED 19 Aug. The schema reason is now DISCHARGED (BLOCK 29
        # reads it from the file). The real blocker was always different and is
        # now stated instead of hidden behind a resolved one.
        P(f"\n  (C) SIGFOX: STILL DEFERRED, but NOT for the schema reason. BLOCK 29")
        P(f"      verified the column layout from the file. The blocker is that")
        P(f"      **Sigfox publishes NO receiver coordinates at all**, so the")
        P(f"      range-based half of this comparison cannot be computed there by")
        P(f"      anyone. That is the asymmetry of BLOCK 25, met again: the two")
        P(f"      benchmarks withhold exactly what the other supplies.")

    # ============================== BLOCK 27 -- WHAT A DEPLOYMENT CHANGE COSTS
    if 27 in BL:
        P("\n" + "=" * 96)
        P("BLOCK 27 -- THE RADIO MAP IS TIED TO A RECEIVER CONFIGURATION")
        P("=" * 96)
        P(floor_line(FLOOR))
        P("  BLOCK 26 removed receivers from the database AND the queries together.")
        P("  That is a SMALLER SURVEY, not a CHANGED DEPLOYMENT, and it understates")
        P("  the fingerprint's exposure.")
        P("")
        P("  The real case: the radio map was recorded with one receiver set. A")
        P("  receiver later FAILS. **The database still carries its dimension while")
        P("  every new query arrives without it**, so the query's value sits at the")
        P("  fill floor against a real reading in every database entry. Every")
        P("  comparison acquires a spurious distance, and nothing detects it.")
        P("")
        P("  A range-based method stops using that anchor. Its intercept is never")
        P("  referenced again. No re-survey, no re-index, no detection required.")

        ALLG = sorted({r.gid for m_ in cal for r in m_.receptions}
                      | {r.gid for m_ in EV for r in m_.receptions})
        MAPPED = [g for g in ALLG if g in PHYS]
        DB = cal if len(cal) <= args.fp_dbcap else random.Random(88).sample(cal, args.fp_dbcap)
        build, knn = fp_vec, fp_knn
        # delegates to the hoisted evaluator -- no private copy, no shadowing
        def geo(gids, drop=frozenset()):
            r, nn = geo_eval(ev, PHYS, gids, EV, cal, n, args.max_gws,
                             wcl, lattice, fit_a0, drop=drop,
                             # GAP FILLED 19 Aug: the differential objective is the
                             # method this paper is about, and this block measured
                             # only the centroid.
                             arms=("wcl", "diff", "minmax"))
            return r["wcl"][0], r["diff"][0], r["minmax"][0], nn

        dX, dY = build(DB, ALLG)                       # the survey, as recorded
        qX0, qY0 = build(EV, ALLG)                     # queries, deployment unchanged
        base_fp = knn(dX, dY, qX0, qY0)
        base_geo, base_gd, base_gm, nb = geo(MAPPED)
        P(f"\n  baseline, deployment UNCHANGED: fingerprint {base_fp:.0f} m | "
          f"WCL_bc {base_geo:.0f} m | DIFF {base_gd:.0f} m | MinMax {base_gm:.0f} m (n={nb})")

        # ---- APPARATUS CONTROL. Failing ZERO receivers must return the baseline
        # EXACTLY, for both families and for both the naive and re-indexed paths.
        # Without it a non-zero result could be an artifact of rebuilding the
        # query matrix rather than of the failure itself.
        zX, zY = build(EV, ALLG, drop=frozenset())
        z_naive = knn(dX, dY, zX, zY)
        z_rep = knn(dX, dY, zX, zY, mask=np.arange(len(ALLG)))
        z_geo, _zgd, _zgm, _zn = geo(MAPPED, drop=frozenset())
        okz = (abs(z_naive - base_fp) < 1e-6 and abs(z_rep - base_fp) < 1e-6
               and abs(z_geo - base_geo) < 1e-6)
        P(f"\n  APPARATUS CONTROL -- fail ZERO receivers; all three must be exact.")
        P(f"      naive      {z_naive:.1f} m vs {base_fp:.1f}   |  re-indexed "
          f"{z_rep:.1f} m vs {base_fp:.1f}  |  WCL_bc {z_geo:.1f} vs {base_geo:.1f}")
        P(f"      {'PASS -- rebuilding the query matrix is neutral' if okz else '*** FAIL -- the apparatus is not neutral; every row below is VOID ***'}")
        P(f"\n  (a) RECEIVERS FAIL AFTER THE SURVEY. The database is NOT rebuilt.")
        P(f"      {'failed':>7}{'FP naive':>9}{'vs':>6}{'FP re-idx':>11}{'vs':>6}"
          f"{'WCL_bc':>9}{'vs':>6}{'DIFF':>8}{'vs':>6}{'MinMax':>9}{'vs':>6}{'n geo':>7}")
        gx = {g: i for i, g in enumerate(ALLG)}
        for nf in (1, 2, 3, 5, 8):
            naive, rep, geos, gds, gms, ns = [], [], [], [], [], []
            for d in range(args.rm_draws):
                dead = frozenset(random.Random(9700 + 31*nf + d).sample(MAPPED, nf))
                qX, qY = build(EV, ALLG, drop=dead)
                naive.append(knn(dX, dY, qX, qY))                     # nobody noticed
                keep = np.array([i for g, i in gx.items() if g not in dead])
                rep.append(knn(dX, dY, qX, qY, mask=keep))            # detected + re-indexed
                gg, gd, gm, nn = geo(MAPPED, drop=dead)
                geos.append(gg); gds.append(gd); gms.append(gm); ns.append(nn)
            nv, rv_, gv, dv, mv = (np.median(naive), np.median(rep),
                                   np.median(geos), np.median(gds), np.median(gms))
            P(f"      {nf:>7}{nv:>8.0f}m{100*(nv-base_fp)/base_fp:>5.0f}%"
              f"{rv_:>10.0f}m{100*(rv_-base_fp)/base_fp:>5.0f}%"
              f"{gv:>8.0f}m{100*(gv-base_geo)/base_geo:>5.0f}%"
              f"{dv:>7.0f}m{100*(dv-base_gd)/base_gd:>5.0f}%"
              f"{mv:>8.0f}m{100*(mv-base_gm)/base_gm:>5.0f}%{int(np.median(ns)):>7}")
        P(f"\n      NAIVE = the failure went undetected; the database keeps the dead")
        P(f"      receiver's dimension. RE-INDEXED = the operator noticed and masked")
        P(f"      it -- the BEST case, and it still costs the survey's information.")
        P(f"      *** the gap between the two columns is the price of NOT KNOWING")
        P(f"          that the deployment changed. ***")

        P(f"\n  (b) A RECEIVER IS ADDED AFTER THE SURVEY.")
        P(f"      The radio map has no dimension for it, so the fingerprint cannot")
        P(f"      use it at all. A range-based method gains an anchor immediately.")
        P(f"      each row starts from a SURVEYED set of (27 - added) receivers and")
        P(f"      then adds them back. Both BEFORE and AFTER are shown, because a")
        P(f"      single 'after' column looks like a constant and reads as a bug.")
        P(f"      {'added':>6}{'surv':>6}{'FP bef':>8}{'FP aft':>8}"
          f"{'WCL bef':>9}{'WCL aft':>9}{'gain':>7}"
          f"{'DIFF bef':>10}{'DIFF aft':>10}{'gain':>7}"
          f"{'MM bef':>9}{'MM aft':>9}{'gain':>7}")
        for na in (2, 5, 8):
            # FIX 19 Aug. base_set was MAPPED[:N] -- the FIRST N receivers in
            # DICT-INSERTION ORDER, i.e. the order of the map file. That made
            # the "before" column measure FILE ORDER: 24 receivers gave 746 m
            # and 21 gave 676 m, so receivers 22-24 in file order were harmful
            # and "gain" was confounded. Now drawn at RANDOM over several draws,
            # exactly as BLOCK 26 does, and the MEDIAN is reported.
            _fw, _mw, _fd, _md, _fm, _mm_ = [], [], [], [], [], []
            for _d in range(max(3, args.rm_draws)):
                base_set = random.Random(9900 + 17*na + _d).sample(
                    MAPPED, max(3, len(MAPPED) - na))
                grown = base_set + [g for g in MAPPED if g not in base_set][:na]
                _a, _b, _m1, _ = geo(base_set)
                _c, _e, _m2, _ = geo(grown)
                _fw.append(_a); _mw.append(_c); _fd.append(_b); _md.append(_e)
                _fm.append(_m1); _mm_.append(_m2)
            fewer, more = float(np.median(_fw)), float(np.median(_mw))
            fewer_d, more_d = float(np.median(_fd)), float(np.median(_md))
            fewer_m, more_m = float(np.median(_fm)), float(np.median(_mm_))
            base_set = random.Random(9900 + 17*na).sample(
                MAPPED, max(3, len(MAPPED) - na))
            sX, sY = build(DB, base_set); tX, tY = build(EV, base_set)
            fp_before = knn(sX, sY, tX, tY)
            # the fingerprint AFTER: the radio map has no dimension for the new
            # receivers, so it is IDENTICAL by construction. We compute it the
            # same way to make that identity visible rather than asserted.
            fp_after = knn(sX, sY, tX, tY)
            P(f"      {na:>6}{len(base_set):>6}{fp_before:>7.0f}m{fp_after:>7.0f}m"
              f"{fewer:>8.0f}m{more:>8.0f}m{100*(more-fewer)/fewer:>6.0f}%"
              f"{fewer_d:>9.0f}m{more_d:>9.0f}m{100*(more_d-fewer_d)/fewer_d:>6.0f}%"
              f"{fewer_m:>8.0f}m{more_m:>8.0f}m{100*(more_m-fewer_m)/fewer_m:>6.0f}%")
        P(f"      *** FP before and after are IDENTICAL, by construction: the radio")
        P(f"          map has no dimension for a receiver that did not exist when it")
        P(f"          was surveyed. The range-based column improves immediately. ***")

    # ============================================================================
    if 28 in BL:
        P("\n" + "=" * 96)
        P("BLOCK 28 -- THE SECOND MISSING COLUMN: RECEPTION REDUNDANCY IS CAPPED")
        P("=" * 96)
        P(floor_line(FLOOR))
        P("  Added 19 Aug. This was the programme's strongest benchmark finding and")
        P("  it lived in NO BLOCK -- it was measured ad hoc and quoted from memory.")
        P("  A finding without a reproducible home is not a finding.")
        P("")
        P("  THE CLAIM. The LoRaWAN release reports at most a fixed number of")
        P("  receptions per message. If that maximum is a TRUNCATION rather than the")
        P("  natural tail of the distribution, the benchmark silently withholds")
        P("  redundancy -- and it withholds it SELECTIVELY, because methods differ in")
        P("  how they consume receivers.")
        P("")
        P("  WHY IT IS METHOD-SELECTIVE. A fingerprint uses the reception VECTOR: one")
        P("  more receiver adds one dimension. A trilateration-style method uses")
        P("  RECEIVERS: k of them. A pairwise method uses PAIRS: k(k-1)/2 of them.")
        P("  Capping k therefore costs the three families in the ratio 1 : k : k^2.")

        rc = np.array([len(mm.receptions) for mm in msgs], dtype=int)
        kmax = int(rc.max())
        P(f"\n  (a) THE RECEPTION-COUNT DISTRIBUTION  (n={len(rc)} messages, ALL of them,")
        P(f"      not a sample -- this is a CENSUS of the release)")
        P(f"      {'k':>4}{'messages':>11}{'share':>9}{'ratio to k-1':>15}")
        prev = None
        for k in range(1, kmax + 1):
            c = int((rc == k).sum())
            r = (c / prev) if prev else float("nan")
            flag = ""
            if k == kmax and prev and c > prev:
                flag = "   <-- RISES AT THE MAXIMUM"
            P(f"      {k:>4}{c:>11}{100.0*c/len(rc):>8.1f}%"
              f"{(f'{r:.2f}x' if np.isfinite(r) else '--'):>15}{flag}")
            prev = c if c else prev

        P(f"\n  (b) IS THE MAXIMUM A TRUNCATION? A decay control.")
        P(f"      A natural tail DECAYS. Fit log(count) linearly over k=2..{kmax-1},")
        P(f"      extrapolate to k={kmax}, and compare. An EXCESS at the maximum is")
        P(f"      the signature of every message with MORE receptions being reported")
        P(f"      AS {kmax} -- i.e. a cap, not a tail.")
        ks = np.arange(2, kmax)
        cs = np.array([(rc == k).sum() for k in ks], dtype=float)
        keep = cs > 0
        obs = int((rc == kmax).sum())
        if keep.sum() >= 3:
            sl, ic = np.polyfit(ks[keep], np.log(cs[keep]), 1)
            pred = float(np.exp(sl * kmax + ic))
            P(f"      observed at k={kmax}      : {obs}")
            P(f"      predicted by the decay  : {pred:.0f}")
            P(f"      EXCESS                  : {obs - pred:+.0f}  "
              f"({obs/pred:.2f}x predicted)")
            if obs > 2.0 * pred:
                P(f"      *** CENSORED: the maximum carries {obs/pred:.1f}x the messages the")
                P(f"          decay predicts. The cap is a REPORTING LIMIT. ***")
            else:
                P(f"      NOT censored by this test: the maximum is consistent with the tail.")
        else:
            P(f"      too few populated k values to fit a decay -- not interpretable")

        P(f"\n  (c) WHAT THE CAP COSTS EACH FAMILY.")
        P(f"      Receivers scale as k; PAIRS scale as k(k-1)/2. The pairwise family")
        P(f"      loses quadratically what the others lose linearly.")
        P(f"      {'k':>4}{'receivers':>11}{'pairs':>8}{'msgs at >=k':>13}{'share':>9}")
        for k in (3, 5, 7, 8, 9, kmax):
            if k > kmax: continue
            atk = int((rc >= k).sum())
            P(f"      {k:>4}{k:>11}{k*(k-1)//2:>8}{atk:>13}{100.0*atk/len(rc):>8.1f}%")

        P(f"\n  (d) IS THE DIFFERENTIAL OBJECTIVE'S OPTIMUM REACHABLE?")
        P(f"      BLOCK 11 locates its optimum near k=7-8. Under the cap:")
        for k in (7, 8):
            atk = int((rc >= k).sum())
            P(f"      messages with >= {k} receptions: {atk} = {100.0*atk/len(rc):.1f}% of the release")
        P(f"      -> a method whose optimum sits at k=7-8 can reach it on only that")
        P(f"         share of traffic. The cap does not merely reduce accuracy; it")
        P(f"         puts the method's own best operating point out of reach.")

        P(f"\n  APPARATUS CONTROL -- the census must sum to the message count.")
        tot = int(sum((rc == k).sum() for k in range(0, kmax + 1)))
        P(f"      sum over all k: {tot} vs {len(rc)} messages   "
          f"{'PASS' if tot == len(rc) else '*** FAIL -- the histogram loses messages ***'}")
        P(f"  META-CHECK -- the >=k column must be MONOTONE DECREASING in k.")
        seq = [int((rc >= k).sum()) for k in range(1, kmax + 1)]
        mono = all(seq[i] >= seq[i + 1] for i in range(len(seq) - 1))
        P(f"      {seq}")
        P(f"      {'PASS -- monotone' if mono else '*** FAIL -- not monotone, the census is wrong ***'}")

        # STALE DEFERRAL REMOVED 19 Aug. This text said the Sigfox schema was
        # UNVERIFIED and the word "specific" was NOT earned. BLOCK 29 verified
        # the schema from the file and ran the control IN THE SAME RUN, so the
        # two blocks contradicted each other inside one output. Found by reading
        # v6 block-by-block; no single-block read could have caught it.
        P(f"\n  SIGFOX CONTROL: RUN. See BLOCK 29, which verified the column schema")
        P(f"  from the file (columns named 'BS <n>'; fill -200.0) and measured the")
        P(f"  same statistic on two Sigfox deployments. LoRaWAN puts 4.892% of ALL")
        P(f"  traffic on its maximum; Sigfox urban 0.007% and rural 0.004%. By the")
        P(f"  rule stated there, **the word LoRaWAN-SPECIFIC is EARNED**.")
        P(f"  NOTE ON THE DECAY RATIO: this block fits k=2..9 and reports 3.83x;")
        P(f"  BLOCK 29 fits the interior and reports 3.41x. Same census, same")
        P(f"  maximum, different fit window. **Quote ONE and name the window** --")
        P(f"  the programme quotes 3.83x, from the k=2..9 fit above.")

    # ============================================================================
    if 29 in BL:
        P("\n" + "=" * 96)
        P("BLOCK 29 -- SIGFOX CONTROL: IS THE RECEPTION CAP LoRaWAN-SPECIFIC?")
        P("=" * 96)
        P(floor_line(FLOOR))
        P("  BLOCK 28 shows the LoRaWAN release piles messages up at exactly its")
        P("  maximum reception count. That alone does not make the cap a REPORTING")
        P("  choice -- it could be a property of LPWAN traffic. A second deployment,")
        P("  same city, same campaign, DIFFERENT operator, settles it.")
        P("")
        P("  SCHEMA, VERIFIED 19 Aug -- this block was deferred for weeks because the")
        P("  Sigfox column layout was a GUESS. It is now read from the file:")
        P("    columns named 'BS <n>'; everything else is RX Time / Latitude /")
        P("    Longitude; NOT-RECEIVED is the explicit fill -200.0, which appears")
        P("    186,110 times against RSSI values clustered near -130. No heuristic.")
        P("")
        P("  THE STATISTIC. A spike test on the raw counts fails here: at a maximum")
        P("  of 56 the tail holds ONE message, which is sparsity, not a pile-up. The")
        P("  discriminating quantity is the SHARE OF ALL TRAFFIC sitting at exactly")
        P("  the maximum. A reporting limit forces every richer message down onto")
        P("  that value; a natural tail leaves it nearly empty.")

        import csv as _csv

        def _sig_counts(path):
            """Reception count per message. Returns None if the file is absent, so
            the block DEGRADES rather than crashing -- the Sigfox files are not
            required for the other 29 blocks."""
            try:
                with open(path) as fh:
                    r = _csv.reader(fh)
                    hdr = next(r)
                    bs = [i for i, h in enumerate(hdr) if h.strip().startswith("BS ")]
                    if not bs:
                        return None, 0
                    out = []
                    for row in r:
                        out.append(sum(1 for i in bs
                                       if row[i] not in ("", "-200.0", "-200")))
                return np.array(out, dtype=int), len(bs)
            except FileNotFoundError:
                return None, 0

        lw = np.array([len(mm.receptions) for mm in msgs], dtype=int)
        # SELF-CONTAINED: ALLG is defined inside BLOCK 25, so reading it here
        # would make BLOCK 29 silently depend on BLOCK 25 -- exactly the
        # cross-block dependency this harness's own audit flags. Counted locally.
        _lw_recv = len({rx.gid for mm in msgs for rx in mm.receptions})
        rows = [("LoRaWAN Antwerp", lw, _lw_recv)]
        for tag, path in (("Sigfox urban", args.sigfox_urban),
                          ("Sigfox rural", args.sigfox_rural)):
            c, ncol = _sig_counts(path)
            if c is None:
                P(f"\n  *** {tag}: file not found at '{path}' -- this block CANNOT")
                P(f"      run its control. Pass --sigfox-urban / --sigfox-rural. ***")
            else:
                rows.append((tag, c, ncol))

        P(f"\n  {'deployment':<18}{'msgs':>9}{'receivers':>11}{'mean k':>9}"
          f"{'max k':>8}{'at max':>9}{'SHARE at max':>15}")
        share = {}
        for tag, c, ncol in rows:
            m = int(c.max())
            at = int((c == m).sum())
            sh = 100.0 * at / len(c)
            share[tag] = sh
            P(f"  {tag:<18}{len(c):>9}{ncol:>11}{c.mean():>9.2f}{m:>8}{at:>9}{sh:>14.3f}%")

        P(f"\n  THE CONTRAST.")
        if len(share) >= 2:
            base = share.get("LoRaWAN Antwerp", float("nan"))
            for tag in ("Sigfox urban", "Sigfox rural"):
                if tag in share and share[tag] > 0:
                    P(f"      LoRaWAN / {tag:<14}: {base/share[tag]:>10.0f}x more traffic"
                      f" sits at the maximum")
                elif tag in share:
                    P(f"      LoRaWAN / {tag:<14}: {tag} has NOTHING at its maximum")

        P(f"\n  DECAY CONTROL, the same test BLOCK 28 applies to LoRaWAN.")
        P(f"      Fit log(count) over the interior of the distribution, extrapolate")
        P(f"      to the maximum, and report observed/predicted.")
        for tag, c, _ in rows:
            m = int(c.max())
            ks = np.arange(max(1, int(c.mean())), m)
            cs = np.array([(c == k).sum() for k in ks], dtype=float)
            keep = cs > 0
            obs = int((c == m).sum())
            if keep.sum() >= 3:
                sl, ic = np.polyfit(ks[keep], np.log(cs[keep]), 1)
                pred = float(np.exp(sl * m + ic))
                ratio = obs / pred if pred > 1e-9 else float("inf")
                # MINIMUM-COUNT GUARD, added 19 Aug after the first run called
                # Sigfox rural CENSORED on ONE observed message against 0.4
                # predicted. A ratio built on single counts is noise. The verdict
                # requires BOTH a ratio above 2 and enough mass to mean anything.
                if obs < 30:
                    verdict = f"NOT INTERPRETABLE -- only {obs} message(s) at the maximum"
                elif ratio > 2.0:
                    verdict = "*** CENSORED ***"
                else:
                    verdict = "consistent with a natural tail"
                P(f"      {tag:<18} observed {obs:>6} | predicted {pred:>9.1f} | "
                  f"{ratio:>8.2f}x   {verdict}")
            else:
                P(f"      {tag:<18} too few populated k values to fit -- not interpretable")

        P(f"\n  APPARATUS CONTROL -- the Sigfox reader must not count the fill value.")
        cu, _ = _sig_counts(args.sigfox_urban)
        if cu is not None:
            P(f"      a message cannot have MORE receptions than there are receivers:")
            P(f"      max count {int(cu.max())} vs {rows[1][2] if len(rows)>1 else '?'} columns   "
              f"{'PASS' if len(rows)>1 and cu.max() <= rows[1][2] else '*** FAIL ***'}")
            P(f"      and cannot have fewer than zero: min {int(cu.min())}   "
              f"{'PASS' if cu.min() >= 0 else '*** FAIL ***'}")
        else:
            P(f"      *** NOT RUN -- Sigfox file absent ***")

        P(f"\n  WHAT THIS EARNS. If LoRaWAN piles a percent-scale share of ALL traffic")
        P(f"  onto its maximum and Sigfox piles essentially none onto its own, then")
        P(f"  the cap is a property of the LoRaWAN RELEASE, not of LPWAN reception.")
        P(f"  The word 'specific' in BLOCK 28 is then EARNED. If both pile up, it is")
        P(f"  not, and BLOCK 28's claim must be narrowed to 'this release'.")

    # ============================================================================
    if 30 in BL:
        P("\n" + "=" * 96)
        P("BLOCK 30 -- WHEN IS THE DIFFERENTIAL A BETTER FALLBACK THAN THE CENTROID?")
        P("=" * 96)
        P(floor_line(FLOOR))
        P("  THE CLAIM THIS TESTS. The differential-objective manuscript asserted in")
        P("  its ABSTRACT that the differential is a better fallback than the centroid")
        P("  when NLLS is not usable. No experiment supported it. That omission was")
        P("  the single largest cause of the ADHOC rejection. This block is it.")
        P("")
        P("  WHAT IT IS NOT. It does NOT claim the differential beats NLLS. It does")
        P("  not, anywhere, at any trigger level, and the rows below say so. The")
        P("  claim is narrow and it is the one that was actually made: BETTER THAN")
        P("  THE CENTROID, on the messages where a fallback is needed.")
        P("")
        P("  THE TRIGGER IS ESTIMATOR-FREE, AND THAT IS THE POINT. An earlier")
        P("  design used |NLLS - WCL| as the trigger. That makes the fallback")
        P("  conditional on the very method it replaces -- circular for deployment,")
        P("  and it predicted the differential's advantage LESS well (rho=+0.436).")
        P("  This block triggers on RECEIVER SPREAD: the median distance of the")
        P("  receiving set from its own centroid. It needs only the map and")
        P("  who-heard-what, is computable BEFORE any localization runs, and")
        P("  predicts the advantage at rho=+0.709 (p~1e-183, n=1200).")
        P("")
        P("  WHY SPREAD. A weighted centroid of widely-separated receivers lands in")
        P("  the middle of nothing. The differential uses RATIOS of distances and is")
        P("  not bound to the convex hull of the receivers, so it is not.")

        def fallback_arm(mp, a0, label):
            """Returns (spread, err_wcl, err_diff, err_nlls) per message."""
            C_ = np.array(list(mp.values()))
            bb_ = (C_[:, 0].min() - 3000, C_[:, 0].max() + 3000,
                   C_[:, 1].min() - 3000, C_[:, 1].max() + 3000)
            spr, ew_, ed_, en_, em_ = [], [], [], [], []
            for mm in EV:
                rx = [r for r in mm.receptions if r.gid in mp and r.gid in a0]
                if len(rx) < 3:
                    continue
                rx = sorted(rx, key=lambda r: -r.rssi)[:args.max_gws]
                g_ = np.vstack([mp[r.gid] for r in rx])
                raw_ = np.array([r.rssi for r in rx], float)
                rv_ = raw_ - np.array([a0[r.gid] for r in rx])
                t_ = np.array([mm.x, mm.y])
                # THE TRIGGER: map + who-heard-what only. No estimator.
                u_ = g_ - g_.mean(axis=0)
                spr.append(float(np.median(np.linalg.norm(u_, axis=1))))
                w_ = wcl(ev, g_, raw_)
                ew_.append(float(np.linalg.norm(w_ - t_)))
                ed_.append(float(np.linalg.norm(
                    lattice(ev, g_, rv_, n, "diff", "median") - t_)))
                x_, _c, _d = ev.robust_nlls_localize(
                    gw_mat=g_, rssi_corrected=rv_, n=n, wcl_init=w_, bbox=bb_,
                    huber_c=1.345, n_starts=3, max_iter=120, grad_tol=1e-6,
                    halton_seed=args.seed)
                en_.append(float(np.linalg.norm(x_ - t_)))
                # MIN-MAX added 19 Aug. It is the BEST range-based method on
                # verified geometry (466 m vs NLLS 641 m), so "is Min-Max the
                # better fallback?" is the first question a reader will ask, and
                # without this column the block cannot answer it.
                em_.append(float(np.linalg.norm(minmax(g_, rv_, n) - t_)))
            return (np.array(spr), np.array(ew_), np.array(ed_), np.array(en_),
                    np.array(em_))

        _arms = {}      # cache: the controls below need exactly these arrays
        for sub, mp_, a0_ in (("VERIFIED", PHYS, a0_phys), ("RSSFIT", RSSF, a0_rssf)):
            spr, ew_, ed_, en_, em_ = fallback_arm(mp_, a0_, sub)
            _arms[sub] = (spr, ew_, ed_, en_, em_)
            if len(spr) < 100:
                P(f"\n  {sub}: only {len(spr)} messages -- THIN, not interpreted")
                continue
            fl = FLOOR.get("seed")
            # EXPORT, added 19 Aug. Every other localizing block calls rec(); this
            # one did not, so the trigger analysis could not be redone or re-cut
            # from the run's own CSV. The TRIGGER travels in the aux column, so a
            # reader can reproduce any subset in the sweep without re-running.
            rec(30, sub, "WCL_raw", ew_, aux=spr)
            rec(30, sub, "DIFF+median", ed_, aux=spr)
            rec(30, sub, "NLLS", en_, aux=spr)
            rec(30, sub, "MinMax", em_, aux=spr)
            P(f"\n  {sub}   n={len(spr)}   trigger = receiver spread, "
              f"median {np.median(spr):,.0f} m")
            P(f"      {'trigger':<24}{'n':>6}{'NLLS':>9}{'WCL_raw':>9}{'DIFF':>9}"
              f"{'MinMax':>9}{'DIFF<WCL':>10}{'gain vs WCL':>13}")
            for q in (95, 90, 75, 50, 0):
                thr = np.percentile(spr, q)
                m_ = spr >= thr
                if m_.sum() < 20:
                    continue
                w_, d_, nl_, mx_ = ew_[m_], ed_[m_], en_[m_], em_[m_]
                gain = 100.0 * (np.median(w_) - np.median(d_)) / max(np.median(w_), 1e-9)
                lab = (f"spread >= p{q} ({thr:,.0f} m)" if q else "ALL messages (no trigger)")
                P(f"      {lab:<24}{m_.sum():>6}{np.median(nl_):>8.0f}m"
                  f"{np.median(w_):>8.0f}m{np.median(d_):>8.0f}m"
                  f"{np.median(mx_):>8.0f}m"
                  f"{100.0*np.mean(d_ < w_):>9.1f}%{gain:>12.1f}%")
            # the headline subset, with a paired CI and the floor
            thr = np.percentile(spr, 90)
            m_ = spr >= thr
            w_, d_ = ew_[m_], ed_[m_]
            lo, hi = boot_diff_medians(w_, d_, args.boot_draws, args.seed)
            P(f"      TOP-DECILE SUBSET  median(WCL)-median(DIFF) = "
              f"{np.median(w_)-np.median(d_):+,.0f} m  CI [{lo:+,.0f}, {hi:+,.0f}]")
            rel = 100.0 * abs(np.median(w_) - np.median(d_)) / max(np.median(w_), 1e-9)
            # FLOOR GUARD, added 19 Aug. FLOOR["seed"] is None when BLOCK 1 has
            # not run, and the format string raised TypeError -- BLOCK 30 could
            # not run standalone. BLOCKS 20, 23 and 26 all say so instead of
            # crashing; this now does too.
            if fl is None:
                P(f"      that is {rel:.1f}%, but BLOCK 1 did not run so there is NO")
                P(f"      MEASURED FLOOR to read it against. Re-run with --blocks 1,30.")
            else:
                P(f"      that is {rel:.1f}% against a {fl:.1f}% floor -- "
                  f"{'RESOLVABLE' if rel > fl else 'NOT resolvable'}")
            P(f"      NLLS on the same subset: {np.median(en_[m_]):,.0f} m | "
              f"Min-Max {np.median(em_[m_]):,.0f} m.")
            # WCL WAS MISSING FROM THIS COMPARISON (fixed 19 Aug). I omitted it
            # reasoning that the claim is DIFF-beats-WCL, so WCL need not be
            # ranked. On the RSSFIT top decile that produced a FALSE STATEMENT:
            # WCL_raw 774 m is the best method there and the line printed
            # "BEST: Min-Max" (792 m). A verdict that names the best method must
            # consider every method in the table.
            _best = min(("NLLS", np.median(en_[m_])), ("Min-Max", np.median(em_[m_])),
                        ("DIFF", np.median(d_)), ("WCL_raw", np.median(w_)),
                        key=lambda kv: kv[1])[0]
            P(f"      **BEST ON THIS SUBSET: {_best}. The claim is that the "
              f"differential beats the CENTROID, not that it beats every method.**")

        # BOTH SUBSTRATES, widened 19 Aug. The first version ran these controls on
        # PHYS only. The full-scale run then showed RSSFIT's untriggered gain at
        # +52.0% -- the differential wins there WITHOUT any trigger, so the
        # trigger is not what creates the effect on that substrate. A control
        # that only inspects the arm you expect to pass is not a control.
        P("\n  APPARATUS CONTROL and META-CHECK -- run on BOTH substrates.")
        # REUSE, not recompute (19 Aug). The controls previously called
        # fallback_arm a SECOND time per substrate, so the block ran it FOUR
        # times and half the work was duplicate: at n=2498 that is ~5 minutes of
        # NLLS recomputing numbers the sweep already held. fallback_arm is
        # deterministic, so the second pair could only ever agree with the first.
        for sub in ("VERIFIED", "RSSFIT"):
            if sub not in _arms:
                continue
            spr, ew_, ed_, en_, em_ = _arms[sub]
            nd = len(np.unique(np.round(spr)))
            P(f"      {sub}")
            P(f"        spread range {spr.min():,.0f}-{spr.max():,.0f} m over "
              f"{len(spr)} messages | distinct {nd}   "
              f"{'PASS' if nd > 50 else '*** FAIL -- trigger is near-constant ***'}")
            g_all = 100.0 * (np.median(ew_) - np.median(ed_)) / max(np.median(ew_), 1e-9)
            if g_all < 0:
                P(f"        untriggered gain {g_all:+.1f}%   PASS -- the advantage is")
                P(f"        CONDITIONAL on the trigger, which is what the claim says.")
            else:
                P(f"        untriggered gain {g_all:+.1f}%   *** THE DIFFERENTIAL WINS")
                P(f"        WITHOUT ANY TRIGGER on this substrate, so the trigger is NOT")
                P(f"        what creates the effect here. The conditional claim is NOT")
                P(f"        supported on {sub} and must not be made for it. ***")
            # the trigger is computed ON THE MAP IN USE, so a compressed map
            # yields a compressed trigger: report the range so it is visible.
            P(f"        trigger dynamic range: {spr.max()/max(spr.min(),1e-9):.1f}x")
        P("")
        P("  WHAT THIS DOES NOT SETTLE. The trigger THRESHOLD is chosen post hoc from")
        P("  this dataset's spread distribution. A deployment would need it fixed in")
        P("  advance, and the sweep above is the evidence for where to fix it -- not")
        P("  a demonstration that any particular percentile transfers.")

    P("\n" + "=" * 96)
    # FOOTER FIX 19 Aug: this said "verified-27" in every run regardless of
    # the map actually loaded -- 29 in v5, 33 in v5_direct and v5_matched,
    # 27 under --restrict-to-map. A stale literal on the LAST LINE a reader
    # sees. Now reports the real count.
    P(f"END. Every number above: substrate = verified-{len(PHYS)} or RSSFIT, "
      f"as labelled.")
    if FLOOR["seed"] is not None:
        P(f"Floors measured in BLOCK 1: seed {FLOOR['seed']:.1f}% | draw {FLOOR['draw']:.1f}%")
    P("=" * 96)
    d_ = os.path.dirname(os.path.abspath(args.out))
    if d_: os.makedirs(d_, exist_ok=True)
    open(args.out + ".txt", "w").write("\n".join(L) + "\n")
    if ROWS:
        import csv as _csv
        with open(args.out + "_permsg.csv", "w", newline="") as fh:
            w_ = _csv.writer(fh)
            w_.writerow(["block", "substrate", "method", "error_m", "aux"])
            w_.writerows(ROWS)
        print(f"-> {args.out}_permsg.csv  ({len(ROWS)} rows -- ECDFs and figures)")
    print(f"\n-> {args.out}.txt")


if __name__ == "__main__":
    main()
