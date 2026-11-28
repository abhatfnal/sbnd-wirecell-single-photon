# round2: retraining machinery for the single-photon `ncpi0`, `other` and `numu` BDTs

Prepared 2026-11-17 on Aurora. The goal is to retrain the single-photon `ncpi0` and `other` BDTs for Haiwang's Round-2
SBND production, by the same validated route Xuyang Ning uses for the νe BDT, without crossing the training /
evaluation boundary:

- **Aurora samples** (Haiwang's aurora-r* merged CAFs of Avinay's gen2 MC) are **training / development**.
- **Official fg1 / FermiGrid samples** are untouched **evaluation**, on EAF.

**Status (2026-11-17, after the thesis audit and the EAF XML fingerprint):**
- **ncpi0: READY FOR DEVELOPMENT TRAINING.** The training classes come from E. H. Yandel's thesis
  (`docs/YANDEL_THESIS_SP_BDT_TRAINING_SOURCE_AUDIT.md`), the frozen XML is the thesis model (exact fingerprint), and a
  dry-run class census passed. `kine_pio_flag` Policy B.
- **other: not trained.** Exact fingerprint. The EXT sample exists: the fg1 beam-off training half, 481 usable rows,
  statistically limited. It needs Avinay's approved exception and reprocessing in the refresh
  (`docs/ROUND2_COLLABORATOR_QUESTION_CLOSURE_AUDIT.md`).
- **numu: READY FOR DEVELOPMENT TRAINING,** proposed to join Round 2 (`docs/SP_NUMU_TRAINING_SOURCE_AUDIT.md`). Final
  training needs Xuyang's frozen νμ chain.
- **nue: decision blocked** by the unknown vertex-domain shift only. Thesis Fig. E.4 = the first 200 trees of the
  frozen XML, exactly.

See `docs/SP_BDT_ROUND2_FREEZE_ORDER.md` for the dependency graph, freeze order and per-model decisions.

**Round-2 production is running (2026-11-17 evening).** Haiwang's **WCLocal2026Nov16** uses WCT 0.38.0 with Snehadri's
DV2-MAX `aurora_space` DL vertex.
- Aurora (training): NC Δ, BNB and νe CC are complete (νe CC: 2026-11-18, 61,238 / 61,252 units OK).
- FermiGrid (evaluation): official CV, νe CC, the full beam-off including its odd-run training half, and beam-on.
- Tracker: `docs/HAIWANG_ROUND2_ACTIVE_PRODUCTION_TRACKER.md`. Registry: `config/samples/round2_training_samples.yaml`
  (still `active_training_domain: aurora-r2`).

**WCL1116 development campaign (2026-11-17 night).** Branch `round2/sp-bdt-wcl1116-development-20261117`; plan, results
and policy in `docs/SP_BDT_WCL1116_DEVELOPMENT_{PLAN,RESULTS}.md` and
`docs/AURORA_UMBRELLA_MODEL_TRAINING_AND_EVALUATION_POLICY.md`.
- Tables of NC Δ and BNB from **both** vertex trees (split-move and snap) on compute nodes.
- SP numu and SP ncpi0 developed per mode (`DEV_DO_NOT_DEPLOY`). Development-holdout AUC: numu 0.976 / 0.974, ncpi0
  0.899 / 0.897, against legacy 0.958 / 0.954 and 0.848 / 0.847.
- SP other is blocked only on staging the beam-off half.
- SP nue shift LARGE: retraining should be developed.
- Exporter verified in C++ (TMVA::Reader = toolkit TmvaGradForest, bit for bit).

**Remaining SP models (2026-11-18 / 19): WCL1116 is now a complete four-model development domain.** Branch
`round2/sp-other-nue-wcl1116-development-20261117`. Four-model view: `docs/SP_BDT_WCL1116_FOUR_MODEL_DEVELOPMENT_SUMMARY.md`.
- **SP nue** (`docs/SP_NUE_WCL1116_DEVELOPMENT_REPORT.md`):
  - developed per mode on the complete WCL1116 νe CC;
  - holdout AUC 0.959 / 0.952 against legacy 0.918 / 0.914;
  - pre-registered verdict RETRAINING CLEARLY BENEFICIAL.
