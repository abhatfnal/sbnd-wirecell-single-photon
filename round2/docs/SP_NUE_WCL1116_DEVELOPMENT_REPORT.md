# SP nue on WCL1116: development report

Date: 2026-11-18. Campaign `development_wcl1116_v1`; branch `round2/sp-other-nue-wcl1116-development-20261117`.

**Status: DEVELOPED (both vertex modes, `…_DEV_DO_NOT_DEPLOY`). Retraining verdict: RETRAINING CLEARLY BENEFICIAL.**
- Every number here is an Aurora **DEVELOPMENT HOLDOUT** result (odd subruns), conditional on an upstream DL vertex
  trained on Aurora events. None is an independent end-to-end measurement
  (`AURORA_UMBRELLA_MODEL_TRAINING_AND_EVALUATION_POLICY.md`).
- No FermiGrid product was read. No threshold, vertex mode or final model was chosen. SP numu and SP ncpi0 were not
  touched.

## 1. νe CC production (Task 9)

Haiwang's `WCLocal2026Nov16-Aurora` νe CC (`full/nuecc`, 8 nodes, resume job 9097990):
- every node reported `pool done` by 01:31Z on 2026-11-18, and its finish line in `nodes.log` by 01:42Z;
- of 61,252 units: **61,238 OK, 11 PARTIAL, 3 FAIL** (`step2 … no complete Wire-Cell event`); 0 without a status.

The census and list (`tools/make_refresh_list.py`) ran read-only in PBS 9100111 (debug, 2 nodes,
`neutrinoGPU::WireCell_aurora`, 02:33–02:58Z).
- It refuses to write a list unless every unit has a final status; here `complete: true`.
- The selection rule is the same as for NC Δ and BNB: status OK, both validations PASS, both trees merged. So the
  sample boundary is the **whole completed production** under a rule fixed before it finished, not a chosen subset.

| item | value |
|---|---|
| units listed / OK / PARTIAL / FAIL | 61,252 / 61,238 / 11 / 3 |
| files in the training list | **61,238** (list sha256 `ca9ebd3b…`) |
| CAF events (= Wire-Cell events, both trees) | 268,783 |
| excluded | 14 units, 63 CAF events (0.02 %), listed in `manifests/wcl1116_dev_v1/inputs_nue.json` |
| file manifest | `manifests/wcl1116_dev_v1/manifest_wcl1116-aurora-nuecc.tsv.gz` (content sha256 `1290ebfd…`, 440.5 GB) |
| pair list | `full/nuecc-pairs.tsv` sha256 `b1eb012e…` |
| table builds (both trees) | 0 errors; 265,367 candidates; `wct_version` `0.38.0` only; 19 / 14 files with an unreadable label branch (split / snap); 1,295 s / 1,273 s at 160 processes |

The census records the list under its `.tmp` name, written before an atomic rename. The path was corrected after the
sha256 was checked to be identical (`renamed_from_tmp_after_census`).

## 2. Source definition (Task 10): uniquely established

| field | source | dev spec |
|---|---|---|
| target | thesis p.133: "trained on 100,958 νe CC background events and 24,936 signal events and uses 56 variables"; Fig. 5.10 caption: "Background includes only νe CC background events" | negative = `nueCCBkg` |
| background FV | the per-BDT training counts sum to 97,580 + 27,377 + 37,205 + 100,958 = 263,120 (p.127), so the classes are disjoint. Out-of-FV belongs to SP other, and νe CC means in the 3 cm FV | not signal, \|pdg\| 12, CC, true vertex in the 3 cm FV (`cuts.h` 0100d4b6:2856) |
| positive | the inclusive single-photon signal shared by the four BDTs (p.127) | `T_match` partner with `sp_signal`, all 5 categories; signal takes precedence |
| rows | after preselection (p.127, p.134) | as for the siblings |
| inputs | 56 `shw_sp_*`, XML order; no classifier output | `single_photon_nue_inputs_v0.json` sha256 `9a1a2446…` |
| XGBoost | App. E.4 (p.284): depth 5, eta 0.1, `binary:logitraw`, colsample 1 / 0.5 / 0.5, subsample 0.8, gamma 0.2, seed 1 | the same |
| trees | the production XML has **300**. Fig. E.4 equals exactly the split counts of its first 200 trees (`validation/nue_appendixE_prefix_test.json`): a plotting snapshot, not the training length | 300 |
| `base_score` | not in the thesis | **0**, the development convention for every SP model. Xuyang's 0.5 was not copied; the export check records that 0.5 would shift the margin by 1.4e-5 and refuses an unfolded export |
| legacy control | `single_photon_nue_bdt_final.xml` sha256 `8580ba04…` (300 trees, depth 5, 56 inputs), historical cut −1.0 | `legacy_control` |

