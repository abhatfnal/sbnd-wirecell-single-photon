# Frozen `single_photon_nue_bdt_final.xml`: source audit (light)

Date: 2026-11-11. Branch `analysis/ncdelta-remaining-frozen-stage-audit-20261111`. Audit only. The `nue` stage is **inactive at the frozen threshold**, so this is a short audit; it records the model, the inputs and why the cut removes nothing. (This is the single-photon-specific `nue` BDT of 56 `shw_sp_*` inputs; it is **not** the nueCC xgboost `nue_score` of `UbooneNueBDTScorer`.)

| item | value |
|---|---|
| weight file / sha256 | `single_photon_nue_bdt_final.xml`, `8580ba04b4a9e3c7aefbb4d5da5006cff2a131804a7b594843461a7cd6f3758a` (identical to the reference bundle, line 10) |
| model | TMVA `BDT::BDT`, `BoostType = Grad`, `xgboost2TMVA`; **300 trees**, depth 5, **8,536 leaves**, `boostWeight = 1.0`, all 56 inputs used |
| score and cut | `tanh(sum)`; frozen cut `score > -1.0` |
| inputs (56) | `shw_sp_*` only: calorimetry 31 (the whole dQ/dx vector 0-19 plus summaries and dE/dx), vertex/gap geometry 11, track/hadron activity 7, multiplicity 6 (incl. `n_20mev_showers`, `n_20br1_showers`), `shw_sp_n_good_showers`; **no upstream BDT score and no cosmic input** |
| reproduction | 8,112 candidates compared with the stored derived score: max |difference| 0.0; independent TMVA-rule evaluator: **5 tie-convention cases** (a visited split with an input exactly on its cut) where the two conventions differ, **max |difference| 0.109** (the other candidates agree to 3e-9); **0 decision flips** at -1.0 |

**Why it is inactive.** The score is `tanh` of a finite margin and therefore lies in the open interval (-1, 1): the cut `> -1.0` is satisfied by every finite score by construction. MEASURED: the lowest nue score over the 8,447 scored candidates is -0.999998; no candidate has `score <= -1`; the stage removes no event (1,313 enter, 1,313 survive). The cut would only act on a non-finite input (production returns -999), and the baseline's evaluability flag already handles those candidates earlier (5 candidates are flagged `nonfinite_input` in the baseline; among the numu/ncpi0/nue inputs scanned here 4 candidates are non-finite, all in `kine_pio_theta/angle/mass` of the ncpi0 model). The five tie-convention cases show that the choice of the `x <= cut` vs `x >= cut` convention can change a nue score by up to 0.11 for exactly-on-the-cut inputs; it never matters for the frozen threshold. Nothing unexpected in the source semantics: the stage is **vacuous at this threshold**, not a dependency of the downstream stages (nue's inputs are all shared with other stages).

