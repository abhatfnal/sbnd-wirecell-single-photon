# Single-photon BDT score scale, and what is needed before a production threshold

Date: 2026-11-17 (Aurora). This applies to the development models of `SP_BDT_DEVELOPMENT_TRAINING_SUMMARY.md` and to
every future SBND single-photon model. **This phase chooses no threshold.**

## 1. The legacy production score

MicroBooNE production (`wcp-uboone-bdt-eyandel@0100d4b6`, `inc/WCPLEEANA/bdt.h`, `cal_single_photon_*_bdts_xgboost`)
stores

  `score = log10((1 + v) / (1 − v))`, with `v = TMVA::Reader::EvaluateMVA("MyBDT")`.

For a `BoostType=Grad` forest, TMVA returns `v = 2 / (1 + exp(−2F)) − 1 = tanh(F)`. Here `F = Σ_trees boostWeight ·
res(leaf)`, and every frozen single-photon XML has `boostWeight = 1` (EAF audit `0148e879`). Since
`(1 + tanh F) / (1 − tanh F) = exp(2F)`, the stored score is exactly

  `score = 2F / ln 10 ≈ 0.8686 · F`.

The legacy cuts 0.4 / 0.2 / −0.05 / −1.0 (thesis Table 5.5) apply to that score. TMVA returns −999 when an input is
NaN, and such a row fails every cut.

## 2. What the development models produce

Development models are XGBoost 3.4.1 with `objective = binary:logitraw` (dev specs `…_dev_round1_domain_v1.yaml`):

- `Booster.predict(d)` and `Booster.predict(d, output_margin=True)` are identical. `logitraw` applies no transform
  (checked on every test row). The output is the **raw margin** `m`.
- `m = base_margin + Σ_trees leaf`. **Under `binary:logitraw`, XGBoost 3.4.1 uses `base_score` directly as the base
  margin.** A smoke test with `base_score = 0.5` gave `m − Σ leaf = 0.5000`; `binary:logistic` with 0.5 gives 0.
  - The development specs therefore set `base_score = 0.0`, which makes `m = Σ leaf` exactly. Measured on 500 test rows
    of each trained development model, `max |m − Σ leaf|` is 5.2e-6 (numu) and 4.7e-6 (ncpi0), float32 rounding of the
    leaf dump. The saved models record `base_score [0E0]`.
  - This was fixed before the development training.
- The training loss is the logistic loss on `m`, so `m` is the log-odds of the training-sample class mix, `p = σ(m)`.
  Natural sample proportions are used, so `p` is not a physical purity.
- **XGBoost's `error` metric under `logitraw` counts `m > 0.5` as positive, not `m > 0`.** It equals our "error at
  margin > 0.5" exactly. The reports quote both. The diagnostic classification error is at `m > 0` (`p = 0.5`).

**None of these is the production score.** The native margin, the probability `σ(m)`, the TMVA response `v`, and
the production `log10((1+v)/(1−v))` are four different numbers.

**Legacy controls (AURORA DEVELOPMENT, NOT OFFICIAL).** The verified legacy XMLs are scored with `sp_retrain.tmva_grad`:
`v` = TMVA `EvaluateMVA` = `tanh(raw)`, then the production score once. On the development test rows that score equals
`2·raw / ln 10` to 2e-8 (numu) and 1e-14 (ncpi0), as §1 states. The legacy historical cuts (0.4, −0.05) are applied
to that score only.

To compare a development model with a legacy cut, the comparison uses **ROC-equivalent diagnostic points**: the
development-margin threshold at the legacy signal efficiency, or at its background acceptance. It never applies 0.4
or −0.05 to the native margin. The development margins at those points (numu 1.32 / 0.43, ncpi0 2.36 / 1.83) are not
Round-2 cuts.

## 3. The expected chain, a hypothesis to be validated

Suppose an exporter writes every XGBoost leaf value into the TMVA `res` of the same node, with `boostWeight = 1`, the
same cut values and no base offset. Then `F = m`, `v = tanh(m)`, and the production score is `2m / ln 10`.

Under that hypothesis, a legacy cut `c` on the production score corresponds to a native margin `c · ln 10 / 2`. For
example, 0.4 → 0.4605 and −0.05 → −0.0576.

This is **not established**:
1. **No exporter exists.** No XGBoost → TMVA writer exists in the toolkit, in Haiwang's area or here
   (`SP_BDT_DEPLOYMENT_EXPORT_AUDIT.md`).
2. **The node semantics must be proven.** XGBoost sends `x < cut` to the "yes" child and NaN to its learned default
   direction. TMVA's `GoesRight` is `x >= cut` (inverted when `cType == 0`) and has no missing value. Equality and NaN
   behaviour must be shown to agree. Rows with non-finite inputs are excluded from development.
3. **The base offset must be handled.** `base_score = 0` removes it for our models. The legacy MicroBooNE models'
   treatment is unknown; the EAF audit notes the "other" first-tree leaves.
4. **float32.** XML cut and `res` values are written to finite precision. The equivalence test must show zero decision
   flips at the chosen threshold.

## 4. Required before any production threshold

1. An XGBoost JSON → TMVA BDT XML exporter: `BoostType=Grad`, `NTransformations=0`, variables in feature-list order.
2. An equivalence test on Aurora development rows:
   - `atanh(EvaluateMVA)` equals the native margin within 1e-5;
   - the production `log10((1+v)/(1−v))` equals `2m / ln 10`;
   - zero decision flips at the threshold;
   - Python `tmva_grad` ↔ toolkit bit-identical, as already done for νe.
3. **Final models only.** These are trained on the Round-2 training refresh after the vertex and upstream freezes, not
   these development models.
4. **A threshold procedure fixed in advance.** The thesis chose all four SP cuts jointly on a 4×4 grid maximising E×P²
   (pure) or S/√B (efficient), pp.140–142. A Round-2 working point needs the same joint scan over all retrained and
   kept models:
   - on an Aurora validation fold — **never the development test fold, never an official sample**;
   - with the final background mix and POT weights from production records.
5. The deployment route decided: toolkit scorer or offline score table. The production score convention is kept
   unchanged, so the EAF Round-1 source-faithful baseline (833 / 12,427) stays comparable.

The legacy MicroBooNE thresholds are cuts on MicroBooNE models. Even on a proven common scale, they do not carry over to
a retrained model.
