#!/usr/bin/env python3
"""All-four SP feature-stability report for the WCL1116 development models (no training).

  python sp_feature_stability.py --models-root $SP_WORK/wcl1116_dev_models --tables-template $SP_WORK/wcl1116_dev_tables/%s \
      --tag dev --bundle-root LEGACY --out-json validation/sp_feature_stability_wcl1116.json --out-csv validation/sp_feature_families_wcl1116.csv

Per model and vertex mode (the 92a1b17 development models, unchanged): top 20 by splits and by total gain; gain share of
the top 5 / top 10; overlap with the inherited MicroBooNE top 20 (legacy XML split counts; the XML carries no gains);
split-move vs snap overlap of the top 20 and Spearman of the gain shares; gain share per family.

Families (audited; an input the sources do not settle is AMBIGUOUS, never forced):
  upstream_classifier   kind == 'upstream_score' in config/features/*_inputs_v0.json
  cosmic_boundary       cosmict_* / cosmic_* reco inputs (written by cosmic_tagger(); RESULTS sec. 11) and the upstream scores
                        that sec. 11 shows are built on cosmic-tagger outputs: numu_score (61 / 74 inputs), cosmict_10_score
                        (cos_tagger_10 on cosmict_10_*). numu_1_score (numu_cc_1_*) and the 15 nu_e L1 scores (NeutrinoTaggerNuE,
                        no cosmic reference) are NOT; numu_2_score is not covered by sec. 11 -> AMBIGUOUS
  vertex_sensitive      MEASURED: split-move and snap differ only in the vertex placed on the same clusters, so the fraction of
                        matched preselected NC Delta + BNB candidates (same key, same cluster_id) whose stored value differs
                        between the two trees: >= 0.10 -> sensitive, <= 0.01 -> insensitive, otherwise AMBIGUOUS
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

ROUND2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROUND2)
from sp_retrain import devstudy as dv, devtrain, features, labels, legacy_control as lc  # noqa: E402

MODELS = ('numu', 'ncpi0', 'other', 'nue')
MODES = ('dv2_split_move', 'dv2_snap')
COSMIC_UPSTREAM = {'numu_score', 'cosmict_10_score'}
NOT_COSMIC_UPSTREAM = {'numu_1_score'}
AMBIGUOUS_COSMIC = {'numu_2_score'}
VTX_SENSITIVE, VTX_INSENSITIVE = 0.10, 0.01


def vertex_change_fractions(tables_template, tag, cols):
    parts = {}
    for mode in MODES:
        P = []
        for s in ('wcl1116-aurora-ncdr', 'wcl1116-aurora-bnb'):
            c = pd.read_parquet(os.path.join(tables_template % mode, 'cands_%s_%s.parquet' % (s, tag)),
                                columns=list(dict.fromkeys(devtrain.ROW_KEY + ['cluster_id', 'is_placeholder', 'shw_sp_n_20mev_showers', 'label_unreadable'] + cols)))
            P.append(c[labels.preselection(c)])
        parts[mode] = pd.concat(P, ignore_index=True)
    M = parts['dv2_split_move'].merge(parts['dv2_snap'], on=devtrain.ROW_KEY + ['cluster_id'], suffixes=('_a', '_b'))
    out = {}
    for c in cols:
        x, y = M[c + '_a'].to_numpy(np.float64), M[c + '_b'].to_numpy(np.float64)
        same = (np.isnan(x) & np.isnan(y)) | (np.abs(x - y) <= 1e-6 * np.maximum(1.0, np.abs(x)))
        out[c] = float((~same).mean())
    return out, int(len(M))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    for k in ('--models-root', '--tables-template', '--tag', '--bundle-root', '--out-json', '--out-csv'):
        ap.add_argument(k, required=True)
    a = ap.parse_args()
    from scipy.stats import spearmanr
    allcols = sorted(set(sum((features.load('single_photon_' + m).columns for m in MODELS), [])))
    vfrac, nmatch = vertex_change_fractions(a.tables_template, a.tag, allcols)
    fam_rows, out = [], dict(label='SP FEATURE STABILITY (WCL1116 development models of 92a1b17; DEV_DO_NOT_DEPLOY)', matched_candidates_for_vertex_test=nmatch,
                             thresholds=dict(vertex_sensitive=VTX_SENSITIVE, vertex_insensitive=VTX_INSENSITIVE), models={})
    for m in MODELS:
        clf = 'single_photon_' + m; fl = features.load(clf); cols = fl.columns
        meta = {(f['table_column'] or f['name']): f for f in dv.feature_meta(m)}
        cosmic_direct = set(dv.cosmic_tagger_direct(m)); ups = set(dv.upstream_family(m))
        fam = {}
        for c in cols:
            cb = 'yes' if (c in cosmic_direct or c in COSMIC_UPSTREAM) else ('ambiguous' if c in AMBIGUOUS_COSMIC else 'no')
            v = vfrac[c]; vs = 'yes' if v >= VTX_SENSITIVE else ('no' if v <= VTX_INSENSITIVE else 'ambiguous')
            fam[c] = dict(upstream_classifier='yes' if c in ups else 'no', cosmic_boundary=cb, vertex_sensitive=vs, vertex_change_fraction=v)
            fam_rows.append(dict(model=m, feature=c, **fam[c]))
        forest = lc.load_control(a.bundle_root, clf, fl.names)
        cnt = np.bincount(forest.ivar[~forest.leaf], minlength=len(forest.names)); name_of = dict(zip(cols, fl.names))
        leg = pd.Series({c: cnt[forest.names.index(name_of[c])] for c in cols})
        leg_top = leg.sort_values(ascending=False).index[:20].tolist()
        res = dict(n_inputs=len(cols), legacy_top20_by_splits=leg_top, modes={})
        imps = {}
        for mode in MODES:
            imp = pd.read_csv(os.path.join(a.models_root, mode, m, 'importance.csv')).set_index('feature').reindex(cols).fillna(0.0)
            imps[mode] = imp
            g = imp.total_gain / imp.total_gain.sum()
            tops, topg = imp.weight.sort_values(ascending=False).index[:20].tolist(), g.sort_values(ascending=False).index[:20].tolist()
            share = lambda key, val: float(sum(g[c] for c in cols if fam[c][key] == val))
            res['modes'][mode] = dict(
                top20_by_splits=tops, top20_by_gain=topg, gain_share_top5=float(g.sort_values(ascending=False).iloc[:5].sum()),
                gain_share_top10=float(g.sort_values(ascending=False).iloc[:10].sum()), top20_split_overlap_with_legacy=len(set(tops) & set(leg_top)),
                gain_share_upstream_classifier=share('upstream_classifier', 'yes'),
                gain_share_cosmic_boundary=share('cosmic_boundary', 'yes'), gain_share_cosmic_boundary_ambiguous=share('cosmic_boundary', 'ambiguous'),
                gain_share_vertex_sensitive=share('vertex_sensitive', 'yes'), gain_share_vertex_ambiguous=share('vertex_sensitive', 'ambiguous'),
                gain_share_vertex_insensitive=share('vertex_sensitive', 'no'))
        ga, gb = imps['dv2_split_move'].total_gain, imps['dv2_snap'].total_gain
        res['split_vs_snap'] = dict(top20_gain_overlap=len(set(res['modes']['dv2_split_move']['top20_by_gain']) & set(res['modes']['dv2_snap']['top20_by_gain'])),
                                    top20_split_overlap=len(set(res['modes']['dv2_split_move']['top20_by_splits']) & set(res['modes']['dv2_snap']['top20_by_splits'])),
                                    gain_spearman=float(spearmanr(ga, gb).correlation))
        res['family_counts'] = {k: {v: int(sum(1 for c in cols if fam[c][k] == v)) for v in ('yes', 'ambiguous', 'no')}
                                for k in ('upstream_classifier', 'cosmic_boundary', 'vertex_sensitive')}
        out['models'][m] = res
        print(m, json.dumps({k: res[k] for k in ('n_inputs', 'split_vs_snap', 'family_counts')}),
              {mo: {k: round(v, 3) for k, v in r.items() if k.startswith('gain_share') or k.endswith('legacy')} for mo, r in res['modes'].items()})
    pd.DataFrame(fam_rows).to_csv(a.out_csv, index=False, float_format='%.5g')
    json.dump(out, open(a.out_json, 'w'), indent=1)


if __name__ == '__main__':
    main()
