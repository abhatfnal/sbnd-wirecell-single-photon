# Upstream νμ / νe release integration for the SP BDTs: audit and handoff (Aurora, DEVELOPMENT)

Date: 2026-11-28. Branch `round2/sp-bdt-wcl1116-upstream-r4-integration-20261128` (from `916037a`). Author: Avinay Bhat
(prepared with Claude Code).

**Scope.** Integrate Xuyang Ning's released upstream Wire-Cell CC classifiers into the NC Δ single-photon (SP) BDT
development pipeline:
- νe `nue_round4_ruleA_v2` (main chain variant) and νμ `numu_round3af`, both trained on WCLocal2026Nov16 / WCT 0.38.0;
- without reprocessing the Aurora reconstruction campaign.

**Rules followed:**
- Every number is Aurora **training-side DEVELOPMENT** (FIT / nested validation / existing holdout).
- **No FermiGrid evaluation sample was opened.** Nothing was tuned on, or evaluated with, the official evaluation
  samples.
- **No model, threshold or vertex mode is frozen.** Xuyang's CC working points are not used as SP thresholds.
- No large production was launched. Only copies of 18 production units were re-run through step 2.
- Nothing in Haiwang's or Xuyang's directories was modified; nobody was contacted.

## 0. Summary

1. **Release audited and pinned.** Commit `0f13988d`; **61/61 model files match their manifests**. The two families are
   independent: the νe final model reads no νμ output and vice versa.
2. **Exact downstream footprint.**
   - SP numu reads `numu_1_score` and `numu_score`.
   - SP other reads all four νμ outputs (`numu_1/2_score`, `cosmict_10_score`, `numu_score`).
   - SP ncpi0 reads **all 15 νe level-1 scores** (not `nue_score`).
   - SP nue reads none.
   - Replacing only `numu_score` / `nue_score` would be wrong. The stored raw cosmic-tagger dQ/dx and `numu_cc_flag`
     do not change: the correction acts only on the copies handed to the νμ BDT.
3. **Offline re-scoring is sufficient. No reconstruction is needed for development.**
   - Every input is stored, for every candidate of NC Δ (24,031), BNB (301,830), νe CC (265,367) and the beam-off
     training half (2,495), in **both** vertex trees.
   - Our extraction is identical to Xuyang's builder.
   - The shipped final models reproduce the stored `numu_score` and `nue_score` **bit for bit on all 593,723
     candidates** per tree.
   - Xuyang's official scorers, run unmodified, agree with our toolkit emulation: level-1 values to float32 rounding;
     final scores to the documented last-bit split crossings, with the same maxima as his own XML checks.
4. **Simulation-only correction verified.**
   - ×1.071 is applied to the seven dQ/dx inputs on the three simulated samples only, never to beam-off, never to the
     νe model, never to an SP input.
   - The `numu_cc_flag` copy is identical to the official `--update-flag1` on all 1.18 M simulated candidates.
   - Without the correction, 9,040 BNB candidates would cross 0.985; Xuyang finds 9,049.
5. **In-chain validation passed** (§7). The patched toolkit, built in our area from `c935e30d` + Xuyang's patch,
   re-ran step 2 (both passes) on copies of 18 production units (7 NC Δ, 4 BNB, 7 νe CC; 128 candidates per tree):
   - shipped weights: **identical to production** except the version stamp;
   - released weights + ×1.071: only the 20 upstream outputs change, and they equal the offline emulation **bit for
     bit**;
   - data gate: the factor is ignored with `reality=data` even when the variable is set;
   - the SP feature vectors and SP predictions from the in-chain CAFs equal the overlay's exactly;
   - the shipped level-1 models also close bit for bit with ROOT TMVA on all 593,723 candidates.
6. **Downstream impact** (§8, nested validation):
   - The new upstream values break the inherited chain: joint 27.1 % → 2.8 % NC Δ in domain D. They also degrade the
     current development models applied unchanged (44.0 % → 35.1 %).
   - **After retraining in the new domain, the joint selection front changes by −0.5 to +2 points** (D: 48.7 % vs 48.0 %
     at BNB ≤ 0.78 %). Per-model AUC: SP numu 0.979 → 0.980, SP other 0.916 → 0.919, SP ncpi0 0.893 → 0.894.
7. **Reuse:** the existing production is reusable for development through checked overlays. The final domain needs a
   new production for other reasons (boundary, vertex, beam-off), which should book the releases.
8. **New integration issues found:**
   - a patched toolkit stamps a new `wct_version` (`numu-sim-dqdx-scale-0.38.0-1-gccb19cf` here);
   - the Aurora step-2 patch forwards the factor regardless of reality, so data safety rests on the jsonnet gate;
   - the upstream models were trained on the same Aurora samples (all rows of their pools except a ~10 % development
     slice);
   - SP inputs based on dQ/dx remain uncorrected on simulation (data/MC systematic).

## 1. Release, commit and checksums

| item | value |
|---|---|
| repository | `https://github.com/Ningclover/sbnd-wirecell-bdt` (public; cloned read-only to `$SP_WORK/upstream_release_audit/sbnd-wirecell-bdt`) |
| commit pinned | **`0f13988db44423a227789e151b0a374e25771abd`** (2026-11-24, merge of PR #9 "releases/README: current defaults") |
| νμ release | **`numu_round3af`** (released 2026-11-23T19:03Z): numu_1, numu_2, cosmict_10 **and** the final model retrained; simulation dQ/dx × 1.071 + numu_1 muon-flag update |
| νe release | **`nue_round4_ruleA_v2`**, variant **main** (frozen 2026-11-19T23:24Z; default decided 2026-11-20): the 15 level-1 models (rule A, byte-identical to v1) + a final model retrained on the chain-stored level-1 values (258 inputs, 116 trees) |
| reconstruction they were trained on | WCLocal2026Nov16 (WCT 0.38.0, `c935e30d`) — the same production as our WCL1116 development domain |
| model files verified | **61 / 61 sha256 match their manifests** (νe: 15 level-1 JSON, 2 level-2 JSON, 32 chain XML in `main` + `nogap`; νμ: 3 level-1 JSON, 1 final JSON, 4 chain XML, 4 `chain_weights.json` entries); no unlisted model file. `validation/upstream_r4/upstream_release_checksums.json` |
| chain XML used (main) | `XGB_nue_seed2_0923.xml` `9912f6f2…`, 15 `<model>_BDT.weights.xml` (e.g. `br3_3` `418ad381…`); `numu_tagger1` `1af283dd…`, `numu_tagger2` `a129aaad…`, `cos_tagger_10` `8405c13c…`, `numu_scalars_scores_0923.xml` `81fb26f8…` |
| correction | `correction.json` `2e9b7eef…` = `{"mode": "uniform", "k": 1.071}`; the seven inputs `numu_cc_1_medium_dQ_dx`, `cosmict_{2,3,7}_dQ_dx_{end,front}`; simulation only; finite values > 0 only; `--update-flag1` |
| patches | `wct-0.38.0-numu_sim_dqdx_scale.patch` `3162b22f…` (5 files, +45/−5); `step2-numu_sim_dqdx_scale.patch` `bc83b90b…` (Aurora workflow, 2 files) |
| Xuyang's operating points (context only, never used here) | νe `nue_score > 3.06` (82 % purity), νμ `numu_score > 0.985` (95 % purity), both from his Fermilab evaluation |

**Upstream CC BDTs are not our SP BDTs.** Xuyang's νμ tagger (`numu_score`; level-1 `numu_1/2_score`,
`cosmict_10_score`) and νe tagger (`nue_score`; 15 level-1 scores) are upstream Wire-Cell classifiers. Our four SP BDTs
(`single_photon_numu`, `_other`, `_ncpi0`, `_nue`) are downstream: they **read** some upstream outputs as inputs. Xuyang's
CC working points are not SP thresholds and are never substituted for them.

