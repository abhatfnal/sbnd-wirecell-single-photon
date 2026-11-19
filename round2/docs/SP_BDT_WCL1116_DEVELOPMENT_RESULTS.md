# SP BDT development on the WCL1116 vertex refresh: results

Date: 2026-11-17; SP nue developed 2026-11-18; SP other developed 2026-11-19 (the campaign is complete). Campaign `development_wcl1116_v1`; plan in
`SP_BDT_WCL1116_DEVELOPMENT_PLAN.md`. Four-model view: `SP_BDT_WCL1116_FOUR_MODEL_DEVELOPMENT_SUMMARY.md`.
- Every model is **`…_DEV_DO_NOT_DEPLOY`**.
- Every number below is an **Aurora DEVELOPMENT HOLDOUT** result (odd subruns), conditional on an upstream DL vertex
  trained on Aurora events. None is an independent end-to-end measurement
  (`AURORA_UMBRELLA_MODEL_TRAINING_AND_EVALUATION_POLICY.md`).
- **No FermiGrid product was read.** No threshold, vertex mode or final model was chosen.

Compact machine summary: `validation/wcl1116_dev_summary.json`.

## 1. Inputs and tables

| sample | manifest | files | events | excluded | tables (both trees) |
|---|---|---:|---:|---|---|
| `wcl1116-aurora-ncdr` | `manifests/wcl1116_dev_v1/manifest_wcl1116-aurora-ncdr.tsv.gz` (content sha256 in `inputs.json`) | 17,604 | 26,745 | none | 24,031 candidates; 0 errors; 38 / 44 files with an unreadable label branch (split / snap) |
| `wcl1116-aurora-bnb` | `…/manifest_wcl1116-aurora-bnb.tsv.gz` | 11,874 | 626,441 | **14 PARTIAL units** (764 CAF events, 729 Wire-Cell events, 0.12 %), recorded in `inputs.json` | 301,830 candidates; 0 errors; 48 / 49 files with an unreadable `T_truth_pf` |
| `wcl1116-fg-beamoff-train` | `…/beamoff_train_membership.{json,tsv.gz}`; staging record `…/beamoff_train_staging.{json,tsv.gz}` | 558 (572 − 14 hold-out), verified 558 / 558 | 26,418 | none | 2,495 candidates; 0 errors; stamp `HEAD-0.38.0` (= toolkit c935e30d; `WCL1116_TOOLKIT_PROVENANCE_NOTE.md`); PBS 9102859 (2026-11-19); SP other EXT only |
| `wcl1116-aurora-nuecc` | `…/manifest_wcl1116-aurora-nuecc.tsv.gz` (`inputs_nue.json`) | 61,238 | 268,783 | 11 PARTIAL + 3 FAIL units (63 CAF events) | 265,367 candidates; 0 errors; PBS 9100111 (2026-11-18); SP nue only |

**Selection rule.** Status OK, both of Haiwang's validations PASS, and both trees merged.
- Lists and manifests were written read-only on Haiwang's area by `tools/make_refresh_list.py`.
- They ran in PBS 9099500 (debug, 2 nodes, `neutrinoGPU::WireCell_aurora`): census 35 s, builds 11–13 min.
- Every training file carries `wct_version` `0.38.0`.
- The trainer refuses any build whose recorded tree differs from the spec's.

## 2. Reconstruction migration before training (`validation/wcl1116_migration_study.json`)

Matched on the same files, aurora-r2 (old) vs WCL1116 split-move vs snap.

**Candidate-formation ceiling** (truth single-photon signal neutrinos):

| sample | truth signal ν | with ≥1 candidate: old / split / snap | with ≥1 **preselected** candidate: old / split / snap | preselected signal within 1 cm of the SCE true vertex: old / split / snap |
|---|---:|---|---|---|
| NC Δ | 22,653 | 0.907 / 0.912 / 0.912 | **0.676 / 0.661 / 0.654** | **0.243 / 0.571 / 0.516** |
| BNB | 4,585 | 0.782 / 0.785 / 0.785 | **0.570 / 0.569 / 0.567** | **0.237 / 0.489 / 0.400** |

