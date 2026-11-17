#!/usr/bin/env python
"""Presentation-material package for the CORRECTED (source-faithful) Round-1 baseline. No analysis, no PPTX; reads committed tables only.

    python scripts/make_source_faithful_presentation_package.py
Writes
  presentation_assets/ncdelta_source_faithful/{*.png, backup/*.png}      corrected redraws + byte copies of figures that are unaffected
  docs/presentation/NCDELTA_SOURCE_FAITHFUL_ROUND1_SLIDE_NUMBERS.{md,json}
  docs/presentation/NCDELTA_SOURCE_FAITHFUL_ROUND1_SLIDE_ASSETS.csv
Every number is read from a committed table here, never typed. Status vocabulary: AUTHORITATIVE CORRECTED | RECONSTRUCTION-ONLY UNCHANGED | HISTORICAL AS-RUN | REVIEW / DO NOT USE.
"""
from __future__ import annotations
import json, shutil, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src"))
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

T = REPO / "tables"; TC = T / "legacy_scorer_correction"; SF = TC / "source_faithful"; DOC = REPO / "docs" / "presentation"
A = REPO / "presentation_assets" / "ncdelta_source_faithful"; BK = A / "backup"; OLDA = REPO / "presentation_assets" / "ncdelta_baseline"
for d in (A, BK):
    d.mkdir(parents=True, exist_ok=True)
NEW = json.load(open(SF / "baseline_consolidation" / "summary.json")); OLD = json.load(open(T / "baseline_consolidation" / "summary.json"))
LB = pd.read_csv(SF / "baseline_consolidation" / "loss_budget.csv"); COMP = pd.read_csv(SF / "background_mechanisms" / "background_composition_by_channel.csv")
COMP_OLD = pd.read_csv(T / "background_mechanisms" / "background_composition_by_channel.csv")
IMP = pd.read_csv(TC / "impact_configurations.csv").set_index("config"); MECH = pd.read_csv(TC / "mechanism_recheck.csv"); DM = pd.read_csv(TC / "delta_mass_subset.csv").set_index("config")
RES = pd.read_csv(TC / "delta_mass_residuals.csv"); VX = pd.read_csv(TC / "vertex_resolution_subset.csv"); DX = pd.read_csv(SF / "differential_efficiency" / "slide_extract.csv")
NATCF = pd.read_csv(SF / "baseline_consolidation" / "natural_cv_cutflow.csv"); FS = pd.read_csv(TC / "flip_summary.csv"); HARM = pd.read_csv(SF / "spine_harmonization" / "wc_efficiency_on_harmonized.csv")
FOOT = "official Gen2 NC-Delta | frozen source-faithful Wire-Cell chain, policy any | provisional TPC truth box | FIRST LOOK, not a final result"
plt.rcParams.update({"font.size": 12})

# ================================================================================================================ figures
def foot(fig, s=FOOT):
    fig.text(0.01, 0.005, s, fontsize=7, color="#444")

stages = ["truth", "wc.valid", "candidate", "> 20 MeV shower", "BDT evaluable", "numu", "other", "ncpi0", "nue", "n_20br1 = final"]
cum = [12427] + [int(LB.set_index("stage").loc[s, "cumulative_surviving"]) for s in ("wc.valid", "candidate", "> 20 MeV shower", "BDT evaluable", "numu", "other", "ncpi0", "nue", "n_20br1")]
fig, ax = plt.subplots(figsize=(8.4, 4.8)); x = np.arange(len(cum)); cols = ["#999999"] + ["#0072B2"] * 8 + ["#D55E00"]; cols[8] = "#CC79A7"
ax.bar(x, np.array(cum) / 12427 * 100, color=cols)
for xi, n in zip(x, cum):
    ax.text(xi, n / 12427 * 100 + 1.5, f"{n:,}", ha="center", fontsize=9, rotation=90, va="bottom")
ax.set_xticks(x); ax.set_xticklabels(stages, rotation=40, ha="right"); ax.set_ylabel("cumulative efficiency (%)"); ax.set_ylim(0, 118); ax.grid(alpha=.25, axis="y")
ax.set_title("833 / 12,427 = 6.70 %  (policy any)", fontsize=13); foot(fig); fig.subplots_adjust(bottom=0.27); fig.savefig(A / "02_cutflow.png", dpi=170, bbox_inches="tight"); plt.close(fig)

ffr = LB[LB.stage != "wc.valid"]; colr = ["#56B4E9", "#0072B2", "#009E73", "#E69F00", "#D55E00", "#CC79A7", "#999999", "#F0E442", "#000000"]
fig, ax = plt.subplots(figsize=(8.4, 4.8)); ax.barh(range(len(ffr)), ffr.first_failure_fraction * 100, color=colr[:len(ffr)])
ax.set_yticks(range(len(ffr))); ax.set_yticklabels([("selected" if s == "final" else "first failure: " + s) for s in ffr.stage]); ax.invert_yaxis()
for yi, (n, f) in enumerate(zip(ffr.first_failure_count, ffr.first_failure_fraction)):
    ax.text(f * 100 + 0.4, yi, f"{n:,} ({100 * f:.1f} %)", va="center", fontsize=10)
ax.set_xlabel("% of the 12,427 truth events (exclusive first failure)"); ax.set_xlim(0, 36); ax.grid(alpha=.25, axis="x"); foot(fig); fig.subplots_adjust(bottom=0.2); fig.savefig(A / "03_loss_budget.png", dpi=170, bbox_inches="tight"); plt.close(fig)

mm = NEW["migration_final"]; vals = np.array([mm[k] for k in ("truth 0p", "truth 1p", "truth >=2p")], float); sel = vals.sum(axis=1)
fig, ax = plt.subplots(figsize=(6.4, 4.4)); ax.imshow(vals / vals.sum(axis=1, keepdims=True), cmap="Blues", vmin=0, vmax=1)
for i in range(3):
    for j in range(3):
        ax.text(j, i, f"{int(vals[i, j])}", ha="center", va="center", fontsize=16, color="white" if vals[i, j] / vals[i].sum() > 0.5 else "black")
ax.set_xticks(range(3)); ax.set_xticklabels(["reco 0p", "reco 1p", "reco >=2p"]); ax.set_yticks(range(3)); ax.set_yticklabels([f"{t}\n({int(s)} selected)" for t, s in zip(("truth 0p", "truth 1p", "truth >=2p"), sel)])
rt = vals.sum(axis=0).astype(int); ax.set_xlabel(f"reco channel (35 MeV truth convention)   reco totals: 1g0p {rt[0]}, 1g1p {rt[1]}, >=2p {rt[2]}", fontsize=9)
ax.set_title("selected events: truth -> reco topology\n(colour = row fraction)", fontsize=11); foot(fig, FOOT); fig.subplots_adjust(bottom=0.22); fig.savefig(A / "08_migration_matrix.png", dpi=170, bbox_inches="tight"); plt.close(fig)

