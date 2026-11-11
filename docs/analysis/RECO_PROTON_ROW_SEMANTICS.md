# What a reconstructed proton row (`wc.T_kine`) is: source facts, measured checks, and the analysis policy kept separate

Date: 2026-11-11. Branch `analysis/ncdelta-proton-truth-association-20261111`. Audit only: no selection, threshold or policy is changed. Statements are **SOURCE** (read in `HaiwangYu/wire-cell-toolkit` branch `sbnd-wc-flatcaf`, **commit `4b6853d4`**, the producer-declared fg1 pin), **MEASURED** (checked on the official Gen2 NC-Delta merged CAFs by `scripts/proton_truth_scan.py` / `scripts/proton_truth_audit.py`) or **POLICY** (an analysis choice, not a fact). Files: `clus/src/NeutrinoKinematics.cxx` (`fill_kine_tree`), `clus/src/PRSegmentFunctions.cxx` (`segment_determine_dir_track`, `segment_cal_4mom`, `cal_kine_range`, `segment_cal_kine_dQdx`), `clus/src/NeutrinoShowerClustering.cxx` (connection types). Complements `RECO_PROTON_DEFINITION_AUDIT.md` (Phase 2, BNB CV) and `WIRECELL_TRUTH_MATCH_SEMANTICS.md`.

## 1. Layout: one row = one reconstructed particle of one candidate  (SOURCE)

`T_kine` is written once per neutrino candidate (`nu_index`); every `kine_particle_*` / `kine_energy_*` vector is parallel and holds one element per **row**. A row is created at exactly one of these sites in `fill_kine_tree`, which also sets `kine_particle_pool`:

| pool | site | what the row is | `kine_energy_included` |
|---|---|---|---|
| 0 | first pass over the segments directly attached to the main vertex | a shower (if the segment is a shower start segment: `push_shower_kine`) or a track segment (`push_segment_kine`) | 1 |
| 1 | breadth-first walk of the remaining track graph from the main vertex | track segments (and showers reached in the walk) | 1 |
| 2 | "remaining showers not yet attached to the traversal" | a **leftover shower** (connection type <= 3, or a type-4 shower kept by the `kine_count_conn4_near` knob) | `vtx_type != 3 ? 1 : vtx_type`, i.e. **1 or 3** |
| 3 | orphan tracks (`kine_count_orphan_tracks`): confident, straight, long main-cluster segments that neither the walk nor a shower claimed | track | 1 |
| 4 / 5 | guard-freed track / near cross-cluster track (rare knobs) | track | 1 |

`kine_particle_id` is the display id of the particle's key segment, `kine_particle_cluster_id` the cluster of that segment, `kine_particle_nseg` the number of segments, `kine_particle_is_shower` = 1 for shower rows, 0 for track rows (`KineRowMembers.is_shower`). The row **index inside the candidate** (`kine_index` in `T_overlap` / `T_match` / `T_pf` / `T_segment`) is the vector element, **not** the display id: the display id is duplicated for a few rows (a shared shower start segment; 17 of 83,080 pool-2 rows in Phase 9), the element index never is.

## 2. How the type (PDG code) is assigned  (SOURCE)

