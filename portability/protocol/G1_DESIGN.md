# Paper A — G1: bounded portability and external-workflow integration

Date: 21 September 2026  
Baseline: PR5D, *A Verified Receiver-Provenance Resource for Reliable Evaluation of the Antwerp LoRaWAN Benchmark*  
Status: designed; the new core, conformance suite and DAE integration have **not** been executed.  
Purpose: a small implementation extension to the existing resource, not a new generalization project, a coordinate-recovery method, or reopening PR1–PR5D.

## 1. Decision and intended contribution

Proceed with one reusable exact-correspondence core, an Antwerp parser preserving the existing rules, one explicitly synthetic alternative schema, and one integration into the already supplied DAE LoRaWAN preparation workflow. Retain the existing scientific claims and results. The extension is optional strategic strengthening of portability and usefulness; previous source-comparison and editorial closures remain closed.

The question is: **Can the same correspondence procedure operate independently of Antwerp field names and attach receiver metadata to a separately authored CSV workflow without changing its measurements, labels, ordered partitions or absence semantics?**

A successful result supports an implementation and applicability claim. It does not demonstrate external-deployment localization accuracy, independent user adoption, a novel schema-matching algorithm, or a general solution for noisy or unrelated datasets. Synthetic schemas and a second workflow on Antwerp are not additional field datasets.

The assessment accompanying PR5D distinguishes resource originality, empirical/diagnostic originality and general methodological originality [R1, lines 75–95]. Its proposed external integration is an optional significance enhancement, not a previously failed completion criterion [R1, lines 68–73, 118]. G1 preserves that distinction.

## 2. Hard scope boundary

### Included

- Extract the existing exact signature-association operation behind an explicit schema-independent interface; do not rewrite the scientific pipeline.
- State conditional soundness, uniqueness and ambiguity behavior and preserve original record/partition identities.
- Reuse existing tests and add only the portability, ambiguity and differential-integration cases not already covered.
- Compare the new core with the frozen existing Antwerp reconstruction as a regression oracle, never as an input to inference.
- Run the supplied DAE preparation notebook's computational source in an isolated workspace and demonstrate metadata attachment without changing its original outputs. No augmentation or estimator training is needed.
- Report descriptive runtime/memory and a complete pass/fail/mismatch inventory. No speed-superiority claim.
- Incorporate one short methods subsection, one compact evidence table, and a concise applicability/limitations paragraph after results are known. Put implementation details in a single supplementary section.

### Excluded

No new city, radio measurement campaign, localization estimator, coordinate fit, learned matcher, fuzzy linkage, automatic schema discovery, timestamp correction, tuned matching threshold, broad factorial study, DAE/ProxyFAUG predictive benchmark, new sensor-control policy, or claim to repair unreported receptions. Do not import Paper B, DeltaMesh or ACFSE contributions. Do not modify the original crosswalk, source data, historical split, fit, selected map, model-selection rule, reported error, or existing GitHub/Zenodo version.

A case failing the exact-correspondence assumptions produces an explicit refusal/ambiguity report. Implementing a statistical or fuzzy remedy for that case is outside G1. Reaching a limitation is a valid phase outcome, not permission to expand scope.

## 3. Scientific separation: three different forms of generality

1. **General formulation:** a conditional statement about compatible representations of the same observations.
2. **Implementation portability:** one core operates under more than one declared schema without data-specific constants.
3. **External empirical validity:** practical benefits recur in independently evaluated datasets/deployments.

G1 targets (1) and (2), plus independently authored workflow compatibility on the same dataset. It does not target (3). The identity procedure is computed, not trained. The inherited coordinate fitter remains a different, calibrated component outside this extension.

## 4. Architecture and explicit inputs

Keep the public/internal module name descriptive (for example `identity_core.py`), not a new grand framework name.

### 4.1 Source adapters

An adapter converts source fields into canonical observations while preserving a separate record of the source bytes and schema rules. For Antwerp, keep the existing conventions: receiver-column parsing; first gateway reception time; spreading factor; two-decimal HDOP key; integral RSSI validation; explicit nonreception; original row order; and original source hashes. Projection and catalogue-coordinate rounding stay in the existing post-association stage.

The synthetic second adapter uses a differently shaped table/long-record schema with arbitrary channel names and an explicit presence field rather than an RSSI sentinel. It demonstrates schema separation, not physical realism. No fitting or training is involved.

### 4.2 Canonical representation

The core receives:

- authoritative primary row handles and declared record-group keys;
- ordered original anonymous feature handles;
- comparable canonical measurement tokens and a distinct presence/absence tag;
- named-identifier measurements in corresponding secondary record groups;
- an optional explicit subset of rows to use for correspondence recovery;
- declared treatment of secondary-only occurrences.

