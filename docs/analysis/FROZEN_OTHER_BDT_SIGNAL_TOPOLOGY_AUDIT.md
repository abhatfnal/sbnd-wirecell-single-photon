# Why does the frozen `other` BDT keep more truth-1p than truth-0p signal? An audit

Date: 2026-11-10. Branch `analysis/ncdelta-other-bdt-audit-20261110` (from the pushed Phase-7 head 2a1ec07). **Audit of the frozen model only: no retraining, no feature selection, no threshold scan (the cut is fixed at 0.2), no surrogate classifier.**
Model provenance and the 146-input table: `FROZEN_OTHER_BDT_SOURCE_AUDIT.md`. Code: `scripts/other_bdt_scan.py`, `scripts/other_bdt_source_table.py`, `scripts/other_bdt_proton_origin_scan.py`, `scripts/other_bdt_audit.py`, `src/sbnd_single_photon/other_audit.py`.
Detailed outputs: `$SP_DATA/other_bdt_audit/official_ncdelta/` (with `metadata.json`: git commit, official manifest hash, BDT weight checksum, baseline-config hash, truth-master hash, Phase-7 harmonization hashes). Compact tables: `tables/other_bdt_audit/`; figures: `plots/other_bdt_audit/`.

**Language used throughout.** *Level 1*: the class distribution of a variable differs. *Level 2*: the variable participates in splits of the frozen trees. *Level 3*: an exact model attribution associates the variable with the class score difference. Nothing here is a controlled counterfactual, so no sentence says that a variable *causes* the efficiency difference.

## 1. Question

Phase 6 found that among official Gen2 NC-Delta signal events reaching the `other` stage (TPC box, policy `any`), the conditional survival is 47.3 % for truth 0p and 63.2 % for truth 1p, contributing +0.289 to ln(eps_1p/eps_0p), and that this is **not** explained by photon energy, direction, neutrino energy, vertex position or conversion distance. What does the frozen BDT see, and which input family carries the difference?

## 2. Exact frozen model provenance (summary)

`single_photon_other_bdt_final.xml`, sha256 `8c0ac375...b8dbb16`, an **XGBoost model converted to TMVA (`xgboost2TMVA`, BoostType Grad)**: **215 trees of depth 5**, 6,251 leaves, all boost weights 1, **146 inputs of which 133 are split on**; `score = tanh(sum of leaf values)`; frozen cut `score > 0.2` (margin 0.2027). BDT scores are **not stored in the CAF**; the offline scorer was checked against an independent implementation of the production TMVA rules: **max |difference| 2.9e-9 over 5,453 candidates, 0 differences above 1e-6, 0 decision flips at 0.2**; it also reproduces the validated derived-table scores exactly (max difference 0.0). Four of the 146 inputs are **outputs of other BDTs** run in the production (`numu_score`, `numu_1_score`, `numu_2_score`, `cosmict_10_score`). Because the exact score is reproduced, model-internal attribution (section 9) is justified. Details and caveats (no ROOT/TMVA runtime here) in the source audit.

## 3. Study population

Official Gen2 NC-Delta signal, provisional TPC truth box, policy `any`, events with at least one candidate that has passed wc.valid, candidate, > 20 MeV shower, BDT evaluable and numu (the `other` cut is applied): **5,007 events** (equal to the validated numu-stage count), by truth class at 35 MeV:

| truth | events reaching `other` | pass (score > 0.2) | conditional survival | events with > 1 reaching candidate |
|---|---|---|---|---|
| 0p | 2,446 | 1,157 | **47.3 %** [46.3, 48.3] | 3 |
| 1p | 2,174 | 1,373 | **63.2 %** [62.1, 64.2] | 4 |
| >=2p | 387 | 251 | 64.9 % [62.3, 67.4] | 0 |

(total 2,781 = the validated `other`-stage count). The difference 1p - 0p is **+15.9 percentage points**. Candidate bookkeeping: 5,453 candidates were scanned for the 5,225 events reaching numu in the filter box; in the TPC-box population 5,014 candidates reach `other`, only **7 events** have more than one reaching candidate, and 220 events have more than one candidate in total. The event decision follows `any`: the **controlling candidate** is the reaching candidate with the largest frozen score (ties: lowest `nu_index`; never selected by truth); the event passes iff that score exceeds 0.2, and this equals the validated event flag for **every one of the 5,007 events**. The controlling candidate is the lowest-`nu_index` reaching candidate in 99.94 % of events, and in only 1 event does the decision come from a non-lead candidate, so multiple candidates do not hide anything here.

