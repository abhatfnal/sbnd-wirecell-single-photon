#!/usr/bin/env python
"""Candidate-associated truth ('light' table) for ALL candidates of the Nov16 generic-BNB CV (MC evaluation only; nothing selects or tunes).

The Round-1 reference already has this table for the old reconstruction (`$SP_DATA/background_mechanisms/bnb_cv/light.parquet`); the Nov16 replay only
associated truth to the SELECTED candidates. Stage-wise purity needs the association at every stage, so the identical `light_work` is run on the Nov16 files.

    source env/setup_eaf.sh && python scripts/ncdelta_purity_light_scan_nov16.py run --workers 24   (resumable) ; ... merge
"""
from __future__ import annotations
import argparse, os, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); sys.path.insert(0, str(REPO / "scripts"))
SPD = Path(os.environ.get("SP_DATA", "/tmp")); ROOT = SPD / "ncdelta_purity_datamc" / "bnb_cv_nov16"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("stage", choices=["run", "merge"]); ap.add_argument("--workers", type=int, default=24); ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    import pandas as pd
    import background_mechanisms_scan as B
    from sbnd_single_photon import samples as S
    urls = [r["url"] for r in S.read_manifest(REPO / "manifests" / "wcl1116" / "bnb_cv.tsv.gz")]
    od = ROOT / "light_pieces"; od.mkdir(parents=True, exist_ok=True)
    if a.stage == "run":
        B.run_pool(B.light_work, [(i, u, str(od)) for i, u in enumerate(urls)][: a.limit], min(a.workers, 24), "light-nov16")
    else:
        ps = sorted(od.glob("*.parquet")); df = pd.concat([pd.read_parquet(p) for p in ps], ignore_index=True)
        df.to_parquet(ROOT / "light.parquet", index=False); print(len(ps), "files", len(df), "rows")


if __name__ == "__main__":
    main()
