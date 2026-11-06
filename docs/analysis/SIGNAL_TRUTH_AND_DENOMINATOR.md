# NC Delta -> N gamma: signal truth object and efficiency denominator (proposal; nothing frozen; no efficiency computed)

Companion to `NCDELTA_GENERATOR_FILTER_AUDIT.md` (filter semantics and the measurements on the official sample) and `TRUTH_PROTON_DEFINITION_AUDIT.md`. Updated 2026-11-06 with direct measurements on the official Gen2 `EX_ncdeltarad` flatCAFs; no FV is introduced, every region below is a *parameter* of the denominator.

## 1. The signal truth object (process and topology are kept apart)

| field (`truth_signal.py`) | meaning | availability |
|---|---|---|
| `is_ncdelta_radiative` | **PROCESS**: an NC interaction with a status-1 photon whose mother is Delta0/Delta+ (the filter's own test) | with the GENIE record (`GenieEvtRecTree`, present in the official flatCAF and in the CV merged CAFs): **1 / 0, exact**. Without it (`recTree` only): tri-state, 1 only if the file is declared a filter stream, otherwise -1; never 0. |
| `delta_pdg`, `delta_charge`, `decay_nucleon_pdg` | Delta0 -> n gamma (2114, charge 0, n 2112) vs Delta+ -> p gamma (2214, +1, p 2212) | with the record: filled (official sample: 7,599 Delta0 / 6,174 Delta+). Without it: 0 = unavailable. |
| `photon_energy_mev`, `photon_energy_record_mev`, `n_primary_photons(_hard)` | hardest primary photon (generation-point energy) and the record photon | available |
| `genie_mode`, `resnum`, `neutrino_energy_gev`, `nu_pdg` | mode, resonance enum, true E_nu | available; **`resnum` is not a definition** (0 for only 97.66 % of the signal) |
| `signal_nu_index`, `n_signal_nu_candidates` | which neutrino of the event is the signal one | with the record: unique for 13,767 / 13,773 events, two qualifying neutrinos in 6 |
| `true_vertex_{x,y,z}`, `vtx_in_filter_box`, `vtx_in_active_tpc` | vertex and two **region flags** | available (signal: 100 % in the filter box, 90.2 % in the provisional TPC box) |
| `n_true_protons`, `true_proton_category` | **TOPOLOGY**: post-FSI primary protons above 35 MeV (provisional, configurable): 0p/1p/>=2p | available (signal: 47.2 % / 44.7 % / 8.1 %) |
| `is_ncdelta_rad_proxy`, `proxy_recovers_stream`, `proxy_agrees_with_record` | CAF-only proxy (NC, resonant, resnum 0, photon > 20 MeV) and its agreement with the record | diagnostic only; recovers 97.66 % of the official sample |

The decay channel (Delta0 -> n gamma vs Delta+ -> p gamma) and truth 0p/1p/>=2p are different axes and must never be equated: measured on the official sample, Delta0 events are 70 % truth-0p / 24 % 1p / 6 % >=2p, Delta+ events 19 % / 70 % / 10 % (the decay nucleon still goes through FSI; the Delta decays before it).

## 2. Denominator

Let **U** be the unfiltered generated sample of the Gen2 `prodgenie_corsika_proton_rockbox0p1` production and **F ⊂ U** the events passing `NCDeltaRadiative` (the `ncdeltarad` stream). The filter is a deterministic function of the generator record applied to every event of U before detector simulation, so every event of U outside F is, by the process definition, not signal: F alone carries the signal population, and no unfiltered event needs to be stored.

* **Generation units** (measured): SAM reco1 has 16,505 units; each has `mc.generated_event_count` = 12,500 and its own `mc.pot`; zero-survivor units **do** produce a reco1 file and (6,626 of them) a flatCAF with `TotalPOT > 0`.
* **Signal denominator in a truth region V** (V = filter box, active TPC, or a future FV; a parameter):

  N_gen(V; units S) = Σ over events e in the flatCAFs of S of  w_e · 1[ signal-neutrino vertex of e in V ],  w_e = 1 (the filter applies no weight, and `genweight` is unfilled)

  with **S = the set of generation units that have a flatCAF** (15,777 units, 13,773 events, Σ`TotalPOT` 2.83853e21, 197,212,500 generated events from the SAM parents). Using the same set of units for the numerator and the POT keeps them consistent. The 728 reco1 units without a flatCAF (669 events, 4.4 % of POT) are excluded from **both**; their pass fraction is statistically indistinguishable from the rest (13,773 / 197,212,500 = 6.984e-5 vs 7.000e-5 for all reco1), so dropping them does not visibly bias the population, but that is an inference, and whether those units failed or are pending is a production question.
* **Not** the denominator: all `wc.valid` events; all merged-CAF entries; the CAF `TotalGenEvents` (125 per file, 100 times below the true 12,500 per unit: **do not use**); the sum over *only non-empty* flatCAFs when computing POT (the zero-event files carry POT too).
* **Total efficiency** (to be computed only once the items in §4 are settled):

  ε_total(V; truth class t, reco class r) = N[ e in S, vertex in V, truth class t, `wc.valid == 1`, passes the frozen baseline with reco class r ] / N_gen(V, truth class t)

  `wc.valid == 0` events and events lost in Wire-Cell processing are in the denominator and fail the numerator (reconstruction inefficiency). A selected event whose signal vertex is outside V is **not** numerator; it is "signal process outside the phase space" background. Candidate matching (`wc.T_match`/`T_overlap`) is an *evaluation* step, never used to choose the candidate; the unmatched case is its own class. Migration matrix M[t -> r] = N[t -> r] / N_gen(V, t) with an explicit "not selected / not reconstructed" column.
* **Expected yield (not an efficiency):** N_exp = N_gen(V; S) · P_data / P_S with P_S = 2.83853e21 (Σ`TotalPOT` of S, = Σ SAM `mc.pot`).
* **Region matters:** the filter box (|x|,|y| <= 210, -1 <= z <= 510 cm) holds 100 % of the generated signal, the provisional TPC box 90.2 %. V = filter box reproduces the generated population exactly; any smaller V (TPC, FV) is a truth cut that must be stated with the result.

## 3. Reading the official sample without Wire-Cell

The numbers above come from `scripts/official_ncdelta_truth_scan.py` (all 15,777 flatCAFs, minimal branches, 1,059 s) and `scripts/official_ncdelta_census_report.py` (`tables/official_ncdelta/official_ncdelta_census.json`; derived products outside Git in `$SP_DATA/official_gen2_ncdelta_truth/`). They are a **truth-only census**; no reconstruction efficiency exists yet.

## 4. What must still be settled before a number is quoted

1. The choice of V and of the truth 0p/1p/>=2p threshold (35 MeV provisional).
2. Why 728 units have no flatCAF, and confirmation of the production chain / GENIE tune (natural, unweighted branching is consistent with the data, not proven).
3. The Wire-Cell merged-CAF production of this sample (so that reco information exists for the numerator).
