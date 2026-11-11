#!/usr/bin/env python
"""Decision support for the three analysis-definition choices D (fiducial volume), E (proton threshold / included == 3) and F (candidate policy any vs first) (READ-ONLY; the frozen baseline is NOT changed).

    source env/setup_eaf.sh
    python scripts/analysis_definition_decisions.py

No optimisation, no threshold scan presented as an optimisation, no final S/B, purity or significance: the cosmic-only background needs the collaboration-approved beam-off normalisation (blocked).
Signal and beam-neutrino-background quantities are quoted independently, both under the SAME reconstructed-vertex FV.  Outputs outside Git: $SP_DATA/analysis_definition_decisions/ ; compact tables:
tables/analysis_definition_decisions/ ; figures: plots/analysis_definition_decisions/.
"""
from __future__ import annotations
import hashlib, importlib.util, json, os, subprocess, sys, warnings
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import yaml
from sbnd_single_photon import analysis_definitions as AD, exclusive_signal as X, observables as OB, plotstyle as PS
import matplotlib.pyplot as plt

SPD = Path(os.environ["SP_DATA"]); OUT = SPD / "analysis_definition_decisions"; P8 = SPD / "other_bdt_audit" / "official_ncdelta"; P9 = SPD / "shower_vertex_audit" / "official_ncdelta"; P10 = SPD / "proton_truth_association" / "official_ncdelta"
P11 = SPD / "common_observables" / "official_ncdelta"; P12 = SPD / "remaining_stage_audit" / "official_ncdelta"
PLD = REPO / "plots" / "analysis_definition_decisions"; SUMD = REPO / "tables" / "analysis_definition_decisions"
for d in (PLD, SUMD, OUT, OUT / "fv_comparisons", OUT / "proton_policy", OUT / "candidate_policy", OUT / "common_volume_rates"):
    d.mkdir(parents=True, exist_ok=True)
K = ["file_index", "ev"]; KC = ["file_index", "ev", "cand"]; SUMMARY: dict = {}
DEN = json.load(open(REPO / "tables" / "official_signal" / "denominators.json")); POT_SIG = DEN["active_tpc"]["POT_signal_sample"]
POT_CV = json.load(open(REPO / "tables" / "official_signal" / "background_rate_model.json"))["pot_cv"]
TOPO = {0: "truth 0p", 1: "truth 1p", 2: "truth >=2p"}; CH = ["1g0p", "1g1p", "1gNp"]
PROV = "official Gen2 NC-Delta + BNB CV | frozen baseline unchanged | decision support, NOT an optimisation | beam-neutrino background only (no cosmic-only component, no S/B)"
AV = ((-200.0, 200.0), (-200.0, 200.0), (0.0, 500.0))


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


# ====================================================================================================================== load (reuses the Phase-11 object builders; adds policy P4)
def load():
    spec = importlib.util.spec_from_file_location("co_audit", REPO / "scripts" / "common_observables_audit.py"); CO = importlib.util.module_from_spec(spec); spec.loader.exec_module(CO)
    OB.PROTON_POLICIES["50_excl_included3"] = dict(threshold_mev=50.0, exclude_included3=True); CO.PV = list(OB.PROTON_POLICIES)
    assert set(AD.PROTON_PACKAGES[p]["variant"] for p in AD.PROTON_PACKAGES) <= set(CO.PV)
    Tk, tag, kine, pf, rm, tpp, gen, vg, bn = CO.load(); rm_idx, tpp_idx = CO.make_indexes(Tk, rm, tpp)
    T = pd.read_parquet(SPD / "spine_harmonization" / "official_ncdelta" / "event_flags_and_table.parquet"); T = T[T.tpc_box].copy().reset_index(drop=True)      # all 12,427 truth events (incl. the production-missing one)
    A = Tk[Tk.A_final.astype(bool)]; F = Tk[Tk.A_final_first.astype(bool)]
    S = CO.assemble_signal(CO.build_objects("signal", [(int(r.file_index), int(r.ev), int(r.sel_nu_index)) for r in A.itertuples()], tag, kine, pf, rm_idx, tpp_idx, None, "any"), Tk, gen, vg)
    S1 = CO.assemble_signal(CO.build_objects("signal", [(int(r.file_index), int(r.ev), 0) for r in F.itertuples()], tag, kine, pf, rm_idx, tpp_idx, None, "first"), Tk, gen, vg)
    Bk = CO.assemble_bnb(CO.build_objects("bnb", [(int(r.file_index), int(r.ev), int(r.nu_index)) for r in bn.itertuples()], tag, kine, pf, {}, {}, None, "any"), bn)
    assert len(S) == 1153 and len(S1) == 1101 and len(Bk) == 649
    return dict(CO=CO, T=T, Tk=Tk, S=S, S1=S1, Bk=Bk, rm=rm, tpp=tpp, vg=vg, kine=kine, tag=tag, pf=pf, bn=bn)


