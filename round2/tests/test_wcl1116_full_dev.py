"""Tests of the WCL1116 full-development studies (sp_retrain.devstudy and its tools). Run: python -m pytest -q round2/tests"""
import json
import os
import sys

import numpy as np
import pandas as pd
import pytest

ROUND2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROUND2)
from sp_retrain import devstudy as dv, features, firewall, labels  # noqa: E402

VAL = os.path.join(ROUND2, 'validation')


def _keys(n=4000, seed=0):
    rng = np.random.default_rng(seed)
    k = pd.DataFrame(dict(sample=rng.choice(['wcl1116-aurora-ncdr', 'wcl1116-aurora-bnb'], n), file_id='f', run=rng.integers(1, 50, n),
                          subrun=rng.integers(0, 400, n), event=rng.integers(0, 100, n), cand=rng.integers(0, 3, n)))
    k['split'] = np.where(k.subrun % 2 == 1, 'test', 'train')
    return k


# ---------------------------------------------------------------- nested split
def test_nested_split_is_deterministic_unit_level_and_keeps_the_outer_holdout():
    k = _keys()
    r1, r2 = dv.nested_roles(k), dv.nested_roles(k.sample(frac=1.0, random_state=3).sort_index())
    assert (r1 == r2).all()                                            # deterministic, order independent
    assert ((r1 == 'test') == (k.split == 'test')).all()               # outer holdout untouched
    assert set(r1[k.split.to_numpy() == 'train']) <= {'fit', 'nval'}
    t = dv.nested_unit_table(k, r1)                                    # one role per unit: events / candidates stay together
    assert not t.duplicated(dv.UNIT).any()
    tr = t[t.role != 'test']
    assert 0.17 < (tr.role == 'nval').mean() < 0.23
    # the hash depends only on (sample, run, subrun): a different candidate / event / file of the same unit has the same role
    k2 = k.assign(event=k.event + 7, cand=0, file_id='g')
    assert (dv.nested_roles(k2) == r1).all()
    # the sample is part of the unit identity (sample boundaries are preserved)
    assert dv.nested_u('a', 1, 2) != dv.nested_u('b', 1, 2)
    assert dv.nested_u('wcl1116-aurora-ncdr', 7026457, 94) == dv.nested_u('wcl1116-aurora-ncdr', 7026457, 94)


def test_nested_split_has_no_event_leakage_between_fit_and_validation():
    k = _keys(8000, 1)
    r = dv.nested_roles(k)
    ev = k[['sample', 'file_id', 'run', 'subrun', 'event']].astype(str).agg('|'.join, axis=1)
    assert not (set(ev[r == 'fit']) & set(ev[r == 'nval'])) and not (set(ev[r == 'fit']) & set(ev[r == 'test']))


@pytest.mark.parametrize('model', ['numu', 'ncpi0', 'other', 'nue'])
def test_study_summaries_record_no_leakage_and_identical_units_across_modes(model):
    p = {m: os.path.join(VAL, 'wcl1116_full_dev_%s_%s.json' % (model, m)) for m in ('dv2_split_move', 'dv2_snap')}
    if not all(os.path.exists(x) for x in p.values()):
        pytest.skip('studies not run')
    S = {m: json.load(open(x)) for m, x in p.items()}
    for s in S.values():
        assert s['nested_rule'] == 'nested_v1' and s['nested_fraction'] == 0.2
        assert s['leakage'] == dict(events_in_fit_and_nval=0, events_in_fit_and_test=0, events_in_nval_and_test=0)
        assert s['label'].startswith('WCL1116 FULL DEVELOPMENT')
        base = s['variants']['FIT_BASELINE']
        assert base['n_inputs'] == len(features.load('single_photon_' + model).columns) and base['removed'] == []


# ---------------------------------------------------------------- weighting
def test_class_weights_hit_the_target_ratio_with_mean_one():
    y = np.array([1] * 100 + [0] * 1200)
    for r in (4.0, 1.0):
        w = dv.class_weights(y, r)
        assert abs(w[y == 0].sum() / w[y == 1].sum() - r) < 1e-9 and abs(w.mean() - 1.0) < 1e-12
        assert len(set(w[y == 1])) == 1 and len(set(w[y == 0])) == 1
    assert (dv.class_weights(y, None) == 1).all()
    assert dv.WEIGHTINGS == {'UNWEIGHTED_BASELINE': None, 'THESIS_PRIOR_APPROX': 4.0, 'BALANCED_STRESS_TEST': 1.0}


