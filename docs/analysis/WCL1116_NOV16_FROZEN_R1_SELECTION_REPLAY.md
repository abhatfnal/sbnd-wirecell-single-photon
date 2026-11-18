# WCL1116 Nov16: frozen Round-1 selection replay (`NOV16_FROZEN_R1_SELECTION_REPLAY`)

Date: 2026-11-18. Branch `analysis/wcl1116-nov16-frozen-r1-replay-20261118` (base `daf95442515b601eecda41c6c586931a5ae38c54`). **Diagnostic only.** The selection is the frozen, source-faithful, corrected Round-1 chain applied unchanged to Haiwang's `WCLocal2026Nov16-FermiGrid` production. Nothing was tuned, trained, scanned or chosen from these results; no analysis FV was adopted; no vertex mode was chosen.

> **This is not the Round-2 reconstruction.** It answers *what the Nov16 reconstruction does to the already-frozen Round-1 analysis*; it does not answer which cuts or models Round 2 should use. The ~Nov 23 production is expected to change the effective boundary and possibly the upstream BDTs (section 13); the analysis must then be re-run with independently frozen choices. None of the numbers below may be used to set a Round-2 threshold, feature, model, vertex mode, FV, signal/topology/background definition or strategy.

## 1. Headline

Dedicated NC-Delta radiative MC, provisional TPC-box truth denominator 12,427 (identical for both productions):

| production | selected | efficiency | interval68 |
|---|---|---|---|
| old fg1-era `ncdr`, corrected Round 1 | 833 | 6.70 % | 6.48-6.94 % |
| WCLocal2026Nov16 `recTreeWireCell` | 1938 | 15.60 % | 15.27-15.93 % |

Generic BNB-CV selected non-signal events: **282 -> 685** (1g0p 150 -> 453; 1g1p 93 -> 178; >=2p 39 -> 54). The dedicated-signal efficiency rose by a factor 2.33 and the selected non-signal BNB count by a factor 2.43: **the larger efficiency comes with a similar increase in selected background, so this replay does not by itself show an improvement of the selection.** The efficiency is a dedicated-signal efficiency, not a purity or S/B (section 11).

## 2. Repository, corrections verified, tree, policy

- Repository `/home/abhat/Single-photon/sbnd-wirecell-single-photon`, host `jupyter-abhat-single-photon---9ba4d904`; analysis commit `daf9544` (scorer correction) is the base. The tree contains the corrections: TMVA response `v`; `score = log10((1+v)/(1-v))` applied **once** (`wcl1116_replay_common.to_D` keeps the raw response as `v_<model>` and transforms once; a test pins this); `kine_pio_flag = 0` for the legacy ncpi0 (the builder stores `c_score_ncpi0_pio0`, computed with `legacy_scorer.ncpi0_input_matrix(..., "zero")`); the four legacy MicroBooNE XMLs with the recorded SHA256 values (a test checks them); frozen thresholds numu > 0.4, other > 0.2, ncpi0 > -0.05, nue > -1.0. The obsolete tanh-space scorer and the SBND development BDTs (`DEV_DO_NOT_DEPLOY`) are not used.
- Tree read: **`recTreeWireCell`** (production default `dv2_split_move`); `caf.MergedCaf` opens only that tree. The alternate `recTreeWireCell_dv2snap` exists in the same files and is recorded for provenance only; it was **not** read and snap vs split-move was **not** compared.
- Selection (pre-FV): `shw_sp_n_20mev_showers > 0`; numu, other, ncpi0, nue scores as above; `shw_sp_n_20br1_showers == 1`. Candidate policy `any` (policy `first` also tabulated). No analysis FV; same truth signal definition, 35 MeV post-FSI proton topology, background taxonomy, candidate/evaluable semantics and non-finite treatment as corrected Round 1.
- Builder reproduction: the (additive) Nov16 builder reproduces the stored Round-1 candidate pieces exactly on the test files, and the old reference below reproduces every Round-1 anchor (asserted in code and pinned by a test).

## 3. What changed between the old production and Nov16

