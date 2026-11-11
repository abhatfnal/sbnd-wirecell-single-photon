"""Pi0-pair member recovery, member truth taxonomy and fragmentation bookkeeping (Phase 14).  Pure functions, no I/O.

DESCRIPTIVE ONLY: nothing here changes a frozen cut, threshold, BDT or candidate policy.

Source facts the helpers rely on (read in ``HaiwangYu/wire-cell-toolkit`` ``4b6853d4``, see ``docs/analysis/PI0_PAIR_CONSTRUCTION_SOURCE_AUDIT.md``):
* ``kine_pio_*`` is NOT the mass-window pair: it is the candidate shower pair with the largest ``E1 + E2`` (kine_charge) among all pairs the pair finder forms (``flag = 1``), possibly overridden by a
  without-vertex pair of larger or equal energy sum (``flag = 2``).  No pair-member id is stored.
* ``shw_sp_pio_1_*`` is the mass-window pair (``map_shower_pio_id``) that contains the tagger's selected shower; no member id is stored either.
* The stored energies are ``Shower::get_kine_charge()``; a ``T_kine`` row stores ``get_kine_best()``; the two are equal exactly when the row's ``kine_energy_info == 2``.
"""
from __future__ import annotations
import numpy as np

ENERGY_RTOL = 1e-5            # float32 round trip of the same C++ double
GEOM_TOL_CM = 5.0             # tolerance of the distance consistency check (the baseline's signal-candidate tolerance)
SHOWER_ROW_INFO_CHARGE = 2    # kine_energy_info == 2: kine_best equals kine_charge (decided by the producer to 0.1 %)

RECOVERY_CLASSES = ["unique_exact", "unique_by_elimination", "unique_by_geometry", "ambiguous", "unresolved"]


def energy_matches(row_energy, stored, rtol: float = ENERGY_RTOL) -> np.ndarray:
    """Boolean mask of rows whose stored kine_best energy equals the stored pair energy (float tolerance)."""
    row_energy = np.asarray(row_energy, float)
    return np.abs(row_energy - float(stored)) < rtol * max(1.0, abs(float(stored)))


def consistent_pairs(rows, energy, info, pool, e1, e2, rtol: float = ENERGY_RTOL, require_detached: bool = True):
    """Ordered ``(row_for_energy_1, row_for_energy_2)`` configurations of shower rows consistent with the stored pair energies.

    A member whose stored energy equals a row's ``kine_best`` energy is identified by it ("exact").  A member for which no row matches is a row whose ``kine_charge`` differs from the stored ``kine_best``,
    i.e. a row with ``kine_energy_info != 2`` (the "wildcard" set).  A pair needs at least one detached member (the source never records an attached/attached pair): with ``require_detached`` at least
    one member must be a pool-2 row.  Returns ``(configs, n_exact_members)``; ``configs`` is a sorted list.
    """
    rows = np.asarray(rows); energy = np.asarray(energy, float); info = np.asarray(info); pool = np.asarray(pool)
    ex = [set(rows[energy_matches(energy, e, rtol)].tolist()) for e in (e1, e2)]
    wild = set(rows[info != SHOWER_ROW_INFO_CHARGE].tolist())
    pool_of = dict(zip(rows.tolist(), pool.tolist()))
    cfg = set()
    for a in (ex[0] or wild):
        for b in (ex[1] or wild):
            if a == b:
                continue
            if require_detached and pool_of[a] != 2 and pool_of[b] != 2:
                continue
            cfg.add((a, b))
    return sorted(cfg), int(bool(ex[0])) + int(bool(ex[1]))


def recovery_class(n_exact_members: int, n_configs: int) -> str:
    """``unique_exact`` (both energies identify one row each), ``unique_by_elimination`` (one member by energy, the other the only admissible leftover row), ``ambiguous`` (several admissible
    configurations), ``unresolved`` (no configuration: a member is not a stored shower row)."""
    if n_configs == 0:
        return "unresolved"
    if n_configs > 1:
        return "ambiguous"
    return "unique_exact" if n_exact_members == 2 else "unique_by_elimination"


def unordered_pair_keys(configs) -> set:
    """Distinct unordered pairs of a configuration list (order is only the energy_1 / energy_2 label)."""
    return {tuple(sorted(c)) for c in configs}


def geometry_status(s_a, s_b, d1, d2, strong_tol: float = 0.01, weak_tol: float = 0.05) -> str:
    """Consistency of a configuration with the stored distances ``dis_1`` / ``dis_2`` (vertex to shower start point), from the particle-flow start points ``s_a`` / ``s_b`` of the two members.

    A member with a stored distance of 0 sits AT the pair vertex, so the other distance must equal the separation of the two start points (``strong``, tolerance in cm; the stored distances reproduce this to
    1e-5 cm for the exactly identified pairs).  Otherwise only the triangle inequality is testable (``weak``).  ``untestable`` if either start point is unavailable (not every row has a particle-flow node)."""
    if s_a is None or s_b is None:
        return "untestable"
    L = float(np.linalg.norm(np.asarray(s_a, float) - np.asarray(s_b, float)))
    if d1 < 1e-3:
        return "strong_pass" if abs(L - d2) < strong_tol else "strong_fail"
    if d2 < 1e-3:
        return "strong_pass" if abs(L - d1) < strong_tol else "strong_fail"
    return "weak_pass" if (abs(d1 - d2) - weak_tol <= L <= d1 + d2 + weak_tol) else "weak_fail"


