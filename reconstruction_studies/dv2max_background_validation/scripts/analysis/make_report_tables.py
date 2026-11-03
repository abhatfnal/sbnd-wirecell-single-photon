#!/usr/bin/env python3
"""Render the markdown tables of docs/DV2MAX_SINGLEPHOTON_BACKGROUND_VALIDATION.md from the CSV / JSON outputs
(no number is typed by hand).  Signal numbers are read from SIGW (read-only); signal score shifts use the run_bg.py
definitions (median delta on both-evaluable events; cross = O <= cut < D).  Output: tables/_work/report_tables.md
"""
import csv, json, math, os
import numpy as np

W = "/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/dv2max_background_validation_20261102"
SIGW = "/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/dv2max_singlephoton59_20261102"
T = f"{W}/tables"
RS = ("numucc", "ncpi0")
TH = {"numu": 0.4, "other": 0.2, "ncpi0": -0.05, "nue": -1.0}
NAME = {"signal_ncdelta": "NC-Δ signal (59)", "numucc": "ν_μ CC (400)", "ncpi0": "NC π0 (214)"}
rd = lambda p: list(csv.DictReader(open(p)))
S = {rs: json.load(open(f"{T}/{rs}_summary.json")) for rs in RS}
out = []
P = out.append


def tbl(head, rows):
    P("| " + " | ".join(head) + " |")
    P("|" + "|".join("---" for _ in head) + "|")
    for r in rows:
        P("| " + " | ".join(str(x) for x in r) + " |")
    P("")


def pe(k, n):
    if not n:
        return "–"
    p = k / n
    return f"{100 * p:.1f} ± {100 * math.sqrt(p * (1 - p) / n):.1f}"


pct = lambda x: f"{100 * float(x):.1f}" if x not in ("", None) else "–"   # "% of previous" undefined after a 0 step

# ---------------------------------------------------------------- cutflows
for rs in RS:
    P(f"### cutflow {rs}")
    rows = []
    for r in rd(f"{T}/{rs}_cutflow.csv"):
        rows.append([r["step"].split("_", 1)[0] + ". " + r["description"], r["O_count"],
                     f"{100 * float(r['O_frac_total']):.1f} ± {100 * float(r['O_frac_total_err']):.1f}",
                     pct(r["O_frac_prev"]), r["D_count"],
                     f"{100 * float(r['D_frac_total']):.1f} ± {100 * float(r['D_frac_total_err']):.1f}",
                     pct(r["D_frac_prev"]), r["D_minus_O"],
                     f"+{len([x for x in r['D_gained_vs_O'].split(';') if x])}/−{len([x for x in r['D_lost_vs_O'].split(';') if x])}"])
    tbl(["step", "O", "O % of total", "O % of prev", "D", "D % of total", "D % of prev", "D−O", "gained/lost"], rows)

# ---------------------------------------------------------------- vertex
P("### vertex comparison")
rows = []
for r in rd(f"{T}/vertex_comparison.csv"):
    rows.append([NAME[r["sample"]], r["frame"], r["arm"], r["n"], f"{float(r['median']):.2f}", f"{float(r['q68']):.1f}",
                 f"{float(r['lt1']):.2f}", f"{float(r['lt3']):.2f}", f"{float(r['lt5']):.2f}", f"{float(r['gt20']):.2f}"])
tbl(["sample", "frame", "arm", "n cand", "median [cm]", "68% [cm]", "<1 cm", "<3 cm", "<5 cm", ">20 cm"], rows)

# ---------------------------------------------------------------- main cluster
P("### main cluster")
rows = []
for rs in RS:
    m = S[rs]["main_cluster"]
    rows.append([NAME[rs], m["n_tv_defined"], m["O_contains_tv"], m["D_contains_tv"], m["dv2_switches"], m["correct_switches"],
                 m["wrong_switches"], m["undetermined_switches"], m["switches_fixing_O"], m["switches_breaking_O"],
                 m["same_cluster_moves"]])