| item | old production (fg1 / ncdr) | WCLocal2026Nov16 | status |
|---|---|---|---|
| wire-cell-toolkit | 4b6853d4 (fg1, ncdr, run3bnb); f6fd2209 (open data) | 0.38.0, c935e30d (= master 647b2733 + version.txt) | CHANGED |
| larwirecell | sbnd-wc-flatcaf ad5d9421 (fg1/run3bnb/ncdr); 3b54651 (open data) | sbnd-wc-flatcaf ad5d9421 | same (fg1/ncdr/run3bnb) |
| wire-cell-data | 9e2f4b8 (run3bnb README); fg1/ncdr: not stated | 99c6497f (master with dv2max/sbnd/aurora_space) + XGB/SCN weights | CHANGED |
| DL vertex model / bundle | not stated | DV2-MAX aurora_space, dv2max/sbnd/aurora_space/bundle.json (sha256 51588842...) | CHANGED or unknown (old not stated) |
| DL vertex mode of recTreeWireCell | not named | dv2_split_move (default); a second tree uses dv2_snap | unknown (old not named) |
| step 1 (imaging/clustering/matching) | fg1 / ncdr / run3bnb step-1 tars | the same tars reused (array-by-array identical on 25/25 files, issue 48 P2) | unchanged |
| step 2 chain | wct-pr.jsonnet, dual chain in the old 'original' step 2 | wct-pr.jsonnet, single chain per mode | CHANGED |
| flat-tree schema md5 of recTreeWireCell | d4396a3490ea (2,401 branches) | af9c87c8 (2,416 branches; adds the DL-vertex space dump) | CHANGED (extra branches) |
| booked numu / nue BDT weights | not stated | not stated (uboone BDT weights listed) | not established |
| cosmic boundary configuration | box boundary (stated for Nov16 by Haiwang) | box boundary (current treatment) | same as stated; not independently verified |
| SCE policy | not stated | no SCE-back correction (stated by Haiwang) | not established for old |
| sbndcode | v10_14_02_03 e26:prof | v10_14_02_03 e26:prof | same |
| input reco1 / CAF files | fg1 / ncdr SAM selections | the same SAM selections (NC-Delta-rad: every pair; same 13,772 events) | same input events |

**Attribution verdict: `VERTEX + OTHER RECONSTRUCTION CHANGES`.** Step 1 (imaging, clustering, matching) is reused and identical, and the candidate set is unchanged (section 6), but step 2 changed in more than the vertex placement: the wire-cell-toolkit commit, the wire-cell-data bundle, the DL-vertex model/bundle, the step-2 chain structure and the flat-tree schema all differ. The old vertex mode and DL model, the booked numu/nue weights, the old cosmic boundary and SCE policy are *not stated* in the production documentation. The comparison therefore cannot be called vertex-only. Nov16 still uses the box boundary and no SCE back-correction (as stated by Haiwang).

## 4. Sample inventory (WCLocal2026Nov16-FermiGrid)

| folder | registry | pairs | pairs_OK | pairs_PARTIAL | pairs_EMPTY | merged_cafs | caf_events | wc_valid_split | wc_valid_snap |
|---|---|---|---|---|---|---|---|---|---|
| mc-cv | bnb_cv | 37742 | 37728 | 14 | 0 | 37742 | 500000 | 499968 | 499977 |
| mc-nuecc | nuecc | 11445 | 11430 | 11 | 4 | 11441 | 100003 | 99987 | 99987 |
| mc-ncdr | official_gen2_ncdelta | 15776 | 9150 | 0 | 6626 | 9150 | 13772 | 13772 | 13772 |
| beam-off | beam_off | 1096 | 1056 | 2 | 38 | 1058 | 49970 | 49968 | 49968 |
| run3bnb | run3bnb | 2208 | 2206 | 2 | 0 | 2208 | 109487 | 109485 | 109485 |
| opendata | beam_on_open | 1817 | 1817 | 0 | 0 | 1817 | 89946 | 89946 | 89946 |

