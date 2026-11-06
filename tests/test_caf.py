import awkward as ak
import numpy as np
import pytest
from sbnd_single_photon import caf as C


def test_open_alignment_valid_and_ids(tiny_caf):
    with C.MergedCaf(str(tiny_caf)) as f:
        assert f.num_entries == 3
        ids = f.read_ids()
        assert ids["evt"].tolist() == [10, 11, 12]
        assert f.read_valid().tolist() == [True, False, True]       # wc.valid == 1 only
        assert not f.has_truth_matching
        assert f.schema_md5() is None


def test_rse_misalignment_raises(make_caf):
    p = make_caf("bad.root", evt_wc=[10, 99, 12])
    with C.MergedCaf(str(p)) as f:
        with pytest.raises(C.AlignmentError):
            f.read_ids()


def test_missing_branch_is_explicit(tiny_caf):
    with C.MergedCaf(str(tiny_caf)) as f:
        with pytest.raises(C.MissingBranchError) as e:
            f.read(wc=["wc.T_tagger.does_not_exist"])
        assert "does_not_exist" in str(e.value)
        with pytest.raises(C.MissingBranchError):
            f.read(rec=["rec.hdr.nope"])


def test_read_only_requested_branches(tiny_caf):
    with C.MergedCaf(str(tiny_caf)) as f:
        d = f.read(wc=["wc.T_tagger.shw_sp_n_20mev_showers"])
        assert set(d) == {"wc.T_tagger.shw_sp_n_20mev_showers", "wc.valid", "ids"}


def test_jagged_candidate_structure(tiny_caf):
    with C.MergedCaf(str(tiny_caf)) as f:
        d = f.read(wc=["wc.T_tagger.shw_sp_n_20mev_showers"])
        assert ak.num(d["wc.T_tagger.shw_sp_n_20mev_showers"]).tolist() == [2, 0, 1]
        nested = f.read_nested("wc.T_kine.kine_particle_type")
        assert nested.tolist() == [[[2212, 11, 13], [2212, 2212]], [], [[11]]]


def test_per_candidate_inconsistent_length_raises():
    flat = ak.Array([[1, 2, 3]])
    with pytest.raises(C.CafError):
        C.per_candidate(flat, ak.Array([[1, 1]]))


def test_common_branches_and_helpers(tiny_caf):
    with C.MergedCaf(str(tiny_caf)) as a, C.MergedCaf(str(tiny_caf)) as b:
        assert "wc.valid" in C.common_branches(a, b)
    assert C.is_helper_branch("wc.T_kine.x..length") and not C.is_helper_branch("wc.T_kine.x")


def test_missing_tree_fails_clearly(tmp_path):
    import uproot
    p = tmp_path / "notree.root"
    with uproot.recreate(p) as f:
        t = f.mktree("recTree", {"a": np.int64}); t.extend({"a": np.arange(3)})
    with pytest.raises(C.MissingBranchError):
        C.MergedCaf(str(p)).open()