tbl(["sample", "true-vertex cluster defined", "O main ∋ tv", "D main ∋ tv", "DV2 switches", "correct", "wrong", "undet.",
     "fix O", "break O", "same-cluster moves"], rows)

# ---------------------------------------------------------------- signal score shifts (same definitions)
E59 = rd(f"{SIGW}/tables/event59_original_vs_dv2.csv")


def f_(x):
    try:
        return float(x) if x not in ("", "None", "nan") else None
    except ValueError:
        return None


SIGSH = {}
for m in TH:
    o = {int(r["evt_idx"]): f_(r[f"O_{m}_score"]) for r in E59 if r["O_all4_bdt_evaluable"] in ("1", "True")}
    d = {int(r["evt_idx"]): f_(r[f"D_{m}_score"]) for r in E59 if r["D_all4_bdt_evaluable"] in ("1", "True")}
    both = [i for i in o if i in d and o[i] is not None and d[i] is not None]
    SIGSH[m] = dict(n_both_evaluable=len(both), median_delta=float(np.median([d[i] - o[i] for i in both])),
                    O_pass_all=sum(1 for v in o.values() if v is not None and v > TH[m]),
                    D_pass_all=sum(1 for v in d.values() if v is not None and v > TH[m]),
                    cross_up_both_evaluable=[i for i in both if o[i] <= TH[m] < d[i]],
                    cross_down_both_evaluable=[i for i in both if d[i] <= TH[m] < o[i]],
                    O_median=float(np.median([v for v in o.values() if v is not None])),
                    D_median=float(np.median([v for v in d.values() if v is not None])))
json.dump(SIGSH, open(f"{T}/_work/signal_score_shift.json", "w"), indent=1)
P("### score shifts (BDT evaluable; pass = score above its cut, not cumulative)")
rows = []
for m in TH:
    for smp, sh in (("signal_ncdelta", SIGSH[m]),) + tuple((rs, S[rs]["score_shift"][m]) for rs in RS):
        rows.append([f"{m} (> {TH[m]})", NAME[smp], sh["n_both_evaluable"], f"{sh['O_median']:+.3f}", f"{sh['D_median']:+.3f}",
                     f"{sh['median_delta']:+.3f}", sh["O_pass_all"], sh["D_pass_all"],
                     len(sh["cross_up_both_evaluable"]), len(sh["cross_down_both_evaluable"])])
tbl(["BDT", "sample", "n both eval.", "O median", "D median", "median Δ", "O pass", "D pass", "cross up", "cross down"], rows)

# ---------------------------------------------------------------- access / fix2 / a5
P("### accessibility (Fix2 classes) and A5")
rows = []
for rs in RS:
    s = S[rs]
    for k in ("O", "D"):
        f = s["fix2"][k]
        rows.append([NAME[rs], k, s["n_candidates"][k], f.get("DIRECT", 0), f.get("ONE_HOP", 0), f.get("INACCESSIBLE", 0),
                     s["shw_sp_filled"][k], s["bdt_evaluable"][k], s["a5"][f"fires_{k}"]])
tbl(["sample", "arm", "candidates", "DIRECT", "ONE_HOP", "INACCESSIBLE", "shw_sp_filled", "BDT evaluable", "A5 fires"], rows)
rows = []
for rs in RS:
    a = S[rs]["a5"]
    rows.append([NAME[rs], a["fires_O"], a["fires_D"], a["both"], a["O_only"], a["D_only"], len(a["differs_and_changes_outcome"])])
tbl(["sample", "A5 fires O", "A5 fires D", "both", "O only", "D only", "differs & changes outcome"], rows)
P("### access-change mechanisms")
rows = []
for rs in RS:
    ac = rd(f"{T}/{rs}_access_changes.csv")
    ac = [r for r in ac if r.get("evt_idx", "") != ""]
    mech = {}
    for r in ac:
        mech.setdefault((r["direction"], r["mechanism"]), []).append(r["evt_idx"])
    for (dr, mc), ev in sorted(mech.items()):
        rows.append([NAME[rs], dr, mc, len(ev), ", ".join(ev)])
