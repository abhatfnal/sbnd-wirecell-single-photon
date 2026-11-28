# Attribution and provenance of round2/

## Whose work this builds on

| source | what is used | how |
|---|---|---|
| Xuyang Ning, `bdt-comm` @ `2c499b937c4e7aa8a5bd948165ffd0e9e260e039` (private GitHub `Ningclover/sbnd-bdt-retraining`; Aurora clone `/lus/flare/projects/neutrinoGPU/xning/bdt-comm`, read-only) | the architecture: merged CAF → per-candidate tables → spec → pool → subrun split → XGBoost; the `T_match` level-2 partner rule, the SCE vertex distance with raw fallback, `label_unreadable` / `truth_pf_unreadable` flags, the placeholder rule, `base_score = 0.5` | **re-implemented, not copied.** Her repository is private and this one is public. Her spec_v1 tables were read, read-only, as an independent reference: 558/558 rows and 1,057 columns agree |
| Xuyang Ning, public release repository `Ningclover/sbnd-wirecell-bdt` @ `0f13988db44423a227789e151b0a374e25771abd` (2026-11-24) | the upstream releases `numu_round3af` and `nue_round4_ruleA_v2`, their scorers, the table builder, the toolkit / Aurora-workflow patches | **three spec files copied verbatim** into `config/upstream/` (`numu_l2_inputs_74.txt`, `nue_l2_inputs_258.txt`, `l1_models_xning_0f13988d.py` = his `spec/l1_models.py`; sha256 checked byte-identical by `tests/test_upstream_r4.py`). His scorers and builder are **run unmodified** from the read-only clone `$SP_WORK/upstream_release_audit/sbnd-wirecell-bdt`; `sp_retrain/upstream_chain.py` is a fresh transcription of the toolkit C++ (wire-cell-toolkit c935e30d + his patch); no model file is copied into this repository |
| Xuyang Ning, `bdt-comm/tools/tmva_grad_forest.py` (from the wcgpu1 session) | the TMVA Grad arithmetic, which mirrors the toolkit's `TmvaGradForest` | `sp_retrain/tmva_grad.py` is a fresh implementation of the same documented arithmetic (TMVA `DecisionTreeNode::GoesRight`, `MethodBDT::GetGradBoostMVA`) |
| Haiwang Yu, Aurora Wire-Cell production | aurora-r2 lists `yuhw/production-prep/dlspace/lists/*-merged-cafs.txt`; merged-CAF schema `recTreeWireCell-dlvtx-space.schema.json` (md5 `af9c87c8…`); toolkit checkout used for the source audit (commits `a2785870`, `55177882`) | read only |
| MicroBooNE, `brb-rightback/wcp-uboone-bdt-eyandel` @ `0100d4b62193ef3ccdb7d759ce53eb9c1b4bb541` (public) | single-photon booking (`apps/bdt_convert.cxx`), score transform (`inc/WCPLEEANA/bdt.h`), selection and categories (`inc/WCPLEEANA/cuts.h`) | cited, not copied; sha256-identical to this repo's reference bundle |
| this repository, `baseline_v0/tables/microboone_single_photon_bdt_inputs.csv` (2026-10-05) | the XML `<Variables>` order of the four frozen models | input to `tools/make_feature_configs.py`, sha256 recorded in each feature JSON |
| MicroBooNE public note 1125 (2024-06-07); PRL 136 181806 (arXiv:2502.06064) | documented intent of the four BDTs, the signal definition, cut values | quoted in the audit |
| E. H. Yandel, *A Search for Anomalous Single Photon Production in Neutrino Interactions with the MicroBooNE Detector*, PhD thesis, UC Santa Barbara, 2024, https://escholarship.org/uc/item/6rq082dr (PDF sha256 `0ad56e36…1465`) | the training classes, sample counts, preselection, split and XGBoost parameters of the four single-photon BDTs (§5.1.2, §5.2, App. E) | cited by page in `docs/YANDEL_THESIS_SP_BDT_TRAINING_SOURCE_AUDIT.md`. The PDF and its text extraction are **not** in git and must not be added. The PDF is kept at `$SP_WORK/thesis_audit/` |
| MicroBooNE legacy single-photon XMLs, EAF bundle `legacy_sp_bdt_bundle_20261117` (tarball sha256 `90239e2a…08cd8`; byte-identical copies of `/exp/uboone/app/users/uboonepro/bbogart/wcp-uboone-bdt/weights/single_photon_*_bdt_final.xml`) | numu and ncpi0 legacy controls for the development study | scored, never modified, **not** in git (`$SP_WORK/legacy_bdt_controls`); registered in `manifests/dev_round1domain_v1/legacy_controls.json` |
| this repository, EAF branch `analysis/sp-bdt-thesis-xml-compatibility-20261117` @ `0148e879ae44c0c61f0fb7874079734a4cead3fa` (Avinay, EAF) | frozen-XML trees, depth, per-variable split counts and upstream usage (`tables/sp_bdt_xml_audit/`) | read with `git show`, not merged; compared with the thesis Appendix E F scores |

## Pins recorded on 2026-11-17

- **aurora-r2 production toolkit:** `wct_version = sbnd-dlvtx-35-pre-master-merge-54-ga2785870`, read from 15 files.
- **Frozen single-photon XMLs** (sha256, in `provenance/software_versions.yaml`):

  | model | sha256 |
  |---|---|
  | numu | `5886affb…` |
  | other | `8c0ac375…` |
  | ncpi0 | `983a0d82…` |
  | nue | `8580ba04…` |

  They are on Aurora in the verified EAF bundle `$SP_WORK/legacy_bdt_controls/legacy_sp_bdt_bundle_20261117/` (all four
  sha256 match; not in git).
- **Shipped νe final model**, used for the scorer check: `uboone/weights/XGB_nue_seed2_0923.xml`, sha256 `6199d202…edd2`.
- **Input manifests:** `manifests/aurora_r2_v0/*.json` (list sha256, manifest sha256).

## Before pushing this branch

The branch has not been pushed. The repository is public. `round2/docs` and `round2/manifests` contain:
- the status of colleagues' unpublished work;
- internal production paths;
- SBND simulation statistics.

Decide with the collaboration what may be public before `git push`. If needed, keep `round2/docs` and `manifests` in a
private repository instead.
