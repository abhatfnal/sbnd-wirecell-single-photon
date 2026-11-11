"""Phase 14: pi0-pair recovery, member truth taxonomy and signal-photon fragmentation closure.

Synthetic checks of the pure helpers (``pair_audit``) and pinned checks of the committed tables.  Nothing here changes a selection flag, threshold or policy.
"""
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from sbnd_single_photon import pair_audit as PA

ROOT = Path(__file__).resolve().parents[1]
TAB = ROOT / "tables" / "pi0_pair_fragmentation_audit"
csv = lambda n: pd.read_csv(TAB / f"{n}.csv")


# ------------------------------------------------------------------------------------------------------------ source ranking semantics
def test_kine_pair_is_largest_energy_sum_strictly_and_ignores_mass():
    pairs = [(100.0, 5.0, "a"), (60.0, 45.0, "b"), (105.0, 0.0, "c"), (30.0, 30.0, "d")]
    assert PA.select_kine_pair(pairs) == "a"            # 105 ties with 105 (b) and (c): the FIRST maximum wins (strict improvement only)
    assert PA.select_kine_pair([(1.0, 1.0, "x"), (2.0, 3.0, "y")]) == "y" and PA.select_kine_pair([]) is None
    assert PA.select_kine_pair([(0.0, 0.0, "z")]) is None          # a zero-energy pair never replaces the initial running maximum of 0


def test_window_pair_is_mass_window_with_offset_and_two_ct2_bonus():
    assert PA.select_window_pair([(99.0, 0, "lo"), (161.0, 0, "hi")]) is None                  # window is 100 < m < 160 (offset 10, -25 < m-125 < 35)
    assert PA.select_window_pair([(100.5, 0, "edge")]) == "edge"                                # just inside the window is eligible
    assert PA.select_window_pair([(100.5, 0, "edge"), (140.0, 0, "mid")]) == "mid"             # |m-125|: 24.5 vs 15
    assert PA.select_window_pair([(120.0, 0, "far"), (126.0, 0, "near")]) == "near"           # closest to 125 MeV
    assert PA.select_window_pair([(124.0, 0, "plain"), (130.0, 2, "ct2")]) == "ct2"           # |5| - 6 beats |1|
    assert PA.select_window_pair([(125.0, 0, "first"), (125.0, 0, "second")]) == "first"      # tie keeps the first
    for m in (100.0, 160.0):                                                                   # open interval: the edges are excluded
        assert PA.select_window_pair([(m, 0, "e")]) is None


# ------------------------------------------------------------------------------------------------------------ pair recovery
ROWS = np.array([0, 1, 2, 3, 4]); EN = np.array([200.0, 30.0, 12.5, 7.0, 1.5]); INFO = np.array([2, 2, 0, 2, 1]); POOL = np.array([0, 2, 2, 2, 2])


def test_consistent_pairs_exact_elimination_and_detached_rule():
    cfg, nex = PA.consistent_pairs(ROWS, EN, INFO, POOL, 200.0, 30.0)
    assert cfg == [(0, 1)] and nex == 2 and PA.recovery_class(nex, len(cfg)) == "unique_exact"
    cfg, nex = PA.consistent_pairs(ROWS, EN, INFO, POOL, 200.0, 9.9)        # 9.9 matches no row: a row with info != 2 (rows 2 or 4)
    assert sorted(cfg) == [(0, 2), (0, 4)] and nex == 1 and PA.recovery_class(nex, len(cfg)) == "ambiguous"
    cfg, nex = PA.consistent_pairs(ROWS[:3], EN[:3], INFO[:3], POOL[:3], 200.0, 9.9)
    assert cfg == [(0, 2)] and PA.recovery_class(nex, len(cfg)) == "unique_by_elimination"
    # both members attached (pool 0/1) is excluded; without the rule it is allowed
    pool2 = np.array([0, 0, 2, 2, 2]); assert PA.consistent_pairs(ROWS, EN, INFO, pool2, 200.0, 30.0)[0] == []
    assert PA.consistent_pairs(ROWS, EN, INFO, pool2, 200.0, 30.0, require_detached=False)[0] == [(0, 1)]
    assert PA.recovery_class(0, 0) == "unresolved"


