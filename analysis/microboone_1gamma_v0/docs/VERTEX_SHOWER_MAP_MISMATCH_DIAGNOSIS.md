# Vertex-Shower Map Mismatch Diagnosis

**Date**: 2026-10-05
**Campaign**: SBND `baseline_v0` — WCT `251ff143`, sbndcode `v10_14_02_04`
**Sample**: 59 NC Delta radiative events
**Subject**: Source-level and event-level diagnosis of 4 `SHOWER_RECONSTRUCTED_ELSEWHERE_UNASSOCIATED` events

**Constraints**: All frozen files read-only. No WireCell rerun. No BDT retrain. No threshold changes.
No truth quantities substituted for reconstruction quantities.

---

## Step 1: The four events

All four events from `tables/main_vertex_shower_failure_diagnostics.csv`:

| evt_idx | run | subrun | event | neutrino vertex (x,y,z) cm | T_tagger cluster_id | cluster npoints | cluster len |
|---------|-----|--------|-------|---------------------------|---------------------|-----------------|-------------|
| evt_0014 | 50 | 0 | 449 | (−106.0, 185.3, 367.1) | 1 | 941 | 42.2 cm |
| evt_0020 | 60 | 0 | 153 | (−14.5, 137.0, 312.5) | 3 | 577 | 47.8 cm |
| evt_0054 | 120 | 0 | 529 | (−67.3, −45.4, 209.4) | 1 | 525 | 40.9 cm |
| evt_0058 | 120 | 0 | 664 | (−68.4, −42.7, 191.5) | 2 | 627 | 29.6 cm |

All 4 events: `shw_sp_filled=0`, `shw_sp_n_20mev_showers=0`, neutrino candidate found (T_tagger present).

**T_cluster note (evt_0020, evt_0058)**: T_cluster contains multiple clusters with `is_main=1`.
For evt_0020, clusters 1 and 2 (5 npoints each, `in_scope=0`) are out-of-scope stubs from a
different beam crossing; cluster 3 (577 npoints, `in_scope=1`, `fc=1`) is the actual neutrino
candidate cluster. For evt_0058, cluster 1 (8 npoints) is matched to a low-PE flash (248 PE);
cluster 2 (627 npoints, `fc=1`) is matched to the main beam flash (16517 PE) and is the
neutrino candidate. In both cases, `T_tagger.cluster_id` correctly identifies the large in-scope
physics cluster.

---

## Step 2: singlephoton_tagger() association logic

Source: `wct/clus/src/NeutrinoTaggerSinglePhoton.cxx`

The critical path in `singlephoton_tagger()`:

```cpp
// NeutrinoTaggerSinglePhoton.cxx:2354-2362
auto mv_it = map_vertex_to_shower.find(main_vertex);
if (mv_it == map_vertex_to_shower.end()) return false;   // LINE 2355: early exit

// Only if main_vertex found:
for (ShowerPtr shw : mv_it->second) {                   // LINE 2362
    // quality checks, energy > 20 MeV, etc.
}
```

`map_vertex_to_shower` is a `VertexShowerSetMap` keyed by shower's `start_vertex` pointer.
It is built by `update_shower_maps()` in `NeutrinoShowerClustering.cxx:403-447`:

```cpp
// NeutrinoShowerClustering.cxx:403-447 (simplified)
for (auto shower : all_showers) {
    VertexPtr vtx = shower->get_start_vertex_and_type().first;
    map_vertex_to_shower[vtx].insert(shower);
}
```

The map can only find a shower at `main_vertex` if the shower's `start_vertex` IS `main_vertex`.

`shw_sp_filled=1` is set at `NeutrinoTaggerSinglePhoton.cxx:1637` inside `mip_identification_sp()`,
which is only called after `singlephoton_tagger()` succeeds in finding and selecting a shower.
Because `singlephoton_tagger()` returns false at line 2355 for all 4 events, `mip_identification_sp()`
is never reached and `shw_sp_filled` stays 0.

