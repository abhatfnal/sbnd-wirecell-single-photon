# Fix2-v2 Frozen Provenance Record

**Date frozen:** 2026-10-05  
**Status:** FROZEN — first accepted SBND single-photon adaptation; do not alter.

---

## Algorithm Identity

| Item | Value |
|------|-------|
| Algorithm name | Fix2-v2 — graph-adjacent shower fallback |
| Algorithm commit | `8dddba5` (clus: Fix 2-v2 — graph-adjacent shower fallback, remove 50 cm proximity scan) |
| Diagnostic probe commit | `cd7e7b3` (Fix2 diagnostic: BFS topology probe for graph-distance measurement) |
| Base WCT commit | `251ff143` (clus: preserve matching bundle provenance for NuGraph4) |
| Repository | wct-dev (Wire-Cell Toolkit, SBND single-photon development branch) |

### Commit ancestry
```
cd7e7b3 Fix2 diagnostic: BFS topology probe for graph-distance measurement
8dddba5 clus: Fix 2-v2 — graph-adjacent shower fallback, remove 50 cm proximity scan
e302f5f fix2: add proximity fallback for shower-typed conversion gap
d2ed206 clus: Fix 2 — one-hop vertex extension for conversion-gap photon showers
251ff14 clus: preserve matching bundle provenance for NuGraph4
```

The A/B study was run with commit `cd7e7b3` (diagnostic probe active, read-only). The frozen production algorithm is `8dddba5` (no diagnostic overhead).

---

## Algorithm Description

Fix2-v2 runs a two-stage shower candidate collection inside `singlephoton_tagger()`
(`NeutrinoTaggerSinglePhoton.cxx`):

**Stage 1 (direct):** Look up `map_vertex_to_shower[main_vertex]`. Evaluate usable-shower gate:
`pdg==11 AND energy>20 MeV AND badreco1`. If any direct shower passes, stop.

**Stage 2 (fallback, only when Stage 1 finds no usable shower):** Traverse ALL incident PRGraph
edges from `main_vertex` (regardless of edge type). For each neighbor vertex `V1`, look up
`map_vertex_to_shower[V1]` and add previously-unseen showers to the candidate pool. Select the
best candidate by the same downstream logic (`singlephoton_tagger()` shower selection loop).

The algorithm is bounded by the existing PRGraph. It does not use Euclidean distance and cannot
cross graph-disconnected components.

---

## Built Library

| Field | Value |
|-------|-------|
| Library | `build/libWireCellClus.so` |
| MD5 | `9cff76d0d81a4b6c45a88908e78e73e4` |
| SHA-256 | `dd0422497a2d6d9a7ee8a8082850394d796c0d6537d445f17076067576c7eb57` |
| Size | 393 MB |
| Build timestamp | 2026-10-05 16:40 UTC |

The library was built on Sophia (ALCF) with the standard SBND Wire-Cell software stack. The
build used the `patched/` environment (LD_PRELOAD hook or equivalent per the run script).

---

## Compiler / Environment

Built on Sophia at ALCF. Software environment from the SBND UPS product stack as configured
in `control/` and the PBS scripts. Exact compiler version is embedded in the binary's `.comment`
section (`readelf -p .comment build/libWireCellClus.so`). The patched library replaced only
`libWireCellClus.so` relative to the baseline environment; all other libraries are unmodified.

---

## A/B Study Job IDs

| Batch | PBS job ID | Events covered | Notes |
|-------|-----------|----------------|-------|
| Batch 1 | `193321` | 0–19 | Array job |
| Batch 2 | `193326` | 20–39 | Array job |
| evt_0015 rerun | `193328` | 15 only | Rerun after node failure |
| Batch 3 | `193332` | 40–58 | Array job |
| 4-event rerun | `193336` | 34, 35, 38, 39 | After node failures on sophia-gpu-01 |
| evt_0038 final rerun | `193337` | 38 only | After two prior failures on sophia-gpu-01 |

**Input:** `baseline_v0/ncdelta_50evt/reco1/ncdelta_reco1.root` (59 NC Delta events, nskip 0–58)  
**Output:** `ab59/wirecell/evt_NNNN/tracking-pr.root` (patched) and `ab59/wirecell/evt_NNNN/tracking-pr.root` baseline comparison via `generate_comparison.py`

---

## Final 59-Event Safety Numbers

All safety criteria confirmed PASS:

| Metric | Value | Criterion |
|--------|-------|-----------|
| Events gaining `shw_sp_filled=1` | **5** | — |
| Events losing `shw_sp_filled=1` | **0** | KEY SAFETY PASS |
| Unexpected changes (direct_has_usable=true, result changed) | **0** | PASS |
| Events with `shw_sp_n_20mev_showers` change | 5 | — |
| `photon_flag` changes | 0 | — |

### Event class summary

| Class | Count |
|-------|-------|
| UNCHANGED_DIRECT_SUCCESS | 33 |
| RECOVERED_BY_FIX2 | 5 |
| FALLBACK_ACTIVATED_NO_RECOVERY | 19 |
| NO_NEUTRINO_CANDIDATE | 2 |
| Total | 59 |

### Recovered events

| evt_idx | RSE | Signal E (MeV) | BFS hops | vtx_type |
|---------|-----|--------------|----------|---------|
| evt_0012 | 50:0:232 | 167.6 | 1 | 3 |
| evt_0014 | 50:0:449 | 121.6 | 1 | 1 |
| evt_0016 | 50:0:499 | 23.6 | 1 | 2 |
| evt_0020 | 60:0:153 | 153.8 | 1 | 2 |
| evt_0026 | 70:0:274 | 90.4 | 1 | 3 |

**BDT selection change:** baseline 3 → patched 4 pre-FV events. Newly selected: evt_0020 (153.8 MeV).

---

## Git Tag

Annotated tag `sbnd-singlephoton-fix2-v2-20261005` was created in the wct-dev repository
pointing to commit `cd7e7b3` (the diagnostic probe used in the A/B study; the frozen production
algorithm is `8dddba5`). The tag was NOT pushed.

To recreate:
```bash
cd wct-dev
git tag -a sbnd-singlephoton-fix2-v2-20261005 cd7e7b3 \
  -m "Fix2-v2: graph-adjacent shower fallback, 59-event A/B study PASS, 5/59 recovered, 0 regressions"
```

---

## Related Documents

- `ab59/FIX2_AB59_REPORT.md` — full 59-event A/B study report
- `ab59/tables/fix2_ab59_event_comparison.csv` — per-event classification
- `ab59/tables/fix2_no_recovery_failure_census.csv` — 19 no-recovery events census
- `docs/EVT0054_FAILURE_DIAGNOSIS.md` — evt_0054 pdg=13 downstream failure
- `docs/SHOWER_PDG_FAILURE_AUDIT.md` — PDG misidentification source archaeology
- `baseline_v0/docs/SBND_1GAMMA_OBSTACLE_LOG.md` — OBS-008 status update
