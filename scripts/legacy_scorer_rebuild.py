#!/usr/bin/env python
"""Rebuild the headline Round-1 baseline products from the rescored candidate tables of ONE scorer configuration (NO training; same library code as the original products).

    source env/setup_eaf.sh
    python scripts/legacy_scorer_impact_scan.py                              # writes $SP_DATA/legacy_scorer_correction/{official,bnb}_candidates_{A_old,D_full}.parquet
    python scripts/legacy_scorer_rebuild.py --config D_full                   # -> tables/legacy_scorer_correction/source_faithful/   (an OVERLAY of tables/)
    python scripts/legacy_scorer_rebuild.py --config A_old --out <scratch>    # validation: must reproduce the committed as-run products byte for byte

The overlay mirrors the sub-paths of ``tables/`` that the consolidation reads, so ``SP_TABLES_OVERLAY=<out> python scripts/baseline_consolidation.py`` regenerates the
consolidated summary for the chosen configuration. The old (as-run) products are untouched.

Products: official signal (active TPC box) cutflow / efficiency / first failure / migration / expected rate (the same ``run_report`` + ``write_report`` of the original runner);
natural-CV rehearsal + its comparison with the official cutflow; selected BNB-CV non-signal background (events, channel, candidate-associated category from the stored ``deep`` truth association; ``scripts/legacy_scorer_deep_new.py`` adds the few candidates
selected only under the corrected scorer), its composition and rate model; the frozen WC efficiency on the SPINE-harmonised denominators.
"""
from __future__ import annotations
import argparse, json, os, sys, warnings
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); sys.path.insert(0, str(REPO / "scripts")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from scipy import stats
from sbnd_single_photon import background_mechanisms as BM, exclusive_signal as X, natural_signal as NS, prediction as P, selection as SEL
import run_official_signal_baseline as RB

SPD = Path(os.environ["SP_DATA"]); SPC = SPD / "legacy_scorer_correction"
CLS = {0: "0p", 1: "1p", 2: ">=2p"}


def eff(mask, col, tab):
    k = int((mask & tab[col].to_numpy(bool)).sum()); n = int(mask.sum()); f, l, h = X.binom_ci(k, n)
    return dict(numerator=k, denominator=n, efficiency=f, lo68=l, hi68=h)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--config", default="D_full", choices=["A_old", "D_full"]); ap.add_argument("--out", default=None); a = ap.parse_args()
    out = Path(a.out) if a.out else REPO / "tables" / "legacy_scorer_correction" / "source_faithful"; out.mkdir(parents=True, exist_ok=True)
    cfg = SEL.load_config(); Ta = SPD / "analysis_tables"; To, Tb = Ta / "official_gen2_ncdelta", Ta / "bnb_cv"
    ev_o = pd.read_parquet(To / "events.parquet"); c_o = pd.read_parquet(SPC / f"official_candidates_{a.config}.parquet")
    ev_b = pd.read_parquet(Tb / "events.parquet"); c_b = pd.read_parquet(SPC / f"bnb_candidates_{a.config}.parquet")
    base = SPD / "official_signal_baseline"; units = pd.read_parquet(SPD / "official_gen2_ncdelta_master" / "units.parquet")
    pot_sig = float(units[units.flatcaf_status == "flatcaf_available"].unit_pot.sum()); pot_cv = float(pd.read_parquet(Tb / "files.parquet").total_pot.sum())
    SIGD = out / "official_signal"; (SIGD / "official_active_tpc").mkdir(parents=True, exist_ok=True); (SIGD / "official_baseline").mkdir(exist_ok=True); (SIGD / "rehearsal_natural_bnb_cv").mkdir(exist_ok=True)
    (out / "background_mechanisms").mkdir(exist_ok=True); (out / "spine_harmonization").mkdir(exist_ok=True)

    # ---- official signal, active TPC box (the headline region)
    arr = pd.read_parquet(base / "signal_joined_active_tpc.parquet"); mis = pd.read_parquet(base / "signal_missing_active_tpc.parquet")
    rep, ta, tf, acc = RB.run_report(arr, mis, ev_o, c_o, cfg, label="official_gen2_ncdelta", region="active_tpc", pot_signal=pot_sig, exposure_pot=1e20)
    RB.write_report(rep, ta, tf, acc, SIGD / "official_active_tpc")
    # ---- natural CV rehearsal (the 117 natural NC-Delta events of the BNB CV in the TPC box)
    sn = pd.read_parquet(SPD / "natural_ncdelta_bnb_cv" / "signal_neutrinos.parquet"); nat = NS.to_signal_truth_table(sn); nat = nat[nat.in_region].reset_index(drop=True)
    rep_n, ta_n, tf_n, acc_n = RB.run_report(nat, nat.iloc[:0], ev_b, c_b, cfg, label="natural_bnb_cv_rehearsal", region="active_tpc")
    RB.write_report(rep_n, ta_n, tf_n, acc_n, SIGD / "rehearsal_natural_bnb_cv")
    rs = json.load(open(SIGD / "rehearsal_natural_bnb_cv" / "summary.json")); cfr = pd.read_csv(SIGD / "rehearsal_natural_bnb_cv" / "cutflow_A_any.csv"); cfo = rep["cutflow_any"]; rows = []
    for s in list(dict.fromkeys(cfo.stage)):
        o = cfo[(cfo.stage == s) & (cfo.group == "all")].iloc[0]; q = cfr[(cfr.stage == s) & (cfr.group == "all")]
        if len(q):
            q = q.iloc[0]; kr, nr, ko, no = int(q.N), int(q.denominator), int(o.N), int(o.denominator)
            rows.append(dict(stage=s, rehearsal=f"{kr}/{nr}", official=f"{ko}/{no}", rehearsal_frac=kr / nr, official_frac=ko / no, p_binom=float(stats.binomtest(kr, nr, ko / no).pvalue)))
    pd.DataFrame(rows).to_csv(SIGD / "official_baseline" / "natural_cv_cutflow_comparison.csv", index=False)

    # ---- BNB-CV selected events: truth category from the stored candidate association (light), event class from the natural-signal table
    deep = pd.read_parquet(SPD / "background_mechanisms" / "bnb_cv" / "deep.parquet"); sig = pd.read_parquet(SPD / "natural_ncdelta_bnb_cv" / "signal_neutrinos.parquet")
    dn = SPC / f"deep_new_{a.config}.parquet"                         # candidates selected only under this configuration: same `deep` stage run on them (scripts/legacy_scorer_deep_new.py)
    if dn.exists():
        deep = pd.concat([deep, pd.read_parquet(dn)], ignore_index=True)
    light = BM.add_categories(deep, sig)
    passing = c_b[c_b.pass_final.values].rename(columns={"c_nu_index": "nu_index"})
    sel = passing.merge(light.drop(columns=[c for c in light.columns if c in passing.columns and c not in BM.CKEY]), on=BM.CKEY, how="left", validate="one_to_one")
    assert len(sel) == len(passing) and sel.tm_top_nu.notna().all(), "selected candidates without a stored truth association"
    sig_ev = NS.classify_selected_events(passing.rename(columns={"nu_index": "c_nu_index"}), sig.rename(columns={"k": "nu_k"}))
    ev = BM.event_level(sel, sig_ev); accb = BM.accounting(ev); bgm = ev[ev.event_class == "background"]
    comp = BM.composition(bgm, pot_cv); comp.round(5).to_csv(out / "background_mechanisms" / "background_composition_by_channel.csv", index=False)
    tab = ev.assign(reco_channel=ev.reco_channel.replace({"ge2p_diag": "ge2p"})); cls = tab.event_class.value_counts().to_dict()
    bkc = P.bnb_background_component(tab, pot_cv, 1e20)
    cnt = {ch: int((tab[tab.event_class == "background"].reco_channel == ch).sum()) for ch in P.CHANNELS}
    model = dict(component="B_BNB_NEUTRINO", sample="bnb_cv", pot_cv=pot_cv, event_classes_in_table=cls, signal_like_removed=int(cls.get("signal_like", 0)), background_events=int(cls.get("background", 0)),
                 by_reco_channel={ch: dict(count=cnt[ch], rate_per_1e20_POT=bkc.values[ch], stat_unc_per_1e20_POT=bkc.stat_unc[ch]) for ch in P.CHANNELS},
                 uncertainty="statistical (Poisson) only; no cosmic-only component, no flux/xsec/detector systematics", nueCC_dedicated_sample="NOT included (control sample only)",
                 note="rate of selected non-signal CV events per 1e20 POT; the natural NC-Delta signal-like events are excluded")
    (SIGD / "background_rate_model.json").write_text(json.dumps(model, indent=1))
    ev.assign(config=a.config).to_csv(out / "background_mechanisms" / "selected_event_classes.csv", index=False)

    # ---- frozen WC efficiency on the SPINE-harmonised denominators (filter box event table; only the numerator A_final changes)
    arr_f = pd.read_parquet(base / "signal_joined_filter_box.parquet"); mis_f = pd.read_parquet(base / "signal_missing_filter_box.parquet")
    _, taf, tff, _ = RB.run_report(arr_f, mis_f, ev_o, c_o, cfg, label="official_gen2_ncdelta", region="filter_box")
    t = pd.read_parquet(SPD / "spine_harmonization" / "official_ncdelta" / "event_flags_and_table.parquet")
    RSE = ["run", "subrun", "evt"]
    t = t.drop(columns=["A_final", "A_final_first"]).merge(taf[RSE + ["A_final"]], on=RSE, how="left", validate="one_to_one").merge(tff[RSE + ["A_final"]].rename(columns={"A_final": "A_final_first"}), on=RSE, how="left", validate="one_to_one")
    t["A_final"] = t.A_final.fillna(False).astype(bool); t["A_final_first"] = t.A_final_first.fillna(False).astype(bool)
    defs = {"loose official, filter box (13,773)": np.ones(len(t), bool), "loose official, provisional TPC box (current baseline)": t.tpc_box.to_numpy(), "SPINE FV only": t.spine_fv.to_numpy(),
            "A spine_technote_threshold": t.spine_technote_threshold.to_numpy(), "B spine_technote_strict = HARMONIZED ALL": t.spine_truth_signal.to_numpy(),
            "harmonized 0p50": t.spine_truth_0p50.to_numpy(), "harmonized Np50": t.spine_truth_Np50.to_numpy(), "B' strict (literal GENIE record)": t.spine_technote_strict_record.to_numpy(),
            "spine_source_signal (Delta resnum set)": t.spine_source_signal.to_numpy(), "spine_source_signal + neutrino2026 veto": t.spine_source_signal_veto2026.to_numpy()}
    for k, nm in ((0, "loose TPC box, truth 0p (35 MeV)"), (1, "loose TPC box, truth 1p (35 MeV)"), (2, "loose TPC box, truth >=2p (35 MeV)")):
        defs[nm] = (t.tpc_box & (t.truth35 == k)).to_numpy()
    E = pd.DataFrame([dict(denominator_set=nm, policy=pol, **eff(m, col, t)) for nm, m in defs.items() for pol, col in (("any", "A_final"), ("first", "A_final_first"))])
    E.to_csv(out / "spine_harmonization" / "wc_efficiency_on_harmonized.csv", index=False)
    res = dict(config=a.config, official_final_any=rep["final_any"]["total"], official_final_first=rep["final_first"]["total"], reco_channel=rep["final_any"]["reco_channel"],
               natural_final_any=rep_n["final_any"]["total"], bnb_accounting={k: accb[k] for k in ("total", "signal_like", "background", "mixed", "background_by_channel", "background_by_category")},
               filter_box_final_any=int(t.A_final.sum()), accounting_ok=bool(acc["ok"]))
    (out / "rebuild_summary.json").write_text(json.dumps(res, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))); print(json.dumps(res, default=lambda o: o.item() if hasattr(o, "item") else str(o)))


if __name__ == "__main__":
    main()