def refine_by_geometry(configs, statuses):
    """Configurations kept after removing those the stored distances contradict (``*_fail``).  If every configuration fails, all are kept and the event is flagged ``geometry_inconsistent``.
    Returns ``(kept_configs, flag)`` with flag in ``consistent`` / ``geometry_inconsistent`` / ``untested``."""
    if not configs:
        return [], "untested"
    keep = [c for c, s in zip(configs, statuses) if not s.endswith("_fail")]
    if not keep:
        return list(configs), "geometry_inconsistent"
    return keep, ("consistent" if any(s != "untestable" for s in statuses) else "untested")


# ------------------------------------------------------------------------------------------------------------------------------ source ranking semantics (documented in code, unit-tested)
PI0_MASS_MEV = 135.0
PI0_MASS_OFFSET_MEV = 10.0          # NeutrinoPatternBase.h:2309 m_pi0_mass_offset (source default)
WITH_VERTEX_WINDOW_MEV = (-25.0, 35.0)   # accepted if -25 < m - 135 + offset < 35  (i.e. 100 < m < 160 MeV)
TWO_CT2_BONUS_MEV = 6.0             # a pair of two connection-type-2 showers is favoured by 6 MeV in the |delta| comparison
WITHOUT_VERTEX_HALF_WINDOW_MEV = 60.0


def select_kine_pair(pairs):
    """Source selection of the ``kine_pio`` (flag 1) pair: among ``pairs`` given in iteration order as ``(E1, E2, tag)``, the one with the LARGEST ``E1 + E2``; a pair replaces the running maximum only if its
    sum is STRICTLY greater (``if (energy_1 + energy_2 <= max_energy) continue``), so a tie keeps the first.  No mass requirement.  Returns the tag or None."""
    best, mx = None, 0.0
    for e1, e2, tag in pairs:
        if e1 + e2 <= mx:
            continue
        best, mx = tag, e1 + e2
    return best


def select_window_pair(pairs):
    """Source selection of the next accepted mass-window pair (type 1): ``pairs`` are ``(mass_MeV, n_conn_type_2_members, tag)`` in iteration order; ``delta = m - 135 + 10``; only ``-25 < delta < 35`` is eligible;
    the winner minimises ``|delta| - penalty`` with ``penalty = 6 MeV`` when both members have connection type 2; a candidate must be strictly better than the running best (a tie keeps the first)."""
    best, best_key = None, (1e9, 0.0)
    for m, nct2, tag in pairs:
        delta = m - PI0_MASS_MEV + PI0_MASS_OFFSET_MEV
        if delta >= WITH_VERTEX_WINDOW_MEV[1] or delta <= WITH_VERTEX_WINDOW_MEV[0]:
            continue
        pen = TWO_CT2_BONUS_MEV if nct2 == 2 else 0.0
        if abs(delta) - pen < abs(best_key[0]) - best_key[1]:
            best, best_key = tag, (delta, pen)
    return best


def mass_from_energies_angle(e1, e2, angle_deg) -> float:
    """Invariant mass sqrt(4 E1 E2 sin^2(theta/2)) of a two-photon system (MeV, degrees)."""
    return float(np.sqrt(max(4.0 * e1 * e2 * np.sin(np.deg2rad(angle_deg) / 2.0) ** 2, 0.0)))


# ------------------------------------------------------------------------------------------------------------------------------ member truth taxonomy
FINE_CLASSES = ["signal_photon_dominant", "signal_photon_fragment", "signal_other_EM", "signal_proton", "signal_other_hadron", "other_nu_EM", "other_nu_hadron", "dirt_outside_AV_nu", "cosmic",
                "unmatched", "ambiguous_mixed"]
# Task-8 headline groups
HEADLINE = {"signal_photon_dominant": "same signal photon (dominant)", "signal_photon_fragment": "same signal photon fragment", "signal_other_EM": "other EM from signal interaction",
            "signal_proton": "signal proton / hadronic object", "signal_other_hadron": "signal proton / hadronic object", "other_nu_EM": "other-neutrino EM object",
            "other_nu_hadron": "other-neutrino hadronic object", "dirt_outside_AV_nu": "dirt / outside-AV neutrino", "cosmic": "cosmic", "unmatched": "unmatched",
            "ambiguous_mixed": "ambiguous / mixed"}
AMBIGUOUS_RATIO = 0.5          # second stored partner at least this fraction of the top partner's point IoU, with a different truth identity => ambiguous / mixed


def is_em_pdg(pdg) -> bool:
    return int(abs(pdg)) in (11, 22)


