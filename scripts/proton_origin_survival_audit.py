#!/usr/bin/env python
"""Phase 17: is the decay-proton versus FSI-created survival difference of truth-1p events (roadmap P), and the Delta+ / Delta0 difference inside truth 1p, explained by proton reconstruction, DL-stage vertex
anchoring and composition, or does a residual origin dependence remain?  CHARACTERISATION ONLY: no selection, BDT, proton-threshold, FV, candidate-policy or retraining change.

    source env/setup_eaf.sh
    python scripts/proton_origin_survival_audit.py        # reads the Phase 9 / 10 / 15 / 16 tables; no ROOT scan

Population: official Gen2 NC-Delta, provisional TPC box, frozen chain (policy ``any``), truth-1p events (one post-FSI primary proton above 35 MeV).  Adjustments are descriptive (stratified direct
standardisation with bootstrap, plus a logistic cross-check), not a causal model.
"""
from __future__ import annotations
import hashlib, json, os, subprocess, sys, warnings
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from sbnd_single_photon import origin_audit as OA

SPD = Path(os.environ["SP_DATA"]); OUT = SPD / "proton_origin_survival_audit" / "official_ncdelta"
P9 = SPD / "shower_vertex_audit" / "official_ncdelta"; P10 = SPD / "proton_truth_association" / "official_ncdelta"; P15 = SPD / "particle_pid_audit" / "official_ncdelta"; P16 = SPD / "vertex_provenance_audit" / "official_ncdelta"; P14 = SPD / "pi0_pair_fragmentation_audit" / "official_ncdelta"
TAB = REPO / "tables" / "proton_origin_survival_audit"; PLT = REPO / "plots" / "proton_origin_survival_audit"
K = ["file_index", "ev"]
STAGES = [("candidate", "A_candidate"), ("shower stage (> 20 MeV shower)", "A_n20mev"), ("BDT evaluable", "A_bdt_evaluable"), ("numu", "A_numu"), ("other", "A_other"), ("ncpi0", "A_ncpi0"), ("nue", "A_nue"), ("n_20br1", "A_n20br1"), ("final", "A_final")]


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


def master():
    """One row per truth-1p event: origin, Delta charge, photon / proton kinematics, proton reconstruction state (Phase 15), vertex anchoring (Phase 16), photon / attachment state, frozen-stage flags."""
    E = pd.read_parquet(P9 / "event_taxonomy.parquet"); E[K] = E[K].astype(int)
    tp = pd.read_parquet(P15 / "proton_pid_events.parquet"); tp[K] = tp[K].astype(int); full = pd.read_parquet(P10 / "truth_protons.parquet"); full[K] = full[K].astype(int)
    p = tp[(tp.ke > 35) & tp.is_signal & tp.primary]
    t1 = E[E.truth35 == 1].copy()
    cnt = p.groupby(K).size().rename("n_p35_rows").reset_index(); t1 = t1.merge(cnt, on=K, how="left")
    assert (t1.n_p35_rows == 1).sum() >= 5100
    t1 = t1[t1.n_p35_rows == 1]
    keep = ["trackid", "ke", "cos_beam", "origin_class", "origin_dke", "proton_class", "true_len_cm", "end_face_cm", "match_cand", "merge_destination"]
    m = t1.merge(p[K + keep], on=K, how="left").merge(full[K + ["trackid", "pf_start_px", "pf_start_py", "pf_start_pz"]], on=K + ["trackid"], how="left")
    m["origin"] = [OA.origin_category(o, d) for o, d in zip(m.origin_class, m.delta_label)]; m["origin_group"] = m.origin.map(OA.ORIGIN_GROUP)
    pu = np.c_[m.pf_start_px, m.pf_start_py, m.pf_start_pz]; pu = pu / np.linalg.norm(pu, axis=1, keepdims=True); ph = np.c_[m.photon_px, m.photon_py, m.photon_pz]; ph = ph / np.linalg.norm(ph, axis=1, keepdims=True)
    m["cos_proton_photon"] = (pu * ph).sum(axis=1); m["reco_state"] = m.proton_class.map(OA.collapse_reco_state)
    V = pd.read_parquet(P16 / "vertex_provenance_events.parquet"); V[K] = V[K].astype(int)
    m = m.merge(V[K + ["trad_true_mag", "dl_true_mag", "final_true_mag", "dl_true_par", "final_dl_mag", "have_dl", "prov_class"]], on=K, how="left")
    m["anchor"] = np.where(m.dl_true_mag.isna(), "no DL record", np.where(m.dl_true_mag <= 5, "DL anchored", "DL not anchored"))
    pe = pd.read_parquet(P15 / "photon_pid_events.parquet"); pe[K] = pe[K].astype(int); m = m.merge(pe[K + ["pid_class", "dom_type", "vtx_face_cm"]], on=K, how="left")
    A = pd.read_parquet(P16 / "shower_attachment_events.parquet"); A[K] = A[K].astype(int)
    m = m.merge(A[K + ["pclass", "parent_truth", "mechanism"]], on=K, how="left"); m["attach_fail"] = m.pclass.notna()
    cl = m.pid_class.fillna("")
    m["photon_state"] = np.where(m.attach_fail, "shower not in main-vertex set", np.where(cl.str.startswith("A "), "clean electron shower", np.where(cl.str.startswith("G "), "fragmented", np.where(cl.str.contains("muon|pion|proton|track"), "track-typed dominant object", "other"))))
    for _, c in STAGES:
        m[c] = m[c].astype(bool)
    # binned covariates
    m["b_E"] = pd.cut(m.photon_energy_mev, [0, 300, 1e9], labels=["<300", ">=300"], right=False).astype(str)          # coarse, pre-set bins: the strata must keep a common support
    m["b_cos"] = pd.cut(m.cos_theta_beam, [-1.01, 0.5, 1.01], labels=["<0.5", ">=0.5"], right=False).astype(str)
    m["b_pke"] = pd.cut(m.ke, [35, 100, 250, 1e9], labels=["35-100", "100-250", ">250"], right=False).astype(str)
    m["b_pke_fine"] = pd.cut(m.ke, [35, 50, 100, 200, 300, 1e9], labels=["35-50", "50-100", "100-200", "200-300", ">300"], right=False).astype(str)
    m["reco3"] = np.where(m.reco_state == "proton-typed", "proton-typed", np.where(m.reco_state == "merged", "merged", "other"))
    m["attach2"] = np.where(m.attach_fail, "attach-fail", "attached")
    m["b_edge"] = pd.cut(m.vtx_face_cm, [-1e9, 50, 100, 1e9], labels=["<50", "50-100", ">100"], right=False).astype(str)
    m["delta"] = m.delta_label
    return m


