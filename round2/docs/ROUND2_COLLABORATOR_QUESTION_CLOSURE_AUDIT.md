# Round-2 collaborator questions: what existing evidence already answers

Date: 2026-11-17 (Aurora, `aurora-uan-0012`). Branch `round2/sp-bdt-development-training-20261117` (from `d460b5d`).

This is a read-only evidence audit: nobody was contacted, nothing was trained or launched, and no file of Xuyang or
Haiwang was changed. Their repositories were read with `git -c safe.directory=… --no-optional-locks`.

## 0. Sources read

| source | pin | inspected |
|---|---|---|
| Xuyang public workflow `github.com/Ningclover/sbnd-wirecell-bdt` | `main` @ **`e0ea617e1e6959e4ed96923a4a07aade7939216a`**; 5 commits, all 2026-11-17; no other branch, no tag. Read-only clone at `$SP_WORK/external/sbnd-wirecell-bdt`. Her Aurora clone `xning/sbnd-wirecell-bdt` is at the same HEAD and clean | 2026-11-17 17:14 UTC |
| Xuyang `xning/bdt-comm` (private `Ningclover/sbnd-bdt-retraining`) | `main` @ `79887cf` (2026-11-17 16:10). New since our 2026-11-11 audit: `459e043`, `79887cf` (results moved out, pointer to the public repo); `PLAN.md` and `results/RESULTS.md` updated 2026-11-17 | read-only |
| Xuyang `xning/data/fg1-beam-off-train/` and `bdt-comm/data/fg1-beam-off-train.list.tsv` | list sha256 `acb69100fc1bb337de01748e823ba8c811522306cc8675231b2c198b7160ea64` (574 lines = 572 files + 2 header lines) | read-only; census run (§3) |
| Haiwang `yuhw/sbnd-wirecell-production` | `main` @ `8edda03` (2026-11-12). Productions catalogue `docs/productions.js` (26 productions), `aurora/docs/*`, `fermigrid/bin/make-tarball.sh` | read-only |
| Haiwang `yuhw/production-prep/`, `yuhw/wire-cell-data/uboone/weights/`, `yuhw/wct-0.38.1-test` (`0c6d24ed`, 2026-11-17), `yuhw/wct-dv2test` (`ddbc0488`, 2026-11-14) | | bounded name / text searches |
| twester `sbnd_gen2_prod1/Gen2_2026` (linked from Haiwang's area) | metadata of one CAF | read-only |
| our docs and specs at `d460b5d` | | |

## 1. Xuyang: νe and νμ chains

### 1.1 νe level-1 (15 small models): NOT retrained — CLOSED

Exact statements:
- `spec/spec_v1.md:67` (public): "inputs = the 258 names in the shipped order as float32, **the 15 small-model scores as
  STORED in the file**".
- `WORKFLOW.md:67` (public): "keep the shipped small-model scores as inputs (**retraining them leaks**)".
- `bdt-comm/inbox/issue-1-2026-11-10.md:519`: "The small models cannot be retrained on SBND with MicroBooNE's rule". The
  next item, `:520`, documents stacking leakage when small models and the final model share events.

Code:
- `training/round1/train_round1.py` retrains "the shipped 258-input structure" only. `spec/nue_l2_inputs_258.txt` lists
  those 258 inputs, the 15 stored small-model scores among them.
- The public repo contains no code that trains a small model. Her private level-1 experiments (`step4_level1/train_l1.py`
  on wcgpu1, `issue-1:455`) were a study that concluded the small models stay as shipped.

Only the final νe L2 model is retrained. Round 2 of her νe work adds "sample weighting, early stopping, depth scan, new
input families" (`README.md:48`) to the final model.

### 1.2 νμ: no spec, no code, no model yet

- Public repo: νμ appears only as a future adaptation target. `README.md:23` mentions "the νμ CC tagger" as another BDT
  the workflow can be adapted to. `spec_v1.md:78` lists "the nu_mu selection" under "What is not in v1".
- Her Aurora area: every `numu` / `nu_mu` hit is either a background class (`numu_cc`) or a νμ tagger variable or score
  used as an input. There is no νμ spec, training script, PBS script or model.
- `PLAN.md:86`: "the nu_e CC BDT first; the nu_mu CC BDT after the nu_e one is fixed".
- **No νμ model is frozen today.** The current `numu_score` is the shipped one.

| νμ quantity | fixed / stored? | planned retrain? | retrain code? | evidence |
|---|---|---|---|---|
| `numu_1_score` (`numu_tagger1`, 7 per-object inputs, max-pooled, empty → −0.4) | stored in CAF | no evidence | no | `issue-1:12-19, 39`; WORKFLOW lesson "keep the shipped small-model scores" (general) |
| `numu_2_score` (`numu_tagger2`, 4 inputs, max, −0.1) | stored | no evidence | no | same |
| `numu_3_score` (`numu_tagger3`, scalar, −0.2) | stored | no evidence | no | same. Input to no SP model and not to the final νμ model |
| `cosmict_10_score` (`cos_tagger_10`, 5 inputs, min, 0.7) | stored | no evidence | no | same |
| final `numu_score` (`numu_scalars_scores_0923.xml`, Grad, 400 trees, **74 inputs**, sha256 `426e670c…`) | stored | **planned** ("νμ CC BDT after νe", `PLAN.md:86`) | no | |

### 1.3 Offline rescoring of the final `numu_score`: ONE REFRESH SUFFICIENT (for a final-model change)

- The 74 inputs of the shipped final νμ model are all T_tagger / T_kine scalars in the aurora-r2 schema (md5 `af9c87c8…`).
  The three upstream scores among them are `cosmict_10_score`, `numu_1_score` and `numu_2_score`.
- **Test.** `tools/check_numu_score_offline.py` re-scores the stored `numu_score` from the stored inputs with
  `sp_retrain.tmva_grad`. Result: **bit-identical on 296,263 / 296,263 BNB and 23,965 / 23,965 NC Δ non-placeholder
  candidates** (`validation/numu_score_offline_bitcheck_aurora_r2.json`).
- Xuyang's route is already offline: "Inference is post-processing of the merged CAF" (`spec_v1.md:64`), and
  `PLAN.md:78` records it as decided ("toolkit integration after the model is final").

| input of the final νμ model / SP numu / SP other | stored in CAF? | branch | recompute offline? |
|---|---|---|---|
| 71 reco scalars of the final νμ model (`numu_cc_flag_3`, `numu_cc_3_*`, `cosmict_*`, `kine_reco_Enu`, `match_isFC`, …) | yes | `wc.T_tagger.*`, `wc.T_kine.kine_reco_Enu` | n/a (reconstruction) |
| `numu_1_score`, `numu_2_score`, `cosmict_10_score` | yes | `wc.T_tagger.*_score` | **inputs persisted** as per-object lists (`numu_cc_1_*`, `numu_cc_2_*`, `cosmict_10_*`, jagged `..totarraysize`). Needs a TMVA **AdaBoost + 6 input transforms** evaluator plus the scorer's protections and pooling; not verified on merged CAFs |
| `numu_3_score` | yes | `wc.T_tagger.numu_3_score` | **no**: input `numu_cc_3_acc_track_length` is not in the CAF (feeds nothing we use) |
| final `numu_score` | yes | `wc.T_tagger.numu_score` | **yes, proven bit-identical** |
| SP numu (73) and SP other (146) inputs | yes, all | `config/features/*_inputs_v0.json` | n/a |

**Verdict:**
- A new **final** `numu_score` can be computed offline on one refresh. A second WCT rerun is not needed for that.
- If Xuyang changed a **νμ level-1** model, the inputs are stored, but an AdaBoost-with-transforms evaluator would be
  needed, or a second rerun. That is the one remaining Xuyang question (§8).

### 1.4 `base_score = 0.5`: UNDERSTOOD — NO QUESTION NEEDED

- `WORKFLOW.md:14-15`: "Train with `base_score=0.5` and export JSON: a model written by xgboost 3.x with a fitted
  base_score loads in 2.1 with a silent constant shift of the margin". The gpvm bundle runs xgboost 2.1.4.
- `spec_v1.md:64`: readers patch `base_score` from the JSON, and the score is written as the raw margin.
- `spec_v1.md:67`: "the one intended difference: wcgpu let xgboost fit it, 0.7355; a constant margin offset".
- Her round-1 model (`BDT/working/step6_round1/output/model_round1_seed7.json`) has xgboost version `[3,4,1]`,
  `base_score [5E-1]`, `binary:logitraw`, 600 trees. Under `logitraw` in 3.4.1 this adds +0.5 to every margin, as we
  measured.

It does not change ranking or AUC within her workflow. It only matters for an export: a TMVA conversion must fold the
+0.5. Our SP specs use `base_score 0` for that reason. No conflict.

## 2. Beam-off: the training half exists

### 2.1 The sample

| | value | source |
|---|---|---|
| what | real SBND beam-off (InTime) data, Run 1, SAM `data_SBND2026A_gen2_InTime-Run1_v10_14_02_02_reco1_sbnd` | `xning/data/fg1-beam-off-train/README.md`; `productions.js` entry `fg1-beamoff-train` |
| production | fg1, FermiGrid (Haiwang, prod#1). Merged CAFs `recTree` + `recTreeWireCell`. `ismc = 0` in every file | README; our census |
| reconstruction stamp | **`sbnd-dlvtx-35-pre-master-merge-2026-09-02-424-g78f81c64`** (fg1 chain), **not** aurora-r2's `…merge-54-ga2785870` | our census (every file) |
| files | 572 (80 runs, **all odd**, 18253–18591; every file subrun 1) | list |
| hold-out | 14 files with Xin's hold-out events (`holdout == 1`) → **558 used**, 26,418 events | list; census; matches `PLAN.md:25` |
| Aurora location | `xning/data/fg1-beam-off-train/<pair>/` (relative symlinks into `../beam-off/`) | |
| designation | **training side** in Haiwang's catalogue ("Training (Aurora MC + fg1 beam-off odd runs)"; "the odd-run half is the training sample"), split by the owner on 2026-11-09 | `productions.js`; commits `5a6c1f2`, `2e79421` |
| split inside it | `run % 4 == 1` test quarter, the rest train (Xuyang `spec_v1.split`) | `spec_v1.md` §6, `spec_v1.py:102-107` |

### 2.2 Disjointness from evaluation

- **Run level.** The evaluation half `fg1-beamoff-eval` is the 486 even-run pairs (runs 18250–18592, 22,894 events).
  The training list has 80 runs, all odd, so no run overlaps.
- **File level.** 572 unique file ids. The catalogue states "disjoint from fg1-beamoff-eval in runs and files".
- **Hold-out.** The 14 hold-out files are dropped.
- **Full sample.** The full `fg1-beamoff` (1,058 files) is marked TruthLeakRisk and is not used.
- **Limit of this check.** The even-run list itself is on FermiGrid, not on Aurora, so event-level comparison against
  it was not possible here. Run parity makes event overlap impossible: run is part of the event key.
- **One caveat** (catalogue): the 212 r8 beam-off files (r7's events) fall in both halves, 123 train and 89 eval. This
  matters only for models trained on r7 / r8 events, which we never use.

### 2.3 SP-other census on the training half

CENSUS ONLY; no training. `tools/beamoff_other_census.py` uses the production extractor (`build_tables.extract`); output
`validation/fg1_beam_off_train_other_census.json`.

| quantity | count |
|---|---:|
| files used / read / errors | 558 / 558 / 0 |
| events (Wire-Cell valid) | 26,418 (26,409) |
| candidates | 2,494 (all "no partner": data) |
| non-placeholder candidates | 1,447 |
| `br_filled == 1` (νe tagger block; Xuyang's "119" before hold-out) | 116 |
| `shw_sp_filled == 1` | 449 |
| preselected (non-placeholder, `shw_sp_n_20mev_showers > 0`) | **481** |
| SP-other inputs present | 146 / 146 |
| preselected rows with a non-finite input | 0 |
| **usable EXT-like negative rows** | **481** (train 267 / test 214, run split) |

### 2.4 Is it enough?

| | rows |
|---|---:|
| usable EXT (beam-off) | 481 (train 267) |
| aurora-r2 MC "other" negatives (full lists, preselected): NC without π⁰ 3,831; out of FV / dirt 7,842; overlay cosmic 3,608 | 15,281 (≈ 7,640 on the train side) |
| SP positives (shared signal) | 17,941 |
| MicroBooNE "other" training | 24,936 signal / 27,377 background (EXT share not stated) |

**Verdict: EXISTING TRAINING BEAM-OFF EXISTS BUT IS STATISTICALLY LIMITED.**
- It would be 3.1 % of the "other" negative class: 267 training rows.
- It is technically compatible: all 146 inputs are present and finite.
- It is reconstructed with the fg1 chain, not aurora-r2. A development model could use it after Avinay approves the
  exception in the spec (our firewall refuses fg1 paths by default).
- A final model needs it reprocessed with the Round-2 refresh configuration.

**No new cosmic generation is needed.** The open item is whether Haiwang can reprocess this half in the refresh (§8).

### 2.5 Other cosmic / off-beam products

| product | what | usable for SP-other training? |
|---|---|---|
| `fg1-beamoff-eval` | even-run half | **no**: evaluation side |
| `fg1-beamoff` (1,058 files) | union of the halves | **no**: TruthLeakRisk |
| `r8-beamoff`, `r3/r5/r7` beam-off, `sync` / `preflip` | small FNAL validation sets; r8 / r7 events are inside fg1 | **no**: evaluation side or overlapping |
| in-time CORSIKA-only MC | **not found** in any searched area | — |
| aurora-r2 BNB CV | BNB + CORSIKA overlay (rockbox) | already used: overlay-cosmic component (3,608 rows) |

## 3. NC π⁰-enriched sample: NOT FOUND

Searched by name (`ncpi0`, `nc-pi0`, `pizero`, `pi0`, filters):
- Avinay's `sbnd/`;
- Haiwang's `production-prep/`, `sbnd-wirecell-production/`, `products/`, `sbnd-gen2-data/`, `prod-r1/` and `dlspace/lists/`;
- Xuyang's lists;
- twester's `Gen2_2026`.

| candidate | what it is | usable? |
|---|---|---|
| `yuhw/production-prep/r3-ncpi0-lynn-2026-09-15` | **19 real-data NC-sideband events** (runs 18255–18364), a reconstruction check (toolkit `0ad64223`) | no: data, 19 events |
| `yuhw/production-prep/ncsb-*` | the same NC-sideband data tests | no |
| `twester/sbnd_gen2_prod1/Gen2_2026` | generic `prodgenie_corsika_proton_rockbox0p1_sbnd` (BNB + CORSIKA), Pandora CAFs (`.flat.caf.root`), **no Wire-Cell tree** | no: not enriched, no Wire-Cell |
| aurora-r2 BNB CV | generic BNB: 8,933 NC π⁰ negative rows | already used |

### 3.1 Is an enriched sample justified? Not yet established

| | positive | negative | ratio |
|---|---:|---:|---|
| development ncpi0 training rows | 8,915 | 4,457 | 2.0 : 1 |
| MicroBooNE training | 24,936 | 37,205 | 0.67 : 1 |

- Train / test AUC is 0.985 / 0.817, and the legacy XML reaches 0.754 on the same rows.
- No SP learning curve exists. Xuyang's round-1 learning curve is for νe only.
- The training code could make a negative-statistics learning curve cheaply: about 6 s per fit, so 4–5 fractions take
  under a minute. That is training, and it is not done in this phase.

**Recommendation.** Run that learning curve (negatives at ¼, ½, ¾, 1, positives fixed) before asking Haiwang for an
enriched production. Ask only if test AUC still rises at full statistics.

## 4. Deployment route

| question | answer | evidence |
|---|---|---|
| where are the legacy SP BDTs evaluated? | in MicroBooNE, in a flat-tree post-process (`apps/bdt_convert.cxx`), not in the Wire-Cell runtime. In SBND, **nowhere** | `bdt_convert.cxx` @ `0100d4b6`; no SP scorer in toolkit `a2785870` or in the newest builds `wct-0.38.1-test` / `wct-dv2test` (only a review doc `clus/docs/patternrecognition/singlephoton_tagger_review.md`); no `single_photon` branch in the CAF schema; the production tarball ships only the νe / νμ weights (`make-tarball.sh:45-50`) |
| can a score be recomputed offline from CAF variables? | **yes** | all SP inputs are stored scalars; `tmva_grad` bit-identical for `nue_score` (423 / 423) and now `numu_score` (320,228 / 320,228); EAF's Round-1 scorer is offline |
| is an offline score table enough for the EAF Round-2 evaluation? | **yes, for analysis and evaluation** | the evaluation reads scores per candidate, whatever produced them |
| what would official CAF production need? | a TMVA XML (`BoostType=Grad`, no transforms) booked by a new toolkit scorer, or a post-process step writing score branches | `issue-1` item 5 (the toolkit reads TMVA XML via `TMVA::Reader` / `TmvaGradForest`); `PLAN.md:78` (Xuyang defers toolkit integration until the model is final) |

**Classification:**
- **Offline score table: acceptable for analysis and evaluation.** No question is needed now.
- **Production integration: unresolved but not needed until the models are final.** It follows Xuyang's νe sequence,
  so it is a later Haiwang item, not a current question.

## 5. Provenance and POT

| question | answer | evidence |
|---|---|---|
| production POT for filtered samples | in the **reco1 sidecars' `mc.pot`** (NC Δ 5.487e21 in total). The pair lists map unit → reco1 → CAF | Haiwang `aurora-campaigns-outputs-guide.md:157, 24` |
| hashes in the CAF | **no hashes**. `Trun` stores `wct_version`, `bdt_weights_dir`, `dl_weights`, `nue_xgboost_xml`, `numu_xgboost_xml`, `trackfitting_config` and `input_file` (names and paths). The campaign docs record toolkit, larwirecell and wire-cell-data commits and the weight and SCN file names | schema; guide:28-30 |
| `wct_version` vs catalogue commit | the stamp is a `git describe --tags` string that "depends on the tags of the checkout" (`aurora-r8-chain.md:155`). Our earlier audit showed catalogue `55177882` = the same change rebased on `a2785870` (13 differing files: writers, truth match, clustering) | understood; files are authoritative |

## 6. SP nue: the thesis is a 200-tree prefix of the frozen XML

`tools/nue_prefix_test.py` compares the per-variable split counts of the first N trees of
`single_photon_nue_bdt_final.xml` (verified bundle) with the thesis Fig. E.4 vector:
- **N = 200 matches exactly**: all 56 inputs, total 5,721 = 5,721.
- No other N matches. All 300 trees differ by 2,515 splits.

Output: `validation/nue_appendixE_prefix_test.json`.

So the thesis importance plot was drawn from the first 200 rounds of the **same forest**: an earlier snapshot, or the
best iteration. The frozen XML holds all 300 trees that App. E.4 lists.

**The SP-nue "THESIS/XML VERSION MISMATCH" is resolved.** It is the same model. SP nue stays DECISION BLOCKED for one
reason only: the vertex-domain shift is unknown.

## 7. Our own statements that the evidence changes

| statement (file:line at `d460b5d`) | classification |
|---|---|
| `SP_BDT_DEPENDENCY_AND_TARGET_AUDIT.md:167-168`: "Cosmic-only real data exist only as official fg1 beam-off, which is evaluation-side … no cosmic-only sample" | **partially obsolete**: the odd-run half is training side in Haiwang's catalogue and is on Aurora. Only our own firewall default treats it as evaluation |
| same `:172`, "It needs an in-time-cosmic sample processed with the training-refresh reconstruction" | **still correct for the final model**: the existing half must be reprocessed |
| same `:203`, "the EXT … negative component has no training-side sample" | **incorrect** |
| same `:241` (Q7), "Which in-time-cosmic sample" | **partially obsolete**: answer `fg1-beamoff-train`. Open: reprocessing, statistics |
| `SP_BDT_DEVELOPMENT_TRAINING_SUMMARY.md:13`, "WAITING FOR IN-TIME COSMIC TRAINING SAMPLE + XUYANG NUMU FREEZE" | **partially obsolete**: sample exists. Waiting for the exception, statistics and the νμ freeze |
| `SP_BDT_ROUND2_FREEZE_ORDER.md:39, 65, 81` ("needs the in-time-cosmic sample") | **partially obsolete** |
| same `:149`, "no EXT / in-time-cosmic sample" | **incorrect** |
| same §4 SP nue, "Thesis/XML fingerprint MISMATCH" | **incorrect** (prefix N = 200) |
| `HAIWANG_AURORA_TRAINING_REFRESH_REQUEST.md:9, 63, 66` ("new sample: in-time cosmics", "none on the training side", "Required … in-time cosmics") | **incorrect**: reword as reprocessing |
| `YANDEL_THESIS_SP_BDT_TRAINING_SOURCE_AUDIT.md:281, 365, 372, 381, 393, 403` (EXT "NO", "no Aurora source") | **incorrect / partially obsolete** |
| `specs/single_photon_other_training_spec_v0.2.yaml:12, 74` ("no Aurora training sample contains such events", "availability: none") | **incorrect** |
| `NCPI0_OTHER_ROUND2_PRODUCTION_HANDOFF_REQUIREMENTS.md:5`; `NCPI0_OTHER_CAF_INPUT_READINESS.md:32`; `README.md:14`; `sp_retrain/labels.py:16` | **partially obsolete** |
| `EAF_ROUND2_EVALUATION_HANDOFF.md:44`, "even-run evaluation half only" | **still correct** |

## 8. Haiwang refresh request, line by line

| request line (`HAIWANG_AURORA_TRAINING_REFRESH_REQUEST.md` at `d460b5d`) | mark | why |
|---|---|---|
| NC Δ (all), BNB CV (all) | **KEEP** | the signal and all MC negative classes |
| CC νe "as Xuyang needs" | **KEEP** | her νe retraining |
| "in-time cosmics (new, required for SP other)", "none on the training side" | **REWORD** | → reprocess the existing `fg1-beamoff-train` half (572 pairs) with the refresh configuration; more off-beam statistics optional |
| "NC π⁰-enriched MC (recommended)" | **REWORD** | → optional, only if the negative-statistics learning curve (§3.1) shows a gain |
| "Not needed: an enriched νμ CC sample" | **KEEP** | |
| "the same check must pass for the frozen νμ model" (`:36-37`) | **REWORD** | → done for the shipped final νμ model: 320,228 / 320,228 bit-identical |
| "A second rerun is needed only if Round-2 changes the νμ or νe level-1 models" (`:38-39`) | **REWORD** | νe level-1: fixed (Xuyang's spec). νμ level-1: STILL UNKNOWN (one Xuyang question) |
| configuration items 1–4; output wanted; branches to persist | **KEEP** | |
| provenance: commits, weight and DL sha256, config hash, schema md5, lists | **KEEP** | `Trun` stores names and paths only, so hashes must come with the production record |
| "the files say `a2785870` while the catalogue says `55177882`" | **REWORD** | understood (describe string, rebased change). Ask only for the commit hash as built |
| production POT per unit for filtered samples | **KEEP** | already in the reco1 sidecars' `mc.pot`; keep the unit → reco1 mapping |
| "If a toolkit single-photon scorer exists by then …" | **KEEP** | none exists; harmless |

## 9. Question-closure matrix

| # | question | evidence | answer | confidence | ask collaborator? | who? |
|---:|---|---|---|---|---|---|
| 1 | Are the νe L1 models changing? | `spec_v1.md:67`; `WORKFLOW.md:67`; `issue-1:519-520`; no L1 training code | no: used as stored | high | **CLOSED — DO NOT ASK** | — |
| 2 | Is only the final νe retrained? | `train_round1.py`; `nue_l2_inputs_258.txt`; `README.md:48` | yes (round 2 adds weighting, early stopping, depth, input families to the final model) | high | **CLOSED — DO NOT ASK** | — |
| 3 | Are the νμ L1 models changing? | no νμ spec or code; general lesson "keep the shipped small-model scores" | not stated for νμ | medium | **GENUINELY NEEDS XUYANG** | Xuyang |
| 4 | Is only the final `numu_score` retrained? | `PLAN.md:86` "νμ CC BDT after νe"; no spec | planned, not specified | medium | **GENUINELY NEEDS XUYANG** (same question as 3) | Xuyang |
| 5 | Can the final νμ score be recomputed offline? | 74 stored inputs; **bit-identical 320,228 / 320,228**; `spec_v1.md:64`, `PLAN.md:78` | yes | high | **CLOSED — DO NOT ASK** | — |
| 6 | Which νμ model is frozen? | no νμ model in either repo or area | none: the shipped `numu_scalars_scores_0923.xml` is current | high | **CLOSED — DO NOT ASK** | — |
| 7 | Is `base_score=0.5` deliberate? | `WORKFLOW.md:14-15`; `spec_v1.md:64, 67`; her 3.4.1 model JSON | yes: gpvm 2.1.4 compatibility, constant +0.5 margin | high | **CLOSED — DO NOT ASK** | — |
| 8 | Do we need a new cosmic sample? | `productions.js` (`fg1-beamoff-train` = training side); census 481 rows | no new generation; reprocessing of the existing half | high | **LIKELY CLOSED — VERIFY INTERNALLY** (Avinay approves the exception) | — |
| 9 | Is the existing training beam-off sufficient? | §2.4 | exists but statistically limited (3.1 % of "other" negatives) | high | **CLOSED — DO NOT ASK** (internal decision) | — |
| 10 | Does an NC π⁰-enriched sample exist? | §3 searches | no | high | **CLOSED — DO NOT ASK** | — |
| 11 | Do we need a new NC π⁰ production? | §3.1 | not established; learning curve first | medium | **LIKELY CLOSED — VERIFY INTERNALLY** | — |
| 12 | Is one training refresh enough? | §1.3; §2 | yes for MC + final `numu_score`; beam-off needs including; νμ L1 depends on #3 | medium | **GENUINELY NEEDS HAIWANG** (beam-off reprocessing) | Haiwang |
| 13 | Do new SP models need TMVA XML / toolkit integration? | §4 | not for analysis / evaluation; for production later, TMVA XML (Grad) | high | **LIKELY CLOSED — VERIFY INTERNALLY**; ask only when models are final | — |
| 14 | Can final SP scores be evaluated offline? | §4; stored inputs; `tmva_grad` bit-identical | yes | high | **CLOSED — DO NOT ASK** | — |
| 15 | Is there already a production integration path? | no SP scorer, branch or weight file anywhere | no | high | **CLOSED — DO NOT ASK** | — |
| 16 | Can production POT be persisted cleanly? | reco1 sidecars `mc.pot`; pair lists | yes, already exists | high | **CLOSED — DO NOT ASK** | — |
| 17 | Can exact toolkit / weight / DL hashes be stored? | `Trun` stores names and paths; docs record commits | hashes can be computed from the recorded commits and paths; request already asks | medium | **LIKELY CLOSED — VERIFY INTERNALLY** | — |
| 18 | Is the `wct_version` / catalogue mismatch understood? | `aurora-r8-chain.md:155`; our audit §0 | yes | high | **LIKELY CLOSED — VERIFY INTERNALLY** | — |

The remaining questions are in `ROUND2_MINIMAL_COLLABORATOR_QUESTIONS.md`.
