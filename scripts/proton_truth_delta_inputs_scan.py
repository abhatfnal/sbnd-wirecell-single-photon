#!/usr/bin/env python
"""Delta-mass ingredient tables for the final-selected reco 1-gamma-1-proton events of the official Gen2 NC-Delta signal sample (READ-ONLY; nothing is selected or tuned).

    source env/setup_eaf.sh; python scripts/proton_truth_delta_inputs_scan.py --workers 24
Events: TPC-box signal events passing the frozen final selection (``A_final``) whose selected candidate has exactly one reco proton row above 35 MeV (``sel_np35 == 1``): 556 events.
Per event: the ``T_pf`` nodes (start/end point, pdg, KE, kine_index, parent) and ``T_segment`` rows of the SELECTED candidate, the selected-shower energy ``shw_sp_energy`` and
the candidate vertex.  The Delta-mass ingredients (E_gamma, photon direction, proton KE, proton direction) are then derived in ``proton_truth_audit.py``.
Output: $SP_DATA/proton_truth_association/official_ncdelta/raw/delta_{pf,seg,evt}.parquet
"""
from __future__ import annotations
import argparse, gzip, os, sys, warnings
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
import multiprocessing as mp
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
SPD = Path(os.environ["SP_DATA"]); RAW = SPD / "proton_truth_association" / "official_ncdelta" / "raw"
PF = ["nu_index", "node_id", "parent_id", "depth", "pdg", "ke_mev", "kine_index", "is_pseudo", "start_x", "start_y", "start_z", "end_x", "end_y", "end_z", "n_children"]
SEG = ["nu_index", "segment_id", "cluster_id", "flag_shower", "shower_id", "start_vertex_id", "end_vertex_id", "dirsign", "pdg", "ke_mev", "kine_index", "length_cm"]


def work(job):
    from sbnd_single_photon import caf as C
    fi, url, rows = job; o = {k: [] for k in ("pf", "seg", "evt")}
    try:
        with C.tolerant_embedded_basket_read(), C.MergedCaf(url) as f:
            w = f._wt
            pf = {c: w["wc.T_pf." + c].array(library="ak") for c in PF}; seg = {c: w["wc.T_segment." + c].array(library="ak") for c in SEG}
            sp = w["wc.T_tagger.shw_sp_energy"].array(library="ak"); spf = w["wc.T_tagger.shw_sp_filled"].array(library="ak"); spd = w["wc.T_tagger.shw_sp_shw_vtx_dis"].array(library="ak")
            for ev, cand in rows:
                key = dict(file_index=fi, ev=ev)
                o["evt"].append(dict(**key, sel_cand=cand, shw_sp_energy=float(sp[ev][cand]), shw_sp_filled=float(spf[ev][cand]), shw_sp_shw_vtx_dis=float(spd[ev][cand])))
                m = np.asarray(pf["nu_index"][ev]) == cand
                for i in np.where(m)[0]:
                    o["pf"].append(dict(**key, **{c: float(np.asarray(pf[c][ev])[i]) for c in PF}))
                m = np.asarray(seg["nu_index"][ev]) == cand
                for i in np.where(m)[0]:
                    o["seg"].append(dict(**key, **{c: float(np.asarray(seg[c][ev])[i]) for c in SEG}))
    except Exception as e:  # noqa: BLE001
        return fi, None, repr(e)[:200]
    return fi, {k: pd.DataFrame(v) for k, v in o.items()}, None


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=24); a = ap.parse_args(); RAW.mkdir(parents=True, exist_ok=True)
    t = pd.read_parquet(SPD / "spine_harmonization" / "official_ncdelta" / "event_flags_and_table.parquet", columns=["file_index", "ev", "tpc_box", "A_final", "sel_nu_index", "sel_np35"])
    ev = t[t.tpc_box & t.A_final.astype(bool) & (t.sel_np35 == 1)].dropna(subset=["file_index"])
    urls = [l.rstrip("\n").split("\t")[2] for l in gzip.open(REPO / "manifests" / "official_gen2_ncdelta_wc.tsv.gz", "rt")][1:]
    jobs = [(int(fi), urls[int(fi)], [(int(r.ev), int(r.sel_nu_index)) for r in g.itertuples()]) for fi, g in ev.groupby("file_index")]
    print("events", len(ev), "files", len(jobs), flush=True)
    with mp.get_context("spawn").Pool(min(a.workers, 24)) as p:
        res = list(p.imap_unordered(work, jobs, chunksize=1))
    bad = [r for r in res if r[2]]; print("errors", len(bad), bad[:3], flush=True)
    for k in ("pf", "seg", "evt"):
        d = pd.concat([r[1][k] for r in res if r[1] is not None and len(r[1][k])], ignore_index=True); d.to_parquet(RAW / f"delta_{k}.parquet", index=False); print(k, d.shape)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