def add_neutron_flag(m):
    nr = neutron_photon_rows(m); m = m.merge(nr, on=K, how="left"); m["n_neutron_photon_rows"] = m.n_neutron_photon_rows.fillna(0); m["has_nph"] = np.where(m.n_neutron_photon_rows > 0, "nph-row", "no-nph-row"); return m


def git_head():
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
    except Exception:
        return "unknown"


ORD = OA.ORIGIN_CATEGORIES[:5]
SHORT = {ORD[0]: "A decay", ORD[1]: "B1 Delta0 FSI-created", ORD[2]: "B2 Delta+ charge-exchange", ORD[3]: "C not from decay", ORD[4]: "D ambiguous"}


def origin_tables(m):
    T = {}
    o = pd.read_parquet(P10 / "proton_origin_per_proton.parquet"); o = o[o.origin != "__event_marker__"].copy()
    ev = m[K + ["delta", "origin_class", "ke"]].merge(pd.read_parquet(P9 / "event_taxonomy.parquet", columns=K + ["run", "subrun", "evt"]).astype({"file_index": int, "ev": int}), on=K)
    j = ev.merge(o, on=["run", "subrun", "evt"], how="left"); j["dk"] = (j.ke - j.ke_mev).abs(); j = j.sort_values("dk").drop_duplicates(K)
    T["origin_definition_support"] = pd.concat([pd.crosstab(j.delta, j.decay_nucleon_pdg).rename_axis(None).reset_index().assign(item="decay nucleon pdg by Delta charge (GENIE status-14 daughter of the Delta)"),
                                                 j.groupby("origin_class").agg(n=("dk", "size"), chain_has_nonproton=("chain_has_nonproton", "mean"), n_decay_nucleon_proton_descendants_mean=("n_decay_nucleon_proton_descendants", "mean"), n_stable_protons_10_mean=("n_stable_protons_10", "mean"), ke_match_dKE_max_mev=("dk", "max")).reset_index().assign(item="chain fields by stored origin class")], ignore_index=True)
    m["_one"] = 1
    comp = pd.crosstab(m.origin, m.delta).reset_index(); comp["all"] = comp[["Delta+", "Delta0"]].sum(axis=1); comp["fraction_of_truth_1p"] = comp["all"] / len(m); T["origin_composition"] = comp
    # Phase-8 reproduction (events reaching `other`)
    r = m[m.A_numu]; rep = r.groupby(["delta", "origin_class"]).agg(n_reaching_other=("A_other", "size"), other_survival=("A_other", "mean"), final_efficiency=("A_final", "mean")).reset_index()
    rep["documented_phase8_n"] = rep.apply(lambda x: {("Delta+", "decay_proton"): 1367, ("Delta+", "fsi_created"): 137, ("Delta+", "ambiguous"): 35}.get((x.delta, x.origin_class), np.nan), axis=1)
    rep["documented_phase8_other_survival"] = rep.apply(lambda x: {("Delta+", "decay_proton"): 0.671, ("Delta+", "fsi_created"): 0.540}.get((x.delta, x.origin_class), np.nan), axis=1)
    T["origin_reproduction_phase8_other"] = rep
    T["origin_reproduction_phase8_totals"] = r.groupby("delta").agg(n_reaching_other=("A_other", "size"), other_survival=("A_other", "mean")).reset_index().assign(documented_n=lambda d: d.delta.map({"Delta+": 1541, "Delta0": 633}), documented_survival=lambda d: d.delta.map({"Delta+": 0.655, "Delta0": 0.574}))
    # reconstruction by origin
    rows = []
    for g, d in [("all truth 1p", m)] + [(SHORT[c], m[m.origin == c]) for c in ORD]:
        rec = dict(origin=g, n=len(d), proton_ke_median=d.ke.median(), proton_ke_p16=d.ke.quantile(.16), proton_ke_p84=d.ke.quantile(.84), proton_cos_beam_median=d.cos_beam.median(), true_path_cm_median=d.true_len_cm.median(), cos_proton_photon_median=d.cos_proton_photon.median(),
                   photon_energy_median=d.photon_energy_mev.median(), photon_cos_beam_median=d.cos_theta_beam.median())
        for c in ["proton-typed", "mu-typed", "pi-typed", "e-shower-typed", "merged / subdominant partner", "no row", "no signal-matched candidate"]:
            rec["frac_" + c] = float((d.proton_class == c).mean())
        rows.append(rec)
    T["reconstruction_by_origin"] = pd.DataFrame(rows)
    rows = []
    for (b, c), d in m.groupby(["b_pke_fine", "origin"]):
        if len(d) >= 5:
            rows.append(dict(proton_ke_bin=b, origin=SHORT[c], n=len(d), proton_typed=float((d.proton_class == "proton-typed").mean()), merged=float((d.proton_class == "merged / subdominant partner").mean()), mu_pi_typed=float(d.proton_class.isin(["mu-typed", "pi-typed"]).mean()), final_efficiency=float(d.A_final.mean())))
    T["reconstruction_by_origin_and_ke"] = pd.DataFrame(rows)
    # anchoring by origin
    rows = []
    for g, d in [("all truth 1p", m)] + [(SHORT[c], m[m.origin == c]) for c in ORD]:
        d = d[d.have_dl.notna()]
        rows.append(dict(origin=g, n=len(d), anchored_traditional=float((d.trad_true_mag.dropna() <= 5).mean()), anchored_dl=float((d.dl_true_mag.dropna() <= 5).mean()), anchored_final=float((d.final_true_mag.dropna() <= 5).mean()), dl_true_median=d.dl_true_mag.median(), dl_true_par_median=d.dl_true_par.median(), final_dl_median=d.final_dl_mag.median(), final_dl_gt5=float((d.final_dl_mag > 5).mean())))
    T["anchoring_by_origin"] = pd.DataFrame(rows)
    rows = []
    for (c, rs), d in m[m.have_dl.notna()].groupby(["origin", "reco_state"]):
        if len(d) >= 10:
            rows.append(dict(origin=SHORT[c], reco_state=rs, n=len(d), anchored_dl=float((d.dl_true_mag.dropna() <= 5).mean()), anchored_traditional=float((d.trad_true_mag.dropna() <= 5).mean())))
    T["anchoring_by_origin_and_reco_state"] = pd.DataFrame(rows)
    # photon / attachment
    rows = []
    for g, d in [("all truth 1p", m)] + [(SHORT[c], m[m.origin == c]) for c in ORD]:
        rec = dict(origin=g, n=len(d))
        for s in ["clean electron shower", "fragmented", "track-typed dominant object", "shower not in main-vertex set", "other"]:
            rec["frac_" + s] = float((d.photon_state == s).mean())
        rec["attach_fail_under_true_proton"] = float((d.attach_fail & (d.parent_truth == "signal_proton")).mean()); rec["attach_fail_under_true_hadron"] = float((d.attach_fail & d.mechanism.fillna("").str.contains("true hadronic")).mean()); rec["attach_fail"] = float(d.attach_fail.mean())
        rows.append(rec)
    T["photon_state_by_origin"] = pd.DataFrame(rows)
    # cutflow
    rows = []
    for g, d in [("all truth 1p", m)] + [(SHORT[c], m[m.origin == c]) for c in ORD] + [("Delta+ (all origins)", m[m.delta == "Delta+"]), ("Delta0 (all origins)", m[m.delta == "Delta0"])]:
        prev = len(d)
        for nm, c in STAGES:
            n = int(d[c].sum()); f, lo, hi = cp(n, len(d)); fc, loc, hic = cp(n, prev) if prev else (np.nan,) * 3
            rows.append(dict(origin=g, stage=nm, n=n, cumulative=f, cum_lo68=lo, cum_hi68=hi, conditional=fc, cond_lo68=loc, cond_hi68=hic, n_total=len(d))); prev = n
    T["cutflow_by_origin"] = pd.DataFrame(rows)
    rows = []
    for ke, d in m.groupby("b_pke_fine"):
        for c in ["A decay proton", "B1 Delta0: proton from the neutron decay nucleon (FSI-created)", "B2 Delta+: decay-nucleon chain contains a non-proton (charge exchange)"]:
            x = d[d.origin == c]
            if len(x) >= 10:
                f, lo, hi = cp(int(x.A_final.sum()), len(x)); rows.append(dict(proton_ke_bin=ke, origin=SHORT[c], n=len(x), final_efficiency=f, lo68=lo, hi68=hi))
    T["final_efficiency_vs_proton_ke_by_origin"] = pd.DataFrame(rows)
    return T


