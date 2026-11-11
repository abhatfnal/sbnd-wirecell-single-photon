#!/usr/bin/env python
"""Phase 16: (T) why does a correctly reconstructed energetic electron shower of the signal photon sit outside the main-vertex shower set, and (V) where is the photon-line vertex displacement of truth-0p events
introduced: by the deep-learning vertex itself or by later Wire-Cell vertex / PF refinement?  CHARACTERISATION ONLY: no selection, threshold, retraining, FV, proton-policy or candidate-policy change.

    source env/setup_eaf.sh
    python scripts/dl_vertex_scan.py --workers 24          # targeted, resumable T_dlvtx_call scan (once)
    python scripts/vertex_provenance_audit.py              # reads the Phase 9 / 10 / 14 / 15 tables and the DL scan

Truth: the source-ranked ``T_match`` level-1 partner (Phase-10 ``row_matches``); the signal vertex in the raw reconstruction frame is the signal interaction's ``truth_all_reco_*`` of ``T_dlvtx_call`` (TrueFwd SCE
shift).  Outputs: ``$SP_DATA/vertex_provenance_audit/official_ncdelta/``, ``tables/vertex_provenance_audit/``, ``plots/vertex_provenance_audit/``.
"""
from __future__ import annotations
import hashlib, json, os, subprocess, sys, warnings
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from sbnd_single_photon import pair_audit as PA, vertex_audit as VA

SPD = Path(os.environ["SP_DATA"]); OUT = SPD / "vertex_provenance_audit" / "official_ncdelta"; RAW = OUT / "raw"
P9 = SPD / "shower_vertex_audit" / "official_ncdelta"; P10 = SPD / "proton_truth_association" / "official_ncdelta"; P14 = SPD / "pi0_pair_fragmentation_audit" / "official_ncdelta"; P15 = SPD / "particle_pid_audit" / "official_ncdelta"
TAB = REPO / "tables" / "vertex_provenance_audit"; PLT = REPO / "plots" / "vertex_provenance_audit"
K = ["file_index", "ev"]
POP = "photon_shower_not_in_main_vertex_set"


def pq(df, path):
    df = df.copy()
    for c in df.columns:
        if "Interval" in str(df[c].dtype) or str(df[c].dtype) == "category":
            df[c] = df[c].astype(str)
    df.to_parquet(path, index=False)


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def cp(k, n):
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    f = k / n; den = 1 + 1 / n; c = (f + 1 / (2 * n)) / den; h = np.sqrt(f * (1 - f) / n + 1 / (4 * n * n)) / den
    return f, c - h, c + h


def q68(s):
    s = pd.Series(s).dropna()
    return (float(s.quantile(0.5)), float(s.quantile(0.16)), float(s.quantile(0.84))) if len(s) else (np.nan,) * 3


def load():
    D = {"E": pd.read_parquet(P9 / "event_taxonomy.parquet"), "V": pd.read_parquet(P9 / "vertex_geometry.parquet"), "pf": pd.read_parquet(P9 / "raw" / "pf.parquet"), "kine": pd.read_parquet(P9 / "raw" / "kine.parquet"),
         "cand": pd.read_parquet(P9 / "raw" / "cand.parquet"), "rm": pd.read_parquet(P10 / "row_matches.parquet"), "tp": pd.read_parquet(P15 / "proton_pid_events.parquet"), "pe": pd.read_parquet(P15 / "photon_pid_events.parquet")}
    x = RAW / "dl_calls.parquet"; D["dl"] = pd.read_parquet(x) if x.exists() else (pd.concat([pd.read_parquet(f) for f in sorted((RAW / "dl_calls").glob("*.parquet"))], ignore_index=True) if (RAW / "dl_calls").exists() else None)
    for n, d in D.items():
        if d is not None and "file_index" in d:
            d[K] = d[K].astype(int)
    return D


# =============================================================================================================== shower attachment (T)
def row_class_lookup(D, keys):
    """Truth class of the (event, candidate, row) rows needed: Phase-14 taxonomy on the Phase-10 source-ranked partner."""
    rm = D["rm"].merge(D["E"][K + ["photon_trackid", "signal_nu_idx", "dom_nu", "dom_row"]], on=K)
    rm = rm.merge(keys, on=K + ["cand", "row"])
    out = {}
    for r in rm.itertuples():
        isdom = bool(np.isfinite(r.dom_nu) and int(r.dom_nu) == r.cand and int(r.dom_row) == r.row)
        out[(r.file_index, r.ev, r.cand, r.row)] = PA.row_truth_class(r.p1_tid, r.p1_t_pdg, r.p1_t_nu, r.p1_iou_n, r.p2_tid, r.p2_iou_n, r.p2_t_nu, r.photon_trackid, r.signal_nu_idx, isdom, {})
    return out


