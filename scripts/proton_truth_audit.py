#!/usr/bin/env python
"""Row-level reco-proton truth association audit of the frozen Wire-Cell baseline on the official Gen2 NC-Delta signal (READ-ONLY analysis of stored tables; no decision, cut, threshold or policy changes).

    source env/setup_eaf.sh
    python scripts/proton_truth_scan.py ; python scripts/proton_truth_origin_scan.py ; python scripts/proton_truth_delta_inputs_scan.py     # raw tables (once)
    python scripts/proton_truth_audit.py

Outputs outside Git: $SP_DATA/proton_truth_association/official_ncdelta/ (reco_proton_rows, truth_protons, row_matches, event_migration_reasons, delta_mass_readiness, metadata.json);
compact summaries: tables/proton_truth_association/; headline figures: plots/proton_truth_association/.
"""
from __future__ import annotations
import hashlib, json, os, subprocess, sys, warnings
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from sbnd_single_photon import exclusive_signal as X, plotstyle as PS, proton_tables as PT
import matplotlib.pyplot as plt

SPD = Path(os.environ["SP_DATA"]); OUT = SPD / "proton_truth_association" / "official_ncdelta"; RAW = OUT / "raw"; P8 = SPD / "other_bdt_audit" / "official_ncdelta"; P9 = SPD / "shower_vertex_audit" / "official_ncdelta"
PLD = REPO / "plots" / "proton_truth_association"; SUMD = REPO / "tables" / "proton_truth_association"
for d in (PLD, SUMD, OUT):
    d.mkdir(parents=True, exist_ok=True)
K = ["file_index", "ev"]; SUMMARY: dict = {}
THR_SCAN = [10, 20, 35, 50, 75, 100]; BASE_THR = 35.0
PROV = "official Gen2 NC-Delta | frozen Wire-Cell baseline (policy any) | TPC-box signal events | descriptive audit, no selection changed"
TL = {0: "truth 0p", 1: "truth 1p", 2: "truth >=2p"}
CLS_SHORT = {"true_primary_signal_proton": "A signal primary p", "other_neutrino_proton": "B other-nu p", "geant4_secondary_proton": "C G4 secondary p", "signal_nonproton_misidentified": "D signal non-p",
             "other_neutrino_nonproton": "E other-nu non-p", "cosmic_or_non_neutrino": "F cosmic", "ambiguous_multiple_truth": "G ambiguous", "unmatched": "H unmatched"}
CLS_COL = {"true_primary_signal_proton": "#009E73", "other_neutrino_proton": "#56B4E9", "geant4_secondary_proton": "#E69F00", "signal_nonproton_misidentified": "#D55E00",
           "other_neutrino_nonproton": "#CC79A7", "cosmic_or_non_neutrino": "#999999", "ambiguous_multiple_truth": "#F0E442", "unmatched": "#000000"}
KE_BINS = [35, 50, 75, 100, 150, 200, 300, 500, 1500]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def cp(k, n):
    return X.binom_ci(int(k), int(n)) if n else (np.nan,) * 3


def savefig(fig, name):
    PS.annotate(fig, PROV, extra=PS.PRELIM); fig.savefig(PLD / name, bbox_inches="tight"); plt.close(fig)


def wr(df, name):
    df.to_csv(SUMD / name, index=False); return df


# =========================================================================================================== load
def load():
    T = pd.read_parquet(SPD / "spine_harmonization" / "official_ncdelta" / "event_flags_and_table.parquet"); T = T[T.tpc_box].copy()
    T["has_file"] = T.file_index.notna()
    rows = pd.read_parquet(RAW / "rows.parquet"); tp = pd.read_parquet(RAW / "tprot.parquet"); ev = pd.read_parquet(RAW / "evt.parquet")
    for d in (rows, tp, ev):
        d["file_index"] = d.file_index.astype(int)
    T["match_cand"] = np.where(T.A_matched.astype(bool), T.match_cand_nu, np.nan); T["sel_cand"] = np.where(T.A_final.astype(bool), T.sel_nu_index, np.nan)
    Tk = T.dropna(subset=["file_index"]).copy(); Tk["file_index"] = Tk.file_index.astype(int)
    E = Tk.merge(ev[K + ["signal_nu_idx", "tmatch_partner_lists_ok", "n_kine_rows"]].rename(columns=dict(signal_nu_idx="sig_nu_scan")), on=K, how="left", validate="1:1")
    assert E.sig_nu_scan.notna().all() and len(E) == 12426
    sig = E.set_index(K).sig_nu_scan
    rows = PT.classify_rows(rows, sig, ratio=0.5)
    rows["ke"] = rows.kine_energy_particle; rows["is_p"] = rows.kine_particle_type == 2212; rows["inc3"] = rows.kine_energy_included == 3
    rows = rows.merge(E[K + ["match_cand", "sel_cand", "truth35", "delta_label", "A_matched", "A_final", "A_candidate"]], on=K, how="left")
    rows["in_match"] = rows.cand == rows.match_cand; rows["in_final"] = rows.cand == rows.sel_cand
    tp["is_signal"] = tp.t_nu.values == pd.MultiIndex.from_frame(tp[K]).map(lambda k: sig.get(k, -99)).to_numpy()
    tp["primary"] = tp.t_proc == PT.PRIMARY_PROCESS         # Geant4 process 0 = generator primary (post-FSI); validated against the baseline truth multiplicities
    tp["ke"] = tp.t_ke
    return T, E, rows, tp, ev


def reco_count(rows, which, thr, mask=None):
    """# rows typed 2212 with KE > thr in the evaluated candidate (``which`` = 'match' or 'final'), per event key (file_index, ev)."""
    m = rows.is_p & (rows.ke > thr) & rows["in_" + which]
    if mask is not None:
        m &= mask
    return rows[m].groupby(K).size()


def baseline_check(E, rows):
    """The proton rows reproduce the baseline reco proton counts (``match_np35`` / ``sel_np35``) exactly: nothing was re-selected."""
    out = {}
    for which, col, sel in (("match", "match_np35", E.A_matched.astype(bool)), ("final", "sel_np35", E.A_final.astype(bool))):
        c = reco_count(rows, which, BASE_THR).reindex(pd.MultiIndex.from_frame(E[sel][K])).fillna(0).to_numpy()
        base = E[sel][col].to_numpy()
        out[which] = dict(events=int(sel.sum()), mismatches=int((c != base).sum()))
    SUMMARY["baseline_reproduction"] = out; assert all(v["mismatches"] == 0 for v in out.values()), out
    return out


# =========================================================================================================== row taxonomy / quality / purity
def taxonomy_block(rows, E):
    rp = rows[rows.is_p]
    T1 = rows.groupby("origin").size().rename("all_rows").to_frame().join(rp.groupby("origin").size().rename("proton_rows")).join(rp[rp.ke > BASE_THR].groupby("origin").size().rename("proton_rows_ke35")).reindex(PT.ROW_CLASSES).fillna(0).astype(int)
    T1["frac_proton_rows_ke35"] = T1.proton_rows_ke35 / T1.proton_rows_ke35.sum(); T1 = T1.reset_index(); wr(T1, "row_origin_taxonomy.csv")
    d = rp[(rp.ke > BASE_THR) & (rp.origin == "signal_nonproton_misidentified")].groupby("d_sub").size().rename("n").reset_index(); wr(d, "row_origin_D_subtypes_ke35.csv")
    um = rows[rows.origin == "unmatched"].groupby(["unmatched_reason"]).size().rename("n_rows").reset_index(); umf = rp[rp.origin == "unmatched"].groupby("unmatched_reason").size().rename("n_proton_rows").reset_index(); wr(um.merge(umf, how="outer").fillna(0), "row_unmatched_reasons.csv")
    SUMMARY["rows"] = dict(total=len(rows), proton_typed=len(rp), proton_typed_ke35=int((rp.ke > BASE_THR).sum()), proton_typed_shower=int((rp.kine_particle_is_shower == 1).sum()), proton_typed_inc3=int(rp.inc3.sum()),
                           proton_ke35_inc3=int((rp.inc3 & (rp.ke > BASE_THR)).sum()), no_level1_object=int((~rows.has_match_row.astype(bool)).sum()), unreadable_partner_events=int((~E.tmatch_partner_lists_ok.astype(bool)).sum()),
                           class_counts_all=T1.set_index("origin").all_rows.to_dict(), class_counts_proton_ke35=T1.set_index("origin").proton_rows_ke35.to_dict())
    # sensitivity of G to the ratio
    sens = []
    for ratio in (None, 0.33, 0.5, 0.75, 1.0):
        c = PT.classify_rows(rp[rp.ke > BASE_THR], E.set_index(K).sig_nu_scan, ratio=ratio).origin.value_counts()
        sens.append(dict(ratio=("off" if ratio is None else ratio), **{k: int(c.get(k, 0)) for k in PT.ROW_CLASSES}))
    wr(pd.DataFrame(sens), "row_origin_G_ratio_sensitivity.csv")
    return T1


