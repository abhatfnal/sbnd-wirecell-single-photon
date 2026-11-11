#!/usr/bin/env python
"""Phase 15: why is a TRUE signal photon (roadmap S) or a TRUE signal proton (roadmap X) given a muon / pion / proton / electron / merged reconstructed type?  CHARACTERISATION ONLY: no selection, threshold,
proton-threshold, FV, PID or reconstructed-type change.

    source env/setup_eaf.sh
    python scripts/particle_pid_audit.py          # reads the Phase 9 / 10 / 12 / 14 tables (+ the Phase-15 T_segment extra scan if present); no merged-CAF scan

Truth association: the source-ranked ``T_match`` level-1 partner of every reconstructed row (Phase 10 ``row_matches``; point IoU, then charge IoU, then object index).  Outputs: ``$SP_DATA/particle_pid_audit/
official_ncdelta/`` (parquet, manual event lists, metadata), ``tables/particle_pid_audit/`` and ``plots/particle_pid_audit/`` (small, committed).
"""
from __future__ import annotations
import hashlib, json, os, subprocess, sys, warnings
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from sbnd_single_photon import pid_audit as PI

SPD = Path(os.environ["SP_DATA"]); OUT = SPD / "particle_pid_audit" / "official_ncdelta"; RAW = OUT / "raw"
P9 = SPD / "shower_vertex_audit" / "official_ncdelta"; P10 = SPD / "proton_truth_association" / "official_ncdelta"; P12 = SPD / "remaining_stage_audit" / "official_ncdelta"; P14 = SPD / "pi0_pair_fragmentation_audit" / "official_ncdelta"
TAB = REPO / "tables" / "particle_pid_audit"; PLT = REPO / "plots" / "particle_pid_audit"
K = ["file_index", "ev"]; KR = K + ["cand", "row"]
E_BINS = [0, 100, 200, 300, 500, 1000, np.inf]; E_LAB = ["<100", "100-200", "200-300", "300-500", "500-1000", ">1000"]
KE_LAB = ["0-35", "35-50", "50-100", "100-200", "200-300", "300-500", ">500"]


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
    """Observed fraction with a Wilson 68 % interval."""
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    f = k / n; den = 1 + 1 / n; c = (f + 1 / (2 * n)) / den; h = np.sqrt(f * (1 - f) / n + 1 / (4 * n * n)) / den
    return f, c - h, c + h


def q68(s):
    s = pd.Series(s).dropna()
    return (float(s.quantile(0.5)), float(s.quantile(0.16)), float(s.quantile(0.84))) if len(s) else (np.nan,) * 3


# =============================================================================================================== load / common object table
def load():
    D = {}
    D["E"] = pd.read_parquet(P9 / "event_taxonomy.parquet"); D["V"] = pd.read_parquet(P9 / "vertex_geometry.parquet")
    D["rm"] = pd.read_parquet(P10 / "row_matches.parquet"); D["tp"] = pd.read_parquet(P10 / "truth_protons.parquet"); D["ps"] = pd.read_parquet(P10 / "truth_proton_states.parquet")
    for n in ("seg", "kine", "pf", "cand"):
        D[n] = pd.read_parquet(P9 / "raw" / f"{n}.parquet")
    D["pieces"] = pd.read_parquet(P14 / "fragmentation_objects.parquet"); D["fe"] = pd.read_parquet(P14 / "fragmentation_events.parquet"); D["numu"] = pd.read_parquet(P12 / "numu_stage.parquet")
    x = RAW / "seg_extra.parquet"; D["seg_extra"] = pd.read_parquet(x) if x.exists() else None
    for n, d in D.items():
        if d is not None and "file_index" in d:
            d[K] = d[K].astype(int)
    return D


def common_objects(D):
    """One row per reconstructed T_kine row of every candidate (83,097) with the key segment's persisted PID inputs, the truth partner and the signal-photon / signal-proton flags."""
    rm = D["rm"].copy(); kn = D["kine"].rename(columns={"cand_pos": "cand"})[KR + ["kine_particle_nseg"]]
    seg = D["seg"].copy(); seg["nu_index"] = seg.nu_index.astype(int)
    tot = seg[seg.kine_index >= 0].groupby(K + ["nu_index", "kine_index"]).agg(row_total_length_cm=("length_cm", "sum"), row_n_segments=("segment_id", "size"), row_n_flag_shower=("flag_shower", "sum")).reset_index().rename(columns={"nu_index": "cand", "kine_index": "row"})
    ks = seg.rename(columns={"nu_index": "cand", "segment_id": "kine_particle_id", "pdg": "seg_pdg", "flag_shower": "seg_flag_shower", "length_cm": "seg_length_cm", "ke_mev": "seg_ke_mev", "kine_index": "seg_kine_index"})[
        K + ["cand", "kine_particle_id", "seg_pdg", "seg_flag_shower", "seg_length_cm", "seg_ke_mev", "start_vertex_id", "end_vertex_id", "cluster_id", "shower_id"]]
    o = rm.merge(kn, on=KR, how="left").merge(ks, on=K + ["cand", "kine_particle_id"], how="left").merge(tot, on=KR, how="left")
    # vertex degrees within the candidate (the source's start_n / end_n = boost::degree of the segment's vertices in the final graph)
    ends = pd.concat([seg[K + ["nu_index", "start_vertex_id"]].rename(columns={"start_vertex_id": "v"}), seg[K + ["nu_index", "end_vertex_id"]].rename(columns={"end_vertex_id": "v"})])
    deg = ends.groupby(K + ["nu_index", "v"]).size().rename("deg").reset_index().rename(columns={"nu_index": "cand"})
    for side in ("start", "end"):
        o = o.merge(deg.rename(columns={"v": side + "_vertex_id", "deg": side + "_degree"}), on=K + ["cand", side + "_vertex_id"], how="left")
    cd = D["cand"].rename(columns={"cand_pos": "cand"})[K + ["cand", "kine_main_vertex_id"]]
    o = o.merge(cd, on=K + ["cand"], how="left")
    o["at_main_vertex"] = (o.start_vertex_id == o.kine_main_vertex_id) | (o.end_vertex_id == o.kine_main_vertex_id)
    sc = seg.merge(cd.rename(columns={"cand": "nu_index"}), on=K + ["nu_index"]); sc = sc[((sc.start_vertex_id == sc.kine_main_vertex_id) | (sc.end_vertex_id == sc.kine_main_vertex_id)) & (sc.flag_shower == 0) & (sc.pdg == 13)]
    mu_main = sc.groupby(K + ["nu_index"]).length_cm.agg(mu_at_main_n="size", mu_at_main_maxlen="max").reset_index().rename(columns={"nu_index": "cand"})
    o = o.merge(mu_main, on=K + ["cand"], how="left"); o["mu_at_main_n"] = o.mu_at_main_n.fillna(0).astype(int)
    o["has_mu_sibling_at_main"] = o.at_main_vertex & (o.mu_at_main_n - (o.seg_pdg == 13).astype(int) > 0)
    o["longer_mu_sibling_at_main"] = o.at_main_vertex & (o.mu_at_main_maxlen >= o.seg_length_cm) & ~((o.seg_pdg == 13) & (o.mu_at_main_n == 1))
    o["n_free_ends"] = (o.start_degree == 1).astype(int) + (o.end_degree == 1).astype(int)
    pfn = D["pf"].copy(); pfn["nu_index"] = pfn.nu_index.astype(int)
    pfn = pfn[pfn.kine_index >= 0].sort_values(K + ["nu_index", "kine_index", "depth"]).drop_duplicates(K + ["nu_index", "kine_index"]).rename(columns={"nu_index": "cand", "kine_index": "row"})[K + ["cand", "row", "depth", "start_x", "start_y", "start_z", "is_pseudo"]]
    o = o.merge(pfn.rename(columns={"depth": "pf_depth", "start_x": "pf_start_x", "start_y": "pf_start_y", "start_z": "pf_start_z", "is_pseudo": "pf_is_pseudo"}), on=KR, how="left")
    if D["seg_extra"] is not None:
        se = D["seg_extra"].rename(columns={"nu_index": "cand", "segment_id": "kine_particle_id", "dirsign": "seg_dirsign", "n_fit": "seg_n_fit"})
        o = o.merge(se[K + ["cand", "kine_particle_id", "seg_dirsign", "seg_n_fit"]], on=K + ["cand", "kine_particle_id"], how="left")
    else:
        o["seg_dirsign"] = np.nan; o["seg_n_fit"] = np.nan
    o["type_class"] = [PI.reco_type_class(t, s == 1) if t != 0 else "no row" for t, s in zip(o.kine_particle_type, o.kine_particle_is_shower)]
    ph = D["E"][K + ["photon_trackid", "signal_nu_idx"]]; o = o.merge(ph, on=K, how="left")
    o["is_signal_photon_row"] = (o.p1_tid == o.photon_trackid) & (o.p1_t_pdg == 22)
    tps = D["tp"][D["tp"].is_signal & D["tp"].primary][K + ["trackid", "ke"]].rename(columns={"trackid": "p1_tid", "ke": "proton_true_ke"})
    o = o.merge(tps, on=K + ["p1_tid"], how="left"); o["is_signal_primary_proton_row"] = o.proton_true_ke.notna() & (o.p1_t_pdg == 2212)
    return o


