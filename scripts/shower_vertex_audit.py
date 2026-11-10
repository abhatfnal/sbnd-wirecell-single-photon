#!/usr/bin/env python
"""Photon-shower / vertex reconstruction audit of the frozen Wire-Cell baseline on the official Gen2 NC-Delta signal (READ-ONLY analysis of stored tables; no decision, cut, threshold or policy changes).

    source env/setup_eaf.sh
    python scripts/shower_vertex_scan.py ; python scripts/other_bdt_proton_origin_scan.py --all-candidate-stage     # raw tables (once)
    python scripts/shower_vertex_audit.py

Population: official Gen2 signal events of the provisional TPC box with wc.valid and >= 1 Wire-Cell candidate (11,331). Outputs outside Git: $SP_DATA/shower_vertex_audit/official_ncdelta/; compact summaries:
tables/shower_vertex_audit/; headline figures: plots/shower_vertex_audit/.
"""
from __future__ import annotations
import hashlib, json, os, subprocess, sys, warnings
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from scipy import stats
from sbnd_single_photon import differential as DF, exclusive_signal as X, plotstyle as PS, shower_audit as SA, shower_tables as ST
import matplotlib.pyplot as plt

SPD = Path(os.environ["SP_DATA"]); OUT = SPD / "shower_vertex_audit" / "official_ncdelta"; RAW = OUT / "raw"; P8 = SPD / "other_bdt_audit" / "official_ncdelta"
PLD = REPO / "plots" / "shower_vertex_audit"; SUMD = REPO / "tables" / "shower_vertex_audit"
for d in (PLD, SUMD, OUT):
    d.mkdir(parents=True, exist_ok=True)
K = ["file_index", "ev"]; RSE = ["run", "subrun", "evt"]; SUMMARY: dict = {}
PROV = "official Gen2 NC-Delta | frozen Wire-Cell baseline (policy any) | TPC-box signal events with >= 1 candidate | descriptive audit, no selection changed"
TRUTH_LABEL = {0: "truth 0p", 1: "truth 1p", 2: "truth >=2p"}; TCOL = {0: "#0072B2", 1: "#D55E00", 2: "#009E73"}
CLS_COL = {"photon_no_reco_charge": "#999999", "photon_charge_outside_candidates": "#cccccc", "photon_fragmented": "#8c564b", "photon_in_other_candidate": "#F0E442", "photon_particle_row_missing": "#56B4E9",
           "photon_as_track": "#0072B2", "photon_shower_typed_non_electron": "#CC79A7", "photon_shower_below_20MeV": "#009E73", "photon_shower_not_in_main_vertex_set": "#D55E00",
           "pass_photon_shower_in_passing_candidate": "#000000", "pass_not_via_signal_photon_shower": "#555555"}
OUTCOMES = ["pass_photon_shower_in_passing_candidate", "pass_not_via_signal_photon_shower"] + SA.FAIL_CLASSES


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def cp(k, n):
    return X.binom_ci(int(k), int(n)) if n else (np.nan,) * 3


def save(fig, name):
    PS.annotate(fig, PROV, extra=PS.PRELIM); fig.savefig(PLD / name, bbox_inches="tight"); plt.close(fig)


def load_events():
    raw = {k: pd.read_parquet(RAW / f"{k}.parquet") for k in ("cand", "kine", "pf", "seg", "shlist", "pho_ov", "ov_all", "truth")}
    assoc = ST.photon_association(raw)
    t = pd.read_parquet(SPD / "spine_harmonization" / "official_ncdelta" / "event_flags_and_table.parquet")
    d6 = pd.read_parquet(SPD / "differential_efficiency" / "official_ncdelta" / "event_table_tpc_box_any.parquet",
                         columns=RSE + ["conv_distance_cm", "photon_end_class", "photon_end_process", "photon_ex", "photon_ey", "photon_ez", "photon_sx", "photon_sy", "photon_sz"])     # photon_px/py/pz are already in the Phase-7 table
    t = t.merge(d6, on=RSE, how="left")
    e = t[t.tpc_box].copy()
    return raw, assoc, e


def main():
    raw, assoc, E_all = load_events()
    cand = raw["cand"].copy(); cand["nu_index"] = cand.nu_index.astype(int)
    E_all["has_candidate"] = E_all.A_candidate.astype(bool); E_all["pass_n20"] = E_all.A_n20mev.astype(bool)
    E = E_all[E_all.has_candidate].merge(assoc, on=K, how="inner", validate="one_to_one"); assert len(E) == 11331
    mx = cand.groupby(K).shw_sp_n_20mev_showers.max().rename("max_n20").reset_index(); E = E.merge(mx, on=K, how="left")
    assert ((E.max_n20 > 0) == E.pass_n20).all(), "A_n20mev disagrees with the per-candidate tagger field"
    # signal-matched candidate (baseline association): the candidate whose dominant truth neutrino vertex is within 5 cm of the signal vertex
    E["dom_is_sig"] = [None if not bool(a) else (bool(int(d) == int(m)) if pd.notna(d) else None) for a, d, m in zip(E.A_matched, E.dom_nu, E.match_cand_nu)]
    # n20 of the dominant candidate
    dn = cand[K + ["nu_index", "shw_sp_n_20mev_showers", "shw_sp_filled", "shw_sp_shw_vtx_dis", "shw_sp_energy", "kine_nu_x_corr", "kine_nu_y_corr", "kine_nu_z_corr"]].rename(columns={"nu_index": "dom_nu", "shw_sp_n_20mev_showers": "dom_cand_n20", "shw_sp_filled": "dom_cand_filled", "shw_sp_shw_vtx_dis": "dom_cand_gap"})
    E = E.merge(dn[K + ["dom_nu", "dom_cand_n20", "dom_cand_filled", "dom_cand_gap"]], on=K + ["dom_nu"], how="left")
    ftype = lambda r: int(r.kine_particle_type) if pd.notna(r.kine_particle_type) else 0
    out = []
    for r in E.itertuples():
        is_sh = bool(r.kine_particle_is_shower == 1); pdg = ftype(r); en = float(r.kine_energy_particle) if pd.notna(r.kine_energy_particle) else 0.0
        if r.pass_n20:
            via = (r.has_kine_row and is_sh and pdg == 11 and en > 20 and pd.notna(r.dom_cand_n20) and r.dom_cand_n20 > 0 and r.dominant_fraction >= SA.DOMINANT_FRAC_MIN)
            out.append("pass_photon_shower_in_passing_candidate" if via else "pass_not_via_signal_photon_shower")
        else:
            out.append(SA.classify_failure(r.q_total, r.q_in_cands, r.dominant_fraction, r.dom_is_sig, bool(r.has_kine_row), is_sh, pdg, en))
    E["outcome"] = out
    # state of the dominant photon object for EVERY event (same hierarchy as the failure taxonomy, ignoring whether the event passes): used to characterise 'pass_not_via_signal_photon_shower'
    E["photon_object_state"] = [SA.classify_failure(r.q_total, r.q_in_cands, r.dominant_fraction, r.dom_is_sig, bool(r.has_kine_row), bool(r.kine_particle_is_shower == 1), ftype(r),
                                                    float(r.kine_energy_particle) if pd.notna(r.kine_energy_particle) else 0.0) for r in E.itertuples()]
    n_fail = int((~E.pass_n20).sum()); n_pass = int(E.pass_n20.sum())
    assert (len(E), n_pass, n_fail) == (11331, 8080, 3251), (len(E), n_pass, n_fail)
    assert set(E.outcome) <= set(OUTCOMES) and E.outcome.notna().all()
    assert int(E.outcome.isin(SA.FAIL_CLASSES).sum()) == 3251

    # ---- Task 1/4: taxonomy tables
    groups = {"all": np.ones(len(E), bool), "truth 0p": (E.truth35 == 0).to_numpy(), "truth 1p": (E.truth35 == 1).to_numpy(), "truth >=2p": (E.truth35 == 2).to_numpy(), "Delta0": (E.delta_label == "Delta0").to_numpy(), "Delta+": (E.delta_label == "Delta+").to_numpy()}
    rows = []
    for g, m in groups.items():
        nc = int(m.sum()); nf = int((m & ~E.pass_n20.to_numpy()).sum())
        for o in OUTCOMES:
            k = int((m & (E.outcome == o).to_numpy()).sum()); f, l, h = cp(k, nc)
            rows.append(dict(group=g, outcome=o, n=k, n_candidate_stage=nc, frac_of_candidate_stage=f, lo68=l, hi68=h, n_failing=nf, frac_of_failing=(k / nf if (nf and o in SA.FAIL_CLASSES) else np.nan)))
    T = pd.DataFrame(rows); T.to_csv(OUT / "taxonomy.csv", index=False); T.to_csv(SUMD / "taxonomy.csv", index=False); SUMMARY["taxonomy"] = T.round(4).to_dict("records")
    SUMMARY["accounting"] = dict(denominator_tpc_box=int(len(E_all)), candidate_stage=len(E), pass_n20=n_pass, fail_n20=n_fail, missing_production_event_in_population=int((~E.arrived).sum()),
                                 baseline_first_fail_no_20mev_shower=3251, fail_classes_sum=int(E.outcome.isin(SA.FAIL_CLASSES).sum()), by_class={k: int(v) for k, v in E[~E.pass_n20].outcome.value_counts().items()})
    fin = E[E.A_final.astype(bool)]; SUMMARY["final_selected_photon_object"] = dict(n=len(fin), outcome={k: int(v) for k, v in fin.outcome.value_counts().items()}, photon_object_state={k: int(v) for k, v in fin.photon_object_state.value_counts().items()},
                                                                                     by_truth={TRUTH_LABEL[int(k)]: {o: int(v) for o, v in fin[fin.truth35 == k].outcome.value_counts().items()} for k in (0, 1, 2)})
    pn = E[E.outcome == "pass_not_via_signal_photon_shower"]; SUMMARY["pass_not_via_breakdown"] = {k: int(v) for k, v in pn.photon_object_state.value_counts().items()}
    SUMMARY["pass_not_via_breakdown_by_truth"] = {TRUTH_LABEL[int(k)]: {o: int(v) for o, v in pn[pn.truth35 == k].photon_object_state.value_counts().items()} for k in (0, 1, 2)}
    fail_ev = E[~E.pass_n20]; sens = []
    for of, df_ in ((0.5, 0.5), (0.25, 0.5), (0.75, 0.5), (0.5, 0.33), (0.5, 0.66), (0.25, 0.33), (0.75, 0.66)):
        cl = [SA.classify_failure(r.q_total, r.q_in_cands, r.dominant_fraction, r.dom_is_sig, bool(r.has_kine_row), bool(r.kine_particle_is_shower == 1), ftype(r), float(r.kine_energy_particle) if pd.notna(r.kine_energy_particle) else 0.0, outside_frac_min=of, dominant_frac_min=df_) for r in fail_ev.itertuples()]
        vc = pd.Series(cl).value_counts(); assert int(vc.sum()) == 3251
        sens.append(dict(outside_frac_min=of, dominant_frac_min=df_, **{o: int(vc.get(o, 0)) for o in SA.FAIL_CLASSES}))
    TS = pd.DataFrame(sens); TS.to_csv(OUT / "taxonomy_threshold_sensitivity.csv", index=False); TS.to_csv(SUMD / "taxonomy_threshold_sensitivity.csv", index=False); SUMMARY["taxonomy_threshold_sensitivity"] = TS.to_dict("records")
    E.to_parquet(OUT / "event_taxonomy.parquet", index=False)
    print(E[~E.pass_n20].outcome.value_counts().to_string())
    dependence(E, E_all)
    G = vertex_block(E, cand, raw)
    connectivity_block(E, G, cand)
    hadronic_block(E, G)
    pop = detachment_block(E, G, cand, raw)
    other_link_block(G, cand, pop)
    energy_block(E, raw)
    high_energy_block(E, raw)
    finish(E)
    return raw, assoc, E, E_all, cand


