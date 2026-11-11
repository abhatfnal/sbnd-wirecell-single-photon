"""Phase 16: DL-vertex provenance (roadmap V) and shower-attachment (roadmap T): synthetic checks of the helpers and pinned checks of the committed tables.

Nothing here changes a selection flag, threshold, vertex, type or policy.
"""
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from sbnd_single_photon import vertex_audit as VA

ROOT = Path(__file__).resolve().parents[1]
TAB = ROOT / "tables" / "vertex_provenance_audit"
csv = lambda n: pd.read_csv(TAB / f"{n}.csv")


# ------------------------------------------------------------------------------------------------------------ helpers
def test_decompose_along_and_perpendicular_to_the_photon():
    d = VA.decompose([0, 0, 0], [3, 4, 0], [1, 0, 0]); assert abs(d["parallel"] - 3) < 1e-12 and abs(d["perp"] - 4) < 1e-12 and abs(d["mag"] - 5) < 1e-12
    d = VA.decompose([1, 1, 1], [0, 1, 1], [10, 0, 0]); assert abs(d["parallel"] + 1) < 1e-12 and d["perp"] < 1e-12            # direction need not be normalised; negative = against the flight
    d = VA.decompose([0, 0, 0], [1, 2, 3], [0, 0, 0]); assert d["mag"] > 0                                                        # a zero direction does not crash


def test_line_state_and_vertex_state_boundaries():
    assert VA.line_state(0.0, 4.9) == "anchored" and VA.line_state(3, 4) == "anchored" and VA.line_state(10, 5) == "along" and VA.line_state(10, 10.0) == "along" and VA.line_state(10, 10.1) == "off-axis"
    assert VA.line_state(-10, 5) == "against" and VA.line_state(0.0, 20.0) == "off-axis" and VA.line_state(np.nan, 1.0) == "undefined" and VA.line_state(10, 5, tol=15) == "anchored"
    v, c = [0, 0, 0], [30, 0, 0]
    assert VA.vertex_state([2, 0, 0], v, c) == "interaction" and VA.vertex_state([29, 0, 0], v, c) == "conversion" and VA.vertex_state([15, 3, 0], v, c) == "between" and VA.vertex_state([0, 40, 0], v, c) == "neither"
    assert VA.vertex_state([np.nan, 0, 0], v, c) == "undefined"


def test_provenance_taxonomy_is_exclusive_and_exhaustive():
    seen = set()
    for ds, fs, conv in itertools.product(["anchored", "along", "against", "off-axis", "undefined"], ["anchored", "along", "against", "off-axis", "undefined"], [1.0, 20.0, np.nan]):
        c = VA.provenance_class_line(ds, fs, conv); assert c in VA.PROVENANCE_CLASSES; seen.add(c)
    assert seen == set(VA.PROVENANCE_CLASSES)
    for ds, fs, conv in itertools.product(["interaction", "conversion", "between", "neither", "undefined"], ["interaction", "conversion", "between", "neither", "undefined"], [1.0, 20.0, np.nan]):
        assert VA.provenance_class(ds, fs, conv) in VA.PROVENANCE_CLASSES
    P = VA.PROVENANCE_CLASSES
    assert VA.provenance_class_line("along", "along", 20) == P[0] and VA.provenance_class_line("anchored", "along", 20) == P[1] and VA.provenance_class_line("anchored", "anchored", 20) == P[2]
    assert VA.provenance_class_line("off-axis", "anchored", 20) == P[3] and VA.provenance_class_line("along", "off-axis", 20) == P[4] and VA.provenance_class_line("along", "along", 4.9) == P[5] and VA.provenance_class_line("along", "along", 20, have_dl=False) == P[6]


def test_dl_vertex_of_call_never_uses_the_sentinel():
    v, k = VA.dl_vertex_of_call(True, [1, 2, 3], [9, 9, 9], True); assert v.tolist() == [1, 2, 3] and k == "dl_accepted"
    v, k = VA.dl_vertex_of_call(False, [0, 0, 0], [9, 9, 9], True); assert v.tolist() == [9, 9, 9] and k == "traditional_kept"           # the (0,0,0) sentinel of a not-accepted call is ignored
    v, k = VA.dl_vertex_of_call(False, [0, 0, 0], [0, 0, 0], False); assert v is None and k == "none"


