#!/usr/bin/env python3
"""
generate_bdt_comparison.py — Parts H, I of the 59-event Fix2-v2 A/B study.

Loads the existing validated MicroBooNE BDT scorer (analysis/microboone_1gamma_v0/)
and re-scores the patched tracking-pr.root outputs from ab59/wirecell/.

Merges with existing baseline scores and writes:
    fix2_ab59_bdt_comparison.csv   (Part H)
    fix2_ab59_cutflow.csv          (Part I)

Usage:
    cd .../development/fix2_vertex_shower_onehop_20261005/ab59/tables/
    python3 generate_bdt_comparison.py
"""

import sys, os, csv, math
import importlib.util
import numpy as np

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE = "/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon"
SCORER_DIR  = f"{BASE}/analysis/microboone_1gamma_v0"
BASEDIR     = f"{BASE}/baseline_v0/ncdelta_50evt/wirecell"
PATCHDIR    = f"{BASE}/development/fix2_vertex_shower_onehop_20261005/ab59/wirecell"
BASELINE_SCORES = f"{SCORER_DIR}/tables/ncdelta_microboone_bdt_scores.csv"
OUTDIR = os.path.dirname(__file__)
N_EVENTS = 59

# ---------------------------------------------------------------------------
# Import the existing scorer's TMVA evaluator and input collectors
# (we'll import the module but override BASEDIR before calling score_all)
# ---------------------------------------------------------------------------
spec = importlib.util.spec_from_file_location(
    "scorer", os.path.join(SCORER_DIR, "score_microboone_bdts.py"))
mod = importlib.util.module_from_spec(spec)

# Monkey-patch BASEDIR before executing the module's top-level code
# by overriding sys.modules and setting the attribute
# The scorer prints to stdout and writes files on import; we capture by
# redirecting at module level — simpler to just re-use its components.

# Shorter approach: directly import only the shared functions by exec'ing
# the module with modified BASEDIR, catching the side effects.
# Even simpler: adapt the scorer minimally.

# Read the scorer source, replace BASEDIR, run it in a clean namespace
with open(os.path.join(SCORER_DIR, "score_microboone_bdts.py")) as fh:
    src = fh.read()

# Replace the BASEDIR line to point to patched outputs
src_patched = src.replace(
    'BASEDIR = ("/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/baseline_v0/"\n'
    '           "ncdelta_50evt/wirecell")',
    f'BASEDIR = "{PATCHDIR}"'
)
# Replace OUTDIR to redirect CSV writes to ab59/tables
src_patched = src_patched.replace(
    'OUTDIR  = os.path.join(os.path.dirname(__file__), "tables")',
    f'OUTDIR = "{OUTDIR}"'
)
# Rename output files so we don't overwrite baseline
src_patched = src_patched.replace(
    '"ncdelta_microboone_bdt_scores.csv"',
    '"fix2_ab59_patched_bdt_scores.csv"'
)
src_patched = src_patched.replace(
    '"ncdelta_reco_failure_taxonomy.csv"',
    '"fix2_ab59_patched_taxonomy.csv"'
)
src_patched = src_patched.replace(
    '"ncdelta_microboone_cutflow.csv"',
    '"fix2_ab59_patched_cutflow.csv"'
)
# Suppress the final 'Scoring 59 NC Delta events...' print at module level
# by checking that score_rows are exported
src_patched = src_patched.replace(
    'print("Scoring 59 NC Delta events...", flush=True)\n'
    'score_rows = score_all()',
    'print("Scoring 59 patched events (Fix2-v2)...", flush=True)\n'
    'score_rows = score_all()'
)

print("Executing adapted scorer on patched outputs...")
ns = {}
exec(compile(src_patched, "score_patched", "exec"), ns)
patched_rows = ns.get("score_rows", [])
print(f"Patched: {len(patched_rows)} events scored")

