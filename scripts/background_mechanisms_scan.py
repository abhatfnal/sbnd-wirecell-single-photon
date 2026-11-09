#!/usr/bin/env python
"""Candidate-associated truth scan of the BNB CV merged CAFs (MC evaluation only). Two stages, both resumable (per-file Parquet pieces):

    source env/setup_eaf.sh
    python scripts/background_mechanisms_scan.py light --workers 28     # ALL candidates: production T_match association + matched interaction
    python scripts/background_mechanisms_scan.py deep  --workers 28     # SELECTED (pass_final) candidates only: shower origin, pi0, protons
    python scripts/background_mechanisms_scan.py merge                  # -> $SP_DATA/background_mechanisms/bnb_cv/{light,deep}.parquet

Nothing here selects a candidate: the passing set comes from the derived analysis table (reconstruction only); truth is attached afterwards.
"""
from __future__ import annotations
import argparse, os, sys, time, warnings
import multiprocessing as mp
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
SPD = Path(os.environ.get("SP_DATA", "/tmp")); ROOT = SPD / "background_mechanisms" / "bnb_cv"


def light_work(job):
    import numpy as np, pandas as pd, awkward as ak
    from sbnd_single_photon import caf as C, background_truth as BT, truth_signal as TS
    idx, url, outdir = job
    out = Path(outdir) / f"{idx}.parquet"
    if out.exists():
        return idx, "cached"
    try:
        with C.MergedCaf(url) as f:
            if not f.has_truth_matching:
                return idx, "no truth"
            nu = f._wt["wc.T_tagger.nu_index"].array(library="ak")
            cnt = ak.to_numpy(ak.num(nu, axis=1))
            cand = pd.DataFrame(dict(ev=np.repeat(np.arange(len(cnt)), cnt), nu_index=ak.to_numpy(ak.flatten(nu)).astype(int)))
            R, I = BT.rows_and_items(f)
            a = BT.candidate_association(R, I)
            tn = BT.truth_nu_table(f)
            d = TS.read_truth_arrays(url, with_record=False); rn = BT.recnu_table(d)
        lk = BT.link_truth_nu_to_recnu(tn, rn)
        m = cand.merge(a, on=["ev", "nu_index"], how="left")
        for c, v in (("tm_n", 0), ("tm_n_distinct_nu", 0), ("tm_n_cosmic", 0), ("tm_top_nu", BT.UNMATCHED), ("tm_mutual", 0), ("tm_top_trackid", -1)):
            m[c] = m[c].fillna(v)
        m["tm_top_nu"] = m.tm_top_nu.astype(int)
        t = tn.rename(columns={"nu_idx": "tm_top_nu", "pdg": "mnu_pdg", "ccnc": "mnu_ccnc", "mode": "mnu_mode", "int_type": "mnu_int_type", "E": "mnu_E",
                               "vtx_x": "mnu_x", "vtx_y": "mnu_y", "vtx_z": "mnu_z", "edep": "mnu_edep"})
        m = m.merge(t, on=["ev", "tm_top_nu"], how="left")
        m = m.merge(lk.rename(columns={"nu_idx": "tm_top_nu", "k": "mnu_k", "link_dist_cm": "mnu_link_dist_cm"}), on=["ev", "tm_top_nu"], how="left")
        m = m.merge(rn.rename(columns={"k": "mnu_k", "pdg": "k_pdg", "iscc": "k_iscc", "isnc": "k_isnc", "mode": "k_mode", "E": "k_E", "x": "k_x", "y": "k_y", "z": "k_z",
                                       "n_pi0": "k_n_pi0", "n_p35": "k_n_p35", "n_photon": "k_n_photon", "nprim": "k_nprim"}), on=["ev", "mnu_k"], how="left")
        m.insert(0, "file_index", np.int32(idx))
        tmp = out.with_name(out.name + ".tmp"); m.to_parquet(tmp, index=False); os.replace(tmp, out)
        return idx, "ok"
    except Exception as e:
        return idx, "ERR " + repr(e)[:300]


def recnu_work(job):
    import numpy as np, pandas as pd
    from sbnd_single_photon import background_truth as BT, truth_signal as TS
    idx, url, outdir = job
    out = Path(outdir) / f"{idx}.parquet"
    if out.exists():
        return idx, "cached"
    try:
        d = TS.read_truth_arrays(url, with_record=False)
        rn = BT.recnu_table(d); rn.insert(0, "file_index", np.int32(idx))
        tmp = out.with_name(out.name + ".tmp"); rn.to_parquet(tmp, index=False); os.replace(tmp, out)
        return idx, "ok"
    except Exception as e:
        return idx, "ERR " + repr(e)[:300]


def run_pool(fn, jobs, workers, tag):
    t0 = time.time(); bad = 0
    with mp.get_context("spawn").Pool(workers) as p:
        for k, (i, st) in enumerate(p.imap_unordered(fn, jobs, chunksize=2)):
            if st.startswith("ERR") or st == "no truth":
                bad += 1; print(f"file {i}: {st}", flush=True)
            if (k + 1) % 500 == 0:
                print(f"[{tag}] {k+1}/{len(jobs)} {bad} bad {time.time()-t0:.0f}s", flush=True)
    print(f"[{tag}] DONE {len(jobs)} files, {bad} bad, {time.time()-t0:.0f}s", flush=True)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("stage", choices=["light", "deep", "recnu", "merge"]); ap.add_argument("--workers", type=int, default=28)
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    import pandas as pd
    from sbnd_single_photon import samples as S
    urls = S.manifest_urls(S.load_samples()["bnb_cv"])
    if a.stage == "light":
        od = ROOT / "light_pieces"; od.mkdir(parents=True, exist_ok=True)
        jobs = [(i, u, str(od)) for i, u in enumerate(urls)][: a.limit]
        run_pool(light_work, jobs, a.workers, "light")
    elif a.stage == "recnu":
        od = ROOT / "recnu_pieces"; od.mkdir(parents=True, exist_ok=True)
        run_pool(recnu_work, [(i, u, str(od)) for i, u in enumerate(urls)][: a.limit], a.workers, "recnu")
    elif a.stage == "deep":
        import background_deep as BD
        od = ROOT / "deep_pieces"; od.mkdir(parents=True, exist_ok=True)
        c = pd.read_parquet(SPD / "analysis_tables" / "bnb_cv" / "candidates.parquet", columns=["file_index", "ev", "c_nu_index", "pass_final"])
        sel = c[c.pass_final]
        files = sorted(sel.file_index.unique())
        sel.to_parquet(ROOT / "selected_candidates.parquet", index=False)
        jobs = [(int(i), urls[int(i)], str(od), sel[sel.file_index == i][["ev", "c_nu_index"]].values.tolist()) for i in files][: a.limit]
        run_pool(BD.deep_work, jobs, a.workers, "deep")
    else:
        for stg in ("light", "deep", "recnu"):
            ps = sorted((ROOT / f"{stg}_pieces").glob("*.parquet"))
            if ps:
                df = pd.concat([pd.read_parquet(p) for p in ps], ignore_index=True); df.to_parquet(ROOT / f"{stg}.parquet", index=False)
                print(stg, len(ps), "files", len(df), "rows")


if __name__ == "__main__":
    main()
