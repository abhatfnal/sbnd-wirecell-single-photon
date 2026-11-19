#!/usr/bin/env python3
"""SP other feature sanity on the WCL1116 development models vs the exact legacy XML fingerprint (no training).

  python sp_other_feature_sanity.py --bundle-root LEGACY --model-dir-template $SP_WORK/wcl1116_dev_models/%s/other --out-json OUT.json

Per mode: top-20 inputs by split count and by total gain; split / gain shares of input families:
  upstream scores   numu_score, numu_1_score, numu_2_score, cosmict_10_score (upstream BDT outputs, SHIPPED_CONTROL)
  cosmic tagger     every other cosmict_* / cosmic_* input (direct outputs of PatternAlgorithms::cosmic_tagger())
  numu tagger       numu_cc_* (numu_cc_flag and the numu tagger blocks)
  shower            shw_sp_*
  vertex            reco_nuvtxY (kine_nu_y_corr)
Legacy: split counts of single_photon_other_bdt_final.xml (215 trees). Bookkeeping identifiers must not be inputs.
"""
import argparse, json, os, sys
import pandas as pd
ROUND2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROUND2)
from sp_retrain import features, legacy_control as lc  # noqa: E402

UPSTREAM = ('numu_score', 'numu_1_score', 'numu_2_score', 'cosmict_10_score')
BOOKKEEPING = {'run', 'subrun', 'event', 'cand', 'file_id', 'sample', 'cluster_id', 'nu_index', 'eventNo', 'runNo', 'subRunNo'}


def family(c):
    if c in UPSTREAM: return 'upstream_scores'
    if c.startswith(('cosmict_', 'cosmic_')): return 'cosmic_tagger'
    if c.startswith('numu_cc_'): return 'numu_tagger'
    if c.startswith('shw_sp_'): return 'shower'
    if c in ('kine_nu_y_corr', 'reco_nuvtxY'): return 'vertex'
    return 'other'


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    for k in ('--bundle-root', '--model-dir-template', '--out-json'):
        ap.add_argument(k, required=True)
    a = ap.parse_args()
    fl = features.load('single_photon_other'); cols = fl.columns; name_of = dict(zip(cols, fl.names))
    forest = lc.load_control(a.bundle_root, 'single_photon_other', fl.names)
    import numpy as np
    cnt = np.bincount(forest.ivar[~forest.leaf], minlength=len(forest.names)); leg = dict(zip(forest.names, cnt.tolist()))
    L = pd.DataFrame(dict(feature=cols, legacy_splits=[leg[name_of[c]] for c in cols]))
    L['family'] = L.feature.map(family)
    fam_n = L.family.value_counts().to_dict()
    out = dict(label='SP other FEATURE SANITY (WCL1116 development models; DEV_DO_NOT_DEPLOY)', n_inputs=len(cols), inputs_per_family=fam_n,
               bookkeeping_inputs=sorted(set(cols) & BOOKKEEPING),
               legacy_top20_by_splits=L.sort_values('legacy_splits', ascending=False).feature.head(20).tolist(),
               legacy_family_split_share={f: float(g.legacy_splits.sum() / L.legacy_splits.sum()) for f, g in L.groupby('family')}, modes={})
    for mode in ('dv2_split_move', 'dv2_snap'):
        imp = pd.read_csv(os.path.join(a.model_dir_template % mode, 'importance.csv'))
        D = L.merge(imp[['feature', 'weight', 'total_gain']], on='feature', how='left').fillna(0.0)
        D['family'] = D.feature.map(family)
        top_s = D.sort_values('weight', ascending=False).head(20)
        top_g = D.sort_values('total_gain', ascending=False).head(20)
        rank = lambda col: {c: int(r) for c, r in zip(D.sort_values(col, ascending=False).feature, range(1, len(D) + 1))}
        rs, rg, rl = rank('weight'), rank('total_gain'), rank('legacy_splits')
        out['modes'][mode] = dict(
            top20_by_splits=[dict(feature=r.feature, splits=int(r.weight), legacy_splits=int(r.legacy_splits), legacy_rank=rl[r.feature]) for r in top_s.itertuples()],
            top20_by_gain=[dict(feature=r.feature, total_gain_share=float(r.total_gain / D.total_gain.sum()), split_rank=rs[r.feature]) for r in top_g.itertuples()],
            family_split_share={f: float(g.weight.sum() / D.weight.sum()) for f, g in D.groupby('family')},
            family_gain_share={f: float(g.total_gain.sum() / D.total_gain.sum()) for f, g in D.groupby('family')},
            upstream_ranks={c: dict(split_rank=rs[c], gain_rank=rg[c], legacy_rank=rl[c]) for c in UPSTREAM},
            top20_split_overlap_with_legacy=len(set(top_s.feature) & set(out['legacy_top20_by_splits'])),
            inputs_never_split=int((D.weight == 0).sum()))
    json.dump(out, open(a.out_json, 'w'), indent=1)
    print(json.dumps({k: out[k] for k in ('inputs_per_family', 'legacy_family_split_share', 'bookkeeping_inputs')}))
    for m, r in out['modes'].items():
        print(m, json.dumps({k: r[k] for k in ('family_split_share', 'family_gain_share', 'upstream_ranks', 'top20_split_overlap_with_legacy', 'inputs_never_split')}))
        print('  splits:', [(x['feature'], x['splits'], x['legacy_rank']) for x in r['top20_by_splits']])
        print('  gain  :', [(x['feature'], round(x['total_gain_share'], 3)) for x in r['top20_by_gain']])


if __name__ == '__main__':
    main()
