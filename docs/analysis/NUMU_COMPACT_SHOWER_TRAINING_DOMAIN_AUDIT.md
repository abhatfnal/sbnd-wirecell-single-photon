# Why does the frozen `numu` BDT reject compact, few-segment NC-Delta photon objects, and is that the intended MicroBooNE discrimination?

Date: 2026-11-11. Branch `analysis/ncdelta-numu-training-domain-audit-20261111`. **Characterisation only**: no threshold (numu 0.4), BDT weight, FV, proton policy, candidate policy, reconstruction or training was changed; the frozen baseline is identical (`configs/baseline_selection.yaml` sha256 `f3251b78...`, numu XML sha256 `5886affb...`, 0 decision flips on re-scoring). Roadmap item **Z**. Source / training-domain audit: `NUMU_TRAINING_DOMAIN_SOURCE_AUDIT.md`. Code `scripts/numu_compact_shower_audit.py`, `src/sbnd_single_photon/numu_audit.py`; tables `tables/numu_compact_shower_audit/` (summary `summary.json`); figures `plots/numu_compact_shower_audit/fig1-fig7`; row-level products and `metadata.json` in `$SP_DATA/numu_training_domain_audit/official_ncdelta/` (outside Git).

Tags: **SOURCE**, **MEASURED**, **INFERENCE**, **NOT ESTABLISHED**. Association language only; adjustments are descriptive standardisations (68 % bootstrap, 300 resamples, seed 20261111) and a logistic deviance bookkeeping, not causal models. Compactness bins were fixed in advance (not scanned): total tagger shower length < 20 cm ("compact"), fewer than 5 shower segments ("few-segment"); the Phase-12 pass-vs-fail medians were 21 cm and 5 segments.

## 1. Short answers

| question | answer |
|---|---|
| what physical / reco feature makes NC-Delta photons fail numu | a **short, few-segment tagger shower object** (total length < 20 cm: survival 29.3 % vs 73.5 %; < 5 segments: 24.8 % vs 73.1 %). Half of these objects (51 % of fragmented, 77-78 % of muon-/pion-typed controlling objects) are **fragmented or mis-typed pieces of the photon**; but compactness predicts rejection **also inside clean electron showers** (length < 20 cm: 42 %, >= 80 cm: 86 %) and after control for object class, anchoring, topology, energy and angle (-25 pp) |
| is it the intended behaviour of the MicroBooNE-trained discriminator | **cannot be established from the source** (no training documentation, no class labels, no comment on these variables). The direction is **consistent with** a muon-/Michel-like-object rejection (INFERENCE), and the BDT rejects exactly the objects the reconstruction typed as muon / pion (22-25 % survival) |
| evidence for an SBND / MicroBooNE domain mismatch | **none established, none excluded**: no MicroBooNE training distribution of any input exists, so a quantitative test is impossible |
| how much of the frozen-baseline inefficiency | numu failures are **29.8 %** of the total loss (3,031 of 10,178 signal-box events lost, 11,331 -> 1,153). Compact objects (< 20 cm) are 1,445 of them (**14.2 %** of the total loss; 47.7 % of the numu failures); compact or few-segment 17.0 %; non-clean photon objects 17.2 % (overlapping, association not additive) |
| what cannot be answered | the training sample, classes and input distributions; whether compactness was meant as a discriminator; whether MicroBooNE photons are longer / more segmented; why survival at fixed shape falls with photon energy (section 6) |

## 2. The frozen numu stage reproduced (Task 2; `numu_baseline_reproduction.csv`, `numu_input_pass_vs_fail.csv`)

Denominator **8,038** events reach numu (of 11,331 signal-box events; the baseline flag `A_bdt_evaluable` counts 8,034, the Phase-12 stage table holds 8,038 events with a numu score; the 4 extra are not separately investigated here), **5,007 pass (62.3 %, 68 % interval 61.8-62.8 %)**, 3,031 fail. Re-scored from the stored 73 inputs with the independent float32 evaluator: max |difference| 2.6e-9, **0 decision flips**, 0 non-finite inputs.

| group | n | survival |
|---|---|---|
| truth 0p / 1p / >= 2p | 3,937 / 3,450 / 651 | 62.1 % / 63.0 % / 59.4 % |
| clean signal-photon shower / non-clean photon object | 5,392 / 2,646 | **76.4 %** / **33.6 %** |
| object: clean e-shower / fragmented / muon-like / pion-like / proton-like / no relevant row | 5,366 / 1,619 / 303 / 333 / 68 / 336 | 76.4 / 36.0 / 25.1 / 22.2 / 30.9 / 43.8 % |
| vertex anchored (5 cm) / not anchored / no signal-matched candidate | 2,551 / 5,263 / 224 | 78.0 / 56.2 / 27.2 % |
| compact (< 20 cm) / not | 2,044 / 5,994 | **29.3 %** / **73.5 %** |
| few-segment (< 5) / not | 1,794 / 6,244 | **24.8 %** / **73.1 %** |

