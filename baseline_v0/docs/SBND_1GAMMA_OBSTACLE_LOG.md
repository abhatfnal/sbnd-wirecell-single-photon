# SBND Single-Photon Obstacle Log

**Purpose**: Evidence-based log of reproducible obstacles to the MicroBooNE→SBND Wire-Cell
single-photon selection port. Intended for eventual discussion with the Wire-Cell/SBND team.

**Baseline**: `baseline_v0` — faithful MicroBooNE port, frozen reconstruction.
Do NOT implement any fixes described here without creating a new tagged baseline.

---

## Status key

- `OBSERVED_ONCE` — seen in engineering sample, not yet reproduced at scale
- `REPRODUCED` — seen in ≥2 independent events
- `QUANTIFIED` — statistical measure from ≥10 events with same class
- `DISCUSSED` — raised with Wire-Cell/SBND reconstruction team
- `FIX_UNDER_DEVELOPMENT` — active work in progress (outside baseline_v0 scope)
- `RESOLVED` — no longer a blocker

---

## OBS-001 — Photon shower inaccessible to `singlephoton_tagger()` at main vertex

**Status**: `QUANTIFIED` (promoted from `OBSERVED_ONCE` 2026-10-05 after 59-event audit)

### Failure class label: `MAIN_VERTEX_SHOWER_INACCESSIBLE`

### Evidence

- Engineering Event 0 (run=1 subrun=0 event=7): companion-cluster inaccessibility
  directly demonstrated for this specific event.
- **59-event NC Delta sample (2026-10-05)**: 24/57 valid events have `shw_sp_filled=0` despite
  having a reconstructed neutrino candidate vertex in `T_tagger`. An additional 2/59 events
  have no `T_tagger` at all (`nu_n_candidates=0`).

### Observed fact (all 24 events)

Neutrino candidate vertex was reconstructed. `singlephoton_tagger()` found no shower
accessible at `map_vertex_to_shower[main_vertex]`, leaving `shw_sp_filled=0`.

### Possible causes (not all events individually confirmed)

- Photon shower in a companion cluster (directly confirmed: Event 0 only)
- Photon shower not reconstructed above imaging threshold
- Photon shower reconstructed but not associated with the main vertex in the cluster graph

Individual events are classified as `COMPANION_CLUSTER_SHOWER_INACCESSIBLE_CONFIRMED` only
when cluster-level evidence directly supports that conclusion. All other events in this
population are `MAIN_VERTEX_SHOWER_INACCESSIBLE` (unresolved cause).

**evt_0058 (RSE 120:0:664) confirmed 2026-10-05:** BFS topology probe establishes signal shower
(449 MeV, vtx_type=3) is in cluster 45 while main_vertex is in cluster 2, with no graph path
between them. kine_energy_included=3 (satellite keep → leftover pass). This event is now
`COMPANION_CLUSTER_SHOWER_INACCESSIBLE_CONFIRMED`. It was already counted in the
shw_sp_filled=0 pool; total count unchanged.

Note: evt_0014 and evt_0020 (previously listed as MAIN_VERTEX_SHOWER_INACCESSIBLE) were
reclassified to OBS-008 (graph-adjacent V1 keying failure) and have been recovered by Fix2-v2.
They are no longer in this pool.

### Quantitative summary (59-event NC Delta baseline_v0)

| Outcome | Events | Fraction of 59 | Class |
|---------|--------|---------------|-------|
| No neutrino candidate (no T_tagger) | 2 | 3.4% | `NO_NEUTRINO_CANDIDATE` |
| Vertex found, shower inaccessible at main vertex (shw_sp_filled=0) | 24 | 40.7% | `MAIN_VERTEX_SHOWER_INACCESSIBLE` |
| Shower accessible (shw_sp_filled=1) | 33 | 55.9% | (further classified) |

### Why it matters

An inclusive 1γ analysis requires reaching showers at photon conversion gaps of order
10–20 cm, which is geometrically frequent for NC Delta events. At 44% upstream failure
rate, fewer than half of signal events ever reach the BDT evaluation stage — regardless
of BDT performance.

### MicroBooNE→SBND question

In MicroBooNE, what fraction of NC Delta radiative photon showers appear in companion vs
main clusters? Does the SBND geometry (different drift volume, different aspect ratio) shift
this balance? The companion-cluster routing may be more common at SBND for moderate gaps.

### Possible remedies (do not implement in baseline_v0)

1. Extend `singlephoton_tagger()` to iterate over all clusters, not just `map_vertex_to_shower[main_vertex]`.
2. Define a companion-cluster photon score path.
3. Retrain the nue BDT to accept input from companion clusters.
4. Use NuGraph topology to seed the photon cluster search.