The core does **not** receive transmitter coordinates, catalogue coordinates, localization errors, receiver-nearness criteria, test outcomes or a learned model. Avoid parsing optional labels at all within the core. Source adapters must make canonicalization explicit; do not silently round or coerce data to force equality. Present numeric zero and absence must be different states. Length-delimited or structured serialization must avoid accidental delimiter collisions. Hashes propose candidates only; exact token/presence equality confirms them.

A primary row handle is `(original_payload_sha256, original_row_index)`. A derivative file gets its own hash and an explicit mapping back to those handles; it does not impersonate the original payload. Original partition order remains authoritative even when the derivative view is sorted differently.

### 4.3 Registry attachment and population sidecars

Attach registry attributes only **after** identity association. Return absent registry attributes as unavailable, not numeric zero and not an estimated replacement. A bad physical registry cannot be authenticated by this procedure.

Population sidecars carry original row handles, original partition name, original within-partition position, source feature order and duplicate-group status. Do not inject these fields into a model's feature or target matrix. In particular, adding a row-ID column to the DAE input table could contaminate its positional target slice; this is prohibited.

### 4.4 Outputs

The phase producer should emit a column-association table, record-group/occurrence reconciliation table, unresolved/conflict report, registry-missingness table, and a preservation/differential-test report. Existing source IDs and original benchmark outputs remain separately pinned. A report of a unique relation means unique within the stated observation model, not independently surveyed physical identity.

## 5. Conditional correctness and refusal rules

Let `s_c` be the signature of primary feature `c` over valid aligned observations (presence tag plus canonical value). Let `t_g` be the signature of named identifier `g` over exactly those observations. Define `C(c) = {g : s_c = t_g}`.

### 5.1 Preconditions

Record/group alignment must be defensible under declared metadata keys. Within an indistinguishable secondary group, named reception maps must agree before arbitrary occurrence representatives can be used. Secondary multiplicity must cover the authoritative primary multiplicity. The canonical value and absence conventions must be comparable. Recovery rows must be explicitly specified. None of these conditions may be repaired using physical proximity or favorable downstream error.

### 5.2 Unique association

When each supported primary feature has exactly one equal named signature and those assignments are injective, the compatible column-to-identifier association is uniquely determined within this input model. Any compatible relation must choose an equal signature; the sole candidate fixes the choice. State this as a short correctness proposition, not a newly invented matching theorem.

### 5.3 Ambiguity and conflict

- No equal candidate: report unmatched/inconsistent at that scope; do not choose a nearest signature.
- More than one equal candidate: report the complete ambiguity class; do not break the tie lexicographically, by registry location or by prediction error.
- No observed support: mark inactive/unsupported, rather than infer an identity from an all-absence signature.
- A duplicate key with disagreeing named maps: report ambiguous record alignment or conflict and refuse certification of the affected join.
- Primary multiplicity exceeds secondary multiplicity: do not silently deduplicate, refill or drop primary rows.
- Secondary-only records: retain a separate surplus report and never append them to the authoritative population. Successful primary reconstruction must still report incomplete cross-source occurrence equivalence.
- Missing registry entry: the identity can be uniquely resolved while its coordinate remains unavailable.

The implementation can emit uniquely supported associations alongside unresolved ones, but the report must not label the complete table uniquely verified when any supported feature is unresolved. Preservation of a set is not sufficient: its order and multiplicities are also tested.

### 5.4 Limits that remain even after a successful check

Two consistently corrupted representations can agree. An incorrect record key can produce a misleading alignment. A permutation shared consistently by both sources is not identifiable without independent provenance. Exact comparison detects declared contradictions; it is not a universal corruption detector or an authenticity guarantee. A hash mismatch means bytes differ, not necessarily that scientific values are wrong. A registry coordinate can be physically wrong even when its association is exact.

## 6. Evidence plan and fixed success criteria

### Track A — implementation separation and conformance

Use one core with the Antwerp adapter and the explicit synthetic alternative adapter. All fixture specifications and expected outcomes are written before the producer is run; code fixes may follow failures but must be versioned and followed by the same full suite. Do not replace an inconvenient failure case or add outcome-selected tolerances.

Use a small, simple reference matcher enumerating exact candidate equalities as an oracle for constructed cases. It must not delegate to the production matcher. At very small dimensions, an independently enumerated injective-association oracle can check claimed uniqueness. This is a code-correctness oracle, not a competing state-of-the-art method.

