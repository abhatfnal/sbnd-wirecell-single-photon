#!/usr/bin/env python
"""High-level runner of the signal baseline: register -> provenance gate -> build tables -> validate accounting -> report.

    source env/setup_eaf.sh
    # (A) the machinery on EXISTING data (no ROOT reads; natural NC Delta in the BNB CV; NOT the official sample)
    python scripts/run_official_signal_baseline.py rehearsal
    # (B) when Haiwang's merged CAFs exist (give exactly one of --manifest/--file-list/--directory/--sam-definition):
    python scripts/run_official_signal_baseline.py official --file-list files.txt --provenance producer_declaration.yaml --workers 20
    python scripts/run_official_signal_baseline.py official --skip-register --skip-build --region active_tpc   # re-report only

Official steps: (1) scripts/register_official_ncdelta_wc.py (inspection, event-key reconciliation, provenance gate; stops if the gate is closed),
(2) scripts/build_official_signal_analysis_table.py (same code as the BNB CV table + the truth join), (3) exact accounting identities,
(4) the report: truth denominator, wc.valid, candidates, BDT evaluable, every frozen cut, final any/first, total / 0p / 1p efficiency (exact binomial),
truth->reco migration, reco 1g0p / 1g1p / >=2p, Delta0 / Delta+ diagnostics, optional expected yield (needs --exposure-pot).
Outputs: tables/official_signal/<label>_<region>/ (small CSV/JSON; commit only when you intend to) and the filled arrival report.
Nothing is optimised or tuned. Workers <= 24.
"""
from __future__ import annotations
import argparse, json, os, subprocess, sys, warnings
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from sbnd_single_photon import exclusive_signal as X, natural_signal as NS, selection as SEL, signal_pipeline as SP, signal_master as SM

SPD = Path(os.environ["SP_DATA"]); TAB = REPO / "tables" / "official_signal"
TEMPLATE = REPO / "docs" / "analysis" / "OFFICIAL_NCDELTA_WC_ARRIVAL_REPORT_TEMPLATE.md"
NOT = "NOT COMPUTED: "


def run_report(sig_arrived, missing, events, cands, cfg, *, label, region, pot_signal=None, exposure_pot=None, tol_cm=5.0):
    """Library path shared by the rehearsal and the official sample. Returns (report dict, tab_any, tab_first, accounting)."""
    stage_names = [s for s, _ in X.stage_defs(cfg)]
    tabs = {}
    for p in ("any", "first"):
        t = X.signal_event_table(sig_arrived, events, cands, cfg, policy=p, tol_cm=tol_cm)
        tabs[p] = SP.with_missing_rows(t, missing, p)
    n_truth = len(sig_arrived) + len(missing)
    acc = SP.validate_accounting(n_truth, tabs["any"], tabs["first"], stage_names)
    rep = SP.signal_report(tabs["any"], tabs["first"], cfg, label=label, region=region, pot_signal=pot_signal, exposure_pot=exposure_pot)
    return rep, tabs["any"], tabs["first"], acc


