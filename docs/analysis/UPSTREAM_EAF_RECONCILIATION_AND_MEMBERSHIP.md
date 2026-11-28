# Upstream classifier integration, part 2: numerical reconciliation, V3-V5 closure, V7 membership, beam-off ledger, final-bundle checklist

> **SUPERSEDED IN PART (2026-11-28, later):** the nominal scoring backend is now Aurora's toolkit-equivalent `wc_upstream_chain` 1.0.0 (vendored, fingerprint verified); the standalone-xgboost scorer described below is cross-check only; V3-V5 are closed on the development fixture and V7 was updated. See `UPSTREAM_EAF_V3V5_CLOSURE_AND_V7_MEMBERSHIP.md`. Statements below that the nominal backend, fixture or membership manifests are pending are historical.

Date: 2026-11-28. Follows `UPSTREAM_WC_CLASSIFIER_EAF_INTEGRATION_READINESS.md` (pushed checkpoint `fc31cf9`).
Policy unchanged: no official new-model evaluation, no beam-on signal-region access, the `evaluation_guard` is **not** authorised, no thresholds, models or vertex configurations are chosen here. Everything below is bookkeeping, code and tests; no classifier score, kinematic distribution, selection output or blinded datum of an official sample was read.

## 0. State of the dependency on Aurora

