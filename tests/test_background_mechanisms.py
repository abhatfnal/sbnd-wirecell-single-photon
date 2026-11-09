import numpy as np
import pandas as pd
import pytest
from sbnd_single_photon import background_truth as BT, background_mechanisms as BM, natural_signal as NS


def _match_tables():
    # event 0: candidate 0 matches truth nu 1 (iou .9) and cosmic object (iou .1); candidate 1 matches nothing; event 1: candidate 0 matches nu 0 and nu 2
    R = pd.DataFrame(dict(
        ev=[0, 0, 0, 0, 0, 1, 1, 1, 1], level=3, side=[0, 0, 1, 1, 1, 0, 1, 1, 1], obj=[0, 1, 0, 1, 2, 0, 0, 1, 2],
        nu_index=[0, 1, -1, -1, -1, 0, -1, -1, -1], truth_nu_idx=[-1, -1, 1, -1, -1, -1, 0, 2, -1],
        truth_trackid=[-1, -1, -1, 2000001, 2000002, -1, -1, -1, 3000001], mutual=[1, 0, 1, 1, 1, 1, 1, 1, 1], nmatch=[2, 0, 1, 1, 0, 2, 1, 1, 0]))
    R["row"] = np.arange(len(R))
    I = pd.DataFrame(dict(row=[0, 0, 5, 5], match_obj=[0, 1, 0, 1], match_iou_q=[0.9, 0.1, 0.6, 0.4], match_shared_q=[9., 1., 6., 4.]))
    return R, I


def test_candidate_association_top_match_ambiguity_and_unmatched():
    R, I = _match_tables()
    a = BT.candidate_association(R, I).set_index(["ev", "nu_index"])
    c = a.loc[(0, 0)]
    assert c.tm_top_nu == 1 and c.tm_n == 2 and c.tm_n_cosmic == 1 and c.tm_n_distinct_nu == 1 and c.tm_second_iou == pytest.approx(0.1)
    assert a.loc[(0, 1)].tm_top_nu == BT.UNMATCHED and a.loc[(0, 1)].tm_n == 0           # candidate with no match stays in the table
    assert a.loc[(1, 0)].tm_n_distinct_nu == 2 and a.loc[(1, 0)].tm_n_cosmic == 0       # overlaps truth nu 0 and nu 2: structurally ambiguous


def test_classify_candidate_precedence_and_no_event_content_override():
    k = BT.classify_candidate
    assert k(BT.UNMATCHED, 0, 0, 0, 0, 0, True, False) == "COSMIC_OR_UNMATCHED" and k(BT.COSMIC, 0, 1, 0, 0, 0, True, False) == "COSMIC_OR_UNMATCHED"
    assert k(1, 2, 2, 14, 1, 0, True, False) == "MULTI_OR_AMBIGUOUS"
    assert k(1, 1, 1, 14, 0, 0, True, True) == "SIGNAL_NCDELTA"
    assert k(1, 1, 1, 14, 0, 1, False, False) == "OUTSIDE_TPC_NU"                       # outside beats pi0
    assert k(1, 1, 1, 14, 0, 1, True, False) == "NC_PI0" and k(1, 1, 1, 14, 1, 1, True, False) == "CC_PI0"
    assert k(1, 1, 1, -12, 1, 0, True, False) == "NUE_CC" and k(1, 1, 1, 14, 1, 0, True, False) == "NUMU_CC"
    assert k(1, 1, 1, 14, 0, 0, True, False) == "OTHER_NC" and k(1, 1, 1, 16, 1, 0, True, False) == "OTHER_CC"


