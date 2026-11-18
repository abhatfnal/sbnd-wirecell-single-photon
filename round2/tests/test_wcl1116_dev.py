"""Tests of the WCL1116 development campaign (development_wcl1116_v1). Run: python -m pytest -q round2/tests"""
import copy
import glob
import gzip
import importlib.util
import json
import os
import sys

import numpy as np
import pandas as pd
import pytest
import yaml

ROUND2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROUND2)
sys.path.insert(0, ROUND2)
from sp_retrain import build_tables, devtrain, features, firewall, labels, split  # noqa: E402

MODES = {'dv2_split_move': 'recTreeWireCell', 'dv2_snap': 'recTreeWireCell_dv2snap'}
MAN = os.path.join(ROUND2, 'manifests', 'wcl1116_dev_v1')


def _tool(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROUND2, 'tools', name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _spec(model, mode):
    return yaml.safe_load(open(os.path.join(ROUND2, 'specs', 'single_photon_%s_training_spec_dev_wcl1116_%s.yaml' % (model, mode))))


# ---------------------------------------------------------------- tree selection
def test_tree_name_selection():
    assert set(build_tables.WC_TREES) == set(MODES.values()) and build_tables.WC == 'recTreeWireCell'
    with pytest.raises(ValueError):
        build_tables.extract('/nonexistent.root', 's', 'f', 0, wc_tree='recTreeWireCell_other')
    # the worker passes the tree through and keeps the old 4-tuple behaviour
    r = build_tables._worker(('/nonexistent.root', 's', 'f', 0, 'recTreeWireCell_dv2snap'))
    assert r[0]['error'].startswith('EXC') and r[1] == [] and r[2] == []


def test_split_assignment_is_identical_across_vertex_modes():
    ev = pd.DataFrame(dict(sample='wcl1116-aurora-bnb', file_id='f', run=[1, 1, 2, 2, 3], subrun=[10, 11, 12, 13, 14],
                           event=[1, 2, 3, 4, 5]))
    a = split.assign_parity(ev.subrun.to_numpy())
    b = split.assign_parity(ev.sample(frac=1, random_state=1).sort_index().subrun.to_numpy())   # a second "mode" table
    assert list(a) == list(b) == ['train', 'test', 'train', 'test', 'train']


def test_ext_rows_split_by_run_and_are_other_negatives():
    spec = dict(spec_id='t', status='READY_FOR_DEVELOPMENT_TRAINING', classifier=dict(name='single_photon_other'),
                label=dict(definition=dict(implementation='x')),
                samples=dict(development=[dict(id='wcl1116-aurora-bnb'), dict(id='beamoff-train-x', role='ext_beam_off')]))
    c = pd.DataFrame(dict(sample=['wcl1116-aurora-bnb'] * 4 + ['beamoff-train-x'] * 2, is_placeholder=0, shw_sp_n_20mev_showers=1,
                          label_unreadable=[0, 0, 0, 0, 1, 1], partner_kind=['neutrino', 'neutrino', 'cosmic', 'neutrino', 'none', 'none'],
                          m_sp_truth_ok=[1, 1, np.nan, 1, np.nan, np.nan], m_sp_signal=[1, 0, np.nan, 0, np.nan, np.nan],
                          m_sp_bkg=['', 'NCBkg', '', 'NCpi0Bkg', '', '']))
    cls, pre = labels.development_classes(c, spec)
    assert list(cls) == [1, 0, 0, -1, 0, 0] and pre.all()
    nspec = dict(spec, classifier=dict(name='single_photon_ncpi0'))
    with pytest.raises(labels.TargetBlockedError):
        labels.development_classes(c, nspec)


# ---------------------------------------------------------------- beam-off training half
def test_beamoff_membership_holdout_removal_and_no_even_runs():
    mk = _tool('make_beamoff_train_membership')
    rows = [dict(file_id='data_filtered_decoded_reco1-%04d' % i, run=str(r), subrun='1', events='50', holdout=str(h),
                 holdout_file='0', holdout_events=str(e)) for i, (r, h, e) in enumerate([(1, 0, 0), (3, 1, 0), (5, 0, 2), (7, 0, 0)])]
    m = mk.membership(rows)
    assert m['pairs'] == 4 and m['holdout_files'] == 2 and m['kept'] == 2 and m['all_runs_odd']
    m2 = mk.membership(rows + [dict(rows[0], file_id='data_filtered_decoded_reco1-9999', run='8')])
    assert not m2['all_runs_odd'] and m2['even_runs'] == [8]
    j = json.load(open(os.path.join(MAN, 'beamoff_train_membership.json')))
    assert j['source_list_sha256'] == mk.FROZEN_SHA256 and (j['pairs'], j['holdout_files_removed'], j['kept']) == (572, 14, 558)
    assert j['all_runs_odd'] and j['even_runs'] == [] and j['overlap_with_even_run_evaluation_half'] == 0
    assert j['firewall_exception']['approved_by'] == 'Avinay Bhat' and 'even-run' in ' '.join(j['firewall_exception']['not_permitted'])
    with gzip.open(os.path.join(MAN, 'beamoff_train_membership.tsv.gz'), 'rt') as f:
        t = pd.read_csv(f, sep='\t')
    assert len(t) == 558 and t.file_id.is_unique and (t.run % 2 == 1).all() and (t.role == 'training_ext_beam_off').all()


# ---------------------------------------------------------------- specs, manifests, provenance, export (campaign outputs)
@pytest.mark.parametrize('model', ['numu', 'ncpi0', 'other'])
def test_vertex_mode_specs_differ_only_in_reconstruction(model):
    a, b = _spec(model, 'dv2_split_move'), _spec(model, 'dv2_snap')
    assert a['campaign'] == b['campaign'] == devtrain.CAMPAIGN_WCL1116 and a['deployable'] is False is b['deployable']
    for s, mode in ((a, 'dv2_split_move'), (b, 'dv2_snap')):
        assert s['reconstruction']['vertex_mode'] == mode and s['reconstruction']['wc_tree'] == MODES[mode]
        assert mode in s['classifier']['model_name'] and s['classifier']['model_name'].endswith('DEV_DO_NOT_DEPLOY')
        assert s['reconstruction']['dl_bundle_sha256'].startswith('51588842') and s['reconstruction']['toolkit_commit'].startswith('c935e30d')
    strip = lambda s: {k: v for k, v in s.items() if k not in ('reconstruction', 'spec_version', 'classifier', 'round2_domain_differences')}
    assert strip(a) == strip(b)
    ca, cb = dict(a['classifier']), dict(b['classifier'])
    ca.pop('model_name'); cb.pop('model_name')
    assert ca == cb
    if model in ('numu', 'other'):
        assert a['inputs']['upstream_numu'] == 'SHIPPED_CONTROL'


@pytest.mark.parametrize('model', ['numu', 'ncpi0'])
def test_wcl1116_specs_keep_the_round1_training_definition(model):
    old = yaml.safe_load(open(os.path.join(ROUND2, 'specs', 'single_photon_%s_training_spec_dev_round1_domain_v1.yaml' % model)))
    new = _spec(model, 'dv2_split_move')
    for k in ('xgboost', 'preselection', 'weights', 'label'):
        assert new[k] == old[k], k
    assert new['split']['scheme'] == old['split']['scheme'] == split.PARITY_SCHEME
    assert {k: v for k, v in new['inputs'].items() if k not in ('upstream_numu', 'upstream_scores')} == \
           {k: v for k, v in old['inputs'].items() if k not in ('upstream_scores',)}
    devtrain.require_development_spec(new)


def test_other_spec_is_blocked_on_transfer_with_a_narrow_exception():
    for mode in MODES:
        s = _spec('other', mode)
        assert s['status'] == 'BLOCKED_TRANSFER_EXECUTION' and 'BLOCKED ONLY ON TRANSFER EXECUTION' in s['status_reason']
        with pytest.raises(labels.TargetBlockedError):
            labels.require_ready(s)
        ext = [d for d in s['samples']['development'] if d.get('role') == labels.EXT_ROLE]
        assert [d['id'] for d in ext] == ['wcl1116-fg-beamoff-train'] and ext[0]['list'] is None
        e = s['samples']['approved_exceptions']
        assert len(e) == 1 and e[0]['approved_by'] == 'Avinay Bhat' and e[0]['scope'].startswith('development_wcl1116_v1 only')
        assert (s['xgboost']['max_depth'], s['xgboost']['n_estimators'], s['xgboost']['base_score']) == (5, 215, 0.0)


def test_training_manifests_carry_no_evaluation_path():
    inp = json.load(open(os.path.join(MAN, 'inputs.json')))
    assert inp['campaign'] == devtrain.CAMPAIGN_WCL1116 and inp['reconstruction']['wct_version_stamp'] == '0.38.0'
    ids = [s['id'] for s in inp['samples']]
    assert ids == ['wcl1116-aurora-ncdr', 'wcl1116-aurora-bnb']
    for s in inp['samples']:
        firewall.check_sample_id(s['id'])
        assert s['excluded'] == [] or all(e['status'] != 'OK' for e in s['excluded'])
        with gzip.open(os.path.join(REPO, s['file_manifest']), 'rt') as f:
            t = pd.read_csv(f, sep='\t')
        assert len(t) == s['files'] and (t['sample'] == s['id']).all() and (t.role == 'training').all()
        assert (t.status == 'OK').all() and (t.validate_split == 1).all() and (t.validate_snap == 1).all()
        assert (t.trees == 'recTreeWireCell,recTreeWireCell_dv2snap').all() and t.unit.is_unique
        assert all(firewall.official_marker(p) is None for p in t.path)
        assert firewall.check_training_inputs(t.path.tolist(), ['/lus/flare/projects/neutrinoGPU/yuhw/production-prep/WCLocal2026Nov16/full']) == len(t)
    bnb = inp['samples'][1]
    assert bnb['units_PARTIAL'] == 14 and bnb['excluded_units'] == 14 and bnb['files'] == bnb['units_OK']


@pytest.mark.parametrize('model', ['numu', 'ncpi0'])
@pytest.mark.parametrize('mode', list(MODES))
def test_wcl1116_model_provenance_and_feature_order(model, mode):
    p = os.path.join(MAN, 'single_photon_%s_%s_dev_manifest.json' % (model, mode))
    m = json.load(open(p))
    sp = _spec(model, mode)
    assert m['deployable'] is False and m['label'] == 'WCL1116_DEVELOPMENT_DO_NOT_DEPLOY' and m['campaign'] == devtrain.CAMPAIGN_WCL1116
    assert m['reconstruction']['vertex_mode'] == mode and m['reconstruction']['wc_tree'] == MODES[mode]
    assert m['model']['name'] == sp['classifier']['model_name'] and len(m['model']['sha256']) == 64
    assert m['spec']['sha256'] == devtrain.sha256_file(os.path.join(ROUND2, m['spec']['path']))
    assert m['feature_list']['sha256'] == sp['inputs']['feature_list_sha256'] and m['feature_list']['n'] == len(features.load('single_photon_' + model).columns)
    assert m['seed'] == 1 and m['xgboost_params']['base_score'] == 0.0 and m['packages']['xgboost'] == '3.4.1'
    assert m['leakage']['overlapping_events'] == 0 and m['leakage']['duplicate_rows'] == 0 and m['leakage']['events_in_more_than_one_file'] == 0
    assert m['reproducibility']['identical_json'] and m['upstream_numu'] == sp['inputs']['upstream_numu']
    assert m['holdout_kind'].startswith('DEVELOPMENT HOLDOUT')
    for s in m['inputs'].values():
        assert s['wct_versions'] == ['0.38.0'] or s['wct_versions'] == ['', '0.38.0']


@pytest.mark.parametrize('mode', list(MODES))
def test_wcl1116_export_equivalence(mode):
    e = json.load(open(os.path.join(ROUND2, 'validation', 'wcl1116_export_equivalence_%s.json' % mode)))
    assert e['all_pass'] and mode in e['label']
    for clf, r in e['models'].items():
        assert r['equivalence']['exporter_exactness_max_abs_xml_raw_minus_double_native_leaf_sum'] == 0.0
        assert r['equivalence']['tree_leaf_mismatches'] == 0 and all(t['flips_score'] == 0 for t in r['thresholds'])
        assert r['order_guard']['refused_by_GradForest']
        man = json.load(open(os.path.join(MAN, 'single_photon_%s_%s_dev_manifest.json' % (clf.split('_')[-1], mode))))
        assert r['model_sha256'] == man['model']['sha256']


def test_cpp_equivalence_if_run():
    for p in glob.glob(os.path.join(ROUND2, 'validation', 'cpp_export_equivalence_*.json')):
        r = json.load(open(p))
        assert r['all_pass'], p
        assert r['reader_equals_forest_bitwise'] == r['rows_compared'] and r['swapped_names_refused']


# ---------------------------------------------------------------- SP other / SP nue campaign (2026-11-18)
def test_spec_scoped_firewall_exceptions():
    spec = dict(samples=dict(approved_exceptions=[
        dict(sample='wcl1116-fg-beamoff-train', approved_by='Avinay Bhat', path_prefix='/pnfs/x/beam-off/', path_prefixes=['/lus/stage/']),
        dict(sample='wcl1116-fg-cv', path_prefix='/pnfs/x/mc-cv/')]))           # no approved_by -> ignored
    ids, pre = firewall.spec_exceptions(spec)
    assert ids == ('wcl1116-fg-beamoff-train',) and pre == ('/pnfs/x/beam-off/', '/lus/stage/')
    with pytest.raises(firewall.FirewallError):
        firewall.check_sample_id('wcl1116-fg-beamoff-train')
    firewall.check_sample_id('wcl1116-fg-beamoff-train', approved_exceptions=ids)
    with pytest.raises(firewall.FirewallError):
        firewall.check_sample_id('wcl1116-fg-cv', approved_exceptions=ids)
    with pytest.raises(firewall.FirewallError):
        firewall.check_training_inputs(['/pnfs/x/mc-cv/a.root'], ['/pnfs/x'], approved_exceptions=pre)
    assert firewall.check_training_inputs(['/lus/stage/data_filtered_decoded_reco1-1/a.root'], ['/lus'], approved_exceptions=pre) == 1


def test_staging_verifier_pieces_and_old_fg1_rejection(tmp_path):
    v = _tool('verify_staged_beamoff')
    m = v.RUN.search('reco2_data_EventBuilder5_p2_art1_run18459_7_strmOffBeamLight_x.wc.flat.caf.root')
    assert m and int(m.group(1)) == 18459
    p = tmp_path / 'f.bin'; p.write_bytes(b'abc' * 1000)
    import zlib, hashlib
    ad, sha = v.checksums(str(p))
    assert ad == '%08x' % (zlib.adler32(b'abc' * 1000) & 0xffffffff) and sha == hashlib.sha256(b'abc' * 1000).hexdigest()
    st = json.load(open(os.path.join(ROUND2, 'validation', 'beamoff_staging_verifier_selftest_old_fg1.json')))
    assert st['status'] == 'NOT VERIFIED' and st['expect_reco'] == 'wcl1116'
    assert st['reco_failures'] == st['staged_files'] == 6 and st['checksum_failures'] == 0
    assert st['evaluation_half_files'] == st['holdout_files'] == st['unknown_files'] == st['duplicate_ids'] == 0
    assert all('not WCL1116' in f['fails'] for f in st['failures'])


def test_sp_other_census_composition():
    c = json.load(open(os.path.join(ROUND2, 'validation', 'sp_other_census_wcl1116_mc_only.json')))
    for mode in MODES:
        r = c['modes'][mode]
        comp = r['negative_by_component']
        assert sum(v['rows'] for v in comp.values()) == r['negative']['rows']
        assert r['negative']['rows'] == r['negative']['train'] + r['negative']['holdout']
        assert r['nonfinite_classed_rows'] == 0 and r['mc_only'] and r['samples_missing'] == ['wcl1116-fg-beamoff-train']
        assert comp['beam_off_ext']['rows'] == 0 and r['beam_off_fraction_of_negatives'] == 0
        numu = json.load(open(os.path.join(MAN, 'single_photon_numu_%s_dev_manifest.json' % mode)))
        assert (r['positive']['train'], r['positive']['holdout']) == (numu['counts']['train']['positive_rows'], numu['counts']['test']['positive_rows'])


def test_nue_spec_source_consistency():
    from sp_retrain import legacy_control as lc
    a, b = _spec('nue', 'dv2_split_move'), _spec('nue', 'dv2_snap')
    for s in (a, b):
        x = s['xgboost']
        assert (x['max_depth'], x['n_estimators'], x['learning_rate'], x['objective'], x['subsample'], x['gamma'], x['seed'], x['base_score']) == \
               (5, 300, 0.1, 'binary:logitraw', 0.8, 0.2, 1, 0.0)
        assert (x['colsample_bytree'], x['colsample_bylevel'], x['colsample_bynode']) == (1, 0.5, 0.5)
        assert s['inputs']['n_inputs'] == 56 == len(features.load('single_photon_nue').columns)
        assert s['inputs']['feature_list_sha256'] == devtrain.sha256_file(os.path.join(REPO, s['inputs']['feature_list']))
        lg = s['classifier']['legacy_control']
        assert lg['sha256'] == lc.XML['single_photon_nue'][1] and (lg['trees'], lg['depth'], lg['inputs']) == (300, 5, 56)
        assert lg['historical_cut_log10_odds'] == lc.LEGACY_CUT['single_photon_nue'] == -1.0
        assert 'nueCCBkg' in s['label']['definition']['negative'] and s['deployable'] is False
        assert s['status'] in ('READY_FOR_DEVELOPMENT_TRAINING', 'WAITING_FOR_NUECC_PRODUCTION')
        ids = [d['id'] for d in s['samples']['development']]
        assert ids[:2] == ['wcl1116-aurora-ncdr', 'wcl1116-aurora-bnb']
        assert (s['status'] == 'READY_FOR_DEVELOPMENT_TRAINING') == ('wcl1116-aurora-nuecc' in ids)
    assert labels.NEGATIVE_BKG['single_photon_nue'] == ('nueCCBkg',)
    assert devtrain.THESIS_XGB['single_photon_nue'] == dict(max_depth=5, n_estimators=300)
    strip = lambda s: {k: v for k, v in s.items() if k not in ('reconstruction', 'spec_version', 'classifier', 'round2_domain_differences')}
    assert strip(a) == strip(b)


def test_legacy_nue_control_is_the_300_tree_production_xml():
    from sp_retrain import legacy_control as lc
    root = '/lus/flare/projects/neutrinoGPU/abhat/sbnd/sp-bdt-round2-work-20261117/legacy_bdt_controls'
    if not os.path.isdir(root):
        pytest.skip('legacy bundle not on this machine')
    f = lc.load_control(root, 'single_photon_nue', features.load('single_photon_nue').names)
    assert (len(f.names), f.ntrees, lc.max_depth(f)) == (56, 300, 5)


@pytest.mark.parametrize('mode', list(MODES))
def test_nue_model_provenance_and_export_if_trained(mode):
    p = os.path.join(MAN, 'single_photon_nue_%s_dev_manifest.json' % mode)
    if not os.path.exists(p):
        pytest.skip('SP nue not trained (nuecc production incomplete)')
    m = json.load(open(p))
    assert m['model']['name'] == 'single_photon_nue_sbnd_wcl1116_%s_DEV_DO_NOT_DEPLOY' % mode and m['reconstruction']['wc_tree'] == MODES[mode]
    assert m['xgboost_params']['base_score'] == 0.0 and m['num_boost_round'] == 300 and m['xgboost_params']['max_depth'] == 5
    assert m['leakage']['overlapping_events'] == 0 and m['reproducibility']['identical_json']
    e = json.load(open(os.path.join(ROUND2, 'validation', 'wcl1116_export_equivalence_nue_%s.json' % mode)))
    assert e['all_pass'] and e['models']['single_photon_nue']['model_sha256'] == m['model']['sha256']


def test_nue_inputs_census_and_manifests_agree():
    p = os.path.join(ROUND2, 'validation', 'sp_nue_census_wcl1116.json')
    if not os.path.exists(os.path.join(MAN, 'single_photon_nue_dv2_split_move_dev_manifest.json')):
        pytest.skip('SP nue not trained')
    nue = [s for s in json.load(open(os.path.join(MAN, 'inputs_nue.json')))['samples'] if s['id'] == 'wcl1116-aurora-nuecc']
    assert len(nue) == 1
    s = nue[0]
    # the whole completed production under the fixed rule: every unit final, only PARTIAL / FAIL units excluded
    assert s['units_listed'] == s['files'] + s['excluded_units'] and s['files'] == s['units_OK']
    assert all(x['status'] == 'PARTIAL' or x['status'].startswith('FAIL') for x in s['excluded'])
    for mode in MODES:
        sp = _spec('nue', mode)
        assert sp['status'] == 'READY_FOR_DEVELOPMENT_TRAINING'
        assert [d for d in sp['samples']['development'] if d['id'] == 'wcl1116-aurora-nuecc'][0]['list_sha256'] == s['list_sha256']
        m = json.load(open(os.path.join(MAN, 'single_photon_nue_%s_dev_manifest.json' % mode)))
        assert m['inputs']['wcl1116-aurora-nuecc']['list_sha256'] == s['list_sha256'] and m['inputs']['wcl1116-aurora-nuecc']['files'] == s['files']
        c = json.load(open(p))['modes'][mode]
        assert c['nonfinite_classed_rows'] == 0
        for half, k in (('train', 'train'), ('test', 'holdout')):
            assert m['counts'][half]['positive_rows'] == c['positive'][k]
            assert m['counts'][half]['negative_rows'] == c['negative'][k]
        # the shared signal sample: SP numu development positives + the nu_e CC-sample signal rows
        mu = json.load(open(os.path.join(MAN, 'single_photon_numu_%s_dev_manifest.json' % mode)))
        assert m['counts']['train']['positive_rows'] == mu['counts']['train']['positive_rows'] + c['per_sample']['wcl1116-aurora-nuecc']['positive']['train']
    v = json.load(open(os.path.join(ROUND2, 'validation', 'wcl1116_mode_compare_nue.json')))
    assert v['retraining_verdict']['verdict'] == _tool('wcl1116_mode_compare').verdict(
        [(v['modes'][md]['dev_minus_legacy_auc']['gain'], v['modes'][md]['dev_minus_legacy_auc']['bootstrap_sd']) for md in MODES])
