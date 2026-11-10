#!/usr/bin/env python
"""SPINE-compatible TRUTH comparison view on the official Gen2 NC-Delta sample + the SAME frozen Wire-Cell numerator (COMPARISON MODE; nothing is tuned).

    source env/setup_eaf.sh
    python scripts/spine_truth_scan.py scan && python scripts/spine_truth_scan.py merge        # once
    python scripts/spine_harmonization.py tables        # event tables (filter box) -> $SP_DATA/spine_harmonization/official_ncdelta/
    python scripts/spine_reco_included_sensitivity.py   # optional: included == 3 policy sensitivity (selected events only)
    python scripts/spine_harmonization.py report        # ladder, cross-tabs, efficiencies, migration, waterfall, differential plots, summaries

Only the TRUTH DENOMINATOR changes. The numerator is exactly the validated frozen baseline decision (``A_final``) of policy ``any`` and ``first`` of the official baseline.
Outputs outside Git: $SP_DATA/spine_harmonization/official_ncdelta/ ; compact summary: tables/spine_harmonization/ ; figures: plots/spine_harmonization/.
"""
from __future__ import annotations
import hashlib, json, os, subprocess, sys, warnings
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd, yaml
from scipy import stats
from sbnd_single_photon import differential as DF, exclusive_signal as X, plotstyle as PS, selection as SEL, spine_def as SD
import matplotlib.pyplot as plt

SPD = Path(os.environ["SP_DATA"]); OUT = SPD / "spine_harmonization" / "official_ncdelta"; PLD = REPO / "plots" / "spine_harmonization"; SUMD = REPO / "tables" / "spine_harmonization"
for d in (OUT, PLD, SUMD):
    d.mkdir(parents=True, exist_ok=True)
RSE = ["run", "subrun", "evt"]; SUMMARY: dict = {}
SCHEMA = "spine-harmonization-1.0"
PROV = "official Gen2 EX_ncdeltarad | SAME frozen Wire-Cell selection, DIFFERENT truth denominator | NOT a Wire-Cell vs SPINE comparison"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def git_commit():
    return subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()


def eff(mask, col, tab):
    k = int((mask & tab[col].to_numpy(bool)).sum()); n = int(mask.sum()); f, l, h = X.binom_ci(k, n)
    return dict(numerator=k, denominator=n, efficiency=f, lo68=l, hi68=h)


# ---------------------------------------------------------------------------------------------------------------- stage 1: event tables of the filter box
def tables():
    cfg = SEL.load_config(); T = SPD / "analysis_tables" / "official_gen2_ncdelta"; B = SPD / "official_signal_baseline"
    ev = pd.read_parquet(T / "events.parquet"); ca = pd.read_parquet(T / "candidates.parquet")
    arr = pd.read_parquet(B / "signal_joined_filter_box.parquet"); mis = pd.read_parquet(B / "signal_missing_filter_box.parquet")
    tab = DF.build_event_table(arr, mis, ev, ca, cfg, None, "any"); tf = DF.build_event_table(arr, mis, ev, ca, cfg, None, "first")
    tab = tab.merge(tf[RSE + ["A_final"]].rename(columns={"A_final": "A_final_first"}), on=RSE, how="left", validate="one_to_one")
    assert len(tab) == 13773 and int((~tab.arrived).sum()) == 1 and int(tab.A_final_first.sum()) == 1120 and int(tab.A_final.sum()) == 1172, (len(tab), tab.A_final.sum(), tab.A_final_first.sum())
    tab.to_parquet(OUT / "event_table_filter_box_any.parquet", index=False)
    print("filter-box event table", tab.shape, "final any", int(tab.A_final.sum()), "first", int(tab.A_final_first.sum()))