**Not stated by the source, documented and not guessed:**
- *Class proportions and weights.* The thesis ratio is about 1 : 4 (signal : background). Here the natural proportions
  give 1 : 12 and are unweighted, the same convention as the siblings.
- *The truth-matching expression.* This is the `T_match` partner (assumption A4), as for SP numu / ncpi0.

None of these leaves a training setting undetermined, so training went ahead.

Specs: `specs/single_photon_nue_training_spec_dev_wcl1116_{dv2_split_move,dv2_snap}.yaml` (sha256 `17a64c92…` /
`923aea52…`). They differ only in their reconstruction block, and were generated from the complete census by
`tools/make_wcl1116_dev_specs.py --only nue`.

## 3. Class census (`validation/sp_nue_census_wcl1116.json`)

| | split-move | snap |
|---|---:|---:|
| **positive** rows: train / holdout | 8,819 / 8,871 | 8,722 / 8,791 |
| **negative** (νe CC background) rows: train / holdout | **106,623** / 106,808 | 106,676 / 106,810 |
| non-finite classed rows | 0 | 0 |
| thesis training counts (reference) | 24,936 signal / 100,958 νe CC | |

By sample (split-move; snap within 1 %):

| sample | events | preselected rows | positive rows | negative rows | excluded preselected rows (largest) |
|---|---:|---:|---:|---:|---|
| `wcl1116-aurora-ncdr` | 26,745 | 16,213 | 14,972 | 13 | outFV 330, NC π⁰ 285, νμ CC 216 |
| `wcl1116-aurora-bnb` | 626,441 | 65,792 | 2,610 | 1,239 | νμ CC 21,525 + 16,398 (π⁰), NC π⁰ 9,267, outFV 7,776 |
| `wcl1116-aurora-nuecc` | 268,783 | 220,503 | 108 | **212,179** | outFV 4,852, νμ CC 1,345 + 901, cosmic partner 578 |

- **79 % of νe CC events give a usable negative row.** The positives are the shared single-photon sample: the SP numu
  development positives plus 58 / 50 νe CC-sample rows that fit the signal definition.
- The **training** half has **106,623 νe CC negatives, matching the thesis's 100,958 (+6 %)**. It has 8,819
  positives, about a third of the thesis's 24,936; that statistics limit is shared by all four SP models.
- The νe CC sample also holds a few thousand preselected rows of other truth classes (outFV, νμ CC, NC π⁰). SP nue
  excludes them by definition. Whether the final SP other / numu / ncpi0 trainings should take them is a final-training
  sample question (four-model summary §4), not reopened here.

## 4. Development models (Tasks 11–12)

Fixed settings, no tuning, no weights, seed 1. Both JSONs are byte-identical on a repeat. Leakage: 0 overlapping
events, 0 duplicate rows, 0 multi-file events.

| mode | train rows +/− | holdout rows +/− | train AUC | holdout AUC | gap | model sha256 | exported XML sha256 |
|---|---:|---:|---:|---:|---:|---|---|
| dv2_split_move | 8,819 / 106,623 | 8,871 / 106,808 | 0.9791 | **0.9588** | 0.020 | `d3bd3b5e…` | `f47468d3…` |
| dv2_snap | 8,722 / 106,676 | 8,791 / 106,810 | 0.9763 | **0.9524** | 0.024 | `6b3282cc…` | `2cff3bb7…` |

