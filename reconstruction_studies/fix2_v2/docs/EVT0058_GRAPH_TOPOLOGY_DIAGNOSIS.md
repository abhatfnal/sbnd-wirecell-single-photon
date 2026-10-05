# evt_0058 Graph Topology Diagnosis

**RSE:** 120:0:664  
**Branch:** `feature/sbnd-singlephoton-onehop-20261005`  
**Diagnostic commit:** cd7e7b3 (BFS topology probe added to `singlephoton_tagger()`)  
**PBS run:** job 193302 (2026-10-05 16:41 UTC)  
**Date:** 2026-10-05

---

## Task A — Exact Shower Identification

The 449 MeV shower's identity from the `fix2_diag` debug log:

```
fix2_diag: MAXE_SHW E=449.0MeV pdg=11 vtx_type=3 sv_idx=1
           sv_pos=(-90.9,-30.9,221.1)cm dist_to_mv=39.0cm
           shw_cl=45 main_cl=2 same_cl=false sv_in_map=true in_candidates=false
```

| Field | Value |
|-------|-------|
| Energy | 449.0 MeV |
| PDG | 11 (electron — photon-initiated shower) |
| vtx_type | 3 |
| start_vertex graph index | 1 |
| start_vertex position | (-90.9, -30.9, 221.1) cm |
| Distance to main_vertex | 39.0 cm (Euclidean) |
| Shower cluster ID | 45 |
| Main cluster ID | 2 |
| Same cluster as main | **false** |
| start_vertex in `map_vertex_to_shower` | **true** |
| In Fix2-v2 `candidate_showers` | **false** |

`main_vertex` is at graph index 97 (vtx97).

---

## Task B — Graph Distance

BFS result from `main_vertex` (vtx97) to the signal shower's `start_vertex` (vtx1), traversing
ALL edges in the PRGraph without type restriction:

```
fix2_diag: BFS_NO_PATH main_vtx=97 diag_sv=1
```

**No graph path exists.** The BFS explored the entire reachable component from vtx97 and did not
encounter vtx1. This is not a partial-search artifact — the BFS is exhaustive (visits all
reachable vertices before giving up).

---

## Task C — Classification

**Classification: `DIFFERENT_CLUSTER`**

Evidence:
1. `shw_cl=45 ≠ main_cl=2`: the signal shower's start_segment belongs to cluster 45; the
   neutrino main_vertex belongs to cluster 2. These are distinct WireCell cluster objects.
2. `BFS_NO_PATH`: no graph edge chain connects vtx97 (main_vertex) to vtx1 (shower start_vertex)
   anywhere in the PRGraph.
3. The 39 cm Euclidean distance is coincidental proximity — the vertices are not connected.

This is distinct from the `SAME_CLUSTER_BUT_GRAPH_DISCONNECTED` case (which would require
same cluster ID but missing graph connectivity within that cluster).

---

## Task D — NeutrinoKinematics Code Path

The 449 MeV shower appears in `T_kine` despite being graph-disconnected from `main_vertex`.
Tracing the `NeutrinoKinematics.cxx` code:

**First pass** (direct edges from `main_vertex`): The gap segment incident on vtx97 leads to
v1_idx=99, not vtx1. vtx1 is not adjacent to vtx97, so the first pass does not encounter the
449 MeV shower.

**BFS traversal** (track segments from main_vertex): The BFS reaches v1_idx=99 and its
adjacent shower-start segments (9 low-energy showers). The 449 MeV shower at vtx1 is in
cluster 45, which has no track edges connecting to cluster 2's traversal graph. The BFS
does not reach vtx1.

**Satellite pass** (conn=2 or 3, different cluster): The 449 MeV shower has `vtx_type=3`
and `shw_cl=45 ≠ main_cl=2` → it enters the satellite drop logic as a candidate. The
satellite verdict was **keep** (it was not placed in `sat_drop_set`), based on the geometric
and topological criteria in `NeutrinoKinematics.cxx` lines ~460-580.

