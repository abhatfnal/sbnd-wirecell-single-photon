# Where is the photon-line vertex displacement of truth-0p events introduced? V_true -> V_trad -> V_DL -> V_final

Date: 2026-11-11. Branch `analysis/ncdelta-shower-attachment-vertex-provenance-20261111`. **Characterisation only**: no selection, threshold, retraining, FV, proton-policy or candidate-policy change. Roadmap item **V** (with item T in `SIGNAL_PHOTON_SHOWER_ATTACHMENT_AUDIT.md`). Sources: `DL_VERTEX_SOURCE_AUDIT.md`, `WIRECELL_VERTEX_REFINEMENT_SOURCE_AUDIT.md`. Tables: `tables/vertex_provenance_audit/`; figures `plots/vertex_provenance_audit/fig1-fig3, fig7, fig8`; row-level products `$SP_DATA/vertex_provenance_audit/official_ncdelta/` (outside Git). Language is *association*, not causation, unless the source says otherwise.

Tags: **SOURCE**, **MEASURED**, **NOT AUDITED**.

## 1. Scope

Official Gen2 NC-Delta, provisional TPC box, frozen chain, no FV. The vertex of an event is that of the **signal-matched candidate** (Phase-9 `match_cand_nu`; fallback: the candidate holding the dominant photon object): 11,109 events with a DL record. All vertices are in the **raw reconstruction frame, cm** (truth shifted by the TrueFwd SCE map; the shift is small: median 0.83 cm, maximum 5.0 cm). Displacements are decomposed along / perpendicular to the **true photon direction** (positive = along the flight). "Anchored" = within **5 cm** of the true vertex (3 and 10 cm sensitivities in `provenance_classes_tol3/10.csv`).

## 2. DL vertex semantics and the record

(`DL_VERTEX_SOURCE_AUDIT.md`.) The DL vertex is a **graph vertex of the traditional PR** selected by a geometric-plus-DL score; the network's top-5 voxels are snapped to the nearest graph vertex; the top-1 DL score is below 0.02 in 85 % of the events (94 % for truth 0p), where the source says geometry decides. **Coverage (MEASURED, `dl_coverage.csv`):** 11,331 events requested, **11,309 with a DL record (22 without)**, 11,783 candidates, **11,754 with a production call (29 without)**, 11,754 OFF calls, **0 duplicates, 0 candidates with more than one production call, 23,508 of 23,508 run/subrun/event keys equal to Phase 9, 0 network errors**, 1,002 not-accepted calls all carrying the sentinel `dl_xyz = 0` (never used), all accepted and valid final vertices inside the detector box, **`final_*` = `kine_nu_*_corr` for 11,754 of 11,754 candidates**.

## 3. Final vertex semantics and the DL-to-final chain

(`WIRECELL_VERTEX_REFINEMENT_SOURCE_AUDIT.md`.) `V_trad` is made by the traditional PR (stage A), `V_DL` selected among existing graph vertices (C), refit by `improve_vertex` and audited (D), and may be overwritten only by the displaced-vertex pi0 finder (E). `V_final` is what `T_tagger`, `T_kine` and `shw_sp_*` see.

## 4. The central diagnostic: displacement along the true photon direction  (MEASURED; `vertex_displacements.csv`, fig1)

Median magnitude / signed component along the photon [cm]:

| displacement | all | truth 0p | truth 1p | truth >= 2p |
|---|---|---|---|---|
| \|V_trad - V_true\| | 23.7 / +20.6 | **29.4 / +25.8** | 17.9 / +13.8 | 16.7 / +15.0 |
| \|V_raw DL top-1 voxel - V_true\| | 43.1 / +25.0 | 55.0 / +36.1 | 34.9 / +14.9 | 2.1 / +0.4 |
| \|V_DL - V_true\| | 18.6 / +14.0 | **28.6 / +24.5** | 6.2 / +1.0 | 2.1 / +0.5 |
| \|V_final - V_DL\| | **0.21 / 0.0** | **0.25 / 0.0** | 0.12 / 0.0 | 0.36 / 0.0 |
| \|V_final - V_true\| | 18.0 / +13.3 | **28.7 / +24.4** | 5.4 / +0.6 | 1.8 / +0.4 |

