# SP BDTs on WCL1116: full-development plan (pre-registered)

Date: 2026-11-20. Branch `round2/sp-bdt-wcl1116-full-development-20261120`, based on `92a1b1768ff3d5585c5b741ffa85a3b522b6e9b8`.
This file and `sp_retrain/devstudy.py` were **committed before any study variant was fitted**. The rules below are
not changed after seeing a result.

**Context only, never an input.** The EAF frozen-selection replay showed the same inherited selection going from
833 / 12427 (6.70 %) on the corrected old reconstruction to 1938 / 12427 (15.60 %) on WCL1116. Selected generic-BNB
non-signal rose from 282 to 685. The question is whether SBND-specific classifiers keep the recovered signal while
restoring background rejection. No EAF or FermiGrid event, number or selection is used to choose anything here.

**Frozen reference.** The WCL1116 development models of `92a1b17` are not modified; their holdout AUCs are in
`SP_BDT_WCL1116_FOUR_MODEL_DEVELOPMENT_SUMMARY.md`.

## 1. Partitions

| role | definition |
|---|---|
| EXISTING DEVELOPMENT HOLDOUT (`test`) | unchanged outer split: MC odd subrun; EXT `run % 4 == 1` |
| FIT (`fit`) | existing training side, nested-validation hash ≥ 0.20 |
| NESTED VALIDATION (`nval`) | existing training side, hash < 0.20 |

**Rule `nested_v1`** (`sp_retrain.devstudy.nested_roles`):
- The unit is `(sample, run, subrun)`, the unit of the outer split. Every candidate of an event, and every event of a
  subrun, stays together.
- EXT files all carry art subrun 1, so an EXT unit is a run, as in the outer EXT split.
- `u = int(sha256("nested_v1|<sample>|<run>|<subrun>")[:8], 16) / 2**32`; NESTED VALIDATION if `u < 0.20`.

Consequences:
- The rule depends only on the unit, so it is identical in split-move and snap, and per sample (sample boundaries are
  preserved).
- No outer-holdout row changes role.
- EXT has few runs: of 29 training-side runs with usable rows, 2 fall in nested validation (20 rows). EXT acceptance is
  therefore also shown on the existing holdout, as a diagnostic only.

None of these partitions is an independent evaluation.

## 2. Common fitting rule

Every variant uses its model's frozen WCL1116 development spec unchanged: features, order, hyperparameters, seed,
`base_score` 0, rounds. It is **fitted on FIT only**; `FIT_BASELINE` is the unchanged spec fitted on FIT.

The study variables are only:
- the row weights (SP nue);
- the negative FIT sample (SP ncpi0);
- the input set (diagnostic ablations).

There is no tuning, no early stopping and no threshold choice.

## 3. SP nue weighting study

| variant | total negative : positive training weight |
|---|---|
| `UNWEIGHTED_BASELINE` | natural, about 12 : 1 (all weights 1) |
| `THESIS_PRIOR_APPROX` | 4 : 1 (thesis 100,958 : 24,936 = 4.05) |
| `BALANCED_STRESS_TEST` | 1 : 1 |

Weights are per class and normalised to mean 1, so XGBoost's absolute regularisation (`min_child_weight`, `gamma`)
keeps its scale.

**Reported, on NESTED VALIDATION:**
- ROC and PR AUC;
- the FIT − validation gap;
- calibration: reliability of sigmoid(margin), Brier score, per-class margin quantiles;
- signal efficiency at the legacy background acceptance, and background acceptance at the legacy signal efficiency
  (legacy XML at −1.0 on the same rows);
- the score correlation with the unweighted model;
- top-feature stability.

Then, separately, the same on the existing holdout.

**Recommendation rule:**
- `UNWEIGHTED_BASELINE` stays the development choice **unless** a weighted variant improves NESTED-VALIDATION ROC AUC by
  ≥ 0.002 **in both modes** and does not raise the background acceptance at the legacy signal efficiency in either
  mode.
- A pure calibration / prior shift (a monotone change of the score) is not a reason to weight. Thresholds are set later
  on validation, which absorbs it.
- No final Round-2 weighting is chosen.

## 4. SP ncpi0 negative statistics

