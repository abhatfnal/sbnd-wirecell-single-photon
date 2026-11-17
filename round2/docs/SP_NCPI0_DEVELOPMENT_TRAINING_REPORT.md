# SP ncpi0 development model: `ROUND1_DOMAIN_DEVELOPMENT_DO_NOT_DEPLOY`

Date: 2026-11-17 (Aurora, `aurora-uan-0012`). This is one development model, trained on aurora-r2 to validate the
training machinery. **It is not the Round-2 model and must not be deployed.**

## 1. What was trained

| item | value |
|---|---|
| spec | `specs/single_photon_ncpi0_training_spec_dev_round1_domain_v1.yaml` (derived from v0.2.1; target in `YANDEL_THESIS_SP_BDT_TRAINING_SOURCE_AUDIT.md`) |
| model | `$SP_WORK/dev_models/ncpi0/single_photon_ncpi0_sbnd_dev_round1domain_v1_DO_NOT_DEPLOY.json`, sha256 `4f29962f19c36af57f5093b59dc9b0b7db5130ba47b6d39126ea3da07ff2fc3e` |
| manifest | `manifests/dev_round1domain_v1/single_photon_ncpi0_dev_manifest.json` |
| inputs | aurora-r2 NC Δ (17,603 files) + BNB CV (11,888 files), full lists. No official sample; no NC π⁰-enriched sample exists |
| features | 45, XML order (`config/features/single_photon_ncpi0_inputs_v0.json`, sha256 `5882391f…`), float32, stored values |
| **`kine_pio_flag`** | **Policy B**: the real reconstructed `T_kine.kine_pio_flag` in training and in inference. Decided before training; not revisited on performance. The legacy MicroBooNE XML keeps its own convention (scored with 0) and is not mixed in |
| classes | positive = inclusive single-photon signal (all 5 categories); negative = NC π⁰ background: not signal, NC, true vertex in the 3 cm FV, ≥ 1 **primary** π⁰ (A6) |
| preselection | non-placeholder candidate, `shw_sp_n_20mev_showers > 0`, label readable. No reco-vertex geometry cut (development convention; numu report §2) |
| split | `subrun_parity_v1`: even subrun = train, odd = test |
| XGBoost 3.4.1 | depth 6, 400 trees, eta 0.1, `binary:logitraw`, colsample 1 / 0.5 / 0.5, subsample 0.8, gamma 0.2, seed 1, eval [auc, error]. Development conventions: `base_score` 0, `hist`, 8 threads, no early stopping |
| weights | none |

## 2. Classes and split

| | train (even subrun) | test (odd subrun) |
|---|---:|---:|
| rows | 13,372 | 13,467 |
| positive rows (events) | 8,915 (8,912) | 9,000 (8,997) |
| negative rows (events) | 4,457 (4,453) | 4,467 (4,458) |
| NC Δ positive / negative | 7,603 / 128 | 7,701 / 142 |
| BNB positive / negative | 1,312 / 4,329 | 1,299 / 4,325 |

**Positive composition** (17,941 rows before the non-finite exclusion):
- NC Δ 1γ: 14,977
- out-of-FV 1γ: 1,381
- NC π⁰ → 1γ: 1,241
- νμ CC 1γ: 330
- NC other 1γ: 12

**Negative truth definition and sensitivity:**
- 8,933 rows before exclusions. By primary π⁰ count, 1 / 2 / ≥ 3: 8,399 / 466 / 68.
- **Sensitivity A6b** (any π⁰ instead of primary π⁰): 9,516 negatives (+583, +6.5 %). Not used.
- **Sensitivity A1b** (photon from any π⁰): changes 353 positive rows. Not used.

**Exclusions:**
- 34 rows with a non-finite input (26 positive, 8 negative; §5).
- One negative row from the single BNB file without the production `wct_version` stamp (10 candidates dropped in
  total).

**Leakage check:** 0 events overlap train and test, 0 duplicate rows, 0 events in more than one file, no event
straddles the split.

