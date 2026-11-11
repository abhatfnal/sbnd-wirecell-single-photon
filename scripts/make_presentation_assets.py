#!/usr/bin/env python
"""Presentation prep (no analysis): assemble presentation_assets/ncdelta_baseline/ and docs/presentation/NCDELTA_BASELINE_SLIDE_NUMBERS.md.

    python scripts/make_presentation_assets.py

* Originals under plots/ are never modified; selected figures are COPIED (1.5 MB in total, so no fragile symlinks).
* Four slide-ready redraws / crops are produced ONLY from committed tables / figures (cutflow and first-failure panels, truth->reco migration heat-map, clean background composition; PIL crops of existing figures).
* The slide-number table is generated from tables/baseline_consolidation/summary.json so that no number is typed by hand where the JSON has it.  Numbers that live only in the consolidated baseline text carry the text
  token that must occur in the cited document (checked by tests/test_presentation_package.py).
"""
from __future__ import annotations
import json, shutil, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src"))
import numpy as np, pandas as pd
from PIL import Image
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

P = REPO / "plots"; A = REPO / "presentation_assets" / "ncdelta_baseline"; BK = A / "backup"; DOC = REPO / "docs" / "presentation"
for d in (A, BK, DOC):
    d.mkdir(parents=True, exist_ok=True)
S = json.load(open(REPO / "tables" / "baseline_consolidation" / "summary.json")); LB = pd.read_csv(REPO / "tables" / "baseline_consolidation" / "loss_budget.csv")
COMP = pd.read_csv(REPO / "tables" / "baseline_consolidation" / "bnb_background_composition_by_channel.csv")
FOOT = "official Gen2 NC-Delta | frozen Wire-Cell baseline, policy any | provisional TPC truth box | FIRST LOOK, not a final result"

# ---------------------------------------------------------------------------------------------------------- copies
MAIN = {"04_photon_taxonomy.png": "shower_vertex_audit/taxonomy_all_0p_1p.png", "05_numu_compactness.png": "numu_compact_shower_audit/fig1_survival_vs_segments_length.png",
        "05b_other_vertex_class_survival.png": "vertex_provenance_audit/fig8_stage_survival_by_vertex_class.png", "06_vertex_provenance.png": "vertex_provenance_audit/fig2_vertex_provenance_by_topology.png",
        "07_proton_reco_vs_ke.png": "particle_pid_audit/fig2_true_proton_reco_type_vs_ke.png", "07b_migration_reasons.png": "proton_truth_association/migration_1p_to_0p_and_0p_to_1p.png",
        "10_backgrounds.png": "background_mechanisms/background_composition_by_channel.png", "11_rates.png": "baseline_consolidation/fig_signal_vs_background_rates.png",
        "13c_vertex_z.png": "differential_efficiency/eff_groups_vs_vtx_z.png", "14_natural_cv.png": "natural_ncdelta/natural_vs_dedicated.png", "15_spine_denominator.png": "spine_harmonization/denominator_definition_effect.png"}
BACKUP = {"B01_official_sample_census.png": "official_ncdelta/official_ncdelta_truth_census.png", "B02_cutflow_combined_original.png": "baseline_consolidation/fig_cutflow_loss_budget.png", "B03_candidate_policy.png": "analysis_definition_decisions/candidate_policy.png",
          "B04_fv_comparison.png": "analysis_definition_decisions/fv_comparison.png", "B04b_fv_edge_stability.png": "analysis_definition_decisions/fv_edge_stability.png", "B05_proton_policy.png": "analysis_definition_decisions/proton_policy_comparison.png",
          "B06_conversion_distance.png": "differential_efficiency/reco_gap_and_true_conversion.png", "B07_photon_taxonomy_vs_energy.png": "shower_vertex_audit/taxonomy_vs_photon_energy.png", "B07b_photon_type_vs_energy.png": "particle_pid_audit/fig1_true_photon_reco_type_vs_energy.png",
          "B08_numu_shap_families.png": "numu_compact_shower_audit/fig5_shap_families_by_group.png", "B08b_numu_survival_vs_energy_by_compactness.png": "numu_compact_shower_audit/fig3_survival_vs_energy_by_compactness.png",
          "B09_ncpi0_pair_origin.png": "pi0_pair_fragmentation_audit/fig5_ncpi0_survival_by_pair_origin.png", "B10_shower_attachment_parents.png": "vertex_provenance_audit/fig4_5_shower_parent_taxonomy_and_truth.png",
          "B11_proton_origin_delta.png": "proton_origin_survival_audit/fig6_delta_difference_after_adjustment.png", "B11b_proton_origin_stage_survival.png": "proton_origin_survival_audit/fig4_stage_survival_by_origin.png",
          "B12_proton_pid_high_ke.png": "particle_pid_audit/fig8_high_ke_proton_mistype_breakdown.png", "B12b_proton_low_ke_merge.png": "particle_pid_audit/fig7_low_ke_proton_merge_destination.png",
          "B14_spine_harmonized_differential.png": "spine_harmonization/differential_loose_vs_harmonized.png", "B13_natural_cv_cutflow.png": "exclusive_signal/natural_bnb_cv_cutflow_by_truth.png"}
