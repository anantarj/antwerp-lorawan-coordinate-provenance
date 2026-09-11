---
title: "Published, Unjoined: Coordinate Provenance and Reception Support in a Public LPWAN Localization Benchmark"
author: ""
date: ""
header-includes:
  - '\usepackage{needspace}'
  - '\usepackage{float}'
  - '\floatplacement{figure}{H}'
  - '\usepackage{fancyhdr}'
  - '\pagestyle{fancy}'
  - '\fancyhf{}'
  - '\fancyhead[L]{\small Paper A | Coordinate provenance and reception support}'
  - '\fancyfoot[C]{\thepage}'
  - '\setlength{\headheight}{14pt}'
  - '\setlength{\emergencystretch}{3em}'
  - '\usepackage{xurl}'
  - '\urlstyle{same}'
---

## Abstract {-}

Receiver-coordinate provenance is a prerequisite for reproducible geometric localization on public RSSI benchmarks. We provide an executable identity join for the LoRaWAN Antwerp v1.3 release, linking all 44 active tabular receiver columns to message-level gateway identifiers without transmitter coordinates or localization outcomes. Thirty-nine identifiers have catalogue coordinates; a frozen 33-receiver roster is used for the primary evaluation. The accompanying resource contains the complete crosswalk, coordinate assignments, ordered populations, code and result records. On 2,495 fixed messages, substituting one specified RSSI-fitted assignment for the metadata-derived coordinates increases raw weighted-centroid median error from 480.09 m to 3,619.22 m (7.54-fold). The substitution is a constrained case study: its median catalogue-relative receiver discrepancy is 5.24 km, 26 fitted receivers lie on search-box boundaries, and eight catalogue positions lie outside their corresponding boxes. The localization contrast persists under the tested paired, spatial and day-block bootstrap sensitivity intervals and after excluding the extreme BS71 catalogue entry. Both CSV and JSON have a ten-reception endpoint with 2,709 records at the maximum; this does not identify its cause or the cost of unobserved receptions. Matched geographic and receiver-removal controls separate calibration, availability and population effects, while temporal and solver diagnostics retain method- and metric-specific interpretations. The contribution is a reusable benchmark resource and an identified coordinate-substitution vulnerability, not a new estimator or a typical or unavoidable penalty for missing coordinates.

**Keywords:** LPWAN; LoRaWAN; RSSI localization; benchmark audit; coordinate provenance; reproducibility

## Highlights {-}

- Reception metadata identify 44 active receivers; 39 have catalogue coordinates.
- On matched records, coordinate substitution increases centroid error 7.54-fold.
- Both released formats have a ten-reception maximum, with 2,709 records at ten.
- Availability and calibration controls refine interpretation of benchmark accuracy.

# Introduction

A public localization benchmark contains more than RSSI measurements and transmitter positions. Receiver identities, coordinate assignments, eligibility rules and calibration records determine which comparisons are reproducible. Two methods evaluated on the same release can receive different information or be scored on different message populations. A reported error is therefore an attribute of an identified experimental procedure, not of a method name alone.

The Antwerp release was introduced as an outdoor fingerprint-localization resource [1]. Version 1.3 supplies a gateway-coordinate catalogue, while the measurement table represents receivers as anonymised `BS` columns [2]. A geometric estimator needs a reliable link between those columns and the catalogue. We supply that link as an executable reconstruction and as a complete, directly readable data product. The reconstruction matches reception metadata between CSV and JSON before consulting coordinates; it does not choose identities using transmitter positions or localization accuracy.

The resource adds an explicit bridge for CSV-based experiments; it does not create gateway identifiers or newly surveyed coordinates. A JSON-native workflow can join its gateway identifiers directly to the catalogue [2]. The CSV crosswalk instead preserves tabular receiver dimensions, source-row identities and established evaluation populations while associating them with those same identifiers. It also audits agreement between representations without silently importing the surplus JSON record or imposing a unique physical-message identity within indistinguishable duplicate groups.

The delivered products are the 44-column identity/coverage table, catalogue-linked coordinate arrays, ordered experimental populations, and executable comparisons with per-message evidence. Tables S1.2–S1.3 print the central crosswalk and primary arrays; the machine-readable resource includes all 39 catalogue-backed identities and explicit missing-coordinate flags. These products support both reconstruction and continuity of existing tabular workflows.

The coordinate experiment examines an analyst's possible response to an unresolved identity join: infer receiver locations from calibration RSSI and transmitter positions. We audit one specified implementation, RSSFIT, rather than treating it as representative of all coordinate-recovery methods. On fixed receiver observations and messages, substituting its frozen coordinates changes the raw-centroid median error 7.54-fold. Its substantial coordinate discrepancies and restrictive search domains are reported alongside that contrast. The result measures this substitution, not the best attainable accuracy with unknown receivers or the prevalence of this procedure in prior work.

Reception support is a separate benchmark property. Both released measurement representations have a maximum of ten receptions per message, with more records at ten than at nine. We report that observation without identifying a cap mechanism or imputing missing signals. Geographic, receiver-removal, temporal and solver-status analyses provide supporting examples of how calibration, availability, evaluation population and event definitions affect interpretation. Together these analyses make the benchmark information and evaluation populations explicit.

# Related work and the scope of this audit

The dataset descriptor [1] presents fingerprinting baselines and explains that fingerprinting does not require receiver locations. The later release notes [2] document the addition of the gateway-coordinate file and the availability of per-message gateway identifiers in JSON. The descriptor covers an earlier collection; the release notes identify a later LoRaWAN collection and four added receiver columns. We use the versioned 2019 measurement files directly rather than importing the descriptor’s earlier population counts. Publication of coordinates does not itself supply the executable join to the tabular receiver labels.

