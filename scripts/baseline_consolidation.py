#!/usr/bin/env python
"""Phase 19: consolidation of the frozen Wire-Cell NC-Delta baseline into ONE machine-readable summary.

    source env/setup_eaf.sh      # not needed: reads only committed tables; no ROOT, no $SP_DATA
    python scripts/baseline_consolidation.py

NO new analysis, NO threshold / weight / policy change.  Every number is read from an already committed table of an earlier phase; the only computations are sums, ratios and Wilson 68 % intervals of those
numbers.  Output: tables/baseline_consolidation/*.csv + summary.json, plots/baseline_consolidation/{fig_cutflow_loss_budget,fig_signal_vs_background_rates}.png.
"""
from __future__ import annotations
import hashlib, json, math, subprocess, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src"))
import numpy as np, pandas as pd
from sbnd_single_photon import numu_audit as NA, plotstyle as PS
import matplotlib.pyplot as plt

T = REPO / "tables"; OUT = T / "baseline_consolidation"; PLT = REPO / "plots" / "baseline_consolidation"; OUT.mkdir(parents=True, exist_ok=True); PLT.mkdir(parents=True, exist_ok=True)
SIG = T / "official_signal" / "official_active_tpc"
S: dict = {}


def wr(df, name, nd=5):
    df.round(nd).to_csv(OUT / name, index=False); return df


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ------------------------------------------------------------------------------------------------------ official signal (Task 2)
cut = pd.read_csv(SIG / "cutflow_A_any.csv"); first = pd.read_csv(SIG / "cutflow_A_first.csv"); eff = pd.read_csv(SIG / "efficiency.csv"); summ = json.load(open(SIG / "summary.json"))
den = cut[(cut.stage == "truth_denominator")].set_index("group").N.to_dict()
rows = []
for pol, df in (("any", cut), ("first", first)):
    for g in ("all", "0p", "1p", ">=2p"):
        r = df[(df.stage == "final") & (df.group == g)].iloc[0]; rows.append(dict(policy=pol, group=g, selected=int(r.N), truth=int(r.denominator), efficiency=r.fraction, lo68=r.lo68, hi68=r.hi68))
dt = pd.read_csv(SIG / "delta_topology_any_truth_all_events.csv", index_col=0); ds = pd.read_csv(SIG / "delta_topology_any_reco_final_selected_stage.csv", index_col=0)
for lab, key in (("Delta0", "Delta0 -> n gamma"), ("Delta+", "Delta+ -> p gamma")):
    k, n = int(ds.loc[key, "total"]), int(dt.loc[key, "total"]); p, lo, hi = NA.wilson(k, n); rows.append(dict(policy="any", group=lab, selected=k, truth=n, efficiency=p, lo68=lo, hi68=hi))
HEAD = wr(pd.DataFrame(rows), "official_signal_headline.csv")
S["signal"] = dict(truth_denominator=den["all"], truth_by_class={g: den[g] for g in ("0p", "1p", ">=2p")}, delta={"Delta0": int(dt.loc["Delta0 -> n gamma", "total"]), "Delta+": int(dt.loc["Delta+ -> p gamma", "total"])},
                   final_any=int(HEAD[(HEAD.policy == "any") & (HEAD.group == "all")].selected.iloc[0]), final_first=int(HEAD[(HEAD.policy == "first") & (HEAD.group == "all")].selected.iloc[0]),
                   eff={f"{r.policy}|{r.group}": [r.selected, r.truth, float(r.efficiency), float(r.lo68), float(r.hi68)] for r in HEAD.itertuples()})

