"""Audit tools of the frozen `other` BDT: TMVA-semantics evaluator, exact tree-contribution decomposition and exact interventional TreeSHAP (validated by brute force on a toy ensemble)."""
import itertools
import math
import numpy as np
import pytest
from sbnd_single_photon import bdt as B, other_audit as OA

XML = """<?xml version="1.0"?>
<MethodSetup Method="BDT"><Variables NVar="3"><Variable VarIndex="0" Expression="a"/><Variable VarIndex="1" Expression="b"/><Variable VarIndex="2" Expression="c"/></Variables>
 <Weights NTrees="3">
  <BinaryTree boostWeight="1.0" itree="0"><Node pos="s" IVar="0" Cut="0.5"><Node pos="l" IVar="1" Cut="0.0"><Node pos="l" IVar="-1" res="-0.4"/><Node pos="r" IVar="-1" res="0.7"/></Node><Node pos="r" IVar="2" Cut="1.0"><Node pos="l" IVar="-1" res="0.2"/><Node pos="r" IVar="-1" res="-0.9"/></Node></Node></BinaryTree>
  <BinaryTree boostWeight="0.5" itree="1"><Node pos="s" IVar="1" Cut="0.3"><Node pos="l" IVar="0" Cut="0.5"><Node pos="l" IVar="-1" res="0.6"/><Node pos="r" IVar="-1" res="-0.1"/></Node><Node pos="r" IVar="-1" res="0.9"/></Node></BinaryTree>
  <BinaryTree boostWeight="0.25" itree="2"><Node pos="s" IVar="0" Cut="0.2"><Node pos="l" IVar="-1" res="-1.0"/><Node pos="r" IVar="0" Cut="0.8"><Node pos="l" IVar="-1" res="0.5"/><Node pos="r" IVar="-1" res="1.5"/></Node></Node></BinaryTree>
 </Weights></MethodSetup>"""


@pytest.fixture
def toy(tmp_path):
    p = tmp_path / "toy.xml"; p.write_text(XML); return B.TmvaBdt("toy", p, check_nvars=False), p


def test_float32_evaluator_matches_scalar_spec_and_decomposition_sums_to_the_margin(toy):
    m, p = toy; rng = np.random.default_rng(2); X = rng.normal(size=(300, 3))
    s = OA.scores_tmva_float32(m, X)
    np.testing.assert_allclose(s, [OA.scalar_score_tmva(p, x) for x in X], atol=1e-12)
    c = OA.tree_contributions(m, X)
    np.testing.assert_allclose(np.tanh(c.sum(axis=1)), s, atol=1e-12)                 # tanh(m) == 2/(1+exp(-2m)) - 1


def test_exact_ties_follow_tmva_rule_right_and_differ_from_the_frozen_le_convention(toy):
    m, _ = toy
    X = np.array([[0.5, 1.0, 1.0]]); X2 = X + np.array([[-1e-3, 0, 0]])
    tmva = OA.scores_tmva_float32(m, X)[0]; frozen = m.decision(X)[0]
    assert tmva != frozen and OA.scores_tmva_float32(m, X2)[0] != tmva                  # x == cut goes RIGHT in TMVA, LEFT in the frozen '<=' scorer: ties are the only difference
    X3 = np.random.default_rng(0).normal(size=(500, 3)); np.testing.assert_allclose(OA.scores_tmva_float32(m, X3), m.decision(X3), atol=1e-6)   # off ties they agree (float32 rounding only)


def _brute_shapley(f, x, bg):
    n = len(x); phi = np.zeros(n)
    def v(S):
        return np.mean([f(np.array([x[i] if i in S else b[i] for i in range(n)])) for b in bg])
    for i in range(n):
        for k in range(n):
            for S in itertools.combinations([j for j in range(n) if j != i], k):
                w = math.factorial(k) * math.factorial(n - k - 1) / math.factorial(n)
                phi[i] += w * (v(set(S) | {i}) - v(set(S)))
    return phi


