#!/usr/bin/env python
"""Build the analysis-ready derived tables of ONE sample (resumable, per-file Parquet pieces, then merged). NO tuning, NO FV.

    source env/setup_eaf.sh
    python scripts/build_analysis_table.py bnb_cv --workers 24 [--limit N]   # pieces -> $SP_DATA/analysis_tables/<sample>/pieces
    python scripts/build_analysis_table.py bnb_cv --merge                    # -> candidates.parquet events.parquet files.parquet + metadata.json

Tables (outside Git; see docs/analysis/ANALYSIS_TABLE_VALIDATION.md):
  files      one row per source CAF: file_index, source_file, TotalPOT, TotalGenEvents, n_events, schema_md5
  events     one row per CAF event (also events with 0 candidates / wc.valid==0): provenance, wc_valid, ncand, truth category
  candidates one row per Wire-Cell candidate: provenance (file_index, source_file, run, subrun, evt, nu_index), cut inputs,
             four offline BDT scores, evaluability, extra reco variables, reco proton variables, dominant truth match (MC only)
Cut flags are NOT stored in the pieces: they are derived at merge time from the stored cut inputs with configs/baseline_selection.yaml
(one definition of the chain, scanio.candidate_chain). Truth is stored for EVALUATION only and never used to choose candidates.
"""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, sys, time, warnings
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")          # EAF rule: one BLAS/OMP thread per worker
import multiprocessing as mp
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
warnings.filterwarnings("ignore")
SCHEMA_VERSION = "1.0"

TAG = "wc.T_tagger."
KIN = "wc.T_kine."
TAG_COLS = ["nu_index", "shw_sp_filled", "shw_sp_n_20mev_showers", "shw_sp_n_20br1_showers", "flash_group", "matched_flash_gid",
            "flash_time_us", "flash_pe", "flash_tpc",
            # relevant shower variables (reco; shower energy MeV, distances cm, dQ/dx in WCP units)
            "shw_sp_energy", "shw_sp_shw_vtx_dis", "shw_sp_min_dis", "shw_sp_max_shw_dis", "shw_sp_angle_beam",
            "shw_sp_lowest_dQ_dx", "shw_sp_medium_dQ_dx", "shw_sp_highest_dQ_dx", "shw_sp_vec_dQ_dx_0", "shw_sp_vec_dQ_dx_1",
            "shw_sp_vec_dQ_dx_2"]
KIN_COLS = ["kine_nu_x_corr", "kine_nu_y_corr", "kine_nu_z_corr", "kine_reco_Enu"]
TRUTH_REC = ["rec.mc.nu.pdg", "rec.mc.nu.iscc", "rec.mc.nu.isnc", "rec.mc.nu.nprim", "rec.mc.nu.prim.pdg",
             "rec.mc.nu.position.x", "rec.mc.nu.position.y", "rec.mc.nu.position.z"]
NESTED = ["kine_particle_type", "kine_energy_particle", "kine_energy_included", "kine_particle_pool"]
_G = {}


def _init():
    from sbnd_single_photon import bdt as B, selection as SEL
    _G["models"] = B.load_models(); _G["cfg"] = SEL.load_config()


