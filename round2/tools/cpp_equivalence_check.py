#!/usr/bin/env python3
"""C++ side of the exporter equivalence (TMVA::Reader + toolkit TmvaGradForest vs Python), development fixtures only.

  prepare:  python cpp_equivalence_check.py prepare --xml M.xml --model-json M.json --tables DIR --tag dev --spec SPEC.yaml \
                --work DIR [--rows 3000]
  compare:  python cpp_equivalence_check.py compare --xml M.xml --model-json M.json --work DIR --summary-out S.json

prepare writes, under --work: names.txt (XML variable order), rows.csv (%.9g, exact for float32) and rows_meta.json.
The rows are up to --rows development-holdout rows rebuilt from the tables and spec exactly as in training
(sp_retrain.devtrain.build_dataset), plus rows forced onto exact split thresholds of sampled nodes (equality routing),
5 rows with a NaN input and 5 with +-FLT_MAX. The C++ program round2/cpp/sp_export_regression.cxx (built and run in the
SL7 container on a compute node) writes out.csv. compare checks, per row:
  reader == forest (bitwise), |reader - python GradForest.evaluate_mva| and |forest - python|, |atanh-consistent
  margin - native XGBoost margin| <= 1e-5 max(1, |m|), NaN rows -> -999 in both readers, the swapped-order refusal,
  and zero decision flips of the log10-odds at the fixture cut and score-quantile midpoints.
"""
import argparse
import json
import math
import os
import sys

import numpy as np

ROUND2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROUND2)
sys.path.insert(0, os.path.join(ROUND2, 'tools'))
from sp_retrain import devtrain, features, labels, tmva_grad  # noqa: E402

FIXTURE_CUT = {'single_photon_numu': 0.4, 'single_photon_ncpi0': -0.05, 'single_photon_other': 0.2, 'single_photon_nue': -1.0}
SEED = 20261117


def prepare(a):
    from legacy_control_compare import load_cands
    spec = labels.load_spec(a.spec)
    clf = spec['classifier']['name']; fl = features.load(clf)
    ds = devtrain.build_dataset(load_cands(a.tables, a.tag, spec, []), spec)
    te = (ds['keys'].split == 'test').to_numpy()
    X = ds['X'][te]
    rng = np.random.default_rng(SEED)
    take = np.sort(rng.choice(len(X), size=min(a.rows, len(X)), replace=False))
    rows = [X[take]]
    forest = tmva_grad.GradForest(a.xml, expected_names=fl.names)
    inner = np.flatnonzero(~forest.leaf)
    nodes = rng.choice(inner, size=min(300, len(inner)), replace=False)
    eq = X[rng.choice(len(X), size=len(nodes))].copy()
    eq[np.arange(len(nodes)), forest.ivar[nodes]] = forest.cut[nodes]
    rows.append(eq)
    nan = X[rng.choice(len(X), size=5)].copy(); nan[np.arange(5), rng.choice(X.shape[1], size=5)] = np.nan
    ext = X[rng.choice(len(X), size=5)].copy(); ext[np.arange(5), rng.choice(X.shape[1], size=5)] = np.float32(3.4028235e38) * np.array([1, -1, 1, -1, 1], np.float32)
    rows += [nan, ext]
    R = np.vstack(rows).astype(np.float32)
    os.makedirs(a.work, exist_ok=True)
    open(os.path.join(a.work, 'names.txt'), 'w').write('\n'.join(fl.names) + '\n')
    with open(os.path.join(a.work, 'rows.csv'), 'w') as f:
        for r in R:
            f.write(','.join('nan' if not np.isfinite(v) and np.isnan(v) else '%.9g' % v for v in r) + '\n')
    meta = dict(classifier=clf, xml=os.path.abspath(a.xml), xml_sha256=devtrain.sha256_file(a.xml), model_json=os.path.abspath(a.model_json),
                spec=os.path.abspath(a.spec), rows=dict(holdout=int(len(take)), equality=int(len(nodes)), nan=5, extreme=5, total=int(len(R))))
    json.dump(meta, open(os.path.join(a.work, 'rows_meta.json'), 'w'), indent=1)
    print(json.dumps(meta))


