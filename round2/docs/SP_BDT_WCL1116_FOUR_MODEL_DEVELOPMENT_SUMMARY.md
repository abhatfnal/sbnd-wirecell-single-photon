# SP BDTs on WCL1116: four-model development summary

Dates: 2026-11-18 (SP nue); completed 2026-11-19 (SP other). Campaign `development_wcl1116_v1` (WCLocal2026Nov16,
WCT 0.38.0 `c935e30d`, DV2-MAX `aurora_space`).
- Every model is **`…_DEV_DO_NOT_DEPLOY`**. Every number is an Aurora **DEVELOPMENT HOLDOUT** result, not an
  independent end-to-end measurement (`AURORA_UMBRELLA_MODEL_TRAINING_AND_EVALUATION_POLICY.md`).
- **FermiGrid evaluation performance: not used.** The only FermiGrid-derived input is the pre-frozen odd-run beam-off
  TRAINING half (SP other).
- No threshold, vertex mode or final model was chosen, and nothing was tuned.

**WCL1116 is now a COMPLETE DEVELOPMENT DOMAIN: all four SP classifiers developed in both vertex modes. It is not the
intended final training domain.** Haiwang's next production is expected to introduce the measured non-box / effective
detector boundary in the cosmic tagger.

Detailed reports:
- SP numu / SP ncpi0: `SP_BDT_WCL1116_DEVELOPMENT_RESULTS.md` (commit a6556cf; not reopened);
- SP other: `SP_OTHER_WCL1116_DEVELOPMENT_REPORT.md`;
- SP nue: `SP_NUE_WCL1116_DEVELOPMENT_REPORT.md`;
- toolkit provenance (`0.38.0` vs `HEAD-0.38.0`): `WCL1116_TOOLKIT_PROVENANCE_NOTE.md`.

## 1. Four-model matrix

| model | split legacy | split dev | snap legacy | snap dev |
|---|---:|---:|---:|---:|
| SP numu | 0.958 | 0.976 | 0.954 | 0.974 |
| SP ncpi0 | 0.848 | 0.899 | 0.847 | 0.897 |
| SP other | **0.840** | **0.915** | **0.836** | **0.912** |
| SP nue | 0.918 | 0.959 | 0.914 | 0.952 |

All AUCs are AURORA DEVELOPMENT HOLDOUT, on identical holdout rows for legacy and dev.

| model | inputs / depth / trees | upstream inputs | mode | holdout rows +/− | dev − legacy | train/holdout gap | export: Python / C++ |
|---|---|---|---|---|---:|---:|---|
| **SP numu** | 73 / 5 / 300 | `numu_score`, `numu_1_score` (SHIPPED_CONTROL) | split | 8,821 / 19,066 | +0.018 | 0.019 | PASS / bit-identical |
| | | | snap | 8,745 / 19,240 | +0.020 | 0.019 | PASS / bit-identical |
| **SP ncpi0** | 45 / 6 / 400 | 15 νe L1 scores (as stored); Policy B | split | 8,820 / 4,790 | +0.051 | 0.089 | PASS / bit-identical |
| | | | snap | 8,744 / 4,770 | +0.051 | 0.091 | PASS / bit-identical |
| **SP other** | 146 / 5 / 215 | `numu_score`, `numu_1_score`, `numu_2_score`, `cosmict_10_score` (SHIPPED_CONTROL); 59 direct cosmic-tagger inputs | split | 8,821 / 7,748 (EXT 224) | **+0.076 ± 0.0025** | 0.053 | PASS / bit-identical |
| | | | snap | 8,745 / 7,757 (EXT 225) | **+0.076 ± 0.0028** | 0.055 | PASS / bit-identical |
| **SP nue** | 56 / 5 / 300 | none | split | 8,871 / 106,808 | +0.041 ± 0.0008 | 0.020 | PASS / bit-identical |
| | | | snap | 8,791 / 106,810 | +0.038 ± 0.0009 | 0.024 | PASS / bit-identical |

**ROC-equivalent diagnostic** (DEVELOPMENT ROC-EQUIVALENT DIAGNOSTIC — NOT ROUND2 CUT), split-move. Legacy at its
historical cut, then the new model at equal signal efficiency and at equal background acceptance:

| model | legacy: signal eff. / bkg acc. | new, same signal eff.: bkg acc. | new, same bkg acc.: signal eff. |
|---|---|---|---|
| SP numu (0.4) | 82.4 % / 6.27 % | 2.91 % | 90.3 % |
| SP ncpi0 (−0.05) | 51.7 % / 10.4 % | 5.0 % | 71.4 % |
| SP other (0.2) | 57.4 % / 11.4 % | **3.28 %** | **78.8 %** |
| SP nue (−1.0) | 78.4 % / 13.4 % | 5.4 % | 91.6 % |

**Development verdicts.**
- SP other and SP nue: the pre-registered rule (`tools/wcl1116_mode_compare.py`, fixed 2026-11-17 before either fit):
  - BENEFICIAL: both modes gain ≥ 0.010 and > 3 σ;
  - COMPETITIVE: both ≤ 0.002;
  - otherwise NEUTRAL.
- SP numu and SP ncpi0: their 2026-11-17 results; the rule was not re-run for them.

| model | development verdict |
|---|---|
| SP numu | retraining beneficial (+0.018 / +0.020 AUC; background acceptance × 0.46 at equal efficiency) |
| SP ncpi0 | retraining beneficial (+0.051); more NC π⁰ negatives: SOME BENEFIT LIKELY |
| SP other | **RETRAINING CLEARLY BENEFICIAL** (+0.076 in both modes, 30 σ / 27 σ; every negative component reduced, EXT included) |
| SP nue | **RETRAINING CLEARLY BENEFICIAL** (+0.041 / +0.038, > 40 σ) |