Base `/pnfs/sbnd/persistent/users/yuhw/prod-fermigrid/WCLocal2026Nov16/<folder>/`; WCT 0.38.0 `c935e30d`, larwirecell `ad5d9421`, wire-cell-data `99c6497f` (DV2-MAX `aurora_space`), sbndcode `v10_14_02_03`; trees `recTreeWireCell` (schema `af9c87c8`, 2,416 branches) and `recTreeWireCell_dv2snap` (schema `d4396a34`). Counts equal Haiwang's README. Open data and Run-3 have no dedicated truth; the old open-data production used an older toolkit (`f6fd2209`) and an older schema, so its old-vs-new comparison is between two quite different productions.

**Critical gate: a refreshed dedicated NC-Delta sample IS available** (`mc-ncdr/`: the same SAM selection as Round 1, 13,772 events, all with Wire-Cell output, the same CAF files in the same order as the Round-1 manifest). The truth denominator is reco-independent and identical (12,427; all events of the denominator joined on run/subrun/event, one never arrived in either production). The apples-to-apples signal efficiency is therefore supportable. Generic-BNB NC-Delta events were not substituted for it.

## 5. Signal: cutflow, topology, first failure

Cumulative cutflow, policy `any`, denominator 12,427:

| stage | old | Nov16 | delta | old_pct_of_12427 | nov16_pct_of_12427 |
|---|---|---|---|---|---|
| candidate | 11331 | 11331 | 0 | 91.18 | 91.18 |
| n20mev | 8080 | 7838 | -242 | 65.02 | 63.07 |
| bdt_evaluable | 8034 | 7758 | -276 | 64.65 | 62.43 |
| numu | 4943 | 6395 | 1452 | 39.78 | 51.46 |
| other | 2717 | 4290 | 1573 | 21.86 | 34.52 |
| ncpi0 | 1305 | 2453 | 1148 | 10.5 | 19.74 |
| nue | 893 | 2002 | 1109 | 7.186 | 16.11 |
| n20br1 | 833 | 1938 | 1105 | 6.703 | 15.6 |
| final | 833 | 1938 | 1105 | 6.703 | 15.6 |

Efficiency (exact binomial 68 % interval):

| group | N_truth | old | nov16 |
|---|---|---|---|
| total | 12427 | 833 = 6.70 % (6.48-6.94) | 1938 = 15.60 % (15.27-15.93) |
| 0p | 5863 | 373 = 6.36 % (6.04-6.70) | 1071 = 18.27 % (17.76-18.79) |
| 1p | 5557 | 416 = 7.49 % (7.13-7.86) | 794 = 14.29 % (13.82-14.77) |
| >=2p | 1007 | 44 = 4.37 % (3.72-5.11) | 73 = 7.25 % (6.43-8.16) |
| Delta0 (descriptive; Delta charge is not reco proton topology) | 6846 | 394 = 5.76 % (5.47-6.05) | 1084 = 15.83 % (15.39-16.29) |
| Delta+ (descriptive; Delta charge is not reco proton topology) | 5581 | 439 = 7.87 % (7.50-8.24) | 854 = 15.30 % (14.82-15.80) |

Policy `first`: old 795 (6.40 %), Nov16 1872 (15.06 %).

Exclusive first failure, `any` policy, percent of 12,427 (Round-1 categories):

| category | old N | Nov16 N | old % | Nov16 % |
|---|---|---|---|---|
| bdt_not_evaluable | 46 | 80 | 0.37 | 0.644 |
| fail_n20br1 | 60 | 64 | 0.483 | 0.515 |
| fail_ncpi0 | 1409 | 1836 | 11.34 | 14.77 |
| fail_nue | 412 | 451 | 3.315 | 3.629 |
| fail_numu | 3094 | 1368 | 24.9 | 11.01 |
| fail_other | 2226 | 2101 | 17.91 | 16.91 |
| missing_from_merged_caf | 1 | 1 | 0.008 | 0.008 |
| no_20mev_shower | 3251 | 3493 | 26.16 | 28.11 |
| no_candidate | 1095 | 1095 | 8.811 | 8.811 |
| selected | 833 | 1938 | 6.703 | 15.6 |

