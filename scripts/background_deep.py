"""Deep per-selected-candidate truth extraction (worker module of background_mechanisms_scan.py). MC evaluation only.

For each passing candidate (ev, nu): the production candidate association (T_match level 3), the matched interaction, the truth origin of the
shower that carries ``shw_sp_energy`` (see docs/analysis/SELECTED_SHOWER_TRUTH_MATCH_AUDIT.md for the mapping), the pi0 decay chain from
``T_truth_pf`` and the proton rows/tracks. Flags are NOT mutually exclusive.
"""
from __future__ import annotations
import os
from pathlib import Path
import numpy as np
import pandas as pd
import awkward as ak

AV = dict(x=(-200.0, 200.0), y=(-200.0, 200.0), z=(0.0, 500.0))       # PROVISIONAL TPC box, not an FV
THR = 35.0
PMASS = 938.272


def _flat(f, tree, cols, jag=()):
    a = f._wt.arrays([f"wc.{tree}.{c}" for c in cols], library="ak", how=dict)
    first = a[f"wc.{tree}.{cols[0]}"]
    cnt = ak.to_numpy(ak.num(first, axis=1))
    d = pd.DataFrame({c: ak.to_numpy(ak.flatten(a[f"wc.{tree}.{c}"])) for c in cols})
    d["ev"] = np.repeat(np.arange(len(cnt)), cnt)
    return d


def _in_box(x, y, z):
    return (AV["x"][0] < x < AV["x"][1]) and (AV["y"][0] < y < AV["y"][1]) and (AV["z"][0] < z < AV["z"][1])


def _dominant(ov_rows, tracks):
    """Dominant truth track (by summed overlap charge) of a set of overlap rows -> dict (trackid, q_dom, q_tot, frac, track fields)."""
    if len(ov_rows) == 0:
        return dict(trackid=-1, q_dom=0.0, q_tot=0.0, frac=np.nan)
    g = ov_rows.groupby("trackid").q.sum().sort_values(ascending=False)
    tid = int(g.index[0]); qt = float(g.sum())
    out = dict(trackid=tid, q_dom=float(g.iloc[0]), q_tot=qt, frac=float(g.iloc[0]) / qt if qt > 0 else np.nan)
    t = tracks.get(tid)
    if t is not None:
        out.update({k: t[k] for k in ("pdg", "nu_idx", "mother_pdg", "mother_trackid", "process", "ancestor_trackid", "prong_trackid", "start_E", "q_in_blobs")})
    return out


