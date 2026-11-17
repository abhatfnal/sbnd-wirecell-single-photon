# Single-photon `ncpi0` and `other` BDTs: training definitions recovered from the Yandel thesis

Date: 2026-11-17 (Aurora, `aurora-uan-0010`). Scope: a source audit of the thesis, plus a dry-run class census for
`ncpi0`. **No BDT was trained.** Nothing outside Avinay's areas was written. The aurora-r2 merged CAFs in Haiwang's area
were only read.

Conventions:
- "p. N" is the printed page number. In Chapter 5 and Appendix E, PDF page = printed page + 13.
- Confidence labels:
  - **SOURCE-ESTABLISHED**: stated in the thesis, or in MicroBooNE code at the reference commit.
  - **THESIS-IMPLIED**: follows from thesis statements, but is not stated as such.
  - **NOT STATED / STILL UNKNOWN**.
  - **A1–A7**: SBND mapping assumptions (§8).
- Quotes are kept short. Tables and figures are cited by number, not reproduced.

## 1. The thesis

| field | value |
|---|---|
| file | `round2/docs/qt6rq082dr.pdf`. Untracked, not in git, not modified |
| size, mtime | 31,127,968 bytes; 2026-11-17 04:56:26 UTC |
| sha256 | `0ad56e360170aa6d15954c7926c7909352cc9e67e8bcfb1b8db3b113cf5d1465` |
| title | *A Search for Anomalous Single Photon Production in Neutrino Interactions with the MicroBooNE Detector* |
| author, institution | Erin Haley Yandel, PhD dissertation, UC Santa Barbara, 2024 (eScholarship ETD) |
| permalink | https://escholarship.org/uc/item/6rq082dr |
| PDF | 308 pages; pdfTeX, created 2024-05-30, re-stamped by eScholarship 2025-02-28 |
| working copy | per-page `pdftotext -layout` text and PNG renders of the Appendix E figures, under `$SP_WORK/thesis_audit/`. Not committed |

Parts of the thesis that bear on the BDTs:

| part | pages | used for |
|---|---|---|
| §5.1.2 Signal Categories | 121–122 | signal definition and its five categories. The Fig. 5.4 caption defines "NC Pi0 Background" for the opening-angle study |
| §5.1.3 | 122–123 | a high-statistics NC π⁰ simulation sample exists |
| §5.2.1 Preselection | 124–126 | Table 5.2 (p.125); Figs. 5.5–5.6 (p.126) |
| §5.2.2 BDTs | 127–133 | common procedure (127–128); νμ CC (128, Fig. 5.7); **Other (129–131, Fig. 5.8)**; **NCπ⁰ (131–132, Fig. 5.9)**; νe CC (133, Fig. 5.10) |
| one-shower cut; §5.2.3 | 134 | where training is done |
| §5.2.4 Efficiency and Purity | 140–142 | the 4×4 grid (p.141); Tables 5.4 and 5.5 (p.142) |
| §5.3 Sidebands | 148, 155, 159 | efficient cuts used for sidebands; the Other and NCπ⁰ sidebands |
| Appendix E | 278–285 | parameters and importance figures: E.1 νμ (278–280); **E.2 Other (279–282, Fig. E.2)**; **E.3 NCπ⁰ (281–283, Fig. E.3)**; E.4 νe (284–285) |

## 2. Systematic search

A case-insensitive keyword scan covered all 308 pages. Pages 121–134, 140–142 and 278–285 were then read in full.

