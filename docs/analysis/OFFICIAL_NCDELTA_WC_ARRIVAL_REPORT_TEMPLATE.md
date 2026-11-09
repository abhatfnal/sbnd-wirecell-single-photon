# Official NC Delta -> N gamma Wire-Cell sample: arrival report  (template; filled automatically by `scripts/run_official_signal_baseline.py`)

Sample label: {{LABEL}}    Truth region V: {{REGION}}    Policy comparison: any (analysis) vs first    Code commit: {{GIT_COMMIT}}
Frozen conventions: `wc.valid == 1` required; proton threshold 35 MeV (provisional); region V is a parameter, not an FV; truth is evaluation only.
Every number below is produced by code from the registered files; a section that cannot be computed says `NOT COMPUTED` and why. Uncertainties are exact
(Clopper-Pearson, 68.3 %) binomial intervals unless stated.

## 1. File inventory
{{FILE_INVENTORY}}

## 2. Provenance (acceptance gate: REQUIRED / EXPECTED / INFORMATIONAL)
{{PROVENANCE}}

## 3. Event-key completeness (against the official flatCAF truth census)
{{EVENT_KEYS}}

## 4. wc.valid
{{WC_VALID}}

## 5. Candidate efficiency
{{CANDIDATE_EFF}}

## 6. Frozen cutflow (all truth events of V in the denominator, by truth class)
{{CUTFLOW}}

## 7. Total signal efficiency (selected / N_signal_truth(V))
{{EFF_TOTAL}}

## 8. Truth 0p efficiency
{{EFF_0P}}

## 9. Truth 1p efficiency
{{EFF_1P}}

## 10. Truth -> reco proton migration (final selection, policy any; last column = not selected / not reconstructed / never arrived)
{{MIGRATION}}

## 11. Reco 1gamma0p yield
{{YIELD_1G0P}}

## 12. Reco 1gamma1p yield
{{YIELD_1G1P}}

## 13. Delta0 / Delta+ diagnostics
{{DELTA_DIAG}}

## 14. Comparison with the natural-CV rehearsal (statistical consistency only; a disagreement is a finding, not something to fix)
{{REHEARSAL_COMPARISON}}

## 15. Any unexpected discrepancy
{{DISCREPANCIES}}
