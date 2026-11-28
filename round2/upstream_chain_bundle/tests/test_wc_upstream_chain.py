"""Self-contained tests of wc_upstream_chain (synthetic TMVA weight files; no data, no ROOT, no xgboost).

Optional end-to-end test on the Aurora development fixture (set all three to run it):
  WC_UPSTREAM_FIXTURE=<fixture dir>  WC_UPSTREAM_RELEASES=<clone>/releases  WC_UPSTREAM_SHIPPED=<wire-cell-data dir>
"""
import hashlib
import json
import math
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import wc_upstream_chain as wuc  # noqa: E402
from wc_upstream_chain import spec as S  # noqa: E402
from wc_upstream_chain.identity import IdentityError, join_exact, translate  # noqa: E402

KEY = wuc.DEFAULT_KEY
LEAF = 0.3


def _mva(r):
    """TMVA EvaluateMVA of one float32 leaf response, as the toolkit computes it (float32 leaf summed in double, then
    2 / (1 + exp(-2 sum)) - 1; math.tanh of the decimal leaf differs in the last bit)."""
    r = float(np.float32(r))
    return np.float32(2.0 / (1.0 + math.exp(-2.0 * r)) - 1.0)


def _xml(names, cut=0.5, ivar=0):
    """One-tree TMVA Grad weight file: x[ivar] >= cut -> +LEAF else -LEAF."""
    v = ''.join('<Variable VarIndex="%d" Expression="%s" Label="%s" Title="%s" Unit="" Internal="%s" Type="F" Min="0" Max="1"/>'
                % (i, n, n, n, n) for i, n in enumerate(names))
    return ('<?xml version="1.0"?><MethodSetup Method="BDT::BDT"><GeneralInfo><Info name="TMVA Release" value="4.2.1"/></GeneralInfo>'
            '<Options><Option name="BoostType" modified="Yes">Grad</Option></Options>'
            '<Variables NVar="%d">%s</Variables><Spectators NSpec="0"/><Classes NClass="2"/><Transformations NTransformations="0"/>'
            '<MVAPdfs/><Weights NTrees="1" AnalysisType="0"><BinaryTree type="DecisionTree" boostWeight="1" itree="0">'
            '<Node pos="s" depth="0" NCoef="0" IVar="%d" Cut="%r" cType="1" res="0" rms="0" purity="0.5" nType="0">'
            '<Node pos="l" depth="1" NCoef="0" IVar="-1" Cut="0" cType="1" res="%r" rms="0" purity="0" nType="-1"/>'
            '<Node pos="r" depth="1" NCoef="0" IVar="-1" Cut="0" cType="1" res="%r" rms="0" purity="1" nType="1"/>'
            '</Node></BinaryTree></Weights></MethodSetup>' % (len(names), v, ivar, cut, -LEAF, LEAF))


@pytest.fixture(scope='module')
def wdir(tmp_path_factory):
    d = tmp_path_factory.mktemp('weights')
    w = d / 'uboone' / 'weights'; w.mkdir(parents=True)
    for m in S.L1_ALL + ['numu_3']:
        names = S.L1[m]['lists'] + S.L1[m]['scalars'] if m in S.L1 else ['a']
        (w / S.CHAIN_FILES[m]).write_text(_xml(names))
    # finals split on numu_1_score / br3_3_score so the level-1 outputs propagate
    (w / S.CHAIN_FILES['numu_final']).write_text(_xml(S.NUMU_FINAL_INPUTS, cut=0.0, ivar=S.NUMU_FINAL_INPUTS.index('numu_1_score')))
    (w / S.CHAIN_FILES['nue_final']).write_text(_xml(S.NUE_FINAL_INPUTS, cut=0.4, ivar=S.NUE_FINAL_INPUTS.index('br3_3_score')))
    return str(d)