def frac_table(df, var, edges, label):
    """fraction of the candidate-stage events of each bin in each outcome (closes to 1 per bin)"""
    b = DF.assign_bins(df[var].to_numpy(), edges); rows = []
    for i in range(len(edges) - 1):
        m = (b == i); n = int(m.sum())
        for o in OUTCOMES:
            k = int((m & (df.outcome == o).to_numpy()).sum()); f, l, h = cp(k, n)
            rows.append(dict(variable=label, bin=i, lo=edges[i], hi=edges[i + 1], outcome=o, n=k, n_bin=n, fraction=f, lo68=l, hi68=h))
    t = pd.DataFrame(rows); chk = t.groupby("bin").n.sum() - t.groupby("bin").n_bin.first(); assert (chk == 0).all(), f"outcome accounting does not close in {label}"; return t


def stack_plot(ax, t, outcomes, xlabel, min_n=10, logx=False):
    bins = sorted(t.bin.unique()); edges = [t[t.bin == b].lo.iloc[0] for b in bins] + [t[t.bin == bins[-1]].hi.iloc[0]]
    bottom = np.zeros(len(bins))
    for o in outcomes:
        d = t[t.outcome == o].sort_values("bin"); v = np.where(d.n_bin.to_numpy() >= min_n, d.fraction.to_numpy(), 0.0)
        ax.bar(edges[:-1], v, width=np.diff(edges), bottom=bottom, align="edge", color=CLS_COL[o], edgecolor="white", linewidth=0.4, label=o.replace("photon_", "").replace("_", " ")); bottom += v
    ax.set_ylim(0, 1); ax.set_xlabel(xlabel); ax.set_ylabel("fraction of candidate-stage events")
    if logx:
        ax.set_xscale("symlog", linthresh=5)