# ====================================================================================================================== A: fiducial volume
def fv_table(T, S, S1, Bk):
    recs = []
    bkg = Bk[Bk.group != "natural_signal_like"]
    for name, spec in AD.FV_SPECS.items():
        tin = AD.fv_mask(T.vtx_x, T.vtx_y, T.vtx_z, None if name == "none" else spec); den = T[tin]
        r = dict(fv=name, audit_id=spec["audit_id"], label=spec["label"], truth_denominator=len(den), **{f"den_{TOPO[t].replace(' ', '_')}": int((den.truth35 == t).sum()) for t in (0, 1, 2)}, den_Delta0=int((den.delta_label == "Delta0").sum()), den_DeltaPlus=int((den.delta_label == "Delta+").sum()))
        for pol, Ssel in (("any", S), ("first", S1)):
            m = AD.fv_mask(Ssel.true_vtx_x, Ssel.true_vtx_y, Ssel.true_vtx_z, None if name == "none" else spec) & AD.fv_mask(Ssel.vtx_x, Ssel.vtx_y, Ssel.vtx_z, None if name == "none" else spec); sel = Ssel[m]
            r[f"sel_{pol}"] = len(sel); r[f"eff_{pol}"] = len(sel) / len(den); r[f"sel_{pol}_reco_in_fv_truth_outside"] = int(AD.fv_mask(Ssel.vtx_x, Ssel.vtx_y, Ssel.vtx_z, None if name == "none" else spec).sum() - m.sum())
            for t in (0, 1, 2):
                n = int((sel.truth35 == t).sum()); nd = int((den.truth35 == t).sum()); r[f"sel_{pol}_{TOPO[t].replace(' ', '_')}"] = n; r[f"eff_{pol}_{TOPO[t].replace(' ', '_')}"] = n / nd if nd else np.nan
            for dl, tag_ in (("Delta0", "Delta0"), ("Delta+", "DeltaPlus")):
                n = int((sel.delta_label == dl).sum()); nd = int((den.delta_label == dl).sum()); r[f"sel_{pol}_{tag_}"] = n; r[f"eff_{pol}_{tag_}"] = n / nd if nd else np.nan
            for c in CH:
                r[f"sel_{pol}_reco_{c}"] = int((sel.baseline_35__channel == c).sum())
            r[f"S_rate_{pol}_per1e20"] = AD.rates_per_1e20(len(sel), POT_SIG)
        r["S_truth_rate_per1e20"] = AD.rates_per_1e20(len(den), POT_SIG)
        for pol, Bsel in (("any", bkg), ("first", bkg[bkg.cand == 0])):
            m = AD.fv_mask(Bsel.vtx_x, Bsel.vtx_y, Bsel.vtx_z, None if name == "none" else spec); b = Bsel[m]
            r[f"bkg_{pol}"] = len(b)
            for c in CH:
                r[f"bkg_{pol}_reco_{c}"] = int((b.baseline_35__channel == c).sum()); r[f"B_beam_rate_{pol}_reco_{c}_per1e20"] = AD.rates_per_1e20(int((b.baseline_35__channel == c).sum()), POT_CV)
            for g in ("NC_PI0", "CC_PI0", "NUE_CC", "NUMU_CC", "OUTSIDE_TPC_NU", "COSMIC_OR_UNMATCHED", "other"):
                r[f"bkg_{pol}_{g}"] = int((b.group == g).sum())
            r[f"B_beam_rate_{pol}_total_per1e20"] = AD.rates_per_1e20(len(b), POT_CV)
        r["natural_signal_like_in_fv_any"] = int(AD.fv_mask(*(Bk[Bk.group == "natural_signal_like"][["vtx_x", "vtx_y", "vtx_z"]].to_numpy().T), None if name == "none" else spec).sum())
        recs.append(r)
    R = pd.DataFrame(recs); wr(R, "fv_comparison.csv", "fv_comparisons")
    SUMMARY["fv"] = R[["fv", "truth_denominator", "sel_any", "eff_any", "sel_first", "eff_first", "bkg_any", "bkg_first"]].to_dict("records"); return R


def edge_diagnostics(D):
    T = D["T"]; Tk = D["Tk"]; vg = D["vg"]
    tx = pd.read_parquet(P9 / "event_taxonomy.parquet", columns=K + ["outcome"]); dtab = pd.read_parquet(SPD / "differential_efficiency" / "official_ncdelta" / "event_table_tpc_box_any.parquet", columns=["run", "subrun", "evt", "photon_end_class"])
    E = Tk.merge(tx, on=K, how="left").merge(vg[K + ["d_vertex"]], on=K, how="left").merge(dtab, on=["run", "subrun", "evt"], how="left")
    E["dface"] = AD.distance_to_faces(E.vtx_x, E.vtx_y, E.vtx_z, AV); E["cand"] = E.A_candidate.astype(bool); E["shower_pass"] = E.A_n20mev.astype(bool); E["final"] = E.A_final.astype(bool); E["left"] = E.photon_end_class == "left_volume"
    edges = [-1e9, 5, 10, 20, 30, 50, 100, 1e9]; E["bin"] = pd.cut(E.dface, edges, right=False); recs = []
    for b, g in E.groupby("bin", observed=True):
        gc = g[g.cand]
        recs.append(dict(dface_bin_cm=str(b), n_truth=len(g), candidate_frac=g.cand.mean(), shower_stage_pass_given_candidate=gc.shower_pass.mean() if len(gc) else np.nan, final_efficiency=g.final.mean(), median_d_vertex_cm=g.d_vertex.median(), frac_d_vertex_gt_5cm=(g.d_vertex > 5).mean(),
                         photon_left_volume_frac=g.left.mean(), n_final=int(g.final.sum()), frac_truth_0p=(g.truth35 == 0).mean()))
    R = wr(pd.DataFrame(recs), "edge_stability_by_distance_to_face.csv", "fv_comparisons")
    plateau = E[E.dface >= 50].final.mean(); SUMMARY["edge"] = dict(plateau_final_eff_dface_ge50=float(plateau), rows=R.to_dict("records"))
    c3 = []
    for ax, edges_ in (("vtx_x", np.arange(-200, 201, 40)), ("vtx_y", np.arange(-200, 201, 40)), ("vtx_z", np.arange(0, 501, 50))):
        E["b_"] = pd.cut(E[ax], edges_, right=False)
        for b, g in E.groupby("b_", observed=True):
            c3.append(dict(axis=ax, bin=str(b), n_truth=len(g), n_final=int(g.final.sum()), efficiency=g.final.mean(), candidate_frac=g.cand.mean(), shower_stage_pass_given_candidate=g[g.cand].shower_pass.mean() if g.cand.any() else np.nan))
    wr(pd.DataFrame(c3), "selected_signal_density_vs_xyz.csv", "fv_comparisons")
    fig, ax = PS.figure(1, 3, size=(16, 4.4)); x = np.arange(len(R)); lab = [s.replace(".0", "").replace("-1000000000", "<0").replace("1000000000", "inf") for s in R.dface_bin_cm]
    a = ax[0][0]; a.plot(x, R.candidate_frac, "o-", label="candidate formed"); a.plot(x, R.shower_stage_pass_given_candidate, "s-", label="> 20 MeV shower | candidate"); a.plot(x, R.final_efficiency / plateau * R.final_efficiency.max() if False else R.final_efficiency, "^-", label="final selection / truth"); a.set_xticks(x); a.set_xticklabels(lab, fontsize=7, rotation=20)
    a.set_xlabel("true vertex distance to nearest face of the 200/200/0-500 box [cm]"); a.set_ylim(0, 1.02); a.legend(fontsize=7); a.set_title("stage efficiencies near the boundary", fontsize=9)
    a = ax[0][1]; a.plot(x, R.median_d_vertex_cm, "o-", color="#D55E00"); a.set_xticks(x); a.set_xticklabels(lab, fontsize=7, rotation=20); a.set_ylabel("median |V_reco - V_true| [cm]"); a.set_title("vertex resolution", fontsize=9)
    a2 = a.twinx(); a2.plot(x, R.photon_left_volume_frac, "s--", color="#009E73"); a2.set_ylabel("photon leaves the volume (fraction)", color="#009E73")
    a = ax[0][2]; d = pd.read_csv(SUMD / "selected_signal_density_vs_xyz.csv"); d = d[d.axis == "vtx_z"]; xx = np.arange(len(d)); a.bar(xx, d.n_final, color="#0072B2"); a.set_xticks(xx); a.set_xticklabels([b.replace("[", "").replace(")", "") for b in d.bin], fontsize=6, rotation=30); a.set_ylabel("final-selected signal (any)"); a.set_xlabel("true z [cm]")
    a3 = a.twinx(); a3.plot(xx, d.efficiency, "o-", color="#D55E00"); a3.set_ylabel("efficiency (selected / truth)", color="#D55E00"); a3.set_ylim(0, 0.2); savefig(fig, "fv_edge_stability.png"); return R, E