## 2. Current Aurora production and training state (preserved, not modified)

| item | state |
|---|---|
| repository / branch | `abhatfnal/sbnd-wirecell-single-photon`; this work on **`round2/sp-bdt-wcl1116-upstream-r4-integration-20261128`**, branched from `round2/sp-bdt-wcl1116-full-development-20261120` @ `916037a` (= origin) |
| baseline preserved | the WCL1116 four-model development (`92a1b17`) and the full-development studies (`179cc58` … `916037a`): models, scores, nested split, operating points and figures are untouched. The joint reference **27.1 → 44.0 % NC Δ, 0.75 → 0.78 % BNB** (split-move, nested validation) is re-derived bit for bit as domain A below |
| reconstruction | WCLocal2026Nov16-Aurora: WCT 0.38.0 `c935e30d`, wire-cell-data `99c6497f`, DL bundle `dv2max/sbnd/aurora_space` (`51588842…`); two trees per CAF: `recTreeWireCell` (dv2_split_move), `recTreeWireCell_dv2snap` |
| upstream weights booked in that production | the **shipped MicroBooNE** files (`numu_scalars_scores_0923.xml` `426e670c…`, `XGB_nue_seed2_0923.xml` `6199d202…`, the 4 νμ and 15 νe level-1 XMLs) |
| development samples (training side only) | NC Δ 17,604 files / 24,031 candidates; BNB 11,874 / 301,830; νe CC 61,238 / 265,367; beam-off odd-run training half 558 files / 2,495 candidates (verified 558/558, stamp `HEAD-0.38.0` = same toolkit) |
| raw tables | `$SP_WORK/wcl1116_dev_tables/{dv2_split_move,dv2_snap}/` (immutable; this work only reads them) |
| split | outer: MC odd subrun / EXT run % 4 == 1 = existing development holdout; inner: `nested_v1` (20 % of training-side units) |
| policy | Aurora = development and training; FermiGrid = independent evaluation, **never opened** here (`AURORA_UMBRELLA_MODEL_TRAINING_AND_EVALUATION_POLICY.md`) |
| new work area | `$SP_WORK/upstream_r4_20261128/` (`tables/`, `equiv/`, `rescore/`, `official/`, `overlay/`, `domain/`, `chain/`, `l1_tmva/`) |

## 3. Upstream-to-downstream dependency matrix

Generated from the code of record (`tools/upstream_dependency_matrix.py`; per-input CSV
`validation/upstream_r4/sp_upstream_dependency_matrix.csv`, summary `.json`).

| SP model (inputs) | replaced by νμ round3af | replaced by νe A v2 | raw upstream-tagger inputs (stored values unchanged) | unaffected |
|---|---|---|---|---:|
| SP numu (73) | `numu_1_score`, `numu_score` | — | 8 raw νμ-final inputs (`numu_cc_flag_3`, `numu_cc_3_*`) | 63 |
| SP other (146) | `cosmict_10_score`, `numu_1_score`, `numu_2_score`, `numu_score` | — | 60 raw νμ-final inputs (cosmic taggers, `numu_cc_flag`); 6 of them (`cosmict_{2,3,7}_dQ_dx_{end,front}`) are scaled ×1.071 **only inside the copy handed to the νμ BDT** | 82 |
| SP ncpi0 (45) | — | **all 15 level-1 scores** (`br3_3 … tro_5`) | — | 30 |
| SP nue (56) | — | — | — | 56 |

Upstream structure (toolkit c935e30d):
- **νμ final** (74 inputs) ← `numu_1_score` (max over numu_cc_1 segments, empty −0.4), `numu_2_score` (max, −0.1),
  `cosmict_10_score` (min, 0.7) + 71 raw tagger values; NaN → 0 on four angles; `numu_score = log10((1+v)/(1−v))`.
  `numu_tagger3` is not retrained and feeds neither the νμ final model nor any SP model.
- **νe final** (258 inputs) ← the 15 level-1 scores + 243 raw values. It reads **no νμ output**, and the νμ final model
  reads no νe output: the two families are independent, so domains B and C compose into D without interaction.
- **νe level-1** (15 models): min over the model's objects; empty constant per model; `pio_2` only when
  `pio_filled == 1 && pio_flag_pio == 0`. **No `br_filled` gate** on the level-1 models (only the νe final model is
  gated: `nue_score = −15` when `br_filled != 1`).
- Not sufficient to replace only `numu_score` / `nue_score`: SP other reads all four νμ outputs; SP numu reads
  `numu_1_score`; SP ncpi0 reads all 15 νe level-1 scores and **not** `nue_score`.

## 4. Raw-input availability and missing-input audit (per sample, both vertex trees)

Every input of Xuyang's standalone scorers and of the chain emulation is stored in the WCL1116 merged CAFs, in **both**
Wire-Cell trees:
- the 74 νμ-final and 258 νe-final scalars, the gates (`br_filled`, `pio_filled`, `pio_flag_pio`, `cosmict_N_filled`,
  `numu_cc_flag_3`) and `kine_reco_Enu`;
- the per-object lists of all 18 level-1 models (numu_1, numu_2, cosmict_10, the 15 νe models) with their `..idx` /
  `..length` and rule flags;
- the stored shipped scores.

Audited on **every file** (`tools/extract_upstream_inputs.py` records missing branches per file):