- Names: `single_photon_nue_sbnd_wcl1116_<mode>_DEV_DO_NOT_DEPLOY`.
- Stored under `$SP_WORK/wcl1116_dev_models/<mode>/nue/`.
- Manifests: `manifests/wcl1116_dev_v1/single_photon_nue_<mode>_dev_manifest.json`. They carry the input lists, the
  table hashes, the spec and feature hashes, the per-file code hashes, the packages, the counts and the model sha256.
- The gap (0.020 / 0.024) is like SP numu's (0.019) and well below SP ncpi0's (0.09).

## 5. Legacy control and ROC-equivalent diagnostics (Task 13)

The legacy XML was scored as log10-odds on **identical** holdout rows: 115,679 / 115,601 rows, 0 excluded, rows rebuilt
equal to the stored ones.

**DEVELOPMENT ROC-EQUIVALENT DIAGNOSTIC — NOT ROUND2 CUT.** The legacy cut is never carried onto the native margin.

| mode | legacy AUC | dev AUC | legacy at −1.0: signal eff. / bkg acceptance | new at the same signal eff.: bkg acceptance | new at the same bkg acceptance: signal eff. |
|---|---:|---:|---|---|---|
| split-move | 0.9176 | **0.9588** | 78.4 % / 13.4 % | **5.4 %** (× 0.40) | **91.6 %** (+13.2 points) |
| snap | 0.9143 | **0.9524** | 78.4 % / 13.9 % | **6.4 %** (× 0.46) | **90.2 %** (+11.8 points) |

- Score correlation, legacy vs new: Spearman 0.878 / 0.877 overall, but only 0.51 / 0.54 within the signal class.
- **Where they disagree** (split-move, at equal signal efficiency): 9,658 νe CC negatives pass legacy but fail the new
  model. 9,608 of them are from the νe CC sample. Their medians are 2 showers above 20 MeV, an indirect max shower
  energy of 34 MeV and a min shower distance of 37 cm, against 1 / 5 MeV / 7 cm for all negatives.
- So the SBND model mainly learns to reject νe CC with a second, displaced shower. That is the topology the refreshed DL
  vertex changes most (`shw_vtx_dis`, `min_dis`).

Details: `$SP_WORK/wcl1116_legacy_controls/<mode>/nue/legacy_vs_dev.json`.

## 6. Retraining-benefit verdict (Task 14): RETRAINING CLEARLY BENEFICIAL

The rule was **pre-registered** in `tools/wcl1116_mode_compare.py` before any SP nue fit:
- BENEFICIAL: both modes gain ≥ 0.010 and > 3 σ;
- COMPETITIVE: both modes gain ≤ 0.002;
- otherwise NEUTRAL / NOT RESOLVED.

σ comes from a 200-sample event bootstrap of (dev − legacy) AUC on the same holdout rows.

| mode | dev − legacy AUC | bootstrap sd | significance |
|---|---:|---:|---:|
| split-move | **+0.0412** | 0.0008 | 51 σ |
| snap | **+0.0381** | 0.0009 | 42 σ |

**Verdict: RETRAINING CLEARLY BENEFICIAL** (`validation/wcl1116_mode_compare_nue.json`).
- The gain is about twice SP numu's (+0.018) and below SP ncpi0's (+0.051).
- It is consistent with the LARGE domain shift measured before training (`SP_BDT_WCL1116_DEVELOPMENT_RESULTS.md` §10).
- It is development evidence for retraining SP nue in Round 2. It is **not** a freeze of this model.

## 7. Snap vs split-move (development evidence only)

On matched holdout candidates (same key, same class, finite in both; 8,587 + / 103,957 −, 0 class disagreements):

| | split-move | snap | snap − split (± sd, 200 event bootstraps) |
|---|---:|---:|---:|
| dev AUC | 0.9599 | 0.9539 | **−0.0059 ± 0.0006** |
| legacy AUC | 0.9197 | 0.9162 | −0.0034 ± 0.0007 |

