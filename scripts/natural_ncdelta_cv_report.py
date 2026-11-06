#!/usr/bin/env python
"""Natural NC Delta -> N gamma in the BNB CV vs the dedicated official EX_ncdeltarad sample, plus the frozen baseline on the natural events.
Truth bookkeeping only; nothing is tuned and no efficiency is claimed. Inputs (outside Git): natural_ncdelta_bnb_cv/*.parquet,
official_gen2_ncdelta_truth/*.parquet, analysis_tables/bnb_cv/*.parquet. Outputs: tables/natural_ncdelta/, plots/natural_ncdelta/."""
import json, os, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src"))
from sbnd_single_photon import natural_signal as NS, selection as SEL  # noqa: E402
from sbnd_single_photon.truth import ActiveVolume  # noqa: E402
from sbnd_single_photon.truth_signal import FILTER_BOX  # noqa: E402
SPD = Path(os.environ["SP_DATA"]); NAT = SPD / "natural_ncdelta_bnb_cv"; OFF = SPD / "official_gen2_ncdelta_truth"; AT = SPD / "analysis_tables" / "bnb_cv"
T = REPO / "tables" / "natural_ncdelta"; P = REPO / "plots" / "natural_ncdelta"; T.mkdir(parents=True, exist_ok=True); P.mkdir(parents=True, exist_ok=True)
TPC = ActiveVolume()

# ---------------- natural CV
nf, ne, nq = (pd.read_parquet(NAT / f"{n}.parquet") for n in ("files", "events", "signal_neutrinos"))
nq = nq.rename(columns={"k": "nu_k"})
sel_cv = NS.select_signal_neutrino(nq)
sel_cv = sel_cv.merge(ne[["file_index", "ev", "run", "subrun", "evt"]], on=["file_index", "ev"], how="left")
pot_cv = float(nf.TotalPOT.sum())
# ---------------- dedicated
on = pd.read_parquet(OFF / "neutrinos.parquet"); oe = pd.read_parquet(OFF / "events.parquet"); of = pd.read_parquet(OFF / "files.parquet")
on["nu_k"] = on.groupby(["file_index", "ev"]).cumcount()
oq = on[(on.isnc == 1) & (on.rec_is_delta_rad == 1)].rename(columns={"position_x": "x", "position_y": "y", "position_z": "z", "rec_delta_pdg": "delta_pdg", "rec_photon_e_gev": "photon_gev"}).copy()
oq["photon_mev"] = oq.photon_gev * 1000.0; oq["n_p35"] = oq.n_p35
sel_ded = NS.select_signal_neutrino(oq)
pot_ded = float(of.TotalPOT.sum())
sel_cv["photon_mev"] = sel_cv.photon_mev
for d in (sel_cv, sel_ded):
    d["in_tpc"] = TPC.contains(d.x, d.y, d.z); d["pcat"] = np.minimum(d.n_p35, 2); d["flav"] = d.pdg
out = {"pot_cv": pot_cv, "pot_dedicated": pot_ded}

def pop(d, nm):
    return dict(n_events=len(d), n_qualifying_neutrinos=int(d.n_signal_nu.sum()), events_with_2plus_signal_nu=int((d.n_signal_nu >= 2).sum()),
        events_2plus_in_box=int((d.n_signal_nu_in_box >= 2).sum()), delta0=int((d.delta_pdg == 2114).sum()), deltaplus=int((d.delta_pdg == 2214).sum()),
        flavour={str(k): int(v) for k, v in d.flav.value_counts().items()}, in_filter_box=int(d.selected_in_box.sum()), in_provisional_tpc=int(d.in_tpc.sum()),
        p0=int((d.pcat == 0).sum()), p1=int((d.pcat == 1).sum()), p2=int((d.pcat == 2).sum()),
        photon_mev_q=np.nanpercentile(d.photon_mev, [5, 25, 50, 75, 95]).round(1).tolist(), nu_energy_gev_q=np.nanpercentile(d.E, [5, 25, 50, 75, 95]).round(3).tolist())
