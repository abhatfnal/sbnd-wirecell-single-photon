#!/usr/bin/env python
"""Resumable parallel candidate-level scan of one sample with the frozen baseline chain (NO tuning, NO FV).

    source env/setup_eaf.sh
    python scripts/baseline_scan.py bnb_cv --workers 24 [--limit N]

Per file it writes ``$SP_DATA/baseline_scan/<sample>/<file_index>.npz`` (skipped if present, so a killed run resumes).
Each npz holds EVENT arrays (ev_*), CANDIDATE arrays (c_*, one row per neutrino candidate of every event, valid or not)
and per-feature BDT-input non-finite counts. No cut is applied here: all cuts, both candidate policies, truth categories
and proton categories are evaluated afterwards from these tables by scripts/baseline_report.py.
Exposure is the per-file ``TotalPOT`` (never de-duplicated by run/subrun).
"""
from __future__ import annotations
import argparse, os, sys, time, traceback, warnings
import multiprocessing as mp
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
warnings.filterwarnings("ignore")

TAG = "wc.T_tagger."
KIN = "wc.T_kine."
TAG_COLS = ["nu_index", "shw_sp_filled", "shw_sp_n_20mev_showers", "shw_sp_n_20br1_showers",
            "flash_group", "matched_flash_gid", "flash_time_us", "flash_pe", "flash_tpc"]
KIN_COLS = ["kine_nu_x_corr", "kine_nu_y_corr", "kine_nu_z_corr"]
TRUTH_REC = ["rec.mc.nu.pdg", "rec.mc.nu.iscc", "rec.mc.nu.isnc", "rec.mc.nu.npizero", "rec.mc.nu.nprim", "rec.mc.nu.prim.pdg",
             "rec.mc.nu.position.x", "rec.mc.nu.position.y", "rec.mc.nu.position.z"]
NESTED = ["kine_particle_type", "kine_energy_particle", "kine_energy_included", "kine_particle_pool"]
_G = {}


def _init():
    from sbnd_single_photon import bdt as B, selection as SEL
    _G["models"] = B.load_models(); _G["cfg"] = SEL.load_config()


def work(job):
    """One retry on a transient (XRootD/IO) error; the second failure is returned as 'ERR ...' (never raised)."""
    res = _work(job)
    if res[1].startswith("ERR"):
        time.sleep(2)
        res = _work(job)
    return res


