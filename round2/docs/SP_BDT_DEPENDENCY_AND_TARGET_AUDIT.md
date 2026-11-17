# Single-photon BDTs: dependency graph, training targets, and when each can be frozen

Date: 2026-11-17 (Aurora, `aurora-uan-0010`). Scope: source audit only. No model was trained and no production area was
changed. Every statement below cites its source. "SOURCE-ESTABLISHED" means read in code or a document. "STRONGLY
INFERRED" is a reasoned conclusion that no source states. "UNKNOWN" means not recoverable from anything reachable today.

**Updated later the same day, once E. H. Yandel's thesis was available locally.** §1 (tree counts), §3, §4, §6 and §7
now follow `YANDEL_THESIS_SP_BDT_TRAINING_SOURCE_AUDIT.md`, which has the page citations.

**Second update, after the EAF XML audit** (`analysis/sp-bdt-thesis-xml-compatibility-20261117` @ `0148e879`):
- The Appendix E F scores fingerprint-match the frozen numu, other and ncpi0 XMLs exactly; nue does not.
- SP numu now has a recovered target (`SP_NUMU_TRAINING_SOURCE_AUDIT.md`).
- The complete graph, freeze order and per-model decisions are in `SP_BDT_ROUND2_FREEZE_ORDER.md`.

## 0. Sources and pins

| what | pin | how it was checked |
|---|---|---|
| SBND Wire-Cell toolkit that made the Aurora training CAFs (aurora-r2) | commit `a2785870df4079d602775bfea2547b869d9215ce`; files are stamped `wc.Trun.wct_version = sbnd-dlvtx-35-pre-master-merge-54-ga2785870` | stamp read from 15 merged CAFs, 5 per sample, spread through each list. Haiwang's catalogue lists `55177882`, which is the same change rebased onto 5 "PR 544 review" commits. The 13 files that differ between the two are writers, truth match and clustering, not taggers or BDT scorers |
| MicroBooNE single-photon scorer and selection | `brb-rightback/wcp-uboone-bdt-eyandel` @ `0100d4b62193ef3ccdb7d759ce53eb9c1b4bb541` (branch `kdar`) | the sha256 of all 6 source files in this repo's frozen reference bundle (`provenance/microboone_reference_SHA256SUMS.txt`) matches the public commit byte for byte |
| first appearance of the single-photon BDTs | `bf9d7113` (eyandel, 2022-09-21, "add in single photon BDTs"; adds scorer code only) | `git show --stat` |
| frozen XML input lists | `baseline_v0/tables/microboone_single_photon_bdt_inputs.csv`, taken from each XML's `<Variables>` (2026-10-05) | counts agree with `bdt_convert.cxx` `AddVariable` lines (73, 146, 45 + 1 commented, 56) |
| public documentation | MicroBooNE public note 1125 (2024-06-07), PRL 136 181806 / arXiv:2502.06064 | text quoted below |
| training definitions | E. H. Yandel, PhD thesis, UCSB 2024 (escholarship 6rq082dr), PDF sha256 `0ad56e36…1465` | `YANDEL_THESIS_SP_BDT_TRAINING_SOURCE_AUDIT.md` |
| frozen-XML structure | EAF audit, branch `analysis/sp-bdt-thesis-xml-compatibility-20261117`, commit `0148e879ae44c0c61f0fb7874079734a4cead3fa`: trees, depth, splits per variable, upstream usage; all four XML sha256 match | read on Aurora with `git show` (not merged) |
| Xuyang's nu_e / nu_mu retraining | `xning/bdt-comm` @ `2c499b9`. **Unchanged since the 2026-11-17 audit.** No commit since; no file in `xning/` newer than 2026-11-11 04:43 UTC; `origin/main` last updated 2026-11-11 04:42:48. GitHub is private and was not queried | read-only `git --no-optional-locks` |

The four XMLs are not on Aurora: not in `yuhw/wire-cell-data/uboone/weights/` (43 files), and `/lus/eagle` is not mounted.
Their sha256s are recorded in `provenance/software_versions.yaml`.

