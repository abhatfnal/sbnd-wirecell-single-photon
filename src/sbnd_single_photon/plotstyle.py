"""Plot style and layout helpers (INFRASTRUCTURE ONLY: no data/MC, no beam-off normalisation, no systematics are drawn with these in this phase).

The layout follows the mature SBND analysis figures so future data/MC figures can reuse it unchanged:

* upper panel = physics distribution / efficiency, shared x axis, bin-edge-aware 'step' or error-bar drawing;
* uncertainty representation: statistical (exact binomial 68 %) bars now; a hatched band slot ``uncertainty_band`` is reserved for the future systematic band;
* optional lower ratio panel (``ratio=True``) with a unity line (e.g. data/MC or natural-CV/official);
* common axis conventions: x label with units, y label 'Efficiency' / 'Fraction of truth denominator' / 'Events';
* a provenance annotation (sample, region, policy, proton threshold, 'PRELIMINARY - characterisation, not a final result').

Colours: the Okabe-Ito colour-blind-safe palette, assigned in fixed order to entities (a stage / group keeps its colour in every figure).
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

STYLE_VERSION = "1.0"
OKABE_ITO = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9", "#F0E442", "#000000"]
STAGE_COLOR = {"candidate": "#56B4E9", "n20mev": "#0072B2", "bdt_evaluable": "#009E73", "numu": "#E69F00", "other": "#D55E00", "ncpi0": "#CC79A7", "final": "#000000",
               "final_first": "#7f7f7f", "n20br1": "#000000"}
GROUP_COLOR = {"all": "#000000", "truth_0p": "#0072B2", "truth_1p": "#D55E00", "truth_ge2p": "#009E73", "Delta0": "#CC79A7", "Delta+": "#E69F00"}
GROUP_LABEL = {"all": "all signal", "truth_0p": "truth 0p", "truth_1p": "truth 1p", "truth_ge2p": r"truth $\geq$2p", "Delta0": r"$\Delta^0$", "Delta+": r"$\Delta^+$"}
FF_COLOR = {"missing_from_merged_caf": "#999999", "wc_invalid": "#cccccc", "no_candidate": "#56B4E9", "no_20mev_shower": "#0072B2", "bdt_not_evaluable": "#009E73",
            "fail_numu": "#E69F00", "fail_other": "#D55E00", "fail_ncpi0": "#CC79A7", "fail_nue": "#F0E442", "fail_n20br1": "#8c564b", "selected": "#000000"}
PRELIM = "PRELIMINARY: baseline characterisation, not a final analysis result"


def apply_style():
    plt.rcParams.update({"figure.dpi": 100, "savefig.dpi": 130, "font.size": 10, "axes.labelsize": 11, "axes.titlesize": 10, "legend.fontsize": 8, "legend.frameon": False,
                         "axes.grid": True, "grid.alpha": 0.25, "grid.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False, "errorbar.capsize": 0,
                         "lines.linewidth": 1.6, "lines.markersize": 4})


def figure(nrows=1, ncols=1, *, ratio: bool = False, size=None, sharey=False):
    """(fig, axes). With ``ratio=True`` each column gets an upper physics panel (3/4 height) and a lower ratio panel sharing x; ``axes`` is then
    ``(upper[ncols], lower[ncols])`` arrays, else a 2-D ndarray ``[nrows, ncols]``."""
    apply_style()
    size = size or (4.2 * ncols, 3.4 * nrows + (1.0 if ratio else 0))
    if ratio:
        fig, ax = plt.subplots(2, ncols, figsize=size, sharex="col", gridspec_kw={"height_ratios": [3, 1], "hspace": 0.05}, squeeze=False)
        return fig, (ax[0], ax[1])
    fig, ax = plt.subplots(nrows, ncols, figsize=size, squeeze=False, sharey=sharey)
    return fig, ax


def annotate(fig, text: str, *, extra: str = ""):
    """Provenance line at the bottom of a figure (sample / region / policy / threshold / status)."""
    fig.text(0.01, 0.005, (text + ("  |  " + extra if extra else "")), fontsize=6.5, color="#444444", ha="left", va="bottom")


def eff_errorbar(ax, lo, hi, eff, elo, ehi, *, label=None, color="k", offset=0.0, marker="o", ls="-"):
    """Efficiency points at bin centres with asymmetric exact-binomial error bars and horizontal bin-width bars."""
    lo, hi, eff = map(np.asarray, (lo, hi, eff)); c = 0.5 * (lo + hi) + offset * (hi - lo)
    ok = np.isfinite(eff)
    ax.errorbar(c[ok], eff[ok], yerr=[(eff - np.asarray(elo))[ok], (np.asarray(ehi) - eff)[ok]], xerr=0.5 * (hi - lo)[ok], fmt=marker, color=color, label=label, ls="none", elinewidth=1.0)
    ax.plot(c[ok], eff[ok], color=color, lw=0.8, ls=ls, alpha=0.6)


def uncertainty_band(ax, x_edges, lo, hi, *, color="0.5", label="syst. (reserved)"):
    """Reserved hook for the future systematic band (hatched): not used in the signal-efficiency figures of this phase."""
    ax.fill_between(x_edges, lo, hi, step="post", facecolor="none", edgecolor=color, hatch="////", lw=0, label=label)


def unity_ratio_panel(ax, x_lo, x_hi, ratio, rlo, rhi, *, ylabel="ratio", ylim=(0, 2)):
    c = 0.5 * (np.asarray(x_lo) + np.asarray(x_hi)); ratio = np.asarray(ratio)
    ax.axhline(1.0, color="k", lw=0.8)
    ax.errorbar(c, ratio, yerr=[ratio - np.asarray(rlo), np.asarray(rhi) - ratio], xerr=0.5 * (np.asarray(x_hi) - np.asarray(x_lo)), fmt="o", color="k", ls="none", elinewidth=1.0)
    ax.set_ylabel(ylabel); ax.set_ylim(*ylim)


def stacked_fraction(ax, edges, fractions: dict, colors: dict, labels: dict | None = None):
    """Stacked bars (fractions summing to 1 per bin) with a thin white gap between segments."""
    edges = np.asarray(edges, float); w = np.diff(edges); bottom = np.zeros(len(w))
    for k, v in fractions.items():
        v = np.asarray(v, float)
        ax.bar(edges[:-1], v, width=w, bottom=bottom, align="edge", color=colors.get(k, "0.5"), edgecolor="white", linewidth=0.5, label=(labels or {}).get(k, k))
        bottom += v
    ax.set_ylim(0, 1)
