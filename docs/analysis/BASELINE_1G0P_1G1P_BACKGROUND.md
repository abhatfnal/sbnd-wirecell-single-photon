# Baseline 1γ0p / 1γ1p background characterisation (BNB CV; background only)

**This is background characterisation only. Neither channel is a signal region.** Everything is computed from the derived analysis table (`ANALYSIS_TABLE_VALIDATION.md`), never from the CAFs, with the frozen baseline chain (no threshold change, no retraining, no fiducial volume, `wc.valid == 1`). Candidate policies stay provisional: `any` (working) and `first` (comparison); no event has two passing candidates, so `any` selects exactly one candidate per selected event. Reco 0p / 1p / ≥2p use the provisional rule (type 2212, KE > 35 MeV, all rows). Reco 0p is called **1γ0p**, reco 1p **1γ1p**; **≥2p is diagnostic only**.

Normalisation: *neutrino-induced rate from the official filtered Gen2 CV sample*, selected events / ΣTotalPOT (2.71940e19 POT of all generated events) × 1e20; Poisson error on the raw count only (no weights, no systematics). **Cosmic-only backgrounds are not represented** (they must come from beam-off, whose scale is unresolved); the numbers are therefore a floor of the total background, not a prediction. No data/MC comparison is made.

Files: `tables/analysis_table/bnb_cv_channel_{summary,composition,variable_quantiles}.csv`, `bnb_cv_channel_diagnostics.json`; plots `plots/analysis_table/bnb_cv_final_{1g0p,1g1p,ge2p_diag,all_proton}.png`.

## 1. Selected events and rates

| policy | channel | selected events | per 1e20 generated POT (neutrino-induced, stat. only) |
|---|---|---|---|
| any | **1γ0p** (reco 0p) | **318** | 1169 ± 66 |
| any | **1γ1p** (reco 1p) | **236** | 868 ± 56 |
| any | diagnostic reco ≥2p | 95 | 349 ± 36 |
| first | 1γ0p | 307 | 1129 ± 64 |
| first | 1γ1p | 226 | 831 ± 55 |
| first | diagnostic ≥2p | 93 | 342 ± 35 |

(`any` totals 649, `first` 626, as in the full-scan cutflow.)

## 2. Truth composition (event-level truth category; precedence in `BNB_TRUTH_CATEGORY_AUDIT.md`)

| category | 1γ0p `any` | frac. | 1γ1p `any` | frac. | ≥2p `any` | 1γ0p `first` | 1γ1p `first` |
|---|---|---|---|---|---|---|---|
| NC_PI0 | 93 | 29.2 % | 63 | 26.7 % | 22 | 93 | 63 |
| NUE_CC | 52 | 16.4 % | 78 | **33.1 %** | 35 | 52 | 78 |
| CC_PI0 | 42 | 13.2 % | 41 | 17.4 % | 18 | 42 | 41 |
| DIRT_NO_ACTIVE | 84 | **26.4 %** | 16 | 6.8 % | 4 | 84 | 16 |
| MULTI_ACTIVE | 14 | 4.4 % | 20 | 8.5 % | 7 | 6 | 11 |
| OTHER_NC | 17 | 5.3 % | 12 | 5.1 % | 4 | 17 | 12 |
| NUMU_CC | 16 | 5.0 % | 6 | 2.5 % | 5 | 13 | 5 |
| total | 318 | | 236 | | 95 | 307 | 226 |

Observations (descriptive, with the small-number caveat of 236–318 events; per-category statistical errors are about √n):

* **NC π⁰ is the largest single category in 1γ0p (29 %) and the second in 1γ1p (27 %)**, as expected for a single-photon search whose dominant physics background is a missed π⁰ photon.
* **ν_e CC is the largest category in 1γ1p (33 %)** and 16 % in 1γ0p. These are the ν_e CC interactions present in the CV sample itself (intrinsic beam ν_e); the dedicated Gen2 nueCC rare-signal sample is not used here and its normalisation (unresolved, `NUECC_CONTROL_SAMPLE.md`) does not enter.
* **Dirt (`DIRT_NO_ACTIVE`: no neutrino vertex in the provisional active-volume box) is 26 % of 1γ0p but 7 % of 1γ1p.** These are events stored through the generator's dirt/energy-deposit path (rock interactions that deposit energy in the TPC) plus any vertex just outside the provisional box (the box is not a fiducial volume). Its contribution to 1γ0p is the reason the SBND FV decision (open) matters most for this channel.
* CC π⁰ is 13–17 % in both channels; ν_μ CC is small (5 % and 2.5 %).
* `MULTI_ACTIVE` (more than one neutrino vertex in the box in the same event) differs between policies (14 vs 6 in 1γ0p): these are the events with several in-window interactions where the candidate policy matters; this is the quantified candidate-policy effect (`CANDIDATE_POLICY_AUDIT.md`), not a physics result.

