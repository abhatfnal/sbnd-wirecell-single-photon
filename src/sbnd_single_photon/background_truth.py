"""Candidate-associated truth for the Wire-Cell single-photon candidates (MC evaluation only; truth never selects anything).

Association actually used: the PRODUCTION bipartite matching ``wc.T_match`` at ``level == 3`` (candidate defined by the particle-flow-tree
segments, ``side == 0``, ``nu_index`` = the candidate) against the truth objects (``side == 1``: ``truth_nu_idx >= 0`` is a truth
neutrino interaction, ``truth_nu_idx == -1`` with ``truth_trackid > 0`` is a cosmic/non-neutrino truth object). For each candidate the
production stores up to 3 partners (``match_obj``) IN ORDER of decreasing ``match_iou_n`` (point IoU; ties ``match_iou_q``, then lower obj),
plus ``match_iou_q``/``match_shared_q`` and ``mutual``. SOURCE-DEFINED top partner = the FIRST stored one (``rule="source"``, default; the
design document of the matcher, docs/analysis/WIRECELL_TRUTH_MATCH_SEMANTICS.md). Phase 4 had used the largest charge IoU among the stored
partners (``rule="iou_q"``, kept for comparison only). No threshold is invented.
Cross-check association (not used for the label): the dominant-charge truth neutrino from ``wc.T_overlap`` already in the derived table.
See docs/analysis/PASSING_CANDIDATE_TRUTH_ASSOCIATION.md.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import awkward as ak

from .truth import ActiveVolume

PROTON_MASS_MEV = 938.272
MATCH_SCALARS = ["level", "side", "obj", "nu_index", "truth_nu_idx", "truth_trackid", "nmatch", "mutual"]
MATCH_JAGGED = ["match_obj", "match_iou_n", "match_iou_q", "match_shared_n", "match_shared_q"]
UNMATCHED, COSMIC = -9, -1          # tm_top_nu codes besides a truth neutrino index (>= 0)

CATEGORIES = ("SIGNAL_NCDELTA", "NC_PI0", "CC_PI0", "NUE_CC", "NUMU_CC", "OTHER_NC", "OTHER_CC", "OUTSIDE_TPC_NU",
              "COSMIC_OR_UNMATCHED", "MULTI_OR_AMBIGUOUS")


def rows_and_items(f, start: int = 0, stop=None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """All ``wc.T_match`` rows (one per matched object) and their match items, with a per-file event index ``ev`` (0-based from ``start``)."""
    sc = {c: f._wt["wc.T_match." + c].array(entry_start=start, entry_stop=stop, library="ak") for c in MATCH_SCALARS}
    cnt = ak.to_numpy(ak.num(sc["level"], axis=1))
    R = pd.DataFrame({c: ak.to_numpy(ak.flatten(v)) for c, v in sc.items()})
    R["ev"] = np.repeat(np.arange(len(cnt)) + start, cnt)
    R["row"] = np.arange(len(R))
    jag = {c: f.read_nested("wc.T_match." + c, start, stop) for c in MATCH_JAGGED}
    lens = ak.to_numpy(ak.flatten(ak.num(jag["match_obj"], axis=2)))
    I = pd.DataFrame({c: ak.to_numpy(ak.flatten(v, axis=None)) for c, v in jag.items()})
    I["row"] = np.repeat(R.row.values, lens)
    return R, I


def candidate_association(R: pd.DataFrame, I: pd.DataFrame, rule: str = "source") -> pd.DataFrame:
    """One row per (ev, nu_index) candidate: production top match and its quality (see module docstring).

    ``rule="source"``: top = first stored partner (production order, decreasing point IoU). ``rule="iou_q"``: largest charge IoU (Phase 4)."""
    if rule not in ("source", "iou_q"):
        raise ValueError(rule)
    I = I.copy()
    I["pos"] = I.groupby("row").cumcount()
    C = R[(R.level == 3) & (R.side == 0) & (R.nu_index >= 0)][["row", "ev", "nu_index", "mutual", "nmatch"]]
    T = R[(R.level == 3) & (R.side == 1)][["ev", "obj", "truth_nu_idx", "truth_trackid"]].rename(columns={"obj": "match_obj"})
    m = I.merge(C[["row", "ev", "nu_index"]], on="row").merge(T, on=["ev", "match_obj"], how="left")
    m["truth_nu_idx"] = m.truth_nu_idx.fillna(-1).astype(int)
    if rule == "source":
        m = m.sort_values(["ev", "nu_index", "pos"], kind="stable")
    else:
        m = m.sort_values(["ev", "nu_index", "match_iou_q", "match_shared_q"], ascending=[True, True, False, False])
    g = m.groupby(["ev", "nu_index"], sort=False)
    top = g.head(1).set_index(["ev", "nu_index"])
    sec = g.nth(1).set_index(["ev", "nu_index"]).match_iou_q.rename("tm_second_iou")
    extra = [c for c in ("match_iou_n",) if c in top.columns]
    agg = pd.DataFrame({"tm_n": g.size(), "tm_n_distinct_nu": g.apply(lambda d: d.loc[d.truth_nu_idx >= 0, "truth_nu_idx"].nunique()),
                        "tm_n_cosmic": g.apply(lambda d: int((d.truth_nu_idx < 0).sum()))})
    out = C.set_index(["ev", "nu_index"])[["mutual"]].rename(columns={"mutual": "tm_mutual"}).join(agg).join(sec)
    out = out.join(top[["truth_nu_idx", "truth_trackid", "match_iou_q", "match_shared_q"] + extra].rename(
        columns={"truth_nu_idx": "tm_top_nu", "truth_trackid": "tm_top_trackid", "match_iou_q": "tm_top_iou", "match_shared_q": "tm_top_shared",
                 "match_iou_n": "tm_top_iou_n"}))
    out["tm_n"] = out.tm_n.fillna(0).astype(int)
    out["tm_n_distinct_nu"] = out.tm_n_distinct_nu.fillna(0).astype(int)
    out["tm_n_cosmic"] = out.tm_n_cosmic.fillna(0).astype(int)
    out["tm_top_nu"] = out.tm_top_nu.fillna(UNMATCHED).astype(int)
    out["tm_top_trackid"] = out.tm_top_trackid.fillna(-1).astype(np.int64)
    return out.reset_index()


def truth_nu_table(f, start: int = 0, stop=None) -> pd.DataFrame:
    cols = ["nu_idx", "pdg", "ccnc", "mode", "int_type", "E", "vtx_x", "vtx_y", "vtx_z", "edep"]
    a = f._wt.arrays(["wc.T_truth_nu." + c for c in cols], entry_start=start, entry_stop=stop, library="ak", how=dict)
    cnt = ak.to_numpy(ak.num(a["wc.T_truth_nu.pdg"], axis=1))
    d = pd.DataFrame({c: ak.to_numpy(ak.flatten(a["wc.T_truth_nu." + c])) for c in cols})
    d["ev"] = np.repeat(np.arange(len(cnt)) + start, cnt)
    return d


def recnu_table(d: dict) -> pd.DataFrame:
    """Per rec.mc.nu interaction (ev, k) from ``truth_signal.read_truth_arrays`` output: flavour, CC/NC, mode, vertex, primary-content counts."""
    from .truth_signal import _regroup
    g = lambda n: d["rec.mc.nu." + n]
    nprim = g("nprim")
    ppdg = _regroup(d["rec.mc.nu.prim.pdg"], nprim); pe = _regroup(d["rec.mc.nu.prim.genE"], nprim)
    ke = (pe - PROTON_MASS_MEV / 1000.0) * 1000.0
    cnt = ak.to_numpy(ak.num(g("pdg"), axis=1))
    fl = lambda a: ak.to_numpy(ak.flatten(a))
    out = pd.DataFrame(dict(ev=np.repeat(np.arange(len(cnt)), cnt), k=np.concatenate([np.arange(c) for c in cnt]) if cnt.sum() else np.zeros(0, int),
                            pdg=fl(g("pdg")), iscc=fl(g("iscc")), isnc=fl(g("isnc")), mode=fl(g("genie_mode")), E=fl(g("E")),
                            x=fl(g("position.x")), y=fl(g("position.y")), z=fl(g("position.z")),
                            n_pi0=fl(ak.sum(ppdg == 111, axis=2)), n_p35=fl(ak.sum((ppdg == 2212) & (ke > 35.0), axis=2)),
                            n_photon=fl(ak.sum(ppdg == 22, axis=2)), nprim=fl(nprim)))
    return out


def link_truth_nu_to_recnu(tn: pd.DataFrame, rn: pd.DataFrame) -> pd.DataFrame:
    """Wire-Cell truth neutrino (ev, nu_idx) -> rec.mc.nu index k by nearest vertex within the event (distance kept; the Wire-Cell truth keeps the beam neutrinos only)."""
    m = tn[["ev", "nu_idx", "vtx_x", "vtx_y", "vtx_z"]].merge(rn[["ev", "k", "x", "y", "z"]], on="ev", how="left")
    m["link_dist_cm"] = np.sqrt((m.vtx_x - m.x) ** 2 + (m.vtx_y - m.y) ** 2 + (m.vtx_z - m.z) ** 2)
    m = m.sort_values(["ev", "nu_idx", "link_dist_cm"]).drop_duplicates(["ev", "nu_idx"])
    return m[["ev", "nu_idx", "k", "link_dist_cm"]]


def classify_candidate(top_nu, n_distinct_nu, tm_n, pdg, iscc, n_pi0, in_tpc, is_signal) -> str:
    """Candidate-associated category from the production match + the matched interaction (provisional TPC box only for the in/out distinction).

    COSMIC_OR_UNMATCHED: no match, or the top match is a non-neutrino truth object. MULTI_OR_AMBIGUOUS: the candidate overlaps >= 2 distinct truth
    neutrino interactions (structural, no threshold). Otherwise: signal > outside-TPC > pi0 (NC/CC) > flavour/CC-NC, matching the precedence of the
    event-level taxonomy (BNB_TRUTH_CATEGORY_AUDIT.md)."""
    if tm_n == 0 or top_nu == UNMATCHED or top_nu == COSMIC:
        return "COSMIC_OR_UNMATCHED"
    if n_distinct_nu >= 2:
        return "MULTI_OR_AMBIGUOUS"
    if is_signal:
        return "SIGNAL_NCDELTA"
    if not in_tpc:
        return "OUTSIDE_TPC_NU"
    if n_pi0 >= 1:
        return "CC_PI0" if iscc else "NC_PI0"
    if iscc:
        return "NUE_CC" if abs(pdg) == 12 else ("NUMU_CC" if abs(pdg) == 14 else "OTHER_CC")
    return "OTHER_NC"


def origin_class(pdg, nu_idx, trackid) -> str:
    """Truth-origin class of a reco shower from the dominant overlapping truth track: photon / electron_positron / proton / muon / charged_pion /
    neutron_or_hadronic / other, or cosmic_or_unmatched when no neutrino-owned track dominates."""
    if trackid is None or trackid < 0 or nu_idx is None or nu_idx < 0 or not np.isfinite(pdg):
        return "cosmic_or_unmatched"
    a = abs(int(pdg))
    return {22: "photon", 11: "electron_positron", 2212: "proton", 13: "muon", 211: "charged_pion", 2112: "neutron_or_hadronic"}.get(a, "other")


PI0_MASS_MEV = 134.9768


def pi0_photon_summary(e1_gev, e2_gev) -> dict:
    """Two-photon decay kinematics from the daughter energies: asymmetry |E1-E2|/(E1+E2) and opening angle from m^2 = 2 E1 E2 (1 - cos theta)
    (exact for pi0 -> gamma gamma; NaN when the argument leaves [-1, 1], which flags an inconsistent record)."""
    e1, e2 = float(max(e1_gev, e2_gev)) * 1000.0, float(min(e1_gev, e2_gev)) * 1000.0
    if e2 <= 0:
        return dict(lead_mev=e1, sub_mev=e2, asymmetry=np.nan, opening_angle_deg=np.nan)
    c = 1.0 - PI0_MASS_MEV ** 2 / (2.0 * e1 * e2)
    ang = float(np.degrees(np.arccos(c))) if -1.0 <= c <= 1.0 else np.nan
    return dict(lead_mev=e1, sub_mev=e2, asymmetry=(e1 - e2) / (e1 + e2), opening_angle_deg=ang)


def photon_fate_labels(r: dict, prefix: str) -> list[str]:
    """Overlapping diagnostic labels for one pi0 daughter photon (``prefix`` e.g. 'ph2_') from the deep-scan fields. Labels may co-occur; no hierarchy is
    imposed. ``lt20`` truth E < 20 MeV; ``no_charge`` no charge in blobs; ``exits`` photon end point outside the provisional TPC; ``no_reco_row`` no
    overlap row in any candidate; ``other_candidate`` dominant reco row belongs to another candidate; ``same_candidate_other_row``; ``nonshower_row`` the
    dominant row in the candidate is not a shower / not type 11; ``selected_row`` it is the selected shower; ``merged_with_selected`` it also
    contributes charge to the selected shower row."""
    g = lambda k, d=None: r.get(prefix + k, d)
    if g("E") is None or (isinstance(g("E"), float) and np.isnan(g("E"))):
        return ["absent"]
    out = []
    if g("lt20"): out.append("lt20")
    if (g("q_in_blobs") or 0) == 0: out.append("no_charge")
    if g("end_in_tpc") is False or g("end_in_tpc") == 0: out.append("exits")
    n = g("n_overlap_rows") or 0
    if n == 0:
        out.append("no_reco_row")
    else:
        if g("is_selected_row"): out.append("selected_row")
        elif g("same_cand") is False or g("same_cand") == 0: out.append("other_candidate")
        else:
            out.append("same_candidate_other_row")
            if g("dom_row_is_shower") is False or g("dom_row_is_shower") == 0 or (g("dom_row_type") not in (None, 11) and g("dom_row_type") == g("dom_row_type")):
                out.append("nonshower_row")
        if (g("q_in_selected_row") or 0) > 0 and not g("is_selected_row"): out.append("merged_with_selected")
    return out