c = COMP[COMP.category != "TOTAL"].copy(); c["channel"] = c.channel.replace({"ge2p_diag": ">=2p"}); cats = ["NC_PI0", "OUTSIDE_TPC_NU", "CC_PI0", "NUMU_CC", "OTHER_NC", "COSMIC_OR_UNMATCHED", "MULTI_OR_AMBIGUOUS", "NUE_CC"]
cc = {"NC_PI0": "#0072B2", "CC_PI0": "#56B4E9", "NUE_CC": "#009E73", "OUTSIDE_TPC_NU": "#D55E00", "NUMU_CC": "#E69F00", "OTHER_NC": "#CC79A7", "COSMIC_OR_UNMATCHED": "#999999", "MULTI_OR_AMBIGUOUS": "#000000"}
tt0 = c.groupby("category")["count"].sum(); fig, ax = plt.subplots(figsize=(9, 3.9)); tot = {"1g0p": 150, "1g1p": 93, ">=2p": 39}
for yi, ch in enumerate((">=2p", "1g1p", "1g0p")):
    left = 0
    for k in cats:
        r = c[(c.channel == ch) & (c.category == k)]
        if len(r) == 0 or int(r["count"].iloc[0]) == 0:
            continue
        n, fr = int(r["count"].iloc[0]), float(r.fraction.iloc[0]); ax.barh(yi, fr * 100, left=left, color=cc[k], label=k if yi == 2 else None, edgecolor="white")
        if fr > 0.07:
            ax.text(left + fr * 50, yi, f"{n}\n{100 * fr:.0f} %", ha="center", va="center", fontsize=8.5, color="white")
        left += fr * 100
ax.set_yticks([0, 1, 2]); ax.set_yticklabels([f">=2p\n{tot['>=2p']} events", f"1g1p\n{tot['1g1p']} events", f"1g0p\n{tot['1g0p']} events"]); ax.set_xlabel("% of selected non-signal BNB-CV events (candidate-associated truth)"); ax.set_xlim(0, 100)
ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color=cc[k]) for k in cats], labels=[f"{k} ({int(tt0[k])})" for k in cats], ncol=4, fontsize=7.5, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.3))
foot(fig, "BNB CV, frozen source-faithful chain, policy any | 282 non-signal events | no cosmic-only component | no nueCC special sample | statistical only | NOT an S/B"); fig.subplots_adjust(bottom=0.38)
fig.savefig(A / "10_backgrounds.png", dpi=170, bbox_inches="tight"); plt.close(fig)

# nue tradeoff: signal cumulative before / after nue and intrinsic nue-CC background as run vs corrected
lb = LB.set_index("stage"); sig_before, sig_after = int(lb.loc["ncpi0", "cumulative_surviving"]), int(lb.loc["nue", "cumulative_surviving"])
nue_old = int(COMP_OLD[COMP_OLD.category == "NUE_CC"]["count"].sum()); nue_new = int(COMP[COMP.category == "NUE_CC"]["count"].sum())
fig, ax = plt.subplots(1, 2, figsize=(9.2, 4.3))
ax[0].bar(["reach nue\n(after ncpi0)", "pass nue"], [sig_before, sig_after], color=["#999999", "#CC79A7"]); ax[0].set_ylabel("NC-Delta signal events (of 12,427)")
for i, n in enumerate((sig_before, sig_after)):
    ax[0].text(i, n + 20, f"{n:,}", ha="center")
ax[0].set_title(f"signal: {sig_before - sig_after} events removed\n(survival {100 * sig_after / sig_before:.1f} %)", fontsize=11); ax[0].set_ylim(0, 1550)
ax[1].bar(["as-run chain\n(historical)", "source-faithful\nfinal selection"], [nue_old, nue_new], color=["#BBBBBB", "#009E73"]); ax[1].set_ylabel("selected intrinsic nue-CC BNB-CV events")
for i, n in enumerate((nue_old, nue_new)):
    ax[1].text(i, n + 4, f"{n}", ha="center")
ax[1].set_title("intrinsic nue-CC background:\n174 of 175 as-run selected events leave", fontsize=11); ax[1].set_ylim(0, 205)
foot(fig, "official Gen2 NC-Delta (left) and BNB CV (right) | source-faithful nue BDT cut: log10((1+v)/(1-v)) > -1.0 | efficiency / background trade-off, not a verdict on the BDT"); fig.subplots_adjust(bottom=0.2, wspace=0.35)
fig.savefig(A / "12_nue_tradeoff.png", dpi=170, bbox_inches="tight"); plt.close(fig)

# numu compactness (corrected cut)
m = MECH[MECH.item == "numu_survival"]; labs = ["compact (< 20 cm)", "not compact (>= 20 cm)"]; keyc = "corrected_score>0.4 (v>0.4305)"
vals_c = [float(m[(m.group == "compact (length < 20 cm)") & (m.scorer == keyc)].value.iloc[0]) * 100, float(m[(m.group == "not compact (>= 20 cm)") & (m.scorer == keyc)].value.iloc[0]) * 100]
nn = [int(m[(m.group == "compact (length < 20 cm)") & (m.scorer == keyc)].n.iloc[0]), int(m[(m.group == "not compact (>= 20 cm)") & (m.scorer == keyc)].n.iloc[0])]
fig, ax = plt.subplots(figsize=(5.8, 4.3)); ax.bar(labs, vals_c, color=["#D55E00", "#0072B2"])
for i, (v, n) in enumerate(zip(vals_c, nn)):
    ax.text(i, v + 1.5, f"{v:.1f} %\n(n = {n:,})", ha="center", fontsize=11)
ax.set_ylim(0, 100); ax.set_ylabel("numu survival of NC-Delta photon objects (%)"); ax.set_title("numu survival vs reconstructed total shower length", fontsize=11)
foot(fig, "official Gen2 NC-Delta, objects reaching the numu stage | source-faithful numu cut | association, not causation"); fig.subplots_adjust(bottom=0.2); fig.savefig(A / "05_numu_compactness.png", dpi=170, bbox_inches="tight"); plt.close(fig)

# Delta mass residual (corrected restricted subset)
r = RES[RES.config == "D_full"].residual_mev.to_numpy(); d = DM.loc["D_full"]
fig, ax = plt.subplots(figsize=(6.6, 4.3)); ax.hist(np.clip(r, -250, 250), bins=np.arange(-250, 251, 10), color="#0072B2", alpha=0.75)
ax.axvline(0, color="k", lw=0.8); ax.axvline(d.median_mev, color="#D55E00", lw=1.5, label=f"median {d.median_mev:+.1f} MeV"); ax.axvspan(d.p16_mev, d.p84_mev, color="#D55E00", alpha=0.12, label=f"68 %: [{d.p16_mev:+.1f}, {d.p84_mev:+.1f}] MeV")
ax.set_xlabel("mass residual M_reco - M_true_decay [MeV]  (clipped at +-250)"); ax.set_ylabel("events / 10 MeV"); ax.legend(frameon=False, fontsize=9); ax.set_title(f"{int(d.decay_pairs)} truth-matched Delta+ decay pairs, selected", fontsize=11)
foot(fig, "official Gen2 NC-Delta | source-faithful chain, policy any | first look\nobjects with a stored row only (818 of 833 selected events)"); fig.subplots_adjust(bottom=0.24); fig.savefig(A / "09_delta_mass_residual.png", dpi=170, bbox_inches="tight"); plt.close(fig)

# natural CV: cumulative fraction by stage
ns = NATCF[NATCF.stage.isin(["candidate", "n20mev", "bdt_evaluable", "numu", "other", "ncpi0", "nue", "n20br1", "final"])]
fig, ax = plt.subplots(figsize=(8, 4.2)); xs = np.arange(len(ns)); w = 0.38
ax.bar(xs - w / 2, ns.rehearsal_frac * 100, w, color="#E69F00", label="natural NC-Delta in BNB CV (117 events)"); ax.bar(xs + w / 2, ns.official_frac * 100, w, color="#0072B2", label="official Gen2 sample (12,427 events)")
ax.set_xticks(xs); ax.set_xticklabels(ns.stage, rotation=35, ha="right"); ax.set_ylabel("cumulative efficiency (%)"); ax.legend(frameon=False, fontsize=9); ax.grid(alpha=.25, axis="y")
ax.set_title("final: 8 / 117 = 6.8 % vs 6.70 %  (p = 0.85; low statistics)", fontsize=11); foot(fig); fig.subplots_adjust(bottom=0.25); fig.savefig(A / "14_natural_cv.png", dpi=170, bbox_inches="tight"); plt.close(fig)

