"""Phase 15: Wire-Cell particle typing audit (roadmap S and X): synthetic checks of the source-rule predicates and taxonomies, and pinned checks of the committed tables.

Nothing here changes a selection flag, threshold, PID or reconstructed type.
"""
import hashlib
import itertools
import json
import re
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from sbnd_single_photon import pid_audit as PI

ROOT = Path(__file__).resolve().parents[1]
TAB = ROOT / "tables" / "particle_pid_audit"
csv = lambda n: pd.read_csv(TAB / f"{n}.csv")
SRC_REPO = Path("/exp/sbnd/app/users/yuhw/wct-pr543")


# ------------------------------------------------------------------------------------------------------------ source rules
def _src(f):
    return subprocess.run(["git", "-c", "safe.directory=*", "show", f"{PI.SOURCE_COMMIT}:clus/src/{f}"], cwd=SRC_REPO, capture_output=True, text=True, timeout=60).stdout


@pytest.mark.skipif(not SRC_REPO.exists(), reason="producer source checkout not on this machine")
def test_source_constants_match_the_pinned_source():
    t = _src("PRSegmentFunctions.cxx")
    if not t:
        pytest.skip("pinned commit not readable")
    assert "medium_dQ_dx > MIP_dQdx * 1.75" in t and "medium_dQ_dx < MIP_dQdx * 1.2" in t and "medium_dQ_dx < MIP_dQdx * 1.5 && length < 4*units::cm" in t        # median fallback
    assert "result_forward.at(3) < min_forward_val && length < 20*units::cm" in t                                                                              # electron template only below 20 cm
    assert "length > 10*units::cm && particle_score > 1.0 && particle_score < 100" in t                                                                        # bad score -> shower
    assert "length < 1.5*units::cm && (start_n == 1 || end_n == 1)" in t and "if (particle_score < 0.15) pdg_code = 13;" in t
    assert "start_n == 1 && end_n == 1 && npoints >= 15" in t and "35*units::cm" in t and "15*units::cm" in t
    v = _src("NeutrinoVertexFinder.cxx")
    assert "Find muon candidate and make others pions" in v and "Convert non-muon candidates to pions" in v and "if (sg_length > muon_length && n_proton == 0 && !chain_proton)" in v


def test_source_rule_table_is_complete_and_ordered():
    steps = [r["step"] for r in PI.SOURCE_RULES]; assert steps == list(range(1, len(steps) + 1)) and len(steps) == 13
    for r in PI.SOURCE_RULES:
        assert all(k in r for k in ("stage", "what", "where", "inputs", "persisted")) and re.search(r"\.cxx", r["where"])
    assert any("pion" in r["what"].lower() or "PION" in r["what"] for r in PI.SOURCE_RULES) and "per-segment dQ/dx vector and its median" in PI.NOT_PERSISTED


def test_median_fallback_and_template_and_bad_score_predicates():
    assert PI.median_fallback_type(1.8, 10) == 2212 and PI.median_fallback_type(1.1, 10) == 13 and PI.median_fallback_type(1.3, 10) == 0
    assert PI.median_fallback_type(1.4, 3.9) == 13 and PI.median_fallback_type(1.4, 4.0) == 0 and PI.median_fallback_type(1.75, 10) == 0 and PI.median_fallback_type(1.2, 10) == 0   # strict inequalities
    assert PI.template_type(0.5, 0.6, 0.7, 10) == 13                                    # muon is the default
    assert PI.template_type(0.5, 0.4, 0.7, 10) == 2212 and PI.template_type(0.5, 0.5, 0.7, 10) == 13          # proton only if strictly smaller
    assert PI.template_type(0.5, 0.6, 0.3, 19.9) == 11 and PI.template_type(0.5, 0.6, 0.3, 20.0) == 13        # electron only below 20 cm
    assert PI.bad_score_becomes_shower(10.1, 1.5) and not PI.bad_score_becomes_shower(10.0, 1.5) and not PI.bad_score_becomes_shower(15, 1.0) and not PI.bad_score_becomes_shower(15, 100.0)
    assert PI.vertex_activity_type(1.0, 2.0, 3) == 2212 and PI.vertex_activity_type(1.0, 1.0, 3) == 211 and PI.vertex_activity_type(1.0, 1.5, 3) is None
    assert PI.vertex_activity_type(1.5, 2.0, 3) is None and PI.vertex_activity_type(1.0, 2.0, 2) is None


