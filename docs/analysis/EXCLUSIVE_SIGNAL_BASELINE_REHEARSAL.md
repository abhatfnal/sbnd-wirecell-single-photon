# Exclusive NC Δ → Nγ signal: baseline rehearsal on the natural BNB population

**Rehearsal / cross-check only.** The population is the natural NC Δ → Nγ sample inside the production BNB CV; the official Wire-Cell merged signal sample is still pending. Nothing was tuned: frozen BDT scores and cuts, `wc.valid == 1`, candidate policy `any` (comparison `first`), proton threshold 35 MeV, provisional active-TPC truth region (|x|,|y| < 200, 0 < z < 500 cm; **not** a fiducial volume), truth used for evaluation only. Numbers are small (N = 117); intervals are exact 68.3 % Clopper-Pearson. Code: `src/sbnd_single_photon/exclusive_signal.py`; scripts `scripts/exclusive_signal_{characterize,mechanisms,vs_background}.py`; tables `tables/exclusive_signal/natural_bnb_cv/`; plots `plots/exclusive_signal/`; future drop-in: `OFFICIAL_SIGNAL_WC_ARRIVAL_RUNBOOK.md`.

## 1. Purpose
Describe how the *current frozen* production reconstruction and the inherited MicroBooNE selection treat the exclusive truth 0p / 1p / ≥2p signal topologies, with machinery that runs unchanged on the high-statistics official sample. No optimisation or recommendation is made.

## 2. Signal definition
NC neutrino interaction whose GENIE record has a status-1 photon with a Δ⁰ / Δ⁺ mother (`truth_signal.genie_record_ancestry`; no `resnum`, no proxy). Δ charge (Δ⁰ → nγ, Δ⁺ → pγ) and truth proton category are separate axes. Truth category = post-FSI Geant4 primary protons (`rec.mc.nu.prim`, PDG 2212, KE > 35 MeV). An event counts once; with several qualifying neutrinos the in-filter-box one is the signal interaction (`SIGNAL_TRUTH_AND_DENOMINATOR.md` §5). Two views are always separate: **A** the actual selection (reconstruction only: an event passes a stage if any candidate does) and **B** the diagnostic view restricted to the *signal-matched* candidate (dominant-truth-neutrino vertex within 5 cm of the signal vertex; the choice among several matched candidates, used only for diagnostics, is the one with the largest dominant charge). Truth matching never decides whether an event passes.

## 3. Natural BNB signal sample
416 events with a qualifying neutrino in the 500,000-event CV (`NATURAL_NCDELTA_CV_CROSSCHECK.md`); **117** have the signal vertex in the provisional TPC box and are the denominator here (the other 299 are padding/rock; 104 of the 288 rock ones have a candidate and none passes). Δ⁰ 65 / Δ⁺ 52 in the 117.

## 4. Truth 0p / 1p / ≥2p populations (117, TPC box)
| truth | N | fraction | Δ⁰ | Δ⁺ |
|---|---|---|---|---|
| 0p | 59 | 50.4 % | 44 | 15 |
| 1p | 46 | 39.3 % | 14 | 32 |
| ≥2p | 12 | 10.3 % | 7 | 5 |
(Dedicated flatCAF, all 13,773 events: 47.2 % / 44.7 % / 8.1 %; the TPC-box 0p/1p/≥2p composition was found consistent in `NATURAL_NCDELTA_CV_CROSSCHECK.md`, χ² p = 0.43.)

## 5. Reconstruction acceptance
`wc.valid`: 117/117. At least one candidate: 105 (89.7 %); a candidate truth-matched to the signal: 103 (88.0 %), i.e. 12 events have no candidate and 2 have candidates that are all attributed to another neutrino. The fraction with a candidate is 88.1 % / 91.3 % / 91.7 % for truth 0p / 1p / ≥2p.

## 6. Frozen cutflow (events; fraction of the truth denominator in brackets; view A, policy `any`)
| stage | all | truth 0p | truth 1p | truth ≥2p |
|---|---|---|---|---|
| truth denominator | 117 | 59 | 46 | 12 |
| wc.valid | 117 | 59 | 46 | 12 |
| ≥1 candidate | 105 (89.7 %) | 52 (88.1 %) | 42 (91.3 %) | 11 (91.7 %) |
| >0 shower of 20 MeV | 70 (59.8 %) | 36 (61.0 %) | 27 (58.7 %) | 7 (58.3 %) |
| BDT evaluable | 70 | 36 | 27 | 7 |
| numu > 0.4 | 47 (40.2 %) | 18 (30.5 %) | 23 (50.0 %) | 6 (50.0 %) |
| other > 0.2 | 31 (26.5 %) | 9 (15.3 %) | 17 (37.0 %) | 5 (41.7 %) |
| ncpi0 > −0.05 | 13 (11.1 %) | 4 (6.8 %) | 8 (17.4 %) | 1 (8.3 %) |
| nue > −1 | 13 | 4 | 8 | 1 |
| n_20br1 == 1 | 13 | 4 | 8 | 1 |
| **final (`any`)** | **13** | **4** | **8** | **1** |
| final (`first`) | 12 | 4 | 7 | 1 |

