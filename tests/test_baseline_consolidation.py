"""Phase 19: the consolidated baseline headline numbers reproduce from the committed machine-readable summaries, and nothing frozen has silently changed.

Nothing here changes a selection flag, threshold, weight, vertex, type or policy.
"""
import hashlib
import json
import re
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / "tables"; B = T / "baseline_consolidation"; D = ROOT / "docs" / "analysis"
S = json.load(open(B / "summary.json"))
csv = lambda n: pd.read_csv(B / f"{n}.csv")
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def test_denominator_and_topology_split():
    s = S["signal"]; assert s["truth_denominator"] == 12427 and s["truth_by_class"] == {"0p": 5863, "1p": 5557, ">=2p": 1007}
    assert sum(s["truth_by_class"].values()) == 12427 and s["delta"] == {"Delta0": 6846, "Delta+": 5581} and sum(s["delta"].values()) == 12427
    j = json.load(open(T / "official_signal" / "official_active_tpc" / "summary.json")); assert j["n_truth"] == 12427 and j["truth_class"] == {"0p": 5863, "1p": 5557, ">=2p": 1007}


def test_efficiency_headlines():
    e = S["signal"]["eff"]
    assert e["any|all"][:2] == [1153, 12427] and abs(e["any|all"][2] - 0.0928) < 5e-5 and e["first|all"][:2] == [1101, 12427] and abs(e["first|all"][2] - 0.0886) < 5e-5
    for g, n, d, v in (("0p", 476, 5863, 0.0812), ("1p", 594, 5557, 0.1069), (">=2p", 83, 1007, 0.0824)):
        assert e[f"any|{g}"][:2] == [n, d] and abs(e[f"any|{g}"][2] - v) < 5e-5
    assert 476 + 594 + 83 == 1153 and 453 + 566 + 82 == 1101 and S["signal"]["final_any"] == 1153 and S["signal"]["final_first"] == 1101
    assert e["any|Delta0"][:2] == [521, 6846] and e["any|Delta+"][:2] == [632, 5581] and 521 + 632 == 1153
    for k, (n, d, p, lo, hi) in e.items():
        assert lo <= p <= hi and abs(p - n / d) < 1e-9


def test_cutflow_and_first_failure_closure():
    lb = csv("loss_budget").set_index("stage")
    assert [int(lb.loc[s, "cumulative_surviving"]) for s in ("wc.valid", "candidate", "> 20 MeV shower", "BDT evaluable", "numu", "other", "ncpi0", "nue", "n_20br1", "final")] == [12426, 11331, 8080, 8034, 5007, 2781, 1313, 1313, 1153, 1153]
    assert int(lb.first_failure_count.sum()) == 12427 and abs(lb.first_failure_fraction.sum() - 1) < 1e-4
    assert [int(lb.loc[s, "first_failure_count"]) for s in ("candidate", "> 20 MeV shower", "BDT evaluable", "numu", "other", "ncpi0", "nue", "n_20br1")] == [1095, 3251, 46, 3030, 2226, 1465, 0, 160]
    assert S["first_failure_cumulative_mismatch"] == {"numu": 3, "ncpi0": -3}                       # documented 3-event bookkeeping difference, inherited
    assert abs(lb.loc["final", "cumulative_efficiency"] - 1153 / 12427) < 1e-5


def test_migration_matrix_and_not_selected():
    assert S["migration_final"] == {"truth 0p": [425, 50, 1], "truth 1p": [93, 471, 30], "truth >=2p": [9, 35, 39]}
    assert S["not_selected"] == {"truth 0p": 5863 - 476, "truth 1p": 5557 - 594, "truth >=2p": 1007 - 83}
    reco = [sum(S["migration_final"][t][i] for t in S["migration_final"]) for i in range(3)]; assert reco == [527, 556, 70]                  # reco 1g0p / 1g1p / >=2p
    assert S["migration_matched_candidate"]["truth 1p"][:3] == [1739, 2643, 596]


def test_bnb_background_and_rates():
    b = S["background"]; assert b["selected_nonsignal"] == 635 and b["signal_like_removed"] == 14
    assert [b["by_channel"][c][0] for c in ("1g0p", "1g1p", "ge2p")] == [310, 230, 95] and sum(b["by_channel"][c][0] for c in b["by_channel"]) == 635
    assert abs(b["by_channel"]["1g0p"][1] - 1139.96) < 0.01 and abs(b["by_channel"]["1g1p"][1] - 845.77) < 0.01 and abs(b["total_rate_per_1e20"] - 2335.07) < 0.01
    comp = csv("bnb_background_composition_by_channel"); comp = comp[comp.category != "TOTAL"]; assert comp[comp.channel == "1g0p"]["count"].sum() == 310 and comp[comp.channel == "1g1p"]["count"].sum() == 230
    r = S["signal_rate"]; assert abs(r["total_per_1e20"] - 40.62) < 0.01 and abs(r["by_reco_channel"]["1g0p"] - 18.57) < 0.01 and abs(r["by_reco_channel"]["1g1p"] - 19.59) < 0.01
    assert abs(sum(r["by_reco_channel"].values()) - r["total_per_1e20"]) < 1e-6
    rr = csv("signal_and_bnb_background_rates"); assert "signal_over_beam_neutrino_background_reference_ratio" in rr.columns and not any(c.lower() in ("s_over_b", "purity", "significance") for c in rr.columns)


def test_natural_cv_counts():
    n = S["natural_cv"]; assert (n["n_events"], n["in_filter_box"], n["in_tpc_box"], n["selected_any"]) == (416, 128, 117, 13)
    assert abs(n["natural_final_fraction"] - 13 / 117) < 1e-9 and 0.5 < n["final_p_binom"] < 0.55 and n["ratio_95ci"][0] < 1 < n["ratio_95ci"][1]


