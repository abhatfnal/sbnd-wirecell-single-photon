#!/usr/bin/env python
"""Read ``wc.T_truth_nu`` (every true neutrino interaction of the readout window) for the official Gen2 NC-Delta events that reach the shower stage (READ-ONLY; nothing is selected or tuned).

    source env/setup_eaf.sh
    python scripts/pi0_pair_truth_nu_scan.py --workers 24

Why: the pair-member truth taxonomy of ``pi0_pair_fragmentation_audit.py`` must tell an *other neutrino interaction inside the active volume* from a *dirt / outside-TPC neutrino*; the row-level T_match partner
only carries the interaction index (``p1_t_nu``).  One row per (file_index, ev, nu_idx): vertex, pdg, ccnc, E, edep.
Population: the 8,080 events with a > 20 MeV shower (``A_n20mev``; the pair and fragmentation populations are subsets).  Output: ``$SP_DATA/pi0_pair_fragmentation_audit/official_ncdelta/raw/truth_nu.parquet``.
Workers <= 24, BLAS/OMP threads pinned to 1.
"""
from __future__ import annotations
import argparse, gzip, os, sys, warnings
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
import multiprocessing as mp
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import pandas as pd

SPD = Path(os.environ["SP_DATA"]); OUT = SPD / "pi0_pair_fragmentation_audit" / "official_ncdelta" / "raw"
TNU = ["nu_idx", "pdg", "ccnc", "E", "vtx_x", "vtx_y", "vtx_z", "edep"]


def work(job):
    from sbnd_single_photon import caf as C
    fi, url, evs = job
    rows = []
    try:
        with C.tolerant_embedded_basket_read(), C.MergedCaf(url) as f:
            w = f._wt
            tnu = {c: w["wc.T_truth_nu." + c].array(library="ak") for c in TNU}
            for ev in evs:
                n = len(tnu["nu_idx"][ev])
                for i in range(n):
                    rows.append(dict(file_index=fi, ev=int(ev), **{c: float(tnu[c][ev][i]) for c in TNU}))
    except Exception as e:  # noqa: BLE001
        return fi, None, repr(e)[:300]
    return fi, pd.DataFrame(rows), None


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=24); ap.add_argument("--limit", type=int, default=None); a = ap.parse_args(); OUT.mkdir(parents=True, exist_ok=True)
    t = pd.read_parquet(SPD / "shower_vertex_audit" / "official_ncdelta" / "event_taxonomy.parquet", columns=["file_index", "ev", "A_n20mev"])
    ev = t[t.A_n20mev.astype(bool)]
    urls = [l.rstrip("\n").split("\t")[2] for l in gzip.open(REPO / "manifests" / "official_gen2_ncdelta_wc.tsv.gz", "rt")][1:]
    jobs = [(int(fi), urls[int(fi)], [int(x) for x in g.ev]) for fi, g in ev.groupby("file_index")][: a.limit]
    print("events", sum(len(j[2]) for j in jobs), "files", len(jobs), flush=True)
    with mp.get_context("spawn").Pool(min(a.workers, 24)) as p:
        res = list(p.imap_unordered(work, jobs, chunksize=1))
    bad = [r for r in res if r[2]]
    print("read errors", len(bad), [(r[0], r[2][:80]) for r in bad[:5]], flush=True)
    d = pd.concat([r[1] for r in res if r[1] is not None and len(r[1])], ignore_index=True); d.to_parquet(OUT / "truth_nu.parquet", index=False); print("truth_nu", d.shape, flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
