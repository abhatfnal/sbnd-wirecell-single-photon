#!/usr/bin/env python
"""Shape-only comparison of beam-on (open), beam-off and BNB CV MC (+ nueCC as a separate control) from the baseline scan.

Every panel is area-normalised and stamped 'SHAPE ONLY - NOT EXPOSURE NORMALIZED'. No MC + scaled beam-off prediction is
built (the beam-off scale is unresolved). Only columns common to the older beam-on schema are used.
    python scripts/shape_plots.py [--outdir plots/baseline_shapes]
"""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src"))
from sbnd_single_photon import scanio as X, selection as SEL  # noqa: E402
SPD = os.environ["SP_DATA"]
STAMP = "SHAPE ONLY — NOT EXPOSURE NORMALIZED"
VARS = [  # name, column, bins, log-x, transform
    ("n 20 MeV showers", "c_shw_sp_n_20mev_showers", np.arange(-.5, 8.5, 1), False),
    ("n 20br1 showers", "c_shw_sp_n_20br1_showers", np.arange(-.5, 8.5, 1), False),
    ("numu BDT score", "c_score_numu", np.linspace(-1, 1, 41), False),
    ("other BDT score", "c_score_other", np.linspace(-1, 1, 41), False),
    ("ncpi0 BDT score", "c_score_ncpi0", np.linspace(-1, 1, 41), False),
    ("nue BDT score", "c_score_nue", np.linspace(-1, 1, 41), False),
    ("flash PE", "c_flash_pe", np.logspace(0, 6, 41), True),
    ("flash time [us]", "c_flash_time_us", np.linspace(-2, 5, 36), False),
    ("vertex x (kine_nu_x_corr) [cm]", "c_kine_nu_x_corr", np.linspace(-300, 300, 61), False),
    ("vertex y [cm]", "c_kine_nu_y_corr", np.linspace(-300, 300, 61), False),
    ("vertex z [cm]", "c_kine_nu_z_corr", np.linspace(-50, 600, 66), False),
    ("reco protons KE>35 per candidate", "c_np35", np.arange(-.5, 6.5, 1), False),
]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--outdir", default=str(REPO / "plots" / "baseline_shapes")); a = ap.parse_args()
    out = Path(a.outdir); out.mkdir(parents=True, exist_ok=True)
    cfg = SEL.load_config(); samples = {"beam_on_open": ("beam-on (open)", "k"), "beam_off": ("beam-off", "tab:blue"), "bnb_cv": ("BNB CV MC", "tab:red")}
    tabs = {}
    for s in samples:
        if (Path(SPD) / "baseline_scan" / s).exists():
            tabs[s] = X.load_scan(f"{SPD}/baseline_scan", s)
    summary = {}
    for stage in ("valid_candidates", "final_selected"):
        fig, axs = plt.subplots(3, 4, figsize=(17, 10))
        for ax, (title, col, bins, logx) in zip(axs.flat, VARS):
            for s, t in tabs.items():
                ch = X.candidate_chain(t, cfg)
                m = ch["candidate_in_valid_event"] if stage == "valid_candidates" else ch[cfg["cuts"][-1]["name"]]
                if col not in t:
                    continue
                x = t[col][m].astype(float); x = x[np.isfinite(x)]
                if not len(x):
                    continue
                h, _ = np.histogram(x, bins=bins); w = h / max(h.sum(), 1)
                ax.stairs(w, bins, color=samples[s][1], label=f"{samples[s][0]} (n={len(x)})")
                summary.setdefault(stage, {}).setdefault(s, {})[col] = int(len(x))
            ax.set(xlabel=title, ylabel="area-normalised"); ax.legend(fontsize=7)
            if logx:
                ax.set_xscale("log")
        fig.suptitle(f"{stage.replace('_', ' ')}: {STAMP}", color="firebrick", fontsize=14)
        fig.tight_layout(); fig.savefig(out / f"shapes_{stage}.png", dpi=100); plt.close(fig)
    (out / "shape_counts.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary)[:600])


if __name__ == "__main__":
    main()
