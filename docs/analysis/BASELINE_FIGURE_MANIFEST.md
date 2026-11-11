# Baseline figure manifest: the 15 figures that tell the first-look story

Date: 2026-11-11 (Phase 19 consolidation). Existing figures are referenced, not re-plotted; only the two missing ones (rows 1 and 14) were created from committed tables (`scripts/baseline_consolidation.py`, `plots/baseline_consolidation/`). Every figure carries its own provenance line; the characterisation conventions (policy `any`, provisional TPC box, 35 MeV) apply to all of them. The text that goes with each is in `NCDELTA_FROZEN_WIRECELL_BASELINE.md` (section in the last column).

| # | story step | file | what it shows (one line) | phase | text |
|---|---|---|---|---|---|
| 1 | cutflow and loss budget | `plots/baseline_consolidation/fig_cutflow_loss_budget.png` | cumulative efficiency 12,427 -> 1,153 (9.28 %) and the exclusive first-failure fractions per stage | 19 (from Phase 5) | 3 |
| 2 | efficiency by truth topology | `plots/differential_efficiency/decomposition_0p_vs_1p.png` | truth-0p 8.12 % vs truth-1p 10.69 % and where the difference develops (`other` stage) | 6 | 5 |
| 3 | truth -> reco topology migration | `plots/proton_truth_association/migration_1p_to_0p_and_0p_to_1p.png` | reasons for truth 1p -> reco 0p and truth 0p -> reco 1p (final migration matrix: section 2 of the baseline) | 10 | 2 |
| 4 | efficiency vs photon energy | `plots/differential_efficiency/eff_stages_vs_photon_energy_mev.png` | per-stage cumulative efficiency vs true photon energy (2.4 % to about 15 %); the shower stage introduces the dependence | 6 | 5 |
| 5 | efficiency vs photon angle | `plots/differential_efficiency/eff_stages_vs_cos_theta_beam.png` | 3 % to 13 % with forward angle; persists after energy stratification | 6 | 5 |
| 6 | efficiency vs vertex edge / z | `plots/differential_efficiency/eff_groups_vs_vtx_z.png` | flat interior, 4.4 % in the last 50 cm in z, by truth class | 6 | 5 |
| 7 | photon reconstruction taxonomy | `plots/shower_vertex_audit/taxonomy_all_0p_1p.png` | exclusive fate of the signal photon at the shower stage (typed non-electron, fragmented, not in the main-vertex set, track, ...) | 9 | 6 |
| 8 | vertex provenance 0p vs 1p | `plots/vertex_provenance_audit/fig2_vertex_provenance_by_topology.png` | where the photon-line displacement is decided (traditional, raw network, DL, final), by topology | 16 | 7 |
| 9 | proton reconstruction vs KE | `plots/particle_pid_audit/fig2_true_proton_reco_type_vs_ke.png` | reco type of true protons vs KE: low-KE merging, high-KE muon / pion typing | 15 | 8 |
| 10 | numu compactness | `plots/numu_compact_shower_audit/fig1_survival_vs_segments_length.png` | numu survival vs shower segments and length, clean vs non-clean photon objects | 18 | 4 |
| 11 | ncpi0 pair origin | `plots/pi0_pair_fragmentation_audit/fig5_ncpi0_survival_by_pair_origin.png` | ncpi0 survival by the origin of the second pair member | 14 | 4 |
| 12 | Delta mass / common observable | `plots/common_observables/delta_mass_resolution.png` | M_Delta resolution for the truth-matched Delta+ decay pairs (median +2.8 MeV, 68 % [-44, +34]) | 11 | 9 |
| 13 | background composition | `plots/background_mechanisms/background_composition_by_channel.png` | candidate-associated composition of the 635 BNB-CV non-signal events by reco channel | 4 | 10 |
| 14 | signal vs beam-neutrino rate | `plots/baseline_consolidation/fig_signal_vs_background_rates.png` | per-channel selected rates per 1e20 POT, independently (NOT an S/B) | 19 (from Phases 4, 5) | 11 |
| 15 | natural-CV cross-check | `plots/natural_ncdelta/natural_vs_dedicated.png` | natural NC-Delta in the BNB CV against the dedicated official sample | 3 / 5 | 12 |

Optional (not counted): `plots/spine_harmonization/denominator_definition_effect.png` (the efficiency on each harmonised denominator, 9.28 % loose box to 10.93 % harmonised; section 16), `plots/analysis_definition_decisions/fv_comparison.png` (decision D).

Rules used: one figure per story step; no aesthetically redundant versions; the 49 Phase-6 figures, the Phase-8 and Phase-12 attribution figures and the Phase-15 to 18 detail figures stay in their phase directories (see `NCDELTA_BASELINE_TECHNICAL_INDEX.md`).
