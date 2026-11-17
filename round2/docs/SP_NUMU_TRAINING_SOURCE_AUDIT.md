# Single-photon `numu` BDT: training definition recovered from the Yandel thesis

Date: 2026-11-17 (Aurora, `aurora-uan-0010`). Scope: a source audit and a dry-run class census. **No BDT was trained.**
Nothing outside Avinay's areas was written. Haiwang's aurora-r2 CAFs and Xuyang's repository were only read.

Conventions are those of `YANDEL_THESIS_SP_BDT_TRAINING_SOURCE_AUDIT.md`:
- "p. N" is the printed page; PDF page = printed + 13.
- Confidence labels: SOURCE-ESTABLISHED, THESIS-IMPLIED, NOT STATED.

Sources:
- **Thesis.** sha256 `0ad56e36…1465`, now outside git at `$SP_WORK/thesis_audit/qt6rq082dr.pdf`.
- **EAF XML audit.** Branch `analysis/sp-bdt-thesis-xml-compatibility-20261117`, commit
  `0148e879ae44c0c61f0fb7874079734a4cead3fa` (`tables/sp_bdt_xml_audit/numu_variable_splits.csv`, `summary.json`).
  Read with `git show`; not merged.

## 1. Search

The keyword scan covered all 308 pages for: νμ / numu / "muon neutrino", "charged current" / CC νμ, muon rejection,
Michel, training sample, Fig. 5.x, Appendix E, 300 trees / depth, and XGBoost.

The SP νμ BDT is described in only four places:
- §5.2.2, p.128, with Fig. 5.7 on p.129;
- the shared procedure on p.127;
- Appendix E.1, pp.278–280 (parameters, then Fig. E.1);
- the cut tables (pp.141–142) and the νμ CC sideband (pp.148, 152).

"Michel" appears only in reconstruction contexts:
- the `lem_*` low-energy-Michel inputs (p.109, p.137);
- the stopped-muon tagger (pp.103–104);
- a comparison table of νe selections (p.117).

It never defines a training class.

## 2. Target

**SOURCE-ESTABLISHED**
- **Purpose.** "The first BDT is made to remove the remaining νµ CC background, which includes νµ CC events with and
  without a π0 in the final state" (p.128).
- **Statistics.** "trained on 97,580 νµ CC events and 24,936 signal events and uses 73 variables" (p.128).
- **Classes.** The Fig. 5.7 caption (p.129) reads: "Background includes only νµ CC events. Signal includes events fitting
  the inclusive single photon signal definition".
- **Shared procedure (p.127).** Signal is the shared 24,936 / 25,389 sample. Backgrounds are "split up by type and used
  only on the relevant BDT". Every training event passed the preselection first.
- **Most important inputs.** The Wire-Cell νμ CC inclusive BDT score ([62, 68]; "numu score", Fig. 5.12, p.135, which
  is the score made for the Wire-Cell inclusive νe LEE analysis) and the "bad reconstruction 3" variables (p.128).
- **Code flags.** `cuts.h` @ `0100d4b6:2852–2853`: `SPnumuCCBkg` and `SPnumuCCpi0Bkg` = not signal, |`truth_nuPdg`| = 14,
  CC, `truth_vtxInside`, and `truth_Npi0` = 0 / > 0 (plus completeness).

**THESIS-IMPLIED**
- **νμ CC events that fit the signal are positive.** νμ CC 1γ with μ below 100 MeV is a signal category (p.122).
- **The negatives are inside the 3 cm FV.** Out-of-FV events belong to the Other BDT, and the per-BDT counts sum
  exactly to 263,120.
- **The classes are truth-defined.** The thesis categories are MC truth categories, as are the code flags.

**NOT STATED**
- which MC files supplied the 97,580 events ("Runs 1 and 3 MC samples", p.127);
- whether an enriched νμ CC sample was used. None is needed: νμ CC is about 67 % of events after preselection (p.127);
- event or class weights, a validation set, early stopping;
- the definitions of the two `_calc` inputs;
- how `numu_score` / `numu_1_score` were produced for the training events, beyond "the Wire-Cell νµ CC inclusive BDT
  score". The thesis gives no separate chain, which implies the standard Wire-Cell ntuples.

## 3. Training procedure

