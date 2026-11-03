#!/usr/bin/env python3
"""
run_dv2.py -- DV2-MAX x single-photon 59-event analysis (dv2max_singlephoton59_20261102).

Arms (all read-only inputs):
  F  = frozen Fix2-v2 ab59 arm (fix2_vertex_shower_onehop_20261005/ab59)         ab_lib.arm_off()
  SW = main_vertex_swap_apply=true DIAGNOSTIC arm (main_vertex_swap_ab59_20261014) ab_lib.arm_on()
  O  = integration build, vertex_method=original         ab_lib.arm_dv2("O", runset)
  D  = integration build, vertex_method=dv2_split_move   ab_lib.arm_dv2("D", runset)

Definitions reused verbatim (exec of the source, never re-typed):
  derive()        <- main_vertex_swap_ab59_20261014/scripts/ab_analysis/run_all.py
                     (DIRECT_SUCCESS / FIX2_ONE_HOP_SUCCESS / NO_USABLE_SHOWER from the fix2_v2: lines)
  scorer          <- analysis/microboone_1gamma_v0/score_microboone_bdts.py (BASEDIR/OUTDIR redirected)
  CUTS_PRE_FV     <- fix2 ab59 tables/generate_bdt_comparison.py
  cluster truth   <- remaining19_rootcause_20261014/lib/forensics.py building blocks (WIRECELL_DIR redirected)
Truth is used ONLY here, diagnostically.

Usage (login node):
  python3 run_dv2.py --selftest                 O := F and D := F, machinery check
  python3 run_dv2.py --runset smoke --events 18 --arms D
  python3 run_dv2.py --runset main --events 18,0,2,58,20       (sentinel)
  python3 run_dv2.py --runset main                              (all 59 -> tables/)
"""
import os, sys, re, csv, json, math, argparse, collections, pickle, hashlib, datetime
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ab_lib as L

S = L.S
N = L.N_EVENTS
MODELS = L.BDT_MODELS
RUN_ALL = f"{L.SWAP_S}/scripts/ab_analysis/run_all.py"
FOR_LIB = f"{L.BASE}/development/remaining19_rootcause_20261014/lib"
SEVEN = [2, 31, 32, 37, 42, 56, 58]
FIX2_REC5 = [12, 14, 16, 20, 26]
SENTINEL = [18, 0, 2, 58, 20]
NOT_RECO = {6, 10, 30}     # remaining19 Task 5 class D: the signal photon never deposits in the TPC
REMAINING19 = {0: "WRONG_PDG", 9: "WRONG_PDG", 21: "WRONG_PDG", 44: "WRONG_PDG", 54: "WRONG_PDG",
               2: "GRAPH_DISCONNECTED", 31: "GRAPH_DISCONNECTED", 32: "GRAPH_DISCONNECTED", 37: "GRAPH_DISCONNECTED",
               42: "GRAPH_DISCONNECTED", 56: "GRAPH_DISCONNECTED", 58: "GRAPH_DISCONNECTED",
               6: "BELOW_20MEV", 10: "BELOW_20MEV", 13: "BELOW_20MEV", 27: "BELOW_20MEV", 30: "BELOW_20MEV",
               50: "BELOW_20MEV", 55: "BELOW_20MEV"}
FROZEN_CUTFLOW = [59, 57, 38, 38, 15, 8, 5, 5, 4]
FROZEN_SELECTED = [5, 15, 20, 36]
KNOWN_BDT_NOISE_EVENTS = {46, 47}       # determinism_ab59_vs_offrerun: numu/other/nue scores move run-to-run
KNOWN_TT_PERM_NOTE = "permutation_only"


def _guard(path):
    ap = os.path.abspath(path)
    assert ap.startswith(S + "/"), f"refusing to write outside {S}: {ap}"
    return ap


def cell(v):
    if v is None:
        return ""
    if isinstance(v, (bool, np.bool_)):
        return "True" if v else "False"
    if isinstance(v, float):
        return "" if not math.isfinite(v) else (f"{v:.4f}" if abs(v) < 1e5 else repr(v))
    if isinstance(v, (np.floating,)):
        return cell(float(v))
    if isinstance(v, (np.integer,)):
        return str(int(v))
    if isinstance(v, (list, tuple, set)):
        return ";".join(cell(x) for x in v)
    return str(v)


def write_csv(path, rows, columns):
    p = _guard(path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=columns, extrasaction="raise")
        w.writeheader()
        for r in rows:
            miss = [c for c in columns if c not in r]
            assert not miss, f"{os.path.basename(p)} row missing {miss[:6]}"
            w.writerow({c: cell(r[c]) for c in columns})
    return p


