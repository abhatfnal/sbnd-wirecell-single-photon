#!/usr/bin/env python
"""Quantify the exact (0,0,0) reconstructed-vertex value (kine_nu_{x,y,z}_corr) per sample. No FV is applied.

    python scripts/vertex_sentinel_report.py  -> tables/vertex_sentinel/vertex_sentinel_by_sample.json
Also probes wc.T_tagger.has_vertex / T_kine on the first files of each sample to relate (0,0,0) to has_vertex.
"""
from __future__ import annotations
import json, multiprocessing as mp, os, sys, warnings
from pathlib import Path
import numpy as np
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
from sbnd_single_photon import scanio as X, selection as SEL  # noqa: E402
OUT = REPO / "tables" / "vertex_sentinel"; OUT.mkdir(parents=True, exist_ok=True)
SPD = os.environ["SP_DATA"]


def probe(url):
    import awkward as ak
    from sbnd_single_photon import caf as C
    with C.MergedCaf(url) as f:
        if not f.has_wc("wc.T_tagger.has_vertex"):
            return None
        v = f.read_valid()
        d = f._wt.arrays(["wc.T_tagger.has_vertex", "wc.T_kine.kine_nu_x_corr", "wc.T_kine.kine_nu_y_corr", "wc.T_kine.kine_nu_z_corr"], library="ak", how=dict)
        n = ak.to_numpy(ak.num(d["wc.T_tagger.has_vertex"], axis=1)); ok = np.repeat(v, n)
        fl = lambda k: ak.to_numpy(ak.flatten(d[k], axis=1))
        zero = (fl("wc.T_kine.kine_nu_x_corr") == 0) & (fl("wc.T_kine.kine_nu_y_corr") == 0) & (fl("wc.T_kine.kine_nu_z_corr") == 0)
        return fl("wc.T_tagger.has_vertex")[ok], zero[ok]


def main():
    from sbnd_single_photon import samples as S
    cfg = SEL.load_config(); reg = S.load_samples(); res = {}
    for s in ("bnb_cv", "nuecc", "beam_off", "beam_on_open"):
        t = X.load_scan(f"{SPD}/baseline_scan", s)
        vc = t["ev_valid"][t["c_gev"]]
        zero = (t["c_kine_nu_x_corr"] == 0) & (t["c_kine_nu_y_corr"] == 0) & (t["c_kine_nu_z_corr"] == 0)
        nan = ~np.isfinite(t["c_kine_nu_x_corr"] + t["c_kine_nu_y_corr"] + t["c_kine_nu_z_corr"])
        ev = X.bdt_evaluable(t); fin = X.candidate_chain(t, cfg)[cfg["cuts"][-1]["name"]]
        n = int(vc.sum()); z = vc & zero
        r = dict(valid_candidates=n, exactly_000=int(z.sum()), frac_000=float(z.sum() / n), nonfinite_vertex=int((vc & nan).sum()),
                 any_one_coordinate_zero_but_not_all=int((vc & ~zero & ((t["c_kine_nu_x_corr"] == 0) | (t["c_kine_nu_y_corr"] == 0) | (t["c_kine_nu_z_corr"] == 0))).sum()),
                 bdt_evaluable_among_000=int((z & ev).sum()), frac_evaluable_among_000=float((z & ev).sum() / max(z.sum(), 1)),
                 frac_evaluable_among_nonzero=float((vc & ~zero & ev).sum() / max((vc & ~zero).sum(), 1)),
                 filled0_among_000=float((z & (t["c_shw_sp_filled"] == 0)).sum() / max(z.sum(), 1)),
                 final_selected=int(fin.sum()), final_selected_000=int((fin & zero).sum()),
                 n20_gt0_among_000=int((z & (t["c_shw_sp_n_20mev_showers"] > 0)).sum()))
        urls = S.manifest_urls(reg[s], 0, 100)
        with mp.get_context("spawn").Pool(8) as p:
            pr = [x for x in p.map(probe, urls) if x is not None]
        if pr:
            hv = np.concatenate([a for a, _ in pr]); zz = np.concatenate([b for _, b in pr])
            r["probe_has_vertex_first100files"] = {str(int(k)): dict(n=int((hv == k).sum()), frac_000=float(zz[hv == k].mean())) for k in np.unique(hv)}
        res[s] = r; print(s, json.dumps(r), flush=True)
    (OUT / "vertex_sentinel_by_sample.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