# ------------------------------------------------------------------------------------------------------ migration (Task 3)
mig = pd.read_csv(SIG / "selected_truth_to_reco_any.csv", index_col=0); mig.index = ["truth 0p", "truth 1p", "truth >=2p"]; mig.columns = ["reco 0p", "reco 1p", "reco >=2p"]
mc = pd.read_csv(SIG / "migration_any_A_all_truth_events__matched_candidate_raw.csv", index_col=0)
mig["selected_total"] = mig.sum(axis=1); mig["truth_total"] = [den["0p"], den["1p"], den[">=2p"]]; mig["not_selected"] = mig.truth_total - mig.selected_total
wr(mig.reset_index().rename(columns={"index": "truth"}), "final_truth_to_reco_migration.csv"); wr(mc.reset_index().rename(columns={"index": "truth"}), "matched_candidate_truth_to_reco_migration.csv")
S["migration_final"] = {i: [int(v) for v in mig.loc[i, ["reco 0p", "reco 1p", "reco >=2p"]]] for i in mig.index}; S["not_selected"] = {i: int(mig.loc[i, "not_selected"]) for i in mig.index}
S["migration_matched_candidate"] = {i: [int(v) for v in mc.loc[i].values] for i in mc.index}

# ------------------------------------------------------------------------------------------------------ loss budget (Task 4)
ff = pd.read_csv(SIG / "first_failure_A_any_by_truth.csv").set_index("reason")
ST = [("wc.valid", "wc_valid", ["wc_invalid", "missing_from_merged_caf"]), ("candidate", "candidate", ["no_candidate"]), ("> 20 MeV shower", "n20mev", ["no_20mev_shower"]), ("BDT evaluable", "bdt_evaluable", ["bdt_not_evaluable"]),
      ("numu", "numu", ["fail_numu"]), ("other", "other", ["fail_other"]), ("ncpi0", "ncpi0", ["fail_ncpi0"]), ("nue", "nue", ["fail_nue"]), ("n_20br1", "n20br1", ["fail_n20br1"]), ("final", "final", [])]
N0 = den["all"]; lb = []; prev = N0
for name, key, reasons in ST:
    r = cut[(cut.stage == key) & (cut.group == "all")].iloc[0]; n = int(r.N); fc = int(sum(ff.loc[x, "all"] for x in reasons)) if reasons else 0
    lb.append(dict(stage=name, cumulative_surviving=n, cumulative_efficiency=n / N0, step_loss_cumulative=prev - n, first_failure_count=fc, first_failure_fraction=fc / N0, conditional_survival=n / prev)); prev = n
LB = pd.DataFrame(lb); LB.loc[LB.stage == "final", ["first_failure_count", "first_failure_fraction"]] = [int(ff.loc["selected", "all"]), ff.loc["selected", "all"] / N0]
wr(LB, "loss_budget.csv")
assert int(ff["all"].sum()) == N0 and int(LB.first_failure_count.sum()) == N0
S["loss_budget"] = {r.stage: [int(r.cumulative_surviving), float(r.cumulative_efficiency), int(r.first_failure_count), float(r.first_failure_fraction)] for r in LB.itertuples()}
S["first_failure_cumulative_mismatch"] = dict(numu=int(LB.set_index("stage").loc["numu", "first_failure_count"] - LB.set_index("stage").loc["numu", "step_loss_cumulative"]), ncpi0=int(LB.set_index("stage").loc["ncpi0", "first_failure_count"] - LB.set_index("stage").loc["ncpi0", "step_loss_cumulative"]))
byt = ff.drop(index=["wc_invalid"]).reset_index().rename(columns={"reason": "first_failure"}); wr(byt, "first_failure_by_truth.csv")

# ------------------------------------------------------------------------------------------------------ Phase-18 denominator correction
p18 = pd.read_csv(T / "numu_compact_shower_audit" / "numu_loss_budget.csv"); s18 = json.load(open(T / "numu_compact_shower_audit" / "summary.json"))["loss_budget"]
lost_true = N0 - S["signal"]["final_any"]; corr = []
for r in p18.itertuples():
    corr.append(dict(group=r.group, n=int(r.n), phase18_share_of_loss=float(r.share_of_total_baseline_loss), phase18_denominator=int(s18["n_lost"]), corrected_share_of_loss=r.n / lost_true, corrected_denominator=int(lost_true), share_of_truth_denominator=r.n / N0))
wr(pd.DataFrame(corr), "phase18_loss_share_correction.csv")
S["phase18_correction"] = dict(phase18_denominator_events=int(s18["n_signal_box_events"]), phase18_lost=int(s18["n_lost"]), true_denominator=N0, true_lost=int(lost_true), missing_from_phase18=int(N0 - s18["n_signal_box_events"]),
                               numu_fail_share_phase18=float(s18["numu_fail_share_of_total_loss"]), numu_fail_share_corrected=float(s18["n_fail_numu"] / lost_true), compact_fail=int(s18["n_fail_numu_compact"]), compact_share_corrected=float(s18["n_fail_numu_compact"] / lost_true))

