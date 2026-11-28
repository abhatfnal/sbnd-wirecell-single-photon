# wc_upstream_chain: numerical conventions

Bundle version 1.0.0. These are the conventions of wire-cell-toolkit 0.38.0 (`c935e30d`), with the `numu_sim_dqdx_scale` patch of
the `numu_round3af` release, as reproduced bit for bit by this bundle. Code references are to the toolkit:
`root/src/UbooneNumuBDTScorer.cxx`, `UbooneNueBDTScorer.cxx`, `TmvaGradForest.cxx`, `cfg/pgrapher/experiment/sbnd/clus.jsonnet`.

## 1. What "chain-equivalent" means

The bundle computes the value that a step-2 job **stores** in `wc.T_tagger.<name>`. It works from the stored tagger inputs of the
same candidate and any set of weight files. Evidence that it does so:

- **In-chain test** (Aurora PBS 9137793; 18 units; both trees; 128 candidates per tree). A step-2 rerun used the patched toolkit
  and the released files. The values it stored equal this code, with max |Δ| = 0 on all 20 outputs. This includes the ×1.071 scale
  and the flag copy.
- **Shipped closure.** The shipped final models reproduce every stored `numu_score` and `nue_score` on all 593,723 development
  candidates.
- **Aurora module.** The bundle equals the Aurora module `sp_retrain/upstream_chain.py` bit for bit on every candidate of both
  trees (`validation/upstream_r4/bundle_equivalence_*.json`).

**It is not the release's standalone xgboost scorer.** `release/score_release.py` and `training/numu/score_numu_release.py`
evaluate the xgboost JSON trees. The toolkit evaluates the TMVA-XML conversion of the same trees, with float32 cuts. A value that
lies on a split boundary can fall on the other side. This happens for about 1 % of candidates, by up to about 0.4 in the final
scores. Xuyang's own checks report the same effect. Production stores the toolkit value, so the toolkit value is the common
reference.

## 2. Model files: resolution and checksums

- **Resolution.** Files are found in `WIRECELL_PATH` order: the first directory that holds `uboone/weights/<file>`, or `<file>`
  itself.
- **Release route.** Use three directories, in this order:
  1. `releases/nue_round4_ruleA_v2/wirecell/main`;
  2. `releases/numu_round3af/wirecell`;
  3. the shipped wire-cell-data directory (`99c6497f`).

  `numu_tagger3.weights.xml` is not released, so it resolves to the shipped file. The chain does the same.
- **Chain files used.** 20 release XMLs, plus `numu_tagger3` from the shipped directory:
  - νμ: `numu_tagger1.weights.xml`, `numu_tagger2.weights.xml`, `cos_tagger_10.weights.xml`, `numu_scalars_scores_0923.xml`;
  - νe: the 15 files `<m>_BDT.weights.xml`, and `XGB_nue_seed2_0923.xml`.
- **Canonical inventory.** The common inventory for Aurora and EAF is in `data/release_inventory.json`. It holds the 57 unique
  paths named by the two manifests. Their fingerprint is `1d48baed0b3d386b3848c20829099b736f42d6020456f4ea60dd4dbbf60c1f9f`: the
  sha256 of the sorted lines `releases/<path> <sha256>`, each followed by `\n`.
  - The Aurora audit counted 61. That is the same 57 files plus the 4 νμ chain XMLs that `numu_round3af/wirecell/chain_weights.json`
    lists a second time.
  - The EAF audit counted the same 57, with the same hashes. The cross-check is recorded in the inventory.
  - The 15 nogap level-1 XMLs are byte-identical to the main ones, so there are 42 distinct contents.
- **Chain fingerprints.** These are the fields of the final-domain contract. Each is the sha256 of the sorted lines
  `<file> <sha256>` of the resolved files:

  | | release | shipped |
  |---|---|---|
  | `numu_model_fingerprint` (numu_tagger1/2/3, cos_tagger_10, final) | `0b8485a8…` | `595a9963…` |
  | `nue_l1_fingerprints` (15 νe level-1) | `36ec972f…` | `17a8e17e…` |
  | `nue_chain_fingerprint` (15 + `XGB_nue_seed2_0923.xml`) | `3526cdea…` | `655fb390…` |

  `python -m wc_upstream_chain fingerprint --weights-path ...` prints them, and names the route as release, shipped or unknown.
- **Shipped level-1 XMLs.** The 18 shipped level-1 XMLs are TMVA AdaBoost with `VarTransform D,P,U,G,D,N`. The numpy evaluator
  refuses them. Their stored CAF values are exact; Aurora closed them with ROOT TMVA. In the shipped domain, use the stored
  level-1 values.

## 3. Ordered feature lists

The TMVA reader binds inputs **by position**. Every forest checks its `<Variable>` list against the bundle order, and refuses a
file that differs.