def quality_block(rows):
    rp = rows[rows.is_p & (rows.ke > BASE_THR)].copy()
    rp["sep"] = rp.p1_iou_n.fillna(0) - rp.p2_iou_n.fillna(0)
    rp["hc"] = (rp.p1_iou_n >= 0.5) & (rp.mutual == 1) & (rp.sep >= 0.2)      # validation-only diagnostic subset
    rp["ov_agrees"] = np.where(rp.ov_dom_tid.notna() & (rp.nmatch > 0), rp.ov_dom_tid == rp.p1_tid, np.nan)
    recs = []
    for o, g in list(rp.groupby("origin")) + [("ALL", rp)]:
        q = lambda s, p: float(np.nanpercentile(s.dropna(), p)) if s.notna().any() else np.nan
        recs.append(dict(origin=o, n=len(g), iou_n_med=q(g.p1_iou_n, 50), iou_n_p16=q(g.p1_iou_n, 16), iou_n_p84=q(g.p1_iou_n, 84), iou_q_med=q(g.p1_iou_q, 50), iou2_n_med=q(g.p2_iou_n, 50), sep_med=q(g.sep, 50),
                         sep_p16=q(g.sep, 16), nmatch_mean=float(g.nmatch.mean()), mutual_frac=float((g.mutual == 1).mean()), hc_frac=float(g.hc.mean()), ov_dominant_agrees_frac=float(g.ov_agrees.mean()), n_ov=int(g.ov_agrees.notna().sum())))
    Q = wr(pd.DataFrame(recs), "row_association_quality_proton_ke35.csv")
    hcc = rp.groupby("origin").hc.agg(["sum", "size"]).rename(columns=dict(sum="n_hc", size="n")).reset_index(); wr(hcc, "row_hc_subset_by_origin.csv")
    comp = rp[rp.hc].origin.value_counts().reindex(PT.ROW_CLASSES).fillna(0).astype(int); SUMMARY["quality"] = dict(hc_rows=int(rp.hc.sum()), rows=len(rp), composition_hc=comp.to_dict(), ov_agree=float(rp.ov_agrees.mean()), n_ov=int(rp.ov_agrees.notna().sum()))
    # disagreement between point-IoU top partner and charge-dominant overlap truth: which one of the two is a proton, per class (diagnostic only)
    dis = rp[rp.ov_agrees == 0].origin.value_counts().rename("n_disagree").reset_index().rename(columns=dict(index="origin")); wr(dis, "row_topmatch_vs_overlap_disagreement.csv")
    return Q


def purity_block(rows):
    pops = {"all_candidates": rows, "signal_matched_candidate": rows[rows.in_match], "final_selected_candidate": rows[rows.in_final]}
    recs = []
    group_defs = {"all": lambda d: pd.Series("all", index=d.index), "truth_topology": lambda d: d.truth35.map(TL), "delta": lambda d: d.delta_label,
                  "row_kind": lambda d: np.where(d.kine_particle_is_shower == 1, np.where(d.inc3, "shower_included3", "shower_included1"), "track")}
    for pn, d0 in pops.items():
        for thr in THR_SCAN:
            d = d0[d0.is_p & (d0.ke > thr)]
            for gn, f in group_defs.items():
                g = f(d)
                ct = pd.crosstab(g, d.origin).reindex(columns=list(PT.ROW_CLASSES), fill_value=0)
                for gv, r in ct.iterrows():
                    n = int(r.sum()); rec = dict(population=pn, thr_mev=thr, group=gn, value=gv, n_rows=n, **{k: int(r[k]) for k in PT.ROW_CLASSES})
                    rec["frac_signal_primary"] = r["true_primary_signal_proton"] / n if n else np.nan; lo, hi = cp(r["true_primary_signal_proton"], n)[1:] if n else (np.nan, np.nan); rec["lo68"] = lo; rec["hi68"] = hi
                    rec["frac_any_proton_truth"] = (r["true_primary_signal_proton"] + r["geant4_secondary_proton"] + r["other_neutrino_proton"]) / n if n else np.nan
                    recs.append(rec)
    P = wr(pd.DataFrame(recs), "reco_proton_purity_scan.csv")
    SUMMARY["purity"] = {pn: {str(t): P[(P.population == pn) & (P.thr_mev == t) & (P.group == "all")].iloc[0].drop(["population", "group", "value"]).to_dict() for t in THR_SCAN} for pn in pops}
    return P


def purity_figure(P):
    fig, ax = PS.figure(1, 3, size=(16, 4.4))
    for a, pn in zip(ax[0], ("all_candidates", "signal_matched_candidate", "final_selected_candidate")):
        d = P[(P.population == pn) & (P.group == "all")].sort_values("thr_mev"); bottom = np.zeros(len(d)); x = np.arange(len(d))
        for k in PT.ROW_CLASSES:
            fr = d[k].to_numpy() / d.n_rows.to_numpy(); a.bar(x, fr, bottom=bottom, color=CLS_COL[k], edgecolor="k", linewidth=0.3, label=CLS_SHORT[k]); bottom += fr
        a.set_xticks(x); a.set_xticklabels([f">{t}" for t in d.thr_mev]); a.set_xlabel("reco proton-row KE threshold [MeV] (diagnostic scan, not an optimisation)"); a.set_title(pn.replace("_", " ") + f"  (n = {int(d.n_rows.iloc[2]):,} rows at >35)", fontsize=9); a.set_ylim(0, 1)
    ax[0][0].set_ylabel("fraction of reco proton rows"); ax[0][2].legend(fontsize=6, ncol=1, loc="center left", bbox_to_anchor=(1.0, 0.5)); savefig(fig, "reco_proton_truth_composition_vs_threshold.png")


# =========================================================================================================== true protons: accounting, efficiency, KE response
def attach_origin(tpp):
    """Join the per-proton GENIE origin (decay_proton / fsi_created / ambiguous / not_from_decay / unknown) to the signal primary protons by event and nearest KE (<= 0.5 MeV, one-to-one)."""
    f = OUT / "proton_origin_per_proton.parquet"
    tpp["origin_class"] = "unlinked"; tpp["origin_dke"] = np.nan
    if not f.exists():
        return tpp
    g = pd.read_parquet(f); g = g[g.origin != "__event_marker__"]
    gg = {k: v.sort_values("ke_mev").reset_index(drop=True) for k, v in g.groupby(["run", "subrun", "evt"])}
    for k, idx in tpp.groupby(["run", "subrun", "evt"]).groups.items():
        genie = gg.get(k)
        if genie is None:
            continue
        used = set()
        for i in sorted(idx, key=lambda j: tpp.at[j, "ke"]):
            d = (genie.ke_mev - tpp.at[i, "ke"]).abs()
            for j in d.sort_values().index:
                if j in used:
                    continue
                if d[j] < 0.5:
                    used.add(j); tpp.at[i, "origin_class"] = genie.at[j, "origin"]; tpp.at[i, "origin_dke"] = d[j]
                break
    return tpp


def truth_protons(E, rows, tp):
    tpp = tp[tp.is_signal & tp.primary].copy()
    # the same particle can appear twice under two track ids (T_truth_track and T_truth_pf numbering); keep one per (event, KE within 1e-3 MeV), preferring the T_truth_track entry
    tpp["_k"] = tpp.ke.round(3); tpp["_pref"] = (~tpp.t_in_tt).astype(int); n0 = len(tpp)
    tpp = tpp.sort_values(K + ["_k", "_pref"]).drop_duplicates(K + ["_k"]).drop(columns=["_k", "_pref"]).reset_index(drop=True); SUMMARY["truth_proton_dedup_removed"] = int(n0 - len(tpp))
    tpp = tpp.merge(E[K + ["run", "subrun", "evt", "truth35", "delta_label", "vtx_x", "vtx_y", "vtx_z", "match_cand", "sel_cand", "A_candidate", "A_matched", "A_final", "n_p35_prim", "n_p50"]], on=K, how="left")
    tpp["p_gev"] = np.sqrt(tpp.pf_start_px ** 2 + tpp.pf_start_py ** 2 + tpp.pf_start_pz ** 2); tpp["cos_beam"] = tpp.pf_start_pz / tpp.p_gev
    tpp = attach_origin(tpp)
    # accounting against the baseline truth multiplicities (post-FSI primary protons of the signal interaction)
    chk = {}
    for thr, col in ((35, "n_p35_prim"), (50, "n_p50")):
        c = tpp[tpp.ke > thr].groupby(K).size().reindex(pd.MultiIndex.from_frame(E[K])).fillna(0).to_numpy()
        chk[thr] = dict(events=len(E), mismatches=int((c != E[col].to_numpy()).sum()), protons=int(c.sum()), baseline_protons=int(E[col].sum()))
    SUMMARY["truth_proton_accounting"] = chk
    # reconstruction state of every signal primary proton above 35 MeV with respect to the signal-matched candidate
    st = PT.true_proton_states(tpp[tpp.ke > BASE_THR].reset_index(drop=True), rows, E.set_index(K).match_cand)
    st["state_ext"] = np.where(st.state != "no_signal_candidate", st.state, np.where(~st.A_candidate.astype(bool), "no_candidate_in_event", "candidate_not_signal_matched"))
    # rows (signal-matched candidate) with the proton as top partner: best proton-row KE
    tr = rows[rows.in_match & (rows.p1_tid >= 0)][K + ["p1_tid", "ke", "is_p", "inc3", "kine_particle_is_shower", "mutual", "p1_iou_n", "origin"]].rename(columns=dict(p1_tid="trackid"))
    g = tr.merge(st[K + ["trackid"]], on=K + ["trackid"])
    agg = g[g.is_p].groupby(K + ["trackid"]).agg(best_proton_row_ke=("ke", "max"), n_proton_rows=("ke", "size"), best_iou_n=("p1_iou_n", "max")).reset_index()
    st = st.merge(agg, on=K + ["trackid"], how="left"); st["n_proton_rows"] = st.n_proton_rows.fillna(0).astype(int)
    return tpp, st