| sample (training side) | files | candidates | file errors | files missing a scalar / a model list | NaN `kine_reco_Enu` / `numu_score` | `br_filled == 1` (all / SP-preselected) |
|---|---:|---:|---:|---:|---:|---|
| NC Δ radiative | 17,604 | 24,031 | 0 | 0 / 0 | 0 / 0 | 26.3 % / 38.8 % |
| generic BNB | 11,874 | 301,830 | 0 | 0 / 0 | 0 / 0 | 6.8 % / 31.0 % |
| dedicated νe CC | 61,238 | 265,367 | 0 | 0 / 0 | 0 / 0 | 72.0 % / 86.6 % |
| beam-off odd-run training half | 558 | 2,495 | 0 | 0 / 0 | 0 / 0 | 5.1 % / 24.8 % |

- Identical counts in `recTreeWireCell` (split-move) and `recTreeWireCell_dv2snap`; the candidate counts equal the SP
  development tables exactly, so every SP row has its upstream inputs.
- Stamps: `0.38.0` (Aurora) and `HEAD-0.38.0` (beam-off half, same toolkit `c935e30d`, approved policy).
- **Extraction equals Xuyang's builder:** `IDENTICAL` on the first 300 files of every sample in both trees (359 shared
  candidate columns and every object column; for snap, his builder run unmodified with only the tree name set).
- **No νe level-1 object exists when `br_filled != 1`** (checked on all candidates): those rows keep the empty constants
  under the shipped and the released weights alike. The official νe scorer's `br_filled == 1` restriction therefore loses
  nothing for SP ncpi0 in WCL1116; the chain emulation still scores every candidate and confirms it.
- NaN inputs: no NaN-input level-1 object anywhere (no −999 level-1 value). **One** NaN νe-final input in the whole
  development set: `pio_1_mass` of one BNB candidate (`run 2110679 subrun 85 event 2`, split-move). The chain stores
  `nue_score = −16.2556` there, with the shipped and the released files alike; the XGBoost scorer returns 0.245.
  `nue_score` is not an SP input.
- **Beam-off:** the merged CAFs on Aurora are complete for offline re-scoring. No beam-off step-1 output exists on
  Aurora, so no beam-off in-chain rerun is possible here (§7).

## 5. Offline scoring: implementation and provenance

Two independent routes on the same per-object inputs, so that each checks the other.

**(a) Xuyang's official standalone scorers, run unmodified** (commit `0f13988d`):
1. `tools/extract_upstream_inputs.py` writes, for either Wire-Cell tree, the inputs of the upstream taggers in Xuyang's
   table schema (`cands_<sample>.parquet`, `objs_<model>_<sample>.parquet`). Same key, same rules as his
   `tables/build_tables.py`. His builder reads only `recTreeWireCell`, so the snap tree needs this extractor. Equivalence
   is checked against his builder (unmodified except for the tree name) on the first 300 files of every sample in both
   trees (`tools/check_upstream_extract_vs_builder.py`).
2. νμ: `training/numu/make_corrected_tables.py MERGED CORRECTED releases/numu_round3af/correction.json --samples
   wcl1116-aurora-ncdr wcl1116-aurora-bnb wcl1116-aurora-nuecc --update-flag1` (the three **simulated** samples only;
   the beam-off training half is scored from the uncorrected tables), then
   `training/numu/score_numu_release.py releases/numu_round3af <tables> <sample> OUT` (`d6_f0` = margin;
   `numu_score = 0.868589 × d6_f0`).
3. νe: `release/score_release.py releases/nue_round4_ruleA_v2 <tables> <sample>` (variant `main`: level-1 values
   chain-transformed, empty constants, final raw margin). **It scores only `is_placeholder == 0 && br_filled == 1`.**

**(b) Chain emulation** (`sp_retrain/upstream_chain.py`, driven by `tools/upstream_rescore.py`): the toolkit-0.38.0 C++
(`UbooneNumuBDTScorer`, `UbooneNueBDTScorer`, `TmvaGradForest`, and the patch), evaluating the **released TMVA XML chain
files** exactly as the chain does:
- inputs and node cuts in float32; any NaN input gives −999;
- `float32` pooling (max for numu_1/2, min for cosmict_10 and the 15 νe models), the toolkit's empty constants;
- `pio_2` gate; no `br_filled` gate on the level-1 models;
- numu_1 `dQ_dx_cut` ±inf → 10, cosmict_10 `angle_beam` NaN → 0;
- the simulation scale applied as `float32(double(q) × 1.071)` to finite q > 0, in the BDT copies only, and the
  numu_cc_flag copy rule;
- NaN → 0 on four νμ-final angles;
- `log10((1+v)/(1−v))` with the toolkit's saturation;
- `nue_score = −15` when `br_filled != 1`.
Files are resolved `WIRECELL_PATH`-style: release folder first, shipped folder after, as README step 3 sets up the chain.
Every weight file's path and sha256 is recorded in each output.

**Why both:** route (a) is the reference implementation but evaluates the XGBoost JSON files, covers only the νe
`br_filled == 1` candidates, and assigns NaN inputs XGBoost's learned default direction. A genuine production runs the
TMVA XML files on every candidate, and the chain returns −999 for a NaN input. Route (b) is what a genuine production
would store; route (a) cross-checks it wherever both are defined.

**Joins and overlays.**
- The raw tables (`$SP_WORK/wcl1116_dev_tables/<mode>/`) are never modified.
- `tools/build_upstream_overlay.py` joins the re-scored candidates to the development tables on the full key
  (`sample, file_id, run, subrun, event, cand`). It requires the key to be unique on both sides, every development row to
  be matched, and the 21 stored upstream values (the 19 SP inputs, `numu_3_score` and `nue_score`) to be float32-identical
  between the two sides. It then writes one overlay per sample: stored copies, new values, the `numu_cc_flag` BDT copy,
  diagnostic unscaled νμ values, and Xuyang's `split_v11` role.
- `sp_retrain/upstream_overlay.apply()` replaces only the domain's columns, and re-checks the stored values row by row
  every time an overlay is applied.

### 5.1 Results of the offline route (all candidates, both trees)

Evidence: `validation/upstream_r4/offline_rescoring_summary.json`; verdict **OFFLINE_INPUTS_SUFFICIENT_AND_CLOSED**.

**Closure on the production's own values.** The shipped final models, fed the stored level-1 values, reproduce the
stored `numu_score` **and** `nue_score` **bit for bit on every candidate** of every sample, in both trees:
NC Δ 24,031, BNB 301,830, νe CC 265,367 and beam-off 2,495. This includes placeholders, the `br_filled = 0` rows
(`nue_score = −15`) and the one NaN-input candidate. Every scalar input and both final-score conventions are therefore
reproduced. The shipped level-1 models are TMVA AdaBoost with input transformations; they are closed separately with
ROOT TMVA (§7.4).

