# Decision support for the proton policy (E) and the candidate policy (F), common-volume rates and the policy envelope

Date: 2026-11-11. Branch `analysis/ncdelta-analysis-definition-decisions-20261111`. **Decision support, not optimisation**: the frozen photon selection (1,153 events, `any`) and `configs/baseline_selection.yaml` are unchanged in every row; signal-performance differences are **support only** and no option is chosen because it gives a higher efficiency or purity. No final S/B, purity or significance is produced (cosmic-only background blocked, `ANALYSIS_READINESS_BLOCKERS.md`). Fiducial volume: `FIDUCIAL_VOLUME_DECISION_AUDIT.md`. Matrix and provisional conventions: `ANALYSIS_DEFINITION_DECISION_MATRIX.md`. Package definitions: `configs/analysis_definition_candidates.yaml`. Code: `scripts/analysis_definition_decisions.py`, `src/sbnd_single_photon/analysis_definitions.py`; tables `tables/analysis_definition_decisions/`.

# Part B: proton policy

## 1. Options
P1: reco KE > 35 MeV, current `included` convention (the frozen baseline); P2: > 35 MeV excluding `kine_energy_included == 3`; P3: > 50 MeV, current convention; P4: > 50 MeV excluding `included == 3`. **Truth categories use the matching 35 or 50 MeV post-FSI primary-proton threshold** (never mixed: P1/P2 against 35, P3/P4 against 50).

## 2. What `kine_energy_included == 3` means (SOURCE; `RECO_PROTON_ROW_SEMANTICS.md`, `NeutrinoKinematics.cxx`, `NeutrinoShowerClustering.cxx` at fg1 `4b6853d4`)
* **It is neither energy accounting nor a track-ownership flag**: the rows with `included != 1` ARE inside `kine_reco_Enu` (the sum is unconditional; the source itself records `kine_energy_flagged` "inside Enu" to prevent confusion). The name is a misnomer.
* **It encodes the connection type of a leftover shower**: only rows of pool 2 ("remaining showers not yet attached to the traversal") can carry it, with `included = (vtx_type != 3 ? 1 : 3)`: value 3 = the shower's start vertex has **connection type 3** = a shower of a **different cluster than the candidate's main cluster, anchored to the nearest vertex within 80 cm** (> 80 cm is type 4, dropped unless a knob keeps it). MEASURED: all 43,168 such rows are pool-2 showers, 99.7 % in a cluster other than the main one.
* **Is treating such a row as an independent reconstructed proton physically natural from the production semantics? No, not as a vertex-attached track.** These objects are not on the traversal from the main vertex (that is what pools 0 and 1 are: segments attached to the main vertex and its breadth-first tracks); they are *satellite showers* of other clusters that the kinematics tree sums into the neutrino energy; their "proton" type is the start-segment PID of a shower object, not a track-fitted proton. The tagger's own proton bookkeeping (`shw_sp_num_protons`, `shw_sp_proton_*`) counts protons **attached at the main vertex**. This answer follows from the production semantics alone; it is **not** derived from the signal purity (the Phase-10 composition of these rows is reported only as information: 58 % true signal primaries, 30 % Geant4 secondaries). The production authors' intent is not documented (question to Haiwang / Hanyu).

## 3. Comparison (final-selected official signal, policy any)

| policy | reco 1g0p | 1g1p | >=2p | 1g1p truth 0p / 1p / >=2p | 1g0p truth 0p / 1p / >=2p | reco proton rows (final) true primary | M usable | both truth-correct | M mode / median / half68 [MeV] |
|---|---|---|---|---|---|---|---|---|---|
| **P1** (35 MeV, incl. `included == 3`) | 527 | 556 | 70 | 50 / 471 / 35 | 425 / 93 / 9 | 84.1 % of 719 | 554 | 88.6 % | 1225 / 1221 / 90 |
| **P2** (35 MeV, excl. `included == 3`) | 592 | 505 | 56 | 24 / 453 / 28 | 452 / 122 / 18 | 87.9 % of 637 | 503 | 91.1 % | 1225 / 1213 / 85 |
| **P3** (50 MeV, incl. `included == 3`) | 545 | 540 | 68 | 64 / 458 / 18 | 462 / 82 / 1 | 84.1 % of 697 | 538 | 88.7 % | 1225 / 1218 / 89 |
| **P4** (50 MeV, excl. `included == 3`) | 603 | 495 | 55 | 36 / 442 / 17 | 491 / 108 / 4 | 87.6 % of 623 | 493 | 90.9 % | 1225 / 1213 / 85 |

