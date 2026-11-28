"""Upstream nu_e / nu_mu classifier deployment layer: pin, guards, nu_mu simulation correction semantics, overlay identity / sentinel handling, and (when a clone of the release is available)
a bit-for-bit cross-check against the release's own standalone scripts on SYNTHETIC tables. No official sample, no real event, no score of the analysis is touched here."""
import json, os, subprocess, sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

from sbnd_single_photon import upstream_scores as US

REPO = Path(__file__).resolve().parents[1]
CLONE = Path(os.environ.get("SP_UPSTREAM_CLONE", "/home/abhat/Single-photon/upstream_audit/sbnd-wirecell-bdt"))
needs_clone = pytest.mark.skipif(not (CLONE / "releases" / "numu_round3af" / "manifest.json").exists(), reason="no local clone of the upstream release (set SP_UPSTREAM_CLONE)")
CFG = US.load_config()
KEY = ["file_id", "run", "subrun", "event", "cand"]


# ---------------------------------------------------------------- pin / guards (always run) ----------------------------------------------------------------
def test_config_pins_the_defaults_and_is_unauthorised():
    r, m = CFG["release"], CFG["models"]
    assert r["pinned_commit"] == "0f13988db44423a227789e151b0a374e25771abd" and r["trained_on_production"] == "WCLocal2026Nov16"
    assert m["nue"]["folder"] == "nue_round4_ruleA_v2" and m["nue"]["variant"] == "main" and m["numu"]["folder"] == "numu_round3af"
    assert CFG["simulation_correction"]["k"] == 1.071 and CFG["simulation_correction"]["update_flag1"] is True
    g = CFG["evaluation_guard"]
    assert g["authorized"] is False and not any(str(g[k]).strip() for k in ("approved_by", "approved_date", "frozen_model_bundle_sha256", "selection_manifest_sha256"))
    assert CFG["fixtures"] == [] and CFG["applicability"]["old_fg1"]["applicable"] is False and CFG["applicability"]["nov16"]["applicable"] is True


def test_every_registered_sample_is_refused():
    names = list(yaml.safe_load((REPO / "configs" / "samples.yaml").read_text())["samples"])
    assert names
    for s in names + ["official_gen2_ncdelta", "bnb_cv", "beam_on_open", "run3bnb", "beam_off", "nuecc"]:
        with pytest.raises(US.AuthorizationError):
            US.require_authorization(s, CFG)
    ok = dict(CFG, fixtures=["dev_fixture_x"]); assert US.require_authorization("dev_fixture_x", ok) == "fixture"
    partial = yaml.safe_load(yaml.safe_dump(CFG)); partial["evaluation_guard"].update(authorized=True, approved_by="X")      # a half-filled guard still refuses
    with pytest.raises(US.AuthorizationError): US.require_authorization("bnb_cv", partial)


def test_committed_release_audit_is_complete_and_clean():
    h = pd.read_csv(REPO / "tables/upstream_release/release_file_hashes.csv"); a = json.loads((REPO / "tables/upstream_release/release_audit.json").read_text())
    assert len(h) == 57 and h.ok.all() and (h.sha256_manifest == h.sha256_found).all() and h.sha256_manifest.str.len().eq(64).all()
    assert a["ok"] is True and a["head_commit"] == a["pinned_commit"] == CFG["release"]["pinned_commit"] and not [c for c in a["checks"] if not c["ok"]]
    ri = pd.read_csv(REPO / "tables/upstream_release/required_inputs.csv")
    assert (ri[(ri.model == "nue") & (ri.level == "L2")].shape[0] == 243) and ri[ri.model == "numu"].name.isin(["numu_cc_flag"]).any()
    assert set(ri[ri.numu_sim_correction_target].name) >= set(CFG["simulation_correction"]["inputs"])
    nue_l2 = set(ri[(ri.model == "nue") & (ri.level == "L2")].name); assert not (nue_l2 & set(CFG["simulation_correction"]["inputs"] + ["numu_cc_flag"])), "nu_e inputs must be disjoint from the correction targets"