def test_no_duplicate_pair_members_and_energy_tolerance():
    rows = np.array([0, 1, 2]); en = np.array([50.0, 50.0, 50.0]); info = np.array([2, 2, 2]); pool = np.array([2, 2, 2])
    cfg, _ = PA.consistent_pairs(rows, en, info, pool, 50.0, 50.0)
    assert cfg and all(a != b for a, b in cfg)                                          # a row is never paired with itself
    assert len(PA.unordered_pair_keys(cfg)) == 3 and PA.recovery_class(2, len(PA.unordered_pair_keys(cfg))) in ("ambiguous", "unique_exact")
    assert PA.energy_matches(np.array([100.0, 100.0 * (1 + 1e-4)]), 100.0).tolist() == [True, False]    # tolerance 1e-5 relative


def test_geometry_status_and_refinement():
    a, b = np.array([0.0, 0, 0]), np.array([3.0, 4.0, 0.0])                             # separation 5
    assert PA.geometry_status(a, b, 0.0, 5.0) == "strong_pass" and PA.geometry_status(a, b, 5.0, 0.0) == "strong_pass"
    assert PA.geometry_status(a, b, 0.0, 6.0) == "strong_fail"
    assert PA.geometry_status(a, b, 3.0, 4.0) == "weak_pass" and PA.geometry_status(a, b, 1.0, 1.0) == "weak_fail"
    assert PA.geometry_status(None, b, 1.0, 1.0) == "untestable"
    assert PA.refine_by_geometry([(0, 1), (0, 2)], ["strong_fail", "untestable"]) == ([(0, 2)], "consistent")
    assert PA.refine_by_geometry([(0, 1)], ["strong_fail"]) == ([(0, 1)], "geometry_inconsistent")     # never silently drops everything
    assert PA.refine_by_geometry([], []) == ([], "untested")


def test_stored_mass_relation_helper():
    assert abs(PA.mass_from_energies_angle(100.0, 100.0, 180.0) - 200.0) < 1e-9 and PA.mass_from_energies_angle(50, 50, 0.0) == 0.0


# ------------------------------------------------------------------------------------------------------------ member truth taxonomy
def test_row_truth_class_is_exhaustive_and_exclusive():
    sig_tid, sig_nu = 10000002, 0; seen = set()
    for p1_tid, pdg, nu, dom, outside, p2_ratio in itertools.product([10000002, 10000005, -1], [22, 11, 2212, 211, 2112], [0, 1, -1, np.nan, -9], [True, False], [True, False], [0.0, 0.9]):
        c = PA.row_truth_class(p1_tid, pdg, nu, 0.8, 10000009 if p2_ratio else np.nan, 0.8 * p2_ratio if p2_ratio else np.nan, 2, sig_tid, sig_nu, dom, {1: outside})
        assert c in PA.FINE_CLASSES                                                         # one class per input, always one of the fixed set
        seen.add(c)
    assert seen == set(PA.FINE_CLASSES)                                                    # every class is reachable
    assert PA.row_truth_class(10000002, 22, 0, 0.9, np.nan, np.nan, np.nan, 10000002, 0, True) == "signal_photon_dominant"
    assert PA.row_truth_class(10000002, 22, 0, 0.9, np.nan, np.nan, np.nan, 10000002, 0, False) == "signal_photon_fragment"
    assert PA.row_truth_class(10000007, 22, 0, 0.9, np.nan, np.nan, np.nan, 10000002, 0, False) == "signal_other_EM"
    assert PA.row_truth_class(10000007, 2212, 0, 0.9, np.nan, np.nan, np.nan, 10000002, 0, False) == "signal_proton"
    assert PA.row_truth_class(10000007, 22, 1, 0.9, np.nan, np.nan, np.nan, 10000002, 0, False, {1: True}) == "dirt_outside_AV_nu"
    assert PA.row_truth_class(10000007, 22, 1, 0.9, np.nan, np.nan, np.nan, 10000002, 0, False, {1: False}) == "other_nu_EM"
    assert PA.row_truth_class(-1, 22, 0, 0.9, np.nan, np.nan, np.nan, 10000002, 0, False) == "unmatched"      # prong id -1: no source-ranked partner


