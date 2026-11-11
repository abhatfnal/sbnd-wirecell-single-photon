"""Analysis-definition decision support (Phase 13): synthetic checks of the helpers and pinned checks of the committed tables.

Nothing here changes a selection flag or a policy; no cosmic normalisation, purity or significance exists in the outputs.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from sbnd_single_photon import analysis_definitions as AD

ROOT = Path(__file__).resolve().parents[1]
TAB = ROOT / "tables" / "analysis_definition_decisions"
S = json.load(open(TAB / "summary.json"))
CFG = yaml.safe_load(open(ROOT / "configs" / "analysis_definition_candidates.yaml"))


def test_fv_boundary_semantics():
    sp = AD.FV_SPECS["spine180"]; ca = AD.FV_SPECS["cafpyana190"]
    # SPINE truth FV is inclusive (<= 180, 10 <= z <= 450); the cafpyana box is strict
    assert AD.fv_mask([180.0], [0.0], [10.0], sp)[0] and AD.fv_mask([180.0], [180.0], [450.0], sp)[0] and not AD.fv_mask([180.01], [0.0], [100.0], sp)[0]
    assert not AD.fv_mask([190.0], [0.0], [100.0], ca)[0] and AD.fv_mask([189.99], [0.0], [100.0], ca)[0] and not AD.fv_mask([0.0], [0.0], [10.0], ca)[0] and not AD.fv_mask([0.0], [0.0], [450.0], ca)[0]
    nu = AD.FV_SPECS["numu2021"]; assert AD.fv_mask([189.0], [189.9], [100.0], nu)[0] and not AD.fv_mask([189.2], [0.0], [100.0], nu)[0]
    assert not AD.fv_mask([np.nan], [0.0], [100.0], ca)[0] and AD.fv_mask([np.nan], [0.0], [100.0], None)[0] and AD.fv_mask([999.0], [999.0], [999.0], AD.FV_SPECS["none"])[0]
    lg = AD.FV_SPECS["legacy_nue175"]; assert not AD.fv_mask([1.0], [0.0], [100.0], lg)[0] and AD.fv_mask([-100.0], [0.0], [100.0], lg)[0] and AD.fv_mask([100.0], [0.0], [100.0], lg)[0]      # cathode excluded on both sides
    co = AD.FV_SPECS["cohpi_carve"]; assert AD.fv_mask([100.0], [150.0], [200.0], co)[0] and not AD.fv_mask([100.0], [150.0], [300.0], co)[0] and AD.fv_mask([100.0], [50.0], [300.0], co)[0]      # high-y carve-out for z > 250
    d = AD.distance_to_faces([0, 190, 0], [0, 0, 0], [250, 250, 0.0]); assert list(d) == [200.0, 10.0, 0.0] and AD.distance_to_faces([210.0], [0.0], [250.0])[0] < 0


def test_truth_and_reco_fv_are_separate_operations():
    sp = AD.FV_SPECS["spine180"]
    truth = pd.DataFrame(dict(x=[0.0, 185.0, 0.0], y=[0.0, 0.0, 0.0], z=[100.0, 100.0, 100.0])); reco = pd.DataFrame(dict(x=[0.0, 0.0, 185.0], y=[0.0, 0.0, 0.0], z=[100.0, 100.0, 100.0]))
    den = AD.fv_mask(truth.x, truth.y, truth.z, sp); num = den & AD.fv_mask(reco.x, reco.y, reco.z, sp)
    assert den.sum() == 2 and num.sum() == 1                                          # an event inside the truth FV but reconstructed outside is NOT counted; one reconstructed inside but truth outside is NOT signal
    fv = pd.DataFrame(S["fv"]).set_index("fv")
    assert fv.loc["none", "truth_denominator"] == 12427 and fv.loc["av200", "truth_denominator"] == 12427 and fv.loc["spine180", "truth_denominator"] == 9206
    ev = pd.read_csv(TAB / "fv_comparison.csv").set_index("fv"); assert ev.loc["av200", "sel_any_reco_in_fv_truth_outside"] == 0 and ev.loc["spine180", "sel_any_reco_in_fv_truth_outside"] > 0      # the truth FV is never imposed on the reco side


def test_signal_and_background_use_the_same_reco_fv_and_nesting():
    f = pd.read_csv(TAB / "fv_comparison.csv").set_index("fv")
    for a, b in (("none", "av200"), ("av200", "cafpyana190"), ("cafpyana190", "spine180"), ("spine180", "legacy_nue175")):
        assert f.loc[a, "bkg_any"] >= f.loc[b, "bkg_any"] and f.loc[a, "sel_any"] >= f.loc[b, "sel_any"] and f.loc[a, "truth_denominator"] >= f.loc[b, "truth_denominator"]      # nested boxes
    assert f.loc["none", "bkg_any"] == 635 and f.loc["none", "sel_any"] == 1153 and f.loc["none", "sel_first"] == 1101 and f.loc["none", "bkg_first"] == 613      # frozen baseline numbers
    for fv in f.index:
        r = f.loc[fv]; assert r.bkg_any_reco_1g0p + r.bkg_any_reco_1g1p + r.bkg_any_reco_1gNp == r.bkg_any and r.sel_any_reco_1g0p + r.sel_any_reco_1g1p + r.sel_any_reco_1gNp == r.sel_any
        assert r["sel_any"] == r["sel_any_Delta0"] + r["sel_any_DeltaPlus"] == r["sel_any_truth_0p"] + r["sel_any_truth_1p"] + r["sel_any_truth_>=2p"]       # topology and Delta-charge closure of the selected signal


def test_proton_policy_p1_p4_closure_and_truth_threshold_pairing():
    P = pd.read_csv(TAB / "proton_policy_comparison.csv").set_index("policy")
    assert list(P.index) == ["P1", "P2", "P3", "P4"] and list(AD.PROTON_PACKAGES) == ["P1", "P2", "P3", "P4"]
    for p in P.index:
        assert P.loc[p, "final_1g0p"] + P.loc[p, "final_1g1p"] + P.loc[p, "final_1gNp"] == 1153                               # the frozen photon selection is identical for every policy
        assert AD.PROTON_PACKAGES[p]["truth_threshold_mev"] == AD.PROTON_PACKAGES[p]["reco_threshold_mev"]                       # truth and reco thresholds are never mixed
    assert AD.truth_column_for("P1") == AD.truth_column_for("P2") == "n_p35_prim" and AD.truth_column_for("P3") == AD.truth_column_for("P4") == "n_p50"
    m = pd.read_csv(TAB / "proton_policy_truth_reco_matrices.csv")
    for p in ("P1", "P2"):
        assert list(m[m.policy == p].groupby("truth").n.sum().reindex(["truth 0p", "truth 1p", "truth >=2p"])) == [476, 594, 83]      # 35 MeV truth composition of the 1,153
    for p in ("P3", "P4"):
        assert list(m[m.policy == p].groupby("truth").n.sum().reindex(["truth 0p", "truth 1p", "truth >=2p"])) == [527, 570, 56]      # 50 MeV truth composition
    mm = pd.read_csv(TAB / "proton_policy_migration_mechanisms.csv")
    for (p, d), g in mm.groupby(["policy", "direction"]):
        assert int(g.n.sum()) == int(g.n_reco.iloc[0])                                                                         # exact closure of the 1p->0p and 0p->1p accounting
        n_mat = int(m[(m.policy == p) & (m.truth == ("truth 1p" if d.startswith("truth1p") else "truth 0p")) & (m.reco == ("1g0p" if d.startswith("truth1p") else "1g1p"))].n.iloc[0]); assert int(g.n.sum()) == n_mat
    assert int(mm[(mm.policy == "P1") & (mm.reason == "proton_row_excluded_by_included3_policy")].n.sum()) == 0 and int(mm[(mm.policy == "P2") & (mm.reason == "proton_row_excluded_by_included3_policy")].n.sum()) == 26      # the new reason exists only when the policy excludes included==3


def test_p1_reproduces_the_frozen_baseline_and_no_flag_changed():
    P = pd.read_csv(TAB / "proton_policy_comparison.csv").set_index("policy"); assert (P.loc["P1", "final_1g0p"], P.loc["P1", "final_1g1p"], P.loc["P1", "final_1gNp"]) == (527, 556, 70)
    m = pd.read_csv(TAB / "proton_policy_truth_reco_matrices.csv"); p1 = m[m.policy == "P1"].pivot(index="truth", columns="reco", values="n")
    assert p1.loc["truth 0p"].tolist() == [425, 50, 1] and p1.loc["truth 1p"].tolist() == [93, 471, 30] and (p1.loc["truth >=2p"].sum() == 83)               # the validated 3x3 migration
    assert S["metadata"]["baseline_config_sha256"].startswith("f3251b78")
    pk = pd.read_csv(TAB / "package_rates_and_headlines.csv").set_index("package"); assert pk.loc["baseline_frozen", "selected_signal"] == 1153 and pk.loc["baseline_frozen", "B_beam_selected"] == 635
    assert pk.loc["baseline_frozen", "truth_denominator"] == 12427


def test_any_first_overlap_and_event_counted_once():
    o = AD.overlap_table([1, 1, 0, 0, 1], [1, 0, 0, 0, 1]); assert o == dict(both=2, any_only=1, first_only=0, neither=2, n_any=3, n_first=2, n_events=5)
    ov = pd.read_csv(TAB / "candidate_policy_event_overlap.csv").set_index("sample")
    assert (ov.loc["official_signal", "both"], ov.loc["official_signal", "any_only"], ov.loc["official_signal", "first_only"]) == (1101, 52, 0)       # exactly as established in Phase 11
    assert (ov.loc["bnb_cv_all_selected", "both"], ov.loc["bnb_cv_all_selected", "any_only"], ov.loc["bnb_cv_all_selected", "first_only"]) == (626, 23, 0)
    assert (ov.first_only == 0).all() and (ov.n_any == ov.both + ov.any_only).all() and (ov.n_first == ov.both).all()
    c = pd.read_csv(TAB / "event_counting_check.csv"); assert (c.events_with_2plus_passing_candidates == 0).all() and (c.max_passing_per_event == 1).all()    # a selected event counts once
    a = pd.read_csv(TAB / "any_only_events_summary.csv"); s = a[(a["sample"] == "official_signal") & (a.variable == "passing_cand_is_signal_matched")].iloc[0]; assert s.n == 52 and s.frac == 1.0
    assert int(a[(a["sample"] == "official_signal") & (a.variable == "same_truth_neutrino") & (a.value == "False")].n.iloc[0]) == 52


def test_first_stage_failure_helper():
    row = {c: True for c in AD.FIRST_FAIL_ORDER}; assert AD.first_failed_stage(row) == "passes all frozen cuts"
    row["cum_single_photon_numu_score_gt_0p4"] = False; row["cum_single_photon_other_score_gt_0p2"] = False; assert AD.first_failed_stage(row) == "numu"
    row["cum_n_20mev_showers_gt0"] = False; assert AD.first_failed_stage(row) == "no > 20 MeV shower"


def test_policy_envelope_bookkeeping_and_no_quadrature():
    r = AD.envelope_row("pkg", dict(a=10.0, b=3, c="x"), dict(a=8.0, b=3, c="x")); assert r["d_a"] == 2.0 and r["d_b"] == 0 and "d_c" not in r
    env = pd.read_csv(TAB / "policy_envelope.csv").set_index("package"); assert env.loc["av200_P1_any", [c for c in env.columns if c.startswith("d_")]].abs().max() == 0       # the reference differs from itself by zero
    assert len(env) == len(CFG["packages"]) == 12 and not any(k in c.lower() for c in env.columns for k in ("quadrature", "total_unc", "syst", "combined"))
    # one-factor packages: each differs from the reference in exactly one respect
    keys = ["truth_fv", "proton_policy", "candidate_policy"]; ref = env.loc["av200_P1_any"]
    for k, r in env.iterrows():
        if k in ("baseline_frozen", "spine_comparable_FV180_P3_any"):
            continue
        assert sum(r[c] != ref[c] for c in keys) <= 1
    assert env.loc["av200_P1_first", "d_signal_efficiency"] < 0 and AD.rates_per_1e20(100, 2e20) == 50.0


def test_no_cosmic_normalisation_purity_or_significance_introduced():
    assert "blocked" in S["metadata"]["no_cosmic_normalisation"] and S["metadata"]["flash_time_shift"] == "none applied"
    for f in TAB.glob("*.csv"):
        cols = [c.lower() for c in pd.read_csv(f, nrows=1).columns]
        assert not any(k in c for c in cols for k in ("purity", "significance", "beam_off", "beamoff", "cosmic_norm"))
    pk = pd.read_csv(TAB / "package_rates_and_headlines.csv"); assert any(c.startswith("signal_over_beam_neutrino_background_reference") for c in pk.columns) and not any(c in ("S_over_B", "purity") for c in pk.columns)
    assert np.isnan(AD.reference_ratio(1.0, 0.0)) and abs(AD.reference_ratio(1.0, 4.0) - 0.25) < 1e-12
    for d in ("ANALYSIS_DEFINITION_DECISION_SUPPORT.md", "FIDUCIAL_VOLUME_DECISION_AUDIT.md", "ANALYSIS_READINESS_BLOCKERS.md"):
        t = (ROOT / "docs" / "analysis" / d).read_text(); assert "S/B" in t or "S / B" in t or "reference ratio" in t
    assert "BLOCKED" in (ROOT / "docs" / "analysis" / "ANALYSIS_READINESS_BLOCKERS.md").read_text()


def test_config_packages_are_alternatives_not_defaults():
    assert "provisional_recommended" not in json.dumps(CFG["packages"])
    assert CFG["provisional_conventions"]["D_fiducial_volume"]["recommendation"] == "NO_RECOMMENDATION" and CFG["provisional_conventions"]["F_candidate_policy"]["recommendation"].startswith("any")
    for name, p in CFG["packages"].items():
        assert p["truth_fv"] in AD.FV_SPECS and p["reco_fv"] in AD.FV_SPECS and p["proton_policy"] in AD.PROTON_PACKAGES and p["candidate_policy"] in ("any", "first")
    base = yaml.safe_load(open(ROOT / "configs" / "baseline_selection.yaml")); assert base["fiducial_volume"]["applied"] is False and base["candidate_policy"] == "any"       # the baseline config is untouched