# =============================================================================================================== photons
def photon_events(D, obj):
    """One row per signal photon (11,331 events): Phase-9 state / outcome (unchanged), dominant object type and persisted PID inputs, truth geometry, and the PID population (A-J)."""
    V = D["V"][K + ["d_vertex", "d_conv", "prox", "shw_start_to_reco_vtx", "shw_start_to_true_conv", "parallel", "perp", "anchored5", "attached_tagger"]]
    E = D["E"].merge(V, on=K, how="left")
    dom = obj.rename(columns={"cand": "dom_nu", "row": "dom_row"})
    keep = K + ["dom_nu", "dom_row", "type_class", "seg_length_cm", "row_total_length_cm", "row_n_segments", "kine_particle_nseg", "seg_n_fit", "seg_dirsign", "seg_flag_shower", "start_degree", "end_degree", "n_free_ends", "at_main_vertex", "has_mu_sibling_at_main", "longer_mu_sibling_at_main", "pf_depth", "ke", "kine_particle_cluster_id"]
    E = E.merge(dom[keep].rename(columns={"type_class": "dom_type", "ke": "dom_ke_row"}), on=K + ["dom_nu", "dom_row"], how="left")
    E["dom_type"] = E.dom_type.fillna("no row")
    E["pid_class"] = [PI.photon_pid_class(s, o, t) for s, o, t in zip(E.photon_object_state, E.outcome, E.dom_type)]
    E["e_bin"] = pd.cut(E.photon_energy_mev, E_BINS, labels=E_LAB, right=False)
    E["conv_bin"] = pd.cut(E.conv_distance_cm, [0, 2, 5, 10, 20, 40, 1e9], labels=["<2", "2-5", "5-10", "10-20", "20-40", ">40"], right=False)
    E["cos_bin"] = pd.cut(E.cos_theta_beam, [-1.01, -0.5, 0, 0.5, 0.8, 1.01], labels=["<-0.5", "-0.5-0", "0-0.5", "0.5-0.8", ">0.8"])
    pts = np.c_[E.vtx_x, E.vtx_y, E.vtx_z]; box = np.array([[-200, 200], [-200, 200], [0, 500]])
    E["vtx_face_cm"] = np.minimum((pts - box[:, 0]).min(axis=1), (box[:, 1] - pts).min(axis=1))
    E["face_bin"] = pd.cut(E.vtx_face_cm, [-1e9, 20, 50, 100, 1e9], labels=["<20", "20-50", "50-100", ">100"])
    pcs = D["pieces"]; sig = pcs[pcs.frac >= 0.10]
    esum = sig.groupby(K).kine_energy_particle.sum().rename("e_sum_pieces").reset_index(); E = E.merge(esum, on=K, how="left")
    E["resp_dom"] = E.dom_ke_row / E.photon_energy_mev; E["resp_sum"] = E.e_sum_pieces / E.photon_energy_mev
    return E


def photon_tables(E, D, obj, pcs):
    T = {}
    E = E.copy(); E["tp_label"] = E.truth35.clip(upper=2).map({0: "truth 0p", 1: "truth 1p", 2: "truth >=2p"})
    # Task 5: populations and the cross-tab with the Phase-9 labels
    T["photon_pid_populations"] = E.pid_class.value_counts().reindex(PI.PHOTON_CLASSES).fillna(0).astype(int).rename_axis("pid_class").reset_index(name="n").assign(fraction=lambda d: d.n / len(E))
    T["photon_pid_vs_phase9"] = pd.crosstab(E.pid_class, E.outcome).reset_index()
    T["photon_pid_vs_phase9_state"] = pd.crosstab(E.pid_class, E.photon_object_state).reset_index()
    T["fragmented_dominant_type"] = E[E.pid_class == PI.PHOTON_CLASSES[6]].dom_type.value_counts().rename_axis("dominant_type").reset_index(name="n")
    # Task 4: confusion (two variants), counts and row-normalised, vs photon energy
    cols = ["e-shower", "e-track", "mu-like", "pi-like", "proton-like", "other", "no row", "ambiguous"]
    def conf(df, variant):
        if variant == "phase9_hierarchy":      # fragmented / outside-candidate events are 'ambiguous'
            c = np.where(df.pid_class.isin([PI.PHOTON_CLASSES[6], PI.PHOTON_CLASSES[9]]), "ambiguous", np.where(df.pid_class.isin([PI.PHOTON_CLASSES[7], PI.PHOTON_CLASSES[8]]), "no row", df.dom_type))
        else:                                   # dominant object type regardless of fragmentation
            c = np.where(df.pid_class.isin([PI.PHOTON_CLASSES[8], PI.PHOTON_CLASSES[9]]), "no row", df.dom_type)
        return pd.Series(c, index=df.index)
    rows = []
    for var in ("phase9_hierarchy", "dominant_type"):
        E["reco_cls_" + var] = conf(E, var)
        for lab, g in [("all", E)] + [(b, d) for b, d in E.groupby("e_bin", observed=True)]:
            vc = g["reco_cls_" + var].value_counts()
            for c in cols:
                rows.append(dict(variant=var, e_bin=lab, reco=c, n=int(vc.get(c, 0)), fraction=float(vc.get(c, 0) / len(g)), n_bin=len(g)))
    T["photon_confusion"] = pd.DataFrame(rows)
    # Task 9: energy response by class
    rr = []
    for pop in (PI.PHOTON_CLASSES[0], PI.PHOTON_CLASSES[1], PI.PHOTON_CLASSES[2], PI.PHOTON_CLASSES[3], PI.PHOTON_CLASSES[4], PI.PHOTON_CLASSES[5], PI.PHOTON_CLASSES[6]):
        g = E[E.pid_class == pop]
        for nm, s in (("dominant row E_reco / E_true", g.resp_dom), ("sum of significant pieces / E_true", g.resp_sum)):
            m, lo, hi = q68(s); rr.append(dict(pid_class=pop, estimator=nm, n=int(s.notna().sum()), median=m, p16=lo, p84=hi))
    T["photon_energy_response"] = pd.DataFrame(rr)
    # Task 6-8: input comparison, clean electron shower vs mu / pi / proton / track dominant objects (non-fragmented events: class by the dominant object only)
    nf = E[E.photon_object_state != "photon_fragmented"].copy()
    feats = ["seg_length_cm", "row_total_length_cm", "row_n_segments", "kine_particle_nseg", "seg_n_fit", "start_degree", "end_degree", "n_free_ends", "pf_depth", "dom_ke_row", "resp_dom", "photon_energy_mev", "conv_distance_cm", "dominant_fraction", "d_vertex", "shw_start_to_reco_vtx"]
    pr = []
    for g_name, g in nf.groupby("dom_type"):
        if g_name == "no row" or len(g) < 5:
            continue
        rec = dict(dom_type=g_name, n=len(g), frac_at_main_vertex=float(g.at_main_vertex.astype(float).mean()), frac_muon_typed_sibling_at_main=float(g.has_mu_sibling_at_main.astype(float).mean()), frac_longer_muon_sibling_at_main=float(g.longer_mu_sibling_at_main.astype(float).mean()), frac_seg_flag_shower=float(g.seg_flag_shower.mean()), frac_dirsign_zero=float((g.seg_dirsign == 0).mean()) if g.seg_dirsign.notna().any() else np.nan,
                   frac_len_lt_1p5=float((g.seg_length_cm < 1.5).mean()), frac_len_lt_4=float((g.seg_length_cm < 4).mean()), frac_len_ge_20=float((g.seg_length_cm >= 20).mean()))
        for f_ in feats:
            m, lo, hi = q68(g[f_]); rec[f_ + "_median"] = m; rec[f_ + "_p16"] = lo; rec[f_ + "_p84"] = hi
        pr.append(rec)
    T["photon_pid_inputs"] = pd.DataFrame(pr)
    # Task 10: mis-typing rate vs geometry (non-fragmented: dominant type not e-shower; and all events: class != A)
    gr = []
    E["mistyped_dom"] = E.dom_type.isin(["mu-like", "pi-like", "proton-like", "e-track", "other"])
    for var, lab in (("e_bin", "photon energy [MeV]"), ("conv_bin", "conversion distance [cm]"), ("cos_bin", "cos theta (beam)"), ("face_bin", "distance of the true vertex to the nearest face [cm]"), ("photon_end_class", "true conversion class")):
        for b, g in E.groupby(var, observed=True):
            n = len(g)
            for c_, m_ in (("track-typed dominant object", g.dom_type.isin(["mu-like", "pi-like", "proton-like", "e-track", "other"])), ("muon-like", g.dom_type == "mu-like"), ("pion-like", g.dom_type == "pi-like"), ("proton-like", g.dom_type == "proton-like"), ("fragmented (Phase 9)", g.pid_class == PI.PHOTON_CLASSES[6]), ("clean electron shower", g.pid_class == PI.PHOTON_CLASSES[0])):
                f, lo, hi = cp(int(m_.sum()), n); gr.append(dict(variable=lab, bin=str(b), quantity=c_, n=n, k=int(m_.sum()), fraction=f, lo68=lo, hi68=hi))
    T["photon_misclassification_vs_geometry"] = pd.DataFrame(gr)
    # Task 19: fate by class
    st = [("shower stage", "A_n20mev"), ("BDT evaluable", "A_bdt_evaluable"), ("numu", "A_numu"), ("other", "A_other"), ("ncpi0", "A_ncpi0"), ("n_20br1", "A_n20br1"), ("final", "A_final")]
    fr = []
    for pop in PI.PHOTON_CLASSES:
        g = E[E.pid_class == pop]; prev = len(g)
        fr.append(dict(pid_class=pop, stage="all events", n=prev, step_survival=np.nan, cumulative=1.0))
        for nm, c in st:
            n = int(g[c].astype(bool).sum()) if len(g) else 0; fr.append(dict(pid_class=pop, stage=nm, n=n, step_survival=(n / prev) if prev else np.nan, cumulative=n / len(g) if len(g) else np.nan)); prev = n
    T["photon_pid_stage_fate"] = pd.DataFrame(fr)
    # Task 21: topology and Delta charge
    tt = []
    for var in ("tp_label", "delta_label"):
        for b, g in E.groupby(var):
            n = len(g)
            for pop in PI.PHOTON_CLASSES[:7]:
                k = int((g.pid_class == pop).sum()); tt.append(dict(group=str(b), pid_class=pop, n=k, fraction=k / n, n_group=n))
            tt.append(dict(group=str(b), pid_class="any track-typed dominant object", n=int(g.dom_type.isin(["mu-like", "pi-like", "proton-like", "e-track", "other"]).sum()), fraction=float(g.dom_type.isin(["mu-like", "pi-like", "proton-like", "e-track", "other"]).mean()), n_group=n))
    T["photon_pid_by_topology"] = pd.DataFrame(tt)
    return T, E