## 4. Score difference (`other_score_0p_vs_1p.png`, `other_score_delta_in_1p.png`)

* Median frozen score: truth 0p 0.145, truth 1p 0.544, truth >=2p 0.531; the 1p distribution is shifted to high scores (KS distance 0.18), not just across the 0.2 line; the 0p distribution has a spike at -1.
* **Delta0 vs Delta+:** all 50.0 % vs 62.4 %. Inside truth 1p: **Delta0 57.4 %** (363/633, median score 0.39) vs **Delta+ 65.5 %** (1,010/1,541, median 0.59), KS 0.11. Inside truth 0p the two charges are close: 46.5 % vs 50.5 % (KS 0.05, p = 0.23).

## 5. Input-variable differences (`other_input_top_differences.png`; table `input_stats_0p_vs_1p.csv`, ranked by KS distance among events reaching `other`, controlling candidate)

Level 1 only. Largest descriptive differences (truth 0p -> truth 1p):

| input (family) | KS | SMD | median 0p -> 1p | at default 0p / 1p | splits |
|---|---|---|---|---|---|
| `numu_1_score` (numu tagger) | 0.36 | -0.60 | -0.22 -> -0.39 | 0 / 0 | 194 |
| `shw_sp_br2_sg_length` (shower sub-tagger) | 0.34 | -0.57 | 12.9 -> 0.0 | 0.28 / 0.61 | 70 |
| `shw_sp_shw_vtx_dis` (geometry) | 0.33 | +0.19 | 0.0 -> 6.7 | 0 / 0 | 114 |
| `shw_sp_br2_n_shower_main_segs` (sub-tagger) | 0.33 | -0.39 | 1 -> 0 | 0.28 / 0.61 | 40 |
| `shw_sp_hol_2_min_angle` (sub-tagger) | 0.33 | -0.59 | 29.4 -> 0.0 | 0.31 / 0.64 | 72 |
| `numu_score` (numu tagger) | 0.20 | +0.30 | -0.96 -> -0.68 | 0 / 0 | 281 |
| `shw_sp_max_shw_dis` (geometry) | 0.20 | -0.04 | 9.5 -> 15.3 | 0 / 0 | 80 |
| `shw_sp_br4_2_ratio_45` (sub-tagger) | 0.18 | -0.31 | 1.0 -> 1.0 | 0.77 / 0.60 | 33 |

## 6. Physics grouping (descriptive; `input_group_summary.csv`)

Groups from the variable names and the filling code (no group is called responsible): mean KS between 0p and 1p: numu-tagger scores 0.154 (4 inputs); shower-quality sub-taggers 0.141 (22); shower multiplicity 0.140 (6); shower/vertex geometry 0.110 (11); shower calorimetry 0.086 (31); **track/proton activity at the vertex 0.058 (11; no input above KS 0.10)**; vertex position 0.037 (1); cosmic-tagger inputs 0.036 (60). The families that differ most are not the ones that describe protons or hadronic tracks.

## 7. Missing / filled inputs (`other_fill_default_fractions.png`, `fill_default_fractions.csv`, `strata_*.csv`)

* `shw_sp_filled != 0` for 100 % of the population in all classes (the BDT is evaluated on a filled shower for everyone).
* **Availability differs strongly for the `br2` and `hol_2` sub-tagger inputs.** Source: `shw_sp_br2_*` (bad_reconstruction_1_sp) is evaluated **only when the leading shower's start segment is directly attached to the main vertex**; otherwise the fields stay at their default 0. MEASURED: `br2` at default is equivalent to `shw_sp_shw_vtx_dis != 0` (2,237 of 2,238 events; one exception), i.e. "the leading shower is detached from the vertex". The fraction detached is **61 % of truth 1p vs 28 % of truth 0p** (Delta0 within 1p 53 %, Delta+ 64 %; other defaults: `hol_2_min_angle` 64 % vs 31 %, `br4_2_ratio_*` the opposite direction).
* **The class difference sits entirely in one availability stratum.**