## 1. The four single-photon classifiers

| BDT | exact input count | upstream BDT-score inputs | direct reco inputs | XML / model source | frozen threshold |
|---|---:|---|---|---|---:|
| `single_photon_numu` | 73 | `numu_1_score` (nu_mu level-1, `numu_tagger1.weights.xml`), `numu_score` (nu_mu final, `numu_scalars_scores_0923.xml`) | 71: `numu_cc_flag_3`, `numu_cc_3_*`, `shw_sp_*` (T_tagger) | `single_photon_numu_bdt_final.xml` sha256 `5886affb…a8961` | > 0.4 |
| `single_photon_other` | 146 | `cosmict_10_score`, `numu_1_score`, `numu_2_score` (nu_mu level-1), `numu_score` (nu_mu final) | 142: cosmic-tagger variables and flags (`cosmict_*`, `cosmic_flag`, `cosmic_filled`, `cosmict_flag`), `numu_cc_flag`, `shw_sp_*` (T_tagger), `reco_nuvtxY` = `T_kine.kine_nu_y_corr` | `single_photon_other_bdt_final.xml` sha256 `8c0ac375…bb16` | > 0.2 |
| `single_photon_ncpi0` | 45 | the 15 nu_e level-1 TMVA scores `br3_3, br3_5, br3_6, pio_2, stw_2, stw_3, stw_4, sig_1, sig_2, lol_1, lol_2, tro_1, tro_2, tro_4, tro_5` (`_score`) | 30: 18 `shw_sp_*` (pi0 pair, shower counts, hol/lol) in T_tagger, 12 `kine_pio_*` in T_kine | `single_photon_ncpi0_bdt_final.xml` sha256 `983a0d82…c3` | > −0.05 |
| `single_photon_nue` | 56 | none | 56 `shw_sp_*` | `single_photon_nue_bdt_final.xml` sha256 `8580ba04…a758a` | > −1.0 |

The ordered lists are in `round2/config/features/single_photon_*_inputs_v0.json`; each input records its branch, type
and producer. All four XMLs are `BoostType=Grad` with `boostWeight` 1. They have 300 / 215 / 400 / 300 trees and
depth 5 / 5 / 6 / 5 for numu / other / ncpi0 / nue (EAF audit `0148e879`), which equals thesis Appendix E. The older
"300 trees for all four" note was wrong for other and ncpi0.

**Thresholds are on the log10-odds score.** MicroBooNE stores `single_photon_*_score = log10((1+v)/(1−v))` with
`v = EvaluateMVA = tanh(raw)` (`inc/WCPLEEANA/bdt.h` `cal_single_photon_*_bdts_xgboost`, present since `bf9d7113`). The
selection `is_singlephoton_sel` (`inc/WCPLEEANA/cuts.h:9088`) cuts that stored score. In `v` the cuts are `v > 0.4305`,
`> 0.2263`, `> −0.0575` and `> −0.8182`. The νe cut is a real cut: note 1125 Table 1 shows it lowers efficiency from
10.8 % to 8.3 %. See §5 for what this means for `baseline_v0`.

Upstream producers in the SBND chain, at `a2785870`:
- `UbooneNumuBDTScorer` writes `numu_1/2/3_score` and `cosmict_10_score` (level-1, empty-list defaults −0.4, −0.1,
  −0.2 and 0.7). It then writes `numu_score` with `cosmict_10_score`, `numu_1_score` and `numu_2_score` as final-model
  inputs 71–73 (`root/src/UbooneNumuBDTScorer.cxx:259-261, 473-476`).
- `UbooneNueBDTScorer` writes the 15 νe level-1 scores and `nue_score` (258 inputs).
- The config requires "nue after numu" (`cfg/pgrapher/experiment/sbnd/clus.jsonnet` near line 2915).
- **No SBND component computes any single-photon score.** No `single_photon_*` XML is named anywhere in `clus/`,
  `root/` or `cfg/pgrapher/experiment/sbnd`. None of the 2,416 merged-CAF branches is a single-photon score.