**Reconstruction ceiling vs BDT response** (before any BDT cut):

| production | N_truth | wc_valid | with_candidate | n20_shower | bdt_evaluable | mean_ncand | total_candidates_signal_events |
|---|---|---|---|---|---|---|---|
| old_fg1 | 12427 | 12426 | 11331 | 8080 | 8034 | 0.9482 | 11783 |
| nov16 | 12427 | 12426 | 11331 | 7838 | 7758 | 0.9482 | 11783 |

Candidate formation is unchanged (same events, same candidate counts). The >20 MeV-shower and BDT-evaluable ceilings are slightly **lower** in Nov16. Everything that raises the efficiency is therefore in the BDT stages (`BDT RESPONSE MIGRATION`); no gain in the reconstruction ceiling is seen before the BDT cuts.

## 6. Signal migration (matched events, same run/subrun/event)

| migration | N | pct |
|---|---|---|
| old fail -> new fail | 10284 | 82.76 |
| old fail -> new pass | 1310 | 10.54 |
| old pass -> new fail | 205 | 1.65 |
| old pass -> new pass | 628 | 5.054 |

First stage whose cumulative any-candidate state differs (events that change selection):

| first_changed_stage | old fail -> new pass | old pass -> new fail |
|---|---|---|
| bdt_evaluable | 5 | 0 |
| n20br1 | 15 | 2 |
| n20mev | 265 | 42 |
| ncpi0 | 184 | 56 |
| nue | 99 | 26 |
| numu | 436 | 19 |
| other | 306 | 60 |

By truth topology and, descriptively, by Delta charge:

| topology | old fail -> new fail | old fail -> new pass | old pass -> new fail | old pass -> new pass |
|---|---|---|---|---|
| 0p | 4665 | 825 | 127 | 246 |
| 1p | 4698 | 443 | 65 | 351 |
| >=2p | 921 | 42 | 13 | 31 |

| delta | old fail -> new fail | old fail -> new pass | old pass -> new fail | old pass -> new pass |
|---|---|---|---|---|
| Delta+ | 4640 | 502 | 87 | 352 |
| Delta0 | 5644 | 808 | 118 | 276 |

First changed stage by topology: `tables/wcl1116_nov16_replay/signal_migration_stage_by_topology.csv`. Counter transitions (`shw_sp_filled`, >20 MeV shower count, `n_20br1` count) of matched candidates: `counts_migration_matched_candidates.csv`.

## 7. Vertex and reconstruction diagnostics (signal)

Reco-to-true neutrino-vertex distance (evaluation only; exact (0,0,0) = no vertex is excluded):

| production | topology | n_events | median_cm | frac_lt_1cm | frac_lt_3cm | frac_lt_5cm |
|---|---|---|---|---|---|---|
| old_fg1 | all | 11306 | 18.89 | 0.1663 | 0.2878 | 0.3297 |
| old_fg1 | 0p | 5194 | 29.27 | 0.04852 | 0.09569 | 0.1248 |
| old_fg1 | 1p | 5162 | 5.88 | 0.264 | 0.4361 | 0.4861 |
| old_fg1 | >=2p | 950 | 2.5 | 0.2789 | 0.5326 | 0.6011 |
| nov16 | all | 11309 | 1.546 | 0.4098 | 0.6033 | 0.6466 |
| nov16 | 0p | 5196 | 11.85 | 0.1809 | 0.3052 | 0.3634 |
| nov16 | 1p | 5163 | 0.7777 | 0.5997 | 0.8489 | 0.8793 |
| nov16 | >=2p | 950 | 0.7554 | 0.6295 | 0.8989 | 0.9305 |

Matched events (nearest candidate): the vertex moved >1 cm closer in 56.2 % and >1 cm farther in 5.6 % of events. Vertex proximity improved clearly for every topology.

