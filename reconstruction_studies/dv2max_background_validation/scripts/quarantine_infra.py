#!/usr/bin/env python3
"""Classify the runs of one PBS batch and MOVE (never delete) infrastructure-compromised runs to W/scratch/<tag>/.

A run is CLEAN only if: container log has 'lar exit: 0' and the BG*_JOB_DONE marker, and neither the lar log nor the
container log contains a resource-exhaustion message (RESOURCE_PATTERNS).  Anything else that was started is
COMPROMISED (non-zero exit, hung/killed, or exit 0 with a failed thread/process creation somewhere in the job).
Usage: quarantine_infra.py <PBS .OU log> <tag> [--dry-run]
"""
import csv, os, re, shutil, sys, glob

W = "/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/development/dv2max_background_validation_20261102"
RESOURCE_PATTERNS = ["Resource temporarily unavailable", "pthread_create", "fork: retry", "popen failure",
                     "Cannot allocate memory", "std::bad_alloc"]
ou, tag = sys.argv[1], sys.argv[2]
dry = "--dry-run" in sys.argv
started = {}
for l in open(ou):
    m = re.match(r"--- lane (\d+) arm (\w) (\w+) event (\d+) (start|container_exit=(\d+) end) (\d+)", l)
    if m:
        k = (m[2], m[3], m[4])
        if m[5] == "start":
            started[k] = dict(lane=m[1], start=int(m[7]), container_exit="", end="")
        else:
            started[k].update(container_exit=m[6], end=int(m[7]))
rows = []
for (arm, rs, tag4), s in sorted(started.items()):
    cl = f"{W}/logs/{rs}/arm{arm}/container_evt_{tag4}.log"
    ll = f"{W}/logs/{rs}/arm{arm}/lar_evt_{tag4}.log"
    od = f"{W}/runs/{rs}/arm{arm}/wirecell/evt_{tag4}"
    ctext = open(cl, errors="replace").read() if os.path.isfile(cl) else ""
    ltext = open(ll, errors="replace").read() if os.path.isfile(ll) else ""
    m = re.search(r"lar exit: (\d+)", ctext)
    lar_exit = m[1] if m else ""
    done = f"BG{arm}_JOB_DONE_{rs}_evt_{tag4}" in ctext
    hits = sorted({p for p in RESOURCE_PATTERNS if p in ctext or p in ltext})
    clean = lar_exit == "0" and done and not hits
    reason = "" if clean else ";".join(filter(None, [
        "" if s["end"] else "NOT_FINISHED(hung; job killed)", f"lar_exit={lar_exit}" if lar_exit not in ("0", "") else "",
        "no_done_marker" if not done else "", ("resource:" + "|".join(hits)) if hits else ""]))
    rows.append(dict(arm=arm, runset=rs, evt=int(tag4), lane=s["lane"], container_exit=s["container_exit"], lar_exit=lar_exit,
                     done=done, resource_messages="|".join(hits), status="CLEAN" if clean else "COMPROMISED", reason=reason))
    if not clean and not dry:
        dst = f"{W}/scratch/{tag}/{rs}/arm{arm}"
        os.makedirs(f"{dst}/wirecell", exist_ok=True)
        os.makedirs(f"{dst}/logs", exist_ok=True)
        if os.path.isdir(od):
            shutil.move(od, f"{dst}/wirecell/evt_{tag4}")
        for p in (cl, ll):
            if os.path.isfile(p):
                shutil.move(p, f"{dst}/logs/{os.path.basename(p)}")
out = f"{W}/scratch/{tag}/runs_classified.csv" if not dry else f"{W}/tables/_work/{tag}_classified_dryrun.csv"
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)
from collections import Counter
print("started", len(rows), Counter((r["arm"], r["status"]) for r in rows), "->", out)