def test_pair_membership_accounting_over_every_member_combination():
    for a, b in itertools.combinations_with_replacement(PA.FINE_CLASSES, 2):
        m = PA.pair_signal_membership([a, b]); n_sig = sum(c in ("signal_photon_dominant", "signal_photon_fragment") for c in (a, b))
        assert m == {0: "contains_neither", 1: ("contains_dominant" if "signal_photon_dominant" in (a, b) else "contains_fragment_only"), 2: "contains_both_pieces"}[n_sig]
    assert PA.other_member_class(["signal_photon_dominant", "signal_proton"]) == "signal_proton" and PA.other_member_class(["signal_photon_dominant", "signal_photon_fragment"]) == "signal_photon_fragment"
    assert PA.decide(["a", "a"]) == "a" and PA.decide(["a", "b"]) == "indeterminate"


def test_significant_pieces_and_type_labels():
    idx, lead = PA.significant_pieces([60.0, 30.0, 6.0, 4.0]); assert idx.tolist() == [0, 1] and abs(lead - 0.6) < 1e-12
    assert PA.significant_pieces([])[0].size == 0
    assert [PA.type_label(11, True), PA.type_label(11, False), PA.type_label(-13, True), PA.type_label(211, False), PA.type_label(2212, True), PA.type_label(22, True)] == ["electron shower", "electron track", "muon-like", "pion-like", "proton-like", "other"]


# ------------------------------------------------------------------------------------------------------------ committed tables: closure
def test_ncpi0_population_closure():
    p = csv("ncpi0_population").iloc[0]
    assert (p.entering, p.passing, p.rejected, p.rejected_finite, p.rejected_nonfinite, p.passing_nonfinite) == (2781, 1313, 1468, 1465, 3, 0)
    assert p.entering == p.passing + p.rejected_finite + p.rejected_nonfinite and bool(p.closure)
    nf = csv("ncpi0_nonfinite_events"); assert len(nf) == 3 and nf.in_kine_pio_angle.isna().all() and (nf.in_kine_pio_flag == 1).all()     # the known non-finite kine_pio cases


def test_pair_recovery_closure_and_validation():
    r = csv("pair_recovery")
    for pair, n in (("kine", 1952), ("tagger", 271)):
        for lvl in r.level.unique():
            d = r[(r.pair == pair) & (r.level == lvl)]; assert d.n.sum() == n and (d.n_present == n).all()          # every present pair is in exactly one class
    k = r[(r.pair == "kine") & (r.level == "energy signature + elimination")].set_index("recovery_class").n
    assert k["unique_exact"] == 1318 and k["unresolved"] == 32 and k["ambiguous"] == 294
    v = csv("pair_recovery_validation").set_index(["pair", "metric"]).value
    assert v[("tagger", "tagger-selected shower is a member of the recovered pair (events with a unique selected row and configuration)")] == v[("tagger", "same: events compared")] == 262
    assert v[("kine", "|distance residual| < 1e-3 cm")] >= 1190


def test_pair_membership_tables_close():
    m = csv("pair_membership")
    for (pair, pop), d in m.groupby(["pair", "population"]):
        assert d.n.sum() == d.n_population.iloc[0] == {"all": 2781, "accepted": 1313, "rejected": 1468}[pop]
    a = m[(m.population == "all")]; r_ = m[(m.population == "rejected")]; ac = m[(m.population == "accepted")]
    assert (a.set_index(["pair", "membership"]).n == ac.set_index(["pair", "membership"]).n + r_.set_index(["pair", "membership"]).n).all()
    ra = csv("rejected_attribution").set_index("measure").n
    assert ra["rejected events (all)"] == 1468 and ra["rejected, any pair flag (kine or tagger)"] == 1383                                  # so 1468 - 1383 = 85 rejected events have no pair flag
    assert ra["rejected, clean photon (Phase 9) and a pair flag"] + ra["rejected, clean photon (Phase 9) and no pair flag"] == 1276         # the clean-photon rejections, partitioned


def test_kine_vs_tagger_partition():
    k = csv("kine_vs_tagger"); assert k.n.sum() == 2781 and k.set_index("label").n["neither"] == 767 and k.set_index("label").n["tagger only"] == 62 and k.set_index("label").n["kine only"] == 1743
    assert k[k.label.str.startswith("both")].n.sum() == 209                                  # 1,952 + 271 - 2,781 + 767 = 209 events with both pairs


