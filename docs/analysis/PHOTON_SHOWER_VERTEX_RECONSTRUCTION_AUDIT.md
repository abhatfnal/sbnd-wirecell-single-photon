# Photon-shower and vertex reconstruction audit of the frozen Wire-Cell baseline on the official Gen2 NC-Delta signal

Date: 2026-11-10. Branch `analysis/ncdelta-shower-vertex-reco-audit-20261110` (from the pushed Phase-8 head 987e901). **Audit only: no cut, threshold, BDT, candidate policy or baseline decision is changed.** Every number is conditional on the provisional TPC truth box, policy `any`, the 35 MeV proton threshold, and the baseline stage flags.
Code: `scripts/shower_vertex_scan.py`, `scripts/other_bdt_proton_origin_scan.py --all-candidate-stage`, `scripts/shower_vertex_audit.py`, `src/sbnd_single_photon/shower_audit.py`, `shower_tables.py`. Detailed outputs: `$SP_DATA/shower_vertex_audit/official_ncdelta/` (event-level taxonomy, vertex geometry, connectivity, high-energy list, `metadata.json`); compact tables `tables/shower_vertex_audit/`; figures `plots/shower_vertex_audit/`.
Companion documents: `WIRECELL_SINGLE_PHOTON_SHOWER_COUNT_SEMANTICS.md` (source), `SIGNAL_PHOTON_RECO_FAILURE_TAXONOMY.md` (taxonomy definition, calibration, sensitivity).

**Language.** *Observed* = a measured distribution or fraction; *source-supported* = follows from the production code (commit `4b6853d4`); *association* = a stratified or regression statement with no counterfactual. No causal claim is made.

## 1. Motivation

Two Phase 6-8 observations call for a reconstruction-level explanation: (i) about a quarter of the candidate-stage signal events fail the `> 20 MeV shower` stage although every signal photon is far above 20 MeV, and the stage never becomes much more than 75-80 % efficient even for energetic photons; (ii) among events reaching `other`, 61 % of truth-1p but 28 % of truth-0p events have the leading shower detached from the vertex, and that detachment carries the whole 0p/1p `other` survival gap. Are these related, and what does the reconstruction actually do with the true photon?

## 2. Source semantics (detail: `WIRECELL_SINGLE_PHOTON_SHOWER_COUNT_SEMANTICS.md`)

`shw_sp_n_20mev_showers` counts, **per candidate**, electron-typed (start segment PDG 11) showers with `kine_best > 20 MeV` **among the showers whose START VERTEX is the candidate's main vertex** (`map_vertex_to_shower[main_vertex]`); showers anywhere else in the graph, in other candidates, or typed muon/pion/proton are never examined. If the main vertex has no shower the function returns before filling anything. `shw_sp_n_20br1_showers` is the subset that also passes `badreco1`. `shw_sp_filled` needs a *max shower* (`en20 && badreco1`), which `badreco2` (evaluated only when the stem is attached to the main vertex) does not influence. Consequently "fails the shower stage" is a statement about **typing and attachment to the main vertex**, not only about energy.

## 3. Signal-photon reconstruction association

Direct truth association, no spatial matching: the signal photon's G4 track id (`T_truth_pf`, vertex-matched to the signal neutrino, found in 11,331/11,331 events) labels reco pieces in `T_overlap` because the truth labeler assigns the e+/e- charge of a converted photon to the photon's own prong row (`q_readout > 0` in 98.9 % of events). Per event the dominant (candidate, T_kine row) holds the photon's in-candidate charge; its T_kine attributes and PF state are read from the stored tables (`SIGNAL_PHOTON_RECO_FAILURE_TAXONOMY.md` sections 2 and 4). 97.3 % of events have photon charge in at least one reco piece; 11.5 % of photon overlap rows lie in clusters that belong to no candidate.

## 4. Exact accounting of the 3,251 shower-stage losses

12,427 TPC-box events -> 11,331 with a candidate -> 8,080 pass -> **3,251 fail, all classified** (`taxonomy.csv`; asserted equal to the baseline `no_20mev_shower` count):