## 2. Answers and the retraining order

1. **Does `other` consume upstream classifier outputs?** Yes. It reads `numu_score`, `numu_1_score`, `numu_2_score`
   and `cosmict_10_score`, the whole νμ chain.
2. **Does `ncpi0` consume `other`, `numu`, `nue` or other BDT scores?** It reads none of the single-photon scores and
   neither `nue_score` nor `numu_score`. It does read the 15 **νe level-1** scores.
3. **Does `nue` depend on any of these?** The single-photon νe BDT consumes no classifier output. Xuyang's νe final
   score (`nue_score`) is consumed by **no** single-photon BDT.
4. **No single-photon BDT consumes another single-photon score.** They are siblings, trained independently and applied
   as successive cuts. The order `numu -> other -> ncpi0` is the order of the *cuts*, not a training dependency.

```
DL vertex + pattern recognition + hand-written taggers (Wire-Cell step 2)      <- Snehadri's DL vertex update
 |-- nu_mu level-1 TMVA: numu_1/2/3_score, cosmict_10_score --+--> nu_mu final --> numu_score  <- Xuyang (nu_mu)
 |-- nu_e  level-1 TMVA: 15 scores (br3_3 ... tro_5) ---------+--> nu_e final  --> nue_score   <- Xuyang (nu_e)
 |                                                             |
 |-- SP numu  <- reco + numu_1_score + numu_score                       inherited; changes with Xuyang's nu_mu
 |-- SP other <- reco + cosmict_10_score + numu_1/2_score + numu_score  Avinay; must follow Xuyang's nu_mu freeze
 |-- SP ncpi0 <- reco + 15 nu_e level-1 scores                          Avinay; independent of nue_score
 `-- SP nue   <- reco only                                              inherited