def dependence(E, E_all):
    # ---- Task 5: energy
    ee = DF.load_bins()["variables"]["photon_energy_mev"]["edges"]; TE = frac_table(E, "photon_energy_mev", ee, "photon_energy_mev"); TE.to_csv(OUT / "taxonomy_vs_photon_energy.csv", index=False)
    hi_rows = []
    for emin in (0, 100, 200, 400):
        m = (E.photon_energy_mev > emin).to_numpy(); nc = int(m.sum()); nf = int((m & ~E.pass_n20.to_numpy()).sum())
        for o in OUTCOMES:
            k = int((m & (E.outcome == o).to_numpy()).sum()); hi_rows.append(dict(E_gamma_above_mev=emin, outcome=o, n=k, n_candidate_stage=nc, frac_of_candidate_stage=k / nc, n_failing=nf, frac_of_failing=(k / nf if o in SA.FAIL_CLASSES else np.nan)))
    H = pd.DataFrame(hi_rows); H.to_csv(OUT / "taxonomy_high_energy.csv", index=False); H.to_csv(SUMD / "taxonomy_high_energy.csv", index=False); SUMMARY["high_energy"] = H.round(4).to_dict("records")
    SUMMARY["shower_stage_efficiency_vs_energy"] = {f">{e}": dict(n=int((E.photon_energy_mev > e).sum()), pass_fraction=float(E.pass_n20[E.photon_energy_mev > e].mean())) for e in (0, 100, 200, 400)}
    fig, ax = PS.figure(1, 2, size=(13, 4.2))
    stack_plot(ax[0][0], TE, OUTCOMES, "True photon energy [MeV]"); ax[0][0].set_title("all candidate-stage events", fontsize=9)
    sub = frac_table(E[E.truth35 == 1], "photon_energy_mev", ee, "e1"); stack_plot(ax[0][1], sub, OUTCOMES, "True photon energy [MeV]"); ax[0][1].set_title("truth 1p", fontsize=9)
    h, l = ax[0][0].get_legend_handles_labels(); fig.legend(h[::-1], l[::-1], loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=7); fig.tight_layout(); save(fig, "taxonomy_vs_photon_energy.png")
    # ---- Task 6: photon end class / conversion distance
    rows = []
    for c in ("conv", "other_interaction", "left_volume"):
        m = (E.photon_end_class == c).to_numpy(); nc = int(m.sum())
        for o in OUTCOMES:
            k = int((m & (E.outcome == o).to_numpy()).sum()); f, l, h = cp(k, nc); rows.append(dict(photon_end_class=c, outcome=o, n=k, n_candidate_stage=nc, fraction=f, lo68=l, hi68=h))
    C6 = pd.DataFrame(rows); C6.to_csv(OUT / "taxonomy_by_photon_end_class.csv", index=False); C6.to_csv(SUMD / "taxonomy_by_photon_end_class.csv", index=False); SUMMARY["by_end_class"] = C6.round(4).to_dict("records")
    ce = DF.load_bins()["variables"]["conv_distance_cm"]["edges"]; conv = E[E.photon_end_class == "conv"]
    TC = frac_table(conv, "conv_distance_cm", ce, "conv_distance_cm"); TC.to_csv(OUT / "taxonomy_vs_conv_distance.csv", index=False); TC.to_csv(SUMD / "taxonomy_vs_conv_distance.csv", index=False)
    rows = []
    for g, mm in (("all", np.ones(len(conv), bool)), ("truth 0p", (conv.truth35 == 0).to_numpy()), ("truth 1p", (conv.truth35 == 1).to_numpy())):
        b = DF.assign_bins(conv.conv_distance_cm.to_numpy(), ce)
        for i in range(len(ce) - 1):
            m = mm & (b == i); n = int(m.sum()); k = int((m & conv.pass_n20.to_numpy()).sum()); f, l, h = cp(k, n); rows.append(dict(group=g, bin=i, lo=ce[i], hi=ce[i + 1], n=n, pass_n20=k, pass_fraction=f, lo68=l, hi68=h))
    PC = pd.DataFrame(rows); PC.to_csv(OUT / "shower_pass_vs_conv_distance.csv", index=False); PC.to_csv(SUMD / "shower_pass_vs_conv_distance.csv", index=False); SUMMARY["pass_vs_conv_distance"] = PC.round(4).to_dict("records")
    fig, ax = PS.figure(1, 2, size=(13, 4.2)); stack_plot(ax[0][0], TC, OUTCOMES, "True conversion distance [cm] (in-volume pair conversions)"); ax[0][0].set_title("outcome composition", fontsize=9)
    for g, col in (("all", "k"), ("truth 0p", TCOL[0]), ("truth 1p", TCOL[1])):
        d = PC[(PC.group == g) & (PC.n >= 10)]; PS.eff_errorbar(ax[0][1], d.lo, d.hi, d.pass_fraction, d.lo68, d.hi68, label=g, color=col, offset=0.08 * (["all", "truth 0p", "truth 1p"].index(g) - 1))
    ax[0][1].set_ylim(0, 1); ax[0][1].set_xlabel("True conversion distance [cm]"); ax[0][1].set_ylabel("shower-stage pass fraction (given a candidate)"); ax[0][1].legend(fontsize=7)
    h, l = ax[0][0].get_legend_handles_labels(); fig.legend(h[::-1], l[::-1], loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=7); fig.tight_layout(); save(fig, "taxonomy_vs_conv_distance.png")
    # ---- Task 7: edges (no candidate separated from candidate-but-shower-fail)
    A = E_all.copy(); A = A.merge(E[K + ["outcome"]], on=K, how="left"); A["outcome_ext"] = np.where(A.has_candidate, A.outcome, "no_candidate")
    A["dist_boundary"] = [float(SA.distance_to_boundary(x, y, z)) for x, y, z in zip(A.vtx_x, A.vtx_y, A.vtx_z)]
    rows = []; edges_map = {"vtx_x": DF.load_bins()["variables"]["vtx_x"]["edges"], "vtx_y": DF.load_bins()["variables"]["vtx_y"]["edges"], "vtx_z": DF.load_bins()["variables"]["vtx_z"]["edges"], "dist_boundary": [0, 10, 25, 50, 75, 100, 150, 250]}
    for var, edges in edges_map.items():
        b = DF.assign_bins(A[var].to_numpy(), edges)
        for i in range(len(edges) - 1):
            m = (b == i); n = int(m.sum())
            for o in ["no_candidate"] + OUTCOMES:
                k = int((m & (A.outcome_ext == o).to_numpy()).sum()); f, l, h = cp(k, n); rows.append(dict(variable=var, bin=i, lo=edges[i], hi=edges[i + 1], outcome=o, n=k, n_bin=n, fraction=f, lo68=l, hi68=h))
    EG = pd.DataFrame(rows); EG.to_csv(OUT / "taxonomy_vs_edges.csv", index=False)
    CLS_COL["no_candidate"] = "#ffffff"
    g3 = []
    for var in edges_map:
        for i in sorted(EG[EG.variable == var].bin.unique()):
            d = EG[(EG.variable == var) & (EG.bin == i)]; n = d.n_bin.iloc[0]; nc = d[d.outcome == "no_candidate"].n.iloc[0]; npass = d[d.outcome.str.startswith("pass_")].n.sum(); nfail = n - nc - npass
            g3.append(dict(variable=var, bin=i, lo=d.lo.iloc[0], hi=d.hi.iloc[0], n_bin=int(n), no_candidate=nc / n, candidate_shower_fail=nfail / n, shower_pass=npass / n))
    G3 = pd.DataFrame(g3); G3.to_csv(OUT / "edge_three_way.csv", index=False); G3.to_csv(SUMD / "edge_three_way.csv", index=False); SUMMARY["edge_three_way"] = G3.round(4).to_dict("records")
    fig, ax = PS.figure(1, 2, size=(13, 4.2)); d = G3[G3.variable == "dist_boundary"]; edges = list(d.lo) + [d.hi.iloc[-1]]; bottom = np.zeros(len(d))
    for nm, col in (("no_candidate", "#cccccc"), ("candidate_shower_fail", "#D55E00"), ("shower_pass", "#000000")):
        ax[0][0].bar(d.lo, d[nm], width=np.diff(edges), bottom=bottom, align="edge", color=col, edgecolor="white", label=nm.replace("_", " ")); bottom += d[nm].to_numpy()
    ax[0][0].set_xlabel("distance of the true vertex to the nearest TPC-box face [cm]"); ax[0][0].set_ylabel("fraction of the TPC-box signal events"); ax[0][0].legend(fontsize=7); ax[0][0].set_ylim(0, 1)
    sub = EG[(EG.variable == "dist_boundary") & (EG.outcome.isin(SA.FAIL_CLASSES))]; fr = {}
    d2 = sub.copy(); d2["n_fail_bin"] = d2.groupby("bin").n.transform("sum"); d2["f"] = d2.n / d2.n_fail_bin.replace(0, np.nan)
    bottom = np.zeros(len(d))
    for o in SA.FAIL_CLASSES:
        v = d2[d2.outcome == o].sort_values("bin").f.fillna(0).to_numpy(); ax[0][1].bar(d.lo, v, width=np.diff(edges), bottom=bottom, align="edge", color=CLS_COL[o], edgecolor="white", label=o.replace("photon_", "").replace("_", " ")); bottom += v
    ax[0][1].set_xlabel("distance to the nearest TPC-box face [cm]"); ax[0][1].set_ylabel("composition of the shower-stage failures"); ax[0][1].set_ylim(0, 1)
    h, l = ax[0][1].get_legend_handles_labels(); fig.legend(h[::-1], l[::-1], loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=7); fig.tight_layout(); save(fig, "taxonomy_vs_edges.png")



def smd_ks(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float); a = a[np.isfinite(a)]; b = b[np.isfinite(b)]
    pooled = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2) if len(a) > 1 and len(b) > 1 else np.nan
    return dict(n_a=len(a), n_b=len(b), median_a=float(np.median(a)), median_b=float(np.median(b)), smd=float((b.mean() - a.mean()) / pooled) if pooled else np.nan, ks=float(stats.ks_2samp(a, b).statistic),
                wasserstein=float(stats.wasserstein_distance(a, b)))