def track_origin(qf, label):
    """Does a fragmented event carry a track-typed significant piece, and in which piece (dominant vs minor)?"""
    trk = ["muon-like", "pion-like", "proton-like", "electron track"]
    ev = qf.groupby(K).agg(has_track=("type", lambda s_: s_.isin(trk).any())).reset_index()
    dom = qf[qf["rank"] == 1][K + ["type"]].rename(columns={"type": "dom_t"}); minor = qf[qf["rank"] > 1].groupby(K).type.apply(lambda s_: s_.isin(trk).any()).rename("minor_track").reset_index()
    ev = ev.merge(dom, on=K).merge(minor, on=K, how="left"); ev["dom_track"] = ev.dom_t.isin(trk); ev["minor_track"] = ev.minor_track.fillna(False).astype(bool); n = len(ev)
    dt = ev.dom_t.value_counts()
    rows = [dict(population=label, item="fragmented events", n=n, fraction=1.0), dict(population=label, item="with a track-typed significant piece", n=int(ev.has_track.sum()), fraction=float(ev.has_track.mean())),
            dict(population=label, item="dominant piece track-typed", n=int(ev.dom_track.sum()), fraction=float(ev.dom_track.mean())), dict(population=label, item="dominant piece electron shower, a minor piece track-typed", n=int((~ev.dom_track & ev.minor_track).sum()), fraction=float((~ev.dom_track & ev.minor_track).mean())),
            dict(population=label, item="dominant and a minor piece track-typed", n=int((ev.dom_track & ev.minor_track).sum()), fraction=float((ev.dom_track & ev.minor_track).mean())), dict(population=label, item="no track-typed significant piece", n=int((~ev.has_track).sum()), fraction=float((~ev.has_track).mean()))]
    for t in ("electron shower", "muon-like", "pion-like", "proton-like", "electron track", "no row"):
        rows.append(dict(population=label, item="dominant piece type: " + t, n=int(dt.get(t, 0)), fraction=float(dt.get(t, 0) / n)))
    return pd.DataFrame(rows)


def fragment_pid_tables(E, D, obj):
    """Task 11/12: PID of the significant pieces by rank and charge fraction."""
    q = D["pieces"].copy(); q = q[q.frac >= 0.10].copy()
    q = q.sort_values(K + ["q"], ascending=[True, True, False]); q["rank"] = q.groupby(K).cumcount() + 1; q["rank_label"] = q["rank"].map({1: "dominant (largest charge)", 2: "second piece"}).fillna("later pieces")
    q["type"] = q["type"].replace({"no particle row": "no row"})
    ks = obj.rename(columns={"cand": "nu_index", "row": "kine_index"})[K + ["nu_index", "kine_index", "seg_length_cm", "seg_flag_shower"]]
    q = q.merge(ks, on=K + ["nu_index", "kine_index"], how="left")
    fe = E[K + ["photon_object_state", "pid_class", "photon_energy_mev"]]; q = q.merge(fe, on=K, how="left")
    q["frac_bin"] = pd.cut(q.frac, [0.1, 0.2, 0.3, 0.5, 0.75, 1.01], labels=["0.1-0.2", "0.2-0.3", "0.3-0.5", "0.5-0.75", ">0.75"], right=False)
    T = {}
    qf = q[q.photon_object_state == "photon_fragmented"]
    rows = []
    for rk, g in qf.groupby("rank_label"):
        vc = g.type.value_counts()
        for t in ["electron shower", "electron track", "muon-like", "pion-like", "proton-like", "other", "no row"]:
            rows.append(dict(population="fragmented events", rank=rk, type=t, n=int(vc.get(t, 0)), fraction=float(vc.get(t, 0) / len(g)), n_pieces=len(g)))
    for rk, g in q[q.photon_object_state != "photon_fragmented"].groupby("rank_label"):
        vc = g.type.value_counts()
        for t in ["electron shower", "electron track", "muon-like", "pion-like", "proton-like", "other", "no row"]:
            rows.append(dict(population="non-fragmented events", rank=rk, type=t, n=int(vc.get(t, 0)), fraction=float(vc.get(t, 0) / len(g)), n_pieces=len(g)))
    T["fragment_type_by_rank"] = pd.DataFrame(rows)
    rows = []
    for fb, g in qf.groupby("frac_bin", observed=True):
        vc = g.type.value_counts()
        for t in ["electron shower", "muon-like", "pion-like", "proton-like", "electron track", "no row"]:
            rows.append(dict(frac_bin=str(fb), type=t, n=int(vc.get(t, 0)), fraction=float(vc.get(t, 0) / len(g)), n_pieces=len(g)))
    T["fragment_type_by_charge_fraction"] = pd.DataFrame(rows)
    rows = []
    for t, g in qf.groupby("type"):
        rec = dict(type=t, n=len(g))
        for f_ in ("frac", "kine_energy_particle", "seg_length_cm", "kine_particle_nseg", "depth"):
            m, lo, hi = q68(g[f_]); rec[f_ + "_median"] = m; rec[f_ + "_p16"] = lo; rec[f_ + "_p84"] = hi
        rec["frac_pool_0_1"] = float(g.kine_particle_pool.isin([0, 1]).mean()); rec["frac_other_cluster_of_dominant"] = float((g.location == "in another cluster (same candidate)").mean())
        rows.append(rec)
    T["fragment_piece_inputs_by_type"] = pd.DataFrame(rows)
    T["fragment_track_piece_origin"] = pd.concat([track_origin(qf.merge(E[K + ["A_n20mev"]], on=K), "fragmented events at the shower stage (Phase-14 population, A_n20mev)", lambda d: d.A_n20mev.astype(bool)), track_origin(qf, "all fragmented events (Phase 9)", lambda d: d.A_n20mev.astype(bool) | True)], ignore_index=True) if False else pd.concat([
        track_origin(qf.merge(E[K + ["A_n20mev"]], on=K).query("A_n20mev == True"), "fragmented events at the shower stage (Phase-14 population)"), track_origin(qf, "all fragmented events (Phase 9)")], ignore_index=True)
    return T, q


