#!/usr/bin/env python
"""DIAGNOSTIC CAF extraction for the NC-pi0-rich sideband events (SB_ncpi0), old reconstruction and WCLocal2026Nov16. NO selection change, NO tuning, NO correction.

    source env/setup_eaf.sh && export BEARER_TOKEN_FILE=... && python scripts/ncdelta_ncpi0_topology_extract.py [--workers 24] [--productions nov16 old_fg1]

Events = exactly those of `regions_plan_{prod}.pkl` (data D, background B, signal-sample S), representative candidate = lowest c_nu_index region-passing (same as the weight extraction).
Per event (reco, data and MC): pi0-pair observables of T_kine (flag, mass, opening angle, energies, conversion gaps), reco proton rows (type, KE, first-segment length, n segments),
shower dE/dx (tagger), identification check against the analysis-table row (shower energy + vertex must agree exactly).
Per MC event (truth, owner interaction k from the plan; unresolved B events get NaN truth): post-FSI primary protons (KE > 35 MeV count, leading KE), pi0 count/energy/momentum, charged pions, genie mode.
Output: $SP_DATA/ncdelta_purity_datamc/topo/topo_{prod}.parquet
"""
import argparse, multiprocessing as mp, pickle, traceback
import awkward as ak
from ncdelta_syst_common import *
import ncdelta_syst_regions as RGN
from sbnd_single_photon import caf as C

R = "SB_ncpi0"; OUTD = SPD / "ncdelta_purity_datamc" / "topo"; OUTD.mkdir(parents=True, exist_ok=True); MP = 0.938272; GEV = 1000.0
TK = "wc.T_kine."; TG = "wc.T_tagger."
PIO = ["flag", "mass", "angle", "energy_1", "energy_2", "dis_1", "dis_2", "vtx_dis"]
TAGV = ["shw_sp_energy", "shw_sp_vec_median_dedx", "shw_sp_vec_mean_dedx", "shw_sp_vec_dQ_dx_0", "shw_sp_medium_dQ_dx", "shw_sp_shw_vtx_dis"]