def eff_rows(st, thr, by, label):
    d = st[st.ke > thr]
    out = []
    for b, g in d.groupby(by, observed=True):
        n = len(g); fnd = g.state.isin(["proton_row_single", "proton_row_multiple", "matched_nonproton_row"]).sum(); pid = g.state.isin(["proton_row_single", "proton_row_multiple"]).sum(); pas = (g.best_proton_row_ke > thr).sum()
        rec = dict(variable=label, bin=str(b), thr_mev=thr, n_true=n)
        for nm, k in (("row_found", fnd), ("proton_id", pid), ("threshold_passing", pas)):
            e, lo, hi = cp(k, n); rec.update({nm: k, nm + "_eff": e, nm + "_lo68": lo, nm + "_hi68": hi})
        out.append(rec)
    return out


def efficiency_block(st):
    S = st.copy()
    S["ke_bin"] = pd.cut(S.ke, KE_BINS + [1e9][:0], right=False); S["cos_bin"] = pd.cut(S.cos_beam, [-1, -0.5, 0, 0.5, 0.8, 1.0001]); S["z_bin"] = pd.cut(S.vtx_z, [0, 100, 200, 300, 400, 500])
    S["x_bin"] = pd.cut(S.vtx_x.abs(), [0, 50, 100, 150, 200]); S["y_bin"] = pd.cut(S.vtx_y.abs(), [0, 50, 100, 150, 200]); S["all"] = "all"; S["truth_topology"] = S.truth35.map(TL)
    S["orig"] = S.origin_class; S["state_all"] = S.state_ext
    recs = []
    for thr in (35, 50):
        for by, lab in (("all", "all"), ("ke_bin", "true_KE"), ("cos_bin", "cos_theta_beam"), ("z_bin", "vertex_z"), ("x_bin", "abs_vertex_x"), ("y_bin", "abs_vertex_y"), ("orig", "proton_origin"), ("delta_label", "delta"), ("truth_topology", "truth_topology")):
            recs += eff_rows(S, thr, by, lab)
    EF = wr(pd.DataFrame(recs), "true_proton_efficiency.csv")
    stc = (S.groupby("state_ext").size().rename("n_ke35").to_frame().join(S[S.ke > 50].groupby("state_ext").size().rename("n_ke50")).fillna(0).astype(int).reset_index()); wr(stc, "true_proton_reco_state.csv")
    stk = S.groupby(["ke_bin", "state_ext"], observed=True).size().rename("n").reset_index(); stk["ke_bin"] = stk.ke_bin.astype(str); wr(stk, "true_proton_reco_state_vs_ke.csv")
    sto = S.groupby(["orig", "state_ext"]).size().rename("n").reset_index(); wr(sto, "true_proton_reco_state_by_origin.csv")
    SUMMARY["true_proton_states"] = stc.set_index("state_ext").to_dict()
    SUMMARY["true_proton_efficiency_all"] = {int(t): EF[(EF.variable == "all") & (EF.thr_mev == t)].iloc[0].to_dict() for t in (35, 50)}
    return EF


def efficiency_figure(EF):
    fig, ax = PS.figure(2, 2, size=(12, 8.2)); cols = {"row_found": "#0072B2", "proton_id": "#D55E00", "threshold_passing": "#009E73"}; lab = {"row_found": "reco row found (any type)", "proton_id": "row typed proton", "threshold_passing": "typed proton and reco KE > 35 MeV"}
    for a, var, xl in ((ax[0][0], "true_KE", "true proton KE bin [MeV]"), (ax[0][1], "cos_theta_beam", "cos(theta to beam)"), (ax[1][0], "vertex_z", "true vertex z [cm]"), (ax[1][1], "proton_origin", "proton origin")):
        d = EF[(EF.variable == var) & (EF.thr_mev == 35)]; d = d[d.bin != "unlinked"] if var == "proton_origin" else d; x = np.arange(len(d))
        for j, k in enumerate(cols):
            PS.eff_errorbar(a, d[k + "_lo68"], d[k + "_hi68"], d[k + "_eff"], d[k + "_lo68"], d[k + "_hi68"], label=lab[k], color=cols[k], offset=0.08 * (j - 1)) if False else a.errorbar(x + 0.08 * (j - 1), d[k + "_eff"], yerr=[d[k + "_eff"] - d[k + "_lo68"], d[k + "_hi68"] - d[k + "_eff"]], fmt="o-", color=cols[k], label=lab[k], ms=4, lw=1)
        a.set_xticks(x); a.set_xticklabels([f"{b}\n(n={n})" for b, n in zip(d.bin.str.replace(", ", "-").str.strip("[)(]"), d.n_true)], fontsize=6); a.set_xlabel(xl); a.set_ylim(0, 1.02); a.set_ylabel("fraction of true signal primary protons > 35 MeV" if a in (ax[0][0], ax[1][0]) else "")
    ax[0][0].legend(fontsize=7, loc="lower right"); fig.subplots_adjust(hspace=0.45); savefig(fig, "true_proton_reco_efficiency.png")


def resp_stats(g):
    r = g.ke / g.p1_t_ke; q = np.nanpercentile(r, [16, 50, 84]) if len(g) else [np.nan] * 3
    return dict(n=len(g), median_ratio=q[1], p16=q[0], p84=q[2], resolution_68=(q[2] - q[0]) / 2, bias_median_frac=float(np.nanmedian((g.ke - g.p1_t_ke) / g.p1_t_ke)) if len(g) else np.nan)


def response_block(rows, E, tpp):
    A = rows[rows.is_p & rows.in_match & (rows.origin == "true_primary_signal_proton") & rows.p1_t_ke.notna() & (rows.p1_t_ke > BASE_THR)].copy()
    A["hc"] = (A.p1_iou_n >= 0.5) & (A.mutual == 1); A["ke_bin"] = pd.cut(A.p1_t_ke, KE_BINS, right=False)
    A["kind"] = np.where(A.kine_particle_is_shower == 1, np.where(A.inc3, "shower_included3", "shower_included1"), "track"); A["inc_kind"] = np.where(A.inc3, "included==3", "included!=3")
    # origin and delta
    A = A.merge(tpp[K + ["trackid", "origin_class"]].rename(columns=dict(trackid="p1_tid")), on=K + ["p1_tid"], how="left"); A["origin_class"] = A.origin_class.fillna("unlinked")
    recs = []
    for sub, mask in (("all_A_rows", A.index == A.index), ("hc_rows", A.hc)):
        d0 = A[mask]
        for split, col in (("all", None), ("kind", "kind"), ("included", "inc_kind"), ("origin", "origin_class"), ("delta", "delta_label")):
            for sv, d1 in ([("all", d0)] if col is None else d0.groupby(col)):
                for b, d2 in list(d1.groupby("ke_bin", observed=True)) + [("all", d1)]:
                    if len(d2) >= 1:
                        recs.append(dict(subset=sub, split=split, value=sv, ke_bin=str(b), **resp_stats(d2)))
    R = wr(pd.DataFrame(recs), "proton_ke_response.csv")
    SUMMARY["ke_response"] = {s: R[(R.subset == s) & (R.split == "all") & (R.ke_bin == "all")].iloc[0].to_dict() for s in ("all_A_rows", "hc_rows")}
    return A, R


