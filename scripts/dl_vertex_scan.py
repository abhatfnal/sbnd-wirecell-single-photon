#!/usr/bin/env python
"""Targeted, resumable read of ``wc.T_dlvtx_call`` (the deep-learning-vertex network calls) for the official Gen2 NC-Delta signal events with a candidate (READ-ONLY; nothing is selected or tuned).

    source env/setup_eaf.sh
    python scripts/dl_vertex_scan.py --workers 24 [--limit N]

Why a scan: ``T_dlvtx_call`` / ``T_dlvtx_cloud`` are not in any derived table.  ``T_dlvtx_cloud`` (the network input points) is NOT read: only per-call metadata, the decision chain (``trad_*`` traditional vertex before the
DL, ``rerank_*`` this call's own pick before the dual-chain snap, ``dl_*`` the accepted DL vertex, ``hint_*``, ``final_*`` the candidate's final main vertex), the top-5 ``payload`` (x, y, z, score) and, from the
truth vectors ``truth_all_*``, the signal interaction (selected by the Phase-9 ``signal_nu_idx``) in the cloud's frame (``truth_all_reco_*``: the TrueFwd SCE shift).  All coordinates cm, raw reconstruction frame.
Population: the 11,331 events of the Phase-9 ``event_taxonomy``.  One parquet per file in ``$SP_DATA/vertex_provenance_audit/official_ncdelta/raw/dl_calls/`` (existing files are skipped: resumable), manifest
in ``dl_manifest.parquet`` (file_index, url, n_events, branch list).  Event keys carry run / subrun / event for the cross-check against Phase 9.  Workers <= 24, BLAS/OMP threads pinned to 1.
"""
from __future__ import annotations
import argparse, gzip, os, sys, warnings
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
import multiprocessing as mp
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd

SPD = Path(os.environ["SP_DATA"]); RAW = SPD / "vertex_provenance_audit" / "official_ncdelta" / "raw"; OUT = RAW / "dl_calls"; NAT = RAW / "dl_calls_natural"
P = "wc.T_dlvtx_call."
SCALARS = ["runNo", "subRunNo", "eventNo", "nu_index", "call_index", "pass", "status", "top_k", "rerank", "n_points", "n_vertex_rows", "q_scale", "q_offset", "cloud_no_exclusion", "payload_from_off", "n_off_voxels",
           "trad_valid", "trad_x", "trad_y", "trad_z", "trad_row", "rerank_valid", "rerank_x", "rerank_y", "rerank_z", "rerank_row", "accepted", "dl_x", "dl_y", "dl_z", "dl_row", "dual_transferred", "two_end_veto",
           "hint_valid", "hint_x", "hint_y", "hint_z", "final_valid", "final_x", "final_y", "final_z", "truth_valid", "truth_sce_applied", "truth_x", "truth_y", "truth_z", "truth_reco_x", "truth_reco_y", "truth_reco_z", "truth_n"]
VECTORS = ["payload", "truth_all_nu_idx", "truth_all_edep", "truth_all_x", "truth_all_y", "truth_all_z", "truth_all_reco_x", "truth_all_reco_y", "truth_all_reco_z"]