# ====================================================================================================================== B: proton policy P1-P4
PRIM = "true_primary_signal_proton"


def tcat_of(S, P):
    """Truth category (0 / 1 / 2 = >=2 primary protons) at the policy's truth threshold: the event-table `truth35` for 35 MeV, `min(n_p50, 2)` for 50 MeV (never mixed with the other reco threshold)."""
    return S.truth35.astype(int).to_numpy() if AD.PROTON_PACKAGES[P]["truth_threshold_mev"] == 35.0 else AD.truth_category(S.n_p50)


def mech_1p_to_0p(S, rm, tpp, P):
    pol = AD.PROTON_PACKAGES[P]; thr = pol["truth_threshold_mev"]; v = pol["variant"]
    ev = S[(tcat_of(S, P) == 1) & (S[v + "__channel"] == "1g0p")][KC + ["delta_label"]].copy()
    pr = tpp[tpp.ke > thr].drop_duplicates(K)[K + ["trackid", "q_readout"]]; ev = ev.merge(pr, on=K, how="left")
    r_c = rm.merge(ev[KC], on=KC); top = r_c[r_c.p1_tid == r_c.merge(ev[KC + ["trackid"]], on=KC).trackid.to_numpy()] if len(r_c) else r_c
    t = r_c.merge(ev[KC + ["trackid"]], on=KC); topr = t[t.p1_tid == t.trackid]
    sub = t[(t.p2_tid == t.trackid) | (t.p3_tid == t.trackid)][KC].drop_duplicates()
    oth = rm.merge(ev[K + ["trackid"]], left_on=K + ["p1_tid"], right_on=K + ["trackid"]).merge(ev[KC], on=K, suffixes=("", "_sel")); oth = oth[oth.cand != oth.cand_sel][K].drop_duplicates()
    def hit(df):
        return pd.MultiIndex.from_frame(ev[KC]).isin(pd.MultiIndex.from_frame(df[KC].drop_duplicates()))
    inc = topr[(topr.kine_particle_type == 2212) & (topr.ke > thr) & (topr.kine_energy_included == 3)] if pol["exclude_included3"] else topr.iloc[0:0]
    low = topr[(topr.kine_particle_type == 2212) & (topr.ke <= thr)]; any_top = topr
    reason = np.select([hit(inc), hit(low), hit(any_top), pd.MultiIndex.from_frame(ev[K]).isin(pd.MultiIndex.from_frame(oth)), hit(sub), ev.q_readout.fillna(0).to_numpy() > 0],
                       ["proton_row_excluded_by_included3_policy", "proton_row_reco_KE_below_threshold", "matched_row_nonproton_type", "proton_in_other_candidate", "proton_only_subdominant_partner", "proton_never_a_row__charge_deposited"], "proton_never_a_row__no_readout_charge")
    ev["reason"] = reason; ev["policy"] = P; return ev


def mech_0p_to_1p(S, rm, tpp, P):
    pol = AD.PROTON_PACKAGES[P]; thr = pol["reco_threshold_mev"]; v = pol["variant"]
    ev = S[(tcat_of(S, P) == 0) & (S[v + "__channel"] == "1g1p")][KC + ["delta_label"]].copy()
    r = rm.merge(ev[KC], on=KC); r = r[(r.kine_particle_type == 2212) & (r.ke > thr)]
    if pol["exclude_included3"]:
        r = r[r.kine_energy_included != 3]
    assert len(r) == len(ev), (P, len(r), len(ev))
    r = r.assign(reason=np.where(r.origin == PRIM, "true_primary_proton_below_truth_threshold_promoted_by_reco", r.origin)); r["policy"] = P; return r[KC + ["delta_label", "reason", "policy"]]