def test_main_vertex_muon_pion_arbitration_semantics():
    m, pions = PI.muon_pion_arbitration([("a", 10.0, False), ("b", 30.0, False), ("c", 20.0, False)])
    assert m == "b" and pions == ["a", "c"]                                             # the longest stays muon, every other becomes a pion
    m, pions = PI.muon_pion_arbitration([("a", 10.0, False), ("b", 30.0, True)])
    assert m == "a" and pions == ["b"]                                                  # a candidate whose far end has a proton neighbour never wins
    m, pions = PI.muon_pion_arbitration([("a", 20.0, False), ("b", 20.0, False)])
    assert m == "a" and pions == ["b"]                                                  # a tie keeps the first
    assert PI.muon_pion_arbitration([("a", 5.0, True)]) == (None, ["a"]) and PI.muon_pion_arbitration([]) == (None, [])
    for n in range(1, 6):                                                               # at most ONE muon is ever kept
        m, pions = PI.muon_pion_arbitration([(i, 3.0 + i, False) for i in range(n)]); assert (m is not None) and len(pions) == n - 1


# ------------------------------------------------------------------------------------------------------------ taxonomies
def test_reco_type_class_is_exclusive_and_exhaustive():
    for pdg, sh in itertools.product([11, -11, 13, -13, 211, -211, 2212, 22, 0, 321], [True, False]):
        c = PI.reco_type_class(pdg, sh); assert c in PI.TYPE_CLASSES
    assert PI.reco_type_class(11, True) == "e-shower" and PI.reco_type_class(-11, False) == "e-track" and PI.reco_type_class(-13, True) == "mu-like" and PI.reco_type_class(2212, True) == "proton-like"
    assert PI.reco_type_class(np.nan, True) == "no row" and PI.reco_type_class(321, False) == "other"


def test_photon_population_taxonomy_is_exclusive_and_exhaustive():
    states = ["photon_no_reco_charge", "photon_charge_outside_candidates", "photon_in_other_candidate", "photon_fragmented", "photon_particle_row_missing", "photon_as_track", "photon_shower_typed_non_electron", "photon_shower_below_20MeV", "photon_shower_not_in_main_vertex_set"]
    outcomes = ["pass_photon_shower_in_passing_candidate", "pass_not_via_signal_photon_shower", "photon_as_track"]; seen = set()
    for s, o, t in itertools.product(states, outcomes, ["e-shower", "e-track", "mu-like", "pi-like", "proton-like", "other", "no row"]):
        c = PI.photon_pid_class(s, o, t); assert c in PI.PHOTON_CLASSES; seen.add(c)
    assert seen == set(PI.PHOTON_CLASSES)
    assert PI.photon_pid_class("photon_fragmented", "x", "mu-like") == PI.PHOTON_CLASSES[6]            # fragmented stays class G whatever the dominant type
    assert PI.photon_pid_class("photon_shower_not_in_main_vertex_set", "pass_photon_shower_in_passing_candidate", "e-shower") == PI.PHOTON_CLASSES[0]


def test_proton_class_and_merge_destination_taxonomy():
    assert PI.proton_reco_class(["proton-like", "mu-like"], [], True) == "proton-typed" and PI.proton_reco_class(["mu-like"], ["e-shower"], True) == "mu-typed"
    assert PI.proton_reco_class([], ["e-shower"], True) == "merged / subdominant partner" and PI.proton_reco_class([], [], True) == "no row" and PI.proton_reco_class(["e-shower"], [], False) == "no signal-matched candidate"
    for top, sub, insig in itertools.product([[], ["e-shower"], ["e-track"], ["mu-like"], ["pi-like"], ["proton-like"], ["other"]], [[], ["pi-like"]], [True, False]):
        assert PI.proton_reco_class(top, sub, insig) in PI.PROTON_CLASSES
    got = {PI.merge_destination(p, nu, 0, ph, p) for p, nu, ph in itertools.product([22, 11, 2212, 211, 2112, np.nan], [0, 1, np.nan], [True, False])}
    assert got <= set(PI.MERGE_DESTINATIONS) and PI.merge_destination(2212, 0, 0, False, 2212) == "another signal proton" and PI.merge_destination(22, 0, 0, True, 22) == "signal photon" and PI.merge_destination(22, 1, 0, False, 22) == "other-neutrino or cosmic object"
    assert PI.row_normalise([[1, 3], [0, 0]]).tolist() == [[0.25, 0.75], [0.0, 0.0]]


