# Truth-origin taxonomy of every reconstructed `T_kine` row (mutually exclusive, exhaustive, source-grounded)

Date: 2026-11-11. Branch `analysis/ncdelta-proton-truth-association-20261111`. Audit only: no selection, threshold or policy changes. Code: `scripts/proton_truth_scan.py` (raw tables), `src/sbnd_single_photon/proton_tables.py` (classification), `scripts/proton_truth_audit.py` (tables, figures). Row semantics: `RECO_PROTON_ROW_SEMANTICS.md`; match semantics: `WIRECELL_TRUTH_MATCH_SEMANTICS.md`.

## 1. The association (no spatial matching, no new truth-match cut)

* **Level.** `T_match` **level 1, side 0** is the production *one-to-one* object of a reco particle: exactly one row per `(nu_index, kine_index)` = one `T_kine` row (0 duplicate keys in all 12,426 events; the 16 events whose stored partner lists are unreadable are flagged). Its up to three truth partners are **truth prongs** (`truth_trackid` = `prong_trackid`, `truth_nu_idx` = interaction, -1 = non-neutrino object) ranked by **point IoU** (`match_iou_n`); the stored order *is* the production ranking, so the **top partner `p1` is `match_obj[0]`**. Charge IoU (`match_iou_q`) is stored and reported but never used to rank. No `T_overlap` aggregation was needed (a one-to-one level exists); `T_overlap` is used as an independent **cross-check only**: the dominant-charge truth track of the row agrees with `p1` for 97.6 % of the 6,916 proton-typed rows above 35 MeV that have an overlap entry (98.0 % for class A, 67 % for class G, `row_topmatch_vs_overlap_disagreement.csv`).
* **Truth attributes of a partner** come from `T_truth_track` (pdg, interaction, `process`, mother pdg, charge) and `T_truth_pf` (KE, momentum): interaction identity `t_nu`, particle `t_pdg`, **primary = Geant4 `process == 0`** (the generator-level, post-FSI particle). `parent_trackid == 0` and `ancestor_trackid == trackid` are *not* used: a secondary whose parent was not stored has `parent_trackid == 0` too (measured: this over-counts primaries; with `process == 0` the signal-primary protons reproduce the baseline truth multiplicities `n_p35_prim` / `n_p50` exactly at 50 MeV and in all but one event at 35 MeV, see section 5).
* **Signal interaction** = the `T_truth_nu` interaction whose vertex matches the signal neutrino (11,331 of 11,331 candidate-stage events; 12,426 of 12,426 with a file).

## 2. The classes (first match wins; applied to every row of every candidate, any type)

| # | class | definition (top partner `p1`, second partner `p2`) |
|---|---|---|
| A | `true_primary_signal_proton` | `p1` is a proton of the signal interaction with `process == 0` (a post-FSI primary) |
| B | `other_neutrino_proton` | `p1` is a proton (primary or secondary) of **another** neutrino interaction of the event |
| C | `geant4_secondary_proton` | `p1` is a proton of the signal interaction with `process != 0` (Geant4 secondary: neutron/proton inelastic or elastic, decay, ...) |
| D | `signal_nonproton_misidentified` | `p1` is another particle of the signal interaction (sub-types `photon_electron`, `pion`, `muon`, `neutron`, `other`) |
| E | `other_neutrino_nonproton` | `p1` is a non-proton particle of another neutrino interaction |
| F | `cosmic_or_non_neutrino` | `p1` is a non-neutrino (cosmic) object (`truth_nu_idx = -1`) |
| G | `ambiguous_multiple_truth` | `p2` exists, its **class (A-F) differs** from the class of `p1`, and `iou_n(p2) >= 0.5 x iou_n(p1)`; takes precedence over A-F |
| H | `unmatched` | no partner (`nmatch == 0`), no level-1 object, or an unreadable/unresolved partner (reason recorded) |