Range-based and fingerprint-based localization have both been evaluated on this benchmark. Janssen et al. [3] compare the two approaches and study path-loss models, a modified E-Min-Max estimator and gateway selection. Islam et al. [4] investigate distance mapping from multiple received-signal features and modified trilateration, including evaluation using the public Antwerp data. Telles et al. [5] consider weighted-centroid localization. Fingerprinting work includes the hierarchical approach of Li et al. [6] and the convolutional architecture of Lutakamale et al. [7]. Moradbeikie et al. [8] additionally study fixed reference nodes and a dual-slope path-loss model, with evaluation using Antwerp data and a separate testbed. That study is relevant to calibration-aware ranging, but its reference-node architecture differs from the procedures tested here. These references establish relevant approaches; their numerical results are not interchangeable with the present splits, feature representations or median-error statistics.

The estimator kernels are drawn from the Antwerp localization analysis source snapshots [9] distributed with this study. The reused components include the centroid, lattice, Min-Max and numerical-solver routines. The contribution here is the receiver-identity resource and its controlled benchmark audit, not a new claim for those kernels or the separate common-mode analysis with which the source was originally associated. Supplement S9 identifies the consumed versions and declared changes. The measured RSSFIT effect is not attributed to publications with undocumented coordinate sources.

Adjacent reproducibility infrastructure includes Anagnostopoulos and Kalousis's dynamic-accuracy-estimation code deposit [10], which lists LoRaWAN preparation code and processed train/validation/test splits. Table S1.5 contrasts the information exposed by that deposit, the source release and this resource. The external comparison verifies deposit descriptions and file inventories, not the contents of the DAE notebooks or split archive; it does not establish whether those uninspected files contain a receiver crosswalk. The cited studies provide method context rather than a common-split leaderboard, and no exhaustive absence or first-ever priority claim is made.

# Data, methods and experimental identities

## Released inputs and the receiver-identity join

The reproduction baseline is the unchanged CSV payload identified by its SHA-256 in Supplement S1. It contains 130,429 data records, excluding the header, and 72 receiver columns. Non-reception is represented by −200. The working localization census contains 55,375 records with finite transmitter coordinates and at least three finite receiver measurements in the inclusive range [−150, −20] dBm. No HDOP filter is applied. Transmitter coordinates are projected from WGS84 to UTM zone 31N, EPSG:32631.

The source JSON contains 130,430 records, including 55,376 with at least three receptions. Every CSV row can be matched to a JSON metadata group while respecting duplicate multiplicities. One additional four-reception JSON record is documented separately. We do not append it to the CSV or alter established row identities. Local payload checksums agree with the published v1.3 file checksums [2]; that establishes file identity, not measurement correctness.

The fresh join uses reception time, spreading factor, HDOP rounded to two decimals and the sorted RSSI multiset to align CSV and JSON message groups. It excludes transmitter coordinates and localization results. Groups sharing a key must have identical gateway-ID/RSSI maps. Complete receiver RSSI/presence–absence sequences then identify which CSV column corresponds to each JSON gateway identifier. Candidate equality is proposed by hashing and confirmed by exact array comparison; ambiguity is not resolved by choosing a physically plausible position or a low localization error.

This procedure identifies all 44 active columns, of which 39 identifiers occur in the 249-entry coordinate catalogue. A calibration-only reconstruction identifies 41 receivers, including every member of the frozen 33-receiver benchmark roster; their identities agree outside calibration. The 33-receiver roster is retained for continuity with the identified primary experiment. Each member has at least twenty receptions in the fixed calibration set, but this verified property is not evidence of a prospectively selected or optimal support threshold. The calibrator's ten-reception minimum is a separate implementation condition. All additional catalogue-backed receivers are listed rather than silently excluded from the resource.

For example, BS14 maps to released identifier `FF0107C9`, whose catalogue entry is latitude 51.219257, longitude 4.413227 and whose preserved EPSG:32631 coordinate is (598,695.3, 5,675,156.5) m. It has 7,013 calibration receptions. BS35 is identifiable as `004A05D4` but has no entry in this catalogue; its coordinate fields remain missing. These examples illustrate identity availability and coordinate availability as separate properties. The complete crosswalk, including calibration-only evidence and out-of-calibration checks, is provided in Table S1.2 and `computational/data_products/receiver_crosswalk.csv`.

## Coordinate assignments and populations

We distinguish **Metadata-33**, the frozen catalogue-derived reference; **Recovered-29**, the historical correlation-selected map; and **RSSFIT-41**, the complete saved coordinate fit, whose primary view uses the same 33 identities as Metadata-33. “Official-33” in the source output is an alias for Metadata-33, not a certificate of physical truth. The metadata-derived **Transfer-29** roster and **historical common-27** intersection have separate memberships (Table S1.4). BS71 is retained in the primary analysis and examined in a named exclusion sensitivity because its catalogue location is extreme relative to the recorded survey (§5.2); no replacement is selected using localization outcomes.

Working records in CSV order are shuffled with Python `random.Random(1)`. The first 16,612 records form calibration; the remaining 38,763 form its ordered complement. Of these, 38,691 have at least three receptions in Metadata-33. `random.Random(9).sample` selects 2,500; five whose content keys occur in calibration are excluded without refill, leaving 2,495 in returned sample order. The content key consists of millimetre-rounded projected transmitter coordinates and sorted receiver/RSSI pairs with RSSI rounded to 0.001 dB. It is distinct from the outcome-independent serialization key used for the metadata join. Table S3.2 supplies all sampling and ordering recipes, including fingerprint, temporal and geographic populations.

The historical comparison used recovered-29 eligibility, giving a 2,498-record master sample and a 2,496-record common-27 subset. Only 174 rows overlap the new primary sample. These are separate experiments. Equal counts, the same seed applied to different pools, or similar method names do not establish pairing. Within each new comparison, pairing is verified using exact CSV-row identities and receiver selections. Supplement S3 supplies the population ledger and exclusion rules.

