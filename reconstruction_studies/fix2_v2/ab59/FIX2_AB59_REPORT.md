# Fix2-v2: 59-Event Controlled A/B Study Report

**Date:** 2026-10-05  
**Algorithm:** Fix2-v2 — Graph-adjacent shower fallback (commit 8dddba5, diagnostic probe cd7e7b3)  
**Input:** baseline_v0/ncdelta_50evt/reco1/ncdelta_reco1.root (59 NC Delta events)  
**Study scope:** Wire-Cell stage only. Reco1 inputs frozen. No companion-cluster Fix1, no BDT retraining, no Fix3.  
**Tables:** ab59/tables/fix2_ab59_event_comparison.csv, fix2_ab59_bdt_comparison.csv, fix2_ab59_cutflow.csv

---

## Algorithm Summary

Fix2-v2 runs a two-stage shower candidate collection inside `NeutrinoPattern`:

**Stage 1 (direct):** Look up `map_vertex_to_shower[main_vertex]`. If any direct shower passes the usable gate (pdg==11 AND energy>20 MeV AND badreco1), stop. No fallback.

**Stage 2 (fallback, only when Stage 1 finds no usable shower):** Traverse ALL incident PRGraph edges from main_vertex regardless of edge type. For each neighbor vertex V1, look up `map_vertex_to_shower[V1]` and add to the candidate pool. Select the best candidate by the same downstream logic.

The algorithm is bounded by the existing PRGraph. It does not use Euclidean distance or cross to graph-disconnected clusters.

---

## Part F: Per-Event Classification

Full table in `fix2_ab59_event_comparison.csv` (59 rows, ~25 columns).

### Event Class Counts

| Class | Count | Events |
|---|---|---|
| UNCHANGED_DIRECT_SUCCESS | 33 | Direct shower usable, no change |
| RECOVERED_BY_FIX2 | **5** | evt_0012, 0014, 0016, 0020, 0026 |
| FALLBACK_ACTIVATED_NO_RECOVERY | 19 | Stage 2 triggers but no usable shower found |
| FALLBACK_ACTIVATED_DIFFERENT_SHOWER | 0 | — |
| UNEXPECTED_CHANGE_WITHOUT_FALLBACK | 0 | — |
| NO_NEUTRINO_CANDIDATE | 2 | evt_0039, evt_0052 (both baseline and patched) |
| OTHER | 0 | — |
| **Total** | **59** | |

### Recovered Events (RECOVERED_BY_FIX2)

| Event | Patched energy | BFS hops | same_cl | vtx_type |
|---|---|---|---|---|
| evt_0012 | 167.6 MeV | 1 | true | 3 |
| evt_0014 | 121.6 MeV | 1 | true | 1 |
| evt_0016 | 23.6 MeV | 1 | false | 2 |
| evt_0020 | 153.8 MeV | 1 | false | 2 |
| evt_0026 | 90.4 MeV | 1 | false | 3 |

All 5 recovered via Stage 2 (graph-adjacent fallback), BFS hops=1 in all cases.

---

## Part G: Eight Safety Metrics

| # | Metric | Value | Criterion |
|---|---|---|---|
| 1 | Events where Stage 2 fallback activates | **24 / 59** (40.7%) | — |
| 2 | Events gaining shw_sp_filled=1 | **5** | — |
| 3 | Events losing shw_sp_filled=1 | **0** | KEY SAFETY CRITERION |
| 4 | Events changing selected shower (both filled=1) | 5 | — |
| 5 | Events changing shw_sp_n_20mev_showers | 5 | — |
| 6 | Events changing shw_sp_n_20br1_showers | 5 | — |
| 7 | Events changing photon_flag | 0 | — |
| 8 | Unexpected changes (direct_has_usable=true, result changed) | **0** | PASS |

**Safety verdict: PASS.** No previously-working event lost its shower selection. No ghost changes without fallback activation.

---

## Part H: BDT Score Changes

Full table in `fix2_ab59_bdt_comparison.csv` (59 rows, 4 BDT models × baseline/patched/delta).

Key findings:
- 5 events gain BDT evaluability (the 5 RECOVERED_BY_FIX2 events gain shw_sp_n_20mev>0, enabling all 4 BDTs)
- 0 events lose BDT evaluability
- photon_flag changes: 0
- No BDT score changes for the 33 UNCHANGED_DIRECT_SUCCESS events

---

## Part I: PRE_FV_REFERENCE_SELECTION Cut Flow