def _work(job):
    import numpy as np, awkward as ak
    from sbnd_single_photon import caf as C, baseline as BL, selection as SEL, truth as T, proton as P
    sample, idx, url, is_mc, outdir = job
    out = Path(outdir) / f"{idx}.npz"
    if out.exists():
        return idx, "cached", 0.0
    t0 = time.time()
    models, cfg = _G["models"], _G["cfg"]
    req = SEL.required_branches(cfg)
    try:
        with C.MergedCaf(url) as f:
            n = f.num_entries
            extra_wc = [TAG + c for c in TAG_COLS if f.has_wc(TAG + c)] + [KIN + c for c in KIN_COLS if f.has_wc(KIN + c)]
            d = BL.read_baseline_arrays(f, models, extra_wc=extra_wc, cut_branches=req["wc"],
                                        extra_rec=TRUTH_REC if (is_mc and f.has_truth_matching) else [])
            nested = {c: f.read_nested(KIN + c) for c in NESTED if f.has_wc(KIN + c)}
            pot = float(f._f["TotalPOT"].values()[0]) if "TotalPOT" in f._f else float("nan")
            gen = float(f._f["TotalGenEvents"].values()[0]) if "TotalGenEvents" in f._f else float("nan")
            md5 = f.schema_md5(); dlw = f.trun("dl_weights")
            ids = d["ids"]
            r = {"pot": pot, "gen": gen, "n_events": n}
            valid = np.asarray(ak.to_numpy(d["wc.valid"]) == 1)
            ncand = ak.to_numpy(ak.num(d[TAG + "nu_index"], axis=1))
            r.update(ev_valid=valid, ev_ncand=ncand.astype(np.int16), ev_run=np.asarray(ids["run"]),
                     ev_subrun=np.asarray(ids["subrun"]), ev_evt=np.asarray(ids["evt"]))
            ev_of = np.repeat(np.arange(n), ncand)
            r["c_ev"] = ev_of.astype(np.int32)
            for c in TAG_COLS + KIN_COLS:
                k = (TAG if c in TAG_COLS else KIN) + c
                if k in d:
                    r["c_" + c] = ak.to_numpy(ak.flatten(d[k], axis=1)).astype(np.float64)
            for b in req["wc"]:
                r.setdefault("c_" + b.split(".")[-1], ak.to_numpy(ak.flatten(d[b], axis=1)).astype(np.float64))
            for m in models:
                r[f"c_score_{m}"] = ak.to_numpy(ak.flatten(d[f"derived.single_photon_{m}_score"], axis=1)).astype(np.float64)
            filled = r["c_shw_sp_filled"] != 0
            # per-feature non-finite counts (all candidates / filled candidates) and non-finite input count per candidate
            for m, pairs in BL.bdt_input_map(models).items():
                X = np.column_stack([ak.to_numpy(ak.flatten(d[b], axis=1)).astype(np.float64) for _, b in pairs]) \
                    if len(ev_of) else np.zeros((0, len(pairs)))
                nf = ~np.isfinite(X)
                r[f"c_nnf_{m}"] = nf.sum(axis=1).astype(np.int16)
                r[f"featnf_all_{m}"] = nf.sum(axis=0).astype(np.int64)
                r[f"featnf_filled_{m}"] = nf[filled].sum(axis=0).astype(np.int64)
            # protons (candidate local rows)
            if nested:
                pdg, ke = nested["kine_particle_type"], nested["kine_energy_particle"]
                inc = nested.get("kine_energy_included")
                fl = lambda a: ak.to_numpy(ak.flatten(a, axis=1))
                r["c_np35"] = fl(P.count_reco_protons(pdg, ke)).astype(np.int16)
                if inc is not None:
                    r["c_np35_inc"] = fl(P.count_reco_protons(pdg, ke, included=inc, require_included=True)).astype(np.int16)
                r["c_nrows"] = fl(ak.num(pdg, axis=2)).astype(np.int16)
                r["c_np_anyke"] = fl(ak.sum(pdg == 2212, axis=2)).astype(np.int16)
            if is_mc and "rec.mc.nu.pdg" in d:
                # rec.mc.nu.npizero is almost always 0 in these CAFs (0 of 738 nu in a first check, 4 of 1014 in a later one, while 13-15% have a primary pi0);
                # the pi0 count is therefore taken from the GENIE primaries (prim.pdg == 111), regrouped per neutrino by nprim.
                n_pi0 = ak.sum(C.per_candidate(d["rec.mc.nu.prim.pdg"], d["rec.mc.nu.nprim"]) == 111, axis=-1)
                r["ev_t_npizero_field_nonzero"] = ak.to_numpy(ak.sum(d["rec.mc.nu.npizero"] > 0, axis=1)).astype(np.int16)
                ts = T.truth_summary(d["rec.mc.nu.pdg"], d["rec.mc.nu.iscc"], d["rec.mc.nu.isnc"], n_pi0,
                                     d["rec.mc.nu.position.x"], d["rec.mc.nu.position.y"], d["rec.mc.nu.position.z"])
                for k, v in ts.items():
                    r["ev_t_" + k] = v
        tmp = out.with_name(out.name + ".tmp.npz")             # atomic: a killed worker never leaves a half-written file
        np.savez_compressed(tmp, md5=str(md5), dlw=str(dlw), **r)
        os.replace(tmp, out)
        return idx, "ok", time.time() - t0
    except Exception as e:                                   # never kill the pool; the file is reported and can be re-run
        return idx, "ERR " + repr(e)[:300], time.time() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sample"); ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--limit", type=int, default=None); ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--out", default=os.path.join(os.environ.get("SP_DATA", "/tmp"), "baseline_scan"))
    a = ap.parse_args()
    from sbnd_single_photon import samples as S
    reg = S.load_samples(); s = reg[a.sample]
    urls = S.manifest_urls(s, a.start, None if a.limit is None else a.start + a.limit)
    outdir = Path(a.out) / a.sample; outdir.mkdir(parents=True, exist_ok=True)
    jobs = [(a.sample, a.start + i, u, bool(s.is_mc), str(outdir)) for i, u in enumerate(urls)]
    t0 = time.time(); nerr = 0
    with mp.get_context("spawn").Pool(a.workers, initializer=_init) as p:
        for k, (idx, st, dt) in enumerate(p.imap_unordered(work, jobs, chunksize=2)):
            if st.startswith("ERR"):
                nerr += 1; print(f"[{a.sample}] file {idx}: {st}", flush=True)
            if (k + 1) % 500 == 0:
                print(f"[{a.sample}] {k+1}/{len(jobs)} files, {nerr} errors, {time.time()-t0:.0f}s", flush=True)
    print(f"[{a.sample}] DONE {len(jobs)} files, {nerr} errors, {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
