import json
import os
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from sbnd_single_photon import exclusive_signal as X, selection as SEL, signal_pipeline as SP, signal_master as SM
from sbnd_single_photon.truth import ActiveVolume

REPO = Path(__file__).resolve().parents[1]
CFG = SEL.load_config()
CUMS = ["cum_candidate_in_valid_event"] + ["cum_" + c["name"] for c in CFG["cuts"]]


def _cand(fi, ev, nu, depth, cat, matched):
    r = dict(file_index=fi, ev=ev, c_nu_index=nu, policy_first=nu == 0, bdt_evaluable=depth >= 2, reco_proton_cat=cat,
             dom_nu_vx=10.0 if matched else 300.0, dom_nu_vy=0.0, dom_nu_vz=100.0, dom_q=1.0, dom_q_cand=2.0)
    for i, c in enumerate(CUMS):
        r[c] = depth > i
    r["pass_final"] = depth == len(CUMS)
    return r


def _inputs():
    # 8 truth signal events (run/subrun/evt keyed): 6 arrive in the merged table (one of them wc.invalid), 2 NEVER arrive
    sig = pd.DataFrame(dict(run=1, subrun=1, evt=range(100, 108), reco1_unit="U", x=10.0, y=0.0, z=100.0, truth_cat=[0, 1, 1, 0, 2, 1, 0, 1],
                            delta_pdg=[2114, 2214, 2214, 2114, 2114, 2214, 2114, 2214], nucleon_pdg=2112, photon_mev=150., E=1., in_region=True, n_p35=0))
    events = pd.DataFrame(dict(file_index=0, ev=range(6), run=1, subrun=1, evt=range(100, 106), wc_valid=[False, True, True, True, True, True]))
    cands = pd.DataFrame([_cand(0, 2, 0, 1, 0, False), _cand(0, 3, 0, 2, 1, True), _cand(0, 4, 0, 7, 0, True), _cand(0, 5, 0, 7, 1, True)])
    return sig, events, cands


def _run():
    sig, events, cands = _inputs()
    arrived, missing = SP.split_arrived(sig, events)
    tabs = {p: SP.with_missing_rows(X.signal_event_table(arrived, events, cands, CFG, policy=p), missing, p) for p in ("any", "first")}
    return sig, arrived, missing, tabs


def test_missing_events_stay_in_the_denominator_and_fail_every_numerator():
    sig, arrived, missing, tabs = _run()
    assert len(arrived) == 6 and len(missing) == 2 and missing.evt.tolist() == [106, 107]
    t = tabs["any"]
    assert len(t) == 8 and (~t.arrived).sum() == 2                                     # the denominator is the truth set, not the arrived set
    assert (t[~t.arrived].first_fail_A == SP.MISSING_REASON).all() and not t[~t.arrived].A_final.any() and not t[~t.arrived].wc_valid.any()
    acc = SP.validate_accounting(8, t, tabs["first"], [s for s, _ in X.stage_defs(CFG)])
    assert acc["ok"] and acc["any"]["missing"] == 2 and acc["any"]["wc_invalid_arrived"] == 1 and acc["any"]["final"] == 2


def test_wc_invalid_and_missing_lower_efficiency_with_exact_binomial():
    _, _, _, tabs = _run()
    rep = SP.signal_report(tabs["any"], tabs["first"], CFG, label="t", region="r")
    eff = rep["efficiency"]; row = eff[(eff.policy == "any") & (eff.truth_class == "total")].iloc[0]
    assert row.selected == 2 and row.truth == 8 and row.efficiency == pytest.approx(0.25) and row.lo68 < 0.25 < row.hi68       # 2 / 8, not 2 / 6
    assert rep["missing"] == 2 and rep["wc_invalid_arrived"] == 1 and rep["n_truth"] == 8 and sum(rep["truth_class"].values()) == 8
    k = rep["selected_truth_to_reco"]; assert k.sum() == rep["final_any"]["total"]


def test_accounting_raises_if_an_event_is_lost():
    _, _, _, tabs = _run()
    stages = [s for s, _ in X.stage_defs(CFG)]
    with pytest.raises(AssertionError):
        SP.validate_accounting(9, tabs["any"], tabs["first"], stages)              # a truth event vanished
    bad = tabs["any"].copy(); bad.loc[0, "A_final"] = True
    with pytest.raises(AssertionError):
        SP.validate_accounting(8, bad, tabs["first"], stages)