Photon-reconstruction taxonomy of the signal photon (Round-1 code and classes unchanged; events with >= 1 candidate, N = 11,331 in both; the OLD column reproduces the Round-1 taxonomy table exactly):

| outcome | old N | Nov16 N | old % | Nov16 % |
|---|---|---|---|---|
| pass_not_via_signal_photon_shower | 2657 | 1134 | 23.45 | 10.01 |
| pass_photon_shower_in_passing_candidate | 5423 | 6704 | 47.86 | 59.17 |
| photon_as_track | 424 | 205 | 3.742 | 1.809 |
| photon_charge_outside_candidates | 329 | 323 | 2.904 | 2.851 |
| photon_fragmented | 492 | 260 | 4.342 | 2.295 |
| photon_in_other_candidate | 1 | 1 | 0.008825 | 0.008825 |
| photon_no_reco_charge | 275 | 280 | 2.427 | 2.471 |
| photon_particle_row_missing | 162 | 256 | 1.43 | 2.259 |
| photon_shower_below_20MeV | 40 | 40 | 0.353 | 0.353 |
| photon_shower_not_in_main_vertex_set | 567 | 432 | 5.004 | 3.813 |
| photon_shower_typed_non_electron | 961 | 1696 | 8.481 | 14.97 |

Improved: the signal photon's shower in a passing candidate, fewer fragmented photons, fewer photons typed as tracks, fewer showers outside the main-vertex set. **Worsened:** more photon showers typed as a non-electron particle and more photon particle rows missing. The new vertexing does not remove the Round-1 reconstruction loss categories uniformly. Proton/shower ownership beyond these classes was not re-derived.

Association of the selection change with the per-event vertex change (descriptive; truth used only for evaluation; **association, not causation**):

| split | cls | n_events | old_selected | new_selected | old_eff_pct | new_eff_pct | old_pass_new_fail | old_fail_new_pass |
|---|---|---|---|---|---|---|---|---|
| vertex_change | improved (>1 cm closer) | 6355 | 128 | 1128 | 2.014 | 17.75 | 89 | 1089 |
| vertex_change | no valid vertex in one production | 1121 | 0 | 0 | 0 | 0 | 0 | 0 |
| vertex_change | unchanged (within 1 cm) | 4319 | 669 | 772 | 15.49 | 17.87 | 87 | 190 |
| vertex_change | worsened (>1 cm farther) | 632 | 36 | 38 | 5.696 | 6.013 | 29 | 31 |
| new_within_5cm | new vertex < 5 cm | 7312 | 566 | 1076 | 7.741 | 14.72 | 128 | 638 |
| new_within_5cm | new vertex >= 5 cm | 3997 | 267 | 862 | 6.68 | 21.57 | 77 | 672 |
| new_within_5cm | no vertex | 1118 | 0 | 0 | 0 | 0 | 0 | 0 |

BDT-input change between the productions for matched candidates (first 600 files with candidates; a sample, `signal_bdt_input_shift*.csv`):

| family | n_inputs | mean_frac_changed | max_frac_changed |
|---|---|---|---|
| pi0 kinematics (kine_pio_*) | 12 | 0.6468 | 0.8109 |
| shower/vertex geometry | 24 | 0.6332 | 0.9919 |
| upstream numu scores | 4 | 0.491 | 0.9675 |
| shower multiplicity / quality | 73 | 0.4282 | 0.6346 |
| shower energy / dQdx | 25 | 0.3711 | 0.9165 |
| tagger sub-scores | 15 | 0.3527 | 0.4513 |
| other | 64 | 0.1448 | 0.6334 |

Inputs change broadly (the reconstructed vertex in ~99 % of matched candidates; shower geometry, pi0 kinematics, upstream numu scores in many), with median signed changes near zero: the frozen classifiers are evaluating many shifted inputs, not one offset feature or a default value. Frozen-score migration of matched candidates:

| model | view | n | median_shift | p16 | p84 | frac_cross_up | frac_cross_down | threshold |
|---|---|---|---|---|---|---|---|---|
| numu | matched candidates (event, nu_index) | 6648 | 0.2916 | -0.2963 | 2.114 | 0.2271 | 0.04377 | 0.4 |
| numu | event-level maximum over candidates | 6613 | 0.2926 | -0.3049 | 2.123 | 0.2285 | 0.04476 | 0.4 |
| other | matched candidates (event, nu_index) | 6648 | 0.08869 | -0.3093 | 1.39 | 0.2193 | 0.06303 | 0.2 |
| other | event-level maximum over candidates | 6613 | 0.08973 | -0.3133 | 1.392 | 0.2206 | 0.06336 | 0.2 |
| ncpi0 | matched candidates (event, nu_index) | 6639 | 0.02618 | -0.2984 | 0.9076 | 0.1964 | 0.08691 | -0.05 |
| ncpi0 | event-level maximum over candidates | 6604 | 0.0279 | -0.2993 | 0.9119 | 0.1981 | 0.08783 | -0.05 |
| nue | matched candidates (event, nu_index) | 6648 | 0.04068 | -0.3123 | 1.825 | 0.2139 | 0.05686 | -1 |
| nue | event-level maximum over candidates | 6613 | 0.04417 | -0.3121 | 1.828 | 0.2146 | 0.05701 | -1 |

## 8. Generic BNB CV

| production | selected_events | signal_like | non_signal | reco_1g0p | reco_1g1p | reco_ge2p |
|---|---|---|---|---|---|---|
| old_fg1 (corrected R1) | 291 | 9 | 282 | 150 | 93 | 39 |
| nov16 | 704 | 19 | 685 | 453 | 178 | 54 |

Non-signal selected events by candidate-associated truth category (Round-1 taxonomy, unchanged) with matched enter/leave counts:

| category | old | nov16 | difference | matched_enters | matched_leaves |
|---|---|---|---|---|---|
| CC_PI0 | 60 | 94 | 34 | 61 | 27 |
| COSMIC_OR_UNMATCHED | 13 | 25 | 12 | 23 | 11 |
| MULTI_OR_AMBIGUOUS | 3 | 5 | 2 | 4 | 2 |
| NC_PI0 | 116 | 316 | 200 | 243 | 43 |
| NUE_CC | 1 | 12 | 11 | 11 | 0 |
| NUMU_CC | 14 | 15 | 1 | 8 | 7 |
| OTHER_NC | 13 | 22 | 9 | 15 | 6 |
| OUTSIDE_TPC_NU | 62 | 196 | 134 | 157 | 23 |
| TOTAL non-signal | 282 | 685 | 403 | 522 | 119 |

Matched selection movement (events, same run/subrun/evt; first changed stage):

| movement | N |
|---|---|
| ENTERS (new selected, old not) | 532 |
| stays selected | 172 |
| LEAVES (old selected -> new not) | 119 |

| first_changed_stage | ENTERS (new selected, old not) | LEAVES (old selected -> new not) |
|---|---|---|
| bdt_evaluable | 1 | 0 |
| n20br1 | 9 | 0 |
| n20mev | 93 | 16 |
| ncpi0 | 74 | 27 |
| nue | 37 | 7 |
| numu | 187 | 36 |
| other | 131 | 33 |

The intrinsic-nueCC category among selected BNB non-signal events (the Round-1 source-faithful reference of 1) is 12 in Nov16. Natural NC-Delta in the BNB CV (117 events, descriptive, low statistics): final 8 -> 17 of 117.

## 9. nueCC control (dedicated intrinsic nueCC MC) and data controls

