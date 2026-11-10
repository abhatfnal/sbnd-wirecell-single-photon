"""Differential-efficiency machinery: accounting identities on synthetic data (no ROOT, no derived data) + pinned official numbers (small committed summary)."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from sbnd_single_photon import differential as DF, exclusive_signal as X, signal_pipeline as SP

REPO = Path(__file__).resolve().parents[1]


def synth(n=4000, seed=1):
    rng = np.random.default_rng(seed)
    t = pd.DataFrame(dict(run=1, subrun=1, evt=np.arange(n), truth_cat=rng.integers(0, 3, n), delta_pdg=rng.choice([2114, 2214], n),
                          photon_energy_mev=rng.exponential(200, n), cos_theta_beam=rng.uniform(-1, 1, n), vtx_z=rng.uniform(0, 500, n)))
    t["arrived"] = np.ones(n, bool); t.loc[0, "arrived"] = False                       # the production-missing event stays in the denominator
    t["wc_valid"] = t.arrived & (rng.random(n) > 0.002)
    cols = {}
    alive = t.wc_valid.to_numpy().copy()
    for c, p in (("A_candidate", .9), ("A_n20mev", .7), ("A_bdt_evaluable", .99), ("A_numu", .6), ("A_other", .5), ("A_ncpi0", .5), ("A_nue", 1.0), ("A_n20br1", .85)):
        alive = alive & (rng.random(n) < p); cols[c] = alive.copy()
    for c, v in cols.items():
        t[c] = v
    t["A_final"] = t.A_n20br1
    t["A_final_first"] = t.A_final & (rng.random(n) < .95)
    seq = [(DF.MISSING, t.arrived), ("wc_invalid", t.wc_valid), ("no_candidate", t.A_candidate), ("no_20mev_shower", t.A_n20mev), ("bdt_not_evaluable", t.A_bdt_evaluable),
           ("fail_numu", t.A_numu), ("fail_other", t.A_other), ("fail_ncpi0", t.A_ncpi0), ("fail_nue", t.A_nue), ("fail_n20br1", t.A_n20br1)]
    ff = np.array(["selected"] * n, object); done = np.zeros(n, bool)
    for r, ok in seq:
        h = (~ok.to_numpy()) & ~done; ff[h] = r; done |= h
    t["first_fail"] = ff
    return t


STAGE_COLS = [(s, dict(DF.STAGES)[s]) for s in ("candidate", "n20mev", "bdt_evaluable", "numu", "other", "ncpi0", "n20br1", "final")]
EDGES = [0, 50, 100, 200, 400, 800]


def test_first_failure_is_exclusive_and_exhaustive():
    t = synth()
    assert set(t.first_fail) <= set(DF.FIRST_FAIL) and len(t.first_fail) == len(t)
    assert (t.first_fail == "selected").sum() == t.A_final.sum()
    assert (t.first_fail == DF.MISSING).sum() == 1


def test_binned_accounting_closes_including_overflow_and_missing_event():
    t = synth(); t.loc[5, "photon_energy_mev"] = 5000.0; t.loc[6, "photon_energy_mev"] = np.nan
    e = DF.efficiency_in_bins(t, "photon_energy_mev", EDGES, ["all", "truth_0p", "truth_1p", "truth_ge2p", "Delta0", "Delta+"], STAGE_COLS)
    assert DF.check_closure(e)
    for g, m in DF.group_masks(t, ["all", "truth_0p", "truth_1p", "truth_ge2p", "Delta0", "Delta+"]).items():
        s = e[(e.group == g) & (e.stage == "final")].denominator.sum()
        assert s == m.sum()                                               # bins + underflow + overflow + no-value == group
    assert e[(e.group == "all") & (e.stage == "final") & (e.kind == "overflow")].denominator.iloc[0] >= 1
    f = DF.first_failure_in_bins(t, "photon_energy_mev", EDGES, ["all", "truth_1p"])           # asserts closure internally
    d = f[(f.group == "all") & (f.kind == "bin") & (f.bin == 1)]
    assert abs(d.fraction.sum() - 1) < 1e-12 and d.denominator.nunique() == 1
    assert (f.groupby(["variable", "group", "kind", "bin"])["count"].sum() == f.groupby(["variable", "group", "kind", "bin"]).denominator.first()).all()


def test_numerator_never_exceeds_denominator_and_cumulative_is_monotone():
    t = synth(); e = DF.efficiency_in_bins(t, "cos_theta_beam", [-1, -.5, 0, .5, 1], ["all", "truth_0p"], STAGE_COLS)
    assert (e.numerator <= e.denominator).all()
    p = e.pivot_table(index=["group", "kind", "bin"], columns="stage", values="numerator")[["candidate", "n20mev", "bdt_evaluable", "numu", "other", "ncpi0", "n20br1"]]
    assert (p.diff(axis=1).iloc[:, 1:] <= 0).all().all()


def test_conditional_survival_is_pass_over_reached_not_over_denominator():
    t = synth(); e = DF.efficiency_in_bins(t, "photon_energy_mev", EDGES, ["all"], STAGE_COLS)
    r = e[(e.stage == "other") & (e.kind == "bin") & (e.bin == 2)].iloc[0]
    m = (DF.assign_bins(t.photon_energy_mev.to_numpy(), EDGES) == 2)
    assert r.n_reach == int((m & t.A_numu).sum()) and r.numerator == int((m & t.A_other).sum())
    assert abs(r.survival - r.numerator / r.n_reach) < 1e-12 and r.survival > r.efficiency       # conditional >= cumulative
    assert r.denominator == int(m.sum())


def test_assign_bins_edges_and_flow():
    b = DF.assign_bins(np.array([-1.0, 0.0, 49.9, 50.0, 800.0, 801.0, np.nan]), EDGES)
    assert b.tolist() == [-1, 0, 0, 1, 4, 5, -2]                                 # last in-range bin closed on the right; flows explicit


def test_truth_proton_ke_binning_matches_threshold_and_class_totals():
    bins = DF.load_bins()["variables"]
    e = bins["lead_proton_ke_mev"]["edges"]; assert e[0] == 35 and e == sorted(e)               # truth-1p/>=2p leading KE starts at the provisional threshold
    assert bins["max_sub35_proton_ke_mev"]["edges"][-1] == 35
    t = synth(); t["lead_proton_ke_mev"] = np.where(t.truth_cat >= 1, 35 + np.random.default_rng(2).exponential(100, len(t)), np.nan)
    ee = DF.efficiency_in_bins(t, "lead_proton_ke_mev", e, ["all", "truth_1p"], STAGE_COLS)
    assert ee[(ee.group == "all") & (ee.stage == "final") & (ee.kind == "novalue")].denominator.iloc[0] == int((t.truth_cat == 0).sum())   # truth-0p has no leading proton


def test_class_and_delta_totals():
    t = synth(); g = DF.group_masks(t, ["truth_0p", "truth_1p", "truth_ge2p", "Delta0", "Delta+"])
    assert g["truth_0p"].sum() + g["truth_1p"].sum() + g["truth_ge2p"].sum() == len(t) and g["Delta0"].sum() + g["Delta+"].sum() == len(t)


def test_stage_decomposition_telescopes_to_the_log_efficiency_ratio():
    t = synth(); d = DF.stage_decomposition(t, "truth_0p", "truth_1p", n_boot=20)
    e0 = t[t.truth_cat == 0].A_final.mean(); e1 = t[t.truth_cat == 1].A_final.mean()
    assert abs(d.attrs["total_ln_ratio"] - np.log(e1 / e0)) < 1e-9


def test_missing_event_retained_by_the_event_table_builder():
    arr = pd.DataFrame(dict(run=[1], subrun=[1], evt=[1], reco1_unit="u", x=0., y=0., z=100., truth_cat=0, delta_pdg=2114, nucleon_pdg=2112, photon_mev=100., E=1., in_region=True, n_p35=0,
                            region="r", n_in_region=1, file_index=0, ev=0))
    mis = arr.assign(evt=2, file_index=np.nan, ev=np.nan)
    out = SP.with_missing_rows(pd.DataFrame(dict(run=[1], subrun=[1], evt=[1], A_final=[True], A_candidate=[True], wc_valid=[True], n_pass=[1], first_fail_A=["selected"], policy="any")), mis, "any")
    assert len(out) == 2 and not out.arrived.iloc[1] and out.first_fail_A.iloc[1] == DF.MISSING


def _te(**kw):
    base = dict(photon_px=[0.1], photon_py=[0.0], photon_pz=[0.1], photon_sx=[0.0], photon_sy=[0.0], photon_sz=[0.0], photon_ex=[3.0], photon_ey=[0.0], photon_ez=[4.0],
                photon_end_process=[36], photon_contained=[1], nu_dir_x=[0.0], nu_dir_y=[0.0], nu_dir_z=[1.0])
    base.update({k: [v] if not isinstance(v, list) else v for k, v in kw.items()})
    return pd.DataFrame(base)


def test_conversion_distance_helper_is_geometric_and_only_defined_for_conversions():
    assert abs(DF.conv_distance(_te()).iloc[0] - 5.0) < 1e-12
    assert np.isnan(DF.conv_distance(_te(photon_end_process=51)).iloc[0])                      # Compton end: not a conversion
    assert np.isnan(DF.conv_distance(_te(photon_end_process=60, photon_contained=0)).iloc[0])  # left the volume
    assert DF.classify_photon_end(_te(photon_end_process=-1, photon_contained=-1)).iloc[0] == "no_photon"
    assert abs(DF.photon_truth_variables(_te()).cos_theta_beam.iloc[0] - np.sqrt(0.5)) < 1e-12


def test_official_summary_is_consistent_with_the_baseline():
    p = REPO / "tables" / "differential_efficiency" / "summary.json"
    if not p.exists():
        pytest.skip("differential summary not generated yet")
    s = json.loads(p.read_text())["denominator"]
    assert s["tpc_box"] == 12427 and s["final_any"] == 1153 and s["final_first"] == 1101 and s["missing"] == 1
    assert sum(s["by_class"].values()) == 12427 and sum(s["by_delta"].values()) == 12427 and sum(s["first_fail"].values()) == 12427
    assert s["first_fail"]["selected"] == 1153 and s["first_fail"][DF.MISSING] == 1