# ------------------------------------------------------------------------------------------------------------ committed tables: closures and unchanged counts
def test_photon_population_closure_and_phase9_counts_unchanged():
    p = csv("photon_pid_populations"); assert p.n.sum() == 11331 and abs(p.fraction.sum() - 1) < 1e-9 and len(p) == 10
    x = csv("photon_pid_vs_phase9").set_index("pid_class").drop(columns=[]); assert int(x.values.sum()) == 11331
    out = x.sum(); assert out["pass_photon_shower_in_passing_candidate"] == 5423 and out["pass_not_via_signal_photon_shower"] == 2657 and out["photon_fragmented"] == 492       # Phase-9 outcome counts
    st = csv("photon_pid_vs_phase9_state").set_index("pid_class").sum(); assert st["photon_fragmented"] == 2114 and st["photon_no_reco_charge"] == 305 and st["photon_particle_row_missing"] == 382
    c = csv("photon_confusion"); d = c[(c.variant == "dominant_type") & (c.e_bin == "all")]; assert d.n.sum() == 11331 and d.set_index("reco").n["mu-like"] + d.set_index("reco").n["pi-like"] + d.set_index("reco").n["proton-like"] > 3000
    for var in ("dominant_type", "phase9_hierarchy"):
        for b, g in c[(c.variant == var) & (c.e_bin != "all")].groupby("e_bin"): assert g.n.sum() == g.n_bin.iloc[0] and abs(g.fraction.sum() - 1) < 1e-9
    x2 = csv("cross_confusion"); assert x2[x2.truth.str.startswith("signal photon")].n.sum() == 11331 and x2[x2.truth.str.startswith("signal primary")].n.sum() == 8132


def test_photon_fate_chain_for_fragmented_class_reproduces_phase14():
    f = csv("photon_pid_stage_fate"); g = f[f.pid_class == PI.PHOTON_CLASSES[6]].set_index("stage").n
    assert [int(g[s]) for s in ("shower stage", "numu", "other", "ncpi0", "n_20br1", "final")] == [1622, 582, 150, 24, 14, 14] and int(g["all events"]) == 2114
    a = f[f.pid_class == PI.PHOTON_CLASSES[0]].set_index("stage").n; assert int(a["final"]) == 1129 and int(a["shower stage"]) == int(a["all events"]) == 5397
    assert f[(f.stage == "all events")].n.sum() == 11331 and f[f.stage == "shower stage"].n.sum() == 8080 and f[f.stage == "final"].n.sum() == 1153   # frozen cutflow untouched
    t = csv("fragment_track_piece_origin"); sh = t[t.population.str.contains("shower stage")].set_index("item")
    assert int(sh.loc["fragmented events", "n"]) == 1622 and abs(sh.loc["with a track-typed significant piece", "fraction"] - 0.835) < 0.001
    assert abs(sh.loc["dominant piece type: electron shower", "fraction"] - 0.544) < 0.001 and abs(sh.loc["dominant piece type: muon-like", "fraction"] - 0.208) < 0.001


def test_proton_population_closure_and_phase10_counts_unchanged():
    d = csv("proton_denominator").set_index("item").n; assert d["signal primary protons (all KE)"] == 20023 and d["signal primary protons KE > 35 MeV (Phase-10 denominator)"] == 8132
    c = csv("proton_confusion"); 
    for lab, n in (("all KE", 20023), ("KE > 35 MeV", 8132)):
        g = c[c.ke_bin == lab]; assert g.n.sum() == n and (g.n_bin == n).all()
    bins = c[~c.ke_bin.isin(["all KE", "KE > 35 MeV"])]; assert bins.groupby("ke_bin").n.sum().sum() >= 20021 and bins[bins.ke_bin != "0-35"].n.sum() == 8132
    k = c[c.ke_bin == "KE > 35 MeV"].set_index("proton_class").n                          # Phase-10: 3,558 + 207 proton rows, 1,320 subdominant, 1,406 non-proton rows, 854 + 2 no row, 785 no signal candidate
    assert (k["proton-typed"], k["merged / subdominant partner"], k["no signal-matched candidate"], k["no row"]) == (3765, 1320, 785, 856) and k["mu-typed"] + k["pi-typed"] + k["e-shower-typed"] + k["e-track-typed"] == 1406
    s = csv("phase10_state_reproduction").set_index("phase10_state").n; assert s["proton_row_single"] + s["proton_row_multiple"] == k["proton-typed"] and s["subdominant_only"] == 1320 and s["no_signal_candidate"] == 785