| term | hits | where the relevant hits are (printed pages) |
|---|---:|---|
| BDT | 150 | 124–134, 140–142, sidebands 148–168, App. E |
| XGBoost | 6 | 127, 279, 281, 283, 284, bibliography |
| TMVA, XML | 0 | **the thesis never mentions TMVA or the XML conversion** |
| training | 96 | BDT training only at 124–135 and 278–285. Most other hits are "cons*training*" |
| test sample/set | 13 | 127–133 |
| NCπ⁰ / π⁰ | 155 / 244 | 121–123, 127, 131–132, 159, 281–283 |
| cosmic / EXT / dirt / outside TPC | 149 / 29 / 30 / 20 | 124–131, 142, 155 |
| weight | 4 | none are training weights. p.127 describes boosting generically; the others are systematics reweighting |
| validation | 18 | none is a BDT validation set |
| ROC/AUC | 4 | only the `eval_metric` lines of App. E |
| hyperparameter, overtrain, "signal sample", "background sample" | 0 | — |

The BDT training is described only in §5.2.1–5.2.3 and Appendix E. No other chapter retrains or redefines them.

## 3. NCPI0 target

**SOURCE-ESTABLISHED**
- **Purpose.** "made to remove background NC events with a π0 in the final state" (p.131).
- **Statistics.** Trained on 37,205 NC π⁰ background events and 24,936 signal events, with 45 variables (p.131).
- **Positive class.** The signal sample common to all four BDTs: 24,936 training and 25,389 test events (p.127). The
  Fig. 5.9 caption (p.132) reads "Signal includes events fitting the inclusive single photon signal definition".
  - The definition (§5.1.2, p.121): exactly one true photon with KE > 20 MeV whose shower starts and ends more than
    3 cm inside the TPC walls, or two such photons from one source within 20°. No electron, and no muon above 100 MeV.
  - All five categories are signal (pp.121–122): NC π⁰ → 1γ, NC Δ 1γ, NC other 1γ, νμ CC 1γ (μ < 100 MeV) and out-of-FV 1γ.
- **Negative class.** "Background includes only NCπ0 background events" (Fig. 5.9 caption).
- **Rows.** All training events passed the preselection (p.127). Training is done "right after preselection" (p.134).
- **Disjoint backgrounds.** Backgrounds are "split up by type and used only on the relevant BDT" (p.127). The four
  per-BDT counts sum exactly to the stated total: 97,580 + 27,377 + 37,205 + 100,958 = 263,120.
- **Same expression in the MicroBooNE code.** The category flags (`cuts.h` @ `0100d4b6`) have the same expressions:
  - `SPNCpi0Bkg` (line 2855) = not any `SP*Sig` (line 2849), `truth_isCC == 0`, `truth_vtxInside == 1`,
    `truth_Npi0 > 0`, and `match_completeness_energy > 0.1·truth_energyInside`.
  - `SPNCPi0Sig` (line 2809) is the signal photon with `truth_showerMother == 111`.

**THESIS-IMPLIED**
- **NC π⁰ events that fit the signal are positive.** NC π⁰ → 1γ is a signal category. It differs from the background
  "only by the number of theoretically reconstruct-able showers" (p.131). An event cannot be in both classes.
- **The negative class is inside the FV.** Out-of-FV interactions are a component of the Other BDT (p.129). The
  disjoint sum above leaves them out of this one, as does `SPNCpi0Bkg`'s `truth_vtxInside`.
- **"A π⁰ in the final state" means ≥ 1 π⁰.**
- **Background training events are enriched, not in natural proportion.**
  - After preselection, NC π⁰ is about 3 % of events (p.127), yet it supplies 37,205 of 263,120 background events.
  - A dedicated "exclusively NCπ0 MC overlay sample" (Fig. 5.4, p.121) and a "high statistics NCπ0 simulation sample"
    (p.123) existed. Which sample fed the training is not stated.
- **One row per event.** MicroBooNE Wire-Cell selects one neutrino candidate per event (§5.2.1).

**STILL UNKNOWN**
- The exact implementations of `truth_single_photon`, of `truth_Npi0` (primary π⁰ or π⁰ from any stage), and of the
  shower-end containment.
- Whether training rows also needed `match_completeness_energy > 0.1·truth_energyInside`. The code flags require it;
  the thesis does not say.