Fourteen named test/evidence families are specified in `G1_TEST_MATRIX.csv`. G01–G12 cover controlled and transformation cases; G13 is frozen Antwerp parity; G14 is the DAE differential integration. Reuse previous tests where their exact inputs and assertions cover a requirement. Do not count an inherited test as a newly discovered scientific result.

Primary endpoints: number of false unique associations (must be zero on truth-known fixtures); correctness of ambiguity/conflict/unsupported statuses; zero alteration of authoritative row/partition/feature identities; complete reporting of surplus and missing registry information; and exact source-workflow array preservation. Timing and memory are descriptive only.

Counterexamples are retained. Failure of a required invariant prevents the corresponding portability claim. It does not retrospectively invalidate PR5D unless the investigation identifies a genuine defect in PR5D itself.

### Track B — backward compatibility on the existing Antwerp data

Load the hash-identical primary CSV and secondary JSON; do not use the saved mapping as an inference input. Compare new outputs with the frozen original reconstruction after canonical output normalization. Pin both source versions.

Required semantic agreement includes 44 active identities, 39 catalogue-backed active identities, the full primary-row order and multiplicities, 147 duplicated serialization groups of size two, the one separately reported surplus occurrence, calibration-only supported identity results at the explicitly identical row subset, and all original row/roster selections. The published missingness and receiver coverage distinctions remain unchanged.

Reuse the existing 2,495-message representation replay to check identical selected measurements, weights and predictions when the generic adapter is substituted. Do not refit or improve an estimator. Numeric tolerance for this existing floating-point readout is the pre-existing receipt's documented tolerance, to be pinned before execution; there is no new tolerance chosen from observed mismatches. Identity, feature and partition equality is exact, with no such numeric relaxation.

Byte equality is required for unmodified input/scientific-parent files; normalized semantic equivalence is the appropriate requirement for a new wrapper whose report paths and metadata differ. A schema refactor may not silently produce a new historical checksum for the original source.

### Track C — the one external-workflow integration

Use `Creating_files_LoRaWAN_dataset.ipynb` (MD5 `0d21a33bdc3501ba16cd989584bd344b`) from the supplied DAE deposit. The complete computational cells have been inspected during design; no cell was executed in this design stage.

The actual notebook filters on nonsentinel reception count, uses the first 72 columns as X, columns from position 75 onward as y, constructs HDOP separately, and performs a two-stage seed-42 train/validation/test split. Preserve exactly that recipe. Do **not** replace its rule with Paper A's in-range/finite-coordinate filter or our 16,612/2,495 populations. Do not silently change dependencies to force a historical byte claim.

1. Stage a hash-identical input at the notebook's expected filename in an isolated workspace. Keep its original source bytes. Run the computational cell as the reference producer with write access limited to that workspace and the common numerical environment recorded.
2. Reproduce the same operations in the integration route, maintaining original row handles in a parallel sidecar. Do not add identity fields to X, y or the source table.
3. Split the row-handle vector with the exact same two-stage routine, sizes, random state and returned order. Check X, y and HDOP separately against the source-cell outputs and against their source rows. The reference branch does not call the new core.
4. Run/attach the already verified correspondence and registry products without reordering the 72 original dimensions or replacing sentinel values. Keep unknown/inactive receiver attributes explicit.
5. Compare all nine exported X/y/HDOP train/validation/test products: shapes, feature/target names, numeric values, element order, alignment and sentinel locations. Within one fixed environment, require matching ordinary export bytes where the original writer settings are retained. Record both byte and parsed-value comparisons so formatting differences cannot hide numeric changes.
6. Demonstrate a bounded negative control: deliberately corrupt a copy of the row sidecar or swap distinct row associations and ensure the preservation checker refuses it. This is a controlled test copy, never a mutation of the source output.

No kNN/ExtraTrees retraining, augmentation search or new localization leaderboard follows. Preserving X/y and the exact ordered splits proves an added metadata channel did not change that preparation task. Existing project predictions already supply the downstream continuity instrument in Track B.

Expected sizes follow the executed source rule; record them, do not force them to our earlier calibration populations. The notebook's saved 55,375-row filter result is a prior stored output, not a new execution result. The 70/15/15 labels are nominal proportions; actual integer split sizes follow the source library's rounding.

**Permitted interpretation:** integration into a separately authored preparation workflow as executed here. **Not permitted:** independent adoption by the DAE authors; reproduction of their predictive results; authentication of unavailable historical exported arrays; or a second independent dataset. If the original environment/exports are unavailable, both branches run in the same declared present environment and that limitation is explicit.

### Why no new localization metric is required here