def test_high_ke_proton_denominator_and_low_ke_merge_closure():
    h = csv("high_ke_proton_classes"); assert h.n.sum() == h.n_total.iloc[0] == 373 and h.set_index("proton_class").n["mu-typed"] == 112 and h.set_index("proton_class").n["proton-typed"] == 82
    c = csv("proton_confusion"); assert c[(c.ke_bin == ">500")].n.sum() == 373
    m = csv("proton_merge_destinations"); merged = c[c.proton_class == "merged / subdominant partner"].set_index("ke_bin").n
    for b, g in m.groupby("ke_bin"): assert g.n.sum() == g.n_bin.iloc[0] == merged[b]            # every merged proton has exactly one destination
    assert m[m.ke_bin == "all KE"].n.sum() == 2236 and (m.set_index(["ke_bin", "destination"]).n.xs("unmatched / ambiguous", level="destination") == 0).all()
    t = csv("proton_merge_destinations_by_truth_topology_gt35"); assert t.n.sum() == 1320 == csv("proton_confusion").query("ke_bin == 'KE > 35 MeV' and proton_class == 'merged / subdominant partner'").n.iloc[0]
    assert t[t.truth_topology == "truth 1p"].n.sum() == 554 and t[t.truth_topology == "truth >=2p"].n.sum() == 766


def test_numu_connection_closes():
    n = csv("numu_by_mu_pi_row_truth"); assert n.n.sum() == 8038 and n.numu_pass.sum() == 5007 and n.numu_fail.sum() == 3031
    s = csv("numu_failure_share"); assert s.n_failures.sum() == 3031 and abs(s.share_of_failures.sum() - 1) < 1e-9
    assert s.set_index("category").n_failures["only signal-photon piece(s)"] == 1704 and int(csv("numu_mu_pi_row_truth_counts").n_rows.sum()) == 7531


def test_segment_extra_scan_matches_phase9_and_checks_hold():
    c = csv("source_vs_data_checks").set_index("check").value
    assert c["T_kine rows (all candidates)"] == 83097 and c["  rows whose type equals the key segment's pdg"] >= 82900
    assert c["  with exactly 1 muon-typed segment at the main vertex"] > 100 * c["  with >= 2 muon-typed segments at the main vertex (source arbitration leaves at most 1 unless a long-muon chain claims the slot)"]
    s = json.load(open(TAB / "summary.json")); assert s["seg_extra_present"] is True and s["n_rows"] == 83097 and s["n_photon_events"] == 11331


def test_no_selection_flag_threshold_or_policy_changed():
    cfg = ROOT / "configs" / "baseline_selection.yaml"
    assert hashlib.sha256(cfg.read_bytes()).hexdigest() == "f3251b785be6e52ff3e429000a0319a6df8e42d2016ace2f51c7650a38e2fb0b"
    th = {c["name"]: c["threshold"] for c in yaml.safe_load(open(cfg))["cuts"]}
    assert th["single_photon_numu_score_gt_0p4"] == 0.4 and th["single_photon_other_score_gt_0p2"] == 0.2 and th["single_photon_ncpi0_score_gt_m0p05"] == -0.05
    assert hashlib.sha256((ROOT / "configs" / "analysis_definition_candidates.yaml").read_bytes()).hexdigest() == json.load(open(ROOT / "tables" / "analysis_definition_decisions" / "summary.json"))["metadata"]["analysis_definition_candidates_sha256"]       # Phase-13 policy packages untouched
    txt = " ".join(p.read_text().lower() for p in (ROOT / "docs" / "analysis").glob("SIGNAL_P*_PID_FAILURE_AUDIT.md"))
    for bad in ("final purity", "final s/b", "significance of", "we retune", "retuned"):
        assert bad not in txt