| quantity | SP numu | source page | confidence |
|---|---|---|---|
| positive class | inclusive single-photon signal, all 5 categories | 121–122, 127, Fig. 5.7 | SOURCE-ESTABLISHED |
| negative class | νμ CC, with and without π⁰ | 128, Fig. 5.7 | SOURCE-ESTABLISHED |
| νμ CC events that fit the signal | trained as signal | 122 | THESIS-IMPLIED |
| FV requirement on the negatives | in the 3 cm FV | 129; `cuts.h:2852–2853` | THESIS-IMPLIED (+ code) |
| truth or reconstruction defined | truth categories | 121–122, Fig. 5.7 | THESIS-IMPLIED |
| training signal / background | 24,936 / 97,580 | 127, 128 | SOURCE-ESTABLISHED |
| test signal / background | 25,389 / NOT STATED | 127 | partly NOT STATED |
| samples | Runs 1 + 3 general BNB + single-photon-enhanced MC (signal); Runs 1 + 3 MC (background) | 127 | SOURCE-ESTABLISHED |
| preselection | generic ν selection; reco vertex 5 < x < 250 cm; ≥ 1 shower > 20 MeV, the same as the siblings | 125, 127 | SOURCE-ESTABLISHED |
| split | shared Wire-Cell training list; otherwise even subrun = train, odd = test | 127–128 | SOURCE-ESTABLISHED |
| weights, validation set, early stopping | NOT STATED | — | NOT STATED |
| inputs | 73; list and importances in Fig. E.1 | 128, 280 | SOURCE-ESTABLISHED |
| `max_depth`, `n_estimators` | 5, 300 | 278 | SOURCE-ESTABLISHED |
| other XGBoost parameters | lr 0.1, `binary:logitraw`, colsample 1 / 0.5 / 0.5, subsample 0.8, gamma 0.2, seed 1, eval [auc, error] | 278–279 | SOURCE-ESTABLISHED |
| pure / efficient cut | 0.4 / 0.1 (Tables 5.5 / 5.4) | 142 | SOURCE-ESTABLISHED |
| cut grid | −2.0 to 2.0, step 0.1 | 141 | SOURCE-ESTABLISHED |
| score convention | log10-odds (`bdt.h`); not stated in the thesis | — | code |
| sideband | νμ CC sideband = preselection + score < 0.1 (27.1 % efficiency, 76.4 % purity for νμ CC) | 148, 152 | SOURCE-ESTABLISHED |

## 4. Thesis versus frozen XML

**Fig. E.1 metric.** The figure (p.280) plots "F score", "the sum of how many times the feature is split on" (caption,
and the text on p.279). That is XGBoost's `weight` importance, i.e. the split count. Its bottom panel is "Gain", the
average gain per split, and is not compared here.

**Method.**
1. Transcribe the 73 printed labels.
2. Measure each bar's length independently. The axis scale comes from the image's own gridlines, not from the XML.
3. Compare with `numu_variable_splits.csv` at `0148e879`.

| item | thesis | frozen XML (EAF) | result |
|---|---|---|---|
| trees | 300 (p.278) | 300 | MATCH |
| depth | 5 (p.278) | 5 (every tree) | MATCH |
| inputs | 73 (p.128) | 73, all split on | MATCH |
| per-feature F score = split count | Fig. E.1 | `numu_variable_splits.csv` | **71 EXACT MATCH, 2 NAME ALIAS ONLY** (`shw_sp_n_20br1_showers_calc` 122, `shw_sp_vec_mean_dedx_calc` 161), 0 MISMATCH, 0 NOT READABLE |
| total splits | 8,103 (sum of Fig. E.1) | 8,103 | MATCH |
| printed labels vs bar lengths | 73 / 73 agree | — | consistent |
| pure cut | 0.4 (Table 5.5) | `cuts.h` `is_singlephoton_sel` | MATCH |
| score convention | grid −2 to 2 (p.141) | `log10((1+v)/(1−v))` | CONSISTENT |

**Verdict: THESIS/XML MATCH — TARGET ACCEPTED.** The frozen `single_photon_numu_bdt_final.xml` (sha256 `5886affb…`) is
the model described in the thesis.

The per-feature comparison is outside git, in `$SP_WORK/thesis_audit/appendixE/`:
- `numu_thesis_vs_xml.csv`;
- the transcription `fig_E1_numu_fscore_transcription.csv`.

## 5. Upstream dependence

