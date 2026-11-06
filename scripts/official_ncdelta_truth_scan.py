#!/usr/bin/env python
"""TRUTH-ONLY census of the OFFICIAL Gen2 EX_ncdeltarad flatCAFs (no Wire-Cell, no efficiency). Resumable, per-file npz.

    source env/setup_eaf.sh
    python scripts/official_ncdelta_truth_scan.py scan  --workers 24 [--limit N]
    python scripts/official_ncdelta_truth_scan.py merge            # -> $SP_DATA/official_gen2_ncdelta_truth/{neutrinos,events,files}.parquet

Input manifest (outside Git, built from SAM): $SP_DATA/sam/official_gen2_ncdelta_flatcaf.locations.txt
(``enstore:<pnfs dir>\\t<file>\\t<size>``; the dCache path is converted with xrd.to_xrootd_url).
Reads only: recTree truth branches, TotalPOT/TotalGenEvents/TotalEvents, rec.hdr.pot, GenieEvtRecTree (StdHep pdg/status/mothers/daughters/E).
"""
from __future__ import annotations
import argparse, os, sys, time, warnings
import multiprocessing as mp
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
SPD = os.environ.get("SP_DATA", "/tmp"); ROOT = Path(SPD) / "official_gen2_ncdelta_truth"
LOC = Path(SPD) / "sam" / "official_gen2_ncdelta_flatcaf.locations.txt"
EXTRA = ["rec.hdr.pot", "rec.mc.nu.prim.gstatus", "rec.mc.nu.genweight", "rec.mc.nu.npizero", "rec.mc.nu.nproton", "rec.mc.nu.prim.startE",
         "rec.mc.nu.prim.cont_tpc"]


def manifest():
    from sbnd_single_photon import xrd
    rows = []
    for ln in LOC.read_text().splitlines():
        loc, name, size = ln.split("\t")
        assert loc.startswith("enstore:/pnfs/"), loc
        rows.append((name, int(size), xrd.to_xrootd_url(loc[len("enstore:"):] + "/" + name)))
    return rows


def work(job):
    import numpy as np, awkward as ak, uproot
    from sbnd_single_photon import truth_signal as TS
    idx, name, size, url, outdir = job
    out = Path(outdir) / f"{idx}.npz"
    if out.exists():
        return idx, "cached"
    try:
        with uproot.open(url) as f:
            t = f["recTree"]; n = int(t.num_entries)
            keys = set(t.keys())
            hist = {h: (float(f[h].values()[0]) if h in f else np.nan) for h in ("TotalPOT", "TotalGenEvents", "TotalEvents")}
            has_rec = "GenieEvtRecTree" in f
        r = dict(n_events=n, size=size, has_genie_record=has_rec, **{k: v for k, v in hist.items()})
        if n > 0:
            d = TS.read_truth_arrays(url)
            sig = TS.signal_truth_from_arrays(d, from_filter_stream=True)
            for k, v in sig.items():
                r["ev_" + k] = np.asarray(v)
            r["ev_run"], r["ev_subrun"], r["ev_evt"] = (np.asarray(d["ids"][k]) for k in ("run", "subrun", "evt"))
            g = lambda c: d["rec.mc.nu." + c]
            nn = ak.to_numpy(ak.num(g("pdg"), axis=1)); r["ev_n_nu"] = nn
            fl = lambda a: ak.to_numpy(ak.flatten(a, axis=1))
            r["nu_ev"] = np.repeat(np.arange(n), nn)
            for c in ("pdg", "isnc", "iscc", "genie_mode", "resnum", "E", "position.x", "position.y", "position.z", "nprim", "genie_evtrec_idx"):
                r["nu_" + c.replace(".", "_")] = fl(g(c))
            pp = TS._regroup(d["rec.mc.nu.prim.pdg"], g("nprim")); pe = TS._regroup(d["rec.mc.nu.prim.genE"], g("nprim"))
            ke = (pe - TS.PROTON_MASS_GEV) * 1000.0
            r["nu_n_photons"] = fl(ak.sum(pp == 22, axis=-1)); r["nu_n_photons_gt20"] = fl(ak.sum((pp == 22) & (pe * 1000 > 20), axis=-1))
            r["nu_max_photon_mev"] = fl(ak.fill_none(ak.max(pe[pp == 22], axis=-1), np.nan)) * 1000.0
            r["nu_n_p_all"] = fl(ak.sum(pp == 2212, axis=-1)); r["nu_n_p35"] = fl(ak.sum((pp == 2212) & (ke > 35), axis=-1))
            r["nu_n_pi0"] = fl(ak.sum(pp == 111, axis=-1)); r["nu_n_pic"] = fl(ak.sum(abs(pp) == 211, axis=-1)); r["nu_n_n"] = fl(ak.sum(pp == 2112, axis=-1))
            if d.get("records"):
                an = TS.record_ancestry_jagged(d["records"], g("genie_evtrec_idx"))
                for k in ("is_delta_rad", "delta_pdg", "nucleon_pdg", "nucleon_status", "photon_e_gev", "via_photon", "int_type"):
                    r["nu_rec_" + k] = fl(an[k])
            # field behaviour checks (BNB-CV comparison): gstatus, genweight, npizero, nproton, startE sentinel
            with uproot.open(url) as f2:
                ex = f2["recTree"].arrays([b for b in EXTRA if b in keys], library="ak")
            for b in ex.fields:
                a = ak.to_numpy(ak.flatten(ex[b], axis=None)).astype(float)
                r["chk_" + b.replace(".", "_") + "_n"] = len(a)
                if len(a):
                    r["chk_" + b.replace(".", "_") + "_min"] = a.min(); r["chk_" + b.replace(".", "_") + "_max"] = a.max()
                    r["chk_" + b.replace(".", "_") + "_nz"] = int((a != 0).sum()); r["chk_" + b.replace(".", "_") + "_sent"] = int((a <= -9000).sum())
        tmp = out.with_name(out.name + ".tmp.npz"); np.savez_compressed(tmp, **{k: np.asarray(v) for k, v in r.items()}); os.replace(tmp, out)
        return idx, "ok"
    except Exception as e:
        return idx, "ERR " + repr(e)[:300]


