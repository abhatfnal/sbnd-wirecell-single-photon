"""Source-faithful legacy scorer: exact transform, threshold boundaries, kine_pio_flag source behaviour, mode separation, no XML / threshold / training change.

Hand-computed values: log10((1+v)/(1-v)) at v = 0, +-1/3 (log10 2), +-0.6 (log10 4), 0.8 (log10 9).
"""
import hashlib
import math
import re
from pathlib import Path

import numpy as np
import pytest
import yaml

from sbnd_single_photon import legacy_scorer as L

ROOT = Path(__file__).resolve().parents[1]


def test_exact_score_transform_hand_computed():
    for v, want in ((0.0, 0.0), (1 / 3, math.log10(2)), (-1 / 3, -math.log10(2)), (0.6, math.log10(4)), (-0.6, -math.log10(4)), (0.8, math.log10(9))):
        assert abs(float(L.log_odds_score(v)) - want) < 2e-7
    assert abs(float(L.log_odds_score(0.6)) - 0.60206) < 1e-5 and abs(float(L.log_odds_score(0.8)) - 0.95424) < 1e-5
    s = L.log_odds_score(np.array([-1.0, 1.0]))
    assert s[0] == -np.inf and s[1] == np.inf                               # source: no clamp
    assert np.isnan(L.log_odds_score(np.nan)) and np.isnan(L.log_odds_score(1.5))
    assert L.log_odds_score(0.3).dtype == np.float32                        # stored as float in the source
    v = np.linspace(-0.99, 0.99, 41); assert np.allclose(L.log_odds_score(v), 2 * np.arctanh(v) / math.log(10), atol=1e-6)       # = 2 raw / ln10
    assert np.allclose(L.response_from_score(L.log_odds_score(v)), v, atol=1e-6)


def test_frozen_thresholds_unchanged_and_translation():
    assert L.FROZEN_THRESHOLDS == {"numu": 0.4, "other": 0.2, "ncpi0": -0.05, "nue": -1.0}
    cfg = yaml.safe_load(open(ROOT / "configs" / "baseline_selection.yaml"))
    assert [c["threshold"] for c in cfg["cuts"] if "score" in c["name"]] == [0.4, 0.2, -0.05, -1.0]
    h = hashlib.sha256((ROOT / "configs" / "baseline_selection.yaml").read_bytes()).hexdigest(); assert h == "f3251b785be6e52ff3e429000a0319a6df8e42d2016ace2f51c7650a38e2fb0b"
    for m, want in (("numu", 0.4305), ("other", 0.2263), ("ncpi0", -0.0575), ("nue", -0.8182)):
        assert abs(float(L.response_from_score(L.FROZEN_THRESHOLDS[m])) - want) < 1e-4, m


@pytest.mark.parametrize("model", L.MODELS)
def test_every_frozen_threshold_boundary(model):
    vt = float(L.response_from_score(L.FROZEN_THRESHOLDS[model]))
    below, above = vt - 1e-4, vt + 1e-4
    assert not L.passes(below, model, True) and L.passes(above, model, True)
    # as-run scale cuts v itself: the same two values straddle a different boundary
    t = L.FROZEN_THRESHOLDS[model]
    assert L.passes(t + 1e-4, model, False) and not L.passes(t - 1e-4, model, False)
    # values between the two boundaries separate the two conventions (the whole effect)
    mid = 0.5 * (vt + t)
    assert bool(L.passes(mid, model, True)) != bool(L.passes(mid, model, False)) or abs(vt - t) < 1e-3
    assert not L.passes(np.nan, model, True) and not L.passes(np.nan, model, False)
    assert bool(L.passes(1.0, model, True)) and not L.passes(-1.0, model, True)       # v=+-1 -> score +-inf (source, no clamp)


def test_nue_cut_is_vacuous_as_run_and_real_when_faithful():
    v = np.array([-0.99, -0.9, -0.82, -0.81, 0.0])
    assert L.passes(v, "nue", False).all()                                  # v > -1.0 always
    assert list(L.passes(v, "nue", True)) == [False, False, False, True, True]     # v > -0.8182


def test_float32_widening_matches_cpp():
    # a score that is exactly the float32 nearest to 0.4 passes `> 0.4` (float(0.4) = 0.4000000059604645), as in C++
    v = float(L.response_from_score(0.4)); s = L.log_odds_score(v)
    assert abs(float(s) - 0.4) < 1e-6


def test_kine_pio_flag_source_behaviour():
    names = ["a", "kine_pio_flag", "b"]; Xm = np.array([[1.0, 2.0, 3.0], [4.0, 1.0, 6.0]])
    z = L.ncpi0_input_matrix(Xm, names, "zero"); r = L.ncpi0_input_matrix(Xm, names, "real")
    assert (z[:, 1] == 0).all() and (z[:, [0, 2]] == Xm[:, [0, 2]]).all() and (r == Xm).all() and Xm[0, 1] == 2.0      # input not mutated, only column 1 forced
    with pytest.raises(ValueError):
        L.ncpi0_input_matrix(Xm, names, "other")
    assert L.MODES["legacy_source_faithful"] == dict(log_odds=True, pio_flag="zero") and L.MODES["legacy_as_run"] == dict(log_odds=False, pio_flag="real")
    # the override only matters to the ncpi0 BDT: the numu / other / nue XMLs do not list kine_pio_flag (needs the weights)
    import xml.etree.ElementTree as ET
    wd = Path("/exp/uboone/app/users/uboonepro/bbogart/wcp-uboone-bdt/weights")
    if wd.exists():
        for m in L.MODELS:
            ex = [v.get("Expression") for v in ET.parse(wd / f"single_photon_{m}_bdt_final.xml").getroot().find("Variables")]
            assert ("kine_pio_flag" in ex) == (m == "ncpi0"), m


def test_old_and_new_modes_are_separate_and_decompose():
    assert L.CONFIGS["A_old"] == L.MODES["legacy_as_run"] and L.CONFIGS["D_full"] == L.MODES["legacy_source_faithful"]
    assert L.CONFIGS["B_score_only"] == dict(log_odds=True, pio_flag="real") and L.CONFIGS["C_pio_only"] == dict(log_odds=False, pio_flag="zero")
    v = np.array([0.1, 0.5]); assert np.array_equal(L.score(v, False), v) and not np.array_equal(L.score(v, True), v)


def test_xml_not_changed_and_no_training_code():
    sums = (ROOT / "provenance" / "microboone_reference_SHA256SUMS.txt").read_text()
    assert "5886affbdb3a4499a4515ecc8d354eb1449e7c204d32f1cc54c1ec8868ead961" in sums
    wd = Path("/exp/uboone/app/users/uboonepro/bbogart/wcp-uboone-bdt/weights")
    if wd.exists():
        for line in sums.splitlines():
            g = re.match(r"([0-9a-f]{64})\s+\S*?(single_photon_\w+\.xml)$", line.strip())
            if g and (wd / g.group(2)).exists():
                assert hashlib.sha256((wd / g.group(2)).read_bytes()).hexdigest() == g.group(1)
    src = (ROOT / "src" / "sbnd_single_photon" / "legacy_scorer.py").read_text() + (ROOT / "scripts" / "legacy_scorer_impact_scan.py").read_text()
    assert not re.search(r"\b(xgboost|\.fit\(|train_test_split|GradientBoosting|TMVA::Factory)\b", src.replace("kine_pio_flag", ""))