Truth to reco migration (final selected):

**P1** (truth rows, reco columns 1g0p / 1g1p / >=2p): truth 0p: 425 / 50 / 1; truth 1p: 93 / 471 / 30; truth >=2p: 9 / 35 / 39

**P2** (truth rows, reco columns 1g0p / 1g1p / >=2p): truth 0p: 452 / 24 / 0; truth 1p: 122 / 453 / 19; truth >=2p: 18 / 28 / 37

**P3** (truth rows, reco columns 1g0p / 1g1p / >=2p): truth 0p: 462 / 64 / 1; truth 1p: 82 / 458 / 30; truth >=2p: 1 / 18 / 37

**P4** (truth rows, reco columns 1g0p / 1g1p / >=2p): truth 0p: 491 / 36 / 0; truth 1p: 108 / 442 / 20; truth >=2p: 4 / 17 / 35

Truth 1p -> reco 0p, exact accounting of the reco-0p events:

| reason | P1 | P2 | P3 | P4 |
|---|---|---|---|---|
| matched row nonproton type | 37 (40 %) | 37 (30 %) | 33 (40 %) | 33 (31 %) |
| proton in other candidate | 1 (1 %) | 1 (1 %) | 1 (1 %) | 1 (1 %) |
| proton never a row  charge deposited | 27 (29 %) | 27 (22 %) | 25 (30 %) | 25 (23 %) |
| proton never a row  no readout charge | 4 (4 %) | 4 (3 %) | 3 (4 %) | 3 (3 %) |
| proton only subdominant partner | 15 (16 %) | 18 (15 %) | 13 (16 %) | 17 (16 %) |
| proton row excluded by included3 policy | 0 (0 %) | 26 (21 %) | 0 (0 %) | 22 (20 %) |
| proton row reco KE below threshold | 9 (10 %) | 9 (7 %) | 7 (9 %) | 7 (6 %) |
| **total** | 93 | 122 | 82 | 108 |

Truth 0p -> reco 1p, origin of the reco proton row:

| reason | P1 | P2 | P3 | P4 |
|---|---|---|---|---|
| geant4 secondary proton | 26 (52 %) | 6 (25 %) | 24 (38 %) | 6 (17 %) |
| other neutrino proton | 1 (2 %) | 1 (4 %) | 1 (2 %) | 1 (3 %) |
| signal nonproton misidentified | 11 (22 %) | 11 (46 %) | 12 (19 %) | 12 (33 %) |
| true primary proton below truth threshold promoted by reco | 11 (22 %) | 6 (25 %) | 26 (41 %) | 17 (47 %) |
| unmatched | 1 (2 %) | 0 (0 %) | 1 (2 %) | 0 (0 %) |
| **total** | 50 | 24 | 64 | 36 |

Reco proton rows (final selected): the true-primary share is 84.1 % (P1), 87.9 % (P2), 84.1 % (P3), 87.6 % (P4); Geant4 secondaries 9.6 / 6.1 / 9.5 / 6.3 %; non-proton signal objects 3.8-3.9 %. Selected non-signal BNB-CV events by reco category:

| policy | selected non-signal BNB-CV: reco 1g0p / 1g1p / >=2p |
|---|---|
| P1 | 310 / 230 / 95 |
| P2 | 339 / 212 / 84 |
| P3 | 317 / 228 / 90 |
| P4 | 345 / 209 / 81 |

No threshold was optimised: the table is the full comparison. **The 35 -> 50 MeV change is small** (P1 -> P3: 20 of the 1,153 events change reco category, 18 of them from 1g1p to 1g0p; the M_Delta mode is 1225 MeV in all four), **the `included == 3` treatment is larger** (P1 -> P2: 63 events leave reco 1g1p for 1g0p, the truth-0p content of reco 1g1p halves from 50 to 24, the truth-1p fraction of reco 1g1p rises from 84.7 % to 89.7 %, and 26 truth-1p events become reco 0p only because their reco proton is an `included == 3` row).

