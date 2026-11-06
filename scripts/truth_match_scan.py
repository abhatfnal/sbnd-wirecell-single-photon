#!/usr/bin/env python
"""MC-only truth-matching scan (T_kine rows <-> T_overlap <-> T_truth_track/T_truth_nu). EVALUATION ONLY.

    python scripts/truth_match_scan.py bnb_cv --workers 8 [--start 0 --limit N]
Writes $SP_DATA/truth_match/<sample>/<file_index>.npz with
  * row_*  : one row per T_kine particle row (candidate-local), with its dominant matched truth track;
  * cand_* : one row per Wire-Cell candidate, with its dominant truth neutrino and charge purity;
  * tp_*   : truth protons of beam neutrinos (denominator for reco-proton finding efficiency).
Matching: T_overlap rows with in_enu==1, key (event, nu_index, particle_id == kine_particle_id); dominant truth track = max q.
Truth KE = start_E[GeV]*1000 - mass(pdg). Truth is used to EVALUATE definitions, never to choose candidates.
"""
from __future__ import annotations
import argparse, os, sys, time, warnings
import multiprocessing as mp
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")

MASS = {2212: 938.272, 13: 105.658, 211: 139.570, 11: 0.511, 22: 0.0, 2112: 939.565, 321: 493.677, 111: 134.977}
K = "wc.T_kine."


def truth_ke(pdg, e_gev):
    import numpy as np
    m = np.zeros(len(pdg))
    for p, v in MASS.items():
        m[np.abs(pdg) == p] = v
    return e_gev * 1000.0 - m