**Events with both classes: 22** (19 NC Δ, 3 BNB). Each involves at least two partner neutrinos, and no neutrino has
rows of both classes. These are legitimate candidate-level labels. 13 neutrinos own two candidate rows (4 positive).

## 3. Performance on the development test fold (native margin; no threshold)

| | AUC | error at m > 0 | XGBoost `error` (m > 0.5) |
|---|---:|---:|---:|
| train | 0.9854 | 0.0563 | 0.0545 |
| test | **0.8167** | 0.2291 | 0.2400 |

At the native diagnostic point m > 0 the test confusion matrix is: TP 7,878, FN 1,122, FP 1,963, TN 2,504.

**Flag: large train/test gap** (0.169 in AUC). The `train_vs_test.png` plot shows the test negatives shifted well
above the training ones. The negative class is small: 4,457 training rows, against MicroBooNE's 37,205. The thesis
depth (6) and tree count (400) fit that class closely.

This is recorded, not tuned. It supports the recommendation of an NC π⁰-enriched training sample for the final model.
The thesis calls this separation intrinsically hard ("only mild separation", Fig. 5.9).

The plots are in `$SP_WORK/dev_models/ncpi0/plots/`:
- `roc.png`;
- `score_test.png`;
- `train_vs_test.png`;
- `importance.png`;
- `kine_pio_flag_diagnostic.png`.

## 4. Feature behaviour compared with the Yandel / XML fingerprint

| input or group | dev splits (share, rank) | dev mean gain (rank) | legacy XML / thesis |
|---|---|---|---|
| 15 νe level-1 scores, as a group | 29.8 % of splits, 23.7 % of total gain | — | 40.6 % of splits |
| 12 `kine_pio_*` | 42.9 % of splits | — | 35.5 % |
| `kine_pio_flag` | 18 (0.11 %, 44th) | 3.03 (20th) | 23 splits, 44th; gain 9.19, 10th (Fig. E.3) |
| `kine_pio_mass` | 753 (4.6 %, 3rd) | 4.70 (8th) | 660, 6th |
| `shw_sp_E_indirect_max_energy` | 630 (3.9 %, 9th) | 6.70 (4th) | 750, 1st |
| `shw_sp_pio_flag_pio` | 10 (45th) | **55.6 (1st)** | 5 splits, 45th; gain 61.8, **1st** (Fig. E.3) |

**Top 10 by split count:** `kine_pio_angle`, `kine_pio_energy_1`, `kine_pio_mass`, `kine_pio_phi_1`,
`kine_pio_energy_2`, `kine_pio_theta_1`, `kine_pio_phi_2`, `kine_pio_theta_2`, `shw_sp_E_indirect_max_energy`,
`kine_pio_dis_2`.

**Top by mean gain:** `shw_sp_pio_flag_pio`, `shw_sp_pio_1_pio_type`, `shw_sp_pio_1_energy_2`.

Split counts correlate with the legacy XML at Spearman 0.854, and all 45 inputs are used.

**Qualitative comparison with the thesis model:**
- **Same pattern.** π⁰ kinematics dominate the split count, and the π⁰-pair flags carry the largest gain per split.
- **Flagged differences.**
  - The development model leans less on the 15 νe level-1 scores (29.8 % vs 40.6 % of splits) and more on `kine_pio_*`.
  - `shw_sp_pio_1_pio_type` ranks 2nd by gain here, but last in the thesis gain plot.
  - These are not errors in themselves: the detector, the reconstruction and the sample composition all differ.

## 5. Non-finite inputs

There is no source-defined replacement: TMVA's Reader returns −999 for a NaN input, which fails every legacy cut.
Development therefore **excludes** every row with a non-finite input from training and test (spec
`non_finite_policy: exclude_row`); none is imputed.

- 34 rows: 26 positive, 8 negative; 22 NC Δ, 12 BNB.
- Inputs involved: `kine_pio_angle` 24, `kine_pio_theta_2` 13, `kine_pio_theta_1` 11, `kine_pio_mass` 6,
  `shw_sp_pio_1_mass` 6.
- The full list is also in `validation/dev_round1domain_v1_ncpi0_nonfinite_rows.csv`.

