# Source semantics of `shw_sp_n_20mev_showers`, `shw_sp_n_20br1_showers` and `shw_sp_filled`

Date: 2026-11-10. Branch `analysis/ncdelta-shower-vertex-reco-audit-20261110`. Source: `HaiwangYu/wire-cell-toolkit`, branch `sbnd-wc-flatcaf`, **commit `4b6853d4`** (the producer-declared fg1 pin of the official Gen2 NC-Delta production; merged CAFs record `Trun.wct_version = sbnd-dlvtx-35-pre-master-merge-2026-09-02-424-g78f81c64`).
Files: `clus/src/NeutrinoTaggerSinglePhoton.cxx` (`PatternAlgorithms::singlephoton_tagger`, line 2268), `clus/src/NeutrinoShowerClustering.cxx` (`update_shower_maps`, line 403), `clus/src/NeutrinoKinematics.cxx` (T_kine shower rows), `clus/src/TaggerCheckNeutrino.cxx` (caller). Every statement is **SOURCE** unless marked **MEASURED** (checked on the official files by `scripts/shower_vertex_scan.py` and `scripts/shower_vertex_audit.py`). Nothing here changes any selection.
Complements `WIRECELL_SOURCE_CONVENTIONS_AUDIT.md` section 5 and `FROZEN_OTHER_BDT_SOURCE_AUDIT.md`.

## 1. The decisive fact: only showers whose START VERTEX is the main vertex are examined

`singlephoton_tagger` runs once per neutrino candidate with that candidate's `main_vertex`. Its shower loop is

```
auto mv_it = map_vertex_to_shower.find(main_vertex);
if (mv_it == map_vertex_to_shower.end()) return false;        // nothing filled: every shw_sp_* stays at its default
...
for (ShowerPtr shower : mv_it->second) { ... if (pdg != 11) continue; ... }
```

* `map_vertex_to_shower` is rebuilt by `update_shower_maps` (`NeutrinoShowerClustering.cxx:403-415`): `map_vertex_to_shower[start_vtx].insert(shower)` for every shower, where `start_vtx` is `shower->get_start_vertex_and_type().first`. So the set examined for a candidate is **exactly the showers whose recorded start vertex is that candidate's main vertex**, whatever the connection type (1 = direct, 2/3 = attached through other segments or by proximity, 4 = far cluster; `set_start_vertex(cur, 1)` at `NeutrinoShowerClustering.cxx:823/898` for the direct case).
* **Showers of the same candidate whose start vertex is any other vertex are never examined** (they still appear in `T_kine` / `T_pf` / `T_segment` and contribute to the reco energy). **Showers of another candidate never enter** (each candidate has its own graph, main vertex and map).
* If the main vertex has **no** shower in the map, the function returns before filling anything: `shw_sp_n_20mev_showers = 0`, `shw_sp_filled = 0`, all other `shw_sp_*` at their `NeutrinoTaggerInfo.h` defaults.

## 2. Which of those showers count

For each shower of the set (first pass; a throw-away `TaggerInfo` receives the intermediate fills):
1. **Typing:** the start segment's PDG `pdg = sg->particle_info()->pdg()`. `|pdg| == 2212` feeds the proton bookkeeping (`shw_sp_num_protons`, `shw_sp_proton_*`), `|pdg| == 13 || 211` the MIP bookkeeping; **`if (pdg != 11) continue;` - only electron-typed showers are sp-showers.** (A photon shower is typed 11 in this chain.)
2. **Energy:** `tmp_energy = kine_best` if `kine_best != 0`, else `kine_charge` (`shower_energy`, line 100). **`en20 = (tmp_energy > 20 MeV)` strictly.**
3. **bad-reconstruction flags** (the variable `badrecoN` is true when the shower is GOOD, i.e. `!bad_reconstruction_*`):
   * `badreco1 = !bad_reconstruction_sp` - br1_1 stem topology (`start_type == 1`, vertex degree 1, E < 120 MeV, <= 3 segments, no shower flag and stem > 10 cm; or stem > 80 cm), br1_2 a long muon-like track inside the shower, br1_3 a straight track near the far end of the stem.
   * `badreco2 = sg_at_main ? !bad_reconstruction_1_sp : true` - the PCA/stem-direction check; **evaluated only if the shower's start segment is directly attached to the main vertex (`sg_at_main`); otherwise it is TRUE (good) by construction**.
   * `badreco3 = !bad_reconstruction_2_sp` (eight br3 sub-checks), `badreco4 = !bad_reconstruction_3_sp` (br4_1, br4_2).
