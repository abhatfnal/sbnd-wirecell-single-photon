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
    assert CFG["fixtures"] == ["upstream_r4_dev_fixture_v1"] and CFG["applicability"]["old_fg1"]["applicable"] is False and CFG["applicability"]["nov16"]["applicable"] is True


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
    assert len(h) == 61 and h.ok.all() and (h.sha256_manifest == h.sha256_found).all() and h.sha256_manifest.str.len().eq(64).all()
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
    allowed = {"release_audit.json", "release_file_hashes.csv", "required_inputs.csv", "baseline_artifact_hashes.csv", "schema_audit_branches.csv", "schema_audit_summary.json", "sample_applicability.csv", "official_id_space_summary.csv", "beam_off_membership_ledger.csv", "membership_audit_result.csv", "fixture_closure_report.json", "membership_audit_summary.json", "official_vs_aurora_membership.csv"}
    assert {p.name for p in (REPO / "tables/upstream_release").iterdir()} <= allowed        # metadata / provenance only: no score table of any sample


def test_baseline_fingerprint_recorded_and_the_cli_refuses_registered_samples():
    t = pd.read_csv(REPO / "tables/upstream_release/baseline_artifact_hashes.csv"); assert len(t) >= 90 and t.sha256.str.len().eq(64).all()
    for need in ("overall_purity.csv", "control_region_summary_final.csv", "candidates.parquet", "owners_B_nov16.parquet", "signal_event_table_new_any.parquet"): assert t.path.str.contains(need).any(), need
    r = subprocess.run([sys.executable, str(REPO / "scripts/upstream_overlay_build.py"), "--sample", "official_gen2_ncdelta", "--production", "nov16", "--inputs", "/nonexistent", "--tag", "t", "--events", "/nonexistent", "--manifest-urls", "/nonexistent", "--releases", "/nonexistent", "--out", "/tmp/never.parquet"],
                       capture_output=True, text=True); assert r.returncode != 0 and "AuthorizationError" in r.stderr and not Path("/tmp/never.parquet").exists()


def test_provenance_records_the_tree_and_refuses_the_snap_tree():
    assert US.provenance_record(CFG, "synthetic", "nov16", True, 1, "fixture")["wc_tree"] == "recTreeWireCell"
    with pytest.raises(US.UpstreamError, match="recTreeWireCell"): US.provenance_record(CFG, "synthetic", "nov16", True, 1, "fixture", tree="recTreeWireCell_dv2snap")
    for bad in ("old_fg1", "final_effective_boundary"):
        with pytest.raises(US.UpstreamError): US.provenance_record(CFG, "synthetic", bad, True, 1, "fixture")


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
    o = ident[US.EAF_KEY].copy(); o["up_nue_score"] = np.arange(len(o), dtype=float); o["up_nue_status"] = np.int8(status); o["up_numu_score"] = 1.0; o["up_numu_status"] = np.int8(0); o["up_origin"] = US.ORIGIN_NOMINAL; o["kine_reco_Enu"] = ident.c_kine_reco_Enu
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
    j2 = j.copy(); j2.loc[2, "up_numu_status"] = US.STATUS["tagger_not_run"]; j2.loc[3, "up_nue_status"] = US.STATUS["placeholder"]
    assert US.apply_to_sp_inputs(sp, j2, "other_sp", CFG).upstream_replaced.all()                       # statuses are descriptive: the chain stores a value for EVERY candidate (br_filled == 0, placeholders)
    j3 = j.copy(); j3.loc[2, "up_numu_score"] = np.nan
    with pytest.raises(US.OverlayError, match="non-finite"): US.apply_to_sp_inputs(sp, j3, "other_sp", CFG)
    assert (~US.apply_to_sp_inputs(sp, j3, "other_sp", CFG, on_unscored="keep_flagged").upstream_replaced).sum() == 1