| sample | production | usable_events_wc_valid | candidates | events_candidate | events_n20mev | events_bdt_evaluable | events_numu | events_other | events_ncpi0 | events_nue | events_n20br1 | selected_per_1000_usable_events |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| nuecc | nov16 | 99987 | 98617 | 94889 | 81072 | 80253 | 45700 | 32840 | 26635 | 873 | 680 | 6.801 |
| nuecc | old (fg1 / open-data production) | 99946 | 98576 | 94849 | 80728 | 79976 | 39723 | 28408 | 22115 | 554 | 381 | 3.812 |
| beam_off | nov16 | 49968 | 4741 | 4705 | 981 | 872 | 404 | 25 | 12 | 6 | 6 | 0.1201 |
| beam_off | old (fg1 / open-data production) | 49917 | 4733 | 4697 | 899 | 820 | 349 | 24 | 9 | 5 | 4 | 0.08013 |
| beam_on_open | nov16 | 89946 | 42328 | 41795 | 8920 | 8321 | 2164 | 725 | 200 | 96 | 81 | 0.9005 |
| beam_on_open | old (fg1 / open-data production) | 89921 | 42316 | 41783 | 8936 | 8480 | 1856 | 490 | 130 | 35 | 26 | 0.2891 |
| run3bnb | nov16 | 109485 | 46682 | 46238 | 9862 | 9198 | 2505 | 790 | 226 | 106 | 96 | 0.8768 |

The Round-1 'reference of 1' belongs to the intrinsic-nueCC *category inside the generic BNB CV* (section 8), not to the dedicated nueCC sample; the dedicated-sample old reference above was rebuilt with the same builder and scorer. Matched old-vs-new migration of the controls:

| sample | matched_events | only_old | only_new | old_pass_new_pass | old_pass_new_fail | old_fail_new_pass | ncand_more | ncand_fewer |
|---|---|---|---|---|---|---|---|---|
| nuecc | 99984 | 0 | 0 | 148 | 233 | 532 | 44 | 4 |
| beam_off | 49970 | 0 | 0 | 2 | 2 | 4 | 8 | 0 |
| beam_on_open | 89946 | 0 | 0 | 18 | 8 | 63 | 12 | 0 |

First changed stage: `controls_first_changed_stage.csv`. The data controls are counts only: no truth interpretation, no new sideband, and no beam-off normalisation (blocker G is still open): the per-1,000-event rates are not exposure-normalised and beam-off and beam-on are not compared quantitatively. Run-3 BNB has no Round-1 counterpart. Data-vs-MC shape comparisons were **not** repeated (they would need the beam-off normalisation).

## 10. Figures

- `plots/wcl1116_nov16_replay/fig_cutflow_old_vs_nov16.png`: cumulative signal cutflow
- `plots/wcl1116_nov16_replay/fig_topology_efficiency_old_vs_nov16.png`: efficiency by truth topology
- `plots/wcl1116_nov16_replay/fig_vertex_distance_old_vs_nov16.png`: reco-vertex distance
- `plots/wcl1116_nov16_replay/fig_sp_scores_old_vs_nov16.png`: four frozen SP scores (identical binning; clipped at +-3)
- `plots/wcl1116_nov16_replay/fig_bnb_background_old_vs_nov16.png`: selected BNB non-signal by category

## 11. Purity / S/B / rate: exact definitions and what is supportable

Round 1 defined **no purity, no S/B and no significance**: they are blocked until the beam-off normalisation (G) and flash-time reference (H) are resolved (`ROUND2_EVALUATION_CONTRACT_SCORER_BASELINES.md`). None is derived here. The quantities that *are* defined are kept distinct:

| quantity | old | nov16 | note |
|---|---|---|---|
| dedicated-signal efficiency (selected / frozen truth denominator) | 6.70 % | 15.60 % | dedicated NC-Delta MC only |
| selected signal rate per 1e20 POT (Round-1 expected-yield definition; stat. only) | 29.3 +- 1.0 | 68.3 +- 1.4 | NOT an S/B |
| selected non-signal BNB rate per 1e20 POT (Poisson stat. only; no cosmic-only component) | 1037 | 2519 | CV exposure 2.72e+19 POT, same files |
| generic-BNB truth signal fraction (signal-like / selected events) | 9/291 = 3.09 % | 19/704 = 2.70 % | natural NC-Delta in generic MC; NOT a purity |
| BNB non-signal acceptance (selected non-signal / usable BNB-CV events) | 282/499,899 | 685/499,968 | background acceptance, descriptive |

