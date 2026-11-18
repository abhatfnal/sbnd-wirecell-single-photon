# SP BDTs on WCL1116: four-model development summary

Date: 2026-11-18. Campaign `development_wcl1116_v1` (WCLocal2026Nov16-Aurora, WCT 0.38.0, DV2-MAX `aurora_space`).
- Every model is **`…_DEV_DO_NOT_DEPLOY`**. Every number is an Aurora **DEVELOPMENT HOLDOUT** result, not an
  independent end-to-end measurement (`AURORA_UMBRELLA_MODEL_TRAINING_AND_EVALUATION_POLICY.md`).
- **FermiGrid evaluation: not used.** No FermiGrid product was read. No threshold, vertex mode or final model was
  chosen, and nothing was tuned.

Detailed reports:
- SP numu / SP ncpi0: `SP_BDT_WCL1116_DEVELOPMENT_RESULTS.md` (commit a6556cf; not reopened here);
- SP other: `SP_OTHER_WCL1116_DEVELOPMENT_REPORT.md`;
- SP nue: `SP_NUE_WCL1116_DEVELOPMENT_REPORT.md`.

## 1. Four-model matrix

| model | inputs / depth / trees | upstream inputs | status | mode | holdout rows +/− | legacy AUC | dev AUC | dev − legacy | train/holdout gap | export: Python / C++ |
|---|---|---|---|---|---|---:|---:|---:|---:|---|
| **SP numu** | 73 / 5 / 300 | `numu_score`, `numu_1_score` (SHIPPED_CONTROL) | DEVELOPED | split | 8,821 / 19,066 | 0.9584 | 0.9759 | +0.018 | 0.019 | PASS / bit-identical |
| | | | | snap | 8,745 / 19,240 | 0.9536 | 0.9739 | +0.020 | 0.019 | PASS / bit-identical |
| **SP ncpi0** | 45 / 6 / 400 | 15 νe L1 scores (as stored); Policy B | DEVELOPED | split | 8,820 / 4,790 | 0.8485 | 0.8992 | +0.051 | 0.089 | PASS / bit-identical |
| | | | | snap | 8,744 / 4,770 | 0.8469 | 0.8974 | +0.051 | 0.091 | PASS / bit-identical |
| **SP other** | 146 / 5 / 215 | `numu_score`, `numu_1_score`, `numu_2_score`, `cosmict_10_score`; 60 cosmic-tagger inputs | **BLOCKED ONLY ON TRANSFER EXECUTION** (beam-off training half) | both | MC census only: 8,821 / 7,524 (split) | — | — | — | — | — |
| **SP nue** | 56 / 5 / 300 | none | DEVELOPED | split | 8,871 / 106,808 | 0.9176 | **0.9588** | **+0.041 ± 0.0008** | 0.020 | PASS / bit-identical |
| | | | | snap | 8,791 / 106,810 | 0.9143 | **0.9524** | **+0.038 ± 0.0009** | 0.024 | PASS / bit-identical |

**ROC-equivalent diagnostic** (DEVELOPMENT ROC-EQUIVALENT DIAGNOSTIC — NOT ROUND2 CUT), split-move. Legacy at its
historical cut, then the new model at equal signal efficiency and at equal background acceptance:

| model | legacy: signal eff. / bkg acc. | new, same signal eff.: bkg acc. | new, same bkg acc.: signal eff. |
|---|---|---|---|
| SP numu (0.4) | 82.4 % / 6.27 % | 2.91 % | 90.3 % |
| SP ncpi0 (−0.05) | 51.7 % / 10.4 % | 5.0 % | 71.4 % |
| SP other (0.2) | — | — | — |
| SP nue (−1.0) | 78.4 % / 13.4 % | 5.4 % | 91.6 % |

**Retraining benefit.**
- SP nue and SP other: by the pre-registered rule (`tools/wcl1116_mode_compare.py`).
- SP numu and SP ncpi0: by the earlier results; the rule was not re-run for them.

| model | verdict |
|---|---|
| SP numu | retraining beneficial (+0.018 / +0.020 AUC; ROC point above) |
| SP ncpi0 | retraining beneficial (+0.051; largest gain); more NC π⁰ negatives: SOME BENEFIT LIKELY |
| SP other | **not measured**: no fit without the beam-off component |
| SP nue | **RETRAINING CLEARLY BENEFICIAL** (both modes ≥ 0.010 and > 40 σ) |

### 1a. C++ equivalence

