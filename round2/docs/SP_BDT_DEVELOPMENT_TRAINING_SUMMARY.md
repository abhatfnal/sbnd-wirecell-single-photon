# Single-photon BDT development training (Round-1 domain): summary

Date: 2026-11-17 (Aurora). Campaign `development_round1_domain_v1`; every product is
**`ROUND1_DOMAIN_DEVELOPMENT_DO_NOT_DEPLOY`**. Branch `round2/sp-bdt-development-training-20261117`, from `6719fce`.

This campaign trained one SP numu and one SP ncpi0 model on the current aurora-r2 CAFs. Its purpose is to validate the
complete training machinery before three things exist:
- Snehadri's frozen vertexing;
- Xuyang's frozen νμ chain;
- Haiwang's Round-2 training refresh.

**Not trained:**
- **SP other:** WAITING FOR IN-TIME COSMIC TRAINING SAMPLE + XUYANG NUMU FREEZE.
- **SP nue:** DECISION BLOCKED — THESIS/XML VERSION MISMATCH + VERTEX DOMAIN SHIFT UNKNOWN.

## 1. Inputs, frozen before training

`manifests/dev_round1domain_v1/inputs.json` (sha256 `e53321f7…`):

| sample | list sha256 | files | content |
|---|---|---:|---|
| `aurora-r2-ncdr` | `8895a65e…5ecf` | 17,603 | NC Δ radiative configL; 26,744 events |
| `aurora-r2-bnb` | `dfbb5240…c6bb` | 11,888 | BNB CV; 627,205 events |

**Provenance:**
- Production tag aurora-r2.
- `wct_version` `sbnd-dlvtx-35-pre-master-merge-54-ga2785870` (toolkit `a2785870`). One BNB file without the stamp
  was dropped (10 candidates).
- Schema md5 `af9c87c8…` (2,416 branches).
- On 2026-11-17 every listed file was re-stat'ed: path, size and mtime are identical to the committed `aurora_r2_v0`
  manifests.

**POT caveat:** `rec.hdr.pot` is not the physical exposure of the filtered NC Δ sample. The fit is unweighted.

**No official fg1 / FermiGrid sample** is an input. The firewall ran on every file path, and a test scans every
development manifest.

**Tables:** `$SP_WORK/dev_tables/`, built with the `6719fce` builder (code sha256 recorded).

| sample | errors | other issues | `cands` sha256 |
|---|---:|---|---|
| NC Δ | 0 | 43 files with an unreadable label branch | `14e105ae…` |
| BNB | 0 | 48 files with an unreadable `T_truth_pf` | `1e90a18a…` |

Rows from those files are excluded through their class: label or truth unreadable gives class −1.

## 2. Specs, frozen before training

Common to both models:

| item | value |
|---|---|
| split | `subrun_parity_v1`: even subrun = train, odd = test. This is the thesis rule and Xuyang's `spec_v1` §6 MC split; no validation fold |
| preselection | non-placeholder candidate, `shw_sp_n_20mev_showers > 0`, label readable. **No SBND reco-vertex geometry cut: development convention**; an illustrative cut would remove ≈ 4–6 % |
| non-finite inputs | rows excluded and listed; no imputation |
| class or event weights | none |

The source-established XGBoost settings come from thesis Appendix E: depth / trees 5 / 300 (numu) and 6 / 400 (ncpi0),
eta 0.1, `binary:logitraw`, colsample 1 / 0.5 / 0.5, subsample 0.8, gamma 0.2, seed 1, eval [auc, error].

Development conventions, fixed before training:
- `base_score` 0. A smoke test showed that XGBoost 3.4.1 adds `base_score` as a raw margin under `logitraw`.
- `hist`, 8 threads.

| | numu | ncpi0 |
|---|---|---|
| spec | `…numu…_dev_round1_domain_v1.yaml` (`da2c9ee2…`) | `…ncpi0…_dev_round1_domain_v1.yaml` (`2b15c6a6…`) |
| features | 73 (`688cde8f…`) | 45 (`5882391f…`) |
| negative class | νμ CC with and without π⁰, in FV | NC π⁰ (≥ 1 primary π⁰), in FV |
| `kine_pio_flag` | not an input | **Policy B**: real value in training and inference |

## 3. Results on the development test fold

These use the native margin and **no threshold**.

| | numu | ncpi0 |
|---|---:|---:|
| train rows: positive / negative | 8,929 / 19,504 | 8,915 / 4,457 |
| test rows: positive / negative | 9,012 / 19,384 | 9,000 / 4,467 |
| events with both classes (pileup, ≥ 2 neutrinos) | 103 | 22 |
| rows excluded, non-finite input | 0 | 34 |
| train / test AUC | 0.9876 / **0.9592** | 0.9854 / **0.8167** |
| train / test error at m > 0 | 0.0532 / 0.1021 | 0.0563 / 0.2291 |
| train / test XGBoost `error` (m > 0.5) | 0.0585 / 0.1061 | 0.0545 / 0.2400 |
| top inputs by split count | `numu_score`, `numu_1_score`, `shw_sp_E_indirect_max_energy` | `kine_pio_angle`, `kine_pio_energy_1`, `kine_pio_mass` |
| upstream-score use | `numu_score` 1st and `numu_1_score` 2nd by splits; 8.6 % of splits and 21.7 % of gain (legacy 11.5 % of splits) | 15 νe level-1 scores: 29.8 % of splits (legacy 40.6 %) |
| Spearman of split counts vs legacy XML | 0.906 | 0.854 |
| model sha256 | `024cce37…a124` | `4f29962f…2fc3e` |

