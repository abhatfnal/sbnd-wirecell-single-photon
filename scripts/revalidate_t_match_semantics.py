#!/usr/bin/env python
"""Re-validate the Phase-4 passing-candidate truth association against the SOURCE-defined T_match semantics (MC evaluation only).

    source env/setup_eaf.sh
    python scripts/revalidate_t_match_semantics.py --workers 20      # reads only the 645 files that hold a selected BNB CV candidate

Per selected candidate: the top partner under the source rule (first stored partner = largest POINT IoU) and under the Phase-4 rule (largest charge IoU).
Per file (all level-3 candidates): the structural invariants stated by the matcher's design document (partner order, <= 3 partners, `mutual`).
Writes tables/background_mechanisms/t_match_source_revalidation*.csv|json. Nothing is selected or tuned.
"""
from __future__ import annotations
import argparse, json, os, sys, warnings
os.environ.setdefault("OMP_NUM_THREADS", "1"); os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1"); os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
import multiprocessing as mp
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd


def invariants(R: pd.DataFrame, I: pd.DataFrame) -> dict:
    """Structural checks on one file's T_match rows/items (pure; tested on synthetic tables)."""
    I = I.copy(); I["pos"] = I.groupby("row").cumcount()
    n_items = I.groupby("row").size().reindex(R.row).fillna(0).astype(int).values
    out = dict(rows=len(R), nmatch_equals_items=bool((n_items == R.nmatch.values).all()), max_nmatch=int(R.nmatch.max()) if len(R) else 0)
    if "match_iou_n" in I.columns and len(I):
        d = I.groupby("row").match_iou_n.diff().dropna()
        out["iou_n_nonincreasing"] = bool((d <= 1e-7).all())
        out["n_iou_n_order_violations"] = int((d > 1e-7).sum())
    # `mutual` == the best partner's best partner is this object
    first = I[I.pos == 0][["row", "match_obj"]].rename(columns={"match_obj": "best"})
    r = R.merge(first, on="row", how="left")
    key = r.set_index(["ev", "level", "side", "obj"]).best
    other = r.assign(side_o=1 - r.side)
    look = key.reindex(pd.MultiIndex.from_arrays([other.ev, other.level, other.side_o, other.best.fillna(-1).astype(int)])).values
    has = r.best.notna().values
    pred = has & (look == r.obj.values)
    out["mutual_flag_agrees_with_definition"] = float((pred == (r.mutual.values == 1))[has].mean()) if has.any() else float("nan")
    return out


def _work(job):
    idx, url, evs = job
    from sbnd_single_photon import caf as C, background_truth as BT
    try:
        with C.MergedCaf(url) as f:
            R, I = BT.rows_and_items(f)
        a_src = BT.candidate_association(R, I, rule="source"); a_q = BT.candidate_association(R, I, rule="iou_q")
        m = a_src.merge(a_q[["ev", "nu_index", "tm_top_nu", "tm_top_iou"]], on=["ev", "nu_index"], suffixes=("", "_q"))
        m = m[m.ev.isin(evs)].assign(file_index=idx)
        R3 = R[(R.level == 3)]
        # truth interaction claimed as top partner by several candidates of one event
        c3 = a_src[a_src.tm_top_nu >= 0].groupby(["ev", "tm_top_nu"]).size()
        inv = invariants(R3, I[I.row.isin(R3.row)])
        inv.update(file_index=idx, n_cands_l3=int(len(a_src)), n_truth_nu_claimed_by_several=int((c3 > 1).sum()), n_truth_nu_claimed=int(len(c3)),
                   n_cands_multi_nu=int((a_src.tm_n_distinct_nu >= 2).sum()))
        return idx, m, inv, None
    except Exception as e:  # noqa
        return idx, None, None, repr(e)[:200]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=20)
    ap.add_argument("--sample", default="bnb_cv"); a = ap.parse_args()
    from sbnd_single_photon import samples as S
    spd = Path(os.environ["SP_DATA"]); sel = pd.read_parquet(spd / "background_mechanisms" / a.sample / "selected_candidates.parquet")
    urls = {i: r["url"] for i, r in enumerate(S.read_manifest(S.load_samples()[a.sample].manifest))}
    jobs = [(int(i), urls[int(i)], set(g.ev.astype(int))) for i, g in sel.groupby("file_index")]
    res, invs, errs = [], [], []
    with mp.get_context("spawn").Pool(min(a.workers, 24)) as p:
        for k, (idx, m, inv, err) in enumerate(p.imap_unordered(_work, jobs, chunksize=1)):
            if err: errs.append((idx, err)); continue
            res.append(m); invs.append(inv)
            if (k + 1) % 100 == 0: print(f"{k+1}/{len(jobs)}", flush=True)
    out = REPO / "tables" / "background_mechanisms"
    M = pd.concat(res, ignore_index=True).merge(sel.rename(columns={"c_nu_index": "nu_index"})[["file_index", "ev", "nu_index"]], on=["file_index", "ev", "nu_index"])
    V = pd.DataFrame(invs)
    M.to_csv(out / "t_match_source_revalidation_selected.csv", index=False)
    js = dict(n_selected_found=int(len(M)), n_selected_expected=int(len(sel)), read_errors=errs, files=int(len(V)),
              top_nu_differs_source_vs_iouq=int((M.tm_top_nu != M.tm_top_nu_q).sum()),
              top_iou_n_quantiles={str(q): float(M.tm_top_iou_n.quantile(q)) for q in (0, .05, .25, .5, .75, .95, 1)},
              mutual_candidates=int((M.tm_mutual == 1).sum()),
              invariants=dict(files_nmatch_equals_items=int(V.nmatch_equals_items.sum()), max_nmatch=int(V.max_nmatch.max()),
                              files_iou_n_nonincreasing=int(V.iou_n_nonincreasing.sum()), iou_n_order_violations=int(V.n_iou_n_order_violations.sum()),
                              mutual_flag_agreement_min=float(V.mutual_flag_agrees_with_definition.min()),
                              candidates_level3=int(V.n_cands_l3.sum()), candidates_with_ge2_distinct_truth_nu=int(V.n_cands_multi_nu.sum()),
                              truth_nu_claimed_as_top_by_several_candidates=int(V.n_truth_nu_claimed_by_several.sum()), truth_nu_claimed=int(V.n_truth_nu_claimed.sum())))
    (out / "t_match_source_revalidation.json").write_text(json.dumps(js, indent=1))
    print(json.dumps(js, indent=1))


if __name__ == "__main__":
    main()