| shower | truth | events | survival |
|---|---|---|---|
| attached to the vertex (gap = 0) | 0p | 1,771 | 48.6 % [47.4, 49.8] |
| attached | 1p | 848 | 49.5 % [47.8, 51.3] |
| **detached** (gap > 0, `br2` at default) | 0p | 675 | **43.8 %** [41.9, 45.8] |
| **detached** | 1p | 1,326 | **71.9 %** [70.6, 73.1] |

For attached showers the two classes are indistinguishable; for detached showers truth-1p events survive much more often than truth-0p ones. Accounting (exact): 1p = 0.39 x 0.495 + 0.61 x 0.719 = 0.632; 0p = 0.72 x 0.486 + 0.28 x 0.438 = 0.473. A symmetric decomposition of the +15.9 pp attributes **about 3 pp (19 %) to the different detached fraction and about 13 pp (81 %) to different survival within the detached stratum**. So this is a **variable-availability / reconstruction-topology difference, not only a difference of physical values**, and it is concentrated where the BDT's `br2`/`hol_2` inputs are at their default.

## 8. Dependence on physical and reconstructed quantities (`other_survival_vs_observables.png`, `other_survival_vs_photon_energy.png`, `other_survival_vs_lead_proton_ke.png`)

* At fixed **true photon energy** and fixed **cos(theta)** the 1p-0p gap persists in every bin below 500 MeV (e.g. 0.58 vs 0.70 at 300-400 MeV; 0.36 vs 0.61 at cos 0-0.25 for 0p vs 1p) and is largest at low energy / backward angles; it narrows above 500 MeV. Logistic adjustment (observed association only) for photon energy, angle, neutrino energy and vertex **does not reduce** the gap (+17.0 pp [15.6, 18.5] vs raw +15.9).
* **Reco shower-to-vertex distance** shows the same structure: at distance 0 the classes are equal (0.486 vs 0.495); at 2-20 cm 1p survives 0.79-0.82 vs 0p 0.49-0.61; at larger distances both fall (0.68 vs 0.44 at 20-50 cm). Adjustment for reco shower energy, shower-vertex distance and vertex displacement **halves** the gap (to +7.2 pp [5.1, 8.4]); all covariates together +7.5 pp.
* **Reco proton multiplicity.** Truth-1p events with **no** reconstructed proton row above 35 MeV (750 events) survive at **48.0 %**, like truth 0p (46.8 %); truth-1p events with one reconstructed proton (1,278) survive at **71.9 %**; with two or more 64.4 %. Truth-0p events with a reconstructed (fake) proton survive at 49.7 % (372) / 48.9 % (47): no elevation. The high survival is concentrated in truth-1p events **that also have a reconstructed proton**, although the proton-related BDT inputs themselves barely differ between the classes (section 6) and carry almost none of the model attribution (section 9).
* Versus the **leading true proton KE** (truth 1p): survival is about 0.50-0.60 for 35-150 MeV and 0.75 at 200-300 MeV, 0.71-0.73 above; no threshold-like feature at the 35 MeV reference.
* Versus **true conversion distance**: 1p stays above 0p up to about 50 cm (0.63-0.68 vs 0.47-0.52 up to 20 cm). Vs **|reco vertex - true vertex|**: both classes fall from ~0.7-0.8 at < 1 cm to ~0.3-0.4 beyond 20 cm and are close above 5 cm.

## 9. Proton-origin study inside truth 1p (`proton_origin_survival.csv`, `proton_origin_x_connected.csv`)

GENIE-record mother chains were used (`classify_proton_origin`): for each truth-1p event the unique stable proton above 35 MeV is traced to the Delta; the Delta-decay nucleon is the status-14 nucleon daughter of the Delta. In 2,174 events: Delta0 decays to a **neutron** in all 633, Delta+ to a **proton** in all 1,541.

| class | events | `other` survival |
|---|---|---|
| Delta+, **decay proton** (sole stable proton descendant of the decay nucleon; it may have rescattered) | 1,367 | **67.1 %** |
| Delta+, FSI-created (chain contains a non-proton, or not the decay nucleon) | 137 | 54.0 % |
| Delta+, ambiguous (the decay proton and a knocked-out proton cannot be told apart) | 35 | 51.4 % |
| Delta0, FSI-created (the decay nucleon is a neutron; the proton comes from charge exchange / knock-out) | 626 | 57.4 % |
| not descended from the decay nucleon | 9 | 55.6 % |