**Leakage:** 0 overlapping events, 0 duplicate rows and 0 multi-file events, for both models.

**Provenance:**
- The manifests' execution record is kept as written: HEAD `6719fce`, with uncommitted training code.
- A `post_training_provenance` block proves that every training code file, spec and feature list is byte-identical to
  the files committed in `c83965c`.

**Reproducibility:** a second training with the same spec and seed gave a byte-identical JSON and identical margins,
for both models.

**`kine_pio_flag` diagnostic** (ncpi0, flag forced to 0 on the test rows):
- |Δm| > 0.1 for 2.6 % of rows;
- Spearman 0.99984;
- AUC 0.81674 → 0.81679;
- 11 decision changes at m = 0.

**Policy B is unchanged.**

**Legacy control (added later the same day).** The verified MicroBooNE XML bundle reached Aurora after the first version
of this summary, which wrongly said "not available".
- Bundle: `$SP_WORK/legacy_bdt_controls/`, tarball sha256 `90239e2a…08cd8`, four XMLs OK
  (`manifests/dev_round1domain_v1/legacy_controls.json`).
- Evaluated on the **same** test rows: AURORA DEVELOPMENT SAMPLE — LEGACY MICROBOONE CONTROL, not official.

| | numu | ncpi0 |
|---|---:|---:|
| common test rows | 28,396 | 13,467 (13 NaN rows excluded by both) |
| legacy test AUC | 0.9262 | 0.7544 (flag forced to 0) |
| development test AUC | 0.9592 | 0.8167 |
| delta | +0.0330 | +0.0623 |
| legacy at its historical cut: signal efficiency / background acceptance | 62.05 % / 5.81 % (> 0.4) | 39.40 % / 12.58 % (> −0.05) |
| development at the same signal efficiency: background acceptance | 2.67 % | 7.05 % |
| development at the same background acceptance: signal efficiency | 79.35 % | 54.57 % |
| Spearman, legacy score vs development margin | 0.923 | 0.651 |

The last two pairs of rows are DIAGNOSTIC ROC-EQUIVALENT POINTS, NOT ROUND-2 CUTS. Details are in the two model
reports.

Model reports:
- `SP_NUMU_DEVELOPMENT_TRAINING_REPORT.md`;
- `SP_NCPI0_DEVELOPMENT_TRAINING_REPORT.md`.

Compact summary: `validation/dev_round1domain_v1_summary.json`.

## 4. Score scale

The native score is the `binary:logitraw` raw margin, `m = Σ leaf` with `base_score` 0. `predict()` equals
`output_margin`. It is **not** the production `log10((1+v)/(1−v))`.

Before any threshold can be assigned, an exporter and an equivalence test are required, then final models and a joint
threshold procedure fixed in advance (`SP_BDT_SCORE_SCALE_AND_EXPORT_REQUIREMENTS.md`). No legacy threshold is drawn on
any plot.

## 5. What we learned from development training

1. **The chain works end to end.** Full-list tables, labels, split, a fixed-parameter fit, manifest and plots are
   deterministic, firewalled and leakage-free.
2. **SP numu** reaches test AUC 0.959 on aurora-r2, against 0.926 for the legacy XML on the same rows. It **still
   relies most on `numu_score` and `numu_1_score`**, as the legacy XML does, so the final model must be trained on
   Xuyang's new upstream values.
3. **SP ncpi0** reaches test AUC 0.817 with a **large train/test gap** (0.17).
   - On the same held-out rows the legacy MicroBooNE model reaches only 0.754. The development model does not
     generalize worse than the legacy one: the gap is variance, not a loss relative to the inherited model.
   - Its negative class is 4.5k training rows, against MicroBooNE's 37k.
   - The development model leans less on the 15 νe level-1 scores than the thesis model.
   - The development model makes little use of `kine_pio_flag`, which is largely redundant with `kine_pio_mass` in SBND.
4. **XGBoost conventions** that the final export must respect:
   - under `logitraw` the `base_score` is a raw margin;
   - XGBoost's `error` metric thresholds the margin at 0.5.

## 6. What remains required for the final Round-2 models

- **SP numu:**
  - frozen DL vertex and reconstruction;
  - frozen Xuyang νμ chain;
  - Haiwang's Aurora training refresh;
  - retraining on the refreshed values;
  - exporter and equivalence test.
- **SP ncpi0:**
  - frozen DL vertex and reconstruction;
  - confirmation that the 15 νe level-1 models stay fixed;
  - the training refresh;
  - ideally an NC π⁰-enriched training sample, if the collaboration produces one;
  - exporter and equivalence test.
- **Both:**
  - a threshold procedure fixed in advance, on an Aurora validation fold, never on the development test fold or an
    official sample;
  - the deployment route.

**Neither development JSON is deployable.** The final readiness in `SP_BDT_ROUND2_FREEZE_ORDER.md` is unchanged:
nothing is ready for production.