for dst, src in MAIN.items():
    shutil.copyfile(P / src, A / dst)
for dst, src in BACKUP.items():
    shutil.copyfile(P / src, BK / dst)

# ---------------------------------------------------------------------------------------------------------- crops (PIL, of existing figures)
im = Image.open(P / "common_observables/delta_mass_resolution.png"); W, H = im.size; cr = im.crop((int(0.085 * W), 0, int(0.388 * W), int(0.925 * H)))                      # left panel only; the original x label / provenance footer overlap and are cut
fig, ax = plt.subplots(figsize=(cr.size[0] / 100, cr.size[1] / 100 + 0.7)); ax.imshow(cr); ax.axis("off"); fig.text(0.5, 0.075, "mass residual M_reco - M_true_decay [MeV]  (348 truth-matched Delta+ decay pairs)", ha="center", fontsize=10)
fig.text(0.01, 0.005, FOOT, fontsize=6, color="#444"); fig.subplots_adjust(left=0, right=1, top=1, bottom=0.14); fig.savefig(A / "09_delta_mass_residual.png", dpi=130); plt.close(fig)
for name, src in (("13a_eff_vs_photon_energy.png", "differential_efficiency/eff_stages_vs_photon_energy_mev.png"), ("13b_eff_vs_photon_angle.png", "differential_efficiency/eff_stages_vs_cos_theta_beam.png")):
    im = Image.open(P / src); W, H = im.size; im.crop((0, int(0.5 * H), int(0.255 * W), int(0.965 * H))).save(A / name)                                                             # bottom-left panel: all signal, selection stages

# ---------------------------------------------------------------------------------------------------------- redraws from committed tables
plt.rcParams.update({"font.size": 12})
stages = LB.stage.tolist(); fig, ax = plt.subplots(figsize=(8.2, 4.8)); x = np.arange(len(LB)); ax.bar(x, LB.cumulative_efficiency * 100, color="#0072B2")
for xi, (n, e) in enumerate(zip(LB.cumulative_surviving, LB.cumulative_efficiency)):
    ax.text(xi, e * 100 + 1.5, f"{n:,}", ha="center", fontsize=9, rotation=90, va="bottom")
ax.set_xticks(x); ax.set_xticklabels(stages, rotation=40, ha="right"); ax.set_ylabel("cumulative efficiency (%)"); ax.set_ylim(0, 118); ax.grid(alpha=.25, axis="y")
ax.set_title("1,153 / 12,427 = 9.28 %  (policy any)", fontsize=13); fig.text(0.01, 0.005, FOOT, fontsize=7, color="#444"); fig.subplots_adjust(bottom=0.27); fig.savefig(A / "02_cutflow.png", dpi=170, bbox_inches="tight"); plt.close(fig)

ffr = LB[LB.stage != "wc.valid"]; colr = ["#56B4E9", "#0072B2", "#009E73", "#E69F00", "#D55E00", "#CC79A7", "#999999", "#F0E442", "#000000"]; fig, ax = plt.subplots(figsize=(8.2, 4.8))
ax.barh(range(len(ffr)), ffr.first_failure_fraction * 100, color=colr[:len(ffr)]); ax.set_yticks(range(len(ffr))); ax.set_yticklabels([("selected" if s == "final" else "first failure: " + s) for s in ffr.stage]); ax.invert_yaxis()
for yi, (n, f) in enumerate(zip(ffr.first_failure_count, ffr.first_failure_fraction)):
    ax.text(f * 100 + 0.4, yi, f"{n:,} ({100 * f:.1f} %)", va="center", fontsize=10)
ax.set_xlabel("% of the 12,427 truth events (exclusive)"); ax.set_xlim(0, 36); ax.grid(alpha=.25, axis="x"); fig.text(0.01, 0.005, FOOT, fontsize=7, color="#444"); fig.subplots_adjust(bottom=0.2); fig.savefig(A / "03_loss_budget.png", dpi=170, bbox_inches="tight"); plt.close(fig)

M = pd.DataFrame(S["migration_final"], index=["reco 0p", "reco 1p", "reco >=2p"]).T; M["selected"] = M.sum(axis=1); fig, ax = plt.subplots(figsize=(6.4, 4.4)); vals = M[["reco 0p", "reco 1p", "reco >=2p"]].to_numpy(float)
ax.imshow(vals / vals.sum(axis=1, keepdims=True), cmap="Blues", vmin=0, vmax=1)
for i in range(3):
    for j in range(3):
        ax.text(j, i, f"{int(vals[i, j])}", ha="center", va="center", fontsize=16, color="white" if vals[i, j] / vals[i].sum() > 0.5 else "black")