- The DL vertex roughly **doubles** the fraction of usable signal candidates within 1 cm of the true vertex.
  Split-move beats snap there, most clearly on BNB.
- The ceiling of signal neutrinos with a usable preselected candidate **drops slightly**: −1.6 / −2.3 points on NC Δ
  and −0.1 / −0.4 on BNB. This is a reconstruction-level change, kept apart from every classifier number below.

**Populations, preselected rows** (old / split / snap):

| | NC Δ | BNB |
|---|---|---|
| preselected candidates | 16,615 / 16,212 / 16,064 | 65,905 / 65,792 / 66,214 |
| SP signal rows | 15,326 / 14,971 / 14,813 | 2,614 / 2,610 / 2,598 |
| SP numu negatives (νμ CC) | 334 / 323 / 326 | 38,509 / 37,923 / 38,322 |
| SP ncpi0 negatives (NC π⁰) | 270 / 285 / 288 | 8,653 / 9,267 / 9,236 |
| SP other MC negatives (NC no π⁰, out-of-FV, cosmic) | 671 / 620 / 625 | 14,662 / 14,500 / 14,563 |
| SP nue negatives (νe CC) | 14 / 13 / 12 | 1,238 / 1,239 / 1,231 |
| non-finite preselected (ncpi0 inputs only) | 24 / 2 / 2 | 51 / 52 / 24 |

**Matched-candidate migration:**

| | NC Δ old→split | NC Δ split→snap | BNB old→split | BNB split→snap |
|---|---:|---:|---:|---:|
| candidates only in the second domain | 16 | 0 | 481 | 0 |
| same `cluster_id` | 65.5 % | 99.8 % | 88.7 % | 99.2 % |
| vertex moved > 1 cm | 63 % | 11 % | 35 % | 17 % |
| median vertex shift | 6.9 cm | 0.35 cm | 0.44 cm | 0.38 cm |
| `shw_sp_filled` flips 0→1 / 1→0 | 2,422 / 2,877 | 372 / 523 | 11,855 / 12,745 | 3,882 / 3,391 |
| filled rows with a changed 20 MeV shower count | 34 % | 3.6 % | 29 % | 9.5 % |

- aurora-r2 → WCL1116 is a **large** change in which cluster a candidate is built on, and in its vertex and shower
  assignment; on NC Δ a third of candidate slots point to a different cluster.
- Split-move ↔ snap is a **small** change on the same clusters.

## 3. Old → refreshed feature shift (preselected rows, marginal distributions)

| feature set | NC Δ old→split: median KS / max KS / fraction KS > 0.1 | BNB old→split | split↔snap, both samples: median KS |
|---|---|---|---|
| SP numu (73) | 0.142 / 0.448 / 71 % | 0.052 / 0.153 / 14 % | 0.005–0.008 |
| SP ncpi0 (45) | 0.103 / 0.448 / 51 % | 0.032 / 0.153 / 4 % | 0.005–0.006 |
| SP other (146) | 0.108 / 0.448 / 51 % | 0.025 / 0.153 / 14 % | 0.003–0.009 |
| SP nue (56) | 0.128 / 0.263 / 66 % | 0.025 / 0.122 / 7 % | 0.007 |

- The largest shifts are in vertex- and segment-counting inputs: `shw_sp_br1_1_vtx_n_segs`, `shw_sp_lol_3_vtx_n_segs`,
  `shw_sp_br4_1_n_vtx_segs`, `kine_pio_dis_*`. The vertex-distance family has the highest median KS in ncpi0: 0.45 on
  NC Δ.
- Then shower start dQ/dx (`shw_sp_vec_mean/median_dedx`, `shw_sp_vec_dQ_dx_*`).
- The upstream `numu_1_score` and the νe L1 scores move because their inputs move, even with unchanged weights.
- Snap vs split-move: every family has median KS ≤ 0.017.

## 4. Exact legacy MicroBooNE controls in the new domain

The legacy XMLs were scored once, as log10-odds; ncpi0 with `kine_pio_flag = 0`. These are all preselected rows of
each sample; the historical cuts are diagnostics only.