Truth-record limits: GENIE hA/hN keeps the same record particle for elastic rescattering, so "decay proton" means identity-continuous descent, and a knocked-out sibling cannot be separated from the decay proton when several protons descend from it (the 35 ambiguous events). Observations: (i) **FSI-created-proton events have the same survival in both charges** (Delta+ 54.0 % vs Delta0 57.4 %), while **decay-proton events survive more** (67.1 %); (ii) within both attachment strata decay-proton events are higher (attached 54.6 % vs 43.5-44.3 %; detached 73.7 % vs 61.8-69.6 %); (iii) decay-proton events are more often detached (65.5 % detached vs 53-55 % for FSI-created). The hypothesis that the Delta+/Delta0 difference inside truth 1p reflects whether the proton is the decay nucleon is therefore **supported as an observed correlation** (the difference tracks the proton origin, not the Delta charge once the origin is fixed); the physical reason is not established. Delta+ vs Delta0 inside 1p by attachment: attached 52.8 % vs 43.4 %, detached 72.6 % vs 69.6 %.

## 10. Model-internal attribution (exact model, exact method)

*Method.* (A) The exact additive decomposition `margin = sum over 215 trees of leaf values` (`tanh(margin)` is the score). (B) **Exact interventional TreeSHAP** of the margin of this very ensemble (`other_audit.interventional_shap`; validated against brute-force Shapley values on a toy ensemble and by additivity, residual < 1e-14 on the real model) against an explicit background sample; for the question "why does a 1p event score higher than a 0p event" the foreground is truth-1p events (600 random controlling candidates) and the background truth-0p events (300 random), so the attributions sum exactly to the mean margin difference. Attributions are in margin units (not probabilities) and depend on that background, which is part of the question. No surrogate model was used.

* **Tree decomposition:** the mean margin is 0.055 (0p) vs 0.531 (1p), difference 0.476, distributed over **many trees** (126 positive, 89 negative); the 15 largest trees account for 47 %; no single tree dominates (largest: tree 0, root `shw_sp_lem_n_3seg`, +0.029).
* **SHAP, 1p vs 0p background** (total +0.427 of the 0.476): by family: **shower-quality sub-taggers +0.308**, numu-tagger scores +0.147, shower/vertex geometry +0.060, shower calorimetry -0.064, shower multiplicity -0.036, **track/proton activity +0.010**, cosmic +0.002, vertex position -0.001. Largest inputs: `shw_sp_hol_2_min_angle` +0.115, `numu_1_score` +0.086, `shw_sp_br2_sg_length` +0.073, `shw_sp_lem_e_charge` +0.064, `shw_sp_shw_vtx_dis` +0.060, `numu_score` +0.046, `shw_sp_n_good_showers` -0.046, `shw_sp_br2_n_shower_main_segs` +0.037.
* **Delta+ vs Delta0 inside truth 1p** (foreground Delta+ 1p, background Delta0 1p; total +0.270): sub-taggers +0.086, multiplicity +0.053, vertex position +0.037 (`reco_nuvtxY`), calorimetry +0.036, geometry +0.033, numu scores +0.024; again almost nothing from the track/proton family (+0.001).
* **Level table (`variable_levels_1_2_3_top25.csv`):** the inputs with a large class difference (L1), many splits (L2) and a large positive attribution (L3) are `shw_sp_hol_2_min_angle`, `shw_sp_br2_sg_length`, `shw_sp_br2_n_shower_main_segs`, `shw_sp_shw_vtx_dis` and `numu_1_score`: exactly the attached/detached-shower inputs of section 7 plus a numu sub-BDT score. `shw_sp_lem_e_charge` has a modest KS (0.09) but a large attribution (mean |SHAP| 0.31): its attribution reflects many small shifts, not a clear class distribution difference, and should not be over-read.

## 11. Does it depend on our loose truth definition? (`other_loose_vs_harmonized.png`, `other_survival_harmonized.csv`)

