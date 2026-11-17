# round2: retraining machinery for the single-photon `ncpi0`, `other` and `numu` BDTs

Prepared 2026-11-17 on Aurora. The goal is to retrain the single-photon `ncpi0` and `other` BDTs for Haiwang's Round-2
SBND production, by the same validated route Xuyang Ning uses for the νe BDT, without crossing the training /
evaluation boundary:

- **Aurora samples** (Haiwang's aurora-r* merged CAFs of Avinay's gen2 MC) are **training / development**.
- **Official fg1 / FermiGrid samples** are untouched **evaluation**, on EAF.

**Status (2026-11-17, after the thesis audit and the EAF XML fingerprint):**
- **ncpi0: READY FOR DEVELOPMENT TRAINING.** The training classes come from E. H. Yandel's thesis
  (`docs/YANDEL_THESIS_SP_BDT_TRAINING_SOURCE_AUDIT.md`), the frozen XML is the thesis model (exact fingerprint), and a
  dry-run class census passed. Development training waits for Avinay's `kine_pio_flag` policy.
- **other: READY ONLY AFTER ADDITIONAL TRAINING SAMPLE.** Exact fingerprint, but it needs an in-time-cosmic sample.
- **numu: READY FOR DEVELOPMENT TRAINING,** proposed to join Round 2 (`docs/SP_NUMU_TRAINING_SOURCE_AUDIT.md`). Final
  training needs Xuyang's frozen νμ chain.
- **nue: decision blocked.** The thesis Fig. E.4 does not fingerprint-match the frozen XML.

See `docs/SP_BDT_ROUND2_FREEZE_ORDER.md` for the dependency graph, freeze order and per-model decisions.

No model has been trained, and none will be until Avinay has reviewed the definitions. `sp_retrain.labels` refuses
final labels, and refuses any label for a spec that is not ready.

## Architecture

```
Aurora merged CAF (recTree + recTreeWireCell)
  -> sp_retrain/build_tables.py   cands / truth / files parquet: every T_tagger + T_kine per-candidate scalar,
                                  T_match level-2 partner, truth ingredients (pi0, photons), hold-out flags
  -> sp_retrain/sp_truth.py       single-photon signal / background categories per truth neutrino (thesis sec. 5.1.2)
  -> specs/*_training_spec_*.yaml frozen spec: inputs, pool, label, samples, split, weights, XGBoost
  -> sp_retrain/labels.py         classes per candidate, gated by the spec status
  -> sp_retrain/split.py          event-safe split by (sample, run, subrun): odd subrun = test,
                                  even = train / validation (seeded)
  -> XGBoost 3.4.1 (binary:logitraw, base_score 0.5)        not run: waits for Avinay's review
  -> validation (Aurora test fold only)
  -> export to TMVA XML (BoostType=Grad) + equivalence test  specified in docs/SP_BDT_DEPLOYMENT_EXPORT_AUDIT.md
  -> handoff to Haiwang           docs/NCPI0_OTHER_ROUND2_PRODUCTION_HANDOFF_REQUIREMENTS.md
```

## Layout

| path | what |
|---|---|
| `config/features/single_photon_<x>_inputs_v0.json` | ordered inputs of the four frozen single-photon BDTs, from the XML `<Variables>`; branch, type, producer, notes. Made by `tools/make_feature_configs.py` |
| `specs/single_photon_{ncpi0,other}_training_spec_v0.2.yaml`, `specs/single_photon_numu_training_spec_v0.1.yaml` | current training specs: ncpi0 (v0.2.1) and numu (v0.1.0) `READY_FOR_DEVELOPMENT_TRAINING`; other (v0.2.1) `READY_ONLY_AFTER_ADDITIONAL_TRAINING_SAMPLE`. The ncpi0 / other v0.1 files (BLOCKED) are kept for the record |
| `sp_retrain/` | `build_tables`, `features`, `firewall`, `split`, `sp_truth` (single-photon truth categories), `labels` (classes + status gate), `tmva_grad` (TMVA Grad scorer), `readiness`, `manifest` |
| `tools/` | `make_feature_configs.py`, `check_scorer_vs_stored_nue.py`, `validate_smoke_tables.py`, `render_readiness_tables.py`, `sp_class_census.py` (dry-run class census for ncpi0 / numu, no training) |
| `tests/test_sp_retrain.py` | 23 unit tests: feature order, dependencies, firewall, split safety, TMVA routing and score conventions, builder truth ingredients, single-photon truth categories, ncpi0 and numu classes, status gate |
| `manifests/aurora_r2_v0/` | input manifests of the three aurora-r2 lists (path, size, mtime; list sha256) |
| `validation/` | scorer bit-check vs the toolkit (423/423), smoke build summaries, builder-vs-spec_v1 comparison, environment freeze |
| `docs/` | audits, readiness, refresh request, handoff contract, deployment/export, EAF evaluation handoff |