The purpose of G1 is to preserve a workflow while exposing reusable metadata, not to improve its predictor. A nonzero prediction change on a valid semantics-preserving adapter substitution is a potential regression, not a gain to advertise. Success includes exact equalities and correct refusals, alongside the already established practical consequences in PR5D.

## 7. Existing checks to reuse rather than reinvent

The design inspection read the original 97-line `rebuild_join.py`, its 26-line `test_join_contract.py`, the PR2 resource-contract test source, and all three DAE preparation cells. It did not execute them anew.

`test_join_contract.py` already exercises permuted identifier columns, a single RSSI mismatch, reception-absence mismatch, indistinguishable signatures, joint row permutation, transmitter-coordinate exclusion, and rejection of nonintegral RSSI under the Antwerp schema.

PR2's resource tests already exercise exact row order, same-count/different-row refusal, duplicate row-ID refusal, source hash checking, occurrence multiplicity, surplus handling, conflicting duplicate maps, nonbijective mapping, leading-zero identifiers, stable numerical-BS tie order, missing/nonfinite coordinates, hand-computed centroid behavior, and a uniform-RSSI-offset identity.

The existing `matches(a, b, rows)` kernel already accepts arrays and explicit row indices rather than Antwerp column names. The schema-specific parsing, alignment keys, sentinel handling and calibration selection are in its surrounding program. Therefore G1 is primarily separation and demonstrated reuse of an existing mechanism—not invention of an exact matcher.

G1 must preserve those scientific/semantic safeguards and adapt only interfaces. New needs are explicit second-schema operation, independently permuted views with preserved lineage, inactive-vs-ambiguous statuses, hash-collision-safe exact matching, broader canonicalization rejection, clean failure reports and the DAE differential sidecar. The test matrix marks this as reusable coverage, not newly passed tests.

## 8. Prior work and novelty boundary

Do not reopen the completed DAE/2024/2026 file inspection. Add only a compact attribution paragraph for the new portable claim. Schema/instance matching is established [S1]; provenance has domain-independent models [S2]; testing relations between transformed inputs/outputs is established metamorphic testing [S3]. G1 neither invents these ideas nor needs to benchmark an unrestricted family of schema matchers.

The claimed additional capability is **strict correspondence and experiment-preserving metadata attachment for compatible redundant representations, with explicit ambiguity and occurrence handling**, demonstrated with a general core and one externally authored preparation workflow. More general wording alone supplies little novelty. Successful implementation and integration primarily strengthen portability, precision and practical significance; do not assign an automatic increase in a novelty score.

A general-purpose fuzzy entity-resolution or schema-discovery claim would create new prior-work and empirical obligations and is explicitly prohibited under this phase.

## 9. Execution sequence and stopping rule

Use three implementation blocks after this design, not a new multi-epoch project:

| Block | Work | Exit condition |
|---|---|---|
| 1 | Extract the core; write adapters and truth-known fixtures; map inherited tests | Required unique/ambiguous/conflict behavior and input exclusion pass; no Antwerp counts/names in the core |
| 2 | Run frozen Antwerp parity and the two-branch DAE preparation integration; repeat outputs once | Exact identities and X/y/HDOP/ordered-partition equivalence; false-certification count zero; parent bytes unchanged |
| 3 | Record all outcomes and integrate one concise methods/result addition | Claims match success/failure evidence; main text remains centred on Paper A; one matching side-package |

This is a scope estimate, not a promised wall-clock completion time or background task. Stop after these acceptance conditions or an explicit, preserved failure. No seed search, new dataset procurement, new fitter or additional baseline family is authorized by failure to produce a more prestigious journal prospect.

If portability is achieved but DAE integration fails, retain the core/testing gain and report the specific integration limitation. If DAE integration succeeds but the core remains schema-bound, claim workflow integration only. If both succeed, claim both; never describe them as cross-deployment validation. If neither produces meaningful added functionality, retain PR5D rather than inflate the title or add a new scope indefinitely.

## 10. Manuscript footprint and unchanged commitments

Target editorial footprint: roughly 500–800 added main-text words and one compact table, integrated by replacing repetitive material where possible; a single supplementary methods/results section with the fuller fixtures and source-workflow comparison. These are planning budgets, not mandatory page limits. Do not bury decisive failure cases, information requirements or ambiguity behavior in the supplement.

Suggested post-success wording:

> We separate exact receiver association from dataset-specific parsing and evaluate a common core on declared schemas and controlled ambiguity cases. Integration into a separately authored Antwerp preparation workflow preserves its feature values, targets and ordered partitions while adding receiver metadata and explicit lineage sidecars. This establishes portable construction and workflow compatibility for conforming representations, not cross-dataset localization performance or independent adoption.

