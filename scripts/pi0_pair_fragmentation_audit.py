#!/usr/bin/env python
"""Phase 14: which reconstructed objects form the pi0-like pair that fails genuine single-photon events at the frozen ncpi0 stage (roadmap Y), and what exactly are the reconstructed fragments of the
signal photon (roadmap U).  CHARACTERISATION ONLY: no cut, threshold, BDT, FV, proton-policy or candidate-policy change.

    source env/setup_eaf.sh
    python scripts/pi0_pair_fragmentation_audit.py            # reads the Phase 9/10/12 tables + the Phase 14 T_truth_nu scan; no ROOT scan

Fixed convention (not a Phase-13 policy alternative): official Gen2 NC-Delta, provisional TPC truth box, frozen BDT thresholds, candidate policy ``any`` (the CONTROLLING candidate of an event is the Phase-12
one), no analysis FV, frozen reconstruction as produced.  Outputs: ``$SP_DATA/pi0_pair_fragmentation_audit/official_ncdelta/`` (parquet, metadata), ``tables/pi0_pair_fragmentation_audit/`` and
``plots/pi0_pair_fragmentation_audit/`` (small, committed).
"""
from __future__ import annotations
import hashlib, json, os, subprocess, sys, warnings
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from sbnd_single_photon import pair_audit as PA

SPD = Path(os.environ["SP_DATA"]); OUT = SPD / "pi0_pair_fragmentation_audit" / "official_ncdelta"; RAW = OUT / "raw"
P9 = SPD / "shower_vertex_audit" / "official_ncdelta"; P10 = SPD / "proton_truth_association" / "official_ncdelta"; P12 = SPD / "remaining_stage_audit" / "official_ncdelta"
TAB = REPO / "tables" / "pi0_pair_fragmentation_audit"; PLT = REPO / "plots" / "pi0_pair_fragmentation_audit"
KEY = ["file_index", "ev"]
AV = dict(x=(-200.0, 200.0), y=(-200.0, 200.0), z=(0.0, 500.0))      # the provisional active-volume box, used ONLY to tell dirt from in-TPC other-neutrino interactions


def pq(df, path):
    df = df.copy()
    for c in df.columns:
        if str(df[c].dtype) in ("category", "interval") or "Interval" in str(df[c].dtype):
            df[c] = df[c].astype(str)
    df.to_parquet(path, index=False)


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load():
    st = pd.read_parquet(P12 / "ncpi0_stage.parquet"); st[KEY] = st[KEY].astype(int)
    cand = pd.read_parquet(P12 / "raw" / "official_candidates.parquet"); cand[KEY] = cand[KEY].astype(int)
    E = pd.read_parquet(P9 / "event_taxonomy.parquet"); E[KEY] = E[KEY].astype(int)
    rm = pd.read_parquet(P10 / "row_matches.parquet"); kine = pd.read_parquet(P9 / "raw" / "kine.parquet"); pf = pd.read_parquet(P9 / "raw" / "pf.parquet")
    seg = pd.read_parquet(P9 / "raw" / "seg.parquet"); pho = pd.read_parquet(P9 / "raw" / "pho_ov.parquet"); ovall = pd.read_parquet(P9 / "raw" / "ov_all.parquet")
    tnu = pd.read_parquet(RAW / "truth_nu.parquet")
    for d in (kine, pf, seg, pho, ovall, tnu):
        d[KEY] = d[KEY].astype(int)
    return dict(st=st, cand=cand, E=E, rm=rm, kine=kine, pf=pf, seg=seg, pho=pho, ovall=ovall, tnu=tnu)


def population(D):
    """Task: ncpi0 population closure (entering / pass / finite-score reject / non-finite)."""
    st = D["st"]; c = D["cand"]
    fin = np.isfinite(st.stage_score); rej = ~st.survive
    nf = st[~fin].merge(c[KEY + ["c_nu_index"] + [x for x in c.columns if "kine_pio" in x or "pio_flag_pio" in x or "pio_1_mass" in x]], on=KEY + ["c_nu_index"], how="left")
    pop = dict(entering=int(len(st)), passing=int(st.survive.sum()), rejected=int(rej.sum()), rejected_finite=int((rej & fin).sum()), rejected_nonfinite=int((rej & ~fin).sum()),
               passing_nonfinite=int((st.survive & ~fin).sum()), closure=bool(len(st) == st.survive.sum() + (rej & fin).sum() + (rej & ~fin).sum()),
               nonfinite_events=nf[KEY + ["c_nu_index", "in_kine_pio_flag", "in_kine_pio_mass", "in_kine_pio_dis_1", "in_kine_pio_dis_2", "in_kine_pio_angle", "in_shw_sp_pio_flag_pio"]].to_dict("records"))
    return pop


def event_inputs(D):
    """One row per ncpi0-stage event with the controlling candidate's pair inputs and the Phase-9 photon state."""
    st, c, E = D["st"], D["cand"], D["E"]
    pc = [x for x in c.columns if "kine_pio" in x or x.startswith("in_shw_sp_pio") or (x.startswith("in_") and x.endswith("_score") and x not in ("in_numu_1_score", "in_numu_score"))]
    cc = c[KEY + ["c_nu_index"] + pc]
    F = st.merge(cc, on=KEY + ["c_nu_index"], how="left", suffixes=("", "_c"), validate="one_to_one")
    ex = E[KEY + ["photon_trackid", "photon_q_readout", "n_truth_nu", "signal_nu_idx", "ph_start_x", "ph_start_y", "ph_start_z", "ph_end_x", "ph_end_y", "ph_end_z", "q_total", "q_in_cands", "dominant_fraction", "n_cand_with_photon"]]
    F = F.merge(ex, on=KEY, how="left", suffixes=("", "_t"), validate="one_to_one")
    return F


def recover_all(F, D):
    """Recover the kine_pio pair and the tagger-side pair of every ncpi0-stage event from the stored products.  Step 1 (energy signature + elimination + at-least-one-detached rule) gives ALL consistent
    configurations; step 2 removes configurations the stored distances contradict (particle-flow start points).  Nothing is chosen among configurations that remain."""
    k = D["kine"]; pf = D["pf"]
    gk = {key: d for key, d in k[k.kine_particle_is_shower == 1].groupby(KEY + ["cand_pos"])}
    gp = {key: d[d.kine_index >= 0].drop_duplicates("kine_index").set_index("kine_index") for key, d in pf.groupby(KEY + ["nu_index"])}

    def sp(p, rw):
        return p.loc[rw, ["start_x", "start_y", "start_z"]].values.astype(float) if p is not None and rw in p.index else None
    recs = []
    for r in F.itertuples():
        key = (int(r.file_index), int(r.ev), int(r.c_nu_index)); d = gk.get(key); p = gp.get(key)
        rec = dict(file_index=key[0], ev=key[1], c_nu_index=key[2])
        sel_e = r.shw_sp_energy
        for pair, flag_ok, (e1, e2, d1, d2) in (("kine", r.in_kine_pio_flag > 0, (r.in_kine_pio_energy_1, r.in_kine_pio_energy_2, r.in_kine_pio_dis_1, r.in_kine_pio_dis_2)),
                                                ("tagger", r.in_shw_sp_pio_flag_pio == 1, (r.in_shw_sp_pio_1_energy_1, r.in_shw_sp_pio_1_energy_2, r.in_shw_sp_pio_1_dis_1, r.in_shw_sp_pio_1_dis_2))):
            rec[pair + "_present"] = bool(flag_ok)
            if not flag_ok or d is None:
                rec[pair + "_class"] = "absent"; rec[pair + "_class_geom"] = "absent"; rec[pair + "_configs"] = []; rec[pair + "_configs_geom"] = []; rec[pair + "_n_exact"] = -1; continue
            cfg, nex = PA.consistent_pairs(d.row.values, d.kine_energy_particle.values, d.kine_energy_info.values, d.kine_particle_pool.values, e1, e2)
            rec[pair + "_class"] = PA.recovery_class(nex, len(cfg)); rec[pair + "_n_exact"] = nex; rec[pair + "_configs"] = cfg
            sts = [PA.geometry_status(sp(p, a), sp(p, b), d1, d2) for a, b in cfg]
            kept, flag = PA.refine_by_geometry(cfg, sts); rec[pair + "_geom_flag"] = flag; rec[pair + "_configs_geom"] = kept
            nk = len(unordered_keys(kept))
            rec[pair + "_class_geom"] = "unresolved" if not kept else ("ambiguous" if nk > 1 else ("unique_exact" if nex == 2 else ("unique_by_geometry" if len(unordered_keys(cfg)) > 1 else "unique_by_elimination")))
            if len(kept) == 1:
                a, b = kept[0]; sa, sb = sp(p, a), sp(p, b)
                if sa is not None and sb is not None:
                    L = float(np.linalg.norm(sa - sb)); rec[pair + "_sep_cm"] = L
                    rec[pair + "_geom_resid"] = (L - d2) if d1 < 1e-3 else ((L - d1) if d2 < 1e-3 else max(abs(d1 - d2) - L, L - (d1 + d2), 0.0))
            if pair == "tagger":       # source: the tagger-selected (max) shower is a member; shw_sp_energy is its energy
                ee = d[(d.kine_particle_type == 11)]
                selrows = set(ee.row.values[np.abs(ee.kine_energy_particle.values - sel_e) < 1e-5 * max(1.0, abs(sel_e))].tolist())
                rec["tagger_sel_rows"] = sorted(selrows); rec["tagger_sel_in_pair_n"] = int(sum(bool(selrows & set(c)) for c in kept))
        recs.append(rec)
    return pd.DataFrame(recs)


