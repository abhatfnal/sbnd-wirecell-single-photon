#!/usr/bin/env python
"""Common NC-Delta reconstructed observables of the frozen Wire-Cell baseline (READ-ONLY analysis of stored tables; no decision, cut, threshold or policy changes).

    source env/setup_eaf.sh
    python scripts/common_observables_scan.py ; python scripts/common_observables_genie_scan.py          # raw tables (once)
    python scripts/common_observables_audit.py

Outputs outside Git: $SP_DATA/common_observables/official_ncdelta/ (selected_object_table, delta_mass_table, resolution_tables/, background_shapes/, policy_sensitivity/, metadata.json);
compact summaries: tables/common_observables/; headline figures: plots/common_observables/.
Signal denominators use the provisional TPC truth box, the BNB CV selected objects have no common FV: every signal-vs-background comparison is a unit-area SHAPE diagnostic, never a rate, purity or S/B.
"""
from __future__ import annotations
import hashlib, json, os, subprocess, sys, warnings
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from scipy import stats
from sbnd_single_photon import exclusive_signal as X, observables as OB, plotstyle as PS
import matplotlib.pyplot as plt

SPD = Path(os.environ["SP_DATA"]); OUT = SPD / "common_observables" / "official_ncdelta"; RAW = OUT / "raw"; P8 = SPD / "other_bdt_audit" / "official_ncdelta"; P9 = SPD / "shower_vertex_audit" / "official_ncdelta"; P10 = SPD / "proton_truth_association" / "official_ncdelta"
PLD = REPO / "plots" / "common_observables"; SUMD = REPO / "tables" / "common_observables"
for d in (PLD, SUMD, OUT, OUT / "resolution_tables", OUT / "background_shapes", OUT / "policy_sensitivity"):
    d.mkdir(parents=True, exist_ok=True)
K = ["file_index", "ev"]; KC = ["file_index", "ev", "cand"]; SUMMARY: dict = {}
PROV = "official Gen2 NC-Delta + BNB CV | frozen Wire-Cell baseline (policy any) | selected-object SHAPES, no rates / S:B | descriptive, no cut"
PV = list(OB.PROTON_POLICIES)
TL = {0: "truth 0p", 1: "truth 1p", 2: "truth >=2p"}
BKG_ORDER = ["NC_PI0", "CC_PI0", "NUE_CC", "NUMU_CC", "OUTSIDE_TPC_NU", "COSMIC_OR_UNMATCHED", "other"]
BKG_COL = {"signal": "#000000", "NC_PI0": "#D55E00", "CC_PI0": "#E69F00", "NUE_CC": "#0072B2", "NUMU_CC": "#56B4E9", "OUTSIDE_TPC_NU": "#999999", "COSMIC_OR_UNMATCHED": "#CC79A7", "other": "#009E73"}
PAIR_COL = {"decay_pair": "#009E73", "fsi_or_other_primary": "#0072B2", "secondary_proton": "#E69F00", "fake_or_other": "#D55E00", "photon_wrong": "#999999"}
PAIR_LAB = {"decay_pair": "reco proton = Delta+ decay proton", "fsi_or_other_primary": "FSI-created / other signal primary", "secondary_proton": "Geant4 secondary proton", "fake_or_other": "fake / non-proton / other", "photon_wrong": "photon not the signal photon"}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def cp(k, n):
    return X.binom_ci(int(k), int(n)) if n else (np.nan,) * 3


def savefig(fig, name):
    PS.annotate(fig, PROV, extra=PS.PRELIM); fig.savefig(PLD / name, bbox_inches="tight"); plt.close(fig)


def wr(df, name, outside=None):
    df.to_csv(SUMD / name, index=False)
    if outside:
        df.to_csv(OUT / outside / name, index=False)
    return df


# ======================================================================================================================= load
def load():
    T = pd.read_parquet(SPD / "spine_harmonization" / "official_ncdelta" / "event_flags_and_table.parquet"); T = T[T.tpc_box & T.file_index.notna()].copy(); T["file_index"] = T.file_index.astype(int)
    tag = pd.read_parquet(RAW / "tag.parquet"); kine = pd.read_parquet(RAW / "kine.parquet"); pf = pd.read_parquet(RAW / "pf.parquet")
    for d in (tag, kine, pf):
        d["file_index"] = d.file_index.astype(int); d["ev"] = d.ev.astype(int); d["cand"] = d.cand.astype(int)
    kine["row"] = kine.row.astype(int)
    rm = pd.read_parquet(P10 / "row_matches.parquet"); tpp = pd.read_parquet(P10 / "truth_protons.parquet")
    gen = pd.read_parquet(OUT / "genie_delta_record.parquet")
    # the scan labelled the four components of each GENIE four-vector p, x, y, z (= px, py, pz, E) by a zip over "pxyze": rename to the true meaning (the masses were computed from the arrays and are unaffected)
    gen = gen if "delta_px" in gen.columns else gen.rename(columns={f"{pre}_{a}": f"{pre}_{b}" for pre in ("delta", "nuc", "gam") for a, b in (("p", "px"), ("x", "py"), ("y", "pz"), ("z", "E"))})
    vg = pd.read_parquet(P9 / "vertex_geometry.parquet", columns=K + ["d_vertex", "parallel", "perp", "anchored5", "d_conv_true", "conv_distance_cm", "photon_end_class"])
    bn = pd.read_csv(REPO / "tables" / "background_mechanisms" / "candidate_truth_category.csv")
    return T, tag, kine, pf, rm, tpp, gen, vg, bn


def index_groups(df):
    return {k: g for k, g in df.groupby(KC)}


def build_objects(sample, items, tag, kine, pf, rm_idx, tpp_idx, T_idx, policy_name):
    """One row per selected object (event, candidate) with the photon and the per-proton-policy proton fields.  ``items``: list of (file_index, ev, cand)."""
    tg = tag[tag["sample"] == sample].set_index(KC); kg = {k: g for k, g in kine[kine["sample"] == sample].groupby(KC)}; pg = {k: g for k, g in pf[pf["sample"] == sample].groupby(KC)}
    out = []
    for key in items:
        t = tg.loc[key]; kr = kg.get(key, pd.DataFrame()); pfn = pg.get(key, pd.DataFrame())
        rec = dict(policy=policy_name, sample=sample, file_index=key[0], ev=key[1], cand=key[2], **{c: t[c] for c in tg.columns if c != "sample"})
        vtx = np.array([t.kine_nu_x_corr, t.kine_nu_y_corr, t.kine_nu_z_corr], float); rec["vtx_x"], rec["vtx_y"], rec["vtx_z"] = vtx
        ph = OB.select_photon_row(kr, t.shw_sp_energy, t.shw_sp_filled) if len(kr) else None
        rec["photon_row"] = int(ph.row) if ph is not None else -1; rec["photon_row_found"] = ph is not None
        pd_dir = np.full(3, np.nan); ps = pe = np.full(3, np.nan); plen = np.nan
        if ph is not None and len(pfn):
            ch = OB.pf_chord(pfn, int(ph.row))
            if ch is not None:
                ps, pe, pd_dir, plen = ch
        rec.update(photon_dir_x=pd_dir[0], photon_dir_y=pd_dir[1], photon_dir_z=pd_dir[2], photon_start_x=ps[0], photon_start_y=ps[1], photon_start_z=ps[2], photon_end_x=pe[0], photon_end_y=pe[1], photon_end_z=pe[2], photon_chord_cm=plen)
        # alternative photon direction: reco vertex -> shower start (diagnostic; defined only for a detached shower)
        alt = OB.unit(ps - vtx) if (np.isfinite(ps).all() and np.linalg.norm(ps - vtx) > 1.0) else np.full(3, np.nan)
        rec.update(photon_dir_vtx_x=alt[0], photon_dir_vtx_y=alt[1], photon_dir_vtx_z=alt[2])
        rec["photon_ke"] = float(ph.kine_energy_particle) if ph is not None else np.nan
        if sample == "signal":
            r0 = rm_idx.get(key + (rec["photon_row"],)) if ph is not None else None
            rec["photon_correct"] = bool(r0 is not None and r0["p1_t_pdg"] == 22 and r0["p1_t_nu"] == r0["sig_nu"] and r0["nmatch"] > 0)
            rec["photon_iou_n"] = float(r0["p1_iou_n"]) if r0 is not None else np.nan; rec["photon_origin"] = r0["origin"] if r0 is not None else "none"
        # proton fields per policy
        for v, pol in OB.PROTON_POLICIES.items():
            prs = OB.proton_rows(kr, pol) if len(kr) else kr; lead = OB.leading_proton_row(prs) if len(prs) else None
            rec[f"{v}__n_p"] = len(prs); rec[f"{v}__channel"] = OB.reco_channel(len(prs))
            rec[f"{v}__lead_row"] = int(lead.row) if lead is not None else -1; rec[f"{v}__lead_ke"] = float(lead.kine_energy_particle) if lead is not None else np.nan
            rec[f"{v}__lead_inc3"] = bool(lead.kine_energy_included == 3) if lead is not None else False; rec[f"{v}__lead_is_shower"] = bool(lead.kine_particle_is_shower == 1) if lead is not None else False
            dd = np.full(3, np.nan); L = np.nan
            if lead is not None and len(pfn):
                ch = OB.pf_chord(pfn, int(lead.row))
                if ch is not None:
                    dd, L = ch[2], ch[3]
            rec.update({f"{v}__dir_x": dd[0], f"{v}__dir_y": dd[1], f"{v}__dir_z": dd[2], f"{v}__chord_cm": L})
            if sample == "signal":
                r1 = rm_idx.get(key + (rec[f"{v}__lead_row"],)) if lead is not None else None
                rec[f"{v}__truth_class"] = r1["origin"] if r1 is not None else ("absent" if lead is None else "none")
                rec[f"{v}__tid"] = int(r1["p1_tid"]) if (r1 is not None and r1["p1_tid"] == r1["p1_tid"]) else -1
                tt = tpp_idx.get((key[0], key[1], rec[f"{v}__tid"])) if rec[f"{v}__tid"] >= 0 else None
                rec[f"{v}__true_ke"] = float(tt["ke"]) if tt is not None else np.nan; rec[f"{v}__origin_class"] = tt["origin_class"] if tt is not None else ""
                for c, n in (("px", "pf_start_px"), ("py", "pf_start_py"), ("pz", "pf_start_pz")):
                    rec[f"{v}__true_{c}"] = float(tt[n]) if tt is not None else np.nan
            # Delta mass (only for reco 1gamma1p under this policy; the photon and the proton directions are the PF chords)
            cosg = OB.cos_between([rec["photon_dir_x"], rec["photon_dir_y"], rec["photon_dir_z"]], dd)
            rec[f"{v}__cos_gp"] = cosg
            if len(prs) != 1:
                status = "not_1g1p"
            elif ph is None:
                status = "no_photon_row"
            elif not np.isfinite(pd_dir).all():
                status = "no_photon_direction"
            elif not np.isfinite(dd).all():
                status = "no_proton_direction"
            else:
                status = "ok"
            m, ok = OB.delta_mass(rec["photon_ke"], rec[f"{v}__lead_ke"], cosg) if status == "ok" else (np.nan, np.array(False))
            if status == "ok" and not bool(ok):
                status = "mass2_nonpositive"
            rec[f"{v}__mass_status"] = status; rec[f"{v}__m_delta"] = float(m) if status == "ok" else np.nan
        out.append(rec)
    return pd.DataFrame(out)