tbl(["sample", "direction", "mechanism", "n", "events"], rows)

# ---------------------------------------------------------------- migration classes
P("### score-migration classes")
cls = ["NO_CHANGE", "IMPROVED_BACKGROUND_REJECTION", "WORSE_BACKGROUND_REJECTION", "ACCESSIBILITY_GAIN_ONLY",
       "ACCESSIBILITY_LOSS", "TOPOLOGY_CHANGE", "OTHER"]
tbl(["sample"] + cls, [[NAME[rs]] + [S[rs]["migration_classes"].get(c, 0) for c in cls] for rs in RS])

# ---------------------------------------------------------------- signal vs background (section 23)
P("### signal vs background (section 23; counts, % of processed events ± binomial; NOT normalized)")
sb = {r["step"]: r for r in rd(f"{T}/signal_background_summary.csv")}
steps = [("2_neutrino_candidate", "candidate"), ("4_all_4_bdts_evaluable", "BDT evaluable"), ("5_numu_gt0p4", "numu pass"),
         ("6_other_gt0p2", "other pass"), ("7_ncpi0_gtneg0p05", "ncpi0 pass"), ("8_nue_gtneg1p0", "nue pass"),
         ("9_shw_sp_n_20br1_eq1", "exactly-one (selected)")]
N = {"signal": 59, "numucc": len(S["numucc"]["events"]), "ncpi0": len(S["ncpi0"]["events"])}
rows = []
for st, lab in steps:
    r = sb[st]
    row = [lab]
    for c in ("signal",) + RS:
        o, d = int(r[f"{c}_O"]), int(r[f"{c}_D"])
        row += [f"{o} ({pe(o, N[c])})", f"{d} ({pe(d, N[c])})", r[f"{c}_D_over_O"]]
    rows.append(row)
tbl(["cumulative step", "signal O", "signal D", "sig D/O", "ν_μ CC O", "ν_μ CC D", "ν_μ CC D/O", "NC π0 O", "NC π0 D", "NC π0 D/O"], rows)

# ---------------------------------------------------------------- BDT input shifts (bdt_input_shift.py)
P("### BDT-input shifts: paired net direction P(D>O) − P(D<O), events evaluable in both arms")
X = rd(f"{T}/bdt_input_shift_crosssample.csv")
nb = {r["sample"]: r["n_both_evaluable"] for r in rd(f"{T}/bdt_input_shift.csv")}
ks = ("signal_ncdelta", "numucc", "ncpi0")
M = np.array([[float(r[f"{k}_net_direction"]) for k in ks] for r in X])
rows = [[NAME[k] + f" (n={nb[k]})", int(np.sum(np.abs(M[:, i]) >= 0.2)), f"{np.median(np.abs(M[:, i])):.3f}"] for i, k in enumerate(ks)]
tbl(["sample", "inputs with abs(net) ≥ 0.2 (of 217)", "median abs(net)"], rows)
cc = [[f"{np.corrcoef(M[:, i], M[:, j])[0, 1]:.2f}" for j in range(3)] for i in range(3)]
tbl(["corr of net direction", "signal", "ν_μ CC", "NC π0"], [[NAME[k]] + cc[i] for i, k in enumerate(ks)])
from collections import Counter
P("direction patterns over the 217 inputs: " + ", ".join(f"{k} {v}" for k, v in Counter(r["direction_pattern"] for r in X).most_common()))
P("")
rows = []
for r in X[:16]:
    rows.append([f"`{r['variable']}`", r["models"]] + [f"{r[f'{k}_net_direction']} ({r[f'{k}_O_median']}→{r[f'{k}_D_median']})" for k in ks]
                + [r["direction_pattern"]])
tbl(["input", "BDTs", "signal net (median O→D)", "ν_μ CC net", "NC π0 net", "pattern"], rows)

open(f"{T}/_work/report_tables.md", "w").write("\n".join(out) + "\n")
print("wrote tables/_work/report_tables.md", len(out), "lines")
