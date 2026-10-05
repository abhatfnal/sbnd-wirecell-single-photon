# MicroBooNE → SBND Single-Photon BDT Compatibility Report

**Baseline**: `baseline_v0` — frozen reconstruction (WCT `251ff143`, sbndcode `v10_14_02_04`)
**Sample**: 59 NC Delta radiative events, full chain Gen→G4→DetSim→Reco1→WireCell complete
**Date**: 2026-10-05
**Constraint**: Measure only. Do NOT implement any fix in this report.

---

## Q1: Can the four BDTs be evaluated as-is on SBND `tracking-pr.root` with zero code changes?

**The frozen WireCell reconstruction does not invoke the BDT scoring step at all** — no
`single_photon_*_score` branch is present in any event file. An offline analysis script
is required regardless of input availability.

With the offline scorer `analysis/microboone_1gamma_v0/score_microboone_bdts.py`:

| BDT | Required inputs available? | Evaluable events |
|-----|---------------------------|-----------------|
| `single_photon_nue` (56 vars) | Yes — all shw_sp_* in T_tagger when shw_sp_filled=1 | 33/59 |
| `single_photon_numu` (73 vars) | Yes — same prerequisite | 33/59 |
| `single_photon_other` (146 vars) | Yes — `reco_nuvtxY` → `T_kine.kine_nu_y_corr` (DIRECT_EQUIVALENT_FOUND) | 33/59 |
| `single_photon_ncpi0` (45 vars) | Yes — `kine_pio_*` in T_kine + shw_sp_* in T_tagger | 33/59 |

**Update 2026-10-05**: The initial audit's conclusion that `reco_nuvtxY` is absent was
incorrect — it exists as `T_kine.kine_nu_y_corr` (source confirmed in NeutrinoKinematics.cxx).
See `RECO_NUVTX_MAPPING.md` for full provenance.

The frozen SBND WireCell output does **not** compute or store `single_photon_*_score` branches.
Every event has sentinel `nue_score=-15` unless `br_filled=1` (this is the Wire-Cell internal
scoring flag, not the evaluability limit of the offline scorer).

---

## Q2: Which BDT inputs are direct matches? Which are absent or detector-specific?

Input status across all 320 inputs from all four BDTs:

| Status | Count | Description |
|--------|-------|-------------|
| `DIRECT_MATCH` | 89 | Branch present in SBND tree with same name and compatible type |
| `PRESENT_BUT_UNFILLED` | 218 | Branch exists in `T_tagger` but holds default/sentinel when `shw_sp_filled=0` |
| `NEEDS_FURTHER_INVESTIGATION` | 12 | `kine_pio_*` in ncpi0 BDT: data in `T_kine`, not `T_tagger`; combined tree read required |
| `DETECTOR_SPECIFIC_REPLACEMENT_NEEDED` | 1 | `reco_nuvtxY` (initial audit); **RESOLVED 2026-10-05**: maps to `T_kine.kine_nu_y_corr` — see RECO_NUVTX_MAPPING.md |

Per-model summary:

| BDT | DIRECT | UNFILLED | PROBLEMATIC | Notes |
|-----|--------|----------|-------------|-------|
| numu (73) | 10 | 63 | 0 | 63 `shw_sp_*` inputs unfilled unless photon shower associated to main vertex |
| other (146) | 64 | 81 | 1 | `reco_nuvtxY` (VarIndex 145) hard-missing |
| ncpi0 (45) | 15 | 18 | 12 | 12 `kine_pio_*` in `T_kine` only; 18 `shw_sp_*` unfilled |
| nue (56) | 0 | 56 | 0 | All 56 inputs are `shw_sp_*`; all unfilled when prerequisite chain breaks |

Detail tables: `baseline_v0/tables/microboone_to_sbnd_bdt_input_mapping.csv`

---

## Q3: What fraction of the 59 NC Delta events have `shw_sp_filled=1`? `br_filled=1`?

Of 59 events total, 2 (evt_0039, evt_0052) have **no** `T_tagger` tree at all
(`nu_n_candidates=0`; Wire-Cell found no neutrino candidate vertex). All statistics
below are over the 57 valid events.

| Metric | Count | Fraction of 57 valid | Fraction of 59 total |
|--------|-------|---------------------|---------------------|
| `shw_sp_filled=1` | 33 | 57.9% | 55.9% |
| `shw_sp_filled=0` | 24 | 42.1% | 40.7% |
| `br_filled=1` | 17 | 29.8% | 28.8% |
| `br_filled=0` | 40 | 70.2% | 67.8% |
| No `T_tagger` (empty) | 2 | — | 3.4% |