def response_figure(A, R):
    fig, ax = PS.figure(1, 3, size=(16, 4.6)); h = A[A.hc]
    a = ax[0][0]; hb = a.hist2d(np.log10(h.p1_t_ke), np.log10(h.ke.clip(lower=1)), bins=[np.linspace(np.log10(35), np.log10(1000), 40), np.linspace(0, 3.2, 40)], cmap="viridis", cmin=1); a.plot([1.5, 3], [1.5, 3], "w--", lw=0.8)
    a.set_xlabel("log10 true proton KE [MeV]"); a.set_ylabel("log10 reco row KE [MeV]"); a.set_title(f"high-confidence rows (n={len(h):,}); dashed y=x", fontsize=9)
    a = ax[0][1]
    for kind, col in (("track", "#0072B2"), ("shower_included1", "#E69F00"), ("shower_included3", "#D55E00")):
        d = R[(R.subset == "hc_rows") & (R.split == "kind") & (R.value == kind) & (R.ke_bin != "all") & (R.n >= 10)]; x = [KE_BINS.index(int(float(b.strip("[)").split(",")[0]))) for b in d.ke_bin]
        a.errorbar(np.array(x) + 0.06 * ["track", "shower_included1", "shower_included3"].index(kind), d.median_ratio, yerr=[d.median_ratio - d.p16, d.p84 - d.median_ratio], fmt="o-", color=col, label=f"{kind} (n={int(d.n.sum()):,})", ms=4, lw=1)
    a.axhline(1, color="k", lw=0.6, ls=":"); a.set_xticks(range(len(KE_BINS) - 1)); a.set_xticklabels([f"{KE_BINS[i]}-{KE_BINS[i+1]}" for i in range(len(KE_BINS) - 1)], fontsize=7); a.set_xlabel("true KE bin [MeV]"); a.set_ylabel("reco / true KE (median, 16-84 %)"); a.legend(fontsize=7); a.set_ylim(0, 2.5)
    a = ax[0][2]
    for o, col in (("decay_proton", "#009E73"), ("fsi_created", "#CC79A7"), ("ambiguous", "#999999")):
        d = R[(R.subset == "hc_rows") & (R.split == "origin") & (R.value == o) & (R.ke_bin != "all") & (R.n >= 10)]
        if len(d):
            x = [KE_BINS.index(int(float(b.strip("[)").split(",")[0]))) for b in d.ke_bin]; a.errorbar(np.array(x) + 0.06 * ["decay_proton", "fsi_created", "ambiguous"].index(o), d.median_ratio, yerr=[d.median_ratio - d.p16, d.p84 - d.median_ratio], fmt="o-", color=col, label=f"{o} (n={int(d.n.sum()):,})", ms=4, lw=1)
    a.axhline(1, color="k", lw=0.6, ls=":"); a.set_xticks(range(len(KE_BINS) - 1)); a.set_xticklabels([f"{KE_BINS[i]}-{KE_BINS[i+1]}" for i in range(len(KE_BINS) - 1)], fontsize=7); a.set_xlabel("true KE bin [MeV]"); a.legend(fontsize=7); a.set_ylim(0, 2.5)
    savefig(fig, "proton_ke_response.png")


# =========================================================================================================== migration: exact accounting of 1p->0p and 0p->1p; multiplicity response
def _n_true(E, thr):
    return E["n_p35_prim"] if thr == 35 else E["n_p50"]


def stage_ladder(E, thr, nt):
    """Where do the events of truth multiplicity ``nt`` (0, 1, >=2) go?  Exact accounting of the 12,427 TPC-box events."""
    n = _n_true(E, thr); sel = (n == nt) if nt < 2 else (n >= 2)
    d = E[sel]
    return dict(total=len(d), production_missing=int((~d.has_file).sum()), no_candidate=int((d.has_file & ~d.A_candidate.astype(bool)).sum()), candidate_not_signal_matched=int((d.A_candidate.astype(bool) & ~d.A_matched.astype(bool)).sum()),
                signal_matched=int(d.A_matched.astype(bool).sum()), final_selected=int(d.A_final.astype(bool).sum()))


def reco_counts_for(E, rows, thr):
    out = {}
    for which, flag in (("match", "A_matched"), ("final", "A_final")):
        c = reco_count(rows, which, thr).reindex(pd.MultiIndex.from_frame(E[K])).fillna(0).astype(int).to_numpy()
        out[which] = np.where(E[flag].astype(bool).to_numpy(), c, -1)
    return out


def one_p_to_zero_p(E, rows, tpp, thr):
    rc = reco_counts_for(E, rows, thr); n = _n_true(E, thr); recs = []; ev_rows = []
    P = tpp[tpp.ke > thr].drop_duplicates(K)[K + ["trackid", "q_readout", "origin_class", "ke"]]       # truth-1p events have exactly one such proton
    for which, label in (("match", "A_signal_matched_candidate"), ("final", "B_final_selected")):
        sel = (n == 1) & (rc[which] == 0); ev = E[sel][K + ["delta_label"]].merge(P, on=K, how="left")
        rr = rows[rows["in_" + which]]
        top = rr[rr.p1_tid >= 0].merge(ev[K + ["trackid"]], left_on=K + ["p1_tid"], right_on=K + ["trackid"])
        anyp = rows[rows.p1_tid >= 0].merge(ev[K + ["trackid"]], left_on=K + ["p1_tid"], right_on=K + ["trackid"])
        sub = pd.concat([rr[rr[c] >= 0].rename(columns={c: "tid"})[K + ["tid"]] for c in ("p2_tid", "p3_tid")]).merge(ev[K + ["trackid"]], left_on=K + ["tid"], right_on=K + ["trackid"])[K].drop_duplicates()
        isp = top[top.is_p].groupby(K).size().rename("n_top_proton"); ntop = top.groupby(K).size().rename("n_top")
        amb = top[top.origin == "ambiguous_multiple_truth"].groupby(K).size().rename("n_top_amb")
        oth = anyp.merge(top[K + ["cand", "row"]].drop_duplicates(), on=K + ["cand", "row"], how="left", indicator=True); oth = oth[oth._merge == "left_only"].groupby(K).size().rename("n_other_cand_rows")
        toptype = top.sort_values("ke", ascending=False).groupby(K).first().kine_particle_type.rename("top_type")
        ev = ev.merge(ntop.reset_index(), on=K, how="left").merge(isp.reset_index(), on=K, how="left").merge(oth.reset_index(), on=K, how="left").merge(amb.reset_index(), on=K, how="left").merge(toptype.reset_index(), on=K, how="left")
        ev["in_sub"] = pd.MultiIndex.from_frame(ev[K]).isin(pd.MultiIndex.from_frame(sub)); ev = ev.fillna({"n_top": 0, "n_top_proton": 0, "n_other_cand_rows": 0, "n_top_amb": 0})
        reason = np.select([ev.n_top_proton > 0, ev.n_top > 0, ev.n_other_cand_rows > 0, ev.in_sub, ev.q_readout > 0],
                           ["proton_row_reco_KE_below_threshold", "matched_row_nonproton_type", "proton_in_other_candidate", "proton_only_subdominant_partner", "proton_never_a_row__charge_deposited"], "proton_never_a_row__no_readout_charge")
        ev["reason"] = reason; ev["stage"] = label; ev["thr_mev"] = thr
        ev["top_type_label"] = np.where(ev.reason == "matched_row_nonproton_type", ev.top_type.map({11: "shower_typed_electron", 13: "typed_muon", 211: "typed_pion", 0: "typed_unknown"}).fillna("other"), "")
        vc = ev.reason.value_counts()
        for rname in ("proton_row_reco_KE_below_threshold", "matched_row_nonproton_type", "proton_in_other_candidate", "proton_only_subdominant_partner", "proton_never_a_row__charge_deposited", "proton_never_a_row__no_readout_charge"):
            recs.append(dict(stage=label, thr_mev=thr, reason=rname, n=int(vc.get(rname, 0)), n_truth1p_events_at_stage=int(((n == 1) & (rc[which] >= 0)).sum()), n_reco0p=int(len(ev)),
                             n_Delta0=int(((ev.reason == rname) & (ev.delta_label == "Delta0")).sum()), n_DeltaPlus=int(((ev.reason == rname) & (ev.delta_label == "Delta+")).sum())))
        assert vc.sum() == len(ev)
        ev_rows.append(ev[K + ["stage", "thr_mev", "reason", "top_type_label", "delta_label", "trackid", "ke", "origin_class"]])
        # diagnostic ONLY (baseline unchanged): how many of the truth-1p events with a reco proton would lose it if included==3 rows were not counted
    R = pd.DataFrame(recs); R["frac_of_reco0p"] = R.n / R.groupby("stage").n.transform("sum"); return R, pd.concat(ev_rows)