def proton_block(D):
    S, Bk, rm, tpp = D["S"], D["Bk"], D["rm"], D["tpp"]; CO = D["CO"]; recs = []; mats = []; mech = []; compo = []; bnb = []; mass = []
    sel_rows = rm.merge(S[KC], on=KC)
    for P, pol in AD.PROTON_PACKAGES.items():
        v = pol["variant"]; thr = pol["reco_threshold_mev"]; S_ = S.copy(); S_["tcat"] = tcat_of(S, P); ch = S_[v + "__channel"]
        r = dict(policy=P, variant=v, reco_threshold_mev=thr, exclude_included3=pol["exclude_included3"], truth_threshold_mev=pol["truth_threshold_mev"], **{f"final_{c}": int((ch == c).sum()) for c in CH})
        for c in CH:
            g = S_[ch == c]; r.update({f"{c}_truth_{t}p": int((g.tcat == t).sum()) for t in (0, 1, 2)}); r[f"{c}_frac_truth_1p"] = float((g.tcat == 1).mean()) if len(g) else np.nan; r[f"{c}_frac_truth_0p"] = float((g.tcat == 0).mean()) if len(g) else np.nan
        for t in (0, 1, 2):
            for c in CH:
                mats.append(dict(policy=P, truth=TOPO[t], reco=c, n=int(((S_.tcat == t) & (ch == c)).sum())))
        ok = S_[v + "__mass_status"] == "ok"; u = S_[ok]; both = u.photon_correct & (u[v + "__truth_class"] == PRIM); m = u[v + "__m_delta"]
        h, e = np.histogram(m, bins=CO.MBINS)
        r.update(m_delta_usable=int(ok.sum()), m_delta_both_truth_correct_frac=float(both.mean()), m_delta_median=float(m.median()), m_delta_p16=float(m.quantile(.16)), m_delta_p84=float(m.quantile(.84)), m_delta_half68=float((m.quantile(.84) - m.quantile(.16)) / 2),
                 m_delta_mode=float(0.5 * (e[h.argmax()] + e[h.argmax() + 1])), frac_decay_pair=float((u[v + "__pair_class"] == "decay_pair").mean()))
        rr = sel_rows[(sel_rows.in_final) & (sel_rows.kine_particle_type == 2212) & (sel_rows.ke > thr)]
        if pol["exclude_included3"]:
            rr = rr[rr.kine_energy_included != 3]
        cc = rr.origin.value_counts(); n = len(rr)
        for k in ("true_primary_signal_proton", "geant4_secondary_proton", "signal_nonproton_misidentified", "other_neutrino_proton", "ambiguous_multiple_truth", "cosmic_or_non_neutrino", "unmatched", "other_neutrino_nonproton"):
            compo.append(dict(policy=P, origin=k, n=int(cc.get(k, 0)), frac=float(cc.get(k, 0) / n) if n else np.nan, n_rows=n))
        r["reco_proton_rows_final"] = n; r["reco_proton_row_frac_true_primary"] = float(cc.get(PRIM, 0) / n)
        m10 = mech_1p_to_0p(S, rm, tpp, P); m01 = mech_0p_to_1p(S, rm, tpp, P)
        for k, g in m10.groupby("reason"):
            mech.append(dict(policy=P, direction="truth1p->reco0p", reason=k, n=len(g), frac=len(g) / len(m10), n_reco=len(m10)))
        for k, g in m01.groupby("reason"):
            mech.append(dict(policy=P, direction="truth0p->reco1p", reason=k, n=len(g), frac=len(g) / len(m01), n_reco=len(m01)))
        b = Bk[Bk.group != "natural_signal_like"]
        for gname, g in list(b.groupby("group")) + [("ALL", b)]:
            bnb.append(dict(policy=P, group=gname, **{c: int((g[v + "__channel"] == c).sum()) for c in CH}))
        recs.append(r)
    R = wr(pd.DataFrame(recs), "proton_policy_comparison.csv", "proton_policy"); wr(pd.DataFrame(mats), "proton_policy_truth_reco_matrices.csv", "proton_policy"); M = wr(pd.DataFrame(mech), "proton_policy_migration_mechanisms.csv", "proton_policy")
    wr(pd.DataFrame(compo), "proton_policy_reco_proton_row_truth_composition.csv", "proton_policy"); wr(pd.DataFrame(bnb), "proton_policy_bnb_selected_by_reco_category.csv", "proton_policy"); SUMMARY["proton"] = R.to_dict("records"); SUMMARY["proton_mech"] = M.to_dict("records"); return R, M


def threshold_robustness(D):
    tpp, rm, S, T = D["tpp"], D["rm"], D["S"], D["T"]; bins = [(25, 35), (35, 50), (50, 75)]; recs = []
    prim = tpp[tpp.ke >= 10]
    for lo, hi in bins:
        t = prim[(prim.ke > lo) & (prim.ke <= hi)]; rr = rm.merge(S[KC], on=KC); rr = rr[(rr.in_final) & (rr.kine_particle_type == 2212)]; rb = rr[(rr.ke > lo) & (rr.ke <= hi)]
        recs.append(dict(band_mev=f"{lo}-{hi}", true_signal_primary_protons=len(t), frac_of_all_true_primary_gt10=len(t) / len(prim), events_with_true_proton_in_band=t[K].drop_duplicates().shape[0], frac_of_events=t[K].drop_duplicates().shape[0] / len(T),
                         selected_events_with_reco_proton_row_in_band=rb[KC].drop_duplicates().shape[0], frac_of_selected=rb[KC].drop_duplicates().shape[0] / len(S), reco_proton_rows_in_band_final=len(rb)))
    R = wr(pd.DataFrame(recs), "threshold_band_populations.csv", "proton_policy")
    # truth-category flips between the two thresholds and reco-category flips between P1 and P3 (final selected)
    tc35 = AD.truth_category(T.n_p35_prim); tc50 = AD.truth_category(T.n_p50); flips_truth = int((tc35 != tc50).sum())
    ch1 = S["baseline_35__channel"]; ch3 = S["50__channel"]; flips_reco = int((ch1 != ch3).sum())
    # response around the thresholds from the row-level association (class A rows of the signal-matched candidate, typed proton)
    A = rm[(rm.in_match) & (rm.kine_particle_type == 2212) & (rm.origin == PRIM) & rm.p1_t_ke.notna()]; cross = []
    for lo, hi, thr_, lab in ((25, 35, 35, "true 25-35, reco > 35"), (35, 50, 35, "true 35-50, reco <= 35"), (35, 50, 50, "true 35-50, reco > 50"), (50, 75, 50, "true 50-75, reco <= 50"), (50, 75, 35, "true 50-75, reco <= 35")):
        g = A[(A.p1_t_ke > lo) & (A.p1_t_ke <= hi)]
        f = float((g.ke > thr_).mean()) if "reco >" in lab else float((g.ke <= thr_).mean()); k = int((g.ke > thr_).sum()) if "reco >" in lab else int((g.ke <= thr_).sum()); cross.append(dict(crossing=lab, n_rows=len(g), n_cross=k, fraction=f))
    C = wr(pd.DataFrame(cross), "threshold_crossing_fractions.csv", "proton_policy")
    SUMMARY["threshold"] = dict(truth_category_flips_35_vs_50=flips_truth, reco_channel_flips_P1_vs_P3_final=flips_reco, n_events=len(T), bands=R.to_dict("records"), crossing=C.to_dict("records")); return R, C


