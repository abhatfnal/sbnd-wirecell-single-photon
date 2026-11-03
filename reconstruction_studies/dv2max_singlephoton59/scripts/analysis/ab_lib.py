#!/usr/bin/env python3
"""
ab_lib.py -- COPY of main_vertex_swap_ab59_20261014/scripts/ab_analysis/ab_lib.py for the
DV2-MAX x single-photon 59-event test (dv2max_singlephoton59_20261102).  Changes vs the original:
  * S -> the DV2 work area (all writes guarded inside it)
  * arm_dv2(ARM, RUNSET) for ARM O (vertex_method=original) / ARM D (dv2_split_move)
  * parse_container_log accepts the DV2O / DV2D wrapper prefixes
  * parse_lar_log also collects the DV2-MAX placement / fallback / failure lines
Original header follows.

ab_lib.py -- readers / parsers for the main_vertex_swap_apply A/B
(OFF = frozen ab59 Fix2-v2 arm, ON = main_vertex_swap_apply=true arm).

Everything here is READ-ONLY on its inputs.  The only writes are:
  * the per-event extraction cache under <workdir>/cache/
  * the redirected MicroBooNE BDT scorer outputs under <workdir>/scorer_<label>/
Both are inside the study area S (asserted in run_all.py before anything is written).
"""
import os, re, io, json, glob, zipfile, hashlib, pickle, math, csv, contextlib
from collections import defaultdict
import numpy as np
import uproot

# ---------------------------------------------------------------------------
# Fixed paths
# ---------------------------------------------------------------------------
BASE = "/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon"
S = f"{BASE}/development/dv2max_singlephoton59_20261102"
SWAP_S = f"{BASE}/development/main_vertex_swap_ab59_20261014"   # read-only: the swap-ON arm (diagnostic)
AB59 = f"{BASE}/development/fix2_vertex_shower_onehop_20261005/ab59"
SCORER_PY = f"{BASE}/analysis/microboone_1gamma_v0/score_microboone_bdts.py"
GEN_BDT_PY = f"{AB59}/tables/generate_bdt_comparison.py"
TRUTH_CSV = f"{BASE}/baseline_v0/ncdelta_50evt/tables/ncdelta_truth.csv"
FROZEN_EVT_CSV = f"{AB59}/tables/fix2_ab59_event_comparison.csv"
FROZEN_BDT_CSV = f"{AB59}/tables/fix2_ab59_bdt_comparison.csv"
FROZEN_CUTFLOW_CSV = f"{AB59}/tables/fix2_ab59_cutflow.csv"
COMPILED_OFF = f"{S}/config/compiled/frozen.json"
COMPILED_ON = f"{S}/config/compiled/armD.json"
EXPECTED_MD5 = "9cff76d0d81a4b6c45a88908e78e73e4"
N_EVENTS = 59
BDT_MODELS = ["numu", "other", "ncpi0", "nue"]


def arm_off():
    return dict(
        label="OFF", fmt="AB59",
        wc_dir=f"{AB59}/wirecell",
        lar_log=f"{AB59}/logs/lar_ab59_evt_{{idx:04d}}.log",
        cont_log=f"{AB59}/logs/container_ab59_{{idx:04d}}.log",
        batch_glob=f"{AB59}/logs/*.OU",
        compiled_cfg=COMPILED_OFF,
    )


def arm_on():
    return dict(
        label="ON", fmt="SWAPON",
        wc_dir=f"{SWAP_S}/wirecell",
        lar_log=f"{SWAP_S}/logs/lar_swapon_evt_{{idx:04d}}.log",
        cont_log=f"{SWAP_S}/logs/container_swapon_{{idx:04d}}.log",
        batch_glob=f"{SWAP_S}/logs/*.OU",
        compiled_cfg=COMPILED_ON,
    )


def arm_dv2(arm, runset="main"):
    """ARM O (vertex_method=original) or ARM D (vertex_method=dv2_split_move) of this study."""
    assert arm in ("O", "D") and runset in ("main", "smoke")
    R = f"{S}/runs/{runset}/arm{arm}"
    G = f"{S}/logs/{runset}/arm{arm}"
    return dict(label=arm, fmt=f"DV2{arm}", wc_dir=f"{R}/wirecell",
                lar_log=f"{G}/lar_evt_{{idx:04d}}.log", cont_log=f"{G}/container_evt_{{idx:04d}}.log",
                batch_glob=f"{S}/logs/pbs/*.OU",
                compiled_cfg=f"{S}/config/compiled/arm{arm}.json")


def arm_offrerun(label):
    """knob-OFF determinism rerun: same binary/config as ab59, new output area."""
    C = f"{S}/control_off_rerun"
    return dict(
        label=label, fmt="OFFRERUN",
        wc_dir=f"{C}/wirecell",
        lar_log=f"{C}/logs/lar_offrerun_evt_{{idx:04d}}.log",
        cont_log=f"{C}/logs/container_offrerun_{{idx:04d}}.log",
        batch_glob=f"{C}/logs/*.OU",
        compiled_cfg=COMPILED_OFF,
    )