def make_indexes(T, rm, tpp):
    keep = rm.merge(T[K].drop_duplicates(), on=K)
    cols = ["file_index", "ev", "cand", "row", "p1_t_pdg", "p1_t_nu", "sig_nu", "nmatch", "p1_iou_n", "origin", "p1_tid"]
    rm_idx = {(r[0], r[1], r[2], r[3]): dict(zip(cols[4:], r[4:])) for r in keep[cols].itertuples(index=False, name=None)}
    t2 = tpp[["file_index", "ev", "trackid", "ke", "origin_class", "pf_start_px", "pf_start_py", "pf_start_pz"]]
    tpp_idx = {(r[0], r[1], r[2]): dict(ke=r[3], origin_class=r[4], pf_start_px=r[5], pf_start_py=r[6], pf_start_pz=r[7]) for r in t2.itertuples(index=False, name=None)}
    return rm_idx, tpp_idx


# ======================================================================================================================= signal assembly with truth
M_P = OB.M_PROTON_MEV


def assemble_signal(O, T, gen, vg):
    keep = K + ["run", "subrun", "evt", "photon_energy_mev", "photon_px", "photon_py", "photon_pz", "nu_energy_gev", "vtx_x", "vtx_y", "vtx_z", "truth35", "delta_label", "cos_theta_beam", "delta_pdg", "n_p50"]
    Tc = T[keep].rename(columns=dict(vtx_x="true_vtx_x", vtx_y="true_vtx_y", vtx_z="true_vtx_z", photon_energy_mev="true_photon_e", nu_energy_gev="true_enu_gev"))
    g = gen[["run", "subrun", "evt", "m_decay", "m_delta_record", "nuc_pdg", "gam_E", "nuc_E"]].rename(columns=dict(m_decay="m_true_decay_gev", m_delta_record="m_delta_record_gev"))
    S = O.merge(Tc, on=K, how="left", validate="m:1").merge(g, on=["run", "subrun", "evt"], how="left").merge(vg, on=K, how="left")
    tp = S[["photon_px", "photon_py", "photon_pz"]].to_numpy(float); S["true_photon_dir_x"], S["true_photon_dir_y"], S["true_photon_dir_z"] = (tp / np.linalg.norm(tp, axis=1, keepdims=True)).T
    S["m_true_decay"] = S.m_true_decay_gev * 1000.0
    S["cos_photon_chord_true"] = [OB.cos_between(a, b) for a, b in zip(S[["photon_dir_x", "photon_dir_y", "photon_dir_z"]].to_numpy(float), S[["true_photon_dir_x", "true_photon_dir_y", "true_photon_dir_z"]].to_numpy(float))]
    S["cos_photon_vtxdir_true"] = [OB.cos_between(a, b) for a, b in zip(S[["photon_dir_vtx_x", "photon_dir_vtx_y", "photon_dir_vtx_z"]].to_numpy(float), S[["true_photon_dir_x", "true_photon_dir_y", "true_photon_dir_z"]].to_numpy(float))]
    S["attached"] = S.shw_sp_shw_vtx_dis == 0
    for v in PV:
        S[f"{v}__pair_class"] = [OB.pair_class(bool(pc), tc, tc, int(dp), oc) for pc, tc, dp, oc in zip(S.photon_correct, S[f"{v}__truth_class"], S.delta_pdg, S[f"{v}__origin_class"])]
        # final-state truth mass B: signal photon + the matched post-FSI primary proton (momentum from T_truth_pf, E = T + m)
        pp = S[[f"{v}__true_px", f"{v}__true_py", f"{v}__true_pz"]].to_numpy(float) * 1000.0; ep = S[f"{v}__true_ke"].to_numpy(float) + M_P
        pg = tp * 1000.0; eg = np.linalg.norm(pg, axis=1)
        s = np.column_stack([pp + pg, ep + eg]); m2 = s[:, 3] ** 2 - (s[:, :3] ** 2).sum(1)
        okB = (S[f"{v}__truth_class"] == "true_primary_signal_proton").to_numpy() & np.isfinite(m2) & (m2 > 0)
        S[f"{v}__m_finalstate_truth"] = np.where(okB, np.sqrt(np.where(okB, m2, 1.0)), np.nan)
        S[f"{v}__cos_gp_true"] = [OB.cos_between(a, b) / 1 if np.isfinite(a).all() and np.isfinite(b).all() else np.nan for a, b in zip(S[["true_photon_dir_x", "true_photon_dir_y", "true_photon_dir_z"]].to_numpy(float), OB_unit_rows(pp))]
        S[f"{v}__cos_proton_true"] = [OB.cos_between(a, b) for a, b in zip(S[[f"{v}__dir_x", f"{v}__dir_y", f"{v}__dir_z"]].to_numpy(float), OB_unit_rows(pp))]
    return S


def OB_unit_rows(a):
    return np.array([OB.unit(x) for x in a]) if len(a) else np.zeros((0, 3))


# ======================================================================================================================= Delta-mass: generator-level validation (Task 4), signal M_Delta (5), resolution (6)
def generator_level_block(T, gen, S):
    g = gen.merge(T[["run", "subrun", "evt", "delta_label", "truth35", "A_final"]], on=["run", "subrun", "evt"], how="inner")
    recs = []
    for lab, d in [("all", g)] + [(x, y) for x, y in g.groupby("delta_label")] + [("final_selected_any", g[g.A_final.astype(bool)])]:
        m = d.m_decay.dropna() * 1000
        h, e = np.histogram(m, bins=np.arange(1080, 1800, 5)); mode = 0.5 * (e[np.argmax(h)] + e[np.argmax(h) + 1]); half = h.max() / 2; above = np.where(h >= half)[0]
        recs.append(dict(sample=lab, n=len(d), n_with_decay_pair=int(m.size), median_mev=float(m.median()), mean_mev=float(m.mean()), p16=float(np.percentile(m, 16)), p84=float(np.percentile(m, 84)), mode_mev=float(mode),
                         fwhm_lo=float(e[above[0]]), fwhm_hi=float(e[above[-1] + 1]), min_mev=float(m.min()), max_mev=float(m.max()), delta_record_equals_decay_pair=float(np.mean(np.abs(d.m_delta_record - d.m_decay).dropna() < 1e-3))))
    G = wr(pd.DataFrame(recs), "generator_delta_decay_mass.csv", "resolution_tables")
    # decay-nucleon identity per Delta charge
    nuc = g.groupby(["delta_label", "nuc_pdg"]).size().rename("n").reset_index(); wr(nuc, "generator_decay_nucleon_by_delta_charge.csv")
    SUMMARY["generator"] = dict(rows=G.to_dict("records"), decay_nucleon=nuc.to_dict("records"))
    return g


def breit_wigner_check(g):
    """Descriptive comparison of the generator decay-pair mass with the nominal relativistic Breit-Wigner of the Delta(1232) (M = 1232, Gamma = 117 MeV; nominal PDG values, NOT fitted)."""
    m = g.m_decay.dropna().to_numpy() * 1000
    edges = np.arange(1100, 1600, 10.0); h, _ = np.histogram(m, bins=edges); c = 0.5 * (edges[1:] + edges[:-1])
    bw = lambda x, M=1232.0, G=117.0: 1.0 / ((x ** 2 - M ** 2) ** 2 + (M * G) ** 2)
    ref = bw(c); ref = ref / ref.sum() * h.sum()
    return pd.DataFrame(dict(m_lo=edges[:-1], m_hi=edges[1:], n=h, bw_nominal_scaled=ref))


MBINS = np.arange(900, 2550, 50.0)