Large outputs (tables, models) are kept outside git under `$SP_WORK` (2026-11-17:
`/lus/flare/projects/neutrinoGPU/abhat/sbnd/sp-bdt-round2-work-20261117`).

## Environment (Aurora)

```bash
module load frameworks/2026.1.0                   # python 3.12, numpy, pandas, pyarrow, pyyaml
SP_WORK=/lus/flare/projects/neutrinoGPU/abhat/sbnd/sp-bdt-round2-work-20261117
PY=$SP_WORK/env/bin/python                        # venv on top of frameworks: + uproot 5.7.7, xgboost 3.4.1, pytest
```

`validation/env_pip_freeze_20261117.txt` records every package version.

## Commands that were run (2026-11-17)

```bash
cd round2
L=/lus/flare/projects/neutrinoGPU/yuhw/production-prep/dlspace/lists
python3 tools/make_feature_configs.py --schema /lus/flare/projects/neutrinoGPU/yuhw/sbnd-wirecell-production/aurora/schema/recTreeWireCell-dlvtx-space.schema.json
$PY -m pytest -q -p no:cacheprovider tests                                   # 23 passed
$PY -I tools/check_scorer_vs_stored_nue.py --xml /lus/flare/projects/neutrinoGPU/yuhw/wire-cell-data/uboone/weights/XGB_nue_seed2_0923.xml \
    --out $SP_WORK/scorer_checks/<name>.json <merged CAFs>                   # 232/232 and 191/191 bit-identical
$PY -m sp_retrain.build_tables aurora-r2-ncdr $SP_WORK/smoke_tables --list $L/ncdr-merged-cafs.txt --slice 0:60 --nproc 8 \
    --allowed-input-root /lus/flare/projects/neutrinoGPU/yuhw/production-prep/dlspace \
    --allowed-output-root /lus/flare/projects/neutrinoGPU/abhat/sbnd --tag smoke              # likewise bnb 0:15, nuecc 0:20
$PY -I tools/validate_smoke_tables.py --tables $SP_WORK/smoke_tables --tag smoke \
    --reference-dir /lus/flare/projects/neutrinoGPU/xning/BDT/working/step4_tables/output/merged --out <json>   # read-only reference
$PY -I sp_retrain/readiness.py --tables <dir> --out-dir <dir> --samples aurora-r2-ncdr aurora-r2-bnb aurora-r2-nuecc
$PY -I sp_retrain/manifest.py aurora-r2-ncdr $L/ncdr-merged-cafs.txt $SP_WORK/manifests \
    --allowed-input-root /lus/flare/projects/neutrinoGPU/yuhw/production-prep/dlspace
$PY -I tools/render_readiness_tables.py
# dry-run class censuses (thesis audit sec. 9.1, numu audit sec. 7); same builder options, --tag census
$PY -m sp_retrain.build_tables aurora-r2-ncdr $SP_WORK/census_tables --list $L/ncdr-merged-cafs.txt --slice 0:3000 --nproc 16 ...
$PY -m sp_retrain.build_tables aurora-r2-bnb $SP_WORK/census_tables --list $L/bnb-merged-cafs.txt --slice 0:1200 --nproc 16 ...
for m in ncpi0:0.2 numu:0.1; do $PY -I tools/sp_class_census.py --tables $SP_WORK/census_tables --tag census \
    --samples aurora-r2-ncdr aurora-r2-bnb --spec specs/single_photon_${m%:*}_training_spec_v${m#*:}.yaml \
    --out $SP_WORK/census_tables/census_${m%:*}.json; done
```

## Documents

- `docs/SP_BDT_ROUND2_FREEZE_ORDER.md`: the dependency graph, the freeze order, the retrain decision for each of the
  four SP models, the `kine_pio_flag` decision support, and development readiness.
- `docs/YANDEL_THESIS_SP_BDT_TRAINING_SOURCE_AUDIT.md`: the ncpi0 / other training definitions recovered from the
  thesis, the XML cross-check and Appendix E fingerprint, Aurora data readiness, the ncpi0 dry-run census, and the gate.
- `docs/SP_NUMU_TRAINING_SOURCE_AUDIT.md`: the same for SP numu.
- `docs/SP_BDT_DEPENDENCY_AND_TARGET_AUDIT.md`: dependency graph, ncpi0 / other target verdicts, the baseline_v0
  score-convention erratum, and development vs final freeze.
- `docs/NCPI0_OTHER_CAF_INPUT_READINESS.md` with `docs/tables/READINESS_PER_INPUT.md`.
- `docs/SP_BDT_DEPLOYMENT_EXPORT_AUDIT.md`: loader, format, exporter and the equivalence test.
- `docs/HAIWANG_AURORA_TRAINING_REFRESH_REQUEST.md`.
- `docs/NCPI0_OTHER_ROUND2_PRODUCTION_HANDOFF_REQUIREMENTS.md`.
- `docs/EAF_ROUND2_EVALUATION_HANDOFF.md`.
- `ATTRIBUTION_AND_PROVENANCE.md`.