**Leftover pass**: The shower was not in `used_showers` (BFS didn't reach it) and not in
`sat_drop_set` (satellite kept it). With `vtx_type=3 ≤ 3`, the leftover pass adds it:

```cpp
ktree.kine_energy_included.push_back(vtx_type != 3 ? 1 : vtx_type);
// → kine_energy_included = 3   (NOT 1)
```

**The 449 MeV shower gets `kine_energy_included=3` in T_kine, NOT 1.**

### Correction to earlier documentation

Previous analyses assumed `kine_energy_included=1` implied BFS-reachability from `main_vertex`.
This is **wrong**:

- `kine_energy_included=1`: shower reached by first-pass or BFS traversal (OR vtx_type=1/2 leftover)
- `kine_energy_included=3`: shower in leftover pass with vtx_type=3 — NOT BFS-reachable, added separately
- `kine_energy_included=3` does NOT imply graph-reachability from `main_vertex`

The evt_0058 signal shower's `kine_energy_included` value is 3, meaning NeutrinoKinematics
includes it as a geometrically-satellite object (conn-3, different cluster, satellite-kept),
not as a BFS-reachable component of the neutrino vertex.

---

## Task E — Comparison with evt_0014 and evt_0020

From the same diagnostic runs:

**evt_0014 (121.6 MeV shower, RSE 50:0:449):**
```
fix2_diag: MAXE_SHW E=121.6MeV pdg=11 vtx_type=1 sv_idx=4
           dist_to_mv=31.9cm shw_cl=1 main_cl=1 same_cl=true sv_in_map=true
fix2_diag: BFS_FOUND hops=1 path_vtx_count=2
fix2_diag:   hop1: vtx0->vtx4 seg_idx=2 is_shw=false len=33.6cm
```
- 1 graph hop via track segment (33.6 cm)
- **Same cluster** (shw_cl=1 == main_cl=1)
- vtx_type=1

**evt_0020 (153.8 MeV shower, RSE 60:0:153):**
```
fix2_diag: MAXE_SHW E=153.8MeV pdg=11 vtx_type=2 sv_idx=1
           dist_to_mv=4.2cm shw_cl=25 main_cl=3 same_cl=false sv_in_map=true
fix2_diag: BFS_FOUND hops=1 path_vtx_count=2
fix2_diag:   hop1: vtx2->vtx1 seg_idx=2 is_shw=false len=4.2cm
```
- 1 graph hop via track segment (4.2 cm)
- **Different cluster** (shw_cl=25 ≠ main_cl=3) — but graph-connected via a cross-cluster track edge
- vtx_type=2

**Summary table:**

| Event | Signal E | vtx_type | same_cl | hops | edge_type | seg_len |
|-------|---------|---------|---------|------|-----------|---------|
| evt_0014 | 121.6 MeV | 1 | YES | **1** | track | 33.6 cm |
| evt_0020 | 153.8 MeV | 2 | NO | **1** | track | 4.2 cm |
| evt_0058 | 449.0 MeV | 3 | NO | **∞ (NO PATH)** | — | — |

evt_0014 and evt_0020: signal shower start_vertex is exactly 1 hop from `main_vertex` via a
track-typed segment. Fix2-v2's Stage 2 (all-edge one-hop) correctly recovers both.

evt_0058: signal shower start_vertex is in a different cluster with NO graph path from
`main_vertex`. One-hop, two-hop, or any graph-bounded traversal from `main_vertex` cannot
reach it. These are fundamentally different failure modes.

---

## Task F — Fix2-v3 Recommendation

**Recommended action: RECLASSIFY evt_0058 as DIFFERENT_CLUSTER (companion-cluster case).**

Per the Fix2-v3 decision logic: if the signal shower is in a different cluster → evt_0058
belongs with the companion-cluster problem, not Fix 2.

Evidence supporting this:
1. `shw_cl=45 ≠ main_cl=2`: confirmed different cluster
2. `BFS_NO_PATH`: no graph connectivity, not a bounded-BFS problem
3. `vtx_type=3`: NeutrinoKinematics' own classification places this shower as a "satellite"
   relative to the neutrino vertex, not as a direct component

**Fix2-v3 should NOT attempt to recover evt_0058.** The correct extension for evt_0058 is a
companion-cluster algorithm that associates detached showers from nearby clusters with the
neutrino vertex using physics-motivated constraints (direction, gap geometry, cluster quality).
That is a separate, more complex problem and is explicitly deferred per the hard constraints.

**Fix2-v2 therefore closes at 2/4 target events recovered** (evt_0014 and evt_0020), with
evt_0058 reclassified and evt_0054 pending separate downstream investigation.

---

## Why the 50 cm Proximity Result Was Misleading

The Fix2-v1 proximity scan found the 449 MeV shower at 39 cm and treated this as evidence
that a geometry-only fallback could recover the shower. This was correct as a diagnostic
observation — the shower IS geometrically near — but the proximity scan was operating
across cluster boundaries without any cluster check.

A geometry-only fallback that ignores cluster identity can accidentally associate unrelated
showers from distant events or cosmic fragments. The correct approach, if one is pursued,
must include at minimum:
- same neutrino pattern (within the PRGraph instance)
- no intervening unrelated topology
- direction compatibility with the gap geometry
- a threshold motivated by physics (e.g., maximum photon conversion length in argon at
  typical energies) rather than the largest observed example

The 50 cm radius was derived from a sample of 4 events. It is not a validated threshold.

---

## Summary

1. **start_vertex of 449 MeV shower**: vtx1, index 1, at (-90.9, -30.9, 221.1) cm
2. **Same main cluster**: NO (shw_cl=45, main_cl=2)
3. **Graph path from main_vertex**: NO (BFS_NO_PATH, exhaustive)
4. **Shortest hop count**: undefined (no path)
5. **Path**: none
6. **NeutrinoKinematics code path**: satellite pass (kept) → leftover pass with `kine_energy_included=3`
7. **kine_energy_included=1 implies BFS-reachability**: FALSE — vtx_type=3 yields `kine_energy_included=3`; vtx_type=1/2 yield 1 but may also come from leftover pass, not BFS
8. **evt_0014 and evt_0020 hop counts**: both exactly 1 (track-typed edges)
9. **evt_0058 belongs to same mechanism as evt_0014/0020**: NO — evt_0014/0020 are 1-hop graph-reachable; evt_0058 is graph-disconnected and in a different cluster
10. **Recommended Fix2-v3 strategy**: RECLASSIFY — evt_0058 is a companion-cluster case, not a Fix 2 case; no Fix2-v3 extension needed for evt_0058
11. **Why better than 50 cm radius**: the 50 cm radius crosses cluster boundaries arbitrarily; the correct classification (different cluster) identifies the structural reason for the separation and routes evt_0058 to the appropriate algorithm class
