#!/usr/bin/env python
"""Frozen corrected-Round-1 selection replayed on the WCLocal2026Nov16 dedicated NC-Delta-radiative sample (same 13,772 events as Round 1). DIAGNOSTIC; nothing is tuned.

    source env/setup_eaf.sh && python scripts/wcl1116_replay_signal.py

OLD  = fg1-era `ncdr` reconstruction: the corrected Round-1 candidate table (D_full) with the stored arrival/denominator tables (regression anchors asserted: 833 / 12,427).
NEW  = WCLocal2026Nov16 `recTreeWireCell` (dv2_split_move) built with scripts/build_analysis_table.py, scored with the SAME frozen legacy scorer (log-odds, flag 0).
Denominator = the frozen provisional TPC-box master truth (12,427): identical for old and new (same truth, joined by run/subrun/event).
Writes tables/wcl1116_nov16_replay/signal_*.csv, $SP_DATA/wcl1116_nov16/derived/signal_*.parquet.
"""
from wcl1116_replay_common import *
import json
import run_official_signal_baseline as RB
from sbnd_single_photon import exclusive_signal as X, signal_master as SM, signal_pipeline as SP

CLS = {0: "0p", 1: "1p", 2: ">=2p"}; DELTA = {2114: "Delta0", 2214: "Delta+"}
ANCHOR_CUTFLOW = {"candidate": 11331, "n20mev": 8080, "bdt_evaluable": 8034, "numu": 4943, "other": 2717, "ncpi0": 1305, "nue": 893, "final": 833}


def vtx_dist(c, sig):
    """Distance (cm) of the reconstructed neutrino vertex of every candidate to the TRUE neutrino vertex of its event (signal truth); (0,0,0) = no vertex (sentinel) -> NaN."""
    m = c[RSE + ["c_nu_index", "c_kine_nu_x_corr", "c_kine_nu_y_corr", "c_kine_nu_z_corr", "pass_final"]].merge(sig[RSE + ["x", "y", "z", "truth_cat"]], on=RSE, how="inner")
    sent = (m.c_kine_nu_x_corr == 0) & (m.c_kine_nu_y_corr == 0) & (m.c_kine_nu_z_corr == 0)
    d = np.sqrt((m.c_kine_nu_x_corr - m.x) ** 2 + (m.c_kine_nu_y_corr - m.y) ** 2 + (m.c_kine_nu_z_corr - m.z) ** 2)
    m["dist"] = np.where(sent | ~np.isfinite(d), np.nan, d); m["sentinel"] = sent
    return m


def vtx_summary(m, label):
    rows = []
    first = m[m.c_nu_index == 0]; best = m.dropna(subset=["dist"]).groupby(RSE).dist.min().rename("dist").reset_index().merge(m[RSE + ["truth_cat"]].drop_duplicates(RSE), on=RSE)
    sel = m[m.pass_final].dropna(subset=["dist"]).groupby(RSE).dist.min().rename("dist").reset_index().merge(m[RSE + ["truth_cat"]].drop_duplicates(RSE), on=RSE)
    for view, t in (("first candidate (nu_index 0)", first.dropna(subset=["dist"])), ("nearest candidate", best), ("nearest SELECTED candidate", sel)):
        for g, mm in [("all", np.ones(len(t), bool))] + [(CLS[k], (t.truth_cat == k).to_numpy()) for k in (0, 1, 2)]:
            d = t.dist.to_numpy()[mm]; n = len(d)
            rows.append(dict(production=label, view=view, topology=g, n_events=n, median_cm=float(np.median(d)) if n else np.nan,
                             frac_lt_1cm=float((d < 1).mean()) if n else np.nan, frac_lt_3cm=float((d < 3).mean()) if n else np.nan, frac_lt_5cm=float((d < 5).mean()) if n else np.nan))
    return rows


def eff_rows(t, label, pol):
    rows = []
    groups = [("total", np.ones(len(t), bool))] + [(CLS[k], (t.truth_cat == k).values) for k in (0, 1, 2)] + [(n, (t.delta_pdg == p).values) for p, n in DELTA.items()]
    for g, m in groups:
        k = int(t.A_final[m].sum()); n = int(m.sum()); v, lo, hi = binom(k, n)
        rows.append(dict(production=label, policy=pol, group=g, selected=k, N_truth=n, efficiency_pct=100 * v, lo68_pct=100 * lo, hi68_pct=100 * hi))
    return rows


