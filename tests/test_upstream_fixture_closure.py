"""V3-V5 closure on an AUTHORISED Aurora development fixture package (never official evaluation events). Skipped until the package is delivered:

    export SP_UPSTREAM_FIXTURE_DIR=/path/to/fixture_package  [SP_UPSTREAM_CLONE=/path/to/sbnd-wirecell-bdt]

Package contents (to be produced by Aurora; formats fixed here so both sides test the same thing):
  fixture_manifest.yaml : name, role (development|dev|fit|nested_validation), files [CAF file names], aurora_commit, scorer_pin {commit, sha256}, release_commit (== configs/upstream_release.yaml),
                          production (nov16), tree (recTreeWireCell), is_simulation, sha256 of every other file in the package
  cands_<tag>.parquet, objs_<model>_<tag>.parquet (18) : output of the PINNED release builder (tables/build_tables.py --objs --file-id-from dirname)
  events.parquet (file_index, ev, run, subrun, evt) and manifest_urls.txt : for the identity translation
  expected_scores.parquet : upstream identity + the toolkit reference values: up_nue_score, up_nue_l1_*, up_numu_margin, up_numu_score, up_numu_{1,2}_score, up_cosmict_10_score (+ optional in_chain_* columns
                            holding the GENUINE in-chain stored values where the fixture CAFs were produced by the released-model chain, and shipped_* columns holding the stored shipped scores)
  expected_features.parquet (optional) : SP input frames and SP BDT predictions / cut decisions per SP model
The numerical reference is the actual toolkit (in_chain_* where present, else Aurora's toolkit-equivalent expected values), not the standalone xgboost scorer.
"""
import json, os
from pathlib import Path

import numpy as np, pandas as pd, pytest, yaml

from sbnd_single_photon import upstream_scores as US

FX = os.environ.get("SP_UPSTREAM_FIXTURE_DIR"); REPO = Path(__file__).resolve().parents[1]; CFG = US.load_config()
pytestmark = pytest.mark.skipif(not FX or not (Path(FX) / "fixture_manifest.yaml").exists(), reason="no authorised Aurora development fixture package delivered (SP_UPSTREAM_FIXTURE_DIR)")


def _official_names():
    import importlib.util
    sp = importlib.util.spec_from_file_location("ma", REPO / "scripts/upstream_membership_audit.py"); ma = importlib.util.module_from_spec(sp); sp.loader.exec_module(ma)
    return {n for p in ("old_fg1", "nov16") for s in ma.SAMPLES for n in (u.rstrip("/").split("/")[-1] for u in ma.urls(p, s))}


def test_fixture_is_registered_development_only_and_pinned():
    d = Path(FX); m = yaml.safe_load((d / "fixture_manifest.yaml").read_text())
    assert US.validate_fixture_manifest(m["files"], _official_names(), m["role"]) == []
    assert m["release_commit"] == CFG["release"]["pinned_commit"] and m["production"] == "nov16" and m["tree"] == "recTreeWireCell"
    for f, h in m.get("sha256", {}).items(): assert US.sha256_file(d / f) == h, f


def test_V3_V5_closure():
    d = Path(FX); m = yaml.safe_load((d / "fixture_manifest.yaml").read_text()); tag = m.get("tag", "fixture"); rel = Path(os.environ.get("SP_UPSTREAM_CLONE", "")) / "releases"
    assert US.verify_release(rel, CFG)["ok"]
    cands = pd.read_parquet(d / f"cands_{tag}.parquet"); exp = pd.read_parquet(d / "expected_scores.parquet")
    nue_m, numu_m = US._manifest(rel, CFG, "nue"), US._manifest(rel, CFG, "numu")
    nue_o = {k: pd.read_parquet(d / f"objs_{k}_{tag}.parquet") for k in nue_m["level1"]["models"]}; numu_o = {k: pd.read_parquet(d / f"objs_{k}_{tag}.parquet") for k in numu_m["level1"]["models"]}
    sim = bool(m["is_simulation"]); key = US.UPSTREAM_KEY; before = cands.copy(deep=True)
    nue = US.score_nue(rel, CFG, cands, nue_o, key)                                     # nominal backend: fails loudly if the toolkit-equivalent scorer is not yet registered
    c, o1, _ = US.apply_numu_sim_correction(cands, numu_o["numu_1"], numu_o["numu_2"], CFG, True, key) if sim else (cands, numu_o["numu_1"], None)
    numu = US.score_numu(rel, CFG, c, dict(numu_o, numu_1=o1), key, sim)
    pd.testing.assert_frame_equal(cands, before)                                         # raw CAF-derived inputs preserved bit for bit
    ov = nue.merge(numu, on=key, validate="one_to_one")
    cols = [x for x in exp.columns if x.startswith("up_") and x in ov.columns]; assert cols
    rep = US.closure_report(exp, ov, key, cols); assert rep["exact"], rep                # exact agreement with the expected (toolkit) values
    for ic in [x for x in exp.columns if x.startswith("in_chain_")]:                     # genuine in-chain scores, wherever the fixture CAFs contain them
        up = "up_" + ic[len("in_chain_"):]; r = US.closure_report(exp, ov, key, [up]) if up in exp else None
        assert (ov.set_index(key).loc[exp.set_index(key).index, up].to_numpy() == exp.set_index(key)[ic].to_numpy()).all(), ic
    st = ov.set_index(key)
    assert (st.loc[cands.set_index(key).index[cands.is_placeholder == 1], "up_nue_status"] == US.STATUS["placeholder"]).all()           # placeholder handling
    assert (st.loc[cands.set_index(key).index[(cands.br_filled != 1) & (cands.is_placeholder == 0)], "up_nue_status"] == US.STATUS["tagger_not_run"]).all()   # br_filled
    assert (st["up_nue_n_nan_inputs"][st.up_nue_status == US.STATUS["scored"]] == 0).all()                                               # NaN sentinels explicit
    for mname, md in nue_m["level1"]["models"].items():                                  # empty-object constants: candidates without objects get the model's constant exactly
        n_obj = nue_o[mname].groupby(key).size().reindex(cands.set_index(key).index).fillna(0).to_numpy(); ok = (cands.br_filled.to_numpy() == 1) & (cands.is_placeholder.to_numpy() == 0) & (n_obj == 0)
        if md["pre_cut"] is None and ok.any(): assert (st.loc[cands.set_index(key).index[ok], f"up_nue_l1_{mname}"].to_numpy() == np.float32(nue_m["level1"]["chain_transform"]["models"][mname]["empty_value"])).all(), mname
    if (d / "expected_features.parquet").exists(): pytest.skip("SP feature / prediction closure: wire the delivered SP models here (bundle manifest required)")