# ------------------------------------------------------------------------------------------------------ background (Tasks 11-12)
bg = json.load(open(T / "official_signal" / "background_rate_model.json")); comp = pd.read_csv(T / "background_mechanisms" / "background_composition_by_channel.csv")
wr(comp, "bnb_background_composition_by_channel.csv")
S["background"] = dict(pot_cv=bg["pot_cv"], selected_nonsignal=bg["background_events"], signal_like_removed=bg["signal_like_removed"], by_channel={k: [v["count"], v["rate_per_1e20_POT"], v["stat_unc_per_1e20_POT"]] for k, v in bg["by_reco_channel"].items()},
                       total_rate_per_1e20=float(sum(v["rate_per_1e20_POT"] for v in bg["by_reco_channel"].values())))
ey = summ["expected_yield"]
S["signal_rate"] = dict(total_per_1e20=ey["total"], total_unc=ey["total_stat_unc"], by_reco_channel=ey["by_reco_channel"], by_reco_channel_unc=ey["by_reco_channel_stat_unc"], by_truth_class=ey["by_truth_class"], pot_signal_sample=ey["pot_signal_sample"], region="provisional TPC box, no reco FV")
rate = pd.DataFrame([dict(channel=c, signal_rate_per_1e20=ey["by_reco_channel"][c], signal_unc=ey["by_reco_channel_stat_unc"][c], bnb_neutrino_background_rate_per_1e20=bg["by_reco_channel"][c]["rate_per_1e20_POT"], bnb_unc=bg["by_reco_channel"][c]["stat_unc_per_1e20_POT"]) for c in ("1g0p", "1g1p", "ge2p")])
rate["signal_over_beam_neutrino_background_reference_ratio"] = rate.signal_rate_per_1e20 / rate.bnb_neutrino_background_rate_per_1e20; wr(rate, "signal_and_bnb_background_rates.csv")

# ------------------------------------------------------------------------------------------------------ natural CV (Task 13)
nat = json.load(open(T / "natural_ncdelta" / "natural_ncdelta_crosscheck.json")); nc = pd.read_csv(T / "official_signal" / "official_baseline" / "natural_cv_cutflow_comparison.csv"); wr(nc, "natural_cv_cutflow.csv")
S["natural_cv"] = dict(n_events=nat["natural_cv"]["n_events"], in_filter_box=nat["natural_cv"]["in_filter_box"], in_tpc_box=nat["natural_cv"]["in_provisional_tpc"], selected_any=int(nc[nc.stage == "final"].rehearsal.iloc[0].split("/")[0]),
                       rate_ratio_cv_over_dedicated=nat["comparison_tpc_box"]["rate_ratio_cv_over_dedicated"], ratio_95ci=nat["comparison_tpc_box"]["ratio_95ci"], binomial_p_equal_rates=nat["comparison_tpc_box"]["binomial_p_equal_rates"],
                       final_p_binom=float(nc[nc.stage == "final"].p_binom.iloc[0]), natural_final_fraction=float(nc[nc.stage == "final"].rehearsal_frac.iloc[0]), official_final_fraction=float(nc[nc.stage == "final"].official_frac.iloc[0]))

# ------------------------------------------------------------------------------------------------------ frozen conventions (Task 14 / tests)
cfg = REPO / "configs" / "baseline_selection.yaml"; dec = json.load(open(T / "analysis_definition_decisions" / "summary.json"))
S["frozen"] = dict(baseline_config_sha256=sha(cfg), numu_xml_sha256="5886affbdb3a4499a4515ecc8d354eb1449e7c204d32f1cc54c1ec8868ead961", candidates_config_sha256=sha(REPO / "configs" / "analysis_definition_candidates.yaml"),
                   thresholds=dict(numu=0.4, other=0.2, ncpi0=-0.05), proton_threshold_mev=35, candidate_policy="any", truth_region="provisional TPC box |x|,|y| < 200 cm, 0 < z < 500 cm (12,427 events); characterisation convention, not an FV")
