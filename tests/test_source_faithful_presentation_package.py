"""The corrected presentation handoff: every number traces to a committed corrected table, stale values appear only as 'do not use' / historical, the package is complete and self-consistent.

Reads committed files only (no $SP_DATA); the PPTX is out of scope.
"""
import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]; P = ROOT / "docs" / "presentation"; TC = ROOT / "tables" / "legacy_scorer_correction"
NUM = json.load(open(P / "NCDELTA_SOURCE_FAITHFUL_ROUND1_SLIDE_NUMBERS.json")); NEW = json.load(open(TC / "source_faithful" / "baseline_consolidation" / "summary.json"))
HAND = (P / "NCDELTA_SOURCE_FAITHFUL_PRESENTATION_HANDOFF.md").read_text(); OUTL = (P / "NCDELTA_SOURCE_FAITHFUL_ROUND1_PRESENTATION_OUTLINE.md").read_text()
ROWS = {r["quantity"]: r for r in NUM["numbers"]}
STATUS = set(NUM["statuses"])


def val(q):
    return ROWS[q]["display"]


def test_numbers_file_structure_and_sources_exist():
    assert STATUS == {"AUTHORITATIVE CORRECTED", "RECONSTRUCTION-ONLY UNCHANGED", "HISTORICAL AS-RUN", "REVIEW / DO NOT USE"}
    assert len(NUM["numbers"]) > 100 and all(r["status"] in STATUS for r in NUM["numbers"])
    for r in NUM["numbers"]:
        assert (ROOT / r["source"]).exists(), r["source"]
        assert r["locator"] and r["unit"] and r["slide"]
    assert not any(r["status"] == "AUTHORITATIVE CORRECTED" and "baseline_consolidation/summary.json" in r["source"] and "source_faithful" not in r["source"] for r in NUM["numbers"])   # no corrected number sourced from the as-run summary
    for r in NUM["numbers"]:
        if r["status"] == "HISTORICAL AS-RUN":
            assert r["slide"] in ("backup", "9", "11") and ("as-run" in r["quantity"] or "historical" in r["quantity"] or r["quantity"].startswith("scorer decomposition")), r["quantity"]


def test_headline_values_match_the_corrected_summary():
    s = NEW["signal"]; assert s["final_any"] == 833 and val("selected events, policy any") == "833" and val("efficiency, policy any") == "6.70 %"
    assert val("68 % interval of the efficiency") == "6.48-6.94 %"
    assert [val(f"efficiency, truth {g}") for g in ("0p", "1p", ">=2p")] == ["6.36 %", "7.49 %", "4.37 %"]
    assert [val(f"cumulative surviving: {k}") for k in ("wc.valid", "candidate", "> 20 MeV shower", "BDT evaluable", "numu", "other", "ncpi0", "nue", "n_20br1", "final")] == ["12,426", "11,331", "8,080", "8,034", "4,943", "2,717", "1,305", "893", "833", "833"]
    assert [val(f"exclusive first failure: {k}") for k in ("candidate", "shower", "numu", "other", "ncpi0", "nue", "n_20br1")] == ["8.8 %", "26.2 %", "24.9 %", "17.9 %", "11.3 %", "3.3 %", "0.5 %"]
    assert val("nue cumulative-stage signal loss") == "412" and val("as-run nue-CC events that leave the selection") == "174" and val("intrinsic nue-CC events selected, corrected") == "1" and val("intrinsic nue-CC events selected, as run (historical)") == "175"
    assert val("selected non-signal BNB-CV events") == "282" and val("by reco channel 1g0p / 1g1p / >=2p") == "150 / 93 / 39" and val("signal rate per 1e20 POT, provisional TPC box (total)") == "29.3"
    assert val("natural NC-Delta selected / in the TPC box") == "8 / 117" and val("binomial compatibility p-value") == "0.85"
    assert val("numu survival, compact < 20 cm") == "28.3 %" and val("numu survival, not compact >= 20 cm") == "72.8 %"
    assert (val("selected truth-matched decay pairs"), val("median(M_reco - M_true_decay)"), val("68 % interval of M_reco - M_true_decay")) == ("251", "-0.1", "[-44.5, +23.4]")
    assert [val(f"diagonal fraction truth {g}") for g in ("0p", "1p", ">=2p")] == ["91.7 %", "80.8 %", "63.6 %"]
    assert val("final migration truth 0p -> reco 0p / 1p / >=2p") == "342 / 30 / 1" and val("final migration truth 1p -> reco 0p / 1p / >=2p") == "61 / 336 / 19" and val("final migration truth >=2p -> reco 0p / 1p / >=2p") == "5 / 11 / 28"
    imp = pd.read_csv(TC / "impact_configurations.csv").set_index("config"); assert [int(imp.loc[k, "official_selected_any"]) for k in ("A_old", "B_score_only", "C_pio_only", "D_full")] == [1153, 831, 1161, 833]
    assert ROWS["historical as-run efficiency (the superseded headline)"]["status"] == "HISTORICAL AS-RUN" and ROWS["historical as-run selected non-signal BNB-CV"]["status"] == "HISTORICAL AS-RUN"


