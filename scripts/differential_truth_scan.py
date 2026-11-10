#!/usr/bin/env python
"""TRUTH-ONLY extra quantities for the official Gen2 NC-Delta signal denominator (photon direction / conversion point, proton KEs, nu direction).

    source env/setup_eaf.sh
    python scripts/differential_truth_scan.py scan  --workers 24 [--limit N]
    python scripts/differential_truth_scan.py merge           # -> $SP_DATA/differential_efficiency/official_ncdelta/truth_extra.parquet

Reads, per official flatCAF, ONLY recTree truth branches of the signal neutrino chosen by the signal master (``signal_nu_index``) plus the GENIE record
photon energy. Nothing from Wire-Cell; no efficiency; nothing tuned. Resumable (per-file npz). Workers <= 24, BLAS/OMP threads pinned to 1.
Definitions: docs/analysis/PHOTON_CONVERSION_DISTANCE_DEFINITION.md.
"""
from __future__ import annotations
import argparse, os, sys, warnings
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
import multiprocessing as mp
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd

SPD = Path(os.environ.get("SP_DATA", "/tmp")); OUT = SPD / "differential_efficiency" / "official_ncdelta"; PIECES = OUT / "truth_extra_pieces"
LOC = SPD / "sam" / "official_gen2_ncdelta_flatcaf.locations.txt"
P = "rec.mc.nu.prim."
EXTRA = [P + c for c in ("genp.x", "genp.y", "genp.z", "start.x", "start.y", "start.z", "end.x", "end.y", "end.z", "end_process", "contained", "length", "endE")] + \
        ["rec.mc.nu.momentum.x", "rec.mc.nu.momentum.y", "rec.mc.nu.momentum.z", "rec.mc.nu.nprim"]
MP = 0.938272088
G4_CONV, G4_PHOT, G4_COMPT, G4_PHOTONUC, G4_TRANSPORT = 36, 37, 51, 47, 60     # caf::g4_process_ (sbnanaobj SREnums.h)


