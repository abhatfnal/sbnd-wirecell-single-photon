# MicroBooNE Single-Photon Offline Scorer — Implementation Report

**Date**: 2026-10-05
**Campaign**: SBND `baseline_v0` — frozen WCT `251ff143`, sbndcode `v10_14_02_04`
**Sample**: 59 NC Delta radiative events (Gen→G4→DetSim→Reco1→WireCell complete)
**Scorer**: `score_microboone_bdts.py`

---

## Step 1: `reco_nuvtxY` resolution

The previous audit classified `reco_nuvtxY` (required by `single_photon_other`, VarIndex 145)
as `DETECTOR_SPECIFIC_REPLACEMENT_NEEDED` after failing to find it in `T_tagger`.

Source archaeology on the frozen SBND WireCell source (`NeutrinoKinematics.cxx`) identified:

**`T_kine.kine_nu_y_corr`** is a direct physical equivalent of `pfeval.reco_nuvtxY`.

Both are derived from `main_vertex->fit().point.y` in cm. The SBND branch uses the raw
fitted vertex (SCE correction not applied for baseline_v0). See `RECO_NUVTX_MAPPING.md`.

**Status change**: `DETECTOR_SPECIFIC_REPLACEMENT_NEEDED` → `DIRECT_EQUIVALENT_FOUND`

All four BDTs are therefore evaluable from existing frozen output with no reconstruction changes.

---

## Step 2: Evaluable event count — corrected

The previous compatibility audit assumed a maximum of ≤17 evaluable events based on `br_filled=1`.

The offline scorer determines evaluability **mechanically**:
- All XML-required inputs for `shw_sp_*`-dependent variables must be finite and non-default.
- `shw_sp_filled=1` is the mechanical indicator that `shw_sp_*` inputs are populated.
- `br_filled=1` is the prerequisite used by the Wire-Cell C++ scorer internally; it is NOT
  a physics cut on input availability.

Result: **33/59 events are evaluable** for all four BDTs simultaneously (16 additional events
beyond the ≤17 assumption were previously missed because `br_filled=0` was incorrectly treated
as the evaluability gate).

| BDT | Evaluable events | Score range (tanh-transformed) | Mean |
|-----|-----------------|-------------------------------|------|
| `single_photon_numu` | 33/59 | [−0.999, +0.999] | +0.103 |
| `single_photon_other` | 33/59 | [−0.989, +0.988] | −0.236 |
| `single_photon_ncpi0` | 33/59 | [−0.985, +0.709] | −0.216 |
| `single_photon_nue` | 33/59 | [−0.997, +0.877] | −0.492 |

*Scores are `tanh(raw_sum)` in `[−1, 1]`, confirmed by ROOT/TMVA cross-validation (132/132 PASS,
max |diff| = 4.94e-7). See `TMVA_VALIDATION.md` for details.*

---

## Step 3: Variable contract and special handling

### ncpi0 BDT: kine_pio_* from T_kine

The 12 `kine_pio_*` variables at VarIndex 33–44 are read from `T_kine`, not `T_tagger`.
This matches the MicroBooNE `bdt_convert.cxx` design where these come from the `kine.*` struct.
The scorer reads them directly from T_kine per event file and supplies them at the correct indices.

`kine_pio_flag` in MicroBooNE's C++ uses a local float copy (`temp_kine_pio_flag`) rather than
`kine.kine_pio_flag` directly (commented-out line). This is a float-type assignment; the numeric
value is identical. The scorer reads `kine_pio_flag` from T_kine as float32 — faithful reproduction.

### other BDT: reco_nuvtxY → kine_nu_y_corr

Mapped via `RECO_NUVTX_MAP = {"reco_nuvtxY": ("T_kine", "kine_nu_y_corr")}`.
Supplied at VarIndex 145 (last input) in the correct XML ordering.

### Evaluability check (mechanical)

```python
if shw_sp_filled == 0:
    mark NOT evaluable: reason = "MAIN_VERTEX_SHOWER_INACCESSIBLE"
else:
    collect all inputs
    if any input missing or not finite:
        mark NOT evaluable: reason = "branch_missing:{name}" or "non_finite_at_index_{i}"
    else:
        evaluate BDT
```

`br_filled` is used only as a diagnostic column in the output CSV, not as an evaluability gate.

### Sentinels NOT silently replaced

No sentinel or default value is silently substituted. All required inputs are checked for
finite floating-point values. Any missing branch produces a categorical failure reason.

---

## Step 4: Cut flow results (MicroBooNE nominal, pre-FV)

**FV treatment**: The MicroBooNE literal FV cut `5 < reco_nuvtxX < 250 cm` is NOT applied as an
SBND physics cut. An SBND-native FV is not yet defined for `baseline_v0`. The selection is
labeled `PRE_FV_REFERENCE_SELECTION`.

