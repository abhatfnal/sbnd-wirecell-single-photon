#!/usr/bin/env python
"""Per-signal-neutrino TRUTH needed to reproduce the SPINE (medulla) NC-Delta signal definition on the official Gen2 flatCAFs. Resumable, truth only.

    source env/setup_eaf.sh
    python scripts/spine_truth_scan.py scan  --workers 24 [--limit N]
    python scripts/spine_truth_scan.py merge     # -> $SP_DATA/spine_harmonization/official_ncdelta/spine_truth.parquet

Extends scripts/differential_truth_scan.py (which stays reproducible and is NOT modified). For the signal neutrino chosen by the signal master
(``signal_nu_index``) it stores, as per-event LISTS over rec.mc.nu.prim: pdg, genE [GeV], start/end positions, contained / cont_tpc flags, end process, total visible
energy and hits over the six planes; and from the GENIE record the status-1 final-state class counts. Also the neutrino-level isnc/iscc/resnum/genie_mode/genie_inttype.
Provenance kept per row: run/subrun/evt, flatcaf name and size, signal nu index. Workers <= 24, BLAS/OMP threads pinned to 1.
Definitions: docs/analysis/SPINE_SIGNAL_DEFINITION_SOURCE_AUDIT.md.
"""
from __future__ import annotations
import argparse, hashlib, os, sys, warnings
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
import multiprocessing as mp
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd

SPD = Path(os.environ.get("SP_DATA", "/tmp")); OUT = SPD / "spine_harmonization" / "official_ncdelta"; PIECES = OUT / "spine_truth_pieces"
LOC = SPD / "sam" / "official_gen2_ncdelta_flatcaf.locations.txt"
P = "rec.mc.nu.prim."
PLANES = [f"{P}plane.{c}.{p}.{q}" for c in (0, 1) for p in (0, 1, 2) for q in ("visE", "nhit")]
PRIM = [P + c for c in ("pdg", "genE", "start.x", "start.y", "start.z", "end.x", "end.y", "end.z", "contained", "cont_tpc", "end_process", "genp.x", "genp.y", "genp.z")] + PLANES
NU = ["rec.mc.nu.nprim", "rec.mc.nu.isnc", "rec.mc.nu.iscc", "rec.mc.nu.resnum", "rec.mc.nu.genie_mode", "rec.mc.nu.genie_inttype", "rec.mc.nu.genie_evtrec_idx"]
SCHEMA = "spine-truth-1.0"


def genie_final_state_counts(records, idx):
    """Status-1 (stable final state) particle class counts of ONE GENIE record (entry ``idx``): photons, nucleons, neutrinos, pi0, charged pions, e/mu, others."""
    pdg = np.asarray(records["StdHepPdg"][idx]); st = np.asarray(records["StdHepStatus"][idx]); f = pdg[st == 1]; a = np.abs(f)
    c = dict(g1_n_photon=int((f == 22).sum()), g1_n_nucleon=int(np.isin(a, (2112, 2212)).sum()), g1_n_neutrino=int(np.isin(a, (12, 14, 16)).sum()), g1_n_pi0=int((f == 111).sum()),
             g1_n_pic=int((a == 211).sum()), g1_n_lepton=int(np.isin(a, (11, 13)).sum()))
    c["g1_n_other"] = int(len(f)) - sum(c.values())
    c["g1_n_total"] = int(len(f))
    return c


