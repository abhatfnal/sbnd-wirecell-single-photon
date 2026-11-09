import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from sbnd_single_photon import background_truth as BT

REPO = Path(__file__).resolve().parents[1]


def _tables(order_by_iou_n=True):
    # candidate 0 of event 0 overlaps truth nu 0 (more shared CHARGE, fewer points) and truth nu 1 (higher POINT IoU). Production lists the
    # partners by decreasing point IoU (the source rule): nu 1 first.
    R = pd.DataFrame(dict(ev=[0, 0, 0, 0], level=3, side=[0, 1, 1, 1], obj=[0, 0, 1, 2], nu_index=[0, -1, -1, -1], truth_nu_idx=[-1, 0, 1, -1],
                          truth_trackid=[-1, -1, -1, 777], mutual=[1, 1, 1, 1], nmatch=[2, 1, 1, 0]))
    R["row"] = np.arange(len(R))
    I = pd.DataFrame(dict(row=[0, 0], match_obj=[1, 0], match_iou_n=[0.62, 0.35], match_iou_q=[0.35, 0.63], match_shared_q=[4.9e6, 8.8e6], match_shared_n=[600., 500.]))
    return R, I


def test_top_partner_is_the_first_stored_one_not_the_largest_charge_iou():
    R, I = _tables()
    src = BT.candidate_association(R, I).iloc[0]
    old = BT.candidate_association(R, I, rule="iou_q").iloc[0]
    assert src.tm_top_nu == 1 and src.tm_top_iou_n == pytest.approx(0.62)                # source: decreasing POINT IoU
    assert old.tm_top_nu == 0                                                           # Phase-4 rule would have chosen the charge-dominant partner
    assert src.tm_n_distinct_nu == 2 and old.tm_n_distinct_nu == 2                      # both flag the structural ambiguity
    with pytest.raises(ValueError):
        BT.candidate_association(R, I, rule="nonsense")


def _inv():
    spec = importlib.util.spec_from_file_location("reval", REPO / "scripts" / "revalidate_t_match_semantics.py")
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def test_invariants_detect_order_and_mutual_violations():
    inv = _inv().invariants
    R, I = _tables()
    # truth objects 0 and 1 each have the candidate as best partner -> candidate mutual with its first partner (nu 1): add the truth rows' own partner lists
    I2 = pd.concat([I, pd.DataFrame(dict(row=[1], match_obj=[0], match_iou_n=[0.35], match_iou_q=[0.63], match_shared_q=[8.8e6], match_shared_n=[500.])),
                    pd.DataFrame(dict(row=[2], match_obj=[0], match_iou_n=[0.62], match_iou_q=[0.35], match_shared_q=[4.9e6], match_shared_n=[600.]))], ignore_index=True)
    R2 = R.copy(); R2["nmatch"] = [2, 1, 1, 0]; R2["mutual"] = [1, 0, 1, 0]            # candidate's best partner is truth 1, whose best partner is the candidate -> mutual; truth 0 best is the candidate but candidate's best is truth 1 -> not mutual
    r = inv(R2, I2)
    assert r["nmatch_equals_items"] and r["iou_n_nonincreasing"] and r["max_nmatch"] == 2 and r["mutual_flag_agrees_with_definition"] == 1.0
    Ibad = I2.copy(); Ibad.loc[0, "match_iou_n"] = 0.1                                   # list no longer in decreasing point-IoU order
    assert not inv(R2, Ibad)["iou_n_nonincreasing"]
    Rbad = R2.copy(); Rbad.loc[0, "mutual"] = 0
    assert inv(Rbad, I2)["mutual_flag_agrees_with_definition"] < 1.0


def test_committed_revalidation_matches_the_documented_phase4_difference():
    import json
    j = json.load(open(REPO / "tables" / "background_mechanisms" / "t_match_source_revalidation.json"))
    assert j["n_selected_found"] == j["n_selected_expected"] == 649 and not j["read_errors"] and j["top_nu_differs_source_vs_iouq"] == 2
    i = j["invariants"]; assert i["iou_n_order_violations"] == 0 and i["max_nmatch"] == 3 and i["mutual_flag_agreement_min"] == 1.0
    s = json.load(open(REPO / "tables" / "background_mechanisms" / "summary.json"))
    assert s["accounting"]["total"] == 649 and s["accounting"]["signal_like"] == 14 and s["accounting"]["background"] == 635 and s["accounting"]["mixed"] == 0
    assert s["accounting"]["background_by_channel"] == {"1g0p": 310, "1g1p": 230, "ge2p_diag": 95}
    assert s["accounting"]["background_by_category"]["OTHER_NC"] == 20 and s["accounting"]["background_by_category"]["COSMIC_OR_UNMATCHED"] == 16
    assert sum(s["accounting"]["background_by_category"].values()) == 635
