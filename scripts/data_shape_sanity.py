#!/usr/bin/env python
"""Beam-on(open) vs beam-off RAW selected counts and unit-area shapes, common branches only (sanity check; no MC, no scaling, no normalisation).

    python scripts/data_shape_sanity.py
Uses the existing baseline scans (baseline_scan/{beam_on_open,beam_off}). Beam-off is NOT scaled and NOT combined with MC; the flash time and the
vertex sentinels are not used for conclusions (flash time is excluded from the plots).
"""
from __future__ import annotations
import json, os, sys, warnings
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from scipy import stats
from sbnd_single_photon import scanio as SIO, selection as SEL

SCAN = Path(os.environ["SP_DATA"]) / "baseline_scan"; OUT = REPO / "tables" / "background_mechanisms"; PL = REPO / "plots" / "background_mechanisms"
cfg = SEL.load_config(); res = {}; D = {}
for s in ("beam_on_open", "beam_off"):
    tab = SIO.load_scan(SCAN, s); fl = SIO.candidate_chain(tab, cfg); fin = fl[cfg["cuts"][-1]["name"]]
    ev_pass = SIO.event_pass(tab, fin, "any"); idx = SIO.chosen_candidate(tab, fin, "any")
    sel = idx[idx >= 0]; cat = SIO.proton_code(tab["c_np35"][sel])
    ev = bdt_ok = SIO.bdt_evaluable(tab) & fl["candidate_in_valid_event"]
    res[s] = dict(files=int(tab["n_files"]), events=int(len(tab["ev_valid"])), wc_valid=int(tab["ev_valid"].sum()), candidates=int(len(tab["c_gev"])), bdt_evaluable_candidates=int(bdt_ok.sum()),
                  selected_events_any=int(ev_pass.sum()), reco_0p_1p_ge2p=[int((cat == k).sum()) for k in (0, 1, 2)], sum_TotalPOT_not_used=float(tab["pot_total"]))
    D[s] = dict(tab=tab, ok=bdt_ok, sel=sel)
VARS = [("c_score_numu", "BDT numu"), ("c_score_other", "BDT other"), ("c_score_ncpi0", "BDT ncpi0"), ("c_score_nue", "BDT nue"), ("c_np35", "reco protons >35 MeV"),
        ("c_kine_nu_x_corr", "reco vtx x (sentinel (0,0,0) included)"), ("c_kine_nu_y_corr", "reco vtx y"), ("c_kine_nu_z_corr", "reco vtx z")]
ks = {}
fig, ax = plt.subplots(2, 4, figsize=(18, 7)); ax = ax.ravel()
for axi, (v, n) in zip(ax, VARS):
    xs = {s: D[s]["tab"][v][D[s]["ok"]].astype(float) for s in D}
    xs = {s: x[np.isfinite(x)] for s, x in xs.items()}
    lo, hi = np.percentile(np.r_[xs["beam_on_open"], xs["beam_off"]], [1, 99]); bins = np.linspace(lo, hi, 25) if hi > lo else 10
    for s, col in (("beam_on_open", "C3"), ("beam_off", "C0")):
        axi.hist(xs[s], bins=bins, density=True, histtype="step", lw=2, color=col, label=f"{s} (n={len(xs[s])})")
    k = stats.ks_2samp(xs["beam_on_open"], xs["beam_off"]); ks[v] = dict(ks_D=float(k.statistic), ks_p=float(k.pvalue), n_on=int(len(xs["beam_on_open"])), n_off=int(len(xs["beam_off"])))
    axi.set_title(n, fontsize=9)
ax[0].legend(fontsize=7)
fig.suptitle("beam-on (open) vs beam-off: BDT-evaluable candidates, unit-area shapes, common branches (no scaling, no MC)", fontsize=10); fig.tight_layout(); fig.savefig(PL / "beam_on_vs_off_shapes.png", dpi=100); plt.close(fig)
res["shape_ks_bdt_evaluable_candidates"] = ks
json.dump(res, open(OUT / "data_shape_sanity.json", "w"), indent=1)
print(json.dumps(res, indent=1)[:2500])
