import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd
from sbnd_single_photon import selection as SEL, truth as T

spec = importlib.util.spec_from_file_location("vat", Path(__file__).resolve().parents[1] / "scripts" / "validate_analysis_table.py")
V = importlib.util.module_from_spec(spec); spec.loader.exec_module(V)


def _tables():
    cfg = SEL.load_config()
    names = ["candidate_in_valid_event"] + [c["name"] for c in cfg["cuts"]]
    # 4 events: ev0 has two candidates, both pass (second has lower proton cat), ev1 one passing, ev2 candidate fails last cut, ev3 invalid/no cand
    rows = [dict(file_index=0, ev=0, c_nu_index=0, np=1, last=True), dict(file_index=0, ev=0, c_nu_index=1, np=0, last=True),
            dict(file_index=0, ev=1, c_nu_index=1, np=2, last=True), dict(file_index=0, ev=2, c_nu_index=0, np=0, last=False)]
    c = pd.DataFrame(rows)
    for n in names[:-1]:
        c["cum_" + n] = True
    c["cum_" + names[-1]] = c["last"]
    c["pass_final"] = c["last"]; c["policy_first"] = c.c_nu_index == 0; c["reco_proton_cat"] = c["np"].astype(np.int8)
    e = pd.DataFrame(dict(file_index=0, ev=[0, 1, 2, 3], wc_valid=[True, True, True, False],
                          t_code=[T.CODE["NC_PI0"], T.CODE["NUE_CC"], T.CODE["OTHER_NC"], T.CODE["COSMIC_NO_NU"]]))
    return c, e, cfg


def test_compute_counts_policies_and_choice():
    c, e, cfg = _tables()
    r = V.compute(c, e, cfg)
    last = "cum_" + cfg["cuts"][-1]["name"]
    assert r["n_events"] == 4 and r["n_valid"] == 3 and r["n_candidates"] == 4
    assert r["stages"][last] == dict(n_candidates=3, n_events_any=2, n_events_first=1)       # 'first' = nu_index 0 only
    # 'any': ev0 -> lowest nu_index passing (index 0, 1p); ev1 -> its only passing candidate (2p)
    comp = r["composition"]["any"]
    assert comp["NC_PI0"] == dict(n=1, n_0p=0, n_1p=1, n_ge2p=0) and comp["NUE_CC"] == dict(n=1, n_0p=0, n_1p=0, n_ge2p=1)
    assert r["composition"]["first"]["_total"]["n"] == 1 and "NUE_CC" not in r["composition"]["first"]
    assert comp["_total"]["n"] == 2


def test_no_event_counted_twice_when_two_candidates_pass():
    c, e, cfg = _tables()
    r = V.compute(c, e, cfg)
    assert r["composition"]["any"]["_total"]["n"] == r["stages"]["cum_" + cfg["cuts"][-1]["name"]]["n_events_any"]
