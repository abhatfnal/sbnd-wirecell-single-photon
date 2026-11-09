# Exclusive single-photon backgrounds: candidate-associated mechanisms (BNB CV, frozen baseline)

> **Revalidated against the matcher's design document (see `WIRECELL_TRUTH_MATCH_SEMANTICS.md`, 2026-11-09).** The production top partner of a candidate is the FIRST stored partner (largest *point* IoU), not the largest *charge* IoU that Phase 4 used. Rule change affects 2 of the 649 selected candidates' top partner and exactly **1 category**: (file 32366, run 8060, subrun 80, evt 5) OTHER_NC -> COSMIC_OR_UNMATCHED (1γ1p; both IoUs are tiny: 0.096 for the old top neutrino vs 0.054 point-IoU for a cosmic object). All numbers below are the revalidated ones; the Phase-4 tables are preserved on the pushed Phase-4 branch.

**Characterisation only.** No cut, threshold, BDT, proton threshold (35 MeV), candidate policy (`any`, with `first` unchanged) or fiducial volume was touched, and truth never decided whether a candidate or event passes. The truth is attached *after* selection to the already-passing candidate. Companion documents: `PASSING_CANDIDATE_TRUTH_ASSOCIATION.md`, `CANDIDATE_ASSOCIATED_BACKGROUND_TAXONOMY.md`, `SELECTED_SHOWER_TRUTH_MATCH_AUDIT.md`, `PI0_SINGLE_PHOTON_BACKGROUND_AUDIT.md`, `OUTSIDE_TPC_AND_COSMIC_BACKGROUND_AUDIT.md`, `NUECC_CONTROL_SHAPE_CROSSCHECK.md`. Tables `tables/background_mechanisms/`, plots `plots/background_mechanisms/`, compact derived table (outside Git) `$SP_DATA/background_mechanisms/bnb_cv/background_mechanism_table.parquet` (+ `.metadata.json`).

## 1. Purpose and scope
Why do the 635 non-signal selected BNB CV events pass the inherited single-photon selection, and why do they land in reco 1γ0p versus 1γ1p? The earlier coarse view (event-level category) could not say which interaction in a multi-neutrino event produced the passing candidate; here the **passing candidate** is associated with its truth source. The cosmic-only (beam-off) contribution is **not** represented in any number below, nueCC is not added to the prediction, and rates are the neutrino-induced rate of the official filtered CV (ΣTotalPOT = 2.71940e19), statistical error only.

## 2. Candidate-associated truth definition
Production association `wc.T_match` level 3 (the first-listed, i.e. largest point-IoU, partner of the reconstructed candidate: a truth neutrino or cosmic object; source-defined in `WIRECELL_TRUTH_MATCH_SEMANTICS.md`), no invented threshold, match quality kept; classes: signal-matched, neutrino-matched (exact truth-neutrino and `rec.mc.nu` index), cosmic/unmatched, ambiguous (≥ 2 distinct truth neutrinos). Taxonomy: COSMIC_OR_UNMATCHED → MULTI_OR_AMBIGUOUS → SIGNAL_NCDELTA → OUTSIDE_TPC_NU (provisional box, not an FV) → NC_PI0 / CC_PI0 → NUE_CC → NUMU_CC → OTHER_NC / OTHER_CC. Cross-check: the `T_overlap` dominant-charge neutrino agrees with the `T_match` top neutrino for 646 of 649 passing candidates.

## 3. Accounting of the 635 (exact; validated)
649 selected `any` events = **14 signal-like + 635 non-signal + 0 mixed** (the 14 signal-like are exactly the 14 `T_match` signal candidates). The 635 split **310 / 230 / 95** into reco 1γ0p / 1γ1p / ≥2p diagnostic, computed from the real table (not by subtraction: 318 − 8, 236 − 6, 95 − 0). Every event has exactly one passing candidate; none is dropped; the 23 cosmic/ambiguous ones are in explicit categories. The event-level and candidate-associated categories are the same for 573 of 635; 62 change interpretation (40 old `MULTI_ACTIVE` resolved or kept ambiguous, 22 re-assigned: 11 old DIRT_NO_ACTIVE are cosmic/unmatched).