def test_overlay_is_versioned_and_needs_provenance(tmp_path):
    i = _ident(); o = _ov(i)
    with pytest.raises(US.OverlayError, match="provenance"): US.write_overlay(o, tmp_path / "a.parquet")
    o.attrs["provenance"] = US.provenance_record(CFG, "synthetic", "nov16", True, len(o), "fixture")
    p = US.write_overlay(o, tmp_path / "a.parquet"); side = json.loads(Path(str(p) + ".provenance.json").read_text())
    assert side["overlay_sha256"] == US.sha256_file(p) and side["numu_sim_dqdx_k_applied"] == 1.071 and side["nue_inputs_corrected"] is False and side["data_corrected"] is False
    with pytest.raises(US.OverlayError, match="never overwritten"): US.write_overlay(o, tmp_path / "a.parquet")
    assert US.provenance_record(CFG, "x", "nov16", False, 1, "fixture")["numu_sim_dqdx_k_applied"] is None


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
    ours = US.score_nue(rel, CFG, cands, {m: O for (f, m), O in objs.items() if f == "nue"}, KEY, backend="xgboost_standalone")
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
        ours = US.score_numu(rel, CFG, c, o, KEY, sim, backend="xgboost_standalone")
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
    t["upstream_scorer"].update(repo="r", commit="c", sha256=h, closure_report="x", closure_report_sha256=h, closure_exact=True, standalone_xgboost_used_for_production=False)
    t["deployment_route"].update(route="R2", r2_evidence=dict(final_domain_closure_report_sha256=h, final_domain_closure_exact=True))
    t["beam_off_normalization"].update(even_run_exposure_ledger_sha256=h, counter_convention="gates", live_time_treatment="x", run_coverage_statement="y", approved_by="Z")
    t["selection_manifest"].update(file="s", sha256=h, candidate_policy="any", fiducial_volume="box", signal_definition="d", topology_definition="t")
    t["training_membership"].update(manifests=[{"sample": "x"}], split_rule="r", beam_off_half_used_for_training="odd", sets_covered=["upstream_fit", "upstream_dev", "sp_fit", "sp_nested_val", "sp_outer_holdout", "dlvertex_train"], dlvertex_training_membership="d", beam_off_upstream_training_files="b")
    assert US.validate_frozen_bundle(t, CFG) == []
    r1 = yaml.safe_load(yaml.safe_dump(t)); r1["deployment_route"].update(route="R1", r1_evidence=dict(job_manifest_sha256="x", all_sim_jobs_release_weights=True, all_sim_jobs_k_1p071=False, no_data_job_corrected=True, sites=["aurora"]))
    pr1 = US.validate_frozen_bundle(r1, CFG); assert any("job_manifest_sha256" in q for q in pr1) and any("all_sim_jobs_k_1p071" in q for q in pr1) and any("both production sites" in q for q in pr1)
    bo = yaml.safe_load(yaml.safe_dump(t)); bo["beam_off_normalization"]["evaluation_files"] = "all"; assert any("even_run_only" in q for q in US.validate_frozen_bundle(bo, CFG))
    t["upstream_release"]["nue"]["variant"] = "nogap"; t["production"]["wc_tree"] = "recTreeWireCell_dv2snap"; t["validation"]["no_official_sample_used"] = False; t["upstream_scorer"]["standalone_xgboost_used_for_production"] = True; t["upstream_scorer"]["closure_exact"] = False
    p2 = US.validate_frozen_bundle(t, CFG); assert any("nue variant" in x for x in p2) and any("verified for that tree only" in x for x in p2) and any("no_official_sample_used" in x for x in p2) and any("standalone_xgboost" in x for x in p2) and any("closure_exact" in x for x in p2)


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


def test_committed_schema_audit_is_complete():
    s = json.loads((REPO / "tables/upstream_release/schema_audit_summary.json").read_text()); t = pd.read_csv(REPO / "tables/upstream_release/schema_audit_branches.csv")
    assert s["files_checked"] == len(t) == s["complete_files"] and s["files_with_error"] == 0 and s["n_required_branches"] == 650 and (t.n_missing == 0).all()
    assert set(t["sample"]) == {"bnb_cv", "official_gen2_ncdelta", "nuecc", "beam_off", "beam_on_open", "run3bnb"} and set(t.production) == {"old_fg1", "nov16"}


