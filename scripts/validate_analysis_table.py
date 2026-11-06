#!/usr/bin/env python
"""Validate the derived analysis table of a sample EXACTLY against the existing full-scan tables (tables/baseline/*.csv) and,
optionally, element-wise against the raw per-file scan (baseline_scan npz). Integer counts must match exactly.

    python scripts/validate_analysis_table.py bnb_cv [--elementwise] [--out tables/analysis_table/bnb_cv_validation.json]
Exit status 1 if any exact check fails.
"""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path
import numpy as np, pandas as pd
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src"))
from sbnd_single_photon import truth as T, selection as SEL, scanio as SIO  # noqa: E402

EXPECT_EVENTS, EXPECT_VALID, EXPECT_ANY, EXPECT_FIRST = 500_000, 499_899, 649, 626
EXPECT_SPLIT = {"any": (318, 236, 95), "first": (307, 226, 93)}


def compute(c: pd.DataFrame, e: pd.DataFrame, cfg) -> dict:
    """Everything the baseline report derives, from the table alone."""
    stages = ["cum_" + s for s in ["candidate_in_valid_event"] + [x["name"] for x in cfg["cuts"]]]
    key = c.file_index.astype(np.int64) * 10_000 + c.ev.astype(np.int64)
    ev_key = e.file_index.astype(np.int64) * 10_000 + e.ev.astype(np.int64)
    pos = pd.Series(np.arange(len(e)), index=ev_key.values).reindex(key.values).values
    out = {"n_events": int(len(e)), "n_valid": int(e.wc_valid.sum()), "n_candidates": int(len(c)), "stages": {}}
    for s in stages:
        f = c[s].values
        any_ev = np.zeros(len(e), bool); any_ev[pos[f]] = True
        fst = np.zeros(len(e), bool); fst[pos[f & c.policy_first.values]] = True
        out["stages"][s] = dict(n_candidates=int(f.sum()), n_events_any=int(any_ev.sum()), n_events_first=int(fst.sum()))
    fin = c.pass_final.values
    comp = {}
    for pol in ("any", "first"):
        m = fin & (c.policy_first.values if pol == "first" else True)
        sel = c[m].assign(pos=pos[m]).sort_values(["pos", "c_nu_index"]).drop_duplicates("pos")      # lowest nu_index passing
        cat = np.array(T.CATEGORIES)[e.t_code.values[sel.pos.values].astype(int)]
        d = pd.DataFrame({"category": cat, "p": sel.reco_proton_cat.values})
        comp[pol] = {k: dict(n=int(len(g)), n_0p=int((g.p == 0).sum()), n_1p=int((g.p == 1).sum()), n_ge2p=int((g.p == 2).sum())) for k, g in d.groupby("category")}
        comp[pol]["_total"] = dict(n=int(len(d)), n_0p=int((d.p == 0).sum()), n_1p=int((d.p == 1).sum()), n_ge2p=int((d.p == 2).sum()))
    out["composition"] = comp
    return out


