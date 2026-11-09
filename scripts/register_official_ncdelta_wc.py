#!/usr/bin/env python
"""Register and validate the OFFICIAL NC Delta Wire-Cell merged CAFs when they arrive (READ-ONLY; never guesses a path).

Give EXACTLY ONE source of files, whatever Haiwang provides:
    --manifest <tsv[.gz]>        index<TAB>pnfs_path<TAB>xrootd_url  (the repository manifest format) or a plain list of paths/URLs
    --file-list <file>           one path / pnfs path / root:// URL per line
    --directory <path>           a directory readable from this machine (recursive *.root); /pnfs paths are mapped to the XRootD door
    --sam-definition <name>      read-only SAM (env/sam_eaf.sh): list-definition-files + locate-file -> XRootD URLs

    source env/setup_eaf.sh
    python scripts/register_official_ncdelta_wc.py --file-list files.txt --provenance producer_declaration.yaml --workers 20

For every file: recTree + recTreeWireCell, entry alignment, run/subrun/event alignment, wc.valid, schema md5, Trun provenance (dl_weights, wct_version,
input_file), GenieEvtRecTree, T_match/T_overlap/T_truth_nu/T_truth_pf/T_truth_track, every baseline branch. Events are reconciled against the
canonical truth set ($SP_DATA/official_gen2_ncdelta_master/signal_events.parquet): expected / represented / wc.valid / missing / duplicates /
unexpected. The provenance gate (configs/official_signal_provenance_gate.yaml) is evaluated; nothing is discarded silently.
Outputs: manifests/official_gen2_ncdelta_wc.tsv.gz (repository convention), $SP_DATA/official_signal_arrival/{files,events}.parquet,
tables/official_signal/arrival_registration.json (+ gate CSV). It does NOT edit configs/samples.yaml (it prints the block to add).
Workers: default 20, never above 24 (EAF: 32 cores); BLAS/OMP threads are pinned to 1.
"""
from __future__ import annotations
import argparse, gzip, hashlib, json, os, subprocess, sys, warnings
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
import multiprocessing as mp
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import pandas as pd
import yaml

MAX_WORKERS = 24


def _lines(path):
    opener = gzip.open if str(path).endswith(".gz") else open
    with opener(path, "rt") as fh:
        return [l.rstrip("\n") for l in fh if l.strip() and not l.startswith("#")]


def paths_from_source(a) -> list[str]:
    from sbnd_single_photon import xrd
    if a.manifest or a.file_list:
        rows = _lines(a.manifest or a.file_list)
        out = []
        for l in rows:
            if l.startswith("index\t"):
                continue
            parts = l.split("\t")
            out.append(parts[-1] if len(parts) == 3 else parts[0])      # repository manifest: third column is the URL
        return out
    if a.directory:
        d = Path(a.directory)
        if not d.is_dir():
            raise SystemExit(f"--directory {d} is not a directory visible from this machine")
        return sorted(str(p) for p in d.rglob("*.root"))
    # SAM definition, read-only
    def sam(*args):
        r = subprocess.run([str(REPO / "env" / "sam_eaf.sh"), *args], capture_output=True, text=True)
        if r.returncode:
            raise SystemExit("SAM failed: " + r.stderr[-300:])
        return r.stdout.split("\n")
    names = [n for n in sam("list-definition-files", a.sam_definition) if n.strip()]
    out = []
    for n in names:
        locs = [l for l in sam("locate-file", n) if l.strip()]
        if not locs:
            raise SystemExit(f"no location for {n}: not guessing a path")
        out.append(xrd.to_xrootd_url(locs[0].split(":", 1)[-1].split("(")[0].strip() + "/" + n))
    return out


def _inspect(job):
    from sbnd_single_photon import signal_arrival as A
    i, p, required = job
    r = A.inspect_merged_caf(p, required=required)
    ev = r.pop("events", None)
    if ev is not None:
        ev["file_index"] = i; ev["file"] = Path(p).name; ev["unit"] = A.normalize_unit_name(p)
    r["file_index"] = i
    return r, ev