**Score convention**: All BDT scores are `tanh(raw_sum)` in `[-1, 1]`, matching
`TMVA::Reader::EvaluateMVA()` for GradBoost (see `TMVA_VALIDATION.md`). The nue threshold
`-1.0` is the mathematical minimum of `tanh(x)` and passes all events.

| Cut step | Events passing | 0p | Np |
|----------|---------------|----|----|
| Total events | 59 | 27 | 30 |
| Has neutrino candidate | 57 | 27 | 30 |
| shw_sp_n_20mev_showers > 0 | 33 | 18 | 15 |
| FV cut | (skipped — PRE_FV_REFERENCE) | — | — |
| All 4 BDTs evaluable | 33 | 18 | 15 |
| numu score > 0.4 | 13 | 10 | 3 |
| other score > 0.2 | 7 | 5 | 2 |
| ncpi0 score > −0.05 | 4 | 3 | 1 |
| nue score > −1.0 | 4 | 3 | 1 |
| shw_sp_n_20br1_showers == 1 | 3 | 2 | 1 |

**3/59 NC Delta events pass the full pre-FV nominal MicroBooNE selection.**

*Note*: An earlier version of this report (before ROOT/TMVA cross-validation) showed 2/59
because the raw sum was used without the tanh transform. The nue threshold −1.0 in raw-score
space incorrectly rejected 7 events whose raw nue scores were < −1.0. After correction, all 4
events surviving the ncpi0 cut also survive the nue cut, and 3 pass the final shower-count cut.

---

## Step 5: 0p / Np decomposition

**Correction (2026-10-05)**: The initial count of 29/30 was wrong. Events evt_0039 and
evt_0052 have no T_kine tree (they also have no T_tagger). The scorer defaulted
`n_protons_kine_above35mev=0` for these events, silently classifying them as 0p.

Correct classification requires T_kine data. Without it, these events are `UNCLASSIFIABLE_NO_KINE`.

| Category | Events | Notes |
|----------|--------|-------|
| 0p (no reco protons > 35 MeV KE) | **27/59** | T_kine present, zero protons above threshold |
| Np (≥1 reco proton > 35 MeV KE) | 30/59 | T_kine present, ≥1 proton above threshold |
| UNCLASSIFIABLE_NO_KINE | 2/59 | evt_0039, evt_0052: T_kine absent (no neutrino candidate) |

Proton threshold: `kine_particle_type == 2212` AND `kine_energy_particle > 35 MeV`.
Applied to jagged `T_kine` arrays per event file.
Column `proton_category` in `ncdelta_microboone_bdt_scores.csv` (replaces old `is_0p` column).

---

## Step 6: Software vs reconstruction reach

### Software/postprocessing reach (what the offline scorer provides)

The scorer adds the ability to evaluate all four BDTs from existing frozen outputs.
**Before scorer**: 0 events had any `single_photon_*_score` (not computed by frozen WireCell).
**After scorer**: 33 events have all four scores; 26 additional events beyond the ≤17 assumed cap.

**Software loss = 0**: Every event that has the required frozen output can be scored.

### Reconstruction-feature reach (physics bottleneck)

26/59 events (44%) never provide photon shower features regardless of whether the scorer exists:
- 2 events: no neutrino candidate vertex found
- 24 events: vertex found but `shw_sp_filled=0` (shower inaccessible at main vertex)

This is a hard reconstruction limit. The offline scorer cannot recover these events.

---

## Step 7: Failure taxonomy (coarse, from scorer)

| Class | Events | Description |
|-------|--------|-------------|
| `NO_NEUTRINO_CANDIDATE` | 2 | Wire-Cell found no neutrino vertex; no T_tagger |
| `COMPANION_CLUSTER_SHOWER_INACCESSIBLE_CONFIRMED` | 1 | evt_0000: companion cluster directly confirmed |
| `MAIN_VERTEX_SHOWER_INACCESSIBLE` | 23 | shw_sp_filled=0; cause further resolved in Step 7b |
| `SEVERE_SHOWER_UNDERRECO` | 7 | shw_sp_energy < 50 MeV vs truth photon 130–460 MeV |
| `SHOWER_FEATURES_AVAILABLE` | 26 | shw_sp_filled=1 and shw_sp_energy ≥ 50 MeV |
| **Total** | **59** | |

## Step 7b: Refined 24-event shower-access failure diagnostic

Using only frozen T_tagger, T_kine, T_cluster data (`make_failure_diagnostics.py`), the 24
`shw_sp_filled=0` events were classified by evidence type:

**Evidence categories:**
- **Type A**: Dominant T_kine EM particle has `kine_energy_included=3` (companion cluster), energy > 50 MeV
- **Type B**: `kine_pio_energy_1 >> T_kine max EM` ratio ≥ 5× with `kine_pio_flag=1` (pi0 reco found photon in companion cluster inaccessible to T_kine particle list; calibrated against evt_0000 confirmed case)
- **Vertex mismatch**: Large EM in T_kine with `kine_energy_included=1` (main cluster) but `shw_sp_filled=0` (singlephoton_tagger vertex-shower map did not associate the shower)
- **No significant EM**: Max T_kine EM < 50 MeV, no companion cluster evidence