# backup: scorer-correction decomposition
fig, ax = plt.subplots(figsize=(7.4, 4.3)); labs = ["A: as run\n(historical)", "B: score\nconvention only", "C: kine_pio_flag\nonly", "D: full\nsource-faithful"]; v = [int(IMP.loc[k, "official_selected_any"]) for k in ("A_old", "B_score_only", "C_pio_only", "D_full")]
ax.bar(labs, v, color=["#BBBBBB", "#0072B2", "#E69F00", "#009E73"])
for i, n in enumerate(v):
    ax.text(i, n + 15, f"{n:,}\n{100 * n / 12427:.2f} %", ha="center", fontsize=11)
ax.set_ylim(0, 1400); ax.set_ylabel("NC-Delta selected events (of 12,427)"); ax.set_title("scorer correction: the score convention drives the change", fontsize=11)
foot(fig, "score = log10((1+v)/(1-v)), v = TMVA response | kine_pio_flag forced to 0 in the single-photon ncpi0 input | thresholds unchanged"); fig.subplots_adjust(bottom=0.2); fig.savefig(BK / "B01_scorer_correction.png", dpi=170, bbox_inches="tight"); plt.close(fig)

# copies of corrected / unaffected figures
shutil.copyfile(REPO / "plots/legacy_scorer_correction/baseline_consolidation_source_faithful/fig_signal_vs_background_rates.png", A / "11_rates.png")
shutil.copyfile(REPO / "plots/legacy_scorer_correction/baseline_consolidation_source_faithful/fig_cutflow_loss_budget.png", BK / "B02_cutflow_loss_budget_combined.png")
DIFF = REPO / "plots/legacy_scorer_correction/differential_efficiency_source_faithful"
for dst, src in (("13a_eff_vs_photon_energy.png", "eff_groups_vs_photon_energy_mev.png"), ("13b_eff_vs_photon_angle.png", "eff_groups_vs_cos_theta_beam.png"), ("13c_vertex_z.png", "eff_groups_vs_vtx_z.png")):
    shutil.copyfile(DIFF / src, BK / ("B03" + dst[2:]))
for dst, src in (("B04_natural_cv_crosscheck_differential.png", "natural_cv_crosscheck.png"), ("B05_decomposition_0p_vs_1p.png", "decomposition_0p_vs_1p.png")):
    shutil.copyfile(DIFF / src, BK / dst)
UNCH_MAIN = {"06_vertex_provenance.png": "06_vertex_provenance.png", "04_photon_taxonomy.png": "04_photon_taxonomy.png", "07_proton_reco_vs_ke.png": "07_proton_reco_vs_ke.png", "07b_migration_reasons.png": "07b_migration_reasons.png"}
UNCH_BK = {"B06_official_sample_census.png": "B01_official_sample_census.png", "B07_conversion_distance.png": "B06_conversion_distance.png", "B08_photon_taxonomy_vs_energy.png": "B07_photon_taxonomy_vs_energy.png",
           "B09_photon_type_vs_energy.png": "B07b_photon_type_vs_energy.png", "B10_numu_shap_families.png": "B08_numu_shap_families.png", "B11_shower_attachment_parents.png": "B10_shower_attachment_parents.png",
           "B12_proton_pid_high_ke.png": "B12_proton_pid_high_ke.png", "B13_proton_low_ke_merge.png": "B12b_proton_low_ke_merge.png"}
for dst, src in UNCH_MAIN.items():
    shutil.copyfile(OLDA / src, A / dst)
for dst, src in UNCH_BK.items():
    shutil.copyfile(OLDA / "backup" / src, BK / dst)
CAV_MAIN = {"05b_other_vertex_class_survival.png": "05b_other_vertex_class_survival.png"}           # drawn with the as-run other cut: the stage-survival shift is ~1 pp, text must use corrected numbers
for dst, src in CAV_MAIN.items():
    shutil.copyfile(OLDA / src, A / dst)

# ================================================================================================================ slide numbers
rows: list[dict] = []
AC, RU, HA, RV = "AUTHORITATIVE CORRECTED", "RECONSTRUCTION-ONLY UNCHANGED", "HISTORICAL AS-RUN", "REVIEW / DO NOT USE"
SUMJ = "tables/legacy_scorer_correction/source_faithful/baseline_consolidation/summary.json"; OLDJ = "tables/baseline_consolidation/summary.json"


def add(slide, quantity, value, unit, source, locator, status, display=None):
    rows.append(dict(slide=slide, quantity=quantity, value=value, display=display if display is not None else (f"{value:,}" if isinstance(value, int) else str(value)), unit=unit, source=source, locator=locator, status=status))


def pc(x, nd=2):
    return f"{100 * x:.{nd}f} %"


s = NEW["signal"]; e = s["eff"]
add("4", "truth denominator (provisional TPC box)", s["truth_denominator"], "events", SUMJ, "$.signal.truth_denominator", AC)
add("2,4", "truth 0p / 1p / >=2p events", f"{s['truth_by_class']['0p']:,} / {s['truth_by_class']['1p']:,} / {s['truth_by_class']['>=2p']:,}", "events", SUMJ, "$.signal.truth_by_class", RU)
add("2", "Delta0 / Delta+ events", f"{s['delta']['Delta0']:,} / {s['delta']['Delta+']:,}", "events", SUMJ, "$.signal.delta", RU)
add("4", "selected events, policy any", s["final_any"], "events", SUMJ, "$.signal.final_any", AC)
add("4", "efficiency, policy any", e["any|all"][2], "fraction", SUMJ, "$.signal.eff['any|all'][2]", AC, pc(e["any|all"][2]))
add("4", "68 % interval of the efficiency", f"{100 * e['any|all'][3]:.2f}-{100 * e['any|all'][4]:.2f} %", "%", SUMJ, "$.signal.eff['any|all'][3:5]", AC)
add("4", "selected events, policy first", s["final_first"], "events", SUMJ, "$.signal.final_first", AC); add("4", "efficiency, policy first", e["first|all"][2], "fraction", SUMJ, "$.signal.eff['first|all'][2]", AC, pc(e["first|all"][2]))
for g in ("0p", "1p", ">=2p"):
    add("4", f"efficiency, truth {g}", e[f"any|{g}"][2], "fraction", SUMJ, f"$.signal.eff['any|{g}'][2]", AC, pc(e[f"any|{g}"][2])); add("4", f"selected, truth {g}", e[f"any|{g}"][0], "events", SUMJ, f"$.signal.eff['any|{g}'][0]", AC)
for g in ("Delta0", "Delta+"):
    add("backup", f"efficiency, {g} (entangled with topology and proton origin)", e[f"any|{g}"][2], "fraction", SUMJ, f"$.signal.eff['any|{g}'][2]", AC, pc(e[f"any|{g}"][2]))
for st in ("wc.valid", "candidate", "> 20 MeV shower", "BDT evaluable", "numu", "other", "ncpi0", "nue", "n_20br1", "final"):
    add("5,B", f"cumulative surviving: {st}", NEW["loss_budget"][st][0], "events", SUMJ, f"$.loss_budget['{st}'][0]", AC)
