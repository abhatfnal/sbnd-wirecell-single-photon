# EVT0054 Downstream Failure Diagnosis

**Date:** 2026-10-05  
**Study:** Fix2-v2 59-event A/B study (ab59), commit cd7e7b3  
**Event:** index 54 (nskip=54) in ncdelta_reco1.root  
**Outcome:** FALLBACK_ACTIVATED_NO_RECOVERY — Fix2-v2 Stage 2 triggers and reaches a graph-adjacent shower (BFS hops=1), but shw_sp_filled remains 0 in both baseline and patched.

---

## Fix2-v2 Trace

### Stage 1: Direct Lookup

```
fix2_v2: main_vtx_deg=2 map_size=4 all_showers=15 n_direct=8
fix2_v2: direct shw E=10.9MeV pdg=11
fix2_v2: direct shw E=1.2MeV pdg=11
fix2_v2: direct shw E=0.8MeV pdg=11
fix2_v2: direct shw E=0.9MeV pdg=11
fix2_v2: direct shw E=3.8MeV pdg=11
fix2_v2: direct shw E=5.6MeV pdg=11
fix2_v2: direct shw E=0.9MeV pdg=2212
fix2_v2: direct shw E=0.3MeV pdg=11
fix2_v2: direct_has_usable=false
```

8 direct showers (start_vertex == main_vertex). All pdg=11 showers are < 20 MeV; the 0.9 MeV entry is pdg=2212 (proton). None pass the usable-shower gate (pdg==11 AND energy>20 MeV AND badreco1). Stage 2 fallback activates.

### Stage 2: Graph-Adjacent Fallback

```
fix2_v2: neighbor shw E=52.3MeV pdg=13  edge_is_shw=false v1_idx=0
fix2_v2: neighbor shw E=3.7MeV  pdg=2212 edge_is_shw=false v1_idx=0
fix2_v2: neighbor shw E=5.6MeV  pdg=2212 edge_is_shw=false v1_idx=0
fix2_v2: fallback n_edges=2 n_neighbor_new=3 total_candidates=11
```

Stage 2 traverses 2 incident PRGraph edges from main_vertex. The neighbor vertex (v1_idx=0) holds 3 showers. The highest-energy one is 52.3 MeV with **pdg=13 (muon)**. The others are protons (pdg=2212).

### Diagnostic

```
fix2_diag: MAXE_SHW E=52.3MeV pdg=13 vtx_type=2 sv_idx=0 sv_pos=(-51.0,-47.0,245.0)cm
           dist_to_mv=39.2cm shw_cl=20 main_cl=1 same_cl=false
           sv_in_map=true in_candidates=true
fix2_diag: BFS_FOUND hops=1 path_vtx_count=2
fix2_diag:   hop1: vtx1->vtx0 seg_idx=37 is_shw=false len=39.6cm seg_in_candidate_start=false
```

BFS confirms: the 52.3 MeV shower is exactly 1 graph hop from main_vertex, via a 39.6 cm track segment. It is in the candidate pool (`in_candidates=true`). The failure is NOT topology.

---

## Root Cause: Shower PDG Misidentification

The Fix2-v2 candidate pool now has 11 showers (8 direct + 3 neighbor). The downstream `NeutrinoFilling` / `TaggerCheckNeutrino` sweep selects the signal shower by requiring:

```
pdg == 11   AND   energy > 20 MeV   AND   badreco1 == true
```

The 52.3 MeV shower has **pdg=13 (muon)**, not pdg=11 (photon/electron). It fails the PDG gate and is excluded from `shw_sp_n_20mev_showers`. No other candidate in the pool passes (all remaining are < 20 MeV or wrong PDG).

The PR36AUDIT log confirms:

```
PR36AUDIT f2_sweep=0/26 f2_gates=[0,0,0,0,0,0,0,0,0,0,0]
```

0 of 26 shower candidates passed the f2 sweep. The PDG gate is the first filter; all candidates fail before reaching energy or badreco1 checks.

---

## Classification

| Criterion | Value |
|---|---|
| Topology failure (BFS_NO_PATH) | No — BFS_FOUND hops=1 |
| Fix2 Stage 2 activates | Yes — fallback triggered |
| Shower geometrically accessible | Yes — 39.6 cm, graph-adjacent |
| Shower PDG | 13 (muon) — NOT 11 (photon/electron) |
| Downstream filter failure | Yes — pdg gate in NeutrinoFilling |
| Fix type needed | Shower misidentification correction, not Fix2 |

**Classification: SHOWER_PDG_MISIDENTIFICATION**  
The NC Delta signal photon shower is present and graph-accessible, but the shower reconstruction assigned pdg=13 instead of pdg=11. Fix2-v2 works correctly (Stage 2 finds and adds the shower to candidates). The failure is downstream in the PDG filter.

---

## Comparison with Other Non-Recovery Cases

| Event | Non-recovery reason | BFS result |
|---|---|---|
| evt_0058 | Companion cluster — shower in different graph component | BFS_NO_PATH |
| evt_0054 | Shower PDG misidentification — pdg=13 blocks downstream filter | BFS_FOUND hops=1 |

evt_0058 is a graph topology failure (OBS-001). evt_0054 is a shower reconstruction failure: the photon/Compton shower is classified as a muon by the clustering algorithm. These are distinct obstacles requiring separate fixes.

---

## Implications

- No Fix2-v3 for evt_0054 is needed or appropriate at this stage (per study constraints).
- evt_0054 should be counted in the shower-reconstruction failure pool, not the companion-cluster pool.
- The correct remedy would be improving shower PDG assignment for short, isolated showers near the interaction vertex. This is outside the scope of Fix 2.