---

## Step 3: NeutrinoKinematics traversal

Source: `wct/clus/src/NeutrinoKinematics.cxx`

**First pass** (segments directly at `main_vertex`, lines 313-342):
```cpp
for (auto ei : sorted_out_edges(main_vertex->get_descriptor(), graph)) {
    SegmentPtr seg = graph[ei].segment;
    auto it = map_sg_shower.find(seg);
    if (it != map_sg_shower.end()) {
        push_shower_kine(it->second);
        ktree.kine_energy_included.push_back(1);     // shower direct at main_vertex
    } else {
        // track segment: add to BFS queue
        segments_to_be_examined.emplace_back(other_vtx, seg);
    }
}
```

**BFS traversal** (lines 348-420): for track segments found at `main_vertex` and descendants:
```cpp
auto it2 = map_sg_shower.find(curr_sg);
if (it2 == map_sg_shower.end()) {
    // another track segment: continue BFS
} else {
    const ShowerPtr& shower = it2->second;
    if (!used_showers.count(shower)) {
        push_shower_kine(shower);
        ktree.kine_energy_included.push_back(1);     // shower via BFS: STILL = 1 !!
        used_showers.insert(shower);
    }
}
```

**Critical observation**: NeutrinoKinematics uses `map_sg_shower` (segment → shower), not
`map_vertex_to_shower` (vertex → shower). Any shower reachable by graph traversal from
`main_vertex` — including showers connected via track-like segments — is found with
`kine_energy_included = 1`.

This is why all 4 events have `kine_energy_included = 1` for their dominant EM particle while
`shw_sp_filled = 0`: NeutrinoKinematics found the shower via BFS, but singlephoton_tagger
requires `map_vertex_to_shower[main_vertex]` to be non-empty.

---

## Step 4: Event-level object matching

| Field | evt_0014 | evt_0020 | evt_0054 | evt_0058 |
|-------|----------|----------|----------|----------|
| neutrino vertex | (−106.0, 185.3, 367.1) | (−14.5, 137.0, 312.5) | (−67.3, −45.4, 209.4) | (−68.4, −42.7, 191.5) |
| T_tagger cluster_id | 1 | 3 | 1 | 2 |
| cluster npoints | 941 | 577 | 525 | 627 |
| cluster length | 42.2 cm | 47.8 cm | 40.9 cm | 29.6 cm |
| cluster fc | 1 | 1 | 1 | 1 |
| dominant EM (pdg=11) energy | 121.6 MeV | 153.8 MeV | 53.2 MeV | **449.0 MeV** |
| kine_energy_included | 1 | 1 | 1 | 1 |
| other particles (incl=1) | 107.3 MeV muon, 70.1 MeV proton | 267.6 + 70.7 MeV protons | 257.4 MeV proton | none |
| shw_sp_filled | 0 | 0 | 0 | 0 |
| shw_sp_n_20mev_showers | 0 | 0 | 0 | 0 |
| map_vertex_to_shower[main_vertex] | absent | absent | absent | absent |

Inferred topology for all 4 events: the photon shower has a **conversion gap** — a short
track-like segment between `main_vertex` (the neutrino interaction point) and the shower
start (the photon conversion point V1). This gap is traversed by NeutrinoKinematics BFS
(finding the shower at V1 with `kine_energy_included=1`) but causes the shower to be
assigned `start_vertex = V1` (not `main_vertex`) by the shower clustering algorithm.

---

## Step 5: Failure mechanism classification

**All 4 events**: `SHOWER_ASSOCIATED_TO_DIFFERENT_VERTEX`

Root cause: `shower_clustering_with_nv_in_main_cluster()` at
`NeutrinoShowerClustering.cxx:852-1054` performs a BFS from `main_vertex`. When a shower
segment is reached via one or more track-like segments (the photon conversion gap), the BFS
assigns `shower->set_start_vertex(parent_vtx, 1)` where `parent_vtx` is the vertex V1
adjacent to the shower segment — NOT `main_vertex` (NeutrinoShowerClustering.cxx:928-932):

