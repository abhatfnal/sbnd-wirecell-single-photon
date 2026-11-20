# SP BDTs: final-domain rerun contract

Date: 2026-11-20. Template `config/campaigns/round2_final_reco_candidate.yaml`; tool `tools/final_domain_campaign.py`.

**Purpose.** When Haiwang's next production, with the measured non-box / effective boundary, appears, the final-domain
SP retraining is a **validated rerun of existing, tested tools, not new software development**.
- The placeholder domain is `round2_final_reco_candidate`.
- Its production tag and paths are not known and are **not invented**.

## 1. What the campaign must be given (refused otherwise)

| block | field | requirement |
|---|---|---|
| production | `tag` | Haiwang's production tag |
| | `toolkit_commit` | full 40-hex commit |
| | `toolkit_version_stamps` | closed list of the exact stored `wc.Trun.wct_version` strings, one per build (cf. `0.38.0` / `HEAD-0.38.0`, `WCL1116_TOOLKIT_PROVENANCE_NOTE.md`) |
| | `toolkit_stamp_evidence` | where each stamp was mapped to the commit |
| | `dl_bundle`, `dl_bundle_sha256` | DL vertex bundle and its 64-hex sha256 |
| | `vertex_mode`, `wc_trees` | the collaboration's vertex mode and the stored tree for it |
| | `effective_boundary_profile`, `effective_boundary_sha256` | the boundary configuration used by `cosmic_tagger()` |
| upstream | `numu_model_fingerprint` | 64-hex over the collaboration-frozen νμ final + level-1 weights |
| | `nue_l1_fingerprints` | 64-hex over the 15 νe level-1 weights |
| inputs | `ncdr_list`, `bnb_list`, `nuecc_list` | path, sha256 and file count of the Aurora **training** lists; no official-evaluation marker in any path |
| | `beamoff_train_list` | the odd-run beam-off TRAINING half reprocessed in this domain |
| | `beamoff_staging_record`, `beamoff_verifier_sha256` | `verify_staged_beamoff.py --expect-reco campaign --campaign-spec …` output, VERIFIED, with the same list hash, toolkit commit and verifier hash, and a stamp from the closed list |
| | `beamoff_exception` | `approved_by`, `date`, `staged_dir`: the SP other firewall exception **re-approved** for this domain |

`final_domain_campaign.py check` refuses, with exit code 2, when any field is null, a placeholder (`TBD`, `TODO`,
`REQUIRED`, …), malformed, or inconsistent with the files it names. Tests
(`tests/test_wcl1116_full_dev.py`):
- the committed template is refused;
- each single defect is refused: a short commit, an unknown vertex mode, a duplicate stamp, a placeholder fingerprint,
  an upper-case hash, a list hash mismatch, an official path;
- a complete synthetic campaign passes.

## 2. The rerun (`final_domain_campaign.py plan` writes it as a script)

| step | tool (existing, tested) |
|---|---|
| 1 provenance verification | `final_domain_campaign.py check`; `verify_staged_beamoff.py --expect-reco campaign` (exact stamps, per-tree `dl_weights`, membership, odd runs, checksums, `ismc`) |
| 2 table building | `sp_retrain.build_tables`, per sample, on compute nodes (`-A neutrinoGPU::WireCell_aurora`); the EXT sample through `--approved-exceptions-spec` |
| 3 sample census | `sp_other_census.py`, `sp_nue_census.py`, `make_refresh_list.py` census records |
| 4 frozen feature-spec loading | `final_domain_campaign.py specs`. It regenerates the four WCL1116 development specs, changing only the reconstruction block, the sample lists, the campaign and the re-approved EXT exception; features, order, hyperparameters and seed are unchanged (tested). The trainer accepts them (`devtrain.CAMPAIGN_FINAL_CANDIDATE`) |
| 5 model training | `train_wcl1116_dev_model.py` (each sample's files checked against its own verified stamp) |
| 6 nested-validation reports | `wcl1116_full_dev_study.py` (nested_v1), `sp_operating_points.py` (joint four-cut evaluator, topology) |
| 7 export, 8 Python equivalence | `export_equivalence_check.py` |
| 9 C++ equivalence | `cpp_equivalence_check.py prepare` → the SL7 WCT compute-node job → `compare` |
| 10 compact summary | `sp_feature_stability.py`; a results document from the validation JSONs |

## 3. Final-domain model policy (written now)

| model | final training needs | WCL1116 development evidence |
|---|---|---|
| **SP numu** | final reconstruction domain; **collaboration-frozen upstream νμ outputs** (`numu_score`, `numu_1_score`), recomputed on the final training CAFs | retraining beneficial (+0.018 / +0.020); without the upstream family −0.003 nested-validation AUC |
| **SP other** | final reconstruction domain **with the effective / non-box boundary**; collaboration-frozen upstream νμ outputs; the **odd-run beam-off training half reprocessed in that domain**, staged and **re-verified with the same strict procedure** (exact stamps, checksums, membership), and the exception re-approved | RETRAINING CLEARLY BENEFICIAL (+0.076); 60 of 146 inputs tied to `cosmic_tagger()`. Removing the cosmic or the upstream family costs about 0.009, both 0.026, so **SP other must be retrained in the final domain** |
| **SP ncpi0** | final reconstruction domain; stored / frozen νe L1 inputs; **Policy B** | retraining beneficial (+0.051); current sample adequate by the pre-registered rule; more NC π⁰ would come from the `outncpi0` stream of the same Gen2 filter, not from the νe CC sample |
| **SP nue** | final reconstruction domain; the **weighting decision informed by the WCL1116 study** (development evidence: unweighted) | RETRAINING CLEARLY BENEFICIAL (+0.041 / +0.038) |

All four are being developed now. **None is final-deployment-ready.** No final threshold, vertex mode or weighting is
frozen. FermiGrid evaluation comes only after the final models and the validation-only thresholds are frozen.