ax.set_xticks(range(3)); ax.set_xticklabels(["reco 0p", "reco 1p", "reco >=2p"]); ax.set_yticks(range(3)); ax.set_yticklabels([f"{t}\n({int(M.loc[t, 'selected'])} selected)" for t in M.index])
ax.set_xlabel("reco channel (35 MeV, existing convention)   reco totals: 1g0p 527, 1g1p 556, >=2p 70", fontsize=9); ax.set_title("selected events: truth -> reco topology\n(colour = row fraction)", fontsize=11)
fig.text(0.01, 0.005, FOOT, fontsize=6.5, color="#444"); fig.subplots_adjust(bottom=0.22); fig.savefig(A / "08_migration_matrix.png", dpi=170, bbox_inches="tight"); plt.close(fig)

c = COMP[COMP.category != "TOTAL"]; cats = ["NC_PI0", "CC_PI0", "NUE_CC", "OUTSIDE_TPC_NU", "NUMU_CC", "OTHER_NC", "COSMIC_OR_UNMATCHED", "MULTI_OR_AMBIGUOUS"]
cc = {"NC_PI0": "#0072B2", "CC_PI0": "#56B4E9", "NUE_CC": "#009E73", "OUTSIDE_TPC_NU": "#D55E00", "NUMU_CC": "#E69F00", "OTHER_NC": "#CC79A7", "COSMIC_OR_UNMATCHED": "#999999", "MULTI_OR_AMBIGUOUS": "#000000"}
fig, ax = plt.subplots(figsize=(9, 3.6))
for yi, ch in enumerate(("1g1p", "1g0p")):
    left = 0
    for k in cats:
        r = c[(c.channel == ch) & (c.category == k)]
        if len(r) == 0:
            continue
        n, fr = int(r["count"].iloc[0]), float(r.fraction.iloc[0]); ax.barh(yi, fr * 100, left=left, color=cc[k], label=k if yi == 0 else None, edgecolor="white")
        if fr > 0.06:
            ax.text(left + fr * 50, yi, f"{n}\n{100 * fr:.0f} %", ha="center", va="center", fontsize=8.5, color="white")
        left += fr * 100
ax.set_yticks([0, 1]); ax.set_yticklabels(["1g1p\n230 events", "1g0p\n310 events"]); ax.set_xlabel("% of selected non-signal BNB-CV events (candidate-associated truth)"); ax.set_xlim(0, 100)
ax.legend(ncol=4, fontsize=7.5, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.28)); fig.text(0.01, 0.005, "BNB CV, frozen baseline policy any | no cosmic-only component | no nueCC special sample | statistical counts", fontsize=7, color="#444")
fig.subplots_adjust(bottom=0.36); fig.savefig(A / "10b_backgrounds_clean_redraw.png", dpi=170, bbox_inches="tight"); plt.close(fig)

# ---------------------------------------------------------------------------------------------------------- slide numbers (generated)
J = "tables/baseline_consolidation/summary.json"; B = "docs/analysis/NCDELTA_FROZEN_WIRECELL_BASELINE.md"; E = "docs/analysis/NCDELTA_FROZEN_BASELINE_EXECUTIVE_SUMMARY.md"


def get(path):
    v = S
    for k in path:
        v = v[k]
    return v


def pct(x, nd=2):
    return f"{100 * x:.{nd}f} %"


rows = []   # (slide, display, meaning, file, key, kind, machine or token)
def jr(slide, disp, meaning, path, fmt=lambda v: v):
    v = get(path); rows.append((slide, disp, meaning, J, "$" + "".join(f"[{k!r}]" for k in path), "json", v))
def tr(slide, disp, meaning, doc, where, token):
    rows.append((slide, disp, meaning, doc, where, "text", token))


jr("1,2", "12,427", "official Gen2 signal events in the provisional TPC box (truth denominator)", ["signal", "truth_denominator"])
jr("2", "5,863 / 5,557 / 1,007", "truth 0p / 1p / >=2p in the box (0p)", ["signal", "truth_by_class", "0p"]); jr("2", "5,557", "truth 1p", ["signal", "truth_by_class", "1p"]); jr("2", "1,007", "truth >=2p", ["signal", "truth_by_class", ">=2p"])
jr("2", "1,153", "selected events, policy any", ["signal", "final_any"]); jr("2", "1,101", "selected events, policy first", ["signal", "final_first"])
for key, disp, mean in (("any|all", "9.28 %", "efficiency any, total"), ("first|all", "8.86 %", "efficiency first, total"), ("any|0p", "8.12 %", "efficiency any, truth 0p"), ("any|1p", "10.69 %", "efficiency any, truth 1p"), ("any|>=2p", "8.24 %", "efficiency any, truth >=2p"),
                        ("any|Delta0", "7.61 %", "efficiency any, Delta0 -> n gamma"), ("any|Delta+", "11.32 %", "efficiency any, Delta+ -> p gamma")):
    jr("2" if "Delta" not in key else "backup", disp, mean + " (value index 2 of [selected, truth, eff, lo68, hi68])", ["signal", "eff", key, 2])