---

## OBS-002 — Contained/partially-contained true photon severely under-reconstructed in imaging

**Status**: `QUANTIFIED` (promoted from `OBSERVED_ONCE` 2026-10-05 after 59-event audit)

### Evidence

- Engineering Event 1 (run=1 subrun=0 event=215): first observation
  - Truth: photon E ≈ 308 MeV, TPC deposited ≈195 MeV; reco energy ≈94 MeV (≈48%)
- **59-event NC Delta sample (2026-10-05)**: Of 33 events with `shw_sp_filled=1`,
  16 (48%) have `shw_sp_energy < 100 MeV` against true photon energies of 130–460 MeV.
  Reconstruction efficiency (shw_sp_energy / leading_photon_E_MeV) ranges from **9% to 54%**
  across these 16 events. All are `clearly_contained` or `partially_contained` in truth.

### Quantitative summary (33 shw_sp_filled=1 events)

| shw_sp_energy range | Events | Fraction |
|--------------------|--------|----------|
| < 50 MeV (severe) | 7 | 21.2% |
| 50–100 MeV | 9 | 27.3% |
| > 100 MeV | 17 | 51.5% |

Worst cases: evt_0033 (9% of 255 MeV photon), evt_0019 (11% of 309 MeV), evt_0008 (13% of 403 MeV)

### Root cause (diagnostic)

Not yet established. Candidate hypotheses:

- Imaging efficiency low near the conversion point or at the conversion gap edges
- Charge deposition misattributed to other clusters or noise
- Wire-Cell clustering threshold cuts reducing connected SP count

### Why it matters

Under-reconstruction of the shower reduces the apparent shower energy, potentially moving
events below threshold even when the neutrino candidate is correctly identified.

### MicroBooNE→SBND question

MicroBooNE Wire-Cell imaging parameters are tuned to MicroBooNE readout noise and
electronics response. SBND uses different wire spacing (3 mm vs 3 mm, similar but not
identical) and different noise levels. Wire-Cell clustering parameters (min SP count,
clustering thresholds) may need SBND-specific tuning.

### Possible remedies (do not implement in baseline_v0)

1. Rerun imaging with adjusted threshold parameters.
2. Validate imaging efficiency as a function of deposited energy at SBND vs MicroBooNE.
3. Cross-check with Pandora/other reco if available.

---

## OBS-003 — Truth single photon routinely generates `kine_pio_flag=1`

**Status**: `QUANTIFIED` (promoted from `OBSERVED_ONCE` 2026-10-05 after 59-event audit)

### Evidence

- Engineering Events 0 and 1: first observation
  - Event 0: `kine_pio_energy_1 ≈ 158.8 MeV`, `kine_pio_energy_2 ≈ 33.1 MeV`, `kine_pio_angle ≈ 15.1°`
  - Event 1: `kine_pio_energy_1 ≈ 2.4 MeV`, `kine_pio_energy_2 ≈ 1.5 MeV`, `kine_pio_angle ≈ 10.4°`
- **59-event NC Delta sample (2026-10-05)**: `kine_pio_flag=1` in **48/57 valid events (84.2%)**.
  Only 8/57 events (14%) have `kine_pio_flag=0`. One event has missing T_kine data.
- `kine_pio_flag` is a reconstructed two-shower pi0 hypothesis, NOT pi0 truth

### Quantitative summary

| kine_pio_flag | Events | Fraction of 57 valid |
|---------------|--------|---------------------|
| 1 (two-shower reco pi0 candidate found) | 48 | 84.2% |
| 0 (no pi0 candidate found) | 8 | 14.0% |
| missing | 1 | 1.8% |

### Root cause (diagnostic)

A single photon shower fragmenting into multiple reconstructed shower objects can satisfy
the two-shower pi0 hypothesis. The `kine_pio_flag` algorithm treats any two-electron-like
clusters near the vertex as a pi0 candidate.

### Why it matters

If `kine_pio_flag` is used as a signal-vs-NC-pi0 discriminant, it will incorrectly reject
a fraction of true single-photon events. The rate of this misclassification vs photon energy
and showering profile must be measured.

### MicroBooNE→SBND question

Was this effect studied in MicroBooNE? The rate may depend on shower reconstruction
granularity and clustering parameters, which could differ at SBND.

### Possible remedies (do not implement in baseline_v0)

1. Use `kine_pio_flag` in veto mode only with care, not as a hard cut.
2. Add a truth-assisted split to separate true NC-pi0 from true single-photon candidates.
3. Retrain pi0 classifier to use additional photon conversion gap information.