# ---------------------------------------------------------------- backend / origin / route / fixture guards ----------------------------------------------------------------
def test_nominal_backend_is_the_vendored_toolkit_equivalent_scorer_and_standalone_cannot_write_production(tmp_path, monkeypatch):
    pin = CFG["scoring_backend"]["reference_pin"]
    assert CFG["scoring_backend"]["nominal"] == "toolkit_equivalent" and CFG["scoring_backend"]["cross_check_only"] == ["xgboost_standalone"] and "toolkit_equivalent" in US.BACKENDS
    w = US._bundle(CFG); assert w.__version__ == "1.0.0" and w.bundle_fingerprint()[0] == pin["bundle_fingerprint"] == "976614411c847041139eacd50ca8ffba54d50eb1083359fe73167e8fe4ad0c9e"
    assert pin["canonical_release_inventory_fingerprint"] == "1d48baed0b3d386b3848c20829099b736f42d6020456f4ea60dd4dbbf60c1f9f"
    bad = yaml.safe_load(yaml.safe_dump(CFG)); bad["scoring_backend"]["reference_pin"]["bundle_fingerprint"] = "0" * 64
    with pytest.raises(US.UpstreamError, match="!= pin"): US._bundle(bad)                                   # a modified / different bundle is refused
    monkeypatch.delenv(CFG["scoring_backend"]["shipped_weights_env"], raising=False)
    with pytest.raises(US.UpstreamError, match="SP_SHIPPED_WIRECELL_DATA"): US.score_nue("x", CFG, pd.DataFrame(), {}, US.UPSTREAM_KEY)
    with pytest.raises(US.BackendUnavailable): US.score_numu("x", CFG, None, {}, US.UPSTREAM_KEY, True, backend="not_registered")
    k = ["k"]; a = pd.DataFrame(dict(k=[1])); a.attrs["backend"] = "xgboost_standalone"; b = a.copy(); b.attrs["backend"] = "xgboost_standalone"
    ov = US.make_overlay(a, b, k, US.provenance_record(CFG, "synthetic", "nov16", True, 1, "fixture"))
    assert ov["up_origin"].iloc[0] == US.ORIGIN_XGB and ov.attrs["provenance"]["purpose"] == "cross_check" and ov.attrs["provenance"]["backend_nominal"] is False
    ov.attrs["provenance"]["purpose"] = "production"
    with pytest.raises(US.OverlayError, match="cross_check"): US.write_overlay(ov, tmp_path / "x.parquet")
    c = b.copy(); c.attrs["backend"] = "other"
    with pytest.raises(US.OverlayError, match="ONE backend"): US.make_overlay(a, c, k, {})
    a.attrs["backend"] = b.attrs["backend"] = "toolkit_equivalent"; n = US.make_overlay(a, b, k, US.provenance_record(CFG, "synthetic", "nov16", True, 1, "fixture")); assert n["up_origin"].iloc[0] == US.ORIGIN_NOMINAL and n.attrs["provenance"]["backend_nominal"]


def test_canonical_inventory_fingerprint_and_vendored_bundle_agree_with_the_committed_tables():
    import hashlib
    h = pd.read_csv(REPO / "tables/upstream_release/release_file_hashes.csv"); mod = h[~h.role.isin(["manifest", "correction", "chain_weights_json"])]
    assert len(mod) == 57 and mod.path.is_unique
    lines = "".join(f"{p} {s}\n" for p, s in sorted(zip(mod.path, mod.sha256_manifest))); assert hashlib.sha256(lines.encode()).hexdigest() == CFG["scoring_backend"]["reference_pin"]["canonical_release_inventory_fingerprint"]
    import sys; sys.path.insert(0, str(REPO / "third_party/wc_upstream_chain_bundle")); import wc_upstream_chain as w
    assert w.release_inventory()["fingerprints"]["canonical_inventory"] == CFG["scoring_backend"]["reference_pin"]["canonical_release_inventory_fingerprint"]


