"""Common NC-Delta reconstructed observables (Phase 11): synthetic checks of the helpers and pinned checks of the committed summary tables.

Nothing here changes a selection flag, threshold or policy; signal-vs-background comparisons are unit-area shape diagnostics only (no rates).
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from sbnd_single_photon import observables as OB

ROOT = Path(__file__).resolve().parents[1]
TAB = ROOT / "tables" / "common_observables"
S = json.load(open(TAB / "summary.json"))
P10 = json.load(open(ROOT / "tables" / "proton_truth_association" / "summary.json"))
MP = OB.M_PROTON_MEV


def _four(m, p):
    p = np.asarray(p, float); return np.append(p, np.sqrt(m * m + p @ p))


def test_delta_mass_formula_matches_the_invariant_mass_of_two_four_vectors():
    rng = np.random.default_rng(1)
    for _ in range(200):
        g = rng.normal(size=3); g = g / np.linalg.norm(g) * rng.uniform(50, 800)           # photon momentum [MeV]
        p = rng.normal(size=3); p = p / np.linalg.norm(p) * rng.uniform(100, 1200)         # proton momentum [MeV]
        ke = np.sqrt(MP ** 2 + p @ p) - MP; eg = np.linalg.norm(g); cosgp = (g @ p) / (np.linalg.norm(g) * np.linalg.norm(p))
        m, ok = OB.delta_mass(eg, ke, cosgp)
        assert bool(ok) and abs(float(m) - OB.invariant_mass(np.append(g, eg), _four(MP, p))) < 1e-6
    # proton at rest: M^2 = m_p^2 + 2 E_gamma m_p ; PDG mass constant
    m, ok = OB.delta_mass(100.0, 0.0, 0.3); assert abs(float(m) ** 2 - (MP ** 2 + 2 * 100.0 * MP)) < 1e-6 and abs(MP - 938.27208816) < 1e-9


def test_positive_mass_handling_and_unit_conversion_of_the_rule():
    m, ok = OB.delta_mass(np.array([-1000.0, np.nan, 200.0]), np.array([100.0, 100.0, np.nan]), np.array([0.1, 0.1, 0.1]))
    assert not ok.any() and np.isnan(m).all()                                              # M^2 <= 0 or missing input: NaN, never clipped to 0
    m, ok = OB.delta_mass(np.array([300.0]), np.array([150.0]), np.array([0.14])); assert ok[0] and 900 < m[0] < 2000
    assert np.isnan(OB.delta_mass2(np.nan, 1.0, 0.0))


def test_deterministic_object_choice_never_uses_truth():
    rows = pd.DataFrame(dict(row=[3, 1, 2, 0], kine_particle_type=[2212, 2212, 2212, 11], kine_energy_particle=[120.0, 120.0, 80.0, 400.0], kine_energy_included=[1, 3, 1, 1], kine_particle_is_shower=[0, 1, 0, 1]))
    lead = OB.leading_proton_row(OB.proton_rows(rows, OB.PROTON_POLICIES["baseline_35"])); assert int(lead.row) == 1             # tie in KE -> lowest row index
    assert OB.leading_proton_row(OB.proton_rows(rows.sample(frac=1, random_state=3), OB.PROTON_POLICIES["baseline_35"])).row == 1   # independent of row order
    assert int(OB.leading_proton_row(OB.proton_rows(rows, OB.PROTON_POLICIES["35_excl_included3"])).row) == 3                      # included==3 row excluded by the sensitivity
    assert len(OB.proton_rows(rows, OB.PROTON_POLICIES["50"])) == 3 and OB.leading_proton_row(rows.iloc[0:0]) is None
    low = pd.concat([rows, pd.DataFrame(dict(row=[9], kine_particle_type=[2212], kine_energy_particle=[40.0], kine_energy_included=[1], kine_particle_is_shower=[0]))])
    assert len(OB.proton_rows(low, OB.PROTON_POLICIES["baseline_35"])) == 4 and len(OB.proton_rows(low, OB.PROTON_POLICIES["50"])) == 3        # a 40 MeV row passes 35 and fails 50
    assert OB.reco_channel(0) == "1g0p" and OB.reco_channel(1) == "1g1p" and OB.reco_channel(2) == "1gNp"
    ph = OB.select_photon_row(rows, 400.0, 1.0); assert int(ph.row) == 0 and OB.select_photon_row(rows, 400.0, 0.0) is None and OB.select_photon_row(rows, 123.0, 1.0) is None


@pytest.mark.parametrize("pc,tc,dpdg,oc,expect", [
    (True, "true_primary_signal_proton", 2214, "decay_proton", "decay_pair"),
    (True, "true_primary_signal_proton", 2114, "decay_proton", "fsi_or_other_primary"),       # Delta0: the decay nucleon is a neutron, never a decay pair
    (True, "true_primary_signal_proton", 2214, "fsi_created", "fsi_or_other_primary"),
    (True, "geant4_secondary_proton", 2214, "", "secondary_proton"),
    (True, "signal_nonproton_misidentified", 2214, "", "fake_or_other"),
    (True, "absent", 2214, "", "fake_or_other"),
    (False, "true_primary_signal_proton", 2214, "decay_proton", "photon_wrong")])
def test_truth_correct_delta_pair_classification(pc, tc, dpdg, oc, expect):
    assert OB.pair_class(pc, tc, tc, dpdg, oc) == expect and expect in OB.PAIR_CLASSES


def test_direction_normalisation_and_chord_without_truth_flipping():
    assert np.isnan(OB.unit([0, 0, 0])).all() and np.isnan(OB.unit([np.inf, 0, 0])).all()
    rng = np.random.default_rng(2); v = rng.normal(size=(50, 3)); assert np.allclose([np.linalg.norm(OB.unit(x)) for x in v], 1.0)
    pf = pd.DataFrame(dict(kine_index=[4, 4], is_pseudo=[1, 0], depth=[1, 2], start_x=[0, 1.0], start_y=[0, 2.0], start_z=[0, 3.0], end_x=[0, 1.0], end_y=[0, 2.0], end_z=[0, 13.0]))
    s, e, d, L = OB.pf_chord(pf, 4); assert np.allclose(d, [0, 0, 1]) and abs(L - 10) < 1e-12                                     # the pseudo node is skipped
    assert OB.pf_chord(pf, 9) is None and abs(OB.cos_between([0, 0, 1], [0, 0, -1]) + 1) < 1e-12 and np.isnan(OB.cos_between([np.nan, 0, 0], [1, 0, 0]))
    s2, e2, d2 = OB.orient_from_vertex([0, 0, 10.0], [0, 0, 0.0], [0, 0, 1.0]); assert np.allclose(d2, [0, 0, 1])                  # reco-only orientation away from the vertex
    st = OB.resolution_stats([1, 2, 3, 4, 100]); assert st["n"] == 5 and st["median"] == 3 and OB.resolution_stats([np.nan])["n"] == 0


def test_photon_energy_resolution_accounting():
    o = S["objects"]; pe = S["photon_energy"]
    assert o["signal_any"] == 1153 and o["photon_row_found"] == 1151 and o["photon_correct"] == 1148
    assert pe["n"] == o["photon_correct"] and pe["excluded_photon_not_signal"] == o["signal_any"] - o["photon_correct"] and pe["excluded_no_row"] == o["signal_any"] - o["photon_row_found"]
    r = pd.read_csv(TAB / "photon_energy_response.csv"); assert int(r[r.split == "all"].n.iloc[0]) == 1148
    for sp in ("e_bin", "conv_bin", "topo", "state", "delta_label"):
        n = int(r[r.split == sp].n.sum())
        assert n <= 1148 and (sp in ("e_bin", "conv_bin") or n == 1148)                                                           # conv_bin keeps in-volume conversions only; e_bin excludes < 20 MeV edges


def test_proton_response_join_agrees_with_phase10_row_level_association():
    r = pd.read_csv(TAB / "proton_ke_response_selected_1g1p.csv"); n = int(r[r.split == "all"].n.iloc[0])
    assert n == P10["delta_readiness"]["proton_truth_correct"] == 493                         # the truth-correct proton rows of the 556 selected 1g1p events are the same rows
    assert S["objects"]["channels_any"]["baseline_35"] == {"1g1p": 556, "1g0p": 527, "1gNp": 70}
    assert S["proton_kinematics"]["n_1g1p"] == 556 and S["objects"]["mass_status"]["baseline_35"]["ok"] == P10["delta_readiness"]["m_delta2_defined"] == 554


def test_policy_sensitivity_leaves_frozen_selection_untouched_and_closes():
    p = pd.read_csv(TAB / "policy_decision_support.csv"); a = p[p.candidate_policy == "any"]
    assert set(a.selected_events) == {1153}                                                  # the single-photon selection is identical under every proton policy
    assert ((a.n_1g0p + a.n_1g1p + a.n_1gNp) == 1153).all() and ((p[p.candidate_policy == "first"].n_1g0p + p[p.candidate_policy == "first"].n_1g1p + p[p.candidate_policy == "first"].n_1gNp) == 1101).all()
    rc = pd.read_csv(TAB / "proton_policy_reclassification_any.csv")
    for v, g in rc.groupby("proton_policy"):
        assert int(g.n.sum()) == 1153
    b = rc[rc.proton_policy == "baseline_35"]; assert (b[b.baseline_channel != b.variant_channel].n == 0).all()
    assert S["metadata"]["baseline_config_sha256"].startswith("f3251b78")
    ex = rc[(rc.proton_policy == "35_excl_included3") & (rc.baseline_channel == "1g1p") & (rc.variant_channel == "1g0p")].n.iloc[0]; assert int(ex) == 63


def test_any_vs_first_accounting():
    a = S["policy"]["any_vs_first"]
    assert a["events_any"] == 1153 and a["events_first"] == 1101 and a["in_both"] + a["only_any"] == 1153 and a["in_both"] + a["only_first"] == 1101
    assert a["same_candidate"] + a["different_candidate"] == a["in_both"] and a["only_first"] == 0
    assert sum(a["only_any_truth35"].values()) == a["only_any"]


def test_common_observable_table_completeness():
    expected = ["generator_delta_decay_mass.csv", "delta_mass_signal_subsets.csv", "delta_mass_resolution_decay_pairs.csv", "delta_mass_substitution_study.csv", "photon_energy_response.csv", "photon_direction_resolution.csv",
                "shower_gap_vs_conversion_distance.csv", "signal_vs_background_shape_summary.csv", "proton_ke_response_selected_1g1p.csv", "reco_enu_response.csv", "vertex_resolution_selected_signal.csv", "policy_decision_support.csv",
                "any_vs_first_comparison.csv", "natural_cv_vs_official_signal.csv", "selected_object_counts_not_rates.csv"]
    assert all((TAB / f).exists() for f in expected)
    sh = pd.read_csv(TAB / "signal_vs_background_shape_summary.csv"); assert {"e_gamma", "gap", "dedx", "dqdx0", "enu", "vx", "vy", "vz", "m_delta", "cos_gp", "p_ke"} <= set(sh.observable)
    plots = [p.name for p in (ROOT / "plots" / "common_observables").glob("*.png")]; assert len(plots) >= 12
    g = pd.read_csv(TAB / "generator_delta_decay_mass.csv").set_index("sample"); assert g.loc["all", "n"] == 12426 and abs(g.loc["all", "mode_mev"] - 1232.5) < 5 and g.loc["all", "delta_record_equals_decay_pair"] == 1.0


def test_no_background_rate_claims_introduced():
    for f in ("signal_vs_background_shape_summary.csv", "selected_object_counts_not_rates.csv", "bnb_selected_objects_by_proton_policy.csv"):
        cols = [c.lower() for c in pd.read_csv(TAB / f).columns]; assert not any(k in c for c in cols for k in ("rate", "purity", "s_over_b", "yield", "weight", "pot"))
    doc = (ROOT / "docs" / "analysis" / "NCDELTA_COMMON_RECO_OBSERVABLES.md").read_text()
    assert "never a rate, purity or S/B" in doc and "not rates" in doc.lower()
    assert "no common FV" in S["metadata"]["no_rate_claims"] or "unit-area shapes only" in S["metadata"]["no_rate_claims"]