# ====================================================================================================================== C: candidate policy
def cand_truth_class(r):
    if not bool(r.dom_ok):
        return "cosmic_or_unmatched"
    return "neutrino_outside_AV_dirt" if not AD.fv_mask([r.dom_nu_vx], [r.dom_nu_vy], [r.dom_nu_vz], AD.FV_SPECS["av200"])[0] else "neutrino_in_AV"


def candidate_block(D):
    T, Tk, S, S1, Bk, bn = D["T"], D["Tk"], D["S"], D["S1"], D["Bk"], D["bn"]; o = pd.read_parquet(SPD / "analysis_tables" / "official_gen2_ncdelta" / "candidates.parquet"); b = pd.read_parquet(SPD / "analysis_tables" / "bnb_cv" / "candidates.parquet")
    ev_b = pd.read_parquet(SPD / "analysis_tables" / "bnb_cv" / "events.parquet", columns=K)
    ov = {"official_signal": AD.overlap_table(T.A_final.astype(bool), T.A_final_first.astype(bool))}
    sel_b = b[b.pass_final.astype(bool)]; keys_b = sel_b[K].drop_duplicates(); kf_b = sel_b[sel_b.policy_first.astype(bool)][K].drop_duplicates(); nb = len(ev_b)
    ov["bnb_cv_all_selected"] = dict(both=len(kf_b), any_only=len(keys_b) - len(kf_b), first_only=0, neither=nb - len(keys_b), n_any=len(keys_b), n_first=len(kf_b), n_events=nb)
    non_sig = bn[bn.event_class == "background"][K].drop_duplicates(); ns_first = bn[(bn.event_class == "background") & (bn.nu_index == 0)][K].drop_duplicates()
    ov["bnb_cv_non_signal_background"] = dict(both=len(ns_first), any_only=len(non_sig) - len(ns_first), first_only=0, neither=nb - len(non_sig), n_any=len(non_sig), n_first=len(ns_first), n_events=nb)
    O = wr(pd.DataFrame(ov).T.reset_index().rename(columns={"index": "sample"}), "candidate_policy_event_overlap.csv", "candidate_policy")
    # counting: number of passing candidates per event and the candidate multiplicity
    cnt = {}
    for nm, c_ in (("official_signal_filter_box", o), ("bnb_cv", b)):
        pc = c_[c_.pass_final.astype(bool)].groupby(K).size(); nc = c_.groupby(K).size()
        cnt[nm] = dict(events_with_candidate=int(len(nc)), events_with_2plus_candidates=int((nc >= 2).sum()), selected_events=int(len(pc)), events_with_2plus_passing_candidates=int((pc >= 2).sum()), max_passing_per_event=int(pc.max()))
    C = wr(pd.DataFrame(cnt).T.reset_index().rename(columns={"index": "sample"}), "event_counting_check.csv", "candidate_policy")
    # why does candidate 1 rescue an event?  signal (TPC box) and BNB
    rows = []
    ao = Tk[Tk.A_final.astype(bool) & ~Tk.A_final_first.astype(bool)]
    for r in ao.itertuples():
        c = o[(o.file_index == r.file_index) & (o.ev == r.ev)]; c0 = c[c.c_nu_index == 0].iloc[0]; cp_ = c[c.c_nu_index == r.sel_nu_index].iloc[0]
        rows.append(dict(sample="official_signal", file_index=r.file_index, ev=r.ev, truth_topology=TOPO[int(r.truth35)], delta=r.delta_label, cand0_first_failed_stage=AD.first_failed_stage(c0), cand0_truth=cand_truth_class(c0), passing_cand_truth=cand_truth_class(cp_),
                         same_truth_neutrino=bool(c0.dom_ok and cp_.dom_ok and c0.dom_nu == cp_.dom_nu), passing_cand_is_signal_matched=bool(r.match_cand_nu == r.sel_nu_index), cand0_is_signal_matched=bool(r.match_cand_nu == 0), cand0_ccnc=float(c0.dom_nu_ccnc), cand0_pdg=float(c0.dom_nu_pdg)))
    bao = bn[(bn.nu_index == 1) | (bn.nu_index == 2)]
    for r in bao.itertuples():
        c = b[(b.file_index == r.file_index) & (b.ev == r.ev)]; c0 = c[c.c_nu_index == 0].iloc[0]; cp_ = c[c.c_nu_index == r.nu_index].iloc[0]
        rows.append(dict(sample="bnb_cv", file_index=r.file_index, ev=r.ev, truth_topology=r.event_class, delta=r.cand_category, cand0_first_failed_stage=AD.first_failed_stage(c0), cand0_truth=cand_truth_class(c0), passing_cand_truth=cand_truth_class(cp_),
                         same_truth_neutrino=bool(c0.dom_ok and cp_.dom_ok and c0.dom_nu == cp_.dom_nu), passing_cand_is_signal_matched=bool(r.event_class == "signal_like"), cand0_is_signal_matched=False, cand0_ccnc=float(c0.dom_nu_ccnc), cand0_pdg=float(c0.dom_nu_pdg)))
    AO = pd.DataFrame(rows); AO.to_csv(OUT / "candidate_policy" / "any_only_events.csv", index=False)
    summ = []
    for smp, g in AO.groupby("sample"):
        for col in ("cand0_first_failed_stage", "cand0_truth", "passing_cand_truth", "same_truth_neutrino", "truth_topology"):
            for k, n in g[col].value_counts().items():
                summ.append(dict(sample=smp, variable=col, value=str(k), n=int(n), frac=float(n / len(g))))
        summ.append(dict(sample=smp, variable="passing_cand_is_signal_matched", value="True", n=int(g.passing_cand_is_signal_matched.sum()), frac=float(g.passing_cand_is_signal_matched.mean())))
    A = wr(pd.DataFrame(summ), "any_only_events_summary.csv", "candidate_policy")
    # observables of the any-only population against the common population (signal)
    tx = pd.read_parquet(P9 / "event_taxonomy.parquet", columns=K + ["outcome"]); Sx = S.merge(tx, on=K, how="left"); Sx["any_only"] = ~Sx.set_index(K).index.isin(S1.set_index(K).index)
    Sx["clean"] = Sx.outcome == "pass_photon_shower_in_passing_candidate"; obs = []
    for lab, g in (("common (any and first)", Sx[~Sx.any_only]), ("any-only", Sx[Sx.any_only])):
        r = dict(population=lab, n=len(g), photon_energy_median=g.photon_ke.median(), gap_median=g.shw_sp_shw_vtx_dis.median(), frac_attached=(g.shw_sp_shw_vtx_dis == 0).mean(), proton_ke_median_1g1p=g[g.baseline_35__channel == "1g1p"].baseline_35__lead_ke.median(),
                 m_delta_median=g.baseline_35__m_delta.median(), vtx_z_median=g.vtx_z.median(), reco_enu_median=g.kine_reco_Enu.median(), frac_photon_truth_correct=g.photon_correct.mean(), frac_clean_photon=g.clean.mean(), frac_1g1p=(g.baseline_35__channel == "1g1p").mean(),
                 frac_truth_1p=(g.truth35 == 1).mean(), frac_anchored=(g.anchored5 == True).mean())
        obs.append(r)
    bb = Bk[Bk.group != "natural_signal_like"].copy(); bb["any_only"] = bb.cand != 0
    for lab, g in (("BNB non-signal common", bb[~bb.any_only]), ("BNB non-signal any-only", bb[bb.any_only])):
        obs.append(dict(population=lab, n=len(g), photon_energy_median=g.photon_ke.median(), gap_median=g.shw_sp_shw_vtx_dis.median(), frac_attached=(g.shw_sp_shw_vtx_dis == 0).mean(), proton_ke_median_1g1p=g[g.baseline_35__channel == "1g1p"].baseline_35__lead_ke.median(),
                        m_delta_median=g.baseline_35__m_delta.median(), vtx_z_median=g.vtx_z.median(), reco_enu_median=g.kine_reco_Enu.median(), frac_1g1p=(g.baseline_35__channel == "1g1p").mean()))
    Ob = wr(pd.DataFrame(obs), "any_only_vs_common_observables.csv", "candidate_policy")
    SUMMARY["candidate"] = dict(overlap=ov, counting=cnt, any_only_summary=A.to_dict("records"), observables=Ob.to_dict("records")); return O, C, AO, A, Ob


