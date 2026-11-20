#!/usr/bin/env python3
"""WCL1116 full-development studies on FIT / NESTED VALIDATION (no FermiGrid product; DEVELOPMENT ONLY).

  python wcl1116_full_dev_study.py --model {numu,ncpi0,other,nue} --mode MODE --tables DIR --tag dev \
      --bundle-root LEGACY --out-dir $SP_WORK/wcl1116_full_dev/studies/MODE/MODEL --summary-out validation/X.json

Studies (fixed before any fit; docs/SP_BDT_WCL1116_FULL_DEVELOPMENT_PLAN.md):
  every model   FIT_BASELINE: the frozen development spec (same features, hyperparameters, seed), fitted on FIT only
  nue           weighting: UNWEIGHTED_BASELINE / THESIS_PRIOR_APPROX / BALANCED_STRESS_TEST (sp_retrain.devstudy.WEIGHTINGS)
  ncpi0         negative-statistics learning curve on NESTED VALIDATION (negative FIT events subsampled 1/8, 1/4, 1/2 with
                seeds 1-3; f = 1 is FIT_BASELINE)
  numu, other   group ablations (sp_retrain.devstudy.ablations): DIAGNOSTICS, never candidate models
Model choice and comparisons use NESTED VALIDATION. The EXISTING DEVELOPMENT HOLDOUT is scored as well and reported
separately, after the nested comparison (it is never used to pick anything).
Writes per-row scores (parquet) and FIT_BASELINE boosters under --out-dir, and a compact summary JSON.
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

ROUND2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROUND2); sys.path.insert(0, os.path.join(ROUND2, 'tools'))
from sp_retrain import devstudy as dv, devtrain, features, firewall, labels, legacy_control as lc  # noqa: E402

CLF = {m: 'single_photon_' + m for m in ('numu', 'ncpi0', 'other', 'nue')}
OTHER_COMPONENTS = ('nc_no_pi0', 'dirt', 'out_of_fv_in_tpc', 'cosmic_matched_mc', 'beam_off_ext')
ALLOWED_OUTPUT = ['/lus/flare/projects/neutrinoGPU/abhat/sbnd']


def components(model, C, keys, y, spec):
    R = dv.row_truth(C, keys)
    if model == 'other':
        from sp_other_census import component
        ext = R['sample'].astype(str).isin(labels.ext_sample_ids(spec)).to_numpy()
        return component(R, np.where(y == 1, 1, 0), ext), OTHER_COMPONENTS, R
    comp = np.where(y == 1, 'signal', R.m_sp_bkg.astype(str).to_numpy())
    return comp, tuple(sorted(set(comp[y == 0]))), R


def block(y, s, legacy, cut, comp, comps, fit_auc=None):
    out = dv.roc_pr(y, s)
    op = dv.op_points(y, s, legacy, cut)
    out['op'] = op
    tA = op['A_equal_signal_efficiency']['cut']
    out['components_at_A'] = dv.component_acceptance(comp, np.asarray(s) > tA, comps)
    out['components_legacy'] = dv.component_acceptance(comp, np.asarray(legacy) > cut, comps)
    out['rows'] = dict(pos=int((y == 1).sum()), neg=int((y == 0).sum()))
    if fit_auc is not None:
        out['fit_minus_this_auc'] = fit_auc - out['roc_auc']
    return out


def binom_sd(p, n):
    return float(np.sqrt(max(p * (1 - p), 1e-12) / n)) if n else None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    for k in ('--model', '--mode', '--tables', '--tag', '--bundle-root', '--out-dir', '--summary-out'):
        ap.add_argument(k, required=True)
    a = ap.parse_args()
    import xgboost as xgb
    from scipy.stats import spearmanr
    firewall.check_output_path(a.out_dir, ALLOWED_OUTPUT); os.makedirs(a.out_dir, exist_ok=True)
    spec = labels.load_spec(os.path.join(ROUND2, 'specs', 'single_photon_%s_training_spec_dev_wcl1116_%s.yaml' % (a.model, a.mode)))
    devtrain.require_development_spec(spec)
    clf = CLF[a.model]; cols = features.load(clf).columns
    params, rounds = devtrain.xgb_params(spec)
    C, ds, roles = dv.load_dataset(spec, a.tables, a.tag)
    keys, X, y = ds['keys'], ds['X'], ds['y']
    if set(cols) & dv.BOOKKEEPING:
        raise SystemExit('bookkeeping identifier among the inputs')
    legacy = dv.legacy_scores(a.bundle_root, clf, X, cols)
    cut = lc.LEGACY_CUT[clf]
    comp, comps, R = components(a.model, C, keys, y, spec)
    fit, nval, test = (roles == dv.ROLE_FIT), (roles == dv.ROLE_NVAL), (roles == dv.ROLE_TEST)
    units = dv.nested_unit_table(keys, roles)
    out = dict(label='WCL1116 FULL DEVELOPMENT (FIT / NESTED VALIDATION; existing holdout reported separately) -- DEVELOPMENT ONLY, NOT ROUND2',
               model=clf, mode=a.mode, spec=os.path.relpath(os.path.join(ROUND2, 'specs', 'single_photon_%s_training_spec_dev_wcl1116_%s.yaml' % (a.model, a.mode)), os.path.dirname(ROUND2)),
               nested_rule=dv.NESTED_RULE, nested_fraction=dv.NESTED_VALIDATION_FRACTION,
               rows={r: dict(pos=int(((roles == r) & (y == 1)).sum()), neg=int(((roles == r) & (y == 0)).sum())) for r in (dv.ROLE_FIT, dv.ROLE_NVAL, dv.ROLE_TEST)},
               units={r: int((units.role == r).sum()) for r in (dv.ROLE_FIT, dv.ROLE_NVAL, dv.ROLE_TEST)},
               rows_by_sample={s: {r: int(((keys['sample'] == s).to_numpy() & (roles == r)).sum()) for r in (dv.ROLE_FIT, dv.ROLE_NVAL, dv.ROLE_TEST)}
                               for s in sorted(keys['sample'].astype(str).unique())},
               legacy_cut=cut, variants={})
    ev = keys[devtrain.EV].astype(str).agg('|'.join, axis=1).to_numpy()
    out['leakage'] = dict(events_in_fit_and_nval=int(len(set(ev[fit]) & set(ev[nval]))), events_in_fit_and_test=int(len(set(ev[fit]) & set(ev[test]))),
                          events_in_nval_and_test=int(len(set(ev[nval]) & set(ev[test]))))
    scores = keys[devtrain.ROW_KEY].assign(role=roles, y=y, legacy=legacy, comp=comp)

    def run(name, cols_used, w=None, rows=fit, meta=None):
        idx = [cols.index(c) for c in cols_used]
        bst = dv.fit(xgb, params, rounds, X[rows][:, idx], y[rows], cols_used, None if w is None else w)
        m = dv.margin(xgb, bst, X[:, idx], cols_used)
        fa = dv.roc_pr(y[fit], m[fit])['roc_auc']
        imp = dv.importance(bst, cols_used)
        res = dict(meta or {}, n_inputs=len(cols_used), removed=[c for c in cols if c not in cols_used], fit_auc=fa,
                   nval=block(y[nval], m[nval], legacy[nval], cut, comp[nval], comps, fa),
                   holdout=block(y[test], m[test], legacy[test], cut, comp[test], comps, fa),
                   calibration_nval=dv.calibration(y[nval], m[nval]),
                   top20_splits=imp.sort_values('splits', ascending=False).feature.head(20).tolist(),
                   top20_gain=imp.sort_values('total_gain', ascending=False).feature.head(20).tolist(),
                   gain_share=dict(zip(imp.feature, imp.gain_share.round(6))), splits=dict(zip(imp.feature, imp.splits)))
        scores['m_' + name] = m
        return res, bst, m

    base, bst0, m0 = run('FIT_BASELINE', cols)
    bst0.save_model(os.path.join(a.out_dir, 'FIT_BASELINE_%s_%s.json' % (a.model, a.mode)))
    out['variants']['FIT_BASELINE'] = base
    out['legacy'] = dict(nval=dv.roc_pr(y[nval], legacy[nval]), holdout=dv.roc_pr(y[test], legacy[test]))

    def compare(name, m):
        v = out['variants'][name]
        v['spearman_vs_baseline_nval'] = float(spearmanr(m[nval], m0[nval]).correlation)
        g0, g1 = out['variants']['FIT_BASELINE']['gain_share'], v['gain_share']
        common = [c for c in g1]
        v['gain_share_spearman_vs_baseline'] = float(spearmanr([g0.get(c, 0) for c in common], [g1[c] for c in common]).correlation)
        v['top10_gain_overlap_with_baseline'] = len(set(out['variants']['FIT_BASELINE']['top20_gain'][:10]) & set(v['top20_gain'][:10]))
        # migration near the useful operating point: rows passing the baseline at its point A that fail this variant at its point A
        tb = out['variants']['FIT_BASELINE']['nval']['op']['A_equal_signal_efficiency']['cut']; tv = v['nval']['op']['A_equal_signal_efficiency']['cut']
        pb, pv = m0[nval] > tb, m[nval] > tv
        yy = y[nval]
        v['migration_at_A_nval'] = dict(signal=lc.flips(pb[yy == 1], pv[yy == 1]), background=lc.flips(pb[yy == 0], pv[yy == 0]),
                                        note='both models at their own equal-legacy-signal-efficiency threshold; legacy_* = baseline here')

    if a.model == 'nue':
        out['study'] = 'weighting'
        for name, ratio in dv.WEIGHTINGS.items():
            if ratio is None:
                out['variants'][name] = dict(out['variants']['FIT_BASELINE'], weighting=name, neg_to_pos_total_weight=None)
                scores['m_' + name] = m0
                continue
            w = dv.class_weights(y[fit], ratio)
            res, _, m = run(name, cols, w, meta=dict(weighting=name, neg_to_pos_total_weight=ratio,
                                                     row_weights=dict(pos=float(w[y[fit] == 1][0]), neg=float(w[y[fit] == 0][0]))))
            out['variants'][name] = res; compare(name, m)
    elif a.model in ('numu', 'other'):
        out['study'] = 'ablation (DIAGNOSTIC ONLY; never candidate models)'
        for name, drop in dv.ablations(a.model).items():
            if not drop:
                out['variants'][name] = dict(out['variants']['FIT_BASELINE'], ablation=name)
                scores['m_' + name] = m0
                continue
            used = [c for c in cols if c not in set(drop)]
            res, _, m = run(name, used, meta=dict(ablation=name))
            out['variants'][name] = res; compare(name, m)
        if a.model == 'other':      # EXT has few nested-validation runs: binomial uncertainty, holdout reported beside it
            for name, v in out['variants'].items():
                for part in ('nval', 'holdout'):
                    e = v[part]['components_at_A'].get('beam_off_ext', {})
                    e['binomial_sd'] = binom_sd(e.get('acceptance') or 0.0, e.get('rows', 0))
    elif a.model == 'ncpi0':
        out['study'] = 'negative-statistics learning curve (nested validation)'
        fev = keys[devtrain.EV].astype(str).agg('|'.join, axis=1)
        neg_ev = np.array(sorted(set(fev[fit & (y == 0)])))
        lcurve = []
        for f in (0.125, 0.25, 0.5):
            for seed in (1, 2, 3):
                rng = np.random.default_rng(seed)
                keep = set(rng.choice(neg_ev, size=int(round(f * len(neg_ev))), replace=False))
                rows = fit & ((y == 1) | fev.isin(keep).to_numpy())
                bst = dv.fit(xgb, params, rounds, X[rows], y[rows], cols)
                m = dv.margin(xgb, bst, X[nval], cols)
                lcurve.append(dict(fraction=f, seed=seed, fit_neg_rows=int((rows & (y == 0)).sum()), nval_auc=dv.roc_pr(y[nval], m)['roc_auc']))
        lcurve.append(dict(fraction=1.0, seed=1, fit_neg_rows=int((fit & (y == 0)).sum()), nval_auc=base['nval']['roc_auc']))
        L = pd.DataFrame(lcurve); g = L.groupby('fraction').nval_auc
        out['learning_curve'] = dict(points=lcurve, mean=g.mean().to_dict(), seed_sd=g.std(ddof=1).fillna(0.0).to_dict(),
                                     gain_per_doubling_half_to_full=float(g.mean()[1.0] - g.mean()[0.5]),
                                     seed_sd_at_half=float(g.std(ddof=1)[0.5]))
    json.dump(out, open(a.summary_out, 'w'), indent=1, default=float)
    scores.to_parquet(os.path.join(a.out_dir, 'scores_%s_%s.parquet' % (a.model, a.mode)), index=False)
    units.to_parquet(os.path.join(a.out_dir, 'nested_units_%s_%s.parquet' % (a.model, a.mode)), index=False)
    print(json.dumps({k: out[k] for k in ('model', 'mode', 'rows', 'leakage')}))
    for n, v in out['variants'].items():
        print(' ', n, 'n_in', v['n_inputs'], 'fit %.4f nval %.4f / pr %.4f  holdout %.4f' % (v['fit_auc'], v['nval']['roc_auc'], v['nval']['pr_auc'], v['holdout']['roc_auc']),
              'A bkg %.4f' % v['nval']['op']['A_equal_signal_efficiency']['background_acceptance'])
    print('  legacy nval %.4f holdout %.4f' % (out['legacy']['nval']['roc_auc'], out['legacy']['holdout']['roc_auc']))
    if 'learning_curve' in out:
        print('  learning curve', out['learning_curve']['mean'], 'gain/doubling', out['learning_curve']['gain_per_doubling_half_to_full'])


if __name__ == '__main__':
    main()
