# Official NC Delta -> N gamma Wire-Cell sample: arrival report  (template; filled automatically by `scripts/run_official_signal_baseline.py`)

Sample label: official_gen2_ncdelta    Truth region V: active_tpc    Policy comparison: any (analysis) vs first    Code commit: 56043c52b80c7b6af303b1295a7dab03aa4595b5
Frozen conventions: `wc.valid == 1` required; proton threshold 35 MeV (provisional); region V is a parameter, not an FV; truth is evaluation only.
Every number below is produced by code from the registered files; a section that cannot be computed says `NOT COMPUTED` and why. Uncertainties are exact
(Clopper-Pearson, 68.3 %) binomial intervals unless stated.

## 1. File inventory
| files | opened_without_error |
|---|---|
| 9150 | 9150 |

## 2. Provenance (acceptance gate: REQUIRED / EXPECTED / INFORMATIONAL)
| id | level | status | observed |
|---|---|---|---|
| rec_trees_present | REQUIRED | PASS | True |
| entries_aligned | REQUIRED | PASS | True |
| ids_aligned | REQUIRED | PASS | True |
| wc_valid_present | REQUIRED | PASS | True |
| truth_trees_present | REQUIRED | PASS | True |
| genie_record_present | REQUIRED | PASS | True |
| baseline_branches_present | REQUIRED | PASS | True |
| unreadable_files | REQUIRED | PASS | 0 |
| event_keys_accounted | REQUIRED | PASS | True |
| no_duplicate_events | REQUIRED | PASS | 0 |
| no_unexpected_events | REQUIRED | PASS | 0 |
| no_unit_mismatch | REQUIRED | PASS | 0 |
| wc_valid_accounted | REQUIRED | PASS | True |
| no_missing_events | EXPECTED | FAIL | 1 |
| same_chain_as_fg1 | REQUIRED | PASS | True |
| scn_vertex_model | REQUIRED | PASS | uboone/scn_vtx/t48k-m16-l5-lr5d-res0.5-CP24.pth |
| no_dv2_max | REQUIRED | PASS | False |
| no_fix2 | REQUIRED | PASS | False |
| no_alternative_bdt | REQUIRED | PASS | False |
| no_hidden_selection_change | REQUIRED | PASS | True |
| schema_md5_matches_fg1 | EXPECTED | PASS | True |
| single_schema | EXPECTED | PASS | 1 |
| single_dl_weights | EXPECTED | PASS | 1 |
| wct_commit_declared | EXPECTED | PASS | 4b6853d4 (HaiwangYu/wire-cell-toolkit sbnd-wc-flatcaf) |
| larwirecell_commit_declared | EXPECTED | PASS | ad5d942 (sbnd-wc-flatcaf) |
| sbndcode_declared | EXPECTED | PASS | v10_14_02_03 e26:prof |
| wct_version_strings | INFORMATIONAL | PASS | ['sbnd-dlvtx-35-pre-master-merge-2026-09-02-424-g78f81c64'] |
| bdt_weights_dir_strings | INFORMATIONAL | PASS | ['uboone/weights'] |
| n_wc_branches | INFORMATIONAL | PASS | [2401] |

## 3. Event-key completeness (against the official flatCAF truth census)
| expected_events | incoming_rows | represented | represented_wc_valid | represented_wc_invalid | missing | duplicate_keys | duplicate_rows | unexpected_rows | unit_mismatch | complete |
|---|---|---|---|---|---|---|---|---|---|---|
| 13773 | 13772 | 13772 | 13772 | 0 | 1 | 0 | 0 | 0 | 0 | False |

## 4. wc.valid
| arrived | wc_valid | wc_invalid | missing |
|---|---|---|---|
| 12426 | 12426 | 0 | 1 |

## 5. Candidate efficiency
| group | N | fraction | lo68 | hi68 |
|---|---|---|---|---|
| all | 11331 | 0.9118 | 0.9092 | 0.9144 |
| 0p | 5210 | 0.8886 | 0.8844 | 0.8928 |
| 1p | 5170 | 0.9304 | 0.9268 | 0.9338 |
| >=2p | 951 | 0.9444 | 0.9362 | 0.9516 |