def mass_distribution_block(S, v="baseline_35"):
    d = S[S[f"{v}__mass_status"] == "ok"].copy(); d["m"] = d[f"{v}__m_delta"]; d["pair"] = d[f"{v}__pair_class"]; d["both_correct"] = d.photon_correct & (d[f"{v}__truth_class"] == "true_primary_signal_proton")
    d["topo"] = d.truth35.map(TL)
    recs = []
    def add(name, g):
        if len(g) == 0:
            return
        h, _ = np.histogram(g.m, bins=MBINS); mode = 0.5 * (MBINS[np.argmax(h)] + MBINS[np.argmax(h) + 1]); q = np.percentile(g.m, [16, 50, 84])
        recs.append(dict(subset=name, n=len(g), median_mev=q[1], p16=q[0], p84=q[2], mode_mev=mode, frac_below_1100=float((g.m < 1100).mean()), frac_1100_1400=float(((g.m >= 1100) & (g.m < 1400)).mean()), frac_above_1400=float((g.m >= 1400).mean())))
    add("all selected reco 1g1p", d); add("photon and proton truth-correct", d[d.both_correct])
    for c in OB.PAIR_CLASSES:
        add("pair: " + c, d[d.pair == c])
    for t, g in d.groupby("topo"):
        add(t, g)
    for t, g in d.groupby("delta_label"):
        add(t, g)
    for t, g in d[d.both_correct].groupby("delta_label"):
        add("truth-correct, " + t, g)
    M = wr(pd.DataFrame(recs), "delta_mass_signal_subsets.csv", "resolution_tables")
    wr(pd.crosstab(d.pair, d.delta_label).reset_index(), "delta_mass_pair_class_by_delta_charge.csv"); SUMMARY["delta_mass_signal"] = M.to_dict("records")
    return d, M


def mass_figure(d):
    fig, ax = PS.figure(1, 3, size=(17, 4.6)); c = 0.5 * (MBINS[1:] + MBINS[:-1])
    a = ax[0][0]; bottom = np.zeros(len(c))
    for k in OB.PAIR_CLASSES[::-1][::-1]:
        h, _ = np.histogram(d[d.pair == k].m, bins=MBINS); a.bar(c, h, width=50, bottom=bottom, color=PAIR_COL[k], edgecolor="k", linewidth=0.2, label=f"{PAIR_LAB[k]} ({int((d.pair == k).sum())})"); bottom += h
    a.axvline(1232, color="k", ls=":", lw=0.8); a.set_xlabel("reconstructed M_Delta [MeV] (reco 1gamma1p, final selected)"); a.set_ylabel("events / 50 MeV"); a.legend(fontsize=6.5); a.set_title(f"all selected reco 1g1p signal, n = {len(d)} (dotted: 1232 MeV)", fontsize=9)
    a = ax[0][1]
    for t, col in (("truth 0p", "#0072B2"), ("truth 1p", "#D55E00"), ("truth >=2p", "#009E73")):
        g = d[d.topo == t]; h, _ = np.histogram(g.m, bins=MBINS); a.step(c, h, where="mid", color=col, label=f"{t} ({len(g)})")
    g = d[d.both_correct]; h, _ = np.histogram(g.m, bins=MBINS); a.step(c, h, where="mid", color="k", ls="--", label=f"photon and proton truth-correct ({len(g)})"); a.axvline(1232, color="k", ls=":", lw=0.8)
    a.set_xlabel("reconstructed M_Delta [MeV]"); a.legend(fontsize=7); a.set_title("by truth proton topology", fontsize=9)
    a = ax[0][2]
    for t, col in (("Delta0", "#CC79A7"), ("Delta+", "#56B4E9")):
        g = d[d.delta_label == t]; h, _ = np.histogram(g.m, bins=MBINS); a.step(c, h / max(h.sum(), 1), where="mid", color=col, label=f"{t} all ({len(g)})")
        g = d[(d.delta_label == t) & d.both_correct]; h, _ = np.histogram(g.m, bins=MBINS); a.step(c, h / max(h.sum(), 1), where="mid", color=col, ls="--", label=f"{t} truth-correct ({len(g)})")
    a.axvline(1232, color="k", ls=":", lw=0.8); a.set_xlabel("reconstructed M_Delta [MeV]"); a.set_ylabel("unit area"); a.legend(fontsize=7); a.set_title("by Delta charge (the reco proton is NOT the decay nucleon for Delta0)", fontsize=9)
    savefig(fig, "delta_mass_signal_decomposition.png")


def resolution_block(S, v="baseline_35"):
    d = S[(S[f"{v}__mass_status"] == "ok") & (S[f"{v}__pair_class"] == "decay_pair")].copy(); d["m"] = d[f"{v}__m_delta"]; d["mB"] = d[f"{v}__m_finalstate_truth"]; d["m0"] = d.m_true_decay
    pairs = {"M_reco - M_true_decay": d.m - d.m0, "M_finalstate_truth - M_true_decay (FSI effect)": d.mB - d.m0, "M_reco - M_finalstate_truth (reconstruction effect)": d.m - d.mB}
    recs = []
    for k, x in pairs.items():
        recs.append(dict(quantity=k, **OB.resolution_stats(x), relative_median=float(np.nanmedian(x / d.m0)) if k.startswith("M_reco - M_true") else np.nan))
    R = wr(pd.DataFrame(recs), "delta_mass_resolution_decay_pairs.csv", "resolution_tables")
    # substitution study: one reco ingredient replaced by its truth value; residual vs the final-state truth mass
    eg_t = d.true_photon_e.to_numpy(float); ke_t = d[f"{v}__true_ke"].to_numpy(float); ke_r = d[f"{v}__lead_ke"].to_numpy(float); eg_r = d.photon_ke.to_numpy(float)
    gd_r = d[["photon_dir_x", "photon_dir_y", "photon_dir_z"]].to_numpy(float); gd_t = d[["true_photon_dir_x", "true_photon_dir_y", "true_photon_dir_z"]].to_numpy(float)
    pd_r = d[[f"{v}__dir_x", f"{v}__dir_y", f"{v}__dir_z"]].to_numpy(float); pd_t = OB_unit_rows(d[[f"{v}__true_px", f"{v}__true_py", f"{v}__true_pz"]].to_numpy(float))
    cs = lambda a, b: np.array([OB.cos_between(x, y) for x, y in zip(a, b)])
    gd_v = d[["photon_dir_vtx_x", "photon_dir_vtx_y", "photon_dir_vtx_z"]].to_numpy(float); gd_alt = np.where(np.isfinite(gd_v).all(axis=1, keepdims=True), gd_v, gd_r)
    cases = {"all reco (baseline)": (eg_r, ke_r, cs(gd_r, pd_r)), "ALTERNATIVE photon direction: vertex->shower start when detached (reco only)": (eg_r, ke_r, cs(gd_alt, pd_r)), "E_gamma true": (eg_t, ke_r, cs(gd_r, pd_r)), "proton KE true": (eg_r, ke_t, cs(gd_r, pd_r)), "photon direction true": (eg_r, ke_r, cs(gd_t, pd_r)),
             "proton direction true": (eg_r, ke_r, cs(gd_r, pd_t)), "opening angle true (both directions)": (eg_r, ke_r, cs(gd_t, pd_t)), "photon energy and opening angle true": (eg_t, ke_r, cs(gd_t, pd_t)), "all ingredients true": (eg_t, ke_t, cs(gd_t, pd_t))}
    rs = []
    for k, (e, ke, c) in cases.items():
        m, ok = OB.delta_mass(e, ke, c); r = OB.resolution_stats(np.where(ok, m - d.mB.to_numpy(float), np.nan)); rs.append(dict(replaced_by_truth=k, n_valid=int(ok.sum()), median_resid=r["median"], half68=r["half68"], p16=r["p16"], p84=r["p84"], rms=r["rms"], tail3=r["tail3"]))
    Sub = wr(pd.DataFrame(rs), "delta_mass_substitution_study.csv", "resolution_tables")
    # component residuals
    cres = pd.DataFrame(dict(e_gamma_frac=(eg_r - eg_t) / eg_t, proton_ke_frac=(ke_r - ke_t) / ke_t, cos_photon=cs(gd_r, gd_t), cos_proton=cs(pd_r, pd_t), cos_gp_reco=cs(gd_r, pd_r), cos_gp_true=cs(gd_t, pd_t)))
    cres["dcos_gp"] = cres.cos_gp_reco - cres.cos_gp_true
    comp = pd.DataFrame([dict(component=c, **OB.resolution_stats(cres[c])) for c in cres.columns]); wr(comp, "delta_mass_component_residuals.csv", "resolution_tables")
    SUMMARY["delta_mass_resolution"] = dict(rows=R.to_dict("records"), substitution=Sub.to_dict("records"), n_decay_pairs=len(d)); return d, R, Sub, cres


def resolution_figure(d, Sub):
    fig, ax = PS.figure(1, 3, size=(17, 4.6)); bins = np.arange(-600, 601, 25)
    a = ax[0][0]
    for x, col, lab in ((d.m - d.m0, "#000000", "M_reco - M_true_decay"), (d.mB - d.m0, "#0072B2", "final-state truth - M_true_decay (FSI)"), (d.m - d.mB, "#D55E00", "M_reco - final-state truth (reconstruction)")):
        a.hist(np.clip(x, -599, 599), bins=bins, histtype="step", color=col, label=f"{lab}: med {np.nanmedian(x):+.0f}, 68% half {(np.nanpercentile(x,84)-np.nanpercentile(x,16))/2:.0f} MeV")
    a.set_xlabel("mass residual [MeV] (Delta+ decay pairs, truth-correct)"); a.set_ylabel("events"); a.legend(fontsize=6.5); a.set_title(f"n = {len(d)} decay pairs", fontsize=9)
    a = ax[0][1]; a.hist2d(d.m0, d.m.clip(upper=2000), bins=[np.arange(1100, 1500, 20), np.arange(900, 2050, 50)], cmap="viridis", cmin=1); a.plot([1100, 1500], [1100, 1500], "w--", lw=0.8); a.set_xlabel("M_true_decay [MeV]"); a.set_ylabel("M_reco [MeV]"); a.set_title("dashed: y = x", fontsize=9)
    a = ax[0][2]; y = np.arange(len(Sub)); a.barh(y, Sub.half68, color="#0072B2"); a.set_yticks(y); a.set_yticklabels([x.replace("ALTERNATIVE photon direction: vertex->shower start when detached (reco only)", "alt. photon dir (vertex->start, reco)") for x in Sub.replaced_by_truth], fontsize=7); a.invert_yaxis(); a.set_xlabel("68 % half-width of (M - M_finalstate_truth) [MeV]"); a.set_title("one ingredient replaced by truth (non-additive)", fontsize=9)
    savefig(fig, "delta_mass_resolution.png")