def build_facts(files: pd.DataFrame, rec: dict, declared: dict) -> dict:
    """Flat fact dictionary for the gate: measured aggregates + the producer's declaration (absent -> UNKNOWN in the gate)."""
    ok = files[files.opened.fillna(False)]
    allf = lambda col: bool(len(files) > 0 and files[col].fillna(False).astype(bool).all())
    f = dict(all_files_have_recTree_and_recTreeWireCell=allf("has_recTree") and allf("has_recTreeWireCell"),
             all_files_entries_aligned=allf("entries_aligned"), all_files_ids_aligned=allf("ids_aligned"), all_files_have_wc_valid=allf("has_wc_valid"),
             all_files_have_truth_and_matching_trees=all(allf("has_" + t) for t in ("T_match", "T_overlap", "T_truth_nu", "T_truth_pf", "T_truth_track")),
             all_files_have_GenieEvtRecTree=allf("has_geniegevtrec"),
             baseline_required_branches_present=bool(len(ok) > 0 and ok.missing_baseline_branches.map(lambda x: len(x) == 0).all()),
             n_files_with_error=int(files.error.notna().sum()),
             event_keys_accounted=True, duplicate_event_rows=rec["duplicate_rows"], unexpected_event_rows=rec["unexpected_rows"],
             unit_mismatch_rows=rec["unit_mismatch"], wc_valid_accounted=bool(rec["represented_wc_valid"] + rec["represented_wc_invalid"] + rec["missing"] == rec["expected_events"]),
             missing_events=rec["missing"],
             n_distinct_schema_md5=int(ok.schema_md5.nunique()), n_distinct_dl_weights=int(ok.dl_weights.nunique()),
             schema_md5_set_equals_fg1=bool(set(ok.schema_md5.dropna()) == {"d4396a3490ea5aec4b02f0c34fa9db33"}),
             dl_weights=(ok.dl_weights.dropna().iloc[0] if ok.dl_weights.nunique() == 1 else sorted(map(str, ok.dl_weights.dropna().unique()))),
             wct_version_set=sorted(map(str, ok.wct_version.dropna().unique())), bdt_weights_dir_set=sorted(map(str, ok.get("bdt_weights_dir", pd.Series(dtype=str)).dropna().unique())) or ["not recorded"],
             n_wc_branches_set=sorted(int(x) for x in ok.n_wc_branches.dropna().unique()))
    from sbnd_single_photon import selection as SEL
    f["baseline_selection_sha256_matches_frozen"] = _sha(REPO / "configs/baseline_selection.yaml") == FROZEN_SELECTION_SHA256
    for k in ("declared_same_evaluation_chain_as_fg1", "declared_uses_dv2_max", "declared_uses_fix2", "declared_alternative_bdt_training",
              "declared_wct_commit", "declared_larwirecell_commit", "declared_sbndcode_version"):
        if k in declared:
            f[k] = declared[k]
    return f


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# sha256 of configs/baseline_selection.yaml as frozen with the BNB CV baseline (tests assert the repository file still matches; changing the cuts changes this)
FROZEN_SELECTION_SHA256 = "f3251b785be6e52ff3e429000a0319a6df8e42d2016ace2f51c7650a38e2fb0b"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--manifest"); g.add_argument("--file-list"); g.add_argument("--directory"); g.add_argument("--sam-definition")
    ap.add_argument("--provenance", help="producer declaration YAML: declared_* facts (same chain as fg1, DV2-MAX, Fix2, alternative BDT, commits)")
    ap.add_argument("--workers", type=int, default=20)
    ap.add_argument("--truth-events", default=None); ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out-root", default=os.path.join(os.environ.get("SP_DATA", "/tmp"), "official_signal_arrival"))
    ap.add_argument("--no-git-manifest", action="store_true", help="do not write manifests/official_gen2_ncdelta_wc.tsv.gz")
    ap.add_argument("--summary-dir", default=str(REPO / "tables" / "official_signal"), help="where arrival_registration.json / arrival_provenance_gate.csv go (use a scratch dir for dry runs)")
    a = ap.parse_args()
    from sbnd_single_photon import signal_arrival as A, selection as SEL, xrd
    workers = min(a.workers, MAX_WORKERS)
    paths = paths_from_source(a)[: a.limit]
    if not paths:
        raise SystemExit("the source lists no files")
    cfg = SEL.load_config(); required = A.required_wc_branches(cfg)
    truth_events = pd.read_parquet(a.truth_events or Path(os.environ["SP_DATA"]) / "official_gen2_ncdelta_master" / "signal_events.parquet")
    expected = truth_events[["run", "subrun", "evt", "reco1_unit", "flatcaf"]].copy()
    with mp.get_context("spawn").Pool(workers) as p:
        res = list(p.imap_unordered(_inspect, [(i, x, required) for i, x in enumerate(paths)], chunksize=1))
    files = pd.DataFrame([r for r, _ in res]).sort_values("file_index").reset_index(drop=True)
    events = pd.concat([e for _, e in res if e is not None], ignore_index=True) if any(e is not None for _, e in res) else \
        pd.DataFrame(columns=["run", "subrun", "evt", "wc_valid", "file_index", "file", "unit"])
    rec = A.reconcile_event_keys(expected, events)
    declared = yaml.safe_load(open(a.provenance)) if a.provenance else {}
    facts = build_facts(files, rec, declared)
    gate = A.evaluate_gate(A.load_gate(), facts)
    out = Path(a.out_root); out.mkdir(parents=True, exist_ok=True)
    files.drop(columns=["events"], errors="ignore").astype({"missing_baseline_branches": str}, errors="ignore").to_parquet(out / "files.parquet", index=False)
    events.to_parquet(out / "events.parquet", index=False)
    for k in ("_missing_rows", "_duplicate_rows", "_unexpected_rows", "_unit_mismatch_rows"):
        if k in rec:
            rec[k].to_parquet(out / (k.strip("_") + ".parquet"), index=False)
    tab = Path(a.summary_dir); tab.mkdir(parents=True, exist_ok=True)
    gate["table"].to_csv(tab / "arrival_provenance_gate.csv", index=False)
    summary = dict(source=dict(manifest=a.manifest, file_list=a.file_list, directory=a.directory, sam_definition=a.sam_definition), n_files=len(paths),
                   reconciliation={k: v for k, v in rec.items() if not k.startswith("_")}, facts={k: v for k, v in facts.items()},
                   gate=dict(open=gate["open"], required_failed=gate["required_failed"], required_unknown=gate["required_unknown"],
                             expected_not_passing=gate["expected_not_passing"]))
    (tab / "arrival_registration.json").write_text(json.dumps(summary, indent=1, default=str))
    if not a.no_git_manifest:
        mp_ = REPO / "manifests" / "official_gen2_ncdelta_wc.tsv.gz"
        with gzip.open(mp_, "wt") as fh:
            fh.write("index\tpnfs_path\txrootd_url\n")
            for i, x in enumerate(paths):
                fh.write(f"{i}\t{x}\t{xrd.resolve(x)}\n")
    print(json.dumps(summary["reconciliation"], indent=1)); print("GATE OPEN:", gate["open"], "| required failed:", gate["required_failed"], "| unknown:", gate["required_unknown"])
    print(f"\nTo enable the readers, add to configs/samples.yaml (official_gen2_ncdelta): status: available, wirecell_merged_status: available, "
          f"manifest: manifests/official_gen2_ncdelta_wc.tsv.gz, n_files_listed: {len(paths)}, is_mc: true  -- only after the gate is OPEN.")
    sys.exit(0 if gate["open"] else 2)


if __name__ == "__main__":
    main()
