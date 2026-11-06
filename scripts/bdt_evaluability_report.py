#!/usr/bin/env python
"""Why are candidates not BDT-evaluable? Counts by sample and mutually exclusive reason (valid-event candidates only).

    python scripts/bdt_evaluability_report.py bnb_cv nuecc beam_off beam_on_open [--probe-files 200]
Reasons (in this order): (1) shw_sp_filled == 0; (2) filled but >=1 non-finite BDT input (per model and any);
(3) evaluable. 'n20mev == 0' is cross-tabulated, not a separate reason. A light MC/data probe of T_kine rows tests the
'no accessible shower at the main vertex' hypothesis on a subset of files. NO reconstruction change, NO tuning.
"""
from __future__ import annotations
import argparse, json, os, sys, multiprocessing as mp, warnings
from pathlib import Path
import numpy as np, pandas as pd

REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
from sbnd_single_photon import scanio as X, bdt as B, baseline as BL  # noqa: E402
OUT = REPO / "tables" / "bdt_evaluability"; OUT.mkdir(parents=True, exist_ok=True)
SPD = os.environ["SP_DATA"]


def probe(job):
    from sbnd_single_photon import caf as C
    import awkward as ak
    url, = job
    with C.MergedCaf(url) as f:
        v = f.read_valid()
        typ = f.read_nested("wc.T_kine.kine_particle_type"); sh = f.read_nested("wc.T_kine.kine_particle_is_shower")
        tg = f._wt.arrays(["wc.T_tagger.shw_sp_filled", "wc.T_tagger.shw_sp_n_20mev_showers", "wc.T_kine.kine_main_vertex_id"], library="ak", how=dict)
        fl = lambda a: ak.to_numpy(ak.flatten(a, axis=1))
        n = len(v); ncand = ak.to_numpy(ak.num(tg["wc.T_tagger.shw_sp_filled"], axis=1))
        ok = np.repeat(v, ncand)
        return pd.DataFrame(dict(valid=ok, filled=fl(tg["wc.T_tagger.shw_sp_filled"]), n20=fl(tg["wc.T_tagger.shw_sp_n_20mev_showers"]),
                                 n_rows=fl(ak.num(typ, axis=2)), n_e_rows=fl(ak.sum(typ == 11, axis=2)),
                                 n_shower_rows=fl(ak.sum(sh == 1, axis=2)), n_mu_rows=fl(ak.sum(typ == 13, axis=2)),
                                 main_vtx=fl(tg["wc.T_kine.kine_main_vertex_id"])))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("samples", nargs="+"); ap.add_argument("--probe-files", type=int, default=200)
    a = ap.parse_args()
    from sbnd_single_photon import samples as S
    reg = S.load_samples(); models = B.load_models(); res = {}
    names = {m: [v for v, _ in pairs] for m, pairs in BL.bdt_input_map(models).items()}
    for s in a.samples:
        t = X.load_scan(f"{SPD}/baseline_scan", s)
        vc = t["ev_valid"][t["c_gev"]]
        filled = t["c_shw_sp_filled"] != 0; n20 = t["c_shw_sp_n_20mev_showers"]
        nnf = {m: t[f"c_nnf_{m}"] for m in X.MODELS}
        anynf = np.any([nnf[m] > 0 for m in X.MODELS], axis=0)
        N = int(vc.sum())
        r = dict(valid_candidates=N, filled0=int((vc & ~filled).sum()),
                 filled_nonfinite_any=int((vc & filled & anynf).sum()), evaluable=int((vc & filled & ~anynf).sum()))
        for m in X.MODELS:
            r[f"filled_but_nonfinite_{m}"] = int((vc & filled & (nnf[m] > 0)).sum())
        r["filled0_and_n20_eq0"] = int((vc & ~filled & (n20 == 0)).sum()); r["filled0_and_n20_gt0"] = int((vc & ~filled & (n20 > 0)).sum())
        r["filled_and_n20_eq0"] = int((vc & filled & (n20 == 0)).sum()); r["filled_and_n20_gt0"] = int((vc & filled & (n20 > 0)).sum())
        r["evaluable_and_n20_eq0"] = int((vc & filled & ~anynf & (n20 == 0)).sum())
        r["fractions"] = {k: v / N for k, v in r.items() if k not in ("valid_candidates", "fractions") and isinstance(v, int)}
        nfill = int((filled).sum())
        top = {}
        for m in X.MODELS:
            c = t[f"featnf_filled_{m}"]; order = np.argsort(-c)[:8]
            top[m] = [(names[m][i], int(c[i]), float(c[i] / max(nfill, 1))) for i in order if c[i] > 0]
        r["top_nonfinite_features_among_filled_candidates"] = top
        if "ev_t_code" in t:
            from sbnd_single_photon import truth as T
            ec = t["ev_t_code"][t["c_gev"]]
            r["filled0_fraction_by_event_truth_category"] = {nm: float((~filled & vc & (ec == k)).sum() / max((vc & (ec == k)).sum(), 1))
                                                             for k, nm in enumerate(T.CATEGORIES) if (vc & (ec == k)).sum() > 0}
        urls = S.manifest_urls(reg[s], 0, a.probe_files)
        with mp.get_context("spawn").Pool(8) as p:
            pr = pd.concat(p.map(probe, [(u,) for u in urls]), ignore_index=True)
        pr = pr[pr.valid]
        g = lambda d: dict(n=int(len(d)), frac_with_electron_row=float((d.n_e_rows > 0).mean()) if len(d) else None,
                           frac_with_shower_row=float((d.n_shower_rows > 0).mean()) if len(d) else None,
                           median_rows=float(d.n_rows.median()) if len(d) else None)
        r["probe_T_kine_rows"] = dict(files=a.probe_files, filled0=g(pr[pr.filled == 0]), filled1=g(pr[pr.filled != 0]),
                                      filled0_n20_eq0=g(pr[(pr.filled == 0) & (pr.n20 == 0)]), filled0_n20_gt0=g(pr[(pr.filled == 0) & (pr.n20 > 0)]))
        res[s] = r
        print(s, json.dumps({k: v for k, v in r.items() if k in ("valid_candidates", "filled0", "filled_nonfinite_any", "evaluable", "filled0_and_n20_eq0", "filled0_and_n20_gt0")}), flush=True)
    (OUT / "bdt_evaluability_by_sample.json").write_text(json.dumps(res, indent=1))
    rows = []
    for s, r in res.items():
        rows.append(dict(sample=s, **{k: r[k] for k in ("valid_candidates", "filled0", "filled_nonfinite_any", "evaluable", "filled0_and_n20_eq0",
                                                          "filled0_and_n20_gt0", "filled_and_n20_eq0", "filled_and_n20_gt0")}))
    pd.DataFrame(rows).to_csv(OUT / "bdt_evaluability_by_sample.csv", index=False)


if __name__ == "__main__":
    main()