def candidate_dominant_truth(f, n, valid):
    """MC only. Per candidate: dominant truth neutrino by shared charge (T_overlap in_enu==1 <-> T_truth_track), its purity and identity.
    Returns a DataFrame keyed (ev, nu_index) or None when the file has no truth matching."""
    import numpy as np, pandas as pd, awkward as ak
    ov = f._wt.arrays(["wc.T_overlap." + c for c in ("nu_index", "in_enu", "trackid", "q")], library="ak", how=dict)
    tt = f._wt.arrays(["wc.T_truth_track." + c for c in ("trackid", "nu_idx")], library="ak", how=dict)
    tn = f._wt.arrays(["wc.T_truth_nu." + c for c in ("pdg", "ccnc", "vtx_x", "vtx_y", "vtx_z", "nu_idx")], library="ak", how=dict)
    fl = lambda a: ak.to_numpy(ak.flatten(a, axis=None))
    ev_of = lambda a: np.repeat(np.arange(n), ak.to_numpy(ak.num(a, axis=1)))
    o = pd.DataFrame({k.split(".")[-1]: fl(v) for k, v in ov.items()}); o["ev"] = ev_of(ov["wc.T_overlap.q"])
    o = o[(o.in_enu == 1) & (o.nu_index >= 0)]
    t = pd.DataFrame({k.split(".")[-1]: fl(v) for k, v in tt.items()}); t["ev"] = ev_of(tt["wc.T_truth_track.trackid"])
    t = t.rename(columns={"nu_idx": "mnu"}).drop_duplicates(["ev", "trackid"])
    o2 = o.merge(t[["ev", "trackid", "mnu"]], how="left", on=["ev", "trackid"]); o2["mnu"] = o2.mnu.fillna(-9).astype(int)
    gq = o2.groupby(["ev", "nu_index", "mnu"]).q.sum().reset_index()
    qt = gq.groupby(["ev", "nu_index"]).q.sum().rename("dom_q_cand")
    dom = gq.loc[gq.groupby(["ev", "nu_index"]).q.idxmax()].rename(columns={"q": "dom_q", "mnu": "dom_nu"}).set_index(["ev", "nu_index"])
    qnu = gq[gq.mnu >= 0].groupby(["ev", "nu_index"]).q.sum().rename("dom_q_nu")
    cand = dom.join(qt).join(qnu).reset_index()
    cand["dom_q_nu"] = cand.dom_q_nu.fillna(0.0)
    tdf = pd.DataFrame({k.split(".")[-1]: fl(v) for k, v in tn.items()}); tdf["ev"] = ev_of(tn["wc.T_truth_nu.pdg"])
    tdf = tdf.rename(columns={"nu_idx": "dom_nu", "pdg": "dom_nu_pdg", "ccnc": "dom_nu_ccnc", "vtx_x": "dom_nu_vx", "vtx_y": "dom_nu_vy", "vtx_z": "dom_nu_vz"})
    return cand.merge(tdf, how="left", on=["ev", "dom_nu"])


def work(job):
    res = _work(job)
    if res[1].startswith("ERR"):
        time.sleep(2); res = _work(job)
    return res


