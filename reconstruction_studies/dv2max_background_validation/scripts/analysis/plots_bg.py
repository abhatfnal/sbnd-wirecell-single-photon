#!/usr/bin/env python3
"""O vs D distributions per background (identical binning across arms).  Run with ~/.conda/envs/nugraph_env/bin/python
(the login-node system python has no matplotlib).  Reads tables/<runset>_score_migration.csv only;
`plots_bg.py cross` also reads SIGW event59_original_vs_dv2.csv (read-only) and tables/bdt_input_shift_crosssample.csv."""
import csv, os, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

W = "/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/dv2max_background_validation_20261102"
OUT = f"{W}/docs/figures"
SIGW = "/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/dv2max_singlephoton59_20261102"
TH = {"numu": 0.4, "other": 0.2, "ncpi0": -0.05, "nue": -1.0}


def fl(v):
    try:
        return float(v) if v not in ("", None) else None
    except ValueError:
        return None


def hist2(ax, o, d, bins, title, xlabel, thr=None, logx=False):
    o = [x for x in o if x is not None]
    d = [x for x in d if x is not None]
    ax.hist(o, bins=bins, histtype="step", lw=1.6, color="#1f5fa8", label=f"O original (n={len(o)})")
    ax.hist(d, bins=bins, histtype="step", lw=1.6, color="#c2410c", ls="--", label=f"D dv2_split_move (n={len(d)})")
    if thr is not None:
        ax.axvline(thr, color="0.3", lw=1, ls=":")
    if logx:
        ax.set_xscale("log")
    ax.set_title(title, fontsize=10)
    ax.set_xlabel(xlabel)
    ax.set_ylabel("events")
    ax.legend(fontsize=7, frameon=False)


def cross():
    """Signal (SIGW event59 table, read-only) vs backgrounds: vertex-truth distance O vs D, and the paired
    BDT-input net directions (tables/bdt_input_shift_crosssample.csv) of signal vs each background."""
    sig = list(csv.DictReader(open(f"{SIGW}/tables/event59_original_vs_dv2.csv")))
    fig, axs = plt.subplots(1, 5, figsize=(24, 4.6))
    vb = np.logspace(-2, 3, 31)
    for ax, (lab, R) in zip(axs[:3], (("NC-Delta signal", sig),
                                       ("numu CC", list(csv.DictReader(open(f"{W}/tables/numucc_score_migration.csv")))),
                                       ("NC pi0", list(csv.DictReader(open(f"{W}/tables/ncpi0_score_migration.csv")))))):
        g = lambda r, a: (max(fl(r[f"{a}_vertex_truth_dist_cm"]), 1e-2) if fl(r[f"{a}_vertex_truth_dist_cm"]) is not None else None)
        hist2(ax, [g(r, "O") for r in R], [g(r, "D") for r in R], vb, f"{lab}: vertex - truth (true frame)", "distance [cm]", logx=True)
    X = list(csv.DictReader(open(f"{W}/tables/bdt_input_shift_crosssample.csv")))
    s = np.array([float(r["signal_ncdelta_net_direction"]) for r in X])
    for ax, k, lab in ((axs[3], "numucc", "numu CC"), (axs[4], "ncpi0", "NC pi0")):
        b = np.array([float(r[f"{k}_net_direction"]) for r in X])
        ax.scatter(s, b, s=9, color="#1f5fa8", alpha=0.7)
        ax.axhline(0, color="0.6", lw=0.8)
        ax.axvline(0, color="0.6", lw=0.8)
        ax.plot([-1, 1], [-1, 1], color="0.6", lw=0.8, ls=":")
        ax.set_xlim(-0.7, 0.7)
        ax.set_ylim(-0.7, 0.7)
        ax.set_xlabel("signal: P(D>O) - P(D<O)")
        ax.set_ylabel(f"{lab}: P(D>O) - P(D<O)")
        ax.set_title(f"BDT inputs (217): signal vs {lab}, r = {np.corrcoef(s, b)[0, 1]:.2f}", fontsize=10)
    fig.tight_layout()
    fig.savefig(f"{OUT}/crosssample_vertex_and_bdt_inputs.png", dpi=110)
    plt.close(fig)
    print("wrote", f"{OUT}/crosssample_vertex_and_bdt_inputs.png")


def main():
    os.makedirs(OUT, exist_ok=True)
    if sys.argv[1:] == ["cross"]:
        return cross()
    for rs in sys.argv[1:] or ["numucc", "ncpi0"]:
        p = f"{W}/tables/{rs}_score_migration.csv"
        if not os.path.isfile(p):
            continue
        R = list(csv.DictReader(open(p)))
        fig, axs = plt.subplots(2, 4, figsize=(17, 7.5))
        vb = np.logspace(-2, 3, 31)
        hist2(axs[0, 0], [max(fl(r["O_vertex_truth_dist_cm"]) or 0, 1e-2) if fl(r["O_vertex_truth_dist_cm"]) is not None else None for r in R],
              [max(fl(r["D_vertex_truth_dist_cm"]) or 0, 1e-2) if fl(r["D_vertex_truth_dist_cm"]) is not None else None for r in R],
              vb, f"{rs}: vertex - truth (true frame)", "distance [cm]", logx=True)
        hist2(axs[0, 1], [max(fl(r["O_vertex_truth_dist_sce_cm"]) or 0, 1e-2) if fl(r["O_vertex_truth_dist_sce_cm"]) is not None else None for r in R],
              [max(fl(r["D_vertex_truth_dist_sce_cm"]) or 0, 1e-2) if fl(r["D_vertex_truth_dist_sce_cm"]) is not None else None for r in R],
              vb, f"{rs}: vertex - truth (SCE frame)", "distance [cm]", logx=True)
        ib = np.arange(-0.5, 8.5, 1)
        hist2(axs[0, 2], [fl(r["O_n20"]) for r in R], [fl(r["D_n20"]) for r in R], ib, f"{rs}: shw_sp_n_20mev_showers", "n")
        hist2(axs[0, 3], [fl(r["O_n20br1"]) for r in R], [fl(r["D_n20br1"]) for r in R], ib, f"{rs}: shw_sp_n_20br1_showers", "n")
        for j, m in enumerate(("numu", "other", "ncpi0", "nue")):
            hist2(axs[1, j], [fl(r[f"O_{m}_score"]) for r in R], [fl(r[f"D_{m}_score"]) for r in R],
                  np.linspace(-1.0, 1.0, 21) if m != "nue" else np.linspace(-1.0, 1.0, 21),
                  f"{rs}: single_photon_{m}_score (cut {TH[m]})", "BDT score", thr=TH[m])
        fig.tight_layout()
        fig.savefig(f"{OUT}/{rs}_O_vs_D.png", dpi=110)
        plt.close(fig)
        print("wrote", f"{OUT}/{rs}_O_vs_D.png")


if __name__ == "__main__":
    main()
