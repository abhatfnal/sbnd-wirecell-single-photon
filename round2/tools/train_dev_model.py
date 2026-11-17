#!/usr/bin/env python3
"""Train ONE development single-photon BDT (ROUND1_DOMAIN_DEVELOPMENT_DO_NOT_DEPLOY) with the spec's fixed parameters.

  python train_dev_model.py --tables DIR --tag TAG --spec SPEC.yaml --out-dir OUT --manifest-out MANIFEST.json

No hyperparameter search, no early stopping, no threshold choice. The test half (odd subruns) is only predicted after
training. The model is trained a second time with the same spec to check reproducibility. Writes, under OUT (outside
git): the model JSON, its repeat, the non-finite row list, test / train margins, importances, ROC points and
metrics.json; and a compact manifest (hashes, counts, versions) to MANIFEST.json.
"""
import argparse
import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd

ROUND2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROUND2)
from sp_retrain import devtrain, features, firewall, labels  # noqa: E402

ALLOWED_INPUT = ['/lus/flare/projects/neutrinoGPU/yuhw/production-prep/dlspace']
ALLOWED_OUTPUT = ['/lus/flare/projects/neutrinoGPU/abhat/sbnd']
CODE = ['sp_retrain/devtrain.py', 'sp_retrain/labels.py', 'sp_retrain/sp_truth.py', 'sp_retrain/build_tables.py',
        'sp_retrain/split.py', 'sp_retrain/features.py', 'sp_retrain/firewall.py', 'tools/train_dev_model.py']