# ======================================================================================================================= photon energy (9), direction (10), gap (11)
def _bin(s, edges):
    return pd.cut(s, edges, right=False)


def photon_energy_block(S):
    d = S[S.photon_correct & S.photon_row_found].copy(); d["ratio"] = d.shw_sp_energy / d.true_photon_e; d["resid"] = d.ratio - 1
    d["e_bin"] = _bin(d.true_photon_e, [20, 100, 200, 300, 500, 800, 5000]); d["conv_bin"] = _bin(d.conv_distance_cm.where(d.photon_end_class == "conv"), [0, 5, 10, 20, 40, 80, 300])
    d["topo"] = d.truth35.map(TL); d["state"] = np.where(d.attached, "attached", "detached")
    recs = []
    for by in ("e_bin", "conv_bin", "topo", "state", "delta_label"):
        for b, g in d.groupby(by, observed=True):
            recs.append(dict(split=by, bin=str(b), **OB.resolution_stats(g.ratio)))
    recs.insert(0, dict(split="all", bin="all", **OB.resolution_stats(d.ratio)))
    R = wr(pd.DataFrame(recs), "photon_energy_response.csv", "resolution_tables")
    SUMMARY["photon_energy"] = dict(n=len(d), all=R.iloc[0].to_dict(), excluded_photon_not_signal=int((~S.photon_correct).sum()), excluded_no_row=int((~S.photon_row_found).sum())); return d, R


def photon_energy_figure(d, R):
    fig, ax = PS.figure(1, 3, size=(16, 4.6)); a = ax[0][0]
    a.hist2d(d.true_photon_e, d.shw_sp_energy, bins=[np.logspace(np.log10(20), np.log10(2500), 40)] * 2, cmap="viridis", cmin=1); a.set_xscale("log"); a.set_yscale("log"); a.plot([20, 2500], [20, 2500], "w--", lw=0.8)
    a.set_xlabel("true photon energy [MeV]"); a.set_ylabel("selected shower energy `shw_sp_energy` [MeV]"); a.set_title(f"truth-associated selected photons (n = {len(d)})", fontsize=9)
    a = ax[0][1]; edges = [20, 100, 200, 300, 500, 800, 5000]; x = np.arange(len(edges) - 1)
    for lab, mask, col in (("all", d.index == d.index, "k"), ("attached", d.attached, "#0072B2"), ("detached", ~d.attached, "#D55E00")):
        g = d[mask]; med = []; lo = []; hi = []
        for i in range(len(edges) - 1):
            r = g[(g.true_photon_e >= edges[i]) & (g.true_photon_e < edges[i + 1])].ratio; q = np.percentile(r, [16, 50, 84]) if len(r) >= 5 else [np.nan] * 3; lo.append(q[0]); med.append(q[1]); hi.append(q[2])
        a.errorbar(x + 0.07 * ["all", "attached", "detached"].index(lab), med, yerr=[np.array(med) - np.array(lo), np.array(hi) - np.array(med)], fmt="o-", color=col, ms=4, lw=1, label=lab)
    a.axhline(1, color="k", ls=":", lw=0.7); a.set_xticks(x); a.set_xticklabels([f"{edges[i]}-{edges[i+1]}" for i in x], fontsize=7); a.set_xlabel("true photon energy bin [MeV]"); a.set_ylabel("E_reco / E_true (median, 16-84 %)"); a.legend(fontsize=7); a.set_ylim(0, 1.6)
    a = ax[0][2]; bins = np.linspace(0, 2, 61)
    for t, col in (("truth 0p", "#0072B2"), ("truth 1p", "#D55E00"), ("truth >=2p", "#009E73")):
        g = d[d.topo == t].ratio; a.hist(g.clip(upper=1.99), bins=bins, histtype="step", density=True, color=col, label=f"{t} (n={len(g)}, med {g.median():.2f})")
    a.set_xlabel("E_reco / E_true"); a.set_ylabel("unit area"); a.legend(fontsize=7); savefig(fig, "photon_energy_response.png")


def photon_direction_block(S):
    d = S[S.photon_correct & S.photon_row_found & S.cos_photon_chord_true.notna()].copy(); d["e_bin"] = _bin(d.true_photon_e, [20, 100, 200, 300, 500, 800, 5000]); d["conv_bin"] = _bin(d.conv_distance_cm.where(d.photon_end_class == "conv"), [0, 5, 10, 20, 40, 80, 300])
    d["topo"] = d.truth35.map(TL); d["state"] = np.where(d.attached, "attached", "detached"); d["chord_bin"] = _bin(d.photon_chord_cm, [0, 10, 25, 50, 100, 300])
    d["ang"] = np.degrees(np.arccos(d.cos_photon_chord_true.clip(-1, 1))); recs = []
    for by in ("e_bin", "conv_bin", "topo", "state", "chord_bin"):
        for b, g in d.groupby(by, observed=True):
            recs.append(dict(split=by, bin=str(b), n=len(g), median_cos=g.cos_photon_chord_true.median(), median_angle_deg=g.ang.median(), p68_angle_deg=np.percentile(g.ang, 68), frac_cos_gt0p9=float((g.cos_photon_chord_true > 0.9).mean()), frac_cos_lt0=float((g.cos_photon_chord_true < 0).mean())))
    recs.insert(0, dict(split="all", bin="all", n=len(d), median_cos=d.cos_photon_chord_true.median(), median_angle_deg=d.ang.median(), p68_angle_deg=np.percentile(d.ang, 68), frac_cos_gt0p9=float((d.cos_photon_chord_true > 0.9).mean()), frac_cos_lt0=float((d.cos_photon_chord_true < 0).mean())))
    R = wr(pd.DataFrame(recs), "photon_direction_resolution.csv", "resolution_tables")
    # alternative direction: reco vertex -> shower start, defined for detached showers (gap > 1 cm) only
    v = d[d.cos_photon_vtxdir_true.notna()]; alt = dict(n=len(v), chord_median_cos=float(v.cos_photon_chord_true.median()), vertex_to_start_median_cos=float(v.cos_photon_vtxdir_true.median()),
                                                        chord_frac_gt0p9=float((v.cos_photon_chord_true > 0.9).mean()), vertex_to_start_frac_gt0p9=float((v.cos_photon_vtxdir_true > 0.9).mean()), vertex_to_start_frac_lt0=float((v.cos_photon_vtxdir_true < 0).mean()))
    # the official stored direction quantity: angle to the beam (deg) of shower_cal_dir_3vector (15 cm) vs the true angle to the beam
    tb = np.degrees(np.arccos(d.true_photon_dir_z.clip(-1, 1))); br = d.shw_sp_angle_beam - tb
    beam = dict(n=len(d), **{"resid_" + k: v2 for k, v2 in OB.resolution_stats(br).items()})
    patho = d[d.cos_photon_chord_true < 0]; pat = dict(n=len(patho), chord_median_cm=float(patho.photon_chord_cm.median()) if len(patho) else np.nan, attached_frac=float(patho.attached.mean()) if len(patho) else np.nan, energy_median=float(patho.true_photon_e.median()) if len(patho) else np.nan)
    SUMMARY["photon_direction"] = dict(all=R.iloc[0].to_dict(), alternative_vertex_to_start=alt, angle_beam_check=beam, negative_cos_cases=pat); return d, R


def gap_block(S):
    d = S[S.photon_correct & S.photon_row_found & (S.photon_end_class == "conv")].copy(); d["gap"] = d.shw_sp_shw_vtx_dis; d["topo"] = d.truth35.map(TL); d["anch"] = np.where(d.anchored5 == True, "anchored", "not anchored")
    d["true_p"] = np.where(d["baseline_35__truth_class"] == "true_primary_signal_proton", "true proton row present", "true proton row absent")
    recs = []
    for by in ("all", "topo", "anch", "true_p"):
        for b, g in ([("all", d)] if by == "all" else d.groupby(by)):
            det = g[g.gap > 0]
            rho = stats.spearmanr(det.gap, det.conv_distance_cm).statistic if len(det) > 10 else np.nan
            recs.append(dict(split=by, value=b, n=len(g), frac_attached=float((g.gap == 0).mean()), median_gap_cm=float(g.gap.median()), median_conv_cm=float(g.conv_distance_cm.median()), median_gap_detached=float(det.gap.median()) if len(det) else np.nan,
                             median_gap_minus_conv_detached=float((det.gap - det.conv_distance_cm).median()) if len(det) else np.nan, spearman_gap_conv_detached=rho, n_detached=len(det)))
    for (t, a_), g in d.groupby(["topo", "anch"]):
        det = g[g.gap > 0]; recs.append(dict(split="topo x anchored", value=f"{t} | {a_}", n=len(g), frac_attached=float((g.gap == 0).mean()), median_gap_cm=float(g.gap.median()), median_conv_cm=float(g.conv_distance_cm.median()), median_gap_detached=float(det.gap.median()) if len(det) else np.nan,
                                           median_gap_minus_conv_detached=float((det.gap - det.conv_distance_cm).median()) if len(det) else np.nan, spearman_gap_conv_detached=stats.spearmanr(det.gap, det.conv_distance_cm).statistic if len(det) > 10 else np.nan, n_detached=len(det)))
    R = wr(pd.DataFrame(recs), "shower_gap_vs_conversion_distance.csv", "resolution_tables"); SUMMARY["gap"] = R.to_dict("records"); return d, R


