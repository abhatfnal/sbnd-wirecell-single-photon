#!/usr/bin/env python
"""Exclusive 0p/1p/>=2p characterisation of the FROZEN baseline on a signal population (evaluation only; no cut is changed or scanned).

    source env/setup_eaf.sh
    python scripts/exclusive_signal_characterize.py --label natural_bnb_cv [--tables $SP_DATA/analysis_tables/bnb_cv]
                                                    [--signal-truth <parquet>]   # default: natural NC-delta in the BNB CV

Sample-agnostic inputs (see exclusive_signal.py): a signal-truth parquet, and the derived analysis table of the SAME sample. For the
official Wire-Cell NC-Delta sample only these two inputs change (docs/analysis/OFFICIAL_SIGNAL_WC_ARRIVAL_RUNBOOK.md).
Outputs: tables/exclusive_signal/<label>/*.csv|json, plots/exclusive_signal/<label>_*.png, per-event table of the selected events.
"""
from __future__ import annotations
import argparse, json, os, sys, warnings
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sbnd_single_photon import exclusive_signal as X, natural_signal as NS, selection as SEL

ap = argparse.ArgumentParser(); ap.add_argument("--label", default="natural_bnb_cv")
ap.add_argument("--tables", default=os.path.join(os.environ["SP_DATA"], "analysis_tables", "bnb_cv"))
ap.add_argument("--signal-truth", default=None); ap.add_argument("--tol-cm", type=float, default=5.0)
a = ap.parse_args()
OUT = REPO / "tables" / "exclusive_signal" / a.label; OUT.mkdir(parents=True, exist_ok=True)
PL = REPO / "plots" / "exclusive_signal"; PL.mkdir(parents=True, exist_ok=True)
DATA = Path(os.environ["SP_DATA"]) / "exclusive_signal" / a.label; DATA.mkdir(parents=True, exist_ok=True)   # per-event tables (Parquet) stay outside Git
cfg = SEL.load_config(); T = Path(a.tables)
events = pd.read_parquet(T / "events.parquet"); cands = pd.read_parquet(T / "candidates.parquet")
if a.signal_truth:
    sig = pd.read_parquet(a.signal_truth)
else:
    sn = pd.read_parquet(Path(os.environ["SP_DATA"]) / "natural_ncdelta_bnb_cv" / "signal_neutrinos.parquet")
    sig = NS.to_signal_truth_table(sn)
need = {"file_index", "ev", "x", "y", "z", "truth_cat", "delta_pdg", "in_region"}
assert need <= set(sig.columns), need - set(sig.columns)
sig_all = sig; sig = sig[sig.in_region].reset_index(drop=True)
print(f"{a.label}: {len(sig_all)} signal events, {len(sig)} in the provisional truth region")
tabs = {p: X.signal_event_table(sig, events, cands, cfg, policy=p, tol_cm=a.tol_cm) for p in ("any", "first")}
tabs_all = {p: X.signal_event_table(sig_all, events, cands, cfg, policy=p, tol_cm=a.tol_cm) for p in ("any",)}
stage_names = [s for s, _ in X.stage_defs(cfg)]
res = dict(label=a.label, n_signal_events_all=int(len(sig_all)), n_in_region=int(len(sig)), tol_cm=a.tol_cm, proton_threshold_mev=35.0,
           truth_denominator={X.CAT_LABEL[k]: int((sig.truth_cat == k).sum()) for k in (0, 1, 2)})

# ---- Task 1: cutflow by truth category, view A (actual) and B (truth-matched diagnostic), both policies
for p, t in tabs.items():
    for v in ("A", "B"):
        cf = X.cutflow_by_truth(t, v, stage_names)
        cf.to_csv(OUT / f"cutflow_{v}_{p}.csv", index=False)
        piv = cf.pivot(index="stage", columns="group", values="N").reindex(cf.stage.unique())[["all", "0p", "1p", ">=2p"]]
        res[f"cutflow_{v}_{p}"] = piv.astype(int).to_dict("index")
