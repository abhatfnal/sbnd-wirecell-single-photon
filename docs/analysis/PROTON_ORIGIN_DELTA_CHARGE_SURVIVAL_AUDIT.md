# Decay-proton versus FSI-created survival of truth-1p events, and the Delta+ / Delta0 difference inside truth 1p: composition, reconstruction, vertex anchoring, and the measured residual

Date: 2026-11-11. Branch `analysis/ncdelta-proton-origin-survival-20261111`. **Characterisation only**: no selection, BDT, proton-threshold, FV, candidate-policy or retraining change. Roadmap item **P**. Truth definition: `SIGNAL_PROTON_ORIGIN_SOURCE_AUDIT.md`. Tables: `tables/proton_origin_survival_audit/`; figures `plots/proton_origin_survival_audit/fig1-fig7`; row-level products `$SP_DATA/proton_origin_survival_audit/official_ncdelta/` (outside Git). Adjustments are **descriptive stratified standardisations with a bootstrap (300 resamples, fixed seed, 68 % percentile intervals) and a logistic cross-check; they are not a causal model**. Language is association unless stated.

Tags: **SOURCE**, **MEASURED**, **EXPLORATORY** (a step added after seeing a residual).

## 1. Scope

Official Gen2 NC-Delta, provisional TPC box, frozen chain, policy `any`, thresholds unchanged. Population: the **5,170 truth-1p events with a Wire-Cell candidate** (Delta+ 3,673, Delta0 1,497); the 5,084 with a DL record enter the anchoring-controlled comparisons. Standardisation bins (fixed before looking): photon energy (<300 / >= 300 MeV), photon cos theta (<0.5 / >= 0.5), proton KE (35-100 / 100-250 / > 250 MeV), vertex-to-face distance (<50 / 50-100 / > 100 cm), proton reconstruction (proton-typed / merged / other), DL-stage anchoring (within 5 cm / not), attachment (shower in the main-vertex set / not). Strata need >= 3 events of both groups; the **fraction of the weighting group that has support is always reported**.

## 2. Proton-origin truth definition  (SOURCE; `SIGNAL_PROTON_ORIGIN_SOURCE_AUDIT.md`)

Categories from the GENIE mother chain (A decay proton, B1 Delta0 proton from the neutron decay nucleon, B2 Delta+ chain with a non-proton, C not descended from the decay nucleon, D ambiguous, E unresolved: 0 events), joined to the Geant4 primaries with a maximum KE mismatch of 1e-4 MeV. **The decay nucleon of every Delta0 is a neutron, so category A exists only for Delta+ and B1 only for Delta0: origin and Delta charge are structurally entangled.** The old "FSI-created" is B2 inside Delta+ and B1 inside Delta0; the old "67 % versus 54 %" is **A versus B2**.

## 3. Origin composition and reproduction  (MEASURED; `origin_composition.csv`, `origin_reproduction_phase8_*.csv`, fig1)

| | A decay | B1 Delta0 FSI-created | B2 Delta+ charge-exchange | C not from decay | D ambiguous |
|---|---|---|---|---|---|
| Delta+ (3,673) | **3,301 (89.9 %)** | 0 | 294 (8.0 %) | 5 | 73 (2.0 %) |
| Delta0 (1,497) | 0 | **1,476 (98.6 %)** | 0 | 21 | 0 |

Reproduction of the earlier numbers (events reaching `other`, 2,174): Delta+ decay **1,367 at 67.1 %**, Delta+ FSI-created **137 at 54.0 %**, ambiguous 35 at 51.4 %, Delta+ 1,541 at 65.5 %, Delta0 633 at 57.3 %. All reproduce.

## 4. Proton reconstruction by origin  (MEASURED; `reconstruction_by_origin*.csv`, fig2)

| | A decay | B1 | B2 | D |
|---|---|---|---|---|
| events | 3,301 | 1,476 | 294 | 73 |
| proton KE, median [16 %, 84 %] MeV | **190** [82, 385] | **96** [46, 266] | **55** [39, 107] | 106 |
| true straight-line path, median (cm) | 16.9 | 6.3 | 2.5 | 7.6 |
| cos(proton, beam), median | 0.87 | 0.73 | 0.58 | 0.83 |
| cos(proton, photon), median | 0.13 | 0.09 | 0.17 | 0.07 |
| proton-typed | 56.2 % | 51.1 % | 49.3 % | 47.9 % |
| merged / subdominant | 8.8 % | 14.4 % | 14.3 % | 6.8 % |
| no row / no signal-matched candidate | 9.9 / 3.4 % | 8.9 / 4.2 % | 10.5 / 5.1 % | 11.0 / 1.4 % |

