# SP numu development model: `ROUND1_DOMAIN_DEVELOPMENT_DO_NOT_DEPLOY`

Date: 2026-11-17 (Aurora, `aurora-uan-0012`). This is one development model, trained on aurora-r2 to validate the
training machinery. **It is not the Round-2 model and must not be deployed.** Its `numu_score` and `numu_1_score`
inputs are the OLD shipped νμ models, which Xuyang will retrain.

## 1. What was trained

| item | value |
|---|---|
| spec | `specs/single_photon_numu_training_spec_dev_round1_domain_v1.yaml` (derived from v0.1.0; target in `SP_NUMU_TRAINING_SOURCE_AUDIT.md`) |
| model | `$SP_WORK/dev_models/numu/single_photon_numu_sbnd_dev_round1domain_v1_DO_NOT_DEPLOY.json`, sha256 `024cce370650d8ccf39f8f6af27f4c16e7b774bb8844fdc753a1ce9b307ea124` |
| manifest | `manifests/dev_round1domain_v1/single_photon_numu_dev_manifest.json` (code, spec, feature-list and table sha256s, package versions, counts) |
| inputs | aurora-r2 NC Δ (17,603 files) + BNB CV (11,888 files), full lists (`manifests/dev_round1domain_v1/inputs.json`). No official sample |
| features | 73, XML order (`config/features/single_photon_numu_inputs_v0.json`, sha256 `688cde8f…`), float32, stored values, no preprocessing |
| classes | positive = inclusive single-photon signal (all 5 categories); negative = νμ CC with and without π⁰, in the 3 cm FV, not signal |
| preselection | non-placeholder candidate, `shw_sp_n_20mev_showers > 0`, label readable. No reco-vertex geometry cut (development convention; §2) |
| split | `subrun_parity_v1`: even subrun = train, odd = test (thesis p.128; Xuyang `spec_v1` §6). No validation fold |
| XGBoost 3.4.1 | depth 5, 300 trees, eta 0.1, `binary:logitraw`, colsample 1 / 0.5 / 0.5, subsample 0.8, gamma 0.2, seed 1, eval [auc, error]. Development conventions: `base_score` 0, `hist`, 8 threads, no early stopping |
| weights | none (no class or event weights) |

## 2. Preselection as applied

The SBND preselection drops the MicroBooNE 5 < x < 250 cm vertex cut. That cut corrects a MicroBooNE trigger-timing
offset (thesis Table 5.2) and has no SBND equivalent.

This is a **development convention, not the final analysis FV**. On the full lists, an illustrative 5 < |x| < 196.3 cm
cut would remove:
- 3.9 % of NC Δ and 5.9 % of BNB preselected rows;
- 3.7 % of positives and 4.5 % of negatives.