NODES = {1: (-1, 2212, False, 0), 2: (1, 22, True, -1), 3: (2, 11, False, 5), 4: (-1, 22, True, -1), 5: (4, 11, False, 6), 6: (1, 111, True, -1), 7: (6, 22, True, -1), 8: (7, 11, False, 7), 9: (-1, 211, False, 1), 10: (9, 111, True, -1), 11: (10, 22, True, -1), 12: (11, 11, False, 2)}


def test_ancestor_chain_and_parent_classes():
    assert [c[0] for c in VA.ancestor_chain(3, NODES)] == [3, 2, 1] and VA.ancestor_chain(99, NODES) == []
    assert VA.ancestor_chain(3, {3: (3, 11, False, 0)}) == [(3, 11, False, 0)]                                                      # cycle-safe
    cls = lambda n, **kw: VA.parent_class(VA.ancestor_chain(n, NODES), **kw)
    assert cls(3) == (VA.PARENT_CLASSES[1], 2212, False)                       # under a proton-typed object through a pseudo-gamma wrapper
    assert cls(5)[0] == VA.PARENT_CLASSES[0]                                    # root-level pseudo photon: direct at the main vertex
    assert cls(8)[0] == VA.PARENT_CLASSES[1] and cls(8)[2] is True              # under the pseudo pi0, whose parent is the proton
    assert cls(12) == (VA.PARENT_CLASSES[3], 211, True) and cls(3, in_other_candidate=True)[0] == VA.PARENT_CLASSES[6] and VA.parent_class([])[0] == VA.PARENT_CLASSES[7]
    only_pseudo = {1: (-1, 111, True, -1), 2: (1, 22, True, -1), 3: (2, 11, False, 0)}; assert VA.parent_class(VA.ancestor_chain(3, only_pseudo))[0] == VA.PARENT_CLASSES[5]
    muon = {1: (-1, 13, False, 0), 2: (1, 22, True, -1), 3: (2, 11, False, 1)}; assert VA.parent_class(VA.ancestor_chain(3, muon))[0] == VA.PARENT_CLASSES[2]
    gen = {1: (-1, 11, False, 0), 2: (1, 22, True, -1), 3: (2, 11, False, 1)}; assert VA.parent_class(VA.ancestor_chain(3, gen))[0] == VA.PARENT_CLASSES[4]


def test_attachment_mechanism_is_exhaustive_and_exclusive():
    seen = set()
    for pc, pi0, tr in itertools.product(VA.PARENT_CLASSES, [True, False], ["signal_proton", "signal_other_hadron", "signal_photon_fragment", "signal_photon_dominant", "cosmic", "none", "ambiguous_mixed"]):
        m = VA.attach_mechanism(pc, pi0, tr); assert m in VA.ATTACH_MECHANISMS; seen.add(m)
    assert seen == set(VA.ATTACH_MECHANISMS)
    assert VA.attach_mechanism(VA.PARENT_CLASSES[1], False, "signal_proton") == VA.ATTACH_MECHANISMS[2] and VA.attach_mechanism(VA.PARENT_CLASSES[1], True, "signal_proton") == VA.ATTACH_MECHANISMS[0]
    assert VA.attach_mechanism(VA.PARENT_CLASSES[2], False, "signal_photon_fragment") == VA.ATTACH_MECHANISMS[1]


# ------------------------------------------------------------------------------------------------------------ DL record closure and coordinate sanity
def test_dl_candidate_event_mapping_closes():
    c = csv("dl_coverage").set_index("item").value
    assert c["events requested (Phase-9 event_taxonomy)"] == 11331 and c["events with >= 1 DL record"] + c["events without any DL record"] == 11331
    assert c["DL records (calls)"] == c["  production calls (pass 0)"] + c["  dual-chain OFF calls (pass 1)"] == 23508 and c["  other pass codes"] == 0
    assert c["candidates with a production DL call"] + c["candidates without a production call"] == c["candidates in the Phase-9 candidate table"] == 11783
    assert c["candidates with more than one production call (duplicates)"] == 0 and c["duplicated (event, candidate, call_index) records"] == 0
    assert c["run / subrun / event keys of the scan match Phase 9 (records)"] == c["  records compared"] == 23508 and c["production calls with status != 0 (network error / odd payload)"] == 0