out["natural_cv"] = pop(sel_cv, "cv"); out["dedicated"] = pop(sel_ded, "ded")
out["natural_cv"]["rate_per_POT_all"] = len(sel_cv) / pot_cv; out["dedicated"]["rate_per_POT_all"] = len(sel_ded) / pot_ded
# ---------------- like-for-like comparison: vertex in the provisional active TPC box (the CV generator keeps events with the vertex in the TPC)
cv, de = sel_cv[sel_cv.in_tpc], sel_ded[sel_ded.in_tpc]
n1, n2 = len(cv), len(de); r1, r2 = n1 / pot_cv, n2 / pot_ded
bt = stats.binomtest(n1, n1 + n2, pot_cv / (pot_cv + pot_ded))          # conditional on the total, rates equal <=> n1 ~ Bin(n1+n2, POT share)
ci = bt.proportion_ci(0.95)
ratio = (n1 / pot_cv) / (n2 / pot_ded)
share = lambda p: p / (1 - p) * (pot_ded / pot_cv)
cmp = dict(region="provisional active TPC box", n_cv=n1, n_dedicated=n2, rate_cv_per_1e20=r1 * 1e20, rate_dedicated_per_1e20=r2 * 1e20,
           rate_ratio_cv_over_dedicated=ratio, ratio_95ci=[share(ci.low), share(ci.high)], binomial_p_equal_rates=float(bt.pvalue),
           expected_n_cv_if_equal=r2 * pot_cv, poisson_z=float((n1 - r2 * pot_cv) / np.sqrt(max(r2 * pot_cv, 1e-9))))
out["comparison_tpc_box"] = cmp
def wilson(k, n):
    lo, hi = stats.binomtest(k, n).proportion_ci(0.95, method="wilson"); return [round(lo, 4), round(hi, 4)]
fr = {}
for name, f in (("delta0_fraction", lambda d: (d.delta_pdg == 2114)), ("truth_0p", lambda d: d.pcat == 0), ("truth_1p", lambda d: d.pcat == 1), ("truth_ge2p", lambda d: d.pcat == 2),
                ("nu_mu_fraction", lambda d: d.flav == 14), ("antinu_mu_fraction", lambda d: d.flav == -14), ("nu_e_fraction", lambda d: abs(d.flav) == 12)):
    a, b = int(f(cv).sum()), int(f(de).sum())
    tab = [[a, n1 - a], [b, n2 - b]]; p = float(stats.fisher_exact(tab)[1])
    fr[name] = dict(cv=a / n1, cv_ci=wilson(a, n1), dedicated=b / n2, dedicated_ci=wilson(b, n2), fisher_p=p, cv_n=a, dedicated_n=b)
out["fractions_tpc_box"] = fr
ct = [[int((cv.pcat == k).sum()) for k in (0, 1, 2)], [int((de.pcat == k).sum()) for k in (0, 1, 2)]]
chi = stats.chi2_contingency(ct); out["truth_proton_3cat_chi2"] = dict(table=ct, chi2=float(chi[0]), dof=int(chi[2]), p=float(chi[1]))
ks = {}
for nm, col in (("photon_energy_mev", "photon_mev"), ("nu_energy_gev", "E"), ("vertex_x", "x"), ("vertex_y", "y"), ("vertex_z", "z")):
    r = stats.ks_2samp(cv[col].dropna(), de[col].dropna()); ks[nm] = dict(ks_stat=float(r.statistic), p=float(r.pvalue), n_cv=len(cv), n_dedicated=len(de))
out["ks_tpc_box"] = ks
# ---------------- dedicated filter-box count vs CV for information (CV keeps padding-region signals only via the dirt path: NOT like-for-like)
# ---------------- plot
fig, ax = plt.subplots(2, 4, figsize=(18, 8)); ax = ax.ravel()
def h(a, col, bins, lab):
    ax[a].hist(de[col].dropna(), bins=bins, density=True, histtype="step", lw=2, label=f"dedicated (n={n2})", color="#0072B2")
    ax[a].hist(cv[col].dropna(), bins=bins, density=True, histtype="step", lw=2, label=f"natural in BNB CV (n={n1})", color="#D55E00"); ax[a].set_xlabel(lab)
    ax[a].text(.97, .95, f"KS p={stats.ks_2samp(cv[col].dropna(), de[col].dropna()).pvalue:.2f}", transform=ax[a].transAxes, ha="right", va="top", fontsize=9)
