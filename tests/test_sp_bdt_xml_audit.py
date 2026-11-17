"""Pins the committed XML-audit outputs (tables/sp_bdt_xml_audit/summary.json) and the audit document's gate wording.
Reads committed files only (no XML needed)."""
import json
from pathlib import Path
R = Path(__file__).resolve().parents[1]
S = json.loads((R / "tables/sp_bdt_xml_audit/summary.json").read_text())
DOC = (R / "docs/analysis/YANDEL_THESIS_FROZEN_XML_COMPATIBILITY_AUDIT.md").read_text()


def test_hashes_match_recorded():
    assert all(S[m]["sha_match"] for m in ("numu", "other", "ncpi0", "nue"))
    assert S["ncpi0"]["sha256"].startswith("983a0d82") and S["other"]["sha256"].endswith("bb16")


def test_tree_counts_and_depth():
    assert {m: S[m]["n_trees"] for m in ("numu", "other", "ncpi0", "nue")} == {"numu": 300, "other": 215, "ncpi0": 400, "nue": 300}
    assert S["other"]["max_depth_splitlevels"] == 5 and S["ncpi0"]["max_depth_splitlevels"] == 6


def test_inputs_and_kine_pio_flag():
    assert (S["other"]["n_vars"], S["ncpi0"]["n_vars"]) == (146, 45)
    f = S["_dependency"]["ncpi0"]["kine_pio_flag"]
    assert f["splits"] == 23 and f["trees"] == 20
    assert "other" in S["_dependency"] and S["_dependency"]["other"]["numu_pair_split_share_pct"] > 7


def test_doc_gate_wording_and_no_training_claim():
    assert DOC.count("THESIS/XML PLAUSIBLY SAME MODEL") >= 2
    assert "BLOCKED" not in DOC.split("## 7. Gate decisions")[1].split("## 8.")[0].replace("Neither of the models is BLOCKED", "").replace("Neither model is BLOCKED", "")
    assert "6.70 %" in DOC and "NOT OBTAINED" in DOC