**Are decay protons simply easier to reconstruct?** They are *different*: higher KE (by a factor 2-3.5), longer, more forward. At **fixed KE** the reconstruction is nearly the same: proton-typed fraction by KE bin 35-50 / 50-100 / 100-200 / 200-300 MeV is 44 / 52 / 56 / 71 % (A), 44 / 51 / 55 / 70 % (B1) and 42 / 57 / 50 / 50 % (B2 with 8-130 events per bin), so the origin dependence of the typing is the **KE difference**, not an intrinsic property.

## 5. Vertex anchoring by origin  (MEASURED; `anchoring_by_origin*.csv`, fig3)

Fraction within 5 cm of the true vertex (5,086 events with a DL record; events without a traditional vertex are excluded from that column's denominator):

| | traditional | DL-stage | final | \|V_DL - V_true\| median | along the photon (signed) | \|V_final - V_DL\| median |
|---|---|---|---|---|---|---|
| A decay | 36.4 % | **51.9 %** | 53.4 % | 4.0 cm | +0.5 cm | 0.09 cm |
| B1 Delta0 FSI-created | 25.9 % | **42.4 %** | 43.5 % | 12.8 cm | +6.4 cm | 0.18 cm |
| B2 Delta+ charge-exchange | 11.5 % | **36.3 %** | 37.9 % | 19.6 cm | +16.8 cm | 0.17 cm |

Decay protons are anchored more often **at the DL stage** (51.9 vs 42.4 / 36.3 %), the late refinement changes the vertex by <= 0.2 cm in all origins. Within a reconstruction state the difference shrinks (`anchoring_by_origin_and_reco_state.csv`): the association is with KE and proton typing, which the Phase-16 anchoring effect already tracks.

## 6. Photon / shower topology by origin  (MEASURED; `photon_state_by_origin.csv`)

Clean electron shower 46.4 % (A), 48.0 % (B1), 48.3 % (B2); fragmented 15.2 / 15.9 / 17.3 %; track-typed dominant object 19.3 / 18.2 / 18.0 %; shower not in the main-vertex set 7.5 / 6.4 / 6.1 %; **attachment failure under a true proton: 6.1 / 4.3 / 3.1 %**. The photon state is almost origin-independent; the only trend is that decay protons (higher KE, longer tracks, more often at the vertex) are slightly *more* often the parent of an unattached photon. No origin makes the photon more likely to be owned by the hadronic branch in a way that disfavours the FSI-created ones.

## 7. Frozen cutflow by origin  (MEASURED; `cutflow_by_origin.csv`, fig4)

Conditional survival (candidate -> final), policy `any`:

| stage | A decay | B1 Delta0 | B2 Delta+ FSI | D | Delta+ | Delta0 |
|---|---|---|---|---|---|---|
| shower stage | 65.6 % | 69.2 % | 71.4 % | 72.6 % | 66.2 % | 69.2 % |
| numu | 63.6 % | 61.5 % | 65.6 % | 66.0 % | 63.8 % | 61.3 % |
| **other** | **67.1 %** | 57.3 % | 54.0 % | 51.4 % | 65.5 % | 57.3 % |
| **ncpi0** | **52.7 %** | **37.3 %** | **25.7 %** | 61.1 % | 50.8 % | **36.9 %** |
| n_20br1 | 92.8 % | 88.8 % | 84.2 % | 100 % | 92.6 % | 88.8 % |
| **final (cumulative)** | **13.6 %** | **8.1 %** | **5.4 %** | 15.1 % | **13.1 %** | **8.1 %** |

**The origin dependence first appears at `other` and is largest at `ncpi0`**; the shower stage and `numu` have none (the shower stage is slightly *better* for FSI-like origins). The `ncpi0` stage contributes a larger share of the Delta+ - Delta0 final-efficiency difference than `other`.

## 8. The `other` stage  (MEASURED; `other_by_origin*.csv`, fig5)

Events reaching `other`: A 1,364 at **67.1 %**, B1 624 at 57.4 %, B2 136 at 54.4 %. Stratified (DL-anchored / not anchored; proton reco-typed / not):

| | A decay | B1 | B2 |
|---|---|---|---|
| DL anchored | **77.5 %** (861) | 73.4 % (331) | 71.9 % (64) |
| DL not anchored | **49.3 %** (503) | 39.2 % (293) | 38.9 % (72) |
| proton reco-typed | 75.7 % (842) | 64.0 % (358) | 60.5 % (81) |
| proton not reco-typed | 53.3 % (522) | 48.5 % (266) | 45.5 % (55) |
| anchored and reco-typed | **80.1 %** (693) | 73.7 % (259) | 75.0 % (52) |
| not anchored and reco-typed | 55.0 % (149) | 38.4 % (99) | 34.5 % (29) |
| anchored, not reco-typed | 66.7 % (168) | 72.2 % (72) | - |
| not anchored, not reco-typed | 46.9 % (354) | 39.7 % (194) | 41.9 % (43) |

Holding **both** anchoring and reconstruction fixed, the decay-minus-FSI difference is **-5.6 pp (z -0.9)** to **+6.3 pp (z 2.0)** for B1 in the anchored cells, **+7.2 (z 1.6) / +16.6 pp (z 2.6)** in the not-anchored cells; for B2 +5.1 (z 0.8) / +5.0 (z 0.6) / **+20.6 pp (z 2.1)**. Strata of < 40 events (B2) are not interpreted. **Anchoring is the dominant variable** (77 vs 49 % in A; 73 vs 39 % in B1): within the DL-anchored events the three origins are within 6 pp of each other; the remaining difference sits in the not-anchored events where a typed proton still helps decay protons (55 vs 38 %); this is small-cell evidence (29-149 events).

## 9. Delta charge inside truth 1p  (MEASURED; `delta_x_origin_x_reco_x_anchoring.csv`, `delta_by_stage.csv`)

Final efficiency by Delta x origin x proton reconstruction x anchoring: **Delta+ decay**: reco-typed and anchored **26.2 %** (1,311), reco-typed not anchored 6.1 % (544), not reco-typed anchored 11.8 % (374), not typed not anchored 2.5 % (1,020); **Delta0 B1**: 15.8 % (469), 4.6 % (285), 7.6 % (144), 3.8 % (549); **Delta+ B2**: 14.6 % (82), 1.6 % (63), 4.3 % (23), 1.7 % (121). The composition differs strongly (the well-reconstructed, anchored cell holds 40 % of A but 32 % of B1 and 28 % of B2); Delta+ decay is higher than Delta0 B1 in three of the four cells (26.2 vs 15.8 %, 6.1 vs 4.6 %, 11.8 vs 7.6 %); the exception is the worst cell (not typed, not anchored: 2.5 vs 3.8 %).

Stage-wise Delta+ minus Delta0 contrast (all truth 1p; raw -> full descriptive adjustment): shower stage -3.3 -> -1.9 pp; numu +2.5 -> +3.0; **other +8.2 -> +4.9 [2.6, 7.5]**; **ncpi0 +13.8 -> +15.1 [12.0, 18.8]**; n_20br1 +3.8 -> -0.5; **final +5.0 [4.1, 5.8] -> +5.2 [4.3, 6.3]**.

## 10. Adjusted comparisons  (MEASURED; `delta_adjustment_steps.csv`, `delta_logistic_crosscheck.csv`, fig6)

**Delta+ - Delta0 final efficiency inside truth 1p** (pp; 68 % bootstrap interval; support = fraction of Delta+ events with a matched stratum):

| step | all truth 1p (origin not controlled) | FSI-like origin only (B1 + B2 + C) |
|---|---|---|
| 1 raw | **+5.0** [4.1, 5.8] | -2.7 [-4.4, -1.5] |
| 2 + photon energy and angle | +5.0 [4.1, 5.8] | -2.7 |
| 3 + proton KE | +5.2 [4.2, 6.1] | -2.5 [-4.2, -1.4] |
| 4 + proton origin (group) | not matchable (no Delta0 decay protons) | -2.5 (trivial inside this population) |
| 5 + proton reconstruction state | +4.9 [3.9, 5.9] (support 99.8 %) | -2.5 [-4.2, -1.3] |
| 6 + DL anchoring | +5.0 [4.1, 6.0] (98.6 %) | -2.6 [-4.4, -1.2] |
| 7 + photon / attachment state | **+5.2** [4.3, 6.3] (94.5 %) | **-2.6** [-4.3, -1.2] (83 %) |
| 8 + neutron-capture-like photon row (EXPLORATORY) | **+1.6** [0.1, 3.1] (85.8 %) | **-1.1** [-3.2, +0.2] (78 %) |

Logistic cross-check (Delta+ marginal effect on the final efficiency): **+4.2 pp** (odds ratio 1.62) with photon, proton KE, reconstruction, anchoring and attachment; **+1.0 pp** (odds ratio 1.11) after adding the neutron-capture-like photon row. **None of the photon, proton-KE, proton-reconstruction, anchoring or attachment adjustments reduces the final-efficiency difference** (+5.0 -> +5.2 pp): it is **not a composition effect** of those variables. The same adjustments reduce the `other` difference from +8.2 to +4.9 pp (proton KE gives most of it: +8.5 -> +5.8 pp; reconstruction +4.9; anchoring none beyond), and the exploratory step lowers it to +3.8 pp.

## 11. Decay proton versus FSI-created: direct test  (MEASURED; `decay_vs_fsi_adjustment.csv`, `decay_vs_fsi_logistic_crosscheck.csv`)

A decay versus **B2 (same Delta charge)** and versus B1 (other charge), decay minus FSI-created, pp (raw -> after photon, proton KE, vertex-face distance, DL anchoring, proton reconstruction; weights = the FSI-created group):

| stage | A vs B2 raw -> adjusted [68 %] | A vs B1 raw -> adjusted [68 %] |
|---|---|---|
| shower stage | -6.1 -> +2.4 [-1.4, 5.9] | -4.0 -> 0.0 [-2.0, 1.6] |
| numu | -1.6 -> -3.4 [-8.9, 1.2] | +2.1 -> +1.5 [-1.4, 3.1] |
| **other** (the old 67 vs 54 %) | **+12.7 -> -1.8 [-6.8, +6.5]** | **+9.7 -> +3.0 [+0.1, +6.0]** |
| **ncpi0** | +27.0 -> **+34.2 [16.1, 41.0]** (support 38 %) | +15.2 -> **+14.9 [10.9, 19.9]** (69 %) |
| final | **+8.2 -> +4.9 [2.4, 6.6]** (78 %) | **+5.5 -> +3.8 [2.8, 4.9]** (93 %) |

Step by step for `other` (A vs B2): +12.7 -> +10.9 (photon) -> **+0.7 (proton KE)** -> -1.1 (edge) -> -0.1 (anchoring) -> -1.8 (reconstruction): **the old 67 % versus ~54 % effect is almost entirely proton KE** (decay protons have a median KE of 190 vs 55 MeV), then anchoring and reconstruction carry what KE does not; the logistic cross-check agrees (marginal effect +0.4 pp, odds ratio 1.02, for `other | numu`). Against B1 a +3.0 pp residual (interval touching zero) remains. **The decay-versus-FSI difference in the final efficiency remains +3.8 to +4.9 pp after those adjustments, because of the `ncpi0` stage**, where the difference is +15 to +34 pp and is not reduced by KE, reconstruction or anchoring.

## 12. Mechanism of the residual at `ncpi0`  (MEASURED, with an EXPLORATORY mediator; `ncpi0_*.csv`, `neutron_photon_rows_by_origin.csv`)

Events reaching `ncpi0` (A 915, B1 358, B2 74): ncpi0 survival 52.7 / 37.4 / 25.7 %; **kine-pair present 64.6 / 75.1 / 86.5 %**; tagger pair present 7.7 / 11.7 / 14.9 %; survival with / without a kine pair **32.3 / 89.8 %** (A), 23.4 / 79.8 % (B1), 17.2 / 80.0 % (B2). The kine-pair second member is "other signal EM" in 23.2 / 32.3 / 34.4 % (Phase 14: neutron-capture-like low-energy photons). The proton-photon geometry, proton reconstruction and anchoring of the three groups reaching `ncpi0` are similar (proton-typed 70 / 64 / 66 %, anchored 73 / 68 / 62 %, median cos(proton, photon) 0.26 / 0.22 / 0.38).

**The mediator.** Counting, in the signal-matched candidate, the reconstructed rows whose source-ranked top truth is a **photon of the signal interaction with a neutron mother** (the Geant4 mother pdg; neutron-capture-like photons; the process code is not audited): **events with such a row: A 25.6 %, B1 54.9 %, B2 68.5 %** (all truth 1p; median energy 4-7 MeV). Among events reaching `ncpi0`, **having such a row gives a kine pair in 95-98 % and ncpi0 survival 25 / 22 / 16 % for A / B1 / B2; without it the kine-pair rate is similar for the three origins (56.7 / 57.8 / 62.5 %) and the survival differs less (59.2 / 51.0 / 45.8 %)**. Standardised, the origin differences in the pair outcomes vanish once the indicator is included: decay minus B1 kine-pair presence -10.5 -> -0.5 pp, ncpi0 survival +13.9 -> **+2.1 pp**; decay minus B2 kine pair -24.0 -> +5.2 pp, ncpi0 survival +26.1 -> **-0.2 pp**. The final efficiency difference decay minus B1 goes from +3.8 to **0.0 [-1.5, +0.8] pp** and decay minus B2 (support 60 %) from +4.9 to **-1.4 [-2.6, +1.3] pp**; the Delta+ - Delta0 difference from +5.2 to +1.6 pp (above).

Reading (association): **FSI-created / neutron-chain protons come with more neutron activity (B1: the decay nucleon is a neutron; B2: a charge exchange passes through a neutron), which produces more low-energy photon rows; those rows give the kinematics-tree pair that the frozen `ncpi0` BDT penalises** (`NCPI0_PAIR_MEMBER_TRUTH_AUDIT.md`). The mediator was introduced after the residual was seen (exploratory, one indicator, from the Geant4 mother pdg), the B2 `ncpi0` comparison has low support (5-38 %) and 74 events, and no process-level truth was audited, so it is a measured association, not a proven mechanism. No frozen input beyond those of Phase 14 was examined.

## 13. Natural-CV  (unavailable beyond the Delta charge; `natural_cv_check.csv`)

The 416 natural signal events (172 truth 1p: 118 with a proton decay nucleon, 54 with a neutron) carry the decay nucleon pdg but **not the GENIE mother chain** (the decay / FSI-created split needs it) and no final-selection flag in the stored natural candidate table. The origin-category and survival comparison is **not available from stored products**; no new scan was made.

## 14. What is established

* The old Delta+ "67 % versus 54 %" (A vs B2) at `other` is **composition**: it falls from +12.7 to +0.7 pp with proton KE alone and to -1.8 pp [-6.8, +6.5] with anchoring and reconstruction; versus Delta0 B1 a small +3.0 pp [+0.1, +6.0] remains.
* Origin and Delta charge are structurally entangled (A only Delta+, B1 only Delta0); decay protons have 2-3.5x higher KE, longer tracks and higher DL-stage anchoring (51.9 / 42.4 / 36.3 %).
* **A real residual exists in the final efficiency**: decay minus FSI-created +3.8 (B1) to +4.9 (B2) pp, Delta+ minus Delta0 +5.2 pp after all adjustments; it arises at `ncpi0` (+15 to +34 pp), not at `other`.
* The `ncpi0` residual is associated with **neutron-capture-like photon rows** (A 26 %, B1 55 %, B2 69 %) that create the kine pair; adjusting for their presence removes it (+3.8 -> 0.0; +5.2 -> +1.6 pp).

## 15. What remains unresolved

* The process behind the neutron-mother photons (not audited) and whether the mediator is the whole story (the Delta+ - Delta0 difference keeps +1.6 pp [0.1, 3.1]).
* B2 comparisons are small (294 events, 74 at `ncpi0`); the ambiguous and not-from-decay categories (73, 26) are too small to interpret.
* Natural-CV: the chain is not stored.