# ---------------------------------------------------------------- ablation families
def test_ablation_families_come_from_the_audited_feature_lists():
    assert dv.upstream_family('numu') == ['numu_1_score', 'numu_score']
    assert sorted(dv.upstream_family('other')) == ['cosmict_10_score', 'numu_1_score', 'numu_2_score', 'numu_score']
    assert dv.upstream_family('nue') == [] and len(dv.upstream_family('ncpi0')) == 15
    cos = dv.cosmic_tagger_direct('other')
    assert len(cos) == 59 and all(c.startswith(('cosmict_', 'cosmic_')) for c in cos) and 'cosmict_10_score' not in cos
    ab = dv.ablations('other')
    assert {k: len(v) for k, v in ab.items()} == {'A_FULL': 0, 'B_NO_COSMIC_TAGGER_DIRECT': 59, 'C_NO_UPSTREAM_NUMU_FAMILY': 4, 'D_NO_COSMIC_NO_UPSTREAM': 63}
    cols = set(features.load('single_photon_other').columns)
    assert all(set(v) <= cols for v in ab.values())
    assert dv.ablations('numu') == {'A_FULL': [], 'B_NO_FINAL_NUMU_SCORE': ['numu_score'], 'C_NO_UPSTREAM_NUMU_FAMILY': ['numu_1_score', 'numu_score']}
    with pytest.raises(ValueError):
        dv.ablations('nue')


@pytest.mark.parametrize('model', ['numu', 'ncpi0', 'other', 'nue'])
def test_no_bookkeeping_identifier_is_an_input(model):
    assert not set(features.load('single_photon_' + model).columns) & dv.BOOKKEEPING


# ---------------------------------------------------------------- thresholds
def test_threshold_table_is_monotonic_and_op_points_match_targets():
    rng = np.random.default_rng(5)
    y = np.r_[np.ones(3000), np.zeros(9000)].astype(int)
    s = np.r_[rng.normal(1.0, 1.0, 3000), rng.normal(-1.0, 1.0, 9000)]
    leg = s + rng.normal(0, 0.8, len(s))
    comp = np.where(y == 1, 'signal', rng.choice(['a', 'b'], len(y)))
    t = dv.threshold_table(y, s, comp, ('a', 'b'))
    assert dv.is_monotonic(t) and (np.diff(t.threshold) < 0).all()
    bad = t.copy(); bad.loc[3, 'background_acceptance'] = 2.0
    assert not dv.is_monotonic(bad)
    op = dv.op_points(y, s, leg, 0.0)
    assert abs(op['A_equal_signal_efficiency']['signal_efficiency'] - op['legacy']['signal_efficiency']) < 1e-3
    assert abs(op['B_equal_background_acceptance']['background_acceptance'] - op['legacy']['background_acceptance']) < 1e-3
    assert op['A_equal_signal_efficiency']['background_acceptance'] < op['legacy']['background_acceptance']   # the better score


# ---------------------------------------------------------------- final-domain rerun template
def _tool(name):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROUND2, 'tools', name + '.py'))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def _complete_campaign(tmp_path):
    import hashlib, yaml
    g = _tool('final_domain_campaign')
    c = yaml.safe_load(open(os.path.join(ROUND2, 'config', 'campaigns', 'round2_final_reco_candidate.yaml')))
    h = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
    stage = tmp_path / 'stage'; stage.mkdir()
    for k, n in (('ncdr_list', 3), ('bnb_list', 2), ('nuecc_list', 2), ('beamoff_train_list', 2)):
        p = tmp_path / (k + '.txt')
        root = str(stage) if k == 'beamoff_train_list' else '/lus/flare/projects/neutrinoGPU/yuhw/production-prep/NEXT/full'
        p.write_text(''.join('%s/u%d/x.wc.flat.caf.root\n' % (root, j) for j in range(n)))
        c['inputs'][k] = dict(path=str(p), sha256=h(p), files=n)
    c['production'].update(tag='WCLocalNEXT', toolkit_commit='a' * 40, toolkit_version_stamps=['0.39.0', 'HEAD-0.39.0'], toolkit_stamp_evidence='build records',
                           dl_bundle='dv2max/sbnd/next/bundle.json', dl_bundle_sha256='b' * 64, vertex_mode='dv2_split_move',
                           wc_trees={'recTreeWireCell': 'dv2_split_move'}, effective_boundary_profile='measured_effective_v1', effective_boundary_sha256='c' * 64)
    c['upstream'].update(numu_model_fingerprint='d' * 64, nue_l1_fingerprints='e' * 64)
    rec = tmp_path / 'staging.json'
    rec.write_text(json.dumps(dict(status='VERIFIED', expect_reco='campaign', list_sha256=c['inputs']['beamoff_train_list']['sha256'],
                                   toolkit_commit='a' * 40, verifier_sha256='f' * 64, wct_version_stamp='HEAD-0.39.0')))
    c['inputs']['beamoff_staging_record'] = dict(path=str(rec), sha256=h(rec))
    c['inputs']['beamoff_verifier_sha256'] = 'f' * 64
    c['inputs']['beamoff_exception'] = dict(approved_by='Avinay Bhat', date='2026-12-01', staged_dir=str(stage))
    return g, c


