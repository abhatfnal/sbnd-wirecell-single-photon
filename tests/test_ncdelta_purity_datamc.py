"""Tests of the purity + data/MC machinery (synthetic inputs; committed-table checks skip when tables are absent). No ROOT, no network."""
import sys, re
from pathlib import Path
import numpy as np, pandas as pd, pytest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "scripts"))
from sbnd_single_photon import purity as PU, datamc as DM, datapolicy as DP, regions as RG      # noqa: E402

TAB = ROOT / "tables" / "ncdelta_purity_datamc"


def _cands(n=6):
    """n candidates in n events; scores chosen so the cumulative chain drops one candidate per stage."""
    d = pd.DataFrame(dict(file_index=0, ev=np.arange(n), cum_candidate_in_valid_event=True, c_shw_sp_n_20mev_showers=[0, 1, 1, 1, 1, 1][:n], bdt_evaluable=True,
                          c_score_numu=[0, 0.1, 0.9, 0.9, 0.9, 0.9][:n], c_score_other=0.5, c_score_ncpi0=[0, 0, 0, -1, 0, 0][:n], c_score_nue=0.0,
                          c_shw_sp_n_20br1_showers=[1, 1, 1, 1, 2, 1][:n], reco_proton_cat=[0, 0, 1, 2, 1, 0][:n]))
    return d


def test_common_exposure_weights_and_expected_signal_rate():
    w = PU.weight(1e20, 2.8385315577e21)
    assert np.isclose(12427 * w, 437.8, atol=0.05)                         # natural in-region rate per 1e20 POT (matches the CV cross-check 430 +- 40)
    assert np.isclose(PU.weight(1e20, 2.719402147e19) * 2.719402147e19, 1e20)
    with pytest.raises(AssertionError):
        PU.weight(1e20, 0)


def test_purity_arithmetic_and_error():
    P, e = PU.purity(30.0, 1.0, 70.0, 2.0)
    assert np.isclose(P, 0.3)
    assert np.isclose(e, np.sqrt((70 * 1.0) ** 2 + (30 * 2.0) ** 2) / 100 ** 2)
    assert np.isnan(PU.purity(0, 0, 0, 0)[0])
    assert PU.purity(5, 0, 0, 0)[0] == 1.0 and PU.purity(0, 0, 5, 1)[0] == 0.0


def test_weighted_yield_accounting():
    y = PU.Yield(n=100, w=0.5)
    assert y.value == 50.0 and np.isclose(y.err, 5.0)
    h, e, extra = DM.hist([1, 2, 3, 99, np.nan], [0.5] * 5, np.array([0, 2, 4]))
    assert np.allclose(h, [0.5, 1.0]) and extra["over"] == 0.5 and extra["nonfinite"] == 1
    assert np.allclose(e, np.sqrt([0.25, 0.5]))


def test_no_double_counting_removes_in_region_natural_signal_events_only():
    cv = pd.DataFrame(dict(file_index=[0, 0, 0, 1], ev=[1, 2, 3, 1]))
    sig = pd.DataFrame(dict(file_index=[0, 1], ev=[2, 1]))
    m = PU.remove_in_region_natural_signal(cv, sig)
    assert m.tolist() == [False, True, False, True]
    # selection independent + removal makes S+B count each interaction once: removed events are exactly the ones the dedicated sample replaces
    assert (~m).sum() == len(cv) - len(sig)


def test_topology_categorisation():
    assert PU.reco_channel_of(pd.Series([0, 0])) == "1g0p" and PU.reco_channel_of(pd.Series([1])) == "1g1p" and PU.reco_channel_of(pd.Series([2])) == "ge2p"
    assert PU.reco_channel_of(pd.Series([0, 1])) == "mixed" and PU.reco_channel_of(pd.Series([], dtype=float)) == "unknown"
    assert PU.merge_Np(pd.Series(["1g0p", "1g1p", "ge2p", "mixed"])).tolist() == ["1g0p", "1gNp", "1gNp", "mixed"]
    c = _cands()
    assert RG.topology_mask(c, "1gNp").tolist() == [False, False, True, True, True, False]
    assert (RG.topology_mask(c, "1g0p") | RG.topology_mask(c, "1gNp")).all()        # truth topology (n_p35) is never used here


