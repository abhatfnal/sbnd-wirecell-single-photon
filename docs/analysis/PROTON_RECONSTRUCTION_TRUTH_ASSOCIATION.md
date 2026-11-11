# Row-level truth association of the reconstructed protons (official Gen2 NC-Delta, frozen Wire-Cell baseline)

Date: 2026-11-11. Branch `analysis/ncdelta-proton-truth-association-20261111` (cut from the pushed Phase-9 head `fe7f91c`). **Characterization only**: no threshold optimisation, selection change, BDT retraining or FV choice. Every statement states its population: official Gen2 NC-Delta signal, provisional TPC truth box (12,427 events; 12,426 with a merged CAF), frozen production fg1 reconstruction and BDT cuts, candidate policy `any`, proton threshold 35 MeV (50 MeV as a projection), "signal-matched candidate" = the baseline `match_cand_nu` (10,831 events), "final selected" = the 1,153 events of the frozen selection. Companion documents: `RECO_PROTON_ROW_SEMANTICS.md` (source), `RECO_PROTON_TRUTH_TAXONOMY.md` (classes and association quality), `WIRECELL_TRUTH_MATCH_SEMANTICS.md`. Code: `scripts/proton_truth_scan.py`, `scripts/proton_truth_origin_scan.py`, `scripts/proton_truth_delta_inputs_scan.py`, `scripts/proton_truth_audit.py`, `src/sbnd_single_photon/proton_tables.py`. Tables `tables/proton_truth_association/`, figures `plots/proton_truth_association/`, row/event tables outside Git in `$SP_DATA/proton_truth_association/official_ncdelta/`.

## 1. Motivation

The event-level 0/1/>=2 proton migration (final selection: truth 1p -> 93 reco 0p, 471 reco 1p, 30 reco >=2p; truth 0p -> 425 / 50 / 1; truth >=2p -> 9 / 35 / 39) hides which *row* of which *true particle* produced each reco proton. Without that, reco-vs-true proton KE, resolution, misidentification, proton-origin plots and the reconstructed Delta mass are not trustworthy, and a common Wire-Cell/SPINE proton comparison has no definition. Phase 3 answered it on N = 117 natural events with non-exclusive flags; this phase does it exclusively on 12,426 official events (8,132 true signal primary protons above 35 MeV, 6,941 reco proton rows above 35 MeV).

## 2. Reco proton semantics (`RECO_PROTON_ROW_SEMANTICS.md`)

A reco proton is a `T_kine` row typed 2212 by the dQ/dx-template/range PID logic (source commit `4b6853d4`); the KE is a range estimate for a track >= 4 cm, a dQ/dx charge estimate for shorter tracks and shower trajectories, `kine_best` for showers. **MEASURED: 56.7 % of all proton-typed rows are shower rows** (leftover showers, pool 2) and **20.3 % of the proton-typed rows above 35 MeV**. `kine_energy_included == 3` is, from the source, a pool-2 leftover *shower of a different cluster attached by proximity (<= 80 cm)*, inside `kine_reco_Enu` despite the name; measured: 43,168 rows, all pool-2 showers, 99.7 % outside the main cluster; 18.7 % of the proton-typed rows above 35 MeV. Whether to count them is **not decided** (roadmap item E). The rows reproduce the baseline reco proton counts exactly (0 mismatches in 10,831 + 1,153 events).

## 3. Truth-match semantics

`T_match` level 1 side 0 is one object per `T_kine` row; its up to three truth-prong partners are ranked by **point IoU** in the stored (production) order, top partner = `match_obj[0]`; charge IoU is reported, never used to rank. Prongs carry the interaction, PDG and the Geant4 `process`; **primary = `process == 0`** (not `parent_trackid == 0`, which also holds for secondaries whose parent was not stored). The signal primary protons built this way reproduce the baseline truth multiplicities (`n_p50` exactly; `n_p35_prim` in all events but one). `T_overlap` agrees with the top partner for 97.6 % of the proton-typed rows (cross-check only).

## 4. Row-level association quality

