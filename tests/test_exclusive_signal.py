import numpy as np
import pandas as pd
from sbnd_single_photon import exclusive_signal as X, selection as SEL

CFG = SEL.load_config()
CUMS = ["cum_candidate_in_valid_event"] + ["cum_" + c["name"] for c in CFG["cuts"]]      # 7 flags: candidate + 6 cuts


def _cand(fi, ev, nu, depth, cat, matched, dom_q=1.0):
    r = dict(file_index=fi, ev=ev, c_nu_index=nu, policy_first=nu == 0, bdt_evaluable=depth >= 2, reco_proton_cat=cat,
             dom_nu_vx=10.0 if matched else 300.0, dom_nu_vy=0.0, dom_nu_vz=100.0, dom_q=dom_q, dom_q_cand=2.0)
    for i, c in enumerate(CUMS):
        r[c] = depth > i
    r["pass_final"] = depth == len(CUMS)
    return r


def _tables():
    sig = pd.DataFrame(dict(file_index=0, ev=range(6), x=10.0, y=0.0, z=100.0, truth_cat=[0, 1, 1, 0, 2, 1],
                            delta_pdg=[2114, 2214, 2214, 2114, 2114, 2214]))
    events = pd.DataFrame(dict(file_index=0, ev=range(6), wc_valid=[False, True, True, True, True, True]))
    rows = [_cand(0, 2, 0, 1, 0, False),                               # e2: unmatched candidate, no >20 MeV shower
            _cand(0, 3, 0, 2, 1, True),                                # e3: matched, stops before numu (passes cand, n20, numu not)
            _cand(0, 4, 0, 7, 0, False), _cand(0, 4, 1, 3, 2, True),   # e4: passing candidate is NOT the signal one; matched fails 'other'
            _cand(0, 5, 0, 7, 1, True)]                                # e5: selected, matched
    return sig, events, pd.DataFrame(rows)


def test_first_failure_is_mutually_exclusive_and_separates_views():
    sig, ev, c = _tables()
    t = X.signal_event_table(sig, ev, c, CFG).set_index("ev")
    assert t.first_fail_A.tolist() == ["wc_invalid", "no_candidate", "no_20mev_shower", "fail_numu", "selected", "selected"]
    assert t.first_fail_B.tolist() == ["wc_invalid", "no_candidate", "no_truth_matched_candidate", "fail_numu", "fail_other", "selected"]
    assert set(t.first_fail_A) <= set(X.REASONS_A) and set(t.first_fail_B) <= set(X.REASONS_B)
    ff = X.first_failure_table(t.reset_index(), "first_fail_A", X.REASONS_A)
    assert ff["all"].sum() == len(sig) and (ff[["0p", "1p", ">=2p"]].sum(axis=1) == ff["all"]).all()      # exact totals


def test_selection_uses_reco_only_truth_match_is_diagnostic():
    sig, ev, c = _tables()
    t = X.signal_event_table(sig, ev, c, CFG).set_index("ev")
    assert bool(t.loc[4, "A_final"]) and not bool(t.loc[4, "sel_is_matched"])        # selected although its passing candidate is not the signal one
    assert t.loc[4, "sel_reco_cat"] == 0 and t.loc[4, "match_reco_cat"] == 2         # analysis-selected vs truth-matched diagnostic category differ
    assert bool(t.loc[5, "A_final"]) and bool(t.loc[5, "match_passes_final"]) and t.loc[5, "n_pass"] == 1
    assert t.loc[0, "match_reco_cat"] == -1 and t.loc[1, "match_reco_cat"] == -1 and t.loc[2, "match_reco_cat"] == -1   # no candidate / none matched
    # flipping which candidate is the truth one must not change who passes
    c2 = c.copy(); c2["dom_nu_vx"] = 300.0
    t2 = X.signal_event_table(sig, ev, c2, CFG).set_index("ev")
    assert (t2.A_final == t.A_final).all() and (t2.first_fail_A == t.first_fail_A).all()


def test_first_policy_subset():
    sig, ev, c = _tables()
    t = X.signal_event_table(sig, ev, c, CFG, policy="first").set_index("ev")
    assert bool(t.loc[4, "A_final"])                       # nu_index 0 passes
    assert t.loc[4, "n_matched"] == 0                      # the matched candidate (nu 1) is not a 'first' candidate
    assert bool(t.loc[5, "A_final"]) and not bool(t.loc[3, "A_final"])


