#!/usr/bin/env python
"""V3-V5 closure of the common toolkit-equivalent upstream scorer (`wc_upstream_chain` 1.0.0, vendored in third_party/) on the AUTHORISED Aurora development fixture `upstream_r4_dev_fixture_v1`.
Development fixture only: it never touches an official sample, and the 16 DEV_DO_NOT_DEPLOY SP boosters are used ONLY to reproduce the fixture's recorded predictions.

    source env/setup_eaf.sh
    python scripts/upstream_fixture_closure.py --fixture $SP_DATA/aurora_fixtures/upstream_r4_dev_fixture_v1 --releases <clone>/releases --builder <clone>/tables/build_tables.py \
           --shipped <wire-cell-data dir holding uboone/weights (99c6497f)> [--part mc|beamoff_restricted|all] [--out tables/upstream_release/fixture_closure_report.json]

All comparisons are exact float32 BIT PATTERNS (no tolerance anywhere). The report holds counts and maxima only (no event-level record) and is safe to commit.
"""
import argparse, hashlib, json, os, platform, subprocess, sys, tempfile
from pathlib import Path
import numpy as np, pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "third_party" / "wc_upstream_chain_bundle")); sys.path.insert(0, str(REPO / "src"))
import wc_upstream_chain as wuc
from wc_upstream_chain import spec as S
from sbnd_single_photon import upstream_scores as US

OUTS = list(S.UPSTREAM_OUTPUTS)


def bits(x):
    return np.ascontiguousarray(np.asarray(x, dtype=np.float64).astype(np.float32)).view(np.uint32)


def cmp_bits(a, b):
    a, b = bits(a), bits(b); return dict(n=int(len(a)), exact=int((a == b).sum()), max_abs_diff=float(np.max(np.abs(a.view(np.float32).astype(np.float64) - b.view(np.float32).astype(np.float64))) if len(a) else 0.0))


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def eqcol(a, b):
    a, b = np.asarray(a), np.asarray(b)
    return bool(a.shape == b.shape and (np.array_equal(a.astype(np.float64), b.astype(np.float64), equal_nan=True) if a.dtype.kind in 'fiub' and b.dtype.kind in 'fiub' else (a == b).all()))


def read_objs(d, pattern="objs_{model}.parquet"):
    return {m: pd.read_parquet(os.path.join(d, pattern.format(model=m))) for m in S.L1_ALL if os.path.exists(os.path.join(d, pattern.format(model=m)))}


