#!/usr/bin/env python
"""Per-PROTON GENIE origin (decay proton / FSI-created / ambiguous / not from decay) for every stable proton >= 10 MeV of every signal event of the TPC box (truth only; resumable per file).

    source env/setup_eaf.sh; python scripts/proton_truth_origin_scan.py --workers 24
Generalises ``other_bdt_proton_origin_scan.classify_proton_origin`` (one class per EVENT with exactly one proton) to a class per STABLE PROTON, with the same chain rules.
Output: $SP_DATA/proton_truth_association/official_ncdelta/proton_origin_per_proton.parquet (run, subrun, evt, ke_mev, origin, ...), joined to the G4 primaries by KE in ``proton_tables.py``.
"""
from __future__ import annotations
import argparse, os, sys, warnings
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
import multiprocessing as mp
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
SPD = Path(os.environ["SP_DATA"]); OUT = SPD / "proton_truth_association" / "official_ncdelta"; PIECES = OUT / "origin_pieces"
LOC = SPD / "sam" / "official_gen2_ncdelta_flatcaf.locations.txt"
M_P = 0.938272088


def classify_each_proton(pdg, status, fm, e_gev, ke_min_mev=10.0) -> list[dict]:
    """One dict per stable (status 1) proton above ``ke_min_mev`` of ONE GENIE record (lists of equal length; ``fm`` = first mother, -1 none).  Rules as in Phase 8:
      decay_proton   the decay nucleon N (status-14 nucleon whose first mother is the Delta) is a proton, P descends from N through protons only and is the ONLY stable proton descending from N
      ambiguous      same, but N has several stable proton descendants
      fsi_created    P descends from N but the chain holds a non-proton (charge exchange) or N is a neutron
      not_from_decay P does not descend from N
      unknown        no Delta / no decay nucleon
    """
    n = len(pdg); pdg = list(pdg); status = list(status); fm = list(fm); ke = np.asarray(e_gev, float) * 1000 - M_P * 1000
    prot = [i for i in range(n) if status[i] == 1 and pdg[i] == 2212 and ke[i] > ke_min_mev]
    delta = next((i for i in range(n) if abs(pdg[i]) in (2114, 2214)), None)
    nuc = next((i for i in range(n) if delta is not None and fm[i] == delta and abs(pdg[i]) in (2112, 2212) and status[i] == 14), None)

    def chain(i):
        c = []
        while i is not None and 0 <= i < n and len(c) < 50:
            c.append(i); i = fm[i] if fm[i] >= 0 else None
        return c
    desc = [i for i in range(n) if nuc is not None and status[i] == 1 and pdg[i] == 2212 and nuc in chain(i)]
    out = []
    for p in prot:
        d = dict(ke_mev=float(ke[p]), origin="unknown", decay_nucleon_pdg=int(pdg[nuc]) if nuc is not None else 0, n_decay_nucleon_proton_descendants=len(desc), chain_has_nonproton=False, n_stable_protons_10=len(prot))
        if nuc is not None:
            ch = chain(p)
            if nuc not in ch:
                d["origin"] = "not_from_decay"
            else:
                between = ch[: ch.index(nuc) + 1]; d["chain_has_nonproton"] = any(abs(pdg[i]) != 2212 for i in between)
                d["origin"] = ("decay_proton" if len(desc) == 1 else "ambiguous") if (pdg[nuc] == 2212 and not d["chain_has_nonproton"]) else "fsi_created"
        out.append(d)
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
            for o in classify_each_proton(rec["StdHepPdg"][gi].to_list(), rec["StdHepStatus"][gi].to_list(), rec["StdHepFm"][gi].to_list(), np.asarray(rec["StdHepP4"][gi])[:, 3]):
                res.append(dict(run=r.run, subrun=r.subrun, evt=r.evt, **o))
            res.append(dict(run=r.run, subrun=r.subrun, evt=r.evt, ke_mev=np.nan, origin="__event_marker__", decay_nucleon_pdg=0, n_decay_nucleon_proton_descendants=0, chain_has_nonproton=False, n_stable_protons_10=0))
        pd.DataFrame(res).to_parquet(str(out) + ".tmp"); os.replace(str(out) + ".tmp", out); return idx, "ok"
    except Exception as e:  # noqa: BLE001
        return idx, "ERR " + repr(e)[:200]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=24); ap.add_argument("--limit", type=int, default=None); a = ap.parse_args()
    PIECES.mkdir(parents=True, exist_ok=True)
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
    d = pd.concat([pd.read_parquet(x) for x in sorted(PIECES.glob("*.parquet"))], ignore_index=True)
    d.to_parquet(OUT / "proton_origin_per_proton.parquet", index=False); print("merged", d.shape)
    return 0


if __name__ == "__main__":
    sys.exit(main())