def git_state():
    head = subprocess.run(['git', '-C', ROUND2, 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(['git', '-C', ROUND2, 'status', '--porcelain', '--', '.'], capture_output=True, text=True).stdout
    return dict(head=head, dirty_paths=[l[3:] for l in dirty.splitlines()])


def train(xgb, params, rounds, X, y, names):
    d = xgb.DMatrix(X, label=y, feature_names=names)
    res = {}
    bst = xgb.train(params, d, num_boost_round=rounds, evals=[(d, 'train')], evals_result=res, verbose_eval=False)
    return bst, res


def leaf_sum(bst, d, n=500):
    """Sum of leaf values per row from the tree dump, to compare with predict(output_margin=True)."""
    trees = bst.trees_to_dataframe()
    lv = trees[trees.Feature == 'Leaf']
    leaves = dict(zip(zip(lv.Tree.astype(int), lv.Node.astype(int)), lv.Gain.astype(float)))
    idx = bst.predict(d, pred_leaf=True)[:n].astype(int)
    return np.array([sum(leaves[(t, int(idx[i, t]))] for t in range(idx.shape[1])) for i in range(idx.shape[0])])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--tables', required=True); ap.add_argument('--tag', required=True); ap.add_argument('--spec', required=True)
    ap.add_argument('--out-dir', required=True); ap.add_argument('--manifest-out', required=True)
    ap.add_argument('--smoke', action='store_true', help='pipeline check on a list slice: allows a sliced build; the list sha must still match')
    a = ap.parse_args()
    import xgboost as xgb
    from sklearn.metrics import roc_auc_score, roc_curve

    spec = labels.load_spec(a.spec)
    devtrain.require_development_spec(spec)
    name = spec['classifier']['name']; model_name = spec['classifier']['model_name']
    firewall.check_output_path(a.out_dir, ALLOWED_OUTPUT)
    os.makedirs(a.out_dir, exist_ok=True)

    # inputs: the spec's samples, full lists, firewall on every file; rows only from files with the manifest's stamp
    stamp = json.load(open(os.path.join(os.path.dirname(ROUND2), spec['samples']['input_manifest'])))['reconstruction']['wct_version_stamp']
    C, builds = [], {}
    for s in spec['samples']['development']:
        sid = s['id']; firewall.check_sample_id(sid)
        p = lambda t: os.path.join(a.tables, '%s_%s_%s.parquet' % (t, sid, a.tag))
        b = json.load(open(os.path.join(a.tables, 'build_%s_%s.json' % (sid, a.tag))))
        if b['list_sha256'] != s['list_sha256'] or (not a.smoke and (b['files'] != s['files'] or b.get('slice'))):
            raise SystemExit('%s: table build does not match the spec list (sha %s, files %s, slice %s)' % (sid, b['list_sha256'], b['files'], b.get('slice')))
        F = pd.read_parquet(p('files'))
        firewall.check_training_inputs(F.path.tolist(), ALLOWED_INPUT)
        builds[sid] = dict(list=b['list'], list_sha256=b['list_sha256'], files=b['files'], errors=b['errors'],
                           events=int(F.events.sum()), wct_versions=sorted(F.wct_version.dropna().unique().tolist()),
                           label_unreadable_files=int((F.label_unreadable > 0).sum()), truth_pf_unreadable_files=int((F.truth_pf_unreadable > 0).sum()),
                           cands_sha256=devtrain.sha256_file(p('cands')), truth_sha256=devtrain.sha256_file(p('truth')),
                           files_sha256=devtrain.sha256_file(p('files')))
        off = set(F[F.wct_version.fillna('') != stamp].file_id)
        cs = pd.read_parquet(p('cands'))
        builds[sid]['files_without_stamp'] = sorted(off)
        builds[sid]['candidates_dropped_without_stamp'] = int(cs.file_id.isin(off).sum())
        C.append(cs[~cs.file_id.isin(off)])
    C = pd.concat(C, ignore_index=True)

    ds = devtrain.build_dataset(C, spec)
    names = ds['names']; keys = ds['keys']; X = ds['X']; y = ds['y']
    ds['nonfinite'].to_csv(os.path.join(a.out_dir, 'nonfinite_rows.csv'), index=False)
    leak = devtrain.leakage_check(keys)
    if leak['overlapping_events'] or leak['duplicate_rows'] or leak['events_in_more_than_one_file']:
        raise SystemExit('leakage check failed: %s' % leak)
    tr = (keys.split == 'train').to_numpy(); te = ~tr

    params, rounds = devtrain.xgb_params(spec)
    bst, evres = train(xgb, params, rounds, X[tr], y[tr], names)
    mpath = os.path.join(a.out_dir, model_name + '.json'); bst.save_model(mpath)
    rep, _ = train(xgb, params, rounds, X[tr], y[tr], names)
    os.makedirs(os.path.join(a.out_dir, 'repeat'), exist_ok=True)
    rpath = os.path.join(a.out_dir, 'repeat', model_name + '.json'); rep.save_model(rpath)

    dtr = xgb.DMatrix(X[tr], label=y[tr], feature_names=names); dte = xgb.DMatrix(X[te], label=y[te], feature_names=names)
    m_tr = bst.predict(dtr, output_margin=True); m_te = bst.predict(dte, output_margin=True)
    p_te_default = bst.predict(dte)
    r_te = rep.predict(dte, output_margin=True)
    ls = leaf_sum(bst, dte)

    met = dict(
        train=dict(auc=devtrain.auc(y[tr], m_tr), auc_sklearn=float(roc_auc_score(y[tr], m_tr)),
                   error_margin_gt_0=devtrain.error_at(y[tr], m_tr, 0.0), error_margin_gt_0p5=devtrain.error_at(y[tr], m_tr, 0.5),
                   xgboost_eval=bst.eval(dtr, 'train')),
        test=dict(auc=devtrain.auc(y[te], m_te), auc_sklearn=float(roc_auc_score(y[te], m_te)),
                  error_margin_gt_0=devtrain.error_at(y[te], m_te, 0.0), error_margin_gt_0p5=devtrain.error_at(y[te], m_te, 0.5),
                  xgboost_eval=bst.eval(dte, 'test'),
                  confusion_margin_gt_0=dict(tp=int(((m_te > 0) & (y[te] == 1)).sum()), fn=int(((m_te <= 0) & (y[te] == 1)).sum()),
                                             fp=int(((m_te > 0) & (y[te] == 0)).sum()), tn=int(((m_te <= 0) & (y[te] == 0)).sum()))),
        train_curve_last=dict((k, float(v[-1])) for k, v in evres['train'].items()),
        score_scale=dict(predict_equals_output_margin=bool(np.array_equal(p_te_default, m_te)),
                         margin_minus_leaf_sum_max_abs=float(np.abs(m_te[:len(ls)] - ls).max()),
                         margin_minus_leaf_sum_mean=float((m_te[:len(ls)] - ls).mean()),
                         base_score_in_model=json.loads(bst.save_config())['learner']['learner_model_param']['base_score']),
        reproducibility=dict(model_sha256=devtrain.sha256_file(mpath), repeat_sha256=devtrain.sha256_file(rpath),
                             identical_json=devtrain.sha256_file(mpath) == devtrain.sha256_file(rpath),
                             max_abs_margin_diff_test=float(np.abs(m_te - r_te).max())),
    )
    # importance
    imp = pd.DataFrame(dict(feature=names))
    for t in ('weight', 'gain', 'total_gain', 'cover'):
        sc = bst.get_score(importance_type=t); imp[t] = [float(sc.get(f, 0.0)) for f in names]
    imp['weight_share'] = imp.weight / imp.weight.sum(); imp['total_gain_share'] = imp.total_gain / imp.total_gain.sum()
    imp['rank_weight'] = imp.weight.rank(ascending=False, method='min').astype(int)
    imp['rank_gain'] = imp.gain.rank(ascending=False, method='min').astype(int)
    imp.to_csv(os.path.join(a.out_dir, 'importance.csv'), index=False)
    met['total_splits'] = int(imp.weight.sum())
    # ROC points and margins (outside git)
    for lab, msk, mm in (('train', tr, m_tr), ('test', te, m_te)):
        fpr, tpr, _ = roc_curve(y[msk], mm)
        np.savez_compressed(os.path.join(a.out_dir, 'roc_%s.npz' % lab), fpr=fpr, tpr=tpr)
        keys[msk].assign(margin=mm).to_parquet(os.path.join(a.out_dir, 'margins_%s.parquet' % lab), index=False)
    # kine_pio_flag diagnostic (legacy convention on the Policy-B model; never used for training)
    if 'kine_pio_flag' in names:
        j = names.index('kine_pio_flag')
        Xte = X[te]; mf = bst.predict(xgb.DMatrix(devtrain.forced_flag_matrix(Xte, names), feature_names=names), output_margin=True)
        d = mf - m_te; nz = Xte[:, j] != 0
        from scipy.stats import spearmanr
        met['kine_pio_flag_diagnostic'] = dict(
            test_rows=int(te.sum()), rows_with_real_flag_nonzero=int(nz.sum()),
            flag_values_test={str(int(v)): int((Xte[:, j] == v).sum()) for v in np.unique(Xte[:, j])},
            delta_margin_all=dict(mean=float(d.mean()), median=float(np.median(d)), q01=float(np.quantile(d, 0.01)), q99=float(np.quantile(d, 0.99))),
            delta_margin_flag_nonzero=dict(mean=float(d[nz].mean()), median=float(np.median(d[nz])), q05=float(np.quantile(d[nz], 0.05)), q95=float(np.quantile(d[nz], 0.95))),
            frac_abs_delta_gt={str(c): float((np.abs(d) > c).mean()) for c in (0.01, 0.1, 0.5, 1.0)},
            frac_abs_delta_gt_flag_nonzero={str(c): float((np.abs(d[nz]) > c).mean()) for c in (0.01, 0.1, 0.5, 1.0)},
            spearman_real_vs_forced=float(spearmanr(m_te, mf).correlation),
            auc_real=float(roc_auc_score(y[te], m_te)), auc_forced0=float(roc_auc_score(y[te], mf)),
            native_diagnostic_point_margin0_decision_changes=int(((m_te > 0) != (mf > 0)).sum()),
            note='margin units; the margin-0 point is a native diagnostic (p = 0.5), not a production threshold')
        np.savez_compressed(os.path.join(a.out_dir, 'kine_pio_flag_diag.npz'), real=m_te, forced0=mf, y=y[te], flag=Xte[:, j])
    met['counts'] = devtrain.counts(keys); met['leakage'] = leak
    met['nonfinite_excluded'] = dict(rows=int(len(ds['nonfinite'])), by_class={str(k): int(v) for k, v in ds['nonfinite'].cls.value_counts().items()},
                                     by_sample={str(k): int(v) for k, v in ds['nonfinite']['sample'].value_counts().items()},
                                     by_feature=ds['nonfinite'].features.str.split(';').explode().value_counts().to_dict() if len(ds['nonfinite']) else {})
    met['preselected_rows'] = ds['preselected']; met['classed_rows'] = ds['classed']
    json.dump(met, open(os.path.join(a.out_dir, 'metrics.json'), 'w'), indent=1, default=str)

    manifest = dict(
        campaign=devtrain.CAMPAIGN + ('-SMOKE' if a.smoke else ''), deployable=False, label='ROUND1_DOMAIN_DEVELOPMENT_DO_NOT_DEPLOY', classifier=name,
        model=dict(name=model_name, path=os.path.abspath(mpath), sha256=met['reproducibility']['model_sha256'], format='xgboost JSON'),
        spec=dict(path=os.path.relpath(os.path.abspath(a.spec), ROUND2), sha256=devtrain.sha256_file(a.spec)),
        feature_list=dict(path=spec['inputs']['feature_list'], sha256=devtrain.sha256_file(os.path.join(os.path.dirname(ROUND2), spec['inputs']['feature_list'])),
                          n=len(names)),
        xgboost_params=params, num_boost_round=rounds, seed=params['seed'],
        inputs=builds, tables_dir=os.path.abspath(a.tables), tag=a.tag,
        code=dict(git=git_state(), sha256={f: devtrain.sha256_file(os.path.join(ROUND2, f)) for f in CODE}),
        packages=devtrain.package_versions(),
        counts=met['counts'], leakage=leak, nonfinite_excluded=met['nonfinite_excluded']['rows'],
        metrics=dict(train_auc=met['train']['auc'], test_auc=met['test']['auc'], train_error=met['train']['error_margin_gt_0'],
                     test_error=met['test']['error_margin_gt_0']),
        reproducibility=met['reproducibility'], outputs_dir=os.path.abspath(a.out_dir))
    os.makedirs(os.path.dirname(os.path.abspath(a.manifest_out)), exist_ok=True)
    json.dump(manifest, open(a.manifest_out, 'w'), indent=1, default=str)
    print(json.dumps(dict(model=model_name, sha256=manifest['model']['sha256'], train_auc=round(met['train']['auc'], 4),
                          test_auc=round(met['test']['auc'], 4), identical_repeat=met['reproducibility']['identical_json'],
                          nonfinite=met['nonfinite_excluded']['rows'], train=met['counts']['train']['rows'], test=met['counts']['test']['rows'])))


if __name__ == '__main__':
    main()
