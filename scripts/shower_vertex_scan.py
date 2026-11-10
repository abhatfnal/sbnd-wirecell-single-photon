#!/usr/bin/env python
"""Per-event reco topology + truth association tables for the signal photon of the OFFICIAL Gen2 NC-Delta sample (READ-ONLY; nothing is selected or tuned).

    source env/setup_eaf.sh
    python scripts/shower_vertex_scan.py --workers 24 [--limit N]

Events: official signal events of the provisional TPC box with ``wc.valid`` and at least one Wire-Cell candidate (11,331 events; ``A_candidate`` of the validated baseline).
For each event (one merged CAF per file) it stores, as long tables keyed by (file_index, ev):
  cand      per candidate: frozen shower-stage tagger fields (shw_sp_*), kine vertex, main vertex id, flags
  kine      per candidate T_kine rows (particle id, pdg, KE, is_shower, pool, included, cluster)
  pf        T_pf particle-flow nodes (node, parent, depth, pdg, KE, kine_index, is_pseudo)
  seg       T_segment rows
  shlist    the per-shower 0/1 flag lists of the tagger (20mev, br1..br4) in loop order
  pho_ov    T_overlap rows whose dominant truth track is the SIGNAL PHOTON (trackid from T_truth_pf; the labeler merges the conversion daughters into the photon)
  ov_all    per (candidate, particle_id): total charge in T_overlap (for charge fractions)
  truth     one row: signal truth neutrino row, photon trackid / q_readout / start / end, other truth neutrinos present
Outputs: $SP_DATA/shower_vertex_audit/official_ncdelta/raw/*.parquet. Workers <= 24, BLAS/OMP threads pinned to 1.
"""
from __future__ import annotations
import argparse, gzip, os, sys, warnings
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
import multiprocessing as mp
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd

SPD = Path(os.environ["SP_DATA"]); OUT = SPD / "shower_vertex_audit" / "official_ncdelta"; RAW = OUT / "raw"
TAG = ["nu_index", "shw_sp_filled", "shw_sp_n_20mev_showers", "shw_sp_n_20br1_showers", "shw_sp_n_br1_showers", "shw_sp_n_br2_showers", "shw_sp_n_br3_showers", "shw_sp_n_br4_showers",
       "shw_sp_n_good_showers", "shw_sp_energy", "shw_sp_shw_vtx_dis", "shw_sp_max_shw_dis", "shw_sp_min_dis", "shw_sp_num_protons", "shw_sp_num_mip_tracks"]
TAGVEC = ["shw_sp_20mev_showers", "shw_sp_br1_showers", "shw_sp_br2_showers", "shw_sp_br3_showers", "shw_sp_br4_showers"]
KIN = ["kine_nu_x_corr", "kine_nu_y_corr", "kine_nu_z_corr", "kine_main_vertex_id", "has_vertex", "kine_reco_Enu"]
KINVEC = ["kine_particle_id", "kine_particle_type", "kine_energy_particle", "kine_particle_is_shower", "kine_particle_pool", "kine_energy_included", "kine_particle_cluster_id", "kine_particle_nseg", "kine_energy_info"]
PF = ["nu_index", "node_id", "parent_id", "depth", "pdg", "ke_mev", "kine_index", "is_pseudo", "start_x", "start_y", "start_z", "end_x", "end_y", "end_z", "n_children"]
SEG = ["nu_index", "segment_id", "cluster_id", "flag_shower", "shower_id", "start_vertex_id", "end_vertex_id", "pdg", "ke_mev", "kine_index", "in_enu", "length_cm"]
OV = ["nu_index", "cluster_id", "segment_id", "particle_id", "kine_index", "in_enu", "in_pf", "trackid", "nu_idx", "n_points", "q", "n_pure", "q_pure"]
TT = ["trackid", "pdg", "nu_idx", "prong_trackid", "ancestor_trackid", "bee_trackid", "q_readout", "q_in_blobs", "start_x", "start_y", "start_z", "end_x", "end_y", "end_z", "start_E", "mother_pdg"]
TPF = ["trackid", "pdg", "E", "KE", "nu_row", "parent_trackid", "start_x", "start_y", "start_z", "end_x", "end_y", "end_z"]
TNU = ["nu_idx", "pdg", "ccnc", "E", "vtx_x", "vtx_y", "vtx_z", "edep"]


