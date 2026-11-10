# Official NC Delta -> N gamma Wire-Cell sample: arrival report  (template; filled automatically by `scripts/run_official_signal_baseline.py`)

Sample label: official_gen2_ncdelta    Truth region V: filter_box    Policy comparison: any (analysis) vs first    Code commit: 56043c52b80c7b6af303b1295a7dab03aa4595b5
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
| 13772 | 13772 | 0 | 1 |

## 5. Candidate efficiency
| group | N | fraction | lo68 | hi68 |
|---|---|---|---|---|
| all | 11938 | 0.8668 | 0.8638 | 0.8697 |
| 0p | 5487 | 0.844 | 0.8394 | 0.8485 |
| 1p | 5449 | 0.8846 | 0.8804 | 0.8887 |
| >=2p | 1002 | 0.9011 | 0.8913 | 0.9101 |

## 6. Frozen cutflow (all truth events of V in the denominator, by truth class)
| group | stage | N | fraction | lo68 | hi68 |
|---|---|---|---|---|---|
| all | truth_denominator | 13773 | 1 | 0.9999 | 1 |
| 0p | truth_denominator | 6501 | 1 | 0.9997 | 1 |
| 1p | truth_denominator | 6160 | 1 | 0.9997 | 1 |
| >=2p | truth_denominator | 1112 | 1 | 0.9983 | 1 |
| all | wc_valid | 13772 | 0.9999 | 0.9998 | 1 |
| 0p | wc_valid | 6501 | 1 | 0.9997 | 1 |
| 1p | wc_valid | 6159 | 0.9998 | 0.9995 | 1 |
| >=2p | wc_valid | 1112 | 1 | 0.9983 | 1 |
| all | candidate | 11938 | 0.8668 | 0.8638 | 0.8697 |
| 0p | candidate | 5487 | 0.844 | 0.8394 | 0.8485 |
| 1p | candidate | 5449 | 0.8846 | 0.8804 | 0.8887 |
| >=2p | candidate | 1002 | 0.9011 | 0.8913 | 0.9101 |
| all | n20mev | 8452 | 0.6137 | 0.6095 | 0.6178 |
| 0p | n20mev | 4129 | 0.6351 | 0.6291 | 0.6412 |
| 1p | n20mev | 3645 | 0.5917 | 0.5854 | 0.5981 |
| >=2p | n20mev | 678 | 0.6097 | 0.5945 | 0.6247 |
| all | bdt_evaluable | 8400 | 0.6099 | 0.6057 | 0.6141 |
| 0p | bdt_evaluable | 4105 | 0.6314 | 0.6254 | 0.6375 |
| 1p | bdt_evaluable | 3622 | 0.588 | 0.5816 | 0.5943 |
| >=2p | bdt_evaluable | 673 | 0.6052 | 0.59 | 0.6202 |
| all | numu | 5225 | 0.3794 | 0.3752 | 0.3835 |
| 0p | numu | 2547 | 0.3918 | 0.3857 | 0.3979 |
| 1p | numu | 2274 | 0.3692 | 0.3629 | 0.3754 |
| >=2p | numu | 404 | 0.3633 | 0.3486 | 0.3783 |
| all | other | 2827 | 0.2053 | 0.2018 | 0.2088 |
| 0p | other | 1184 | 0.1821 | 0.1773 | 0.187 |
| 1p | other | 1390 | 0.2256 | 0.2203 | 0.2311 |
| >=2p | other | 253 | 0.2275 | 0.2147 | 0.2408 |
| all | ncpi0 | 1336 | 0.097 | 0.09447 | 0.09959 |
| 0p | ncpi0 | 586 | 0.09014 | 0.08657 | 0.09384 |
| 1p | ncpi0 | 656 | 0.1065 | 0.1025 | 0.1106 |
| >=2p | ncpi0 | 94 | 0.08453 | 0.07613 | 0.09372 |
| all | nue | 1336 | 0.097 | 0.09447 | 0.09959 |
| 0p | nue | 586 | 0.09014 | 0.08657 | 0.09384 |
| 1p | nue | 656 | 0.1065 | 0.1025 | 0.1106 |
| >=2p | nue | 94 | 0.08453 | 0.07613 | 0.09372 |
| all | n20br1 | 1172 | 0.08509 | 0.08271 | 0.08754 |
| 0p | n20br1 | 484 | 0.07445 | 0.07118 | 0.07785 |
| 1p | n20br1 | 603 | 0.09789 | 0.09409 | 0.1018 |
| >=2p | n20br1 | 85 | 0.07644 | 0.06842 | 0.08527 |
| all | final | 1172 | 0.08509 | 0.08271 | 0.08754 |
| 0p | final | 484 | 0.07445 | 0.07118 | 0.07785 |
| 1p | final | 603 | 0.09789 | 0.09409 | 0.1018 |
| >=2p | final | 85 | 0.07644 | 0.06842 | 0.08527 |

## 7. Total signal efficiency (selected / N_signal_truth(V))
| policy | truth_class | selected | truth | efficiency | lo68 | hi68 | policy_first |
|---|---|---|---|---|---|---|---|
| any | total | 1172 | 13773 | 0.08509 | 0.08271 | 0.08754 | 0.08132 |

## 8. Truth 0p efficiency
| policy | truth_class | selected | truth | efficiency | lo68 | hi68 | policy_first |
|---|---|---|---|---|---|---|---|
| any | 0p | 484 | 6501 | 0.07445 | 0.07118 | 0.07785 | 0.07091 |

## 9. Truth 1p efficiency
| policy | truth_class | selected | truth | efficiency | lo68 | hi68 | policy_first |
|---|---|---|---|---|---|---|---|
| any | 1p | 603 | 6160 | 0.09789 | 0.09409 | 0.1018 | 0.09334 |

## 10. Truth -> reco proton migration (final selection, policy any; last column = not selected / not reconstructed / never arrived)
| index | reco 0p | reco 1p | reco >=2p | no candidate/unreco | row_total |
|---|---|---|---|---|---|
| truth 0p | 433 | 50 | 1 | 0 | 484 |
| truth 1p | 98 | 475 | 30 | 0 | 603 |
| truth >=2p | 10 | 36 | 39 | 0 | 85 |

## 11. Reco 1gamma0p yield
| channel | expected | stat_unc | exposure_pot | region |
|---|---|---|---|---|
| 1g0p | 19.06 | 0.796 | 1e+20 | filter_box |

## 12. Reco 1gamma1p yield
| channel | expected | stat_unc | exposure_pot | region |
|---|---|---|---|---|
| 1g1p | 19.76 | 0.8055 | 1e+20 | filter_box |

## 13. Delta0 / Delta+ diagnostics
| index | 0p | 1p | >=2p | total |
|---|---|---|---|---|
| Delta0 -> n gamma | 377 | 134 | 21 | 532 |
| Delta+ -> p gamma | 164 | 427 | 49 | 640 |

## 14. Comparison with the natural-CV rehearsal (statistical consistency only; a disagreement is a finding, not something to fix)
NOT COMPUTED: official mode: fill with scripts/run_official_signal_baseline.py rehearsal output

## 15. Any unexpected discrepancy
none detected by the automatic accounting checks (manual review still required)
