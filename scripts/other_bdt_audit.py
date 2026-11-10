#!/usr/bin/env python
"""AUDIT of the FROZEN ``single_photon_other_bdt_final.xml``: why does the ``other`` stage keep more truth-1p than truth-0p signal? (descriptive; NO retraining, NO threshold scan)

    source env/setup_eaf.sh
    python scripts/other_bdt_scan.py official ; python scripts/other_bdt_scan.py natural ; python scripts/other_bdt_proton_origin_scan.py
    python scripts/other_bdt_source_table.py --wct-src <production source dir>
    python scripts/other_bdt_audit.py

Study population: official Gen2 NC-Delta, provisional TPC truth box, policy ``any``, events with at least one candidate that has passed wc.valid, candidate, > 20 MeV shower, BDT evaluable and numu
(i.e. the ``other`` cut is applied). The event-level ``any`` logic is kept: the *controlling candidate* of an event is the reaching candidate with the largest frozen ``other`` score (ties: lowest
nu_index); the event survives iff that score exceeds the FIXED threshold 0.2 (checked event by event against the validated baseline flag). Candidate-level tables are kept alongside.
Outputs outside Git: $SP_DATA/other_bdt_audit/official_ncdelta/ ; compact summaries: tables/other_bdt_audit/ ; figures: plots/other_bdt_audit/.
"""
from __future__ import annotations
import hashlib, json, os, subprocess, sys, warnings
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from scipy import stats
from sbnd_single_photon import bdt as B, differential as DF, exclusive_signal as X, natural_signal as NS, other_audit as OA, plotstyle as PS, selection as SEL
import matplotlib.pyplot as plt

SPD = Path(os.environ["SP_DATA"]); OUT = SPD / "other_bdt_audit" / "official_ncdelta"; PLD = REPO / "plots" / "other_bdt_audit"; SUMD = REPO / "tables" / "other_bdt_audit"
for d in (PLD, SUMD, OUT):
    d.mkdir(parents=True, exist_ok=True)
THRESHOLD = 0.2          # the frozen cut (configs/baseline_selection.yaml); never scanned
KEY = ["file_index", "ev"]; RSE = ["run", "subrun", "evt"]
SUMMARY: dict = {}
PROV = "official Gen2 NC-Delta | frozen other BDT (single_photon_other_bdt_final.xml) | events reaching the other stage, TPC box, policy any | cut fixed at 0.2 | descriptive audit"
CLS = {0: "truth 0p", 1: "truth 1p", 2: "truth >=2p"}; CCOL = {0: "#0072B2", 1: "#D55E00", 2: "#009E73"}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def cp(k, n):
    return X.binom_ci(int(k), int(n))


def save(fig, name):
    PS.annotate(fig, PROV, extra=PS.PRELIM)
    fig.savefig(PLD / name, bbox_inches="tight"); plt.close(fig)


# ---------------------------------------------------------------------------------------------------------------------------- load
def load_population():
    c = pd.read_parquet(OUT / "official_candidates.parquet")
    d = pd.read_parquet(SPD / "analysis_tables" / "official_gen2_ncdelta" / "candidates.parquet",
                        columns=KEY + ["c_nu_index", "c_score_other", "cum_single_photon_numu_score_gt_0p4", "cum_single_photon_other_score_gt_0p2", "bdt_evaluable", "c_np35", "c_lead_proton_ke_mev",
                                       "c_shw_sp_energy", "c_shw_sp_shw_vtx_dis", "c_kine_nu_x_corr", "c_kine_nu_y_corr", "c_kine_nu_z_corr", "c_nrows"])
    c = c.merge(d, on=KEY + ["c_nu_index"], how="left", validate="one_to_one")
    c["reaches_other"] = c.cum_single_photon_numu_score_gt_0p4.fillna(False).astype(bool)
    c["passes_other"] = c.cum_single_photon_other_score_gt_0p2.fillna(False).astype(bool)
    ev = pd.read_parquet(SPD / "spine_harmonization" / "official_ncdelta" / "event_flags_and_table.parquet")
    ex = pd.read_parquet(SPD / "differential_efficiency" / "official_ncdelta" / "event_table_tpc_box_any.parquet", columns=RSE + ["conv_distance_cm", "photon_end_class"])
    ev = ev.merge(ex, on=RSE, how="left")
    return c, ev


def controlling(c):
    r = c[c.reaches_other].sort_values(KEY + ["other_score", "c_nu_index"], ascending=[True, True, False, True])
    ctrl = r.drop_duplicates(KEY, keep="first").copy()
    n = r.groupby(KEY).size().rename("n_reaching").reset_index(); ctrl = ctrl.merge(n, on=KEY)
    ntot = c.groupby(KEY).size().rename("n_candidates_total").reset_index(); ctrl = ctrl.merge(ntot, on=KEY)
    lead = r.sort_values(KEY + ["c_nu_index"]).drop_duplicates(KEY, keep="first")[KEY + ["other_score", "c_nu_index"]].rename(columns={"other_score": "lead_cand_score", "c_nu_index": "lead_cand_nu"})
    return r, ctrl.merge(lead, on=KEY)


def vstats(a, b, name, default=None):
    """Descriptive two-sample comparison of one input (a: reference class, b: comparison class)."""
    a = np.asarray(a, float); b = np.asarray(b, float)
    pooled = math.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2) if len(a) > 1 and len(b) > 1 else np.nan
    ks = stats.ks_2samp(a, b)
    d = dict(variable=name, n_a=len(a), n_b=len(b), median_a=np.median(a), median_b=np.median(b), q16_a=np.quantile(a, .16), q84_a=np.quantile(a, .84), q16_b=np.quantile(b, .16), q84_b=np.quantile(b, .84),
             mean_a=a.mean(), mean_b=b.mean(), smd=(b.mean() - a.mean()) / pooled if pooled and pooled > 0 else 0.0, ks=ks.statistic, ks_p=ks.pvalue,
             wasserstein=stats.wasserstein_distance(a, b), wasserstein_over_pooled_sd=(stats.wasserstein_distance(a, b) / pooled) if pooled and pooled > 0 else 0.0, n_unique=len(np.unique(np.r_[a, b])))
    if default is not None and np.isfinite(default):
        fa = float((np.float32(a) == np.float32(default)).mean()); fb = float((np.float32(b) == np.float32(default)).mean()); d.update(default=default, frac_default_a=fa, frac_default_b=fb, frac_default_diff=fb - fa)
    return d


import math  # noqa: E402