def other_stage_tables(m):
    """Task 7 / 8: `other` survival (events reaching `other`, i.e. passing numu) stratified by origin, DL anchoring, proton reconstruction, photon / attachment state; Delta x origin x reconstruction x anchoring."""
    r = m[m.A_numu & (m.anchor != "no DL record")].copy(); T = {}
    r["o3"] = r.origin.map(lambda c: SHORT.get(c, c)); r.loc[r.origin.isin([OA.ORIGIN_CATEGORIES[3], OA.ORIGIN_CATEGORIES[4]]), "o3"] = "C/D other origin"
    r["proton_ok"] = np.where(r.reco_state == "proton-typed", "proton reco-typed", "proton not reco-typed")
    def tab(cols, name, nmin=15):
        rows = []
        for key, g in r.groupby(cols):
            key = key if isinstance(key, tuple) else (key,)
            if len(g) >= nmin:
                f, lo, hi = cp(int(g.A_other.sum()), len(g)); rows.append(dict(**dict(zip(cols, key)), n=len(g), other_pass=int(g.A_other.sum()), other_survival=f, lo68=lo, hi68=hi, final_efficiency_of_these=float(g.A_final.mean())))
        T[name] = pd.DataFrame(rows)
    tab(["o3"], "other_by_origin"); tab(["o3", "anchor"], "other_by_origin_x_anchoring"); tab(["o3", "proton_ok"], "other_by_origin_x_proton_reco"); tab(["o3", "anchor", "proton_ok"], "other_by_origin_x_anchoring_x_proton_reco")
    tab(["o3", "photon_state"], "other_by_origin_x_photon_state"); tab(["anchor", "proton_ok"], "other_by_anchoring_x_proton_reco"); tab(["delta", "o3", "anchor", "proton_ok"], "other_by_delta_x_origin_x_anchoring_x_proton_reco", nmin=20)
    # a within-stratum origin contrast: A vs B1 / B2 at fixed anchoring and proton reconstruction
    rows = []
    for (an, pk), g in r.groupby(["anchor", "proton_ok"]):
        a = g[g.o3 == "A decay"]
        for other in ("B1 Delta0 FSI-created", "B2 Delta+ charge-exchange"):
            b = g[g.o3 == other]
            if len(a) >= 15 and len(b) >= 15:
                d = a.A_other.mean() - b.A_other.mean(); se = np.sqrt(a.A_other.var() / len(a) + b.A_other.var() / len(b)); rows.append(dict(anchoring=an, proton_reco=pk, vs=other, n_decay=len(a), n_other_origin=len(b), other_decay=a.A_other.mean(), other_origin=b.A_other.mean(), diff=d, se=se, z=d / se))
    T["other_decay_minus_origin_within_strata"] = pd.DataFrame(rows)
    return T


