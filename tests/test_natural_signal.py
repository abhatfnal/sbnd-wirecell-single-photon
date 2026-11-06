import numpy as np
import pandas as pd
from sbnd_single_photon import natural_signal as NS, selection as SEL


def _q():
    # event (0,0): two qualifying neutrinos, the FIRST (nu_k=0) is a far rock one; event (0,1): one in-box; event (1,0): two in-box
    return pd.DataFrame(dict(file_index=[0, 0, 0, 1, 1], ev=[0, 0, 1, 0, 0], nu_k=[0, 2, 1, 0, 3],
                             x=[-690.0, 10.0, 0.0, 5.0, -5.0], y=[0.0] * 5, z=[679.0, 100.0, 50.0, 60.0, 70.0]))


def test_select_signal_neutrino_prefers_in_box_then_lowest_index():
    s = NS.select_signal_neutrino(_q()).set_index(["file_index", "ev"])
    assert s.loc[(0, 0), "nu_k"] == 2 and s.loc[(0, 0), "n_signal_nu"] == 2 and s.loc[(0, 0), "n_signal_nu_in_box"] == 1
    assert s.loc[(0, 1), "nu_k"] == 1 and s.loc[(1, 0), "nu_k"] == 0 and s.loc[(1, 0), "n_signal_nu_in_box"] == 2
    assert len(s) == 3                                           # one row per event: an event counts once


def test_no_in_box_neutrino_falls_back_to_lowest_index_and_is_flagged():
    q = pd.DataFrame(dict(file_index=[0, 0], ev=[0, 0], nu_k=[1, 4], x=[-690.0, 700.0], y=[0.0, 0.0], z=[679.0, 900.0]))
    s = NS.select_signal_neutrino(q)
    assert len(s) == 1 and s.nu_k[0] == 1 and not s.selected_in_box[0]


def _tables():
    cfg = SEL.load_config(); st = NS.stage_columns(cfg)
    events = pd.DataFrame(dict(file_index=[0, 0, 0, 1], ev=[0, 1, 2, 0], wc_valid=[True, True, False, True]))
    rows = []
    def cand(fi, ev, nu, depth, cat):                            # passes the first `depth` stages (+ final if depth == len(stages))
        r = dict(file_index=fi, ev=ev, c_nu_index=nu, policy_first=nu == 0, bdt_evaluable=depth >= 3, reco_proton_cat=cat)
        for i, s in enumerate(st): r[s] = depth > i
        r["pass_final"] = depth == len(st); return r
    rows += [cand(0, 0, 0, 2, 0), cand(0, 0, 1, len(st), 1)]      # event (0,0): candidate 1 (not 'first') passes everything
    rows += [cand(0, 1, 0, len(st), 2)]                           # event (0,1): first candidate passes everything, >=2p
    rows += [cand(1, 0, 0, 3, 0)]                                 # event (1,0): stops after 3 stages
    return cfg, events, pd.DataFrame(rows)


def test_stage_counts_join_any_vs_first_and_missing_events():
    cfg, events, cands = _tables()
    sig = pd.DataFrame(dict(file_index=[0, 0, 0, 1, 9], ev=[0, 1, 2, 0, 0]))   # (9,0) is not in the table
    r = NS.stage_counts(sig, events, cands, cfg)
    assert r["n_signal_events"] == 5 and r["events_not_found_in_table"] == 1 and r["wc_valid"] == 3
    assert r["any"]["pass_final" if False else "cum_" + cfg["cuts"][-1]["name"]] == 2 and r["first"]["cum_" + cfg["cuts"][-1]["name"]] == 1
    assert r["any"]["reco_0p_1p_ge2p"] == [0, 1, 1]               # event (0,0): lowest-nu_index PASSING candidate is nu 1 (1p); event (0,1): 2p
    assert r["first"]["reco_0p_1p_ge2p"] == [0, 0, 1]             # (0,0) has no passing 'first' candidate
    assert r["any"]["cum_candidate_in_valid_event"] == 3          # event (0,2) has no candidate: not counted; invalid-event candidates handled by the table flags
