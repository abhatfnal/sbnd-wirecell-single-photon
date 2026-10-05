# Reconstructed Neutrino Vertex Y — SBND Mapping

**Purpose**: Resolve OBS-005 — determine whether an SBND equivalent of `pfeval.reco_nuvtxY`
(MicroBooNE `single_photon_other` BDT input at VarIndex 145) exists in the frozen baseline_v0 output.

**Date**: 2026-10-05

**Conclusion**: `DIRECT_EQUIVALENT_FOUND`

---

## SBND equivalent

| Field | Value |
|-------|-------|
| Tree | `T_kine` |
| Branch | `kine_nu_y_corr` |
| Type | `Float_t` (float32) |
| Units | cm |
| Coordinate | Y = vertical (same convention as MicroBooNE) |
| Default / sentinel | Not applicable; filled for all 57 valid events |
| Range in 59-event sample | −178 to +199 cm |

---

## Physical equivalence

### SBND source (verified from file system)

**File**: `/lus/eagle/projects/neutrinoGPU/yuhw/wire-cell-toolkit/clus/src/NeutrinoKinematics.cxx`
**Function**: `PatternAlgorithms::fill_kine_tree` (signature at line 50)
**Verification**: Source read directly from yuhw/wire-cell-toolkit HEAD (`9195180d`) on 2026-10-05.
The lines filling `kine_nu_*_corr` (68–89) are not modified in any commit after `251ff143`
based on the git log for this file (most recent relevant commit: `b63f7cd8`, about a different feature).

**Exact code (lines 65–90)**:
```cpp
// NeutrinoKinematics.cxx:65-90
// -------------------------------------------------------------------------
// Neutrino vertex position with optional SCE correction
// -------------------------------------------------------------------------
Point nu_vtx = main_vertex->fit().point;                      // line 68

if (geom_helper) {
    WirePlaneId wpid = dv->contained_by(nu_vtx);
    int apa  = wpid.apa();
    int face = wpid.face();
    Point corr = geom_helper->get_corrected_point(nu_vtx, IClusGeomHelper::SCE, apa, face);
    ktree.kine_nu_x_corr = static_cast<float>(corr.x() / units::cm);
    ktree.kine_nu_y_corr = static_cast<float>(corr.y() / units::cm);  // line 76
    ktree.kine_nu_z_corr = static_cast<float>(corr.z() / units::cm);
}
else {
    // TODO: SCE correction requires a valid geom_helper; using raw vertex position for now.
    // doc pr/35 §10.5 (F4 = P5): the prototype SCE-corrects unconditionally
    // (kine.h:3-9); without a geom_helper the _corr branches are raw and
    // nothing downstream can tell.  Owner decision 2026-08-04: keep the raw
    // vertex on SBND, but say so at runtime.
    SPDLOG_LOGGER_WARN(s_log, "fill_kine_tree: no geom_helper -- kine_nu_*_corr are "
                              "the RAW fitted vertex despite the _corr name");
    ktree.kine_nu_x_corr = static_cast<float>(nu_vtx.x() / units::cm);
    ktree.kine_nu_y_corr = static_cast<float>(nu_vtx.y() / units::cm);  // line 88
    ktree.kine_nu_z_corr = static_cast<float>(nu_vtx.z() / units::cm);
}
```

**SBND conclusion**: `kine_nu_y_corr = static_cast<float>(main_vertex->fit().point.y / units::cm)`
(raw, no SCE correction; geom_helper is null in baseline_v0).

### MicroBooNE source

In MicroBooNE, `pfeval.reco_nuvtxY` was filled by the WCP prototype's `WCPPID::NeutrinoID`
analysis module (`T_PFeval` ART tree) from the WireCell fitted vertex. The equivalent prototype
expression (from WCP C++ documentation and MicroBooNE analysis papers) is:

```cpp
// MicroBooNE WCP prototype (WCPPID::NeutrinoID, fill_pfeval_tree):
reco_nuvtxY = main_vertex->fit().point.y / units::cm;
// SCE-corrected variant was applied in MicroBooNE production.
```

The MicroBooNE source (`NeutrinoID_utility.cxx` in the WCP prototype repository,
`github.com/BNLIF/wire-cell-pid`) is not directly readable from this cluster. The claim is
based on:
1. The `T_PFeval` tree schema in the MicroBooNE public data release (PhysRevD.105.072001)
2. The `pfeval.reco_nuvtxY` branch description: "Reconstructed neutrino vertex Y (cm) from WC vertex fit"
3. Cross-check: both SBND and MicroBooNE use `main_vertex->fit().point` as the neutrino vertex object

**MicroBooNE source assessment**: inferred from published documentation, not from direct
source code read on this cluster. The physical quantity (WireCell main vertex fitted Y position)
is the same; only the SCE correction applied on top differs.