# =============================================================================================================== protons
def proton_table(D, obj):
    """One row per signal primary proton (all KE; the Phase-10 denominator is KE > 35 MeV): class from the rows of the SIGNAL-MATCHED candidate (Phase-10 bookkeeping)."""
    tp = D["tp"]; tp = tp[tp.is_signal & tp.primary].copy(); tp["ke_bin"] = pd.cut(tp.ke, PI.PROTON_KE_BINS, labels=KE_LAB, right=False)
    e_ = np.c_[tp.pf_end_x, tp.pf_end_y, tp.pf_end_z]; bx = np.array([[-200, 200], [-200, 200], [0, 500]])
    tp["end_face_cm"] = np.minimum((e_ - bx[:, 0]).min(axis=1), (bx[:, 1] - e_).min(axis=1)); tp["true_len_cm"] = np.linalg.norm(np.c_[tp.pf_end_x - tp.pf_start_x, tp.pf_end_y - tp.pf_start_y, tp.pf_end_z - tp.pf_start_z], axis=1)
    rows = obj[obj.p1_tid.notna()][KR + ["p1_tid", "p2_tid", "p3_tid", "type_class", "p1_iou_n", "p1_t_pdg", "p1_t_nu", "is_signal_photon_row", "pf_start_x", "pf_start_y", "pf_start_z", "seg_length_cm", "ke", "kine_particle_cluster_id", "kine_particle_pool"]]
    top = {k: g for k, g in rows.groupby(K + ["p1_tid"])}; sub2 = {k: g for k, g in rows.groupby(K + ["p2_tid"])}; sub3 = {k: g for k, g in rows.groupby(K + ["p3_tid"])}
    cls, dest, dom_t, info = [], [], [], []
    ps = D["ps"].set_index(K + ["trackid"]).state if "trackid" in D["ps"] else None
    for r in tp.itertuples():
        mc = r.match_cand
        if not np.isfinite(mc):
            cls.append(PI.PROTON_CLASSES[8]); dest.append(None); dom_t.append(None); info.append(None); continue
        key = (r.file_index, r.ev, r.trackid)
        t = top.get(key); t = t[t.cand == mc] if t is not None else None
        s = [x.get(key) for x in (sub2, sub3)]; s = pd.concat([x[x.cand == mc] for x in s if x is not None]) if any(x is not None for x in s) else None
        tr = list(t.type_class) if t is not None and len(t) else []
        c = PI.proton_reco_class(tr, list(s.type_class) if s is not None and len(s) else [], True); cls.append(c)
        dest.append(None); dom_t.append(None); info.append(None)
        if c == PI.PROTON_CLASSES[7]:      # merged / subdominant: what is the dominant object on those points?
            s = s.sort_values("p1_iou_n", ascending=False).iloc[0]
            dest.__setitem__(len(dest) - 1, PI.merge_destination(s.p1_t_pdg, s.p1_t_nu, r.t_nu, bool(s.is_signal_photon_row), s.p1_t_pdg))
            dom_t.__setitem__(len(dom_t) - 1, s.type_class)
            info.__setitem__(len(info) - 1, dict(dom_cand=int(s.cand), dom_row=int(s.row), dom_ke=float(s.ke), dom_iou_n=float(s.p1_iou_n), dom_cluster=float(s.kine_particle_cluster_id), dom_pool=float(s.kine_particle_pool), dom_len=float(s.seg_length_cm),
                                                  d_true_vertex=float(np.linalg.norm(np.array([s.pf_start_x - r.vtx_x, s.pf_start_y - r.vtx_y, s.pf_start_z - r.vtx_z]))) if np.isfinite(s.pf_start_x) else np.nan))
    tp["proton_class"] = cls; tp["merge_destination"] = dest; tp["merge_dominant_type"] = dom_t
    inf = pd.DataFrame([i if i else {} for i in info], index=tp.index); tp = pd.concat([tp, inf], axis=1)
    return tp