| failure class | n | % of the 3,251 | truth 0p / 1p / >=2p |
|---|---|---|---|
| photon shower typed muon / pion / proton | 961 | 29.6 % | 325 / 530 / 106 |
| energetic electron shower NOT in the main vertex's shower set | 567 | 17.4 % | 120 / 364 / 83 |
| photon fragmented over several particles | 492 | 15.1 % | 277 / 193 / 22 |
| photon reconstructed as a track | 424 | 13.0 % | 225 / 171 / 28 |
| photon charge mostly outside every candidate | 329 | 10.1 % | 163 / 151 / 15 |
| no reconstructed photon charge | 275 | 8.5 % | 79 / 173 / 23 |
| dominant object without a T_kine row | 162 | 5.0 % | 56 / 92 / 14 |
| electron shower with E_reco <= 20 MeV | **40** | **1.2 %** | 9 / 27 / 4 |
| photon in a candidate other than the signal-matched one | 1 | 0.03 % | 0 / 1 / 0 |

Delta0 / Delta+ columns are in the taxonomy document. **The energy threshold is essentially irrelevant: 1.2 % of the failures.** 42.6 % of the failures are photon objects typed as muon/pion/proton (shower or track), 25.3 % are fragmented or lie outside the candidates, 17.4 % are energetic correctly-typed showers that are not at the main vertex. The class mix differs by topology: truth 1p / >=2p lose 21 % / 28 % of their failures to "not in the main vertex set" (0p: 10 %); truth 0p loses more to fragmentation and track typing.

## 5. Energy dependence (`taxonomy_vs_photon_energy.png`, `taxonomy_high_energy.csv`)

Shower-stage pass fraction given a candidate: 71.3 % (all), 71.5 % (E > 100 MeV), 74.4 % (> 200), **80.2 % (> 400 MeV)**: it rises slowly and **does not approach 1**. The failure composition is nearly energy independent: for E > 400 MeV (387 failures) typed non-electron 114 (29 %), not in the main vertex set 91 (24 %), fragmented 56 (14 %), track 41 (11 %), outside candidates 29 (7 %), no charge 28 (7 %), row missing 20 (5 %), below 20 MeV 8 (2 %); for E > 200 MeV (2,226 failures) typed non-electron 31 %, not in set 18 %, fragmented 16 %, track 11 %. The ~20 % loss that remains at high energy is therefore a **typing / attachment / fragmentation** loss, not a calorimetric one. The ~75 % plateau of the cumulative stage efficiency seen in Phase 6 is this conditional 71-80 % times the 91 % candidate efficiency.

## 6. Conversion-distance dependence (`taxonomy_vs_conv_distance.png`, `taxonomy_by_photon_end_class.csv`)

* By Geant4 fate: in-volume pair conversions pass at 73.6 % given a candidate (49.6 % via a clean photon shower + 24.0 % via other showers/fragments); contained photoelectric/photonuclear endings 51 %; **photons that leave the volume: 78 % have no reconstructed photon charge** and only 11.7 % pass.
* **Among ordinary in-volume conversions the shower-stage pass fraction is flat in the true conversion distance** (0.74, 0.745, 0.735, 0.727, 0.736, 0.723, 0.728 for 0-100 cm; 0.66 at 100-150 cm): truth 0p 0.75-0.80, truth 1p 0.68-0.73. Conversion distance does not explain why some in-volume conversions fail the stage.

## 6b. What the final selection keeps

Of the 8,080 events that pass the `> 20 MeV shower` stage, 5,423 pass through a clean energetic electron photon shower and 2,657 do not (mostly fragmented photons; `SIGNAL_PHOTON_RECO_FAILURE_TAXONOMY.md` section 6). Of the **1,153 final-selected events, 1,131 (98.1 %) belong to the clean group** (final rate 20.9 %), 22 (1.9 %) to the other (0.8 %): the later stages (`n_20br1`, `numu`, `other`, `ncpi0`) remove almost all passes that are not carried by a clean photon shower, so the efficiency of the frozen chain is in practice limited to events with a cleanly reconstructed, correctly typed and main-vertex-attached photon shower.

## 7. Detector-edge dependence (`taxonomy_vs_edges.png`, `edge_three_way.csv`)

Separating "no candidate" from "candidate but shower-stage failure" by the distance of the true vertex to the nearest TPC-box face: no candidate 29.1 % (0-10 cm), 14.5 % (10-25), 7.0 % (25-50), 3.8 %, 2.8 %, 2.1 %, 1.1 % (150-250 cm); **candidate-but-shower-fail is 22-32 % at every distance (27 % at 0-10 cm, 22 % at 100-150 cm)**. By z the last 50 cm (450-500 cm) shows no-candidate 28.9 %; by x the outer 50 cm 16-18 %. The edge deficit of Phase 6 is a **candidate-formation** effect; the shower-stage failure rate is nearly edge independent. No FV is proposed.

