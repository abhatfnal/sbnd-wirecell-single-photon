"""Legacy-scorer correction: closure of the impact table, of the event flips and of the rebuilt baseline; source facts; nothing frozen changed.

Reads only committed tables (no $SP_DATA, no ROOT). The source-tree checks run where the MicroBooNE tree exists (EAF).
"""
import hashlib
import json
import re
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / "tables" / "legacy_scorer_correction"; SF = T / "source_faithful"; D = ROOT / "docs"
OLD = json.load(open(ROOT / "tables" / "baseline_consolidation" / "summary.json")); NEW = json.load(open(SF / "baseline_consolidation" / "summary.json"))
IMP = pd.read_csv(T / "impact_configurations.csv").set_index("config"); FL = pd.read_csv(T / "event_flips.csv")
CF = {k: pd.read_csv(T / f"cutflow_by_config_{k}.csv").set_index("stage") for k in ("signal", "bnb_cv", "natural_cv")}


def test_impact_table_closure_and_as_run_reproduction():
    a, b, c, d = (IMP.loc[k] for k in ("A_old", "B_score_only", "C_pio_only", "D_full"))
    assert (a.official_selected_any, a.official_selected_first, a.N_truth) == (OLD["signal"]["final_any"], OLD["signal"]["final_first"], 12427) == (1153, 1101, 12427)    # as-run reproduces Phase 19
    assert a.bnb_selected_events == 649 == OLD["background"]["selected_nonsignal"] + OLD["background"]["signal_like_removed"] and a.natural_selected == OLD["natural_cv"]["selected_any"] == 13
    assert [int(a.reco_1g0p), int(a.reco_1g1p), int(a.reco_ge2p)] == [527, 556, 70]
    assert (d.official_selected_any, d.official_selected_first) == (NEW["signal"]["final_any"], NEW["signal"]["final_first"]) == (833, 795)
    assert d.bnb_selected_events == NEW["background"]["selected_nonsignal"] + NEW["background"]["signal_like_removed"] == 291 and d.natural_selected == NEW["natural_cv"]["selected_any"] == 8
    assert abs(d.efficiency - 833 / 12427) < 1e-12 and abs(a.efficiency - 1153 / 12427) < 1e-12
    for k in IMP.index:                                                                    # reco channels sum to the selected events
        assert IMP.loc[k, ["reco_1g0p", "reco_1g1p", "reco_ge2p"]].sum() == IMP.loc[k, "official_selected_any"]
    assert (b.official_selected_any, c.official_selected_any) == (831, 1161)               # decomposition: score convention dominates, the flag is small
    assert abs(b.official_selected_any - a.official_selected_any) > 20 * abs(c.official_selected_any - a.official_selected_any)
    assert d.bnb_selected_signal_like + NEW["background"]["selected_nonsignal"] == d.bnb_selected_events and NEW["background"]["signal_like_removed"] == 9


def test_materiality_rule_is_met_and_stated():
    half = (OLD["signal"]["eff"]["any|all"][4] - OLD["signal"]["eff"]["any|all"][3]) / 2
    assert abs(NEW["signal"]["eff"]["any|all"][2] - OLD["signal"]["eff"]["any|all"][2]) > 5 * half
    assert abs(649 - 291) > 10 * 649 ** 0.5
    t = (D / "analysis" / "LEGACY_SCORER_CORRECTION_IMPACT.md").read_text(); assert "**MATERIAL." in t and "HISTORICAL AS-RUN BASELINE" in t and "833 / 12,427 = 6.70 %" in t


