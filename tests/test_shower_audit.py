"""Photon-shower / vertex reconstruction audit: geometry, taxonomy exclusivity and accounting identities (synthetic + pinned committed summaries)."""
import json
from pathlib import Path
import numpy as np
import pytest
from sbnd_single_photon import shower_audit as SA

REPO = Path(__file__).resolve().parents[1]


def test_conversion_point_geometry_and_decomposition():
    V = np.array([0.0, 0.0, 0.0]); u = np.array([0.0, 0.0, 2.0]); C = V + 10 * u / 2
    r = SA.decompose_vertex([1.0, 0.0, 4.0], V, C, u)
    assert abs(r["parallel"] - 4.0) < 1e-12 and abs(r["perp"] - 1.0) < 1e-12 and abs(r["d_vertex"] - np.sqrt(17)) < 1e-12 and abs(r["d_conv_true"] - 10.0) < 1e-12
    assert abs(r["frac_axis"] - 0.4) < 1e-12 and abs(r["d_conv"] - np.sqrt(1 + 36)) < 1e-12
    r0 = SA.decompose_vertex(C, V, C, u); assert abs(r0["frac_axis"] - 1.0) < 1e-12 and r0["d_conv"] == 0.0 and r0["perp"] == 0.0
    assert np.isnan(SA.decompose_vertex([1, 0, 0], V, V, u)["frac_axis"])               # zero conversion distance: axis undefined


def test_decomposition_pythagoras_for_random_points():
    rng = np.random.default_rng(1)
    for _ in range(50):
        V, C, R = rng.normal(size=3) * 50, rng.normal(size=3) * 50, rng.normal(size=3) * 50; u = C - V
        r = SA.decompose_vertex(R, V, C, u)
        assert abs(r["parallel"] ** 2 + r["perp"] ** 2 - r["d_vertex"] ** 2) < 1e-8


def test_proximity_classes():
    assert SA.classify_proximity(1.0, 14.0, 15.0) == "interaction_vertex" and SA.classify_proximity(14.0, 1.0, 15.0) == "conversion_point"
    assert SA.classify_proximity(30.0, 30.0, 15.0) == "neither" and SA.classify_proximity(8.0, 9.0, 15.0) == "between"
    assert SA.classify_proximity(1.0, 2.0, 3.0) == "not_separable" and SA.classify_proximity(np.nan, 1.0, 15.0) == "undefined"


def test_distance_to_boundary_and_counting_rule():
    assert SA.distance_to_boundary(0, 0, 250) == 200.0 and SA.distance_to_boundary(195, 0, 250) == 5.0 and SA.distance_to_boundary(0, 0, 3) == 3.0
    assert SA.counted_by_sp(21.0, True, 11) and not SA.counted_by_sp(20.0, True, 11) and not SA.counted_by_sp(300.0, False, 11) and not SA.counted_by_sp(300.0, True, 2212)


def test_failure_taxonomy_is_exclusive_exhaustive_and_ordered():
    f = SA.classify_failure
    cases = [dict(q_total=0, q_in_cands=0, dominant_fraction=0, dominant_in_signal_candidate=True, has_kine_row=True, is_shower=True, pdg=11, e_reco_mev=100, want="photon_no_reco_charge"),
             dict(q_total=10, q_in_cands=2, dominant_fraction=1, dominant_in_signal_candidate=True, has_kine_row=True, is_shower=True, pdg=11, e_reco_mev=100, want="photon_charge_outside_candidates"),
             dict(q_total=10, q_in_cands=9, dominant_fraction=0.4, dominant_in_signal_candidate=True, has_kine_row=True, is_shower=True, pdg=11, e_reco_mev=100, want="photon_fragmented"),
             dict(q_total=10, q_in_cands=9, dominant_fraction=0.9, dominant_in_signal_candidate=False, has_kine_row=True, is_shower=True, pdg=11, e_reco_mev=100, want="photon_in_other_candidate"),
             dict(q_total=10, q_in_cands=9, dominant_fraction=0.9, dominant_in_signal_candidate=None, has_kine_row=False, is_shower=True, pdg=11, e_reco_mev=100, want="photon_particle_row_missing"),
             dict(q_total=10, q_in_cands=9, dominant_fraction=0.9, dominant_in_signal_candidate=True, has_kine_row=True, is_shower=False, pdg=2212, e_reco_mev=100, want="photon_as_track"),
             dict(q_total=10, q_in_cands=9, dominant_fraction=0.9, dominant_in_signal_candidate=True, has_kine_row=True, is_shower=True, pdg=2212, e_reco_mev=100, want="photon_shower_typed_non_electron"),
             dict(q_total=10, q_in_cands=9, dominant_fraction=0.9, dominant_in_signal_candidate=True, has_kine_row=True, is_shower=True, pdg=11, e_reco_mev=20.0, want="photon_shower_below_20MeV"),
             dict(q_total=10, q_in_cands=9, dominant_fraction=0.9, dominant_in_signal_candidate=True, has_kine_row=True, is_shower=True, pdg=11, e_reco_mev=20.01, want="photon_shower_not_in_main_vertex_set")]
    got = set()
    for c in cases:
        want = c.pop("want"); g = f(**c); assert g == want and g in SA.FAIL_CLASSES; got.add(g)
    assert got == set(SA.FAIL_CLASSES)                                              # every class is reachable and the list is closed


