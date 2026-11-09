#!/usr/bin/env python
"""ONE command: official NC Delta Wire-Cell merged CAFs -> derived tables + the truth-joined signal table (outside Git). No tuning, no FV.

    source env/setup_eaf.sh
    python scripts/build_official_signal_analysis_table.py --manifest manifests/official_gen2_ncdelta_wc.tsv.gz --workers 20

Needs: (1) a manifest written by scripts/register_official_ncdelta_wc.py whose provenance gate is OPEN (tables/official_signal/arrival_registration.json),
(2) the master truth table ($SP_DATA/official_gen2_ncdelta_master/), (3) the frozen configs/baseline_selection.yaml.
Steps: build_analysis_table.py (pieces, then merge; the SAME code and offline BDT scoring as the BNB CV) ->
       $SP_DATA/analysis_tables/official_gen2_ncdelta/{candidates,events,files}.parquet + metadata.json
       join of the master truth with the events table, per truth region ->
       $SP_DATA/official_signal_baseline/{signal_joined_<region>.parquet, signal_missing_<region>.parquet, metadata.json}
Events absent from the merged CAFs stay in the truth denominator (signal_missing_*). Workers <= 24.
"""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, sys, time, warnings
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import pandas as pd

SAMPLE = "official_gen2_ncdelta"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", default=str(REPO / "manifests" / "official_gen2_ncdelta_wc.tsv.gz"))
    ap.add_argument("--workers", type=int, default=20); ap.add_argument("--skip-build", action="store_true", help="tables already built: only (re)join the truth")
    ap.add_argument("--arrival", default=str(REPO / "tables" / "official_signal" / "arrival_registration.json"))
    a = ap.parse_args()
    spd = Path(os.environ["SP_DATA"]); root = spd / "analysis_tables"; out = spd / "official_signal_baseline"; out.mkdir(parents=True, exist_ok=True)
    if not Path(a.arrival).exists():
        raise SystemExit("no arrival registration: run scripts/register_official_ncdelta_wc.py first (nothing is guessed)")
    arr = json.load(open(a.arrival))
    if not arr["gate"]["open"]:
        raise SystemExit(f"PROVENANCE GATE CLOSED: required failed {arr['gate']['required_failed']}, unknown {arr['gate']['required_unknown']}. "
                         "Fix the sample or the declaration; the gate has no override.")
    if not a.skip_build:
        base = [sys.executable, str(REPO / "scripts" / "build_analysis_table.py"), SAMPLE, "--manifest", a.manifest, "--root", str(root)]
        subprocess.run(base + ["--workers", str(min(a.workers, 24))], check=True)
        subprocess.run(base + ["--merge"], check=True)
    from sbnd_single_photon import signal_master as SM, signal_pipeline as SP
    ev = pd.read_parquet(root / SAMPLE / "events.parquet")
    master = spd / "official_gen2_ncdelta_master"
    rec = pd.read_parquet(master / "signal_records.parquet"); units = pd.read_parquet(master / "units.parquet")
    regions = SM.load_regions()
    meta = dict(schema_version="1.0", created_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                git_commit=subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
                manifest=a.manifest, manifest_sha256=sha(a.manifest), arrival_registration_sha256=sha(a.arrival),
                analysis_table_metadata_sha256=sha(root / SAMPLE / "metadata.json"), master_metadata_sha256=sha(master / "metadata.json"),
                baseline_selection_sha256=sha(REPO / "configs" / "baseline_selection.yaml"), regions={})
    for name, box in regions.items():
        sig = SP.region_truth(rec, box, name)
        arrived, missing = SP.split_arrived(sig, ev)
        arrived.to_parquet(out / f"signal_joined_{name}.parquet", index=False); missing.to_parquet(out / f"signal_missing_{name}.parquet", index=False)
        meta["regions"][name] = dict(n_truth=int(len(sig)), arrived=int(len(arrived)), missing=int(len(missing)))
    (out / "metadata.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps(meta["regions"]))


if __name__ == "__main__":
    main()