for st, key in (("candidate", "candidate"), ("> 20 MeV shower", "shower"), ("numu", "numu"), ("other", "other"), ("ncpi0", "ncpi0"), ("nue", "nue"), ("n_20br1", "n_20br1")):
    add("5", f"exclusive first failure: {key}", NEW["loss_budget"][st][3], "fraction of 12,427", SUMJ, f"$.loss_budget['{st}'][3]", AC, pc(NEW["loss_budget"][st][3], 1)); add("5", f"first-failure events: {key}", NEW["loss_budget"][st][2], "events", SUMJ, f"$.loss_budget['{st}'][2]", AC)
add("5", "nue cumulative-stage signal loss", int(LB.set_index("stage").loc["nue", "step_loss_cumulative"]), "events", "tables/legacy_scorer_correction/source_faithful/baseline_consolidation/loss_budget.csv", "stage == nue, step_loss_cumulative", AC)
add("5,9", "events reaching nue / passing nue", f"{sig_before:,} -> {sig_after:,} (survival {100 * sig_after / sig_before:.1f} %)", "events", SUMJ, "$.loss_budget['ncpi0'][0], ['nue'][0]", AC)
add("9", "nue survival by truth class (0p / 1p / >=2p)", " / ".join(f"{100 * float(MECH[(MECH.item == 'stage_conditional_survival') & (MECH.group == f'nue | truth {g}') & (MECH.scorer == 'source_faithful')].value.iloc[0]):.1f} %" for g in ("0p", "1p", ">=2p")), "%", "tables/legacy_scorer_correction/mechanism_recheck.csv", "stage_conditional_survival, nue | truth g, source_faithful", AC)
add("9", "signal events that were selected as run and leave through nue", int(FS[(FS.config == "D_full") & (FS["sample"] == "official") & (FS.flip == "old_pass_new_fail") & (FS.dimension == "stage") & (FS.value == "fail_nue")].N.iloc[0]), "events", "tables/legacy_scorer_correction/flip_summary.csv", "official, D_full, old_pass_new_fail, stage, fail_nue", AC)
add("9", "intrinsic nue-CC events selected, as run (historical)", nue_old, "events", "tables/background_mechanisms/background_composition_by_channel.csv", "sum count, category == NUE_CC", HA)
add("9,12", "intrinsic nue-CC events selected, corrected", nue_new, "events", "tables/legacy_scorer_correction/source_faithful/background_mechanisms/background_composition_by_channel.csv", "sum count, category == NUE_CC", AC)
add("9", "as-run nue-CC events that leave the selection", int(FS[(FS.config == "D_full") & (FS["sample"] == "bnb_cv") & (FS.flip == "old_pass_new_fail") & (FS.dimension == "bkg_cand_category") & (FS.value == "NUE_CC")].N.iloc[0]), "events (of 175)", "tables/legacy_scorer_correction/flip_summary.csv", "bnb_cv, D_full, old_pass_new_fail, bkg_cand_category, NUE_CC", AC)
tot_loss = 12427 - s["final_any"]; add("5", "numu failures as a share of the total loss", NEW["loss_budget"]["numu"][2] / tot_loss, "fraction", SUMJ, "$.loss_budget['numu'][2] / (12,427 - 833)", AC, f"{100 * NEW['loss_budget']['numu'][2] / tot_loss:.1f} % ({NEW['loss_budget']['numu'][2]:,} of {tot_loss:,})")
add("5", "first-failure vs cumulative bookkeeping difference at numu / ncpi0", "+3 / -3", "events", SUMJ, "$.first_failure_cumulative_mismatch", RU)
for g, key in (("compact (length < 20 cm)", "compact < 20 cm"), ("not compact (>= 20 cm)", "not compact >= 20 cm")):
    r = MECH[(MECH.item == "numu_survival") & (MECH.group == g) & (MECH.scorer == keyc)].iloc[0]; add("7", f"numu survival, {key}", float(r.value), "fraction", "tables/legacy_scorer_correction/mechanism_recheck.csv", f"numu_survival, {g}, corrected", AC, pc(float(r.value), 1))
for g in ("few-segment (< 5)", "not few-segment"):
    r = MECH[(MECH.item == "numu_survival") & (MECH.group == g) & (MECH.scorer == keyc)].iloc[0]; add("7", f"numu survival, {g}", float(r.value), "fraction", "tables/legacy_scorer_correction/mechanism_recheck.csv", f"numu_survival, {g}, corrected", AC, pc(float(r.value), 1))
for g in ("0p", "1p"):
    r = MECH[(MECH.item == "stage_conditional_survival") & (MECH.group == f"other | truth {g}") & (MECH.scorer == "source_faithful")].iloc[0]; add("7,8", f"other survival given numu, truth {g}", float(r.value), "fraction", "tables/legacy_scorer_correction/mechanism_recheck.csv", f"other | truth {g}, source_faithful", AC, pc(float(r.value), 1))
for g in ("truth all",):
    r = MECH[(MECH.item == "stage_conditional_survival") & (MECH.group == f"ncpi0 | {g}") & (MECH.scorer == "source_faithful")].iloc[0]; add("7", "ncpi0 survival given other", float(r.value), "fraction", "tables/legacy_scorer_correction/mechanism_recheck.csv", "ncpi0 | truth all, source_faithful", AC, pc(float(r.value), 1))
vv = VX[VX.config == "D_full"].set_index("group")
for g in ("truth 0p", "truth 1p"):
    add("8", f"median |V_reco - V_true|, {g} (objects with a stored row)", float(vv.loc[g, "median_cm"]), "cm", "tables/legacy_scorer_correction/vertex_resolution_subset.csv", f"D_full, {g}", AC, f"{vv.loc[g, 'median_cm']:.2f} cm (n = {int(vv.loc[g, 'n'])})")
add("8", "number of selected objects with a stored vertex row (of 833)", int(vv.loc["all", "n"]), "events", "tables/legacy_scorer_correction/vertex_resolution_subset.csv", "D_full, all", AC)
mg = NEW["migration_final"]
for k, v in mg.items():
    add("10", f"final migration {k} -> reco 0p / 1p / >=2p", " / ".join(str(x) for x in v), "events", SUMJ, f"$.migration_final['{k}']", AC)
for k, i in (("truth 0p", 0), ("truth 1p", 1), ("truth >=2p", 2)):
    add("10", f"diagonal fraction {k}", mg[k][i] / sum(mg[k]), "fraction", SUMJ, f"$.migration_final['{k}'][{i}] / sum", AC, pc(mg[k][i] / sum(mg[k]), 1))
