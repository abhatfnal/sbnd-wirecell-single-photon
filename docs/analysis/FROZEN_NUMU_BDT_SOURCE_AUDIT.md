# Frozen `single_photon_numu_bdt_final.xml`: source audit

Date: 2026-11-11. Branch `analysis/ncdelta-remaining-frozen-stage-audit-20261111`. Audit only: no retraining, no tuning, no threshold scan. Tags: **SOURCE** (read from code / XML), **MEASURED** (from the official files), **INFERRED** (flagged). Source: `HaiwangYu/wire-cell-toolkit`, branch `sbnd-wc-flatcaf`, commit `4b6853d4` (the producer-declared fg1 pin; same as `FROZEN_OTHER_BDT_SOURCE_AUDIT.md`). Machine-readable per-input table: `tables/remaining_stage_audit/input_source_table_numu.csv`. Companion: `REMAINING_FROZEN_SELECTION_STAGE_AUDIT.md`.

## 1. The model

| item | value | tag |
|---|---|---|
| weight file | `single_photon_numu_bdt_final.xml` (frozen stage name `single_photon_numu_score`) | SOURCE |
| location read | `/exp/uboone/app/users/uboonepro/bbogart/wcp-uboone-bdt/weights/` (the frozen MicroBooNE reference bundle) | MEASURED |
| sha256 | `5886affbdb3a4499a4515ecc8d354eb1449e7c204d32f1cc54c1ec8868ead961` (identical to `provenance/microboone_reference_SHA256SUMS.txt`, line 7) | MEASURED |
| model type | TMVA `BDT::BDT`, `BoostType = Grad`, created by `xgboost2TMVA` (an XGBoost model converted to TMVA XML) | SOURCE (XML header) |
| ensemble | **300 trees**, every tree depth 5, **8,403 leaves**, `boostWeight = 1.0` for every tree, all **73 inputs used in at least one split** | MEASURED |
| score | `score = tanh(sum_t leaf_t) = 2/(1+exp(-2 sum)) - 1` (TMVA `GetGradBoostMVA`); frozen cut `score > 0.4`, i.e. margin `sum > atanh(0.4) = 0.4236` (`configs/baseline_selection.yaml`) | SOURCE / config |
| split rule | production `TmvaGradForest::evaluate`: right iff `value >= cut`, float32 values and cuts; the frozen scorer uses `<=` (differs only on exact ties) | SOURCE |
| preprocessing | none (raw `wc.T_tagger` values, no scaling or transformation); input order = XML `VarIndex` 0-72 (table in section 6) | SOURCE |
| missing values | production: any NaN input gives -999; this repository: a non-finite input makes the candidate not evaluable and fail the BDT cuts. MEASURED: 0 non-finite numu inputs in the 8,447 scored candidates | SOURCE / MEASURED |
| where it runs | **the score is NOT stored in the CAF** (`Trun.bdt_weights_dir = uboone/weights` records only a path); it is computed offline by `bdt.py`; the reference is the validated derived-table score of the baseline | MEASURED |
| what it is | the **single-photon-specific `numu` BDT**: the `numu_*` inputs describe the **muon-like objects of the candidate** (so the stage is a muon-neutrino-CC rejection trained on MicroBooNE) | SOURCE (inputs) |

## 2. Score reproduction (Task 4)

| quantity | value |
|---|---|
| candidates scored (all candidates of the 8,080 shower-stage events) | 8,447 |
| compared with the stored derived-table score (`candidates.parquet`, `c_score_numu`) | 8,112 candidates; **max |difference| = 0.0** (median 0.0); 335 candidates have no stored score (shw_sp_filled == 0 or a non-finite input) |
| independent TMVA-rule float32 evaluator (`other_audit.scores_tmva_float32`) | max |difference| to the frozen scorer **3.12e-09**, median 4.2e-11; candidates differing by more than 1e-6: **0** |
| decision flips at the frozen threshold | **0** |
| tie-convention cases (a visited split compares a float32 input exactly equal to its cut) | **1** |
| non-finite recomputed scores | 0 |
| transparent per-event scalar XML reader (random 200 candidates) | agrees with the vectorised float32 evaluator, max 0.0 |