## 6. Frozen cutflow (all truth events of V in the denominator, by truth class)
| group | stage | N | fraction | lo68 | hi68 |
|---|---|---|---|---|---|
| all | truth_denominator | 12427 | 1 | 0.9999 | 1 |
| 0p | truth_denominator | 5863 | 1 | 0.9997 | 1 |
| 1p | truth_denominator | 5557 | 1 | 0.9997 | 1 |
| >=2p | truth_denominator | 1007 | 1 | 0.9982 | 1 |
| all | wc_valid | 12426 | 0.9999 | 0.9997 | 1 |
| 0p | wc_valid | 5863 | 1 | 0.9997 | 1 |
| 1p | wc_valid | 5556 | 0.9998 | 0.9994 | 1 |
| >=2p | wc_valid | 1007 | 1 | 0.9982 | 1 |
| all | candidate | 11331 | 0.9118 | 0.9092 | 0.9144 |
| 0p | candidate | 5210 | 0.8886 | 0.8844 | 0.8928 |
| 1p | candidate | 5170 | 0.9304 | 0.9268 | 0.9338 |
| >=2p | candidate | 951 | 0.9444 | 0.9362 | 0.9516 |
| all | n20mev | 8080 | 0.6502 | 0.6459 | 0.6545 |
| 0p | n20mev | 3956 | 0.6747 | 0.6685 | 0.6809 |
| 1p | n20mev | 3468 | 0.6241 | 0.6175 | 0.6306 |
| >=2p | n20mev | 656 | 0.6514 | 0.6358 | 0.6668 |
| all | bdt_evaluable | 8034 | 0.6465 | 0.6422 | 0.6508 |
| 0p | bdt_evaluable | 3936 | 0.6713 | 0.6651 | 0.6775 |
| 1p | bdt_evaluable | 3447 | 0.6203 | 0.6137 | 0.6269 |
| >=2p | bdt_evaluable | 651 | 0.6465 | 0.6308 | 0.6619 |
| all | numu | 5007 | 0.4029 | 0.3985 | 0.4074 |
| 0p | numu | 2446 | 0.4172 | 0.4107 | 0.4237 |
| 1p | numu | 2174 | 0.3912 | 0.3846 | 0.3979 |
| >=2p | numu | 387 | 0.3843 | 0.3686 | 0.4003 |
| all | other | 2781 | 0.2238 | 0.22 | 0.2276 |
| 0p | other | 1157 | 0.1973 | 0.1921 | 0.2027 |
| 1p | other | 1373 | 0.2471 | 0.2412 | 0.253 |
| >=2p | other | 251 | 0.2493 | 0.2354 | 0.2636 |
| all | ncpi0 | 1313 | 0.1057 | 0.1029 | 0.1085 |
| 0p | ncpi0 | 574 | 0.0979 | 0.094 | 0.1019 |
| 1p | ncpi0 | 647 | 0.1164 | 0.1121 | 0.1209 |
| >=2p | ncpi0 | 92 | 0.09136 | 0.08221 | 0.1014 |
| all | nue | 1313 | 0.1057 | 0.1029 | 0.1085 |
| 0p | nue | 574 | 0.0979 | 0.094 | 0.1019 |
| 1p | nue | 647 | 0.1164 | 0.1121 | 0.1209 |
| >=2p | nue | 92 | 0.09136 | 0.08221 | 0.1014 |
| all | n20br1 | 1153 | 0.09278 | 0.09017 | 0.09546 |
| 0p | n20br1 | 476 | 0.08119 | 0.07761 | 0.08491 |
| 1p | n20br1 | 594 | 0.1069 | 0.1027 | 0.1112 |
| >=2p | n20br1 | 83 | 0.08242 | 0.07369 | 0.09203 |
| all | final | 1153 | 0.09278 | 0.09017 | 0.09546 |
| 0p | final | 476 | 0.08119 | 0.07761 | 0.08491 |
| 1p | final | 594 | 0.1069 | 0.1027 | 0.1112 |
| >=2p | final | 83 | 0.08242 | 0.07369 | 0.09203 |

## 7. Total signal efficiency (selected / N_signal_truth(V))
| policy | truth_class | selected | truth | efficiency | lo68 | hi68 | policy_first |
|---|---|---|---|---|---|---|---|
| any | total | 1153 | 12427 | 0.09278 | 0.09017 | 0.09546 | 0.0886 |

## 8. Truth 0p efficiency
| policy | truth_class | selected | truth | efficiency | lo68 | hi68 | policy_first |
|---|---|---|---|---|---|---|---|
| any | 0p | 476 | 5863 | 0.08119 | 0.07761 | 0.08491 | 0.07726 |

## 9. Truth 1p efficiency
| policy | truth_class | selected | truth | efficiency | lo68 | hi68 | policy_first |
|---|---|---|---|---|---|---|---|
| any | 1p | 594 | 5557 | 0.1069 | 0.1027 | 0.1112 | 0.1019 |

## 10. Truth -> reco proton migration (final selection, policy any; last column = not selected / not reconstructed / never arrived)
| index | reco 0p | reco 1p | reco >=2p | no candidate/unreco | row_total |
|---|---|---|---|---|---|
| truth 0p | 425 | 50 | 1 | 0 | 476 |
| truth 1p | 93 | 471 | 30 | 0 | 594 |
| truth >=2p | 9 | 35 | 39 | 0 | 83 |

## 11. Reco 1gamma0p yield
| channel | expected | stat_unc | exposure_pot | region |
|---|---|---|---|---|
| 1g0p | 18.57 | 0.7835 | 1e+20 | active_tpc |

## 12. Reco 1gamma1p yield
| channel | expected | stat_unc | exposure_pot | region |
|---|---|---|---|---|
| 1g1p | 19.59 | 0.799 | 1e+20 | active_tpc |

## 13. Delta0 / Delta+ diagnostics
| index | 0p | 1p | >=2p | total |
|---|---|---|---|---|
| Delta0 -> n gamma | 368 | 132 | 21 | 521 |
| Delta+ -> p gamma | 159 | 424 | 49 | 632 |

## 14. Comparison with the natural-CV rehearsal (statistical consistency only; a disagreement is a finding, not something to fix)
NOT COMPUTED: official mode: fill with scripts/run_official_signal_baseline.py rehearsal output

## 15. Any unexpected discrepancy
none detected by the automatic accounting checks (manual review still required)
