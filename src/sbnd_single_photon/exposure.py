"""Per-file exposure bookkeeping (POT, generated events, run/subrun) for merged CAFs.

NO final analysis weights are computed here. See docs/analysis/POT_EXPOSURE_AUDIT.md.

Facts established on the fg1 MC files (see the audit):
  * one merged CAF == one (run, subrun);
  * ``rec.hdr.pot`` is non-zero only on the event with ``rec.hdr.first_in_subrun == 1``
    (float32), i.e. it is a PER-SUBRUN number stored once per file;
  * ``TotalPOT`` (TH1D, float64) is the POT of the same subrun, and ``TotalGenEvents``
    counts ALL generated events of that subrun, including those that did not survive into the CAF.
"""
from __future__ import annotations

import warnings
from typing import Optional

import numpy as np

HDR = ["rec.hdr.run", "rec.hdr.subrun", "rec.hdr.evt", "rec.hdr.pot",
       "rec.hdr.first_in_subrun", "rec.hdr.first_in_file", "rec.hdr.ngenevt", "rec.hdr.noffbeambnb"]


def _hist_value(f, name: str) -> Optional[float]:
    try:
        return float(f[name].values()[0])
    except Exception:
        return None


def read_file_exposure(url: str) -> dict:
    """Light-weight read of one merged CAF. Never raises: errors go into ``error``."""
    import uproot
    warnings.filterwarnings("ignore")
    out = {"url": url, "error": ""}
    try:
        with uproot.open(url) as f:
            rt, wt = f["recTree"], f["recTreeWireCell"]
            have = set(rt.keys())
            cols = [c for c in HDR if c in have]
            a = rt.arrays(cols, library="np")
            n = len(a["rec.hdr.evt"])
            valid = wt["wc.valid"].array(library="np")
            out.update(
                n_events=n,
                n_wc_events=wt.num_entries,
                n_wc_valid=int((valid == 1).sum()),
                runs=sorted({int(x) for x in a["rec.hdr.run"]}),
                subruns=sorted({(int(r), int(s)) for r, s in zip(a["rec.hdr.run"], a["rec.hdr.subrun"])}),
                hdr_pot_sum=float(np.sum(a["rec.hdr.pot"], dtype=np.float64)) if "rec.hdr.pot" in a else None,
                hdr_pot_n_nonzero=int((a["rec.hdr.pot"] > 0).sum()) if "rec.hdr.pot" in a else None,
                n_first_in_subrun=int(a["rec.hdr.first_in_subrun"].sum()) if "rec.hdr.first_in_subrun" in a else None,
                n_first_in_file=int(a["rec.hdr.first_in_file"].sum()) if "rec.hdr.first_in_file" in a else None,
                noffbeambnb_sum=float(np.sum(a["rec.hdr.noffbeambnb"], dtype=np.float64)) if "rec.hdr.noffbeambnb" in a else None,
                noffbeambnb_n_nonzero=int((a["rec.hdr.noffbeambnb"] > 0).sum()) if "rec.hdr.noffbeambnb" in a else None,
                ngenevt_unique=sorted({int(x) for x in a["rec.hdr.ngenevt"]}) if "rec.hdr.ngenevt" in a else None,
                total_pot=_hist_value(f, "TotalPOT"),
                total_events=_hist_value(f, "TotalEvents"),
                total_gen_events=_hist_value(f, "TotalGenEvents"),
            )
    except Exception as e:  # noqa: BLE001 - the scan must keep going
        out["error"] = f"{type(e).__name__}: {e}"[:300]
    return out


def summarize(rows: list[dict]) -> dict:
    """Aggregate per-file rows; flags duplicated (run, subrun) across files."""
    ok = [r for r in rows if not r["error"]]
    seen: dict = {}
    for r in ok:
        for rs in r["subruns"]:
            seen.setdefault(rs, []).append(r["url"])
    dup = {k: v for k, v in seen.items() if len(v) > 1}
    tp = [r["total_pot"] for r in ok if r.get("total_pot") is not None]
    return {
        "n_files": len(rows), "n_files_ok": len(ok), "n_files_error": len(rows) - len(ok),
        "n_events": sum(r["n_events"] for r in ok),
        "n_wc_valid": sum(r["n_wc_valid"] for r in ok),
        "n_unique_subruns": len(seen), "n_duplicate_subruns": len(dup),
        "total_pot_sum": float(np.sum(tp, dtype=np.float64)) if tp else None,
        "hdr_pot_sum": float(sum(r["hdr_pot_sum"] or 0.0 for r in ok)),
        "n_zero_total_pot_files": sum(1 for r in ok if (r.get("total_pot") or 0) == 0),
        "n_files_hdr_pot_nonzero_count_ne_1": sum(1 for r in ok if r.get("hdr_pot_n_nonzero") != 1),
        "noffbeambnb_sum": float(sum(r.get("noffbeambnb_sum") or 0.0 for r in ok)),
        "n_files_noffbeambnb_nonzero_count_ne_1": sum(1 for r in ok if r.get("noffbeambnb_n_nonzero") != 1),
        "runs_min": min((min(r["runs"]) for r in ok if r["runs"]), default=None),
        "runs_max": max((max(r["runs"]) for r in ok if r["runs"]), default=None),
        "n_unique_runs": len({x for r in ok for x in r["runs"]}),
        "total_gen_events_sum": float(sum(r.get("total_gen_events") or 0 for r in ok)),
    }
