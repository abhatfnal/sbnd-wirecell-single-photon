#!/usr/bin/env python
"""POLICY SENSITIVITY ONLY: the reco proton-row count of the analysis-selected candidate with and without the ``kine_energy_included == 3`` rows (leftover-shower pool).

Baseline convention (unchanged, used for every headline number): every ``kine_particle_type == 2212`` row with KE above the threshold counts, regardless of ``kine_energy_included``.
This script re-reads only the wc.T_kine rows of the final-selected candidate of each selected event (one merged CAF per event; ~1.2k files) and writes
$SP_DATA/spine_harmonization/official_ncdelta/reco_included_sensitivity.parquet with, per selected event: proton counts above 35 and 50 MeV for (all rows) and (included == 1 only).
    source env/setup_eaf.sh; python scripts/spine_reco_included_sensitivity.py --workers 16
"""
from __future__ import annotations
import argparse, gzip, os, sys, warnings
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
import multiprocessing as mp
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
SPD = Path(os.environ["SP_DATA"]); OUT = SPD / "spine_harmonization" / "official_ncdelta"
KIN = "wc.T_kine."; TAG = "wc.T_tagger.nu_index"


def urls():
    return [l.rstrip("\n").split("\t")[2] for l in gzip.open(REPO / "manifests" / "official_gen2_ncdelta_wc.tsv.gz", "rt")][1:]


def work(job):
    from sbnd_single_photon import caf as C
    fi, url, evs = job
    out = []
    try:
        with C.tolerant_embedded_basket_read(), C.MergedCaf(url) as f:
            pdg = f.read_nested(KIN + "kine_particle_type"); ke = f.read_nested(KIN + "kine_energy_particle"); inc = f.read_nested(KIN + "kine_energy_included")
            nu = f.read([TAG], with_ids=False)[TAG]
            for ev, snu in evs:
                pos = [i for i, v in enumerate(nu[ev].to_list()) if int(v) == int(snu)]
                assert len(pos) == 1, (fi, ev, snu)
                p, k, ii = np.asarray(pdg[ev][pos[0]]), np.asarray(ke[ev][pos[0]]), np.asarray(inc[ev][pos[0]])
                isp = p == 2212
                out.append(dict(file_index=fi, ev=ev, sel_nu_index=snu, n35_all=int((isp & (k > 35)).sum()), n50_all=int((isp & (k > 50)).sum()),
                                n35_inc1=int((isp & (k > 35) & (ii == 1)).sum()), n50_inc1=int((isp & (k > 50) & (ii == 1)).sum()),
                                n50_inc3_rows=int((isp & (k > 50) & (ii != 1)).sum())))
    except Exception as e:  # noqa: BLE001
        return [dict(file_index=fi, error=repr(e)[:200])]
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=16); a = ap.parse_args()
    t = pd.read_parquet(OUT / "event_table_filter_box_any.parquet", columns=["file_index", "ev", "A_final", "sel_nu_index"])
    s = t[t.A_final.astype(bool)]
    u = urls(); jobs = [(int(fi), u[int(fi)], [(int(e), int(n)) for e, n in zip(g.ev, g.sel_nu_index)]) for fi, g in s.groupby("file_index")]
    with mp.get_context("spawn").Pool(min(a.workers, 24)) as p:
        res = [r for rr in p.imap_unordered(work, jobs, chunksize=1) for r in rr]
    d = pd.DataFrame(res)
    if "error" in d and d.error.notna().any():
        print("ERRORS", d[d.error.notna()].head()); return 1
    d.to_parquet(OUT / "reco_included_sensitivity.parquet", index=False); print(d.shape, (d.n50_all != d.n50_inc1).sum(), "events change at 50 MeV")


if __name__ == "__main__":
    sys.exit(main())