All six development models, numu / ncpi0 / nue × 2 modes, pass:
- TMVA::Reader == toolkit `TmvaGradForest`, bit-identical on 3,310 / 3,310 fixture rows per model;
- C++ vs Python ≤ 4.4e-16;
- NaN → −999; the swapped order is refused;
- 0 decision flips.

Runs: numu / ncpi0 in PBS 9099556 (commit a6556cf); SP nue in PBS 9100172
(`validation/cpp_export_equivalence_wcl1116_<mode>_nue.json`). SP other has no model to export yet.

## 2. Inputs (all Aurora training side)

| sample | files | events | used by |
|---|---:|---:|---|
| `wcl1116-aurora-ncdr` | 17,604 | 26,745 | all four |
| `wcl1116-aurora-bnb` | 11,874 | 626,441 | all four |
| `wcl1116-aurora-nuecc` | 61,238 (of 61,252 units; 11 PARTIAL + 3 FAIL excluded) | 268,783 | SP nue |
| `wcl1116-fg-beamoff-train` | 558 frozen odd-run pairs (membership only) | — | SP other, once staged |

## 3. Vertex mode (development evidence only; no decision)

| evidence | split-move vs snap |
|---|---|
| preselected signal within 1 cm of the true vertex (NC Δ / BNB) | 0.571 vs 0.516 / 0.489 vs 0.400 |
| preselected-signal ceiling, NC Δ | 0.661 vs 0.654 |
| matched-candidate dev AUC, snap − split: numu / ncpi0 / nue | −0.0015 ± 0.0004 / −0.0010 ± 0.0015 / **−0.0059 ± 0.0006** |
| matched-candidate legacy AUC, snap − split: numu / ncpi0 / nue | −0.0034 / −0.0012 / −0.0034 |

- Every measured SP model is equal or better on split-move, and SP nue shows the clearest difference.
- This favours split-move as the SP input domain. **The vertex mode stays a collaboration decision**, made with
  Xuyang's upstream-BDT and Matteo's downstream studies. Nothing is frozen here.

## 4. Final retraining requirements (Task 18)

| model | final reconstruction domain | frozen upstream | extra data | open sample questions | final training now? |
|---|---|---|---|---|---|
| **SP numu** | needed (vertex mode; cosmic-boundary production: **potentially affected** through `numu_score`) | **νμ final + `numu_1_score`** (Xuyang/Matteo), recomputed on the final training CAFs | — | signal statistics (8.8k training positives) | **no** |
| **SP other** | needed (**definitely retrain** after a cosmic-boundary change: 60 / 146 direct inputs + `numu_score`) | **νμ**, as for SP numu, trained on the same frozen `numu_score` | **refreshed beam-off training half** staged and verified (558 pairs), and again on the final reconstruction | EXT share (old reco: 3.1 % of negatives); component proportions are not source-established | **no** |
| **SP ncpi0** | needed (likely insensitive to the cosmic boundary) | 15 νe L1 stay as stored, or are frozen first; Policy B | more NC π⁰ negatives would help (learning-curve gain +0.007 per doubling) | whether the νe CC sample's 374 NC π⁰ rows enter | **no** |
| **SP nue** | needed (likely insensitive to the cosmic boundary) | none | the final νe CC + NC Δ + BNB lists | class weighting (thesis ratio 1 : 4, here 1 : 12); signal statistics | **no** |

**Common to all four:**
1. the final reconstruction domain (vertex mode + toolkit + DL bundle, after the cosmic-boundary production);
2. the frozen specs re-run unchanged on its training lists;
3. export with Python and C++ equivalence (the machinery is verified);
4. the validation-only joint threshold freeze;
5. only then, FermiGrid evaluation.

## 5. Final-training readiness

| model | target known | refreshed training data | upstream frozen | development model | blocking item | READY FOR FINAL TRAINING |
|---|---|---|---|---|---|---|
| SP numu | yes (thesis + exact XML fingerprint) | yes (WCL1116 NC Δ + BNB) | **no** (νμ) | DONE, both modes | upstream νμ, final reco | **NO** |
| SP other | yes (thesis + exact fingerprint; documented assumption A4) | MC yes; **beam-off training half not on Aurora** | **no** (νμ) | not trained | transfer execution, upstream νμ, final reco | **NO** |
| SP ncpi0 | yes | yes | νe L1 fixed (stored) | DONE, both modes | final reco | **NO** |
| SP nue | yes (thesis p.133 + 300-tree XML) | yes (WCL1116 νe CC complete) | not needed | DONE, both modes | final reco | **NO** |