## 8. Vertex reconstruction (`vertex_longitudinal_and_proximity.png`, `vertex_distributions.csv`, `vertex_effect_sizes.csv`)

For events with a signal-matched candidate (10,831; 10,348 with an in-volume conversion point) the reco neutrino vertex (`kine_nu_*_corr`) is decomposed relative to the true interaction vertex V_true, the true conversion point C_true and the true photon direction:

| quantity (median) | truth 0p | truth 1p | truth >=2p | effect size 0p vs 1p |
|---|---|---|---|---|
| \|V_reco - V_true\| [cm] | **27.8** | **4.8** | 2.4 | SMD -0.46, KS 0.37 |
| displacement along the photon direction [cm] | **+24.6** | **+1.1** | +0.5 | KS 0.41 |
| perpendicular displacement [cm] | 1.18 | 1.06 | 1.02 | KS 0.04 |
| projection on the interaction-to-conversion axis / conversion distance | **1.43** | **0.20** | 0.06 | KS 0.43 |
| reco shower start to reco vertex [cm] | **0.0** | 4.8 | 6.0 | KS 0.31 |

**In truth-0p events the reco vertex lies on the photon line, a median 25 cm downstream of the true interaction vertex (1.4x the conversion distance), at the reco shower start (distance 0.0 cm); in truth-1p and >=2p events it lies at the true interaction vertex (median offset 1.1 / 0.5 cm along the photon) and the shower starts ~4-6 cm away.** The perpendicular offset is the same (about 1 cm) in all classes: the displacement is purely longitudinal. Proximity classes (5 cm tolerance; sensitivity at 3 and 10 cm in `vertex_proximity_classes.csv`): interaction vertex 5.5 % (0p) / 32.9 % (1p) / 40.4 % (>=2p); conversion point 23.6 % / 7.6 % / 5.6 %; neither 44.1 % / 31.5 % / 24.2 %; not separable (conversion distance < 5 cm) 21-23 %. Shower-stage pass vs fail changes the picture little (e.g. truth 1p interaction-vertex class 34.0 % pass / 30.5 % fail).

## 9. Vertex-connectivity states (`connectivity_states.png`, `connectivity_states.csv`)

States of the dominant photon object, PF-tree based (validated: root shower = attached in 98.7 %; a shower under a root-level pseudo photon node = detached in 100 %; section 4 of the taxonomy document):

| state | truth 0p | truth 1p | truth >=2p |
|---|---|---|---|
| A: electron shower attached at the vertex (PF root) | 32.5 % | 16.9 % | 18.2 % |
| B: shower under a pseudo photon node at the vertex (detached by a gap, start vertex = main vertex) | 8.1 % | **23.2 %** | 23.7 % |
| C: connected through another particle (deeper in the tree) | 9.8 % | 14.9 % | 17.7 % |
| D: in the candidate but no PF path | 0.1 % | 0.2 % | 0.3 % |
| E: shower in another candidate | 0 | 0 | 0.1 % |
| F: no clean electron-shower object (track, non-electron typing, fragmented, no row, ...) | 49.4 % | 44.8 % | 40.1 % |

The vertex dimension (interaction vertex vs conversion point vs displaced) is section 8. Combining the two descriptions: a *detached* shower is an invisible photon between an anchored vertex and a displaced shower (state B), an *attached* shower is a shower that has become the vertex.

## 10. Why truth 1p detaches more often (61 % vs 28 %) (`detachment_fraction_explained.png`, `detachment_strata.csv`)

Population: events reaching `other` (Phase 8, 5,007; truth 0p 2,446, 1p 2,174). Observed accounting through the vertex anchoring state (|V_reco - V_true| <= 5 cm):

| | P(anchored) | P(detached \| anchored) | P(detached \| not anchored) | P(detached) |
|---|---|---|---|---|
| truth 0p | 16.8 % | 53.4 % | 22.4 % | 27.6 % |
| truth 1p | **60.9 %** | **82.8 %** | 27.0 % | 61.0 % |

