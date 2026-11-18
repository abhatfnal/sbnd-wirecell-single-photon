#!/usr/bin/env python3
"""Snap vs split-move as a BDT input domain, for one SP model (development holdout only; no training, no threshold).

  python wcl1116_mode_compare.py --model numu --bundle-root LEGACY --tag dev --out-json OUT.json \
      --split-tables DIR --split-spec SPEC --split-model-dir DIR --snap-tables DIR --snap-spec SPEC --snap-model-dir DIR

Per mode: development-holdout rows (+/-), legacy-XML AUC and the development model's AUC on those rows, the train /
holdout gap, top features. Then a FAIR classifier-only comparison on the MATCHED COMMON POPULATION: holdout candidates
present in both modes with the same key (file_id, run, subrun, event, cand), classed identically and scored (finite)
in both. Differences in candidate availability are reported separately (ceilings: tools/wcl1116_migration_study.py)
and never folded into the classifier numbers. Feature sanity: split counts vs the exact legacy XML fingerprint
(Spearman, top-10 overlap, upstream-score share); no bookkeeping identifier is an input.
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

ROUND2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROUND2)
sys.path.insert(0, os.path.join(ROUND2, 'tools'))
from sp_retrain import devtrain, features, labels, legacy_control as lc  # noqa: E402
from legacy_control_compare import load_cands  # noqa: E402

# Retraining verdict (Task 14), FIXED BEFORE the SP nue / SP other fits (2026-11-17 23:5xZ), on identical holdout rows:
#   RETRAINING CLEARLY BENEFICIAL            in BOTH modes: dev - legacy AUC >= 0.010 and > 3 sigma (event bootstrap)
#   LEGACY MODEL REMAINS COMPETITIVE         in BOTH modes: dev - legacy AUC <= 0.002
#   RETRAINING NEUTRAL / NOT RESOLVED        otherwise
VERDICT_RULE = 'BENEFICIAL: both modes gain >= 0.010 and > 3 sigma; COMPETITIVE: both modes gain <= 0.002; else NEUTRAL / NOT RESOLVED'


def verdict(gains):
    """gains: list of (mean, sd) of dev - legacy AUC, one per vertex mode."""
    if all(m >= 0.010 and m > 3 * sd for m, sd in gains):
        return 'RETRAINING CLEARLY BENEFICIAL'
    if all(m <= 0.002 for m, _ in gains):
        return 'LEGACY MODEL REMAINS COMPETITIVE'
    return 'RETRAINING NEUTRAL / NOT RESOLVED'


def boot_gain(hold, roc_auc_score, n=200, seed=20261117):
    rng = np.random.default_rng(seed)
    ev = hold[devtrain.EV].astype(str).agg('|'.join, axis=1).to_numpy()
    uev, inv = np.unique(ev, return_inverse=True)
    g = []
    for _ in range(n):
        w = np.bincount(rng.integers(0, len(uev), len(uev)), minlength=len(uev))[inv]
        s = hold.iloc[np.repeat(np.arange(len(hold)), w)]
        if s.y.nunique() < 2:
            continue
        g.append(roc_auc_score(s.y, s.margin) - roc_auc_score(s.y, s.legacy))
    return float(roc_auc_score(hold.y, hold.margin) - roc_auc_score(hold.y, hold.legacy)), float(np.std(g))


BOOKKEEPING = {'run', 'subrun', 'event', 'cand', 'file_id', 'sample', 'cluster_id', 'nu_index', 'eventNo', 'runNo', 'subRunNo'}
GROUPS = {'single_photon_numu': {'upstream_numu': ('numu_score', 'numu_1_score')},
          'single_photon_ncpi0': {'nue_L1_scores': ('_score',), 'pi0_kinematics': ('kine_pio_',)},
          'single_photon_other': {'upstream_numu': ('numu_score', 'numu_1_score', 'numu_2_score', 'cosmict_10_score'),
                                  'cosmic_tagger': ('cosmict_', 'cosmic_')},
          'single_photon_nue': {'shower_stem_dQdx': ('dQ_dx', 'dedx', 'dqdx', 'stem'), 'conversion_distance': ('vtx_dis', 'shw_dis', 'min_dis')}}


def legacy_splits(forest):
    cnt = np.bincount(forest.ivar[~forest.leaf], minlength=len(forest.names))
    return dict(zip(forest.names, cnt.tolist()))


def mode_block(tables, tag, spec_path, mdir, bundle, xgb, roc_auc_score):
    spec = labels.load_spec(spec_path); devtrain.require_development_spec(spec)
    clf = spec['classifier']['name']; fl = features.load(clf); cols = fl.columns
    C = load_cands(tables, tag, spec, [])
    ds = devtrain.build_dataset(C, spec)
    keys = ds['keys']; X = ds['X']; y = ds['y']
    te = (keys.split == 'test').to_numpy(); tr = ~te
    man = json.load(open(os.path.join(mdir, 'metrics.json')))
    mname = spec['classifier']['model_name']
    bst = xgb.Booster(); bst.load_model(os.path.join(mdir, mname + '.json'))
    m_te = bst.predict(xgb.DMatrix(X[te], feature_names=cols), output_margin=True)
    forest = lc.load_control(bundle, clf, fl.names)
    s_leg = lc.legacy_score(forest, lc.legacy_matrix(X[te], fl.names, clf))[1]
    imp = pd.read_csv(os.path.join(mdir, 'importance.csv'))
    out = dict(model=mname, vertex_mode=spec['reconstruction']['vertex_mode'], wc_tree=spec['reconstruction']['wc_tree'],
               train_rows=dict(pos=int((y[tr] == 1).sum()), neg=int((y[tr] == 0).sum())),
               holdout_rows=dict(pos=int((y[te] == 1).sum()), neg=int((y[te] == 0).sum())),
               train_auc=man['train']['auc'], holdout_auc=float(roc_auc_score(y[te], m_te)), holdout_auc_stored=man['test']['auc'],
               legacy_holdout_auc=float(roc_auc_score(y[te], s_leg)),
               train_holdout_gap=float(man['train']['auc'] - roc_auc_score(y[te], m_te)),
               top10_by_splits=imp.sort_values('weight', ascending=False).feature.head(10).tolist())
    out['holdout_auc_matches_stored'] = abs(out['holdout_auc'] - out['holdout_auc_stored']) < 1e-12
    leg = legacy_splits(forest)
    dev = dict(zip(imp.feature, imp.weight))
    name_of = dict(zip(cols, fl.names))
    a = np.array([dev.get(c, 0.0) for c in cols]); b = np.array([leg[name_of[c]] for c in cols])
    from scipy.stats import spearmanr
    out['feature_sanity'] = dict(
        spearman_split_counts_vs_legacy=float(spearmanr(a, b).correlation),
        top10_overlap_with_legacy=len(set(imp.sort_values('weight', ascending=False).feature.head(10)) &
                                      set(c for c, _ in sorted(zip(cols, b), key=lambda t: -t[1])[:10])),
        bookkeeping_inputs=sorted(set(cols) & BOOKKEEPING),
        group_split_share={g: dict(dev=float(sum(dev.get(c, 0) for c in cols if any(p in c for p in pats)) / max(a.sum(), 1)),
                                   legacy=float(sum(leg[name_of[c]] for c in cols if any(p in c for p in pats)) / max(b.sum(), 1)))
                           for g, pats in GROUPS.get(clf, {}).items()},
        dev_rank={c: int(r) for c, r in zip(imp.feature, imp.rank_weight) if c in sum(GROUPS.get(clf, {}).values(), ()) or c.startswith('kine_pio')})
    hold = keys[te].reset_index(drop=True).assign(margin=m_te, legacy=s_leg, y=y[te])
    gm, gsd = boot_gain(hold, roc_auc_score)
    out['dev_minus_legacy_auc'] = dict(gain=gm, bootstrap_sd=gsd, n_bootstrap=200)
    from scipy.stats import spearmanr as _sp
    out['spearman_dev_vs_legacy'] = float(_sp(m_te, s_leg).correlation)
    return out, hold, clf


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    for k in ('--model', '--bundle-root', '--tag', '--out-json', '--split-tables', '--split-spec', '--split-model-dir',
              '--snap-tables', '--snap-spec', '--snap-model-dir'):
        ap.add_argument(k, required=True)
    a = ap.parse_args()
    import xgboost as xgb
    from sklearn.metrics import roc_auc_score
    lc.verify_bundle(a.bundle_root)
    res = dict(label='DEVELOPMENT HOLDOUT (Aurora WCL1116) -- not independent end-to-end performance; no threshold', model=a.model, modes={})
    H = {}
    for mode in ('split', 'snap'):
        out, hold, clf = mode_block(getattr(a, mode + '_tables'), a.tag, getattr(a, mode + '_spec'), getattr(a, mode + '_model_dir'),
                                    a.bundle_root, xgb, roc_auc_score)
        res['modes'][out['vertex_mode']] = out
        H[mode] = hold
    k = devtrain.ROW_KEY
    m = H['split'].merge(H['snap'], on=k, suffixes=('_split', '_snap'))
    same = m[m.y_split == m.y_snap]
    res['matched_common_population'] = dict(
        definition='holdout candidates present in both modes with the same key, the same class and finite inputs in both',
        rows=int(len(same)), pos=int((same.y_split == 1).sum()), neg=int((same.y_split == 0).sum()),
        class_disagreement_rows=int(len(m) - len(same)),
        only_split_holdout_rows=int(len(H['split']) - len(m)), only_snap_holdout_rows=int(len(H['snap']) - len(m)),
        dev_auc_split=float(roc_auc_score(same.y_split, same.margin_split)), dev_auc_snap=float(roc_auc_score(same.y_split, same.margin_snap)),
        legacy_auc_split=float(roc_auc_score(same.y_split, same.legacy_split)), legacy_auc_snap=float(roc_auc_score(same.y_split, same.legacy_snap)),
        spearman_dev_margin_split_vs_snap=float(same[['margin_split', 'margin_snap']].corr(method='spearman').iloc[0, 1]),
        spearman_legacy_split_vs_snap=float(same[['legacy_split', 'legacy_snap']].corr(method='spearman').iloc[0, 1]))
    # bootstrap spread of the matched AUC differences (event-level resampling, fixed seed): statistical context only
    rng = np.random.default_rng(20261117)
    ev = same[devtrain.EV].astype(str).agg('|'.join, axis=1).to_numpy()
    uev, inv = np.unique(ev, return_inverse=True)
    dd, dl = [], []
    for _ in range(200):
        w = np.bincount(rng.integers(0, len(uev), len(uev)), minlength=len(uev))[inv]
        idx = np.repeat(np.arange(len(same)), w)
        s = same.iloc[idx]
        if s.y_split.nunique() < 2:
            continue
        dd.append(roc_auc_score(s.y_split, s.margin_snap) - roc_auc_score(s.y_split, s.margin_split))
        dl.append(roc_auc_score(s.y_split, s.legacy_snap) - roc_auc_score(s.y_split, s.legacy_split))
    res['matched_common_population']['bootstrap_200_snap_minus_split'] = dict(
        dev_auc_mean=float(np.mean(dd)), dev_auc_std=float(np.std(dd)), legacy_auc_mean=float(np.mean(dl)), legacy_auc_std=float(np.std(dl)))
    res['retraining_verdict'] = dict(rule=VERDICT_RULE, verdict=verdict([(v['dev_minus_legacy_auc']['gain'], v['dev_minus_legacy_auc']['bootstrap_sd'])
                                                                         for v in res['modes'].values()]))
    json.dump(res, open(a.out_json, 'w'), indent=1)
    print(json.dumps({kk: (vv if kk != 'modes' else {mm: {x: vv[mm][x] for x in ('train_rows', 'holdout_rows', 'train_auc', 'holdout_auc', 'legacy_holdout_auc')} for mm in vv})
                      for kk, vv in res.items()}, indent=1, default=str))


if __name__ == '__main__':
    main()