# ---------------------------------------------------------------------------------------------------------------- stage 2: report
def load_all():
    tab = pd.read_parquet(OUT / "event_table_filter_box_any.parquet")
    m = pd.read_parquet(SPD / "official_gen2_ncdelta_master" / "signal_events.parquet")
    st = pd.read_parquet(OUT / "spine_truth.parquet").rename(columns={"ev": "flat_ev"})      # the flatCAF event index must not collide with the merged-CAF (file_index, ev) key
    te = pd.read_parquet(SPD / "differential_efficiency" / "official_ncdelta" / "truth_extra.parquet")[RSE + ["photon_px", "photon_py", "photon_pz"]]
    assert len(st) == len(m) == len(tab) == 13773
    st = st.merge(m[RSE + ["vtx_x", "vtx_y", "vtx_z", "delta_pdg", "n_true_protons", "truth_cat", "in_active_tpc", "in_filter_box", "resnum", "photon_energy_mev", "nu_energy_gev"]], on=RSE, validate="one_to_one")
    fl = SD.build_flags(st)
    t = st.drop(columns=[c for c in st.columns if c.startswith("p_")]).merge(fl, on=RSE, validate="one_to_one")
    assert (t.n_p35_prim == t.n_true_protons).all(), "35 MeV proton count from the new scan disagrees with the signal master"
    assert (t.nu_resnum == t.resnum).all()
    t = SD.masks(t)
    keep = RSE + ["file_index", "ev", "arrived", "wc_valid", "A_candidate", "A_n20mev", "A_bdt_evaluable", "A_numu", "A_other", "A_ncpi0", "A_nue", "A_n20br1", "A_final", "A_final_first", "first_fail",
                  "A_matched", "match_reco_cat", "sel_reco_cat", "sel_nu_index", "match_cand_nu", "sel_lead_proton_ke_mev", "match_lead_proton_ke_mev", "sel_np35", "match_np35", "match_passes_final"]
    t = t.merge(tab[keep], on=RSE, validate="one_to_one").merge(te, on=RSE, validate="one_to_one")
    t["cos_theta_beam"] = t.photon_pz / np.sqrt(t.photon_px ** 2 + t.photon_py ** 2 + t.photon_pz ** 2)
    t["tpc_box"] = t.in_active_tpc.astype(bool)
    t["truth35"] = np.minimum(t.n_p35_prim, 2)
    t["delta_label"] = np.where(t.delta_pdg == 2114, "Delta0", "Delta+")
    return t


