#!/usr/bin/env python
"""Which frozen-BDT INPUTS changed between the old fg1-era and the Nov16 reconstruction? (descriptive; matched candidates = same file, event, nu_index; no selection is touched)

    source env/setup_eaf.sh && python scripts/wcl1116_input_shift.py --files 600 --workers 24
Reads the union of the input branches of the four frozen BDTs for the first N files of the dedicated NC-Delta sample (signal events with a candidate), in BOTH productions,
and tabulates per input: fraction of matched candidates with identical value, fraction changed, median signed change in units of the old inter-quartile range, family.
"""
from wcl1116_replay_common import *
import argparse, gzip
import multiprocessing as mp

FAMILY = [("upstream numu scores", ("numu_score", "numu_1_score", "numu_2_score", "cosmict_10_score")), ("tagger sub-scores", ("_score",)),
          ("pi0 kinematics (kine_pio_*)", ("kine_pio_",)), ("shower/vertex geometry", ("shw_sp_shw_vtx_dis", "shw_sp_min_dis", "shw_sp_max_shw_dis", "shw_sp_vec_dQ_dx", "reco_nuvtxY", "shw_sp_angle")),
          ("shower multiplicity / quality", ("shw_sp_n_", "shw_sp_br", "shw_sp_lem", "shw_sp_hol", "shw_sp_lol", "shw_sp_pio")), ("shower energy / dQdx", ("shw_sp_E", "shw_sp_energy", "dQ_dx", "dQdx", "length")), ]


def family(n):
    for f, keys in FAMILY:
        if any(k in n for k in keys):
            return f
    return "other"


def work(job):
    import awkward as ak
    from sbnd_single_photon import bdt as B, caf as C
    fi, uo, un, evs = job
    ms = {m: B.TmvaBdt(m, B.DEFAULT_WEIGHT_DIR / f"single_photon_{m}_bdt_final.xml") for m in L.MODELS}
    cols = {}
    for m, x in ms.items():
        for n in x.var_names:
            cols.setdefault(n, B.input_branch(m, n))
    br = sorted(set(cols.values())); nu = "wc.T_tagger.nu_index"; res = {}
    try:
        for tag, url in (("old", uo), ("new", un)):
            with C.tolerant_embedded_basket_read(), C.MergedCaf(url) as f:
                d = f.read(wc=br + [nu]); rows = []
                for ev in evs:
                    k = len(d[nu][ev])
                    if k == 0:
                        continue
                    df = pd.DataFrame({n: np.asarray(ak.to_numpy(d[b][ev]), dtype=np.float64) for n, b in cols.items()})
                    df.insert(0, "nu_index", np.asarray(ak.to_numpy(d[nu][ev])).astype(int)); df.insert(0, "ev", ev); rows.append(df)
                res[tag] = pd.concat(rows, ignore_index=True) if rows else None
    except Exception as e:  # noqa: BLE001
        return fi, None, repr(e)[:200]
    if res.get("old") is None or res.get("new") is None:
        return fi, None, None
    m = res["old"].merge(res["new"], on=["ev", "nu_index"], suffixes=("_old", "_new")); m.insert(0, "file_index", fi)
    return fi, m, None


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--files", type=int, default=600); ap.add_argument("--workers", type=int, default=24); a = ap.parse_args()
    ta = pd.read_parquet(DER / "signal_event_table_new_any.parquet"); ev = ta[ta.A_candidate.astype(bool) & ta.arrived.astype(bool)].dropna(subset=["file_index"])
    rd = lambda p: [l.rstrip("\n").split("\t")[2] for l in gzip.open(p, "rt")][1:]
    uo, un = rd(REPO / "manifests" / "official_gen2_ncdelta_wc.tsv.gz"), rd(REPO / "manifests" / "wcl1116" / "official_gen2_ncdelta.tsv.gz")
    fis = sorted(ev.file_index.unique())[: a.files]
    jobs = [(int(fi), uo[int(fi)], un[int(fi)], sorted(int(e) for e in ev[ev.file_index == fi].ev)) for fi in fis]
    with mp.get_context("spawn").Pool(min(a.workers, 24)) as p:
        out = list(p.imap_unordered(work, jobs, chunksize=1))
    bad = [o for o in out if o[2]]; print("files", len(jobs), "errors", len(bad), bad[:2])
    m = pd.concat([o[1] for o in out if o[1] is not None], ignore_index=True); print("matched candidates", len(m))
    names = sorted({c[:-4] for c in m.columns if c.endswith("_old")}); rows = []
    for n in names:
        o, w = m[n + "_old"].to_numpy(float), m[n + "_new"].to_numpy(float)
        same = (o == w) | (~np.isfinite(o) & ~np.isfinite(w)); ok = np.isfinite(o) & np.isfinite(w)
        iqr = np.nanpercentile(o[np.isfinite(o)], 75) - np.nanpercentile(o[np.isfinite(o)], 25) if np.isfinite(o).any() else np.nan
        d = (w - o)[ok]
        rows.append(dict(input=n, family=family(n), n=len(m), frac_identical=float(same.mean()), frac_changed=float(1 - same.mean()),
                         median_change_over_old_IQR=float(np.median(d) / iqr) if iqr and iqr > 0 and len(d) else np.nan,
                         median_abs_change_over_old_IQR=float(np.median(np.abs(d)) / iqr) if iqr and iqr > 0 and len(d) else np.nan))
    t = pd.DataFrame(rows).sort_values("frac_changed", ascending=False); t.to_csv(OUT / "signal_bdt_input_shift.csv", index=False)
    f = t.groupby("family").agg(n_inputs=("input", "size"), mean_frac_changed=("frac_changed", "mean"), max_frac_changed=("frac_changed", "max")).sort_values("mean_frac_changed", ascending=False)
    f.to_csv(OUT / "signal_bdt_input_shift_by_family.csv"); print(f.round(3).to_string()); print(t.head(25).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