def vertex_block(E, cand, raw):
    """Task 8/11: reco neutrino vertex of the signal-matched candidate relative to the true interaction vertex and the true conversion point."""
    v = cand[K + ["nu_index", "kine_nu_x_corr", "kine_nu_y_corr", "kine_nu_z_corr", "shw_sp_filled", "shw_sp_shw_vtx_dis", "shw_sp_n_20mev_showers"]].rename(columns={"nu_index": "match_cand_nu", "shw_sp_filled": "sig_filled", "shw_sp_shw_vtx_dis": "sig_gap", "shw_sp_n_20mev_showers": "sig_n20"})
    G = E[E.A_matched.astype(bool)].merge(v, on=K + ["match_cand_nu"], how="inner")
    kn = raw["kine"]; npr = kn[(kn.kine_particle_type == 2212) & (kn.kine_energy_particle > 35)].groupby(K + ["cand_pos"]).size().rename("reco_np35").reset_index().rename(columns={"cand_pos": "sig_cand_pos"})
    cp_ = cand[K + ["cand_pos", "nu_index"]].rename(columns={"nu_index": "match_cand_nu", "cand_pos": "sig_cand_pos"}); G = G.merge(cp_, on=K + ["match_cand_nu"], how="left").merge(npr, on=K + ["sig_cand_pos"], how="left"); G["reco_np35"] = G.reco_np35.fillna(0).astype(int)
    rows = []
    for r in G.itertuples():
        vr = [r.kine_nu_x_corr, r.kine_nu_y_corr, r.kine_nu_z_corr]; vt = [r.vtx_x, r.vtx_y, r.vtx_z]; u = [r.photon_px, r.photon_py, r.photon_pz]
        ct = [r.photon_ex, r.photon_ey, r.photon_ez] if r.photon_end_class == "conv" else vt
        d = SA.decompose_vertex(vr, vt, ct, u)
        if r.photon_end_class != "conv":
            d.update(d_conv=np.nan, d_conv_true=np.nan, frac_axis=np.nan, perp_axis=np.nan); d["prox"] = "no_conversion_point"
        else:
            d["prox"] = SA.classify_proximity(d["d_vertex"], d["d_conv"], d["d_conv_true"])
            for tol in (3.0, 10.0):
                d[f"prox_tol{int(tol)}"] = SA.classify_proximity(d["d_vertex"], d["d_conv"], d["d_conv_true"], tol)
        # reco shower start (PF node of the dominant photon shower) relative to the true conversion point and to the reco vertex
        if pd.notna(r.pf_start_x):
            s0 = np.array([r.pf_start_x, r.pf_start_y, r.pf_start_z]); d["shw_start_to_reco_vtx"] = float(np.linalg.norm(s0 - np.array(vr))); d["shw_start_to_true_conv"] = float(np.linalg.norm(s0 - np.array(ct))) if r.photon_end_class == "conv" else np.nan
            uu = np.array(u) / np.linalg.norm(u); d["vtx_minus_shw_start_along_photon"] = float((np.array(vr) - s0) @ uu)
        rows.append(d)
    G = pd.concat([G.reset_index(drop=True), pd.DataFrame(rows)], axis=1)
    G["attached_tagger"] = np.where(G.sig_filled == 1, G.sig_gap == 0, np.nan); G["anchored5"] = G.d_vertex <= 5.0
    G.to_parquet(OUT / "vertex_geometry.parquet", index=False)
    cls = {0: "truth 0p", 1: "truth 1p", 2: "truth >=2p"}
    rows = []
    for var in ("d_vertex", "parallel", "perp", "d_conv", "frac_axis", "shw_start_to_reco_vtx", "shw_start_to_true_conv", "vtx_minus_shw_start_along_photon"):
        for k in (0, 1, 2):
            x = G[(G.truth35 == k)][var].dropna()
            if len(x):
                rows.append(dict(variable=var, group=cls[k], n=len(x), median=x.median(), q16=x.quantile(.16), q84=x.quantile(.84), mean=x.mean()))
    VD = pd.DataFrame(rows); VD.to_csv(OUT / "vertex_distributions.csv", index=False); VD.to_csv(SUMD / "vertex_distributions.csv", index=False); SUMMARY["vertex_distributions"] = VD.round(3).to_dict("records")
    eff = []
    for var in ("d_vertex", "parallel", "perp", "d_conv", "frac_axis", "shw_start_to_reco_vtx", "vtx_minus_shw_start_along_photon"):
        for a, b in ((0, 1), (1, 2), (0, 2)):
            eff.append(dict(variable=var, a=cls[a], b=cls[b], **smd_ks(G[G.truth35 == a][var].dropna(), G[G.truth35 == b][var].dropna())))
    EF = pd.DataFrame(eff); EF.to_csv(OUT / "vertex_effect_sizes.csv", index=False); EF.to_csv(SUMD / "vertex_effect_sizes.csv", index=False); SUMMARY["vertex_effect_sizes"] = EF.round(3).to_dict("records")
    pr = []
    for g_, m in {**{cls[k]: (G.truth35 == k).to_numpy() for k in (0, 1, 2)}}.items():
        for stratum, sm in (("all", np.ones(len(G), bool)), ("shower-stage pass", G.pass_n20.to_numpy()), ("shower-stage fail", ~G.pass_n20.to_numpy()), ("tagger attached", (G.attached_tagger == 1).to_numpy()), ("tagger detached", (G.attached_tagger == 0).to_numpy())):
            mm = m & sm; n = int(mm.sum())
            for col in ("prox", "prox_tol3", "prox_tol10"):
                if col not in G:
                    continue
                for c in sorted(G[col].dropna().unique()):
                    k = int((mm & (G[col] == c).to_numpy()).sum()); f, l, h = cp(k, n); pr.append(dict(group=g_, stratum=stratum, tolerance_col=col, proximity=c, n=k, n_group=n, fraction=f, lo68=l, hi68=h))
    PR = pd.DataFrame(pr); PR.to_csv(OUT / "vertex_proximity_classes.csv", index=False); PR.to_csv(SUMD / "vertex_proximity_classes.csv", index=False); SUMMARY["vertex_proximity"] = PR[PR.tolerance_col == "prox"].round(4).to_dict("records")
    SUMMARY["vertex_events"] = dict(matched_candidate_events=len(G), conv_events=int((G.photon_end_class == "conv").sum()), anchored5_by_class={cls[k]: float(G[G.truth35 == k].anchored5.mean()) for k in (0, 1, 2)})
    # figures: longitudinal displacement and proximity
    fig, ax = PS.figure(1, 3, size=(15, 4.0)); bins = np.linspace(-20, 80, 51)
    for k in (0, 1, 2):
        x = G[G.truth35 == k].parallel.clip(-20, 80); ax[0][0].hist(x, bins=bins, density=True, histtype="step", color=TCOL[k], lw=1.6, label=f"{cls[k]} (N={len(x)})")
    ax[0][0].set_xlabel("(V_reco - V_true) along the true photon direction [cm] (clipped)"); ax[0][0].set_ylabel("normalised"); ax[0][0].legend(fontsize=7); ax[0][0].set_title("longitudinal vertex displacement", fontsize=9)
    for k in (0, 1, 2):
        x = np.sort(G[G.truth35 == k].d_vertex.clip(0, 100).to_numpy()); ax[0][1].plot(x, np.arange(1, len(x) + 1) / len(x), color=TCOL[k], label=cls[k])
    ax[0][1].set_xlabel("|V_reco - V_true| [cm]"); ax[0][1].set_ylabel("cumulative fraction"); ax[0][1].legend(fontsize=7)
    d = PR[(PR.tolerance_col == "prox") & (PR.stratum == "all")]; cats = ["interaction_vertex", "conversion_point", "between", "neither", "not_separable", "no_conversion_point"]; cc = {"interaction_vertex": "#D55E00", "conversion_point": "#0072B2", "between": "#F0E442", "neither": "#999999", "not_separable": "#dddddd", "no_conversion_point": "#ffffff"}
    bottom = np.zeros(3)
    for c in cats:
        v_ = np.array([d[(d.group == cls[k]) & (d.proximity == c)].fraction.sum() for k in (0, 1, 2)]); ax[0][2].bar(range(3), v_, bottom=bottom, color=cc[c], edgecolor="white", label=c.replace("_", " ")); bottom += v_
    ax[0][2].set_xticks(range(3)); ax[0][2].set_xticklabels([cls[k] for k in (0, 1, 2)], fontsize=8); ax[0][2].set_ylim(0, 1); ax[0][2].set_ylabel("fraction of matched-candidate events"); ax[0][2].legend(fontsize=6, loc="upper right")
    ax[0][2].set_title("reco vertex proximity (tolerance 5 cm)", fontsize=9)
    fig.tight_layout(); save(fig, "vertex_longitudinal_and_proximity.png")
    return G


def pf_state_label(row):
    if bool(row.dom_is_sig is False):
        return "E_shower_in_other_candidate"
    if not row.has_kine_row or row.kine_particle_is_shower != 1 or int(row.kine_particle_type) != 11 or row.dominant_fraction < SA.DOMINANT_FRAC_MIN:
        return "F_no_clean_electron_shower_object"
    return {"root": "A_attached_at_vertex_root", "photon_node_at_vertex": "B_detached_photon_node_at_vertex", "deeper": "C_connected_through_other_particle", "none": "D_no_pf_path_in_candidate"}.get(row.pf_state, "F_no_clean_electron_shower_object")