def test_origins_are_never_mixed_into_sp_features():
    i = _ident(); j = US.join_overlay(i, _ov(i), US.EAF_KEY); j["up_origin"] = US.ORIGIN_XGB
    for c in ("up_numu_1_score", "up_cosmict_10_score", "up_numu_2_score"): j[c] = 0.1
    sp = pd.DataFrame(dict(numu_score=-9.0, numu_1_score=-9.0, cosmict_10_score=-9.0, numu_2_score=-9.0), index=range(6))
    with pytest.raises(US.OverlayError, match="never be mixed"): US.apply_to_sp_inputs(sp, j, "other_sp", CFG)                      # cross-check scores refused as nominal
    j["up_origin"] = US.ORIGIN_NOMINAL; assert (US.apply_to_sp_inputs(sp, j, "other_sp", CFG).upstream_origin == US.ORIGIN_NOMINAL).all()
    j.loc[0, "up_origin"] = "stored_production_score"
    with pytest.raises(US.OverlayError, match="never be mixed"): US.apply_to_sp_inputs(sp, j, "other_sp", CFG)                      # one origin per frame


def test_routes_and_domain_protection():
    assert US.resolve_route(CFG, "nov16", "recTreeWireCell") == "R2"
    with pytest.raises(US.UpstreamError, match="verified for tree"): US.resolve_route(CFG, "nov16", "recTreeWireCell_dv2snap")
    with pytest.raises(US.UpstreamError, match="not applicable"): US.resolve_route(CFG, "old_fg1", "recTreeWireCell")
    with pytest.raises(US.UpstreamError, match="no applicability entry"): US.resolve_route(CFG, "final_effective_boundary", "recTreeWireCell")
    r1 = yaml.safe_load(yaml.safe_dump(CFG)); r1["applicability"]["nov16"]["route"] = "R1"
    with pytest.raises(US.UpstreamError, match="R1 needs"): US.resolve_route(r1, "nov16", "recTreeWireCell")            # stored Nov16 scores are the SHIPPED weights, not released-model scores
    assert CFG["applicability"]["nov16"]["stored_scores"]["released_models_booked"] is False and CFG["applicability"]["nov16"]["stored_scores"]["weights_domain"] == "shipped_microboone"
    r1["applicability"]["nov16"]["stored_scores"].update(released_models_booked=True, booked_chain_weights_sha256_table="tables/x.csv"); assert US.resolve_route(r1, "nov16", "recTreeWireCell") == "R1"


def test_fixture_registration_refuses_official_files_and_closure_is_exact():
    off = {"reco2-reco1-detsim-g4-filter-gen-0009-3f30-ac82-477c_ncdeltarad.wc.flat.caf.root"}
    assert US.validate_fixture_manifest(["/a/b/dev-0001-aaaa-bbbb-cccc.wc.flat.caf.root"], off, "development") == []
    assert any("official-sample file names" in x for x in US.validate_fixture_manifest(["/z/" + next(iter(off))], off, "development"))
    assert any("production-job id" in x for x in US.validate_fixture_manifest(["x-filter-gen-0009-3f30-ac82-477c_other.root"], off, "development"))
    assert any("permitted development role" in x for x in US.validate_fixture_manifest(["f.root"], off, "evaluation"))
    e = pd.DataFrame(dict(k=[1, 2, 3], s=[1.0, np.nan, 3.0])); g = e.copy(); assert US.closure_report(e, g, ["k"], ["s"])["exact"]
    g.loc[2, "s"] = 3.0 + 1e-12; r = US.closure_report(e, g, ["k"], ["s"]); assert not r["exact"] and r["columns"]["s"]["n_mismatch"] == 1
    assert US.closure_report(e, g.iloc[:2], ["k"], ["s"])["missing_rows"] == 1