- The samples behind the 37,205 negatives. Event or class weights: none are stated.
- What `shw_sp_n_20br1_showers_calc` is. It is the thesis's name for input `shw_sp_n_20br1_showers` (§6).

**Verdict: target SOURCE-ESTABLISHED.**

## 4. OTHER target

**SOURCE-ESTABLISHED**
- **Purpose (p.129).** "made to remove four different, but similar, backgrounds":
  1. NC events with no π⁰ in the final state;
  2. dirt events, which interact outside the cryostat;
  3. out-of-FV events, in the cryostat with the true vertex outside Wire-Cell's 3 cm FV;
  4. cosmic rays. This includes in-time cosmic rays from **off-beam data ("extbnb"/"EXT")** and out-of-time cosmic rays
     from BNB overlay events where a cosmic flash-cluster pair was selected as the neutrino candidate ("cosmic").
- **Signal override (p.129).** Events of these categories that fit the signal definition are "removed from these
  background categories and trained as signal". The exception is the EXT/cosmic category, which "has no truth
  information and is always considered background".
- **Statistics.** 27,377 background and 24,936 signal events, 146 variables (pp.129–130).
- **Fig. 5.8 caption (p.131).** "Background includes only NC, out of FV, dirt, cosmic, and extbnb events." Signal is
  the inclusive single-photon definition.
- **Matching code categories** (`cuts.h`): `SPNCBkg` (line 2854) and `SPoutFVBkg` (line 2851). `badmatch` =
  `match_completeness_energy ≤ 0.1·truth_energyInside` (line 2719).

**THESIS-IMPLIED**
- EXT events are part of the 27,377 training background. "Always considered background" is said of training, and the
  disjoint total of 263,120 includes the Other count. There is one tension in the text: p.127 calls all background
  events "from Runs 1 and 3 MC samples", although EXT is off-beam data.

**STILL UNKNOWN**
- How the 27,377 events divide between NC, dirt, out of FV, overlay cosmic and EXT. Any weights.
- The truth expression behind "cosmic". The likely candidate is MicroBooNE's `badmatch`.
- What the two `_calc` inputs are (§6).

**Verdict: target SOURCE-ESTABLISHED; one negative component is not available on the training side (§9).**

## 5. Training procedure