## The particular RSSFIT substitute

RSSFIT infers receiver coordinates from calibration transmitter positions and RSSI. The metadata assignment instead resolves reception identities before consulting the catalogue. We compare these two information paths using the specified implementation, not a representative or optimized coordinate-recovery method.

RSSFIT fits each receiver independently, using the inherited exponent 4.7, at most 2,000 calibration observations, and an upper-quartile RSSI filter when at least fifty observations survive. A power-weighted centroid of up to fifty strongest observations initializes a bounded local pattern search. At each candidate receiver coordinate, the objective uses a plug-in median intercept and scores the median absolute RSSI residual; the search reduces that score without a global-optimum guarantee. The fit box is the retained transmitter-coordinate extrema expanded by 2,000 m on every side. These settings, the full receiver traversal, shared generator and ordered search directions are specified in Supplement S2.3. They are settings of the audited implementation, not newly estimated physical constants or optimized design recommendations.

The frozen contract preserves input order when RSSI values tie at initialization. This is the declared stable-sort change to the copied evaluator; the map is saved and fingerprinted before localization. The reported effect includes this procedure's sampling, filtering, fixed exponent, bounds and local search. It is not a lower bound, a typical cost, or an unavoidable consequence of recovering coordinates without a catalogue. Supplement S8 distinguishes the original source contract from the current frozen result.

## Localization methods and calibration

For selected receivers with coordinates $g_i$, RSSI $r_i$ and fitted intercepts $A_i$, the raw and corrected weighted centroids are

\begin{equation}
\label{eq:M-1}
\widehat{x}_{\rm raw}=\frac{\sum_i10^{r_i/10}g_i}{\sum_i10^{r_i/10}},\qquad
\widehat{x}_{\rm bc}=\frac{\sum_i10^{(r_i-A_i)/10}g_i}{\sum_i10^{(r_i-A_i)/10}}.
\end{equation}

The raw centroid is the primary assignment instrument because it does not fit or consume intercepts. All selected receptions are ranked by raw RSSI, retaining source column order on ties, with at most ten receivers per fix. Coordinates do not enter this selection rule.

\needspace{7\baselineskip}

The baseline calibrator uses exponent $n=4.7$ and

\begin{equation}
\label{eq:M-2}
A_i=\operatorname{median}_{j\in\mathcal C_i}
\{r_{ij}+10n\log_{10}(\lVert g_i-t_j\rVert+1)\},
\end{equation}

where distances are in metres and a receiver requires at least ten calibration observations. No pooled-intercept imputation is used in the retained primary or geographic controls. For a map substitution, calibrated methods refit $A_i$ on the same calibration records; their treatment therefore includes the consequences of using that map during calibration.

The absolute and differential lattice methods use $q_i=r_i-A_i$ and $\ell_i(x)=\log_{10}(\lVert x-g_i\rVert+1)$. ABS minimizes the mean of $|q_i+10n\ell_i(x)|$. DIFF minimizes the median of

\begin{equation}
\label{eq:M-3}
\left|(q_i-q_j)+10n[\ell_i(x)-\ell_j(x)]\right|
\end{equation}

over pairs satisfying $|q_i-q_j|\geq3$ dB. Two triangular search grids are used, with side/spacing 6,000/600 m and 1,500/150 m. HYBRID combines the normalized absolute and differential residual groups as specified in Supplement S2. The revised empty-pair DIFF rule returns the corrected-centroid initializer; the historical first-grid-point behavior and its sensitivity are saved separately.

NLLS minimizes a Huber absolute-RSSI objective with three bounded L-BFGS-B starts. The implementation selects the lowest returned objective across starts, including finite unsuccessful returns. Trilateration jointly fits a common intercept. Min-Max returns the midpoint of the extrema of its per-receiver square bounds, including inverted intervals. All these behaviors are part of the evaluated implementations; they are not recommendations that every implementation should use them. Full definitions, starts, stopping settings and status handling are in Supplement S2.

The fingerprint baseline uses 8,000 calibration records selected by `random.Random(33).sample` from the ordered calibration indices, retaining returned sample order as database order. Features are raw RSSI with −200 fill; the estimate is the mean coordinate of three nearest neighbours under squared Euclidean feature distance. Equal-distance neighbours retain database order. The fixed neighbour count is not tuned to evaluation errors. The same receiver dimensions are used in each paired comparison. Removing a receiver masks that dimension in both database and query; this is not a simulated undetected hardware failure.

## Quantities, pairing and resampling sensitivity

The primary error is Euclidean distance from the returned location to the CSV transmitter coordinate. We report medians, selected tail summaries and availability; finite estimates with solver warnings are not discarded. Contrasts are differences of medians or ratios of medians, not medians of paired differences. Percentage increases use the named reference arm as denominator.

For a fixed evaluation sample, maps and predictions, the observed contrast is deterministic. We report **95% conditional bootstrap sensitivity intervals**: the 2.5th and 97.5th percentiles of 6,000 resampled contrasts, seed 20260905. The reference distribution is the stated empirical resampling scheme over the observed messages or occupied blocks, not a claimed population-sampling law. Each replicate uses the same indices in both arms. Spatial schemes sample occupied 500 m or 1,000 m UTM cells anchored at the coordinate origin; temporal clusters are UTC calendar days. Every member of each sampled cluster is included with multiplicity. Calibration records and coordinate assignments remain fixed. The intervals describe sensitivity to representation of the observed messages/blocks; nominal population coverage, cluster independence, repeated-refitting uncertainty and transfer to other deployments are not established. The same interpretation applies to all resampling intervals below. Secondary and post-analysis choices remain identified, without multiplicity-adjusted discovery claims.

