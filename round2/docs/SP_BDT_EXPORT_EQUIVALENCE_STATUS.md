# Single-photon BDT export: XGBoost JSON → TMVA Grad XML, equivalence status

Date: 2026-11-17. This is infrastructure only. The two development models are used as **fixtures**: they are
`ROUND1_DOMAIN_DEVELOPMENT_DO_NOT_DEPLOY`, were not retrained or changed, and no threshold was chosen. The legacy cuts
and score quantiles below are only places where a decision could flip.

## 1. What was built

| file | what |
|---|---|
| `sp_retrain/export_tmva.py` | The exporter. It takes a native XGBoost 3.4.1 JSON and writes `<name>.xml` (TMVA `BDT::BDT`, `BoostType=Grad`, `<Weights AnalysisType="1">`), plus `<name>.json` (a copy of the native model), `<name>.features.json` (the ordered XML names ↔ table columns ↔ CAF branches) and `<name>.sha256`. |
| `tools/export_equivalence_check.py` | Rebuilds the development test fold, exports, reads the export back with `sp_retrain.tmva_grad.GradForest` and compares (§2). |
| `tests/test_export_tmva.py` | 5 tests on a tiny synthetic `binary:logitraw` model: margin and per-tree leaves, routing at exact thresholds, base-margin refusal and fold, refused objective / names / unsafe text, order guard, sidecar hashes. |
| `validation/sp_export_equivalence_dev_fixtures.json` | Aggregates and the 20 rows closest to each fixture threshold. Per-row outputs and the exported files are in `$W/export_equivalence/{numu,ncpi0}/`, outside git. |

**Layout.** The output copies, element for element, the inherited MicroBooNE single-photon XMLs (`Creator =
xgboost2TMVA`) and the toolkit's `numu_scalars_scores_0923.xml`. Those are the files TMVA::Reader (MicroBooNE
`bdt_convert`; SBND `UbooneNumuBDTScorer` with `Float_t` bindings) and the toolkit's `TmvaGradForest` already read in
production. Where this differs from the plan in `SP_BDT_DEPLOYMENT_EXPORT_AUDIT.md` §2, the inherited layout wins:

| plan in the audit | what the exporter does | why |
|---|---|---|
| `Type="F"` | `Type="D"` | Every inherited file has `D` with float bindings; `F` is available as `var_type='F'` |
| leaf `nType=±1` | leaf `nType="-99"` | As in the inherited files; both readers stop at any `nType != 0` |
| `<Spectators>`, `<Classes>`, `<Transformations NTransformations="0"/>` | not written | Not in the inherited files; a missing element means no transformations to both readers |

The writer also adds an `NTrees` option and provenance `<Info>` entries to the header, which neither reader uses:
- creator and exporter version;
- spec id, version and campaign, and `Deployable=false`;
- the training commit;
- the source-JSON sha256 and the feature-list sha256.

**Node and base-margin semantics.**
- *Splits.* XGBoost sends `x < t` to the yes-branch and TMVA goes right when `x >= Cut`. So every split is written
  `cType="1"`, `Cut = t`, with the left child being XGBoost's yes-branch.
- *Floats.* All floats are written `%.9g`, so float32 → text → `atof` → `Float_t` round-trips exactly.
- *Base margin.* Under `binary:logitraw`, XGBoost 3.4.1 adds `base_score` to the margin **unchanged**.
  - We measured this on both fixtures: rewriting `base_score` to 0.5 in a temporary copy shifts every margin by
    0.5 ± 1e-5 (float32 rounding).
  - Our SP specs use `base_score = 0`, so nothing extra is exported.
  - A nonzero offset is refused unless `fold_base_margin=True` is given. That option appends one constant
    single-leaf tree; on both fixtures it reproduced `0.5 + leaf sum` exactly in double.
- *Correction to an existing doc.* `SP_BDT_DEPLOYMENT_EXPORT_AUDIT.md` (§1 item 3 and §2 item 1) says the offset
  "disappears with `base_score = 0.5` under `binary:logitraw`". That is wrong for 3.4.1: 0.5 *is* an offset of
  +0.5. The score-scale doc and the dev specs already state the correct rule.

**Missing values.** XGBoost sends NaN along `default_left`, and TMVA returns −999. Policy: rows with a non-finite input
are excluded from training and from offline scoring. In production, −999 maps to the minimum score (−16.256), so the
event is rejected.

