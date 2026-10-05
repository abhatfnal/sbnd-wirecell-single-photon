# MicroBooNE Single-Photon Offline Scorer — microboone_1gamma_v0

Offline evaluation of the four original MicroBooNE single-photon TMVA BDT models against
the SBND `baseline_v0` frozen reconstruction outputs.

## What this is

This directory contains a standalone offline scorer that reads existing `tracking-pr.root`
files from the frozen `baseline_v0` NC Delta 59-event sample and evaluates the four
MicroBooNE single-photon BDTs. No reconstruction code is modified.

## Invocation

```bash
cd /lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/analysis/microboone_1gamma_v0
python3 score_microboone_bdts.py
```

Requirements: Python ≥ 3.8, uproot ≥ 5.x, numpy (all available on Sophia login node).

## Input paths

| Resource | Path |
|----------|------|
| Frozen baseline events | `/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/baseline_v0/ncdelta_50evt/wirecell/evt_NNNN/tracking-pr.root` |
| BDT XML models | `/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/reference/sbnd_single_photon_microboone_reference_20261005/weights/` |

## Output files

| File | Description |
|------|-------------|
| `tables/ncdelta_microboone_bdt_scores.csv` | Per-event BDT scores and failure reasons |
| `tables/ncdelta_microboone_cutflow.csv` | Sequential cut-flow counts |
| `tables/ncdelta_reco_failure_taxonomy.csv` | Per-event failure classification |

## Constraints

- Do NOT modify any `tracking-pr.root` or `nugraph.h5`
- Do NOT modify the XML BDT models
- Do NOT retrain or tune anything
- Do NOT use fresh-50evt WireCell outputs (different WCT commit)
- This directory is OUTSIDE `baseline_v0/` and must never overwrite baseline files

## Key results (2026-10-05)

- 33/59 events evaluable for all four BDTs
- 2/59 events pass full pre-FV MicroBooNE nominal selection
- Previous audit cap of ≤17 was wrong: `br_filled=0` is NOT a evaluability blocker;
  `shw_sp_filled=1` (33 events) is the correct mechanical gate
- `reco_nuvtxY` maps to `T_kine.kine_nu_y_corr` (direct equivalent found — `other` BDT unlocked)

## Cross-validation

```bash
# Inside sbndcode apptainer container with larsoft env sourced:
root -q -l validate_tmva_vs_root.C
# Expected: numu score for evt_0001 ≈ 2.9060 (within 1e-4 of Python result)
```