Mutually exclusive and exhaustive by construction (`np.select` on the top partner, then G; asserted in the code and pinned by `tests/test_proton_truth.py`). The category B definition merges primary and secondary protons of another interaction (567 proton-typed rows above 35 MeV, 97 % of them in candidates other than the signal-matched one); cosmic secondary protons are F. The 0.5 ratio of class G is an analysis choice; its sensitivity is in `row_origin_G_ratio_sensitivity.csv` (G = 0 / 218 / 146 / 59 / 1 rows for ratio off / 0.33 / 0.5 / 0.75 / 1.0, taken mostly from A and C).

## 3. Result: every proton-typed row above 35 MeV (all candidates, 6,941 rows; `row_origin_taxonomy.csv`)

| class | rows | % | signal-matched candidate (6,280 rows) | final-selected candidate (719 rows) |
|---|---|---|---|---|
| A true primary signal proton | 3,825 | 55.1 | 60.6 % | 84.1 % |
| C Geant4 secondary proton (signal interaction) | 1,250 | 18.0 | 19.8 % | 9.6 % |
| D signal non-proton (photon 967, pion 13, other 45) | 1,025 | 14.8 | 16.2 % | 3.8 % |
| B other-neutrino proton | 567 | 8.2 | 0.3 % | 0.1 % |
| G ambiguous | 146 | 2.1 | 2.2 % | 1.9 % |
| F cosmic / non-neutrino | 75 | 1.1 | 0.5 % | 0.3 % |
| H unmatched | 28 | 0.4 | 0.4 % | 0.1 % |
| E other-neutrino non-proton | 25 | 0.4 | 0.0 % | 0.0 % |

Of the 1,025 class-D rows, **967 (94 %) are the signal photon itself typed as a proton** (a shower row or a short track whose start segment was typed proton): the Phase-9 "photon typed muon/pion/proton" mechanism seen from the proton side. Class B is a candidate-level effect: other interactions of the event sit in other candidates, which is why only 0.3 % of the rows of the signal-matched candidate are B.

## 4. Association quality (proton-typed rows above 35 MeV; `row_association_quality_proton_ke35.csv`, `row_hc_subset_by_origin.csv`)

| class | n | median top point IoU | median 2nd IoU | median top-minus-second | mutual | `nmatch` mean |
|---|---|---|---|---|---|---|
| A | 3,825 | 0.93 | 0.06 | 0.91 | 96.4 % | 1.54 |
| C | 1,250 | 0.89 | 0.04 | 0.86 | 97.8 % | 1.81 |
| B | 567 | 0.83 | 0.03 | 0.81 | 97.7 % | 1.99 |
| F | 75 | 0.93 | 0.05 | 0.89 | 89 % | 1.48 |
| **D** | 1,025 | **0.17** | 0.04 | **0.17** | **31 %** | 1.11 |
| G | 146 | 0.50 | 0.34 | 0.12 | 90 % | 2.50 |
| all | 6,941 | 0.87 | 0.05 | 0.84 | 86 % | 1.58 |

Class D is a different regime: the proton-typed row carries only a small part of the photon's charge (point IoU 0.17, mutual in 31 %), consistent with a photon fragment typed as a proton. The **validation-only high-confidence subset** (`iou_n >= 0.5`, mutual, top-minus-second >= 0.2) holds 5,532 of the 6,941 rows (79.7 %: A 92 %, C 94 %, B 90 %, D 22 %, G 21 %); it is used for the KE-response diagnostic and nowhere else; **all rows stay represented** in every other table. Unmatched rows: 1,168 `nmatch == 0` (186 typed proton), 320 with no level-1 object (2 typed proton), 95 with unreadable partners (11 typed proton) (`row_unmatched_reasons.csv`).

## 5. Truth proton inventory used with the taxonomy

Signal primary protons (interaction = signal, `process == 0`, one entry per `(event, KE)` after removing 7 duplicate track-id copies of the same particle): **8,132 above 35 MeV against 8,131 in the baseline truth** (`n_p35_prim`: exact in all events except one, where a 35.18 MeV proton with 0.009 readout charge is counted here and not in the baseline) and **6,630 above 50 MeV, exact in all 12,426 events** (`summary.json: truth_proton_accounting`). The production-missing event has no file: it contributes no row and one truth-1p event to the ladder (`event_stage_ladder.csv`).