Aurora's integration branch `round2/sp-bdt-wcl1116-upstream-r4-integration-20261128` (commits `c10ef2d`, `a66c25d`) was **not yet on `origin`** when this was written (`git ls-remote origin 'refs/heads/round2/*'` shows only `round2/sp-bdt-wcl1116-full-development-20261120` and `round2/sp-other-nue-wcl1116-development-20261117`). Therefore:
- `round2/docs/SP_BDT_UPSTREAM_R4_INTEGRATION_AUDIT.md`, its validation artifacts, `sp_retrain/upstream_chain.py`, the fixture package and the membership manifests have **not** been read or used.
- The nominal scoring backend is **not registered**; the repository now refuses to produce a production overlay until it is (section 1). I deliberately did not write a competing "toolkit-equivalent" implementation: the reference arithmetic is Aurora's, to be pinned by commit and sha256 in `configs/upstream_release.yaml: scoring_backend.reference_pin`.
- Everything that does not depend on that code was prepared and is tested (22 + 2 skipped tests): backend architecture, origins, routes, fixture registration, closure comparison, membership classification, beam-off ledger, bundle checklist.

## 1. Numerical implementation reconciliation

### 1.1 What the code now enforces
| point | before | now |
|---|---|---|
| reference arithmetic | xgboost-standalone re-implementation (bit-identical to the release scripts on synthetic tables) | **nominal backend = toolkit-equivalent scorer (Aurora), pending**; `xgboost_standalone` is `cross_check_only`: `score_nue`/`score_numu` default to the nominal backend and raise `BackendUnavailable` until it is registered (`register_backend`); a standalone overlay can only be written with `purpose=cross_check` and carries `up_origin = offline_xgboost_standalone_cross_check`; nu_e and nu_mu must come from ONE backend |
| why | the release's standalone scorer differs from the toolkit on ~1 % of candidates, up to 0.4 score units (Aurora, 2026-11-28). My earlier agreement with the standalone scripts on synthetic tables was a valid check of *my code against that script*, not evidence of toolkit equivalence | the plausible cause is documented by the release itself: a last-bit float difference in a small-model value (stored as float32(tanh(scale x margin + offset)) in the chain) can cross a split of the final model, moving ~1 % of candidates by up to ~0.3 (nu_mu) / ~0.05 (nu_e). The toolkit evaluates the converted TMVA XMLs in its own arithmetic; xgboost sums differently |
| score origins | implicit | four explicit origins (`configs/upstream_release.yaml: score_origins`): `raw_caf_input`, `numu_corrected_copy`, `stored_production_score`, `offline_chain_equivalent`; the overlay carries `up_origin`; `apply_to_sp_inputs` requires exactly one origin per frame (default `offline_chain_equivalent`) so shipped / stored / cross-check scores can never be mixed into SP features |
| production routes | none | `resolve_route(production, tree)`: **R1** consume stored scores (only if the production books the released models, with hash evidence) or **R2** regenerate offline; unknown productions, non-applicable productions and trees other than the verified one are refused; `provenance_record` calls it (so the vertex-tree / reconstruction-domain guard is unchanged and now route-aware) |
| stored scores of our samples | not stated | declared: Nov16 and old fg1 store the **shipped MicroBooNE-weight** scores (`released_models_booked: false`); route for Nov16 is R2; R1 is refused for them (tested) |
| 1.071 correction | marker column on corrected copies | unchanged; documentation corrected: **recomputing nu_mu offline from the unchanged raw CAF inputs applies the correction exactly once, to a temporary copy, and is not a double correction.** Double correction would require correcting an already-corrected copy (refused), or treating the stored score of a production whose chain already applies the patch as uncorrected |
| release inventory | 57 files | **61**: 57 model files named by the manifests (nue 15 level-1 + 2 level-2 + 2 x 16 chain XML = 49; numu 3 level-1 + 1 level-2 + 4 chain XML = 8) **plus** 2 manifests, `correction.json`, `chain_weights.json`; all hashes verified; `chain_weights.json` hashes equal the manifest's; 23 checks pass |

### 1.2 Items to reconcile line by line once Aurora's branch is readable (EAF side is ready to compare)
| item | EAF value (pinned) | to compare with Aurora |
|---|---|---|
| file count | 61 (above; the "57 vs 61" difference is most likely exactly the four control files, hypothesis not yet checked against Aurora's list) | Aurora's 61 checks and which files they cover (incl. whether nogap / ruleB variants are in scope) |
| release fingerprint | commit `0f13988db44423a227789e151b0a374e25771abd`; manifests `226ab04b...8cb2` (nue), `b900b33f...28d6` (numu); `correction.json` `2e9b7eef...1d960` | identical pins |
| feature mapping | 243 nue L2 candidate scalars + 15 L1 outputs (`l1_<m>` in the L2 input list, = chain `<m>_score`); 71 numu L2 scalars + 3 L1 outputs; 90 / 16 per-object inputs; `pio_mip_id` as per-candidate scalar of pio_2; identity `kine_*` from `T_kine` | `required_inputs.csv` (435 rows) vs Aurora's feature maps |
| score transformations | L1: float32(tanh(scale x pooled margin + offset)), pool min (nue; max for numu_1/numu_2, min for cosmict_10), empty constants (0.3 br3_3, 0.42 br3_5, 0.75 br3_6, 0.2 pio_2, 0.7 stw_2, 0.5 stw_3, 0.7 stw_4, 0.59 sig_1, 0.55 sig_2, 0.85 lol_1, 0.7 lol_2, 0.28 tro_1, 0.35 tro_2, 0.33 tro_4, 0.5 tro_5; numu -0.4, -0.1, 0.7); nue_score = raw L2 margin; numu_score = (2/ln 10) x margin (0.868589) | Aurora's toolkit arithmetic |
| sentinels | nue_score -15 (tagger not run), -16.2556 (any declared input NaN, chain); statuses `scored / tagger_not_run / placeholder / input_nan`; `to_chain_convention` maps them | the in-chain values on the fixtures |
| protections | numu_1 `numu_cc_1_dQ_dx_cut` inf -> 10; cosmict_10 `angle_beam` NaN -> 0; final-model NaN -> 0 on `cosmict_4_angle_beam`, `cosmict_7_angle_beam`, `cosmict_7_theta`, `cosmict_7_phi` | toolkit (`UbooneNumuBDTScorer.cxx`) |
| correction | seven inputs x1.071, simulation only, `cosmict_N_filled == 1`, finite and > 0; flag rule; only switches off | patch arithmetic (float32 product in the toolkit vs float64-then-cast in the release's table script) |
| placeholder / br_filled / pio_2 | status codes; pio_2 pre-cut `pio_filled == 1 and pio_flag_pio == 0` -> empty constant | fixture closure (section 2) |

The numerical reference for every item is the **actual toolkit** (genuine in-chain values), then Aurora's toolkit-equivalent values; the standalone xgboost route is reported only as the cross-check it is.

## 2. V3-V5 fixture closure

Status: **blocked on the fixture package; tests prepared and skipping** (`tests/test_upstream_fixture_closure.py`, 2 tests; `SP_UPSTREAM_FIXTURE_DIR`). No official FermiGrid file is, or may be, used as a fixture (`validate_fixture_manifest` refuses any fixture sharing a file name or production-job id with any official manifest, or a role other than development / dev / fit / nested_validation; `fixtures: []` in the config until a package is registered).

What Aurora must transfer (format fixed in the test docstring): `fixture_manifest.yaml` (role, CAF names, Aurora commit, scorer pin, release commit, production nov16, tree `recTreeWireCell`, simulation flag, sha256s); the pinned release builder's `cands_<tag>.parquet` + 18 `objs_<model>_<tag>.parquet`; `events.parquet` + `manifest_urls.txt` for the identity translation; `expected_scores.parquet` (toolkit values for `up_nue_score`, 15 `up_nue_l1_*`, `up_numu_margin`, `up_numu_score`, `up_numu_{1,2}_score`, `up_cosmict_10_score`, plus `in_chain_*` genuine in-chain columns where the fixture CAFs came from a released-model chain and `shipped_*` stored shipped scores); optionally `expected_features.parquet` (SP inputs, predictions, cut decisions).

Checks the closure test performs once the package exists, all with exact (rtol = 0) comparison via `closure_report`: release verification; fixture registration; raw inputs unchanged after scoring and correction; agreement with the expected toolkit values on every `up_*` column; agreement with genuine in-chain values; placeholder, `br_filled` and NaN-sentinel statuses; the 15 nue empty-object constants for candidates without objects; identity translation + identity-check columns; the SP BDT predictions and cut decisions (needs the bundle's SP models: left as an explicit skip with that reason). Shipped-score reproduction (V4, with the release's `tools/tmva_grad_forest.py` on the shipped weights) is listed for the fixture and needs the shipped TMVA files as well.

## 3. V7 membership audit

### 3.1 Method and what is obtainable from permitted metadata
`scripts/upstream_membership_audit.py` (bookkeeping only) classifies each official sample against a delivered membership manifest into **TRUE_OVERLAP_FILE** (same file name), **TRUE_OVERLAP_GENJOB** (same production job id, i.e. the same generated events, different stage file), **ID_COLLISION** (same run/subrun/event numbers, different job id: a numerical coincidence of distinct productions, not an overlap), **DISJOINT**, **UNDETERMINED** (the manifest lacks file or job identifiers; run/subrun/event alone can never establish disjointness or overlap). The manifest schema (set, sample, file_name or gen_id, optional run/subrun/event, ancestry) is in the script docstring. Tested on synthetic manifests for all five verdicts.

Official identity space (committed, `tables/upstream_release/official_id_space_summary.csv`): every official CAF file name carries a production job id (`filter-gen-0009-3f30-ac82-477c_ncdeltarad`, `Gen2_2026-0002-9c32-4940-5c57`, `data_filtered_decoded_reco1-<uuid>`); ids are unique per file in every sample; the Nov16 and old-production lists contain exactly the same job ids. Run numbers are **not** unique identifiers: official MC uses runs 201-476 (ncdr, nuecc) and 301-8500 (bnb_cv), the nuecc sample has 19 `(run, subrun, evt)` triples repeated across files, and the release itself notes `(run, subrun, event)` is not unique across files of a filtered sample. So an apparent equality of run/subrun/event between an Aurora file and an official file is expected to be frequent and is by itself no evidence of overlap.

### 3.2 The official NC-Delta sample (the critical case)
From the saved SAM metadata (`$SP_DATA/sam/official_gen2_ncdelta_flatcaf.meta.csv.gz`): 15,777 flatCAFs (production `Exclusive`, **`ptype: aurora`**, software v10_14_02_05, created 2026-05-25/26), each flatCAF's job id equals its reco1 parent's (15,777 of 15,777), 9,151 with events > 0; the 9,150 non-empty WCL merged CAFs of both productions are a subset of these job ids (0 outside). Key consequence: **the official "Fermilab" Gen2 samples are themselves Aurora-generated productions** (SAM `ptype: aurora`). The Aurora NC-Delta training sample used upstream (`wcl1116-ncdr`, ~27k events, vs 13,772 official events) could therefore share generator job ids with the official sample (a different reconstruction or a larger campaign of the same generation). That is exactly what `TRUE_OVERLAP_GENJOB` detects; it cannot be excluded from run/subrun/event comparison, and **it cannot be decided without the Aurora / Xuyang file or job-id lists**.

### 3.3 Results today
| comparison | result |
|---|---|
| official samples vs Aurora SP fit / nested validation / outer holdout | **UNDETERMINED**: manifests not delivered (branch not pushed) |
| official samples vs Xuyang's upstream fit and development samples | **UNDETERMINED**: no file or job-id list exists in the release repository (only the statement that the Fermilab samples were not used in training, and that hold-out lists exist matched on `file_id`) |
| official samples vs Snehadri's DL-vertex training samples | **UNDETERMINED**: no membership information on EAF |
| beam-off (odd-run training half) | **overlap established by rule** (section 4) |
| official ncdr vs `wcl1116_beamoff_*` staged lists | not applicable (data) |

Precise additional items needed (no permission beyond bookkeeping): (i) from Aurora, per set (`sp_fit`, `sp_nested_val`, `sp_outer_holdout`), file names or production job ids with sha256, and the `ncdr`, `bnb`, `nuecc` sample definitions (which SAM reco1/flatCAF definitions or which Aurora job-id ranges); (ii) from Xuyang, the file or job-id lists of upstream fit and development samples for BNB, nueCC-filtered, NC-Delta-radiative and beam-off (the training half, 558 files); (iii) from Snehadri, the DL-vertex training file lists if members of official productions; (iv) optionally read-only SAM queries of the parents/children of the Aurora-staged NC-Delta files, which need only the existing Kerberos access.

### 3.4 Independence statement to carry with any result
Upstream model-variant and cut choices (round 3af over 3a/3b/3bf, the 3.06 and 0.985 operating points, data/prediction checks with Run-3 beam-on) already consulted the Fermilab evaluation productions, which are the same WCLocal2026Nov16 samples as our official manifests. The final EAF evaluation is therefore **downstream-SP-independent conditional on the collaboration-selected upstream configuration**: independence is claimed for the retrained SP BDTs, their features, thresholds and selection, not for the upstream classifier choice.

## 4. Beam-off membership ledger

Committed: `tables/upstream_release/beam_off_membership_ledger.csv` (1,058 files, same names in the old and Nov16 manifests).

| partition | files | events | runs | policy |
|---|---:|---:|---:|---|
| odd-run | 572 | 27,076 | 80 | **excluded from any evaluation**: this is the upstream training half (`UPSTREAM_TRAINING_HALF_EXCLUDE`) |
| of which staged for SP `other` training (`wcl1116_beamoff_train_stage/files.txt`, membership list `wcl1116_beamoff_transfer`) | 558 (= 558 distinct units; all odd runs 18253-18591; missing list empty) | 26,418 | | training data (permitted for training and for the closure test below) |
| of which odd-run but NOT staged | **14** (658 events) | | | **still excluded**: all upstream-training-used beam-off data must be excluded, not only the SP-staged 558 |
| even-run | 486 | 22,894 | 76 | `EVALUATION_ELIGIBLE_EVEN_RUN`: the only beam-off that may enter an evaluation; existing policy unchanged |

- The 558 staged files are a strict subset of the 572 odd-run files; none of the 486 even-run files was staged. Whether the 14 unstaged odd-run files were part of Xuyang's training (his README says "the odd-run half ... (558 files)") is **not established**: the column `in_upstream_training_list` is empty until his list arrives; the exclusion does not depend on it.
- Run parity is the rule; the evaluation-eligible half must be checked again against Xuyang's list once delivered (any even-run file in his list would also be excluded).
- **Normalization (not derived, not approved here).** Outstanding: (1) the counter pair (gates `noffbeambnb`, sum 2,542,847 over all 1,058 files, vs triggers/`nbnbinfo` of the beam-on sample, 960,047) and whether the scale uses gates or recorded triggers; (2) live-time / dead-time treatment; (3) run coverage: beam-off runs 18250-18592 vs open-data runs 18255 and 18259 (there is no beam-off file in run 18255); (4) the exposure of the even-run half alone must be recomputed from its own counters once the convention is approved: the existing all-file scale cannot be reused; (5) the odd-run half's counters are irrelevant for evaluation. `rec.mc.nu.imp_weight` for MC is a separate open item.

## 5. Final-production deployment routes (prepared, not enabled)
- **R1** (the final production books the released models): needs a written statement and the hashes of the booked chain weights equal to `release_file_hashes.csv` (`chain:` rows); then stored scores are consumed with origin `stored_production_score` after a provenance check; no regeneration, no correction.
- **R2** (otherwise): offline regeneration with the validated toolkit-equivalent scorer after Xuyang's applicability statement for that production; correction applied once to the temporary copies; origin `offline_chain_equivalent`.
- Neither route can be selected by code today: no entry for the final production exists in `applicability`, and entries are to be added only after production, tree and vertex configuration are frozen and technically validated. The `recTreeWireCell` / Nov16 guard is unchanged.
- **Beam-off in-chain closure test** (training half only): needs (a) the Step-1 outputs (`qlpctree.tar.gz`) for a few odd-run beam-off units, (b) an approved runtime with the patched wire-cell-toolkit 0.38.0 (`numu_sim_dqdx_scale`; data runs with `reality=data`, no correction), and (c) the released weights in `WIRECELL_PATH`. None exists on EAF (no `wire-cell` binary; `/cvmfs` is mounted but contains no such build that I used or verified). The plan is ready: run the chain on 2-3 odd-run units from the 558 staged set, compare stored `nue_score`/`numu_score`/small-model scores with the toolkit-equivalent scorer on the same CAFs (data: no correction anywhere). Needs the runtime and Step-1 inputs from Aurora/Haiwang; **evaluation-half files must not be used.**

## 6. Updated final frozen-bundle checklist
`configs/frozen_bundle_manifest.template.yaml` / `scripts/upstream_bundle_check.py` now also require:
- [ ] `upstream_scorer`: repo, commit, sha256 of the toolkit-equivalent scorer; fixture closure report with sha256 and `closure_exact: true`; `standalone_xgboost_used_for_production: false`.
- [ ] `training_membership.sets_covered` includes `upstream_fit`, `upstream_dev`, `sp_fit`, `sp_nested_val`, `sp_outer_holdout`, `dlvertex_train` (or an explicit "not available"); `dlvertex_training_membership`; `beam_off_upstream_training_files`.
- [ ] (unchanged) bundle owner and commit; four SP model files with sha256, feature lists, score definition, sentinel policy, frozen thresholds (frozen before any official sample is touched); selection manifest; production, tree, vertex configuration, effective-boundary treatment, Xuyang's applicability statement; upstream pins identical to the config; `no_official_sample_used: true`; development fixture package registered by name.
The guard fields (`authorized`, approver, date, bundle hash, selection-manifest hash) stay empty until you fill them.

## 7. Blockers requiring you or a collaborator
1. **Aurora:** push `round2/sp-bdt-wcl1116-upstream-r4-integration-20261128` (so the scorer, audit and closure artifacts can be read and pinned), the fixture package and the membership manifests.
2. **Xuyang:** file/job-id lists for upstream fit/development (all four samples incl. the 558 beam-off files); written applicability statement for the final production and for `recTreeWireCell_dv2snap`; what the chain stores for the nue small-model scores when `br_filled == 0`.
3. **Snehadri:** DL-vertex training membership.
4. **Haiwang/Hanyu:** beam-off normalization convention; final production definition; runtime and Step-1 inputs for the beam-off in-chain closure.
5. **You:** confirm that even-run beam-off remains the only evaluation-eligible beam-off; decide whether read-only SAM parentage queries for Aurora-staged files are acceptable for the NC-Delta overlap audit.
