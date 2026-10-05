# SBND Wire-Cell Single-Photon

Development and analysis repository for an inclusive single-photon selection in
SBND using Wire-Cell reconstruction.

This project ports and validates the MicroBooNE Wire-Cell inclusive
single-photon selection on SBND while keeping reconstruction changes, offline
analysis, and physics-selection studies explicitly separated.

## Current milestone

The current validated milestone includes:

- frozen SBND Wire-Cell `baseline_v0`
- 59-event dedicated NC Delta radiative sample reconstructed through Wire-Cell
- original four MicroBooNE single-photon BDTs recovered and evaluated offline
- Python BDT evaluator validated against ROOT/TMVA:
  132/132 comparisons pass
- Fix2-v2 graph-adjacent shower fallback tested in a controlled 59-event A/B study

### Fix2-v2 result

- fallback activated: 24/59 events
- reconstructed single-photon feature block recovered: 5 events
- BDT-evaluable events: 33 -> 38
- MicroBooNE pre-FV reference selection: 3 -> 4
- newly selected event: evt_0020
- previously working events lost: 0
- unexpected changes without fallback: 0

No BDT thresholds were tuned on the NC Delta sample.

## Software layers

### Wire-Cell Toolkit

The actual reconstruction adaptation is maintained in a separate WCT
development branch.

Frozen baseline:

`251ff143bf6fa0c212ead0b8453abe94afcd2dda`

Fix2-v2 algorithm:

`8dddba5be2ccbb0ee1146e990fce89808bbd2816`

Diagnostic instrumentation used for the 59-event A/B study:

`cd7e7b39e1c101da3c31e09850e367934f621950`

Patch snapshots and provenance are stored under `provenance/`.

### larwirecell

No larwirecell code changes were made for this single-photon adaptation.

Pinned baseline commit:

`9295e2a3`

### Offline analysis

This repository contains the offline BDT evaluation, TMVA validation,
cut flows, reconstruction diagnostics, failure taxonomy, provenance,
job templates, and A/B studies.

## Repository layout

- `analysis/` — offline scorer, TMVA validation, diagnostics, and tables
- `baseline_v0/` — frozen-baseline documentation and lightweight outputs
- `reconstruction_studies/fix2_v2/` — Fix2-v2 development and A/B results
- `selection/` — frozen MicroBooNE reference-selection definitions
- `jobs/` — job/build templates used for reproducibility
- `provenance/` — software SHAs, checksums, WCT patches, and reference metadata

Large event files (`*.root`, `*.h5`), compiled libraries, build products,
and MicroBooNE XML model files are intentionally not committed.

## Analysis philosophy

The development sequence is:

1. faithfully reproduce the MicroBooNE selection,
2. quantify SBND reconstruction failure modes,
3. make isolated reconstruction adaptations,
4. validate each change with controlled A/B studies,
5. only later optimize using signal and generic-BNB background samples.

The dedicated NC Delta sample is used for signal reconstruction validation,
not for tuning the final SBND analysis thresholds.
