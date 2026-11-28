#!/usr/bin/env python
"""Audit of Xuyang's released upstream SBND Wire-Cell nu_e / nu_mu classifiers (https://github.com/Ningclover/sbnd-wirecell-bdt, `releases/`).
Verifies, in a local clone: the pinned commit, every model file against the sha256 recorded in its manifest, manifest invariants (A v2 main chain variant,
nu_mu round 3af, simulation correction 1.071), the nu_e / nu_mu input lists against the shipped specs; and writes the required-input table
(`tables/upstream_release/required_inputs.csv`) and a file-hash table. Reads only the release repository. Does NOT touch any CAF, sample or score.

    git clone https://github.com/Ningclover/sbnd-wirecell-bdt.git /path/to/clone && git -C /path/to/clone checkout <pinned commit>
    source env/setup_eaf.sh && python scripts/upstream_release_audit.py /path/to/clone [--write]
"""
import argparse, json, subprocess, sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sbnd_single_photon import upstream_scores as US

REPO = Path(__file__).resolve().parents[1]; OUT = REPO / "tables" / "upstream_release"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("clone"); ap.add_argument("--write", action="store_true"); a = ap.parse_args()
    cfg = US.load_config(); clone = Path(a.clone)
    head = subprocess.run(["git", "-C", str(clone), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(clone), "status", "--porcelain", "--", "releases"], capture_output=True, text=True).stdout.strip()
    rep = US.verify_release(clone / "releases", cfg, head_commit=head, dirty=bool(dirty))
    print(json.dumps({k: v for k, v in rep.items() if k != "files"}, indent=1))
    if a.write:
        OUT.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rep["files"]).to_csv(OUT / "release_file_hashes.csv", index=False)
        (OUT / "release_audit.json").write_text(json.dumps({k: v for k, v in rep.items() if k != "files"}, indent=1) + "\n")
        US.required_inputs(clone / "releases", cfg).to_csv(OUT / "required_inputs.csv", index=False)
        print("wrote", OUT)
    sys.exit(0 if rep["ok"] else 1)


if __name__ == "__main__":
    main()