- **SP other** (`docs/SP_OTHER_WCL1116_DEVELOPMENT_REPORT.md`):
  - the beam-off training half was pushed from Avinay's gpvm (`tools/beamoff_staging/`) and verified 558 / 558
    (`tools/verify_staged_beamoff.py`);
  - its `HEAD-0.38.0` stamp is the FermiGrid build of the same toolkit c935e30d (`docs/WCL1116_TOOLKIT_PROVENANCE_NOTE.md`);
  - 509 / 508 EXT rows;
  - holdout AUC 0.915 / 0.912 against legacy 0.840 / 0.836;
  - pre-registered verdict RETRAINING CLEARLY BENEFICIAL.
- WCL1116 is **not** the final training domain. SP other MUST be retrained after the measured non-box / effective
  boundary production; SP numu / ncpi0 / nue also wait for the final reconstruction.

**Full development on WCL1116 (2026-11-20).** Branch `round2/sp-bdt-wcl1116-full-development-20261120`; summary
`docs/SP_BDT_FULL_DEVELOPMENT_SUMMARY.md`, pre-registered plan `docs/SP_BDT_WCL1116_FULL_DEVELOPMENT_PLAN.md`.
- A nested FIT / NESTED VALIDATION split of the training side (`sp_retrain/devstudy.py`); the outer holdout is
  unchanged.
- SP nue weighting: unweighted is kept.
- SP ncpi0 statistics: current sample adequate; the νe CC NC π⁰ rows are not source-compatible.
- SP numu / SP other upstream and boundary ablations: diagnostics only.
- Validation-only operating points and the joint four-cut evaluator (`tools/sp_operating_points.py`): on nested
  validation, 44.0 % vs 27.1 % NC Δ efficiency at the same BNB background, versus the inherited XMLs.
- The final-domain rerun template `config/campaigns/round2_final_reco_candidate.yaml` with
  `tools/final_domain_campaign.py`, which refuses until the provenance is supplied
  (`docs/SP_BDT_FINAL_DOMAIN_RERUN_CONTRACT.md`).
- Nothing is frozen.

**Upstream-release integration (2026-11-28; branch `round2/sp-bdt-wcl1116-upstream-r4-integration-20261128`).**
Xuyang's recommended upstream models `numu_round3af` and `nue_round4_ruleA_v2` (main), from
`Ningclover/sbnd-wirecell-bdt` @ `0f13988d`:
- re-scored offline on every candidate of the four development samples, both trees: 61/61 model checksums; extraction
  identical to Xuyang's builder; shipped final models closed bit for bit; official scorers and chain emulation agree;
- validated in-chain on copies of production units;
- downstream effect: SP numu, other and ncpi0 must be retrained on the new upstream values; after retraining, the joint
  selection moves by ≤ ~2 points;
- report: `docs/SP_BDT_UPSTREAM_R4_INTEGRATION_AUDIT.md`. Domain A (stored WCL1116) remains the reference. Nothing is
  frozen.

**Follow-up (2026-11-28, approved by Avinay).**
- Domain D (`numu_round3af` and `nue_round4_ruleA_v2` main) is the current WCL1116 **development** domain. Domain A and all its
  models, thresholds and results are immutable.
- The patched toolkit stamp `numu-sim-dqdx-scale-0.38.0-1-gccb19cf` is approved for development validation only
  (`sp_retrain/provenance.py`, `validation/upstream_r4/patched_toolkit_dev_approval.json`). The final campaign refuses it.
- **Common Aurora/EAF scoring bundle**: `upstream_chain_bundle/` (`wc_upstream_chain` 1.0.0; numpy and pandas only). It is
  toolkit-equivalent, and bit-identical to the in-chain test and to `sp_retrain/upstream_chain.py` on every candidate.
