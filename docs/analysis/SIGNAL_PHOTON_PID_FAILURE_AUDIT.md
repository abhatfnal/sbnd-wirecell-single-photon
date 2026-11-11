# Why is the true signal photon typed muon / pion / proton / track-like? Reconstructed-type confusion, persisted PID inputs and the effect on the frozen chain

Date: 2026-11-11. Branch `analysis/ncdelta-particle-pid-audit-20261111`. **Characterisation only**: no selection, BDT threshold, proton threshold, FV, PID or reconstructed-type change; nothing is hand-modified. Roadmap item **S**. Companions: `WIRECELL_PARTICLE_PID_SOURCE_AUDIT.md` (source), `SIGNAL_PROTON_PID_FAILURE_AUDIT.md` (item X), `SIGNAL_PHOTON_RECO_FAILURE_TAXONOMY.md` (Phase 9, labels unchanged), `SIGNAL_PHOTON_FRAGMENTATION_CLOSURE.md` (Phase 14). Tables: `tables/particle_pid_audit/`; figures `plots/particle_pid_audit/fig1, fig3, fig5, fig6, fig9, fig10`; row-level products in `$SP_DATA/particle_pid_audit/official_ncdelta/` (outside Git).

Tags: **SOURCE**, **MEASURED**, **NOT AVAILABLE** (a source input that is not persisted).

## 1. Scope