## Inputs (XML order)
| idx | variable | CAF branch | declared default | first fill (file:line) |
|---|---|---|---|---|
| 0 | `shw_sp_max_dQ_dx_sample` | `wc.T_tagger.shw_sp_max_dQ_dx_sample` | 1 | NTSinglePhoton:1612 |
| 1 | `shw_sp_n_below_threshold` | `wc.T_tagger.shw_sp_n_below_threshold` | 19 | NTSinglePhoton:1615 |
| 2 | `shw_sp_n_below_zero` | `wc.T_tagger.shw_sp_n_below_zero` | 0 | NTSinglePhoton:1626 |
| 3 | `shw_sp_n_lowest` | `wc.T_tagger.shw_sp_n_lowest` | 1 | NTSinglePhoton:1628 |
| 4 | `shw_sp_n_highest` | `wc.T_tagger.shw_sp_n_highest` | 1 | NTSinglePhoton:1629 |
| 5 | `shw_sp_lowest_dQ_dx` | `wc.T_tagger.shw_sp_lowest_dQ_dx` | 1 | NTSinglePhoton:1624 |
| 6 | `shw_sp_highest_dQ_dx` | `wc.T_tagger.shw_sp_highest_dQ_dx` | 1 | NTSinglePhoton:1627 |
| 7 | `shw_sp_medium_dQ_dx` | `wc.T_tagger.shw_sp_medium_dQ_dx` | 1 | NTSinglePhoton:1636 |
| 8 | `shw_sp_stem_length` | `wc.T_tagger.shw_sp_stem_length` | 1 | NTSinglePhoton:1630 |
| 9 | `shw_sp_length_main` | `wc.T_tagger.shw_sp_length_main` | 1 | NTSinglePhoton:1621 |
| 10 | `shw_sp_length_total` | `wc.T_tagger.shw_sp_length_total` | 1 | NTSinglePhoton:1622 |
| 11 | `shw_sp_n_vertex` | `wc.T_tagger.shw_sp_n_vertex` | 1 | NTSinglePhoton:1617 |
| 12 | `shw_sp_n_good_tracks` | `wc.T_tagger.shw_sp_n_good_tracks` | 0 | NTSinglePhoton:1616 |
| 13 | `shw_sp_E_indirect_max_energy` | `wc.T_tagger.shw_sp_E_indirect_max_energy` | 0 | NTSinglePhoton:1631 |
| 14 | `shw_sp_flag_all_above` | `wc.T_tagger.shw_sp_flag_all_above` | 0 | NTSinglePhoton:1620 |
| 15 | `shw_sp_min_dQ_dx_5` | `wc.T_tagger.shw_sp_min_dQ_dx_5` | 1 | NTSinglePhoton:1623 |
| 16 | `shw_sp_n_other_vertex` | `wc.T_tagger.shw_sp_n_other_vertex` | 2 | NTSinglePhoton:1634 |
| 17 | `shw_sp_n_stem_size` | `wc.T_tagger.shw_sp_n_stem_size` | 20 | NTSinglePhoton:1635 |
| 18 | `shw_sp_min_dis` | `wc.T_tagger.shw_sp_min_dis` | 0 | NTSinglePhoton:1633 |
| 19 | `shw_sp_vec_mean_dedx` | `wc.T_tagger.shw_sp_vec_mean_dedx` | 0 | NTSinglePhoton:1657 |
| 20 | `shw_sp_vec_dQ_dx_0` | `wc.T_tagger.shw_sp_vec_dQ_dx_0` | 1 | NTSinglePhoton:1613 |
| 21 | `shw_sp_vec_dQ_dx_1` | `wc.T_tagger.shw_sp_vec_dQ_dx_1` | 1 | NTSinglePhoton:1614 |
| 22 | `shw_sp_vec_dQ_dx_2` | `wc.T_tagger.shw_sp_vec_dQ_dx_2` | 0 | NTSinglePhoton:1638 |
| 23 | `shw_sp_vec_dQ_dx_3` | `wc.T_tagger.shw_sp_vec_dQ_dx_3` | 0 | NTSinglePhoton:1639 |
| 24 | `shw_sp_vec_dQ_dx_4` | `wc.T_tagger.shw_sp_vec_dQ_dx_4` | 0 | NTSinglePhoton:1640 |
| 25 | `shw_sp_vec_dQ_dx_5` | `wc.T_tagger.shw_sp_vec_dQ_dx_5` | 0 | NTSinglePhoton:1641 |
| 26 | `shw_sp_vec_dQ_dx_6` | `wc.T_tagger.shw_sp_vec_dQ_dx_6` | 0 | NTSinglePhoton:1642 |
| 27 | `shw_sp_vec_dQ_dx_7` | `wc.T_tagger.shw_sp_vec_dQ_dx_7` | 0 | NTSinglePhoton:1643 |
| 28 | `shw_sp_vec_dQ_dx_8` | `wc.T_tagger.shw_sp_vec_dQ_dx_8` | 0 | NTSinglePhoton:1644 |
| 29 | `shw_sp_vec_dQ_dx_9` | `wc.T_tagger.shw_sp_vec_dQ_dx_9` | 0 | NTSinglePhoton:1645 |
| 30 | `shw_sp_vec_dQ_dx_10` | `wc.T_tagger.shw_sp_vec_dQ_dx_10` | 0 | NTSinglePhoton:1646 |
| 31 | `shw_sp_vec_dQ_dx_11` | `wc.T_tagger.shw_sp_vec_dQ_dx_11` | 0 | NTSinglePhoton:1647 |
| 32 | `shw_sp_vec_dQ_dx_12` | `wc.T_tagger.shw_sp_vec_dQ_dx_12` | 0 | NTSinglePhoton:1648 |
| 33 | `shw_sp_vec_dQ_dx_13` | `wc.T_tagger.shw_sp_vec_dQ_dx_13` | 0 | NTSinglePhoton:1649 |
| 34 | `shw_sp_vec_dQ_dx_14` | `wc.T_tagger.shw_sp_vec_dQ_dx_14` | 0 | NTSinglePhoton:1650 |
| 35 | `shw_sp_vec_dQ_dx_15` | `wc.T_tagger.shw_sp_vec_dQ_dx_15` | 0 | NTSinglePhoton:1651 |
| 36 | `shw_sp_vec_dQ_dx_16` | `wc.T_tagger.shw_sp_vec_dQ_dx_16` | 0 | NTSinglePhoton:1652 |
| 37 | `shw_sp_vec_dQ_dx_17` | `wc.T_tagger.shw_sp_vec_dQ_dx_17` | 0 | NTSinglePhoton:1653 |
| 38 | `shw_sp_vec_dQ_dx_18` | `wc.T_tagger.shw_sp_vec_dQ_dx_18` | 0 | NTSinglePhoton:1654 |
| 39 | `shw_sp_vec_dQ_dx_19` | `wc.T_tagger.shw_sp_vec_dQ_dx_19` | 0 | NTSinglePhoton:1655 |
| 40 | `shw_sp_vec_median_dedx` | `wc.T_tagger.shw_sp_vec_median_dedx` | 0 | NTSinglePhoton:1656 |
| 41 | `shw_sp_proton_length_1` | `wc.T_tagger.shw_sp_proton_length_1` | -1 | NTSinglePhoton:2525 |
| 42 | `shw_sp_proton_dqdx_1` | `wc.T_tagger.shw_sp_proton_dqdx_1` | -1 | NTSinglePhoton:2526 |
| 43 | `shw_sp_proton_energy_1` | `wc.T_tagger.shw_sp_proton_energy_1` | -1 | NTSinglePhoton:2527 |
| 44 | `shw_sp_proton_length_2` | `wc.T_tagger.shw_sp_proton_length_2` | -1 | NTSinglePhoton:2528 |
| 45 | `shw_sp_proton_dqdx_2` | `wc.T_tagger.shw_sp_proton_dqdx_2` | -1 | NTSinglePhoton:2529 |
| 46 | `shw_sp_proton_energy_2` | `wc.T_tagger.shw_sp_proton_energy_2` | -1 | NTSinglePhoton:2530 |
| 47 | `shw_sp_n_good_showers` | `wc.T_tagger.shw_sp_n_good_showers` | 0 | NTSinglePhoton:2514 |
| 48 | `shw_sp_n_20mev_showers` | `wc.T_tagger.shw_sp_n_20mev_showers` | 0 | NTSinglePhoton:2515 |
| 49 | `shw_sp_n_br1_showers` | `wc.T_tagger.shw_sp_n_br1_showers` | 0 | NTSinglePhoton:2516 |
| 50 | `shw_sp_n_br2_showers` | `wc.T_tagger.shw_sp_n_br2_showers` | 0 | NTSinglePhoton:2517 |
| 51 | `shw_sp_n_br3_showers` | `wc.T_tagger.shw_sp_n_br3_showers` | 0 | NTSinglePhoton:2518 |
| 52 | `shw_sp_n_br4_showers` | `wc.T_tagger.shw_sp_n_br4_showers` | 0 | NTSinglePhoton:2519 |
| 53 | `shw_sp_n_20br1_showers` | `wc.T_tagger.shw_sp_n_20br1_showers` | 0 | NTSinglePhoton:2520 |
| 54 | `shw_sp_shw_vtx_dis` | `wc.T_tagger.shw_sp_shw_vtx_dis` | -1 | NTSinglePhoton:2593 |
| 55 | `shw_sp_max_shw_dis` | `wc.T_tagger.shw_sp_max_shw_dis` | -1 | NTSinglePhoton:2594 |