def test_review_classification_is_complete():
    rv = NUM["review_classification"]; assert len(rv) == 58
    assert {r["classification"] for r in rv} <= {"SAFE UNCHANGED", "CORRECTED VALUE EXISTS", "NEEDS RECOMPUTE", "DROP FROM PRESENTATION"}
    old = pd.read_csv(P / "ROUND1_CORRECTED_SLIDE_NUMBERS.csv"); assert len(rv) == int(old.status.str.startswith("REVIEW").sum())
    for r in rv:
        if r["classification"] == "CORRECTED VALUE EXISTS":
            assert r["corrected_value"], r
    d = {r["old_displayed"]: r for r in rv}
    assert d["29.8 %"]["classification"] == "DROP FROM PRESENTATION" and d["+2.8 MeV, [-44, +34] MeV"]["corrected_value"].startswith("-0.1 MeV") and d["27.6 %"]["classification"] == "SAFE UNCHANGED"


def test_stale_values_only_in_do_not_use_or_historical_context():
    stale = re.compile(r"9\.28|1,153|\b1153\b|\b635\b|\b310 ?/ ?230|40\.6|13 ?/ ?117|\+2\.8|425 / 471 / 39|nue CC 17|nue CC 37|\b4\.51")
    flag = re.compile(r"do not|don't|never|historical|superseded|as-run|as run|earlier|old |not |must not", re.I)
    for name, text in (("handoff", HAND), ("outline", OUTL)):
        for i, line in enumerate(text.splitlines(), 1):
            if stale.search(line):
                assert flag.search(line), (name, i, line[:120])
    for name in ("NCDELTA_SOURCE_FAITHFUL_ROUND1_SLIDE_NUMBERS.md",):
        for line in (P / name).read_text().splitlines():
            if stale.search(line) and line.startswith("|"):
                assert "HISTORICAL AS-RUN" in line or "DROP FROM PRESENTATION" in line or "REVIEW" in line or "NEEDS RECOMPUTE" in line or "retired" in line or "superseded" in line or "SAFE" in line or "CORRECTED VALUE EXISTS" in line, line[:140]


def test_nue_wording_and_headlines_in_the_handoff():
    assert "412" in HAND and "174 of the 175" in HAND and "trade-off" in HAND and "Xuyang" in HAND
    for line in HAND.splitlines():
        if re.search(r"removes? (no|nothing)", line, re.I):
            assert re.search(r"do not|never|not say", line, re.I), line[:120]
    for must in ("833 / 12,427 = 6.70 %", "282", "150 / 93 / 39", "251", "−0.1 MeV", "[−44.5, +23.4]", "91.7 % / 80.8 % / 63.6 %", "28.3 %", "72.8 %", "29.3 per 1e20 POT", "8 / 117", "p = 0.85", "score = log10((1+v)/(1−v))"):
        assert must in HAND, must
    assert "kine_pio_flag" in HAND and "831" in HAND and "1,161" in HAND