```

**Required order:**
1. Freeze the DL vertex and any other reconstruction change.
2. Freeze Xuyang's νμ chain. Confirm that the 15 νe level-1 models stay as shipped (Xuyang's plan keeps them; see
   `bdt-comm` spec_v1 §7).
3. Run the Aurora training refresh (`HAIWANG_AURORA_TRAINING_REFRESH_REQUEST.md`).
4. Train single-photon `other` and `ncpi0`. They can run in parallel.

Xuyang's νe final model is not upstream of any single-photon BDT. It only has to be in the refresh so that the refresh
CAFs match Round-2.

**SP numu (now addressed).** The inherited `single_photon_numu` reads `numu_score`, its most-used input (EAF: 7.7 % of
splits, root of 41 / 300 trees). If Xuyang retrains the νμ final model and SP numu is not retrained, SP numu is
evaluated outside its training domain. Its target is now recovered (`SP_NUMU_TRAINING_SOURCE_AUDIT.md`), and
`SP_BDT_ROUND2_FREEZE_ORDER.md` §4 proposes retraining it together with SP other.

## 3. NCPI0: what the frozen model rejects, and what it was trained on

**A. What it is used to reject (SOURCE-ESTABLISHED).**
- Selection: `single_photon_ncpi0_score > −0.05`. Higher means more single-photon-like (`cuts.h:9093`).
- Note 1125 §3: "NC π0 background BDT: Targeting NC events with a π0 in the final state. As much of this background is
  very similar to the single-photon signal events, separation is difficult."
- The analysis channels (evaluation code) define the NC π⁰ background as NC, `truth_NprimPio == 1`,
  `match_completeness_energy > 0.1·truth_energyInside`, and not any `SP*Sig` signal (`cuts.h` `*_ncpi0overlay`
  channels).

**B. What its training classes were.**
- **SOURCE-ESTABLISHED:** all four BDTs "use the XGBoost framework, and are trained on statistically separate training
  samples of both signal and specific backgrounds" (note 1125 §3).
- **SOURCE-ESTABLISHED:** the analysis signal definition (note 1125 §2.1): exactly one true photon above 20 MeV whose
  shower starts and ends more than 3 cm from the TPC walls, or two photons from one source within 20°. No electrons,
  and no muon above 100 MeV.
  - **NC π⁰ → 1γ is part of the signal** (42 % of the expected SM signal).
  - Analysis categories `SPNCDeltaSig`, `SPNCPi0Sig`, `SPNCOtherSig`, `SPNumuCCSig` and `SPOutFVSig` (`cuts.h:2807-2819`).
- **SOURCE-ESTABLISHED by the thesis** (printed pages; audit §3):
  - The positive class is the inclusive single-photon signal, all five categories: 24,936 training and 25,389 test
    events, shared by all four BDTs (p.127; Fig. 5.9 caption, p.132).
  - The negative class is NC π⁰ background, "background NC events with a π0 in the final state": 37,205 training
    events (p.131). It is the same expression as `cuts.h` `SPNCpi0Bkg` (line 2855).
  - Rows passed the preselection first (p.127): generic selection, 5 < x < 250 cm, ≥ 1 shower > 20 MeV (Table 5.2).
  - Split: shared Wire-Cell list, otherwise even subrun = train (p.128). XGBoost parameters: App. E.3 (p.281).
- **THESIS-IMPLIED:** the negatives are inside the FV (out-of-FV events go to "other"); background counts are enriched,
  not natural; one row per event.
- **STILL UNKNOWN:** primary or any π⁰; a completeness requirement on the training rows; the samples behind the
  negatives; `shw_sp_n_20br1_showers_calc`. No weights are stated.
- No training code exists in `wcp-uboone-bdt-eyandel` (all 12 branches), `eyandel/wcp-uboone-bdt`, `eyandel/LEEana` or
  `brb-rightback/wire-cell-pid`.

**Verdict (thesis audit §10): READY FOR DEVELOPMENT TRAINING** (spec v0.2.2). The EAF XML check is done:
**EXACT MODEL FINGERPRINT MATCH**. 400 trees and depth 6 agree, and all 45 Fig. E.3 F scores equal the XML split counts
(thesis audit §6.1). `kine_pio_flag` Policy B was decided, and a development model was trained on 2026-11-17
(`SP_NCPI0_DEVELOPMENT_TRAINING_REPORT.md`, DO NOT DEPLOY). See also the `kine_pio_flag` options
(`SP_BDT_ROUND2_FREEZE_ORDER.md` §5).

**Two inherited semantics a retrained model must decide explicitly:**
- `kine_pio_flag` (input 34). MicroBooNE's scorer sets `temp_kine_pio_flag = 0` before all single-photon evaluations
  (eyandel `47b1f0c`, 2024-02-26, "break pi0 flag for sp only", comment "uncomment to match old files"). baseline_v0
  fed the real `T_kine` value, which in SBND takes 0, 1 and 2. The thesis model splits on it (Fig. E.3: F score 23,
  10th of 45 by gain), so it was trained with real values. The frozen XML has the same 23 splits on VarIndex 34
  (EAF), so MicroBooNE scored a model trained with real values using 0. Policy options:
  `SP_BDT_ROUND2_FREEZE_ORDER.md` §5.
- `shw_sp_pio_1_mass` is NaN on 0.006–0.02 % of filled candidates. TMVA returns −999 for such rows, while XGBoost
  routes NaN as "missing". In the ncpi0 dry-run census, 6 of 2,599 NC Δ positive rows have a non-finite input:
  `kine_pio_angle`, `kine_pio_theta_1/2`, `kine_pio_mass` and `shw_sp_pio_1_mass`.

## 4. OTHER: the training target

- **SOURCE-ESTABLISHED:**
  - Note 1125 §3: "'Other' background BDT: Targeting remaining backgrounds, primarily cosmic induced events and neutrino
    events in which the true scattering takes place outside of the TPC but charge scatters in and is reconstructed."
  - Note 1125 §4: the "Other" sideband is "primarily consisting of non-beam induced events from cosmic rays and beam
    events that take place outside of the TPC and scatter in".
  - PRL: "'other' backgrounds (mainly consisting of cosmic rays and neutrinos interacting outside of the TPC)".
  - Score direction: higher means more signal-like; cut `> 0.2`.
- **SOURCE-ESTABLISHED by the thesis** (pp.129–131; audit §4):
  - The positive class is the same single-photon signal sample as the sibling BDTs.
  - The negative class has four background types: NC with no π⁰; dirt (outside the cryostat); out of the 3 cm FV inside
    the cryostat; and cosmic rays. The cosmic rays are **both** in-time cosmics from off-beam data ("extbnb" / EXT) and
    overlay events where a cosmic flash-cluster pair was selected.
  - Signal-fitting events of the first three types are trained as signal. EXT is always background.
  - 27,377 background and 24,936 signal events, 146 variables. XGBoost parameters: App. E.2 (depth 5, 215 trees).
- **STILL UNKNOWN:** how the 27,377 events divide between the types; the truth expression for "cosmic"; the two `_calc`
  inputs. No weights are stated.
- **SBND gap.** Cosmic-only real data exist only as official fg1 beam-off, which is evaluation-side under the Round-2
  rule. Aurora MC has cosmic-matched candidates (`T_match` partner with `truth_nu_idx < 0`) but no cosmic-only sample.
  The cosmic-matched candidates are the overlay-cosmic component, not a substitute for EXT.

**Verdict (thesis audit §10): READY ONLY AFTER ADDITIONAL TRAINING SAMPLE.** The thesis/XML link holds, with an
exact fingerprint: 215 trees, depth 5, and all 133 split-on inputs (thesis audit §6.1). It needs an in-time-cosmic sample
processed with the training-refresh reconstruction and split by run. It is also held by its `numu_score` input, which
changes when Xuyang's νμ model is installed.

## 5. Erratum for `baseline_v0` (score convention and routing)

1. **Threshold space.** `analysis/microboone_1gamma_v0/score_microboone_bdts.py` compares `tanh(raw)` with
   0.4 / 0.2 / −0.05 / −1.0. Its validation note states that the thresholds are in tanh space. The MicroBooNE source
   applies them to `log10((1+v)/(1−v))`; the four `cal_single_photon_*` functions have done so since 2022. Recomputed
   from the committed score tables (59 events):

   | sample | selected, tanh space | selected, log10-odds space |
   |---|---|---|
   | baseline_v0 | 3 (evt 5, 15, 36) | **2** (evt 5, 15) |
   | Fix2-v2 | 4 (5, 15, 20, 36) | **3** (5, 15, 20) |

   The whole difference is the νe cut: evt 36 has `v ≤ −0.818`. The numu, other and ncpi0 counts are unchanged on this
   sample.
2. **Equality routing.** That scorer goes left when `x <= cut`. TMVA goes right when `x >= cut`, inverted when
   `cType == 0`, so the two disagree when an input equals a cut, which is plausible for integer counts and flags. The
   132/132 ROOT comparison passed, so it did not happen there. `round2/sp_retrain/tmva_grad.py` follows TMVA.
3. **Multi-candidate events.** baseline_v0 read per-event `tracking-pr.root` and skipped every branch with more than one
   entry, so events with more than one candidate were never scored.

If the EAF first-look round reused this scorer, the same three points apply there.

## 6. Development now versus final freeze

| classifier | development training now? | final freeze now? | must wait for |
|---|---|---|---|
| ncpi0 | **DONE 2026-11-17**: development model, Policy B, DO NOT DEPLOY (`SP_NCPI0_DEVELOPMENT_TRAINING_REPORT.md`). Classes recovered from the thesis, exact XML fingerprint; both present in aurora-r2 (dry-run census: thesis audit §9.1) | **NO** | (1) ~~the EAF XML check~~ done; (2) Snehadri's DL vertex frozen; (3) confirmation that the νe level-1 models stay shipped; (4) any shower or candidate reconstruction change for Round-2 decided, for example the Fix2-v2 fallback; (5) Aurora training refresh with 2–4 installed; (6) exporter and scorer-equivalence test; (7) the deployment route for single-photon scores decided |
| other | **NO**: the EXT (in-time cosmic) negative component has no training-side sample, and `numu_score` is about to change | **NO** | (1) an in-time-cosmic sample in the refresh, split by run; (2) Xuyang's νμ chain frozen and installed; (3) DL vertex frozen; (4) refresh; (5) exporter and equivalence test; (6) ~~the EAF XML check~~ done |
| numu | **DONE 2026-11-17**: development model, DO NOT DEPLOY (`SP_NUMU_DEVELOPMENT_TRAINING_REPORT.md`). Target recovered, exact fingerprint, both classes in aurora-r2 (`SP_NUMU_TRAINING_SOURCE_AUDIT.md` §7) | **NO** | (1) Xuyang's νμ chain frozen and installed; (2) DL vertex frozen; (3) refresh; (4) exporter and equivalence test |
| nue | not proposed: decision blocked (`SP_BDT_ROUND2_FREEZE_ORDER.md` §4; thesis Fig. E.4 does not fingerprint-match the frozen XML) | **NO** | the decision itself |

What would change the input domain of a model trained on today's (Round-1) CAFs:

| future change | ncpi0 | other |
|---|---|---|
| new `numu_score` (Xuyang) | no | **yes** (input 144) |
| new νμ level-1 scores | no | **yes** (141–143) |
| new `nue_score` (Xuyang) | no | no |
| new νe level-1 scores | **yes** (18–32) | no |
| new single-photon `other` score | no | (itself) |
| new DL vertex (Snehadri) | **yes**: every `shw_sp_*`, every `kine_pio_*`, the shower-to-vertex assignment and `shw_sp_filled` itself | **yes**: cosmic-tagger variables, `reco_nuvtxY` = `kine_nu_y_corr` |
| shower or candidate reconstruction change | **yes** | **yes** |
| truth-match (`T_match`) rule change | label only | label only |

A model trained on Round-1 features and deployed on Round-2 features would be evaluated outside its training domain.
The `status` field of each training spec prevents freezing one by accident.

## 7. The questions to send (Haiwang / Xin / Xuyang, to forward to Erin Yandel if needed)

Not sent. Questions 1–2 are mostly answered by the thesis (audit §3–4); only the residuals are listed.

1. **ncpi0 (residual).** Was `truth_Npi0` primary π⁰ or π⁰ from any stage? Did the training rows also need
   `match_completeness_energy > 0.1·truth_energyInside`? Which samples gave the 37,205 negatives? What is
   `shw_sp_n_20br1_showers_calc`?
2. **other (residual).** How did the 27,377 negatives divide between NC, dirt, out of FV, overlay cosmic and EXT? Was
   "cosmic" defined by `badmatch`? What is `shw_sp_vec_mean_dedx_calc`?
3. **kine_pio_flag.** The thesis model and the frozen XML both split on it, 23 times. MicroBooNE nevertheless scored with
   it forced to 0 ("uncomment to match old files"). Was that deliberate?
4. **Xuyang.** Her spec uses the 15 νe level-1 scores as stored (`spec_v1.md:67`), and her plan retrains the νμ CC BDT
   after νe (`PLAN.md:86`). Still to confirm: do the νμ level-1 models stay as shipped, and when is `numu_score`
   frozen?
5. **Haiwang.** Which route will compute single-photon scores in Round-2: a new toolkit scorer or offline post-processing?
6. ~~**EAF (Avinay).** Count trees, depth and splits per variable~~. Done (`0148e879`): exact fingerprint for numu,
   other and ncpi0. **New (EAF):** for nue, count splits per variable over the first N trees (N = 1 … 300) and compare
   with the thesis Fig. E.4 vector (total 5,721), to test whether the thesis nue model is a prefix of the frozen forest.
7. **Haiwang / Avinay.** Which in-time-cosmic sample for "other": SBND off-beam triggers, or an in-time-cosmic
   simulation, processed with the training-refresh reconstruction?