Resampling sensitivity is evaluated for the paired contrast itself, not by comparing it with a marginal redraw-dispersion threshold. Close medians and intervals crossing zero do not establish equivalence.

# Experimental questions and controlled contrasts

Table 1 identifies each controlled contrast. Raw WCL changes only its coordinate input; calibrated pipelines can also change through intercepts and numerical domains. Other controls vary calibration records or receivers. Their magnitudes are not additive contributions to inter-study differences.

\Needspace{10\baselineskip}
**Table 1. Retained experimental questions and the variables held fixed.**

| Question | Controlled comparison | Interpretation |
|:--|:--|:--|
| Coordinate assignment | Same identities, RSSI, messages and raw centroid | Cost of the tested assignment substitution |
| Method sensitivity | Same inputs within an identified benchmark; method-specific calibration/bounds stated | Performance of these implementations |
| Receiver removal | Reduced and full rosters on the same survivors, plus availability | Separate treatment from population selection |
| Geographic calibration | Equal training budgets; common calibrated roster; both directions | Transfer sensitivity of the specified baseline |
| Temporal calibration | Original-row timestamps; matched records and budgets | Method-, metric- and map-specific sensitivity |
| Reception endpoint | Complete source-representation counts | Observed support, without a proven cap mechanism |

# Coordinates: the measured assignment effect

## Fixed-roster comparison and resampling sensitivity

The primary 33-receiver comparison gives raw-centroid medians of **480.09 m** with metadata-derived coordinates and **3,619.22 m** with the frozen RSSFIT assignment: **7.5387×**, a difference of **3,139.13 m**. RSSFIT produces greater individual error on 98.68% of the 2,495 records. The same receiver identities and raw measurements are used at every paired fix. Figure 1 shows the empirical error distributions; Table 2 reports conditional resampling sensitivity.

![Raw weighted-centroid error distributions on the same 2,495 primary records and 33 receiver identities. The horizontal scale is logarithmic. The two arms differ only in the supplied coordinates; this comparison does not include a calibration-dependent centroid correction.](figures/F1_assignment_ecdf.pdf){width=93%}

\Needspace{9\baselineskip}
**Table 2. Primary assignment contrast: 95% conditional bootstrap sensitivity intervals with frozen calibration and maps.**

| Resampling unit | Occupied units | Difference sensitivity interval (m) | Ratio sensitivity interval |
| :-- | :-- | :-- | :-- |
| Paired messages | 2495 | [3,074.13, 3,203.73] | [7.16, 7.98] |
| 500 m spatial cells | 107 | [1,081.77, 3,418.07] | [5.19, 10.15] |
| 1,000 m spatial cells | 39 | [757.23, 3,433.93] | [4.80, 10.31] |
| UTC calendar days | 52 | [3,002.51, 3,245.94] | [6.96, 8.47] |

\Needspace{4\baselineskip}
All four sensitivity intervals retain a positive contrast, with materially wider spatial limits. This does not imply that every possible resample, region or future deployment has the same effect.

\Needspace{4\baselineskip}

The historical-population common-27 control separately gives **425.28 m versus 3,657.74 m**, or **8.6007×**, on 2,496 records. It is not interchangeable with the primary sample, and the difference between 8.60× and 7.54× is not a roster-only decomposition.

The two coordinate assignments are shown in Figure 2 and characterized in Table 3. The median receiver discrepancy remains 5.22 km after excluding BS71, so the largest discrepancy is not the sole source of the roster-wide mismatch. Discrepancies are unweighted summaries over the named receiver identities, relative to the catalogue assignment rather than independently verified physical errors.

\Needspace{12\baselineskip}
**Table 3. Frozen coordinate discrepancies and fit-domain properties. Distances are in metres; p90 uses linear quantile interpolation. The second row is an explicitly restricted sensitivity summary, not the full primary roster.**

| Receiver set | Median | p90 | Maximum | Reference outside box | Fit on boundary |
| :-- | --: | --: | --: | --: | --: |
| Primary 33 | 5,236.26 | 10,855.46 | 45,169.18 (BS71) | 8/33 | 26/33 |
| Same set without BS71 | 5,222.24 | 9,279.64 | 11,617.95 (BS16) | 7/32 | 26/32 |

Eight reference locations—BS6, BS16, BS22, BS33, BS37, BS44, BS48 and BS71—lie outside the exact boxes reconstructed from their retained fit observations. Their catalogue locations were unavailable to those constrained fits. Twenty-six fitted points lie on a box boundary, using absolute tolerance $10^{-7}$ m. These are receiver-fitting domains, not NLLS transmitter-localization domains. Full coordinates, support, box limits and side margins are available in Tables S1.3 and S4.1 and the machine-readable geometry records.

Boundary solutions and excluded reference points materially qualify the intervention. They do not isolate the contributions of bounds, exponent, objective, observation selection and local optimization to the localization-error contrast, or show that a larger domain would recover catalogue coordinates. The maps and boxes were not changed for this retrospective description.

![The complete frozen coordinate intervention in EPSG:32631. Catalogue-derived positions are circles, RSSFIT positions are crosses, and the recorded calibration transmitter positions provide survey context. Dashed segments connect the two assignments for each of the same 33 identities. BS71 is shown at its actual catalogue location rather than hidden by local plot limits. Distances relative to the catalogue are not independently surveyed physical position errors.](figures/G1_full_coordinate_overview.pdf){height=5.65in}

For the fixed normalized raw-WCL weights $p_{ij}=10^{r_{ij}/10}/\sum_{h\in I_j}10^{r_{hj}/10}$ over the selected receivers $I_j$,

