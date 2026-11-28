#!/usr/bin/env python
"""Manifest-only inventory of the official EAF samples for the upstream-classifier integration: per production x sample, the file list sizes, role, which upstream training / evaluation
statement applies, and (beam-off) the run-parity split that decides overlap with the upstream training half. Reads ONLY the committed manifests and configs/samples.yaml; no CAF, no score.

    source env/setup_eaf.sh && python scripts/upstream_sample_inventory.py
"""
import re, sys
from pathlib import Path
import pandas as pd, yaml
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sbnd_single_photon import samples as S

REPO = Path(__file__).resolve().parents[1]; OUT = REPO / "tables" / "upstream_release" / "sample_applicability.csv"
UPSTREAM = {   # what the release documentation says about each kind of sample (releases/README.md, numu_round3af/README.md, nue README "How they were trained")
    "bnb_cv": ("Fermilab evaluation sample (fg1 / WCLocal2026Nov16 mc-cv); NOT used in training per the release", "upstream trained on Aurora BNB CV (627k events, a different production); event-level disjointness not documented"),
    "nuecc": ("Fermilab nuecc: evaluation use only per the release", "Aurora nueCC-filtered (269k events) was used for training; file-level hold-out lists matched on file_id exist (examples/gpvm README); membership manifest needed"),
    "official_gen2_ncdelta": ("official Gen2 NC-Delta: evaluation", "Aurora NC-Delta radiative (27k events, 'wcl1116-ncdr') was TRAINING background for nu_e and nu_mu; official sample is a separate production, but event-level disjointness is not documented"),
    "beam_off": ("even-run half = evaluation; ODD-RUN half = upstream TRAINING data", "run parity decides overlap (counts below)"),
    "beam_on_open": ("open data (runs 18255/18259): used by the release only for data/prediction checks", "no training use"),
    "run3bnb": ("Run-3 beam-on: used by the release for data/prediction checks (their evaluation); BLOCKED for us (data policy)", "no training use"),
}


def manifest(prod, sample):
    return S.manifest_urls(S.load_samples()[sample]) if prod == "old_fg1" else [r["url"] for r in S.read_manifest(REPO / "manifests" / "wcl1116" / f"{sample}.tsv.gz")]


def main():
    rows = []
    for prod in ("old_fg1", "nov16"):
        for s, (ev, tr) in UPSTREAM.items():
            if prod == "old_fg1" and s == "run3bnb": rows.append(dict(production=prod, sample=s, n_files=0, note="registered for WCLocal2026Nov16 only (no old-production run3bnb)", applicable_to_released_models=False)); continue
            try: urls = manifest(prod, s)
            except Exception as e: rows.append(dict(production=prod, sample=s, n_files=-1, note=f"no manifest {e!r}"[:100])); continue
            r = dict(production=prod, sample=s, n_files=len(urls), upstream_role=ev, upstream_training_overlap_statement=tr, applicable_to_released_models=(prod == "nov16"))
            if s == "beam_off":
                run = pd.Series([int(m.group(1)) if (m := re.search(r"run(\d+)_", u)) else -1 for u in urls])
                r.update(n_runs=int(run[run > 0].nunique()), n_files_odd_run=int((run % 2 == 1).sum()), n_files_even_run=int((run % 2 == 0).sum()), n_files_no_run_in_name=int((run < 0).sum()))
            rows.append(r)
    pd.DataFrame(rows).to_csv(OUT, index=False); print(pd.DataFrame(rows)[["production", "sample", "n_files", "applicable_to_released_models", "n_files_odd_run", "n_files_even_run"]].to_string())


if __name__ == "__main__":
    main()