def arm_on_selftest():
    """ON := OFF (self-test).  Every input path points at the frozen ab59 arm."""
    a = arm_off()
    a["label"] = "ON"
    return a


BASELINE_V0 = f"{BASE}/baseline_v0/ncdelta_50evt"


def arm_baseline_negcontrol():
    """ON := baseline_v0 (pre-Fix2 library, same config): a KNOWN-DIFFERENT arm used only as a
    negative control of the difference-detection machinery.  Its logs have no fix2_v2/fix2_diag lines."""
    return dict(
        label="ON", fmt="BASELINE",
        wc_dir=f"{BASELINE_V0}/wirecell",
        lar_log=f"{BASELINE_V0}/logs/lar_wct_evt_{{idx:04d}}.log",
        cont_log=f"{BASELINE_V0}/logs/container_wct_evt_{{idx:04d}}.log",
        batch_glob=f"{BASELINE_V0}/logs/__no_batch_logs__*.OU",
        compiled_cfg=COMPILED_OFF,
    )


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def _sha1(b):
    return hashlib.sha1(b).hexdigest()


def _file_sig(path):
    try:
        st = os.stat(path)
        return (path, st.st_size, st.st_mtime_ns)
    except FileNotFoundError:
        return (path, None, None)


def to_py(v):
    """numpy -> plain python (for JSON)."""
    if isinstance(v, np.ndarray):
        return [to_py(x) for x in v.tolist()]
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        f = float(v)
        return f if math.isfinite(f) else str(f)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if isinstance(v, float) and not math.isfinite(v):
        return str(v)
    if isinstance(v, dict):
        return {str(k): to_py(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [to_py(x) for x in v]
    return v


def fmt_scalar(x):
    """Shortest exact representation of a numpy/python scalar."""
    if x is None:
        return ""
    if isinstance(x, (bool, np.bool_)):
        return "True" if x else "False"
    if isinstance(x, (np.floating,)):
        return str(x)            # numpy shortest round-trip repr for its own dtype
    if isinstance(x, float):
        return repr(x)
    if isinstance(x, (np.integer, int)):
        return str(int(x))
    return str(x)


def summarize_value(v, nhead=6):
    if v is None:
        return "ABSENT"
    if isinstance(v, np.ndarray):
        n = len(v)
        head = ",".join(fmt_scalar(x) for x in v[:nhead])
        more = ",..." if n > nhead else ""
        return f"len={n}[{head}{more}]#{_sha1(np.ascontiguousarray(v).tobytes())[:8]}"
    return fmt_scalar(v)


def compare_values(a, b):
    """Return (equal, max_abs_diff, note).  Integers: exact.  Floats: exact first
    (NaN==NaN treated as equal), then max abs diff.  Vectors: length then elementwise."""
    if a is None and b is None:
        return True, "", "absent_both"
    if a is None:
        return False, "", "absent_off"
    if b is None:
        return False, "", "absent_on"
    is_vec = isinstance(a, np.ndarray) or isinstance(b, np.ndarray)
    aa = np.atleast_1d(np.asarray(a))
    bb = np.atleast_1d(np.asarray(b))
    if aa.shape != bb.shape:
        return False, "", f"length_change {aa.size}->{bb.size}"
    if aa.size == 0:
        return True, 0.0 if is_vec else "", ""
    isf = aa.dtype.kind == "f" or bb.dtype.kind == "f"

    def perm_note(eq):
        # a differing vector whose sorted contents are identical -> element order changed only
        if is_vec and not eq and aa.dtype.kind != "O" and bb.dtype.kind != "O":
            if np.array_equal(np.sort(aa), np.sort(bb), equal_nan=isf):
                return "permutation_only"
        return ""
    if isf:
        eq = bool(np.array_equal(aa, bb, equal_nan=True))
        a64 = aa.astype(np.float64)
        b64 = bb.astype(np.float64)
        na, nb = np.isnan(a64), np.isnan(b64)
        if np.any(na != nb):
            return False, "inf", perm_note(False) or "nan_mismatch"
        m = ~na
        if not np.any(m):
            return eq, 0.0, ""
        with np.errstate(invalid="ignore", over="ignore"):
            d = np.abs(a64[m] - b64[m])
        d = d[np.isfinite(d)] if np.any(np.isfinite(d)) else d
        mad = float(np.max(d)) if d.size else 0.0
        if not eq and mad == 0.0:
            # e.g. +inf vs -inf
            return False, "inf", "inf_mismatch"
        return eq, mad, perm_note(eq)
    if aa.dtype.kind in "iub" and bb.dtype.kind in "iub":
        eq = bool(np.array_equal(aa, bb))
        mad = int(np.max(np.abs(aa.astype(np.int64) - bb.astype(np.int64))))
        return eq, mad, perm_note(eq)
    # object / strings
    eq = [summarize_value(x) for x in aa.tolist()] == [summarize_value(x) for x in bb.tolist()]
    return eq, "", ""


# ---------------------------------------------------------------------------
# ROOT reader
# ---------------------------------------------------------------------------
def _branch_digest(arr):
    h = hashlib.sha1()
    if arr.dtype == object:
        for e in arr:
            if isinstance(e, np.ndarray):
                if e.dtype == object:
                    for ee in e:
                        h.update(repr(to_py(ee)).encode())
                else:
                    h.update(str(e.dtype).encode()); h.update(np.ascontiguousarray(e).tobytes())
            else:
                h.update(repr(to_py(e)).encode())
            h.update(b"|")
    else:
        h.update(str(arr.dtype).encode()); h.update(np.ascontiguousarray(arr).tobytes())
    return h.hexdigest()


def _tree_rows(t):
    """All branches of a TTree -> list (one per entry) of {branch: value}."""
    arrs = t.arrays(library="np")
    n = t.num_entries
    rows = []
    for e in range(n):
        rows.append({b: arrs[b][e] for b in arrs})
    types = {b: t[b].typename for b in t.keys()}
    return rows, types


def read_root(path):
    out = {"path": path, "exists": os.path.isfile(path), "ok": False, "error": "",
           "trees": {}, "T_tagger_rows": None, "T_tagger_types": {},
           "T_kine_rows": None, "T_kine_types": {}, "T_cluster": None, "T_bundle": None,
           "rse": (None, None, None), "tree_digests": {}}
    if not out["exists"]:
        out["error"] = "missing"
        return out
    try:
        with uproot.open(path) as f:
            cls = f.classnames(cycle=False)
            trees = sorted(k for k, c in cls.items() if c == "TTree")
            for tn in trees:
                out["trees"][tn] = int(f[tn].num_entries)
            if "T_tagger" in trees:
                out["T_tagger_rows"], out["T_tagger_types"] = _tree_rows(f["T_tagger"])
            if "T_kine" in trees:
                out["T_kine_rows"], out["T_kine_types"] = _tree_rows(f["T_kine"])
            if "T_cluster" in trees:
                out["T_cluster"] = f["T_cluster"].arrays(library="np")
            if "T_bundle" in trees:
                out["T_bundle"] = f["T_bundle"].arrays(library="np")
            if "Trun" in trees:
                tr = f["Trun"].arrays(["runNo", "subRunNo", "eventNo"], library="np")
                out["rse"] = (int(tr["runNo"][0]), int(tr["subRunNo"][0]), int(tr["eventNo"][0]))
            for tn in trees:
                if tn in ("T_tagger", "T_kine"):
                    continue
                t = f[tn]
                dg = {}
                for b in t.keys():
                    try:
                        dg[b] = _branch_digest(t[b].array(library="np"))
                    except Exception as e:  # pragma: no cover
                        dg[b] = f"unreadable:{type(e).__name__}"
                out["tree_digests"][tn] = dg
        out["ok"] = True
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"
    return out


# ---------------------------------------------------------------------------
# mabc.zip reader (duplicate filenames -> iterate infolist() in order)
# ---------------------------------------------------------------------------
def read_mabc(path):
    out = {"path": path, "exists": os.path.isfile(path), "ok": False, "error": "",
           "entries": [], "testzip_bad": None, "n_vertices_entries": 0,
           "vertices": None, "nu_vertices": []}
    if not out["exists"]:
        out["error"] = "missing"
        return out
    try:
        with zipfile.ZipFile(path) as z:
            infos = z.infolist()
            out["entries"] = [zi.filename for zi in infos]
            out["testzip_bad"] = z.testzip()
            vs = [zi for zi in infos if zi.filename.endswith("-vertices-global.json")]
            out["n_vertices_entries"] = len(vs)
            if vs:
                d = json.loads(z.open(vs[-1]).read())
                n = len(d["x"])
                verts = [dict(x=float(d["x"][j]), y=float(d["y"][j]), z=float(d["z"][j]),
                              q=float(d["q"][j]), cluster_id=int(d["cluster_id"][j]),
                              code=int(d["real_cluster_id"][j])) for j in range(n)]
                out["vertices"] = verts
                out["nu_vertices"] = [v for v in verts if v["q"] == 15000]
        out["ok"] = out["testzip_bad"] is None
        if out["testzip_bad"] is not None:
            out["error"] = f"testzip bad member {out['testzip_bad']}"
    except Exception as e:
        out["error"] = f"{type(e).__name__}: {e}"
    return out


# ---------------------------------------------------------------------------
# lar log parser
# ---------------------------------------------------------------------------
RE_TS = re.compile(r"^\[\d{2}:\d{2}:\d{2}\.\d+\]\s?")
RE_CFG_START = re.compile(r'configuring component: "([^"]*)":"([^"]*)"')
RE_CFG_END = re.compile(r'configured component:\s+"([^"]*)":"([^"]*)"')
RE_MVSA = re.compile(r"mvsa: traditional path swapped main cluster (-?\d+) -> (-?\d+) \((applied|discarded)\)")
RE_SEL = re.compile(r"TaggerCheckNeutrino: selected main cluster (-?\d+) \(t0 ([-\d.eE+]+) us, L ([-\d.eE+]+) cm")
RE_ROW = re.compile(r"\[nu_per_bundle\] ROW (\d+) gid (-?\d+) cluster (-?\d+) vertex \(([^,]+), ([^,]+), ([^)]+)\) cm Enu (\S+) acts (\d+)")
RE_DEG = re.compile(r"fix2_v2: main_vtx_deg=(\d+) map_size=(\d+) all_showers=(\d+) n_direct=(\d+)")
RE_DIR = re.compile(r"fix2_v2: direct shw E=([-\d.]+)MeV pdg=(-?\d+)")
RE_DHU = re.compile(r"fix2_v2: direct_has_usable=(true|false)")
RE_NB = re.compile(r"fix2_v2: neighbor shw E=([-\d.]+)MeV pdg=(-?\d+) edge_is_shw=(true|false) v1_idx=(-?\d+)")
RE_FB = re.compile(r"fix2_v2: fallback n_edges=(\d+) n_neighbor_new=(\d+) total_candidates=(\d+)")
RE_MAXE = re.compile(r"fix2_diag: MAXE_SHW E=([-\d.]+)MeV pdg=(-?\d+) vtx_type=(-?\d+) sv_idx=(-?\d+) "
                     r"sv_pos=\(([-\d.]+),([-\d.]+),([-\d.]+)\)cm dist_to_mv=([-\d.]+)cm "
                     r"shw_cl=(-?\d+) main_cl=(-?\d+) same_cl=(\w+) sv_in_map=(\w+) in_candidates=(\w+)")
RE_SAME = re.compile(r"fix2_diag: MAXE_SHW same vertex as main_vertex")
RE_BFS = re.compile(r"fix2_diag: BFS_FOUND hops=(\d+) path_vtx_count=(\d+)")
RE_HOP = re.compile(r"fix2_diag:\s+hop(\d+): vtx(\d+)->vtx(\d+) seg_idx=(-?\d+) is_shw=(\w+) len=([-\d.]+)cm seg_in_candidate_start=(\w+)")
RE_NOPATH = re.compile(r"fix2_diag: BFS_NO_PATH main_vtx=(-?\d+) diag_sv=(-?\d+)")
RE_ART = re.compile(r"Art has completed and will exit with status (-?\d+)")
RE_CRASH = re.compile(r"segmentation|segfault|fatal|exception|core dumped|terminate called", re.I)
# --- DV2-MAX lines (PR 543: NeutrinoVertexFinder.cxx / TaggerCheckNeutrino.cxx)
_F = r"(-?[\d.]+(?:e[-+]?\d+)?|nan|-?inf)"
RE_DV2_CFG = re.compile(r"TaggerCheckNeutrino: vertex_method (\S+), DV2-MAX bundle (\S+), module (\S+)")
RE_DV2_PRED = re.compile(r"DV2 prediction \(" + _F + r", " + _F + r", " + _F + r"\) cm, P\(<1cm\)=" + _F)
RE_DV2_PLACE = re.compile(r"vertex_method (dv2_\w+): main vertex = (split|graph vertex) at \(" + _F + r", " + _F + r", " + _F +
                          r"\) cm, " + _F + r" cm from the DV2-MAX point \(" + _F + r", " + _F + r", " + _F +
                          r"\) cm, P\(<1cm\) " + _F + r", cluster (-?\d+), nearest graph vertex " + _F + r" cm")
RE_DV2_MOVE = re.compile(r"vertex_method dv2_split_move: main vertex moved " + _F + r" cm onto the DV2-MAX point \(" + _F +
                         r", " + _F + r", " + _F + r"\) cm, (\d+) segment\(s\) re-routed, " + _F +
                         r" cm from it after the refit, cluster (\S+)")
RE_DV2_NOPRED = re.compile(r"vertex_method (\S+): no DV2-MAX prediction for this call \((\d+) cloud points")
RE_DV2_DECLINE = re.compile(r"dv2_place_main_vertex: cluster (\S+) UpdateInfo declined")
RE_DV2_BRKDECL = re.compile(r"DV2 break_segment declined, using the nearest vertex \(" + _F + r" cm\)")
RE_DL_FAILED = re.compile(r"determine_overall_main_vertex_DL: DL vertex failed: (.*)$")
RE_DV2_PAYLOAD = re.compile(r"unexpected DV2 payload size (\d+)")
RE_DV2_PYERR = re.compile(r"^DV2_Vertex: (\w+): (.*)\(no DV2-MAX vertex for this call\)")
RE_A5 = re.compile(r"A5 hadronic retype: shower id=(-?\d+) start_seg len=([-\d.]+)cm -> pdg (-?\d+) \(growth=([-\d.]+) bragg=([-\d.]+)\)")
RE_DUAL_SKIP = re.compile(r"dual_chain: OFF pass skipped for cluster (-?\d+) -- vertex_method")
RE_DUAL_OFF = re.compile(r"dual_chain: OFF pass \((\w+)\) vertex=(\w+)")


def _new_group():
    return {"selected_main": None, "mvsa": [], "dv2": [], "fix2": {
        "deg": None, "direct": [], "direct_has_usable": None, "neighbor": [], "fallback": None,
        "maxe": None, "same_vertex": False, "bfs": None, "hops": [], "nopath": None, "raw": []}}


def parse_lar_log(path):
    out = {"path": path, "exists": os.path.isfile(path), "n_lines": 0, "art_status": None,
           "mvsa": [], "groups": [], "rows": [], "crash_lines": [], "cfg_blocks": [],
           "orphan_fix2": False, "dv2": [], "dv2_cfg": None, "dual_off": [], "dual_skip": [], "a5": []}
    if not out["exists"]:
        return out
    groups = []
    cur = None
    cfg_cur = None
    with open(path, errors="replace") as fh:
        for raw in fh:
            out["n_lines"] += 1
            line = raw.rstrip("\n")
            norm = RE_TS.sub("", line).rstrip()
            # --- crash keywords (every line, including configuration blocks)
            if RE_CRASH.search(line):
                out["crash_lines"].append(norm[:300])
            # --- DV2 configure() INFO line (logged INSIDE the configuration block)
            m = RE_DV2_CFG.search(line)
            if m:
                out["dv2_cfg"] = dict(method=m.group(1), bundle=m.group(2), module=m.group(3))
            # --- configuration blocks
            m = RE_CFG_START.search(line)
            if m and "configuring component:" in line:
                cfg_cur = {"type": m.group(1), "name": m.group(2), "lines": [norm]}
                continue
            if cfg_cur is not None:
                m = RE_CFG_END.search(line)
                if m:
                    cfg_cur["lines"].append(norm)
                    cfg_cur["closed_ok"] = (m.group(1), m.group(2)) == (cfg_cur["type"], cfg_cur["name"])
                    out["cfg_blocks"].append(cfg_cur)
                    cfg_cur = None
                else:
                    cfg_cur["lines"].append(norm)
                continue
            m = RE_ART.search(line)
            if m:
                out["art_status"] = int(m.group(1))
                continue
            m = RE_SEL.search(line)
            if m:
                cur = _new_group()
                cur["selected_main"] = int(m.group(1))
                groups.append(cur)
                continue
            m = RE_MVSA.search(line)
            if m:
                d = {"A": int(m.group(1)), "B": int(m.group(2)), "mode": m.group(3), "raw": norm}
                out["mvsa"].append(d)
                if cur is None:
                    cur = _new_group(); groups.append(cur)
                cur["mvsa"].append(d)
                continue
            if "fix2_v2:" in line or "fix2_diag:" in line:
                if cur is None:
                    cur = _new_group(); groups.append(cur); out["orphan_fix2"] = True
                fx = cur["fix2"]
                fx["raw"].append(norm)
                m = RE_DEG.search(line)
                if m:
                    fx["deg"] = dict(main_vtx_deg=int(m.group(1)), map_size=int(m.group(2)),
                                     all_showers=int(m.group(3)), n_direct=int(m.group(4)))
                    continue
                m = RE_DIR.search(line)
                if m:
                    fx["direct"].append(dict(E=float(m.group(1)), pdg=int(m.group(2))))
                    continue
                m = RE_DHU.search(line)
                if m:
                    fx["direct_has_usable"] = m.group(1) == "true"
                    continue
                m = RE_NB.search(line)
                if m:
                    fx["neighbor"].append(dict(E=float(m.group(1)), pdg=int(m.group(2)),
                                               edge_is_shw=m.group(3) == "true", v1_idx=int(m.group(4))))
                    continue
                m = RE_FB.search(line)
                if m:
                    fx["fallback"] = dict(n_edges=int(m.group(1)), n_neighbor_new=int(m.group(2)),
                                          total_candidates=int(m.group(3)))
                    continue
                m = RE_MAXE.search(line)
                if m:
                    fx["maxe"] = dict(E=float(m.group(1)), pdg=int(m.group(2)), vtx_type=int(m.group(3)),
                                      sv_idx=int(m.group(4)),
                                      sv_pos=(float(m.group(5)), float(m.group(6)), float(m.group(7))),
                                      dist_to_mv=float(m.group(8)), shw_cl=int(m.group(9)),
                                      main_cl=int(m.group(10)), same_cl=m.group(11),
                                      sv_in_map=m.group(12), in_candidates=m.group(13))
                    continue
                if RE_SAME.search(line):
                    fx["same_vertex"] = True
                    continue
                m = RE_BFS.search(line)
                if m:
                    fx["bfs"] = dict(hops=int(m.group(1)), path_vtx_count=int(m.group(2)))
                    continue
                m = RE_HOP.search(line)
                if m:
                    fx["hops"].append(dict(k=int(m.group(1)), vA=int(m.group(2)), vB=int(m.group(3)),
                                           seg_idx=int(m.group(4)), is_shw=m.group(5), len=float(m.group(6)),
                                           seg_in_candidate_start=m.group(7)))
                    continue
                m = RE_NOPATH.search(line)
                if m:
                    fx["nopath"] = dict(main_vtx=int(m.group(1)), diag_sv=int(m.group(2)))
                    continue
                continue
            # --- DV2-MAX lines (event-level list + attached to the current candidate group)
            m = RE_DV2_CFG.search(line)
            if m:
                out["dv2_cfg"] = dict(method=m.group(1), bundle=m.group(2), module=m.group(3))
                continue
            d = None
            m = RE_DV2_PLACE.search(line)
            if m:
                g_ = [m.group(k) for k in range(1, 13)]
                d = dict(kind="place", method=g_[0], placed=g_[1], vtx=(float(g_[2]), float(g_[3]), float(g_[4])),
                         d_vtx_point=float(g_[5]), point=(float(g_[6]), float(g_[7]), float(g_[8])),
                         score=float(g_[9]), cluster=int(g_[10]), d_nearest_graph_vertex=float(g_[11]))
            if d is None:
                m = RE_DV2_MOVE.search(line)
                if m:
                    d = dict(kind="move", move=float(m.group(1)),
                             point=(float(m.group(2)), float(m.group(3)), float(m.group(4))),
                             n_seg=int(m.group(5)), d_after_refit=float(m.group(6)), cluster_ident=m.group(7))
            if d is None:
                m = RE_DV2_PRED.search(line)
                if m:
                    d = dict(kind="pred", point=(float(m.group(1)), float(m.group(2)), float(m.group(3))),
                             score=float(m.group(4)))
            if d is None:
                for kind, rx in (("nopred", RE_DV2_NOPRED), ("decline", RE_DV2_DECLINE), ("brk_decline", RE_DV2_BRKDECL),
                                 ("dl_failed", RE_DL_FAILED), ("bad_payload", RE_DV2_PAYLOAD), ("pyerr", RE_DV2_PYERR)):
                    m = rx.search(norm)
                    if m:
                        d = dict(kind=kind, detail=[m.group(k) for k in range(1, (rx.groups or 0) + 1)])
                        break
            if d is not None:
                d["raw"] = norm[:500]
                out["dv2"].append(d)
                if cur is not None:
                    cur["dv2"].append(d)
                continue
            m = RE_A5.search(line)
            if m:
                out["a5"].append(dict(shower=int(m.group(1)), len_cm=float(m.group(2)), pdg=int(m.group(3)),
                                      growth=float(m.group(4)), bragg=float(m.group(5)),
                                      group=len(groups) - 1))
                continue
            m = RE_DUAL_SKIP.search(line)
            if m:
                out["dual_skip"].append(int(m.group(1)))
                continue
            m = RE_DUAL_OFF.search(line)
            if m:
                out["dual_off"].append(dict(mode=m.group(1), vertex=m.group(2), raw=norm[:300]))
                continue
            m = RE_ROW.search(line)
            if m:
                out["rows"].append(dict(row=int(m.group(1)), gid=int(m.group(2)), cluster=int(m.group(3)),
                                        x=float(m.group(4)), y=float(m.group(5)), z=float(m.group(6)),
                                        Enu=m.group(7), acts=int(m.group(8))))
    out["groups"] = groups
    return out


# ---------------------------------------------------------------------------
# wrapper (container) log and PBS batch logs
# ---------------------------------------------------------------------------
def parse_container_log(path, fmt, idx):
    tag = f"evt_{idx:04d}"
    pre = fmt if fmt in ("SWAPON", "OFFRERUN", "DV2O", "DV2D") else "AB59"
    out = {"path": path, "exists": os.path.isfile(path), "lar_exit": None, "runtime_sec": None,
           "lib_line": None, "lib_path": None, "lib_md5": None, "main_jsonnet": None,
           "done": False, "guard_fail": [], "result_line": None, "warn_nonzero": False,
           "fmt": pre}
    if not out["exists"]:
        return out
    re_exit = re.compile(rf"\[{pre} {tag}\] lar exit: (-?\d+)(?:\s+runtime_sec=(\d+))?")
    re_lib = re.compile(rf"\[{pre} {tag}\] Library: (.*)$")
    re_mj = re.compile(rf"\[{pre} {tag}\] Main jsonnet: (\S+)")
    re_res = re.compile(rf"{pre}_RESULT {tag}: (.*)$")
    done_marker = f"{pre}_JOB_DONE_{tag}"
    with open(path, errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\n")
            m = re_exit.search(line)
            if m:
                out["lar_exit"] = int(m.group(1))
                if m.group(2) is not None:
                    out["runtime_sec"] = int(m.group(2))
                continue
            m = re_lib.search(line)
            if m:
                out["lib_line"] = m.group(1).strip()
                mm = re.search(r"md5=([0-9a-f]{32})", line)
                if mm:
                    out["lib_md5"] = mm.group(1)
                mp = re.search(r"(/\S*libWireCellClus\.so)", line)
                if mp:
                    out["lib_path"] = mp.group(1)
                continue
            m = re_mj.search(line)
            if m:
                out["main_jsonnet"] = m.group(1)
                continue
            m = re_res.search(line)
            if m:
                out["result_line"] = m.group(1)
                continue
            if "GUARD_FAIL" in line:
                out["guard_fail"].append(line.strip())
            if "[WARN] lar non-zero" in line:
                out["warn_nonzero"] = True
            if done_marker in line:
                out["done"] = True
    return out


def parse_batch_logs(glob_pat):
    """event idx -> list of {job, file, start, end, container_exit}."""
    ev = defaultdict(list)
    for p in sorted(glob.glob(glob_pat)):
        try:
            txt = open(p, errors="replace").read()
        except Exception:
            continue
        base = os.path.basename(p)
        fjob = base.split(".sophia")[0]
        starts = re.findall(r"--- event (\d{4}) start (\d+) job=(\S+)", txt)
        if starts:
            ends = {int(e): (int(rc), int(t)) for e, rc, t in
                    re.findall(r"--- event (\d{4}) container_exit=(-?\d+) end (\d+)", txt)}
            for e, t, job in starts:
                e = int(e)
                rc, tend = ends.get(e, (None, None))
                ev[e].append(dict(job=job, file=p, start=int(t), end=tend, container_exit=rc))
            continue
        m = re.search(r"Array index: (\d+)", txt)
        if m:
            ev[int(m.group(1))].append(dict(job=fjob, file=p, start=None, end=None, container_exit=None))
            continue
        for e in sorted(set(re.findall(r"\[(?:AB59|SWAPON|OFFRERUN) evt_(\d{4})\]", txt))):
            ev[int(e)].append(dict(job=fjob, file=p, start=None, end=None, container_exit=None))
    return ev


# ---------------------------------------------------------------------------
# Truth
# ---------------------------------------------------------------------------
def read_truth():
    d = {}
    with open(TRUTH_CSV, newline="") as fh:
        for r in csv.DictReader(fh):
            d[(int(r["run"]), int(r["subrun"]), int(r["event"]))] = r
    return d


# ---------------------------------------------------------------------------
# Per-event extraction with a content-signature cache
# ---------------------------------------------------------------------------
CACHE_VERSION = 6   # DV2 fields + A5 lines


def load_event(arm, idx, cache_dir):
    root_p = f"{arm['wc_dir']}/evt_{idx:04d}/tracking-pr.root"
    mabc_p = f"{arm['wc_dir']}/evt_{idx:04d}/mabc.zip"
    log_p = arm["lar_log"].format(idx=idx)
    sig = (CACHE_VERSION, _file_sig(root_p), _file_sig(mabc_p), _file_sig(log_p))
    key = _sha1(repr(sig).encode())
    cp = os.path.join(cache_dir, f"evt_{idx:04d}_{key}.pkl")
    if os.path.isfile(cp):
        with open(cp, "rb") as fh:
            return pickle.load(fh)
    d = {"idx": idx, "root": read_root(root_p), "mabc": read_mabc(mabc_p), "log": parse_lar_log(log_p)}
    os.makedirs(cache_dir, exist_ok=True)
    tmp = cp + ".tmp"
    with open(tmp, "wb") as fh:
        pickle.dump(d, fh, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(tmp, cp)
    return d


# ---------------------------------------------------------------------------
# MicroBooNE BDT scorer (validated; used UNCHANGED, only BASEDIR/OUTDIR/file names redirected)
# ---------------------------------------------------------------------------
_SCORER_BASEDIR_SRC = ('BASEDIR = ("/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/baseline_v0/"\n'
                       '           "ncdelta_50evt/wirecell")')
_SCORER_OUTDIR_SRC = 'OUTDIR  = os.path.join(os.path.dirname(__file__), "tables")'


def run_scorer(wc_dir, outdir, label):
    """exec the scorer source with BASEDIR -> wc_dir and OUTDIR -> outdir (inside S).
    Returns the scorer namespace (score_rows, read_event, collect_inputs, MODELS, ...)."""
    outdir = os.path.abspath(outdir)
    assert outdir.startswith(S + "/"), f"scorer OUTDIR {outdir} outside study area"
    src = open(SCORER_PY).read()
    reps = [
        (_SCORER_BASEDIR_SRC, f'BASEDIR = "{wc_dir}"'),
        (_SCORER_OUTDIR_SRC, f'OUTDIR = "{outdir}"'),
        ('/ncdelta_microboone_bdt_scores.csv"', f'/scorer_{label}_bdt_scores.csv"'),
        ('/ncdelta_reco_failure_taxonomy.csv"', f'/scorer_{label}_taxonomy.csv"'),
        ('/ncdelta_microboone_cutflow.csv"', f'/scorer_{label}_cutflow.csv"'),
    ]
    for old, new in reps:
        n = src.count(old)
        assert n == 1, f"scorer source: expected exactly one occurrence of {old!r}, found {n}"
        src = src.replace(old, new)
    os.makedirs(outdir, exist_ok=True)
    ns = {"__name__": f"scorer_{label}", "__file__": os.path.join(outdir, "score_microboone_bdts_exec.py")}
    logp = os.path.join(outdir, f"scorer_{label}_stdout.log")
    with open(logp, "w") as fh, contextlib.redirect_stdout(fh):
        exec(compile(src, f"score_microboone_bdts[{label}]", "exec"), ns)
    assert ns["BASEDIR"] == wc_dir, "scorer BASEDIR redirect failed"
    assert ns["OUTDIR"] == outdir, "scorer OUTDIR redirect failed"
    for fn in (f"scorer_{label}_bdt_scores.csv", f"scorer_{label}_taxonomy.csv", f"scorer_{label}_cutflow.csv"):
        assert os.path.isfile(os.path.join(outdir, fn)), f"scorer did not write {fn} into {outdir}"
    return ns


def load_cutflow_definitions():
    """Extract CUTS_PRE_FV and apply_cutflow verbatim from the frozen generate_bdt_comparison.py."""
    gsrc = open(GEN_BDT_PY).read()
    i0 = gsrc.index("CUTS_PRE_FV = [")
    i1 = gsrc.index("bsl_cf, bsl_final = apply_cutflow(")
    block = gsrc[i0:i1]
    assert "def apply_cutflow(rows, label):" in block
    ns = {"MODELS": list(BDT_MODELS)}
    exec(compile(block, "generate_bdt_comparison.py[CUTS_PRE_FV+apply_cutflow]", "exec"), ns)
    steps = [s for s, _ in ns["CUTS_PRE_FV"]]
    return ns["CUTS_PRE_FV"], ns["apply_cutflow"], steps, block


# ---------------------------------------------------------------------------
# Config-block comparison helpers
# ---------------------------------------------------------------------------
def compiled_config_diff(path_a, path_b):
    """Leaf diff of two compiled WCT configs, components matched by (type, name)."""
    a = json.load(open(path_a))
    b = json.load(open(path_b))

    def key(c):
        return (c.get("type"), c.get("name", ""))

    def walk(x, y, p, out):
        if isinstance(x, dict) and isinstance(y, dict):
            for k in sorted(set(x) | set(y)):
                if k not in x:
                    out.append((p + [k], "<absent>", y[k]))
                elif k not in y:
                    out.append((p + [k], x[k], "<absent>"))
                else:
                    walk(x[k], y[k], p + [k], out)
        elif isinstance(x, list) and isinstance(y, list) and len(x) == len(y):
            for i, (u, v) in enumerate(zip(x, y)):
                walk(u, v, p + [i], out)
        elif x != y:
            out.append((p, x, y))

    am = {key(c): c for c in a}
    bm = {key(c): c for c in b}
    diffs = []
    for k in sorted(set(am) & set(bm), key=str):
        d = []
        walk(am[k], bm[k], [], d)
        for p, x, y in d:
            diffs.append({"component": f"{k[0]}:{k[1]}", "path": "/".join(map(str, p)),
                          "off": x, "on": y})
    return {"n_off": len(a), "n_on": len(b),
            "only_off": sorted(map(str, set(am) - set(bm))), "only_on": sorted(map(str, set(bm) - set(am))),
            "order_identical": [key(c) for c in a] == [key(c) for c in b],
            "diffs": diffs}
