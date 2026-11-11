# Why does a correctly reconstructed energetic electron shower of the signal photon sit outside the main-vertex shower set? The 567-event population

Date: 2026-11-11. Branch `analysis/ncdelta-shower-attachment-vertex-provenance-20261111`. **Characterisation only**: no selection, threshold, retraining, FV, proton-policy or candidate-policy change. Roadmap item **T**. Companions: `SHOWER_ATTACHMENT_SOURCE_AUDIT.md` (source), `NCDELTA_VERTEX_PROVENANCE_AUDIT.md` (item V), `SIGNAL_PHOTON_RECO_FAILURE_TAXONOMY.md` (Phase 9, population definition), `SIGNAL_PHOTON_PID_FAILURE_AUDIT.md` (Phase 15). Tables `tables/vertex_provenance_audit/attachment_*.csv`; figures fig4-fig6 (`plots/vertex_provenance_audit/`); row-level products `shower_attachment_events.parquet`, `shower_parent_objects.parquet` in `$SP_DATA/vertex_provenance_audit/official_ncdelta/` (outside Git).

Tags: **SOURCE**, **MEASURED**, **NOT AUDITED**. Mechanism language is descriptive (association) unless the source supports it.

## 1. Scope

Official Gen2 NC-Delta, provisional box, frozen chain. Truth is the source-ranked `T_match` partner (Phase-10 `row_matches`, Phase-14 taxonomy on it). The PF tree (`T_pf`) is the persisted record of ownership (section 2 of the source audit).

## 2. Source attachment rules  (SOURCE; `SHOWER_ATTACHMENT_SOURCE_AUDIT.md`)

`shw_sp_n_20mev_showers` counts only showers in **`map_vertex_to_shower[main_vertex]`**, i.e. showers whose **start vertex is the main vertex**, with an **electron-typed start segment** and **E > 20 MeV**. A shower seeded by the breadth-first builder gets the vertex at its **upstream end** (type 1), a gap shower or another cluster's shower gets the nearest candidate vertex (type 2 / 3 / 4), and the members of an accepted pi0 pair are re-seated at the pair vertex (type 2). In the PF tree an indirect (type 2 / 3) shower appears under a **pseudo-gamma wrapper**; its real parent is the object whose end it hangs from.

## 3. The 567-event population  (MEASURED; `attachment_population.csv`)