`shw_sp_filled=1` indicates the tagger evaluated a photon shower in the main cluster.
`br_filled=1` indicates the fuller feature block (required for `nue_score`) was populated.
`br_filled` is a stricter requirement; 16 events have `shw_sp_filled=1` but `br_filled=0`.

Full per-event table: `baseline_v0/tables/ncdelta_single_photon_feature_availability.csv`

---

## Q4: For each of the four BDTs, how many events are ready for evaluation?

**Initial audit** (frozen WireCell output only, no offline scorer): 0/59 for all four BDTs.

**With offline scorer** (`analysis/microboone_1gamma_v0/score_microboone_bdts.py`):

| BDT | Evaluable events | Score range | Notes |
|-----|-----------------|-------------|-------|
| `single_photon_nue` | **33 / 59** | [−3.232, +1.361] | All shw_sp_* filled when shw_sp_filled=1 |
| `single_photon_numu` | **33 / 59** | [−3.820, +3.942] | shw_sp_filled=1 sufficient; br_filled not a gate |
| `single_photon_other` | **33 / 59** | [−2.579, +2.539] | kine_nu_y_corr = reco_nuvtxY equivalent (resolved) |
| `single_photon_ncpi0` | **33 / 59** | [−2.435, +0.886] | T_kine kine_pio_* + T_tagger shw_sp_* combined |

**Correction to initial audit**: The assumed cap of ≤17 (based on `br_filled=1`) was wrong.
`br_filled=1` is the Wire-Cell internal scoring flag, not the mechanical evaluability criterion.
All 33 events with `shw_sp_filled=1` have populated `shw_sp_*` inputs and are evaluable.
16 additional events (shw_sp_filled=1 but br_filled=0) are now scored by the offline scorer.

---

## Q5: Does the companion-cluster problem from event 0 repeat across the full 59-event sample?

**Yes — it is the dominant failure mode, not an isolated case.**

24/57 valid events (42%) have `shw_sp_filled=0` despite having a neutrino candidate vertex
reconstructed by Wire-Cell. In these events, `singlephoton_tagger()` found no shower
associated to `map_vertex_to_shower[main_vertex]` — the photon shower is either in a
companion cluster or was not reconstructed at the vertex.

An additional 2/59 events (evt_0039, evt_0052) have **no neutrino candidate at all**
(`nu_n_candidates=0`), representing a more upstream failure.

Combined upstream failure rate: 26/59 events (44%) never reach the shower-evaluation stage.

| Failure mode | Events | Fraction |
|-------------|--------|----------|
| No neutrino candidate (no T_tagger) | 2 | 3.4% |
| Neutrino candidate but shower inaccessible (shw_sp_filled=0) | 24 | 40.7% |
| Shower accessible (shw_sp_filled=1) | 33 | 55.9% |

Status upgrade: this is no longer OBSERVED_ONCE. See updated `SBND_1GAMMA_OBSTACLE_LOG.md`.

---

## Q6: Are the `single_photon_*_score` branches already computed and stored in `tracking-pr.root`?

**No.** None of the four score branches are present in any of the 59 SBND `tracking-pr.root`
files. The frozen SBND WireCell reconstruction does not invoke the `bdt_convert.cxx`
scoring step. Branches confirmed absent:

- `single_photon_nue_score`
- `single_photon_numu_score`
- `single_photon_ncpi0_score`
- `single_photon_other_score`

The branch `nue_score` IS present in `T_tagger` but this is the `nue_score` from the
`UbooneNueBDTScorer` (separate from `single_photon_nue`). Its value is `-15` (sentinel)
for 40/57 valid events (`br_filled=0`), and a real BDT score for 17/57 events.

---

## Q7: Can the 0p/Np split be implemented immediately from existing data?

**Yes — the data is available in `T_kine`.**

The 0p/Np split is defined as: events with at least one reconstructed proton candidate
with kinetic energy > 35 MeV (`kine_particle_type==2212` and `kine_energy_particle > 35 MeV`).

`T_kine` contains the required branches (`kine_particle_type`, `kine_energy_particle`)
for all 57 valid events. Implementation requires reading from `T_kine`, which is already
present and consistent across the sample. No code modification to the frozen reconstruction
is needed — a pure analysis-level calculation over existing output files.

