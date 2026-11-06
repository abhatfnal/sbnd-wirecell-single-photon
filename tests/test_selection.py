import awkward as ak
import numpy as np
import pytest
from sbnd_single_photon import selection as SEL


@pytest.fixture
def cfg():
    return SEL.load_config()


def _arrays(**over):
    n = ak.Array([[1.0, 0.0], [], [2.0]])
    a = {
        "wc.T_tagger.shw_sp_n_20mev_showers": n,
        "wc.T_tagger.shw_sp_n_20br1_showers": ak.Array([[1.0, 1.0], [], [2.0]]),
        "derived.single_photon_numu_score": ak.Array([[0.5, 0.9], [], [0.5]]),
        "derived.single_photon_other_score": ak.Array([[0.3, 0.3], [], [0.3]]),
        "derived.single_photon_ncpi0_score": ak.Array([[0.0, 0.0], [], [0.0]]),
        "derived.single_photon_nue_score": ak.Array([[0.0, 0.0], [], [0.0]]),
        "wc.T_tagger.nu_index": ak.Array([[0, 1], [], [0]]),
    }
    a.update(over)
    return a


def test_config_cut_names_and_thresholds(cfg):
    th = {c["name"]: (c["op"], c["threshold"]) for c in cfg["cuts"]}
    assert th["single_photon_numu_score_gt_0p4"] == (">", 0.4)
    assert th["single_photon_other_score_gt_0p2"] == (">", 0.2)
    assert th["single_photon_ncpi0_score_gt_m0p05"] == (">", -0.05)
    assert th["single_photon_nue_score_gt_m1"] == (">", -1.0)
    assert th["n_20mev_showers_gt0"] == (">", 0) and th["n_20br1_showers_eq1"] == ("==", 1)
    assert cfg["fiducial_volume"]["applied"] is False
    assert SEL.required_branches(cfg)["wc"] == ["wc.T_tagger.shw_sp_n_20mev_showers", "wc.T_tagger.shw_sp_n_20br1_showers"]


def test_cutflow_and_candidate_policy(cfg):
    a = _arrays()
    valid = np.array([True, True, True])
    rows = {r["cut"]: r["n_events"] for r in SEL.cutflow(a, cfg, valid, "any")}
    assert rows["all_events"] == 3 and rows["wc_valid"] == 3 and rows["has_neutrino_candidate"] == 2
    assert rows["cum:n_20mev_showers_gt0"] == 2
    assert rows["cum:n_20br1_showers_eq1"] == 1          # event0 cand0 passes all; event2 has n_20br1 == 2
    # 'first' policy only considers nu_index == 0 (still event0 cand0)
    first = {r["cut"]: r["n_events"] for r in SEL.cutflow(a, cfg, valid, "first")}
    assert first["cum:n_20br1_showers_eq1"] == 1


def test_wc_valid_is_respected(cfg):
    rows = {r["cut"]: r["n_events"] for r in SEL.cutflow(_arrays(), cfg, np.array([False, True, False]), "any")}
    assert rows["wc_valid"] == 1 and rows["cum:n_20br1_showers_eq1"] == 0


def test_nan_score_fails_cut(cfg):
    a = _arrays(**{"derived.single_photon_numu_score": ak.Array([[np.nan, np.nan], [], [np.nan]])})
    rows = {r["cut"]: r["n_events"] for r in SEL.cutflow(a, cfg, np.array([True] * 3), "any")}
    assert rows["cum:single_photon_numu_score_gt_0p4"] == 0


def test_missing_input_is_an_error(cfg):
    a = _arrays()
    a.pop("derived.single_photon_nue_score")
    with pytest.raises(KeyError):
        SEL.cutflow(a, cfg, np.array([True] * 3), "any")


def test_bad_policy(cfg):
    with pytest.raises(ValueError):
        SEL.event_pass(ak.Array([[True]]), "best")
