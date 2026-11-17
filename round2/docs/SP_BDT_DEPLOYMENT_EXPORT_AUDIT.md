# What Round-2 production can consume: single-photon BDT loader, format, export and the equivalence test

Date: 2026-11-17. Source audit only; no production code was changed.

## 1. What exists today

| component | where | model format | lookup | feature order | score |
|---|---|---|---|---|---|
| **SBND single-photon scorer** | **does not exist.** At the aurora-r2 pin `a2785870` no component books a `single_photon_*` XML, and no merged-CAF branch holds a single-photon score | — | — | — | — |
| SBND νμ / νe scorers (pattern for a new one) | `root/src/UbooneNumuBDTScorer.cxx`, `root/src/UbooneNueBDTScorer.cxx`; config `cfg/pgrapher/experiment/sbnd/clus.jsonnet` (`numu_bdt_scorer`, `nue_bdt_scorer`, near line 2915) | TMVA BDT XML. The final models are `xgboost2TMVA` conversions (`BoostType=Grad`, regression leaves, no transforms); level-1 models are TMVA AdaBoost with transforms | config keys `*_weights_xml`, `numu_xgboost_xml`, `nue_xgboost_xml` = `'uboone/weights/<file>.xml'`, resolved by `wc.resolve` through `WIRECELL_PATH` (wire-cell-data) | fixed by the order of `AddVariable` calls in C++. The fast reader `TmvaGradForest` (`root/inc/WireCellRoot/TmvaGradForest.h`) refuses a file whose variable names or order differ, or that has transforms or a boost type other than Grad | `log10((1+v)/(1−v))`, v = TMVA output; `nue_score = −15` when `br_filled == 0`. The `fast_xgb_forest` flag selects `TMVA::Reader` (default) or `TmvaGradForest`, which is bit-identical |
| MicroBooNE single-photon loader (the reference) | `wcp-uboone-bdt-eyandel@0100d4b6` `apps/bdt_convert.cxx`; functions in `inc/WCPLEEANA/bdt.h` | TMVA BDT XML, Grad, 300 trees (the inherited `*_bdt_final.xml`) | `BookMVA("MyBDT", "weights/single_photon_<x>_bdt_final.xml")`, relative to the working directory | `AddVariable` order = XML `<Variables>` order | `log10((1+v)/(1−v))`. Evaluated for every entry with no gate; `kine_pio_flag` forced to 0 |
| SBND baseline_v0 offline scorer | this repo, `analysis/microboone_1gamma_v0/score_microboone_bdts.py` | the same XMLs | hard-coded Eagle paths | XML order | **tanh only**, with thresholds wrongly applied in tanh space; routes `x <= cut` to the left (TMVA sends `x == cut` right); skips multi-candidate events. See the erratum in `SP_BDT_DEPENDENCY_AND_TARGET_AUDIT.md` §5 |
| this package | `round2/sp_retrain/tmva_grad.py` | TMVA BDT XML, Grad | path argument | checks the names and order against the caller | raw, tanh (EvaluateMVA, −999 on NaN), log10-odds. **Bit-identical to the toolkit's stored `nue_score` on 423/423 candidates** from 64 aurora-r2 files (`round2/validation/`) |

**TMVA XML or native XGBoost JSON?** The toolkit reads only TMVA XML. Native XGBoost JSON is read by no production
component. Equivalence between the two is not automatic; three differences must be handled:
1. Missing values. XGBoost sends NaN along `default_left`, while TMVA returns −999 for any NaN input.
2. Float precision. XGBoost accumulates leaf values in float32, while TMVA sums in double.
3. Base score. XGBoost may carry a fitted `base_score` that a TMVA XML cannot hold. This disappears with
   `base_score = 0.5` under `binary:logitraw`, as Xuyang's spec_v1 already requires.

**Exporter:** **none exists.** Nothing in the toolkit (`xgboost2TMVA` appears only in comments), in Haiwang's `tools/` or
production repo, or in Xuyang's `bdt-comm` converts an XGBoost model to TMVA XML. Xuyang's step 7 plans JSON plus Python
inference only. Her wcgpu notes say "We never built or validated such a converter".

## 2. The minimal exporter (to build before any final freeze)

`export_tmva_grad.py`: native XGBoost JSON → TMVA BDT XML that both `TMVA::Reader` and `TmvaGradForest` accept.

