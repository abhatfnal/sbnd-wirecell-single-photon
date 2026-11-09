# Official Gen2 NC Delta signal: canonical truth table and denominators (truth only; no reconstruction efficiency exists yet)

Built by `scripts/build_official_signal_master.py` (library `signal_master.py`) from the flatCAF truth census (`$SP_DATA/official_gen2_ncdelta_truth/`) and the SAM metadata of the generation units. Outputs **outside Git**: `$SP_DATA/official_gen2_ncdelta_master/{signal_records,signal_events,units}.parquet` + `metadata.json` (git commit, SAM definition names, sha256 of every input and of `configs/signal_regions.yaml`, row counts, schema 1.0). Small summaries in Git: `tables/official_signal/denominators*.{json,csv}`.

| table | grain | rows |
|---|---|---|
| `signal_records` | one qualifying signal neutrino (NC and GENIE-record Δ-radiative); **both** neutrinos of the six multi-signal events are kept, `is_selected_signal` marks the deterministic event-level choice | 13,779 |
| `signal_events` | one stored signal event (the selected record + `n_signal_in_filter_box/active_tpc`) | 13,773 |
| `units` | one generation (reco1) unit: SAM `mc.pot`, `mc.generated_event_count`, flatCAF availability (`flatcaf_available` 15,777 / `no_flatcaf_child` 728) | 16,505 |

Key: `(reco1_unit, flatcaf, file_index, run, subrun, evt, signal_nu_index)`. Columns: Δ PDG/charge and decay nucleon, neutrino flavour/energy, vertex, `in_filter_box`, `in_active_tpc`, photon energy, truth protons (35 MeV, provisional) and 0p/1p/≥2p, primary π⁰/charged-pion/neutron counts, mode/resnum, SAM POT and generated events of the unit, flatCAF status. Three CC neutrinos with a Δ-radiative photon do **not** qualify (NC is part of the process test); they are excluded and counted in the metadata.

## Denominators (event level; region V from `configs/signal_regions.yaml`; no FV invented)
An event counts once in N_signal_truth(V) if ≥ 1 qualifying neutrino has its vertex in V; its class is that of the in-V neutrino (lowest index if several, flagged). N_signal_truth, POT and generated throws stay separate; **generated throws are never the efficiency denominator**. S = the 15,777 units with a flatCAF (the same units for the count and the POT).

| region | N_signal_truth | truth 0p / 1p / ≥2p | Δ0 / Δ+ | POT(S) | generated throws(S) |
|---|---|---|---|---|---|
| filter box | 13,773 | 6,501 / 6,160 / 1,112 | 7,599 / 6,174 | 2.83853e21 | 197,212,500 |
| provisional active-TPC box | 12,427 | 5,863 / 5,557 / 1,007 | 6,846 / 5,581 | 2.83853e21 | 197,212,500 |

Δ × proton category (filter box): Δ0 5,311 / 1,809 / 479, Δ+ 1,190 / 4,351 / 633; (TPC box): Δ0 4,783 / 1,626 / 437, Δ+ 1,080 / 3,931 / 570. R_signal(TPC box) = 12,427 / 2.83853e21 = 4.378e-18 per POT. To add an approved FV, add one entry to `configs/signal_regions.yaml`; nothing else changes.