def proton_tables(tp, obj, D):
    T = {}
    tp = tp.copy(); t35 = tp[tp.ke > 35]
    T["proton_denominator"] = pd.DataFrame([dict(item="signal primary protons (all KE)", n=len(tp)), dict(item="signal primary protons KE > 35 MeV (Phase-10 denominator)", n=len(t35)), dict(item="  of which with a signal-matched candidate", n=int((t35.proton_class != PI.PROTON_CLASSES[8]).sum())),
                                            dict(item="signal primary protons KE <= 35 MeV", n=int((tp.ke <= 35).sum()))])
    cl = PI.PROTON_CLASSES
    rows = []
    for lab, g in [("all KE", tp), ("KE > 35 MeV", t35)] + [(b, d) for b, d in tp.groupby("ke_bin", observed=True)]:
        vc = g.proton_class.value_counts()
        for c in cl:
            rows.append(dict(ke_bin=lab, proton_class=c, n=int(vc.get(c, 0)), fraction=float(vc.get(c, 0) / len(g)), n_bin=len(g)))
    T["proton_confusion"] = pd.DataFrame(rows)
    # >500 MeV detail
    hi = tp[tp.ke > 500]; T["high_ke_proton_classes"] = hi.proton_class.value_counts().rename_axis("proton_class").reset_index(name="n").assign(fraction=lambda d: d.n / len(hi), n_total=len(hi))
    # persisted inputs of the typed rows of high-KE protons: length etc. of the top rows
    tops = obj[obj.is_signal_primary_proton_row].merge(tp[K + ["trackid", "match_cand", "ke_bin"]].rename(columns={"trackid": "p1_tid"}), on=K + ["p1_tid"], how="inner")
    tops = tops[tops.cand == tops.match_cand]
    feats = ["seg_length_cm", "row_total_length_cm", "row_n_segments", "kine_particle_nseg", "seg_n_fit", "start_degree", "end_degree", "n_free_ends", "ke", "proton_true_ke"]
    rr = []
    for (b, tc), g in tops.groupby(["ke_bin", "type_class"], observed=True):
        if len(g) < 5:
            continue
        rec = dict(ke_bin=str(b), reco_type=tc, n=len(g), frac_at_main_vertex=float(g.at_main_vertex.astype(float).mean()), frac_muon_typed_sibling_at_main=float(g.has_mu_sibling_at_main.astype(float).mean()), frac_longer_muon_sibling_at_main=float(g.longer_mu_sibling_at_main.astype(float).mean()), frac_seg_flag_shower=float(g.seg_flag_shower.mean()), frac_dirsign_zero=float((g.seg_dirsign == 0).mean()) if g.seg_dirsign.notna().any() else np.nan,
                   frac_is_shower_row=float((g.kine_particle_is_shower == 1).mean()))
        for f_ in feats:
            m, lo, hi_ = q68(g[f_]); rec[f_ + "_median"] = m; rec[f_ + "_p16"] = lo; rec[f_ + "_p84"] = hi_
        rec["ereco_over_etrue_median"] = q68(g.ke / g.proton_true_ke)[0]
        rr.append(rec)
    T["proton_pid_inputs"] = pd.DataFrame(rr)
    hk = tp[tp.ke > 300]; lr = []
    for (b, c), g in hk.groupby(["ke_bin", "proton_class"], observed=True):
        lr.append(dict(ke_bin=str(b), proton_class=c, n=len(g), frac_true_end_within_10cm_of_a_face=float((g.end_face_cm < 10).mean()), frac_true_end_within_30cm_of_a_face=float((g.end_face_cm < 30).mean()), true_path_length_median_cm=float(g.true_len_cm.median()), true_ke_median=float(g.ke.median())))
    T["high_ke_proton_leaving_and_length"] = pd.DataFrame(lr)
    # how many reconstructed rows carry a high-KE proton as their top partner, and how much of its true path they cover
    tr = obj[obj.is_signal_primary_proton_row].merge(tp[K + ["trackid", "match_cand", "true_len_cm", "ke_bin", "proton_class"]].rename(columns={"trackid": "p1_tid"}), on=K + ["p1_tid"]); tr = tr[tr.cand == tr.match_cand]
    sp_ = tr.groupby(K + ["p1_tid"]).agg(n_top_rows=("row", "size"), reco_path_cm=("row_total_length_cm", "sum"), true_len_cm=("true_len_cm", "first"), ke_bin=("ke_bin", "first"), proton_class=("proton_class", "first"), n_types=("type_class", "nunique")).reset_index()
    sp_["path_ratio"] = sp_.reco_path_cm / sp_.true_len_cm.replace(0, np.nan)
    rr2 = []
    for (b, c), g in sp_[sp_.ke_bin.isin(["200-300", "300-500", ">500"])].groupby(["ke_bin", "proton_class"], observed=True):
        rr2.append(dict(ke_bin=str(b), proton_class=c, n=len(g), frac_two_or_more_top_rows=float((g.n_top_rows >= 2).mean()), n_top_rows_mean=float(g.n_top_rows.mean()), reco_over_true_path_median=float(g.path_ratio.median()), reco_over_true_path_p16=float(g.path_ratio.quantile(0.16)), reco_over_true_path_p84=float(g.path_ratio.quantile(0.84))))
    T["high_ke_proton_row_splitting"] = pd.DataFrame(rr2)
    # merge destinations
    mg = tp[tp.proton_class == PI.PROTON_CLASSES[7]]
    rows = []
    for lab, g in [("all KE", mg)] + [(b, d) for b, d in mg.groupby("ke_bin", observed=True)]:
        vc = g.merge_destination.value_counts()
        for c in PI.MERGE_DESTINATIONS:
            rows.append(dict(ke_bin=lab, destination=c, n=int(vc.get(c, 0)), fraction=float(vc.get(c, 0) / len(g)) if len(g) else np.nan, n_bin=len(g)))
    T["proton_merge_destinations"] = pd.DataFrame(rows)
    mg35 = mg[mg.ke > 35]; rows_ = []
    for tr_, g in mg35.groupby(mg35.truth35.clip(upper=2)):
        vc = g.merge_destination.value_counts()
        for c in PI.MERGE_DESTINATIONS:
            rows_.append(dict(truth_topology={0: "truth 0p", 1: "truth 1p", 2: "truth >=2p"}[int(tr_)], destination=c, n=int(vc.get(c, 0)), fraction=float(vc.get(c, 0) / len(g)), n_group=len(g)))
    T["proton_merge_destinations_by_truth_topology_gt35"] = pd.DataFrame(rows_)
    T["proton_merge_dominant_type"] = mg.groupby(["ke_bin", "merge_dominant_type"], observed=True).size().rename("n").reset_index()
    T["proton_merge_geometry"] = pd.DataFrame([dict(item=k_, **dict(zip(("median", "p16", "p84"), q68(mg[k_])))) for k_ in ("dom_iou_n", "d_true_vertex", "dom_ke", "dom_len")])
    # topology
    tt = []
    for var in ("truth35", "delta_label"):
        for b, g in t35.groupby(var):
            n = len(g)
            for c in cl:
                tt.append(dict(group=str(b), proton_class=c, n=int((g.proton_class == c).sum()), fraction=float((g.proton_class == c).mean()), n_group=n))
    T["proton_pid_by_topology"] = pd.DataFrame(tt)
    # Phase-10 reproduction (KE > 35)
    ps = D["ps"]; T["phase10_state_reproduction"] = pd.DataFrame([dict(phase10_state=k_, n=int(v)) for k_, v in ps.state.value_counts().items()])
    return T, tp


def crossconf(E, tp):
    """Task 17: compact photon / proton cross-confusion."""
    ph = E.reco_cls_dominant_type.value_counts(); n = len(E); t35 = tp[tp.ke > 35]; pc = t35.proton_class.value_counts(); m = len(t35)
    rows = [dict(truth="signal photon (dominant object)", reco=("no row / merged / no candidate" if r == "no row" else r), n=int(ph.get(r, 0)), fraction=float(ph.get(r, 0) / n), n_truth=n) for r in ["e-shower", "e-track", "mu-like", "pi-like", "proton-like", "other", "no row"]]
    mp = {"e-shower": PI.PROTON_CLASSES[3], "e-track": PI.PROTON_CLASSES[4], "mu-like": PI.PROTON_CLASSES[1], "pi-like": PI.PROTON_CLASSES[2], "proton-like": PI.PROTON_CLASSES[0], "other": PI.PROTON_CLASSES[5]}
    rows += [dict(truth="signal primary proton > 35 MeV (top row)", reco=r, n=int(pc.get(c, 0)), fraction=float(pc.get(c, 0) / m), n_truth=m) for r, c in mp.items()]
    rows += [dict(truth="signal primary proton > 35 MeV (top row)", reco="no row / merged / no candidate", n=int(pc.get(PI.PROTON_CLASSES[6], 0) + pc.get(PI.PROTON_CLASSES[7], 0) + pc.get(PI.PROTON_CLASSES[8], 0)), fraction=float((pc.get(PI.PROTON_CLASSES[6], 0) + pc.get(PI.PROTON_CLASSES[7], 0) + pc.get(PI.PROTON_CLASSES[8], 0)) / m), n_truth=m)]
    return pd.DataFrame(rows)


# =============================================================================================================== numu connection
def numu_connection(D, obj):
    """Task 20: for the events that reach numu, classify the muon/pion-typed rows of the controlling candidate by truth (signal-photon piece / true hadron / other) and tabulate numu survival."""
    n = D["numu"][K + ["c_nu_index", "survive", "numu_score", "reach_numu", "n_mu_pi_rows", "truth35"]].copy(); n = n[n.reach_numu.astype(bool)] if "reach_numu" in n else n
    mp_ = obj[obj.type_class.isin(["mu-like", "pi-like"])].merge(n[K + ["c_nu_index"]].rename(columns={"c_nu_index": "cand"}), on=K + ["cand"])
    def kind(r):
        if r.is_signal_photon_row:
            return "signal-photon piece"
        if not np.isfinite(r.p1_t_nu) or r.p1_t_nu < -5 or r.p1_tid < 0:
            return "other (unmatched)"
        if r.p1_t_nu == r.signal_nu_idx and int(abs(r.p1_t_pdg)) in (2212, 211, 13, 2112, 321) or (r.p1_t_nu == r.signal_nu_idx and int(abs(r.p1_t_pdg)) > 1000):
            return "true hadronic object (signal interaction)"
        if r.p1_t_nu == r.signal_nu_idx:
            return "other signal-interaction object (EM, e.g. low-energy photon)"
        return "other (cosmic / other neutrino)"
    mp_["mp_kind"] = [kind(r) for r in mp_.itertuples()]
    ev = mp_.groupby(K).mp_kind.apply(lambda s: set(s)).rename("kinds").reset_index(); m = n.merge(ev, on=K, how="left"); m["kinds"] = m.kinds.apply(lambda x: x if isinstance(x, set) else set())
    def cat(s):
        if not s:
            return "no muon/pion-typed row"
        ph = "signal-photon piece" in s; had = "true hadronic object (signal interaction)" in s; oth = bool(s - {"signal-photon piece", "true hadronic object (signal interaction)"})
        if ph and not had and not oth: return "only signal-photon piece(s)"
        if had and not ph and not oth: return "only true hadronic object(s)"
        if ph and had: return "signal-photon piece(s) and true hadronic object(s)"
        if oth and not ph and not had: return "only other objects"
        return "signal-photon piece(s) and other objects (no hadron)" if ph else "hadron and other objects (no photon piece)"
    m["numu_mp_category"] = m.kinds.apply(cat); m["numu_fail"] = ~m.survive.astype(bool)
    rows = []
    for c, g in m.groupby("numu_mp_category"):
        f, lo, hi = cp(int(g.survive.sum()), len(g)); rows.append(dict(category=c, n=len(g), numu_pass=int(g.survive.sum()), numu_fail=int((~g.survive.astype(bool)).sum()), survival=f, lo68=lo, hi68=hi, median_numu_score=float(g.numu_score.median())))
    T = pd.DataFrame(rows).sort_values("n", ascending=False)
    fail = m[m.numu_fail]; tot = len(fail)
    share = pd.DataFrame([dict(category=c, n_failures=int((fail.numu_mp_category == c).sum()), share_of_failures=float((fail.numu_mp_category == c).mean())) for c in m.numu_mp_category.unique()]).sort_values("n_failures", ascending=False)
    cnt = mp_.mp_kind.value_counts().rename_axis("mu_pi_row_truth").reset_index(name="n_rows")
    return T, share, cnt, m