def _tables(n=6):
    rng = np.random.default_rng(1)
    C = pd.DataFrame({c: rng.uniform(0.1, 0.9, n) for c in S.candidate_inputs()})
    C['file_id'] = 'f.root'; C['run'] = 1; C['subrun'] = 2; C['event'] = np.arange(n); C['cand'] = 0
    C['br_filled'] = [1, 1, 1, 0, 1, 1]; C['pio_filled'] = [1, 0, 1, 1, 1, 1]; C['pio_flag_pio'] = 0
    C['numu_cc_flag'] = 1.0; C['numu_cc_flag_3'] = 0.0
    for c in ('cosmict_2_filled', 'cosmict_3_filled', 'cosmict_7_filled'):
        C[c] = 1
    O = {}
    for m in S.L1_ALL:
        rows = []
        for e in range(n - 1):                         # the last candidate has no object in any list
            for j in range(2):
                r = dict(file_id='f.root', run=1, subrun=2, event=e, cand=0, index=j)
                for x in S.L1[m]['lists'] + S.L1[m]['scalars']:
                    r[x] = 0.7 if (j == 0 and e % 2 == 0) else 0.2
                r['flag'] = 1.0
                rows.append(r)
        O[m] = pd.DataFrame(rows)
    return C, O


def test_spec_shapes():
    assert len(S.NUMU_FINAL_INPUTS) == 74 and len(S.NUE_FINAL_INPUTS) == 258 and len(S.L1_ALL) == 18 and len(S.UPSTREAM_OUTPUTS) == 20
    assert not set(S.candidate_inputs()) & set(S.NUMU_SCORES + S.NUE_L1_SCORES)
    assert S.SIM_DQDX_INPUTS == ['numu_cc_1_medium_dQ_dx', 'cosmict_2_dQ_dx_end', 'cosmict_2_dQ_dx_front', 'cosmict_3_dQ_dx_end',
                                 'cosmict_3_dQ_dx_front', 'cosmict_7_dQ_dx_end', 'cosmict_7_dQ_dx_front']
    assert abs(float(wuc.SATURATED_LOW) - (-16.2556)) < 1e-4 and float(wuc.NUE_NOT_RUN) == -15.0


def test_scaled_dqdx():
    q = np.array([1.0, -1.0, 0.0, np.nan, np.inf, 3.3], np.float32)
    s = wuc.scaled_dqdx(q, 1.071)
    assert s[0] == np.float32(np.float64(np.float32(1.0)) * 1.071) and s[5] == np.float32(np.float64(np.float32(3.3)) * 1.071)
    assert s[1] == -1.0 and s[2] == 0.0 and np.isnan(s[3]) and np.isinf(s[4])
    assert (wuc.scaled_dqdx(q, 1.0)[[0, 1, 2, 5]] == q[[0, 1, 2, 5]]).all()


def test_level1_pooling_empty_and_pio2_gate(wdir):
    C, O = _tables()
    r = wuc.UpstreamChain([wdir], sim_dqdx_scale=1.071).score(C, O, kind='data')
    hi, lo = _mva(LEAF), _mva(-LEAF)
    # nu_mu numu_1 pools by max: events 0,2,4 have one object at 0.7 (>= cut) -> hi; others lo; the last has no object -> empty
    assert list(r.numu_1_score) == [hi, lo, hi, lo, hi, S.EMPTY['numu_1']]
    # nu_e pools by min -> lo wherever there are objects (the 0.2 object), empty constant without objects
    assert (r.br3_3_score.iloc[:5] == lo).all() and r.br3_3_score.iloc[5] == S.EMPTY['br3_3']
    # pio_2 is gated: candidate 1 has pio_filled == 0 -> empty constant despite its objects
    assert r.pio_2_score.iloc[1] == S.EMPTY['pio_2'] and r.pio_2_score.iloc[0] == lo
    # level-1 models are NOT gated by br_filled (candidate 3 has br_filled == 0 but objects)
    assert r.br3_3_score.iloc[3] == lo
    # nue_score: -15 where br_filled != 1
    assert r.nue_score.iloc[3] == wuc.NUE_NOT_RUN and (r.nue_score.iloc[[0, 1, 2, 4, 5]] != wuc.NUE_NOT_RUN).all()