def work(job):
    import numpy as np, pandas as pd, awkward as ak
    from sbnd_single_photon import caf as C
    idx, url, outdir = job
    out = Path(outdir) / f"{idx}.npz"
    if out.exists():
        return idx, "cached"
    try:
        with C.MergedCaf(url) as f:
            if not f.has_truth_matching:
                return idx, "no truth"
            n = f.num_entries
            nes = lambda c: f.read_nested(K + c)
            typ, ke, inc, pool, pid = (nes(c) for c in ("kine_particle_type", "kine_energy_particle", "kine_energy_included",
                                                       "kine_particle_pool", "kine_particle_id"))
            tag = f._wt.arrays(["wc.T_tagger.nu_index"], library="ak", how=dict)["wc.T_tagger.nu_index"]
            valid = f.read_valid()
            ov = f._wt.arrays(["wc.T_overlap." + c for c in ("particle_id", "nu_index", "in_enu", "trackid", "q", "q_pure")],
                              library="ak", how=dict)
            tt = f._wt.arrays(["wc.T_truth_track." + c for c in ("trackid", "pdg", "start_E", "nu_idx", "mother_pdg", "q_in_blobs")],
                              library="ak", how=dict)
            tn = f._wt.arrays(["wc.T_truth_nu." + c for c in ("pdg", "ccnc", "vtx_x", "vtx_y", "vtx_z", "nu_idx")], library="ak", how=dict)
            fl = lambda a: ak.to_numpy(ak.flatten(a, axis=None))
            def ev_of(a):
                return np.repeat(np.arange(n), ak.to_numpy(ak.num(a, axis=1)))
            # ---- reco rows
            nu_b = ak.broadcast_arrays(tag, typ)[0]
            nrow = ak.to_numpy(ak.sum(ak.num(typ, axis=2), axis=1))
            rows = pd.DataFrame(dict(ev=np.repeat(np.arange(n), nrow), nu=fl(nu_b), pid=fl(pid), typ=fl(typ), ke=fl(ke),
                                     inc=fl(inc) if inc is not None else 0, pool=fl(pool)))
            rows["valid"] = valid[rows.ev.values]
            # ---- overlap -> dominant truth track per (ev, nu, pid)
            o = pd.DataFrame({k.split(".")[-1]: ak.to_numpy(ak.flatten(v)) for k, v in ov.items()})
            o["ev"] = ev_of(ov["wc.T_overlap.q"])
            o = o[(o.in_enu == 1) & (o.nu_index >= 0)]
            g = o.groupby(["ev", "nu_index", "particle_id"])
            tot = g.q.sum().rename("q_row")
            best = o.loc[g.q.idxmax()].set_index(["ev", "nu_index", "particle_id"])[["trackid", "q", "q_pure"]].rename(
                columns={"q": "q_best", "q_pure": "q_best_pure"})
            best = best.join(tot).reset_index().rename(columns={"nu_index": "nu", "particle_id": "pid", "trackid": "mtrack"})
            rows = rows.merge(best, how="left", on=["ev", "nu", "pid"])
            t = pd.DataFrame({k.split(".")[-1]: ak.to_numpy(ak.flatten(v)) for k, v in tt.items()})
            t["ev"] = ev_of(tt["wc.T_truth_track.pdg"])
            t = t.rename(columns={"trackid": "mtrack", "pdg": "mpdg", "start_E": "mE", "nu_idx": "mnu", "mother_pdg": "mmother", "q_in_blobs": "mqblobs"})
            t = t.drop_duplicates(["ev", "mtrack"])
            rows = rows.merge(t, how="left", on=["ev", "mtrack"])
            rows["mke"] = truth_ke(rows.mpdg.fillna(0).values.astype(int), rows.mE.fillna(0).values)
            rows.loc[rows.mpdg.isna(), "mke"] = np.nan
            # ---- candidate table: dominant truth nu by charge, purity
            o2 = o.merge(t[["ev", "mtrack", "mnu"]].rename(columns={"mtrack": "trackid"}), how="left", on=["ev", "trackid"])
            o2["mnu"] = o2.mnu.fillna(-9).astype(int)
            gq = o2.groupby(["ev", "nu_index", "mnu"]).q.sum().reset_index()
            qt = gq.groupby(["ev", "nu_index"]).q.sum().rename("q_cand")
            dom = gq.loc[gq.groupby(["ev", "nu_index"]).q.idxmax()].rename(columns={"q": "q_dom", "mnu": "dom_nu"}).set_index(["ev", "nu_index"])
            qnu = gq[gq.mnu >= 0].groupby(["ev", "nu_index"]).q.sum().rename("q_nu")
            nn = gq[gq.mnu >= 0].groupby(["ev", "nu_index"]).mnu.nunique().rename("n_nu_in_cand")
            cand = dom.join(qt).join(qnu).join(nn).reset_index().rename(columns={"nu_index": "nu"})
            cand[["q_nu", "n_nu_in_cand"]] = cand[["q_nu", "n_nu_in_cand"]].fillna(0)
            tn_df = pd.DataFrame({k.split(".")[-1]: ak.to_numpy(ak.flatten(v)) for k, v in tn.items()})
            tn_df["ev"] = ev_of(tn["wc.T_truth_nu.pdg"])
            tn_df = tn_df.rename(columns={"nu_idx": "dom_nu", "pdg": "nu_pdg", "ccnc": "nu_ccnc", "vtx_x": "nvx", "vtx_y": "nvy", "vtx_z": "nvz"})
            cand = cand.merge(tn_df, how="left", on=["ev", "dom_nu"])
            cand["valid"] = valid[cand.ev.values]
            # ---- truth protons from beam neutrinos
            tp = t[(t.mnu >= 0) & (t.mpdg == 2212)].copy()
            tp["tke"] = truth_ke(tp.mpdg.values.astype(int), tp.mE.values)
            tp = tp[tp.tke > 0].copy()
            hit = rows[(rows.typ == 2212)].groupby(["ev", "mtrack"]).ke.max().rename("reco_ke_best").reset_index()
            tp = tp.merge(hit, how="left", on=["ev", "mtrack"]); tp["valid"] = valid[tp.ev.values]
            z = {}
            for nm, df in (("row", rows), ("cand", cand), ("tp", tp)):
                for c in df.columns:
                    z[f"{nm}_{c}"] = df[c].values
            tmp = out.with_name(out.name + ".tmp.npz")
            np.savez_compressed(tmp, **z)
            os.replace(tmp, out)
        return idx, "ok"
    except Exception as e:
        return idx, "ERR " + repr(e)[:300]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("sample"); ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--start", type=int, default=0); ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--out", default=os.path.join(os.environ.get("SP_DATA", "/tmp"), "truth_match"))
    a = ap.parse_args()
    from sbnd_single_photon import samples as S
    s = S.load_samples()[a.sample]
    urls = S.manifest_urls(s, a.start, None if a.limit is None else a.start + a.limit)
    outdir = Path(a.out) / a.sample; outdir.mkdir(parents=True, exist_ok=True)
    jobs = [(a.start + i, u, str(outdir)) for i, u in enumerate(urls)]
    t0 = time.time(); bad = 0
    with mp.get_context("spawn").Pool(a.workers) as p:
        for k, (i, st) in enumerate(p.imap_unordered(work, jobs, chunksize=2)):
            if st.startswith("ERR") or st == "no truth":
                bad += 1; print(f"file {i}: {st}", flush=True)
            if (k + 1) % 200 == 0:
                print(f"{k+1}/{len(jobs)} {bad} bad {time.time()-t0:.0f}s", flush=True)
    print(f"DONE {len(jobs)} files, {bad} bad, {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
