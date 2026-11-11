#!/usr/bin/env python
"""Per-candidate reco-object tables for the common NC-Delta observables (READ-ONLY; nothing is selected or tuned).

    source env/setup_eaf.sh
    python scripts/common_observables_scan.py --workers 24

Samples (same reader, same columns):
  signal  official Gen2 NC-Delta, TPC-box events passing the frozen final selection under policy ``any`` (``sel_nu_index``) and/or ``first`` (candidate 0): 1,153 + the extra ``first`` objects.
  bnb     the 649 passing candidates of the BNB CV (``tables/background_mechanisms/candidate_truth_category.csv``; 635 background + 14 natural signal-like).
Per (sample, file_index, ev, cand): tagger fields of the selected single-photon shower (``shw_sp_*``: energy, gap, beam angle, stem dQ/dx vector, dE/dx), flash time, kine scalars (``kine_reco_Enu``,
vertex), the T_kine rows of the candidate and the T_pf nodes of the candidate (start / end points).
Outputs: $SP_DATA/common_observables/official_ncdelta/raw/{tag,kine,pf}.parquet.  Workers <= 24, BLAS/OMP threads pinned to 1.
"""
from __future__ import annotations
import argparse, gzip, os, sys, warnings
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
import multiprocessing as mp
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd

SPD = Path(os.environ["SP_DATA"]); OUT = SPD / "common_observables" / "official_ncdelta"; RAW = OUT / "raw"
TAG = ["shw_sp_filled", "shw_sp_n_20mev_showers", "shw_sp_n_20br1_showers", "shw_sp_energy", "shw_sp_shw_vtx_dis", "shw_sp_max_shw_dis", "shw_sp_angle_beam", "shw_sp_vec_median_dedx", "shw_sp_vec_mean_dedx", "shw_sp_medium_dQ_dx",
       "shw_sp_highest_dQ_dx", "shw_sp_lowest_dQ_dx", "shw_sp_min_dQ_dx_5", "shw_sp_max_dQ_dx_sample", "shw_sp_num_protons", "shw_sp_num_mip_tracks", "flash_time_us", "nu_x", "nu_y", "nu_z"] + [f"shw_sp_vec_dQ_dx_{i}" for i in range(20)]
KINSC = ["kine_reco_Enu", "kine_reco_add_energy", "kine_energy_flagged", "kine_nu_x_corr", "kine_nu_y_corr", "kine_nu_z_corr", "kine_main_vertex_id", "has_vertex"]
KINVEC = ["kine_particle_id", "kine_particle_type", "kine_energy_particle", "kine_particle_is_shower", "kine_particle_pool", "kine_energy_included", "kine_particle_cluster_id", "kine_energy_info"]
PF = ["nu_index", "node_id", "parent_id", "depth", "pdg", "ke_mev", "kine_index", "is_pseudo", "start_x", "start_y", "start_z", "end_x", "end_y", "end_z", "n_children"]


def work(job):
    from sbnd_single_photon import caf as C
    sample, fi, url, items = job            # items: list of (ev, cand)
    o = {k: [] for k in ("tag", "kine", "pf")}
    try:
        with C.tolerant_embedded_basket_read(), C.MergedCaf(url) as f:
            w = f._wt
            tag = {c: w["wc.T_tagger." + c].array(library="ak") for c in TAG if "wc.T_tagger." + c in f.wc_branches}
            ksc = {c: w["wc.T_kine." + c].array(library="ak") for c in KINSC if "wc.T_kine." + c in f.wc_branches}
            kv = {c: f.read_nested("wc.T_kine." + c) for c in KINVEC}; pf = {c: w["wc.T_pf." + c].array(library="ak") for c in PF}
            for ev, cand in items:
                key = dict(sample=sample, file_index=fi, ev=ev, cand=cand)
                o["tag"].append(dict(**key, n_cand=len(next(iter(tag.values()))[ev]), **{c: float(tag[c][ev][cand]) if c in tag else np.nan for c in TAG}, **{c: float(ksc[c][ev][cand]) if c in ksc else np.nan for c in KINSC}))
                n = len(kv["kine_particle_id"][ev][cand])
                for r in range(n):
                    o["kine"].append(dict(**key, row=r, **{c: float(kv[c][ev][cand][r]) for c in KINVEC}))
                m = np.asarray(pf["nu_index"][ev]) == cand
                for i in np.where(m)[0]:
                    o["pf"].append(dict(**key, **{c: float(np.asarray(pf[c][ev])[i]) for c in PF}))
    except Exception as e:  # noqa: BLE001
        return fi, None, repr(e)[:300]
    return fi, {k: pd.DataFrame(v) for k, v in o.items()}, None


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=24); ap.add_argument("--limit", type=int, default=None); a = ap.parse_args(); RAW.mkdir(parents=True, exist_ok=True)
    from sbnd_single_photon import samples as S
    t = pd.read_parquet(SPD / "spine_harmonization" / "official_ncdelta" / "event_flags_and_table.parquet", columns=["file_index", "ev", "tpc_box", "A_final", "A_final_first", "sel_nu_index"])
    t = t[t.tpc_box & (t.A_final.astype(bool) | t.A_final_first.astype(bool))].dropna(subset=["file_index"])
    urls = [l.rstrip("\n").split("\t")[2] for l in gzip.open(REPO / "manifests" / "official_gen2_ncdelta_wc.tsv.gz", "rt")][1:]
    jobs = []
    for fi, g in t.groupby("file_index"):
        items = set()
        for r in g.itertuples():
            if r.A_final:
                items.add((int(r.ev), int(r.sel_nu_index)))
            if r.A_final_first:
                items.add((int(r.ev), 0))
        jobs.append(("signal", int(fi), urls[int(fi)], sorted(items)))
    b = pd.read_csv(REPO / "tables" / "background_mechanisms" / "candidate_truth_category.csv"); burls = S.manifest_urls(S.load_samples()["bnb_cv"])
    for fi, g in b.groupby("file_index"):
        jobs.append(("bnb", int(fi), burls[int(fi)], sorted({(int(r.ev), int(r.nu_index)) for r in g.itertuples()})))
    jobs = jobs[: a.limit]
    print("jobs", len(jobs), "items", sum(len(j[3]) for j in jobs), flush=True)
    with mp.get_context("spawn").Pool(min(a.workers, 24)) as p:
        res = list(p.imap_unordered(work, jobs, chunksize=1))
    bad = [r for r in res if r[2]]; print("errors", len(bad), bad[:3], flush=True)
    for k in ("tag", "kine", "pf"):
        d = pd.concat([r[1][k] for r in res if r[1] is not None and len(r[1][k])], ignore_index=True); d.to_parquet(RAW / f"{k}.parquet", index=False); print(k, d.shape, flush=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