Pass versus fail medians (`numu_input_pass_vs_fail.csv`): number of shower segments **14 vs 5** (br1_1, br1_2 and br3_1 hold the same value in every event), total shower length **55.9 vs 21.5 cm**, main-segment length 31.7 vs 13.8 cm, `lem_e_charge` 226 vs 82, upstream `numu_score` -0.81 vs +0.12, `numu_1_score` -0.30 vs -0.09; the hol_1 / hol_2 inputs barely separate (SMD 0.2). Reco shower energy by bin: < 50 MeV 23 %, 50-100 43 %, 100-200 64 %, 200-400 82 %, >= 400 86 %. Controlling photon objects (`numu_controlling_object_classes.csv`): clean e-showers have median 14 segments / 59 cm, E_reco/E_true 0.90; fragmented 5 / 20 cm, 0.37; muon-like 4 / 12 cm, 0.45; pion-like 4 / 11 cm, 0.50; anchored fractions 42 / 7 / 19 / 7 %.

## 3. Compactness after descriptive control (Task 3; `numu_compactness_adjusted_difference.csv`, fig4, fig6)

The controlling photon object is the dominant object of the signal-matched candidate (98.6 % of events: the controlling numu candidate is the signal-matched one). The mu-like / pion-like controlling objects are signal-photon pieces **by construction** (of the 636 muon-/pion-typed controlling objects, 630 are signal-photon pieces, 2 are true signal protons, 4 have no truth-matched row: `numu_mu_pi_row_truth.csv`): the reconstruction typed fragments of the photon as muon or pion.

Compact (< 20 cm) minus not-compact survival, standardised over strata (weights = compact group):

| control | difference (pp) [68 %] | support kept |
|---|---|---|
| none | -44.2 [-45.4, -43.1] | 100 % |
| + photon object class | -25.4 [-27.2, -23.9] | 99.8 % |
| + object class + vertex anchoring | -25.4 [-27.2, -23.8] | 99.2 % |
| + class + anchoring + truth topology | -24.8 [-26.6, -23.4] | 95.0 % |
| + all above + true energy and angle bins | **-24.6 [-26.7, -22.7]** | 61.7 % |
| anchoring + topology + energy + angle, **no** class | -40.5 [-41.9, -39.2] | 95.1 % |

Few-segment (< 5): raw -48.3 pp, after object class -32.4, after everything -32.3 [-34.8, -31.1]. So **about 44 % of the raw compact-versus-extended difference is shared with the photon's reconstruction class** (fragmentation, mis-typing), and **a 25-32 pp association with compactness remains** after control. Object class itself partly encodes compactness (fragmented objects are 51 % compact), so this is bookkeeping, not separation of causes. Within **clean electron showers only** (`numu_clean_eshower_survival_vs_length.csv`): length < 20 cm 42.4 % (n = 491), 20-40 69.2 %, 40-80 80.2 %, >= 80 86.0 %.

## 4. Photon-state and kinematic dependence (Task 5; `numu_conditional_survival.csv`, `numu_driver_deviance_groups*.csv`)

Conditional survival (all events; clean-only and non-clean-only populations in the same table): true beam angle 59-64 % (flat); true conversion distance < 5 cm 59.2 %, 5-30 cm 64-65 %, >= 30 cm 65 %; vertex-to-edge distance 58-64 % (flat); truth 0p / 1p / >= 2p 62.1 / 63.0 / 59.4 %; Delta+ 63.5 % vs Delta0 61.4 %; proton origin (truth 1p) decay 63.6 %, FSI-created 62.2 %; vertex anchored 78.0 % vs 56.2 %; reco shower energy as above.

Grouped logistic deviance (descriptive; pseudo-R2 of each group alone, full model 0.259):

| factor group | alone | deviance increase when dropped from the full model |
|---|---|---|
| compactness / segmentation (segments, length) | **0.186** | **338** |
| reco shower energy | 0.162 | 60 |
| photon reco state (object class) | 0.133 | 159 |
| vertex anchoring | 0.046 | 146 |
| true kinematics (energy, angle, conversion, edge) | 0.005 | **264** |
| truth topology (0p/1p/>=2p, Delta charge) | 0.001 | 72 |

The loss is a **combination dominated by the reconstructed compactness / photon-state side** (alone 0.19 + 0.13 + 0.05, strongly overlapping), **not by topology** (alone 0.001; the marginal 0p / 1p survival is equal) **and not by the vertex or conversion geometry alone**; vertex anchoring is associated with +22 pp survival but it is a secondary factor (it also determines the object class). True kinematics add information only **conditionally** (264, next section). In clean electron showers alone the groups are compactness 200, kinematics 215, anchoring 119.

## 5. Energy dependence (Task 2 confirmation, Task 5; `numu_survival_vs_true_energy.csv`, fig3)

The earlier statement "independent of photon energy" holds **only as a marginal statement**: survival by true energy is 59.9 % (< 200 MeV), 62.4, 64.6, 62.4, 56.7 % (>= 600), Spearman with the outcome 0.02. But compactness rises strongly with energy (Spearman of segments / length with true energy 0.41 / 0.46) and **at fixed compactness survival falls with energy**:

| total length bin | < 200 MeV | 200-300 | 300-400 | 400-600 | >= 600 |
|---|---|---|---|---|---|
| < 20 cm | 38 % | 31 | 22 | 17 | 8 |
| 20-40 cm | 71 | 56 | 48 | 33 | 21 |
| 40-80 cm | 79 | 83 | 76 | 59 | 39 |
| >= 80 cm | 25 (n = 8) | 89 | 88 | 85 | 75 |

The marginal flatness is a **cancellation** between longer showers at higher energy (favouring acceptance) and a lower acceptance at fixed shape. The loss is therefore **compactness / segmentation-dependent at fixed energy, and not simply a low-energy-photon effect**; the conditional energy dependence is an association whose mechanism was not investigated (open question, section 8).

## 6. Upstream score and TreeSHAP (Task 6; `numu_shap_*.csv`, `numu_upstream_score_dependence.csv`, fig2, fig5)

Exact interventional TreeSHAP of the frozen margin (800 foreground candidates: 400 accepted + 400 rejected, seed 20261111; 300 mixed signal background; additivity error 2e-14; mean margin accepted +1.82, rejected -0.98, background 0.89, threshold 0.4236):

| group | upstream scores | shower quality br/lem | vertex / gap | track / hadron | calorimetry |
|---|---|---|---|---|---|
| rejected (n=400): mean phi | -0.75 | -0.72 | -0.17 | -0.08 | -0.08 |
| rejected & compact (n=198) | -0.57 | **-1.19** (51 % of the abs mass) | -0.20 | -0.08 | -0.08 |
| rejected & not compact (n=202) | **-0.93** (21 %) | -0.25 | -0.15 | -0.07 | -0.09 |
| accepted & compact (n=52) | **+1.05** | -0.39 | +0.02 | +0.10 | -0.04 |
| accepted & not compact (n=348) | +0.45 | +0.43 | +0.08 | +0.05 | -0.01 |

Two routes: **compact rejected objects are rejected by the shower-quality inputs** (largest single inputs: `lem_e_charge` -0.52, `br1_2_n_shower_segs` -0.42, `br3_1_n_shower_segments` -0.38, `br1_1_n_segs` -0.37 -- the last three are the same number in every event, so the model weight on "segment count" is split over three inputs); **extended rejected objects are rejected through the upstream `numu_score`** (-0.90). A compact object that is accepted is rescued by a favourable upstream score (+1.05). The upstream score is **not a compactness proxy** (Spearman with segments -0.05, with length -0.08, with true energy +0.17); alone it separates survivors with AUC 0.835 (low score survives); survival by upstream-score quintile 92 / 85 / 71 / 46 / 18 %; a high upstream score is somewhat more common for compact objects (59.6 % vs 46.7 % above the median).

## 7. Natural CV and the MicroBooNE domain (Tasks 4 and 7)

**Natural CV** (`numu_natural_cv_vs_official.csv`, fig7; 108 stored candidates in 105 events, numu inputs stored; **no truth label or photon state is stored**, so no control is possible): survival 43.5 %; length < 20 cm 11.3 % (6 of 53; 68 % interval 7.7-16.4 %) vs >= 20 cm 74.5 % (41 of 55). The official-sample values are 29.3 % and 73.5 %. The **direction is the same and the extended-shower survival agrees**; the compact survival is lower and the compact fraction is higher (49 % vs 25 %), in a small, unmatched sample.

**SOURCE**: no MicroBooNE training sample, class definition or input distribution is available (`NUMU_TRAINING_DOMAIN_SOURCE_AUDIT.md`). **MEASURED**: the SBND distributions above. **INFERENCE**: the numuCC / shower-quality inputs (`low_energy_michel_sp`, `bad_reconstruction_sp`, numuCC flag 3) point to a muon / Michel-like-object rejection, so rejecting compact, track-like or mis-typed objects is the direction of the design; the objects that fail are largely the reconstruction's own fragments (51 % of fragmented, 77-78 % of mu-/pi-typed objects are compact; E_reco/E_true 0.37-0.50). A **domain shift cannot be claimed**: there is nothing to compare the SBND input values with. What is MEASURED is only the SBND-side association; whether SBND photons are shorter or more segmented than MicroBooNE's at the same energy is unanswerable here.

## 8. Bookkeeping and open questions

Loss budget (`numu_loss_budget.csv`): numu fails 3,031 = 29.8 % of the 10,178 events lost; compact 1,445 (14.2 %); few-segment 1,349 (13.2 %); compact or few-segment 1,733 (17.0 %); non-clean photon object 1,756 (17.2 %); clean photon shower 1,275 (12.5 %), of which not compact 983 (9.7 %); muon-/pion-like controlling object 486 (4.8 %). Overlapping categories; association only. If the compact objects had the numu survival of the others there would be ~900 more numu survivors (before the downstream stages, which they would also have to pass); this is bookkeeping, not a proposal.

Open (not answered): (1) the training sample, class labels and per-class input distributions of the MicroBooNE model; (2) whether compactness was intended as a discriminator; (3) why survival at fixed shape falls with true energy; (4) a photon-state-labelled natural-CV or data control; (5) the same question for the `numu_score` upstream BDT, whose training is also undocumented.