- Development fixture and transfer procedure; training-membership manifest; joint-selection statistics; final-domain routes
  R1 / R2 with simulation-only correction evidence (`tools/verify_sim_dqdx_logs.py`).
- Report: `docs/SP_BDT_UPSTREAM_R4_FOLLOWUP.md`. EAF handoff: `docs/EAF_HANDOFF_UPSTREAM_CHAIN_BUNDLE.md`.

**Ownership.** Avinay owns SP numu / SP other / SP ncpi0 and the SP nue decision. Xuyang and Matteo own the upstream νμ
(`numu_score`) and νe (`nue_score`) taggers, which are **not** SP numu / SP nue.

**Final-model status.**
- SP numu: WAITS FOR REFRESH + FROZEN UPSTREAM NUMU.
- SP other: WAITS FOR FINAL RECONSTRUCTION (boundary change: MUST retrain) + FROZEN UPSTREAM NUMU + BEAM-OFF IN THAT
  RECONSTRUCTION. Development verdict CLEARLY BENEFICIAL.
- SP ncpi0: WAITS FOR REFRESH (Policy B) + the collaboration's choice of νe release (its 15 upstream inputs change under
  `nue_round4_ruleA_v2`).
- SP nue: RETRAIN RECOMMENDED (development verdict CLEARLY BENEFICIAL); final training waits for the final reconstruction
  domain.

**Development training (2026-11-17):** one SP numu and one SP ncpi0 model were trained on aurora-r2
(`docs/SP_BDT_DEVELOPMENT_TRAINING_SUMMARY.md`).
- They are labelled `ROUND1_DOMAIN_DEVELOPMENT_DO_NOT_DEPLOY`, and neither is deployable.
- Test AUC: 0.959 (numu) and 0.817 (ncpi0). On the same test rows, the verified legacy MicroBooNE XMLs reach 0.926
  and 0.754 (AURORA DEVELOPMENT, NOT OFFICIAL; `manifests/dev_round1domain_v1/legacy_controls.json`).
- No final model exists. `sp_retrain.labels` refuses final labels, and refuses any label for a spec that is not ready.

## Architecture

```
Aurora merged CAF (recTree + recTreeWireCell)
  -> sp_retrain/build_tables.py   cands / truth / files parquet: every T_tagger + T_kine per-candidate scalar,
                                  T_match level-2 partner, truth ingredients (pi0, photons), hold-out flags
  -> sp_retrain/sp_truth.py       single-photon signal / background categories per truth neutrino (thesis sec. 5.1.2)
  -> specs/*_training_spec_*.yaml frozen spec: inputs, pool, label, samples, split, weights, XGBoost
  -> sp_retrain/labels.py         classes per candidate, gated by the spec status
  -> sp_retrain/split.py          event-safe split by (sample, run, subrun): odd subrun = test; development
                                  campaign: even = train (subrun_parity_v1)
  -> sp_retrain/devtrain.py       dataset (XML-ordered float32, Policy B, non-finite rows excluded), parameters
  -> tools/train_dev_model.py     XGBoost 3.4.1, binary:logitraw, base_score 0, fixed thesis parameters; repeat check
  -> validation (Aurora test fold only)
  -> sp_retrain/export_tmva.py    XGBoost JSON -> TMVA Grad XML (inherited xgboost2TMVA layout) + sidecars
  -> tools/export_equivalence_check.py  native margin = XML forest sum = TMVA response = log10-odds; 0 flips (dev fixtures)
  -> handoff to Haiwang           docs/NCPI0_OTHER_ROUND2_PRODUCTION_HANDOFF_REQUIREMENTS.md
```

## Layout