(`RECO_PROTON_TRUTH_TAXONOMY.md` section 4.) Rows above 35 MeV, all candidates: 6,941. Median top point IoU 0.87 (class A 0.93, C 0.89, **D 0.17**), median top-minus-second separation 0.84, mutual in 86 % (A 96 %, D 31 %); 79.7 % of the rows belong to the validation-only high-confidence subset. Unmatched: 28 rows (0.4 %), ambiguous (class G, second partner of a different origin and >= half the top IoU): 146 (2.1 %). Association is therefore **robust for the rows that are real protons** (A, B, C: IoU 0.83-0.93) and **weak exactly for the rows that are not** (D: a small piece of another particle's charge), which is itself diagnostic.

## 5. Reco proton truth composition (the question: "what fraction of a reconstructed proton is a proton from the intended signal interaction?")

Rows typed 2212 above the threshold (`reco_proton_purity_scan.csv`; the scan is diagnostic, **not a threshold optimisation**):

| population / threshold | rows | A signal primary p | C G4 secondary p | D signal non-p | B other-nu p | F cosmic | G ambiguous | H unmatched | E other-nu non-p |
|---|---|---|---|---|---|---|---|---|---|
| all candidates, >35 MeV | 6,941 | 55.1 % | 18.0 % | 14.8 % | 8.2 % | 1.1 % | 2.1 % | 0.4 % | 0.4 % |
| **signal-matched candidate, >10** | 6,997 | 59.0 % | 19.3 % | 18.0 % | 0.3 % | 0.5 % | 2.0 % | 0.9 % | 0.0 % |
| signal-matched, >20 | 6,545 | 60.4 % | 20.0 % | 16.1 % | 0.3 % | 0.5 % | 2.1 % | 0.5 % | 0.0 % |
| **signal-matched, >35** | **6,280** | **60.6 %** | **19.8 %** | **16.2 %** | 0.3 % | 0.5 % | 2.2 % | 0.4 % | 0.0 % |
| signal-matched, >50 | 5,963 | 60.5 % | 19.3 % | 16.9 % | 0.3 % | 0.4 % | 2.2 % | 0.4 % | 0.0 % |
| signal-matched, >75 | 5,151 | 60.4 % | 18.7 % | 17.5 % | 0.3 % | 0.3 % | 2.5 % | 0.3 % | 0.0 % |
| signal-matched, >100 | 3,838 | 61.0 % | 18.3 % | 17.1 % | 0.3 % | 0.3 % | 2.8 % | 0.2 % | 0.0 % |
| **final selected, >35** | **719** | **84.1 %** | **9.6 %** | **3.8 %** | 0.1 % | 0.3 % | 1.9 % | 0.1 % | 0.0 % |
| final selected, >50 | 697 | 84.1 % | 9.5 % | 3.9 % | 0.1 % | 0.3 % | 2.0 % | 0.1 % | 0.0 % |

* The composition is **flat in the threshold** from 10 to 100 MeV (A: 59-61 %): the KE threshold does not change what kind of object a "reco proton" is. (All rows are read; the scan starts at 10 MeV.)
* **By truth topology (signal-matched, >35 MeV):** truth 0p 10.5 % A / 41.4 % C / 44.9 % D (1,262 rows); truth 1p 70.2 % / 16.2 % / 10.1 % (3,917); truth >=2p 83.9 % / 7.8 % / 5.4 % (1,101). **By Delta charge:** Delta+ 70.9 % A (3,698 rows), Delta0 45.8 % A with 27.5 % C and 23.5 % D (2,582). **By row kind:** tracks 62.5 % A (4,962 rows); leftover showers with `included == 3` 57.8 % A / 29.9 % C (1,216); leftover showers with `included == 1` 2.9 % A / **92 % D** (102: these are the signal photon typed proton).
* **Final selected (>35):** truth 0p 21.2 % A / 51.9 % C / 23.1 % D (52 rows), truth 1p 88.5 % / 6.5 % / 2.6 % (537), truth >=2p 91.5 % / 5.4 % / 0.8 % (130), Delta+ 87.9 %, Delta0 73.1 %.
* **Answer:** in the signal-matched candidate, **about 61 % of the rows called reco proton above 35 MeV are a post-FSI primary proton of the signal interaction, 20 % are a Geant4 secondary proton of the signal interaction (a real proton but not a primary), 16 % are not a proton at all (94 % of those, in the all-candidate sample, are the signal photon)**; after the frozen selection the primary fraction is 84 %. Counting any true proton (A + B + C) the proton purity is 80.7 % (signal-matched) / 93.8 % (final).

## 6. True proton reconstruction efficiency

Denominator: the 8,132 signal primary protons above 35 MeV (6,630 above 50 MeV) in **all** 12,426 events with a file (`true_proton_efficiency.csv`, `true_proton_reco_state*.csv`). A proton is *found* if a row of the **signal-matched** candidate has it as top partner, *proton-IDed* if such a row is typed 2212, *threshold-passing* if that row has reco KE above the threshold.

| state of the true proton (35 MeV) | protons | % |
|---|---|---|
| a single typed-proton row | 3,558 | 43.8 |
| two or more rows, at least one typed proton | 207 | 2.5 |
| rows exist but none typed proton (matched non-proton row) | 1,406 | 17.3 |
| only a subdominant (2nd/3rd) partner of some row | 1,320 | 16.2 |
| no row of any candidate has it as a partner | 854 | 10.5 |
| the event has no candidate | 541 | 6.7 |
| the event has a candidate but no signal-matched one | 244 | 3.0 |
| rows only in another candidate | 2 | 0.0 |

| (all signal primary protons) | row found | proton ID | threshold passing |
|---|---|---|---|
| > 35 MeV (8,132) | 63.6 % | 46.3 % | 44.4 % |
| > 50 MeV (6,630) | 69.9 % | 51.5 % | 49.2 % |

* **Versus true KE (35 MeV scan, `true_proton_reco_efficiency.png`):** row-found 36 % (35-50 MeV), 56 % (50-75), 72 % (75-100), 68-79 % above 100 MeV; **proton-ID** 23 %, 38 %, 55 %, 51 %, 60 %, 67 % (200-300), 58 % (300-500) and **23 % above 500 MeV** (there the row is found in 73 % but typed non-proton in half: 182 of 362 are matched non-proton rows - high-energy protons look MIP-like to the dQ/dx-template PID). Below 75 MeV the proton is most often merged into another object (35-50 MeV: 507 of 1,502 are only a subdominant partner).
* **Angle:** row-found 48 % (backward, cos < -0.5) to 69 % (forward, cos > 0.8); proton-ID 36 % to 50 %. **Vertex:** proton-ID 49 % (z < 100 cm), 46 %, 48 %, 47 %, **41 % (z 400-500 cm)**: a mild dip at the downstream end, no monotonic trend; no strong x or y dependence (44-49 % in |x| and |y| bins; `true_proton_efficiency.csv`).
* **Origin:** Delta-decay protons 73.1 % found / 52.8 % typed (3,537), FSI-created protons 55.3 % / 40.6 % (4,109), ambiguous 69.0 % / 49.7 % (348). Delta+ 66.5 % found, Delta0 57.8 %; truth-1p events 70.5 % found / 48.5 % passing, truth->=2p events 48.7 % / 35.7 % (the second and third protons are the missing ones, section 10).
* **What this means for truth 1p -> reco 0p:** the leading cause is not the KE threshold but that the proton is not available as a typed-proton row (sections 8, 10).

## 7. Proton KE response

Rows with the true signal primary proton as top partner in the signal-matched candidate, typed proton (class A, n = 3,915; the validation-only high-confidence subset n = 3,537) (`proton_ke_response.csv`, `proton_ke_response.png`):

| true KE (MeV) | n (HC) | median reco/true | 16-84 % | resolution (half-width) | median (reco-true)/true |
|---|---|---|---|---|---|
| 35-50 | 327 | 1.33 | 0.65-2.04 | 0.69 | +0.33 |
| 50-75 | 493 | 1.10 | 0.78-1.57 | 0.40 | +0.10 |
| 75-100 | 477 | 0.97 | 0.93-1.01 | 0.04 | -0.03 |
| 100-150 | 563 | 0.99 | 0.95-1.01 | 0.03 | -0.015 |
| 150-200 | 490 | 0.99 | 0.89-1.01 | 0.06 | -0.01 |
| 200-300 | 639 | 0.99 | 0.86-1.01 | 0.07 | -0.01 |
| 300-500 | 477 | 0.99 | 0.66-1.01 | 0.17 | -0.015 |
| 500-1500 | 71 | 0.98 | 0.64-1.02 | 0.19 | -0.02 |
| all | 3,537 | 0.99 | 0.87-1.06 | 0.095 | -0.01 |

* Above ~75 MeV the proton KE is **unbiased with a few-percent core** (range of a contained track); the low tail above ~300 MeV is the leaving/interacting proton (a range lower limit). **Near threshold the reco KE is biased high and broad** (+33 % at 35-50 MeV): with a falling spectrum, rows with an over-estimated KE migrate across the threshold, which is a migration effect and not a calibration shift. All class-A rows (not only high-confidence) give the same medians with a wider core (resolution 0.154 overall).
* **Delta decay vs FSI-created:** decay protons median 0.983 (resolution 0.081, n = 1,783), FSI-created 0.999 with a long upper tail (resolution 0.247, n = 1,546): the FSI-created rows include low-KE protons in the biased-high region and leftover showers.
* **`included == 3` vs `!= 3` (diagnostic, no policy decision):** `included != 3` rows (n = 2,874 HC): median 0.990, resolution 0.079; `included == 3` rows (n = 663 HC; all showers): median 0.988 but a broad **upper** tail (84th percentile 1.45; resolution 0.295). The median hides the difference: leftover showers typed proton are on average right but with a much wider response. (Phase 2 saw a second low peak at reco/true ~ 0.25 for `included != 1` rows on BNB CV; among the class-A rows of the signal sample only 3.5 % of the `included == 3` rows and 8.0 % of the others lie below 0.4, while 21.7 % of the `included == 3` rows lie above 1.3: here the leftover-shower rows are broad on the upper side, not bimodal.)

## 8. Truth 1p -> reco 0p (exact accounting)

Ladder for the 5,557 truth-1p events (35 MeV): 1 production-missing, 386 without a candidate, 192 with a candidate but no signal-matched one, **4,978 signal-matched** (reco 0p 1,739 / 1p 2,643 / >=2p 596), **594 final selected** (reco 0p 93 / 1p 471 / >=2p 30). Reasons for the reco-0p events (mutually exclusive, hierarchy in `proton_tables`/audit; `migration_truth1p_to_reco0p.csv`):

| reason | signal-matched candidate (n = 1,739) | final selected (n = 93) |
|---|---|---|
| a row has the proton as top partner but **no row is typed proton** (shower-typed electron 536, muon 268, pion 79) | **883 (50.8 %)** | 37 (39.8 %): muon 23, pion 10, electron 4 |
| the proton is only a subdominant partner (merged into another object) | 387 (22.3 %) | 15 (16.1 %) |
| the proton has **no row** although it deposited charge | 370 (21.3 %) | 27 (29.0 %) |
| a typed-proton row exists but its reco KE <= 35 MeV | 89 (5.1 %) | 9 (9.7 %) |
| no readout charge at all | 9 (0.5 %) | 4 (4.3 %) |
| the proton is only in another candidate | 1 | 1 |
| excluded by the `included` convention | 0 (the baseline counts `included == 3` rows) | 0 |

**50 MeV projection** (truth-1p at 50 MeV: 5,131 events; signal-matched 4,641, reco 0p 1,563; final 570 with reco 0p 82): non-proton type 802 (51.3 %) / 33 (40.2 %), subdominant 327 (20.9 %) / 13 (15.9 %), no row 350 (22.4 %) / 25 (30.5 %), KE below threshold 77 (4.9 %) / 7 (8.5 %), no charge 7 / 3, other candidate 0 / 1. Delta0 / Delta+ splits are in the table (Delta+ contributes 60-73 % of every reason). **Old Phase-3 rehearsal (N = 13 events):** no row 7, non-proton PID 4, KE below 2 - statistically compatible in structure but it over-weighted "no row" and "KE below threshold" and could not see the **subdominant-partner** state that, with the non-proton-typed row, accounts for about three quarters of the official loss. The KE threshold is a minor (5-10 %) cause.

## 9. Truth 0p -> reco 1p (exact accounting)

Truth-0p events (35 MeV): 5,863 = 653 no candidate + 284 not signal-matched + **4,926 signal-matched** (reco 0p 3,836 / 1p 940 / >=2p 150) ; **476 final selected** (reco 0p 425 / 1p 50 / >=2p 1). Origin of the unique reco proton row (`migration_truth0p_to_reco1p.csv`):

| truth origin of the reco proton row | signal-matched (n = 940) | final selected (n = 50) |
|---|---|---|
| D another signal particle (**signal photon typed proton 442**, other 24, pion 2) | **468 (49.8 %)** | 11 (22 %, all photon) |
| C Geant4 secondary proton of the signal interaction (parent neutron 296, proton 19) | **319 (33.9 %)**: Delta0 290, Delta+ 29 | 26 (52 %) |
| true primary proton **below** the 35 MeV truth threshold, promoted by reco (median true 31 MeV, reco 52 MeV) | 121 (12.9 %) | 11 (22 %) |
| B other-neutrino proton | 9 | 1 |
| F cosmic / G ambiguous / H unmatched / E | 9 / 6 / 7 / 1 | 0 / 0 / 1 / 0 |

50 MeV projection (truth 0p at 50 MeV: 6,664; signal-matched 5,599, reco 1p 1,081; final 527, reco 1p 64): D 516 (47.7 %) / 12, C 306 (28.3 %) / 24, promoted primary 225 (20.8 %) / 26, others 34 / 2. **Reading:** the 0p -> 1p migration is mostly the signal photon typed as a proton and neutron-induced Geant4 secondary protons (the Delta0 -> n gamma decay neutron scattering on argon: 290 of 319 secondaries are Delta0); a sub-threshold *true* proton promoted by reco is a minor (13-21 %, larger at 50 MeV) cause. About 28 % of the signal-matched 0p -> 1p rows are `included == 3` leftover showers (Phase 3: 5 of 15). Old rehearsal (N = 15): different PDG 7, secondary 4, sub-threshold primary 3: same ordering.

## 10. >=2p reconstruction and the multiplicity response

For the 927 truth->=2p events with a signal-matched candidate (35 MeV): 2,368 true protons (mean 2.55), **1,253 (52.9 %) with a row, 963 (40.7 %) typed proton, 918 (38.8 %) passing**, mean reco rows 1.19; only **26 %** of the events have every true proton found and **16.5 %** have every proton passing. 50 MeV: 591 events, 1,403 protons (mean 2.37), 954 (68.0 %) found, 756 (53.9 %) typed, 697 (49.7 %) passing, mean reco 1.39; 47 % of events have all protons found (`ge2p_reconstruction_summary_*.csv`).

Multiplicity response, 35 MeV truth and reco (`multiplicity_response.csv`, `multiplicity_response_matrix.png`):

| signal-matched (10,831) | reco 0 | 1 | 2 | 3+ |
|---|---|---|---|---|
| truth 0 (4,926) | 3,836 | 940 | 131 | 19 |
| truth 1 (4,978) | 1,739 | **2,643** | 520 | 76 |
| truth 2 (599) | 184 | 245 | **141** | 29 |
| truth 3+ (328) | 72 | 113 | 78 | **65** |

| final selected (1,153) | reco 0 | 1 | 2 | 3+ |
|---|---|---|---|---|
| truth 0 (476) | 425 | 50 | 1 | 0 |
| truth 1 (594) | 93 | **471** | 24 | 6 |
| truth 2 (60) | 5 | 28 | **22** | 5 |
| truth 3+ (23) | 4 | 7 | 3 | **9** |

Diagonal fractions (signal-matched): truth 1 -> reco 1 53.1 %, truth 2 -> reco 2 23.5 %, truth 3+ -> reco 3+ 19.8 %: the reco multiplicity is **systematically below truth for every truth multiplicity above 0** (mean reco 1.19 vs true 2.55 for >=2p). The 50 MeV projection (signal-matched: truth 0 4,349 / 1,081 / 155 / 14; truth 1 1,563 / 2,530 / 473 / 75; truth 2 102 / 157 / **149** / 21; truth 3+ 26 / 41 / 42 / **53**; final: truth 0 462 / 64 / 1 / 0, truth 1 82 / 458 / 24 / 6, truth 2 0 / 15 / 23 / 4, truth 3+ 1 / 3 / 2 / 8) has a better diagonal (truth 2 -> 2: 34.7 % signal-matched, 55 % final; truth 3+ -> 3+: 33 % and 57 %, small samples) because the low-KE, merged protons drop out of the truth. The final 3x3 collapse reproduces the known 425/50/1, 93/471/30, 9/35/39.

## 11. Vertex anchoring versus the truth identity of the leading reco proton

Leading reco proton = the highest-KE typed-proton row above 35 MeV in the signal-matched candidate; anchored = `|V_reco - V_true| <= 5 cm` (Phase 9). (`vertex_anchoring_by_leading_proton_truth.csv`, `anchoring_and_other_by_leading_proton_truth.png`.)

| leading reco proton | all (n) | truth 0p | truth 1p | truth >=2p |
|---|---|---|---|---|
| true signal primary proton | **72.3 %** (3,167) | 54.5 % (121) | **71.1 %** (2,472) | 81.4 % (574) |
| Geant4 secondary proton | 28.2 % (793) | 9.5 % (410) | 46.4 % (349) | 67.6 % (34) |
| non-proton row (fake) | **9.1 %** (894) | 2.8 % (536) | **18.1 %** (315) | 20.9 % (43) |
| ambiguous truth | 59.1 % (115) | - | 61.1 % (90) | 72.2 % (18) |
| other-neutrino proton | 0 % (18) | - | - | - |
| **absent** (no reco proton > 35 MeV) | **18.1 %** (5,831) | 13.7 % (3,836) | 27.0 % (1,739) | 22.7 % (256) |

**The strong anchoring of truth-1p events is specific to a correctly reconstructed true proton:** a fake non-proton row anchors *less* than no proton at all (truth 1p 18 % vs 27 %; 9 % vs 18 % overall), a Geant4 secondary proton anchors partially (46 % in truth 1p, 9.5 % in truth 0p where it sits away from the vertex), and a true primary proton anchors the vertex in 71 % (truth 1p), 82 % (>=2p) and even 54.5 % of truth-0p events (where it is a sub-threshold true primary). Phase 9's statement "a reco proton anchors the vertex" is therefore refined: *a reco proton row that is a true signal primary proton* is associated with anchoring; the label "reco proton present" alone is not (fake rows 9-21 %). The tagger-gap detached fraction of the same events is 43 % for true-proton rows (truth 1p), 13 % for fake rows, 27 % for absent. No causal statement: a true proton and a well-placed vertex are produced by the same pattern recognition, and whether the proton places the vertex or the vertex lets the proton be found was not tested.

## 12. Frozen `other` BDT versus the truth identity of the leading reco proton

Events reaching the `other` stage (Phase 8 population, 5,007), survival of the frozen `other` cut (`other_survival_by_leading_proton_truth.csv`):

| leading reco proton | all (n) | truth 0p | truth 1p | truth >=2p |
|---|---|---|---|---|
| true signal primary proton | **72.8 %** (1,498) | 55.9 % (68) | **73.0 %** (1,184) | 76.8 % (246) |
| Geant4 secondary proton | 57.7 % (305) | 50.9 % (171) | 66.1 % (118) | 68.8 % (16) |
| non-proton row (fake) | **49.0 %** (249) | 49.1 % (161) | 51.3 % (78) | 30.0 % (10) |
| ambiguous truth | 69.6 % (46) | - | 72.5 % (40) | - |
| **absent** | **47.4 %** (2,837) | 47.1 % (2,009) | 48.6 % (724) | 43.3 % (104) |

**The Phase-8 observation "truth 1p + reco proton -> high survival" is specific to a TRUE reconstructed proton:** a fake non-proton row survives at the level of "no reco proton" (49 % vs 47 %; truth 1p 51 % vs 49 %), the high survival (73 %) appears only when the row is a true signal primary proton, and a secondary proton is intermediate (66 % in truth 1p). The truth-0p events with a true (sub-threshold) primary proton row survive at 56 % versus 47 % for truth 0p without a proton, so the response follows the proton, not the nominal truth class. Small cells (n < 20) are not interpreted. Not tested here: the cause inside the BDT (item N).

## 13. Delta-mass readiness (ingredients only; no M_Delta cut, no physics plot)

`M_Delta^2 = m_p^2 + 2 E_gamma (E_p - p_p cos theta_gamma,p)` for the **556 final-selected reco 1gamma1p events** (`sel_np35 == 1`) (`delta_mass_readiness*.csv`, `$SP_DATA/.../delta_mass_readiness.parquet`):

| ingredient | availability | source definition |
|---|---|---|
| E_gamma | selected shower row found by energy equality with `shw_sp_energy` in **554 / 556** (the other 2 have `shw_sp_filled == 0`) | **understood** (`kine_best`, charge/range shower energy; selected shower = `shw_sp` max shower) |
| proton KE (E_p, p_p) | 556 / 556 (the unique typed-proton row) | **understood** (range / dQ/dx, section 2 of the row-semantics note) |
| photon direction | 554 / 556 from the `T_pf` node of the shower row (chord start -> end; median chord 91 cm); cos with the true photon direction: median 0.985, > 0.9 in 85.6 %, negative in 0.9 % (truth-correct rows) | **available, empirically consistent; the definition of the shower node's end point is not source-audited** (question for the pattern-recognition authors) |
| proton direction | 556 / 556 from the `T_pf` node chord (median 16 cm); cos with the true proton direction: median 0.998, > 0.9 in 93.3 %, **negative in 5.3 %** (direction sign / orientation, truth-correct rows) | as above; 5 % sign ambiguity visible |

All inputs present in **554 / 556**; `M_Delta^2` defined and positive for 554. Truth correctness: photon row is the signal photon in 554 / 554; proton row is a true signal primary proton in 493 / 556 (88.7 %), both truth-correct in **491 (88.3 %)**: truth 1p 446 / 471 (94.7 %), truth 0p 11 / 50 (22 %), truth >=2p 34 / 35. The 65 events with a wrong proton row are exactly the secondary / non-proton / ambiguous rows of section 5. No quantity is cut or plotted.

## 14. Future SPINE mapping (conceptual; no SPINE numbers)

From `SPINE_SIGNAL_DEFINITION_SOURCE_AUDIT.md`: SPINE truth counts **primary** SPINE-species protons (species id 4, `is_primary`), `KE = energy_init - mass`, threshold 50 MeV (technote); neutrons are not a species.

| Wire-Cell object | SPINE counterpart | status for a same-event comparison |
|---|---|---|
| true signal primary proton (post-FSI, `process == 0`, KE = `T_truth_pf.KE`) | SPINE truth primary proton, `energy_init - mass` | **same definition** (both are the generator-level post-FSI proton KE); only the threshold differs (35 vs 50 MeV): both projections are provided here |
| class A row (reco proton row whose top partner is a true primary proton) | a SPINE reco particle matched to a true primary proton, reco primary + proton PID | needs the SPINE particle-level match (by overlap), not yet available |
| class C row (Geant4 secondary proton) | a SPINE non-primary proton or a primary proton from a secondary | SPINE distinguishes by its primary flag; here it is a truth fact (`process != 0`) |
| class D row (photon typed proton) | SPINE photon/electron-vs-proton PID confusion | PID confusion matrix comparable only with the same truth particle definition |
| `included == 3` leftover-shower proton row | no analogue (SPINE has no "leftover shower in another cluster" class) | the policy question E should be answered before any comparison; the diagnostic here quantifies it |
| reco 0p/1p/>=2p from KE > 35 MeV rows | reco proton multiplicity from primary proton-PID particles above a reco-KE threshold | the **multiplicity matrix with the same truth multiplicity 0/1/2/3+ and the same reco threshold** is the common product; both frameworks need the truth population of `SPINE_SIGNAL_DEFINITION_HARMONIZATION.md` |

What must match for **proton reconstruction efficiency**: the truth proton set (post-FSI primary, same KE definition, same threshold, same truth region/FV flag), the denominator (all signal events vs events with a candidate/interaction; here the per-proton table keeps "no candidate" and "no signal-matched candidate" as explicit states) and the definition of "found" (row exists / typed proton / above threshold). For **multiplicity**: the same 0/1/2/3+ binning and reco threshold. For **KE response**: the same truth KE (`energy_init - mass` of the matched primary), the reco KE definition of each framework (WC: range/charge row KE; SPINE: its own) and a high-confidence matching subset defined identically on both sides.

## 15. What is established

* The reco proton rows can be associated with truth **one-to-one at the production level** (T_match level 1, source ranking) for 99.6 % of the rows; **61 % (signal-matched, >35 MeV) / 84 % (final) of the reco proton rows are true signal primary protons**; 20 % / 10 % are Geant4 secondary protons of the signal interaction; 16 % / 4 % are not protons (94 % of them the signal photon typed as proton).
* The primary reason a true proton is not a reco proton is **PID/typing and merging, not the KE threshold**: for the 1p -> 0p migration 51 % are matched non-proton rows, 22 % merged subdominant, 21 % no row, 5 % KE below threshold; efficiency 46 % typed (>35), 52 % (>50), with a collapse above 500 MeV (typed muon/pion) and below 75 MeV (merged).
* The 0p -> 1p migration is the signal photon typed as a proton (50 %), neutron-induced Geant4 secondary protons (34 %, mostly Delta0) and sub-threshold true primaries (13 %).
* The proton KE is unbiased with a few-percent core above 75 MeV and biased high and broad below ~75 MeV; leftover-shower proton rows have a much broader response.
* The Phase-9 vertex anchoring and the Phase-8 high `other` survival are specific to a **true signal primary proton row**; fake rows behave like no proton.
* The ingredients of the Delta mass are available for 554 of 556 selected 1gamma1p events (direction definition caveat).

## 16. What remains unresolved

* Whether the proton row causes the vertex anchoring (or the reverse): not tested.
* Why a proton is typed muon/pion (above 500 MeV) or merged into another object (below 75 MeV): the PID/merging source logic of the pattern recognition was read only at the level needed for the row semantics.
* The definition of the `T_pf` shower end point (photon direction) and the 5 % proton direction-sign ambiguity.
* The `included == 3` policy (item E) and the proton threshold (35 vs 50 MeV): only diagnostics are provided (`included3_diagnostic_*.csv`: the topology changes for 1,130 / 10,831 signal-matched and 77 / 1,153 final-selected events at 35 MeV, 965 and 69 at 50 MeV).
* 16 events with unreadable T_match partner lists (92 rows), 320 rows without a level-1 object, and one proton (35.18 MeV, 0.009 readout charge) counted here but not by the baseline truth.
* The 0.5 ambiguity ratio of class G and the high-confidence subset are analysis diagnostics.

## 17. Questions for later policy / optimization phases (no recommendations)

1. Is a reco proton defined by the typed-proton rows of one candidate, by true-origin classes that can only be known in MC, or by observables available in data (shower vs track, pool, `included`)? Which of the 18.7 % `included == 3` and 20 % shower proton rows belong to the analysis definition?
2. Is the 35 or the 50 MeV threshold the physics definition, given that the purity is flat in the threshold but the truth multiplicity matrix changes?
3. Should the multiplicity response (0/1/2/3+) replace the 0/1/>=2 matrix as the reported migration object?
4. Should Geant4 secondary protons of the signal neutron (Delta0) be part of the signal definition or of the efficiency systematic?
5. Which of the typing losses (muon/pion-typed proton above 500 MeV, photon typed proton) are pattern-recognition effects that SPINE would share or not?
6. What does the BDT response look like for a true proton row with the MicroBooNE training-domain features (item N)?
7. Which direction definition should the Delta-mass phase use for the shower and the proton (item B)?
