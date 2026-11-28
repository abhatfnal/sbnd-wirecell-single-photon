"""Deployment interface for the RELEASED upstream SBND Wire-Cell nu_e / nu_mu classifiers (Xuyang, `sbnd-wirecell-bdt/releases`; pinned in ``configs/upstream_release.yaml``).

What this module is: a versioned, NON-destructive score overlay.  It verifies the release, builds scores for candidate tables the CALLER hands in, and writes them as a separate
overlay keyed by the full candidate identity.  The original CAFs and analysis tables are never modified; a corrected copy of the nu_mu inputs is a scratch object that never reaches
the raw reconstruction features, the nu_e classifier or any data sample.

What it is NOT: it selects no model, no vertex mode and no threshold (the operating cuts of the release are recorded in the config as information only), and it refuses to run on any
registered sample unless ``evaluation_guard`` in the config has been filled by a named person (independent-evaluation policy).  Tests use synthetic tables only.

The scoring algorithm re-implements the release's own standalone scripts (``release/score_release.py`` for nu_e, ``training/numu/score_numu_release.py`` and
``make_corrected_tables.py --update-flag1`` for nu_mu) and is cross-checked against them bit for bit in ``tests/test_upstream_scores.py`` (when a clone of the release is available).
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

CONFIG_FILE = Path(__file__).resolve().parents[2] / "configs" / "upstream_release.yaml"
UPSTREAM_KEY = ["file_id", "run", "subrun", "event", "cand"]                       # identity of the release's own table builder (tables/build_tables.py)
EAF_KEY = ["file_index", "ev", "run", "subrun", "evt", "nu_index"]          # full verified candidate identity of the EAF analysis tables (c_nu_index -> nu_index)
CORR_COL = "_numu_dqdx_k"                                                   # present ONLY on corrected scratch copies: marks them and prevents double / wrong-sample use
TO_NUMU_SCORE = 2.0 / math.log(10.0)                                        # numu_score = TO_NUMU_SCORE * margin (0.868589)
STATUS = dict(scored=0, tagger_not_run=1, placeholder=2, input_nan=3)
NUE_NOT_RUN, CHAIN_NAN_FAIL = -15.0, -16.2556                               # chain sentinels of nue_score (release README)


class UpstreamError(RuntimeError):
    pass


class OverlayError(UpstreamError):
    pass


class AuthorizationError(UpstreamError):
    pass


def load_config(path: Path | None = None) -> dict:
    return yaml.safe_load(Path(path or CONFIG_FILE).read_text())


def sha256_file(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# ------------------------------------------------------------------------------------------------------------------------------------------------------------
# release verification
# ------------------------------------------------------------------------------------------------------------------------------------------------------------
def _manifest(releases: Path, cfg: dict, which: str) -> dict:
    return json.loads((releases / cfg["models"][which]["folder"] / "manifest.json").read_text())


def verify_release(releases, cfg: dict, head_commit: str | None = None, dirty: bool = False) -> dict:
    """Check a local copy of ``<clone>/releases`` against the pin. Returns {'ok', 'checks', 'files'}; never raises on a failed check (the caller decides)."""
    releases = Path(releases); checks, files = [], []

    def chk(name, ok, detail=""):
        checks.append(dict(check=name, ok=bool(ok), detail=str(detail)))

    if head_commit is not None:
        chk("clone HEAD == pinned commit", head_commit == cfg["release"]["pinned_commit"], head_commit)
        chk("releases/ has no uncommitted change", not dirty)
    nue_m, numu_m = _manifest(releases, cfg, "nue"), _manifest(releases, cfg, "numu")
    for which, man in (("nue", nue_m), ("numu", numu_m)):
        p = releases / cfg["models"][which]["folder"] / "manifest.json"
        chk(f"{which} manifest sha256 == pin", sha256_file(p) == cfg["models"][which]["manifest_sha256"], sha256_file(p))
    # ---- nu_e: chain-compatible A v2, main variant ----
    chk("nue manifest is nue_round4_ruleA_v2", nue_m["name"] == "nue_round4_ruleA_v2", nue_m["name"])
    chk("nue default variant is main", nue_m["default"]["variant"] == "main", nue_m["default"])
    chk("nue label rule A", nue_m["level1"]["label_rule"] == "A")
    chk("nue has the chain transform (v2: runs in the toolkit without missing values)", "chain_transform" in nue_m["level1"])
    chk("nue main L2: 258 inputs, nothing left out", len(nue_m["level2"]["main"]["inputs"]) == cfg["models"]["nue"]["n_l2_inputs"] and nue_m["level2"]["main"]["left_out"] == [], len(nue_m["level2"]["main"]["inputs"]))
    chk("nue 15 level-1 models", len(nue_m["level1"]["models"]) == cfg["models"]["nue"]["n_l1_models"])
    chk("nue informational cut == release value", abs(nue_m["operating_cut"] - cfg["models"]["nue"]["informational_operating_cut_nue_score"]) < 1e-12, nue_m["operating_cut"])
    chk("nue chain files: main variant has 16 files and declares 258 inputs", nue_m["wirecell"]["variants"]["main"]["n_files"] == 16 and nue_m["wirecell"]["variants"]["main"]["final_inputs_declared"] == 258)
    # ---- nu_mu: round 3af with the 1.071 correction ----
    chk("numu manifest is numu_round3af", numu_m["name"] == "numu_round3af", numu_m["name"])
    sc, cc = numu_m["simulation_correction"], cfg["simulation_correction"]
    chk("numu correction mode uniform, k == 1.071", sc["mode"] == "uniform" and sc["k"] == cc["k"], (sc["mode"], sc["k"]))
    chk("numu correction inputs == the seven documented dQ/dx inputs", list(sc["inputs"]) == list(cc["inputs"]))
    chk("numu muon-flag update on (3af, not 3a)", sc["update_flag1"] is True)
    chk("numu 74 L2 inputs; numu_cc_flag among them", len(numu_m["inputs"]) == cfg["models"]["numu"]["n_l2_inputs"] and "numu_cc_flag" in numu_m["inputs"])
    chk("numu informational cut == release value", abs(numu_m["operating_point"]["cut_numu_score"] - cfg["models"]["numu"]["informational_operating_cut_numu_score"]) < 1e-12)
    corr_json = releases / cfg["models"]["numu"]["folder"] / "correction.json"
    chk("correction.json sha256 == pin", sha256_file(corr_json) == cc["correction_json_sha256"])
    cj = json.loads(corr_json.read_text())
    chk("correction.json k == config k", cj.get("k") == cc["k"] and cj.get("mode") == "uniform", cj)
    # ---- every model file against its manifest hash ----
    def addfile(model, role, rel, sha):
        p = releases / rel; got = sha256_file(p) if p.exists() else ""
        files.append(dict(model=model, role=role, path=f"releases/{rel}", sha256_manifest=sha, sha256_found=got, ok=got == sha))
    for m, v in nue_m["level1"]["models"].items():
        addfile("nue", f"l1:{m}", f"{cfg['models']['nue']['folder']}/{v['file']}", v["sha256"])
    for var, v in nue_m["level2"].items():
        addfile("nue", f"l2:{var}", f"{cfg['models']['nue']['folder']}/{v['file']}", v["sha256"])
    for var, v in nue_m["wirecell"]["variants"].items():
        for fn, sha in v["sha256"].items():
            addfile("nue", f"chain:{var}", f"{cfg['models']['nue']['folder']}/{v['weights_dir']}/{fn}", sha)
    for m, v in numu_m["level1"]["models"].items():
        addfile("numu", f"l1:{m}", f"{cfg['models']['numu']['folder']}/{v['file']}", v["sha256"])
    for m, v in numu_m["models"].items():
        addfile("numu", f"l2:{m}", f"{cfg['models']['numu']['folder']}/{v['file']}", v["sha256"])
    for m, v in numu_m["wirecell"]["files"].items():
        addfile("numu", f"chain:{m}", f"{cfg['models']['numu']['folder']}/{v['file']}", v["sha256"])
    chk(f"all {len(files)} model files match their manifest sha256", all(f["ok"] for f in files), f"{sum(not f['ok'] for f in files)} mismatches")
    # ---- committed hash table agrees (so a later change to the clone is detected) ----
    tab = Path(cfg["release"]["file_hash_table"])
    tab = tab if tab.is_absolute() else CONFIG_FILE.parents[1] / tab
    if tab.exists():
        t = pd.read_csv(tab); got = {f["path"]: f["sha256_found"] for f in files}
        chk("clone files == committed release_file_hashes.csv", len(t) == len(files) and all(got.get(r.path) == r.sha256_manifest for r in t.itertuples()))
    return dict(ok=all(c["ok"] for c in checks), n_checks=len(checks), n_files=len(files), pinned_commit=cfg["release"]["pinned_commit"], head_commit=head_commit, checks=checks, files=files)


def required_inputs(releases, cfg: dict) -> pd.DataFrame:
    """Every CAF quantity the two classifiers read. ``caf_branch`` is a wc.T_tagger / wc.T_kine branch of ``recTreeWireCell``; per-object lists need the ``..idx`` / ``..length`` helpers."""
    releases = Path(releases); nue_m, numu_m = _manifest(releases, cfg, "nue"), _manifest(releases, cfg, "numu"); rows = []
    corr = set(cfg["simulation_correction"]["inputs"]) | {"numu_cc_flag", "numu_cc_flag_1"}

    def branch(n):
        return ("wc.T_kine." + n) if n.startswith("kine_") else ("wc.T_tagger." + n)

    def add(model, level, name, kind, note=""):
        rows.append(dict(model=model, level=level, name=name, kind=kind, caf_branch=branch(name), numu_sim_correction_target=name in corr, note=note))
    for n in nue_m["level2"]["main"]["inputs"]:
        if n.startswith("l1_"): continue
        add("nue", "L2", n, "candidate scalar")
    for m, v in nue_m["level1"]["models"].items():
        for n in v["inputs_per_object"]: add("nue", f"L1:{m}", n, "per-object list (+..idx/..length)")
        for n in v["inputs_per_candidate"]: add("nue", f"L1:{m}", n, "candidate scalar copied to every object")
        if v["pre_cut"]:
            for n in sorted(set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", v["pre_cut"])) - {"and", "or"}): add("nue", f"L1:{m}", n, "candidate scalar (pre-cut)", v["pre_cut"])
    for n in ("br_filled",): add("nue", "gate", n, "candidate scalar (the tagger ran)")
    for n in numu_m["inputs"]:
        if n in ("numu_1_score", "numu_2_score", "cosmict_10_score"): continue
        add("numu", "L2", n, "candidate scalar")
    for m, v in numu_m["level1"]["models"].items():
        for n in v["inputs"]: add("numu", f"L1:{m}", n, "per-object list (+..idx/..length)")
    for n in ("numu_cc_flag_1", "numu_cc_flag_2"): add("numu", "L1-flag", n, "per-object list (flag; used only by the correction)")
    for n in ("cosmict_2_filled", "cosmict_3_filled", "cosmict_7_filled"): add("numu", "correction", n, "candidate scalar")
    for n in ("nu_index", "nu_x", "nu_y", "nu_z", "neutrino_type"): add("both", "identity/placeholder", n, "candidate scalar", "placeholder rule: kine_reco_Enu==0 and neutrino_type==0 and vertex at origin")
    add("both", "identity/placeholder", "kine_reco_Enu", "candidate scalar")
    df = pd.DataFrame(rows).drop_duplicates(["model", "level", "name"]).reset_index(drop=True)
    return df


# ------------------------------------------------------------------------------------------------------------------------------------------------------------
# evaluation guard
# ------------------------------------------------------------------------------------------------------------------------------------------------------------
def require_authorization(sample: str, cfg: dict | None = None) -> str:
    """Scoring a REGISTERED sample (anything in configs/samples.yaml) needs either a designated non-evaluation fixture or a fully filled ``evaluation_guard``. Never auto-fills."""
    cfg = cfg or load_config(); g = cfg["evaluation_guard"]
    if sample in (cfg.get("fixtures") or []):
        return "fixture"
    need = ("approved_by", "approved_date", "frozen_model_bundle_sha256", "selection_manifest_sha256")
    if g.get("authorized") is True and all(str(g.get(k, "")).strip() for k in need):
        return "authorized"
    raise AuthorizationError(f"sample {sample!r}: scoring official / evaluation samples is blocked (independent-evaluation policy). evaluation_guard is not authorised "
                             f"(needs authorized: true and {', '.join(need)}); no designated fixture matches.")


# ------------------------------------------------------------------------------------------------------------------------------------------------------------
# nu_mu simulation correction (copies only)
# ------------------------------------------------------------------------------------------------------------------------------------------------------------
def _is_marked(df: pd.DataFrame) -> bool:
    return CORR_COL in df.columns


def apply_numu_sim_correction(cands: pd.DataFrame, objs_numu_1: pd.DataFrame, objs_numu_2: pd.DataFrame, cfg: dict, is_simulation: bool, key: list[str]):
    """Return (cands_c, objs_numu_1_c, report): corrected COPIES (originals untouched), exactly ``make_corrected_tables.py --update-flag1``:
    q -> k q on numu_cc_1_medium_dQ_dx (every numu_1 segment) and cosmict_{2,3,7}_dQ_dx_{end,front} (where cosmict_N_filled == 1), only finite values > 0; per numu_1 segment
    flag stays on only if corrected dQ/dx < numu_cc_1_dQ_dx_cut; numu_cc_flag = any flag_1 OR any numu_cc_2 flag OR numu_cc_flag_3 (only ever switched off).
    Refuses data, and refuses an already corrected frame (double correction)."""
    if not is_simulation:
        raise UpstreamError("the dQ/dx correction is simulation only: refusing to correct beam-on / beam-off data")
    if _is_marked(cands) or _is_marked(objs_numu_1):
        raise UpstreamError("input already carries the correction marker: refusing to correct twice")
    cc = cfg["simulation_correction"]; k = float(cc["k"]); inputs = cc["inputs"]
    c = cands.copy(); o1 = objs_numu_1.copy(); rep = {}

    def scale(s: pd.Series, mask: np.ndarray) -> pd.Series:
        q = s.to_numpy(np.float64); ok = mask & np.isfinite(q) & (q > 0); out = q.copy(); out[ok] = q[ok] * k
        return pd.Series(out.astype(s.dtype), index=s.index), int(ok.sum())
    o1["numu_cc_1_medium_dQ_dx"], n = scale(o1["numu_cc_1_medium_dQ_dx"], np.ones(len(o1), bool)); rep["numu_cc_1_medium_dQ_dx"] = n
    for name in inputs:
        if name == "numu_cc_1_medium_dQ_dx": continue
        filled = c[f"cosmict_{name.split('_')[1]}_filled"].to_numpy() == 1
        c[name], n = scale(c[name], filled); rep[name] = n
    fl = o1["flag"].to_numpy(np.float64); q = o1["numu_cc_1_medium_dQ_dx"].to_numpy(np.float64); cut = o1["numu_cc_1_dQ_dx_cut"].to_numpy(np.float64)
    newfl = np.where((fl == 1) & ~(q < cut), 0.0, fl); o1["flag"] = newfl.astype(objs_numu_1["flag"].dtype)
    g = pd.DataFrame({**{kk: o1[kk].to_numpy() for kk in key}, "old": fl == 1, "new": newfl == 1}).groupby(key)[["old", "new"]].any()
    off = g[g.old & ~g.new].reset_index()[key]
    a2 = objs_numu_2.assign(a2=objs_numu_2["flag"] == 1).groupby(key).a2.any().reset_index()
    m = c[key].merge(off.assign(_off=True), on=key, how="left").merge(a2, on=key, how="left")
    hit = m["_off"].fillna(False).to_numpy(bool) & ~m["a2"].fillna(False).to_numpy(bool) & (c["numu_cc_flag_3"].to_numpy() != 1)
    f0 = np.where(hit, 0.0, c["numu_cc_flag"].to_numpy(np.float64)); rep["numu_cc_flag_turned_off"] = int(((c["numu_cc_flag"].to_numpy() == 1) & (f0 != 1)).sum())
    rep["segments_flag1_turned_off"] = int(((fl == 1) & (newfl != 1)).sum()); c["numu_cc_flag"] = f0.astype(cands["numu_cc_flag"].dtype)
    c[CORR_COL] = k; o1[CORR_COL] = k
    return c, o1, rep


def _check_marker(cands, objs: dict, is_simulation: bool, cfg: dict, model: str):
    frames = [("cands", cands)] + [(f"objs_{n}", o) for n, o in objs.items()]
    if model == "nue":
        bad = [n for n, f in frames if _is_marked(f)]
        if bad: raise UpstreamError(f"nu_e inputs must never carry the nu_mu dQ/dx correction ({bad} are marked corrected)")
        return
    for n, f in frames:
        if n in ("cands", "objs_numu_1") and is_simulation:
            if not _is_marked(f) or not np.all(f[CORR_COL].to_numpy() == cfg["simulation_correction"]["k"]):
                raise UpstreamError(f"simulation nu_mu scoring needs the corrected copies (k = {cfg['simulation_correction']['k']}); {n} is not marked: score it through apply_numu_sim_correction")
        elif _is_marked(f) and not is_simulation:
            raise UpstreamError(f"data must never be corrected, but {n} carries the correction marker")


# ------------------------------------------------------------------------------------------------------------------------------------------------------------
# scoring (re-implementation of the release's standalone scripts)
# ------------------------------------------------------------------------------------------------------------------------------------------------------------
def _booster(path):
    import xgboost as xgb
    b = xgb.Booster(); b.load_model(str(path)); b.set_param({"nthread": 4}); return b


def _predict(b, X: np.ndarray, names: list[str], missing=np.nan) -> np.ndarray:
    import xgboost as xgb
    return b.predict(xgb.DMatrix(X.astype(np.float32), feature_names=names, missing=missing), output_margin=True)


def _l1_pooled(releases: Path, folder: str, model: str, md: dict, objs: pd.DataFrame, keep: pd.DataFrame, cands: pd.DataFrame, key: list[str], protect: dict | None = None) -> pd.Series:
    """Pooled raw margin per candidate (NaN where the candidate has no object / fails the pre-cut)."""
    O = objs.merge(keep[key], on=key, how="inner")
    for c in md.get("inputs_per_candidate", []) or []:
        if c not in O.columns: O = O.merge(cands[key + [c]], on=key, how="left")
    if len(O) == 0: return pd.Series(dtype=np.float64)
    X = O[md["inputs"]].copy()
    for col, (kind, v) in (protect or {}).items():
        x = X[col].to_numpy(float); X[col] = np.where(np.isinf(x) if kind == "inf" else np.isnan(x), v, x)
    O = O.assign(_p=_predict(_booster(releases / folder / md["file"]), X.to_numpy(np.float32), md["inputs"]))
    return O.groupby(key, sort=False)["_p"].agg(md.get("pool", "min"))


def score_nue(releases, cfg: dict, cands: pd.DataFrame, objs: dict, key: list[str]) -> pd.DataFrame:
    """nu_e A v2 (main chain variant). ``cands``: key + the 243 non-L1 L2 inputs + br_filled + is_placeholder + pio_filled/pio_flag_pio; ``objs[model]``: key + that model's per-object inputs.
    Returns one row per input candidate: raw pooled L1 margins (up_nue_margin_l1_*), chain-stored L1 values (up_nue_l1_*), the final raw margin ``up_nue_score`` and ``up_nue_status``."""
    releases = Path(releases); _check_marker(cands, objs, False, cfg, "nue"); man = _manifest(releases, cfg, "nue"); folder = cfg["models"]["nue"]["folder"]
    l2m = man["level2"][cfg["models"]["nue"]["variant"]]; T = man["level1"]["chain_transform"]["models"]
    if cands[key].duplicated().any(): raise OverlayError("duplicate candidate identities in the nu_e input table")
    C = cands.copy(); run = (C["is_placeholder"] == 0) & (C["br_filled"] == 1); Cs = C[run]
    out = C[key].copy(); status = np.where(C["is_placeholder"] == 1, STATUS["placeholder"], np.where(C["br_filled"] != 1, STATUS["tagger_not_run"], STATUS["scored"]))
    for m, md in man["level1"]["models"].items():
        keep = Cs[Cs.eval(md["pre_cut"]).to_numpy(bool)] if md["pre_cut"] else Cs
        pooled = _l1_pooled(releases, folder, m, md, objs[m], keep, Cs, key)
        col = md["level2_input_name"]; Cs = Cs.merge(pooled.rename(col).reset_index(), on=key, how="left") if len(pooled) else Cs.assign(**{col: np.nan})
        x = Cs[col].to_numpy(np.float64); t = T[m]
        Cs["margin_" + col] = x; Cs[col] = np.where(np.isnan(x), np.float32(t["empty_value"]), np.tanh(t["scale"] * x + t["offset"]).astype(np.float32)).astype(np.float32)
    names = l2m["inputs"]; nan_in = np.isnan(Cs[names].to_numpy(np.float32)).sum(1)
    Cs["up_nue_score"] = _predict(_booster(releases / folder / l2m["file"]), Cs[names].to_numpy(np.float32), names)
    for m, md in man["level1"]["models"].items():
        col = md["level2_input_name"]; Cs["up_nue_l1_" + m] = Cs[col]; Cs["up_nue_margin_l1_" + m] = Cs["margin_" + col]
    keep_cols = key + ["up_nue_score"] + [f"up_nue_l1_{m}" for m in man["level1"]["models"]] + [f"up_nue_margin_l1_{m}" for m in man["level1"]["models"]]
    Cs = Cs[keep_cols].assign(up_nue_n_nan_inputs=nan_in.astype(np.int16))
    res = out.merge(Cs, on=key, how="left"); res["up_nue_status"] = status.astype(np.int8)
    res.loc[(res["up_nue_status"] == STATUS["scored"]) & (res["up_nue_n_nan_inputs"] > 0), "up_nue_status"] = STATUS["input_nan"]
    return res


def score_numu(releases, cfg: dict, cands: pd.DataFrame, objs: dict, key: list[str], is_simulation: bool) -> pd.DataFrame:
    """nu_mu round 3af. For simulation the inputs must be the corrected copies from ``apply_numu_sim_correction``; for data they must be raw. ``objs``: numu_1, numu_2, cosmict_10."""
    releases = Path(releases); _check_marker(cands, objs, is_simulation, cfg, "numu"); man = _manifest(releases, cfg, "numu"); folder = cfg["models"]["numu"]["folder"]
    if cands[key].duplicated().any(): raise OverlayError("duplicate candidate identities in the nu_mu input table")
    names = man["inputs"]; C = cands[cands["is_placeholder"] == 0].copy()
    for n in man["nan_to_0"]: C[n] = C[n].fillna(0.0)
    for m, t in man["level1"]["models"].items():
        pooled = _l1_pooled(releases, folder, m, dict(t, pool=t["pool"], inputs_per_candidate=[]), objs[m], C, C, key, protect={c: tuple(v) for c, v in t["protect"].items()})
        x = C[key].merge(pooled.rename("margin").reset_index(), on=key, how="left")["margin"].to_numpy(np.float64) if len(pooled) else np.full(len(C), np.nan)
        v = np.where(np.isnan(x), np.float32(t["empty_value"]), np.tanh(t["scale"] * x + t["offset"]).astype(np.float32)).astype(np.float32)
        C["up_numu_l1_" + m] = v; C[m + "_score"] = v
    margin = _predict(_booster(releases / folder / man["models"]["d6_f0"]["file"]), C[names].to_numpy(np.float32), names, missing=np.nan)
    R = C[key].assign(up_numu_margin=margin, up_numu_score=margin * TO_NUMU_SCORE, **{"up_" + m + "_score": C["up_numu_l1_" + m].to_numpy() for m in man["level1"]["models"]})
    res = cands[key].merge(R, on=key, how="left"); res["up_numu_status"] = np.where(cands["is_placeholder"].to_numpy() == 1, STATUS["placeholder"], STATUS["scored"]).astype(np.int8)
    return res


# ------------------------------------------------------------------------------------------------------------------------------------------------------------
# overlay: assembly, sentinels, provenance, join
# ------------------------------------------------------------------------------------------------------------------------------------------------------------
def to_chain_convention(ov: pd.DataFrame) -> pd.DataFrame:
    """The score in the Wire-Cell chain's own sentinel convention (nue: -15 = tagger not run, -16.2556 = a declared input was NaN); NaN for placeholders. For comparison with stored scores only."""
    o = pd.DataFrame(index=ov.index)
    o["nue_score_chain"] = np.select([ov["up_nue_status"] == STATUS["tagger_not_run"], ov["up_nue_status"] == STATUS["input_nan"], ov["up_nue_status"] == STATUS["placeholder"]], [NUE_NOT_RUN, CHAIN_NAN_FAIL, np.nan], ov["up_nue_score"])
    return o


