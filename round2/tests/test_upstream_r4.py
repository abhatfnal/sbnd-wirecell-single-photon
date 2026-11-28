"""Upstream nu_mu round3af / nu_e A v2 integration: chain emulation conventions, overlay safety, dependency matrix,
release checksums. Tests that need Xuyang's cloned release skip when it is absent."""
import json
import os
import sys

import numpy as np
import pandas as pd
import pytest

ROUND2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROUND2)
from sp_retrain import upstream_chain as uc, upstream_overlay as uo  # noqa: E402

XREPO = '/lus/flare/projects/neutrinoGPU/abhat/sbnd/sp-bdt-round2-work-20261117/upstream_release_audit/sbnd-wirecell-bdt'
VAL = os.path.join(ROUND2, 'validation', 'upstream_r4')
need_repo = pytest.mark.skipif(not os.path.isdir(XREPO), reason='release clone absent')


class Stub:
    """Forest stand-in: EvaluateMVA = column `col` of X (so tests choose object values), -999 on any NaN input."""
    def __init__(self, col=0):
        self.col = col

    def evaluate_mva(self, X):
        X = np.asarray(X, np.float32)
        v = X[:, self.col].astype(np.float64)
        v[np.isnan(X).any(1)] = -999.0
        return v


def scorer(stubs):
    s = uc.ChainScorer.__new__(uc.ChainScorer)
    s.dirs, s.paths, s._f = [], {}, dict(stubs)
    return s


def cands(n, **cols):
    C = pd.DataFrame(dict(file_id=['f'] * n, run=[1] * n, subrun=[1] * n, event=list(range(n)), cand=[0] * n))
    for k, v in cols.items():
        C[k] = v
    return C


def objs(rows, model):
    d = uc.L1_SPEC[model]
    O = pd.DataFrame(rows)
    for c in d['lists'] + d['scalars'] + ['flag']:
        if c not in O:
            O[c] = 1.0
    O['file_id'] = 'f'; O['run'] = 1; O['subrun'] = 1; O['cand'] = 0
    return O


def test_input_lists_match_release_and_spec_copy():
    assert len(uc.NUMU_FINAL_INPUTS) == 74 and len(uc.NUE_FINAL_INPUTS) == 258
    assert uc.NUMU_FINAL_INPUTS[71:] == ['cosmict_10_score', 'numu_1_score', 'numu_2_score']
    assert [m for m in uc.L1_NUE] == ['br3_3', 'br3_5', 'br3_6', 'pio_2', 'stw_2', 'stw_3', 'stw_4', 'sig_1', 'sig_2', 'lol_1', 'lol_2', 'tro_1', 'tro_2', 'tro_4', 'tro_5']
    assert {m: uc.L1_SPEC[m]['empty'] for m in uc.L1_NUMU} == {'numu_1': -0.4, 'numu_2': -0.1, 'cosmict_10': 0.7}
    assert uc.L1_SPEC['pio_2']['pre_cut'] == 'pio_filled == 1 and pio_flag_pio == 0'
    assert not any(x in uc.NUE_FINAL_INPUTS for x in ('numu_score', 'numu_1_score', 'numu_2_score', 'cosmict_10_score'))


@need_repo
def test_copied_spec_files_are_byte_identical_to_pinned_release():
    for a, b in (('numu_l2_inputs_74.txt', 'spec/numu_l2_inputs_74.txt'), ('nue_l2_inputs_258.txt', 'spec/nue_l2_inputs_258.txt'),
                 ('l1_models_xning_0f13988d.py', 'spec/l1_models.py')):
        assert uc.sha256(os.path.join(uc.CFG, a)) == uc.sha256(os.path.join(XREPO, b))
    man = json.load(open(os.path.join(XREPO, 'releases', 'numu_round3af', 'manifest.json')))
    assert man['inputs'] == uc.NUMU_FINAL_INPUTS and man['nan_to_0'] == uc.NUMU_NAN_TO_0


def test_scaled_dqdx_only_finite_positive():
    q = np.array([2.0, 0.0, -1.0, np.nan, np.inf, 1.5], np.float32)
    s = uc.scaled_dqdx(q, 1.071)
    assert s[0] == np.float32(np.float64(np.float32(2.0)) * 1.071) and s[5] == np.float32(np.float64(np.float32(1.5)) * 1.071)
    assert s[1] == 0 and s[2] == -1 and np.isnan(s[3]) and np.isinf(s[4])
    assert (uc.scaled_dqdx(q[:3], 1.0) == q[:3]).all()


def test_pooling_empty_constant_and_nan_sentinel():
    v, has = uc._pool(3, np.array([0, 0, 2]), np.array([0.2, -999.0, 0.5]), 'min', np.float32(0.3))
    assert v[0] == np.float32(-999) and v[1] == np.float32(0.3) and v[2] == np.float32(0.5) and has.tolist() == [True, False, True]
    v, _ = uc._pool(2, np.array([0, 0, 1]), np.array([0.2, -999.0, -999.0]), 'max', np.float32(-0.4))
    assert v[0] == np.float32(0.2) and v[1] == np.float32(-999)