def unordered_keys(configs):
    return PA.unordered_pair_keys(configs)


def cp(k, n):
    """Observed fraction and a 68 % Clopper-Pearson-like interval via the Wilson score (descriptive)."""
    if n == 0:
        return float("nan"), float("nan"), float("nan")
    f = k / n; z = 1.0; den = 1 + z * z / n; c = (f + z * z / (2 * n)) / den; h = z * np.sqrt(f * (1 - f) / n + z * z / (4 * n * n)) / den
    return f, c - h, c + h


def outside_av_map(tnu):
    """{(file_index, ev, nu_idx): True} when the truth interaction's vertex is outside the provisional active-volume box (dirt / outside-AV neutrino)."""
    out = {}
    for r in tnu.itertuples():
        inside = AV["x"][0] < r.vtx_x < AV["x"][1] and AV["y"][0] < r.vtx_y < AV["y"][1] and AV["z"][0] < r.vtx_z < AV["z"][1]
        out[(int(r.file_index), int(r.ev), int(r.nu_idx))] = not inside
    return out


def build_rows(D, F):
    """Truth class of every T_kine row of the CONTROLLING candidate of every ncpi0-stage event (source-ranked T_match partner, no charge-IoU ranking)."""
    rm = D["rm"]; rm[KEY] = rm[KEY].astype(int)
    f = F[KEY + ["c_nu_index", "photon_trackid", "signal_nu_idx", "dom_nu", "dom_row"]]
    rows = rm.merge(f, on=KEY); rows = rows[rows.cand == rows.c_nu_index].copy()
    out_av = outside_av_map(D["tnu"]); cls = []
    for r in rows.itertuples():
        nuo = {int(r.p1_t_nu): out_av.get((r.file_index, r.ev, int(r.p1_t_nu)), False)} if np.isfinite(r.p1_t_nu) and r.p1_t_nu >= 0 else {}
        isdom = bool(np.isfinite(r.dom_nu) and int(r.dom_nu) == r.cand and int(r.dom_row) == r.row)
        cls.append(PA.row_truth_class(r.p1_tid, r.p1_t_pdg, r.p1_t_nu, r.p1_iou_n, r.p2_tid, r.p2_iou_n, r.p2_t_nu, r.photon_trackid, r.signal_nu_idx, isdom, nuo))
    rows["tclass"] = cls
    return rows


def pair_truth(F, R, rows):
    """Event-level truth of the recovered pairs: every consistent configuration is classified; a property that differs between configurations is reported as ``indeterminate``."""
    rc = {key: d.set_index("row") for key, d in rows.groupby(KEY + ["cand"])}
    recs = []
    for r in R.itertuples():
        key = (int(r.file_index), int(r.ev), int(r.c_nu_index)); d = rc.get(key); rec = dict(file_index=key[0], ev=key[1])
        for pair in ("kine", "tagger"):
            cfgs = getattr(r, pair + "_configs_geom")
            if not len(cfgs) or d is None:
                rec[pair + "_membership"] = "absent" if not getattr(r, pair + "_present") else "unresolved"; rec[pair + "_other"] = "n/a"; rec[pair + "_mem_classes"] = ""; continue
            keys = sorted({tuple(sorted(c)) for c in cfgs}); mems = [[d.tclass.get(x, "unmatched") for x in k] for k in keys]
            rec[pair + "_membership"] = PA.decide([PA.pair_signal_membership(m) for m in mems])
            rec[pair + "_other"] = PA.decide([PA.other_member_class(m) for m in mems])
            rec[pair + "_mem_classes"] = PA.decide(["|".join(sorted(m)) for m in mems]); rec[pair + "_n_unordered"] = len(keys)
        recs.append(rec)
    return pd.DataFrame(recs)


# ================================================================================================================== fragmentation (roadmap U)
def pieces_table(D):
    """All reconstructed pieces of the signal photon: one row per (event, candidate, T_kine row) holding signal-photon charge in T_overlap (trackid in the photon family; the Phase-9 definition),
    with the piece's charge fraction of the photon's in-candidate charge and the row's reconstructed type / pool / cluster.  ``kine_index == -1``: a piece without a particle row."""
    po = D["pho"].copy(); po["nu_index"] = po.nu_index.astype(int); po["kine_index"] = po.kine_index.astype(int)
    inc = po[po.nu_index >= 0]
    pc = inc.groupby(KEY + ["nu_index", "kine_index"]).agg(q=("q", "sum"), n_points=("n_points", "sum"), n_seg=("segment_id", "nunique"), cluster_id=("cluster_id", "first"), in_pf=("in_pf", "max"), in_enu=("in_enu", "max")).reset_index()
    qin = pc.groupby(KEY).q.sum().rename("q_in_cands").reset_index(); pc = pc.merge(qin, on=KEY); pc["frac"] = pc.q / pc.q_in_cands
    k = D["kine"].rename(columns={"cand_pos": "nu_index", "row": "kine_index"})[KEY + ["nu_index", "kine_index", "kine_particle_type", "kine_energy_particle", "kine_particle_is_shower", "kine_particle_pool", "kine_energy_included", "kine_particle_cluster_id", "kine_particle_nseg", "kine_energy_info"]]
    pc = pc.merge(k, on=KEY + ["nu_index", "kine_index"], how="left")
    pc["type"] = [PA.type_label(t, s == 1) if pd.notna(t) else "no particle row" for t, s in zip(pc.kine_particle_type, pc.kine_particle_is_shower)]
    return pc


def piece_locations(D, pcs):
    """Exclusive location of every significant (>= 10 % of in-candidate photon charge) NON-dominant piece relative to the Phase-9 dominant object, hierarchy (first match wins):
    other candidate -> other cluster of the same candidate -> no particle row -> under another particle (PF depth > 0 below a real particle) -> attached at the main vertex (PF root, PF child of a
    pseudo photon node, or pool 0/1 walk row) -> detached leftover shower of the same cluster (pool 2 / no PF node)."""
    E = D["E"].set_index(KEY)[["dom_nu", "dom_row"]]; pf = D["pf"].copy(); pf["nu_index"] = pf.nu_index.astype(int)
    pfn = pf[pf.kine_index >= 0].sort_values(KEY + ["nu_index", "kine_index", "depth"]).drop_duplicates(KEY + ["nu_index", "kine_index"])[KEY + ["nu_index", "kine_index", "node_id", "parent_id", "depth"]]
    par = pf[KEY + ["nu_index", "node_id", "parent_id", "is_pseudo"]].rename(columns={"node_id": "parent_id", "parent_id": "gp_id", "is_pseudo": "par_pseudo"}).drop_duplicates(KEY + ["nu_index", "parent_id"])
    q = pcs.merge(pfn, on=KEY + ["nu_index", "kine_index"], how="left").merge(par, on=KEY + ["nu_index", "parent_id"], how="left")
    q = q.merge(E.reset_index(), on=KEY, how="left"); q["is_dom"] = (q.nu_index == q.dom_nu) & (q.kine_index == q.dom_row)
    domcl = q[q.is_dom].groupby(KEY).cluster_id.first().rename("dom_cluster").reset_index(); q = q.merge(domcl, on=KEY, how="left")
    loc = []
    for r in q.itertuples():
        if r.is_dom:
            loc.append("dominant"); continue
        if r.nu_index != r.dom_nu:
            loc.append("in another candidate")
        elif pd.notna(r.dom_cluster) and r.cluster_id != r.dom_cluster:
            loc.append("in another cluster (same candidate)")
        elif r.kine_index < 0:
            loc.append("no particle row")
        elif pd.notna(r.node_id) and r.depth > 0 and not (r.par_pseudo == 1 and r.gp_id == -1):
            loc.append("under another particle")
        elif (pd.notna(r.node_id) and (r.depth == 0 or (r.par_pseudo == 1 and r.gp_id == -1))) or r.kine_particle_pool in (0, 1):
            loc.append("attached at the main vertex")
        else:
            loc.append("detached shower, same cluster")
    q["location"] = loc
    return q


