# Fix 2 — Graph-Adjacent Shower Fallback (2026-10-05)

Isolated development area for Fix 2 to `singlephoton_tagger()`.

**Branch:** `feature/sbnd-singlephoton-onehop-20261005` (in `wct-dev/`)  
**Algorithm version:** Fix2-v2 (commit 8dddba5) — all-edge one-hop neighbor fallback  
**Hard constraints:** baseline_v0, frozen configs, BDT weights — all untouched

---

## Directory Layout

```
fix2_vertex_shower_onehop_20261005/
├── wct-dev/                    # git worktree; branch feature/sbnd-singlephoton-onehop-20261005
│   └── clus/src/
│       └── NeutrinoTaggerSinglePhoton.cxx   # THE ONLY MODIFIED FILE
├── build/
│   ├── compile_pbs.sh          # PBS job: compile + relink libWireCellClus.so
│   ├── libWireCellClus.so      # 392 MB patched shared library (Fix2-v2)
│   ├── run_patched_only.pbs    # PBS job: patched run evt_0058
│   ├── run_patched_evt_0014.pbs
│   ├── run_patched_evt_0020.pbs
│   ├── run_patched_evt_0054.pbs
│   ├── run_patched_evt_0005.pbs  # control: 0p topology (known-good)
│   ├── run_patched_evt_0001.pbs  # control: 0p topology (known-good)
│   ├── run_patched_evt_0015.pbs  # control: Np topology (known-good)
│   ├── score_step9.pbs
│   ├── score_patched_evt0058.py  # BDT scorer (PyROOT, NOT uproot)
│   ├── extract_ttagger.py
│   ├── extract_pbs.sh
│   └── run_patched_evt_template.sh
├── control/evt_0058/           # Control (unpatched) run output for evt_0058
├── patched/evt_0058/           # Patched run output (VALIDATED Fix2-v2)
├── patched/evt_0014/           # Patched run output (VALIDATED Fix2-v2)
├── patched/evt_0020/           # Patched run output (VALIDATED Fix2-v2)
├── patched/evt_0054/           # Patched run output (NOT FIXED)
├── patched/evt_0005/           # Patched run output (control, no regression)
├── patched/evt_0001/           # Patched run output (control, no regression)
├── patched/evt_0015/           # Patched run output (control, no regression)
├── tables/
│   ├── evt0058_control_vs_patch.csv    # T_tagger column diff baseline vs patched
│   ├── evt0058_bdt_scores.csv          # BDT scores; baseline row marked DIAGNOSTIC
│   ├── four_event_fix2_validation.csv  # 4-event Fix2-v2 validation summary
│   └── fix2_feature_completeness.csv   # BDT evaluability for recovered events (Part D)
├── docs/ (see ../../docs/)
└── logs/                       # PBS stdout/stderr and container logs
```

---

## The Patch (Fix2-v2 Summary)

`NeutrinoTaggerSinglePhoton.cxx` lines ~2354-2433:

**Before (baseline):**
```cpp
auto it = map_vertex_to_shower.find(main_vertex);
if (it == map_vertex_to_shower.end()) return false;
```

**After (Fix2-v2): Two-stage candidate collection with usable-shower gate:**
1. **Stage 1 (direct):** lookup `main_vertex` in `map_vertex_to_shower` — preserves baseline behavior
2. **Usable-shower gate:** if any direct shower passes `pdg==11 && en>20MeV && badreco1`, direct path is sufficient; no fallback runs
3. **Stage 2 (neighbor fallback, only when direct is insufficient):** traverse ALL incident graph edges (regardless of topology type), look up each neighboring vertex V1 in `map_vertex_to_shower`

No global vertex scan. No distance threshold. Exactly one hop.

Full algorithm documentation: [docs/FIX2_IMPLEMENTATION.md](../../docs/FIX2_IMPLEMENTATION.md)

---

## Key Results (Fix2-v2, topology-confirmed 2026-10-05)

| Event | RSE | Baseline filled | Patched filled | Energy | Mechanism | Result |
|-------|-----|----------------|----------------|--------|-----------|--------|
| evt_0014 | 50:0:449 | 0 | **1** | 121.6 MeV | Stage 2 (track, 33.6cm, same cluster, vtx_type=1) | **RECOVERED** |
| evt_0020 | 60:0:153 | 0 | **1** | 153.8 MeV | Stage 2 (track, 4.2cm, diff cluster graph-connected, vtx_type=2) | **RECOVERED** |
| evt_0054 | 120:0:529 | 0 | 0 | — | 11 candidates found, downstream singlephoton_tagger() fail | NOT FIXED |
| evt_0058 | 120:0:664 | 0 | 0 | 449 MeV | DIFFERENT_CLUSTER, BFS_NO_PATH, vtx_type=3 | NOT FIXED |
| evt_0005 | — | 1 | 1 | ~344 MeV | Stage 1 direct sufficient (direct_has_usable=true) | NO REGRESSION |
| evt_0001 | — | 1 | 1 | — | Stage 1 direct sufficient | NO REGRESSION |
| evt_0015 | — | 1 | 1 | — | Stage 1 direct sufficient | NO REGRESSION |

**2/4 target events recovered. 3/3 known-good controls unchanged.**

### evt_0058 topology note
A prior interim analysis predicted evt_0058 would be recovered by Stage 2 via the
`kShowerTopology` edge. Graph-topology diagnosis (2026-10-05) established this is wrong.
Stage 2 reaches vtx99 (the kShowerTopology neighbor) but vtx99 holds only noise showers.
The 449 MeV signal shower is keyed to vtx1 (idx=1) in cluster 45, which has no graph path
from main_vertex (idx=97) in cluster 2. BFS_NO_PATH confirmed. evt_0058 is a
companion-cluster case (OBS-001), not an OBS-008 graph-adjacent case.
See `docs/EVT0058_GRAPH_TOPOLOGY_DIAGNOSIS.md` for the full measurement.

---

## Algorithm Scope

Fix2-v2 is a **graph-adjacent shower fallback within the existing PRGraph**:
- Recovers showers whose `start_vertex` is exactly one PRGraph edge from `main_vertex`
- Works regardless of edge type (track or shower topology)
- Works regardless of cluster ID (evt_0020 demonstrates cross-cluster recovery is valid
  when the graph explicitly connects the vertices)
- Does NOT recover companion-cluster showers with no graph path from `main_vertex`
- Does NOT use any Euclidean distance threshold

---

## Build Reproducibility

```bash
qsub build/compile_pbs.sh   # rebuilds libWireCellClus.so from Fix2-v2 source
qsub build/run_patched_only.pbs   # run patched evt_0058
```

---

## Regression Report

Full report: [docs/FIX2_REGRESSION_REPORT.md](../../docs/FIX2_REGRESSION_REPORT.md)
