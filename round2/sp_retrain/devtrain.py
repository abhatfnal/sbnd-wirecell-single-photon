"""Development training of the single-photon BDTs: ROUND1_DOMAIN_DEVELOPMENT_DO_NOT_DEPLOY.

Only specs with campaign 'development_round1_domain_v1', deployable false and status READY_FOR_DEVELOPMENT_TRAINING
are accepted. The rows are the classifier's development classes (sp_retrain.labels.development_classes) after the
preselection; the inputs are the stored values of the XML-ordered feature list as float32, with no preprocessing; a row
with any non-finite input is excluded and listed (spec non_finite_policy exclude_row); the split is subrun_parity_v1
(even subrun = train, odd = test). For ncpi0, kine_pio_flag Policy B: the stored value enters training and inference
unchanged. forced_flag_matrix() exists only for the legacy-convention diagnostic and is never used to train.
"""
import hashlib
import json
import os

import numpy as np
import pandas as pd

from sp_retrain import features, labels, split

CAMPAIGN = 'development_round1_domain_v1'
EV = ['sample', 'file_id', 'run', 'subrun', 'event']
ROW_KEY = EV + ['cand']
SOURCE_XGB = ('max_depth', 'n_estimators', 'learning_rate', 'objective', 'colsample_bytree', 'colsample_bylevel',
              'colsample_bynode', 'subsample', 'gamma', 'seed', 'eval_metric')
THESIS_XGB = {  # Yandel thesis appendix E (E.1 p.278-279, E.3 p.281-283)
    'single_photon_numu': dict(max_depth=5, n_estimators=300),
    'single_photon_ncpi0': dict(max_depth=6, n_estimators=400),
}
THESIS_COMMON = dict(learning_rate=0.1, objective='binary:logitraw', colsample_bytree=1, colsample_bylevel=0.5,
                     colsample_bynode=0.5, subsample=0.8, gamma=0.2, seed=1, eval_metric=['auc', 'error'])


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def require_development_spec(spec):
    if spec.get('campaign') != CAMPAIGN or spec.get('deployable') is not False:
        raise labels.TargetBlockedError('%s is not a %s (non-deployable) spec' % (spec.get('spec_id'), CAMPAIGN))
    labels.require_ready(spec, final=False)
    name = spec['classifier']['name']
    if name not in THESIS_XGB:
        raise labels.TargetBlockedError('no development training for %s' % name)
    x = spec['xgboost']
    want = dict(THESIS_COMMON, **THESIS_XGB[name])
    bad = {k: (x.get(k), v) for k, v in want.items() if x.get(k) != v}
    if bad:
        raise ValueError('%s xgboost block differs from the thesis: %s' % (name, bad))
    if 'kine_pio_flag' in features.load(name).columns and spec['inputs'].get('kine_pio_flag_policy') != 'B':
        raise ValueError('%s: kine_pio_flag_policy must be B for development training' % name)
    if spec['split']['scheme'] != split.PARITY_SCHEME:
        raise ValueError('split scheme must be %s' % split.PARITY_SCHEME)


def xgb_params(spec):
    """(params, num_boost_round) for xgboost.train, mapped one-to-one from the spec's xgboost block."""
    x = spec['xgboost']
    params = dict(max_depth=x['max_depth'], eta=x['learning_rate'], objective=x['objective'],
                  colsample_bytree=x['colsample_bytree'], colsample_bylevel=x['colsample_bylevel'],
                  colsample_bynode=x['colsample_bynode'], subsample=x['subsample'], gamma=x['gamma'], seed=x['seed'],
                  eval_metric=list(x['eval_metric']), base_score=x['base_score'], tree_method=x['tree_method'],
                  nthread=x['nthread'])
    return params, int(x['n_estimators'])