def connectivity_block(E, G, cand):
    """Task 9: vertex-connectivity states of the dominant signal-photon shower (PF-tree based, validated against shw_sp_shw_vtx_dis)."""
    E["conn_state"] = [pf_state_label(r) for r in E.itertuples()]
    states = sorted(E.conn_state.unique()); rows = []
    for g, m in {"all": np.ones(len(E), bool), "truth 0p": (E.truth35 == 0).to_numpy(), "truth 1p": (E.truth35 == 1).to_numpy(), "truth >=2p": (E.truth35 == 2).to_numpy()}.items():
        n = int(m.sum())
        for st in states:
            k = int((m & (E.conn_state == st).to_numpy()).sum()); f, l, h = cp(k, n); rows.append(dict(group=g, state=st, n=k, n_group=n, fraction=f, lo68=l, hi68=h))
    C = pd.DataFrame(rows); C.to_csv(OUT / "connectivity_states.csv", index=False); C.to_csv(SUMD / "connectivity_states.csv", index=False); SUMMARY["connectivity_states"] = C.round(4).to_dict("records")
    # validation of the PF state against the tagger's own shw_sp_shw_vtx_dis (candidates with a filled max shower whose row energy equals shw_sp_energy)
    kn = pd.read_parquet(RAW / "kine.parquet"); pf = pd.read_parquet(RAW / "pf.parquet"); pf["nu_index"] = pf.nu_index.astype(int)
    f = cand[cand.shw_sp_filled == 1].merge(kn[(kn.kine_particle_is_shower == 1) & (kn.kine_particle_type == 11)], on=["file_index", "ev", "cand_pos"])
    f = f[np.abs(f.kine_energy_particle - f.shw_sp_energy) < 1e-3].drop_duplicates(["file_index", "ev", "cand_pos"])
    pfn = pf[pf.kine_index >= 0].rename(columns={"kine_index": "row"}).sort_values(K + ["nu_index", "row", "depth"]).drop_duplicates(K + ["nu_index", "row"])
    par = pf[K + ["nu_index", "node_id", "parent_id", "is_pseudo"]].rename(columns={"node_id": "parent_id", "parent_id": "gp_id", "is_pseudo": "par_pseudo"}).drop_duplicates(K + ["nu_index", "parent_id"])
    f = f.merge(pfn[K + ["nu_index", "row", "depth", "parent_id"]], on=K + ["nu_index", "row"], how="left").merge(par, on=K + ["nu_index", "parent_id"], how="left")
    f["pfs"] = [SA.pf_attachment_state(bool(pd.notna(d)), int(d) if pd.notna(d) else 0, bool(p == 1), int(g) if pd.notna(g) else 0) for d, p, g in zip(f.depth, f.par_pseudo, f.gp_id)]
    V = pd.crosstab(f.pfs, f.shw_sp_shw_vtx_dis == 0); V.to_csv(OUT / "pf_state_vs_tagger_gap.csv"); SUMMARY["pf_state_vs_tagger_gap"] = {str(k): v for k, v in V.to_dict().items()}
    # figure: connectivity states by truth class
    fig, ax = PS.figure(1, 1, size=(8, 4.2)); a = ax[0][0]; colors = ["#000000", "#D55E00", "#0072B2", "#999999", "#F0E442", "#cccccc"]
    bottom = np.zeros(3)
    for st, col in zip(states, colors):
        v_ = np.array([C[(C.group == g) & (C.state == st)].fraction.sum() for g in ("truth 0p", "truth 1p", "truth >=2p")]); a.bar(range(3), v_, bottom=bottom, color=col, edgecolor="white", label=st); bottom += v_
    a.set_xticks(range(3)); a.set_xticklabels(["truth 0p", "truth 1p", "truth >=2p"]); a.set_ylim(0, 1); a.set_ylabel("fraction of candidate-stage events"); a.legend(fontsize=6, loc="center left", bbox_to_anchor=(1.0, 0.5))
    a.set_title("connectivity state of the dominant signal-photon object", fontsize=9); fig.tight_layout(); save(fig, "connectivity_states.png")


def hadronic_block(E, G):
    """Task 10: truth-1p proton-origin categories vs vertex location, photon attachment state and shower-stage efficiency."""
    po = OUT.parent.parent / "other_bdt_audit" / "official_ncdelta" / "proton_origin_all_candidate_stage.parquet"
    if not po.exists():
        SUMMARY["hadronic"] = "unavailable: proton_origin_all_candidate_stage.parquet missing"; return
    P = pd.read_parquet(po); E1 = E[E.truth35 == 1].merge(P[RSE + ["origin", "decay_nucleon_pdg"]], on=RSE, how="left"); E1["origin"] = E1.origin.fillna("missing")
    G1 = G[G.truth35 == 1].merge(P[RSE + ["origin"]], on=RSE, how="left"); G1["origin"] = G1.origin.fillna("missing")
    rows = []
    for dn in ("Delta+", "Delta0", "all"):
        for og in ["decay_proton", "fsi_created", "ambiguous", "not_from_decay", "n_protons_ke!=1"]:
            m = (E1.origin == og) & ((E1.delta_label == dn) if dn != "all" else True); n = int(m.sum())
            if n < 5:
                continue
            g1 = G1[(G1.origin == og) & ((G1.delta_label == dn) if dn != "all" else True)]
            kp = int(E1.pass_n20[m].sum()); f, l, h = cp(kp, n)
            rows.append(dict(delta=dn, origin=og, n_events=n, shower_stage_pass=kp, pass_fraction=f, lo68=l, hi68=h, n_matched_vertex_events=len(g1), anchored5_fraction=float(g1.anchored5.mean()) if len(g1) else np.nan,
                             parallel_median=float(g1.parallel.median()) if len(g1) else np.nan, d_vertex_median=float(g1.d_vertex.median()) if len(g1) else np.nan,
                             frac_state_A=float((E1[m].conn_state == "A_attached_at_vertex_root").mean()), frac_state_B=float((E1[m].conn_state == "B_detached_photon_node_at_vertex").mean()), frac_state_C=float((E1[m].conn_state == "C_connected_through_other_particle").mean()),
                             frac_not_in_main_vertex_set=float((E1[m].outcome == "photon_shower_not_in_main_vertex_set").mean()), frac_typed_non_electron=float((E1[m].outcome == "photon_shower_typed_non_electron").mean()),
                             reco_proton_present=float((g1.reco_np35 > 0).mean()) if len(g1) else np.nan))
    HD = pd.DataFrame(rows); HD.to_csv(OUT / "hadronic_origin_table.csv", index=False); HD.to_csv(SUMD / "hadronic_origin_table.csv", index=False); SUMMARY["hadronic"] = HD.round(4).to_dict("records")
    # does a visible (reconstructed) proton anchor the vertex? truth-1p events by reco proton presence
    anc = []
    for rp in (0, 1):
        g = G[(G.truth35 == 1) & ((G.reco_np35 > 0) == bool(rp))]; anc.append(dict(truth="1p", reco_proton_present=bool(rp), n=len(g), anchored5=float(g.anchored5.mean()), parallel_median=float(g.parallel.median()), d_vertex_median=float(g.d_vertex.median()),
                                                                                  frac_interaction_vertex=float((g.prox == "interaction_vertex").mean()), frac_conversion_point=float((g.prox == "conversion_point").mean()), attached_tagger=float(g.attached_tagger.dropna().mean())))
    for rp in (0, 1):
        g = G[(G.truth35 == 0) & ((G.reco_np35 > 0) == bool(rp))]; anc.append(dict(truth="0p", reco_proton_present=bool(rp), n=len(g), anchored5=float(g.anchored5.mean()), parallel_median=float(g.parallel.median()), d_vertex_median=float(g.d_vertex.median()),
                                                                                  frac_interaction_vertex=float((g.prox == "interaction_vertex").mean()), frac_conversion_point=float((g.prox == "conversion_point").mean()), attached_tagger=float(g.attached_tagger.dropna().mean())))
    AN = pd.DataFrame(anc); AN.to_csv(OUT / "vertex_anchoring_by_reco_proton.csv", index=False); AN.to_csv(SUMD / "vertex_anchoring_by_reco_proton.csv", index=False); SUMMARY["vertex_anchoring_by_reco_proton"] = AN.round(4).to_dict("records")
    fig, ax = PS.figure(1, 2, size=(11, 4)); H = HD[HD.delta != "all"]; lab = [f"{r.delta}\n{r.origin}" for r in H.itertuples()]; x = np.arange(len(H))
    ax[0][0].bar(x, H.anchored5_fraction, color="#D55E00"); ax[0][0].set_xticks(x); ax[0][0].set_xticklabels(lab, fontsize=7); ax[0][0].set_ylabel("fraction with |V_reco - V_true| <= 5 cm"); ax[0][0].set_title("truth 1p: vertex anchored at the interaction vertex", fontsize=8)
    ax[0][1].errorbar(x, H.pass_fraction, yerr=[H.pass_fraction - H.lo68, H.hi68 - H.pass_fraction], fmt="o", color="k"); ax[0][1].set_xticks(x); ax[0][1].set_xticklabels(lab, fontsize=7); ax[0][1].set_ylabel("shower-stage pass fraction (given a candidate)"); ax[0][1].set_ylim(0, 1)
    fig.tight_layout(); save(fig, "proton_origin_vertex_and_shower_stage.png")