def gap_figure(d):
    fig, ax = PS.figure(1, 3, size=(16, 4.6)); lim = 100
    for a, an in zip(ax[0][:2], ("anchored", "not anchored")):
        g = d[d.anch == an]
        for t, col in (("truth 0p", "#0072B2"), ("truth 1p", "#D55E00"), ("truth >=2p", "#009E73")):
            h = g[g.topo == t]; a.scatter(h.conv_distance_cm, h.gap, s=6, alpha=0.5, color=col, label=f"{t} (n={len(h)})")
        a.plot([0, lim], [0, lim], "k:", lw=0.8); a.set_xlim(0, lim); a.set_ylim(-3, 120); a.set_xlabel("true conversion distance [cm]"); a.set_ylabel("`shw_sp_shw_vtx_dis` [cm] (0 = attached)"); a.set_title(f"vertex {an} (|V_reco - V_true| {'<=' if an == 'anchored' else '>'} 5 cm)", fontsize=9); a.legend(fontsize=6.5)
    a = ax[0][2]; edges = [0, 5, 10, 20, 40, 80, 300]; x = np.arange(len(edges) - 1)
    for lab, mask, col in (("anchored", d.anch == "anchored", "#0072B2"), ("not anchored", d.anch != "anchored", "#D55E00"), ("true proton row present", d.true_p == "true proton row present", "#009E73"), ("true proton row absent", d.true_p != "true proton row present", "#999999")):
        g = d[mask]; fr = []; 
        for i in range(len(edges) - 1):
            h = g[(g.conv_distance_cm >= edges[i]) & (g.conv_distance_cm < edges[i + 1])]; fr.append((h.gap == 0).mean() if len(h) >= 8 else np.nan)
        a.plot(x, fr, "o-", color=col, label=lab, ms=4, lw=1)
    a.set_xticks(x); a.set_xticklabels([f"{edges[i]}-{edges[i+1]}" for i in x], fontsize=7); a.set_xlabel("true conversion distance bin [cm]"); a.set_ylabel("fraction of showers attached (gap = 0)"); a.legend(fontsize=7); a.set_ylim(0, 1)
    savefig(fig, "shower_gap_vs_conversion_distance.png")


# ======================================================================================================================= BNB selected objects, shape comparisons, proton kinematics, Enu, vertex
GROUP_OF = {"NC_PI0": "NC_PI0", "CC_PI0": "CC_PI0", "NUE_CC": "NUE_CC", "NUMU_CC": "NUMU_CC", "OUTSIDE_TPC_NU": "OUTSIDE_TPC_NU", "COSMIC_OR_UNMATCHED": "COSMIC_OR_UNMATCHED", "OTHER_NC": "other", "MULTI_OR_AMBIGUOUS": "other", "OTHER_CC": "other"}


def assemble_bnb(B, bn):
    b = B.merge(bn[["file_index", "ev", "nu_index", "event_class", "reco_channel", "cand_category"]].rename(columns=dict(nu_index="cand")), on=KC, how="left", validate="1:1")
    b["group"] = np.where(b.event_class == "signal_like", "natural_signal_like", b.cand_category.map(GROUP_OF)); assert b.group.notna().all()
    assert ((b["baseline_35__channel"].map({"1g0p": "1g0p", "1g1p": "1g1p", "1gNp": "ge2p_diag"})) == b.reco_channel).all(), "BNB baseline channel not reproduced by the rows"
    return b


OBS = {   # name: (column, label, range, nbins, channels)
    "e_gamma": ("photon_ke", "selected shower energy E_gamma [MeV]", (0, 1500), 30), "gap": ("shw_sp_shw_vtx_dis", "shower-to-vertex gap `shw_sp_shw_vtx_dis` [cm]", (0, 100), 25),
    "dedx": ("shw_sp_vec_median_dedx", "shower-start median dE/dx `shw_sp_vec_median_dedx` [MeV/cm]", (0, 8), 32), "dqdx0": ("shw_sp_vec_dQ_dx_0", "first stem dQ/dx / MIP (`shw_sp_vec_dQ_dx_0`)", (0, 4), 32),
    "enu": ("kine_reco_Enu", "`kine_reco_Enu` [MeV]", (0, 3000), 30), "vx": ("vtx_x", "reco vertex x [cm]", (-220, 220), 22), "vy": ("vtx_y", "reco vertex y [cm]", (-220, 220), 22), "vz": ("vtx_z", "reco vertex z [cm]", (-20, 520), 27),
    "m_delta": ("baseline_35__m_delta", "reconstructed M_Delta [MeV]", (900, 2500), 32), "cos_gp": ("baseline_35__cos_gp", "cos(theta_gamma,p)", (-1, 1), 20), "p_ke": ("baseline_35__lead_ke", "reco proton KE [MeV]", (0, 800), 32),
}


def shape_table(frames: dict, obs_names, channel):
    recs = []
    for name in obs_names:
        col = OBS[name][0]
        for g, f in frames.items():
            x = f[f.baseline_35__channel == channel][col].dropna() if channel else f[col].dropna()
            if len(x):
                q = np.percentile(x, [16, 50, 84]); recs.append(dict(observable=name, channel=channel, group=g, n=len(x), median=q[1], p16=q[0], p84=q[2]))
    return pd.DataFrame(recs)