def zero_p_to_one_p(E, rows, tpp, thr):
    rc = reco_counts_for(E, rows, thr); n = _n_true(E, thr); recs = []; evr = []
    for which, label in (("match", "A_signal_matched_candidate"), ("final", "B_final_selected")):
        sel = (n == 0) & (rc[which] == 1); ev = E[sel][K + ["delta_label"]]
        rr = rows[rows["in_" + which] & rows.is_p & (rows.ke > thr)].merge(ev[K], on=K)
        assert len(rr) == len(ev), (len(rr), len(ev))
        rr = rr.merge(tpp[K + ["trackid", "ke", "origin_class"]].rename(columns=dict(trackid="p1_tid", ke="true_ke_sig", origin_class="true_origin")), on=K + ["p1_tid"], how="left")
        rr["row_kind"] = np.where(rr.kine_particle_is_shower == 1, np.where(rr.inc3, "shower_included3", "shower_included1"), "track")
        lab = rr.origin.copy().astype(object)
        lab[(rr.origin == "true_primary_signal_proton")] = "true_primary_proton_below_truth_threshold__promoted_by_reco"
        rr["reason"] = lab; rr["stage"] = label; rr["thr_mev"] = thr
        for o, g in rr.groupby("reason"):
            recs.append(dict(stage=label, thr_mev=thr, reason=o, n=len(g), n_reco1p=len(rr), n_Delta0=int((g.delta_label == "Delta0").sum()), n_DeltaPlus=int((g.delta_label == "Delta+").sum()), n_track=int((g.row_kind == "track").sum()), n_shower_inc1=int((g.row_kind == "shower_included1").sum()),
                             n_shower_inc3=int((g.row_kind == "shower_included3").sum()), median_reco_ke=float(g.ke.median()), median_true_ke=float(g.p1_t_ke.median()) if g.p1_t_ke.notna().any() else np.nan, d_sub=";".join(f"{k}:{v}" for k, v in g[g.d_sub != ""].d_sub.value_counts().items())))
        evr.append(rr[K + ["stage", "thr_mev", "reason", "row_kind", "ke", "p1_t_ke", "p1_t_pdg", "p1_t_proc", "p1_t_mpdg", "d_sub", "delta_label"]])
        # secondary-proton parentage
        sec = rr[rr.origin == "geant4_secondary_proton"]
        if len(sec):
            recs.append(dict(stage=label, thr_mev=thr, reason="__secondary_parent_pdg__", n=len(sec), n_reco1p=len(rr), d_sub=";".join(f"{k}:{v}" for k, v in sec.p1_t_mpdg.value_counts().items())))
    R = pd.DataFrame(recs); return R, pd.concat(evr)


def multiplicity_matrix(E, rows, thr, which):
    rc = reco_counts_for(E, rows, thr)[which]; sel = rc >= 0; n = _n_true(E, thr).to_numpy()[sel]; r = PT.reco_multiplicity(rc[sel]); t = PT.reco_multiplicity(n)
    M = pd.crosstab(pd.Series(t, name="truth").map({0: "0", 1: "1", 2: "2", 3: "3+"}), pd.Series(r, name="reco").map({0: "0", 1: "1", 2: "2", 3: "3+"})).reindex(index=["0", "1", "2", "3+"], columns=["0", "1", "2", "3+"], fill_value=0)
    return M


def multiplicity_block(E, rows):
    recs = []; mats = {}
    for thr in (35, 50):
        for which, label in (("match", "signal_matched_candidate"), ("final", "final_selected")):
            M = multiplicity_matrix(E, rows, thr, which); mats[(thr, which)] = M
            for t in M.index:
                for r in M.columns:
                    recs.append(dict(thr_mev=thr, stage=label, truth=t, reco=r, n=int(M.loc[t, r]), row_total=int(M.loc[t].sum())))
    MM = wr(pd.DataFrame(recs), "multiplicity_response.csv")
    # closure with the baseline 3x3 (35 MeV, final): truth {0,1,>=2} x reco {0,1,>=2}
    b = mats[(35, "final")]; three = pd.DataFrame({"0": b["0"], "1": b["1"], ">=2": b["2"] + b["3+"]}); three.loc["1"] = three.loc["1"]
    t3 = pd.DataFrame([three.loc["0"], three.loc["1"], three.loc["2"] + three.loc["3+"]], index=["0", "1", ">=2"])
    SUMMARY["multiplicity_3x3_final_35"] = t3.to_dict(); return MM, mats


def ge2p_block(E, rows, st, thr=35):
    """Per truth->=2p event: true protons above threshold, reconstructed (row found), proton-IDed, passing the reco threshold, and the reco multiplicity."""
    n = _n_true(E, thr); ev = E[(n >= 2) & E.A_matched.astype(bool)][K + ["delta_label"]].copy(); ev["n_true"] = _n_true(E, thr)[ev.index].astype(int)
    s = st[(st.ke > thr)]; s = s.assign(found=s.state.isin(["proton_row_single", "proton_row_multiple", "matched_nonproton_row"]), pid=s.state.isin(["proton_row_single", "proton_row_multiple"]), passing=s.best_proton_row_ke > thr)
    g = s.groupby(K)[["found", "pid", "passing"]].sum().reset_index().rename(columns=dict(found="n_row_found", pid="n_proton_id", passing="n_passing"))
    ev = ev.merge(g, on=K, how="left").fillna(0); ev["n_reco_rows_baseline"] = reco_count(rows, "match", thr).reindex(pd.MultiIndex.from_frame(ev[K])).fillna(0).astype(int).to_numpy()
    summ = pd.DataFrame([dict(thr_mev=thr, events=len(ev), true_protons=int(ev.n_true.sum()), row_found=int(ev.n_row_found.sum()), proton_id=int(ev.n_proton_id.sum()), passing=int(ev.n_passing.sum()), reco_rows=int(ev.n_reco_rows_baseline.sum()),
                              mean_true=float(ev.n_true.mean()), mean_reco=float(ev.n_reco_rows_baseline.mean()), frac_all_found=float((ev.n_row_found == ev.n_true).mean()), frac_all_passing=float((ev.n_passing == ev.n_true).mean()))])
    wr(summ, f"ge2p_reconstruction_summary_{thr}.csv"); return ev, summ


def migration_figures(R10, R01, MM):
    fig, ax = PS.figure(1, 2, size=(14, 4.8)); cmap = ["#009E73", "#D55E00", "#E69F00", "#56B4E9", "#CC79A7", "#999999"]
    a = ax[0][0]; d = R10[R10.thr_mev == 35]; stages = list(d.stage.unique()); w = 0.38; reasons = list(d.reason.unique()); bottoms = np.zeros(len(stages)); x = np.arange(len(stages))
    for j, rn in enumerate(reasons):
        v = np.array([d[(d.stage == s) & (d.reason == rn)].frac_of_reco0p.iloc[0] for s in stages]); a.bar(x, v, bottom=bottoms, color=cmap[j], edgecolor="k", linewidth=0.3, label=rn.replace("_", " ")); bottoms += v
    a.set_xticks(x); a.set_xticklabels([f"{s.replace('_', ' ')}\n(n={int(d[d.stage == s].n_reco0p.iloc[0])})" for s in stages], fontsize=8); a.set_ylabel("fraction of truth-1p -> reco-0p events"); a.set_title("truth 1p -> reco 0p, reasons (35 MeV)", fontsize=9); a.legend(fontsize=6, loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2)
    a = ax[0][1]; d = R01[(R01.thr_mev == 35) & (~R01.reason.str.startswith("__"))]; stages = list(d.stage.unique()); order = [k for k in PT.ROW_CLASSES if k in set(d.reason)] + ["true_primary_proton_below_truth_threshold__promoted_by_reco"]; bottoms = np.zeros(len(stages))
    ccol = dict(CLS_COL); ccol["true_primary_proton_below_truth_threshold__promoted_by_reco"] = "#009E73"
    for rn in order:
        v = np.array([(d[(d.stage == s) & (d.reason == rn)].n.sum() / d[d.stage == s].n_reco1p.iloc[0]) if len(d[(d.stage == s) & (d.reason == rn)]) else 0 for s in stages]); a.bar(x, v, bottom=bottoms, color=ccol.get(rn, "#999999"), edgecolor="k", linewidth=0.3, label=CLS_SHORT.get(rn, "sub-threshold true primary promoted")); bottoms += v
    a.set_xticks(x); a.set_xticklabels([f"{s.replace('_', ' ')}\n(n={int(d[d.stage == s].n_reco1p.iloc[0])})" for s in stages], fontsize=8); a.set_ylabel("fraction of truth-0p -> reco-1p events"); a.set_title("truth 0p -> reco 1p, truth origin of the reco proton row (35 MeV)", fontsize=9); a.legend(fontsize=6, loc="upper center", bbox_to_anchor=(0.5, -0.18), ncol=2)
    savefig(fig, "migration_1p_to_0p_and_0p_to_1p.png")
    fig, ax = PS.figure(1, 2, size=(11, 4.8))
    for a, which, ttl in ((ax[0][0], "match", "signal-matched candidate"), (ax[0][1], "final", "final selected")):
        d = MM[(MM.thr_mev == 35) & (MM.stage == ("signal_matched_candidate" if which == "match" else "final_selected"))]; M = d.pivot(index="truth", columns="reco", values="n").reindex(index=["0", "1", "2", "3+"], columns=["0", "1", "2", "3+"]); F = M.div(M.sum(axis=1), axis=0)
        a.imshow(F.values, cmap="Blues", vmin=0, vmax=1)
        for i in range(4):
            for j in range(4):
                a.text(j, i, f"{int(M.values[i, j])}\n{F.values[i, j]*100:.0f}%", ha="center", va="center", fontsize=8, color="w" if F.values[i, j] > 0.5 else "k")
        a.set_xticks(range(4)); a.set_xticklabels(M.columns); a.set_yticks(range(4)); a.set_yticklabels(M.index); a.set_xlabel("reco proton multiplicity (35 MeV)"); a.set_ylabel("truth post-FSI proton multiplicity (35 MeV)"); a.set_title(ttl, fontsize=9)
    savefig(fig, "multiplicity_response_matrix.png")


