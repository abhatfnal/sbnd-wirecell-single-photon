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


# ---- GENIE-record ancestry (GenieEvtRecTree) -------------------------------------------------------------------------
def test_record_ancestry_direct_and_chain_and_negative():
    # record: 0 nu_mu, 1 Ar40, 2 Delta0(2114,st3), 3 n(st14, daughter), 4 gamma(st1, mother Delta)
    pdg = [14, 1000180400, 2114, 2112, 22]; st = [0, 0, 3, 14, 1]; fm = [-1, -1, 0, 2, 2]; fd = [-1, -1, 3, -1, -1]; ld = [-1, -1, 4, -1, -1]
    e = [0, 0, 1.2, 0.9, 0.18]
    r = TS.genie_record_ancestry(pdg, st, fm, fd, ld, e)
    assert r["is_delta_rad"] and r["delta_pdg"] == 2114 and r["nucleon_pdg"] == 2112 and r["nucleon_status"] == 14
    assert r["photon_e_gev"] == 0.18 and not r["via_photon"]
    # Delta+ -> p gamma via an in-nucleus photon: gamma(st1) <- gamma(st3) <- Delta+
    pdg = [14, 2214, 2212, 22, 22]; st = [0, 3, 14, 3, 1]; fm = [-1, 0, 1, 1, 3]; fd = [-1, 2, -1, 4, -1]; ld = [-1, 3, -1, 4, -1]
    r = TS.genie_record_ancestry(pdg, st, fm, fd, ld, [0] * 5)
    assert r["is_delta_rad"] and r["delta_pdg"] == 2214 and r["nucleon_pdg"] == 2212 and r["via_photon"]
    # photon from a de-excitation (mother = nucleus) or a pi0-like parent is NOT signal; neither is Delta++ / Delta-
    for mother_pdg in (1000180390, 2224, 1114, 111):
        pdg = [14, mother_pdg, 22]; st = [0, 3, 1]; fm = [-1, 0, 1]
        assert not TS.genie_record_ancestry(pdg, st, fm, [-1] * 3, [-1] * 3)["is_delta_rad"]
    # a status != 1 photon from a Delta does not count (must be an exiting photon)
    pdg = [14, 2114, 22]; st = [0, 3, 3]; fm = [-1, 0, 1]
    assert not TS.genie_record_ancestry(pdg, st, fm, [-1] * 3, [-1] * 3)["is_delta_rad"]


def test_signal_truth_with_record_fills_delta_fields_and_resolves_tristate():
    ev = _ev([dict(SIG, isnc=1), dict(pos=(0.0, 0.0, 900.0), isnc=0, mode=0, prims=[(2212, 100.0)])])
    rec = dict(is_delta_rad=[[True, False]], delta_pdg=[[2114, 0]], nucleon_pdg=[[2112, 0]], nucleon_status=[[14, -1]],
               photon_e_gev=[[0.15, float("nan")]])
    cat = lambda k: [ev[k][0]]
    r = TS.signal_truth(cat("pdg"), cat("isnc"), cat("mode"), cat("res"), cat("E"), cat("x"), cat("y"), cat("z"),
                        cat("prim_pdg"), cat("prim_e"), nprim=cat("nprim"), record=rec)
    assert r["is_ncdelta_radiative"][0] == 1 and r["delta_pdg"][0] == 2114 and r["delta_charge"][0] == 0 and r["decay_nucleon_pdg"][0] == 2112
    assert r["signal_nu_index"][0] == 0 and np.isclose(r["photon_energy_record_mev"][0], 150.0)
    # record says not Delta ancestry -> 0 (resolved), even if the proxy fires
    rec0 = dict(rec, is_delta_rad=[[False, False]])
    r0 = TS.signal_truth(cat("pdg"), cat("isnc"), cat("mode"), cat("res"), cat("E"), cat("x"), cat("y"), cat("z"),
                         cat("prim_pdg"), cat("prim_e"), nprim=cat("nprim"), record=rec0)
    assert r0["is_ncdelta_radiative"][0] == 0 and r0["is_ncdelta_rad_proxy"][0] and not r0["proxy_agrees_with_record"][0]
    # Delta+ -> charge +1
    recp = dict(rec, delta_pdg=[[2214, 0]], nucleon_pdg=[[2212, 0]])
    rp = TS.signal_truth(cat("pdg"), cat("isnc"), cat("mode"), cat("res"), cat("E"), cat("x"), cat("y"), cat("z"),
                         cat("prim_pdg"), cat("prim_e"), nprim=cat("nprim"), record=recp)
    assert rp["delta_charge"][0] == 1 and rp["decay_nucleon_pdg"][0] == 2212