# ====================================================================================================================== D/E/F packages: common-volume rates and the policy envelope
def evaluate_packages(D):
    cfg = yaml.safe_load(open(REPO / "configs" / "analysis_definition_candidates.yaml")); T, S, S1, Bk = D["T"], D["S"], D["S1"], D["Bk"]; CO = D["CO"]; recs = []
    bkg_all = Bk[Bk.group != "natural_signal_like"]
    for name, pk in cfg["packages"].items():
        P = pk["proton_policy"]; pol = AD.PROTON_PACKAGES[P]; v = pol["variant"]; ft = AD.FV_SPECS[pk["truth_fv"]]; fr = AD.FV_SPECS[pk["reco_fv"]]
        nt = None if pk["truth_fv"] == "none" else ft; nr = None if pk["reco_fv"] == "none" else fr
        Ssel = S if pk["candidate_policy"] == "any" else S1
        tin = AD.fv_mask(T.vtx_x, T.vtx_y, T.vtx_z, nt); den = T[tin]; dcat = tcat_of(den, P)
        m = AD.fv_mask(Ssel.true_vtx_x, Ssel.true_vtx_y, Ssel.true_vtx_z, nt) & AD.fv_mask(Ssel.vtx_x, Ssel.vtx_y, Ssel.vtx_z, nr); sel = Ssel[m]; scat = tcat_of(sel, P); ch = sel[v + "__channel"]
        r = dict(package=name, truth_fv=pk["truth_fv"], reco_fv=pk["reco_fv"], proton_policy=P, candidate_policy=pk["candidate_policy"], truth_denominator=len(den), selected_signal=len(sel), signal_efficiency=len(sel) / len(den))
        for t in (0, 1, 2):
            r[f"eff_truth_{t}p"] = float(((scat == t).sum()) / max((dcat == t).sum(), 1))
        for c in CH:
            r[f"S_reco_{c}"] = int((ch == c).sum()); r[f"S_rate_reco_{c}_per1e20"] = AD.rates_per_1e20(int((ch == c).sum()), POT_SIG)
        r["frac_1g1p_truth_1p"] = float(((scat == 1) & (ch == "1g1p")).sum() / max((ch == "1g1p").sum(), 1)); r["frac_1g0p_truth_0p"] = float(((scat == 0) & (ch == "1g0p")).sum() / max((ch == "1g0p").sum(), 1))
        S_truth_rate = AD.rates_per_1e20(len(den), POT_SIG); r["S_truth_rate_per1e20"] = S_truth_rate; r["S_selected_rate_per1e20"] = AD.rates_per_1e20(len(sel), POT_SIG)
        ok = sel[v + "__mass_status"] == "ok"; u = sel[ok]; mm = u[v + "__m_delta"]; h, e = np.histogram(mm, bins=CO.MBINS)
        r.update(m_delta_usable=int(ok.sum()), m_delta_mode=float(0.5 * (e[h.argmax()] + e[h.argmax() + 1])) if len(mm) else np.nan, m_delta_median=float(mm.median()), m_delta_half68=float((mm.quantile(.84) - mm.quantile(.16)) / 2) if len(mm) else np.nan,
                 m_delta_both_truth_correct_frac=float((u.photon_correct & (u[v + "__truth_class"] == PRIM)).mean()) if len(u) else np.nan)
        b = bkg_all if pk["candidate_policy"] == "any" else bkg_all[bkg_all.cand == 0]; b = b[AD.fv_mask(b.vtx_x, b.vtx_y, b.vtx_z, nr)]
        r["B_beam_selected"] = len(b); r["B_beam_rate_total_per1e20"] = AD.rates_per_1e20(len(b), POT_CV)
        for c in CH:
            n = int((b[v + "__channel"] == c).sum()); r[f"B_beam_reco_{c}"] = n; r[f"B_beam_rate_reco_{c}_per1e20"] = AD.rates_per_1e20(n, POT_CV)
        for g in ("NC_PI0", "CC_PI0", "NUE_CC", "NUMU_CC", "OUTSIDE_TPC_NU", "COSMIC_OR_UNMATCHED", "other"):
            r[f"B_beam_{g}"] = int((b.group == g).sum())
        for c in ("1g0p", "1g1p"):
            r[f"signal_over_beam_neutrino_background_reference_{c}"] = AD.reference_ratio(r[f"S_rate_reco_{c}_per1e20"], r[f"B_beam_rate_reco_{c}_per1e20"])
        recs.append(r)
    R = pd.DataFrame(recs); wr(R, "package_rates_and_headlines.csv", "common_volume_rates")
    ref = R[R.package == "av200_P1_any"].iloc[0].to_dict(); keys = ["signal_efficiency", "S_reco_1g0p", "S_reco_1g1p", "frac_1g1p_truth_1p", "frac_1g0p_truth_0p", "B_beam_reco_1g0p", "B_beam_reco_1g1p", "B_beam_rate_reco_1g0p_per1e20", "B_beam_rate_reco_1g1p_per1e20", "m_delta_mode", "m_delta_half68", "m_delta_usable"]
    env = pd.DataFrame([AD.envelope_row(r.package, {k: r[k] for k in keys}, {k: ref[k] for k in keys}) for _, r in R.iterrows()])
    for c in ("truth_fv", "reco_fv", "proton_policy", "candidate_policy"):
        env.insert(1, c, R[c].to_numpy())
    wr(env.sort_index(axis=1), "policy_envelope.csv", "common_volume_rates")
    SUMMARY["packages"] = R.to_dict("records"); SUMMARY["envelope_reference"] = "av200_P1_any"; return R, env


