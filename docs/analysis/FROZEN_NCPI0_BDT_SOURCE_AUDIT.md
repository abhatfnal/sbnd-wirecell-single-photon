# Frozen `single_photon_ncpi0_bdt_final.xml`: source audit

Date: 2026-11-11. Branch `analysis/ncdelta-remaining-frozen-stage-audit-20261111`. Audit only: no retraining, no tuning, no threshold scan. Tags: **SOURCE**, **MEASURED**, **INFERRED** as in `FROZEN_NUMU_BDT_SOURCE_AUDIT.md`. Source commit `4b6853d4`. Per-input table: `tables/remaining_stage_audit/input_source_table_ncpi0.csv`.

## 1. The model

| item | value | tag |
|---|---|---|
| weight file | `single_photon_ncpi0_bdt_final.xml` (frozen stage name `single_photon_ncpi0_score`) | SOURCE |
| location read | `/exp/uboone/app/users/uboonepro/bbogart/wcp-uboone-bdt/weights/` | MEASURED |
| sha256 | `983a0d829aafdb4cb10afa273287cacab1cc27223bd46d3df5a2ebac1b3217c3` (identical to the reference bundle, `microboone_reference_SHA256SUMS.txt` line 9) | MEASURED |
| model type | TMVA `BDT::BDT`, `BoostType = Grad`, created by `xgboost2TMVA` | SOURCE |
| ensemble | **400 trees**, every tree depth 6, **18,622 leaves**, `boostWeight = 1.0`, all **45 inputs used** | MEASURED |
| score | `tanh(sum)`; frozen cut `score > -0.05` (margin `> atanh(-0.05) = -0.0500`) | SOURCE / config |
| split rule, preprocessing, missing values, where it runs | as for the numu BDT: right iff `x >= cut` (float32), no preprocessing, NaN -> -999 in production / not evaluable here, **not stored in the CAF** (offline scorer; reference = validated derived score) | SOURCE / MEASURED |
| what it is | the single-photon `ncpi0` BDT: **a neutral-pion rejection** built on the pi0 variables of the tagger and of the kinematics tree, on the shower multiplicity counters and on **15 upstream sub-BDT scores** | SOURCE (inputs) |

## 2. Score reproduction (Task 4)

| quantity | value |
|---|---|
| candidates scored | 8,447 |
| compared with the stored derived-table score (`c_score_ncpi0`) | 8,108 candidates; **max |difference| = 0.0** (339 without a stored score) |
| independent TMVA-rule float32 evaluator | max |difference| to the frozen scorer **2.41e-09**, median 1.3e-10; candidates above 1e-6: **0** |
| decision flips at the frozen threshold | **0** |
| tie-convention cases | **0** |
| non-finite recomputed scores | **4** (candidates with a non-finite input, not evaluable; outside the model-internal population) |
| transparent scalar XML reader (200 candidates) | agrees with the vectorised float32 evaluator, max 0.0 |

Exact at float level (2.4e-9, 0 candidates above 1e-6, no tie case, no decision flip). The four non-finite candidates have a non-finite `kine_pio_theta_1/theta_2/angle` (one also `kine_pio_mass`) input (MEASURED): they are not evaluable by this model and are the reason why 3 events pass the numu stage in the baseline without being "BDT evaluable" (see the combined report, section 2).

## 3. The 45 inputs by family (every row in section 6)