def work(job):
    from sbnd_single_photon import caf as C
    fi, url, evs, outdir = job                # evs: list of (ev, run, subrun, evt, signal_nu_idx, sx, sy, sz); signal_nu_idx < 0: pick the truth interaction nearest to (sx, sy, sz)
    p = Path(outdir) / f"{fi}.parquet"
    if p.exists():
        return fi, "skipped", None
    rows = []
    try:
        with C.tolerant_embedded_basket_read(), C.MergedCaf(url) as f:
            w = f._wt; sc = {c: w[P + c].array(library="ak") for c in SCALARS}; vc = {c: f.read_nested(P + c) for c in VECTORS}
            for ev, run, sub, evt, snu, sx, sy, sz in evs:
                n = len(sc["nu_index"][ev])
                for k in range(n):
                    r = dict(file_index=fi, ev=int(ev), run_p9=int(run), subrun_p9=int(sub), evt_p9=int(evt), signal_nu_idx=int(snu), **{c: float(sc[c][ev][k]) for c in SCALARS})
                    pay = np.asarray(vc["payload"][ev][k], float); pay = pay.reshape(-1, 4) if pay.size % 4 == 0 and pay.size else np.zeros((0, 4))
                    r["payload_n"] = int(len(pay)); r["payload_flat"] = pay.ravel().tolist()
                    ids = np.asarray(vc["truth_all_nu_idx"][ev][k])
                    if snu >= 0:
                        j = np.where(ids == snu)[0]
                    else:
                        dd = np.sqrt((np.asarray(vc["truth_all_x"][ev][k]) - sx) ** 2 + (np.asarray(vc["truth_all_y"][ev][k]) - sy) ** 2 + (np.asarray(vc["truth_all_z"][ev][k]) - sz) ** 2)
                        j = np.where(dd < 0.05)[0][:1] if len(dd) else np.array([], int)
                    if len(j):
                        j = int(j[0]); r["sig_found"] = True; r["sig_edep"] = float(np.asarray(vc["truth_all_edep"][ev][k])[j])
                        for c in ("x", "y", "z", "reco_x", "reco_y", "reco_z"):
                            r["sig_" + c] = float(np.asarray(vc["truth_all_" + c][ev][k])[j])
                    else:
                        r["sig_found"] = False
                    rows.append(r)
    except Exception as e:  # noqa: BLE001
        return fi, None, repr(e)[:300]
    pd.DataFrame(rows).to_parquet(p, index=False)
    return fi, "done", None


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=24); ap.add_argument("--limit", type=int, default=None); ap.add_argument("--sample", choices=["official", "natural"], default="official"); a = ap.parse_args(); od = OUT if a.sample == "official" else NAT; od.mkdir(parents=True, exist_ok=True)
    if a.sample == "official":
        t = pd.read_parquet(SPD / "shower_vertex_audit" / "official_ncdelta" / "event_taxonomy.parquet", columns=["file_index", "ev", "run", "subrun", "evt", "signal_nu_idx"])
        urls = [l.rstrip("\n").split("\t")[2] for l in gzip.open(REPO / "manifests" / "official_gen2_ncdelta_wc.tsv.gz", "rt")][1:]
        jobs = [(int(fi), urls[int(fi)], [(int(r.ev), int(r.run), int(r.subrun), int(r.evt), int(r.signal_nu_idx), 0.0, 0.0, 0.0) for r in g.itertuples()], str(od)) for fi, g in t.groupby("file_index")][: a.limit]
    else:     # natural NC-Delta CV events of the 117-event rehearsal region (Phase 12 natural candidate table); signal vertex from the natural signal-neutrino table
        from sbnd_single_photon import natural_signal as NS, samples as S
        nc = pd.read_parquet(SPD / "remaining_stage_audit" / "official_ncdelta" / "raw" / "natural_candidates.parquet", columns=["file_index", "ev", "run", "subrun", "evt"]).drop_duplicates()
        sn = pd.read_parquet(SPD / "natural_ncdelta_bnb_cv" / "signal_neutrinos.parquet"); sig = NS.to_signal_truth_table(sn); sig = sig[sig.in_region]
        cols = [c for c in ("file_index", "ev", "x", "y", "z") if c in sig.columns]; t = nc.merge(sn[["file_index", "ev", "x", "y", "z"]].drop_duplicates(["file_index", "ev"]), on=["file_index", "ev"])
        urls = S.manifest_urls(S.load_samples()["bnb_cv"])
        jobs = [(int(fi), urls[int(fi)], [(int(r.ev), int(r.run), int(r.subrun), int(r.evt), -1, float(r.x), float(r.y), float(r.z)) for r in g.itertuples()], str(od)) for fi, g in t.groupby("file_index")][: a.limit]
    pd.DataFrame([dict(file_index=j[0], url=j[1], n_events=len(j[2]), branches=",".join(SCALARS + VECTORS)) for j in jobs]).to_parquet(RAW / ("dl_manifest.parquet" if a.sample == "official" else "dl_manifest_natural.parquet"), index=False)
    print("events", sum(len(j[2]) for j in jobs), "files", len(jobs), flush=True)
    with mp.get_context("spawn").Pool(min(a.workers, 24)) as p:
        res = list(p.imap_unordered(work, jobs, chunksize=1))
    bad = [r for r in res if r[2]]; print("read errors", len(bad), [(r[0], r[2][:80]) for r in bad[:5]], flush=True)
    d = pd.concat([pd.read_parquet(x) for x in sorted(od.glob("*.parquet"))], ignore_index=True); d.to_parquet(RAW / ("dl_calls.parquet" if a.sample == "official" else "dl_calls_natural.parquet"), index=False); print("dl_calls", d.shape, flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