def make_overlay(nue: pd.DataFrame, numu: pd.DataFrame, key: list[str], provenance: dict) -> pd.DataFrame:
    for n, d in (("nue", nue), ("numu", numu)):
        if d[key].duplicated().any(): raise OverlayError(f"{n} scores have duplicate identities")
    if len(nue) != len(numu) or not nue[key].equals(numu[key]):
        m = nue[key].merge(numu[key], on=key, how="outer", indicator=True)
        raise OverlayError(f"nu_e and nu_mu scored different candidate sets ({(m['_merge'] != 'both').sum()} differ)")
    ov = nue.merge(numu, on=key, how="inner", validate="one_to_one"); ov.attrs["provenance"] = provenance
    return ov


def provenance_record(cfg: dict, sample: str, production: str, is_simulation: bool, n_input_candidates: int, authorization: str, extra: dict | None = None, tree: str = "recTreeWireCell") -> dict:
    import xgboost
    if tree != cfg["applicability"].get(production, {}).get("tree", tree):
        raise UpstreamError(f"{production}: the released models apply to tree {cfg['applicability'][production]['tree']!r}, not {tree!r}")
    return dict(overlay_schema=1, sample=sample, production=production, wc_tree=tree, is_simulation=bool(is_simulation), n_input_candidates=int(n_input_candidates), authorization=authorization,
                release_repo=cfg["release"]["repo"], release_commit=cfg["release"]["pinned_commit"], nue_manifest_sha256=cfg["models"]["nue"]["manifest_sha256"], numu_manifest_sha256=cfg["models"]["numu"]["manifest_sha256"],
                nue_model=f"{cfg['models']['nue']['folder']}/{cfg['models']['nue']['variant']}", numu_model=cfg["models"]["numu"]["folder"],
                numu_sim_dqdx_k_applied=cfg["simulation_correction"]["k"] if is_simulation else None, nue_inputs_corrected=False, data_corrected=False,
                xgboost_version=xgboost.__version__, config_sha256=sha256_file(CONFIG_FILE), status_codes=STATUS, **(extra or {}))


