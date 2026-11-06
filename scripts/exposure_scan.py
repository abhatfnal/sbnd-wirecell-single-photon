#!/usr/bin/env python
"""Read-only parallel scan of per-file exposure info (TotalPOT, rec.hdr.*) over a manifest.

    python scripts/exposure_scan.py bnb_cv nuecc beam_off beam_on_open --workers 16 --out $SP_DATA/exposure_scan
Writes <out>/<sample>.jsonl (one row per file) and tables/pot/<sample>_summary.json (small, committable).
Only a handful of tiny branches are read per file; nothing is copied.
"""
from __future__ import annotations
import argparse, json, sys, time
import multiprocessing as mp
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from sbnd_single_photon import samples as S, exposure as E  # noqa: E402


def work(url):
    for attempt in range(3):
        r = E.read_file_exposure(url)
        if not r["error"]:
            return r
        time.sleep(1 + attempt)
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("samples", nargs="+")
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    reg = S.load_samples()
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    (REPO / "tables" / "pot").mkdir(parents=True, exist_ok=True)
    for name in a.samples:
        urls = S.manifest_urls(reg[name])[: a.limit]
        t0 = time.time(); rows = []
        with mp.get_context("spawn").Pool(a.workers) as p, open(out / f"{name}{'_lim'+str(a.limit) if a.limit else ''}.jsonl", "w") as fh:
            for i, r in enumerate(p.imap(work, urls, chunksize=4)):
                rows.append(r); fh.write(json.dumps(r) + "\n")
                if (i + 1) % 2000 == 0:
                    print(f"[{name}] {i+1}/{len(urls)} {time.time()-t0:.0f}s", flush=True)
        summ = E.summarize(rows); summ["sample"] = name; summ["wall_s"] = round(time.time() - t0, 1)
        summ["known_events"] = reg[name].n_caf_events; summ["known_wc_valid"] = reg[name].n_wc_valid_events
        (REPO / "tables" / "pot" / f"{name}{'_lim'+str(a.limit) if a.limit else ''}_summary.json").write_text(json.dumps(summ, indent=1))
        print(name, json.dumps(summ), flush=True)


if __name__ == "__main__":
    main()