Detached fraction by stratum: reco proton absent 23.7 % (0p) / 35.5 % (1p), present 46.5 % / 74.4 %; vertex not anchored 22.4 % / 27.0 %, anchored 53.4 % / 82.8 %; reco proton AND anchored vertex 80.0 % (0p, n=70) / 87.9 % (1p, n=1,091); neither 18.8 % / 24.8 %. For truth 1p the detached fraction depends on the conversion distance (38.6 % at 0-5 cm, 70-72 % at 5-20 cm, 62 % beyond), as expected when a gap needs a non-zero conversion distance; for truth 0p it is flat (22-34 %). Descriptive stepwise adjustment of the 1p - 0p detached-fraction difference (logistic + standardisation; 68 % intervals): raw **33.4 pp**; + reco proton present 17.8 pp; + vertex displacement along the photon 11.9 pp; + vertex anchored 4.0 pp [2.5, 5.3]; + conversion distance 3.4 pp; + photon energy and angle 2.7 pp [1.2, 4.0]; + candidate multiplicity 2.7 pp.

**Structurally:** a reconstructed proton at the true interaction point anchors the neutrino vertex there (section 11); once the vertex is at the interaction vertex the photon shower, which starts at the conversion point a few cm away, is by construction a gap-detached shower (83 % of anchored 1p events). In events without that anchor the vertex migrates to the shower (or along the photon line) and the shower is attached; there the detached fraction is the same in both classes (22 % / 27 %). About 92 % of the 33 pp difference is carried by the proton/anchoring/vertex-displacement variables. **Unexplained:** a residual of about 2.7 pp [1.2, 4.0]; whether the proton's reconstruction is the *cause* of the anchoring (rather than both being consequences of a visible hadronic vertex) is not tested.

## 11. Proton-origin dependence (`hadronic_origin_table.csv`, `proton_origin_vertex_and_shower_stage.png`)

Truth-1p candidate-stage events (5,170 in the TPC box) classified from the GENIE record (Phase 8 method): Delta+ decay proton 3,301; Delta+ FSI-created 294, ambiguous 73; Delta0 (decay nucleon is a neutron) FSI-created 1,476; not from the decay nucleon 26.

| class | shower-stage pass | vertex anchored (<=5 cm) | state A / B / C | typed non-electron / not in set | reco proton present |
|---|---|---|---|---|---|
| Delta+ decay proton | **65.6 %** | **54.0 %** | 15.6 / 25.0 / 14.2 % | 11.2 % / 7.5 % | 67.4 % |
| Delta+ FSI-created | 71.4 % | 39.1 % | 19.0 / 19.0 / 16.3 % | 7.8 % / 6.1 % | 55.6 % |
| Delta0 FSI-created | 69.2 % | 44.5 % | 19.2 / 20.0 / 16.1 % | 8.7 % / 6.4 % | 62.3 % |

Hypotheses quantified: (1) **a visible proton anchors the vertex**: truth-1p events *with* a reconstructed proton row have the vertex within 5 cm of the true vertex in 62.8 % (median longitudinal offset +0.36 cm) vs 27.0 % (+24.3 cm) *without* one; truth-0p events are 13.7 % / 11.2 % with a (necessarily fake) reco proton, so a *true* proton is what anchors the vertex. **Supported.** The decay proton anchors somewhat better (54.0 %) than FSI-created protons (39-45 %). (2) **anchoring makes the shower appear detached**: state B (detached through a pseudo photon node) is 25.0 % for decay-proton events vs 19-20 % for FSI-created ones; Phase 8 found 65.5 % vs 53-55 % detached among events reaching `other`. **Supported (modest).** The decay-proton events have the *lowest* shower-stage pass fraction (65.6 % vs 69-71 %), with more photon showers typed non-electron (11.2 % vs 8 %). (3) the higher `other` response is section 12.

## 12. Detached 0p versus detached 1p, and the `other` response (`other_survival_by_state.csv`, `detached_states_and_origin.png`, `detached_0p_vs_1p_effect_sizes.csv`)

"Detached" (`shw_sp_shw_vtx_dis > 0`, `br2`/`hol_2` inputs at default) is **not one reconstruction state**:

| among detached showers | truth 0p (n = 675) | truth 1p (n = 1,326) |
|---|---|---|
| vertex within 5 cm of the true vertex | **32.6 %** | **82.7 %** |
| reco proton present | 28.9 % | 79.9 % |
| PF state B (pseudo photon node at the vertex) | 48.4 % | 78.4 % |
| no clean electron-shower object (F) | 34.8 % | 12.0 % |
| median \|V_reco - V_true\| / along the photon [cm] | 28.1 / +17.4 | 1.0 / +0.2 |
| median `numu_1_score` | -0.35 | -0.47 (SMD -0.65, KS 0.47) |
| median frozen `other` score | 0.05 | 0.69 |