# =============================================================================================================== manual event lists
def manual_lists(E, tp, obj):
    out = {}
    def pick(df, n=20):
        df = df.sort_values(K)
        if len(df) <= n:
            return df
        idx = np.unique(np.round(np.linspace(0, len(df) - 1, n)).astype(int)); return df.iloc[idx]
    base = E[E.photon_object_state != "photon_fragmented"]
    out["photon_to_muon_like"] = pick(base[base.dom_type == "mu-like"][K + ["photon_energy_mev", "dom_nu", "dom_row", "outcome"]])
    out["photon_to_pion_like"] = pick(base[base.dom_type == "pi-like"][K + ["photon_energy_mev", "dom_nu", "dom_row", "outcome"]])
    out["photon_to_proton_like"] = pick(base[base.dom_type == "proton-like"][K + ["photon_energy_mev", "dom_nu", "dom_row", "outcome"]])
    h = tp[(tp.ke > 500) & tp.proton_class.isin([PI.PROTON_CLASSES[1], PI.PROTON_CLASSES[2], PI.PROTON_CLASSES[3]])]
    out["proton_gt500_to_mu_pi_e"] = pick(h[K + ["trackid", "ke", "proton_class", "match_cand"]])
    l = tp[(tp.ke < 75) & (tp.ke > 0) & (tp.proton_class == PI.PROTON_CLASSES[7])]
    out["proton_lt75_merged"] = pick(l[K + ["trackid", "ke", "proton_class", "merge_destination", "match_cand"]])
    return out


def git_head():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    except Exception:
        return "unknown"


# =============================================================================================================== source-vs-data checks, vertex, figures, main
def source_checks(D, obj, E):
    seg = D["seg"].copy(); seg["nu_index"] = seg.nu_index.astype(int)
    cd = D["cand"][K + ["cand_pos", "kine_main_vertex_id"]].rename(columns={"cand_pos": "nu_index"})
    s = seg.merge(cd, on=K + ["nu_index"]); s["atmain"] = (s.start_vertex_id == s.kine_main_vertex_id) | (s.end_vertex_id == s.kine_main_vertex_id)
    m = s[s.atmain & (s.flag_shower == 0)]
    nmu = m.groupby(K + ["nu_index"]).pdg.apply(lambda x: int((x == 13).sum()))
    pi = m[m.pdg == 211]; mu_len = m[m.pdg == 13].groupby(K + ["nu_index"]).length_cm.max().rename("mu_len").reset_index()
    pi = pi.merge(mu_len, on=K + ["nu_index"], how="left")
    ns = s[(s.flag_shower == 0)]
    rows = [
        dict(check="candidates with a main vertex and >= 1 non-shower segment at it", value=int(len(nmu))),
        dict(check="  with 0 muon-typed segments at the main vertex", value=int((nmu == 0).sum())), dict(check="  with exactly 1 muon-typed segment at the main vertex", value=int((nmu == 1).sum())),
        dict(check="  with >= 2 muon-typed segments at the main vertex (source arbitration leaves at most 1 unless a long-muon chain claims the slot)", value=int((nmu >= 2).sum())),
        dict(check="pion-typed non-shower segments (all)", value=int(((ns.pdg == 211)).sum())), dict(check="  of which at the main vertex", value=int(len(pi))),
        dict(check="  at the main vertex with a muon-typed sibling at the main vertex", value=int(pi.mu_len.notna().sum())), dict(check="  at the main vertex with a muon-typed sibling at least as long", value=int((pi.mu_len >= pi.length_cm).sum())),
        dict(check="pion-typed non-shower segments shorter than 1.5 cm (vertex-activity rule region)", value=int(((ns.pdg == 211) & (ns.length_cm < 1.5)).sum())),
        dict(check="T_kine rows (all candidates)", value=int(len(obj))), dict(check="  rows whose type equals the key segment's pdg", value=int((obj.kine_particle_type.abs() == obj.seg_pdg.abs()).sum())),
        dict(check="  shower rows (kine_particle_is_shower == 1)", value=int((obj.kine_particle_is_shower == 1).sum())), dict(check="  shower rows whose key segment is NOT flagged shower (the shower object is built around a track-typed start segment)", value=int(((obj.kine_particle_is_shower == 1) & (obj.seg_flag_shower == 0)).sum())),
        dict(check="  shower rows typed muon / pion / proton", value=int(((obj.kine_particle_is_shower == 1) & obj.kine_particle_type.abs().isin([13, 211, 2212])).sum())),
        dict(check="  shower rows typed electron", value=int(((obj.kine_particle_is_shower == 1) & (obj.kine_particle_type.abs() == 11)).sum()))]
    if obj.seg_dirsign.notna().any():
        t = obj[obj.seg_flag_shower == 0]
        for p in (11, 13, 211, 2212):
            g = t[t.seg_pdg.abs() == p]; rows.append(dict(check=f"non-shower key segments typed {p}: fraction with dirsign 0", value=float((g.seg_dirsign == 0).mean())))
    return pd.DataFrame(rows)


def vertex_check(E):
    """Task 23 (limited): reco vs true vertex by photon PID class from the Phase-9 vertex geometry; T_dlvtx is NOT in the derived tables, so the DL vertex comparison is deferred."""
    rows = []
    for c in PI.PHOTON_CLASSES[:7]:
        g = E[(E.pid_class == c) & E.d_vertex.notna()]
        if len(g) < 5:
            continue
        rows.append(dict(pid_class=c, n=len(g), d_vertex_median=q68(g.d_vertex)[0], d_vertex_p16=q68(g.d_vertex)[1], d_vertex_p84=q68(g.d_vertex)[2], shw_start_to_reco_vtx_median=q68(g.shw_start_to_reco_vtx)[0], shw_start_to_true_conv_median=q68(g.shw_start_to_true_conv)[0],
                         frac_anchored_5cm=float(g.anchored5.astype(float).mean()), frac_prox_interaction_vertex=float((g.prox == "interaction_vertex").mean()), frac_prox_conversion_point=float((g.prox == "conversion_point").mean()), frac_prox_neither=float((g.prox == "neither").mean())))
    return pd.DataFrame(rows)


import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sbnd_single_photon import plotstyle as PS
PROV = "official Gen2 NC-Delta | Wire-Cell fg1 reconstruction as produced | source-ranked T_match truth | TPC-box signal events | descriptive audit, no type or cut changed"
TCOL = {"e-shower": "#009E73", "e-track": "#56B4E9", "mu-like": "#D55E00", "pi-like": "#E69F00", "proton-like": "#0072B2", "other": "#999999", "no row": "#bbbbbb", "ambiguous": "#CC79A7"}
PCOL = {"proton-typed": "#0072B2", "mu-typed": "#D55E00", "pi-typed": "#E69F00", "e-shower-typed": "#009E73", "e-track-typed": "#56B4E9", "other-typed": "#999999", "no row": "#bbbbbb", "merged / subdominant partner": "#CC79A7", "no signal-matched candidate": "#444444"}


def save(fig, name):
    PS.annotate(fig, PROV, extra=PS.PRELIM); fig.savefig(PLT / name, bbox_inches="tight"); plt.close(fig)


