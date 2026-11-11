#!/usr/bin/env python
"""Targeted, resumable read of two ``wc.T_segment`` branches not stored by Phase 9: ``dirsign`` and ``n_fit`` (READ-ONLY).

    source env/setup_eaf.sh
    python scripts/particle_pid_seg_scan.py --workers 24

Why: ``segment_determine_dir_track`` (4b6853d4, PRSegmentFunctions.cxx:2923) writes ``dirsign`` (0 = PID abstained / weak direction, e.g. the electron both-ends rule) and the number of fit points ``n_fit``
(the PID needs >= 2 points, >= 15 for the two-vertex-end branch).  Phase 9's ``seg`` table has ``pdg``, ``flag_shower``, ``length_cm``, the vertex ids and ``ke_mev`` but neither.
Population: the 11,331 official Gen2 NC-Delta TPC-box events with a candidate (Phase-9 ``event_taxonomy``).  One parquet per file in ``$SP_DATA/particle_pid_audit/official_ncdelta/raw/seg_extra/``
(files already present are skipped, so the scan is resumable); the exact manifest (file_index -> url, n events) is written to ``seg_extra_manifest.parquet``.  Workers <= 24, BLAS/OMP threads pinned to 1.
"""
from __future__ import annotations
import argparse, gzip, os, sys, warnings
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
import multiprocessing as mp
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd

SPD = Path(os.environ["SP_DATA"]); RAW = SPD / "particle_pid_audit" / "official_ncdelta" / "raw"; OUT = RAW / "seg_extra"


def work(job):
    from sbnd_single_photon import caf as C
    fi, url, evs = job
    p = OUT / f"{fi}.parquet"
    if p.exists():
        return fi, "skipped", None
    rows = []
    try:
        with C.tolerant_embedded_basket_read(), C.MergedCaf(url) as f:
            w = f._wt; d = {c: w["wc.T_segment." + c].array(library="ak") for c in ("nu_index", "segment_id", "dirsign", "n_fit")}
            for ev in evs:
                n = len(d["segment_id"][ev])
                if n:
                    rows.append(pd.DataFrame(dict(file_index=fi, ev=int(ev), **{c: np.asarray(d[c][ev]) for c in d})))
    except Exception as e:  # noqa: BLE001
        return fi, None, repr(e)[:300]
    pd.concat(rows, ignore_index=True).to_parquet(p, index=False) if rows else pd.DataFrame(columns=["file_index", "ev", "nu_index", "segment_id", "dirsign", "n_fit"]).to_parquet(p, index=False)
    return fi, "done", None


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=24); ap.add_argument("--limit", type=int, default=None); a = ap.parse_args(); OUT.mkdir(parents=True, exist_ok=True)
    t = pd.read_parquet(SPD / "shower_vertex_audit" / "official_ncdelta" / "event_taxonomy.parquet", columns=["file_index", "ev"])
    urls = [l.rstrip("\n").split("\t")[2] for l in gzip.open(REPO / "manifests" / "official_gen2_ncdelta_wc.tsv.gz", "rt")][1:]
    jobs = [(int(fi), urls[int(fi)], [int(x) for x in g.ev]) for fi, g in t.groupby("file_index")][: a.limit]
    pd.DataFrame([dict(file_index=j[0], url=j[1], n_events=len(j[2])) for j in jobs]).to_parquet(RAW / "seg_extra_manifest.parquet", index=False)
    print("events", sum(len(j[2]) for j in jobs), "files", len(jobs), flush=True)
    with mp.get_context("spawn").Pool(min(a.workers, 24)) as p:
        res = list(p.imap_unordered(work, jobs, chunksize=1))
    bad = [r for r in res if r[2]]; print("read errors", len(bad), [(r[0], r[2][:80]) for r in bad[:5]], flush=True)
    d = pd.concat([pd.read_parquet(x) for x in sorted(OUT.glob("*.parquet"))], ignore_index=True); d.to_parquet(RAW / "seg_extra.parquet", index=False); print("seg_extra", d.shape, flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