for st, disp in (("candidate", "8.8 %"), ("> 20 MeV shower", "26.2 %"), ("numu", "24.4 %"), ("other", "17.9 %"), ("ncpi0", "11.8 %"), ("n_20br1", "1.3 %")):
    jr("3", disp, f"first-failure fraction of the 12,427, stage {st} (index 3)", ["loss_budget", st, 3])
for st, disp in (("candidate", "11,331"), ("> 20 MeV shower", "8,080"), ("BDT evaluable", "8,034"), ("numu", "5,007"), ("other", "2,781"), ("ncpi0", "1,313"), ("n_20br1", "1,153")):
    jr("2,backup", disp, f"cumulative surviving events after stage {st} (index 0)", ["loss_budget", st, 0])
jr("3", "3,030", "first-failure count at numu (exclusive; 3,027 by cumulative difference, documented 3-event bookkeeping difference)", ["loss_budget", "numu", 2])
jr("3,5", "26.9 %", "numu failures as a share of the total baseline loss (11,274 of 12,427) - CORRECTED Phase-19 value", ["phase18_correction", "numu_fail_share_corrected"])
jr("backup", "12.8 %", "compact (< 20 cm) numu failures as a share of the total loss (corrected)", ["phase18_correction", "compact_share_corrected"])
rows.append(("3,5", "29.8 %", "SUPERSEDED Phase-18 share (denominator 11,331 omitted the 1,096 events without a candidate); NEVER show on a slide", J, "$['phase18_correction']['numu_fail_share_phase18']", "json", S["phase18_correction"]["numu_fail_share_phase18"]))
for t, vv in S["migration_final"].items():
    for lab, v, idx in zip(("reco 0p", "reco 1p", "reco >=2p"), vv, range(3)):
        jr("8", f"{v}", f"{t} -> {lab} (selected events)", ["migration_final", t, idx])
rows.append(("8", "527 / 556 / 70", "reco 1g0p / 1g1p / >=2p totals (column sums of migration_final)", J, "sum over $['migration_final'][*][0..2]", "sum", [sum(S["migration_final"][t][i] for t in S["migration_final"]) for i in range(3)]))
jr("10", "635", "selected non-signal BNB-CV events", ["background", "selected_nonsignal"])
for ch, disp in (("1g0p", "310"), ("1g1p", "230"), ("ge2p", "95")):
    jr("10", disp, f"selected non-signal events, reco {ch} (index 0)", ["background", "by_channel", ch, 0])
for ch, disp in (("1g0p", "1,140"), ("1g1p", "846"), ("ge2p", "349")):
    jr("11", disp, f"beam-neutrino selected rate per 1e20 POT, reco {ch} (index 1; stat. only)", ["background", "by_channel", ch, 1])