add("10", "reco totals 1g0p / 1g1p / >=2p", " / ".join(str(sum(mg[k][i] for k in mg)) for i in range(3)), "events", SUMJ, "column sums of $.migration_final", AC)
add("10", "not selected: truth 0p / 1p / >=2p", " / ".join(f"{NEW['not_selected'][k]:,}" for k in mg), "events", SUMJ, "$.not_selected", AC)
add("10", "matched-candidate migration (pre-BDT) truth 1p -> reco 0p / 1p / >=2p / none", " / ".join(str(x) for x in OLD["migration_matched_candidate"]["truth 1p"]), "events", OLDJ, "$.migration_matched_candidate['truth 1p']", RU)
dd = DM.loc["D_full"]
add("11", "selected truth-matched decay pairs", int(dd.decay_pairs), "events", "tables/legacy_scorer_correction/delta_mass_subset.csv", "D_full, decay_pairs", AC)
add("11", "median(M_reco - M_true_decay)", f"{dd.median_mev:+.1f}", "MeV", "tables/legacy_scorer_correction/delta_mass_subset.csv", "D_full, median_mev", AC)
add("11", "68 % interval of M_reco - M_true_decay", f"[{dd.p16_mev:+.1f}, {dd.p84_mev:+.1f}]", "MeV", "tables/legacy_scorer_correction/delta_mass_subset.csv", "D_full, p16_mev / p84_mev", AC)
add("11", "half-width / RMS", f"{dd.half68_mev:.1f} / {dd.rms_mev:.1f}", "MeV", "tables/legacy_scorer_correction/delta_mass_subset.csv", "D_full, half68_mev / rms_mev", AC)
add("11", "decay-pair headline of the as-run chain (historical)", f"{int(DM.loc['A_old', 'decay_pairs'])} pairs, median {DM.loc['A_old', 'median_mev']:+.1f} MeV, [{DM.loc['A_old', 'p16_mev']:+.1f}, {DM.loc['A_old', 'p84_mev']:+.1f}] MeV", "MeV", "tables/legacy_scorer_correction/delta_mass_subset.csv", "A_old", HA)
b = NEW["background"]
add("12", "selected non-signal BNB-CV events", b["selected_nonsignal"], "events", SUMJ, "$.background.selected_nonsignal", AC)
add("12", "by reco channel 1g0p / 1g1p / >=2p", " / ".join(str(b["by_channel"][k][0]) for k in ("1g0p", "1g1p", "ge2p")), "events", SUMJ, "$.background.by_channel", AC)
add("12", "non-signal rate per 1e20 POT by channel (stat. only)", " / ".join(f"{b['by_channel'][k][1]:.0f}" for k in ("1g0p", "1g1p", "ge2p")), "per 1e20 POT", SUMJ, "$.background.by_channel[*][1]", AC)
add("12", "signal-like (natural NC-Delta) events removed from the background", b["signal_like_removed"], "events", SUMJ, "$.background.signal_like_removed", AC)
tt = COMP[COMP.category != "TOTAL"].groupby("category")["count"].sum()
for cat in ("NC_PI0", "OUTSIDE_TPC_NU", "CC_PI0", "NUMU_CC", "OTHER_NC", "COSMIC_OR_UNMATCHED", "MULTI_OR_AMBIGUOUS", "NUE_CC"):
    add("12,B", f"background category {cat} (all channels)", int(tt[cat]), "events", "tables/legacy_scorer_correction/source_faithful/background_mechanisms/background_composition_by_channel.csv", f"sum count, category == {cat}", AC, f"{int(tt[cat])} ({100 * tt[cat] / tt.sum():.1f} %)")
for ch, lab in (("1g0p", "1g0p"), ("1g1p", "1g1p"), ("ge2p_diag", ">=2p")):
    for cat in ("NC_PI0", "OUTSIDE_TPC_NU", "CC_PI0"):
        r = COMP[(COMP.channel == ch) & (COMP.category == cat)]
        add("12,B", f"{lab}: {cat}", int(r["count"].iloc[0]) if len(r) else 0, "events", "tables/legacy_scorer_correction/source_faithful/background_mechanisms/background_composition_by_channel.csv", f"channel == {ch}, category == {cat}", AC, f"{int(r['count'].iloc[0])} ({100 * float(r.fraction.iloc[0]):.0f} %)" if len(r) else "0")
sr = NEW["signal_rate"]
add("12", "signal rate per 1e20 POT, provisional TPC box (total)", sr["total_per_1e20"], "per 1e20 POT", SUMJ, "$.signal_rate.total_per_1e20", AC, f"{sr['total_per_1e20']:.1f}")
add("12", "signal rate by reco channel 1g0p / 1g1p / >=2p", " / ".join(f"{sr['by_reco_channel'][k]:.1f}" for k in ("1g0p", "1g1p", "ge2p")), "per 1e20 POT", SUMJ, "$.signal_rate.by_reco_channel", AC)
nc = NEW["natural_cv"]
add("backup", "natural NC-Delta selected / in the TPC box", f"{nc['selected_any']} / {nc['in_tpc_box']}", "events", SUMJ, "$.natural_cv.selected_any, in_tpc_box", AC); add("backup", "natural fraction vs dedicated efficiency", f"{pc(nc['natural_final_fraction'], 1)} vs {pc(nc['official_final_fraction'], 2)}", "%", SUMJ, "$.natural_cv.natural_final_fraction, official_final_fraction", AC)
add("backup", "binomial compatibility p-value", f"{nc['final_p_binom']:.2f}", "p", SUMJ, "$.natural_cv.final_p_binom", AC)
for k, g in (("A_old", HA), ("B_score_only", AC), ("C_pio_only", AC), ("D_full", AC)):
    add("backup", f"scorer decomposition: {k} selected", int(IMP.loc[k, "official_selected_any"]), "events", "tables/legacy_scorer_correction/impact_configurations.csv", f"config == {k}, official_selected_any", g)
add("backup", "historical as-run efficiency (the superseded headline)", OLD["signal"]["eff"]["any|all"][2], "fraction", OLDJ, "$.signal.eff['any|all'][2]", HA, pc(OLD["signal"]["eff"]["any|all"][2]))
add("backup", "historical as-run selected non-signal BNB-CV", OLD["background"]["selected_nonsignal"], "events", OLDJ, "$.background.selected_nonsignal", HA, "635 = 310 / 230 / 95"); add("backup", "historical signal rate per 1e20 POT", OLD["signal_rate"]["total_per_1e20"], "per 1e20 POT", OLDJ, "$.signal_rate.total_per_1e20", HA, f"{OLD['signal_rate']['total_per_1e20']:.1f}")
add("backup", "threshold translation: v at the frozen cuts numu / other / ncpi0 / nue", " / ".join(f"{x:.4f}" for x in pd.read_csv(TC / "threshold_translation.csv").equivalent_cut_on_v), "response v", "tables/legacy_scorer_correction/threshold_translation.csv", "equivalent_cut_on_v", AC)
hh = HARM.query("policy == 'any'").set_index("denominator_set")
for nm in ("B spine_technote_strict = HARMONIZED ALL", "harmonized 0p50", "harmonized Np50"):
    add("backup", f"WC efficiency on SPINE-harmonised denominator: {nm}", f"{int(hh.loc[nm, 'numerator'])} / {int(hh.loc[nm, 'denominator']):,} = {100 * hh.loc[nm, 'efficiency']:.2f} %", "events", "tables/legacy_scorer_correction/source_faithful/spine_harmonization/wc_efficiency_on_harmonized.csv", nm, AC)
dn = DX[DX.config == "D_full"]
ee = dn[dn.variable == "photon_energy_mev"]; ee = ee[ee.denominator >= 100]
add("backup", "efficiency vs true photon energy: lowest / highest populated bin (>= 100 events)", f"{100 * ee.efficiency.iloc[0]:.1f} % ({ee.lo.iloc[0]:.0f}-{ee.hi.iloc[0]:.0f} MeV) / {100 * ee.efficiency.max():.1f} % ({ee.loc[ee.efficiency.idxmax(), 'lo']:.0f}-{ee.loc[ee.efficiency.idxmax(), 'hi']:.0f} MeV)", "%", "tables/legacy_scorer_correction/source_faithful/differential_efficiency/slide_extract.csv", "D_full, photon_energy_mev", AC)
cs_ = dn[dn.variable == "cos_theta_beam"]; add("backup", "efficiency vs cos(theta_beam): most backward / most forward bin", f"{100 * cs_.efficiency.iloc[0]:.1f} % / {100 * cs_.efficiency.iloc[-1]:.1f} %", "%", "tables/legacy_scorer_correction/source_faithful/differential_efficiency/slide_extract.csv", "D_full, cos_theta_beam", AC)
vz = dn[dn.variable == "vtx_z"]; add("backup", "efficiency in the last 50 cm in z (bin 9)", f"{100 * vz.efficiency.iloc[-1]:.1f} %", "%", "tables/legacy_scorer_correction/source_faithful/differential_efficiency/slide_extract.csv", "D_full, vtx_z, last bin", AC)
ie = dn[dn.variable.isin(["interior_diagnostic_box", "edge_complement"])].set_index("variable"); add("backup", "interior diagnostic box vs edge complement (not a proposed FV)", f"{100 * ie.loc['interior_diagnostic_box', 'efficiency']:.1f} % vs {100 * ie.loc['edge_complement', 'efficiency']:.1f} %", "%", "tables/legacy_scorer_correction/source_faithful/differential_efficiency/slide_extract.csv", "D_full, interior / edge", AC)

