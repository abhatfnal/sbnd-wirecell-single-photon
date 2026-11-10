# Exclusive failure taxonomy of the signal photon at the `> 20 MeV shower` stage

Date: 2026-11-10. Branch `analysis/ncdelta-shower-vertex-reco-audit-20261110`. Audit only: no selection, cut, threshold or policy is changed (the baseline stage flags are inputs). Code: `scripts/shower_vertex_scan.py` (raw tables), `src/sbnd_single_photon/shower_audit.py` / `shower_tables.py` (classification), `scripts/shower_vertex_audit.py` (tables and figures). Source semantics: `WIRECELL_SINGLE_PHOTON_SHOWER_COUNT_SEMANTICS.md`.

## 1. Population and the number to explain

Official Gen2 NC-Delta signal, provisional TPC truth box: 12,427 events -> **11,331 have a Wire-Cell candidate** (`wc.valid`, >= 1 candidate) -> **8,080 have `shw_sp_n_20mev_showers > 0`** -> **3,251 events are lost at this stage** (the baseline first-failure `no_20mev_shower`). The production-missing event (run 317 / subrun 41 / evt 6753) has no candidate and stays in the denominator (it is part of the 1,096 no-candidate events, not of this population). Every one of the 3,251 is classified below; the classes sum to 3,251 exactly (asserted in the script and pinned in `tests/test_shower_audit.py`).

## 2. How the true signal photon is associated with the reconstruction (no spatial matching)

* **Truth photon.** `T_truth_pf` row with `pdg = 22`, `nu_row` = the signal neutrino's row of `T_truth_nu` (vertex match to the signal vertex within 0.01 cm: **11,331/11,331**), and `KE` within 0.5 MeV of the signal photon energy: **found for every event**; its `trackid` is the photon's G4 track id.
* **Conversion daughters.** The truth labeler (`T_truth_track`) assigns charge to the **ancestor/prong**: for a converted photon the e+/e- charge is carried under the photon's own row (`pdg 22`, `prong_trackid = ancestor_trackid = trackid`, `q_readout` is the full charge of the electromagnetic cascade; the end point of that row is the conversion point). So the stored truth matching does **not** need the e+/e- tracks: the blobs of the shower are labeled with the photon's track id. MEASURED: the photon row has `q_readout > 0` in 98.9 % of events and `q_in_blobs > 0` in 97.2 %; 97.3 % of events have at least one `T_overlap` row whose dominant truth track is the photon. (The rest are mostly photons that leave the volume.)
* **Reco pieces.** `T_overlap` rows (one per reco piece x dominant truth track) with `trackid` = the photon family give, per piece: the candidate (`nu_index`; **-1 = the cluster belongs to no candidate**), the cluster, the segment, `particle_id`, **`kine_index` (the T_kine row inside the candidate; -1 = no particle row)** and the charge `q`.
* **Dominant object.** The (candidate, `kine_index`) holding the largest photon charge **inside candidates** is the *dominant photon object*; its fraction of the in-candidate photon charge is `dominant_fraction`. The key is `kine_index` (not `particle_id`, which is duplicated for 17 of 83,080 pool-2 rows: a shared shower start segment). Its attributes come from the `T_kine` row (pdg, KE, `is_shower`, pool, `included`) and the stored particle-flow tree (`T_pf`).
* **Signal-matched candidate.** The baseline's `match_cand_nu` (the candidate whose dominant truth vertex lies within 5 cm of the signal vertex).

## 3. The taxonomy (mutually exclusive, exhaustive, source-supported)

Applied to the events whose candidates all have `shw_sp_n_20mev_showers == 0`; first match wins. The category names and order differ from the suggested list because the source (section 1 of the semantics document) shows that the dominant "reconstructed but not counted" mechanisms are different from the ones suggested.

| # | class | definition | maps to suggested |
|---|---|---|---|
| 1 | `photon_no_reco_charge` | no `T_overlap` piece carries the photon's charge | G |
| 2 | `photon_charge_outside_candidates` | < 50 % of the photon's reconstructed charge lies in clusters that belong to a candidate | G / F |
| 3 | `photon_fragmented` | inside candidates the dominant object holds < 50 % of the photon charge (split over several particles) | H |
| 4 | `photon_in_other_candidate` | the dominant object is in a candidate other than the signal-matched candidate | D |
| 5 | `photon_particle_row_missing` | the dominant object has no `T_kine` row (cluster present, no particle row) | F |
| 6 | `photon_as_track` | the dominant `T_kine` row is not a shower row | E |
| 7 | `photon_shower_typed_non_electron` | a shower row typed other than electron (13, 211, 2212, ...) | E |
| 8 | `photon_shower_below_20MeV` | an electron shower with E_reco <= 20 MeV | B |
| 9 | `photon_shower_not_in_main_vertex_set` | an electron shower with E_reco > 20 MeV: by the source rule it is **not counted because it is not in the main vertex's shower set** | C |

The 50 % cuts (classes 2 and 3) are analysis choices; the class counts at other values are in `taxonomy_threshold_sensitivity.csv` (e.g. `dominant_frac_min` 0.33 / 0.66 moves `photon_fragmented` 95 / 907 and mostly exchanges events with `photon_as_track` and `photon_shower_typed_non_electron`; the `photon_shower_not_in_main_vertex_set` class varies between 473 and 640, and `photon_shower_below_20MeV` stays 36-43). Suggested category A (`sp_shower_pass`) is the pass side (section 5).

