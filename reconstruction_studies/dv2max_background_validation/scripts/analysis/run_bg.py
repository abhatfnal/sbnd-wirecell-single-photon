#!/usr/bin/env python3
"""
run_bg.py -- DV2-MAX x single-photon BACKGROUND validation analysis (dv2max_background_validation_20261102).

Per runset (numucc | ncpi0), arms O (vertex_method=original) and D (dv2_split_move) on the SAME events,
plus the frozen Fix2-v2 arm F on the sentinel/control events.  Every reconstruction-side definition is the
signal study's, reused VERBATIM by exec of dv2max_singlephoton59_20261102/scripts/analysis/run_dv2.py up to its
main() (load_arm / derive / diff_tree / dv2_fields / summarize_event / bdt_view / access_class / main_contains /
control_rows / cluster_truth), the MicroBooNE scorer (N_EVENTS redirected to the list length) and CUTS_PRE_FV.
Truth (generator + the labeler's nu-only Bee truth tree) is used ONLY here, diagnostically.

Usage (login node):  python3 run_bg.py --runset numucc [--n N] [--events i,j,..] [--arms O,D,F]
"""
import os, sys, csv, json, math, argparse, collections, datetime, pickle
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ab_lib as L   # noqa: E402  (background copy; S = this work area)

_SIG = f"{L.SIGW}/scripts/analysis/run_dv2.py"
_src = open(_SIG).read()
R = {"__file__": os.path.join(HERE, "run_dv2_signal_defs.py"), "__name__": "run_dv2_signal_defs"}
exec(compile(_src[:_src.index("def main():")], "run_dv2.py[..main]", "exec"), R)
exec(compile(_src[_src.index("def control_rows("):_src.index("def build_tables(")], "run_dv2.py[control_rows]", "exec"), R)
assert R["L"] is L and R["S"] == L.S
R["KNOWN_BDT_NOISE_EVENTS"] = set()      # the signal-study noise list refers to SIGNAL event indices -> not used here
F = R["F"]
load_arm, summarize_event, bdt_view, access_class = R["load_arm"], R["summarize_event"], R["bdt_view"], R["access_class"]
main_contains, control_rows, write_csv, write_json, cell, dist = (R["main_contains"], R["control_rows"], R["write_csv"],
                                                                  R["write_json"], R["cell"], R["dist"])
S = L.S
MODELS = L.BDT_MODELS
TH = {"numu": 0.4, "other": 0.2, "ncpi0": -0.05, "nue": -1.0}
CUTS, apply_cutflow, STEPS, _CUTSRC = L.load_cutflow_definitions()
STEP_LABEL = {"1_total": "total", "2_neutrino_candidate": "neutrino candidate",
              "3_shw_sp_n_20mev_gt0": ">20 MeV SP shower", "4_all_4_bdts_evaluable": "all 4 BDTs evaluable",
              "5_numu_gt0p4": "numu > 0.4", "6_other_gt0p2": "other > 0.2", "7_ncpi0_gtneg0p05": "ncpi0 > -0.05",
              "8_nue_gtneg1p0": "nue > -1.0", "9_shw_sp_n_20br1_eq1": "n_20br1 == 1"}


# ---------------------------------------------------------------------------
def em_truth(wc_dir, idx, truth_row, cache_dir):
    """EM truth of the active interaction from the labeler's nu-only Bee tree (KE > 10 MeV kept by the labeler):
    gammas / e+- with KE > 20 MeV (any depth; includes pi0 decay photons), their charge membership over the arm's PR
    clusters (forensics.photon_membership), and the pi0 -> gamma photons separately."""
    p = f"{wc_dir}/evt_{idx:04d}/mabc.zip"
    sig = (3, L._file_sig(p))
    cp = os.path.join(cache_dir, f"emtruth_{idx:04d}_{L._sha1(repr(sig).encode())}.pkl")
    if os.path.isfile(cp):
        return pickle.load(open(cp, "rb"))
    out = {"ok": False}
    try:
        F.WIRECELL_DIR = wc_dir
        ent = F.read_bee(idx)
        inters, parts = F.parse_truth_tree(F.bee_get(ent, "mc", 0, kind="truth"))
        tv = np.array([float(truth_row["vtx_x"]), float(truth_row["vtx_y"]), float(truth_row["vtx_z"])])
        it = min(inters, key=lambda i: np.linalg.norm(np.subtract(i["vertex"], tv)) if i.get("vertex") else 1e9)
        mine = [q for q in parts if q["interaction_id"] == it["id"]]
        byid = {q["id"]: q for q in mine}
        em = [q for q in mine if q["name"] in ("gamma", "e-", "e+") and (q["ke_mev"] or 0) > 20]
        pi0g = [q for q in mine if q["name"] == "gamma" and q["parent_id"] in byid and byid[q["parent_id"]]["name"] == "pi0"]
        Sx = F.build_stage_points(ent)
        mem = F.photon_membership(Sx, {q["id"] for q in em})["pr"] if em else {"clusters": [], "photon_q_total": 0}
        out = {"ok": True, "vertex_true": list(it["vertex"]) if it.get("vertex") else None,
               "n_em_gt20": len(em), "em_names": [f"{q['name']}:{q['ke_mev']:.0f}" for q in em],
               "n_pi0_gammas": len(pi0g), "pi0_gamma_ke": sorted([q["ke_mev"] for q in pi0g], reverse=True),
               "em_clusters": [(int(r["key"]) if r["key"] != "none" else None, r["frac_of_photon_q"]) for r in mem["clusters"]],
               "em_q_total": mem["photon_q_total"]}
    except Exception as e:  # pragma: no cover
        out = {"ok": False, "error": f"{type(e).__name__}: {e}"}
    os.makedirs(cache_dir, exist_ok=True)
    pickle.dump(out, open(cp, "wb"))
    return out


