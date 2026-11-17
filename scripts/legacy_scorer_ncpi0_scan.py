#!/usr/bin/env python
"""Read-only scan: the 45 inputs of the frozen ``ncpi0`` BDT (incl. the real ``kine_pio_flag``) for every candidate of the BNB-CV events whose
as-run chain reaches the ``ncpi0`` stage (as-run numu AND other pass). NO training, NO tuning.

Why only these: every configuration of the scorer-convention correction is STRICTER than the as-run chain at numu / other / nue and re-scores only
``ncpi0`` (the one BDT that sees ``kine_pio_flag``), so the corrected selected set is a subset of the events that reach ``ncpi0`` as run.

    source env/setup_eaf.sh
    python scripts/legacy_scorer_ncpi0_scan.py bnb_cv --workers 24

Output: $SP_DATA/legacy_scorer_correction/bnb_cv_ncpi0_inputs.parquet  (columns in_<xml var>, c_nu_index, file_index, ev, ncpi0_score_asrun_recomputed)
"""
from __future__ import annotations
import argparse, os, sys, warnings
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
import multiprocessing as mp
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd

SPD = Path(os.environ["SP_DATA"]); OUT = SPD / "legacy_scorer_correction"; OUT.mkdir(parents=True, exist_ok=True)
TAG = "wc.T_tagger."


def work(job):
    import awkward as ak
    from sbnd_single_photon import bdt as B, caf as C
    fi, url, evs = job
    x = B.TmvaBdt("ncpi0", B.DEFAULT_WEIGHT_DIR / "single_photon_ncpi0_bdt_final.xml")
    cols = {n: B.input_branch("ncpi0", n) for n in x.var_names}
    branches = sorted(set(cols.values())); extra = TAG + "nu_index"
    rows = []
    try:
        with C.tolerant_embedded_basket_read(), C.MergedCaf(url) as f:
            d = f.read(wc=branches + ([extra] if extra not in branches else []))
            for ev in evs:
                if len(d[extra][ev]) == 0:
                    continue
                vals = {b: np.asarray(ak.to_numpy(d[b][ev]), dtype=np.float64) for b in branches}
                df = pd.DataFrame({"in_" + n: vals[b] for n, b in cols.items()})
                df.insert(0, "c_nu_index", np.asarray(ak.to_numpy(d[extra][ev])).astype(np.int64))
                df["ncpi0_score_asrun_recomputed"] = x.decision(np.column_stack([vals[cols[n]] for n in x.var_names]))
                df.insert(0, "file_index", fi); df.insert(1, "ev", ev)
                rows.append(df)
    except Exception as e:  # noqa: BLE001
        return fi, None, repr(e)[:200]
    return fi, (pd.concat(rows, ignore_index=True) if rows else None), None


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("sample", choices=["bnb_cv"]); ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--limit", type=int, default=0); a = ap.parse_args()
    from sbnd_single_photon import samples as S
    T = SPD / "analysis_tables" / a.sample
    c = pd.read_parquet(T / "candidates.parquet", columns=["file_index", "ev", "cum_single_photon_other_score_gt_0p2"])
    r = c[c.cum_single_photon_other_score_gt_0p2][["file_index", "ev"]].drop_duplicates()
    urls = S.manifest_urls(S.load_samples()[a.sample])
    jobs = [(int(fi), urls[int(fi)], sorted(int(e) for e in g.ev)) for fi, g in r.groupby("file_index")]
    if a.limit:
        jobs = jobs[: a.limit]
    print(a.sample, "events", len(r), "files", len(jobs), flush=True)
    with mp.get_context("spawn").Pool(min(a.workers, 24)) as p:
        res = list(p.imap_unordered(work, jobs, chunksize=1))
    bad = [q for q in res if q[2]]
    if bad:
        print("ERRORS", len(bad), bad[:5]); return 1
    t = pd.concat([q[1] for q in res if q[1] is not None], ignore_index=True).sort_values(["file_index", "ev", "c_nu_index"]).reset_index(drop=True)
    t.to_parquet(OUT / f"{a.sample}_ncpi0_inputs.parquet", index=False); print(a.sample, t.shape, "events", t.groupby(["file_index", "ev"]).ngroups)
    return 0


if __name__ == "__main__":
    sys.exit(main())
