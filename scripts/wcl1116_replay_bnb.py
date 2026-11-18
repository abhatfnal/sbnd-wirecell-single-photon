#!/usr/bin/env python
"""Frozen corrected-Round-1 selection on the WCLocal2026Nov16 BNB CV (generic MC), versus the corrected Round-1 reference. DIAGNOSTIC; categories and cuts are unchanged.

    source env/setup_eaf.sh
    python scripts/wcl1116_replay_bnb.py deep  --workers 24      # candidate-associated truth of the NEW selected candidates (same `deep` code as Round 1)
    python scripts/wcl1116_replay_bnb.py report                  # composition, rates, natural-CV, matched enter/leave migration

OLD = corrected Round-1 (D_full) candidate table + `selected_event_classes.csv` of the source-faithful rebuild (regression anchors: 291 selected, 282 non-signal = 150/93/39, nueCC 1).
Same files in the same order (file_index maps one to one); events are matched on run/subrun/evt.
"""
from wcl1116_replay_common import *
import argparse, json
import multiprocessing as mp
from sbnd_single_photon import background_mechanisms as BM, natural_signal as NS, prediction as P, samples as S
import run_official_signal_baseline as RB

SF = REPO / "tables" / "legacy_scorer_correction" / "source_faithful"
DEEP = DER / "bnb_new_deep"


def selected_new(cfg):
    ev, c_raw, files = read_tables(NEW, "bnb_cv")
    c = to_D(c_raw, ev, cfg)
    return ev, c, files


def stage_deep(a):
    import background_deep as BD
    cfg = load_cfg(); ev, c, files = selected_new(cfg)
    urls = [r["url"] for r in S.read_manifest(REPO / "manifests" / "wcl1116" / "bnb_cv.tsv.gz")]
    sel = c[c.pass_final][["file_index", "ev", "c_nu_index"]]; print("NEW selected candidates", len(sel), "events", sel.groupby(["file_index", "ev"]).ngroups, flush=True)
    DEEP.mkdir(parents=True, exist_ok=True)
    jobs = [(int(i), urls[int(i)], str(DEEP), g[["ev", "c_nu_index"]].values.tolist()) for i, g in sel.groupby("file_index")]
    with mp.get_context("spawn").Pool(min(a.workers, 24)) as p:
        res = list(p.imap_unordered(BD.deep_work, jobs))
    bad = [r for r in res if isinstance(r, tuple) and len(r) > 1 and str(r[1]).startswith("ERR")]
    print("deep files", len(res), "errors", bad[:3], flush=True)
    df = pd.concat([pd.read_parquet(p) for p in sorted(DEEP.glob("*.parquet"))], ignore_index=True); df.to_parquet(DER / "bnb_new_deep.parquet", index=False); print(df.shape)


def classify(c, deep, sig):
    """Round-1 procedure, unchanged: candidate category from the deep association, event class from the natural-signal table."""
    light = BM.add_categories(deep, sig)
    passing = c[c.pass_final.values].rename(columns={"c_nu_index": "nu_index"})
    sel = passing.merge(light.drop(columns=[x for x in light.columns if x in passing.columns and x not in BM.CKEY]), on=BM.CKEY, how="left", validate="one_to_one")
    assert len(sel) == len(passing) and sel.tm_top_nu.notna().all(), "selected candidates without a stored truth association"
    sig_ev = NS.classify_selected_events(passing.rename(columns={"nu_index": "c_nu_index"}), sig.rename(columns={"k": "nu_k"}))
    return BM.event_level(sel, sig_ev)


