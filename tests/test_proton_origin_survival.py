"""Phase 17: proton origin, Delta-charge survival and the descriptive standardisation (roadmap P): synthetic checks of the helpers and pinned checks of the committed tables.

Nothing here changes a selection flag, threshold or policy.
"""
import hashlib
import itertools
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from sbnd_single_photon import origin_audit as OA

ROOT = Path(__file__).resolve().parents[1]
TAB = ROOT / "tables" / "proton_origin_survival_audit"
csv = lambda n: pd.read_csv(TAB / f"{n}.csv")
C = OA.ORIGIN_CATEGORIES


# ------------------------------------------------------------------------------------------------------------ origin taxonomy
def test_origin_category_is_exclusive_exhaustive_and_charge_aware():
    seen = set()
    for oc, d in itertools.product(["decay_proton", "fsi_created", "not_from_decay", "ambiguous", "unknown", "unlinked", None], ["Delta+", "Delta0"]):
        c = OA.origin_category(oc, d); assert c in C; seen.add(c)
    assert seen == set(C)
    assert OA.origin_category("decay_proton", "Delta+") == C[0] and OA.origin_category("fsi_created", "Delta0") == C[1] and OA.origin_category("fsi_created", "Delta+") == C[2]
    assert OA.origin_category("not_from_decay", "Delta0") == C[3] and OA.origin_category("ambiguous", "Delta+") == C[4] and OA.origin_category("unknown", "Delta+") == C[5]
    assert set(OA.ORIGIN_GROUP) == set(C) and OA.ORIGIN_GROUP[C[1]] == OA.ORIGIN_GROUP[C[2]] == OA.ORIGIN_GROUP[C[3]] == "FSI-like"
    assert OA.collapse_reco_state("proton-typed") == "proton-typed" and OA.collapse_reco_state("mu-typed") == "mu/pi-typed" and OA.collapse_reco_state("no row") == "no row / no candidate"


# ------------------------------------------------------------------------------------------------------------ standardisation helpers
def _synthetic(n=6000, seed=1, effect=0.0):
    """A confounded sample: group `hi` is concentrated in the high-rate stratum although the outcome depends on the stratum only (plus `effect` for hi)."""
    rng = np.random.default_rng(seed); s = rng.integers(0, 2, n); hi = rng.random(n) < np.where(s == 1, 0.8, 0.2); p = np.where(s == 1, 0.6, 0.2) + effect * hi
    return pd.DataFrame(dict(g=np.where(hi, "H", "L"), s=s.astype(str), y=(rng.random(n) < p).astype(int)))


def test_standardisation_removes_pure_confounding_and_keeps_a_true_effect():
    d = _synthetic(effect=0.0); r = OA.standardise(d, "g", "H", "L", "y", ["s"]); assert r["raw"] > 0.2 and abs(r["adjusted"]) < 0.04 and r["support_fraction"] == 1.0 and r["n_strata"] == 2        # raw confounded, adjusted ~ 0
    d = _synthetic(effect=0.15, seed=2); r = OA.standardise(d, "g", "H", "L", "y", ["s"]); assert abs(r["adjusted"] - 0.15) < 0.04


def test_common_support_is_reported_and_separate_from_the_adjustment():
    d = pd.DataFrame(dict(g=["H"] * 10 + ["L"] * 10, s=["a"] * 5 + ["b"] * 5 + ["a"] * 10, y=[1] * 10 + [0] * 10))      # stratum b has no L events
    r = OA.standardise(d, "g", "H", "L", "y", ["s"], min_count=3); assert r["support_fraction"] == 0.5 and r["n_strata"] == 1 and abs(r["raw"] - 1.0) < 1e-12 and abs(r["adjusted"] - 1.0) < 1e-12
    assert OA.standardise(d, "g", "H", "L", "y", ["s"], min_count=6)["n_strata"] == 0 and np.isnan(OA.standardise(d, "g", "H", "L", "y", ["s"], min_count=6)["adjusted"])
    assert OA.standardise(d, "g", "H", "L", "y", [])["n_strata"] == 1                                                    # no strata: the raw difference


