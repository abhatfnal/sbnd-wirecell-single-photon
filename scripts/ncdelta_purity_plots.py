#!/usr/bin/env python
"""Presentation figures of the frozen-chain purity study (old fg1-era vs Nov16). Reads tables/ncdelta_purity_datamc/*.csv; every figure carries the normalisation banner.
Colours are fixed per production (old = #0072B2, Nov16 = #D55E00) as in the replay figures."""
from ncdelta_purity_common import *
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sbnd_single_photon import plotstyle as PS
PS.apply_style()
CO, CN = "#0072B2", "#D55E00"; C = {"old_fg1": CO, "nov16": CN}; NAME = {"old_fg1": "old fg1-era reco", "nov16": "WCLocal2026Nov16"}
TAG = "expected yields at 1e20 POT: signal = dedicated NC-Delta sample, background = generic BNB CV (in-region natural NC-Delta events removed); NO cosmic-only (beam-off) component -> purity is an UPPER BOUND; statistical errors only; DIAGNOSTIC"
LAB = [PU.STAGE_LABEL[s] for s in PU.STAGES]


def save(fig, n):
    fig.text(0.01, 0.003, TAG, fontsize=6, color="#555"); fig.tight_layout(rect=(0, 0.02, 1, 1)); fig.savefig(PLT / n, bbox_inches="tight", dpi=130); plt.close(fig); print("wrote", n)


def A_cumulative():
    c = pd.read_csv(TAB / "cumulative_efficiency_purity.csv"); fig, ax = plt.subplots(1, 3, figsize=(14, 4)); x = np.arange(len(PU.STAGES))
    for p in PRODUCTIONS:
        d = c[c.production == p].set_index("stage").loc[PU.STAGES]
        ax[0].errorbar(x, d.efficiency_pct, yerr=[d.efficiency_pct - d.eff_lo68_pct, d.eff_hi68_pct - d.efficiency_pct], fmt="o-", color=C[p], label=NAME[p])
        ax[1].errorbar(x, 100 * d.purity, yerr=100 * d.purity_err, fmt="o-", color=C[p], label=NAME[p]); ax[2].plot(x, d.B_per_1e20, "o-", color=C[p], label=NAME[p] + " background")
        ax[2].plot(x, d.S_per_1e20, "s--", color=C[p], mfc="none", label=NAME[p] + " signal")
    ax[0].set_ylabel("cumulative signal efficiency [%] (of 12,427)"); ax[1].set_ylabel("expected purity S/(S+B) [%]"); ax[1].set_yscale("log"); ax[2].set_ylabel("expected events per 1e20 POT"); ax[2].set_yscale("log")
    for a, t in zip(ax, ("efficiency", "purity", "expected signal and background yield")):
        a.set_xticks(x); a.set_xticklabels(LAB, rotation=40, ha="right", fontsize=7); a.set_title(t); a.legend(fontsize=7)
    save(fig, "A_cumulative_efficiency_purity_vs_stage.png")


def B_topology():
    t = pd.read_csv(TAB / "topology_purity.csv"); comp = pd.read_csv(TAB / "background_composition_final_production_matched.csv")
    fig, ax = plt.subplots(1, 2, figsize=(12, 4)); labs = ["1g0p", "1g1p", "1gNp", "ge2p"]; x = np.arange(len(labs)); w = 0.38
    for off, p in ((-w / 2, "old_fg1"), (w / 2, "nov16")):
        d = t[t.production == p].set_index("reco_channel").loc[labs]
        ax[0].bar(x + off, 100 * d.purity, w, yerr=100 * d.purity_err, color=C[p], label=NAME[p])
        for xi, v in zip(x + off, 100 * d.purity): ax[0].text(xi, v + 0.15, f"{v:.1f}", ha="center", fontsize=7)
    ax[0].set_xticks(x); ax[0].set_xticklabels([l.replace("ge2p", ">=2p (diag.)") for l in labs]); ax[0].set_ylabel("expected purity [%] (final frozen selection)"); ax[0].legend(); ax[0].set_title("purity by RECONSTRUCTED proton topology")
    xp = np.arange(3); labp = ["1g0p", "1g1p", "ge2p"]
    for off, p in ((-w / 2, "old_fg1"), (w / 2, "nov16")):
        d = t[t.production == p].set_index("reco_channel").loc[labp]
        ax[1].bar(xp + off, d.S_per_1e20, w, color=C[p], alpha=0.95, label=f"{NAME[p]} signal"); ax[1].bar(xp + off, d.B_per_1e20, w, bottom=d.S_per_1e20, color=C[p], alpha=0.35, hatch="//", label=f"{NAME[p]} background")
    ax[1].set_xticks(xp); ax[1].set_xticklabels([l.replace("ge2p", ">=2p (diag.)") for l in labp]); ax[1].set_ylabel("expected events per 1e20 POT"); ax[1].legend(fontsize=7); ax[1].set_title("signal + background yield (stacked)")
    fig.text(0.01, 0.025, "1gNp = 1g1p + >=2p (reco-proton multiplicity of the selected candidate, >35 MeV; NOT the truth topology; Delta charge is not proton topology); right panel: partition 1g0p + 1g1p + >=2p (1gNp is their sum, not drawn)", fontsize=6.5, color="#555")
    save(fig, "B_topology_purity.png")