1. **Audit** the about 374 NC π⁰-labelled rows of `wcl1116-aurora-nuecc` (provenance, topology, selection bias,
   target definition, duplication with BNB).
   - They are used only if source-compatible: drawn from an unbiased NC π⁰ population in an environment like the
     training BNB, satisfying the thesis target, and not duplicating BNB.
   - A label match alone is not enough.
2. **Learning curve on NESTED VALIDATION.** The negative FIT events are subsampled at 1/8, 1/4, 1/2 (seeds 1–3); f = 1
   is `FIT_BASELINE`. All positives are kept.
3. **Rule:**
   - `MORE NCPI0 STATISTICS WORTH REQUESTING` if the gain from f = 1/2 to 1, mean over seeds, is ≥ 0.004 AUC and more
     than 3 × its seed sd, in both modes;
   - otherwise `CURRENT SAMPLE ADEQUATE`.
   - If the extra sample fails the audit: `AVAILABLE EXTRA SAMPLE NOT SOURCE-COMPATIBLE`, together with the
     learning-curve result.

## 5. Diagnostic ablations (robustness, never candidate models)

Families come from the audited feature lists (`config/features/*_inputs_v0.json`, `kind` and `upstream.family`) and the
toolkit-source audit of `cosmic_tagger()` (`SP_BDT_WCL1116_DEVELOPMENT_RESULTS.md` §11):

| model | variant | removed |
|---|---|---|
| SP numu | `A_FULL` | — (73) |
| | `B_NO_FINAL_NUMU_SCORE` | `numu_score` |
| | `C_NO_UPSTREAM_NUMU_FAMILY` | every `upstream_score` input: `numu_score`, `numu_1_score` |
| SP other | `A_FULL` | — (146) |
| | `B_NO_COSMIC_TAGGER_DIRECT` | the 59 `cosmict_*` / `cosmic_*` reco inputs |
| | `C_NO_UPSTREAM_NUMU_FAMILY` | the 4 `upstream_score` inputs of the νμ BDT scorer: `numu_score`, `numu_1_score`, `numu_2_score`, `cosmict_10_score` |
| | `D_NO_COSMIC_NO_UPSTREAM` | both (63) |

**Reported, on NESTED VALIDATION:**
- ROC and PR AUC;
- background acceptance at the legacy signal efficiency, and signal efficiency at the legacy background acceptance;
- SP other only: per-component acceptance (EXT, dirt, NC without π⁰, out-of-FV, cosmic MC). For EXT, also the existing
  holdout, with binomial uncertainty;
- Spearman correlation with the full model;
- top-feature redistribution;
- migration of rows at the equal-efficiency operating point.

## 6. Operating-point machinery (no threshold frozen)

Per model, on NESTED VALIDATION and with the `FIT_BASELINE` model:
- the legacy historical cut;
- the new model at equal legacy signal efficiency, and at equal legacy background acceptance;
- the full ROC and PR tables;
- a monotonic threshold table with component acceptances.

**Joint four-cut evaluator.**
- Applies numu → other → ncpi0 → nue in production order to every preselected NESTED-VALIDATION row of every sample.
- A row with a non-finite input scores −999 and fails, as in production.
- Grid: per model, thresholds at its own signal efficiency 0.80 / 0.85 / 0.90 / 0.95 / 0.98 / no cut.
- Reported per grid point:
  - NC Δ signal efficiency, total and by truth topology;
  - BNB background acceptance, with its components;
  - EXT and νe CC acceptance.
- The Pareto front is shown, and **no threshold vector is chosen**.

**Truth topology.**
- Established NC Δ analysis definition: post-FSI primaries `rec.mc.nu.prim` with pdg 2212 and KE > 35 MeV; 0p, 1p,
  ≥ 2p.
- Matched to the `T_match` partner by pdg, energy and vertex.
- Δ0 / Δ+ is reported descriptively, from the struck nucleon of NC resonances.

## 7. Vertex modes

Every study runs in split-move and snap. Whether weighting, ablations or operating points change the qualitative
split-move preference is reported; no mode is frozen.

## 8. Final-domain rerun

There is a campaign template `round2_final_reco_candidate`. It refuses to run unless every provenance field is
explicitly set (`SP_BDT_FINAL_DOMAIN_RERUN_CONTRACT.md`).
