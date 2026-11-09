#!/usr/bin/env python
"""Per-file BNB gate counters of the data samples (read-only): beam-on `rec.hdr.nbnbinfo` and `rec.hdr.pot`, beam-off `rec.hdr.noffbeambnb`.

    source env/setup_eaf.sh && python scripts/exposure_gate_counters.py --workers 20

Source facts (sbncode CAFMaker_module.cc / FillExposure.cxx / SBNDBNBEXTRetriever / SBNDBNBRetriever, see DATA_EXPOSURE_NORMALIZATION.md):
  rec.hdr.nbnbinfo   = number of BNBSpillInfo entries of the sub-run (one per beam spill matched to the beam database), filled on the first event of a sub-run
  rec.hdr.pot        = sum of the POT of those spills
  rec.hdr.noffbeambnb= sum over the off-beam (EXT) triggers of the PTB GateCounter: BNB gates counted since the previous trigger
This only RECORDS the raw counters. No scale factor is computed.
Writes $SP_DATA/exposure_scan/gate_counters_<sample>.parquet and tables/pot/gate_counters_summary.json. Workers <= 24.
"""
from __future__ import annotations
import argparse, json, os, sys, warnings
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
import multiprocessing as mp
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd


def work(job):
    i, url = job
    from sbnd_single_photon import caf as C
    try:
        with C.MergedCaf(url, check_alignment=False) as f:
            a = f._rt.arrays(["rec.hdr.run", "rec.hdr.subrun", "rec.hdr.nbnbinfo", "rec.hdr.noffbeambnb", "rec.hdr.pot", "rec.hdr.first_in_subrun"], library="np")
            tp = float(f._f["TotalPOT"].values()[0]) if "TotalPOT" in f._f else np.nan
        return dict(file_index=i, ok=True, n_events=len(a["rec.hdr.run"]), run=int(a["rec.hdr.run"][0]), n_subruns=int(a["rec.hdr.first_in_subrun"].sum()),
                    nbnbinfo=float(a["rec.hdr.nbnbinfo"].sum()), noffbeambnb=float(a["rec.hdr.noffbeambnb"].sum()), hdr_pot=float(a["rec.hdr.pot"].sum()), total_pot=tp,
                    n_nonzero_nbnb=int((a["rec.hdr.nbnbinfo"] > 0).sum()), n_nonzero_off=int((a["rec.hdr.noffbeambnb"] > 0).sum()))
    except Exception as e:  # noqa: BLE001
        return dict(file_index=i, ok=False, err=repr(e)[:150])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=20); a = ap.parse_args()
    from sbnd_single_photon import samples as S
    out = Path(os.environ["SP_DATA"]) / "exposure_scan"; summ = {}
    for name in ("beam_on_open", "beam_off"):
        urls = S.manifest_urls(S.load_samples()[name])
        with mp.get_context("spawn").Pool(min(a.workers, 24)) as p:
            rows = list(p.imap_unordered(work, list(enumerate(urls)), chunksize=4))
        df = pd.DataFrame(rows).sort_values("file_index"); df.to_parquet(out / f"gate_counters_{name}.parquet", index=False)
        ok = df[df.ok]
        summ[name] = dict(files=int(len(df)), read_ok=int(len(ok)), events=int(ok.n_events.sum()), sum_nbnbinfo=float(ok.nbnbinfo.sum()), sum_noffbeambnb=float(ok.noffbeambnb.sum()),
                          sum_hdr_pot=float(ok.hdr_pot.sum()), sum_TotalPOT=float(ok.total_pot.sum()), files_with_one_nonzero_nbnbinfo=int((ok.n_nonzero_nbnb == 1).sum()),
                          files_with_one_nonzero_noffbeambnb=int((ok.n_nonzero_off == 1).sum()), runs=sorted(int(r) for r in ok.run.unique())[:3] + ["..."] if len(ok.run.unique()) > 6 else sorted(int(r) for r in ok.run.unique()),
                          n_runs=int(ok.run.nunique()), files_per_run_top=ok.run.value_counts().head(5).to_dict())
        print(name, json.dumps(summ[name], default=str), flush=True)
    (REPO / "tables" / "pot" / "gate_counters_summary.json").write_text(json.dumps(summ, indent=1, default=str))


if __name__ == "__main__":
    main()