- νμ final: the 74 names in `data/numu_l2_inputs_74.txt`.
- νe final: the 258 names in `data/nue_l2_inputs_258.txt`.
- Level-1 model `m`: `L1[m]['lists'] + L1[m]['scalars']` from `data/l1_models.json`. Only `pio_2` has a scalar, `pio_mip_id`, and
  it is last.
- Final-model inputs that are level-1 outputs (`numu_1_score`, `br3_3_score`, …) are replaced by the values the bundle computes.
  Every other input is read from the candidate table, as stored.

## 4. Float precision and tree splits

- Inputs are cast to float32: `float64 → float32`, as the toolkit's `float` buffers. Node cuts are float32.
- At a node, go right when `x >= cut`, and invert when `cType == 0`. Leaves are nodes with `nType != 0`.
- The raw sum adds the float32 leaf responses in double. `boostWeight` is ignored, since Grad boosting gives 1.
- `EvaluateMVA = 2 / (1 + exp(-2 * raw)) - 1`. Do not use `math.tanh`: it differs in the last bit.
- Refused: input transformations, BoostType other than Grad, preselection, Fisher-cut nodes, and a variable list that differs.

## 5. Score transformations

| output | value stored |
|---|---|
| level-1 `<m>_score` | `float32(EvaluateMVA)` of one object, pooled per candidate. Released XMLs already encode Xuyang's `tanh(scale·margin + offset)`, so no further transform. |
| `numu_score` | `float32(log10((1 + v) / (1 − v)))`, with `v = EvaluateMVA` of the final model (= `(2/ln 10) · raw`). When \|v\| ≥ 1 or v is non-finite, v is pulled to ±`nextafter(1, 0)` (`bdt_log_odds_score`). |
| `nue_score` | the same log10 odds when `br_filled == 1`, otherwise **−15**. The release's standalone `score` (raw margin) is in the same units. |

## 6. Object pooling and empty constants

- **Pooling.** `numu_1` and `numu_2` take the **max** over objects. `cosmict_10` and the 15 νe models take the **min**.
- **Empty list.** A candidate with no object gets the model's constant:

  | model | constant |
  |---|---|
  | numu_1 | −0.4 |
  | numu_2 | −0.1 |
  | cosmict_10 | 0.7 |
  | br3_3 | 0.3 |
  | br3_5 | 0.42 |
  | br3_6 | 0.75 |
  | pio_2 | 0.2 |
  | stw_2 | 0.7 |
  | stw_3 | 0.5 |
  | stw_4 | 0.7 |
  | sig_1 | 0.59 |
  | sig_2 | 0.55 |
  | lol_1 | 0.85 |
  | lol_2 | 0.7 |
  | tro_1 | 0.28 |
  | tro_2 | 0.35 |
  | tro_4 | 0.33 |
  | tro_5 | 0.5 |

  The release manifests carry the same constants; `verify_release` checks this.
- **Gates.** In the chain, only `pio_2` is gated. It runs when `pio_filled == 1 and pio_flag_pio == 0`, and otherwise stores its
  constant, even if objects exist.
  - The νμ level-1 models run on **every** candidate. There is no `cosmict_flag_1` gate in the chain; the `pre_cut` in
    `l1_models.json` is the training-table cut of the spec.
  - The 15 νe level-1 models run without a `br_filled` gate.
  - On all 593,723 Aurora candidates, `br_filled != 1` never comes with νe level-1 objects. Such candidates therefore carry the
    constants, and `nue_score = −15`.

## 7. Missing inputs, NaN and sentinels

| situation | chain behaviour |
|---|---|
| any NaN input to one evaluation | `EvaluateMVA = −999` (TMVA::Reader). For a level-1 object, the −999 **wins a min and loses a max**. |
| level-1 input protections, before evaluation | `numu_cc_1_dQ_dx_cut` = ±inf → 10; `cosmict_10_angle_beam` NaN → 0 |
| νμ final protections | NaN → 0 on `cosmict_4_angle_beam`, `cosmict_7_angle_beam`, `cosmict_7_theta`, `cosmict_7_phi` |
| νe final protections | `mip_min_dis` and `mip_quality_shortest_length` capped at 1000; `mip_quality_shortest_angle` NaN → 0; `stem_dir_ratio` NaN → 1 |
| a NaN reaches a final model | `v = −999` saturates to **−16.2556** (`SATURATED_LOW`), in `numu_score` and in `nue_score` (when `br_filled == 1`) |
| `br_filled != 1` | `nue_score = −15` (`NUE_NOT_RUN`) |

The standalone xgboost scripts send NaN down xgboost's default branch instead. The bundle flags these cases in
`diag_l1_models_with_nan_object`, `diag_numu_final_nan_input` and `diag_nue_final_nan_input`. It **keeps the chain value**: no
output is ever replaced by NaN.