`other` conditional survival by state (0p / 1p): attached & vertex anchored 67.7 % / 64.9 %; attached & not anchored 46.3 % / 43.9 %; **detached & anchored 65.4 % / 78.6 %**; **detached & not anchored 33.4 % / 39.7 %**. So the survival is high when the vertex sits at the true interaction vertex (65-79 % in either class and either attachment) and low when it does not (33-46 %): the class effect is largely a **difference in the fraction of events in each state** (detached-1p: 83 % anchored, detached-0p: 33 %), with a residual 0p/1p difference inside the states (e.g. detached & anchored 65.4 % vs 78.6 %). Detached-1p showers are an *anchored vertex plus a displaced photon shower* (the BDT responds as to a hadronic vertex with a nearby shower); detached-0p showers are mostly a *vertex displaced along the photon line* (67 % not anchored). Both have `shw_vtx_dis > 0` but are different reconstruction states. Whether the BDT's behaviour on the anchored state is a MicroBooNE-training-domain effect remains untested (Phase 8). Inside truth 1p by proton origin: decay-proton detached 73.7 % vs FSI-created detached 68.1 %; attached 54.6 % vs 43.7 %.

## 13. High-energy failures (`high_energy_failure_events.csv`, `high_energy_failure_pf_sample.md`, `high_energy_failure_composition.png`)

The deterministic list of the **387 events with E_gamma > 400 MeV, a candidate, and no counted > 20 MeV shower** (sorted by run/subrun/evt; fields: topology, Delta charge, energy, conversion distance, true vertex, dominant object, candidate association, PF state, class) is outside Git, with a deterministic every-16th sample of 25 PF trees (not cherry-picked). Composition: typed non-electron 114, not in main vertex set 91, fragmented 56, track 41, outside candidates 29, no charge 28, row missing 20, below 20 MeV 8; by topology 205 truth 1p, 152 truth 0p, 30 >=2p. The deterministic sample (every 16th event, 25 PF trees; no event displays were available, so the reading is limited to the stored PF tables) has: not in the main vertex set 10, outside candidates 4, fragmented 3, typed non-electron 3, track 2, row missing 2, below 20 MeV 1. In the 10 "not in the main vertex set" cases the correctly reconstructed electron shower (reco energy 0.6-1.05 of the true photon energy, e.g. 337 MeV for a 529 MeV photon, 466 MeV for 425 MeV, 301 MeV for 471 MeV) is a **child of a pseudo photon node that hangs below a non-root particle**: below a proton in most cases, below a low-energy muon-typed object (12 MeV) in one case; i.e. the shower is connected to the graph but through a hadron or a mis-typed short track, not to the main vertex. In the typed-non-electron / track / fragmented cases the dominant photon object is a muon-, pion- or proton-typed object of 80-100 MeV at the root of the tree (reco energy 0.2-0.4 of the true). These are qualitative observations of 25 events and are not used for any number.

## 14. Shower energy response before the SP count (`shower_energy_response.png`, `shower_energy_response.csv`)

For the 6,061 events whose dominant photon object is an electron-typed shower (53.5 % of candidate-stage events; 63.6 % above 400 MeV): E_reco/E_true median **0.90 for counted and 0.89 for not-counted showers** (68 % band 0.60-1.08 vs 0.47-1.07): energy response does not distinguish them. Genuinely reconstructed below 20 MeV: 61 events (0.5 % of candidate-stage events; 1.0 % of electron showers); for true E_gamma > 100 / 200 / 400 MeV: 60 / 39 / 10 events (0.5 %, 0.4 %, 0.5 % of the candidate-stage events in that range). Muon/pion-typed photon showers have E_reco/E_true of about 0.6; track-typed about 0.4 (taxonomy document). The failure is **topology/typing/attachment, not calorimetric energy**.

## 15. Future common reconstruction-stage mapping (no performance comparison)

How the Wire-Cell failure classes correspond conceptually to the preselection of the SPINE NC-Delta analysis (one reconstructed primary shower > 25 MeV; containment; no muon / charged pion; proton channel). No SPINE efficiency is used or implied.

