# Round-2 evaluation contract: which Round-1 baseline to compare with

Date: 2026-11-17. Status: conceptual contract, written after the Round-1 scorer correction (`LEGACY_SCORER_CORRECTION_IMPACT.md`, verdict MATERIAL). It changes no code and trains nothing.

## Rule

Any Round-2 claim of improvement (new reconstruction, retrained or replaced models, new cuts) is measured against **the source-faithful Round-1 legacy scorer**, never against the accidental as-run implementation. The as-run result is kept only as a diagnostic, so that the effect of the scorer-convention correction itself is never mistaken for a reconstruction or model improvement.

## Three reference points (always reported side by side)

| label | definition | role | NC-Delta efficiency (provisional TPC box, `any`, 35 MeV) |
|---|---|---|---|
| **R1-as-run** | frozen XMLs; cuts on the bare TMVA response `v`; real `kine_pio_flag` (`legacy_as_run`) | HISTORICAL DIAGNOSTIC, not a baseline | 1,153 / 12,427 = 9.28 % |
| **R1-source-faithful** | frozen XMLs; cuts on `log10((1+v)/(1-v))`; `kine_pio_flag = 0` (`legacy_source_faithful`) | **the Round-1 BASELINE** | 833 / 12,427 = 6.70 % |
| **R2** | new reconstruction and / or new models | the thing under test | to be measured |

The decomposition of the correction (A OLD / B SCORE ONLY / C PIO FLAG ONLY / D FULL = 1,153 / 831 / 1,161 / 833) is part of the reference record: a Round-2 change that moves the selection by less than the A-to-D gap must say which side of that gap it is on.

## Required for every Round-2 comparison

1. **Same events, same denominator, same truth conventions** for R1-source-faithful and R2 (denominator, proton threshold, candidate policy and any fiducial volume only once the analysis decisions D / E / F are recorded; until then the provisional TPC box and 35 MeV, labelled as conventions).
2. **Both R1 rows are produced by the one code path** (`src/sbnd_single_photon/legacy_scorer.py`, modes `legacy_as_run` and `legacy_source_faithful`, and `scripts/legacy_scorer_rebuild.py`); the thresholds stay 0.4 / 0.2 / -0.05 / -1.0 on the stated score.
3. **Improvement is claimed only relative to R1-source-faithful.** A gain relative to R1-as-run alone is a statement about the scorer convention, not about Round 2.
4. **Backgrounds are compared under the same convention**: the corrected R1 non-signal BNB-CV selection is 282 events (150 / 93 / 39); the as-run 635 is not a valid comparison point (it contained 175 intrinsic nue-CC events removed by the real `nue` cut).
5. **Reference validity caveat travels with R1-source-faithful**: no stored MicroBooNE single-photon score or live TMVA exists on EAF, so the corrected scorer is validated by source reading and bit-for-bit as-run reproduction, not by comparison with production scores. If a stored-score reference becomes available it must be compared before Round-2 results are quoted (N compared, max / median difference, decision flips).
6. **Training hygiene**: the official Gen2 NC-Delta sample is an evaluation sample; nothing in the correction or in this contract allows it as a training input.
7. Statistical conventions unchanged (Wilson 68 % intervals; Poisson errors on counts; no S/B, purity or significance until the beam-off normalisation (G) and flash-time reference (H) are resolved).

## What stays as a diagnostic

`tables/legacy_scorer_correction/impact_configurations.csv`, `cutflow_by_config_*.csv`, `event_flips.csv` and the A_old candidate tables (`$SP_DATA/legacy_scorer_correction/*_candidates_A_old.parquet`) are the permanent record of the as-run behaviour and of exactly which events the correction moves (335 signal and 366 BNB events leave the selection, 15 and 8 enter).