def test_pf_attachment_states():
    assert SA.pf_attachment_state(False, 0, False, -1) == "none" and SA.pf_attachment_state(True, 0, False, -1) == "root"
    assert SA.pf_attachment_state(True, 1, True, -1) == "photon_node_at_vertex" and SA.pf_attachment_state(True, 2, True, 45017) == "deeper" and SA.pf_attachment_state(True, 1, False, -1) == "deeper"


# ---------------------------------------------------------------------------------------------------------------------------- association on a synthetic event, and pinned committed summaries
import pandas as pd
from sbnd_single_photon import shower_tables as ST

SUM = REPO / "tables" / "shower_vertex_audit" / "summary.json"
needs_summary = pytest.mark.skipif(not SUM.exists(), reason="shower/vertex audit summary not generated")


def _raw():
    cand = pd.DataFrame(dict(file_index=0, ev=0, cand_pos=[0, 1], nu_index=[0.0, 1.0]))
    kine = pd.DataFrame(dict(file_index=0, ev=0, cand_pos=[0, 0, 1], row=[0, 1, 0], kine_particle_id=[10.0, 11.0, 20.0], kine_particle_type=[2212.0, 11.0, 13.0], kine_energy_particle=[80.0, 300.0, 40.0],
                             kine_particle_is_shower=[0.0, 1.0, 0.0], kine_particle_pool=[0.0, 2.0, 0.0], kine_energy_included=[1.0, 1.0, 1.0]))
    pf = pd.DataFrame(dict(file_index=0, ev=0, nu_index=[0.0, 0.0, 0.0, 0.0], node_id=[10.0, 1.0, 11.0, 5.0], parent_id=[-1.0, 10.0, 1.0, -1.0], depth=[0.0, 1.0, 2.0, 0.0], pdg=[2212.0, 22.0, 11.0, 13.0],
                           ke_mev=[80, 300, 300, 5.0], kine_index=[0.0, -1.0, 1.0, -1.0], is_pseudo=[0.0, 1.0, 0.0, 0.0], start_x=0.0, start_y=0.0, start_z=0.0, end_x=0.0, end_y=0.0, end_z=0.0, n_children=0.0))
    po = pd.DataFrame(dict(file_index=0, ev=0, nu_index=[0, 0, 1, -1], particle_id=[11, 11, 20, 99], kine_index=[1, 1, 0, -1], q=[600.0, 200.0, 100.0, 100.0]))   # candidate 0 holds 800 (row 1), candidate 1 holds 100, 100 outside
    truth = pd.DataFrame(dict(file_index=[0], ev=[0], photon_found=[True]))
    return dict(cand=cand, kine=kine, pf=pf, pho_ov=po, truth=truth)