```cpp
// NeutrinoShowerClustering.cxx:928-932 (BFS inner loop, simplified)
if (curr_sg->flag_shower()) {
    ShowerPtr shower = new_shower(curr_sg);
    shower->set_start_vertex(parent_vtx, 1);   // parent_vtx = V1, NOT main_vertex
    // ...
}
```

The conversion gap segment is then absorbed into the shower by
`shower->complete_structure_with_start_segment(...)`, claiming it in `map_segment_in_shower`.
Subsequently, `shower_clustering_connecting_to_main_vertex()` (line 1056) finds the gap segment
already claimed in `map_segment_in_shower` and skips it. Result: no shower is created with
`start_vertex = main_vertex`, so `map_vertex_to_shower[main_vertex]` is absent.

After `update_shower_maps()` runs:
- `map_vertex_to_shower[V1]` contains the photon shower
- `map_vertex_to_shower[main_vertex]` is absent or empty
- `singlephoton_tagger()` returns false at line 2355 without inspecting any shower
- `NeutrinoKinematics` BFS finds the shower at V1 via `map_sg_shower[gap_segment]`

---

## Step 6: Minimal proposed code change (no implementation)

The smallest change is in `singlephoton_tagger()` in `NeutrinoTaggerSinglePhoton.cxx`.
Instead of requiring `map_vertex_to_shower[main_vertex]` to be non-empty, also check showers
at vertices one track-hop from `main_vertex`:

```cpp
// Replace lines 2354-2362 with:
std::set<ShowerPtr> candidate_showers;

auto mv_it = map_vertex_to_shower.find(main_vertex);
if (mv_it != map_vertex_to_shower.end())
    candidate_showers.insert(mv_it->second.begin(), mv_it->second.end());

// One-hop extension: showers at V1 = neighbor of main_vertex via track segment
for (auto ei : sorted_out_edges(main_vertex->get_descriptor(), graph)) {
    SegmentPtr gap_seg = graph[ei].segment;
    if (!gap_seg->flag_shower()) {                    // track-like = possible conversion gap
        VertexPtr v1 = find_other_vertex(graph, gap_seg, main_vertex);
        auto it2 = map_vertex_to_shower.find(v1);
        if (it2 != map_vertex_to_shower.end())
            candidate_showers.insert(it2->second.begin(), it2->second.end());
    }
}
if (candidate_showers.empty()) return false;

// Replace "for (ShowerPtr shw : mv_it->second)" with:
for (ShowerPtr shw : candidate_showers) {
    // existing quality checks unchanged
}
```

Estimated scope: ~15 lines changed in one function. The shower clustering algorithm itself
is unchanged. The shower's `start_vertex` is still V1 (physically correct — that IS the
conversion point), but singlephoton_tagger now looks one step farther.

**Risk**: This could also pick up track-like segments from protons or muons that happen to
be followed by an EM shower (secondary interactions). Those showers would then pass the
existing 20 MeV and quality cuts in singlephoton_tagger. The existing `mip_identification_sp()`
selection criteria are the defense against false positives — no threshold changes needed.

**Alternative (harder)**: Modify `shower_clustering_with_nv_in_main_cluster` to additionally
insert conversion-gap showers into `map_vertex_to_shower[main_vertex]` alongside `[V1]`.
This would be 1 line in the clustering algorithm but has broader effects (shower appears
under 2 vertex keys; downstream code that iterates the map must handle duplicates).

**Recommended**: The singlephoton_tagger extension (first option) is safer and more local.

---

## Step 7: Regression test

**Best candidate: `evt_0058`** (run=120, subrun=0, event=664)

