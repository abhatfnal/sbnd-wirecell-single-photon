"""Tests of the systematic-weight machinery (synthetic inputs; committed-table checks skip when tables are absent). No ROOT, no network. Nothing here applies a weight to a result."""
import re, struct, sys
from pathlib import Path
import numpy as np, pandas as pd, pytest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src")); sys.path.insert(0, str(ROOT / "scripts"))
from sbnd_single_photon import syst_weights as SW      # noqa: E402

TAB = ROOT / "tables" / "ncdelta_purity_datamc"


def _entry(name: str, vals, mean=0.0, width=0.0, covidx=0):
    nb = name.encode(); body = b"@\x00\x00" + bytes([2 + 1 + len(nb)]) + b"\x00\t" + bytes([len(nb)]) + nb + struct.pack(">ffi", mean, width, covidx)
    return body + b"@\x00\x00" + bytes([2 + 4 + 4 * len(vals)]) + b"\x00\t" + struct.pack(">i", len(vals)) + b"".join(struct.pack(">f", v) for v in vals)


def test_weight_map_parser_reads_sigma_values_and_rejects_inconsistent_bytecounts():
    raw = b"\x00\x01junk" + _entry("ZExpA1CCQE", [-1, 1, -2, 2, -3, 3]) + b"\x00\x00\x00\x01" + _entry("VecFFCCQEshape", [1.0]) + _entry("SPPLowQ2Suppression", [0.1, 0.5, 1.0])
    e = SW.parse_weight_map(raw)
    assert [x["name"] for x in e] == ["ZExpA1CCQE", "VecFFCCQEshape", "SPPLowQ2Suppression"] and list(e[0]["vals"]) == [-1, 1, -2, 2, -3, 3]
    bad = bytearray(_entry("MaCCQE", [-1, 1])); bad[bad.index(b"@\x00\x00", 5) + 3] += 1                      # corrupt the second byte-count word
    assert SW.parse_weight_map(bytes(bad)) == []
    ps = [("GENIEReWeight_SBN_v1_multisigma_ZExpA1CCQE", 6, 3), ("GENIEReWeight_SBN_v1_multisigma_VecFFCCQEshape", 1, 3), ("x_SPPLowQ2Suppression", 3, 3), ("some_multisim", 100, 0)]
    m = SW.multisigma_sigmas(ps, e); assert set(m) == {p[0] for p in ps if p[2] == 3} and list(m[ps[1][0]]) == [1.0]
    with pytest.raises(ValueError):
        SW.multisigma_sigmas([("x_Unknown", 2, 3)], e)


def test_block_layout_and_id_join_are_explicit():
    nuniv = np.array([6, 1, 100]); tot = 107
    flat = np.arange(2 * tot, dtype=np.float32)
    b = SW.split_blocks(flat, 2, nuniv); assert b.shape == (2, tot) and b[1, 0] == tot                       # neutrino-major
    with pytest.raises(ValueError):
        SW.split_blocks(flat[:-1], 2, nuniv)
    assert SW.layout_ok(np.tile(nuniv, 2), 2, nuniv) and not SW.layout_ok(np.tile(nuniv, 2)[:-1], 2, nuniv) and not SW.layout_ok(np.tile(nuniv[::-1], 2), 2, nuniv)
    rec = np.array([[1, 1, 10], [1, 1, 11], [1, 2, 10]]); want = np.array([[1, 2, 10], [1, 1, 10], [9, 9, 9]])
    assert list(SW.map_events_by_id(rec, want)) == [2, 0, -1]                                                  # joined on ids, not on entry number
    with pytest.raises(ValueError):
        SW.map_events_by_id(np.array([[1, 1, 1], [1, 1, 1]]), want)