def fragment_events(D, q):
    """Per event of the shower-stage population (``A_n20mev``): significant-piece multiplicity (10 % of the in-candidate photon charge; 5 / 20 % sensitivity), leading and subleading charge fractions,
    rows / tracks / candidates / clusters spanned, reconstructed type combination, and the fate by stage.  Phase-9's ``photon_fragmented`` (dominant fraction < 0.5) is kept unchanged."""
    E = D["E"]; ev = E[E.A_n20mev.astype(bool)].copy(); rec = []
    for key, d in q.groupby(KEY):
        d = d.sort_values("q", ascending=False); sg = d[d.frac >= PA.FRAGMENT_MIN_FRACTION]; oth = sg[~sg.is_dom]
        energies = sg.kine_energy_particle.fillna(0.0).values; es = energies.sum()
        rec.append(dict(file_index=key[0], ev=key[1], n_pieces_all=len(d), n_sig=len(sg), n_sig_5=int((d.frac >= 0.05).sum()), n_sig_20=int((d.frac >= 0.20).sum()), lead_frac=float(d.frac.iloc[0]), second_frac=float(d.frac.iloc[1]) if len(d) > 1 else 0.0,
                        n_cands=int(sg.nu_index.nunique()), n_clusters=int(sg.groupby("nu_index").cluster_id.nunique().sum()), n_rows=int((sg.kine_index >= 0).sum()), n_shower_rows=int((sg.kine_particle_is_shower == 1).sum()),
                        n_track_rows=int((sg.kine_particle_is_shower == 0).sum()), types="+".join(sorted(sg.type)), n_other_cand=int((oth.location == "in another candidate").sum()),
                        n_other_cluster=int((oth.location == "in another cluster (same candidate)").sum()), lead_energy_frac=float(energies.max() / es) if es > 0 else np.nan, e_sum_pieces=float(es), has_dom=bool(sg.is_dom.any())))
    return ev.merge(pd.DataFrame(rec), on=KEY, how="left")


# ================================================================================================================== pair tables
SUBS = ["tro_5", "tro_4", "tro_2", "tro_1", "stw_4", "stw_3", "stw_2", "sig_2", "sig_1", "pio_2", "lol_2", "lol_1", "br3_6", "br3_5", "br3_3"]
ORIGINS = ["same-photon pieces", "signal photon + signal proton/hadron", "signal photon + other signal EM", "signal photon + non-signal object", "pair without the signal photon", "indeterminate"]


def origin_class(membership, other):
    if membership in ("absent",):
        return "no pair"
    if membership in ("indeterminate", "unresolved") or other == "indeterminate":
        return "indeterminate"
    if membership == "contains_neither":
        return "pair without the signal photon"
    if membership == "contains_both_pieces":
        return "same-photon pieces"
    if other in ("signal_proton", "signal_other_hadron"):
        return "signal photon + signal proton/hadron"
    if other == "signal_other_EM":
        return "signal photon + other signal EM"
    return "signal photon + non-signal object"


def state3(clean_l, state):
    return "clean" if clean_l == "clean" else ("fragmented" if state == "photon_fragmented" else "other non-clean")


def survival_row(g, label, **kw):
    n = len(g); k = int(g.survive.sum()); f, lo, hi = cp(k, n)
    return dict(label=label, n=n, survive=k, rejected=n - k, survival=f, lo68=lo, hi68=hi, **kw)


def pair_blocks(F, R, T, rows, D):
    M = F.merge(R, on=KEY + ["c_nu_index"], validate="one_to_one").merge(T, on=KEY, validate="one_to_one")
    M["state3"] = [state3(a, b) for a, b in zip(M.clean_l, M.photon_object_state)]
    for p in ("kine", "tagger"):
        M[p + "_origin"] = [origin_class(a, b) for a, b in zip(M[p + "_membership"], M[p + "_other"])]
    M["kine_E1"] = M.in_kine_pio_energy_1; M["kine_E2"] = M.in_kine_pio_energy_2
    for p, (e1, e2) in (("kine", ("in_kine_pio_energy_1", "in_kine_pio_energy_2")), ("tagger", ("in_shw_sp_pio_1_energy_1", "in_shw_sp_pio_1_energy_2"))):
        M[p + "_asym"] = np.abs(M[e1] - M[e2]) / (M[e1] + M[e2])
    mass = {"kine": M.in_kine_pio_mass, "tagger": M.in_shw_sp_pio_1_mass}
    out = {}
    # ---- recovery
    rec = []
    for p in ("kine", "tagger"):
        pres = M[M[p + "_present"]]
        for lvl, col in (("energy signature + elimination", p + "_class"), ("+ stored-distance geometry", p + "_class_geom")):
            for c, n in pres[col].value_counts().items():
                rec.append(dict(pair=p, level=lvl, recovery_class=c, n=int(n), fraction=float(n / len(pres)), n_present=len(pres)))
    out["pair_recovery"] = pd.DataFrame(rec)
    val = []
    kp = M[M.kine_present & (M.kine_class != "unresolved")]
    for p in ("kine", "tagger"):
        pres = M[M[p + "_present"]]; gr = pres[p + "_geom_resid"].dropna() if p + "_geom_resid" in pres else pd.Series(dtype=float)
        val.append(dict(pair=p, metric="n pairs present", value=len(pres)))
        val.append(dict(pair=p, metric="both stored energies equal a stored row energy (exact, rel. 1e-5)", value=int((pres[p + "_n_exact"] == 2).sum())))
        val.append(dict(pair=p, metric="geometry testable (unique configuration with both PF start points)", value=int(len(gr))))
        if len(gr):
            val.append(dict(pair=p, metric="|distance residual| < 1e-3 cm", value=int((gr.abs() < 1e-3).sum())))
            val.append(dict(pair=p, metric="|distance residual| < 0.05 cm", value=int((gr.abs() < 0.05).sum())))
            val.append(dict(pair=p, metric="max |distance residual| cm", value=float(gr.abs().max())))
            val.append(dict(pair=p, metric="median |distance residual| cm", value=float(gr.abs().median())))
    pr = M[M.kine_present & np.isfinite(M.in_kine_pio_angle) & (M.in_kine_pio_energy_1 > 0) & (M.in_kine_pio_energy_2 > 0)]
    m_rec = np.sqrt(4 * pr.in_kine_pio_energy_1 * pr.in_kine_pio_energy_2 * np.sin(np.deg2rad(pr.in_kine_pio_angle) / 2) ** 2); dm = m_rec - pr.in_kine_pio_mass
    val += [dict(pair="kine", metric="stored mass vs sqrt(4 E1 E2 sin^2(angle/2)) from the stored energies and angle: |diff| < 1 MeV", value=int((dm.abs() < 1).sum())), dict(pair="kine", metric="same: events compared", value=len(pr)),
            dict(pair="kine", metric="same: median |diff| MeV", value=float(dm.abs().median())), dict(pair="kine", metric="same: max |diff| MeV", value=float(dm.abs().max()))]
    tg = M[M.tagger_present & (M.tagger_n_exact == 2) & (M.tagger_class != "unresolved")]
    val.append(dict(pair="tagger", metric="tagger-selected shower is a member of the recovered pair (events with a unique selected row and configuration)", value=int((tg.tagger_sel_in_pair_n > 0).sum()))); val.append(dict(pair="tagger", metric="same: events compared", value=len(tg)))
    out["pair_recovery_validation"] = pd.DataFrame(val)
    # ---- Task 7 / 8
    mem_order = ["contains_dominant", "contains_fragment_only", "contains_both_pieces", "contains_neither", "indeterminate", "unresolved", "absent"]
    t7 = []
    for p in ("kine", "tagger"):
        for pop, g in (("all", M), ("accepted", M[M.survive]), ("rejected", M[~M.survive])):
            for m in mem_order:
                n = int((g[p + "_membership"] == m).sum()); t7.append(dict(pair=p, population=pop, membership=m, n=n, fraction=n / len(g), n_population=len(g)))
    out["pair_membership"] = pd.DataFrame(t7)
    t8 = []
    for p in ("kine", "tagger"):
        d = M[M[p + "_membership"].isin(["contains_dominant", "contains_fragment_only", "contains_both_pieces"])]
        for (st, sv), g in d.groupby(["state3", "survive"]):
            for c, n in g[p + "_other"].map(lambda x: PA.HEADLINE.get(x, x)).value_counts().items():
                t8.append(dict(pair=p, photon_state=st, ncpi0="pass" if sv else "fail", second_member=c, n=int(n), n_group=len(g)))
    out["second_member"] = pd.DataFrame(t8)
    # ---- Task 9
    t9 = []
    for p in ("kine", "tagger"):
        for o in ORIGINS + ["no pair"]:
            g = M[M[p + "_origin"] == o]
            if o == "no pair" or not len(g):
                continue
            q = lambda s_: s_.dropna().quantile([0.16, 0.5, 0.84]).values if s_.notna().any() else [np.nan] * 3
            m_ = mass[p].loc[g.index]; E1 = M[("in_kine_pio_energy_1" if p == "kine" else "in_shw_sp_pio_1_energy_1")].loc[g.index]; E2 = M[("in_kine_pio_energy_2" if p == "kine" else "in_shw_sp_pio_1_energy_2")].loc[g.index]
            ang = g.in_kine_pio_angle if p == "kine" else 2 * np.rad2deg(np.arcsin(np.clip(m_ / (2 * np.sqrt(E1 * E2)), 0, 1)))
            d1 = g["in_kine_pio_dis_1" if p == "kine" else "in_shw_sp_pio_1_dis_1"]; d2 = g["in_kine_pio_dis_2" if p == "kine" else "in_shw_sp_pio_1_dis_2"]
            t9.append(dict(pair=p, origin=o, n=len(g), survive=int(g.survive.sum()), survival=float(g.survive.mean()), mass_p16=q(m_)[0], mass_median=q(m_)[1], mass_p84=q(m_)[2], frac_mass_100_170=float(((m_ > 100) & (m_ < 170)).mean()),
                           frac_mass_75_195=float(((m_ > 75) & (m_ < 195)).mean()), angle_median=q(ang)[1], E1_median=q(E1)[1], E2_median=q(E2)[1], asym_median=q(g[p + "_asym"])[1], dis_min_median=q(np.minimum(d1, d2))[1], dis_max_median=q(np.maximum(d1, d2))[1],
                           sep_median=q(g[p + "_sep_cm"] if p + "_sep_cm" in g else pd.Series(dtype=float))[1]))
    out["fake_pi0_mass_by_origin"] = pd.DataFrame(t9)
    out["survival_by_origin"] = pd.DataFrame([survival_row(M[M[p + "_origin"] == o], o, pair=p) for p in ("kine", "tagger") for o in ORIGINS + ["no pair"] if (M[p + "_origin"] == o).any()])
    # ---- Task 10: kine vs tagger
    rel = []
    for r in M.itertuples():
        if not (r.kine_present and r.tagger_present):
            rel.append("neither" if not (r.kine_present or r.tagger_present) else ("kine only" if r.kine_present else "tagger only")); continue
        K_ = {tuple(sorted(c)) for c in r.kine_configs_geom}; T_ = {tuple(sorted(c)) for c in r.tagger_configs_geom}
        if not K_ or not T_:
            rel.append("both: unresolved"); continue
        vals = set("same pair" if k == t else ("share one member" if len(set(k) & set(t)) == 1 else "different pairs") for k in K_ for t in T_)
        rel.append("both: " + (next(iter(vals)) if len(vals) == 1 else "unresolved"))
    M["kine_vs_tagger"] = rel
    out["kine_vs_tagger"] = pd.DataFrame([survival_row(g, c) for c, g in M.groupby("kine_vs_tagger")])
    return M, out