| quantity | ncpi0 | other | source page | confidence |
|---|---|---|---|---|
| framework | XGBoost | XGBoost | 127; App. E | SOURCE-ESTABLISHED |
| place in the selection | 3rd of 4 sibling cuts | 2nd of 4 | 128–131 | SOURCE-ESTABLISHED |
| positive class | inclusive single-photon signal, all 5 categories | same sample | 121–122, 127, Figs. 5.8–5.9 | SOURCE-ESTABLISHED |
| negative class | NC background with a π⁰ in the final state | NC without π⁰ + dirt + out of FV + overlay cosmic + EXT | 131; 129, Fig. 5.8 | SOURCE-ESTABLISHED |
| signal-fitting events of a background type | trained as signal (NC π⁰ → 1γ is signal) | trained as signal; EXT always background | 121, 131; 129 | THESIS-IMPLIED; SOURCE-ESTABLISHED |
| FV requirement on the negatives | in the 3 cm FV | out of FV is itself a component | 129; `cuts.h:2855` | THESIS-IMPLIED (+ code) |
| π⁰ multiplicity | ≥ 1; primary or any π⁰ NOT STATED | 0 | 131; 129 | partly NOT STATED |
| training signal events | 24,936 | 24,936 | 127, 131; 129 | SOURCE-ESTABLISHED |
| test signal events | 25,389 | 25,389 | 127 | SOURCE-ESTABLISHED |
| training background events | 37,205 | 27,377 | 131; 129–130 | SOURCE-ESTABLISHED |
| test background events | NOT STATED (246,876 for all four BDTs) | NOT STATED | 127 | NOT STATED |
| background reuse across BDTs | none; per-BDT counts sum to 263,120 | none | 127–133 | SOURCE-ESTABLISHED |
| composition of the negatives | one type | NOT STATED | — | NOT STATED |
| samples | Runs 1 + 3: general BNB and "inclusive single photon enhanced" MC (signal); Runs 1 + 3 MC (background) | same, plus off-beam EXT data | 127; 129 | SOURCE-ESTABLISHED |
| enriched background samples | used, by proportion; which ones NOT STATED | NOT STATED | 121, 123, 127 | THESIS-IMPLIED |
| preselection before training | generic ν selection; reco vertex 5 < x < 250 cm; ≥ 1 shower > 20 MeV | same | 124–125 (Table 5.2), 127, 134 | SOURCE-ESTABLISHED |
| one-shower cut | after the BDT cuts, not in training | same | 134 | THESIS-IMPLIED |
| row unit | event (one candidate per event) | same | 124–127 | THESIS-IMPLIED |
| train / test split | shared Wire-Cell training list; otherwise even subrun = train, odd = test | same | 127–128 | SOURCE-ESTABLISHED |
| validation set, early stopping | NOT STATED | NOT STATED | — | NOT STATED |
| class weights, balancing | NOT STATED (the counts imply natural counts) | NOT STATED | — | NOT STATED |
| event weights (POT, cross-section) | NOT STATED | NOT STATED | — | NOT STATED |
| number of inputs | 45 | 146 | 131; 130 | SOURCE-ESTABLISHED |
| input list with F score and gain | Fig. E.3 | Fig. E.2 | 283; 282 | SOURCE-ESTABLISHED |
| `max_depth` | 6 | 5 | 281; 279 | SOURCE-ESTABLISHED |
| `n_estimators` | 400 | 215 | 281; 279 | SOURCE-ESTABLISHED |
| `learning_rate` | 0.1 | 0.1 | 281; 279 | SOURCE-ESTABLISHED |
| `objective` | `binary:logitraw` | `binary:logitraw` | 281; 279 | SOURCE-ESTABLISHED |
| `colsample_bytree` / `_bylevel` / `_bynode` | 1 / 0.5 / 0.5 | 1 / 0.5 / 0.5 | 281; 279 | SOURCE-ESTABLISHED |
| `subsample`, `gamma`, `seed` | 0.8, 0.2, 1 | 0.8, 0.2, 1 | 281; 281 | SOURCE-ESTABLISHED |
| `eval_metric` | [auc, error] | [auc, error] | 283; 281 | SOURCE-ESTABLISHED |
| other XGBoost settings (`min_child_weight`, `lambda`, `alpha`, `base_score`, `tree_method`, version) | NOT STATED (defaults implied) | NOT STATED | — | NOT STATED |
| conversion to TMVA XML | NOT STATED | NOT STATED | — | NOT STATED (code: `bdt_convert.cxx`) |
| cut scale | log10-odds; grid −2.0 to 1.2 in steps of 0.05 | grid −3.0 to 3.0 in steps of 0.2 | 141 | THESIS-IMPLIED (the Other and νe grids exceed ±1); code: `bdt.h` |
| final ("more pure", E×P²) cut | −0.05 | 0.2 | 141–142 (Table 5.5) | SOURCE-ESTABLISHED |
| "more efficient" (S/√B) cut, used for sidebands | −0.4 | −0.4 | 141–142 (Table 5.4), 148 | SOURCE-ESTABLISHED |
| `kine_pio_flag` | an input that the model splits on (F score 23 in Fig. E.3) | not an input | 283 | SOURCE-ESTABLISHED; scoring treatment NOT STATED (code forces 0) |
| `_calc` inputs | `shw_sp_n_20br1_showers_calc` | `shw_sp_n_20br1_showers_calc`, `shw_sp_vec_mean_dedx_calc` | 283; 282 | definition NOT STATED |
| data / MC check of the top inputs | Figs. 5.12–5.19 | same | 134–139 | SOURCE-ESTABLISHED |
| overtraining check | NOT STATED (test-sample score plots only) | NOT STATED | 131–132 | NOT STATED |

