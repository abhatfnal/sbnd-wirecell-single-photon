"""Row-level reco-proton truth association: pure helpers (no I/O).

Everything here is characterisation: nothing changes a selection flag, threshold or policy.  The inputs are the raw tables of ``scripts/proton_truth_scan.py`` (``rows``: one line per ``T_kine`` row
joined to its production ``T_match`` level-1 row and the top-3 truth partners; ``tprot``: neutrino-origin true protons; ``evt``).

Truth semantics (``docs/analysis/WIRECELL_TRUTH_MATCH_SEMANTICS.md``): a level-1 reco object is one ``T_kine`` row (``nu_index``, ``kine_index``); its partners are truth **prongs** (``truth_trackid`` =
``prong_trackid``) ranked by point IoU; the stored order IS the production ranking, the top partner is ``p1``.  ``t_nu`` is the truth interaction (``T_truth_nu.nu_idx``; -1 = non-neutrino object).
"""
from __future__ import annotations
import numpy as np, pandas as pd

ROW_CLASSES = (
    "true_primary_signal_proton",          # A  top partner = a post-FSI primary proton of the signal interaction
    "other_neutrino_proton",               # B  top partner = a proton (primary or secondary) of ANOTHER neutrino interaction
    "geant4_secondary_proton",             # C  top partner = a proton of the signal interaction that is not a primary (Geant4 secondary)
    "signal_nonproton_misidentified",      # D  top partner = another particle of the signal interaction
    "other_neutrino_nonproton",            # E  top partner = a non-proton particle of another neutrino interaction
    "cosmic_or_non_neutrino",              # F  top partner = a non-neutrino (cosmic) object
    "ambiguous_multiple_truth",            # G  the top two partners are different origin classes and the second is comparable (>= ratio x top point IoU)
    "unmatched",                           # H  no partner (nmatch == 0) or no level-1 row
)
PRIMARY_PROCESS = 0
D_SUBTYPES = ("photon_electron", "pion", "muon", "neutron", "other")


def _sub_d(pdg):
    a = abs(int(pdg))
    return "photon_electron" if a in (22, 11) else "pion" if a in (211, 111) else "muon" if a == 13 else "neutron" if a == 2112 else "other"


def partner_class(t_nu, t_pdg, t_prim, sig_nu):
    """Origin class (A-F) of ONE truth partner.  ``t_nu`` -9 (partner unresolved) is treated as non-neutrino (never occurs on the official sample: asserted in the audit)."""
    if t_nu < 0:
        return "cosmic_or_non_neutrino"
    if t_nu == sig_nu:
        if int(t_pdg) == 2212:
            return "true_primary_signal_proton" if t_prim else "geant4_secondary_proton"
        return "signal_nonproton_misidentified"
    return "other_neutrino_proton" if int(t_pdg) == 2212 else "other_neutrino_nonproton"


def classify_rows(rows: pd.DataFrame, sig_nu_by_event: pd.Series, ratio: float = 0.5) -> pd.DataFrame:
    """Add ``origin`` (mutually exclusive, exhaustive: ``ROW_CLASSES``), ``origin_top`` (class of the top partner alone) and ``d_sub``.

    ``rows`` needs: file_index, ev, nmatch, p1_* / p2_* (iou_n, nu = ``t_nu`` fields, ``t_pdg``, ``t_prim``).  ``sig_nu_by_event`` is indexed by (file_index, ev).  ``ratio`` only defines class G
    (second partner's point IoU >= ratio x the top partner's, and a different class); ``ratio=None`` disables G (the top-partner class stands)."""
    r = rows.copy()
    sig = pd.MultiIndex.from_frame(r[["file_index", "ev"]]).map(lambda k: sig_nu_by_event.get(k, -99)).to_numpy()
    r["p1_prim"] = r.p1_t_proc.fillna(-1).astype(int) == PRIMARY_PROCESS      # primary (generator-level, post-FSI) particle: Geant4 ``process`` code 0.  NOT ``parent_trackid == 0`` (a secondary whose parent was not stored has parent 0 too)
    r["p2_prim"] = r.p2_t_proc.fillna(-1).astype(int) == PRIMARY_PROCESS
    has1 = (r.nmatch.fillna(0) > 0).to_numpy() & r.p1_t_nu.notna().to_numpy() & (r.p1_tid.fillna(-1) >= 0).to_numpy()
    top = np.array([partner_class(a, b, c, s) if h else "unmatched" for a, b, c, s, h in zip(r.p1_t_nu.fillna(-9), r.p1_t_pdg.fillna(0), r.p1_prim, sig, has1)], dtype=object)
    has2 = (r.nmatch.fillna(0) >= 2).to_numpy() & r.p2_t_nu.notna().to_numpy() & (r.p2_tid.fillna(-1) >= 0).to_numpy()
    sec = np.array([partner_class(a, b, c, s) if h else "" for a, b, c, s, h in zip(r.p2_t_nu.fillna(-9), r.p2_t_pdg.fillna(0), r.p2_prim, sig, has2)], dtype=object)
    out = top.copy()
    if ratio is not None:
        comparable = has2 & (r.p2_iou_n.fillna(0).to_numpy() >= ratio * r.p1_iou_n.fillna(0).to_numpy()) & (r.p1_iou_n.fillna(0).to_numpy() > 0)
        out = np.where(comparable & (sec != top), "ambiguous_multiple_truth", top)
    r["sig_nu"] = sig; r["origin_top"] = top; r["origin"] = out
    r["unmatched_reason"] = np.where(~r.has_match_row.fillna(False).astype(bool), "no_level1_object", np.where(r.nmatch.fillna(0) == 0, "nmatch_0", np.where(~has1, "partner_unresolved_or_unreadable", "")))
    r["d_sub"] = [(_sub_d(p) if o == "signal_nonproton_misidentified" else "") for p, o in zip(r.p1_t_pdg.fillna(0), top)]
    assert set(r.origin) <= set(ROW_CLASSES)
    return r