The EAF audit gives:
- `numu_score` (XML index 72): 623 splits, 7.7 %, rank 1. It is at the root of 41 of 300 trees and used in 193.
- `numu_1_score` (XML index 71): 311 splits, 3.8 %, rank 3. It is at the root of 23 trees.
- Together they hold **11.5 %** of all splits.

Fig. E.1 shows the same: `numu_score` is the top feature by F score.

Both scores come from the νμ chain. Xuyang plans to retrain the νμ CC BDT "after the nu_e one is fixed"
(`xning/bdt-comm@2c499b9` `PLAN.md:86`). A retrained `numu_score` therefore moves SP numu's most-used input.

## 6. Aurora data readiness

| requirement | available now? | sample | additional sample needed? |
|---|---|---|---|
| inclusive single-photon signal, all categories | yes | `aurora-r2-ncdr` (NC Δ 1γ) + `aurora-r2-bnb` (NC π⁰ → 1γ, out-of-FV, νμ CC 1γ) | no |
| νμ CC background, no π⁰, in FV | yes | `aurora-r2-bnb` (+ NC Δ-spill pileup) | no |
| νμ CC background with π⁰, in FV | yes | `aurora-r2-bnb` | no |
| truth: \|pdg\|, CC/NC, vertex, primary π⁰, primary μ KE | yes | `T_truth_nu`, `T_truth_pf` | no |
| 73 inputs incl. `numu_score`, `numu_1_score` | yes (shipped νμ models) | `T_tagger` | the Round-2 values need Xuyang's frozen νμ chain |
| an enriched νμ CC sample | not required | — | **no**: none is stated, and BNB CV gives about 39k preselected νμ CC rows |

## 7. Class census (dry run, no training)

These are the same census tables as for ncpi0: `aurora-r2-ncdr` files 0–2999 and `aurora-r2-bnb` files 0–1199.
- Spec: `specs/single_photon_numu_training_spec_v0.1.yaml`.
- Tool: `tools/sp_class_census.py`.
- Output: `$SP_WORK/census_tables/census_numu.json` (sha256 `3141da36…01f4`), which records the spec sha256 `c7970ed2…` and the code sha256s.

| | NC Δ (3,000 files) | BNB (1,200 files) |
|---|---:|---:|
| preselected rows (events) | 2,835 (2,809) | 6,748 (6,709) |
| **positive rows (events)** | **2,599 (2,599)** | **257 (257)** |
| **negative rows (events)** | **59 (58)** | **3,937 (3,917)** |
| negative: νμ CC / νμ CC π⁰ | 35 / 24 | 2,332 / 1,605 |
| negative by primary π⁰ count: 0 / 1 / 2 / ≥ 3 | 35 / 23 / 1 / 0 | 2,332 / 1,455 / 132 / 18 |
| excluded rows | 177 | 2,554 |
| events with both classes | 14 | 1 |
| events with ≥ 2 negative rows | 1 | 20 |
| preselected candidates per event: 1 / 2 | 2,783 / 26 | 6,670 / 39 |
| split train / validation / test, negative | 22 / 8 / 29 | 1,478 / 495 / 1,964 |
| rows with a non-finite input | 0 | 0 |
| `shw_sp_filled == 1`: positive / negative | 99.5 % / 94.9 % | 99.2 % / 95.8 % |
| true νμ CC background ν with a preselected candidate | 59 / 231 | 3,933 / 21,092 (19 %) |

The positive class is identical to ncpi0's: same rows, same categories.

**Full-list estimate** (linear by file count; indicative only):

| | positive | negative |
|---|---:|---:|
| total | ≈ 17,800 | ≈ 39,300 (99 % BNB) |
| even subrun (train + validation) | ≈ 9,060 | ≈ 19,700 |
| MicroBooNE training sample | 24,936 | 97,580 |

The even-subrun negatives are about 20 % of MicroBooNE's count. That is ample for development. A final model would
gain from the full BNB list in the refresh, which is already required; no enriched sample is required.

## 8. Gate

**SP numu: target SOURCE-ESTABLISHED; THESIS/XML MATCH — TARGET ACCEPTED; spec v0.1.0
`READY_FOR_DEVELOPMENT_TRAINING`.** Development training uses aurora-r2 only, and nothing is trained until Avinay has
reviewed this.

Final training waits for:
- Xuyang's frozen νμ chain (`numu_score`, `numu_1_score`);
- the DL vertex;
- the training refresh;
- the exporter.

The Round-2 decision is in `SP_BDT_ROUND2_FREEZE_ORDER.md`.
