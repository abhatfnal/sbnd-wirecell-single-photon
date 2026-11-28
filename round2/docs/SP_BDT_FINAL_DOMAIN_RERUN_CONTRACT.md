# SP BDTs: final-domain rerun contract

Date: 2026-11-20; upstream routes R1 / R2 added 2026-11-28. Template `config/campaigns/round2_final_reco_candidate.yaml`; tool
`tools/final_domain_campaign.py`.

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
| upstream | `route`, release and fingerprint fields, `sim_dqdx_scale`, `sim_correction_evidence`; per route the patch hashes (R1) or the stored fingerprints, bundle version and closure record (R2) | section 1a |
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

## 1a. Upstream models: route R1 or R2 (2026-11-28)

The final SP training reads upstream tagger outputs. Two routes are accepted, and both are checked by `final_domain_campaign.py
check`. Neither is filled in the template: the collaboration has not selected the upstream models, and Haiwang's final production
does not exist yet.

| | **R1, preferred**: the final production books the collaboration-selected upstream models in the chain | **R2**: a validated score-only overlay on CAFs that carry the shipped weights |
|---|---|---|
| where the values come from | stored by Haiwang's step 2 (release folders first on `WIRECELL_PATH`, toolkit with the `numu_sim_dqdx_scale` patch) | `wc_upstream_chain` (the common Aurora/EAF bundle) applied to the stored inputs, joined by `build_upstream_overlay.py` |
| `upstream.route` | `R1` | `R2` |
| release | `release_repository`, `release_commit` (40-hex), `canonical_inventory_fingerprint` (64-hex) | same |
| fingerprints | `numu_model_fingerprint`, `nue_l1_fingerprints`, `nue_chain_fingerprint` of the files the chain resolves | the same for the selected models, plus `stored_numu_model_fingerprint` and `stored_nue_l1_fingerprints` of the CAF weights. Stored equal to selected is refused: that is R1 |
| toolkit provenance | `production.toolkit_commit`, `toolkit_version_stamps` with evidence (a patched build stores `<branch>-0.38.0-<n>-g<sha>`, which needs its own approval), `toolkit_patch_sha256` and `workflow_patch_sha256` when k ≠ 1 | the toolkit of the production as stored; `scoring_bundle_version` |
| simulation-only charge correction | `sim_dqdx_scale` (k), and `sim_correction_evidence` = a `tools/verify_sim_dqdx_logs.py` record over **every** step-2 job of the training samples: VERIFIED, every simulation log has the scale line with k, no data log has it | `sim_dqdx_scale`, and `sim_correction_evidence` = the overlay record (VERIFIED, route R2, per sample `kind` and `sim_dqdx_scale_applied`: k for simulation, 1.0 for data) |
| closure in the final domain | the in-chain values are the stored values | `overlay_closure_record`, CLOSED for this production tag: the shipped final models reproduce the stored scores, and the bundle equals an in-chain rerun of a sample of this production |
| vertex mode and boundary | `production.vertex_mode`, `wc_trees`, `effective_boundary_profile`, `effective_boundary_sha256` (both routes) | same |

Always refused:
- the patched-toolkit stamp `numu-sim-dqdx-scale-0.38.0-1-gccb19cf`. It was approved on 2026-11-28 **for development validation
  only** (`sp_retrain.provenance.UPSTREAM_R4_DEV_TOOLKIT`, `validation/upstream_r4/patched_toolkit_dev_approval.json`);
- any stamp list containing patterns. Membership is exact string equality.

**Enforcement chain of the simulation-only correction** (read-only recheck, 2026-11-28; our clones `ccb19cf` and `eaaa02f`):

1. **Workflow** (`swp-wclocal aurora/bin/step2.sh:26`). It builds `--tla-code numu_sim_dqdx_scale=<k>` whenever
   `NUMU_SIM_DQDX_SCALE` is set, whatever the reality. `site/aurora.sh:15` forwards the variable. **The workflow does not gate
   it.**
2. **Toolkit jsonnet** (`cfg/pgrapher/experiment/sbnd/clus.jsonnet:2993`). This is the only gate:
   `numu_sim_dqdx_scale = (if reality == 'sim' then numu_sim_dqdx_scale else 1.0)`. Then `common/clus.jsonnet:778` omits the key
   at 1.0, so a data configuration is byte-identical to the unpatched one.
3. **C++** (`UbooneNumuBDTScorer.cxx:55`). It reads the value and does **not** re-check reality.
4. **Tests.**
   - In-chain test: the data arm with the variable set stored the unscaled values and had 0 scale lines.
   - Log census (`validation/upstream_r4/sim_dqdx_log_census_chain_test.json`): 36/36 simulation logs scaled, 0/2 data logs.
   - The census flags the `noscale` arm, so a simulation job without the factor is detected.

Residual risks:
- **A mislabelled unit.** A unit run as `REAL=sim` would also switch on truth matching, so the whole job would be visibly wrong.
- **A hand-built configuration.**
- **The reverse gap: a simulation job that silently stays at k = 1.** Two cases:
  - drivers that never pass the parameter (`wct-pr-perevt.jsonnet`, `wcls-img-clus-matching-pr-lib.jsonnet:193`);
  - FermiGrid `fermigrid/bin/submit.sh:36`, whose `jobsub -e` list does not forward `NUMU_SIM_DQDX_SCALE`.

**For R1, the log census over every training-sample job is therefore mandatory, not optional.** The production workflow should
also set the variable for simulation jobs only. Haiwang's current workflow does not reference the variable at all
(`swp-wclocal@d05cf47`).

The fingerprint function is `wc_upstream_chain.chain_fingerprints`, identical to `sp_retrain.upstream_chain.fingerprint`. Values:

| | numu | νe level-1 | νe level-1 + final |
|---|---|---|---|
| releases @ 0f13988d | `0b8485a8…` | `36ec972f…` | `3526cdea…` |
| shipped | `595a9963…` | `17a8e17e…` | `655fb390…` |

The canonical inventory fingerprint of the release is `1d48baed…`: the 57 manifest-listed files, the same at Aurora and EAF. See
`SP_BDT_UPSTREAM_R4_INTEGRATION_AUDIT.md` and `SP_BDT_UPSTREAM_R4_FOLLOWUP.md`.

## 2. The rerun (`final_domain_campaign.py plan` writes it as a script)

| step | tool (existing, tested) |
|---|---|
| 1 provenance verification | `final_domain_campaign.py check`; `verify_staged_beamoff.py --expect-reco campaign` (exact stamps, per-tree `dl_weights`, membership, odd runs, checksums, `ismc`); upstream route R1: `wc_upstream_chain fingerprint` on the production `WIRECELL_PATH` and `verify_sim_dqdx_logs.py`; route R2: `extract_upstream_inputs.py` → `wc_upstream_chain score` (kind per sample) → `build_upstream_overlay.py` |
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