## 4. Threshold robustness (not an optimisation)
| band [MeV] | true signal primary protons | events with one (of 12,427) | selected events with a reco proton row in the band (of 1,153) |
|---|---|---|---|
| 25-35 | 1,554 (11.1 % of primaries > 10 MeV) | 1,235 (9.9 %) | 11 (1.0 %) |
| 35-50 | 1,502 (10.7 % of primaries > 10 MeV) | 1,247 (10.0 %) | 22 (1.9 %) |
| 50-75 | 1,453 (10.4 % of primaries > 10 MeV) | 1,269 (10.2 %) | 74 (6.4 %) |

Truth topology depends on the band: **1,072 of the 12,427 truth events (8.6 %) change their 0p/1p/>=2p category between the 35 and 50 MeV thresholds**, because about 10 % of the events have a true proton in each 15-25 MeV band. The reco side is much less affected: only 1.9 % of the selected events have a reco proton row in 35-50 MeV and 20 of 1,153 change reco category (P1 vs P3). Resolution around the thresholds (Phase-10 row-level response, class-A rows):

* true 25-35, reco > 35: 108 of 238 rows (45.4 %)
* true 35-50, reco <= 35: 76 of 348 rows (21.8 %)
* true 35-50, reco > 50: 205 of 348 rows (58.9 %)
* true 50-75, reco <= 50: 128 of 561 rows (22.8 %)
* true 50-75, reco <= 35: 55 of 561 rows (9.8 %)

so the **topology definition is sensitive to the proton energy resolution within +-15 MeV of either threshold** (a true proton of 35-50 MeV is reconstructed below 35 MeV in 22 % and above 50 MeV in 59 % of the rows), but few selected events live there.

## 5. Compatibility with other analyses (same threshold vs same proton definition)
SPINE (Seokju): truth `genE - m_p > 50 MeV` of **primary** SPINE protons (`proton_threshold = 50`), reco side not audited. MicroBooNE single-photon reference (`selection/microboone_single_photon_selection.yaml`): reconstructed proton KE 35 MeV (also the Wire-Cell planning value). No Prabhjot / Matteo topology definition is available in the repository. **A 50 MeV threshold does not make the Wire-Cell and SPINE proton definitions equivalent**: Wire-Cell rows are typed-proton `T_kine` rows of any pool (track or shower, secondary or primary, 84 % true primaries after the selection), SPINE counts primary-flagged proton-PID particles; the `included == 3` leftover-shower rows have no SPINE analogue.

# Part C: candidate policy

## 6. Definitions (SOURCE: `WIRECELL_SOURCE_CONVENTIONS_AUDIT.md` section 1)
`any`: the event passes if any candidate passes all frozen cuts (the baseline). `first`: only candidate index 0 is used. **`nu_index` is the position after sorting the in-window flash bundles that survive the cosmic vetoes by the length of their selected activity, longest first, ties by lower flash gid**: candidate 0 is the candidate with the longest selected activity, **not** the highest BDT score, **not** the truth neutrino candidate and not a guaranteed neutrino interaction (`nu_dedup_flash_group` is off in the fg1 files).

## 7. Event overlap and counting (exact; `candidate_policy_event_overlap.csv`, `event_counting_check.csv`)
| sample | passes both | any only | first only | neither | n(any) | n(first) |
|---|---|---|---|---|---|---|
| official_signal | 1101 | 52 | 0 | 11,274 | 1153 | 1101 |
| bnb_cv_all_selected | 626 | 23 | 0 | 499,351 | 649 | 626 |
| bnb_cv_non_signal_background | 613 | 22 | 0 | 499,365 | 635 | 613 |

Official signal (TPC box): 1,101 events pass under both (the **same candidate**), **52 only under `any`** (candidate 0 fails, candidate 1 passes), 0 only under `first`, confirmed exactly. BNB-CV: 626 / 23 / 0 (non-signal background: 613 / 22 / 0; the natural signal-like events: 13 / 1 / 0). The BNB `first` products are reproduced from the existing derived candidate table (`policy_first` and `pass_final`): 626 of the 649 selected candidates have `nu_index == 0`.