def fast_scan(directory, sample, cols):
    """Threaded read of only the needed arrays of every per-file scan npz (same row order as scanio.load_scan: numeric file order)."""
    from concurrent.futures import ThreadPoolExecutor
    d = Path(directory) / sample
    files = sorted((p for p in d.glob("*.npz") if not p.name.endswith(".tmp.npz")), key=lambda p: int(p.stem))
    keys = ["ev_valid", "ev_run", "ev_subrun", "ev_evt", "ev_t_code", "c_ev"] + list(cols)
    def one(p):
        z = np.load(p, allow_pickle=False)
        return {k: z[k] for k in keys}
    with ThreadPoolExecutor(32) as ex:
        parts = list(ex.map(one, files))
    offs = np.cumsum([0] + [len(x["ev_valid"]) for x in parts])
    t = {k: np.concatenate([x[k] for x in parts]) for k in keys if k != "c_ev"}
    t["c_gev"] = np.concatenate([x["c_ev"].astype(np.int64) + o for x, o in zip(parts, offs[:-1])])
    t["ev_file"] = np.repeat(np.arange(len(parts)), np.diff(offs))
    t["file_index"] = np.array([int(p.stem) for p in files])
    return t


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("sample"); ap.add_argument("--elementwise", action="store_true")
    ap.add_argument("--out"); ap.add_argument("--root", default=os.path.join(os.environ.get("SP_DATA", "/tmp"), "analysis_tables"))
    a = ap.parse_args()
    d = Path(a.root) / a.sample
    c, e, fl = (pd.read_parquet(d / f"{n}.parquet") for n in ("candidates", "events", "files"))
    cfg = SEL.load_config(); r = compute(c, e, cfg); checks = []
    def chk(name, got, exp):
        checks.append(dict(check=name, got=got, expected=exp, ok=bool(got == exp)))
    ref = pd.read_csv(REPO / "tables" / "baseline" / f"{a.sample}_cutflow.csv").set_index("stage")
    if a.sample == "bnb_cv":
        chk("events", r["n_events"], EXPECT_EVENTS); chk("wc.valid", r["n_valid"], EXPECT_VALID)
        fin = r["stages"]["cum_" + cfg["cuts"][-1]["name"]]
        chk("final any", fin["n_events_any"], EXPECT_ANY); chk("final first", fin["n_events_first"], EXPECT_FIRST)
        for pol in ("any", "first"):
            t = r["composition"][pol]["_total"]; chk(f"split {pol} 0p/1p/>=2p", (t["n_0p"], t["n_1p"], t["n_ge2p"]), EXPECT_SPLIT[pol])
    meta = json.load(open(REPO / "tables" / "baseline" / f"{a.sample}_cutflow.json"))["meta"]
    chk("files", int(len(fl)), int(meta["n_files"]))
    chk("candidate rows", r["n_candidates"], int(ref.loc["all_events", "n_candidates"]))
    chk("events (ref csv)", r["n_events"], int(ref.loc["all_events", "n_events_any"]))
    chk("wc.valid (ref csv)", r["n_valid"], int(ref.loc["wc_valid", "n_events_any"]))
    for s_, v in r["stages"].items():
        if s_ == "cum_candidate_in_valid_event":   # reference rows: wc_valid (candidates of valid events) / candidate_exists (events with >=1 candidate)
            chk("stage candidate_in_valid_event n_candidates", v["n_candidates"], int(ref.loc["wc_valid", "n_candidates"]))
            chk("stage candidate_exists n_events_any", v["n_events_any"], int(ref.loc["candidate_exists", "n_events_any"]))
            chk("stage candidate_exists n_events_first", v["n_events_first"], int(ref.loc["candidate_exists", "n_events_first"]))
            continue
        row = "cum:" + s_[4:]
        for k in ("n_candidates", "n_events_any", "n_events_first"):
            chk(f"stage {row} {k}", v[k], int(ref.loc[row, k]))
    comp = pd.read_csv(REPO / "tables" / "baseline" / f"{a.sample}_final_composition.csv")
    if len(comp):
        for _, row in comp.iterrows():
            got = r["composition"][row.policy].get(row.category, dict(n=0, n_0p=0, n_1p=0, n_ge2p=0))
            chk(f"composition {row.policy} {row.category}", (got["n"], got["n_0p"], got["n_1p"], got["n_ge2p"]),
                (int(row.n_final), int(row.n_0p), int(row.n_1p), int(row.n_ge2p)))
    # provenance uniqueness
    chk("candidate key (file,run,subrun,evt,nu_index) unique", int(c.duplicated(["file_index", "run", "subrun", "evt", "c_nu_index"]).sum()), 0)
    chk("event key (file,ev) unique", int(e.duplicated(["file_index", "ev"]).sum()), 0)
    chk("sum TotalPOT matches full-scan meta (rtol 1e-12)", bool(np.isclose(fl.total_pot.sum(), meta["sum_TotalPOT"], rtol=1e-12)), True)
    chk("sum TotalGenEvents matches full-scan meta", float(fl.total_gen_events.sum()), float(meta["sum_TotalGenEvents"]))
    if a.elementwise:                                           # raw scan vs table, every candidate and every event
        COLS = ["c_score_numu", "c_score_other", "c_score_ncpi0", "c_score_nue", "c_kine_nu_x_corr", "c_kine_nu_y_corr", "c_kine_nu_z_corr", "c_flash_time_us",
                "c_flash_pe", "c_shw_sp_n_20mev_showers", "c_shw_sp_n_20br1_showers", "c_shw_sp_filled", "c_np35", "c_nu_index"]
        t = fast_scan(os.path.join(os.environ["SP_DATA"], "baseline_scan"), a.sample, COLS)
        raw = pd.DataFrame({"file_index": t["file_index"][t["ev_file"]][t["c_gev"]], "run": t["ev_run"][t["c_gev"]],
                            "subrun": t["ev_subrun"][t["c_gev"]], "evt": t["ev_evt"][t["c_gev"]], "nu": t["c_nu_index"]})
        chk("candidate rows align (file,run,subrun,evt,nu_index) in order", bool((raw.values.astype(float) == c[["file_index", "run", "subrun", "evt", "c_nu_index"]].values.astype(float)).all()), True)
        for col in COLS[:-1]:
            chk(f"column {col} identical (NaN-aware)", bool(np.array_equal(t[col].astype(float), c[col].values.astype(float), equal_nan=True)), True)
        chk("event valid identical", bool((t["ev_valid"] == e.wc_valid.values).all()), True)
        chk("event truth code identical", bool((t["ev_t_code"] == e.t_code.values).all()), True)
        chk("bdt_evaluable identical", bool((SIO.bdt_evaluable(t) == c.bdt_evaluable.values).all()), True)
    bad = [k for k in checks if not k["ok"]]
    rep = dict(sample=a.sample, n_checks=len(checks), n_failed=len(bad), failed=bad, result=r, checks=checks)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True); Path(a.out).write_text(json.dumps(rep, indent=1, default=str))
    print(f"{len(checks)} checks, {len(bad)} failed"); [print("FAIL", k) for k in bad]
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