def _work(job):
    import numpy as np, pandas as pd, awkward as ak
    from sbnd_single_photon import caf as C, baseline as BL, selection as SEL, truth as T, proton as P, scanio as SIO
    sample, idx, url, is_mc, outdir = job
    out = Path(outdir) / f"{idx}.parquet"
    if out.exists():
        return idx, "cached", 0.0
    t0 = time.time(); models, cfg = _G["models"], _G["cfg"]; req = SEL.required_branches(cfg)
    try:
        with C.MergedCaf(url) as f:
            n = f.num_entries
            extra_wc = [TAG + c for c in TAG_COLS if f.has_wc(TAG + c)] + [KIN + c for c in KIN_COLS if f.has_wc(KIN + c)]
            d = BL.read_baseline_arrays(f, models, extra_wc=extra_wc, cut_branches=req["wc"],
                                        extra_rec=TRUTH_REC if (is_mc and f.has_truth_matching) else [])
            nested = {c: f.read_nested(KIN + c) for c in NESTED if f.has_wc(KIN + c)}
            pot = float(f._f["TotalPOT"].values()[0]) if "TotalPOT" in f._f else float("nan")
            gen = float(f._f["TotalGenEvents"].values()[0]) if "TotalGenEvents" in f._f else float("nan")
            md5 = f.schema_md5(); ids = d["ids"]
            valid = np.asarray(ak.to_numpy(d["wc.valid"]) == 1)
            ncand = ak.to_numpy(ak.num(d[TAG + "nu_index"], axis=1)).astype(np.int16)
            ev = pd.DataFrame(dict(file_index=np.int32(idx), ev=np.arange(n, dtype=np.int32), run=np.asarray(ids["run"]),
                                   subrun=np.asarray(ids["subrun"]), evt=np.asarray(ids["evt"]), wc_valid=valid, ncand=ncand))
            ev_of = np.repeat(np.arange(n, dtype=np.int32), ncand)
            cd = {"file_index": np.full(len(ev_of), idx, np.int32), "ev": ev_of,
                  "run": np.asarray(ids["run"])[ev_of], "subrun": np.asarray(ids["subrun"])[ev_of], "evt": np.asarray(ids["evt"])[ev_of]}
            flat = lambda k: ak.to_numpy(ak.flatten(d[k], axis=1)).astype(np.float64)
            for c in TAG_COLS:
                if TAG + c in d: cd["c_" + c] = flat(TAG + c)
            for c in KIN_COLS:
                if KIN + c in d: cd["c_" + c] = flat(KIN + c)
            for b in req["wc"]:
                cd.setdefault("c_" + b.split(".")[-1], flat(b))
            for m in models:
                cd[f"c_score_{m}"] = flat(f"derived.single_photon_{m}_score")
            cd["c_bdt_n_nonfinite_inputs"] = np.zeros(len(ev_of), np.int16)
            for m, pairs in BL.bdt_input_map(models).items():
                X = np.column_stack([flat(b) for _, b in pairs]) if len(ev_of) else np.zeros((0, len(pairs)))
                cd["c_bdt_n_nonfinite_inputs"] = np.maximum(cd["c_bdt_n_nonfinite_inputs"], (~np.isfinite(X)).sum(axis=1).astype(np.int16))
            if nested:
                pdg, ke = nested["kine_particle_type"], nested["kine_energy_particle"]
                fl = lambda a: ak.to_numpy(ak.flatten(a, axis=1))
                cd["c_np35"] = fl(P.count_reco_protons(pdg, ke)).astype(np.int16)
                isp = pdg == 2212
                cd["c_np_any_ke"] = fl(ak.sum(isp, axis=2)).astype(np.int16)
                pke = ke[isp & (ke > 35.0)]
                cd["c_lead_proton_ke_mev"] = fl(ak.fill_none(ak.max(pke, axis=2), np.nan)).astype(np.float64)
                cd["c_sum_proton_ke_mev"] = fl(ak.sum(pke, axis=2)).astype(np.float64)
                cd["c_nrows"] = fl(ak.num(pdg, axis=2)).astype(np.int16)
            cdf = pd.DataFrame(cd)
            if is_mc and "rec.mc.nu.pdg" in d:
                n_pi0 = ak.sum(C.per_candidate(d["rec.mc.nu.prim.pdg"], d["rec.mc.nu.nprim"]) == 111, axis=-1)
                ts = T.truth_summary(d["rec.mc.nu.pdg"], d["rec.mc.nu.iscc"], d["rec.mc.nu.isnc"], n_pi0,
                                     d["rec.mc.nu.position.x"], d["rec.mc.nu.position.y"], d["rec.mc.nu.position.z"])
                for k, v in ts.items():
                    ev["t_" + k] = v
                if f.has_truth_matching:
                    try:
                        dm = candidate_dominant_truth(f, n, valid).rename(columns={"nu_index": "c_nu_index"})
                        cdf = cdf.merge(dm.rename(columns={"c_nu_index": "c_nu_index_dm"}), how="left",
                                        left_on=["ev", "c_nu_index"], right_on=["ev", "c_nu_index_dm"]).drop(columns=["c_nu_index_dm"])
                        cdf["dom_ok"] = True
                    except Exception as e:                      # keep the file; record that candidate-level matching is missing
                        cdf["dom_ok"] = False
                        print(f"[{sample}] file {idx}: dominant-truth failed: {repr(e)[:120]}", flush=True)
            ev["dom_ok"] = bool(cdf["dom_ok"].all()) if "dom_ok" in cdf else False
        tmp = Path(outdir) / f"{idx}.tmp.parquet"
        ev.to_parquet(tmp.with_name(f"{idx}.events.tmp.parquet"), index=False)
        cdf.to_parquet(tmp, index=False)
        meta = pd.DataFrame(dict(file_index=[idx], source_file=[url.split("/")[-1]], total_pot=[pot], total_gen_events=[gen],
                                 n_events=[n], schema_md5=[str(md5)]))
        meta.to_parquet(Path(outdir) / f"{idx}.files.tmp.parquet", index=False)
        os.replace(Path(outdir) / f"{idx}.events.tmp.parquet", Path(outdir) / f"{idx}.events.parquet")
        os.replace(Path(outdir) / f"{idx}.files.tmp.parquet", Path(outdir) / f"{idx}.files.parquet")
        os.replace(tmp, out)                                     # candidates last: its presence marks the file as complete
        return idx, "ok", time.time() - t0
    except Exception as e:
        return idx, "ERR " + repr(e)[:300], time.time() - t0