## 6. Cross-check against the frozen XMLs

The XMLs are not on Aurora; §0 of `SP_BDT_DEPENDENCY_AND_TARGET_AUDIT.md` lists where they were looked for. This check
also searched every ref of the four public MicroBooNE clones for any single-photon XML, and found none. The comparison
below uses the XML `<Variables>` lists (`baseline_v0/tables/microboone_single_photon_bdt_inputs.csv`) and the MicroBooNE
code at `0100d4b6`.

| item | thesis | frozen XML / MicroBooNE code | result |
|---|---|---|---|
| ncpi0 input count | 45 (p.131) | 45 `<Variables>`; 45 `AddVariable` in `bdt_convert.cxx` | MATCH |
| ncpi0 input names | Fig. E.3 (p.283) | XML list | 44 of 45 identical. Thesis `shw_sp_n_20br1_showers_calc` = XML `shw_sp_n_20br1_showers` |
| other input count | 146 (p.130) | 146 | MATCH |
| other input names | Fig. E.2 (p.282) | XML list | every legible name identical, except `shw_sp_n_20br1_showers_calc` and `shw_sp_vec_mean_dedx_calc` |
| `_calc` | used in training | no `_calc` name in any ref of the four public repos. `bdt_convert.cxx` binds the stored names (lines 2862, 2895, 2918); its charge scale is 1.0 (line 4141) | OPEN. SBND trains on what it deploys, so this does not affect SBND |
| booster | XGBoost `binary:logitraw` | TMVA `BoostType=Grad`, `boostWeight` 1 | CONSISTENT. The thesis does not document the conversion |
| cut values | Table 5.5: 0.4 / 0.2 / −0.05 / −1.0 | `cuts.h` `is_singlephoton_sel`; note 1125; PRL | MATCH |
| cut scale | grids reach −3 and −4 (p.141) | stored score `log10((1+v)/(1−v))` (`bdt.h`) | CONSISTENT. Cuts are in log10-odds, as in EAF's corrected scorer |
| `kine_pio_flag` (ncpi0) | the model splits on it 23 times (F score 23, gain 9.19, 10th of 45 by gain) | the scorer reads the T_kine value (line 4067), then sets it to 0 before the single-photon scores ("uncomment to match old files", lines 4166–4167) | if the XML is the thesis model, MicroBooNE scored it with a value the training did not use. Check below |
| ncpi0 trees / depth | 400 / 6 (p.281) | **unverified.** `analysis/microboone_1gamma_v0/docs/TMVA_VALIDATION.md` (2026-10-05) says "all 300 trees in all four" models, with no per-model count recorded | **POTENTIAL CONFLICT** |
| other trees / depth | 215 / 5 (p.279) | unverified; the same note | **POTENTIAL CONFLICT** |

**The check that settles it, on EAF** (the XMLs are in the reference bundle there, sha256 in
`provenance/microboone_reference_SHA256SUMS.txt`):
1. Count the `<BinaryTree>` elements and find the deepest node in each XML. The thesis gives
   400 / ≤ 6 (ncpi0) and 215 / ≤ 5 (other).
2. Count the splits on each `IVar` and compare with the XGBoost F scores of Figs. E.3 and E.2. A converted forest keeps
   every split, so the counts should match exactly. In particular, `kine_pio_flag` should have 23 splits.

If both agree, the thesis describes the frozen XMLs. If they disagree, the thesis and the frozen XMLs are different
model versions. The ncpi0 / other final gate then becomes **BLOCKED — THESIS/XML VERSION MISMATCH** until another
source ties the classes to the frozen files. Development training (§10) does not depend on the result. Its classes are
the analysis definitions, and the code that books these XMLs uses the same category flags.

## 7. References and repositories