| legacy model | sample | AUC old / split / snap | signal pass at the historical cut: old / split / snap | negative pass: old / split / snap |
|---|---|---|---|---|
| SP numu (> 0.4) | BNB | 0.913 / 0.934 / 0.929 | 0.567 / 0.707 / 0.711 | 0.058 / 0.064 / 0.072 |
| SP ncpi0 (> −0.05) | BNB | 0.741 / 0.793 / 0.792 | 0.415 / 0.458 / 0.448 | 0.126 / 0.108 / 0.106 |
| SP other (> 0.2), MC components only | BNB | 0.743 / 0.777 / 0.775 | 0.334 / 0.425 / 0.430 | 0.098 / 0.121 / 0.120 |
| SP nue (> −1.0) | BNB (νe CC negatives) | 0.854 / 0.903 / 0.907 | 0.622 / 0.770 / 0.783 | 0.141 / 0.137 / 0.138 |
| SP numu | NC Δ (signal) | — | 0.625 / 0.846 / 0.845 | — |

The inherited models **rank better** in the refreshed reconstruction. Their **operating points move a lot**: signal
pass rates rise by 9–22 points at unchanged cuts.

## 5. Development models

Fixed thesis settings, `base_score` 0, seed 1, no weights, no tuning. Each JSON is byte-identical on a repeat. Leakage
checks: 0 overlapping events, 0 duplicate rows, 0 multi-file events.

| model | vertex mode | train rows +/− | holdout rows +/− | legacy AUC | dev AUC | status |
|---|---|---:|---:|---:|---:|---|
| SP numu | dv2_split_move | 8,761 / 19,180 | 8,821 / 19,066 | 0.9584 | **0.9759** | DEV_DO_NOT_DEPLOY; UPSTREAM_NUMU = SHIPPED_CONTROL |
| SP numu | dv2_snap | 8,667 / 19,408 | 8,745 / 19,240 | 0.9536 | **0.9739** | DEV_DO_NOT_DEPLOY; UPSTREAM_NUMU = SHIPPED_CONTROL |
| SP ncpi0 | dv2_split_move | 8,760 / 4,757 | 8,820 / 4,790 | 0.8485 | **0.8992** | DEV_DO_NOT_DEPLOY; Policy B; νe L1 as stored |
| SP ncpi0 | dv2_snap | 8,666 / 4,751 | 8,744 / 4,770 | 0.8469 | **0.8974** | DEV_DO_NOT_DEPLOY; Policy B; νe L1 as stored |
| SP other | dv2_split_move | 8,761 / 7,881 | 8,821 / 7,748 | 0.8398 | **0.9153** | DEV_DO_NOT_DEPLOY; UPSTREAM_NUMU = SHIPPED_CONTROL (2026-11-19; `SP_OTHER_WCL1116_DEVELOPMENT_REPORT.md`) |
| SP other | dv2_snap | 8,667 / 7,939 | 8,745 / 7,757 | 0.8360 | **0.9121** | DEV_DO_NOT_DEPLOY; UPSTREAM_NUMU = SHIPPED_CONTROL |
| SP nue | dv2_split_move | 8,819 / 106,623 | 8,871 / 106,808 | 0.9176 | **0.9588** | DEV_DO_NOT_DEPLOY (2026-11-18; `SP_NUE_WCL1116_DEVELOPMENT_REPORT.md`) |
| SP nue | dv2_snap | 8,722 / 106,676 | 8,791 / 106,810 | 0.9143 | **0.9524** | DEV_DO_NOT_DEPLOY |

- **Train / holdout gap:** numu 0.019 (split) / 0.019 (snap); ncpi0 0.089 / 0.091. For reference, the Round-1-domain
  development models had 0.028 and 0.17.
- **Model sha256:**
  - numu split `b440543a…`, snap `45d721b2…`;
  - ncpi0 split `c5406d20…`, snap `23fb495d…`.
- **Stored under** `$SP_WORK/wcl1116_dev_models/<mode>/<model>/`, with the JSON, a repeat, margins, importances, ROC and
  metrics. Manifests: `manifests/wcl1116_dev_v1/single_photon_<model>_<mode>_dev_manifest.json`. They record:
  - the input manifest and list hashes;
  - the vertex mode and tree;
  - the spec and feature-list hashes;
  - the code commit and per-file hashes;
  - XGBoost 3.4.1, seed 1;
  - counts and the model sha256.

  The exported XML sha256 is in the export summaries (§12).