def test_handoff_structure_slides_backup_qa_and_prohibitions():
    assert len(re.findall(r"^### Slide \d+:", HAND, flags=re.M)) == 14 == len(re.findall(r"^### Slide \d+:", OUTL, flags=re.M))
    for h in ("## 1. Purpose of the talk", "## 2. Critical terminology", "## 3. Analysis scope", "## 4. Corrected headline", "## 5. Main slides", "## 6. Backup slides", "## 7. Questions Avinay should be ready for", "## 8. Transition from Nate", "## 9. Round-2 plan", "## 10. Things the presentation Claude must NOT do"):
        assert h in HAND, h
    assert len(re.findall(r"^\*\*Q: ", HAND, flags=re.M)) >= 15
    for q in ("Why did the efficiency change", "Was the physics analysis wrong", "What exactly was wrong", "Why does nue now remove so much signal", "Does nue retraining risk", "Why retrain the BDTs", "Why are the 0p and 1p", "Why can Delta0", "How do fragmentation", "What will change in Round 2", "training and which for evaluation", "Why no purity", "Nate's inclusive", "SPINE comparison", "validated against stored MicroBooNE"):
        assert q in HAND, q
    sec = HAND.split("## 10. Things the presentation Claude must NOT do")[1]
    for must in ("9.28", "635", "S/B", "Delta0 with 0p", "decay nucleon", "retraining is complete", "causality", "4.51", "REVIEW", "stored MicroBooNE scores"):
        assert must in sec, must
    r2 = HAND.split("## 9. Round-2 plan")[1].split("## 10.")[0]
    for must in ("Snehadri", "Xuyang", "Avinay", "Haiwang", "Aurora = training", "fg1 = evaluation", "R1-source-faithful = 6.70 %", "Neither BDT has been trained"):
        assert must in r2, must
    assert "Nate has just shown the inclusive single-photon picture" in HAND and "8/89" not in HAND and "8 / 89" not in HAND                    # the numerical Nate NC-Delta check is dropped
    for s in re.findall(r"^- \*\*Speaker notes \(30–60 s\):\*\* (.*)$", OUTL, flags=re.M):
        assert 25 <= len(s.split()) <= 140


def test_asset_manifest_paths_and_assets():
    m = pd.read_csv(P / "NCDELTA_SOURCE_FAITHFUL_ROUND1_SLIDE_ASSETS.csv"); assert set(m.main_or_backup) == {"main", "backup", "DO NOT USE"}
    for r in m[m.main_or_backup != "DO NOT USE"].itertuples():
        if r.asset_path.startswith("presentation_assets/"):
            assert (ROOT / r.asset_path).exists(), r.asset_path
    for r in m[m.main_or_backup == "main"].itertuples():
        assert str(r.old_version_must_not_be_used) and "9.28" not in r.asset_path
    for f in ("02_cutflow", "03_loss_budget", "05_numu_compactness", "08_migration_matrix", "09_delta_mass_residual", "10_backgrounds", "11_rates", "12_nue_tradeoff", "14_natural_cv"):
        assert (ROOT / "presentation_assets" / "ncdelta_source_faithful" / f"{f}.png").stat().st_size > 5000, f
    assert (ROOT / "presentation_assets" / "ncdelta_source_faithful" / "backup" / "B01_scorer_correction.png").exists()
    for tex in HAND.split("## 5. Main slides")[1].split("## 6.")[0].split("Recommended graphic:**")[1:]:
        for p in re.findall(r"presentation_assets/ncdelta_source_faithful/[\w./]+\.png", tex.split("\n")[0]):
            assert (ROOT / p).exists(), p


def test_historical_package_is_marked_superseded():
    for f in (P / "NCDELTA_BASELINE_PRESENTATION_OUTLINE.md", P / "NCDELTA_BASELINE_SLIDE_NUMBERS.md", ROOT / "presentation_assets" / "ncdelta_baseline" / "README_HISTORICAL.md"):
        t = f.read_text(); assert ("SUPERSEDED" in t or "superseded" in t) and "HISTORICAL AS-RUN" in t, f
    assert "NCDELTA_SOURCE_FAITHFUL" in (P / "NCDELTA_BASELINE_SLIDE_NUMBERS.md").read_text()


def test_no_pptx_and_no_analysis_code_touched():
    assert not list(ROOT.rglob("*.pptx"))
    import hashlib
    assert hashlib.sha256((ROOT / "configs" / "baseline_selection.yaml").read_bytes()).hexdigest() == "f3251b785be6e52ff3e429000a0319a6df8e42d2016ace2f51c7650a38e2fb0b"


def test_round2_status_wording_after_thesis_audit():
    """ncpi0/other targets are recovered (not 'under audit'); DL vertexing is not claimed frozen; nothing is trained."""
    for name in ("NCDELTA_SOURCE_FAITHFUL_PRESENTATION_HANDOFF.md", "NCDELTA_SOURCE_FAITHFUL_ROUND1_PRESENTATION_OUTLINE.md"):
        t = (Path(__file__).resolve().parents[1] / "docs/presentation" / name).read_text()
        low = t.lower()
        assert "under source audit" not in low and "being source-audited" not in low and "being audited" not in low
        assert "updated dl vertexing is being established / will be frozen for round 2" in low
        assert "dl vertexing (frozen)" not in low
        assert "recovered from the yandel thesis" in low and "cosmic / off-beam" in low
        assert "freeze updated dl vertexing" in low and "independent eaf evaluation against r1-source-faithful" in low
