"""Regression tests of the Nov16 FROZEN-R1 replay: the selection must stay exactly the corrected Round-1 chain (source-faithful scorer, frozen thresholds, no FV,
production-default tree, legacy MicroBooNE XMLs only) and the sample roles must stay evaluation / diagnostic. No ROOT, no network."""
import gzip, hashlib, json, os, re, sys
from pathlib import Path
import numpy as np, pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "scripts"))
from sbnd_single_photon import legacy_scorer as L, selection as SEL, samples as S      # noqa: E402

TABLES = ROOT / "tables" / "wcl1116_nov16_replay"


def _common():
    import wcl1116_replay_common as C
    return C


def test_frozen_thresholds_unchanged():
    cfg = SEL.load_config()
    assert [c["threshold"] for c in cfg["cuts"] if "score" in c["name"]] == [0.4, 0.2, -0.05, -1.0]
    assert L.FROZEN_THRESHOLDS == {"numu": 0.4, "other": 0.2, "ncpi0": -0.05, "nue": -1.0}
    _common().load_cfg()                                     # asserts the same inside the replay library


def test_chain_is_exactly_the_frozen_round1_chain_and_has_no_fv():
    cfg = SEL.load_config()
    names = [c["name"] for c in cfg["cuts"]]
    assert names == ["n_20mev_showers_gt0", "single_photon_numu_score_gt_0p4", "single_photon_other_score_gt_0p2",
                     "single_photon_ncpi0_score_gt_m0p05", "single_photon_nue_score_gt_m1", "n_20br1_showers_eq1"]
    assert not any(re.search(r"fv|fiducial|box|boundary|wall", n, re.I) for n in names)
    src = (ROOT / "scripts" / "wcl1116_replay_common.py").read_text()
    assert "ActiveVolume" not in src and "fiducial" not in src.lower()          # nothing in the replay library restricts the volume


def test_source_faithful_scoring_log_odds_applied_once_and_flag_zero_column():
    C = _common()
    cfg = SEL.load_config()
    v = {"numu": [0.0, 0.5, 0.9], "other": [0.1, 0.3, -0.5], "ncpi0": [0.0, 0.0, 0.0], "nue": [-0.9, -0.5, 0.2]}
    pio0 = [-0.0575 + 1e-3, -0.0575 - 1e-3, 0.3]
    n = 3
    c = pd.DataFrame(dict(file_index=0, ev=np.arange(n), run=1, subrun=1, evt=np.arange(n), gev=np.arange(n), c_nu_index=0, bdt_evaluable=True, c_shw_sp_filled=1,
                          c_shw_sp_n_20mev_showers=1, c_shw_sp_n_20br1_showers=1, c_bdt_n_nonfinite_inputs=0,
                          **{f"c_score_{m}": v[m] for m in v}, c_score_ncpi0_pio0=pio0))
    ev = pd.DataFrame(dict(wc_valid=np.ones(n, bool)))
    out = C.to_D(c, ev, cfg)
    for m in ("numu", "other", "nue"):
        np.testing.assert_allclose(out[f"c_score_{m}"], np.log10((1 + np.array(v[m])) / (1 - np.array(v[m]))), rtol=1e-6)    # exactly one transform
    np.testing.assert_allclose(out["c_score_ncpi0"], np.log10((1 + np.array(pio0)) / (1 - np.array(pio0))), rtol=1e-5)       # ncpi0 comes from the flag-zero response
    np.testing.assert_allclose(out["v_ncpi0"], pio0)                                                                           # raw response kept, never transformed twice
    # cut semantics: numu 0.5 -> score 0.477 > 0.4 passes; 0.0 -> 0 fails (the as-run tanh-space cut would have passed 0.5 > 0.4 too, but 0.0 < 0.4 either way: use the discriminating point)
    assert L.passes(0.40, "numu", True) is not None
    assert bool(L.passes(np.array([0.42]), "numu", True)[0]) is False and bool(L.passes(np.array([0.44]), "numu", True)[0]) is True      # response-space equivalent 0.4305
    with pytest.raises(AssertionError):
        C.to_D(c.drop(columns=["c_score_ncpi0_pio0"]), ev, cfg)                                                                 # refuses tables without the flag-zero response


def test_builder_forces_kine_pio_flag_zero_for_legacy_ncpi0_only():
    src = (ROOT / "scripts" / "build_analysis_table.py").read_text()
    assert 'ncpi0_input_matrix(' in src and '"zero"' in src and "c_score_ncpi0_pio0" in src
    X = np.arange(12.0).reshape(2, 6) + 1
    out = L.ncpi0_input_matrix(X, ["a", "b", "kine_pio_flag", "c", "d", "e"], "zero")
    assert (out[:, 2] == 0).all() and (out[:, [0, 1, 3, 4, 5]] == X[:, [0, 1, 3, 4, 5]]).all() and (X[:, 2] != 0).all()      # input matrix untouched


def test_production_default_tree_is_read_not_the_snap_tree():
    caf = (ROOT / "src" / "sbnd_single_photon" / "caf.py").read_text()
    assert 'self._f["recTreeWireCell"]' in caf and "dv2snap" not in caf
    for f in ("wcl1116_replay_common.py", "wcl1116_replay_signal.py", "wcl1116_replay_bnb.py", "wcl1116_replay_controls.py", "wcl1116_replay_taxonomy.py", "build_analysis_table.py"):
        code = "\n".join(l for l in (ROOT / "scripts" / f).read_text().splitlines() if not l.strip().startswith("#"))
        assert "recTreeWireCell_dv2snap" not in code, f