## 4. 1γ0p composition (310 non-signal events; rate per 1e20 POT, neutrino-induced, stat. only)
| category | n | fraction | rate / 1e20 |
|---|---|---|---|
| NC_PI0 | 102 | 32.9 % | 375 |
| NUE_CC | 53 | 17.1 % | 195 |
| OUTSIDE_TPC_NU | 75 | 24.2 % | 276 |
| CC_PI0 | 43 | 13.9 % | 158 |
| COSMIC_OR_UNMATCHED | 14 | 4.5 % | 51 |
| NUMU_CC / OTHER_NC | 11 / 10 | 3.5 / 3.2 % | 40 / 37 |
| MULTI_OR_AMBIGUOUS | 2 | 0.6 % | 7 |
| **total** | **310** | | **1140 ± 65** |
NC π⁰ is the largest class, then outside-TPC neutrinos (a quarter of the channel), ν_e CC, CC π⁰. Plot `background_composition_by_channel.png`.

## 5. 1γ1p composition (230)
| category | n | fraction | rate / 1e20 |
|---|---|---|---|
| NUE_CC | 86 | 37.4 % | 316 |
| NC_PI0 | 68 | 29.6 % | 250 |
| CC_PI0 | 42 | 18.3 % | 154 |
| OUTSIDE_TPC_NU | 17 | 7.4 % | 63 |
| NUMU_CC / OTHER_NC | 6 / 6 | 2.6 / 2.6 % | 22 / 22 |
| MULTI_OR_AMBIGUOUS | 4 | 1.7 % | 15 |
| COSMIC_OR_UNMATCHED | 1 | 0.4 % | 4 |
| **total** | **230** | | **846 ± 56** |
ν_e CC is the largest class (the primary electron is the selected shower in all 86), then NC π⁰ and CC π⁰.

## 6. ≥2p diagnostic category (95; not a signal region)
NUE_CC 36 (37.9 %), NC_PI0 22 (23.2 %), CC_PI0 21 (22.1 %), NUMU_CC 7, OTHER_NC 4, OUTSIDE_TPC_NU 3, COSMIC 1, MULTI 1; rate 349 ± 36 per 1e20.

## 7. NC π⁰ / CC π⁰ mechanisms (`PI0_SINGLE_PHOTON_BACKGROUND_AUDIT.md`)
The π⁰ decay is traced exactly (`T_truth_pf`). The selected shower is a π⁰ daughter photon in 91–98 % of the cases, mostly the leading one; the decay is very asymmetric (median 0.44–0.62) but the subleading photon is usually above 20 MeV (median 71–98 MeV). The other photon is, in overlapping labels: merged into the selected shower (NC π⁰ 0p 43/102, 1p 17/68), reconstructed in another row (30, 33) or another candidate (28, 13), a non-shower/PID failure (16, 21), exiting or without charge/row (12/10/10 and 12/10/10) or below 20 MeV (15, 8). **No single mechanism dominates**, and the photon-side labels are similar in the 0p and 1p channels; what differs is the proton content: NC π⁰ 1γ0p is truth-0p in 68 of 102, 1γ1p truth-1p in 50 of 68.

## 8. ν_e CC mechanisms (175 NUE_CC)
In **all 175** the selected shower is the Geant4-primary electron/positron of the CC interaction (ancestor = the lepton; 53 / 86 / 36 per channel), at a median dominant-charge fraction of 0.90–0.93: no photon, hadron or cosmic origin. So the ν_e CC background is the genuine lepton shower, not a photon-like mis-ID, and no discriminator was studied. Descriptive differences between its 1γ0p (53) and 1γ1p (86) members: main-shower energy median 1186 vs 920 MeV, reco E_ν 1375 vs 1093 MeV, BDT numu 0.96 vs 0.91, other 0.84 vs 0.84, ncpi0 0.77 vs 0.69, nue ≈ −1 in both, `shw_vtx_dis` 0 in both, `shw_min_dis` 4.4 vs 5.0 cm, medium dQ/dx 1.50 vs 1.21, highest 1.56 vs 1.61, lowest 0.78 vs 0.82 (`variable_quantiles_by_class_channel.csv`); 1γ1p has leading-proton KE median 157 MeV (IQR 106–212). Truth protons: 1γ0p 25 / 23 / 5 (0p / 1p / ≥2p), 1γ1p 1 / 68 / 17.

## 9. Outside-TPC / cosmic mechanisms (`OUTSIDE_TPC_AND_COSMIC_BACKGROUND_AUDIT.md`)
95 passing candidates are matched to neutrinos with the vertex outside the provisional box (75 in 1γ0p): median distance 15 cm from the box (54 within 20 cm; 48 upstream z < 0), all deposit energy in the active volume, ν_μ 84 / ν_e 10, CC 48 / NC 47, the shower is a photon in 84; 15 candidates are cosmic/unmatched (12 with a dominant cosmic muon, 2 cosmic π⁰ photons, 1 e⁺; 14 in 1γ0p) and 7 are ambiguous. The earlier "dirt/no-active" 104-event group is 91 outside-TPC neutrinos + 11 cosmic/unmatched + 1 ambiguous + 1 signal. They are not called dirt: the truth only says "outside the box".

