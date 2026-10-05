# 59-Event A/B Study Provenance

**Study:** Fix2-v2 baseline vs patched, 59-event NC Delta signal sample  
**Date:** 2026-10-05

---

## Part C — Commit and Library Decision

**Algorithm freeze commit:** `8dddba5`  
Fix2-v2: all-edge one-hop neighbor fallback; 50 cm proximity scan removed.

**A/B study commit:** `cd7e7b3`  
Adds a read-only BFS topology probe (108 lines, logging only) after the candidate collection
block. The probe:
- identifies the max-energy shower in all showers (not just candidates)
- runs an exhaustive BFS from main_vertex to that shower's start_vertex
- logs `BFS_FOUND hops=N` or `BFS_NO_PATH` to spdlog

The diagnostic block does NOT modify `candidate_showers`, does NOT change any reconstruction
data structure, and does NOT affect `shw_sp_filled` or any other output branch. Reconstruction
behavior is bit-for-bit identical to `8dddba5`. The BFS probe adds O(V+E) read-only graph
traversal per event, negligible for 59 events.

**Decision:** Use `cd7e7b3` for the A/B study. The diagnostic output will provide per-event
graph connectivity information for Part J validation.

**Library:** `development/fix2_vertex_shower_onehop_20261005/build/libWireCellClus.so`  
**Built:** 2026-10-05 16:40 UTC  
**MD5:** `9cff76d0d81a4b6c45a88908e78e73e4`  
**Size:** 393 MB  
**Compiler:** GCC 12.1.0 (`/lus/flare/.../gcc/v12_1_0/`)  
**Flags:** `-ggdb3` (not stripped)

---

## Input Provenance

**Input file:**
```
/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/baseline_v0/ncdelta_50evt/reco1/ncdelta_reco1.root
```

**Events:** indices 0–58 (59 events, `--nskip N -n 1` per job)

**Frozen WCT config:**
```
/lus/eagle/projects/neutrinoGPU/abhat/sbnd/sample_generation_port/work/haiwang-current/integration-2026-09-08/reco-bundle-id-fix-validation-20260916/config-final/
```
FCL: `wcls-img-clus-matching-xin-prod.fcl`

**WCT base commit (production candidate):**
```
/lus/eagle/projects/neutrinoGPU/abhat/sbnd/sample_generation_port/work/latest_wct_master_migration_candidate_20260930
```

**Wire-Cell data snapshot:**
```
/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/runtime/wire-cell-data
```

**Baseline outputs (immutable):**
```
/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/baseline_v0/ncdelta_50evt/wirecell/
```
These are never overwritten. Patched outputs go to `ab59/wirecell/`.

---

## Output Layout

```
ab59/
├── jobs/
│   ├── run_ab59_array.pbs       # PBS array job (#PBS -J 0-58)
│   ├── run_ab59_template.sh     # Per-event shell script
│   └── submit_ab59.sh           # Submission wrapper
├── logs/
│   ├── run_ab59_0.out/err       # PBS stdout/err per array index
│   └── lar_ab59_evt_NNNN.log    # lar output per event
├── wirecell/
│   └── evt_NNNN/
│       └── tracking-pr.root
├── tables/
│   ├── fix2_ab59_event_comparison.csv   # Part F
│   └── fix2_ab59_bdt_comparison.csv     # Part H
└── docs/
    ├── PROVENANCE.md            # this file
    └── FIX2_AB59_REPORT.md     # Part L
```

---

## Constraints

- Do NOT overwrite existing `patched/evt_NNNN/` directories
- Do NOT modify any baseline_v0 file
- Do NOT retrain BDTs or change BDT thresholds
- Do NOT rerun Gen/G4/DetSim/Reco1 stages
- Do NOT introduce companion-cluster recovery