def read_one(url, rows):
    """rows: DataFrame (ev, signal_nu_index). Returns dict of arrays aligned with ``rows``."""
    import awkward as ak, uproot
    from sbnd_single_photon import truth_signal as TS
    with uproot.open(url) as f:
        t = f["recTree"]
        a = t.arrays(["rec.mc.nu.prim.pdg", "rec.mc.nu.prim.genE"] + EXTRA, library="ak")
    d = TS.read_truth_arrays(url)
    an = TS.record_ancestry_jagged(d["records"], d["rec.mc.nu.genie_evtrec_idx"]) if d.get("records") else None
    npr = a["rec.mc.nu.nprim"]
    out = {k: [] for k in ("ev", "photon_n_primary", "photon_n_gt20", "photon_e_mev", "photon_px", "photon_py", "photon_pz", "photon_sx", "photon_sy", "photon_sz",
                           "photon_ex", "photon_ey", "photon_ez", "photon_end_process", "photon_contained", "photon_track_len", "photon_record_e_mev",
                           "nu_dir_x", "nu_dir_y", "nu_dir_z", "n_p_all", "n_p35", "p_ke_lead", "p_ke_sub", "p_ke_max_below35", "p_ke_sum", "n_p_ge10", "n_p_ge20")}
    for ev, k in zip(rows.ev.to_numpy(), rows.signal_nu_index.to_numpy()):
        ev = int(ev); k = int(k)
        off = int(ak.sum(npr[ev][:k])); n = int(npr[ev][k]); sl = slice(off, off + n)
        g = lambda c: np.asarray(a[P + c][ev][sl], dtype=float)
        pdg = np.asarray(a[P + "pdg"][ev][sl]); e = g("genE") * 1000.0
        ph = np.where(pdg == 22)[0]
        out["ev"].append(ev); out["photon_n_primary"].append(len(ph)); out["photon_n_gt20"].append(int(((pdg == 22) & (e > 20)).sum()))
        if len(ph):
            j = ph[np.argmax(e[ph])]
            out["photon_e_mev"].append(e[j]); out["photon_px"].append(g("genp.x")[j]); out["photon_py"].append(g("genp.y")[j]); out["photon_pz"].append(g("genp.z")[j])
            for c in "xyz":
                out["photon_s" + c].append(g("start." + c)[j]); out["photon_e" + c].append(g("end." + c)[j])
            out["photon_end_process"].append(int(g("end_process")[j])); out["photon_contained"].append(int(g("contained")[j])); out["photon_track_len"].append(g("length")[j])
        else:
            for c in ("photon_e_mev", "photon_px", "photon_py", "photon_pz", "photon_sx", "photon_sy", "photon_sz", "photon_ex", "photon_ey", "photon_ez", "photon_track_len"):
                out[c].append(np.nan)
            out["photon_end_process"].append(-1); out["photon_contained"].append(-1)
        out["photon_record_e_mev"].append(float(an["photon_e_gev"][ev][k]) * 1000.0 if an is not None else np.nan)
        v = np.array([float(a["rec.mc.nu.momentum." + c][ev][k]) for c in "xyz"]); v = v / np.linalg.norm(v) if np.linalg.norm(v) > 0 else v * np.nan
        out["nu_dir_x"].append(v[0]); out["nu_dir_y"].append(v[1]); out["nu_dir_z"].append(v[2])
        ke = np.sort(e[pdg == 2212] - MP * 1000.0)[::-1]
        out["n_p_all"].append(len(ke)); out["n_p35"].append(int((ke > 35).sum())); out["n_p_ge10"].append(int((ke > 10).sum())); out["n_p_ge20"].append(int((ke > 20).sum()))
        out["p_ke_lead"].append(ke[0] if len(ke) else np.nan); out["p_ke_sub"].append(ke[1] if len(ke) > 1 else np.nan)
        out["p_ke_max_below35"].append(ke[ke <= 35][0] if (ke <= 35).any() else np.nan); out["p_ke_sum"].append(ke.sum() if len(ke) else 0.0)
    return {k: np.asarray(v) for k, v in out.items()}


def manifest():
    from sbnd_single_photon import xrd
    return {ln.split("\t")[1]: xrd.to_xrootd_url(ln.split("\t")[0][len("enstore:"):] + "/" + ln.split("\t")[1]) for ln in LOC.read_text().splitlines()}


def work(job):
    idx, name, url, rows = job
    out = PIECES / f"{idx}.parquet"
    if out.exists():
        return idx, "cached"
    try:
        r = pd.DataFrame(read_one(url, rows)); r["flatcaf"] = name
        r["run"], r["subrun"], r["evt"] = rows.run.to_numpy(), rows.subrun.to_numpy(), rows.evt.to_numpy()
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
        man = manifest()
        jobs = [(i, n, man[n], g) for i, (n, g) in enumerate(groups)][: a.limit]
        with mp.get_context("spawn").Pool(min(a.workers, 24)) as p:
            res = list(p.imap_unordered(work, jobs, chunksize=1))
        bad = [r for r in res if r[1].startswith("ERR")]
        print(f"files={len(jobs)} ok={sum(r[1]=='ok' for r in res)} cached={sum(r[1]=='cached' for r in res)} errors={len(bad)}")
        for b in bad[:10]:
            print(b)
        return 1 if bad else 0
    parts = [pd.read_parquet(p) for p in sorted(PIECES.glob("*.parquet"))]
    t = pd.concat(parts, ignore_index=True)
    assert len(t) == len(m) and not t.duplicated(["run", "subrun", "evt"]).any(), (len(t), len(m))
    t.to_parquet(OUT / "truth_extra.parquet", index=False); print("merged", t.shape)


if __name__ == "__main__":
    sys.exit(main())
