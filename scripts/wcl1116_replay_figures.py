#!/usr/bin/env python
"""Figures of the Nov16 frozen-R1 replay (old fg1-era reconstruction vs WCLocal2026Nov16). Same binning for both productions; every figure is labelled DIAGNOSTIC.

    source env/setup_eaf.sh && python scripts/wcl1116_replay_figures.py
"""
from wcl1116_replay_common import *
import matplotlib.pyplot as plt
from sbnd_single_photon import plotstyle as PS

PS.apply_style()
CO, CN = "#0072B2", "#D55E00"                      # Okabe-Ito blue = old fg1-era, vermillion = Nov16 (fixed per entity)
TAG = "DIAGNOSTIC: frozen Round-1 selection replayed on WCLocal2026Nov16; not a Round-2 result"


def save(fig, name):
    fig.text(0.01, 0.005, TAG, fontsize=6.5, color="#555555"); fig.tight_layout(rect=(0, 0.02, 1, 1)); fig.savefig(PLOTS / name, bbox_inches="tight"); plt.close(fig); print("wrote", name)


def cutflow():
    d = pd.read_csv(OUT / "signal_cutflow_old_vs_nov16.csv"); n = 12427
    fig, ax = plt.subplots(figsize=(7.2, 3.8)); x = np.arange(len(d)); w = 0.38
    ax.bar(x - w / 2, 100 * d.old_fg1_N / n, w, color=CO, label="old fg1-era reconstruction")
    ax.bar(x + w / 2, 100 * d.nov16_N / n, w, color=CN, label="WCLocal2026Nov16")
    for i, (a, b) in enumerate(zip(d.old_fg1_N, d.nov16_N)):
        ax.text(i - w / 2, 100 * a / n + 0.8, f"{a:,}", ha="center", fontsize=6, rotation=90, va="bottom"); ax.text(i + w / 2, 100 * b / n + 0.8, f"{b:,}", ha="center", fontsize=6, rotation=90, va="bottom")
    ax.set_xticks(x); ax.set_xticklabels(d.stage, rotation=30, ha="right"); ax.set_ylabel("% of 12,427 truth signal events (cumulative)"); ax.set_ylim(0, 118); ax.legend(loc="upper right")
    ax.set_title("Cumulative signal cutflow, frozen selection (any-candidate policy)"); save(fig, "fig_cutflow_old_vs_nov16.png")


def topology():
    e = pd.read_csv(OUT / "signal_topology_efficiency.csv"); e = e[e.policy == "any"]; groups = ["total", "0p", "1p", ">=2p", "Delta0", "Delta+"]
    fig, ax = plt.subplots(figsize=(7.2, 3.6)); x = np.arange(len(groups)); w = 0.38
    for off, lab, col, name in ((-w / 2, "old_fg1", CO, "old fg1-era"), (w / 2, "nov16", CN, "WCLocal2026Nov16")):
        s = e[e.production == lab].set_index("group").loc[groups]
        ax.errorbar(x + off, s.efficiency_pct, yerr=[s.efficiency_pct - s.lo68_pct, s.hi68_pct - s.efficiency_pct], fmt="o", color=col, label=name)
        for xi, v in zip(x + off, s.efficiency_pct):
            ax.text(xi, v + 0.45, f"{v:.2f}", ha="center", fontsize=6.5, color=col)
    ax.set_xticks(x); ax.set_xticklabels(["all", "truth 0p", "truth 1p", r"truth $\geq$2p", r"$\Delta^0$ (descriptive)", r"$\Delta^+$ (descriptive)"], rotation=15)
    ax.set_ylabel("final efficiency [%] (exact binomial 68%)"); ax.set_ylim(0, None); ax.legend(); ax.set_title("Final efficiency by truth topology (Delta charge is not reco proton topology)")
    save(fig, "fig_topology_efficiency_old_vs_nov16.png")


def vertex():
    vo, vn = pd.read_parquet(DER / "signal_vtx_old.parquet"), pd.read_parquet(DER / "signal_vtx_new.parquet")
    edges = np.concatenate([[0], np.logspace(-1, 2.5, 36)])
    fig, ax = plt.subplots(1, 3, figsize=(11, 3.6), sharey=True)
    for a, (g, k) in zip(ax, (("all", None), ("truth 0p", 0), ("truth 1p", 1))):
        for v, col, lab in ((vo, CO, "old fg1-era"), (vn, CN, "WCLocal2026Nov16")):
            t = v.dropna(subset=["dist"]).groupby(RSE).agg(d=("dist", "min"), c=("truth_cat", "first")); t = t if k is None else t[t.c == k]
            a.hist(np.clip(t.d, 0.1, 300), bins=np.logspace(-1, 2.5, 36), histtype="step", color=col, label=f"{lab} (N={len(t):,}, median {t.d.median():.1f} cm)", weights=np.full(len(t), 1.0 / len(t)))
        a.set_xscale("log"); a.set_xlabel("nearest reco-to-true vertex distance [cm]", fontsize=9); a.set_title(g); a.legend(fontsize=6.5, loc="upper left")
    ax[0].set_ylabel("fraction of events per bin (values < 0.1 cm in first bin)"); save(fig, "fig_vertex_distance_old_vs_nov16.png")


def scores():
    d = np.load(DER / "signal_score_distributions.npz"); fig, ax = plt.subplots(1, 4, figsize=(13, 3.4)); rng = {"numu": (-3, 3), "other": (-3, 3), "ncpi0": (-3, 3), "nue": (-3, 3)}
    for a, m in zip(ax, L.MODELS):
        bins = np.linspace(*rng[m], 41)
        for k, col, lab in (("old", CO, "old fg1-era"), ("new", CN, "WCLocal2026Nov16")):
            x = d[f"{k}_{m}"]; a.hist(np.clip(x, *rng[m]), bins=bins, histtype="step", color=col, label=f"{lab} (N={len(x):,})")
        a.axvline(FROZEN[m], color="k", ls="--", lw=0.9); a.set_xlabel(f"SP-{m} score (clipped at +-3)", fontsize=9); a.set_title(f"{m} (cut > {FROZEN[m]:g}, dashed)")
        a.legend(fontsize=6)
    ax[0].set_ylabel("signal events (max over candidates)"); save(fig, "fig_sp_scores_old_vs_nov16.png")


def background():
    c = pd.read_csv(OUT / "bnb_category_old_vs_new.csv"); c = c[c.category != "TOTAL non-signal"]
    fig, ax = plt.subplots(figsize=(7.4, 3.8)); x = np.arange(len(c)); w = 0.38
    ax.bar(x - w / 2, c.old, w, color=CO, label="old fg1-era"); ax.bar(x + w / 2, c.nov16, w, color=CN, label="WCLocal2026Nov16")
    for xi, a, b in zip(x, c.old, c.nov16):
        ax.text(xi - w / 2, a + 0.5, str(a), ha="center", fontsize=6.5); ax.text(xi + w / 2, b + 0.5, str(b), ha="center", fontsize=6.5)
    ax.set_xticks(x); ax.set_xticklabels(c.category, rotation=30, ha="right", fontsize=7); ax.set_ylabel("selected non-signal BNB-CV events"); ax.legend()
    ax.set_title("Selected generic-BNB non-signal events by candidate-associated truth category"); save(fig, "fig_bnb_background_old_vs_nov16.png")


if __name__ == "__main__":
    for f in (cutflow, topology, vertex, scores, background):
        try:
            f()
        except FileNotFoundError as e:
            print("skip", f.__name__, e)
