"""Row-level reco-proton truth association (Phase 10): synthetic checks of the classification helpers and pinned checks of the committed summary tables.

Nothing here changes a selection flag, threshold or policy: the pinned checks assert that the baseline decisions are untouched.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from sbnd_single_photon import proton_tables as PT

TAB = Path(__file__).resolve().parents[1] / "tables" / "proton_truth_association"
S = json.load(open(TAB / "summary.json"))
K = ["file_index", "ev"]


def _row(**kw):
    base = dict(file_index=0, ev=0, nmatch=1, has_match_row=True, p1_tid=10, p1_iou_n=0.9, p1_iou_q=0.9, p1_t_nu=0, p1_t_pdg=2212, p1_t_proc=0, p1_t_prim=False, p1_t_prim_pf=False,
                p2_tid=-1, p2_iou_n=np.nan, p2_t_nu=np.nan, p2_t_pdg=np.nan, p2_t_proc=np.nan, p2_t_prim=False, p2_t_prim_pf=False)
    base.update(kw); return base


SIG = pd.Series({(0, 0): 0})


def test_one_association_result_per_row():
    u = S["row_uniqueness"]
    assert u["rows"] == u["unique_keys"] == u["origin_assigned"] == u["origin_in_taxonomy"] > 80000
    assert u["proton_typed_rows"] == u["proton_typed_unique"]
    t = pd.read_csv(TAB / "row_origin_taxonomy.csv")
    assert int(t.all_rows.sum()) == u["rows"] and int(t.proton_rows.sum()) == u["proton_typed_rows"]


def test_source_ranked_top_partner_and_primary_by_process():
    # the top partner is the FIRST stored partner (point-IoU ranking) even if the second has the larger charge IoU
    r = pd.DataFrame([_row(nmatch=2, p1_iou_n=0.8, p1_iou_q=0.1, p2_tid=11, p2_iou_n=0.05, p2_iou_q=0.95, p2_t_nu=-1, p2_t_pdg=13, p2_t_proc=0)])
    c = PT.classify_rows(r, SIG, ratio=0.5)
    assert c.origin.iloc[0] == "true_primary_signal_proton"
    # primary means process == 0; parent_trackid == 0 (t_prim_pf) of a secondary must NOT make it primary
    r = pd.DataFrame([_row(p1_t_proc=15, p1_t_prim=True, p1_t_prim_pf=True)])
    assert PT.classify_rows(r, SIG).origin.iloc[0] == "geant4_secondary_proton"


def test_truth_origin_taxonomy_exclusive_and_reachable():
    rows = [_row(),                                                                  # A
            _row(p1_t_nu=1),                                                         # B other-neutrino proton
            _row(p1_t_proc=15),                                                      # C secondary
            _row(p1_t_pdg=22),                                                       # D photon
            _row(p1_t_pdg=211),                                                      # D pion
            _row(p1_t_nu=1, p1_t_pdg=13),                                            # E
            _row(p1_t_nu=-1, p1_t_pdg=2212),                                         # F
            _row(nmatch=2, p1_iou_n=0.5, p2_tid=11, p2_iou_n=0.4, p2_t_nu=0, p2_t_pdg=22, p2_t_proc=0),   # G: different class, comparable
            _row(nmatch=0, p1_tid=-1, p1_t_nu=np.nan, p1_t_pdg=np.nan, p1_t_proc=np.nan),                 # H
            _row(has_match_row=False, nmatch=np.nan, p1_tid=np.nan, p1_t_nu=np.nan, p1_t_pdg=np.nan, p1_t_proc=np.nan)]   # H, no level-1 object
    c = PT.classify_rows(pd.DataFrame(rows), SIG, ratio=0.5)
    assert list(c.origin) == ["true_primary_signal_proton", "other_neutrino_proton", "geant4_secondary_proton", "signal_nonproton_misidentified", "signal_nonproton_misidentified",
                              "other_neutrino_nonproton", "cosmic_or_non_neutrino", "ambiguous_multiple_truth", "unmatched", "unmatched"]
    assert set(c.origin) == set(PT.ROW_CLASSES)                                      # all eight classes are reachable and nothing else occurs
    assert list(c.d_sub)[3:5] == ["photon_electron", "pion"]
    assert list(c.unmatched_reason)[-2:] == ["nmatch_0", "no_level1_object"]
    # G needs a DIFFERENT class and a comparable second partner; same class or a weak second partner keeps the top class
    same = pd.DataFrame([_row(nmatch=2, p1_iou_n=0.5, p2_tid=11, p2_iou_n=0.45, p2_t_nu=0, p2_t_pdg=2212, p2_t_proc=0)])
    weak = pd.DataFrame([_row(nmatch=2, p1_iou_n=0.9, p2_tid=11, p2_iou_n=0.05, p2_t_nu=0, p2_t_pdg=22, p2_t_proc=0)])
    assert PT.classify_rows(same, SIG).origin.iloc[0] == "true_primary_signal_proton" and PT.classify_rows(weak, SIG).origin.iloc[0] == "true_primary_signal_proton"
    assert PT.classify_rows(pd.DataFrame(rows), SIG, ratio=None).origin.eq("ambiguous_multiple_truth").sum() == 0
    t = pd.read_csv(TAB / "row_origin_taxonomy.csv"); assert set(t.origin) == set(PT.ROW_CLASSES)


def test_true_proton_states_hierarchy():
    def r(cand, row, tid, typ, p2=-1):
        return dict(file_index=0, ev=0, cand=cand, row=row, kine_particle_type=typ, p1_tid=tid, p2_tid=p2, p3_tid=-1)
    rows = pd.DataFrame([r(0, 0, 1, 2212), r(0, 1, 2, 13), r(0, 2, 3, 2212), r(0, 3, 3, 2212), r(1, 0, 4, 2212), r(0, 4, 9, 11, p2=5)])
    tp = pd.DataFrame([dict(file_index=0, ev=0, trackid=t, ke=100.0) for t in (1, 2, 3, 4, 5, 6)] + [dict(file_index=1, ev=0, trackid=1, ke=100.0)])
    mc = pd.Series({(0, 0): 0.0, (1, 0): np.nan})
    st = PT.true_proton_states(tp, rows, mc).set_index(["file_index", "trackid"]).state
    assert st[(0, 1)] == "proton_row_single" and st[(0, 2)] == "matched_nonproton_row" and st[(0, 3)] == "proton_row_multiple"
    assert st[(0, 4)] == "in_other_candidate_only" and st[(0, 5)] == "subdominant_only" and st[(0, 6)] == "no_reco_row" and st[(1, 1)] == "no_signal_candidate"
    assert set(st) == set(PT.TRUE_PROTON_STATES)


def test_true_proton_accounting_against_baseline_truth():
    a = S["truth_proton_accounting"]
    assert a["50"]["mismatches"] == 0 and a["50"]["protons"] == a["50"]["baseline_protons"] == 6630
    assert a["35"]["protons"] - a["35"]["baseline_protons"] == 1 and a["35"]["mismatches"] <= 1       # one 35.18 MeV, 0.009-charge proton
    st = pd.read_csv(TAB / "true_proton_reco_state.csv")
    assert int(st.n_ke35.sum()) == a["35"]["protons"] and int(st.n_ke50.sum()) == a["50"]["protons"]
    e = S["true_proton_efficiency_all"]
    assert e["35"]["n_true"] == a["35"]["protons"] and 0 < e["35"]["threshold_passing_eff"] <= e["35"]["proton_id_eff"] <= e["35"]["row_found_eff"] < 1


@pytest.mark.parametrize("thr", [35, 50])
def test_1p_to_0p_reason_closure(thr):
    R = pd.read_csv(TAB / "migration_truth1p_to_reco0p.csv"); M = pd.read_csv(TAB / "multiplicity_response.csv")
    for stage, mstage in (("A_signal_matched_candidate", "signal_matched_candidate"), ("B_final_selected", "final_selected")):
        d = R[(R.thr_mev == thr) & (R.stage == stage)]
        n0 = int(M[(M.thr_mev == thr) & (M.stage == mstage) & (M.truth == "1") & (M.reco == "0")].n.iloc[0])
        assert int(d.n.sum()) == int(d.n_reco0p.iloc[0]) == n0                      # exact event accounting
        assert d.reason.nunique() == 6


@pytest.mark.parametrize("thr", [35, 50])
def test_0p_to_1p_reason_closure(thr):
    R = pd.read_csv(TAB / "migration_truth0p_to_reco1p.csv"); M = pd.read_csv(TAB / "multiplicity_response.csv")
    for stage, mstage in (("A_signal_matched_candidate", "signal_matched_candidate"), ("B_final_selected", "final_selected")):
        d = R[(R.thr_mev == thr) & (R.stage == stage) & (~R.reason.str.startswith("__"))]
        n1 = int(M[(M.thr_mev == thr) & (M.stage == mstage) & (M.truth == "0") & (M.reco == "1")].n.iloc[0])
        assert int(d.n.sum()) == int(d.n_reco1p.iloc[0]) == n1


def test_multiplicity_matrix_closure_and_projections():
    M = pd.read_csv(TAB / "multiplicity_response.csv")
    assert set(M.thr_mev) == {35, 50}
    for thr in (35, 50):
        assert int(M[(M.thr_mev == thr) & (M.stage == "signal_matched_candidate")].n.sum()) == 10831
        assert int(M[(M.thr_mev == thr) & (M.stage == "final_selected")].n.sum()) == 1153
    # synthetic: the matrix conserves events and bins 3+ together
    n_true = np.array([0, 1, 2, 5, 1]); n_reco = np.array([0, 1, 1, 4, 0])
    assert list(PT.reco_multiplicity(n_reco)) == [0, 1, 1, 3, 0] and len(PT.reco_multiplicity(n_true)) == 5
    t = S["multiplicity_3x3_final_35"]            # {reco: {truth: n}}: the published 3x3 migration (final, 35 MeV): truth 0 -> 425/50/1, truth 1 -> 93/471/30, truth >=2 -> 9/35/39
    got = [[t[r][tr] for r in ("0", "1", ">=2")] for tr in ("0", "1", ">=2")]
    assert got == [[425, 50, 1], [93, 471, 30], [9, 35, 39]]


def test_event_ladder_and_missing_production_event_accounted():
    L = pd.read_csv(TAB / "event_stage_ladder.csv")
    for thr in (35, 50):
        d = L[L.thr_mev == thr]
        assert int(d.total.sum()) == 12427
        assert (d.production_missing + d.no_candidate + d.candidate_not_signal_matched + d.signal_matched == d.total).all()
        assert int(d.production_missing.sum()) == 1 and int(d.signal_matched.sum()) == 10831 and int(d.final_selected.sum()) == 1153
    ev = S["events"]; assert ev["production_missing"] == 1 and ev["with_file"] + ev["production_missing"] == ev["tpc_box"] == 12427


def test_included3_diagnostic_does_not_change_baseline_and_no_flag_changed():
    b = S["baseline_reproduction"]
    assert b["match"] == dict(events=10831, mismatches=0) and b["final"] == dict(events=1153, mismatches=0)      # baseline reco proton counts reproduced exactly
    assert S["config"]["baseline_config_sha256"].startswith("f3251b78") and S["events"]["final"] == 1153 and S["events"]["matched"] == 10831 and S["events"]["candidate"] == 11331
    d = pd.read_csv(TAB / "included3_diagnostic_summary.csv")
    assert set(d.events[d.stage == "final_selected"]) == {1153} and set(d.events[d.stage == "signal_matched_candidate"]) == {10831}
    assert (d.events_changing_topology > 0).all() and (d.events_changing_topology < d.events).all()
    m = pd.read_csv(TAB / "included3_diagnostic_migration.csv")
    assert int(m[(m.thr_mev == 35) & (m.stage == "final_selected")].n.sum()) == 1153


def test_semantics_checks_match_source_facts():
    q = pd.read_csv(TAB / "row_semantics_checks.csv").set_index("quantity").value
    assert q["included_not_1_or_3_rows"] == 0 and q["included3_rows"] == q["included3_rows_in_pool2"] == q["included3_rows_shower"]      # source: only pool-2 showers carry 3
    assert q["included3_rows_cluster_not_main"] > 0.99 and q["level1_key_duplicates"] == 0


def test_delta_mass_ingredient_availability():
    d = S["delta_readiness"]
    assert d["events"] == 556 and d["all_inputs_available"] <= d["events"] and d["m_delta2_defined"] <= d["all_inputs_available"]
    assert d["both_truth_correct"] <= min(d["photon_truth_correct"], d["proton_truth_correct"]) and d["both_correct_and_all_inputs"] <= d["both_truth_correct"]
    assert d["photon_row_found"] >= d["all_inputs_available"] and d["dirs_available"] >= d["all_inputs_available"]
    by = pd.read_csv(TAB / "delta_mass_readiness_by_truth.csv"); assert int(by.n.sum()) == 556 and (by.both_truth_correct <= by.n).all()
