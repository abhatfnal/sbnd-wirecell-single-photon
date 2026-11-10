#!/usr/bin/env python
"""Official Gen2 NC-Delta baseline: efficiencies by truth class and Delta type, truth->reco migration (rows normalised, binomial errors), comparison with the
117-event natural-BNB-CV rehearsal, migration-aware yields, beam-neutrino-only S/B and the DESCRIPTIVE Task-13 diagnostics. Frozen baseline only; nothing is tuned.

    source env/setup_eaf.sh && python scripts/run_official_signal_baseline.py official --skip-register --skip-build --region active_tpc --exposure-pot 1e20
    (same for --region filter_box) && python scripts/analyze_official_signal_baseline.py

Writes tables/official_signal/official_baseline/{summary.json, *.csv}. Total background / purity / significance are NOT produced (cosmic normalisation unresolved).
"""
from __future__ import annotations
import json, os, sys, warnings
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); sys.path.insert(0, str(REPO / "scripts")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from scipy import stats
from sbnd_single_photon import exclusive_signal as X, selection as SEL, signal_yield as Y, prediction as P
import run_official_signal_baseline as RB

SPD = Path(os.environ["SP_DATA"]); TAB = REPO / "tables" / "official_signal"; OUT = TAB / "official_baseline"; OUT.mkdir(parents=True, exist_ok=True)
CLS = {0: "0p", 1: "1p", 2: ">=2p"}; DELTA = {2114: "Delta0", 2214: "Delta+"}
REG = ("filter_box", "active_tpc")


def ci(k, n):
    v, lo, hi = X.binom_ci(int(k), int(n)); return float(v), float(lo), float(hi)


def eff_rows(t, label):
    rows = []
    groups = [("total", np.ones(len(t), bool))] + [(CLS[c], (t.truth_cat == c).values) for c in (0, 1, 2)] + [(n, (t.delta_pdg == p).values) for p, n in DELTA.items()]
    for g, m in groups:
        k = int(t.A_final[m].sum()); n = int(m.sum()); v, lo, hi = ci(k, n)
        rows.append(dict(policy=label, group=g, selected=k, N_signal_truth=n, efficiency=v, lo68=lo, hi68=hi))
    return rows


def migration(t, rows_mask, reco_col, with_unsel):
    """truth class (rows) x reco channel (0p,1p,>=2p, unselected/unreconstructed) with row fractions and exact errors."""
    out = []
    for tc in (0, 1, 2):
        m = rows_mask & (t.truth_cat == tc).values; n = int(m.sum())
        cnt = [int((m & (t[reco_col] == r).values).sum()) for r in (0, 1, 2)]
        cnt.append(n - sum(cnt)) if with_unsel else cnt.append(0)
        for j, name in enumerate(["reco 0p", "reco 1p", "reco >=2p", "unselected/unreconstructed"]):
            v, lo, hi = ci(cnt[j], n) if n else (np.nan,) * 3
            out.append(dict(truth=CLS[tc], reco=name, N=cnt[j], row_total=n, fraction=v, lo68=lo, hi68=hi))
    return pd.DataFrame(out)


def cond_survival(cf_all):
    """Conditional survival of each stage relative to the previous one, per truth group (descriptive; order-dependent by construction)."""
    st = list(dict.fromkeys(cf_all.stage)); rows = []
    for g in ("all", "0p", "1p", ">=2p"):
        prev = None
        for s in st:
            n = int(cf_all[(cf_all.stage == s) & (cf_all.group == g)].N.iloc[0])
            if prev is not None and s != "truth_denominator":
                v, lo, hi = ci(n, prev) if prev else (np.nan,) * 3
                rows.append(dict(group=g, stage=s, N_in=prev, N_out=n, survival=v, lo68=lo, hi68=hi))
            prev = n
    return pd.DataFrame(rows)


def main():
    cfg = SEL.load_config(); T = SPD / "analysis_tables" / "official_gen2_ncdelta"; base = SPD / "official_signal_baseline"
    events = pd.read_parquet(T / "events.parquet"); cands = pd.read_parquet(T / "candidates.parquet")
    units = pd.read_parquet(SPD / "official_gen2_ncdelta_master" / "units.parquet")
    pot_sig = float(units[units.flatcaf_status == "flatcaf_available"].unit_pot.sum())
    summary = dict(label="official Gen2 NC-Delta baseline (frozen configs/baseline_selection.yaml; proton threshold 35 MeV provisional; no FV)", pot_signal_sample=pot_sig, regions={})
    tabs = {}
    for r in REG:
        arrived = pd.read_parquet(base / f"signal_joined_{r}.parquet"); missing = pd.read_parquet(base / f"signal_missing_{r}.parquet")
        rep, ta, tf, acc = RB.run_report(arrived, missing, events, cands, cfg, label="official_gen2_ncdelta", region=r, pot_signal=pot_sig, exposure_pot=1e20)
        tabs[r] = (rep, ta, tf)
        d = OUT / r; d.mkdir(exist_ok=True)
        eff = pd.DataFrame(eff_rows(ta, "any") + eff_rows(tf, "first")); eff.to_csv(d / "efficiency_by_truth_and_delta.csv", index=False)
        for p, tt in (("any", ta), ("first", tf)):
            has = (tt.match_cand_nu >= 0).values; fin = tt.A_final.astype(bool).values
            views = {"A_all_denominator_events": (np.ones(len(tt), bool), "match_reco_cat", True),
                     "B_with_signal_matched_candidate": (has, "match_reco_cat", False),
                     "C_matched_candidate_bdt_evaluable": (has & tt.match_bdt_evaluable.astype(bool).values, "match_reco_cat", False),
                     "D_final_selected": (fin, "sel_reco_cat", False)}
            for name, (mask, col, wu) in views.items():
                migration(tt, mask, col, wu).to_csv(d / f"migration_{p}_{name}.csv", index=False)
        rep["cutflow_any"].pipe(cond_survival).to_csv(d / "conditional_survival_any.csv", index=False)
        ex = rep["expected_yield"]
        R = (np.array([rep["truth_class"][CLS[c]] for c in (0, 1, 2)], float) / pot_sig) * 1e20
        summary["regions"][r] = dict(N_signal_truth=rep["n_truth"], arrived=rep["arrived"], missing=rep["missing"], wc_valid=rep["wc_valid"],
                                     truth_class=rep["truth_class"], delta=rep["delta"], final_any=rep["final_any"]["total"], final_first=rep["final_first"]["total"],
                                     signal_rate_before_reco_per_1e20POT=dict(total=float(R.sum()), by_truth_class={CLS[c]: float(R[c]) for c in (0, 1, 2)}),
                                     expected_yield_any_per_1e20POT=ex)
        # first-failure by Delta type (any)
        ff = []
        for p, n in DELTA.items():
            m = ta.delta_pdg == p
            for reason, k in ta[m].first_fail_A.value_counts().items():
                ff.append(dict(group=n, reason=reason, N=int(k), of=int(m.sum()), fraction=k / int(m.sum())))
        pd.DataFrame(ff).to_csv(d / "first_failure_any_by_delta.csv", index=False)

    # --------------------------------------------------------------------------- natural-CV rehearsal comparison (TPC box)
    rh = TAB / "rehearsal_natural_bnb_cv"; rs = json.load(open(rh / "summary.json")); rep, ta, tf = tabs["active_tpc"]
    cmpr = {}
    k, n = rs["final_any"]["total"], rs["n_truth"]; p_off = ta.A_final.mean()
    cmpr["overall_any"] = dict(rehearsal=f"{k}/{n}", official=f"{int(ta.A_final.sum())}/{len(ta)}", p_binom_two_sided=float(stats.binomtest(k, n, p_off).pvalue),
                               p_fisher=float(stats.fisher_exact([[k, n - k], [int(ta.A_final.sum()), len(ta) - int(ta.A_final.sum())]])[1]))
    reh_eff = pd.read_csv(rh / "efficiency.csv"); reh_any = reh_eff[reh_eff.policy == "any"].set_index("truth_class")
    for c in (0, 1, 2):
        m = (ta.truth_cat == c); ko, no = int(ta[m].A_final.sum()), int(m.sum()); kr, nr = int(reh_any.loc[CLS[c], "selected"]), int(reh_any.loc[CLS[c], "truth"])
        cmpr[f"truth_{CLS[c]}_any"] = dict(rehearsal=f"{kr}/{nr}", official=f"{ko}/{no}", p_binom_two_sided=float(stats.binomtest(kr, nr, ko / no).pvalue))
    # Delta charge and truth-class mix
    cmpr["delta0_fraction"] = dict(rehearsal=f"{rs['delta']['Delta0']}/{rs['n_truth']}", official=f"{rep['delta']['Delta0']}/{rep['n_truth']}",
                                   p_binom_two_sided=float(stats.binomtest(rs["delta"]["Delta0"], rs["n_truth"], rep["delta"]["Delta0"] / rep["n_truth"]).pvalue))
    ro = np.array([rep["truth_class"][CLS[c]] for c in (0, 1, 2)], float); rr = np.array([rs["truth_class"][CLS[c]] for c in (0, 1, 2)], float)
    chi = stats.chisquare(rr, ro / ro.sum() * rr.sum()); cmpr["truth_class_mix"] = dict(rehearsal=rr.tolist(), official=ro.tolist(), p_chisquare_gof=float(chi.pvalue))
    # cut-by-cut survival (fraction of the truth denominator surviving each cumulative stage)
    cfr = pd.read_csv(rh / "cutflow_A_any.csv"); cfo = rep["cutflow_any"]; rows = []
    for s in list(dict.fromkeys(cfo.stage)):
        o = cfo[(cfo.stage == s) & (cfo.group == "all")].iloc[0]; q = cfr[(cfr.stage == s) & (cfr.group == "all")]
        if len(q):
            q = q.iloc[0]; kr, nr, ko, no = int(q.N), int(q.denominator), int(o.N), int(o.denominator)
            rows.append(dict(stage=s, rehearsal=f"{kr}/{nr}", official=f"{ko}/{no}", rehearsal_frac=kr / nr, official_frac=ko / no,
                             p_binom=float(stats.binomtest(kr, nr, ko / no).pvalue)))
    pd.DataFrame(rows).to_csv(OUT / "natural_cv_cutflow_comparison.csv", index=False)
    cmpr["cutflow_min_p"] = float(min(r["p_binom"] for r in rows))
    # selected truth->reco: diagonal fraction
    dsel = pd.read_csv(rh / "migration_any_D_final_events__analysis_selected_candidate_raw.csv", index_col=0)
    summary["natural_cv_comparison"] = cmpr

    # --------------------------------------------------------------------------- backgrounds and beam-neutrino-only S/B
    bg = json.load(open(TAB / "background_rate_model.json"))
    comp = P.Component("B_BNB_NEUTRINO", "known", {c: bg["by_reco_channel"][c]["rate_per_1e20_POT"] for c in P.CHANNELS},
                       {c: bg["by_reco_channel"][c]["stat_unc_per_1e20_POT"] for c in P.CHANNELS}, note="from tables/official_signal/background_rate_model.json")
    sb = {}
    for r in REG:
        ex = summary["regions"][r]["expected_yield_any_per_1e20POT"]; s = ex["by_reco_channel"]; ds = ex["by_reco_channel_stat_unc"]
        pred = P.Prediction(1e20, P.Component("S_NCDELTA", "known", {c: s[c] for c in P.CHANNELS}, {c: ds[c] for c in P.CHANNELS}, note=f"official sample, region {r}"), comp,
                            P.Component("B_COSMIC", "unresolved", None, None, note="beam-off normalisation unresolved"), P.Component("DATA", "pending", None, None), region=r)
        ref = {}
        for name in ("total_background", "purity", "s_over_b", "significance"):
            try:
                getattr(pred, name)(); ref[name] = "NOT REFUSED (bug)"
            except P.UnresolvedNormalizationError:
                ref[name] = "refused (UnresolvedNormalizationError)"
        sb[r] = dict(refusals=ref, **{ch: dict(S=s[ch], S_unc=ds[ch], B_beam_neutrino=comp.values[ch], B_unc=comp.stat_unc[ch],
                    S_over_B_beam_neutrino_only=s[ch] / comp.values[ch],
                    S_over_B_unc=(s[ch] / comp.values[ch]) * float(np.hypot(ds[ch] / s[ch], comp.stat_unc[ch] / comp.values[ch])),
                    beam_neutrino_only_purity=s[ch] / (s[ch] + comp.values[ch])) for ch in ("1g0p", "1g1p")})
    summary["beam_neutrino_only_S_B_per_1e20POT"] = dict(note="EXCLUDES cosmic-only background (unresolved); stat only; the S region is the truth region, B is the whole BNB CV non-signal selection", **sb)

    # --------------------------------------------------------------------------- Task 13 descriptive diagnostics (TPC box, policy any)
    t13 = {}
    n0, n1 = (ta.truth_cat == 0), (ta.truth_cat == 1)
    e0, e1 = ci(ta[n0].A_final.sum(), n0.sum()), ci(ta[n1].A_final.sum(), n1.sum()); d = e1[0] - e0[0]
    se = np.hypot((e0[2] - e0[1]) / 2, (e1[2] - e1[1]) / 2)
    z = stats.chi2_contingency([[int(ta[n0].A_final.sum()), int(n0.sum() - ta[n0].A_final.sum())], [int(ta[n1].A_final.sum()), int(n1.sum() - ta[n1].A_final.sum())]])
    t13["q1_eff_1p_minus_0p"] = dict(eff_0p=e0, eff_1p=e1, diff=d, approx_unc_68=float(se), p_chi2=float(z[1]))
    mg = {nm: pd.read_csv(OUT / "active_tpc" / f"migration_any_{nm}.csv") for nm in ("A_all_denominator_events", "B_with_signal_matched_candidate", "D_final_selected")}
    g = lambda df, t, rc: df[(df.truth == t) & (df.reco == rc)].iloc[0]
    t13["q2_migration"] = {nm: dict(truth0p_to_reco1p=g(df, "0p", "reco 1p")[["N", "row_total", "fraction", "lo68", "hi68"]].to_dict(),
                                    truth1p_to_reco0p=g(df, "1p", "reco 0p")[["N", "row_total", "fraction", "lo68", "hi68"]].to_dict()) for nm, df in mg.items()}
    fin = ta[ta.A_final.astype(bool)]
    comp3 = {}
    for rc, nm in ((0, "reco_1g0p"), (1, "reco_1g1p"), (2, "reco_ge2p")):
        s = fin[fin.sel_reco_cat == rc]; comp3[nm] = dict(N=int(len(s)), truth={CLS[c]: int((s.truth_cat == c).sum()) for c in (0, 1, 2)},
                                                          delta={n: int((s.delta_pdg == p).sum()) for p, n in DELTA.items()},
                                                          truth_x_delta={f"{CLS[c]}/{n}": int(((s.truth_cat == c) & (s.delta_pdg == p)).sum()) for c in (0, 1, 2) for p, n in DELTA.items()})
    t13["q3_q4_selected_composition"] = comp3
    cs = pd.read_csv(OUT / "active_tpc" / "conditional_survival_any.csv"); t13["q5_conditional_survival"] = cs.round(4).to_dict("records")
    ffd = pd.read_csv(OUT / "active_tpc" / "first_failure_any_by_delta.csv"); ff = pd.read_csv(TAB / "official_active_tpc" / "first_failure_A_any_by_truth.csv")
    t13["q5_first_failure_by_truth"] = ff.to_dict("records"); t13["q5_first_failure_by_delta"] = ffd.round(4).to_dict("records")
    summary["task13_descriptive_diagnostics_TPC_box_any"] = t13
    (OUT / "summary.json").write_text(json.dumps(summary, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    print(json.dumps({r: (summary["regions"][r]["final_any"], summary["regions"][r]["expected_yield_any_per_1e20POT"]["by_reco_channel"]) for r in REG}))
    print(json.dumps(cmpr, default=str)[:1800])


if __name__ == "__main__":
    main()