def test_final_domain_template_is_refused_until_every_field_is_supplied():
    import yaml
    g = _tool('final_domain_campaign')
    c = yaml.safe_load(open(os.path.join(ROUND2, 'config', 'campaigns', 'round2_final_reco_candidate.yaml')))
    assert c['campaign'] == 'round2_final_reco_candidate' and c['status'] == 'TEMPLATE_NOT_RUNNABLE'
    bad = g.check(c)
    for f in ('production.tag', 'production.toolkit_commit', 'production.toolkit_version_stamps', 'production.dl_bundle_sha256', 'production.vertex_mode',
              'production.effective_boundary_profile', 'production.effective_boundary_sha256', 'upstream.numu_model_fingerprint', 'upstream.nue_l1_fingerprints',
              'inputs.ncdr_list.path', 'inputs.bnb_list.sha256', 'inputs.nuecc_list.files', 'inputs.beamoff_train_list.path',
              'inputs.beamoff_verifier_sha256', 'inputs.beamoff_exception.approved_by'):
        assert any(b.startswith(f) for b in bad), f
    with pytest.raises(SystemExit):
        g.make_specs(c)
    with pytest.raises(SystemExit):
        g.plan(c, '/tmp/never')


def test_complete_final_domain_campaign_generates_trainable_frozen_specs_and_a_ten_step_plan(tmp_path):
    from sp_retrain import devtrain
    import copy
    g, c = _complete_campaign(tmp_path)
    assert g.check(c) == []
    specs = g.make_specs(c)
    assert sorted(specs) == ['ncpi0', 'nue', 'numu', 'other']
    for m, s in specs.items():
        base = labels.load_spec(os.path.join(ROUND2, 'specs', 'single_photon_%s_training_spec_dev_wcl1116_dv2_split_move.yaml' % m))
        devtrain.require_development_spec(s)                        # the trainer accepts it unchanged
        assert s['xgboost'] == base['xgboost'] and s['inputs'] == base['inputs'] and s['label'] == base['label']    # frozen
        assert s['campaign'] == 'round2_final_reco_candidate' and s['deployable'] is False and s['reconstruction']['toolkit_commit'] == 'a' * 40
        assert all(firewall.official_marker(d['id']) is None for d in s['samples']['development'] if d.get('role') != 'ext_beam_off')
    ext = [d for d in specs['other']['samples']['development'] if d.get('role') == 'ext_beam_off'][0]
    assert ext['wct_version_stamp'] == 'HEAD-0.39.0' and specs['other']['samples']['approved_exceptions'][0]['approved_by'] == 'Avinay Bhat'
    body = g.plan(c, str(tmp_path / 'plan'))
    pos = [body.index('# %d ' % k) for k in range(1, 11) if '# %d ' % k in body]
    assert len(pos) == 9 and pos == sorted(pos) and '# 7 export + 8 Python equivalence' in body      # steps 7 and 8 share one tool
    # every single defect is refused
    for path, val in (('production.toolkit_commit', 'abc'), ('production.vertex_mode', 'dv2_other'), ('production.toolkit_version_stamps', ['x', 'x']),
                      ('upstream.numu_model_fingerprint', 'TBD'), ('production.dl_bundle_sha256', 'B' * 64)):
        c2 = copy.deepcopy(c); a, b = path.split('.'); c2[a][b] = val
        assert g.check(c2), path
    c2 = copy.deepcopy(c); c2['inputs']['bnb_list']['sha256'] = '0' * 64
    assert any('does not match' in b for b in g.check(c2))
    c2 = copy.deepcopy(c); open(c2['inputs']['ncdr_list']['path'], 'a').write('/pnfs/sbnd/x/beam-off/y.root\n')
    assert g.check(c2)                                              # hash and line count no longer match, official marker present