def test_bootstrap_is_reproducible_and_brackets_the_estimate():
    d = _synthetic(effect=0.1, seed=3); a = OA.bootstrap_standardise(d, "g", "H", "L", "y", ["s"], n_boot=100, seed=5); b = OA.bootstrap_standardise(d, "g", "H", "L", "y", ["s"], n_boot=100, seed=5)
    assert a == b and a["adjusted_lo68"] <= a["adjusted"] <= a["adjusted_hi68"] and a["adjusted_hi68"] - a["adjusted_lo68"] < 0.1
    assert OA.bootstrap_standardise(d, "g", "H", "L", "y", ["s"], n_boot=100, seed=6) != a                                # a different seed is a different resample
    assert abs(OA.fraction_explained(0.05, 0.01) - 0.8) < 1e-12 and np.isnan(OA.fraction_explained(0.0, 0.0))
    w = OA.standardise(d, "g", "H", "L", "y", ["s"], weights="lo"); assert abs(w["adjusted"] - 0.1) < 0.05


# ------------------------------------------------------------------------------------------------------------ truth-1p and Delta closure
def test_truth_1p_denominator_and_delta_charge_closure():
    c = csv("origin_composition").set_index("origin"); assert c["all"].sum() == 5170 and c["Delta+"].sum() == 3673 and c["Delta0"].sum() == 1497
    a, b1, b2 = [c.loc[x] for x in C[:3]]; assert (a["Delta+"], a["Delta0"]) == (3301, 0) and (b1["Delta+"], b1["Delta0"]) == (0, 1476) and (b2["Delta+"], b2["Delta0"]) == (294, 0)       # no Delta0 decay protons
    assert (c.loc[C[3], "Delta+"], c.loc[C[3], "Delta0"], c.loc[C[4], "Delta+"], c.loc[C[4], "Delta0"]) == (5, 21, 73, 0) and C[5] not in c.index                                    # E: 0 events
    s = json.load(open(TAB / "summary.json")); assert s["n_truth_1p"] == 5170 and s["n_delta_plus"] + s["n_delta0"] == 5170
    dx = csv("origin_definition_support"); nuc = dx[dx["item"].str.startswith("decay nucleon")].set_index("index"); assert nuc.loc["Delta0", "2112"] == 1497 and nuc.loc["Delta+", "2212"] == 3673                  # decay nucleon: neutron for every Delta0


def test_phase8_origin_and_other_survival_reproduced():
    t = csv("origin_reproduction_phase8_totals").set_index("delta"); assert (t.loc["Delta+", "n_reaching_other"], t.loc["Delta0", "n_reaching_other"]) == (1541, 633) and t.n_reaching_other.sum() == 2174
    assert abs(t.loc["Delta+", "other_survival"] - 0.655) < 0.001 and abs(t.loc["Delta0", "other_survival"] - 0.574) < 0.002
    r = csv("origin_reproduction_phase8_other").set_index(["delta", "origin_class"]); assert r.loc[("Delta+", "decay_proton"), "n_reaching_other"] == 1367 and abs(r.loc[("Delta+", "decay_proton"), "other_survival"] - 0.671) < 0.001
    assert r.loc[("Delta+", "fsi_created"), "n_reaching_other"] == 137 and abs(r.loc[("Delta+", "fsi_created"), "other_survival"] - 0.540) < 0.001 and r.loc[("Delta+", "ambiguous"), "n_reaching_other"] == 35