jr("11", "40.6", "signal selected rate per 1e20 POT, provisional TPC box, policy any (total)", ["signal_rate", "total_per_1e20"])
jr("11", "18.57 / 19.59 / 2.47", "signal rate per 1e20 POT by reco channel (1g0p)", ["signal_rate", "by_reco_channel", "1g0p"]); jr("11", "19.59", "signal rate, reco 1g1p", ["signal_rate", "by_reco_channel", "1g1p"]); jr("11", "2.47", "signal rate, reco >=2p", ["signal_rate", "by_reco_channel", "ge2p"])
jr("14", "416 / 128 / 117", "natural NC-Delta events in the BNB CV (total)", ["natural_cv", "n_events"]); jr("14", "128", "natural events in the filter box", ["natural_cv", "in_filter_box"]); jr("14", "117", "natural events in the provisional TPC box", ["natural_cv", "in_tpc_box"])
jr("14", "13", "natural events selected, policy any", ["natural_cv", "selected_any"]); jr("14", "11.1 %", "13 / 117", ["natural_cv", "natural_final_fraction"]); jr("14", "p = 0.52", "binomial p, natural 13/117 vs official 9.28 %", ["natural_cv", "final_p_binom"])
jr("14", "0.98", "TPC-box rate ratio natural CV / dedicated (95 % interval 0.81-1.18)", ["natural_cv", "rate_ratio_cv_over_dedicated"])
jr("15", "947 / 8,668 = 10.93 %", "Wire-Cell efficiency on the SPINE-harmonised denominator (selected, index 0)", ["harmonized", "B spine_technote_strict = HARMONIZED ALL", 0]); jr("15", "8,668", "harmonised denominator (index 1)", ["harmonized", "B spine_technote_strict = HARMONIZED ALL", 1])
jr("15", "9.38 %", "harmonised 0p50 (index 2)", ["harmonized", "harmonized 0p50", 2]); jr("15", "12.81 %", "harmonised Np50 (index 2)", ["harmonized", "harmonized Np50", 2])
jr("1", "0.4 / 0.2 / -0.05", "frozen thresholds numu / other / ncpi0 (numu)", ["frozen", "thresholds", "numu"]); jr("1", "35 MeV", "provisional truth proton threshold", ["frozen", "proton_threshold_mev"]); jr("1", "any", "candidate policy used for characterisation", ["frozen", "candidate_policy"])
tr("4", "27.6 %", "signal photons with a track-typed dominant object", B, "section 6, PID mis-typing", "27.6 %"); tr("4", "~3", "median number of pieces of a fragmented photon", B, "section 6, Fragmentation", "median 3")
tr("4", "567", "events with a good electron shower outside the main-vertex shower set", B, "section 6, last bullet", "567 events"); tr("4", "17.4 %", "share of the shower-stage failures that are the 567", B, "section 4, > 20 MeV shower", "17.4 %")
tr("4", "29.6 %", "share of shower-stage failures typed muon / pion / proton", B, "section 4, > 20 MeV shower", "29.6 %"); tr("4", "1.2 %", "shower-stage failures that are genuinely below 20 MeV", B, "section 4, > 20 MeV shower", "1.2 %")
tr("5", "29 % vs 74 %", "numu survival for total shower length < 20 cm vs above", B, "section 4, numu", "survival 29 % for total shower length < 20 cm vs 74 % above"); tr("5", "25 % vs 73 %", "numu survival for < 5 vs >= 5 segments", B, "section 4, numu", "25 % for < 5 segments vs 73 %")
tr("5", "76 %", "numu survival, clean electron shower", B, "section 4, numu", "clean electron shower 76 %"); tr("5", "36 %", "numu survival, fragmented", B, "section 4, numu", "fragmented 36 %"); tr("5", "22-25 %", "numu survival, muon-/pion-typed", B, "section 4, numu", "muon-/pion-typed 22-25 %")
tr("5", "44 %", "share of the raw compact-vs-extended difference shared with the photon reco class", B, "section 4, numu", "About 44 %"); tr("5", "25-32 pp", "association that remains after control", B, "section 4, numu", "25-32 pp")
tr("5", "65-79 % vs 33-46 %", "other-stage survival, anchored vs not anchored vertex", B, "section 4, other", "65-79 %, not anchored 33-46 %")
tr("5", "94.2 % / 88.0 %", "ncpi0-rejected events with a pair flag / with a pair containing the signal photon", B, "section 4, ncpi0", "94.2 %")
tr("6", "0.93 cm vs 11.6 cm", "|V_reco - V_true| median, truth 1p vs truth 0p (final selected)", B, "section 7", "truth 1p 0.93 cm"); tr("6", "11.6 cm", "truth 0p vertex distance", B, "section 7", "truth 0p 11.6 cm")
tr("6", "+25.8 / +36 / +24.5 cm", "median photon-line displacement for truth 0p: traditional / raw network / DL-stage", B, "section 7", "+25.8 cm in the traditional vertex, +36 cm in the raw network output and +24.5 cm at the DL-stage vertex")
tr("6", "0.25 cm", "median move of the late refinement", B, "section 7", "median 0.25 cm"); tr("6", "42 % -> 67.5 %", "DL-stage anchoring when a true proton is reco-typed", B, "section 7", "42 % to 67.5 %")
tr("7", "46 % / 67 % / 22 %", "proton typing efficiency above 35 MeV / at 200-300 MeV / above 500 MeV", B, "section 8", "46 % overall, 67 % at 200-300 MeV and 22 % above 500 MeV")
tr("7", "17 %", "protons above 35 MeV with a row typed muon / pion / electron-shower", B, "section 8", "17 % of the protons above 35 MeV"); tr("7", "65 %", "merged truth-1p protons merged into the signal photon", B, "section 8", "65 % of the merged truth-1p protons")
tr("7", "883 -> 37", "truth 1p -> reco 0p: matched row typed non-proton (matched candidate -> final)", B, "section 2, mechanisms", "883 -> 37"); tr("7", "468 -> 11 / 319 -> 26", "truth 0p -> reco 1p: signal photon typed proton / Geant4 secondary (matched -> final)", B, "section 2, mechanisms", "468 -> 11")
tr("9", "+2.8 MeV, [-44, +34] MeV", "M_reco - M_true_decay for 348 truth-matched Delta+ decay pairs", B, "section 9", "median **+2.8 MeV, 68 % interval [-44, +34] MeV**"); tr("9", "1.034 / 12.7 %", "photon E_reco / E_true median and 68 % half-width (1,148 truth-correct selected photons)", B, "section 9", "1.034 +/- 12.7 %")
tr("9", "348", "selected Delta+ decay pairs in the headline resolution", B, "section 9", "348 selected **Delta+ decay pairs**")
tr("10", "~33 / 24 / 17 %", "1g0p: NC pi0 / outside-TPC / nue CC share of the 310", B, "section 10", "NC pi0 102 (32.9 %), outside-TPC neutrinos 75 (24.2 %), nue CC 53 (17.1 %)"); tr("10", "~37 / 30 / 18 %", "1g1p: nue CC / NC pi0 / CC pi0 share of the 230", B, "section 10", "nue CC 86 (37.4 %")
tr("13a", "2.4 % -> ~15 %", "final efficiency vs true photon energy, 50-100 MeV to above 400 MeV", B, "section 5", "2.4 % (50-100 MeV) to about 15 % above 400 MeV"); tr("13b", "3.0 % -> 12.8 %", "final efficiency vs photon cos(theta), backward to forward", B, "section 5", "3.0 % (cos in [-1,-0.75]) to 12.8 %")
tr("13c", "4.4 %", "final efficiency in the last 50 cm in z (450-500 cm)", B, "section 5", "4.4 % at 450-500 cm"); tr("13c", "11.4 % vs 7.3 %", "interior diagnostic box vs outside (not a proposed FV)", B, "section 5", "11.4 % vs 7.3 % outside")
tr("2,5", "+3 / -3", "exclusive first failure minus cumulative difference at numu / ncpi0 (bookkeeping)", B, "section 3 bookkeeping note", "+3 at `numu`")