def em_frac_in(f, em, cl):
    if not em.get("ok") or cl is None:
        return None
    return sum(fr for c, fr in em["em_clusters"] if c == cl and fr is not None)


def stage_of(sr, i):
    """(n_passed_steps, last_passed_step, first_failed_step) of the pre-FV cut sequence for one event."""
    row = {**sr, "evt_idx": i}
    last, failed, n = None, "", 0
    for name, cut in CUTS:
        if name == "1_total" or cut(row):
            last, n = name, n + 1
        else:
            failed = name
            break
    return n, last, failed


def a5_sel(f):
    g = f["grp"]
    if g is None:
        return []
    gi = f["evd"]["log"]["groups"].index(g)
    return [a for a in f["evd"]["log"]["a5"] if a["group"] == gi]


def a5_str(lst):
    return ";".join(f"id{a['shower']}/{a['len_cm']}cm->{a['pdg']}(g{a['growth']},b{a['bragg']})" for a in lst)


def pool(f):
    sa = f["sa"]
    return (sa["direct_list"] or []) + (sa["neighbor_list"] or [])


def vtx_ok(f):
    return bool((f["truth_dist_sce"] is not None and f["truth_dist_sce"] < 3.0) or main_contains(f, "vertex"))


def dv2_gate(f):
    """event-level DV2 hard gate (ARM D): every DV2 call produced a prediction and a placement, nothing failed."""
    g = f["evd"]["log"]
    k = collections.Counter(d["kind"] for d in g["dv2"])
    hook = f["hook"] or []
    calls, preds = len(hook), sum(1 for h in hook if h.get("pred") is not None)
    bad = k.get("nopred", 0) + k.get("dl_failed", 0) + k.get("pyerr", 0) + k.get("bad_payload", 0)
    ok = (not f["has_tagger"] and calls == 0 and bad == 0) or (f["has_tagger"] and calls >= 1 and preds == calls
                                                                and k.get("place", 0) >= calls and bad == 0)
    return dict(dv2_calls=calls, dv2_predictions=preds, dv2_place_lines=k.get("place", 0), dv2_move_lines=k.get("move", 0),
                no_prediction_warn=k.get("nopred", 0), dl_step_exception_warn=k.get("dl_failed", 0),
                python_error_lines=k.get("pyerr", 0), place_declined=k.get("decline", 0), gate_pass=ok)


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runset", required=True, choices=["numucc", "ncpi0"])
    ap.add_argument("--n", type=int, default=0, help="first N events of the list (default: all complete in O and D)")
    ap.add_argument("--events", default="", help="explicit subset (control / sentinel); writes to tables/_work")
    ap.add_argument("--arms", default="O,D")
    ap.add_argument("--outdir", default="")
    args = ap.parse_args()
    rs = args.runset
    arms = {a: L.arm_bg(a, rs) for a in args.arms.split(",")}
    if args.events:
        idxs = [int(x) for x in args.events.split(",")]
    else:
        n = args.n
        if not n:
            n = 0
            while all(os.path.isfile(arms[a]["cont_log"].format(idx=n)) and
                      L.parse_container_log(arms[a]["cont_log"].format(idx=n), arms[a]["fmt"], n)["done"] for a in ("O", "D")):
                n += 1
        idxs = list(range(n))
    full = not args.events
    outdir = args.outdir or (f"{S}/tables" if full else f"{S}/tables/_work/{rs}_{'-'.join(map(str, idxs))[:60]}")
    truth = L.read_truth(rs)
    tlist = {int(r["evt_idx"]): r for r in csv.DictReader(open(f"{S}/inputs/{rs}_events.csv"))}
    print("runset", rs, "events", len(idxs), "outdir", outdir, flush=True)
    A = {k: load_arm(v, idxs, truth) for k, v in arms.items()}
    EM = {k: {i: em_truth(arms[k]["wc_dir"], i, tlist[i], f"{S}/tables/_work/cache/em_{k}_{rs}") for i in idxs} for k in arms}
    SR = {}
    for k, v in arms.items():
        ns = L.run_scorer(v["wc_dir"], f"{S}/tables/_work/scorer_{k}_{rs}", f"{k}_{rs}", n_events=max(idxs) + 1)
        SR[k] = {int(r["evt_idx"]): r for r in ns["score_rows"]}
    # RSE consistency: the reconstructed event must be the listed one
    for k in arms:
        for i in idxs:
            rse = A[k][i]["rse"]
            want = (int(tlist[i]["run"]), int(tlist[i]["subrun"]), int(tlist[i]["event"]))
            assert rse[0] is None or tuple(rse) == want, (k, i, rse, want)
    res = dict(runset=rs, events=idxs, generated_utc=datetime.datetime.utcnow().isoformat() + "Z", arms=list(arms))
    os.makedirs(R["_guard"](outdir), exist_ok=True)

    # ------------------------------------------------ per-arm per-event views
    V = {}
    for k in arms:
        V[k] = {}
        for i in idxs:
            f, sr = A[k][i], SR[k][i]
            s = summarize_event(f, sr)
            nst, last, failed = stage_of(sr, i)
            V[k][i] = dict(s=s, stage=nst, last=last, failed=failed, a5=a5_sel(f), vok=vtx_ok(f), em=EM[k][i],
                           cont=f["cont"], dv2=f["dv2"], gate=dv2_gate(f) if k == "D" else None)
    # ------------------------------------------------ control: F vs O (where F was run)
    if "F" in arms and "O" in arms:
        A2 = {"F": A["F"], "O": A["O"]}
        rows = control_rows(A2, {"F": SR["F"], "O": SR["O"]}, idxs)
        write_csv(f"{outdir}/{rs}_control_F_vs_O.csv", rows, list(rows[0].keys()))
        res["control_verdicts"] = collections.Counter(r["verdict"] for r in rows)
        res["control_different"] = {r["evt_idx"]: r["mismatched_fields"] + "|" + r["ttagger_value_diffs_other"] for r in rows
                                    if r["verdict"] != "MATCH"}
        print("CONTROL F vs O:", dict(res["control_verdicts"]), res["control_different"])
    # ------------------------------------------------ run / gate table
    run_rows = []
    for i in idxs:
        r = {"evt_idx": i, "rse": tlist[i]["rse"]}
        for k in arms:
            c = V[k][i]["cont"]
            r[f"{k}_lar_exit"], r[f"{k}_runtime_sec"], r[f"{k}_lib_md5"] = c["lar_exit"], c["runtime_sec"], c["lib_md5"]
            r[f"{k}_done"], r[f"{k}_guard_fail"] = c["done"], ";".join(c["guard_fail"])
            r[f"{k}_candidate"] = V[k][i]["s"]["has_tagger"]
        if "D" in arms:
            r.update({f"D_{x}": y for x, y in V["D"][i]["gate"].items()})
            r["D_fallback"] = V["D"][i]["dv2"]["fallback"]
            r["D_placement"] = V["D"][i]["dv2"]["placement"]
        run_rows.append(r)
    write_csv(f"{outdir}/{rs}_run_gate.csv", run_rows, list(run_rows[0].keys()))
    if "D" in arms:
        res["D_gate_fail"] = [r["evt_idx"] for r in run_rows if not r["D_gate_pass"]]
        res["D_fallback"] = collections.Counter(r["D_fallback"] for r in run_rows)
        res["D_placement"] = collections.Counter(r["D_placement"] or "none" for r in run_rows)
        res["D_dv2_calls"] = sum(r["D_dv2_calls"] for r in run_rows)
        res["D_dv2_predictions"] = sum(r["D_dv2_predictions"] for r in run_rows)
        res["D_calls_per_event"] = collections.Counter(r["D_dv2_calls"] for r in run_rows)
    for k in arms:
        res[f"{k}_lar_exit"] = collections.Counter(r[f"{k}_lar_exit"] for r in run_rows)
        res[f"{k}_lib_md5"] = collections.Counter(r[f"{k}_lib_md5"] for r in run_rows)
        rt = [r[f"{k}_runtime_sec"] for r in run_rows if r[f"{k}_runtime_sec"] is not None]
        res[f"{k}_runtime_median_sec"] = float(np.median(rt)) if rt else None
    if not ("O" in arms and "D" in arms):
        write_json(f"{outdir}/{rs}_summary.json", res)
        return

    # ------------------------------------------------ cutflow
    def cutflow(k):
        rows = [{**SR[k][i], "evt_idx": i} for i in idxs]
        cf, final = apply_cutflow(rows, k)
        return cf, sorted(int(r["evt_idx"]) for r in final)
    CF = {k: cutflow(k) for k in ("O", "D")}
    ntot = len(idxs)
    cfr = []
    for j, step in enumerate(CF["O"][0]):
        r = {"step": step["step"], "description": STEP_LABEL[step["step"]]}
        for k in ("O", "D"):
            c = CF[k][0][j]["count"]
            prev = CF[k][0][j - 1]["count"] if j else ntot
            ft, fp = c / ntot, (c / prev if prev else None)
            r[f"{k}_count"], r[f"{k}_0p"], r[f"{k}_np"] = c, CF[k][0][j]["n_0p"], CF[k][0][j]["n_np"]
            r[f"{k}_frac_total"], r[f"{k}_frac_total_err"] = ft, math.sqrt(ft * (1 - ft) / ntot)
            r[f"{k}_frac_prev"] = fp
            r[f"{k}_frac_prev_err"] = math.sqrt(fp * (1 - fp) / prev) if prev else None
        pO = set(map(int, filter(None, CF["O"][0][j]["passing_evt_idx"].split(";"))))
        pD = set(map(int, filter(None, CF["D"][0][j]["passing_evt_idx"].split(";"))))
        r["D_gained_vs_O"], r["D_lost_vs_O"] = sorted(pD - pO), sorted(pO - pD)
        r["D_minus_O"] = r["D_count"] - r["O_count"]
        cfr.append(r)
    write_csv(f"{outdir}/{rs}_cutflow.csv", cfr, list(cfr[0].keys()))
    res["cutflow"] = {k: [s["count"] for s in CF[k][0]] for k in CF}
    res["selected"] = {k: CF[k][1] for k in CF}
    selO, selD = set(CF["O"][1]), set(CF["D"][1])

    # ------------------------------------------------ score migration
    def topo(v):
        s = v["s"]
        return (s["n20"], s["n20br1"], s.get("proton_category"))
    mig = []
    for i in idxs:
        o, d = V["O"][i], V["D"][i]
        so, sd = o["s"], d["s"]
        accO, accD = so["shw_sp_filled"] == 1, sd["shw_sp_filled"] == 1
        if so["has_tagger"] != sd["has_tagger"]:
            cls = "OTHER"
        elif accO and not accD:
            cls = "ACCESSIBILITY_LOSS"
        elif accD and not accO:
            cls = "ACCESSIBILITY_GAIN_ONLY" if d["stage"] <= 4 else "WORSE_BACKGROUND_REJECTION"
        elif d["stage"] > o["stage"]:
            cls = "WORSE_BACKGROUND_REJECTION"
        elif d["stage"] < o["stage"]:
            cls = "IMPROVED_BACKGROUND_REJECTION"
        elif topo(o) != topo(d) or so["final_main"] != sd["final_main"]:
            cls = "TOPOLOGY_CHANGE"
        else:
            cls = "NO_CHANGE"
        r = {"evt_idx": i, "rse": tlist[i]["rse"], "O_candidate": int(so["has_tagger"]), "D_candidate": int(sd["has_tagger"]),
             "O_vertex": so["nu_xyz"], "D_vertex": sd["nu_xyz"],
             "vertex_shift_cm": dist(so["nu_xyz"], sd["nu_xyz"]) if (so["nu_xyz"] and sd["nu_xyz"]) else None,
             "O_vertex_truth_dist_cm": so["truth_dist"], "D_vertex_truth_dist_cm": sd["truth_dist"],
             "O_vertex_truth_dist_sce_cm": so["truth_dist_sce"], "D_vertex_truth_dist_sce_cm": sd["truth_dist_sce"],
             "O_main_cluster": so["final_main"], "D_main_cluster": sd["final_main"],
             "true_vertex_cluster": A["D"][i]["ctruth"].get("true_vertex_cluster") if A["D"][i]["ctruth"].get("ok") else None,
             "O_main_contains_true_vertex": main_contains(A["O"][i], "vertex"),
             "D_main_contains_true_vertex": main_contains(A["D"][i], "vertex"),
             "dv2_switched_main_cluster": (d["dv2"]["placed_cluster"] is not None and A["D"][i]["log_selected_main"] is not None
                                           and d["dv2"]["placed_cluster"] != A["D"][i]["log_selected_main"]),
             "dv2_placement": d["dv2"]["placement"], "dv2_move_cm": d["dv2"]["move_cm"], "dv2_score": d["dv2"]["dv2_score"],
             "O_access": so["access"], "D_access": sd["access"]}
        for m in MODELS:
            r[f"O_{m}_score"], r[f"D_{m}_score"] = so.get(f"{m}_score"), sd.get(f"{m}_score")
            a, b = so.get(f"{m}_score"), sd.get(f"{m}_score")
            r[f"{m}_delta"] = (b - a) if (a is not None and b is not None) else None
        r.update({"O_n20": so["n20"], "D_n20": sd["n20"], "O_n20br1": so["n20br1"], "D_n20br1": sd["n20br1"],
                  "O_proton_category": so.get("proton_category"), "D_proton_category": sd.get("proton_category"),
                  "O_kine_reco_Enu": so.get("kine_reco_Enu"), "D_kine_reco_Enu": sd.get("kine_reco_Enu"),
                  "O_last_cut_passed": o["last"], "O_first_cut_failed": o["failed"],
                  "D_last_cut_passed": d["last"], "D_first_cut_failed": d["failed"],
                  "O_stage": o["stage"], "D_stage": d["stage"], "selected_O": i in selO, "selected_D": i in selD,
                  "O_A5_retypes": a5_str(o["a5"]), "D_A5_retypes": a5_str(d["a5"]),
                  "O_fix2_fallback": so["fix2_fallback"], "D_fix2_fallback": sd["fix2_fallback"],
                  "truth_n_em_gt20": d["em"].get("n_em_gt20"), "truth_em": ";".join(d["em"].get("em_names", [])),
                  "O_em_q_frac_in_main": em_frac_in(A["O"][i], o["em"], so["final_main"]),
                  "D_em_q_frac_in_main": em_frac_in(A["D"][i], d["em"], sd["final_main"]),
                  "migration_class": cls})
        for x in ("mode", "nu_E_GeV", "lepton_E_GeV", "n_pi0", "n_pipm", "n_proton_ke35", "vtx_dist_to_active_boundary_cm",
                  "g4_muon_straight_len_cm", "g4_muon_end_in_active", "g4_pi0_E_GeV", "g4_gamma1_E_GeV", "g4_gamma2_E_GeV",
                  "g4_gamma_asym", "g4_gamma1_conv_cm", "g4_gamma2_conv_cm"):
            r[f"truth_{x}"] = tlist[i].get(x, "")
        mig.append(r)
    write_csv(f"{outdir}/{rs}_score_migration.csv", mig, list(mig[0].keys()))
    res["migration_classes"] = collections.Counter(r["migration_class"] for r in mig)
    M = {r["evt_idx"]: r for r in mig}

    # ------------------------------------------------ score shifts
    sh = {}
    for m in MODELS:
        both = [r for r in mig if r[f"O_{m}_score"] is not None and r[f"D_{m}_score"] is not None]
        dl = [r[f"{m}_delta"] for r in both]
        up = [r["evt_idx"] for r in both if r[f"O_{m}_score"] <= TH[m] < r[f"D_{m}_score"]]
        dn = [r["evt_idx"] for r in both if r[f"D_{m}_score"] <= TH[m] < r[f"O_{m}_score"]]
        sh[m] = dict(n_both_evaluable=len(both), median_delta=float(np.median(dl)) if dl else None,
                     mean_delta=float(np.mean(dl)) if dl else None,
                     O_pass_all=sum(1 for r in mig if r[f"O_{m}_score"] is not None and r[f"O_{m}_score"] > TH[m]),
                     D_pass_all=sum(1 for r in mig if r[f"D_{m}_score"] is not None and r[f"D_{m}_score"] > TH[m]),
                     cross_up_both_evaluable=up, cross_down_both_evaluable=dn,
                     O_median=float(np.median([r[f"O_{m}_score"] for r in mig if r[f"O_{m}_score"] is not None])) if any(r[f"O_{m}_score"] is not None for r in mig) else None,
                     D_median=float(np.median([r[f"D_{m}_score"] for r in mig if r[f"D_{m}_score"] is not None])) if any(r[f"D_{m}_score"] is not None for r in mig) else None)
    res["score_shift"] = sh

    # ------------------------------------------------ vertex metrics and main-cluster diagnostics
    def vstats(vals):
        v = [x for x in vals if x is not None]
        if not v:
            return {}
        a = np.asarray(v)
        return dict(n=len(v), median=float(np.median(a)), q68=float(np.quantile(a, 0.68)),
                    lt1=float(np.mean(a < 1)), lt3=float(np.mean(a < 3)), lt5=float(np.mean(a < 5)), gt20=float(np.mean(a > 20)))
    res["vertex"] = {k: {"true": vstats([V[k][i]["s"]["truth_dist"] for i in idxs if V[k][i]["s"]["has_tagger"]]),
                         "sce": vstats([V[k][i]["s"]["truth_dist_sce"] for i in idxs if V[k][i]["s"]["has_tagger"]])}
                     for k in ("O", "D")}
    tv_def = [r for r in mig if r["true_vertex_cluster"] is not None and r["O_candidate"] and r["D_candidate"]]
    sw = [r for r in mig if r["dv2_switched_main_cluster"]]
    res["main_cluster"] = dict(
        n_tv_defined=len(tv_def),
        O_contains_tv=sum(1 for r in tv_def if r["O_main_contains_true_vertex"]),
        D_contains_tv=sum(1 for r in tv_def if r["D_main_contains_true_vertex"]),
        dv2_switches=len(sw),
        correct_switches=sum(1 for r in sw if r["D_main_contains_true_vertex"] is True),
        wrong_switches=sum(1 for r in sw if r["D_main_contains_true_vertex"] is False),
        undetermined_switches=sum(1 for r in sw if r["D_main_contains_true_vertex"] is None),
        switches_fixing_O=sum(1 for r in sw if r["D_main_contains_true_vertex"] is True and r["O_main_contains_true_vertex"] is False),
        switches_breaking_O=sum(1 for r in sw if r["D_main_contains_true_vertex"] is False and r["O_main_contains_true_vertex"] is True),
        same_cluster_moves=sum(1 for r in mig if r["D_candidate"] and not r["dv2_switched_main_cluster"]
                               and r["vertex_shift_cm"] is not None and r["vertex_shift_cm"] > 1e-3),
        same_cluster_same_vertex=sum(1 for r in mig if r["D_candidate"] and not r["dv2_switched_main_cluster"]
                                     and r["vertex_shift_cm"] is not None and r["vertex_shift_cm"] <= 1e-3))

    # ------------------------------------------------ accessibility changes
    acc = ("DIRECT", "ONE_HOP")
    ch = []
    for i in idxs:
        o, d = V["O"][i], V["D"][i]
        cO, cD = o["s"]["access"], d["s"]["access"]
        if (cO in acc) == (cD in acc):
            continue
        gain = cD in acc
        big = lambda f: [s for s in pool(f) if s["E"] > 20]
        bO, bD = big(A["O"][i]), big(A["D"][i])
        if gain:
            if cD == "ONE_HOP":
                mech = "FIX2_GAIN"
            elif any(s["pdg"] == 211 for s in bO) and o["a5"]:
                mech = "A5_RETYPE_GAIN"
            elif d["vok"] and not o["vok"]:
                mech = "VERTEX_CORRECTION_GAIN"
            elif not d["vok"]:
                mech = "WRONG_VERTEX_GAIN"
            else:
                mech = "OTHER"
        else:
            if any(s["pdg"] == 211 for s in bD) and d["a5"]:
                mech = "A5_RETYPE_LOSS"
            elif cO == "ONE_HOP":
                mech = "FIX2_LOSS"
            elif d["vok"] and not o["vok"]:
                mech = "VERTEX_CORRECTION_DETACHED_SHOWER_LOSS"
            elif not d["vok"]:
                mech = "DV2_WRONG_VERTEX"
            else:
                mech = "OTHER"
        fa = A["D"][i] if gain else A["O"][i]       # the accessible arm
        sel_sh = [s for s in pool(fa) if s["E"] > 20 and s["pdg"] == 11]
        lead = max(sel_sh, key=lambda s: s["E"]) if sel_sh else None
        em_main = em_frac_in(fa, (d if gain else o)["em"], fa["final_main"])
        ch.append({"evt_idx": i, "background": rs, "direction": "GAIN" if gain else "LOSS", "O_access": cO, "D_access": cD,
                   "O_vertex_truth_dist_cm": o["s"]["truth_dist"], "D_vertex_truth_dist_cm": d["s"]["truth_dist"],
                   "O_vertex_truth_dist_sce_cm": o["s"]["truth_dist_sce"], "D_vertex_truth_dist_sce_cm": d["s"]["truth_dist_sce"],
                   "O_vertex_ok": o["vok"], "D_vertex_ok": d["vok"],
                   "O_main_cluster": o["s"]["final_main"], "D_main_cluster": d["s"]["final_main"],
                   "accessible_arm_shower_E_MeV": lead["E"] if lead else None,
                   "O_pool_gt20MeV": ";".join(f"{s['E']:.1f}/{s['pdg']}" for s in bO),
                   "D_pool_gt20MeV": ";".join(f"{s['E']:.1f}/{s['pdg']}" for s in bD),
                   "O_A5": a5_str(o["a5"]), "D_A5": a5_str(d["a5"]),
                   "O_fix2": f"fallback={o['s']['fix2_fallback']} added={o['s']['n_neighbor_added']}",
                   "D_fix2": f"fallback={d['s']['fix2_fallback']} added={d['s']['n_neighbor_added']}",
                   "truth_em": ";".join(d["em"].get("em_names", [])),
                   "accessible_arm_em_q_frac_in_main": em_frac_in(fa, (d if gain else o)["em"], fa["final_main"]),
                   "detached_cluster": (em_main is not None and em_main < 0.5 and ((d if gain else o)["em"].get("n_em_gt20") or 0) > 0),
                   "O_stage": o["stage"], "D_stage": d["stage"], "selected_O": i in selO, "selected_D": i in selD,
                   "mechanism": mech})
    if ch:
        write_csv(f"{outdir}/{rs}_access_changes.csv", ch, list(ch[0].keys()))
    else:
        write_csv(f"{outdir}/{rs}_access_changes.csv", [{"evt_idx": "", "mechanism": "NO_ACCESS_CHANGES"}], ["evt_idx", "mechanism"])
    res["access_changes"] = collections.Counter(r["mechanism"] for r in ch)
    res["access_gain_events"] = [r["evt_idx"] for r in ch if r["direction"] == "GAIN"]
    res["access_loss_events"] = [r["evt_idx"] for r in ch if r["direction"] == "LOSS"]

    # ------------------------------------------------ A5
    a5r = []
    fO = {i for i in idxs if V["O"][i]["a5"]}
    fD = {i for i in idxs if V["D"][i]["a5"]}
    for i in sorted(fO | fD):
        o, d = V["O"][i], V["D"][i]
        acc_ch = (o["s"]["shw_sp_filled"] == 1) != (d["s"]["shw_sp_filled"] == 1)
        a5r.append({"evt_idx": i, "background": rs, "A5_in_O": i in fO, "A5_in_D": i in fD,
                    "set": "BOTH" if i in fO and i in fD else ("O_ONLY" if i in fO else "D_ONLY"),
                    "O_vertex": o["s"]["nu_xyz"], "D_vertex": d["s"]["nu_xyz"],
                    "O_truth_dist_cm": o["s"]["truth_dist"], "D_truth_dist_cm": d["s"]["truth_dist"],
                    "O_A5_retypes": a5_str(o["a5"]), "D_A5_retypes": a5_str(d["a5"]),
                    "O_pool_gt20MeV": ";".join(f"{s['E']:.1f}/{s['pdg']}" for s in pool(A["O"][i]) if s["E"] > 20),
                    "D_pool_gt20MeV": ";".join(f"{s['E']:.1f}/{s['pdg']}" for s in pool(A["D"][i]) if s["E"] > 20),
                    "O_access": o["s"]["access"], "D_access": d["s"]["access"], "accessibility_changed": acc_ch,
                    **{f"{m}_O_D": f"{cell(o['s'].get(m + '_score'))}->{cell(d['s'].get(m + '_score'))}" for m in MODELS},
                    "O_stage": o["stage"], "D_stage": d["stage"], "selected_O": i in selO, "selected_D": i in selD,
                    "A5_differs_and_changes_outcome": ((i in fO) != (i in fD)) and (acc_ch or o["stage"] != d["stage"])})
    res["a5"] = dict(n_candidates_O=sum(1 for i in idxs if V["O"][i]["s"]["has_tagger"]),
                     fires_O=len(fO), fires_D=len(fD), both=len(fO & fD), O_only=len(fO - fD), D_only=len(fD - fO),
                     O_only_events=sorted(fO - fD), D_only_events=sorted(fD - fO),
                     differs_and_changes_outcome=[r["evt_idx"] for r in a5r if r["A5_differs_and_changes_outcome"]])
    write_csv(f"{outdir}/{rs}_a5.csv", a5r if a5r else [{"evt_idx": "", "set": "NONE"}],
              list(a5r[0].keys()) if a5r else ["evt_idx", "set"])

    # ------------------------------------------------ Fix2
    fx = []
    for i in idxs:
        o, d = V["O"][i], V["D"][i]
        if "ONE_HOP" not in (o["s"]["access"], d["s"]["access"]):
            continue
        for k, v in (("O", o), ("D", d)):
            if v["s"]["access"] != "ONE_HOP":
                continue
            nb = [s for s in (A[k][i]["sa"]["neighbor_list"] or []) if s["E"] > 20 and s["pdg"] == 11]
            lead = max(nb, key=lambda s: s["E"]) if nb else None
            nem = v["em"].get("n_em_gt20") or 0
            fx.append({"evt_idx": i, "background": rs, "arm": k, "access": "ONE_HOP",
                       "other_arm_access": (d if k == "O" else o)["s"]["access"],
                       "fix2_neighbor_shower_E_MeV": lead["E"] if lead else None, "n_neighbor_added": v["s"]["n_neighbor_added"],
                       "truth_n_em_gt20_in_interaction": nem, "truth_em": ";".join(v["em"].get("em_names", [])),
                       "plausible_em": ("TRUTH_EM_PRESENT" if nem > 0 else "NO_TRUTH_EM_ACCIDENTAL_ASSOCIATION"),
                       "required_to_enter_bdts": True, "stage": v["stage"], "selected": i in (selO if k == "O" else selD),
                       "truth_dist_cm": v["s"]["truth_dist"]})
    res["fix2"] = {k: collections.Counter(V[k][i]["s"]["access"] for i in idxs) for k in ("O", "D")}
    res["fix2_onehop_events"] = {k: [i for i in idxs if V[k][i]["s"]["access"] == "ONE_HOP"] for k in ("O", "D")}
    res["fix2_onehop_selected"] = {k: [i for i in res["fix2_onehop_events"][k] if i in (selO if k == "O" else selD)] for k in ("O", "D")}
    res["fix2_onehop_plausibility"] = {k: collections.Counter(r["plausible_em"] for r in fx if r["arm"] == k) for k in ("O", "D")}
    write_csv(f"{outdir}/{rs}_fix2.csv", fx if fx else [{"evt_idx": "", "arm": "NONE"}],
              list(fx[0].keys()) if fx else ["evt_idx", "arm"])

    # ------------------------------------------------ newly selected / rejected
    def audit(i, kind):
        o, d, r = V["O"][i], V["D"][i], M[i]
        if kind == "NEW":
            if d["s"]["access"] == "ONE_HOP" and o["s"]["access"] != "ONE_HOP":
                cls = "FIX2_ASSOCIATION"
            elif bool(o["a5"]) != bool(d["a5"]):
                cls = "A5_EFFECT"
            elif not d["vok"]:
                cls = "WRONG_VERTEX"
            elif (r["D_em_q_frac_in_main"] is not None and r["D_em_q_frac_in_main"] < 0.5 and (d["em"].get("n_em_gt20") or 0) > 0
                  and r["O_main_cluster"] != r["D_main_cluster"]):
                cls = "DETACHED_EM_ASSOCIATION"
            elif o["failed"] == "9_shw_sp_n_20br1_eq1":
                cls = "MULTIPLICITY_CHANGE"
            elif d["vok"]:
                cls = "GOOD_RECONSTRUCTION_BUT_BDT_LEAKAGE"
            else:
                cls = "OTHER"
        else:
            if d["s"]["shw_sp_filled"] != 1:
                cls = "ACCESSIBILITY_LOSS" + ("_A5" if d["a5"] and not o["a5"] else "")
            elif d["failed"] == "9_shw_sp_n_20br1_eq1":
                cls = "MULTIPLICITY_CHANGE"
            elif d["vok"] and not o["vok"]:
                cls = "VERTEX_CORRECTED_BDT_REJECTS"
            else:
                cls = "BDT_SCORE_CHANGE"
        t = tlist[i]
        return {"evt_idx": i, "background": rs, "rse": t["rse"],
                "truth_topology": f"{t['mode']} Enu={t['nu_E_GeV']} lepE={t['lepton_E_GeV']} npi0={t['n_pi0']} npipm={t['n_pipm']} "
                                  f"np35={t['n_proton_ke35']}" + (f" mu_len={t.get('g4_muon_straight_len_cm','')}" if rs == "numucc" else
                                                                  f" g1={t.get('g4_gamma1_E_GeV','')}@{t.get('g4_gamma1_conv_cm','')}cm"
                                                                  f" g2={t.get('g4_gamma2_E_GeV','')}@{t.get('g4_gamma2_conv_cm','')}cm"),
                "true_vertex": (t["vtx_x"], t["vtx_y"], t["vtx_z"]), "O_vertex": o["s"]["nu_xyz"], "D_vertex": d["s"]["nu_xyz"],
                "O_truth_dist_cm": o["s"]["truth_dist"], "D_truth_dist_cm": d["s"]["truth_dist"],
                "D_truth_dist_sce_cm": d["s"]["truth_dist_sce"],
                "O_main_cluster": o["s"]["final_main"], "D_main_cluster": d["s"]["final_main"],
                "O_main_contains_tv": r["O_main_contains_true_vertex"], "D_main_contains_tv": r["D_main_contains_true_vertex"],
                "truth_em": r["truth_em"], "O_em_q_frac_in_main": r["O_em_q_frac_in_main"], "D_em_q_frac_in_main": r["D_em_q_frac_in_main"],
                "O_access": o["s"]["access"], "D_access": d["s"]["access"],
                "fix2_involvement": f"O:{o['s']['access']}/fb={o['s']['fix2_fallback']} D:{d['s']['access']}/fb={d['s']['fix2_fallback']}",
                "A5_involvement": f"O:[{a5_str(o['a5'])}] D:[{a5_str(d['a5'])}]",
                **{f"{m}_O": o["s"].get(f"{m}_score") for m in MODELS}, **{f"{m}_D": d["s"].get(f"{m}_score") for m in MODELS},
                "O_n20": o["s"]["n20"], "D_n20": d["s"]["n20"], "O_n20br1": o["s"]["n20br1"], "D_n20br1": d["s"]["n20br1"],
                "O_proton_category": o["s"].get("proton_category"), "D_proton_category": d["s"].get("proton_category"),
                "O_first_cut_failed": o["failed"], "D_first_cut_failed": d["failed"],
                "why": (f"O stopped at {o['failed'] or 'none'}; D passes all pre-FV cuts" if kind == "NEW" else
                        f"O passed all; D stops at {d['failed']}"),
                "classification": cls}
    new = [audit(i, "NEW") for i in sorted(selD - selO)]
    rej = [audit(i, "REJ") for i in sorted(selO - selD)]
    for nm, rows in (("newly_selected", new), ("rejected_by_dv2", rej)):
        write_csv(f"{outdir}/{rs}_{nm}.csv", rows if rows else [{"evt_idx": "", "classification": "NONE"}],
                  list(rows[0].keys()) if rows else ["evt_idx", "classification"])
    res["newly_selected"] = {r["evt_idx"]: r["classification"] for r in new}
    res["rejected_by_dv2"] = {r["evt_idx"]: r["classification"] for r in rej}
    res["access"] = {k: collections.Counter(V[k][i]["s"]["access"] for i in idxs) for k in ("O", "D")}
    res["shw_sp_filled"] = {k: sum(1 for i in idxs if V[k][i]["s"]["shw_sp_filled"] == 1) for k in ("O", "D")}
    res["bdt_evaluable"] = {k: sum(1 for i in idxs if V[k][i]["s"].get("all4_evaluable")) for k in ("O", "D")}
    res["n_candidates"] = {k: sum(1 for i in idxs if V[k][i]["s"]["has_tagger"]) for k in ("O", "D")}
    write_json(f"{outdir}/{rs}_summary.json", res)
    print(json.dumps(L.to_py({k: v for k, v in res.items() if k not in ("events",)}), indent=1)[:9000])


if __name__ == "__main__":
    main()