| denominator | events reaching `other` | survival |
|---|---|---|
| loose TPC box, truth 0p / 1p / >=2p (35 MeV) | 2,446 / 2,174 / 387 | 47.3 % / 63.2 % / 64.9 % |
| **SPINE-harmonized**, truth 0p / 1p / >=2p (35 MeV) | 1,967 / 1,716 / 298 | 48.4 % / 64.4 % / 66.1 % |
| **SPINE-harmonized 0p50 / Np50** | 2,220 / 1,761 | **49.6 % / 65.5 %** |
| loose TPC box, 0p50 / Np50 definition | 2,745 / 2,262 | 48.2 % / 64.5 % |

The gap is **+16.0 pp on the harmonized denominator** (+15.9 pp loose): the `other` effect is **not an artifact of the loose truth definition or of the 35-MeV threshold**. KS distance of the score between harmonized 0p50 and Np50: 0.19.

## 12. Natural-CV check (`natural_cv_other.csv`; low statistics)

47 natural NC-Delta events reach `other`: truth 0p 9/18 = 50.0 %, truth 1p 17/23 = 73.9 %, truth >=2p 5/6; Fisher p = 0.19, KS of the scores 0.32 (p = 0.20). Same direction as the dedicated sample, **too few events for more than a consistency statement**.

## 13. What is established

1. The frozen `other` model is an XGBoost-converted TMVA ensemble (215 depth-5 trees, 146 inputs, four of them outputs of upstream numu/cosmic BDTs); its score is reproduced exactly (3e-9) by an independent implementation of the production rules.
2. Among events reaching `other`: survival 47.3 % (0p) vs 63.2 % (1p) vs 64.9 % (>=2p); the event decision equals the controlling-candidate score > 0.2 for all 5,007 events; multiple candidates are negligible (7 events).
3. The class difference is **not** a difference in photon energy/angle/vertex/conversion distance, persists at fixed values of them, and persists on the SPINE-harmonized denominator.
4. It is concentrated in events whose leading shower is **detached from the vertex** (the `br2`/`hol_2` sub-tagger inputs are then at their default): attached showers 48.6 % vs 49.5 % (equal), detached showers 43.8 % (0p) vs 71.9 % (1p); 61 % of truth-1p events but 28 % of truth-0p events are detached; about 81 % of the gap is within the detached stratum.
5. The BDT's own proton/track inputs differ little between classes and carry ~0 of the model attribution; the attribution is carried by the shower-quality sub-taggers (+0.31 of +0.43 margin units) and the numu-tagger scores (+0.15).
6. The high survival is concentrated in truth-1p events that also have a reconstructed proton; truth-1p events without one behave like truth 0p.
7. Inside truth 1p the Delta+ > Delta0 survival difference tracks the **proton origin**: decay-proton events 67.1 %, FSI-created-proton events 54-57 % in either charge.
8. The direction is confirmed by the natural-CV rehearsal at low statistics.

## 14. What remains unexplained, and questions for a future optimization phase (no recommendations)

* **Why** truth-1p events are detached from the vertex more often (61 % vs 28 %), and why detached truth-1p showers score high while detached truth-0p showers score low (43.8 %). The source defines what `br2` availability means but not why a true proton changes the shower-vertex connectivity; a possible role of vertex placement at the hadronic vertex versus the photon conversion point (Phase 6 found the reco vertex displaced along the photon direction by about the conversion distance in matched candidates) is **not tested here**.
* Whether the frozen model's response to an *unfilled* `br2`/`hol_2` input (the value 0) is a property of the MicroBooNE training domain (how defaults were produced there) rather than of the physics; the training sample and its default conventions are not available here.
* What the upstream numu-tagger scores (`numu_1_score` -0.22 -> -0.39 for 1p) encode for NC-Delta, and whether they are available/meaningful for the SBND chain as run.
* Whether the decay-proton / FSI-created difference is itself a vertex-connectivity effect (decay-proton events are more often detached) or an independent effect.
* Questions a future optimization phase could ask (not recommended actions): is the `other` stage's behaviour on detached showers acceptable for a dedicated NC-Delta selection; should the BDT inputs be audited for default-value availability before any retraining; does a topology-independent score exist for the same events. Nothing in this audit recommends a new cut.