Justification:
- Simplest topology: only 3 T_kine particles (1 dominant EM + 2 tiny companion-cluster EM)
- Largest EM shower: 449 MeV — unambiguous signal, far above 20 MeV threshold
- Clean expected outcome: after fix, `shw_sp_n_20mev_showers` should change 0→≥1,
  `shw_sp_filled` should change 0→1
- Single-file test: `baseline_v0/ncdelta_50evt/wirecell/evt_0058/tracking-pr.root`
- Current frozen state (before fix): `shw_sp_filled=0`, `shw_sp_n_20mev_showers=0`
- Expected post-fix state: `shw_sp_filled=1`, `shw_sp_n_20mev_showers≥1`

The test verifies that the 449 MeV photon shower is now accessible to `singlephoton_tagger()`
via the one-hop map extension, without requiring any change to the frozen `tracking-pr.root` file.

**Alternative candidate: `evt_0014`** (run=50, subrun=0, event=449) — useful as a second case
because it includes a muon-like track (107.3 MeV, pdg=13) at the vertex, which tests that
the one-hop extension does not incorrectly route the muon's downstream segments as shower
candidates when there is no shower at V1.

---

## Final report (9 items)

### 1. Four RSEs

| evt_idx | run | subrun | event |
|---------|-----|--------|-------|
| evt_0014 | 50 | 0 | 449 |
| evt_0020 | 60 | 0 | 153 |
| evt_0054 | 120 | 0 | 529 |
| evt_0058 | 120 | 0 | 664 |

### 2. Do all four share the same root cause?

**Yes.** All 4 events share a single mechanism: the photon shower has a conversion gap topology
(a track-like segment between the neutrino vertex and the photon conversion point). The BFS in
`shower_clustering_with_nv_in_main_cluster` assigns `start_vertex = V1` (the conversion point)
to the shower, rather than `main_vertex`. All further consequences follow deterministically.

### 3. Exact reason NeutrinoKinematics sees the shower while singlephoton_tagger does not

**NeutrinoKinematics** (`NeutrinoKinematics.cxx:399-418`): uses `map_sg_shower` (segment→shower
mapping) during BFS traversal. The BFS follows track-like segments (the conversion gap) from
`main_vertex` to V1, finds the shower segment at V1 in `map_sg_shower`, and assigns
`kine_energy_included = 1`. Any shower reachable by graph traversal from `main_vertex` is found.

**singlephoton_tagger** (`NeutrinoTaggerSinglePhoton.cxx:2354-2362`): uses `map_vertex_to_shower`
(vertex→shower mapping). Only showers whose `start_vertex` IS `main_vertex` are found.
The shower at V1 is keyed to `map_vertex_to_shower[V1]`, not `map_vertex_to_shower[main_vertex]`.

This is a lookup-key granularity mismatch: NeutrinoKinematics traverses the graph; singlephoton_tagger
looks up a specific vertex pointer.

### 4. Source code location of the discrepancy

| File | Lines | Role |
|------|-------|------|
| `wct/clus/src/NeutrinoShowerClustering.cxx` | 928-932 | BFS assigns `start_vertex = V1` (conversion point, not `main_vertex`) |
| `wct/clus/src/NeutrinoTaggerSinglePhoton.cxx` | 2354-2355 | Early exit: `map_vertex_to_shower.find(main_vertex) == end()` |
| `wct/clus/src/NeutrinoKinematics.cxx` | 399-418 | BFS finds shower via `map_sg_shower`, sets `kine_energy_included=1` |
| `wct/clus/src/NeutrinoShowerClustering.cxx` | 403-447 | `update_shower_maps()`: map keyed by shower's stored `start_vertex` |

### 5. SBND-specific or generic Wire-Cell logic?

**Generic.** All four source files (`NeutrinoShowerClustering.cxx`, `NeutrinoTaggerSinglePhoton.cxx`,
`NeutrinoKinematics.cxx`) are in `wct/clus/src/` which is detector-agnostic WCT code. The same
code ran on MicroBooNE data. The conversion-gap topology is a physical property of photon showers
(the photon travels some distance before pair-producing), not an SBND artifact.