| # | class | sample | file (unit) | run | subrun | event | cand | non-finite input(s) |
|---:|---|---|---|---:|---:|---:|---:|---|
| 1 | positive | aurora-r2-ncdr | `reco2-reco1-detsim-g4-filter-gen-197a-4a9f-7530-c968` | 7013744 | 70 | 16 | 0 | kine_pio_mass |
| 2 | positive | aurora-r2-ncdr | `reco2-reco1-detsim-g4-filter-gen-305e-024d-0b7c-dd59` | 7027629 | 16 | 63 | 0 | kine_pio_theta_2, kine_pio_angle |
| 3 | positive | aurora-r2-ncdr | `reco2-reco1-detsim-g4-filter-gen-46b3-d32c-a1f9-d343` | 7013760 | 60 | 90 | 0 | kine_pio_theta_1, kine_pio_angle |
| 4 | positive | aurora-r2-ncdr | `reco2-reco1-detsim-g4-filter-gen-9b35-26e1-38ef-be50` | 7018290 | 24 | 43 | 0 | kine_pio_theta_1, kine_pio_angle |
| 5 | positive | aurora-r2-ncdr | `reco2-reco1-detsim-g4-filter-gen-a697-ccb6-f6e6-3776` | 7018254 | 98 | 20 | 0 | kine_pio_theta_2, kine_pio_angle |
| 6 | positive | aurora-r2-ncdr | `reco2-reco1-detsim-g4-filter-gen-ae2a-6c69-8b61-6531` | 7019753 | 35 | 116 | 0 | shw_sp_pio_1_mass |
| 7 | positive | aurora-r2-ncdr | `reco2-reco1-detsim-g4-filter-gen-ca43-b755-1e61-0ad5` | 7008853 | 99 | 73 | 0 | kine_pio_theta_2, kine_pio_angle |
| 8 | positive | aurora-r2-ncdr | `reco2-reco1-detsim-g4-filter-gen-cadb-8ec2-5661-ef2f` | 7008181 | 95 | 62 | 0 | kine_pio_theta_2, kine_pio_angle |
| 9 | positive | aurora-r2-ncdr | `reco2-reco1-detsim-g4-filter-gen-dc47-8dbb-959e-5302` | 7011146 | 28 | 71 | 0 | kine_pio_theta_1, kine_pio_angle |
| 10 | positive | aurora-r2-ncdr | `reco2-reco1-detsim-g4-filter-gen-7ae1-0d86-c2ac-2538` | 7003771 | 30 | 24 | 0 | kine_pio_theta_2, kine_pio_angle |
| 11 | positive | aurora-r2-ncdr | `reco2-reco1-detsim-g4-filter-gen-9ce7-0b35-f2b4-8b94` | 7020140 | 98 | 86 | 0 | kine_pio_theta_2, kine_pio_angle |
| 12 | positive | aurora-r2-ncdr | `reco2-reco1-detsim-g4-filter-gen-a35a-31ea-edd3-d866` | 7025296 | 1 | 117 | 0 | kine_pio_theta_1, kine_pio_angle |
| 13 | positive | aurora-r2-ncdr | `reco2-reco1-detsim-g4-filter-gen-d57e-80fc-6a45-17c9` | 7000680 | 15 | 95 | 0 | kine_pio_theta_2, kine_pio_angle |
| 14 | positive | aurora-r2-ncdr | `reco2-reco1-detsim-g4-filter-gen-01eb-8f2f-1a3f-5121` | 7019694 | 51 | 68 | 0 | kine_pio_theta_2, kine_pio_angle |
| 15 | positive | aurora-r2-ncdr | `reco2-reco1-detsim-g4-filter-gen-a72f-88c0-2cc4-0c66` | 7016068 | 22 | 83 | 0 | kine_pio_theta_2, kine_pio_angle |
| 16 | positive | aurora-r2-ncdr | `reco2-reco1-detsim-g4-filter-gen-bb2f-b947-6acd-0378` | 7015233 | 33 | 51 | 0 | shw_sp_pio_1_mass |
| 17 | positive | aurora-r2-ncdr | `reco2-reco1-detsim-g4-filter-gen-3aaa-86ee-2405-b6c9` | 7001292 | 39 | 106 | 0 | shw_sp_pio_1_mass |
| 18 | positive | aurora-r2-ncdr | `reco2-reco1-detsim-g4-filter-gen-3dde-c54e-a7c9-cb83` | 7002039 | 74 | 90 | 0 | kine_pio_mass |
| 19 | positive | aurora-r2-ncdr | `reco2-reco1-detsim-g4-filter-gen-5e54-aafb-c455-9060` | 7021722 | 88 | 10 | 0 | kine_pio_theta_1, kine_pio_angle |
| 20 | positive | aurora-r2-ncdr | `reco2-reco1-detsim-g4-filter-gen-a939-2bf1-3aa9-7bc6` | 7026231 | 14 | 58 | 0 | kine_pio_theta_1, kine_pio_angle |
| 21 | positive | aurora-r2-ncdr | `reco2-reco1-detsim-g4-filter-gen-ad2a-bcbe-ebb8-f4df` | 7012991 | 25 | 49 | 0 | kine_pio_theta_1, kine_pio_angle |
| 22 | positive | aurora-r2-ncdr | `reco2-reco1-detsim-g4-filter-gen-f68f-5e49-7740-1f78` | 7021855 | 5 | 86 | 0 | kine_pio_mass |
| 23 | negative | aurora-r2-bnb | `reco2-reco1-detsim-g4-gen-d672-db86-b2fc-9abf` | 2105003 | 66 | 9 | 0 | kine_pio_theta_2, kine_pio_angle |
| 24 | negative | aurora-r2-bnb | `reco2-reco1-detsim-g4-gen-d6d7-501d-4474-5e87` | 2100716 | 6 | 2 | 0 | shw_sp_pio_1_mass, kine_pio_mass, kine_pio_theta_2, kine_pio_angle |
| 25 | negative | aurora-r2-bnb | `reco2-reco1-detsim-g4-gen-343f-33cd-9061-287c` | 2100078 | 18 | 1 | 0 | kine_pio_theta_1, kine_pio_angle |
| 26 | negative | aurora-r2-bnb | `reco2-reco1-detsim-g4-gen-bca1-1f27-3945-fc95` | 2110581 | 7 | 6 | 0 | shw_sp_pio_1_mass |
| 27 | positive | aurora-r2-bnb | `reco2-reco1-detsim-g4-gen-5f5e-038e-0895-ce0b` | 2110362 | 13 | 5 | 0 | kine_pio_theta_1, kine_pio_angle |
| 28 | positive | aurora-r2-bnb | `reco2-reco1-detsim-g4-gen-7acc-46b2-91cc-fe39` | 2105572 | 90 | 6 | 0 | kine_pio_mass |
| 29 | negative | aurora-r2-bnb | `reco2-reco1-detsim-g4-gen-ea5a-231c-9d8e-08d3` | 2100358 | 92 | 1 | 0 | kine_pio_mass |
| 30 | negative | aurora-r2-bnb | `reco2-reco1-detsim-g4-gen-7f29-15e9-a596-08cd` | 2110506 | 22 | 6 | 0 | kine_pio_theta_1, kine_pio_angle |
| 31 | negative | aurora-r2-bnb | `reco2-reco1-detsim-g4-gen-0ada-c075-242c-e4f8` | 2100218 | 30 | 6 | 0 | kine_pio_theta_2, kine_pio_angle |
| 32 | positive | aurora-r2-bnb | `reco2-reco1-detsim-g4-gen-33b1-7bfb-b4d1-3a39` | 5000711 | 25 | 4 | 0 | shw_sp_pio_1_mass |
| 33 | negative | aurora-r2-bnb | `reco2-reco1-detsim-g4-gen-9017-c2ee-7b93-2e52` | 2105387 | 72 | 8 | 0 | kine_pio_theta_1, kine_pio_angle |
| 34 | positive | aurora-r2-bnb | `reco2-reco1-detsim-g4-gen-df42-e98d-1b26-60c3` | 2100354 | 16 | 5 | 0 | kine_pio_theta_2, kine_pio_angle |