S["harmonized"] = {r.denominator_set: [int(r.numerator), int(r.denominator), float(r.efficiency)] for r in pd.read_csv(T / "spine_harmonization" / "wc_efficiency_on_harmonized.csv").query("policy == 'any'").itertuples()}
S["metadata"] = dict(git_head_at_run=subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(), note="reads committed tables only")
(OUT / "summary.json").write_text(json.dumps(S, indent=1, default=float))

# ------------------------------------------------------------------------------------------------------ figures
PS.apply_style()
fig, ax = PS.figure(1, 2, size=(11, 4.2)); a = ax[0, 0]; x = np.arange(len(LB)); a.bar(x, LB.cumulative_efficiency, color="#0072B2")
for xi, (n, e) in enumerate(zip(LB.cumulative_surviving, LB.cumulative_efficiency)): a.text(xi, e + 0.01, f"{n:,}", ha="center", fontsize=6.5, rotation=90, va="bottom")
a.set_xticks(x); a.set_xticklabels(LB.stage, rotation=45, ha="right", fontsize=8); a.set_ylabel("cumulative efficiency (of 12,427 truth events)"); a.set_ylim(0, 1.18); a.grid(alpha=.25, axis="y"); a.set_title("frozen chain, policy any", fontsize=9)
b = ax[0, 1]; ffr = LB[LB.stage != "wc.valid"]; colr = ["#56B4E9", "#0072B2", "#009E73", "#E69F00", "#D55E00", "#CC79A7", "#999999", "#F0E442", "#000000"]
b.barh(range(len(ffr)), ffr.first_failure_fraction, color=colr[:len(ffr)]); b.set_yticks(range(len(ffr))); b.set_yticklabels([("selected" if s == "final" else "fail " + s) for s in ffr.stage], fontsize=8); b.invert_yaxis()
for yi, (n, f) in enumerate(zip(ffr.first_failure_count, ffr.first_failure_fraction)): b.text(f + 0.003, yi, f"{n:,} ({100 * f:.1f} %)", va="center", fontsize=7)
b.set_xlabel("first-failure fraction of 12,427 truth events"); b.set_xlim(0, 0.36); b.grid(alpha=.25, axis="x")
fig.subplots_adjust(bottom=0.25); PS.annotate(fig, "official Gen2 NC-Delta | provisional TPC box | frozen selection, policy any | characterisation convention, not an approved definition"); fig.savefig(PLT / "fig_cutflow_loss_budget.png", dpi=150, bbox_inches="tight"); plt.close(fig)

fig, ax = PS.figure(1, 1, size=(6.4, 4.2)); a = ax[0, 0]; w = 0.35; xs = np.arange(3); lab = ["1g0p", "1g1p", ">=2p"]
a.bar(xs - w / 2, rate.signal_rate_per_1e20, w, yerr=rate.signal_unc, color="#0072B2", label="NC-Delta signal (official, provisional TPC box)", capsize=2)
a.bar(xs + w / 2, rate.bnb_neutrino_background_rate_per_1e20, w, yerr=rate.bnb_unc, color="#D55E00", label="selected non-signal BNB-CV (whole generated volume)", capsize=2)
a.set_yscale("log"); a.set_xticks(xs); a.set_xticklabels(lab); a.set_ylabel("selected rate per 1e20 POT (stat. only)"); a.legend(frameon=False, fontsize=7); a.grid(alpha=.25, axis="y")
fig.subplots_adjust(bottom=0.3); PS.annotate(fig, "NOT S/B: different volumes, no beam-off normalisation (cosmic-only component absent), no nueCC special sample; statistical errors only"); fig.savefig(PLT / "fig_signal_vs_background_rates.png", dpi=150, bbox_inches="tight"); plt.close(fig)
print(json.dumps({k: v for k, v in S.items() if k in ("signal", "migration_final", "not_selected", "phase18_correction", "background", "signal_rate", "natural_cv", "first_failure_cumulative_mismatch")}, indent=1, default=float)[:5000]); print(LB.round(4).to_string())