View B (signal-matched candidate): identical final 13 / 4 / 8 / 1; it differs only at the early stages (103 matched candidates; 69 with a >20 MeV shower, 46 pass numu). With 13 final events, the 0p/1p difference in the final efficiency (4/59 vs 8/46) has Fisher p = 0.12 and is **not** significant; the numu step is where the truth-0p and truth-1p fractions differ most (30 % vs 50 %); these are descriptive differences of small counts. Full tables with intervals: `cutflow_{A,B}_{any,first}.csv`. Plot: `natural_bnb_cv_cutflow_by_truth.png`.

**Natural-CV baseline efficiency cross-check (NOT a final signal efficiency)**, selected / truth in the provisional TPC box, `any` (68 % exact): total 13/117 = 11.1 % [8.2, 14.8]; 0p 4/59 = 6.8 % [3.6, 11.8]; 1p 8/46 = 17.4 % [11.6, 24.8]; ≥2p 1/12 = 8.3 % [1.4, 25.0]. `first`: 12/117 = 10.3 % [7.4, 13.9]; 0p 4/59; 1p 7/46 = 15.2 % [9.8, 22.5]; ≥2p 1/12. Provisional because of the small number, the truth region, the 35 MeV threshold, the candidate policy and the pending official sample.

## 7. Truth → reco proton migration (raw counts, diagnostic = signal-matched candidate's reco category)
Reco category = `kine_particle_type == 2212` and `kine_energy_particle > 35 MeV` over the inherited row set.

**A. all 117 truth events** (last column: no candidate or none signal-matched)

| | reco 0p | reco 1p | reco ≥2p | none |
|---|---|---|---|---|
| truth 0p | 34 | 15 | 2 | 8 |
| truth 1p | 13 | 23 | 5 | 5 |
| truth ≥2p | 7 | 2 | 2 | 1 |

**B. events with a signal-matched candidate (103):** same without the last column. **C. BDT-evaluable matched candidate (69):** 0p: 25/11/0; 1p: 9/15/2; ≥2p: 5/1/1. **D. final selected (13), analysis-selected candidate:** truth 0p → 4/0/0; truth 1p → 2/6/0; truth ≥2p → 1/0/0 (the matched candidate gives the same matrix; in all 13 the passing candidate *is* the signal-matched one). Row-normalised matrices and the `first` versions: `migration_*_rownorm.csv`. Plot: `natural_bnb_cv_migration.png`.

Mechanisms (`mechanisms_by_migration_cell.csv`, `mechanisms_events.csv`; row-level truth matching, flags are **not** mutually exclusive, no unique cause is forced; `T_truth_track` contains only tracks with charge in the blobs, so a primary proton with no deposited charge is invisible to it; the WC truth-track count of primary protons >35 MeV agrees with the CAF truth category for 99 of the 103 matched events):
* **truth 1p → reco 0p (13 events):** the truth primary proton above threshold (as a Wire-Cell truth track) has *no reco particle row* in 7 events, a row with a *non-proton PID* in 4, and a proton row with *KE below 35 MeV* in 2.
* **truth 0p → reco 1p (15 events):** the reco-proton row is matched to a signal particle with a *different* truth PDG (PID) in 7 events, to a *secondary Geant4 proton* of the signal interaction in 4, to a *primary proton whose truth KE is below 35 MeV* in 3 (truth KE from the Wire-Cell track); a leftover-shower row (`included == 3`) is the proton row in 5; no reco-proton row is unmatched to truth in this cell (flags overlap).
* **truth 1p → reco 1p (23):** the truth primary proton is found as a reco proton in 18, has a row with another PID in 3 and no row in 2 (the reco proton row is a secondary Geant4 proton in 2, another signal particle in 3, a leftover-shower row in 3, so some correct-multiplicity events carry a wrong-origin row).
* **truth ≥2p → reco 0p (7 events):** at least one truth primary proton has no reco row in all 7 and a row with another PID in 4 (12 proton tracks without a row in total); → reco 1p (2) and ≥2p (2) are partial / full recovery.

## 8. 1γ0p results (reco 0p channel)
Selected: 7 of 13 events (`any`; `first` 7): truth 0p 4, truth 1p 2, truth ≥2p 1 (the 0p reco channel contains truth-1p and truth-≥2p events). Δ⁰ 5, Δ⁺ 2. Selected photon energy 311–507 MeV (true), shower energy 317–543 MeV. Event table: `selected_signal_events_any.csv`.

## 9. 1γ1p results (reco 1p channel)
Selected: 6 of 13 (`any`; `first` 5): all truth 1p, all Δ⁺ → pγ, reco leading-proton KE 137–524 MeV, reco E_ν 376–1207 MeV (reco E_ν includes the proton). No reco ≥2p selected. Purity of the dominant-neutrino charge of the selected candidate 0.76–1.00 over all 13. All 13 selected events have a single passing candidate which is the signal-matched one; no event is mixed.