## 2. Results on the development fixtures (Aurora test fold, rows rebuilt and checked equal to the stored ones)

| check | SP numu (300 trees, depth 5, 73 inputs) | SP ncpi0 (400 trees, depth 6, 45 inputs) |
|---|---|---|
| test rows (positive / negative) | 28,396 (9,012 / 19,384) | 13,467 (9,000 / 4,467) |
| XML forest sum vs the native leaves summed in double (exporter exactness) | **0 exactly** | **0 exactly** |
| native XGBoost margin vs the same leaves summed in float32, tree order | 0 exactly | 0 exactly |
| max \|native margin − XML sum\| (float32 vs double accumulation) | 1.24e-5 (25 rows > 1e-5, all \|m\| ≥ 8.17; max relative 1.9e-6) | 5.7e-6 |
| max \|tanh(margin) − TMVA response\| | 1.06e-6 | 1.27e-6 |
| max \|production log10-odds − 2·margin/ln 10\| | 1.08e-5 | 5.0e-6 |
| per-tree leaf identity | 8,518,800 / 8,518,800 | 5,386,800 / 5,386,800 |
| visited splits in real test rows with x == Cut exactly (routed identically) | 1,391,006 | 671,004 |
| decision flips at the fixture legacy cut (0.4 / −0.05) | **0** | **0** |
| flips at 5 quantile cuts placed midway between adjacent scores | **0** (smallest row-to-cut gap 1.3e-5) | **0** (smallest gap 5.2e-5) |
| adversarial cut placed exactly on the median row's score | 0 flips | **1 flip** (the row on the cut) |
| equality boundary: 400 sampled splits, 3 rows each forced to x = Cut | 1,200 / 1,200 identical in every tree; all routed right in both | 1,200 / 1,200, same |
| ±FLT_MAX in one input, 400 rows | 0 leaf mismatches | 0 leaf mismatches |
| NaN, synthetic (50 rows) | XGBoost finite (default direction); TMVA −999 → score −16.256 on 50 / 50 | same |
| NaN, real excluded rows | none | 34 rows (`shw_sp_pio_1_mass`, `kine_pio_*`): XGBoost finite, TMVA −999 on 34 / 34 |
| order guard (first two names swapped) | refused | refused |
| `binary:logistic` objective; unfolded base_score 0.5 | refused; refused | refused; refused |

**Verdict.**
- The exporter is exact: the XML holds XGBoost's leaves and routing bit for bit.
- The only difference left is arithmetic. XGBoost sums the leaves in float32 and TMVA sums them in double. The
  difference is at most about 2e-6 relative.

**Consequences for the hand-off rules.**
1. The absolute `≤ 1e-5` per-row rule in `SP_BDT_DEPLOYMENT_EXPORT_AUDIT.md` §4 cannot hold for large margins: SP numu
   reaches 1.24e-5 at |m| ≈ 9. The check therefore uses two conditions:
   - an exactness test against the double leaf sum;
   - `|Δ| ≤ 1e-5 · max(1, |m|)`.
2. A cut placed on, or within about 1e-5 of, a row's score can flip that row; the adversarial case shows it.
   - The final threshold must be placed between distinct validation scores.
   - The hand-off must show zero flips on a fixed test set.
   - The hand-off must list the rows within 1e-4 of the cut.

## 3. Not yet verified

- ~~**C++ readers.**~~ **VERIFIED the same night** (`SP_BDT_WCL1116_DEVELOPMENT_RESULTS.md` §12;
  `validation/cpp_export_equivalence_*.json`).
  - Method: `cpp/sp_export_regression.cxx` in the SL7 WCT 0.38.0 container on a compute node.
  - Result on both Round-1 fixtures here and the 4 WCL1116 development models, 3,310 rows each (holdout,
    exact-threshold, NaN and ±FLT_MAX rows):
    - `TMVA::Reader` is bit-identical to the toolkit `TmvaGradForest`;
    - both are within 4.4e-16 of Python `GradForest`;
    - NaN gives −999; the swapped order is refused; 0 flips.
  - A toolkit-side doctest would still be the natural permanent home for this check; that is optional now.
- **Production scorer.** No production scorer for single-photon scores exists, so no end-to-end toolkit check has
  been done.
- **Fixtures only.** Only the development fixtures were exported. The final models will be exported only after
  their specs are `READY_FOR_FINAL_TRAINING`; the equivalence check is then rerun on the final test fold.