def test_no_sbnd_development_bdt_is_used():
    src = "\n".join((ROOT / "scripts" / f).read_text() for f in ("wcl1116_replay_common.py", "wcl1116_replay_signal.py", "wcl1116_replay_bnb.py", "wcl1116_replay_controls.py", "wcl1116_replay_taxonomy.py"))
    assert "DEV_DO_NOT_DEPLOY" not in src and "aurora" not in src.lower().replace("aurora_space", "")
    assert re.search(r"uboone", (ROOT / "src" / "sbnd_single_photon" / "bdt.py").read_text())      # default weight directory is the MicroBooNE reference bundle
    prov = (ROOT / "provenance" / "microboone_reference_SHA256SUMS.txt").read_text()
    for h in ("5886affbdb3a4499a4515ecc8d354eb1449e7c204d32f1cc54c1ec8868ead961", "8c0ac375e957f5b332bc35339e4ebcbfef35bb778fb73315b06a814e600dbb16",
              "983a0d829aafdb4cb10afa273287cacab1cc27223bd46d3df5a2ebac1b3217c3", "8580ba04b4a9e3c7aefbb4d5da5006cff2a131804a7b594843461a7cd6f3758a"):
        assert h in prov                                                                     # the four legacy XMLs are the recorded ones


def test_legacy_xml_hashes_on_disk_if_available():
    from sbnd_single_photon import bdt as B
    w = B.DEFAULT_WEIGHT_DIR
    if not (w / "single_photon_ncpi0_bdt_final.xml").exists():
        pytest.skip("MicroBooNE weights not mounted")
    prov = dict(l.split()[::-1] for l in (ROOT / "provenance" / "microboone_reference_SHA256SUMS.txt").read_text().splitlines() if "single_photon_" in l)
    for m in L.MODELS:
        f = w / f"single_photon_{m}_bdt_final.xml"
        assert hashlib.sha256(f.read_bytes()).hexdigest() == prov[f"weights/{f.name}"]


def test_sample_roles_and_manifests_are_evaluation_only_and_nov16():
    s = S.load_samples()
    for name in ("bnb_cv", "nuecc", "beam_off", "beam_on_open", "run3bnb", "official_gen2_ncdelta"):
        assert s[name].may_train in (False, None) and s[name].role != "training_development", name
    assert s["run3bnb"].role == "data_validation" and s["run3bnb"].is_mc is False
    for name in ("bnb_cv", "nuecc", "beam_off", "beam_on_open", "run3bnb", "official_gen2_ncdelta"):
        rows = [l.split("\t")[1] for l in gzip.open(ROOT / "manifests" / "wcl1116" / f"{name}.tsv.gz", "rt")][1:]
        assert rows and all("/prod-fermigrid/WCLocal2026Nov16/" in r for r in rows), name


def test_replay_scripts_never_change_a_cut_or_train():
    for f in ("wcl1116_replay_common.py", "wcl1116_replay_signal.py", "wcl1116_replay_bnb.py", "wcl1116_replay_controls.py"):
        code = (ROOT / "scripts" / f).read_text()
        assert not re.search(r"\.fit\(|train\(|xgboost\.train|optimi[sz]e|scipy\.optimize|GridSearch", code), f


@pytest.mark.skipif(not (TABLES / "signal_cutflow_old_vs_nov16.csv").exists(), reason="replay outputs not generated")
def test_committed_old_reference_reproduces_round1_anchors():
    cf = pd.read_csv(TABLES / "signal_cutflow_old_vs_nov16.csv").set_index("stage").old_fg1_N.to_dict()
    assert cf == {"candidate": 11331, "n20mev": 8080, "bdt_evaluable": 8034, "numu": 4943, "other": 2717, "ncpi0": 1305, "nue": 893, "n20br1": 833, "final": 833}
    eff = pd.read_csv(TABLES / "signal_topology_efficiency.csv"); e = eff[(eff.production == "old_fg1") & (eff.policy == "any")].set_index("group")
    assert int(e.loc["total", "N_truth"]) == 12427 and int(e.loc["total", "selected"]) == 833
    assert [round(e.loc[g, "efficiency_pct"], 2) for g in ("0p", "1p", ">=2p")] == [6.36, 7.49, 4.37]
    tot = pd.read_csv(TABLES / "bnb_selected_totals.csv").set_index("production")
    o = tot.loc["old_fg1 (corrected R1)"]
    assert (int(o.selected_events), int(o.non_signal), int(o.reco_1g0p), int(o.reco_1g1p), int(o.reco_ge2p)) == (291, 282, 150, 93, 39)


@pytest.mark.skipif(not (TABLES / "signal_cutflow_old_vs_nov16.csv").exists(), reason="replay outputs not generated")
def test_signal_denominator_identical_for_old_and_new():
    eff = pd.read_csv(TABLES / "signal_topology_efficiency.csv")
    for g in eff.group.unique():
        assert eff[(eff.group == g) & (eff.policy == "any")].N_truth.nunique() == 1, g