def main():
    cfg = load_cfg(); stage_names = [s for s, _ in X.stage_defs(cfg)]
    # ---------------- OLD (corrected Round-1 reference) ----------------
    To = SPD / "analysis_tables" / "official_gen2_ncdelta"; base = SPD / "official_signal_baseline"
    ev_o = pd.read_parquet(To / "events.parquet"); c_o = pd.read_parquet(SPC / "official_candidates_D_full.parquet")
    arr_o = pd.read_parquet(base / "signal_joined_active_tpc.parquet"); mis_o = pd.read_parquet(base / "signal_missing_active_tpc.parquet")
    units = pd.read_parquet(SPD / "official_gen2_ncdelta_master" / "units.parquet"); pot_sig = float(units[units.flatcaf_status == "flatcaf_available"].unit_pot.sum())
    rep_o, ta_o, tf_o, acc_o = RB.run_report(arr_o, mis_o, ev_o, c_o, cfg, label="old", region="active_tpc", pot_signal=pot_sig, exposure_pot=1e20)
    cf_o = rep_o["cutflow_any"]; cf_o = cf_o[cf_o.group == "all"].set_index("stage").N.to_dict()
    n_truth = len(arr_o) + len(mis_o)
    assert n_truth == 12427 and int(ta_o.A_final.sum()) == 833 and int(tf_o.A_final.sum()) == 795, "OLD reference not loaded correctly"
    assert {k: int(cf_o[k]) for k in ANCHOR_CUTFLOW} == ANCHOR_CUTFLOW, cf_o
    print("OLD reference regression OK: 833 / 12,427; cutflow", {k: int(cf_o[k]) for k in ANCHOR_CUTFLOW})
    # ---------------- NEW (Nov16) ----------------
    ev_n, c_n_raw, files_n = read_tables(NEW, "official_gen2_ncdelta")
    c_n = to_D(c_n_raw, ev_n, cfg)
    master = SPD / "official_gen2_ncdelta_master"; rec = pd.read_parquet(master / "signal_records.parquet")
    sig = SP.region_truth(rec, SM.load_regions()["active_tpc"], "active_tpc")
    arr_n, mis_n = SP.split_arrived(sig, ev_n)
    assert len(arr_n) + len(mis_n) == n_truth == 12427, (len(arr_n), len(mis_n))
    assert set(map(tuple, sig[RSE].values)) == set(map(tuple, pd.concat([arr_o, mis_o])[RSE].values)), "denominator differs between old and new"
    pot_new = float(files_n.total_pot.sum())
    rep_n, ta_n, tf_n, acc_n = RB.run_report(arr_n, mis_n, ev_n, c_n, cfg, label="nov16", region="active_tpc", pot_signal=pot_sig, exposure_pot=1e20)
    cf_n = rep_n["cutflow_any"]; cf_n = cf_n[cf_n.group == "all"].set_index("stage").N.to_dict()
    # ---------------- tables ----------------
    cf = pd.DataFrame(dict(stage=stage_names, old_fg1_N=[int(cf_o[s]) for s in stage_names], nov16_N=[int(cf_n[s]) for s in stage_names]))
    cf["delta"] = cf.nov16_N - cf.old_fg1_N; cf["old_pct_of_12427"] = 100 * cf.old_fg1_N / n_truth; cf["nov16_pct_of_12427"] = 100 * cf.nov16_N / n_truth
    cf.to_csv(OUT / "signal_cutflow_old_vs_nov16.csv", index=False)
    eff = pd.DataFrame(eff_rows(ta_o, "old_fg1", "any") + eff_rows(ta_n, "nov16", "any") + eff_rows(tf_o, "old_fg1", "first") + eff_rows(tf_n, "nov16", "first"))
    eff.to_csv(OUT / "signal_topology_efficiency.csv", index=False)
    # cutflow by truth topology (any)
    rows = []
    for lab, ta in (("old_fg1", ta_o), ("nov16", ta_n)):
        for g, m in [("all", np.ones(len(ta), bool))] + [(CLS[k], (ta.truth_cat == k).values) for k in (0, 1, 2)] + [(n, (ta.delta_pdg == p).values) for p, n in DELTA.items()]:
            rows.append(dict(production=lab, group=g, N_truth=int(m.sum()), **{s: int(ta[f"A_{s}"][m].sum()) for s in stage_names}))
    pd.DataFrame(rows).to_csv(OUT / "signal_cutflow_by_topology.csv", index=False)
    # first failure (view A; any policy) by production
    ff = []
    for lab, ta in (("old_fg1", ta_o), ("nov16", ta_n)):
        vc = ta.first_fail_A.value_counts()
        for k, v in vc.items():
            ff.append(dict(production=lab, first_fail=k, N=int(v), pct=100 * v / len(ta)))
    pd.DataFrame(ff).pivot_table(index="first_fail", columns="production", values=["N", "pct"]).round(3).to_csv(OUT / "signal_first_failure.csv")
    # ---------------- matched migration ----------------
    def flags(ta):
        t = ta[RSE + ["truth_cat", "delta_pdg", "wc_valid"] + [f"A_{s}" for s in stage_names]].copy()
        return t.set_index(RSE)
    fo, fn = flags(ta_o), flags(ta_n)
    ix = fo.index.intersection(fn.index); assert len(ix) == n_truth, len(ix)
    fo, fn = fo.loc[ix], fn.loc[ix]
    po, pn = fo.A_final.values, fn.A_final.values
    mig = np.select([po & pn, po & ~pn, ~po & pn], ["old pass -> new pass", "old pass -> new fail", "old fail -> new pass"], "old fail -> new fail")
    old_f = pd.DataFrame({s: fo[f"A_{s}"].values for s in STAGES}, index=ix); new_f = pd.DataFrame({s: fn[f"A_{s}"].values for s in STAGES}, index=ix)
    fcs = first_changed_stage(old_f, new_f)
    M = pd.DataFrame(dict(migration=mig, first_changed_stage=fcs.values, truth_cat=fo.truth_cat.values, delta_pdg=fo.delta_pdg.values), index=ix).reset_index()
    M.to_parquet(DER / "signal_migration_events.parquet", index=False)
    s1 = M.groupby("migration").size().rename("N").reset_index(); s1["pct"] = 100 * s1.N / len(M)
    s2 = M[M.migration != "old fail -> new fail"].groupby(["migration", "first_changed_stage"]).size().rename("N").reset_index()
    s3 = M.groupby(["migration", M.truth_cat.map(CLS)]).size().rename("N").reset_index().rename(columns={"truth_cat": "topology"})
    s4 = M.groupby(["migration", M.delta_pdg.map(DELTA).fillna("other")]).size().rename("N").reset_index().rename(columns={"delta_pdg": "delta"})
    s5 = M[M.migration.isin(["old pass -> new fail", "old fail -> new pass"])].groupby(["migration", "first_changed_stage", M.truth_cat.map(CLS)]).size().rename("N").reset_index().rename(columns={"truth_cat": "topology"})
    s1.to_csv(OUT / "signal_migration_summary.csv", index=False); s2.to_csv(OUT / "signal_migration_first_changed_stage.csv", index=False)
    s3.to_csv(OUT / "signal_migration_by_topology.csv", index=False); s4.to_csv(OUT / "signal_migration_by_delta_charge.csv", index=False)
    s5.to_csv(OUT / "signal_migration_stage_by_topology.csv", index=False)
    # ---------------- candidate / ceiling ----------------
    ceil = []
    for lab, ev, c, ta in (("old_fg1", ev_o, c_o, ta_o), ("nov16", ev_n, c_n, ta_n)):
        nc = c.groupby(RSE).size().rename("ncand").reset_index().merge(ta[RSE + ["truth_cat"]], on=RSE, how="right"); nc["ncand"] = nc.ncand.fillna(0).astype(int)
        ceil.append(dict(production=lab, N_truth=len(ta), wc_valid=int(ta.wc_valid.sum()), with_candidate=int(ta.A_candidate.sum()), n20_shower=int(ta.A_n20mev.sum()), bdt_evaluable=int(ta.A_bdt_evaluable.sum()),
                         mean_ncand=float(nc.ncand.mean()), pct_events_ncand_ge2=100 * float((nc.ncand >= 2).mean()), total_candidates_signal_events=int(nc.ncand.sum())))
    pd.DataFrame(ceil).to_csv(OUT / "signal_reco_ceiling.csv", index=False)
    # ---------------- vertex distance ----------------
    vo, vn = vtx_dist(c_o, sig), vtx_dist(c_n, sig)
    vs = pd.DataFrame(vtx_summary(vo, "old_fg1") + vtx_summary(vn, "nov16")); vs.to_csv(OUT / "signal_vertex_distance.csv", index=False)
    vo.to_parquet(DER / "signal_vtx_old.parquet", index=False); vn.to_parquet(DER / "signal_vtx_new.parquet", index=False)
    # matched per-event nearest-candidate distance change
    def near(v):
        return v.dropna(subset=["dist"]).groupby(RSE).dist.min().rename("d")
    dd = pd.concat([near(vo).rename("d_old"), near(vn).rename("d_new")], axis=1).dropna()
    dd = dd.reset_index().merge(sig[RSE + ["truth_cat"]], on=RSE)
    vm = [dict(topology=g, n_matched=int(m.sum()), median_old=float(dd.d_old[m].median()), median_new=float(dd.d_new[m].median()),
               frac_improved_gt_1cm=float(((dd.d_old - dd.d_new)[m] > 1).mean()), frac_worsened_gt_1cm=float(((dd.d_new - dd.d_old)[m] > 1).mean()),
               frac_lt5_old=float((dd.d_old[m] < 5).mean()), frac_lt5_new=float((dd.d_new[m] < 5).mean()))
          for g, m in [("all", np.ones(len(dd), bool))] + [(CLS[k], (dd.truth_cat == k).to_numpy()) for k in (0, 1, 2)]]
    pd.DataFrame(vm).to_csv(OUT / "signal_vertex_distance_matched.csv", index=False)
    # ---------------- score migration (candidate matched on event + nu_index; event-level maximum is index independent) ----------------
    sg = sig[RSE]; cols = ["c_nu_index"] + [f"c_score_{m}" for m in L.MODELS]
    a = c_o.merge(sg, on=RSE)[RSE + cols]; b = c_n.merge(sg, on=RSE)[RSE + cols]
    mc = a.merge(b, on=RSE + ["c_nu_index"], suffixes=("_old", "_new"))
    sh = []
    for m in L.MODELS:
        o, n = mc[f"c_score_{m}_old"].to_numpy(float), mc[f"c_score_{m}_new"].to_numpy(float); ok = np.isfinite(o) & np.isfinite(n); d = (n - o)[ok]
        thr = FROZEN[m]; po_, pn_ = o[ok] > thr, n[ok] > thr
        sh.append(dict(model=m, view="matched candidates (event, nu_index)", n=int(ok.sum()), median_shift=float(np.median(d)), p16=float(np.percentile(d, 16)), p84=float(np.percentile(d, 84)),
                       frac_cross_up=float((~po_ & pn_).mean()), frac_cross_down=float((po_ & ~pn_).mean()), threshold=thr))
        ao = a.groupby(RSE)[f"c_score_{m}"].max(); bn = b.groupby(RSE)[f"c_score_{m}"].max(); j = pd.concat([ao.rename("o"), bn.rename("n")], axis=1).dropna(); j = j[np.isfinite(j.o) & np.isfinite(j.n)]
        d2 = (j.n - j.o).to_numpy()
        sh.append(dict(model=m, view="event-level maximum over candidates", n=len(j), median_shift=float(np.median(d2)), p16=float(np.percentile(d2, 16)), p84=float(np.percentile(d2, 84)),
                       frac_cross_up=float(((j.o <= thr) & (j.n > thr)).mean()), frac_cross_down=float(((j.o > thr) & (j.n <= thr)).mean()), threshold=thr))
    pd.DataFrame(sh).to_csv(OUT / "signal_score_migration.csv", index=False)
    # score distributions of the four SP scores for later figures (event-level max, same events)
    sd = {}
    for m in L.MODELS:
        sd[f"old_{m}"] = a.groupby(RSE)[f"c_score_{m}"].max().replace([np.inf, -np.inf], np.nan).dropna().to_numpy()
        sd[f"new_{m}"] = b.groupby(RSE)[f"c_score_{m}"].max().replace([np.inf, -np.inf], np.nan).dropna().to_numpy()
    np.savez_compressed(DER / "signal_score_distributions.npz", **sd)
    # ---------------- rates (Round-1 definitions, unchanged) ----------------
    def rate(rep, ta):
        e = rep.get("expected_yield") or rep.get("expected") or {}
        return e
    summary = dict(n_truth=n_truth, pot_signal=pot_sig,
                   old=dict(selected_any=int(ta_o.A_final.sum()), selected_first=int(tf_o.A_final.sum()), final_any=rep_o["final_any"], expected=rep_o.get("expected_yield", rep_o.get("expected"))),
                   nov16=dict(selected_any=int(ta_n.A_final.sum()), selected_first=int(tf_n.A_final.sum()), final_any=rep_n["final_any"], expected=rep_n.get("expected_yield", rep_n.get("expected"))),
                   accounting_old=acc_o, accounting_new=acc_n, nov16_total_pot_files=pot_new, nov16_events_table=int(len(ev_n)), nov16_wc_valid=int(ev_n.wc_valid.sum()),
                   migration=s1.set_index("migration").N.to_dict())
    json.dump(summary, open(OUT / "signal_summary.json", "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    ta_o.to_parquet(DER / "signal_event_table_old_any.parquet", index=False); ta_n.to_parquet(DER / "signal_event_table_new_any.parquet", index=False)
    tf_n.to_parquet(DER / "signal_event_table_new_first.parquet", index=False); tf_o.to_parquet(DER / "signal_event_table_old_first.parquet", index=False)
    c_n.to_parquet(DER / "signal_candidates_new_D.parquet", index=False)
    print(cf.to_string(index=False)); print(eff[eff.policy == "any"].round(3).to_string(index=False)); print(s1.to_string(index=False)); print(s2.to_string(index=False))


if __name__ == "__main__":
    main()