| source | what it gives | status |
|---|---|---|
| this thesis | training classes, counts, procedure, hyperparameters | primary source |
| MicroBooNE public note 1125 (2024-06-07) | the intent of the four BDTs, the signal definition, cut values | consistent; no training classes |
| PRL 136 181806 / arXiv:2502.06064 | the selection; defers details to the thesis | consistent |
| L. Hagaman, thesis, arXiv:2506.18956 | checked in the earlier audit (front matter only) | not a source for these BDTs |
| `brb-rightback/wcp-uboone-bdt-eyandel` @ `0100d4b6` | booking (`bdt_convert.cxx`), score transform (`bdt.h`), categories and preselection (`cuts.h`) | code-level classes, §3–4 |
| `eyandel/wcp-uboone-bdt`, `eyandel/LEEana`, `brb-rightback/wire-cell-pid` | — | no training code, no single-photon XML, no `_calc` (all refs) |
| thesis refs [61], [62, 68], [67] | Wire-Cell generic selection, the νμ CC BDT, XGBoost | cited by the thesis; not needed for the classes |

## 8. SBND mapping and the implementation

`sp_retrain/sp_truth.py` builds the class ingredients for every truth neutrino from `T_truth_nu` / `T_truth_pf`.
`sp_retrain/build_tables.py` attaches them to each candidate's `T_match` level-2 partner as `m_sp_*`.
`sp_retrain/labels.ncpi0_development_classes` turns them into classes:
- **1** (positive): the partner fits the signal;
- **0** (negative): the partner is NC π⁰ background;
- **−1**: anything else, or a row that fails the preselection.

Assumptions (also in the spec):
- **A1. Photon origin.** A photon is primary, or comes from the decay of a primary π⁰, η, η′, ω or Σ⁰.
- **A2. Shower containment.** Shower start = conversion point. The shower end is not checked; it is not in the CAF.
- **A3. Leptons.** "No electron" means no primary e±. "No muon above 100 MeV" applies to primary μ±.
- **A4. Matching.** The candidate-to-neutrino link is the `T_match` partner; no completeness cut.
- **A5. NC Δ 1γ.** NC, GENIE mode 1, with a primary photon.
- **A6. π⁰ count.** `truth_Npi0` is the number of primary π⁰.
- **A7. FV.** The TPC active volume minus 3 cm on each face.

The preselection is a candidate (every non-placeholder SBND candidate has `numu_cc_flag ≥ 0`, the generic-selection
flag), `shw_sp_n_20mev_showers > 0`, and a readable label. MicroBooNE's 5 < x < 250 cm cut corrects a MicroBooNE
trigger-timing offset (Table 5.2) and is left OPEN for SBND. Unit tests cover the classifier, including merged pairs,
low-KE and exiting photons, and the status gate (22 tests).

## 9. Aurora data readiness

| requirement | ncpi0 available? | other available? | source / sample |
|---|---|---|---|
| inclusive single-photon signal, all categories | **YES** | **YES** | `aurora-r2-ncdr` (NC Δ 1γ) + `aurora-r2-bnb` (NC π⁰ → 1γ, out-of-FV 1γ, νμ CC 1γ, NC other 1γ) |
| signal truth: photon KE, conversion point, parent, primary leptons, vertex | YES (A1–A3, A7) | YES | `T_truth_pf`, `T_truth_nu`; the shower end point is not stored |
| NC π⁰ background in the FV | **YES** | n/a | `aurora-r2-bnb`; a few pileup neutrinos in NC Δ spills |
| NC without π⁰ in the FV | n/a | YES | `aurora-r2-bnb` (+ NC Δ pileup) |
| dirt (outside the cryostat) | n/a | YES | BNB truth includes interactions outside the active volume (73.2 % of BNB truth vertices) |
| out of FV, inside the cryostat | n/a | YES | `aurora-r2-bnb` (the class is `outFVBkg`, which also holds dirt) |
| overlay cosmic (cosmic flash-cluster pair selected) | n/a | YES (simulated CORSIKA cosmics, not data) | BNB / NC Δ candidates whose `T_match` partner is cosmic |
| **EXT: in-time cosmic rays from off-beam data** | n/a | **NO** | none on the training side. The only beam-off CAFs are the official fg1 halves (evaluation only) |
| preselection variables | YES | YES | `shw_sp_n_20mev_showers`, tagger vertex |
| classifier inputs | 45 / 45 | 146 / 146; 4 classifier inputs change with Xuyang's νμ model | `NCPI0_OTHER_CAF_INPUT_READINESS.md` |
| event-safe split keys | YES | YES for MC; off-beam needs a split by run | `(sample, run, subrun)` |
| match-completeness cut | not applied (A4) | not applied | — |

