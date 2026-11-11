"""Analysis-definition decision support (Phase 13): fiducial-volume specifications, proton-policy and candidate-policy bookkeeping.  Pure functions, no I/O.

DECISION SUPPORT ONLY: nothing here changes ``configs/baseline_selection.yaml``, a frozen cut or a threshold.  A fiducial volume is applied to a RECONSTRUCTED (selected-candidate) vertex for numerator and
background and to the TRUE vertex for the signal denominator; the truth FV is never imposed on the BNB-CV background, which has its own reco-FV application.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

# source-supported FV conventions (docs/analysis/SBND_FIDUCIAL_VOLUME_AUDIT.md numbering in `audit_id`, SPINE truth FV from SPINE_SIGNAL_DEFINITION_SOURCE_AUDIT.md)
FV_SPECS = {
    "none": dict(audit_id="-", label="no FV (frozen baseline, reference)", x=None, y=None, z=None),
    "av200": dict(audit_id="1", label="active volume |x|,|y|<200, 0<z<500 (provisional truth box; sbnana `avnd`)", x=(-200.0, 200.0), y=(-200.0, 200.0), z=(0.0, 500.0), inclusive=False),
    "cafpyana190": dict(audit_id="5", label="cafpyana SBND `InFV`: |x|,|y|<190, 10<z<450", x=(-190.0, 190.0), y=(-190.0, 190.0), z=(10.0, 450.0), inclusive=False),
    "numu2021": dict(audit_id="4", label="numuCC 2021 `kInFV`: |x|<189.15, |y|<190, 10<z<450", x=(-189.15, 189.15), y=(-190.0, 190.0), z=(10.0, 450.0), inclusive=False),
    "spine180": dict(audit_id="SPINE", label="SPINE truth FV (Seokju): |x|,|y|<=180, 10<=z<=450", x=(-180.0, 180.0), y=(-180.0, 180.0), z=(10.0, 450.0), inclusive=True),
    "legacy_nue175": dict(audit_id="2", label="legacy nue `fvndAbs`: 1.5<|x|<175, |y|<175, 30<z<450 (cathode excluded)", xabs=(1.5, 175.0), y=(-175.0, 175.0), z=(30.0, 450.0), inclusive=False),
    "cohpi_carve": dict(audit_id="9", label="cohpi: 10<|x|<190, 10<z<450, |y|<190 for z<250 and -190<y<100 for z>250 (high-y carve-out)", xabs=(10.0, 190.0), y=(-190.0, 190.0), z=(10.0, 450.0), highy=(250.0, -190.0, 100.0), inclusive=False),
}


def fv_mask(x, y, z, spec) -> np.ndarray:
    """Boolean mask of vertices inside a FV spec (``None`` / ``FV_SPECS['none']`` = everything).  NaN coordinates are outside.  Boundary semantics: strict ``<`` unless ``inclusive``."""
    x = np.asarray(x, float); y = np.asarray(y, float); z = np.asarray(z, float)
    if spec is None or spec.get("x", 1) is None and spec.get("xabs") is None:
        return np.ones(x.shape, bool)
    lt = (lambda a, b: a <= b) if spec.get("inclusive") else (lambda a, b: a < b)
    ok = np.isfinite(x) & np.isfinite(y) & np.isfinite(z)
    if spec.get("xabs") is not None:
        lo, hi = spec["xabs"]; ok &= lt(lo, np.abs(x)) & lt(np.abs(x), hi)
    else:
        lo, hi = spec["x"]; ok &= lt(lo, x) & lt(x, hi)
    lo, hi = spec["y"]; ok &= lt(lo, y) & lt(y, hi)
    lo, hi = spec["z"]; ok &= lt(lo, z) & lt(z, hi)
    if spec.get("highy") is not None:                 # for z > z0 the y window becomes (y_lo, y_hi)
        z0, ylo, yhi = spec["highy"]; ok &= ~(z > z0) | (lt(ylo, y) & lt(y, yhi))
    return ok


def distance_to_faces(x, y, z, box=((-200.0, 200.0), (-200.0, 200.0), (0.0, 500.0))) -> np.ndarray:
    """Distance (cm) of a point to the nearest face of the active-volume box (negative outside); used for the edge diagnostics, not to define a cut."""
    (x0, x1), (y0, y1), (z0, z1) = box
    return np.minimum.reduce([np.asarray(x, float) - x0, x1 - np.asarray(x, float), np.asarray(y, float) - y0, y1 - np.asarray(y, float), np.asarray(z, float) - z0, z1 - np.asarray(z, float)])


# proton policies P1-P4 (reco threshold, included == 3 treatment); truth threshold = reco threshold (never mixed)
PROTON_PACKAGES = {
    "P1": dict(variant="baseline_35", reco_threshold_mev=35.0, exclude_included3=False, truth_threshold_mev=35.0),
    "P2": dict(variant="35_excl_included3", reco_threshold_mev=35.0, exclude_included3=True, truth_threshold_mev=35.0),
    "P3": dict(variant="50", reco_threshold_mev=50.0, exclude_included3=False, truth_threshold_mev=50.0),
    "P4": dict(variant="50_excl_included3", reco_threshold_mev=50.0, exclude_included3=True, truth_threshold_mev=50.0),
}


def truth_category(n_primary_protons) -> np.ndarray:
    """0 / 1 / 2 (>=2) from the post-FSI primary-proton count above the policy's truth threshold."""
    return np.minimum(np.asarray(n_primary_protons, int), 2)