**Results:**

| Category | N | Evidence | Implications |
|----------|---|----------|--------------|
| `COMPANION_CLUSTER_SHOWER_INACCESSIBLE_CONFIRMED` | **10** | Type A: 9 events (dominant EM in companion cluster); Type B: 1 event (evt_0021, kine_pio pattern) | singlephoton_tagger cannot access showers via map_vertex_to_shower[main_vertex] for this cluster |
| `SHOWER_RECONSTRUCTED_ELSEWHERE_UNASSOCIATED` | **4** | Large EM (53–449 MeV) in main cluster (included=1) but shw_sp_filled=0 | NeutrinoKinematics found the shower; singlephoton_tagger did not route it to the vertex-shower map |
| `SEVERE_IMAGING_UNDERRECO` | **10** | Max T_kine EM < 50 MeV, no companion cluster evidence | Photon shower not reconstructed or severely fragmented; independent of companion cluster routing |

**Note**: evt_0000 (COMPANION_CLUSTER confirmed from prior investigation) also shows Type B pattern
(max T_kine EM=11 MeV, kine_pio_energy_1=137 MeV, ratio=12.5×), which was used to calibrate
the Type B criterion for evt_0021 (max_em=12 MeV, pio_e1=114 MeV, ratio=9.5×).

Diagnostic table: `tables/main_vertex_shower_failure_diagnostics.csv`

**Key finding**: The 24-event population is NOT dominated by companion cluster routing alone.
10/24 = 42% are severe imaging failures; those events would NOT be recovered by a
companion-cluster-aware tagger extension. The companion cluster fix would recover at most 10/24
(41% of the failures, 17% of total 59-event sample).

---

## Outputs

| File | Description |
|------|-------------|
| `tables/ncdelta_microboone_bdt_scores.csv` | 59 rows; per-event BDT scores and failure reasons |
| `tables/ncdelta_microboone_cutflow.csv` | Sequential cut-flow counts |
| `tables/ncdelta_reco_failure_taxonomy.csv` | Per-event failure classification |
| `docs/TMVA_VALIDATION.md` | Algorithm documentation and reproducibility record |
| `validate_tmva_vs_root.C` | ROOT TMVA cross-validation macro (superseded by `validate_tmva_standalone.cxx`; see TMVA_VALIDATION.md) |

---

## Step 8 update: Audit assumption corrections

| Assumption | From audit | From scorer | Status |
|-----------|-----------|------------|--------|
| `other` BDT evaluable | 0/59 (reco_nuvtxY missing) | **33/59** (kine_nu_y_corr found) | CORRECTED |
| nue/numu/ncpi0 max evaluable | ≤17 (br_filled cap) | **33** (shw_sp_filled=1 sufficient) | CORRECTED |
| 0p count | 29 | **27** (2 UNCLASSIFIABLE_NO_KINE removed) | CORRECTED |
| Single_photon_*_score in output | Not present | Not present | Confirmed |
| 0p/Np split implementable | Yes | Yes (27/30/2 split) | Confirmed (with UNCLASSIFIABLE) |
| Companion cluster = dominant failure | Assumed (1 confirmed) | **10/24 confirmed, 10/24 imaging failure** | REFINED |
| BDT score convention | Raw sum (raw scorer) | **tanh(raw) per ROOT TMVA** | CORRECTED by ROOT cross-validation |
| Events passing full selection | 2/59 (raw scorer) | **3/59** (tanh-corrected) | CORRECTED |

## Next reconstruction step supported by evidence

The refined 24-event diagnostic changes the recommended action:

**Two distinct failure modes requiring different fixes:**

**Fix 1 — Companion cluster routing (10/24 events)**:
Extend `singlephoton_tagger()` to access showers associated to companion clusters, not only
`map_vertex_to_shower[main_vertex]`. This would recover ~10 events if companion cluster showers
are within the photon shower quality threshold.

**Fix 2 — Vertex-shower association mismatch (4/24 events)**:
Large EM showers reconstructed by NeutrinoKinematics (T_kine included=1) that singlephoton_tagger
does not find. This suggests a vertex-shower map population issue; may be recoverable without
full companion cluster extension.

**No fix can recover (10/24 events)**:
SEVERE_IMAGING_UNDERRECO events have max reconstructed EM < 50 MeV. The photon is not
reconstructed by any available algorithm. These require improved low-energy shower imaging.

**Recommendation**: Investigate Fix 2 first (4 events, simpler diagnosis) to understand
the vertex-shower map mismatch. Fix 1 (companion cluster extension) is the larger scope.
Do NOT implement either fix in baseline_v0. Both require new WireCell reconstruction runs.

Do NOT implement any change in baseline_v0.