Restricted to separable events (true conversion >= 5 cm; 3,768 / 3,752 / 674 events): the median longitudinal displacement of `V_DL` is **+29.6 / +4.5 / +0.7 cm** (0p / 1p / >= 2p) and of `V_final` **+29.6 / +1.8 / +0.5 cm**; `V_final - V_DL` along the photon is **0.0 cm** with a spread of ±0; the fraction displaced by more than 5 cm along the photon is **87.6 / 49.6 / 40.1 %** at DL and 86.8 / 47.4 / 38.9 % at the final vertex, while only **1.6 / 1.4 / 0.7 %** of the events move by more than 5 cm along the photon *after* the DL stage (and 1.9 / 3.0 / 1.9 % against it).

**Answer to roadmap V:** the photon-line displacement of truth-0p events is **already present at the DL-stage vertex (median +24.5 cm along the photon) and, before that, at the traditional vertex (+25.8 cm) and in the network's raw top-1 voxel (+36.1 cm)**; it is **not introduced after the DL**: the later refinement moves the vertex by 0.25 cm (median) and along the photon by more than 5 cm in 1.6 % of the events.

## 5. Where the stages differ  (MEASURED; `provenance_trad_dl_final_states.csv`, `dl_accept_and_snap.csv`)

* **Traditional -> DL.** The DL stage keeps the same vertex in most events (|DL - trad| median 0.0 cm; > 1 cm in 44.8 %, > 5 cm in 38.7 %). Where it moves, it moves **toward** the true vertex by more than 5 cm in 22.9 % of the events and **away** in 14.4 %; the net effect depends on the topology: toward / away = **19.9 / 18.1 %** (truth 0p), **23.9 / 11.6 %** (1p), **33.4 / 9.9 %** (>= 2p). Of the 7,805 events whose traditional vertex lies along the photon line, **6,098 (78 %) remain along it at the DL stage and 1,495 (19 %) are anchored by it**; 208 anchored traditional vertices are displaced along the photon by the DL.
* **DL -> final.** 0.21 cm (median); > 5 cm in 3.8 % (0p 3.8 %, 1p 4.1 %, >= 2p 2.6 %).
* **Anchoring fraction (within 5 cm of the true vertex), `vertex_anchoring_by_stage.csv`:**

| stage | truth 0p | truth 1p | truth >= 2p |
|---|---|---|---|
| traditional | 7.8 % | 31.7 % | 31.5 % |
| raw DL top-1 voxel | 4.4 % | 27.2 % | 57.4 % |
| DL-stage vertex | 12.6 % | 48.1 % | 60.3 % |
| final | 12.9 % | 49.6 % | 61.2 % |

The improvement from traditional to DL (7.8 -> 12.6 %, 31.7 -> 48.1 %, 31.5 -> 60.3 %) and the ~1 pp from DL to final show that **the anchoring is set at the DL stage and kept**.

## 6. Truth 0p versus 1p versus >= 2p: event-level provenance classes  (MEASURED; `provenance_classes_by_topology.csv`, fig2)

Exclusive hierarchy on the line-based states of `V_DL` and `V_final` (anchored / along / against / off-axis, 5 cm), after setting aside **S** (true conversion < 5 cm: the interaction vertex and conversion point are not separable, 2,426 events) and **F** (missing or unresolved, 497):

| class | truth 0p | truth 1p | truth >= 2p | all |
|---|---|---|---|---|
| **A** DL displaced along the photon, final stays there | **3,174** | 1,675 | 251 | 5,100 |
| **B** DL at the interaction vertex, final moves along the photon | 0 | 1 | 0 | **1** |
| **C** DL at the interaction vertex, final stays anchored | 247 | **1,570** | 368 | 2,185 |
| **D** DL displaced, final corrects toward the interaction vertex | 25 | 78 | 10 | 113 |
| **E** other DL / final disagreement | 316 | 427 | 44 | 787 |
| S not separable / F missing | 1,145 / 175 | 1,065 / 270 | 216 / 52 | 2,426 / 497 |