def _light():
    # multi-neutrino event (0,0): nu 0 = NC pi0 in TPC, nu 1 = nue CC in TPC; the passing candidate matches nu 1 -> NUE_CC, whatever else is in the event
    base = dict(file_index=0, tm_n=1, tm_n_distinct_nu=1)
    rows = [dict(ev=0, nu_index=0, tm_top_nu=1, mnu_pdg=12, mnu_ccnc=0, mnu_x=0., mnu_y=0., mnu_z=100., mnu_k=1, k_n_pi0=0, **base),
            dict(ev=1, nu_index=0, tm_top_nu=0, mnu_pdg=14, mnu_ccnc=1, mnu_x=0., mnu_y=0., mnu_z=100., mnu_k=0, k_n_pi0=1, **base),
            dict(ev=2, nu_index=0, tm_top_nu=0, mnu_pdg=14, mnu_ccnc=0, mnu_x=500., mnu_y=0., mnu_z=100., mnu_k=0, k_n_pi0=0, **base),
            dict(ev=3, nu_index=0, tm_top_nu=BT.UNMATCHED, mnu_pdg=np.nan, mnu_ccnc=np.nan, mnu_x=np.nan, mnu_y=np.nan, mnu_z=np.nan, mnu_k=np.nan, k_n_pi0=np.nan, file_index=0, tm_n=0, tm_n_distinct_nu=0),
            dict(ev=4, nu_index=0, tm_top_nu=0, mnu_pdg=14, mnu_ccnc=1, mnu_x=10., mnu_y=0., mnu_z=100., mnu_k=0, k_n_pi0=0, **base)]
    return pd.DataFrame(rows)


def test_add_categories_signal_exclusion_and_taxonomy():
    sig = pd.DataFrame(dict(file_index=[0], ev=[4], k=[0]))
    d = BM.add_categories(_light(), sig)
    assert d.cand_category.tolist() == ["NUE_CC", "NC_PI0", "OUTSIDE_TPC_NU", "COSMIC_OR_UNMATCHED", "SIGNAL_NCDELTA"]
    assert d.is_signal.tolist() == [False, False, False, False, True]
    assert d.out_dist_cm.iloc[2] == pytest.approx(300.0) and d.out_dist_cm.iloc[0] == 0


def test_event_accounting_exact_and_nothing_lost():
    d = BM.add_categories(_light().assign(reco_proton_cat=[0, 1, 0, 1, 0]), pd.DataFrame(dict(file_index=[0], ev=[4], k=[0])))
    sel = d.assign(nu_index=0)
    cls = pd.DataFrame(dict(file_index=0, ev=range(5), event_class=["background"] * 4 + ["signal_like"]))
    ev = BM.event_level(sel, cls)
    acc = BM.accounting(ev)
    assert acc["total"] == 5 and acc["signal_like"] == 1 and acc["background"] == 4 and acc["mixed"] == 0
    assert sum(acc["background_by_channel"].values()) == 4 and sum(acc["background_by_category"].values()) == 4
    assert acc["background_by_channel"] == {"1g0p": 2, "1g1p": 2}
    bad = ev.copy(); bad.loc[0, "event_class"] = np.nan
    with pytest.raises(AssertionError):
        BM.accounting(bad)                                                     # an unclassified event must raise, never vanish


def test_event_level_marks_two_passing_candidates_with_different_categories():
    sel = pd.DataFrame(dict(file_index=0, ev=[0, 0], nu_index=[0, 1], cand_category=["NC_PI0", "NUE_CC"], reco_proton_cat=[0, 1]))
    cls = pd.DataFrame(dict(file_index=[0], ev=[0], event_class=["background"]))
    e = BM.event_level(sel, cls).iloc[0]
    assert e.n_pass == 2 and e.event_cand_category == "MULTI_OR_AMBIGUOUS" and e.reco_channel == "mixed"


def test_migration_by_class_row_totals_and_unmatched_handling():
    sel = pd.DataFrame(dict(cand_category=["NC_PI0"] * 4 + ["COSMIC_OR_UNMATCHED"] * 2, k_n_p35=[0, 1, 1, 3, np.nan, np.nan],
                            reco_proton_cat=[0, 0, 1, 1, 0, 1], tm_top_nu=[0, 0, 0, 0, BT.UNMATCHED, BT.UNMATCHED], tm_n_distinct_nu=[1, 1, 1, 1, 0, 0]))
    m = BM.migration_by_class(sel)
    p = m["NC_PI0"].drop(columns="no_truth_category")
    assert p.loc["truth 0p", "reco 0p"] == 1 and p.loc["truth 1p", "reco 0p"] == 1 and p.loc["truth 1p", "reco 1p"] == 1 and p.loc["truth >=2p", "reco 1p"] == 1
    assert p.drop(index="no truth category (reco counts)").values.sum() == 4
    c = m["COSMIC_OR_UNMATCHED"]
    assert c.drop(index="no truth category (reco counts)").values.sum() == 0 and c.loc["no truth category (reco counts)", "reco 0p"] == 1