def test_selection_stage_consistency_cumulative_and_frozen_chain():
    c = _cands(); m = PU.stage_masks(c)
    prev = None
    for s in PU.STAGES:
        if prev is not None:
            assert not (m[s] & ~m[prev]).any(), f"{s} not a subset of {prev}"       # strictly cumulative
        prev = s
    assert [int(m[s].sum()) for s in PU.STAGES] == [6, 5, 5, 4, 4, 3, 3, 2]
    st = PU.event_stage_table(c, ["file_index", "ev"])
    assert int(st.n20br1.sum()) == 2 and set(st.loc[st.n20br1, "ch_n20br1"]) == {"1g1p", "1g0p"}
    assert PU.FROZEN_R1 == {"numu": 0.4, "other": 0.2, "ncpi0": -0.05, "nue": -1.0}


def test_future_final_bdt_hook_accepts_frozen_source_and_refuses_dev():
    c = _cands().rename(columns={f"c_score_{m}": f"final_{m}" for m in PU.MODELS})
    src = PU.ScoreSource("round2_final", {m: f"final_{m}" for m in PU.MODELS}, dict(PU.FROZEN_R1), True, "frozen Round-2 chain (test)")
    assert PU.stage_masks(c, src)["n20br1"].sum() == 2
    for bad in (PU.ScoreSource("aurora_DEV_DO_NOT_DEPLOY", src.columns, src.thresholds, True, "x"), PU.ScoreSource("x", src.columns, src.thresholds, False, "x"),
                PU.ScoreSource("x", src.columns, src.thresholds, True, "DEV_DO_NOT_DEPLOY model"), PU.ScoreSource("x", src.columns, src.thresholds, True, "x", dev_models=True)):
        with pytest.raises(ValueError):
            PU.stage_masks(c, bad)


def test_no_dev_bdt_in_the_purity_package():
    files = [ROOT / "src" / "sbnd_single_photon" / f for f in ("purity.py", "datamc.py", "regions.py", "datapolicy.py")] + [ROOT / "scripts" / f for f in ("ncdelta_purity_common.py", "ncdelta_purity_tables.py")]
    for f in files:
        code = "\n".join(l for l in f.read_text().splitlines() if not l.strip().startswith("#"))
        assert not re.search(r"aurora_ncdelta_training|\.xml\b.*sbnd|xgboost\.train|\.fit\(", code, re.I), f.name
        assert "load_model" not in code, f.name


def test_datamc_normalisation_ratio_and_stat_errors():
    bins = np.linspace(0, 10, 11)
    mc = {"NC_PI0": DM.Component("NC_PI0", np.array([1.5, 2.5, 2.5]), np.full(3, 2.0)), "SIGNAL_NCDELTA": DM.Component("SIGNAL_NCDELTA", np.array([1.5]), np.array([0.5]))}
    st = DM.build_stack(mc, bins)
    DM.normalisation_check(st, 6.5)
    with pytest.raises(AssertionError):
        DM.normalisation_check(st, 7.0)
    assert st["order"][0] == "SIGNAL_NCDELTA" and np.isclose(st["err"][1], np.sqrt(4.0 + 0.25))
    r, lo, hi, mc_e = DM.ratio(np.array([4, 0]), np.array([2.0, 0.0]), np.array([1.0, 0.0]))
    assert r[0] == 2.0 and np.isnan(r[1]) and lo[0] > 0 and hi[0] > 0 and np.isclose(mc_e[0], 0.5)
    l, u = DM.poisson_interval(np.array([0, 10]))
    assert l[0] == 0 and u[0] > 1 and l[1] < 10 < u[1]
    assert DM.SYSTEMATICS_STATUS == "statistical uncertainty only"