| family | n | what it is (from the fill code) | operative default |
|---|---|---|---|
| **pi0 topology, tagger side** | 8 | `shw_sp_pio_1_{mass, pio_type, energy_1, energy_2, dis_1, dis_2}`, `shw_sp_pio_flag_pio`, `shw_sp_pio_mip_id` (`NeutrinoTaggerSinglePhoton.cxx:2076-2096, 2607`): filled **only if the selected shower belongs to a reconstructed pi0 pair** (`map_shower_pio_id` of the pattern recognition): invariant mass of the pair (MeV), the pair type, the two shower energies (`kine_charge`, MeV) and their distances to the vertex (cm); `pio_mip_id` is the result of the mip identification of that shower | 0 |
| **pi0 topology, kinematics-tree side** | 12 | `kine_pio_{mass, flag, vtx_dis, energy_1, theta_1, phi_1, dis_1, energy_2, theta_2, phi_2, dis_2, angle}` (`T_kine`, `NeutrinoKinematics.cxx:1269-1283`): the best pi0 pair found by the kinematics tree of the candidate (mass in MeV, energies in MeV, angles in degrees, distances in cm, opening angle) | 0 (flag 0 = no pair) |
| **upstream BDT scores** | 15 | `tro_{1,2,4,5}_score`, `stw_{2,3,4}_score`, `sig_{1,2}_score`, `pio_2_score`, `lol_{1,2}_score`, `br3_{3,5,6}_score`: **sub-BDTs of the nueCC scorer** (`UbooneNueBDTScorer.cxx`, `cal_bdts_xgboost` step 1) evaluated on per-segment vectors (the minimum over the elements); written to `wc.T_tagger` | the scorer `default_val` (e.g. `sig_1` 0.59, `lol_1` 0.85, `tro_1` 0.28, `br3_3` 0.30; struct default 0 only if the scorer was not run, MEASURED never) |
| multiplicity / extra-shower counters | 5 | `shw_sp_n_20br1_showers`, `n_br1..4_showers` (counts of showers at the main vertex that pass the corresponding bad-reconstruction check; see `N20BR1_SEMANTICS.md`) | 0 |
| shower quality / gap | 5 | `shw_sp_hol_1_{min_length, min_angle}`, `hol_2_min_angle`, `lol_3_vtx_n_segs` (overlap checks `high/low_energy_overlapping`), `E_indirect_max_energy` (largest energy of a shower connected indirectly: an extra-shower variable) | 0 |

There is **no input of the vertex-to-photon gap** except through `shw_sp_n_*` counters and `E_indirect_max_energy`: `shw_sp_shw_vtx_dis` is **not** an input of the ncpi0 BDT.

## 4. Default and fill semantics (MEASURED, stage population 2,781 events; `default_fractions_ncpi0.csv`)
* **Tagger-side pi0 pair (`shw_sp_pio_flag_pio`, `pio_1_*`): at default (the shower is NOT in a reconstructed pair) for 90.3 %** of the events (truth 0p 89.7 %, truth 1p 90.7 %); **98.1 % of the events that survive vs 83.2 % of the events that fail**: 16.8 % of the rejected events have the selected shower in a reconstructed pi0 pair.
* **Kinematics-tree pi0 pair (`kine_pio_flag`): at default (no pair) for 29.8 %** of the events: the kinematics tree finds a pair for **70 %** of the events; it is at default for 52.2 % of the survivors and **9.8 % of the rejected**.
* **Upstream sub-BDT scores at the scorer default: 60.4 % on average over the 15** (sig_1 86.8 %, stw_4 71.1 %, ... tro_1 49.8 %): these sub-BDTs have nothing to score for most candidates; none is ever exactly 0 (the scorer ran).
* `E_indirect_max_energy` at 0 (no indirectly connected shower): 65.9 % (79.1 % of the survivors, 54.1 % of the rejected); `hol_1_min_length` 81.7 %.
* The counters `n_br1_showers`, `n_20br1_showers` and `lol_3_vtx_n_segs` are never at default 0 in this population.

## 5. What is and is not established
Established: file, checksum, structure, score transform, inputs and their fill code, defaults (struct and scorer), exact reproduction. Not established: the training sample; the definition of the "pi0 pair" of `map_shower_pio_id` and of the kinematics tree's `pio_kine` beyond the field names and the mass window used in `pi0_identification_sp` (135 +- 35 / 60 MeV, `pio_type`); whether the signal's single photon being paired is a reconstruction pairing with a fragment or with a hadronic shower (answered empirically in the combined report, section 7).