\begin{equation}
\label{eq:M-4}
\widehat{x}^{\rm fit}_j-\widehat{x}^{\rm meta}_j
=\sum_{i\in I_j}p_{ij}(g_i^{\rm fit}-g_i^{\rm meta}).
\end{equation}

The identity explains the coordinate-only position change of the instrument. It does not require error relative to the transmitter to increase, and it does not make the two medians or the receiver discrepancies additive.

## BS71 exclusion sensitivity

BS71 has released identifier `004A026B`, catalogue latitude 50.844898 and longitude 4.132583, and preserved EPSG:32631 coordinate (579,736.5, 5,633,188.3) m. In a retrospective description of this frozen entry, its nearest distance to any of the 16,612 calibration transmitter positions is **42.398 km**. Across the **58 calibration records received by BS71**, the median individual catalogue-to-transmitter distance is **46.995 km**, with range **46.641–47.134 km**. This is an extreme catalogue entry relative to this survey, not proof of a typo, relocation, impossible reception, or physical error. This retrospective diagnostic uses transmitter positions; the identity join does not. The historical flagging rationale remains unknown.

BS71 is selected in eight of the 2,495 primary messages. The paired exclusion result below, rather than this low selection count alone, tests whether the aggregate contrast persists without it.

Excluding BS71 from both primary assignments leaves 2,493 jointly eligible records. On those survivors the raw medians are 479.46 m and 3,623.73 m, giving 7.56×. The archive also retains full-roster predictions on those exact survivors, so the effect of changing the roster is not confused with the loss of two messages. No alternative BS71 coordinate is selected.

For NLLS, exclusion also changes the full-map bounding box and Halton starts. Predictions can therefore change even for messages that did not receive BS71. Its anomaly sensitivity includes a search-domain change; the raw-centroid sensitivity does not. Metadata identity, physical catalogue accuracy and estimator-optimal coordinates are separate questions.

## Method-level consequences

Table 4 gives the primary comparison. In both arms, the roster and messages are matched. Calibrated methods additionally refit their intercepts; the NLLS search box depends on the map. Accordingly, these are coordinate-substitution consequences within specified pipelines, not all pure coordinate-only interventions.

\Needspace{14\baselineskip}
**Table 4. Primary median errors (m), 2,495 messages.**

| Method / variant | Metadata-derived | RSSFIT, same roster | Ratio |
| :-- | :-- | :-- | :-- |
| Fingerprint (k=3) | 219.29 | Identical predictions | Not coordinate-dependent |
| Min-Max | 467.64 | 2,078.50 | 4.44× |
| Raw WCL | 480.09 | 3,619.22 | 7.54× |
| NLLS | 524.87 | 1,201.86 | 2.29× |
| ABS, mean | 527.75 | 1,243.11 | 2.36× |
| HYBRID, mean | 576.26 | 1,225.80 | 2.13× |
| Corrected WCL | 584.75 | 3,105.20 | 5.31× |
| Trilateration | 585.03 | 1,708.86 | 2.92× |
| DIFF, median | 999.91 | 1,611.17 | 1.61× |

Min-Max has the smallest observed geometric median, but its paired median difference relative to raw WCL is −12.45 m, with a paired sensitivity interval [−39.98, 13.19] m. This does not establish a unique geometric winner. Fingerprinting is more accurate under this dense within-survey protocol. For each of the 2,495 queries, we compute the minimum Euclidean distance in EPSG:32631 from its recorded transmitter position to any of the 8,000 stored database transmitter positions; the median of those minima is 1.58 m. This geographic-support diagnostic is distinct from the RSSI-selected neighbours and from localization error (Supplement S2.7). Cross-region transfer is tested separately.

These are implementation-specific results; Supplement S8 records consequential version differences.

## Fitted-residual diagnostic

On the same 69,988 common-27 calibration links, pooled per-receiver-median-centred residuals have excess kurtosis **1.5913** under metadata-derived coordinates and **18.3076** under the stable RSSFIT map. The links and moment conventions are identical in the two arms. Their residual standard deviations are 8.8553 and 6.2837 dB respectively: lower fitted-residual dispersion does not by itself establish a coordinate assignment's positional accuracy. This is a calibration-residual diagnostic for the specified model, not a universal physical-noise law or an explanation of heavy tails reported in other studies. Definitions and the full link record are supplied in Supplement S5.

# Redundancy: observed support and what it leaves unknown

## Endpoint in both representations

The working CSV census has the counts in Figure 3. Its most frequent count is three; ten is its maximum observed support with a local upturn. There are 2,709 ten-reception records, compared with 1,358 at nine. The endpoint comprises 4.892% of the 55,375-record working census and approximately 2.077% of the full 130,429-record CSV.

![Observed reception counts in the unchanged CSV working census (55,375 records with at least three receptions). Counts one and two are outside this conditional census, not observed zero-frequency bins. The maximum is ten, with 2,709 records; no extrapolated curve or mechanistic cap label is imposed.](figures/F2_observed_receptions.pdf){width=93%}

The source JSON also has maximum ten and 2,709 records at ten; its one surplus record has four receptions. The version notes describe the updated release as including metadata from all receiving gateways, in contrast to the previous three-gateway metadata limit [2]. We report the observed endpoint alongside that source description, not as a contradiction proving truncation. The files do not identify whether filtering, a reporting limit, reception conditions or another process produced the endpoint, or reveal the identities and strengths of any unreported receptions.

## Threshold membership and dependent pair terms

Under ordinary count top-coding,

\begin{equation}
\label{eq:M-5}
K_{\rm obs}=\min(K_{\rm true},10),
\end{equation}

and for every threshold $k\leq10$,

\begin{equation}
\label{eq:M-6}
\{K_{\rm obs}\geq k\}=\{K_{\rm true}\geq k\}.
\end{equation}