# ---- backup-slide numbers (all from the consolidated baseline text)
R = "docs/analysis/NCDELTA_ANALYSIS_ROADMAP.md"
tr("B03", "52 events", "any minus first: real signal events whose candidate 0 belongs to another interaction", B, "section 1", "52 events"); tr("B03", "22", "extra background events selected by any", B, "section 14, F", "adds 22 background events")
tr("B04", "9.28 % / 10.1-10.6 % / 9.92 %", "efficiency with no FV / 175-190 cm families / with the high-y carve-out (decision support only; no recommendation)", B, "section 14, D", "10.1-10.6 % for the 175-190 cm families")
tr("B05", "63 events", "1g1p -> 1g0p when included == 3 rows are excluded", B, "section 14, E2", "63 events 1g1p -> 1g0p"); tr("B05", "1,072", "truth events that change truth category between 35 and 50 MeV", B, "section 14, E1", "1,072 truth events"); tr("B05", "84.7 -> 89.7 %", "truth-1p fraction of the reco 1g1p channel, included == 3 counted vs excluded (a truth-composition number)", B, "section 14, E2", "84.7 -> 89.7 %")
tr("B06", "11,512", "events with a defined true conversion distance (92.6 % of the box)", B, "section 6", "11,512 events"); tr("B06", "0.975", "Spearman of the reco gap with the true conversion distance for detached showers with an anchored vertex", B, "section 6", "Spearman 0.975")
tr("B07", "15.1 % / 13.0 %", "shower-stage failures that are fragmented / track-typed", B, "section 4", "fragmented 15.1 %"); tr("B07", "13.0 %", "shower-stage failures that are track-typed", B, "section 4", "track 13.0 %")
tr("B09", "62 % / 15 % / 6 %", "parent of the 567 shower-not-in-main-vertex-set events: true signal proton / mis-typed photon piece / pi0 pair", B, "section 6", "a true signal proton 62 %")
tr("B11", "+12.7 pp -> +0.7 pp", "decay-vs-FSI difference at other, before and after proton KE alone", B, "section 1", "+12.7 pp falls to +0.7 pp"); tr("B11", "+3.8 pp / +5.2 pp", "residual final-efficiency differences (decay minus FSI-created; Delta+ minus Delta0 after adjustment)", B, "section 1", "decay minus FSI-created +3.8 pp")
tr("B12", "182 of 362", "protons above 500 MeV with a row typed muon / pion / electron-shower", B, "section 8", "182 of 362"); tr("B12", "55-66 cm vs 122 cm", "length of mistyped protons vs correctly typed", B, "section 8", "55-66 cm vs 122 cm")
tr("B14", "9,206 of 13,773", "official events inside the SPINE truth FV", B, "section 16", "9,206 of 13,773")
tr("B15", "A B C O P Q T U V Y", "roadmap items DONE", B, "section 17", "A B C O P Q T U V Y")
tr("9", "10.4 %", "photon-energy half-width of the Delta-mass width (proton KE 3 %)", B, "section 9", "photon energy (half-width 10.4 %)"); tr("9", "1220.8 MeV", "median M_Delta of all 554 usable events (context only; includes policy-dependent wrong-pair tails, NOT the headline resolution)", B, "section 9", "median 1220.8 MeV")
doc = ["# Slide numbers: where every number intended for a slide comes from", "",
       "Generated by `scripts/make_presentation_assets.py` from `tables/baseline_consolidation/summary.json` (kind `json`: the machine value is read from the JSON path, and the displayed number must round to it) or from the consolidated baseline text (kind `text`: the quoted token must occur in the cited document). `tests/test_presentation_package.py` re-checks every row. **If a slide shows a number that is not in this table, it is stale or unsourced.** The consolidated Phase-19 values win over any earlier phase document.", "",
       "| slide | displayed number | meaning | authoritative file | exact key / row | kind | machine value / text token |", "|---|---|---|---|---|---|---|"]