def main_report():
    t = load_all(); t.drop(columns=["first_fail"]).to_parquet(OUT / "event_flags_and_table.parquet", index=False)
    SUMMARY["denominators"] = {c: int(t[c].sum()) for c in ["nc_delta_ancestry", "spine_resnum_1232", "spine_resnum_delta", "spine_fv", "spine_containment", "spine_one_photon_25", "spine_no_e_25", "spine_no_mu_25",
                                                          "spine_no_charged_pi_25", "spine_genie_final_state", "spine_genie_record_strict", "spine_technote_threshold", "spine_technote_strict",
                                                          "spine_technote_strict_record", "spine_source_signal", "spine_source_signal_veto2026", "spine_truth_signal", "spine_truth_0p50", "spine_truth_Np50", "tpc_box",
                                                          "cont_literal", "cont_gdml", "cont_flag", "veto2026"]}
    SUMMARY["checks"] = dict(n_events=len(t), missing_event_in_table=int((~t.arrived).sum()), missing_event_in_spine_truth_signal=int(((~t.arrived) & t.spine_truth_signal).sum()),
                             sum_final_any_filter_box=int(t.A_final.sum()), sum_final_first_filter_box=int(t.A_final_first.sum()), tpc_final_any=int((t.A_final & t.tpc_box).sum()),
                             spine_fv_inside_tpc_box=bool((~t.spine_fv | t.tpc_box).all()), ancestry_all_true=bool(t.nc_delta_ancestry.all()),
                             n_p35_scan_equals_master=bool((t.n_p35_prim == t.n_true_protons).all()))
    L = SD.denominator_ladder(t); L.to_csv(OUT / "denominator_ladder.csv", index=False); L.to_csv(SUMD / "denominator_ladder.csv", index=False); SUMMARY["ladder"] = L.round(4).to_dict("records")

    # ---- Task 8: current TPC box vs SPINE FV
    reg = {"in both (TPC box and SPINE FV)": t.tpc_box & t.spine_fv, "current-only (TPC box, not SPINE FV)": t.tpc_box & ~t.spine_fv, "SPINE-only (SPINE FV, not TPC box)": ~t.tpc_box & t.spine_fv,
           "neither (filter box, not TPC box, not SPINE FV)": ~t.tpc_box & ~t.spine_fv}
    rows = []
    for k, m in reg.items():
        m = np.asarray(m, bool)
        for pol, col in (("any", "A_final"), ("first", "A_final_first")):
            rows.append(dict(region=k, policy=pol, **eff(m, col, t)))
        rows.append(dict(region=k, policy="candidate", **eff(m, "A_candidate", t)))
    R = pd.DataFrame(rows); R.to_csv(OUT / "tpc_box_vs_spine_fv.csv", index=False); SUMMARY["tpc_vs_fv"] = R.round(4).to_dict("records")

    # ---- Task 9: 35 vs 50 MeV truth topology
    ct = {}
    for name, d in (("harmonized (spine_truth_signal)", t[t.spine_truth_signal]), ("TPC box (loose, current)", t[t.tpc_box]), ("filter box (all official signal)", t)):
        x = pd.crosstab(d.truth35.map({0: "35: 0p", 1: "35: 1p", 2: "35: >=2p"}), d.n_p50.clip(upper=1).map({0: "50: 0p50", 1: "50: Np50"}))
        x = x.reindex(index=["35: 0p", "35: 1p", "35: >=2p"], columns=["50: 0p50", "50: Np50"]).fillna(0).astype(int); ct[name] = x
        x.to_csv(OUT / f"crosstab_35_vs_50_{name.split()[0]}.csv")
        # extra migration: 1p35 -> 0p50, >=2p35 -> exactly 1 proton above 50 vs >=2
    h = t[t.spine_truth_signal]
    SUMMARY["crosstab_35_vs_50"] = {k: v.to_dict("index") for k, v in ct.items()}
    SUMMARY["migration_35_to_50"] = dict(truth1p35_to_0p50=int(((h.truth35 == 1) & (h.n_p50 == 0)).sum()), truth1p35_total=int((h.truth35 == 1).sum()),
                                         truth_ge2p35_to_1p50=int(((h.truth35 == 2) & (h.n_p50 == 1)).sum()), truth_ge2p35_to_0p50=int(((h.truth35 == 2) & (h.n_p50 == 0)).sum()), truth_ge2p35_total=int((h.truth35 == 2).sum()),
                                         truth0p35_is_0p50=bool(((h.truth35 == 0) & (h.n_p50 == 0)).sum() == (h.truth35 == 0).sum()),
                                         topology_fraction_0p50=float((h.n_p50 == 0).mean()), topology_fraction_Np50=float((h.n_p50 >= 1).mean()),
                                         topology_fraction_35_0p=float((h.truth35 == 0).mean()), topology_fraction_35_1p=float((h.truth35 == 1).mean()), topology_fraction_35_ge2p=float((h.truth35 == 2).mean()))
    fig, ax = PS.figure(1, 2, size=(10, 3.6)); e = np.arange(0, 125, 5.0)
    for a, (nm, d) in zip(ax[0], (("harmonized denominator", h), ("loose TPC-box denominator", t[t.tpc_box]))):
        v = d.lead_p_ke.dropna(); a.hist(v, bins=np.arange(20, 105, 5.0), color="#0072B2", histtype="stepfilled", alpha=0.6)
        for xv, lab in ((35, "35 MeV (current)"), (50, "50 MeV (SPINE)")):
            a.axvline(xv, color="k", ls=":" if xv == 35 else "--", lw=1)
        a.set_xlabel("leading true proton KE [MeV]"); a.set_ylabel("events / 5 MeV"); a.set_title(nm + "  (dotted 35, dashed 50 MeV)", fontsize=9)
    fig.tight_layout(); PS.annotate(fig, PROV, extra="threshold migration view; not an optimisation"); fig.savefig(PLD / "leading_proton_ke_35_75.png", bbox_inches="tight"); plt.close(fig)

    # ---- Task 10: frozen WC efficiency on the harmonized denominators
    defs = {"loose official, filter box (13,773)": np.ones(len(t), bool), "loose official, provisional TPC box (current baseline)": t.tpc_box.to_numpy(),
            "SPINE FV only": t.spine_fv.to_numpy(), "A spine_technote_threshold": t.spine_technote_threshold.to_numpy(), "B spine_technote_strict = HARMONIZED ALL": t.spine_truth_signal.to_numpy(),
            "harmonized 0p50": t.spine_truth_0p50.to_numpy(), "harmonized Np50": t.spine_truth_Np50.to_numpy(), "B' strict (literal GENIE record)": t.spine_technote_strict_record.to_numpy(),
            "spine_source_signal (Delta resnum set)": t.spine_source_signal.to_numpy(), "spine_source_signal + neutrino2026 veto": t.spine_source_signal_veto2026.to_numpy()}
    # loose TPC-box classes at 35 MeV for context
    for k, nm in ((0, "loose TPC box, truth 0p (35 MeV)"), (1, "loose TPC box, truth 1p (35 MeV)"), (2, "loose TPC box, truth >=2p (35 MeV)")):
        defs[nm] = (t.tpc_box & (t.truth35 == k)).to_numpy()
    rows = []
    for nm, m in defs.items():
        for pol, col in (("any", "A_final"), ("first", "A_final_first")):
            rows.append(dict(denominator_set=nm, policy=pol, **eff(m, col, t)))
    E = pd.DataFrame(rows); E.to_csv(OUT / "wc_efficiency_on_harmonized.csv", index=False); E.to_csv(SUMD / "wc_efficiency_on_harmonized.csv", index=False); SUMMARY["wc_efficiency"] = E.round(5).to_dict("records")

    # ---- sensitivity of the harmonized efficiency to the individually ambiguous pieces (each variant changes ONE piece of the headline mask)
    thr = (t.spine_one_photon_25 & t.spine_no_e_25 & t.spine_no_mu_25 & t.spine_no_charged_pi_25); base = t.nc_delta_ancestry & thr & t.spine_genie_final_state
    var = {"HEADLINE spine_truth_signal": t.spine_truth_signal, "containment: literal (all non-nu primaries incl. neutrons, 5 cm)": base & t.spine_fv & t.cont_literal,
           "containment: flatCAF contained flag (zero margin)": base & t.spine_fv & t.cont_flag, "containment: GDML active box instead of SPINE box": base & t.spine_fv & t.cont_gdml,
           "no containment requirement": base & t.spine_fv, "FV with medulla docstring margins (25/25/30/50)": base & t.spine_fv_docstring & t.spine_containment,
           "Delta(1232) only (resnum == 0)": t.spine_truth_signal & t.spine_resnum_1232, "Delta-type resnum set (source)": t.spine_truth_signal & t.spine_resnum_delta,
           "literal GENIE record final state instead of the thresholded rule": t.spine_technote_strict_record, "+ neutrino2026 veto (approx.)": t.spine_truth_signal & t.veto2026,
           "A: without any final-state restriction": t.spine_technote_threshold}
    rows = []
    for nm, m in var.items():
        m = np.asarray(m, bool); d = dict(variant=nm, n=int(m.sum()), n_0p50=int((m & (t.n_p50 == 0)).sum()), n_Np50=int((m & (t.n_p50 >= 1)).sum()))
        for pol, col in (("any", "A_final"), ("first", "A_final_first")):
            e_ = eff(m, col, t); d[f"eff_{pol}"] = e_["efficiency"]; d[f"lo_{pol}"] = e_["lo68"]; d[f"hi_{pol}"] = e_["hi68"]
        d["eff_any_0p50"] = eff(m & (t.n_p50 == 0).to_numpy(), "A_final", t)["efficiency"]; d["eff_any_Np50"] = eff(m & (t.n_p50 >= 1).to_numpy(), "A_final", t)["efficiency"]
        rows.append(d)
    V = pd.DataFrame(rows); V.to_csv(OUT / "sensitivity_variants.csv", index=False); V.to_csv(SUMD / "sensitivity_variants.csv", index=False); SUMMARY["sensitivity_variants"] = V.round(5).to_dict("records")

    # ---- region x proton-class matrix: separates the region/definition effect from the 35 -> 50 MeV category effect
    rows = []
    for rn, rm in (("loose TPC box", t.tpc_box.to_numpy(bool)), ("harmonized", t.spine_truth_signal.to_numpy(bool))):
        for cn, cm in (("all", np.ones(len(t), bool)), ("35: 0p", (t.truth35 == 0).to_numpy()), ("35: 1p", (t.truth35 == 1).to_numpy()), ("35: >=2p", (t.truth35 == 2).to_numpy()),
                       ("50: 0p50", (t.n_p50 == 0).to_numpy()), ("50: Np50", (t.n_p50 >= 1).to_numpy())):
            for pol, col in (("any", "A_final"), ("first", "A_final_first")):
                rows.append(dict(region=rn, proton_class=cn, policy=pol, **eff(rm & cm, col, t)))
    CM = pd.DataFrame(rows); CM.to_csv(OUT / "region_x_protonclass_efficiency.csv", index=False); CM.to_csv(SUMD / "region_x_protonclass_efficiency.csv", index=False); SUMMARY["region_x_class"] = CM.round(5).to_dict("records")

    # ---- Task 11/12: 50 MeV reco projection and truth->reco migration
    sel = t.A_final.to_numpy(bool); has_m = t.A_matched.to_numpy(bool)
    t["reco50_sel"] = SD.reco50_category(t.sel_lead_proton_ke_mev, sel)
    t["reco50_match"] = SD.reco50_category(t.match_lead_proton_ke_mev, has_m)
    sens = OUT / "reco_included_sensitivity.parquet"
    if sens.exists():
        sd = pd.read_parquet(sens); t = t.merge(sd[["file_index", "ev", "n50_inc1", "n50_all", "n35_inc1", "n35_all"]], on=["file_index", "ev"], how="left")
        t["reco50_sel_inc1"] = np.where(sel, np.where(t.n50_inc1 >= 1, "Np50", "0p50"), "none")
        SUMMARY["included_sensitivity"] = dict(n_selected=int(sel.sum()), baseline_equals_stored_lead_ke=bool(((t.n50_all[sel] >= 1) == (t.sel_lead_proton_ke_mev[sel] > 50)).all()),
                                               n_selected_changed_0p50_Np50=int(((t.reco50_sel != t.reco50_sel_inc1) & sel).sum()))
    mig_rows = []
    for dname, dm in (("harmonized", t.spine_truth_signal.to_numpy(bool)),):
        for stage, col in (("signal_matched_candidate", "reco50_match"), ("final_frozen_selection_any", "reco50_sel")):
            for tc, tm in (("truth_0p50", t.n_p50 == 0), ("truth_Np50", t.n_p50 >= 1)):
                m = dm & tm.to_numpy(bool); n = int(m.sum())
                for rc in ("0p50", "Np50", "none"):
                    k = int((m & (t[col] == rc).to_numpy()).sum()); f, l, h = X.binom_ci(k, n)
                    mig_rows.append(dict(denominator=dname, stage=stage, truth=tc, reco=rc if rc != "none" else "no selected/matched candidate", count=k, row_total=n, fraction=f, lo68=l, hi68=h))
    if sens.exists():
        dm = t.spine_truth_signal.to_numpy(bool)
        for tc, tm in (("truth_0p50", t.n_p50 == 0), ("truth_Np50", t.n_p50 >= 1)):
            m = dm & tm.to_numpy(bool); n = int(m.sum())
            for rc in ("0p50", "Np50", "none"):
                k = int((m & (t.reco50_sel_inc1 == rc).to_numpy()).sum()); f, l, h = X.binom_ci(k, n)
                mig_rows.append(dict(denominator="harmonized", stage="final_SENSITIVITY_included==1_rows_only", truth=tc, reco=rc if rc != "none" else "no selected/matched candidate", count=k, row_total=n, fraction=f, lo68=l, hi68=h))
    chk = SD.migration_50(t.n_p50, t.spine_truth_signal, t.reco50_sel); assert int(chk.to_numpy().sum()) == int(t.spine_truth_signal.sum())
    M = pd.DataFrame(mig_rows); M.to_csv(OUT / "migration_50mev.csv", index=False); M.to_csv(SUMD / "migration_50mev.csv", index=False); SUMMARY["migration_50"] = M.round(4).to_dict("records")
    # for comparison: the loose 35-MeV matrix on the harmonized denominator and on the TPC box
    rows = []
    for nm, dm in (("harmonized", t.spine_truth_signal.to_numpy(bool)), ("TPC box", t.tpc_box.to_numpy(bool))):
        for tc in (0, 1, 2):
            m = dm & (t.truth35 == tc).to_numpy(); n = int(m.sum())
            for rc, nmr in ((0, "reco_0p"), (1, "reco_1p"), (2, "reco_ge2p")):
                k = int((m & sel & (t.sel_reco_cat == rc).to_numpy()).sum()); rows.append(dict(denominator=nm, truth35=tc, reco35=nmr, count=k, row_total=n, fraction=k / n if n else np.nan))
            rows.append(dict(denominator=nm, truth35=tc, reco35="not_selected", count=int((m & ~sel).sum()), row_total=n, fraction=float((m & ~sel).sum() / n) if n else np.nan))
    pd.DataFrame(rows).to_csv(OUT / "migration_35mev_on_same_denominators.csv", index=False); SUMMARY["migration_35"] = rows

    # ---- Task 13: waterfall of the frozen WC efficiency under successive definition changes
    cum = np.ones(len(t), bool); wf = []
    seq = [("loose official signal, filter box", np.ones(len(t), bool)), ("provisional TPC box (current baseline)", t.tpc_box), ("SPINE FV", t.spine_fv), ("+ containment (approx.)", t.spine_containment),
           ("+ photon topology (one photon > 25 MeV)", t.spine_one_photon_25), ("+ charged-particle veto (e/mu/pi+- > 25 MeV)", t.spine_no_e_25 & t.spine_no_mu_25 & t.spine_no_charged_pi_25),
           ("+ strict final state (only photons/nucleons above threshold)", t.spine_genie_final_state)]
    for i, (nm, m) in enumerate(seq):
        # the first two rows are alternative starting regions; from 'SPINE FV' on the steps are cumulative
        if i >= 2:
            cum = cum & np.asarray(m, bool) if i > 2 else np.asarray(m, bool)
            mm = cum
        else:
            mm = np.asarray(m, bool)
        wf.append(dict(step=nm, **{f"any_{k}": v for k, v in eff(mm, "A_final", t).items()}, first_eff=eff(mm, "A_final_first", t)["efficiency"]))
    for nm, m in (("harmonized 0p50 (50 MeV categories)", t.spine_truth_0p50), ("harmonized Np50 (50 MeV categories)", t.spine_truth_Np50)):
        wf.append(dict(step=nm, **{f"any_{k}": v for k, v in eff(m.to_numpy(bool), "A_final", t).items()}, first_eff=eff(m.to_numpy(bool), "A_final_first", t)["efficiency"]))
    W = pd.DataFrame(wf); W.to_csv(OUT / "waterfall.csv", index=False); W.to_csv(SUMD / "waterfall.csv", index=False); SUMMARY["waterfall"] = W.round(5).to_dict("records")
    fig, ax = PS.figure(1, 1, size=(8.5, 4.2)); a = ax[0][0]; x = np.arange(len(W)); y = W.any_efficiency.to_numpy()
    a.errorbar(x, y, yerr=[y - W.any_lo68, W.any_hi68 - y], fmt="o-", color="k"); a.set_xticks(x); a.set_xticklabels(W.step, rotation=35, ha="right", fontsize=7); a.set_ylabel("frozen WC final efficiency (policy any)"); a.set_ylim(bottom=0)
    fig.tight_layout(); PS.annotate(fig, PROV, extra="denominator-definition effects only"); fig.savefig(PLD / "waterfall_definition_effect.png", bbox_inches="tight"); plt.close(fig)

    # ---- Task 14: differential trends, loose TPC box vs harmonized
    bins = DF.load_bins()["variables"]; sub = {"loose TPC box": t[t.tpc_box].copy(), "harmonized": t[t.spine_truth_signal].copy()}
    sub["harmonized Np50"] = t[t.spine_truth_Np50].copy(); sub["harmonized 0p50"] = t[t.spine_truth_0p50].copy()
    for k, d in sub.items():
        d["lead_proton_ke_mev"] = d.lead_p_ke; d["photon_energy_mev"] = d.photon_energy_mev; d["vtx_z"] = d.vtx_z
        d["truth_cat"] = 0; d["delta_pdg"] = d.delta_pdg
    stages = [("final", "A_final")]
    diff_tables = []
    var_edges = {"photon_energy_mev": bins["photon_energy_mev"]["edges"], "cos_theta_beam": bins["cos_theta_beam"]["edges"], "vtx_z": bins["vtx_z"]["edges"], "lead_proton_ke_mev": [50, 75, 100, 150, 200, 300, 500, 2000]}
    labels = {"photon_energy_mev": "True photon energy [MeV]", "cos_theta_beam": "cos(theta_gamma, +z beam axis)", "vtx_z": "True vertex z [cm]", "lead_proton_ke_mev": "Leading true proton KE [MeV]"}
    fig, ax = PS.figure(1, 4, size=(17, 3.6))
    for a, (var, edges) in zip(ax[0], var_edges.items()):
        sets = [("loose TPC box", "#D55E00"), ("harmonized", "#000000")] + ([("harmonized Np50", "#0072B2")] if var == "lead_proton_ke_mev" else [("harmonized 0p50", "#009E73"), ("harmonized Np50", "#0072B2")])
        for k, (nm, col) in enumerate(sets):
            d = sub[nm]
            if var == "lead_proton_ke_mev":
                d = d[d.lead_p_ke > 50] if nm != "loose TPC box" else d[d.lead_p_ke > 35]
            e = DF.efficiency_in_bins(d, var, edges, ["all"], stages); e["denominator_set"] = nm; e["variable"] = var; diff_tables.append(e)
            c = e[(e.kind == "bin") & (e.denominator >= 10)]
            PS.eff_errorbar(a, c.lo, c.hi, c.efficiency, c.lo68, c.hi68, label=nm, color=col, offset=0.08 * (k - 1))
        a.set_xlabel(labels[var]); a.set_ylabel("frozen WC final efficiency (any)"); a.set_ylim(bottom=0)
        if var == "photon_energy_mev":
            a.legend(fontsize=7)
    fig.tight_layout(); PS.annotate(fig, PROV, extra="bins with <10 events not drawn; lead-KE panel: events with a proton above the plotted threshold"); fig.savefig(PLD / "differential_loose_vs_harmonized.png", bbox_inches="tight"); plt.close(fig)
    D = pd.concat(diff_tables, ignore_index=True); D.to_csv(OUT / "differential_loose_vs_harmonized.csv", index=False)
    # shape comparison: ratio harmonized / loose efficiency across photon-energy bins and the slope
    def trend(var):
        a = D[(D.variable == var) & (D.denominator_set == "loose TPC box") & (D.kind == "bin")].set_index("bin"); b = D[(D.variable == var) & (D.denominator_set == "harmonized") & (D.kind == "bin")].set_index("bin")
        j = a[["lo", "hi", "efficiency"]].join(b[["efficiency", "denominator"]], rsuffix="_h", how="inner"); j = j[j.denominator >= 10]
        return dict(bins=j.round(4).reset_index().to_dict("records"), ratio_first_last=float(j.efficiency_h.iloc[-1] / j.efficiency_h.iloc[0]) if len(j) > 1 and j.efficiency_h.iloc[0] > 0 else None,
                    loose_ratio_first_last=float(j.efficiency.iloc[-1] / j.efficiency.iloc[0]) if len(j) > 1 and j.efficiency.iloc[0] > 0 else None)
    SUMMARY["differential"] = {v: trend(v) for v in ("photon_energy_mev", "cos_theta_beam", "vtx_z")}
    # Np50 lead-KE efficiency
    SUMMARY["differential_np50_lead_ke"] = D[(D.variable == "lead_proton_ke_mev") & (D.denominator_set == "harmonized Np50") & (D.kind == "bin")][["lo", "hi", "denominator", "numerator", "efficiency"]].round(4).to_dict("records")

    # ---- metadata and summary
    meta = dict(schema_version=SCHEMA, signal_definition_schema="spine-signal-definition-1.0", git_commit_at_run=git_commit(), official_manifest_sha256=sha(REPO / "manifests" / "official_gen2_ncdelta_wc.tsv.gz"),
                truth_master_sha256=sha(SPD / "official_gen2_ncdelta_master" / "signal_events.parquet"), differential_truth_scan_sha256=sha(SPD / "differential_efficiency" / "official_ncdelta" / "truth_extra.parquet"),
                spine_truth_scan_sha256=sha(OUT / "spine_truth.parquet"), signal_definition_config_sha256=sha(REPO / "configs" / "spine_signal_definition.yaml"),
                baseline_selection_sha256=sha(REPO / "configs" / "baseline_selection.yaml"), medulla_source=dict(repo="github.com/seokjuchung/medulla", branch="feature/schung_NCDelta", commit="4048f930aa7679cebbcf9f9b11aa33f21f350f05"))
    (OUT / "metadata.json").write_text(json.dumps(meta, indent=1)); SUMMARY["metadata"] = meta
    (SUMD / "summary.json").write_text(json.dumps(SUMMARY, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    print("report written; denominators:", {k: SUMMARY["denominators"][k] for k in ("spine_fv", "spine_technote_threshold", "spine_technote_strict", "spine_source_signal", "spine_source_signal_veto2026")})


if __name__ == "__main__":
    {"tables": tables, "report": main_report}[sys.argv[1]]()
