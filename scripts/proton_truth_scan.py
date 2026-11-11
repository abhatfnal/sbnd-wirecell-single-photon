#!/usr/bin/env python
"""Row-level reco-proton <-> truth association tables of the OFFICIAL Gen2 NC-Delta sample (READ-ONLY; nothing is selected or tuned).

    source env/setup_eaf.sh
    python scripts/proton_truth_scan.py --workers 24 [--limit N]

Events: official signal events of the provisional TPC box that have a merged-CAF file (12,426 of the 12,427; the production-missing event has no file and stays accounted in the analysis).
For each event it stores (long tables keyed by (file_index, ev)):
  rows    every ``T_kine`` row of every candidate (one row = one reco particle; ``cand`` = ``nu_index``, ``row`` = ``kine_index``) joined with its **T_match level-1 side-0** row
          (the production one-to-one reco-particle object) and the top-3 truth partners (production ranking = point IoU), each resolved to the truth prong
          (pdg, interaction ``nu_idx``, primary flag, KE, process, mother pdg).  Also the dominant-charge truth track of the row from ``T_overlap`` (cross-check only).
  tprot   every neutrino-origin true proton (``T_truth_pf`` rows with pdg 2212 and ``T_truth_track`` rows with pdg 2212 and nu_idx >= 0) with the level-1 truth-object partners (reco side) resolved.
  evt     one row per event: signal interaction (vertex match), counts.
Outputs: $SP_DATA/proton_truth_association/official_ncdelta/raw/*.parquet.  Workers <= 24, BLAS/OMP threads pinned to 1.
"""
from __future__ import annotations
import argparse, gzip, os, sys, warnings
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
import multiprocessing as mp
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd

SPD = Path(os.environ["SP_DATA"]); OUT = SPD / "proton_truth_association" / "official_ncdelta"; RAW = OUT / "raw"
KINVEC = ["kine_particle_id", "kine_particle_type", "kine_energy_particle", "kine_particle_is_shower", "kine_particle_pool", "kine_energy_included", "kine_particle_cluster_id", "kine_particle_nseg", "kine_energy_info"]
KINSC = ["kine_main_vertex_id", "kine_nu_x_corr", "kine_nu_y_corr", "kine_nu_z_corr"]
MSC = ["level", "side", "obj", "nu_index", "cluster_id", "kine_index", "truth_nu_idx", "truth_trackid", "nmatch", "mutual", "size_n", "size_q"]
MVEC = ["match_obj", "match_iou_n", "match_iou_q", "match_shared_q"]
OV = ["nu_index", "cluster_id", "segment_id", "particle_id", "kine_index", "in_enu", "in_pf", "trackid", "nu_idx", "n_points", "q"]
TT = ["trackid", "pdg", "nu_idx", "prong_trackid", "ancestor_trackid", "bee_trackid", "mother_pdg", "process", "q_readout", "q_in_blobs", "start_E", "start_x", "start_y", "start_z"]
TPF = ["trackid", "pdg", "KE", "nu_row", "parent_trackid", "process", "start_x", "start_y", "start_z", "start_px", "start_py", "start_pz", "end_x", "end_y", "end_z"]
TNU = ["nu_idx", "vtx_x", "vtx_y", "vtx_z"]
MASS = {2212: 938.272, 2112: 939.565, 22: 0.0, 11: 0.511, 13: 105.658, 211: 139.570, 321: 493.677, 111: 134.977, 14: 0.0, 12: 0.0}


def _a(x):
    return np.asarray(x)