def versions():
    import pyarrow, numpy, pandas
    try: import xgboost; xv = xgboost.__version__
    except Exception: xv = None
    return dict(python=platform.python_version(), numpy=numpy.__version__, pandas=pandas.__version__, pyarrow=pyarrow.__version__, xgboost=xv, platform=platform.platform(), bundle=wuc.__version__)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--fixture", required=True); ap.add_argument("--releases", required=True); ap.add_argument("--builder", required=True); ap.add_argument("--shipped", required=True)
    ap.add_argument("--part", default="all", choices=["all", "mc", "beamoff_restricted"]); ap.add_argument("--out", default=str(REPO / "tables/upstream_release/fixture_closure_report.json")); ap.add_argument("--skip-reader", action="store_true"); a = ap.parse_args()
    fx = Path(a.fixture); man = json.loads((fx / "FIXTURE_MANIFEST.json").read_text()); cfg = US.load_config(); rep = dict(fixture=man["name"], versions=versions(), blocks={})
    # ---- 0. fixture integrity, registration, disjointness from official names ----
    bad = [l for l in (fx / "SHA256SUMS").read_text().splitlines() if l.strip() and sha(fx / l.split(None, 1)[1].strip()) != l.split()[0]]
    rep["blocks"]["fixture_checksums"] = dict(files=len((fx / "SHA256SUMS").read_text().splitlines()), mismatches=len(bad))
    rep["blocks"]["fixture_registered_in_config"] = man["name"] in (cfg.get("fixtures") or [])
    rep["blocks"]["bundle_fingerprint"] = wuc.chain.__dict__ and json.loads(subprocess.run([sys.executable, "-m", "wc_upstream_chain", "bundle-fingerprint"], capture_output=True, text=True, env=dict(os.environ, PYTHONPATH=str(REPO / "third_party/wc_upstream_chain_bundle"))).stdout)["bundle_fingerprint"]
    rep["blocks"]["release_verification"] = {k: v for k, v in wuc.verify_release(a.releases, cfg["release"]["pinned_commit"]).items() if k in ("ok", "n_canonical_files", "n_auxiliary_files", "inventory_fingerprint")}
    rel_dirs = [os.path.join(a.releases, "nue_round4_ruleA_v2/wirecell/main"), os.path.join(a.releases, "numu_round3af/wirecell"), a.shipped]
    route, fps = wuc.inventory.identify_route(":".join(rel_dirs)); rep["blocks"]["weights_route"] = dict(route=route, fingerprints=fps)
    inv = json.loads((REPO / "third_party/wc_upstream_chain_bundle/wc_upstream_chain/data/shipped_inventory.json").read_text())["files"]
    nm = {k: v for k, v in inv.items() if k in ("numu_1", "numu_2", "numu_3", "cosmict_10", "numu_final")}; have = {k: (sha(Path(a.shipped) / "uboone/weights" / v["file"]) == v["sha256"]) if (Path(a.shipped) / "uboone/weights" / v["file"]).exists() else None for k, v in nm.items()}
    rep["blocks"]["shipped_numu_files_match_shipped_inventory"] = have; assert all(v for v in have.values()), have
    release = wuc.UpstreamChain(rel_dirs); shp_numu = wuc.UpstreamChain([a.shipped], nue=False, sim_dqdx_scale=1.0)   # shipped weights ran UNPATCHED: k = 1.0 on simulation (CONVENTIONS section 9)
    try: shp_nue = wuc.UpstreamChain([a.shipped], numu=False, sim_dqdx_scale=1.0); shp_nue_err = None
    except Exception as e: shp_nue, shp_nue_err = None, type(e).__name__ + ": " + str(e).split(" not found along")[0]
    rep["blocks"]["shipped_nue_final_available"] = shp_nue is not None; rep["blocks"]["shipped_nue_final_error"] = shp_nue_err
    # ---- 1. scoring closure, per case ----
    cases = []; scored = {}
    for case in man["cases"]:
        if a.part != "all" and case["part"] != a.part: continue
        d = fx / case["dir"]
        if not d.is_dir(): cases.append(dict(case=case["dir"], absent=True)); continue
        C = pd.read_parquet(d / "cands.parquet"); O = read_objs(str(d)); E = pd.read_parquet(d / "expected_upstream.parquet"); key = case["key"]; kind = case["kind"]
        assert C[key].equals(E[key]), "candidate order differs from the expected table"
        before = C.copy(deep=True); r = release.score(C, O, kind=kind, key=key); scored[case["dir"]] = (r, C, O, E, case)
        c = dict(case=case["dir"], kind=kind, candidates=int(len(C)), raw_inputs_unchanged=bool(C.equals(before)))
        c["release_vs_expected"] = {o: cmp_bits(r[o], E["chain_release_" + o]) for o in OUTS}
        c["diag_vs_expected"] = {k: bool(np.array_equal(np.asarray(r[k]), np.asarray(E[k]), equal_nan=True)) for k in [x for x in E.columns if x.startswith("diag_") and x in r.columns]}
        if kind == "mc":                                                       # MC no-scale diagnostic (what an UNPATCHED chain with the released weights would store)
            rn = release.score(C, O, kind="mc", key=key, apply_sim_correction=False); c["noscale_vs_expected"] = {o: cmp_bits(rn[o], E["chain_release_noscale_" + o]) for o in S.NUMU_SCORES}
        sn = shp_numu.score(C, O, kind=kind, key=key, stored_l1=True); c["shipped_closure_numu"] = {k: cmp_bits(sn["numu_score"], E[k]) for k in ("ship_numu_score", "stored_numu_score")}
        if shp_nue is not None:
            ss = shp_nue.score(C, O, kind=kind, key=key, stored_l1=True); c["shipped_closure_nue"] = {k: cmp_bits(ss["nue_score"], E[k]) for k in ("ship_nue_score", "stored_nue_score")}
        else: c["shipped_closure_nue"] = "BLOCKED: shipped XGB_nue_seed2_0923.xml (the 199 MB shipped nu_e final model) is not in wire-cell-data@99c6497f and not on EAF"
        # the release's standalone xgboost values vs the chain-equivalent values (reported, never used)
        x = {o: E["official_xgb_" + o] for o in OUTS if "official_xgb_" + o in E.columns}
        dd = {o: np.abs(np.asarray(r[o], float) - np.asarray(v, float)) for o, v in x.items()}
        c["standalone_xgboost_vs_chain"] = {o: dict(n_bit_differ=int((bits(r[o]) != bits(v)).sum()), n_abs_diff_gt_1e5=int((np.nan_to_num(dd[o]) > 1e-5).sum()), n_abs_diff_gt_1e2=int((np.nan_to_num(dd[o]) > 1e-2).sum()), max_abs_diff=float(np.nanmax(dd[o]))) for o, v in x.items()}
        c["ok_release_and_numu_shipped"] = bool(all(v["exact"] == v["n"] for v in c["release_vs_expected"].values()) and all(c["diag_vs_expected"].values()) and all(v["exact"] == v["n"] for v in c["shipped_closure_numu"].values())
                                                and (kind != "mc" or all(v["exact"] == v["n"] for v in c["noscale_vs_expected"].values())) and c["raw_inputs_unchanged"])
        c["tags"] = {t: int(E.fixture_tags.fillna("").str.contains(t).sum()) for t in ("br_filled_0", "placeholder", "some_list_empty", "pio2_objects_gate_passes", "in_chain_unit", "nue_final_nan_input", "numu_flag_switched_off")}
        cases.append(c)
    rep["cases"] = cases
    # ---- 3/4. reader equivalence + genuine in-chain stored scores, on the 18 CAF units (pinned release builder, both trees) ----
    if not a.skip_reader and a.part in ("all", "mc"):
        units = pd.read_csv(fx / "mc/caf/units.tsv", sep="\t"); idm = pd.read_parquet(fx / "mc/caf/identity_map.parquet"); gen = pd.read_parquet(fx / "mc/caf/expected_released_chain_scores.parquet"); V = {}
        for tree, mode in (("recTreeWireCell", "dv2_split_move"), ("recTreeWireCell_dv2snap", "dv2_snap")):
            blk = dict(tree=tree); allr = []
            for sample in ("ncdr", "bnb", "nuecc"):
                u = units[units["sample"] == sample]
                if u.empty: continue
                tag = f"wcl1116-aurora-{sample}"; outs = {}
                for kind_dir in ("production", "released_chain"):
                    files = [str(fx / "mc/caf" / r.unit / kind_dir / r.file_id) for r in u.itertuples()]; td = tempfile.mkdtemp(prefix="bt_")
                    code = f"import sys; sys.path.insert(0, {str(Path(a.builder).parent)!r}); import build_tables as bt; bt.WC = {tree!r}; sys.argv = ['build_tables', {tag!r}, {td!r}, '--objs', '--file-id-from', 'basename', '--files'] + {files!r}; bt.main()"
                    p = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True); assert p.returncode == 0, p.stderr[-800:]
                    outs[kind_dir] = (pd.read_parquet(f"{td}/cands_{tag}.parquet"), read_objs(td, f"objs_{{model}}_{tag}.parquet"))
                (Cp, Op), (Cr, Or) = outs["production"], outs["released_chain"]; key = ["sample", "file_id", "run", "subrun", "event", "cand"]
                # V3: reader == fixture inputs for the in-chain candidates
                case = scored.get(f"mc/cases/{tag}/{mode}")
                if case:
                    _, Cf, Of, Ef, _ = case; sel = Cf.fixture_tags.fillna("").str.contains("in_chain_unit") if "fixture_tags" in Cf.columns else Ef.fixture_tags.fillna("").str.contains("in_chain_unit")
                    Cfs = Cf[sel.to_numpy()].sort_values(key).reset_index(drop=True); Cps = Cp[Cp.file_id.isin(Cfs.file_id.unique())].sort_values(key).reset_index(drop=True)
                    cols = [c for c in Cfs.columns if c in Cps.columns and c != "fixture_tags"]; same_keys = Cfs[key].equals(Cps[key])
                    mism = [c for c in cols if not eqcol(Cfs[c].to_numpy(), Cps[c].to_numpy())] if same_keys else ["KEYS_DIFFER"]
                    ob = {}
                    for m, Ofx in Of.items():
                        fk = Ofx[Ofx.file_id.isin(Cfs.file_id.unique())].sort_values(key + ["index"]).reset_index(drop=True); bk = Op[m][Op[m].file_id.isin(Cfs.file_id.unique())].sort_values(key + ["index"]).reset_index(drop=True) if m in Op else pd.DataFrame()
                        ocols = [c for c in fk.columns if c in bk.columns]; ob[m] = dict(rows_fixture=int(len(fk)), rows_reader=int(len(bk)), mismatching_columns=[c for c in ocols if len(fk) == len(bk) and not eqcol(fk[c].to_numpy(), bk[c].to_numpy())] if len(fk) == len(bk) else ["ROWCOUNT"])
                    blk[f"V3_{sample}"] = dict(candidates_fixture=int(len(Cfs)), candidates_reader=int(len(Cps)), keys_equal=same_keys, cand_columns_compared=len(cols), cand_columns_mismatching=mism[:10], objs=ob)
                # V4: genuine patched in-chain stored values (released_chain CAFs) == bundle scores computed from the PRODUCTION CAF inputs, all 20 outputs, every candidate
                sc = release.score(Cp, Op, kind="mc", key=key); J = sc.merge(Cr[key + OUTS], on=key, suffixes=("", "_chain"), validate="one_to_one"); blk.setdefault("V4_in_chain", {})[sample] = dict(candidates=int(len(J)), outputs={o: cmp_bits(J[o], J[o + "_chain"]) for o in OUTS})
                # shipped route: production CAF stored (shipped) scores vs shipped numu closure with stored level-1 values
                sh = shp_numu.score(Cp, Op, kind="mc", key=key, stored_l1=True); blk.setdefault("V4_shipped_numu", {})[sample] = cmp_bits(sh["numu_score"], Cp.set_index(key).loc[sh.set_index(key).index, "numu_score"].to_numpy())
                allr.append(Cp[key].assign(tree=tree))
                # V5 identity: map to the EAF key through identity_map, 1:1, overlay set == candidate set (every candidate scored, placeholders included), raw features preserved
                im = idm[(idm.tree == tree) & idm.file_id.isin(u.file_id)]; ev = im[["file_id", "entry", "run", "subrun", "event"]].drop_duplicates().rename(columns={"entry": "ev", "event": "evt"}); fm = pd.DataFrame(dict(file_id=sorted(u.file_id), file_index=range(len(u))))
                ov = sc.copy(); ev["file_index"] = ev.file_id.map(dict(zip(fm.file_id, fm.file_index))); T = US.translate_identity(ov.drop(columns=[c for c in ("sample",) if c in ov.columns]), ev[["file_index", "ev", "run", "subrun", "evt"]], fm)
                cand_eaf = US.translate_identity(Cp[["file_id", "run", "subrun", "event", "cand"]], ev[["file_index", "ev", "run", "subrun", "evt"]], fm)
                J2 = US.join_overlay(cand_eaf, T[US.EAF_KEY + ["numu_score", "nue_score"]], US.EAF_KEY)
                pos = im[["file_id", "run", "subrun", "event", "cand", "position"]]; blk.setdefault("V5_identity", {})[sample] = dict(candidates=int(len(cand_eaf)), overlay_rows=int(len(T)), joined_one_to_one=bool(len(J2) == len(cand_eaf)), nu_index_equals_vector_position=bool((pos.cand == pos.position).all()),
                                                                                                                                  placeholders_scored=int(Cp.eval("kine_reco_Enu == 0 and neutrino_type == 0 and nu_x == 0 and nu_y == 0 and nu_z == 0").sum()) if {"neutrino_type", "nu_x"} <= set(Cp.columns) else None)
            V[mode] = blk
        rep["reader_and_in_chain"] = V
        # compare against the fixture's own expected_released_chain_scores table too (same 128 candidates per tree)
        rep["expected_released_chain_scores_rows"] = int(len(gen))
    # ---- 5b. SP features and predictions with the DEV_DO_NOT_DEPLOY boosters (reproduction only) ----
    sp = {}
    try:
        import xgboost as xgb
        fl = json.loads((fx / "mc/models/sp_feature_lists.json").read_text())
        for dirn, (r, C, O, E, case) in scored.items():
            d = fx / case["dir"]; key = case["key"]; mode = d.name; A = pd.read_parquet(d / "sp_features_A.parquet"); D = pd.read_parquet(d / "sp_features_D.parquet"); P = pd.read_parquet(d / "sp_predictions.parquet"); res = {}
            ki = A.set_index(key).index; ri = r.set_index(key).index; res["sp_rows_missing_from_overlay"] = int((~ki.isin(ri)).sum()); res["sp_rows"] = int(len(A)); res["overlay_candidates"] = int(len(r))
            Dn = wuc.sp.replace_upstream_inputs(A, r[ri.isin(ki).tolist()], key, "D")        # the SP frame is the preselected SUBSET (placeholders dropped); every SP row must exist in the all-candidate overlay (checked above)
            res["features_D_rebuilt_exact"] = {c: bool(np.array_equal(Dn[c].to_numpy(), D[c].to_numpy(), equal_nan=True)) for c in A.columns if c not in key}
            res["features_D_columns_not_exact"] = [c for c, ok in res["features_D_rebuilt_exact"].items() if not ok]; res.pop("features_D_rebuilt_exact")
            res["raw_features_unchanged"] = bool(all(np.array_equal(Dn[c].to_numpy(), A[c].to_numpy(), equal_nan=True) for c in S.RAW_MUST_STAY_RAW if c in A.columns))
            for m in ("numu", "other", "ncpi0", "nue"):
                names = fl[m]; mp = (fx / "mc/models" / f"DEV_DO_NOT_DEPLOY_{m}_{mode}_dev")
                for dev, feats, col, fin in (("A", A, f"{m}_devA_on_A", f"{m}_finite_inputs_A"), ("D", Dn, f"{m}_devD_on_D", f"{m}_finite_inputs_D")):
                    b = xgb.Booster(); b.load_model(str(mp) + dev + ".json"); X = feats[names].to_numpy(np.float32); finite = np.isfinite(X).all(1)
                    pred = np.where(finite, b.predict(xgb.DMatrix(X, feature_names=names), output_margin=True), -np.inf); Pm = P.set_index(key).loc[feats.set_index(key).index]
                    res[col] = dict(rows=int(len(pred)), finite_flag_equal=bool(np.array_equal(finite, Pm[fin].to_numpy().astype(bool))), bits_equal=int((bits(np.where(np.isfinite(pred), pred, 0)) == bits(np.where(np.isfinite(Pm[col].to_numpy()), Pm[col].to_numpy(), 0))).sum()),
                                    nonfinite_pattern_equal=bool(np.array_equal(~np.isfinite(pred), ~np.isfinite(Pm[col].to_numpy()))))
            try:                                                     # extra, tolerance-reported cross-check of the INHERITED MicroBooNE SP XML models (domain A), via our independent frozen scorer
                from sbnd_single_photon import bdt as LB
                M = LB.load_models(); lx = {}
                for m in ("numu", "nue"):
                    v = M[m].decision(A[M[m].var_names].to_numpy(np.float64)); fin = np.isfinite(v)
                    with np.errstate(all="ignore"): lo = np.log10((1 + v) / (1 - v))
                    lx[m] = dict(rows=int(fin.sum()), max_abs_diff=float(np.max(np.abs(lo[fin] - P[f"{m}_legacy_xml_on_A"].to_numpy()[fin]))), bits_equal=int((bits(lo[fin]) == bits(P[f"{m}_legacy_xml_on_A"].to_numpy()[fin])).sum()))
                res["legacy_xml_cross_check_numu_nue"] = lx
            except Exception as e:
                res["legacy_xml_cross_check_numu_nue"] = repr(e)[:120]
            sp[dirn] = res
    except Exception as e:
        sp["error"] = repr(e)[:300]
    rep["sp_chain"] = sp
    Path(a.out).write_text(json.dumps(rep, indent=1, default=str) + "\n"); print("wrote", a.out)
    ok = all(c.get("ok_release_and_numu_shipped", True) for c in cases)
    print("scoring closure ok (release 20 outputs + numu shipped closure + diag + raw preserved):", ok); sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
