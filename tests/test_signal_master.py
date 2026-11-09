import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from sbnd_single_photon import signal_master as SM
from sbnd_single_photon.truth import ActiveVolume

REPO = Path(__file__).resolve().parents[1]
FB = ActiveVolume(x=(-210., 210.), y=(-210., 210.), z=(-1., 510.)); TPC = ActiveVolume()


def _fixture():
    # unit U0 (flatCAF f0, 3 events worth of signal), U1 (flatCAF f1), U2 has NO flatCAF child
    flat = pd.DataFrame(dict(name=["f0", "f1"], parents=["U0", "U1"], pot=[1e18, 2e18]))
    reco = pd.DataFrame(dict(name=["U0", "U1", "U2"], pot=[1e18, 2e18, 5e17], gen=[1000, 2000, 500], events=[2, 1, 1]))
    files = pd.DataFrame(dict(file_index=[0, 1], source_file=["f0", "f1"], n_events=[2, 1]))
    events = pd.DataFrame(dict(file_index=[0, 0, 1], ev=[0, 1, 0], run=[1, 1, 2], subrun=[1, 1, 1], evt=[10, 11, 12], signal_nu_index=[1, 0, 0]))
    # neutrinos: event (0,0): k=0 far rock qualifying (z=679, outside the filter box), k=1 in-box qualifying, k=2 CC Delta-radiative (does NOT qualify)
    rows = [dict(file_index=0, ev=0, pdg=14, isnc=1, rec_is_delta_rad=True, position_x=-690., position_y=0., position_z=679., E=1., rec_delta_pdg=2214, rec_nucleon_pdg=2212, n_p35=1, n_p_all=1, n_pi0=0, n_pic=0, n_n=0, rec_photon_e_gev=.2, genie_mode=1, resnum=0),
            dict(file_index=0, ev=0, pdg=14, isnc=1, rec_is_delta_rad=True, position_x=10., position_y=0., position_z=100., E=1.2, rec_delta_pdg=2114, rec_nucleon_pdg=2112, n_p35=0, n_p_all=0, n_pi0=0, n_pic=0, n_n=1, rec_photon_e_gev=.3, genie_mode=1, resnum=0),
            dict(file_index=0, ev=0, pdg=14, isnc=0, rec_is_delta_rad=True, position_x=0., position_y=0., position_z=50., E=1., rec_delta_pdg=2214, rec_nucleon_pdg=2212, n_p35=1, n_p_all=1, n_pi0=0, n_pic=0, n_n=0, rec_photon_e_gev=.1, genie_mode=1, resnum=0),
            dict(file_index=0, ev=1, pdg=14, isnc=1, rec_is_delta_rad=True, position_x=205., position_y=0., position_z=100., E=1., rec_delta_pdg=2114, rec_nucleon_pdg=2112, n_p35=3, n_p_all=3, n_pi0=0, n_pic=0, n_n=0, rec_photon_e_gev=.1, genie_mode=1, resnum=0),   # in filter box, outside TPC box
            dict(file_index=1, ev=0, pdg=12, isnc=1, rec_is_delta_rad=True, position_x=0., position_y=0., position_z=200., E=.8, rec_delta_pdg=2214, rec_nucleon_pdg=2212, n_p35=1, n_p_all=1, n_pi0=0, n_pic=0, n_n=0, rec_photon_e_gev=.15, genie_mode=1, resnum=0)]
    return flat, reco, files, events, pd.DataFrame(rows)


def _records():
    flat, reco, files, events, nu = _fixture()
    units = SM.build_units(flat, reco, files.set_index("source_file").n_events)
    return units, SM.build_records(events, nu, files, units, flat, filter_box=FB, tpc_box=TPC)