* **Track rows:** `pdg = seg->particle_info()->pdg()`. The type is set in `segment_determine_dir_track` (`PRSegmentFunctions.cxx`) from a **dQ/dx-versus-residual-range template comparison** (`segment_do_track_pid` / `do_track_comp`: for the forward and backward direction it forms `sqrt(ks^2 + (ratio-1)^2)` against the muon, proton and electron templates; the best candidate becomes `pdg_code` and its score `particle_score`). Fallbacks of the same function: if `pdg_code == 0` the **median dQ/dx** is compared with the MIP value (`> 1.75 MIP` -> proton, `< 1.2 MIP` -> muon, `< 1.5 MIP` and length `< 4 cm` -> muon); a track `< 1.5 cm` with activity at only one end is typed proton (`> 1.75 MIP`) or pion (`< 1.2 MIP`); a track `> 10 cm` with a bad particle score becomes a shower (`pdg 11`). So **"proton" is an algorithmic dQ/dx-template/range call, not a truth statement**; there is no kaon in the default set.
* **Shower rows:** `pdg = shower_kine_pdg(shower)` = the start segment's live PDG (knob `shower_pdg_live`) or the cached `Shower::get_particle_type()`; a shower row can therefore also be typed 13, 211 or **2212** (a "shower" whose start segment was typed proton). The leftover-cluster branch of `NeutrinoShowerClustering.cxx` has a force-to-electron rule and a low-confidence proton case.
* **Consequence for the categoriser (SOURCE + POLICY):** `proton.classify_reco_protons` counts every row with `kine_particle_type == 2212`, track or shower, any pool, any `included`. That is a policy, not a source fact.

## 3. How the energy is assigned  (SOURCE)

`kine_energy_particle` [MeV] is `particle_info()->kinetic_energy()` for tracks and `Shower::get_kine_best()` for showers.
* **Track KE** is computed in `segment_cal_4mom` once the type is set: **range** (`cal_kine_range(track_length, pdg)` with the proton range function for pdg 2212) for a track `>= 4 cm`; **dQ/dx-integrated charge** (`segment_cal_kine_dQdx`) for a track `< 4 cm` or one flagged as a shower trajectory. So a proton KE is a range estimate, **a contained proton is measured, a proton that leaves or interacts is a lower limit**. (For the muon/pion/electron the same function uses their range function.)
* **Shower KE** (`kine_best`): charge-based or range-based energy of the shower object (`kine_energy_info` records which: 0 dQ/dx, 1 range, 2 charge, decided by equality of `kine_best` with `kine_charge` / `kine_range` to 0.1 %).
* **Rest/binding terms** (`kine_reco_add_energy`) are added to the candidate's `kine_reco_Enu`, not to the row KE: a proton row contributes its KE (+ the average binding energy in the Enu sum).

## 4. What `kine_energy_included` means  (SOURCE; the analysis policy is NOT decided here)

* Rows of pools 0, 1, 3, 4, 5 are pushed with `included = 1`. Only **pool-2 leftover shower rows** can carry another value, and the value is **3** exactly when the shower's start-vertex connection type is 3 (`vtx_type != 3 ? 1 : vtx_type`).
* **Connection type 3** (`NeutrinoShowerClustering.cxx`, `shower_clustering_in_other_clusters` and the `vertex-of-nearest-candidate` anchoring): the shower belongs to a cluster **other than the main (candidate) cluster** and is anchored to the **nearest vertex of the candidate graph, at a distance <= 80 cm** (> 80 cm is connection type 4, `connection_type = (min_dis > 80 cm) ? 4 : 3`). Connection type 1 is a shower starting at the vertex (directly attached); type 2 a shower created at a vertex of the same graph through the in-cluster bridging.
* **The flag is a misnomer.** The tree itself documents (`kine_energy_flagged` in the source) that the rows with `included != 1` **are** inside `kine_reco_Enu`; the sum is unconditional. They are the "satellite" showers of other clusters that the reconstruction counts into the neutrino energy.
* So `included == 3` is, physically/reconstructively: **"a leftover object (shower-typed) from a different cluster, attached to the candidate by proximity (<= 80 cm)"**. It carries a shower energy even when typed as a proton (the proton-typed, shower-row case).
* Not a source fact: whether the analysis should count these rows as reco protons (item E of the roadmap). This document and the whole phase only **diagnose** them (`included == 3` vs `!= 3` columns); the baseline keeps counting them.

## 5. Candidate bookkeeping  (SOURCE)

`nu_index` of every table is the candidate (position in `T_tagger` / `T_kine`). `T_match` level 1 gives, per candidate, one object per `T_kine` row (`kine_index`), and objects for clusters that no row accounts for (`nu_index = -1`, `cluster_id >= 0`, `kine_index = -1`: "rest of cluster"). The baseline reads the protons of the signal-matched candidate (`match_cand_nu`) or of the first/selected candidate; that choice and the rows' pools are policy (`CANDIDATE_POLICY_AUDIT.md`).