---

## OBS-004 — `nue_score=-15` often means prerequisite features unfilled, not a nue/non-nue classification

**Status**: `QUANTIFIED` (promoted from `OBSERVED_ONCE` 2026-10-05 after 59-event audit)

### Evidence

- Engineering Events 0 and 1: first observation
- **59-event NC Delta sample (2026-10-05)**: 40/57 valid events have `nue_score=-15` (sentinel).
  Of these 40, all have `br_filled=0`. Only 17/57 (29.8%) events have a real `nue_score`.
- `nue_score=-15` is the sentinel from `UbooneNueBDTScorer` when `br_filled=0`

### Quantitative summary

| Metric | Count | Fraction of 57 valid |
|--------|-------|---------------------|
| `nue_score=-15` (sentinel, br_filled=0) | 40 | 70.2% |
| `nue_score` real BDT score (br_filled=1) | 17 | 29.8% |

### Root cause (diagnostic)

`nue_score=-15` is emitted when the shower feature block (`br_*`) was never populated.
This requires `shw_sp_filled=1`, which requires `singlephoton_tagger()` to have evaluated
a shower object. If the photon shower is in companion clusters (see OBS-001) or if imaging
fails (see OBS-002), the prerequisite chain is broken before BDT scoring.

`nue_score=-15` is therefore a diagnostic of upstream reconstruction failure, NOT a
classifier score indicating the event is non-nue-like.

### Why it matters

Applying any cut on `nue_score` that treats `-15` as a low-nue-score bin is incorrect.
Events with `-15` should be analyzed separately as a population with unmet prerequisites.
Conflating them with the scored population masks the true BDT performance on events where
the full chain was evaluated.

### Possible remedies (do not implement in baseline_v0)

1. Treat `nue_score=-15` events as a separate category in all analysis tables.
2. Always report `shw_sp_filled` and `br_filled` alongside `nue_score`.
3. In a future SBND adaptation, the shower-feature filling prerequisite chain should be
   mapped and its failure modes quantified independently.

---

---

## OBS-005 — `reco_nuvtxY` completely absent from SBND output; blocks `single_photon_other` BDT

**Status**: `RESOLVED` (2026-10-05)

### Original evidence

- Confirmed absent from `T_tagger` and `T_kine` in all 57 valid events (and 2 empty events).
- `reco_nuvtxY` is VarIndex 145 (the last variable) in `single_photon_other_bdt_final.xml`.
- `single_photon_other` has 146 inputs; without `reco_nuvtxY`, the BDT cannot be evaluated.
- `reco_nuvtxX` and `reco_nuvtxZ` are also absent (not required by other BDTs but confirming
  the MicroBooNE PFParticle reco vertex block is entirely missing from SBND output).

### Resolution (2026-10-05)

Source archaeology of `NeutrinoKinematics.cxx` (frozen baseline WCT `251ff143`) identified
`T_kine.kine_nu_y_corr` as a direct physical equivalent of `pfeval.reco_nuvtxY`. Both are
derived from `main_vertex->fit().point.y` in cm. The SBND branch uses the raw fitted vertex
(SCE correction not applied for `baseline_v0`).

The offline scorer (`analysis/microboone_1gamma_v0/score_microboone_bdts.py`) maps:
```
reco_nuvtxY → T_kine.kine_nu_y_corr
```
via `RECO_NUVTX_MAP = {"reco_nuvtxY": ("T_kine", "kine_nu_y_corr")}`.

`single_photon_other` is now evaluable for all 33 events with `shw_sp_filled=1`.
ROOT/TMVA cross-validation confirms correct evaluation (132/132 PASS, max |diff| = 4.94e-7).

Documented in: `analysis/microboone_1gamma_v0/docs/RECO_NUVTX_MAPPING.md`,
`analysis/microboone_1gamma_v0/docs/IMPLEMENTATION_REPORT.md` Step 1.

---

## OBS-006 — `kine_pio_*` variables in `T_kine`, not `T_tagger`; `single_photon_ncpi0` requires combined tree read

**Status**: `RESOLVED` (2026-10-05)

### Original evidence

- 12/45 inputs for `single_photon_ncpi0` are `kine_pio_*` variables (VarIndex 33–44).
- All 12 are in `T_kine` (confirmed present in 57/57 valid events with non-zero values).
- None are in `T_tagger`.
- `bdt_convert.cxx` reads them from `kine.*` (a C++ struct from the kine tree), with a
  commented-out line `//reader_single_photon_ncpi0.AddVariable("kine_pio_flag",&kine.kine_pio_flag)`.
  The active line uses a local temp variable: `AddVariable("kine_pio_flag",&temp_kine_pio_flag)`.