Reproduction is exact at float level (3e-9); the one tie-convention case does not change a score at the 1e-6 level and no decision flips at 0.4. The model-internal attribution of the companion report is therefore valid.

## 3. The 73 inputs by family (fill code read; every row in section 6)

| family | n | what it is (from the fill code) |
|---|---|---|
| shower quality (br1 / br3 / lem) | 29 | `shw_sp_br1_*`: the three sub-checks of `bad_reconstruction_sp` (stem topology, longest muon-like track inside the shower, straight track near the stem's far end); `shw_sp_br3_*`: sub-checks of `bad_reconstruction_2_sp` (segment topology, dQ/dx and angular structure relative to the stem); `shw_sp_lem_*`: `low_energy_michel_sp` ("rejects showers that look like michel electrons from low-energy muon decays"); the shower-segment counts (`br1_1_n_segs`, `br1_2_n_shower_segs`, `br3_1_n_shower_segments`) all describe the number of segments of the same shower |
| vertex / gap geometry | 11 | stem and shower lengths (`shw_sp_stem_length`, `length_main`, `length_total`), vertex degrees (`n_vertex`, `n_other_vertex`, `n_stem_size`), `E_indirect_max_energy`, `min_dis`, `shw_vtx_dis`, `max_shw_dis` (the gap is 0 for an attached shower) |
| calorimetry | 10 | stem dQ/dx summaries (`max_dQ_dx_sample`, `lowest/highest/medium_dQ_dx`, `min_dQ_dx_5`, `n_below_*`, `n_lowest/highest`, mean dE/dx), MIP-normalised |
| track / hadron activity | 7 | `shw_sp_proton_{length,dqdx,energy}_{1,2}` and `n_good_tracks`: protons / MIP tracks attached at the main vertex (default -1 or 0 if absent) |
| numuCC tagger inputs | 8 | `numu_cc_flag_3`, `numu_cc_3_*` from `NeutrinoTaggerNuMu.cxx:364-371`: the numuCC tagger's flag-3 (indirect long muon-like track) check: longest muon-like length, track length, number of daughter tracks |
| multiplicity | 6 | `n_good_showers`, `n_br1..4_showers`, `n_20br1_showers` (counts over the shower set of the main vertex, see `N20BR1_SEMANTICS.md`) |
| **upstream BDT scores** | 2 | `numu_1_score` (sub-BDT `numu_1` on the flag-1 direct-muon features; scorer default -0.4) and `numu_score` (the log-odds `log10((1+v)/(1-v))` of the xgboost numu BDT output v of `UbooneNumuBDTScorer`); see `FROZEN_BDT_DEPENDENCY_GRAPH.md` |

## 4. Default and fill semantics (MEASURED on the stage population, 8,038 events; `default_fractions_numu.csv`, `default_fractions_cross_bdt.csv`)
* **Struct default 0** for the `numu_cc_*` inputs: they sit at the default when the numuCC flag-3 check found no qualifying muon-like candidate: `numu_cc_flag_3` 98.6 %, `numu_cc_3_n_daughter_tracks` 94.8 %, `numu_cc_3_max_muon_length` 79.3 %; family mean 69.8 %.
* **Track / hadron activity** at default (no second proton / MIP track at the vertex): mean 81.0 % (identical for truth 0p and 1p within 4 points).
* The shower-quality, geometry and multiplicity families are mostly filled (mean default fractions 14.7 %, 17.0 %, 9.2 %), calorimetry 21.1 %.
* The upstream scores are never at their scorer default in this population (`numu_1_score` at -0.4: 0.0 %) and never exactly 0.
* **The inputs of a candidate without a max shower are sentinels** (`shw_sp_filled == 0`): the baseline's not-evaluable status comes from that criterion, not from non-finite values.

## 5. What is and is not source-established
Established: file, checksum, structure, score transform, input order, fill code of every input, tie convention, exact reproduction. Not established: the training sample and training procedure (the XGBoost training is not in the repository; the XML carries no training metadata) and the physical meaning of a few sub-check variable names beyond the fill code and the source comments quoted above.

## 6. The 73 inputs in XML order
| idx | variable | CAF branch | family | struct / operative default | first fill (file:line) | units (fill code) | fraction at default (stage population) |
|---|---|---|---|---|---|---|---|
| 0 | `numu_cc_flag_3` | `wc.T_tagger.numu_cc_flag_3` | numuCC tagger inputs | 0 | NTNuMu:364 | not stated | 0.986 |
| 1 | `numu_cc_3_particle_type` | `wc.T_tagger.numu_cc_3_particle_type` | numuCC tagger inputs | 0 | NTNuMu:365 | not stated | 0.986 |
| 2 | `numu_cc_3_max_length` | `wc.T_tagger.numu_cc_3_max_length` | numuCC tagger inputs | 0 | NTNuMu:366 | cm | 0.645 |
| 3 | `numu_cc_3_track_length` | `wc.T_tagger.numu_cc_3_track_length` | numuCC tagger inputs | 0 | NTNuMu:367 | cm | 0.205 |
| 4 | `numu_cc_3_max_length_all` | `wc.T_tagger.numu_cc_3_max_length_all` | numuCC tagger inputs | 0 | NTNuMu:368 | cm | 0.205 |
| 5 | `numu_cc_3_max_muon_length` | `wc.T_tagger.numu_cc_3_max_muon_length` | numuCC tagger inputs | 0 | NTNuMu:369 | cm | 0.793 |
| 6 | `numu_cc_3_n_daughter_tracks` | `wc.T_tagger.numu_cc_3_n_daughter_tracks` | numuCC tagger inputs | 0 | NTNuMu:370 | not stated | 0.948 |
| 7 | `numu_cc_3_n_daughter_all` | `wc.T_tagger.numu_cc_3_n_daughter_all` | numuCC tagger inputs | 0 | NTNuMu:371 | not stated | 0.816 |
| 8 | `shw_sp_br1_1_shower_type` | `wc.T_tagger.shw_sp_br1_1_shower_type` | shower quality (br/lem/hol/lol) | 0 | NTSinglePhoton:242 | not stated | 0.000 |
| 9 | `shw_sp_br1_1_vtx_n_segs` | `wc.T_tagger.shw_sp_br1_1_vtx_n_segs` | shower quality (br/lem/hol/lol) | 0 | NTSinglePhoton:243 | not stated | 0.000 |
| 10 | `shw_sp_br1_1_n_segs` | `wc.T_tagger.shw_sp_br1_1_n_segs` | shower quality (br/lem/hol/lol) | 0 | NTSinglePhoton:245 | not stated | 0.000 |
| 11 | `shw_sp_br1_1_sg_length` | `wc.T_tagger.shw_sp_br1_1_sg_length` | shower quality (br/lem/hol/lol) | 0 | NTSinglePhoton:248 | cm | 0.000 |
| 12 | `shw_sp_br1_2_n_connected` | `wc.T_tagger.shw_sp_br1_2_n_connected` | shower quality (br/lem/hol/lol) | 0 | NTSinglePhoton:367 | not stated | 0.359 |
| 13 | `shw_sp_br1_2_max_length` | `wc.T_tagger.shw_sp_br1_2_max_length` | shower quality (br/lem/hol/lol) | 0 | NTSinglePhoton:368 | cm | 0.039 |
| 14 | `shw_sp_br1_2_n_connected_1` | `wc.T_tagger.shw_sp_br1_2_n_connected_1` | shower quality (br/lem/hol/lol) | 0 | NTSinglePhoton:369 | not stated | 0.862 |
| 15 | `shw_sp_br1_2_n_shower_segs` | `wc.T_tagger.shw_sp_br1_2_n_shower_segs` | shower quality (br/lem/hol/lol) | 0 | NTSinglePhoton:371 | not stated | 0.000 |
| 16 | `shw_sp_br1_2_max_length_ratio` | `wc.T_tagger.shw_sp_br1_2_max_length_ratio` | shower quality (br/lem/hol/lol) | 1 | NTSinglePhoton:372 | not stated | 0.012 |
| 17 | `shw_sp_br1_2_shower_length` | `wc.T_tagger.shw_sp_br1_2_shower_length` | shower quality (br/lem/hol/lol) | 0 | NTSinglePhoton:373 | cm | 0.000 |
| 18 | `shw_sp_br1_3_max_length_p` | `wc.T_tagger.shw_sp_br1_3_max_length_p` | shower quality (br/lem/hol/lol) | 0 | NTSinglePhoton:521 | cm | 0.893 |
| 19 | `shw_sp_br1_3_n_shower_main_segs` | `wc.T_tagger.shw_sp_br1_3_n_shower_main_segs` | shower quality (br/lem/hol/lol) | 0 | NTSinglePhoton:525 | not stated | 0.000 |
| 20 | `shw_sp_br3_1_n_shower_segments` | `wc.T_tagger.shw_sp_br3_1_n_shower_segments` | shower quality (br/lem/hol/lol) | 0 | NTSinglePhoton:726 | not stated | 0.000 |
| 21 | `shw_sp_br3_1_sg_direct_length` | `wc.T_tagger.shw_sp_br3_1_sg_direct_length` | shower quality (br/lem/hol/lol) | 0 | NTSinglePhoton:729 | cm | 0.000 |
| 22 | `shw_sp_br3_1_sg_length` | `wc.T_tagger.shw_sp_br3_1_sg_length` | shower quality (br/lem/hol/lol) | 0 | NTSinglePhoton:730 | cm | 0.000 |
| 23 | `shw_sp_br3_1_total_main_length` | `wc.T_tagger.shw_sp_br3_1_total_main_length` | shower quality (br/lem/hol/lol) | 0 | NTSinglePhoton:731 | cm | 0.000 |
| 24 | `shw_sp_br3_1_total_length` | `wc.T_tagger.shw_sp_br3_1_total_length` | shower quality (br/lem/hol/lol) | 0 | NTSinglePhoton:732 | cm | 0.000 |
| 25 | `shw_sp_br3_2_n_ele` | `wc.T_tagger.shw_sp_br3_2_n_ele` | shower quality (br/lem/hol/lol) | 0 | NTSinglePhoton:781 | not stated | 0.180 |
| 26 | `shw_sp_br3_2_n_other` | `wc.T_tagger.shw_sp_br3_2_n_other` | shower quality (br/lem/hol/lol) | 0 | NTSinglePhoton:782 | not stated | 0.384 |
| 27 | `shw_sp_br3_2_other_fid` | `wc.T_tagger.shw_sp_br3_2_other_fid` | shower quality (br/lem/hol/lol) | 0 | NTSinglePhoton:786 | not stated | 0.021 |
| 28 | `shw_sp_br3_4_acc_length` | `wc.T_tagger.shw_sp_br3_4_acc_length` | shower quality (br/lem/hol/lol) | 0 | NTSinglePhoton:829 | cm | 0.915 |
| 29 | `shw_sp_br3_4_total_length` | `wc.T_tagger.shw_sp_br3_4_total_length` | shower quality (br/lem/hol/lol) | 0 | NTSinglePhoton:830 | cm | 0.000 |
| 30 | `shw_sp_br3_8_max_dQ_dx` | `wc.T_tagger.shw_sp_br3_8_max_dQ_dx` | shower quality (br/lem/hol/lol) | 0 | NTSinglePhoton:958 | not stated | 0.024 |
| 31 | `shw_sp_br3_8_n_main_segs` | `wc.T_tagger.shw_sp_br3_8_n_main_segs` | shower quality (br/lem/hol/lol) | 0 | NTSinglePhoton:960 | not stated | 0.000 |
| 32 | `shw_sp_lem_shower_main_length` | `wc.T_tagger.shw_sp_lem_shower_main_length` | shower quality (br/lem/hol/lol) | 0 | NTSinglePhoton:2235 | cm | 0.000 |
| 33 | `shw_sp_lem_n_3seg` | `wc.T_tagger.shw_sp_lem_n_3seg` | shower quality (br/lem/hol/lol) | 0 | NTSinglePhoton:2236 | not stated | 0.565 |
| 34 | `shw_sp_lem_e_charge` | `wc.T_tagger.shw_sp_lem_e_charge` | shower quality (br/lem/hol/lol) | 0 | NTSinglePhoton:2237 | MeV | 0.000 |
| 35 | `shw_sp_lem_e_dQdx` | `wc.T_tagger.shw_sp_lem_e_dQdx` | shower quality (br/lem/hol/lol) | 0 | NTSinglePhoton:2238 | MeV | 0.000 |
| 36 | `shw_sp_lem_shower_num_main_segs` | `wc.T_tagger.shw_sp_lem_shower_num_main_segs` | shower quality (br/lem/hol/lol) | 0 | NTSinglePhoton:2240 | not stated | 0.000 |
| 37 | `shw_sp_max_dQ_dx_sample` | `wc.T_tagger.shw_sp_max_dQ_dx_sample` | calorimetry (dQ/dx, dE/dx) | 1 | NTSinglePhoton:1612 | not stated | 0.000 |
| 38 | `shw_sp_n_below_threshold` | `wc.T_tagger.shw_sp_n_below_threshold` | calorimetry (dQ/dx, dE/dx) | 19 | NTSinglePhoton:1615 | not stated | 0.031 |
| 39 | `shw_sp_n_below_zero` | `wc.T_tagger.shw_sp_n_below_zero` | calorimetry (dQ/dx, dE/dx) | 0 | NTSinglePhoton:1626 | not stated | 0.939 |
| 40 | `shw_sp_n_lowest` | `wc.T_tagger.shw_sp_n_lowest` | calorimetry (dQ/dx, dE/dx) | 1 | NTSinglePhoton:1628 | not stated | 0.100 |
| 41 | `shw_sp_n_highest` | `wc.T_tagger.shw_sp_n_highest` | calorimetry (dQ/dx, dE/dx) | 1 | NTSinglePhoton:1629 | not stated | 0.090 |
| 42 | `shw_sp_lowest_dQ_dx` | `wc.T_tagger.shw_sp_lowest_dQ_dx` | calorimetry (dQ/dx, dE/dx) | 1 | NTSinglePhoton:1624 | not stated | 0.000 |
| 43 | `shw_sp_highest_dQ_dx` | `wc.T_tagger.shw_sp_highest_dQ_dx` | calorimetry (dQ/dx, dE/dx) | 1 | NTSinglePhoton:1627 | not stated | 0.000 |
| 44 | `shw_sp_medium_dQ_dx` | `wc.T_tagger.shw_sp_medium_dQ_dx` | calorimetry (dQ/dx, dE/dx) | 1 | NTSinglePhoton:1636 | not stated | 0.000 |
| 45 | `shw_sp_stem_length` | `wc.T_tagger.shw_sp_stem_length` | vertex / gap geometry | 1 | NTSinglePhoton:1630 | cm | 0.000 |
| 46 | `shw_sp_length_main` | `wc.T_tagger.shw_sp_length_main` | vertex / gap geometry | 1 | NTSinglePhoton:1621 | cm | 0.000 |
| 47 | `shw_sp_length_total` | `wc.T_tagger.shw_sp_length_total` | vertex / gap geometry | 1 | NTSinglePhoton:1622 | cm | 0.000 |
| 48 | `shw_sp_n_vertex` | `wc.T_tagger.shw_sp_n_vertex` | vertex / gap geometry | 1 | NTSinglePhoton:1617 | not stated | 0.351 |
| 49 | `shw_sp_n_good_tracks` | `wc.T_tagger.shw_sp_n_good_tracks` | track / hadron activity | 0 | NTSinglePhoton:1616 | not stated | 0.596 |
| 50 | `shw_sp_E_indirect_max_energy` | `wc.T_tagger.shw_sp_E_indirect_max_energy` | vertex / gap geometry | 0 | NTSinglePhoton:1631 | MeV | 0.545 |
| 51 | `shw_sp_flag_all_above` | `wc.T_tagger.shw_sp_flag_all_above` | vertex / gap geometry | 0 | NTSinglePhoton:1620 | not stated | 0.782 |
| 52 | `shw_sp_min_dQ_dx_5` | `wc.T_tagger.shw_sp_min_dQ_dx_5` | calorimetry (dQ/dx, dE/dx) | 1 | NTSinglePhoton:1623 | not stated | 0.943 |
| 53 | `shw_sp_n_other_vertex` | `wc.T_tagger.shw_sp_n_other_vertex` | vertex / gap geometry | 2 | NTSinglePhoton:1634 | not stated | 0.162 |
| 54 | `shw_sp_n_stem_size` | `wc.T_tagger.shw_sp_n_stem_size` | vertex / gap geometry | 20 | NTSinglePhoton:1635 | not stated | 0.028 |
| 55 | `shw_sp_min_dis` | `wc.T_tagger.shw_sp_min_dis` | vertex / gap geometry | 0 | NTSinglePhoton:1633 | cm | 0.000 |
| 56 | `shw_sp_vec_mean_dedx` | `wc.T_tagger.shw_sp_vec_mean_dedx` | calorimetry (dQ/dx, dE/dx) | 0 | NTSinglePhoton:1657 | not stated | 0.006 |
| 57 | `shw_sp_proton_length_1` | `wc.T_tagger.shw_sp_proton_length_1` | track / hadron activity | -1 | NTSinglePhoton:2525 | not stated | 0.728 |
| 58 | `shw_sp_proton_dqdx_1` | `wc.T_tagger.shw_sp_proton_dqdx_1` | track / hadron activity | -1 | NTSinglePhoton:2526 | not stated | 0.728 |
| 59 | `shw_sp_proton_energy_1` | `wc.T_tagger.shw_sp_proton_energy_1` | track / hadron activity | -1 | NTSinglePhoton:2527 | not stated | 0.728 |
| 60 | `shw_sp_proton_length_2` | `wc.T_tagger.shw_sp_proton_length_2` | track / hadron activity | -1 | NTSinglePhoton:2528 | not stated | 0.964 |
| 61 | `shw_sp_proton_dqdx_2` | `wc.T_tagger.shw_sp_proton_dqdx_2` | track / hadron activity | -1 | NTSinglePhoton:2529 | not stated | 0.964 |
| 62 | `shw_sp_proton_energy_2` | `wc.T_tagger.shw_sp_proton_energy_2` | track / hadron activity | -1 | NTSinglePhoton:2530 | not stated | 0.964 |
| 63 | `shw_sp_n_good_showers` | `wc.T_tagger.shw_sp_n_good_showers` | multiplicity | 0 | NTSinglePhoton:2514 | not stated | 0.341 |
| 64 | `shw_sp_n_br1_showers` | `wc.T_tagger.shw_sp_n_br1_showers` | multiplicity | 0 | NTSinglePhoton:2516 | not stated | 0.000 |
| 65 | `shw_sp_n_br2_showers` | `wc.T_tagger.shw_sp_n_br2_showers` | multiplicity | 0 | NTSinglePhoton:2517 | not stated | 0.007 |
| 66 | `shw_sp_n_br3_showers` | `wc.T_tagger.shw_sp_n_br3_showers` | multiplicity | 0 | NTSinglePhoton:2518 | not stated | 0.133 |
| 67 | `shw_sp_n_br4_showers` | `wc.T_tagger.shw_sp_n_br4_showers` | multiplicity | 0 | NTSinglePhoton:2519 | not stated | 0.071 |
| 68 | `shw_sp_n_20br1_showers` | `wc.T_tagger.shw_sp_n_20br1_showers` | multiplicity | 0 | NTSinglePhoton:2520 | not stated | 0.000 |
| 69 | `shw_sp_shw_vtx_dis` | `wc.T_tagger.shw_sp_shw_vtx_dis` | vertex / gap geometry | -1 | NTSinglePhoton:2593 | not stated | 0.000 |
| 70 | `shw_sp_max_shw_dis` | `wc.T_tagger.shw_sp_max_shw_dis` | vertex / gap geometry | -1 | NTSinglePhoton:2594 | not stated | 0.000 |
| 71 | `numu_1_score` | `wc.T_tagger.numu_1_score` | upstream BDT scores | -0.4 | scorer (see section 4) | not stated | 0.000 |
| 72 | `numu_score` | `wc.T_tagger.numu_score` | upstream BDT scores | n/a | scorer (see section 4) | not stated | n/a |