# ---- Task 2: first failure, by truth category and by Delta charge (separate axis)
for p, t in tabs.items():
    for v, reasons in (("A", X.REASONS_A), ("B", X.REASONS_B)):
        col = f"first_fail_{v}"
        X.first_failure_table(t, col, reasons, "truth_cat").to_csv(OUT / f"first_failure_{v}_{p}_by_truth.csv", index=False)
        X.first_failure_table(t, col, reasons, "delta_pdg").rename(columns={"2114": "Delta0_to_ngamma", "2214": "Delta+_to_pgamma"}).to_csv(OUT / f"first_failure_{v}_{p}_by_delta.csv", index=False)
# ---- Task 3: migration at the checkpoints
for p, t in tabs.items():
    for name, m in X.migration_checkpoints(t).items():
        m.to_csv(OUT / f"migration_{p}_{name}_raw.csv")
        # row-normalised version
        r = m.copy(); tot = r.pop("row_total").replace(0, np.nan); r.div(tot, axis=0).round(4).to_csv(OUT / f"migration_{p}_{name}_rownorm.csv")
# ---- Task 6: efficiency cross-check
eff = X.efficiency_table(tabs["any"], tabs["first"]); eff.to_csv(OUT / "efficiency_crosscheck.csv", index=False)
res["efficiency_crosscheck"] = eff.round(4).to_dict("records")
# ---- Task 8: Delta charge vs topology
dt = X.delta_topology(tabs["any"])
for k, v in dt.items():
    v.to_csv(OUT / f"delta_topology_any_{k}.csv"); res[f"delta_topology_any_{k}"] = v.to_dict("index")
dtf = X.delta_topology(tabs["first"])
for k, v in dtf.items():
    v.to_csv(OUT / f"delta_topology_first_{k}.csv")
# ---- Task 5: selected-event table (any policy), one row per selected signal event, small
t = tabs["any"]; selev = t[t.A_final].copy()
cc = cands.merge(selev[X.KEY + ["sel_nu_index"]], left_on=X.KEY + ["c_nu_index"], right_on=X.KEY + ["sel_nu_index"], how="inner")
keep = ["c_shw_sp_energy", "c_kine_reco_Enu", "c_lead_proton_ke_mev", "c_sum_proton_ke_mev", "c_np35", "c_nrows", "c_kine_nu_x_corr", "c_kine_nu_y_corr",
        "c_kine_nu_z_corr", "c_score_numu", "c_score_other", "c_score_ncpi0", "c_score_nue", "c_flash_time_us", "c_shw_sp_n_20mev_showers", "dom_q", "dom_q_cand", "run", "subrun", "evt"]
sel = selev.drop(columns=["dom_q", "dom_q_cand"]).merge(cc[X.KEY + keep], on=X.KEY, how="left")
sel["match_purity"] = sel.dom_q / sel.dom_q_cand
sel["reco_channel"] = sel.sel_reco_cat.map({0: "1g0p", 1: "1g1p", 2: "ge2p_diag"})
sel["truth_class"] = sel.truth_cat.map(X.CAT_LABEL); sel["delta"] = sel.delta_pdg.map({2114: "D0->n", 2214: "D+->p"})
sel["first_policy_selected"] = sel[X.KEY].merge(tabs["first"][X.KEY + ["A_final"]].rename(columns={"A_final": "fp"}), on=X.KEY, how="left").fp.values
cols = ["file_index", "ev", "run", "subrun", "evt", "truth_class", "delta", "nucleon_pdg", "photon_mev", "E", "x", "y", "z", "reco_channel", "n_pass", "sel_is_matched",
        "match_purity", "c_shw_sp_energy", "c_kine_reco_Enu", "c_np35", "c_lead_proton_ke_mev", "c_sum_proton_ke_mev", "c_kine_nu_x_corr", "c_kine_nu_y_corr", "c_kine_nu_z_corr",
        "c_score_numu", "c_score_other", "c_score_ncpi0", "c_score_nue", "c_flash_time_us", "first_policy_selected"]
sel[cols].round(3).to_csv(OUT / "selected_signal_events_any.csv", index=False)
res["selected_any"] = dict(n=int(len(sel)), reco_channel=sel.reco_channel.value_counts().to_dict(), truth=sel.truth_class.value_counts().to_dict(),
                           n_selected_candidate_not_signal_matched=int((~sel.sel_is_matched).sum()),
                           n_events_multiple_passing=int((sel.n_pass > 1).sum()))