## 6. MEASURED checks on the official signal sample

Population: the 11,331 TPC-box signal events with a Wire-Cell candidate (11,783 candidates, **83,097 `T_kine` rows**; the production-missing event has no file). Numbers: `tables/proton_truth_association/row_semantics_checks.csv`, `proton_rows_by_pool_shower_included.csv`.

* **Rows typed proton:** 14,733 of 83,097 (17.7 %). Of these **8,356 (56.7 %) are shower rows** (`is_shower == 1`) and 6,377 are track rows. By pool: 5,965 pool 0, 405 pool 1, **8,348 pool 2**, 13 pool 3, 2 pool 4 (pool 5 never occurs among proton-typed rows). So "proton-typed" is, in more than half of the rows, a leftover shower whose start segment was typed proton.
* **`kine_energy_included` takes only the values 1 and 3** (no other value occurs). The **43,168 rows with `included == 3` are all pool-2 shower rows** (100 %), and **99.7 % of them lie in a cluster other than the candidate's main cluster** (`kine_main_vertex_id // 1000`), as the source predicts for connection type 3. For comparison, 87.8 % of the pool-2 rows with `included == 1` (connection type 1/2 or a kept type 4) are also outside the main cluster, and only 2.3 % of the pool-0/1 rows are. `included == 3` is therefore **a subset of "leftover shower in another cluster"**, not a synonym for it.
* **`included == 3` among proton-typed rows:** 8,238 of 14,733 (55.9 %) - but only **18.7 % of the proton-typed rows above 35 MeV** (the low-energy proton-typed rows are mostly leftover showers). Of the proton-typed rows above 35 MeV, 20.3 % are shower rows.
* **Level-1 association object:** exactly one `T_match` level-1 side-0 row per `(nu_index, kine_index)` in every event (0 duplicate keys); 320 of the 83,097 rows (0.4 %; median KE a few MeV, 2 of them typed proton) have **no level-1 object** at all (an object without imaging points); in 16 events the stored partner lists are inconsistent with their `..length` branches (the standard nested reader fails; the scan parses them per event, those rows keep `nmatch` but no partners and are classified `unmatched` with the reason recorded: 95 rows, 11 typed proton).
* **The rows reproduce the baseline:** counting `kine_particle_type == 2212 and kine_energy_particle > 35` over the rows of the signal-matched candidate (`match_cand_nu`) / the selected candidate (`sel_nu_index`) gives `match_np35` for all 10,831 and `sel_np35` for all 1,153 events, with **0 mismatches** (`summary.json: baseline_reproduction`). Nothing was re-selected.

## 7. Source fact versus analysis policy (the two are not mixed)

| item | source fact | analysis policy (not decided here) |
|---|---|---|
| what a proton row is | a `T_kine` row whose key segment/shower was typed 2212 by the dQ/dx-range template/fallback logic | counting every such row (track or shower, any pool, any `included`) above a KE threshold: the baseline rule (`proton.classify_reco_protons`) |
| which candidate's rows | rows are per candidate | candidate policy `any`; signal-matched candidate for the migration diagnostics |
| row KE | range (track >= 4 cm), dQ/dx charge (track < 4 cm, shower trajectory), shower `kine_best` | reading it as the proton KE; the 35 MeV (and 50 MeV) threshold |
| `included == 3` | pool-2 leftover shower of a different cluster attached by proximity (<= 80 cm); inside `kine_reco_Enu` | whether those rows are counted as protons (roadmap item E): only the diagnostic `included3_diagnostic_*.csv` exists |
| truth match | level-1 object = one `T_kine` row, partners ranked by point IoU (source order) | the 50 % ambiguity ratio (class G) and the high-confidence validation subset are analysis diagnostics |
