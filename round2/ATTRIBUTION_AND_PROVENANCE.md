# Attribution and provenance of round2/

## Whose work this builds on

| source | what is used | how |
|---|---|---|
| Xuyang Ning, `bdt-comm` @ `2c499b937c4e7aa8a5bd948165ffd0e9e260e039` (private GitHub `Ningclover/sbnd-bdt-retraining`; Aurora clone `/lus/flare/projects/neutrinoGPU/xning/bdt-comm`, read-only) | the architecture: merged CAF → per-candidate tables → spec → pool → subrun split → XGBoost; the `T_match` level-2 partner rule, the SCE vertex distance with raw fallback, `label_unreadable` / `truth_pf_unreadable` flags, the placeholder rule, `base_score = 0.5` | **re-implemented, not copied.** Her repository is private and this one is public. Her spec_v1 tables were read, read-only, as an independent reference: 558/558 rows and 1,057 columns agree |
| Xuyang Ning, `bdt-comm/tools/tmva_grad_forest.py` (from the wcgpu1 session) | the TMVA Grad arithmetic, which mirrors the toolkit's `TmvaGradForest` | `sp_retrain/tmva_grad.py` is a fresh implementation of the same documented arithmetic (TMVA `DecisionTreeNode::GoesRight`, `MethodBDT::GetGradBoostMVA`) |
| Haiwang Yu, Aurora Wire-Cell production | aurora-r2 lists `yuhw/production-prep/dlspace/lists/*-merged-cafs.txt`; merged-CAF schema `recTreeWireCell-dlvtx-space.schema.json` (md5 `af9c87c8…`); toolkit checkout used for the source audit (commits `a2785870`, `55177882`) | read only |
| MicroBooNE, `brb-rightback/wcp-uboone-bdt-eyandel` @ `0100d4b62193ef3ccdb7d759ce53eb9c1b4bb541` (public) | single-photon booking (`apps/bdt_convert.cxx`), score transform (`inc/WCPLEEANA/bdt.h`), selection and categories (`inc/WCPLEEANA/cuts.h`) | cited, not copied; sha256-identical to this repo's reference bundle |
| this repository, `baseline_v0/tables/microboone_single_photon_bdt_inputs.csv` (2026-10-05) | the XML `<Variables>` order of the four frozen models | input to `tools/make_feature_configs.py`, sha256 recorded in each feature JSON |
| MicroBooNE public note 1125 (2024-06-07); PRL 136 181806 (arXiv:2502.06064) | documented intent of the four BDTs, the signal definition, cut values | quoted in the audit |

## Pins recorded on 2026-11-17

- **aurora-r2 production toolkit:** `wct_version = sbnd-dlvtx-35-pre-master-merge-54-ga2785870`, read from 15 files.
- **Frozen single-photon XMLs** (sha256, in `provenance/software_versions.yaml`):

  | model | sha256 |
  |---|---|
  | numu | `5886affb…` |
  | other | `8c0ac375…` |
  | ncpi0 | `983a0d82…` |
  | nue | `8580ba04…` |

  None of the four is on Aurora.
- **Shipped νe final model**, used for the scorer check: `uboone/weights/XGB_nue_seed2_0923.xml`, sha256 `6199d202…edd2`.
- **Input manifests:** `manifests/aurora_r2_v0/*.json` (list sha256, manifest sha256).

## Before pushing this branch

The branch has not been pushed. The repository is public. `round2/docs` and `round2/manifests` contain:
- the status of colleagues' unpublished work;
- internal production paths;
- SBND simulation statistics.

Decide with the collaboration what may be public before `git push`. If needed, keep `round2/docs` and `manifests` in a
private repository instead.
