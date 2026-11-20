# SP numu: dependence on the upstream νμ chain (DIAGNOSTIC ablations)

Date: 2026-11-20. Rules: `SP_BDT_WCL1116_FULL_DEVELOPMENT_PLAN.md` §5. Results:
`validation/wcl1116_full_dev_numu_{dv2_split_move,dv2_snap}.json`.

**Purpose.** The collaboration sees a data / MC discrepancy in the upstream νμ chain, especially for exiting or
uncontained muons. This study quantifies how much SP numu leans on it.
- It does **not** retrain Xuyang/Matteo's classifier.
- The ablated variants are **diagnostics, never candidate models**. They do not bypass the collaboration's upstream νμ
  freeze.

Every variant is fitted on FIT with the frozen 73-input development spec minus the named inputs; the numbers are
NESTED VALIDATION. The upstream family is the `kind == upstream_score` inputs of the audited feature list:
`numu_score` (νμ final BDT) and `numu_1_score` (νμ level-1).

| split-move | A full (73) | B without `numu_score` (72) | C without the upstream family (71) |
|---|---:|---:|---:|
| ROC AUC | **0.9789** | 0.9760 (−0.0029) | 0.9760 (−0.0029) |
| PR AUC | 0.957 | 0.953 | 0.952 |
| background acceptance at the legacy signal eff. (83.9 %) | **3.35 %** | 3.79 % | 3.61 % |
| signal eff. at the legacy background acceptance (6.58 %) | 91.5 % | 91.0 % | 91.0 % |
| Spearman with the full model | 1 | 0.977 | 0.974 |
| top-10 gain overlap with the full model | — | 9 | 7 |
| signal rows changing pass/fail at the equal-efficiency point (of 1,761) | — | 58 + 58 | 57 + 57 |
| background rows changing (of 3,935) | — | 24 lost, 41 gained | 30 lost, 40 gained |
| *existing holdout ROC AUC* | *0.9752* | *0.9736* | *0.9732* |

| snap | A | B | C |
|---|---:|---:|---:|
| ROC AUC | **0.9749** | 0.9734 (−0.0015) | 0.9720 (−0.0029) |
| background acceptance at the legacy signal eff. | 3.92 % | 4.05 % | 4.25 % |

The legacy XML on the same rows: 0.961 / 0.958.

## Reading

- **SP numu is only mildly dependent on the upstream νμ scores.**
  - Removing `numu_score`, or the whole upstream family, costs 0.0015–0.003 AUC.
  - Background acceptance at equal signal efficiency rises by 0.3–0.4 points: +8–13 % relative.
  - Every ablated variant still beats the legacy XML clearly: 0.976 vs 0.961.
- **When the upstream score is removed, the muon-track inputs take over.** `numu_cc_3_track_length`,
  `numu_cc_3_max_muon_length` and `numu_cc_3_max_length_all` lead the gain ranking. Most of the upstream score's
  information is therefore also available from those inputs, which is why the loss is small.
- **Risk if the upstream νμ model changes substantially.**
  - The direct exposure is bounded: at most about 0.003 AUC, or 8–13 % more νμ CC background at fixed efficiency, if
    the upstream score lost its value entirely.
  - The real risk is a *shift* of `numu_score` between MC and data, which a fixed SP numu would inherit. Data / MC
    differences for exiting muons also reach SP numu through the `numu_cc_3_*` track-length inputs.
  - So SP numu must still be retrained on the **collaboration-frozen** upstream outputs in the final domain. Removing
    the scores is not the remedy: it costs performance and leaves the muon-track inputs.