def test_phase15_proton_state_and_phase16_anchoring_reproduced():
    p15 = pd.read_csv(ROOT / "tables" / "particle_pid_audit" / "proton_pid_by_topology.csv"); one = p15[(p15.group == "1") & (p15.proton_class == "proton-typed")].iloc[0]
    r = csv("reconstruction_by_origin").set_index("origin").loc["all truth 1p"]; assert round(r["frac_proton-typed"] * r["n"]) == one.n == 2802                                  # every proton-typed truth-1p proton has a candidate
    p16 = pd.read_csv(ROOT / "tables" / "vertex_provenance_audit" / "vertex_anchoring_by_stage.csv").query("tolerance_cm == 5 and topology == 'truth 1p'").iloc[0]
    a = csv("anchoring_by_origin").set_index("origin").loc["all truth 1p"]
    assert a["n"] == p16.n == 5086 and abs(a.anchored_traditional - p16.anchored_trad) < 1e-9 and abs(a.anchored_dl - p16.anchored_dl) < 1e-9 and abs(a.anchored_final - p16.anchored_final) < 1e-9


def test_cutflow_closure_by_origin_and_delta():
    c = csv("cutflow_by_origin"); stages = list(c.stage.unique()); n = c.pivot(index="stage", columns="origin", values="n").reindex(stages)
    assert (n.diff().dropna() <= 0).all().all() and (n.loc["candidate"] == c.groupby("origin").n_total.first()).all()                                                # monotone, every event has a candidate
    origins = [o for o in c.origin.unique() if o[0] in "ABCD" and not o.startswith("Delta")]
    assert n.loc["final", origins].sum() == n.loc["final", "all truth 1p"] and n.loc["final", "Delta+ (all origins)"] + n.loc["final", "Delta0 (all origins)"] == n.loc["final", "all truth 1p"]
    assert n.loc["candidate", "all truth 1p"] == 5170 and c[c.stage == "final"].set_index("origin").loc["A decay", "cumulative"] > c[c.stage == "final"].set_index("origin").loc["B2 Delta+ charge-exchange", "cumulative"]


def test_other_stage_strata_close_to_the_phase8_population():
    o = csv("other_by_origin"); assert o.n.sum() <= 2174 and o.n.sum() >= 2150 and o.set_index("o3").loc["A decay", "n"] == 1364                                                     # DL-record subset of the 2,174
    x = csv("other_by_origin_x_anchoring"); assert x.groupby("o3").n.sum().loc["A decay"] == 1364
    t = csv("other_by_origin_x_anchoring_x_proton_reco"); assert t[t.o3 == "A decay"].n.sum() == 1364 and (t.n >= 15).all()                                                      # cells below 15 events are not tabulated
    w = csv("other_decay_minus_origin_within_strata"); assert (w.n_decay >= 15).all() and (w.n_other_origin >= 15).all()


# ------------------------------------------------------------------------------------------------------------ adjustment tables
def test_adjustment_tables_are_internally_consistent():
    a = csv("delta_adjustment_steps"); f = a[(a.outcome == "final efficiency") & a.population.str.startswith("all")].set_index("step")
    assert abs(f.loc["1 raw", "raw"] - 0.05) < 0.002 and abs(f.loc["1 raw", "adjusted"] - f.loc["1 raw", "raw"]) < 1e-9 and f.loc["1 raw", "support_fraction_of_delta_plus"] == 1.0                        # the raw step is the raw difference
    assert (f.adjusted_lo68 <= f.adjusted + 1e-12).all() and (f.adjusted <= f.adjusted_hi68 + 1e-12).all() and (f.support_fraction_of_delta_plus > 0.8).all()
    assert abs(f.loc["7 + photon / attachment state", "adjusted"] - 0.05) < 0.015                                                                                                  # no reduction by the pre-registered covariates
    assert f.iloc[-1].adjusted < f.loc["7 + photon / attachment state", "adjusted"] and "exploratory" in f.index[-1].lower()                                                        # the exploratory step is labelled and reduces it
    d = csv("decay_vs_fsi_adjustment"); o = d[(d.comparison.str.contains("B2")) & (d.stage == "other | numu")].set_index("adjustment")
    assert o.loc["raw", "raw"] > 0.1 and abs(o.loc["+ proton KE", "adjusted"]) < 0.03 and (d.n_decay > 0).all()                                                                     # the old 67 vs 54 % effect is removed by proton KE