def test_membership_classification_never_treats_different_job_ids_as_independence():
    import importlib.util
    sp = importlib.util.spec_from_file_location("ma", REPO / "scripts/upstream_membership_audit.py"); ma = importlib.util.module_from_spec(sp); sp.loader.exec_module(ma)
    off = pd.DataFrame(dict(sample="official_gen2_ncdelta", file_name=["reco2-x-gen-0009-3f30-ac82-477c_ncdeltarad.wc.flat.caf.root", "reco2-x-gen-0013-f189-8bbd-676e_ncdeltarad.wc.flat.caf.root"], run=[201, 202], subrun=[1, 1], event=[5, 6]))
    off["gen_id"] = off.file_name.map(ma.gen_id); assert off.gen_id.tolist() == ["0009-3f30-ac82-477c", "0013-f189-8bbd-676e"]
    v = lambda m, **k: ma.classify(off, pd.DataFrame(m), **k).verdict.iloc[0]
    assert v(dict(set="upstream_fit", sample="a", file_name=["reco2-x-gen-0009-3f30-ac82-477c_ncdeltarad.wc.flat.caf.root"])) == "CONFIRMED_IDENTICAL_FILE"
    assert v(dict(set="upstream_fit", sample="a", file_name=["reco1-y-filter-gen-0013-f189-8bbd-676e_ncdeltarad.root"])) == "CONFIRMED_SHARED_GENERATOR_ANCESTRY"      # same production job, different stage file
    assert v(dict(set="sp_fit", sample="a", file_name=["aurora-1111-2222-3333-4444.root"], run=[201], subrun=[1], event=[5])) == "NUMERICAL_COLLISION_NO_ANCESTRY"
    o2 = off.assign(seed=[750004154, 750004155])
    own = ma.classify(o2, pd.DataFrame(dict(set="sp_fit", sample="a", file_name=["aurora-1111-2222-3333-4444.root"], seed=[750004154]))); assert own.verdict.iloc[0] == "SHARED_SEED_REQUIRES_VERIFICATION"
    # different job ids and different run numbers: NOT independence unless the official seed namespace is documented and distinct
    m = dict(set="sp_fit", sample="a", file_name=["aurora-1111-2222-3333-4444.root"], run=[7000005], subrun=[1], event=[1])
    assert v(m) == "UNDETERMINED_INDEPENDENCE" and "seed namespace" in ma.classify(off, pd.DataFrame(m)).reason.iloc[0]
    assert v(m, official_seed_documented={"official_gen2_ncdelta": "distinct_namespace"}) == "ESTABLISHED_DISJOINT"
    assert v(dict(set="sp_fit", sample="a", run=[1], subrun=[1], event=[1])) == "UNDETERMINED_INDEPENDENCE"                                                       # no file / job identifier at all
    assert v(dict(set="train", sample="beamoff", file_name=["other-run1-file.root"], is_data=[True])) == "ESTABLISHED_DISJOINT"                                      # data files: no generator, no file in common
    assert ma.OFFICIAL_SEED_NAMESPACE_DOCUMENTED == {}                                                                                                            # no official seed namespace is documented today
    L = ma.beam_off_ledger(); assert len(L) == 1058 and (L.groupby("parity").size().to_dict() == {"even": 486, "odd": 572}) and (L[L.parity == "odd"].policy_class == "UPSTREAM_TRAINING_HALF_EXCLUDE").all() and (L.in_sp_other_staged_558.astype(bool).sum() in (0, 558))


def test_committed_v7_result_reports_ncdelta_undetermined_and_beamoff_identical():
    r = pd.read_csv(REPO / "tables/upstream_release/official_vs_aurora_membership.csv").set_index("official_sample")
    assert r.loc["official_gen2_ncdelta", "verdict"] == "UNDETERMINED_INDEPENDENCE" and r.loc["official_gen2_ncdelta", ["files_same_name", "files_same_genjob", "run_subrun_event_coincidences"]].sum() == 0
    assert r.loc["beam_off", "verdict"] == "CONFIRMED_IDENTICAL_FILE" and r.loc["beam_off", "files_same_name"] >= 544
    import importlib.util
    sp = importlib.util.spec_from_file_location("ma", REPO / "scripts/upstream_membership_audit.py"); ma = importlib.util.module_from_spec(sp); sp.loader.exec_module(ma); assert set(r.verdict) <= set(ma.VERDICTS)


# ---------------------------------------------------------------- closure on the authorised development fixture (skipped if not present) ----------------------------------------------------------------
FIXTURE = Path(os.environ.get("SP_UPSTREAM_FIXTURE_DIR", "/exp/sbnd/data/users/abhat/single_photon_ncdelta/aurora_fixtures/upstream_r4_dev_fixture_v1")); SHIPPED = os.environ.get("SP_SHIPPED_WIRECELL_DATA", "")
needs_fixture = pytest.mark.skipif(not ((FIXTURE / "FIXTURE_MANIFEST.json").exists() and (CLONE / "releases").exists() and SHIPPED), reason="fixture, release clone or SP_SHIPPED_WIRECELL_DATA missing")


