#!/usr/bin/env python
"""METADATA-ONLY audit: does each official sample's merged CAF contain every `recTreeWireCell` branch the released upstream classifiers need
(`tables/upstream_release/required_inputs.csv`), for offline score-only regeneration?  Reads only the BRANCH NAMES of `recTreeWireCell` / `recTree` (uproot `keys()`), of a few
files per sample/production. No array, no event, no score, no selection is read or computed, so the independent-evaluation policy is not touched.

    source env/setup_eaf.sh && export BEARER_TOKEN_FILE=... && python scripts/upstream_schema_audit.py [--n-files 2] [--samples ...]

Outputs: tables/upstream_release/schema_audit_branches.csv (per sample/production/file: counts and the missing branch list) and schema_audit_summary.json.
"""
import argparse, json, sys
from pathlib import Path
import numpy as np, pandas as pd, uproot
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sbnd_single_photon import samples as S

REPO = Path(__file__).resolve().parents[1]; OUT = REPO / "tables" / "upstream_release"
SAMPLES = ["bnb_cv", "official_gen2_ncdelta", "nuecc", "beam_off", "beam_on_open", "run3bnb"]
ALSO = ["wc.T_tagger.nu_index", "wc.T_tagger.nu_x", "wc.T_tagger.nu_y", "wc.T_tagger.nu_z", "wc.T_tagger.neutrino_type", "wc.T_kine.nu_index", "wc.T_kine.kine_reco_Enu", "wc.run", "wc.subrun", "wc.evt", "wc.valid", "wc.Trun.wct_version"]
MC_ONLY = ["wc.T_truth_nu.nu_idx", "wc.T_match.level", "rec.mc.nu.wgt.univ", "rec.mc.nu.imp_weight"]


def manifest(prod, sample):
    return S.manifest_urls(S.load_samples()[sample]) if prod == "old_fg1" else [r["url"] for r in S.read_manifest(REPO / "manifests" / "wcl1116" / f"{sample}.tsv.gz")]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n-files", type=int, default=2); ap.add_argument("--samples", nargs="+", default=SAMPLES); ap.add_argument("--productions", nargs="+", default=["old_fg1", "nov16"]); a = ap.parse_args()
    req = pd.read_csv(OUT / "required_inputs.csv"); need = set()
    for r in req.itertuples():
        need.add(r.caf_branch)
        if "per-object" in r.kind: need |= {r.caf_branch + "..idx", r.caf_branch + "..length"}
    need |= set(ALSO); rows = []; rng = np.random.default_rng(0)
    for prod in a.productions:
        for s in a.samples:
            try: urls = manifest(prod, s)
            except Exception as e: rows.append(dict(production=prod, sample=s, error=f"no manifest: {e!r}"[:200])); continue
            pick = sorted(set([0] + list(rng.choice(len(urls), size=min(a.n_files - 1, len(urls) - 1), replace=False)))) if a.n_files > 1 else [0]
            for i in pick:
                try:
                    f = uproot.open(urls[i]); wc = set(f["recTreeWireCell"].keys()); rec = set(f["recTree"].keys()); keys = wc | rec; mc = s not in ("beam_off", "beam_on_open", "run3bnb")
                    miss = sorted(b for b in need if b not in keys); miss_mc = sorted(b for b in MC_ONLY if b not in keys) if mc else []
                    rows.append(dict(production=prod, sample=s, file_index=int(i), url=urls[i], n_wc_branches=len(wc), n_required=len(need), n_missing=len(miss), missing=";".join(miss[:60]), n_missing_mc_truth_or_weights=len(miss_mc), missing_mc=";".join(miss_mc), error=""))
                except Exception as e:
                    rows.append(dict(production=prod, sample=s, file_index=int(i), url=urls[i], error=repr(e)[:200]))
            print(prod, s, [(r.get("n_missing"), r.get("error")) for r in rows[-len(pick):]], flush=True)
    df = pd.DataFrame(rows); df.to_csv(OUT / "schema_audit_branches.csv", index=False)
    (OUT / "schema_audit_summary.json").write_text(json.dumps(dict(n_required_branches=len(need), files_checked=int(len(df)), files_with_error=int((df.error.fillna("") != "").sum()),
                                                                 complete_files=int(((df.get("n_missing", pd.Series(dtype=float)) == 0)).sum())), indent=1) + "\n")
    print(df.drop(columns=["url", "missing"], errors="ignore").to_string())


if __name__ == "__main__":
    main()