## 10. Truth → reco proton migration by background class (`proton_migration_*.csv`, `proton_migration_mechanisms.csv`)
In-TPC-neutrino candidates with a truth proton category (n = 517: NC_PI0, CC_PI0, NUE_CC, NUMU_CC, OTHER_NC; truth 0p/1p/≥2p primary protons above 35 MeV from `rec.mc.nu.prim`; reco = `T_kine` type 2212 and KE > 35 MeV):

| | reco 0p | reco 1p | reco ≥2p |
|---|---|---|---|
| truth 0p (137) | 121 | 14 | 2 |
| truth 1p (267) | 80 | 156 | 31 |
| truth ≥2p (113) | 18 | 38 | 57 |

(Per-class matrices: `proton_migration_<class>.csv`; e.g. for the 55 outside-TPC candidates with a truth 1p, 44 are reco 0p.) **Answer to "physics topology or migration?": both, but topology is the larger part.** Reco 1γ0p backgrounds of this set (219): truth 0p 121 (55 %), 1p 80 (37 %), ≥2p 18 (8 %); reco 1γ1p (208): truth 0p 14 (7 %), 1p 156 (75 %), ≥2p 38 (18 %). The channels differ mainly because NC π⁰/CC π⁰/ν_e CC interactions with 0 vs 1 true proton land in 0p vs 1p, and a substantial **1p → 0p migration (80 events = 37 % of the 1γ0p backgrounds)** moves true-1p events into 1γ0p, while the converse 0p → 1p migration is small (14 events, 7 % of 1γ1p). Mechanisms (overlapping): **truth 1p → reco 0p (80)**: the truth primary proton is matched to a reco row of the same candidate whose PID is not a proton in 69 (row labelled electron/shower 41, muon 20, charged pion 8), has no reco row in 4 (and in 39 of the 44 outside-TPC cases, i.e. the proton never produced charge inside the TPC), a reco-proton row below 35 MeV in 1, and is found only in another candidate in 6. **Truth 0p → reco 1p (14)**: the reco proton row is a secondary Geant4 proton of the same interaction in 8, another particle of the same interaction (non-proton truth) in 5, a leftover-shower (`included == 3`) row in 7, a primary proton whose truth KE is below 35 MeV in 1; unmatched/other-neutrino origin in none. Per class: NC π⁰ 28 (1p→0p: 24 PID, 2 no row, 2 other candidate) and 8 (0p→1p); CC π⁰ 20 (15 PID, 1 no row, 4 other candidate) and 4; ν_e CC 23 (23 PID) and 1; ν_μ CC 5 (5 PID); OTHER_NC 4 and 1.

## 11. How the frozen cuts act on each class (all 241,845 candidates; `cutflow_by_class_all_candidates*.csv`, `cutflow_by_class.png`)
Class of every candidate from the dominant-charge truth neutrino (`T_overlap`) because the production `T_match` was only run for the passing candidates and a 2,397-file subset (98.0 % category agreement on its 15,409 candidates); the final counts by this association (CC_PI0 106, NC_PI0 192, NUE_CC 179, other ν 47, OUTSIDE_TPC_NU 96, COSMIC 15, signal 14; total 649) differ from the `T_match` ones by a few candidates. Candidates → >20 MeV shower → BDT-evaluable → numu → other → ncpi0 → nue → n_20br1 → final:

| class | candidates | >20 MeV shower | evaluable | numu | other | ncpi0 | nue | n_20br1 | final | final / candidates |
|---|---|---|---|---|---|---|---|---|---|---|
| NC_PI0 | 9,988 | 8,007 | 7,971 | 4,041 | 2,059 | 277 | 277 | 192 | 192 | 1.9 % |
| CC_PI0 | 16,456 | 13,521 | 13,392 | 1,228 | 700 | 173 | 173 | 106 | 106 | 0.64 % |
| NUE_CC | 1,030 | 854 | 841 | 452 | 303 | 238 | 238 | 179 | 179 | 17.4 % |
| other ν (ν_μ CC, other NC/CC) | 168,501 | 21,042 | 19,846 | 1,389 | 207 | 59 | 59 | 47 | 47 | 0.028 % |
| OUTSIDE_TPC_NU | 31,108 | 6,343 | 6,144 | 3,471 | 549 | 155 | 155 | 96 | 96 | 0.31 % |
| COSMIC_OR_UNMATCHED | 14,631 | 3,077 | 2,693 | 1,309 | 72 | 21 | 21 | 15 | 15 | 0.10 % |
| signal NC Δ→Nγ (reference) | 131 | 82 | 82 | 55 | 36 | 14 | 14 | 14 | 14 | 10.7 % |