def truth_column_for(policy: str) -> str:
    """Event-table column of the truth proton count for the policy: 35 MeV -> ``n_p35_prim``, 50 MeV -> ``n_p50`` (the two thresholds are never mixed)."""
    return "n_p35_prim" if PROTON_PACKAGES[policy]["truth_threshold_mev"] == 35.0 else "n_p50"


def overlap_table(a_flag, f_flag) -> dict:
    """Event overlap of the two candidate policies from boolean per-event flags (``a`` = any, ``f`` = first); ``first_only`` must be 0 for the frozen chain (candidate 0 passing implies the event passes under any)."""
    a = np.asarray(a_flag, bool); f = np.asarray(f_flag, bool)
    return dict(both=int((a & f).sum()), any_only=int((a & ~f).sum()), first_only=int((~a & f).sum()), neither=int((~a & ~f).sum()), n_any=int(a.sum()), n_first=int(f.sum()), n_events=len(a))


FIRST_FAIL_ORDER = ["cum_candidate_in_valid_event", "cum_n_20mev_showers_gt0", "bdt_evaluable", "cum_single_photon_numu_score_gt_0p4", "cum_single_photon_other_score_gt_0p2", "cum_single_photon_ncpi0_score_gt_m0p05",
                    "cum_single_photon_nue_score_gt_m1", "cum_n_20br1_showers_eq1"]
STAGE_NAME = {"cum_candidate_in_valid_event": "candidate/valid event", "cum_n_20mev_showers_gt0": "no > 20 MeV shower", "bdt_evaluable": "BDT not evaluable", "cum_single_photon_numu_score_gt_0p4": "numu",
              "cum_single_photon_other_score_gt_0p2": "other", "cum_single_photon_ncpi0_score_gt_m0p05": "ncpi0", "cum_single_photon_nue_score_gt_m1": "nue", "cum_n_20br1_showers_eq1": "n_20br1"}


def first_failed_stage(row) -> str:
    """Name of the first frozen stage that a candidate (row of the baseline candidate table) fails; ``passes all`` if none.  The cumulative flags are NOT re-derived: ``bdt_evaluable`` precedes numu."""
    for c in FIRST_FAIL_ORDER:
        if not bool(row[c]):
            return STAGE_NAME[c]
    return "passes all frozen cuts"


def envelope_row(label: str, metrics: dict, reference: dict) -> dict:
    """One row of the policy envelope: a package's headline quantities and their difference to the reference package.  Differences are reported separately and NEVER combined (no quadrature)."""
    out = dict(package=label)
    for k, v in metrics.items():
        out[k] = v
        if isinstance(v, (int, float, np.integer, np.floating)) and k in reference and reference[k] is not None:
            out["d_" + k] = v - reference[k]
    return out


def rates_per_1e20(n, pot) -> float:
    """Events per 1e20 POT for ``n`` selected events in a sample of exposure ``pot``."""
    return float(n) * 1e20 / float(pot)


def reference_ratio(s, b) -> float:
    """signal / beam-neutrino-background REFERENCE ratio (NOT an analysis S/B: no cosmic-only component, no systematic)."""
    return float(s) / float(b) if b else float("nan")
