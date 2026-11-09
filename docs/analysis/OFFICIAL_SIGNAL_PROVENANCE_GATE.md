# Provenance acceptance gate for the official NC Delta Wire-Cell sample

Machine-readable: `configs/official_signal_provenance_gate.yaml`; evaluated by `signal_arrival.evaluate_gate` inside `scripts/register_official_ncdelta_wc.py` (exit code 2 if closed). Built-in rule: **the gate is OPEN only if every REQUIRED check passes; an UNKNOWN fact is not a pass.** `build_official_signal_analysis_table.py` refuses to run with a closed gate and there is no override. Exact byte-identical software versions are NOT required (fg1 and later production legitimately differ); the gate asks for the *same evaluation chain* and records the versions.

fg1 reference (Haiwang's `fg1/README.md`): chain r8; WCT `HaiwangYu/wire-cell-toolkit` `sbnd-wc-flatcaf` `4b6853d4`; larwirecell `ad5d942`; sbndcode `v10_14_02_03`; SCN vertex weights `uboone/scn_vtx/t48k-m16-l5-lr5d-res0.5-CP24.pth`; schema 2,401 branches / 20 trees, md5 `d4396a3490ea5aec4b02f0c34fa9db33`; in-file `Trun.wct_version` `sbnd-dlvtx-35-pre-master-merge-2026-09-02-424-g78f81c64`.

| id | level | fact source | rule |
|---|---|---|---|
| rec_trees_present, entries_aligned, ids_aligned, wc_valid_present | REQUIRED | measured, every file | both trees; equal entry counts; identical run/subrun/event; `wc.valid` present |
| truth_trees_present, genie_record_present | REQUIRED | measured | `T_match T_overlap T_truth_nu T_truth_pf T_truth_track`; `GenieEvtRecTree` |
| baseline_branches_present | REQUIRED | measured | every branch the frozen chain and the evaluation read (schema compatibility, not byte equality) |
| unreadable_files | REQUIRED | measured | 0 files fail |
| event_keys_accounted, no_duplicate_events, no_unexpected_events, no_unit_mismatch, wc_valid_accounted | REQUIRED | reconciliation vs the 13,773-event official truth set | each expected and incoming event classified; none duplicated or foreign; from the unit the truth says; `wc.valid` explicit |
| no_missing_events | EXPECTED | reconciliation | missing events are inefficiency (kept in the denominator) but must be explained |
| same_chain_as_fg1 | REQUIRED | producer declaration | same imaging/clustering/PR/tagger chain |
| scn_vertex_model | REQUIRED | measured (`Trun.dl_weights`) | equals the fg1 SCN model string |
| no_dv2_max, no_fix2, no_alternative_bdt | REQUIRED | producer declaration | `false` each |
| no_hidden_selection_change | REQUIRED | sha256 of `configs/baseline_selection.yaml` | equals the frozen value (a test pins it) |
| schema_md5_matches_fg1, single_schema, single_dl_weights | EXPECTED | measured | a newer schema is allowed if the baseline branches are present |
| wct_commit_declared, larwirecell_commit_declared, sbndcode_declared | EXPECTED | producer declaration | recorded |
| wct_version_strings, bdt_weights_dir_strings, n_wc_branches | INFORMATIONAL | measured | recorded only |

Producer declaration (YAML passed with `--provenance`), the keys the gate reads: `declared_same_evaluation_chain_as_fg1`, `declared_uses_dv2_max`, `declared_uses_fix2`, `declared_alternative_bdt_training`, `declared_wct_commit`, `declared_larwirecell_commit`, `declared_sbndcode_version`. If Haiwang cannot state one of the REQUIRED ones, the gate stays closed and the sample is not used for the baseline.