TRUE_PROTON_STATES = (
    "no_signal_candidate",          # the event has no candidate / no signal-matched candidate: no reco object of the signal exists to hold the proton
    "proton_row_single",            # exactly one row of the signal-matched candidate has the proton as top partner and it is typed 2212
    "proton_row_multiple",          # >= 2 rows of the signal-matched candidate have it as top partner and at least one is typed 2212
    "matched_nonproton_row",        # rows have it as top partner but none is typed 2212
    "in_other_candidate_only",      # only rows of a candidate other than the signal-matched one have it as top partner
    "subdominant_only",             # it is a 2nd/3rd partner of some row of the signal-matched candidate but never the top partner
    "no_reco_row",                  # no row of any candidate has it as a partner (its imaging points sit in rest-of-cluster objects, unclaimed clusters, or are unlabeled / absent)
)


def true_proton_states(tp: pd.DataFrame, rows: pd.DataFrame, match_cand: pd.Series, threshold_mev: float | None = None) -> pd.DataFrame:
    """Reconstruction state of every true proton in ``tp`` (one row per proton; needs file_index, ev, trackid), given the baseline's signal-matched candidate per event (``match_cand``, NaN = none).

    Hierarchy (first match wins) is ``TRUE_PROTON_STATES``.  Rows are matched to the proton by the production top partner (``p1_tid``); ``p2_tid`` / ``p3_tid`` give ``subdominant_only``."""
    t = tp.copy()
    mc = pd.MultiIndex.from_frame(t[["file_index", "ev"]]).map(lambda k: match_cand.get(k, np.nan)).to_numpy(dtype=float)
    t["match_cand"] = mc
    key = ["file_index", "ev"]
    rr = rows[key + ["cand", "row", "kine_particle_type", "p1_tid", "p2_tid", "p3_tid"]].copy()
    top = rr.rename(columns=dict(p1_tid="trackid"))[key + ["cand", "row", "kine_particle_type", "trackid"]]
    sub = pd.concat([rr.rename(columns={c: "trackid"})[key + ["cand", "row", "trackid"]] for c in ("p2_tid", "p3_tid")], ignore_index=True)
    m = t[key + ["trackid", "match_cand"]].reset_index().merge(top, on=key + ["trackid"], how="left")
    m["in_match"] = m.cand == m.match_cand; m["is_p"] = m.kine_particle_type == 2212
    g = m.groupby("index").agg(n_top_any=("cand", lambda s: int(s.notna().sum())), n_top_match=("in_match", "sum"), n_p_match=("is_p", lambda s: 0))
    gp = m[m.in_match & m.is_p].groupby("index").size().rename("n_p_match"); g = g.drop(columns="n_p_match").join(gp).fillna({"n_p_match": 0})
    s2 = t[key + ["trackid", "match_cand"]].reset_index().merge(sub, on=key + ["trackid"], how="inner"); s2 = s2[s2.cand == s2.match_cand].groupby("index").size().rename("n_sub_match")
    t = t.join(g, how="left").join(s2, how="left").fillna({"n_top_any": 0, "n_top_match": 0, "n_p_match": 0, "n_sub_match": 0})
    st = np.full(len(t), "no_reco_row", dtype=object)
    st[(t.n_sub_match > 0).to_numpy()] = "subdominant_only"
    st[((t.n_top_any > 0) & (t.n_top_match == 0)).to_numpy()] = "in_other_candidate_only"
    st[((t.n_top_match > 0) & (t.n_p_match == 0)).to_numpy()] = "matched_nonproton_row"
    st[(t.n_p_match >= 2).to_numpy()] = "proton_row_multiple"
    st[((t.n_top_match >= 1) & (t.n_p_match == 1)).to_numpy()] = "proton_row_single"
    st[t.match_cand.isna().to_numpy()] = "no_signal_candidate"
    t["state"] = st
    assert set(t.state) <= set(TRUE_PROTON_STATES)
    return t


def reco_multiplicity(n: np.ndarray) -> np.ndarray:
    """0, 1, 2, 3+ bins used by the multiplicity response (3+ = 3)."""
    return np.minimum(np.asarray(n, int), 3)


def migration_reason_1p_to_0p(n_true_ge_thr: int, row_info: pd.DataFrame, thr: float) -> str:
    """Exclusive reason why a truth-1p event (one primary signal proton above ``thr``) has zero reco proton rows above ``thr`` in the evaluated candidate.

    ``row_info`` = the rows of the evaluated candidate that have the proton as top partner (columns: kine_particle_type, kine_energy_particle, kine_energy_included, kine_particle_is_shower).
    Hierarchy: 1 a row typed proton with KE > thr and ``included != 3`` exists (cannot happen if reco0p) -> only checked for closure;
      proton typed, KE <= thr -> ``proton_reco_ke_below_threshold``; proton typed with KE > thr only through ``included == 3`` rows is NOT excluded by the baseline (they count), so it cannot occur;
      non-proton typed row -> ``matched_row_nonproton_pid``; no rows -> caller decides (``never_reconstructed`` / ``in_other_candidate`` / ``ambiguous`` / ``other``)."""
    if len(row_info) == 0:
        return "no_matched_row"
    p = row_info[row_info.kine_particle_type == 2212]
    if len(p) == 0:
        return "matched_row_nonproton_pid"
    if (p.kine_energy_particle > thr).any():
        return "proton_row_above_threshold"
    return "proton_reco_ke_below_threshold"