**Official standalone vs chain emulation** (same tables; the official scorers unmodified):

| sample | mode | candidates | νμ level-1 max \|Δ\| | `numu_score` max \|Δ\| (rows > 1e-5) | pass/fail at 0.985 differs | νe level-1 max \|Δ\| (rows) | `nue_score` max \|Δ\| | pass/fail at 3.06 differs |
|---|---|---:|---:|---|---:|---|---:|---:|
| NC Δ | split | 24,031 | 5.5e-7 | 0.235 (454) | 0 of 1,501 | 6.0e-7 (6,310) | 0.244 | 0 of 256 |
| BNB | split | 301,830 | 5.5e-7 | 0.307 (4,089) | 4 of 171,315 | 6.9e-7 (20,414) | 16.5 (one NaN-input row; else ≤ 0.35) | 0 of 835 |
| νe CC | split | 265,367 | 6.6e-7 | 0.338 (2,585) | 2 of 34,222 | 7.5e-7 (190,945) | 0.334 | 19 of 137,287 |
| beam-off | split | 2,495 | 5.5e-7 | 0.130 (45) | 0 of 140 | 5.1e-7 (126) | 0.126 | 0 of 3 |
| NC Δ | snap | 24,031 | 5.5e-7 | 0.190 (490) | 1 of 1,446 | 6.6e-7 (6,142) | 0.244 | 0 of 289 |
| BNB | snap | 301,830 | 5.5e-7 | 0.307 (4,257) | 5 of 168,227 | 6.9e-7 (20,102) | 0.354 | 0 of 843 |
| νe CC | snap | 265,367 | 7.2e-7 | 0.422 (2,530) | 8 of 33,519 | 6.9e-7 (189,004) | 0.398 | 18 of 127,634 |
| beam-off | snap | 2,495 | 5.5e-7 | 0.130 (51) | 0 of 156 | 6.9e-7 (114) | 0.126 | 0 of 2 |

- **Level-1 values agree to float32 rounding (≤ 7.5e-7) everywhere.**
- The final scores differ on about 1 % of candidates, by up to 0.3–0.4. A last-bit difference in a level-1 value, or
  in a leaf written to XML, can cross a split of the deep final model. This is the effect Xuyang documents; his own
  XML-vs-XGBoost checks give the same maxima (BNB 0.3069 with 4 pass/fail changes, NC Δ 0.2350, beam-off 0.1298).
  Our emulator reproduces those numbers independently, so it evaluates the XML files exactly as his independent TMVA
  evaluator does.
- Production stores the **XML** result; the overlay therefore uses the chain emulation, not the XGBoost value.
- Single largest disagreement: the one NaN `pio_1_mass` candidate (`nue_score` −16.2556 in the chain, 0.245 in XGBoost;
  §4).

## 6. Simulation-only correction and flag handling

**Rule (release manifest, toolkit patch):**
- q → float32(double(q) × 1.071) on the seven dQ/dx inputs, only where q is finite and > 0;
- the six `cosmict_{2,3,7}` values only where `cosmict_N_filled == 1`;
- simulation only.

The `numu_cc_flag` copy handed to the νμ final model becomes 0 when:
- some numu_1 segment had `numu_cc_flag_1 == 1`, and
- none keeps it with the scaled dQ/dx below its `numu_cc_1_dQ_dx_cut`, and
- no `numu_cc_2` object has its flag set, and
- `numu_cc_flag_3 != 1`.

The **stored** `cosmict_*` dQ/dx and `numu_cc_flag` stay raw, so no SP input other than the four νμ scores changes.

**Verified:**
- Code identity: the emulator's rule is a line-by-line transcription of the patch (`UbooneNumuBDTScorer.cxx` hunk
  @@ −577), and the official `make_corrected_tables.py --update-flag1` implements the same rule on tables.
- Unit tests (`tests/test_upstream_r4.py`): the scale touches only finite positive values and only filled taggers; the
  four flag cases (kept, lost, rescued by numu_cc_2, rescued by flag_3); scale 1 (data) changes nothing; the stored
  columns are never modified.
- **Simulated samples only:** the official correction was run with `--samples wcl1116-aurora-ncdr wcl1116-aurora-bnb
  wcl1116-aurora-nuecc`. The beam-off training half was scored from uncorrected tables, and `upstream_rescore.py
  --kind data` forces the scale to 1.
- **Not applied** to the νe classifier (the νe scorer is not patched, and the emulator never passes the scale to it),
  nor to any SP input (the overlay replaces only the four νμ scores and the 15 νe level-1 scores).
- In the chain: the patch forwards the factor only when `reality == 'sim'` (`cfg/pgrapher/experiment/sbnd/clus.jsonnet`).
  The Aurora step-2 patch forwards `NUMU_SIM_DQDX_SCALE` whenever the variable is set, **regardless of the unit's
  reality**; data protection therefore rests on the jsonnet gate, which the in-chain gate test exercises (§7).

**Measured on the development samples (offline, both trees; `offline_rescoring_summary.json`):**

| sample | `numu_cc_1_medium_dQ_dx` values corrected (split / snap) | candidates whose `numu_cc_flag` copy switches off (split / snap) | flag copy vs official `--update-flag1`, candidate by candidate |
|---|---:|---:|---:|
| NC Δ | 29,540 / 29,132 | 151 / 154 | 0 mismatches |
| BNB | 526,026 / 518,217 | 1,639 / 1,816 | 0 mismatches |
| νe CC | 554,648 / 551,171 | 2,127 / 2,222 | 0 mismatches |
| beam-off (data) | 0 (not corrected) | 0 | — |

The median correction factor is exactly 1.071 on every corrected column.

**Size of the correction** (split-move overlays: the corrected values against `diag_noscale_*`, which is what an
unpatched chain would store):

| sample | candidates whose `numu_score` changes | max \|Δ\| (p95) | crossing 0.985 |
|---|---:|---|---:|
| NC Δ | 63 % | 3.82 (0.50) | 208 |
| BNB | 84 % | 4.65 (1.70) | **9,040** |
| νe CC | 68 % | 4.38 (0.55) | 7,132 |

The BNB number reproduces Xuyang's independent figure: 9,049 of his 302,172 BNB candidates cross the cut without the
correction. A chain run with the released νμ weights but **without** the patch would feed SP numu / SP other visibly
different inputs from what the release intends.

## 7. Offline versus genuine in-chain parity

### 7.1 Compatibility with our WCL1116 toolkit and workflow (checked before applying anything)

