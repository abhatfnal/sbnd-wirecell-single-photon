import hashlib
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from sbnd_single_photon import signal_arrival as A

REPO = Path(__file__).resolve().parents[1]


def _exp():
    return pd.DataFrame(dict(run=[1, 1, 2, 3], subrun=[1, 1, 1, 1], evt=[10, 11, 12, 13], reco1_unit=["reco1-A.root", "reco1-A.root", "reco1-B.root", "reco1-C.root"]))


def _inc(rows):
    return pd.DataFrame(rows, columns=["run", "subrun", "evt", "wc_valid", "unit"])


def test_unit_name_normalisation_across_file_kinds():
    n = A.normalize_unit_name
    assert n("reco1-detsim-x_ncdeltarad.root") == n("reco2-reco1-detsim-x_ncdeltarad.flat.caf.root") == n("/pnfs/a/b/reco2-reco1-detsim-x_ncdeltarad.wc.flat.caf.root")


def test_reconcile_missing_invalid_duplicate_unexpected_unit_mismatch():
    inc = _inc([(1, 1, 10, 1, "reco1-A"), (1, 1, 11, 0, "reco1-A"),          # represented, one wc.invalid
                (2, 1, 12, 1, "reco1-B"), (2, 1, 12, 1, "reco1-B"),            # duplicate of (2,1,12)
                (9, 9, 99, 1, "reco1-Z"),                                       # unexpected
                ])
    r = A.reconcile_event_keys(_exp(), inc)
    assert r["expected_events"] == 4 and r["represented"] == 3 and r["represented_wc_valid"] == 2 and r["represented_wc_invalid"] == 1
    assert r["missing"] == 1 and r["duplicate_keys"] == 1 and r["duplicate_rows"] == 2 and r["unexpected_rows"] == 1 and not r["complete"]
    assert r["represented"] + r["missing"] == r["expected_events"]                              # nothing lost
    assert r["_missing_rows"].evt.tolist() == [13] and r["_unexpected_rows"].evt.tolist() == [99]
    bad = A.reconcile_event_keys(_exp(), _inc([(1, 1, 10, 1, "reco1-WRONGUNIT")]))
    assert bad["unit_mismatch"] == 1


def test_complete_sample():
    inc = _inc([(1, 1, 10, 1, "reco1-A"), (1, 1, 11, 1, "reco1-A"), (2, 1, 12, 0, "reco1-B"), (3, 1, 13, 1, "reco1-C")])
    r = A.reconcile_event_keys(_exp(), inc)
    assert r["complete"] and r["missing"] == 0 and r["represented_wc_invalid"] == 1             # wc.invalid is accounted, not dropped
    with pytest.raises(ValueError):
        A.reconcile_event_keys(pd.concat([_exp(), _exp().iloc[:1]]), inc)                       # an ambiguous expected key is refused, never assumed unique


def _facts_ok():
    g = A.load_gate()
    f = {}
    for c in g["checks"]:
        r, v = c["rule"], c.get("value")
        f[c["fact"]] = True if r == "true" else False if r == "false" else v if r in ("equals", "in") else (["x"] if r == "present" else v)
    return g, f


def test_gate_yaml_levels_and_required_checks_cover_the_brief():
    g = A.load_gate()
    ids = {c["id"]: c["level"] for c in g["checks"]}
    assert set(ids.values()) == {"REQUIRED", "EXPECTED", "INFORMATIONAL"}
    for need in ("same_chain_as_fg1", "scn_vertex_model", "no_dv2_max", "no_fix2", "no_alternative_bdt", "no_hidden_selection_change", "truth_trees_present",
                 "event_keys_accounted", "wc_valid_accounted", "rec_trees_present"):
        assert ids[need] == "REQUIRED"
    assert ids["wct_version_strings"] == "INFORMATIONAL" and ids["schema_md5_matches_fg1"] == "EXPECTED"     # exact byte-identical versions are NOT required


def test_gate_open_only_if_all_required_pass_and_unknown_is_not_a_pass():
    g, f = _facts_ok()
    assert A.evaluate_gate(g, f)["open"]
    f2 = dict(f); f2["declared_uses_fix2"] = True
    r = A.evaluate_gate(g, f2); assert not r["open"] and "no_fix2" in r["required_failed"]
    f3 = dict(f); del f3["declared_uses_dv2_max"]
    r = A.evaluate_gate(g, f3); assert not r["open"] and "no_dv2_max" in r["required_unknown"]       # undeclared => closed
    f4 = dict(f); f4["missing_events"] = 3; f4["schema_md5_set_equals_fg1"] = False; f4["wct_version_set"] = []
    r = A.evaluate_gate(g, f4); assert r["open"] and {"no_missing_events", "schema_md5_matches_fg1"} <= set(r["expected_not_passing"])    # EXPECTED/INFORMATIONAL never block
    f5 = dict(f); f5["dl_weights"] = "other/model.pth"
    assert "scn_vertex_model" in A.evaluate_gate(g, f5)["required_failed"]
    f6 = dict(f); f6["unexpected_event_rows"] = 1; f6["duplicate_event_rows"] = 2
    assert {"no_unexpected_events", "no_duplicate_events"} <= set(A.evaluate_gate(g, f6)["required_failed"])


def test_required_branch_list_covers_the_frozen_chain():
    from sbnd_single_photon import selection as SEL
    req = A.required_wc_branches(SEL.load_config())
    for b in SEL.required_branches(SEL.load_config())["wc"]:
        assert b in req
    assert "wc.T_match.match_iou_n" in req and "wc.valid" in req


def test_frozen_selection_hash_matches_repository_config():
    spec = importlib.util.spec_from_file_location("reg", REPO / "scripts" / "register_official_ncdelta_wc.py")
    src = (REPO / "scripts" / "register_official_ncdelta_wc.py").read_text()
    h = hashlib.sha256((REPO / "configs" / "baseline_selection.yaml").read_bytes()).hexdigest()
    assert f'FROZEN_SELECTION_SHA256 = "{h}"' in src                                           # a hidden cut change would break this
