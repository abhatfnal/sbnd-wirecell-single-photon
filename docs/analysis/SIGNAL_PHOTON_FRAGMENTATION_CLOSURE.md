# What are the reconstructed fragments of the signal photon, where do they go, and why do almost none survive the frozen chain?

Date: 2026-11-11. Branch `analysis/ncdelta-pi0-pair-fragmentation-audit-20261111`. **Characterisation only**: no cut, threshold, BDT, FV, proton-policy or candidate-policy change. Roadmap item **U**; companion of `NCPI0_PAIR_MEMBER_TRUTH_AUDIT.md` (item Y) and of `SIGNAL_PHOTON_RECO_FAILURE_TAXONOMY.md` (Phase 9, definition source). Tables: `tables/pi0_pair_fragmentation_audit/fragment_*.csv`, `fragmentation_vs_ncpi0.csv`, `n20br1_*.csv`; figures fig6-fig8, fig10; row-level products `fragmentation_{objects,events,stage_fate}.parquet` in `$SP_DATA/pi0_pair_fragmentation_audit/official_ncdelta/` (outside Git). Population: the **8,080** official Gen2 NC-Delta TPC-box events with a > 20 MeV shower (provisional box, frozen chain, candidate policy `any`, no FV).

## 1. Definition  (restated from Phase 9; nothing changed)

* **Phase-9 "fragmented" (unchanged, SOURCE: `shower_audit.classify_failure`, `shower_tables.photon_association`).** The signal photon's reconstructed charge is `T_overlap` charge whose dominant truth track belongs to the photon family (the photon trackid and its conversion daughters, merged by the labeler). The **dominant object** is the (candidate, `T_kine` row) holding the largest share of the photon charge that lies inside candidates. The event is *fragmented* when that share is **< 0.5** (`DOMINANT_FRAC_MIN`). **1,622** events are fragmented at the shower stage.
* **Significant piece (this phase, POLICY, descriptive).** A (candidate, `T_kine` row) holding **>= 10 %** of the photon's in-candidate charge (`FRAGMENT_MIN_FRACTION`); 5 % and 20 % sensitivities are in `fragment_multiplicity.csv`. It does not change the Phase-9 flag.
* Truth is the charge-based `T_overlap` association of Phase 9 (the sufficient statistics of `T_match`); the row-level source-ranked `T_match` partner is used in the pair audit.

## 2. Fragment multiplicity  (MEASURED; `fragment_multiplicity*.csv`)

| population | events | significant pieces (mean / median) | leading charge fraction (median) | second (median) | rows (median) | shower / track rows (median) | clusters (median) | > 1 cluster |
|---|---|---|---|---|---|---|---|---|
| **fragmented (Phase 9)** | **1,622** | 3.26 / **3** | 0.41 | 0.28 | 3 | 2 / 1 | 2 | **79.2 %** |
| clean (Phase 9) | 5,423 | 1.49 / 1 | 0.94 | 0.05 | 1 | 1 / 0 | 1 | 26.3 % |
| other non-clean | 1,035 | 2.03 / 2 | 0.67 | 0.18 | 2 | 1 / 0 | 1 | 44.6 % |

Distribution of the number of significant pieces of the fragmented events: **2: 256, 3: 805, 4: 461, 5: 91, 6: 8, 7: 1** (at 5 % / 20 % thresholds the mean is 4.19 / 2.15). The pieces are in **one candidate** in all but 2 events (the candidate is the signal-matched or the only one). The leading piece carries a median **47.7 %** of the summed piece energy. **16 %** of the fragmented events have a piece that is not a `T_kine` row at all.

## 3. Reconstructed types of the pieces  (MEASURED; `fragment_type_*.csv`, fig6)

Type of a piece = the row's PDG assignment (`kine_particle_type`) and shower flag. **83.5 %** of the fragmented events have at least one track-typed significant piece (muon-like, pion-like, proton-like or electron track); only **3.3 %** are two electron showers and nothing else.

| combination (non-exclusive) | events | share of 1,622 |
|---|---|---|
| e + muon-like (no pion, no proton) | 455 | 28.1 % |
| e + pion-like | 263 | 16.2 % |
| e + proton-like (any) | 233 | 14.4 % |
| track + shower (>= 1 each) | 1,130 | 69.7 % |
| >= 3 significant pieces | 1,366 | 84.2 % |
| >= 2 electron-typed showers | 938 | 57.8 % |
| a piece without a particle row | 260 | 16.0 % |
| e + e only (2 pieces) | 53 | 3.3 % |

Most frequent exact combinations: e+e+mu 183 (11.3 %), e+mu+pi 151 (9.3 %), e+e+mu+pi 101 (6.2 %), e+e+pi 94 (5.8 %), e+e+e 93 (5.7 %), e+mu 85 (5.2 %). **The "dominant" object itself** is an electron shower in 54.4 % of the fragmented events, **muon-like in 20.8 %**, pion-like in 14.9 %, proton-like in 3.9 %, no row in 4.9 %: a fragmented event is the Phase-9 hierarchy's earlier-ranked class, so events whose dominant piece is muon- or pion-typed (35.8 %) would otherwise be called "typed non-electron" or "track" (`SIGNAL_PHOTON_RECO_FAILURE_TAXONOMY.md`).