def test_cutflow_by_truth_denominators_and_monotone():
    sig, ev, c = _tables()
    t = X.signal_event_table(sig, ev, c, CFG)
    names = [s for s, _ in X.stage_defs(CFG)]
    cf = X.cutflow_by_truth(t, "A", names)
    d = cf[cf.stage == "truth_denominator"].set_index("group").N
    assert d["all"] == 6 and d["0p"] == 2 and d["1p"] == 3 and d[">=2p"] == 1 and d["all"] == d["0p"] + d["1p"] + d[">=2p"]
    n = cf[cf.group == "all"].N.values
    assert (np.diff(n) <= 0).all() and n[-1] == 2          # monotone, 2 selected
    r = cf[(cf.stage == "final") & (cf.group == "all")].iloc[0]
    assert r.lo68 <= r.fraction <= r.hi68


def test_migration_accounting_and_checkpoints():
    sig, ev, c = _tables()
    t = X.signal_event_table(sig, ev, c, CFG)
    cps = X.migration_checkpoints(t)
    a = cps["A_all_truth_events__matched_candidate"]
    assert a.row_total.tolist() == [2, 3, 1] and a.drop(columns="row_total").values.sum() == 6      # every truth event is in exactly one cell
    assert a.loc["truth 1p", "no candidate/unreco"] == 2 and a.loc["truth 0p", "no candidate/unreco"] == 1   # e1, e2 ; e0
    b = cps["B_events_with_matched_candidate"]
    assert b["no candidate/unreco"].sum() == 0 and b.row_total.sum() == 3
    d = cps["D_final_events__analysis_selected_candidate"]
    assert d.row_total.sum() == 2 and d.loc["truth >=2p", "reco 0p"] == 1 and d.loc["truth 1p", "reco 1p"] == 1
    dm = cps["D_final_events__matched_candidate"]
    assert dm.loc["truth >=2p", "reco >=2p"] == 1               # diagnostic matched candidate of event 4
    nrm = X.migration_matrix(t.truth_cat.values, t.match_reco_cat.values, normalize=True)
    nz = nrm.sum(axis=1).dropna()
    assert np.allclose(nz.values, 1.0)


def test_efficiency_and_delta_topology_totals():
    sig, ev, c = _tables()
    ta = X.signal_event_table(sig, ev, c, CFG); tf = X.signal_event_table(sig, ev, c, CFG, policy="first")
    e = X.efficiency_table(ta, tf).set_index(["policy", "truth_class"])
    assert e.loc[("any", "total"), "selected"] == 2 and e.loc[("any", "total"), "truth"] == 6
    assert e.loc[("any", "0p"), "truth"] + e.loc[("any", "1p"), "truth"] + e.loc[("any", ">=2p"), "truth"] == 6
    assert 0 < e.loc[("any", "total"), "lo68"] < e.loc[("any", "total"), "efficiency"] < e.loc[("any", "total"), "hi68"] < 1
    dt = X.delta_topology(ta)
    assert dt["truth_all_events"]["total"].sum() == 6 and dt["reco_final_selected_stage"]["total"].sum() == 2
    assert dt["truth_all_events"].loc["Delta0 -> n gamma", "0p"] == 2          # Delta charge is not the proton category


def test_official_adapter_and_event_key_join():
    ev = pd.DataFrame(dict(run=[1, 1, 2], subrun=[1, 1, 1], evt=[10, 11, 5], true_vertex_x=0.0, true_vertex_y=0.0, true_vertex_z=100.0,
                           true_proton_category=np.array([0, 1, 2], dtype=np.int8), delta_pdg=[2114, 2214, 2214], decay_nucleon_pdg=[2112, 2212, 2212],
                           photon_energy_mev=300.0, neutrino_energy_gev=1.0, vtx_in_active_tpc=[True, True, False], n_true_protons=[0, 1, 3]))
    s = X.signal_truth_from_official_events(ev)
    assert s.truth_cat.tolist() == [0, 1, 2] and s.in_region.tolist() == [True, True, False]
    table = pd.DataFrame(dict(run=[1, 1], subrun=[1, 1], evt=[10, 11], file_index=[7, 7], ev=[0, 1]))   # run 2 lost in WC production
    j, nmiss = X.attach_event_key(s, table)
    assert nmiss == 1 and len(j) == 2 and j.file_index.tolist() == [7, 7] and j.ev.tolist() == [0, 1]
    import pytest
    with pytest.raises(ValueError):
        X.attach_event_key(s, pd.concat([table, table]))