def write_overlay(ov: pd.DataFrame, path) -> Path:
    path = Path(path); prov = dict(ov.attrs.get("provenance") or {})
    if not prov: raise OverlayError("an overlay without provenance may not be written")
    if path.exists(): raise OverlayError(f"{path} exists: overlays are versioned and never overwritten")
    ov.to_parquet(path, index=False); prov["overlay_sha256"] = sha256_file(path); prov["n_rows"] = int(len(ov))
    Path(str(path) + ".provenance.json").write_text(json.dumps(prov, indent=1, default=str) + "\n"); return path


def join_overlay(identity: pd.DataFrame, overlay: pd.DataFrame, key: list[str], check: dict[str, str] | None = None, rtol: float = 0.0) -> pd.DataFrame:
    """Left-join an overlay onto a candidate table 1:1 on the FULL identity. Raises on duplicates, missing rows, extra rows, or an identity-check column (e.g. shower energy / vertex copied
    from the CAF at scoring time) that differs: the overlay can never be attached to a different candidate."""
    if identity[key].duplicated().any(): raise OverlayError("duplicate identities in the candidate table")
    if overlay[key].duplicated().any(): raise OverlayError("duplicate identities in the overlay")
    m = identity[key].merge(overlay[key], on=key, how="outer", indicator=True); miss, extra = int((m["_merge"] == "left_only").sum()), int((m["_merge"] == "right_only").sum())
    if miss or extra: raise OverlayError(f"overlay does not match the candidate table: {miss} candidates without a score row, {extra} score rows without a candidate")
    out = identity.merge(overlay, on=key, how="left", validate="one_to_one", suffixes=("", "_ov"))
    for ca, ob in (check or {}).items():
        a, b = out[ca].to_numpy(np.float64), out[ob].to_numpy(np.float64)
        if not np.allclose(a, b, rtol=rtol, atol=0.0, equal_nan=True): raise OverlayError(f"identity check failed: {ca} != {ob} on {int((~np.isclose(a, b, rtol=rtol, atol=0.0, equal_nan=True)).sum())} rows")
    return out