def test_cutflows_close_and_are_monotone():
    for k, stages in (("signal", ["wc_valid", "candidate", "n20mev", "bdt_evaluable", "numu", "other", "ncpi0", "nue", "n20br1", "final"]), ("natural_cv", ["wc_valid", "candidate", "n20mev", "bdt_evaluable", "numu", "other", "ncpi0", "nue", "n20br1", "final"]),
                      ("bnb_cv", ["candidate", "n20mev", "numu", "other", "ncpi0", "nue", "n20br1", "FINAL"])):
        t = CF[k]
        for cfg in IMP.index:
            v = [int(t.loc[s, cfg]) for s in stages]; assert all(x >= y for x, y in zip(v, v[1:])), (k, cfg, v)
    for cfg in IMP.index:
        assert CF["signal"].loc["final", cfg] == IMP.loc[cfg, "official_selected_any"] and CF["bnb_cv"].loc["FINAL", cfg] == IMP.loc[cfg, "bnb_selected_events"] and CF["natural_cv"].loc["final", cfg] == IMP.loc[cfg, "natural_selected"]
    assert list(CF["signal"].loc[["candidate", "n20mev", "bdt_evaluable"], "A_old"]) == list(CF["signal"].loc[["candidate", "n20mev", "bdt_evaluable"], "D_full"]) == [11331, 8080, 8034]   # BDT-independent stages
    assert CF["signal"].loc["nue", "A_old"] == CF["signal"].loc["ncpi0", "A_old"] == 1313 and CF["signal"].loc["nue", "D_full"] < CF["signal"].loc["ncpi0", "D_full"]            # nue vacuous as run, a real stage corrected


def test_event_flip_closure():
    for cfg in ("B_score_only", "C_pio_only", "D_full"):
        for smp, n_old, n_new in (("official", 1153, IMP.loc[cfg, "official_selected_any"]), ("bnb_cv", 649, IMP.loc[cfg, "bnb_selected_events"])):
            f = FL[(FL.config == cfg) & (FL["sample"] == smp)].flip.value_counts()
            up, pf, pn, uf = (int(f.get(k, 0)) for k in ("unchanged_pass", "old_pass_new_fail", "old_fail_new_pass", "unchanged_fail"))
            assert up + pf == n_old and up + pn == n_new, (cfg, smp)
            if smp == "official":
                assert up + pf + pn + uf == 12427
    S = pd.read_csv(T / "flip_summary.csv")
    for cfg in ("B_score_only", "C_pio_only", "D_full"):
        for smp in ("official", "bnb_cv"):
            for fl in ("old_pass_new_fail", "old_fail_new_pass"):
                n = int(((FL.config == cfg) & (FL["sample"] == smp) & (FL.flip == fl)).sum()); g = S[(S.config == cfg) & (S["sample"] == smp) & (S.flip == fl)]
                assert int(g[g.dimension == "stage"].N.sum()) == n, (cfg, smp, fl)                     # the first-stage summary partitions the flips
                if smp == "official":
                    assert int(g[g.dimension == "truth"].N.sum()) == n and int(g[g.dimension == "delta"].N.sum()) == n
    d = S[(S.config == "D_full") & (S["sample"] == "official") & (S.flip == "old_pass_new_fail") & (S.dimension == "stage")].set_index("value").N
    assert d["fail_nue"] == 312 and d.sum() == 335                                                  # the nue stage drives the correction
    assert (S[(S.config == "C_pio_only") & (S.flip == "old_pass_new_fail") & (S.dimension == "stage")].value.isin(["fail_ncpi0", "ncpi0"])).all()         # the flag only touches ncpi0