def test_vertex_coordinate_sanity_and_sentinels():
    c = csv("dl_coverage").set_index("item").value
    assert c["production calls with accepted == 1 (DL vertex switched the main vertex)"] + c["production calls not accepted (traditional vertex kept)"] == c["  production calls (pass 0)"]
    assert c["  of those with the sentinel dl_xyz = (0, 0, 0)"] == c["production calls not accepted (traditional vertex kept)"]            # every not-accepted call carries the sentinel
    assert c["accepted DL vertices inside the box |x|,|y| < 260, -60 < z < 560 cm"] == c["  accepted DL vertices"]
    assert c["final vertices inside the same box"] >= c["  valid final vertices"] - 5 and c["  max |final - kine_nu_corr| cm"] < 1e-3                       # final = kine_nu_*_corr
    assert c["  |final - kine_nu_corr| < 0.01 cm"] == c["production calls compared with T_kine kine_nu_*_corr"] == 11754
    assert c["production calls with the signal interaction found in truth_all_*"] == 11754 and c["production calls with truth_sce_applied == 1"] == 11754


# ------------------------------------------------------------------------------------------------------------ provenance tables
def test_truth_topology_denominators_close_and_provenance_classes_partition_them():
    pc = csv("provenance_classes_by_topology").set_index("prov_class"); tops = ["truth 0p", "truth 1p", "truth >=2p"]
    assert [int(pc[t].sum()) for t in tops] == [5082, 5086, 941] and int(pc["all"].sum()) == 11109 and (pc[tops].sum(axis=1) == pc["all"]).all()
    assert pc.loc[VA.PROVENANCE_CLASSES[1], "all"] == 1 and pc.loc[VA.PROVENANCE_CLASSES[0], "all"] > 5000                              # the displacement is at DL time: class B is one event
    a = csv("vertex_anchoring_by_stage").query("tolerance_cm == 5").set_index("topology"); assert a.n.to_dict() == {"all": 11109, "truth 0p": 5082, "truth 1p": 5086, "truth >=2p": 941}
    p = csv("proton_anchoring_by_stage"); sub = p[(p.topology == "all") & (p.proton_class != "all")]; assert sub.n.sum() == 11109
    for t, n in (("truth 0p", 5082), ("truth 1p", 5086), ("truth >=2p", 941)):
        assert p[(p.topology == t) & (p.proton_class != "all")].n.sum() == n


def test_photon_line_displacement_is_present_at_dl_and_not_introduced_after():
    w = csv("photon_line_displacement_where").set_index("topology")
    assert w.loc["truth 0p", "median_dl_true_par"] > 20 and abs(w.loc["truth 0p", "median_final_dl_par"]) < 0.5 and w.loc["truth 0p", "frac_final_moves_gt5cm_along_after_dl"] < 0.05
    assert w.loc["truth 1p", "median_dl_true_par"] < 0.3 * w.loc["truth 0p", "median_dl_true_par"] and w.loc["all", "n"] == w.loc[["truth 0p", "truth 1p", "truth >=2p"], "n"].sum()


def test_stage_survival_closure_by_vertex_class_and_frozen_cutflow_untouched():
    s = csv("stage_survival_by_vertex_class"); stages = ["all events", "candidate", "shower stage", "numu", "other", "ncpi0", "n_20br1", "final"]
    for c, g in s.groupby("prov_class"):
        n = g.set_index("stage").n.reindex(stages).values; assert (np.diff(n) <= 0).all() and n[0] == n[1]                              # monotone, every event has a candidate
    tot = s.groupby("stage").n.sum(); assert tot["all events"] == 11109 and tot["final"] == 1153                                          # every final-selected event (Phase-9 cutflow) is in the table
    assert tot["shower stage"] <= 8080 and tot["numu"] <= 5007 and tot["ncpi0"] <= 1313


def test_other_stage_gap_standardisation_is_a_bounded_fraction():
    g = csv("other_stage_gap_standardisation").set_index("vertex")
    assert abs(g.loc["DL vertex", "gap_1p_minus_0p"] - 0.158) < 0.002 and 0.5 < g.loc["DL vertex", "gap_explained_by_anchored_fraction_using_0p_rates"] < 0.7 and 0.75 < g.loc["DL vertex", "gap_explained_by_anchored_fraction_using_1p_rates"] < 0.95
    assert g.loc["DL vertex", "anchored_fraction_1p"] > 3 * g.loc["DL vertex", "anchored_fraction_0p"]