| item | WCL1116 production | patch base | result |
|---|---|---|---|
| toolkit | `yuhw/wct-0.38.0` = `c935e30d` (tag 0.38.0), clean worktree | 0.38.0 `c935e30d` | `wct-0.38.0-numu_sim_dqdx_scale.patch` applies cleanly (`git apply --check`, `git am`): 5 files, +45/−5 |
| Aurora workflow | `yuhw/swp-wclocal` = `sbnd-wirecell-production` branch `wclocal-nov16` @ `d05cf47`; `aurora/bin/step2.sh` blob `35729618…`, `aurora/site/aurora.sh` blob `aa19f58f…` | the patch's `index 3572961..` / `aa19f58..` lines | identical blobs; `step2-numu_sim_dqdx_scale.patch` applies cleanly |
| wire-cell-data | `yuhw/wcd-0.38.0` = `99c6497f` (`uboone/weights` identical to the main data checkout) | release folders go **in front** on `WIRECELL_PATH` | no file of wire-cell-data is replaced |

Neither patch was applied in any of Haiwang's or Xuyang's directories. Both were applied to **our own clones**:
- toolkit: `$SP_WORK/upstream_r4_20261128/chain/wct-0.38.0-numu-sim`, branch `numu-sim-dqdx-scale` @ `ccb19cf` =
  `c935e30d` + the patch;
- workflow: `.../chain/swp-wclocal-numu`, branch `numu-sim-dqdx-scale` @ `eaaa02f` = `d05cf47` + the step-2 patch.

The toolkit was built into our own prefix (`.../chain/opt-0.38.0-numu-sim`) with Haiwang's recipe: same container,
configure script and `waf -k`.

### 7.2 Design of the small matched test

- **Input:** copies of WCLocal2026Nov16 production units, reusing their kept step-1 tars (`ql/<tag>/qlpctree.tar.gz`).
- **Run:** step 2 (both passes, split-move and snap), merge and validation, rerun with the production settings
  (`WC_STEP2_PASSES`, DV2 bundle, `WC_STEP1_SEEDED=1`, `WC_KEEP=semiprod`).
- **Arms:**

| arm | toolkit | weights | `NUMU_SIM_DQDX_SCALE` | purpose |
|---|---|---|---|---|
| prodbuild | Haiwang's `opt-0.38.0` + original cfg | shipped | unset | determinism of a rerun |
| ctl | ours (patched) | shipped | unset | patch is default-off; our build = production |
| **new** | ours (patched) | **released νμ + νe** | **1.071** (simulation) | the genuine new production |
| noscale | ours (patched) | released | unset | what an unpatched chain would store |
| gate | ours (patched) | released | 1.071 set, unit run as `reality=data` | the data gate |

- **Units:**
  - pre-registered hash rule: `sha256("upstream_r4_chain_test|<sample>|<unit>")` ascending, the first complete units;
  - plus targeted units chosen from the offline re-scoring (a `numu_cc_flag` copy switched off);
  - `tools/pick_chain_test_units.py`, `units.tsv` in the work area.
- **Comparisons:**
  - every branch of `recTree`, `recTreeWireCell` and `recTreeWireCell_dv2snap` against the production merged CAF
    (`tools/compare_chain_test.py`);
  - the chain-stored upstream scores against the emulation of the same inputs (`tools/compare_chain_scores.py`).
- **Beam-off:** no permitted data step-1 output exists on Aurora. The only data tars here are `selected-r2` beam-on
  events, which are excluded by the firewall and were not used. The data path is therefore tested by the gate arm.

### 7.3 Results (PBS 9137793; `validation/upstream_r4/chain_test_summary.json`)

**Build.**
- Our clone `ccb19cf` (= `c935e30d` + patch) was built with `waf -k` (rc 0, 3 min 51 s on 96 cores).
- Same library set as Haiwang's `opt-0.38.0`; the patched symbol is present.
- **Configured version: `numu-sim-dqdx-scale-0.38.0-1-gccb19cf`.** The toolkit derives the stamp from the git checkout,
  so a patched production stores a new `wct_version`.

**Environment proof inside the container** (README step 5.2):
- `ctl` and `new` ran our `wire-cell`.
- `new` resolved every released file first: `XGB_nue_seed2_0923.xml` `9912f6f2…`, `br3_3` `418ad381…`, `tro_5`
  `f071db76…`, `numu_scalars_scores_0923.xml` `81fb26f8…`, `numu_tagger1` `1af283dd…`, `cos_tagger_10` `8405c13c…`.
- `numu_tagger3` fell back to the shipped file (`fda35809…`).
- `ctl` and `prodbuild` resolved only shipped files.

**Units.** 18 production units, all `OK` in every arm:
- 7 NC Δ, 4 BNB, 7 νe CC;
- 15 picked by the pre-registered hash rule, plus 3 targeted units where the correction switches the `numu_cc_flag`
  copy off;
- 128 candidates per tree; both passes (split-move and snap) and the merge rerun.