def test_sp_dependency_map_matches_committed_input_tables():
    """The upstream-score inputs of each downstream SP BDT (from the committed input_source tables) are exactly what the overlay mapping replaces; nothing else."""
    sp = CFG["sp_downstream_dependencies"]; T = REPO / "tables"
    srcs = dict(numu_sp="remaining_stage_audit/input_source_table_numu.csv", ncpi0_sp="remaining_stage_audit/input_source_table_ncpi0.csv", other_sp="other_bdt_audit/input_source_table.csv", nue_sp="remaining_stage_audit/input_source_table_nue.csv")
    up = {f"{m}_score" for m in "br3_3 br3_5 br3_6 pio_2 stw_2 stw_3 stw_4 sig_1 sig_2 lol_1 lol_2 tro_1 tro_2 tro_4 tro_5".split()} | {"numu_1_score", "numu_2_score", "cosmict_10_score", "numu_score", "nue_score"}
    for k, f in srcs.items():
        v = set(pd.read_csv(T / f).bdt_variable); assert set(sp[k]) == v & up, k
        for up_col in sp[k].values(): assert up_col.startswith("up_")
    other = set(pd.read_csv(T / srcs["other_sp"]).bdt_variable); assert set(sp["raw_features_that_must_stay_raw"]) <= other, "the `other` SP BDT reads these raw features"


def test_no_scores_or_overlays_of_official_samples_in_the_repo():
    bad = [p for p in (REPO / "tables").rglob("*") if p.is_file() and ("overlay" in p.name.lower() or p.name.startswith("up_") or "upstream_scores" in p.name)]
    assert not bad, bad
    allowed = {"release_audit.json", "release_file_hashes.csv", "required_inputs.csv", "baseline_artifact_hashes.csv", "schema_audit_branches.csv", "schema_audit_summary.json", "sample_applicability.csv"}
    assert {p.name for p in (REPO / "tables/upstream_release").iterdir()} <= allowed        # metadata / provenance only: no score table of any sample


def test_baseline_fingerprint_recorded_and_the_cli_refuses_registered_samples():
    t = pd.read_csv(REPO / "tables/upstream_release/baseline_artifact_hashes.csv"); assert len(t) >= 90 and t.sha256.str.len().eq(64).all()
    for need in ("overall_purity.csv", "control_region_summary_final.csv", "candidates.parquet", "owners_B_nov16.parquet", "signal_event_table_new_any.parquet"): assert t.path.str.contains(need).any(), need
    r = subprocess.run([sys.executable, str(REPO / "scripts/upstream_overlay_build.py"), "--sample", "official_gen2_ncdelta", "--production", "nov16", "--inputs", "/nonexistent", "--tag", "t", "--events", "/nonexistent", "--manifest-urls", "/nonexistent", "--releases", "/nonexistent", "--out", "/tmp/never.parquet"],
                       capture_output=True, text=True); assert r.returncode != 0 and "AuthorizationError" in r.stderr and not Path("/tmp/never.parquet").exists()


def test_provenance_records_the_tree_and_refuses_the_snap_tree():
    assert US.provenance_record(CFG, "synthetic", "nov16", True, 1, "fixture")["wc_tree"] == "recTreeWireCell"
    with pytest.raises(US.UpstreamError, match="recTreeWireCell"): US.provenance_record(CFG, "synthetic", "nov16", True, 1, "fixture", tree="recTreeWireCell_dv2snap")