## 4. Where do the pieces go?  (MEASURED; `fragment_location_*.csv`)

Exclusive hierarchy for each significant **non-dominant** piece (first match wins): other candidate -> other cluster of the same candidate -> no particle row -> under another particle (PF depth > 0 below a real particle) -> attached at the main vertex (PF root, child of the pseudo photon node, or pool-0/1 row) -> detached shower of the same cluster.

| location | pieces | share | events with >= 1 |
|---|---|---|---|
| **in another cluster (same candidate)** | **2,308** | **63.1 %** | **79.1 %** |
| attached at the main vertex | 1,023 | 28.0 % | 44.0 % |
| under another particle | 237 | 6.5 % | 12.0 % |
| no particle row | 86 | 2.4 % | 5.3 % |
| in another candidate | 4 | 0.1 % | 0.1 % |
| detached shower, same cluster | 1 | 0.0 % | 0.1 % |

**The pieces are overwhelmingly separate clusters inside the same candidate** (a gap in the imaging clusters), not other candidates and not detached showers of one cluster. Charge outside every candidate is small: median **2 %** of the photon's reconstructed charge, > 20 % in only 49 of 1,622 events. The `kine_energy_included == 3` / connection-type structure of the pieces is not separated here.

## 5. Why do fragmented events die?  (MEASURED; `fragment_stage_fate.csv`, `fragment_first_loss.csv`, fig7)

| stage | fragmented: events reaching / passing | conditional survival | clean (Phase 9): conditional survival |
|---|---|---|---|
| shower stage | 1,622 | - | 5,423 |
| BDT evaluable | 1,618 | 99.8 % | 99.4 % |
| numu | **582** | **36.0 %** | 76.4 % |
| other | **150** | **25.8 %** | 62.1 % |
| ncpi0 | **24** | **16.0 %** | 50.1 % |
| nue | 24 | 100 % | 100 % |
| n_20br1 == 1 | **14** | 58.3 % | 88.4 % |
| final | **14** | cumulative **0.86 %** | cumulative 20.9 % |

First stage that removes the event: **numu 1,036 (63.9 %)**, **other 432 (26.6 %)**, **ncpi0 126 (7.8 %)**, n_20br1 10 (0.6 %), not evaluable 4, final 14. (Exactly the chain quoted in the task: 1,622 -> 582 -> 150 -> 24 -> 14.)

**Does the ~0.9 % final survival come mainly from one stage?** **No: it is cumulative.** numu removes the most events in absolute terms (64 % of the population), but *every* stage suppresses fragmented events 1.5-3x more than clean ones (conditional survival 36 / 26 / 16 / 58 % against 76 / 62 / 50 / 88 %); the product 0.360 x 0.258 x 0.160 x 0.583 = 0.87 % is the observed cumulative survival.

**Descriptive mechanism per loss stage (`fragment_stage_mechanism.csv`; association, not proof):**

| first loss | n | median dominant energy [MeV] | share with a muon/pion-typed piece | dominant object not an electron shower | piece in another cluster | median numu score |
|---|---|---|---|---|---|---|
| numu | 1,036 | **90** | **83 %** | **54 %** | 75 % | **-0.66** |
| other | 432 | 94 | 69 % | 35 % | **86 %** | +0.85 |
| ncpi0 | 126 | 125 | 61 % | 21 % | 84 % | +0.82 |
| n_20br1 | 10 | 145 | 60 % | 0 % | 100 % | +0.87 |
| final (survive) | 14 | 128 | 71 % | 43 % | 71 % | +0.85 |

* **numu:** the removed events are the ones with the **lowest dominant-piece energy, a muon/pion-typed piece (83 %) and a non-electron dominant object (54 %)**; the numu score is strongly negative. The frozen numu BDT's inputs are the particle-type, length and daughter-track counts (`FROZEN_NUMU_BDT_SOURCE_AUDIT.md`), which are exactly what a muon-/pion-typed fragment feeds.
* **other:** the removed events have the largest share of pieces in another cluster (86 %); the numu score is already high. Consistent with the vertex-anchoring / connectivity dependence of the `other` BDT (`FROZEN_OTHER_BDT_SIGNAL_TOPOLOGY_AUDIT.md`), but **not proven here** (no `other`-score decomposition was made).
* **ncpi0:** see section 7. **n_20br1:** see section 8.
* The 14 survivors have 2-4 significant pieces and a leading charge fraction 0.32-0.50 (9 truth 1p, 5 truth 0p, none >= 2p; listed in `fragmentation_events.parquet`): the same piece structure as the other fragmented events.