def apply_to_sp_inputs(frame: pd.DataFrame, overlay_joined: pd.DataFrame, sp_name: str, cfg: dict, on_unscored: str = "error") -> pd.DataFrame:
    """Copy of the single-photon BDT input frame with ONLY the upstream-classifier outputs replaced (mapping ``sp_downstream_dependencies``); every raw reconstruction feature is asserted bit-identical."""
    mp = cfg["sp_downstream_dependencies"][sp_name]; raw = [c for c in cfg["sp_downstream_dependencies"]["raw_features_that_must_stay_raw"] if c in frame.columns]
    st_col = "up_nue_status" if any(v.startswith("up_nue") for v in mp.values()) else "up_numu_status"
    if mp and on_unscored == "error" and (overlay_joined[st_col].to_numpy() != STATUS["scored"]).any():
        raise OverlayError(f"{sp_name}: {(overlay_joined[st_col].to_numpy() != STATUS['scored']).sum()} candidates have no upstream score ({st_col} != scored); decide the convention for them explicitly (on_unscored='keep_flagged')")
    out = frame.copy(); ok = overlay_joined[st_col].to_numpy() == STATUS["scored"] if mp else np.ones(len(frame), bool); out["upstream_replaced"] = ok
    for sp_col, up_col in mp.items():
        if sp_col not in frame.columns: raise OverlayError(f"{sp_name}: input {sp_col!r} not in the frame")
        out.loc[ok, sp_col] = overlay_joined.loc[ok, up_col].to_numpy()
    for c in raw:
        if not np.array_equal(out[c].to_numpy(), frame[c].to_numpy(), equal_nan=True): raise UpstreamError(f"raw feature {c} was modified")
    return out