h(0, "photon_mev", np.linspace(0, 1000, 26), "radiative photon energy [MeV]"); h(1, "E", np.linspace(0, 4, 26), "true E_nu [GeV]")
h(2, "x", np.linspace(-200, 200, 21), "vertex x [cm]"); h(3, "z", np.linspace(0, 500, 21), "vertex z [cm]")
w = np.arange(3); ax[4].bar(w - .2, [ (de.pcat == k).mean() for k in w], .4, label="dedicated", color="#0072B2"); ax[4].bar(w + .2, [(cv.pcat == k).mean() for k in w], .4, label="natural CV", color="#D55E00")
ax[4].set_xticks(w); ax[4].set_xticklabels(["0p", "1p", ">=2p"]); ax[4].set_xlabel("truth protons KE>35 MeV (fraction)")
ax[5].bar([0, 1], [(de.delta_pdg == 2114).mean(), (cv.delta_pdg == 2114).mean()], color=["#0072B2", "#D55E00"]); ax[5].set_xticks([0, 1]); ax[5].set_xticklabels(["dedicated", "natural CV"]); ax[5].set_ylabel("Delta0 -> n gamma fraction"); ax[5].set_ylim(0, 1)
ax[6].errorbar([0, 1], [r2 * 1e20, r1 * 1e20], yerr=[np.sqrt(n2) / pot_ded * 1e20, np.sqrt(n1) / pot_cv * 1e20], fmt="o", color="k"); ax[6].set_xticks([0, 1]); ax[6].set_xticklabels(["dedicated", "natural CV"]); ax[6].set_ylabel("signal in TPC box per 1e20 POT"); ax[6].set_xlim(-.5, 1.5); ax[6].set_ylim(bottom=0)
ax[7].axis("off"); ax[0].legend(fontsize=8)
fig.suptitle("Natural NC Delta -> N gamma in the BNB CV vs the dedicated EX_ncdeltarad sample (vertex in provisional active TPC box; truth only; no tuning)", fontsize=10, color="firebrick")
fig.tight_layout(); fig.savefig(P / "natural_vs_dedicated.png", dpi=75)
# ---------------- frozen baseline on natural events (join by the full event key)
cands = pd.read_parquet(AT / "candidates.parquet"); evt = pd.read_parquet(AT / "events.parquet"); cfg = SEL.load_config()
bl = {}
for nm, d in (("all_natural_signal_events", sel_cv), ("signal_vertex_in_provisional_tpc", sel_cv[sel_cv.in_tpc]), ("signal_vertex_in_filter_box", sel_cv[sel_cv.selected_in_box])):
    bl[nm] = NS.stage_counts(d, evt, cands, cfg)
out["frozen_baseline_on_natural_signal"] = bl
# which of the final CV selected events are natural-signal events; is the selected candidate dominated by the signal neutrino (truth, evaluation only)
fin = cands[cands.pass_final].sort_values(["file_index", "ev", "c_nu_index"]).drop_duplicates(["file_index", "ev"])
j = fin.merge(sel_cv[["file_index", "ev", "x", "y", "z", "n_p35", "in_tpc"]], on=["file_index", "ev"], how="inner")
dist = np.sqrt((j.dom_nu_vx - j.x) ** 2 + (j.dom_nu_vy - j.y) ** 2 + (j.dom_nu_vz - j.z) ** 2)
out["final_selected_cv_events_that_are_natural_signal"] = dict(n_final_any=int(len(fin)), n_natural_signal_among_final=int(len(j)), candidate_dominated_by_signal_neutrino_within_5cm=int((dist < 5).sum()),
                                                                reco_0p_1p_ge2p=[int((j.reco_proton_cat == k).sum()) for k in (0, 1, 2)])
# bookkeeping: events with qualifying neutrinos that are multi-signal
dbl = sel_cv[sel_cv.n_signal_nu >= 2]
out["double_signal_events_cv"] = dict(n=len(dbl), selected_in_box=int(dbl.selected_in_box.sum()), events=dbl[["file_index", "ev", "run", "subrun", "evt", "n_signal_nu", "n_signal_nu_in_box"]].to_dict("records"))
dd = sel_ded[sel_ded.n_signal_nu >= 2]
qq = oq.merge(dd[["file_index", "ev"]], on=["file_index", "ev"]); qq["pc"] = np.minimum(qq.n_p35, 2); qq["tpc"] = TPC.contains(qq.x, qq.y, qq.z); qq["box"] = NS.in_box(qq)
g = qq.groupby(["file_index", "ev"])
out["double_signal_events_dedicated"] = dict(n=int(g.ngroups), same_proton_category=int((g.pc.nunique() == 1).sum()), same_tpc_region=int((g.tpc.nunique() == 1).sum()),
    exactly_one_in_filter_box=int((g.box.sum() == 1).sum()), category_differs_between_choices=int((g.pc.nunique() > 1).sum()),
    category_of_in_box_choice={str(k): int(v) for k, v in dd.pcat.value_counts().items()})
(T / "natural_ncdelta_crosscheck.json").write_text(json.dumps(out, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
sel_cv[["file_index", "ev", "run", "subrun", "evt", "nu_k", "pdg", "delta_pdg", "nucleon_pdg", "photon_mev", "E", "x", "y", "z", "n_p35", "selected_in_box", "in_tpc", "n_signal_nu"]].to_csv(T / "natural_signal_events_bnb_cv.csv", index=False)
print(json.dumps({k: out[k] for k in ("natural_cv", "dedicated", "comparison_tpc_box")}, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))[:3000])