def scan(a):
    rows = manifest()
    if a.limit: rows = rows[a.start:a.start + a.limit]
    pdir = ROOT / "pieces"; pdir.mkdir(parents=True, exist_ok=True)
    jobs = [(a.start + i, n, s, u, str(pdir)) for i, (n, s, u) in enumerate(rows)]
    t0 = time.time(); bad = 0
    with mp.get_context("spawn").Pool(a.workers) as p:
        for k, (i, st) in enumerate(p.imap_unordered(work, jobs, chunksize=4)):
            if st.startswith("ERR"):
                bad += 1; print(f"file {i}: {st}", flush=True)
            if (k + 1) % 500 == 0: print(f"{k+1}/{len(jobs)} {bad} errors {time.time()-t0:.0f}s", flush=True)
    print(f"DONE {len(jobs)} files, {bad} errors, {time.time()-t0:.0f}s", flush=True)


def merge(a):
    import numpy as np, pandas as pd
    rows = manifest(); pdir = ROOT / "pieces"
    have = sorted(int(p.stem) for p in pdir.glob("*.npz") if not p.name.endswith(".tmp.npz"))
    if len(have) != len(rows): raise SystemExit(f"INCOMPLETE {len(have)}/{len(rows)}")
    F, E, N, C = [], [], [], []
    for i in have:
        z = np.load(pdir / f"{i}.npz", allow_pickle=False)
        f = dict(file_index=i, source_file=rows[i][0], size=rows[i][1], url=rows[i][2], **{k: float(z[k]) for k in ("n_events", "TotalPOT", "TotalGenEvents", "TotalEvents")},
                 has_genie_record=bool(z["has_genie_record"]))
        F.append(f)
        for k in z.files:
            if k.startswith("chk_"): f[k] = float(z[k])
        if int(z["n_events"]) == 0: continue
        n = int(z["n_events"])
        E.append(pd.DataFrame({"file_index": i, "ev": np.arange(n), **{k[3:]: z[k] for k in z.files if k.startswith("ev_") and z[k].ndim == 1 and len(z[k]) == n}}))
        nn = len(z["nu_ev"])
        N.append(pd.DataFrame({"file_index": i, **{k[3:]: z[k] for k in z.files if k.startswith("nu_") and z[k].ndim == 1 and len(z[k]) == nn}}))
    pd.DataFrame(F).to_parquet(ROOT / "files.parquet"); pd.concat(E, ignore_index=True).to_parquet(ROOT / "events.parquet"); pd.concat(N, ignore_index=True).to_parquet(ROOT / "neutrinos.parquet")
    print("merged", len(F), "files")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["scan", "merge"]); ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--limit", type=int); ap.add_argument("--start", type=int, default=0); a = ap.parse_args()
    ROOT.mkdir(parents=True, exist_ok=True)
    scan(a) if a.cmd == "scan" else merge(a)