**Reference only, not a like-for-like comparison** (different rows and domain): the Round-1-domain development models
on aurora-r2 reached 0.959 (numu) and 0.817 (ncpi0), against legacy 0.926 and 0.754.

## 6. Legacy vs new: ROC-equivalent points on common holdout rows

**DEVELOPMENT ROC-EQUIVALENT DIAGNOSTIC — NOT ROUND2 CUT.** The legacy cut is never carried onto the native margin.

| model / mode | legacy at its historical cut: signal eff. / bkg acceptance | new at the same signal efficiency: bkg acceptance | new at the same bkg acceptance: signal efficiency |
|---|---|---|---|
| SP numu split-move | 82.4 % / 6.27 % | **2.91 %** | **90.3 %** |
| SP numu snap | 82.5 % / 7.16 % | **3.44 %** | **90.3 %** |
| SP ncpi0 split-move | 51.7 % / 10.4 % | **5.0 %** (at 49.5 %: margin ties) | **71.4 %** |
| SP ncpi0 snap | 51.1 % / 10.3 % | **5.0 %** | **71.7 %** |

Details: `$SP_WORK/wcl1116_legacy_controls/<mode>/<model>/legacy_vs_dev.json`.

## 7. Snap vs split-move as a BDT input domain

1. **Reconstruction level (§2).**
   - Split-move puts more usable signal candidates within 1 cm of the true vertex: 0.571 vs 0.516 (NC Δ), 0.489 vs
     0.400 (BNB).
   - Split-move has a slightly higher preselected-signal ceiling on NC Δ (0.661 vs 0.654). On BNB the two are equal
     within 0.3 points.
   - Class populations differ by < 1.5 %.
2. **Legacy control.** Holdout AUC split / snap: numu 0.958 / 0.954; ncpi0 0.849 / 0.847.
3. **New development models.** Holdout AUC split / snap: numu 0.976 / 0.974; ncpi0 0.899 / 0.897. Similar gaps and
   importances.
4. **Fair matched comparison** on holdout candidates present in both modes with the same key and class (bootstrap of
   200 event resamples):

| model | common rows +/− | rows only in split / only in snap | dev AUC split / snap | snap − split (± sd) | legacy AUC split / snap | snap − split (± sd) |
|---|---|---|---|---|---|---|
| SP numu | 8,541 / 17,792 | 1,554 / 1,652 | 0.9759 / 0.9744 | −0.0015 ± 0.0004 | 0.9582 / 0.9548 | −0.0034 ± 0.0005 |
| SP ncpi0 | 8,539 / 4,684 | 387 / 291 | 0.9005 / 0.8993 | −0.0010 ± 0.0015 | 0.8503 / 0.8489 | −0.0012 ± 0.0015 |

**Reading.**
- On the same candidates, split-move is better by a small, statistically resolved amount for numu, and
  indistinguishable for ncpi0. It is also better on vertex accuracy, with a marginally higher NC Δ ceiling.
- **This is development evidence for split-move, not a decision.** The differences are ≤ 0.002 AUC on matched
  candidates.
- The mode is a collaboration decision, taken together with Xuyang's upstream-BDT and Matteo's downstream studies. No
  mode is frozen here.

## 8. Feature sanity (split counts vs the exact legacy fingerprints)

| | Spearman of split counts vs legacy (split / snap) | top-10 overlap with legacy | key structure |
|---|---|---|---|
| SP numu | 0.876 / 0.898 | 6 / 10 | `numu_score` rank 1 and `numu_1_score` rank 3 in both modes (legacy ranks 1 and 3); the νμ pair is 8.4 % / 8.7 % of splits (legacy 11.5 %); then shower energy (`shw_sp_E_indirect_max_energy`), muon-track length (`numu_cc_3_track_length`, `numu_cc_3_max_length_all`), shower-vertex distance and dQ/dx |
| SP ncpi0 | 0.816 / 0.800 | 9 / 10 | π⁰ kinematics dominate: 49 % / 50 % of splits (legacy 36 %); the 15 νe L1 scores 26 % / 25 % (legacy 41 %); `kine_pio_mass` rank 3 / 7; `kine_pio_flag` rank 45 / 45 (never split: redundant with `kine_pio_mass` in SBND) |