def test_interventional_treeshap_equals_brute_force_shapley_and_is_additive(toy):
    m, _ = toy; rng = np.random.default_rng(7); Xf = rng.normal(0.4, 1.0, size=(6, 3)).astype(np.float32); Xb = rng.normal(0.0, 1.0, size=(5, 3)).astype(np.float32)
    r = OA.interventional_shap(m, Xf, Xb)
    margin = lambda x: OA.tree_contributions(m, x[None, :].astype(np.float64)).sum()
    for i in range(len(Xf)):
        np.testing.assert_allclose(r["phi"][i], _brute_shapley(margin, Xf[i].astype(np.float64), Xb.astype(np.float64)), atol=1e-9)
        np.testing.assert_allclose(r["base"] + r["phi"][i].sum(), margin(Xf[i].astype(np.float64)), atol=1e-9)    # additivity


def test_leaf_paths_cover_every_event_exactly_once_per_tree(toy):
    m, _ = toy; paths = OA.leaf_paths(m); X = np.random.default_rng(3).normal(size=(200, 3)).astype(np.float32)
    for ti in range(len(m.trees)):
        hit = np.zeros(len(X), int)
        for t, _, cond in paths:
            if t != ti:
                continue
            ok = np.ones(len(X), bool)
            for f, (lo, hi) in cond.items():
                ok &= (X[:, f] >= np.float32(lo)) & (X[:, f] < np.float32(hi))
            hit += ok
        assert (hit == 1).all()


# ---------------------------------------------------------------------------------------------------------------------------- pinned audit results (small committed tables)
import json
from pathlib import Path
import pandas as pd
import yaml

REPO = Path(__file__).resolve().parents[1]
SUM = REPO / "tables" / "other_bdt_audit" / "summary.json"
WEIGHT = B.DEFAULT_WEIGHT_DIR / "single_photon_other_bdt_final.xml"
needs_summary = pytest.mark.skipif(not SUM.exists(), reason="other-BDT audit summary not generated")


def _s():
    return json.loads(SUM.read_text())


@pytest.mark.skipif(not WEIGHT.exists(), reason="frozen weight file not visible from this machine")
def test_frozen_weight_checksum_and_structure_and_independent_score_reproduction():
    assert B.sha256(WEIGHT) == "8c0ac375e957f5b332bc35339e4ebcbfef35bb778fb73315b06a814e600dbb16"
    m = B.TmvaBdt("other", WEIGHT)
    assert len(m.var_names) == 146 and len(m.trees) == 215 and set(np.round(m.boost, 9)) == {1.0}
    X = np.random.default_rng(11).normal(size=(200, 146)) * 5.0
    np.testing.assert_allclose(OA.scores_tmva_float32(m, X), m.decision(X), atol=1e-6)         # off exact ties the two implementations agree to float32 rounding


@needs_summary
def test_exact_reproduction_numbers_are_pinned():
    r = _s()["reproduction"]
    assert r["n_candidates"] == 5453 and r["max_abs_diff_vs_stored"] == 0.0 and r["n_nonfinite_recomputed"] == 0
    assert r["max_abs_diff_vs_independent_tmva_f32"] < 1e-6 and r["n_decision_flips_at_0p2"] == 0 and r["scalar_vs_vectorised_f32_max"] == 0.0 and r["cm_stored_in_caf"] is False


def test_threshold_is_the_frozen_0p2_only():
    cfg = yaml.safe_load(open(REPO / "configs" / "baseline_selection.yaml"))
    other = [c for c in cfg["cuts"] if c.get("bdt_model") == "other"][0]
    assert float(other["threshold"]) == 0.2
    src = (REPO / "scripts" / "other_bdt_audit.py").read_text()
    assert "THRESHOLD = 0.2" in src and "np.linspace" not in src.split("def hist_cdf")[0].split("THRESHOLD = 0.2")[1][:200]
    if SUM.exists():
        assert _s()["metadata"]["threshold"] == 0.2