# ---------------------------------------------------------------------------
# Load baseline scores (already computed)
# ---------------------------------------------------------------------------
baseline_rows = {}
with open(BASELINE_SCORES, newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        baseline_rows[int(row["evt_idx"])] = row

print(f"Baseline: {len(baseline_rows)} events loaded")

# ---------------------------------------------------------------------------
# Part H: Build BDT comparison table
# ---------------------------------------------------------------------------
MODELS = ["numu", "other", "ncpi0", "nue"]

def get_score(row, model):
    s = row.get(f"{model}_bdt_score", "")
    return float(s) if s not in ("", None) else None

def get_evaluable(row, model):
    return int(row.get(f"{model}_bdt_evaluable", 0) or 0)

comparison_rows = []
for p in patched_rows:
    idx = int(p["evt_idx"])
    b = baseline_rows.get(idx, {})

    row = {
        "evt_idx":  idx,
        "run":      p.get("run", ""),
        "subrun":   p.get("subrun", ""),
        "event":    p.get("event", ""),
        # Filled status
        "baseline_shw_sp_filled":  b.get("shw_sp_filled", "NA"),
        "patched_shw_sp_filled":   p.get("shw_sp_filled", "NA"),
        "baseline_shw_sp_n_20mev": b.get("shw_sp_n_20mev_showers", "NA"),
        "patched_shw_sp_n_20mev":  p.get("shw_sp_n_20mev_showers", "NA"),
        "baseline_shw_sp_n_20br1": b.get("shw_sp_n_20br1_showers", "NA"),
        "patched_shw_sp_n_20br1":  p.get("shw_sp_n_20br1_showers", "NA"),
        "baseline_shw_sp_energy":  b.get("shw_sp_energy", "NA"),
        "patched_shw_sp_energy":   p.get("shw_sp_energy", "NA"),
        "baseline_proton_cat":     b.get("proton_category", "NA"),
        "patched_proton_cat":      p.get("proton_category", "NA"),
    }

    for model in MODELS:
        be = get_evaluable(b, model)
        pe = get_evaluable(p, model)
        bs = get_score(b, model)
        ps = get_score(p, model)
        row[f"baseline_{model}_evaluable"] = be
        row[f"patched_{model}_evaluable"]  = pe
        row[f"baseline_{model}_score"]     = f"{bs:.6f}" if bs is not None else ""
        row[f"patched_{model}_score"]      = f"{ps:.6f}" if ps is not None else ""
        row[f"{model}_evaluability_changed"] = 1 if be != pe else 0
        if bs is not None and ps is not None:
            row[f"{model}_score_delta"] = f"{ps-bs:+.6f}"
        else:
            row[f"{model}_score_delta"] = ""

    row["notes"] = ""
    if idx == 14: row["notes"] = "signal: expected recovery, shw_sp_filled 0->1"
    elif idx == 20: row["notes"] = "signal: expected recovery, shw_sp_filled 0->1"
    elif idx == 58: row["notes"] = "companion-cluster: no recovery expected"
    elif idx == 54: row["notes"] = "downstream fail: no recovery expected"

    comparison_rows.append(row)

bdt_csv = os.path.join(OUTDIR, "fix2_ab59_bdt_comparison.csv")
fieldnames = list(comparison_rows[0].keys()) if comparison_rows else []
with open(bdt_csv, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(comparison_rows)
print(f"Written: {bdt_csv}")

# ---------------------------------------------------------------------------
# Part I: Cut flow comparison (baseline vs patched, PRE_FV_REFERENCE_SELECTION)
# ---------------------------------------------------------------------------
CUTS_PRE_FV = [
    ("1_total",                  lambda r: True),
    ("2_neutrino_candidate",     lambda r: int(r.get("has_neutrino_candidate", 0) or 0)),
    ("3_shw_sp_n_20mev_gt0",     lambda r: int(r.get("shw_sp_n_20mev_showers", 0) or 0) > 0),
    ("4_all_4_bdts_evaluable",   lambda r: all(int(r.get(f"{m}_bdt_evaluable", 0) or 0) for m in MODELS)),
    ("5_numu_gt0p4",             lambda r: r.get("numu_bdt_score","") != "" and float(r["numu_bdt_score"]) > 0.4),
    ("6_other_gt0p2",            lambda r: r.get("other_bdt_score","") != "" and float(r["other_bdt_score"]) > 0.2),
    ("7_ncpi0_gtneg0p05",        lambda r: r.get("ncpi0_bdt_score","") != "" and float(r["ncpi0_bdt_score"]) > -0.05),
    ("8_nue_gtneg1p0",           lambda r: r.get("nue_bdt_score","") != "" and float(r["nue_bdt_score"]) > -1.0),
    ("9_shw_sp_n_20br1_eq1",     lambda r: int(r.get("shw_sp_n_20br1_showers", -1) or -1) == 1),
]

def apply_cutflow(rows, label):
    passing = list(rows)
    out = []
    for step_name, cut in CUTS_PRE_FV:
        if step_name != "1_total":
            passing = [r for r in passing if cut(r)]
        n = len(passing)
        n0p = sum(1 for r in passing if r.get("proton_category") == "0p")
        nnp = sum(1 for r in passing if r.get("proton_category") == "Np")
        out.append({"label": label, "step": step_name, "count": n,
                    "n_0p": n0p, "n_np": nnp,
                    "passing_evt_idx": ";".join(str(r["evt_idx"]) for r in passing)})
    return out, passing

bsl_cf, bsl_final = apply_cutflow(
    [r for r in baseline_rows.values()], "baseline")
pat_cf, pat_final = apply_cutflow(
    [{**r, "evt_idx": int(r["evt_idx"])} for r in patched_rows], "patched")

# Build side-by-side
cf_rows = []
for b_row, p_row in zip(bsl_cf, pat_cf):
    assert b_row["step"] == p_row["step"]
    cf_rows.append({
        "step":           b_row["step"],
        "baseline_count": b_row["count"],
        "patched_count":  p_row["count"],
        "baseline_0p":    b_row["n_0p"],
        "patched_0p":     p_row["n_0p"],
        "baseline_np":    b_row["n_np"],
        "patched_np":     p_row["n_np"],
        "delta":          p_row["count"] - b_row["count"],
    })

cutflow_csv = os.path.join(OUTDIR, "fix2_ab59_cutflow.csv")
with open(cutflow_csv, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["step","baseline_count","patched_count",
                                      "baseline_0p","patched_0p",
                                      "baseline_np","patched_np","delta"])
    w.writeheader()
    w.writerows(cf_rows)
print(f"Written: {cutflow_csv}")

# Newly selected and lost events
bsl_final_idx = {int(r["evt_idx"]) for r in bsl_final}
pat_final_idx = {int(r["evt_idx"]) for r in pat_final}
newly_selected = pat_final_idx - bsl_final_idx
lost_events    = bsl_final_idx - pat_final_idx

print("\n=== Part I: PRE_FV_REFERENCE_SELECTION Cut Flow ===")
print(f"{'Step':<35} {'Baseline':>8} {'Patched':>8} {'Delta':>6}")
print("-" * 60)
for row in cf_rows:
    d = row['delta']
    d_str = f"{d:+d}" if d != 0 else "0"
    print(f"{row['step']:<35} {row['baseline_count']:>8} {row['patched_count']:>8} {d_str:>6}")

print(f"\nNewly selected by Fix2-v2: {sorted(newly_selected)}")
print(f"Lost from selection:        {sorted(lost_events)}")
print(f"\nBaseline final count: {len(bsl_final_idx)}")
print(f"Patched  final count: {len(pat_final_idx)}")
