import awkward as ak
import numpy as np
from sbnd_single_photon import proton as P


def test_categories_and_threshold_boundary():
    pdg = ak.Array([[[2212, 11], [2212, 2212]], [[13]], [[2212]]])
    ke = ak.Array([[[40.0, 500.0], [36.0, 35.0]], [[200.0]], [[35.0]]])
    # cand0: one proton >35 (40)  -> 1p ; cand1: 36 counts, 35.0 does NOT (strict >) -> 1p ; no protons -> 0p ; 35.0 -> 0p
    code = P.classify_reco_protons(pdg, ke, 35.0)
    assert code.tolist() == [[1, 1], [0], [0]]
    assert [P.LABELS[c] for c in ak.flatten(code).to_list()] == ["1p", "1p", "0p", "0p"]


def test_ge2p_and_configurable_threshold():
    pdg = ak.Array([[[2212, 2212, 2212]]])
    ke = ak.Array([[[100.0, 60.0, 20.0]]])
    assert P.classify_reco_protons(pdg, ke, 35.0).tolist() == [[2]]
    assert P.classify_reco_protons(pdg, ke, 70.0).tolist() == [[1]]
    assert P.classify_reco_protons(pdg, ke, 10.0).tolist() == [[2]]


def test_only_proton_pdg_counts_and_included_variant():
    pdg = ak.Array([[[211, 13, 2212, 0]]])
    ke = ak.Array([[[500.0, 500.0, 50.0, 500.0]]])
    assert P.count_reco_protons(pdg, ke).tolist() == [[1]]
    inc = ak.Array([[[1, 1, 3, 1]]])
    assert P.classify_reco_protons(pdg, ke, included=inc, require_included=True).tolist() == [[0]]


def test_empty_candidate_and_scalar_counts():
    assert P.classify_counts(0) == 0 and P.classify_counts(1) == 1 and P.classify_counts(5) == 2
    assert P.classify_counts(np.array([0, 1, 2, 3])).tolist() == [0, 1, 2, 2]
    # a candidate with no particle rows is 0p; an event with no candidates stays empty
    empty = ak.Array([[[]], []])
    assert P.classify_reco_protons(empty, empty).tolist() == [[0], []]
