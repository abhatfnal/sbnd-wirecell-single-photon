"""Vertex provenance (DL vertex -> final vertex) and shower-attachment helpers (Phase 16).  Pure functions, no I/O.

DESCRIPTIVE ONLY: nothing here changes a selection, a threshold, a vertex or a type.

Frames: every vertex of ``T_dlvtx_call`` (trad_*, rerank_*, dl_*, hint_*, final_*) is in the raw reconstruction frame (cm); the truth vertex of the same table is shifted into that frame by the TrueFwd SCE map
(``truth_all_reco_*``).  Displacements are therefore frame-consistent differences.  See ``docs/analysis/DL_VERTEX_SOURCE_AUDIT.md``.
"""
from __future__ import annotations
import numpy as np

ANCHOR_TOL_CM = 5.0           # the Phase-9 proximity tolerance (sensitivity at 3 and 10 cm is reported by the audit)
NOT_SEPARABLE_CM = 5.0        # below this true conversion distance the interaction vertex and the conversion point are not separable at the tolerance (Phase 9)

PROVENANCE_CLASSES = ["A DL displaced along the photon, final stays there", "B DL at the interaction vertex, final moves along the photon", "C DL at the interaction vertex, final stays anchored",
                      "D DL displaced, final corrects toward the interaction vertex", "E other DL / final disagreement", "S conversion distance < 5 cm (not separable)", "F missing / unresolved"]


def unit(v):
    v = np.asarray(v, float); n = np.linalg.norm(v)
    return v / n if n > 0 else v


def decompose(v_from, v_to, direction) -> dict:
    """Displacement ``v_to - v_from`` split along ``direction`` (the true photon direction) and perpendicular to it (cm).  ``parallel`` is signed (positive = along the photon flight)."""
    d = np.asarray(v_to, float) - np.asarray(v_from, float); u = unit(direction)
    par = float(d @ u); perp = float(np.linalg.norm(d - par * u))
    return dict(dx=float(d[0]), dy=float(d[1]), dz=float(d[2]), mag=float(np.linalg.norm(d)), parallel=par, perp=perp)


def vertex_state(v, v_true, conv_pt, tol: float = ANCHOR_TOL_CM) -> str:
    """Where a vertex sits relative to the true interaction vertex and the true conversion point: ``interaction`` (within tol of the vertex and not closer to the conversion point), ``conversion`` (within tol of the
    conversion point and closer to it than to the vertex), ``between`` (neither, but d_vertex + d_conv <= 1.2 x the vertex-conversion distance), ``neither``; ``undefined`` for a non-finite input."""
    v, vt, cp = (np.asarray(a, float) for a in (v, v_true, conv_pt))
    if not (np.isfinite(v).all() and np.isfinite(vt).all() and np.isfinite(cp).all()):
        return "undefined"
    dv = float(np.linalg.norm(v - vt)); dc = float(np.linalg.norm(v - cp)); lc = float(np.linalg.norm(cp - vt))
    if dv <= tol and dv <= dc:
        return "interaction"
    if dc <= tol and dc < dv:
        return "conversion"
    if dv + dc <= 1.2 * lc:
        return "between"
    return "neither"


def provenance_class(dl_state: str, final_state: str, conv_distance_cm: float, have_dl: bool = True) -> str:
    """Exclusive provenance hierarchy of an event from the state of the DL vertex and of the final vertex (``vertex_state``):
    S not separable (true conversion < 5 cm); F missing; A DL displaced along the photon (conversion / between) and the final vertex also there; B DL at the interaction vertex and the final vertex displaced along the
    photon; C both at the interaction vertex; D DL displaced (conversion / between / neither) and the final vertex at the interaction vertex; E everything else."""
    if not np.isfinite(conv_distance_cm):
        return PROVENANCE_CLASSES[6]
    if conv_distance_cm < NOT_SEPARABLE_CM:
        return PROVENANCE_CLASSES[5]
    if not have_dl or "undefined" in (dl_state, final_state):
        return PROVENANCE_CLASSES[6]
    along = ("conversion", "between")
    if dl_state in along and final_state in along:
        return PROVENANCE_CLASSES[0]
    if dl_state == "interaction" and final_state in along:
        return PROVENANCE_CLASSES[1]
    if dl_state == "interaction" and final_state == "interaction":
        return PROVENANCE_CLASSES[2]
    if dl_state in along + ("neither",) and final_state == "interaction":
        return PROVENANCE_CLASSES[3]
    return PROVENANCE_CLASSES[4]


def line_state(parallel: float, perp: float, tol: float = ANCHOR_TOL_CM) -> str:
    """State of a vertex from its displacement from the true vertex (signed ``parallel`` along the true photon direction, ``perp`` the perpendicular size): ``anchored`` (|d| <= tol), ``along`` (parallel > tol and
    perp <= parallel: within 45 deg of the photon flight line), ``against`` (parallel < -tol and perp <= |parallel|), ``off-axis`` otherwise; ``undefined`` for a non-finite input."""
    if not (np.isfinite(parallel) and np.isfinite(perp)):
        return "undefined"
    if np.hypot(parallel, perp) <= tol:
        return "anchored"
    if parallel > tol and perp <= parallel:
        return "along"
    if parallel < -tol and perp <= -parallel:
        return "against"
    return "off-axis"