def stackbars(a, df, xcol, ccol, colors, order_c, order_x, ylabel="fraction"):
    bottom = np.zeros(len(order_x)); x = np.arange(len(order_x))
    for c in order_c:
        v = np.array([df[(df[xcol] == xx) & (df[ccol] == c)].fraction.sum() for xx in order_x]); a.bar(x, v, 0.8, bottom=bottom, color=colors.get(c, "0.5"), edgecolor="white", linewidth=0.4, label=c); bottom += v
    a.set_xticks(x); a.set_xticklabels(order_x); a.set_ylabel(ylabel); a.set_ylim(0, 1.02)


def figures(E, obj, T, tp, FT, numu_T, cross):
    pc = T["photon_confusion"]; fig, ax = PS.figure(1, 2, size=(13, 4.3))
    for j, var in enumerate(("dominant_type", "phase9_hierarchy")):
        d = pc[(pc.variant == var) & (pc.e_bin != "all")]; stackbars(ax[0][j], d, "e_bin", "reco", TCOL, ["e-shower", "e-track", "mu-like", "pi-like", "proton-like", "other", "no row", "ambiguous"], E_LAB)
        ax[0][j].set_xlabel("true photon energy [MeV]"); ax[0][j].set_title("dominant reconstructed object's type" if j == 0 else "Phase-9 hierarchy (fragmented / outside = ambiguous)", fontsize=9)
    ax[0][1].legend(fontsize=6, loc="upper left", bbox_to_anchor=(1.0, 1)); fig.tight_layout(); save(fig, "fig1_true_photon_reco_type_vs_energy.png")
    cf = T["proton_confusion"]; fig, ax = PS.figure(1, 1, size=(9.5, 4.4)); d = cf[~cf.ke_bin.isin(["all KE", "KE > 35 MeV"])]
    stackbars(ax[0][0], d, "ke_bin", "proton_class", PCOL, PI.PROTON_CLASSES, KE_LAB); ax[0][0].set_xlabel("true proton KE [MeV]"); ax[0][0].legend(fontsize=6, loc="upper left", bbox_to_anchor=(1.0, 1)); ax[0][0].set_title("true signal primary proton -> reconstructed class (signal-matched candidate)"); fig.tight_layout(); save(fig, "fig2_true_proton_reco_type_vs_ke.png")
    nf = E[E.photon_object_state != "photon_fragmented"]; fig, ax = PS.figure(1, 3, size=(14, 3.8))
    for j, (col, lab, bins, lg) in enumerate((("seg_length_cm", "key-segment fit-path length [cm]", np.logspace(-1, 2, 40), True), ("row_n_segments", "segments in the object", np.arange(0.5, 31.5, 1), False), ("dom_ke_row", "object reconstructed energy [MeV]", np.logspace(0, 3.3, 40), True))):
        for t in ("e-shower", "mu-like", "pi-like", "proton-like"):
            v = nf[nf.dom_type == t][col].dropna(); ax[0][j].hist(v.clip(lower=bins[0]), bins=bins, histtype="step", lw=1.6, color=TCOL[t], density=True, label=f"{t} (n={len(v)})")
        if lg: ax[0][j].set_xscale("log")
        ax[0][j].set_xlabel(lab); ax[0][j].set_ylabel("normalised")
    ax[0][0].legend(fontsize=6); ax[0][1].set_title("persisted PID inputs of the dominant photon object (dQ/dx not persisted)", fontsize=8); fig.tight_layout(); save(fig, "fig3_photon_pid_inputs.png")
    tops = obj[obj.is_signal_primary_proton_row].merge(tp[K + ["trackid", "match_cand", "ke_bin"]].rename(columns={"trackid": "p1_tid"}), on=K + ["p1_tid"]); tops = tops[(tops.cand == tops.match_cand) & (tops.proton_true_ke > 35)]
    fig, ax = PS.figure(1, 3, size=(14, 3.8))
    for j, (col, lab, bins, lg) in enumerate((("seg_length_cm", "key-segment fit-path length [cm]", np.logspace(-1, 2.3, 40), True), ("row_n_segments", "segments in the object", np.arange(0.5, 31.5, 1), False), ("proton_true_ke", "true proton KE [MeV]", np.logspace(1.5, 3.4, 40), True))):
        for t in ("proton-like", "mu-like", "pi-like", "e-shower"):
            v = tops[tops.type_class == t][col].dropna(); ax[0][j].hist(v.clip(lower=bins[0]), bins=bins, histtype="step", lw=1.6, color=TCOL[t], density=True, label=f"{t} (n={len(v)})")
        if lg: ax[0][j].set_xscale("log")
        ax[0][j].set_xlabel(lab); ax[0][j].set_ylabel("normalised")
    ax[0][0].legend(fontsize=6); ax[0][1].set_title("persisted PID inputs of the true-proton top rows (> 35 MeV)", fontsize=8); fig.tight_layout(); save(fig, "fig4_proton_pid_inputs.png")
    fig, ax = PS.figure(1, 2, size=(13, 4.6))
    for j, (df, cls, ttl, ycol) in enumerate(((nf[nf.dom_type.isin(["e-shower", "mu-like", "pi-like", "proton-like"])], "dom_type", "dominant photon object", "dom_ke_row"), (tops, "type_class", "true-proton top row", "ke"))):
        for t in ("e-shower", "mu-like", "pi-like", "proton-like"):
            g = df[df[cls] == t]; g = g[(g.seg_length_cm > 0) & (g[ycol] > 0)]; ax[0][j].scatter(g.seg_length_cm, g[ycol], s=3, alpha=0.25, color=TCOL[t], label=f"{t} ({len(g)})", rasterized=True)
        for xv, lb in ((1.5, "1.5: vertex-activity rule"), (4, "4: range vs dQ/dx KE"), (10, "10: bad-score -> shower"), (20, "20: electron template")):
            ax[0][j].axvline(xv, color="k", lw=0.7, ls=":"); ax[0][j].text(xv, 0.985, lb, rotation=90, fontsize=5.5, va="top", ha="right", transform=ax[0][j].get_xaxis_transform())
        ax[0][j].set_xscale("log"); ax[0][j].set_yscale("log"); ax[0][j].set_xlabel("key-segment fit-path length [cm]"); ax[0][j].set_ylabel("reconstructed row energy [MeV]"); ax[0][j].set_title(ttl + " (source LENGTH thresholds; dQ/dx axes not available)", fontsize=8); ax[0][j].legend(fontsize=6, markerscale=3)
    fig.tight_layout(); save(fig, "fig5_length_vs_energy_with_source_thresholds.png")
    fq = FT["fragment_type_by_charge_fraction"]; fr = FT["fragment_type_by_rank"]; fig, ax = PS.figure(1, 2, size=(13, 4.3)); tc = {"electron shower": TCOL["e-shower"], "muon-like": TCOL["mu-like"], "pion-like": TCOL["pi-like"], "proton-like": TCOL["proton-like"], "electron track": TCOL["e-track"], "no row": "#bbbbbb"}
    order = ["0.1-0.2", "0.2-0.3", "0.3-0.5", "0.5-0.75", ">0.75"]; stackbars(ax[0][0], fq, "frac_bin", "type", tc, list(tc), order); ax[0][0].set_xlabel("piece charge fraction of the photon's in-candidate charge"); ax[0][0].set_title("fragmented events: piece type vs charge fraction", fontsize=9)
    d = fr[fr.population == "fragmented events"]; rk = ["dominant (largest charge)", "second piece", "later pieces"]; stackbars(ax[0][1], d, "rank", "type", tc, list(tc), rk); ax[0][1].set_title("fragmented events: piece type by rank", fontsize=9); ax[0][1].legend(fontsize=6, loc="upper left", bbox_to_anchor=(1.0, 1)); fig.tight_layout(); save(fig, "fig6_fragment_type_vs_charge_fraction.png")
    md = T["proton_merge_destinations"]; md = md[md.ke_bin != "all KE"]; fig, ax = PS.figure(1, 1, size=(9, 4.2)); dc = {"signal photon": "#D55E00", "another signal proton": "#0072B2", "non-proton signal hadron (pion / muon / neutron-like)": "#E69F00", "other signal EM": "#009E73", "other-neutrino or cosmic object": "#000000", "unmatched / ambiguous": "#bbbbbb"}
    stackbars(ax[0][0], md, "ke_bin", "destination", dc, PI.MERGE_DESTINATIONS, KE_LAB); ax[0][0].set_xlabel("true proton KE [MeV]"); ax[0][0].legend(fontsize=6, loc="upper left", bbox_to_anchor=(1.0, 1))
    for k_, b in enumerate(KE_LAB):
        n = int(md[(md.ke_bin == b)].n_bin.iloc[0]) if (md.ke_bin == b).any() else 0; ax[0][0].text(k_, 1.005, f"n={n}", ha="center", fontsize=7)
    ax[0][0].set_title("subdominant (merged) true protons: truth of the dominant object they merge into", fontsize=9); fig.tight_layout(); save(fig, "fig7_low_ke_proton_merge_destination.png")
    hi = tp[tp.ke > 300].copy(); fig, ax = PS.figure(1, 1, size=(8, 4.2)); hc = hi.groupby(["ke_bin", "proton_class"], observed=True).size().rename("n").reset_index(); hc["fraction"] = hc.n / hc.groupby("ke_bin", observed=True).n.transform("sum")
    stackbars(ax[0][0], hc, "ke_bin", "proton_class", PCOL, PI.PROTON_CLASSES, ["300-500", ">500"]); ax[0][0].set_xlabel("true proton KE [MeV]"); ax[0][0].legend(fontsize=6, loc="upper left", bbox_to_anchor=(1.0, 1)); ax[0][0].set_title("high-KE true protons: reconstructed class", fontsize=9); fig.tight_layout(); save(fig, "fig8_high_ke_proton_mistype_breakdown.png")
    fig, ax = PS.figure(1, 1, size=(9, 4.2)); d = numu_T.sort_values("survival"); y = np.arange(len(d)); ax[0][0].barh(y, d.survival, color="#D55E00"); ax[0][0].errorbar(d.survival, y, xerr=[d.survival - d.lo68, d.hi68 - d.survival], fmt="none", color="k", lw=0.8)
    ax[0][0].set_yticks(y); ax[0][0].set_yticklabels([f"{c} (n={n})" for c, n in zip(d.category, d.n)], fontsize=7); ax[0][0].set_xlabel("numu survival of events reaching numu"); ax[0][0].set_title("numu survival by the truth of the muon/pion-typed rows of the controlling candidate", fontsize=8); ax[0][0].set_xlim(0, 1); fig.tight_layout(); save(fig, "fig9_numu_survival_by_mu_pi_row_truth.png")
    fig, ax = PS.figure(1, 1, size=(8, 4.6)); a = ax[0][0]; c = cross.copy(); c["lab"] = c.truth.str.split(" ").str[:3].str.join(" "); piv = c.pivot_table(index="truth", columns="reco", values="fraction", aggfunc="sum").fillna(0)
    im = a.imshow(piv.values, cmap="Blues", vmin=0, vmax=1, aspect="auto"); a.set_xticks(range(piv.shape[1])); a.set_xticklabels(piv.columns, rotation=40, ha="right", fontsize=7); a.set_yticks(range(piv.shape[0])); a.set_yticklabels(piv.index, fontsize=7); a.grid(False)
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            a.text(j, i, f"{piv.values[i, j]:.3f}", ha="center", va="center", fontsize=7, color="white" if piv.values[i, j] > 0.5 else "black")
    a.set_title("common photon / proton reconstructed-type summary (row-normalised)", fontsize=9); fig.tight_layout(); save(fig, "fig10_photon_proton_confusion_summary.png")


