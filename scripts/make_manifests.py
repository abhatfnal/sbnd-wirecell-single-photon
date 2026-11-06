#!/usr/bin/env python
"""Fetch Haiwang's prepared merged-CAF lists over XRootD and write lightweight manifests.

Output: manifests/<sample>.tsv.gz   (# header lines, then index<TAB>pnfs_path<TAB>xrootd_url)
Original list order is preserved. No ROOT file is read or copied.

    source env/setup_eaf.sh && python scripts/make_manifests.py
"""
from __future__ import annotations

import argparse, gzip, hashlib, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from sbnd_single_photon import samples as S, xrd  # noqa: E402


def fetch(short_path: str) -> bytes:
    url = xrd.to_xrootd_url(short_path)
    r = subprocess.run(["xrdcp", "-s", "-f", url, "-"], capture_output=True, check=True)
    return r.stdout


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", default=str(S.DEFAULT_SAMPLES_YAML))
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    for name, s in S.load_samples(a.samples).items():
        if not s.available or "source_list" not in s.extra:
            print(f"[skip] {name}: status={s.status}")
            continue
        if a.only and name not in a.only:
            continue
        raw = fetch(s.extra["source_list"])
        paths = [l.strip() for l in raw.decode().splitlines() if l.strip()]
        if len(set(paths)) != len(paths):
            print(f"[warn] {name}: duplicate entries in source list")
        if s.n_files_listed is not None and len(paths) != s.n_files_listed:
            print(f"[WARN] {name}: list has {len(paths)} entries, samples.yaml says {s.n_files_listed}")
        out = REPO / s.manifest
        out.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(out, "wt") as fh:
            fh.write(f"# sample: {name}\n# label: {s.label}\n# data_or_mc: {'MC' if s.is_mc else 'data'}\n")
            fh.write(f"# production: {s.production}\n# source_list: {s.extra['source_list']}\n")
            fh.write(f"# source_list_sha256: {hashlib.sha256(raw).hexdigest()}\n")
            fh.write(f"# n_files_listed: {len(paths)}\n# n_caf_events_known: {s.n_caf_events}\n")
            fh.write(f"# n_wc_valid_events_known: {s.n_wc_valid_events}\n# schema_md5: {s.schema_md5}\n")
            fh.write(f"# xrootd_door: {xrd.DOOR}\n# generated_utc: {datetime.now(timezone.utc).isoformat(timespec='seconds')}\n")
            fh.write("index\tpnfs_path\txrootd_url\n")
            for i, p in enumerate(paths):
                fh.write(f"{i}\t{p}\t{xrd.to_xrootd_url(p)}\n")
        print(f"[ok] {name}: {len(paths)} files -> {out.relative_to(REPO)} ({out.stat().st_size/1e6:.2f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