def other_blocks(M, D, rows):
    """Task 11 (upstream sub-BDTs), 16 (fragmentation <-> ncpi0), 18 (clean-photon failures), 19 / 20 (topology, Delta charge, proton origin)."""
    out = {}
    M["origin_any"] = np.where(M.tagger_present, M.tagger_origin, M.kine_origin)
    # ---- Task 11: descriptive only.  Each upstream sub-BDT score has a producer default (the mode: inputs not filled); a score is "evaluated" when it differs from it and "background-like" when it is < 0.
    cols = [f"in_{s}_score" for s in SUBS]; modes = {c: M[c].mode().iloc[0] for c in cols}
    ev_ = pd.DataFrame({c: (M[c] != modes[c]) for c in cols}); neg = pd.DataFrame({c: (M[c] < 0) for c in cols})
    M["n_sub_evaluated"] = ev_.sum(axis=1); M["n_sub_negative"] = neg.sum(axis=1)
    grp = np.where(~M.kine_present & ~M.tagger_present, "no pair flag", np.where(M.tagger_present, "tagger (mass-window) pair", "kine pair only"))
    M["pair_group"] = grp; t11 = []
    for g_, d in M.groupby("pair_group"):
        for sv in (True, False):
            x = d[d.survive == sv]
            if len(x) < 5:
                continue
            rec = dict(pair_group=g_, ncpi0="pass" if sv else "fail", n=len(x), median_ncpi0_score=float(x.stage_score.median()), mean_n_subscores_evaluated=float(x.n_sub_evaluated.mean()), mean_n_subscores_background_like=float(x.n_sub_negative.mean()),
                       frac_with_any_background_like=float((x.n_sub_negative > 0).mean()))
            for c in cols:
                k = c.replace("in_", "").replace("_score", ""); rec["neg_" + k] = float((x[c] < 0).mean())
            t11.append(rec)
    out["upstream_by_pair_group"] = pd.DataFrame(t11)
    t11b = []
    for o in ORIGINS:
        g = M[M.origin_any == o]
        if len(g) >= 5:
            t11b.append(dict(origin=o, n=len(g), survival=float(g.survive.mean()), median_ncpi0_score=float(g.stage_score.median()), mean_n_subscores_background_like=float(g.n_sub_negative.mean()), frac_with_any_background_like=float((g.n_sub_negative > 0).mean())))
    out["upstream_by_origin"] = pd.DataFrame(t11b)
    # ---- Task 16
    t16 = []
    for st_, g in M.groupby("state3"):
        sigpair = lambda p: g[p + "_membership"].isin(["contains_dominant", "contains_fragment_only", "contains_both_pieces"])
        frag = lambda p: g[p + "_membership"].isin(["contains_fragment_only", "contains_both_pieces"])
        t16.append(dict(photon_state=st_, n=len(g), survive=int(g.survive.sum()), rejected=int((~g.survive).sum()), survival=float(g.survive.mean()), kine_pair=int(g.kine_present.sum()), tagger_pair=int(g.tagger_present.sum()),
                        kine_pair_contains_signal_photon=int(sigpair("kine").sum()), tagger_pair_contains_signal_photon=int(sigpair("tagger").sum()), kine_pair_has_same_photon_fragment=int(frag("kine").sum()),
                        tagger_pair_has_same_photon_fragment=int(frag("tagger").sum()), rejected_with_kine_pair=int((~g.survive & g.kine_present).sum()), rejected_with_tagger_pair=int((~g.survive & g.tagger_present).sum()),
                        rejected_pair_has_same_photon_fragment_either=int((~g.survive & (frag("kine") | frag("tagger"))).sum())))
    out["fragmentation_vs_ncpi0"] = pd.DataFrame(t16)
    rj = M[~M.survive]; fragev = rj.state3 == "fragmented"; pf_ = lambda p: rj[p + "_membership"].isin(["contains_fragment_only", "contains_both_pieces"])
    out["rejected_attribution"] = pd.DataFrame([
        dict(measure="rejected events (all)", n=len(rj)), dict(measure="rejected, any pair flag (kine or tagger)", n=int((rj.kine_present | rj.tagger_present).sum())),
        dict(measure="rejected, a pair contains the signal photon (dominant or fragment), either pair", n=int(rj.kine_membership.isin(["contains_dominant", "contains_fragment_only", "contains_both_pieces"]).__or__(rj.tagger_membership.isin(["contains_dominant", "contains_fragment_only", "contains_both_pieces"])).sum())),
        dict(measure="rejected, Phase-9 photon state = fragmented (event-level fragmentation)", n=int(fragev.sum())), dict(measure="rejected, a pair contains a same-photon fragment (kine or tagger)", n=int((pf_("kine") | pf_("tagger")).sum())),
        dict(measure="rejected, both fragmented (Phase 9) AND a pair contains a same-photon fragment", n=int((fragev & (pf_("kine") | pf_("tagger"))).sum())),
        dict(measure="rejected, clean photon (Phase 9) and a pair flag", n=int(((rj.state3 == "clean") & (rj.kine_present | rj.tagger_present)).sum())), dict(measure="rejected, clean photon (Phase 9) and no pair flag", n=int(((rj.state3 == "clean") & ~(rj.kine_present | rj.tagger_present)).sum())),
        dict(measure="rejected, clean photon (Phase 9) and a pair containing the signal photon and a non-photon second member", n=int(((rj.state3 == "clean") & (rj.origin_any.isin(["signal photon + signal proton/hadron", "signal photon + other signal EM", "signal photon + non-signal object"]))).sum()))])
    # ---- Task 18
    cf = M[(M.state3 == "clean")].copy()
    rn = rows.groupby(KEY + ["cand"]).apply(lambda d: pd.Series(dict(n_rows=len(d), n_other_nu_or_cosmic_rows_gt5=int(((d.tclass.isin(["other_nu_EM", "other_nu_hadron", "cosmic", "dirt_outside_AV_nu"])) & (d.ke > 5)).sum()),
                                                                     n_signal_proton_rows=int((d.tclass == "signal_proton").sum())))).reset_index().rename(columns={"cand": "c_nu_index"})
    cf = cf.merge(rn, on=KEY + ["c_nu_index"], how="left")
    t18 = []
    for lab, g in (("clean, ncpi0 rejected", cf[~cf.survive]), ("clean, ncpi0 accepted", cf[cf.survive])):
        t18.append(dict(population=lab, n=len(g), kine_pair=float(g.kine_present.mean()), tagger_pair=float(g.tagger_present.mean()), no_pair_flag=float((~g.kine_present & ~g.tagger_present).mean()),
                        pair_contains_signal_photon=float((g.kine_membership.isin(["contains_dominant", "contains_fragment_only", "contains_both_pieces"]) | g.tagger_membership.isin(["contains_dominant", "contains_fragment_only", "contains_both_pieces"])).mean()),
                        median_n_candidates=float(g.n_candidates_total.median()), frac_multi_candidate=float((g.n_candidates_total > 1).mean()), frac_anchored_5cm=float(g.anchored5.astype(float).mean()), median_vertex_dist_cm=float(g.d_vertex.median()),
                        frac_other_nu_or_cosmic_row=float((g.n_other_nu_or_cosmic_rows_gt5 > 0).mean()), frac_other_truth_nu_in_window=float((g.n_truth_nu > 1).mean()), frac_truth_0p=float((g.truth35 == 0).mean()), frac_truth_1p=float((g.truth35 == 1).mean()), frac_truth_ge2p=float((g.truth35 >= 2).mean()),
                        median_kine_mass=float(g.in_kine_pio_mass[g.kine_present].median()), median_tagger_mass=float(g.in_shw_sp_pio_1_mass[g.tagger_present].median()),
                        median_stage_score=float(g.stage_score.median())))
    out["clean_photon_failures"] = pd.DataFrame(t18)
    cfr = cf[~cf.survive]
    out["clean_photon_failures_origin"] = pd.DataFrame([dict(pair=p, origin=o, n=int((cfr[p + "_origin"] == o).sum()), fraction=float((cfr[p + "_origin"] == o).mean())) for p in ("kine", "tagger") for o in ORIGINS + ["no pair"]])
    sec = []
    for p in ("kine", "tagger"):
        d = cfr[cfr[p + "_membership"].isin(["contains_dominant", "contains_fragment_only", "contains_both_pieces"])]
        for c, n in d[p + "_other"].map(lambda x: PA.HEADLINE.get(x, x)).value_counts().items():
            sec.append(dict(pair=p, second_member=c, n=int(n), fraction=float(n / len(d)), n_group=len(d)))
    out["clean_photon_second_member"] = pd.DataFrame(sec)
    # ---- Task 19 / 20
    topo = {0: "truth 0p", 1: "truth 1p", 2: "truth >=2p"}; M["topology"] = M.truth35.map(lambda x: topo[min(int(x), 2)])
    t19 = []
    for tp, g in M.groupby("topology"):
        for p in ("kine", "tagger"):
            pres = g[g[p + "_present"]]
            sig = pres[pres[p + "_membership"].isin(["contains_dominant", "contains_fragment_only", "contains_both_pieces"])]
            t19.append(dict(topology=tp, pair=p, n_events=len(g), survival=float(g.survive.mean()), pair_present=len(pres), pair_present_fraction=float(len(pres) / len(g)), contains_signal_photon=len(sig),
                            second_signal_proton_or_hadron=int(sig[p + "_other"].isin(["signal_proton", "signal_other_hadron"]).sum()), second_other_signal_EM=int((sig[p + "_other"] == "signal_other_EM").sum()),
                            second_same_photon_fragment=int((sig[p + "_other"] == "signal_photon_fragment").sum()), second_non_signal=int(sig[p + "_other"].isin(["other_nu_EM", "other_nu_hadron", "cosmic", "dirt_outside_AV_nu", "unmatched", "ambiguous_mixed"]).sum()),
                            n_fragmented_photon=int((g.state3 == "fragmented").sum()), survival_with_pair=float(pres.survive.mean()) if len(pres) else np.nan, survival_without_pair=float(g[~g[p + "_present"]].survive.mean())))
    out["topology"] = pd.DataFrame(t19)
    t20 = []
    for dl, g in M.groupby("delta_label"):
        for p in ("kine", "tagger"):
            pres = g[g[p + "_present"]]; t20.append(dict(group="delta " + str(dl), pair=p, n=len(g), survival=float(g.survive.mean()), pair_present=int(len(pres)), pair_present_fraction=float(len(pres) / len(g)),
                                                          second_signal_proton=int((pres[p + "_other"] == "signal_proton").sum()), pair_contains_signal_photon=int(pres[p + "_membership"].isin(["contains_dominant", "contains_fragment_only", "contains_both_pieces"]).sum())))
    p1 = M[M.truth35 == 1]
    for po, g in p1.groupby("proton_origin"):
        for p in ("kine", "tagger"):
            pres = g[g[p + "_present"]]; t20.append(dict(group="truth 1p, proton origin " + str(po), pair=p, n=len(g), survival=float(g.survive.mean()), pair_present=int(len(pres)), pair_present_fraction=float(len(pres) / len(g)),
                                                          second_signal_proton=int((pres[p + "_other"] == "signal_proton").sum()), pair_contains_signal_photon=int(pres[p + "_membership"].isin(["contains_dominant", "contains_fragment_only", "contains_both_pieces"]).sum())))
    out["delta_and_proton_origin"] = pd.DataFrame(t20)
    return M, out


