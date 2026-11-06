# Runbook: when the official Wire-Cell merged NC-Delta signal CAFs arrive

Status: **not ready to run yet; nothing has arrived.** No sample path, manifest or result for the official Wire-Cell merged sample exists in this repository and none must be invented (`configs/samples.yaml`: `official_gen2_ncdelta` has `status: official_flatcaf_only`, `wirecell_merged_status: pending`; the merged-CAF readers stay disabled until the manifest is registered).

The signal characterisation is sample-agnostic by construction (`src/sbnd_single_photon/exclusive_signal.py`, `scripts/exclusive_signal_characterize.py`): it consumes (i) a signal-truth table and (ii) the derived analysis table of the same sample. Rehearsed on the natural BNB signal (`EXCLUSIVE_SIGNAL_BASELINE_REHEARSAL.md`). The physics code does not change; only inputs do.

## Steps (in order; stop and ask if a check fails)

1. **Get from Haiwang:** the merged-CAF location/manifest, the Wire-Cell commit and SCN-vertexer provenance, and confirmation that `recTree` + `recTreeWireCell` (incl. `T_tagger`, `T_kine`, `T_overlap`, `T_truth_track`, `T_truth_nu`) and `GenieEvtRecTree` are present, and the full list of units (to account for the 728 reco1 units without a flatCAF).
2. **Register the manifest** (do not create paths in advance): add `manifest:` to `official_gen2_ncdelta` in `configs/samples.yaml`, set `wirecell_merged_status: available` and `status: available` (this is the only switch that enables the merged-CAF readers); `tests/test_samples.py` must be updated in the same commit; `python scripts/make_manifests.py`.
3. **Schema check:** `python scripts/smoke_test.py official_gen2_ncdelta` (branch presence, `wc.valid`, `schema_md5` against the BNB CV schema).
4. **Build the derived table** (same code as the BNB CV; offline BDT scoring from the original MicroBooNE XMLs; scoring, not training):
   `python scripts/build_analysis_table.py official_gen2_ncdelta --workers 28` then `--merge`, then `python scripts/validate_analysis_table.py official_gen2_ncdelta --elementwise` (the exact checks that need sample-specific expected numbers must be supplied from the new sample, not from the BNB CV).
5. **Signal truth table:** `signal_truth_from_official_events(pd.read_parquet("$SP_DATA/official_gen2_ncdelta_truth/events.parquet"))` (already built from all 15,777 flatCAFs with the exact GENIE-record ancestry) then `attach_event_key(sig, events)` to map (run, subrun, evt) onto the merged table's `(file_index, ev)`; **report `n_missing`**: events absent from the merged table are *inefficiency* (they stay in the truth denominator), not dropped events. Write the result as Parquet under `$SP_DATA/exclusive_signal_inputs/official_gen2_ncdelta/signal_truth.parquet` (columns: file_index, ev, x, y, z, truth_cat, delta_pdg, in_region, nucleon_pdg, photon_mev, E, n_p35).
6. **Run the same characterisation:**
   `python scripts/exclusive_signal_characterize.py --label official_gen2_ncdelta --tables $SP_DATA/analysis_tables/official_gen2_ncdelta --signal-truth <parquet from step 5>`
   `python scripts/exclusive_signal_mechanisms.py --label official_gen2_ncdelta --sample official_gen2_ncdelta`
   `python scripts/exclusive_signal_vs_background.py --label official_gen2_ncdelta --signal-tables $SP_DATA/analysis_tables/official_gen2_ncdelta --tables $SP_DATA/analysis_tables/bnb_cv` (signal candidates from the official table, background = the BNB CV table; no code edit).
7. **Denominator and exposure:** `N_signal_truth(V; S)` per event from the truth table restricted to the units S that have a merged CAF; POT(S) and generated throws from SAM `mc.pot` / `mc.generated_event_count` of the same units (`SIGNAL_TRUTH_AND_DENOMINATOR.md`). Never use the CAF `TotalGenEvents` (125 per file).
8. **Cross-check against the rehearsal:** the efficiencies and migration matrices must be statistically consistent with the natural-CV rehearsal (the natural events are an unbiased subset of the same physics; agreement of the TPC-box rate per POT was already shown). A disagreement is a finding to report, not to fix.
9. **Then, and only then,** consider the comparison builds (DV2, Fix2) as controlled studies. Nothing is tuned in this runbook.

## Frozen conventions (unchanged)
`wc.valid == 1` required; candidate policy `any` (comparison `first`); proton threshold 35 MeV; truth region = provisional active-TPC box (a parameter, no FV); truth is evaluation only and never chooses a candidate or an event.
