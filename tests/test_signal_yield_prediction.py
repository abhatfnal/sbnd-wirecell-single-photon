import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from sbnd_single_photon import signal_yield as Y, prediction as P

REPO = Path(__file__).resolve().parents[1]


def _inp(selected=((50, 20, 1), (10, 100, 20), (0, 5, 30)), n=(100, 200, 50), pot=1e20, region="active_tpc"):
    return Y.SignalEfficiencyInputs(region, pot, n, selected)


def test_reco_channel_yield_uses_full_migration_not_the_diagonal():
    inp = _inp()
    r = Y.expected_yield(inp, 2e20)
    # N(r) = P/POT * sum_t selected[t][r]
    assert r["by_reco_channel"]["1g0p"] == pytest.approx(2 * (50 + 10 + 0)) and r["by_reco_channel"]["1g1p"] == pytest.approx(2 * (20 + 100 + 5))
    assert r["by_reco_channel"]["ge2p"] == pytest.approx(2 * (1 + 20 + 30)) and r["total"] == pytest.approx(2 * 236)
    naive = Y.naive_diagonal_yield(inp, 2e20)
    assert naive[0] == pytest.approx(2 * 50) and naive[0] != pytest.approx(r["by_reco_channel"]["1g0p"])      # truth-0p x reco-0p only would miss the 1p -> 0p migration
    assert r["by_truth_class"]["1p"] == pytest.approx(2 * 130)
    assert sum(r["by_reco_channel"].values()) == pytest.approx(r["total"])


def test_yield_uncertainty_is_multinomial_and_covariance_consistent():
    r = Y.expected_yield(_inp(), 1e20)
    cov = np.array(r["covariance_reco"]); assert np.allclose(cov, cov.T) and r["total_stat_unc"] ** 2 == pytest.approx(cov.sum())
    # one truth class, all selected in one channel -> zero variance for that channel
    r0 = Y.expected_yield(Y.SignalEfficiencyInputs("x", 1e20, (10, 0, 0), ((10, 0, 0), (0, 0, 0), (0, 0, 0))), 1e20)
    assert r0["total"] == 10 and r0["total_stat_unc"] == 0


def test_region_dependent_rate_and_wc_invalid_in_denominator():
    d = json.load(open(REPO / "tables" / "official_signal" / "denominators.json"))
    rates = {k: d[k]["R_signal_per_POT"] for k in ("filter_box", "active_tpc")}
    assert rates["filter_box"] > rates["active_tpc"] and rates["active_tpc"] / rates["filter_box"] == pytest.approx(12427 / 13773)
    # events lost in Wire-Cell remain in n_truth and so lower the efficiency and the yield
    full = Y.expected_yield(Y.SignalEfficiencyInputs("r", 1e20, (100, 0, 0), ((50, 0, 0), (0, 0, 0), (0, 0, 0))), 1e20)
    assert full["total"] == pytest.approx(50)
    with pytest.raises(ValueError):                                  # more selected than truth: numerator and denominator are not the same events
        Y.SignalEfficiencyInputs("r", 1e20, (10, 0, 0), ((11, 0, 0), (0, 0, 0), (0, 0, 0)))


def test_inputs_from_event_table():
    tab = pd.DataFrame(dict(truth_cat=[0, 0, 1, 2], pass_any=[True, False, True, True], reco_cat_any=[0, -1, 0, 2]))
    i = Y.inputs_from_event_table(tab, (2, 1, 1), 1e20, "r")
    assert np.asarray(i.selected).tolist() == [[1, 0, 0], [1, 0, 0], [0, 0, 1]] and i.n_truth == (2, 1, 1)


def _selected(n0=3, n1=2, n2=1, sig=2):
    rows = [dict(event_class="background", reco_channel="1g0p")] * n0 + [dict(event_class="background", reco_channel="1g1p")] * n1 + \
           [dict(event_class="background", reco_channel="ge2p")] * n2 + [dict(event_class="signal_like", reco_channel="1g0p")] * sig
    return pd.DataFrame(rows)


def test_background_excludes_signal_like_and_scales_with_exposure():
    c = P.bnb_background_component(_selected(), pot_cv=1e19, exposure_pot=1e20)
    assert c.values == {"1g0p": 30.0, "1g1p": 20.0, "ge2p": 10.0}                      # the 2 signal-like events are NOT in B
    assert c.stat_unc["1g0p"] == pytest.approx(np.sqrt(3) * 10)
    with pytest.raises(ValueError):
        P.bnb_background_component(pd.concat([_selected(), pd.DataFrame([dict(event_class="mixed", reco_channel="1g0p")])]), 1e19, 1e20)


def test_committed_background_rate_model_is_the_phase4_635():
    m = json.load(open(REPO / "tables" / "official_signal" / "background_rate_model.json"))
    assert m["background_events"] == 635 and m["signal_like_removed"] == 14 and m["event_classes_in_table"] == {"background": 635, "signal_like": 14}
    assert {k: v["count"] for k, v in m["by_reco_channel"].items()} == {"1g0p": 310, "1g1p": 230, "ge2p": 95}
    assert m["by_reco_channel"]["1g0p"]["rate_per_1e20_POT"] == pytest.approx(310 / m["pot_cv"] * 1e20)
    assert "NOT included" in m["nueCC_dedicated_sample"]


def _pred(signal_known=False):
    bnb = P.bnb_background_component(_selected(), 1e19, 1e20)
    sig = P.Component("S_NCDELTA", "known", {"1g0p": 5., "1g1p": 4., "ge2p": 1.}, {"1g0p": 1., "1g1p": 1., "ge2p": 1.}) if signal_known else P.pending_signal()
    return P.Prediction(1e20, sig, bnb, P.cosmic_shape_only({"1g0p": 4, "1g1p": 2, "ge2p": 0}), P.open_data({"1g0p": 39, "1g1p": 27, "ge2p": 11}, 4.6e18))


@pytest.mark.parametrize("name", ["total_background", "purity", "s_over_b", "significance"])
def test_unresolved_cosmic_normalization_blocks_every_derived_quantity(name):
    for known in (False, True):
        with pytest.raises(P.UnresolvedNormalizationError):                           # never silently zero, whether or not the signal is known
            getattr(_pred(known), name)()
    p = _pred(True)
    p.B_COSMIC = P.Component("B_COSMIC", "known", {"1g0p": 2., "1g1p": 1., "ge2p": 0.})      # only an explicit, known component unblocks it
    assert p.total_background()["1g0p"] == pytest.approx(32.0) and p.s_over_b()["1g1p"] == pytest.approx(4. / 21.)


def test_status_table_and_committed_status():
    s = _pred().status_table()
    assert s["B_COSMIC"]["status"] == "unresolved" and s["S_NCDELTA"]["status"] == "pending" and s["B_BNB_NEUTRINO"]["status"] == "known"
    c = json.load(open(REPO / "tables" / "official_signal" / "prediction_status.json"))
    assert all(v.startswith("refused") for v in c["refusals"].values())