### 9.1 NCPI0 class census (dry run, no training)

Tables were built with the committed builder from the heads of the two lists:
- `aurora-r2-ncdr` files 0–2999 of 17,603;
- `aurora-r2-bnb` files 0–1199 of 11,888.

Both builds had 0 errors, and both carry `wct_version` `sbnd-dlvtx-35-pre-master-merge-54-ga2785870`. 17 NC Δ files
have an unreadable label branch, and 4 BNB files have an unreadable `T_truth_pf`. Their rows are excluded.

The result is `$SP_WORK/census_tables/census.json` (sha256 `653a1df9…6110`), kept outside git. It records the spec
sha256 (`a69bbd37…a0aa`, the committed v0.2.0) and the code sha256s.

| | NC Δ (3,000 files) | BNB (1,200 files) |
|---|---:|---:|
| events / candidates | 4,579 / 4,136 | 63,431 / 30,685 |
| preselected rows (events) | 2,835 (2,809) | 6,748 (6,709) |
| **positive rows (events)** | **2,599 (2,599)** | **257 (257)** |
| **negative rows (events)** | **49 (48)** | **903 (903)** |
| excluded rows | 187 | 5,588 |
| events with both classes | 3 | 0 |
| events with ≥ 2 positive rows | 0 | 0 |
| preselected candidates per event: 1 / 2 | 2,783 / 26 | 6,670 / 39 |
| positive events with 2 candidates; negative events with 2 | 22; 5 | 1; 6 |
| positive by category | NC Δ 2,522; out-of-FV 73; NC π⁰ 3; νμ CC 1 | NC π⁰ 112; out-of-FV 88; νμ CC 43; NC Δ 12; NC other 2 |
| negative by primary π⁰ count: 1 / 2 / ≥ 3 | 47 / 1 / 1 | 856 / 39 / 8 |
| split: train / validation / test, positive | 1,012 / 297 / 1,290 | 105 / 34 / 118 |
| split: train / validation / test, negative | 19 / 7 / 23 | 336 / 121 / 446 |
| rows with a non-finite input: positive; negative | 6 (`kine_pio_angle` 4, `kine_pio_theta_1/2` 2, `kine_pio_mass` 1, `shw_sp_pio_1_mass` 1); 0 | 0; 0 |
| `shw_sp_filled == 1`: positive / negative | 99.5 % / 95.9 % | 99.2 % / 99.7 % |
| true signal ν with a preselected candidate | 2,599 / 3,888 (67 %) | 257 / 460 (56 %) |
| true NC π⁰ background ν with a preselected candidate | 48 / 56 | 903 / 1,189 (76 %) |

Sensitivity to the mapping choices, on the same rows:

| choice | NC Δ | BNB |
|---|---|---|
| A1b: photon from any π⁰, or primary (instead of A1) | 2,575 positive (24 rows change) | 271 positive (22 rows change) |
| A6b: any π⁰ in the event (instead of primary π⁰) | 49 negative (no change) | 956 negative (+53) |
| an illustrative SBND x cut, 5 < \|x\| < 196.3 cm | 2,514 / 48 | 247 / 874 |