def test_rebuilt_baseline_is_self_consistent():
    s = NEW["signal"]; assert s["truth_denominator"] == 12427 and sum(s["truth_by_class"].values()) == 12427 and s["final_any"] == 833
    assert s["eff"]["any|all"][:2] == [833, 12427] and s["eff"]["first|all"][:2] == [795, 12427]
    cls = sum(s["eff"][f"any|{g}"][0] for g in ("0p", "1p", ">=2p")); assert cls == 833 and s["eff"]["any|Delta0"][0] + s["eff"]["any|Delta+"][0] == 833
    for k, (n, den, p, lo, hi) in s["eff"].items():
        assert lo <= p <= hi and abs(p - n / den) < 1e-9
    m = NEW["migration_final"]; assert m == {"truth 0p": [342, 30, 1], "truth 1p": [61, 336, 19], "truth >=2p": [5, 11, 28]}
    assert sum(sum(v) for v in m.values()) == 833 and [sum(m[t][i] for t in m) for i in range(3)] == [408, 377, 48]
    lb = NEW["loss_budget"]
    assert sum(v[2] for k, v in lb.items() if k != "final") + 833 == 12427                           # exclusive first failures + selected = the truth denominator
    assert lb["nue"][0] == 893 and lb["nue"][2] == 412 and OLD["loss_budget"]["nue"][2] == 0
    b = NEW["background"]; assert sum(v[0] for v in b["by_channel"].values()) == b["selected_nonsignal"] == 282 and b["signal_like_removed"] == 9 and b["by_channel"]["1g0p"][0] == 150
    comp = pd.read_csv(SF / "background_mechanisms" / "background_composition_by_channel.csv"); tot = comp[comp.category == "TOTAL"].set_index("channel")["count"]
    assert tot.sum() == 282 and comp[comp.category != "TOTAL"]["count"].sum() == 282
    assert comp[(comp.category == "NUE_CC")]["count"].sum() == 1                                      # as run: 175
    assert abs(NEW["signal_rate"]["total_per_1e20"] - 29.346) < 5e-3 and abs(sum(NEW["signal_rate"]["by_reco_channel"].values()) - NEW["signal_rate"]["total_per_1e20"]) < 1e-6
    assert NEW["frozen"]["scorer_mode"] == "legacy_source_faithful" and "scorer_mode" not in OLD["frozen"]
    assert NEW["frozen"]["thresholds"] == OLD["frozen"]["thresholds"] == {"numu": 0.4, "other": 0.2, "ncpi0": -0.05}       # no threshold changed
    assert NEW["natural_cv"]["selected_any"] == 8 and abs(NEW["natural_cv"]["final_p_binom"] - 0.854) < 2e-3
    h = {r["denominator_set"]: r for r in pd.read_csv(SF / "spine_harmonization" / "wc_efficiency_on_harmonized.csv").query("policy == 'any'").to_dict("records")}
    assert h["B spine_technote_strict = HARMONIZED ALL"]["numerator"] == 685 and h["loose official, provisional TPC box (current baseline)"]["numerator"] == 833


def test_old_products_preserved_and_new_ones_separate():
    assert OLD["signal"]["final_any"] == 1153 and OLD["background"]["selected_nonsignal"] == 635 and OLD["migration_final"]["truth 1p"] == [93, 471, 30]                    # historical products untouched
    assert (ROOT / "tables" / "baseline_consolidation" / "summary.json").read_bytes() != (SF / "baseline_consolidation" / "summary.json").read_bytes()
    assert {p.name for p in (T).iterdir()} >= {"source_faithful", "impact_configurations.csv", "event_flips.csv", "threshold_translation.csv"}
    assert (D / "analysis" / "NCDELTA_FROZEN_WIRECELL_BASELINE.md").read_text().count("HISTORICAL AS-RUN BASELINE") == 1


def test_threshold_translation_table():
    t = pd.read_csv(T / "threshold_translation.csv").set_index("model")
    assert list(t.frozen_cut_on_score) == [0.4, 0.2, -0.05, -1.0] and list(t.as_run_cut_on_v) == [0.4, 0.2, -0.05, -1.0]
    for m, v in (("numu", 0.43051), ("other", 0.22627), ("ncpi0", -0.05750), ("nue", -0.81818)):
        assert abs(t.loc[m, "equivalent_cut_on_v"] - v) < 1e-5


def test_delta_mass_subset_validation_and_mechanism_table():
    d = pd.read_csv(T / "delta_mass_subset.csv").set_index("config")
    assert (d.loc["A_old", "decay_pairs"], round(d.loc["A_old", "median_mev"], 2), round(d.loc["A_old", "p16_mev"], 1), round(d.loc["A_old", "p84_mev"], 1)) == (348, 2.77, -44.1, 33.7)     # as-run restriction reproduces Phase 11
    assert d.loc["D_full", "decay_pairs"] < d.loc["A_old", "decay_pairs"] and abs(d.loc["D_full", "median_mev"]) < 1.0
    m = pd.read_csv(T / "mechanism_recheck.csv"); g = lambda item, grp, sc: m[(m.item == item) & (m.group == grp) & (m.scorer == sc)].iloc[0]
    assert abs(g("numu_survival", "compact (length < 20 cm)", "as_run_v>0.4").value - 0.293) < 1e-3
    assert g("numu_survival", "compact (length < 20 cm)", "as_run_v>0.4").value < g("numu_survival", "not compact (>= 20 cm)", "as_run_v>0.4").value
    assert g("stage_conditional_survival", "nue | truth all", "as_run").value == 1.0 and abs(g("stage_conditional_survival", "nue | truth all", "source_faithful").value - 0.684) < 1e-3