- The `single_photon_ncpi0` analysis pipeline therefore requires reading from **both**
  `T_tagger` (for the 33 `shw_sp_*` inputs) and `T_kine` (for the 12 `kine_pio_*` inputs).

### Resolution (2026-10-05)

The offline scorer (`analysis/microboone_1gamma_v0/score_microboone_bdts.py`) implements the
dual-tree read: `kine_pio_*` variables are loaded from `T_kine` per event and supplied at the
correct VarIndex positions (33–44) for the ncpi0 BDT.

A separate `kine_pio_flag` branch-type fix was also required: `T_kine.kine_pio_flag` is stored
as `Int_t`, not float. The Python scorer reads it with the correct type via `uproot`; the C++
validator uses `Int_t ival; b->SetAddress(&ival);` to avoid binary reinterpretation.

ROOT/TMVA cross-validation confirms ncpi0 evaluates correctly for all 33 events (33/33 PASS,
max |diff| = 4.81e-7). Documented in: `analysis/microboone_1gamma_v0/docs/TMVA_VALIDATION.md`,
`analysis/microboone_1gamma_v0/docs/IMPLEMENTATION_REPORT.md` Step 3.

---

## OBS-007 — Two events produce no neutrino candidate vertex (`nu_n_candidates=0`)

**Status**: `REPRODUCED` (2 events; ≥2 required for REPRODUCED; <10 same-class events for QUANTIFIED)

### Evidence

- `evt_0039` (run=90, subrun=2, event=479) and `evt_0052` (run=120, subrun=0, event=293)
  have no `T_tagger` tree in `tracking-pr.root`.
- `nu_n_candidates=0` in the Wire-Cell main output for these two events.
- Both events have `tracking-pr.root` file sizes in the normal range (~250K), indicating
  Wire-Cell ran to completion; it simply found no neutrino cluster candidate.
- `T_kine` is also absent (or empty) for these events.

### Root cause (diagnostic)

Wire-Cell's neutrino vertex identification stage found no candidate above threshold. This
can occur when:
- All reconstructed clusters are below the energy/topology threshold for neutrino ID.
- The photon shower is too short or too displaced to be identified as a neutrino candidate.
- Cosmic rejection removes the signal cluster before neutrino ID.

### Why it matters

These 2 events are completely inaccessible to any downstream single-photon analysis.
They represent a 3.4% hard loss floor from Wire-Cell's own vertex finding, independent
of the shower association issue in OBS-001.

### Possible remedies (do not implement in baseline_v0)

Investigation of what Wire-Cell reconstructed (if anything) would require examining the
full WCT output beyond `tracking-pr.root`. Not pursued in `baseline_v0`.

---

## OBS-008 — Photon shower graph-adjacent to main vertex but invisible to direct map lookup

**Failure class label**: `GRAPH_ADJACENT_SHOWER_NOT_VISIBLE_TO_DIRECT_MAIN_VERTEX_LOOKUP`

**Status**: `REPRODUCED — full-sample rate measured` (59-event NC Delta sample, 2026-10-05; 5/59 recovered by Fix2-v2)
**Date confirmed**: 2026-10-05
**Updated**: 2026-10-05 (full-sample census; evt_0058 reclassified; evt_0054 separated)
**Related**: OBS-001 (companion cluster inaccessible); this is an orthogonal failure mode

### Confirmed OBS-008 events and Fix2-v2 recovery

Two NC Delta events are confirmed OBS-008 failures (signal shower start_vertex exactly one
graph hop from main_vertex). Both are recovered by Fix2-v2 (59-event A/B study, 2026-10-05):

**Full-sample rate (59 events):** OBS-008 contributes directly to 5 recoveries by Fix2-v2
(evt_0012, 0014, 0016, 0020, 0026 — all BFS hops=1). Of the 59 events, Fix2-v2 recovers 5/59
events that were previously shw_sp_filled=0. The remaining 19 FALLBACK_ACTIVATED_NO_RECOVERY
events fail at distinct first-failure gates; see `fix2_no_recovery_failure_census.csv`.

OBS-008 narrowly defined (direct map-lookup miss, graph-adjacent shower):


| evt_idx | run | subrun | event | signal E (MeV) | vtx_type | hops | fix2_status |
|---------|-----|--------|-------|--------------|---------|------|-------------|
| evt_0014 | 50 | 0 | 449 | 121.6 | 1 | 1 (track, 33.6 cm) | **RECOVERED by Fix2-v2** |
| evt_0020 | 60 | 0 | 153 | 153.8 | 2 | 1 (track, 4.2 cm) | **RECOVERED by Fix2-v2** |

