"""Pure helpers of the photon-shower / vertex reconstruction audit (no I/O; every function is unit-tested). Nothing here selects or changes a baseline decision."""
from __future__ import annotations

import numpy as np

PROXIMITY_TOL_CM = 5.0        # analysis tolerance (the signal-candidate matching tolerance of the baseline); sensitivity at 3 and 10 cm is reported by the audit script
NEAR_CONV_MIN_CM = 5.0        # below this conversion distance the interaction vertex and the conversion point are not separable at the tolerance


def decompose_vertex(v_reco, v_true, c_true, photon_dir) -> dict:
    """Decompose (V_reco - V_true) relative to the true photon direction and relate V_reco to the true interaction vertex and the true conversion point.

    ``photon_dir`` need not be normalised. Returns: ``parallel`` (signed projection on the photon direction, cm), ``perp`` (magnitude of the perpendicular part), ``d_vertex`` = |V_reco - V_true|,
    ``d_conv`` = |V_reco - C_true|, ``d_conv_true`` = |C_true - V_true|, ``frac_axis`` = projection of (V_reco - V_true) on the true interaction->conversion axis divided by the true conversion distance
    (0 at the interaction vertex, 1 at the conversion point; NaN if the conversion distance is 0), and ``perp_axis`` the distance of V_reco from that axis."""
    v_reco, v_true, c_true, u = (np.asarray(a, float) for a in (v_reco, v_true, c_true, photon_dir))
    u = u / np.linalg.norm(u)
    d = v_reco - v_true; par = float(d @ u); perp = float(np.linalg.norm(d - par * u))
    axis = c_true - v_true; L = float(np.linalg.norm(axis))
    if L > 0:
        a = axis / L; s = float(d @ a) / L; pax = float(np.linalg.norm(d - (d @ a) * a))
    else:
        s, pax = float("nan"), float(np.linalg.norm(d))
    return dict(parallel=par, perp=perp, d_vertex=float(np.linalg.norm(d)), d_conv=float(np.linalg.norm(v_reco - c_true)), d_conv_true=L, frac_axis=s, perp_axis=pax)


def classify_proximity(d_vertex: float, d_conv: float, d_conv_true: float, tol: float = PROXIMITY_TOL_CM) -> str:
    """'not_separable' (true conversion distance below ``NEAR_CONV_MIN_CM``), 'interaction_vertex' (V_reco within ``tol`` of V_true and not closer to C_true),
    'conversion_point' (within ``tol`` of C_true and not closer to V_true), 'between' (neither within tol but the point lies between the two), 'neither' otherwise."""
    if not np.isfinite(d_vertex) or not np.isfinite(d_conv):
        return "undefined"
    if d_conv_true < NEAR_CONV_MIN_CM:
        return "not_separable"
    if d_vertex <= tol and d_vertex <= d_conv:
        return "interaction_vertex"
    if d_conv <= tol and d_conv < d_vertex:
        return "conversion_point"
    if d_vertex + d_conv <= 1.2 * d_conv_true:
        return "between"
    return "neither"


def distance_to_boundary(x, y, z, box=((-200.0, 200.0), (-200.0, 200.0), (0.0, 500.0))) -> np.ndarray:
    """Distance (cm) from a point to the nearest face of the provisional TPC box (positive inside)."""
    p = np.asarray([x, y, z], float)
    return np.min([np.minimum(p[i] - box[i][0], box[i][1] - p[i]) for i in range(3)], axis=0)


def counted_by_sp(energy_mev, in_main_vertex_set: bool, pdg: int) -> bool:
    """Whether a shower is counted by ``shw_sp_n_20mev_showers`` under the source rule: it must be in the main vertex's shower set, its start segment typed electron (PDG 11), and its energy strictly above 20 MeV."""
    return bool(in_main_vertex_set and int(pdg) == 11 and float(energy_mev) > 20.0)


# ---------------------------------------------------------------------------------------------------------------------------- exclusive shower-stage failure taxonomy
FAIL_CLASSES = ["photon_no_reco_charge", "photon_charge_outside_candidates", "photon_fragmented", "photon_in_other_candidate", "photon_particle_row_missing", "photon_as_track",
                "photon_shower_typed_non_electron", "photon_shower_below_20MeV", "photon_shower_not_in_main_vertex_set"]
OUTSIDE_FRAC_MIN = 0.5        # at least this fraction of the photon's reconstructed charge must lie inside a candidate (else 'outside candidates')
DOMINANT_FRAC_MIN = 0.5       # the dominant (candidate, particle) must hold at least this fraction of the in-candidate photon charge (else 'fragmented')
SP_ENERGY_MEV = 20.0


def classify_failure(q_total: float, q_in_cands: float, dominant_fraction: float, dominant_in_signal_candidate, has_kine_row: bool, is_shower: bool, pdg: int, e_reco_mev: float,
                     outside_frac_min: float = OUTSIDE_FRAC_MIN, dominant_frac_min: float = DOMINANT_FRAC_MIN) -> str:
    """Exclusive, exhaustive outcome of an event that has >= 1 candidate but NO electron-typed > 20 MeV shower at any candidate's main vertex (``shw_sp_n_20mev_showers == 0`` for all candidates).

    Hierarchy (first match wins): (1) the signal photon has no reconstructed charge in the event; (2) most of its reconstructed charge is in clusters that belong to no candidate; (3) inside the candidates
    its charge is fragmented over several particles (no dominant particle holds ``dominant_frac_min``); (4) the dominant particle is in a candidate other than the signal-matched one (None = no signal-matched
    candidate: this branch is skipped); (5) the dominant particle has no T_kine row; (6) it is a track (not a shower row); (7) a shower row typed other than electron; (8) an electron shower with
    E_reco <= 20 MeV; (9) an electron shower with E_reco > 20 MeV: by the source rule (only showers whose start vertex is the main vertex are examined) it is NOT in the main vertex's shower set."""
    if not q_total > 0:
        return "photon_no_reco_charge"
    if q_in_cands / q_total < outside_frac_min:
        return "photon_charge_outside_candidates"
    if dominant_fraction < dominant_frac_min:
        return "photon_fragmented"
    if dominant_in_signal_candidate is False:
        return "photon_in_other_candidate"
    if not has_kine_row:
        return "photon_particle_row_missing"
    if not is_shower:
        return "photon_as_track"
    if int(pdg) != 11:
        return "photon_shower_typed_non_electron"
    if not float(e_reco_mev) > SP_ENERGY_MEV:
        return "photon_shower_below_20MeV"
    return "photon_shower_not_in_main_vertex_set"


def pf_attachment_state(has_node: bool, depth: int, parent_is_pseudo: bool, grandparent_id: int) -> str:
    """State of a reco shower in the stored particle-flow tree (validated against the tagger's own shw_sp_shw_vtx_dis in the audit): 'none' (no PF node), 'root' (depth 0),
    'photon_node_at_vertex' (child of a root-level pseudo photon node), 'deeper' (below another particle)."""
    if not has_node:
        return "none"
    if depth == 0:
        return "root"
    if parent_is_pseudo and grandparent_id == -1:
        return "photon_node_at_vertex"
    return "deeper"
