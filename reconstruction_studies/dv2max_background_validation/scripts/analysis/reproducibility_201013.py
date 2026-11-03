#!/usr/bin/env python3
"""Run-to-run reproducibility: the 58 runs of the killed job 201013 that were CLEAN (lar exit 0, no resource message;
kept in scratch/infra_pids_limit_201013/clean_but_same_job) vs their reruns in job 201062 (same template, inputs,
binaries).  Compares every T_tagger / T_kine branch (exact, NaN==NaN) and the T_segment / T_cluster entry counts.
Output: tables/reproducibility_rerun.csv.  Diagnostic only: sets the run-to-run noise floor for O-vs-D differences.
"""
import csv, os, glob
import numpy as np
import uproot

W = "/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/dv2max_background_validation_20261102"
Q = f"{W}/scratch/infra_pids_limit_201013/clean_but_same_job"
DECISION = ("shw_sp_filled", "shw_sp_n_20mev_showers", "shw_sp_n_20br1_showers", "shw_sp_energy")


def flat(t):
    out = {}
    if t is None:
        return out
    for k, v in t.arrays(library="np").items():
        x = v[0] if len(v) else None
        out[k] = np.asarray(x).ravel() if x is not None else None
    return out


def same(a, b):
    if a is None or b is None:
        return a is None and b is None
    if a.shape != b.shape:
        return False
    if a.dtype.kind in "fc":
        return bool(np.all((a == b) | (np.isnan(a) & np.isnan(b))))
    return bool(np.all(a == b))


rows = []
for d in sorted(glob.glob(f"{Q}/*/arm?/wirecell/evt_*")):
    rs, arm, ev = d.split("/")[-4], d.split("/")[-3][-1], d.split("/")[-1]
    new = f"{W}/runs/{rs}/arm{arm}/wirecell/{ev}"
    r = {"runset": rs, "arm": arm, "evt_idx": int(ev[4:])}
    fa, fb = uproot.open(f"{d}/tracking-pr.root"), uproot.open(f"{new}/tracking-pr.root")
    diffs = []
    for tree in ("T_tagger", "T_kine"):
        A = flat(fa[tree]) if tree in fa else {}
        B = flat(fb[tree]) if tree in fb else {}
        r[f"{tree}_present"] = f"{int(bool(A))}/{int(bool(B))}"
        dd = [k for k in sorted(set(A) | set(B)) if not same(A.get(k), B.get(k))]
        perm = [k for k in dd if A.get(k) is not None and B.get(k) is not None and A[k].shape == B[k].shape
                and same(np.sort(A[k]), np.sort(B[k]))]
        r[f"{tree}_n_diff_permutation_only"] = len(perm)
        r[f"{tree}_n_branches"] = len(set(A) | set(B))
        r[f"{tree}_n_diff"] = len(dd)
        diffs += [f"{tree}.{k}" for k in dd]
        if tree == "T_tagger":
            r["decision_branch_diff"] = ";".join(k for k in dd if k in DECISION)
    for tree in ("T_segment", "T_cluster"):
        r[f"{tree}_entries"] = f"{fa[tree].num_entries if tree in fa else 0}/{fb[tree].num_entries if tree in fb else 0}"
    r["diff_branches"] = ";".join(diffs[:20]) + (" ..." if len(diffs) > 20 else "")
    seg_ok = r["T_segment_entries"].split("/")[0] == r["T_segment_entries"].split("/")[1]
    nperm = r["T_tagger_n_diff_permutation_only"] + r["T_kine_n_diff_permutation_only"]
    r["identical"] = not diffs and seg_ok
    r["verdict"] = ("IDENTICAL" if r["identical"] else
                    "PERMUTATION_ONLY" if seg_ok and nperm == len(diffs) else "DIFFERENT")
    rows.append(r)
os.makedirs(f"{W}/tables", exist_ok=True)
with open(f"{W}/tables/reproducibility_rerun.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
from collections import Counter
print(len(rows), "pairs;", Counter((r["arm"], r["verdict"]) for r in rows))
for r in rows:
    if r["verdict"] == "DIFFERENT":
        print(r["runset"], r["arm"], r["evt_idx"], "tagger_diff", r["T_tagger_n_diff"], "kine_diff", r["T_kine_n_diff"],
              "decision:", r["decision_branch_diff"], "seg", r["T_segment_entries"], "|", r["diff_branches"][:200])