| path | what |
|---|---|
| `config/samples/round2_training_samples.yaml` | training-sample registry: aurora-r2 (active, development) and the WCLocal2026Nov16-Aurora refresh (skeleton, placeholders for lists, upstream model hashes, the vertex-tree confirmation) |
| `config/features/single_photon_<x>_inputs_v0.json` | ordered inputs of the four frozen single-photon BDTs, from the XML `<Variables>`; branch, type, producer, notes. Made by `tools/make_feature_configs.py` |
| `specs/single_photon_{ncpi0,other}_training_spec_v0.2.yaml`, `specs/single_photon_numu_training_spec_v0.1.yaml` | current training specs: ncpi0 (v0.2.2) and numu (v0.1.0) `READY_FOR_DEVELOPMENT_TRAINING`; other (v0.2.3) `READY_ONLY_AFTER_ADDITIONAL_TRAINING_SAMPLE`. The ncpi0 / other v0.1 files (BLOCKED) are kept for the record |
| `specs/single_photon_{numu,ncpi0}_training_spec_dev_round1_domain_v1.yaml` | frozen DEVELOPMENT specs of the 2026-11-17 campaign (`deployable: false`) |
| `sp_retrain/` | `build_tables`, `features`, `firewall`, `split`, `sp_truth` (single-photon truth categories), `labels` (classes + status gate), `devtrain` (development training library), `legacy_control` (verified legacy XML bundle, legacy scoring and ROC-equivalent points), `tmva_grad` (TMVA Grad scorer), `export_tmva` (XGBoost JSON → TMVA Grad XML exporter), `readiness`, `manifest` |
| `tools/` | `make_feature_configs.py`, `check_scorer_vs_stored_nue.py`, `validate_smoke_tables.py`, `render_readiness_tables.py`, `sp_class_census.py` (dry-run class census for ncpi0 / numu), `train_dev_model.py`, `plot_dev_model.py`, `summarize_dev_models.py` (development campaign), `legacy_control_compare.py`, `plot_legacy_control.py`, `record_dev_provenance.py` (legacy controls and post-training provenance), `check_numu_score_offline.py`, `nue_prefix_test.py`, `beamoff_other_census.py` (evidence audit, no training), `refresh_smoke_check.py`, `make_refresh_list.py` (read-only smoke and census / list builder for the refreshed production), `ncpi0_negative_learning_curve.py` (diagnostic only), `export_equivalence_check.py` (exporter equivalence on the dev fixtures), `make_wcl1116_dev_specs.py`, `train_wcl1116_dev_model.py`, `wcl1116_mode_compare.py` (WCL1116 development specs, training, mode comparison with the pre-registered retraining verdict), `sp_other_census.py`, `sp_nue_census.py` (class censuses), `verify_staged_beamoff.py` + `beamoff_staging/` (beam-off training-half staging and verification), `cpp_equivalence_check.py` (C++ fixtures); upstream-release integration (2026-11-28): `verify_upstream_release.py`, `upstream_dependency_matrix.py`, `extract_upstream_inputs.py`, `merge_upstream_slices.py`, `check_upstream_extract_vs_builder.py`, `upstream_rescore.py`, `compare_upstream_official.py`, `summarize_upstream_rescoring.py`, `build_upstream_overlay.py`, `upstream_domain_study.py`, `upstream_l1_tmva_closure.py`, the in-chain test (`pick_chain_test_units.py`, `find_targeted_chain_units.py`, `chain_test_compare.sh`, `compare_chain_test.py`, `compare_chain_scores.py`, `compare_chain_sp_predictions.py`, `summarize_chain_test.py`); follow-up: `build_upstream_chain_bundle_data.py`, `check_upstream_chain_bundle.py`, `build_upstream_fixture.py`, `build_training_membership_manifest.py`, `upstream_joint_comparison.py`, `verify_sim_dqdx_logs.py` |
| `upstream_chain_bundle/` | `wc_upstream_chain`: the portable, toolkit-equivalent upstream-score reference shared with EAF (README, CONVENTIONS, tests) |
| `tests/test_sp_retrain.py`, `tests/test_export_tmva.py`, `tests/test_wcl1116_dev.py` | 100 unit tests: feature order, dependencies, firewall, split safety, TMVA routing and score conventions, builder truth ingredients, single-photon truth categories, ncpi0 and numu classes, status gate, development split / leakage / Policy B / hyperparameters / manifests / reproducibility, legacy bundle hashes / structure / score transform / forced flag / ROC-equivalent points / provenance mapping, evidence summaries, the Round-2 registry and provenance, the refresh census, the learning-curve rule, the refresh smoke, the exporter (margins, exact-threshold routing, base margin, guards, sidecars), and the WCL1116 campaign (tree selection, spec-scoped firewall exceptions and their directory boundary, the exact WCLocal2026Nov16 stamp policy, beam-off staging verifier and record, SP other census / provenance / verdict, SP nue source / census / provenance / verdict), and the full-development studies (`tests/test_wcl1116_full_dev.py`: nested split, weighting, ablation families, bookkeeping, threshold monotonicity, joint-cut order, final-domain template refusal) |
| `manifests/aurora_r2_v0/` | input manifests of the three aurora-r2 lists (path, size, mtime; list sha256) |
| `manifests/wcl1116_aurora_v0/production_provenance.json` | live snapshot of the WCLocal2026Nov16 configuration as run: toolkit, wire-cell-data, DL bundle and file hashes, config md5s, schemas, the 36 booked BDT weight hashes |
| `manifests/dev_round1domain_v1/` | development campaign: frozen inputs; one manifest per model (model, spec, feature-list, table and code sha256, package versions, counts, post-training provenance); `legacy_controls.json` (verified legacy bundle and the legacy-vs-development results) |
| `validation/` | scorer bit-check vs the toolkit (423/423), smoke build summaries, builder-vs-spec_v1 comparison, environment freeze; development summary and the ncpi0 non-finite row list |
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
$PY -m pytest -q -p no:cacheprovider tests                                   # 67 passed (night)
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
# development campaign (full lists, tag dev)
$PY -m sp_retrain.build_tables aurora-r2-ncdr $SP_WORK/dev_tables --list $L/ncdr-merged-cafs.txt --nproc 12 ... --tag dev   # and aurora-r2-bnb
for m in numu ncpi0; do $PY -I tools/train_dev_model.py --tables $SP_WORK/dev_tables --tag dev \
    --spec specs/single_photon_${m}_training_spec_dev_round1_domain_v1.yaml --out-dir $SP_WORK/dev_models/$m \
    --manifest-out manifests/dev_round1domain_v1/single_photon_${m}_dev_manifest.json; $PY -I tools/plot_dev_model.py $SP_WORK/dev_models/$m; done