def deep_work(job):
    from sbnd_single_photon import caf as C, background_truth as BT, truth_signal as TS
    idx, url, outdir, sel = job
    out = Path(outdir) / f"{idx}.parquet"
    if out.exists():
        return idx, "cached"
    try:
        recs = []
        with C.MergedCaf(url) as f:
            R, I = BT.rows_and_items(f)
            assoc = BT.candidate_association(R, I)
            tn = BT.truth_nu_table(f)
            d = TS.read_truth_arrays(url, with_record=False); rn = BT.recnu_table(d); lk = BT.link_truth_nu_to_recnu(tn, rn)
            cand_nu = f._wt["wc.T_tagger.nu_index"].array(library="ak")
            cnt = ak.to_numpy(ak.num(cand_nu, axis=1))
            tag = pd.DataFrame(dict(ev=np.repeat(np.arange(len(cnt)), cnt), nu_index=ak.to_numpy(ak.flatten(cand_nu)).astype(int)))
            tag["ci"] = tag.groupby("ev").cumcount()
            energy = ak.to_numpy(ak.flatten(f._wt["wc.T_tagger.shw_sp_energy"].array(library="ak")))
            tag["shw_sp_energy"] = energy
            kn = {c: f.read_nested("wc.T_kine." + c) for c in ("kine_particle_type", "kine_energy_particle", "kine_particle_id", "kine_particle_is_shower", "kine_energy_included", "kine_particle_pool")}
            ov = _flat(f, "T_overlap", ["nu_index", "particle_id", "in_enu", "trackid", "nu_idx", "q"])
            tt = _flat(f, "T_truth_track", ["trackid", "nu_idx", "ancestor_trackid", "prong_trackid", "pdg", "mother_trackid", "mother_pdg", "process", "q_in_blobs", "start_E"])
            pf = _flat(f, "T_truth_pf", ["nu_row", "trackid", "parent_trackid", "pdg", "process", "E", "KE", "start_x", "start_y", "start_z", "end_x", "end_y", "end_z", "start_px", "start_py", "start_pz"])
            n_blobs_cols = None
        tracks_by_ev = {e: g.drop_duplicates("trackid").set_index("trackid").assign(trackid=lambda x: x.index).to_dict("index") for e, g in tt.groupby("ev")}
        pfs_by_ev = {e: g for e, g in pf.groupby("ev")}
        tts_by_ev = {e: g for e, g in tt.groupby("ev")}
        ovs = {e: g for e, g in ov.groupby("ev")}
        for ev, nu in sel:
            ev = int(ev); nu = int(nu)
            rec = dict(file_index=int(idx), ev=ev, nu_index=nu)
            a = assoc[(assoc.ev == ev) & (assoc.nu_index == nu)]
            if len(a) == 0:
                rec["assoc_missing"] = True; recs.append(rec); continue
            rec.update({c: a[c].iloc[0] for c in a.columns if c.startswith("tm_")})
            top = int(rec["tm_top_nu"]); tr = tracks_by_ev.get(ev, {}); ovc = ovs.get(ev, pd.DataFrame(columns=ov.columns)); ovc = ovc[ovc.nu_index == nu]
            cd = _dominant(ovc, tr); rec.update({"ovl_cand_" + k: v for k, v in cd.items()})
            # matched interaction
            t = tn[(tn.ev == ev) & (tn.nu_idx == top)]
            s_nu = top if top >= 0 else None
            if s_nu is not None and len(t):
                t = t.iloc[0]; rec.update(mnu_pdg=int(t.pdg), mnu_ccnc=int(t.ccnc), mnu_mode=int(t["mode"]), mnu_E=float(t.E), mnu_x=float(t.vtx_x), mnu_y=float(t.vtx_y), mnu_z=float(t.vtx_z), mnu_edep=float(t.edep))
                l = lk[(lk.ev == ev) & (lk.nu_idx == top)]
                if len(l):
                    k = int(l.k.iloc[0]); rec["mnu_k"] = k; rec["mnu_link_dist_cm"] = float(l.link_dist_cm.iloc[0])
                    r = rn[(rn.ev == ev) & (rn.k == k)].iloc[0]
                    rec.update(k_n_pi0=int(r.n_pi0), k_n_p35=int(r.n_p35), k_iscc=int(r.iscc), k_pdg=int(r.pdg), k_n_photon=int(r.n_photon))
            # selected shower row
            ci = int(tag[(tag.ev == ev) & (tag.nu_index == nu)].ci.iloc[0]); E = float(tag[(tag.ev == ev) & (tag.nu_index == nu)].shw_sp_energy.iloc[0])
            typ = ak.to_numpy(kn["kine_particle_type"][ev][ci]); ke = ak.to_numpy(kn["kine_energy_particle"][ev][ci]); pid = ak.to_numpy(kn["kine_particle_id"][ev][ci])
            ish = ak.to_numpy(kn["kine_particle_is_shower"][ev][ci]); inc = ak.to_numpy(kn["kine_energy_included"][ev][ci]); pool = ak.to_numpy(kn["kine_particle_pool"][ev][ci])
            hits = [i for i in range(len(ke)) if ish[i] == 1 and abs(ke[i] - E) <= 1e-4 * max(E, 1.0)]
            rec["sel_n_row_hits"] = len(hits)
            if hits:
                i = hits[0]; rec.update(sel_row=i, sel_row_type=int(typ[i]), sel_row_ke=float(ke[i]), sel_row_included=int(inc[i]), sel_row_pool=int(pool[i]), sel_row_pid=int(pid[i]))
                shower_ke = [ke[j] for j in range(len(ke)) if ish[j] == 1]
                rec["sel_shower_is_max_ke_shower"] = bool(abs(max(shower_ke) - ke[i]) < 1e-6)
                sd = _dominant(ovc[ovc.particle_id == pid[i]], tr); rec.update({"sh_" + k: v for k, v in sd.items()})
                rec["sh_primary"] = bool(sd.get("mother_pdg", 1) == 0 and sd.get("process", 1) == 0) if "pdg" in sd else False
                anc = sd.get("ancestor_trackid", -1)
                pe = pfs_by_ev.get(ev)
                if pe is not None and anc is not None and anc >= 0:
                    ap = pe[pe.trackid == anc]
                    rec["sh_ancestor_pdg"] = int(ap.pdg.iloc[0]) if len(ap) else (int(tr[anc]["pdg"]) if anc in tr else 0)
                rec["sh_origin"] = BT.origin_class(sd.get("pdg", np.nan), sd.get("nu_idx", -1), sd.get("trackid", -1)) if "pdg" in sd else "cosmic_or_unmatched"
            # pi0 chain of the matched interaction
            pe = pfs_by_ev.get(ev); te = tts_by_ev.get(ev)
            if s_nu is not None and pe is not None:
                pe = pe[pe.nu_row == s_nu]; pis = pe[pe.pdg == 111]
                rec["pf_n_pi0"] = len(pis)
                if len(pis):
                    p0 = pis.sort_values("E", ascending=False).iloc[0]
                    rec.update(pi0_E=float(p0.E), pi0_KE=float(p0.KE), pi0_p=float(np.sqrt(p0.start_px ** 2 + p0.start_py ** 2 + p0.start_pz ** 2)),
                               pi0_vtx_in_tpc=_in_box(p0.start_x, p0.start_y, p0.start_z))
                    ph = pe[(pe.parent_trackid == p0.trackid) & (pe.pdg == 22)].sort_values("E", ascending=False)
                    rec["pi0_n_daughter_photons"] = len(ph)
                    ph = ph.head(2).reset_index(drop=True)
                    for j in range(len(ph)):
                        q = ph.iloc[j]; p = f"ph{j+1}_"; tid = int(q.trackid)
                        rec[p + "E"] = float(q.E); rec[p + "end_in_tpc"] = _in_box(q.end_x, q.end_y, q.end_z); rec[p + "lt20"] = bool(q.E * 1000 < 20.0)
                        pro = te[te.prong_trackid == tid] if te is not None else pd.DataFrame(columns=tt.columns)
                        tids = set(pro.trackid.tolist()) | {tid}
                        rec[p + "q_in_blobs"] = float(pro.q_in_blobs.sum())
                        o2 = ovs.get(ev, pd.DataFrame(columns=ov.columns)); o2 = o2[o2.trackid.isin(tids)]
                        rec[p + "n_overlap_rows"] = int(len(o2))
                        if len(o2):
                            g = o2.groupby(["nu_index", "particle_id"]).q.sum().sort_values(ascending=False)
                            dn, dp = g.index[0]
                            rec[p + "dom_cand"] = int(dn); rec[p + "same_cand"] = bool(dn == nu)
                            rec[p + "is_selected_row"] = bool(dn == nu and "sel_row_pid" in rec and dp == rec["sel_row_pid"])
                            rec[p + "q_in_selected_row"] = float(o2[(o2.nu_index == nu) & (o2.particle_id == rec.get("sel_row_pid", -9))].q.sum())
                            if dn == nu:
                                w = np.where(pid == dp)[0]
                                if len(w):
                                    rec[p + "dom_row_type"] = int(typ[w[0]]); rec[p + "dom_row_is_shower"] = bool(ish[w[0]] == 1)
                    if "sh_trackid" in rec:
                        for j in range(len(ph)):
                            tid = int(ph.iloc[j].trackid)
                            pro = te[te.prong_trackid == tid] if te is not None else pd.DataFrame()
                            if rec["sh_trackid"] in set(pro.trackid.tolist()) | {tid}:
                                rec["selected_photon_rank"] = j + 1
            # primary CC lepton (for nue)
            if s_nu is not None and pe is not None:
                lep = pe[(pe.process == 0) & (pe.pdg.abs() == 11)]
                rec["sel_is_primary_nue_lepton"] = bool("sh_trackid" in rec and len(lep) and rec["sh_trackid"] in set(lep.trackid.tolist()))
            # protons: reco rows and truth primaries
            rp = [i for i in range(len(ke)) if typ[i] == 2212 and ke[i] > THR]
            rec["n_reco_p35"] = len(rp)
            if s_nu is not None:
                cats = dict(rp_primary_signal=0, rp_secondary_proton=0, rp_other_pdg_same_nu=0, rp_other_neutrino=0, rp_unmatched=0, rp_leftover_inc3=0, rp_truth_ke_below_thr=0)
                for i in rp:
                    dd = _dominant(ovc[ovc.particle_id == pid[i]], tr)
                    if inc[i] == 3: cats["rp_leftover_inc3"] += 1
                    if "pdg" not in dd or dd["trackid"] < 0 or dd["nu_idx"] < 0: cats["rp_unmatched"] += 1
                    elif dd["nu_idx"] != s_nu: cats["rp_other_neutrino"] += 1
                    elif dd["pdg"] != 2212: cats["rp_other_pdg_same_nu"] += 1
                    elif dd["mother_pdg"] == 0:
                        cats["rp_primary_signal"] += 1
                        if (dd["start_E"] * 1000.0 - PMASS) < THR: cats["rp_truth_ke_below_thr"] += 1
                    else: cats["rp_secondary_proton"] += 1
                rec.update(cats)
                prot = pe[(pe.pdg == 2212) & (pe.process == 0) & (pe.KE * 1000.0 > THR)] if pe is not None else pd.DataFrame()
                fate = dict(tp_found=0, tp_row_below_thr=0, tp_row_other_pid=0, tp_no_row=0, tp_only_other_cand=0); other_types = []
                for tid in prot.trackid:
                    pro = te[te.prong_trackid == tid] if te is not None else pd.DataFrame()
                    tids = set(pro.trackid.tolist()) | {int(tid)}
                    o3 = ovs.get(ev, pd.DataFrame(columns=ov.columns)); o3 = o3[o3.trackid.isin(tids)]
                    if len(o3) == 0: fate["tp_no_row"] += 1; continue
                    o3c = o3[o3.nu_index == nu]
                    if len(o3c) == 0: fate["tp_only_other_cand"] += 1; continue
                    g = o3c.groupby("particle_id").q.sum().sort_values(ascending=False); w = np.where(pid == g.index[0])[0]
                    if not len(w): fate["tp_no_row"] += 1
                    elif typ[w[0]] == 2212 and ke[w[0]] > THR: fate["tp_found"] += 1
                    elif typ[w[0]] == 2212: fate["tp_row_below_thr"] += 1
                    else:
                        fate["tp_row_other_pid"] += 1; other_types.append(int(typ[w[0]]))
                rec.update(fate); rec["tp_other_pid_types"] = ";".join(str(x) for x in other_types); rec["n_truth_primary_p35_pf"] = int(len(prot))
            recs.append(rec)
        df = pd.DataFrame(recs)
        tmp = out.with_name(out.name + ".tmp"); df.to_parquet(tmp, index=False); os.replace(tmp, out)
        return idx, "ok"
    except Exception as e:
        import traceback
        return idx, "ERR " + repr(e)[:200] + traceback.format_exc()[-300:]