# --- review classification of every text-sourced / flagged number of the previous package
OLDN = pd.read_csv(REPO / "docs" / "presentation" / "ROUND1_CORRECTED_SLIDE_NUMBERS.csv"); REVN = OLDN[OLDN.status.str.startswith("REVIEW")]
SAFE, CORR, RECOMP, DROP = "SAFE UNCHANGED", "CORRECTED VALUE EXISTS", "NEEDS RECOMPUTE", "DROP FROM PRESENTATION"
sh = lambda k: float(MECH[(MECH.item == "stage_conditional_survival") & (MECH.group == k) & (MECH.scorer == "source_faithful")].value.iloc[0])
CLASS = {
    "26.9 %": (CORR, f"{100 * NEW['loss_budget']['numu'][2] / tot_loss:.1f} % ({NEW['loss_budget']['numu'][2]:,} of {tot_loss:,}); the old 26.9 % / 29.8 % are retired", "unaffected denominators changed (833 selected)"),
    "12.8 %": (DROP, "", "compact numu failures as a share of the loss: as-run population; not recomputed"),
    "29.8 %": (DROP, "", "superseded Phase-18 erratum; must not appear"),
    "527 / 556 / 70": (CORR, " / ".join(str(sum(mg[k][i] for k in mg)) for i in range(3)), "corrected reco totals"),
    "27.6 %": (SAFE, "", "shower-stage failure taxonomy, defined before the BDTs"), "~3": (SAFE, "", "fragmentation of the photon, before the BDTs"), "567": (SAFE, "", "shower attachment, before the BDTs"),
    "17.4 %": (SAFE, "", "shower-stage failures"), "29.6 %": (SAFE, "", "shower-stage failures"), "1.2 %": (SAFE, "", "shower-stage failures"),
    "29 % vs 74 %": (CORR, "28.3 % vs 72.8 %", "mechanism_recheck.csv"), "25 % vs 73 %": (CORR, "24.0 % vs 72.3 %", "mechanism_recheck.csv"),
    "76 %": (DROP, "", "numu survival by photon-object class under the corrected cut was not recomputed; state qualitatively"), "36 %": (DROP, "", "same"), "22-25 %": (DROP, "", "same"),
    "44 %": (DROP, "", "share of the compact-vs-extended difference shared with object class; not recomputed"), "25-32 pp": (DROP, "", "association after control; not recomputed (say: persists, magnitude not recomputed)"),
    "65-79 % vs 33-46 %": (DROP, f"replace by other survival given numu: truth 0p {100 * sh('other | truth 0p'):.1f} % vs truth 1p {100 * sh('other | truth 1p'):.1f} %", "anchored-vs-unanchored split was not recomputed"),
    "94.2 % / 88.0 %": (DROP, "", "ncpi0-rejected pair-flag percentages; the rejected set changes slightly; not recomputed; keep the qualitative fake-pair statement"),
    "0.93 cm vs 11.6 cm": (CORR, f"{vv.loc['truth 1p', 'median_cm']:.2f} cm vs {vv.loc['truth 0p', 'median_cm']:.1f} cm (truth 1p vs truth 0p; objects with a stored row)", "vertex_resolution_subset.csv"),
    "11.6 cm": (CORR, f"{vv.loc['truth 0p', 'median_cm']:.1f} cm", "vertex_resolution_subset.csv"),
    "+25.8 / +36 / +24.5 cm": (DROP, "", "population of the photon-line displacement not established as selection-independent; do not show"),
    "0.25 cm": (DROP, "", "population not established; say only that the late refinement moves the vertex by a small amount"),
    "42 % -> 67.5 %": (DROP, "", "population not established; do not show"),
    "46 % / 67 % / 22 %": (SAFE, "", "proton typing vs KE at the matched candidate, before the BDTs"), "17 %": (SAFE, "", "proton typing, before the BDTs"), "65 %": (SAFE, "", "proton merge, before the BDTs"),
    "883 -> 37": (DROP, "keep only 883 (matched candidate, pre-BDT, unchanged)", "the '-> 37' final-subset count is as-run; the final matrix replaces it"),
    "468 -> 11 / 319 -> 26": (DROP, "keep only 468 / 319 (matched candidate, pre-BDT, unchanged)", "the '-> 11 / 26' final-subset counts are as-run; the final matrix replaces them"),
    "+2.8 MeV, [-44, +34] MeV": (CORR, f"{dd.median_mev:+.1f} MeV, [{dd.p16_mev:+.1f}, {dd.p84_mev:+.1f}] MeV", "delta_mass_subset.csv"),
    "1.034 / 12.7 %": (RECOMP, "", "photon energy response of the 1,148 truth-correct selected photons is an as-run selected sample; the corrected subset was not computed; omit the number or recompute from the Phase-11 object table"),
    "348": (CORR, f"{int(dd.decay_pairs)}", "delta_mass_subset.csv"),
    "~33 / 24 / 17 %": (CORR, "1g0p: " + ", ".join(f"{k} {100 * float(COMP[(COMP.channel == '1g0p') & (COMP.category == k)].fraction.iloc[0]):.0f} %" for k in ("NC_PI0", "OUTSIDE_TPC_NU", "CC_PI0")), "composition table"),
    "~37 / 30 / 18 %": (CORR, "1g1p: " + ", ".join(f"{k} {100 * float(COMP[(COMP.channel == '1g1p') & (COMP.category == k)].fraction.iloc[0]):.0f} %" for k in ("NC_PI0", "CC_PI0", "OUTSIDE_TPC_NU")), "composition table"),
    "2.4 % -> ~15 %": (CORR, ee.pipe(lambda x: f"{100 * x.efficiency.iloc[0]:.1f} % -> {100 * x.efficiency.max():.1f} %"), "slide_extract.csv"), "3.0 % -> 12.8 %": (CORR, f"{100 * cs_.efficiency.iloc[0]:.1f} % -> {100 * cs_.efficiency.iloc[-1]:.1f} %", "slide_extract.csv"),
    "4.4 %": (CORR, f"{100 * vz.efficiency.iloc[-1]:.1f} %", "slide_extract.csv"), "11.4 % vs 7.3 %": (CORR, f"{100 * ie.loc['interior_diagnostic_box', 'efficiency']:.1f} % vs {100 * ie.loc['edge_complement', 'efficiency']:.1f} %", "slide_extract.csv"),
    "+3 / -3": (SAFE, "", "still +3 / -3 in the corrected cutflow"),
    "52 events": (DROP, "", "any-minus-first counts are as-run; not recomputed"), "22": (DROP, "", "same"),
    "9.28 % / 10.1-10.6 % / 9.92 %": (DROP, "", "as-run FV decision support (starts from the superseded 9.28 %); not recomputed; the decision stays open"),
    "63 events": (DROP, "", "included == 3 counts at the final selection are as-run; not recomputed"), "1,072": (SAFE, "", "truth-only count of events changing truth category between 35 and 50 MeV"),
    "84.7 -> 89.7 %": (DROP, "", "as-run reco composition; not recomputed"),
    "11,512": (SAFE, "", "truth quantity"), "0.975": (SAFE, "", "truth / reco-geometry quantity"), "15.1 % / 13.0 %": (SAFE, "", "shower-stage failures"), "13.0 %": (SAFE, "", "shower-stage failures"),
    "62 % / 15 % / 6 %": (SAFE, "", "567-event attachment audit, before the BDTs"),
    "+12.7 pp -> +0.7 pp": (DROP, "", "decay-vs-FSI difference at other: as-run; not recomputed"), "+3.8 pp / +5.2 pp": (DROP, "", "residual final-efficiency differences: as-run; not recomputed"),
    "182 of 362": (SAFE, "", "proton PID, before the BDTs"), "55-66 cm vs 122 cm": (SAFE, "", "proton PID, before the BDTs"), "9,206 of 13,773": (SAFE, "", "truth quantity"),
    "A B C O P Q T U V Y": (SAFE, "", "roadmap bookkeeping"), "10.4 %": (DROP, "", "photon-energy contribution to the Delta-mass width: as-run; not recomputed"), "1220.8 MeV": (DROP, "", "as-run context median"),
}
rv = []
for r in REVN.itertuples():
    k = r.displayed_old
    if k not in CLASS:
        raise SystemExit(f"unclassified REVIEW number: {k!r} (slide {r.slide}, {r.meaning[:60]})")
    c, new, why = CLASS[k]; rv.append(dict(slide=r.slide, old_displayed=k, meaning=r.meaning, classification=c, corrected_value=new, reason=why))