### Previously listed events — reclassified (2026-10-05)

**evt_0058 (RSE 120:0:664, 449 MeV):** Initially listed as OBS-008 based on the assumption
that its signal shower was keyed to V1 (the immediate graph neighbor). Graph-topology diagnosis
(BFS probe, commit cd7e7b3) established this is wrong. The 449 MeV signal shower's
`start_vertex` (vtx1, idx=1) is in cluster 45, main_vertex (idx=97) is in cluster 2.
Exhaustive BFS finds no path between them. vtx_type=3, `kine_energy_included=3` (leftover
pass via satellite keep, not BFS from main_vertex). **evt_0058 is a companion-cluster case
(OBS-001 class), NOT an OBS-008 case.** It was already counted in the 24-event
shw_sp_filled=0 pool under OBS-001; no count correction is needed.

**evt_0054 (RSE 120:0:529, 52.3 MeV):** Fix2-v2 Stage 2 finds 11 candidate showers (BFS hops=1,
39.6 cm path). The map-lookup step succeeds. However, the highest-energy shower (52.3 MeV) has
`pdg=13` (muon) assigned by `NeutrinoTrackShowerSep`. The `singlephoton_tagger`'s `pdg==11` gate
blocks it. **Classification: SHOWER_PDG_MISIDENTIFICATION** — distinct from OBS-008 (which is
about map-lookup routing, not downstream PDG gates). Source audited in
`development/fix2_vertex_shower_onehop_20261005/docs/SHOWER_PDG_FAILURE_AUDIT.md` (also
evt_0044, a second pdg=13 case). Not promoted to a standalone obstacle status based on 2 events;
tracked in the 59-event failure census as NEIGHBOR_SHOWER_WRONG_PDG category.

### Root cause (source-confirmed for evt_0014, evt_0020)

`shower_clustering_with_nv_in_main_cluster()` (`NeutrinoShowerClustering.cxx:852-1054`) BFS
traverses from `main_vertex`. When a shower segment is reached via one track-like segment
(the photon conversion gap), the shower receives `start_vertex = V1` (the conversion point),
not `main_vertex`. The conversion gap segment is absorbed into the shower by
`complete_structure_with_start_segment()`, preventing `shower_clustering_connecting_to_main_vertex()`
from creating a shower at `main_vertex` (gap segment already claimed in `map_segment_in_shower`).

`update_shower_maps()` (`NeutrinoShowerClustering.cxx:403-447`) keys `map_vertex_to_shower`
by stored `start_vertex`. The photon shower is in `map_vertex_to_shower[V1]`, not
`map_vertex_to_shower[main_vertex]`.

`singlephoton_tagger()` (`NeutrinoTaggerSinglePhoton.cxx:2354-2355`) exits immediately when
`map_vertex_to_shower.find(main_vertex) == end()`. `shw_sp_filled` stays 0.

`NeutrinoKinematics` (`NeutrinoKinematics.cxx:399-418`) uses `map_sg_shower` (segment-keyed),
finds the shower via BFS through the gap segment, and correctly assigns `kine_energy_included=1`.
This is the discrepancy between the two algorithms.

### Why it matters

evt_0014 and evt_0020 have large EM showers (121–154 MeV) one graph hop from the neutrino
vertex. Wire-Cell DOES reconstruct them, but the shower association routing prevents them
from reaching the tagger. Fix2-v2 recovers both.

### SBND-specific?

No. The failure is in generic `wct/clus/src/` code common to MicroBooNE and SBND.

### Fix status

**Fix2-v2 (implemented, under 59-event A/B study)**: Extends `singlephoton_tagger()` to
check `map_vertex_to_shower[V1]` for vertices V1 one graph hop from `main_vertex` (all edge
types). Recovers evt_0014 and evt_0020. Does not recover evt_0058 (companion-cluster, OBS-001)
or evt_0054 (downstream failure, unclassified). See
`development/fix2_vertex_shower_onehop_20261005/docs/FIX2_IMPLEMENTATION.md`.

---

## Future entries

New entries will be added as the generic BNB sample (Phase F) is reconstructed and analyzed,
or as the NC Delta sample is reanalyzed under a new baseline. Each new entry requires:

- At least one concrete event with RSE and relevant `tracking-pr.root` branches cited
- A clear statement of why it differs from the MicroBooNE expectation or is SBND-specific
- Status label from the key above
- Promotion from `OBSERVED_ONCE` only when reproduced in ≥2 independent events