def delta_origin_table(m):
    """Task 8: Delta0 / Delta+ x origin x proton reconstruction x DL anchoring (counts and final efficiency)."""
    d = m[m.anchor != "no DL record"].copy(); d["proton_ok"] = np.where(d.reco_state == "proton-typed", "proton reco-typed", "proton not reco-typed"); d["o3"] = d.origin.map(lambda c: SHORT.get(c, c)); d.loc[d.origin.isin([OA.ORIGIN_CATEGORIES[3], OA.ORIGIN_CATEGORIES[4]]), "o3"] = "C/D other origin"
    rows = []
    for key, g in d.groupby(["delta", "o3", "proton_ok", "anchor"]):
        if len(g) >= 10:
            f, lo, hi = cp(int(g.A_final.sum()), len(g)); rows.append(dict(delta=key[0], origin=key[1], proton_reco=key[2], anchoring=key[3], n=len(g), final_efficiency=f, lo68=lo, hi68=hi, other_survival_given_reached=float(g[g.A_numu].A_other.mean()) if g.A_numu.any() else np.nan))
    return pd.DataFrame(rows)


def comp_columns():
    return dict(photon=["b_E", "b_cos"], pke=["b_pke"], origin=["origin_group"], reco=["reco3"], anchor=["anchor"], attach=["attach2"], edge=["b_edge"], nph=["has_nph"])


def adjustment_delta(m, n_boot=300):
    """Task 9: Delta+ - Delta0 final-efficiency (and `other`) difference inside truth 1p under increasingly controlled comparisons.  Two populations: all truth-1p events (origin cannot be matched: Delta0 has no decay
    protons) and the FSI-like origin only (both charges present)."""
    c = comp_columns(); rows = []
    pops = {"all truth 1p (origin not controlled: no Delta0 decay protons)": m[m.anchor != "no DL record"], "FSI-like origin only (B1 + B2 + C; both charges)": m[(m.origin_group == "FSI-like") & (m.anchor != "no DL record")]}
    def steps_for(with_origin):
        o = c["origin"] if with_origin else []
        st = [("1 raw", []), ("2 + photon energy and angle", c["photon"]), ("3 + proton KE", c["photon"] + c["pke"])]
        if with_origin:
            st.append(("4 + proton origin (group)", c["photon"] + c["pke"] + o))
        st += [("5 + proton reconstruction state", c["photon"] + c["pke"] + o + c["reco"]), ("6 + DL anchoring state", c["photon"] + c["pke"] + o + c["reco"] + c["anchor"]), ("7 + photon / attachment state", c["photon"] + c["pke"] + o + c["reco"] + c["anchor"] + c["attach"]), ("8 + neutron-capture-like photon row (exploratory, from the ncpi0 mechanism)", c["photon"] + c["pke"] + o + c["reco"] + c["anchor"] + c["attach"] + c["nph"])]
        return st
    for pn, d in pops.items():
        for outcome, sub, olab in (("A_final", d, "final efficiency"), ("A_other", d[d.A_numu], "other survival (reaching other)")):
            for sn, cols in steps_for(not pn.startswith("all")):
                r = OA.bootstrap_standardise(sub, "delta", "Delta+", "Delta0", outcome, cols, n_boot=n_boot, weights="hi")
                rows.append(dict(population=pn, outcome=olab, step=sn, n_delta_plus=r["n_hi"], n_delta0=r["n_lo"], raw=r["raw"], raw_on_support=r["raw_on_support"], raw_on_support_lo68=r["raw_on_support_lo68"], raw_on_support_hi68=r["raw_on_support_hi68"], adjusted=r["adjusted"],
                                 adjusted_lo68=r["adjusted_lo68"], adjusted_hi68=r["adjusted_hi68"], support_fraction_of_delta_plus=r["support_fraction"], n_strata=r["n_strata"]))
    T = pd.DataFrame(rows); T["fraction_of_raw_remaining"] = T.adjusted / T.raw; return T


def logistic_cross_check(d, group_col, hi, lo, outcome, cols):
    """Secondary cross-check: unpenalised logistic regression of the outcome on the group flag and one-hot covariates; average marginal effect of the group over the ``hi`` events."""
    from sklearn.linear_model import LogisticRegression
    x = pd.get_dummies(d[cols].astype(str), drop_first=True).astype(float); x.insert(0, "grp", (d[group_col] == hi).astype(float).values); y = d[outcome].astype(int).values
    mdl = LogisticRegression(penalty=None, max_iter=5000).fit(x.values, y); h = x[x.grp == 1].copy(); p1 = mdl.predict_proba(h.values)[:, 1]; h["grp"] = 0.0; p0 = mdl.predict_proba(h.values)[:, 1]
    return dict(coef_group=float(mdl.coef_[0][0]), odds_ratio=float(np.exp(mdl.coef_[0][0])), marginal_effect=float((p1 - p0).mean()), n=len(d))