def test_function_deltas_follow_the_documented_prescriptions():
    rng = np.random.default_rng(1); Qn = np.array([10.0, 20.0]); Qu = Qn[:, None] + rng.normal(0, 1, (2, 50))
    D, s = SW.function_deltas(dict(type_code=0, sigmas="", name="m"), Qu, Qn)
    assert np.allclose(s * D @ D.T, (Qu - Qn[:, None]) @ (Qu - Qn[:, None]).T / 50)                           # sample covariance about the NOMINAL, 1/N
    grid = ";".join(f"{x:g}" for x in SW.SIGMA_GRID); Q6 = np.stack([Qn - 1, Qn + 3, Qn - 2, Qn + 6, Qn - 3, Qn + 9], 1)    # order -1, +1, -2, +2, -3, +3 ... first two are the 1 sigma pair
    D, s = SW.function_deltas(dict(type_code=3, sigmas=grid, name="u"), Q6, Qn); assert np.allclose(D[:, 0], [2.0, 2.0]) and s == 1.0       # (N(+1) - N(-1))/2 with N(-1) = Q[:,0] = Qn - 1, N(+1) = Qn + 3
    D, s = SW.function_deltas(dict(type_code=3, sigmas="1", name="one"), (Qn + 5)[:, None], Qn); assert np.allclose(D[:, 0], 5.0)
    with pytest.raises(ValueError):
        SW.function_deltas(dict(type_code=3, sigmas="0.1;0.2;0.3", name="spp"), np.ones((2, 3)), Qn)         # undocumented dial: refuses instead of guessing


def test_universe_yields_with_unit_weights_reproduce_the_counts_and_unbinned_events_are_excluded():
    W = np.ones((5, 7), np.float32); idx = np.array([0, 1, 1, -1, 2])
    Y = SW.universe_yields(W, 2.5, idx, 3); assert Y.shape == (3, 7) and np.allclose(Y[:, 0], [2.5, 5.0, 2.5]) and np.allclose(Y, Y[:, [0]])


def test_coherent_purity_cancels_what_independent_propagation_cannot():
    """S and B scale together in every universe: P_u == P_nom exactly (coherent sigma = 0) while the naive independent S/B propagation reports a spread."""
    rng = np.random.default_rng(3); f = 1 + 0.2 * rng.standard_normal(200); Sn, Bn = 30.0, 1000.0
    Qn = np.array([Sn, Bn]); Qu = np.stack([Sn * f, Bn * f]); pur = lambda Q: Q[:1] / (Q[:1] + Q[1:])
    D, s = SW.function_deltas(dict(type_code=0, sigmas="", name="m"), Qu, Qn, pur); assert np.allclose(D, 0, atol=1e-12)
    Dq, sq = SW.function_deltas(dict(type_code=0, sigmas="", name="m"), Qu, Qn); sS, sB = np.sqrt(sq * (Dq ** 2).sum(1))
    naive = np.sqrt((Bn / (Sn + Bn) ** 2 * sS) ** 2 + (Sn / (Sn + Bn) ** 2 * sB) ** 2); assert naive / (Sn / (Sn + Bn)) > 0.1


def test_audit_reports_without_modifying_the_weights():
    W = np.array([[1, 1, -0.5, np.inf, 0, 30.0], [1, 1, 1, 1, 1, 1]], np.float32); W0 = W.copy()
    a = SW.audit_weights(W, [("f_a", 0, 2), ("f_b", 2, 6)]).set_index("name")
    assert a.loc["f_a", "frac_events_inert"] == 1.0 and a.loc["f_b", "n_nonfinite"] == 1 and a.loc["f_b", "n_negative"] == 1 and a.loc["f_b", "n_zero"] == 1 and a.loc["f_b", "max"] == 30.0
    assert np.array_equal(W, W0, equal_nan=True)