def C_tradeoff():
    d = pd.read_csv(TAB / "efficiency_vs_purity_single_score_scan.csv"); fig, ax = plt.subplots(1, 4, figsize=(16, 3.8))
    for a, m in zip(ax, PU.MODELS):
        for p in PRODUCTIONS:
            s = d[(d.production == p) & (d.model == m) & (d.N_cv_background >= 10)]
            a.plot(s.efficiency_pct, 100 * s.purity, "-", color=C[p], label=NAME[p]); f = s[s.frozen_point]
            if len(f): a.plot(f.efficiency_pct, 100 * f.purity, "*", ms=13, color=C[p], mec="k")
        a.set_xlabel("signal efficiency [%]"); a.set_ylabel("expected purity [%]"); a.set_title(f"vary SP-{m} (cut {PU.FROZEN_R1[m]:g}, star); others frozen"); a.legend(fontsize=7)
    fig.text(0.01, 0.025, "DESCRIPTIVE reference of the frozen legacy chain: one score varied, the other three scores, n20 and n20br1 at their frozen values; points with < 10 background events not drawn; NOT a threshold choice", fontsize=6.5, color="#555")
    save(fig, "C_efficiency_vs_purity_single_score.png")


def D_composition():
    c = pd.read_csv(TAB / "background_composition_final_production_matched.csv"); t = pd.read_csv(TAB / "overall_purity.csv").set_index("production")
    cats = ["NC_PI0", "CC_PI0", "NUE_CC", "NUMU_CC", "OTHER_NC", "OTHER_CC", "OUTSIDE_TPC_NU", "COSMIC_OR_UNMATCHED", "MULTI_OR_AMBIGUOUS"]
    col = {"NC_PI0": "#0072B2", "CC_PI0": "#56B4E9", "NUE_CC": "#009E73", "NUMU_CC": "#999999", "OTHER_NC": "#E69F00", "OTHER_CC": "#8C564B", "OUTSIDE_TPC_NU": "#CC79A7", "COSMIC_OR_UNMATCHED": "#444444", "MULTI_OR_AMBIGUOUS": "#CCCCCC"}
    fig, ax = plt.subplots(figsize=(7.5, 4.8)); x = np.arange(2)
    bot = np.zeros(2)
    for p_i, p in enumerate(PRODUCTIONS):
        pass
    S = np.array([t.loc[p, "S_per_1e20"] for p in PRODUCTIONS]); ax.bar(x, S, 0.55, color="#F0E442", edgecolor="k", label="NC-Delta signal (dedicated)"); bot = S.copy()
    for cat in cats:
        v = np.array([c[(c.production == p) & (c.category == cat)].expected_per_1e20.sum() for p in PRODUCTIONS]); ax.bar(x, v, 0.55, bottom=bot, color=col[cat], label=cat); bot += v
    ax.set_xticks(x); ax.set_xticklabels([NAME[p] for p in PRODUCTIONS]); ax.set_ylabel("expected events per 1e20 POT, final frozen selection"); ax.legend(fontsize=7, loc="upper left")
    for xi, p in zip(x, PRODUCTIONS): ax.text(xi, bot[xi] + 40, f"purity {100*t.loc[p,'purity']:.2f}%", ha="center", fontsize=8)
    ax.set_title("Expected composition after the frozen selection (production-matched categories)"); save(fig, "D_signal_background_composition.png")


if __name__ == "__main__":
    for f in (A_cumulative, B_topology, C_tradeoff, D_composition):
        f()