STAGES = [("shower stage (> 20 MeV shower)", "A_n20mev"), ("BDT evaluable", "A_bdt_evaluable"), ("numu", "A_numu"), ("other", "A_other"), ("ncpi0", "A_ncpi0"), ("nue", "A_nue"), ("n_20br1 == 1", "A_n20br1"), ("final", "A_final")]


def stage_fate(fe):
    """Event counts through the frozen chain and the FIRST stage that removes each event (cumulative flags of the validated baseline)."""
    fe = fe.copy(); flags = [c for _, c in STAGES]
    fe["first_loss"] = "final"
    for (name, c), (_, prev) in reversed(list(zip(STAGES[1:], STAGES[:-1]))):
        fe.loc[~fe[c].astype(bool), "first_loss"] = name
    fe.loc[~fe.A_n20mev.astype(bool), "first_loss"] = "not at shower stage"
    return fe


def frag_blocks(D, M, q, fe, rows):
    out = {}; fe = stage_fate(fe); fe["state3"] = ["clean" if (a == "pass_photon_shower_in_passing_candidate") else ("fragmented" if b == "photon_fragmented" else "other non-clean") for a, b in zip(fe.outcome, fe.photon_object_state)]
    fr = fe[fe.photon_object_state == "photon_fragmented"]; cl = fe[fe.outcome == "pass_photon_shower_in_passing_candidate"]
    # ---- definition / multiplicity (Task 12)
    out["fragmentation_definition"] = pd.DataFrame([
        dict(item="Phase-9 fragmented state", value=f"dominant (candidate, T_kine row) holds < {0.5} of the photon's in-candidate charge (T_overlap, signal-photon trackid family)", n=int(len(fr))),
        dict(item="significant piece (Phase 14, descriptive)", value=f">= {PA.FRAGMENT_MIN_FRACTION} of the photon's in-candidate charge, per (candidate, T_kine row); 5 % and 20 % sensitivities in the multiplicity table", n=int(len(q[q.frac >= PA.FRAGMENT_MIN_FRACTION]))),
        dict(item="event population", value="official Gen2 NC-Delta TPC-box events with a > 20 MeV shower (A_n20mev)", n=int(len(fe)))])
    def dist(g, lab):
        return dict(population=lab, n=len(g), n_sig_mean=float(g.n_sig.mean()), n_sig_median=float(g.n_sig.median()), n_sig_5_mean=float(g.n_sig_5.mean()), n_sig_20_mean=float(g.n_sig_20.mean()), lead_frac_median=float(g.lead_frac.median()), second_frac_median=float(g.second_frac.median()),
                    rows_median=float(g.n_rows.median()), shower_rows_median=float(g.n_shower_rows.median()), track_rows_median=float(g.n_track_rows.median()), cands_mean=float(g.n_cands.mean()), clusters_median=float(g.n_clusters.median()), frac_multi_cluster=float((g.n_clusters > 1).mean()),
                    frac_multi_candidate=float((g.n_cands > 1).mean()), frac_with_piece_without_row=float(g.types.str.contains("no particle row").mean()), lead_energy_frac_median=float(g.lead_energy_frac.median()))
    out["fragment_multiplicity"] = pd.DataFrame([dist(fr, "fragmented (Phase 9)"), dist(cl, "clean (Phase 9)"), dist(fe[fe.state3 == "other non-clean"], "other non-clean")])
    out["fragment_multiplicity_hist"] = fr.n_sig.value_counts().sort_index().rename_axis("n_significant_pieces").reset_index(name="n_events")
    # ---- types (Task 13)
    out["fragment_type_combinations"] = fr.types.value_counts().rename_axis("types").reset_index(name="n").assign(fraction=lambda d: d.n / len(fr))
    has = lambda pat: fr.types.str.contains(pat)
    ne = fr.types.str.count("electron shower")
    broad = {"e + e only (2 pieces)": (fr.n_sig == 2) & (fr.types == "electron shower+electron shower"), "e + muon-like": has("muon-like") & ~has("pion-like") & ~has("proton-like"), "e + pion-like": has("pion-like") & ~has("muon-like") & ~has("proton-like"),
             "e + proton-like": has("proton-like"), "any track-typed piece (muon/pion/proton/e-track)": has("muon-like") | has("pion-like") | has("proton-like") | has("electron track"), "track + shower (>= 1 each)": (fr.n_track_rows > 0) & (fr.n_shower_rows > 0),
             ">= 3 significant pieces": fr.n_sig >= 3, "has a piece without a particle row": has("no particle row"), ">= 2 electron-typed showers": ne >= 2}
    out["fragment_type_broad"] = pd.DataFrame([dict(category=k, n=int(v.sum()), fraction=float(v.mean())) for k, v in broad.items()])
    # ---- where do the pieces go (Task 14)
    sp = q[(q.frac >= PA.FRAGMENT_MIN_FRACTION) & ~q.is_dom].merge(fr[KEY], on=KEY)
    out["fragment_location_pieces"] = sp.location.value_counts().rename_axis("location").reset_index(name="n_pieces").assign(fraction=lambda d: d.n_pieces / len(sp))
    ev_loc = sp.groupby(KEY).location.apply(lambda s_: sorted(set(s_))).reset_index()
    out["fragment_location_events"] = pd.DataFrame([dict(location=l, n_events=int(ev_loc.location.apply(lambda x: l in x).sum()), fraction=float(ev_loc.location.apply(lambda x: l in x).sum() / len(fr))) for l in sp.location.unique()]).sort_values("n_events", ascending=False)
    ph = D["E"].set_index(KEY); q_out = (ph.loc[fr.set_index(KEY).index, "q_total"].values - ph.loc[fr.set_index(KEY).index, "q_in_cands"].values) / np.maximum(ph.loc[fr.set_index(KEY).index, "q_total"].values, 1)
    out["fragment_outside_candidates"] = pd.DataFrame([dict(item="median fraction of the photon's reconstructed charge outside every candidate (fragmented events)", value=float(np.median(q_out))), dict(item="events with > 20 % outside every candidate", value=int((q_out > 0.2).sum()))])
    # Phase-9 category cross-tab (the dominant object of a fragmented event has no state of its own, so the cross-tab is by the dominant object's type / PF state)
    out["fragment_dominant_object"] = fr.assign(dom_type=[PA.type_label(t, s == 1) if pd.notna(t) else "no particle row" for t, s in zip(fr.kine_particle_type, fr.kine_particle_is_shower)]).groupby(["dom_type", "pf_state"]).size().rename("n").reset_index().sort_values("n", ascending=False)
    # ---- fate (Task 15)
    fate = []
    for pop, g in (("fragmented", fr), ("clean", cl), ("all shower-stage events", fe)):
        prev = None
        for name, c in STAGES:
            n = int(g[c].astype(bool).sum()); fate.append(dict(population=pop, stage=name, n_reaching_or_passing=n, step_survival=(n / prev) if prev else np.nan, cumulative=n / len(g))); prev = n
    out["fragment_stage_fate"] = pd.DataFrame(fate)
    out["fragment_first_loss"] = pd.DataFrame([dict(population=pop, first_loss=k, n=int(v), fraction=float(v / len(g))) for pop, g in (("fragmented", fr), ("clean", cl)) for k, v in g.first_loss.value_counts().items()])
    cand = D["cand"].rename(columns={"c_nu_index": "dom_nu"})
    keep = [c for c in ("in_shw_sp_shw_vtx_dis", "numu_score", "c_score_other") if c in cand.columns]
    d2 = fr.merge(cand[KEY + ["dom_nu"] + keep], on=KEY + ["dom_nu"], how="left", suffixes=("", "_cand"))
    mech = []
    for st_, g in d2.groupby("first_loss"):
        mech.append(dict(first_loss=st_, n=len(g), n_sig_median=float(g.n_sig.median()), lead_frac_median=float(g.lead_frac.median()), frac_with_muon_pion_piece=float((g.types.str.contains("muon-like") | g.types.str.contains("pion-like")).mean()),
                         frac_dominant_not_electron_shower=float(1 - ((g.kine_particle_type == 11) & (g.kine_particle_is_shower == 1)).mean()),
                         frac_piece_in_other_cluster=float((g.n_other_cluster > 0).mean()), dominant_E_median=float(g.kine_energy_particle.median()), vtx_gap_median=float(g.get("in_shw_sp_shw_vtx_dis", pd.Series(dtype=float)).median()),
                         numu_score_median=float(g.get("numu_score", pd.Series(dtype=float)).median())))
    out["fragment_stage_mechanism"] = pd.DataFrame(mech)
    return out, fe