def build_dataset(cands, spec):
    """Rows with a class (1 / 0) after preselection. Returns dict(X, y, split, keys, names, nonfinite, counts)."""
    name = spec['classifier']['name']
    names = features.load(name).columns
    cls, pre = labels.development_classes(cands, spec)
    rows = np.flatnonzero(cls >= 0)
    sub = cands.iloc[rows]
    X64 = sub[names].to_numpy(np.float64)          # Policy B: every input, kine_pio_flag included, exactly as stored
    X = X64.astype(np.float32)
    finite = np.isfinite(X64).all(1) & np.isfinite(X).all(1)
    y = cls[rows].astype(np.int8)
    keys = sub[ROW_KEY].reset_index(drop=True)
    bad = []
    for i in np.flatnonzero(~finite):
        cols = [names[j] for j in range(len(names)) if not np.isfinite(X64[i, j]) or not np.isfinite(X[i, j])]
        bad.append(dict(model=name, features=';'.join(cols), cls=int(y[i]), **{k: keys.iloc[i][k] for k in ROW_KEY}))
    keep = np.flatnonzero(finite)
    keys = keys.iloc[keep].reset_index(drop=True)
    sp = split.assign_parity(keys.subrun.to_numpy())
    keys = keys.assign(split=sp, cls=y[keep])
    return dict(X=X[keep], y=y[keep], split=sp, keys=keys, names=names,
                nonfinite=pd.DataFrame(bad, columns=['model', 'features', 'cls'] + ROW_KEY),
                preselected=int(pre.sum()), classed=int(len(rows)))


def forced_flag_matrix(X, names, value=0.0):
    """Copy of X with kine_pio_flag set to `value`: the legacy MicroBooNE scoring convention, for diagnostics only."""
    j = names.index('kine_pio_flag')
    Xf = X.copy()
    Xf[:, j] = value
    return Xf


def auc(y, s):
    """Rank (Mann-Whitney) AUC with average ranks for ties."""
    y = np.asarray(y); s = np.asarray(s, np.float64)
    r = pd.Series(s).rank(method='average').to_numpy()
    npos = int((y == 1).sum()); nneg = int((y == 0).sum())
    return float((r[y == 1].sum() - npos * (npos + 1) / 2) / (npos * nneg))


def error_at(y, margin, cut):
    return float(((margin > cut).astype(int) != np.asarray(y)).mean())


def counts(keys):
    out = {}
    for sp in ('train', 'test'):
        k = keys[keys.split == sp]
        out[sp] = dict(rows=int(len(k)), positive_rows=int((k.cls == 1).sum()), negative_rows=int((k.cls == 0).sum()),
                       events=int(k[EV].drop_duplicates().shape[0]),
                       positive_events=int(k[k.cls == 1][EV].drop_duplicates().shape[0]),
                       negative_events=int(k[k.cls == 0][EV].drop_duplicates().shape[0]),
                       by_sample={s: dict(positive=int(((k['sample'] == s) & (k.cls == 1)).sum()),
                                          negative=int(((k['sample'] == s) & (k.cls == 0)).sum()))
                                  for s in sorted(k['sample'].unique())})
    return out


def leakage_check(keys):
    """Zero (sample, run, subrun, event) and zero file-row overlap between train and test; events never straddle."""
    split.check_event_safe(keys)
    tr = set(map(tuple, keys[keys.split == 'train'][['sample', 'run', 'subrun', 'event']].to_numpy().tolist()))
    te = set(map(tuple, keys[keys.split == 'test'][['sample', 'run', 'subrun', 'event']].to_numpy().tolist()))
    dup_rows = int(keys.duplicated(ROW_KEY).sum())
    nfile = keys.groupby(['sample', 'run', 'subrun', 'event']).file_id.nunique()
    return dict(train_events=len(tr), test_events=len(te), overlapping_events=len(tr & te), duplicate_rows=dup_rows,
                events_in_more_than_one_file=int((nfile > 1).sum()))


def package_versions():
    import sys
    import xgboost
    import sklearn
    return dict(python=sys.version.split()[0], numpy=np.__version__, pandas=pd.__version__, xgboost=xgboost.__version__,
                scikit_learn=sklearn.__version__)
