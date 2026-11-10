# Frozen `single_photon_other_bdt_final.xml`: source audit

Date: 2026-11-10. Branch `analysis/ncdelta-other-bdt-audit-20261110`. Audit only: no retraining, no tuning. Statements are tagged **SOURCE** (read from code/XML), **MEASURED** (from the files/data), or **INFERRED** (flagged).
Companion: `FROZEN_OTHER_BDT_SIGNAL_TOPOLOGY_AUDIT.md`. Machine-readable table: `tables/other_bdt_audit/input_source_table.csv` (the same 146 rows with fill file/line/code).

## 1. The model

| item | value | tag |
|---|---|---|
| weight file | `single_photon_other_bdt_final.xml` | SOURCE |
| location read | `/exp/uboone/app/users/uboonepro/bbogart/wcp-uboone-bdt/weights/` (the frozen MicroBooNE reference bundle) | MEASURED |
| sha256 | `8c0ac375e957f5b332bc35339e4ebcbfef35bb778fb73315b06a814e600dbb16` (identical to `provenance/microboone_reference_SHA256SUMS.txt`) | MEASURED |
| origin | MicroBooNE `wcp-uboone-bdt-eyandel` (`https://github.com/brb-rightback/wcp-uboone-bdt-eyandel.git`, head `0100d4b62193ef3ccdb7d759ce53eb9c1b4bb541`); the single-photon BDT code first appears at `bf9d7113` (2022-09-21, "add in single photon BDTs"); the XMLs themselves are **not tracked in that repository** (`provenance/reference_bundle/weights_source.txt`); booked in the original code as `reader_single_photon_other.BookMVA("MyBDT", "weights/single_photon_other_bdt_final.xml")` | SOURCE |
| model type | TMVA `BDT::BDT`, `BoostType = Grad`, created by **`xgboost2TMVA`** (an XGBoost model converted to a TMVA XML) | SOURCE (XML header) |
| ensemble | **215 trees**, every tree depth 5, 6,251 leaves in total, all `boostWeight = 1.0`; **133 of the 146 inputs are used in at least one split** (13 are never split on) | MEASURED (XML) |
| variables | 146 (`VarIndex` 0-145, table below), type D | SOURCE |
| score | `score = tanh(sum_t boostWeight_t * leaf_t) = 2/(1+exp(-2 sum)) - 1` (TMVA `GetGradBoostMVA`); the frozen cut is `score > 0.2` (`configs/baseline_selection.yaml`), i.e. margin `sum > atanh(0.2) = 0.2027` | SOURCE / config |
| split rule | production C++ `TmvaGradForest::evaluate` (`root/src/TmvaGradForest.cxx`, fg1 commit `4b6853d4`): a node goes **right iff `value >= cut`** (cType 1), float32 values and cuts, leaf responses summed in double | SOURCE |
| missing values | production: **any NaN input gives `-999`** (`Reader::EvaluateMVA` rule in `TmvaGradForest::evaluate`); this repository's offline scorer returns NaN for any non-finite input and the candidate is **not BDT-evaluable** and fails the BDT cuts (same decision). In the studied population no candidate had a non-finite input. XGBoost's learned default direction for missing values is not represented in the TMVA XML | SOURCE / MEASURED |
| preprocessing | none (raw `wc.T_tagger` / `wc.T_kine` values are the inputs; no scaling, no transformation) | SOURCE |
| where it runs | **BDT scores are NOT stored in the CAF.** They are computed offline by `src/sbnd_single_photon/bdt.py` from this XML; the merged CAFs record only `Trun.bdt_weights_dir = uboone/weights` (a path string; the file identity of the production directory is not verifiable from the CAF, so the identity of the model is established through the XML checksum of the reference bundle) | MEASURED |
| production provenance | fg1-compatible Wire-Cell chain, `Trun.wct_version = sbnd-dlvtx-35-pre-master-merge-2026-09-02-424-g78f81c64`, producer-declared commit `4b6853d4` (`HaiwangYu/wire-cell-toolkit`, branch `sbnd-wc-flatcaf`), `Trun.dl_weights = uboone/scn_vtx/t48k-m16-l5-lr5d-res0.5-CP24.pth`, declared "no alternative BDT training" | MEASURED / declared |

## 2. Reproduction of the score

The CAF stores no BDT score, so "agreement with the stored CAF score" cannot be tested. The following was done instead (`scripts/other_bdt_audit.py`, `reproduction` in `tables/other_bdt_audit/summary.json`), on the **5,453 candidates** of the 5,225 official events that reach the numu stage and beyond:
1. Inputs re-read from the merged CAFs reproduce the derived-table score `c_score_other` of the validated baseline: 5,280 candidates compared, **max |difference| = 0.0** (173 candidates have no stored score in the derived table: they are the candidates with `shw_sp_filled == 0`, which the baseline treats as not BDT-evaluable).
2. An **independent evaluator** written from the TMVA/production rules (`other_audit.scores_tmva_float32`: float32 values/cuts, right iff `>=`, float32 leaf responses summed in double) agrees with the frozen scorer to **max 2.9e-9** (median 1.4e-10), with **0 differences above 1e-6 and 0 decision flips at the threshold 0.2**. A transparent per-event scalar reader of the XML agrees with the vectorised independent evaluator exactly (max 0.0, 300 random candidates) and with the frozen scorer to 2.3e-9.
3. The two evaluators differ **only in the convention for an input exactly equal to a cut** (frozen scorer: left iff `x <= cut`, float64; TMVA/production: right iff `x >= cut`, float32). No such tie changes any score at the 1e-6 level in this sample (unit test `test_exact_ties_follow_tmva_rule...` shows the difference exists on constructed ties).
4. Limits: no ROOT/TMVA runtime exists in this environment, so the evaluators were not compared with TMVA itself; the repository's earlier statement "validated 132/132 against ROOT/TMVA" is cited, not re-run. **The frozen score is reproduced exactly with respect to an independent implementation of the documented TMVA rules; that is the basis for the model-internal analysis.**