$PY -I tools/summarize_dev_models.py --numu $SP_WORK/dev_models/numu --ncpi0 $SP_WORK/dev_models/ncpi0 \
    --legacy-splits $SP_WORK/eaf_xml_audit_0148e879/tables/sp_bdt_xml_audit --out validation/dev_round1domain_v1_summary.json
# legacy controls on the same test rows (no training), then provenance
for m in numu ncpi0; do $PY -I tools/legacy_control_compare.py --bundle-root $SP_WORK/legacy_bdt_controls --tables $SP_WORK/dev_tables \
    --tag dev --spec specs/single_photon_${m}_training_spec_dev_round1_domain_v1.yaml --dev-out $SP_WORK/dev_models/$m \
    --out-dir $SP_WORK/legacy_controls_results/$m; $PY -I tools/plot_legacy_control.py $SP_WORK/legacy_controls_results/$m; done
$PY -I tools/record_dev_provenance.py --content-commit c83965c1ee1a5726f7bdcda218d768ad2c4f146b \
    --bundle-root $SP_WORK/legacy_bdt_controls --results-dir $SP_WORK/legacy_controls_results
# evening: active Round-2 production (read-only), learning curve (diagnostic), exporter
R=/lus/flare/projects/neutrinoGPU/yuhw/production-prep/WCLocal2026Nov16/full; WD=/lus/flare/projects/neutrinoGPU/yuhw/wcd-0.38.0
for s in bnb:5 ncdr:20; do $PY tools/refresh_smoke_check.py --sample ${s%:*} --new-root $R/${s%:*} \
    --old-manifest manifests/aurora_r2_v0/manifest_aurora-r2-${s%:*}.tsv.gz --units ${s#*:} \
    --numu-xml $WD/uboone/weights/numu_scalars_scores_0923.xml --numu-final-inputs $SP_WORK/external/numu_final_inputs.json \
    --out $SP_WORK/refresh_smoke/smoke_${s%:*}.json; done                     # -> validation/refresh_smoke_wcl1116_aurora.json
# census / list builder (read-only; metadata-bound, run on a compute node with --threads; stopped on the login node):
# $PY tools/make_refresh_list.py --sample ncdr --root $R/ncdr --pairs $R/ncdr-pairs.tsv --census-out <json> --threads 16
$PY tools/ncpi0_negative_learning_curve.py --tables $SP_WORK/dev_tables --tag dev \
    --spec specs/single_photon_ncpi0_training_spec_dev_round1_domain_v1.yaml \
    --out-json validation/ncpi0_negative_learning_curve_dev.json --work-dir $SP_WORK/ncpi0_learning_curve
$PY tools/export_equivalence_check.py ...                                     # see docs/SP_BDT_EXPORT_EQUIVALENCE_STATUS.md
```

## Documents

- `docs/HAIWANG_ROUND2_ACTIVE_PRODUCTION_TRACKER.md`: live snapshot of Haiwang's WCLocal2026Nov16 rerun (tag, jobs,
  configs and hashes, the sample table for training and evaluation, the beam-off half, the smoke, handoff conditions).
- `docs/ROUND2_COLLABORATOR_QUESTION_CLOSURE_AUDIT.md` and `docs/ROUND2_MINIMAL_COLLABORATOR_QUESTIONS.md`: what
  existing evidence answers (§10: the active production), and what remains: one Xuyang/Matteo question, none for
  Haiwang now.
- `docs/SP_BDT_EXPORT_EQUIVALENCE_STATUS.md`: the exporter and its equivalence on the development fixtures.
- `docs/SP_BDT_DEVELOPMENT_TRAINING_SUMMARY.md`, `docs/SP_NUMU_DEVELOPMENT_TRAINING_REPORT.md`,
  `docs/SP_NCPI0_DEVELOPMENT_TRAINING_REPORT.md`: the development campaign (DO NOT DEPLOY).
- `docs/SP_BDT_SCORE_SCALE_AND_EXPORT_REQUIREMENTS.md`: native margin vs production score; what a threshold needs.
- `docs/SP_BDT_ROUND2_FREEZE_ORDER.md`: ownership; the final dependency graph; the freeze order; the final model set;
  the SP nue domain-shift test plan; the threshold policy; the evaluation firewall; `kine_pio_flag`; the roadmap;
  readiness, including the ncpi0 learning curve.
- `docs/YANDEL_THESIS_SP_BDT_TRAINING_SOURCE_AUDIT.md`: the ncpi0 / other training definitions recovered from the
  thesis, the XML cross-check and Appendix E fingerprint, Aurora data readiness, the ncpi0 dry-run census, and the gate.
- `docs/SP_NUMU_TRAINING_SOURCE_AUDIT.md`: the same for SP numu.
- `docs/SP_BDT_DEPENDENCY_AND_TARGET_AUDIT.md`: dependency graph, ncpi0 / other target verdicts, the baseline_v0
  score-convention erratum, and development vs final freeze.
- `docs/NCPI0_OTHER_CAF_INPUT_READINESS.md` with `docs/tables/READINESS_PER_INPUT.md`.
- `docs/SP_BDT_DEPLOYMENT_EXPORT_AUDIT.md`: loader, format, exporter and the equivalence test.
- `docs/HAIWANG_AURORA_TRAINING_REFRESH_REQUEST.md`: **SUPERSEDED, refresh already in progress**; never sent and
  kept as provenance.
- `docs/NCPI0_OTHER_ROUND2_PRODUCTION_HANDOFF_REQUIREMENTS.md`.
- `docs/EAF_ROUND2_EVALUATION_HANDOFF.md`.
- `ATTRIBUTION_AND_PROVENANCE.md`.