Excluded preselected rows: NC Δ has 56 out of FV, 47 cosmic-partner, 35 νμ CC, 24 νμ CC π⁰, 22 NC without π⁰ and
3 νe CC. BNB has 2,332 νμ CC, 1,605 νμ CC π⁰, 788 out of FV, 379 NC without π⁰, 348 cosmic-partner, 115 νe CC,
13 unreadable truth and 8 with no partner. They are the other BDTs' classes, as p.127 requires.

**Full-list statistics** (linear extrapolation by file count; the slices are list heads, so indicative only):

| | positive | negative |
|---|---:|---:|
| total | ≈ 17,800 (86 % NC Δ) | ≈ 9,230 (97 % BNB) |
| even subrun (train + validation) | ≈ 9,060 | ≈ 4,680 |
| odd subrun (test) | ≈ 8,740 | ≈ 4,550 |
| MicroBooNE training sample (p.127, p.131) | 24,936 | 37,205 |

The negative class is the limit: the even-subrun side has about 13 % of MicroBooNE's NC π⁰ training count. That is
enough for development, but thin for a final 400-tree, depth-6 model.

### 9.2 OTHER class census

Not run, because the spec status is not ready. Its MC components are present in the same slices, as the excluded rows
above show:
- NC without π⁰: 379 BNB and 22 NC Δ rows;
- out of FV / dirt: 788 and 56;
- cosmic partner: 348 and 47.

The EXT component has no Aurora source.

## 10. Gate

| classifier | gate | reason |
|---|---|---|
| ncpi0 | **READY FOR DEVELOPMENT TRAINING** | Classes SOURCE-ESTABLISHED (§3). Both are present in aurora-r2 (§9.1). Spec `single_photon_ncpi0_training_spec_v0.2.yaml` |
| other | **READY ONLY AFTER ADDITIONAL TRAINING SAMPLE** | Classes SOURCE-ESTABLISHED (§4), but the EXT negative component has no training-side sample. BNB cosmic-matched candidates are a different component and are **not** substituted. Spec `single_photon_other_training_spec_v0.2.yaml` |

Neither gate permits final training. Final training needs:
- the §6 XML check;
- the Round-2 freezes (`SP_BDT_DEPENDENCY_AND_TARGET_AUDIT.md` §6);
- the training refresh.

**Nothing is trained until Avinay has reviewed these definitions.**

**Additional samples:**
- **other (required).** In-time cosmic events: SBND off-beam triggers, or an in-time-cosmic simulation if Avinay and
  Haiwang accept it as a stand-in.
  - Processed with exactly the training-refresh reconstruction.
  - Split by run, because every beam-off file has art subrun 1.
  - Disjoint from any evaluation beam-off. The fg1 beam-off halves are never used.
  - Normalized by gates, never by POT. Training uses event counts.
- **ncpi0 (recommended for final, not required).** An NC π⁰-enriched MC sample in the same refresh, to raise the
  negative class towards MicroBooNE's scale. MicroBooNE's background counts imply enriched samples (§3).

**Consequence for Haiwang's refresh** (`HAIWANG_AURORA_TRAINING_REFRESH_REQUEST.md`, updated):
- NC Δ and BNB CV in full serve both classifiers.
- CC νe is not a class of either; it is in the refresh only for Xuyang.
- The off-beam / in-time-cosmic sample must be added for "other".
- An NC π⁰-enriched sample is optional, for the final ncpi0 model.

## 11. Still open for Avinay's review

1. The §6 XML check on EAF (tree count, depth, split counts against Figs. E.2 / E.3).
2. A1–A7, in particular A1 (photon origin; 8.6 % of BNB positive rows change) and A6 (primary π⁰; +5.9 % negatives).
3. The SBND x cut, and whether to keep one candidate per event.
4. `kine_pio_flag`: train with the stored value (proposed), with the legacy control fed 0.
5. Whether to keep NC Δ-spill pileup negatives (49 of 952 in the census).
6. Which in-time-cosmic sample to use for "other", and who produces it.