## 6. The 45 inputs in XML order
| idx | variable | CAF branch | family | struct / operative default | first fill (file:line) | units (fill code) | fraction at default (stage population) |
|---|---|---|---|---|---|---|---|
| 0 | `shw_sp_pio_1_mass` | `wc.T_tagger.shw_sp_pio_1_mass` | pi0 topology | 0 | NTSinglePhoton:2091 | MeV | 0.903 |
| 1 | `shw_sp_pio_1_pio_type` | `wc.T_tagger.shw_sp_pio_1_pio_type` | pi0 topology | 0 | NTSinglePhoton:2092 | not stated | 0.903 |
| 2 | `shw_sp_pio_1_energy_1` | `wc.T_tagger.shw_sp_pio_1_energy_1` | pi0 topology | 0 | NTSinglePhoton:2093 | MeV | 0.903 |
| 3 | `shw_sp_pio_1_energy_2` | `wc.T_tagger.shw_sp_pio_1_energy_2` | pi0 topology | 0 | NTSinglePhoton:2094 | MeV | 0.903 |
| 4 | `shw_sp_pio_1_dis_1` | `wc.T_tagger.shw_sp_pio_1_dis_1` | pi0 topology | 0 | NTSinglePhoton:2095 | cm | 0.920 |
| 5 | `shw_sp_pio_1_dis_2` | `wc.T_tagger.shw_sp_pio_1_dis_2` | pi0 topology | 0 | NTSinglePhoton:2096 | cm | 0.926 |
| 6 | `shw_sp_pio_mip_id` | `wc.T_tagger.shw_sp_pio_mip_id` | pi0 topology | 0 | NTSinglePhoton:2607 | not stated | 0.176 |
| 7 | `shw_sp_pio_flag_pio` | `wc.T_tagger.shw_sp_pio_flag_pio` | pi0 topology | 0 | NTSinglePhoton:2076 | not stated | 0.903 |
| 8 | `shw_sp_n_20br1_showers` | `wc.T_tagger.shw_sp_n_20br1_showers` | multiplicity | 0 | NTSinglePhoton:2520 | not stated | 0.000 |
| 9 | `shw_sp_n_br1_showers` | `wc.T_tagger.shw_sp_n_br1_showers` | multiplicity | 0 | NTSinglePhoton:2516 | not stated | 0.000 |
| 10 | `shw_sp_n_br2_showers` | `wc.T_tagger.shw_sp_n_br2_showers` | multiplicity | 0 | NTSinglePhoton:2517 | not stated | 0.003 |
| 11 | `shw_sp_n_br3_showers` | `wc.T_tagger.shw_sp_n_br3_showers` | multiplicity | 0 | NTSinglePhoton:2518 | not stated | 0.154 |
| 12 | `shw_sp_n_br4_showers` | `wc.T_tagger.shw_sp_n_br4_showers` | multiplicity | 0 | NTSinglePhoton:2519 | not stated | 0.091 |
| 13 | `shw_sp_E_indirect_max_energy` | `wc.T_tagger.shw_sp_E_indirect_max_energy` | vertex / gap geometry | 0 | NTSinglePhoton:1631 | MeV | 0.659 |
| 14 | `shw_sp_lol_3_vtx_n_segs` | `wc.T_tagger.shw_sp_lol_3_vtx_n_segs` | shower quality (br/lem/hol/lol) | 0 | NTSinglePhoton:2026 | not stated | 0.000 |
| 15 | `shw_sp_hol_1_min_length` | `wc.T_tagger.shw_sp_hol_1_min_length` | shower quality (br/lem/hol/lol) | 0 | NTSinglePhoton:1776 | cm | 0.817 |
| 16 | `shw_sp_hol_2_min_angle` | `wc.T_tagger.shw_sp_hol_2_min_angle` | shower quality (br/lem/hol/lol) | 0 | NTSinglePhoton:1835 | not stated | 0.543 |
| 17 | `shw_sp_hol_1_min_angle` | `wc.T_tagger.shw_sp_hol_1_min_angle` | shower quality (br/lem/hol/lol) | 0 | NTSinglePhoton:1773 | not stated | 0.543 |
| 18 | `tro_5_score` | `wc.T_tagger.tro_5_score` | upstream BDT scores | 0.5 | scorer (see section 4) | not stated | 0.605 |
| 19 | `tro_4_score` | `wc.T_tagger.tro_4_score` | upstream BDT scores | 0.33 | scorer (see section 4) | not stated | 0.498 |
| 20 | `tro_2_score` | `wc.T_tagger.tro_2_score` | upstream BDT scores | 0.35 | scorer (see section 4) | not stated | 0.647 |
| 21 | `tro_1_score` | `wc.T_tagger.tro_1_score` | upstream BDT scores | 0.28 | scorer (see section 4) | not stated | 0.498 |
| 22 | `stw_4_score` | `wc.T_tagger.stw_4_score` | upstream BDT scores | 0.7 | scorer (see section 4) | not stated | 0.711 |
| 23 | `stw_3_score` | `wc.T_tagger.stw_3_score` | upstream BDT scores | 0.5 | scorer (see section 4) | not stated | 0.618 |
| 24 | `stw_2_score` | `wc.T_tagger.stw_2_score` | upstream BDT scores | 0.7 | scorer (see section 4) | not stated | 0.676 |
| 25 | `sig_2_score` | `wc.T_tagger.sig_2_score` | upstream BDT scores | 0.55 | scorer (see section 4) | not stated | 0.503 |
| 26 | `sig_1_score` | `wc.T_tagger.sig_1_score` | upstream BDT scores | 0.59 | scorer (see section 4) | not stated | 0.868 |
| 27 | `pio_2_score` | `wc.T_tagger.pio_2_score` | upstream BDT scores | 0.2 | scorer (see section 4) | not stated | 0.553 |
| 28 | `lol_2_score` | `wc.T_tagger.lol_2_score` | upstream BDT scores | 0.7 | scorer (see section 4) | not stated | 0.690 |
| 29 | `lol_1_score` | `wc.T_tagger.lol_1_score` | upstream BDT scores | 0.85 | scorer (see section 4) | not stated | 0.498 |
| 30 | `br3_6_score` | `wc.T_tagger.br3_6_score` | upstream BDT scores | 0.75 | scorer (see section 4) | not stated | 0.604 |
| 31 | `br3_5_score` | `wc.T_tagger.br3_5_score` | upstream BDT scores | 0.42 | scorer (see section 4) | not stated | 0.587 |
| 32 | `br3_3_score` | `wc.T_tagger.br3_3_score` | upstream BDT scores | 0.3 | scorer (see section 4) | not stated | 0.498 |
| 33 | `kine_pio_mass` | `wc.T_kine.kine_pio_mass` | pi0 topology | 0 | scorer (see section 4) | not stated | 0.299 |
| 34 | `kine_pio_flag` | `wc.T_kine.kine_pio_flag` | pi0 topology | 0 | scorer (see section 4) | not stated | 0.298 |
| 35 | `kine_pio_vtx_dis` | `wc.T_kine.kine_pio_vtx_dis` | pi0 topology | 0 | scorer (see section 4) | not stated | 0.976 |
| 36 | `kine_pio_energy_1` | `wc.T_kine.kine_pio_energy_1` | pi0 topology | 0 | scorer (see section 4) | not stated | 0.298 |
| 37 | `kine_pio_theta_1` | `wc.T_kine.kine_pio_theta_1` | pi0 topology | 0 | scorer (see section 4) | not stated | 0.298 |
| 38 | `kine_pio_phi_1` | `wc.T_kine.kine_pio_phi_1` | pi0 topology | 0 | scorer (see section 4) | not stated | 0.299 |
| 39 | `kine_pio_dis_1` | `wc.T_kine.kine_pio_dis_1` | pi0 topology | 0 | scorer (see section 4) | not stated | 0.475 |
| 40 | `kine_pio_energy_2` | `wc.T_kine.kine_pio_energy_2` | pi0 topology | 0 | scorer (see section 4) | not stated | 0.299 |
| 41 | `kine_pio_theta_2` | `wc.T_kine.kine_pio_theta_2` | pi0 topology | 0 | scorer (see section 4) | not stated | 0.298 |
| 42 | `kine_pio_phi_2` | `wc.T_kine.kine_pio_phi_2` | pi0 topology | 0 | scorer (see section 4) | not stated | 0.298 |
| 43 | `kine_pio_dis_2` | `wc.T_kine.kine_pio_dis_2` | pi0 topology | 0 | scorer (see section 4) | not stated | 0.465 |
| 44 | `kine_pio_angle` | `wc.T_kine.kine_pio_angle` | pi0 topology | 0 | scorer (see section 4) | not stated | 0.298 |