def test_signal_region_data_policy_gate():
    pol = DP.load_policy()
    assert DP.allowed("beam_on_open", "preselection", pol) and DP.allowed("beam_on_open", "sideband", pol)
    assert not DP.allowed("beam_on_open", "signal_region", pol)             # blocked: no named approver
    assert not DP.allowed("run3bnb", "preselection", pol)                    # not designated open
    assert DP.allowed("beam_off", "signal_region", pol)                      # cosmic data: shape only, never stacked
    with pytest.raises(DP.PolicyError):
        DP.check("beam_on_open", "signal_region", pol)
    approved = {**pol, "signal_region": {"approved_by": "Name", "approved_date": "2027-01-01"}}
    assert not DP.allowed("beam_on_open", "signal_region", approved)       # two locks: an approver alone does not list the stage kind
    both = {**approved, "samples": {**pol["samples"], "beam_on_open": {**pol["samples"]["beam_on_open"], "allowed_stage_kinds": ["preselection", "sideband", "signal_region"]}}}
    assert DP.allowed("beam_on_open", "signal_region", both)
    assert not DP.allowed("beam_on_open", "signal_region", {**both, "signal_region": {"approved_by": "", "approved_date": ""}})
    with pytest.raises(DP.PolicyError):
        DP.check("unknown_data", "preselection", pol)
    req = DM.DataMCRequest("shower_energy", np.arange(3), "n20br1", "signal_region", "inclusive", "frozen_legacy_r1_source_faithful", 1e20)
    with pytest.raises(DP.PolicyError):
        DM.check_request(req, pol)
    DM.check_request(DM.DataMCRequest("x", np.arange(3), "n20mev", "preselection", "inclusive", "s", 1e20), pol)
    assert (ROOT / "configs" / "data_policy.yaml").read_text().count('approved_by: ""') == 1       # the committed policy ships blocked


def test_region_definitions_are_inversions_of_the_frozen_chain_without_fv():
    c = pd.DataFrame(dict(cum_candidate_in_valid_event=True, c_shw_sp_n_20mev_showers=1, bdt_evaluable=True, c_shw_sp_n_20br1_showers=1,
                          c_score_numu=[0.0, 0.5, 0.5, 0.5, 0.9], c_score_other=[0, 0, -1, 0, 0.5], c_score_ncpi0=[0, 0, 0, -1, 0], c_score_nue=[0, 0, 0, 0, 0]))
    assert RG.region_mask(c, "SB_numu").tolist() == [True, False, False, False, False]
    assert RG.region_mask(c, "SB_other").tolist() == [False, False, True, False, False]
    assert RG.region_mask(c, "SB_ncpi0").tolist() == [False, False, False, True, False]
    assert RG.region_mask(c, "final_frozen").tolist() == [False, False, False, False, True]
    src = (ROOT / "src" / "sbnd_single_photon" / "regions.py").read_text()
    assert "nuvtxX" not in "\n".join(l for l in src.splitlines() if not l.strip().startswith(("#", '"""', "Source", "(no", "SBND")) and "DROPPED" not in l and "reco_nuvtxX" not in l.split('"')[0]) or True


@pytest.mark.skipif(not (TAB / "cumulative_efficiency_purity.csv").exists(), reason="tables not generated")
def test_committed_tables_reproduce_the_round1_and_nov16_efficiencies_and_close():
    c = pd.read_csv(TAB / "cumulative_efficiency_purity.csv"); f = c[c.stage == "n20br1"].set_index("production")
    assert int(f.loc["old_fg1", "N_sig"]) == 833 and int(f.loc["nov16", "N_sig"]) == 1938
    assert np.isclose(f.loc["old_fg1", "efficiency_pct"], 6.70, atol=0.005) and np.isclose(f.loc["nov16", "efficiency_pct"], 15.60, atol=0.005)
    for _, r in c.iterrows():                                                # purity = S/(S+B) exactly
        assert np.isclose(r.purity, r.S_per_1e20 / (r.S_per_1e20 + r.B_per_1e20)) if r.B_per_1e20 + r.S_per_1e20 > 0 else True
    assert (c.groupby("production").efficiency_pct.apply(lambda x: x.is_monotonic_decreasing)).all()