def worker(job):
    prod, kind, url, fidx, evs = job            # evs: list of (ev, c_nu_index, owner_k or -1, row_energy, row_x)
    rows, err = [], None
    try:
        f = C.MergedCaf(url).open(); lo, hi = min(e[0] for e in evs), max(e[0] for e in evs) + 1
        wcb = [TG + "nu_index", TK + "kine_nu_x_corr"] + [TK + "kine_pio_" + p for p in PIO] + [TG + v for v in TAGV if f.has_wc(TG + v)] + ["wc.T_segment.segment_id", "wc.T_segment.length_cm", "wc.T_segment.nu_index", "wc.T_segment.pdg"]
        mc = kind in ("B", "S")
        rb = ["rec.mc.nu.prim.pdg", "rec.mc.nu.prim.genE", "rec.mc.nu.prim.genp.x", "rec.mc.nu.prim.genp.y", "rec.mc.nu.prim.genp.z", "rec.mc.nu.genie_mode", "rec.mc.nu.genie_inttype", "rec.mc.nu.E", "rec.mc.nu.nprim"] if mc else []
        d = f.read(wc=wcb, rec=rb, start=lo, stop=hi)
        nest = {k: f.read_nested(TK + "kine_" + k, lo, hi) for k in ("particle_type", "energy_particle", "particle_id", "particle_nseg", "particle_is_shower")}
        for ev, cnu, k, e_row, x_row in evs:
            i = ev - lo; ni = ak.to_numpy(d[TG + "nu_index"][i]); j = int(np.where(ni == cnu)[0][0])
            r = dict(prod=prod, kind=kind, file_index=fidx, ev=ev, c_nu_index=cnu)
            r["id_dE"] = float(abs(float(d[TG + "shw_sp_energy"][i][j]) - e_row)); r["id_dx"] = float(abs(float(d[TK + "kine_nu_x_corr"][i][j]) - x_row))
            for p in PIO: r["pio_" + p] = float(d[TK + "kine_pio_" + p][i][j])
            for v in TAGV:
                if TG + v in d: r[v] = float(d[TG + v][i][j])
            typ = ak.to_numpy(nest["particle_type"][i][j]); ke = ak.to_numpy(nest["energy_particle"][i][j]); pid = ak.to_numpy(nest["particle_id"][i][j]); nseg = ak.to_numpy(nest["particle_nseg"][i][j]); ish = ak.to_numpy(nest["particle_is_shower"][i][j])
            sid = ak.to_numpy(d["wc.T_segment.segment_id"][i]); slen = ak.to_numpy(d["wc.T_segment.length_cm"][i]); snu = ak.to_numpy(d["wc.T_segment.nu_index"][i])
            L = {}
            for p_i in range(len(typ)):
                m = np.where((sid == pid[p_i]) & (snu == cnu))[0]; L[p_i] = float(slen[m[0]]) if len(m) else np.nan
            pr = [p_i for p_i in range(len(typ)) if typ[p_i] == 2212]; p35 = [p_i for p_i in pr if ke[p_i] > 35.0]
            r["n_p_any"], r["n_p35"] = len(pr), len(p35)
            if p35:
                lead = max(p35, key=lambda q: ke[q]); r["lead_p_ke"] = float(ke[lead]); r["lead_p_len_first_seg"] = L[lead]; r["lead_p_nseg"] = int(nseg[lead]); r["lead_p_is_shower_flag"] = int(ish[lead])
            r["n_part_rows"] = len(typ); r["n_shower_rows"] = int((ish == 1).sum()); r["n_track_rows"] = int((ish == 0).sum())
            r["n_gamma_like"] = int(((typ == 22) | (typ == 11)).sum())
            if mc and k >= 0:
                npr = ak.to_numpy(d["rec.mc.nu.nprim"][i]).astype(int); off = int(npr[:k].sum()); sl = slice(off, off + int(npr[k]))      # prim.* is flat per event: slice by nprim offsets
                assert len(d["rec.mc.nu.prim.pdg"][i]) == int(npr.sum()), "prim length != sum(nprim)"
                pdg = ak.to_numpy(d["rec.mc.nu.prim.pdg"][i])[sl]; gE = ak.to_numpy(d["rec.mc.nu.prim.genE"][i])[sl] * GEV
                px, py, pz = (ak.to_numpy(d[f"rec.mc.nu.prim.genp.{a}"][i])[sl] * GEV for a in "xyz"); pm = np.sqrt(px ** 2 + py ** 2 + pz ** 2)
                kep = gE - MP * GEV; isp = pdg == 2212
                r["t_np_any"] = int(isp.sum()); r["t_np35"] = int((isp & (kep > 35)).sum()); r["t_lead_p_ke"] = float(kep[isp].max()) if isp.any() else np.nan
                r["t_n_pi0"] = int((pdg == 111).sum()); r["t_pi0_E"] = float(gE[pdg == 111].max()) if (pdg == 111).any() else np.nan; r["t_pi0_p"] = float(pm[pdg == 111].max()) if (pdg == 111).any() else np.nan
                r["t_n_pich"] = int((np.abs(pdg) == 211).sum()); r["t_n_neutron"] = int((pdg == 2112).sum())
                r["t_nprim"] = int(npr[k]); r["t_mode"] = int(d["rec.mc.nu.genie_mode"][i][k]); r["t_inttype"] = int(d["rec.mc.nu.genie_inttype"][i][k]); r["t_Enu"] = float(d["rec.mc.nu.E"][i][k]) * GEV
            rows.append(r)
        f.close()
    except Exception as e:
        err = f"{url.split('/')[-1]}: {repr(e)[:200]}"
    return rows, err


def main(workers, prods):
    for prod in prods:
        plan = pickle.load(open(SYST / f"regions_plan_{prod}.pkl", "rb")); jobs = []
        sample = {"B": "bnb_cv", "S": "official_gen2_ncdelta", "D": "beam_on_open"}
        for kind in "BSD":
            d = plan[kind][R]; U = RGN.urls(prod, sample[kind])
            for fi, g in d.groupby("file_index"):
                evs = [(int(r.ev), int(r.c_nu_index), int(r.owner_k) if kind != "D" and "owner_k" in d and r.resolved else -1, float(r.c_shw_sp_energy), np.nan) for r in g.itertuples()]
                jobs.append((prod, kind, U[int(fi)], int(fi), evs))
        print(prod, "jobs", len(jobs), flush=True); out, errs = [], []
        with mp.Pool(workers) as pool:
            for n, (rows, err) in enumerate(pool.imap_unordered(worker, jobs, chunksize=4)):
                out += rows; errs += [err] if err else []
                if n % 500 == 0: print(prod, n, len(out), len(errs), flush=True)
        df = pd.DataFrame(out); print(prod, "events", len(df), "errors", len(errs), errs[:5])
        assert not errs, "extraction errors: refusing to save a partial table"
        df.to_parquet(OUTD / f"topo_{prod}.parquet"); print("saved", prod, flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=24); ap.add_argument("--productions", nargs="+", default=["nov16", "old_fg1"])
    a = ap.parse_args(); main(a.workers, a.productions)