Among the separable, resolved events, **A = 62.3 %, C = 26.7 %, D = 1.4 %, E = 9.6 %, B = 0.01 %**: **a vertex displaced along the photon at DL time that stays there (A) is the commonest outcome (truth 0p: 84 % of its A-E events; 1p: 45 %; >= 2p: 37 %); "DL near the interaction vertex, then displaced by the refinement" (B) essentially never happens (1 event)**; the final correction (D) is 113 events. The 3 / 10 cm tolerances give the same pattern (A 5,128 / 4,763; B 1 / 17).

## 7. Proton anchoring  (MEASURED; `proton_anchoring_by_stage.csv`, fig3)

Event classes from the Phase-10/15 proton bookkeeping (KE > 35 MeV): true proton reco-typed / true proton merged / reco proton present but not a true proton (fake) / no reco proton. Fraction within 5 cm of the true vertex at the traditional / DL / final vertex:

| truth 1p, proton state | n | traditional | DL | final | median \|V_final - V_DL\| |
|---|---|---|---|---|---|
| **true proton reco-typed** | 2,802 | **42.0 %** | **67.5 %** | **68.7 %** | 0.00 cm |
| no reco proton | 1,371 | 16.6 % | 23.0 % | 25.4 % | 0.27 |
| reco proton, not a true proton (fake) | 359 | 19.8 % | 28.7 % | 29.0 % | 0.31 |
| true proton merged | 554 | 22.4 % | 24.5 % | 26.2 % | 0.34 |
| truth >= 2p, true proton reco-typed | 630 | 40.2 % | 80.3 % | 81.6 % | |

**The reco-typed true proton is associated with an anchored vertex already at the DL stage**: 42 % -> 67.5 % between the traditional and the DL vertex and +1.2 pp afterwards. A merged true proton does **not** anchor (24.5 %), a fake reco proton anchors only slightly more than no proton. So the proton does not act through the late PF refinement: it is associated with the vertex *choice* (the DL network input contains the proton's charge and the graph's vertex candidates sit at its start; a causal statement would need the network internals, NOT AVAILABLE).

## 8. Photon reconstruction state  (MEASURED; `vertex_by_photon_state.csv`, fig7)

Median |V_DL - V_true| / |V_final - V_DL| [cm] and the fraction anchored at DL:

| photon state | n | \|DL - true\| | \|final - DL\| | anchored (DL) | displaced > 5 cm along the photon at DL |
|---|---|---|---|---|---|
| A clean electron shower | 5,397 | 11.5 | 0.16 | 40 % | 55 % |
| muon-like dominant object | 1,079 | 13.1 | 0.09 | 41 % | 51 % |
| proton-like dominant object | 225 | 14.4 | 0.19 | 39 % | 51 % |
| **pion-like dominant object** | 784 | **28.0** | 0.34 | **15 %** | **84 %** |
| **fragmented (Phase 9)** | 2,114 | **31.6** | 0.48 | **9 %** | **90 %** |
| shower not in the main-vertex set (Phase 9) | 567 | 8.9 | 0.05 | 40 % | 32 % |

The pion-like and fragmented photon objects (Phase 15) are those whose DL-stage vertex is far (28-32 cm) and along the photon; the muon-like, proton-like and clean cases are anchored like the average; **in all of them the refinement moves the vertex by < 0.5 cm**. The shower-not-in-main-vertex-set events have a *well-anchored* vertex (40 % within 5 cm): their problem is not the vertex (`SIGNAL_PHOTON_SHOWER_ATTACHMENT_AUDIT.md`).

## 9. Effect on the frozen selection  (MEASURED; `stage_survival_by_vertex_class.csv`, fig8; no BDT rerun)

