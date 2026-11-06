#!/usr/bin/env python
"""Truth/exposure inspection of OFFICIAL Gen2 EX_ncdeltarad flatCAFs. Reads ONLY recTree (+ TotalPOT/TotalGenEvents); no Wire-Cell tree needed.

    source env/setup_eaf.sh
    python scripts/inspect_official_ncdelta_caf.py <root-url-or-path> [...] [--json out.json]

For every file it reports what docs/analysis/NCDELTA_GENERATOR_FILTER_AUDIT.md §5 could only assume: which truth branches exist,
whether gstatus/genweight/startE are filled, the POT/gen-event bookkeeping, and how often the CAF-only PROXY recovers the filter-passing
event (every stored event of the ncdeltarad stream passed the generator filter by construction). Nothing here selects reco candidates.
"""
import argparse, json, sys, warnings
from pathlib import Path
import numpy as np, awkward as ak
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src")); warnings.filterwarnings("ignore")
from sbnd_single_photon import truth_signal as TS


def inspect(url):
    import uproot
    rep = {"url": url}
    with uproot.open(url) as f:
        t = f["recTree"]; keys = set(t.keys())
        rep["trees"] = sorted(k.split(";")[0] for k in f.keys() if "/" not in k)
        rep["has_recTreeWireCell"] = "recTreeWireCell" in rep["trees"]
        rep["n_events"] = int(t.num_entries)
        rep["missing_truth_branches"] = [b for b in TS.TRUTH_BRANCHES if b not in keys]
        rep["has_prefsi"] = any(k.startswith("rec.mc.nu.prefsi") for k in keys)
        extra = [b for b in ("rec.mc.nu.prim.gstatus", "rec.mc.nu.genweight", "rec.mc.nu.prim.startE", "rec.mc.nu.nproton",
                             "rec.mc.nu.npizero", "rec.mc.nu.imp_weight", "rec.mc.nu.prim.contained") if b in keys]
        rep["TotalPOT"] = float(f["TotalPOT"].values()[0]) if "TotalPOT" in f else None
        rep["TotalGenEvents"] = float(f["TotalGenEvents"].values()[0]) if "TotalGenEvents" in f else None
        rep["TotalEvents"] = float(f["TotalEvents"].values()[0]) if "TotalEvents" in f else None
    if rep["missing_truth_branches"]:
        return rep
    d = TS.read_truth_arrays(url)
    r = TS.signal_truth_from_arrays(d, from_filter_stream=True)
    n = len(r["is_ncdelta_radiative"])
    rep.update(n_events_read=n, proxy_recovers_stream=int(r["proxy_recovers_stream"].sum()),
               proxy_recovery_fraction=float(r["proxy_recovers_stream"].mean()) if n else None,
               n_nu_per_event=np.bincount(ak.to_numpy(ak.num(d["rec.mc.nu.pdg"], axis=1))).tolist(),
               proxy_candidates_hist=np.bincount(r["n_signal_nu_candidates"]).tolist(),
               true_proton_category_counts={k: int((r["true_proton_category"] == v).sum()) for k, v in (("none", -1), ("0p", 0), ("1p", 1), ("ge2p", 2))},
               photon_energy_mev_quantiles=(np.nanquantile(r["photon_energy_mev"], [0.05, .25, .5, .75, .95]).round(1).tolist()
                                           if np.isfinite(r["photon_energy_mev"]).any() else None),
               vtx_in_filter_box_frac=float(r["vtx_in_filter_box"][r["is_ncdelta_rad_proxy"]].mean()) if r["is_ncdelta_rad_proxy"].any() else None,
               genie_mode_of_proxy=np.unique(r["genie_mode"][r["is_ncdelta_rad_proxy"]], return_counts=True)[0].tolist())
    # sentinel / unfilled-field checks (the CV facts the audit relies on)
    import uproot
    with uproot.open(url) as f:
        t = f["recTree"]
        for b in extra:
            a = ak.flatten(t[b].array(library="ak"), axis=None)
            a = ak.to_numpy(a) if len(a) else np.zeros(0)
            rep.setdefault("field_check", {})[b] = dict(n=int(len(a)), min=float(np.min(a)) if len(a) else None, max=float(np.max(a)) if len(a) else None,
                                                       frac_sentinel_or_zero=float(np.mean((a <= -9000) | (a == 0))) if len(a) else None)
    return rep


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("urls", nargs="+"); ap.add_argument("--json")
    a = ap.parse_args()
    out = [inspect(u) for u in a.urls]
    print(json.dumps(out, indent=2))
    if a.json:
        Path(a.json).write_text(json.dumps(out, indent=2))