Such a cap cannot hide additional raw-count membership at seven or eight. In the working census, 8,596 records reach seven and 5,993 reach eight. What remains unknown under that model is the distribution above ten. Unknown reception retention can separately alter support within a particular mapped roster; that must not be confused with the raw-count identity.

Likewise, $k(k-1)/2$ pairwise differences are not that many independent observations. The complete difference representation of $k$ scalar observations has rank at most $k-1$. Pair-count growth alone therefore cannot establish a quadratic information disadvantage for an entire localization family. Observed estimator sensitivity can be measured, but the cost of unobserved receptions is not measured here.

The selector cannot choose among more than ten observed receptions in this release. This limits the selection regimes that the data can exercise; it does not establish an estimator's optimum or identify which method would improve under unobserved deeper support.

# Transfer: calibration and available receivers

## Equal-budget geographic comparison

The geographic experiment distinguishes within-survey interpolation from spatial extrapolation, both legitimate evaluation targets. It fixes the metadata reference, equalizes the training-record budget, and tests both directions. The easting boundary is the median of calibration transmitter eastings, **598,817.27 m**. West and east each contain 8,306 of the calibration records; each training arm samples **8,000**. Fingerprint database entries and geometric intercept-calibration records are the same within an arm.

Across citywide, west-only and east-only training for three specified seeds, **29 metadata-derived receivers** have at least ten calibration receptions in every arm. This common transfer roster excludes BS33, BS44, BS50 and BS71 for calibration support; it is **not recovered-29**. Holding that roster fixed gives 1,263 eastern evaluation records and 1,218 western records. All eastern parent records remain; 14 of the 1,232 western parent records fail the shared-roster eligibility rule. There is no pooled-intercept imputation, and the same evaluated rows are used in both calibration arms and all three repeats.

\Needspace{15\baselineskip}
**Table 5. Geographic transfer, prespecified first calibration draw (seed 3101). Each direction is a separate fixed population. Errors are medians in metres.**

| Method | East: citywide | East: west only | West: citywide | West: east only |
| :-- | :-- | :-- | :-- | :-- |
| Fingerprint (k=3) | 51.09 | 614.29 | 304.32 | 1,124.88 |
| Raw WCL | 246.70 | 246.70 | 631.25 | 631.25 |
| Corrected WCL | 171.73 | 185.95 | 785.14 | 839.95 |
| ABS, mean | 284.35 | 652.39 | 622.34 | 860.99 |
| DIFF, median | 568.21 | 572.55 | 1,417.93 | 1,315.19 |
| Min-Max | 238.58 | 343.03 | 567.89 | 687.94 |

The fingerprint baseline deteriorates in both directions. Its 1,000 m spatial-block sensitivity intervals for the increase in median error are [532.42, 1,276.41] m eastward and [616.48, 1,261.23] m westward. Across the three specified calibration draws, its median increase ranges from 1,102.28% to 1,140.79% eastward and from 263.57% to 269.64% westward. These large relative changes begin from very different in-region accuracies and must be read with the absolute transferred errors.

The geometric methods do not move uniformly. ABS worsens substantially; the corrected centroid moves less; the differential median is nearly unchanged eastward and decreases westward in the point estimates. Raw WCL is exactly invariant to a change in unused calibration. No result here establishes a limitation of fingerprinting as a family or general transfer superiority of range-based methods. The training pools overlap heavily across the three draws; they provide calibration-subset sensitivity, not three independent deployments. All method contrasts and dependence-sensitivity intervals are reported in Supplement S6 and the numerical archive.

## Receiver removal: coverage and selection separated

Receiver removal is evaluated on the existing 2,495-record primary population. At retained roster sizes 23, 16, 10 and six, eight explicitly seeded subsets of the 33 reference identities are tested; the full roster supplies a zero-removal control. Fingerprinting uses the same 8,000 training records with dimensions removed from both database and query. Min-Max retains the existing per-receiver calibration values. At each subset, both methods are compared on the same messages having at least three remaining receptions.

For each subset $S$ with surviving population $E_S$, we report

\begin{equation}
\label{eq:M-7}
\begin{aligned}
\Delta_{\rm removal}&=\operatorname{med}(e_S\mid E_S)-\operatorname{med}(e_{33}\mid E_S),\\
\Delta_{\rm selection}&=\operatorname{med}(e_{33}\mid E_S)-\operatorname{med}(e_{33}\mid E),
\end{aligned}
\end{equation}

whose sum equals the displayed reduced-versus-parent median difference. This is an exact accounting of two changes, not a universal causal density model. Fingerprint predictions on all parent rows are also exported: the three-reception restriction is a shared geometry-comparison rule, not a requirement of the fingerprint algorithm.

\Needspace{11\baselineskip}
**Table 6. Receiver-removal descriptions. At each reduced count, error entries are the median of eight subset-specific medians, not a pooled-message median. Availability ranges across the eight draws are reported separately.**

| Receivers retained | Surviving messages: range | Fingerprint | Min-Max |
| :-- | :-- | :-- | :-- |
| 33 | 2,495 | 219.29 | 467.64 |
| 23 | 972–1,796 | 323.75 | 609.72 |
| 16 | 690–1,276 | 380.46 | 685.69 |
| 10 | 177–722 | 450.11 | 830.08 |
| 6 | 4–274 | 514.62 | 1,404.65 |

Which receivers remain matters substantially. Six-receiver subsets retain only **4–274** geometrically eligible records out of 2,495; the median retained count is 43. Those subsets do not establish a universal sparse-deployment tie or a sharp density threshold. The complete per-subset results, exact decomposition and conditional paired sensitivity intervals are retained, including the smallest strata. Intervals for tiny strata are descriptive and should not be treated as reliable population-level evidence.

