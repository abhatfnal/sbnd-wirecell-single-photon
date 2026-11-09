# Expected-yield and prediction plumbing (code ready; NO final number is claimed)

## Signal yield (`src/sbnd_single_photon/signal_yield.py`)
Truth class t in {0p, 1p, ≥2p} and reco channel r in {1γ0p, 1γ1p, ≥2p} are **different variables**; the measured proton migration is large (Phase 3/4), so a reco-channel yield must use the full truth → reco migration:

* R_t(V) = N_signal_truth(V, t) / POT_signal (the official truth sample; region V is a parameter; wc.invalid and never-arrived events stay in N_signal_truth)
* ε(t → r) = N_selected(V, t → r) / N_signal_truth(V, t)
* **N(r; P) = P · Σ_t R_t(V) · ε(t → r) = (P / POT_signal) · Σ_t N_selected(V, t → r)**, total = Σ_r, per truth class = Σ_r.
* Statistical covariance (signal sample only): Cov[N(r), N(r')] = (P/POT_signal)² Σ_t n_t (δ_rr' ε_tr − ε_tr ε_tr') (multinomial per truth class).
`naive_diagonal_yield` (truth-0p × reco-0p only) exists solely so a test shows it differs. Tested: migration vs diagonal, identities, covariance, region dependence, refusal when more is selected than generated for a class. The efficiency inputs come from the signal report (`signal_pipeline.signal_report`, `selected_truth_to_reco`), the truth rates from `tables/official_signal/denominators.json`.

## Beam-neutrino background (`tables/official_signal/background_rate_model.json`, `scripts/build_prediction_model.py`)
From the validated Phase-4 table, selected **non-signal** CV events only (649 = 14 signal-like + 635 background + 0 mixed; the natural NC Δ → Nγ events are removed from B). Rates per 1e20 POT (ΣTotalPOT 2.71940e19; Poisson statistical only; no cosmic-only component; the dedicated nueCC sample is NOT included):

| reco channel | selected non-signal events | rate / 1e20 POT |
|---|---|---|
| 1γ0p | 310 | 1140 ± 65 |
| 1γ1p | 230 | 846 ± 56 |
| ≥2p (diagnostic) | 95 | 349 ± 36 |

## Prediction object (`src/sbnd_single_photon/prediction.py`)
Components `S_NCDELTA` (truth rate known, efficiency **pending** the official Wire-Cell sample), `B_BNB_NEUTRINO` (known), `B_COSMIC` (beam-off **shape** only: selected 4 / 2 / 0; absolute scale **unresolved**), `DATA` (open beam-on raw selected 39 / 27 / 11). The object **refuses to produce the total predicted background, purity, S/B and significance** while any needed component is not `known`, raising `UnresolvedNormalizationError` (never substituting zero); `tables/official_signal/prediction_status.json` records the four refusals. The one open item behind `B_COSMIC` is the single question in `DATA_EXPOSURE_NORMALIZATION.md` section 0.
