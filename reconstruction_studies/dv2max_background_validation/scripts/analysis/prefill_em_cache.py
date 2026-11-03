#!/usr/bin/env python3
"""Speed-up only: pre-fill the run_bg.py EM-truth cache (tables/_work/cache/em_<ARM>_<rs>) for a shard of events,
calling run_bg.em_truth VERBATIM (same inputs, same cache key -> identical pickle).  Each pickle is computed into a
private directory and os.replace()d into the shared cache, so a concurrently running run_bg.py sees either no file or
a complete one.  Events go in reverse order (run_bg.py walks forward).
Usage: python3 prefill_em_cache.py --runset numucc --arm O --shard j --nshards k [--first 0 --last 399]
"""
import os, sys, csv, argparse, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_bg as B   # noqa: E402  (module import only; main() not run)

ap = argparse.ArgumentParser()
ap.add_argument("--runset", required=True)
ap.add_argument("--arm", required=True)
ap.add_argument("--shard", type=int, required=True)
ap.add_argument("--nshards", type=int, required=True)
ap.add_argument("--first", type=int, default=0)
ap.add_argument("--last", type=int, required=True)
a = ap.parse_args()
L, S = B.L, B.S
arm = L.arm_bg(a.arm, a.runset)
tlist = {int(r["evt_idx"]): r for r in csv.DictReader(open(f"{S}/inputs/{a.runset}_events.csv"))}
cache = f"{S}/tables/_work/cache/em_{a.arm}_{a.runset}"
os.makedirs(cache, exist_ok=True)
priv = tempfile.mkdtemp(prefix=f"emprefill_{a.arm}_{a.shard}_", dir=f"{S}/scratch")
n_new = 0
for i in list(range(a.last, a.first - 1, -1))[a.shard::a.nshards]:
    p = f"{arm['wc_dir']}/evt_{i:04d}/mabc.zip"
    name = f"emtruth_{i:04d}_{L._sha1(repr((3, L._file_sig(p))).encode())}.pkl"
    if os.path.isfile(os.path.join(cache, name)):
        continue
    out = B.em_truth(arm["wc_dir"], i, tlist[i], priv)
    os.replace(os.path.join(priv, name), os.path.join(cache, name))
    n_new += 1
    if not out.get("ok"):
        print("NOT_OK", a.arm, i, out.get("error"), flush=True)
os.rmdir(priv)
print("done", a.runset, a.arm, "shard", a.shard, "new", n_new, flush=True)
