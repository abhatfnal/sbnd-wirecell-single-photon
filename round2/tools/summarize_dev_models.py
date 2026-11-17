#!/usr/bin/env python3
"""Compact summary of the development models, with input importance compared with the frozen legacy XMLs.

  python summarize_dev_models.py --numu OUT_NUMU --ncpi0 OUT_NCPI0 --legacy-splits DIR --out SUMMARY.json

--legacy-splits: the EAF XML audit tables (<model>_variable_splits.csv, commit 0148e879), read as published.
"""
import argparse
import json
import os

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

L1 = ['tro_5_score', 'tro_4_score', 'tro_2_score', 'tro_1_score', 'stw_4_score', 'stw_3_score', 'stw_2_score',
      'sig_2_score', 'sig_1_score', 'pio_2_score', 'lol_2_score', 'lol_1_score', 'br3_6_score', 'br3_5_score', 'br3_3_score']


def one(out, legacy_csv, focus, groups):
    met = json.load(open(os.path.join(out, 'metrics.json')))
    imp = pd.read_csv(os.path.join(out, 'importance.csv'))
    leg = pd.read_csv(legacy_csv).rename(columns={'name': 'feature', 'n_splits': 'legacy_splits'})
    leg['legacy_share'] = leg.legacy_splits / leg.legacy_splits.sum()
    leg['legacy_rank'] = leg.legacy_splits.rank(ascending=False, method='min').astype(int)
    groups = {g: (fs if fs is not None else [x for x in imp.feature if x.startswith(g.split('_12')[0] + '_')]) for g, fs in groups.items()}
    m = imp.merge(leg[['feature', 'legacy_splits', 'legacy_share', 'legacy_rank']], on='feature', how='left')
    assert m.legacy_splits.notna().all(), 'feature names differ from the legacy XML'
    r = dict(counts=met['counts'], leakage=met['leakage'], nonfinite_excluded=met['nonfinite_excluded'],
             train=dict((k, met['train'][k]) for k in ('auc', 'error_margin_gt_0', 'error_margin_gt_0p5', 'xgboost_eval')),
             test=dict((k, met['test'][k]) for k in ('auc', 'error_margin_gt_0', 'error_margin_gt_0p5', 'xgboost_eval', 'confusion_margin_gt_0')),
             score_scale=met['score_scale'], reproducibility=met['reproducibility'], total_splits=met['total_splits'],
             top10_weight=m.sort_values('weight', ascending=False).head(10)[['feature', 'weight', 'weight_share', 'legacy_splits', 'legacy_rank']].to_dict('records'),
             top10_gain=m.sort_values('gain', ascending=False).head(10)[['feature', 'gain', 'rank_weight', 'legacy_rank']].to_dict('records'),
             focus={f: m[m.feature == f][['weight', 'weight_share', 'rank_weight', 'gain', 'rank_gain', 'total_gain_share', 'legacy_splits', 'legacy_share', 'legacy_rank']].iloc[0].to_dict() for f in focus},
             groups={g: dict(weight_share=float(m[m.feature.isin(fs)].weight_share.sum()), total_gain_share=float(m[m.feature.isin(fs)].total_gain_share.sum()),
                             legacy_share=float(m[m.feature.isin(fs)].legacy_share.sum())) for g, fs in groups.items()},
             spearman_split_share_dev_vs_legacy=float(spearmanr(m.weight, m.legacy_splits).correlation),
             unused_inputs_dev=m[m.weight == 0].feature.tolist(), unused_inputs_legacy=m[m.legacy_splits == 0].feature.tolist())
    if 'kine_pio_flag_diagnostic' in met:
        r['kine_pio_flag_diagnostic'] = met['kine_pio_flag_diagnostic']
    return r


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--numu', required=True); ap.add_argument('--ncpi0', required=True)
    ap.add_argument('--legacy-splits', required=True); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    res = dict(label='ROUND1_DOMAIN_DEVELOPMENT_DO_NOT_DEPLOY', legacy_split_source='EAF XML audit 0148e879 tables/sp_bdt_xml_audit',
               numu=one(a.numu, os.path.join(a.legacy_splits, 'numu_variable_splits.csv'), ['numu_score', 'numu_1_score'],
                        {'numu_score+numu_1_score': ['numu_score', 'numu_1_score']}),
               ncpi0=one(a.ncpi0, os.path.join(a.legacy_splits, 'ncpi0_variable_splits.csv'),
                         ['kine_pio_flag', 'kine_pio_mass', 'shw_sp_E_indirect_max_energy', 'shw_sp_pio_flag_pio'],
                         {'15_nue_L1_scores': L1, 'kine_pio_12': None}))
    json.dump(res, open(a.out, 'w'), indent=1, default=float)
    print('wrote', a.out)


if __name__ == '__main__':
    main()