## 6. `kine_pio_flag` diagnostic (no model selection)

The Policy-B model was scored twice on the same 13,467 test rows: once with the real flag, once with the flag forced to
0 and everything else identical. The flag values on the test rows are 0 / 1 / 2 = 2,323 / 10,903 / 241.

| quantity | value |
|---|---|
| Δm = m(flag 0) − m(real), all rows | mean −0.0014, median 0, 1 % / 99 % quantiles −0.122 / +0.095 |
| rows with \|Δm\| > 0.01 / 0.1 / 0.5 / 1 | 5.9 % / 2.6 % / 0.06 % / 0 |
| same, among the 11,144 rows with real flag ≠ 0 | 7.2 % / 3.1 % / 0.07 % / 0 |
| Spearman rank correlation, real vs forced | 0.99984 |
| test AUC, real / forced 0 | 0.81674 / 0.81679 |
| decision changes at the native diagnostic point m = 0 | 11 of 13,467 |

**What it shows.** The SBND development model makes little use of the flag: 18 splits, and the 0 vs ≥ 1 information is
also carried by `kine_pio_mass` and `kine_pio_energy_2`, which are 0 whenever the flag is 0. Forcing the flag to 0
therefore moves few scores, and those only slightly.

**Legacy context.** The legacy XML is always scored with the flag at 0 (§7.2). Policy B is unchanged.