def report(a):
    cfg = load_cfg()
    sig = pd.read_parquet(SPD / "natural_ncdelta_bnb_cv" / "signal_neutrinos.parquet")
    # ---- OLD
    Tb = SPD / "analysis_tables" / "bnb_cv"; ev_o = pd.read_parquet(Tb / "events.parquet"); c_o = pd.read_parquet(SPC / "bnb_candidates_D_full.parquet")
    old_cls = pd.read_csv(SF / "background_mechanisms" / "selected_event_classes.csv")
    assert len(old_cls) == 291 and int((old_cls.event_class == "background").sum()) == 282, "OLD BNB reference not loaded correctly"
    ch_o = old_cls[old_cls.event_class == "background"].reco_channel.replace({"ge2p_diag": "ge2p"}).value_counts().to_dict()
    assert (ch_o.get("1g0p"), ch_o.get("1g1p"), ch_o.get("ge2p")) == (150, 93, 39), ch_o
    # ---- NEW
    ev_n, c_n, files_n = selected_new(cfg)
    deep = pd.read_parquet(DER / "bnb_new_deep.parquet")
    new_cls = classify(c_n, deep, sig)
    pot_cv_new = float(files_n.total_pot.sum()); pot_cv_old = float(pd.read_parquet(Tb / "files.parquet").total_pot.sum())
    assert abs(pot_cv_new - pot_cv_old) / pot_cv_old < 1e-9, (pot_cv_new, pot_cv_old)          # same files: same exposure
    bg = new_cls[new_cls.event_class == "background"]
    ch_n = bg.reco_channel.replace({"ge2p_diag": "ge2p"}).value_counts().to_dict()
    tab = new_cls.assign(reco_channel=new_cls.reco_channel.replace({"ge2p_diag": "ge2p"}))
    bkc = P.bnb_background_component(tab, pot_cv_new, 1e20); bko = P.bnb_background_component(old_cls.assign(reco_channel=old_cls.reco_channel.replace({"ge2p_diag": "ge2p"})), pot_cv_old, 1e20)
    comp = BM.composition(bg, pot_cv_new); comp.round(5).to_csv(OUT / "bnb_background_composition_nov16.csv", index=False)
    # ---- selected totals
    cls_n = new_cls.event_class.value_counts().to_dict(); cls_o = old_cls.event_class.value_counts().to_dict()
    tot = pd.DataFrame([dict(production="old_fg1 (corrected R1)", selected_events=len(old_cls), signal_like=cls_o.get("signal_like", 0), mixed=cls_o.get("mixed", 0), non_signal=cls_o.get("background", 0),
                             reco_1g0p=ch_o.get("1g0p", 0), reco_1g1p=ch_o.get("1g1p", 0), reco_ge2p=ch_o.get("ge2p", 0), pot=pot_cv_old,
                             **{f"rate_per_1e20_{k}": bko.values[k] for k in P.CHANNELS}),
                        dict(production="nov16", selected_events=len(new_cls), signal_like=cls_n.get("signal_like", 0), mixed=cls_n.get("mixed", 0), non_signal=cls_n.get("background", 0),
                             reco_1g0p=ch_n.get("1g0p", 0), reco_1g1p=ch_n.get("1g1p", 0), reco_ge2p=ch_n.get("ge2p", 0), pot=pot_cv_new, **{f"rate_per_1e20_{k}": bkc.values[k] for k in P.CHANNELS})])
    tot.to_csv(OUT / "bnb_selected_totals.csv", index=False)
    # ---- category counts old vs new (non-signal events), by candidate-associated event category
    co = old_cls[old_cls.event_class == "background"].event_cand_category.value_counts(); cn = bg.event_cand_category.value_counts()
    # ---- matched enter/leave
    key_o = ev_o[["file_index", "ev"] + RSE]; key_n = ev_n[["file_index", "ev"] + RSE]
    assert (key_o[RSE].to_numpy() == key_n[RSE].to_numpy()).all() if len(key_o) == len(key_n) else False, "BNB event sets differ between old and new"
    o_sel = old_cls.merge(key_o, on=["file_index", "ev"]); n_sel = new_cls.merge(key_n, on=["file_index", "ev"])
    so, sn = set(map(tuple, o_sel[RSE].values)), set(map(tuple, n_sel[RSE].values))
    fo, fn = ev_stage_flags(c_o), ev_stage_flags(c_n); ix = fo.index.union(fn.index)
    fo, fn = fo.reindex(ix, fill_value=False), fn.reindex(ix, fill_value=False)
    fcs = first_changed_stage(fo, fn)
    rows = []
    cat_o = o_sel.set_index(RSE).event_cand_category.to_dict() if False else {tuple(r[RSE]): (r.event_class, r.event_cand_category, r.reco_channel) for _, r in o_sel.iterrows()}
    cat_n = {tuple(r[RSE]): (r.event_class, r.event_cand_category, r.reco_channel) for _, r in n_sel.iterrows()}
    for k in so | sn:
        st = "stays selected" if (k in so and k in sn) else ("LEAVES (old selected -> new not)" if k in so else "ENTERS (new selected, old not)")
        rows.append(dict(run=k[0], subrun=k[1], evt=k[2], movement=st, first_changed_stage=fcs.get(k, "") if st != "stays selected" else "",
                         old_class=cat_o.get(k, (None, None, None))[0], old_category=cat_o.get(k, (None, None, None))[1], old_channel=cat_o.get(k, (None, None, None))[2],
                         new_class=cat_n.get(k, (None, None, None))[0], new_category=cat_n.get(k, (None, None, None))[1], new_channel=cat_n.get(k, (None, None, None))[2]))
    mv = pd.DataFrame(rows); mv.to_parquet(DER / "bnb_selection_movement.parquet", index=False)
    summ = mv.movement.value_counts().rename("N").reset_index(); summ.to_csv(OUT / "bnb_migration_summary.csv", index=False)
    mv[mv.movement != "stays selected"].groupby(["movement", "first_changed_stage"]).size().rename("N").reset_index().to_csv(OUT / "bnb_migration_first_changed_stage.csv", index=False)
    nonsig = mv[(mv.movement != "stays selected")].copy()
    nonsig["category"] = np.where(nonsig.movement.str.startswith("LEAVES"), nonsig.old_category, nonsig.new_category)
    nonsig["klass"] = np.where(nonsig.movement.str.startswith("LEAVES"), nonsig.old_class, nonsig.new_class)
    nonsig.groupby(["movement", "klass", "category"]).size().rename("N").reset_index().to_csv(OUT / "bnb_migration_by_category.csv", index=False)
    cats = sorted(set(co.index) | set(cn.index))
    ent = nonsig[(nonsig.movement.str.startswith("ENTERS")) & (nonsig.klass == "background")].category.value_counts(); lv = nonsig[(nonsig.movement.str.startswith("LEAVES")) & (nonsig.klass == "background")].category.value_counts()
    pd.DataFrame([dict(category=c, old=int(co.get(c, 0)), nov16=int(cn.get(c, 0)), difference=int(cn.get(c, 0)) - int(co.get(c, 0)), matched_enters=int(ent.get(c, 0)), matched_leaves=int(lv.get(c, 0))) for c in cats]
                 + [dict(category="TOTAL non-signal", old=int(co.sum()), nov16=int(cn.sum()), difference=int(cn.sum() - co.sum()), matched_enters=int(ent.sum()), matched_leaves=int(lv.sum()))]).to_csv(OUT / "bnb_category_old_vs_new.csv", index=False)
    # by channel
    chn = pd.DataFrame({"old": pd.Series(ch_o), "nov16": pd.Series(ch_n)}).fillna(0).astype(int); chn.loc["TOTAL"] = chn.sum(); chn.to_csv(OUT / "bnb_nonsignal_by_reco_channel.csv")
    # ---- natural NC-Delta in the BNB CV (descriptive, 117 events), same frozen selection
    nat = NS.to_signal_truth_table(sig); nat = nat[nat.in_region].reset_index(drop=True)
    rep_n, ta_n, tf_n, acc_n = RB.run_report(nat, nat.iloc[:0], ev_n, c_n, cfg, label="natural_bnb_cv_nov16", region="active_tpc")
    rep_o, ta_o, tf_o, _ = RB.run_report(nat, nat.iloc[:0], ev_o, c_o, cfg, label="natural_bnb_cv_old", region="active_tpc")
    nat_cf = pd.DataFrame(dict(stage=[s for s, _ in __import__("sbnd_single_photon").exclusive_signal.stage_defs(cfg)]))
    for lab, rep in (("old_fg1", rep_o), ("nov16", rep_n)):
        cf = rep["cutflow_any"]; cf = cf[cf.group == "all"].set_index("stage").N; nat_cf[lab] = [int(cf[s]) for s in nat_cf.stage]
    nat_cf["denominator"] = len(nat); nat_cf.to_csv(OUT / "bnb_natural_cv_cutflow.csv", index=False)
    # ---- BNB cumulative cutflow (events with any candidate at the stage), old and new
    fo_, fn_ = ev_stage_flags(c_o), ev_stage_flags(c_n)
    cfl = pd.DataFrame(dict(stage=STAGES, old_fg1=[int(fo_[s_].sum()) for s_ in STAGES], nov16=[int(fn_[s_].sum()) for s_ in STAGES]))
    cfl.to_csv(OUT / "bnb_cutflow_old_vs_nov16.csv", index=False)
    json.dump(dict(old=dict(selected=len(old_cls), non_signal=int(cls_o.get("background", 0)), classes=cls_o, channels=ch_o), nov16=dict(selected=len(new_cls), non_signal=int(cls_n.get("background", 0)), classes=cls_n, channels=ch_n),
                   pot=pot_cv_new, movement=mv.movement.value_counts().to_dict(), events_old=len(ev_o), events_new=len(ev_n), wc_valid_old=int(ev_o.wc_valid.sum()), wc_valid_new=int(ev_n.wc_valid.sum())),
              open(OUT / "bnb_summary.json", "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    print(tot.round(2).T.to_string()); print(summ.to_string(index=False)); print(pd.read_csv(OUT / "bnb_category_old_vs_new.csv").to_string(index=False)); print(nat_cf.to_string(index=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("stage", choices=["deep", "report"]); ap.add_argument("--workers", type=int, default=24); a = ap.parse_args()
    (stage_deep if a.stage == "deep" else report)(a)