### 1a. C++ equivalence

TMVA::Reader == toolkit `TmvaGradForest`, bit-identical on 3,310 / 3,310 fixture rows per model; C++ vs Python
≤ 4.4e-16; NaN → −999; swapped order refused; 0 decision flips. Runs:
- numu / ncpi0: PBS 9099556 (a6556cf);
- nue: PBS 9100172;
- other: PBS 9102928.

Summaries: `validation/cpp_export_equivalence_wcl1116_<mode>_<model>.json`.

## 2. Inputs (all training side)

| sample | files | events | stored `wct_version` | used by |
|---|---:|---:|---|---|
| `wcl1116-aurora-ncdr` | 17,604 | 26,745 | `0.38.0` | all four |
| `wcl1116-aurora-bnb` | 11,874 | 626,441 | `0.38.0` | all four |
| `wcl1116-aurora-nuecc` | 61,238 (of 61,252 units; 11 PARTIAL + 3 FAIL excluded) | 268,783 | `0.38.0` | SP nue |
| `wcl1116-fg-beamoff-train` | 558 (verified 558 / 558; list sha256 `8f2ea601…`) | 26,418 | `HEAD-0.38.0` | SP other (EXT, approved exception) |

`0.38.0` and `HEAD-0.38.0` are the two exact stamps of the same toolkit build, `c935e30d44a09bf208f6de2c2968171b01efd63d`
(tag 0.38.0, 0 dirty cfg files): campaign-level evidence, approved by Avinay (`WCL1116_TOOLKIT_PROVENANCE_NOTE.md`).

## 3. Vertex mode (development evidence only; no decision)

| evidence | split-move vs snap |
|---|---|
| preselected signal within 1 cm of the true vertex (NC Δ / BNB) | 0.571 vs 0.516 / 0.489 vs 0.400 |
| preselected-signal ceiling, NC Δ | 0.661 vs 0.654 |
| SP other EXT rows | 509 vs 508 |
| matched-candidate dev AUC, snap − split: numu / ncpi0 / other / nue | −0.0015 ± 0.0004 / −0.0010 ± 0.0015 / **−0.0029 ± 0.0010** / **−0.0059 ± 0.0006** |
| matched-candidate legacy AUC, snap − split: numu / ncpi0 / other / nue | −0.0034 / −0.0012 / −0.0036 / −0.0034 |

- All four SP models are equal or better on split-move. SP nue and SP other show the clearest differences, about 10 σ
  and 3 σ.
- This favours split-move as the SP input domain. **The vertex mode stays a collaboration decision**, made with
  Xuyang's upstream-BDT and Matteo's downstream studies. Nothing is frozen here.

## 4. Final retraining requirements

| model | final reconstruction domain | frozen upstream | extra data | open sample questions | final training now? |
|---|---|---|---|---|---|
| **SP numu** | needed (vertex mode; the boundary change is **potentially relevant** through `numu_score`) | **νμ final + `numu_1_score`** (Xuyang/Matteo), recomputed on the final training CAFs | — | signal statistics (8.8k training positives) | **no** |
| **SP other** | **MUST be retrained** in the final domain: 59 direct cosmic-tagger inputs + `cosmict_10_score` (60 / 146), and `numu_score`, built mostly from cosmic-tagger outputs | **νμ**, as for SP numu, trained on the same frozen `numu_score` | the beam-off training half **reprocessed in the final reconstruction**, staged and verified again (same route and verifier) | EXT share (3.3 % of negatives here); component proportions are not source-established | **no** |
| **SP ncpi0** | needed (likely insensitive to the boundary) | 15 νe L1 stay as stored, or are frozen first; Policy B | more NC π⁰ negatives would help (+0.007 per doubling) | whether the νe CC sample's 374 NC π⁰ rows enter | **no** |
| **SP nue** | needed (likely insensitive to the boundary) | none | the final νe CC + NC Δ + BNB lists | class weighting (thesis ratio 1 : 4, here 1 : 12); signal statistics | **no** |

**Common to all four:**
1. the final reconstruction domain: vertex mode, toolkit and DL bundle, after the boundary production;
2. the frozen specs re-run unchanged on its training lists;
3. export with Python and C++ equivalence;
4. the validation-only joint threshold freeze;
5. only then, FermiGrid evaluation.

**Why finish all four now** although another production is coming:
- It gives the complete four-classifier SBND development baseline, against which the final domain is compared.
- It validates every piece of the final procedure end to end: target definitions, sample and staging route, verifier,
  firewall exception, tables, training, legacy controls, export and C++ readers.
- It measures, before the final production, that SBND retraining is beneficial for every SP model, and clearly so for
  SP other and SP nue by the pre-registered rule.

The final retraining is then a re-run of a validated pipeline, not new development.

## 5. Final-training readiness

| model | target known | refreshed training data | upstream frozen | development model | blocking item | READY FOR FINAL TRAINING |
|---|---|---|---|---|---|---|
| SP numu | yes (thesis + exact XML fingerprint) | WCL1116 (development domain) | **no** (νμ) | DONE, both modes | upstream νμ, final reco | **NO** |
| SP other | yes (thesis + exact fingerprint; documented assumption A4) | WCL1116 MC + verified beam-off half (development domain) | **no** (νμ) | DONE, both modes | upstream νμ, final reco (boundary), beam-off in the final reco | **NO** |
| SP ncpi0 | yes | WCL1116 (development domain) | νe L1 fixed (stored) | DONE, both modes | final reco | **NO** |
| SP nue | yes (thesis p.133 + 300-tree XML) | WCL1116 incl. νe CC (development domain) | not needed | DONE, both modes | final reco | **NO** |