| Step | Baseline | Patched | Delta | Notes |
|---|---|---|---|---|
| 1. Total events | 59 | 59 | 0 | |
| 2. Has neutrino candidate | 57 | 57 | 0 | |
| 3. shw_sp_n_20mev > 0 | 33 | **38** | **+5** | 5 recovered events gain valid shower |
| 4. All 4 BDTs evaluable | 33 | **38** | **+5** | all 5 also become evaluable |
| 5. numu BDT > 0.4 | 13 | **15** | **+2** | evt_0014 and evt_0020 pass |
| 6. other BDT > 0.2 | 7 | **8** | **+1** | evt_0014 does not pass this cut |
| 7. ncpi0 BDT > -0.05 | 4 | **5** | **+1** | |
| 8. nue BDT > -1.0 | 4 | **5** | **+1** | |
| 9. shw_sp_n_20br1 == 1 | 3 | **4** | **+1** | |

**Final pre-FV selection: baseline 3 → patched 4**  
**Newly selected by Fix2-v2: [evt_0020]** (153.8 MeV photon, different cluster, vtx_type=2, BFS 1 hop)  
**Lost from selection: none**

Note: evt_0014 (121.6 MeV, same cluster, vtx_type=1) is recovered at step 3–5 but does not pass the `other BDT > 0.2` cut (step 6).

---

## Part J: Target Event Verification

### evt_0014 — Expected Recovery ✓

```
fix2_v2: direct_has_usable=false
fix2_v2: fallback n_edges=2 n_neighbor_new=2 total_candidates=9
fix2_diag: MAXE_SHW E=121.6MeV pdg=11 vtx_type=1 same_cl=true
fix2_diag: BFS_FOUND hops=1 (vtx0->vtx4, 33.6cm track)
```

Outcome: RECOVERED_BY_FIX2. shw_sp_filled 0→1. Does not pass all 9 pre-FV cuts (fails other BDT > 0.2).

### evt_0020 — Expected Recovery ✓ AND newly selected

```
fix2_v2: direct_has_usable=false
fix2_v2: fallback n_edges=2 n_neighbor_new=3 total_candidates=6
fix2_diag: MAXE_SHW E=153.8MeV pdg=11 vtx_type=2 same_cl=false shw_cl=25 main_cl=3
fix2_diag: BFS_FOUND hops=1 (vtx2->vtx1, 4.2cm track)
```

Outcome: RECOVERED_BY_FIX2. shw_sp_filled 0→1. Passes all 9 pre-FV cuts → newly selected.

### evt_0058 — Expected Non-Recovery ✓

```
fix2_v2: direct_has_usable=false
fix2_v2: fallback activates
fix2_diag: BFS_NO_PATH
```

Stage 2 activates but signal shower (449 MeV, vtx1, cluster 45) is in a companion cluster unreachable from main_vertex (cluster 2) via PRGraph. Outcome: FALLBACK_ACTIVATED_NO_RECOVERY. shw_sp_filled remains 0.

Topology confirmed: main_vertex idx=97 and signal shower start_vertex idx=1 are in different graph components (BFS_NO_PATH). This is the COMPANION_CLUSTER_SHOWER_INACCESSIBLE case documented in EVT0058_GRAPH_TOPOLOGY_DIAGNOSIS.md.

### Controls (evt_0001, evt_0005, evt_0015) — No Regression ✓

All three: UNCHANGED_DIRECT_SUCCESS. direct_has_usable=true, no fallback, shw_sp_filled=1 in both baseline and patched, shower energy unchanged.

---

## Part K: evt_0054 Downstream Failure

See [EVT0054_FAILURE_DIAGNOSIS.md](../docs/EVT0054_FAILURE_DIAGNOSIS.md) for full trace.

Summary: Stage 2 fallback activates and BFS finds a 1-hop path (vtx1→vtx0, 39.6 cm). The maximum-energy neighbor shower is **52.3 MeV with pdg=13 (muon)**. Downstream NeutrinoFilling requires pdg==11; the muon shower fails the PDG gate. `shw_sp_n_20mev_showers` remains 0.

Classification: **SHOWER_PDG_MISIDENTIFICATION** — the NC Delta photon shower is graph-accessible but shower reconstruction assigned pdg=13. Fix2-v2 works correctly; the failure is in shower particle identification.

This is distinct from evt_0058 (graph topology failure) and evt_0014/evt_0020 (successful recovery). No Fix2-v3 is required for evt_0054; the remedy is upstream shower PDG classification.

---

## Summary of All 4 OBS-008 Target Events

| Event | OBS class | Fix2-v2 outcome | Pre-FV selected |
|---|---|---|---|
| evt_0014 | OBS-008 (map-lookup, vtx_type=1) | RECOVERED | No (fails other BDT) |
| evt_0020 | OBS-008 (map-lookup, vtx_type=2) | RECOVERED | **Yes** (+1 to selection) |
| evt_0058 | OBS-001 (companion cluster) | NOT RECOVERED (BFS_NO_PATH) | No |
| evt_0054 | SHOWER_PDG_MISIDENTIFICATION | NOT RECOVERED (pdg=13) | No |

---

## Algorithm Scope Assessment

Fix2-v2 recovered **5 of 59 events** (8.5%), all via graph-adjacent 1-hop fallback. The algorithm is conservative:

- **Does not use Euclidean distance** — bounded by PRGraph topology
- **Does not cross graph-disconnected clusters** — companion-cluster events remain unrecovered (as required)
- **0 regressions** — no event loses its shower selection
- **0 ghost changes** — no change occurs without Stage 2 activation
- **Fallback activation rate: 40.7%** (24/59) — Stage 2 activates frequently, recovers 5/24 of those events

The 19 FALLBACK_ACTIVATED_NO_RECOVERY events decompose into three first-failure categories
(see `tables/fix2_no_recovery_failure_census.csv` for full census):

| First-failure category | Count | Events |
|---|---|---|
| GRAPH_DISCONNECTED_NO_RELEVANT_NEIGHBOR_SHOWER | 7 | 0002, 0031, 0032, 0037, 0042, 0056, 0058 |
| NO_NEIGHBOR_SHOWER_ABOVE_20MEV | 7 | 0006, 0010, 0013, 0027, 0030, 0050, 0055 |
| NEIGHBOR_SHOWER_WRONG_PDG | 5 | 0000, 0009, 0021, 0044, 0054 |

GRAPH_DISCONNECTED events all have vtx_type=3 and kine_energy_included=3 (leftover pass). The
7 events break into two topological sub-classes: WITHIN_CLUSTER_BFS_DISCONNECTED (same_cl=true:
evt_0002, 0031, 0032, 0037) and COMPANION_CLUSTER (same_cl=false: evt_0042, 0056, 0058).

NEIGHBOR_SHOWER_WRONG_PDG includes 3× pdg=211 (pion tracks) and 2× pdg=13 (muon misidentification
of EM shower). The pdg=13 cases (evt_0044, evt_0054) are audited in `docs/SHOWER_PDG_FAILURE_AUDIT.md`.

---

---

## Part M: 59-Event Mutually Exclusive Hierarchy (Bottleneck Accounting)

All bins are mutually exclusive; they sum to 59.

| Bin | Category | Count | Events |
|-----|----------|-------|--------|
| 1 | No neutrino candidate (`nu_n_candidates=0`) | 2 | evt_0039, evt_0052 |
| 2 | Direct shower success — `shw_sp_filled=1` unchanged | 33 | (all UNCHANGED_DIRECT_SUCCESS) |
| 3 | Recovered by Fix2-v2 (Stage 2 fallback, BFS hops=1) | 5 | evt_0012, 0014, 0016, 0020, 0026 |
| 4 | Graph-disconnected: no PRGraph path to signal shower | 7 | evt_0002, 0031, 0032, 0037, 0042, 0056, 0058 |
| 5 | Graph-reachable, wrong PDG (pdg≠11) | 5 | evt_0000, 0009, 0021, 0044, 0054 |
| 6 | Graph-reachable, max pdg=11 shower below 20 MeV | 7 | evt_0006, 0010, 0013, 0027, 0030, 0050, 0055 |
| **Total** | | **59** | |

Bin 4 is the largest remaining bottleneck (7 events), all vtx_type=3 with kine_energy_included=3.
Sub-classes: 4× WITHIN_CLUSTER_BFS_DISCONNECTED (same_cl=true) and 3× COMPANION_CLUSTER
(same_cl=false, including evt_0058).

Fix2-v2 directly addressed Bin 3 (OBS-008 class) and recovered 5 events. It does NOT address
Bins 4, 5, or 6. The next highest-impact fix target is Bin 4 (companion-cluster / Fix 1).

**Note on Part J (reconstruction accessibility vs BDT selection):** These are kept strictly separate.
- *Reconstruction accessibility*: 33 → 38 events evaluable (shw_sp_n_20mev > 0). This is what Fix2-v2 improves.
- *BDT selection* (pre-FV): 3 → 4 events pass all BDT cuts. This is a consequence of the accessibility
  change, not a direct Fix2-v2 target. BDT thresholds are NOT tuned.
- Of the 5 newly accessible events, only evt_0020 passes all BDT cuts. The other 4 fail at various
  BDT thresholds (not shower-association failures). These 4 BDT failures are NOT fix targets.

---

## Infrastructure Notes

- PBS jobs: 193321 (batch 1, idx 0–19), 193326 (batch 2, idx 20–39), 193332 (batch 3, idx 40–58), 193328 (evt_0015 rerun), 193336 (reruns for 34/35/38/39), 193337 (evt_0038 final rerun)
- Library: libWireCellClus.so, MD5=9cff76d0d81a4b6c45a88908e78e73e4, 393 MB, built 2026-10-05 16:40 UTC
- Algorithm commit: 8dddba5 (Fix2-v2 frozen); diagnostic BFS probe: cd7e7b3 (read-only, used for A/B run)
- Events 0039 and 0052: no T_tagger in either baseline or patched (NO_NEUTRINO_CANDIDATE — no neutrino pattern reconstructed); both excluded from all counts above