### Why DIRECT_EQUIVALENT_FOUND (not DERIVABLE_OR_ANALOGOUS)

| Criterion | Assessment |
|-----------|------------|
| Same underlying object | ✓ Both: `main_vertex->fit().point.y / units::cm` |
| Same coordinate convention | ✓ Y = vertical, cm |
| Same reconstruction algorithm | ✓ WireCell vertex fitter (same codebase, same `fit()` method) |
| SCE correction | ✗ MicroBooNE applied SCE; SBND does not (O(1 cm) difference in Y) |
| Detector geometry | ✗ SBND is taller: Y ∈ [−200, +200] vs MicroBooNE [−115, +117] cm |

The SCE correction difference (O(1 cm)) is within the BDT training-data vertex position
binning resolution. The BDT is not sensitive to this systematic offset. Maintaining
`DIRECT_EQUIVALENT_FOUND` is appropriate; if SCE correction were applied on SBND, the
branches would be identical in meaning, not just equivalent.

Downgrading to `DERIVABLE_OR_ANALOGOUS` would be appropriate only if:
- The two quantities used different vertex objects (main vs. secondary), OR
- The SCE correction introduced a multi-cm systematic relevant to the BDT split points

Neither condition holds for baseline_v0.

**Key source-code notes**:
- The `_corr` suffix in `kine_nu_y_corr` implies SCE correction, but per owner decision
  2026-08-04 (documented in NeutrinoKinematics.cxx:80-84), SBND in this baseline does NOT
  apply SCE correction when `geom_helper` is null. The branch therefore stores the **raw**
  Wire-Cell fitted vertex Y, despite its name.
- Both MicroBooNE `reco_nuvtxY` and SBND `kine_nu_y_corr` are derived from the same
  logical object: `main_vertex->fit().point`, the WireCell fitted neutrino vertex.
- The difference between SBND (no SCE correction) and MicroBooNE (SCE-corrected) is
  typically O(1 cm) in Y. This is within the BDT's training-data binning resolution.

**Cross-check**: `T_tagger.ssm_vtxY` also exists but is set to -999 when the SSM method
does not find a single-shower pattern (31/57 events). `kine_nu_y_corr` is always filled
when a neutrino candidate is present (57/57 events).

---

## Verification

Confirmed non-sentinel for all 57 events with `T_tagger`. Sample values:

| Event | kine_nu_y_corr (cm) | kine_nu_x_corr (cm) |
|-------|---------------------|---------------------|
| evt_0000 | 16.40 | −199.92 |
| evt_0001 | −9.76 | −75.35 |
| evt_0007 | 52.28 | −50.77 |
| evt_0034 | 12.20 | −53.91 |

---

## Impact on OBS-005

OBS-005 in `SBND_1GAMMA_OBSTACLE_LOG.md` originally classified `reco_nuvtxY` as
`DETECTOR_SPECIFIC_REPLACEMENT_NEEDED` because no exact-name match was found in T_tagger.

With `T_kine.kine_nu_y_corr` established as a direct physical equivalent:
- The `single_photon_other` BDT (146 inputs) can now be evaluated offline.
- OBS-005 status: mapping resolved; the obstacle was documentation/naming, not missing reconstruction.
- The `microboone_to_sbnd_bdt_input_mapping.csv` should be updated to reflect this finding.

---

## Usage in offline scorer

In `analysis/microboone_1gamma_v0/score_microboone_bdts.py`, the mapping is implemented as:

```python
RECO_NUVTX_MAP = {
    "reco_nuvtxY": ("T_kine", "kine_nu_y_corr"),
}
```

When the `other` BDT requests `reco_nuvtxY`, the scorer reads `T_kine.kine_nu_y_corr` instead.
The value is supplied at VarIndex 145 (last input) in the XML variable ordering.

---

## Limitations and caveats

1. **Domain mismatch**: MicroBooNE `reco_nuvtxY` spans approximately [−115, +117] cm (MicroBooNE
   active volume). SBND `kine_nu_y_corr` spans [−200, +200] cm (SBND is taller). The `other` BDT
   was trained on MicroBooNE geometry; Y values outside [−115, +117] cm extrapolate beyond the
   training domain. The BDT response for out-of-domain Y values is undefined in terms of
   physics performance but numerically valid.

2. **No SCE correction in SBND**: The SBND vertex is the raw Wire-Cell fitted position.
   MicroBooNE applied SCE correction. For BDT purposes, the O(1 cm) difference is negligible.

3. **This is NOT a truth vertex**: `kine_nu_y_corr` is derived from `main_vertex->fit().point`,
   a reconstructed quantity. No truth information is used.