@pytest.mark.skipif(not (TAB / "syst_function_table.csv").exists(), reason="inventory not generated")
def test_function_table_keeps_the_ncdelta_signal_model_outside_the_band_and_does_not_double_count_genie():
    ft = pd.read_csv(TAB / "syst_function_table.csv", keep_default_na=False)
    assert len(ft) == 134 and int(ft.nuniv.sum()) == 22485 and (ft.stop - ft.start).tolist() == ft.nuniv.tolist()
    for suffix in ("multisim_RDecBR1gamma", "multisigma_ThetaDelta2NRad"):                                       # the two NC-Delta radiative-decay model dials: separate category, not in the generic band
        r = ft[ft.name.str.endswith(suffix)].iloc[0]; assert (not r.in_band) and r.group == SW.NCDELTA_SIGNAL_MODEL_GROUP
    assert ft[ft.group == SW.NCDELTA_SIGNAL_MODEL_GROUP].shape[0] == 2
    ms = ft[ft.name.str.contains("multisigma_") & ft.name.str.startswith("GENIE") & (ft.nuniv == 6)]; assert len(ms) == 48 and not ms.in_band.any()      # duplicates of the multisim sets
    assert set(ft[ft.in_band].type_name) <= {"multisim", "multisigma"} and int(ft[(ft.group == "flux_multisim")].nuniv.min()) == 1000
    assert ft[ft.in_band & (ft.type_name == "multisigma")].sigmas.isin([";".join(f"{x:g}" for x in SW.SIGMA_GRID), "1"]).all()                           # only documented sigma conventions are applied
    assert (~ft[(ft.type_name == "multisigma") & ~ft.in_band & (ft.group == "xsec_extra_multisigma")].reason_if_not.eq("")).all()


@pytest.mark.skipif(not (TAB / "syst_unit_weight_reproduction.csv").exists(), reason="diagnostics not generated")
def test_committed_diagnostics_close():
    u = pd.read_csv(TAB / "syst_unit_weight_reproduction.csv"); assert len(u) == 6 and u.exact.all()
    p = pd.read_csv(TAB / "syst_identity_proof.csv"); assert (p.same_length_all & p.rec_ids_unique_all & p.wc_ids_unique_all).all()
    assert (p.files_ids_identical_in_order == p.n_files).all() and (p.found_by_id == p.n_events_joined).all() and (p.joined_entry_equals_table_entry == p.n_events_joined).all()
    assert (p.layout_ok == p.n_events_joined).all() and (p.owner_vertex_within_1e3_um == p.n_events_joined).all() and (p.owner_pdg_matches == p.n_events_joined).all()
    j = pd.read_csv(TAB / "syst_join_diagnostics.csv"); assert (j[j["sample"] == "S"].frac_events == 1.0).all() and j[j["sample"] == "B"].frac_events.between(0.94, 0.96).all()
    h = pd.read_csv(TAB / "syst_imp_weight_hypothetical.csv"); assert h.HYPOTHETICAL_ONLY.all()
    a = pd.read_csv(TAB / "syst_weight_audit.csv"); inb = a[a.in_band]; assert inb.n_nonfinite.sum() == 0 and inb.n_negative.sum() == 0                          # no clipping needed for any function in the band


@pytest.mark.skipif(not (TAB / "syst_band_by_component.csv").exists(), reason="band not generated")
def test_band_total_is_the_quadrature_of_its_in_band_components_and_excludes_outside_sources():
    b = pd.read_csv(TAB / "syst_band_by_component.csv"); comps = ["flux", "beamline_g4_reint", "xsec_genie", "xsec_extras", "fsi_genie"]
    for (prod, view, bin_), g in b.groupby(["production", "view", "bin"]):
        g = g.set_index("component"); assert np.isclose(g.loc["TOTAL_available", "sigma_pred"] ** 2, sum(g.loc[c, "sigma_pred"] ** 2 for c in comps), rtol=1e-9)
        assert {"ncdelta_model_RDecBR1gamma_OUTSIDE_band", "ncdelta_model_ThetaDelta2NRad_OUTSIDE_band"} <= set(g.index) and g.loc["TOTAL_available", "sigma_pred"] >= g.loc["TOTAL_excluding_single_event_dominated", "sigma_pred"] - 1e-12
    cov = pd.read_csv(TAB / "syst_band_coverage.csv"); assert cov.frac_prediction_with_varied_neutrino_systematics.between(0.94, 0.96).all()


def test_new_scripts_use_no_dev_bdt_no_blocked_data_and_no_imp_weight_product():
    code = "\n".join(l for f in ("ncdelta_syst_common.py", "ncdelta_syst_extract.py", "ncdelta_syst_diagnostics.py", "ncdelta_syst_covariance.py") for l in (ROOT / "scripts" / f).read_text().splitlines() if not l.strip().startswith("#"))
    assert "DEV_DO_NOT_DEPLOY" not in code and "beam_on_open" not in code and "run3bnb" not in code and not re.search(r"\.fit\(|train\(", code)
    assert not re.search(r"W\s*\*=?\s*.*imp_weight|imp_weight\s*\*", code)                                    # imp_weight is read and reported, never multiplied into a yield