# ------------------------------------------------------------------------------------------------------------ committed tables: fragmentation closure
def test_fragmentation_event_count_reproduces_phase9_and_stage_counts():
    d = csv("fragment_multiplicity").set_index("population"); assert d.loc["fragmented (Phase 9)", "n"] == 1622 and d.loc["clean (Phase 9)", "n"] == 5423
    f = csv("fragment_stage_fate").query("population == 'fragmented'").set_index("stage").n_reaching_or_passing
    assert [int(f[s]) for s in ("shower stage (> 20 MeV shower)", "numu", "other", "ncpi0", "n_20br1 == 1")] == [1622, 582, 150, 24, 14] and int(f["final"]) == 14 and int(f["BDT evaluable"]) == 1618
    fl = csv("fragment_first_loss"); g = fl[fl.population == "fragmented"].set_index("first_loss").n
    assert g.sum() == 1622 and g["numu"] == 1036 and g["other"] == 432 and g["ncpi0"] == 126 and g["final"] == 14          # exclusive: every event has exactly one first-loss stage
    sf = csv("fragment_stage_fate").query("population == 'fragmented'").set_index("stage").step_survival
    prod = float(np.prod([sf[x] for x in ("BDT evaluable", "numu", "other", "ncpi0", "nue", "n_20br1 == 1")])); assert abs(prod - 14 / 1622) < 1e-9       # the cumulative survival is the product of the stage survivals


def test_n20br1_split_photon_overlap_closes():
    b = csv("n20br1_failures_base").set_index("item").n
    assert b["n_20br1 failures"] == 160 and b["with an extra shower row attributed to the signal photon (T_match top partner)"] == 126 and b["without"] == 34
    m = csv("n20br1_mapping"); assert m.n.sum() == 126 and m.set_index("mapping").n["already fragmented at the shower stage (Phase 9)"] == 10
    assert csv("n20br1_failures_by_phase9_state").n.sum() == 160


def test_fragment_location_and_type_tables_close():
    loc = csv("fragment_location_pieces"); assert loc.n_pieces.sum() == int(round(loc.n_pieces.sum())) and abs(loc.fraction.sum() - 1) < 1e-9
    assert loc.set_index("location").n_pieces["in another cluster (same candidate)"] == loc.n_pieces.max()
    t = csv("fragment_type_combinations"); assert t.n.sum() == 1622 and abs(t.fraction.sum() - 1) < 1e-9
    h = csv("fragment_multiplicity_hist"); assert h.n_events.sum() == 1622


def test_no_frozen_selection_flag_threshold_or_config_changed():
    cfg = ROOT / "configs" / "baseline_selection.yaml"
    assert hashlib.sha256(cfg.read_bytes()).hexdigest() == "f3251b785be6e52ff3e429000a0319a6df8e42d2016ace2f51c7650a38e2fb0b"
    th = {c["name"]: c["threshold"] for c in yaml.safe_load(open(cfg))["cuts"]}
    assert th["single_photon_numu_score_gt_0p4"] == 0.4 and th["single_photon_other_score_gt_0p2"] == 0.2 and th["single_photon_ncpi0_score_gt_m0p05"] == -0.05
    s = json.load(open(TAB / "summary.json")); assert s["population"]["entering"] == 2781 and s["population"]["passing"] == 1313        # the frozen cutflow is preserved
    txt = " ".join(p.read_text().lower() for p in (ROOT / "docs" / "analysis").glob("*PAIR*")) + " ".join(p.read_text().lower() for p in (ROOT / "docs" / "analysis").glob("SIGNAL_PHOTON_FRAGMENTATION*"))
    for bad in ("final purity", "final s/b", "significance of"):
        assert bad not in txt


@pytest.mark.skipif(not (Path(__import__("os").environ.get("SP_DATA", "/nonexistent")) / "pi0_pair_fragmentation_audit" / "official_ncdelta" / "ncpi0_pair_members.parquet").exists(), reason="detailed Phase-14 outputs not on this machine")
def test_member_parquet_has_no_duplicate_members():
    d = pd.read_parquet(Path(__import__("os").environ["SP_DATA"]) / "pi0_pair_fragmentation_audit" / "official_ncdelta" / "ncpi0_pair_members.parquet")
    assert (d.row_for_energy1 != d.row_for_energy2).all()
    assert not d.duplicated(["file_index", "ev", "pair", "config"]).any()
