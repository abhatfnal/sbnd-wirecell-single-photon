# SP other: boundary and upstream dependence (DIAGNOSTIC group ablations)

Date: 2026-11-20. Rules: `SP_BDT_WCL1116_FULL_DEVELOPMENT_PLAN.md` §5. Results:
`validation/wcl1116_full_dev_other_{dv2_split_move,dv2_snap}.json`.

**Purpose.** Measure how much SP other relies on the cosmic / boundary machinery that the next production changes,
and so how much retraining will matter.
- These are **robustness diagnostics only**. No ablated model is proposed for deployment.

Families come from the audited feature list and the toolkit `cosmic_tagger()` audit:
- **direct cosmic tagger:** 59 `cosmict_*` / `cosmic_*` reconstruction inputs;
- **upstream νμ:** the 4 `upstream_score` inputs of the νμ BDT scorer: `numu_score`, `numu_1_score`, `numu_2_score`
  and `cosmict_10_score`.

Fitted on FIT; NESTED VALIDATION shown.

| split-move | A full (146) | B no cosmic tagger (87) | C no upstream νμ (142) | D no both (83) |
|---|---:|---:|---:|---:|
| ROC AUC | **0.9158** | 0.9068 (−0.009) | 0.9071 (−0.009) | 0.8895 (−0.026) |
| PR AUC | 0.932 | 0.926 | 0.926 | 0.911 |
| background acceptance at the legacy signal eff. (57.9 %) | **2.51 %** | 2.71 % | 2.71 % | 3.90 % |
| signal eff. at the legacy background acceptance (12.0 %) | 80.1 % | 77.7 % | 77.5 % | 75.0 % |
| Spearman with the full model | 1 | 0.965 | 0.960 | 0.913 |
| top-10 gain overlap with the full model | — | 6 | 7 | 6 |
| *existing holdout ROC AUC* | *0.9149* | *0.9085* | *0.9060* | *0.8887* |

| snap | A | B | C | D |
|---|---:|---:|---:|---:|
| ROC AUC | **0.9115** | 0.9039 (−0.008) | 0.9037 (−0.008) | 0.8880 (−0.024) |
| background acceptance at the legacy signal eff. | 2.63 % | 3.75 % | 3.09 % | 4.47 % |

The legacy XML on the same rows: 0.834 / 0.834.

**Component acceptance at the equal-efficiency point.** Split-move, nested validation; legacy XML at 0.2 in the first
column.

| component (rows) | legacy | A | B | C | D |
|---|---:|---:|---:|---:|---:|
| NC without π⁰ (398) | 14.3 % | 2.5 % | 2.5 % | 1.5 % | 1.8 % |
| dirt (730) | 12.3 % | 2.3 % | 2.5 % | 2.9 % | 4.9 % |
| out-of-FV inside the TPC (80) | 16.3 % | 3.7 % | 5.0 % | 3.7 % | 6.2 % |
| cosmic-matched MC (284) | 7.4 % | 2.8 % | 3.2 % | 3.9 % | 3.9 % |
| EXT, nested validation (20 rows, 2 runs) | 5.0 % | 0 | 0 | 0 | 0 |
| EXT, *existing holdout* (224 rows) | *5.4 %* | *0.9 ± 0.6 %* | *0.9 ± 0.6 %* | *1.3 ± 0.8 %* | *1.3 ± 0.8 %* |

## Reading

- **Each family matters, and they overlap.**
  - Removing either the direct cosmic-tagger outputs or the upstream νμ scores costs about 0.009 AUC.
  - Removing both costs 0.026, almost three times either alone. Each family partly substitutes for the other:
    `numu_score` is built mostly from cosmic-tagger outputs.
  - The gain share of the 63 cosmic + upstream inputs is about 21 % (`SP_BDT_FULL_DEVELOPMENT_SUMMARY.md` §5).
- **What the boundary-dependent inputs do.**
  - Without them (D), the model loses dirt and out-of-FV rejection: dirt 2.3 → 4.9 %, out-of-FV 3.7 → 6.2 %. These are
    exactly the components a boundary definition governs.
  - Its NC-without-π⁰ rejection does not degrade (2.5 → 1.8 %).
  - Even D (0.890) is far above the legacy XML (0.834). The shower inputs alone carry most of the SBND gain.
- **EXT.** On the existing holdout, which has 224 rows (nested validation has only 20), EXT acceptance stays at about
  1 % for every variant, against 5.4 % for legacy. Off-beam cosmic rejection is robust to removing either family, at
  the precision available.
- **Implication for the final domain.**
  - The effective / non-box boundary changes the inputs that carry about a fifth of SP other's gain, and they govern
    its dirt / out-of-FV rejection.
  - The changed cosmic-tagger values move the learned response even where the AUC impact looks modest.
  - **SP other must be retrained in the final reconstruction domain,** with the beam-off training half reprocessed
    there.
  - The ablations show that a removed family costs 0.009–0.026 AUC. So retraining on the final-domain values is better
    than dropping the boundary-dependent inputs.
