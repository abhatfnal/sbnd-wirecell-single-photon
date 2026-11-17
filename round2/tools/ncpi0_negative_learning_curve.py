#!/usr/bin/env python3
"""DIAGNOSTIC ONLY: SP ncpi0 test performance versus the number of NC pi0 negative training events.

  python ncpi0_negative_learning_curve.py --tables DIR --tag dev --spec SPEC.yaml --out-json OUT.json [--work-dir DIR]

Question: does the development SP ncpi0 model still gain materially from more NC pi0 negatives at the full aurora-r2
BNB count? If yes, an NC pi0-enriched production is worth asking for; if not, the BNB statistics are adequate.

Fixed (nothing is tuned):
  * the development spec, its xgboost parameters, its feature list and Policy B (kine_pio_flag as stored);
  * the held-out test fold (odd subruns), always complete;
  * ALL positive training rows.
Varied:
  * the fraction f of NEGATIVE training EVENTS kept. Selection is per event (sample, file_id, run, subrun, event):
    u = sha256("<seed>|<event key>") / 2^64, keep the event's negative rows when u < f. Nested in f for a fixed seed.
  * seed s in the seed set, used for the event selection AND as the xgboost seed. Seeds only estimate spread; no
    model is selected. f = 1 with s = the spec seed reproduces the development model exactly (checked).
No model is saved. The development model is not touched. Thresholds are not chosen.

Decision rule, fixed before the run (doubling = f 1/2 -> 1):
  gain = mean test AUC(f = 1) - mean test AUC(f = 1/2); sigma = largest seed std of test AUC at f >= 1/2
  STRONG CASE FOR NCPI0 ENRICHMENT          gain >= 0.020 and gain > 3 sigma
  SOME BENEFIT LIKELY                       gain >= 0.005 and gain > 2 sigma
  CURRENT BNB STATISTICS APPEAR ADEQUATE    otherwise
"""
import argparse
import hashlib
import json
import os
import sys
import time

import numpy as np
import pandas as pd

ROUND2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROUND2)
from sp_retrain import devtrain, firewall, labels  # noqa: E402

ALLOWED_INPUT = ['/lus/flare/projects/neutrinoGPU/yuhw/production-prep/dlspace']
ALLOWED_OUTPUT = ['/lus/flare/projects/neutrinoGPU/abhat/sbnd']
FRACTIONS = (0.125, 0.25, 0.5, 0.75, 1.0)
SEEDS = (1, 2, 3)
DEV_MANIFEST = 'manifests/dev_round1domain_v1/single_photon_ncpi0_dev_manifest.json'   # f = 1, spec seed must reproduce it


def classify(gain, sigma):
    if gain >= 0.020 and gain > 3 * sigma:
        return 'STRONG CASE FOR NCPI0 ENRICHMENT'
    if gain >= 0.005 and gain > 2 * sigma:
        return 'SOME BENEFIT LIKELY'
    return 'CURRENT BNB STATISTICS APPEAR ADEQUATE'


def event_u(keys, seed):
    ev = keys[devtrain.EV].astype(str).agg('|'.join, axis=1)
    return np.array([int.from_bytes(hashlib.sha256(('%d|%s' % (seed, e)).encode()).digest()[:8], 'big') / 2.0 ** 64
                     for e in ev])


