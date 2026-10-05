# Shower PDG Misidentification: Source Audit

**Date:** 2026-10-05  
**Trigger:** ≥2 independent no-recovery events with first-failure category NEIGHBOR_SHOWER_WRONG_PDG
and shower PDG = 13 (muon): evt_0044 (90.1 MeV) and evt_0054 (52.3 MeV).  
**Constraint:** Read-only archaeology. Do NOT alter any PDG assignment code.

---

## Summary

Two NC Delta signal events have their highest-energy graph-accessible shower classified as
pdg=13 (muon) by reconstruction. The downstream `pdg==11` gate in `singlephoton_tagger()`
blocks these showers, leaving `shw_sp_filled=0` despite Fix2-v2 Stage 2 successfully finding
and adding the shower to the candidate pool. A total of 5 events fail at NEIGHBOR_SHOWER_WRONG_PDG
(3× pdg=211, 2× pdg=13); only the pdg=13 cases require explanation, as pdg=211 showers are
expected to be pion tracks, not photon showers.

---

## Affected Events

| evt_idx | RSE | Shower E (MeV) | PDG | BFS hops | dist_to_mv (cm) | Notes |
|---------|-----|--------------|-----|----------|----------------|-------|
| evt_0044 | 100:0:922 | 90.1 | 13 | (direct at main_vertex) | 0.0 | dist=0 from vertex |
| evt_0054 | 120:0:529 | 52.3 | 13 | 1 | 39.2 | 1 hop via 39.6 cm track |

Both are geometrically accessible (in_candidates=true). Both fail only at the PDG gate.
evt_0054 is additionally documented in `docs/EVT0054_FAILURE_DIAGNOSIS.md`.

---

## PDG Assignment Chain (source archaeology)

### Step 1: Where the fix2 log PDG is read

`NeutrinoTaggerSinglePhoton.cxx:2383`:
```cpp
SPDLOG_LOGGER_DEBUG(s_log, "fix2_v2: direct shw E={:.1f}MeV pdg={}",
    shw_en / units::MeV, sg0->particle_info()->pdg());
```

And for neighbor showers (`NeutrinoTaggerSinglePhoton.cxx:2421`):
```cpp
"fix2_v2: neighbor shw E={:.1f}MeV pdg={} edge_is_shw={} v1_idx={}",
    shw_en / units::MeV, sg0->particle_info()->pdg(), ...
```

The logged `pdg` is the shower start segment's `particle_info()->pdg()`. This is also the
value checked at the downstream gate.

### Step 2: The downstream gate that blocks pdg=13 showers

`NeutrinoTaggerSinglePhoton.cxx:2394`:
```cpp
if (sg0->particle_info()->pdg() != 11) continue;
```

Any shower whose start segment does not have pdg=11 is skipped. The 20 MeV and badreco1
gates are downstream of this check and are never reached for pdg=13 showers.

Also at `NeutrinoTaggerSinglePhoton.cxx:2599`:
```cpp
if (pdg != 11) continue;
```

This is a second pdg==11 filter in the `singlephoton_tagger` shower selection loop,
independent of the Fix2 direct/neighbor categorisation.

### Step 3: Where the shower gets its PDG

`NeutrinoShowerClustering.cxx:904`:
```cpp
shower->set_particle_type(curr_sg->particle_info()->pdg());
```

This line runs in the "main-cluster long muon" path of `shower_clustering_with_nv_in_main_cluster()`.
When `curr_sg` (the shower seed segment) has `abs(pdg)==13`, the resulting shower inherits pdg=13.

For multi-segment showers, `NeutrinoShowerClustering.cxx:831`:
```cpp
shower->update_particle_type(particle_data, recomb_model, m_mip_dqdx, ...);
```

`update_particle_type()` computes a majority vote over all segments and may or may not promote
to pdg=11 depending on hit topology and dE/dx pattern.

The fix2 diagnostic additionally confirms via `NeutrinoTaggerSinglePhoton.cxx:2452–2453`:
```cpp
int diag_pdg = (diag_sg0 && diag_sg0->has_particle_info())
               ? diag_sg0->particle_info()->pdg() : 0;
```

So `fix2_diag: MAXE_SHW ... pdg=13` is the start segment's `particle_info()->pdg()`.

### Step 4: Where segment PDG is assigned

Segment PDG is set by `NeutrinoTrackShowerSep.cxx` (the track-shower separator). At multiple
points in `NeutrinoTrackShowerSep`, segments are reclassified between pdg=11 (EM shower),
pdg=13 (muon-like track), pdg=211 (pion-like), and pdg=2212 (proton-like) based on:

- Trajectory curvature flags (`kShowerTrajectory`)
- Topology flags (`kShowerTopology`)
- dE/dx median relative to MIP threshold
- Particle score from the cluster graph (`particle_score()`)

A segment is set to pdg=13 when the classifier determines it is muon-like. This is ordinarily
correct for muon tracks, but can fire on compact EM deposits with straight-track-like topology
or with MIP-range dE/dx (e.g., at the beginning of an EM shower before the cascade develops).

`NeutrinoShowerClustering.cxx:2302`:
```cpp
if (pdg == 0 || std::abs(pdg) == 13) {
```

There are multiple branches that handle pdg=13 showers explicitly, indicating this case
(a segment classified as muon but accepted into the shower pool) is a known pattern in the code.

### Step 5: Why a photon shower gets pdg=13 in these events

The photon from NC Delta decay undergoes Compton scattering or pair conversion. At 52–90 MeV:
- The shower may be short (the cascade is starting, few SPs reconstructed)
- The leading segment near the interaction vertex has straight-track-like topology
- dE/dx may be near the MIP peak at the start of the shower

Under these conditions, `NeutrinoTrackShowerSep` classifies the leading segment as muon-like
(pdg=13) rather than EM-like (pdg=11). The cluster then propagates to the shower pool with
pdg=13, where it fails the `singlephoton_tagger`'s pdg==11 requirement.

For evt_0044 (dist=0.0 cm, same vertex): the shower is directly at the interaction vertex,
where the high track density makes EM/muon disambiguation particularly difficult.

For evt_0054 (dist=39.2 cm, 1 hop via 39.6 cm track): the shower is across a conversion gap,
so the leading segment appears after a clean track stretch — it may have a compact, straight
leading edge that resembles a track rather than a shower.

---

## Cross-Check: pdg=211 Cases (evt_0000, 0009, 0021)

Three other NEIGHBOR_SHOWER_WRONG_PDG events have pdg=211 (charged pion, not muon):
- evt_0000: 124.2 MeV pdg=211 (max candidate is a pion track, not the signal shower)
- evt_0009: 162.8 MeV pdg=211 (max candidate is a pion)
- evt_0021: 279.7 MeV pdg=211 (max candidate is a pion)

These events have a true hadron track (pion from NC interaction) at higher energy than any
reconstructed EM shower. The pdg=211 assignment is correct — these are pion tracks, not
misidentified photon showers. The failure mode is different: no high-energy EM shower in
the candidate pool at all. Part F focuses on the pdg=13 cases where a true EM shower exists
but is misidentified.

---

## Distinguishing Features: pdg=13 vs Correct pdg=11 Showers

The 5 recovered events (evt_0012, 0014, 0016, 0020, 0026) all had their photon showers
correctly classified pdg=11 by reconstruction, enabling Fix2-v2 to recover them. Those showers
range from 23.6 to 167.6 MeV.

The pdg=13 cases (evt_0044 at 90.1 MeV, evt_0054 at 52.3 MeV) overlap in energy with the
successfully classified showers. The misidentification is therefore not purely energy-driven
— it depends on the local topology, conversion-gap geometry, and cluster neighborhood.

---

## Implications

- The pdg=13 misidentification is a failure of the shower particle ID step, not of Fix2-v2
  or the graph-adjacency traversal.
- Fix2-v2 works correctly: Stage 2 finds and adds the shower to the candidate pool. The failure
  is at the `pdg==11` gate downstream.
- The correct remedy is upstream shower PDG correction for compact EM segments near the vertex.
  This is a separate fix requiring `NeutrinoTrackShowerSep` changes.
- Do NOT modify the `pdg==11` gate to accept pdg=13 — that would admit genuine muon tracks
  into the photon selection.
- 2/59 events (3.4%) fail at this gate; the rate may differ in the full BNB data sample.

---

## Source Locations (read-only audit)

| File | Lines | Role |
|------|-------|------|
| `clus/src/NeutrinoTaggerSinglePhoton.cxx` | 2383, 2394, 2421, 2453, 2468, 2599 | PDG logging and gate |
| `clus/src/NeutrinoShowerClustering.cxx` | 831, 904, 2302, 2620, 2677 | Shower PDG assignment |
| `clus/src/NeutrinoTrackShowerSep.cxx` | (multiple) | Segment PDG classification |

Do not alter any of these files under the current freeze.
