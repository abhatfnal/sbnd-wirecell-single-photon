#!/usr/bin/env python3
"""Assemble the required background-validation tables from the per-runset run_bg.py outputs.

Inputs (written by run_bg.py; nothing is recomputed here except counts / binomial errors):
  tables/{numucc,ncpi0}_{cutflow,score_migration,access_changes,a5,fix2,newly_selected,rejected_by_dv2,run_gate}.csv
  tables/{numucc,ncpi0}_summary.json
  tables/_work/control_{numucc,ncpi0}/{rs}_control_F_vs_O.csv   (Stage-1 F,O,D pass)
  SIGW/tables/summary.json, SIGW/tables/cutflow_original_vs_dv2.csv   (signal study, read-only)
Outputs (tables/): control_validation, a5_background_comparison, fix2_background_comparison,
  newly_selected_backgrounds, backgrounds_rejected_by_dv2, signal_background_summary (+ summary.json).
  + vertex_comparison (signal 59 from SIGW event59_original_vs_dv2.csv, same vstats definition as run_bg.py).
The per-runset cutflow / score_migration / access_changes files ARE the required numucc_* / ncpi0_* tables.
No normalization (POT, flux, exposure) is applied anywhere: fractions are per processed truth-class event.
"""
import csv, json, math, os, datetime

W = "/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/dv2max_background_validation_20261102"
SIGW = "/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/dv2max_singlephoton59_20261102"
T = f"{W}/tables"
RS = ("numucc", "ncpi0")


def rd(p):
    return list(csv.DictReader(open(p)))


def wr(p, rows, keys=None):
    keys = keys or (list(rows[0].keys()) if rows else ["empty"])
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    print("wrote", os.path.relpath(p, W), len(rows), "rows")


def frac(k, n):
    if not n:
        return "", ""
    p = k / n
    return f"{p:.4f}", f"{math.sqrt(p * (1 - p) / n):.4f}"


def combine(name, out, tag):
    rows = []
    for rs in RS:
        for r in rd(f"{T}/{rs}_{name}.csv"):
            if r.get("evt_idx", "") == "":
                continue  # NONE / NO_ACCESS_CHANGES placeholder
            rows.append({"background": rs, **r})
    if not rows:
        rows = [{"background": "", tag: "NONE"}]
    keys = []
    for r in rows:
        keys += [k for k in r if k not in keys]
    wr(f"{T}/{out}.csv", rows, keys)
    return rows


# --------------------------------------------------------------- control
ctrl = []
for rs in RS:
    p = f"{T}/_work/control_{rs}/{rs}_control_F_vs_O.csv"
    gate = {r["evt_idx"]: r for r in rd(f"{T}/_work/control_{rs}/{rs}_run_gate.csv")}
    for r in rd(p):
        g = gate[r["evt_idx"]]
        ctrl.append({"background": rs, "evt_idx": r["evt_idx"], "rse": g["rse"], "F_lar_exit": g["F_lar_exit"],
                     "O_lar_exit": g["O_lar_exit"], "F_lib_md5": g["F_lib_md5"], "O_lib_md5": g["O_lib_md5"],
                     **{k: r[k] for k in r if k not in ("evt_idx", "run", "subrun", "event")}})
wr(f"{T}/control_validation.csv", ctrl)

# --------------------------------------------------------------- combined per-event tables
a5 = combine("a5", "a5_background_comparison", "set")
fx = combine("fix2", "fix2_background_comparison", "arm")
ns = combine("newly_selected", "newly_selected_backgrounds", "classification")
rj = combine("rejected_by_dv2", "backgrounds_rejected_by_dv2", "classification")