def n20br1_overlap(D, fe, rows):
    """Task 17: how the 126 n_20br1 failures with an extra shower row attributed to the signal photon map onto the Phase-9 fragmentation taxonomy."""
    n = pd.read_parquet(P12 / "n20br1_stage.parquet"); n[KEY] = n[KEY].astype(int)
    fq = fe[KEY + ["n_sig", "n_sig_5", "lead_frac", "second_frac", "state3", "photon_object_state"]]
    m = n.merge(fq, on=KEY, how="left", suffixes=("", "_f"))
    ex = m[m.extra_signal_photon > 0].copy()
    cls = np.where(ex.photon_object_state_f == "photon_fragmented", "already fragmented at the shower stage (Phase 9)", np.where(ex.n_sig >= 2, "clean at Phase 9, second significant piece (>= 10 % charge) below the 50 % dominance threshold", np.where(ex.n_sig_5 >= 2, "clean at Phase 9, second piece 5-10 % of the photon charge", "clean at Phase 9, extra row carries < 5 % of the photon charge or is not a charge piece")))
    ex["mapping"] = cls
    t = ex.mapping.value_counts().rename_axis("mapping").reset_index(name="n").assign(fraction=lambda d: d.n / len(ex))
    base = pd.DataFrame([dict(item="n_20br1 failures", n=len(m)), dict(item="with an extra shower row attributed to the signal photon (T_match top partner)", n=len(ex)), dict(item="without", n=len(m) - len(ex))])
    stt = m.groupby("photon_object_state_f").size().rename("n").reset_index()
    return t, base, stt, ex


def natural_check():
    n = pd.read_parquet(P12 / "raw" / "natural_candidates.parquet"); o = pd.read_parquet(P12 / "raw" / "official_candidates.parquet")
    f = lambda d: d[(d.shw_sp_filled > 0) & (d.shw_sp_n_20mev_showers > 0)]
    rec = []
    for lab, d in (("natural NC-Delta CV (rehearsal region)", f(n)), ("official Gen2 NC-Delta", f(o))):
        rec.append(dict(sample=lab, n_candidates_at_shower_stage=len(d), kine_pair_flag_fraction=float((d.in_kine_pio_flag > 0).mean()), tagger_pair_flag_fraction=float((d.in_shw_sp_pio_flag_pio == 1).mean()),
                        median_ncpi0_score=float(d.ncpi0_score.median())))
    return pd.DataFrame(rec)


def object_map(D, rows, R):
    """Task 3: reconstructed-object map of the controlling candidate of every ncpi0-stage event: T_kine row (type, pool, included, energy, cluster, nseg), PF node (depth, start point), source-ranked T_match partner
    and truth class, whether the row is the Phase-9 dominant signal-photon object, and whether it belongs to a recovered kine / tagger pair (any consistent configuration).  Shower DIRECTION is not stored per row
    in the flatCAF (it is recomputed from shower points inside the reconstruction), so it is not part of the map."""
    k = D["kine"].rename(columns={"cand_pos": "cand", "row": "row"})[KEY + ["cand", "row", "kine_particle_nseg"]]
    pf = D["pf"]; pf = pf[pf.kine_index >= 0].sort_values(KEY + ["nu_index", "kine_index", "depth"]).drop_duplicates(KEY + ["nu_index", "kine_index"]).rename(columns={"nu_index": "cand", "kine_index": "row"})[KEY + ["cand", "row", "node_id", "depth", "start_x", "start_y", "start_z"]]
    o = rows.merge(k, on=KEY + ["cand", "row"], how="left").merge(pf, on=KEY + ["cand", "row"], how="left")
    memb = {}
    for r in R.itertuples():
        for pair in ("kine", "tagger"):
            for a, b in getattr(r, pair + "_configs_geom"):
                memb.setdefault((r.file_index, r.ev, r.c_nu_index, a), set()).add(pair); memb.setdefault((r.file_index, r.ev, r.c_nu_index, b), set()).add(pair)
    o["in_kine_pair_any_config"] = [("kine" in memb.get((a, b, c, d), ())) for a, b, c, d in zip(o.file_index, o.ev, o.cand, o.row)]
    o["in_tagger_pair_any_config"] = [("tagger" in memb.get((a, b, c, d), ())) for a, b, c, d in zip(o.file_index, o.ev, o.cand, o.row)]
    o["is_dominant_photon_object"] = (o.dom_nu == o.cand) & (o.dom_row == o.row)
    return o


# ================================================================================================================== figures
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sbnd_single_photon import plotstyle as PS
PROV = "official Gen2 NC-Delta | frozen inherited selection (policy any) | events reaching ncpi0 (controlling candidate) | TPC-box, no FV | descriptive audit, no cut changed"
COL = {"same signal photon (dominant)": "#009E73", "same signal photon fragment": "#56B4E9", "other EM from signal interaction": "#E69F00", "signal proton / hadronic object": "#D55E00", "other-neutrino EM object": "#CC79A7",
       "other-neutrino hadronic object": "#8c564b", "dirt / outside-AV neutrino": "#7f7f7f", "cosmic": "#000000", "unmatched": "#bbbbbb", "ambiguous / mixed": "#F0E442", "indeterminate": "#dddddd"}
ORICOL = dict(zip(ORIGINS + ["no pair"], ["#56B4E9", "#D55E00", "#E69F00", "#CC79A7", "#000000", "#bbbbbb", "#009E73"]))