The original main title can remain. Avoid escalating to “a universal IoT benchmark framework.” Preserve all original/adverse results and authorship declarations. The assessment's small NLLS wording fix (“across all 2,487 survivors”) can be incorporated with the eventual document update; it is not part of the new science. Do not change the author-approved exact AI declaration without explicit authorization, regardless of editorial suggestions concerning its product name or grammar.

No GitHub/Zenodo publication, repository change, journal submission, email or Library mutation is included in this design or automatically authorized by it.

## 11. Journal strategy as of 21 September 2026

**Working primary candidate: Computer Networks. Alternative: Wireless Networks. TMC is a stretch rather than the design target; TWC is not recommended for this contribution.** These are fit judgments, not acceptance forecasts or a hierarchy inferred from IoT's rejection.

TMC's official scope includes mobile data/knowledge management, reliability and location-sensitive applications and asks for a clear mobile-systems contribution [J1]. It is closer than TWC to this resource's centre. Nevertheless, making an adapter schema-independent and integrating one same-dataset workflow does not by itself create a major mobile-systems result. Do not enlarge G1 to manufacture that result.

TWC's author guidelines require a central wireless-communications advance in which wireless-channel characteristics play a prominent role [J2]. A general data/provenance adapter does not become such an advance merely because its case data are LoRaWAN. Improving the channel model or a coordinate-recovery method would be a different project. Its current prior-rejection policy requires disclosure of a prior journal and manuscript ID and excludes manuscripts already rejected by two different journals [J2]. This is a journal-specific sequencing caveat, not a reason to choose it for an ill-fitting paper.

Computer Networks explicitly accommodates datasets and open-source software microarticles alongside research papers [J3]. This makes the network-resource/evaluation centre plausible; it does **not** mean the current full manuscript is already a compliant microarticle. A full research/case-study framing should be evaluated first. The latest article-type-specific author fees and SCIE record were not independently established through accessible primary pages in this design; retain that submission gate. Its ScienceDirect pages returned HTTP 403. A shop subscription listing is not proof of zero author charges.

Wireless Networks' publisher describes research, experience and management in wireless networking [J4]. Its official pages confirm SCIE indexing [J5] and a subscription option with no APC [J6]. That is the directly verified budget-compatible alternative; it is not a promise of a lower novelty standard. Existing lack-of-funding and independent-researcher status must not be replaced with assumed institutional APC support.

IEEE traditional publication is not automatically zero-cost: Computer Society author guidance lists possible mandatory overlength charges [J7]. Current draft page counts are not IEEE typeset page counts. Do not infer fees from “11 manuscript pages plus supplement.” This design does not approve any payment or select an unaffordable OA route.

A past rejection does not logically cap the quality or destination of a revised paper. Equally, completing more stages or adding general symbols does not establish that a higher-tier venue is now the best target. Choose the venue from the final demonstrated contribution without allowing prestige to redefine the bounded phase.

## 12. Evidence and references

**R1.** Supplied *Paper A PR5D: improvement, novelty and suitability for Internet of Things*, assessment 21 September 2026; exact uploaded file and hash in `INPUTS_AND_SOURCES.json`. Relevant sections: specific originality, external generality, optional integration, and finite remaining actions. No new full manuscript peer review was undertaken for this design.

**Local design sources.** Frozen PR5D complete review bundle; original `rebuild_join.py` and `test_join_contract.py`; PR2 `test_resource_contract.py`; supplied `Creating_files_LoRaWAN_dataset.ipynb`. Code was inspected for planning and reuse mapping, not executed. Exact enclosing/member hashes are in `INPUTS_AND_SOURCES.json`.

**S1.** E. Rahm and P. A. Bernstein, *A Survey of Approaches to Automatic Schema Matching*, The VLDB Journal 10(4), 2001, DOI 10.1007/s007780100057. Author-group bibliographic/abstract page inspected; not a newly completed exhaustive matching-literature review.

**S2.** W3C, *PROV-DM: The PROV Data Model*. Official recommendation consulted for the already established domain-independent provenance context.

**S3.** T. Y. Chen et al., *Metamorphic Testing: A Review of Challenges and Opportunities*, ACM Computing Surveys 51(1), article 4, 2018, DOI 10.1145/3143561. Author/institutional record consulted for terminology and attribution; no claim of inventing the testing approach.

**J1–J7.** Official publisher/society pages, URLs and access outcomes are listed in `INPUTS_AND_SOURCES.json`. Venue judgments in this document are analysis of scope against the current contribution, not journal decisions. No impact-factor, quartile, acceptance-rate or publication-speed claim is used.