def write_report(rep, tab_any, tab_first, acc, outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    for p in ("any", "first"):
        rep[f"cutflow_{p}"].to_csv(outdir / f"cutflow_A_{p}.csv", index=False)
        rep[f"first_failure_{p}"].to_csv(outdir / f"first_failure_A_{p}_by_truth.csv", index=False)
        for k, m in rep[f"migration_{p}"].items():
            m.to_csv(outdir / f"migration_{p}_{k}_raw.csv")
        for k, v in rep[f"delta_topology_{p}"].items():
            v.to_csv(outdir / f"delta_topology_{p}_{k}.csv")
    rep["efficiency"].to_csv(outdir / "efficiency.csv", index=False)
    pd.DataFrame(rep["selected_truth_to_reco"], index=[f"truth_{c}" for c in ("0p", "1p", "ge2p")], columns=[f"reco_{c}" for c in ("1g0p", "1g1p", "ge2p")]).to_csv(outdir / "selected_truth_to_reco_any.csv")
    js = {k: rep[k] for k in ("label", "region", "n_truth", "truth_class", "delta", "arrived", "missing", "wc_valid", "wc_invalid_arrived", "final_any", "final_first")}
    js["accounting"] = acc
    if "expected_yield" in rep:
        js["expected_yield"] = rep["expected_yield"]
    (outdir / "summary.json").write_text(json.dumps(js, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))


def fill_template(rep, tab_any, extra: dict) -> str:
    cf = rep["cutflow_any"]
    eff = rep["efficiency"]
    sel = lambda pol, cls: eff[(eff.policy == pol) & (eff.truth_class == cls)]
    mig = rep["migration_any"]; key = [k for k in mig if k.startswith("D_")][0]
    cand = cf[cf.stage == "candidate"][["group", "N", "fraction", "lo68", "hi68"]]
    ex = rep.get("expected_yield")
    y = lambda ch: markdown_ok(pd.DataFrame([dict(channel=ch, expected=ex["by_reco_channel"][ch], stat_unc=ex["by_reco_channel_stat_unc"][ch], exposure_pot=ex["exposure_pot"], region=ex["region"])])) if ex else NOT + "needs --exposure-pot and the signal-sample POT"
    markdown_ok = SP.markdown_table
    vals = dict(LABEL=rep["label"], REGION=rep["region"], GIT_COMMIT=extra.get("git_commit", "unknown"),
                FILE_INVENTORY=extra.get("file_inventory", NOT + "rehearsal: no merged-CAF inventory"),
                PROVENANCE=extra.get("provenance", NOT + "rehearsal: provenance gate applies to the official files only"),
                EVENT_KEYS=extra.get("event_keys", markdown_ok(pd.DataFrame([dict(expected=rep["n_truth"], represented=rep["arrived"], missing=rep["missing"])]))),
                WC_VALID=markdown_ok(pd.DataFrame([dict(arrived=rep["arrived"], wc_valid=rep["wc_valid"], wc_invalid=rep["wc_invalid_arrived"], missing=rep["missing"])])),
                CANDIDATE_EFF=markdown_ok(cand), CUTFLOW=markdown_ok(cf[["group", "stage", "N", "fraction", "lo68", "hi68"]]),
                EFF_TOTAL=markdown_ok(sel("any", "total").assign(policy_first=sel("first", "total").efficiency.values)),
                EFF_0P=markdown_ok(sel("any", "0p").assign(policy_first=sel("first", "0p").efficiency.values)),
                EFF_1P=markdown_ok(sel("any", "1p").assign(policy_first=sel("first", "1p").efficiency.values)),
                MIGRATION=markdown_ok(mig[key], index=True), YIELD_1G0P=y("1g0p"), YIELD_1G1P=y("1g1p"),
                DELTA_DIAG=markdown_ok(rep["delta_topology_any"]["reco_final_selected_stage"], index=True),
                REHEARSAL_COMPARISON=extra.get("rehearsal_comparison", NOT + "official mode: fill with scripts/run_official_signal_baseline.py rehearsal output"),
                DISCREPANCIES=extra.get("discrepancies", "none detected by the automatic accounting checks (manual review still required)"))
    return SP.render_template(TEMPLATE.read_text(), vals)


def git_commit():
    return subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()


def rehearsal(a):
    cfg = SEL.load_config(); T = SPD / "analysis_tables" / "bnb_cv"
    events = pd.read_parquet(T / "events.parquet"); cands = pd.read_parquet(T / "candidates.parquet")
    sn = pd.read_parquet(SPD / "natural_ncdelta_bnb_cv" / "signal_neutrinos.parquet")
    sig_all = NS.to_signal_truth_table(sn); sig = sig_all[sig_all.in_region].reset_index(drop=True)
    empty = sig.iloc[:0]
    rep, ta, tf, acc = run_report(sig, empty, events, cands, cfg, label="natural_bnb_cv_rehearsal", region="active_tpc")
    out = TAB / "rehearsal_natural_bnb_cv"; write_report(rep, ta, tf, acc, out)
    # exact comparison with the Phase-3 outputs (same data, independent code path through the library)
    ref = REPO / "tables" / "exclusive_signal" / "natural_bnb_cv"; cmp = {}
    for name in ("cutflow_A_any.csv", "cutflow_A_first.csv", "efficiency_crosscheck.csv"):
        mine = out / (name if name != "efficiency_crosscheck.csv" else "efficiency.csv")
        cmp[name] = bool(pd.read_csv(ref / name).round(10).equals(pd.read_csv(mine).round(10)))
    for p in ("any", "first"):
        for k in rep[f"migration_{p}"]:
            cmp[f"migration_{p}_{k}_raw.csv"] = bool(pd.read_csv(ref / f"migration_{p}_{k}_raw.csv", index_col=0).equals(pd.read_csv(out / f"migration_{p}_{k}_raw.csv", index_col=0)))
    s3 = json.load(open(ref / "summary.json"))
    cmp["denominator_117"] = rep["n_truth"] == 117 == s3["n_in_region"]
    cmp["final_any_13"] = rep["final_any"]["total"] == 13 == s3["final_any"]["total"]
    cmp["final_first_12"] = rep["final_first"]["total"] == 12 == s3["final_first"]["total"]
    cmp["truth_classes"] = rep["truth_class"] == {"0p": 59, "1p": 46, ">=2p": 12}
    cmp["ALL"] = all(cmp.values())
    (out / "rehearsal_comparison.json").write_text(json.dumps(cmp, indent=1))
    md = fill_template(rep, ta, dict(git_commit=git_commit(), rehearsal_comparison="rehearsal vs Phase-3 exact reproduction: " + json.dumps(cmp)))
    (out / "RENDERED_TEMPLATE_TEST.md").write_text("> RENDER TEST ON THE NATURAL-CV REHEARSAL. NOT the official sample; no official number is claimed.\n\n" + md)
    print(json.dumps(dict(n_truth=rep["n_truth"], final_any=rep["final_any"], final_first=rep["final_first"], reproduces_phase3=cmp["ALL"], accounting=acc["ok"])))
    return 0 if cmp["ALL"] else 1


def official(a):
    here = [sys.executable]
    if not a.skip_register:
        src = [x for x in ("manifest", "file_list", "directory", "sam_definition") if getattr(a, x)]
        if len(src) != 1:
            raise SystemExit("give exactly one of --manifest/--file-list/--directory/--sam-definition (paths are never guessed)")
        cmd = here + [str(REPO / "scripts" / "register_official_ncdelta_wc.py"), "--" + src[0].replace("_", "-"), getattr(a, src[0]), "--workers", str(min(a.workers, 24))]
        if a.provenance:
            cmd += ["--provenance", a.provenance]
        r = subprocess.run(cmd)
        if r.returncode != 0:
            raise SystemExit("registration / provenance gate did not pass: stopping (see tables/official_signal/arrival_registration.json)")
    if not a.skip_build:
        subprocess.run(here + [str(REPO / "scripts" / "build_official_signal_analysis_table.py"), "--workers", str(min(a.workers, 24))], check=True)
    cfg = SEL.load_config(); reg = SM.load_regions()
    region = a.region or "active_tpc"
    if region not in reg:
        raise SystemExit(f"unknown region {region!r}; known: {sorted(reg)}")
    base = SPD / "official_signal_baseline"; T = SPD / "analysis_tables" / "official_gen2_ncdelta"
    events = pd.read_parquet(T / "events.parquet"); cands = pd.read_parquet(T / "candidates.parquet")
    arrived = pd.read_parquet(base / f"signal_joined_{region}.parquet"); missing = pd.read_parquet(base / f"signal_missing_{region}.parquet")
    master = SPD / "official_gen2_ncdelta_master"
    units = pd.read_parquet(master / "units.parquet")
    arr = json.load(open(TAB / "arrival_registration.json"))
    present = set(arrived.reco1_unit) | set(missing.reco1_unit)
    pot_sig = float(units[units.flatcaf_status == "flatcaf_available"].unit_pot.sum())
    rep, ta, tf, acc = run_report(arrived, missing, events, cands, cfg, label="official_gen2_ncdelta", region=region, pot_signal=pot_sig, exposure_pot=a.exposure_pot)
    out = TAB / f"official_{region}"; write_report(rep, ta, tf, acc, out)
    extra = dict(git_commit=git_commit(), file_inventory=SP.markdown_table(pd.DataFrame([dict(files=arr["n_files"], opened_without_error=arr["n_files"] - arr["facts"]["n_files_with_error"])])),
                 provenance=SP.markdown_table(pd.read_csv(TAB / "arrival_provenance_gate.csv")[["id", "level", "status", "observed"]]),
                 event_keys=SP.markdown_table(pd.DataFrame([arr["reconciliation"]])))
    (out / "ARRIVAL_REPORT.md").write_text(fill_template(rep, ta, extra))
    print(json.dumps(dict(n_truth=rep["n_truth"], arrived=rep["arrived"], missing=rep["missing"], final_any=rep["final_any"], final_first=rep["final_first"])))
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="mode", required=True)
    sub.add_parser("rehearsal")
    o = sub.add_parser("official")
    for k in ("manifest", "file_list", "directory", "sam_definition", "provenance"):
        o.add_argument("--" + k.replace("_", "-"), dest=k)
    o.add_argument("--workers", type=int, default=20); o.add_argument("--region"); o.add_argument("--exposure-pot", type=float, default=None)
    o.add_argument("--skip-register", action="store_true"); o.add_argument("--skip-build", action="store_true")
    a = ap.parse_args()
    sys.exit(rehearsal(a) if a.mode == "rehearsal" else official(a))


if __name__ == "__main__":
    main()