Population: the **11,331** official Gen2 NC-Delta TPC-box events with a Wire-Cell candidate (provisional box, frozen chain, candidate policy `any`, no FV). The *dominant reconstructed photon object* is the Phase-9 object (the (candidate, `T_kine` row) holding the largest share of the photon's in-candidate charge). A **significant piece** holds >= 10 % of that charge (Phase 14). Types are the row's PDG assignment and shower flag: e-shower, e-track, mu-like, pi-like, proton-like.

## 2. Truth association

The source-ranked `T_match` level-1 partner (point IoU, then charge IoU, then object index; Phase-10 `row_matches`, unchanged). A row is a **signal-photon row** if its top partner is the signal photon's prong. Common table: 83,097 rows (every candidate), of which 40697 are signal-photon rows and 6786 signal-primary-proton rows (`truth_matched_pid_objects.parquet`); each carries the key segment's persisted PID inputs (length, fit points, segment count, vertex degrees, vertex attachment, PF depth, pool, `T_segment` pdg / shower flag).

## 3. Source PID rules  (see the source audit)

Type of a track object = dQ/dx template (muon default) -> median fallback -> short-segment rule -> **main-vertex arbitration (only the longest muon candidate stays muon, every other becomes pion)**; a shower object inherits its start segment's type; the single-photon stage needs an electron-typed object. **The dQ/dx vector, the template scores and `particle_score` are NOT persisted**, so no muon/pion/proton-typed photon object has a dQ/dx on file.

## 4. Reco-type confusion  (MEASURED; `photon_confusion.csv`, `photon_pid_populations.csv`, fig1)

Dominant object's type, all 11,331 photons (no row = Phase-9 "no particle row", "no reconstructed charge" and "charge outside candidates"):

| reco type | events | fraction |
|---|---|---|
| e-shower | 6,980 | **61.6 %** |
| mu-like | 1,593 | **14.1 %** |
| pi-like | 1,164 | **10.3 %** |
| proton-like | 332 | 2.9 % |
| e-track | 30 | 0.3 % |
| no row / no charge / outside | 1,232 | 10.9 % |

So **27.6 % of the photons have a track-typed dominant object** (27.3 % mu / pi / proton). Versus the true photon energy (row-normalised, `dominant_type` variant): e-shower 51.6 / 60.1 / 67.4 / 73.2 % and mu-like 19.9 / 15.1 / 10.6 / 6.8 % for 100-200 / 200-300 / 300-500 / 500-1000 MeV; pi-like is flat (10.5 / 10.9 / 10.1 / 8.0 %), proton-like rises slowly (2.2 -> 4.1 %).

**PID populations (Phase-9 labels kept in `photon_pid_vs_phase9*.csv`):**

| class | events | share |
|---|---|---|
| A clean electron shower | 5,397 | 47.6 % |
| B electron shower, not usable by the single-photon stage | 617 | 5.4 % |
| C muon-like dominant object | 1,079 | 9.5 % |
| D pion-like dominant object | 784 | 6.9 % |
| E proton-like dominant object | 225 | 2.0 % |
| F electron-track / other track | 5 | 0.04 % |
| G fragmented (Phase 9), mixed types | 2,114 | 18.7 % |
| H no particle row | 383 | 3.4 % |
| I no reconstructed charge | 305 | 2.7 % |
| J charge outside candidates / other candidate | 422 | 3.7 % |

(Fragmented events are class G whatever their dominant type; the dominant type of the 2,114 is e-shower 45.7 %, mu 24.3 %, pi 18.0 %, proton 5.1 %, no row 5.8 %.) Class C and D overlap the Phase-9 `photon_as_track` (325 / 37 / 60 of C / D / E) and `photon_shower_typed_non_electron` states; the dominant objects of C-E are **non-shower-flagged segments in 99.8-100 %** (`frac_seg_flag_shower` 0.002 / 0.001 / 0.000, against 38 % of the e-shower objects).

## 5. Muon-like photons  (MEASURED inputs; SOURCE logic)

Compared with clean-shower dominant objects (non-fragmented events; `photon_pid_inputs.csv`, fig3):

| | e-shower | mu-like | pi-like | proton-like |
|---|---|---|---|---|
| events | 6,067 | 1,094 | 794 | 228 |
| segments in the object (median) | 14 | **1** | **8** | **1** |
| key-segment fit-path length (median, cm) | 13.7 | **20.8** | 15.0 | 13.0 |
| key segment >= 20 cm | 27 % | **52 %** | 23 % | 25 % |
| fit points of the key segment (median) | 24 | 36 | 26 | 23 |
| at the main vertex | 52 % | 54 % | **93 %** | 51 % |
| muon-typed sibling at the main vertex | - | **0 %** | 11 % (longer one) | 3 % |
| reconstructed energy of the object (median, MeV) | 240 | 105 | 132 | 160 |
| key segment flagged shower | 38 % | 0.2 % | 0.1 % | 0 % |

A muon-like photon object is a **single, long (median 21 cm), non-shower-flagged track segment**: over half of them exceed the 20 cm limit above which the source does not even offer the electron template, so the competition is muon-versus-proton with **muon as the default**. Which of the two the dQ/dx vector selects cannot be examined (NOT AVAILABLE). 54 % are at the main vertex, **where there is never a second muon**: they are the vertex's muon, the longest candidate.

## 6. Pion-like photons

Pion-like photon objects are different: **multi-segment (median 8 segments), 93 % at the main vertex, PF depth 0**, displaced from the vertex (median reconstructed-to-true vertex distance 27.8 cm against 9.9 cm for clean showers; anchored within 5 cm in 14 % against 43 %; the shower start is 10 cm from the true conversion against 1.9 cm). They are showers built around a **pion-typed start segment**. The source gives a mechanism that fits: at the main vertex the longest muon candidate keeps the muon type and every other becomes a pion, a topological label (SOURCE). Persisted evidence: 11 % of the pion-like photon objects have a longer muon-typed sibling at the main vertex (the rule's signature) and 93 % are at the main vertex, but **the other pion rules (proton-neighbour re-typing, the short-segment rule) cannot be separated from persisted inputs**: only 5 % of these objects are shorter than 4 cm, so the vertex-activity rule is not the main route. Measured correlation and source logic are therefore consistent but not proved to be the same thing.

## 7. Proton-like photons

228 non-fragmented events with a proton-like dominant object (class E: 225 events, 2.0 % of the photons). Single segment (median 1), median length 13 cm and reconstructed energy 160 MeV, 9 % shorter than 4 cm, 51 % at the main vertex, anchored like the clean showers (40 %): they are **single track segments whose dQ/dx competition ended proton**, typed at a vertex region where hadronic activity may overlap (the conversion-near-hadron hypothesis cannot be tested without dQ/dx). Statistics are low; nothing further is inferred.

## 8. Track-like photons (e-track / other)

Five events (class F) and 30 e-track dominant objects: a negligible population. An electron-typed *track* is a segment that kept an electron type from the template competition (length < 20 cm) or the bad-score rule; not studied further.

## 9. Energy response by reconstructed type  (MEASURED; `photon_energy_response.csv`)

| class | dominant row E_reco / E_true: median [16 %, 84 %] | sum of significant pieces / E_true |
|---|---|---|
| A clean electron shower | **0.90** [0.60, 1.08] | 0.99 [0.79, 1.10] |
| B electron shower, not usable | 0.91 [0.54, 1.07] | 0.97 [0.63, 1.08] |
| C muon-like | **0.52** [0.31, 0.77] | 0.69 [0.41, 0.87] |
| D pion-like | **0.52** [0.37, 0.73] | 0.73 [0.54, 0.92] |
| E proton-like | **0.56** [0.33, 0.81] | 0.70 [0.38, 0.94] |
| G fragmented | 0.36 [0.23, 0.50] | 0.83 [0.57, 1.06] |

**The type mistake is coupled to losing photon charge.** The dominant row of a mu / pi / proton typed photon holds about half of the true energy, and even the sum over all its significant pieces is 0.70 (clean: 0.99): the energy that goes missing is not recovered by the other pieces. Because a track-typed object's KE is the **range energy of the assigned type** (source), the typed energy is a different quantity from a calorimetric shower energy; a reasonable calorimetric reconstruction is *not* what these objects have.

## 10. Conversion geometry  (MEASURED; `photon_misclassification_vs_geometry.csv`)

Fraction of photons with a track-typed dominant object:

| variable | bins | fraction |
|---|---|---|
| conversion distance [cm] | <2 / 2-5 / 5-10 / 10-20 / 20-40 / >40 | 30.2 / 30.3 / 26.9 / 27.8 / 27.9 / 28.1 % |
| photon energy [MeV] | <100 / 100-200 / 200-300 / 300-500 / 500-1000 | 24.0 / 32.9 / 29.2 / 24.8 / **19.2 %** |
| cos theta (beam) | <-0.5 / -0.5-0 / 0-0.5 / 0.5-0.8 / >0.8 | 33.6 / 30.8 / 28.2 / 26.2 / 24.9 % |
| true vertex to nearest face [cm] | <20 / 20-50 / 50-100 / >100 | 26.0 / 30.4 / 27.8 / 25.4 % |

**Short conversion gaps are NOT more often mis-typed**: the rate is flat in conversion distance (27-30 %), so the hypothesis "a merged-with-vertex photon looks MIP/hadron-like" is not supported at this level. The only clear trend is with photon energy (lower energy, more track typing), plus a mild backward-direction excess (33.6 % for cos theta < -0.5). The fragmented fraction is flat too (15-22 %). No causal claim.

## 11. Fragments and PID  (MEASURED; `fragment_*.csv`, fig6)

The Phase-14 population reproduces: **1,622 fragmented shower-stage events, 83.5 % (1,354) with a track-typed significant piece, dominant piece 54.4 % electron shower / 20.8 % muon-like / 14.9 % pion-like / 3.9 % proton-like.** Why track-typed pieces?
* In **40.6 %** of them the **dominant** piece itself is track-typed; in 42.8 % the dominant piece is an electron shower and a minor piece is track-typed; in 25.6 % both (all fragmented events: 86.3 % / 48.5 %).
* **Small-charge pieces are not preferentially mistyped**: by charge fraction (0.1-0.2 / 0.2-0.3 / 0.3-0.5) the muon-like share is 15 / 22 / 24 % and pion-like 21 / 20 / 18 %: if anything the larger pieces are *more* often muon-like. By rank: dominant 24.3 % mu / 18.0 % pi, second 24.0 / 19.0 %, later 14.9 / 21.0 %.
* The track-typed pieces are **vertex-attached track segments**: 92-95 % of the muon / pion / proton pieces are pool 0/1 rows at PF depth 0, against 53 % of the electron-shower pieces; muon-like pieces are single segments (median length 17.5 cm), pion-like pieces median 2 segments, proton-like single segments of 123 MeV.
Answer: the pieces are typed by the **track machinery because they are graph segments attached at the main vertex** (not flagged shower), independent of their charge share.

## 12. Effect on the frozen selection  (MEASURED; `photon_pid_stage_fate.csv`)

Events reaching each stage (shower stage -> evaluable -> numu -> other -> ncpi0 -> n_20br1 -> final):

| class | all | shower | numu | other | ncpi0 | final |
|---|---|---|---|---|---|---|
| A clean electron shower | 5,397 | 5,397 | 4,101 | 2,552 | 1,278 | 1,129 |
| C muon-like | 1,079 | 304 | 76 | 10 | 3 | 2 |
| D pion-like | 784 | 333 | 74 | 24 | 2 | 2 |
| E proton-like | 225 | 69 | 21 | 7 | 0 | 0 |
| G fragmented | 2,114 | 1,622 | 582 | 150 | 24 | 14 |

Only **28 % / 42 % / 31 %** of the C / D / E events reach the shower stage (the photon is not an electron shower; those that do pass it through another electron shower), and **2, 2 and 0** survive the whole chain, against 20.9 % of the clean photons (1,129 of 5,397).

## 13. numu connection  (MEASURED; `numu_by_mu_pi_row_truth.csv`, `numu_failure_share.csv`, fig9)

For the 8,038 events that reach numu (5,007 pass, **3,031 fail**), the muon/pion-typed rows of the controlling candidate were classified by truth (source-ranked partner): of 7,531 such rows **5,755 are pieces of the signal photon**, 762 true hadronic objects of the signal interaction, 456 other signal-interaction objects (mostly low-energy photons), 466 cosmic / other-neutrino, 92 unmatched.

| the candidate's muon/pion-typed rows are | events | numu survival |
|---|---|---|
| none | 3,574 | **83.3 %** |
| only signal-photon piece(s) | **3,076** | **44.6 %** (median numu score 0.24) |
| only true hadronic object(s) | 443 | 58.0 % (0.71) |
| only other objects | 464 | 45.7 % |
| signal-photon piece(s) and true hadron(s) | 177 | 34.5 % |
| signal-photon piece(s) and other objects | 257 | 43.2 % |
| hadron and other objects (no photon piece) | 47 | 38.3 % |

**Headline:** of the **3,031 numu failures, 1,704 (56.2 %) have muon/pion-typed rows that are only pieces of the signal photon**, and **1,966 (64.9 %)** have at least one signal-photon piece among them; only **186 (6.1 %)** have only true hadronic objects, and 598 (19.7 %) have no muon/pion-typed row at all. Pure-hadron muon/pion rows barely hurt numu (58 % survival); photon pieces typed MIP/hadron by Wire-Cell itself cut it to 45 %. So the numu BDT is, for most of the signal it loses, **responding to a signal photon that Wire-Cell has typed as a MIP / hadron**. (An association, not a causal decomposition: the BDT's inputs are not re-run.)

## 14. Topology  (MEASURED; `photon_pid_by_topology.csv`)

| group | clean shower (A) | muon-like (C) | pion-like (D) | proton-like (E) | fragmented (G) | any track-typed dominant |
|---|---|---|---|---|---|---|
| truth 0p | 47.7 % | 8.1 % | 8.1 % | 1.5 % | **23.1 %** | 29.2 % |
| truth 1p | 47.0 % | 10.7 % | 5.6 % | 2.4 % | 15.5 % | 26.8 % |
| truth >= 2p | 50.5 % | 10.8 % | 7.2 % | 2.1 % | 11.5 % | 25.6 % |
| Delta0 | 47.4 % | 8.6 % | 7.9 % | 1.6 % | 20.8 % | 28.1 % |
| Delta+ | 47.9 % | 10.6 % | 5.8 % | 2.4 % | 16.1 % | 27.4 % |

**Does hadronic activity degrade photon PID?** Not through the track-typed rate (29 -> 27 -> 26 % with more protons): the truth-0p events (no hadron in the final state) are the *most* fragmented (23 %) and have the highest track-typed share. The muon-like and proton-like shares are higher with protons (8.1 -> 10.7 %, 1.5 -> 2.4 %), the pion-like and fragmented ones lower: protons shift *which* type the mistyped photon gets, not how often. Whether the photon topology interferes with proton PID is in `SIGNAL_PROTON_PID_FAILURE_AUDIT.md`.

## 15. Vertex provenance (limited; `photon_vertex_check.csv`)

By class, median reconstructed-to-true vertex distance / anchored within 5 cm: A 9.9 cm / 43 %; C muon-like 12.6 cm / 42 %; E proton-like 13.8 cm / 40 %; **D pion-like 27.8 cm / 14 %**; G fragmented 31.4 cm / 9 %. Muon- and proton-like photon objects are anchored like clean showers; pion-like and fragmented ones are not. The deep-learning-vertex comparison needs `T_dlvtx_call` rows that are **not in the derived tables**: **deferred** as a dependency of roadmap items T / V (no scan launched).

## 16. What is established

* 27.6 % of true signal photons have a track-typed dominant Wire-Cell object (mu 14.1 %, pi 10.3 %, proton 2.9 %); their objects hold about half of the true energy and the type error is **coupled to charge loss**, not a calorimetric artefact.
* The type is assigned by the **track machinery** to **non-shower-flagged, vertex-attached segments**: single long segments (muon-like, median 21 cm), multi-segment objects around a pion-typed start segment (pion-like), short single segments (proton-like). The main-vertex arbitration (one muon, every other candidate a pion) is a topological source rule consistent with the 93 % main-vertex attachment of pion-like objects.
* The track-typing rate is **flat in conversion distance**, falls with photon energy, and is not preferentially carried by minor fragments (the dominant piece is track-typed in 40.6 % of fragmented events).
* 56 % of the numu failures carry muon/pion-typed rows that are pieces of the signal photon.

## 17. Open reconstruction questions

* What the dQ/dx vector and the template scores of these segments are (**not persisted**): the template outcome for a photon segment cannot be examined; a producer-side addition of per-segment median dQ/dx, the three template scores and `start_n` / `end_n` would close the question.
* Which pion-typed photon objects came from the arbitration rule and which from the proton-neighbour or knob-gated rules (production knobs not audited).
* Why a photon's showering produces a vertex-attached *single long segment* rather than a shower-flagged object (the shower-topology RMS cut is a geometric statement about the associated-point cloud; its inputs are not persisted).
