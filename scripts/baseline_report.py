#!/usr/bin/env python
"""Aggregate a baseline_scan of one sample into the baseline tables (raw counts + 'selected events per 1e20 generated POT').

    python scripts/baseline_report.py bnb_cv [--scan $SP_DATA/baseline_scan]
Writes tables/baseline/<sample>_cutflow.{csv,json}, _truth_cutflow.csv, _final_composition.csv (MC only),
_evaluability.json and the proton-category split of the selected events.
Policies ``first`` and ``any`` are both PROVISIONAL. Exposure = sum of per-file TotalPOT of the files loaded.
nueCC (control) and the data samples: per-POT columns are written as None unless --allow-rates is given.
"""
from __future__ import annotations
import argparse, csv, json, os, sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from sbnd_single_photon import samples as S, scanio as X, selection as SEL, truth as T  # noqa: E402

OUT = REPO / "tables" / "baseline"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sample"); ap.add_argument("--scan", default=os.path.join(os.environ.get("SP_DATA", "."), "baseline_scan"))
    ap.add_argument("--allow-rates", action="store_true")
    a = ap.parse_args()
    cfg = SEL.load_config(); tab = X.load_scan(a.scan, a.sample); OUT.mkdir(parents=True, exist_ok=True)
    reg = S.load_samples()[a.sample]
    comp = X.completeness(tab, reg.n_files_listed, reg.n_caf_events)
    if not comp["complete"]:
        print(f"WARNING: INCOMPLETE SCAN {comp}", file=sys.stderr)
    control_only = (a.sample == "nuecc" or not reg.is_mc) and not a.allow_rates      # nueCC: unresolved normalisation; data: shapes only (no scale factor)
    pot = tab["pot_total"]; nev = len(tab["ev_valid"])
    meta = dict(sample=a.sample, n_files=tab["n_files"], n_events=nev, n_wc_valid=int(tab["ev_valid"].sum()),
                sum_TotalPOT=pot, sum_TotalGenEvents=tab["gen_total"],
                schema_md5=sorted(set(tab["file"]["md5"].tolist())), dl_weights=sorted(set(tab["file"]["dlw"].tolist())),
                completeness=comp, policies="provisional: first (nu_index==0) and any; NO fiducial volume; no weights",
                rates_note="per-POT columns suppressed: nueCC normalisation unresolved / data samples are shape-only (no scale factor)" if control_only else "POT-normalised neutrino-induced rate from the official filtered Gen2 CV sample = N / sum(TotalPOT) * 1e20 (TotalPOT = POT of ALL generated events; 26.5% stored, consistent with the 25% expected filter efficiency); Poisson on the raw count only; cosmic-only backgrounds are NOT represented and must come from beam-off (POT_EXPOSURE_AUDIT.md sec. 7)")
    rows = X.cutflow_rows(tab, cfg)
    if control_only:
        for r in rows:
            for k in [k for k in r if k.startswith("stored")]:
                r[k] = None
    cols = ["stage", "n_candidates", "n_events_any", "n_events_first", "stored_per_1e20_genPOT_any", "stored_err_per_1e20_genPOT_any",
            "stored_per_1e20_genPOT_first", "stored_err_per_1e20_genPOT_first", "note"]
    with open(OUT / f"{a.sample}_cutflow.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, cols, extrasaction="ignore"); w.writeheader(); w.writerows(rows)
    chain = X.candidate_chain(tab, cfg); final = chain[cfg["cuts"][-1]["name"]]
    # reco proton split of the selected events (candidate chosen by the policy)
    prot = {}
    for pol in ("first", "any"):
        idx = X.chosen_candidate(tab, final, pol); sel = idx >= 0
        for tag, col in (("ke>35", "c_np35"), ("ke>35 & included==1", "c_np35_inc")):
            if col in tab:
                code = X.proton_code(tab[col][idx[sel]])
                prot[f"{pol}|{tag}"] = {l: int((code == i).sum()) for i, l in enumerate(("0p", "1p", "ge2p"))}
    multi = np.bincount(tab["c_gev"][final], minlength=nev)
    meta["final_events_with_>1_passing_candidate"] = int((multi > 1).sum())
    (OUT / f"{a.sample}_cutflow.json").write_text(json.dumps(dict(meta=meta, cutflow=rows, final_reco_proton_split=prot), indent=1, default=str))
    # truth
    if "ev_t_code" in tab:
        stage_flags = {"candidate_exists": chain["candidate_in_valid_event"]}
        for c in cfg["cuts"]:
            stage_flags["cum:" + c["name"]] = chain[c["name"]]
        recs = []
        def emit(stage, pol, mask):
            for k, nm in enumerate(T.CATEGORIES):
                n = int((mask & (tab["ev_t_code"] == k)).sum())
                r, e = (None, None) if control_only else X.rate(n, pot)
                recs.append(dict(stage=stage, policy=pol, category=nm, n_raw=n, stored_per_1e20_genPOT=r, stored_err_per_1e20_genPOT=e))
        emit("all_events", "-", np.ones(nev, bool)); emit("wc_valid", "-", tab["ev_valid"])
        for st, fl in stage_flags.items():
            for pol in ("any", "first"):
                emit(st, pol, X.event_pass(tab, fl, pol))
        with open(OUT / f"{a.sample}_truth_cutflow.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, list(recs[0])); w.writeheader(); w.writerows(recs)
        comp = []
        for pol in ("first", "any"):
            idx = X.chosen_candidate(tab, final, pol); sel = idx >= 0
            for tag, col in (("ke>35", "c_np35"),):
                code = X.proton_code(tab[col][idx[sel]]) if col in tab else None
                for k, nm in enumerate(T.CATEGORIES):
                    m = tab["ev_t_code"][sel] == k
                    row = dict(policy=pol, category=nm, n_final=int(m.sum()))
                    for i, l in enumerate(("0p", "1p", "ge2p")):
                        row["n_" + l] = int((m & (code == i)).sum()) if code is not None else None
                    row["stored_per_1e20_genPOT"], row["stored_err_per_1e20_genPOT"] = (None, None) if control_only else X.rate(int(m.sum()), pot)
                    comp.append(row)
        with open(OUT / f"{a.sample}_final_composition.csv", "w", newline="") as fh:
            w = csv.DictWriter(fh, list(comp[0])); w.writeheader(); w.writerows(comp)
    print(json.dumps(meta, indent=1, default=str)); print(json.dumps(prot))
    for r in rows:
        print(f"{r['stage']:46s} cand={r['n_candidates']:>9} any={r['n_events_any']:>8} first={r['n_events_first']:>8}")


if __name__ == "__main__":
    main()