def write_json(path, obj):
    p = _guard(path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w") as fh:
        json.dump(L.to_py(obj), fh, indent=1)
    return p


# ---------------------------------------------------------------------------
# verbatim definitions from the swap A/B (exec of source blocks)
# ---------------------------------------------------------------------------
def _exec_block(path, start, end, ns):
    src = open(path).read()
    i0, i1 = src.index(start), src.index(end)
    exec(compile(src[i0:i1], f"{os.path.basename(path)}[{start.strip()}..]", "exec"), ns)
    return ns


_NS = _exec_block(RUN_ALL, "def _maxby(", "# ---------------------------------------------------------------------------\n# tree diff",
                  {"L": L, "math": math})
derive = _NS["derive"]
_NS2 = _exec_block(RUN_ALL, "def diff_tree(", "def tagger_family(", {"L": L})
diff_tree = _NS2["diff_tree"]


# ---------------------------------------------------------------------------
# cluster-level truth per arm (forensics building blocks; diagnostic only)
# ---------------------------------------------------------------------------
sys.path.insert(0, FOR_LIB)
import forensics as F          # noqa: E402


def cluster_truth(wc_dir, idx, truth_row, cache_dir):
    p = f"{wc_dir}/evt_{idx:04d}/mabc.zip"
    sig = (2, L._file_sig(p))
    cp = os.path.join(cache_dir, f"ctruth_{idx:04d}_{L._sha1(repr(sig).encode())}.pkl")
    if os.path.isfile(cp):
        return pickle.load(open(cp, "rb"))
    out = {"ok": False}
    if not os.path.isfile(p):
        out["error"] = "no mabc.zip"
        return out
    try:
        F.WIRECELL_DIR = wc_dir
        ent = F.read_bee(idx)
        inters, parts = F.parse_truth_tree(F.bee_get(ent, "mc", 0, kind="truth"))
        tv = np.array([float(truth_row["vtx_x"]), float(truth_row["vtx_y"]), float(truth_row["vtx_z"])])
        it = min(inters, key=lambda i: np.linalg.norm(np.subtract(i["vertex"], tv)) if i.get("vertex") else 1e9)
        d_sce, used_r = None, None
        for rr in (5.0, 15.0, 40.0):
            sh = F.sce_shift_near(ent, it["vertex"], r=rr)
            if sh and "d_sce" in sh:
                d_sce, used_r = sh["d_sce"], rr
                break
        v_sce = (np.add(it["vertex"], d_sce) if d_sce is not None else np.asarray(it["vertex"])).tolist()
        Sx = F.build_stage_points(ent)
        near = F.clusters_near_point_pr(Sx, v_sce)
        ph = {q["id"] for q in parts if q["name"] == "gamma" and q["is_primary"] and q["interaction_id"] == it["id"]}
        pr_tids = {q["id"] for q in parts if q["name"] == "proton" and q["is_primary"] and q["interaction_id"] == it["id"]}
        mem = F.photon_membership(Sx, ph)["pr"]
        pr = Sx["pr"]
        lab = Sx["pr_label"]
        isp = np.isin(lab, list(pr_tids)) if pr_tids else np.zeros(len(lab), bool)
        pq = collections.Counter()
        for c, q, f in zip(pr["cluster_id"].tolist(), pr["q"].tolist(), isp.tolist()):
            if f:
                pq[int(c)] += q
        out = {"ok": True, "interaction_id": it["id"], "vertex_true": list(it["vertex"]), "vertex_sce_est": v_sce,
               "sce_shift_radius_cm": used_r, "d_sce": d_sce,
               "true_vertex_cluster": near["pr"]["key"], "true_vertex_nearest_cluster": near["pr"]["nearest_key"],
               "true_vertex_nearest_pr_point_cm": near["nearest_pr_point_dist_cm"],
               "true_vertex_cluster_counts": near["pr"]["counts"],
               "n_photons": len(ph), "photon_clusters": [(int(r["key"]) if r["key"] != "none" else None,
                                                        r["frac_of_photon_q"]) for r in mem["clusters"]],
               "photon_q_total": mem["photon_q_total"],
               "n_primary_protons": len(pr_tids),
               "proton_clusters": [(c, q / sum(pq.values())) for c, q in pq.most_common()] if pq else [],
               "cluster_ids": sorted(set(int(c) for c in pr["cluster_id"].tolist())),
               "pr_digest": L._sha1(np.round(pr["xyz"], 3).tobytes() + pr["cluster_id"].astype(np.int64).tobytes())}
    except Exception as e:  # pragma: no cover
        out = {"ok": False, "error": f"{type(e).__name__}: {e}"}
    os.makedirs(cache_dir, exist_ok=True)
    pickle.dump(out, open(cp, "wb"))
    return out


# ---------------------------------------------------------------------------
# DV2 per-event extraction
# ---------------------------------------------------------------------------
def read_hook(wc_dir, idx):
    p = f"{wc_dir}/evt_{idx:04d}/dv2_hook.jsonl"
    if not os.path.isfile(p):
        return None
    return [json.loads(x) for x in open(p) if x.strip()]


def dv2_fields(f, evd, hook):
    g = evd["log"]
    grp = f["grp"]
    lines = (grp["dv2"] if grp else []) or []
    ev_lines = g["dv2"]
    kinds = collections.Counter(d["kind"] for d in ev_lines)
    place = [d for d in lines if d["kind"] == "place"]
    move = [d for d in lines if d["kind"] == "move"]
    pred = [d for d in lines if d["kind"] == "pred"]
    o = {"dv2_cfg_line": bool(g["dv2_cfg"]), "dv2_cfg_method": g["dv2_cfg"]["method"] if g["dv2_cfg"] else "",
         "n_hook_calls": len(hook) if hook is not None else None,
         "n_hook_pred": sum(1 for h in hook if h.get("pred") is not None) if hook else 0,
         "n_place_lines_event": kinds.get("place", 0), "n_move_lines_event": kinds.get("move", 0),
         "n_nopred_event": kinds.get("nopred", 0), "n_dl_failed_event": kinds.get("dl_failed", 0),
         "n_pyerr_event": kinds.get("pyerr", 0), "n_decline_event": kinds.get("decline", 0),
         "n_brk_decline_event": kinds.get("brk_decline", 0), "n_bad_payload_event": kinds.get("bad_payload", 0),
         "dual_off_skipped": len(g["dual_skip"]), "dual_off_ran": len(g["dual_off"])}
    P = place[-1] if place else None
    M = move[-1] if move else None
    o["dv2_placed"] = P is not None
    o["dv2_point"] = P["point"] if P else (pred[-1]["point"] if pred else None)
    o["dv2_score"] = P["score"] if P else (pred[-1]["score"] if pred else None)
    o["placement"] = P["placed"] if P else ""
    o["placed_vertex"] = P["vtx"] if P else None
    o["placed_cluster"] = P["cluster"] if P else None
    o["d_placed_to_point"] = P["d_vtx_point"] if P else None
    o["d_nearest_graph_vertex"] = P["d_nearest_graph_vertex"] if P else None
    o["split"] = (P["placed"] == "split") if P else None
    o["moved"] = M is not None
    o["move_cm"] = M["move"] if M else (0.0 if P else None)
    o["move_nseg"] = M["n_seg"] if M else None
    o["move_d_after_refit"] = M["d_after_refit"] if M else None
    o["fallback"] = ("NO_PREDICTION" if any(d["kind"] == "nopred" for d in lines) else
                     "DL_STEP_EXCEPTION" if any(d["kind"] == "dl_failed" for d in lines) else
                     "NONE" if P else ("NO_DV2_LINE" if f["has_tagger"] else "NO_CANDIDATE"))
    o["n_dv2_groups"] = sum(1 for gg in g["groups"] if gg["dv2"])
    return o


def dist(a, b):
    if a is None or b is None or any(x is None for x in a) or any(x is None for x in b):
        return None
    return float(math.dist([float(x) for x in a], [float(x) for x in b]))


# ---------------------------------------------------------------------------
# arm loading
# ---------------------------------------------------------------------------
def load_arm(arm, idxs, truth, with_ctruth=True):
    cache = f"{S}/tables/_work/cache/{arm['label']}_{arm['fmt']}"
    out = {}
    for i in idxs:
        evd = L.load_event(arm, i, cache)
        rse = evd["root"]["rse"]
        trow = truth.get(rse) if rse[0] is not None else None
        f = derive(evd, rse, truth)
        f["evd"] = evd
        f["idx"] = i
        f["rse"] = rse
        f["truth_row"] = trow
        f["cont"] = L.parse_container_log(arm["cont_log"].format(idx=i), arm["fmt"], i)
        f["hook"] = read_hook(arm["wc_dir"], i)
        f["dv2"] = dv2_fields(f, evd, f["hook"])
        f["ctruth"] = cluster_truth(arm["wc_dir"], i, trow, cache) if (with_ctruth and trow) else {"ok": False}
        ct = f["ctruth"]
        f["truth_dist_sce"] = dist(f["nu_xyz"], ct.get("vertex_sce_est")) if (ct.get("ok") and f["has_tagger"]) else None
        out[i] = f
    return out


def scorer_rows(arm, tag):
    ns = L.run_scorer(arm["wc_dir"], f"{S}/tables/_work/scorer_{tag}", tag)
    return {int(r["evt_idx"]): r for r in ns["score_rows"]}


def fnum(r, k):
    v = r.get(k, "")
    try:
        return float(v) if v not in ("", None) else None
    except (TypeError, ValueError):
        return None


def bdt_view(sr):
    o = {}
    for m in MODELS:
        o[f"{m}_evaluable"] = int(sr[f"{m}_bdt_evaluable"]) if sr.get(f"{m}_bdt_evaluable", "") != "" else 0
        o[f"{m}_score"] = fnum(sr, f"{m}_bdt_score")
    th = {"numu": 0.4, "other": 0.2, "ncpi0": -0.05, "nue": -1.0}
    for m in MODELS:
        o[f"{m}_pass"] = (o[f"{m}_score"] is not None and o[f"{m}_score"] > th[m])
    o["all4_evaluable"] = all(o[f"{m}_evaluable"] for m in MODELS)
    o["proton_category"] = sr.get("proton_category", "")
    o["shw_sp_n_20mev_showers"] = sr.get("shw_sp_n_20mev_showers", "")
    o["shw_sp_n_20br1_showers"] = sr.get("shw_sp_n_20br1_showers", "")
    o["kine_reco_Enu"] = fnum(sr, "kine_reco_Enu")
    return o


# ---------------------------------------------------------------------------
def access_class(f):
    if not f["has_tagger"]:
        return "NO_CANDIDATE"
    c = f["sa"]["classification"]
    return {"DIRECT_SUCCESS": "DIRECT", "FIX2_ONE_HOP_SUCCESS": "ONE_HOP", "NO_USABLE_SHOWER": "INACCESSIBLE"}.get(c, c)


def main_contains(f, key):
    ct = f["ctruth"]
    if not ct.get("ok") or not f["has_tagger"]:
        return None
    if key == "vertex":
        tv = ct["true_vertex_cluster"]
        return None if tv is None else (int(tv) == f["final_main"])
    if key == "photon":
        pcs = [c for c in ct["photon_clusters"] if c[0] is not None]
        return None if not pcs else (pcs[0][0] == f["final_main"])
    if key == "proton":
        if not ct["proton_clusters"]:
            return None
        return ct["proton_clusters"][0][0] == f["final_main"]


def photon_frac_in_main(f):
    ct = f["ctruth"]
    if not ct.get("ok") or not f["has_tagger"]:
        return None
    return sum(fr for c, fr in ct["photon_clusters"] if c == f["final_main"] and fr is not None)


def summarize_event(f, sr=None):
    """one-line dict used in console + several tables"""
    o = {"has_tagger": f["has_tagger"], "selected_main": f["log_selected_main"], "final_main": f["final_main"],
         "nu_xyz": f["nu_xyz"] if f["has_tagger"] else None,
         "truth_dist": f["truth_dist"], "truth_dist_sce": f["truth_dist_sce"],
         "access": access_class(f), "shw_sp_filled": f["sa"]["shw_sp_filled"],
         "n20": f["sa"]["shw_sp_n_20mev_showers"], "n20br1": f["sa"]["shw_sp_n_20br1_showers"],
         "fix2_fallback": f["sa"]["fallback_activated"], "n_neighbor_added": f["sa"]["n_neighbor_added"],
         "mvsa": f["mvsa_modes"]}
    if sr is not None:
        o.update(bdt_view(sr))
    return o


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runset", default="main")
    ap.add_argument("--events", default="")
    ap.add_argument("--arms", default="O,D")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--no-ctruth", action="store_true")
    ap.add_argument("--outdir", default="")
    args = ap.parse_args()
    idxs = [int(x) for x in args.events.split(",") if x != ""] or list(range(N))
    full = (len(idxs) == N) and not args.selftest
    truth = L.read_truth()
    arms = {"F": L.arm_off(), "SW": L.arm_on()}
    if args.selftest:
        arms["O"] = dict(L.arm_off(), label="O_selftest")
        arms["D"] = dict(L.arm_off(), label="D_selftest")
    else:
        for a in args.arms.split(","):
            arms[a] = L.arm_dv2(a, args.runset)
    outdir = args.outdir or (f"{S}/tables" if full else f"{S}/tables/_work/{'selftest' if args.selftest else args.runset}_"
                                                          f"{'-'.join(map(str, idxs)) if len(idxs) < 10 else 'n%d' % len(idxs)}")
    print("outdir", outdir)
    A = {k: load_arm(v, idxs, truth, with_ctruth=not args.no_ctruth) for k, v in arms.items()}
    # scorer (handles missing files as no-candidate events)
    SR = {}
    for k, v in arms.items():
        tag = f"{k}_{args.runset}" if k in ("O", "D") and not args.selftest else (k if not args.selftest else f"{k}_selftest")
        SR[k] = scorer_rows(v, tag)
    CUTS, apply_cutflow, STEPS, _src = L.load_cutflow_definitions()

    def cutflow(k, subset=None):
        rows = [{**SR[k][i], "evt_idx": i} for i in (subset if subset is not None else range(N))]
        cf, final = apply_cutflow(rows, k)
        return cf, sorted(int(r["evt_idx"]) for r in final)

    present = [k for k in ("O", "D") if k in A]
    # --------------------------------------------------------------- console
    for i in idxs:
        print(f"\n=== evt {i:04d} rse={A['F'][i]['rse']}")
        for k in ["F", "SW"] + present:
            f = A[k][i]
            s = summarize_event(f, SR[k].get(i))
            dv = f["dv2"]
            print(f"  {k:2s} cand={int(s['has_tagger'])} sel={s['selected_main']} final={s['final_main']} "
                  f"dT={cell(s['truth_dist'])} dSCE={cell(s['truth_dist_sce'])} {s['access']:12s} filled={s['shw_sp_filled']} "
                  f"n20={s['n20']} br1={s['n20br1']} eval4={int(s.get('all4_evaluable', 0))} "
                  f"pc={s.get('proton_category','')} mvsa={s['mvsa']} ")
            if dv["dv2_cfg_line"] or dv["n_hook_calls"]:
                print(f"     DV2 cfg={dv['dv2_cfg_method']} hook={dv['n_hook_calls']}/{dv['n_hook_pred']} place={dv['placement']} "
                      f"pcl={dv['placed_cluster']} P={dv['dv2_point']} s={cell(dv['dv2_score'])} dnear={cell(dv['d_nearest_graph_vertex'])} "
                      f"move={cell(dv['move_cm'])} fb={dv['fallback']} nopred={dv['n_nopred_event']} dlfail={dv['n_dl_failed_event']} "
                      f"pyerr={dv['n_pyerr_event']} dualskip={dv['dual_off_skipped']} dualran={dv['dual_off_ran']}")
            ct = f["ctruth"]
            if ct.get("ok"):
                print(f"     truth: tv_cluster={ct['true_vertex_cluster']} (nearest {ct['true_vertex_nearest_cluster']}, "
                      f"{ct['true_vertex_nearest_pr_point_cm']:.2f} cm) photon_cl={ct['photon_clusters'][:3]} "
                      f"proton_cl={ct['proton_clusters'][:2]} main_has_vtx={main_contains(f, 'vertex')} "
                      f"main_has_photon={main_contains(f, 'photon')}")
    for k in ["F", "SW"] + present:
        cf, sel = cutflow(k)
        print(f"cutflow {k}: {[r['count'] for r in cf]} selected {sel}")
    build_tables(A, SR, cutflow, outdir, full, args, idxs, present)


# ---------------------------------------------------------------------------
def control_rows(A, SR, idxs):
    """ARM O vs frozen Fix2-v2."""
    rows = []
    for i in idxs:
        fF, fO = A["F"][i], A["O"][i]
        sF, sO = summarize_event(fF, SR["F"][i]), summarize_event(fO, SR["O"][i])
        rF, rO = fF["evd"]["root"], fO["evd"]["root"]
        dt = diff_tree(rF["T_tagger_rows"], rO["T_tagger_rows"], rF["T_tagger_types"], rO["T_tagger_types"])
        dk = diff_tree(rF["T_kine_rows"], rO["T_kine_rows"], rF["T_kine_types"], rO["T_kine_types"])
        tt_new = [d["branch"] for d in dt if d["note"] == "absent_off"]
        tt_gone = [d["branch"] for d in dt if d["note"] == "absent_on"]
        tt_diff = [d for d in dt if not d["equal"] and d["note"] not in ("absent_off", "absent_on")]
        tt_perm = [d["branch"] for d in tt_diff if KNOWN_TT_PERM_NOTE in (d["note"] or "")]
        tt_real = [d["branch"] for d in tt_diff if KNOWN_TT_PERM_NOTE not in (d["note"] or "")]
        tk_new = [d["branch"] for d in dk if d["note"] == "absent_off"]
        tk_real = [d["branch"] for d in dk if not d["equal"] and d["note"] not in ("absent_off", "absent_on")]
        r = {"evt_idx": i, "run": fF["rse"][0], "subrun": fF["rse"][1], "event": fF["rse"][2]}
        checks = {}
        for key in ("has_tagger", "final_main", "access", "shw_sp_filled", "n20", "n20br1",
                    "numu_evaluable", "other_evaluable", "ncpi0_evaluable", "nue_evaluable", "proton_category"):
            r[f"frozen_{key}"], r[f"O_{key}"] = sF.get(key), sO.get(key)
            checks[key] = (str(sF.get(key)) == str(sO.get(key)))
        dvtx = dist(sF["nu_xyz"], sO["nu_xyz"]) if (sF["nu_xyz"] and sO["nu_xyz"]) else None
        r["nu_vertex_shift_cm"] = dvtx
        checks["nu_vertex"] = (dvtx is None and not sF["has_tagger"] and not sO["has_tagger"]) or (dvtx is not None and dvtx < 1e-3)
        for m in MODELS:
            a, b = sF.get(f"{m}_score"), sO.get(f"{m}_score")
            r[f"frozen_{m}_score"], r[f"O_{m}_score"] = a, b
            r[f"{m}_score_absdiff"] = abs(a - b) if (a is not None and b is not None) else None
            checks[f"{m}_score"] = (a is None and b is None) or (a is not None and b is not None and abs(a - b) < 1e-6)
        a, b = sF.get("kine_reco_Enu"), sO.get("kine_reco_Enu")
        r["frozen_kine_reco_Enu"], r["O_kine_reco_Enu"] = a, b
        checks["kine_reco_Enu"] = (a is None and b is None) or (a is not None and b is not None and abs(a - b) < 1e-3)
        cfF, cfO = SR["F"][i], SR["O"][i]
        r["frozen_preFV_stage_reached"] = r["O_preFV_stage_reached"] = None
        r["n_ttagger_branches_new_in_O"] = len(tt_new)
        r["ttagger_branches_new_in_O"] = ";".join(tt_new[:12]) + (" ..." if len(tt_new) > 12 else "")
        r["n_ttagger_branches_missing_in_O"] = len(tt_gone)
        r["n_ttagger_value_diffs_permutation_only"] = len(tt_perm)
        r["ttagger_value_diffs_other"] = ";".join(tt_real)
        r["n_tkine_branches_new_in_O"] = len(tk_new)
        r["tkine_value_diffs"] = ";".join(tk_real)
        bad = [k for k, v in checks.items() if not v]
        noise = [k for k in bad if k.endswith("_score") and i in KNOWN_BDT_NOISE_EVENTS]
        unexpl = [k for k in bad if k not in noise]
        r["mismatched_fields"] = ";".join(bad)
        r["verdict"] = ("MATCH" if not bad and not tt_real and not tk_real else
                        "MATCH_EXCEPT_KNOWN_NOISE" if not unexpl and not tk_real else "DIFFERENT")
        r["notes"] = ("known run-to-run BDT noise event (determinism_ab59_vs_offrerun)" if noise else "")
        rows.append(r)
    return rows


def build_tables(A, SR, cutflow, outdir, full, args, idxs, present):
    os.makedirs(_guard(outdir), exist_ok=True)
    summ = {"generated_utc": datetime.datetime.utcnow().isoformat() + "Z", "events": idxs, "runset": args.runset,
            "selftest": args.selftest}
    # ---------------- control O vs frozen
    if "O" in present:
        rows = control_rows(A, SR, idxs)
        cols = list(rows[0].keys())
        write_csv(f"{outdir}/diagnostic_control_original.csv", rows, cols)
        summ["control_verdicts"] = collections.Counter(r["verdict"] for r in rows)
        summ["control_different"] = [r["evt_idx"] for r in rows if r["verdict"] == "DIFFERENT"]
        print("CONTROL O vs frozen:", dict(summ["control_verdicts"]), "DIFFERENT:", summ["control_different"])
    if "D" not in present:
        write_json(f"{outdir}/summary.json", summ)
        return
    # ---------------- per-event DV2 diagnostics (ARM D)
    dv_rows = []
    for i in idxs:
        f = A["D"][i]
        dv = f["dv2"]
        ct = f["ctruth"]
        tv = ct.get("vertex_true") if ct.get("ok") else (
            [float(f["truth_row"][k]) for k in ("vtx_x", "vtx_y", "vtx_z")] if f["truth_row"] else None)
        r = {"evt_idx": i, "run": f["rse"][0], "subrun": f["rse"][1], "event": f["rse"][2],
             "has_candidate": f["has_tagger"], "n_dv2_calls_hook": dv["n_hook_calls"], "n_dv2_predictions_hook": dv["n_hook_pred"],
             "dv2_point": dv["dv2_point"], "dv2_score_P_lt1cm": dv["dv2_score"],
             "truth_vertex_true_frame": tv, "truth_vertex_sce_est": ct.get("vertex_sce_est"),
             "d_dv2_point_truth_cm": dist(dv["dv2_point"], tv),
             "d_dv2_point_truth_sce_cm": dist(dv["dv2_point"], ct.get("vertex_sce_est")),
             "placement": dv["placement"], "d_nearest_pr_vertex_cm": dv["d_nearest_graph_vertex"],
             "split": dv["split"], "moved": dv["moved"], "move_cm": dv["move_cm"],
             "move_segments_rerouted": dv["move_nseg"], "d_after_refit_cm": dv["move_d_after_refit"],
             "initial_main_cluster": f["log_selected_main"], "placed_vertex_cluster": dv["placed_cluster"],
             "dv2_switched_main_cluster": (dv["placed_cluster"] is not None and f["log_selected_main"] is not None
                                           and dv["placed_cluster"] != f["log_selected_main"]),
             "final_main_cluster": f["final_main"], "final_vertex": f["nu_xyz"] if f["has_tagger"] else None,
             "final_truth_dist_cm": f["truth_dist"], "final_truth_dist_sce_cm": f["truth_dist_sce"],
             "fallback": dv["fallback"], "n_no_prediction_warn": dv["n_nopred_event"],
             "n_dl_step_exception_warn": dv["n_dl_failed_event"], "n_python_error_lines": dv["n_pyerr_event"],
             "n_place_declined_warn": dv["n_decline_event"], "traditional_mvsa_lines": ";".join(f["mvsa_modes"]),
             "true_vertex_cluster": ct.get("true_vertex_cluster") if ct.get("ok") else None,
             "final_main_contains_true_vertex": main_contains(f, "vertex"),
             "photon_q_frac_in_final_main": photon_frac_in_main(f),
             "final_main_is_photon_dominant_cluster": main_contains(f, "photon"),
             "n_primary_protons": ct.get("n_primary_protons") if ct.get("ok") else None,
             "final_main_is_proton_dominant_cluster": main_contains(f, "proton"),
             "n_A5_retypes_selected_candidate": sum(1 for a in f["evd"]["log"]["a5"] if f["grp"] is not None and a["group"] == f["evd"]["log"]["groups"].index(f["grp"])),
             "A5_retypes": ";".join(f"id{a['shower']}/{a['len_cm']}cm->{a['pdg']}(g{a['growth']},b{a['bragg']})" for a in f["evd"]["log"]["a5"]),
             "access": access_class(f), "shw_sp_filled": f["sa"]["shw_sp_filled"]}
        dv_rows.append(r)
    write_csv(f"{outdir}/dv2_event_diagnostics.csv", dv_rows, list(dv_rows[0].keys()))
    if "O" not in present:
        write_json(f"{outdir}/summary.json", summ)
        return
    # ---------------- event59 O vs D
    ev_rows = []
    for i in idxs:
        r = {"evt_idx": i, "run": A["D"][i]["rse"][0], "subrun": A["D"][i]["rse"][1], "event": A["D"][i]["rse"][2]}
        for k in ("O", "D"):
            f = A[k][i]
            s = summarize_event(f, SR[k][i])
            r[f"{k}_candidate"] = int(s["has_tagger"])
            r[f"{k}_main_cluster"] = s["final_main"]
            r[f"{k}_vertex_truth_dist_cm"] = s["truth_dist"]
            r[f"{k}_vertex_truth_dist_sce_cm"] = s["truth_dist_sce"]
            r[f"{k}_access"] = s["access"]
            r[f"{k}_shw_sp_filled"] = s["shw_sp_filled"]
            r[f"{k}_all4_bdt_evaluable"] = s["all4_evaluable"]
            for m in MODELS:
                r[f"{k}_{m}_score"] = s[f"{m}_score"]
                r[f"{k}_{m}_pass"] = s[f"{m}_pass"]
            r[f"{k}_shw_sp_n_20br1_showers"] = s["shw_sp_n_20br1_showers"]
            r[f"{k}_proton_category"] = s["proton_category"]
        ev_rows.append(r)
    _, selO = cutflow("O") if full else (None, [])
    _, selD = cutflow("D") if full else (None, [])
    for r in ev_rows:
        r["O_preFV_selected"] = r["evt_idx"] in selO
        r["D_preFV_selected"] = r["evt_idx"] in selD
    write_csv(f"{outdir}/event59_original_vs_dv2.csv", ev_rows, list(ev_rows[0].keys()))
    if not full:
        write_json(f"{outdir}/summary.json", summ)
        return
    # ---------------- cutflow side by side
    cf = {k: cutflow(k) for k in ("F", "SW", "O", "D")}
    labels = {"1_total": "total", "2_neutrino_candidate": "neutrino candidate",
              "3_shw_sp_n_20mev_gt0": ">20 MeV shower (shw_sp_n_20mev_showers>0)",
              "4_all_4_bdts_evaluable": "all 4 BDTs evaluable", "5_numu_gt0p4": "numu BDT > 0.4",
              "6_other_gt0p2": "other BDT > 0.2", "7_ncpi0_gtneg0p05": "ncpi0 BDT > -0.05",
              "8_nue_gtneg1p0": "nue BDT > -1.0", "9_shw_sp_n_20br1_eq1": "exactly one shower (n_20br1 == 1)"}
    cfr = []
    for j, step in enumerate(cf["O"][0]):
        r = {"step": step["step"], "description": labels[step["step"]]}
        for k in ("F", "SW", "O", "D"):
            s = cf[k][0][j]
            r[f"{k}_count"], r[f"{k}_0p"], r[f"{k}_np"] = s["count"], s["n_0p"], s["n_np"]
            r[f"{k}_events"] = s["passing_evt_idx"]
        pO = set(map(int, filter(None, cf["O"][0][j]["passing_evt_idx"].split(";"))))
        pD = set(map(int, filter(None, cf["D"][0][j]["passing_evt_idx"].split(";"))))
        r["D_gained_vs_O"] = sorted(pD - pO)
        r["D_lost_vs_O"] = sorted(pO - pD)
        cfr.append(r)
    cols = ["step", "description"] + [f"{k}_{x}" for k in ("O", "D") for x in ("count", "0p", "np")] + \
           ["D_gained_vs_O", "D_lost_vs_O", "F_count", "SW_count", "O_events", "D_events", "F_events", "SW_events"]
    write_csv(f"{outdir}/cutflow_original_vs_dv2.csv", cfr, cols)
    summ["cutflow"] = {k: [s["count"] for s in cf[k][0]] for k in cf}
    summ["selected"] = {k: cf[k][1] for k in cf}
    # ---------------- graph7
    g7 = []
    for i in SEVEN:
        fD, fO, fS = A["D"][i], A["O"][i], A["SW"][i]
        sD = summarize_event(fD, SR["D"][i])
        ct = fD["ctruth"]
        g7.append({"event": f"{i:04d}", "original_accessibility": access_class(fO),
                   "frozen_fix2v2_accessibility": access_class(A["F"][i]),
                   "traditional_swapON_accessibility": access_class(fS),
                   "dv2_accessibility": access_class(fD),
                   "dv2_vertex_truth_distance": fD["truth_dist"], "dv2_vertex_truth_distance_sce": fD["truth_dist_sce"],
                   "dv2_main_cluster": fD["final_main"], "original_main_cluster": fO["final_main"],
                   "swapON_main_cluster": fS["final_main"],
                   "true_vertex_cluster": ct.get("true_vertex_cluster") if ct.get("ok") else None,
                   "same_as_true_vertex_cluster": main_contains(fD, "vertex"),
                   "direct_or_onehop": access_class(fD) if access_class(fD) in ("DIRECT", "ONE_HOP") else "",
                   "shw_sp_filled": sD["shw_sp_filled"], "BDT_evaluable": sD["all4_evaluable"],
                   "selection": i in cf["D"][1],
                   "notes": f"dv2 placement={fD['dv2']['placement']} switched_main={fD['dv2']['placed_cluster'] != fD['log_selected_main']} "
                            f"fallback={fD['dv2']['fallback']} photon_q_frac_in_main={cell(photon_frac_in_main(fD))}"})
    write_csv(f"{outdir}/graph7_dv2_outcome.csv", g7, list(g7[0].keys()))
    summ["graph7_accessible"] = [r["event"] for r in g7 if r["shw_sp_filled"] == 1]
    summ["graph7_accessible_correct_cluster"] = [r["event"] for r in g7 if r["shw_sp_filled"] == 1 and r["same_as_true_vertex_cluster"]]
    # ---------------- fix2 under dv2
    fx = []
    for i in range(N):
        fO, fD = A["O"][i], A["D"][i]
        cO, cD = access_class(fO), access_class(fD)
        if not (i in FIX2_REC5 or cO == "ONE_HOP" or cD == "ONE_HOP" or fD["sa"]["fallback_activated"]):
            continue
        if i in FIX2_REC5:
            role = ("STILL_NEEDED" if cD == "ONE_HOP" else "MADE_REDUNDANT" if cD == "DIRECT" else
                    "NO_LONGER_SUFFICIENT" if cD in ("INACCESSIBLE", "NO_CANDIDATE") else "CHANGED")
            if role != "NO_LONGER_SUFFICIENT" and fD["final_main"] != fO["final_main"]:
                role += "_MAIN_CLUSTER_CHANGED"
        else:
            role = ("NEW_FIX2_RECOVERY_UNDER_DV2" if cD == "ONE_HOP" and cO != "ONE_HOP" else
                    "FIX2_RECOVERY_LOST_UNDER_DV2" if cO == "ONE_HOP" and cD != "ONE_HOP" else
                    "SAME_ONE_HOP" if cO == cD == "ONE_HOP" else "FALLBACK_ACTIVATED_NO_RECOVERY")
        fx.append({"evt_idx": i, "original_five": i in FIX2_REC5, "O_access": cO, "D_access": cD,
                   "O_fallback_activated": fO["sa"]["fallback_activated"], "D_fallback_activated": fD["sa"]["fallback_activated"],
                   "D_n_neighbor_added": fD["sa"]["n_neighbor_added"], "O_main_cluster": fO["final_main"],
                   "D_main_cluster": fD["final_main"], "O_truth_dist": fO["truth_dist"], "D_truth_dist": fD["truth_dist"],
                   "D_shw_sp_filled": fD["sa"]["shw_sp_filled"], "D_selected": i in cf["D"][1], "role": role})
    write_csv(f"{outdir}/fix2_under_dv2.csv", fx, list(fx[0].keys()))
    summ["fix2_roles"] = {r["evt_idx"]: r["role"] for r in fx}
    # ---------------- remaining 19
    r19 = []
    for i, orig in REMAINING19.items():
        fD, fO = A["D"][i], A["O"][i]
        cD = access_class(fD)
        sa = fD["sa"]
        pool = (sa["direct_list"] or []) + (sa["neighbor_list"] or [])
        maxE = max(pool, key=lambda s: s["E"]) if pool else None
        vtx_ok = bool((fD["truth_dist_sce"] is not None and fD["truth_dist_sce"] < 3.0) or main_contains(fD, "vertex"))
        sub = ""
        if cD == "DIRECT":
            cls = "RESOLVED_DIRECT"
        elif cD == "ONE_HOP":
            cls = "RESOLVED_ONE_HOP"
        elif i in NOT_RECO:
            cls, sub = "NOT_RECONSTRUCTABLE", "signal photon never deposits in the TPC (remaining19 Task 5 class D)"
        elif not fD["has_tagger"]:
            cls, sub = "OTHER", "no neutrino candidate"
        elif not vtx_ok:
            cls, sub = "STILL_INACCESSIBLE_VERTEX", "wrong vertex (final vertex >3 cm from truth and not in the true-vertex cluster)"
        elif maxE is not None and maxE["pdg"] != 11 and maxE["E"] > 20:
            cls, sub = "STILL_TRACK_DOMINATED", f"vertex right; leading >20 MeV pool object typed pdg {maxE['pdg']}"
        elif maxE is not None and maxE["pdg"] == 11 and maxE["E"] > 20:
            cls, sub = "PID_DOWNSTREAM", "vertex right; pdg-11 >20 MeV shower in pool rejected downstream (badreco)"
        else:
            cls, sub = "STILL_INACCESSIBLE_VERTEX", "vertex right; no >20 MeV object within one hop (photon beyond the graph neighbourhood)"
        r19.append({"evt_idx": i, "remaining19_class": orig, "O_access": access_class(fO), "D_access": cD,
                    "D_class": cls, "D_subreason": sub, "D_vertex_ok": vtx_ok, "D_main_cluster": fD["final_main"], "D_true_vertex_cluster":
                        fD["ctruth"].get("true_vertex_cluster") if fD["ctruth"].get("ok") else None,
                    "D_truth_dist_cm": fD["truth_dist"], "D_truth_dist_sce_cm": fD["truth_dist_sce"],
                    "D_photon_q_frac_in_main": photon_frac_in_main(fD),
                    "D_pool_maxE_MeV": maxE["E"] if maxE else None, "D_pool_maxE_pdg": maxE["pdg"] if maxE else None,
                    "D_shw_sp_filled": sa["shw_sp_filled"], "D_selected": i in cf["D"][1],
                    "O_selected": i in cf["O"][1]})
    write_csv(f"{outdir}/remaining19_under_dv2.csv", r19, list(r19[0].keys()))
    summ["remaining19"] = collections.Counter(r["D_class"] for r in r19)
    # ---------------- every accessibility change O -> D, with the mechanism read from the D log / truth
    acc = ("DIRECT", "ONE_HOP")
    ch = []
    for i in range(N):
        fO, fD = A["O"][i], A["D"][i]
        cO, cD = access_class(fO), access_class(fD)
        if (cO in acc) == (cD in acc):
            continue
        direction = "GAIN" if cD in acc else "LOSS"
        f = fD if direction == "LOSS" else fO
        sa = f["sa"]
        pool = (sa["direct_list"] or []) + (sa["neighbor_list"] or [])
        big = [s for s in pool if s["E"] > 20]
        gi = f["evd"]["log"]["groups"].index(f["grp"]) if f["grp"] is not None else None
        a5 = [a for a in f["evd"]["log"]["a5"] if a["group"] == gi]
        vtx_ok = bool((f["truth_dist_sce"] is not None and f["truth_dist_sce"] < 3.0) or main_contains(f, "vertex"))
        if any(s["pdg"] == 211 for s in big) and a5:
            mech = "A5_RETYPE_TO_211"
        elif any(s["pdg"] == 13 for s in big):
            mech = "LEADING_OBJECT_TYPED_MUON"
        elif any(s["pdg"] not in (11,) for s in big):
            mech = "LEADING_OBJECT_TYPED_" + str(max(big, key=lambda s: s["E"])["pdg"])
        elif not big and vtx_ok and not main_contains(f, "photon"):
            mech = "VERTEX_CORRECT_PHOTON_NOT_ATTACHED"
        elif not big and not vtx_ok:
            mech = "WRONG_VERTEX_NO_20MEV_OBJECT"
        elif not big:
            mech = "NO_20MEV_OBJECT_WITHIN_ONE_HOP"
        else:
            mech = "OTHER"
        ch.append({"evt_idx": i, "direction": direction, "O_access": cO, "D_access": cD,
                   "inaccessible_arm": "D" if direction == "LOSS" else "O", "mechanism_in_inaccessible_arm": mech,
                   "inaccessible_arm_pool_gt20MeV": ";".join(f"{s['E']:.1f}MeV/pdg{s['pdg']}" for s in big),
                   "inaccessible_arm_A5_retypes": ";".join(f"id{a['shower']}/{a['len_cm']}cm->{a['pdg']}(g{a['growth']},b{a['bragg']})" for a in a5),
                   "O_main_cluster": fO["final_main"], "D_main_cluster": fD["final_main"],
                   "dv2_switched_main_cluster": dv_rows[i]["dv2_switched_main_cluster"],
                   "true_vertex_cluster": fD["ctruth"].get("true_vertex_cluster") if fD["ctruth"].get("ok") else None,
                   "O_truth_dist_cm": fO["truth_dist"], "D_truth_dist_cm": fD["truth_dist"],
                   "O_truth_dist_sce_cm": fO["truth_dist_sce"], "D_truth_dist_sce_cm": fD["truth_dist_sce"],
                   "O_main_contains_true_vertex": main_contains(fO, "vertex"), "D_main_contains_true_vertex": main_contains(fD, "vertex"),
                   "O_photon_q_frac_in_main": photon_frac_in_main(fO), "D_photon_q_frac_in_main": photon_frac_in_main(fD),
                   "dv2_placement": fD["dv2"]["placement"], "dv2_move_cm": fD["dv2"]["move_cm"], "dv2_score": fD["dv2"]["dv2_score"],
                   "O_selected": i in cf["O"][1], "D_selected": i in cf["D"][1]})
    write_csv(f"{outdir}/dv2_access_changes.csv", ch, list(ch[0].keys()))
    summ["access_changes"] = {r["evt_idx"]: f"{r['direction']}:{r['mechanism_in_inaccessible_arm']}" for r in ch}
    # ---------------- aggregate numbers
    def med(v):
        v = [x for x in v if x is not None]
        return float(np.median(v)) if v else None
    for k in ("O", "D", "F"):
        d = [A[k][i]["truth_dist"] for i in range(N) if A[k][i]["has_tagger"]]
        ds = [A[k][i]["truth_dist_sce"] for i in range(N) if A[k][i]["has_tagger"]]
        summ[f"{k}_n_candidates"] = len(d)
        summ[f"{k}_truth_dist_median"] = med(d)
        summ[f"{k}_truth_dist_sce_median"] = med(ds)
        summ[f"{k}_within1cm"] = sum(1 for x in d if x is not None and x < 1.0)
        summ[f"{k}_within1cm_sce"] = sum(1 for x in ds if x is not None and x < 1.0)
        summ[f"{k}_shw_sp_filled"] = sum(1 for i in range(N) if A[k][i]["sa"]["shw_sp_filled"] == 1)
        summ[f"{k}_all4_evaluable"] = sum(1 for i in range(N) if bdt_view(SR[k][i])["all4_evaluable"])
        summ[f"{k}_access_counts"] = collections.Counter(access_class(A[k][i]) for i in range(N))
    summ["D_placement"] = collections.Counter(A["D"][i]["dv2"]["placement"] or A["D"][i]["dv2"]["fallback"] for i in range(N))
    summ["D_fallbacks"] = {i: A["D"][i]["dv2"]["fallback"] for i in range(N) if A["D"][i]["dv2"]["fallback"] != "NONE"}
    summ["D_moved"] = sum(1 for i in range(N) if A["D"][i]["dv2"]["moved"])
    summ["D_switched_main"] = [i for i in range(N) if dv_rows[i]["dv2_switched_main_cluster"]]
    write_json(f"{outdir}/summary.json", summ)
    print(json.dumps(L.to_py({k: v for k, v in summ.items() if k not in ("events",)}), indent=1)[:6000])


if __name__ == "__main__":
    main()