# =========================================================================================================== vertex anchoring and `other` BDT versus the truth identity of the leading reco proton
LEAD_LABEL = {"true_primary_signal_proton": "true signal primary proton", "geant4_secondary_proton": "Geant4 secondary proton", "other_neutrino_proton": "other-neutrino proton", "signal_nonproton_misidentified": "non-proton row (fake)",
              "other_neutrino_nonproton": "non-proton row (fake)", "cosmic_or_non_neutrino": "non-proton row (fake)", "ambiguous_multiple_truth": "ambiguous truth", "unmatched": "unmatched row"}
LEAD_ORDER = ["true signal primary proton", "Geant4 secondary proton", "non-proton row (fake)", "other-neutrino proton", "ambiguous truth", "unmatched row", "absent (no reco proton > 35 MeV)"]


def leading_proton(E, rows):
    d = rows[rows.is_p & (rows.ke > BASE_THR) & rows.in_match].sort_values("ke", ascending=False).groupby(K).first().reset_index()
    d["lead_class"] = d.origin.map(LEAD_LABEL); d["lead_ke"] = d.ke
    L = E[E.A_matched.astype(bool)][K].merge(d[K + ["lead_class", "lead_ke", "origin", "kine_particle_is_shower", "inc3"]], on=K, how="left"); L["lead_class"] = L.lead_class.fillna(LEAD_ORDER[-1]); return L


def anchoring_block(E, L):
    vg = pd.read_parquet(P9 / "vertex_geometry.parquet", columns=K + ["d_vertex", "anchored5", "truth35", "attached_tagger", "sig_gap"]).drop(columns=["truth35"]).merge(L, on=K, how="inner").merge(E[K + ["truth35"]], on=K)
    recs = []
    for tv, d0 in [("all", vg)] + [(TL[t], g) for t, g in vg.groupby("truth35")]:
        for lc in LEAD_ORDER:
            g = d0[d0.lead_class == lc]; n = len(g); k = int(g.anchored5.sum()); e, lo, hi = cp(k, n)
            recs.append(dict(truth=tv, leading_reco_proton=lc, n=n, anchored=k, frac_anchored=e, lo68=lo, hi68=hi, median_d_vertex_cm=float(g.d_vertex.median()) if n else np.nan, frac_detached_tagger=float((g.sig_gap > 0).mean()) if n else np.nan))
    A = wr(pd.DataFrame(recs), "vertex_anchoring_by_leading_proton_truth.csv"); SUMMARY["anchoring_events"] = len(vg); return A, vg


def other_block(E, L):
    pe = pd.read_parquet(P8 / "population_events.parquet", columns=K + ["survive", "reaches_other", "cls"])
    pe = pe[pe.reaches_other.astype(bool)].merge(L, on=K, how="left").merge(E[K + ["truth35"]], on=K)
    recs = []
    for tv, d0 in [("all", pe)] + [(TL[t], g) for t, g in pe.groupby("truth35")]:
        for lc in LEAD_ORDER:
            g = d0[d0.lead_class == lc]; n = len(g); k = int(g.survive.sum()); e, lo, hi = cp(k, n); recs.append(dict(truth=tv, leading_reco_proton=lc, n=n, survive=k, survival=e, lo68=lo, hi68=hi))
    O = wr(pd.DataFrame(recs), "other_survival_by_leading_proton_truth.csv"); SUMMARY["other_events"] = len(pe); return O, pe


def connection_figures(A, O):
    fig, ax = PS.figure(1, 2, size=(14, 4.8)); cols = {"all": "k", "truth 0p": "#0072B2", "truth 1p": "#D55E00", "truth >=2p": "#009E73"}
    for a, D, col_e, col_lo, col_hi, yl in ((ax[0][0], A, "frac_anchored", "lo68", "hi68", "vertex anchored (|V_reco - V_true| <= 5 cm)"), (ax[0][1], O, "survival", "lo68", "hi68", "frozen `other` BDT survival (events reaching it)")):
        x = np.arange(len(LEAD_ORDER))
        for j, tv in enumerate(cols):
            d = D[D.truth == tv].set_index("leading_reco_proton").reindex(LEAD_ORDER); ok = d.n >= 10
            a.errorbar(x[ok.values] + 0.09 * (j - 1.5), d[col_e][ok], yerr=[(d[col_e] - d[col_lo])[ok], (d[col_hi] - d[col_e])[ok]], fmt="o", color=cols[tv], label=f"{tv}", ms=4, lw=1)
        a.set_xticks(x); a.set_xticklabels([s.replace(" (no reco proton > 35 MeV)", "").replace(" ", "\n", 2) for s in LEAD_ORDER], fontsize=6.5); a.set_ylabel(yl); a.set_ylim(0, 1.02)
    ax[0][0].legend(fontsize=7); ax[0][0].set_title("leading reco proton row, by its truth identity (n >= 10 per point)", fontsize=9); savefig(fig, "anchoring_and_other_by_leading_proton_truth.png")


# =========================================================================================================== Delta-mass ingredient readiness (no M_Delta cut, no physics plot)
M_P = 938.272


def _unit(v):
    n = np.linalg.norm(v); return v / n if n > 0 else np.full(3, np.nan)