def decay_vs_fsi(m, n_boot=300):
    """Task 10: decay proton (A) versus FSI-created inside Delta+ (B2: clean charge-exchange comparison) and versus Delta0 B1: stage-wise survival before and after standardisation on photon E / angle, proton KE, vertex edge
    distance, DL anchoring and proton reconstruction state (weights: the FSI-created group, the smaller one)."""
    d = m[m.anchor != "no DL record"].copy(); rows = []; logs = []
    stg = [("shower stage", d, "A_n20mev"), ("numu | evaluable", d[d.A_bdt_evaluable], "A_numu"), ("other | numu", d[d.A_numu], "A_other"), ("ncpi0 | other", d[d.A_other], "A_ncpi0"), ("n_20br1 | ncpi0", d[d.A_ncpi0], "A_n20br1"), ("final (cumulative)", d, "A_final")]
    c = comp_columns(); cum = [("raw", []), ("+ photon E, angle", c["photon"]), ("+ proton KE", c["photon"] + c["pke"]), ("+ vertex edge distance", c["photon"] + c["pke"] + c["edge"]), ("+ DL anchoring", c["photon"] + c["pke"] + c["edge"] + c["anchor"]), ("+ proton reco state", c["photon"] + c["pke"] + c["edge"] + c["anchor"] + c["reco"]), ("+ neutron-capture-like photon row (exploratory)", c["photon"] + c["pke"] + c["edge"] + c["anchor"] + c["reco"] + c["nph"])]
    for lo_name, lo_lab in ((OA.ORIGIN_CATEGORIES[2], "B2 Delta+ charge-exchange (same Delta charge)"), (OA.ORIGIN_CATEGORIES[1], "B1 Delta0 FSI-created (other Delta charge)")):
        sub_all = d[d.origin.isin([OA.ORIGIN_CATEGORIES[0], lo_name])]
        for sname, s, oc in stg:
            s = s[s.origin.isin([OA.ORIGIN_CATEGORIES[0], lo_name])]
            for cn, cols in cum:
                r = OA.bootstrap_standardise(s, "origin", OA.ORIGIN_CATEGORIES[0], lo_name, oc, cols, n_boot=n_boot, weights="lo")
                rows.append(dict(comparison=f"A decay vs {lo_lab}", stage=sname, adjustment=cn, n_decay=r["n_hi"], n_fsi=r["n_lo"], raw=r["raw"], raw_on_support=r["raw_on_support"], adjusted=r["adjusted"], adjusted_lo68=r["adjusted_lo68"], adjusted_hi68=r["adjusted_hi68"],
                                 support_fraction_of_fsi=r["support_fraction"], n_strata=r["n_strata"]))
        cols_all = c["photon"] + c["pke"] + c["edge"] + c["anchor"] + c["reco"]
        logs.append(dict(comparison=f"A decay vs {lo_lab}", outcome="final", covariates="photon E, angle; proton KE; edge; anchoring; reco", **logistic_cross_check(sub_all, "origin", OA.ORIGIN_CATEGORIES[0], lo_name, "A_final", cols_all)))
        s2 = sub_all[sub_all.A_numu]; logs.append(dict(comparison=f"A decay vs {lo_lab}", outcome="other | numu", covariates="photon E, angle; proton KE; edge; anchoring; reco", **logistic_cross_check(s2, "origin", OA.ORIGIN_CATEGORIES[0], lo_name, "A_other", cols_all)))
    return pd.DataFrame(rows), pd.DataFrame(logs)


def delta_by_stage(m, n_boot=300):
    """Stage-wise Delta+ - Delta0 contrast inside truth 1p (conditional survival at each stage), raw and with the full descriptive adjustment (photon E / angle, proton KE, proton reconstruction, DL anchoring, attachment)."""
    d = m[m.anchor != "no DL record"]; c = comp_columns(); full = c["photon"] + c["pke"] + c["reco"] + c["anchor"] + c["attach"]; rows = []
    stg = [("shower stage", d, "A_n20mev"), ("numu | evaluable", d[d.A_bdt_evaluable], "A_numu"), ("other | numu", d[d.A_numu], "A_other"), ("ncpi0 | other", d[d.A_other], "A_ncpi0"), ("n_20br1 | ncpi0", d[d.A_ncpi0], "A_n20br1"), ("final (cumulative)", d, "A_final")]
    for pn, sel in (("all truth 1p", lambda x: x), ("FSI-like origin only", lambda x: x[x.origin_group == "FSI-like"])):
        for sname, s, oc in stg:
            s = sel(s)
            for an, cols in (("raw", []), ("photon + proton KE", c["photon"] + c["pke"]), ("full descriptive adjustment", full)):
                r = OA.bootstrap_standardise(s, "delta", "Delta+", "Delta0", oc, cols, n_boot=n_boot, weights="hi")
                rows.append(dict(population=pn, stage=sname, adjustment=an, n_delta_plus=r["n_hi"], n_delta0=r["n_lo"], delta_plus_rate=float(s[s.delta == "Delta+"][oc].mean()), delta0_rate=float(s[s.delta == "Delta0"][oc].mean()), raw=r["raw"], adjusted=r["adjusted"], adjusted_lo68=r["adjusted_lo68"], adjusted_hi68=r["adjusted_hi68"], support_fraction=r["support_fraction"]))
    return pd.DataFrame(rows)


def neutron_photon_rows(m):
    """Per truth-1p event: number of reconstructed rows of the signal-matched candidate whose source-ranked T_match top partner is a PHOTON of the signal interaction whose mother is a NEUTRON (the neutron-capture-like
    low-energy photons of Phase 14) and the total energy of those rows (Phase-10 row_matches; mother pdg ``p1_t_mpdg``)."""
    rm = pd.read_parquet(P10 / "row_matches.parquet"); rm[K] = rm[K].astype(int)
    mc = m[K + ["match_cand"]].dropna(); rm = rm.merge(mc, on=K); rm = rm[rm.cand == rm.match_cand]
    sel = rm[(rm.p1_t_pdg == 22) & (rm.p1_t_nu == rm.sig_nu) & (rm.p1_t_mpdg == 2112)]
    g = sel.groupby(K).agg(n_neutron_photon_rows=("row", "size"), neutron_photon_energy=("ke", "sum")).reset_index()
    return g


