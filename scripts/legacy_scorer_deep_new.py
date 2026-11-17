#!/usr/bin/env python
"""Candidate-associated truth (the Phase-4 ``deep`` stage, unchanged code) for the BNB-CV candidates that pass ONLY under the source-faithful scorer and were never selected as run.

    source env/setup_eaf.sh && python scripts/legacy_scorer_deep_new.py --config D_full --workers 8
Output: $SP_DATA/legacy_scorer_correction/deep_new_<config>.parquet. MC evaluation only; nothing here decides whether a candidate passes.
"""
from __future__ import annotations
import argparse, os, sys, warnings
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); sys.path.insert(0, str(REPO / "scripts")); warnings.filterwarnings("ignore")
import multiprocessing as mp
import pandas as pd
SPD = Path(os.environ["SP_DATA"]); SPC = SPD / "legacy_scorer_correction"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--config", default="D_full"); ap.add_argument("--workers", type=int, default=8); a = ap.parse_args()
    import background_deep as BD
    from sbnd_single_photon import samples as S
    urls = S.manifest_urls(S.load_samples()["bnb_cv"]); od = SPC / f"deep_new_pieces_{a.config}"; od.mkdir(parents=True, exist_ok=True)
    c = pd.read_parquet(SPC / f"bnb_candidates_{a.config}.parquet", columns=["file_index", "ev", "c_nu_index", "pass_final"]); sel = c[c.pass_final]
    deep = pd.read_parquet(SPD / "background_mechanisms" / "bnb_cv" / "deep.parquet", columns=["file_index", "ev", "nu_index"]).rename(columns={"nu_index": "c_nu_index"}).assign(_have=True)
    new = sel.merge(deep, on=["file_index", "ev", "c_nu_index"], how="left"); new = new[new._have.isna()]
    print(a.config, "selected", len(sel), "already in deep", len(sel) - len(new), "NEW", len(new), flush=True)
    jobs = [(int(i), urls[int(i)], str(od), new[new.file_index == i][["ev", "c_nu_index"]].values.tolist()) for i in sorted(new.file_index.unique())]
    with mp.get_context("spawn").Pool(min(a.workers, len(jobs) or 1)) as p:
        res = list(p.imap_unordered(BD.deep_work, jobs))
    print(res)
    ps = sorted(od.glob("*.parquet")); df = pd.concat([pd.read_parquet(p) for p in ps], ignore_index=True); df.to_parquet(SPC / f"deep_new_{a.config}.parquet", index=False); print(df.shape)


if __name__ == "__main__":
    main()
