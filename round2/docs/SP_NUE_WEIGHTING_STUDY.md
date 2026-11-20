# SP nue class-weighting study (WCL1116 development)

Date: 2026-11-20. Rules: `SP_BDT_WCL1116_FULL_DEVELOPMENT_PLAN.md` §3 (committed in 179cc58 before any fit). Results:
`validation/wcl1116_full_dev_nue_{dv2_split_move,dv2_snap}.json`.
- Everything is fitted on FIT. The choice is made on NESTED VALIDATION, and the existing holdout is shown afterwards.
- These are development numbers, not independent evaluation.
- Fixed: the 56 inputs, depth 5, 300 trees, eta 0.1, subsample 0.8, colsample 1 / 0.5 / 0.5, gamma 0.2, seed 1 and
  `base_score` 0. Only the per-class weights change, normalised to mean 1.

Rows: FIT 7,052 + / 85,428 − (split-move); NESTED VALIDATION 1,767 + / 21,195 −. Natural ratio about 1 : 12.

| split-move | `UNWEIGHTED_BASELINE` | `THESIS_PRIOR_APPROX` (4 : 1) | `BALANCED_STRESS_TEST` (1 : 1) |
|---|---:|---:|---:|
| row weight +/− | 1 / 1 | 2.62 / 0.87 | 6.56 / 0.54 |
| **nested-validation ROC AUC** | **0.9624** | 0.9620 | 0.9618 |
| nested-validation PR AUC | **0.748** | 0.744 | 0.744 |
| FIT − validation gap | 0.018 | 0.021 | 0.022 |
| background acceptance at legacy signal eff. (80.0 %) | 5.57 % | 5.52 % | 5.65 % |
| signal eff. at legacy background acceptance (13.4 %) | 91.9 % | 91.7 % | 91.9 % |
| Brier score (natural prevalence) | **0.034** | 0.040 | 0.068 |
| mean sigmoid(margin): signal / background | 0.54 / 0.04 | 0.68 / 0.07 | 0.82 / 0.13 |
| Spearman of scores vs unweighted | 1 | 0.976 | 0.968 |
| top-10 gain overlap with unweighted / gain-share Spearman | — | 9 / 0.981 | 8 / 0.951 |
| *existing holdout ROC AUC (after the choice)* | *0.9582* | *0.9582* | *0.9572* |

| snap | unweighted | thesis prior | balanced |
|---|---:|---:|---:|
| nested-validation ROC AUC | **0.9574** | 0.9566 | 0.9558 |
| nested-validation PR AUC | 0.723 | **0.724** | 0.717 |
| FIT − validation gap | 0.021 | 0.025 | 0.026 |
| background acceptance at legacy signal eff. (79.2 %) | 5.98 % | 5.98 % | 6.19 % |
| signal eff. at legacy background acceptance (13.9 %) | 91.9 % | 91.3 % | 90.7 % |
| Brier score | **0.036** | 0.042 | 0.072 |
| *existing holdout ROC AUC* | *0.9517* | *0.9519* | *0.9506* |

The legacy XML on the same nested-validation rows has ROC AUC 0.922 / 0.917 and PR AUC 0.507 / 0.501.

## Reading

- **Weighting does not improve ranking.** Nested-validation ROC AUC changes by −0.0004 / −0.0006 (split-move) and
  −0.0008 / −0.0016 (snap). The operating points move by ≤ 0.6 points, inside the statistical spread of 1.8k validation
  positives.
- It mainly **shifts the score scale**: the predicted signal fraction rises with the weight, and the Brier score at the
  natural prevalence worsens (0.034 → 0.040 → 0.068). Up-weighting the positives also slightly **widens the FIT −
  validation gap**: they are fitted harder.
- The feature structure is stable. The top inputs are `shw_sp_shw_vtx_dis`, `shw_sp_length_total`,
  `shw_sp_E_indirect_max_energy` and `shw_sp_length_main` in every variant.
- Split-move ranks better than snap in every variant, so the qualitative vertex-mode result is unchanged.

**WCL1116 DEVELOPMENT WEIGHTING RECOMMENDATION: `UNWEIGHTED_BASELINE`.**
- By the pre-registered rule, no weighted variant gains ≥ 0.002 nested-validation AUC in either mode.
- The thesis-like 1 : 4 prior and the balanced stress test are monotone re-scalings of nearly the same ranking. A
  later validation-only threshold absorbs a prior shift, so it is not a reason to weight.
- This is development evidence for the final-domain decision. **No final Round-2 weighting is chosen.**
