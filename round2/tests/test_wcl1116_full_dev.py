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