@pytest.mark.skipif(not (Path(os.environ.get("SP_DATA", "/nonexistent")) / "proton_origin_survival_audit" / "official_ncdelta" / "proton_origin_events.parquet").exists(), reason="detailed Phase-17 outputs not on this machine")
def test_adjustment_reproduces_from_the_stored_event_table():
    m = pd.read_parquet(Path(os.environ["SP_DATA"]) / "proton_origin_survival_audit" / "official_ncdelta" / "proton_origin_events.parquet"); d = m[m.anchor != "no DL record"]
    r = OA.standardise(d, "delta", "Delta+", "Delta0", "A_final", ["b_E", "b_cos", "b_pke"]); a = csv("delta_adjustment_steps"); row = a[(a.outcome == "final efficiency") & a.population.str.startswith("all") & (a.step == "3 + proton KE")].iloc[0]
    assert abs(r["adjusted"] - row.adjusted) < 1e-9 and abs(r["raw"] - row.raw) < 1e-9 and abs(r["support_fraction"] - row.support_fraction_of_delta_plus) < 1e-9
    b = OA.bootstrap_standardise(d, "delta", "Delta+", "Delta0", "A_final", ["b_E", "b_cos", "b_pke"], n_boot=300, seed=20261111); assert abs(b["adjusted_lo68"] - row.adjusted_lo68) < 1e-9


def test_ncpi0_mechanism_tables_close():
    m = csv("ncpi0_mechanism_by_origin").set_index("origin"); assert m.n_reaching_ncpi0.sum() == 1370 or m.n_reaching_ncpi0.sum() >= 1360
    assert m.loc["A decay", "kine_pair_present"] < m.loc["B1 Delta0 FSI-created", "kine_pair_present"] < m.loc["B2 Delta+ charge-exchange", "kine_pair_present"]
    n = csv("neutron_photon_rows_by_origin").set_index("origin"); assert n.loc["A decay", "events_with_neutron_photon_row"] < n.loc["B1 Delta0 FSI-created", "events_with_neutron_photon_row"] < n.loc["B2 Delta+ charge-exchange", "events_with_neutron_photon_row"]


def test_natural_cv_unavailability_is_recorded_and_nothing_selected_or_tuned():
    nat = csv("natural_cv_check"); assert nat.set_index("item").n["GENIE mother chain of the final proton (decay / FSI-created split)"] == -1 and nat.set_index("item").n["final-selection flags for these events"] == -1
    cfg = ROOT / "configs" / "baseline_selection.yaml"
    assert hashlib.sha256(cfg.read_bytes()).hexdigest() == "f3251b785be6e52ff3e429000a0319a6df8e42d2016ace2f51c7650a38e2fb0b"
    th = {c["name"]: c["threshold"] for c in yaml.safe_load(open(cfg))["cuts"]}
    assert th["single_photon_numu_score_gt_0p4"] == 0.4 and th["single_photon_other_score_gt_0p2"] == 0.2 and th["single_photon_ncpi0_score_gt_m0p05"] == -0.05
    assert hashlib.sha256((ROOT / "configs" / "analysis_definition_candidates.yaml").read_bytes()).hexdigest() == json.load(open(ROOT / "tables" / "analysis_definition_decisions" / "summary.json"))["metadata"]["analysis_definition_candidates_sha256"]
    txt = " ".join(p.read_text().lower() for p in (ROOT / "docs" / "analysis").glob("PROTON_ORIGIN_*.md")) + (ROOT / "docs" / "analysis" / "SIGNAL_PROTON_ORIGIN_SOURCE_AUDIT.md").read_text().lower()
    for bad in ("final purity", "final s/b", "significance of", "retuned", "we conclude that the origin causes"):
        assert bad not in txt