def main():
    OUT.mkdir(parents=True, exist_ok=True); TAB.mkdir(parents=True, exist_ok=True); PLT.mkdir(parents=True, exist_ok=True); (OUT / "manual_event_lists").mkdir(exist_ok=True)
    D = load(); obj = common_objects(D); E = photon_events(D, obj); T, E = photon_tables(E, D, obj, D["pieces"]); FT, pieces = fragment_pid_tables(E, D, obj)
    tp = proton_table(D, obj); PT, tp = proton_tables(tp, obj, D); T.update(PT); T.update(FT)
    T["cross_confusion"] = crossconf(E, tp); T["source_vs_data_checks"] = source_checks(D, obj, E); T["photon_vertex_check"] = vertex_check(E)
    nT, share, cnt, nm = numu_connection(D, obj); T["numu_by_mu_pi_row_truth"] = nT; T["numu_failure_share"] = share; T["numu_mu_pi_row_truth_counts"] = cnt
    T["source_rules"] = pd.DataFrame(PI.SOURCE_RULES); T["not_persisted_pid_inputs"] = pd.DataFrame(dict(input=PI.NOT_PERSISTED))
    for k, v in T.items():
        v.to_csv(TAB / f"{k}.csv", index=False)
    figures(E, obj, T, tp, FT, nT, T["cross_confusion"])
    # ---- detailed outputs
    sel = obj[obj.is_signal_photon_row | obj.is_signal_primary_proton_row]
    pq(sel, OUT / "truth_matched_pid_objects.parquet"); pq(E[K + ["pid_class", "dom_type", "photon_object_state", "outcome", "photon_energy_mev", "conv_distance_cm", "cos_theta_beam", "vtx_face_cm", "truth35", "delta_label", "dom_nu", "dom_row", "seg_length_cm", "row_n_segments", "dom_ke_row", "resp_dom", "resp_sum", "d_vertex",
                                                                 "A_n20mev", "A_numu", "A_other", "A_ncpi0", "A_n20br1", "A_final"]], OUT / "photon_pid_events.parquet")
    pq(tp.drop(columns=[c for c in tp.columns if c.startswith(("r1_", "r2_", "r3_", "pf_start_p"))], errors="ignore"), OUT / "proton_pid_events.parquet"); pq(pieces, OUT / "photon_fragment_pid.parquet")
    pq(tp[tp.proton_class == PI.PROTON_CLASSES[7]], OUT / "proton_merge_destinations.parquet"); pq(nm, OUT / "numu_mu_pi_row_events.parquet")
    for k, v in manual_lists(E, tp, obj).items():
        v.to_csv(OUT / "manual_event_lists" / f"{k}.csv", index=False)
    meta = dict(phase=15, git_commit_at_run=git_head(), official_manifest_sha256=sha(REPO / "manifests" / "official_gen2_ncdelta_wc.tsv.gz"), source_pin=PI.SOURCE_COMMIT, phase9_taxonomy_sha256=sha(P9 / "event_taxonomy.parquet"), phase10_proton_association_sha256=sha(P10 / "row_matches.parquet"),
                phase10_truth_proton_states_sha256=sha(P10 / "truth_proton_states.parquet"), phase14_fragment_table_sha256=sha(P14 / "fragmentation_objects.parquet"), phase12_numu_stage_sha256=sha(P12 / "numu_stage.parquet"),
                seg_extra_scan=dict(present=D["seg_extra"] is not None, sha256=sha(RAW / "seg_extra.parquet") if D["seg_extra"] is not None else None, manifest=str(RAW / "seg_extra_manifest.parquet")),
                pid_source_files={f: "git show 4b6853d4:clus/src/" + f for f in ("PRSegmentFunctions.cxx", "NeutrinoTrackShowerSep.cxx", "NeutrinoVertexFinder.cxx", "NeutrinoPatternBase.cxx", "NeutrinoShowerClustering.cxx", "NeutrinoKinematics.cxx", "PRShower.cxx")},
                truth_association="source-ranked T_match level-1 partner (point IoU, then charge IoU, then object index), Phase-10 row_matches", significant_piece_fraction=0.10, not_persisted=PI.NOT_PERSISTED)
    (OUT / "metadata.json").write_text(json.dumps(meta, indent=1))
    summ = dict(n_photon_events=len(E), n_rows=len(obj), n_signal_photon_rows=int(obj.is_signal_photon_row.sum()), n_signal_proton_rows=int(obj.is_signal_primary_proton_row.sum()), n_primary_protons=len(tp), n_protons_gt35=int((tp.ke > 35).sum()),
                photon_populations=T["photon_pid_populations"].to_dict("records"), seg_extra_present=D["seg_extra"] is not None)
    (TAB / "summary.json").write_text(json.dumps(summ, indent=1, default=float)); print("done", len(E), len(tp), flush=True)
    return E, obj, tp, T


if __name__ == "__main__":
    main()
