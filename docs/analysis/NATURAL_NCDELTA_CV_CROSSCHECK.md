# Natural NC Δ → Nγ in the BNB CV, and consistency with the dedicated official sample

Cross-check only. No reconstruction, cut, FV or classifier was changed; nothing here was tuned; **no signal efficiency is claimed** (the dedicated sample will provide that once its Wire-Cell merged CAF exists). Scans: `scripts/natural_ncdelta_cv_scan.py` (all 37,742 CV files, 1,377 s, 0 errors; derived products outside Git in `$SP_DATA/natural_ncdelta_bnb_cv/`), `scripts/natural_ncdelta_cv_report.py` (tables `tables/natural_ncdelta/`, plot `plots/natural_ncdelta/natural_vs_dedicated.png`). Library: `natural_signal.py`, `truth_signal.py`.

## 1. Definition (identical to the dedicated-sample validation)

An NC neutrino whose GENIE record (`GenieEvtRecTree`) has a status-1 photon with a Δ⁰ (2114) or Δ⁺ (2214) mother (`truth_signal.genie_record_ancestry`, the same function and code path used for the 13,773 dedicated events). **No `resnum`, no CAF proxy.** Event key kept: `(file_index, run, subrun, evt)` plus the qualifying `rec.mc.nu` index (`natural_signal_events_bnb_cv.csv`; (run, subrun, evt) is unique over the 416 events).

## 2. The natural population in the stored BNB CV (500,000 events, ΣTotalPOT 2.71940e19)