def test_pio_2_gate_and_min_pooling():
    C = cands(3, pio_filled=[1, 1, 0], pio_flag_pio=[0, 1, 0], pio_mip_id=[0.0, 0.0, 0.0])
    O = objs([dict(event=0, index=0, pio_2_v_dis2=0.6), dict(event=0, index=1, pio_2_v_dis2=0.4),
              dict(event=1, index=0, pio_2_v_dis2=0.7), dict(event=2, index=0, pio_2_v_dis2=0.9)], 'pio_2')
    v, _, _ = scorer({'pio_2': Stub(0)}).l1('pio_2', C, O)
    assert v[0] == np.float32(0.4) and v[1] == np.float32(0.2) and v[2] == np.float32(0.2)


def test_numu_flag_copy_rule_and_raw_columns_untouched():
    # five candidates: (a) flag1 kept, (b) flag1 lost -> flag off, (c) lost but numu_cc_2 flag on, (d) lost but flag_3 on, (e) no flag1
    n = 5
    base = {nm: [0.0] * n for nm in uc.NUMU_FINAL_INPUTS if nm not in ('cosmict_10_score', 'numu_1_score', 'numu_2_score', 'kine_reco_Enu')}
    base['kine_reco_Enu'] = [500.0] * n
    base['numu_cc_flag'] = [1.0, 1.0, 1.0, 1.0, 1.0]
    base['numu_cc_flag_3'] = [0.0, 0.0, 0.0, 1.0, 0.0]
    base['cosmict_2_filled'] = [1.0, 1.0, 1.0, 1.0, 0.0]; base['cosmict_3_filled'] = [0.0] * n; base['cosmict_7_filled'] = [0.0] * n
    base['cosmict_2_dQ_dx_end'] = [0.5] * n
    C = cands(n, **base)
    O1 = objs([dict(event=0, index=0, numu_cc_1_medium_dQ_dx=1.0, numu_cc_1_dQ_dx_cut=1.5, flag=1.0),
               dict(event=1, index=0, numu_cc_1_medium_dQ_dx=1.45, numu_cc_1_dQ_dx_cut=1.5, flag=1.0),
               dict(event=2, index=0, numu_cc_1_medium_dQ_dx=1.45, numu_cc_1_dQ_dx_cut=1.5, flag=1.0),
               dict(event=3, index=0, numu_cc_1_medium_dQ_dx=1.45, numu_cc_1_dQ_dx_cut=1.5, flag=1.0),
               dict(event=4, index=0, numu_cc_1_medium_dQ_dx=1.45, numu_cc_1_dQ_dx_cut=1.5, flag=0.0)], 'numu_1')
    O2 = objs([dict(event=2, index=0, flag=1.0)], 'numu_2')
    st = {'numu_1': Stub(0), 'numu_2': Stub(0), 'cosmict_10': Stub(0), 'numu_final': Stub(uc.NUMU_FINAL_INPUTS.index('numu_cc_flag'))}
    sc = scorer(st)
    raw = C.copy()
    out = sc.numu(C, {'numu_1': O1, 'numu_2': O2, 'cosmict_10': None}, k=1.071)
    assert out['numu_cc_flag_bdt'].tolist() == [1, 0, 1, 1, 1]
    assert out['numu_score'][1] == np.float32(0.0) and out['numu_score'][0] > 0     # the final model saw the flag copy
    pd.testing.assert_frame_equal(C, raw)                                            # stored columns untouched
    out1 = sc.numu(C, {'numu_1': O1, 'numu_2': O2, 'cosmict_10': None}, k=1.0)
    assert out1['numu_cc_flag_bdt'].tolist() == [1, 1, 1, 1, 1]                       # data / scale 1: no change
    st['numu_final'] = Stub(uc.NUMU_FINAL_INPUTS.index('cosmict_2_dQ_dx_end'))
    v = scorer(st).numu(C, {'numu_1': O1, 'numu_2': O2, 'cosmict_10': None}, k=1.071)['numu_score']
    scaled = uc.log10_odds(np.full(1, float(np.float32(np.float64(np.float32(0.5)) * 1.071))))[0]
    unscaled = uc.log10_odds(np.full(1, 0.5))[0]
    assert v[0] == np.float32(scaled) and v[4] == np.float32(unscaled)            # scaled only where cosmict_2_filled == 1
    assert (C['cosmict_2_dQ_dx_end'] == 0.5).all()


def test_overlay_apply_refuses_misaligned_rows(tmp_path):
    C = pd.DataFrame(dict(sample=['s', 's'], file_id=['f', 'f'], run=[1, 1], subrun=[1, 1], event=[1, 2], cand=[0, 0]))
    for c in uo.NUMU_SCORES:
        C[c] = [0.5, 0.6]
    O = C[uo.KEY].copy()
    for c in uo.NUMU_SCORES:
        O['stored_' + c] = np.array([0.5, 0.6], np.float32); O['ovl_' + c] = np.array([0.9, 0.1], np.float32)
    O.to_parquet(uo.overlay_path(str(tmp_path), 's'))
    D = uo.apply(C, 'B', str(tmp_path))
    assert np.allclose(D['numu_score'], [0.9, 0.1]) and np.allclose(C['numu_score'], [0.5, 0.6])
    assert uo.apply(C, 'A', str(tmp_path)).equals(C)
    bad = C.copy(); bad.loc[0, 'numu_score'] = 0.55
    with pytest.raises(ValueError, match='wrong join'):
        uo.apply(bad, 'B', str(tmp_path))
    extra = pd.concat([C, C.iloc[[0]].assign(event=3)], ignore_index=True)
    with pytest.raises(ValueError, match='no overlay row'):
        uo.apply(extra, 'B', str(tmp_path))