The 3 cm truth FV in the labels is the GDML `volTPCActive` box shrunk by 3 cm (Matteo Vicenzi's `cuts.ACTIVE`).

## 3. Classes and split

| | train (even subrun) | test (odd subrun) |
|---|---:|---:|
| rows | 28,433 | 28,396 |
| positive rows (events) | 8,929 (8,926) | 9,012 (9,009) |
| negative rows (events) | 19,504 (19,435) | 19,384 (19,297) |
| events | 28,316 | 28,248 |
| NC Δ positive / negative | 7,615 / 150 | 7,711 / 184 |
| BNB positive / negative | 1,314 / 19,354 | 1,301 / 19,200 |

**Totals and composition:**
- 17,941 positive and 38,888 negative rows.
- Negatives without π⁰: 22,820. With π⁰: 16,068 (primary π⁰ 1 / 2 / ≥ 3: 14,495 / 1,400 / 173).

**Leakage check:**
- 0 events overlap train and test;
- 0 duplicate rows;
- 0 events in more than one file;
- no event straddles the split (`split.check_event_safe`).

**Events with both classes: 103** (89 NC Δ, 14 BNB). Each involves at least two different partner neutrinos (pileup in
one spill), and no neutrino has rows of both classes. These are legitimate candidate-level labels, kept on one side of
the split.

32 neutrinos own two candidate rows (4 of them positive); the candidate-level policy is OPEN.

Other exclusions:
- **Non-finite inputs:** 0 rows.
- **Provenance:** 10 BNB candidates come from one file without the production `wct_version` stamp, which recorded 20
  Wire-Cell events of its 42. They were dropped; none was a numu class row.

## 4. Performance on the development test fold

The native margin `m` of `binary:logitraw` is used (`SP_BDT_SCORE_SCALE_AND_EXPORT_REQUIREMENTS.md`). There is no
threshold tuning and no operating point.

| | AUC | error at m > 0 (p = 0.5) | XGBoost `error` (m > 0.5) |
|---|---:|---:|---:|
| train | 0.9876 | 0.0532 | 0.0585 |
| test | 0.9592 | 0.1021 | 0.1061 |

At the native diagnostic point m > 0 the test confusion matrix is: TP 7,679, FN 1,333, FP 1,566, TN 17,818. That point
is not a production threshold.

The train / test gap is 0.028 in AUC.

The plots are in `$SP_WORK/dev_models/numu/plots/`:
- `roc.png`;
- `score_test.png`;
- `train_vs_test.png`;
- `importance.png`.

## 5. Feature behaviour compared with the legacy XML

| input | dev splits (share, rank) | dev mean gain (rank) | legacy XML splits (share, rank) |
|---|---|---|---|
| `numu_score` | 335 (4.4 %, **1**) | 50.6 (5) | 623 (7.7 %, 1) |
| `numu_1_score` | 321 (4.2 %, **2**) | 26.5 (7) | 311 (3.8 %, 3) |
| the pair | **8.6 %** of splits, **21.7 % of total gain** | — | 11.5 % of splits |

- The development model still relies most on the upstream νμ scores. They are the top two by split count and together
  carry about a fifth of the total gain. **A new `numu_score` from Xuyang will move this model.**
- Other top inputs by split count: `shw_sp_E_indirect_max_energy` (287; legacy rank 2), `shw_sp_max_dQ_dx_sample`,
  `numu_cc_3_track_length`, `shw_sp_br3_8_max_dQ_dx`, `numu_cc_3_max_length_all`. These are the muon-track and
  "bad reconstruction 3" families the thesis names (p.128).
- Top inputs by mean gain: `numu_cc_3_max_muon_length`, `numu_cc_3_particle_type`, `numu_cc_3_track_length`.
- Split counts correlate with the legacy XML at Spearman 0.906 over the 73 inputs. Every input is used, as in the
  legacy model.

## 6. Legacy control: AURORA DEVELOPMENT SAMPLE — LEGACY MICROBOONE CONTROL

**AURORA DEVELOPMENT — NOT OFFICIAL EVALUATION.** These numbers are not SBND performance and set no Round-2 cut.

**Legacy XML.** `single_photon_numu_bdt_final.xml`, sha256 `5886affb…ead961`.
- It comes from the verified EAF bundle `$SP_WORK/legacy_bdt_controls/legacy_sp_bdt_bundle_20261117/`; tarball sha256
  `90239e2a…08cd8`, all four XMLs OK (`manifests/dev_round1domain_v1/legacy_controls.json`).
- 73 inputs in the feature-list order, 300 trees, depth 5.
- It is scored with the validated `sp_retrain.tmva_grad` (TMVA routing). The production score
  `log10((1+v)/(1−v))` is applied once, and equals `2·raw/ln 10` to 2e-8.

**Rows.** 28,396 original test rows; all are new-evaluable and legacy-evaluable. Common: 28,396 (9,012 positive /
19,384 negative).

The test rows rebuilt from the frozen tables equal the stored ones in order. The development margins recomputed from
the model JSON equal the stored ones exactly.

| model | test AUC (common rows) |
|---|---:|
| legacy MicroBooNE XML | 0.9262 |
| SBND development model | 0.9592 |
| delta | **+0.0330** |

**Legacy at its historical cut, score > 0.4:**

| | value |
|---|---|
| signal efficiency | 62.05 % (TP 5,592, FN 3,420) |
| background acceptance | 5.81 % (FP 1,127, TN 18,257) |
| background rejection | 94.19 % |

**DIAGNOSTIC ROC-EQUIVALENT POINTS — NOT ROUND-2 CUTS** (thresholds on the development native margin):

| point | development threshold | development | legacy | difference |
|---|---:|---|---|---|
| A: same signal efficiency (62.05 %) | m > 1.319 | background acceptance 2.67 % (FP 518) | 5.81 % | −3.14 points (×0.46) |
| B: same background acceptance (5.81 %) | m > 0.434 | signal efficiency 79.35 % (TP 7,151) | 62.05 % | +17.3 points (×1.28) |

**Event-by-event, at point A:**

| rows | both pass | legacy pass / development fail | legacy fail / development pass | both fail |
|---|---:|---:|---:|---:|
| positive | 4,498 | 1,094 | 1,094 | 2,326 |
| negative | 349 | 778 | 169 | 18,088 |

- **Negatives the legacy model keeps and the development model removes** (778):
  - median `numu_score` −0.76, against 2.20 for all negatives;
  - median `numu_cc_3_track_length` 15 cm against 113 cm, and `numu_cc_3_max_muon_length` 0 against 77 cm;
  - longer, more segmented showers (`shw_sp_length_total` 27 cm, `br3_1` segments 8).

  These are νμ CC events without a clear muon. The development model rejects them through shower and track variables
  rather than `numu_score` alone.
- **Positives that only the development model keeps** (1,094; 989 NC Δ, 274 BNB in that flip class):
  - `numu_score` −0.02, against −0.53 for all positives;
  - two ≥ 20 MeV showers;
  - compact showers (23 cm, 6 segments).

**At point B** the development model gains 1,905 and loses 346 positives, while the negatives swap 530 / 530.

**Score correlation** (legacy production score vs development margin, common rows):
- Spearman 0.923 (positive 0.675, negative 0.878);
- Pearson 0.920.

The two models rank events similarly overall.

**Routing cross-check.** The EAF Python-scorer routing (left if `x <= cut`) changes the raw sum of 12 of the 28,396
rows, by at most 0.17. TMVA routing is used throughout.

**Plots** (`$SP_WORK/legacy_controls_results/numu/plots/`):
- `roc_legacy_vs_dev.png`;
- `legacy_score_test.png`, with the historical cut drawn on the legacy production-score axis only;
- `legacy_vs_dev_2d.png`.

**Feature sanity.**

| | legacy XML | development model |
|---|---|---|
| `numu_score` | rank 1 | rank 1 (335 splits) |
| `numu_1_score` | rank 3 | rank 2 (321 splits) |
| share of splits held by the pair | 11.5 % | 8.6 % (21.7 % of total gain) |

The split counts correlate at Spearman 0.906, and the event scores at 0.923. The development model is learning
qualitatively the same structure: upstream νμ score first, then muon-track and shower-quality variables. This is a
sanity check, not a selection criterion.

## 7. Reproducibility

Training a second time with the same spec and seed gives a **byte-identical model JSON** (same sha256) and identical
test margins (maximum difference 0).

## 8. Not learned here, and still required for the final model

This model validates:
- the table → label → split → fit → manifest chain;
- the absence of leakage;
- determinism;
- the size of the classes.

**Its performance is not a Round-2 number.**

The final SP numu still needs:
- the frozen DL vertex and reconstruction;
- Xuyang's frozen νμ chain;
- Haiwang's training refresh;
- retraining on the refreshed values, with an exporter and equivalence test before any threshold.