def provenance_class_line(dl_state: str, final_state: str, conv_distance_cm: float, have_dl: bool = True) -> str:
    """Same hierarchy as ``provenance_class`` but on the line-based states: A both ``along``; B DL anchored and final ``along``; C both anchored; D DL displaced (along / against / off-axis) and final anchored;
    E everything else (including DL along and final elsewhere); S not separable; F missing."""
    if not np.isfinite(conv_distance_cm):
        return PROVENANCE_CLASSES[6]
    if conv_distance_cm < NOT_SEPARABLE_CM:
        return PROVENANCE_CLASSES[5]
    if not have_dl or "undefined" in (dl_state, final_state):
        return PROVENANCE_CLASSES[6]
    if dl_state == "along" and final_state == "along":
        return PROVENANCE_CLASSES[0]
    if dl_state == "anchored" and final_state == "along":
        return PROVENANCE_CLASSES[1]
    if dl_state == "anchored" and final_state == "anchored":
        return PROVENANCE_CLASSES[2]
    if dl_state != "anchored" and final_state == "anchored":
        return PROVENANCE_CLASSES[3]
    return PROVENANCE_CLASSES[4]


def dl_vertex_of_call(accepted: bool, dl, trad, trad_valid: bool):
    """The DL-stage vertex of a production call: the accepted DL graph vertex, else (the DL changed nothing) the traditional vertex; ``None`` if neither exists."""
    if accepted:
        return np.asarray(dl, float), "dl_accepted"
    if trad_valid:
        return np.asarray(trad, float), "traditional_kept"
    return None, "none"


# ------------------------------------------------------------------------------------------------------------------------------ PF-tree ancestry
def ancestor_chain(node_id, nodes: dict):
    """Chain from a PF node up to the root: ``nodes`` maps ``node_id -> (parent_id, pdg, is_pseudo, kine_index)``; returns ``[(node_id, pdg, is_pseudo, kine_index), ...]`` starting at the node itself
    (cycle-safe)."""
    out, seen, cur = [], set(), node_id
    while cur in nodes and cur not in seen:
        seen.add(cur); p, pdg, ps, ki = nodes[cur]; out.append((cur, int(pdg), bool(ps), int(ki)))
        if p == -1 or p not in nodes:
            break
        cur = p
    return out


PARENT_CLASSES = ["A direct child of the main vertex", "B under a proton-typed object", "C under a muon-like object", "D under a pion-like object", "E under a generic (electron / other) object",
                  "F under pseudo objects only (no real ancestor)", "G different candidate", "H unresolved"]


def parent_class(chain, in_other_candidate: bool = False) -> tuple:
    """Task-11 class of a shower from its PF ancestor chain (first element = the shower node itself).  Returns ``(class, nearest_real_ancestor_pdg_or_None, under_pi0_pseudo)``.
    Real ancestors are non-pseudo nodes above the shower; ``under_pi0_pseudo`` is true if a pseudo pdg-111 node lies on the chain."""
    if in_other_candidate:
        return PARENT_CLASSES[6], None, False
    if not chain:
        return PARENT_CLASSES[7], None, False
    anc = chain[1:]; pi0 = any(pdg == 111 and ps for _, pdg, ps, _ in anc)
    real = [(pdg, ki) for _, pdg, ps, ki in anc if not ps]
    if not anc or (len(anc) == 1 and anc[0][2] and anc[0][1] == 22):
        return PARENT_CLASSES[0], None, pi0                               # root, or a root-level pseudo photon wrapper
    if not real:
        return PARENT_CLASSES[5], None, pi0
    pdg = abs(real[0][0])
    return {2212: PARENT_CLASSES[1], 13: PARENT_CLASSES[2], 211: PARENT_CLASSES[3]}.get(pdg, PARENT_CLASSES[4]), real[0][0], pi0


ATTACH_MECHANISMS = ["member of a reconstructed pi0 pair (pseudo-pi0 ancestor)", "indirect shower under a track-typed object that is itself a piece of the signal photon (type inheritance / fragmentation)",
                     "indirect shower under a true hadronic object of the signal interaction", "indirect shower under another object (generic / other truth)", "direct child of the main vertex node or root (start vertex differs)", "unresolved"]


def attach_mechanism(pclass: str, under_pi0: bool, parent_truth: str) -> str:
    """Exclusive event-level mechanism label (descriptive hierarchy): pi0-pair membership first; otherwise by the truth of the nearest real ancestor."""
    if pclass == PARENT_CLASSES[7]:
        return ATTACH_MECHANISMS[5]
    if under_pi0:
        return ATTACH_MECHANISMS[0]
    if pclass == PARENT_CLASSES[0]:
        return ATTACH_MECHANISMS[4]
    if parent_truth in ("signal_photon_dominant", "signal_photon_fragment"):
        return ATTACH_MECHANISMS[1]
    if parent_truth in ("signal_proton", "signal_other_hadron"):
        return ATTACH_MECHANISMS[2]
    return ATTACH_MECHANISMS[3]