def test_composition_totals_and_cutflow_by_class():
    b = pd.DataFrame(dict(reco_channel=["1g0p"] * 3 + ["1g1p"] * 2, event_cand_category=["NC_PI0", "NC_PI0", "NUE_CC", "NUE_CC", "OUTSIDE_TPC_NU"]))
    t = BM.composition(b, pot=1e19)
    tot = t[t.category == "TOTAL"].set_index("channel")["count"]
    assert tot["1g0p"] == 3 and tot["1g1p"] == 2 and t[t.category != "TOTAL"]["count"].sum() == 5
    assert t[(t.channel == "1g0p") & (t.category == "NC_PI0")].rate_per_1e20.iloc[0] == pytest.approx(20.0)
    c = pd.DataFrame(dict(cand_category=["NC_PI0", "NC_PI0", "NUE_CC"], reco_proton_cat=[0, 1, 0], s1=[True, True, True], s2=[True, False, True]))
    f = BM.cutflow_by_class(c, [("s1", "s1"), ("s2", "s2")], by_reco=True)
    a = f[f.split == "all"].set_index("category")
    assert a.loc["NC_PI0", "candidates"] == 2 and a.loc["NC_PI0", "s2"] == 1 and (a.s2 <= a.s1).all() and a.candidates.sum() == 3


def test_shower_origin_and_pi0_helpers():
    assert BT.origin_class(22, 0, 100) == "photon" and BT.origin_class(-11, 0, 5) == "electron_positron" and BT.origin_class(2212, 0, 5) == "proton"
    assert BT.origin_class(13, 0, 5) == "muon" and BT.origin_class(-211, 0, 5) == "charged_pion" and BT.origin_class(2112, 0, 5) == "neutron_or_hadronic"
    assert BT.origin_class(22, -1, 5) == "cosmic_or_unmatched" and BT.origin_class(22, 0, -1) == "cosmic_or_unmatched" and BT.origin_class(321, 0, 5) == "other"
    s = BT.pi0_photon_summary(0.0689, 0.2685)
    assert s["lead_mev"] == pytest.approx(268.5) and 0.5 < s["asymmetry"] < 0.6 and 30 < s["opening_angle_deg"] < 60      # known event of the audit
    assert np.isnan(BT.pi0_photon_summary(0.01, 0.01)["opening_angle_deg"])                                            # m^2 > 2E1E2: inconsistent
    r = dict(ph2_E=0.069, ph2_lt20=False, ph2_q_in_blobs=0.0, ph2_end_in_tpc=False, ph2_n_overlap_rows=0)
    assert BT.photon_fate_labels(r, "ph2_") == ["no_charge", "exits", "no_reco_row"]
    r2 = dict(ph2_E=0.01, ph2_lt20=True, ph2_q_in_blobs=5.0, ph2_end_in_tpc=True, ph2_n_overlap_rows=3, ph2_same_cand=True, ph2_is_selected_row=False,
              ph2_dom_row_is_shower=False, ph2_dom_row_type=211, ph2_q_in_selected_row=2.0)
    assert BT.photon_fate_labels(r2, "ph2_") == ["lt20", "same_candidate_other_row", "nonshower_row", "merged_with_selected"]
    assert BT.photon_fate_labels({}, "ph2_") == ["absent"]


def test_committed_summary_reproduces_validated_accounting():
    """The committed full-sample summary must keep the exactly validated decomposition 649 = 14 + 635 + 0 and consistent channel/category totals."""
    import json
    from pathlib import Path
    p = Path(__file__).resolve().parents[1] / "tables" / "background_mechanisms" / "summary.json"
    j = json.loads(p.read_text())
    a = j["accounting"]
    assert (a["total"], a["signal_like"], a["background"], a["mixed"]) == (649, 14, 635, 0)
    assert sum(a["background_by_channel"].values()) == 635 and sum(a["background_by_category"].values()) == 635
    assert a["background_by_channel"] == {"1g0p": 310, "1g1p": 230, "ge2p_diag": 95}                    # 318-8, 236-6, 95 from the real table
    ct = a["crosstab"]
    assert sum(sum(r.values()) for r in ct.values()) == 635
    for ch, n in a["background_by_channel"].items():
        assert sum(r.get(ch, 0) for r in ct.values()) == n
    assert all(j["validation"][k] for k in ("total_649", "signal_like_14", "background_635", "mixed_0", "event_signal_like_equals_T_match_signal"))