# ---------------------------------------------------------------- correction semantics (hand-checkable) -------------------------------------------------
def _frames():
    key = ["k"]
    c = pd.DataFrame(dict(k=[0, 1, 2, 3, 4], cosmict_2_filled=[1, 0, 1, 1, 1], cosmict_3_filled=[1, 1, 1, 1, 1], cosmict_7_filled=[1, 1, 1, 1, 1], numu_cc_flag=[1.0, 1, 1, 1, 0], numu_cc_flag_3=[0.0, 0, 0, 1, 0]))
    for n in ("cosmict_2", "cosmict_3", "cosmict_7"):
        for e in ("end", "front"): c[f"{n}_dQ_dx_{e}"] = np.float32([1.0, 2.0, 0.0, np.nan, 3.0])
    # numu_1 segments: cand0 seg: q=1.0 cut 1.05 -> corrected 1.071 >= 1.05: flag off; cand1 two segs (one stays on); cand2 cut=inf; cand3: flag off but flag_3 on; cand4 no flag
    o1 = pd.DataFrame(dict(k=[0, 1, 1, 2, 3, 4], numu_cc_1_medium_dQ_dx=np.float32([1.0, 1.0, 0.5, 5.0, 1.0, np.nan]), numu_cc_1_dQ_dx_cut=np.float32([1.05, 1.05, 1.05, np.inf, 1.05, 1.05]), flag=np.float32([1, 1, 1, 1, 1, 0])))
    o2 = pd.DataFrame(dict(k=[1, 2], flag=np.float32([0, 0])))
    return key, c, o1, o2


def test_correction_semantics_and_originals_untouched():
    key, c, o1, o2 = _frames(); c0, o10 = c.copy(), o1.copy()
    cc, oc, rep = US.apply_numu_sim_correction(c, o1, o2, CFG, True, key)
    pd.testing.assert_frame_equal(c, c0); pd.testing.assert_frame_equal(o1, o10)                                  # originals untouched
    k = np.float32  # float32 columns: q*1.071 in float64 then cast
    assert np.allclose(oc.numu_cc_1_medium_dQ_dx.to_numpy()[:5], np.float32(np.float64(np.float32([1.0, 1.0, 0.5, 5.0, 1.0])) * 1.071)) and np.isnan(oc.numu_cc_1_medium_dQ_dx.iloc[5])
    assert cc.cosmict_2_dQ_dx_end.tolist()[:1] == [np.float32(1.071)] and cc.cosmict_2_dQ_dx_end.iloc[1] == 2.0            # cosmict_2_filled == 0 -> NOT corrected
    assert cc.cosmict_2_dQ_dx_end.iloc[2] == 0.0 and np.isnan(cc.cosmict_2_dQ_dx_end.iloc[3])                               # zero / NaN never scaled
    assert oc.flag.tolist() == [0, 0, 1, 1, 0, 0]                                                                          # cand0 off (1.071 >= 1.05); cand1 seg a off, seg b on; cand2 cut inf stays; cand3 off
    assert cc.numu_cc_flag.tolist() == [0.0, 1, 1, 1, 0]                                                                   # cand0 off; cand3: flag_3 keeps it; cand1: another segment still on
    assert rep["segments_flag1_turned_off"] == 3 and rep["numu_cc_flag_turned_off"] == 1 and (cc[US.CORR_COL] == 1.071).all()


def test_double_correction_data_correction_and_misrouting_refused():
    key, c, o1, o2 = _frames(); cc, oc, _ = US.apply_numu_sim_correction(c, o1, o2, CFG, True, key)
    with pytest.raises(US.UpstreamError, match="twice"): US.apply_numu_sim_correction(cc, oc, o2, CFG, True, key)
    with pytest.raises(US.UpstreamError, match="simulation only"): US.apply_numu_sim_correction(c, o1, o2, CFG, False, key)
    with pytest.raises(US.UpstreamError, match="never carry"): US._check_marker(cc, {"x": oc}, False, CFG, "nue")                    # nu_e must never see corrected inputs
    with pytest.raises(US.UpstreamError, match="needs the corrected copies"): US._check_marker(c, {"numu_1": o1}, True, CFG, "numu")  # simulation scored raw
    with pytest.raises(US.UpstreamError, match="never be corrected"): US._check_marker(cc, {"numu_1": oc}, False, CFG, "numu")      # data scored corrected
    US._check_marker(c, {"numu_1": o1}, False, CFG, "numu"); US._check_marker(cc, {"numu_1": oc}, True, CFG, "numu")             # the two legal routes


