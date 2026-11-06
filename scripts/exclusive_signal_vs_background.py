#!/usr/bin/env python
"""What does the FROZEN inherited selection respond to? Signal-matched candidates vs the non-signal BNB population (descriptive only).

    python scripts/exclusive_signal_vs_background.py [--label natural_bnb_cv] [--tables $SP_DATA/analysis_tables/bnb_cv]

No variable ranking, no cut scan, no ROC, no training, no new working point: quantiles, a KS distance as a descriptive shape comparison, and the
pass fractions of the EXISTING cuts. Signal = candidates truth-matched (evaluation only) to an in-region natural signal interaction; background =
all candidates of events that contain no natural NC Delta -> N gamma interaction at all. Compared on the BDT-evaluable candidates (the population
on which the BDT cuts are defined) and, for the final stage, on events.
"""
from __future__ import annotations
import argparse, os, sys, warnings
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from scipy import stats
from sbnd_single_photon import exclusive_signal as X, selection as SEL

ap = argparse.ArgumentParser(); ap.add_argument("--label", default="natural_bnb_cv")
ap.add_argument("--tables", default=os.path.join(os.environ["SP_DATA"], "analysis_tables", "bnb_cv"), help="BACKGROUND population (BNB CV derived table)")
ap.add_argument("--signal-tables", default=None, help="derived table holding the signal candidates; default = --tables (natural-signal rehearsal)")
a = ap.parse_args()
OUT = REPO / "tables" / "exclusive_signal" / a.label; PL = REPO / "plots" / "exclusive_signal"
cfg = SEL.load_config(); stages = X.stage_defs(cfg)
c = pd.read_parquet(Path(a.tables) / "candidates.parquet")
sc = pd.read_parquet(Path(a.signal_tables) / "candidates.parquet") if a.signal_tables else c
sig_in = pd.read_parquet(Path(os.environ["SP_DATA"]) / "exclusive_signal" / a.label / "signal_event_table_any.parquet")
sig_all = pd.read_parquet(Path(os.environ["SP_DATA"]) / "natural_ncdelta_bnb_cv" / "signal_neutrinos.parquet")[X.KEY].drop_duplicates()
for d_ in {id(c): c, id(sc): sc}.values():
    d_["_matched"] = X.match_candidates(d_, sig_in); d_["_bdt_eval"] = d_["cum_n_20mev_showers_gt0"] & d_["bdt_evaluable"]
in_nat = c[X.KEY].merge(sig_all.assign(_n=1), on=X.KEY, how="left")._n.fillna(0).values > 0
S = sc[sc._matched.values]; B = c[~in_nat] if sc is c else c
pre = lambda d: d[d._bdt_eval.values]
VARS = [("c_score_numu", "BDT numu"), ("c_score_other", "BDT other"), ("c_score_ncpi0", "BDT ncpi0"), ("c_score_nue", "BDT nue"),
        ("c_shw_sp_n_20mev_showers", "n showers >20 MeV"), ("c_shw_sp_n_20br1_showers", "n 20br1 showers"), ("c_shw_sp_energy", "main shower E [MeV]"),
        ("c_kine_reco_Enu", "reco E_nu [MeV]"), ("c_lead_proton_ke_mev", "leading proton KE [MeV] (np35>0)"), ("c_np35", "reco protons >35 MeV"),
        ("c_kine_nu_x_corr", "reco vtx x"), ("c_kine_nu_y_corr", "reco vtx y"), ("c_kine_nu_z_corr", "reco vtx z"), ("c_flash_time_us", "flash time [us]"),
        ("c_shw_sp_shw_vtx_dis", "shw_vtx_dis"), ("c_shw_sp_min_dis", "shw min_dis"), ("c_shw_sp_max_shw_dis", "shw max_shw_dis"), ("c_shw_sp_angle_beam", "shw angle_beam"),
        ("c_shw_sp_lowest_dQ_dx", "lowest dQ/dx (<50)"), ("c_shw_sp_medium_dQ_dx", "medium dQ/dx (<50)"), ("c_shw_sp_highest_dQ_dx", "highest dQ/dx (<50)")]
def clean(v, s):
    x = v[s].astype(float)
    if "dQ_dx" in s: x = x[(x < 50)]
    return x[np.isfinite(x)]