def read_rows(work, nvar):
    R = []
    for line in open(os.path.join(work, 'rows.csv')):
        R.append([float(t) for t in line.strip().split(',')])
    R = np.array(R, np.float32)
    assert R.shape[1] == nvar
    return R


def compare(a):
    import xgboost as xgb
    meta = json.load(open(os.path.join(a.work, 'rows_meta.json')))
    names = [l.strip() for l in open(os.path.join(a.work, 'names.txt')) if l.strip()]
    R = read_rows(a.work, len(names))
    out = np.genfromtxt(os.path.join(a.work, 'out.csv'), delimiter=',', names=True)
    reader, forest_c = out['reader'].astype(np.float64), out['forest'].astype(np.float64)
    log = open(os.path.join(a.work, 'run.log')).read() if os.path.exists(os.path.join(a.work, 'run.log')) else ''
    py = tmva_grad.GradForest(a.xml, expected_names=names)
    v_py = py.evaluate_mva(R); raw_py = py.raw(R)
    fl = features.load(meta['classifier'])
    bst = xgb.Booster(); bst.load_model(a.model_json)
    m = bst.predict(xgb.DMatrix(R, feature_names=fl.columns), output_margin=True).astype(np.float64)
    n = meta['rows']; nh = n['holdout']; ne = n['equality']; idx_nan = slice(nh + ne, nh + ne + 5)
    fin = np.ones(len(R), bool); fin[idx_nan] = False
    K = 2.0 / math.log(10.0)
    s_c = tmva_grad.log10_odds(forest_c); s_n = K * m
    u = np.unique(s_n[:nh])
    cuts = [('fixture_cut', FIXTURE_CUT[meta['classifier']])] + [
        ('quantile_%g_midpoint' % q, float(0.5 * (u[int(q * (len(u) - 1))] + u[int(q * (len(u) - 1)) + 1]))) for q in (0.05, 0.25, 0.5, 0.75, 0.95)]
    res = dict(label='DEVELOPMENT FIXTURE -- C++ EXPORTER EQUIVALENCE (not deployable, not a cut)', **meta,
               rows_compared=int(len(R)),
               reader_equals_forest_bitwise=int((reader == forest_c).sum()),
               reader_vs_python_max_abs=float(np.abs(reader[fin] - v_py[fin]).max()),
               forest_vs_python_max_abs=float(np.abs(forest_c[fin] - v_py[fin]).max()),
               forest_equals_python_bitwise=int((forest_c[fin] == v_py[fin]).sum()), finite_rows=int(fin.sum()),
               tanh_native_vs_forest_max_abs=float(np.abs(np.tanh(m[fin]) - forest_c[fin]).max()),
               raw_python_vs_native_margin_rows_beyond_1em5_rel=int((np.abs(raw_py[fin] - m[fin]) > 1e-5 * np.maximum(1, np.abs(m[fin]))).sum()),
               nan_rows_reader=[float(x) for x in reader[idx_nan]], nan_rows_forest=[float(x) for x in forest_c[idx_nan]],
               swapped_names_refused='swapped_names_refused=1' in log,
               flips=[dict(name=k, cut=c, flips=int(((s_c[:nh] > c) != (s_n[:nh] > c)).sum())) for k, c in cuts])
    res['all_pass'] = bool(res['reader_equals_forest_bitwise'] == len(R) and res['forest_vs_python_max_abs'] < 1e-12
                           and res['raw_python_vs_native_margin_rows_beyond_1em5_rel'] == 0
                           and all(x == -999.0 for x in res['nan_rows_reader'] + res['nan_rows_forest'])
                           and res['swapped_names_refused'] and all(f['flips'] == 0 for f in res['flips']))
    json.dump(res, open(a.summary_out, 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k not in ('flips',)}, indent=1), res['flips'])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('prepare')
    for k in ('--xml', '--model-json', '--tables', '--tag', '--spec', '--work'):
        p.add_argument(k, required=True)
    p.add_argument('--rows', type=int, default=3000)
    c = sub.add_parser('compare')
    for k in ('--xml', '--model-json', '--work', '--summary-out'):
        c.add_argument(k, required=True)
    a = ap.parse_args()
    prepare(a) if a.cmd == 'prepare' else compare(a)


if __name__ == '__main__':
    main()
