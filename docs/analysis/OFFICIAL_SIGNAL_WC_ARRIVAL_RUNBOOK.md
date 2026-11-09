# Runbook: when the official Wire-Cell merged NC-Delta signal CAFs arrive (analysis is READY; nothing has arrived)

Status 2026-11-09: **no merged-CAF path, manifest or result exists and none is invented** (`configs/samples.yaml`: `official_gen2_ncdelta` stays `status: official_flatcaf_only`, `wirecell_merged_status: pending`; the merged-CAF readers stay off until the provenance gate is open). The machinery has been exercised on the natural-CV rehearsal (exact reproduction, below) and on real BNB CV merged CAFs as a dry run of the registration tool (the gate correctly stayed closed: all events unexpected, declarations unknown).

## What Haiwang needs to provide
Exactly one of: a file list / manifest, a directory, or a SAM definition of the merged CAFs; plus a short producer declaration (`declared_same_evaluation_chain_as_fg1`, `declared_uses_dv2_max`, `declared_uses_fix2`, `declared_alternative_bdt_training`, `declared_wct_commit`, `declared_larwirecell_commit`, `declared_sbndcode_version`; `OFFICIAL_SIGNAL_PROVENANCE_GATE.md`).

## One command (workers <= 24; BLAS/OMP threads pinned to 1)
```bash
source env/setup_eaf.sh
python scripts/run_official_signal_baseline.py official --file-list <files.txt> --provenance <declaration.yaml> --workers 20
#   (or --manifest / --directory / --sam-definition; --region active_tpc is the default; --exposure-pot P adds the expected-yield section)
```
Steps it performs, each also callable alone:

1. `scripts/register_official_ncdelta_wc.py` - read-only inspection of every file (trees, alignment, `wc.valid`, schema, `Trun` provenance, truth/matching trees, baseline branches); event-key reconciliation against the 13,773-event truth census (expected / represented / `wc.valid` / missing / duplicates / unexpected / unit mismatch); evaluates the provenance gate (`configs/official_signal_provenance_gate.yaml`); writes `manifests/official_gen2_ncdelta_wc.tsv.gz` and `tables/official_signal/arrival_registration.json`. **Stops (exit 2) if the gate is closed.**
2. `scripts/build_official_signal_analysis_table.py` - the same derived-table code as the BNB CV (`build_analysis_table.py --manifest ...`, offline BDT scoring from the original XMLs: scoring, not training), then the truth join per region -> `$SP_DATA/analysis_tables/official_gen2_ncdelta/` and `$SP_DATA/official_signal_baseline/` (events never found in the merged CAFs are kept as `signal_missing_*`: they stay in the denominator).
3. Exact accounting (`signal_pipeline.validate_accounting`): rows = truth denominator, every event in exactly one first-failure reason (incl. `missing_from_merged_caf`), cumulative cutflow non-increasing, any >= first.
4. The report (`tables/official_signal/official_<region>/` and a filled `ARRIVAL_REPORT.md` from `OFFICIAL_NCDELTA_WC_ARRIVAL_REPORT_TEMPLATE.md`): truth denominator, `wc.valid`, candidates, BDT evaluable, each frozen cut, final any/first, total / 0p / 1p efficiency with exact binomial intervals, truth -> reco migration, reco 1γ0p / 1γ1p / ≥2p, Δ0 / Δ+ diagnostics, and (with `--exposure-pot`) the expected yield through the full truth -> reco migration (`SIGNAL_YIELD_AND_PREDICTION_PLUMBING.md`).

Prerequisite already done: `python scripts/build_official_signal_master.py` (truth master + denominators, `OFFICIAL_SIGNAL_MASTER_TABLE.md`).

## After the report
* Compare with the natural-CV rehearsal (`tables/official_signal/rehearsal_natural_bnb_cv/`): statistical consistency only; a disagreement is a finding, not something to fix. The rehearsal reproduces denominator 117 -> final `any` 13 -> `first` 12 and every Phase-3 table exactly (`python scripts/run_official_signal_baseline.py rehearsal`).
* Only then consider the comparison builds (DV2, Fix2) as controlled studies. Nothing is tuned here: no cut, threshold, FV or BDT is changed by this workflow.

## Frozen conventions (unchanged)
`wc.valid == 1` required; candidate policy `any` (comparison `first`); proton threshold 35 MeV; truth region = provisional active-TPC box (a parameter in `configs/signal_regions.yaml`, no FV); truth is evaluation only and never chooses a candidate or an event; generated throws are never the efficiency denominator.