rows = []
for s, name in VARS:
    for pop, sg, bg in (("bdt_evaluable_candidates", pre(S), pre(B)),):
        xs, xb = clean(sg, s), clean(bg, s)
        if s == "c_lead_proton_ke_mev": xs, xb = xs[xs > 0], xb[xb > 0]
        if len(xs) < 3: continue
        q = lambda x: np.percentile(x, [5, 25, 50, 75, 95])
        ks = stats.ks_2samp(xs, xb)
        rows.append(dict(variable=s, label=name, population=pop, n_signal=len(xs), n_bkg=len(xb), **{f"sig_q{p}": v for p, v in zip((5, 25, 50, 75, 95), q(xs))},
                         **{f"bkg_q{p}": v for p, v in zip((5, 25, 50, 75, 95), q(xb))}, ks_D=ks.statistic, ks_p=ks.pvalue))
V = pd.DataFrame(rows); V.round(4).to_csv(OUT / "signal_vs_background_variables.csv", index=False)
# reco proton category among evaluable candidates and among final events
cat = {}
for nm, sg, bg in (("evaluable_candidates", pre(S), pre(B)), ("final_events", S[S.pass_final.values], B[B.pass_final.values])):
    cat[nm] = {"signal": [int((sg.reco_proton_cat == k).sum()) for k in (0, 1, 2)], "bkg": [int((bg.reco_proton_cat == k).sum()) for k in (0, 1, 2)]}
pd.DataFrame({f"{k}_{w}": v for k, d in cat.items() for w, v in d.items()}, index=["reco 0p", "reco 1p", "reco >=2p"]).to_csv(OUT / "signal_vs_background_reco_category.csv")
# pass fractions of the EXISTING cuts among BDT-evaluable candidates (cumulative from the evaluable stage)
pf = []
prev = None
for nm, col in [s for s in stages if s[0] not in ("candidate", "n20mev", "bdt_evaluable")]:
    ps, pb = pre(S), pre(B)
    k_s, k_b = int(ps[col].sum()), int(pb[col].sum()); lo, hi = X.binom_ci(k_s, len(ps))[1:]
    pf.append(dict(stage=nm, n_signal_evaluable=len(ps), signal_pass=k_s, signal_frac=k_s / len(ps), sig_lo68=lo, sig_hi68=hi, n_bkg_evaluable=len(pb), bkg_pass=k_b, bkg_frac=k_b / len(pb)))
pd.DataFrame(pf).round(4).to_csv(OUT / "signal_vs_background_cut_pass_fractions.csv", index=False)
# plots
n = len(VARS); fig, ax = plt.subplots(4, 6, figsize=(21, 11)); ax = ax.ravel()
for axi, (s, name) in zip(ax, VARS):
    xs, xb = clean(pre(S), s), clean(pre(B), s)
    if s == "c_lead_proton_ke_mev": xs, xb = xs[xs > 0], xb[xb > 0]
    if len(xs) < 3: axi.set_visible(False); continue
    lo, hi = np.percentile(np.r_[xs, xb], [1, 99]); bins = np.linspace(lo, hi, 25) if hi > lo else 10
    axi.hist(xb, bins=bins, density=True, alpha=.5, color="gray", label=f"non-signal CV (n={len(xb)})"); axi.hist(xs, bins=bins, density=True, histtype="step", color="C3", lw=2, label=f"signal-matched (n={len(xs)})")
    axi.set_title(name, fontsize=9)
ax[0].legend(fontsize=7)
for axi in ax[n:]: axi.set_visible(False)
fig.suptitle("frozen-selection variables, BDT-evaluable candidates: natural-signal-matched vs non-signal BNB CV (shape, area-normalised; descriptive)", fontsize=11)
fig.tight_layout(); fig.savefig(PL / f"{a.label}_signal_vs_background_variables.png", dpi=90); plt.close(fig)
print(V[["label", "n_signal", "n_bkg", "sig_q50", "bkg_q50", "ks_D", "ks_p"]].round(3).to_string()); print(pd.read_csv(OUT / "signal_vs_background_cut_pass_fractions.csv").to_string()); print(pd.read_csv(OUT / "signal_vs_background_reco_category.csv").to_string())
