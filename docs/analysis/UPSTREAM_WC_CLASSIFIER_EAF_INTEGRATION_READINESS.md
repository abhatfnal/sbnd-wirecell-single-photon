# Upstream SBND Wire-Cell nu_e / nu_mu classifiers: EAF / FermiGrid integration readiness report

Date: 2026-11-28. Branch `analysis/ncdelta-purity-datamc-20261120` (pushed base `d18b8a8`; this work is local until Avinay reviews).
Scope: audit the released upstream classifiers, audit the official EAF samples for offline score-only regeneration, prepare an isolated, non-destructive deployment layer, and list what remains before a final evaluation.
**Nothing was evaluated.** No official sample was read except branch-name metadata (and even that is pending credentials, see 4.4); no upstream score was computed on any official event; no selection, threshold, vertex mode or model variant was chosen; no signal-region data were opened; no Aurora development BDT was evaluated. The independent-evaluation policy stays in force and is now enforced in code (section 7).

## 1. Summary

| item | status |
|---|---|
| Release pinned and verified | **done**: commit `0f13988db44423a227789e151b0a374e25771abd`; 57 model files, all sha256 match the manifests; 22 manifest/invariant checks pass |
| Recommended defaults are the ones audited | **yes**: `nue_round4_ruleA_v2` (chain-compatible A v2, `wirecell/main`) and `numu_round3af` |
| nu_mu 1.071 correction semantics understood and implemented on copies only | **done**; matches the release's `make_corrected_tables.py --update-flag1` bit for bit on synthetic tables; raw SP features, nu_e inputs and data are protected by code |
| Our scoring layer equals the release's standalone scripts | **done**: bit-identical final margins and level-1 values (nu_e and nu_mu, simulation and data routes) on synthetic tables |
| Which official samples correspond to WCL1116 | **done** (section 3): all six `manifests/wcl1116/*` samples; the old fg1-era files are NOT applicable |
| EAF analysis tables sufficient for rescoring | **no**: they hold ~64 summary columns. Rescoring needs the merged CAFs themselves (`recTreeWireCell`), which are already reachable on EAF |
| Merged CAFs contain every required input | **expected, not yet verified here**: the release's own table builder reads exactly these branches from the same production files, and the release states it re-scored the shipped model from them. The metadata-only schema audit script is ready but could not run: no valid Kerberos/bearer credentials in this session (4.4) |
| Final evaluation | **not authorised and not executable**: `evaluation_guard` is empty; no frozen bundle yet |

Findings that change how the evaluation must be run (details in sections 5-8):
1. **Beam-off overlaps the upstream training data.** The upstream classifiers were trained on the *odd-run half* of the beam-off data. Our beam-off manifest has 572 odd-run and 486 even-run files (both productions). Any use of beam-off in an evaluation of these scores must use the even-run half only (and the beam-off normalization is still unresolved).
2. **The upstream operating points and the choice among variants were made on the same Fermilab evaluation productions** (same WCLocal2026Nov16 merged CAFs as our manifests), including Run-3 beam-on data/prediction checks. The released *models* were not trained on them, but the upstream choices (e.g. round 3af over 3a/3b/3bf, the 3.06 and 0.985 cuts) saw them. Our code never uses those cuts; the final SP selection must come from Aurora's frozen bundle.
3. **NC-Delta radiative events were training background in both upstream classifiers** (Aurora `wcl1116-ncdr`, ~27k events). Our official signal sample (13,772 events) is a separate production, but event-level disjointness is **not documented**. This is the most important disjointness check, because the upstream scores of the *signal* feed the downstream SP BDTs.
4. **The released models are verified for `recTreeWireCell` (dv2_split_move) of WCLocal2026Nov16 only.** Nothing is said for `recTreeWireCell_dv2snap`, for the expected effective-boundary production, or for the old fg1-era files.
5. **Downstream dependence is narrow and explicit:** the numu SP BDT reads `numu_1_score`, `numu_score`; the ncpi0 SP BDT reads the 15 nu_e small-model scores; the `other` SP BDT reads `cosmict_10_score`, `numu_1_score`, `numu_2_score`, `numu_score` **and** raw `cosmict_{2,3,7}_dQ_dx_{end,front}` and `numu_cc_flag` (which must stay raw); the nue SP BDT reads none; the final `nue_score` is read by no SP BDT.

