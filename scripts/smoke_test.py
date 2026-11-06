#!/usr/bin/env python
"""Small read-only software smoke test of the baseline framework (NOT a physics result).

    source env/setup_eaf.sh && python scripts/smoke_test.py --events 1000

Per sample (bnb_cv, nuecc, beam_off, beam_on_open): the first ~N events of the manifest are read over XRootD.
Writes only small outputs: tables/smoke/*.csv|json and plots/smoke/*.png.
NO efficiency, NO purity, NO normalisation. Counts are raw, unweighted software-validation counts.
"""
from __future__ import annotations

import argparse, csv, json, resource, sys, time, warnings
from pathlib import Path

import awkward as ak
import numpy as np

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
warnings.filterwarnings("ignore")
from sbnd_single_photon import (samples as S, caf as C, bdt as B, baseline as BL, selection as SEL,  # noqa: E402
                                proton as P, truth as T, plots as PL)

TRUTH_REC = ["rec.mc.nu.pdg", "rec.mc.nu.iscc", "rec.mc.nu.isnc", "rec.mc.nu.npizero", "rec.mc.nu.nprim", "rec.mc.nu.prim.pdg",
             "rec.mc.nu.position.x", "rec.mc.nu.position.y", "rec.mc.nu.position.z"]
KINE = ["wc.T_kine.kine_particle_type", "wc.T_kine.kine_energy_particle", "wc.T_kine.kine_energy_included"]


def rss_gb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6   # kB -> GB (Linux)