def ncpi0_mechanism(m, n_boot=300):
    """Task 11 (residual at ncpi0): by origin, for events reaching ncpi0: pair presence, second-member class, neutron-capture-like photon rows, proton geometry; standardised A-vs-FSI contrasts of the pair outcomes."""
    S = pd.read_parquet(P14 / "ncpi0_pair_truth_taxonomy.parquet"); S[K] = S[K].astype(int)
    x = m.merge(S[K + ["survive", "stage_score", "kine_present", "tagger_present", "kine_origin", "in_kine_pio_mass"]], on=K)
    x = x[x.anchor != "no DL record"].copy(); x["o3"] = x.origin.map(lambda c: SHORT.get(c, c)); x["kine"] = x.kine_present.astype(int); x["tag"] = x.tagger_present.astype(int); x["sur"] = x.survive.astype(int); x["em2"] = (x.kine_origin == "signal photon + other signal EM").astype(int)
    x["has_nphoton"] = (x.n_neutron_photon_rows > 0).astype(int); T = {}
    rows = []
    for g, d in x.groupby("o3"):
        if len(d) < 5:
            continue
        rows.append(dict(origin=g, n_reaching_ncpi0=len(d), ncpi0_survival=d.sur.mean(), kine_pair_present=d.kine.mean(), tagger_pair_present=d.tag.mean(), survival_with_kine_pair=d[d.kine == 1].sur.mean(), survival_without_kine_pair=d[d.kine == 0].sur.mean(),
                         kine_pair_second_member_other_signal_EM=float((d[d.kine == 1].kine_origin == "signal photon + other signal EM").mean()), kine_pair_second_member_signal_proton_or_hadron=float((d[d.kine == 1].kine_origin == "signal photon + signal proton/hadron").mean()),
                         kine_pair_same_photon_pieces=float((d[d.kine == 1].kine_origin == "same-photon pieces").mean()), events_with_neutron_photon_row=float(d.has_nphoton.mean()), mean_neutron_photon_rows=float(d.n_neutron_photon_rows.mean()),
                         proton_ke_median=d.ke.median(), cos_proton_photon_median=d.cos_proton_photon.median(), proton_typed=float((d.reco_state == "proton-typed").mean()), dl_anchored=float((d.anchor == "DL anchored").mean())))
    T["ncpi0_mechanism_by_origin"] = pd.DataFrame(rows)
    rows = []
    for g, d in x.groupby(["o3", "has_nphoton"]):
        if len(d) >= 10:
            rows.append(dict(origin=g[0], neutron_capture_like_photon_row=bool(g[1]), n=len(d), kine_pair_present=d.kine.mean(), ncpi0_survival=d.sur.mean()))
    T["ncpi0_by_origin_x_neutron_photon_row"] = pd.DataFrame(rows)
    c = comp_columns(); cols = c["photon"] + c["pke"] + c["reco"] + c["anchor"]; rows = []
    for lo in (OA.ORIGIN_CATEGORIES[1], OA.ORIGIN_CATEGORIES[2]):
        s = x[x.origin.isin([OA.ORIGIN_CATEGORIES[0], lo])]
        for out, lab in (("sur", "ncpi0 survival"), ("kine", "kine pair present"), ("tag", "tagger pair present"), ("em2", "kine pair with other-signal-EM second member"), ("has_nphoton", "event has a neutron-capture-like photon row")):
            for an, cc in (("raw", []), ("photon + proton KE", c["photon"] + c["pke"]), ("+ proton reco + DL anchoring", cols), ("+ neutron-capture-like photon row", cols + ["has_nphoton"])):
                if out == "has_nphoton" and an.startswith("+ neutron"):
                    continue
                r = OA.bootstrap_standardise(s, "origin", OA.ORIGIN_CATEGORIES[0], lo, out, cc, n_boot=n_boot, weights="lo")
                rows.append(dict(comparison=f"A decay vs {SHORT[lo]}", outcome=lab, adjustment=an, n_decay=r["n_hi"], n_fsi=r["n_lo"], raw=r["raw"], adjusted=r["adjusted"], adjusted_lo68=r["adjusted_lo68"], adjusted_hi68=r["adjusted_hi68"], support_fraction=r["support_fraction"]))
    T["ncpi0_standardised_contrasts"] = pd.DataFrame(rows)
    # neutron-capture-like photon rows over all truth-1p events (not only those reaching ncpi0)
    y = m[m.match_cand.notna()]; rows = []
    for g in ORD:
        d = y[y.origin == g]; rows.append(dict(origin=SHORT[g], n=len(d), events_with_neutron_photon_row=float((d.n_neutron_photon_rows > 0).mean()), mean_rows=float(d.n_neutron_photon_rows.mean()), median_energy_mev=float(d[d.n_neutron_photon_rows > 0].neutron_photon_energy.median())))
    T["neutron_photon_rows_by_origin"] = pd.DataFrame(rows)
    return T, x


def natural_note():
    sn = pd.read_parquet(SPD / "natural_ncdelta_bnb_cv" / "signal_neutrinos.parquet"); cols = [c for c in ("nucleon_pdg", "nucleon_status", "delta_pdg", "n_p35") if c in sn.columns]
    sn = sn.drop_duplicates(["file_index", "ev"]); t1 = sn[sn.n_p35 == 1]
    return pd.DataFrame([dict(item="natural signal events (unique file, event)", n=len(sn)), dict(item="  truth 1p (n_p35 == 1)", n=len(t1)), dict(item="  truth 1p with decay nucleon pdg 2212 (Delta+)", n=int((t1.nucleon_pdg == 2212).sum())), dict(item="  truth 1p with decay nucleon pdg 2112 (Delta0)", n=int((t1.nucleon_pdg == 2112).sum())),
                         dict(item="GENIE mother chain of the final proton (decay / FSI-created split)", n=-1), dict(item="final-selection flags for these events", n=-1)])


# =============================================================================================================== figures
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sbnd_single_photon import plotstyle as PS
PROV = "official Gen2 NC-Delta | frozen chain, policy any | truth-1p events | descriptive standardisation (not a causal model) | no cut changed"
OCOL = {"A decay": "#0072B2", "B1 Delta0 FSI-created": "#D55E00", "B2 Delta+ charge-exchange": "#E69F00", "C not from decay": "#999999", "D ambiguous": "#009E73"}


def save(fig, name):
    PS.annotate(fig, PROV, extra=PS.PRELIM); fig.savefig(PLT / name, bbox_inches="tight"); plt.close(fig)