def attachment_events(D):
    """The Phase-9 population (outcome == photon_shower_not_in_main_vertex_set) with the PF ancestry of the dominant signal shower, the truth of the nearest real ancestor and the mechanism label."""
    E = D["E"]; P = E[E.outcome == POP].copy()
    pf = D["pf"].copy(); pf["nu_index"] = pf.nu_index.astype(int)
    nodes = {k: {int(r.node_id): (int(r.parent_id), r.pdg, r.is_pseudo, r.kine_index) for r in g.itertuples()} for k, g in pf.groupby(K + ["nu_index"])}
    node_of = {k: g for k, g in pf[pf.kine_index >= 0].sort_values("depth").drop_duplicates(K + ["nu_index", "kine_index"]).groupby(K + ["nu_index", "kine_index"])}
    pfg = {k: g.set_index("node_id") for k, g in pf.groupby(K + ["nu_index"])}
    need = []; recs = []
    for r in P.itertuples():
        cand = int(r.dom_nu) if np.isfinite(r.dom_nu) else -1; row = int(r.dom_row) if np.isfinite(r.dom_row) else -1
        key = (r.file_index, r.ev, cand); rec = dict(file_index=r.file_index, ev=r.ev, cand=cand, row=row, truth35=r.truth35, delta_label=r.delta_label, photon_energy_mev=r.photon_energy_mev, dom_is_sig=r.dom_is_sig)
        nd = node_of.get(key + (row,))
        if nd is None or key not in nodes:
            rec.update(pclass=VA.PARENT_CLASSES[7], under_pi0=False, chain_len=0); recs.append(rec); continue
        nid = int(nd.iloc[0].node_id); chain = VA.ancestor_chain(nid, nodes[key]); other = bool(r.dom_is_sig is False)
        pc, rpdg, pi0 = VA.parent_class(chain, other)
        real = [c for c in chain[1:] if not c[2]]
        rec.update(pclass=pc, under_pi0=pi0, real_parent_pdg=rpdg, chain_len=len(chain), pf_depth=int(nd.iloc[0].depth), chain_desc=">".join(("~" if c[2] else "") + str(c[1]) for c in chain), real_parent_ki=real[0][3] if real else -1)
        n0 = pfg[key].loc[nid]; rec.update(shw_x=float(n0.start_x), shw_y=float(n0.start_y), shw_z=float(n0.start_z))
        if real:
            pn = [i for i, v in nodes[key].items() if v[3] == real[0][3] and not v[2] and v[1] == real[0][1]]
            if pn:
                p0 = pfg[key].loc[pn[0]]; ps = np.array([p0.start_x, p0.start_y, p0.start_z]); pe = np.array([p0.end_x, p0.end_y, p0.end_z]); s = np.array([n0.start_x, n0.start_y, n0.start_z])
                rec.update(parent_ke=float(p0.ke_mev), dist_shower_to_parent_start=float(np.linalg.norm(s - ps)), dist_shower_to_parent_end=float(np.linalg.norm(s - pe)))
            need.append((r.file_index, r.ev, cand, real[0][3]))
        # pi0 sibling: the other shower leaf under the same pseudo-pi0 node
        if pi0:
            pi0_node = next(c[0] for c in chain[1:] if c[2] and c[1] == 111)
            kids = [i for i, v in nodes[key].items() if v[0] == pi0_node]
            sib = []
            for kdn in kids:
                for i, v in nodes[key].items():
                    if v[0] == kdn and not v[2] and i != nid and v[3] >= 0:
                        sib.append(v[3])
            if sib:
                rec["pi0_sibling_row"] = sib[0]; need.append((r.file_index, r.ev, cand, sib[0]))
        recs.append(rec)
    A = pd.DataFrame(recs)
    keys = pd.DataFrame(need, columns=K + ["cand", "row"]).drop_duplicates()
    lk = row_class_lookup(D, keys)
    A["parent_truth"] = [lk.get((a, b, c, int(d)), "none") if d >= 0 else "none" for a, b, c, d in zip(A.file_index, A.ev, A.cand, A.get("real_parent_ki", pd.Series(-1, index=A.index)).fillna(-1))]
    A["pi0_sibling_truth"] = [lk.get((a, b, c, int(d)), "none") if np.isfinite(d) else "none" for a, b, c, d in zip(A.file_index, A.ev, A.cand, A.get("pi0_sibling_row", pd.Series(np.nan, index=A.index)))]
    A["mechanism"] = [VA.attach_mechanism(a, b, c) for a, b, c in zip(A.pclass, A.under_pi0, A.parent_truth)]
    return A


def proton_event_class(D):
    """Task 8 classes per event from the Phase-15 proton table and the reco proton count of the signal-matched candidate (Phase 9 ``reco_np35``)."""
    tp = D["tp"]; t = tp[tp.ke > 35]
    g = t.groupby(K).agg(any_typed=("proton_class", lambda s: bool((s == "proton-typed").any())), any_merged=("proton_class", lambda s: bool((s == "merged / subdominant partner").any())), n_true=("ke", "size")).reset_index()
    e = D["E"][K + ["match_np35", "truth35"]].merge(g, on=K, how="left")
    e[["any_typed", "any_merged"]] = e[["any_typed", "any_merged"]].fillna(False).astype(bool); e["n_true"] = e.n_true.fillna(0)
    e["proton_class"] = np.where(e.any_typed, "true proton reco-typed", np.where(e.any_merged, "true proton merged (no typed true proton)", np.where(e.match_np35.fillna(0) > 0, "reco proton present, not a true proton (fake)", "no reco proton")))
    return e[K + ["proton_class"]]


