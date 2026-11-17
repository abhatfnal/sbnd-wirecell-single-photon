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

## 6. Legacy control

**Not available.** The frozen `single_photon_numu_bdt_final.xml` is not on Aurora: it is in no public repository, not
in `yuhw/wire-cell-data`, and `/lus/eagle` is not mounted. It was not reconstructed from the audit tables.

A legacy-vs-development comparison on these test events needs the XML scored with the source-faithful scorer on EAF,
or the XML copied to Aurora with its sha256 checked.

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
