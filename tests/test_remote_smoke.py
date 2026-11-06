"""Tiny REMOTE test: needs a bearer token and dCache access. Skipped otherwise."""
import os
from pathlib import Path
import pytest
from sbnd_single_photon import samples as S, caf as C

tok = os.environ.get("BEARER_TOKEN_FILE")


def _token_usable(path) -> bool:
    """Token file exists, is non-empty and its JWT ``exp`` claim is in the future (contents are never printed)."""
    import base64, json, time
    try:
        p = Path(path)
        if not (p.is_file() and p.stat().st_size > 0):
            return False
        body = p.read_text().strip().split(".")[1]
        return json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))["exp"] > time.time()
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not (tok and _token_usable(tok)), reason="no usable (present and unexpired) bearer token")


def test_remote_bnb_file_and_data_schema():
    reg = S.load_samples()
    os.environ.setdefault("XRD_NETWORKSTACK", "IPv4")
    with C.MergedCaf(S.manifest_urls(reg["bnb_cv"], 0, 1)[0]) as f:      # 3 events max are read
        assert f.has_truth_matching and f.n_wc_branches == 2401
        assert f.trun("dl_weights") == "uboone/scn_vtx/t48k-m16-l5-lr5d-res0.5-CP24.pth"
        d = f.read(wc=["wc.T_tagger.shw_sp_n_20mev_showers"], stop=3)
        assert len(d["wc.valid"]) == 3 and d["ids"]["evt"].shape == (3,)
        bnb = f.wc_branches
    with C.MergedCaf(S.manifest_urls(reg["beam_on_open"], 0, 1)[0]) as g:   # older schema is a strict subset
        assert not g.has_truth_matching and g.n_wc_branches == 2283
        assert g.wc_branches <= bnb