def load_population(E, cand):
    """Phase-8 population (events reaching `other`, TPC box, policy any) with the controlling candidate's vertex geometry and proton origin."""
    pop = pd.read_parquet(P8 / "population_events.parquet"); pop = pop[pop.cls <= 2].copy()
    v = cand[K + ["nu_index", "kine_nu_x_corr", "kine_nu_y_corr", "kine_nu_z_corr", "shw_sp_shw_vtx_dis", "shw_sp_filled", "shw_sp_n_20mev_showers"]].rename(columns={"nu_index": "c_nu_index", "kine_nu_x_corr": "rx", "kine_nu_y_corr": "ry", "kine_nu_z_corr": "rz"})
    pop = pop.merge(v[K + ["c_nu_index", "rx", "ry", "rz"]], on=K + ["c_nu_index"], how="left")
    need = [c for c in ["photon_px", "photon_py", "photon_pz", "photon_ex", "photon_ey", "photon_ez", "photon_end_class", "conv_distance_cm", "conn_state", "n_cand_with_photon", "pf_state"] if c not in pop.columns]
    pop = pop.merge(E[K + need + ["outcome"]].rename(columns={"outcome": "sh_outcome"}), on=K, how="left")
    rows = []
    for r in pop.itertuples():
        d = SA.decompose_vertex([r.rx, r.ry, r.rz], [r.vtx_x, r.vtx_y, r.vtx_z], [r.photon_ex, r.photon_ey, r.photon_ez] if r.photon_end_class == "conv" else [r.vtx_x, r.vtx_y, r.vtx_z], [r.photon_px, r.photon_py, r.photon_pz])
        d["prox"] = SA.classify_proximity(d["d_vertex"], d["d_conv"], d["d_conv_true"]) if r.photon_end_class == "conv" else "no_conversion_point"; rows.append(d)
    pop = pd.concat([pop.reset_index(drop=True), pd.DataFrame(rows)], axis=1)
    pop["detached"] = ~pop.connected.astype(bool); pop["anchored5"] = pop.d_vertex <= 5.0; pop["reco_p_present"] = (pop.reco_np35 > 0)
    po = P8 / "proton_origin_all_candidate_stage.parquet"
    if po.exists():
        pop = pop.merge(pd.read_parquet(po)[RSE + ["origin"]], on=RSE, how="left")
    return pop


def detachment_block(E, G, cand, raw):
    """Task 12: what explains the 28 % (truth 0p) vs 61 % (truth 1p) detached-shower fractions among events reaching `other`."""
    pop = load_population(E, cand); cls = {0: "truth 0p", 1: "truth 1p", 2: "truth >=2p"}
    rows = [dict(stratum="all", truth=cls[k], n=int((pop.cls == k).sum()), detached=float(pop.detached[pop.cls == k].mean())) for k in (0, 1, 2)]
    for nm, col in (("reco proton present", "reco_p_present"), ("vertex within 5 cm of the true vertex", "anchored5")):
        for val in (False, True):
            for k in (0, 1, 2):
                m = (pop.cls == k) & (pop[col] == val); rows.append(dict(stratum=f"{nm} = {val}", truth=cls[k], n=int(m.sum()), detached=float(pop.detached[m].mean()) if m.sum() else np.nan))
    for k in (0, 1):
        for rp in (False, True):
            for an in (False, True):
                m = (pop.cls == k) & (pop.reco_p_present == rp) & (pop.anchored5 == an); rows.append(dict(stratum=f"reco proton {rp} & anchored {an}", truth=cls[k], n=int(m.sum()), detached=float(pop.detached[m].mean()) if m.sum() else np.nan))
    conv = pop[pop.photon_end_class == "conv"]; ce = [0, 5, 10, 20, 30, 50, 1000]; b = DF.assign_bins(conv.conv_distance_cm.to_numpy(), ce)
    for k in (0, 1):
        for i in range(len(ce) - 1):
            m = ((conv.cls == k).to_numpy() & (b == i)); rows.append(dict(stratum=f"conversion distance {ce[i]}-{ce[i + 1]} cm", truth=cls[k], n=int(m.sum()), detached=float(conv.detached[m].mean()) if m.sum() else np.nan))
    if "origin" in pop:
        for og in ("decay_proton", "fsi_created", "ambiguous"):
            m = (pop.cls == 1) & (pop.origin == og); rows.append(dict(stratum=f"proton origin = {og}", truth="truth 1p", n=int(m.sum()), detached=float(pop.detached[m].mean())))
    D12 = pd.DataFrame(rows); D12.to_csv(OUT / "detachment_strata.csv", index=False); D12.to_csv(SUMD / "detachment_strata.csv", index=False); SUMMARY["detachment_strata"] = D12.round(4).to_dict("records")
    # exact accounting through the anchoring state: P(det) = P(anch) P(det|anch) + P(~anch) P(det|~anch)
    acc = {}
    for k in (0, 1):
        g = pop[pop.cls == k]; pa = float(g.anchored5.mean()); acc[cls[k]] = dict(p_anchored=pa, p_det_given_anchored=float(g.detached[g.anchored5].mean()), p_det_given_not_anchored=float(g.detached[~g.anchored5].mean()), p_detached=float(g.detached.mean()))
    SUMMARY["detachment_accounting_through_anchoring"] = acc
    # descriptive stepwise adjustment of the 1p - 0p detachment difference (observed association only)
    Q = pop[pop.cls <= 1].copy(); Q["truth_cat"] = Q.cls; Q["delta_pdg"] = np.where(Q.delta_label == "Delta0", 2114, 2214); Q["A_final"] = Q.detached
    Q["reco_p"] = Q.reco_p_present.astype(float); Q["is_conv"] = (Q.photon_end_class == "conv").astype(float); Q["conv_d"] = Q.conv_distance_cm.fillna(Q.conv_distance_cm.median()); Q["parallel_c"] = Q.parallel.clip(-20, 150); Q["d_vertex_c"] = Q.d_vertex.clip(0, 150)
    Q["anch"] = Q.anchored5.astype(float); Q["ncand"] = Q.n_candidates_total.astype(float)
    sets = {"none": [], "+ reco proton present": ["reco_p"], "+ vertex displacement along the photon": ["reco_p", "parallel_c", "d_vertex_c"], "+ vertex anchored (<=5 cm)": ["reco_p", "parallel_c", "d_vertex_c", "anch"],
            "+ conversion distance": ["reco_p", "parallel_c", "d_vertex_c", "anch", "conv_d", "is_conv"], "+ photon energy and angle": ["reco_p", "parallel_c", "d_vertex_c", "anch", "conv_d", "is_conv", "photon_energy_mev", "cos_theta_beam"],
            "+ candidate multiplicity": ["reco_p", "parallel_c", "d_vertex_c", "anch", "conv_d", "is_conv", "photon_energy_mev", "cos_theta_beam", "ncand"]}
    adj = {}
    for nm, f in sets.items():
        Qf = Q.dropna(subset=f) if f else Q
        adj[nm] = ({k: float(v) for k, v in DF.adjusted_difference(Qf, "truth_0p", "truth_1p", f, n_boot=100).items() if isinstance(v, (int, float))} if f else dict(raw_difference=float(Q[Q.cls == 1].detached.mean() - Q[Q.cls == 0].detached.mean())))
    SUMMARY["detachment_adjusted"] = adj
    fig, ax = PS.figure(1, 2, size=(12, 4.2)); a = ax[0][0]; labs = ["all", "reco proton absent", "reco proton present", "vertex anchored (<=5 cm)", "vertex NOT anchored"]; x = np.arange(len(labs)); w = 0.27
    for k in (0, 1, 2):
        vals = [D12[(D12.stratum == s_) & (D12.truth == cls[k])].detached.iloc[0] for s_ in ("all", "reco proton present = False", "reco proton present = True", "vertex within 5 cm of the true vertex = True", "vertex within 5 cm of the true vertex = False")]
        a.bar(x + (k - 1) * w, vals, w, color=TCOL[k], label=cls[k])
    a.set_xticks(x); a.set_xticklabels(labs, fontsize=7, rotation=20, ha="right"); a.set_ylabel("detached-shower fraction (events reaching `other`)"); a.set_ylim(0, 1); a.legend(fontsize=7)
    a = ax[0][1]; names = list(adj); vals = [adj[n].get("adjusted_difference", adj[n].get("raw_difference")) for n in names]
    lo = [adj[n].get("adjusted_lo68", vals[i]) for i, n in enumerate(names)]; hi = [adj[n].get("adjusted_hi68", vals[i]) for i, n in enumerate(names)]
    a.errorbar(range(len(names)), vals, yerr=[np.array(vals) - np.array(lo), np.array(hi) - np.array(vals)], fmt="o", color="k"); a.set_xticks(range(len(names))); a.set_xticklabels(names, rotation=35, ha="right", fontsize=7); a.axhline(0, color="k", lw=0.6)
    a.set_ylabel("detached fraction: truth 1p - truth 0p (adjusted)"); fig.tight_layout(); save(fig, "detachment_fraction_explained.png")
    return pop


