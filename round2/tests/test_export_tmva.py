"""XGBoost JSON -> TMVA Grad XML exporter (sp_retrain.export_tmva), on a tiny synthetic model. Fast (< 10 s)."""
import hashlib
import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sp_retrain import export_tmva, features, tmva_grad  # noqa: E402

xgb = pytest.importorskip('xgboost')

NAMES = ['n_showers', 'flag_a', 'energy', 'reco_nuvtxY']          # XML expressions
COLUMNS = ['n_showers', 'flag_a', 'energy', 'kine_nu_y_corr']      # model feature names (table columns)


def _data(n=200, seed=3):
    r = np.random.default_rng(seed)
    X = np.stack([r.integers(0, 6, n), r.integers(0, 2, n), r.normal(0, 1, n), np.round(r.normal(0, 50, n), 0)], 1).astype(np.float32)
    y = ((X[:, 0] >= 2) & (X[:, 1] == 1) | (X[:, 2] > 0.8) | (X[:, 3] > 60)).astype(int)
    return X, y


def _train(X, y, base_score=0.0, objective='binary:logitraw'):
    p = dict(objective=objective, base_score=base_score, max_depth=3, eta=0.3, tree_method='hist', seed=1, nthread=1)
    return xgb.train(p, xgb.DMatrix(X, label=y, feature_names=COLUMNS), num_boost_round=8)


def _feature_list(tmp_path):
    cfg = dict(model='toy', n_inputs=4, inputs=[dict(index=i, name=n, table_column=c, caf_branch='wc.T_tagger.' + c, kind='reco')
                                                 for i, (n, c) in enumerate(zip(NAMES, COLUMNS))])
    p = tmp_path / 'toy_inputs_v0.json'
    p.write_text(json.dumps(cfg))
    return features.FeatureList(str(p))


def _export(tmp_path, bst, name='toy', **kw):
    mj = tmp_path / (name + '_src.json')
    bst.save_model(str(mj))
    return export_tmva.export(str(mj), _feature_list(tmp_path), str(tmp_path / 'out'), name, info=dict(SpecId='toy'), **kw)


def test_export_matches_native_margin_and_leaves(tmp_path):
    X, y = _data()
    bst = _train(X, y)
    rec = _export(tmp_path, bst)
    f = tmva_grad.GradForest(rec['paths']['xml'], expected_names=NAMES)
    assert f.ntrees == 8 and f.names == NAMES
    m = bst.predict(xgb.DMatrix(X, feature_names=COLUMNS), output_margin=True).astype(np.float64)
    raw = f.raw(X)
    assert np.abs(raw - m).max() <= 1e-5
    lx, _ = export_tmva.forest_leaves(f, X)
    ln = bst.predict(xgb.DMatrix(X, feature_names=COLUMNS), pred_leaf=True).astype(np.int64).reshape(len(X), -1)
    assert (export_tmva.xml_leaf_to_xgb_node(f, rec['node_order'], lx) == ln).all()
    v = f.evaluate_mva(X)
    assert np.abs(tmva_grad.log10_odds(v) - 2.0 * m / np.log(10.0)).max() <= 1e-5
    txt = open(rec['paths']['xml']).read()
    assert txt.startswith('<MethodSetup Method="BDT::BDT"><Variables NVar="4">')
    assert '<Weights NTrees="8" AnalysisType="1">' in txt and 'Expression="reco_nuvtxY"' in txt
    assert 'Expression="kine_nu_y_corr"' not in txt


def test_routing_identical_at_exact_thresholds(tmp_path):
    X, y = _data()
    bst = _train(X, y)
    rec = _export(tmp_path, bst)
    f = tmva_grad.GradForest(rec['paths']['xml'], expected_names=NAMES)
    splits = sorted({(int(f.ivar[k]), float(f.cut[k])) for k in range(len(f.cut)) if not f.leaf[k]})
    assert splits
    rows = []
    for j, c in splits:
        Z = X[:20].copy()
        Z[:, j] = np.float32(c)
        rows.append(Z)
    Z = np.concatenate(rows)
    lx, eq = export_tmva.forest_leaves(f, Z)
    assert eq > 0                                   # equality actually exercised
    ln = bst.predict(xgb.DMatrix(Z, feature_names=COLUMNS), pred_leaf=True).astype(np.int64).reshape(len(Z), -1)
    assert (export_tmva.xml_leaf_to_xgb_node(f, rec['node_order'], lx) == ln).all()
    m = bst.predict(xgb.DMatrix(Z, feature_names=COLUMNS), output_margin=True)
    assert np.abs(f.raw(Z) - m).max() <= 1e-5


def test_nonzero_base_margin_refused_unless_folded(tmp_path):
    X, y = _data()
    bst = _train(X, y, base_score=0.5)
    with pytest.raises(export_tmva.ExportError):
        _export(tmp_path, bst, name='b05')
    rec = _export(tmp_path, bst, name='b05f', fold_base_margin=True)
    f = tmva_grad.GradForest(rec['paths']['xml'], expected_names=NAMES)
    assert f.ntrees == 9 and rec['base_margin'] == 0.5 and rec['base_margin_folded']
    m = bst.predict(xgb.DMatrix(X, feature_names=COLUMNS), output_margin=True)
    assert np.abs(f.raw(X) - m).max() <= 1e-5
    assert f.info['BaseMarginFoldedAsTree'] == 'true'


def test_wrong_objective_and_names_refused(tmp_path):
    X, y = _data()
    bst = _train(X, y, base_score=0.5, objective='binary:logistic')
    with pytest.raises(export_tmva.ExportError):
        _export(tmp_path, bst, name='logistic')
    good = _train(X, y)
    mj = tmp_path / 'g.json'
    good.save_model(str(mj))
    model = json.load(open(mj))
    with pytest.raises(export_tmva.ExportError):
        export_tmva.to_tmva_xml(model, NAMES, COLUMNS[::-1])      # model names != feature-list columns
    with pytest.raises(export_tmva.ExportError):
        export_tmva.to_tmva_xml(model, ['a<b'] + NAMES[1:], COLUMNS)   # unsafe attribute text


def test_order_guard_and_sidecars(tmp_path):
    X, y = _data()
    rec = _export(tmp_path, _train(X, y))
    with pytest.raises(ValueError):
        tmva_grad.GradForest(rec['paths']['xml'], expected_names=[NAMES[1], NAMES[0]] + NAMES[2:])
    lines = open(rec['paths']['sha256']).read().split('\n')
    got = dict(reversed(l.split('  ')) for l in lines if l)
    for k in ('xml', 'json', 'features'):
        p = rec['paths'][k]
        assert got[os.path.basename(p)] == hashlib.sha256(open(p, 'rb').read()).hexdigest()
    assert rec['sha256']['json'] == rec['source_json_sha256']
    fj = json.load(open(rec['paths']['features']))
    assert [i['xml_name'] for i in fj['inputs']] == NAMES and [i['table_column'] for i in fj['inputs']] == COLUMNS