For SP nue the difference is larger than for SP numu (−0.0015) and SP ncpi0 (−0.0010), and it favours split-move in
both the legacy and the new model. This is development evidence, not a vertex-mode decision (four-model summary §3).

## 8. Feature sanity

| | split-move | snap |
|---|---|---|
| Spearman of split counts vs the legacy 300-tree XML | 0.863 | 0.890 |
| top-10 overlap with legacy | 8 / 10 | 8 / 10 |
| shower-start dQ/dx family, share of splits (legacy 60.9 %) | 61.8 % | 62.2 % |
| conversion distance (`shw_vtx_dis`, `min_dis`), share (legacy 7.9 %) | 9.2 % | 9.6 % |
| bookkeeping identifiers among inputs | none | none |

- Top 10 by splits (split-move): `shw_vtx_dis`, `length_total`, `length_main`, `E_indirect_max_energy`, `vec_dQ_dx_0`,
  `vec_dQ_dx_2`, `vec_dQ_dx_1`, `stem_length`, `max_shw_dis`, `max_dQ_dx_sample`.
- This is the expected e/γ separation: conversion gap and start dQ/dx, plus a second-shower veto. The structure is
  close to the legacy fingerprint.

## 9. Export and equivalence

- **Python** (`validation/wcl1116_export_equivalence_nue_{dv2_split_move,dv2_snap}.json`): **all pass** in both modes.
  - 300 trees, depth 5, XML names = feature list;
  - max |native margin − XML raw| 1.3e-5 / 1.8e-5, from XGBoost's float32 sum, within `1e-5·max(1,|m|)`;
  - per-tree leaves identical; equality routing 1,200 / 1,200;
  - ±FLT_MAX: 0 leaf mismatches;
  - NaN → −999;
  - 0 flips at the fixture cut and the quantile midpoints;
  - swapped-order guard refuses.
- **C++: VERIFIED.** TMVA::Reader and the toolkit `TmvaGradForest`, run in Haiwang's SL7 WCT 0.38.0 environment
  (ROOT 6.28/12, gcc 12.1) on a compute node: PBS 9100172, `neutrinoGPU::WireCell_aurora`, under 1 min. Summaries:
  `validation/cpp_export_equivalence_wcl1116_{dv2_split_move,dv2_snap}_nue.json`. Each mode has 3,310 fixture rows:
  3,000 holdout, 300 on exact split thresholds, 5 NaN and 5 ±FLT_MAX.

| check | split-move | snap |
|---|---|---|
| `TMVA::Reader` vs `TmvaGradForest` | bit-identical 3,310 / 3,310 | bit-identical 3,310 / 3,310 |
| C++ vs Python `sp_retrain.tmva_grad` | max \|Δ\| 4.4e-16; bit-identical on 3,302 / 3,305 finite rows | max \|Δ\| 2.2e-16; bit-identical on 3,299 / 3,305 |
| tanh(native margin) vs C++ | 6.4e-7 | 5.8e-7 |
| NaN input | −999 in both readers | −999 in both readers |
| swapped variable order | refused | refused |
| decision flips (fixture cut −1.0 and 5 quantile midpoints) | 0 | 0 |

## 10. What final SP nue training needs

- The **final reconstruction domain**: the vertex mode, plus confirmation that the cosmic-boundary production leaves
  `shw_sp_*` unchanged. SP nue reads no cosmic-tagger output and no upstream score (results §11: LIKELY INSENSITIVE),
  but a clustering-level change would move candidate formation.
- A **re-run of this spec unchanged** on the final νe CC + NC Δ + BNB training lists. No upstream freeze is needed.
- A decision on the signal statistics shared by all four models (8.8k training positives vs the thesis 24.9k), and on
  class weighting, which is not source-established. These are final-campaign questions, not tuning here.
- Then the validation-only threshold freeze, together with the other three models.