def test_phase18_loss_share_correction_uses_the_truth_denominator():
    c = S["phase18_correction"]; assert c["true_denominator"] == 12427 and c["true_lost"] == 12427 - 1153 and c["phase18_denominator_events"] == 11331 and c["missing_from_phase18"] == 1096
    assert abs(c["numu_fail_share_corrected"] - 3031 / 11274) < 1e-9 and abs(c["compact_share_corrected"] - 1445 / 11274) < 1e-9
    p18 = json.load(open(T / "numu_compact_shower_audit" / "summary.json"))["loss_budget"]; assert p18["n_fail_numu"] == 3031 and p18["n_fail_numu_compact"] == 1445          # the pushed Phase-18 counts are untouched


def test_no_baseline_threshold_hash_or_convention_changed():
    cfg = ROOT / "configs" / "baseline_selection.yaml"; assert sha(cfg) == "f3251b785be6e52ff3e429000a0319a6df8e42d2016ace2f51c7650a38e2fb0b" == S["frozen"]["baseline_config_sha256"]
    th = {c["name"]: c["threshold"] for c in yaml.safe_load(open(cfg))["cuts"]}
    assert th["single_photon_numu_score_gt_0p4"] == 0.4 and th["single_photon_other_score_gt_0p2"] == 0.2 and th["single_photon_ncpi0_score_gt_m0p05"] == -0.05 and S["frozen"]["thresholds"] == {"numu": 0.4, "other": 0.2, "ncpi0": -0.05}
    assert S["frozen"]["numu_xml_sha256"] == "5886affbdb3a4499a4515ecc8d354eb1449e7c204d32f1cc54c1ec8868ead961"
    assert S["frozen"]["candidates_config_sha256"] == sha(ROOT / "configs" / "analysis_definition_candidates.yaml") == json.load(open(T / "analysis_definition_decisions" / "summary.json"))["metadata"]["analysis_definition_candidates_sha256"]
    assert S["frozen"]["candidate_policy"] == "any" and S["frozen"]["proton_threshold_mev"] == 35
    ref = Path("/exp/uboone/app/users/uboonepro/bbogart/wcp-uboone-bdt/weights")
    sums = (ROOT / "provenance" / "microboone_reference_SHA256SUMS.txt").read_text()
    assert "5886affbdb3a4499a4515ecc8d354eb1449e7c204d32f1cc54c1ec8868ead961" in sums
    if ref.exists():                                                                                    # on EAF: every frozen single-photon XML still matches its recorded hash
        for line in sums.splitlines():
            m = re.match(r"([0-9a-f]{64})\s+\S*?(single_photon_\w+\.xml)$", line.strip())
            if m and (ref / m.group(2)).exists():
                assert sha(ref / m.group(2)) == m.group(1), m.group(2)


def test_decisions_remain_open_and_headline_doc_states_it():
    t = (D / "NCDELTA_FROZEN_WIRECELL_BASELINE.md").read_text()
    assert t.count("OPEN ANALYSIS DECISION") >= 4 and "NOT collaboration-approved analysis definitions" in t and "| analysis FV | **none** |" in t
    low = (t + (D / "NCDELTA_FROZEN_BASELINE_EXECUTIVE_SUMMARY.md").read_text()).lower()
    for bad in ("final purity of", "s/b of", "significance of", "we recommend the", "retuned"):
        assert bad not in low
    assert "not an s/b" in low and "externally blocked" in low


def test_roadmap_matrix_matches_the_roadmap():
    road = (D / "NCDELTA_ANALYSIS_ROADMAP.md").read_text(); ids = {}
    for line in road.splitlines():
        m = re.match(r"\| \*\*([A-Z])\*\* \| (.*)", line)
        if m:
            ids[m.group(1)] = m.group(2)
    done = set("ABCOPQTUVY"); largely = set("MNSXZ")
    for k in done:
        assert "[DONE" in ids[k] or "completed" in ids[k], k
    for k in largely:
        assert "[LARGELY DONE" in ids[k], k
    for k in "DEF":
        assert "open decision" in ids[k], k
    for k in "GH":
        assert "blocked" in ids[k], k
    assert "queued" in ids["I"] and "queued" in ids["J"] and "queued" in ids["K"] and "deferred" in ids["L"]
    assert set(ids) == set("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    assert "| DONE | A B C O P Q T U V Y |" in (D / "NCDELTA_FROZEN_WIRECELL_BASELINE.md").read_text().replace("**", "")


def test_manifest_has_15_existing_figures_and_index_documents_exist():
    m = (D / "BASELINE_FIGURE_MANIFEST.md").read_text()
    figs = re.findall(r"^\| (\d+) \| .*?\| `(plots/[^`]+\.png)`", m, flags=re.M); assert [int(a) for a, _ in figs] == list(range(1, 16))
    for _, f in figs:
        assert (ROOT / f).exists(), f
    idx = (D / "NCDELTA_BASELINE_TECHNICAL_INDEX.md").read_text()
    for d in set(re.findall(r"`([A-Z0-9_]+\.md)`", idx)):
        assert (D / d).exists(), d
    rows = [l for l in idx.splitlines() if re.match(r"\| \d+ \|", l)]; assert len(rows) == 19
    for l in rows:
        for t in re.findall(r"`([a-z0-9_]+)`", l.split("|")[-5] + "|" + l.split("|")[-4]):
            if not t.endswith(".md"):
                assert (T / t).is_dir() or (ROOT / "plots" / t).is_dir(), t