def surv_bins(df, var, edges, mask, col="survive"):
    b = DF.assign_bins(df[var].to_numpy(), edges); rows = []
    for i in range(len(edges) - 1):
        m = mask & (b == i); n = int(m.sum()); k = int((m & df[col].to_numpy(bool)).sum()); f, l, h = cp(k, n) if n else (np.nan,) * 3
        rows.append(dict(bin=i, lo=edges[i], hi=edges[i + 1], n=n, k=k, survival=f, lo68=l, hi68=h))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------------------------------------------------------- main
def main():
    c, ev = load_population(); model = B.TmvaBdt("other", B.DEFAULT_WEIGHT_DIR / "single_photon_other_bdt_final.xml"); names = model.var_names; inc = ["in_" + n for n in names]
    src = pd.read_csv(SUMD / "input_source_table.csv"); dflt = {r.bdt_variable: (float(r.declared_default) if str(r.declared_default).strip() not in ("", "nan") else np.nan) for r in src.itertuples()}
    group = dict(zip(src.bdt_variable, src.group))

    # ---- Task 2: exact score reproduction
    ok = c.c_score_other.notna()
    s32 = OA.scores_tmva_float32(model, c[inc].to_numpy(float)); fin = np.isfinite(c.other_score) & np.isfinite(s32)
    rng = np.random.default_rng(1); sub = rng.choice(np.where(fin)[0], size=300, replace=False)
    sc = np.array([OA.scalar_score_tmva(B.DEFAULT_WEIGHT_DIR / "single_photon_other_bdt_final.xml", c[inc].to_numpy(float)[i]) for i in sub])
    dd = np.abs(s32 - c.other_score)[fin]
    SUMMARY["reproduction"] = dict(n_candidates=len(c), n_compared_to_stored_derived_score=int(ok.sum()), max_abs_diff_vs_stored=float(np.abs(c.other_score[ok] - c.c_score_other[ok]).max()),
                                   n_stored_missing=int((~ok).sum()), n_nonfinite_recomputed=int((~np.isfinite(c.other_score)).sum()), n_independent_tmva_f32=int(fin.sum()),
                                   max_abs_diff_vs_independent_tmva_f32=float(dd.max()), median_abs_diff_vs_independent=float(np.median(dd)), n_diff_gt_1e6=int((dd > 1e-6).sum()),
                                   n_decision_flips_at_0p2=int(((c.other_score > THRESHOLD) != (s32 > THRESHOLD))[fin].sum()),
                                   scalar_xml_subset_n=len(sub), scalar_vs_vectorised_f32_max=float(np.abs(sc - s32[sub]).max()), scalar_vs_frozen_max=float(np.abs(sc - c.other_score.to_numpy()[sub]).max()),
                                   cm_stored_in_caf=False)
    assert SUMMARY["reproduction"]["max_abs_diff_vs_stored"] == 0.0 and SUMMARY["reproduction"]["max_abs_diff_vs_independent_tmva_f32"] < 1e-6 and SUMMARY["reproduction"]["n_decision_flips_at_0p2"] == 0

    # ---- Task 3: study population
    reach, ctrl = controlling(c)
    t = ev[ev.tpc_box & ev.A_numu.astype(bool)].copy()
    E = t.merge(ctrl, on=KEY, how="inner", validate="one_to_one", suffixes=("", "_c")); assert len(E) == len(t), (len(E), len(t))
    E["survive"] = E.other_score > THRESHOLD
    assert (E.survive == E.A_other.astype(bool)).all(), "controlling-candidate decision disagrees with the validated event flag"
    E["cls"] = E.truth35.astype(int); E["is1p"] = E.cls == 1
    pop = []
    for k in (0, 1, 2):
        m = E.cls == k; n = int(m.sum()); kk = int(E.survive[m].sum()); f, l, h = cp(kk, n)
        pop.append(dict(truth=CLS[k], events_reaching_other=n, survive=kk, survival=f, lo68=l, hi68=h, multi_candidate_events=int((E.n_reaching[m] > 1).sum()), reaching_candidates=int(E.n_reaching[m].sum()),
                        events_with_more_than_one_candidate_total=int((E.n_candidates_total[m] > 1).sum())))
    kk0, n0 = int(E.survive[E.cls == 0].sum()), int((E.cls == 0).sum()); kk1, n1 = int(E.survive[E.cls == 1].sum()), int((E.cls == 1).sum())
    SUMMARY["population"] = dict(table=pop, n_events=len(E), n_reaching_candidates=int(len(reach[reach.set_index(KEY).index.isin(E.set_index(KEY).index)])),
                                 survival_diff_1p_minus_0p=kk1 / n1 - kk0 / n0, total_candidates_in_scan=len(c),
                                 multi_candidate_events=int((E.n_reaching > 1).sum()),
                                 multi_candidate_decision_driven_by_non_lead=int((E.survive & (E.lead_cand_score <= THRESHOLD)).sum()), n_events_multi_cand_total=int((E.n_candidates_total > 1).sum()))
    pd.DataFrame(pop).to_csv(OUT / "population.csv", index=False); pd.DataFrame(pop).to_csv(SUMD / "population.csv", index=False)

    # ---- Task 4: score distributions
    E["delta"] = E.delta_label
    groups = {"truth 0p": E.cls == 0, "truth 1p": E.cls == 1, "truth >=2p": E.cls == 2}
    grp_d = {"Delta0 (all)": E.delta == "Delta0", "Delta+ (all)": E.delta == "Delta+", "truth 1p, Delta0": (E.cls == 1) & (E.delta == "Delta0"), "truth 1p, Delta+": (E.cls == 1) & (E.delta == "Delta+"),
             "truth 0p, Delta0": (E.cls == 0) & (E.delta == "Delta0"), "truth 0p, Delta+": (E.cls == 0) & (E.delta == "Delta+")}
    rows = []
    for nm, m in {**groups, **grp_d}.items():
        s = E.other_score[m]; k = int((s > THRESHOLD).sum()); n = len(s); f, l, h = cp(k, n)
        rows.append(dict(group=nm, n=n, survive=k, survival=f, lo68=l, hi68=h, median_score=float(s.median()), q16=float(s.quantile(.16)), q84=float(s.quantile(.84)), mean_score=float(s.mean())))
    S = pd.DataFrame(rows); S.to_csv(OUT / "score_summary.csv", index=False); S.to_csv(SUMD / "score_summary.csv", index=False); SUMMARY["score_summary"] = S.round(4).to_dict("records")
    ksd = {}
    for a, b, nm in (("truth 0p", "truth 1p", "0p_vs_1p"), ("truth 1p, Delta0", "truth 1p, Delta+", "1p_Delta0_vs_Delta+"), ("truth 0p, Delta0", "truth 0p, Delta+", "0p_Delta0_vs_Delta+")):
        ma = {**groups, **grp_d}[a]; mb = {**groups, **grp_d}[b]; r = stats.ks_2samp(E.other_score[ma], E.other_score[mb]); ksd[nm] = dict(ks=float(r.statistic), p=float(r.pvalue))
    SUMMARY["score_ks"] = ksd

    def hist_cdf(sets, name, title):
        fig, ax = PS.figure(1, 3, size=(14, 3.8)); bins = np.linspace(-1, 1, 41)
        for k, (nm, m, col) in enumerate(sets):
            s = E.other_score[m]
            ax[0][0].hist(s, bins=bins, density=True, histtype="step", color=col, lw=1.6, label=f"{nm} (N={len(s)})")
            ss = np.sort(s.to_numpy()); ax[0][1].plot(ss, np.arange(1, len(ss) + 1) / len(ss), color=col, label=nm)
            k_ = int((s > THRESHOLD).sum()); f, l, h = cp(k_, len(s)); ax[0][2].errorbar([k], [f], yerr=[[f - l], [h - f]], fmt="o", color=col)
            ax[0][2].annotate(f"{100 * f:.1f}%", (k, f), textcoords="offset points", xytext=(8, -3), fontsize=8)
        for a in ax[0][:2]:
            a.axvline(THRESHOLD, color="k", ls="--", lw=1)
        ax[0][0].set_xlabel("frozen single_photon_other_score (controlling candidate)"); ax[0][0].set_ylabel("normalised"); ax[0][0].legend(fontsize=7); ax[0][0].set_title(title + "  (dashed: frozen cut 0.2)", fontsize=8)
        ax[0][1].set_xlabel("score"); ax[0][1].set_ylabel("cumulative fraction"); ax[0][1].set_title("cumulative distribution", fontsize=8)
        ax[0][2].set_xticks(range(len(sets))); ax[0][2].set_xticklabels([s[0] for s in sets], rotation=20, fontsize=7); ax[0][2].set_ylabel("survival at the frozen cut (score > 0.2)"); ax[0][2].set_ylim(0, 1)
        fig.tight_layout(); save(fig, name)
    hist_cdf([(k, groups[k], CCOL[i]) for i, k in enumerate(groups)], "other_score_0p_vs_1p.png", "0p vs 1p vs >=2p")
    hist_cdf([("truth 1p, Delta0", grp_d["truth 1p, Delta0"], "#CC79A7"), ("truth 1p, Delta+", grp_d["truth 1p, Delta+"], "#E69F00"), ("truth 0p, Delta0", grp_d["truth 0p, Delta0"], "#56B4E9"), ("truth 0p, Delta+", grp_d["truth 0p, Delta+"], "#009E73")],
             "other_score_delta_in_1p.png", "Delta0 vs Delta+ inside truth classes")

    # ---- Task 5/6/7: every input, 0p vs 1p among events reaching other (controlling candidate)
    a, b = E[E.cls == 0], E[E.cls == 1]
    V = pd.DataFrame([vstats(a[n], b[n], n[3:], dflt.get(n[3:])) for n in inc])
    V["group"] = V.variable.map(group); V["rank_ks"] = V.ks.rank(ascending=False).astype(int)
    split_counts = pd.Series(0, index=range(len(names)))
    for t_ in model.trees:
        for iv in t_.ivar[t_.ivar >= 0]:
            split_counts[iv] += 1
    ntrees_use = pd.Series({i: sum((t_.ivar == i).any() for t_ in model.trees) for i in range(len(names))})
    V["n_splits_in_ensemble"] = V.variable.map(dict(zip(names, split_counts.to_numpy()))); V["n_trees_using"] = V.variable.map(dict(zip(names, ntrees_use.to_numpy())))
    V = V.sort_values("ks", ascending=False); V.to_csv(OUT / "input_stats_0p_vs_1p.csv", index=False); V.to_csv(SUMD / "input_stats_0p_vs_1p.csv", index=False)
    d1 = E[(E.cls == 1) & (E.delta == "Delta0")]; d2 = E[(E.cls == 1) & (E.delta == "Delta+")]
    VD = pd.DataFrame([vstats(d1[n], d2[n], n[3:], dflt.get(n[3:])) for n in inc]); VD["group"] = VD.variable.map(group)
    VD = VD.sort_values("ks", ascending=False); VD.to_csv(OUT / "input_stats_1p_Delta0_vs_Delta+.csv", index=False)
    G = V.groupby("group").agg(n_inputs=("variable", "size"), mean_ks=("ks", "mean"), max_ks=("ks", "max"), n_ks_gt_0p1=("ks", lambda s: int((s > 0.1).sum())), n_ks_gt_0p2=("ks", lambda s: int((s > 0.2).sum())),
                               top=("variable", "first")).reset_index().sort_values("mean_ks", ascending=False)
    G.to_csv(OUT / "input_group_summary.csv", index=False); G.to_csv(SUMD / "input_group_summary.csv", index=False); SUMMARY["group_summary"] = G.round(4).to_dict("records")
    SUMMARY["top_inputs_ks"] = V.head(15)[["variable", "group", "ks", "smd", "median_a", "median_b", "q16_a", "q84_a", "q16_b", "q84_b", "frac_default_a", "frac_default_b", "n_splits_in_ensemble"]].round(4).to_dict("records")
    SUMMARY["constant_inputs"] = V[V.n_unique == 1].variable.tolist()
    top = V.head(8)
    fig, ax = PS.figure(2, 4, size=(15, 6.2))
    for i, r in enumerate(top.itertuples()):
        a_ = ax[i // 4][i % 4]; lo, hi = np.quantile(np.r_[E["in_" + r.variable]], [0.01, 0.99]); lo, hi = (lo, hi) if hi > lo else (lo - 1, hi + 1)
        bins = np.linspace(lo, hi, 31)
        for k, col in ((0, CCOL[0]), (1, CCOL[1])):
            a_.hist(np.clip(E["in_" + r.variable][E.cls == k], lo, hi), bins=bins, density=True, histtype="step", color=col, lw=1.6, label=CLS[k])
        a_.set_xlabel(r.variable, fontsize=7); a_.set_title(f"KS={r.ks:.2f}  SMD={r.smd:+.2f}  [{r.group.split(' (')[0][:34]}]", fontsize=7)
        if i == 0:
            a_.legend(fontsize=7)
    fig.tight_layout(); save(fig, "other_input_top_differences.png")

    # fill / default (availability) study
    FD = []
    for n in names:
        df_ = dflt.get(n)
        if df_ is None or not np.isfinite(df_):
            continue
        row = dict(variable=n, group=group[n], default=df_)
        for nm, m in (("0p", E.cls == 0), ("1p", E.cls == 1), (">=2p", E.cls == 2), ("Delta0", E.delta == "Delta0"), ("Delta+", E.delta == "Delta+"), ("1p_Delta0", (E.cls == 1) & (E.delta == "Delta0")), ("1p_Delta+", (E.cls == 1) & (E.delta == "Delta+"))):
            row["frac_default_" + nm] = float((np.float32(E["in_" + n][m]) == np.float32(df_)).mean())
        row["diff_1p_minus_0p"] = row["frac_default_1p"] - row["frac_default_0p"]; row["diff_1p_D+_minus_D0"] = row["frac_default_1p_Delta+"] - row["frac_default_1p_Delta0"]
        FD.append(row)
    FD = pd.DataFrame(FD).sort_values("diff_1p_minus_0p", key=lambda s: -s.abs()); FD.to_csv(OUT / "fill_default_fractions.csv", index=False); FD.to_csv(SUMD / "fill_default_fractions.csv", index=False)
    SUMMARY["fill_default_top"] = FD.head(12).round(4).to_dict("records")
    SUMMARY["shw_sp_filled_fraction"] = {nm: float((E.shw_sp_filled[m] != 0).mean()) for nm, m in {"0p": E.cls == 0, "1p": E.cls == 1, ">=2p": E.cls == 2}.items()}
    strat = []
    for n in FD.head(4).variable:
        isd = np.float32(E["in_" + n]) == np.float32(dflt[n])
        for sn, sm in (("at default", isd), ("not default", ~isd)):
            for k in (0, 1):
                m = (E.cls == k) & sm; kk = int(E.survive[m].sum()); nn = int(m.sum()); f, l, h = cp(kk, nn) if nn else (np.nan,) * 3
                strat.append(dict(variable=n, stratum=sn, truth=CLS[k], n=nn, survive=kk, survival=f, lo68=l, hi68=h))
    pd.DataFrame(strat).to_csv(OUT / "survival_by_default_stratum.csv", index=False); SUMMARY["survival_by_default_stratum"] = strat
    fig, ax = PS.figure(1, 2, size=(13, 4.2)); top12 = FD.head(12)[::-1]; y = np.arange(len(top12))
    ax[0][0].barh(y - 0.2, top12.frac_default_0p, 0.4, color=CCOL[0], label="truth 0p"); ax[0][0].barh(y + 0.2, top12.frac_default_1p, 0.4, color=CCOL[1], label="truth 1p")
    ax[0][0].set_yticks(y); ax[0][0].set_yticklabels(top12.variable, fontsize=6); ax[0][0].set_xlabel("fraction of events AT the declared default value"); ax[0][0].legend(fontsize=7)
    ax[0][0].set_title("inputs with the largest 0p/1p default-fraction difference", fontsize=8)
    t2 = FD.sort_values("diff_1p_D+_minus_D0", key=lambda s: -s.abs()).head(12)[::-1]; y = np.arange(len(t2))
    ax[0][1].barh(y - 0.2, t2["frac_default_1p_Delta0"], 0.4, color="#CC79A7", label="1p, Delta0"); ax[0][1].barh(y + 0.2, t2["frac_default_1p_Delta+"], 0.4, color="#E69F00", label="1p, Delta+")
    ax[0][1].set_yticks(y); ax[0][1].set_yticklabels(t2.variable, fontsize=6); ax[0][1].set_xlabel("fraction at default"); ax[0][1].legend(fontsize=7); ax[0][1].set_title("inside truth 1p: Delta0 vs Delta+", fontsize=8)
    fig.tight_layout(); save(fig, "other_fill_default_fractions.png")

    # availability = shower-vertex connectivity: br2_* are only filled when the leading shower's stem is directly attached to the main vertex (source: bad_reconstruction_1_sp is called only if sg_at_main)
    E["connected"] = E["in_shw_sp_shw_vtx_dis"] == 0; E["br2_default"] = (E["in_shw_sp_br2_sg_length"] == 0) & (E["in_shw_sp_br2_n_shower_main_segs"] == 0)
    E["reco_np35"] = E.c_np35.clip(upper=2)
    SUMMARY["br2_default_vs_connected_crosstab"] = pd.crosstab(E.br2_default, E.connected).to_dict()

    def strata(df, by, label):
        rows = []
        for key, g in df.groupby(by, observed=True):
            key = key if isinstance(key, tuple) else (key,); n = len(g); kk = int(g.survive.sum()); f, l, h = cp(kk, n)
            rows.append(dict(zip(by, key), n=n, survive=kk, survival=f, lo68=l, hi68=h, frac_br2_default=float(g.br2_default.mean()), frac_connected=float(g.connected.mean()), median_score=float(g.other_score.median())))
        t_ = pd.DataFrame(rows); t_.to_csv(OUT / f"strata_{label}.csv", index=False); return t_
    E01 = E[E.cls <= 1]
    S1 = strata(E01.assign(connected_label=np.where(E01.connected, "attached (gap = 0)", "detached (gap > 0)")), ["cls", "connected_label"], "class_x_connected")
    S2 = strata(E01, ["cls", "reco_np35"], "class_x_reco_np35")
    E1_ = E[E.cls == 1]
    S3 = strata(E1_.assign(connected_label=np.where(E1_.connected, "attached (gap = 0)", "detached (gap > 0)")), ["delta", "connected_label"], "truth1p_delta_x_connected")
    S4 = strata(E1_, ["delta", "reco_np35"], "truth1p_delta_x_reco_np35")
    SUMMARY["strata"] = dict(class_x_connected=S1.round(4).to_dict("records"), class_x_reco_np35=S2.round(4).to_dict("records"), truth1p_delta_x_connected=S3.round(4).to_dict("records"), truth1p_delta_x_reco_np35=S4.round(4).to_dict("records"))
    for t_, nm in ((S1, "class_x_connected"), (S2, "class_x_reco_np35"), (S3, "truth1p_delta_x_connected"), (S4, "truth1p_delta_x_reco_np35")):
        t_.to_csv(SUMD / f"strata_{nm}.csv", index=False)
    # share of the 0p/1p survival difference that sits in each availability stratum (exact accounting: S = sum_s P(s) S(s))
    acc = {}
    for k in (0, 1):
        g = E[E.cls == k]; acc[CLS[k]] = {nm: dict(frac_events=float((g.connected == v).mean()), survival=float(g.survive[g.connected == v].mean())) for nm, v in (("attached", True), ("detached", False))}
    SUMMARY["survival_accounting_by_attachment"] = acc

    # ---- Task 8: score / survival vs observables, split 0p / 1p
    E["reco_vtx_disp"] = np.sqrt((E.c_kine_nu_x_corr - E.vtx_x) ** 2 + (E.c_kine_nu_y_corr - E.vtx_y) ** 2 + (E.c_kine_nu_z_corr - E.vtx_z) ** 2)
    E["reco_lead_p_ke"] = E.c_lead_proton_ke_mev.fillna(0.0)
    obs = [("photon_energy_mev", "True photon energy [MeV]", DF.load_bins()["variables"]["photon_energy_mev"]["edges"]), ("cos_theta_beam", "cos(theta_gamma)", DF.load_bins()["variables"]["cos_theta_beam"]["edges"]),
           ("lead_p_ke", "Leading TRUE proton KE [MeV] (truth >= 1p)", [35, 50, 75, 100, 150, 200, 300, 500, 2000]), ("reco_np35", "Reco proton multiplicity (35 MeV rows)", [0, 1, 2, 3]),
           ("reco_lead_p_ke", "Leading RECO proton-row KE [MeV] (0 = none)", [0, 1e-6, 50, 100, 150, 250, 400, 1500]), ("c_shw_sp_energy", "Reco shower energy [MeV]", [0, 100, 200, 300, 400, 600, 1000, 6000]),
           ("c_shw_sp_shw_vtx_dis", "Reco shower-to-vertex distance [cm]", [-1.0001, 0.0001, 2, 5, 10, 20, 50, 600]), ("conv_distance_cm", "True conversion distance [cm]", [0, 5, 10, 20, 30, 50, 100, 1000]),
           ("reco_vtx_disp", "|reco - true vertex| [cm]", [0, 1, 2, 5, 10, 20, 50, 500])]
    fig, ax = PS.figure(3, 3, size=(14, 11)); SB = []
    CATEG = ("reco_np35", "reco_lead_p_ke", "c_shw_sp_energy", "c_shw_sp_shw_vtx_dis", "conv_distance_cm", "reco_vtx_disp")      # wide / irregular bins: plotted at bin positions with labelled ticks
    for i, (v, lab, edges) in enumerate(obs):
        a_ = ax[i // 3][i % 3]
        for k in (0, 1, 2) if v == "lead_p_ke" else (0, 1):
            if v == "lead_p_ke" and k == 0:
                continue
            m = (E.cls == k).to_numpy(); sb = surv_bins(E, v, edges, m); sb["variable"] = v; sb["truth"] = CLS[k]; SB.append(sb); c_ = sb[sb.n >= 10].copy()
            if v in CATEG:
                c_["lo"], c_["hi"] = c_.bin - 0.4, c_.bin + 0.4
            PS.eff_errorbar(a_, c_.lo, c_.hi, c_.survival, c_.lo68, c_.hi68, label=CLS[k], color=CCOL[k], offset=0.08 * (k - 0.5))
        a_.set_xlabel(lab, fontsize=8); a_.set_ylabel("`other` conditional survival", fontsize=8); a_.set_ylim(0, 1)
        if v in CATEG:
            if v == "reco_np35":
                a_.set_xticks(range(3)); a_.set_xticklabels(["0", "1", ">=2"])
            else:
                a_.set_xticks(range(len(edges) - 1)); a_.set_xticklabels([f"{edges[b]:g}-{edges[b + 1]:g}" for b in range(len(edges) - 1)], rotation=35, ha="right", fontsize=6)
        elif v == "lead_p_ke":
            a_.set_xscale("log")
        if i == 0:
            a_.legend(fontsize=7)
    fig.tight_layout(); save(fig, "other_survival_vs_observables.png")
    SBt = pd.concat(SB, ignore_index=True); SBt.to_csv(OUT / "survival_vs_observables.csv", index=False)
    # dedicated headline figures
    for v, nm, lab in (("lead_p_ke", "other_survival_vs_lead_proton_ke.png", "Leading TRUE proton KE [MeV]"), ("photon_energy_mev", "other_survival_vs_photon_energy.png", "True photon energy [MeV]")):
        fig, ax = PS.figure(1, 2 if v == "lead_p_ke" else 1, size=(10 if v == "lead_p_ke" else 5, 3.8)); edges = dict((o[0], o[2]) for o in obs)[v]
        sets = ([("truth 1p", (E.cls == 1), CCOL[1]), ("truth >=2p", (E.cls == 2), CCOL[2])] if v == "lead_p_ke" else [("truth 0p", E.cls == 0, CCOL[0]), ("truth 1p", E.cls == 1, CCOL[1]), ("truth >=2p", E.cls == 2, CCOL[2])])
        for k, (nm_, m, col) in enumerate(sets):
            sb = surv_bins(E, v, edges, m.to_numpy()); c_ = sb[sb.n >= 10]; PS.eff_errorbar(ax[0][0], c_.lo, c_.hi, c_.survival, c_.lo68, c_.hi68, label=nm_, color=col, offset=0.08 * (k - 0.5))
        ax[0][0].set_xlabel(lab); ax[0][0].set_ylabel("`other` conditional survival (score > 0.2)"); ax[0][0].set_ylim(0, 1); ax[0][0].legend(fontsize=7)
        if v == "lead_p_ke":
            ax[0][0].set_xscale("log"); ax[0][0].set_title("truth-1p / >=2p events", fontsize=8)
            for dn, col in (("Delta0", "#CC79A7"), ("Delta+", "#E69F00")):
                sb = surv_bins(E, v, edges, ((E.cls == 1) & (E.delta == dn)).to_numpy()); c_ = sb[sb.n >= 10]; PS.eff_errorbar(ax[0][1], c_.lo, c_.hi, c_.survival, c_.lo68, c_.hi68, label=f"truth 1p, {dn}", color=col, offset=0.04 if dn == "Delta+" else -0.04)
            ax[0][1].set_xscale("log"); ax[0][1].set_xlabel(lab); ax[0][1].set_ylim(0, 1); ax[0][1].legend(fontsize=7); ax[0][1].set_title("inside truth 1p: Delta0 vs Delta+", fontsize=8)
        fig.tight_layout(); save(fig, nm)
    # does the gap persist at fixed observables? logistic adjustment of the SURVIVAL gap (observed association only)
    Q = E[(E.cls <= 1)].copy(); Q["truth_cat"] = Q.cls; Q["delta_pdg"] = np.where(Q.delta == "Delta0", 2114, 2214); Q["A_final"] = Q.survive
    for col in ("c_shw_sp_energy", "c_shw_sp_shw_vtx_dis", "reco_vtx_disp", "reco_np35", "reco_lead_p_ke"):
        Q[col] = Q[col].fillna(Q[col].median())
    Qf = Q.replace([np.inf, -np.inf], np.nan).dropna(subset=["photon_energy_mev", "cos_theta_beam", "nu_energy_gev", "vtx_x", "vtx_y", "vtx_z", "c_shw_sp_energy", "c_shw_sp_shw_vtx_dis", "reco_vtx_disp"])
    sets_ = {"none": [], "truth kinematics": ["photon_energy_mev", "cos_theta_beam", "nu_energy_gev", "vtx_x", "vtx_y", "vtx_z"], "reco shower + vertex": ["c_shw_sp_energy", "c_shw_sp_shw_vtx_dis", "reco_vtx_disp"],
             "truth kinematics + reco shower/vertex": ["photon_energy_mev", "cos_theta_beam", "nu_energy_gev", "vtx_x", "vtx_y", "vtx_z", "c_shw_sp_energy", "c_shw_sp_shw_vtx_dis", "reco_vtx_disp"]}
    adj = {}
    for k, f in sets_.items():
        adj[k] = ({kk: float(vv) for kk, vv in DF.adjusted_difference(Qf, "truth_0p", "truth_1p", f, n_boot=100).items() if isinstance(vv, (int, float))} if f else
                  dict(raw_difference=float(Qf[Qf.cls == 1].survive.mean() - Qf[Qf.cls == 0].survive.mean())))
    SUMMARY["survival_gap_adjusted"] = adj

    # ---- Task 9: proton-origin study inside truth 1p
    po = OUT / "proton_origin.parquet"
    if po.exists():
        P = pd.read_parquet(po); E1 = E[E.cls == 1].merge(P, on=RSE, how="left", validate="one_to_one"); E1["origin"] = E1.origin.fillna("missing")
        tab = []
        for dn in ("Delta0", "Delta+", "all"):
            for og in sorted(E1.origin.unique()):
                m = (E1.origin == og) & ((E1.delta == dn) if dn != "all" else True); n = int(m.sum())
                if n == 0:
                    continue
                kk = int(E1.survive[m].sum()); f, l, h = cp(kk, n); tab.append(dict(delta=dn, origin=og, n=n, survive=kk, survival=f, lo68=l, hi68=h, median_score=float(E1.other_score[m].median())))
        T9 = pd.DataFrame(tab); T9.to_csv(OUT / "proton_origin_survival.csv", index=False); T9.to_csv(SUMD / "proton_origin_survival.csv", index=False); SUMMARY["proton_origin"] = T9.round(4).to_dict("records")
        SUMMARY["proton_origin_decay_nucleon_vs_delta"] = pd.crosstab(E1.delta, E1.decay_nucleon_pdg).to_dict()
        cmp_ = []
        for dn in ("Delta+",):
            for a_o, b_o in (("decay_proton", "fsi_created"), ("decay_proton", "ambiguous")):
                ma = (E1.origin == a_o) & (E1.delta == dn); mb = (E1.origin == b_o) & (E1.delta == dn)
                if ma.sum() > 20 and mb.sum() > 20:
                    VV = pd.DataFrame([vstats(E1["in_" + n][ma], E1["in_" + n][mb], n) for n in names]).sort_values("ks", ascending=False).head(6)
                    cmp_.append(dict(delta=dn, a=a_o, b=b_o, n_a=int(ma.sum()), n_b=int(mb.sum()), top_inputs=VV[["variable", "ks", "smd"]].round(3).to_dict("records"),
                                     score_ks=float(stats.ks_2samp(E1.other_score[ma], E1.other_score[mb]).statistic)))
        SUMMARY["proton_origin_input_comparison"] = cmp_
        # Delta0 vs Delta+ inside truth 1p, split by whether the proton is FSI-created (Delta0 is always FSI-created by construction)
        E1["fsi"] = E1.origin.isin(["fsi_created", "not_from_decay"])
        E1["connected"] = E1["in_shw_sp_shw_vtx_dis"] == 0
        oc = []
        for dn in ("Delta0", "Delta+"):
            for og in ("decay_proton", "fsi_created", "ambiguous"):
                for cn, cm in (("attached", True), ("detached", False)):
                    m = (E1.delta == dn) & (E1.origin == og) & (E1.connected == cm); n = int(m.sum())
                    if n >= 5:
                        kk = int(E1.survive[m].sum()); f, l, h = cp(kk, n); oc.append(dict(delta=dn, origin=og, shower=cn, n=n, survive=kk, survival=f, lo68=l, hi68=h))
        pd.DataFrame(oc).to_csv(OUT / "proton_origin_x_connected.csv", index=False); pd.DataFrame(oc).to_csv(SUMD / "proton_origin_x_connected.csv", index=False); SUMMARY["proton_origin_x_connected"] = oc
        og_frac = E1.groupby(["delta", "origin"]).connected.mean().round(4); SUMMARY["proton_origin_frac_attached"] = {f"{a}/{b}": float(v) for (a, b), v in og_frac.items()}
        SUMMARY["proton_origin_1p_by_fsi"] = {f"{dn}/{'fsi' if f else 'non-fsi'}": [int(((E1.delta == dn) & (E1.fsi == f)).sum()), float(E1.survive[(E1.delta == dn) & (E1.fsi == f)].mean()) if ((E1.delta == dn) & (E1.fsi == f)).any() else None] for dn in ("Delta0", "Delta+") for f in (True, False)}
    else:
        SUMMARY["proton_origin"] = "unavailable: proton_origin.parquet not produced"

    # ---- Task 10: exact model-internal interpretation
    Xall = E[inc].to_numpy(float); fin_ = np.isfinite(Xall).all(axis=1)
    contrib = OA.tree_contributions(model, Xall[fin_]); marg = contrib.sum(axis=1)
    assert np.allclose(np.tanh(marg), E.other_score.to_numpy()[fin_], atol=1e-6)
    Ef = E[fin_].reset_index(drop=True); contrib = pd.DataFrame(contrib)
    m0, m1 = (Ef.cls == 0).to_numpy(), (Ef.cls == 1).to_numpy()
    td = contrib[m1].mean() - contrib[m0].mean(); order = td.abs().sort_values(ascending=False).index[:15]
    trees = []
    for ti in order:
        tr = model.trees[ti]; vars_ = sorted({names[i] for i in tr.ivar[tr.ivar >= 0]}); trees.append(dict(tree=int(ti), boost=float(model.boost[ti]), mean_contrib_0p=float(contrib[m0][ti].mean()), mean_contrib_1p=float(contrib[m1][ti].mean()),
                                                                                        difference=float(td[ti]), root_variable=names[int(tr.ivar[0])], variables=vars_))
    SUMMARY["tree_decomposition"] = dict(mean_margin_0p=float(marg[m0].mean()), mean_margin_1p=float(marg[m1].mean()), mean_margin_difference=float(marg[m1].mean() - marg[m0].mean()),
                                         sum_tree_differences=float(td.sum()), threshold_margin=float(np.arctanh(THRESHOLD)), top_trees=trees,
                                         fraction_of_difference_in_top15_trees=float(td[order].sum() / td.sum()), n_trees_positive=int((td > 0).sum()), n_trees_negative=int((td < 0).sum()))
    pd.DataFrame(trees).to_csv(OUT / "tree_decomposition_top15.csv", index=False)
    rs = np.random.default_rng(5)

    def shap_run(fg_mask, bg_mask, tag, nfg=600, nbg=300):
        fi = rs.choice(np.where(fg_mask)[0], size=min(nfg, int(fg_mask.sum())), replace=False); bi = rs.choice(np.where(bg_mask)[0], size=min(nbg, int(bg_mask.sum())), replace=False)
        r = OA.interventional_shap(model, Ef[inc].to_numpy(float)[fi], Ef[inc].to_numpy(float)[bi]); m_f = contrib.to_numpy()[fi].sum(axis=1)
        resid = float(np.abs(r["base"] + r["phi"].sum(axis=1) - m_f).max())
        phi = pd.DataFrame(r["phi"], columns=names); mean_phi = phi.mean(); grp = mean_phi.groupby(mean_phi.index.map(group)).sum()
        out = dict(tag=tag, n_foreground=len(fi), n_background=len(bi), base_margin=r["base"], mean_foreground_margin=float(m_f.mean()), mean_margin_difference=float(m_f.mean() - r["base"]), max_additivity_residual=resid,
                   groups={k: float(v) for k, v in grp.sort_values(key=lambda s: -s.abs()).items()}, top_variables=[dict(variable=k, mean_phi=float(v), mean_abs_phi=float(phi[k].abs().mean()), group=group[k], n_splits=int(split_counts[names.index(k)]))
                                                                                                                       for k, v in mean_phi.sort_values(key=lambda s: -s.abs()).head(15).items()])
        return out, phi
    s1, phi1 = shap_run(m1, m0, "foreground truth 1p vs background truth 0p (margin space)")
    mD1 = ((Ef.cls == 1) & (Ef.delta == "Delta+")).to_numpy(); mD0 = ((Ef.cls == 1) & (Ef.delta == "Delta0")).to_numpy()
    s2, phi2 = shap_run(mD1, mD0, "foreground truth-1p Delta+ vs background truth-1p Delta0 (margin space)")
    SUMMARY["shap"] = [s1, s2]; assert s1["max_additivity_residual"] < 1e-8 and s2["max_additivity_residual"] < 1e-8
    pd.DataFrame(s1["top_variables"]).to_csv(OUT / "shap_1p_vs_0p_top.csv", index=False); pd.DataFrame(s2["top_variables"]).to_csv(OUT / "shap_1p_Deltaplus_vs_Delta0_top.csv", index=False)
    pd.DataFrame(s1["top_variables"]).to_csv(SUMD / "shap_1p_vs_0p_top.csv", index=False); pd.DataFrame(s2["top_variables"]).to_csv(SUMD / "shap_1p_Deltaplus_vs_Delta0_top.csv", index=False)
    fig, ax = PS.figure(2, 2, size=(14, 8))
    for j, s in enumerate((s1, s2)):
        g = pd.Series(s["groups"]); ax[0][j].barh(range(len(g))[::-1], g.values, color=["#D55E00" if v > 0 else "#0072B2" for v in g.values]); ax[0][j].set_yticks(range(len(g))[::-1]); ax[0][j].set_yticklabels([x[:44] for x in g.index], fontsize=7)
        ax[0][j].axvline(0, color="k", lw=0.8); ax[0][j].set_xlabel("mean signed contribution to the margin difference (SHAP, summed per input family)", fontsize=7)
        ax[0][j].set_title(("1p vs 0p background" if j == 0 else "1p Delta+ vs 1p Delta0 background") + f"  (total {s['mean_margin_difference']:+.3f})", fontsize=8)
        tv = pd.DataFrame(s["top_variables"]).head(12)[::-1]; ax[1][j].barh(range(len(tv)), tv.mean_phi, color=["#D55E00" if v > 0 else "#0072B2" for v in tv.mean_phi]); ax[1][j].set_yticks(range(len(tv))); ax[1][j].set_yticklabels(tv.variable, fontsize=6)
        ax[1][j].axvline(0, color="k", lw=0.8); ax[1][j].set_xlabel("mean signed SHAP value per input (margin units)", fontsize=7)
    fig.tight_layout(); save(fig, "other_model_attribution.png")

    lv = V.set_index("variable")[["group", "ks", "smd", "n_splits_in_ensemble", "n_trees_using"]].rename(columns={"ks": "L1_ks_0p_vs_1p", "smd": "L1_smd", "n_splits_in_ensemble": "L2_n_splits", "n_trees_using": "L2_n_trees"})
    lv["L3_shap_mean_1p_vs_0p"] = pd.Series({r["variable"]: r["mean_phi"] for r in s1["top_variables"]}); full1 = phi1.mean(); lv["L3_shap_mean_1p_vs_0p"] = full1
    lv["L3_shap_mean_Dplus_vs_D0_within_1p"] = phi2.mean(); lv["L3_mean_abs_shap_1p_vs_0p"] = phi1.abs().mean()
    lv = lv.sort_values("L3_shap_mean_1p_vs_0p", key=lambda x: -x.abs()); lv.to_csv(OUT / "variable_levels_1_2_3.csv"); lv.head(25).round(4).to_csv(SUMD / "variable_levels_1_2_3_top25.csv"); SUMMARY["levels_top"] = lv.head(12).round(4).reset_index().to_dict("records")

    # ---- Task 12: SPINE-harmonized denominator
    H = []
    for nm, m in (("loose TPC box, truth 0p (35 MeV)", E.cls == 0), ("loose TPC box, truth 1p (35 MeV)", E.cls == 1), ("loose TPC box, truth >=2p (35 MeV)", E.cls == 2),
                  ("harmonized, truth 0p (35 MeV)", E.spine_truth_signal & (E.cls == 0)), ("harmonized, truth 1p (35 MeV)", E.spine_truth_signal & (E.cls == 1)), ("harmonized, truth >=2p (35 MeV)", E.spine_truth_signal & (E.cls == 2)),
                  ("harmonized 0p50", E.spine_truth_0p50), ("harmonized Np50", E.spine_truth_Np50), ("loose TPC box, 0p50 definition", E.n_p50 == 0), ("loose TPC box, Np50 definition", E.n_p50 >= 1)):
        n = int(m.sum()); kk = int(E.survive[m].sum()); f, l, h = cp(kk, n); H.append(dict(denominator=nm, events_reaching_other=n, survive=kk, survival=f, lo68=l, hi68=h))
    H = pd.DataFrame(H); H.to_csv(OUT / "other_survival_harmonized.csv", index=False); H.to_csv(SUMD / "other_survival_harmonized.csv", index=False); SUMMARY["harmonized"] = H.round(4).to_dict("records")
    hv = E[E.spine_truth_signal]
    SUMMARY["harmonized_ks_score_0p50_vs_Np50"] = float(stats.ks_2samp(hv.other_score[hv.n_p50 == 0], hv.other_score[hv.n_p50 >= 1]).statistic)
    fig, ax = PS.figure(1, 2, size=(11, 3.8)); x_ = np.arange(len(H))
    ax[0][0].errorbar(x_, H.survival, yerr=[H.survival - H.lo68, H.hi68 - H.survival], fmt="o", color="k"); ax[0][0].set_xticks(x_); ax[0][0].set_xticklabels(H.denominator, rotation=40, ha="right", fontsize=6); ax[0][0].set_ylim(0, 1); ax[0][0].set_ylabel("`other` conditional survival")
    for nm, m, col in (("loose 0p", E.cls == 0, CCOL[0]), ("loose 1p", E.cls == 1, CCOL[1]), ("harmonized 0p50", E.spine_truth_0p50, "#009E73"), ("harmonized Np50", E.spine_truth_Np50, "#56B4E9")):
        s_ = np.sort(E.other_score[m].to_numpy()); ax[0][1].plot(s_, np.arange(1, len(s_) + 1) / len(s_), color=col, label=nm)
    ax[0][1].axvline(THRESHOLD, color="k", ls="--", lw=1); ax[0][1].legend(fontsize=7); ax[0][1].set_xlabel("frozen other score"); ax[0][1].set_ylabel("cumulative fraction")
    fig.tight_layout(); save(fig, "other_loose_vs_harmonized.png")

    # ---- Task 13: natural CV (low statistics)
    nat = natural_cv(model, names, inc)
    SUMMARY["natural_cv"] = nat

    E.drop(columns=inc).to_parquet(OUT / "population_events.parquet", index=False)
    meta = dict(git_commit_at_run=subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(), official_manifest_sha256=sha(REPO / "manifests" / "official_gen2_ncdelta_wc.tsv.gz"),
                other_bdt_weights_sha256=sha(B.DEFAULT_WEIGHT_DIR / "single_photon_other_bdt_final.xml"), baseline_selection_sha256=sha(REPO / "configs" / "baseline_selection.yaml"),
                truth_master_sha256=sha(SPD / "official_gen2_ncdelta_master" / "signal_events.parquet"), phase7_event_flags_sha256=sha(SPD / "spine_harmonization" / "official_ncdelta" / "event_flags_and_table.parquet"),
                phase7_spine_truth_sha256=sha(SPD / "spine_harmonization" / "official_ncdelta" / "spine_truth.parquet"), candidate_scan_sha256=sha(OUT / "official_candidates.parquet"), threshold=THRESHOLD,
                weights_path=str(B.DEFAULT_WEIGHT_DIR / "single_photon_other_bdt_final.xml"), wct_commit="4b6853d4 (HaiwangYu/wire-cell-toolkit sbnd-wc-flatcaf)")
    (OUT / "metadata.json").write_text(json.dumps(meta, indent=1)); SUMMARY["metadata"] = meta
    (SUMD / "summary.json").write_text(json.dumps(SUMMARY, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    print("done", {k: SUMMARY["population"]["table"][i]["survival"] for i, k in enumerate(("0p", "1p", ">=2p"))}, "events", SUMMARY["population"]["n_events"])


def natural_cv(model, names, inc):
    T = SPD / "analysis_tables" / "bnb_cv"; events = pd.read_parquet(T / "events.parquet"); cands = pd.read_parquet(T / "candidates.parquet")
    sn = pd.read_parquet(SPD / "natural_ncdelta_bnb_cv" / "signal_neutrinos.parquet"); sig_all = NS.to_signal_truth_table(sn); sig = sig_all[sig_all.in_region].reset_index(drop=True)
    cfg = SEL.load_config(); t = X.signal_event_table(sig, events, cands, cfg, policy="any")
    c = pd.read_parquet(OUT / "natural_candidates.parquet")
    d = cands[KEY + ["c_nu_index", "cum_single_photon_numu_score_gt_0p4"]]
    c = c.merge(d, on=KEY + ["c_nu_index"], how="left"); c["reaches"] = c.cum_single_photon_numu_score_gt_0p4.fillna(False).astype(bool)
    r = c[c.reaches].sort_values(KEY + ["other_score"], ascending=[True, True, False]).drop_duplicates(KEY)
    E = t.merge(r[KEY + ["other_score"]], on=KEY, how="inner")
    E["survive"] = E.other_score > THRESHOLD; assert (E.survive == E.A_other).all()
    rows = []
    for k in (0, 1, 2):
        m = E.truth_cat == k; n = int(m.sum()); kk = int(E.survive[m].sum()); f, l, h = cp(kk, n) if n else (np.nan,) * 3
        rows.append(dict(truth=CLS[k], events_reaching_other=n, survive=kk, survival=f, lo68=l, hi68=h, median_score=float(E.other_score[m].median()) if n else None))
    a, b = E[E.truth_cat == 0], E[E.truth_cat == 1]
    out = dict(table=rows, n_signal_events=len(t), n_reaching_other=len(E))
    if len(a) > 3 and len(b) > 3:
        out["fisher_p_survival_0p_vs_1p"] = float(stats.fisher_exact([[a.survive.sum(), len(a) - a.survive.sum()], [b.survive.sum(), len(b) - b.survive.sum()]])[1])
        out["ks_score_0p_vs_1p"] = float(stats.ks_2samp(a.other_score, b.other_score).statistic); out["ks_p"] = float(stats.ks_2samp(a.other_score, b.other_score).pvalue)
    out["note"] = "low statistics: consistency check only"
    pd.DataFrame(rows).to_csv(SUMD / "natural_cv_other.csv", index=False)
    return out


if __name__ == "__main__":
    main()
