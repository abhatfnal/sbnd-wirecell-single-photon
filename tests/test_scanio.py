import numpy as np
from sbnd_single_photon import scanio as X, selection as SEL


def mk():
    # 5 events: e0 valid, 2 cands (both pass everything); e1 valid, 2 cands (only nu_index 1 passes); e2 valid, no cand;
    # e3 INVALID with a passing-looking candidate; e4 valid, 1 cand that is not BDT-evaluable (NaN scores)
    t = dict(ev_valid=np.array([1, 1, 1, 0, 1], bool),
             c_gev=np.array([0, 0, 1, 1, 3, 4]), c_nu_index=np.array([0, 1, 0, 1, 0, 0]),
             c_shw_sp_filled=np.array([1, 1, 1, 1, 1, 0.]),
             c_shw_sp_n_20mev_showers=np.array([2, 2, 2, 2, 2, 0.]),
             c_shw_sp_n_20br1_showers=np.array([1, 1, 2, 1, 1, 0.]))
    for m in X.MODELS:
        t[f"c_score_{m}"] = np.array([.9, .9, .9, .9, .9, np.nan])
    t["c_flash_group"] = np.array([5, 5, 7, 8, 1, 1.])
    t["pot_total"] = 2e19
    return t


def test_candidate_vs_event_bookkeeping_and_policies():
    cfg = SEL.load_config(); t = mk()
    ch = X.candidate_chain(t, cfg)
    final = ch[cfg["cuts"][-1]["name"]]
    assert final.tolist() == [True, True, False, True, False, False]       # invalid-event cand never passes
    assert X.event_pass(t, final, "any").tolist() == [True, True, False, False, False]
    assert X.event_pass(t, final, "first").tolist() == [True, False, False, False, False]
    assert X.chosen_candidate(t, final, "any").tolist() == [0, 3, -1, -1, -1]


def test_cutflow_rows_and_rates():
    rows = {r["stage"]: r for r in X.cutflow_rows(mk(), SEL.load_config())}
    assert rows["all_events"]["n_events_any"] == 5 and rows["wc_valid"]["n_events_any"] == 4
    assert rows["candidate_exists"]["n_events_any"] == 3 and rows["candidate_exists"]["n_events_first"] == 3
    last = rows["cum:n_20br1_showers_eq1"]
    assert (last["n_candidates"], last["n_events_any"], last["n_events_first"]) == (3, 2, 1)
    assert abs(last["stored_per_1e20_genPOT_any"] - 2 / 2e19 * 1e20) < 1e-9
    assert rows["(info) bdt_evaluable_candidates"]["n_candidates"] == 4     # e3's candidates counted only through valid flag


def test_rate_zero_pot_is_nan():
    r, e = X.rate(5, 0.0)
    assert np.isnan(r) and np.isnan(e)


def test_dedup_any_keeps_longest_per_flash_group():
    t = mk()
    # event 0: both candidates in flash group 5 -> only nu_index 0 survives; event 1: groups 7 and 8 -> both survive
    assert X.dedup_keep(t).tolist() == [True, False, True, True, True, True]
    final = X.candidate_chain(t, SEL.load_config())["n_20br1_showers_eq1"]
    assert X.event_pass(t, final, "dedup_any").tolist() == [True, True, False, False, False]


def test_completeness_flags_missing_files():
    t = dict(n_files=3, ev_valid=np.zeros(30, bool))
    assert X.completeness(t, 3, 30)["complete"]
    assert not X.completeness(t, 4, 30)["complete"]
    assert not X.completeness(t, 3, 31)["complete"]