def test_input_mapping_is_the_bdt_module_mapping_and_covers_all_inputs():
    t = pd.read_csv(REPO / "tables" / "other_bdt_audit" / "input_source_table.csv")
    assert len(t) == 146 and t.bdt_variable.is_unique and t.caf_branch.is_unique and (t.var_index == np.arange(146)).all()
    assert (t.caf_branch == [B.input_branch("other", v) for v in t.bdt_variable]).all()
    assert t[t.bdt_variable == "reco_nuvtxY"].caf_branch.iloc[0] == "wc.T_kine.kine_nu_y_corr" and (t[t.bdt_variable != "reco_nuvtxY"].caf_branch.str.startswith("wc.T_tagger.")).all()
    assert t.declared_default.notna().all()


@needs_summary
def test_study_population_accounting_and_class_counts():
    p = _s()["population"]; tab = {r["truth"]: r for r in p["table"]}
    assert (tab["truth 0p"]["events_reaching_other"], tab["truth 1p"]["events_reaching_other"], tab["truth >=2p"]["events_reaching_other"]) == (2446, 2174, 387)
    assert sum(r["events_reaching_other"] for r in p["table"]) == p["n_events"] == 5007                    # = the validated numu-stage count of the TPC box
    assert tab["truth 0p"]["survive"] + tab["truth 1p"]["survive"] + tab["truth >=2p"]["survive"] == 1157 + 1373 + 251 == 2781   # = the validated `other`-stage count
    assert abs(tab["truth 0p"]["survival"] - 0.4730) < 5e-4 and abs(tab["truth 1p"]["survival"] - 0.6316) < 5e-4
    assert p["multi_candidate_events"] == 7 and p["n_reaching_candidates"] >= p["n_events"]


@needs_summary
def test_delta_split_inside_truth_1p_closes():
    s = {r["group"]: r for r in _s()["score_summary"]}
    assert s["truth 1p, Delta0"]["n"] + s["truth 1p, Delta+"]["n"] == s["truth 1p"]["n"] == 2174
    assert s["truth 0p, Delta0"]["n"] + s["truth 0p, Delta+"]["n"] == s["truth 0p"]["n"] == 2446
    assert s["truth 1p, Delta0"]["survive"] + s["truth 1p, Delta+"]["survive"] == s["truth 1p"]["survive"]


@needs_summary
def test_fill_default_classification_br2_default_is_detached_shower():
    ct = _s()["br2_default_vs_connected_crosstab"]            # {connected: {br2_default: n}}
    assert ct["false"]["true"] + ct["true"]["false"] == 5006 and ct["true"]["true"] == 1 and ct["false"]["false"] == 0        # br2 default <=> detached shower (one exception in 5,007 events)
    st = {(r["cls"], r["connected_label"]): r for r in _s()["strata"]["class_x_connected"]}
    assert st[(0, "attached (gap = 0)")]["n"] + st[(0, "detached (gap > 0)")]["n"] == 2446 and st[(1, "attached (gap = 0)")]["n"] + st[(1, "detached (gap > 0)")]["n"] == 2174
    assert st[(0, "detached (gap > 0)")]["frac_br2_default"] == 1.0 and st[(1, "attached (gap = 0)")]["frac_br2_default"] == 0.0 or st[(1, "attached (gap = 0)")]["frac_br2_default"] < 0.01


@needs_summary
def test_harmonized_denominator_mapping_closes():
    h = {r["denominator"]: r for r in _s()["harmonized"]}
    a = h["harmonized, truth 0p (35 MeV)"]["events_reaching_other"] + h["harmonized, truth 1p (35 MeV)"]["events_reaching_other"] + h["harmonized, truth >=2p (35 MeV)"]["events_reaching_other"]
    b = h["harmonized 0p50"]["events_reaching_other"] + h["harmonized Np50"]["events_reaching_other"]
    assert a == b == 3981                                                    # same harmonized events, two proton-category schemes
    assert h["loose TPC box, truth 0p (35 MeV)"]["survive"] == 1157


@needs_summary
def test_model_contribution_reconstruction_and_shap_additivity_pinned():
    t = _s()["tree_decomposition"]
    assert abs(t["sum_tree_differences"] - t["mean_margin_difference"]) < 1e-9 and abs(t["threshold_margin"] - np.arctanh(0.2)) < 1e-12
    assert t["n_trees_positive"] + t["n_trees_negative"] <= 215
    for s in _s()["shap"]:
        assert s["max_additivity_residual"] < 1e-8