def test_xn_split_v11_matches_xuyang_rule():
    s = np.array(['wcl1116-aurora-bnb', 'wcl1116-aurora-bnb', 'wcl1116-fg-beamoff-train', 'wcl1116-fg-beamoff-train'])
    r = uo.xn_split_v11(s, [5, 5, 11, 12], [10, 11, 1, 1])
    assert r.tolist() == ['dev', 'train', 'dev', 'train']
    if os.path.isdir(XREPO):
        sys.path.insert(0, os.path.join(XREPO, 'spec'))
        import spec_v1
        xs = np.array(['wcl1116-bnb', 'wcl1116-bnb', 'wcl1116-beam-off-train', 'wcl1116-beam-off-train'], dtype=object)
        assert spec_v1.split_v11(xs, np.array([5, 5, 11, 12]), np.array([10, 11, 1, 1])).tolist() == r.tolist()


def test_dependency_matrix_committed():
    d = json.load(open(os.path.join(VAL, 'sp_upstream_dependency_matrix.json')))
    sp = d['sp']
    assert sp['single_photon_numu']['replaced_by_numu_round3af'] == ['numu_1_score', 'numu_score']
    assert sorted(sp['single_photon_other']['replaced_by_numu_round3af']) == sorted(uo.NUMU_SCORES)
    assert sp['single_photon_ncpi0']['replaced_by_nue_round4_ruleA_v2'] == [c for c in uo.NUE_L1_SCORES[::-1]] or \
        sorted(sp['single_photon_ncpi0']['replaced_by_nue_round4_ruleA_v2']) == sorted(uo.NUE_L1_SCORES)
    assert not sp['single_photon_nue']['replaced_by_numu_round3af'] and not sp['single_photon_nue']['replaced_by_nue_round4_ruleA_v2']
    assert len(sp['single_photon_other']['sim_scaled_in_bdt_copy_only']) == 6
    assert d['upstream']['nue_final']['reads_numu_outputs'] is False


def test_release_checksums_committed_all_match():
    d = json.load(open(os.path.join(VAL, 'upstream_release_checksums.json')))
    assert d['commit'] == '0f13988db44423a227789e151b0a374e25771abd' and d['verdict'] == 'ALL_MATCH' and d['files_checked'] == 61
    assert d['correction'] == {'mode': 'uniform', 'k': 1.071, 'source': 'gpvm #41 round3_charge_correction.json 3a'}


def test_registry_records_release_but_freezes_nothing():
    import yaml
    d = yaml.safe_load(open(os.path.join(ROUND2, 'config', 'samples', 'round2_training_samples.yaml')))['upstream_models']
    assert d['nu_mu_final']['sha256'] is None and d['nu_e_final']['sha256'] is None
    assert d['nu_mu_final']['release_sha256'] == '81fb26f88bb1aed30455ea5e55e6179f53b49bf6af4a36a119fbd181da6310b6'
    assert d['nu_e_final']['release_sha256'] == '9912f6f2976f6bd0aaa731d8eb04d4f596b5c4e5e0d980ab20d71f142724f078'
    assert d['release_repository']['commit'] == '0f13988db44423a227789e151b0a374e25771abd'
    assert 'RETRAINED' in d['nu_e_level1']['status']


@need_repo
def test_upstream_fingerprints_reproduce():
    d = json.load(open(os.path.join(VAL, 'upstream_fingerprints.json')))
    R = os.path.join(XREPO, 'releases'); S = '/lus/flare/projects/neutrinoGPU/yuhw/wcd-0.38.0'
    if not os.path.isdir(S):
        pytest.skip('wire-cell-data checkout absent')
    assert uc.fingerprint([os.path.join(R, 'numu_round3af', 'wirecell'), S], uc.NUMU_FINGERPRINT_MODELS)[0] == d['release']['numu_model_fingerprint']['fingerprint']
    assert uc.fingerprint([os.path.join(R, 'nue_round4_ruleA_v2', 'wirecell', 'main'), S], uc.L1_NUE)[0] == d['release']['nue_l1_fingerprints']['fingerprint']
    assert uc.fingerprint([S], uc.L1_NUE)[0] == d['shipped']['nue_l1_fingerprints']['fingerprint']
    # numu_tagger3 is not released: it resolves to the shipped file in both sets
    assert [l for l in d['release']['numu_model_fingerprint']['files'] if l.startswith('numu_tagger3')] == \
           [l for l in d['shipped']['numu_model_fingerprint']['files'] if l.startswith('numu_tagger3')]