## 4. Calibration of the reco-side proxy for the main-vertex shower set (MEASURED)

* The stored candidate fields are consistent with the source: `shw_sp_n_20mev_showers` equals the sum of the per-shower flag list for all 11,783 candidates (100 %), and `A_n20mev` equals "any candidate has n20 > 0" for all 11,331 events.
* The shower start vertex is **not** stored in the CAF; the `T_kine` shower rows are a **superset** of the examined set: a pdg-11 shower row with E > 20 MeV exists in 9,246 candidates (8,064 + 1,182) while only 8,159 have n20 > 0: **1,182 candidates have an energetic electron shower row that the tagger did not count** (the source-predicted not-in-main-vertex-set population), and 95 candidates count a shower for which no such row exists (typing/energy differences between the start segment and the T_kine row).
* The PF-tree state of a shower row is a validated attachment descriptor: for the max shower of 7,947 filled candidates, a shower at PF depth 0 (`root`) has `shw_sp_shw_vtx_dis == 0` in 98.7 % (4,125/4,180); a shower below a **root-level pseudo photon node** (`photon_node_at_vertex`) is detached (`shw_vtx_dis > 0`) in **100 %** (2,556/2,556); a shower deeper in the tree is mixed (718 attached, 490 detached). The PF pseudo photon node is Wire-Cell's representation of an invisible photon between the vertex and a displaced shower.

## 5. Exact accounting: the 3,251

| class | all | truth 0p | truth 1p | truth >=2p | Delta0 | Delta+ |
|---|---|---|---|---|---|---|
| `photon_shower_typed_non_electron` | **961** (29.6 %) | 325 | 530 | 106 | 419 | 542 |
| `photon_shower_not_in_main_vertex_set` | **567** (17.4 %) | 120 | 364 | 83 | 226 | 341 |
| `photon_fragmented` | **492** (15.1 %) | 277 | 193 | 22 | 283 | 209 |
| `photon_as_track` | **424** (13.0 %) | 225 | 171 | 28 | 263 | 161 |
| `photon_charge_outside_candidates` | 329 (10.1 %) | 163 | 151 | 15 | 196 | 133 |
| `photon_no_reco_charge` | 275 (8.5 %) | 79 | 173 | 23 | 120 | 155 |
| `photon_particle_row_missing` | 162 (5.0 %) | 56 | 92 | 14 | 88 | 74 |
| `photon_shower_below_20MeV` | **40 (1.2 %)** | 9 | 27 | 4 | 12 | 28 |
| `photon_in_other_candidate` | 1 (0.03 %) | 0 | 1 | 0 | 0 | 1 |
| **total fail** | **3,251** | 1,254 | 1,702 | 295 | 1,607 | 1,644 |

As fractions of the 11,331 candidate-stage events: pass 71.3 %; typed non-electron 8.5 %, not in main-vertex set 5.0 %, fragmented 4.3 %, track 3.7 %. **Only 1.2 % of the failures (0.4 % of candidate-stage events) are a genuinely sub-20 MeV reconstructed shower.** The classes split by truth topology very differently (columns of `taxonomy.csv`): truth 0p fails mostly as `fragmented` (22 % of its failures), `as_track` (18 %) and `typed_non_electron` (26 %), whereas truth 1p / >=2p lose 21 % / 28 % of their failures to `not_in_main_vertex_set` (0p: 10 %).

## 6. What the passing events look like

Of the 8,080 passing events, 5,423 pass through a clean energetic electron shower that is the dominant photon object of a passing candidate; **2,657 (23.4 % of candidate-stage events; 28.0 % of truth 0p) pass although the dominant photon object is not that**. In those, the photon object state is: fragmented 1,622, typed non-electron 409, track 300, row missing 220, charge outside candidates 66, no charge 30, electron shower not in the set (a different candidate state) 6, below 20 MeV 4 (`pass_not_via_breakdown`). So "passing the `> 20 MeV shower` stage" is in a quarter of the cases carried by a **fragment of the photon or by other showers**, not by a cleanly reconstructed photon shower. (The `n_20br1 == 1` final cut and the BDTs act on whatever object is selected.) **The later stages remove them:** of the 1,153 final-selected events, **1,131 (98.1 %) have the clean energetic electron photon shower as the dominant photon object** (truth 0p 469 / 476, 1p 579 / 594, >=2p 83 / 83) and only 22 pass without it (14 fragmented, 4 row missing, 2 typed non-electron, 2 track); the final selection rate is 1,131 / 5,423 = 20.9 % for the clean-photon passes but 22 / 2,657 = 0.8 % for the others.

## 7. Reading guide
* Counting classes 7 and 6 together (typed non-electron or track): 1,385 events (42.6 % of the failures) have a photon object that the pattern recognition typed as a muon / pion / proton, as a shower (961) or as a track (424).
* Classes 3 and 2 (fragmented or mostly outside candidates): 821 (25.3 %).
* Class 9 (an energetic electron shower exists but is not at the main vertex): 567 (17.4 %), of which 554 sit below another particle in the PF tree.
* Class 8 (a real low-energy reconstruction): 40 (1.2 %).
