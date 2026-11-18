#!/usr/bin/env python3
"""Legacy MicroBooNE XML vs SBND development model on the SAME development test rows (no training).

  python legacy_control_compare.py --bundle-root DIR --tables DIR --tag dev --spec DEV_SPEC.yaml \
      --dev-out DEV_MODEL_DIR --out-dir OUT

AURORA DEVELOPMENT SAMPLE -- LEGACY MICROBOONE CONTROL. Not official SBND performance, not a Round-2 cut.
The test rows are rebuilt with sp_retrain.devtrain.build_dataset from the frozen tables and spec, and must equal the
stored margins_test.parquet keys in order; the development model's margins are recomputed from its JSON and must
equal the stored ones. Legacy scores use sp_retrain.legacy_control (TMVA semantics, transform applied once; legacy
ncpi0 with kine_pio_flag = 0). New-model thresholds at the legacy signal efficiency (point A) and background
acceptance (point B) are DIAGNOSTIC ROC-EQUIVALENT POINTS -- NOT ROUND-2 CUTS.
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

ROUND2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROUND2)
from sp_retrain import devtrain, features, labels, legacy_control as lc  # noqa: E402

VARS = {
    'single_photon_numu': ['numu_score', 'numu_1_score', 'shw_sp_length_total', 'shw_sp_length_main',
                           'shw_sp_br3_1_n_shower_segments', 'numu_cc_3_track_length', 'numu_cc_3_max_muon_length',
                           'shw_sp_E_indirect_max_energy', 'shw_sp_n_20mev_showers'],
    'single_photon_ncpi0': ['kine_pio_flag', 'kine_pio_mass', 'kine_pio_energy_1', 'kine_pio_energy_2', 'kine_pio_angle',
                            'shw_sp_pio_flag_pio', 'shw_sp_E_indirect_max_energy', 'shw_sp_n_20mev_showers'],
    'single_photon_other': ['numu_score', 'numu_1_score', 'cosmict_10_score', 'cosmict_flag', 'cosmic_flag', 'numu_cc_flag',
                            'shw_sp_E_indirect_max_energy', 'shw_sp_n_20mev_showers', 'kine_nu_y_corr'],
    'single_photon_nue': ['shw_sp_vec_mean_dedx', 'shw_sp_vec_median_dedx', 'shw_sp_vec_dQ_dx_0', 'shw_sp_vec_dQ_dx_1',
                          'shw_sp_stem_length', 'shw_sp_shw_vtx_dis', 'shw_sp_min_dis', 'shw_sp_E_indirect_max_energy',
                          'shw_sp_n_20mev_showers'],
}
LABEL = 'AURORA DEVELOPMENT SAMPLE -- LEGACY MICROBOONE CONTROL'


def load_cands(tables, tag, spec, extra):
    stamp = json.load(open(os.path.join(os.path.dirname(ROUND2), spec['samples']['input_manifest'])))['reconstruction']['wct_version_stamp']
    out = []
    for s in spec['samples']['development']:
        F = pd.read_parquet(os.path.join(tables, 'files_%s_%s.parquet' % (s['id'], tag)))
        C = pd.read_parquet(os.path.join(tables, 'cands_%s_%s.parquet' % (s['id'], tag)))
        out.append(C[~C.file_id.isin(set(F[F.wct_version.fillna('') != stamp].file_id))])
    return pd.concat(out, ignore_index=True)


def summarize_flips(sub, lp, dp, clf):
    cat = np.where(lp & dp, 'both_pass', np.where(lp & ~dp, 'legacy_pass_dev_fail', np.where(~lp & dp, 'legacy_fail_dev_pass', 'both_fail')))
    sub = sub.assign(flip=cat)
    res = {}
    for c in ('legacy_pass_dev_fail', 'legacy_fail_dev_pass'):
        q = sub[sub.flip == c]
        r = dict(rows=int(len(q)), by_class={str(k): int(v) for k, v in q.cls.value_counts().items()},
                 by_sample={str(k): int(v) for k, v in q['sample'].value_counts().items()})
        if clf == 'single_photon_ncpi0':
            r['positive_by_category'] = {str(k): int(v) for k, v in q[q.cls == 1].m_sp_category.value_counts().items()}
            r['negative_by_n_prim_pi0'] = {str(int(k)): int(v) for k, v in q[q.cls == 0].m_sp_n_prim_pi0.value_counts().items()}
            r['kine_pio_flag'] = {str(int(k)): int(v) for k, v in q.kine_pio_flag.value_counts().items()}
        r['median_by_class'] = {str(k): {v: float(g[v].median()) for v in VARS[clf]} for k, g in q.groupby('cls')}
        res[c] = r
    res['reference_median_by_class_all_common_rows'] = {str(k): {v: float(g[v].median()) for v in VARS[clf]} for k, g in sub.groupby('cls')}
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    for k in ('--bundle-root', '--tables', '--tag', '--spec', '--dev-out', '--out-dir'):
        ap.add_argument(k, required=True)
    a = ap.parse_args()
    import xgboost as xgb
    from scipy.stats import pearsonr, spearmanr
    from sklearn.metrics import roc_auc_score, roc_curve

    bundle = lc.verify_bundle(a.bundle_root)
    spec = labels.load_spec(a.spec); devtrain.require_development_spec(spec)
    clf = spec['classifier']['name']; fl = features.load(clf); cols = fl.columns
    forest = lc.load_control(a.bundle_root, clf, fl.names)
    os.makedirs(a.out_dir, exist_ok=True)

    C = load_cands(a.tables, a.tag, spec, VARS[clf])
    ds = devtrain.build_dataset(C, spec)
    te = (ds['keys'].split == 'test').to_numpy()
    keys = ds['keys'][te].reset_index(drop=True); X = ds['X'][te]; y = ds['y'][te]
    stored = pd.read_parquet(os.path.join(a.dev_out, 'margins_test.parquet'))
    same_rows = keys[devtrain.ROW_KEY + ['split', 'cls']].equals(stored[devtrain.ROW_KEY + ['split', 'cls']].reset_index(drop=True))
    if not same_rows:
        raise SystemExit('rebuilt test rows differ from the stored development test rows')
    bst = xgb.Booster(); mpath = os.path.join(a.dev_out, spec['classifier']['model_name'] + '.json'); bst.load_model(mpath)
    m_new = bst.predict(xgb.DMatrix(X, feature_names=cols), output_margin=True)
    max_margin_diff = float(np.abs(m_new - stored.margin.to_numpy()).max())

    # legacy on the same rows (ncpi0: flag forced to 0), plus the excluded non-finite test rows as a diagnostic
    v_leg, s_leg = lc.legacy_score(forest, lc.legacy_matrix(X, cols, clf))
    legacy_ok = v_leg != -999.0
    nf = ds['nonfinite'].copy(); nf['split'] = np.where(nf.subrun % 2 == 1, 'test', 'train')
    ext = nf['sample'].astype(str).isin(labels.ext_sample_ids(spec)).to_numpy()   # EXT: by run, as in devtrain
    nf.loc[ext, 'split'] = np.where(nf.run[ext] % 4 == 1, 'test', 'train'); nft = nf[nf.split == 'test']
    if len(nft):
        Xn = nft[devtrain.ROW_KEY].merge(C, on=devtrain.ROW_KEY, how='left')[cols].to_numpy(np.float64).astype(np.float32)
        vn, _ = lc.legacy_score(forest, lc.legacy_matrix(Xn, cols, clf)); nf_legacy_evaluable = int((vn != -999.0).sum())
    else:
        nf_legacy_evaluable = 0
    common = legacy_ok  # every new-evaluable row is finite
    yc, sl, mn = y[common], s_leg[common], m_new[common]
    raw_tmva = forest.raw(lc.legacy_matrix(X, cols, clf)); raw_le = lc.raw_left_if_le(forest, lc.legacy_matrix(X, cols, clf))

    op_leg = lc.operating_point(yc, sl, lc.LEGACY_CUT[clf])
    tA = lc.threshold_for_rate(mn[yc == 1], op_leg['signal_efficiency']); opA = lc.operating_point(yc, mn, tA)
    tB = lc.threshold_for_rate(mn[yc == 0], op_leg['background_acceptance']); opB = lc.operating_point(yc, mn, tB)
    lp = sl > lc.LEGACY_CUT[clf]
    sub = keys[common].reset_index(drop=True).merge(C[devtrain.ROW_KEY + VARS[clf] + ['m_sp_category', 'm_sp_n_prim_pi0']].drop_duplicates(devtrain.ROW_KEY),
                                                    on=devtrain.ROW_KEY, how='left')
    res = dict(
        label=LABEL, classifier=clf, bundle=bundle, legacy_xml=lc.XML[clf][0], legacy_xml_sha256=lc.XML[clf][1],
        legacy_structure=dict(inputs=len(forest.names), trees=forest.ntrees, max_depth=lc.max_depth(forest), xml_order_equals_feature_list=forest.names == fl.names),
        legacy_convention='score = log10((1+v)/(1-v)), v = TMVA EvaluateMVA (tmva_grad)' + ('; kine_pio_flag forced to 0' if clf == 'single_photon_ncpi0' else ''),
        rows=dict(original_test=int(len(keys) + len(nft)), new_evaluable=int(len(keys)), legacy_evaluable=int(legacy_ok.sum() + nf_legacy_evaluable),
                  common=int(common.sum()), excluded_nonfinite_test=int(len(nft)), excluded_nonfinite_test_legacy_evaluable=nf_legacy_evaluable,
                  common_positive=int((yc == 1).sum()), common_negative=int((yc == 0).sum())),
        alignment=dict(rebuilt_rows_equal_stored=bool(same_rows), max_abs_margin_diff_vs_stored=max_margin_diff),
        auc=dict(legacy=float(roc_auc_score(yc, sl)), dev=float(roc_auc_score(yc, mn)), dev_stored_metrics=json.load(open(os.path.join(a.dev_out, 'metrics.json')))['test']['auc']),
        legacy_at_historical_cut=op_leg,
        point_A_same_signal_efficiency=dict(new_threshold_native_margin=tA, new=opA, legacy=op_leg,
                                            background_acceptance_abs_diff=opA['background_acceptance'] - op_leg['background_acceptance'],
                                            background_acceptance_ratio=opA['background_acceptance'] / max(op_leg['background_acceptance'], 1e-12)),
        point_B_same_background_acceptance=dict(new_threshold_native_margin=tB, new=opB, legacy=op_leg,
                                                signal_efficiency_abs_diff=opB['signal_efficiency'] - op_leg['signal_efficiency'],
                                                signal_efficiency_ratio=opB['signal_efficiency'] / max(op_leg['signal_efficiency'], 1e-12)),
        flips_A=dict(all=lc.flips(lp, mn > tA), positive=lc.flips(lp[yc == 1], (mn > tA)[yc == 1]), negative=lc.flips(lp[yc == 0], (mn > tA)[yc == 0]),
                     summary=summarize_flips(sub, lp, mn > tA, clf)),
        flips_B=dict(all=lc.flips(lp, mn > tB), positive=lc.flips(lp[yc == 1], (mn > tB)[yc == 1]), negative=lc.flips(lp[yc == 0], (mn > tB)[yc == 0]),
                     summary=summarize_flips(sub, lp, mn > tB, clf)),
        correlation=dict(spearman_all=float(spearmanr(sl, mn).correlation), pearson_all_legacy_score_vs_margin=float(pearsonr(sl, mn)[0]),
                         spearman_positive=float(spearmanr(sl[yc == 1], mn[yc == 1]).correlation),
                         spearman_negative=float(spearmanr(sl[yc == 0], mn[yc == 0]).correlation)),
        routing_check=dict(rows_where_le_routing_changes_raw=int((np.abs(raw_tmva - raw_le) > 0).sum()), max_abs_raw_diff=float(np.abs(raw_tmva - raw_le).max())),
        score_check=dict(score_equals_2raw_over_ln10_max_abs=float(np.abs(s_leg - 2 * raw_tmva / np.log(10)).max())),
    )
    if clf == 'single_photon_ncpi0':
        _, s_real = lc.legacy_score(forest, X)      # diagnostic only: the legacy XML is NOT scored this way in production
        res['legacy_with_real_flag_diagnostic'] = dict(auc=float(roc_auc_score(yc, s_real[common])),
                                                       spearman_vs_forced0=float(spearmanr(s_real[common], sl).correlation),
                                                       decision_changes_at_historical_cut=int(((s_real[common] > lc.LEGACY_CUT[clf]) != lp).sum()),
                                                       note='not the source-faithful convention; shows how the legacy model reacts to the real SBND flag')
        res['dev_policy_B_flag_diagnostic'] = json.load(open(os.path.join(a.dev_out, 'metrics.json')))['kine_pio_flag_diagnostic']
    json.dump(res, open(os.path.join(a.out_dir, 'legacy_vs_dev.json'), 'w'), indent=1, default=float)
    fl_, tl_, _ = roc_curve(yc, sl); fn_, tn_, _ = roc_curve(yc, mn)
    np.savez_compressed(os.path.join(a.out_dir, 'roc_and_scores.npz'), legacy_fpr=fl_, legacy_tpr=tl_, dev_fpr=fn_, dev_tpr=tn_,
                        y=yc, legacy_score=sl, dev_margin=mn, tA=tA, tB=tB, legacy_cut=lc.LEGACY_CUT[clf])
    print(json.dumps(dict(model=clf, rows=res['rows'], auc=res['auc'], legacy_cut=op_leg, A=opA, B=opB, spearman=res['correlation']['spearman_all'],
                          routing=res['routing_check'], align=res['alignment']), default=float))


if __name__ == '__main__':
    main()