def delta_readiness(E, rows, tpp):
    pf = pd.read_parquet(RAW / "delta_pf.parquet"); ev = pd.read_parquet(RAW / "delta_evt.parquet")
    for d in (pf, ev):
        d["file_index"] = d.file_index.astype(int)
    sel = E[E.A_final.astype(bool) & (E.sel_np35 == 1)].merge(ev, on=K, how="inner"); assert len(sel) == 556 == len(ev)
    rr = rows[rows.in_final].set_index(K)
    out = []
    for r in sel.itertuples():
        d = rows[(rows.file_index == r.file_index) & (rows.ev == r.ev) & rows.in_final]
        p = d[d.is_p & (d.ke > BASE_THR)]; assert len(p) == 1
        p = p.iloc[0]
        sh = d[(d.kine_particle_is_shower == 1) & (d.kine_particle_type == 11)]; sh = sh[np.abs(sh.ke - r.shw_sp_energy) <= 1e-3 * max(r.shw_sp_energy, 1e-9)] if r.shw_sp_filled > 0 else sh.iloc[0:0]
        rec = dict(file_index=r.file_index, ev=r.ev, run=r.run, subrun=r.subrun, evt=r.evt, truth35=r.truth35, delta_label=r.delta_label, shw_sp_energy=r.shw_sp_energy, proton_row=int(p.row), proton_ke=float(p.ke), proton_class=p.origin, proton_inc3=bool(p.inc3),
                   proton_is_shower=bool(p.kine_particle_is_shower), proton_iou_n=float(p.p1_iou_n) if pd.notna(p.p1_iou_n) else np.nan, proton_mutual=int(p.mutual) if pd.notna(p.mutual) else -1, photon_row_found=len(sh) >= 1, n_photon_rows_same_energy=len(sh))
        if len(sh):
            s = sh.iloc[0]; rec.update(photon_row=int(s.row), photon_ke=float(s.ke), photon_class=s.origin, photon_top_pdg=int(s.p1_t_pdg) if pd.notna(s.p1_t_pdg) else 0, photon_top_nu_is_signal=bool(s.p1_t_nu == s.sig_nu), photon_iou_n=float(s.p1_iou_n) if pd.notna(s.p1_iou_n) else np.nan,
                                       photon_mutual=int(s.mutual) if pd.notna(s.mutual) else -1)
        # PF-node geometry of the two rows
        g = pf[(pf.file_index == r.file_index) & (pf.ev == r.ev)]
        for who, row in (("photon", rec.get("photon_row")), ("proton", rec["proton_row"])):
            nd = g[(g.kine_index == row) & (g.is_pseudo == 0)] if row is not None else g.iloc[0:0]
            if len(nd):
                n0 = nd.iloc[0]; v = np.array([n0.end_x - n0.start_x, n0.end_y - n0.start_y, n0.end_z - n0.start_z]); rec[f"{who}_pf_found"] = True; rec[f"{who}_dir"] = _unit(v); rec[f"{who}_pf_len_cm"] = float(np.linalg.norm(v))
            else:
                rec[f"{who}_pf_found"] = False; rec[f"{who}_dir"] = np.full(3, np.nan); rec[f"{who}_pf_len_cm"] = np.nan
        # truth directions for the truth-correct rows
        pho_true = np.array([r.photon_px, r.photon_py, r.photon_pz]); rec["photon_true_dir"] = _unit(pho_true)
        tq = tpp[(tpp.file_index == r.file_index) & (tpp.ev == r.ev)]
        if pd.notna(p.p1_tid) and p.p1_tid >= 0:
            t = tq[tq.trackid == p.p1_tid]
            rec["proton_true_dir"] = _unit(t.iloc[0][["pf_start_px", "pf_start_py", "pf_start_pz"]].astype(float).to_numpy()) if len(t) and pd.notna(t.iloc[0].pf_start_px) else np.full(3, np.nan)
        else:
            rec["proton_true_dir"] = np.full(3, np.nan)
        out.append(rec)
    D = pd.DataFrame(out)
    D["photon_truth_correct"] = D.photon_row_found & D.photon_top_nu_is_signal.fillna(False) & (D.photon_top_pdg.fillna(0) == 22)
    D["proton_truth_correct"] = D.proton_class == "true_primary_signal_proton"; D["both_truth_correct"] = D.photon_truth_correct & D.proton_truth_correct
    D["dirs_available"] = D.photon_pf_found & D.proton_pf_found & D.photon_dir.map(lambda v: np.isfinite(v).all()) & D.proton_dir.map(lambda v: np.isfinite(v).all())
    D["all_inputs_available"] = D.photon_row_found & D.dirs_available & (D.shw_sp_energy > 0) & (D.proton_ke > 0)
    cosd = lambda a, b: float(np.clip(np.dot(a, b), -1, 1)) if np.isfinite(a).all() and np.isfinite(b).all() else np.nan
    D["cos_photon_reco_vs_true"] = [cosd(a, b) for a, b in zip(D.photon_dir, D.photon_true_dir)]; D["cos_proton_reco_vs_true"] = [cosd(a, b) for a, b in zip(D.proton_dir, D.proton_true_dir)]
    D["cos_gamma_p_reco"] = [cosd(a, b) for a, b in zip(D.photon_dir, D.proton_dir)]
    Ep = D.proton_ke + M_P; pp = np.sqrt(np.maximum(Ep ** 2 - M_P ** 2, 0)); m2 = M_P ** 2 + 2 * D.photon_ke.fillna(np.nan) * (Ep - pp * D.cos_gamma_p_reco)
    D["m_delta2_defined"] = D.all_inputs_available & np.isfinite(m2) & (m2 > 0)      # availability flag ONLY; no value is used for a cut or a plot
    summ = dict(events=len(D), photon_row_found=int(D.photon_row_found.sum()), photon_truth_correct=int(D.photon_truth_correct.sum()), proton_truth_correct=int(D.proton_truth_correct.sum()), both_truth_correct=int(D.both_truth_correct.sum()),
                dirs_available=int(D.dirs_available.sum()), all_inputs_available=int(D.all_inputs_available.sum()), m_delta2_defined=int(D.m_delta2_defined.sum()),
                both_correct_and_all_inputs=int((D.both_truth_correct & D.all_inputs_available).sum()),
                photon_dir_cos_median=float(D.cos_photon_reco_vs_true[D.photon_truth_correct].median()), photon_dir_cos_gt0p9=float((D.cos_photon_reco_vs_true[D.photon_truth_correct] > 0.9).mean()),
                proton_dir_cos_median=float(D.cos_proton_reco_vs_true[D.proton_truth_correct].median()), proton_dir_cos_gt0p9=float((D.cos_proton_reco_vs_true[D.proton_truth_correct] > 0.9).mean()),
                proton_dir_cos_lt0=float((D.cos_proton_reco_vs_true[D.proton_truth_correct] < 0).mean()), photon_dir_cos_lt0=float((D.cos_photon_reco_vs_true[D.photon_truth_correct] < 0).mean()),
                median_photon_pf_len_cm=float(D.photon_pf_len_cm.median()), median_proton_pf_len_cm=float(D.proton_pf_len_cm.median()))
    SUMMARY["delta_readiness"] = summ
    by = D.groupby("truth35").agg(n=("ev", "size"), both_truth_correct=("both_truth_correct", "sum"), all_inputs=("all_inputs_available", "sum"), m2_defined=("m_delta2_defined", "sum")).reset_index(); by["truth35"] = by.truth35.map(TL)
    wr(by, "delta_mass_readiness_by_truth.csv")
    comp = D.groupby(["photon_truth_correct", "proton_truth_correct"]).size().rename("n").reset_index(); wr(comp, "delta_mass_readiness_truth_correctness.csv")
    wr(pd.DataFrame([summ]).T.reset_index().rename(columns={"index": "quantity", 0: "value"}), "delta_mass_readiness_summary.csv")
    return D


# =========================================================================================================== included==3 diagnostic (baseline untouched) and row-semantics checks
def included_diagnostic(E, rows):
    """DIAGNOSTIC ONLY: reco proton topology if the `kine_energy_included == 3` rows were NOT counted.  The baseline rule keeps counting them; nothing here changes a flag or the final selection (it does not use the proton count)."""
    recs = []; lab = {0: "0p", 1: "1p", 2: ">=2p"}
    for thr in (35, 50):
        for which, flag, label in (("match", "A_matched", "signal_matched_candidate"), ("final", "A_final", "final_selected")):
            sel = E[flag].astype(bool); idx = pd.MultiIndex.from_frame(E[sel][K])
            b = np.minimum(reco_count(rows, which, thr).reindex(idx).fillna(0).astype(int).to_numpy(), 2); a = np.minimum(reco_count(rows, which, thr, mask=~rows.inc3).reindex(idx).fillna(0).astype(int).to_numpy(), 2)
            tr = np.minimum(_n_true(E, thr)[sel].to_numpy(), 2)
            for t in (0, 1, 2):
                for rb in (0, 1, 2):
                    for ra in (0, 1, 2):
                        n = int(((tr == t) & (b == rb) & (a == ra)).sum())
                        if n:
                            recs.append(dict(thr_mev=thr, stage=label, truth=lab[t], reco_baseline=lab[rb], reco_excluding_included3=lab[ra], n=n))
    D = wr(pd.DataFrame(recs), "included3_diagnostic_migration.csv")
    chg = D[D.reco_baseline != D.reco_excluding_included3].groupby(["thr_mev", "stage"]).n.sum().rename("events_changing_topology").reset_index(); tot = D.groupby(["thr_mev", "stage"]).n.sum().rename("events").reset_index(); chg = tot.merge(chg, how="left").fillna(0)
    wr(chg, "included3_diagnostic_summary.csv"); SUMMARY["included3_diagnostic"] = chg.to_dict("records"); return D


def semantics_checks(rows):
    rp = rows[rows.is_p]; recs = []
    def add(q, v, note=""):
        recs.append(dict(quantity=q, value=v, note=note))
    add("rows_total", len(rows)); add("rows_proton_typed", len(rp)); add("proton_typed_shower_rows", int((rp.kine_particle_is_shower == 1).sum())); add("proton_typed_track_rows", int((rp.kine_particle_is_shower == 0).sum()))
    for p, n in rp.kine_particle_pool.value_counts().sort_index().items():
        add(f"proton_typed_pool_{int(p)}", int(n))
    i3 = rows[rows.inc3]
    add("included3_rows", len(i3)); add("included3_rows_in_pool2", int((i3.kine_particle_pool == 2).sum())); add("included3_rows_shower", int((i3.kine_particle_is_shower == 1).sum()))
    add("included3_rows_cluster_not_main", float((i3.kine_particle_cluster_id != i3.main_cluster_id).mean()), "fraction of included==3 rows whose cluster differs from the main cluster of the candidate (source: connection type 3 = other cluster)")
    add("included_not_1_or_3_rows", int((~rows.kine_energy_included.isin([1, 3])).sum()))
    p2 = rows[(rows.kine_particle_pool == 2) & (rows.kine_energy_included == 1)]
    add("pool2_included1_cluster_not_main", float((p2.kine_particle_cluster_id != p2.main_cluster_id).mean()), "pool-2 leftover showers with connection type != 3 (1, 2 or a kept type 4)")
    add("pool0_1_cluster_not_main", float((rows[rows.kine_particle_pool < 2].kine_particle_cluster_id != rows[rows.kine_particle_pool < 2].main_cluster_id).mean()))
    add("proton_typed_included3_fraction", float(rp.inc3.mean())); add("proton_typed_ke35_included3_fraction", float(rp[rp.ke > BASE_THR].inc3.mean()))
    t = rp[rp.ke > BASE_THR]; add("proton_ke35_shower_fraction", float((t.kine_particle_is_shower == 1).mean()))
    add("rows_without_level1_match_object", int((~rows.has_match_row.astype(bool)).sum()), "tiny objects (median KE a few MeV); classified `unmatched` (reason no_level1_object)")
    add("level1_key_duplicates", 0, "asserted zero per event in the scan (evt.dup_l1_key)")
    add("rows_in_unreadable_partner_events", int((~rows.p1_t_nu.notna() & rows.has_match_row.astype(bool) & (rows.nmatch > 0)).sum()), "T_match partner lists inconsistent with their ..length in 16 events; those rows keep nmatch but no partners")
    S = pd.DataFrame(recs); wr(S, "row_semantics_checks.csv")
    k = rp.groupby([rp.kine_particle_pool, rp.kine_particle_is_shower, rp.kine_energy_included]).size().rename("n_proton_typed_rows").reset_index(); wr(k, "proton_rows_by_pool_shower_included.csv")
    SUMMARY["semantics"] = {r.quantity: r.value for r in S.itertuples()}; return S


