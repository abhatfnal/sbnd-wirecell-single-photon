#!/usr/bin/env python3
"""Diagnostic (section 13 / 27): O -> D shift of every MicroBooNE SP-BDT INPUT variable, per sample, on the events
whose four BDTs are evaluable in BOTH arms.  The scorer's read_event / collect_inputs / MODELS are exec'd VERBATIM from
the frozen score_microboone_bdts.py (source up to score_all(); BASEDIR set per arm), so the inputs are exactly what the
BDTs see; "evaluable" = score_all()'s rule (candidate, shw_sp_filled != 0, all inputs finite).  Samples: NC-Delta signal 59 (SIGW runs, read-only), numucc 400, ncpi0 214 (W runs).
Outputs: tables/bdt_input_shift.csv (sample x variable) and tables/bdt_input_shift_crosssample.csv (variable rows,
paired net direction P(D>O)-P(D<O) side by side + direction pattern).  Per-event inputs cached in
tables/_work/bdt_inputs_cache.pkl (--reuse).  Truth is not used.
Usage: python3 bdt_input_shift.py [--procs 8]
"""
import os, sys, csv, math, argparse, collections, pickle
import multiprocessing as mp
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ab_lib as L   # noqa: E402

W = L.S
SAMPLES = {"signal_ncdelta": (f"{L.SIGW}/runs/main/arm{{arm}}/wirecell", 59),
           "numucc": (f"{W}/runs/numucc/arm{{arm}}/wirecell", 400),
           "ncpi0": (f"{W}/runs/ncpi0/arm{{arm}}/wirecell", 214)}
_src = open(L.SCORER_PY).read()
NS = {"__name__": "scorer_inputs_only", "__file__": os.path.join(HERE, "score_microboone_bdts_inputs_exec.py")}
exec(compile(_src[:_src.index("def score_all():")], "score_microboone_bdts[..score_all]", "exec"), NS)
MODELS = NS["MODELS"]
VARS = {}
for m in L.BDT_MODELS:
    for _, v in MODELS[m].var_list:
        VARS.setdefault(v, []).append(m)


def one(job):
    basedir, idx = job
    NS["BASEDIR"] = basedir
    tag, kine, meta = NS["read_event"](idx)
    if tag is None:
        return None
    vals, ok = {}, meta["shw_sp_filled"] != 0   # score_all(): shw_sp_filled == 0 -> MAIN_VERTEX_SHOWER_INACCESSIBLE
    for m in L.BDT_MODELS:
        v, issues = NS["collect_inputs"](m, tag, kine)
        ok &= NS["is_evaluable"](v, issues)
        for (i, name) in MODELS[m].var_list:
            vals.setdefault(name, v[i])
    return {"ok": ok, "vals": vals}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--procs", type=int, default=8)
    ap.add_argument("--reuse", action="store_true", help="reuse tables/_work/bdt_inputs_cache.pkl (per-event inputs)")
    a = ap.parse_args()
    cache = f"{W}/tables/_work/bdt_inputs_cache.pkl"
    if a.reuse and os.path.isfile(cache):
        RR = pickle.load(open(cache, "rb"))
    else:
        RR = {}
        with mp.get_context("fork").Pool(a.procs) as pool:
            for smp, (tmpl, n) in SAMPLES.items():
                RR[smp] = {arm: pool.map(one, [(tmpl.format(arm=arm), i) for i in range(n)], chunksize=4) for arm in ("O", "D")}
        pickle.dump(RR, open(cache, "wb"))
    rows, cross = [], collections.defaultdict(dict)
    for smp, (tmpl, n) in SAMPLES.items():
        R = RR[smp]
        both = [i for i in range(n) if R["O"][i] and R["D"][i] and R["O"][i]["ok"] and R["D"][i]["ok"]]
        print(smp, "events", n, "evaluable in both arms", len(both), flush=True)
        for v, models in VARS.items():
            o = np.array([R["O"][i]["vals"][v] for i in both], float)
            d = np.array([R["D"][i]["vals"][v] for i in both], float)
            # robust, paired: net direction = P(D > O) - P(D < O) over the same events (outlier-proof; works for
            # discrete inputs).  Means are reported but not used for any conclusion (a few inputs have extreme values).
            net = float(np.mean(np.sign(d - o)))
            r = {"sample": smp, "variable": v, "models": "+".join(models), "n_both_evaluable": len(both),
                 "O_median": f"{np.median(o):.5g}", "D_median": f"{np.median(d):.5g}",
                 "median_of_delta": f"{np.median(d - o):.5g}", "frac_events_changed": f"{np.mean(d != o):.3f}",
                 "net_direction": f"{net:+.3f}", "frac_D_gt_O": f"{np.mean(d > o):.3f}", "frac_D_lt_O": f"{np.mean(d < o):.3f}",
                 "O_mean": f"{np.mean(o):.5g}", "D_mean": f"{np.mean(d):.5g}", "O_max_abs": f"{np.max(np.abs(o)):.5g}",
                 "D_max_abs": f"{np.max(np.abs(d)):.5g}"}
            rows.append(r)
            cross[v]["models"] = "+".join(models)
            cross[v][f"{smp}_frac_changed"] = r["frac_events_changed"]
            cross[v][f"{smp}_net_direction"] = r["net_direction"]
            cross[v][f"{smp}_O_median"], cross[v][f"{smp}_D_median"] = r["O_median"], r["D_median"]
    out = f"{W}/tables/bdt_input_shift.csv"
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("wrote", out, len(rows))
    ks = list(SAMPLES)
    crows = []
    for v, c in cross.items():
        s = [float(c[f"{k}_net_direction"]) for k in ks]
        c2 = {"variable": v, **c}
        c2["min_abs_net_direction"] = f"{min(abs(x) for x in s):.3f}"
        c2["direction_pattern"] = ("COMMON_UP" if all(x >= 0.1 for x in s) else "COMMON_DOWN" if all(x <= -0.1 for x in s)
                                   else "SIGNAL_ONLY" if abs(s[0]) >= 0.2 and all(abs(x) < 0.1 for x in s[1:])
                                   else "MIXED_OR_SMALL")
        crows.append(c2)
    crows.sort(key=lambda r: -abs(float(r["signal_ncdelta_net_direction"])))
    out2 = f"{W}/tables/bdt_input_shift_crosssample.csv"
    keys = []
    for r in crows:
        keys += [k for k in r if k not in keys]
    with open(out2, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(crows)
    print("wrote", out2, len(crows))
    M = np.array([[float(c[f"{k}_net_direction"]) for k in ks] for c in crows])
    print("variables:", len(M), "| direction patterns:", dict(collections.Counter(c["direction_pattern"] for c in crows)))
    for i in range(3):
        for j in range(i + 1, 3):
            print(f"  corr(net_direction {ks[i]}, {ks[j]}) = {np.corrcoef(M[:, i], M[:, j])[0, 1]:.3f}")
    for i, k in enumerate(ks):
        print(f"  {k}: variables with |net| >= 0.2: {int(np.sum(np.abs(M[:, i]) >= 0.2))}; median |net| {np.median(np.abs(M[:, i])):.3f}")


if __name__ == "__main__":
    main()