Descriptively: the ≥ 1 shower above 20 MeV requirement removes most ν_μ-CC/other-ν candidates (13 % survive) and cosmics (21 %) but few π⁰ or ν_e candidates (80–83 %); the numu cut removes ~49 % of the BDT-evaluable NC π⁰, ~91 % of CC π⁰ (the CC muon is recognised) and 44–51 % of the outside-TPC and cosmic candidates; the ncpi0 cut removes 87 % of the NC π⁰ candidates that reach it (277 of 2,059); the nue step removes nothing and n_20br1 removes 20–39 % of the candidates that reach it (none of the 14 signal ones). The split by the candidate's own reco proton category (1γ0p/1γ1p/≥2p) is in the CSV (e.g. NC π⁰ 5,090 / 3,560 / 1,338 candidates → 102 / 68 / 22 final). This is characterisation of the inherited cuts; no rejection is read as a reason to retune.

## 12. nueCC control-sample shape check (`NUECC_CONTROL_SHAPE_CROSSCHECK.md`)
Unit-area shapes only, no POT, no rate. The nueCC control candidates match the intrinsic ν_e CC candidates of the CV for the four BDT scores, shower energy, reco E_ν, proton multiplicity and leading-proton KE, vertex and the shower variables (KS D ≤ 0.044 for 1,023 vs 78,061 BDT-evaluable candidates, D ≤ 0.095 for 183 vs 15,813 selected). It is a usable *shape* surrogate; its normalisation remains unresolved and it was not added to the CV.

## 12b. Optional data shape check (done; raw counts and shapes only)
`scripts/data_shape_sanity.py` from the existing scans (no MC, no scaling, no normalisation, flash time not used): open beam-on has 77 selected events (reco 0p/1p/≥2p = 39 / 27 / 11) in 89,946 events, beam-off 6 (4 / 2 / 0) in 49,970 events; unit-area shapes of BDT-evaluable candidates differ between the two (KS D = 0.24 numu, 0.24 other, 0.18 ncpi0, 0.05 nue, 0.34 reco-proton count; vertex y 0.24), as expected when beam-on contains beam-neutrino candidates and beam-off does not; the beam-off statistics (821 evaluable candidates, 6 selected) are small. No data/MC conclusion is drawn (`data_shape_sanity.json`, `beam_on_vs_off_shapes.png`).

## 13. Unresolved limitations
* The meaning of the `T_match` levels/flags is inferred from the stored data (to be confirmed with the Wire-Cell authors); the cutflow by class for all candidates uses `T_overlap`.
* The truth categories are for the matched interaction; the selected shower can still be a merged object (dominant-charge fraction down to 0.22); photons without charge in blobs are invisible to the overlap labels.
* The provisional TPC box (not an FV), the 35 MeV threshold on both sides, candidate policy `any` (no event here has two passing candidates), the `included == 3` leftover-shower row convention, and the truth-proton definition (post-FSI primaries) are provisional. 8 π⁰ candidates have no opening angle (inconsistent/missing second photon energy); 3 passing candidates have no energy-matching shower row.
* Statistics: 635 non-signal events (≤ 100 per cell); intervals are Poisson on raw counts; no weights, no systematics; **no cosmic-only (beam-off) component**, unresolved beam-off normalisation and unresolved nueCC normalisation.

## 14. What this means for the eventual signal + background prediction (descriptive)
* The selected backgrounds are dominated by three physical sources: π⁰ (NC and CC: 298 of 635, 47 %), ν_e CC (175, 28 %, always the genuine primary electron shower) and neutrinos interacting just outside the provisional box (95, 15 %, concentrated in 1γ0p); cosmic-matched candidates are 15 (2.4 %).
* 1γ0p and 1γ1p differ in composition (outside-TPC neutrinos and NC π⁰ vs ν_e CC) and in proton topology; true-1p events entering 1γ0p through proton mis-identification is a material migration (37 % of the in-TPC 1γ0p backgrounds), while the reverse is small.
* The prediction can therefore be organised by these classes: signal from the dedicated NC-Δ sample (replacing the 14 natural signal-like events in the CV), beam background from the inclusive CV's selected non-signal events (635), cosmic-only from beam-off once its scale is approved; the nueCC control sample is available as a shape surrogate only.
* No optimisation or retuning is implied by any number here.
