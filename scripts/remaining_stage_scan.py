#!/usr/bin/env python
"""Candidate-level inputs of the frozen ``numu`` / ``ncpi0`` / ``nue`` BDTs for the events that reach the shower stage (READ-ONLY; no training, no tuning).

    source env/setup_eaf.sh
    python scripts/remaining_stage_scan.py official --workers 24      # official Gen2 NC-Delta events (TPC box) with > 20 MeV shower: 8,080 events, ALL their candidates
    python scripts/remaining_stage_scan.py natural  --workers 12      # natural NC-Delta events of the BNB CV (117-event rehearsal region)

For each selected event ALL Wire-Cell candidates are stored (event-level ``any`` logic must not hide multi-candidate behaviour): the input branches of the three frozen models (exactly the
``bdt.input_branch`` mapping, union over the models), ``wc.T_tagger.shw_sp_filled`` / ``n_20mev`` / ``n_20br1`` / ``nu_index`` and the frozen scorer's scores of the three models.
Output: $SP_DATA/remaining_stage_audit/official_ncdelta/raw/{official,natural}_candidates.parquet. Workers <= 24, BLAS/OMP threads pinned to 1.
"""
from __future__ import annotations
import argparse, gzip, os, sys, warnings
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
import multiprocessing as mp
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd

SPD = Path(os.environ["SP_DATA"]); OUT = SPD / "remaining_stage_audit" / "official_ncdelta" / "raw"; OUT.mkdir(parents=True, exist_ok=True)
MODELS = ("numu", "ncpi0", "nue")
TAG = "wc.T_tagger."


def work(job):
    import awkward as ak
    from sbnd_single_photon import bdt as B, caf as C
    fi, url, evs = job
    ms = {m: B.TmvaBdt(m, B.DEFAULT_WEIGHT_DIR / f"single_photon_{m}_bdt_final.xml") for m in MODELS}
    cols = {}
    for m, x in ms.items():
        for n in x.var_names:
            cols.setdefault(n, B.input_branch(m, n))
    branches = sorted(set(cols.values())); extra = [TAG + c for c in ("shw_sp_filled", "nu_index", "shw_sp_n_20mev_showers", "shw_sp_n_20br1_showers", "shw_sp_n_br1_showers", "shw_sp_energy")]
    rows = []
    try:
        with C.tolerant_embedded_basket_read(), C.MergedCaf(url) as f:
            d = f.read(wc=branches + [e for e in extra if e not in branches]); ids = d["ids"]
            for ev in evs:
                ncand = len(d[TAG + "nu_index"][ev])
                if ncand == 0:
                    continue
                vals = {b: np.asarray(ak.to_numpy(d[b][ev]), dtype=np.float64) for b in branches}
                df = pd.DataFrame({"in_" + n: vals[b] for n, b in cols.items()})
                df.insert(0, "c_nu_index", np.asarray(ak.to_numpy(d[TAG + "nu_index"][ev])).astype(np.int64))
                for e in extra[:1] + extra[2:]:
                    df[e.replace(TAG, "")] = np.asarray(ak.to_numpy(d[e][ev]), dtype=np.float64)
                for m, x in ms.items():
                    df[f"{m}_score"] = x.decision(np.column_stack([vals[B.input_branch(m, n)] for n in x.var_names]))
                df.insert(0, "file_index", fi); df.insert(1, "ev", ev)
                df.insert(2, "run", int(ids["run"][ev])); df.insert(3, "subrun", int(ids["subrun"][ev])); df.insert(4, "evt", int(ids["evt"][ev]))
                rows.append(df)
    except Exception as e:  # noqa: BLE001
        return fi, None, repr(e)[:200]
    return fi, (pd.concat(rows, ignore_index=True) if rows else None), None


def run(jobs, workers, name):
    with mp.get_context("spawn").Pool(min(workers, 24)) as p:
        res = list(p.imap_unordered(work, jobs, chunksize=1))
    bad = [r for r in res if r[2]]
    if bad:
        print("ERRORS", bad[:5]); return 1
    t = pd.concat([r[1] for r in res if r[1] is not None], ignore_index=True).sort_values(["file_index", "ev", "c_nu_index"]).reset_index(drop=True)
    t.to_parquet(OUT / f"{name}_candidates.parquet", index=False); print(name, t.shape, "events", t.groupby(["file_index", "ev"]).ngroups)
    return 0


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("sample", choices=["official", "natural"]); ap.add_argument("--workers", type=int, default=24); a = ap.parse_args()
    if a.sample == "official":
        t = pd.read_parquet(SPD / "spine_harmonization" / "official_ncdelta" / "event_flags_and_table.parquet", columns=["file_index", "ev", "tpc_box", "A_n20mev"])
        ev = t[t.tpc_box & t.A_n20mev.astype(bool)].dropna(subset=["file_index"]).head(int(os.environ.get("SCAN_LIMIT", "10000000")))
        urls = [l.rstrip("\n").split("\t")[2] for l in gzip.open(REPO / "manifests" / "official_gen2_ncdelta_wc.tsv.gz", "rt")][1:]
    else:
        from sbnd_single_photon import natural_signal as NS, samples as S
        sn = pd.read_parquet(SPD / "natural_ncdelta_bnb_cv" / "signal_neutrinos.parquet"); sig = NS.to_signal_truth_table(sn); sig = sig[sig.in_region]
        ev = sig[["file_index", "ev"]]; urls = S.manifest_urls(S.load_samples()["bnb_cv"])
    jobs = [(int(fi), urls[int(fi)], sorted(int(e) for e in g.ev)) for fi, g in ev.groupby("file_index")]
    print(a.sample, "events", len(ev), "files", len(jobs))
    return run(jobs, a.workers, a.sample)


if __name__ == "__main__":
    sys.exit(main())