def test_nan_conventions(wdir):
    C, O = _tables()
    O = {m: o.copy() for m, o in O.items()}
    O['br3_3'].loc[0, 'br3_3_v_energy'] = np.nan          # a NaN object evaluates to -999: it wins the min
    O['numu_1'].loc[2, 'numu_cc_1_length'] = np.nan       # event 1's first object -> -999, loses the max
    C.loc[4, 'kine_reco_Enu'] = np.nan                    # a NaN final input -> EvaluateMVA -999 -> saturated score
    r = wuc.UpstreamChain([wdir], sim_dqdx_scale=1.071).score(C, O, kind='data')
    assert r.br3_3_score.iloc[0] == np.float32(-999.0) and r.diag_l1_models_with_nan_object.iloc[0] >= 1
    assert r.numu_1_score.iloc[1] == _mva(-LEAF)
    if 'kine_reco_Enu' in S.NUMU_FINAL_INPUTS:
        assert r.numu_score.iloc[4] == wuc.SATURATED_LOW and r.diag_numu_final_nan_input.iloc[4]
    if 'kine_reco_Enu' in S.NUE_FINAL_INPUTS:
        assert r.nue_score.iloc[4] == wuc.SATURATED_LOW and r.diag_nue_final_nan_input.iloc[4]


def test_numu_final_protections(wdir):
    C, O = _tables()
    for c in S.NUMU_NAN_TO_0:
        C[c] = np.nan                                    # replaced by 0, never a NaN input
    r = wuc.UpstreamChain([wdir], sim_dqdx_scale=1.071).score(C, O, kind='data')
    assert not r.diag_numu_final_nan_input.any()


def test_sim_correction_flag_copy_and_data(wdir):
    C, O = _tables()
    O = {m: o.copy() for m, o in O.items()}
    O['numu_1']['numu_cc_1_medium_dQ_dx'] = 1.0; O['numu_1']['numu_cc_1_dQ_dx_cut'] = 1.05   # 1.071 > 1.05: flag switches off
    O['numu_2']['flag'] = 0.0
    O['numu_2'].loc[O['numu_2'].event == 2, 'flag'] = 1.0                                      # event 2 keeps it through numu_cc_2
    C.loc[3, 'numu_cc_flag_3'] = 1.0                                                           # event 3 keeps it through flag_3
    uc = wuc.UpstreamChain([wdir], sim_dqdx_scale=1.071)
    mc = uc.score(C, O, kind='mc'); da = uc.score(C, O, kind='data'); diag = uc.score(C, O, kind='mc', apply_sim_correction=False)
    assert list(mc.diag_numu_cc_flag_bdt) == [0, 0, 1, 1, 0, 1]          # event 5 has no numu_1 segment: unchanged
    assert (da.diag_numu_cc_flag_bdt == 1).all() and (diag.diag_numu_cc_flag_bdt == 1).all()
    assert (mc.diag_sim_dqdx_scale == 1.071).all() and (da.diag_sim_dqdx_scale == 1.0).all()
    assert list(mc.diag_numu_cc_flag_switched_off) == [True, True, False, False, True, False]
    # the input tables are never modified
    assert (C['numu_cc_flag'] == 1).all() and (O['numu_1']['numu_cc_1_medium_dQ_dx'] == 1.0).all()


def test_input_errors(wdir):
    C, O = _tables(); uc = wuc.UpstreamChain([wdir], sim_dqdx_scale=1.071)
    with pytest.raises(wuc.InputError):
        uc.score(C, O, kind=None)
    with pytest.raises(wuc.InputError):
        uc.score(pd.concat([C, C.iloc[:1]]), O, kind='data')
    bad = {m: o.copy() for m, o in O.items()}; bad['br3_3'].loc[0, 'event'] = 999
    with pytest.raises(wuc.InputError):
        uc.score(C, bad, kind='data')
    with pytest.raises(wuc.InputError):
        uc.score(C.drop(columns=['br_filled']), O, kind='data')


def test_sim_scale_follows_the_numu_weights(wdir):
    with pytest.raises(wuc.InputError):                      # synthetic weights: neither release nor shipped
        wuc.UpstreamChain([wdir])
    assert wuc.UpstreamChain([wdir], numu=False).k_sim == 1.0


