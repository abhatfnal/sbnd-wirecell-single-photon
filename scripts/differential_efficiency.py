#!/usr/bin/env python
"""Differential characterisation of the FROZEN baseline efficiency on the official Gen2 NC-Delta signal (CHARACTERISATION ONLY; no optimisation).

    source env/setup_eaf.sh
    python scripts/differential_truth_scan.py scan --workers 24 && python scripts/differential_truth_scan.py merge   # extra truth variables (once)
    python scripts/differential_natural_cv_truth.py                                                           # natural-CV photon direction (once)
    python scripts/differential_efficiency.py                                                                  # tables (outside Git) + plots + summary

Reuses the derived tables of the official baseline (no ROOT rescan of the merged CAFs). Region: the provisional TPC box; policy ``any`` (``first`` reported as one extra curve).
Tables -> $SP_DATA/differential_efficiency/official_ncdelta/tables/; plots -> plots/differential_efficiency/; small summary -> tables/differential_efficiency/summary.json.
"""
from __future__ import annotations
import hashlib, json, os, subprocess, sys, warnings
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from scipy import stats
from sbnd_single_photon import differential as DF, exclusive_signal as X, natural_signal as NS, plotstyle as PS, selection as SEL, signal_pipeline as SP
import matplotlib.pyplot as plt

SPD = Path(os.environ["SP_DATA"]); OUT = SPD / "differential_efficiency" / "official_ncdelta"; TABD = OUT / "tables"; PLD = REPO / "plots" / "differential_efficiency"
SUMD = REPO / "tables" / "differential_efficiency"
for d in (TABD, PLD, SUMD):
    d.mkdir(parents=True, exist_ok=True)
GROUPS4 = ["all", "truth_0p", "truth_1p", "truth_ge2p"]; GROUPS_D = ["Delta0", "Delta+"]
RECO_STAGES = ["candidate", "n20mev", "bdt_evaluable"]; SEL_STAGES = ["numu", "other", "ncpi0", "final"]
ALL_STAGES = RECO_STAGES + SEL_STAGES
STAGE_LABEL = {"candidate": r"$\geq$1 candidate", "n20mev": r"$>$20 MeV shower", "bdt_evaluable": "BDT evaluable", "numu": "numu", "other": "other", "ncpi0": "ncpi0",
               "nue": "nue", "n20br1": "n_20br1", "final": "final (any)", "final_first": "final (first)"}
PROV = "bins with <10 events not drawn | official Gen2 EX_ncdeltarad fg1-compatible WC | TPC-box truth denominator (N=12,427) | policy any | proton KE>35 MeV (provisional) | no FV"
VARS = {  # name -> groups
    "photon_energy_mev": GROUPS4 + GROUPS_D, "cos_theta_beam": GROUPS4 + GROUPS_D, "nu_energy_gev": GROUPS4 + GROUPS_D, "vtx_x": GROUPS4 + GROUPS_D, "vtx_y": GROUPS4 + GROUPS_D,
    "vtx_z": GROUPS4 + GROUPS_D, "conv_distance_cm": GROUPS4 + GROUPS_D, "lead_proton_ke_mev": ["all", "truth_1p", "truth_ge2p"], "max_sub35_proton_ke_mev": ["truth_0p"]}
SUMMARY: dict = {}
MIN_DRAW = 10      # bins with fewer events in the denominator (or reaching the stage) are not DRAWN (they stay in every table)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def git_commit():
    return subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()


# ---------------------------------------------------------------------------------------------------------------- load / build
def load():
    cfg = SEL.load_config(); T = SPD / "analysis_tables" / "official_gen2_ncdelta"; B = SPD / "official_signal_baseline"
    ev = pd.read_parquet(T / "events.parquet"); ca = pd.read_parquet(T / "candidates.parquet")
    arr = pd.read_parquet(B / "signal_joined_active_tpc.parquet"); mis = pd.read_parquet(B / "signal_missing_active_tpc.parquet")
    te = pd.read_parquet(OUT / "truth_extra.parquet")
    tab = DF.build_event_table(arr, mis, ev, ca, cfg, te, "any"); tf = DF.build_event_table(arr, mis, ev, ca, cfg, None, "first")
    tab = tab.merge(tf[DF.RSE + ["A_final"]].rename(columns={"A_final": "A_final_first"}), on=DF.RSE, how="left", validate="one_to_one")
    assert len(tab) == 12427 and int(tab.A_final.sum()) == 1153 and int(tab.A_final_first.sum()) == 1101 and int((~tab.arrived).sum()) == 1
    assert not tab.photon_energy_mev.isna().any() and tab.cos_theta_beam.notna().all()
    assert (tab.scan_n_p35 == tab.n_p35).all() and (abs(tab.photon_e_mev - tab.photon_energy_mev) < 1e-3).all()      # extra scan agrees with the master
    return cfg, tab, ev, ca


def write(df, name):
    df.to_csv(TABD / name, index=False)


def save(fig, name):
    PS.annotate(fig, PROV, extra=PS.PRELIM)
    fig.savefig(PLD / name, bbox_inches="tight"); plt.close(fig)


# ---------------------------------------------------------------------------------------------------------------- plotting
def _curve(eff, var, g, s, key="efficiency"):
    d = eff[(eff.variable == var) & (eff.group == g) & (eff.stage == s) & (eff.kind == "bin")].sort_values("bin")
    if key == "efficiency":
        n = d.denominator.values; ok = n >= MIN_DRAW
        f = lambda c: np.where(ok, d[c].values, np.nan)
        return d.lo.values, d.hi.values, f("efficiency"), f("lo68"), f("hi68"), n
    n = d.n_reach.values; ok = n >= MIN_DRAW
    f = lambda c: np.where(ok, d[c].values, np.nan)
    return d.lo.values, d.hi.values, f("survival"), f("surv_lo68"), f("surv_hi68"), n


def _fmt(ax, label, ylabel, log=False):
    ax.set_xlabel(label); ax.set_ylabel(ylabel); ax.set_ylim(bottom=0)
    if log:
        ax.set_xscale("log")


def plot_stage_grid(eff, var, label, rows, groups, name, key="efficiency"):
    nr, nc = len(rows), len(groups)
    fig, ax = PS.figure(nr, nc, size=(3.9 * nc, 3.1 * nr))
    for i, (title, stages) in enumerate(rows):
        for j, g in enumerate(groups):
            a = ax[i][j]
            for k, s in enumerate(stages):
                lo, hi, e, l, h, n = _curve(eff, var, g, s, key)
                PS.eff_errorbar(a, lo, hi, e, l, h, label=STAGE_LABEL[s], color=PS.STAGE_COLOR.get(s, "k"), offset=0.12 * (k - (len(stages) - 1) / 2) / max(1, len(stages) - 1))
            a.set_title(f"{PS.GROUP_LABEL[g]}  [{title}]", fontsize=9); _fmt(a, label, "cumulative efficiency" if key == "efficiency" else "conditional survival")
            if i == 0 and j == 0:
                a.legend(loc="best")
    fig.tight_layout(); save(fig, name)