def work(job):
    from sbnd_single_photon import caf as C
    fi, url, rows = job          # rows: list of (ev, vtx_x, vtx_y, vtx_z)
    o = {k: [] for k in ("rows", "tprot", "evt")}
    try:
        with C.tolerant_embedded_basket_read(), C.MergedCaf(url) as f:
            w = f._wt
            kinv = {c: f.read_nested("wc.T_kine." + c) for c in KINVEC}; kins = {c: w["wc.T_kine." + c].array(library="ak") for c in KINSC}
            ms = {c: w["wc.T_match." + c].array(library="ak") for c in MSC}
            mvf = {c: w["wc.T_match." + c].array(library="ak") for c in MVEC}; mvl = {c: w["wc.T_match." + c + "..length"].array(library="ak") for c in MVEC}   # parsed per event below (13 files have one event whose partner lists are inconsistent with their ..length)
            ov = {c: w["wc.T_overlap." + c].array(library="ak") for c in OV}; tt = {c: w["wc.T_truth_track." + c].array(library="ak") for c in TT}
            tpf = {c: w["wc.T_truth_pf." + c].array(library="ak") for c in TPF}; tnu = {c: w["wc.T_truth_nu." + c].array(library="ak") for c in TNU}
            tnu["nu_row_idx"] = None
            for ev, vx, vy, vz in rows:
                ev = int(ev); key = dict(file_index=fi, ev=ev)
                # ---------------- truth tables of this event
                ttd = pd.DataFrame({c: _a(tt[c][ev]) for c in TT}).drop_duplicates("trackid").set_index("trackid", drop=False) if len(tt["trackid"][ev]) else pd.DataFrame(columns=TT).set_index("trackid", drop=False)
                pfd = pd.DataFrame({c: _a(tpf[c][ev]) for c in TPF}).drop_duplicates("trackid").set_index("trackid", drop=False) if len(tpf["trackid"][ev]) else pd.DataFrame(columns=TPF).set_index("trackid", drop=False)
                nu_idx_of_row = _a(tnu["nu_idx"][ev]); nvx = _a(tnu["vtx_x"][ev]); nvy = _a(tnu["vtx_y"][ev]); nvz = _a(tnu["vtx_z"][ev])
                dv = np.sqrt((nvx - vx) ** 2 + (nvy - vy) ** 2 + (nvz - vz) ** 2)
                trow = int(np.argmin(dv)) if len(dv) else -1; vok = bool(len(dv) and dv[trow] < 1e-2)
                sig_nu = int(nu_idx_of_row[trow]) if vok else -99

                def tinfo(tid):
                    """truth attributes of a prong / track id"""
                    d = dict(t_pdg=0, t_nu=-9, t_prim=False, t_prim_pf=False, t_ke=np.nan, t_proc=-1, t_mpdg=0, t_in_tt=False, t_in_pf=False)
                    if tid in ttd.index:
                        r = ttd.loc[tid]; d.update(t_pdg=int(r.pdg), t_nu=int(r.nu_idx), t_prim=bool(r.ancestor_trackid == tid), t_proc=int(r["process"]), t_mpdg=int(r.mother_pdg), t_in_tt=True)
                        m = MASS.get(abs(int(r.pdg)))
                        if m is not None:
                            d["t_ke"] = float(r.start_E) * 1000.0 - m
                    if tid in pfd.index:
                        r = pfd.loc[tid]; d["t_in_pf"] = True; d["t_prim_pf"] = bool(r.parent_trackid == 0); d["t_ke"] = float(r.KE) * 1000.0
                        if not d["t_in_tt"]:
                            d["t_pdg"] = int(r.pdg); d["t_nu"] = int(nu_idx_of_row[int(r.nu_row)]) if 0 <= int(r.nu_row) < len(nu_idx_of_row) else -9; d["t_proc"] = int(r["process"])
                    return d
                # ---------------- T_match level 1
                md = pd.DataFrame({c: _a(ms[c][ev]) for c in MSC})
                tm_ok = all(int(np.sum(_a(mvl[c][ev]))) == len(mvf[c][ev]) and len(mvl[c][ev]) == len(md) for c in MVEC)
                def _split(c):
                    if not tm_ok:
                        return [[] for _ in range(len(md))]
                    ln = _a(mvl[c][ev]).astype(int); fl = _a(mvf[c][ev]); return [list(x) for x in np.split(fl, np.cumsum(ln)[:-1])] if len(ln) else []
                md["mo"] = _split("match_obj"); md["iou_n"] = _split("match_iou_n"); md["iou_q"] = _split("match_iou_q"); md["sh_q"] = _split("match_shared_q")
                l1 = md[md.level == 1]; l1s0 = l1[l1.side == 0].set_index("obj", drop=False); l1s1 = l1[l1.side == 1].set_index("obj", drop=False)
                # ---------------- T_kine rows
                ncand = len(kinv["kine_particle_id"][ev])
                kr = []
                for ci in range(ncand):
                    n = len(kinv["kine_particle_id"][ev][ci])
                    if n:
                        d = pd.DataFrame({c: _a(kinv[c][ev][ci]) for c in KINVEC}); d["cand"] = ci; d["row"] = np.arange(n)
                        d["main_cluster_id"] = int(kins["kine_main_vertex_id"][ev][ci]) // 1000
                        kr.append(d)
                kd = pd.concat(kr, ignore_index=True) if kr else pd.DataFrame(columns=KINVEC + ["cand", "row", "main_cluster_id"])
                l0 = l1s0[(l1s0.nu_index >= 0) & (l1s0.kine_index >= 0)]
                dup_key = int(l0.duplicated(["nu_index", "kine_index"]).sum())
                # T_overlap dominant truth per (cand,row)
                od = pd.DataFrame(dict(cand=_a(ov["nu_index"][ev]), row=_a(ov["kine_index"][ev]), tid=_a(ov["trackid"][ev]), q=_a(ov["q"][ev]).astype(float)))
                od = od[(od.cand >= 0) & (od.row >= 0)]
                if len(od):
                    g = od.groupby(["cand", "row", "tid"]).q.sum().reset_index()
                    tot = g.groupby(["cand", "row"]).q.sum().rename("ov_q_total"); unl = g[g.tid < 0].groupby(["cand", "row"]).q.sum().rename("ov_q_unlabeled")
                    gl = g[g.tid >= 0].sort_values(["cand", "row", "q"], ascending=[True, True, False])
                    top = gl.groupby(["cand", "row"]).nth(0).set_index(["cand", "row"])[["tid", "q"]].rename(columns=dict(tid="ov_dom_tid", q="ov_dom_q"))
                    sec = gl.groupby(["cand", "row"]).nth(1).set_index(["cand", "row"])[["tid", "q"]].rename(columns=dict(tid="ov_dom2_tid", q="ov_dom2_q"))
                    ovs = pd.concat([tot, unl, top, sec], axis=1).reset_index()
                else:
                    ovs = pd.DataFrame(columns=["cand", "row", "ov_q_total", "ov_q_unlabeled", "ov_dom_tid", "ov_dom_q", "ov_dom2_tid", "ov_dom2_q"])
                if len(kd):
                    mm = l0[["nu_index", "kine_index", "obj", "nmatch", "mutual", "size_n", "size_q", "mo", "iou_n", "iou_q", "sh_q"]].rename(columns=dict(nu_index="cand", kine_index="row", obj="m_obj"))
                    kd = kd.merge(mm, on=["cand", "row"], how="left").merge(ovs, on=["cand", "row"], how="left")
                    out_rows = []
                    for r in kd.itertuples(index=False):
                        d = {c: getattr(r, c) for c in KINVEC + ["cand", "row", "main_cluster_id", "m_obj", "nmatch", "mutual", "size_n", "size_q", "ov_q_total", "ov_q_unlabeled", "ov_dom_tid", "ov_dom_q", "ov_dom2_tid", "ov_dom2_q"]}
                        d["has_match_row"] = not (isinstance(r.mo, float) and np.isnan(r.mo)) if not isinstance(r.mo, list) else True
                        mo = r.mo if isinstance(r.mo, list) else []; i_n = r.iou_n if isinstance(r.iou_n, list) else []; i_q = r.iou_q if isinstance(r.iou_q, list) else []; sq = r.sh_q if isinstance(r.sh_q, list) else []
                        for k in range(3):
                            if k < len(mo):
                                po = int(mo[k]); tr = l1s1.loc[po] if po in l1s1.index else None
                                tid = int(tr.truth_trackid) if tr is not None else -1
                                d.update({f"p{k+1}_obj": po, f"p{k+1}_iou_n": float(i_n[k]), f"p{k+1}_iou_q": float(i_q[k]), f"p{k+1}_shared_q": float(sq[k]), f"p{k+1}_tid": tid, f"p{k+1}_truth_nu": int(tr.truth_nu_idx) if tr is not None else -9})
                                if k < 2:
                                    d.update({f"p{k+1}_{kk}": vv for kk, vv in tinfo(tid).items()})
                            else:
                                d.update({f"p{k+1}_obj": -1, f"p{k+1}_iou_n": np.nan, f"p{k+1}_iou_q": np.nan, f"p{k+1}_shared_q": np.nan, f"p{k+1}_tid": -1, f"p{k+1}_truth_nu": -9})
                        out_rows.append(dict(**key, **d))
                    o["rows"].extend(out_rows)
                # ---------------- true protons
                pk = set(int(x) for x in ttd.index[(ttd.pdg == 2212) & (ttd.nu_idx >= 0)]) if len(ttd) else set()
                pk |= set(int(x) for x in pfd.index[pfd.pdg == 2212]) if len(pfd) else set()
                prong_obj = {int(r.truth_trackid): r for r in l1s1.itertuples()}
                for tid in sorted(pk):
                    d = dict(**key, trackid=tid, **tinfo(tid))
                    if tid in ttd.index:
                        r = ttd.loc[tid]; d.update(q_readout=float(r.q_readout), q_in_blobs=float(r.q_in_blobs), tt_start_x=float(r.start_x), tt_start_y=float(r.start_y), tt_start_z=float(r.start_z))
                    if tid in pfd.index:
                        r = pfd.loc[tid]; d.update({"pf_" + c: float(r[c]) for c in ("start_x", "start_y", "start_z", "start_px", "start_py", "start_pz", "end_x", "end_y", "end_z")}); d["pf_nu_row"] = int(r.nu_row)
                    po = prong_obj.get(tid)
                    d["is_l1_obj"] = po is not None
                    if po is not None:
                        d.update(l1_obj=int(po.obj), l1_nmatch=int(po.nmatch), l1_mutual=int(po.mutual))
                        mo = list(po.mo); i_n = list(po.iou_n); i_q = list(po.iou_q)
                        for k in range(3):
                            if k < len(mo):
                                rr = l1s0.loc[int(mo[k])] if int(mo[k]) in l1s0.index else None
                                d.update({f"r{k+1}_obj": int(mo[k]), f"r{k+1}_iou_n": float(i_n[k]), f"r{k+1}_iou_q": float(i_q[k]), f"r{k+1}_cand": int(rr.nu_index) if rr is not None else -9,
                                          f"r{k+1}_row": int(rr.kine_index) if rr is not None else -9, f"r{k+1}_cluster": int(rr.cluster_id) if rr is not None else -9})
                    o["tprot"].append(d)
                o["evt"].append(dict(**key, signal_row=trow, vertex_match_ok=vok, signal_nu_idx=sig_nu, n_cand=ncand, n_truth_nu=len(nu_idx_of_row), n_l1_s0=int(len(l1s0)), n_l1_s1=int(len(l1s1)), dup_l1_key=dup_key, n_kine_rows=int(len(kd)), tmatch_partner_lists_ok=tm_ok))
    except Exception as e:  # noqa: BLE001
        import traceback
        return fi, {k: (pd.DataFrame(v) if v else pd.DataFrame()) for k, v in o.items()}, repr(e)[:200] + traceback.format_exc()[-300:]
    return fi, {k: (pd.DataFrame(v) if v else pd.DataFrame()) for k, v in o.items()}, None


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=24); ap.add_argument("--limit", type=int, default=None); a = ap.parse_args(); RAW.mkdir(parents=True, exist_ok=True)
    t = pd.read_parquet(SPD / "spine_harmonization" / "official_ncdelta" / "event_flags_and_table.parquet", columns=["file_index", "ev", "tpc_box", "vtx_x", "vtx_y", "vtx_z"])
    ev = t[t.tpc_box].dropna(subset=["file_index"])
    urls = [l.rstrip("\n").split("\t")[2] for l in gzip.open(REPO / "manifests" / "official_gen2_ncdelta_wc.tsv.gz", "rt")][1:]
    jobs = [(int(fi), urls[int(fi)], [(int(r.ev), float(r.vtx_x), float(r.vtx_y), float(r.vtx_z)) for r in g.itertuples()]) for fi, g in ev.groupby("file_index")][: a.limit]
    print("events", sum(len(j[2]) for j in jobs), "files", len(jobs), flush=True)
    with mp.get_context("spawn").Pool(min(a.workers, 24)) as p:
        res = list(p.imap_unordered(work, jobs, chunksize=1))
    bad = [r for r in res if r[2]]
    print("read errors", len(bad), [(r[0], r[2][:200]) for r in bad[:3]], flush=True)
    pd.DataFrame([dict(file_index=r[0], error=r[2]) for r in bad]).to_parquet(RAW / "read_errors.parquet", index=False)
    for k in ("rows", "tprot", "evt"):
        d = pd.concat([r[1][k] for r in res if len(r[1][k])], ignore_index=True); d.to_parquet(RAW / f"{k}.parquet", index=False); print(k, d.shape, flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