def figures(D, R, Rfv, Rpol, Mech, AO, A, env, Ov):
    # 1. fiducial volumes
    fig, ax = PS.figure(1, 3, size=(16, 4.6)); x = np.arange(len(Rfv)); lab = list(Rfv.fv)
    a = ax[0][0]; a.bar(x - 0.2, Rfv.eff_any, 0.4, color="#0072B2", label="any"); a.bar(x + 0.2, Rfv.eff_first, 0.4, color="#E69F00", label="first"); a.set_xticks(x); a.set_xticklabels(lab, rotation=25, fontsize=7); a.set_ylabel("signal efficiency (selected in FV / truth in FV)"); a.legend(fontsize=7)
    a = ax[0][1]; a.bar(x - 0.2, Rfv.S_rate_any_per1e20, 0.4, color="#0072B2", label="selected signal"); a.bar(x + 0.2, Rfv.B_beam_rate_any_total_per1e20, 0.4, color="#D55E00", label="selected beam-neutrino background"); a.set_xticks(x); a.set_xticklabels(lab, rotation=25, fontsize=7)
    a.set_ylabel("rate per 1e20 POT (policy any, same reco FV)"); a.legend(fontsize=7); a.set_title("signal and beam-neutrino background under the SAME reco FV (no cosmic-only)", fontsize=8)
    a = ax[0][2]
    for c, col in (("1g0p", "#0072B2"), ("1g1p", "#D55E00")):
        a.plot(x, (Rfv[f"sel_any_reco_{c}"] / POT_SIG) / (Rfv[f"bkg_any_reco_{c}"] / POT_CV), "o-", color=col, label=f"reference ratio of RATES S / B_beam, reco {c}")
    a.set_xticks(x); a.set_xticklabels(lab, rotation=25, fontsize=7); a.set_ylabel("signal / beam-neutrino-background REFERENCE ratio (not analysis S/B)"); a.legend(fontsize=7); a.set_ylim(0, None); fig.subplots_adjust(bottom=0.25, wspace=0.35); savefig(fig, "fv_comparison.png")
    # 2. proton policy
    fig, ax = PS.figure(1, 3, size=(16, 4.6)); a = ax[0][0]; x = np.arange(4)
    for j, c in enumerate(CH):
        a.bar(x + 0.27 * (j - 1), Rpol[f"final_{c}"], 0.27, label=f"reco {c}")
    a.set_xticks(x); a.set_xticklabels(Rpol.policy); a.set_ylabel("final-selected signal events (any)"); a.legend(fontsize=7)
    for a, d, ttl in ((ax[0][1], "truth1p->reco0p", "truth 1p -> reco 0p reasons"), (ax[0][2], "truth0p->reco1p", "truth 0p -> reco 1p origin of the reco proton")):
        M = Mech[Mech.direction == d].pivot(index="policy", columns="reason", values="frac").fillna(0); bottom = np.zeros(len(M))
        for k in M.columns:
            a.bar(np.arange(len(M)), M[k], bottom=bottom, label=k.replace("_", " ")[:44]); bottom += M[k].to_numpy()
        a.set_xticks(np.arange(len(M))); a.set_xticklabels(M.index); a.set_title(ttl, fontsize=9); a.legend(fontsize=5, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=2)
    savefig(fig, "proton_policy_comparison.png")
    # 3. candidate policy
    fig, ax = PS.figure(1, 3, size=(16, 4.6)); a = ax[0][0]; d = Ov[Ov["sample"].isin(["official_signal", "bnb_cv_non_signal_background"])]; xx = np.arange(len(d))
    a.bar(xx - 0.2, d.both, 0.4, label="passes under both"); a.bar(xx + 0.2, d.any_only, 0.4, label="any only"); a.set_xticks(xx); a.set_xticklabels(["official signal", "BNB non-signal"]); a.set_yscale("log"); a.legend(fontsize=7); a.set_ylabel("events (first-only = 0)")
    for a, col, ttl in ((ax[0][1], "cand0_first_failed_stage", "first frozen stage failed by candidate 0"), (ax[0][2], "cand0_truth", "truth of the failing candidate 0")):
        for j, smp in enumerate(("official_signal", "bnb_cv")):
            g = AO[AO["sample"] == smp][col].value_counts(); a.bar(np.arange(len(g)) + 0.4 * j, g.values, 0.4, label=smp); a.set_xticks(np.arange(len(g)) + 0.2); a.set_xticklabels([s.replace("_", " ") for s in g.index], rotation=25, fontsize=6, ha="right") if j == 0 else None
        a.set_title(ttl, fontsize=9); a.legend(fontsize=7)
    savefig(fig, "candidate_policy.png")
    # 4. envelope
    fig, ax = PS.figure(2, 2, size=(14, 8.4)); x = np.arange(len(R)); lab = list(R.package)
    for a, col, yl in ((ax[0][0], "signal_efficiency", "signal efficiency"), (ax[0][1], "B_beam_rate_total_per1e20", "beam-neutrino background rate per 1e20 POT"), (ax[1][0], "S_rate_reco_1g1p_per1e20", "selected signal rate reco 1g1p per 1e20 POT"), (ax[1][1], "m_delta_mode", "M_Delta mode [MeV] (error bar: 68 % half-width)")):
        if col == "m_delta_mode":
            a.errorbar(x, R[col], yerr=R.m_delta_half68, fmt="o", color="k")
        else:
            a.plot(x, R[col], "o", color="k")
        a.axhline(R[R.package == "av200_P1_any"][col].iloc[0], color="#999999", ls=":", lw=0.8); a.set_xticks(x); a.set_xticklabels(lab, rotation=40, ha="right", fontsize=6); a.set_ylabel(yl, fontsize=8)
    savefig(fig, "policy_envelope.png")