def read_one(url, rows):
    import awkward as ak, uproot
    from sbnd_single_photon import truth_signal as TS
    with uproot.open(url) as f:
        t = f["recTree"]; a = t.arrays(PRIM + NU, library="ak")
    d = TS.read_truth_arrays(url)
    rec = d.get("records") or {}
    npr = a["rec.mc.nu.nprim"]; out = []
    for ev, k in zip(rows.ev.to_numpy(), rows.signal_nu_index.to_numpy()):
        ev = int(ev); k = int(k); off = int(ak.sum(npr[ev][:k])); n = int(npr[ev][k]); sl = slice(off, off + n)
        g = lambda c: np.asarray(a[P + c][ev][sl], dtype=float)
        vis = sum(np.asarray(a[b][ev][sl], dtype=float) for b in PLANES if b.endswith("visE")); nh = sum(np.asarray(a[b][ev][sl], dtype=float) for b in PLANES if b.endswith("nhit"))
        r = dict(ev=ev, n_prim=n, p_pdg=np.asarray(a[P + "pdg"][ev][sl], dtype=np.int64), p_genE=g("genE"),
                 p_sx=g("start.x"), p_sy=g("start.y"), p_sz=g("start.z"), p_ex=g("end.x"), p_ey=g("end.y"), p_ez=g("end.z"),
                 p_contained=np.asarray(a[P + "contained"][ev][sl], dtype=np.int8), p_cont_tpc=np.asarray(a[P + "cont_tpc"][ev][sl], dtype=np.int8),
                 p_end_process=np.asarray(a[P + "end_process"][ev][sl], dtype=np.int32), p_px=g("genp.x"), p_py=g("genp.y"), p_pz=g("genp.z"), p_vis=vis, p_nhit=nh,
                 nu_isnc=int(a["rec.mc.nu.isnc"][ev][k]), nu_iscc=int(a["rec.mc.nu.iscc"][ev][k]), nu_resnum=int(a["rec.mc.nu.resnum"][ev][k]),
                 nu_genie_mode=int(a["rec.mc.nu.genie_mode"][ev][k]), nu_genie_inttype=int(a["rec.mc.nu.genie_inttype"][ev][k]))
        gi = int(a["rec.mc.nu.genie_evtrec_idx"][ev][k])
        r.update(genie_final_state_counts(rec, gi) if rec else {})
        out.append(r)
    return out


def manifest():
    from sbnd_single_photon import xrd
    d = {}
    for ln in LOC.read_text().splitlines():
        loc, name, size = ln.split("\t"); d[name] = (xrd.to_xrootd_url(loc[len("enstore:"):] + "/" + name), int(size))
    return d


def work(job):
    idx, name, url, size, rows = job
    out = PIECES / f"{idx}.parquet"
    if out.exists():
        return idx, "cached"
    try:
        r = pd.DataFrame(read_one(url, rows)); r["flatcaf"] = name; r["flatcaf_size"] = size
        r["run"], r["subrun"], r["evt"], r["signal_nu_index"] = rows.run.to_numpy(), rows.subrun.to_numpy(), rows.evt.to_numpy(), rows.signal_nu_index.to_numpy()
        r.to_parquet(str(out) + ".tmp"); os.replace(str(out) + ".tmp", out)
        return idx, "ok"
    except Exception as e:  # noqa: BLE001
        return idx, "ERR " + repr(e)[:200]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("mode", choices=["scan", "merge"]); ap.add_argument("--workers", type=int, default=24); ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args(); PIECES.mkdir(parents=True, exist_ok=True)
    m = pd.read_parquet(SPD / "official_gen2_ncdelta_master" / "signal_events.parquet")
    groups = [(n, g[["ev", "signal_nu_index", "run", "subrun", "evt"]].reset_index(drop=True)) for n, g in m.groupby("flatcaf", sort=True)]
    if a.mode == "scan":
        man = manifest(); jobs = [(i, n, man[n][0], man[n][1], g) for i, (n, g) in enumerate(groups)][: a.limit]
        with mp.get_context("spawn").Pool(min(a.workers, 24)) as p:
            res = list(p.imap_unordered(work, jobs, chunksize=1))
        bad = [r for r in res if r[1].startswith("ERR")]
        print(f"files={len(jobs)} ok={sum(r[1]=='ok' for r in res)} cached={sum(r[1]=='cached' for r in res)} errors={len(bad)}")
        for b in bad[:10]:
            print(b)
        return 1 if bad else 0
    t = pd.concat([pd.read_parquet(p) for p in sorted(PIECES.glob("*.parquet"))], ignore_index=True)
    assert len(t) == len(m) and not t.duplicated(["run", "subrun", "evt"]).any(), (len(t), len(m))
    t.attrs["schema"] = SCHEMA
    t.to_parquet(OUT / "spine_truth.parquet", index=False)
    (OUT / "spine_truth.sha256").write_text(hashlib.sha256((OUT / "spine_truth.parquet").read_bytes()).hexdigest() + "\n")
    print("merged", t.shape, "sha256", (OUT / "spine_truth.sha256").read_text().strip())


if __name__ == "__main__":
    sys.exit(main())
