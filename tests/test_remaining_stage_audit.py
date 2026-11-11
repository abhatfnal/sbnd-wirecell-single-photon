"""Remaining frozen single-photon stages (Phase 12): synthetic checks of the helpers and pinned checks of the committed summary tables.

Nothing here changes a selection flag, threshold or policy: the pinned checks assert that the frozen decisions are untouched.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from sbnd_single_photon import bdt as B, remaining_audit as RA

ROOT = Path(__file__).resolve().parents[1]
TAB = ROOT / "tables" / "remaining_stage_audit"
S = json.load(open(TAB / "summary.json"))
WEIGHTS = B.DEFAULT_WEIGHT_DIR / "single_photon_numu_bdt_final.xml"


def test_exact_numu_ncpi0_score_reproduction():
    r = S["reproduction"]
    for m, n_in, n_tr in (("numu", 73, 300), ("ncpi0", 45, 400)):
        d = r[m]
        assert d["max_abs_diff_vs_stored"] == 0.0 and d["max_abs_diff_vs_independent"] < 1e-6 and d["n_decision_flips_at_threshold"] == 0 and d["n_diff_gt_1e6"] == 0
        assert d["n_inputs"] == n_in and d["n_trees"] == n_tr and d["n_compared_to_stored_derived_score"] > 8000 and d["scalar_vs_vectorised_f32_max"] == 0.0
    assert r["numu"]["n_nonfinite_recomputed"] == 0 and r["ncpi0"]["n_nonfinite_recomputed"] == 4
    assert r["nue"]["n_decision_flips_at_threshold"] == 0 and r["nue"]["n_diff_gt_1e6"] <= r["nue"]["n_tie_convention_cases"] == 5      # every nue difference is a tie-convention case
    sums = [l.split()[0] for l in (ROOT / "provenance" / "microboone_reference_SHA256SUMS.txt").read_text().splitlines() if l.strip()]
    for m in ("numu", "ncpi0", "nue"):
        assert r[m]["weight_sha256"] in sums                                                   # the frozen weight files are the reference bundle's


@pytest.mark.skipif(not WEIGHTS.exists(), reason="MicroBooNE reference weights not available")
def test_tie_convention_counter_on_the_real_numu_model():
    m = B.TmvaBdt("numu", WEIGHTS); t = m.trees[0]; X = np.zeros((2, len(m.var_names)))
    X[0, int(t.ivar[0])] = float(np.float32(t.cut[0]))                                         # exactly on the root cut
    X[1, int(t.ivar[0])] = float(np.float32(t.cut[0])) + 1.0                                   # off the cut
    assert RA.n_tie_cases(m, X) >= 1 and RA.n_tie_cases(m, X[1:]) <= RA.n_tie_cases(m, X)


def test_stage_population_accounting():
    p = S["populations"]
    assert p["numu"] == dict(events=8038, survive=5007) and p["other"] == dict(events=5007, survive=2781) and p["ncpi0"] == dict(events=2781, survive=1313) and p["nue"] == dict(events=1313, survive=1313)
    ch = pd.read_csv(TAB / "chain_conditional_survival_by_group.csv"); a = ch[ch.group == "all"].set_index("stage")
    assert list(a.n_surviving.reindex(["candidate", "shower", "evaluable", "numu", "other", "ncpi0", "nue", "n20br1"])) == [11331, 8080, 8034, 5007, 2781, 1313, 1313, 1153]
    assert (a.n_surviving.diff().dropna() <= 0).all()                                          # a cutflow never gains events
    for g in ("truth 0p", "truth 1p", "truth >=2p"):
        pass
    t = ch[ch.group.isin(["truth 0p", "truth 1p", "truth >=2p"])].groupby("stage").n_surviving.sum(); assert (t == a.n_surviving.reindex(t.index)).all()      # topology closure at every stage
    d = ch[ch.group.isin(["Delta0", "Delta+"])].groupby("stage").n_surviving.sum(); assert (d == a.n_surviving.reindex(d.index)).all()


def test_fixed_thresholds_unchanged():
    cfg = yaml.safe_load(open(ROOT / "configs" / "baseline_selection.yaml")); th = {c["name"]: c["threshold"] for c in cfg["cuts"]}
    assert RA.FROZEN_THRESHOLDS == {"numu": th["single_photon_numu_score_gt_0p4"], "other": th["single_photon_other_score_gt_0p2"], "ncpi0": th["single_photon_ncpi0_score_gt_m0p05"], "nue": th["single_photon_nue_score_gt_m1"]}
    assert S["metadata"]["frozen_thresholds"] == RA.FROZEN_THRESHOLDS and S["metadata"]["baseline_config_sha256"].startswith("f3251b78")
    assert abs(S["numu_shap"]["threshold_margin"] - np.arctanh(0.4)) < 1e-12 and abs(S["ncpi0_shap"]["threshold_margin"] - np.arctanh(-0.05)) < 1e-12


def test_default_fraction_semantics_and_family_map_completeness():
    assert RA.default_fraction([0.0, 0.0, 1.0, np.nan], 0.0) == 2 / 3 and np.isnan(RA.default_fraction([1.0], np.nan)) and RA.default_fraction([0.4], 0.4) == 1.0      # float32 comparison, NaN ignored
    for f in ("input_source_table_numu.csv", "input_source_table_ncpi0.csv", "input_source_table_nue.csv"):
        t = pd.read_csv(TAB / f)
        assert all(RA.family_of(v) in RA.FAMILIES for v in t.bdt_variable)                      # every input of the three models belongs to exactly one family
    assert all(RA.family_of(v) in RA.FAMILIES for v in pd.read_csv(ROOT / "tables" / "other_bdt_audit" / "input_source_table.csv").bdt_variable)
    for m in ("numu", "ncpi0"):
        d = pd.read_csv(TAB / f"default_fractions_{m}.csv"); fr = d.filter(like="frac_default_").stack().dropna(); assert ((fr >= 0) & (fr <= 1)).all() and len(d) == (73 if m == "numu" else 45)
    x = pd.read_csv(TAB / "default_fractions_cross_bdt.csv").set_index("family")
    assert x.loc["pi0 topology", "ncpi0_n_inputs"] == 20 and x.loc["cosmic tagger", "other_n_inputs"] == 59 and x.loc["upstream BDT scores", "ncpi0_n_inputs"] == 15
    assert RA.family_of("numu_score") == "upstream BDT scores" and RA.family_of("tro_1_score") == "upstream BDT scores" and RA.family_of("kine_pio_mass") == "pi0 topology"


def test_controlling_candidate_rule():
    c = pd.DataFrame(dict(file_index=[0, 0, 0, 1], ev=[0, 0, 0, 0], c_nu_index=[0, 1, 2, 0], reach=[True, True, False, True], score=[0.1, 0.9, 5.0, 0.2]))
    r = RA.controlling_candidate(c, "reach", "score").set_index("file_index")
    assert r.loc[0, "c_nu_index"] == 1 and r.loc[0, "n_reaching"] == 2 and r.loc[0, "n_candidates_total"] == 3 and r.loc[1, "c_nu_index"] == 0     # a non-reaching candidate never controls
    tie = pd.DataFrame(dict(file_index=[0, 0], ev=[0, 0], c_nu_index=[1, 0], reach=[True, True], score=[0.5, 0.5])); assert RA.controlling_candidate(tie, "reach", "score").c_nu_index.iloc[0] == 0   # ties: lowest nu_index


def test_n20br1_source_logic_and_class_hierarchy():
    with pytest.raises(ValueError):
        RA.classify_n20br1(1, True, 0, 0, 0)                                                  # an event with n_20br1 == 1 does not fail
    assert RA.classify_n20br1(0, True, 0, 0, 0) == RA.N20BR1_CLASSES[0] and RA.classify_n20br1(0, False, 0, 0, 0) == RA.N20BR1_CLASSES[1]
    assert RA.classify_n20br1(2, True, 1, 1, 1) == RA.N20BR1_CLASSES[2] and RA.classify_n20br1(2, True, 0, 1, 1) == RA.N20BR1_CLASSES[3]
    assert RA.classify_n20br1(3, True, 0, 0, 2) == RA.N20BR1_CLASSES[4] and RA.classify_n20br1(2, False, 0, 0, 0) == RA.N20BR1_CLASSES[5]
    d = pd.read_csv(TAB / "n20br1_n20mev_vs_n20br1.csv"); assert int(d.n_events.sum()) == 1313
    assert int(d[d.max_n_20br1_over_reaching_cands_capped_4 == 1].n_pass.sum()) == 1153 and int(d[d.max_n_20br1_over_reaching_cands_capped_4 >= 2].n_pass.sum()) == 0
    assert not (d.max_n_20br1_over_reaching_cands_capped_4 == 0).any()                         # n_20br1 == 0 never reaches the stage (shw_sp_filled requires en20 && badreco1)


def test_exact_160_event_n20br1_accounting():
    t = pd.read_csv(TAB / "n20br1_failure_taxonomy.csv")
    assert int(t.n.sum()) == 160 == 1313 - 1153 and set(t.cls) == set(RA.N20BR1_CLASSES)
    assert (t.n0p + t.n1p + t.n2p == t.n).all() and (t.nDelta0 + t.nDeltaPlus == t.n).all()   # split closure
    assert int(t.n0p.sum()) == 98 and int(t.n1p.sum()) == 53 and int(t.n2p.sum()) == 9
    assert int(t[t.cls.str.startswith("no_br1")].n.sum()) == 0 and int(t[t.cls == "multiple_br1_showers__extra_signal_photon_piece"].n.iloc[0]) == 126
    assert S["n20br1"][2]["n"] == 126


def test_photon_cleanliness_stage_closure():
    c = pd.read_csv(TAB / "chain_cleanliness.csv").set_index("stage")
    parts = ["n_clean", "n_fragmented", "n_typed_non_electron", "n_track", "n_row_missing", "n_other_non_clean"]
    assert (c[parts].sum(axis=1) == c.n).all()                                                 # every surviving event has exactly one photon-object state
    assert list(c.n) == [8080, 8034, 5007, 2781, 1313, 1313, 1153] and int(c.loc["shower", "n_clean"]) == 5423 and int(c.loc["n20br1", "n_clean"]) == 1131
    assert c.loc["numu":].clean_fraction.is_monotonic_increasing and c.loc["n20br1", "clean_fraction"] > c.loc["shower", "clean_fraction"] + 0.3      # the BDT stages and n_20br1 only clean the sample (the evaluability step is neutral to 4e-4)
    k = pd.read_csv(TAB / "chain_conditional_survival_by_photon_state.csv")
    for st in ("numu", "other", "ncpi0", "n20br1"):
        a = k[(k.stage == st) & (k.state == "clean")].iloc[0]; b = k[(k.stage == st) & (k.state == "non-clean (all)")].iloc[0]; assert a.conditional_survival > b.conditional_survival


def test_topology_survival_closure_and_harmonized_mapping():
    s = pd.read_csv(TAB / "stage_survival_by_group.csv")
    for st, n, k in (("numu", 8038, 5007), ("ncpi0", 2781, 1313)):
        d = s[(s.stage == st) & (s.group == "truth_topology")]; assert int(d.n.sum()) == n and int(d.k.sum()) == k
        d = s[(s.stage == st) & (s.group == "delta_charge")]; assert int(d.n.sum()) == n and int(d.k.sum()) == k
        d = s[(s.stage == st) & (s.group == "photon_cleanliness")]; assert int(d.n.sum()) == n and int(d.k.sum()) == k
    ch = pd.read_csv(TAB / "chain_conditional_survival_by_group.csv"); g = lambda name: ch[ch.group == name].set_index("stage").n_surviving
    assert ((g("harmonized 0p50") + g("harmonized Np50")) == g("harmonized signal (spine_truth_signal)")).all()          # the Phase-7 0p50 / Np50 subsets partition the harmonized signal at every stage
    assert g("harmonized signal (spine_truth_signal)")["n20br1"] == 947


def test_no_baseline_selection_flag_changed_and_no_rate_claims():
    assert S["metadata"]["baseline_config_sha256"].startswith("f3251b78")
    ch = pd.read_csv(TAB / "chain_conditional_survival_by_group.csv"); assert int(ch[(ch.group == "all") & (ch.stage == "n20br1")].n_surviving.iloc[0]) == 1153       # the validated final selection is reproduced, not re-selected
    t = pd.read_csv(TAB / "full_frozen_chain_summary.csv"); assert list(t.stage)[0] == "candidate" and int(t.n_surviving.iloc[-1]) == 1153 and len(t) == 8
    assert {"dominant_signal_loss_mechanism", "main_model_or_input_family", "dependence_on_0p_1p", "source_audited", "remaining_caveat", "conditional_efficiency"} <= set(t.columns)
    doc = (ROOT / "docs" / "analysis" / "REMAINING_FROZEN_SELECTION_STAGE_AUDIT.md").read_text()
    assert "no threshold scan" in doc.lower() and "## 18. Questions for later optimization (questions only)" in doc