Selection can even make a reduced-roster comparison look better than the full-parent benchmark. For the first specified 23-receiver draw, the fingerprint median on 1,676 survivors is 154.63 m, compared with 219.29 m on the original parent. Of the −64.66 m displayed difference, −56.68 m is selection and −7.98 m is the within-survivor removal component. Min-Max on those same survivors has a +37.15 m removal component partly offset by −16.10 m selection. Figures S2–S3 display both components for **all 32 reduced-roster draws per method**, including negative values and the smallest survivor strata. Components add within each draw; separate across-draw medians or range endpoints need not add. This is why conditional error and availability are reported together.

## Temporal calibration sensitivity

Temporal membership uses original CSV-row timestamps. Equal 16,612-record early and interleaved calibration sets are compared on 1,198 fixed late messages under Metadata-33. Median increases are +1.88% for ABS, +0.18% for DIFF and +1.42% for Min-Max; corrected WCL is nearly unchanged. Their paired median sensitivity intervals and tested spatial/day intervals include zero.

This does not establish that temporal deterioration is absent. The recovered-map median effect persists after timestamp repair, and an explicitly exploratory examination of the preferred-map results finds ABS mean error increasing from 752.23 to 816.44 m and p90 from 1,637.07 to 1,835.99 m. Their sensitivity intervals remain positive under the tested block schemes. The follow-up inspected all five temporal methods, retained null outcomes and was not substituted for the median endpoint as though it were a pre-existing primary claim. It is not multiplicity-adjusted.

The defensible conclusion is method-, metric-, map- and protocol-specific calibration sensitivity. The interleaved arm is not a prospective deployment, and time, route and calibration-distribution changes are not fully separated. Supplement S6 preserves the legacy replay, timestamp-only repair, matched-map bridge and secondary mean/tail evidence. Neither universal ageing nor universal calibration stability is established.

\Needspace{7\baselineskip}

## Operational boundaries

Receiver masking in this fingerprint baseline does not require a complete database rebuild. A geometric anchor requires its coordinate and any fitted intercept. Runtime and storage comparisons are not measured here; their costs depend on the implementation and data representation.

# Diagnosis: what the recorded status means

## Aggregate feasibility and optimizer termination

In the primary analysis, Min-Max marks 1,195/2,495 intersections infeasible with the metadata assignment and 469/2,495 with RSSFIT, while returning its midpoint-of-extrema estimate in every case. The lower aggregate infeasibility rate accompanies worse positional accuracy under RSSFIT. Thus this aggregate rate is not a monotonic indicator of reference-map quality in the tested comparison. It does not establish that per-message infeasibility has no predictive value.

Optimizer termination and proximity to the geographic search boundary are recorded separately (Table 7). A boundary-near result is defined by a distance below 100 m to a side of the map-dependent search box.

\Needspace{10\baselineskip}
**Table 7. NLLS events, 2,495 evaluated cases per assignment. All finite returned positions remain in the accuracy summaries.**

| Event | Metadata-derived | RSSFIT |
|:--|--:|--:|
| Selected optimizer return unsuccessful | 281 | 296 |
| All three starts unsuccessful | 3 | 6 |
| Selected position within 100 m of a search bound | 0 | 102 |

An unsuccessful termination need not imply an unusable returned position, and proximity to a boundary is not optimizer failure. All finite returns remain in the accuracy summaries. The observed NLLS median contrast—524.87 m versus 1,201.86 m—is a result for this solver, its map-dependent calibration and its search domain. It is neither a comparative runtime result nor a finding that optimizer warnings occur only under estimated coordinates. Supplement S8 distinguishes the older boundary-based “divergence” count from these events.

## Diagnostic scope

Aggregate feasibility, optimizer termination and positional error are different diagnostics. No per-message prediction, pruning or switching policy is validated. Supplement S8 retains the relevant adverse exploratory observations.

# Reproducibility and limits of the evidence

The reviewer resource exposes the complete receiver crosswalk, catalogue/support flags and coordinate arrays in `computational/data_products/`. Ordered calibration, evaluation and database identities are in `computational/populations/`. Current per-message results and solver-start records are in `computational/results/`, with operative sources in `computational/src/`. Exact receiver-fit geometry and retrospective BS71 records are in `geometry/results/frozen_geometry/`. The main and supplementary tables have direct input/producer entries in `table_figure_index/INDEX.md`; a reader does not need the development chronology to retrieve a current result.

The root `README.md` distinguishes saved-evidence verification, a source-to-join/frozen-map centroid replay, full primary and secondary producer routes, and the geometry description. For example, the `verify` route checks the supplied evidence without refitting coordinates. With the two hash-matched raw measurement archives, the `core` route rebuilds identities, checks ordered populations and independently computes raw-WCL positions. The `primary` route additionally repeats the existing RSSFIT fit and localization producers. These execution scopes are not interchangeable. Supplement S7 gives commands, environments and receipt locations.

Source snapshots and declared method changes remain distinguishable. Hashes establish byte identity, while scoped execution checks test specified failure modes. Repeatability in the recorded environment is not independent replication or physical verification of catalogue coordinates.

The study concerns one release, one survey setting and a particular constrained coordinate substitute. Transmitter positions are the provided GPS reference, not independently resurveyed truth. Catalogue compatibility with every measurement time is not certified. The reference is preferred because its identity derivation is explicit and does not choose assignments by localization outcomes, not because it is known to minimize error. Block resampling examines conditional sensitivity within the observed survey; it does not establish cross-city performance or account for repeated coordinate refitting.

The accompanying reviewer resource is `Computational_Supplement_Anonymous_S1.zip`, version `PaperA-Anonymous-S1-2026-09-11`. It contains the scientific sources, data products, ordered populations, saved predictions, and reproduction entry points supporting this paper. `EVIDENCE_MANIFEST.json` identifies the retained scientific files; `REVIEW_BINDING.json` binds this manuscript and supplement to that evidence. Author-identifying documents and deposit metadata are separated into the editor-only record. Original public inputs are cited independently [2].