4. **Counters:** `num_20mev_shws += en20`; `num_badreco{1..4}_shws += badreco{k}`; **`num_20br1_shws += en20 && badreco1`**.
5. **Max shower:** among showers with `en20 && badreco1 && badreco3 && badreco4` ("good") the one with the largest energy; if none is good, the largest among `en20 && badreco1` ("ok"). `badreco2` is counted but **does not enter the max-shower choice**. `num_good_shws = good_showers.size()` is taken **before** an ok-shower is promoted, so `shw_sp_n_good_showers = 0` when the max shower came from the "ok" fallback.

## 3. The aggregate fields

| field | definition (source) | note |
|---|---|---|
| `shw_sp_n_20mev_showers` | number of electron-typed showers **at the main vertex** with energy > 20 MeV | the baseline's `n_20mev > 0` stage tests this field |
| `shw_sp_n_20br1_showers` | number of those that also have `badreco1` | the frozen final cut `== 1`; `20br1 <= 20mev`. It is **not** a truth photon multiplicity |
| `shw_sp_n_br1/2/3/4_showers`, `shw_sp_n_good_showers` | counters above | all over the same main-vertex shower set |
| `shw_sp_20mev_showers`, `shw_sp_br1..4_showers` | per-shower 0/1 flags in loop order (not indices) | one entry per electron-typed shower examined |
| `shw_sp_filled` | set to 1 (`NeutrinoTaggerSinglePhoton.cxx:1637`) only when a **max shower exists** and its detailed evaluation runs | if no shower is `en20 && badreco1`, `n_20mev` can be > 0 while `filled = 0` (the 46 'BDT not evaluable' events of the baseline) |
| `shw_sp_energy`, `shw_sp_shw_vtx_dis`, ... | filled for the max shower only (second pass) | `shw_vtx_dis` = |max-shower start point - main vertex| |

So the baseline stage `candidate -> n20mev` removes the events in which **no candidate has an electron-typed shower, with start vertex = main vertex and kine energy > 20 MeV**. "No shower reconstructed" is only one of several ways to fail it; an energetic, correctly reconstructed photon shower that is not at the main vertex fails it as well (see `SIGNAL_PHOTON_RECO_FAILURE_TAXONOMY.md`).

## 4. Can detached showers enter? Can showers of another candidate enter?

* A shower whose start vertex IS the main vertex but whose start point is displaced from it (conn-type 2/3, `shw_sp_shw_vtx_dis > 0`) **does** enter: this is the 'detached' state of Phase 8 (the `br2` fields stay at default 0 for it because `sg_at_main` is false). Phase 8 measured `br2` at default <=> `shw_vtx_dis != 0` for 5,006 of 5,007 events.
* A shower attached to a different vertex of the same graph, a shower in a cluster not associated with the candidate, and conn-type-4 (far) showers do **not** enter.
* Showers of another candidate never enter.

## 5. Related T_kine / T_pf facts used by the audit (SOURCE, `NeutrinoKinematics.cxx`)

`T_kine` shower rows of pool 2 ("remaining showers not yet attached to the traversal") carry `kine_energy_included = (vtx_type != 3 ? 1 : 3)`; showers with `vtx_type > 3` are skipped unless kept by the conn-4-near knob. So the shower rows of `T_kine` are a **superset** of the showers examined by `shw_sp` (all showers with connection type <= 3 of the candidate, not only those whose start vertex is the main vertex).

## 6. MEASURED consistency checks

See the section "Calibration of the reco-side proxy for the main-vertex shower set" of `SIGNAL_PHOTON_RECO_FAILURE_TAXONOMY.md` (added by the audit script): the number of electron-typed showers examined (`len(shw_sp_20mev_showers)`) and `n_20mev` are compared with what can be reconstructed from the stored `T_kine`, `T_pf` and `T_segment` tables.