def load(a, spec):
    roots = a.allowed_input_root or ALLOWED_INPUT
    stamp = json.load(open(os.path.join(os.path.dirname(ROUND2), spec['samples']['input_manifest'])))['reconstruction']['wct_version_stamp']
    C = []
    for s in spec['samples']['development']:
        sid = s['id']; firewall.check_sample_id(sid)
        b = json.load(open(os.path.join(a.tables, 'build_%s_%s.json' % (sid, a.tag))))
        if b['list_sha256'] != s['list_sha256'] or b['files'] != s['files'] or b.get('slice'):
            raise SystemExit('%s: table build does not match the spec list' % sid)
        F = pd.read_parquet(os.path.join(a.tables, 'files_%s_%s.parquet' % (sid, a.tag)))
        firewall.check_training_inputs(F.path.tolist(), roots)
        off = set(F[F.wct_version.fillna('') != stamp].file_id)
        cs = pd.read_parquet(os.path.join(a.tables, 'cands_%s_%s.parquet' % (sid, a.tag)))
        C.append(cs[~cs.file_id.isin(off)])
    return pd.concat(C, ignore_index=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--tables', required=True); ap.add_argument('--tag', required=True); ap.add_argument('--spec', required=True)
    ap.add_argument('--out-json', required=True); ap.add_argument('--work-dir', default=None)
    ap.add_argument('--dev-manifest', default=DEV_MANIFEST, help='manifest of the model the f = 1 run must reproduce')
    ap.add_argument('--allowed-input-root', action='append', default=None)
    a = ap.parse_args()
    import xgboost as xgb
    from sklearn.metrics import log_loss, roc_auc_score, roc_curve

    spec = labels.load_spec(a.spec)
    devtrain.require_development_spec(spec)
    if spec['classifier']['name'] != 'single_photon_ncpi0':
        raise SystemExit('this diagnostic is for the SP ncpi0 development spec only')
    if a.work_dir:
        firewall.check_output_path(a.work_dir, ALLOWED_OUTPUT); os.makedirs(a.work_dir, exist_ok=True)
    ds = devtrain.build_dataset(load(a, spec), spec)
    names, keys, X, y = ds['names'], ds['keys'], ds['X'], ds['y']
    tr = (keys.split == 'train').to_numpy(); te = ~tr
    params0, rounds = devtrain.xgb_params(spec)
    dte = xgb.DMatrix(X[te], label=y[te], feature_names=names)
    neg_tr = tr & (y == 0); pos_tr = tr & (y == 1)
    neg_events_all = keys[neg_tr][devtrain.EV].drop_duplicates()
    runs = []
    for s in SEEDS:
        u = event_u(keys, s)
        for f in FRACTIONS:
            keep = pos_tr | (neg_tr & (u < f))
            params = dict(params0, seed=s)
            t0 = time.time()
            dtr = xgb.DMatrix(X[keep], label=y[keep], feature_names=names)
            bst = xgb.train(params, dtr, num_boost_round=rounds, verbose_eval=False)
            m_tr = bst.predict(dtr, output_margin=True); m_te = bst.predict(dte, output_margin=True)
            p_te = 1.0 / (1.0 + np.exp(-m_te.astype(np.float64)))
            fpr, tpr, _ = roc_curve(y[te], m_te)
            rej = {str(e): float(1.0 - np.interp(e, tpr, fpr)) for e in (0.5, 0.8)}
            sel = keep & (y == 0)
            runs.append(dict(seed=s, fraction=f, neg_rows=int(sel.sum()),
                             neg_events=int(keys[sel][devtrain.EV].drop_duplicates().shape[0]), pos_rows=int(pos_tr.sum()),
                             train_auc=float(roc_auc_score(y[keep], m_tr)), test_auc=float(roc_auc_score(y[te], m_te)),
                             test_logloss_prior_dependent=float(log_loss(y[te], np.clip(p_te, 1e-15, 1 - 1e-15))),
                             test_bkg_rejection_at_sig_eff=rej, seconds=round(time.time() - t0, 1)))
            print(json.dumps(runs[-1]), flush=True)
    R = pd.DataFrame(runs)
    agg = []
    for f, g in R.groupby('fraction'):
        agg.append(dict(fraction=float(f), neg_rows_mean=float(g.neg_rows.mean()), neg_events_mean=float(g.neg_events.mean()),
                        train_auc_mean=float(g.train_auc.mean()), test_auc_mean=float(g.test_auc.mean()),
                        test_auc_std=float(g.test_auc.std(ddof=1)), test_auc_min=float(g.test_auc.min()), test_auc_max=float(g.test_auc.max()),
                        test_rej_at_eff0p5_mean=float(np.mean([r['0.5'] for r in g.test_bkg_rejection_at_sig_eff])),
                        test_rej_at_eff0p8_mean=float(np.mean([r['0.8'] for r in g.test_bkg_rejection_at_sig_eff])),
                        test_logloss_mean=float(g.test_logloss_prior_dependent.mean())))
    A = pd.DataFrame(agg).set_index('fraction')
    gain = float(A.loc[1.0, 'test_auc_mean'] - A.loc[0.5, 'test_auc_mean'])
    gain_last = float(A.loc[1.0, 'test_auc_mean'] - A.loc[0.75, 'test_auc_mean'])
    sigma = float(A.loc[[0.5, 0.75, 1.0], 'test_auc_std'].max())
    # log-linear slope of test AUC per doubling over f in [1/4, 1]
    sub = A.loc[[0.25, 0.5, 0.75, 1.0]]
    slope = float(np.polyfit(np.log2(sub.neg_rows_mean.to_numpy()), sub.test_auc_mean.to_numpy(), 1)[0])
    ref = R[(R.seed == spec['xgboost']['seed']) & (R.fraction == 1.0)].test_auc.iloc[0]
    dev_auc = json.load(open(os.path.join(ROUND2, a.dev_manifest)))['metrics']['test_auc']
    out = dict(
        label='DIAGNOSTIC_ONLY_NOT_A_MODEL', spec=os.path.relpath(os.path.abspath(a.spec), ROUND2),
        spec_sha256=devtrain.sha256_file(a.spec), tables=os.path.abspath(a.tables), tag=a.tag,
        fixed=dict(xgboost=dict((k, v) for k, v in params0.items() if k != 'seed'), num_boost_round=rounds, policy='B (kine_pio_flag as stored)',
                   positives_train_rows=int(pos_tr.sum()), negatives_train_rows_full=int(neg_tr.sum()),
                   negatives_train_events_full=int(len(neg_events_all)), test_rows=int(te.sum()),
                   test_pos=int((y[te] == 1).sum()), test_neg=int((y[te] == 0).sum())),
        varied=dict(fractions=list(FRACTIONS), seeds=list(SEEDS), selection='per event, sha256(seed|key) < f, nested in f',
                    xgboost_seed='= seed'),
        reproduces_development_model=dict(manifest=a.dev_manifest, test_auc_f1_spec_seed=float(ref), development_manifest_test_auc=float(dev_auc),
                                          abs_diff=float(abs(ref - dev_auc)), match=bool(abs(ref - dev_auc) < 1e-9)),
        per_fraction=agg, runs=runs,
        result=dict(gain_test_auc_half_to_full=gain, gain_test_auc_three_quarter_to_full=gain_last, seed_sigma=sigma,
                    test_auc_slope_per_doubling_f_quarter_to_full=slope,
                    decision_rule='STRONG: gain >= 0.020 and > 3 sigma; SOME: gain >= 0.005 and > 2 sigma; else ADEQUATE',
                    classification=classify(gain, sigma)),
        caveats=['development domain (aurora-r2, Round-1 reconstruction), not the refreshed domain',
                 'test logloss depends on the class prior, which changes with f; AUC and rejection do not',
                 'train AUC is measured on the subsampled training rows'])
    json.dump(out, open(a.out_json, 'w'), indent=1)
    print(json.dumps(out['result'], indent=1))


if __name__ == '__main__':
    main()
