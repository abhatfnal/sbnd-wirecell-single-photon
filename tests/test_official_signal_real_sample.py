"""Issues found with the REAL official NC-Delta Wire-Cell production (2026-11-10), pinned so that they cannot silently regress.
Only small committed tables are read (no ROOT, no derived data)."""
import gzip
import json
from pathlib import Path
import pandas as pd
import pytest
import yaml
from sbnd_single_photon import caf as C, signal_arrival as A, signal_pipeline as SP

REPO = Path(__file__).resolve().parents[1]
TAB = REPO / "tables" / "official_signal"


def test_tolerant_basket_read_is_scoped_and_restored():
    uproot = pytest.importorskip("uproot")
    from uproot.models.TObjArray import Model_TObjArrayOfTBaskets as M
    orig = M.check_numbytes
    with C.tolerant_embedded_basket_read():
        assert M.check_numbytes is not orig and M.check_numbytes(None, None, None, None) is None
    assert M.check_numbytes is orig
    with pytest.raises(RuntimeError):
        with C.tolerant_embedded_basket_read():
            raise RuntimeError("boom")
    assert M.check_numbytes is orig                      # restored even when the body raises


def test_one_event_never_processed_stays_in_the_denominator_and_fails():
    exp = pd.DataFrame(dict(run=[1, 1, 2], subrun=[1, 1, 1], evt=[10, 11, 12], reco1_unit=["reco1-A.root", "reco1-A.root", "reco1-B.root"]))
    inc = pd.DataFrame([(1, 1, 10, 1, "reco1-A"), (1, 1, 11, 1, "reco1-A")], columns=["run", "subrun", "evt", "wc_valid", "unit"])
    r = A.reconcile_event_keys(exp, inc)
    assert (r["expected_events"], r["represented"], r["missing"], r["unexpected_rows"], r["duplicate_rows"]) == (3, 2, 1, 0, 0) and not r["complete"]
    tab = pd.DataFrame(dict(run=[1, 1], subrun=[1, 1], evt=[10, 11], A_final=[True, False], A_candidate=[True, True], wc_valid=[True, True], n_pass=[1, 0],
                            first_fail_A=["selected", "fail_numu"], policy="any"))
    out = SP.with_missing_rows(tab, r["_missing_rows"].assign(truth_cat=1), "any")
    assert len(out) == 3 and out.arrived.tolist() == [True, True, False]
    assert out.A_final.sum() == 1 and out.iloc[-1].first_fail_A == SP.MISSING_REASON      # a lost event is an inefficiency, not a dropped row


def test_registry_matches_the_registered_manifest():
    s = yaml.safe_load(open(REPO / "configs" / "samples.yaml"))
    s = s.get("samples", s)["official_gen2_ncdelta"]
    assert s["status"] == "available" and s["wirecell_merged_status"] == "available" and s["is_mc"] is True
    man = REPO / s["manifest"]
    rows = [l for l in gzip.open(man, "rt").read().splitlines() if l and not l.startswith("index\t")]
    assert len(rows) == s["n_files_listed"] == s["wirecell_merged"]["merged_cafs"] == 9150
    assert s["wirecell_merged"]["events"] == s["wirecell_merged"]["wc_valid"] == 13772


def test_production_record_documents_the_13773_vs_13772_event():
    rec = json.load(open(TAB / "production_record.json"))
    assert rec["list_files"]["pairs-mc-ncdr.skipped.tsv"]["lines"] == 729                  # Haiwang: 729 reco1 without a CAF; our census: 728
    assert rec["list_files"]["pairs-mc-ncdr.tsv"]["lines"] - 1 == 15776
    m = rec["missing_event"]
    assert (m["run"], m["subrun"], m["evt"]) == (317, 41, 6753) and m["in_active_tpc"] and m["in_filter_box"]
    assert "000011/caf/subrun_" in m["sam_flatcaf_location"] and m["sam_flatcaf_checks"]["content_status"] == "good"
    assert rec["live_sam"]["file_lists_identical_to_saved_2026_11_06_snapshot"] is True


@pytest.mark.parametrize("region,n_truth", [("active_tpc", 12427), ("filter_box", 13773)])
def test_official_baseline_accounting_is_exact(region, n_truth):
    s = json.load(open(TAB / f"official_{region}" / "summary.json"))
    assert s["n_truth"] == n_truth == s["arrived"] + s["missing"] and s["missing"] == 1 and s["wc_valid"] == s["arrived"]
    assert sum(s["truth_class"].values()) == n_truth and sum(s["delta"].values()) == n_truth
    assert s["final_first"]["total"] <= s["final_any"]["total"]
    assert sum(s["final_any"]["by_truth"].values()) == sum(s["final_any"]["reco_channel"].values()) == s["final_any"]["total"]
    assert s["accounting"]["ok"] is True