def figures(m, T, adj, dv, ds):
    fig, ax = PS.figure(1, 1, size=(7, 4.2)); x = np.arange(2); bottom = np.zeros(2)
    for c in ORD:
        v = np.array([(m[(m.delta == d)].origin == c).mean() for d in ("Delta+", "Delta0")]); ax[0][0].bar(x, v, 0.55, bottom=bottom, color=OCOL[SHORT[c]], edgecolor="white", label=f"{SHORT[c]}"); bottom += v
    ax[0][0].set_xticks(x); ax[0][0].set_xticklabels([f"{d}\n(n={int((m.delta == d).sum())})" for d in ("Delta+", "Delta0")]); ax[0][0].set_ylabel("fraction of truth-1p events"); ax[0][0].legend(fontsize=6, loc="upper left", bbox_to_anchor=(1, 1)); ax[0][0].set_title("proton origin by Delta charge", fontsize=9)
    fig.tight_layout(); save(fig, "fig1_origin_composition_by_delta.png")
    cls = ["proton-typed", "mu-typed", "pi-typed", "e-shower-typed", "merged / subdominant partner", "no row", "no signal-matched candidate"]; cc = ["#0072B2", "#D55E00", "#E69F00", "#009E73", "#CC79A7", "#bbbbbb", "#444444"]
    fig, ax = PS.figure(1, 1, size=(8.5, 4.2)); x = np.arange(len(ORD[:3]) + 1); bottom = np.zeros(len(x)); groups = [m[m.origin == c] for c in ORD[:3]] + [m[m.origin.isin(ORD[3:])]]; labs = [SHORT[c] for c in ORD[:3]] + ["C/D other"]
    for k, c in enumerate(cls):
        v = np.array([(g.proton_class == c).mean() for g in groups]); ax[0][0].bar(x, v, 0.6, bottom=bottom, color=cc[k], edgecolor="white", label=c); bottom += v
    ax[0][0].set_xticks(x); ax[0][0].set_xticklabels([f"{l}\n(n={len(g)})" for l, g in zip(labs, groups)], fontsize=7); ax[0][0].set_ylabel("fraction"); ax[0][0].legend(fontsize=6, loc="upper left", bbox_to_anchor=(1, 1)); ax[0][0].set_title("proton reconstruction outcome by origin", fontsize=9)
    fig.tight_layout(); save(fig, "fig2_proton_reco_by_origin.png")
    a_ = T["anchoring_by_origin"]; a_ = a_[a_.origin != "all truth 1p"]; fig, ax = PS.figure(1, 1, size=(8.5, 4.0)); x = np.arange(len(a_)); w = 0.26
    for k, (c, l, col) in enumerate((("anchored_traditional", "traditional vertex", "#999999"), ("anchored_dl", "DL-stage vertex", "#0072B2"), ("anchored_final", "final vertex", "#D55E00"))):
        ax[0][0].bar(x + (k - 1) * w, a_[c], w, label=l, color=col)
    ax[0][0].set_xticks(x); ax[0][0].set_xticklabels([f"{o}\n(n={n})" for o, n in zip(a_.origin, a_.n)], fontsize=7); ax[0][0].set_ylabel("fraction within 5 cm of the true vertex"); ax[0][0].legend(fontsize=7); ax[0][0].set_title("vertex anchoring by proton origin", fontsize=9)
    fig.tight_layout(); save(fig, "fig3_anchoring_by_origin.png")
    cf = T["cutflow_by_origin"]; stg = [s for s, _ in STAGES[1:] if s not in ("nue", "final")]; fig, ax = PS.figure(1, 1, size=(10, 4.2)); sel = [SHORT[c] for c in ORD[:3]]; w = 0.8 / len(sel); x = np.arange(len(stg))
    for k, o in enumerate(sel):
        g = cf[cf.origin == o].set_index("stage").reindex(stg); ax[0][0].bar(x + (k - 1) * w, g.conditional, w, yerr=[np.maximum(g.conditional - g.cond_lo68, 0), np.maximum(g.cond_hi68 - g.conditional, 0)], color=OCOL[o], label=f"{o} (n={int(g.n_total.iloc[0])})", error_kw=dict(lw=0.7))
    ax[0][0].set_xticks(x); ax[0][0].set_xticklabels([s.replace(" (> 20 MeV shower)", "") for s in stg], rotation=15); ax[0][0].set_ylabel("conditional survival"); ax[0][0].legend(fontsize=7); ax[0][0].set_ylim(0, 1.05); ax[0][0].set_title("frozen-stage conditional survival by proton origin", fontsize=9)
    fig.tight_layout(); save(fig, "fig4_stage_survival_by_origin.png")
    o1 = T["other_by_origin"]; o2 = T["other_by_origin_x_anchoring"]; fig, ax = PS.figure(1, 2, size=(12, 4.0)); sel = [SHORT[c] for c in ORD[:3]]
    ax[0][0].bar(sel, [o1.set_index("o3").loc[s].other_survival for s in sel], color=[OCOL[s] for s in sel], yerr=[[max(o1.set_index("o3").loc[s].other_survival - o1.set_index("o3").loc[s].lo68, 0) for s in sel], [max(o1.set_index("o3").loc[s].hi68 - o1.set_index("o3").loc[s].other_survival, 0) for s in sel]]); ax[0][0].set_ylim(0, 1); ax[0][0].set_ylabel("`other` survival (reaching other)"); ax[0][0].set_title("raw by origin", fontsize=9); ax[0][0].tick_params(axis="x", labelsize=7)
    x = np.arange(len(sel)); w = 0.38
    for k, (an, col) in enumerate((("DL anchored", "#0072B2"), ("DL not anchored", "#bbbbbb"))):
        g = o2[o2.anchor == an].set_index("o3").reindex(sel); ax[0][1].bar(x + (k - 0.5) * w, g.other_survival, w, yerr=[np.maximum(g.other_survival - g.lo68, 0), np.maximum(g.hi68 - g.other_survival, 0)], color=col, label=an)
    ax[0][1].set_xticks(x); ax[0][1].set_xticklabels(sel, fontsize=7); ax[0][1].set_ylim(0, 1); ax[0][1].legend(fontsize=7); ax[0][1].set_title("split by DL-stage anchoring", fontsize=9)
    fig.tight_layout(); save(fig, "fig5_other_survival_by_origin_and_anchoring.png")
    fig, ax = PS.figure(1, 2, size=(13, 4.4))
    for j, pop in enumerate(adj.population.unique()):
        d = adj[(adj.population == pop) & (adj.outcome == "final efficiency")]; y = np.arange(len(d))[::-1]
        ax[0][j].errorbar(d.adjusted * 100, y, xerr=[np.maximum(d.adjusted - d.adjusted_lo68, 0) * 100, np.maximum(d.adjusted_hi68 - d.adjusted, 0) * 100], fmt="o", color="k", lw=1); ax[0][j].plot(d.raw_on_support * 100, y, "x", color="#D55E00", label="raw on the same support")
        ax[0][j].axvline(0, color="0.5", lw=0.7); ax[0][j].set_yticks(y); ax[0][j].set_yticklabels([f"{s[:42]} (support {sf:.0%})" for s, sf in zip(d.step, d.support_fraction_of_delta_plus)], fontsize=7); ax[0][j].set_xlabel("Delta+ - Delta0 final efficiency [pp]"); ax[0][j].set_title(pop[:60], fontsize=8); ax[0][j].legend(fontsize=6)
    fig.tight_layout(); save(fig, "fig6_delta_difference_after_adjustment.png")
    fk = T["final_efficiency_vs_proton_ke_by_origin"]; fig, ax = PS.figure(1, 1, size=(8, 4.2)); bins = ["35-50", "50-100", "100-200", "200-300", ">300"]
    for o in [SHORT[c] for c in ORD[:3]]:
        g = fk[fk.origin == o].set_index("proton_ke_bin").reindex(bins); ax[0][0].errorbar(np.arange(len(bins)) + (0.05 * (list(OCOL).index(o) - 1)), g.final_efficiency, yerr=[np.maximum(g.final_efficiency - g.lo68, 0), np.maximum(g.hi68 - g.final_efficiency, 0)], fmt="o-", color=OCOL[o], label=o)
    ax[0][0].set_xticks(range(len(bins))); ax[0][0].set_xticklabels(bins); ax[0][0].set_xlabel("true proton KE [MeV]"); ax[0][0].set_ylabel("final efficiency"); ax[0][0].legend(fontsize=7); ax[0][0].set_title("final efficiency vs proton KE by origin", fontsize=9)
    fig.tight_layout(); save(fig, "fig7_final_efficiency_vs_proton_ke_by_origin.png")