def other_link_block(G, cand, pop):
    """Task 13: are 'detached 0p' and 'detached 1p' different reconstruction states? Links the reconstruction states to the Phase-8 `other` response (no SHAP is repeated)."""
    inc = pd.read_parquet(P8 / "official_candidates.parquet", columns=K + ["c_nu_index", "in_numu_1_score", "in_numu_score", "in_shw_sp_hol_2_min_angle", "in_shw_sp_shw_vtx_dis", "in_shw_sp_br2_sg_length", "in_shw_sp_lem_e_charge", "in_shw_sp_n_good_showers", "in_shw_sp_max_shw_dis", "other_score"])
    inc = inc.rename(columns={"other_score": "other_score_cand"}); X = pop.merge(inc, on=K + ["c_nu_index"], how="left", validate="one_to_one")
    X["hol2_default"] = X.in_shw_sp_hol_2_min_angle == 0
    det = X[X.detached & (X.cls <= 1)]; d0, d1 = det[det.cls == 0], det[det.cls == 1]
    rows = []
    for var, lab in (("in_numu_1_score", "numu_1_score"), ("in_numu_score", "numu_score"), ("in_shw_sp_shw_vtx_dis", "shw_sp_shw_vtx_dis"), ("in_shw_sp_max_shw_dis", "shw_sp_max_shw_dis"), ("in_shw_sp_n_good_showers", "n_good_showers"), ("in_shw_sp_lem_e_charge", "lem_e_charge"),
                     ("parallel", "vertex displacement along photon (cm)"), ("d_vertex", "|V_reco - V_true| (cm)"), ("other_score", "frozen other score")):
        rows.append(dict(variable=lab, **smd_ks(d0[var].dropna(), d1[var].dropna())))
    DL = pd.DataFrame(rows); DL.to_csv(OUT / "detached_0p_vs_1p_effect_sizes.csv", index=False); DL.to_csv(SUMD / "detached_0p_vs_1p_effect_sizes.csv", index=False); SUMMARY["detached_0p_vs_1p_effect_sizes"] = DL.round(3).to_dict("records")
    fr = {}
    for nm, col in (("hol_2 at default", "hol2_default"), ("reco proton present", "reco_p_present"), ("vertex anchored (<=5 cm)", "anchored5")):
        fr[nm] = dict(detached_0p=float(d0[col].mean()), detached_1p=float(d1[col].mean()))
    for st in sorted(X.conn_state.dropna().unique()):
        fr["PF state " + st] = dict(detached_0p=float((d0.conn_state == st).mean()), detached_1p=float((d1.conn_state == st).mean()))
    for pr_ in ("interaction_vertex", "conversion_point", "between", "neither", "not_separable", "no_conversion_point"):
        fr["vertex class " + pr_] = dict(detached_0p=float((d0.prox == pr_).mean()), detached_1p=float((d1.prox == pr_).mean()))
    SUMMARY["detached_0p_vs_1p_fractions"] = fr
    st_rows = []
    for k in (0, 1):
        for dt in (False, True):
            for an in (False, True):
                m = (X.cls == k) & (X.detached == dt) & (X.anchored5 == an); n = int(m.sum()); kk = int(X.survive[m].sum()); f, l, h = cp(kk, n)
                st_rows.append(dict(truth=f"truth {k}p", shower="detached" if dt else "attached", vertex="anchored (<=5 cm)" if an else "not anchored", n=n, survive=kk, survival=f, lo68=l, hi68=h, median_other_score=float(X.other_score[m].median()) if n else np.nan,
                                    median_numu_1=float(X.in_numu_1_score[m].median()) if n else np.nan, hol2_default=float(X.hol2_default[m].mean()) if n else np.nan))
    SS = pd.DataFrame(st_rows); SS.to_csv(OUT / "other_survival_by_state.csv", index=False); SS.to_csv(SUMD / "other_survival_by_state.csv", index=False); SUMMARY["other_survival_by_state"] = SS.round(4).to_dict("records")
    if "origin" in X:
        og = []
        for o in ("decay_proton", "fsi_created"):
            for dt in (False, True):
                m = (X.cls == 1) & (X.origin == o) & (X.detached == dt); n = int(m.sum()); kk = int(X.survive[m].sum()); f, l, h = cp(kk, n); og.append(dict(origin=o, detached=dt, n=n, survival=f, lo68=l, hi68=h, anchored5=float(X.anchored5[m].mean())))
        SUMMARY["other_survival_by_origin_and_attachment"] = og
    fig, ax = PS.figure(1, 2, size=(11, 4.2)); a = ax[0][0]; labs = ["0p att.", "0p det.", "1p att.", "1p det."]; x = np.arange(4)
    for off, an, col in ((-0.2, False, "#999999"), (0.2, True, "#D55E00")):
        v_ = [SS[(SS.truth == f"truth {k}p") & (SS.shower == dt) & (SS.vertex == ("anchored (<=5 cm)" if an else "not anchored"))] for k in (0, 1) for dt in ("attached", "detached")]
        vals = [r.survival.iloc[0] if len(r) else np.nan for r in v_]; a.bar(x + off, vals, 0.4, color=col, label="vertex anchored (<=5 cm)" if an else "vertex not anchored")
    a.set_xticks(x); a.set_xticklabels(labs); a.set_ylabel("`other` conditional survival"); a.set_ylim(0, 1); a.legend(fontsize=7); a.set_title("survival by shower attachment and vertex anchoring", fontsize=8)
    a = ax[0][1]
    if "origin" in pop:
        labs = []; vals = []; cols = []
        for o, dn in (("decay_proton", "Delta+"), ("fsi_created", "Delta+"), ("fsi_created", "Delta0")):
            m = (pop.cls == 1) & (pop.origin == o) & (pop.delta_label == dn); labs.append(f"{dn}\n{o}"); vals.append(float(pop.detached[m].mean())); cols.append("#E69F00" if dn == "Delta+" else "#CC79A7")
        a.bar(range(3), vals, color=cols); a.set_xticks(range(3)); a.set_xticklabels(labs, fontsize=7); a.set_ylim(0, 1); a.set_ylabel("detached-shower fraction (events reaching `other`)"); a.set_title("truth 1p: detachment by proton origin", fontsize=8)
    fig.tight_layout(); save(fig, "detached_states_and_origin.png")