def sha(path):
    h = hashlib.sha256(); h.update(Path(path).read_bytes()); return h.hexdigest()


def resolve_sample(name, manifest=None):
    """The registered sample, or (with ``--manifest``) the same sample enabled with an explicit manifest (the registration step of the official
    NC Delta Wire-Cell sample; nothing is written to configs/samples.yaml). ``is_mc`` comes from the registry."""
    import dataclasses
    from sbnd_single_photon import samples as S
    s = S.load_samples()[name]
    if manifest:
        rows = S.read_manifest(manifest)
        s = dataclasses.replace(s, status="available", manifest=str(manifest), n_files_listed=len(rows))
    return s


def merge(sample, root, expected_files, s=None):
    import numpy as np, pandas as pd, pyarrow as pa, pyarrow.parquet as pq
    from sbnd_single_photon import samples as S, selection as SEL, scanio as SIO, bdt as B
    pdir = Path(root) / sample / "pieces"
    idxs = sorted(int(p.name.split(".")[0]) for p in pdir.glob("*.parquet") if p.name.count(".") == 1)
    if expected_files is not None and len(idxs) != expected_files:
        raise SystemExit(f"INCOMPLETE: {len(idxs)} of {expected_files} pieces; refusing to merge")
    cat = lambda suf: pd.concat([pd.read_parquet(pdir / f"{i}{suf}.parquet") for i in idxs], ignore_index=True)
    cand, ev, files = cat(""), cat(".events"), cat(".files")
    cfg = SEL.load_config()
    # global event key, cut flags from stored inputs (one definition of the chain)
    ev = ev.reset_index(drop=True); ev["gev"] = np.arange(len(ev))
    key = ev.set_index(["file_index", "ev"]).gev
    cand["gev"] = key.reindex(pd.MultiIndex.from_arrays([cand.file_index, cand.ev])).values
    tab = {"ev_valid": ev.wc_valid.values, "c_gev": cand.gev.values.astype(np.int64)}
    for c in cand.columns:
        if c.startswith("c_"): tab[c] = cand[c].values
    cand["bdt_evaluable"] = SIO.bdt_evaluable(tab)
    reason = np.full(len(cand), "evaluable", dtype=object)
    reason[cand.c_bdt_n_nonfinite_inputs.values > 0] = "nonfinite_input"
    reason[cand.c_shw_sp_filled.values == 0] = "shw_sp_filled==0"
    cand["bdt_reason"] = pd.Categorical(reason)
    chain = SIO.candidate_chain(tab, cfg)
    for name, flag in chain.items():
        cand["cum_" + name] = flag
    cand["pass_final"] = chain[cfg["cuts"][-1]["name"]]
    cand["policy_first"] = cand.c_nu_index.values == 0
    cand["policy_dedup_keep"] = SIO.dedup_keep(tab)
    cand["reco_proton_cat"] = np.clip(cand.c_np35.values, 0, 2).astype(np.int8)
    cand["source_file"] = pd.Categorical(files.set_index("file_index").source_file.reindex(cand.file_index).values)
    ev["source_file"] = pd.Categorical(files.set_index("file_index").source_file.reindex(ev.file_index).values)
    for name, df in (("candidates", cand), ("events", ev), ("files", files)):
        pq.write_table(pa.Table.from_pandas(df, preserve_index=False), Path(root) / sample / f"{name}.parquet", compression="zstd")
    s = s if s is not None else S.load_samples()[sample]
    git = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "-C", str(REPO), "status", "--porcelain", "--untracked-files=no"], capture_output=True, text=True).stdout.strip())
    wdir = Path(cfg["bdt"]["weight_dir_default"])
    meta = dict(schema_version=SCHEMA_VERSION, sample=sample, created_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                git_commit=git, git_tree_dirty_tracked=dirty,
                manifest=str(s.manifest), manifest_sha256=sha(REPO / s.manifest) if s.manifest else None,
                config_sha256={p: sha(REPO / p) for p in ("configs/baseline_selection.yaml", "configs/samples.yaml")},
                bdt_xml_sha256={x.name: sha(x) for x in sorted(wdir.glob("*.xml"))} if wdir.exists() else {},
                input_files=int(len(files)), events=int(len(ev)), candidates=int(len(cand)),
                total_pot=float(files.total_pot.sum()), total_gen_events=float(files.total_gen_events.sum()),
                tables={"candidates": "one row per Wire-Cell candidate", "events": "one row per CAF event", "files": "one row per source CAF"},
                cut_chain=[c["name"] for c in cfg["cuts"]], candidate_policies=["any", "first", "dedup_any"],
                notes="cut flags derived from stored inputs; truth for evaluation only; no FV; BDT scores offline from original XML (no training)")
    (Path(root) / sample / "metadata.json").write_text(json.dumps(meta, indent=2))
    print(json.dumps({k: meta[k] for k in ("input_files", "events", "candidates", "total_pot")}), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sample"); ap.add_argument("--workers", type=int, default=24)
    ap.add_argument("--limit", type=int, default=None); ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--manifest", default=None, help="explicit merged-CAF manifest (official NC Delta sample registration); overrides the registry entry")
    ap.add_argument("--root", default=os.path.join(os.environ.get("SP_DATA", "/tmp"), "analysis_tables"))
    a = ap.parse_args()
    from sbnd_single_photon import samples as S
    s = resolve_sample(a.sample, a.manifest)
    pdir = Path(a.root) / a.sample / "pieces"
    if a.merge:
        return merge(a.sample, a.root, s.n_files_listed, s)
    pdir.mkdir(parents=True, exist_ok=True)
    urls = S.manifest_urls(s, a.start, None if a.limit is None else a.start + a.limit)
    jobs = [(a.sample, a.start + i, u, bool(s.is_mc), str(pdir)) for i, u in enumerate(urls)]
    t0 = time.time(); nerr = 0
    with mp.get_context("spawn").Pool(min(a.workers, 24), initializer=_init) as p:      # EAF rule: at most 24 workers (32 cores)
        for k, (idx, st, dt) in enumerate(p.imap_unordered(work, jobs, chunksize=2)):
            if st.startswith("ERR"):
                nerr += 1; print(f"[{a.sample}] file {idx}: {st}", flush=True)
            if (k + 1) % 500 == 0:
                print(f"[{a.sample}] {k+1}/{len(jobs)} files, {nerr} errors, {time.time()-t0:.0f}s", flush=True)
    print(f"[{a.sample}] DONE {len(jobs)} files, {nerr} errors, {time.time()-t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