1. **Refuse** anything other than `gbtree` with numerical splits and objective `binary:logitraw` with
   `base_score == 0.5`, which gives zero margin offset. Otherwise write the offset as one single-leaf tree.
2. **Header.**
   - `<MethodSetup Method="BDT::BDT">`.
   - `<GeneralInfo>`: creator, exporter version, training-spec id and version, training commit, sha256 of the source JSON.
   - `<Options>`: `BoostType=Grad`, `NTrees`.
   - `<Variables NVar=n>`: the feature-list names in order, `Type="F"`. Use the XML expression names, e.g. `reco_nuvtxY`
     and `numu_cc_3_track_length`.
   - `<Spectators NSpec="0"/>`, `<Classes>`, `<Transformations NTransformations="0"/>`.
   - `<Weights NTrees=k AnalysisType="1">`.
3. **Nodes.**
   - XGBoost sends `x < t` left and `x >= t` right. That equals TMVA `cType = 1`, `Cut = t`.
   - Leaves get `nType = ±1` and `res = leaf value`; the XGBoost leaf already includes the learning rate.
   - `boostWeight = 1`.
   - Write every float with `%.9g`, so float32 → text → float32 is exact.
4. **Missing values.** No row with a non-finite input is trained on or scored. On production NaN gives −999, which maps
   to the minimum log10-odds, so the event is rejected. Training and evaluation must use the same rule.
5. **Sidecars.**
   - `<name>.features.json`: ordered names and source branches, copied from `round2/config/features`.
   - `<name>.json`: the native model.
   - `<name>.sha256`: hashes of all three files.

## 3. Production-side route (Haiwang's decision)

- **A. In the toolkit.** A new `UbooneSinglePhotonBDTScorer`.
  - Runs after `numu_bdt_scorer` and `nue_bdt_scorer`, because it needs `numu_score` and the level-1 scores.
  - Binds the inputs per candidate in feature-list order, with `reco_nuvtxY` ← `kine_nu_y_corr` and the
    `kine_pio_flag` policy chosen in the training spec.
  - Evaluates with `TmvaGradForest`.
  - Writes `single_photon_{numu,other,ncpi0,nue}_score` to `T_tagger`. This needs a writer change, the merge schema
    rebuilt with `bin/make-schema.py`, and a new schema md5.
  - Config keys: `single_photon_<x>_xml`, resolved by `wc.resolve`.
  - Proposed location: `sbnd/weights/single_photon/`, not `uboone/weights/`, so SBND-trained files are never confused
    with the inherited MicroBooNE ones.
- **B. Offline.** Python post-processing of the merged CAFs with `sp_retrain.tmva_grad`, keyed by
  `(file_id, run, subrun, event, cand)`. This is the same choice Xuyang made for νe (bdt-comm decision #5). No toolkit
  rebuild is needed, but the scores are not inside the CAFs.

Route B is enough for Round-2 evaluation on EAF if Haiwang does not need the scores in production. Route A is needed if
the CAFs must carry the scores.

## 4. The regression test (HARD requirement before the large production)

| check | inputs | pass rule |
|---|---|---|
| training ↔ export | ≥ 10,000 candidates from the Aurora **test** fold of every development sample, all classes. Add edge cases: inputs set exactly to split thresholds (equality routing), integer-valued counts and flags, empty-list defaults, extreme values | `|raw_xgboost − raw_xml| ≤ 1e-5` per row; stored log10-odds `|Δ| ≤ 1e-5`; **zero decision flips** at the operating threshold; the 20 rows closest to the threshold listed |
| Python scorer ↔ toolkit | the same rows through `sp_retrain.tmva_grad` and through the C++ scorer (`TMVA::Reader` and `TmvaGradForest`) | bit-identical, as already shown for νe (423/423) |
| order guard | the XML with two variables swapped | refused by both readers |
| missing-value guard | rows with a NaN input | not scored on the training side; −999 → minimum score on the production side; counted |
| end-to-end | a handful of events run through the Round-2 toolkit build | the stored single-photon score equals the offline score bit for bit |

Toolkit side: a `doctest_single_photon_scorer.cxx` beside `root/test/doctest_tmva_grad_forest.cxx`. Package side: a
pytest that reads the exported files and the fold's rows. Both results go into the handoff record.
