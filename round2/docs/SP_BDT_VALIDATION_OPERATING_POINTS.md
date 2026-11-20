# SP BDTs: validation-only operating points and the joint four-cut evaluator (WCL1116 development)

Date: 2026-11-20. Tool `tools/sp_operating_points.py`. Results:
- `validation/sp_operating_points_{dv2_split_move,dv2_snap}.json`;
- tables `validation/op_tables/` (per-model threshold / ROC / PR tables; joint Pareto fronts).

**DEVELOPMENT ROC-EQUIVALENT DIAGNOSTIC — NOT ROUND2 CUT. NO THRESHOLD FROZEN.**
- Rows: NESTED VALIDATION only; the `FIT_BASELINE` models are fitted on FIT.
- No FermiGrid product was read.
- Rates are per candidate row of each sample. The filtered samples have no usable exposure, so they are never mixed
  with exposure weights.
- **Context only:** the EAF frozen-selection replay (6.70 % → 15.60 % signal; selected non-signal 282 → 685) is not an
  input.

## 1. Per model (split-move; snap in the JSON)

| model | dev / legacy ROC AUC | legacy at its historical cut: signal / background | new at equal signal: background | new at equal background: signal |
|---|---|---|---|---|
| SP numu (0.4) | 0.979 / 0.961 | 83.9 % / 6.58 % | **3.35 %** | **91.5 %** |
| SP other (0.2) | 0.916 / 0.834 | 57.9 % / 12.0 % | **2.51 %** | **80.1 %** |
| SP ncpi0 (−0.05) | 0.893 / 0.853 | 52.3 % / 9.72 % | **5.75 %** | **69.6 %** |
| SP nue (−1.0) | 0.962 / 0.922 | 80.0 % / 13.4 % | **5.57 %** | **91.9 %** |

Each threshold table is monotonic, which is tested.

**Signal efficiency by truth topology** (NC Δ sample signal rows; post-FSI primary protons > 35 MeV):

| model | legacy: 0p / 1p / ≥2p | new at equal signal: 0p / 1p / ≥2p | new at equal background: 0p / 1p / ≥2p |
|---|---|---|---|
| SP numu | 0.88 / 0.84 / 0.80 | 0.92 / 0.86 / **0.68** | 0.97 / 0.93 / 0.81 |
| SP other | 0.55 / 0.65 / 0.66 | 0.62 / 0.67 / 0.61 | 0.84 / 0.87 / 0.86 |
| SP ncpi0 | 0.58 / 0.53 / 0.29 | 0.68 / 0.50 / 0.39 | 0.79 / 0.75 / 0.53 |
| SP nue | 0.84 / 0.78 / 0.69 | 0.84 / 0.85 / 0.77 | 0.93 / 0.95 / 0.92 |

- At equal total signal efficiency, the new SP numu moves efficiency from ≥ 2p (0.80 → 0.68) to 0p. Multi-proton
  signal is the most νμ-CC-like.
- The new SP ncpi0 favours 0p (0.58 → 0.68).
- At equal background, every topology gains.

## 2. Joint four-cut evaluator (production order numu → other → ncpi0 → nue)

Nested-validation rows, split-move:
- 1,494 NC Δ signal (0p 681, 1p 689, ≥ 2p 124);
- 6,424 BNB background;
- 21,079 νe CC background;
- 20 EXT;
- 263 events with more than one preselected candidate.

| point | NC Δ signal eff. | BNB background acc. | 0p | 1p | ≥ 2p | νe CC acc. |
|---|---:|---:|---:|---:|---:|---:|
| **LEGACY_HISTORICAL** (0.4 / 0.2 / −0.05 / −1.0) | 27.1 ± 1.2 % | 0.75 ± 0.11 % (48) | 30.1 % | 27.1 % | 10.5 % | 1.08 % |
| **DEV_ROC_EQUIVALENT** (each model at its legacy-equal efficiency; not chosen on the joint) | **44.0 ± 1.3 %** | 0.78 ± 0.11 % (50) | **51.2 %** | **39.9 %** | **26.6 %** | 0.93 % |
| best grid vector at the legacy BNB acceptance (selected on these rows: optimistic) | 47.4 % | 0.75 % | 50.1 % | 48.8 % | 25.0 % | 0.95 % |
| snap: legacy / dev ROC-equivalent | 26.4 % / **41.2 %** | 0.65 % / 0.68 % | 30.6 / **49.0** % | 25.0 / **36.6** % | 10.7 / **23.8** % | 1.02 / 0.92 % |

**Cascade, split-move.** NC Δ efficiency / BNB acceptance after each cut:

| after | legacy | development |
|---|---|---|
| numu | 85.8 % / 25.4 % | 87.2 % / 18.6 % |
| other | 56.9 % / 9.3 % | 62.5 % / **2.7 %** |
| ncpi0 | 33.3 % / 1.7 % | 46.1 % / 1.0 % |
| nue | 27.1 % / 0.75 % | 44.0 % / 0.78 % |

**Reading.**
- On training-side validation rows, the retrained set keeps about **1.6× the NC Δ signal at the same BNB background
  acceptance**.
  - The largest absolute gain is for **0p (30 → 51 %)**, which is where the WCL1116 reconstruction recovers signal.
  - The largest relative gain is for ≥ 2p (×2.5).
- At the development ROC-equivalent point, the highest BNB component acceptances are νe CC (2.6 %) and NC π⁰ (2.5 %),
  then out-of-FV (1.7 %) and cosmic-partner (1.1 %); νμ CC is below 0.3 %. Accepted counts are about 50 rows, so each
  component is statistically limited.
- This is the training-domain answer to the Round-2 question: *SBND classifiers can restore rejection while keeping the
  recovered signal.* It is not an independent measurement, and **no joint threshold vector is chosen**.
- The full 9⁴ grid is in `$SP_WORK/wcl1116_full_dev/op/<mode>/joint_grid_<mode>.csv`; the Pareto front (123 / 129
  points) is in `validation/op_tables/joint_pareto_<mode>.csv`.

**Grid levels.**
- Per-model levels 0.80–0.98 and no cut were pre-declared.
- 0.50 / 0.60 / 0.70 were added after the first run, because the pre-declared grid never reached the legacy joint
  background acceptance.
- That change is reporting coverage only.
