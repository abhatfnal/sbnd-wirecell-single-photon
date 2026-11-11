#!/usr/bin/env python
"""Generator-level Delta decay record of every signal event of the TPC box (truth only; resumable per file).

    source env/setup_eaf.sh; python scripts/common_observables_genie_scan.py --workers 24
For each signal interaction: the Delta resonance (pdg +-2114 / +-2214; the intermediate particle of the GENIE record), its decay nucleon (status 14, first mother = Delta; the nucleon BEFORE final-state
interactions) and the decay photon (pdg 22, first mother = Delta), all with their four-momenta (px, py, pz, E in GeV).  ``m_decay`` = invariant mass of photon + decay nucleon = the Delta record mass.
Output: $SP_DATA/common_observables/official_ncdelta/genie_delta_record.parquet
"""
from __future__ import annotations
import argparse, os, sys, warnings
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
import multiprocessing as mp
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
SPD = Path(os.environ["SP_DATA"]); OUT = SPD / "common_observables" / "official_ncdelta"; PIECES = OUT / "genie_pieces"
LOC = SPD / "sam" / "official_gen2_ncdelta_flatcaf.locations.txt"


def delta_record(pdg, status, fm, p4) -> dict:
    """Decay structure of ONE GENIE record (lists of equal length; ``p4`` rows = px, py, pz, E in GeV)."""
    pdg = list(pdg); status = list(status); fm = list(fm); p4 = np.asarray(p4, float)
    d = next((i for i in range(len(pdg)) if abs(pdg[i]) in (2114, 2214)), None)
    out = dict(delta_found=d is not None, delta_pdg=0, m_decay=np.nan, nuc_pdg=0, n_decay_photons=0, nuc_found=False)
    if d is None:
        return out
    out["delta_pdg"] = int(pdg[d]); pd_ = p4[d]; out.update({f"delta_{c}": float(v) for c, v in zip(("px", "py", "pz", "E"), pd_)}); out["m_delta_record"] = float(np.sqrt(max(pd_[3] ** 2 - pd_[0] ** 2 - pd_[1] ** 2 - pd_[2] ** 2, 0)))
    nuc = next((i for i in range(len(pdg)) if fm[i] == d and abs(pdg[i]) in (2112, 2212) and status[i] == 14), None)
    pho = [i for i in range(len(pdg)) if fm[i] == d and pdg[i] == 22]
    out["n_decay_photons"] = len(pho)
    if nuc is not None:
        out["nuc_found"] = True; out["nuc_pdg"] = int(pdg[nuc]); out.update({f"nuc_{c}": float(v) for c, v in zip(("px", "py", "pz", "E"), p4[nuc])})
    if pho:
        out.update({f"gam_{c}": float(v) for c, v in zip(("px", "py", "pz", "E"), p4[pho[0]])})
    if nuc is not None and pho:
        s = p4[nuc] + p4[pho[0]]; out["m_decay"] = float(np.sqrt(max(s[3] ** 2 - s[0] ** 2 - s[1] ** 2 - s[2] ** 2, 0)))
    return out


def work(job):
    from sbnd_single_photon import truth_signal as TS
    idx, name, url, rows, pdir = job; out = Path(pdir) / f"{idx}.parquet"
    if out.exists():
        return idx, "cached"
    try:
        rec = TS.read_genie_records(url); d = TS.read_truth_arrays(url, with_record=False); res = []
        for r in rows.itertuples():
            gi = int(d["rec.mc.nu.genie_evtrec_idx"][int(r.ev)][int(r.signal_nu_index)])
            res.append(dict(run=r.run, subrun=r.subrun, evt=r.evt, **delta_record(rec["StdHepPdg"][gi].to_list(), rec["StdHepStatus"][gi].to_list(), rec["StdHepFm"][gi].to_list(), np.asarray(rec["StdHepP4"][gi]))))
        pd.DataFrame(res).to_parquet(str(out) + ".tmp"); os.replace(str(out) + ".tmp", out); return idx, "ok"
    except Exception as e:  # noqa: BLE001
        return idx, "ERR " + repr(e)[:200]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=24); ap.add_argument("--limit", type=int, default=None); a = ap.parse_args(); PIECES.mkdir(parents=True, exist_ok=True)
    from sbnd_single_photon import xrd
    t = pd.read_parquet(SPD / "spine_harmonization" / "official_ncdelta" / "event_flags_and_table.parquet", columns=["run", "subrun", "evt", "tpc_box"])
    m = pd.read_parquet(SPD / "official_gen2_ncdelta_master" / "signal_events.parquet", columns=["run", "subrun", "evt", "flatcaf", "ev", "signal_nu_index"])
    ev = t[t.tpc_box].merge(m, on=["run", "subrun", "evt"])
    loc = {l.split("\t")[1]: xrd.to_xrootd_url(l.split("\t")[0][len("enstore:"):] + "/" + l.split("\t")[1]) for l in LOC.read_text().splitlines()}
    jobs = [(i, n, loc[n], g[["run", "subrun", "evt", "ev", "signal_nu_index"]], str(PIECES)) for i, (n, g) in enumerate(ev.groupby("flatcaf", sort=True))][: a.limit]
    print("events", len(ev), "files", len(jobs), flush=True)
    with mp.get_context("spawn").Pool(min(a.workers, 24)) as p:
        res = list(p.imap_unordered(work, jobs, chunksize=1))
    bad = [r for r in res if r[1].startswith("ERR")]; print("errors", len(bad), bad[:3], flush=True)
    if bad:
        return 1
    d = pd.concat([pd.read_parquet(x) for x in sorted(PIECES.glob("*.parquet"))], ignore_index=True); d.to_parquet(OUT / "genie_delta_record.parquet", index=False); print("merged", d.shape)
    return 0


if __name__ == "__main__":
    sys.exit(main())
