#!/usr/bin/env python
"""Fingerprint of the BASELINE artifacts (diagnostic legacy-chain comparison: candidate / event / file tables of both productions, owner and identity-proof tables, derived signal tables, and the
committed result CSVs) so that the upstream-score integration can PROVE it overwrote nothing.  The overlay mechanism only ever writes new files; this manifest is the check.

    source env/setup_eaf.sh && python scripts/upstream_integrity_manifest.py --write     # record (once, before any upstream score exists)
    source env/setup_eaf.sh && python scripts/upstream_integrity_manifest.py --verify    # exit 1 if any recorded file changed or vanished
"""
import argparse, hashlib, os, sys
from pathlib import Path
import pandas as pd

REPO = Path(__file__).resolve().parents[1]; SPD = Path(os.environ.get("SP_DATA", "/exp/sbnd/data/users/abhat/single_photon_ncdelta")); OUT = REPO / "tables" / "upstream_release" / "baseline_artifact_hashes.csv"
RESULT_CSVS = ["overall_purity", "topology_purity", "cumulative_efficiency_purity", "control_region_summary_final", "np_over_0p_double_ratio_with_covariance", "ncpi0_P_truth_Np_given_reco", "background_composition_final_production_matched",
               "syst_band_by_component", "syst_unit_weight_reproduction", "syst_identity_proof", "audit_neutron_g4_variance_concentration_final", "audit_neutron_g4_variance_concentration_regions"]


def files():
    out = []
    for base in (SPD / "analysis_tables", SPD / "wcl1116_nov16" / "analysis_tables_new", SPD / "wcl1116_nov16" / "analysis_tables_old"):
        for p in sorted(base.glob("*/*")):
            if p.is_file(): out.append(p)
    out += sorted(p for p in (SPD / "wcl1116_nov16" / "derived").glob("*") if p.is_file())
    syst = SPD / "ncdelta_purity_datamc" / "syst"
    out += sorted(p for p in syst.glob("*") if p.is_file() and p.name.startswith(("owners_", "proof_", "blocks_meta_", "regions_plan_", "neutron_g4_events_")) and p.suffix != ".npy")
    out += [SPD / "ncdelta_purity_datamc" / s / "light.parquet" for s in ("bnb_cv_old", "bnb_cv_nov16") if (SPD / "ncdelta_purity_datamc" / s / "light.parquet").exists()]
    out += [REPO / "tables" / "ncdelta_purity_datamc" / f"{n}.csv" for n in RESULT_CSVS]
    return out


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""): h.update(b)
    return h.hexdigest()


def rel(p):
    return ("repo:" + str(p.relative_to(REPO))) if REPO in p.parents else ("SP_DATA:" + str(p.relative_to(SPD)))


def main():
    ap = argparse.ArgumentParser(); g = ap.add_mutually_exclusive_group(required=True); g.add_argument("--write", action="store_true"); g.add_argument("--verify", action="store_true"); a = ap.parse_args()
    if a.write:
        if OUT.exists(): sys.exit(f"{OUT} exists: the baseline fingerprint is written once")
        rows = [dict(path=rel(p), size=p.stat().st_size, sha256=sha(p)) for p in files() if p.exists()]; pd.DataFrame(rows).to_csv(OUT, index=False); print("recorded", len(rows), "files,", sum(r["size"] for r in rows) / 1e9, "GB")
    else:
        t = pd.read_csv(OUT); bad = []
        for r in t.itertuples():
            p = (REPO / r.path[5:]) if r.path.startswith("repo:") else (SPD / r.path[8:])
            if not p.exists() or p.stat().st_size != r.size or sha(p) != r.sha256: bad.append(r.path)
        print("verified", len(t), "files;", len(bad), "changed or missing", bad[:10]); sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