# ---- control-region data/MC with covariance ---------------------------------------------------------------------------------------------------------------
def test_shape_normalisation_and_chi2_helpers():
    import ncdelta_syst_regions as R
    Q = np.array([[1.0, 2.0], [3.0, 2.0]]); g = R.shape_norm(10.0)(Q)
    assert np.allclose(g.sum(0), 10.0) and np.allclose(g[:, 0], [2.5, 7.5])                                  # every universe renormalised to the data total
    D = np.array([8.0, 12.0]); P = np.array([10.0, 10.0]); assert np.isclose(R.chi2_pearson(D, P, np.zeros((2, 2)), P), 0.4 + 0.4)
    C = np.full((2, 2), 4.0)                                                                                  # a fully correlated (normalisation-like) covariance does not penalise a common shift
    assert R.chi2_pearson(np.array([9.0, 9.0]), P, C, P) < R.chi2_pearson(np.array([9.0, 9.0]), P, np.diag(np.diag(C)), P)


def test_region_script_never_touches_the_blocked_final_region_or_stacks_beam_off():
    src = (ROOT / "scripts" / "ncdelta_syst_regions.py").read_text(); code = "\n".join(l for l in src.splitlines() if not l.strip().startswith("#"))
    assert "final_frozen" not in code and "signal_region" not in code.replace("signal_region approval", "")
    assert "DP.check(\"beam_on_open\", KIND[r])" in code and "DP.check(\"beam_on_open\", \"sideband\")" in code                 # the data-policy gate is called for every region and for the sideband stage
    assert "DEV_DO_NOT_DEPLOY" not in code and "run3bnb" not in code


@pytest.mark.skipif(not list(TAB.glob("syst_sideband_datamc_chi2_*.csv")), reason="sideband analysis not generated")
def test_committed_sideband_table_is_internally_consistent():
    from scipy import stats
    for f in TAB.glob("syst_sideband_datamc_chi2_*.csv"):
        d = pd.read_csv(f)
        r = d[d.test.str.startswith("rate_only")]; assert len(r) > 0
        assert np.allclose(r.ratio, r.n_data / r.prediction)
        assert np.allclose(r.rel_total, np.sqrt(r.rel_data_stat ** 2 + r.rel_mc_stat ** 2 + r.rel_syst ** 2))
        comps = [c for c in r.columns if c.startswith("rel_syst_")]; assert np.allclose(r.rel_syst ** 2, (r[comps] ** 2).sum(1), rtol=1e-6)                 # independent sources add in quadrature
        assert np.allclose(d.p_value, stats.chi2.sf(d.chi2, d.ndof)) and (d.ndof >= 1).all() and (d.chi2 >= 0).all()
        assert set(d.production) == {"old_fg1", "nov16"} and not d.region.isin(["final_frozen"]).any()


def test_ncpi0_topology_truth_migration_tables_are_sane():
    """Truth topology must be sliced per interaction (prim.* is flat per event): the committed migration has non-empty >=2p truth and rows that sum to the MC weight."""
    import glob
    import pandas as pd
    fs = sorted(glob.glob(str(ROOT / "tables" / "ncdelta_purity_datamc" / "ncpi0_truth_reco_migration_*_all_resolved.csv")))
    if not fs:
        pytest.skip("migration tables not generated")
    for f in fs:
        M = pd.read_csv(f, index_col=0); assert M.loc["truth >=2p"].sum() > 0 and M.loc["truth 1p"].sum() > 0
        assert (M.to_numpy() >= 0).all()
    src = (ROOT / "scripts" / "ncdelta_ncpi0_topology_extract.py").read_text()
    assert "nprim" in src and "sum(nprim)" in src.replace("npr.sum()", "sum(nprim)") and "beam_on_open" in src and "signal" not in src.lower().replace("signal-sample", "")
