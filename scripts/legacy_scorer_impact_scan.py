#!/usr/bin/env python
"""Impact scan of the legacy-scorer correction (NO training; XMLs, thresholds, candidate policy, truth region, proton convention, cut order unchanged).

Re-scores the existing candidate tables of (1) the official Gen2 NC-Delta signal, (2) the fg1 BNB CV, (3) the natural NC-Delta in the BNB CV under four configurations

    A_old          as-run: v = tanh(raw) cut at the frozen numbers, real kine_pio_flag
    B_score_only   log10((1+v)/(1-v)) score, real kine_pio_flag
    C_pio_only     as-run score scale, kine_pio_flag = 0
    D_full         log-odds score and kine_pio_flag = 0   (= legacy_source_faithful)

ROOT is not read here. The only new input is the ncpi0 BDT inputs of the BNB-CV candidates reaching the ncpi0 stage as run (scripts/legacy_scorer_ncpi0_scan.py);
the official / natural ones were stored by the Phase-12 stage scan. Every configuration is stricter than as-run at numu/other, so the corrected selected set is a subset of the
as-run candidates that reach ncpi0 (asserted below).

    source env/setup_eaf.sh && python scripts/legacy_scorer_impact_scan.py
Writes tables/legacy_scorer_correction/*, and the D_full candidate tables to $SP_DATA/legacy_scorer_correction/.
"""
from __future__ import annotations
import json, os, sys, warnings
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); sys.path.insert(0, str(REPO / "scripts")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from sbnd_single_photon import bdt as B, exclusive_signal as X, legacy_scorer as L, natural_signal as NS, scanio as SIO, selection as SEL
import run_official_signal_baseline as RB

SPD = Path(os.environ["SP_DATA"]); OUT = REPO / "tables" / "legacy_scorer_correction"; OUT.mkdir(parents=True, exist_ok=True)
SPOUT = SPD / "legacy_scorer_correction"; SPOUT.mkdir(parents=True, exist_ok=True)
CFGS = list(L.CONFIGS)
STAGES = ["candidate", "n20mev", "bdt_evaluable", "numu", "other", "ncpi0", "nue", "n20br1"]
CLS = {0: "0p", 1: "1p", 2: ">=2p"}; DELTA = {2114: "Delta0", 2214: "Delta+"}
NCP = B.TmvaBdt("ncpi0", B.DEFAULT_WEIGHT_DIR / "single_photon_ncpi0_bdt_final.xml")


def load_inputs(sample):
    """ncpi0 inputs (+ as-run recomputed score) keyed on (file_index, ev, c_nu_index)."""
    if sample == "official":
        d = pd.read_parquet(SPD / "remaining_stage_audit" / "official_ncdelta" / "raw" / "official_candidates.parquet")
        cols = ["in_" + n for n in NCP.var_names]; d = d[["file_index", "ev", "c_nu_index"] + cols].copy()
    else:
        d = pd.read_parquet(SPOUT / "bnb_cv_ncpi0_inputs.parquet"); cols = ["in_" + n for n in NCP.var_names]; d = d[["file_index", "ev", "c_nu_index"] + cols].copy()
    return d, cols


def rescore(cands, events, cfg, config, inp, cols, *, check_asrun=False):
    """Candidate table with the c_score_* columns of the configuration, and the cum_* chain recomputed with the UNCHANGED frozen thresholds."""
    mode = L.CONFIGS[config]; c = cands.copy()
    v = {m: c[f"c_score_{m}"].to_numpy(float).copy() for m in L.MODELS}
    key = pd.MultiIndex.from_arrays([c.file_index, c.ev, c.c_nu_index]); ik = pd.MultiIndex.from_arrays([inp.file_index, inp.ev, inp.c_nu_index])
    pos = ik.get_indexer(key); have = pos >= 0
    X0 = L.ncpi0_input_matrix(inp[cols].to_numpy(float), NCP.var_names, mode["pio_flag"])
    vn = np.full(len(c), np.nan); vn[have] = NCP.decision(X0[pos[have]])
    vn = np.where(np.isfinite(v["ncpi0"]), vn, np.nan)       # the as-run table masks non-filled / non-evaluable candidates to NaN: keep exactly that
    if check_asrun:                                         # real flag recomputation must reproduce the stored as-run score
        d = np.abs(vn[have] - v["ncpi0"][have])
        assert np.nanmax(d) < 1e-9 and (np.isfinite(vn[have]) == np.isfinite(v["ncpi0"][have])).all(), np.nanmax(d)
    if mode["pio_flag"] == "zero":
        v["ncpi0"] = np.where(have, vn, v["ncpi0"])         # candidates without inputs cannot reach ncpi0 (asserted by the caller)
    for m in L.MODELS:
        c[f"c_score_{m}"] = np.asarray(L.score(v[m], mode["log_odds"]), dtype=np.float64)
    tab = {"ev_valid": events.wc_valid.values, "c_gev": c.gev.values.astype(np.int64)}
    for col in c.columns:
        if col.startswith("c_"):
            tab[col] = c[col].values
    chain = SIO.candidate_chain(tab, cfg)
    for name, flag in chain.items():
        c["cum_" + name] = flag
    c["pass_final"] = chain[cfg["cuts"][-1]["name"]]
    c["_have_ncpi0_inputs"] = have
    return c


def ev_stage_depth(c):
    """Deepest cumulative stage reached by any candidate of each event, 0 = none; first failing stage name."""
    cols = ["cum_candidate_in_valid_event", "cum_n_20mev_showers_gt0", "cum_single_photon_numu_score_gt_0p4", "cum_single_photon_other_score_gt_0p2",
            "cum_single_photon_ncpi0_score_gt_m0p05", "cum_single_photon_nue_score_gt_m1", "cum_n_20br1_showers_eq1"]
    nm = ["candidate", "n20mev", "numu", "other", "ncpi0", "nue", "n20br1", "FINAL"]
    d = c[cols].to_numpy(bool).sum(axis=1)
    g = pd.Series(d).groupby([c.file_index.values, c.ev.values]).max()
    return g.rename("depth").to_frame().assign(first_fail=lambda t: [nm[i] for i in t.depth])


def eff_rows(t, config, sample):
    rows = []
    groups = [("total", np.ones(len(t), bool))] + [(CLS[k], (t.truth_cat == k).values) for k in (0, 1, 2)] + [(n, (t.delta_pdg == p).values) for p, n in DELTA.items()]
    for g, m in groups:
        k = int(t.A_final[m].sum()); n = int(m.sum()); v, lo, hi = X.binom_ci(k, n)
        rows.append(dict(sample=sample, config=config, group=g, selected=k, N_truth=n, efficiency=float(v), lo68=float(lo), hi68=float(hi)))
    return rows


def main():
    cfg = SEL.load_config()
    assert [c["threshold"] for c in cfg["cuts"] if "score" in c["name"]] == [0.4, 0.2, -0.05, -1.0]      # the frozen numbers are used unchanged
    # ---- official signal
    T = SPD / "analysis_tables" / "official_gen2_ncdelta"; base = SPD / "official_signal_baseline"
    ev_o = pd.read_parquet(T / "events.parquet"); c_o = pd.read_parquet(T / "candidates.parquet")
    arr = pd.read_parquet(base / "signal_joined_active_tpc.parquet"); mis = pd.read_parquet(base / "signal_missing_active_tpc.parquet")
    inp_o, cols = load_inputs("official")
    # ---- BNB CV + natural
    Tb = SPD / "analysis_tables" / "bnb_cv"; ev_b = pd.read_parquet(Tb / "events.parquet"); c_b = pd.read_parquet(Tb / "candidates.parquet")
    inp_b, _ = load_inputs("bnb")
    sn = pd.read_parquet(SPD / "natural_ncdelta_bnb_cv" / "signal_neutrinos.parquet"); sig_all = NS.to_signal_truth_table(sn); nat = sig_all[sig_all.in_region].reset_index(drop=True)
    bkg = pd.read_parquet(SPD / "background_mechanisms" / "bnb_cv" / "background_mechanism_table.parquet", columns=["file_index", "run", "subrun", "evt", "reco_channel", "event_class", "cand_category"])
    bkg_key = {(int(r.run), int(r.subrun), int(r.evt)): (r.event_class, r.reco_channel, r.cand_category) for r in bkg.itertuples()}
    ev_b_key = ev_b.set_index(["file_index", "ev"])[["run", "subrun", "evt"]]

    res, rows_eff, cf_sig, cf_bnb, cf_nat, tabs, depth = [], [], [], [], [], {}, {}
    for cfgname in CFGS:
        co = rescore(c_o, ev_o, cfg, cfgname, inp_o, cols, check_asrun=(cfgname == "A_old"))
        cb = rescore(c_b, ev_b, cfg, cfgname, inp_b, cols, check_asrun=(cfgname == "A_old"))
        for nm, c in (("official", co), ("bnb", cb)):                       # every candidate that reaches ncpi0 has stored inputs (else the subset argument fails)
            reach = c.cum_single_photon_other_score_gt_0p2
            if nm == "official":
                reg = c.set_index(["file_index", "ev"]).index.isin(arr.set_index(["file_index", "ev"]).index)
                assert bool((c._have_ncpi0_inputs | ~reach | ~reg).all()), (cfgname, nm, int((reach & ~c._have_ncpi0_inputs & reg).sum()))
            else:
                assert bool((c._have_ncpi0_inputs | ~reach).all()), (cfgname, nm, int((reach & ~c._have_ncpi0_inputs).sum()))
        if cfgname == "A_old":                                              # exact reproduction of the stored as-run flags
            for nm, c0, cc in (("official", c_o, co), ("bnb", c_b, cb)):
                for col in [k for k in c0.columns if k.startswith("cum_")] + ["pass_final"]:
                    assert (c0[col].values == cc[col].values).all(), (nm, col)
        rep, ta, tf, acc = RB.run_report(arr, mis, ev_o, co, cfg, label="official_gen2_ncdelta", region="active_tpc")
        tabs[cfgname] = ta; depth[("official", cfgname)] = ev_stage_depth(co[co.cum_candidate_in_valid_event | True])
        rows_eff += eff_rows(ta, cfgname, "official_any") + eff_rows(tf, cfgname, "official_first")
        cf = rep["cutflow_any"]; cf = cf[cf.group == "all"][["stage", "N"]].assign(config=cfgname); cf_sig.append(cf)
        # BNB: events passing any candidate
        selb = cb[cb.pass_final].groupby(["file_index", "ev"]).size().index
        nb = len(selb); k = {(int(a), int(b)) for a, b in selb}
        dep = ev_stage_depth(cb); depth[("bnb", cfgname)] = dep
        cumb = {st: int((dep.depth >= i).sum()) for i, st in zip(range(1, 8), ["candidate", "n20mev", "numu", "other", "ncpi0", "nue", "n20br1"])}
        cumb["FINAL"] = int((dep.depth >= 7).sum()); cf_bnb.append(pd.DataFrame(dict(stage=list(cumb), N=list(cumb.values()), config=cfgname)))
        # natural CV (117-event region)
        rep_n, ta_n, tf_n, _ = RB.run_report(nat, nat.iloc[:0], ev_b, cb, cfg, label="natural", region="active_tpc")
        cfn = rep_n["cutflow_any"]; cfn = cfn[cfn.group == "all"][["stage", "N"]].assign(config=cfgname); cf_nat.append(cfn)
        # non-signal BNB selected (event_class from the Phase-4 table; events new to the selection have no label)
        lab = [bkg_key.get(tuple(int(x) for x in ev_b_key.loc[i]), (None, None, None)) for i in selb]
        nonsig = sum(1 for l in lab if l[0] == "background")
        res.append(dict(config=cfgname, official_selected_any=rep["final_any"]["total"], official_selected_first=rep["final_first"]["total"], N_truth=int(len(ta)),
                        bnb_selected_events=nb, bnb_selected_labelled_nonsignal=nonsig, bnb_selected_signal_like=sum(1 for l in lab if l[0] == "signal_like"), bnb_new_unlabelled=sum(1 for l in lab if l[0] is None),
                        natural_selected=rep_n["final_any"]["total"], natural_N=int(len(nat)),
                        reco_1g0p=rep["final_any"]["reco_channel"]["0p"], reco_1g1p=rep["final_any"]["reco_channel"]["1p"], reco_ge2p=rep["final_any"]["reco_channel"][">=2p"]))
        if cfgname in ("A_old", "D_full"):
            co.drop(columns=["_have_ncpi0_inputs"]).to_parquet(SPOUT / f"official_candidates_{cfgname}.parquet", index=False)
            cb.drop(columns=["_have_ncpi0_inputs"]).to_parquet(SPOUT / f"bnb_candidates_{cfgname}.parquet", index=False)
        tabs[(cfgname, "bnb_sel")] = k; tabs[(cfgname, "bnb_lab")] = dict(zip(selb, lab))

    R = pd.DataFrame(res); R["efficiency"] = R.official_selected_any / R.N_truth
    R.to_csv(OUT / "impact_configurations.csv", index=False)
    pd.DataFrame(rows_eff).to_csv(OUT / "efficiency_by_config.csv", index=False)
    for nm, lst in (("signal", cf_sig), ("bnb_cv", cf_bnb), ("natural_cv", cf_nat)):
        t = pd.concat(lst).pivot_table(index="stage", columns="config", values="N", aggfunc="first", sort=False)[CFGS]; t.to_csv(OUT / f"cutflow_by_config_{nm}.csv")
    # ---- flips (event level, 'any' policy)
    flips = []
    for newc in ("B_score_only", "C_pio_only", "D_full"):
        a, n = tabs["A_old"], tabs[newc]
        m = a[["file_index", "ev", "truth_cat", "delta_pdg", "A_final", "first_fail_A"]].merge(n[["file_index", "ev", "A_final", "first_fail_A"]], on=["file_index", "ev"], suffixes=("_old", "_new"))
        assert len(m) == len(a)
        m["flip"] = np.select([m.A_final_old & ~m.A_final_new, ~m.A_final_old & m.A_final_new, m.A_final_old & m.A_final_new], ["old_pass_new_fail", "old_fail_new_pass", "unchanged_pass"], "unchanged_fail")
        m["config"] = newc; m["sample"] = "official"
        flips.append(m)
        ob = tabs[("A_old", "bnb_sel")]; nb_ = tabs[(newc, "bnb_sel")]
        for kk in sorted(ob | nb_):
            st = "unchanged_pass" if kk in ob and kk in nb_ else ("old_pass_new_fail" if kk in ob else "old_fail_new_pass")
            lb = tabs[("A_old", "bnb_lab")].get(kk) or tabs[(newc, "bnb_lab")].get(kk) or (None, None, None)
            flips.append(pd.DataFrame([dict(file_index=kk[0], ev=kk[1], flip=st, config=newc, sample="bnb_cv", bkg_cand_category=lb[2],
                                            first_fail_old=depth[("bnb", "A_old")].first_fail.get(kk, "FINAL"), first_fail_new=depth[("bnb", newc)].first_fail.get(kk, "FINAL"),
                                            bkg_class=lb[0], bkg_channel=lb[1])]))
    F = pd.concat(flips, ignore_index=True); F.to_csv(OUT / "event_flips.csv", index=False)
    # flip summaries: first stage whose decision changes = new first failure (pass -> fail) or old first failure (fail -> pass)
    rows = []
    S_ = F[(F["sample"] == "official") & F.flip.isin(["old_pass_new_fail", "old_fail_new_pass"])].copy()
    S_["stage"] = np.where(S_.flip == "old_pass_new_fail", S_.first_fail_A_new, S_.first_fail_A_old)
    S_["truth"] = S_.truth_cat.map(CLS); S_["delta"] = S_.delta_pdg.map(DELTA)
    for (cf_, fl), g in S_.groupby(["config", "flip"]):
        for dim in ("stage", "truth", "delta"):
            for val, n in g[dim].value_counts().items():
                rows.append(dict(sample="official", config=cf_, flip=fl, dimension=dim, value=val, N=int(n)))
    Bf = F[(F["sample"] == "bnb_cv") & F.flip.isin(["old_pass_new_fail", "old_fail_new_pass"])].copy()
    Bf["stage"] = np.where(Bf.flip == "old_pass_new_fail", Bf.first_fail_new, Bf.first_fail_old)
    for (cf_, fl), g in Bf.groupby(["config", "flip"]):
        for dim in ("stage", "bkg_class", "bkg_channel", "bkg_cand_category"):
            for val, n in g[dim].fillna("(not in Phase-4 selected table: newly selected)").value_counts().items():
                rows.append(dict(sample="bnb_cv", config=cf_, flip=fl, dimension=dim, value=val, N=int(n)))
    pd.DataFrame(rows).to_csv(OUT / "flip_summary.csv", index=False)
    # threshold translation
    thr = pd.DataFrame([dict(model=m, frozen_cut_on_score=L.FROZEN_THRESHOLDS[m], as_run_cut_on_v=L.FROZEN_THRESHOLDS[m], equivalent_cut_on_v=float(L.response_from_score(L.FROZEN_THRESHOLDS[m]))) for m in L.MODELS])
    thr.to_csv(OUT / "threshold_translation.csv", index=False)
    print(R.to_string()); print(thr.to_string())
    json.dump(dict(configs=R.to_dict("records")), open(OUT / "impact_summary.json", "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))


if __name__ == "__main__":
    main()