**Exactly reproduced:** the events with Phase-9 `outcome == photon_shower_not_in_main_vertex_set`: **567** (the Phase-9 state `photon_shower_not_in_main_vertex_set` holds for 5,970 events, because the 5,403 others pass the shower stage through another electron shower; the failure taxonomy applies only to the 567 with no > 20 MeV electron shower at any candidate's main vertex). All 567 fail the shower stage (`A_n20mev = False`) and have a candidate; their dominant object is an electron shower of median energy **212 MeV** (true photon 253 MeV): **not an energy failure**. The Phase-9 PF states: `deeper` 554, `photon_node_at_vertex` 12, `root` 1.

## 4. Where is the shower in the PF tree?  (MEASURED; `attachment_parent_class.csv`, `attachment_chain_structure.csv`, fig4)

Classes by the nearest *real* (non-pseudo) ancestor of the dominant shower node:

| class | events | share |
|---|---|---|
| A direct child of the main vertex node (root or root-level pseudo photon) | 13 | 2.3 % |
| **B under a proton-typed object** | **336** | **59.3 %** |
| **C under a muon-like object** | **124** | **21.9 %** |
| D under a pion-like object | 46 (11 of them also under a pseudo pi0) | 8.1 % |
| E under a generic (electron / other typed) object | 23 | 4.1 % |
| F under pseudo objects only (a pseudo pi0 at the root) | 25 | 4.4 % |
| G different candidate | 0 | |
| H unresolved | 0 | |

The commonest chains are `shower > pseudo-photon > proton` (311), `> pseudo-photon > muon` (106), `> pseudo-photon > pseudo-pi0` (25), `> pseudo-photon > pion` (20); the median **PF depth is 2** (shower, pseudo-gamma wrapper, real parent). **All 567 are pool-2 leftover showers** (connection type <= 3); `kine_energy_included == 3` (type 3, another-cluster association) in **10 %**; **94 % lie in a different cluster than the main vertex** (same cluster only 6 %: B 2 %, C 8 %, D 28 %); **all are in the signal-matched candidate** (0 in a different candidate). Only **36 events (6.3 %)** are members of a reconstructed pi0 pair (a pseudo-pi0 ancestor) — the earlier idea that these are mostly pi0-pair members is **not** supported.

## 5. What is the parent object, truly?  (MEASURED; `attachment_parent_truth*.csv`, fig5)

Truth of the nearest real ancestor (source-ranked `T_match` partner, no equating of reco type with truth):

| parent truth | events | share |
|---|---|---|
| **signal proton** | **352** | **62.1 %** |
| signal-photon piece (a photon fragment typed proton / muon / pion) | 87 | 15.3 % |
| ambiguous / mixed | 47 | 8.3 % |
| none (no real ancestor: classes A, F) | 46 | 8.1 % |
| other-neutrino hadron | 13 | 2.3 % |
| cosmic | 11 | 1.9 % |
| other signal hadron | 7 | 1.2 % |
| other signal EM / unmatched | 4 | 0.7 % |

By class: B (proton-typed parent): 293 of 336 are a true signal proton (87 %), 33 ambiguous, 2 photon pieces; C (muon-like parent): 47 true protons, **42 photon pieces**, 11 ambiguous, 8 cosmic, 9 other-neutrino hadrons; D (pion-like parent): 22 photon pieces, 12 protons; E (generic parent): **21 of 23 photon pieces**. So the hadron-like parent is a **true signal proton for 62 %** and **a mis-typed piece of the photon itself for 15 %**. The pi0 sibling (the other member of the pair) is a photon fragment in 16 of 36, a proton in 10.

## 6. Geometry and connectivity  (MEASURED; `attachment_geometry.csv`, `attachment_shower_distance_to_vertices.csv`, fig6)

| class | shower start to the final vertex (median, cm) | to the parent's start / end (cm) | parent KE (MeV) |
|---|---|---|---|
| all 567 | **19.7** [7.4, 57] | 18.7 / 18.1 | 76 |
| B proton-typed parent | 20.3 | 20.3 / 19.2 | 89 |
| C muon-like parent | 17.0 | 16.6 / 18.1 | 55 |
| D pion-like parent | 12.9 | 12.3 / 10.1 | 46 |
| E generic parent | 79.4 | 6.1 / 11.5 | 11 |

The shower starts **~20 cm from the main vertex and ~19 cm from both ends of its parent**, and **at the true conversion point**: the distance from the shower start to the true vertex is 1.04 x the true conversion distance (median; within 5 cm of it in 67 %), and the conversion distance of these photons (median 14.1 cm) is the same as for clean photons (13.3 cm). The shower reconstruction itself is therefore good; **the gap between the interaction vertex and the shower is the photon's conversion gap**, which the PR graph bridges (indirect connection) to a hadron-typed object near the vertex instead of to the main vertex. Class E is different (79 cm from the vertex, `included == 3`, 91 %): another-cluster associations whose parent is a photon piece.

## 7. Hadronic-activity dependence  (MEASURED; `attachment_failure_rate_by_hadronic_activity.csv`)

Rate = failures / (failures + clean passes) = 567 / 5,990:

| group | denominator | failures | rate |
|---|---|---|---|
| truth 0p | 2,619 | 120 | **4.6 %** |
| truth 1p | 2,808 | 364 | **13.0 %** |
| truth >= 2p | 563 | 83 | **14.7 %** |
| true proton reco-typed | 2,077 | 335 | **16.1 %** |
| reco proton present, not a true proton (fake) | 622 | 76 | 12.2 % |
| true proton merged | 432 | 34 | 7.9 % |
| no reco proton | 2,859 | 122 | **4.3 %** |
| Delta+ | 2,841 | 341 | 12.0 % |
| Delta0 | 3,149 | 226 | 7.2 % |

Mechanism by topology (`attachment_mechanism_by_topology.csv`): **truth 1p: 281 of 364 (77 %) under a true hadronic object of the signal interaction**; truth >= 2p: 47 of 83 (57 %); **truth 0p: 54 of 120 (45 %) under a track-typed piece of the photon itself** (type inheritance / fragmentation) and only 29 (24 %) under a true hadron, 15 pi0 pairs. So with hadronic activity the failure rate triples (4.6 -> 13 %) and the graph mechanism is **ownership by a hadron-typed object**; in truth 0p, where no hadron exists, the same configuration arises from the photon's own pieces typed as hadrons (Phase 15).

## 8. Event-level mechanism hierarchy  (MEASURED; `attachment_mechanism.csv`)

| mechanism (exclusive, descriptive) | events | share |
|---|---|---|
| indirect shower under a **true hadronic object** of the signal interaction | **357** | **63.0 %** |
| indirect shower under a track-typed object that is **itself a piece of the signal photon** (type inheritance / fragmentation) | 82 | 14.5 % |
| indirect shower under another object (generic / other truth) | 79 | 13.9 % |
| member of a **reconstructed pi0 pair** | 36 | 6.3 % |
| direct child of the main-vertex node or root (start vertex differs) | 13 | 2.3 % |

Several populations coexist: the dominant one is graph / topology **ownership** (indirect connection across the conversion gap to a hadron-typed object, 63 % + 14 % + 14 %); within it, **object-type inheritance** (the parent is a photon piece typed as a hadron) is 14.5 %; pi0-pair membership 6 %; no "physically connected charge" case is separately identified (the truth of the parent says the objects are distinct particles).

## 9. DL vertex versus final vertex  (MEASURED; `attachment_shower_distance_to_vertices.csv`)

Median distance of the shower start to the **true / DL / final** vertex: **21.7 / 19.7 / 19.7 cm**; |V_final - V_DL| median **0.05 cm**. The DL-stage vertex is within 5 cm of the true vertex in **40 %** of these events (B: 50 %, truth 1p 41 %, truth 0p 12 %) and the shower is within 5 cm of the final vertex in only **8 %**; it is closer to the final vertex than to the true vertex in 44 %. **The vertex is neither displaced to the shower (DL = final, both ~20 cm from it) nor moved by the later refinement: the failure arises in the ownership assignment with the vertex fixed** — the vertex is, in 40 %, at the right place and the shower is ~20 cm away across the conversion gap. Provenance classes of the 567 (`attachment_dl_vs_final_class.csv`): A (DL displaced along the photon) 91, **C (DL anchored, final stays anchored) 171**, D 6, E 184, S 104, F 11.

## 10. Consequences for the frozen selection

All 567 fail at the shower stage (no > 20 MeV electron shower in the main-vertex set; the tagger never sees the shower). They are the part of the shower-stage loss that depends on hadronic activity (13-15 % of the clean-or-attached population in hadronic events against 4.6 % without hadrons), complementary to the 2,114 fragmented and the 1,079 + 784 + 225 mis-typed events (Phase 15).

## 11. What is established

* The 567 events are good electron showers (212 MeV median) lost to **ownership**: the shower is attached through a pseudo-gamma (indirect) connection to an object whose end it hangs from, and only showers with start vertex = main vertex are counted.
* The parent is a hadron-typed object that is a **true signal proton in 62 %** and a **mis-typed photon piece in 15 %**; pi0-pair membership is 6 %.
* The shower starts at the true conversion point (~20 cm from the vertex); the conversion distance is not unusual.
* The failure rate is 4.6 % (truth 0p) -> 13 % (1p) -> 14.7 % (>= 2p), 16 % with a reco-typed true proton.
* Neither the DL vertex nor the refinement is responsible: DL = final, and the vertex is anchored in 40 %.

## 12. Open reconstruction questions

* Why the builder / nearest-vertex rule prefers the hadron-typed object's vertex to the main vertex across a ~20 cm gap (the candidate-vertex selection for type-2 connections is geometric; its exact choice for each event is not persisted).
* The persisted proxy for the connection type (PF wrapper, pool, `included`) is not the connection type itself.
* Production values of the knob-gated EM merge / split steps.