def shape_panels(frames: dict, obs_names, channel, fname, ncols=3, colors=None, title=None, size=None):
    n = len(obs_names); nrows = int(np.ceil(n / ncols)); fig, ax = PS.figure(nrows, ncols, size=size or (5.2 * ncols, 3.9 * nrows)); colors = colors or BKG_COL
    for i, name in enumerate(obs_names):
        a = ax[i // ncols][i % ncols]; col, lab, rng, nb = OBS[name]; bins = np.linspace(*rng, nb + 1)
        for g, f in frames.items():
            x = f[f.baseline_35__channel == channel][col].dropna() if channel else f[col].dropna()
            if len(x) >= 3:
                a.hist(x.clip(rng[0] + 1e-9, rng[1] - 1e-9), bins=bins, density=True, histtype="step", color=colors.get(g, "#555555"), lw=1.6 if g == "signal" else 1.1, label=f"{g} ({len(x)})")
        a.set_xlabel(lab, fontsize=8); a.set_ylabel("unit area", fontsize=8); a.tick_params(labelsize=7)
        if i == 0:
            a.legend(fontsize=6)
    for j in range(n, nrows * ncols):
        ax[j // ncols][j % ncols].axis("off")
    if title:
        fig.suptitle(title, fontsize=10)
    savefig(fig, fname)


def bkg_frames(S, Bk, channel_col="baseline_35__channel"):
    fr = {"signal": S}
    for g in BKG_ORDER:
        fr[g] = Bk[Bk.group == g]
    return fr


def shapes_block(S, Bk):
    fr = bkg_frames(S, Bk); T = []
    for ch in ("1g0p", "1g1p"):
        T.append(shape_table(fr, list(OBS), ch))
    R = pd.concat(T); wr(R, "signal_vs_background_shape_summary.csv", "background_shapes")
    # counts of selected objects (NOT rates)
    cnt = pd.DataFrame([dict(group=g, **{ch: int((f.baseline_35__channel == ch).sum()) for ch in ("1g0p", "1g1p", "1gNp")}) for g, f in fr.items()]); wr(cnt, "selected_object_counts_not_rates.csv", "background_shapes")
    SUMMARY["shape_counts"] = cnt.to_dict("records")
    sig = {"signal": S}; bk = {g: Bk[Bk.group == g] for g in ("NC_PI0", "CC_PI0", "NUE_CC")}
    dedx_fr = {"signal photon": S, "NC pi0 (selected shower)": bk["NC_PI0"], "CC pi0 (selected shower)": bk["CC_PI0"], "nueCC (selected shower)": bk["NUE_CC"]}
    cols = {"signal photon": "#000000", "NC pi0 (selected shower)": "#D55E00", "CC pi0 (selected shower)": "#E69F00", "nueCC (selected shower)": "#0072B2"}
    fig, ax = PS.figure(2, 2, size=(11, 8)); 
    for j, ch in enumerate(("1g0p", "1g1p")):
        for i, name in enumerate(("dedx", "dqdx0")):
            a = ax[i][j]; col, lab, rng, nb = OBS[name]; bins = np.linspace(*rng, nb + 1)
            for g, f in dedx_fr.items():
                x = f[f.baseline_35__channel == ch][col].dropna()
                if len(x) >= 3:
                    a.hist(x.clip(rng[0] + 1e-9, rng[1] - 1e-9), bins=bins, density=True, histtype="step", color=cols[g], lw=1.6 if g.startswith("signal") else 1.1, label=f"{g} ({len(x)})")
            a.set_xlabel(lab, fontsize=8); a.set_ylabel("unit area", fontsize=8); a.set_title(f"reco {ch.replace('g', 'gamma')}", fontsize=9)
            if i == 0 and j == 0:
                a.legend(fontsize=6.5)
    savefig(fig, "start_dedx_signal_vs_pi0_vs_nue.png")
    return R, cnt


def mass_shape_figures(S, Bk):
    S1 = S[S.baseline_35__mass_status == "ok"]; fr = {"signal": S1}
    for g in BKG_ORDER:
        fr[g] = Bk[(Bk.group == g) & (Bk.baseline_35__mass_status == "ok")]
    fig, ax = PS.figure(1, 2, size=(12, 4.6)); bins = np.linspace(900, 2500, 33)
    for a, ttl, sub in ((ax[0][0], "M_Delta: signal vs selected backgrounds (unit area)", fr), (ax[0][1], "M_Delta: signal split by truth origin of the proton row", None)):
        if sub is not None:
            for g, f in sub.items():
                x = f["baseline_35__m_delta"].dropna()
                if len(x) >= 3:
                    a.hist(x.clip(901, 2499), bins=bins, density=True, histtype="step", color=BKG_COL[g], lw=1.8 if g == "signal" else 1.1, label=f"{g} ({len(x)})")
        else:
            for k in OB.PAIR_CLASSES[:4]:
                x = S1[S1["baseline_35__pair_class"] == k]["baseline_35__m_delta"]
                if len(x) >= 3:
                    a.hist(x.clip(901, 2499), bins=bins, density=True, histtype="step", color=PAIR_COL[k], label=f"{PAIR_LAB[k]} ({len(x)})")
        a.axvline(1232, color="k", ls=":", lw=0.7); a.set_xlabel("reconstructed M_Delta [MeV]"); a.set_ylabel("unit area"); a.set_title(ttl, fontsize=9); a.legend(fontsize=6.5)
    savefig(fig, "delta_mass_signal_vs_background_shapes.png")


def cos_angle_figure(S, Bk):
    S1 = S[S.baseline_35__channel == "1g1p"].copy(); S1 = S1[S1.baseline_35__cos_gp.notna()]
    fig, ax = PS.figure(1, 2, size=(12, 4.6)); bins = np.linspace(-1, 1, 21)
    a = ax[0][0]
    for k in ("decay_pair", "fsi_or_other_primary", "secondary_proton", "fake_or_other"):
        x = S1[S1["baseline_35__pair_class"] == k].baseline_35__cos_gp
        if len(x) >= 3:
            a.hist(x, bins=bins, density=True, histtype="step", color=PAIR_COL[k], label=f"{PAIR_LAB[k]} ({len(x)})")
    a.set_xlabel("cos(theta_gamma,p) reco"); a.set_ylabel("unit area"); a.legend(fontsize=6.5); a.set_title("official signal, final-selected reco 1gamma1p", fontsize=9)
    a = ax[0][1]; fr = {"signal": S1}
    for g in BKG_ORDER:
        fr[g] = Bk[(Bk.group == g) & (Bk.baseline_35__channel == "1g1p") & Bk.baseline_35__cos_gp.notna()]
    for g, f in fr.items():
        if len(f) >= 3:
            a.hist(f.baseline_35__cos_gp, bins=bins, density=True, histtype="step", color=BKG_COL[g], lw=1.8 if g == "signal" else 1.1, label=f"{g} ({len(f)})")
    a.set_xlabel("cos(theta_gamma,p) reco"); a.legend(fontsize=6.5); a.set_title("signal vs selected backgrounds (BNB CV, reco 1gamma1p)", fontsize=9); savefig(fig, "photon_proton_opening_angle.png")


def proton_kinematics_block(S, Bk):
    d = S[S.baseline_35__channel == "1g1p"].copy(); d["cls"] = d.baseline_35__truth_class.map({"true_primary_signal_proton": "truth-correct signal primary", "geant4_secondary_proton": "Geant4 secondary"}).fillna("fake / other")
    A = d[d.cls == "truth-correct signal primary"].copy(); A["ratio"] = A.baseline_35__lead_ke / A.baseline_35__true_ke; A["kbin"] = _bin(A.baseline_35__true_ke, [35, 50, 75, 100, 150, 200, 300, 500, 1500])
    recs = [dict(split="all", bin="all", **OB.resolution_stats(A.ratio))] + [dict(split="true_KE", bin=str(b), **OB.resolution_stats(g.ratio)) for b, g in A.groupby("kbin", observed=True)]
    A["incl"] = np.where(A.baseline_35__lead_inc3, "included==3", "included!=3"); recs += [dict(split="included", bin=b, **OB.resolution_stats(g.ratio)) for b, g in A.groupby("incl")]
    R = wr(pd.DataFrame(recs), "proton_ke_response_selected_1g1p.csv", "resolution_tables")
    comp = d.groupby("cls").baseline_35__lead_ke.agg(["size", "median", lambda s: s.quantile(0.16), lambda s: s.quantile(0.84)]).reset_index(); comp.columns = ["class", "n", "median_reco_ke", "p16", "p84"]; wr(comp, "proton_reco_ke_by_truth_class_selected_1g1p.csv")
    # proton direction (PF chord) vs truth for the truth-correct rows
    A["cosp"] = A.baseline_35__cos_proton_true; dirs = dict(n=len(A.cosp.dropna()), median_cos=float(A.cosp.median()), frac_gt0p9=float((A.cosp > 0.9).mean()), frac_lt0=float((A.cosp < 0).mean()), frac_lt0_chord_lt3cm=float((A[A.baseline_35__chord_cm < 3].cosp < 0).mean()), n_chord_lt3cm=int((A.baseline_35__chord_cm < 3).sum()))
    SUMMARY["proton_kinematics"] = dict(response=R.iloc[0].to_dict(), classes=comp.to_dict("records"), direction=dirs, n_1g1p=len(d))
    bk = Bk[Bk.baseline_35__channel == "1g1p"].groupby("group").baseline_35__lead_ke.agg(["size", "median"]).reset_index(); wr(bk, "proton_reco_ke_bnb_selected_1g1p_by_group.csv"); return d, A, R


def proton_figure(d, A, Bk):
    fig, ax = PS.figure(1, 3, size=(16, 4.6)); a = ax[0][0]
    a.hist2d(np.log10(A.baseline_35__true_ke), np.log10(A.baseline_35__lead_ke.clip(lower=1)), bins=[np.linspace(np.log10(35), np.log10(1000), 30), np.linspace(1, 3.2, 30)], cmap="viridis", cmin=1); a.plot([1.5, 3], [1.5, 3], "w--", lw=0.8)
    a.set_xlabel("log10 true proton KE [MeV]"); a.set_ylabel("log10 reco proton KE [MeV]"); a.set_title(f"final-selected reco 1g1p, truth-correct proton (n = {len(A)})", fontsize=9)
    a = ax[0][1]; edges = [35, 50, 75, 100, 150, 200, 300, 500, 1500]; x = np.arange(len(edges) - 1)
    for lab, mask, col in (("all", A.index == A.index, "k"), ("included!=3", ~A.baseline_35__lead_inc3, "#0072B2"), ("included==3", A.baseline_35__lead_inc3, "#D55E00")):
        g = A[mask]; med = []; lo = []; hi = []
        for i in range(len(edges) - 1):
            r = g[(g.baseline_35__true_ke >= edges[i]) & (g.baseline_35__true_ke < edges[i + 1])].ratio; q = np.percentile(r, [16, 50, 84]) if len(r) >= 5 else [np.nan] * 3; lo.append(q[0]); med.append(q[1]); hi.append(q[2])
        a.errorbar(x + 0.07 * ["all", "included!=3", "included==3"].index(lab), med, yerr=[np.array(med) - np.array(lo), np.array(hi) - np.array(med)], fmt="o-", color=col, ms=4, lw=1, label=f"{lab} ({len(g)})")
    a.axhline(1, color="k", ls=":", lw=0.7); a.set_xticks(x); a.set_xticklabels([f"{edges[i]}-{edges[i+1]}" for i in x], fontsize=7); a.set_xlabel("true KE bin [MeV]"); a.set_ylabel("reco / true KE"); a.set_ylim(0, 2.5); a.legend(fontsize=7)
    a = ax[0][2]; bins = np.linspace(0, 800, 33)
    for k, col in (("truth-correct signal primary", "#009E73"), ("Geant4 secondary", "#E69F00"), ("fake / other", "#D55E00")):
        g = d[d.cls == k].baseline_35__lead_ke; a.hist(g.clip(upper=799), bins=bins, density=True, histtype="step", color=col, label=f"signal: {k} ({len(g)})")
    for g, col in (("NC_PI0", BKG_COL["NC_PI0"]), ("NUE_CC", BKG_COL["NUE_CC"]), ("CC_PI0", BKG_COL["CC_PI0"])):
        x_ = Bk[(Bk.group == g) & (Bk.baseline_35__channel == "1g1p")].baseline_35__lead_ke; a.hist(x_.clip(upper=799), bins=bins, density=True, histtype="step", ls="--", color=col, label=f"BNB {g} ({len(x_)})")
    a.set_xlabel("reco proton KE [MeV]"); a.set_ylabel("unit area"); a.legend(fontsize=6.5); savefig(fig, "proton_kinematics.png")


def enu_block(S, kine, tpp):
    inc3 = kine[(kine["sample"] == "signal") & (kine.kine_energy_included == 3)].groupby(KC).kine_energy_particle.sum().rename("inc3_ke_sum").reset_index()
    pk = tpp[tpp.is_signal & tpp.primary & (tpp.ke > 0)].groupby(K).ke.sum().rename("true_primary_proton_ke").reset_index()
    d = S.merge(inc3, on=KC, how="left").merge(pk, on=K, how="left").fillna({"inc3_ke_sum": 0, "true_primary_proton_ke": 0}); d["true_visible"] = d.true_photon_e + d.true_primary_proton_ke; d["ratio_visible"] = d.kine_reco_Enu / d.true_visible; d["true_enu"] = d.true_enu_gev * 1000; d["ratio"] = d.kine_reco_Enu / d.true_enu; d["ratio_excl_inc3"] = (d.kine_reco_Enu - d.inc3_ke_sum) / d.true_enu
    d["topo"] = d.truth35.map(TL); d["anch"] = np.where(d.anchored5 == True, "anchored", "not anchored"); d["channel"] = d.baseline_35__channel; d["has_inc3"] = np.where(d.inc3_ke_sum > 0, "has included==3 rows", "no included==3 rows")
    recs = []
    for by in ("all", "topo", "anch", "channel", "has_inc3", "delta_label"):
        for b, g in ([("all", d)] if by == "all" else d.groupby(by)):
            recs.append(dict(split=by, bin=b, n=len(g), **{"ratio_" + k: v for k, v in OB.resolution_stats(g.ratio).items() if k in ("median", "p16", "p84", "half68")}, ratio_excl_inc3_median=float(g.ratio_excl_inc3.median()), ratio_to_true_visible_median=float(g.ratio_visible.median()), ratio_to_true_visible_p16=float(g.ratio_visible.quantile(.16)), ratio_to_true_visible_p84=float(g.ratio_visible.quantile(.84)), median_inc3_ke_mev=float(g.inc3_ke_sum.median())))
    R = wr(pd.DataFrame(recs), "reco_enu_response.csv", "resolution_tables")
    SUMMARY["reco_enu"] = dict(all=R.iloc[0].to_dict(), corr_log=float(np.corrcoef(np.log(d.kine_reco_Enu.clip(lower=1)), np.log(d.true_enu))[0, 1])); return d, R


def enu_figure(d):
    fig, ax = PS.figure(1, 3, size=(16, 4.6)); a = ax[0][0]
    a.hist2d(d.true_enu, d.kine_reco_Enu.clip(upper=4000), bins=[np.linspace(200, 3500, 34), np.linspace(0, 4000, 34)], cmap="viridis", cmin=1); a.plot([200, 3500], [200, 3500], "w--", lw=0.8); a.set_xlabel("true neutrino energy [MeV]"); a.set_ylabel("`kine_reco_Enu` [MeV]"); a.set_title(f"final-selected signal (n = {len(d)})", fontsize=9)
    a = ax[0][1]; edges = [200, 500, 800, 1100, 1500, 2000, 4000]; x = np.arange(len(edges) - 1)
    for lab, mask, col, ls in (("truth 0p", d.topo == "truth 0p", "#0072B2", "-"), ("truth 1p", d.topo == "truth 1p", "#D55E00", "-"), ("truth >=2p", d.topo == "truth >=2p", "#009E73", "-")):
        g = d[mask]; med = []; lo = []; hi = []
        for i in range(len(edges) - 1):
            r = g[(g.true_enu >= edges[i]) & (g.true_enu < edges[i + 1])].ratio; q = np.percentile(r, [16, 50, 84]) if len(r) >= 5 else [np.nan] * 3; lo.append(q[0]); med.append(q[1]); hi.append(q[2])
        a.errorbar(x + 0.07 * ["truth 0p", "truth 1p", "truth >=2p"].index(lab), med, yerr=[np.array(med) - np.array(lo), np.array(hi) - np.array(med)], fmt="o-", color=col, ms=4, lw=1, label=lab)
    a.axhline(1, color="k", ls=":", lw=0.7); a.set_xticks(x); a.set_xticklabels([f"{edges[i]}-{edges[i+1]}" for i in x], fontsize=7); a.set_xlabel("true E_nu bin [MeV]"); a.set_ylabel("E_reco / E_true"); a.legend(fontsize=7); a.set_ylim(0, 1.6)
    a = ax[0][2]; bins = np.linspace(0, 1.6, 41)
    for lab, mask, col in (("anchored", d.anch == "anchored", "#0072B2"), ("not anchored", d.anch != "anchored", "#D55E00")):
        g = d[mask].ratio; a.hist(g.clip(upper=1.59), bins=bins, density=True, histtype="step", color=col, label=f"{lab} (n={len(g)}, med {g.median():.2f})")
    g = d.ratio_excl_inc3; a.hist(g.clip(upper=1.59), bins=bins, density=True, histtype="step", color="k", ls="--", label=f"all, excluding included==3 energy (med {g.median():.2f})")
    g = d.ratio_visible; a.hist(g.clip(upper=1.59), bins=bins, density=True, histtype="step", color="#009E73", label=f"vs TRUE VISIBLE energy (photon + primary protons) (med {g.median():.2f})")
    a.set_xlabel("`kine_reco_Enu` / E_nu,true"); a.set_ylabel("unit area"); a.legend(fontsize=6.5); savefig(fig, "reco_enu_response.png")


def vertex_block(S, Bk):
    d = S.copy(); d["topo"] = d.truth35.map(TL); d["channel"] = d.baseline_35__channel; recs = []
    for by in ("all", "topo", "channel"):
        for b, g in ([("all", d)] if by == "all" else d.groupby(by)):
            recs.append(dict(split=by, bin=b, n=len(g), median_d_vertex=g.d_vertex.median(), p16=g.d_vertex.quantile(0.16), p84=g.d_vertex.quantile(0.84), frac_within_5cm=float((g.d_vertex <= 5).mean()), median_parallel=g.parallel.median(), median_abs_perp=g.perp.abs().median(),
                             median_vtx_z=g.vtx_z.median()))
    R = wr(pd.DataFrame(recs), "vertex_resolution_selected_signal.csv", "resolution_tables")
    sig = {"signal": S}; fr = bkg_frames(S, Bk); wr(shape_table(fr, ["vx", "vy", "vz"], None), "vertex_xyz_shapes_summary.csv", "background_shapes")
    fig, ax = PS.figure(2, 3, size=(16, 8.4))
    for i, name in enumerate(("vx", "vy", "vz")):
        a = ax[0][i]; col, lab, rng, nb = OBS[name]; bins = np.linspace(*rng, nb + 1)
        for g, f in fr.items():
            x = f[col].dropna()
            if len(x) >= 3:
                a.hist(x.clip(rng[0] + 1e-9, rng[1] - 1e-9), bins=bins, density=True, histtype="step", color=BKG_COL[g], lw=1.6 if g == "signal" else 1.0, label=f"{g} ({len(x)})")
        a.set_xlabel(lab, fontsize=8); a.set_ylabel("unit area", fontsize=8)
        if i == 0:
            a.legend(fontsize=6)
    for i, (c, lab, rng) in enumerate((("d_vertex", "|V_reco - V_true| [cm]", (0, 100)), ("parallel", "displacement along the true photon direction [cm]", (-60, 120)), ("perp", "perpendicular displacement [cm]", (0, 20)))):
        a = ax[1][i]; bins = np.linspace(*rng, 41)
        for t, col in (("truth 0p", "#0072B2"), ("truth 1p", "#D55E00"), ("truth >=2p", "#009E73")):
            g = d[d.topo == t][c]; a.hist(g.clip(rng[0] + 1e-9, rng[1] - 1e-9), bins=bins, density=True, histtype="step", color=col, label=f"{t} (n={len(g)}, med {g.median():.1f})")
        a.set_xlabel(lab, fontsize=8); a.set_ylabel("unit area", fontsize=8); a.legend(fontsize=6.5)
    savefig(fig, "vertex_observables.png"); SUMMARY["vertex"] = R.to_dict("records"); return R


# ======================================================================================================================= policy decision support (7, 8, 23), natural CV check (19), summary figure
def _mode(x, bins=MBINS):
    x = x.dropna()
    if len(x) < 3:
        return np.nan
    h, _ = np.histogram(x, bins=bins); return float(0.5 * (bins[np.argmax(h)] + bins[np.argmax(h) + 1]))


def policy_block(S_any, S_first, Bk):
    recs = []; recl = []
    for cpol, S in (("any", S_any), ("first", S_first)):
        for v in PV:
            ch = S[f"{v}__channel"]; ok = S[f"{v}__mass_status"] == "ok"; g1 = S[ch == "1g1p"]; g0 = S[ch == "1g0p"]; u = S[ok]; both = u.photon_correct & (u[f"{v}__truth_class"] == "true_primary_signal_proton")
            recs.append(dict(candidate_policy=cpol, proton_policy=v, selected_events=len(S), n_1g0p=len(g0), n_1g1p=len(g1), n_1gNp=int((ch == "1gNp").sum()), **{f"1g0p_{TL[t].replace(' ', '_')}": int((g0.truth35 == t).sum()) for t in (0, 1, 2)},
                             **{f"1g1p_{TL[t].replace(' ', '_')}": int((g1.truth35 == t).sum()) for t in (0, 1, 2)}, frac_1g1p_truth1p=float((g1.truth35 == 1).mean()) if len(g1) else np.nan, frac_1g0p_truth0p=float((g0.truth35 == 0).mean()) if len(g0) else np.nan,
                             m_delta_usable=int(ok.sum()), m_delta_both_truth_correct=int(both.sum()), m_delta_both_truth_correct_frac=float(both.mean()) if len(u) else np.nan, m_delta_median=float(u[f"{v}__m_delta"].median()), m_delta_p16=float(u[f"{v}__m_delta"].quantile(0.16)),
                             m_delta_p84=float(u[f"{v}__m_delta"].quantile(0.84)), m_delta_mode=_mode(u[f"{v}__m_delta"]), frac_decay_pair=float((u[f"{v}__pair_class"] == "decay_pair").mean()) if len(u) else np.nan))
            if cpol == "any":
                ct = pd.crosstab(S["baseline_35__channel"], S[f"{v}__channel"])
                for a in ct.index:
                    for b in ct.columns:
                        recl.append(dict(proton_policy=v, baseline_channel=a, variant_channel=b, n=int(ct.loc[a, b])))
    P = wr(pd.DataFrame(recs), "policy_decision_support.csv", "policy_sensitivity"); Rl = wr(pd.DataFrame(recl), "proton_policy_reclassification_any.csv", "policy_sensitivity")
    # BNB selected candidates (policy any): counts by group and channel under each proton policy (objects, not rates)
    b = []
    for v in PV:
        ct = Bk.groupby(["group", f"{v}__channel"]).size().rename("n").reset_index().rename(columns={f"{v}__channel": "channel"}); ct["proton_policy"] = v; b.append(ct)
    wr(pd.concat(b), "bnb_selected_objects_by_proton_policy.csv", "policy_sensitivity")
    # any vs first on the common observables
    m = S_any.merge(S_first, on=K, how="outer", suffixes=("_any", "_first"), indicator=True)
    both = m[m._merge == "both"]; same = both[both.cand_any == both.cand_first]; diff = both[both.cand_any != both.cand_first]
    cols = {"e_gamma": "photon_ke", "gap": "shw_sp_shw_vtx_dis", "proton_ke": "baseline_35__lead_ke", "m_delta": "baseline_35__m_delta"}
    af = dict(events_any=len(S_any), events_first=len(S_first), in_both=len(both), only_any=int((m._merge == "left_only").sum()), only_first=int((m._merge == "right_only").sum()), same_candidate=len(same), different_candidate=len(diff))
    for k, c in cols.items():
        x = diff[c + "_any"] - diff[c + "_first"]; af[f"diff_candidates_median_{k}_any_minus_first"] = float(x.median()) if len(diff) and x.notna().any() else np.nan; af[f"diff_candidates_n_{k}"] = int(x.notna().sum())
    for k, c in cols.items():
        af[f"{k}_median_any"] = float(S_any[c].median()); af[f"{k}_median_first"] = float(S_first[c].median())
    af["truth_topology_any"] = S_any.truth35.value_counts().to_dict(); af["truth_topology_first"] = S_first.truth35.value_counts().to_dict(); af["only_any_truth35"] = m[m._merge == "left_only"].truth35_any.value_counts().to_dict()
    AF = wr(pd.DataFrame([af]).T.reset_index().rename(columns={"index": "quantity", 0: "value"}).astype({"value": str}), "any_vs_first_comparison.csv", "policy_sensitivity")
    SUMMARY["policy"] = dict(decision_support=P.to_dict("records"), any_vs_first=af); return P, Rl, AF


def natural_block(S, Bk):
    N = Bk[Bk.group == "natural_signal_like"]; recs = []; fig, ax = PS.figure(2, 2, size=(11, 8)); spec = [("e_gamma", "photon_ke", None, (0, 1500), "selected shower energy [MeV]"), ("gap", "shw_sp_shw_vtx_dis", None, (0, 100), "gap [cm]"),
                                                                               ("proton_ke", "baseline_35__lead_ke", "1g1p", (0, 800), "reco proton KE [MeV]"), ("m_delta", "baseline_35__m_delta", "1g1p", (900, 2500), "reconstructed M_Delta [MeV]")]
    for a, (nm, col, ch, rng, lab) in zip(ax.flatten(), spec):
        o = (S if ch is None else S[S.baseline_35__channel == ch])[col].dropna(); n = (N if ch is None else N[N.baseline_35__channel == ch])[col].dropna()
        ks = stats.ks_2samp(o, n) if len(n) >= 3 else None
        recs.append(dict(observable=nm, channel=ch or "all", n_official=len(o), n_natural=len(n), median_official=float(o.median()), median_natural=float(n.median()) if len(n) else np.nan, p16_official=float(o.quantile(.16)), p84_official=float(o.quantile(.84)),
                         ks_stat=float(ks.statistic) if ks else np.nan, ks_pvalue=float(ks.pvalue) if ks else np.nan))
        bins = np.linspace(*rng, 26); a.hist(o.clip(rng[0] + 1e-9, rng[1] - 1e-9), bins=bins, density=True, histtype="step", color="k", label=f"official signal ({len(o)})"); a.plot(n.clip(rng[0] + 1e-9, rng[1] - 1e-9), np.full(len(n), -0.0005), "|", color="#D55E00", ms=12, mew=1.5, label=f"natural BNB-CV signal-like ({len(n)})")
        a.set_xlabel(lab, fontsize=8); a.set_ylabel("unit area", fontsize=8); a.legend(fontsize=6.5)
    R = wr(pd.DataFrame(recs), "natural_cv_vs_official_signal.csv"); savefig(fig, "natural_cv_cross_check.png"); SUMMARY["natural"] = dict(n=len(N), rows=R.to_dict("records")); return R


def summary_figure(S):
    fr = {"reco 1gamma0p": S[S.baseline_35__channel == "1g0p"], "reco 1gamma1p": S[S.baseline_35__channel == "1g1p"]}; colors = {"reco 1gamma0p": "#0072B2", "reco 1gamma1p": "#D55E00"}
    fr0 = {k: v.assign(baseline_35__channel="all") for k, v in fr.items()}
    old = {}
    n = 6; names = ["e_gamma", "gap", "dedx", "enu", "vz", "vx"]; fig, ax = PS.figure(2, 3, size=(16, 8.2))
    for i, name in enumerate(names):
        a = ax[i // 3][i % 3]; col, lab, rng, nb = OBS[name]; bins = np.linspace(*rng, nb + 1)
        for g, f in fr.items():
            x = f[col].dropna(); a.hist(x.clip(rng[0] + 1e-9, rng[1] - 1e-9), bins=bins, density=True, histtype="step", color=colors[g], lw=1.6, label=f"{g} ({len(x)}, med {x.median():.1f})")
        a.set_xlabel(lab, fontsize=8); a.set_ylabel("unit area", fontsize=8); a.legend(fontsize=6.5)
    savefig(fig, "common_observables_1g0p_vs_1g1p.png")


# ======================================================================================================================= orchestration
def finish(extra):
    meta = dict(git_commit_at_run=subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(), branch=subprocess.run(["git", "-C", str(REPO), "branch", "--show-current"], capture_output=True, text=True).stdout.strip(),
                official_manifest_sha256=sha(REPO / "manifests" / "official_gen2_ncdelta_wc.tsv.gz"), signal_truth_master_sha256=sha(SPD / "official_gen2_ncdelta_master" / "signal_events.parquet"), baseline_config_sha256=sha(REPO / "configs" / "baseline_selection.yaml"),
                event_table_sha256=sha(SPD / "spine_harmonization" / "official_ncdelta" / "event_flags_and_table.parquet"), phase9_summary_sha256=sha(REPO / "tables" / "shower_vertex_audit" / "summary.json"), phase9_vertex_geometry_sha256=sha(P9 / "vertex_geometry.parquet"),
                phase10_summary_sha256=sha(REPO / "tables" / "proton_truth_association" / "summary.json"), phase10_row_matches_sha256=sha(P10 / "row_matches.parquet"), phase10_truth_protons_sha256=sha(P10 / "truth_protons.parquet"), phase10_metadata=json.load(open(P10 / "metadata.json")),
                raw_sha256={k: sha(RAW / f"{k}.parquet") for k in ("tag", "kine", "pf")}, genie_delta_record_sha256=sha(OUT / "genie_delta_record.parquet"), bnb_candidates_sha256=sha(REPO / "tables" / "background_mechanisms" / "candidate_truth_category.csv"),
                proton_policy="primary: type 2212, reco KE > 35 MeV, all rows (baseline convention); sensitivities: 35 MeV excluding included==3, and 50 MeV (policy sensitivities, NOT alternative selections; no policy frozen)", candidate_policy="any (primary), first (sensitivity); not chosen",
                truth_region="provisional TPC box |x|,|y| < 200 cm, 0 < z < 500 cm (no approved FV)", proton_mass_mev=OB.M_PROTON_MEV, direction_definition="T_pf node chord (shower: start point -> farthest trajectory vertex; proton track: start -> end), unit vector; no truth-based flipping",
                no_rate_claims="signal and BNB-CV selected objects are compared as unit-area shapes only", **extra)
    (OUT / "metadata.json").write_text(json.dumps(meta, indent=1)); SUMMARY["metadata"] = meta
    (SUMD / "summary.json").write_text(json.dumps(SUMMARY, indent=1, default=lambda o: o.item() if hasattr(o, "item") else (o.tolist() if hasattr(o, "tolist") else str(o))))


def main():
    T, tag, kine, pf, rm, tpp, gen, vg, bn = load(); rm_idx, tpp_idx = make_indexes(T, rm, tpp)
    A = T[T.A_final.astype(bool)]; F = T[T.A_final_first.astype(bool)]
    O_any = build_objects("signal", [(int(r.file_index), int(r.ev), int(r.sel_nu_index)) for r in A.itertuples()], tag, kine, pf, rm_idx, tpp_idx, None, "any")
    O_first = build_objects("signal", [(int(r.file_index), int(r.ev), 0) for r in F.itertuples()], tag, kine, pf, rm_idx, tpp_idx, None, "first")
    B = build_objects("bnb", [(int(r.file_index), int(r.ev), int(r.nu_index)) for r in bn.itertuples()], tag, kine, pf, {}, {}, None, "any")
    S = assemble_signal(O_any, T, gen, vg); S1 = assemble_signal(O_first, T, gen, vg); Bk = assemble_bnb(B, bn)
    assert len(S) == 1153 and len(S1) == int(T.A_final_first.sum()) and len(Bk) == 649
    SUMMARY["objects"] = dict(signal_any=len(S), signal_first=len(S1), bnb=len(Bk), photon_row_found=int(S.photon_row_found.sum()), photon_correct=int(S.photon_correct.sum()), channels_any={v: S[v + "__channel"].value_counts().to_dict() for v in PV},
                              mass_status={v: S[v + "__mass_status"].value_counts().to_dict() for v in PV})
    g = generator_level_block(T, gen, S); breit = breit_wigner_check(g); wr(breit, "generator_decay_mass_vs_nominal_bw.csv", "resolution_tables")
    d, M = mass_distribution_block(S); mass_figure(d); dres, R, Sub, cres = resolution_block(S); resolution_figure(dres, Sub)
    pe, Re = photon_energy_block(S); photon_energy_figure(pe, Re); pdr, Rd = photon_direction_block(S); gp, Rg = gap_block(S); gap_figure(gp)
    Rs, cnt = shapes_block(S, Bk); mass_shape_figures(S, Bk); cos_angle_figure(S, Bk)
    dk, Ak, Rk = proton_kinematics_block(S, Bk); proton_figure(dk, Ak, Bk); en, Ren = enu_block(S, kine, tpp); enu_figure(en); vertex_block(S, Bk)
    P, Rl, AF = policy_block(S, S1, Bk); natural_block(S, Bk); summary_figure(S)
    # outside Git
    S.to_parquet(OUT / "selected_object_table.parquet", index=False); S1.assign(policy="first").to_parquet(OUT / "selected_object_table_first.parquet", index=False); Bk.to_parquet(OUT / "selected_object_table_bnb.parquet", index=False)
    mc = [c for c in S.columns if c.endswith("__m_delta") or c.endswith("__mass_status") or c.endswith("__pair_class") or c.endswith("__m_finalstate_truth") or c.endswith("__cos_gp") or c in K + ["cand", "photon_ke", "m_true_decay", "delta_label", "truth35", "photon_correct"]]
    pd.concat([S[mc].assign(policy="any"), S1[mc].assign(policy="first")]).to_parquet(OUT / "delta_mass_table.parquet", index=False)
    finish({}); print("done", list(SUMMARY))


if __name__ == "__main__":
    main()