However, the **rate** at which this mechanism fires depends on detector geometry (gap size relative
to reconstruction resolution) and on the NC Delta photon energy distribution. The SBND sample
has photon energies 53–449 MeV; the fraction of conversions reconstructed as track-like segments
in the gap will depend on Wire-Cell's `flag_shower` threshold, which is the same algorithm in
both detectors.

This failure mode likely exists in MicroBooNE NC Delta analysis as well, but may be less visible
because MicroBooNE uses a higher statistics signal sample with different composition.

### 6. Smallest proposed code change

~15 lines in `singlephoton_tagger()` in `NeutrinoTaggerSinglePhoton.cxx` (lines 2354-2362):
extend the vertex-shower map lookup to include vertices one track-hop from `main_vertex`.
See Step 6 above for the exact pseudocode. No changes to shower clustering, shower clustering
parameters, map structure, or BDT thresholds.

### 7. Best one-event regression test

**evt_0058** (run=120, subrun=0, event=664):
- 449 MeV photon shower, 3 total T_kine particles
- File: `baseline_v0/ncdelta_50evt/wirecell/evt_0058/tracking-pr.root`
- Before fix: `shw_sp_filled=0`, `shw_sp_n_20mev_showers=0`
- After fix: `shw_sp_filled` should be 1, `shw_sp_n_20mev_showers` should be ≥1

### 8. How many of the 4 events are recoverable?

**All 4 are recoverable** by the proposed fix, pending the BDT selection:

| Event | EM shower energy | Outcome after fix |
|-------|-----------------|-------------------|
| evt_0014 | 121.6 MeV | Likely passes `shw_sp_n_20mev_showers>0`; BDT selection TBD |
| evt_0020 | 153.8 MeV | Likely passes; BDT selection TBD |
| evt_0054 | 53.2 MeV | Marginally passes `shw_sp_n_20mev_showers>0` (53 > 20 MeV) |
| evt_0058 | 449.0 MeV | Clearly passes; highest expected BDT signal score |

Note: passing `shw_sp_n_20mev_showers>0` is necessary but not sufficient for BDT evaluation.
After `shw_sp_filled=1`, all other `shw_sp_*` inputs must also be populated. The BDT cut
flow (`numu > 0.4`, `other > 0.2`, `ncpi0 > −0.05`, `nue > −1.0`, `shw_sp_n_20br1_showers==1`)
cannot be predicted without running the fixed code. Do NOT run the fix in `baseline_v0`.

### 9. Priority relative to the 10 companion-cluster events

**Recommend Fix 2 (vertex-shower map, 4 events) first**, then Fix 1 (companion cluster, 10 events).

Rationale:
- Fix 2 is fully traceable to a single code change in one function (~15 lines)
- Fix 1 requires extending `singlephoton_tagger()` to access companion cluster showers, which
  touches more code paths and requires understanding the companion cluster structure
- The evt_0058 regression test is clean (449 MeV, 3 particles, clear before/after state)
- Fix 2 does not interfere with Fix 1 — they are orthogonal code paths
- Fix 1 has higher total impact (10 events vs 4), but both fixes require a new WireCell run;
  understanding Fix 2 first de-risks the combined implementation

**Do NOT implement either fix in `baseline_v0`.** Both require a new WireCell reconstruction run
from the same NC Delta generated events.

---

## Deliverables

- `tables/vertex_shower_map_mismatch_diagnostics.csv` — per-event object matching table
- This document — source-level diagnosis and 9-item report
- `docs/IMPLEMENTATION_REPORT.md` — Step 0 corrections applied (score ranges, output table)
- `baseline_v0/docs/SBND_1GAMMA_OBSTACLE_LOG.md` — OBS-008 added
