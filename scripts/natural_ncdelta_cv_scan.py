#!/usr/bin/env python
"""Natural NC Delta -> N gamma census in the ordinary BNB CV merged CAFs (truth only; no cuts, no candidate selection).

    source env/setup_eaf.sh
    python scripts/natural_ncdelta_cv_scan.py scan --workers 28 [--limit N]
    python scripts/natural_ncdelta_cv_scan.py merge        # -> $SP_DATA/natural_ncdelta_bnb_cv/{signal_neutrinos,events,files}.parquet

The signal definition is EXACTLY the one validated on the dedicated EX_ncdeltarad sample: an NC neutrino whose GENIE record
(GenieEvtRecTree) has a status-1 photon with a Delta0/Delta+ mother (truth_signal.genie_record_ancestry). No resnum, no proxy.
Rows keep (file_index, ev, run, subrun, evt) and the qualifying rec.mc.nu index ``nu_k`` (position in the event's rec.mc.nu array).
"""
from __future__ import annotations
import argparse, os, sys, time, warnings
import multiprocessing as mp
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
SPD = os.environ.get("SP_DATA", "/tmp"); ROOT = Path(SPD) / "natural_ncdelta_bnb_cv"


def work(job):
    import numpy as np, awkward as ak
    from sbnd_single_photon import truth_signal as TS
    idx, url, outdir = job
    out = Path(outdir) / f"{idx}.npz"
    if out.exists():
        return idx, "cached"
    try:
        d = TS.read_truth_arrays(url)
        n = len(d["ids"]["run"]); g = lambda c: d["rec.mc.nu." + c]
        an = TS.record_ancestry_jagged(d["records"], g("genie_evtrec_idx")) if d.get("records") else None
        fl = lambda a: ak.to_numpy(ak.flatten(a, axis=1))
        nn = ak.to_numpy(ak.num(g("pdg"), axis=1))
        r = dict(n_events=n, TotalPOT=d["TotalPOT"], TotalGenEvents=d["TotalGenEvents"], has_record=bool(d.get("records")),
                 ev_run=np.asarray(d["ids"]["run"]), ev_subrun=np.asarray(d["ids"]["subrun"]), ev_evt=np.asarray(d["ids"]["evt"]), ev_n_nu=nn)
        if an is None and nn.sum() > 0:
            return idx, "ERR no GenieEvtRecTree but neutrinos present"
        if an is not None and nn.sum() > 0:
            nu_ev = np.repeat(np.arange(n), nn); k = ak.to_numpy(ak.flatten(ak.local_index(g("pdg"), axis=1), axis=1))
            q = (fl(g("isnc")) == 1) & fl(an["is_delta_rad"]).astype(bool)
            pp = TS._regroup(d["rec.mc.nu.prim.pdg"], g("nprim")); pe = TS._regroup(d["rec.mc.nu.prim.genE"], g("nprim"))
            ke = (pe - TS.PROTON_MASS_GEV) * 1000.0
            sel = lambda a: a[q]
            r.update(nu_ev=sel(nu_ev), nu_k=sel(k), nu_pdg=sel(fl(g("pdg"))), nu_E=sel(fl(g("E"))), nu_resnum=sel(fl(g("resnum"))), nu_mode=sel(fl(g("genie_mode"))),
                     nu_x=sel(fl(g("position.x"))), nu_y=sel(fl(g("position.y"))), nu_z=sel(fl(g("position.z"))),
                     nu_delta_pdg=sel(fl(an["delta_pdg"])), nu_nucleon_pdg=sel(fl(an["nucleon_pdg"])), nu_nucleon_status=sel(fl(an["nucleon_status"])),
                     nu_photon_mev=sel(fl(an["photon_e_gev"])) * 1000.0, nu_int_type=sel(fl(an["int_type"])),
                     nu_n_p35=sel(fl(ak.sum((pp == 2212) & (ke > 35), axis=-1))), nu_n_p_all=sel(fl(ak.sum(pp == 2212, axis=-1))),
                     nu_n_photons=sel(fl(ak.sum(pp == 22, axis=-1))), nu_n_pi0=sel(fl(ak.sum(pp == 111, axis=-1))), nu_n_pic=sel(fl(ak.sum(abs(pp) == 211, axis=-1))),
                     nu_n_nc_in_event=ak.to_numpy(ak.sum(g("isnc") == 1, axis=1))[nu_ev][q])
        tmp = out.with_name(out.name + ".tmp.npz"); np.savez_compressed(tmp, **{k: np.asarray(v) for k, v in r.items()}); os.replace(tmp, out)
        return idx, "ok"
    except Exception as e:
        return idx, "ERR " + repr(e)[:300]


def scan(a):
    from sbnd_single_photon import samples as S
    s = S.load_samples()["bnb_cv"]; urls = S.manifest_urls(s, a.start, None if a.limit is None else a.start + a.limit)
    pdir = ROOT / "pieces"; pdir.mkdir(parents=True, exist_ok=True)
    jobs = [(a.start + i, u, str(pdir)) for i, u in enumerate(urls)]; t0 = time.time(); bad = 0
    with mp.get_context("spawn").Pool(a.workers) as p:
        for k, (i, st) in enumerate(p.imap_unordered(work, jobs, chunksize=4)):
            if st.startswith("ERR"):
                bad += 1; print(f"file {i}: {st}", flush=True)
            if (k + 1) % 1000 == 0: print(f"{k+1}/{len(jobs)} {bad} errors {time.time()-t0:.0f}s", flush=True)
    print(f"DONE {len(jobs)} files, {bad} errors, {time.time()-t0:.0f}s", flush=True)


def merge(a):
    import numpy as np, pandas as pd
    from sbnd_single_photon import samples as S
    nf = S.load_samples()["bnb_cv"].n_files_listed; pdir = ROOT / "pieces"
    have = sorted(int(p.stem) for p in pdir.glob("*.npz") if not p.name.endswith(".tmp.npz"))
    if len(have) != nf: raise SystemExit(f"INCOMPLETE {len(have)}/{nf}")
    F, E, N = [], [], []
    for i in have:
        z = np.load(pdir / f"{i}.npz", allow_pickle=False); n = int(z["n_events"])
        F.append(dict(file_index=i, n_events=n, TotalPOT=float(z["TotalPOT"]), TotalGenEvents=float(z["TotalGenEvents"]), has_record=bool(z["has_record"])))
        E.append(pd.DataFrame(dict(file_index=i, ev=np.arange(n), run=z["ev_run"], subrun=z["ev_subrun"], evt=z["ev_evt"], n_nu=z["ev_n_nu"])))
        if "nu_ev" in z.files and len(z["nu_ev"]):
            N.append(pd.DataFrame({"file_index": i, "ev": z["nu_ev"], **{k[3:]: z[k] for k in z.files if k.startswith("nu_") and k != "nu_ev"}}))
    pd.DataFrame(F).to_parquet(ROOT / "files.parquet"); pd.concat(E, ignore_index=True).to_parquet(ROOT / "events.parquet")
    pd.concat(N, ignore_index=True).to_parquet(ROOT / "signal_neutrinos.parquet"); print("merged", len(F), "files; signal neutrinos", sum(len(x) for x in N))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["scan", "merge"]); ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--limit", type=int); ap.add_argument("--start", type=int, default=0); a = ap.parse_args()
    ROOT.mkdir(parents=True, exist_ok=True); scan(a) if a.cmd == "scan" else merge(a)
