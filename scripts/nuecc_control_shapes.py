#!/usr/bin/env python
"""nueCC CONTROL-sample shape cross-check against the intrinsic NUE_CC candidates of the ordinary BNB CV. SHAPES ONLY (unit area): no POT, no rate.

    python scripts/nuecc_control_shapes.py          # needs $SP_DATA/analysis_tables/{bnb_cv,nuecc} (build_analysis_table.py)
NUE_CC-like candidate (both samples, same definition): the dominant-charge truth neutrino of the candidate (T_overlap, derived table) is an electron-
flavour CC interaction with its vertex in the provisional TPC box. (The candidate taxonomy of the background study additionally separates CC pi0
first; here pi0 is not split.) The nueCC sample is never added to the CV and nothing is normalised.
"""
from __future__ import annotations
import json, os, sys, warnings
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from scipy import stats
from sbnd_single_photon import exclusive_signal as X, selection as SEL
from sbnd_single_photon.truth import ActiveVolume

SPD = Path(os.environ["SP_DATA"]); OUT = REPO / "tables" / "background_mechanisms"; PL = REPO / "plots" / "background_mechanisms"
cfg = SEL.load_config(); stages = X.stage_defs(cfg)
def load(s):
    c = pd.read_parquet(SPD / "analysis_tables" / s / "candidates.parquet")
    c["_bdt_eval"] = c[stages[1][1]] & c["bdt_evaluable"]
    c["nue_cc_like"] = (c.dom_nu >= 0) & c.dom_ok.fillna(False).astype(bool) & (c.dom_nu_pdg.abs() == 12) & (c.dom_nu_ccnc == 0) & ActiveVolume().contains(c.dom_nu_vx, c.dom_nu_vy, c.dom_nu_vz).fillna(False)
    return c
cv, nc = load("bnb_cv"), load("nuecc")
VARS = [("c_score_numu", "BDT numu"), ("c_score_other", "BDT other"), ("c_score_ncpi0", "BDT ncpi0"), ("c_score_nue", "BDT nue"), ("c_shw_sp_energy", "main shower E [MeV]"), ("c_kine_reco_Enu", "reco E_nu [MeV]"),
        ("c_np35", "reco protons >35 MeV"), ("c_lead_proton_ke_mev", "leading proton KE [MeV]"), ("c_kine_nu_x_corr", "reco vtx x"), ("c_kine_nu_y_corr", "reco vtx y"), ("c_kine_nu_z_corr", "reco vtx z"),
        ("c_shw_sp_shw_vtx_dis", "shw_vtx_dis"), ("c_shw_sp_min_dis", "shw min_dis (sentinel 1000)"), ("c_shw_sp_angle_beam", "shw angle_beam"), ("c_shw_sp_lowest_dQ_dx", "lowest dQ/dx (<50)"),
        ("c_shw_sp_medium_dQ_dx", "medium dQ/dx (<50)"), ("c_shw_sp_highest_dQ_dx", "highest dQ/dx (<50)")]
res = dict(counts={}, ks={})
pops = {"bdt_evaluable": lambda d: d[d.nue_cc_like & d._bdt_eval], "selected_final": lambda d: d[d.nue_cc_like & d.pass_final]}
for pn, f in pops.items():
    a, b = f(cv), f(nc); res["counts"][pn] = dict(cv=len(a), nuecc=len(b), cv_reco_0_1_ge2=[int((a.reco_proton_cat == k).sum()) for k in (0, 1, 2)], nuecc_reco_0_1_ge2=[int((b.reco_proton_cat == k).sum()) for k in (0, 1, 2)])
    fig, ax = plt.subplots(3, 6, figsize=(22, 11)); ax = ax.ravel(); res["ks"][pn] = {}
    for axi, (v, n) in zip(ax, VARS):
        xa, xb = a[v].astype(float), b[v].astype(float)
        if "dQ_dx" in v: xa, xb = xa[xa < 50], xb[xb < 50]
        if v == "c_lead_proton_ke_mev": xa, xb = xa[xa > 0], xb[xb > 0]
        xa, xb = xa[np.isfinite(xa)], xb[np.isfinite(xb)]
        if len(xa) < 3 or len(xb) < 3: axi.set_visible(False); continue
        lo, hi = np.percentile(np.r_[xa, xb], [1, 99]); bins = np.arange(-0.5, 6.5, 1) if v == "c_np35" else (np.linspace(lo, hi, 25) if hi > lo else 10)
        axi.hist(xb, bins=bins, density=True, alpha=.45, color="gray", label=f"nueCC control (n={len(xb)})"); axi.hist(xa, bins=bins, density=True, histtype="step", lw=2, color="C3", label=f"BNB CV intrinsic (n={len(xa)})")
        k = stats.ks_2samp(xa, xb); res["ks"][pn][v] = dict(ks_D=round(float(k.statistic), 4), ks_p=float(k.pvalue), n_cv=len(xa), n_nuecc=len(xb), med_cv=float(np.median(xa)), med_nuecc=float(np.median(xb)))
        axi.set_title(f"{n}   KS D={k.statistic:.2f}", fontsize=9)
    ax[0].legend(fontsize=7)
    for axi in ax[len(VARS):]: axi.set_visible(False)
    fig.suptitle(f"NUE_CC-like candidates, {pn}: unit-area shapes, nueCC control vs BNB CV (NO normalisation, NO rates)", fontsize=11); fig.tight_layout(); fig.savefig(PL / f"nuecc_control_shapes_{pn}.png", dpi=85); plt.close(fig)
json.dump(res, open(OUT / "nuecc_control_shape_crosscheck.json", "w"), indent=1)
print(json.dumps(res["counts"])); 
for pn in res["ks"]:
    print(pn); print(pd.DataFrame(res["ks"][pn]).T.round(3).to_string())
