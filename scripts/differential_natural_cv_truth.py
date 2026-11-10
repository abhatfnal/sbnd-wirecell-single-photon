#!/usr/bin/env python
"""Photon direction / proton KEs of the NATURAL NC-Delta signal neutrinos in the BNB CV (truth only; ~100 files). Output: $SP_DATA/differential_efficiency/natural_cv_truth_extra.parquet.

    source env/setup_eaf.sh; python scripts/differential_natural_cv_truth.py --workers 12
Same definitions as scripts/differential_truth_scan.py (primary photon of maximum energy of the selected signal neutrino ``k``)."""
from __future__ import annotations
import argparse, os, sys, warnings
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
import multiprocessing as mp
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); sys.path.insert(0, str(REPO / "scripts")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
SPD = Path(os.environ["SP_DATA"])


def work(job):
    import differential_truth_scan as S
    url, rows = job
    r = pd.DataFrame(S.read_one(url, rows.rename(columns={"k": "signal_nu_index"})))
    r["file_index"] = rows.file_index.iloc[0]
    return r


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=12); a = ap.parse_args()
    from sbnd_single_photon import natural_signal as NS, samples as S
    sn = pd.read_parquet(SPD / "natural_ncdelta_bnb_cv" / "signal_neutrinos.parquet"); sig = NS.to_signal_truth_table(sn)
    sig = sig[sig.in_region]
    sn = sn.merge(sig[["file_index", "ev"]], on=["file_index", "ev"]).copy()      # keep the neutrino rows of the selected events only
    sel = sn.sort_values(["file_index", "ev", "k"]).merge(sig[["file_index", "ev", "x", "y", "z"]], on=["file_index", "ev"], suffixes=("", "_s"))
    sel = sel[(abs(sel.x - sel.x_s) < 1e-3) & (abs(sel.y - sel.y_s) < 1e-3) & (abs(sel.z - sel.z_s) < 1e-3)].drop_duplicates(["file_index", "ev"])
    assert len(sel) == len(sig), (len(sel), len(sig))
    urls = S.manifest_urls(S.load_samples()["bnb_cv"])
    jobs = [(urls[int(fi)], g[["ev", "k"]].assign(run=0, subrun=0, evt=0).reset_index(drop=True).assign(file_index=int(fi))) for fi, g in sel.groupby("file_index")]
    with mp.get_context("spawn").Pool(min(a.workers, 24)) as p:
        out = pd.concat(p.map(work, jobs), ignore_index=True)
    out.to_parquet(SPD / "differential_efficiency" / "natural_cv_truth_extra.parquet", index=False); print(out.shape)


if __name__ == "__main__":
    main()