| SPINE preselection element | Wire-Cell counterpart | failure classes / states here |
|---|---|---|
| a reconstructed interaction | candidate (flash-matched bundle) | no candidate (1,096 events, mostly the detector edges); `photon_in_other_candidate` (1) |
| a reconstructed **photon/shower** exists | an EM object with charge in a candidate | `photon_no_reco_charge`, `photon_charge_outside_candidates`, `photon_shower_below_20MeV` |
| the shower is **primary** (attached to the interaction) | shower in the main vertex's set (start vertex = main vertex) | `photon_shower_not_in_main_vertex_set`; PF states B, C |
| shower PID (not muon / pion / proton) and "no muon / pi above 25 MeV" | start-segment typing 11; muon/pion-typed objects | `photon_shower_typed_non_electron`, `photon_as_track` (and the fact that a photon typed muon/pion can also count as a muon/pion for a veto in either chain) |
| shower completeness | one dominant particle | `photon_fragmented`, `photon_particle_row_missing` |
| containment | none in the baseline (flash/cosmic handling instead) | edge no-candidate fraction |
| proton channel (> 50 MeV) | reco proton rows (> 35 MeV; the 50 MeV projection of Phase 7) | vertex anchoring by a reco proton (section 11) |

A same-event comparison would classify each event by the pair (Wire-Cell class, SPINE class) with the Phase-7 keys.

## 16. What is established

1. All 3,251 shower-stage losses are classified (exactly); only 1.2 % are a genuinely sub-20 MeV reconstructed shower. The stage is a typing/attachment/fragmentation stage: 42.6 % typed muon/pion/proton, 25.3 % fragmented or outside candidates, 17.4 % energetic electron showers not at the main vertex.
2. The shower-stage pass fraction is 71-80 % and nearly energy independent for energetic photons; it is flat in conversion distance for in-volume conversions; edge effects are in candidate formation, not in the shower stage.
3. The count semantics are source-supported: only showers whose start vertex is the main vertex and that are electron-typed are examined.
4. The reco vertex of truth-0p events sits at the photon shower (25 cm along the photon line); that of truth-1p/>=2p events at the true interaction vertex; the proton, not the photon, anchors the vertex.
5. The 61 vs 28 % detached fractions are structurally the 61 vs 17 % probability that the vertex is anchored at the interaction vertex (an anchored vertex makes the shower gap-detached in 83 % of 1p events); about 92 % of the difference is carried by proton/anchoring/vertex-displacement variables.
6. Detached-0p and detached-1p are different reconstruction states; the `other` survival follows the vertex anchoring state.
7. Shower energy response does not separate counted from not-counted showers.

## 17. What remains unresolved

* Why 26 % (961) of the failed photon showers are typed muon/pion/proton while other photon showers are typed electron (the typing is the start-segment particle ID; its dependence on the first segment's dQ/dx/length near a short gap or a hadronic vertex is not tested).
* Why photons fragment (492) and what their fragments are (shower pieces typed 11 can make the stage pass: 1,622 passing events have a fragmented photon object).
* A residual 2.7 pp [1.2, 4.0] of the detachment difference after the proton/anchoring covariates, and whether the proton anchors the vertex causally.
* The BDT's response to the anchored-vertex/detached-shower state (training-domain question, Phase 8 item).
* The 50 % thresholds of the association (sensitivity documented) and that the geometry statistics are conditioned on the baseline's signal-matched candidate.

## 18. Implications for later optimization: questions only (no cuts are recommended)

* Is a photon shower typed muon/pion/proton, a fragmented photon, or an energetic electron shower below another particle a reconstruction limitation of this chain for NC-Delta or a pattern-recognition setting that a dedicated study should audit first?
* Which later stages (`numu`, `other`, `ncpi0`, `n_20br1`) act on a photon object that was never the cleanly reconstructed signal photon (2,657 passing events), and how does the final-selection purity of those events differ?
* Is the main-vertex-set requirement of the single-photon tagger appropriate when a proton anchors the vertex (most truth-1p events), and what would an anchoring-independent photon count look like?
* How should the `numu`/`other` stages be interpreted for the two detached states, and would a vertex-anchoring-independent reconstruction of the same events behave differently?
* Do the same failure classes appear, with similar fractions, in the SPINE reconstruction of the same events (Phase-7 keys)?
