# NC Delta -> N gamma: signal truth object and efficiency denominator (proposal; nothing frozen; no efficiency computed)

Companion to `NCDELTA_GENERATOR_FILTER_AUDIT.md` (filter semantics and the measurements on the official sample) and `TRUTH_PROTON_DEFINITION_AUDIT.md`. Updated 2026-11-06 with direct measurements on the official Gen2 `EX_ncdeltarad` flatCAFs; no FV is introduced, every region below is a *parameter* of the denominator.

## 1. The signal truth object (process and topology are kept apart)

| field (`truth_signal.py`) | meaning | availability |
|---|---|---|
| `is_ncdelta_radiative` | **PROCESS**: an NC interaction with a status-1 photon whose mother is Delta0/Delta+ (the filter's own test) | with the GENIE record (`GenieEvtRecTree`, present in the official flatCAF and in the CV merged CAFs): **1 / 0, exact**. Without it (`recTree` only): tri-state, 1 only if the file is declared a filter stream, otherwise -1; never 0. |
| `delta_pdg`, `delta_charge`, `decay_nucleon_pdg` | Delta0 -> n gamma (2114, charge 0, n 2112) vs Delta+ -> p gamma (2214, +1, p 2212) | with the record: filled (official sample: 7,599 Delta0 / 6,174 Delta+). Without it: 0 = unavailable. |
| `photon_energy_mev`, `photon_energy_record_mev`, `n_primary_photons(_hard)` | hardest primary photon (generation-point energy) and the record photon | available |
| `genie_mode`, `resnum`, `neutrino_energy_gev`, `nu_pdg` | mode, resonance enum, true E_nu | available; **`resnum` is not a definition** (0 for only 97.66 % of the signal) |
| `signal_nu_index`, `n_signal_nu_candidates`, `n_signal_nu_in_box` | which neutrino of the event is the signal one (rule in §5) | with the record: one qualifying neutrino in 13,767 / 13,773 events, two in 6 (exactly one of the two inside the filter box in each) |
| `true_vertex_{x,y,z}`, `vtx_in_filter_box`, `vtx_in_active_tpc` | vertex and two **region flags** | available (signal: 100 % in the filter box, 90.2 % in the provisional TPC box) |
| `n_true_protons`, `true_proton_category` | **TOPOLOGY**: post-FSI primary protons above 35 MeV (provisional, configurable): 0p/1p/>=2p | available (signal: 47.2 % / 44.7 % / 8.1 %) |
| `is_ncdelta_rad_proxy`, `proxy_recovers_stream`, `proxy_agrees_with_record` | CAF-only proxy (NC, resonant, resnum 0, photon > 20 MeV) and its agreement with the record | diagnostic only; recovers 97.66 % of the official sample |

The decay channel (Delta0 -> n gamma vs Delta+ -> p gamma) and truth 0p/1p/>=2p are different axes and must never be equated: measured on the official sample, Delta0 events are 70 % truth-0p / 24 % 1p / 6 % >=2p, Delta+ events 19 % / 70 % / 10 % (the decay nucleon still goes through FSI; the Delta decays before it).

## 2. Two different quantities: efficiency denominator vs generator exposure

**Notation.** S = the set of generation units of the analysis dataset (units with a flatCAF); V = the chosen truth region (filter box, active TPC, or a future FV; a parameter).

**A. Signal truth denominator (for efficiency)**

  N_signal_truth(V; S) = number of **actual NC Δ → Nγ signal interactions in V** among the units of S, counted **per event** (one event counts once; §5), with weight 1 (the filter applies no weight, and `genweight` is unfilled).

Future efficiency (to be computed only after §4):

  ε(V; truth class t, reco class r) = N_selected_signal(V; t, r) / N_signal_truth(V; t)

where N_selected_signal counts signal events with the signal vertex in V, truth class t, `wc.valid == 1`, passing the frozen baseline with reco class r. `wc.valid == 0` events and events lost in Wire-Cell processing stay **in** N_signal_truth and fail the numerator. A selected event whose signal vertex is outside V is not numerator; it is "signal process outside the phase space" background. Candidate matching (`wc.T_match`/`T_overlap`) is an evaluation step, never used to choose the candidate; "unmatched" is its own class. Migration matrix M[t → r] = N[t → r] / N_signal_truth(V; t) with an explicit "not selected / not reconstructed" column.

**B. Generator exposure and physical production rate (NOT the efficiency denominator)**

  N_generated_throws(S) and POT(S) describe how much beam the filtered sample represents. They give

  R_signal(V) = N_signal_truth(V; S) / POT(S),    N_expected = R_signal(V) · POT_data

The 197,212,500 (flatCAF-bearing units) or 206,312,500 (all reco1 units) generated events are **not** the efficiency denominator: they include the ~99.993 % of throws that are not signal. They only fix the exposure (together with `mc.pot`) and the filter pass fraction.

**Measured values (unchanged):**

| quantity | value |
|---|---|
| generation units in S | 15,777 flatCAFs (6,626 with zero stored events) |
| N_signal_truth, V = filter box | 13,773 events (all stored events; 100 % have the signal vertex in the box) |
| N_signal_truth, V = provisional TPC box | 12,427 events (90.2 %) |
| N_generated_throws(S) | 197,212,500 (SAM reco1 parents; 12,500 per unit) |
| POT(S) = Σ`TotalPOT` = Σ SAM `mc.pot` | 2.83853e21 |
| R_signal (filter box) | 13,773 / 2.83853e21 = 4.852e-18 per POT (4.852e2 per 1e20 POT) |
| all reco1 units | 14,442 events, 206,312,500 throws, 2.96970e21 POT, 4.863e-18 per POT |

Rules for S: use the same set of units for numerator and POT. The 728 reco1 units without a flatCAF (669 events, 4.4 % of POT) are excluded from both; their pass fraction agrees with the rest (6.984e-5 vs 7.000e-5), so no visible bias, but this is an inference. **Not** to be used: all `wc.valid` events; all merged-CAF entries; the CAF `TotalGenEvents` (125 per file, 100 times below the true 12,500 per unit); a POT sum over only non-empty flatCAFs (zero-event files carry POT too). The filter-box region holds 100 % of the generated signal, the provisional TPC box 90.2 %; any smaller V is a truth cut that must be stated with the result.

## 3. Reading the official sample without Wire-Cell

The numbers above come from `scripts/official_ncdelta_truth_scan.py` (all 15,777 flatCAFs, minimal branches, 1,059 s) and `scripts/official_ncdelta_census_report.py` (`tables/official_ncdelta/official_ncdelta_census.json`; derived products outside Git in `$SP_DATA/official_gen2_ncdelta_truth/`). They are a **truth-only census**; no reconstruction efficiency exists yet.

## 4. What must still be settled before a number is quoted

1. The choice of V and of the truth 0p/1p/>=2p threshold (35 MeV provisional).
2. Why 728 units have no flatCAF, and confirmation of the production chain / GENIE tune (natural, unweighted branching is consistent with the data, not proven).
3. The Wire-Cell merged-CAF production of this sample (so that reco information exists for the numerator).

## 5. Events with more than one qualifying signal neutrino (provisional bookkeeping)

In the official sample 6 of 13,773 events contain two NC Δ-radiative neutrinos (12 neutrinos; `NATURAL_NCDELTA_CV_CROSSCHECK.md` repeats the check on the CV). Measured: in **every** one of the six events exactly one of the two neutrinos has its vertex inside the filter box (and the provisional TPC box); the other is a far rock interaction (e.g. x = −691 cm, z = 679 cm, or z = −423 cm) outside the filter box. Both interactions share the same truth proton category in 4 of the 6; the two vertices are never in the same region (0 of 6); the 0p/1p/≥2p category would differ between the two choices in 2 of the 6, so an arbitrary choice would not be harmless in general.

**Proposed deterministic rule (provisional, implemented in `truth_signal.signal_truth`):**

1. The efficiency denominator is **event-level**: an event counts once in N_signal_truth(V) if it has ≥ 1 qualifying signal neutrino with vertex in V.
2. The signal interaction of the event (for the truth proton category, vertex, photon energy, flavour) is the qualifying neutrino **inside the filter box**; if several are inside, the one with the lowest `rec.mc.nu` index, and the event is flagged (`n_signal_nu_in_box > 1`; none observed).
3. A qualifying neutrino outside V is never the signal interaction of the event even if it is the only one; the event is then "signal outside V".
4. `n_signal_nu_candidates` keeps the total count so the multi-signal events remain visible as a diagnostic.

The rule never silently picks "first": it is geometric and reproduces the physical choice in all six measured events. It must be revisited if a configuration with several in-V signal neutrinos appears.
