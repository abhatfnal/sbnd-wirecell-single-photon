#!/usr/bin/env python
"""Per-EVENT extraction of the `reinteractions_neutron_Geant4` weights (1000 universes) of the owner interaction for the control-region events used in the covariance (SB_numu, preselection;
background and signal-sample events with a resolved owner), plus owner truth (PDG, CC/NC, genie mode, true Enu, true proton >35 MeV and neutron multiplicity) and the maximum neutron-G4 weight over ALL
interactions of the event (association check). Same identity/layout/vertex/pdg checks as `region_accum_worker`. NO clipping. Output: $SP_DATA/ncdelta_purity_datamc/syst/neutron_g4_events_{prod}.parquet/.npy

    source env/setup_eaf.sh && export BEARER_TOKEN_FILE=... && python scripts/ncdelta_neutron_g4_extract.py [--workers 24] [--productions nov16 old_fg1]
"""
import argparse, multiprocessing as mp
from ncdelta_syst_common import *
import ncdelta_syst_regions as RGN
from sbnd_single_photon import syst_weights as SW

REGS = ["SB_numu", "preselection"]; FN = "reinteractions_neutron_Geant4"; MP_GEV = 0.938272


def worker(job):
    import awkward as ak, uproot
    tag, files, lo, hi = job["tag"], job["files"], job["lo"], job["hi"]; out, cnt = [], dict(files=0, file_errors=0, events=0, not_found=0, layout_bad=0, vertex_bad=0, pdg_bad=0, ids_not_identical=0, entry_not_equal=0, errs=[])
    for fi, url, rows in files:
        try:
            f = uproot.open(url); t = f["recTree"]; w = f["recTreeWireCell"]; nuniv = np.asarray(f["globalTree"]["global/wgts/wgts.nuniv"].array(library="ak")[0].tolist())
            rid = np.stack([t[b].array(library="np").astype(np.int64) for b in ("rec.hdr.run", "rec.hdr.subrun", "rec.hdr.evt")], 1); wid = np.stack([w[b].array(library="np").astype(np.int64) for b in ("wc.run", "wc.subrun", "wc.evt")], 1)
            cnt["ids_not_identical"] += int(not (len(rid) == len(wid) and np.array_equal(rid, wid)))
            ent = SW.map_events_by_id(rid, np.array([[r["run"], r["subrun"], r["evt"]] for r in rows], dtype=np.int64))
            a = t.arrays(["rec.mc.nu.pdg", "rec.mc.nu.iscc", "rec.mc.nu.E", "rec.mc.nu.genie_mode", "rec.mc.nu.nprim", "rec.mc.nu.position.x", "rec.mc.nu.position.y", "rec.mc.nu.position.z", "rec.mc.nu.wgt.univ",
                          "rec.mc.nu.wgt.univ..length", "rec.mc.nu.prim.pdg", "rec.mc.nu.prim.genE"], library="ak"); cnt["files"] += 1
            for r, e in zip(rows, ent):
                cnt["events"] += 1
                if e < 0: cnt["not_found"] += 1; continue
                cnt["entry_not_equal"] += int(e != r["ev"]); n_nu = len(a["rec.mc.nu.pdg"][e]); k = int(r["k"])
                if not SW.layout_ok(np.asarray(a["rec.mc.nu.wgt.univ..length"][e]), n_nu, nuniv) or not (0 <= k < n_nu): cnt["layout_bad"] += 1; continue
                px, py, pz = (float(a[f"rec.mc.nu.position.{q}"][e][k]) for q in "xyz")
                if np.sqrt((px - r["ex"]) ** 2 + (py - r["ey"]) ** 2 + (pz - r["ez"]) ** 2) > 1e-3: cnt["vertex_bad"] += 1; continue
                if r.get("epdg", 0) != 0 and int(a["rec.mc.nu.pdg"][e][k]) != r["epdg"]: cnt["pdg_bad"] += 1; continue
                blks = SW.split_blocks(np.asarray(a["rec.mc.nu.wgt.univ"][e]), n_nu, nuniv)[:, lo:hi].astype(np.float32)          # all interactions, this function only
                npr = np.asarray(a["rec.mc.nu.nprim"][e]).astype(int); off = int(npr[:k].sum()); sl = slice(off, off + int(npr[k]))
                pdg = np.asarray(a["rec.mc.nu.prim.pdg"][e])[sl]; ke = np.asarray(a["rec.mc.nu.prim.genE"][e])[sl] * 1000.0 - MP_GEV * 1000.0
                out.append(dict(tag=tag, file_index=fi, ev=r["ev"], run=r["run"], subrun=r["subrun"], evt=r["evt"], k=k, n_nu=n_nu, nu_pdg=int(a["rec.mc.nu.pdg"][e][k]), iscc=int(a["rec.mc.nu.iscc"][e][k]),
                                mode=int(a["rec.mc.nu.genie_mode"][e][k]), Enu_GeV=float(a["rec.mc.nu.E"][e][k]), t_np35=int(((pdg == 2212) & (ke > 35)).sum()), t_nneutron=int((pdg == 2112).sum()),
                                max_w_all_interactions=float(blks.max()), max_w_owner=float(blks[k].max()), min_w_owner=float(blks[k].min()), items=r["items"], W=blks[k].copy()))
        except Exception as ex:
            cnt["file_errors"] += 1; cnt["errs"].append(repr(ex)[:200])
    return dict(out=out, cnt=cnt)


def main(workers, prods):
    ft = RGN.CV.FT.set_index("name").loc[FN]; lo, hi = int(ft.start), int(ft.stop); assert hi - lo == 1000
    for prod in prods:
        jobs = [dict(j, lo=lo, hi=hi) for j in RGN.jobs_for(prod, REGS)]; print(prod, "jobs", len(jobs), "files", sum(len(j["files"]) for j in jobs), flush=True)
        with mp.get_context("spawn").Pool(workers) as p:
            res = list(p.imap_unordered(worker, jobs))
        cs = {k: sum(r["cnt"][k] for r in res) for k in res[0]["cnt"] if k != "errs"}; print(cs, [e for r in res for e in r["cnt"]["errs"]][:3], flush=True)
        assert not {k: v for k, v in cs.items() if k not in ("files", "events") and v}, "extraction checks failed; nothing saved"
        ev = [o for r in res for o in r["out"]]; W = np.stack([o.pop("W") for o in ev]); items = [o.pop("items") for o in ev]
        df = pd.DataFrame(ev)
        for ri, reg in enumerate(REGS):
            df["in_" + reg] = [any(s // 3 == ri for s, _ in it) for it in items]; df["binT_" + reg] = [next((b for s, b in it if s == ri * 3 + 2), -1) for it in items]
        df.to_parquet(SYST / f"neutron_g4_events_{prod}.parquet", index=False); np.save(SYST / f"neutron_g4_events_{prod}.npy", W); print("saved", prod, W.shape, flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=24); ap.add_argument("--productions", nargs="+", default=["nov16", "old_fg1"]); a = ap.parse_args(); main(a.workers, a.productions)