(MEASURED: all 173 have `shw_sp_filled == 0`, and their score recomputed from the re-read inputs is finite. So the baseline's 'not evaluable' status comes from the `shw_sp_filled == 0` criterion (the inputs are sentinels), not from non-finite values. These 173 are outside every `other`-stage population below, which requires `cum_numu`.)

## 3. Upstream BDT outputs used as inputs

Four of the 146 inputs are **outputs of other BDTs run in the same production** (not detector observables): `numu_score`, `numu_1_score`, `numu_2_score`, `cosmict_10_score`. SOURCE (`root/src/UbooneNumuBDTScorer.cxx`, fg1 `4b6853d4`): `cal_numu_bdts_xgboost()` writes `ti.numu_score` as the log-odds transform `log10((1+v)/(1-v))` of the xgboost numu BDT output `v` (`bdt_log_odds_score` in `TmvaGradForest.cxx`); `numu_1_score` / `numu_2_score` / `cosmict_10_score` are sub-BDT scores (`cal_numu_1_bdt(ti, -0.4)`, `cal_numu_2_bdt(ti, -0.1)`, `cal_cosmict_10_bdt(ti, 0.7)`; the second argument is the fill value used when the sub-BDT has nothing to evaluate). These four are not constant (MEASURED: ranges -5.1..1.7, -0.59..0.20, -0.17..0.11, -0.39..0.71 among the candidates reaching `other`) even though `NeutrinoTaggerInfo.h` declares them with default 0 and no plain `ti.numu_score =` assignment exists in the tagger sources: they are filled by the scorer visitor.

## 4. The 146 inputs

`NeutrinoTaggerInfo.h` (fg1 `4b6853d4`) declares every input as `float name{DEFAULT}` and contains **no per-field documentation comments**; the physical meaning below is therefore taken from the **filling code** (`NeutrinoTagger*.cxx`, file:line and right-hand side shown), not from a description. Units are listed **only where the fill expression states them** (`/ units::cm`, `/ units::MeV`, `/ M_PI * 180`); otherwise "not stated". All inputs are candidate-scoped (one value per neutrino-candidate bundle); 145 come from `wc.T_tagger`, `reco_nuvtxY` from `wc.T_kine.kine_nu_y_corr` (`NeutrinoKinematics.cxx:93/105`, vertex y in cm: the space-charge/position-corrected vertex). "default" = the value the field holds if the code that fills it did not run (`float x{default}`). The last two columns are measured among events reaching `other` (fraction of candidates AT the default value for truth 0p / truth 1p, and the number of splits on the variable in the 215 trees).

Groups (from the variable names and fill code; descriptive only): cosmic-tagger flags/scores (60 inputs, `cosmict_*`/`cosmic_*`, filled in `NeutrinoTaggerCosmic.cxx`); shower calorimetry (31, dQ/dx vectors and summary statistics of the leading shower, `NeutrinoTaggerSinglePhoton.cxx`); shower-quality sub-taggers (22: `br2` bad-reconstruction-1 PCA/stem check, `br4`, `lem`, `hol`); track/proton activity at the vertex (11); shower/vertex geometry (11, incl. `shw_vtx_dis`); shower multiplicity (6); numu tagger scores (4); vertex position (1).

Important source facts for the interpretation:
* `shw_sp_*` quantities describe the single **`max_shower`** chosen by the single-photon tagger (see `WIRECELL_SOURCE_CONVENTIONS_AUDIT.md` section 5).
* **`shw_sp_br2_*` (`bad_reconstruction_1_sp`, `NeutrinoTaggerSinglePhoton.cxx:535-664`) is evaluated only when the leading shower's start segment is directly attached to the main vertex**: `badreco2 = sg_at_main ? !bad_reconstruction_1_sp(...) : true` (line ~2461). If the shower is not attached, the `br2` fields stay at their default 0. `shw_sp_hol_2_*` likewise depends on the segments connected at the vertex. MEASURED: `br2` at default is **equivalent to `shw_sp_shw_vtx_dis != 0`** (2,237 of 2,238 events; one exception), i.e. to "the leading shower is detached from the vertex".
* `reco_nuvtxY` is read from `T_kine`, not `T_tagger`.

| idx | variable | CAF branch | declared default | first fill (file:line) | fill expression (RHS) | units (from fill code) | fraction at default 0p / 1p | splits |
|---|---|---|---|---|---|---|---|---|
| 0 | `cosmict_flag_2` | `wc.T_tagger.cosmict_flag_2` | 0 | NTCosmic:1372 | `flag_cosmic_2;` | not stated in the fill expression | 0.98 / 0.99 | 1 |
| 1 | `cosmict_2_filled` | `wc.T_tagger.cosmict_2_filled` | 0 | NTCosmic:681 | `1;` | not stated in the fill expression | 0.59 / 0.70 | 5 |
| 2 | `cosmict_2_particle_type` | `wc.T_tagger.cosmict_2_particle_type` | 0 | NTCosmic:682 | `muon->has_particle_info() ? muon->particle_info()->pdg() : 0` | not stated in the fill expression | 0.59 / 0.70 | 11 |
| 3 | `cosmict_2_n_muon_tracks` | `wc.T_tagger.cosmict_2_n_muon_tracks` | 0 | NTCosmic:683 | `n_muon_tracks;` | not stated in the fill expression | 0.69 / 0.76 | 15 |
| 4 | `cosmict_2_total_shower_length` | `wc.T_tagger.cosmict_2_total_shower_length` | 0 | NTCosmic:684 | `static_cast<float>(total_shower_length / units::cm);` | cm | 0.96 / 0.97 | 10 |
| 5 | `cosmict_2_flag_inside` | `wc.T_tagger.cosmict_2_flag_inside` | 1 | NTCosmic:685 | `flag_inside;` | not stated in the fill expression | 1.00 / 0.99 | 5 |
| 6 | `cosmict_2_angle_beam` | `wc.T_tagger.cosmict_2_angle_beam` | 0 | NTCosmic:686 | `static_cast<float>(dir.angle(dir_beam) / M_PI * 180.0);` | degrees | 0.59 / 0.70 | 48 |
| 7 | `cosmict_2_flag_dir_weak` | `wc.T_tagger.cosmict_2_flag_dir_weak` | 0 | NTCosmic:687 | `seg_dir_weak(muon);` | not stated in the fill expression | 0.59 / 0.70 | 3 |
| 8 | `cosmict_2_dQ_dx_end` | `wc.T_tagger.cosmict_2_dQ_dx_end` | 0 | NTCosmic:688 | `static_cast<float>(dQ_dx_end / m_mip_dqdx_median);` | not stated in the fill expression | 0.59 / 0.70 | 74 |
| 9 | `cosmict_2_dQ_dx_front` | `wc.T_tagger.cosmict_2_dQ_dx_front` | 0 | NTCosmic:689 | `static_cast<float>(dQ_dx_front / m_mip_dqdx_median);` | not stated in the fill expression | 0.59 / 0.70 | 52 |
| 10 | `cosmict_2_theta` | `wc.T_tagger.cosmict_2_theta` | 0 | NTCosmic:690 | `static_cast<float>(vec_theta(dir) / M_PI * 180.0);` | degrees | 0.59 / 0.70 | 34 |
| 11 | `cosmict_2_phi` | `wc.T_tagger.cosmict_2_phi` | 0 | NTCosmic:691 | `static_cast<float>(vec_phi(dir) / M_PI * 180.0);` | degrees | 0.59 / 0.70 | 54 |
| 12 | `cosmict_2_valid_tracks` | `wc.T_tagger.cosmict_2_valid_tracks` | 0 | NTCosmic:692 | `valid_tracks;` | not stated in the fill expression | 0.64 / 0.73 | 19 |
| 13 | `cosmict_flag_4` | `wc.T_tagger.cosmict_flag_4` | 0 | NTCosmic:1374 | `flag_cosmic_4;` | not stated in the fill expression | 1.00 / 1.00 | 0 |
| 14 | `cosmict_4_filled` | `wc.T_tagger.cosmict_4_filled` | 0 | NTCosmic:764 | `1;` | not stated in the fill expression | 0.59 / 0.70 | 0 |
| 15 | `cosmict_4_flag_inside` | `wc.T_tagger.cosmict_4_flag_inside` | 0 | NTCosmic:765 | `flag_inside;` | not stated in the fill expression | 0.60 / 0.71 | 11 |
| 16 | `cosmict_4_angle_beam` | `wc.T_tagger.cosmict_4_angle_beam` | 0 | NTCosmic:766 | `static_cast<float>(dir.angle(dir_beam) / M_PI * 180.0);` | degrees | 0.59 / 0.70 | 26 |
| 17 | `cosmict_4_connected_showers` | `wc.T_tagger.cosmict_4_connected_showers` | 0 | NTCosmic:767 | `connected_showers;` | not stated in the fill expression | 0.79 / 0.86 | 7 |
| 18 | `cosmict_flag_3` | `wc.T_tagger.cosmict_flag_3` | 0 | NTCosmic:1373 | `flag_cosmic_3;` | not stated in the fill expression | 1.00 / 1.00 | 1 |
| 19 | `cosmict_3_filled` | `wc.T_tagger.cosmict_3_filled` | 0 | NTCosmic:738 | `1;` | not stated in the fill expression | 1.00 / 1.00 | 1 |
| 20 | `cosmict_3_flag_inside` | `wc.T_tagger.cosmict_3_flag_inside` | 0 | NTCosmic:739 | `flag_inside;` | not stated in the fill expression | 1.00 / 1.00 | 1 |
| 21 | `cosmict_3_angle_beam` | `wc.T_tagger.cosmict_3_angle_beam` | 0 | NTCosmic:740 | `static_cast<float>(dir.angle(dir_beam) / M_PI * 180.0);` | degrees | 1.00 / 1.00 | 6 |
| 22 | `cosmict_3_flag_dir_weak` | `wc.T_tagger.cosmict_3_flag_dir_weak` | 0 | NTCosmic:741 | `last_sg ? seg_dir_weak(last_sg) : false;` | not stated in the fill expression | 1.00 / 1.00 | 0 |
| 23 | `cosmict_3_dQ_dx_end` | `wc.T_tagger.cosmict_3_dQ_dx_end` | 0 | NTCosmic:743 | `static_cast<float>(dQ_dx_end   / m_mip_dqdx_median);` | not stated in the fill expression | 1.00 / 1.00 | 9 |
| 24 | `cosmict_3_dQ_dx_front` | `wc.T_tagger.cosmict_3_dQ_dx_front` | 0 | NTCosmic:742 | `static_cast<float>(dQ_dx_front / m_mip_dqdx_median);` | not stated in the fill expression | 1.00 / 1.00 | 6 |
| 25 | `cosmict_3_theta` | `wc.T_tagger.cosmict_3_theta` | 0 | NTCosmic:744 | `static_cast<float>(vec_theta(dir) / M_PI * 180.0);` | degrees | 1.00 / 1.00 | 3 |
| 26 | `cosmict_3_phi` | `wc.T_tagger.cosmict_3_phi` | 0 | NTCosmic:745 | `static_cast<float>(vec_phi(dir)   / M_PI * 180.0);` | degrees | 1.00 / 1.00 | 2 |
| 27 | `cosmict_3_valid_tracks` | `wc.T_tagger.cosmict_3_valid_tracks` | 0 | NTCosmic:746 | `valid_tracks;` | not stated in the fill expression | 1.00 / 1.00 | 1 |
| 28 | `cosmict_flag_5` | `wc.T_tagger.cosmict_flag_5` | 0 | NTCosmic:1375 | `flag_cosmic_5;` | not stated in the fill expression | 1.00 / 1.00 | 0 |
| 29 | `cosmict_5_filled` | `wc.T_tagger.cosmict_5_filled` | 0 | NTCosmic:778 | `1;` | not stated in the fill expression | 1.00 / 1.00 | 0 |
| 30 | `cosmict_5_flag_inside` | `wc.T_tagger.cosmict_5_flag_inside` | 0 | NTCosmic:779 | `flag_inside;` | not stated in the fill expression | 1.00 / 1.00 | 0 |
| 31 | `cosmict_5_angle_beam` | `wc.T_tagger.cosmict_5_angle_beam` | 0 | NTCosmic:780 | `static_cast<float>(dir.angle(dir_beam) / M_PI * 180.0);` | degrees | 1.00 / 1.00 | 4 |
| 32 | `cosmict_5_connected_showers` | `wc.T_tagger.cosmict_5_connected_showers` | 0 | NTCosmic:781 | `connected_showers;` | not stated in the fill expression | 1.00 / 1.00 | 0 |
| 33 | `cosmict_flag_6` | `wc.T_tagger.cosmict_flag_6` | 0 | NTCosmic:1376 | `flag_cosmic_6;` | not stated in the fill expression | 1.00 / 1.00 | 0 |
| 34 | `cosmict_6_filled` | `wc.T_tagger.cosmict_6_filled` | 0 | NTCosmic:1007 | `1;` | not stated in the fill expression | 0.99 / 0.99 | 0 |
| 35 | `cosmict_6_flag_dir_weak` | `wc.T_tagger.cosmict_6_flag_dir_weak` | 0 | NTCosmic:1008 | `seg_dir_weak(muon_2nd);` | not stated in the fill expression | 0.99 / 0.99 | 0 |
| 36 | `cosmict_6_flag_inside` | `wc.T_tagger.cosmict_6_flag_inside` | 1 | NTCosmic:1009 | `inside_fv(vtx_fit_pt(other_vtx2));` | not stated in the fill expression | 1.00 / 1.00 | 1 |
| 37 | `cosmict_6_angle` | `wc.T_tagger.cosmict_6_angle` | 0 | NTCosmic:1010 | `static_cast<float>(dir.angle(dir2) / M_PI * 180.0);` | degrees | 0.99 / 0.99 | 1 |
| 38 | `cosmict_flag_7` | `wc.T_tagger.cosmict_flag_7` | 0 | NTCosmic:1377 | `flag_cosmic_7;` | not stated in the fill expression | 0.96 / 0.98 | 3 |
| 39 | `cosmict_7_filled` | `wc.T_tagger.cosmict_7_filled` | 0 | NTCosmic:1019 | `1;` | not stated in the fill expression | 0.85 / 0.91 | 0 |
| 40 | `cosmict_7_flag_sec` | `wc.T_tagger.cosmict_7_flag_sec` | 0 | NTCosmic:1020 | `flag_sec;` | not stated in the fill expression | 0.94 / 0.97 | 4 |
| 41 | `cosmict_7_n_muon_tracks` | `wc.T_tagger.cosmict_7_n_muon_tracks` | 0 | NTCosmic:1021 | `n_muon_tracks;` | not stated in the fill expression | 0.86 / 0.93 | 1 |
| 42 | `cosmict_7_total_shower_length` | `wc.T_tagger.cosmict_7_total_shower_length` | 0 | NTCosmic:1022 | `static_cast<float>(total_shower_length / units::cm);` | cm | 0.98 / 0.99 | 1 |
| 43 | `cosmict_7_flag_inside` | `wc.T_tagger.cosmict_7_flag_inside` | 1 | NTCosmic:1023 | `flag_inside;` | not stated in the fill expression | 1.00 / 1.00 | 5 |
| 44 | `cosmict_7_angle_beam` | `wc.T_tagger.cosmict_7_angle_beam` | 0 | NTCosmic:1024 | `static_cast<float>(dir.angle(dir_beam) / M_PI * 180.0);` | degrees | 0.85 / 0.91 | 13 |
| 45 | `cosmict_7_flag_dir_weak` | `wc.T_tagger.cosmict_7_flag_dir_weak` | 0 | NTCosmic:1025 | `flag_weak_dir;` | not stated in the fill expression | 0.85 / 0.91 | 5 |
| 46 | `cosmict_7_dQ_dx_end` | `wc.T_tagger.cosmict_7_dQ_dx_end` | 0 | NTCosmic:1026 | `static_cast<float>(dQ_dx_end   / m_mip_dqdx_median);` | not stated in the fill expression | 0.85 / 0.91 | 10 |
| 47 | `cosmict_7_dQ_dx_front` | `wc.T_tagger.cosmict_7_dQ_dx_front` | 0 | NTCosmic:1027 | `static_cast<float>(dQ_dx_front / m_mip_dqdx_median);` | not stated in the fill expression | 0.85 / 0.91 | 19 |
| 48 | `cosmict_7_theta` | `wc.T_tagger.cosmict_7_theta` | 0 | NTCosmic:1028 | `static_cast<float>(vec_theta(dir) / M_PI * 180.0);` | degrees | 0.85 / 0.91 | 8 |
| 49 | `cosmict_7_phi` | `wc.T_tagger.cosmict_7_phi` | 0 | NTCosmic:1029 | `static_cast<float>(vec_phi(dir)   / M_PI * 180.0);` | degrees | 0.85 / 0.91 | 23 |
| 50 | `cosmict_flag_8` | `wc.T_tagger.cosmict_flag_8` | 0 | NTCosmic:1378 | `flag_cosmic_8;` | not stated in the fill expression | 1.00 / 1.00 | 0 |
| 51 | `cosmict_8_filled` | `wc.T_tagger.cosmict_8_filled` | 0 | NTCosmic:1065 | `1;` | not stated in the fill expression | 0.90 / 0.90 | 0 |
| 52 | `cosmict_8_flag_out` | `wc.T_tagger.cosmict_8_flag_out` | 0 | NTCosmic:1066 | `flag_out;` | not stated in the fill expression | 1.00 / 1.00 | 1 |
| 53 | `cosmict_8_muon_length` | `wc.T_tagger.cosmict_8_muon_length` | 0 | NTCosmic:1067 | `static_cast<float>(muon_length / units::cm);` | cm | 0.90 / 0.90 | 18 |
| 54 | `cosmict_8_acc_length` | `wc.T_tagger.cosmict_8_acc_length` | 0 | NTCosmic:1068 | `static_cast<float>(acc_length  / units::cm);` | cm | 0.91 / 0.94 | 16 |
| 55 | `cosmict_flag_9` | `wc.T_tagger.cosmict_flag_9` | 0 | NTCosmic:1379 | `flag_cosmic_9;` | not stated in the fill expression | 0.99 / 0.99 | 5 |
| 56 | `cosmic_flag` | `wc.T_tagger.cosmic_flag` | 1 | NTCosmic:1299 | `true;` | not stated in the fill expression | 0.99 / 0.99 | 6 |
| 57 | `cosmic_filled` | `wc.T_tagger.cosmic_filled` | 0 | NTCosmic:1292 | `1;` | not stated in the fill expression | 0.98 / 0.99 | 24 |
| 58 | `cosmict_flag` | `wc.T_tagger.cosmict_flag` | 0 | NTCosmic:1387 | `flag_cosmic;` | not stated in the fill expression | 0.92 / 0.95 | 51 |
| 59 | `numu_cc_flag` | `wc.T_tagger.numu_cc_flag` | 0 | NTNuMu:378 | `static_cast<float>(flag_numu_cc);` | not stated in the fill expression | 0.84 / 0.90 | 41 |
| 60 | `shw_sp_br2_num_valid_tracks` | `wc.T_tagger.shw_sp_br2_num_valid_tracks` | 0 | NTSinglePhoton:652 | `num_valid_tracks;` | not stated in the fill expression | 0.81 / 0.84 | 8 |
| 61 | `shw_sp_br2_n_shower_main_segs` | `wc.T_tagger.shw_sp_br2_n_shower_main_segs` | 0 | NTSinglePhoton:658 | `shower->get_num_main_segments();` | not stated in the fill expression | 0.28 / 0.61 | 40 |
| 62 | `shw_sp_br2_sg_length` | `wc.T_tagger.shw_sp_br2_sg_length` | 0 | NTSinglePhoton:660 | `static_cast<float>(segment_track_length(sg) / units::cm);` | cm | 0.28 / 0.61 | 70 |
| 63 | `shw_sp_br4_1_shower_main_length` | `wc.T_tagger.shw_sp_br4_1_shower_main_length` | 0 | NTSinglePhoton:1069 | `main_length / units::cm;` | cm | 0.00 / 0.00 | 69 |
| 64 | `shw_sp_br4_1_shower_total_length` | `wc.T_tagger.shw_sp_br4_1_shower_total_length` | 0 | NTSinglePhoton:1070 | `total_length / units::cm;` | cm | 0.00 / 0.00 | 100 |
| 65 | `shw_sp_br4_1_min_dis` | `wc.T_tagger.shw_sp_br4_1_min_dis` | 0 | NTSinglePhoton:1071 | `min_dis / units::cm;` | cm | 0.17 / 0.12 | 70 |
| 66 | `shw_sp_br4_1_flag_avoid_muon_check` | `wc.T_tagger.shw_sp_br4_1_flag_avoid_muon_check` | 0 | NTSinglePhoton:1073 | `(start_sg && start_sg->flags_any(SegmentFlags::kAvoidMuonChe` | not stated in the fill expression | 0.85 / 0.90 | 8 |
| 67 | `shw_sp_br4_1_n_vtx_segs` | `wc.T_tagger.shw_sp_br4_1_n_vtx_segs` | 0 | NTSinglePhoton:1074 | `(int)n_vtx_segs;` | not stated in the fill expression | 0.00 / 0.00 | 20 |
| 68 | `shw_sp_br4_1_n_main_segs` | `wc.T_tagger.shw_sp_br4_1_n_main_segs` | 0 | NTSinglePhoton:1075 | `shower->get_num_main_segments();` | not stated in the fill expression | 0.00 / 0.00 | 39 |
| 69 | `shw_sp_br4_2_ratio_45` | `wc.T_tagger.shw_sp_br4_2_ratio_45` | 1 | NTSinglePhoton:1149 | `ncount_45  / (ncount + 1e-9);` | not stated in the fill expression | 0.77 / 0.59 | 33 |
| 70 | `shw_sp_br4_2_ratio_35` | `wc.T_tagger.shw_sp_br4_2_ratio_35` | 1 | NTSinglePhoton:1150 | `ncount_35  / (ncount + 1e-9);` | not stated in the fill expression | 0.72 / 0.54 | 41 |
| 71 | `shw_sp_br4_2_ratio_25` | `wc.T_tagger.shw_sp_br4_2_ratio_25` | 1 | NTSinglePhoton:1151 | `ncount_25  / (ncount + 1e-9);` | not stated in the fill expression | 0.60 / 0.44 | 26 |
| 72 | `shw_sp_br4_2_ratio_15` | `wc.T_tagger.shw_sp_br4_2_ratio_15` | 1 | NTSinglePhoton:1152 | `ncount_15  / (ncount + 1e-9);` | not stated in the fill expression | 0.33 / 0.23 | 48 |
| 73 | `shw_sp_br4_2_ratio1_45` | `wc.T_tagger.shw_sp_br4_2_ratio1_45` | 1 | NTSinglePhoton:1159 | `ncount1_45 / (ncount1 + 1e-9);` | not stated in the fill expression | 0.32 / 0.33 | 36 |
| 74 | `shw_sp_br4_2_ratio1_35` | `wc.T_tagger.shw_sp_br4_2_ratio1_35` | 1 | NTSinglePhoton:1160 | `ncount1_35 / (ncount1 + 1e-9);` | not stated in the fill expression | 0.25 / 0.26 | 47 |
| 75 | `shw_sp_br4_2_ratio1_25` | `wc.T_tagger.shw_sp_br4_2_ratio1_25` | 1 | NTSinglePhoton:1161 | `ncount1_25 / (ncount1 + 1e-9);` | not stated in the fill expression | 0.15 / 0.15 | 45 |
| 76 | `shw_sp_br4_2_ratio1_15` | `wc.T_tagger.shw_sp_br4_2_ratio1_15` | 1 | NTSinglePhoton:1162 | `ncount1_15 / (ncount1 + 1e-9);` | not stated in the fill expression | 0.03 / 0.03 | 109 |
| 77 | `shw_sp_lem_shower_main_length` | `wc.T_tagger.shw_sp_lem_shower_main_length` | 0 | NTSinglePhoton:2235 | `main_length  / units::cm;` | cm | 0.00 / 0.00 | 59 |
| 78 | `shw_sp_lem_n_3seg` | `wc.T_tagger.shw_sp_lem_n_3seg` | 0 | NTSinglePhoton:2236 | `n_3seg;` | not stated in the fill expression | 0.50 / 0.38 | 15 |
| 79 | `shw_sp_lem_e_charge` | `wc.T_tagger.shw_sp_lem_e_charge` | 0 | NTSinglePhoton:2237 | `E_charge / units::MeV;` | MeV | 0.00 / 0.00 | 174 |
| 80 | `shw_sp_lem_e_dQdx` | `wc.T_tagger.shw_sp_lem_e_dQdx` | 0 | NTSinglePhoton:2238 | `E_dQdx   / units::MeV;` | MeV | 0.00 / 0.00 | 83 |
| 81 | `shw_sp_lem_shower_num_main_segs` | `wc.T_tagger.shw_sp_lem_shower_num_main_segs` | 0 | NTSinglePhoton:2240 | `shower->get_num_main_segments();` | not stated in the fill expression | 0.00 / 0.00 | 28 |
| 82 | `shw_sp_max_dQ_dx_sample` | `wc.T_tagger.shw_sp_max_dQ_dx_sample` | 1 | NTSinglePhoton:1612 | `max_dQ_dx_sample;` | not stated in the fill expression | 0.00 / 0.00 | 105 |
| 83 | `shw_sp_n_below_threshold` | `wc.T_tagger.shw_sp_n_below_threshold` | 19 | NTSinglePhoton:1615 | `n_below_threshold;` | not stated in the fill expression | 0.02 / 0.02 | 31 |
| 84 | `shw_sp_n_below_zero` | `wc.T_tagger.shw_sp_n_below_zero` | 0 | NTSinglePhoton:1626 | `n_below_zero;` | not stated in the fill expression | 0.96 / 0.96 | 2 |
| 85 | `shw_sp_n_lowest` | `wc.T_tagger.shw_sp_n_lowest` | 1 | NTSinglePhoton:1628 | `n_lowest;` | not stated in the fill expression | 0.09 / 0.10 | 32 |
| 86 | `shw_sp_n_highest` | `wc.T_tagger.shw_sp_n_highest` | 1 | NTSinglePhoton:1629 | `n_highest;` | not stated in the fill expression | 0.08 / 0.09 | 43 |
| 87 | `shw_sp_lowest_dQ_dx` | `wc.T_tagger.shw_sp_lowest_dQ_dx` | 1 | NTSinglePhoton:1624 | `lowest_dQ_dx;` | not stated in the fill expression | 0.00 / 0.00 | 89 |
| 88 | `shw_sp_highest_dQ_dx` | `wc.T_tagger.shw_sp_highest_dQ_dx` | 1 | NTSinglePhoton:1627 | `highest_dQ_dx;` | not stated in the fill expression | 0.00 / 0.00 | 108 |
| 89 | `shw_sp_medium_dQ_dx` | `wc.T_tagger.shw_sp_medium_dQ_dx` | 1 | NTSinglePhoton:1636 | `medium_dQ_dx;` | not stated in the fill expression | 0.00 / 0.00 | 70 |
| 90 | `shw_sp_stem_length` | `wc.T_tagger.shw_sp_stem_length` | 1 | NTSinglePhoton:1630 | `segment_track_length(sg) / units::cm;` | cm | 0.00 / 0.00 | 84 |
| 91 | `shw_sp_length_main` | `wc.T_tagger.shw_sp_length_main` | 1 | NTSinglePhoton:1621 | `(sg->cluster() ? shower->get_total_length(sg->cluster()) : 0` | cm | 0.00 / 0.00 | 44 |
| 92 | `shw_sp_length_total` | `wc.T_tagger.shw_sp_length_total` | 1 | NTSinglePhoton:1622 | `shower->get_total_length() / units::cm;` | cm | 0.00 / 0.00 | 70 |
| 93 | `shw_sp_n_vertex` | `wc.T_tagger.shw_sp_n_vertex` | 1 | NTSinglePhoton:1617 | `vtx_deg;` | not stated in the fill expression | 0.43 / 0.36 | 34 |
| 94 | `shw_sp_n_good_tracks` | `wc.T_tagger.shw_sp_n_good_tracks` | 0 | NTSinglePhoton:1616 | `n_good_tracks;` | not stated in the fill expression | 0.70 / 0.67 | 22 |
| 95 | `shw_sp_E_indirect_max_energy` | `wc.T_tagger.shw_sp_E_indirect_max_energy` | 0 | NTSinglePhoton:1631 | `E_indirect_max_energy / units::MeV;` | MeV | 0.61 / 0.61 | 224 |
| 96 | `shw_sp_flag_all_above` | `wc.T_tagger.shw_sp_flag_all_above` | 0 | NTSinglePhoton:1620 | `flag_all_above;` | not stated in the fill expression | 0.76 / 0.71 | 4 |
| 97 | `shw_sp_min_dQ_dx_5` | `wc.T_tagger.shw_sp_min_dQ_dx_5` | 1 | NTSinglePhoton:1623 | `min_dQ_dx_5;` | not stated in the fill expression | 0.96 / 0.94 | 45 |
| 98 | `shw_sp_n_other_vertex` | `wc.T_tagger.shw_sp_n_other_vertex` | 2 | NTSinglePhoton:1634 | `n_other_vertex;` | not stated in the fill expression | 0.19 / 0.16 | 27 |
| 99 | `shw_sp_n_stem_size` | `wc.T_tagger.shw_sp_n_stem_size` | 20 | NTSinglePhoton:1635 | `(float)sg->fits().size();` | not stated in the fill expression | 0.03 / 0.02 | 56 |
| 100 | `shw_sp_min_dis` | `wc.T_tagger.shw_sp_min_dis` | 0 | NTSinglePhoton:1633 | `min_dis / units::cm;` | cm | 0.00 / 0.00 | 73 |
| 101 | `shw_sp_vec_mean_dedx` | `wc.T_tagger.shw_sp_vec_mean_dedx` | 0 | NTSinglePhoton:1657 | `mean_dedx;` | not stated in the fill expression | 0.00 / 0.00 | 66 |
| 102 | `shw_sp_vec_dQ_dx_0` | `wc.T_tagger.shw_sp_vec_dQ_dx_0` | 1 | NTSinglePhoton:1613 | `vec_dQ_dx[0];` | not stated in the fill expression | 0.00 / 0.00 | 80 |
| 103 | `shw_sp_vec_dQ_dx_1` | `wc.T_tagger.shw_sp_vec_dQ_dx_1` | 1 | NTSinglePhoton:1614 | `vec_dQ_dx[1];` | not stated in the fill expression | 0.00 / 0.00 | 106 |
| 104 | `shw_sp_vec_dQ_dx_2` | `wc.T_tagger.shw_sp_vec_dQ_dx_2` | 0 | NTSinglePhoton:1638 | `vec_dQ_dx[2];` | not stated in the fill expression | 0.00 / 0.00 | 88 |
| 105 | `shw_sp_vec_dQ_dx_3` | `wc.T_tagger.shw_sp_vec_dQ_dx_3` | 0 | NTSinglePhoton:1639 | `vec_dQ_dx[3];` | not stated in the fill expression | 0.00 / 0.00 | 64 |
| 106 | `shw_sp_vec_dQ_dx_4` | `wc.T_tagger.shw_sp_vec_dQ_dx_4` | 0 | NTSinglePhoton:1640 | `vec_dQ_dx[4];` | not stated in the fill expression | 0.00 / 0.00 | 86 |
| 107 | `shw_sp_vec_dQ_dx_5` | `wc.T_tagger.shw_sp_vec_dQ_dx_5` | 0 | NTSinglePhoton:1641 | `vec_dQ_dx[5];` | not stated in the fill expression | 0.00 / 0.00 | 71 |
| 108 | `shw_sp_vec_dQ_dx_6` | `wc.T_tagger.shw_sp_vec_dQ_dx_6` | 0 | NTSinglePhoton:1642 | `vec_dQ_dx[6];` | not stated in the fill expression | 0.00 / 0.00 | 73 |
| 109 | `shw_sp_vec_dQ_dx_7` | `wc.T_tagger.shw_sp_vec_dQ_dx_7` | 0 | NTSinglePhoton:1643 | `vec_dQ_dx[7];` | not stated in the fill expression | 0.00 / 0.00 | 60 |
| 110 | `shw_sp_vec_dQ_dx_8` | `wc.T_tagger.shw_sp_vec_dQ_dx_8` | 0 | NTSinglePhoton:1644 | `vec_dQ_dx[8];` | not stated in the fill expression | 0.00 / 0.00 | 72 |
| 111 | `shw_sp_vec_dQ_dx_9` | `wc.T_tagger.shw_sp_vec_dQ_dx_9` | 0 | NTSinglePhoton:1645 | `vec_dQ_dx[9];` | not stated in the fill expression | 0.00 / 0.00 | 66 |
| 112 | `shw_sp_vec_dQ_dx_10` | `wc.T_tagger.shw_sp_vec_dQ_dx_10` | 0 | NTSinglePhoton:1646 | `vec_dQ_dx[10];` | not stated in the fill expression | 0.00 / 0.00 | 69 |
| 113 | `shw_sp_vec_dQ_dx_11` | `wc.T_tagger.shw_sp_vec_dQ_dx_11` | 0 | NTSinglePhoton:1647 | `vec_dQ_dx[11];` | not stated in the fill expression | 0.00 / 0.00 | 80 |
| 114 | `shw_sp_vec_dQ_dx_12` | `wc.T_tagger.shw_sp_vec_dQ_dx_12` | 0 | NTSinglePhoton:1648 | `vec_dQ_dx[12];` | not stated in the fill expression | 0.00 / 0.00 | 55 |
| 115 | `shw_sp_vec_dQ_dx_13` | `wc.T_tagger.shw_sp_vec_dQ_dx_13` | 0 | NTSinglePhoton:1649 | `vec_dQ_dx[13];` | not stated in the fill expression | 0.00 / 0.00 | 51 |
| 116 | `shw_sp_vec_dQ_dx_14` | `wc.T_tagger.shw_sp_vec_dQ_dx_14` | 0 | NTSinglePhoton:1650 | `vec_dQ_dx[14];` | not stated in the fill expression | 0.00 / 0.00 | 40 |
| 117 | `shw_sp_vec_dQ_dx_15` | `wc.T_tagger.shw_sp_vec_dQ_dx_15` | 0 | NTSinglePhoton:1651 | `vec_dQ_dx[15];` | not stated in the fill expression | 0.00 / 0.00 | 70 |
| 118 | `shw_sp_vec_dQ_dx_16` | `wc.T_tagger.shw_sp_vec_dQ_dx_16` | 0 | NTSinglePhoton:1652 | `vec_dQ_dx[16];` | not stated in the fill expression | 0.00 / 0.00 | 51 |
| 119 | `shw_sp_vec_dQ_dx_17` | `wc.T_tagger.shw_sp_vec_dQ_dx_17` | 0 | NTSinglePhoton:1653 | `vec_dQ_dx[17];` | not stated in the fill expression | 0.00 / 0.00 | 54 |
| 120 | `shw_sp_vec_dQ_dx_18` | `wc.T_tagger.shw_sp_vec_dQ_dx_18` | 0 | NTSinglePhoton:1654 | `vec_dQ_dx[18];` | not stated in the fill expression | 0.00 / 0.00 | 62 |
| 121 | `shw_sp_vec_dQ_dx_19` | `wc.T_tagger.shw_sp_vec_dQ_dx_19` | 0 | NTSinglePhoton:1655 | `vec_dQ_dx[19];` | not stated in the fill expression | 0.00 / 0.00 | 61 |
| 122 | `shw_sp_vec_median_dedx` | `wc.T_tagger.shw_sp_vec_median_dedx` | 0 | NTSinglePhoton:1656 | `median_dedx;` | not stated in the fill expression | 0.00 / 0.01 | 76 |
| 123 | `shw_sp_proton_length_1` | `wc.T_tagger.shw_sp_proton_length_1` | -1 | NTSinglePhoton:2525 | `proton_length_1;` | not stated in the fill expression | 0.69 / 0.79 | 45 |
| 124 | `shw_sp_proton_dqdx_1` | `wc.T_tagger.shw_sp_proton_dqdx_1` | -1 | NTSinglePhoton:2526 | `proton_dqdx_1;` | not stated in the fill expression | 0.69 / 0.79 | 74 |
| 125 | `shw_sp_proton_energy_1` | `wc.T_tagger.shw_sp_proton_energy_1` | -1 | NTSinglePhoton:2527 | `proton_energy_1;` | not stated in the fill expression | 0.69 / 0.79 | 38 |
| 126 | `shw_sp_proton_length_2` | `wc.T_tagger.shw_sp_proton_length_2` | -1 | NTSinglePhoton:2528 | `proton_length_2;` | not stated in the fill expression | 0.96 / 0.98 | 16 |
| 127 | `shw_sp_proton_dqdx_2` | `wc.T_tagger.shw_sp_proton_dqdx_2` | -1 | NTSinglePhoton:2529 | `proton_dqdx_2;` | not stated in the fill expression | 0.96 / 0.98 | 14 |
| 128 | `shw_sp_proton_energy_2` | `wc.T_tagger.shw_sp_proton_energy_2` | -1 | NTSinglePhoton:2530 | `proton_energy_2;` | not stated in the fill expression | 0.96 / 0.98 | 12 |
| 129 | `shw_sp_n_good_showers` | `wc.T_tagger.shw_sp_n_good_showers` | 0 | NTSinglePhoton:2514 | `num_good_shws;` | not stated in the fill expression | 0.25 / 0.41 | 33 |
| 130 | `shw_sp_n_br1_showers` | `wc.T_tagger.shw_sp_n_br1_showers` | 0 | NTSinglePhoton:2516 | `num_badreco1_shws;` | not stated in the fill expression | 0.00 / 0.00 | 60 |
| 131 | `shw_sp_n_br2_showers` | `wc.T_tagger.shw_sp_n_br2_showers` | 0 | NTSinglePhoton:2517 | `num_badreco2_shws;` | not stated in the fill expression | 0.01 / 0.00 | 67 |
| 132 | `shw_sp_n_br3_showers` | `wc.T_tagger.shw_sp_n_br3_showers` | 0 | NTSinglePhoton:2518 | `num_badreco3_shws;` | not stated in the fill expression | 0.08 / 0.19 | 65 |
| 133 | `shw_sp_n_br4_showers` | `wc.T_tagger.shw_sp_n_br4_showers` | 0 | NTSinglePhoton:2519 | `num_badreco4_shws;` | not stated in the fill expression | 0.04 / 0.13 | 35 |
| 134 | `shw_sp_n_20br1_showers` | `wc.T_tagger.shw_sp_n_20br1_showers` | 0 | NTSinglePhoton:2520 | `num_20br1_shws;` | not stated in the fill expression | 0.00 / 0.00 | 47 |
| 135 | `shw_sp_shw_vtx_dis` | `wc.T_tagger.shw_sp_shw_vtx_dis` | -1 | NTSinglePhoton:2593 | `shw_vtx_dis;` | not stated in the fill expression | 0.00 / 0.00 | 114 |
| 136 | `shw_sp_max_shw_dis` | `wc.T_tagger.shw_sp_max_shw_dis` | -1 | NTSinglePhoton:2594 | `max_shw_dis;` | not stated in the fill expression | 0.00 / 0.00 | 80 |
| 137 | `shw_sp_num_mip_tracks` | `wc.T_tagger.shw_sp_num_mip_tracks` | 0 | NTSinglePhoton:2521 | `num_mip_tracks;` | not stated in the fill expression | 0.76 / 0.85 | 6 |
| 138 | `shw_sp_num_muons` | `wc.T_tagger.shw_sp_num_muons` | 0 | NTSinglePhoton:2522 | `num_muons;` | not stated in the fill expression | 0.83 / 0.88 | 6 |
| 139 | `shw_sp_num_protons` | `wc.T_tagger.shw_sp_num_protons` | 0 | NTSinglePhoton:2524 | `num_protons;` | not stated in the fill expression | 0.69 / 0.79 | 9 |
| 140 | `shw_sp_hol_2_min_angle` | `wc.T_tagger.shw_sp_hol_2_min_angle` | 0 | NTSinglePhoton:1835 | `min_ang2;` | not stated in the fill expression | 0.31 / 0.64 | 72 |
| 141 | `cosmict_10_score` | `wc.T_tagger.cosmict_10_score` | 0 | see text | `` | not stated in the fill expression | 0.00 / 0.00 | 36 |
| 142 | `numu_1_score` | `wc.T_tagger.numu_1_score` | 0 | see text | `` | not stated in the fill expression | 0.00 / 0.00 | 194 |
| 143 | `numu_2_score` | `wc.T_tagger.numu_2_score` | 0 | see text | `` | not stated in the fill expression | 0.00 / 0.00 | 14 |
| 144 | `numu_score` | `wc.T_tagger.numu_score` | 0 | see text | `` | not stated in the fill expression | 0.00 / 0.00 | 281 |
| 145 | `reco_nuvtxY` | `wc.T_kine.kine_nu_y_corr` | 0 | see text | `` | not stated in the fill expression | 0.00 / 0.00 | 221 |

## 5. What was not established
* The CAF-stored production identity of the BDT directory (only the string `uboone/weights`).
* TMVA-runtime agreement (no ROOT here); the independent evaluator follows the production C++ evaluator semantics from source.
* Physical definitions beyond what the fill code states (e.g. the exact physics motivation of each sub-tagger), since the source carries no field documentation.