# ---------------------------------------------------------------- overlay identity / sentinels ----------------------------------------------------------------
def _ident(n=6):
    return pd.DataFrame(dict(file_index=[0, 0, 1, 1, 2, 2][:n], ev=[0, 1, 0, 1, 0, 1][:n], run=1, subrun=2, evt=range(n), nu_index=[0, 0, 0, 1, 0, 0][:n], c_kine_reco_Enu=np.linspace(1, 2, n)))


def _ov(ident, status=0):
    o = ident[US.EAF_KEY].copy(); o["up_nue_score"] = np.arange(len(o), dtype=float); o["up_nue_status"] = np.int8(status); o["up_numu_score"] = 1.0; o["up_numu_status"] = np.int8(0); o["kine_reco_Enu"] = ident.c_kine_reco_Enu
    return o


def test_join_checks_identity_duplicates_missing_extra():
    i = _ident(); o = _ov(i); j = US.join_overlay(i, o, US.EAF_KEY, {"c_kine_reco_Enu": "kine_reco_Enu"}); assert len(j) == len(i)
    with pytest.raises(US.OverlayError, match="without a score row"): US.join_overlay(i, o.iloc[:-1], US.EAF_KEY)
    with pytest.raises(US.OverlayError, match="without a candidate"): US.join_overlay(i.iloc[:-1], o, US.EAF_KEY)
    with pytest.raises(US.OverlayError, match="duplicate identities in the overlay"): US.join_overlay(i, pd.concat([o, o.iloc[:1]]), US.EAF_KEY)
    with pytest.raises(US.OverlayError, match="duplicate identities in the candidate"): US.join_overlay(pd.concat([i, i.iloc[:1]]), o, US.EAF_KEY)
    bad = o.copy(); bad.loc[3, "kine_reco_Enu"] += 1e-3
    with pytest.raises(US.OverlayError, match="identity check failed"): US.join_overlay(i, bad, US.EAF_KEY, {"c_kine_reco_Enu": "kine_reco_Enu"})
    sw = o.copy(); sw["ev"] = sw["ev"].to_numpy()[::-1]                                                                      # scores attached to the wrong candidate identity
    with pytest.raises(US.OverlayError): US.join_overlay(i, sw, US.EAF_KEY, {"c_kine_reco_Enu": "kine_reco_Enu"})


def test_sentinel_convention_and_sp_input_replacement():
    st = np.array([US.STATUS["scored"], US.STATUS["tagger_not_run"], US.STATUS["input_nan"], US.STATUS["placeholder"]], np.int8)
    ov = pd.DataFrame(dict(up_nue_status=st, up_nue_score=[1.5, np.nan, 2.0, np.nan]))
    assert US.to_chain_convention(ov).nue_score_chain.tolist()[:3] == [1.5, -15.0, -16.2556] and np.isnan(US.to_chain_convention(ov).nue_score_chain.iloc[3])
    i = _ident(); j = US.join_overlay(i, _ov(i), US.EAF_KEY)
    sp = pd.DataFrame(dict(numu_score=-9.0, numu_1_score=-9.0, cosmict_10_score=-9.0, numu_2_score=-9.0, cosmict_2_dQ_dx_end=np.arange(6.0), numu_cc_flag=1.0), index=range(6))
    j["up_numu_1_score"], j["up_cosmict_10_score"], j["up_numu_2_score"] = 0.1, 0.2, 0.3
    out = US.apply_to_sp_inputs(sp, j, "other_sp", CFG); assert (out.numu_score == 1.0).all() and (out.cosmict_10_score == 0.2).all() and out.upstream_replaced.all()
    assert out.cosmict_2_dQ_dx_end.equals(sp.cosmict_2_dQ_dx_end) and out.numu_cc_flag.equals(sp.numu_cc_flag) and (sp.numu_score == -9.0).all()      # raw features identical; input frame untouched
    j2 = j.copy(); j2.loc[2, "up_numu_status"] = US.STATUS["tagger_not_run"]
    with pytest.raises(US.OverlayError, match="no upstream score"): US.apply_to_sp_inputs(sp, j2, "other_sp", CFG)
    assert (~US.apply_to_sp_inputs(sp, j2, "other_sp", CFG, on_unscored="keep_flagged").upstream_replaced).sum() == 1


