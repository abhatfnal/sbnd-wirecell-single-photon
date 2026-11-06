import sys
from pathlib import Path
import awkward as ak
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def _write(path, *, evt_wc=None, valid=(1, 0, 1), drop_branch=None):
    """Tiny synthetic merged CAF written with uproot (a few events, a few branches)."""
    import uproot
    run = np.array([7, 7, 7], dtype=np.uint32)
    sub = np.array([1, 1, 1], dtype=np.uint32)
    evt = np.array([10, 11, 12], dtype=np.uint32)
    rec = {"rec.hdr.run": run, "rec.hdr.subrun": sub, "rec.hdr.evt": evt,
           "rec.hdr.pot": np.array([1e14, 0, 0], dtype=np.float32)}
    wc_evt = evt if evt_wc is None else np.asarray(evt_wc, dtype=np.uint32)
    # event0: 2 candidates (particles 3 + 2), event1: 0 candidates, event2: 1 candidate (1 particle)
    ptype = ak.Array([[2212, 11, 13, 2212, 2212], [], [11]])
    plen = ak.Array([[3, 2], [], [1]])
    wc = {"wc.valid": np.array(valid, dtype=np.int32), "wc.run": run, "wc.subrun": sub, "wc.evt": wc_evt,
          "wc.T_tagger.nu_index": ak.Array([[0, 1], [], [0]]),
          "wc.T_tagger.shw_sp_n_20mev_showers": ak.Array([[1.0, 0.0], [], [2.0]]),
          "wc.T_kine.kine_particle_type": ptype, "wc.T_kine.kine_particle_type..length": plen,
          "wc.T_kine.kine_energy_particle": ak.Array([[50.0, 5.0, 100.0, 40.0, 10.0], [], [30.0]]),
          "wc.T_kine.kine_energy_particle..length": plen}
    if drop_branch:
        wc.pop(drop_branch)
    def _tree(f, name, cols):
        types = {k: (v.dtype if isinstance(v, np.ndarray) else ak.type(v).content) for k, v in cols.items()}
        t = f.mktree(name, types)          # force a classic TTree (a plain dict assignment may write an RNTuple)
        t.extend(cols)

    with uproot.recreate(path) as f:
        _tree(f, "recTree", rec)
        _tree(f, "recTreeWireCell", wc)
    return path


@pytest.fixture
def tiny_caf(tmp_path):
    return _write(tmp_path / "tiny.root")


@pytest.fixture
def make_caf(tmp_path):
    def _mk(name="x.root", **kw):
        return _write(tmp_path / name, **kw)
    return _mk