# Conclusion

The Antwerp receiver-identity resource links all 44 active measurement columns to gateway identifiers and connects 39 to catalogue coordinates. It supplies complete crosswalk and coverage tables, frozen coordinate arrays, ordered populations and executable evidence, so geometric comparisons can be traced to the information actually used.

On the frozen 33-receiver roster and 2,495 fixed messages, the specified RSSFIT coordinate substitution increases raw-centroid median error from 480.09 m to 3,619.22 m. A separate historical-population common-27 comparison and the tested paired, dependence and BS71-exclusion sensitivities support the same qualitative finding. The fit is substantially constrained: 26 primary fitted positions are on box boundaries and eight catalogue points are outside their boxes. The contrast therefore describes this procedure and its output, not a typical or unavoidable penalty for missing coordinates or a bound on attainable coordinate recovery.

Both CSV and JSON have a ten-reception endpoint with 2,709 records at the maximum. Its cause and the performance cost of unobserved receptions remain unresolved. The CSV census is preserved, and its one-record difference from JSON is documented rather than silently reconciled. The supporting controls show why calibration distribution, available receivers, exact population and solver-event definitions belong alongside accuracy. Temporal sensitivity is retained in conditional recovered-map and exploratory mean/tail findings, without a universal ageing claim.

The supplied identity and execution products make benchmark choices inspectable: the coordinate assignment and receiver roster, preserved evaluation records, separate coverage and conditional-error reporting, and an explicit resampling target.

# Declaration of generative AI and AI-assisted technologies {-}

The author used 5.6 Sol. as assistive tools for drafting and refining the manuscript and supporting the implementation of analyses and computational experiments. The author directed the research, made the final methodological and interpretive decisions, and reviewed and verified the AI-assisted work incorporated into the study. The author takes full responsibility for the accuracy and integrity of the manuscript, including its methods, results, and conclusions.

# References {-}

\Needspace{6\baselineskip}

[1] M. Aernouts, R. Berkvens, K. Van Vlaenderen and M. Weyn, “Sigfox and LoRaWAN datasets for fingerprint localization in large urban and rural areas,” *Data* 3(2), 13 (2018). doi:10.3390/data3020013.

\Needspace{6\baselineskip}

[2] M. Aernouts, R. Berkvens, K. Van Vlaenderen and M. Weyn, *Sigfox and LoRaWAN Datasets for Fingerprint Localization in Large Urban and Rural Areas*, Zenodo, version 1.3. doi:10.5281/zenodo.3904158. File version and checksums are specified in Supplement S1.

\Needspace{6\baselineskip}

[3] T. Janssen, R. Berkvens and M. Weyn, “Benchmarking RSS-based localization algorithms with LoRaWAN,” *Internet of Things* 11, 100235 (2020). doi:10.1016/j.iot.2020.100235.

\Needspace{6\baselineskip}

[4] K. Z. Islam, D. Murray, D. Diepeveen, M. G. K. Jones and F. Sohel, “Machine learning-based LoRa localisation using multiple received signal features,” *IET Wireless Sensor Systems* 13(4), 133–150 (2023). doi:10.1049/wss2.12063.

\Needspace{6\baselineskip}

[5] G. P. Telles, O. K. Rayel and G. L. Moritz, “Weighted-Centroid localization using LoRaWAN network on large outdoor areas,” *Internet Technology Letters* 5(4), e367 (2022). doi:10.1002/itl2.367.

\Needspace{6\baselineskip}

[6] Y. Li, J. Barthélemy, S. Sun, P. Perez and B. Moran, “Urban vehicle localization in public LoRaWan network,” *IEEE Internet of Things Journal* 9(12), 10283–10294 (2022). doi:10.1109/JIOT.2021.3121778.

\Needspace{6\baselineskip}

[7] A. S. Lutakamale, H. C. Myburgh and A. de Freitas, “RSSI-based fingerprint localization in LoRaWAN networks using CNNs with squeeze and excitation blocks,” *Ad Hoc Networks* 159, 103486 (2024). doi:10.1016/j.adhoc.2024.103486.

\Needspace{6\baselineskip}

[8] A. Moradbeikie, A. Keshavarz, H. Rostami, S. Paiva and S. I. Lopes, “A cost-effective LoRaWAN-based IoT localization method using fixed reference nodes and dual-slope path-loss modeling,” *Internet of Things* 24, 100990 (2023). doi:10.1016/j.iot.2023.100990.

[9] Antwerp localization analysis source snapshots, research software accompanying this submission (2026). The original evaluator, baseline harness and versioned stable evaluator are specified in Supplement S9 and `provenance/CODE_ATTRIBUTION.md`. Author-identifying bibliographic details are supplied separately to the editor for double-anonymized review; no companion-publication status is asserted.

[10] G. Anagnostopoulos and A. Kalousis, *Can I Trust This Location Estimate? Reproducibly Benchmarking the Methods of Dynamic Accuracy Estimation of Localization (code)*, Zenodo, version v1 (2022). doi:10.5281/zenodo.5589651.

\clearpage

# Declarations {-}

**Funding.** No funding was received for this work.

**Data and code availability.** The public input is dataset version 1.3 [2]. The review resource `Computational_Supplement_Anonymous_S1.zip` contains the identity and coordinate products, ordered populations, operative code, saved results and verification instructions. Raw CSV and message-JSON payloads are obtained separately and checked against their recorded fingerprints. The catalogue retains its original source identity. Author-identifying repository and deposit details are supplied in the editor-only submission record rather than linked from this anonymous copy.