From the scored 59-event sample: **29/59 events are 0p** and **30/59 are Np** (≥1 proton with
KE > 35 MeV, from `T_kine.kine_particle_type==2212` and `kine_energy_particle > 35 MeV`).

---

## Q8: Single most important blocker and smallest unblocking code change

### Single most important blocker

**The frozen SBND WireCell output does not invoke the single-photon BDT scoring step.**

`bdt_convert.cxx` (the MicroBooNE scoring code) is never called by the frozen
`wcls-img-clus-matching-xin-prod.fcl` or its SBND port. As a result:

1. No `single_photon_*_score` branch is populated.
2. The intermediate feature-filling code (`singlephoton_tagger()` full evaluation) may or
   may not have been adapted for SBND — this cannot be determined from outputs alone.
3. Even if scoring code were added, the companion-cluster routing issue (OBS-001, now
   QUANTIFIED) means 42% of events would yield unfilled inputs regardless.

The second-order blocker is the companion-cluster access pattern: 42% of events have a
reconstructed vertex but no associated shower, because `singlephoton_tagger()` only
accesses showers in `map_vertex_to_shower[main_vertex]`.

### Smallest unblocking code change (do not implement in baseline_v0)

**Update 2026-10-05**: The standalone offline scorer has been implemented at
`analysis/microboone_1gamma_v0/score_microboone_bdts.py`. All four BDTs are now evaluable.
The `reco_nuvtxY` obstacle was resolved: `T_kine.kine_nu_y_corr` is the direct equivalent
(see `RECO_NUVTX_MAPPING.md`). The scorer requires **no modification to frozen WireCell,
frozen FCL, or frozen reconstruction code**.

**Result**: 33/59 events scored for all four BDTs. 2/59 events pass the full pre-FV
MicroBooNE nominal selection. See `IMPLEMENTATION_REPORT.md` for full details.

### Smallest next reconstruction change (post-scorer, do not implement in baseline_v0)

The dominant remaining failure mode is 24/59 events (40.7%) with `shw_sp_filled=0` —
the photon shower is not accessible via `map_vertex_to_shower[main_vertex]`. At least
1 event (evt_0000) has a confirmed companion-cluster cause. For the remaining 23, the
cause is unresolved at the event level.

**Smallest unblocking reconstruction step**: Extend `singlephoton_tagger()` to iterate
over all Wire-Cell clusters (not just the main vertex cluster) when looking for associated
photon showers. This would require:
1. Modifying the shower-vertex matching in `singlephoton_tagger()` to check companion clusters.
2. Re-running WireCell reconstruction with the modified tagger on the NC Delta sample.
3. Validating that the change does not degrade BNB background rejection.

This is a new-baseline change, not a baseline_v0 change.

---

## Summary table

| Question | Answer |
|----------|--------|
| BDTs evaluable with offline scorer? | **Yes — all four, 33/59 events** (scorer implemented) |
| BDTs in frozen WireCell output? | No — `single_photon_*_score` not computed |
| Direct-match inputs / total | 89 / 320 (27.8%) |
| Unfilled inputs (present but default) / total | 218 / 320 (68.1%) |
| kine_pio_* (T_kine, ncpi0 BDT) | 12 / 320 (combined read implemented) |
| reco_nuvtxY → kine_nu_y_corr | 1 / 320 (RESOLVED — direct equivalent found) |
| `shw_sp_filled=1` events | 33 / 57 valid (55.9%) |
| `br_filled=1` events | 17 / 57 valid (29.8%) — Wire-Cell internal flag only |
| nue BDT evaluable (offline scorer) | **33 / 59** (corrected from ≤17) |
| numu BDT evaluable (offline scorer) | **33 / 59** |
| other BDT evaluable (offline scorer) | **33 / 59** (corrected from 0; reco_nuvtxY resolved) |
| ncpi0 BDT evaluable (offline scorer) | **33 / 59** |
| Events passing full pre-FV selection | **2 / 59** (0p=1, Np=1) |
| 0p/Np split | 29/30 (from T_kine proton counting) |
| Companion-cluster problem widespread? | Yes — 40.7% of valid events affected (QUANTIFIED) |
| Single most important blocker | 44% of events never reach shower evaluation (reconstruction limit) |
| Next reconstruction step | Extend singlephoton_tagger() to access companion clusters |