Purity, S/B and significance: **not computed** (not defined in Round 1; the dedicated-signal and generic-BNB samples carry different physics normalisations and must not be combined into a purity).

## 12. Interpretation (diagnostic; no tuning)

**Improved**
- Reconstructed-vertex proximity: the fraction of events with a candidate vertex within 5 cm of the true vertex is 33 % -> 65 % (truth 0p 12 -> 36 %; truth 1p 49 -> 88 %).
- Photon-shower association: more signal photons end as a shower in a passing candidate; fewer fragmented, track-typed or main-vertex-set-excluded photons.
- Dedicated-signal efficiency 6.70 % -> 15.60 %, in every truth topology (6.36/7.49/4.37 -> 18.27/14.29/7.25 % for 0p/1p/>=2p); truth 0p is now the highest, a change of ordering.

**Worsened or not improved**
- The selected non-signal BNB count rose from 282 to 685; NC pi0, outside-TPC and CC pi0 categories rise, and the intrinsic-nueCC category from 1 to 12. The dedicated nueCC control selects 680 vs 381 events.
- Candidate formation is unchanged and the >20 MeV-shower ceiling is slightly lower; photons typed as a non-electron particle and missing particle rows increase.
- 205 signal events selected in the old reconstruction are not selected in Nov16.

**What is associated with the vertex / reconstruction change** (association only): the per-event selection change is concentrated in events whose vertex moved closer (table in section 7) and the frozen-BDT inputs change broadly. **What cannot be isolated:** the vertex placement from the other step-2 changes (toolkit, wire-cell-data, DL bundle, upstream numu/nue scores that are inputs of the SP numu/other BDTs, schema); the effect of the unchanged box boundary; and whether the response of the frozen MicroBooNE-trained classifiers to shifted inputs is a domain effect. No causal statement is made.

## 13. Nov16 versus the upcoming Nov23 production

**Nov16 contains:** Snehadri's improved vertexing (`aurora_space` DL bundle), the current **box boundary**, the shipped (MicroBooNE-trained) upstream BDTs, and **no SCE back-correction**.

**The upcoming ~Nov23 production is expected (per the collaboration plan communicated with this task; Haiwang's plan `issues/50-sbnd-effective-boundary/plan.md` itself gives no date and does not name Xuyang) to add or change:**

- a measured non-box *effective boundary* (wall inset versus drift distance, per TPC), with separate data and MC shapes, and no SCE back-correction for either;
- consequences that propagate through TGM, the STM containment gate, FC, the neutrino containment flags (`match_isFC`), the cosmic-tagger flags (BDT inputs), and the nue / single-photon `angular_cut`, `shower_to_wall` and `bad_reconstruction_2(_sp)` inputs (the plan marks these 'validate');
- possibly Xuyang's updated upstream BDT, and a full new production and analyzer rerun.

Therefore **the Nov16 result is not the final Round-2 result.** Its purpose is to isolate and document what the current improved reconstruction does to the frozen Round-1 analysis, as a clean reference. In particular the outside-TPC and cosmic-like background categories and the nue-sensitive stages are quantities for which the Nov23 inputs are expected to differ; no prediction of their direction is made here. The Nov23 analysis must re-freeze its choices independently of this replay.

## 14. Limits

- One production, one replay: nothing was tuned or selected from it; the alternate vertex tree was not read.
- The old nueCC, beam-off and open-data references were rebuilt with the same builder and scorer (not taken from Round-1 products, which did not rescore them); the old open-data production is a different, older toolkit.
- The BDT-input shift table is a 600-file sample; the taxonomy covers events with >= 1 candidate (N = 11,331); proton/shower ownership beyond the Round-1 classes and data-vs-MC shapes were not recomputed.
- A transient dCache pool outage caused missing pieces in the first CV and old-nueCC passes; they were re-read (0 errors in the final tables, 37,742 / 11,441 files).
- BNB selected-event truth uses the Round-1 `deep` association on the 704 newly selected candidates; statistics are Poisson-limited and no systematics are included.