# --------------------------------------------------------------- signal vs background
sig = json.load(open(f"{SIGW}/tables/summary.json"))
S = {rs: json.load(open(f"{T}/{rs}_summary.json")) for rs in RS}
CF = {rs: {r["step"]: r for r in rd(f"{T}/{rs}_cutflow.csv")} for rs in RS}
SCF = {r["step"]: r for r in rd(f"{SIGW}/tables/cutflow_original_vs_dv2.csv")}
rows = []
steps = [r["step"] for r in rd(f"{T}/numucc_cutflow.csv")]
for st in steps:
    r = {"step": st, "description": CF["numucc"][st]["description"]}
    sn = int(SCF[st]["O_count"]) if st in SCF else None
    for arm in ("O", "D"):
        k = int(SCF[st][f"{arm}_count"])
        r[f"signal_{arm}"] = k
        r[f"signal_{arm}_frac"], r[f"signal_{arm}_frac_err"] = frac(k, int(SCF["1_total"][f"{arm}_count"]))
    for rs in RS:
        tot = int(CF[rs]["1_total"]["O_count"])
        for arm in ("O", "D"):
            k = int(CF[rs][st][f"{arm}_count"])
            r[f"{rs}_{arm}"] = k
            r[f"{rs}_{arm}_frac"], r[f"{rs}_{arm}_frac_err"] = frac(k, tot)
    for c in ("signal",) + RS:   # relative O -> D change (counts on the same events)
        r[f"{c}_D_minus_O"] = r[f"{c}_D"] - r[f"{c}_O"]
        r[f"{c}_D_over_O"] = f"{r[f'{c}_D'] / r[f'{c}_O']:.3f}" if r[f"{c}_O"] else ("inf" if r[f"{c}_D"] else "")
    rows.append(r)
last = steps[-1]
for arm in ("O", "D"):
    r = {"step": f"ratio_final_{arm}", "description": f"arm {arm}: final-step fraction, signal / background (per processed event, NOT normalized)"}
    sfr = int(SCF[last][f"{arm}_count"]) / int(SCF["1_total"][f"{arm}_count"])
    for rs in RS:
        bfr = int(CF[rs][last][f"{arm}_count"]) / int(CF[rs]["1_total"]["O_count"])
        r[f"{rs}_{arm}_frac"] = f"{sfr / bfr:.3f}" if bfr else "inf (0 background selected)"
    rows.append(r)
keys = []
for r in rows:
    keys += [k for k in r if k not in keys]
wr(f"{T}/signal_background_summary.csv", rows, keys)

# --------------------------------------------------------------- vertex quality: signal vs backgrounds (section 15)
def vstats(vals):  # same definition as run_bg.py vstats
    v = sorted(float(x) for x in vals if x not in ("", "None", None))
    if not v:
        return {}
    import numpy as np
    a = np.asarray(v)
    return dict(n=len(v), median=float(np.median(a)), q68=float(np.quantile(a, 0.68)),
                lt1=float(np.mean(a < 1)), lt3=float(np.mean(a < 3)), lt5=float(np.mean(a < 5)), gt20=float(np.mean(a > 20)))


E59 = rd(f"{SIGW}/tables/event59_original_vs_dv2.csv")
VX = {"signal_ncdelta": {a: {"true": vstats(r[f"{a}_vertex_truth_dist_cm"] for r in E59),
                             "sce": vstats(r[f"{a}_vertex_truth_dist_sce_cm"] for r in E59)} for a in ("O", "D")}}
VX.update({rs: S[rs]["vertex"] for rs in RS})
vrows = []
for smp, v in VX.items():
    for frame in ("true", "sce"):
        for arm in ("O", "D"):
            d = v[arm][frame]
            vrows.append({"sample": smp, "frame": frame, "arm": arm, **{k: (f"{d[k]:.4f}" if k != "n" else d[k]) for k in d}})
wr(f"{T}/vertex_comparison.csv", vrows)

summary = dict(
    generated_utc=datetime.datetime.utcnow().isoformat() + "Z",
    normalization="NONE: fractions are per processed truth-class event; no POT / flux / exposure weighting; "
                  "no sensitivity or significance computed",
    signal=dict(n=59, selected_O=sig["selected"]["O"], selected_D=sig["selected"]["D"], cutflow_O=sig["cutflow"]["O"],
                cutflow_D=sig["cutflow"]["D"]),
    control=dict(n=len(ctrl), verdicts={v: sum(1 for c in ctrl if c["verdict"] == v) for v in {c["verdict"] for c in ctrl}}),
    backgrounds={rs: {k: S[rs][k] for k in S[rs] if k not in ("events",)} for rs in RS},
    n_events={rs: len(S[rs]["events"]) for rs in RS},
    vertex_comparison=VX,
    tables=dict(a5_rows=len(a5), fix2_rows=len(fx), newly_selected_rows=len(ns), rejected_rows=len(rj)),
)
json.dump(summary, open(f"{T}/summary.json", "w"), indent=1, default=str)
print("wrote tables/summary.json")