def test_expected_yield_flows_from_the_report():
    _, _, _, tabs = _run()
    rep = SP.signal_report(tabs["any"], tabs["first"], CFG, label="t", region="r", pot_signal=1e20, exposure_pot=2e20)
    y = rep["expected_yield"]; assert y["total"] == pytest.approx(2 * rep["final_any"]["total"]) and sum(y["by_reco_channel"].values()) == pytest.approx(y["total"])


def test_template_rendering_refuses_missing_placeholders_and_has_all_15_sections():
    text = (REPO / "docs" / "analysis" / "OFFICIAL_NCDELTA_WC_ARRIVAL_REPORT_TEMPLATE.md").read_text()
    assert sum(1 for l in text.splitlines() if l.startswith("## ")) == 15
    with pytest.raises(KeyError):
        SP.render_template(text, {"LABEL": "x"})
    assert SP.render_template("a {{X}} b", {"X": "1"}) == "a 1 b"
    import re
    assert not re.search(r"\d\.\d+e|\b\d{3,}\b", re.sub(r"\{\{[A-Z0-9_]+\}\}|`[^`]*`", "", text.split("## 1.")[1]))      # no physics numbers hard-coded in the sections


def test_region_truth_and_split_arrived_partition():
    units = None
    rec = pd.DataFrame(dict(reco1_unit="U", run=[1, 1], subrun=1, evt=[1, 2], file_index=0, ev=[0, 1], signal_nu_index=0, vtx_x=0., vtx_y=0., vtx_z=100.,
                            truth_cat=[0, 1], delta_pdg=[2114, 2214], decay_nucleon_pdg=[2112, 2212], photon_energy_mev=100., nu_energy_gev=1., n_true_protons=[0, 1]))
    s = SP.region_truth(rec, ActiveVolume(), "tpc")
    ev = pd.DataFrame(dict(file_index=0, ev=[0], run=1, subrun=1, evt=[1]))
    a, m = SP.split_arrived(s, ev)
    assert len(a) == 1 and len(m) == 1 and len(a) + len(m) == len(s)


# ---- natural-CV rehearsal: the machinery reproduces the Phase-3 results exactly (data live outside Git; the committed comparison is always checked)
def test_committed_rehearsal_reproduces_phase3():
    d = REPO / "tables" / "official_signal" / "rehearsal_natural_bnb_cv"
    cmp = json.load(open(d / "rehearsal_comparison.json"))
    assert cmp["ALL"] and cmp["denominator_117"] and cmp["final_any_13"] and cmp["final_first_12"]
    s = json.load(open(d / "summary.json"))
    assert s["n_truth"] == 117 and s["final_any"]["total"] == 13 and s["final_first"]["total"] == 12 and s["truth_class"] == {"0p": 59, "1p": 46, ">=2p": 12}
    ref = REPO / "tables" / "exclusive_signal" / "natural_bnb_cv"
    for f in ("cutflow_A_any.csv", "cutflow_A_first.csv"):
        assert pd.read_csv(ref / f).round(10).equals(pd.read_csv(d / f).round(10))
    assert s["accounting"]["ok"]


@pytest.mark.skipif("SP_DATA" not in os.environ or not (Path(os.environ.get("SP_DATA", "/nonexistent")) / "analysis_tables" / "bnb_cv" / "events.parquet").exists(),
                    reason="derived tables are outside Git")
def test_rehearsal_recomputed_from_tables_matches_phase3():
    from sbnd_single_photon import natural_signal as NS
    spd = Path(os.environ["SP_DATA"]); T = spd / "analysis_tables" / "bnb_cv"
    events, cands = pd.read_parquet(T / "events.parquet"), pd.read_parquet(T / "candidates.parquet")
    sig_all = NS.to_signal_truth_table(pd.read_parquet(spd / "natural_ncdelta_bnb_cv" / "signal_neutrinos.parquet")); sig = sig_all[sig_all.in_region].reset_index(drop=True)
    tabs = {p: SP.with_missing_rows(X.signal_event_table(sig, events, cands, CFG, policy=p), sig.iloc[:0], p) for p in ("any", "first")}
    assert len(sig) == 117 and int(tabs["any"].A_final.sum()) == 13 and int(tabs["first"].A_final.sum()) == 12