def test_slide_number_table_marks_every_changed_number():
    d = pd.read_csv(D / "presentation" / "ROUND1_CORRECTED_SLIDE_NUMBERS.csv"); assert len(d) == 119 and d.status.str.startswith("UPDATE").sum() > 20
    x = d[d.meaning.str.contains("efficiency any, total")].iloc[0]; assert x.status == "UPDATE" and x.corrected_value.startswith("0.0670")
    assert not d[d.displayed_old == "12,427"].status.str.startswith("UPDATE").any()                  # the truth denominator is unchanged


def test_presentation_impact_covers_every_slide():
    t = (D / "presentation" / "ROUND1_SCORER_CORRECTION_PRESENTATION_IMPACT.md").read_text()
    for i in range(1, 13):
        assert re.search(rf"^\| {i} \|", t, flags=re.M), i
    for k in ("O1", "O2", "O3") + tuple(f"B{j:02d}" for j in range(1, 16)):
        assert re.search(rf"^\| {k} \|", t, flags=re.M), k
    assert "PPTX is NOT touched" in t and "6.70 %" in t
    low = t.lower()
    for bad in ("purity of", "s/b of", "significance of"):
        assert bad not in low


def test_round2_contract_names_three_reference_points():
    t = (D / "analysis" / "ROUND2_EVALUATION_CONTRACT_SCORER_BASELINES.md").read_text()
    assert "R1-as-run" in t and "R1-source-faithful" in t and "**R2**" in t and "never against the accidental as-run" in t and "Training hygiene" in t


def test_source_facts_in_the_microboone_tree_if_present():
    src = Path("/exp/uboone/app/users/uboonepro/bbogart/wcp-uboone-bdt")
    if not src.exists():
        pytest.skip("MicroBooNE source tree not on this machine")
    h = (src / "inc" / "WCPLEEANA" / "bdt.h").read_text()
    for m in ("numu", "other", "ncpi0", "nue"):
        blk = h[h.index(f"float LEEana::cal_single_photon_{m}_bdts_xgboost"):]; blk = blk[: blk.index("return val;")]
        assert "TMath::Log10( (1+val1)/(1-val1) )" in blk and 'reader.EvaluateMVA("MyBDT")' in blk
    c = (src / "apps" / "bdt_convert.cxx").read_text()
    assert c.index("temp_kine_pio_flag = 0;") < c.index("tagger.single_photon_numu_score = cal_single_photon_numu_bdts_xgboost") and 'reader_single_photon_ncpi0.AddVariable("kine_pio_flag",&temp_kine_pio_flag);' in c
    cuts = (src / "inc" / "WCPLEEANA" / "cuts.h").read_text(); i = cuts.index("bool LEEana::is_singlephoton_sel")
    assert all(s in cuts[i: i + 700] for s in ("single_photon_numu_score > 0.4", "single_photon_other_score > 0.2", "single_photon_ncpi0_score > -0.05", "single_photon_nue_score > -1.0"))


def test_frozen_config_and_xml_hashes_unchanged():
    assert hashlib.sha256((ROOT / "configs" / "baseline_selection.yaml").read_bytes()).hexdigest() == "f3251b785be6e52ff3e429000a0319a6df8e42d2016ace2f51c7650a38e2fb0b"
    assert "5886affbdb3a4499a4515ecc8d354eb1449e7c204d32f1cc54c1ec8868ead961" in (ROOT / "provenance" / "microboone_reference_SHA256SUMS.txt").read_text()
    code = "".join((ROOT / "scripts" / f).read_text() for f in ("legacy_scorer_impact_scan.py", "legacy_scorer_rebuild.py", "legacy_scorer_ncpi0_scan.py", "legacy_scorer_deep_new.py"))
    assert not re.search(r"\.fit\(|train_test_split|TMVA::Factory|GradientBoosting|xgboost", code)   # no training code, no official sample used to train