| sample | events with a candidate | with >= 2 candidates | selected events | selected with >= 2 passing candidates | max passing per event |
|---|---|---|---|---|---|
| official_signal_filter_box | 11,938 | 471 | 1,172 | 0 | 1 |
| bnb_cv | 237,460 | 4,371 | 649 | 0 | 1 |

**Event counting: every selected event counts once** (no event has two passing candidates in either sample, hence none under any reco FV either, which can only reduce the count). Interaction candidates are not counted as separate events.

## 8. Why candidate 1 rescues an event (`any_only_events.csv`, `any_only_events_summary.csv`)
Official signal, 52 events: candidate 0 first fails at no > 20 MeV shower: 37; numu: 13; BDT not evaluable: 1; ncpi0: 1; candidate 0 belongs to neutrino_in_AV: 50; neutrino_outside_AV_dirt: 2 and to **another neutrino interaction in all 52** (never the same truth neutrino); the **passing candidate 1 is the signal-matched candidate in all 52** (truth: truth 1p: 28; truth 0p: 23; truth >=2p: 1). BNB-CV, 23 events: candidate 0 fails at no > 20 MeV shower: 19; numu: 2; n_20br1: 1; ncpi0: 1; candidate 0 truth neutrino_in_AV: 22; neutrino_outside_AV_dirt: 1; passing candidate truth neutrino_in_AV: 18; neutrino_outside_AV_dirt: 5; same truth neutrino for candidate 0 and the passing one: False: 22; True: 1.

**Interpretation:** the signal events have on average 1.9 truth neutrino interactions in the readout window; when another interaction (mostly a CC interaction) has the longest activity it becomes candidate 0 and fails; candidate 1 is then the real NC-Delta candidate. `any` recovers legitimate non-primary candidates, it does not pick pathological ones (below). Truth-association caveat: candidate-level truth is the Phase-3 dominant-charge association (`dom_nu`), not the `T_match` top partner.

## 9. Policy effect on the common observables (`any_only_vs_common_observables.csv`)
For the 1,101 common events the objects are identical under both policies (Phase 11). The additional `any`-only population:

| population | n | median E_gamma [MeV] | attached | median M_Delta [MeV] | median vertex z [cm] | median kine_reco_Enu [MeV] | reco 1g1p |
|---|---|---|---|---|---|---|---|
| common (any and first) | 1101 | 314 | 50 % | 1221 | 247 | 466 | 49 % |
| any-only | 52 | 348 | 58 % | 1218 | 216 | 441 | 38 % |
| BNB non-signal common | 613 | 485 | 67 % | 1379 | 208 | 797 | 36 % |
| BNB non-signal any-only | 22 | 403 | 68 % | 1372 | 245 | 645 | 41 % |

The 52 signal events resemble the common ones (photon truth-correct 100 % vs 99.5 %, clean photon 98 % vs 98 %, anchored 56 % vs 62 %, M_Delta median 1218 vs 1221 MeV, truth-1p fraction 54 % vs 51 %); their reco proton KE is lower (median 104 vs 154 MeV, 1g1p fraction 38 % vs 49 %) and the vertices sit slightly more upstream (z 216 vs 247 cm): **no qualitatively pathological population**. The BNB `any`-only events are likewise like the common background (E_gamma 403 vs 485 MeV, M_Delta 1372 vs 1379 MeV).

# Part E: policy envelope and common-volume rates