for r in rows:
    v = r[6]; v = f"`{v}`" if r[5] != "text" else f"\"{v}\""; doc.append(f"| {r[0]} | {r[1]} | {r[2]} | `{r[3]}` | `{r[4]}` | {r[5]} | {v} |")
(DOC / "NCDELTA_BASELINE_SLIDE_NUMBERS.md").write_text("\n".join(doc) + "\n")
json.dump([dict(slide=r[0], displayed=r[1], meaning=r[2], file=r[3], key=r[4], kind=r[5], value=r[6]) for r in rows], open(DOC / "NCDELTA_BASELINE_SLIDE_NUMBERS.json", "w"), default=str, indent=0)
print(len(rows), "numbers;", len(MAIN) + 6, "main assets;", len(BACKUP), "backup assets")

# ---------------------------------------------------------------------------------------------------------- asset table
import hashlib
AR = []
def asset(dst, src, slide, role, fig, crop, headline, how, main):
    AR.append(dict(slide=slide, role=role, source_file=("tables/" if src.endswith((".json", ".csv")) else "plots/") + src, phase="", figure_number=fig, crop_or_panel=crop, headline_number=headline, provenance=f"asset: presentation_assets/ncdelta_baseline/{dst}; {how}", main_or_backup=main))
PH = {"shower_vertex_audit": 9, "numu_compact_shower_audit": 18, "vertex_provenance_audit": 16, "particle_pid_audit": 15, "proton_truth_association": 10, "common_observables": 11, "background_mechanisms": 4, "baseline_consolidation": 19, "differential_efficiency": 6,
      "natural_ncdelta": "3/5", "spine_harmonization": 7, "official_ncdelta": 5, "analysis_definition_decisions": 13, "pi0_pair_fragmentation_audit": 14, "proton_origin_survival_audit": 17, "exclusive_signal": 3}
spec = [("02_cutflow.png", "baseline_consolidation/fig_cutflow_loss_budget.png", "2", "hero plot", 1, "left panel redrawn at slide size from tables/baseline_consolidation/loss_budget.csv", "1,153 / 12,427 = 9.28 %", "redraw", "main"),
        ("03_loss_budget.png", "baseline_consolidation/fig_cutflow_loss_budget.png", "3", "hero plot", 1, "right panel redrawn at slide size from tables/baseline_consolidation/loss_budget.csv", "first failures 8.8 / 26.2 / 24.4 / 17.9 / 11.8 / 1.3 %", "redraw", "main"),
        ("04_photon_taxonomy.png", "shower_vertex_audit/taxonomy_all_0p_1p.png", "4", "hero plot", 7, "whole figure; bars are fractions of the 11,331 candidate-stage events (not of 12,427)", "27.6 % track-typed; 567 events", "copy", "main"),
        ("05_numu_compactness.png", "numu_compact_shower_audit/fig1_survival_vs_segments_length.png", "5", "hero plot", 10, "both panels (segments, length); clean vs non-clean photon objects", "29 % vs 74 % (< 20 cm vs above)", "copy", "main"),
        ("05b_other_vertex_class_survival.png", "vertex_provenance_audit/fig8_stage_survival_by_vertex_class.png", "5", "second panel (optional)", "", "whole figure; classes A (DL displaced along the photon) and C (anchored); cumulative fraction of the class", "anchored 65-79 % vs not anchored 33-46 % at other (text, not read from the figure)", "copy", "main"),
        ("06_vertex_provenance.png", "vertex_provenance_audit/fig2_vertex_provenance_by_topology.png", "6", "hero plot", 8, "whole figure; legend entries A and C carry the message; the class B bar is essentially empty", "0.93 cm (1p) vs 11.6 cm (0p); refinement 0.25 cm", "copy", "main"),
        ("07_proton_reco_vs_ke.png", "particle_pid_audit/fig2_true_proton_reco_type_vs_ke.png", "7", "hero plot", 9, "whole figure; read the blue (proton-typed) bar at 200-300 and > 500 MeV", "67 % at 200-300 MeV; 22 % above 500 MeV", "copy", "main"),
        ("07b_migration_reasons.png", "proton_truth_association/migration_1p_to_0p_and_0p_to_1p.png", "7", "second panel", 3, "whole figure (left: truth 1p -> reco 0p; right: truth 0p -> reco 1p)", "883 -> 37 non-proton-typed; 468 -> 11 photon typed proton", "copy", "main"),
        ("08_migration_matrix.png", "baseline_consolidation/summary.json", "8", "hero plot", 3, "heat-map drawn from summary.json['migration_final']", "425 / 471 / 39 on the diagonal; reco 527 / 556 / 70", "redraw from committed table", "main"),
        ("09_delta_mass_residual.png", "common_observables/delta_mass_resolution.png", "9", "hero plot", 12, "left panel only (histogram of M_reco - M_true_decay); x label re-added; the legend quotes the 68 % half-width 39 MeV = half of [-44, +34]", "+2.8 MeV, [-44, +34] MeV", "crop of the original", "main"),
        ("10_backgrounds.png", "background_mechanisms/background_composition_by_channel.png", "10", "original (legend overlaps the bars)", 13, "crop to the 1g0p and 1g1p panels if used; prefer 10b", "310 / 230 / 95", "copy", "main"),
        ("10b_backgrounds_clean_redraw.png", "baseline_consolidation/bnb_background_composition_by_channel.csv", "10", "hero plot (recommended)", 13, "fractions of the 310 and 230 events redrawn from tables/baseline_consolidation/bnb_background_composition_by_channel.csv", "1g0p: NC pi0 33 %, outside-TPC 24 %, nue CC 17 %; 1g1p: nue CC 37 %, NC pi0 30 %, CC pi0 18 %", "redraw from committed table", "main"),
        ("11_rates.png", "baseline_consolidation/fig_signal_vs_background_rates.png", "11", "hero plot", 14, "whole figure; keep its NOT S/B footer visible", "signal 40.6; background 1,140 / 846 / 349 per 1e20 POT", "copy", "main"),
        ("13a_eff_vs_photon_energy.png", "differential_efficiency/eff_stages_vs_photon_energy_mev.png", "O1", "panel", "", "bottom-left panel (all signal, selection stages: numu yellow, other dark orange, ncpi0 pink, final black)", "2.4 % -> ~15 %", "crop of the original", "optional main"),
        ("13b_eff_vs_photon_angle.png", "differential_efficiency/eff_stages_vs_cos_theta_beam.png", "O1", "panel", "", "bottom-left panel (all signal, selection stages; same colours)", "3.0 % -> 12.8 %", "crop of the original", "optional main"),
        ("13c_vertex_z.png", "differential_efficiency/eff_groups_vs_vtx_z.png", "O1", "panel", 6, "whole figure or the bottom-right 'final (any)' panel; last bin z 450-500 cm", "4.4 % at 450-500 cm", "copy", "optional main"),
        ("14_natural_cv.png", "natural_ncdelta/natural_vs_dedicated.png", "O2", "hero plot", 15, "whole figure, or the bottom-right rate panel plus the top-left energy panel", "13 / 117 = 11.1 % vs 9.28 %, p = 0.52", "copy", "optional main"),
        ("15_spine_denominator.png", "spine_harmonization/denominator_definition_effect.png", "O3", "hero plot", "optional", "whole figure; keep the NOT a WC-vs-SPINE comparison footer visible", "947 / 8,668 = 10.93 %", "copy", "backup (optional main)")]