def attachment_tables(D, A):
    T = {}; E = D["E"]
    n = len(A)
    T["attachment_population"] = pd.DataFrame([dict(item="events with outcome photon_shower_not_in_main_vertex_set (Phase 9)", n=int((E.outcome == POP).sum())), dict(item="reproduced population", n=n), dict(item="  of which PF state 'deeper' (Phase 9)", n=int((E[E.outcome == POP].pf_state == "deeper").sum())),
                                               dict(item="  PF state photon_node_at_vertex", n=int((E[E.outcome == POP].pf_state == "photon_node_at_vertex").sum())), dict(item="  PF state root", n=int((E[E.outcome == POP].pf_state == "root").sum())),
                                               dict(item="events with state photon_shower_not_in_main_vertex_set (all, incl. those that pass n20 via another shower)", n=int((E.photon_object_state == POP).sum())), dict(item="all of the 567 reach the shower stage", n=int(E[E.outcome == POP].A_n20mev.astype(bool).sum()))])
    T["attachment_parent_class"] = A.pclass.value_counts().rename_axis("pf_parent_class").reset_index(name="n").assign(fraction=lambda d: d.n / n)
    T["attachment_chain_structure"] = A.chain_desc.value_counts().rename_axis("chain (~ = pseudo node; shower first)").reset_index(name="n").assign(fraction=lambda d: d.n / n).head(25)
    T["attachment_parent_truth"] = pd.crosstab(A.pclass, A.parent_truth).reset_index(); T["attachment_parent_truth_total"] = A.parent_truth.value_counts().rename_axis("parent_truth").reset_index(name="n").assign(fraction=lambda d: d.n / n)
    T["attachment_pi0_sibling_truth"] = A[A.under_pi0].pi0_sibling_truth.value_counts().rename_axis("pi0_sibling_truth").reset_index(name="n")
    T["attachment_mechanism"] = A.mechanism.value_counts().rename_axis("mechanism").reset_index(name="n").assign(fraction=lambda d: d.n / n)
    # geometry / connectivity
    cd = D["cand"][K + ["cand_pos", "kine_main_vertex_id", "kine_nu_x_corr", "kine_nu_y_corr", "kine_nu_z_corr"]].rename(columns={"cand_pos": "cand"})
    G = A.merge(cd, on=K + ["cand"], how="left").merge(E[K + ["kine_particle_pool", "kine_energy_included", "kine_energy_particle", "match_cand_nu", "A_matched", "vtx_x", "vtx_y", "vtx_z", "conv_distance_cm"]], on=K)
    kc = D["kine"].rename(columns={"cand_pos": "cand", "row": "row"})[K + ["cand", "row", "kine_particle_cluster_id"]]; G = G.merge(kc, on=K + ["cand", "row"], how="left")
    G["d_shower_to_final_vertex"] = np.linalg.norm(np.c_[G.shw_x - G.kine_nu_x_corr, G.shw_y - G.kine_nu_y_corr, G.shw_z - G.kine_nu_z_corr], axis=1)
    G["main_cluster"] = (G.kine_main_vertex_id // 1000); G["same_cluster_as_main_vertex"] = G.kine_particle_cluster_id == G.main_cluster
    G["different_candidate_than_matched"] = G.A_matched.astype(bool) & (G.cand != G.match_cand_nu)
    rows = []
    for lab, g in [("all 567", G)] + [(c, d) for c, d in G.groupby("pclass")]:
        rec = dict(group=lab, n=len(g), same_cluster_as_main_vertex=float(g.same_cluster_as_main_vertex.mean()), different_candidate=float(g.different_candidate_than_matched.mean()), pool2=float((g.kine_particle_pool == 2).mean()), included3=float((g.kine_energy_included == 3).mean()))
        for f_ in ("pf_depth", "d_shower_to_final_vertex", "dist_shower_to_parent_start", "dist_shower_to_parent_end", "parent_ke", "kine_energy_particle", "photon_energy_mev"):
            m, lo, hi = q68(g[f_]); rec[f_ + "_median"] = m; rec[f_ + "_p16"] = lo; rec[f_ + "_p84"] = hi
        rows.append(rec)
    T["attachment_geometry"] = pd.DataFrame(rows)
    # hadronic dependence
    pe = proton_event_class(D); Ea = E.merge(pe, on=K); den = Ea[Ea.outcome.isin(["pass_photon_shower_in_passing_candidate", POP])].copy(); den["att_fail"] = den.outcome == POP
    den["tp_label"] = den.truth35.clip(upper=2).map({0: "truth 0p", 1: "truth 1p", 2: "truth >=2p"})
    rr = []
    for var in ("tp_label", "proton_class", "delta_label"):
        for b, g in den.groupby(var):
            f, lo, hi = cp(int(g.att_fail.sum()), len(g)); rr.append(dict(variable=var, group=str(b), n_denominator=len(g), n_failures=int(g.att_fail.sum()), failure_rate=f, lo68=lo, hi68=hi))
    for (a, b), g in den.groupby(["tp_label", "proton_class"]):
        f, lo, hi = cp(int(g.att_fail.sum()), len(g)); rr.append(dict(variable="truth topology x proton class", group=f"{a} | {b}", n_denominator=len(g), n_failures=int(g.att_fail.sum()), failure_rate=f, lo68=lo, hi68=hi))
    T["attachment_failure_rate_by_hadronic_activity"] = pd.DataFrame(rr)
    ap = A.merge(pe, on=K); T["attachment_mechanism_by_topology"] = pd.crosstab(ap.mechanism, ap.truth35.clip(upper=2).map({0: "truth 0p", 1: "truth 1p", 2: "truth >=2p"})).reset_index()
    T["attachment_parent_class_by_proton_class"] = pd.crosstab(ap.pclass, ap.proton_class).reset_index()
    return T, G


# =============================================================================================================== DL vertex provenance (V)
V3 = lambda d, p: np.c_[d[p + "_x"], d[p + "_y"], d[p + "_z"]]


def dl_coverage(D):
    """Task 5: closure of the event / candidate mapping of the DL records."""
    dl = D["dl"]; E = D["E"]; cand = D["cand"]
    prod = dl[dl["pass"] == 0]; off = dl[dl["pass"] == 1]
    ev = dl.groupby(K).size().rename("n").reset_index()
    ek = E[K + ["run", "subrun", "evt"]]; chk = dl.merge(ek, on=K)
    pc = prod.groupby(K + ["nu_index"]).size()
    nc = cand.groupby(K).size().rename("n_cand").reset_index().merge(prod.groupby(K).nu_index.nunique().rename("n_dl_cand").reset_index(), on=K, how="left")
    r = [dict(item="events requested (Phase-9 event_taxonomy)", value=len(E)), dict(item="events with >= 1 DL record", value=len(ev)), dict(item="events without any DL record", value=len(E) - len(ev)),
         dict(item="DL records (calls)", value=len(dl)), dict(item="  production calls (pass 0)", value=len(prod)), dict(item="  dual-chain OFF calls (pass 1)", value=len(off)), dict(item="  other pass codes", value=int((~dl['pass'].isin([0, 1])).sum())),
         dict(item="candidates in the Phase-9 candidate table", value=len(cand)), dict(item="candidates with a production DL call", value=len(pc)), dict(item="candidates without a production call", value=len(cand) - len(pc)),
         dict(item="candidates with more than one production call (duplicates)", value=int((pc > 1).sum())), dict(item="duplicated (event, candidate, call_index) records", value=int(dl.duplicated(K + ["nu_index", "call_index"]).sum())),
         dict(item="run / subrun / event keys of the scan match Phase 9 (records)", value=int(((chk.runNo == chk.run) & (chk.subRunNo == chk.subrun) & (chk.eventNo == chk.evt)).sum())), dict(item="  records compared", value=len(chk)),
         dict(item="events where the DL candidate count differs from the T_kine candidate count", value=int((nc.n_cand != nc.n_dl_cand).sum())), dict(item="production calls with status != 0 (network error / odd payload)", value=int((prod.status != 0).sum())),
         dict(item="production calls with accepted == 1 (DL vertex switched the main vertex)", value=int((prod.accepted == 1).sum())), dict(item="production calls not accepted (traditional vertex kept)", value=int((prod.accepted == 0).sum())),
         dict(item="  of those with the sentinel dl_xyz = (0, 0, 0)", value=int(((prod.accepted == 0) & (prod.dl_x == 0) & (prod.dl_y == 0) & (prod.dl_z == 0)).sum())), dict(item="production calls with a valid traditional vertex", value=int((prod.trad_valid == 1).sum())),
         dict(item="production calls with a valid final vertex", value=int((prod.final_valid == 1).sum())), dict(item="production calls with the signal interaction found in truth_all_*", value=int(prod.sig_found.astype(bool).sum())),
         dict(item="production calls with truth_sce_applied == 1", value=int((prod.truth_sce_applied == 1).sum()))]
    # coordinate sanity: accepted / final / truth-reco inside a generous box around the active volume
    inside = lambda d, p: ((d[p + "_x"].abs() < 260) & (d[p + "_y"].abs() < 260) & (d[p + "_z"] > -60) & (d[p + "_z"] < 560))
    r += [dict(item="accepted DL vertices inside the box |x|,|y| < 260, -60 < z < 560 cm", value=int(inside(prod[prod.accepted == 1], "dl").sum())), dict(item="  accepted DL vertices", value=int((prod.accepted == 1).sum())),
          dict(item="final vertices inside the same box", value=int(inside(prod[prod.final_valid == 1], "final").sum())), dict(item="  valid final vertices", value=int((prod.final_valid == 1).sum()))]
    # final vs kine_nu_*_corr
    kc = cand[K + ["cand_pos", "kine_nu_x_corr", "kine_nu_y_corr", "kine_nu_z_corr"]].rename(columns={"cand_pos": "nu_index"}); m = prod.merge(kc, on=K + ["nu_index"])
    dd = np.linalg.norm(V3(m, "final") - np.c_[m.kine_nu_x_corr, m.kine_nu_y_corr, m.kine_nu_z_corr], axis=1)
    r += [dict(item="production calls compared with T_kine kine_nu_*_corr", value=len(m)), dict(item="  |final - kine_nu_corr| < 0.01 cm", value=int((dd < 0.01).sum())), dict(item="  max |final - kine_nu_corr| cm", value=float(np.nanmax(dd)))]
    return pd.DataFrame(r)


def vertex_events(D, cand_rule="matched"):
    """One row per event with a DL record for the signal-matched candidate (fallback: the candidate holding the dominant photon object): V_true, V_trad, V_rerank, V_dl, V_final in the raw frame, the
    displacements decomposed along / perpendicular to the true photon direction, the vertex states and the provenance class."""
    dl = D["dl"]; E = D["E"]; prod = dl[(dl["pass"] == 0)].copy(); off = dl[dl["pass"] == 1][K + ["nu_index", "dl_x", "dl_y", "dl_z", "accepted"]].rename(columns={"dl_x": "off_x", "dl_y": "off_y", "dl_z": "off_z", "accepted": "off_accepted"})
    e = E.copy(); e["vcand"] = np.where(e.A_matched.astype(bool), e.match_cand_nu, e.dom_nu); e = e[e.vcand.notna()]
    m = e.merge(prod.rename(columns={"nu_index": "vcand"}), on=K + ["vcand"], how="left", suffixes=("", "_dl")).merge(off.rename(columns={"nu_index": "vcand"}), on=K + ["vcand"], how="left")
    recs = []
    for r in m.itertuples():
        rec = dict(file_index=r.file_index, ev=r.ev, vcand=int(r.vcand), truth35=r.truth35, delta_label=r.delta_label, conv_distance_cm=r.conv_distance_cm, photon_energy_mev=r.photon_energy_mev, have_dl=bool(r.sig_found) if isinstance(r.sig_found, (bool, np.bool_)) else False)
        if not rec["have_dl"]:
            recs.append(rec); continue
        vt = np.array([r.sig_reco_x, r.sig_reco_y, r.sig_reco_z]); u = VA.unit([r.photon_px, r.photon_py, r.photon_pz])
        conv = np.array([r.ph_end_x, r.ph_end_y, r.ph_end_z]) + (vt - np.array([r.vtx_x, r.vtx_y, r.vtx_z]))
        vtr = np.array([r.trad_x, r.trad_y, r.trad_z]) if r.trad_valid == 1 else None; vrr = np.array([r.rerank_x, r.rerank_y, r.rerank_z]) if r.rerank_valid == 1 else None
        vdl, dl_kind = VA.dl_vertex_of_call(r.accepted == 1, [r.dl_x, r.dl_y, r.dl_z], [r.trad_x, r.trad_y, r.trad_z], r.trad_valid == 1)
        vf = np.array([r.final_x, r.final_y, r.final_z]) if r.final_valid == 1 else None
        pay = list(r.payload_flat) if r.payload_flat is not None else []
        vraw = np.array(pay[:3], float) if len(pay) >= 4 else None; rec["raw_top1_score"] = float(pay[3]) if len(pay) >= 4 else np.nan
        rec.update(dl_kind=dl_kind, dl_accepted=bool(r.accepted == 1), dual_transferred=bool(r.dual_transferred == 1), two_end_veto=bool(r.two_end_veto == 1), true_x=vt[0], true_y=vt[1], true_z=vt[2], hint_valid=bool(r.hint_valid == 1))
        for nm, v in (("trad", vtr), ("rerank", vrr), ("dl", vdl), ("final", vf), ("raw", vraw)):
            if v is not None:
                rec.update({f"{nm}_{c}": float(x) for c, x in zip("xyz", v)})
        pairs = [("dl_true", vdl, vt), ("final_dl", vdl, vf), ("final_true", vt, vf), ("trad_true", vt, vtr), ("dl_trad", vtr, vdl), ("rerank_true", vt, vrr), ("final_trad", vtr, vf)]
        # displacement a->b: dl_true = V_dl - V_true etc. (from, to)
        for nm, (a, b) in {"dl_true": (vt, vdl), "final_dl": (vdl, vf), "final_true": (vt, vf), "trad_true": (vt, vtr), "dl_trad": (vtr, vdl), "rerank_true": (vt, vrr), "final_trad": (vtr, vf), "raw_true": (vt, vraw), "raw_dl": (vraw, vdl)}.items():
            if a is not None and b is not None:
                d = VA.decompose(a, b, u); rec.update({f"{nm}_mag": d["mag"], f"{nm}_par": d["parallel"], f"{nm}_perp": d["perp"]})
        rec["dl_state_pt"] = VA.vertex_state(vdl, vt, conv) if vdl is not None else "undefined"; rec["final_state_pt"] = VA.vertex_state(vf, vt, conv) if vf is not None else "undefined"
        rec["trad_state_pt"] = VA.vertex_state(vtr, vt, conv) if vtr is not None else "undefined"
        rec["prov_class_state"] = VA.provenance_class(rec["dl_state_pt"], rec["final_state_pt"], r.conv_distance_cm, have_dl=vdl is not None)
        for tol in (3.0, 5.0, 10.0):
            ds = VA.line_state(rec.get("dl_true_par", np.nan), rec.get("dl_true_perp", np.nan), tol); fs = VA.line_state(rec.get("final_true_par", np.nan), rec.get("final_true_perp", np.nan), tol)
            ts = VA.line_state(rec.get("trad_true_par", np.nan), rec.get("trad_true_perp", np.nan), tol)
            if tol == 5.0:
                rec["dl_state"], rec["final_state"], rec["trad_state"] = ds, fs, ts
                rec["prov_class"] = VA.provenance_class_line(ds, fs, r.conv_distance_cm, vdl is not None)
            else:
                rec[f"prov_class_tol{int(tol)}"] = VA.provenance_class_line(ds, fs, r.conv_distance_cm, vdl is not None)
        rec["off_to_dl_mag"] = float(np.linalg.norm(np.array([r.off_x, r.off_y, r.off_z]) - vdl)) if vdl is not None and r.off_accepted == 1 else np.nan
        recs.append(rec)
    return pd.DataFrame(recs)


TOPO = {0: "truth 0p", 1: "truth 1p", 2: "truth >=2p"}
STAGES = [("candidate", "A_candidate"), ("shower stage", "A_n20mev"), ("numu", "A_numu"), ("other", "A_other"), ("ncpi0", "A_ncpi0"), ("n_20br1", "A_n20br1"), ("final", "A_final")]


def provenance_tables(D, V):
    T = {}; E = D["E"]; V = V.copy(); V["topology"] = V.truth35.clip(upper=2).map(TOPO); H = V[V.have_dl & V.final_mag.notna() if "final_mag" in V else V.have_dl] if False else V[V.have_dl]
    pairs = [("dl_true", "|V_DL - V_true|"), ("final_dl", "|V_final - V_DL|"), ("final_true", "|V_final - V_true|"), ("trad_true", "|V_trad - V_true|"), ("dl_trad", "|V_DL - V_trad|"), ("rerank_true", "|V_rerank - V_true|"), ("raw_true", "|V_raw top-1 voxel - V_true|"), ("raw_dl", "|V_DL - V_raw top-1 voxel|")]
    rows = []
    for tp, g in [("all", H)] + [(b, d) for b, d in H.groupby("topology")]:
        for nm, lab in pairs:
            for comp, col in (("magnitude", nm + "_mag"), ("along photon (signed)", nm + "_par"), ("perpendicular", nm + "_perp")):
                if col in g:
                    m, lo, hi = q68(g[col]); rows.append(dict(topology=tp, displacement=lab, component=comp, n=int(g[col].notna().sum()), median=m, p16=lo, p84=hi, mean=float(g[col].mean())))
    T["vertex_displacements"] = pd.DataFrame(rows)
    # anchoring fractions at each stage
    ar = []
    for tp, g in [("all", H)] + [(b, d) for b, d in H.groupby("topology")]:
        for tol in (3.0, 5.0, 10.0):
            rec = dict(topology=tp, tolerance_cm=tol, n=len(g))
            for nm in ("trad_true", "raw_true", "dl_true", "final_true"):
                x = g[nm + "_mag"].dropna(); rec["anchored_" + nm.split("_")[0]] = float((x <= tol).mean()); rec["n_" + nm.split("_")[0]] = len(x)
            rec["final_moved_gt_1cm_from_dl"] = float((g.final_dl_mag > 1).mean()); rec["final_moved_gt_5cm_from_dl"] = float((g.final_dl_mag > 5).mean())
            ar.append(rec)
    T["vertex_anchoring_by_stage"] = pd.DataFrame(ar)
    # 0p along-photon displacement: where does it arise (separable events only)
    sep = H[H.conv_distance_cm >= VA.NOT_SEPARABLE_CM]; rr = []
    for tp, g in [("all", sep)] + [(b, d) for b, d in sep.groupby("topology")]:
        rr.append(dict(topology=tp, n=len(g), median_dl_true_par=q68(g.dl_true_par)[0], median_final_dl_par=q68(g.final_dl_par)[0], median_final_true_par=q68(g.final_true_par)[0],
                       frac_dl_displaced_gt5cm_along=float((g.dl_true_par > 5).mean()), frac_final_displaced_gt5cm_along=float((g.final_true_par > 5).mean()), frac_final_moves_gt5cm_along_after_dl=float((g.final_dl_par > 5).mean()), frac_final_moves_gt5cm_against_after_dl=float((g.final_dl_par < -5).mean()),
                       median_trad_true_par=q68(g.trad_true_par)[0], median_dl_trad_par=q68(g.dl_trad_par)[0], frac_dl_accepted=float(g.dl_accepted.mean()), frac_dual_transferred=float(g.dual_transferred.mean())))
    T["photon_line_displacement_where"] = pd.DataFrame(rr)
    # provenance classes by topology
    pc = pd.crosstab(H.prov_class, H.topology); pc["all"] = pc.sum(axis=1); T["provenance_classes_by_topology"] = pc.reset_index()
    T["provenance_state_crosstab"] = pd.crosstab([H.dl_state], [H.final_state]).reset_index(); T["provenance_classes_state_based_sensitivity"] = pd.crosstab(H.prov_class_state, H.topology).reset_index(); T["provenance_trad_dl_final_states"] = pd.crosstab([H.trad_state, H.dl_state], H.final_state).reset_index()
    for tol in (3, 10):
        T[f"provenance_classes_tol{tol}"] = pd.crosstab(H[f"prov_class_tol{tol}"], H.topology).reset_index()
    T["dl_accept_and_snap"] = pd.DataFrame([dict(topology=tp, n=len(g), raw_top1_score_median=float(g.raw_top1_score.median()), frac_raw_top1_score_lt_0p02=float((g.raw_top1_score < 0.02).mean()), frac_raw_top1_score_gt_0p1=float((g.raw_top1_score > 0.1).mean()), dl_differs_from_trad_gt1cm=float((g.dl_trad_mag > 1).mean()), dl_differs_from_trad_gt5cm=float((g.dl_trad_mag > 5).mean()), dl_moves_toward_true_gt5cm=float((g.trad_true_mag - g.dl_true_mag > 5).mean()), dl_moves_away_from_true_gt5cm=float((g.dl_true_mag - g.trad_true_mag > 5).mean()), dl_accepted=float(g.dl_accepted.mean()), dual_transferred=float(g.dual_transferred.mean()), two_end_veto=float(g.two_end_veto.mean()), traditional_kept=float((g.dl_kind == "traditional_kept").mean()), hint_valid=float(g.hint_valid.mean())) for tp, g in [("all", H)] + list(H.groupby("topology"))])
    # Task 8: proton anchoring classes
    pe = proton_event_class(D); P = H.merge(pe, on=K, how="left"); rows = []
    for (tp, pcl), g in [(("all", "all"), P)] + [((a, "all"), d) for a, d in P.groupby("topology")] + [((a, b), d) for (a, b), d in P.groupby(["topology", "proton_class"])] + [(("all", b), d) for b, d in P.groupby("proton_class")]:
        if len(g) < 5:
            continue
        rows.append(dict(topology=tp, proton_class=pcl, n=len(g), anchored5_trad=float((g.trad_true_mag <= 5).mean()), anchored5_dl=float((g.dl_true_mag <= 5).mean()), anchored5_final=float((g.final_true_mag <= 5).mean()), dl_true_median=q68(g.dl_true_mag)[0], final_true_median=q68(g.final_true_mag)[0],
                         final_dl_median=q68(g.final_dl_mag)[0], final_dl_gt5=float((g.final_dl_mag > 5).mean()), dl_true_par_median=q68(g.dl_true_par)[0], dl_accepted=float(g.dl_accepted.mean())))
    T["proton_anchoring_by_stage"] = pd.DataFrame(rows)
    # Task 9: photon reconstruction state
    pt = D["pe"][K + ["pid_class", "dom_type"]]; Q = H.merge(pt, on=K, how="left").merge(E[K + ["outcome"]], on=K)
    Q["state"] = np.where(Q.outcome == POP, "shower not in main-vertex set (Phase 9)", Q.pid_class)
    rows = []
    for st, g in Q.groupby("state"):
        if len(g) < 5:
            continue
        rows.append(dict(photon_state=st, n=len(g), dl_true_median=q68(g.dl_true_mag)[0], final_dl_median=q68(g.final_dl_mag)[0], final_true_median=q68(g.final_true_mag)[0], dl_true_par_median=q68(g.dl_true_par)[0], final_dl_par_median=q68(g.final_dl_par)[0],
                         anchored5_dl=float((g.dl_true_mag <= 5).mean()), anchored5_final=float((g.final_true_mag <= 5).mean()), final_dl_gt5=float((g.final_dl_mag > 5).mean()), frac_dl_displaced_gt5cm_along=float((g.dl_true_par > 5).mean())))
    T["vertex_by_photon_state"] = pd.DataFrame(rows)
    # Task 17: stage survival by provenance class
    rr = []
    for cl, g in H.merge(E[K + [c for _, c in STAGES]], on=K).groupby("prov_class"):
        prev = len(g); rr.append(dict(prov_class=cl, stage="all events", n=prev, step_survival=np.nan, cumulative=1.0))
        for nm, c in STAGES:
            n_ = int(g[c].astype(bool).sum()); rr.append(dict(prov_class=cl, stage=nm, n=n_, step_survival=n_ / prev if prev else np.nan, cumulative=n_ / len(g))); prev = n_
    T["stage_survival_by_vertex_class"] = pd.DataFrame(rr)
    # Task 18: the 0p / 1p other-stage difference
    S = H.merge(E[K + [c for _, c in STAGES]], on=K); S = S[S.A_numu.astype(bool)]            # events reaching `other`
    rr = []
    for tp, g in [("all", S)] + [(b, d) for b, d in S.groupby("topology")]:
        k = int(g.A_other.astype(bool).sum()); f, lo, hi = cp(k, len(g)); rr.append(dict(group=tp, split="all reaching other", n=len(g), other_pass=k, other_survival=f, lo68=lo, hi68=hi))
    for (tp, a), g in S.groupby(["topology", S.final_true_mag <= 5]):
        k = int(g.A_other.astype(bool).sum()); f, lo, hi = cp(k, len(g)); rr.append(dict(group=tp, split="final vertex anchored (<=5 cm)" if a else "final vertex not anchored", n=len(g), other_pass=k, other_survival=f, lo68=lo, hi68=hi))
    for (tp, a), g in S.groupby(["topology", S.dl_true_mag <= 5]):
        k = int(g.A_other.astype(bool).sum()); f, lo, hi = cp(k, len(g)); rr.append(dict(group=tp, split="DL vertex anchored (<=5 cm)" if a else "DL vertex not anchored", n=len(g), other_pass=k, other_survival=f, lo68=lo, hi68=hi))
    oso = pd.DataFrame(rr); T["other_stage_vs_vertex_anchoring"] = oso
    sd = []
    for stage_lab, col in (("DL vertex", "dl_true_mag"), ("final vertex", "final_true_mag")):
        g0 = S[S.topology == "truth 0p"]; g1 = S[S.topology == "truth 1p"]
        f = lambda g: (g[col] <= 5).mean(); sv = lambda g, m: g[m].astype(bool).mean() if False else g.A_other.astype(bool)[(g[col] <= 5) == m].mean()
        a0, a1 = f(g0), f(g1); s0a, s0n, s1a, s1n = sv(g0, True), sv(g0, False), sv(g1, True), sv(g1, False)
        sd.append(dict(vertex=stage_lab, anchored_fraction_0p=a0, anchored_fraction_1p=a1, other_survival_0p=g0.A_other.astype(bool).mean(), other_survival_1p=g1.A_other.astype(bool).mean(), survival_0p_anchored=s0a, survival_0p_not_anchored=s0n, survival_1p_anchored=s1a, survival_1p_not_anchored=s1n,
                       expected_0p_with_1p_anchored_fraction=a1 * s0a + (1 - a1) * s0n, expected_1p_with_0p_anchored_fraction=a0 * s1a + (1 - a0) * s1n,
                       gap_1p_minus_0p=g1.A_other.astype(bool).mean() - g0.A_other.astype(bool).mean()))
    sd = pd.DataFrame(sd); sd["gap_explained_by_anchored_fraction_using_0p_rates"] = (sd.expected_0p_with_1p_anchored_fraction - sd.other_survival_0p) / sd.gap_1p_minus_0p; sd["gap_explained_by_anchored_fraction_using_1p_rates"] = (sd.other_survival_1p - sd.expected_1p_with_0p_anchored_fraction) / sd.gap_1p_minus_0p
    T["other_stage_gap_standardisation"] = sd
    return T, H


def attach_vs_dl(D, A, H):
    """Task 15: distance of the signal shower start to the true / DL / final vertex for the 567 events."""
    G = A.merge(H[K + ["true_x", "true_y", "true_z", "dl_x", "dl_y", "dl_z", "final_x", "final_y", "final_z", "dl_state", "final_state", "prov_class", "dl_true_mag", "final_true_mag", "final_dl_mag", "have_dl", "dl_accepted", "trad_x", "trad_y", "trad_z"]], on=K, how="left")
    s = np.c_[G.shw_x, G.shw_y, G.shw_z]
    for nm in ("true", "dl", "final", "trad"):
        G["d_shower_to_" + nm] = np.linalg.norm(s - np.c_[G[nm + "_x"], G[nm + "_y"], G[nm + "_z"]], axis=1)
    G["closest"] = G[["d_shower_to_true", "d_shower_to_dl", "d_shower_to_final"]].idxmin(axis=1).str.replace("d_shower_to_", "")
    return G


def attach_vs_dl_tables(G):
    T = {}; ok = G[G.have_dl.fillna(False).astype(bool)]
    rows = []
    for lab, g in [("all 567", ok)] + [(c, d) for c, d in ok.groupby("pclass")] + [(t, d) for t, d in ok.groupby(ok.truth35.clip(upper=2).map(TOPO))]:
        rec = dict(group=lab, n=len(g))
        for nm in ("true", "trad", "dl", "final"):
            m, lo, hi = q68(g["d_shower_to_" + nm]); rec[f"d_shower_to_{nm}_median"] = m; rec[f"d_shower_to_{nm}_p16"] = lo; rec[f"d_shower_to_{nm}_p84"] = hi
        rec["frac_dl_within_5cm_of_true_vertex"] = float((g.dl_true_mag <= 5).mean()); rec["frac_final_within_5cm_of_true_vertex"] = float((g.final_true_mag <= 5).mean()); rec["median_final_minus_dl"] = float(g.final_dl_mag.median())
        rec["frac_shower_closer_to_final_than_to_true"] = float((g.d_shower_to_final < g.d_shower_to_true).mean()); rec["frac_shower_within_5cm_of_final"] = float((g.d_shower_to_final <= 5).mean()); rec["frac_shower_within_5cm_of_dl"] = float((g.d_shower_to_dl <= 5).mean())
        rows.append(rec)
    T["attachment_shower_distance_to_vertices"] = pd.DataFrame(rows)
    T["attachment_dl_vs_final_class"] = pd.crosstab(ok.prov_class, ok.truth35.clip(upper=2).map(TOPO)).reset_index()
    return T


def natural_check():
    """Task 19: headline DL / final vertex distances for the natural NC-Delta CV candidates (the 105 files of the 117-event rehearsal region; magnitudes only: the natural signal table has no photon direction)."""
    x = RAW / "dl_calls_natural.parquet"
    if not x.exists():
        return None
    dl = pd.read_parquet(x); prod = dl[(dl["pass"] == 0) & dl.sig_found.astype(bool) & (dl.final_valid == 1)].copy()
    sn = pd.read_parquet(SPD / "natural_ncdelta_bnb_cv" / "signal_neutrinos.parquet").drop_duplicates(["file_index", "ev"])[["file_index", "ev", "n_p35"]]
    prod["final_true"] = np.linalg.norm(np.c_[prod.final_x - prod.sig_reco_x, prod.final_y - prod.sig_reco_y, prod.final_z - prod.sig_reco_z], axis=1)
    prod["dl_vx"] = np.where(prod.accepted == 1, prod.dl_x, prod.trad_x); prod["dl_vy"] = np.where(prod.accepted == 1, prod.dl_y, prod.trad_y); prod["dl_vz"] = np.where(prod.accepted == 1, prod.dl_z, prod.trad_z)
    prod["dl_true"] = np.linalg.norm(np.c_[prod.dl_vx - prod.sig_reco_x, prod.dl_vy - prod.sig_reco_y, prod.dl_vz - prod.sig_reco_z], axis=1)
    prod["final_dl"] = np.linalg.norm(np.c_[prod.final_x - prod.dl_vx, prod.final_y - prod.dl_vy, prod.final_z - prod.dl_vz], axis=1)
    best = prod.sort_values("final_true").drop_duplicates(K).merge(sn, on=K, how="left"); best["topology"] = best.n_p35.fillna(-1).clip(upper=2).map({0: "truth 0p", 1: "truth 1p", 2: "truth >=2p"}).fillna("unknown")
    rows = []
    for tp, g in [("all", best)] + [(b, d) for b, d in best.groupby("topology")]:
        rows.append(dict(topology=tp, n_events=len(g), dl_true_median=q68(g.dl_true)[0], final_true_median=q68(g.final_true)[0], final_dl_median=q68(g.final_dl)[0], dl_true_p84=q68(g.dl_true)[2], final_dl_p84=q68(g.final_dl)[2],
                         frac_final_within_5cm_of_true=float((g.final_true <= 5).mean()), frac_dl_within_5cm_of_true=float((g.dl_true <= 5).mean()), frac_final_moved_gt_5cm_from_dl=float((g.final_dl > 5).mean())))
    return pd.DataFrame(rows), dict(records=len(dl), production_calls=int((dl["pass"] == 0).sum()), events=int(dl.groupby(K).ngroups))


# =============================================================================================================== figures
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sbnd_single_photon import plotstyle as PS
PROV = "official Gen2 NC-Delta | Wire-Cell fg1 reconstruction as produced | raw reconstruction frame (truth shifted by the TrueFwd SCE map) | descriptive audit, no cut changed"
CCOL = dict(zip(VA.PROVENANCE_CLASSES, ["#D55E00", "#CC79A7", "#009E73", "#E69F00", "#56B4E9", "#bbbbbb", "#444444"]))


def save(fig, name):
    PS.annotate(fig, PROV, extra=PS.PRELIM); fig.savefig(PLT / name, bbox_inches="tight"); plt.close(fig)


def figures(H, V, T, A, G, S):
    H = H.copy(); H["topology"] = H.truth35.clip(upper=2).map(TOPO)
    fig, ax = PS.figure(1, 3, size=(14, 3.9)); bins = np.linspace(-60, 100, 65)
    for j, tp in enumerate(("truth 0p", "truth 1p", "truth >=2p")):
        g = H[(H.topology == tp) & (H.conv_distance_cm >= 5)]
        for nm, lab, c in (("dl_true_par", "V_DL - V_true", "#0072B2"), ("final_dl_par", "V_final - V_DL", "#D55E00"), ("final_true_par", "V_final - V_true", "#000000")):
            ax[0][j].hist(g[nm].clip(-59, 99), bins=bins, histtype="step", lw=1.6, color=c, label=f"{lab} (median {g[nm].median():.1f} cm)")
        ax[0][j].set_yscale("log"); ax[0][j].set_xlabel("displacement along the true photon direction [cm]"); ax[0][j].set_title(f"{tp} (n = {len(g)}, conversion >= 5 cm)", fontsize=9); ax[0][j].legend(fontsize=6)
    ax[0][0].set_ylabel("events"); fig.tight_layout(); save(fig, "fig1_longitudinal_displacement_true_dl_final.png")
    pc = T["provenance_classes_by_topology"].set_index("prov_class"); fig, ax = PS.figure(1, 1, size=(8.5, 4.2)); x = np.arange(3); bottom = np.zeros(3)
    for c in VA.PROVENANCE_CLASSES:
        if c in pc.index:
            v = np.array([pc.loc[c, t] / pc[t].sum() for t in TOPO.values()]); ax[0][0].bar(x, v, 0.6, bottom=bottom, color=CCOL[c], edgecolor="white", label=c); bottom += v
    ax[0][0].set_xticks(x); ax[0][0].set_xticklabels([f"{t}\n(n={int(pc[t].sum())})" for t in TOPO.values()]); ax[0][0].set_ylabel("fraction of events"); ax[0][0].legend(fontsize=6, loc="upper left", bbox_to_anchor=(1, 1)); ax[0][0].set_title("vertex provenance class (5 cm tolerance, line-based)", fontsize=9)
    fig.tight_layout(); save(fig, "fig2_vertex_provenance_by_topology.png")
    pa = T["proton_anchoring_by_stage"]; pa = pa[(pa.topology == "all") & (pa.proton_class != "all")]; fig, ax = PS.figure(1, 1, size=(9.5, 4.2)); x = np.arange(len(pa)); w = 0.26
    for k, (c, lab, col) in enumerate((("anchored5_trad", "traditional vertex", "#999999"), ("anchored5_dl", "DL-stage vertex", "#0072B2"), ("anchored5_final", "final vertex", "#D55E00"))):
        ax[0][0].bar(x + (k - 1) * w, pa[c], w, label=lab, color=col)
    ax[0][0].set_xticks(x); ax[0][0].set_xticklabels([f"{c}\n(n={n})" for c, n in zip(pa.proton_class, pa.n)], fontsize=7); ax[0][0].set_ylabel("fraction within 5 cm of the true vertex"); ax[0][0].legend(fontsize=7); ax[0][0].set_title("vertex anchoring by reconstructed-proton state", fontsize=9)
    fig.tight_layout(); save(fig, "fig3_anchoring_by_proton_state.png")
    pcl = T["attachment_parent_class"]; fig, ax = PS.figure(1, 2, size=(13, 4.2)); a = ax[0][0]; d = pcl.iloc[::-1]; a.barh(d.pf_parent_class, d.n, color="#8c564b"); a.set_xlabel("events (567)"); a.set_title("PF ancestry of the signal shower", fontsize=9)
    for y_, (n_, f_) in enumerate(zip(d.n, d.fraction)):
        a.text(n_, y_, f"  {n_} ({f_:.0%})", va="center", fontsize=7)
    a.set_xlim(0, d.n.max() * 1.3); b = ax[0][1]; pt = pd.crosstab(A.pclass, A.parent_truth); pt = pt.loc[[c for c in VA.PARENT_CLASSES if c in pt.index]]; order = list(pt.sum().sort_values(ascending=False).index); bottom = np.zeros(len(pt)); cm = plt.get_cmap("tab10")
    for k, c in enumerate(order):
        b.barh(np.arange(len(pt)), pt[c].values, left=bottom, color=cm(k), label=c, edgecolor="white", linewidth=0.4); bottom += pt[c].values
    b.set_yticks(np.arange(len(pt))); b.set_yticklabels([c[:34] for c in pt.index], fontsize=7); b.invert_yaxis(); b.legend(fontsize=6, loc="lower right"); b.set_xlabel("events"); b.set_title("truth of the nearest real ancestor (source-ranked T_match)", fontsize=9)
    fig.tight_layout(); save(fig, "fig4_5_shower_parent_taxonomy_and_truth.png")
    ok = G[G.have_dl.fillna(False).astype(bool)]; fig, ax = PS.figure(1, 1, size=(8, 4.3)); bins = np.logspace(-0.5, 2.3, 40)
    for nm, lab, c in (("true", "true vertex", "#009E73"), ("dl", "DL-stage vertex", "#0072B2"), ("final", "final vertex", "#D55E00")):
        ax[0][0].hist(ok["d_shower_to_" + nm].clip(lower=bins[0]), bins=bins, histtype="step", lw=1.7, color=c, label=f"{lab} (median {ok['d_shower_to_' + nm].median():.1f} cm)")
    ax[0][0].set_xscale("log"); ax[0][0].set_xlabel("distance of the signal-shower start to the vertex [cm]"); ax[0][0].set_ylabel("events"); ax[0][0].legend(fontsize=7); ax[0][0].set_title("567 events: the shower outside the main-vertex set", fontsize=9)
    fig.tight_layout(); save(fig, "fig6_shower_start_distance_to_vertices.png")
    ps = T["vertex_by_photon_state"].sort_values("dl_true_median"); fig, ax = PS.figure(1, 1, size=(9.5, 4.4)); y = np.arange(len(ps)); h = 0.38
    ax[0][0].barh(y - h / 2, ps.dl_true_median, h, color="#0072B2", label="median |V_DL - V_true|"); ax[0][0].barh(y + h / 2, ps.final_dl_median, h, color="#D55E00", label="median |V_final - V_DL|")
    ax[0][0].set_yticks(y); ax[0][0].set_yticklabels([f"{s[:46]} (n={n})" for s, n in zip(ps.photon_state, ps.n)], fontsize=7); ax[0][0].set_xlabel("cm"); ax[0][0].legend(fontsize=7); ax[0][0].set_title("vertex movement by photon reconstruction state", fontsize=9)
    fig.tight_layout(); save(fig, "fig7_dl_vs_final_by_photon_state.png")
    sv = T["stage_survival_by_vertex_class"]; sv = sv[sv.stage != "all events"]; cls = [c for c in VA.PROVENANCE_CLASSES if c in set(sv.prov_class) and c[0] in "ABCD"]; fig, ax = PS.figure(1, 1, size=(10, 4.2)); x = np.arange(len(STAGES)); w = 0.8 / max(len(cls), 1)
    for k, c in enumerate(cls):
        g = sv[sv.prov_class == c].set_index("stage").reindex([s for s, _ in STAGES]); ax[0][0].bar(x + (k - (len(cls) - 1) / 2) * w, g.cumulative, w, color=CCOL[c], label=f"{c} (n={int(sv[(sv.prov_class == c)].n.max())})")
    ax[0][0].set_xticks(x); ax[0][0].set_xticklabels([s for s, _ in STAGES]); ax[0][0].set_ylabel("cumulative fraction of the class"); ax[0][0].legend(fontsize=6); ax[0][0].set_title("frozen-stage survival by vertex-provenance class", fontsize=9)
    fig.tight_layout(); save(fig, "fig8_stage_survival_by_vertex_class.png")


def git_head():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    except Exception:
        return "unknown"


def main():
    OUT.mkdir(parents=True, exist_ok=True); TAB.mkdir(parents=True, exist_ok=True); PLT.mkdir(parents=True, exist_ok=True)
    D = load(); cov = dl_coverage(D); V = vertex_events(D); T, H = provenance_tables(D, V); T["dl_coverage"] = cov
    A = attachment_events(D); AT, G0 = attachment_tables(D, A); T.update(AT); G = attach_vs_dl(D, A, H); T.update(attach_vs_dl_tables(G))
    nat = natural_check()
    if nat is not None:
        T["natural_cv_check"], meta_nat = nat; T["natural_cv_coverage"] = pd.DataFrame([meta_nat])
    # stage survival of the 567 by provenance class is not needed (all fail the shower stage); keep the provenance of the 567
    T["attachment_provenance_class"] = pd.crosstab(G.prov_class.fillna("no DL record"), G.truth35.clip(upper=2).map(TOPO)).reset_index()
    for k, v in T.items():
        v.to_csv(TAB / f"{k}.csv", index=False)
    figures(H, V, T, A, G, None)
    dlp = D["dl"]; pq(dlp.drop(columns=["payload_flat"]).assign(payload_top1_score=[x[3] if len(x) >= 4 else np.nan for x in dlp.payload_flat]), OUT / "dl_vertex_candidates.parquet"); pq(V, OUT / "vertex_provenance_events.parquet")
    pq(G, OUT / "shower_attachment_events.parquet")
    pf = D["pf"]; pf = pf.merge(A[K + ["cand", "real_parent_ki"]].rename(columns={"cand": "nu_index"}), on=K + ["nu_index"])
    pq(A[K + ["cand", "row", "truth35", "pclass", "under_pi0", "real_parent_pdg", "real_parent_ki", "parent_truth", "pi0_sibling_truth", "mechanism", "chain_desc", "parent_ke", "dist_shower_to_parent_start", "dist_shower_to_parent_end"]], OUT / "shower_parent_objects.parquet")
    T["stage_survival_by_vertex_class"].to_csv(OUT / "stage_survival_by_vertex_class.csv", index=False)
    meta = dict(phase=16, git_commit_at_run=git_head(), official_manifest_sha256=sha(REPO / "manifests" / "official_gen2_ncdelta_wc.tsv.gz"), source_pin="4b6853d4", phase9_taxonomy_sha256=sha(P9 / "event_taxonomy.parquet"), phase10_proton_association_sha256=sha(P10 / "row_matches.parquet"),
                phase15_pid_sha256=sha(P15 / "proton_pid_events.parquet"), phase15_photon_pid_sha256=sha(P15 / "photon_pid_events.parquet"), phase14_fragment_sha256=sha(P14 / "fragmentation_objects.parquet"), dl_calls_sha256=sha(RAW / "dl_calls.parquet"), dl_manifest_sha256=sha(RAW / "dl_manifest.parquet"),
                dl_scan_branches="T_dlvtx_call: see scripts/dl_vertex_scan.py (SCALARS + VECTORS); T_dlvtx_cloud NOT read", frame="raw reconstruction frame; truth shifted by the TrueFwd SCE map (truth_all_reco_*)", anchor_tolerance_cm=VA.ANCHOR_TOL_CM,
                vertex_for_event="signal-matched candidate (Phase 9 match_cand_nu), fallback the candidate holding the dominant photon object")
    (OUT / "metadata.json").write_text(json.dumps(meta, indent=1))
    summ = dict(n_events=len(V), n_have_dl=int(V.have_dl.sum()), n_attachment=len(A), dl_records=len(dlp))
    (TAB / "summary.json").write_text(json.dumps(summ, indent=1)); print("done", summ, flush=True)
    return V, H, A, G, T


if __name__ == "__main__":
    main()