| check | result |
|---|---|
| `prodbuild` vs production (Haiwang's build, shipped weights) | **every branch identical** in `recTree`, `recTreeWireCell`, `recTreeWireCell_dv2snap` (2 units): a step-2 rerun is deterministic |
| `ctl` vs production (our patched build, shipped weights, factor unset) | **every branch identical except `wc.Trun.wct_version`** (18 units, both trees): the patch is default-off, and our build reproduces production |
| `new` vs production | differing branches = exactly the **20 upstream outputs** (4 νμ scores, 15 νe level-1, `nue_score`) + `wct_version`. Every raw tagger value, the stored `numu_cc_flag`, every `shw_sp_*` / `kine_*` input and the vertex are identical |
| `new`: chain-stored vs offline emulation of the same inputs | **bit for bit**, max \|Δ\| = 0 on all 20 outputs, 128 / 128 candidates in each tree (NC Δ 10, BNB 86, νe CC 32). This includes the ×1.071 scale and the flag copy on the targeted units |
| `noscale` (released weights, factor unset) | bit for bit against the unscaled emulation (20 candidates per tree) |
| **`gate`** (released weights, `NUMU_SIM_DQDX_SCALE=1.071` set, unit run as `reality=data`) | the chain stored exactly the **unscaled** emulation; the scale log line is absent. The jsonnet gate blocks the factor on data even when the variable is set. (`reality=data` on a simulation input also changes 214 other branches, such as truth matching and flash/cluster association, as expected; the gate check uses only the scores of its own inputs) |
| scale log line `UbooneNumuBDTScorer: simulation dQ/dx scale 1.071 …` | `new` 36 / 36 step-2 logs; `noscale` 0 / 6, `gate` 0 / 2, `ctl` 0 / 36, `prodbuild` 0 / 4 |
| shipped final-model closure on the `ctl` / `prodbuild` outputs | exact |
| **SP level** (`new` CAFs vs production tables + domain-D overlay, same candidates) | SP feature vectors **identical** for all four SP models (128 / 128, both trees). Predictions identical (max \|Δ\| = 0) for the domain-D retrained development models, for the domain-A models and for the inherited XMLs; no pass/fail change |

**Conclusion:** for the simulated development samples (NC Δ, BNB, νe CC), the offline domain-D overlay **is** the genuine
in-chain result. The beam-off half is covered by the offline route (scale forced to 1) and the data-gate test. The
releases change nothing but the upstream scores. The data path never receives the factor. The only production-visible
side effect is the toolkit version stamp.

### 7.4 Level-1 closure with ROOT TMVA itself (all candidates)

`tools/upstream_l1_tmva_closure.py` + `cpp/upstream_l1_tmva_eval.cxx`, built and run in the SL7 container (ROOT 6.28/12,
the production's `TMVA::Reader`), on every object of the four development samples (dv2_split_move). Result
`validation/upstream_r4/l1_tmva_closure_dv2_split_move.json`: **CLOSED / AGREE**.

- **Shipped level-1 models** (TMVA AdaBoost with `VarTransform=D,P,U,G,D,N`; not reproducible in numpy): evaluated by
  ROOT, then pooled with the chain's rules (float32, max/min, empty constants, `pio_2` gate).
  - Reproduces the stored value **exactly on 593,723 / 593,723 candidates for all 18 models**: numu_1, numu_2,
    cosmict_10 and the 15 νe models.
  - That is 25.8 M objects, including 12.1 M `pio_2` objects, the empty lists and the `br_filled == 0` rows.
  - So the extracted per-object inputs, their order, the protections, the gate and the pooling and empty conventions are
    exactly what the chain used.
- **Released chain XMLs:** `TMVA::Reader` equals the numpy chain emulator **bit for bit (float32) on every object of
  every model**. The emulator's arithmetic is the production arithmetic.
- No NaN-input object anywhere (0 values of −999).

Combined with §5.1 (final models closed bit for bit with the stored level-1 inputs), the offline route reproduces every
upstream output the WCL1116 chain stored, exactly. The released models evaluated offline are therefore what the chain
computes from the same inputs. The one remaining in-chain element, the simulation scale and flag copy inside
`UbooneNumuBDTScorer`, is the subject of §7.3.

## 8. Impact on the downstream SP feature vectors and scores (DEVELOPMENT ONLY)

`tools/upstream_domain_study.py` → `validation/upstream_r4/upstream_domain_study_{dv2_split_move,dv2_snap}.json`.
Identical rows in every domain (same preselection, classes and `nested_v1` roles; checked). The domain-A rerun
reproduces every reference bit for bit:
- per-model nested-validation AUCs 0.9789 / 0.9158 / 0.8934 / 0.9624;
- the joint 27.1 % / 0.747 % and 44.0 % / 0.778 % (`reference_check: REPRODUCED`);
- the retrained domain-A models equal the existing boosters exactly (max |Δ| 0).

### 8.1 What changes in the SP inputs (split-move; snap alike)

| SP model | replaced inputs | rows whose vector changes | nature of the change |
|---|---|---|---|
| SP numu | `numu_1_score`, `numu_score` | **55,828 / 55,828** | `numu_1_score` moves to a new range: median −0.37 → 0.90 (signal), 0.04 → 0.96 (background); KS = 1.00. `numu_score` shifts (median −0.85 → −1.02 signal; KS 0.16 / 0.06) |
| SP other | 4 νμ outputs | **33,211 / 33,211** | as above; `numu_2_score` changes on 734 rows and `cosmict_10_score` on 2,573 (the rest keep the empty constants) |
| SP ncpi0 | 15 νe level-1 scores | **9,838 / 27,127** (the `br_filled == 1` rows) | new values lie in [empty + 0.05, 0.99] (chain transform), where the shipped values could fall below the empty constant; KS 0.08–0.40 per input |
| SP nue | none | 0 | — |

### 8.2 Per-model separation (nested validation; holdout in brackets)

| model | domain | inherited XML | domain-A model applied unchanged | **retrained in the domain** |
|---|---|---:|---:|---:|
| SP numu | A | 0.9610 | 0.9789 | 0.9789 (0.9752) |
| | **B** | 0.9611 | 0.9780 | **0.9802** (0.9785) |
| SP other | A | 0.8336 | 0.9158 | 0.9158 (0.9149) |
| | **B** | 0.8125 | **0.9016** | **0.9194** (0.9165) |
| SP ncpi0 | A | 0.8531 | 0.8934 | 0.8934 (0.8966) |
| | **C** | **0.7323** | 0.8824 | **0.8945** (0.8958) |
| SP nue | A (= all) | 0.9224 | 0.9624 | 0.9624 |

Snap: numu 0.9749 → 0.9769, other 0.9115 → 0.9166, ncpi0 0.8943 → 0.8916 (holdout 0.8974 → 0.8964).

At the domain-A per-model signal efficiency, the retrained background acceptance on nested validation is:
- SP numu: 3.35 % → **2.95 %**;
- SP other: 2.51 % → **2.05 %**;
- SP ncpi0: 5.75 % → 6.27 %, at 51.7 % instead of 52.3 % signal (the threshold grid is discrete).

### 8.3 Joint four-cut selection (production order, nested validation, split-move)

| domain | inherited XMLs, historical cuts | domain-A models + thresholds, unchanged | retrained, at the domain-A per-model efficiencies | retrained front: best NC Δ at BNB ≤ 0.78 % / ≤ 0.70 % |
|---|---|---|---|---|
| A stored | 27.1 % / 0.75 % | 44.0 % / 0.78 % | 44.0 % / 0.78 % | 48.0 % / 45.4 % |
| B νμ release | **2.5 % / 0.08 %** | 34.4 % / 0.42 % | 42.9 % / 0.73 % | 47.5 % / 45.4 % |
| C νe release | 30.6 % / **2.32 %** | 44.9 % / 0.87 % | 43.0 % / 0.70 % | 48.3 % / 46.7 % |
| **D both** | **2.8 % / 0.19 %** | 35.1 % / 0.42 % | **42.1 % / 0.70 %** | **48.7 % / 47.4 %** |

Snap, retrained front at ≤ 0.78 %: A 48.2, B 48.4, C 47.7, D 48.0 %.

Rows (split-move): 1,494 NC Δ signal and 6,424 BNB background. One binomial sd on 48 % is 1.3 points.
- **Without retraining, the new upstream scores break the selection.**
  - The inherited XMLs at their historical cuts keep 2.5 % of the signal in B/D, because the SP numu and SP other cuts
    now act on a `numu_1_score` on a different scale.
  - In C the inherited SP ncpi0 cut lets three times the background through.
  - The domain-A development models lose 145 of 657 passing signal rows in B (paired).
- **With retraining in the domain**, the joint front moves by **−0.5 to +2 points** (D at ≤ 0.70 %: +2.0). That is
  within about 1.5 σ of the domain-A front. The per-model reference points sit at somewhat lower efficiency and
  background (42.1 % / 0.70 % in D); paired against A, 64 signal rows are lost and 36 gained, and 17 BNB rows are lost
  and 12 gained. No threshold is chosen from this.
- Topology (retrained, D): 0p 49.6 %, 1p 38.8 %, ≥ 2p 19.4 % (A: 51.2 / 39.9 / 26.6 %), on 124 rows for ≥ 2p.
- EXT: 0 of 20 nested-validation rows pass in any domain; νe CC `nueCCBkg` acceptance 0.93 % in A and D.

### 8.4 Upstream training overlap (diagnostic)

Xuyang trained on the same Aurora samples:
- νμ: BNB, the NC events of NC Δ, the beam-off half;
- νe: BNB, νe CC, NC Δ, beam-off, restricted to `br_filled == 1` candidates with the reco vertex in the νe FV.

Within those pools every row was fitted except the `split_v11 == 'dev'` slice (MC `subrun % 10 == 0`, beam-off
`run % 10 == 1`; ~10 % of rows), which was used only for early stopping. Our outer holdout (odd subruns) lies entirely in
his fitted part. Change of the retrained nested-validation AUC between
domain A and the release domain, by Xuyang's role:

| model | his dev slice: A → domain (rows) | his training rows: A → domain (rows) |
|---|---|---|
| SP numu | 0.9785 → 0.9795 (+0.0010; 1,114) | 0.9790 → 0.9803 (+0.0013; 4,582) |
| SP other | 0.9335 → 0.9334 (−0.0001; 653) | 0.9114 → 0.9159 (**+0.0045**; 2,620) |
| SP ncpi0 | 0.9080 → 0.9110 (+0.0030; 547) | 0.8899 → 0.8905 (+0.0006; 2,171) |

The SP other gain appears only on rows that trained the upstream νμ models. That is compatible with mild in-sample
optimism of the new νμ scores, but the dev-slice precision (~0.01 on 653 rows) cannot separate it from a fluctuation.
The joint NC Δ efficiency shows no larger gap in D than in A (dev / train rows: A 45.5 / 43.6 %, D 43.3 / 41.8 %).
**The upstream overlap cannot be measured with development data; it is measured only by the independent evaluation
after the freeze.**

## 9. Can the existing production be reused, or is reconstruction needed?

**For development: reuse — no reconstruction is needed.**
- The WCL1116 merged CAFs hold every input of both releases for every candidate of the four development samples, in both
  vertex trees (§4).
- The shipped final models close bit for bit on them (§5.1), and so do the shipped level-1 models with ROOT TMVA (§7.4).
- The released models evaluated offline match the patched chain (§7).
- The overlay therefore **is** what a WCL1116 production booking the releases would have stored: bit for bit in the
  in-chain test. (The last-bit split crossings of §5.1 separate Xuyang's XGBoost scorer from the chain, not our overlay
  from the chain.)

**What the releases do not change** (verified in-chain, §7.3: every other branch identical):
- the reconstruction, the vertex, the taggers' raw values;
- every other SP input (`shw_sp_*`, `kine_pio_*`, the raw cosmic-tagger values);
- the stored `numu_cc_flag`.

A step-2 rerun with the releases is a pure re-scoring of the same reconstruction.

**For the final training: no extra reconstruction is caused by the releases.**
- The final domain needs a new production anyway: the effective boundary, the frozen vertex, and the reprocessed
  beam-off half (§10).
- That production should book the releases: patched toolkit, release folders on `WIRECELL_PATH`, and
  `NUMU_SIM_DQDX_SCALE=1.071` on simulation.
- Where its step 1 is reusable, only step 2 reruns.
- If it does not book them, the same overlay pipeline applies unchanged; it is verified on both trees.

## 10. Remaining blockers to final training

Final SP training is **not** unblocked by the upstream release alone. Open items, in the order they gate:

| # | blocker | owner | status / what closes it |
|---|---|---|---|
| 1 | **Effective detector-boundary treatment** (cosmic-tagger boundary). SP other must be retrained in it (60 of 146 inputs tied to `cosmic_tagger()`; ablations −0.009 / −0.009 / −0.026 AUC) | Haiwang | not delivered; the WCL1116 reconstruction is the current development domain, not the final one |
| 2 | **Final vertex configuration** (dv2_split_move vs dv2_snap) | collaboration | not frozen. Development evidence favours split-move, and the upstream release does not change that (both trees re-scored, see §8) |
| 3 | **Beam-off training half in the final domain**, reprocessed and re-verified (stamps, checksums, membership) with the EXT exception re-approved | Haiwang (FermiGrid) + Avinay | the WCL1116 half is verified (558/558). A boundary production needs a new staging and verification |
| 4 | **Upstream models chosen for production** (whether Round 2 books `numu_round3af` + `nue_round4_ruleA_v2`, with the toolkit patch) | Xuyang, Matteo, Haiwang | released and recommended; not booked in any production yet. A production with the patch also needs a toolkit build whose **version stamp** our provenance gate accepts (see §7) |
| 5 | **Upstream training overlap** | — | the new upstream models were fitted on the same Aurora samples (all pool rows outside a ~10 % slice; §8.4). Downstream development numbers on those rows are conditional on in-sample upstream scores. Independent quantification is possible only on the FermiGrid evaluation samples, **after** the freeze, by the policy |
| 6 | **Data/simulation charge scale** for the SP inputs themselves | collaboration | the 1.071 correction is a νμ-tagger-specific training correction and is (correctly) not applied to SP inputs. 27 / 56 SP nue, 34 / 146 SP other and 9 / 73 SP numu inputs are dQ/dx-based and stay uncorrected on simulation. This is a data/MC systematic to evaluate, not something to fix by reusing the νμ factor |
| 7 | **Beam-off in-chain check** | — | no beam-off step-1 output exists on Aurora (the half was reconstructed at Fermilab). The data path is covered offline (no correction) and by the reality=data gate test (§7); a beam-off step-2 check belongs to the next FermiGrid production |

Until 1–4 close, every retraining result in this note is labelled **DEVELOPMENT ONLY**.

## 11. Recommended training plan and EAF deployment handoff

### 11.1 Development (now, no new production)

1. **Adopt domain D as the SP development domain**, through the checked overlays: νμ `numu_round3af` (simulation
   corrected in the BDT copies) and νe `nue_round4_ruleA_v2` main. These are the values a genuine production with the
   release files and the toolkit patch would store. Keep domain A as the frozen reference (27.1 → 44.0 %).
2. Keep the four-model architecture, the frozen development specs (features, hyperparameters, seed), the sample
   membership and `nested_v1`. Train only on FIT, compare on NESTED VALIDATION, and report the existing development
   holdout separately.
3. **SP ncpi0 and SP other / SP numu must be retrained in domain D**; the inherited XMLs and the domain-A development
   models must not be applied to domain-D inputs (§8: the level-1 scores change scale). SP nue is unchanged and is not
   retrained for this.
4. Report every number **by Xuyang's `split_v11` role** as well as in total, so that the upstream training overlap stays
   visible.
5. Do not tune or choose thresholds. Do not substitute 3.06 / 0.985 for SP cuts. Nothing is frozen.

### 11.2 Final-domain retraining (after the §10 gates)

The rerun machinery exists (`config/campaigns/round2_final_reco_candidate.yaml`, `tools/final_domain_campaign.py`); its
contract gains upstream fields, which are now known:
- `numu_model_fingerprint` and `nue_l1_fingerprints`: `sp_retrain.upstream_chain.fingerprint` over the resolved files.
  The releases would give `0b8485a8…` and `36ec972f…` (shipped: `595a9963…`, `17a8e17e…`;
  `validation/upstream_r4/upstream_fingerprints.json`). Not filled in the template: nothing is frozen;
- the toolkit build **with** the `numu_sim_dqdx_scale` patch and its version stamp;
- `NUMU_SIM_DQDX_SCALE=1.071` on simulation units only, verified by the log line in every simulation step-2 log and its
  absence in every data log.

Two routes, both valid:
- **(R1) Production books the releases** (preferred): Haiwang's next production runs step 2 with the patched toolkit and
  the release folders first on `WIRECELL_PATH`. The stored values are then final, and the tables are built as before.
  Step 1 can be reused where the reconstruction does not change. The boundary production will need step 2 anyway, so the
  upstream change adds no cost there.
- **(R2) Offline overlay on a production that booked the shipped weights**: valid because the offline route is shown
  equal to the chain (§7). It is acceptable for development; for the final training (R1) is cleaner, because the stored
  CAF values are then what EAF reads.

### 11.3 EAF deployment handoff

What EAF needs in order to evaluate the SP chain consistently with training:
1. **The same upstream files** in the evaluation production: `numu_round3af` (4 chain XMLs, sha256 in
   `validation/upstream_r4/upstream_release_checksums.json`) and `nue_round4_ruleA_v2/wirecell/main` (16 chain XMLs),
   with the toolkit patch, and `numu_sim_dqdx_scale=1.071` **on simulation only**.
2. Or, when EAF reads FermiGrid CAFs reconstructed with the shipped weights: the same offline overlay
   (`tools/extract_upstream_inputs.py` → `tools/upstream_rescore.py` → `tools/build_upstream_overlay.py`), with
   `--kind mc` for simulation and `--kind data` for beam-on / beam-off. The SP models then read the overlaid columns.
3. **Never mix**: SP models trained in domain D must never score domain-A inputs, and vice versa. The SP model manifest
   must carry the upstream fingerprints, and the EAF scorer must refuse a mismatch.
4. The SP thresholds remain open. They are frozen only after the final retraining, from training-side validation, and
   before any EAF performance is opened.

## Appendix A. Artifacts and reproduction

**In git (this branch):**

| path | what |
|---|---|
| `sp_retrain/upstream_chain.py` | toolkit-0.38.0 chain emulation (+ numu sim patch), WIRECELL_PATH resolution, fingerprints |
| `sp_retrain/upstream_overlay.py` | domains A/B/C/D; checked column replacement; Xuyang's `split_v11` role |
| `config/upstream/` | the three spec files copied verbatim from the release (`numu_l2_inputs_74.txt`, `nue_l2_inputs_258.txt`, `l1_models_xning_0f13988d.py`) |
| `tools/verify_upstream_release.py` | release checksums → `validation/upstream_r4/upstream_release_checksums.json` |
| `tools/upstream_dependency_matrix.py` | → `validation/upstream_r4/sp_upstream_dependency_matrix.{csv,json}` |
| `tools/extract_upstream_inputs.py`, `merge_upstream_slices.py` | Xuyang-schema input tables for either tree |
| `tools/check_upstream_extract_vs_builder.py` | equivalence with Xuyang's builder |
| `tools/upstream_rescore.py`, `compare_upstream_official.py`, `summarize_upstream_rescoring.py` | closure, release scoring, official comparison → `validation/upstream_r4/offline_rescoring_summary.json` |
| `tools/build_upstream_overlay.py` | checked overlays |
| `tools/upstream_domain_study.py` | domains A–D development comparison → `validation/upstream_r4/upstream_domain_study_<mode>.json` |
| `tools/pick_chain_test_units.py`, `find_targeted_chain_units.py`, `chain_test_compare.sh`, `compare_chain_test.py`, `compare_chain_scores.py`, `compare_chain_sp_predictions.py`, `summarize_chain_test.py` | in-chain test → `validation/upstream_r4/chain_test_summary.json`, `chain_test_units*.tsv/json` |
| `tools/upstream_l1_tmva_closure.py`, `cpp/upstream_l1_tmva_eval.cxx` | shipped level-1 closure with ROOT TMVA |
| `tests/test_upstream_r4.py` | unit tests (chain conventions, flag rule, overlay refusal, checksums, fingerprints, registry) |

**Under `$SP_WORK/upstream_r4_20261128/` (not in git):**
- `tables/<mode>/`: extracted inputs;
- `equiv/<mode>/`: builder subsets;
- `rescore/<mode>/`: per-candidate stored / shipped / released values;
- `official/<mode>/`: corrected tables, official scores;
- `overlay/<mode>/`: SP overlays;
- `domain/<mode>/`: retrained development boosters `RETRAINED_<model>_<mode>_<domain>.json`, per-row scores, joint
  grids — all **DEV_DO_NOT_DEPLOY**;
- `chain/`: patched toolkit and workflow clones, build, units, runs, logs;
- `l1_tmva/`: TMVA closure work.

**PBS jobs** (all `neutrinoGPU::WireCell_aurora`, debug queues):

| job | what | nodes, wall time |
|---|---|---|
| 9137631 | extraction, equivalence, scoring | 2 nodes, 30 min |
| 9137651 | patched toolkit build | 1 node, 7 min |
| 9137757 | overlays + domain study | 2 nodes, 2 min |
| 9137793 | in-chain test + TMVA closure | 1 node, 15 min |