def main():
    OUT.mkdir(parents=True, exist_ok=True); TAB.mkdir(parents=True, exist_ok=True); PLT.mkdir(parents=True, exist_ok=True)
    m = add_neutron_flag(master()); T = origin_tables(m); T.update(other_stage_tables(m)); T["delta_x_origin_x_reco_x_anchoring"] = delta_origin_table(m)
    adj = adjustment_delta(m); T["delta_adjustment_steps"] = adj; ds = delta_by_stage(m); T["delta_by_stage"] = ds; dv, lg = decay_vs_fsi(m); T["decay_vs_fsi_adjustment"] = dv; T["decay_vs_fsi_logistic_crosscheck"] = lg
    mech, x = ncpi0_mechanism(m); T.update(mech)
    lgd = []
    for pn, d in (("all truth 1p", m[m.anchor != "no DL record"]),):
        c = comp_columns()
        for out, sub, lab in (("A_final", d, "final"), ("A_other", d[d.A_numu], "other | numu")):
            lgd.append(dict(population=pn, outcome=lab, covariates="photon E, angle; proton KE; reco; anchoring; attachment", **logistic_cross_check(sub, "delta", "Delta+", "Delta0", out, c["photon"] + c["pke"] + c["reco"] + c["anchor"] + c["attach"])))
            lgd.append(dict(population=pn, outcome=lab, covariates="+ neutron-capture-like photon row", **logistic_cross_check(sub, "delta", "Delta+", "Delta0", out, c["photon"] + c["pke"] + c["reco"] + c["anchor"] + c["attach"] + c["nph"])))
    T["delta_logistic_crosscheck"] = pd.DataFrame(lgd); T["natural_cv_check"] = natural_note()
    for k, v in T.items():
        v.to_csv(TAB / f"{k}.csv", index=False)
    figures(m, T, adj, dv, ds)
    pq = lambda d, f: d.to_parquet(OUT / f, index=False)
    mm = m.copy(); pq(mm.drop(columns=[c for c in mm.columns if mm[c].dtype == object and c in ("chain_desc",)], errors="ignore"), "proton_origin_events.parquet")
    meta = dict(phase=17, git_commit_at_run=git_head(), official_manifest_sha256=sha(REPO / "manifests" / "official_gen2_ncdelta_wc.tsv.gz"), phase9_taxonomy_sha256=sha(P9 / "event_taxonomy.parquet"), phase10_truth_proton_sha256=sha(P10 / "truth_protons.parquet"), phase10_origin_sha256=sha(P10 / "proton_origin_per_proton.parquet"),
                phase15_proton_pid_sha256=sha(P15 / "proton_pid_events.parquet"), phase15_photon_pid_sha256=sha(P15 / "photon_pid_events.parquet"), phase16_vertex_provenance_sha256=sha(P16 / "vertex_provenance_events.parquet"), phase16_attachment_sha256=sha(P16 / "shower_attachment_events.parquet"),
                bootstrap=dict(n=300, seed=20261111, interval="68 % percentile"), min_stratum_count_per_group=3, bins=dict(photon_E=["<300", ">=300"], photon_cos=["<0.5", ">=0.5"], proton_ke=["35-100", "100-250", ">250"], edge_cm=["<50", "50-100", ">100"]), anchoring_tolerance_cm=5.0,
                note="descriptive stratified standardisation, not a causal model; no cut or threshold changed")
    (OUT / "metadata.json").write_text(json.dumps(meta, indent=1))
    (TAB / "summary.json").write_text(json.dumps(dict(n_truth_1p=len(m), n_delta_plus=int((m.delta == "Delta+").sum()), n_delta0=int((m.delta == "Delta0").sum()), origin_counts={k: int(v) for k, v in m.origin.value_counts().items()}), indent=1)); print("done", len(m), flush=True)
    return m, T


if __name__ == "__main__":
    main()