## 10. Δ charge vs proton topology
| Δ → | truth 0p | 1p | ≥2p | total |
|---|---|---|---|---|
| Δ⁰ → nγ (all) | 44 | 14 | 7 | 65 |
| Δ⁺ → pγ (all) | 15 | 32 | 5 | 52 |

| Δ → | reco 0p | reco 1p | reco ≥2p | N | stage |
|---|---|---|---|---|---|
| Δ⁰ → nγ | 38 | 16 | 3 | 57 | signal-matched candidate |
| Δ⁺ → pγ | 16 | 24 | 6 | 46 | signal-matched candidate |
| Δ⁰ → nγ | 5 | 0 | 0 | 5 | final selected (`any`) |
| Δ⁺ → pγ | 2 | 6 | 0 | 8 | final selected (`any`) |

Δ⁰ ≠ reco 0p and Δ⁺ ≠ reco 1p: of the 57 Δ⁰ candidates 16 + 3 are reconstructed with ≥ 1 proton (33 %); of the 46 Δ⁺ candidates 16 are reco 0p (35 %). In the final sample Δ⁺ events appear in the reco-0p channel (2 of 8) and the reco-1p channel holds only Δ⁺. The Δ charge is a diagnostic axis, never a topology label.

## 11. Failure modes (first failure, view A, `any`; mutually exclusive; `first_failure_*` tables, by truth category and by Δ charge)
| first failure | all | 0p | 1p | ≥2p | Δ⁰ | Δ⁺ |
|---|---|---|---|---|---|---|
| wc.invalid | 0 | 0 | 0 | 0 | 0 | 0 |
| no candidate | 12 | 7 | 4 | 1 | 7 | 5 |
| no >20 MeV shower | 35 | 16 | 15 | 4 | 22 | 13 |
| BDT not evaluable | 0 | 0 | 0 | 0 | 0 | 0 |
| fails numu | 23 | 18 | 4 | 1 | 15 | 8 |
| fails other | 16 | 9 | 6 | 1 | 10 | 6 |
| fails ncpi0 | 18 | 5 | 9 | 4 | 6 | 12 |
| fails nue / n_20br1 | 0 | 0 | 0 | 0 | 0 | 0 |
| **selected** | **13** | 4 | 8 | 1 | 5 | 8 |

View B inserts "candidates exist but none signal-matched" (2 events: one 0p, one 1p) before the shower step. "BDT not evaluable" is empty because every candidate with a >20 MeV shower in this sample is evaluable. The largest losses are the absence of a 20 MeV shower (35, 30 %) and the numu cut (23), concentrated in truth 0p. The nue and n_20br1 cuts remove nothing here. Plot: `natural_bnb_cv_first_failure.png`.

**What the frozen selection responds to** (descriptive, `signal_vs_background_*.csv`, BDT-evaluable candidates, signal-matched n = 69 vs non-signal CV n = 50,872; no ranking or optimisation): the numu and other BDT scores are strongly shifted (median 0.90 vs −0.96 and 0.06 vs −0.81; pass fractions of the existing cuts 67 % vs 23 % and 45 % vs 7.6 %; ncpi0 19 % vs 1.8 % cumulatively), the main-shower energy is higher (median 191 vs 82 MeV), reco E_ν lower (452 vs 632 MeV) and the shower attaches closer to the vertex (`shw_min_dis` median 13 cm vs the 1000 sentinel for most background candidates); the ncpi0 and nue scores, number of 20 MeV showers, reco proton multiplicity, leading-proton KE, flash time, vertex coordinates and dQ/dx variables are not distinguishable at this statistics (KS p > 0.09 for all). The inherited selection appears to respond mainly to "a vertex-attached shower of a few hundred MeV with a numu/other-BDT-like profile"; it contains no direct proton information (the reco proton category is a label applied after the selection). Reco category among final events: signal 7 0p / 6 1p / 0 ≥2p; non-signal CV 310 / 230 / 95.

## 12. What is provisional
Truth region (TPC box, not an FV); the 35 MeV threshold on both sides; candidate policy (`any` working, `first` comparison; no event here has two passing candidates); 5 cm signal-match tolerance and the matched-candidate choice (diagnostic); the Wire-Cell truth-track proton mechanisms (charge-in-blobs only; row-level flags ambiguous); the leftover-shower (`included == 3`) row convention; dQ/dx and `shw_vtx_dis` units/meaning (sentinels masked for display only); the sentinel value (1000) of `shw_min_dis`. All statistics are N = 117 (13 selected): the efficiency intervals above are the honest uncertainty.

## 13. What the official high-statistics sample will replace
The natural 117 events become ~12,400 truth events in the TPC box (13,773 in the filter box) with `recTreeWireCell`; the same scripts run on it (`OFFICIAL_SIGNAL_WC_ARRIVAL_RUNBOOK.md`). It supplies the efficiency, the truth → reco migration with sufficient statistics for the 1γ0p/1γ1p mixing, its own exposure (SAM `mc.pot`) for the yield, and replaces — not adds to — the natural signal already inside the inclusive CV (`NCDELTA_BASELINE_ANALYSIS_DESIGN.md`, "Signal/background bookkeeping"). No recommendation about the selection is made here.