def test_record_ancestry_jagged_links_by_index_and_rejects_bad_index():
    records = dict(StdHepPdg=ak.Array([[14, 2114, 22], [14, 2112, 22]]), StdHepStatus=ak.Array([[0, 3, 1], [0, 1, 1]]),
                   StdHepFm=ak.Array([[-1, 0, 1], [-1, 0, 0]]), StdHepFd=ak.Array([[-1, 2, -1], [-1, -1, -1]]),
                   StdHepLd=ak.Array([[-1, 2, -1], [-1, -1, -1]]), StdHepP4=ak.Array([[[0] * 4, [0] * 4, [0, 0, 0, 0.2]]] + [[[0] * 4] * 3]),
                   IntType=ak.Array([3, 2]))
    out = TS.record_ancestry_jagged(records, [[0, 1]])
    assert out["is_delta_rad"].to_list() == [[True, False]] and out["delta_pdg"].to_list() == [[2114, 0]]
    with pytest.raises(IndexError):
        TS.record_ancestry_jagged(records, [[0, 5]])


def test_multi_signal_event_prefers_in_box_neutrino_and_keeps_counts():
    rock = dict(SIG, pos=(-690.0, 0.0, 679.0), prims=[(22, 270.0), (2212, 80.0), (2212, 90.0)])     # outside the filter box
    near = dict(SIG, pos=(-96.0, 0.0, 186.0), prims=[(22, 160.0), (2212, 80.0)])
    ev = _ev([rock, near])                                                       # rock listed FIRST: 'first' would pick the wrong one
    rec = dict(is_delta_rad=[[True, True]], delta_pdg=[[2114, 2214]], nucleon_pdg=[[2112, 2212]], nucleon_status=[[14, 14]], photon_e_gev=[[0.27, 0.16]])
    cat = lambda k: [ev[k][0]]
    r = TS.signal_truth(cat("pdg"), cat("isnc"), cat("mode"), cat("res"), cat("E"), cat("x"), cat("y"), cat("z"), cat("prim_pdg"), cat("prim_e"), nprim=cat("nprim"), record=rec)
    assert r["n_signal_nu_candidates"][0] == 2 and r["n_signal_nu_in_box"][0] == 1
    assert r["signal_nu_index"][0] == 1 and r["delta_pdg"][0] == 2214 and r["n_true_protons"][0] == 1 and r["is_ncdelta_radiative"][0] == 1


def test_no_resnum_based_signal_definition():
    # a record-defined signal neutrino with an arbitrary resnum is still signal; a resnum-0 NC resonant neutrino with a hard photon
    # but NO Delta ancestry in the record is NOT signal. resnum must play no role.
    ev = _ev([dict(SIG, res=9)]); cat = lambda k: [ev[k][0]]
    on = dict(is_delta_rad=[[True]], delta_pdg=[[2114]], nucleon_pdg=[[2112]], nucleon_status=[[14]], photon_e_gev=[[0.15]])
    off = dict(on, is_delta_rad=[[False]])
    args = (cat("pdg"), cat("isnc"), cat("mode"), cat("res"), cat("E"), cat("x"), cat("y"), cat("z"), cat("prim_pdg"), cat("prim_e"))
    assert TS.signal_truth(*args, nprim=cat("nprim"), record=on)["is_ncdelta_radiative"][0] == 1
    ev0 = _ev([dict(SIG, res=0)]); a0 = [[ev0[k][0]] for k in ("pdg", "isnc", "mode", "res", "E", "x", "y", "z", "prim_pdg", "prim_e")]
    assert TS.signal_truth(*a0, nprim=[ev0["nprim"][0]], record=off)["is_ncdelta_radiative"][0] == 0