# ====================================================================================================================== orchestration
def finish(extra):
    meta = dict(git_commit_at_run=subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(), branch=subprocess.run(["git", "-C", str(REPO), "branch", "--show-current"], capture_output=True, text=True).stdout.strip(),
                official_manifest_sha256=sha(REPO / "manifests" / "official_gen2_ncdelta_wc.tsv.gz"), signal_truth_master_sha256=sha(SPD / "official_gen2_ncdelta_master" / "signal_events.parquet"), baseline_config_sha256=sha(REPO / "configs" / "baseline_selection.yaml"),
                analysis_definition_candidates_sha256=sha(REPO / "configs" / "analysis_definition_candidates.yaml"), bnb_cv_candidate_table_sha256=sha(SPD / "analysis_tables" / "bnb_cv" / "candidates.parquet"), bnb_cv_selected_taxonomy_sha256=sha(REPO / "tables" / "background_mechanisms" / "candidate_truth_category.csv"),
                official_candidate_table_sha256=sha(SPD / "analysis_tables" / "official_gen2_ncdelta" / "candidates.parquet"), phase10_row_matches_sha256=sha(P10 / "row_matches.parquet"), phase10_summary_sha256=sha(REPO / "tables" / "proton_truth_association" / "summary.json"),
                phase11_summary_sha256=sha(REPO / "tables" / "common_observables" / "summary.json"), phase11_object_table_sha256=sha(P11 / "selected_object_table.parquet"), phase12_summary_sha256=sha(REPO / "tables" / "remaining_stage_audit" / "summary.json"),
                pot_signal_sample=POT_SIG, pot_bnb_cv=POT_CV, no_cosmic_normalisation="beam-off normalisation blocked on the collaboration; no purity, S/B or significance is produced", flash_time_shift="none applied", **extra)
    (OUT / "metadata.json").write_text(json.dumps(meta, indent=1)); SUMMARY["metadata"] = meta
    (SUMD / "summary.json").write_text(json.dumps(SUMMARY, indent=1, default=lambda o: o.item() if hasattr(o, "item") else (o.tolist() if hasattr(o, "tolist") else str(o))))


def main():
    D = load(); Rfv = fv_table(D["T"], D["S"], D["S1"], D["Bk"]); Rfv.to_parquet(OUT / "fv_comparisons" / "fv_comparison.parquet", index=False); edge_diagnostics(D)
    Rpol, Mech = proton_block(D); threshold_robustness(D); Ov, Cnt, AO, A, Ob = candidate_block(D); R, env = evaluate_packages(D); figures(D, R, Rfv, Rpol, Mech, AO, A, env, Ov)
    finish({}); print("done", list(SUMMARY))


if __name__ == "__main__":
    main()