## 7. Legacy control: AURORA DEVELOPMENT SAMPLE — LEGACY MICROBOONE CONTROL

**AURORA DEVELOPMENT — NOT OFFICIAL EVALUATION.** These numbers are not SBND performance and set no Round-2 cut.

**Legacy XML.** `single_photon_ncpi0_bdt_final.xml`, sha256 `983a0d82…17c3`, from the verified EAF bundle
(`manifests/dev_round1domain_v1/legacy_controls.json`).
- 45 inputs in the feature-list order, 400 trees, depth 6.
- It is scored with `sp_retrain.tmva_grad`, then `log10((1+v)/(1−v))` once.
- **`kine_pio_flag` is set to 0 for the legacy model only**, as MicroBooNE production does. The development model keeps
  the real flag (Policy B).

**Rows:**

| | rows |
|---|---:|
| original test rows (odd subrun, classed) | 13,480 (9,012 positive / 4,468 negative) |
| development-evaluable | 13,467 |
| legacy-evaluable | 13,467 |
| **common** | **13,467** (9,000 / 4,467) |

The 13 excluded rows have a NaN input. TMVA returns −999 for them, so they fail every legacy cut; neither model scores
them. The rebuilt test rows equal the stored ones, and the recomputed development margins equal the stored ones
exactly.

| model | test AUC (common rows) |
|---|---:|
| legacy MicroBooNE XML (flag 0) | 0.7544 |
| SBND development model (Policy B) | 0.8167 |
| delta | **+0.0623** |

**Legacy at its historical cut, score > −0.05:**

| | value |
|---|---|
| signal efficiency | 39.40 % (TP 3,546, FN 5,454) |
| background acceptance | 12.58 % (FP 562, TN 3,905) |
| background rejection | 87.42 % |

**DIAGNOSTIC ROC-EQUIVALENT POINTS — NOT ROUND-2 CUTS:**

| point | development threshold | development | legacy | difference |
|---|---:|---|---|---|
| A: same signal efficiency (39.40 %) | m > 2.357 | background acceptance 7.05 % (FP 315) | 12.58 % | −5.53 points (×0.56) |
| B: same background acceptance (12.58 %) | m > 1.828 | signal efficiency 54.57 % (TP 4,911) | 39.40 % | +15.2 points (×1.39) |

**Event-by-event, at point A:**

| rows | both pass | legacy pass / development fail | legacy fail / development pass | both fail |
|---|---:|---:|---:|---:|
| positive | 1,994 | 1,552 | 1,552 | 3,902 |
| negative | 141 | 421 | 174 | 3,731 |