| quantity | value |
|---|---|
| stored events with ≥ 1 qualifying signal neutrino | **416** |
| qualifying signal neutrinos | 416 (no event has two) |
| Δ⁰ → nγ / Δ⁺ → pγ | **242 / 174** (58.2 % / 41.8 %) |
| signal-neutrino flavour | ν_μ 403, ν_e 8, anti-ν_μ 5 |
| vertex region | **117** in the provisional active TPC box; 11 in the filter box outside it (padding); **288 outside the filter box** (rock interactions kept by the generator's dirt/energy-deposit path) |
| truth protons (post-FSI primaries, KE > 35 MeV, provisional) all 416 / TPC-box 117 | 0p 212 / 59; 1p 172 / 46; ≥2p 32 / 12 |
| radiative photon energy 5/25/50/75/95 % (all) | 136 / 205 / 283 / 369 / 550 MeV |
| rate, vertex in the TPC box | 117 / 2.71940e19 = 4.30e-18 per POT (**430 ± 40 per 1e20 POT**) |

The CV generator keeps an event if the vertex is in the TPC (`GenNuFilter VtxInTPC`) or if the interaction deposits > 0.1 MeV in the TPC (dirt path), so only the TPC-box region is a complete, like-for-like population; the 288 rock-region signal interactions have no counterpart in the dedicated sample (the filter vetoes parents outside its box).

## 3. Dedicated sample vs natural CV (vertex in the provisional active TPC box: 12,427 dedicated, 117 CV)

| test | dedicated | natural CV | result |
|---|---|---|---|
| signal rate per 1e20 POT | 437.8 | 430.2 ± 39.8 | **ratio CV/dedicated 0.983, 95 % CI 0.81–1.18; conditional-binomial p = 0.89**; 117 observed vs 119.05 expected (Poisson z = −0.19) |
| Δ⁰ fraction | 0.551 [0.542, 0.560] | 0.556 [0.465, 0.642] | Fisher p = 1.00 |
| truth 0p / 1p / ≥2p | 47.2 / 44.7 / 8.1 % (TPC box: 47.2 / 44.7 / 8.1) | 50.4 / 39.3 / 10.3 % | χ² (2 dof) = 1.68, p = 0.43 |
| ν_μ fraction | 0.981 | 0.966 [0.915, 0.987] | Fisher p = 0.18 |
| ν_e fraction | 0.0068 | 0.017 (2 events) | Fisher p = 0.19 |
| radiative photon energy | | | KS p = 0.86 |
| neutrino energy | | | KS p = 0.90 |
| vertex x / y / z | | | KS p = 0.097 / 0.65 / 0.69 |

Padding region (information, not like-for-like): the CV has 11 signal events with the vertex in the filter box but outside the TPC box; the dedicated rate predicts 12.9 if all were stored.

**Answer.** The dedicated EX_ncdeltarad sample is statistically consistent with being an **unweighted filtered subset of the same naturally generated NC Δ → Nγ population** that the CV production contains: the absolute rate per POT agrees to 2 % (±18 % at 95 %), the Δ⁰/Δ⁺ split, the truth proton fractions, the flavour mix and the photon and neutrino energy and vertex distributions show no significant difference (smallest p-value 0.097, among 12 comparisons, not significant). **What this does not prove:** which GENIE branching configuration the generator uses. The CV is an inclusive generation with the default decays, so agreement means the dedicated sample is not enhanced by a forced branching or a weight at more than roughly the 20 % level of the CV's own statistical precision (a few-percent difference is untestable with 117 events); it does not identify the configuration, and agreement of shapes does not replace the producers' confirmation. The dedicated sample's own `genweight` is unfilled, so no per-event weight exists.

## 4. The frozen baseline on the natural signal events (join by the full event key; truth is never used to choose the candidate)

All 416 events are present in the derived analysis table (0 not found) and are `wc.valid == 1`. Events are counted once; `any` = any candidate passes the stage, `first` = only the `nu_index == 0` candidate.

| stage (cumulative) | all 416, `any` | TPC-box 117, `any` | TPC-box 117, `first` |
|---|---|---|---|
| `wc.valid == 1` | 416 | 117 | 117 |
| has a candidate | 209 | 105 | 105 |
| ≥ 1 shower above 20 MeV | 97 | 70 | 69 |
| BDT-evaluable (info) | 96 | 70 | 69 |
| numu > 0.4 | 60 | 47 | 46 |
| other > 0.2 | 38 | 31 | 30 |
| ncpi0 > −0.05 | 15 | 13 | 12 |
| nue > −1 | 15 | 13 | 12 |
| **final (n20br1 == 1)** | **14** | **13** | **12** |
| final reco 0p / 1p / ≥2p | 8 / 6 / 0 | 7 / 6 / 0 | 7 / 5 / 0 |

Observations (cross-check, small numbers, no efficiency claimed): of the 288 rock-region signal events only 104 have a candidate and none passes the final selection; the TPC-vertex events behave like the signal the baseline was developed for: 90 % have a candidate, 60 % have an evaluable 20-MeV shower (70/117), 11.1 % (13/117) pass the full chain (statistical error ≈ 3 points). This is qualitatively like the old development study (59 Aurora events, no FV: 33/59 = 56 % BDT-evaluable, 24/59 shw_sp_filled = 0, 3/59 = 5.1 % final; `analysis/microboone_1gamma_v0/docs/PART_E_FINAL_PHYSICS_NUMBERS.md`): 70/117 = 60 % evaluable vs 56 %, 13/117 vs 3/59 gives Fisher p = 0.27 (not distinguishable with these numbers). The dominant loss is the "no shower above 20 MeV / `shw_sp_filled == 0`" step (≈ 40 % of TPC-vertex events), as in `BDT_EVALUABILITY_AUDIT.md`. Those are development-sample numbers; neither they nor the 117-event natural sample is the efficiency.

**Overlap with the CV baseline background.** 14 of the 649 final `any` CV events (2.2 %) are natural NC Δ → Nγ events (13 in the TPC box, 1 in the padding region); in all 14 the selected candidate is dominated by the signal neutrino (truth vertex within 5 cm; evaluation only). Their reco split (8 0p / 6 1p) is already part of the 318 / 236 1γ0p / 1γ1p numbers of `BASELINE_1G0P_1G1P_BACKGROUND.md`. That is why the dedicated sample must not simply be added to the full CV (`NCDELTA_BASELINE_ANALYSIS_DESIGN.md`, "Signal/background bookkeeping").

## 5. Events with more than one qualifying neutrino

None in the CV (0 of 416). In the dedicated sample 6 of 13,773 events have two; in all six exactly one lies inside the filter box (the other is a far rock interaction); same truth proton category in 4 of 6; the 0p/1p/≥2p category would differ between the two choices in 2 of 6; the proposed provisional rule (prefer the in-filter-box neutrino, then the lowest `rec.mc.nu` index) picks the physical one in all six (`SIGNAL_TRUTH_AND_DENOMINATOR.md` §5).