def work(job):
    import awkward as ak
    from sbnd_single_photon import caf as C
    fi, url, rows = job          # rows: list of (ev, vtx_x, vtx_y, vtx_z, photon_mev)
    out = {k: [] for k in ("cand", "kine", "pf", "seg", "shlist", "pho_ov", "ov_all", "truth")}
    try:
        with C.tolerant_embedded_basket_read(), C.MergedCaf(url) as f:      # scoped fallback for the known TObjArrayOfTBaskets size mismatch in some T_overlap baskets (Phase 5)
            w = f._wt
            have = lambda n: n in f.wc_branches
            tag = {c: w["wc.T_tagger." + c].array(library="ak") for c in TAG}; kin = {c: w["wc.T_kine." + c].array(library="ak") for c in KIN}
            tagv = {c: f.read_nested("wc.T_tagger." + c) for c in TAGVEC if have("wc.T_tagger." + c + "..length")}
            kinv = {c: f.read_nested("wc.T_kine." + c) for c in KINVEC}
            pf = {c: w["wc.T_pf." + c].array(library="ak") for c in PF}; seg = {c: w["wc.T_segment." + c].array(library="ak") for c in SEG}
            ov = {c: w["wc.T_overlap." + c].array(library="ak") for c in OV}; tt = {c: w["wc.T_truth_track." + c].array(library="ak") for c in TT}
            tpf = {c: w["wc.T_truth_pf." + c].array(library="ak") for c in TPF}; tnu = {c: w["wc.T_truth_nu." + c].array(library="ak") for c in TNU}
            for ev, vx, vy, vz, emev in rows:
                ev = int(ev); key = dict(file_index=fi, ev=ev)
                ncand = len(tag["nu_index"][ev])
                # ---- truth
                dv = np.sqrt((np.asarray(tnu["vtx_x"][ev]) - vx) ** 2 + (np.asarray(tnu["vtx_y"][ev]) - vy) ** 2 + (np.asarray(tnu["vtx_z"][ev]) - vz) ** 2)
                trow = int(np.argmin(dv)) if len(dv) else -1; vok = bool(len(dv) and dv[trow] < 1e-2)
                nuidx = int(tnu["nu_idx"][ev][trow]) if vok else -99
                pk = np.asarray(tpf["pdg"][ev]); pnu = np.asarray(tpf["nu_row"][ev]); pke = np.asarray(tpf["KE"][ev]) * 1000.0
                cand_ph = np.where((pk == 22) & (pnu == trow) & (np.abs(pke - emev) < 0.5))[0] if vok else np.array([], int)
                tid = int(tpf["trackid"][ev][cand_ph[0]]) if len(cand_ph) else -1
                ttid = np.asarray(tt["trackid"][ev]); pr = np.asarray(tt["prong_trackid"][ev]); an = np.asarray(tt["ancestor_trackid"][ev]); bee = np.asarray(tt["bee_trackid"][ev])
                fam = np.where((pr == tid) | (an == tid) | (bee == tid) | (ttid == tid))[0] if tid >= 0 else np.array([], int)
                fam_ids = set(int(x) for x in ttid[fam]) | ({tid} if tid >= 0 else set())
                q_read = float(np.asarray(tt["q_readout"][ev])[fam].sum()) if len(fam) else 0.0; q_blob = float(np.asarray(tt["q_in_blobs"][ev])[fam].sum()) if len(fam) else 0.0
                trow_info = dict(**key, signal_truth_row=trow, vertex_match_ok=vok, signal_nu_idx=nuidx, photon_trackid=tid, photon_found=tid >= 0, n_family_tracks=len(fam_ids), photon_q_readout=q_read, photon_q_in_blobs=q_blob,
                                 n_truth_nu=int(len(tnu["nu_idx"][ev])))
                if len(cand_ph):
                    j = cand_ph[0]
                    for c in ("start_x", "start_y", "start_z", "end_x", "end_y", "end_z"):
                        trow_info["ph_" + c] = float(tpf[c][ev][j])
                    trow_info["photon_ke_mev"] = float(pke[j])
                out["truth"].append(trow_info)
                # ---- overlap rows
                onu = np.asarray(ov["nu_index"][ev]); otid = np.asarray(ov["trackid"][ev]); opid = np.asarray(ov["particle_id"][ev]); oq = np.asarray(ov["q"][ev])
                isph = np.isin(otid, list(fam_ids)) if fam_ids else np.zeros(len(otid), bool)
                for i in np.where(isph)[0]:
                    out["pho_ov"].append(dict(**key, **{c: float(np.asarray(ov[c][ev])[i]) for c in OV}))
                d_all = pd.DataFrame(dict(nu_index=onu, particle_id=opid, q=oq)).groupby(["nu_index", "particle_id"]).q.sum().reset_index() if len(onu) else pd.DataFrame(columns=["nu_index", "particle_id", "q"])
                for r in d_all.itertuples():
                    out["ov_all"].append(dict(**key, nu_index=int(r.nu_index), particle_id=int(r.particle_id), q_total=float(r.q)))
                # ---- candidates
                for ci in range(ncand):
                    row = dict(**key, cand_pos=ci, **{c: float(tag[c][ev][ci]) for c in TAG}, **{c: float(kin[c][ev][ci]) for c in KIN})
                    out["cand"].append(row)
                    for c in TAGVEC:
                        if c in tagv:
                            lst = [int(x) for x in tagv[c][ev][ci]]
                            for si, v in enumerate(lst):
                                out["shlist"].append(dict(**key, cand_pos=ci, flag=c, shower_pos=si, value=v))
                    nrow = len(kinv["kine_particle_id"][ev][ci])
                    for ri in range(nrow):
                        out["kine"].append(dict(**key, cand_pos=ci, row=ri, **{c: float(kinv[c][ev][ci][ri]) for c in KINVEC}))
                for i in range(len(pf["node_id"][ev])):
                    out["pf"].append(dict(**key, **{c: float(pf[c][ev][i]) for c in PF}))
                for i in range(len(seg["segment_id"][ev])):
                    out["seg"].append(dict(**key, **{c: float(seg[c][ev][i]) for c in SEG}))
    except Exception as e:  # noqa: BLE001
        return fi, None, repr(e)[:300]
    return fi, {k: (pd.DataFrame(v) if v else pd.DataFrame()) for k, v in out.items()}, None


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=24); ap.add_argument("--limit", type=int, default=None); a = ap.parse_args(); RAW.mkdir(parents=True, exist_ok=True)
    t = pd.read_parquet(SPD / "spine_harmonization" / "official_ncdelta" / "event_flags_and_table.parquet", columns=["file_index", "ev", "tpc_box", "A_candidate", "vtx_x", "vtx_y", "vtx_z", "photon_energy_mev"])
    ev = t[t.tpc_box & t.A_candidate.astype(bool)].dropna(subset=["file_index"])
    urls = [l.rstrip("\n").split("\t")[2] for l in gzip.open(REPO / "manifests" / "official_gen2_ncdelta_wc.tsv.gz", "rt")][1:]
    jobs = [(int(fi), urls[int(fi)], [(int(r.ev), float(r.vtx_x), float(r.vtx_y), float(r.vtx_z), float(r.photon_energy_mev)) for r in g.itertuples()]) for fi, g in ev.groupby("file_index")][: a.limit]
    print("events", sum(len(j[2]) for j in jobs), "files", len(jobs), flush=True)
    with mp.get_context("spawn").Pool(min(a.workers, 24)) as p:
        res = list(p.imap_unordered(work, jobs, chunksize=1))
    bad = [r for r in res if r[2]]
    print("read errors", len(bad), [(r[0], r[2][:80]) for r in bad[:5]], flush=True)
    pd.DataFrame([dict(file_index=r[0], error=r[2]) for r in bad]).to_parquet(RAW / "read_errors.parquet", index=False)
    for k in ("cand", "kine", "pf", "seg", "shlist", "pho_ov", "ov_all", "truth"):
        d = pd.concat([r[1][k] for r in res if r[1] is not None and len(r[1][k])], ignore_index=True); d.to_parquet(RAW / f"{k}.parquet", index=False); print(k, d.shape, flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