for p, tt in tabs.items():
    res[f"final_{p}"] = dict(total=int(tt.A_final.sum()), **{X.CAT_LABEL[k]: int(tt[tt.truth_cat == k].A_final.sum()) for k in (0, 1, 2)},
                             reco={X.CAT_LABEL[k]: int(((tt.sel_reco_cat == k) & tt.A_final).sum()) for k in (0, 1, 2)})
res["all_signal_events_any_final"] = int(tabs_all["any"].A_final.sum())
# persist event tables for the downstream scripts (small)
for p, tt in tabs.items():
    tt.to_parquet(DATA / f"signal_event_table_{p}.parquet")
json.dump(res, open(OUT / "summary.json", "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))

# ---- plots (matplotlib only)
cf = pd.read_csv(OUT / "cutflow_A_any.csv"); cfb = pd.read_csv(OUT / "cutflow_B_any.csv")
fig, ax = plt.subplots(1, 2, figsize=(13, 4.6))
for axi, c, ttl in ((ax[0], cf, "A: actual selection (reco only)"), (ax[1], cfb, "B: truth-matched candidate (diagnostic)")):
    st = list(c.stage.unique()); xs = np.arange(len(st))
    for i, (g, col) in enumerate((("all", "k"), ("0p", "C0"), ("1p", "C1"), (">=2p", "C2"))):
        d = c[c.group == g].set_index("stage").loc[st]
        axi.errorbar(xs + 0.12 * (i - 1.5), d.fraction, yerr=[d.fraction - d.lo68, d.hi68 - d.fraction], fmt="o-", ms=4, lw=1, color=col, label=f"truth {g}")
    axi.set_xticks(xs); axi.set_xticklabels(st, rotation=60, ha="right", fontsize=8); axi.set_ylim(0, 1.05); axi.set_ylabel("fraction of truth denominator"); axi.set_title(ttl, fontsize=10); axi.legend(fontsize=8)
fig.suptitle(f"{a.label}: frozen-baseline cutflow by truth proton category (provisional region, 35 MeV, policy any; 68% exact intervals)", fontsize=10)
fig.tight_layout(); fig.savefig(PL / f"{a.label}_cutflow_by_truth.png", dpi=110); plt.close(fig)
ff = pd.read_csv(OUT / "first_failure_A_any_by_truth.csv").set_index("reason")
fig, ax = plt.subplots(figsize=(7.5, 4.6)); bottom = np.zeros(3)
for r in X.REASONS_A:
    v = ff.loc[r, ["0p", "1p", ">=2p"]].values.astype(float); n = ff.loc["selected", ["0p", "1p", ">=2p"]].values.astype(float)
    tot = ff[["0p", "1p", ">=2p"]].sum().values
    ax.bar(["truth 0p", "truth 1p", "truth >=2p"], v, bottom=bottom, label=r); bottom += v
ax.set_ylabel("signal events"); ax.set_title("first-failure reason (actual selection, policy any)", fontsize=10); ax.legend(fontsize=7, ncol=2)
fig.tight_layout(); fig.savefig(PL / f"{a.label}_first_failure.png", dpi=110); plt.close(fig)
cps = X.migration_checkpoints(tabs["any"]); fig, ax = plt.subplots(1, 4, figsize=(15, 3.6))
for axi, k in zip(ax, ["A_all_truth_events__matched_candidate", "B_events_with_matched_candidate", "C_matched_candidate_bdt_evaluable", "D_final_events__analysis_selected_candidate"]):
    m = cps[k].drop(columns="row_total"); axi.imshow(m.values, cmap="Blues")
    for i in range(3):
        for j in range(4):
            axi.text(j, i, int(m.values[i, j]), ha="center", va="center", fontsize=9)
    axi.set_xticks(range(4)); axi.set_xticklabels(["0p", "1p", ">=2p", "none"]); axi.set_yticks(range(3)); axi.set_yticklabels(["t0p", "t1p", "t>=2p"]); axi.set_title(k.replace("__", "\n"), fontsize=8)
fig.tight_layout(); fig.savefig(PL / f"{a.label}_migration.png", dpi=110); plt.close(fig)
print(json.dumps({k: res[k] for k in ("truth_denominator", "final_any", "final_first", "selected_any")}, default=str))