def test_photon_association_dominant_object_and_charge_bookkeeping():
    a = ST.photon_association(_raw()); assert len(a) == 1; r = a.iloc[0]
    assert r.q_total == 1000.0 and r.q_in_cands == 900.0 and r.dom_nu == 0 and r.dom_row == 1 and abs(r.dominant_fraction - 800 / 900) < 1e-12 and r.n_cand_with_photon == 2
    assert r.has_kine_row and r.kine_particle_type == 11 and r.kine_particle_is_shower == 1 and r.pf_state == "deeper"                 # electron shower below a pseudo node below a proton: not at the root
    assert SA.classify_failure(r.q_total, r.q_in_cands, r.dominant_fraction, True, True, True, 11, r.kine_energy_particle) == "photon_shower_not_in_main_vertex_set"


@needs_summary
def test_exact_3251_accounting_and_exclusive_classes():
    s = json.loads(SUM.read_text()); a = s["accounting"]
    assert (a["denominator_tpc_box"], a["candidate_stage"], a["pass_n20"], a["fail_n20"]) == (12427, 11331, 8080, 3251) and a["fail_classes_sum"] == a["baseline_first_fail_no_20mev_shower"] == 3251
    assert sum(a["by_class"].values()) == 3251 and set(a["by_class"]) <= set(SA.FAIL_CLASSES)
    T = pd.DataFrame(s["taxonomy"])
    for g, d in T.groupby("group"):
        assert d.n.sum() == d.n_candidate_stage.iloc[0]                                  # every outcome set closes in every group (exclusive and exhaustive)
        assert d[d.outcome.isin(SA.FAIL_CLASSES)].n.sum() == d.n_failing.iloc[0]
    assert a["missing_production_event_in_population"] == 0                              # the one missing production event has no candidate: it stays in the 12,427, not in the 11,331


@needs_summary
def test_truth_class_totals_and_baseline_decisions_unchanged():
    s = json.loads(SUM.read_text()); T = pd.DataFrame(s["taxonomy"]); n = T.groupby("group").n_candidate_stage.first()
    assert n["all"] == n["truth 0p"] + n["truth 1p"] + n["truth >=2p"] == n["Delta0"] + n["Delta+"] == 11331
    assert s["final_selected_photon_object"]["n"] == 1153                                # the baseline final selection (any) is untouched
    import hashlib
    assert hashlib.sha256((REPO / "configs" / "baseline_selection.yaml").read_bytes()).hexdigest() == "f3251b785be6e52ff3e429000a0319a6df8e42d2016ace2f51c7650a38e2fb0b"


@needs_summary
def test_pf_state_validation_against_the_tagger_gap_is_pinned():
    v = json.loads(SUM.read_text())["pf_state_vs_tagger_gap"]           # {attached(True)/detached(False): {pf state: n}}
    assert v["False"]["photon_node_at_vertex"] > 2000 and v["True"].get("photon_node_at_vertex", 0) == 0
    assert v["True"]["root"] / (v["True"]["root"] + v["False"]["root"]) > 0.98


@needs_summary
def test_proton_origin_join_closes_and_energy_counting_closes():
    s = json.loads(SUM.read_text()); h = pd.DataFrame(s["hadronic"]); allr = h[h.delta == "all"]
    T = pd.DataFrame(s["taxonomy"]); n1 = int(T[(T.group == "truth 1p")].n_candidate_stage.iloc[0])
    assert int(allr.n_events.sum()) == n1 == 5170                                       # every truth-1p candidate-stage event has exactly one origin class
    for r in s["energy_response"]:
        assert r["n_counted"] + r["n_not_counted"] == r["n_dominant_electron_shower"] and r["n_dominant_electron_shower"] <= r["n_candidate_stage"]


@needs_summary
def test_vertex_decomposition_summary_is_consistent():
    s = json.loads(SUM.read_text()); d = pd.DataFrame(s["vertex_distributions"]).pivot(index="variable", columns="group", values="median")
    assert d.loc["parallel", "truth 0p"] > 10 > abs(d.loc["parallel", "truth 1p"]) and abs(d.loc["perp", "truth 0p"] - d.loc["perp", "truth 1p"]) < 0.5
    assert s["vertex_events"]["anchored5_by_class"]["truth 1p"] > 3 * s["vertex_events"]["anchored5_by_class"]["truth 0p"]
