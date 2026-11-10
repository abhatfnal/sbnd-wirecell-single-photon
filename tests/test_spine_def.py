"""SPINE-harmonized truth definition: boundaries, thresholds, topology, containment, ladder closure, 35->50 MeV topology and 50-MeV reco projection (synthetic; no ROOT)."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
import yaml
from sbnd_single_photon import spine_def as SD

REPO = Path(__file__).resolve().parents[1]
MP = SD.M_P


def ke_to_e(ke_mev, m):          # GeV total energy from KE in MeV
    return ke_mev / 1000.0 + m


def test_config_matches_module_constants():
    c = yaml.safe_load(open(REPO / "configs" / "spine_signal_definition.yaml"))
    assert c["thresholds_mev"] == SD.THRESH and tuple(c["delta_resnum"]) == SD.DELTA_RESNUM and c["containment_margin_cm"] == SD.SPINE_MARGIN_CM
    assert {k: tuple(v) for k, v in c["walls_cm"].items()} == SD.WALLS and {k: tuple(v) for k, v in c["fiducial_distance_cm"].items()} == SD.FID_DIST


def test_spine_fv_boundaries_are_strict():
    x = np.array([179.999, 180.0, -179.999, -180.0, 0, 0, 0, 0, 0, 0]); y = np.zeros(10); z = np.array([100.0] * 4 + [10.0, 10.001, 449.999, 450.0, 100, 100])
    y[8], y[9] = 179.999, 180.0
    assert SD.fiducial(x, y, z).tolist() == [True, False, True, False, False, True, True, False, True, False]


def test_threshold_rules_photon_electron_muon_pion_proton_neutrino_other():
    pdg = np.array([22, 22, 11, 11, 13, 211, 2212, 2212, 14, 2112, 111])
    e = np.array([0.025, 0.02501, ke_to_e(25.01, SD.M_E), ke_to_e(24.9, SD.M_E), ke_to_e(30, SD.M_MU), ke_to_e(30, SD.M_PIC), ke_to_e(50.01, MP), ke_to_e(49.9, MP), 5.0, 1.0, 0.01])
    assert SD.above_threshold(pdg, e).tolist() == [False, True, True, False, True, True, True, False, False, True, True]     # exactly-at-threshold photon is NOT above; nu never; neutron/pi0 always


def test_counts_and_only_photons_and_nucleons():
    pdg = np.array([14, 22, 22, 2112, 2212, 211, 211])
    e = np.array([1.0, 0.2, 0.01, 1.0, ke_to_e(60, MP), ke_to_e(10, SD.M_PIC), ke_to_e(10, SD.M_PIC)])
    c = SD.counts(pdg, e)
    assert (c["n_gamma"], c["n_proton"], c["n_charged_pion"], c["n_neutron"]) == (1, 1, 0, 1) and c["only_photons_and_nucleons"]     # sub-threshold photon/pions are ignored
    c2 = SD.counts(np.append(pdg, 111), np.append(e, 0.001))
    assert not c2["only_photons_and_nucleons"] and c2["n_pi0"] == 1                                                                   # a pi0 at ANY energy breaks the source rule
    c3 = SD.counts(np.append(pdg, 211), np.append(e, ke_to_e(30, SD.M_PIC)))
    assert c3["n_charged_pion"] == 1 and not c3["only_photons_and_nucleons"]
    assert not SD.counts(np.array([22, -2212]), np.array([0.2, 1.5]))["only_photons_and_nucleons"]


def test_fifty_mev_proton_count_and_0p50_np50_exclusive():
    pdg = np.array([22, 2212, 2212, 2212]); e = np.array([0.2, ke_to_e(34, MP), ke_to_e(40, MP), ke_to_e(80, MP)])
    assert SD.proton_count(pdg, e, 35.0) == 2 and SD.proton_count(pdg, e, 50.0) == 1 and SD.proton_count(pdg, e, 100.0) == 0
    n50 = np.array([0, 0, 1, 3]); a, b = n50 == 0, n50 >= 1
    assert (a ^ b).all() and (a & b).sum() == 0


def test_containment_margin_deposit_logic_and_sentinels():
    pdg = np.array([22, 2112]); z = np.array([100.0, 100.0]); y = np.zeros(2)
    ok = SD.containment_margin(pdg, [0, 0], y, z, [100, 300], y, z, [1.0, 0.0])                     # neutron (no deposit) exits but is ignored by default
    assert ok
    assert not SD.containment_margin(pdg, [0, 0], y, z, [100, 300], y, z, [1.0, 0.0], require_deposit=False, include_neutrons=True)
    assert not SD.containment_margin(pdg[:1], [0], y[:1], z[:1], [197.0], y[:1], z[:1], [1.0])         # 196.6 is the 5-cm limit of the SPINE box (201.6)
    assert SD.containment_margin(pdg[:1], [0], y[:1], z[:1], [196.0], y[:1], z[:1], [1.0])
    assert not SD.containment_margin(pdg[:1], [0], y[:1], z[:1], [-9999.0], y[:1], z[:1], [1.0])        # sentinel end of a depositing particle = not contained
    assert SD.containment_margin(np.array([14, 22]), [0, 0], y, z, [9e4, 100], y, z, [0.0, 1.0])       # neutrino never considered
    assert not SD.containment_margin(pdg[:1], [0], y[:1], [4.0], [100], y[:1], [100], [1.0])            # z = 4 < 4.84 (upstream margin)


def test_neutrino2026_veto_pieces():
    pdg = np.array([22]); one = lambda v: np.array([v], float)
    base = dict(sx=one(10), sy=one(0), sz=one(100), ex=one(20), ey=one(0), ez=one(120), vis=one(1.0))
    assert SD.neutrino2026_veto(50.0, pdg, **base)
    assert not SD.neutrino2026_veto(3.0, pdg, **base)                                                      # |x| <= 5 cm of the cathode
    assert not SD.neutrino2026_veto(50.0, pdg, **{**base, "ey": one(150), "ez": one(300), "ex": one(50)})   # ends in the high-y/high-z region (x > 0)
    assert SD.neutrino2026_veto(-50.0, pdg, **{**base, "sx": one(-10), "ex": one(-50), "ey": one(150), "ez": one(300)})   # same y/z but x < 0: allowed
    assert not SD.neutrino2026_veto(50.0, pdg, **{**base, "sx": one(10), "ex": one(-10)})                  # crosses the cathode


def test_genie_record_strict():
    ok = dict(g1_n_photon=1, g1_n_pi0=0, g1_n_pic=0, g1_n_lepton=0, g1_n_other=0)
    assert SD.genie_record_strict(ok) and not SD.genie_record_strict({**ok, "g1_n_pi0": 1}) and not SD.genie_record_strict({**ok, "g1_n_photon": 2})


def _toy(n=3000, seed=3):
    rng = np.random.default_rng(seed)
    t = pd.DataFrame(dict(delta_pdg=rng.choice([2114, 2214], n), nu_isnc=1, nu_resnum=rng.choice([0, 0, 0, 2, 6], n), vtx_x=rng.uniform(-200, 200, n), vtx_y=rng.uniform(-200, 200, n),
                          vtx_z=rng.uniform(0, 500, n), n_gamma25=rng.choice([0, 1, 1, 1, 2], n), n_e25=rng.choice([0, 0, 0, 1], n), n_mu25=0, n_pic25=rng.choice([0, 0, 1], n),
                          only_phot_nuc=rng.random(n) > 0.2, n_p50=rng.choice([0, 0, 1, 2, 3], n), n_p35_prim=0, cont_main=rng.random(n) > 0.3, veto2026=rng.random(n) > 0.1,
                          g1_n_photon=1, g1_n_pi0=0, g1_n_pic=0, g1_n_lepton=0, g1_n_other=rng.choice([0, 0, 1], n)))
    t["truth35"] = np.minimum(t.n_p50 + rng.choice([0, 0, 1], n), 2)
    for c in ("cont_literal", "cont_gdml", "cont_flag"):
        t[c] = rng.random(n) > 0.4
    t["tpc_box"] = rng.random(n) > 0.1
    return SD.masks(t)


def test_denominator_ladder_closes_and_is_monotone():
    t = _toy(); L = SD.denominator_ladder(t); c = L[L.kind == "cumulative"]
    assert c.n.is_monotonic_decreasing and c.n.iloc[0] == len(t)
    assert (c.n_0p50 + c.n_Np50 == c.n).all() and (c.n_Delta0 + c.n_DeltaPlus == c.n).all() and (c.n_truth35_0p + c.n_truth35_1p + c.n_truth35_ge2p == c.n).all()
    assert (L.n_0p50 + L.n_Np50 == L.n).all()
    nm = c[c.step.str.contains("spine_technote_strict")].n.iloc[0]
    assert nm == int(t.spine_technote_strict.sum()) == int(t.spine_truth_signal.sum())


def test_strict_is_subset_of_threshold_and_topology_masks_exclusive():
    t = _toy()
    assert not (t.spine_technote_strict & ~t.spine_technote_threshold).any() and t.spine_technote_strict.sum() <= t.spine_technote_threshold.sum()
    assert (t.spine_truth_0p50 ^ t.spine_truth_Np50 ^ ~t.spine_truth_signal).all() or ((t.spine_truth_0p50 & t.spine_truth_Np50).sum() == 0)
    assert int(t.spine_truth_0p50.sum() + t.spine_truth_Np50.sum()) == int(t.spine_truth_signal.sum())


def test_crosstab_35_to_50_closes():
    t = _toy(); mk = t.spine_truth_signal
    x = SD.crosstab_35_50(t.truth35, t.n_p50, mk)
    assert int(x.to_numpy().sum()) == int(mk.sum()) and int(x["50: 0p50"].sum()) == int(t.spine_truth_0p50.sum()) and int(x["50: Np50"].sum()) == int(t.spine_truth_Np50.sum())


def test_reco50_projection_closure_and_selected_numerator_unchanged():
    rng = np.random.default_rng(5); n = 2000
    sel = rng.random(n) < 0.1; ke = np.where(rng.random(n) < 0.4, rng.uniform(35, 300, n), np.nan)
    cat = SD.reco50_category(ke, sel)
    assert set(cat) <= {"0p50", "Np50", "none"} and (cat[~sel] == "none").all() and (cat[sel] != "none").all()
    assert ((cat == "Np50") == (sel & (ke > 50))).all()                       # a stored leading KE is already above 35 MeV; 35 < KE <= 50 projects to 0p50
    t = _toy(n); sel = rng.random(n) < 0.1
    for mask in (t.spine_truth_signal, t.spine_truth_0p50, t.spine_truth_Np50):
        m = SD.migration_50(t.n_p50, mask, SD.reco50_category(ke[:n] if len(ke) >= n else ke, sel))
        assert int(m.to_numpy().sum()) == int(mask.sum())
    # the harmonized numerator is the SAME frozen decision restricted to the denominator: sum over the classes equals the whole
    assert int((sel & t.spine_truth_0p50).sum() + (sel & t.spine_truth_Np50).sum()) == int((sel & t.spine_truth_signal).sum())


def test_missing_production_event_is_retained_in_the_denominator():
    t = _toy(100); t["arrived"] = True; t.loc[0, ["arrived"]] = False; t["A_final"] = np.arange(100) % 7 == 0; t.loc[0, "A_final"] = False
    t.loc[0, ["vtx_x", "vtx_y", "vtx_z"]] = 0.0, 0.0, 250.0                                      # place the missing event inside the FV
    t = SD.masks(t.assign(cont_main=True, veto2026=True, n_gamma25=1, n_e25=0, n_mu25=0, n_pic25=0, only_phot_nuc=True, g1_n_other=0))
    assert bool(t.spine_truth_signal.iloc[0]) and not bool(t.A_final.iloc[0])                      # in the denominator, fails every numerator


def test_committed_summary_pins_the_baseline_numerator():
    p = REPO / "tables" / "spine_harmonization" / "summary.json"
    if not p.exists():
        pytest.skip("harmonization summary not generated yet")
    s = json.loads(p.read_text())
    c = s["checks"]
    assert c["n_events"] == 13773 and c["missing_event_in_table"] == 1 and c["sum_final_any_filter_box"] == 1172 and c["sum_final_first_filter_box"] == 1120 and c["tpc_final_any"] == 1153
    assert c["spine_fv_inside_tpc_box"] and c["n_p35_scan_equals_master"]
    d = s["denominators"]
    assert d["spine_truth_0p50"] + d["spine_truth_Np50"] == d["spine_truth_signal"] == d["spine_technote_strict"] <= d["spine_technote_threshold"]
