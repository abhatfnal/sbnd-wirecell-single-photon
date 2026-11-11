# Fiducial-volume decision audit (decision D): source-supported conventions, application semantics, common-phase-space effect and edge stability

Date: 2026-11-11. Branch `analysis/ncdelta-analysis-definition-decisions-20261111`. **Decision support only**: the frozen baseline (no FV) is unchanged, no FV is chosen here by signal performance, and no final S/B, purity or significance is produced (the cosmic-only background is blocked on the collaboration-approved beam-off normalisation). Code: `src/sbnd_single_photon/analysis_definitions.py` (`FV_SPECS`, `fv_mask`), `scripts/analysis_definition_decisions.py`; tables `tables/analysis_definition_decisions/`, figures `plots/analysis_definition_decisions/`. Builds on `SBND_FIDUCIAL_VOLUME_AUDIT.md` (read-only search of CVMFS and analysis checkouts), `SPINE_SIGNAL_DEFINITION_SOURCE_AUDIT.md`, Phases 6, 9 and 11.

## 1. What the sources establish
**There is no single authoritative SBND fiducial volume.** Every definition found belongs to a specific analysis and they conflict (the 18 entries of `SBND_FIDUCIAL_VOLUME_AUDIT.md`: x,y edges 175-195 cm, z lower 5-30 cm, z upper 450 / 490 / 495 cm, x with or without a cathode exclusion, some with a high-y carve-out at z > 250 cm). None was designed for the Wire-Cell `kine_nu_*_corr` vertex. No Prabhjot, Matteo or collaboration-approved NC-Delta FV is present in this repository or in the accessible sources; nothing is invented as a "standard SBND FV". The conventions that are evaluated below are the **source-supported** ones:

| key | boundaries | source | truth vs reco | containment | purpose |
|---|---|---|---|---|---|
| `none` | no cut | frozen baseline (`configs/baseline_selection.yaml`: `fiducial_volume.applied: false`) | - | none | reference |
| `av200` | \|x\|,\|y\| < 200, 0 < z < 500 | sbnana `VolumeDefinitions.h` `avnd` (#1); the provisional box of this project (taxonomy box, `truth.ActiveVolume`) | both (here truth and reco) | none | active volume, not an analysis FV |
| `cafpyana190` | \|x\|,\|y\| < 190, 10 < z < 450 | mharriso/cafpyana `makedf/util.py` `InFV(det="SBND")` (#5; used by nueCC and cc2p helpers) | reco or true vertex of other reconstructions | separate `InFV_trk` containment 190/10/490 for tracks (#8) | nueCC, cc2p |
| `numu2021` | x in (-189.15, 189.15), \|y\| < 190, 10 < z < 450 | `NumuCutsSBND202106.cxx` `kInFV` (#4) | reco (numuCC 2021) | track-end containment 190/190/10-490 (#3) | numuCC |
| `spine180` | \|x\|,\|y\| <= 180, 10 <= z <= 450 (inclusive) | Seokju's SPINE NC-Delta truth FV (`SPINE_SIGNAL_DEFINITION_SOURCE_AUDIT.md`) | **truth vertex** | all final-state endpoints contained with a 5 cm margin; `neutrino2026_veto`; the production reco FV is SPINE's `FiducialProcessor` with its own margins | NC-Delta signal definition |
| `legacy_nue175` | 1.5 < \|x\| < 175, \|y\| < 175, 30 < z < 450 | sbnana `fvndAbs` (#2), 2020 | reco | none | legacy nue (predates the geometry) |
| `cohpi_carve` | 10 < \|x\| < 190, 10 < z < 450; \|y\| < 190 for z < 250, -190 < y < 100 for z > 250 | `make_cohpidf_v2.py` (#9); the same high-y carve-out in gump (#10) | reco | none | coherent pi |

Not used: the MicroBooNE x-FV (`reco_nuvtxX` 5-250 cm) is **not** an SBND cut; the SPINE `is_fiducial` margins of #13 rest on a code comment only; the ICARUS default of `InFV` (#5/#7) must not be reused blindly. Boundaries in `spine180` are inclusive, the others strict.

## 2. Application semantics (decision, applied identically below)
* **Signal efficiency denominator**: true NC-Delta vertex inside the truth FV (12,427 events for `av200`, the whole sample for `none`).
* **Signal numerator**: event in the truth denominator AND the frozen selection passes AND the reconstructed vertex (`kine_nu_*_corr`) of the **selected candidate** is inside the reco FV (same boundaries). Events whose true vertex is outside but whose reco vertex is inside are **not** counted as signal (`sel_any_reco_in_fv_truth_outside`: 0 for `av200`, 27-46 for the tighter volumes: the migration into the FV).
* **Background**: frozen-selected BNB-CV non-signal event AND the reconstructed vertex of its selected candidate inside the **same** reco FV. The truth FV is **never** imposed on the background (the BNB-CV objects keep their own truth category, `OUTSIDE_TPC_NU` included).
* **Data** (later): selected candidate satisfying the same reco FV. This yields a common reconstructed phase space for signal, background and data; it repairs the earlier mismatch between a truth-region signal denominator and an unrestricted background, **but not the missing cosmic component**.
* `first` uses the vertex of candidate 0, `any` the vertex of the single passing candidate.

## 3. Comparison (official signal, BNB-CV selected objects; policy any / first; P1 proton convention for the reco channels)

| FV | truth denominator | selected (any) | efficiency (any) | selected (first) | efficiency (first) | eff truth 0p / 1p / >=2p (any) | eff Delta0 / Delta+ (any) | reco 1g0p / 1g1p / >=2p (any) |
|---|---|---|---|---|---|---|---|---|
| `none` | 12,427 | 1,153 | 9.28 % | 1,101 | 8.86 % | 8.12 / 10.69 / 8.24 % | 7.61 / 11.32 % | 527 / 556 / 70 |
| `av200` | 12,427 | 1,153 | 9.28 % | 1,101 | 8.86 % | 8.12 / 10.69 / 8.24 % | 7.61 / 11.32 % | 527 / 556 / 70 |
| `cafpyana190` | 10,087 | 1,020 | 10.11 % | 970 | 9.62 % | 8.80 / 11.75 / 8.78 % | 8.27 / 12.37 % | 459 / 499 / 62 |
| `numu2021` | 10,048 | 1,020 | 10.15 % | 970 | 9.65 % | 8.84 / 11.78 / 8.83 % | 8.30 / 12.43 % | 459 / 499 / 62 |
| `spine180` | 9,206 | 961 | 10.44 % | 914 | 9.93 % | 9.15 / 12.03 / 9.17 % | 8.58 / 12.74 % | 436 / 467 / 58 |
| `legacy_nue175` | 8,272 | 874 | 10.57 % | 835 | 10.09 % | 9.24 / 12.28 / 8.84 % | 8.67 / 12.93 % | 396 / 429 / 49 |
| `cohpi_carve` | 8,486 | 842 | 9.92 % | 804 | 9.47 % | 8.57 / 11.55 / 8.74 % | 8.12 / 12.13 % | 364 / 421 / 57 |

Background (selected non-signal BNB-CV events, 635 before any FV; the 14 natural signal-like events are not background):

| FV | non-signal BNB selected (any) | reco 0p / 1p / >=2p | NC_PI0 | CC_PI0 | NUE_CC | NUMU_CC | OUTSIDE_TPC_NU | COSMIC_OR_UNMATCHED | other | first: total | natural signal-like in FV |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `none` | 635 | 310 / 230 / 95 | 192 | 106 | 175 | 24 | 95 | 16 | 27 | 613 | 14 |
| `av200` | 628 | 305 / 228 / 95 | 191 | 106 | 175 | 24 | 89 | 16 | 27 | 607 | 14 |
| `cafpyana190` | 485 | 221 / 191 / 73 | 158 | 81 | 160 | 23 | 28 | 13 | 22 | 465 | 12 |
| `numu2021` | 484 | 220 / 191 / 73 | 158 | 81 | 160 | 23 | 27 | 13 | 22 | 464 | 12 |
| `spine180` | 448 | 202 / 177 / 69 | 149 | 73 | 147 | 22 | 23 | 13 | 21 | 429 | 12 |
| `legacy_nue175` | 394 | 175 / 153 / 66 | 139 | 66 | 128 | 19 | 11 | 12 | 19 | 377 | 12 |
| `cohpi_carve` | 401 | 180 / 159 / 62 | 129 | 65 | 132 | 22 | 26 | 9 | 18 | 384 | 12 |

Rates per 1e20 POT (signal: dedicated-sample exposure 2.8385e21 POT; beam-neutrino background: BNB-CV exposure 2.7194e19 POT; statistical only): 

| FV | S truth rate (per 1e20 POT) | S selected rate (any) | B_beam total rate (any) | B_beam reco 0p / 1p |
|---|---|---|---|---|
| `none` | 437.8 | 40.6 | 2335 | 1140 / 846 |
| `av200` | 437.8 | 40.6 | 2309 | 1122 / 838 |
| `cafpyana190` | 355.4 | 35.9 | 1783 | 813 / 702 |
| `numu2021` | 354.0 | 35.9 | 1780 | 809 / 702 |
| `spine180` | 324.3 | 33.9 | 1647 | 743 / 651 |
| `legacy_nue175` | 291.4 | 30.8 | 1449 | 644 / 563 |
| `cohpi_carve` | 299.0 | 29.7 | 1475 | 662 / 585 |

**These are signal and beam-neutrino-background rates, not an analysis S/B**: the cosmic-only component, flux and cross-section systematics are absent. The signal / beam-neutrino-background *reference* ratio is 0.016 (reco 1g0p) and 0.023 (reco 1g1p) with no FV and 0.020-0.022 / 0.025-0.027 for the 175-190 cm volumes; **the OUTSIDE_TPC_NU background falls from 95 to 11-28 events and is the main category the FV removes** (and the reason the ratio improves), the pi0 and nueCC categories fall in proportion to the signal. The efficiency of every FV is higher than the no-FV one because the denominator also shrinks (the edge region has lower efficiency, section 4).

## 4. Edge stability (`edge_stability_by_distance_to_face.csv`, `selected_signal_density_vs_xyz.csv`, `fv_edge_stability.png`)

| distance of the true vertex to the nearest face of the 200/200/0-500 box [cm] | truth events | candidate formed | > 20 MeV shower given candidate | final efficiency | median |V_reco - V_true| [cm] | photon leaves the volume |
|---|---|---|---|---|---|---|
| [<0, 5.0) | 733 | 63.7 % | 65.5 % | 5.5 % | 14.7 | 30.3 % |
| [5.0, 10.0) | 735 | 78.1 % | 58.7 % | 5.4 % | 13.0 | 22.4 % |
| [10.0, 20.0) | 1,343 | 83.8 % | 63.9 % | 5.8 % | 14.4 | 12.2 % |
| [20.0, 30.0) | 1,309 | 89.7 % | 64.8 % | 7.9 % | 15.7 | 5.5 % |
| [30.0, 50.0) | 2,274 | 93.8 % | 72.5 % | 8.9 % | 17.3 | 2.2 % |
| [50.0, 100.0) | 3,883 | 96.6 % | 74.3 % | 10.8 % | 18.2 | 0.6 % |
| [100.0, inf) | 2,149 | 98.0 % | 77.1 % | 12.5 % | 19.0 | 0.0 % |

* **No sharp knee.** The candidate-formation fraction rises from 64 % (< 5 cm from a face) to 98 % beyond 100 cm, the shower-stage pass fraction from 66 % to 77 %, and the final efficiency from 5.5 % to 12.5 %: the edge effects are **gradual and extend over 50-100 cm**; the median vertex offset is 13-19 cm at every distance (it is a topology property, Phase 9) and slightly larger in the centre. **The photon leaves the volume in 30 % of the events within 5 cm of a face, 12 % at 10-20 cm, 2 % at 30-50 cm and < 1 % beyond 50 cm**: the left-volume loss is confined to the outer ~30 cm.
* **Along each axis** the efficiency is flat inside the volume and falls at the edges: z: 8.6-11.6 % for z < 450 cm and **4.4 % in 450-500 cm** (candidate fraction 71 %); x: 6.0 % at 160-200 cm and 8.5 % at -200 to -160 cm; y: **5.4 % and 6.1 % at the lower edge, 5.3 % and 8.5 % at the upper edge (|y| > 120 cm already lower: 6-9 %)**. So `spine180` and the 190 cm volumes remove only the outermost 10-20 cm, **a region where the efficiency has already started to fall in y and x**: none of the volumes is "safely away" from every region of changing reconstruction, but none sits inside a region where it changes abruptly either; the z < 450 cut removes the last (worst) 50 cm bin.
* No boundary was tuned bin by bin.

## 5. SPINE comparability of each volume
| FV | equals the SPINE truth FV? | can SPINE apply an equivalent reco FV? | truth containment compatible? | same-event comparison |
|---|---|---|---|---|
| `spine180` | **yes** (truth vertex: 9,206 of 12,427 events inside; the full Phase-7 SPINE-like signal additionally needs containment and the veto: 8,668 events) | TO CONFIRM (SPINE `is_fiducial` with the `FiducialProcessor` margins, unaudited) | the SPINE truth definition adds endpoint containment (5 cm); Wire-Cell has no equivalent truth flag besides the Phase-7 harmonization | straightforward on the truth side, reco FV to be matched |
| `cafpyana190`, `numu2021` | no (10 cm margin instead of 20 in x,y) | TO CONFIRM | not defined | comparable after applying the same box to both reco vertices |
| `av200`, `legacy_nue175`, `cohpi_carve` | no | TO CONFIRM | no | `av200` is the loose reference |
Choosing the SPINE volume merely because it eases the comparison is not a criterion here; it is one consideration (`ANALYSIS_DEFINITION_DECISION_MATRIX.md`).

## 6. What is established and what is not
Established: the list of source-supported conventions and their semantics; the common-phase-space application rule; the signal/background effect of each volume (tables above); the absence of a sharp edge and the extent of the edge regions (30 cm for the photon leaving the volume, 50-100 cm for candidate formation). **Not established:** which convention the analysis group wants; whether it is applied to the SCE-corrected `kine_nu_*_corr` vertex or the raw one; whether the high-y / z > 250 carve-out is wanted; whether a cathode (x ~ 0) exclusion is wanted; the cosmic-only background shape inside each volume (beam-off is selected 4 / 2 / 0 events in the open data, absolute scale blocked).