def row_kind_response_note(A):
    return A.groupby("kind").size().to_dict()


def write_outside_git(rows, tpp, st, evmig, D, E):
    cols = ["file_index", "ev", "cand", "row", "kine_particle_id", "kine_particle_cluster_id", "kine_particle_type", "ke", "kine_energy_included", "kine_particle_pool", "kine_particle_is_shower", "kine_energy_info", "in_match", "in_final", "truth35", "delta_label",
            "nmatch", "mutual", "p1_obj", "p1_tid", "p1_iou_n", "p1_iou_q", "p1_shared_q", "p1_t_pdg", "p1_t_nu", "p1_prim", "p1_t_ke", "p1_t_proc", "p1_t_mpdg", "p2_obj", "p2_tid", "p2_iou_n", "p2_iou_q", "p2_t_pdg", "p2_t_nu", "p3_tid", "p3_iou_n", "p3_iou_q",
            "ov_dom_tid", "ov_dom_q", "ov_q_total", "ov_q_unlabeled", "sig_nu", "origin_top", "origin", "d_sub", "unmatched_reason"]
    rows[rows.is_p][cols].to_parquet(OUT / "reco_proton_rows.parquet", index=False); rows[cols].to_parquet(OUT / "row_matches.parquet", index=False)
    pd.concat([tpp.drop(columns=[c for c in tpp.columns if c in ("state",)]).assign(table="signal_primary_protons")], ignore_index=True).to_parquet(OUT / "truth_protons.parquet", index=False)
    st.drop(columns=["trackid"], errors="ignore").assign(trackid=st.trackid).to_parquet(OUT / "truth_proton_states.parquet", index=False)
    evmig.to_parquet(OUT / "event_migration_reasons.parquet", index=False)
    D2 = D.copy()
    for c in ("photon_dir", "proton_dir", "photon_true_dir", "proton_true_dir"):
        D2[c + "_x"], D2[c + "_y"], D2[c + "_z"] = np.vstack(D2[c].to_numpy()).T; D2 = D2.drop(columns=c)
    D2.to_parquet(OUT / "delta_mass_readiness.parquet", index=False)


def finish(meta_extra):
    meta = dict(git_commit_at_run=subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(), branch=subprocess.run(["git", "-C", str(REPO), "branch", "--show-current"], capture_output=True, text=True).stdout.strip(),
                official_manifest_sha256=sha(REPO / "manifests" / "official_gen2_ncdelta_wc.tsv.gz"), signal_truth_master_sha256=sha(SPD / "official_gen2_ncdelta_master" / "signal_events.parquet"),
                baseline_config_sha256=sha(REPO / "configs" / "baseline_selection.yaml"), event_table_sha256=sha(SPD / "spine_harmonization" / "official_ncdelta" / "event_flags_and_table.parquet"),
                phase9_summary_sha256=sha(REPO / "tables" / "shower_vertex_audit" / "summary.json"), phase9_vertex_geometry_sha256=sha(P9 / "vertex_geometry.parquet"), phase8_population_sha256=sha(P8 / "population_events.parquet"),
                t_match_source_semantics="WIRECELL_TRUTH_MATCH_SEMANTICS.md (2026-11-09): T_match level 1 side 0 = one T_kine row; partners ranked by point IoU (source order); top-3", reco_row_semantics="RECO_PROTON_ROW_SEMANTICS.md (source commit 4b6853d4)",
                raw_sha256={k: sha(RAW / f"{k}.parquet") for k in ("rows", "tprot", "evt", "delta_pf", "delta_seg", "delta_evt")}, origin_per_proton_sha256=sha(OUT / "proton_origin_per_proton.parquet"),
                parameters=dict(base_threshold_mev=BASE_THR, threshold_scan=THR_SCAN, ambiguity_ratio=0.5, hc_iou_n_min=0.5, hc_sep_min=0.2, primary_rule="Geant4 process == 0", origin_link_tolerance_mev=0.5), **meta_extra)
    (OUT / "metadata.json").write_text(json.dumps(meta, indent=1)); SUMMARY["metadata"] = meta
    (SUMD / "summary.json").write_text(json.dumps(SUMMARY, indent=1, default=lambda o: o.item() if hasattr(o, "item") else (o.tolist() if hasattr(o, "tolist") else str(o))))


def main():
    T, E, rows, tp, ev = load(); baseline_check(E, rows)
    SUMMARY["events"] = dict(tpc_box=len(T), with_file=int(T.has_file.sum()), production_missing=int((~T.has_file).sum()), candidate=int(T.A_candidate.astype(bool).sum()), matched=int(T.A_matched.astype(bool).sum()), final=int(T.A_final.astype(bool).sum()))
    SUMMARY["row_uniqueness"] = dict(rows=len(rows), unique_keys=int(len(rows.drop_duplicates(K + ["cand", "row"]))), proton_typed_rows=int(rows.is_p.sum()), proton_typed_unique=int(len(rows[rows.is_p].drop_duplicates(K + ["cand", "row"]))),
                                     origin_assigned=int(rows.origin.notna().sum()), origin_in_taxonomy=int(rows.origin.isin(PT.ROW_CLASSES).sum()), t_match_top_is_first_stored_partner=True)
    SUMMARY["config"] = dict(baseline_config_sha256=sha(REPO / "configs" / "baseline_selection.yaml"))
    semantics_checks(rows); taxonomy_block(rows, E); quality_block(rows); P = purity_block(rows); purity_figure(P)
    tpp, st = truth_protons(E, rows, tp); EF = efficiency_block(st); efficiency_figure(EF)
    A, R = response_block(rows, E, tpp); response_figure(A, R)
    ladders = []
    R10, R01, evm = [], [], []
    for thr in (35, 50):
        for nt in (0, 1, 2):
            ladders.append(dict(thr_mev=thr, truth_multiplicity=("0", "1", ">=2")[nt], **stage_ladder(T, thr, nt)))
        a, e1 = one_p_to_zero_p(E, rows, tpp, thr); b, e2 = zero_p_to_one_p(E, rows, tpp, thr); R10.append(a); R01.append(b); evm += [e1, e2]
    wr(pd.DataFrame(ladders), "event_stage_ladder.csv"); R10 = wr(pd.concat(R10), "migration_truth1p_to_reco0p.csv"); R01 = wr(pd.concat(R01), "migration_truth0p_to_reco1p.csv")
    top_types = pd.concat([x for x in evm if "top_type_label" in x.columns]); wr(top_types[top_types.reason == "matched_row_nonproton_type"].groupby(["stage", "thr_mev", "top_type_label"]).size().rename("n").reset_index(), "migration_truth1p_to_reco0p_nonproton_types.csv")
    MM, mats = multiplicity_block(E, rows); ev2, _ = ge2p_block(E, rows, st, 35); ge2p_block(E, rows, st, 50); migration_figures(R10, R01, MM)
    L = leading_proton(E, rows); Aa, vg = anchoring_block(E, L); O, pe = other_block(E, L); connection_figures(Aa, O)
    included_diagnostic(E, rows); D = delta_readiness(E, rows, tpp)
    evmig = pd.concat([x.assign(table=("1p_to_0p" if "top_type_label" in x.columns else "0p_to_1p")) for x in evm], ignore_index=True)
    write_outside_git(rows, tpp, st, evmig, D, E); finish({})
    SUMMARY_KEYS = list(SUMMARY); print("done", SUMMARY_KEYS)


if __name__ == "__main__":
    main()