## 10. Policy envelope (reference package `av200_P1_any`; differences are not combined)
| package | FV | proton | cand | signal eff | reco 1g0p / 1g1p / >=2p | 1g1p truth-1p / 1g0p truth-0p | B_beam reco 0p / 1p | M mode / half68 | usable |
|---|---|---|---|---|---|---|---|---|---|
| `baseline_frozen` | none | P1 | any | 9.28 % | 527 / 556 / 70 | 84.7 / 80.6 % | 310 / 230 | 1225 / 89.9 | 554 |
| `av200_P1_any` | av200 | P1 | any | 9.28 % | 527 / 556 / 70 | 84.7 / 80.6 % | 305 / 228 | 1225 / 89.9 | 554 |
| `cafpyana190_P1_any` | cafpyana190 | P1 | any | 10.11 % | 459 / 499 / 62 | 84.6 / 81.0 % | 221 / 191 | 1225 / 92.6 | 497 |
| `numu2021_P1_any` | numu2021 | P1 | any | 10.15 % | 459 / 499 / 62 | 84.6 / 81.0 % | 220 / 191 | 1225 / 92.6 | 497 |
| `spine180_P1_any` | spine180 | P1 | any | 10.44 % | 436 / 467 / 58 | 83.9 / 80.5 % | 202 / 177 | 1225 / 91.7 | 465 |
| `legacy_nue175_P1_any` | legacy_nue175 | P1 | any | 10.57 % | 396 / 429 / 49 | 84.4 / 80.8 % | 175 / 153 | 1225 / 92.8 | 428 |
| `cohpi_carve_P1_any` | cohpi_carve | P1 | any | 9.92 % | 364 / 421 / 57 | 85.7 / 83.2 % | 180 / 159 | 1225 / 87.8 | 419 |
| `av200_P2_any` | av200 | P2 | any | 9.28 % | 592 / 505 / 56 | 89.7 / 76.4 % | 334 / 210 | 1225 / 85.2 | 503 |
| `av200_P3_any` | av200 | P3 | any | 9.28 % | 545 / 540 / 68 | 84.8 / 84.8 % | 312 / 226 | 1225 / 89.0 | 538 |
| `av200_P4_any` | av200 | P4 | any | 9.28 % | 603 / 495 / 55 | 89.3 / 81.4 % | 340 / 207 | 1225 / 85.4 | 493 |
| `av200_P1_first` | av200 | P1 | first | 8.86 % | 498 / 536 / 67 | 84.5 / 81.1 % | 294 / 220 | 1225 / 90.1 | 534 |
| `spine_comparable_FV180_P3_any` | spine180 | P3 | any | 10.44 % | 453 / 452 / 56 | 83.8 / 84.8 % | 207 / 177 | 1225 / 90.3 | 450 |

`policy_envelope.csv` carries the differences to the reference package for every column (`d_*`); they are **not** a systematic uncertainty and are not combined in quadrature.

## 11. Signal and beam-neutrino-background rates per 1e20 POT under each package's reconstructed FV

| package | S reco 0p [/1e20 POT] | S reco 1p | B_beam reco 0p | B_beam reco 1p | S/B_beam reference ratio 0p | 1p |
|---|---|---|---|---|---|---|
| `baseline_frozen` | 18.6 | 19.6 | 1140 | 846 | 0.016 | 0.023 |
| `av200_P1_any` | 18.6 | 19.6 | 1122 | 838 | 0.017 | 0.023 |
| `cafpyana190_P1_any` | 16.2 | 17.6 | 813 | 702 | 0.020 | 0.025 |
| `numu2021_P1_any` | 16.2 | 17.6 | 809 | 702 | 0.020 | 0.025 |
| `spine180_P1_any` | 15.4 | 16.5 | 743 | 651 | 0.021 | 0.025 |
| `legacy_nue175_P1_any` | 14.0 | 15.1 | 644 | 563 | 0.022 | 0.027 |
| `cohpi_carve_P1_any` | 12.8 | 14.8 | 662 | 585 | 0.019 | 0.025 |
| `av200_P2_any` | 20.9 | 17.8 | 1228 | 772 | 0.017 | 0.023 |
| `av200_P3_any` | 19.2 | 19.0 | 1147 | 831 | 0.017 | 0.023 |
| `av200_P4_any` | 21.2 | 17.4 | 1250 | 761 | 0.017 | 0.023 |
| `av200_P1_first` | 17.5 | 18.9 | 1081 | 809 | 0.016 | 0.023 |
| `spine_comparable_FV180_P3_any` | 16.0 | 15.9 | 761 | 651 | 0.021 | 0.024 |

Signal rate: dedicated-sample exposure 2.8385e21 POT (flux-equivalent); beam-neutrino background: BNB-CV 2.7194e19 POT; statistical only. These are rates of selected objects: **not** a final S/B or purity (no cosmic-only component, no flux / cross-section / detector systematics). The last two columns are the **signal / beam-neutrino-background reference ratio**, labelled as such, **not** an analysis S/B.