## 3. BDT-score distributions (selected events; quantiles 5/25/50/75/95 %, `any`)

| score | channel | q05 | q25 | q50 | q75 | q95 |
|---|---|---|---|---|---|---|
| numu | 1γ0p | 0.64 | 0.90 | 0.97 | 0.99 | 1.00 |
| numu | 1γ1p | 0.51 | 0.84 | 0.94 | 0.98 | 1.00 |
| other | 1γ0p | 0.24 | 0.54 | 0.78 | 0.93 | 0.99 |
| other | 1γ1p | 0.32 | 0.63 | 0.84 | 0.95 | 0.99 |
| ncpi0 | 1γ0p | 0.03 | 0.26 | 0.60 | 0.80 | 0.96 |
| ncpi0 | 1γ1p | 0.03 | 0.24 | 0.39 | 0.77 | 0.98 |
| nue | 1γ0p | -1.00 | -1.00 | -0.84 | 0.57 | 0.94 |
| nue | 1γ1p | -1.00 | -1.00 | -0.96 | 0.33 | 0.95 |

The numu and other scores pile up just above their cuts' high side in both channels, the ncpi0 score is broad above its −0.05 cut and the nue score (cut at −1, which removes nothing) is bimodal, close to −1 for most events and high for a minority. The two channels have very similar score distributions. Plots: `bnb_cv_final_{1g0p,1g1p}.png` (cut lines are the frozen thresholds).

## 4. Photon/shower energy, conversion distance, dQ/dx, reco E_ν

| variable | channel | q05 | q25 | q50 | q75 | q95 |
|---|---|---|---|---|---|---|
| main shower energy `shw_sp_energy` [MeV] | 1γ0p | 131 | 290 | 423 | 863 | 2113 |
| | 1γ1p | 77 | 231 | 473 | 1037 | 2243 |
| shower-vertex distance `shw_sp_shw_vtx_dis` [cm] | 1γ0p | 0 | 0 | 0 | 0 | 27 |
| | 1γ1p | 0 | 0 | 0 | 12 | 48 |
| medium dQ/dx `shw_sp_medium_dQ_dx` | 1γ0p | 0.98 | 1.17 | 1.72 | 2.20 | 3.22 |
| | 1γ1p | 0.98 | 1.12 | 1.34 | 2.03 | 2.79 |
| reco E_ν `kine_reco_Enu` [MeV] | 1γ0p | 180 | 365 | 576 | 1091 | 2363 |
| | 1γ1p | 302 | 555 | 862 | 1468 | 2698 |

The reco shower energy is broad (median 0.4–0.5 GeV with a tail beyond 2 GeV) and the 1γ1p sample has a higher reco E_ν (as expected when a proton carries energy). `shw_sp_shw_vtx_dis` is **0 for most selected events (the shower attaches at the vertex)**; the physical meaning/unit of this variable and its use as a "conversion distance" is **not confirmed** (the preselection has 48 % exact zeros and some −1), so no photon conversion-distance conclusion is drawn. dQ/dx variables are drawn with their sentinels (100 for `lowest_dQ_dx`, 6.25e9 for `vec_dQ_dx_0`) excluded, display only; their units are not confirmed either. All shower variables are WCP values, not truth photon energies.

## 5. Vertex distributions and proton diagnostics

* Vertex (`kine_nu_{x,y,z}_corr`): x median +12 / −8 cm (1γ0p / 1γ1p), spanning ≈ ±180 cm (5–95 %); z median ≈ 205–209 cm, spanning ≈ 5–450 cm. No selected event has the `(0,0,0)` default. Against the *provisional* TPC box (|x|,|y| < 200, 0 < z < 500; **not** a fiducial volume): 5 of 318 (1γ0p) and 2 of 236 (1γ1p) selected vertices are outside it. The distributions are broad over the whole active volume; the baseline has no FV, so edge regions are included.
* Reco proton multiplicity (all rows with KE > 35 MeV): by construction 0 in 1γ0p and 1 in 1γ1p; the ≥2p diagnostic sample splits 62 / 24 / 8 / 1 for 2 / 3 / 4 / 5 protons. Leading reco proton KE in 1γ1p: median 152 MeV (q05 69, q95 426); ≥2p: median 182 MeV.
* The truth proton multiplicity of these background events was **not** stored in the table (only the event truth category); a truth-vs-reco proton migration for backgrounds is not part of this stage.

## 6. What this does not say

* It is not a prediction of the total background: cosmic-only backgrounds are absent and the official nueCC / beam-off normalisations are unresolved (`QUESTIONS_FOR_HAIWANG_HANYU.md`).
* It is not a signal-region definition and nothing here was used to tune a threshold or select a variable.
* Candidate policy (`any` vs `first`), the SBND FV, the 35 MeV proton threshold, the leftover-shower proton-row convention and the flash-time offset all remain provisional.