def test_campaign_provenance_is_exact_and_explicit():
    from sp_retrain import provenance as pv
    v = _tool('verify_staged_beamoff')
    spec = dict(campaign='round2_final_reco_candidate', production=dict(toolkit_commit='a' * 40, toolkit_version_stamps=['0.39.0', 'HEAD-0.39.0'],
                dl_bundle='dv2max/sbnd/next/bundle.json', dl_bundle_sha256='b' * 64, wc_trees={'recTreeWireCell': 'dv2_split_move'}))
    p = pv.from_campaign_spec(spec)
    ok = dict(trees={'recTree': True, 'recTreeWireCell': True}, recTreeWireCell=dict(wct_version='HEAD-0.39.0', dl_weights=p.dl_weights('dv2_split_move')))
    assert v.wcl1116_problems(ok, p) == []
    for s in ('HEAD-0.39.0-1-gabcdef1', '0.38.0', 'HEAD-0.38.0', 'branch-0.39.0'):
        assert v.wcl1116_problems(dict(ok, recTreeWireCell=dict(ok['recTreeWireCell'], wct_version=s)), p), s
    with pytest.raises(ValueError):
        pv.from_campaign_spec(dict(production=dict(toolkit_commit='a' * 40)))
    assert pv.WCL1116.stamp_ok('HEAD-0.38.0') and not pv.WCL1116.stamp_ok('HEAD-0.39.0')


# ---------------------------------------------------------------- operating points and joint four-cut evaluator
def test_joint_cut_order_is_the_production_order():
    op = _tool('sp_operating_points')
    assert op.ORDER == ('numu', 'other', 'ncpi0', 'nue')
    assert set(op.LEVELS) >= {0.80, 0.85, 0.90, 0.95, 0.98, None}          # the pre-declared levels are all kept


@pytest.mark.parametrize('mode', ['dv2_split_move', 'dv2_snap'])
def test_operating_point_outputs_are_monotonic_ordered_and_unfrozen(mode):
    p = os.path.join(VAL, 'sp_operating_points_%s.json' % mode)
    if not os.path.exists(p):
        pytest.skip('operating points not run')
    d = json.load(open(p))
    assert 'NOT ROUND2 CUT' in d['label'] and 'NO THRESHOLD FROZEN' in d['label']
    for m, v in d['models'].items():
        assert v['threshold_table_monotonic'], m
        t = pd.read_csv(os.path.join(VAL, 'op_tables', 'threshold_table_%s_%s.csv' % (m, mode)))
        assert dv.is_monotonic(t) and (np.diff(t.threshold) <= 0).all()
        A = v['op']['A_equal_signal_efficiency']; L = v['op']['legacy']
        assert abs(A['signal_efficiency'] - L['signal_efficiency']) < 0.01
    j = d['joint']
    assert j['order'] == ['numu', 'other', 'ncpi0', 'nue']
    for ref in ('LEGACY_HISTORICAL', 'DEV_ROC_EQUIVALENT'):
        c = j[ref]['cascade']
        assert [s['after'] for s in c] == j['order']
        assert all(c[k + 1]['ncdr_signal_eff'] <= c[k]['ncdr_signal_eff'] + 1e-12 and c[k + 1]['bnb_bkg_acc'] <= c[k]['bnb_bkg_acc'] + 1e-12 for k in range(3))
    assert sum(j['rows']['ncdr_signal_by_topology'].values()) == j['rows']['ncdr_signal']
    f = pd.read_csv(os.path.join(VAL, 'op_tables', 'joint_pareto_%s.csv' % mode)).sort_values('bnb_bkg_acc')
    assert len(f) == j['pareto_points'] and (np.diff(f.ncdr_signal_eff) > 0).all()     # a front: more signal only for more background
