import numpy as np
import awkward as ak
import pytest
from sbnd_single_photon import truth_signal as TS

MP = TS.PROTON_MASS_GEV


def _ev(nus, **kw):
    """nus: list of dict(pdg,isnc,mode,res,E,pos,prims=[(pdg, KE_MeV or E_GeV)]) for ONE event. Primary energy given as KE (MeV) for hadrons, total GeV for photons."""
    prim_pdg, prim_e, nprim = [], [], []
    for n in nus:
        nprim.append(len(n["prims"]))
        for p, v in n["prims"]:
            prim_pdg.append(p)
            prim_e.append(v / 1000.0 + MP if p == 2212 else (v / 1000.0 if p == 22 else v))
    return dict(pdg=[[n.get("pdg", 14) for n in nus]], isnc=[[n.get("isnc", 1) for n in nus]],
                mode=[[n.get("mode", 1) for n in nus]], res=[[n.get("res", 0) for n in nus]],
                E=[[n.get("E", 1.0) for n in nus]], x=[[n["pos"][0] for n in nus]], y=[[n["pos"][1] for n in nus]],
                z=[[n["pos"][2] for n in nus]], prim_pdg=[prim_pdg], prim_e=[prim_e], nprim=[nprim])


def _run(events, **kw):
    cat = lambda k: [e[k][0] for e in events]
    return TS.signal_truth(cat("pdg"), cat("isnc"), cat("mode"), cat("res"), cat("E"), cat("x"), cat("y"), cat("z"),
                           cat("prim_pdg"), cat("prim_e"), nprim=cat("nprim"), **kw)


SIG = dict(pos=(10.0, 20.0, 100.0), prims=[(14, 0.4), (22, 150.0), (2212, 80.0), (2112, 0.5)])


def test_proxy_and_proton_categories():
    ev0p = _ev([dict(SIG, prims=[(14, 0.4), (22, 150.0), (2112, 0.5)])])
    ev1p = _ev([SIG])
    ev2p = _ev([dict(SIG, prims=[(22, 150.0), (2212, 80.0), (2212, 200.0)])])
    r = _run([ev0p, ev1p, ev2p])
    assert r["is_ncdelta_rad_proxy"].tolist() == [True, True, True]
    assert r["n_true_protons"].tolist() == [0, 1, 2]
    assert r["true_proton_category"].tolist() == [0, 1, 2]
    assert np.allclose(r["photon_energy_mev"], 150.0)
    assert r["true_vertex_z"].tolist() == [100.0] * 3
    assert r["vtx_in_active_tpc"].all() and r["vtx_in_filter_box"].all()


def test_proton_threshold_is_strict_and_configurable():
    e = _ev([dict(SIG, prims=[(22, 150.0), (2212, 34.9), (2212, 35.1)])])
    assert _run([e])["n_true_protons"][0] == 1                       # 34.9 fails, 35.1 passes (the exact boundary is meaningless at float32 precision)
    assert _run([e], proton_ke_mev=10.0)["n_true_protons"][0] == 2
    assert _run([e], proton_ke_mev=50.0)["n_true_protons"][0] == 0
    assert _run([e])["n_true_protons_all_ke"][0] == 2


def test_deexcitation_photon_does_not_make_proxy():
    e = _ev([dict(SIG, prims=[(22, 6.2), (2212, 80.0)])])          # 6.2 MeV nuclear line
    r = _run([e])
    assert not r["is_ncdelta_rad_proxy"][0] and r["signal_nu_index"][0] == -1
    assert r["true_proton_category"][0] == -1 and np.isnan(r["photon_energy_mev"][0])


@pytest.mark.parametrize("kw", [dict(isnc=0), dict(mode=0), dict(res=3)])
def test_proxy_requires_nc_res_delta1232(kw):
    assert not _run([_ev([dict(SIG, **kw)])])["is_ncdelta_rad_proxy"][0]


def test_unavailable_quantities_are_not_fabricated():
    r = _run([_ev([SIG])], from_filter_stream=True)
    assert set(TS.UNAVAILABLE_FROM_CAF) == {"delta_pdg", "delta_charge", "decay_nucleon_pdg"}
    for k in TS.UNAVAILABLE_FROM_CAF:
        assert (r[k] == 0).all()


def test_is_ncdelta_radiative_is_tristate_never_zero():
    r = _run([_ev([SIG])])
    assert r["is_ncdelta_radiative"][0] == -1                      # not a filter stream: unknown, never 0
    r2 = _run([_ev([dict(SIG, isnc=0)])])
    assert r2["is_ncdelta_radiative"][0] == -1
    rs = _run([_ev([dict(SIG, isnc=0)])], from_filter_stream=True)  # proxy fails on a stream event: still 1, proxy False
    assert rs["is_ncdelta_radiative"][0] == 1 and not rs["is_ncdelta_rad_proxy"][0] and not rs["proxy_recovers_stream"][0]


def test_multi_neutrino_event_picks_the_signal_one_and_counts_candidates():
    dirt = dict(pdg=14, isnc=0, mode=0, pos=(0.0, 0.0, 900.0), prims=[(2212, 100.0)])
    other = dict(SIG, pos=(1.0, 2.0, 3.0), prims=[(22, 80.0), (2212, 50.0), (2212, 60.0), (2212, 70.0)])
    e = _ev([dirt, SIG, other])
    r = _run([e])
    assert r["signal_nu_index"][0] == 1 and r["n_signal_nu_candidates"][0] == 2
    assert r["n_true_protons"][0] == 1 and r["true_vertex_z"][0] == 100.0


def test_vertex_regions_filter_box_vs_active_tpc():
    e = _ev([dict(SIG, pos=(205.0, 0.0, 100.0))])
    r = _run([e])
    assert r["vtx_in_filter_box"][0] and not r["vtx_in_active_tpc"][0]


def test_empty_event_and_vectorised():
    empty = dict(pdg=[[]], isnc=[[]], mode=[[]], res=[[]], E=[[]], x=[[]], y=[[]], z=[[]], prim_pdg=[[]], prim_e=[[]], nprim=[[]])
    r = _run([empty, _ev([SIG]), empty])
    assert r["is_ncdelta_rad_proxy"].tolist() == [False, True, False]
    assert r["signal_nu_index"].tolist() == [-1, 0, -1]
    assert r["n_true_protons"].tolist() == [-1, 1, -1]


def test_prim_columns_regrouped_with_nprim_not_mixed_across_neutrinos():
    a = dict(SIG, prims=[(22, 150.0), (2212, 80.0)])
    b = dict(SIG, isnc=0, pos=(0.0, 0.0, 50.0), prims=[(2212, 90.0), (2212, 91.0), (2212, 92.0)])
    r = _run([_ev([b, a])])                                        # the signal neutrino is second; its protons are NOT b's
    assert r["signal_nu_index"][0] == 1 and r["n_true_protons"][0] == 1