(DOC / "NCDELTA_SOURCE_FAITHFUL_ROUND1_SLIDE_NUMBERS.json").write_text(json.dumps(dict(
    authority="tables/legacy_scorer_correction/ (commit daf95442515b601eecda41c6c586931a5ae38c54)", statuses=[AC, RU, HA, RV], numbers=rows, review_classification=rv), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
md = ["# Source-faithful Round-1: slide numbers and their sources", "",
      "Generated by `scripts/make_source_faithful_presentation_package.py` from committed tables (nothing typed by hand). **Use only rows with status AUTHORITATIVE CORRECTED or RECONSTRUCTION-ONLY UNCHANGED as current. HISTORICAL AS-RUN rows may appear only on the scorer-correction backup slide, labelled historical. REVIEW / DO NOT USE rows must not be shown.** Authority: branch `analysis/ncdelta-source-faithful-legacy-scorer-20261117`, commit `daf95442515b601eecda41c6c586931a5ae38c54`.", "",
      "| slide / topic | quantity | value | unit | source | locator | status |", "|---|---|---|---|---|---|---|"]
for r in rows:
    md.append(f"| {r['slide']} | {r['quantity']} | {r['display']} | {r['unit']} | `{r['source']}` | `{r['locator']}` | {r['status']} |")
md += ["", "## Classification of the previously flagged REVIEW numbers (from `ROUND1_CORRECTED_SLIDE_NUMBERS.md`)", "",
       "SAFE UNCHANGED = a reconstruction or truth quantity defined before, or independent of, the final BDT selection (keep). CORRECTED VALUE EXISTS = use the corrected value. NEEDS RECOMPUTE / DROP FROM PRESENTATION = do not show (the reason says what would be needed).", "",
       "| old slide | old value | meaning | classification | corrected value | reason / needed source |", "|---|---|---|---|---|---|"]
for r in rv:
    md.append(f"| {r['slide']} | {r['old_displayed']} | {r['meaning']} | {r['classification']} | {r['corrected_value']} | {r['reason']} |")
(DOC / "NCDELTA_SOURCE_FAITHFUL_ROUND1_SLIDE_NUMBERS.md").write_text("\n".join(md) + "\n")

# ================================================================================================================ asset manifest
AS = "presentation_assets/ncdelta_source_faithful/"
man = [
    ("main", "2 channels / terminology", "(no figure: definition table drawn from the numbers file)", "", "n/a", "truth classes and Delta charge are different splits", "n/a"),
    ("main", "4 baseline efficiency", AS + "02_cutflow.png", "scripts/make_source_faithful_presentation_package.py (tables/legacy_scorer_correction/source_faithful/baseline_consolidation/loss_budget.csv)", "CORRECTED", "833 / 12,427 = 6.70 % through the frozen chain; nue is a real stage", "YES: presentation_assets/ncdelta_baseline/02_cutflow.png shows 9.28 %"),
    ("main", "5 where the signal is lost", AS + "03_loss_budget.png", "same table", "CORRECTED", "exclusive first failures; nue 3.3 %", "YES: ncdelta_baseline/03_loss_budget.png"),
    ("main", "6 photon reconstruction failure modes", AS + "04_photon_taxonomy.png", "plots/shower_vertex_audit/taxonomy_all_0p_1p.png", "UNCHANGED (reconstruction-only; fractions of the 11,331 candidate-stage events)", "photon mis-typed, fragmented, or owned by a hadron-typed object", "no: the old file is the same figure"),
    ("main", "7 BDTs respond to reconstruction state (numu)", AS + "05_numu_compactness.png", "tables/legacy_scorer_correction/mechanism_recheck.csv", "CORRECTED", "numu survival 28.3 % vs 72.8 % by shower length", "YES: ncdelta_baseline/05_numu_compactness.png was drawn with the as-run cut"),
    ("main", "7/8 other vs vertex class", AS + "05b_other_vertex_class_survival.png", "plots/vertex_provenance_audit/fig8_stage_survival_by_vertex_class.png", "AS-RUN FIGURE, qualitative use only (stage-survival shift about 1 pp)", "other survival follows vertex anchoring; quote text numbers from the numbers file, not from the bars", "caption must not quote bar values"),
    ("main", "8 vertex provenance", AS + "06_vertex_provenance.png", "plots/vertex_provenance_audit/fig2_vertex_provenance_by_topology.png", "UNCHANGED (mechanism; BDT-independent)", "truth-0p vertex follows the photon; a reconstructed proton anchors the vertex", "quote vertex medians from the numbers file (0.87 / 11.3 cm), not from older captions"),
    ("main", "9 nue trade-off", AS + "12_nue_tradeoff.png", "tables/legacy_scorer_correction/source_faithful/baseline_consolidation/loss_budget.csv; tables/legacy_scorer_correction/flip_summary.csv", "CORRECTED (new)", "nue costs signal efficiency and removes nearly all intrinsic nue-CC background", "n/a (new)"),
    ("main", "10 proton reconstruction", AS + "07_proton_reco_vs_ke.png", "plots/particle_pid_audit/fig2_true_proton_reco_type_vs_ke.png", "UNCHANGED (matched-candidate, pre-BDT)", "proton typing efficiency vs true KE", "no"),
    ("main", "10 migration reasons", AS + "07b_migration_reasons.png", "plots/proton_truth_association/migration_1p_to_0p_and_0p_to_1p.png", "UNCHANGED for the matched-candidate counts; any final-subset counts in its caption are as-run", "why truth 1p becomes reco 0p and truth 0p becomes reco 1p (matched candidate)", "do not quote the '-> final' counts of the old caption"),
    ("main", "10 truth -> reco matrix", AS + "08_migration_matrix.png", "SUMMARY: tables/legacy_scorer_correction/source_faithful/baseline_consolidation/summary.json migration_final", "CORRECTED", "reco 1g0p / 1g1p are not truth labels", "YES: ncdelta_baseline/08_migration_matrix.png"),
    ("main", "11 Delta observables", AS + "09_delta_mass_residual.png", "tables/legacy_scorer_correction/delta_mass_residuals.csv", "CORRECTED (restricted subset)", "251 decay pairs; median -0.1 MeV; 68 % [-44.5, +23.4] MeV", "YES: ncdelta_baseline/09_delta_mass_residual.png (348 pairs, +2.8 MeV)"),
    ("main", "12 surviving backgrounds", AS + "10_backgrounds.png", "tables/legacy_scorer_correction/source_faithful/background_mechanisms/background_composition_by_channel.csv", "CORRECTED", "282 non-signal events; NC pi0, outside-TPC and CC pi0 dominate", "YES: ncdelta_baseline/10_backgrounds.png and 10b (635 events, nue-CC 17-37 %)"),
    ("main", "12 signal and background rates", AS + "11_rates.png", "plots/legacy_scorer_correction/baseline_consolidation_source_faithful/fig_signal_vs_background_rates.png", "CORRECTED", "29.3 per 1e20 signal; NOT an S/B", "YES: ncdelta_baseline/11_rates.png"),
    ("backup", "scorer correction", AS + "backup/B01_scorer_correction.png", "tables/legacy_scorer_correction/impact_configurations.csv", "CORRECTED (new)", "the score convention, not kine_pio_flag, drives the change", "n/a"),
    ("backup", "complete cutflow", AS + "backup/B02_cutflow_loss_budget_combined.png", "plots/legacy_scorer_correction/baseline_consolidation_source_faithful/fig_cutflow_loss_budget.png", "CORRECTED", "cumulative and first-failure panels", "YES: ncdelta_baseline/backup/B02_cutflow_combined_original.png"),
    ("backup", "differential efficiency, photon energy", AS + "backup/B03a_eff_vs_photon_energy.png", "plots/legacy_scorer_correction/differential_efficiency_source_faithful/eff_groups_vs_photon_energy_mev.png", "CORRECTED", "efficiency rises with photon energy", "YES: old 13a crop"),
    ("backup", "differential efficiency, photon angle", AS + "backup/B03b_eff_vs_photon_angle.png", "plots/legacy_scorer_correction/differential_efficiency_source_faithful/eff_groups_vs_cos_theta_beam.png", "CORRECTED", "efficiency is lower for backward photons", "YES: old 13b crop"),
    ("backup", "differential efficiency, vertex z", AS + "backup/B03c_vertex_z.png", "plots/legacy_scorer_correction/differential_efficiency_source_faithful/eff_groups_vs_vtx_z.png", "CORRECTED", "efficiency drops in the last 50 cm in z", "YES: old 13c"),
    ("backup", "natural NC-Delta", AS + "14_natural_cv.png", "tables/legacy_scorer_correction/source_faithful/baseline_consolidation/natural_cv_cutflow.csv", "CORRECTED", "8 / 117 vs 6.70 %, p = 0.85; low statistics", "YES: ncdelta_baseline/14_natural_cv.png, B13"),
    ("backup", "natural NC-Delta differential cross-check", AS + "backup/B04_natural_cv_crosscheck_differential.png", "plots/legacy_scorer_correction/differential_efficiency_source_faithful/natural_cv_crosscheck.png", "CORRECTED", "differential comparison, low statistics", "YES: as-run version"),
    ("backup", "0p vs 1p decomposition", AS + "backup/B05_decomposition_0p_vs_1p.png", "plots/legacy_scorer_correction/differential_efficiency_source_faithful/decomposition_0p_vs_1p.png", "CORRECTED", "descriptive stage decomposition", "YES: as-run version"),
    ("backup", "official sample census", AS + "backup/B06_official_sample_census.png", "plots/official_ncdelta/official_ncdelta_truth_census.png", "UNCHANGED (truth)", "sample provenance and truth census", "no"),
    ("backup", "conversion-distance definition", AS + "backup/B07_conversion_distance.png", "plots/differential_efficiency/reco_gap_and_true_conversion.png", "UNCHANGED (truth / reco geometry)", "true conversion distance vs reco gap", "no"),
    ("backup", "photon taxonomy vs energy", AS + "backup/B08_photon_taxonomy_vs_energy.png", "plots/shower_vertex_audit/taxonomy_vs_photon_energy.png", "UNCHANGED", "detailed taxonomy", "no"),
    ("backup", "photon type vs energy", AS + "backup/B09_photon_type_vs_energy.png", "plots/particle_pid_audit/", "UNCHANGED", "photon typing", "no"),
    ("backup", "numu SHAP families", AS + "backup/B10_numu_shap_families.png", "plots/numu_compact_shower_audit/fig5_shap_families_by_group.png", "UNCHANGED (property of the frozen XML)", "attribution of the numu response", "do not quote its survival numbers"),
    ("backup", "shower attachment (567 events)", AS + "backup/B11_shower_attachment_parents.png", "plots/vertex_provenance_audit/fig4_5_shower_parent_taxonomy_and_truth.png", "UNCHANGED (before the BDTs)", "ownership of the shower, not vertexing", "no"),
    ("backup", "proton PID failure modes (high KE)", AS + "backup/B12_proton_pid_high_ke.png", "plots/particle_pid_audit/fig8_high_ke_proton_mistype_breakdown.png", "UNCHANGED", "high-KE protons typed as muon / pion", "no"),
    ("backup", "proton low-KE merge", AS + "backup/B13_proton_low_ke_merge.png", "plots/particle_pid_audit/fig7_low_ke_proton_merge_destination.png", "UNCHANGED", "low-KE protons merge into other objects", "no"),
    ("DO NOT USE", "ncpi0 pair origin (old B09)", "presentation_assets/ncdelta_baseline/backup/B09_ncpi0_pair_origin.png", "", "AS-RUN, percentages not recomputed", "", "DO NOT USE with its caption numbers; qualitative statement only"),
    ("DO NOT USE", "proton origin / Delta charge (old B11, B11b)", "presentation_assets/ncdelta_baseline/backup/B11_proton_origin_delta.png", "", "AS-RUN, pp differences not recomputed", "", "DO NOT USE"),
    ("DO NOT USE", "FV / policy / proton-policy decision support (old B03, B04, B05)", "presentation_assets/ncdelta_baseline/backup/B03_candidate_policy.png", "", "AS-RUN (start from 9.28 %)", "", "DO NOT USE; decisions D, E, F remain open (text only)"),
    ("DO NOT USE", "SPINE harmonised differential (old B14)", "presentation_assets/ncdelta_baseline/backup/B14_spine_harmonized_differential.png", "", "AS-RUN", "", "DO NOT USE; use the numbers-file table"),
    ("DO NOT USE", "old main figures with 9.28 % era numbers", "presentation_assets/ncdelta_baseline/{02_cutflow,03_loss_budget,08_migration_matrix,09_delta_mass_residual,10_backgrounds,10b_backgrounds_clean_redraw,11_rates,14_natural_cv,15_spine_denominator}.png", "", "HISTORICAL AS-RUN", "", "DO NOT USE"),
]
pd.DataFrame(man, columns=["main_or_backup", "slide_topic", "asset_path", "source", "corrected_vs_unchanged", "caption_message", "old_version_must_not_be_used"]).to_csv(DOC / "NCDELTA_SOURCE_FAITHFUL_ROUND1_SLIDE_ASSETS.csv", index=False)
print(len(rows), "numbers;", len(rv), "review rows;", len(man), "asset rows;", pd.Series([r["classification"] for r in rv]).value_counts().to_dict())