@needs_fixture
def test_nominal_adapter_is_bit_exact_on_the_fixture_and_never_corrects_data_or_nue(monkeypatch):
    monkeypatch.setenv(CFG["scoring_backend"]["shipped_weights_env"], SHIPPED); man = json.loads((FIXTURE / "FIXTURE_MANIFEST.json").read_text()); rel = CLONE / "releases"; n = 0
    assert man["name"] in CFG["fixtures"]
    for case in man["cases"]:
        d = FIXTURE / case["dir"]
        if not d.is_dir(): continue
        C = pd.read_parquet(d / "cands.parquet"); E = pd.read_parquet(d / "expected_upstream.parquet"); key = case["key"]; sim = case["kind"] == "mc"; before = C.copy(deep=True)
        O = {m: pd.read_parquet(d / f"objs_{m}.parquet") for m in json.loads((rel / "numu_round3af/manifest.json").read_text())["level1"]["models"]}
        O.update({m: pd.read_parquet(d / f"objs_{m}.parquet") for m in json.loads((rel / "nue_round4_ruleA_v2/manifest.json").read_text())["level1"]["models"]})
        nue = US.score_nue(rel, CFG, C, O, key, is_simulation=sim); numu = US.score_numu(rel, CFG, C, O, key, sim)
        pd.testing.assert_frame_equal(C, before)                                                                    # raw inputs untouched
        bits = lambda x: np.asarray(x, np.float64).astype(np.float32).view(np.uint32)
        assert (bits(nue.up_nue_score) == bits(E.chain_release_nue_score)).all() and (bits(numu.up_numu_score) == bits(E.chain_release_numu_score)).all(), case["dir"]
        for m in ("br3_3", "pio_2", "tro_5"): assert (bits(nue["up_nue_l1_" + m]) == bits(E[f"chain_release_{m}_score"])).all()
        assert (E.fixture_tags.fillna("").str.contains("br_filled_0")).any() == bool((nue.up_nue_status == US.STATUS["tagger_not_run"]).any())             # br_filled == 0 rows carry chain values, flagged not NaN
        assert np.isfinite(nue.up_nue_score).all() and np.isfinite(numu.up_numu_score).all(); n += 1
        if not sim: assert (numu.get("up_numu_sim_dqdx_scale", pd.Series([1.0])) == 1.0).all()                      # data are never corrected
    assert n == 8
    mk = C.assign(**{US.CORR_COL: 1.071})
    with pytest.raises(US.UpstreamError, match="exactly once"): US.score_numu(rel, CFG, mk, O, key, True)           # a marked (already corrected) copy is refused by the nominal backend


@needs_fixture
def test_closure_script_report_is_exact(tmp_path):
    out = tmp_path / "r.json"; env = dict(os.environ, SP_SHIPPED_WIRECELL_DATA=SHIPPED)
    r = subprocess.run([sys.executable, str(REPO / "scripts/upstream_fixture_closure.py"), "--fixture", str(FIXTURE), "--releases", str(CLONE / "releases"), "--builder", str(CLONE / "tables/build_tables.py"), "--shipped", SHIPPED, "--out", str(out)], capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stderr[-600:]; rep = json.loads(out.read_text())
    assert rep["blocks"]["fixture_checksums"]["mismatches"] == 0 and rep["blocks"]["release_verification"]["ok"]
    assert all(all(v["exact"] == v["n"] for v in c["release_vs_expected"].values()) for c in rep["cases"])
    for mode, b in rep["reader_and_in_chain"].items():
        assert all(not v["cand_columns_mismatching"] and v["keys_equal"] and all(not o["mismatching_columns"] for o in v["objs"].values()) for k, v in b.items() if k.startswith("V3_"))
        assert all(all(o["exact"] == o["n"] for o in v["outputs"].values()) for v in b["V4_in_chain"].values()) and all(v["joined_one_to_one"] for v in b["V5_identity"].values())
    assert all(not v["features_D_columns_not_exact"] and v["raw_features_unchanged"] and all(d["bits_equal"] == d["rows"] for d in v.values() if isinstance(d, dict) and "bits_equal" in d) for v in rep["sp_chain"].values())