def row_truth_class(p1_tid, p1_pdg, p1_nu, p1_iou_n, p2_tid, p2_iou_n, p2_nu, sig_tid, sig_nu, is_dominant_photon_row, nu_outside_av: dict | None = None) -> str:
    """Exclusive truth class of ONE reconstructed particle row from its source-ranked T_match partner (point IoU first, then charge IoU, then object index: ``p1``).

    ``p1_nu`` -9 / NaN = no resolvable partner (unmatched); -1 = non-neutrino (cosmic).  ``sig_tid`` is the trackid of the signal photon (the labeler merges its conversion daughters into the prong);
    a row whose top partner IS that prong is the signal photon (``dominant`` if it is the Phase-9 dominant reconstructed photon object, else a fragment).  ``nu_outside_av`` maps a truth interaction
    index to True when its vertex is outside the active volume (dirt)."""
    if not (np.isfinite(p1_nu) and p1_nu > -5) or not (p1_tid is not None and np.isfinite(p1_tid) and p1_tid >= 0):
        return "unmatched"
    ambiguous = False
    if np.isfinite(p2_iou_n) and np.isfinite(p1_iou_n) and p1_iou_n > 0 and p2_iou_n >= AMBIGUOUS_RATIO * p1_iou_n and np.isfinite(p2_tid) and p2_tid != p1_tid:
        ambiguous = True                               # two comparable truth objects share the row's points
    if ambiguous:
        return "ambiguous_mixed"
    if p1_nu < 0:
        return "cosmic"
    if p1_nu == sig_nu:
        if int(p1_tid) == int(sig_tid) and int(p1_pdg) == 22:
            return "signal_photon_dominant" if is_dominant_photon_row else "signal_photon_fragment"
        if is_em_pdg(p1_pdg):
            return "signal_other_EM"
        if int(p1_pdg) == 2212:
            return "signal_proton"
        return "signal_other_hadron"
    if nu_outside_av and nu_outside_av.get(int(p1_nu), False):
        return "dirt_outside_AV_nu"
    return "other_nu_EM" if is_em_pdg(p1_pdg) else "other_nu_hadron"


def pair_signal_membership(member_classes) -> str:
    """Task-7 class of a pair from the fine classes of its two members: ``contains_dominant``, ``contains_fragment_only`` (a signal-photon fragment but not the dominant object),
    ``contains_both_pieces`` (two signal-photon rows, dominant or not) or ``contains_neither``."""
    dom = sum(c == "signal_photon_dominant" for c in member_classes); frag = sum(c == "signal_photon_fragment" for c in member_classes)
    if dom + frag == 0:
        return "contains_neither"
    if dom + frag == 2:
        return "contains_both_pieces"
    return "contains_dominant" if dom == 1 else "contains_fragment_only"


def decide(values):
    """Value shared by every consistent configuration of an event, else ``'indeterminate'`` (the ambiguity is NOT resolved by choosing one configuration)."""
    s = set(values)
    return next(iter(s)) if len(s) == 1 else "indeterminate"


def other_member_class(member_classes) -> str:
    """Class of the member that is not the (dominant/fragment) signal photon; for a pair with two signal-photon pieces the 'other' is another signal-photon fragment."""
    sig = [c for c in member_classes if c in ("signal_photon_dominant", "signal_photon_fragment")]
    oth = [c for c in member_classes if c not in ("signal_photon_dominant", "signal_photon_fragment")]
    if len(sig) == 2:
        return "signal_photon_fragment"
    return oth[0] if oth and sig else "n/a"


# ------------------------------------------------------------------------------------------------------------------------------ fragmentation
FRAGMENT_MIN_FRACTION = 0.10   # a reconstructed particle holding >= 10 % of the signal photon's in-candidate charge is a "significant piece" (descriptive; Phase 9's fragmented flag is unchanged)


def significant_pieces(charges, min_fraction: float = FRAGMENT_MIN_FRACTION):
    """Indices of the pieces holding at least ``min_fraction`` of the total piece charge (descending charge), plus the leading-piece fraction."""
    q = np.asarray(charges, float)
    if q.size == 0 or q.sum() <= 0:
        return np.array([], int), float("nan")
    f = q / q.sum(); idx = np.where(f >= min_fraction)[0]
    return idx[np.argsort(-f[idx])], float(f.max())


def type_label(pdg, is_shower) -> str:
    """Reconstructed object type of a T_kine row for the fragment taxonomy."""
    a = int(abs(pdg))
    if a == 11:
        return "electron shower" if is_shower else "electron track"
    if a == 13:
        return "muon-like"
    if a == 211:
        return "pion-like"
    if a == 2212:
        return "proton-like"
    return "other"


def first_failed_stage(reach: dict) -> str:
    """First frozen stage an event stops at, from the cumulative ``reach_*`` flags (event-level ``any`` logic): evaluable, numu, other, ncpi0, nue, n_20br1, or ``final``."""
    for k in ("evaluable", "numu", "other", "ncpi0", "nue", "n20br1"):
        if not reach.get(k, False):
            return k
    return "final" if reach.get("final", False) else "n20br1"
