# Dependency graph of the four frozen single-photon BDTs: which inputs are outputs of other BDTs / taggers

Date: 2026-11-11. Branch `analysis/ncdelta-remaining-frozen-stage-audit-20261111`. Audit only. SOURCE = fg1 commit `4b6853d4` (`UbooneNumuBDTScorer.cxx`, `UbooneNueBDTScorer.cxx`, `NeutrinoTaggerNuMu.cxx`, `NeutrinoTaggerSinglePhoton.cxx`, `NeutrinoKinematics.cxx`); MEASURED = official Gen2 NC-Delta stage populations. Edge table: `tables/remaining_stage_audit/bdt_dependency_edges.csv`; measured fractions: `upstream_bdt_inputs.csv`. No optimisation.

## 1. The graph

```
 detector objects -> pattern recognition (segments, showers, vertices)
        |                                  |
        |  NeutrinoTaggerNuMu              |  NeutrinoTaggerSinglePhoton            NeutrinoKinematics
        |  numu_cc_flag_* / numu_cc_N_*    |  shw_sp_* (max shower, br1..4,         kine_pio_* (best pi0 pair)
        |  (flag 1, 2, 3 features)         |  lem, hol/lol, pio_1/2, dQ/dx, counters)
        v                                  v                                          v
 UbooneNumuBDTScorer  --- sub-BDTs: numu_1 (-0.4), numu_2 (-0.1), numu_3 (-0.2, computed, not fed to the xgboost),
        |                            cosmict_10 (0.7)   [defaults when the sub-BDT has nothing to score]
        |        --- xgboost numu BDT -> numu_score = log10((1+v)/(1-v))
        |
 UbooneNueBDTScorer   --- 15 per-segment sub-BDTs: br3_3 (0.30) br3_5 (0.42) br3_6 (0.75) pio_2 (0.20) stw_2/3/4 (0.7/0.5/0.7)
        |                                          sig_1/2 (0.59/0.55) lol_1/2 (0.85/0.70) tro_1/2/4/5 (0.28/0.35/0.33/0.50)
        |        --- (xgboost nueCC BDT -> nue_score: NOT used by the frozen chain)
        v
 FROZEN SINGLE-PHOTON BDT STAGES (offline scorer, not stored in the CAF):
   numu  (73 inputs)  <- numu_1_score, numu_score               + 71 shw_sp_* / numu_cc_* observables
   other (146 inputs) <- numu_score, numu_1_score, numu_2_score, cosmict_10_score + 142 (cosmic tagger 59, shower, ...)
   ncpi0 (45 inputs)  <- the 15 nueCC-chain sub-BDT scores      + 12 kine_pio_* + 8 shw_sp_pio_* + counters / overlap checks
   nue   (56 inputs)  <- (none)                                  shw_sp_* only
```

* **The frozen `numu` stage consumes the output of another numu BDT** (`numu_score`, the single largest attribution of the stage, see the combined report) and of its sub-BDT `numu_1`; the frozen `other` stage consumes the same two plus `numu_2_score` and `cosmict_10_score`: **the `numu` and `other` rejections share `numu_score`** (an event rejected by one is partly rejected for the same reason by the other).
* **The frozen `ncpi0` stage consumes 15 sub-BDT scores of the nueCC scorer chain** (a third BDT family), 24 % of its attribution mass (combined report, section 7).
* **`nue` consumes no upstream score.**
* `shw_sp_n_20br1_showers`, `n_br1_showers` ... are **inputs of numu, ncpi0 and nue**: the multiplicity counter of the final `n_20br1 == 1` cut also feeds the BDTs.

## 2. Measured behaviour of the upstream inputs on the stage populations (official signal)

| downstream BDT | upstream input | scorer default | events at default | median (pass / fail) |
|---|---|---|---|---|
| numu | `numu_1_score` | -0.4 | 0.0% | -0.30 / -0.09 |
| numu | `numu_score` | none | n/a | -0.80 / 0.12 |
| other | `numu_score` | none | n/a | -0.70 / -0.96 |
| other | `numu_1_score` | -0.4 | 0.0% | -0.35 / -0.21 |
| other | `numu_2_score` | -0.1 | 99.7% | -0.10 / -0.10 |
| other | `cosmict_10_score` | 0.7 | 99.6% | 0.70 / 0.70 |
| ncpi0 | `tro_5_score` | 0.5 | 60.5% | 0.50 / 0.50 |
| ncpi0 | `tro_4_score` | 0.33 | 49.8% | 0.33 / 0.33 |
| ncpi0 | `tro_2_score` | 0.35 | 64.7% | 0.35 / 0.35 |
| ncpi0 | `tro_1_score` | 0.28 | 49.8% | 0.28 / 0.28 |
| ncpi0 | `stw_4_score` | 0.7 | 71.1% | 0.70 / 0.70 |
| ncpi0 | `stw_3_score` | 0.5 | 61.8% | 0.50 / 0.50 |
| ncpi0 | `stw_2_score` | 0.7 | 67.6% | 0.70 / 0.70 |
| ncpi0 | `sig_2_score` | 0.55 | 50.3% | 0.55 / 0.55 |
| ncpi0 | `sig_1_score` | 0.59 | 86.8% | 0.59 / 0.59 |
| ncpi0 | `pio_2_score` | 0.2 | 55.3% | 0.20 / 0.20 |
| ncpi0 | `lol_2_score` | 0.7 | 69.0% | 0.70 / 0.70 |
| ncpi0 | `lol_1_score` | 0.85 | 49.8% | 0.66 / 0.85 |
| ncpi0 | `br3_6_score` | 0.75 | 60.4% | 0.75 / 0.75 |
| ncpi0 | `br3_5_score` | 0.42 | 58.7% | 0.42 / 0.42 |
| ncpi0 | `br3_3_score` | 0.3 | 49.8% | 0.30 / 0.30 |

* `numu_1_score` and `numu_score` are continuous and never at default: the numu tagger fills them for every candidate of the population. The `other`-stage inputs `numu_2_score` (-0.1) and `cosmict_10_score` (0.7) are **at their scorer default for 99.7 % and 99.6 % of the events** (their sub-BDTs have nothing to score for the signal): they carry no information on signal events.
* The 15 nueCC-chain sub-scores are **at their scorer default for 50-87 % of the ncpi0-stage events** and never exactly 0 (the scorer ran everywhere); where they are not at default they differ little between survivors and rejected on the median (the median equals the default for most): the information is in the minority tail.
* **No score is stored in the CAF other than these sub-scores and `numu_score`** (written by the scorers into `wc.T_tagger`); the four frozen single-photon scores are computed offline.

## 3. Known source notes
`bdt-scorers-examination.md` (review of the two scorers, kept with the source) records, among others: the `log10((1+v)/(1-v))` transform can return +-inf or NaN for |v| >= 1 (no clamp); `numu_3_score` is computed but not given to the final xgboost (flagged for verification against the training XML); the scorer functions return their default when the per-object vectors are empty. These are source notes, **not verified here** and not acted on.
