"""The portable bundle (upstream_chain_bundle/wc_upstream_chain) is the same numerical object as the validated Aurora chain
emulation (sp_retrain/upstream_chain.py), and the patched-toolkit stamp approval is exact and development-only."""
import importlib.util
import json
import os
import sys

import numpy as np
import pandas as pd
import pytest

ROUND2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUNDLE = os.path.join(ROUND2, 'upstream_chain_bundle')
sys.path.insert(0, ROUND2); sys.path.insert(0, BUNDLE)
import wc_upstream_chain as wuc  # noqa: E402
from wc_upstream_chain import spec as S  # noqa: E402
from sp_retrain import provenance as pv, upstream_chain as uc  # noqa: E402

DATA = os.path.join(BUNDLE, 'wc_upstream_chain', 'data')


def _bytes(p):
    return open(p, 'rb').read()


def test_data_copies_and_evaluator_identical():
    for f in ('numu_l2_inputs_74.txt', 'nue_l2_inputs_258.txt'):
        assert _bytes(os.path.join(DATA, f)) == _bytes(os.path.join(ROUND2, 'config', 'upstream', f))
    assert _bytes(os.path.join(BUNDLE, 'wc_upstream_chain', 'tmva_grad.py')) == _bytes(os.path.join(ROUND2, 'sp_retrain', 'tmva_grad.py'))


def test_l1_json_equals_python_spec():
    assert S.L1_NUE == list(uc.L1_NUE) and S.L1_ALL == uc.L1_ALL
    for m in uc.L1_ALL:
        a, b = S.L1[m], uc.L1_SPEC[m]
        assert a['lists'] == b['lists'] and a['scalars'] == b['scalars'] and a['pool'] == b['pool'] and a['flag'] == b['flag']
        assert np.float32(a['empty']) == np.float32(b['empty']) and a['protect'] == dict(b['protect'])
    assert S.NUMU_FINAL_INPUTS == uc.NUMU_FINAL_INPUTS and S.NUE_FINAL_INPUTS == uc.NUE_FINAL_INPUTS
    assert [c for _, c in S.SIM_DQDX_FINAL] == [c for _, c in uc.SIM_DQDX_FINAL] and S.NUMU_NAN_TO_0 == uc.NUMU_NAN_TO_0


def test_fingerprints_match_the_audit_record():
    rec = json.load(open(os.path.join(ROUND2, 'validation', 'upstream_r4', 'upstream_fingerprints.json')))
    cf = wuc.release_inventory()['chain_fingerprints']
    for route in ('shipped', 'release'):
        for name in ('numu_model_fingerprint', 'nue_l1_fingerprints'):
            assert cf[route][name] == rec[route][name]['fingerprint']


def _bundle_test_module():
    spec = importlib.util.spec_from_file_location('bt', os.path.join(BUNDLE, 'tests', 'test_wc_upstream_chain.py'))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


@pytest.mark.parametrize('kind', ['mc', 'data'])
def test_bundle_equals_aurora_module_on_synthetic_weights(tmp_path, kind):
    bt = _bundle_test_module()
    w = tmp_path / 'uboone' / 'weights'; w.mkdir(parents=True)
    for m in S.L1_ALL:
        (w / S.CHAIN_FILES[m]).write_text(bt._xml(S.L1[m]['lists'] + S.L1[m]['scalars'], cut=0.45))
    (w / S.CHAIN_FILES['numu_final']).write_text(bt._xml(S.NUMU_FINAL_INPUTS, cut=0.3, ivar=S.NUMU_FINAL_INPUTS.index('numu_cc_flag')))
    (w / S.CHAIN_FILES['nue_final']).write_text(bt._xml(S.NUE_FINAL_INPUTS, cut=0.4, ivar=S.NUE_FINAL_INPUTS.index('pio_2_score')))
    C, O = bt._tables()
    O = {m: o.copy() for m, o in O.items()}
    O['numu_1']['numu_cc_1_medium_dQ_dx'] = 1.0; O['numu_1']['numu_cc_1_dQ_dx_cut'] = 1.05
    O['br3_5'].loc[3, 'br3_5_v_energy'] = np.nan
    k = 1.071 if kind == 'mc' else 1.0
    key = wuc.DEFAULT_KEY
    r = wuc.UpstreamChain([str(tmp_path)], sim_dqdx_scale=1.071).score(C, O, kind=kind, key=key)
    A = uc.ChainScorer([str(tmp_path)], uc.L1_NUMU + ['numu_final'] + list(uc.L1_NUE) + ['nue_final'])
    an = A.numu(C, O, k); ae = A.nue(C, O, final=True)
    for s in S.NUMU_SCORES:
        assert (r[s].to_numpy() == an[s]).all(), s
    for s in S.NUE_L1_SCORES + ['nue_score']:
        assert (r[s].to_numpy() == ae[s]).all(), s
    assert (r.diag_numu_cc_flag_bdt.to_numpy() == an['numu_cc_flag_bdt']).all()


def test_patched_stamp_is_exact_and_development_only():
    st = pv.UPSTREAM_R4_DEV_TOOLKIT['stamp']
    assert st == 'numu-sim-dqdx-scale-0.38.0-1-gccb19cf'
    assert pv.upstream_r4_dev_stamp_ok(st, 'development_validation')
    for purpose in ('final', 'final_reconstruction_campaign', 'production', '', None):
        assert not pv.upstream_r4_dev_stamp_ok(st, purpose)
    for near in ('numu-sim-dqdx-scale-0.38.0-1-gccb19c', 'numu-sim-dqdx-scale-0.38.0-2-gccb19cf', 'numu-sim-dqdx-scale-0.38.0',
                 'HEAD-0.38.0-1-gccb19cf', ' ' + st, st + ' ', st.upper()):
        assert not pv.upstream_r4_dev_stamp_ok(near, 'development_validation')
    assert not pv.wcl1116_stamp_ok(st) and not pv.WCL1116.stamp_ok(st)                 # not a WCLocal2026Nov16 stamp
    rec = pv.UPSTREAM_R4_DEV_TOOLKIT
    assert rec['commit'].startswith('ccb19cf') and len(rec['commit']) == 40 and rec['base_commit'] == pv.WCL1116_TOOLKIT_COMMIT
    aux = {a['path']: a['sha256'] for a in wuc.release_inventory()['auxiliary_files']}
    assert aux['releases/' + rec['patch']['file'][len('releases/'):]] == rec['patch']['sha256']
    assert aux['releases/' + rec['workflow']['patch'][len('releases/'):]] == rec['workflow']['patch_sha256']
    assert rec['observed']['stamp'] == st and rec['approved_by'] == 'Avinay Bhat'


def test_final_campaign_template_carries_no_assumed_values():
    import yaml
    t = yaml.safe_load(open(os.path.join(ROUND2, 'config', 'campaigns', 'round2_final_reco_candidate.yaml')))
    txt = json.dumps(t)
    assert 'numu-sim-dqdx-scale-0.38.0-1-gccb19cf' not in txt                          # the dev approval does not leak into it
    up = t.get('upstream') or {}
    for k in ('numu_model_fingerprint', 'nue_l1_fingerprints'):
        assert up.get(k) in (None, '', [], {})