def energy_block(E, raw):
    """Task 15: reco shower energy relative to the true photon energy for the dominant electron-typed photon shower, counted vs not counted."""
    S = E[E.has_kine_row & (E.kine_particle_is_shower == 1) & (E.kine_particle_type == 11) & (E.dominant_fraction >= SA.DOMINANT_FRAC_MIN)].copy()
    S["ratio"] = S.kine_energy_particle / S.photon_energy_mev; S["counted"] = S.outcome == "pass_photon_shower_in_passing_candidate"
    rows = []
    for emin in (0, 100, 200, 400):
        a = E[E.photon_energy_mev > emin]; s = S[S.photon_energy_mev > emin]
        rows.append(dict(E_gamma_above_mev=emin, n_candidate_stage=len(a), n_dominant_electron_shower=len(s), frac_with_electron_shower=len(s) / len(a), n_shower_below_20=int((s.kine_energy_particle <= 20).sum()),
                         frac_below_20_of_candidate_stage=float((s.kine_energy_particle <= 20).sum() / len(a)), frac_below_20_of_electron_showers=float((s.kine_energy_particle <= 20).mean()),
                         ratio_median_counted=float(s[s.counted].ratio.median()), ratio_median_not_counted=float(s[~s.counted].ratio.median()), n_counted=int(s.counted.sum()), n_not_counted=int((~s.counted).sum())))
    ER = pd.DataFrame(rows); ER.to_csv(OUT / "shower_energy_response.csv", index=False); ER.to_csv(SUMD / "shower_energy_response.csv", index=False); SUMMARY["energy_response"] = ER.round(4).to_dict("records")
    q = {nm: S[m].ratio.quantile([.16, .5, .84]).round(3).tolist() for nm, m in (("counted", S.counted), ("not counted", ~S.counted))}; SUMMARY["energy_response_quantiles"] = q
    SUMMARY["energy_response_by_outcome"] = {o: S[S.outcome == o].ratio.quantile([.16, .5, .84]).round(3).tolist() for o in S.outcome.unique()}
    fig, ax = PS.figure(1, 2, size=(11, 4.2)); bins = np.linspace(0, 2.0, 41)
    for nm, m, col in (("counted (pass via the photon shower)", S.counted, "#000000"), ("not counted", ~S.counted, "#D55E00")):
        ax[0][0].hist(S[m].ratio.clip(0, 2), bins=bins, density=True, histtype="step", color=col, lw=1.6, label=f"{nm} (N={int(m.sum())})")
    ax[0][0].set_xlabel("E_reco / E_true of the dominant photon electron shower"); ax[0][0].set_ylabel("normalised"); ax[0][0].legend(fontsize=7)
    ax[0][1].hist2d(S.photon_energy_mev.clip(0, 1000), S.kine_energy_particle.clip(0, 1000), bins=[np.linspace(0, 1000, 41)] * 2, cmap="Blues", cmin=1); ax[0][1].plot([0, 1000], [0, 1000], "k--", lw=0.8)
    ax[0][1].axhline(20, color="r", lw=0.8); ax[0][1].set_xlabel("true photon energy [MeV]"); ax[0][1].set_ylabel("reco shower energy [MeV]")
    fig.tight_layout(); save(fig, "shower_energy_response.png")


def high_energy_block(E, raw):
    """Task 14: deterministic list of the E_gamma > 400 MeV events that have a candidate but fail the > 20 MeV shower stage, with a deterministic sample of PF trees."""
    H = E[(E.photon_energy_mev > 400) & (~E.pass_n20)].sort_values(RSE).copy()
    cols = RSE + ["file_index", "ev", "truth35", "delta_label", "photon_energy_mev", "conv_distance_cm", "photon_end_class", "vtx_x", "vtx_y", "vtx_z", "dom_nu", "n_cand_with_photon", "dominant_fraction", "kine_particle_type",
                  "kine_particle_is_shower", "kine_particle_pool", "kine_energy_particle", "pf_state", "conn_state", "outcome"]
    H[cols].to_csv(OUT / "high_energy_failure_events.csv", index=False)
    SUMMARY["high_energy_failure_events"] = dict(n=len(H), by_outcome={k: int(v) for k, v in H.outcome.value_counts().items()}, by_truth={TRUTH_LABEL[int(k)]: int(v) for k, v in H.truth35.value_counts().items()})
    sample = H.iloc[::16]; pf = raw["pf"].copy(); lines = [f"# deterministic sample (every 16th of {len(H)} events sorted by run/subrun/evt): E_gamma > 400 MeV, candidate exists, fails the > 20 MeV shower stage\n"]
    for r in sample.itertuples():
        lines.append(f"## run {r.run} subrun {r.subrun} evt {r.evt} | {TRUTH_LABEL[int(r.truth35)]} {r.delta_label} | E_gamma {r.photon_energy_mev:.0f} MeV | conv {r.conv_distance_cm} cm | outcome {r.outcome} | dominant object pdg {r.kine_particle_type} shower {r.kine_particle_is_shower} E_reco {r.kine_energy_particle} | PF state {r.pf_state}")
        t = pf[(pf.file_index == r.file_index) & (pf.ev == r.ev) & (pf.nu_index == (r.dom_nu if pd.notna(r.dom_nu) else 0))]
        for n in t.sort_values("depth").itertuples():
            lines.append(f"    node {int(n.node_id)} parent {int(n.parent_id)} depth {int(n.depth)} pdg {int(n.pdg)} KE {n.ke_mev:.0f} pseudo {int(n.is_pseudo)} kine_index {int(n.kine_index)}")
    (OUT / "high_energy_failure_pf_sample.md").write_text("\n".join(lines))
    fig, ax = PS.figure(1, 1, size=(8, 4)); a = ax[0][0]; vc = H.outcome.value_counts().reindex(SA.FAIL_CLASSES).fillna(0); a.barh(range(len(vc)), vc.values / vc.sum(), color=[CLS_COL[o] for o in vc.index], edgecolor="k")
    a.set_yticks(range(len(vc))); a.set_yticklabels([o.replace("photon_", "").replace("_", " ") for o in vc.index], fontsize=7); a.invert_yaxis(); a.set_xlabel(f"fraction of the {len(H)} E_gamma > 400 MeV shower-stage failures")
    for i, v in enumerate(vc.values):
        a.text(v / vc.sum() + 0.005, i, str(int(v)), va="center", fontsize=7)
    fig.tight_layout(); save(fig, "high_energy_failure_composition.png")


def taxonomy_figure(E):
    fig, ax = PS.figure(1, 1, size=(9, 4.4)); a = ax[0][0]; gs = {"all": np.ones(len(E), bool), "truth 0p": (E.truth35 == 0).to_numpy(), "truth 1p": (E.truth35 == 1).to_numpy()}
    bottom = np.zeros(3)
    for o in OUTCOMES:
        v_ = np.array([float(((E.outcome == o).to_numpy() & m).sum() / m.sum()) for m in gs.values()]); a.bar(range(3), v_, bottom=bottom, color=CLS_COL[o], edgecolor="white", label=o.replace("photon_", "").replace("_", " ")); bottom += v_
    a.set_xticks(range(3)); a.set_xticklabels(list(gs)); a.set_ylim(0, 1); a.set_ylabel("fraction of candidate-stage events"); h, l = a.get_legend_handles_labels(); a.legend(h[::-1], l[::-1], fontsize=6, loc="center left", bbox_to_anchor=(1.0, 0.5))
    a.set_title("shower-stage outcome of the signal photon (pass / fail taxonomy)", fontsize=9); fig.tight_layout(); save(fig, "taxonomy_all_0p_1p.png")


def finish(E):
    taxonomy_figure(E)
    meta = dict(git_commit_at_run=subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(), official_manifest_sha256=sha(REPO / "manifests" / "official_gen2_ncdelta_wc.tsv.gz"),
                truth_master_sha256=sha(SPD / "official_gen2_ncdelta_master" / "signal_events.parquet"), t_match_semantics="WIRECELL_TRUTH_MATCH_SEMANTICS.md (2026-11-09), level-1 particle/overlap rows; association via T_overlap trackid of the signal photon",
                baseline_selection_sha256=sha(REPO / "configs" / "baseline_selection.yaml"), phase8_audit_summary_sha256=sha(REPO / "tables" / "other_bdt_audit" / "summary.json"), phase8_population_sha256=sha(P8 / "population_events.parquet"),
                phase8_metadata=json.load(open(P8 / "metadata.json")), raw_scan_sha256={k: sha(RAW / f"{k}.parquet") for k in ("cand", "kine", "pf", "seg", "shlist", "pho_ov", "ov_all", "truth")},
                classification_parameters=dict(outside_frac_min=SA.OUTSIDE_FRAC_MIN, dominant_frac_min=SA.DOMINANT_FRAC_MIN, proximity_tol_cm=SA.PROXIMITY_TOL_CM, sp_energy_mev=SA.SP_ENERGY_MEV))
    (OUT / "metadata.json").write_text(json.dumps(meta, indent=1)); SUMMARY["metadata"] = meta
    (SUMD / "summary.json").write_text(json.dumps(SUMMARY, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    E.to_parquet(OUT / "event_taxonomy.parquet", index=False)


if __name__ == "__main__":
    main()