def run_sample(name, sample, n_events, models, cfg, specs):
    req = SEL.required_branches(cfg)
    extra_wc = PL.spec_branches(specs)
    acc = PL.HistAccumulator(specs)
    t0 = time.perf_counter()
    res = dict(sample=name, n_files=0, n_events=0, n_valid=0, cand_hist={}, finite={}, cutflow_rows=None,
               proton={}, truth={}, file_times=[], schema_md5=set(), dl_weights=set(), n_wc_branches=set(),
               bdt_evaluable={}, ids_aligned=True)
    cut_arrays = None; valid_all = []; truth_codes = []
    pieces = []
    for url in S.manifest_urls(sample):
        if res["n_events"] >= n_events:
            break
        tf = time.perf_counter()
        with C.MergedCaf(url) as f:
            stop = min(f.num_entries, n_events - res["n_events"])
            res["schema_md5"].add(f.schema_md5()); res["dl_weights"].add(f.trun("dl_weights"))
            res["n_wc_branches"].add(f.n_wc_branches)
            d = BL.read_baseline_arrays(f, models, extra_wc=extra_wc + KINE, cut_branches=req["wc"], stop=stop,
                                        extra_rec=TRUTH_REC if sample.is_mc else [])
            valid = np.asarray(ak.to_numpy(d["wc.valid"]) == 1)
            pdg = f.read_nested("wc.T_kine.kine_particle_type", 0, stop)
            ke = f.read_nested("wc.T_kine.kine_energy_particle", 0, stop)
            inc = f.read_nested("wc.T_kine.kine_energy_included", 0, stop)
            res["n_files"] += 1; res["n_events"] += stop; res["n_valid"] += int(valid.sum())
            acc.fill(d, valid, pdg, ke)
            ncand = ak.to_numpy(ak.num(d["wc.T_tagger.nu_index"], axis=1))
            for k, v in zip(*np.unique(ncand[valid], return_counts=True)):
                res["cand_hist"][int(k)] = res["cand_hist"].get(int(k), 0) + int(v)
            # availability / finiteness of every baseline cut variable (candidates of valid events)
            for b in req["wc"] + req["derived"]:
                x = ak.to_numpy(ak.flatten(d[b][valid], axis=None))
                e = res["finite"].setdefault(b, [0, 0]); e[0] += int(np.isfinite(x).sum()); e[1] += int(len(x))
            for m in models:
                x = ak.to_numpy(ak.flatten(d[f"derived.single_photon_{m}_score"][valid], axis=None))
                e = res["bdt_evaluable"].setdefault(m, [0, 0]); e[0] += int(np.isfinite(x).sum()); e[1] += int(len(x))
            # reco proton categories (per candidate; all candidates, no selection)
            for tag, kw in (("ke>35", {}), ("ke>35 & included==1", {"require_included": True})):
                c = P.classify_reco_protons(pdg[valid], ke[valid], 35.0, included=inc[valid], **kw)
                v, n = np.unique(ak.to_numpy(ak.flatten(c, axis=None)), return_counts=True)
                dct = res["proton"].setdefault(tag, {})
                for a, b2 in zip(v, n):
                    dct[P.LABELS[int(a)]] = dct.get(P.LABELS[int(a)], 0) + int(b2)
            pieces.append({k: d[k] for k in req["wc"] + req["derived"] + ["wc.T_tagger.nu_index"]})
            valid_all.append(valid)
            if sample.is_mc and f.has_truth_matching:
                n_pi0 = ak.sum(C.per_candidate(d["rec.mc.nu.prim.pdg"], d["rec.mc.nu.nprim"]) == 111, axis=-1)  # npizero field is almost always 0
                code = T.classify_events(d["rec.mc.nu.pdg"], d["rec.mc.nu.iscc"], d["rec.mc.nu.isnc"],
                                         n_pi0, d["rec.mc.nu.position.x"],
                                         d["rec.mc.nu.position.y"], d["rec.mc.nu.position.z"])
                for k, n in zip(*np.unique(code, return_counts=True)):
                    nm = T.CATEGORIES[int(k)]; res["truth"][nm] = res["truth"].get(nm, 0) + int(n)
        res["file_times"].append(time.perf_counter() - tf)
    # software cut-flow on the concatenated arrays (raw counts)
    cat = {k: ak.concatenate([p[k] for p in pieces]) for k in pieces[0]}
    res["cutflow_rows"] = SEL.cutflow(cat, cfg, np.concatenate(valid_all), cfg.get("candidate_policy", "any"))
    res["wall_s"] = time.perf_counter() - t0
    res["max_rss_gb_so_far"] = rss_gb()
    for k in ("schema_md5", "dl_weights", "n_wc_branches"):
        res[k] = sorted(res[k], key=str)
    return res, acc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events", type=int, default=1000)
    ap.add_argument("--samples", nargs="*", default=["bnb_cv", "nuecc", "beam_off", "beam_on_open"])
    ap.add_argument("--outdir", default=str(REPO / "tables" / "smoke"))
    ap.add_argument("--plotdir", default=str(REPO / "plots" / "smoke"))
    a = ap.parse_args()
    reg = S.load_samples(); cfg = SEL.load_config(); specs = PL.load_specs()
    models = B.load_models()
    out = Path(a.outdir); out.mkdir(parents=True, exist_ok=True)
    results, hists = {}, {}
    for name in a.samples:
        print(f"[smoke] {name} ...", flush=True)
        r, acc = run_sample(name, reg[name], a.events, models, cfg, specs)
        results[name] = r; hists[name] = acc.to_json()
        print(f"[smoke] {name}: {r['n_events']} events, {r['n_files']} files, {r['wall_s']:.1f}s, "
              f"rss {r['max_rss_gb_so_far']:.2f} GB", flush=True)
        (out / f"hists_{name}.json").write_text(json.dumps(hists[name]))
    # branch compatibility MC vs beam-on (first file of each)
    comp = {}
    sets = {}
    for name in a.samples:
        with C.MergedCaf(S.manifest_urls(reg[name], 0, 1)[0]) as f:
            sets[name] = f.wc_branches
    if "beam_on_open" in sets:
        on = sets["beam_on_open"]
        for name, s in sets.items():
            comp[name] = {"n_wc_branches": len(s), "branches_not_in_beam_on": len(s - on),
                          "beam_on_branches_not_here": len(on - s)}
    summary = {"events_requested": a.events, "baseline_policy": cfg.get("candidate_policy"),
               "samples": {k: {kk: vv for kk, vv in v.items() if kk != "cutflow_rows"} for k, v in results.items()},
               "branch_compat_vs_beam_on": comp}
    for v in summary["samples"].values():
        v["file_time_mean_s"] = float(np.mean(v["file_times"])); v.pop("file_times")
        v["events_per_s"] = v["n_events"] / v["wall_s"]
        v["valid_fraction"] = v["n_valid"] / max(v["n_events"], 1)
        v["finite_fraction"] = {b: (x[0] / x[1] if x[1] else None) for b, x in v.pop("finite").items()}
        v["bdt_evaluable_fraction"] = {b: (x[0] / x[1] if x[1] else None) for b, x in v.pop("bdt_evaluable").items()}
    summary["max_rss_gb"] = rss_gb()
    (out / "smoke_summary.json").write_text(json.dumps(summary, indent=1, default=str))
    with open(out / "smoke_cutflow_raw_counts.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["sample", "cut", "n_events_raw"])
        for k, v in results.items():
            for row in v["cutflow_rows"]:
                w.writerow([k, row["cut"], row["n_events"]])
    with open(out / "smoke_truth_categories_raw_counts.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["sample", "category", "n_events_raw"])
        for k, v in results.items():
            for c, n in sorted(v["truth"].items()):
                w.writerow([k, c, n])
    with open(out / "smoke_reco_proton_counts.csv", "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["sample", "rule", "category", "n_candidates"])
        for k, v in results.items():
            for rule, d in v["proton"].items():
                for c, n in d.items():
                    w.writerow([k, rule, c, n])
    PL.draw(hists, specs, a.plotdir)
    print(json.dumps({k: {"events": v["n_events"], "valid": v["n_valid"], "wall_s": round(v["wall_s"], 1)}
                      for k, v in results.items()}))


if __name__ == "__main__":
    main()