def save(fig, name):
    PS.annotate(fig, PROV, extra=PS.PRELIM); fig.savefig(PLT / name, bbox_inches="tight"); plt.close(fig)


def figures(M, rows, T8, fe, tabs, ex):
    # 1. member truth taxonomy accepted vs rejected (member-level, recovered unique pairs only)
    fig, ax = PS.figure(1, 2, size=(12, 4.2))
    for j, p in enumerate(("kine", "tagger")):
        a = ax[0][j]; d = M[M[p + "_present"] & M[p + "_class_geom"].isin(["unique_exact", "unique_by_elimination", "unique_by_geometry"])]
        cats = list(PA.HEADLINE.values()); cats = list(dict.fromkeys(cats)); w = 0.38
        for k, (sv, lab) in enumerate(((True, "accepted"), (False, "rejected"))):
            g = d[d.survive == sv]; mem = [PA.HEADLINE.get(c, c) for x in g[p + "_mem_classes"] if isinstance(x, str) and x for c in x.split("|")]
            vc = pd.Series(mem).value_counts(); tot = max(vc.sum(), 1)
            a.bar(np.arange(len(cats)) + (k - 0.5) * w, [vc.get(c, 0) / tot for c in cats], w, label=f"ncpi0 {lab} ({len(g)} pairs)", color=["#0072B2", "#D55E00"][k])
        a.set_xticks(np.arange(len(cats))); a.set_xticklabels(cats, rotation=60, ha="right", fontsize=7); a.set_ylabel("fraction of pair members"); a.set_title(("kine_pio pair" if p == "kine" else "tagger (mass-window) pair") + ": member truth, uniquely recovered pairs"); a.legend()
    fig.tight_layout(); save(fig, "fig1_pair_member_truth_accepted_vs_rejected.png")
    # 2. second member when the pair contains the signal photon: clean vs fragmented
    fig, ax = PS.figure(1, 2, size=(12, 4.4))
    for j, p in enumerate(("kine", "tagger")):
        a = ax[0][j]; t = T8[T8.pair == p]; cats = [c for c in COL if c in set(t.second_member)]; x = np.arange(2); bottom = np.zeros(2); gs = ["clean", "fragmented"]
        for c in cats:
            v = [t[(t.photon_state == g) & (t.second_member == c)].n.sum() / max(t[t.photon_state == g].n.sum(), 1) for g in gs]; a.bar(x, v, 0.6, bottom=bottom, color=COL[c], edgecolor="white", label=c); bottom += v
        a.set_xticks(x); a.set_xticklabels([f"{g}\n(n={int(t[t.photon_state == g].n.sum())})" for g in gs]); a.set_ylabel("fraction of pairs containing the signal photon"); a.set_title(("kine_pio" if p == "kine" else "tagger") + ": identity of the other member")
        if j == 1:
            a.legend(fontsize=6, loc="upper left", bbox_to_anchor=(1.0, 1.0))
    fig.tight_layout(); save(fig, "fig2_second_member_clean_vs_fragmented.png")
    # 3. overlap matrix: kine pair (rows) x tagger pair (columns), counts and ncpi0 survival; right panel: the 'both' events by relation
    fig, ax = PS.figure(1, 2, size=(11.5, 4.2), sharey=False); a = ax[0][0]
    cnt = np.zeros((2, 2)); sv = np.zeros((2, 2))
    for i_, kp_ in enumerate((False, True)):
        for j_, tp_ in enumerate((False, True)):
            g = M[(M.kine_present == kp_) & (M.tagger_present == tp_)]; cnt[i_, j_] = len(g); sv[i_, j_] = g.survive.mean() if len(g) else np.nan
    im = a.imshow(sv, vmin=0, vmax=1, cmap="Blues", aspect="auto")
    for i_ in range(2):
        for j_ in range(2):
            a.text(j_, i_, f"{int(cnt[i_, j_])} events\nsurvival {sv[i_, j_]:.3f}", ha="center", va="center", fontsize=9, color="white" if sv[i_, j_] > 0.6 else "black")
    a.set_xticks([0, 1]); a.set_xticklabels(["no tagger pair", "tagger pair"]); a.set_yticks([0, 1]); a.set_yticklabels(["no kine pair", "kine pair"]); a.grid(False); a.set_title("pair presence (colour = ncpi0 survival)")
    kv = tabs["kine_vs_tagger"]; both = kv[kv.label.str.startswith("both")].sort_values("n", ascending=True); b_ = ax[0][1]
    b_.barh([l.replace("both: ", "") for l in both.label], both.n, color="#56B4E9")
    for k_, (n_, s_) in enumerate(zip(both.n, both.survival)):
        b_.text(n_, k_, f"  {int(n_)} (survival {s_:.2f})", va="center", fontsize=8)
    b_.set_xlabel("events with both pairs"); b_.set_title("the two pairs when both exist"); b_.set_xlim(0, both.n.max() * 1.6); fig.tight_layout(); save(fig, "fig3_kine_vs_tagger_overlap.png")
    # 4. reconstructed pair mass by origin
    fig, ax = PS.figure(1, 2, size=(12, 4.2)); bins = np.linspace(0, 400, 41)
    for j, p in enumerate(("kine", "tagger")):
        a = ax[0][j]; mass = M.in_kine_pio_mass if p == "kine" else M.in_shw_sp_pio_1_mass
        for o in ORIGINS:
            g = M[(M[p + "_origin"] == o)]
            if len(g) >= 10:
                a.hist(mass.loc[g.index].clip(upper=399), bins=bins, histtype="step", lw=1.6, color=ORICOL[o], label=f"{o} (n={len(g)})")
        a.axvspan(100, 170, color="0.9", zorder=0); a.set_xlabel("stored pair mass [MeV]"); a.set_ylabel("events"); a.set_title("kine_pio pair" if p == "kine" else "tagger pair"); a.legend(fontsize=6)
    fig.tight_layout(); save(fig, "fig4_pair_mass_by_origin.png")
    # 5. survival by origin
    so = tabs["survival_by_origin"]; fig, ax = PS.figure(1, 2, size=(12, 4.2))
    for j, p in enumerate(("kine", "tagger")):
        a = ax[0][j]; d = so[so.pair == p].reset_index(drop=True); y = np.arange(len(d))
        a.barh(y, d.survival, color=[ORICOL.get(o, "0.5") for o in d.label]); a.errorbar(d.survival, y, xerr=[d.survival - d.lo68, d.hi68 - d.survival], fmt="none", color="k", lw=0.8); a.set_yticks(y); a.set_yticklabels([f"{l} (n={n})" for l, n in zip(d.label, d.n)], fontsize=7); a.invert_yaxis()
        a.set_xlabel("ncpi0 survival (frozen threshold)"); a.set_title(("kine_pio" if p == "kine" else "tagger") + " pair origin"); a.set_xlim(0, 1)
    fig.tight_layout(); save(fig, "fig5_ncpi0_survival_by_pair_origin.png")
    # 6. type combinations of fragmented photons
    tc = tabs["fragment_type_combinations"].head(14); fig, ax = PS.figure(1, 1, size=(8.5, 4.6)); a = ax[0][0]; y = np.arange(len(tc))
    a.barh(y, tc.n, color="#8c564b"); a.set_yticks(y); a.set_yticklabels([t.replace("electron shower", "e-sh").replace("muon-like", "mu").replace("pion-like", "pi").replace("proton-like", "p").replace("no particle row", "no-row") for t in tc.types], fontsize=7); a.invert_yaxis()
    a.set_xlabel("fragmented-photon events (n = 1622)"); a.set_title("reconstructed types of the significant pieces (>= 10 % charge)"); save(fig, "fig6_fragment_type_combinations.png")
    # 7. first-loss stage
    fl = tabs["fragment_first_loss"]; fig, ax = PS.figure(1, 2, size=(11, 4.2)); order = ["BDT evaluable", "numu", "other", "ncpi0", "n_20br1 == 1", "final"]
    for j, pop in enumerate(("fragmented", "clean")):
        a = ax[0][j]; d = fl[fl.population == pop].set_index("first_loss").reindex(order).fillna(0)
        a.bar(order, d.n, color=["#009E73", "#E69F00", "#D55E00", "#CC79A7", "#8c564b", "#000000"]); a.set_ylim(0, max(d.n.max() * 1.2, 1)); a.set_ylabel("events"); a.set_title(f"{pop} photon: first frozen stage that removes the event (n = {int(d.n.sum())})"); a.tick_params(axis="x", rotation=30)
        for k, v in enumerate(d.n):
            a.text(k, v, f"{int(v)}\n{v / d.n.sum():.1%}", ha="center", va="bottom", fontsize=7)
    fig.tight_layout(); save(fig, "fig7_fragmented_first_loss_stage.png")
    # 8. fragmentation <-> fake pi0
    fv = tabs["fragmentation_vs_ncpi0"]; fig, ax = PS.figure(1, 2, size=(11, 4.2)); a = ax[0][0]; x = np.arange(len(fv)); w = 0.2
    for k, (c, lab) in enumerate((("kine_pair", "kine pair flag"), ("tagger_pair", "tagger pair flag"), ("kine_pair_has_same_photon_fragment", "kine pair holds a same-photon fragment"), ("tagger_pair_has_same_photon_fragment", "tagger pair holds a same-photon fragment"))):
        a.bar(x + (k - 1.5) * w, fv[c] / fv.n, w, label=lab)
    a.set_xticks(x); a.set_xticklabels([f"{s}\n(n={n})" for s, n in zip(fv.photon_state, fv.n)]); a.set_ylabel("fraction of events"); a.legend(fontsize=6); a.set_title("pair presence by photon state"); b = ax[0][1]
    b.bar(x, fv.survival, color=["#009E73", "#8c564b", "#999999"]); b.set_xticks(x); b.set_xticklabels(fv.photon_state); b.set_ylabel("ncpi0 survival"); b.set_title("ncpi0 survival by photon state"); b.set_ylim(0, 1)
    for k, v in enumerate(fv.survival):
        b.text(k, v, f"{v:.2f}", ha="center", va="bottom", fontsize=8)
    fig.tight_layout(); save(fig, "fig8_fragmentation_vs_fake_pi0.png")
    # 9. clean-photon failures: second-object taxonomy
    cs = tabs["clean_photon_second_member"]; fig, ax = PS.figure(1, 2, size=(12, 4.2))
    for j, p in enumerate(("kine", "tagger")):
        a = ax[0][j]; d = cs[cs.pair == p].sort_values("n", ascending=True); a.barh(d.second_member, d.fraction, color=[COL.get(c, "0.5") for c in d.second_member]); a.set_xlabel(f"fraction of clean-photon ncpi0-rejected events whose {p} pair contains the signal photon (n = {int(d.n_group.iloc[0]) if len(d) else 0})")
        a.set_title(("kine_pio" if p == "kine" else "tagger") + " pair: the other member", fontsize=9); a.xaxis.label.set_size(7)
    fig.tight_layout(); save(fig, "fig9_clean_photon_failures_second_object.png")
    # 10. fragmentation <-> n_20br1
    t, base, stt, _ = ex; fig, ax = PS.figure(1, 1, size=(9, 3.6)); a = ax[0][0]; d = t.sort_values("n"); a.barh([m_[:70] for m_ in d.mapping], d.n, color="#8c564b"); a.set_xlabel("n_20br1 failures with an extra shower row attributed to the signal photon (n = 126)")
    a.set_title("n_20br1 failures: how the extra signal-photon row maps onto the Phase-9 fragmentation taxonomy", fontsize=8); fig.tight_layout(); save(fig, "fig10_fragmentation_vs_n20br1.png")


