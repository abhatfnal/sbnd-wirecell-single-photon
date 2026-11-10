#!/usr/bin/env python
"""Proton origin of truth-1p signal events from the GENIE record (truth only; resumable per file).

    source env/setup_eaf.sh; python scripts/other_bdt_proton_origin_scan.py --workers 6
Events: truth-1p (35 MeV) official signal events of the filter box whose frozen selection reaches the ``other`` stage. For each, the stable (status 1) protons above 35 MeV and the GENIE
mother chains are examined (see ``classify_proton_origin``). Output: $SP_DATA/other_bdt_audit/official_ncdelta/proton_origin.parquet.
"""
from __future__ import annotations
import argparse, os, sys, warnings
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
import multiprocessing as mp
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
SPD = Path(os.environ["SP_DATA"]); OUT = SPD / "other_bdt_audit" / "official_ncdelta"; PIECES = OUT / "proton_origin_pieces"
LOC = SPD / "sam" / "official_gen2_ncdelta_flatcaf.locations.txt"
M_P = 0.938272088


def classify_proton_origin(pdg, status, fm, e_gev, ke_threshold_mev=35.0) -> dict:
    """Classify the stable proton(s) of ONE GENIE record by its mother chain (all lists of equal length; ``fm`` = first mother index, -1 none).

    decay nucleon N = the status-14 (in-nucleus) nucleon whose first mother is the Delta (2114/2214, any status). For each status-1 proton above threshold P the chain
    P -> fm -> ... is followed to the Delta.
      * ``decay_proton``    N is a proton, P descends from N through protons only, and P is the ONLY status-1 proton descending from N: the Delta-decay proton (it may have rescattered).
      * ``ambiguous``       N is a proton, P descends from N through protons only, but N has several stable proton descendants (decay proton or knocked-out sibling cannot be told apart).
      * ``fsi_created``     P descends from N but the chain contains a non-proton (charge exchange: decay NEUTRON -> proton) or N is a neutron.
      * ``not_from_decay``  P does not descend from the decay nucleon.
      * ``unknown``         no Delta / decay nucleon / broken chain.
    Only events with exactly one stable proton above threshold get a class; others get ``n_protons_ke!=1``."""
    n = len(pdg); pdg = list(pdg); status = list(status); fm = list(fm); e = np.asarray(e_gev, float)
    ke = e * 1000 - M_P * 1000
    prot = [i for i in range(n) if status[i] == 1 and pdg[i] == 2212 and ke[i] > ke_threshold_mev]
    out = dict(n_stable_protons_ke=len(prot), origin="n_protons_ke!=1", decay_nucleon_pdg=0, n_decay_nucleon_proton_descendants=-1, chain_has_nonproton=False, p_ke_mev=float(ke[prot[0]]) if len(prot) else np.nan)
    if len(prot) != 1:
        return out
    delta = next((i for i in range(n) if abs(pdg[i]) in (2114, 2214)), None)
    if delta is None:
        out["origin"] = "unknown"; return out
    nuc = next((i for i in range(n) if fm[i] == delta and abs(pdg[i]) in (2112, 2212) and status[i] == 14), None)
    if nuc is None:
        out["origin"] = "unknown"; return out
    out["decay_nucleon_pdg"] = int(pdg[nuc])

    def chain(i):
        c = []
        while i is not None and 0 <= i < n and len(c) < 50:
            c.append(i); i = fm[i] if fm[i] >= 0 else None
        return c
    desc_protons = [i for i in range(n) if status[i] == 1 and pdg[i] == 2212 and nuc in chain(i)]
    out["n_decay_nucleon_proton_descendants"] = len(desc_protons)
    p = prot[0]; ch = chain(p)
    if nuc not in ch:
        out["origin"] = "not_from_decay"; return out
    between = ch[: ch.index(nuc) + 1]
    out["chain_has_nonproton"] = any(abs(pdg[i]) != 2212 for i in between)
    if pdg[nuc] == 2212 and not out["chain_has_nonproton"]:
        out["origin"] = "decay_proton" if len(desc_protons) == 1 else "ambiguous"
    else:
        out["origin"] = "fsi_created"
    return out


def work(job):
    import awkward as ak
    from sbnd_single_photon import truth_signal as TS, xrd
    idx, name, url, rows = job; out = PIECES / f"{idx}.parquet"
    if out.exists():
        return idx, "cached"
    try:
        rec = TS.read_genie_records(url); d = TS.read_truth_arrays(url, with_record=False); res = []
        for r in rows.itertuples():
            gi = int(d["rec.mc.nu.genie_evtrec_idx"][int(r.ev)][int(r.signal_nu_index)])
            o = classify_proton_origin(rec["StdHepPdg"][gi].to_list(), rec["StdHepStatus"][gi].to_list(), rec["StdHepFm"][gi].to_list(), np.asarray(rec["StdHepP4"][gi])[:, 3])
            res.append(dict(run=r.run, subrun=r.subrun, evt=r.evt, **o))
        pd.DataFrame(res).to_parquet(str(out) + ".tmp"); os.replace(str(out) + ".tmp", out); return idx, "ok"
    except Exception as e:  # noqa: BLE001
        return idx, "ERR " + repr(e)[:200]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=6); a = ap.parse_args(); PIECES.mkdir(parents=True, exist_ok=True)
    from sbnd_single_photon import xrd
    t = pd.read_parquet(SPD / "spine_harmonization" / "official_ncdelta" / "event_flags_and_table.parquet", columns=["run", "subrun", "evt", "truth35", "A_numu"])
    m = pd.read_parquet(SPD / "official_gen2_ncdelta_master" / "signal_events.parquet", columns=["run", "subrun", "evt", "flatcaf", "ev", "signal_nu_index"])
    ev = t[(t.truth35 == 1) & t.A_numu.astype(bool)].merge(m, on=["run", "subrun", "evt"])
    loc = {l.split("\t")[1]: xrd.to_xrootd_url(l.split("\t")[0][len("enstore:"):] + "/" + l.split("\t")[1]) for l in LOC.read_text().splitlines()}
    jobs = [(i, n, loc[n], g[["run", "subrun", "evt", "ev", "signal_nu_index"]]) for i, (n, g) in enumerate(ev.groupby("flatcaf", sort=True))]
    print("events", len(ev), "files", len(jobs))
    with mp.get_context("spawn").Pool(min(a.workers, 24)) as p:
        res = list(p.imap_unordered(work, jobs, chunksize=1))
    bad = [r for r in res if r[1].startswith("ERR")]; print("errors", len(bad), bad[:3])
    if bad:
        return 1
    pd.concat([pd.read_parquet(x) for x in sorted(PIECES.glob("*.parquet"))], ignore_index=True).to_parquet(OUT / "proton_origin.parquet", index=False)
    print("merged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