No bookkeeping identifier (run, subrun, event, file, cluster or candidate index) is an input, so none can gain
importance. Both models learned physically sensible structures close to the legacy fingerprints.

## 9. SP other

**Developed 2026-11-19** (`SP_OTHER_WCL1116_DEVELOPMENT_REPORT.md`):
- the beam-off training half was pushed by Avinay and verified 558 / 558;
- 509 / 508 EXT rows (old reconstruction: 481);
- holdout AUC 0.915 / 0.912 against legacy 0.840 / 0.836;
- pre-registered verdict **RETRAINING CLEARLY BENEFICIAL** (+0.076 in both modes).

History: updated 2026-11-18 in `SP_OTHER_WCL1116_DEVELOPMENT_REPORT.md`:
- the established route was found (Xuyang's gpvm rsync push, ALCF passcode);
- the staging script and verifier are ready, and the verifier rejects the old fg1 copy;
- the target audit is frozen;
- the MC census is done.

The transfer itself needs Avinay's gpvm session. The text below is the original 2026-11-17 status.

- **Membership.** The frozen `fg1-beamoff-train` list (sha256 `acb69100…`, 572 pairs, 80 runs, all odd) minus the 14
  hold-out files gives **558** pairs. There is zero overlap with the even-run evaluation half by construction.
  - The refreshed pair ids keep the same form: 3 of the 42 from-reco1 pairs and 9 of the 11 pilot pairs on Aurora are
    training-side ids.
  - Expected location: `/pnfs/sbnd/persistent/users/yuhw/prod-fermigrid/WCLocal2026Nov16/beam-off/<id>/`, which is not
    readable from Aurora (no `/pnfs`).
- **Prepared.**
  - Specs `single_photon_other_training_spec_dev_wcl1116_{dv2_split_move,dv2_snap}.yaml`: status
    `BLOCKED_DATA_STAGING`, 146 inputs, 5 / 215, `base_score` 0.
  - The narrowly scoped exception: Avinay, development only, this odd-run membership only.
  - The run-based EXT split (run % 4 == 1 → holdout).
  - The SP other development label: NC no π⁰, out-of-FV (dirt included), cosmic-matched / unmatched MC and EXT rows
    are negatives.
- **Ready to run.** The MC components are already in the WCL1116 tables: 14,500 / 14,563 BNB negatives and 620 / 625
  NC Δ negatives (§2). Once the 558 refreshed beam-off CAFs are on Aurora, the same builder, trainer, legacy control
  and export run unchanged.
- **Evaluation beam-off was not substituted.**

## 10. SP nue domain shift (no training)

| evidence | aurora-r2 → split-move | aurora-r2 → snap | split ↔ snap |
|---|---|---|---|
| 56-input median KS, NC Δ / BNB | 0.128 / 0.025 | 0.123 / 0.027 | 0.007 / 0.007 |
| inputs with KS > 0.1, NC Δ | 66 % | 61 % | 4 % |
| matched rows whose inputs changed, median | 64 % / 48 % | 58 % / 45 % | 35 % / 33 % |
| legacy SP nue AUC, BNB signal vs νe CC | 0.854 → 0.903 | 0.854 → 0.907 | 0.903 vs 0.907 |
| legacy signal pass at −1.0, BNB / NC Δ | 0.622 → 0.770 / 0.611 → 0.785 | 0.622 → 0.783 / 0.611 → 0.783 | ±0.01 |
| legacy pass/fail migration at −1.0 (matched, BNB) | 3,361 pass→fail, 5,905 fail→pass of 53,458 | similar | 2,497 / 2,564 of 62,327 |

**Classification: LARGE.** The criteria were applied after the measurement and were not pre-registered in the plan:
- small: |ΔAUC| < 0.01 and |Δ signal efficiency| < 2 points and median KS < 0.05;
- large: |ΔAUC| > 0.03 or |Δ efficiency| > 5 points or median KS > 0.15;
- moderate otherwise.

SP nue fails "small" on every axis: ΔAUC +0.05, Δ signal efficiency +15–17 points, and NC Δ median KS 0.12–0.13.

**Developed 2026-11-18** (`SP_NUE_WCL1116_DEVELOPMENT_REPORT.md`):
- holdout AUC 0.959 / 0.952 against legacy 0.918 / 0.914 on identical rows;
- pre-registered verdict **RETRAINING CLEARLY BENEFICIAL** (+0.041 ± 0.0008 / +0.038 ± 0.0009).

The recommendation as written before training:

**Recommendation (not a freeze decision): SP-NUE RETRAINING SHOULD BE DEVELOPED.**
- The inherited response improved, but its operating point is no longer the thesis one.
- The two SBND-retrained siblings beat their legacy XMLs by +0.018 (numu) and +0.051 (ncpi0) AUC on the same
  refreshed rows.
- The νe CC negatives (thesis: 100,958 events) need the refreshed `wcl1116-aurora-nuecc`, which is still completing.
  BNB holds only about 1.2k νe CC rows.
- So: develop when νe CC completes, keep the legacy XML as the control, and do not freeze.

## 11. Cosmic-tagger-boundary dependence (from the toolkit, WCT 0.38.0)

The planned production with "more realistic cosmic-tagger boundaries" touches `PatternAlgorithms::cosmic_tagger()`
(`clus/src/NeutrinoTaggerCosmic.cxx`). Its boundary parameters are:
- the four "reaches the top" y cuts `cosmic_y_top_main` / `_strict` / `_loose` / `_small_piece`, re-anchored to SBND's
  y = +200 cm (`clus.jsonnet` `sbnd_y_top`);
- the consistent-FV routing (`cosmic_consistent_fv`, tolerances).

`cosmic_tagger()` writes **every** `cosmict_*` and `cosmic_*` field and `neutrino_type`. It only fills BDT inputs; it
gates no other tagger (`TaggerCheckNeutrino.cxx`, around 4455). The νμ, νe, single-photon and kinematics taggers read
none of its outputs: `NeutrinoTaggerNuMu.cxx` mentions it only in a comment, and `NeutrinoTaggerNuE.cxx`,
`NeutrinoTaggerSinglePhoton.cxx`, `NeutrinoEnergyReco.cxx` and `NeutrinoKinematics.cxx` have 0 references.

| SP model | direct cosmic-tagger inputs | through upstream scores | class |
|---|---|---|---|
| **SP other** | **60 of 146** (`cosmict_*`, `cosmic_*`) | `cosmict_10_score` (cos_tagger_10 on `cosmict_10_*`) and `numu_score`, 61 of whose 74 inputs are cosmic-tagger outputs | **DEFINITELY REQUIRES RETRAINING** after a boundary change |
| **SP numu** | 0 of 73 | `numu_score`, its rank-1 input; 61 / 74 of the νμ-final inputs come from `cosmic_tagger()`. `numu_1_score` (numu_tagger1 on `numu_cc_1_*`) is unaffected | **POTENTIALLY AFFECTED**, through `numu_score`. In practice retrained anyway after the upstream νμ freeze; one retrain covers both if both land together |
| SP ncpi0 | 0 of 45 | the 15 νe L1 scores come from `NeutrinoTaggerNuE` (no cosmic reference) | **LIKELY INSENSITIVE** |
| SP nue | 0 of 56 (`shw_sp_*` only) | none | **LIKELY INSENSITIVE** |

**Caveat.** This holds if the change is confined to `cosmic_tagger()`. If the later production also changes how
clusters are tagged or separated at the clustering / flash-matching stage, candidate formation moves for every model.
`tools/wcl1116_migration_study.py` then measures it exactly as here, before any refit.

## 12. Export

**Python.** Every development model was exported with `sp_retrain/export_tmva.py`:
- XML, native JSON, ordered `.features.json` and `.sha256` in `$SP_WORK/wcl1116_export/<mode>/<model>/`.
- Checked by `tools/export_equivalence_check.py`; summaries in
  `validation/wcl1116_export_equivalence_{dv2_split_move,dv2_snap}.json`. All pass in both modes:
  - XML forest sum = double leaf sum, exactly;
  - native margin within `1e-5·max(1,|m|)`; max |Δm| is 1.2e-5 (numu) and 7.4e-6 (ncpi0), from XGBoost's float32 sum;
  - per-tree leaves identical on every holdout row;
  - equality routing 1,200 / 1,200 identical;
  - 0 flips at the fixture and quantile-midpoint cuts;
  - the order guard refuses a swapped list;
  - NaN → −999.

**C++: VERIFIED.**
- Setup:
  - `cpp/sp_export_regression.cxx`, built and run in Haiwang's SL7 WCT 0.38.0 environment on an Aurora compute node:
    PBS 9099556, `neutrinoGPU::WireCell_aurora`, about 1 min; his build used read-only.
  - ROOT 6.28/12, gcc 12.1, `opt-0.38.0` `libWireCellRoot`.
  - Fixtures: the 4 WCL1116 development models plus the 2 Round-1-domain development models. Per model, 3,000 holdout
    rows, 300 rows forced onto exact split thresholds, 5 NaN rows and 5 ±FLT_MAX rows.
  - Summaries: `validation/cpp_export_equivalence_*.json`; Python side `tools/cpp_equivalence_check.py`.
- Results:

| check | result (all 6 models) |
|---|---|
| `TMVA::Reader::EvaluateMVA` vs toolkit `TmvaGradForest::evaluate` | **bit-identical on 3,310 / 3,310 rows** |
| C++ vs Python `sp_retrain.tmva_grad` | max \|Δ\| ≤ 4.4e-16: bit-identical on 99.3–99.97 % of finite rows, otherwise 1–2 ulp from tanh rounding |
| tanh(native XGBoost margin) vs C++ | ≤ 1.2e-6 (XGBoost's float32 accumulation) |
| NaN input | −999 in both readers |
| swapped variable order | refused by `TmvaGradForest` |
| decision flips (log10-odds at the fixture cut and 5 quantile midpoints) | 0 |

The exporter chain is now verified end to end, from native XGBoost JSON through the exported TMVA Grad XML to the
production C++ readers. These are development fixtures only; none of these models is deployable.

**2026-11-18:** the two SP nue development models pass the same C++ check (PBS 9100172): bit-identical on 3,310 / 3,310
rows per mode, C++ vs Python ≤ 4.4e-16, 0 flips (`validation/cpp_export_equivalence_wcl1116_<mode>_nue.json`).

**2026-11-19:** the two SP other development models pass the same C++ check (PBS 9102928): bit-identical on
3,310 / 3,310 rows per mode, C++ vs Python ≤ 4.4e-16, 0 flips (`validation/cpp_export_equivalence_wcl1116_<mode>_other.json`).
All eight WCL1116 development models are now verified end to end.

## 13. Not done; what comes next

- No final SP model, threshold, vertex-mode choice or FermiGrid use.
- No enriched-sample request. SP nue was developed on 2026-11-18 (§10), and SP other on 2026-11-19 (§9).
- **NC π⁰ statistics on WCL1116** (`validation/ncpi0_negative_learning_curve_wcl1116_{mode}.json`; f = 1 reproduces each
  development model exactly):
  - holdout AUC 0.867 → 0.881 → 0.892 → 0.896 → 0.899 (split-move), and similarly for snap;
  - gain per doubling from 1/2 to 1: +0.0069 (±0.0017 seed sd), against +0.010 before;
  - still **SOME BENEFIT LIKELY**, but flatter;
  - the refresh changes the available negatives only from 4,457 to 4,757 training rows (+7 %): the same BNB events with
    a different NC π⁰ class migration.
- **Next, with no question to anyone yet:**
  - ~~stage the refreshed beam-off training half and develop SP other~~: done 2026-11-19;
  - ~~develop SP nue when νe CC completes~~: done 2026-11-18;
  - re-run this campaign on the final reconstruction (vertex mode, cosmic-boundary production) and on Xuyang/Matteo's
    frozen νμ.