def validate_frozen_bundle(b: dict, cfg: dict | None = None) -> list[str]:
    """Structural check of a filled ``configs/frozen_bundle_manifest.template.yaml``. Returns the list of problems (empty = acceptable). Does not evaluate anything."""
    cfg = cfg or load_config(); bad = []; hexre = re.compile(r"^[0-9a-f]{64}$")
    def need(path, v):
        if v in ("", None, [], {}): bad.append(f"{path} is empty")
    for k in ("frozen_utc", "frozen_by"): need(k, b.get(k))
    for k in ("repo", "commit"): need(f"code.{k}", (b.get("code") or {}).get(k))
    u = b.get("upstream_release") or {}
    if u.get("commit") != cfg["release"]["pinned_commit"]: bad.append("upstream_release.commit != the pinned release")
    for w in ("nue", "numu"):
        if (u.get(w) or {}).get("manifest_sha256") != cfg["models"][w]["manifest_sha256"]: bad.append(f"upstream_release.{w}.manifest_sha256 != pin")
    if (u.get("nue") or {}).get("variant") != cfg["models"]["nue"]["variant"]: bad.append("nue variant != main (chain-compatible A v2)")
    if u.get("sim_dqdx_k") != cfg["simulation_correction"]["k"]: bad.append("sim_dqdx_k != 1.071")
    pr = b.get("production") or {}
    for k in ("name", "wct", "wc_tree", "vertex_configuration", "effective_boundary_treatment", "upstream_applicability_statement"): need(f"production.{k}", pr.get(k))
    if pr.get("wc_tree") and pr.get("wc_tree") != "recTreeWireCell": bad.append("production.wc_tree is not recTreeWireCell: the released models are verified for that tree only")
    sp = b.get("sp_models") or []
    if len(sp) != 4: bad.append(f"expected 4 SP models (numu, other, ncpi0, nue), got {len(sp)}")
    allowed = {f"{k}_sp": set((cfg["sp_downstream_dependencies"].get(f"{k}_sp") or {}).values()) for k in ("numu", "other", "ncpi0", "nue")}
    for m in sp:
        for k in ("name", "file", "inputs_file", "score_definition", "sentinel_policy", "xgboost_version"): need(f"sp_models[{m.get('name')}].{k}", m.get(k))
        for k in ("sha256", "inputs_sha256"):
            if not hexre.match(str(m.get(k, ""))): bad.append(f"sp_models[{m.get('name')}].{k} is not a sha256")
        if not m.get("frozen_thresholds"): bad.append(f"sp_models[{m.get('name')}].frozen_thresholds empty")
        unk = set((m.get("upstream_score_inputs") or {}).values()) - set().union(*allowed.values()) if allowed else set()
        if unk: bad.append(f"sp_models[{m.get('name')}] uses unknown overlay columns {sorted(unk)}")
        raw = set(m.get("raw_features_used") or []) & set(cfg["simulation_correction"]["inputs"])
        if raw and not m.get("raw_features_used"): bad.append("raw features missing")
    sm = b.get("selection_manifest") or {}
    for k in ("file", "candidate_policy", "fiducial_volume", "signal_definition", "topology_definition"): need(f"selection_manifest.{k}", sm.get(k))
    if not hexre.match(str(sm.get("sha256", ""))): bad.append("selection_manifest.sha256 is not a sha256")
    tm = b.get("training_membership") or {}
    need("training_membership.manifests", tm.get("manifests")); need("training_membership.split_rule", tm.get("split_rule")); need("training_membership.beam_off_half_used_for_training", tm.get("beam_off_half_used_for_training"))
    if (b.get("validation") or {}).get("no_official_sample_used") is not True: bad.append("validation.no_official_sample_used must be true")
    return bad