def git_head():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    except Exception:
        return "unknown"


def main():
    OUT.mkdir(parents=True, exist_ok=True); TAB.mkdir(parents=True, exist_ok=True); PLT.mkdir(parents=True, exist_ok=True)
    D = load(); pop = population(D); F = event_inputs(D); R = recover_all(F, D); rows = build_rows(D, F); T = pair_truth(F, R, rows)
    M, tabs = pair_blocks(F, R, T, rows, D); M, t2 = other_blocks(M, D, rows); tabs.update(t2)
    pcs = pieces_table(D); q = piece_locations(D, pcs); fe = fragment_events(D, q); fo, fe = frag_blocks(D, M, q, fe, rows); tabs.update(fo)
    ex = n20br1_overlap(D, fe, rows); tabs["n20br1_mapping"] = ex[0]; tabs["n20br1_failures_base"] = ex[1]; tabs["n20br1_failures_by_phase9_state"] = ex[2]; tabs["natural_cv_check"] = natural_check()
    # ---- population / recovery accounting tables
    tabs["ncpi0_population"] = pd.DataFrame([{k: v for k, v in pop.items() if k != "nonfinite_events"}]); tabs["ncpi0_nonfinite_events"] = pd.DataFrame(pop["nonfinite_events"])
    T8 = tabs["second_member"]
    for k, v in tabs.items():
        v.to_csv(TAB / f"{k}.csv", index=False)
    figures(M, rows, T8, fe, tabs, ex)
    # ---- detailed outputs outside Git
    mem = []
    for r in R.itertuples():
        for pair in ("kine", "tagger"):
            cfg = getattr(r, pair + "_configs_geom"); d = rows[(rows.file_index == r.file_index) & (rows.ev == r.ev) & (rows.cand == r.c_nu_index)].set_index("row") if len(cfg) else None
            for ci, (a, b) in enumerate(cfg):
                mem.append(dict(file_index=r.file_index, ev=r.ev, c_nu_index=r.c_nu_index, pair=pair, config=ci, n_configs=len(cfg), recovery_class=getattr(r, pair + "_class_geom"), row_for_energy1=a, row_for_energy2=b,
                                class1=d.tclass.get(a, "unmatched"), class2=d.tclass.get(b, "unmatched"), E1_row=float(d.ke.get(a, np.nan)), E2_row=float(d.ke.get(b, np.nan))))
    members = pd.DataFrame(mem)
    pq(members, OUT / "ncpi0_pair_members.parquet")
    keep = KEY + ["c_nu_index", "survive", "stage_score", "state3", "topology", "delta_label", "kine_present", "tagger_present", "kine_class", "kine_class_geom", "tagger_class", "tagger_class_geom", "kine_membership", "kine_other", "kine_origin", "tagger_membership", "tagger_other", "tagger_origin",
                  "kine_vs_tagger", "origin_any", "in_kine_pio_flag", "in_kine_pio_mass", "in_kine_pio_energy_1", "in_kine_pio_energy_2", "in_kine_pio_dis_1", "in_kine_pio_dis_2", "in_kine_pio_angle", "in_shw_sp_pio_1_mass", "in_shw_sp_pio_1_pio_type", "in_shw_sp_pio_1_energy_1", "in_shw_sp_pio_1_energy_2",
                  "in_shw_sp_pio_1_dis_1", "in_shw_sp_pio_1_dis_2", "n_sub_negative", "n_candidates_total"]
    pq(M[keep], OUT / "ncpi0_pair_truth_taxonomy.parquet"); omap = object_map(D, rows, R)
    pq(omap[KEY + ["cand", "row", "kine_particle_id", "kine_particle_type", "kine_particle_is_shower", "kine_particle_pool", "kine_energy_included", "kine_energy_info", "ke", "kine_particle_cluster_id", "kine_particle_nseg", "node_id", "depth", "start_x", "start_y", "start_z",
                    "p1_tid", "p1_t_pdg", "p1_t_nu", "p1_iou_n", "tclass", "is_dominant_photon_object", "in_kine_pair_any_config", "in_tagger_pair_any_config"]], OUT / "ncpi0_row_truth_class.parquet")
    pq(q, OUT / "fragmentation_objects.parquet"); pq(fe, OUT / "fragmentation_events.parquet"); pq(tabs["fragment_stage_fate"], OUT / "fragmentation_stage_fate.parquet")
    pq(M[(M.state3 == "clean") & ~M.survive][keep].drop_duplicates(KEY), OUT / "clean_photon_ncpi0_failures.parquet")
    meta = dict(phase=14, git_commit_at_run=git_head(), official_manifest_sha256=sha(REPO / "manifests" / "official_gen2_ncdelta_wc.tsv.gz"), t_match_ranking="source: point IoU first, then charge IoU, then object index (the stored match_obj[0]); no charge-IoU ranking",
                phase9_taxonomy_sha256=sha(P9 / "event_taxonomy.parquet"), phase10_truth_association_sha256=sha(P10 / "row_matches.parquet"), phase12_stage_audit_sha256=sha(P12 / "ncpi0_stage.parquet"), truth_nu_scan_sha256=sha(RAW / "truth_nu.parquet"),
                pair_reconstruction=dict(version="1", kine_pair="energy signature (stored kine_charge = row kine_best where kine_energy_info == 2) + elimination (rows with info != 2) + at-least-one-detached-member rule + stored-distance geometry", tagger_pair="same, with the tagger-selected shower required to be a member (checked, not imposed)",
                                         tolerance_energy_rel=PA.ENERGY_RTOL, geometry_strong_cm=0.01, geometry_weak_cm=0.05), significant_piece_fraction=PA.FRAGMENT_MIN_FRACTION, source_commit="4b6853d4 (HaiwangYu/wire-cell-toolkit, sbnd-wc-flatcaf)",
                convention="official Gen2 NC-Delta, provisional TPC box, frozen BDT thresholds, candidate policy any, no analysis FV, no proton policy in the selection")
    (OUT / "metadata.json").write_text(json.dumps(meta, indent=1))
    # ---- headline summary for the report / tests
    pr = tabs["pair_recovery"]; mm = tabs["pair_membership"]
    summ = dict(population={k: v for k, v in pop.items() if k != "nonfinite_events"}, nonfinite=pop["nonfinite_events"], n_events=len(M), pair_recovery=pr.to_dict("records"), membership=mm.to_dict("records"),
                stage_fate=tabs["fragment_stage_fate"].query("population == 'fragmented'").to_dict("records"), first_loss=tabs["fragment_first_loss"].to_dict("records"))
    (TAB / "summary.json").write_text(json.dumps(summ, indent=1, default=float))
    print("done", len(M), flush=True)
    return M, tabs


if __name__ == "__main__":
    main()