def test_units_one_to_one_and_missing_flatcaf_status():
    units, _ = _records()
    assert len(units) == 3 and units.set_index("reco1_unit").flatcaf_status.to_dict() == {"U0": "flatcaf_available", "U1": "flatcaf_available", "U2": "no_flatcaf_child"}
    flat, reco, files, *_ = _fixture()
    with pytest.raises(ValueError):
        SM.build_units(pd.concat([flat, flat.assign(name=["f0b", "f1b"])]), reco)        # two flatCAFs sharing one parent


def test_multi_signal_event_keeps_both_neutrinos_and_cc_does_not_qualify():
    _, rec = _records()
    e0 = rec[(rec.file_index == 0) & (rec.ev == 0)]
    assert len(e0) == 2 and e0.multi_signal_event.all() and e0.n_signal_nu.eq(2).all()      # both qualifying records kept; the CC Delta-radiative one is not signal
    assert e0.is_selected_signal.sum() == 1 and int(e0[e0.is_selected_signal].signal_nu_index.iloc[0]) == 1      # deterministic rule choice survives
    assert rec.groupby(SM.KEY).is_selected_signal.sum().eq(1).all()
    assert len(rec) == 4 and SM.build_events(rec).shape[0] == 3                                # 4 records, 3 events: an event counts once


def test_region_denominator_rule_and_region_dependence():
    units, rec = _records()
    all_ = SM.region_records(rec, None); fb = SM.region_records(rec, FB); tpc = SM.region_records(rec, TPC)
    assert (len(all_), len(fb), len(tpc)) == (3, 3, 2)                                          # event (0,1) is in the filter box but outside the TPC box
    sel = fb[(fb.file_index == 0) & (fb.ev == 0)].iloc[0]
    assert sel.signal_nu_index == 1 and sel.n_in_region == 1                                   # the far rock neutrino is never the signal interaction of the event
    assert SM.region_records(rec, None).query("file_index == 0 and ev == 0").iloc[0].n_in_region == 2   # without a region cut both qualify: flagged


def test_denominator_keeps_pot_throws_and_truth_separate():
    units, rec = _records()
    d = SM.denominator_summary(rec, units, TPC, label="tpc")
    assert d["N_signal_truth"] == 2 and d["POT_signal_sample"] == pytest.approx(3e18) and d["generated_throws"] == 3000     # U2 (no flatCAF) excluded from both
    assert d["truth_class"] == {"0p": 1, "1p": 1, "ge2p": 0} and d["delta"] == {"Delta0": 1, "Delta+": 1}
    assert d["R_signal_per_POT"] == pytest.approx(2 / 3e18) and "NOT the efficiency denominator" in d["NOTE"]
    d1 = SM.denominator_summary(rec, units, TPC, label="tpc", unit_subset={"U0"})               # same S for numerator and POT
    assert d1["N_signal_truth"] == 1 and d1["POT_signal_sample"] == pytest.approx(1e18)
    assert SM.denominator_summary(rec, units, FB, label="fb")["N_signal_truth"] == 3


def test_committed_official_denominators():
    d = json.load(open(REPO / "tables" / "official_signal" / "denominators.json"))
    assert d["filter_box"]["N_signal_truth"] == 13773 and d["active_tpc"]["N_signal_truth"] == 12427
    assert d["active_tpc"]["truth_class"] == {"0p": 5863, "1p": 5557, "ge2p": 1007} and sum(d["filter_box"]["truth_class"].values()) == 13773
    assert d["filter_box"]["delta"] == {"Delta0": 7599, "Delta+": 6174}
    assert d["filter_box"]["POT_signal_sample"] == pytest.approx(2.83853154e21) and d["filter_box"]["generated_throws"] == 197212500
    assert d["no_region_cut"]["n_events_with_several_in_region"] == 6                           # the six multi-signal events stay visible
    assert d["active_tpc"]["R_signal_per_1e20_POT"] == pytest.approx(12427 / 2.83853154e21 * 1e20)


def test_regions_config_has_no_invented_fv():
    r = SM.load_regions()
    assert set(r) == {"filter_box", "active_tpc"} and r["active_tpc"] == TPC and r["filter_box"] == FB