def file_map_from_manifest(urls: list[str], rule: str = "dirname") -> pd.DataFrame:
    """file_id (as the release table builder writes it: ``--file-id-from dirname`` = the unit folder name, ``basename`` = the file name) -> our manifest ``file_index``. Must be 1:1."""
    ids = [(u.rstrip("/").split("/")[-2] if rule == "dirname" else u.rstrip("/").split("/")[-1]) for u in urls]
    m = pd.DataFrame(dict(file_id=ids, file_index=np.arange(len(urls))))
    if m.file_id.duplicated().any(): raise OverlayError(f"file_id rule {rule!r} is not unique over the manifest ({int(m.file_id.duplicated().sum())} duplicates): choose the other rule")
    return m


def translate_identity(df: pd.DataFrame, events: pd.DataFrame, file_map: pd.DataFrame) -> pd.DataFrame:
    """Upstream-builder identity (file_id, run, subrun, event, cand) -> EAF identity (file_index, ev, run, subrun, evt, nu_index) by joining our events table 1:1; raises on any unmapped file,
    event not found, or ambiguous event (so a score row can only ever attach to the candidate it was computed for)."""
    m = df.merge(file_map, on="file_id", how="left", validate="many_to_one")
    if m.file_index.isna().any(): raise OverlayError(f"{int(m.file_index.isna().sum())} rows have a file_id that is not in the manifest")
    ev = events[["file_index", "ev", "run", "subrun", "evt"]]
    if ev.duplicated(["file_index", "run", "subrun", "evt"]).any(): raise OverlayError("(file_index, run, subrun, evt) is not unique in our events table")
    m["file_index"] = m.file_index.astype(ev.file_index.dtype)
    out = m.merge(ev, left_on=["file_index", "run", "subrun", "event"], right_on=["file_index", "run", "subrun", "evt"], how="left", validate="many_to_one")
    if out.ev.isna().any(): raise OverlayError(f"{int(out.ev.isna().sum())} scored candidates belong to events that are not in our events table")
    out = out.rename(columns={"cand": "nu_index"}).drop(columns=["file_id", "event"])
    return out[EAF_KEY + [c for c in out.columns if c not in EAF_KEY]]


def carry_identity_checks(ov: pd.DataFrame, cands: pd.DataFrame, key: list[str], cols: dict[str, str]) -> pd.DataFrame:
    """Copy reconstruction quantities that exist in BOTH our tables and the builder's candidate table (e.g. kine_reco_Enu, shw_sp_energy) into the overlay as ``id_<name>``, for ``join_overlay(check=...)``."""
    return ov.merge(cands[key + list(cols.values())].rename(columns={v: "id_" + v for v in cols.values()}), on=key, how="left", validate="one_to_one")