def plot_group_compare(eff, var, label, stages, groups, name, key="efficiency", ncols=3):
    nr = int(np.ceil(len(stages) / ncols)); fig, ax = PS.figure(nr, ncols, size=(3.9 * ncols, 3.1 * nr))
    for i, s in enumerate(stages):
        a = ax[i // ncols][i % ncols]
        for k, g in enumerate(groups):
            lo, hi, e, l, h, n = _curve(eff, var, g, s, key)
            PS.eff_errorbar(a, lo, hi, e, l, h, label=PS.GROUP_LABEL[g], color=PS.GROUP_COLOR[g], offset=0.1 * (k - (len(groups) - 1) / 2))
        a.set_title(STAGE_LABEL[s] + (" (cumulative)" if key == "efficiency" else " (conditional survival)"), fontsize=9); _fmt(a, label, "efficiency" if key == "efficiency" else "survival")
        if i == 0:
            a.legend(loc="best")
    for j in range(len(stages), nr * ncols):
        ax[j // ncols][j % ncols].axis("off")
    fig.tight_layout(); save(fig, name)


def plot_firstfail(ff, var, label, groups, name):
    fig, ax = PS.figure(1, len(groups), size=(4.2 * len(groups), 3.4))
    for j, g in enumerate(groups):
        d = ff[(ff.variable == var) & (ff.group == g) & (ff.kind == "bin")]
        edges = sorted(set(d.lo) | set(d.hi)); fr = {}
        for r in DF.FIRST_FAIL[::-1]:
            dd = d[d.reason == r].sort_values("bin"); fr[r] = np.where(dd.denominator.values >= MIN_DRAW, dd.fraction.values, 0.0)
        PS.stacked_fraction(ax[0][j], edges, fr, PS.FF_COLOR, DF.FIRST_FAIL_LABEL)
        ax[0][j].set_title(f"{PS.GROUP_LABEL[g]}: fraction of denominator", fontsize=9); ax[0][j].set_xlabel(label); ax[0][j].set_ylabel("first-failure fraction")
    h, l = ax[0][0].get_legend_handles_labels(); fig.legend(h[::-1], l[::-1], loc="center left", bbox_to_anchor=(1.0, 0.5), fontsize=7)
    fig.tight_layout(); save(fig, name)


# ---------------------------------------------------------------------------------------------------------------- analyses
def main():
    cfg, tab, ev, ca = load()
    bins = DF.load_bins(); V = bins["variables"]
    stages_cols = [(s, dict(DF.STAGES)[s]) for s in ALL_STAGES + ["n20br1"]] + [("final_first", "A_final_first")]
    tab.to_parquet(OUT / "event_table_tpc_box_any.parquet", index=False)

    # ---- Task 3: accounting of stages / first-failure exclusivity
    ff_counts = tab.first_fail.value_counts().reindex(DF.FIRST_FAIL).fillna(0).astype(int)
    assert int(ff_counts.sum()) == len(tab)
    SUMMARY["denominator"] = dict(tpc_box=len(tab), by_class=tab.truth_class.value_counts().to_dict(), by_delta=tab.delta_label.value_counts().to_dict(),
                                  missing=int((~tab.arrived).sum()), final_any=int(tab.A_final.sum()), final_first=int(tab.A_final_first.sum()), first_fail=ff_counts.to_dict())
    write(pd.DataFrame(dict(reason=ff_counts.index, count=ff_counts.values)), "first_failure_integrated.csv")

    # ---- Tasks 4-8, 10, 11: binned efficiencies, survival, first-failure
    effs, ffs = [], []
    for var, groups in VARS.items():
        edges = V[var]["edges"]
        e = DF.efficiency_in_bins(tab, var, edges, groups, stages_cols); DF.check_closure(e); effs.append(e)
        f = DF.first_failure_in_bins(tab, var, edges, groups); ffs.append(f)
    eff = pd.concat(effs, ignore_index=True); ffall = pd.concat(ffs, ignore_index=True)
    eff["schema_version"] = DF.SCHEMA_VERSION; ffall["schema_version"] = DF.SCHEMA_VERSION
    write(eff, "efficiency_differential.csv"); write(ffall, "first_failure_differential.csv")
    # monotonicity of cumulative efficiency across stages in every (variable, group, bin)
    cum_order = ["candidate", "n20mev", "bdt_evaluable", "numu", "other", "ncpi0", "n20br1"]
    piv = eff[eff.stage.isin(cum_order)].pivot_table(index=["variable", "group", "kind", "bin"], columns="stage", values="numerator")[cum_order]
    assert (piv.diff(axis=1).iloc[:, 1:] <= 0).all().all(), "cumulative numerators not monotone"
    for var in VARS:
        lab = V[var]["label"]
        if var in ("max_sub35_proton_ke_mev",):
            continue
        gs = VARS[var]
        g4 = [g for g in GROUPS4 if g in gs]
        plot_stage_grid(eff, var, lab, [("reconstruction stages", RECO_STAGES), ("selection stages", SEL_STAGES)], g4, f"eff_stages_vs_{var}.png")
        plot_group_compare(eff, var, lab, ["candidate", "n20mev", "numu", "other", "ncpi0", "final"], g4, f"eff_groups_vs_{var}.png")
        if "Delta0" in gs:
            plot_group_compare(eff, var, lab, ["candidate", "n20mev", "numu", "other", "ncpi0", "final"], GROUPS_D + ["all"], f"eff_delta_vs_{var}.png")
        plot_group_compare(eff, var, lab, ["candidate", "n20mev", "bdt_evaluable", "numu", "other", "ncpi0", "n20br1"], [g for g in ["truth_0p", "truth_1p", "truth_ge2p"] if g in gs],
                           f"survival_vs_{var}.png", key="survival", ncols=4)
        plot_firstfail(ffall, var, lab, [g for g in ["all", "truth_0p", "truth_1p", "truth_ge2p"] if g in gs], f"firstfail_vs_{var}.png")
    # the "first" policy as an extra curve on the final-efficiency plot for the headline variable
    SUMMARY["bins_used"] = {k: V[k]["edges"] for k in VARS}

    # ---- integrated tables by class / Delta / stage (cumulative, survival)
    rows = []
    for g in GROUPS4 + GROUPS_D:
        m = DF.group_masks(tab, [g])[g]
        for s, c in stages_cols:
            k = int((m & tab[c].to_numpy(bool)).sum()); n = int(m.sum()); f, l, h = X.binom_ci(k, n)
            rows.append(dict(group=g, stage=s, numerator=k, denominator=n, efficiency=f, lo68=l, hi68=h))
    integ = pd.DataFrame(rows); write(integ, "efficiency_integrated.csv")
    SUMMARY["integrated"] = {f"{r.group}/{r.stage}": [int(r.numerator), int(r.denominator), round(r.efficiency, 5)] for r in integ.itertuples() if r.stage in ("candidate", "final", "final_first")}

    # ---- Task 2/6: conversion distance
    cls = tab.photon_end_class.value_counts().to_dict(); proc = tab.photon_end_process.map(lambda c: DF.G4_PROCESS.get(int(c), f"code{int(c)}")).value_counts().to_dict()
    SUMMARY["conversion"] = dict(end_class=cls, end_process=proc, n_conv=int(tab.conv_distance_cm.notna().sum()),
                                 d_quantiles=tab.conv_distance_cm.quantile([0.1, 0.25, 0.5, 0.75, 0.9]).round(2).to_dict(),
                                 photon_n_gt20_distribution=tab.photon_n_gt20.value_counts().sort_index().to_dict(),
                                 record_vs_primary_photon_energy_maxabsdiff_mev=float(np.nanmax(np.abs(tab.photon_record_e_mev - tab.photon_energy_mev))),
                                 cos_beam_vs_cos_nu_maxabsdiff=float(np.nanmax(np.abs(tab.cos_theta_beam - tab.cos_theta_nu))),
                                 nu_dir_z_min=float(tab.nu_dir_z.min()))
    rows = []
    for c in ["conv", "other_interaction", "left_volume", "no_photon"]:
        for g in GROUPS4:
            m = DF.group_masks(tab, [g])[g] & (tab.photon_end_class == c).to_numpy()
            for s in ["candidate", "n20mev", "bdt_evaluable", "numu", "other", "ncpi0", "final"]:
                col = dict(DF.STAGES)[s]; k = int((m & tab[col].to_numpy(bool)).sum()); n = int(m.sum()); f, l, h = X.binom_ci(k, n)
                rows.append(dict(photon_end_class=c, group=g, stage=s, numerator=k, denominator=n, efficiency=f, lo68=l, hi68=h))
    cls_tab = pd.DataFrame(rows); write(cls_tab, "efficiency_by_photon_end_class.csv")
    fig, ax = PS.figure(1, 2, size=(9, 3.4))
    for k, g in enumerate(GROUPS4):
        d = cls_tab[(cls_tab.group == g) & (cls_tab.stage == "final") & cls_tab.denominator.gt(0)]
        ax[0][0].errorbar(np.arange(len(d)) + 0.08 * (k - 1.5), d.efficiency, yerr=[d.efficiency - d.lo68, d.hi68 - d.efficiency], fmt="o", color=PS.GROUP_COLOR[g], label=PS.GROUP_LABEL[g])
        d = cls_tab[(cls_tab.group == g) & (cls_tab.stage == "candidate") & cls_tab.denominator.gt(0)]
        ax[0][1].errorbar(np.arange(len(d)) + 0.08 * (k - 1.5), d.efficiency, yerr=[d.efficiency - d.lo68, d.hi68 - d.efficiency], fmt="o", color=PS.GROUP_COLOR[g])
    for a, t in zip(ax[0], ("final", r"$\geq$1 candidate")):
        a.set_xticks(range(4)); a.set_xticklabels(["conv", "other\ninteraction", "left\nvolume", "no\nphoton"]); a.set_title(f"{t} efficiency by Geant4 fate of the signal photon", fontsize=9); a.set_ylim(bottom=0)
    ax[0][0].legend(); fig.tight_layout(); save(fig, "eff_by_photon_end_class.png")

    # reco shower-to-vertex distance (reco diagnostic, NOT truth conversion distance)
    mt = tab[tab.A_matched & (tab.match_shw_sp_filled.fillna(False)) & (tab.match_shw_sp_shw_vtx_dis >= 0)]
    fn = tab[tab.A_final & tab.sel_shw_sp_filled.fillna(False) & (tab.sel_shw_sp_shw_vtx_dis >= 0)]
    gap_edges = [0, 1, 2, 5, 10, 20, 50, 100, 500]
    fig, ax = PS.figure(1, 2, size=(9, 3.4))
    for lab, d, col in (("signal-matched candidate (candidate stage)", mt.match_shw_sp_shw_vtx_dis, "#0072B2"), ("analysis-selected candidate (final)", fn.sel_shw_sp_shw_vtx_dis, "#000000")):
        ax[0][0].hist(np.clip(d, 0, 499), bins=gap_edges, histtype="step", density=True, color=col, label=lab)
    ax[0][0].set_xscale("symlog", linthresh=1); ax[0][0].set_xlabel("reco shower-to-vertex distance shw_sp_shw_vtx_dis [cm]"); ax[0][0].set_ylabel("density"); ax[0][0].legend(fontsize=7)
    cv = mt[mt.conv_distance_cm.notna()]
    ax[0][1].scatter(cv.conv_distance_cm, cv.match_shw_sp_shw_vtx_dis, s=3, alpha=0.25, color="#0072B2"); ax[0][1].plot([0, 300], [0, 300], "k--", lw=0.8)
    ax[0][1].set_xscale("symlog", linthresh=1); ax[0][1].set_yscale("symlog", linthresh=1); ax[0][1].set_xlabel("TRUE conversion distance [cm]"); ax[0][1].set_ylabel("reco shower-to-vertex distance [cm]")
    ax[0][1].set_title("matched candidates (converted photons only)", fontsize=9)
    fig.tight_layout(); save(fig, "reco_gap_and_true_conversion.png")
    gap_rows = []
    for s_name, d in (("candidate_matched", mt.match_shw_sp_shw_vtx_dis), ("final_selected", fn.sel_shw_sp_shw_vtx_dis)):
        gap_rows.append(dict(sample=s_name, n=len(d), q16=d.quantile(.16), median=d.median(), q84=d.quantile(.84), frac_gt5cm=float((d > 5).mean()), frac_gt20cm=float((d > 20).mean())))
    gap = pd.DataFrame(gap_rows); write(gap, "reco_shower_gap.csv")
    cvv = cv.assign(cbin=pd.cut(cv.conv_distance_cm, V["conv_distance_cm"]["edges"], right=False))
    gtab = cvv.groupby("cbin", observed=True).match_shw_sp_shw_vtx_dis.agg(["count", "median", lambda s: s.quantile(.16), lambda s: s.quantile(.84)]); gtab.columns = ["n", "median", "q16", "q84"]
    gtab.reset_index().astype({"cbin": str}).to_csv(TABD / "reco_gap_vs_true_conv.csv", index=False)
    SUMMARY["reco_gap"] = gap.round(3).to_dict("records"); SUMMARY["reco_gap_vs_true_conv_corr_spearman"] = float(stats.spearmanr(cv.conv_distance_cm, cv.match_shw_sp_shw_vtx_dis)[0])

    # ---- Task 7: detector sides
    side = np.where(tab.vtx_x < 0, "negative-x side", "positive-x side"); tab["side"] = side
    rows = []
    for sd in ("negative-x side", "positive-x side"):
        for g in GROUPS4:
            m = DF.group_masks(tab, [g])[g] & (tab.side == sd).to_numpy()
            for s, c in stages_cols:
                k = int((m & tab[c].to_numpy(bool)).sum()); n = int(m.sum()); f, l, h = X.binom_ci(k, n)
                rows.append(dict(side=sd, group=g, stage=s, numerator=k, denominator=n, efficiency=f, lo68=l, hi68=h))
    side_t = pd.DataFrame(rows); write(side_t, "detector_sides.csv")
    sf = side_t[(side_t.stage == "final") & (side_t.group == "all")].set_index("side")
    a, b = sf.loc["negative-x side"], sf.loc["positive-x side"]
    p_side = float(stats.fisher_exact([[a.numerator, a.denominator - a.numerator], [b.numerator, b.denominator - b.numerator]])[1])
    SUMMARY["sides"] = dict(negative_x=[int(a.numerator), int(a.denominator)], positive_x=[int(b.numerator), int(b.denominator)], fisher_p=p_side,
                            convention="x<0 'negative-x side' / x>=0 'positive-x side' of the detector coordinate system; NOT mapped to TPC0/TPC1 (mapping not source-established here)")

    # ---- diagnostics for interpreting the angle / energy trends (descriptive; the 'interior' box is NOT a proposed FV)
    tab["Ebin3"] = pd.cut(tab.photon_energy_mev, [0, 200, 300, 1200]).astype(str); tab["cbin3"] = pd.cut(tab.cos_theta_beam, [-1, 0, 0.5, 1.0001]).astype(str)
    two = []
    for (eb, cb), g in tab.groupby(["Ebin3", "cbin3"]):
        for st, col in (("candidate", "A_candidate"), ("n20mev", "A_n20mev"), ("final", "A_final")):
            k = int(g[col].sum()); n = len(g); f, l, h = X.binom_ci(k, n); two.append(dict(photon_energy_bin=eb, cos_bin=cb, stage=st, numerator=k, denominator=n, efficiency=f, lo68=l, hi68=h))
    write(pd.DataFrame(two), "efficiency_photon_energy_x_cos.csv")
    inter = ((tab.vtx_x.abs() < 150) & (tab.vtx_y.abs() < 150) & (tab.vtx_z > 50) & (tab.vtx_z < 450)).to_numpy()
    ie = []
    for name, m in (("interior_diagnostic_box", inter), ("edge_complement", ~inter)):
        for g in GROUPS4:
            mm = m & DF.group_masks(tab, [g])[g]
            for st, col in (("candidate", "A_candidate"), ("n20mev", "A_n20mev"), ("bdt_evaluable", "A_bdt_evaluable"), ("final", "A_final")):
                k = int((mm & tab[col].to_numpy(bool)).sum()); n = int(mm.sum()); f, l, h = X.binom_ci(k, n); ie.append(dict(region=name, group=g, stage=st, numerator=k, denominator=n, efficiency=f, lo68=l, hi68=h))
    ie = pd.DataFrame(ie); write(ie, "efficiency_interior_vs_edge.csv")
    SUMMARY["interior_edge"] = {f"{r.region}/{r.group}/{r.stage}": [int(r.numerator), int(r.denominator), round(r.efficiency, 4)] for r in ie.itertuples()}
    SUMMARY["energy_cos_spearman"] = float(stats.spearmanr(tab.photon_energy_mev, tab.cos_theta_beam)[0])
    SUMMARY["energy_cos_final_2d"] = {f"{r.photon_energy_bin}|{r.cos_bin}": [r.numerator, r.denominator, round(r.efficiency, 4)] for r in pd.DataFrame(two).query("stage=='final'").itertuples()}

    # ---- Task 9: proton KE and 0p/1p migration
    prot = proton_migration(tab, V)

    # ---- Task 12: 0p vs 1p
    explain_0p_1p(tab, V)

    # ---- Task 13: Delta0 vs Delta+
    delta_study(tab)

    # ---- Task 14: resolution
    resolution(tab, V)

    # ---- Task 15: natural CV
    natural_crosscheck(cfg, tab, V)

    meta = dict(schema_version=DF.SCHEMA_VERSION, plot_style_version=PS.STYLE_VERSION, git_commit_at_run=git_commit(), proton_threshold_mev=35.0, candidate_policy="any (first as extra)",
                region="active_tpc (provisional TPC box |x|,|y|<200, 0<z<500 cm; no FV)", official_manifest_sha256=sha(REPO / "manifests" / "official_gen2_ncdelta_wc.tsv.gz"),
                truth_master_sha256=sha(SPD / "official_gen2_ncdelta_master" / "signal_events.parquet"), truth_extra_sha256=sha(OUT / "truth_extra.parquet"),
                signal_regions_sha256=sha(REPO / "configs" / "signal_regions.yaml"), baseline_selection_sha256=sha(REPO / "configs" / "baseline_selection.yaml"),
                bins_sha256=sha(DF.BINS_YAML), n_events=len(tab))
    (OUT / "metadata.json").write_text(json.dumps(meta, indent=1)); SUMMARY["metadata"] = meta
    (SUMD / "summary.json").write_text(json.dumps(SUMMARY, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    print("done; figures:", len(list(PLD.glob("*.png"))))


def proton_migration(tab, V):
    edges = V["lead_proton_ke_mev"]["edges"]; nb = len(edges) - 1
    out = {}
    one = tab[tab.truth_cat == 1].copy(); one["bin"] = DF.assign_bins(one.lead_proton_ke_mev.to_numpy(), edges)
    cats = ["reco_0p", "reco_1p", "reco_ge2p", "no_selected_or_matched"]
    rows = []
    for stage in ("matched_candidate", "final_selected"):
        for bi in range(-1, nb + 1):
            m = one[one.bin == bi]
            if len(m) == 0:
                continue
            if stage == "matched_candidate":
                rc = m.match_reco_cat.to_numpy()          # -1 = no signal-matched candidate
            else:
                rc = np.where(m.A_final, m.sel_reco_cat, -1)
            for k, name in enumerate(cats):
                kk = int((rc == (k if k < 3 else -1)).sum()); f, l, h = X.binom_ci(kk, len(m))
                rows.append(dict(stage=stage, bin=bi, lo=edges[bi] if 0 <= bi < nb else np.nan, hi=edges[bi + 1] if 0 <= bi < nb else np.nan, outcome=name, count=kk, denominator=len(m), fraction=f, lo68=l, hi68=h))
    mig1 = pd.DataFrame(rows); write(mig1, "migration_truth1p_vs_lead_proton_ke.csv")
    fig, ax = PS.figure(1, 2, size=(10, 3.6))
    colors = {"reco_0p": "#0072B2", "reco_1p": "#D55E00", "reco_ge2p": "#009E73", "no_selected_or_matched": "#999999"}
    for j, stage in enumerate(("matched_candidate", "final_selected")):
        for k, c in enumerate(cats):
            d = mig1[(mig1.stage == stage) & (mig1.outcome == c) & (mig1.bin >= 0) & (mig1.bin < nb)].sort_values("bin")
            PS.eff_errorbar(ax[0][j], d.lo, d.hi, d.fraction, d.lo68, d.hi68, label=c.replace("_", " ").replace("ge2p", ">=2p") if j == 0 else None, color=colors[c], offset=0.1 * (k - 1.5))
        ax[0][j].set_xscale("log"); ax[0][j].set_xlabel("leading TRUE proton KE [MeV]"); ax[0][j].set_ylabel("fraction of truth-1p events")
        ax[0][j].set_title({"matched_candidate": "signal-matched candidate stage", "final_selected": "final selected stage (analysis candidate)"}[stage], fontsize=9)
        ax[0][j].axvline(35, color="k", ls=":", lw=0.8); ax[0][j].set_ylim(0, 1)
    ax[0][0].legend(fontsize=7); fig.tight_layout(); save(fig, "migration_truth1p_vs_lead_proton_ke.png")
    # truth-0p: reco proton creation vs highest sub-35 true proton KE
    zero = tab[tab.truth_cat == 0].copy(); e2 = V["max_sub35_proton_ke_mev"]["edges"]
    zero["bin"] = np.where(zero.n_p_all == 0, -3, DF.assign_bins(zero.max_sub35_proton_ke_mev.to_numpy(), e2))
    rows = []
    for stage in ("matched_candidate", "final_selected"):
        for bi in [-3] + list(range(0, len(e2) - 1)):
            m = zero[zero.bin == bi]
            if len(m) == 0:
                continue
            rc = m.match_reco_cat.to_numpy() if stage == "matched_candidate" else np.where(m.A_final, m.sel_reco_cat, -1)
            for k, name in enumerate(cats):
                kk = int((rc == (k if k < 3 else -1)).sum()); f, l, h = X.binom_ci(kk, len(m))
                rows.append(dict(stage=stage, bin=bi, lo=e2[bi] if bi >= 0 else np.nan, hi=e2[bi + 1] if bi >= 0 else np.nan, outcome=name, count=kk, denominator=len(m), fraction=f, lo68=l, hi68=h))
    mig0 = pd.DataFrame(rows); write(mig0, "migration_truth0p_vs_max_sub35_proton_ke.csv")
    fig, ax = PS.figure(1, 2, size=(10, 3.6))
    for j, stage in enumerate(("matched_candidate", "final_selected")):
        for k, c in enumerate(cats):
            d = mig0[(mig0.stage == stage) & (mig0.outcome == c) & (mig0.bin >= 0)].sort_values("bin")
            PS.eff_errorbar(ax[0][j], d.lo, d.hi, d.fraction, d.lo68, d.hi68, label=c.replace("_", " ").replace("ge2p", ">=2p") if j == 0 else None, color=colors[c], offset=0.1 * (k - 1.5))
            nop = mig0[(mig0.stage == stage) & (mig0.outcome == c) & (mig0.bin == -3)]
            if len(nop):
                ax[0][j].axhline(float(nop.fraction.iloc[0]), color=colors[c], ls=":", lw=0.8)
        ax[0][j].set_xlabel("highest TRUE proton KE below 35 MeV [MeV]  (dotted: truth-0p with NO true proton)"); ax[0][j].set_ylabel("fraction of truth-0p events"); ax[0][j].set_ylim(0, 1)
        ax[0][j].set_title(stage.replace("_", " "), fontsize=9)
    ax[0][0].legend(fontsize=7); fig.tight_layout(); save(fig, "migration_truth0p_vs_sub35_proton_ke.png")
    # final efficiency vs leading proton KE already in eff_groups_vs_lead_proton_ke_mev; also the three-class migration headline numbers
    def frac(df, stage, c):
        d = df[(df.stage == stage) & (df.outcome == c) & (df.kind if False else True)]
        return d
    SUMMARY["proton_migration"] = dict(
        truth1p_matched_candidate={r.outcome + f"@bin{int(r.bin)}": round(r.fraction, 3) for r in mig1[mig1.stage == "matched_candidate"].itertuples()},
        truth1p_final={r.outcome + f"@bin{int(r.bin)}": round(r.fraction, 3) for r in mig1[mig1.stage == "final_selected"].itertuples()},
        truth0p_matched={r.outcome + f"@bin{int(r.bin)}": round(r.fraction, 3) for r in mig0[mig0.stage == "matched_candidate"].itertuples()},
        truth0p_final={r.outcome + f"@bin{int(r.bin)}": round(r.fraction, 3) for r in mig0[mig0.stage == "final_selected"].itertuples()})
    return mig1, mig0


def explain_0p_1p(tab, V):
    res = {}
    dec = DF.stage_decomposition(tab, "truth_0p", "truth_1p"); write(dec, "decomposition_0p_vs_1p.csv")
    res["stage_decomposition"] = dict(total_ln_ratio=dec.attrs["total_ln_ratio"], rows=dec.round(4).to_dict("records"))
    fig, ax = PS.figure(1, 2, size=(10, 3.4))
    d = dec[dec.stage != "represented"]
    ax[0][0].errorbar(range(len(d)), d.ln_ratio_surv, yerr=[d.ln_ratio_surv - d.ln_lo68, d.ln_hi68 - d.ln_ratio_surv], fmt="o", color="k"); ax[0][0].axhline(0, color="k", lw=0.8)
    ax[0][0].set_xticks(range(len(d))); ax[0][0].set_xticklabels(d.stage, rotation=45, ha="right"); ax[0][0].set_ylabel("ln[ survival(1p) / survival(0p) ]"); ax[0][0].set_title("per-stage contribution to ln(eps_1p/eps_0p)", fontsize=9)
    ax[0][1].plot(range(len(d)), d.cum_a, "o-", color=PS.GROUP_COLOR["truth_0p"], label="truth 0p"); ax[0][1].plot(range(len(d)), d.cum_b, "o-", color=PS.GROUP_COLOR["truth_1p"], label="truth 1p")
    ax[0][1].set_xticks(range(len(d))); ax[0][1].set_xticklabels(d.stage, rotation=45, ha="right"); ax[0][1].set_ylabel("cumulative efficiency"); ax[0][1].set_yscale("log"); ax[0][1].legend()
    fig.tight_layout(); save(fig, "decomposition_0p_vs_1p.png")
    sd = [DF.standardised_difference(tab, v, V[v]["edges"], "truth_0p", "truth_1p") for v in ("photon_energy_mev", "cos_theta_beam", "nu_energy_gev", "vtx_x", "vtx_y", "vtx_z")]
    write(pd.DataFrame(sd), "standardisation_0p_vs_1p.csv"); res["standardisation"] = sd
    feats = {"none": [], "photon_energy": ["photon_energy_mev"], "photon_energy+cos": ["photon_energy_mev", "cos_theta_beam"],
             "photon+cos+nuE": ["photon_energy_mev", "cos_theta_beam", "nu_energy_gev"], "photon+cos+nuE+vertex": ["photon_energy_mev", "cos_theta_beam", "nu_energy_gev", "vtx_x", "vtx_y", "vtx_z"]}
    adj = {}
    for k, f in feats.items():
        if f:
            adj[k] = DF.adjusted_difference(tab, "truth_0p", "truth_1p", f)
        else:
            m0 = tab[tab.truth_cat == 0].A_final.mean(); m1 = tab[tab.truth_cat == 1].A_final.mean(); adj[k] = dict(raw_difference=float(m1 - m0), adjusted_difference=float(m1 - m0))
    write(pd.DataFrame([dict(model=k, **{kk: vv for kk, vv in v.items() if kk != "features"}) for k, v in adj.items()]), "adjusted_0p_vs_1p.csv"); res["adjusted"] = adj
    # distributions of the truth variables in the two classes (KS)
    ks = {}
    for v in ("photon_energy_mev", "cos_theta_beam", "nu_energy_gev", "vtx_x", "vtx_y", "vtx_z", "conv_distance_cm"):
        a = tab[(tab.truth_cat == 0)][v].dropna(); b = tab[(tab.truth_cat == 1)][v].dropna(); r = stats.ks_2samp(a, b)
        ks[v] = dict(mean_0p=float(a.mean()), mean_1p=float(b.mean()), median_0p=float(a.median()), median_1p=float(b.median()), ks=float(r.statistic), p=float(r.pvalue))
    res["distribution_ks"] = ks; write(pd.DataFrame(ks).T.reset_index(), "distributions_0p_vs_1p.csv")
    # conversion class composition
    comp = pd.crosstab(tab.truth_class, tab.photon_end_class, normalize="index").round(4); res["photon_end_class_by_truth"] = comp.to_dict("index")
    # reco-side correlation: reco shower energy vs truth class at the matched candidate; fraction BDT-evaluable etc. already in decomposition
    SUMMARY["zero_vs_one_proton"] = res
    fig, ax = PS.figure(1, 3, size=(12, 3.4))
    for a, v, lab in zip(ax[0], ("photon_energy_mev", "cos_theta_beam", "vtx_z"), ("true photon energy [MeV]", "cos(theta_gamma, beam)", "true z [cm]")):
        for g in ("truth_0p", "truth_1p", "truth_ge2p"):
            m = DF.group_masks(tab, [g])[g]; a.hist(tab[v][m], bins=V[v]["edges"], density=True, histtype="step", color=PS.GROUP_COLOR[g], label=PS.GROUP_LABEL[g])
        a.set_xlabel(lab); a.set_ylabel("normalised")
    ax[0][0].legend(); fig.tight_layout(); save(fig, "truth_distributions_by_class.png")


def delta_study(tab):
    res = {}
    rows = []
    for d in ("Delta0", "Delta+"):
        for c in ("all", "truth_0p", "truth_1p", "truth_ge2p"):
            m = (DF.group_masks(tab, [d])[d]) & (DF.group_masks(tab, [c])[c])
            for s, col in (("candidate", "A_candidate"), ("final", "A_final"), ("final_first", "A_final_first")):
                k = int((m & tab[col].to_numpy(bool)).sum()); n = int(m.sum()); f, l, h = X.binom_ci(k, n)
                rows.append(dict(delta=d, truth_class=c, stage=s, numerator=k, denominator=n, efficiency=f, lo68=l, hi68=h))
    t = pd.DataFrame(rows); write(t, "delta_by_truth_class.csv"); res["by_class"] = t.round(4).to_dict("records")
    comp = pd.crosstab(tab.delta_label, tab.truth_class); res["class_composition"] = comp.to_dict("index")
    res["decomposition"] = DF.stage_decomposition(tab, "Delta0", "Delta+").round(4).to_dict("records"); write(DF.stage_decomposition(tab, "Delta0", "Delta+"), "decomposition_delta0_vs_deltaplus.csv")
    adj = {}
    for k, f in {"none": [], "photon_energy": ["photon_energy_mev"], "photon+cos+nuE+vertex": ["photon_energy_mev", "cos_theta_beam", "nu_energy_gev", "vtx_x", "vtx_y", "vtx_z"],
                 "photon+cos+nuE+vertex+n_p35": ["photon_energy_mev", "cos_theta_beam", "nu_energy_gev", "vtx_x", "vtx_y", "vtx_z", "n_p35"]}.items():
        if f:
            adj[k] = DF.adjusted_difference(tab, "Delta0", "Delta+", f)
        else:
            m0 = tab[tab.delta_pdg == 2114].A_final.mean(); m1 = tab[tab.delta_pdg == 2214].A_final.mean(); adj[k] = dict(raw_difference=float(m1 - m0), adjusted_difference=float(m1 - m0))
    for c, kk in ((0, "within_truth_0p"), (1, "within_truth_1p")):
        sub = tab[tab.truth_cat == c]
        adj[kk] = DF.adjusted_difference(sub, "Delta0", "Delta+", ["photon_energy_mev", "cos_theta_beam", "nu_energy_gev", "vtx_x", "vtx_y", "vtx_z"])
    res["adjusted"] = adj; write(pd.DataFrame([dict(model=k, **{kk: vv for kk, vv in v.items() if kk != "features"}) for k, v in adj.items()]), "adjusted_delta0_vs_deltaplus.csv")
    ks = {v: dict(mean_d0=float(tab[tab.delta_pdg == 2114][v].mean()), mean_dp=float(tab[tab.delta_pdg == 2214][v].mean()), ks_p=float(stats.ks_2samp(tab[tab.delta_pdg == 2114][v].dropna(), tab[tab.delta_pdg == 2214][v].dropna()).pvalue))
          for v in ("photon_energy_mev", "cos_theta_beam", "nu_energy_gev", "vtx_z")}
    res["distribution_ks"] = ks
    SUMMARY["delta_study"] = res


def resolution(tab, V):
    res = {}
    mt = tab[tab.A_matched & tab.match_shw_sp_filled.fillna(False) & (tab.match_shw_sp_energy > 0)].copy()
    mt["ratio"] = mt.match_shw_sp_energy / mt.photon_energy_mev
    fin = mt[mt.A_final & mt.match_passes_final]
    ee = V["photon_energy_mev"]["edges"]
    rows = []
    for samp, d in (("candidate_matched", mt), ("final_selected_and_matched", fin)):
        d = d.assign(b=DF.assign_bins(d.photon_energy_mev.to_numpy(), ee))
        for bi in range(len(ee) - 1):
            x = d[d.b == bi].ratio
            if len(x) >= 5:
                rows.append(dict(sample=samp, lo=ee[bi], hi=ee[bi + 1], n=len(x), median=x.median(), q16=x.quantile(.16), q84=x.quantile(.84), half_width68_over_median=(x.quantile(.84) - x.quantile(.16)) / 2 / x.median()))
        rows.append(dict(sample=samp, lo=0, hi=1200, n=len(d), median=d.ratio.median(), q16=d.ratio.quantile(.16), q84=d.ratio.quantile(.84), half_width68_over_median=(d.ratio.quantile(.84) - d.ratio.quantile(.16)) / 2 / d.ratio.median()))
    er = pd.DataFrame(rows); write(er, "resolution_shower_energy.csv"); res["shower_energy_ratio"] = er[(er.lo == 0) & (er.hi == 1200)].round(3).to_dict("records")
    fig, ax = PS.figure(1, 3, size=(13, 3.6))
    ax[0][0].hist2d(mt.photon_energy_mev, mt.match_shw_sp_energy, bins=[np.linspace(0, 800, 41)] * 2, cmap="Blues", cmin=1); ax[0][0].plot([0, 800], [0, 800], "k--", lw=0.8)
    ax[0][0].set_xlabel("true photon energy [MeV]"); ax[0][0].set_ylabel("reco shw_sp_energy [MeV] (matched candidates)")
    for samp, col in (("candidate_matched", "#0072B2"), ("final_selected_and_matched", "#000000")):
        d = er[(er["sample"] == samp) & ~((er.lo == 0) & (er.hi == 1200))]
        c = 0.5 * (d.lo + d.hi); ax[0][1].errorbar(c, d["median"], yerr=[d["median"] - d.q16, d.q84 - d["median"]], fmt="o-", color=col, label=samp.replace("_", " "))
    ax[0][1].axhline(1, color="k", ls="--", lw=0.8); ax[0][1].set_xlabel("true photon energy [MeV]"); ax[0][1].set_ylabel("E_reco / E_true (median, 68% band)"); ax[0][1].legend(fontsize=7)
    d = mt.assign(b=DF.assign_bins(mt.photon_energy_mev.to_numpy(), ee))
    # vertex resolution
    for tag, dd in (("candidate_matched", mt), ("final_selected_and_matched", fin)):
        dx, dy, dz = (dd.match_kine_nu_x_corr - dd.vtx_x), (dd.match_kine_nu_y_corr - dd.vtx_y), (dd.match_kine_nu_z_corr - dd.vtx_z)
        r3 = np.sqrt(dx ** 2 + dy ** 2 + dz ** 2)
        res.setdefault("vertex", {})[tag] = dict(n=len(dd), **{f"{n}_median": float(v.median()) for n, v in (("dx", dx), ("dy", dy), ("dz", dz))},
                                                 **{f"{n}_q16": float(v.quantile(.16)) for n, v in (("dx", dx), ("dy", dy), ("dz", dz))}, **{f"{n}_q84": float(v.quantile(.84)) for n, v in (("dx", dx), ("dy", dy), ("dz", dz))},
                                                 r3d_median=float(r3.median()), r3d_q68=float(r3.quantile(.68)), r3d_q90=float(r3.quantile(.90)), frac_gt5cm=float((r3 > 5).mean()), frac_gt20cm=float((r3 > 20).mean()))
        if tag == "candidate_matched":
            ax[0][2].hist(np.clip(r3, 0, 50), bins=np.linspace(0, 50, 51), histtype="step", color="#0072B2", label="matched cand.")
        else:
            ax[0][2].hist(np.clip(r3, 0, 50), bins=np.linspace(0, 50, 51), histtype="step", color="#000000", label="final")
    ax[0][2].set_xlabel("|reco vertex - true vertex| [cm] (clipped at 50)"); ax[0][2].set_ylabel("events"); ax[0][2].set_yscale("log"); ax[0][2].legend(fontsize=7)
    fig.tight_layout(); save(fig, "resolution_energy_vertex.png")
    # component distributions
    fig, ax = PS.figure(1, 3, size=(12, 3.4))
    for a, (c, lab) in zip(ax[0], (("x", "dx"), ("y", "dy"), ("z", "dz"))):
        for dd, col, nm in ((mt, "#0072B2", "matched cand."), (fin, "#000000", "final")):
            v = dd[f"match_kine_nu_{c}_corr"] - dd[f"vtx_{c}"]
            a.hist(np.clip(v, -30, 30), bins=np.linspace(-30, 30, 61), histtype="step", color=col, label=nm)
        a.set_xlabel(f"reco - true {c} [cm] (clipped at +-30)"); a.set_yscale("log")
    ax[0][0].legend(fontsize=7); fig.tight_layout(); save(fig, "resolution_vertex_components.png")
    # does the reco vertex sit at the TRUE conversion point? projection of (reco - true vertex) on the true photon direction vs the true conversion distance
    for tag, dd in (("candidate_matched", mt), ("final_selected_and_matched", fin)):
        dd = dd[dd.conv_distance_cm.notna()]
        off = np.column_stack([dd.match_kine_nu_x_corr - dd.vtx_x, dd.match_kine_nu_y_corr - dd.vtx_y, dd.match_kine_nu_z_corr - dd.vtx_z])
        u = dd[["photon_px", "photon_py", "photon_pz"]].to_numpy(float); u = u / np.linalg.norm(u, axis=1)[:, None]
        proj = (off * u).sum(axis=1); perp = np.linalg.norm(off - proj[:, None] * u, axis=1)
        res.setdefault("vertex_vs_conversion_point", {})[tag] = dict(n=len(dd), spearman_proj_vs_dconv=float(stats.spearmanr(proj, dd.conv_distance_cm)[0]),
            median_proj=float(np.median(proj)), median_dconv=float(dd.conv_distance_cm.median()), median_proj_minus_dconv=float(np.median(proj - dd.conv_distance_cm)),
            median_perp=float(np.median(perp)), q68_abs_proj_minus_dconv=float(np.quantile(np.abs(proj - dd.conv_distance_cm), .68)))
    # proton: event-level association is NOT available (no row-level proton truth match in the derived table)
    both = tab[tab.A_matched & (tab.match_lead_proton_ke_mev.notna()) & tab.lead_proton_ke_mev.notna()]
    res["proton_ke_event_level_only"] = dict(n=len(both), corr_spearman=float(stats.spearmanr(both.match_lead_proton_ke_mev, both.lead_proton_ke_mev)[0]) if len(both) > 3 else None,
                                              median_ratio=float((both.match_lead_proton_ke_mev / both.lead_proton_ke_mev).median()) if len(both) else None,
                                              note="NOT row-associated: the derived table has the leading RECO proton row and the leading TRUE proton but no truth link between individual rows; indicative only")
    fig, a = PS.figure(1, 1, size=(4.4, 3.8)); a = a[0][0]
    a.hist2d(both.lead_proton_ke_mev, both.match_lead_proton_ke_mev, bins=[np.linspace(0, 600, 31)] * 2, cmap="Blues", cmin=1); a.plot([0, 600], [0, 600], "k--", lw=0.8)
    a.set_xlabel("leading TRUE proton KE [MeV]"); a.set_ylabel("leading RECO proton-row KE [MeV]"); a.set_title("event level, NOT row-associated (indicative)", fontsize=8); save(fig, "proton_ke_reco_vs_true_indicative.png")
    SUMMARY["resolution"] = res


def natural_crosscheck(cfg, tab, V):
    T = SPD / "analysis_tables" / "bnb_cv"; events = pd.read_parquet(T / "events.parquet"); cands = pd.read_parquet(T / "candidates.parquet")
    sn = pd.read_parquet(SPD / "natural_ncdelta_bnb_cv" / "signal_neutrinos.parquet"); sig_all = NS.to_signal_truth_table(sn); sig = sig_all[sig_all.in_region].reset_index(drop=True)
    ex = pd.read_parquet(SPD / "differential_efficiency" / "natural_cv_truth_extra.parquet")[["file_index", "ev", "photon_px", "photon_py", "photon_pz", "photon_e_mev"]]
    sig = sig.merge(ex, on=["file_index", "ev"], how="left", validate="one_to_one"); assert sig.photon_px.notna().all()
    assert (abs(sig.photon_e_mev - sig.photon_mev) < 1e-3).all()
    sig["cos_theta_beam"] = sig.photon_pz / np.sqrt(sig.photon_px ** 2 + sig.photon_py ** 2 + sig.photon_pz ** 2)
    t = X.signal_event_table(sig, events, cands, cfg, policy="any"); assert len(t) == 117 and int(t.A_final.sum()) == 13
    t["photon_energy_mev"] = t.photon_mev
    out = {"n": len(t), "final": int(t.A_final.sum())}
    rows = []
    for var, e in V.items() if False else bins_nat().items():
        for stage_name, col in (("candidate", "A_candidate"), ("final", "A_final")):
            for i in range(len(e) - 1):
                for samp, d in (("natural_cv", t), ("official", tab)):
                    m = ((d[var] >= e[i]) & ((d[var] < e[i + 1]) if i < len(e) - 2 else (d[var] <= e[i + 1]))).to_numpy()
                    rows.append(dict(variable=var, lo=e[i], hi=e[i + 1], stage=stage_name, sample=samp, n=int(m.sum()), k=int((m & d[col].to_numpy(bool)).sum())))
    r = pd.DataFrame(rows)
    w = r.pivot_table(index=["variable", "lo", "hi", "stage"], columns="sample", values=["n", "k"]).reset_index(); w.columns = ["_".join([c for c in col if c]) for col in w.columns]
    w["eff_nat"] = w.k_natural_cv / w.n_natural_cv; w["eff_off"] = w.k_official / w.n_official
    w["fisher_p"] = [stats.fisher_exact([[a, b - a], [c, d - c]])[1] for a, b, c, d in zip(w.k_natural_cv, w.n_natural_cv, w.k_official, w.n_official)]
    ci = [X.binom_ci(int(k), int(n)) for k, n in zip(w.k_natural_cv, w.n_natural_cv)]; w["nat_lo68"] = [c[1] for c in ci]; w["nat_hi68"] = [c[2] for c in ci]
    ci = [X.binom_ci(int(k), int(n)) for k, n in zip(w.k_official, w.n_official)]; w["off_lo68"] = [c[1] for c in ci]; w["off_hi68"] = [c[2] for c in ci]
    write(w, "natural_cv_crosscheck.csv")
    # shape of the natural-CV true photon energy / cos against the official distribution
    out["ks_photon_energy_p"] = float(stats.ks_2samp(t.photon_energy_mev, tab.photon_energy_mev).pvalue); out["ks_cos_p"] = float(stats.ks_2samp(t.cos_theta_beam, tab.cos_theta_beam).pvalue)
    fin = w[w.stage == "final"]
    # one chi2-like check per variable: binomial expected (official eff) vs observed in the natural-CV bins
    chi = {}
    for var, g in fin.groupby("variable"):
        exp = g.eff_off * g.n_natural_cv; var_ = g.n_natural_cv * g.eff_off * (1 - g.eff_off); chi2 = float((((g.k_natural_cv - exp) ** 2) / var_).sum()); chi[var] = dict(chi2=chi2, ndf=len(g), p=float(stats.chi2.sf(chi2, len(g))))
    out["chi2_final_vs_official_eff"] = chi; out["min_fisher_p"] = float(w.fisher_p.min()); out["table"] = w.round(4).to_dict("records")
    SUMMARY["natural_cv"] = out
    fig, ax = PS.figure(1, 2, size=(9, 3.6))
    for a, var in zip(ax[0], ("photon_energy_mev", "cos_theta_beam")):
        g = fin[fin.variable == var]; c = 0.5 * (g.lo + g.hi)
        a.errorbar(c - 0.01 * (g.hi.max() - g.lo.min()), g.eff_off, yerr=[g.eff_off - g.off_lo68, g.off_hi68 - g.eff_off], xerr=0.5 * (g.hi - g.lo), fmt="o", color="#D55E00", label="official dedicated (N=12,427)")
        a.errorbar(c + 0.01 * (g.hi.max() - g.lo.min()), g.eff_nat, yerr=[g.eff_nat - g.nat_lo68, g.nat_hi68 - g.eff_nat], fmt="s", color="#0072B2", label="natural NC-delta in CV (N=117)")
        a.set_xlabel(V[var]["label"]); a.set_ylabel("final efficiency (any)"); a.set_ylim(0, 0.45)
    ax[0][0].legend(fontsize=7); fig.tight_layout(); save(fig, "natural_cv_crosscheck.png")


def bins_nat():
    return DF.load_bins()["broad_bins_natural_cv"]


if __name__ == "__main__":
    main()