def test_overlay_is_versioned_and_needs_provenance(tmp_path):
    i = _ident(); o = _ov(i)
    with pytest.raises(US.OverlayError, match="provenance"): US.write_overlay(o, tmp_path / "a.parquet")
    o.attrs["provenance"] = US.provenance_record(CFG, "synthetic", "none", True, len(o), "fixture")
    p = US.write_overlay(o, tmp_path / "a.parquet"); side = json.loads(Path(str(p) + ".provenance.json").read_text())
    assert side["overlay_sha256"] == US.sha256_file(p) and side["numu_sim_dqdx_k_applied"] == 1.071 and side["nue_inputs_corrected"] is False and side["data_corrected"] is False
    with pytest.raises(US.OverlayError, match="never overwritten"): US.write_overlay(o, tmp_path / "a.parquet")
    assert US.provenance_record(CFG, "x", "y", False, 1, "fixture")["numu_sim_dqdx_k_applied"] is None


# ---------------------------------------------------------------- cross-check against the release's own scripts (synthetic tables) ----------------------------------------------------------------
def _run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, (cmd[1], [l for l in r.stderr.splitlines() if "Error" in l or "No match" in l][:3])


def _synthetic(rel: Path, n=400, seed=7):
    rng = np.random.default_rng(seed); nue_m = json.loads((rel / "nue_round4_ruleA_v2/manifest.json").read_text()); numu_m = json.loads((rel / "numu_round3af/manifest.json").read_text())
    base = pd.DataFrame(dict(sample="synth", file_id="f", run=1, subrun=np.arange(n) // 20, event=np.arange(n) % 20, cand=0))
    base["is_placeholder"] = (rng.random(n) < 0.03).astype(int); base["br_filled"] = (rng.random(n) < 0.9).astype(int); base["pio_filled"] = (rng.random(n) < 0.7).astype(int); base["pio_flag_pio"] = (rng.random(n) < 0.3).astype(int)
    base["cosmict_flag_1"] = 0
    cols = {c: rng.normal(size=n).astype(np.float32) for c in [x for x in nue_m["level2"]["main"]["inputs"] if not x.startswith("l1_")] + list(numu_m["inputs"])}
    cols = {k: v for k, v in cols.items() if not k.endswith("_score")}; cands = pd.concat([base, pd.DataFrame(cols)], axis=1).loc[:, lambda d: ~d.columns.duplicated()]
    for sc in ("numu_1_score", "numu_2_score", "cosmict_10_score"): cands[sc] = rng.normal(size=n).astype(np.float32)      # shipped values: the release scorer reads and then replaces them
    for nn in (2, 3, 7): cands[f"cosmict_{nn}_filled"] = (rng.random(n) < 0.8).astype(np.float32)
    for c in CFG["simulation_correction"]["inputs"]:
        if c != "numu_cc_1_medium_dQ_dx": cands[c] = np.abs(rng.normal(1.0, 0.5, n)).astype(np.float32); cands.loc[rng.random(n) < 0.1, c] = np.nan
    cands["numu_cc_flag"] = (rng.random(n) < 0.5).astype(np.float32); cands["numu_cc_flag_3"] = (rng.random(n) < 0.1).astype(np.float32)
    for nm in ("cosmict_4_angle_beam", "cosmict_7_angle_beam", "cosmict_7_theta", "cosmict_7_phi"): cands.loc[rng.random(n) < 0.2, nm] = np.nan
    objs = {}
    def mk(inputs, extra=None, flag=False, cut=None):
        rows = []
        for i in range(n):
            for _ in range(rng.integers(0, 5)): rows.append(i)
        idx = np.array(rows, int); O = base.iloc[idx][["sample", "file_id", "run", "subrun", "event", "cand"]].reset_index(drop=True)
        for c in inputs: O[c] = rng.normal(size=len(O)).astype(np.float32)
        if flag: O["flag"] = (rng.random(len(O)) < 0.5).astype(np.float32)
        return O
    for m, v in nue_m["level1"]["models"].items():
        O = mk([c for c in v["inputs"] if c != "pio_mip_id"], flag=True)
        if "pio_mip_id" in v["inputs"]: O = O.merge(pd.concat([base[["sample", "file_id", "run", "subrun", "event", "cand"]], cands[["pio_mip_id"]]], axis=1), on=["sample", "file_id", "run", "subrun", "event", "cand"])
        objs[("nue", m)] = O
    for m, v in numu_m["level1"]["models"].items():
        O = mk(v["inputs"], flag=m in ("numu_1", "numu_2"))
        if m == "numu_1":
            O["numu_cc_1_medium_dQ_dx"] = np.abs(O["numu_cc_1_medium_dQ_dx"]) + 0.5; O["numu_cc_1_dQ_dx_cut"] = np.abs(rng.normal(1.6, 0.3, len(O))).astype(np.float32); O.loc[rng.random(len(O)) < 0.2, "numu_cc_1_dQ_dx_cut"] = np.inf
        if m == "cosmict_10": O.loc[rng.random(len(O)) < 0.2, "cosmict_10_angle_beam"] = np.nan
        objs[("numu", m)] = O
    return cands, objs


@needs_clone
def test_cross_check_against_release_scripts_on_synthetic_tables(tmp_path):
    rel = CLONE / "releases"; cands, objs = _synthetic(rel); T = tmp_path / "t"; T.mkdir(); (T / "cands_synth.parquet").parent.mkdir(exist_ok=True)
    cands.to_parquet(T / "cands_synth.parquet", index=False)
    for (fam, m), O in objs.items(): O.to_parquet(T / f"objs_{m}_synth.parquet", index=False)
    py = sys.executable
    # ---- nu_e ----
    _run([py, str(CLONE / "release/score_release.py"), str(rel / "nue_round4_ruleA_v2"), str(T), "synth", "--out", str(tmp_path / "nue_up.parquet"), "--nthread", "2"])
    up = pd.read_parquet(tmp_path / "nue_up.parquet")
    ours = US.score_nue(rel, CFG, cands, {m: O for (f, m), O in objs.items() if f == "nue"}, KEY)
    j = up.merge(ours, on=KEY, how="left", validate="one_to_one"); assert len(up) == int(((cands.is_placeholder == 0) & (cands.br_filled == 1)).sum()) and len(ours) == len(cands)
    assert (j.score.to_numpy() == j.up_nue_score.to_numpy()).all(), np.abs(j.score - j.up_nue_score).max()                  # bit identical final margin
    for m in json.loads((rel / "nue_round4_ruleA_v2/manifest.json").read_text())["level1"]["models"]:
        assert (j["l1_" + m].to_numpy() == j["up_nue_l1_" + m].to_numpy()).all(), m
    assert set(ours.loc[ours.up_nue_status == US.STATUS["tagger_not_run"]].index) == set(cands.index[(cands.br_filled != 1) & (cands.is_placeholder == 0)])
    assert ours.loc[ours.up_nue_status.isin([1, 2]), "up_nue_score"].isna().all()
    # ---- nu_mu: simulation (correct first, as make_corrected_tables does) and data (raw) ----
    Tc = tmp_path / "tc"
    _run([py, str(CLONE / "training/numu/make_corrected_tables.py"), str(T), str(Tc), str(rel / "numu_round3af/correction.json"), "--samples", "synth", "--update-flag1"])
    for d, name, sim in ((Tc, "sim", True), (T, "data", False)):
        _run([py, str(CLONE / "training/numu/score_numu_release.py"), str(rel / "numu_round3af"), str(d), "synth", str(tmp_path / f"numu_{name}.parquet")])
        upn = pd.read_parquet(tmp_path / f"numu_{name}.parquet"); o = {m: O for (f, m), O in objs.items() if f == "numu"}; c = cands
        if sim:
            c, o1, rep = US.apply_numu_sim_correction(cands, o["numu_1"], o["numu_2"], CFG, True, KEY); o = dict(o, numu_1=o1)
            cr = pd.read_parquet(Tc / "cands_synth.parquet"); orr = pd.read_parquet(Tc / "objs_numu_1_synth.parquet")                  # the release's corrected tables == our corrected copies
            for col in CFG["simulation_correction"]["inputs"] + ["numu_cc_flag"]:
                if col != "numu_cc_1_medium_dQ_dx": assert np.array_equal(c[col].to_numpy(), cr[col].to_numpy(), equal_nan=True), col
            assert np.array_equal(o["numu_1"].numu_cc_1_medium_dQ_dx.to_numpy(), orr.numu_cc_1_medium_dQ_dx.to_numpy(), equal_nan=True) and np.array_equal(o["numu_1"].flag.to_numpy(), orr.flag.to_numpy())
            assert rep["numu_cc_flag_turned_off"] > 0 and rep["segments_flag1_turned_off"] > 0                                    # the synthetic set exercises the flag update
        ours = US.score_numu(rel, CFG, c, o, KEY, sim)
        jj = upn.merge(ours, on=KEY, how="left", validate="one_to_one")
        keep = cands.is_placeholder == 0; assert len(upn) == len(cands) and len(ours) == len(cands)
        m = (jj.is_placeholder if "is_placeholder" in jj else pd.Series(0, index=jj.index)).eq(0) if False else jj.up_numu_status.eq(US.STATUS["scored"])
        assert (jj.loc[m, "d6_f0"].to_numpy() == jj.loc[m, "up_numu_margin"].to_numpy()).all(), (name, np.abs(jj.loc[m, "d6_f0"] - jj.loc[m, "up_numu_margin"]).max())
        for mm in ("numu_1", "numu_2", "cosmict_10"): assert (jj.loc[m, "l1_" + mm].to_numpy() == jj.loc[m, f"up_{mm}_score"].to_numpy()).all(), mm
    # sim and data differ (the correction acts), nue is unaffected by it
    s, d = pd.read_parquet(tmp_path / "numu_sim.parquet"), pd.read_parquet(tmp_path / "numu_data.parquet"); assert (s.d6_f0.to_numpy() != d.d6_f0.to_numpy()).mean() > 0.2


@needs_clone
def test_release_verification_passes_on_the_clone_and_detects_tampering(tmp_path):
    rep = US.verify_release(CLONE / "releases", CFG, head_commit=CFG["release"]["pinned_commit"]); assert rep["ok"], [c for c in rep["checks"] if not c["ok"]]
    bad = US.verify_release(CLONE / "releases", CFG, head_commit="0" * 40, dirty=True); assert not bad["ok"]
    cfg2 = yaml.safe_load(yaml.safe_dump(CFG)); cfg2["simulation_correction"]["k"] = 1.07; assert not US.verify_release(CLONE / "releases", cfg2, head_commit=CFG["release"]["pinned_commit"])["ok"]


def test_bundle_template_is_incomplete_by_design_and_a_complete_one_passes():
    t = yaml.safe_load((REPO / "configs/frozen_bundle_manifest.template.yaml").read_text()); p = US.validate_frozen_bundle(t, CFG)
    assert len(p) > 20 and any("empty" in x for x in p)                         # the template can never pass as it stands
    h = "a" * 64
    t.update(frozen_utc="2026-12-01T00:00:00Z", frozen_by="X Y", code=dict(repo="r", commit="c"), production=dict(name="WCLocal2026Nov16", wct="0.38.0", wc_tree="recTreeWireCell", vertex_configuration="dv2_split_move", effective_boundary_treatment="box", upstream_applicability_statement="trained here"))
    t["sp_models"] = [dict(name=n, file="f", sha256=h, xgboost_version="3.4.1", inputs_file="i", inputs_sha256=h, upstream_score_inputs=({"numu_score": "up_numu_score"} if n == "numu" else {}), raw_features_used=[], score_definition="margin", sentinel_policy="s", frozen_thresholds={"cut": 0.0}) for n in ("numu", "other", "ncpi0", "nue")]
    t["selection_manifest"].update(file="s", sha256=h, candidate_policy="any", fiducial_volume="box", signal_definition="d", topology_definition="t")
    t["training_membership"].update(manifests=[{"sample": "x"}], split_rule="r", beam_off_half_used_for_training="odd")
    assert US.validate_frozen_bundle(t, CFG) == []
    t["upstream_release"]["nue"]["variant"] = "nogap"; t["production"]["wc_tree"] = "recTreeWireCell_dv2snap"; t["validation"]["no_official_sample_used"] = False
    p2 = US.validate_frozen_bundle(t, CFG); assert any("nue variant" in x for x in p2) and any("verified for that tree only" in x for x in p2) and any("no_official_sample_used" in x for x in p2)


def test_identity_translation_is_one_to_one_and_loud():
    urls = ["root://x//a/unitA/f.root", "root://x//a/unitB/f.root"]; fm = US.file_map_from_manifest(urls, "dirname"); assert fm.file_id.tolist() == ["unitA", "unitB"] and fm.file_index.tolist() == [0, 1]
    with pytest.raises(US.OverlayError, match="not unique"): US.file_map_from_manifest(["a/x/f.root", "a/y/f.root"], "basename")
    ev = pd.DataFrame(dict(file_index=[0, 0, 1], ev=[0, 1, 0], run=1, subrun=[1, 1, 2], evt=[10, 11, 10]))
    df = pd.DataFrame(dict(file_id=["unitA", "unitA", "unitB"], run=1, subrun=[1, 1, 2], event=[10, 11, 10], cand=[0, 1, 0], up_nue_score=[1.0, 2.0, 3.0]))
    t = US.translate_identity(df, ev, fm); assert t[US.EAF_KEY].values.tolist() == [[0, 0, 1, 1, 10, 0], [0, 1, 1, 1, 11, 1], [1, 0, 1, 2, 10, 0]] and t.up_nue_score.tolist() == [1.0, 2.0, 3.0]
    with pytest.raises(US.OverlayError, match="not in the manifest"): US.translate_identity(df.assign(file_id="zzz"), ev, fm)
    with pytest.raises(US.OverlayError, match="not in our events table"): US.translate_identity(df.assign(event=[10, 99, 10]), ev, fm)
    with pytest.raises(US.OverlayError, match="not unique"): US.translate_identity(df, pd.concat([ev, ev.iloc[:1]]), fm)
    c = pd.DataFrame(dict(file_id=["unitA"], run=1, subrun=1, event=10, cand=0, kine_reco_Enu=0.5, shw_sp_energy=3.0)); o = pd.DataFrame(dict(file_id=["unitA"], run=1, subrun=1, event=10, cand=0, up_nue_score=1.0))
    k = ["file_id", "run", "subrun", "event", "cand"]; assert US.carry_identity_checks(o, c, k, {"kine_reco_Enu": "kine_reco_Enu", "shw_sp_energy": "shw_sp_energy"}).columns.tolist()[-2:] == ["id_kine_reco_Enu", "id_shw_sp_energy"]