# ------------------------------------------------------------------------------------------------------------ the 567-event population
def test_567_population_closes_exactly():
    p = csv("attachment_population").set_index("item").n
    assert p["events with outcome photon_shower_not_in_main_vertex_set (Phase 9)"] == p["reproduced population"] == 567 and p["  of which PF state 'deeper' (Phase 9)"] + p["  PF state photon_node_at_vertex"] + p["  PF state root"] == 567
    assert p["all of the 567 reach the shower stage"] == 0                                                                             # none reaches it: they ARE the shower-stage failures
    assert csv("attachment_parent_class").n.sum() == 567 and csv("attachment_parent_truth_total").n.sum() == 567 and csv("attachment_mechanism").n.sum() == 567


def test_pf_parent_and_parent_truth_taxonomy_closure():
    pc = csv("attachment_parent_class").set_index("pf_parent_class").n
    assert set(pc.index) <= set(VA.PARENT_CLASSES) and pc["B under a proton-typed object"] == 336 and pc["C under a muon-like object"] == 124
    ct = csv("attachment_parent_truth").set_index("pclass"); assert int(ct.values.sum()) == 567 and (ct.sum(axis=1) == pc.reindex(ct.index)).all()                    # class x truth partitions the population
    m = csv("attachment_mechanism"); assert set(m.mechanism) <= set(VA.ATTACH_MECHANISMS) and abs(m.fraction.sum() - 1) < 1e-9
    mt = csv("attachment_mechanism_by_topology").set_index("mechanism"); assert mt.sum().to_dict() == {"truth 0p": 120, "truth 1p": 364, "truth >=2p": 83}


def test_attachment_failure_rate_denominators_close():
    r = csv("attachment_failure_rate_by_hadronic_activity"); t = r[r.variable == "tp_label"]
    assert t.n_failures.sum() == 567 and t.n_denominator.sum() == 5990 and set(t.group) == {"truth 0p", "truth 1p", "truth >=2p"}                   # 567 failures + 5,423 clean passes
    assert r[r.variable == "proton_class"].n_failures.sum() == 567 and r[r.variable == "delta_label"].n_failures.sum() == 567
    rate = t.set_index("group").failure_rate; assert rate["truth 0p"] < rate["truth 1p"] < rate["truth >=2p"]


def test_natural_cv_check_is_low_statistics_and_consistent():
    n = csv("natural_cv_check").set_index("topology"); cv = csv("natural_cv_coverage").iloc[0]
    assert cv.records == 216 and cv.production_calls == 108 and cv.events == 105 and n.loc["all", "n_events"] == 105 and n.loc["all", "frac_final_moved_gt_5cm_from_dl"] < 0.1


# ------------------------------------------------------------------------------------------------------------ nothing selected or tuned
def test_no_selection_flag_threshold_or_policy_changed():
    cfg = ROOT / "configs" / "baseline_selection.yaml"
    assert hashlib.sha256(cfg.read_bytes()).hexdigest() == "f3251b785be6e52ff3e429000a0319a6df8e42d2016ace2f51c7650a38e2fb0b"
    th = {c["name"]: c["threshold"] for c in yaml.safe_load(open(cfg))["cuts"]}
    assert th["single_photon_numu_score_gt_0p4"] == 0.4 and th["single_photon_other_score_gt_0p2"] == 0.2 and th["single_photon_ncpi0_score_gt_m0p05"] == -0.05
    assert hashlib.sha256((ROOT / "configs" / "analysis_definition_candidates.yaml").read_bytes()).hexdigest() == json.load(open(ROOT / "tables" / "analysis_definition_decisions" / "summary.json"))["metadata"]["analysis_definition_candidates_sha256"]
    txt = " ".join(p.read_text().lower() for p in (ROOT / "docs" / "analysis").glob("*VERTEX*")) + " ".join(p.read_text().lower() for p in (ROOT / "docs" / "analysis").glob("SIGNAL_PHOTON_SHOWER_ATTACHMENT_AUDIT.md"))
    for bad in ("final purity", "final s/b", "significance of", "retuned"):
        assert bad not in txt