def test_resolution_order_and_fingerprints(wdir, tmp_path):
    first = tmp_path / 'first' / 'uboone' / 'weights'; first.mkdir(parents=True)
    (first / S.CHAIN_FILES['numu_1']).write_text(_xml(S.L1['numu_1']['lists'], cut=0.9))
    assert wuc.resolve([str(tmp_path / 'first'), wdir], S.CHAIN_FILES['numu_1']).startswith(str(tmp_path / 'first'))
    assert wuc.resolve([str(tmp_path / 'first'), wdir], S.CHAIN_FILES['numu_2']).startswith(wdir)
    fp = wuc.chain_fingerprints([wdir])
    lines = fp['nue_l1_fingerprints'][1]
    assert fp['nue_l1_fingerprints'][0] == hashlib.sha256(('\n'.join(sorted(lines)) + '\n').encode()).hexdigest() and len(lines) == 15


def test_inventory_counts_and_fingerprint():
    inv = wuc.release_inventory()
    c = inv['counts']
    assert c['canonical_files'] == 57 and c['aurora_audit_checks'] == 61 and c['eaf_audit_files'] == 57 and c['distinct_contents'] == 42
    lines = ['%s %s' % (e['path'], e['sha256_manifest']) for e in inv['canonical_files']]
    assert hashlib.sha256(('\n'.join(sorted(lines)) + '\n').encode()).hexdigest() == inv['fingerprints']['canonical_inventory']
    assert inv['fingerprints']['canonical_inventory'] == '1d48baed0b3d386b3848c20829099b736f42d6020456f4ea60dd4dbbf60c1f9f'
    assert inv['release_commit'] == '0f13988db44423a227789e151b0a374e25771abd'
    assert inv.get('eaf_cross_check', {}).get('same_hashes') is True
    cf = inv['chain_fingerprints']
    assert cf['release']['numu_model_fingerprint'].startswith('0b8485a8') and cf['release']['nue_l1_fingerprints'].startswith('36ec972f')
    assert cf['shipped']['numu_model_fingerprint'].startswith('595a9963') and cf['shipped']['nue_l1_fingerprints'].startswith('17a8e17e')
    assert inv['chain_set']['numu_3']['release_path'] is None                  # numu_tagger3 is not released: shipped fallback


def test_identity_and_sp_replacement(wdir):
    C, O = _tables()
    m = C[KEY].assign(file_index=7, ev=np.arange(len(C)), evt=C.event, nu_index=C.cand)
    t = translate(C[KEY], m, KEY, ['file_index', 'ev', 'run', 'subrun', 'evt', 'nu_index'])
    assert len(t) == len(C)
    with pytest.raises(IdentityError):
        translate(C[KEY], m.iloc[1:], KEY, ['file_index', 'ev'])
    with pytest.raises(IdentityError):
        join_exact(C[KEY], C[KEY].iloc[1:], KEY)
    r = wuc.UpstreamChain([wdir], sim_dqdx_scale=1.071).score(C, O, kind='mc')
    frame = C[KEY].assign(numu_score=-5.0, numu_1_score=-5.0, br3_3_score=-5.0, numu_cc_flag=1.0, cosmict_2_dQ_dx_end=2.0, other=3.0)
    out = wuc.sp.replace_upstream_inputs(frame, r, KEY, 'B')
    assert (out.numu_score.to_numpy(np.float32) == r.numu_score.to_numpy()).all() and (out.br3_3_score == -5.0).all()
    assert (out.numu_cc_flag == 1.0).all() and (out.cosmict_2_dQ_dx_end == 2.0).all() and (out.other == 3.0).all()
    out = wuc.sp.replace_upstream_inputs(frame, r, KEY, 'D')
    assert (out.br3_3_score.to_numpy(np.float32) == r.br3_3_score.to_numpy()).all()
    assert wuc.sp.replaced_inputs('single_photon_nue', 'D') == []


@pytest.mark.skipif(not all(os.environ.get(v) for v in ('WC_UPSTREAM_FIXTURE', 'WC_UPSTREAM_RELEASES', 'WC_UPSTREAM_SHIPPED')),
                    reason='fixture / release clone / wire-cell-data not configured')
def test_aurora_fixture_bit_exact():
    from wc_upstream_chain.cli import check_fixture
    r = check_fixture(os.environ['WC_UPSTREAM_FIXTURE'], os.environ['WC_UPSTREAM_RELEASES'], os.environ['WC_UPSTREAM_SHIPPED'],
                      os.environ.get('WC_UPSTREAM_FIXTURE_PART', 'all'))
    assert r['ok'], json.dumps([c for c in r['cases'] if not c['ok']])[:2000]
