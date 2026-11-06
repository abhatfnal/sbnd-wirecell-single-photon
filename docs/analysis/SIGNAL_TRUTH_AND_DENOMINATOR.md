# NC Delta -> N gamma: signal truth object and efficiency denominator (proposal; nothing frozen; no efficiency computed)

Companion to `NCDELTA_GENERATOR_FILTER_AUDIT.md` (what the filter does) and `TRUTH_PROTON_DEFINITION_AUDIT.md` (truth proton categories). No FV is introduced; every region below is a *parameter* of the denominator, not a decision.

## 1. The signal truth object (process and topology are kept apart)

| field (`truth_signal.py`) | meaning | availability |
|---|---|---|
| `is_ncdelta_radiative` | **PROCESS** NC Delta -> N gamma in the sense of the generator filter (an exiting photon with a Delta0/Delta+ mother in an NC interaction, mother vertex in the filter box) | `1` only for events of the official `ncdeltarad` stream (declared by `from_filter_stream=True`); otherwise `-1` = unknown. Never `0`. |
| `is_ncdelta_rad_proxy`, `proxy_recovers_stream` | CAF-only proxy (NC, resonant, `resnum == 0`, >=1 primary photon above 20 MeV, provisional) and its recovery of the stream | available; diagnostic |
| `delta_pdg`, `delta_charge`, `decay_nucleon_pdg` | Delta0 -> n gamma vs Delta+ -> p gamma | **not available from the CAF** (0). Needs the GENIE record / filter diagnostics tree. |
| `photon_energy_mev`, `n_primary_photons(_hard)` | hardest primary photon of the signal neutrino (generation-point energy) | available |
| `genie_mode`, `resnum`, `neutrino_energy_gev`, `nu_pdg` | interaction mode, resonance enum, true E_nu | available |
| `true_vertex_{x,y,z}`, `vtx_in_filter_box`, `vtx_in_active_tpc` | true interaction vertex and two **region flags** (filter box; provisional TPC box) | available |
| `n_true_protons`, `true_proton_category` | **TOPOLOGY**: post-FSI primary protons above `proton_ke_mev` (35 MeV default), 0p/1p/>=2p | available |

`Delta0 -> n gamma` / `Delta+ -> p gamma` (decay channel) and truth `0p/1p/>=2p` (final-state multiplicity) are different axes. They must never be equated: a Delta0 event can have truth 1p or >=2p from FSI, and a Delta+ -> p gamma event can be truth 0p if the proton is below threshold or absorbed.

## 2. Denominator

Let **U** be the unfiltered generated sample (all events produced by the Gen2 `prodgenie_corsika_proton_rockbox0p1` generator for the production), with generated POT P_U. The filter `NCDeltaRadiative` is a deterministic function of the generator record evaluated on every event of U **before** detector simulation. Let **F ⊂ U** be the events it passes (the `ncdeltarad` stream).

* Every event of U outside F is, **by the agreed process definition**, not signal; no information is lost by not storing it. So the filtered stream *can* provide the denominator, provided it is complete (below).
* **Signal denominator in a truth region V** (V = filter box, active TPC, or a future FV; a parameter):

  N_gen(V) = sum over e in F of  w_e · 1[ signal-neutrino vertex of e in V ],     with w_e = 1 (the filter applies no weight; an enhanced branching ratio would need w_e ≠ 1, see audit §3.7)

  taken over **filter-passing events**, not over events that happen to survive to the merged CAF.
* **Completeness requirement (must be shown, not assumed):** N_F must be the number of events written by the filter stage (before g4/detsim/reco1/reco2/CAF/Wire-Cell) for exactly the validated file set. Events lost later in the chain (the Aurora campaign lost 1 of 26,745 at Wire-Cell, and some files are unreadable) are **reconstruction inefficiency**, not a reduction of the denominator.
* **Not** the denominator: all `wc.valid` events; all merged-CAF entries; all events of the stream whose vertex is anywhere (unless V is defined to be that).
* **Total efficiency** (to be computed only after the items in §4 are settled):

  ε_total(V; truth class t, reco class r) = N[ e in F, vertex in V, truth class t, `wc.valid == 1`, passes the frozen baseline with reco class r ] / N_gen(V, truth class t)

  `wc.valid == 0` events and events with no merged-CAF entry are in the denominator and fail the numerator. Selected events whose signal vertex is outside V are **not** efficiency numerator; they are "signal-process outside phase space" background. Candidate matching (does the selected candidate belong to the signal neutrino?) is an *evaluation* choice using `wc.T_match`/`T_overlap`, never used to pick the candidate; the unmatched case is reported as its own class. The migration matrix is M[t -> r] = N[t -> r] / N_gen(V, t) with an explicit row for "not selected / not reconstructed".
* **Expected yield (not an efficiency):** N_exp = N_gen(V) · P_data / P_U, with P_U the generator POT of *all* unfiltered inputs including those with an empty filter output (audit §4: the CAF-stored files alone can undercount P_U; 39 % of the Aurora NC files hold 0 events).

## 3. Why the filter semantics matter for V

The filter box (|x|,|y| <= 210, -1 <= z <= 510 cm, applied to the photon's mother vertex) is larger than the active TPC (|x|,|y| < 200, 0 < z < 500). `V = filter box` therefore reproduces the generated population exactly; any smaller V (active TPC or FV) is a cut on truth that must be stated with the result. An event whose Delta-photon parent lies outside the filter box was vetoed at generation and does not exist in F, so it can never be in a denominator built from F.

## 4. What must be settled before a number is quoted

1. Production chain, GENIE tune/branching ratio and weights for the official definition (audit §6.1-6.2).
2. Filter-stage event counts and the unfiltered-input POT / generated-event bookkeeping, including empty outputs (audit §4, §6.3).
3. The choice of V (filter box vs active TPC vs future FV) and of the truth 0p/1p/>=2p threshold.
4. Which neutrino is the signal neutrino when the proxy fails or several qualify (`signal_nu_index`, `n_signal_nu_candidates`).
