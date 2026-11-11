"""Phase 18: numu compact-shower / training-domain audit (roadmap Z): synthetic checks of the helpers and pinned checks of the committed tables.

Nothing here changes a selection flag, threshold, weight, vertex, type or policy.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from sbnd_single_photon import numu_audit as NA

ROOT = Path(__file__).resolve().parents[1]
TAB = ROOT / "tables" / "numu_compact_shower_audit"
csv = lambda n: pd.read_csv(TAB / f"{n}.csv")
S = json.load(open(TAB / "summary.json"))


# ------------------------------------------------------------------------------------------------------------ helpers
def test_wilson_interval_basic():
    p, lo, hi = NA.wilson(50, 100); assert abs(p - 0.5) < 1e-12 and lo < 0.5 < hi and abs((hi - 0.5) - (0.5 - lo)) < 1e-9
    p, lo, hi = NA.wilson(0, 10); assert p == 0 and lo == 0 and 0 < hi < 0.3
    p, lo, hi = NA.wilson(10, 10); assert p == 1 and abs(hi - 1) < 1e-12 and 0.7 < lo < 1
    assert np.isnan(NA.wilson(0, 0)[0])


def test_bins_are_left_closed_and_preset():
    b = NA.bin_labels([0, 4.9, 5, 10.9, 11, 17.9, 18, 100], NA.SEG_EDGES, NA.SEG_LABELS).astype(str).tolist()
    assert b == ["1-4", "1-4", "5-10", "5-10", "11-17", "11-17", ">=18", ">=18"]
    assert NA.bin_labels([19.99, 20, 39.9, 40, 80], NA.LEN_EDGES, NA.LEN_LABELS).astype(str).tolist() == ["<20", "20-40", "20-40", "40-80", ">=80"]
    assert NA.COMPACT_LENGTH_CM == 20.0 and NA.COMPACT_NSEG == 5
    assert NA.compact_flag([19.9, 20.0, 50], None).tolist() == [True, False, False]


def test_object_class_mapping_is_exhaustive_for_phase15_classes():
    for k in ("A clean electron shower", "G fragmented (Phase 9), mixed types", "C muon-like dominant object", "D pion-like dominant object", "E proton-like dominant object", "F electron-track / other track",
              "B electron shower, not usable by the single-photon stage", "H no particle row", "I no reconstructed charge", "J charge outside candidates / other candidate"):
        assert NA.object_class(k) in NA.OBJECT_ORDER
    assert NA.object_class("something new") == "no relevant photon row"


def test_survival_table_and_auc_and_deviance():
    df = pd.DataFrame({"g": list("aabbb"), "survive": [True, False, True, True, False]})
    t = NA.survival_table(df, ["g"]).set_index("g"); assert t.loc["a", "n"] == 2 and t.loc["b", "n_pass"] == 2 and abs(t.loc["b", "survival"] - 2 / 3) < 1e-12
    assert NA.auc([1, 2, 3, 4], [0, 0, 1, 1]) == 1.0 and NA.auc([4, 3, 2, 1], [0, 0, 1, 1]) == 0.0 and NA.auc([1, 1, 1, 1], [0, 1, 0, 1]) == 0.5
    y = np.array([1, 0, 1, 0]); assert NA.bernoulli_deviance(y, np.full(4, 0.5)) > NA.bernoulli_deviance(y, np.array([0.99, 0.01, 0.99, 0.01]))


def test_grouped_deviance_recovers_a_planted_factor():
    rng = np.random.default_rng(1); n = 4000; a = rng.integers(0, 2, n); b = rng.integers(0, 2, n); y = (rng.random(n) < np.where(a == 1, 0.8, 0.2)).astype(float)
    df = pd.DataFrame({"a": a.astype(str), "b": b.astype(str), "y": y}); t = NA.grouped_deviance_table(df, "y", {"signal": ["a"], "noise": ["b"]}).set_index("group")
    assert t.loc["signal", "pseudo_r2_alone"] > 0.2 and abs(t.loc["noise", "pseudo_r2_alone"]) < 0.01 and t.loc["signal", "deviance_increase_if_dropped"] > 100 * max(t.loc["noise", "deviance_increase_if_dropped"], 0.01)


# ------------------------------------------------------------------------------------------------------------ pinned tables
def test_numu_stage_denominator_and_survival_are_reproduced_exactly():
    b = S["baseline"]; assert (b["n_events"], b["n_pass"], b["n_fail"]) == (8038, 5007, 3031) and b["n_total_signal_box_events"] == 11331
    r = csv("numu_baseline_reproduction").set_index("group")
    assert r.loc["all events reaching numu", "n"] == 8038 and r.loc["all events reaching numu", "n_pass"] == 5007
    assert [int(r.loc[g, "n"]) for g in ("truth 0p", "truth 1p", "truth >=2p")] == [3937, 3450, 651] and [int(r.loc[g, "n_pass"]) for g in ("truth 0p", "truth 1p", "truth >=2p")] == [2446, 2174, 387]
    assert r.loc["clean signal-photon shower", "n_pass"] == 4117 and r.loc["non-clean photon object", "n_pass"] == 890
    assert r.loc["clean signal-photon shower", "n"] + r.loc["non-clean photon object", "n"] == 8038


def test_score_reproduction_has_no_decision_flip():
    q = S["reproduction"]; assert q["decision_flips"] == 0 and q["max_abs_score_diff"] < 1e-6 and q["n_nonfinite_inputs"] == 0 and q["n_trees"] == 300 and q["n_inputs"] == 73 and q["threshold"] == 0.4


def test_conditional_survival_reproduces_the_stage_pass_count_in_every_binning():
    c = csv("numu_conditional_survival"); a = c[c.population == "all"]
    for v in a.variable.unique():
        s = a[a.variable == v]; assert s.n.sum() == 8038 and s.n_pass.sum() == 5007, v
    for name in ("numu_survival_vs_n_segments", "numu_survival_vs_total_length", "numu_survival_vs_true_energy"):
        t = csv(name); assert t.n.sum() == 8038 and t.n_pass.sum() == 5007, name


def test_topology_and_photon_state_closure():
    r = csv("numu_baseline_reproduction").set_index("group"); o = csv("numu_controlling_object_classes")
    assert o.n.sum() == 8038 and (o.n * o.survival).sum().round() == 5007
    assert abs(o.set_index("object").loc["clean e-shower", "survival"] - r.loc["object: clean e-shower", "survival"]) < 1e-3
    assert r.loc["compact (length < 20 cm)", "n"] + r.loc["not compact (length >= 20 cm)", "n"] == 8038 and r.loc["few-segment (< 5 segments)", "n"] + r.loc["not few-segment", "n"] == 8038
    cs = csv("numu_conditional_survival"); t = cs[(cs.population == "all") & (cs.variable == "truth proton class")].set_index("bin"); assert abs(t.loc["truth 0p", "survival"] - 0.621) < 1e-3 and abs(t.loc["truth 1p", "survival"] - 0.630) < 1e-3
    mt = csv("numu_mu_pi_row_truth"); assert mt.n.sum() == 636 and mt[mt.truth_of_row == "signal-photon piece"].n.sum() == 630


def test_compactness_result_is_pinned_and_associated_not_causal():
    r = csv("numu_baseline_reproduction").set_index("group")
    assert abs(r.loc["compact (length < 20 cm)", "survival"] - 0.293) < 1e-3 and abs(r.loc["not compact (length >= 20 cm)", "survival"] - 0.735) < 1e-3
    a = csv("numu_compactness_adjusted_difference"); a = a[a.contrast.str.startswith("compact")].set_index("control")
    assert abs(a.loc["raw (no control)", "adjusted"] + 0.442) < 2e-3 and -0.30 < a.loc["+ photon object class", "adjusted"] < -0.20 and a.iloc[:5].adjusted.max() < -0.2
    assert (a.support_fraction > 0.6).all()
    d = csv("numu_driver_deviance_groups").set_index("group"); assert d.pseudo_r2_alone.idxmax() == "compactness / segmentation (segments, length)" and d.loc["truth topology (0p/1p/>=2p, Delta charge)", "pseudo_r2_alone"] < 0.01
    # energy: marginally flat, conditionally falling
    e = S["energy_flatness"]; assert abs(e["spearman_survive_vs_etrue"]) < 0.05 and e["spearman_len_vs_etrue"] > 0.4
    c = csv("numu_conditional_survival"); c = c[(c.population == "all") & (c.variable == "true photon energy (MeV)")]; assert c.survival.max() - c.survival.min() < 0.1


def test_shap_additivity_and_family_bookkeeping():
    s = S["shap"]; assert s["additivity_max_error"] < 1e-6 and s["n_fg"] == 800 and s["mean_margin_accepted"] > s["threshold_margin"] > s["mean_margin_rejected"]
    f = csv("numu_shap_families_by_group"); r = f[f.group == "rejected"]; assert abs(r.share_of_abs_phi.sum() - 1) < 1e-2
    rc = f[f.group == "rejected & compact"].set_index("family"); assert rc.mean_signed_phi.idxmin() == "shower quality (br/lem/hol/lol)"
    rn = f[f.group == "rejected & not compact"].set_index("family"); assert rn.mean_signed_phi.idxmin() == "upstream BDT scores"


def test_loss_budget_closure():
    b = S["loss_budget"]; assert b["n_signal_box_events"] == 11331 and b["n_lost"] == b["n_signal_box_events"] - b["n_final"] and b["n_fail_numu"] == 3031
    assert b["n_fail_numu_clean"] + b["n_fail_numu_nonclean"] == 3031 and abs(b["numu_fail_share_of_total_loss"] - 3031 / b["n_lost"]) < 1e-12
    t = csv("numu_loss_budget").set_index("group"); assert t.loc["fail numu: all", "n"] == 3031 and t.loc["compact (length < 20 cm)", "n"] == b["n_fail_numu_compact"]


def test_natural_cv_check_uses_stored_inputs_only():
    n = S["natural_cv"]; assert n["n_candidates"] == 108 and 0 < n["compact_survival"] < n["noncompact_survival"] < 1
    t = csv("numu_natural_cv_vs_official"); nat = t[t.population.str.startswith("natural")]; assert nat[nat.binned_by == "total length"].n.sum() == 108


def test_nothing_selected_tuned_or_changed():
    cfg = ROOT / "configs" / "baseline_selection.yaml"
    assert hashlib.sha256(cfg.read_bytes()).hexdigest() == "f3251b785be6e52ff3e429000a0319a6df8e42d2016ace2f51c7650a38e2fb0b" == S["metadata"]["baseline_config_sha256"]
    th = {c["name"]: c["threshold"] for c in yaml.safe_load(open(cfg))["cuts"]}
    assert th["single_photon_numu_score_gt_0p4"] == 0.4 and th["single_photon_other_score_gt_0p2"] == 0.2 and th["single_photon_ncpi0_score_gt_m0p05"] == -0.05
    assert S["metadata"]["numu_xml_sha256"] == "5886affbdb3a4499a4515ecc8d354eb1449e7c204d32f1cc54c1ec8868ead961"
    assert hashlib.sha256((ROOT / "configs" / "analysis_definition_candidates.yaml").read_bytes()).hexdigest() == json.load(open(ROOT / "tables" / "analysis_definition_decisions" / "summary.json"))["metadata"]["analysis_definition_candidates_sha256"]
    assert S["metadata"]["compactness_bins"]["compact_length_cm"] == 20.0     # fixed in advance, not scanned
    txt = (ROOT / "docs" / "analysis" / "NUMU_COMPACT_SHOWER_TRAINING_DOMAIN_AUDIT.md").read_text().lower() + (ROOT / "docs" / "analysis" / "NUMU_TRAINING_DOMAIN_SOURCE_AUDIT.md").read_text().lower()
    for bad in ("final purity", "final s/b", "significance of", "retuned", "we conclude that the domain shift", "proves a domain shift"):
        assert bad not in txt
    assert "cannot be established" in txt and "impossible" in txt