## 6. Topology  (MEASURED)

Fragmentation is *more* frequent for truth 0p (**23.4 %** of 3,956 shower-stage events) than for 1p (**17.5 %** of 3,468) and >= 2p (**13.3 %** of 656); final survival of the fragmented events is 0.5 % (0p), 1.5 % (1p), 0 of 87 (>= 2p). The piece structure is the same (3.26 / 3.26 / 3.16 pieces; leading fraction 0.41 / 0.40 / 0.40); proton-like pieces occur in 14 % / 14 % / 22 % of the fragmented events.

## 7. Role in ncpi0  (MEASURED; `fragmentation_vs_ncpi0.csv`, fig8)

| Phase-9 photon state at ncpi0 | events | survival | kine pair | tagger pair | pair holds a same-photon fragment (kine / tagger) |
|---|---|---|---|---|---|
| clean | 2,556 | 50.1 % | 68.1 % | 9.0 % | 562 / 92 |
| **fragmented** | **150** | **16.0 %** | **93.3 %** | **18.0 %** | **87 / 19** |
| other non-clean | 75 | 12.0 % | 93.3 % | 18.7 % | 29 / 5 |

* Of the **1,468 ncpi0-rejected** events **126 (8.6 %)** are Phase-9 fragmented; **482 (32.8 %)** have a pair (kine or tagger) containing a same-photon fragment, but **406 of those 482 are not Phase-9 fragmented** (379 clean, 27 other non-clean: minor pieces or crumbs); **76** are both. So *event-level fragmentation (Phase 9)* explains **8.6 %** of the ncpi0 rejections, while *a same-photon piece inside a pair* is present in **32.8 %**; measured event by event, not inferred from scores. The remaining rejections are other pair mechanisms (neutron-capture-like photons, signal protons, section 6 of the pair audit).
* A fragmented photon is nearly always given a pair (kine 93 %), and survives ncpi0 at 16 % against 50 % for a clean photon.

## 8. Role in n_20br1  (MEASURED; `n20br1_mapping.csv`)

`n_20br1 == 1` removes **160** events, **126** of which have an extra shower row attributed (source-ranked `T_match`) to the signal photon (Phase 12). How those 126 map onto the shower-stage taxonomy:

| mapping | events | share |
|---|---|---|
| clean at Phase 9, a second significant piece (>= 10 % of the photon charge) below the 50 % dominance threshold | **77** | 61.1 % |
| clean at Phase 9, second piece of 5-10 % of the photon charge | 22 | 17.5 % |
| clean at Phase 9, extra row of < 5 % of the photon charge (or not a charge piece) | 17 | 13.5 % |
| already fragmented at the shower stage (Phase 9) | **10** | 7.9 % |

By Phase-9 state, 149 of the 160 failures are the "clean" state, 10 fragmented, 1 track. **The two definitions differ by construction**: Phase 9 asks whether one object holds >= 50 % of the photon's charge; `n_20br1` counts every electron-typed row above 20 MeV that passes br1, so a 20-100 MeV second piece of an otherwise dominant photon is "clean" for Phase 9 and a split for `n_20br1`. Only 10 of the 126 were already fragmented; the rest become split only under the later shower bookkeeping.

## 9. Final surviving fragments

14 events (0.86 % of 1,622). Types: e+mu+pi in 6, e+e in 1, e+e+mu+p, e+p+p, e+e+track, ... (listed in `fragmentation_events.parquet`); truth 5 0p / 9 1p / 0 >= 2p; median numu score +0.85 (above the 0.4 threshold by construction). No further inference is drawn from 14 events.

## 10. What is established

* The fragmented population (1,622) has a **median of 3 significant pieces, 79 % of events across more than one cluster of the same candidate, 84 % with a track-typed piece**; the dominant piece is a muon- or pion-typed object in 36 %.
* **Fragments are almost entirely separate clusters inside the same candidate**, not other candidates (0.1 %) and not charge outside every candidate (median 2 %).
* The 0.86 % final survival is a **cumulative** effect: every stage (numu 36 %, other 26 %, ncpi0 16 %, n_20br1 58 %) suppresses fragmented events 1.5-3x more than clean ones.
* Event-level fragmentation explains 8.6 % of the ncpi0 rejections; a same-photon piece inside a pair is present in 32.8 % (mostly clean events with a minor piece); 126 of the 160 `n_20br1` failures carry an extra signal-photon row, but only 10 of them were fragmented by Phase 9.

## 11. Open reconstruction questions

* Why the photon's charge splits into **separate clusters** (a gap in the imaging/clustering, the 3D clustering of the toolkit) and why the pieces are typed muon/pion by the dQ/dx template (a production-side question; no reconstruction change is proposed here).
* The mechanism of the `other` loss for fragmented events (no `other` score decomposition done).
* The truth-matching definition of a piece is charge-based (T_overlap) for fragmentation and point-IoU-based (T_match) for pair members; their differences on minor pieces are not quantified.