- **Negatives the legacy model keeps and the development model removes** (421):
  - 399 with one primary π⁰;
  - soft, low-mass π⁰ candidates: median `kine_pio_mass` 43 MeV against 101 MeV for all negatives, and energies
    37 / 44 MeV against 85 / 74 MeV.
- **Positives that only the development model keeps** (1,552; 1,430 NC Δ 1γ):
  - an energetic leading shower: median `kine_pio_energy_1` 102 MeV against 46 MeV for all positives;
  - a soft second shower: `kine_pio_energy_2` 18 MeV.
- **Positives that only the legacy model keeps** (1,552): NC Δ 1γ 1,166, NC π⁰ → 1γ 175, out-of-FV 168, νμ CC 40;
  low-energy pairs (median mass 20 MeV).
- `kine_pio_flag` is 1 for most flipped rows.

**At point B** the development model gains 2,238 and loses 873 positives; the negatives swap 328 / 328.

**Score correlation:**
- Spearman 0.651 (positive 0.505, negative 0.696);
- Pearson 0.684.

The two models rank events noticeably differently: the retrained model has learned a different ordering. That is not
in itself a defect.

**Routing cross-check:** the `<=` routing changes the raw sum of 10 rows.

**Plots:** `$SP_WORK/legacy_controls_results/ncpi0/plots/`.

### 7.1 What the legacy comparison says about the train/test gap

The development model has train AUC 0.985 and test AUC 0.817. On the same held-out SBND rows:
- the legacy MicroBooNE model reaches only **0.754**;
- at the legacy working point's signal efficiency, the development model accepts **44 % less background**;
- at equal background acceptance, it keeps **+15 points** of signal.

So the answer is **A, not B**:
- the legacy model also performs poorly on the SBND test sample;
- the development model does **not** generalize worse than the legacy one.

The large train/test gap is the variance of 400 depth-6 trees fitted to 4.5k training negatives. It is not a loss
relative to the inherited model.

Two caveats:
- The legacy model is evaluated out of its MicroBooNE domain, so part of its deficit is domain shift.
- The comparison does not show how much better a model trained on more NC π⁰ negatives would be.

It does support the plan for an NC π⁰-enriched final training sample. Nothing was retrained or tuned.

### 7.2 `kine_pio_flag` context

The legacy XML is **always** scored with the flag forced to 0. That is its source-faithful convention, and all numbers
above use it.

As a non-source-faithful diagnostic only, scoring the legacy XML with the real SBND flag gives:
- AUC 0.7557 (against 0.7544 with the flag at 0);
- Spearman 0.9991 between the two;
- 120 decision changes at −0.05 (0.9 % of rows).

The new model's Policy-B diagnostic (§6) is similar in size: 11 changes at its native margin 0. In SBND the flag
carries little information beyond `kine_pio_mass`, for both models. Policy B is unchanged.

**Feature sanity:**

| | legacy XML | development model |
|---|---|---|
| 15 νe level-1 scores | 40.6 % of splits | 29.8 % |
| `kine_pio_*` | 35.5 % | 42.9 % |
| `kine_pio_flag` | 23 splits, rank 44 | 18 splits, rank 44 |
| `shw_sp_pio_flag_pio` | highest mean gain (thesis) | highest mean gain |

Split counts correlate at Spearman 0.854. Both models are dominated by π⁰ kinematics. The development model leans less
on the inherited level-1 scores, which is a plausible effect of the SBND domain. This is a sanity check only.

## 8. Reproducibility

A second training with the same spec and seed gives a byte-identical model JSON (same sha256) and identical test
margins.

## 9. Not learned here, and still required for the final model

Final ncpi0 needs:
- the frozen DL vertex and reconstruction;
- confirmation that the 15 νe level-1 models stay as shipped;
- Haiwang's training refresh;
- ideally an NC π⁰-enriched training sample, which the train/test gap above argues for;
- the production exporter and equivalence test (`SP_BDT_SCORE_SCALE_AND_EXPORT_REQUIREMENTS.md`).

**This JSON is not deployable.**