for dst, src, sl, role, fig, crop, head, how, main in spec:
    asset(dst, src, sl, role, fig, crop, head, how, main); AR[-1]["phase"] = PH.get(src.split("/")[0], "")
bspec = {"B01": ("B01_official_sample_census.png", 5), "B02": ("B02_cutflow_combined_original.png", 19), "B03": ("B03_candidate_policy.png", 13), "B04": ("B04_fv_comparison.png", 13), "B05": ("B05_proton_policy.png", 13), "B06": ("B06_conversion_distance.png", 6), "B07": ("B07_photon_taxonomy_vs_energy.png", 9),
         "B08": ("B08_numu_shap_families.png", 18), "B09": ("B09_ncpi0_pair_origin.png", 14), "B10": ("B10_shower_attachment_parents.png", 16), "B11": ("B11_proton_origin_delta.png", 17), "B12": ("B12_proton_pid_high_ke.png", 15), "B13": ("B13_natural_cv_cutflow.png", 3), "B14": ("B14_spine_harmonized_differential.png", 7)}
for dst, src in BACKUP.items():
    asset("backup/" + dst, src, dst.split("_")[0][:3], "backup figure", "", "whole figure", "see NCDELTA_BASELINE_PRESENTATION_OUTLINE.md", "copy", "backup"); AR[-1]["phase"] = PH.get(src.split("/")[0], "")
AR.append(dict(slide="B15", role="table slide (no figure)", source_file="docs/analysis/NCDELTA_ANALYSIS_ROADMAP.md", phase=19, figure_number="", crop_or_panel="status matrix from baseline section 17", headline_number="DONE A B C O P Q T U V Y", provenance="no asset; build as a table", main_or_backup="backup"))
AR.append(dict(slide="1,12", role="table slide (no figure)", source_file="docs/analysis/NCDELTA_FROZEN_WIRECELL_BASELINE.md", phase=19, figure_number="", crop_or_panel="definition box (slide 1); status table (slide 12)", headline_number="9.28 %", provenance="no asset; build as text / table", main_or_backup="main"))
pd.DataFrame(AR)[["slide", "role", "source_file", "phase", "figure_number", "crop_or_panel", "headline_number", "provenance", "main_or_backup"]].to_csv(DOC / "NCDELTA_BASELINE_SLIDE_ASSETS.csv", index=False)
print(len(AR), "asset rows")