## 2. The upstream release (audit)

Repository `https://github.com/Ningclover/sbnd-wirecell-bdt`, `releases/`. Pinned commit **`0f13988db44423a227789e151b0a374e25771abd`** (merge of PR #9, 2026-11-24, "releases/README: current defaults..."). Trained on SBND simulation reconstructed with **WCLocal2026Nov16, wire-cell-toolkit 0.38.0 (c935e30d)**, which equals the toolkit of our Nov16 manifests. Models are xgboost 3.4.1 JSON (our environment has xgboost 3.4.2; the cross-check below shows bit-identical margins).

| model | folder | manifest sha256 | key file sha256 |
|---|---|---|---|
| nu_e A v2, main chain variant | `releases/nue_round4_ruleA_v2` | `226ab04bc8a7d5feda2e1e7ae5168a595ee4a5bc8d4ae199c0272814640a8cb2` | L2 `l2/nue_l2.json` `67df0d90...813743` (116 trees, 258 inputs); chain final `wirecell/main/uboone/weights/XGB_nue_seed2_0923.xml` `9912f6f2...f078`; 15 small models `l1/*.json` + 15 chain XMLs |
| nu_mu round 3af | `releases/numu_round3af` | `b900b33f453f1b52754e85605626859f7bd290cdb6e2e2cbac2d4e3fd5a328d6` | L2 `l2/numu_l2.json` `48b3c887...c434920` (472 trees, 74 inputs); chain final `numu_scalars_scores_0923.xml` `81fb26f8...6310b6`; small models numu_1 / numu_2 / cosmict_10 (`l1/*.json`, chain XMLs `1af283dd...`, `a129aaad...`, `8405c13c...`) |
| correction | `numu_round3af/correction.json` | `2e9b7eef8cf1b355b15b32ffa876bda6779699f4e0c7cdf195032554e7c1d960` | `{"mode":"uniform","k":1.071}` |

All 57 files named by the two manifests were hashed (`tables/upstream_release/release_file_hashes.csv`); the audit (`scripts/upstream_release_audit.py`, output `release_audit.json`) passes 22 checks: pinned HEAD, clean `releases/`, manifest hashes, A v2 name and `default.variant == main`, label rule A, `chain_transform` present (the v2 chain version that runs without missing values), 258 declared inputs and nothing left out, 15 level-1 models, 16 chain files, round-3af name, correction `uniform` with `k == 1.071`, the seven documented dQ/dx inputs, `update_flag1` true (3af, not 3a), 74 inputs including `numu_cc_flag`, informational cuts as released.

**The nu_e model is the chain-compatible A v2** (not v1, whose final model expects NaNs, not A-nogap, not B v2). A v2 retrains the final model on the values the chain stores: small-model output `float32(tanh(scale * pooled margin + offset))`, with the toolkit's empty constants (e.g. 0.3 for br3_3, 0.2 for pio_2) for a candidate with no object or a failed pio_2 pre-cut; final output = raw margin; `-15` = tagger did not run; `-16.2556` = a declared input was NaN.

**nu_mu 1.071 correction** (README + `correction.json` + toolkit patch, all read):
- seven inputs only: `numu_cc_1_medium_dQ_dx` of every numu_1 segment and `cosmict_{2,3,7}_dQ_dx_{end,front}` (the latter only where `cosmict_N_filled == 1`), only finite values > 0, multiplied by 1.071;
- internal muon-flag update: per numu_1 segment, `numu_cc_flag_1` stays on iff the corrected dQ/dx is still below `numu_cc_1_dQ_dx_cut`; `numu_cc_flag` = any segment flag_1 OR any `numu_cc_flag_2` OR `numu_cc_flag_3`; the flag is only ever switched off (about 1 % of flagged segments);
- applied **only to copies handed to the nu_mu BDTs**, simulation only; stored tagger values stay raw; the stored `numu_score` of a patched-chain simulation is already corrected, so re-scoring those would double-correct (the Aurora/chain route is irrelevant to us because our CAFs were produced with the shipped weights and no patch);
- never to data (the toolkit's `reality == 'data'` forces 1.0), never to the nu_e classifier.
Without the correction, 9,049 of 302,172 BNB candidates move across the cut (release README): the correction is part of the model.

Release-side caveats worth knowing: the final-model scale is `numu_score = (2/ln 10) margin = 0.868589 margin`; the upstream scorers read `numu_1_score`, `numu_2_score`, `cosmict_10_score` columns in the candidate table even though they overwrite them; candidates move by up to ~0.05 (nu_e) or ~0.3 (nu_mu) in score from last-bit float differences, which matters only within that distance of a cut.

## 3. Official sample inventory and provenance

Correspondence to the updated WCL1116 reconstruction (all numbers from `docs/analysis/WCL1116_NOV16_FROZEN_R1_SELECTION_REPLAY.md` section 4, `configs/samples.yaml`, `tables/ncdelta_purity_datamc/normalization_ledger.csv`, `manifests/wcl1116/*.tsv.gz`):

| sample (registry name) | WCL1116 folder (`.../prod-fermigrid/WCLocal2026Nov16/`) | merged CAFs | events (wc.valid) | exposure | truth / systematic weights | role / data policy |
|---|---|---:|---:|---|---|---|
| `bnb_cv` | `mc-cv` | 37,742 | 500,000 (499,968) | sum TotalPOT 2.7194e19 over the listed files (same files in old and Nov16) | MC truth, `T_match`, 22,485-universe weights, `imp_weight` (not 1; NOT applied) | background evaluation; MC |
| `official_gen2_ncdelta` | `mc-ncdr` | 9,150 (6,626 empty units) | 13,772 (13,772) | SAM mc.pot 2.8385e21; denominator 12,427 TPC-box events | MC truth, weights | signal evaluation; MC |
| `nuecc` | `mc-nuecc` | 11,441 | 100,003 (99,987) | filtered production, ~100x the CV POT per event; control only | MC truth | control only; not a BNB mixture |
| `beam_off` | `beam-off` | 1,058 | 49,970 (49,968) | none (TotalPOT = 0); gate counters 2,542,847 (beam-off) vs 960,047 (beam-on); **scale not approved** | data | shape / counts only |
| `beam_on_open` | `opendata` | 1,817 | 89,946 (89,946) | 4.62125e18 POT (runs 18255, 18259) | data | allowed at preselection / sidebands only |
| `run3bnb` | `run3bnb` | 2,208 | 109,487 (109,485) | not used | data | **blocked** at every stage |
| signal region (final selection) of any beam-on | - | - | - | - | - | **BLOCKED** (`approved_by` empty) |

- **Productions.** `nov16` = WCLocal2026Nov16 (WCT 0.38.0 c935e30d, larwirecell ad5d9421, wire-cell-data 99c6497f, DV2-MAX `aurora_space`, `recTreeWireCell` schema `af9c87c8`, 2,416 branches). `old_fg1` = the fg1-era reconstruction (WCT 4b6853d4; open data f6fd2209; `recTreeWireCell` schema `d4396a34`, 2,401 branches). Step 1 (imaging/clustering/matching) is identical between them; step 2 changed. The old production is the documented diagnostic baseline (efficiency 6.70 %, MC-only purity 2.74 %) and is **not** a target of the released models (`configs/upstream_release.yaml: applicability.old_fg1.applicable: false`).
- **Two trees.** Each Nov16 file carries `recTreeWireCell` (dv2_split_move, the production default, which the release table builder reads and which all our Nov16 results use) and `recTreeWireCell_dv2snap` (dv2_snap; schema `d4396a34`; recorded for provenance, never read in the analysis). Scores depend on the tree, so an overlay is per tree; `provenance_record` records `wc_tree`, and refuses any tree other than the one verified.
- **Identity, truth, ownership, POT, weights.** Identity in our tables is `(file_index, ev, run, subrun, evt, c_nu_index)`; the release's builder uses `(file_id, run, subrun, event, cand)`. The layer translates 1:1 through our `events.parquet` and the manifest and raises on any unmapped file, missing event or ambiguity (`translate_identity`). Truth (`rec.mc.*`), the 22,485 weight universes (`rec.mc.nu.wgt.univ`), POT (`rec.hdr`, TotalPOT), `imp_weight`, the owner-interaction tables (`owners_*`), the identity-proof tables and all committed results are **never rewritten** by the overlay; `scripts/upstream_integrity_manifest.py` fingerprints 95 baseline artifacts (candidates/events/files tables of both productions, owners, identity proofs, derived signal tables, the committed result CSVs; `tables/upstream_release/baseline_artifact_hashes.csv`) and `--verify` proves they are unchanged. Candidate identity does not depend on scores, so owner tables stay valid; what changes with new scores is the *selected set*, which is rebuilt as new files, never edited in place.
- **Existing diagnostics (preserved).** NC-Delta efficiency 6.70 % -> 15.60 %; MC-only expected purity 2.74 % -> 2.63 % (upper bound, beam-off unresolved); NC-pi0 sideband Data/MC 0.764 -> 0.740; the Np/0p control diagnostics and the available-covariance study are all untouched and fingerprinted. They stay labelled "frozen legacy chain with shipped upstream scores".

Manifest-level inventory with the upstream training/evaluation statement per sample: `tables/upstream_release/sample_applicability.csv` (`scripts/upstream_sample_inventory.py`).

## 4. Input schema and offline rescoring compatibility

### 4.1 What the classifiers need
`tables/upstream_release/required_inputs.csv` (435 rows) lists every quantity with its `recTreeWireCell` branch:
- nu_e: 243 candidate scalars (the 258 final-model inputs minus the 15 small-model outputs; 242 `wc.T_tagger.*` plus `wc.T_kine.kine_reco_Enu`), `br_filled`, the pio_2 pre-cut scalars (`pio_filled`, `pio_flag_pio`), `pio_mip_id`, and **90 per-object list inputs** for the 15 small models (each a jagged branch with `..idx` / `..length` helpers).
- nu_mu: 71 candidate scalars of the 74 final-model inputs (the other three are small-model outputs) plus `cosmict_{2,3,7}_filled`, **16 per-object list inputs** (numu_1, numu_2, cosmict_10) and the two per-object flag lists used only by the correction.
- identity / placeholder: `nu_index`, `nu_x`, `nu_y`, `nu_z`, `neutrino_type`, `kine_reco_Enu`.
- Nothing in the nu_e inputs is in the correction set (checked by a test): the nu_e classifier is insensitive to the 1.071 handling by construction, and the guard still forbids passing it corrected data.

### 4.2 What the existing EAF tables contain
`analysis_tables/*/candidates.parquet` has 64 columns (~40 `c_*` reconstruction summaries, truth-dominant fields, cumulative stage flags). It carries none of the 243 + 71 candidate scalars and none of the 106 per-object list inputs. The SP BDTs the analysis already uses read a different, smaller set (`input_source_table_*.csv`: numu 73, nue 56, ncpi0 45, other 146 inputs) read directly from the CAFs. **Score-only regeneration therefore needs a re-read of the merged CAFs, not richer tables, and not a new Wire-Cell production**, provided 4.3-4.4 hold.

### 4.3 Evidence that the merged CAFs are sufficient
- The release's table builder (`tables/build_tables.py`) reads exactly `recTreeWireCell` branches (`wc.T_tagger.*` scalars, per-object lists with `..idx/..length`, `wc.T_kine`, `wc.T_dlvtx_call`, `wc.T_match`, `wc.T_truth_nu`, `wc.T_truth_pf`) from the *same* production files (its `examples/gpvm` README builds tables for the Fermilab productions from the merged CAFs, `--file-id-from dirname`), and the release README states the shipped TMVA model was re-scored without ROOT "to prove the merged CAFs carry the complete model inputs".
- The Nov16 schema (`af9c87c8`, 2,416 branches) is the old schema plus the DL-vertex space dump; the tagger branches are unchanged.
- Our own frozen chain already reads the shipped small-model scores, `numu_1_score`, `numu_score`, `cosmict_*`, `numu_cc_*` from `wc.T_tagger` for these files (`input_source_table_*.csv`), so the stored scalars exist.
- **Not yet established here:** presence of the 90 + 16 per-object lists in each of our samples (data and MC, both productions), and of every branch name above. This is a pure branch-name check.

### 4.4 Schema audit status
`scripts/upstream_schema_audit.py` (metadata only: `uproot` `keys()`, no array) compares `required_inputs.csv` with the branch lists of a few files per production x sample and writes `schema_audit_branches.csv` / `schema_audit_summary.json`. **It has not run**: this session has no Kerberos ticket (`klist: No credentials cache found`) so `htgettoken` cannot mint a bearer token. To run it: `kinit abhat@FNAL.GOV`, `htgettoken -a htvaultprod.fnal.gov -i sbnd --nooidc -o $BEARER_TOKEN_FILE`, then `python scripts/upstream_schema_audit.py --n-files 3`. Until it runs, "the CAFs contain all inputs" is an expectation, not a result.

### 4.5 Other compatibility points
- Candidate sets differ by design: nu_e scores candidates with `br_filled == 1` and `is_placeholder == 0`; nu_mu scores every non-placeholder candidate. The overlay carries one row per input candidate with a status code (`scored`, `tagger_not_run`, `placeholder`, `input_nan`); the overlay's identity set must equal our candidate table's after the same placeholder rule (to be reconciled on a fixture, 6.V5).
- A nu_e candidate with a NaN declared input would give `-16.2556` in the chain but is scored by xgboost's missing-value logic in the release scripts; the layer reports it as status `input_nan` and `to_chain_convention` maps both sentinels, so the two conventions can never be silently mixed.
- Stored (shipped-weight) upstream scores remain in the CAFs and in all our tables; regenerated scores live only in the overlay under new `up_*` names.

## 5. Proposed deployment and score-overlay mechanism (implemented, synthetic-tested)

Code: `src/sbnd_single_photon/upstream_scores.py`; config/pin `configs/upstream_release.yaml`; CLIs `scripts/upstream_release_audit.py`, `upstream_schema_audit.py`, `upstream_sample_inventory.py`, `upstream_integrity_manifest.py`, `upstream_overlay_build.py`, `upstream_bundle_check.py`; template `configs/frozen_bundle_manifest.template.yaml`.

Flow (nothing here has been executed on an official sample):
1. `upstream_release_audit.py <clone>` verifies the pin and all hashes (re-run before every use).
2. Candidate-input tables for an *authorised* sample are built with the **pinned release's own** `tables/build_tables.py --objs --file-id-from dirname`, so the inputs are exactly those the models were trained on (we do not write a second extractor that could differ).
3. `upstream_overlay_build.py` (guard checked first) scores nu_e on raw inputs and nu_mu on raw inputs (data) or on a **corrected copy** (simulation), carries `kine_reco_Enu` / `shw_sp_energy` as identity checks, translates the identity, and writes a **new, never-overwritten** parquet `overlay` plus a sidecar `*.provenance.json`.
4. Analysis code attaches the overlay with `join_overlay` (full-identity 1:1 join: raises on duplicates, missing rows, extra rows, or a differing check column) and builds SP inputs with `apply_to_sp_inputs` (replaces only the mapped upstream-score inputs; raw features asserted bit-identical; unscored candidates raise unless the convention is chosen explicitly).

Overlay columns: identity `(file_index, ev, run, subrun, evt, nu_index)`; nu_e `up_nue_score` (raw margin), 15 `up_nue_l1_<m>` (chain-stored values), 15 `up_nue_margin_l1_<m>`, `up_nue_n_nan_inputs`, `up_nue_status`; nu_mu `up_numu_margin`, `up_numu_score` (= margin x 2/ln 10), `up_numu_1_score`, `up_numu_2_score`, `up_cosmict_10_score`, `up_numu_status`; `id_*` identity checks. Mapping to the SP inputs (`sp_downstream_dependencies`): `numu_sp`: `numu_1_score`, `numu_score`; `ncpi0_sp`: the 15 small-model scores; `other_sp`: `cosmict_10_score`, `numu_1_score`, `numu_2_score`, `numu_score`; `nue_sp`: none.

Provenance sidecar: release repo and commit, both manifest hashes, models used, sample, production, tree, simulation flag, `numu_sim_dqdx_k_applied` (1.071 or null), `nue_inputs_corrected: false`, `data_corrected: false`, xgboost version, config hash, status codes, correction counts, authorisation status, overlay sha256, row count.

Guards implemented and tested: refuses any registered sample unless authorised or a designated fixture; refuses data correction; refuses double correction (corrected copies carry a marker column); refuses simulation nu_mu scoring on uncorrected inputs and data scoring on corrected inputs; refuses nu_e scoring on corrected copies; refuses duplicate or missing/extra rows in joins; refuses overwriting an overlay; refuses a tree other than `recTreeWireCell` and any production other than `nov16`; refuses a half-filled `evaluation_guard`.

## 6. Technical validation plan

| step | what | status |
|---|---|---|
| V0 | release pin, 57 hashes, manifest invariants | **done**, in `tests/test_upstream_scores.py` (skipped without a clone; the committed audit/hash tables are tested always) |
| V1 | our scoring == the release's standalone scripts (`release/score_release.py`, `make_corrected_tables.py --update-flag1`, `score_numu_release.py`) on synthetic tables incl. NaN/inf/flag edge cases; correction semantics by hand-computed cases | **done** (bit-identical final margins, level-1 values, corrected columns and flags; 16 tests) |
| V2 | metadata-only schema audit of every sample x production | **ready, blocked on credentials** |
| V3 | reader equivalence on a designated *non-evaluation* fixture: run the pinned builder + overlay on development CAFs and compare with the release scripts end to end | **needs Aurora**: no non-evaluation fixture exists on EAF (`fixtures: []`); Aurora can run the same CLI on its development files |
| V4 | reproduce the *stored shipped* scores from the CAF inputs with the shipped TMVA model (the release's `tools/tmva_grad_forest.py`) on the fixture, to prove the reader and the sentinel conventions | needs the fixture |
| V5 | identity reconciliation: overlay key set == our candidate table key set after the placeholder rule; `kine_reco_Enu`/`shw_sp_energy` checks equal | needs the fixture |
| V6 | integrity: `upstream_integrity_manifest.py --verify` before and after every overlay build | **recorded** (95 files, 0.27 GB); verify passes now |
| V7 | disjointness of the official samples from the upstream and Aurora training/dev sets by (run, subrun, event) lists | needs membership manifests (section 10) |
| V8 | rerun of the full package (efficiency, purity, topology purity, backgrounds, control regions, data/MC, Np/0p) with the final frozen configuration | **only after** the freeze and explicit authorisation |

## 7. Independent-evaluation safeguards

- `configs/upstream_release.yaml: evaluation_guard` (`authorized: false`; approver, date, frozen model bundle hash and selection manifest hash all empty) and `fixtures: []`; `require_authorization` is called before any file is read by `upstream_overlay_build.py`, refuses all six registered samples, and only a named person can fill the fields (tests pin the empty state; any change to it shows up in review).
- `tables/upstream_release/` holds metadata and provenance only; a test fails if any overlay or score table of an official sample appears in `tables/`.
- The data policy (`configs/data_policy.yaml`) is untouched: `beam_on_open` at preselection/sidebands only, signal region blocked, `run3bnb` blocked, beam-off shape/counts only.
- The informational cuts of the release (3.06, 0.985) are recorded but never applied by any code here; no model variant or threshold is chosen by EAF.
- Retrained SP BDTs are not touched: the bundle manifest validator checks structure only (it cannot authorise).
- Process rule: the first look at any official-sample result computed with new scores happens only after Avinay authorises it against a bundle whose hash is recorded in the guard.

## 8. Remaining dependencies (none is resolved by the upstream release)

| dependency | state | needed |
|---|---|---|
| Final effective detector-boundary treatment | expected in the ~Nov 23-onward production (non-box effective boundary; changes `match_isFC`, cosmic-tagger flags, angular/wall inputs of the nu_e and SP BDTs); the upstream models were trained on **Nov16 (box boundary)** | Haiwang: which production, when; Xuyang: do the models apply unchanged to it, or are they retrained? |
| Final vertex configuration | Nov16: DV2-MAX `aurora_space`, `dv2_split_move` default; a second `dv2_snap` tree exists; the release says nothing about snap | frozen vertex configuration in the bundle; statement of tree applicability |
| Beam-off provenance and approved normalization | scale unresolved (gate counters vs triggers; run overlap; no beam-off file in run 18255); **odd-run half is upstream training data** (572 odd / 486 even files in our manifest) | approved convention; Aurora/Xuyang training file list; evaluate with even-run files only |
| Detector and proton-reconstruction uncertainties | absent; no detector-variation samples known | Haiwang/Hanyu question 4 |
| `reinteractions_neutron_Geant4` weights | heavy tail (max 223,065); no approved SBN treatment; shown separately | Haiwang/Hanyu question 5 |
| Exposure-normalization conventions | POT from TotalPOT; `rec.mc.nu.imp_weight` (mean ~0.185 BNB CV) not applied, convention unknown; nuecc/ncdr filter conventions | question 2 |
| Truth-to-reco proton migration | WCL1116 improves it in MC but the data/MC Np/0p mismatch (~20 %) remains; new classifiers change which events are selected, so the migration and Np/0p study must be redone with final scores | repeat after the freeze |
| Exact training/evaluation sample disjointness | **not provable from the documents**: release says Fermilab samples were not used in training, but gives no event lists; Aurora samples are different productions; NC-Delta radiative Aurora events were training background; beam-off odd runs were training | membership manifests (section 10) |
| Upstream-stage independence | upstream defaults/cuts were chosen using the Fermilab evaluation samples and Run-3 beam-on data/prediction | accept and document, or have the final SP evaluation use only cuts frozen on Aurora |

## 9. Open questions (for Xuyang / Haiwang, in priority order)
1. Do the released models apply unchanged to the effective-boundary production? If not, what is retrained and from which date?
2. Event-level (run, subrun, event) membership of the Aurora BNB, nueCC-filtered, NC-Delta radiative and beam-off training/development samples; are any of these the same events as the official Fermilab files?
3. Were the models trained on `recTreeWireCell` (split-move) only? Are the scores meaningful on `recTreeWireCell_dv2snap`?
4. Which beam-off files (run list) formed the training half exactly (558 listed)?
5. What does the chain store for `<model>_score` of the 15 nu_e small models on candidates where the nu_e tagger did not run (`br_filled == 0`)? The retrained SP BDT must see the same convention.
6. Placeholder candidates: does the chain score them, and does Aurora's SP training drop them?

## 10. Checklist of artifacts needed from Aurora Claude before the final frozen-model evaluation

Validated structurally by `scripts/upstream_bundle_check.py` against `configs/frozen_bundle_manifest.template.yaml`:
- [ ] Frozen bundle manifest (filled template) with freeze timestamp and named owner, code repo and commit.
- [ ] The four retrained SP BDT model files (numu, other, ncpi0, nue) with sha256, xgboost version, ordered feature lists with sha256, score definition (margin/probability/transform, applied once), sentinel and non-finite policy, and the **frozen thresholds** (set before any official sample is touched).
- [ ] The exact mapping of upstream-score inputs to overlay columns, and the list of raw reconstruction features used (so the guard that raw features stay raw can be checked).
- [ ] Selection manifest (file + sha256): candidate policy, fiducial volume, signal and topology definitions, denominator.
- [ ] Production and tree: WCL production name and toolkit commit, `wc_tree` (must be `recTreeWireCell` unless Xuyang extends the verification), vertex configuration (DL bundle sha256), effective-boundary treatment, and a written applicability statement from Xuyang for that production.
- [ ] Upstream pins confirmed identical to `configs/upstream_release.yaml` (commit, both manifest hashes, `k = 1.071`).
- [ ] Training/validation membership: file lists with sha256 and (run, subrun, event) lists for every Aurora sample and split, the beam-off half used, the split rule, the nested-validation report. These make V7 computable.
- [ ] Confirmation that no official FermiGrid sample entered training, tuning, threshold choice or model selection of the SP BDTs (`validation.no_official_sample_used: true`).
- [ ] A non-evaluation development fixture (a few hundred CAFs of Aurora development data) registered by name for V3-V5, with the Aurora-side results of running the same overlay CLI on it.
- [ ] Aurora-side result of V1 on its tables with the same pinned release (agreement with this repository's scoring).
- [ ] Beam-off: the file list actually used for training, so the EAF evaluation uses the complementary even-run files.

## 11. Repository artifacts of this work
`configs/upstream_release.yaml`, `configs/frozen_bundle_manifest.template.yaml`, `src/sbnd_single_photon/upstream_scores.py`, `scripts/upstream_{release_audit,schema_audit,sample_inventory,integrity_manifest,overlay_build,bundle_check}.py`, `tests/test_upstream_scores.py` (16 tests), `tables/upstream_release/{release_file_hashes.csv, release_audit.json, required_inputs.csv, sample_applicability.csv, baseline_artifact_hashes.csv}`. The release clone used for the audit is outside the repository (`/home/abhat/Single-photon/upstream_audit/sbnd-wirecell-bdt`, HEAD `0f13988`); tests that need it skip when it is absent (`SP_UPSTREAM_CLONE`).