## 8. Placeholder candidates

- The builder rule is `is_placeholder = (kine_reco_Enu == 0 and neutrino_type == 0 and nu_x == nu_y == nu_z == 0)`; see
  `identity.placeholder_mask`.
- The chain **scores placeholders** like any other candidate, and their stored scores close bit-exact. The bundle scores them too,
  and reports `diag_is_placeholder`.
- The Aurora SP preselection drops them (`is_placeholder == 0`), so no SP model ever sees a placeholder.

## 9. Simulation-only νμ charge correction (`kind='mc'`)

- **Parameter.** `k = 1.071`, from `numu_round3af/correction.json` (uniform).
- **Scaled copies.** `float32(double(q) · k)` is applied where `q` is finite and > 0. It goes only to the **copies** handed to the
  νμ BDTs:
  - `numu_cc_1_medium_dQ_dx` of every numu_1 segment;
  - `cosmict_{2,3,7}_dQ_dx_{end,front}`, where `cosmict_N_filled == 1`.
- **Flag copy.** The `numu_cc_flag` copy becomes 0 when all of the following hold:
  - a numu_1 segment had flag 1;
  - no flagged segment keeps its scaled dQ/dx below its `numu_cc_1_dQ_dx_cut`;
  - no `numu_cc_2` object has flag 1;
  - `numu_cc_flag_3 != 1`.

  The copy is only ever switched off. Over 1.18 M simulated candidates it is identical to `make_corrected_tables.py --update-flag1`.
  It is reported as `diag_numu_cc_flag_bdt` and `diag_numu_cc_flag_switched_off`.
- **Data.** For `kind='data'`, k = 1 always; the toolkit jsonnet forces 1.0 unless `reality == 'sim'`. There is no default
  `kind`.
- **νe classifier.** It is never corrected; none of its inputs is in the correction set.

## 10. Corrected versus raw features

- **Raw values stay raw.** The stored raw values never change: the six `cosmict_*_dQ_dx_*` values, `numu_cc_flag` and every
  per-object list. That holds in the tables and in the SP inputs (`spec.RAW_MUST_STAY_RAW`). The patched chain likewise changes
  only its private copies; the in-chain test confirmed that every stored raw branch is identical.
- **What changes.** The only stored values a release production changes are the 20 outputs in `spec.UPSTREAM_OUTPUTS`.
- **SP inputs.** The SP models read some of these (`sp.SP_UPSTREAM_INPUTS`):
  - numu: `numu_1_score`, `numu_score`;
  - other: the four νμ outputs;
  - ncpi0: the 15 νe level-1 scores;
  - nue: none.

  `sp.replace_upstream_inputs` replaces exactly these columns and asserts that the raw ones are unchanged.

## 11. Candidate identity

- **Scorer key.** The scorer key defaults to Xuyang's builder key `(file_id, run, subrun, event, cand)`, and must be unique.
  - `cand` = `wc.T_tagger.nu_index`, not the position in the vector.
  - Only events with `wc.valid == 1` are included.
  - `file_id` = the CAF basename (builder default; the `dirname` and `unit` rules exist).
- **Other keys.**
  - Aurora SP tables add `sample`.
  - EAF uses `(file_index, ev, run, subrun, evt, nu_index)`, with `evt = event` and `nu_index = cand`.
  - `identity.translate` and `identity.join_exact` raise on any unmapped, duplicated or extra row.
- **Fixture.** The fixture's `caf/identity_map.parquet` gives, for every candidate of the 18 test CAFs: the tree entry, the
  position and `nu_index`, for both trees.
- **Trees.** Scores depend on the tree: `recTreeWireCell` is dv2_split_move and `recTreeWireCell_dv2snap` is dv2_snap. Score
  each tree separately, and never join across trees.

## 12. Dependencies and environment

- Python ≥ 3.8, numpy ≥ 1.20, pandas ≥ 1.3; pyarrow is needed only for parquet I/O.
- No ROOT, no xgboost, no network. It runs on EAF (AlmaLinux 9, conda) and on Aurora.
- Speed: see `validation/upstream_r4/bundle_equivalence_*.json` (`wall_s` per sample, one core). It is dominated by parsing the
  νe final XMLs: the shipped one is 199 MB.
- **Determinism.** Inputs and cuts are float32, sums are in double, and `exp`/`log10` come from numpy. On Aurora the bundle equals
  the toolkit (glibc `std::exp`) bit for bit. A different numpy or libm build could in principle differ by 1 ulp in a float64
  `exp`/`log10`. That is almost always invisible after the float32 cast, but not guaranteed. **Run the fixture check on every new
  environment**; it compares exact float32 bit patterns.
- The test suite runs without data (synthetic TMVA files). The optional fixture test proves bit-exactness on real development
  candidates.