| class | events | shower stage | numu | other | ncpi0 | n_20br1 | final |
|---|---|---|---|---|---|---|---|
| A displaced along the photon | 5,100 | 4,087 (80.1 %) | 2,331 (57.0 %) | **1,053 (45.2 %)** | 498 (47.3 %) | 398 (79.9 %) | 398 = **7.8 %** |
| C anchored | 2,185 | 1,516 (69.4 %) | 1,275 (84.1 %) | **983 (77.1 %)** | 465 (47.3 %) | 455 (97.8 %) | 455 = **20.8 %** |
| D corrected | 113 | 103 | 82 | 64 | 26 | 25 | 25 |
| E other | 787 | 362 | 181 | 74 | 13 | 10 | 10 |
| S not separable | 2,426 | 1,818 (74.9 %) | 1,055 (58.0 %) | 579 (54.9 %) | 301 (52.0 %) | 255 (84.7 %) | 255 = 10.5 % |

(per-stage percentages are conditional on the previous stage.) **The stages most sensitive to vertex displacement are `other` (45 % vs 77 % conditional survival) and `numu` (57 % vs 84 %), then `n_20br1` (80 % vs 98 %); `ncpi0` is equal (47 % vs 47 %).** The shower stage goes the other way (80 % for displaced, 69 % for anchored): anchored events are the hadronic ones, where the attachment failure lives.

## 10. The 0p / 1p `other` difference  (MEASURED; `other_stage_vs_vertex_anchoring.csv`, `other_stage_gap_standardisation.csv`)

Among events reaching `other`: survival **47.4 % (0p), 63.2 % (1p), 65.4 % (>= 2p)**. Split by anchoring of the DL-stage vertex:

| | truth 0p | truth 1p |
|---|---|---|
| fraction anchored at DL | 16.2 % | **58.9 %** |
| `other` survival, anchored | 66.0 % | 75.8 % |
| `other` survival, not anchored | 43.8 % | 45.0 % |

The final vertex gives the same numbers (61.5 % anchored for 1p; 66.4 / 76.0 / 43.4 / 42.7 % survival). **The not-anchored events survive equally in 0p and 1p (43.8 / 45.0 %); 60 % (using the 0p rates) to 83 % (using the 1p rates) of the 15.8 pp 1p-0p gap is the different anchored fraction** (final vertex: 65 % to 93 %). The anchored fraction is set at the **DL stage** (section 5), not by the later refinement, so **the topology difference in `other` is present at DL-vertex time**; the residual ~10 pp inside the anchored events (66 vs 76 %) is not explained by the vertex.

## 11. Natural-CV check  (MEASURED; `natural_cv_check.csv`)

The natural NC-Delta CV files carry `T_dlvtx_call`; a small targeted read of the 105 files of the 117-event rehearsal region gave 216 records (108 candidates, 105 events; magnitudes only, the natural signal table has no photon direction). Median |V_DL - V_true| / |V_final - V_true| / |V_final - V_DL|: truth 0p (52 events) **21.8 / 19.3 / 0.21 cm**, truth 1p (42) **1.2 / 1.1 / 0.00 cm**, truth >= 2p (11) 30.9 / 33.7 / 0.35 cm; > 5 cm movement after the DL in 3 % of the events. The pattern (displaced 0p, anchored 1p, negligible refinement) is the official one at low statistics.

## 12. What is established

* The photon-line displacement of truth-0p events is present in the **traditional vertex, the raw network output and the DL-stage vertex**; the refinement after the DL changes the vertex by 0.25 cm (median) and does not introduce it (class B: 1 event).
* The DL stage re-selects among existing graph vertices; it anchors the vertex when a true reco-typed proton is present (42 % -> 67.5 % anchored) and is where the 0p / 1p anchoring difference is established.
* `other` and `numu` are the stages most sensitive to vertex displacement; 60-83 % of the 0p/1p `other` gap is the anchored fraction.

## 13. What remains unresolved

* *Why* the traditional vertexing and the network place the vertex along the photon in 0p events (the network input contains the photon's shower charge; its internals are not audited; the MicroBooNE-trained network is applied to SBND).
* Which stage (graph audit, pi0 displaced-vertex acceptance, main-cluster switch) causes the 3.8 % large post-DL moves: only the final vertex is recorded.
* The residual 66 vs 76 % `other` difference inside anchored events.
