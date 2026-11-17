#!/usr/bin/env python3
"""Export / equivalence check of the XGBoost -> TMVA Grad exporter on the development fixtures (no training).

  python export_equivalence_check.py --tables DIR --tag dev --dev-models DIR --out-root DIR --summary-out JSON
         [--models numu ncpi0]

FIXTURES ONLY: the development models are ROUND1_DOMAIN_DEVELOPMENT_DO_NOT_DEPLOY. Nothing here selects a threshold:
the legacy cuts (numu 0.4, ncpi0 -0.05) and score quantiles are used only as places where decisions could flip.

Per model: the held-out TEST rows are rebuilt exactly as in training (sp_retrain.devtrain.build_dataset from the
frozen tables and dev spec; ncpi0 kine_pio_flag Policy B = stored value) and must equal the stored margins_test keys;
the native margins must equal the stored ones. The model is exported with sp_retrain.export_tmva and read back with
the validated evaluator sp_retrain.tmva_grad.GradForest (bit-identical to the toolkit on 423 nue and 320,228 numu
candidates). Compared per row: (a) native margin, (b) XML forest sum, (c) TMVA response tanh, (d) production
log10-odds score vs 2 margin / ln 10; per-tree leaf identity; decision flips at fixture thresholds; exact-threshold
(equality) routing on rows forced to a split value; extreme values; NaN behaviour; order guard; base-margin fold.
Large outputs go under --out-root (outside git); the summary JSON holds aggregates and the 20 rows closest to each
fixture threshold.

Pass rules (all_pass):
  * exporter exactness: XML forest sum == the native leaves summed in double in tree order (TMVA's arithmetic), exactly;
  * native margin (XGBoost sums the same leaves in float32) vs XML: |diff| <= 1e-5 * max(1, |margin|) on every row;
  * per-tree leaf identity on every test row, on rows forced to exact split values and on +-FLT_MAX rows;
  * zero decision flips at the legacy fixture cut and at quantile cuts placed midway between adjacent native scores
    (a cut ON a row's score is reported separately as an adversarial diagnostic and may flip that row);
  * order guard refuses a swapped variable list; a nonzero base margin is refused unless folded, and the folded
    constant tree reproduces base_score + leaf sum; objective binary:logistic is refused; NaN rows give -999.
"""
import argparse
import copy
import json
import math
import os
import sys

import numpy as np
import pandas as pd

ROUND2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROUND2)
sys.path.insert(0, os.path.join(ROUND2, 'tools'))
from sp_retrain import devtrain, export_tmva, features, labels, legacy_control as lc, tmva_grad  # noqa: E402
from legacy_control_compare import load_cands  # noqa: E402

LABEL = 'DEVELOPMENT FIXTURES (ROUND1_DOMAIN_DEVELOPMENT_DO_NOT_DEPLOY) -- EXPORT INFRASTRUCTURE CHECK, NOT A CUT'
FIXTURE_CUT = {'single_photon_numu': 0.4, 'single_photon_ncpi0': -0.05}
QUANTILES = (0.05, 0.25, 0.5, 0.75, 0.95)
SEED = 20261117
K = 2.0 / math.log(10.0)


def closest_rows(keys, s_nat, s_xml, cut, n=20):
    d = np.abs(s_nat - cut)
    idx = np.argsort(d, kind='stable')[:n]
    k = keys.iloc[idx]
    return dict(file_id=[str(v) for v in k.file_id], run=[int(v) for v in k.run], subrun=[int(v) for v in k.subrun],
                event=[int(v) for v in k.event], cand=[int(v) for v in k.cand], cls=[int(v) for v in k.cls],
                score_native=[float(s_nat[i]) for i in idx], score_xml=[float(s_xml[i]) for i in idx],
                pass_native=[bool(s_nat[i] > cut) for i in idx], pass_xml=[bool(s_xml[i] > cut) for i in idx])


def in_right_subtree(tree, node, leaf):
    """Is XGBoost node `leaf` a descendant of the right child of `node`?"""
    target = tree['right_children'][node]
    par = tree['parents']
    m = int(leaf)
    while m != 0 and m != 2147483647:
        if m == target:
            return True
        m = par[m]
    return m == target


def equality_test(bst, xgb, forest, order, trees, X, names, rng, n_nodes=400, rows_per_node=3):
    """Force x[f] = Cut at sampled internal nodes on rows that reach the node; compare every tree's leaf."""
    internal = [(t, k) for t in range(len(order)) for k in range(int(forest.roots[t]),
                int(forest.roots[t + 1]) if t + 1 < len(order) else len(forest.cut)) if not forest.leaf[k]]
    pick = rng.choice(len(internal), size=min(n_nodes, len(internal)), replace=False)
    sampled = exercised_nodes = rows = agree_all = right_both = 0
    for p in pick:
        t, k = internal[int(p)]
        sampled += 1
        vis = np.flatnonzero(export_tmva.visits(forest, X, t, k))
        if not len(vis):
            continue
        sel = rng.choice(vis, size=min(rows_per_node, len(vis)), replace=False)
        Xm = X[sel].copy()
        Xm[:, forest.ivar[k]] = forest.cut[k]
        still = export_tmva.visits(forest, Xm, t, k)
        Xm = Xm[still]
        if not len(Xm):
            continue
        exercised_nodes += 1
        rows += len(Xm)
        lx, _ = export_tmva.forest_leaves(forest, Xm)
        lx = export_tmva.xml_leaf_to_xgb_node(forest, order, lx)
        ln = bst.predict(xgb.DMatrix(Xm, feature_names=names), pred_leaf=True).astype(np.int64).reshape(len(Xm), -1)
        agree_all += int((lx == ln).all(axis=1).sum())
        xgb_node = order[t][k - int(forest.roots[t])]
        right_both += int(sum(in_right_subtree(trees[t], xgb_node, ln[i, t]) and lx[i, t] == ln[i, t] for i in range(len(Xm))))
    return dict(nodes_sampled=sampled, nodes_exercised=exercised_nodes, rows_exercised=rows,
                rows_all_trees_identical=agree_all, rows_routed_right_at_equality_both=right_both)


def run_model(short, a, xgb):
    spec_path = os.path.join(ROUND2, 'specs', 'single_photon_%s_training_spec_dev_round1_domain_v1.yaml' % short)
    spec = labels.load_spec(spec_path)
    devtrain.require_development_spec(spec)
    clf = spec['classifier']['name']; model_name = spec['classifier']['model_name']
    fl = features.load(clf); cols = fl.columns
    man = json.load(open(os.path.join(ROUND2, 'manifests', 'dev_round1domain_v1', 'single_photon_%s_dev_manifest.json' % short)))
    mdir = os.path.join(a.dev_models, short)
    mjson = os.path.join(mdir, model_name + '.json')
    model_sha = devtrain.sha256_file(mjson)
    if model_sha != man['model']['sha256']:
        raise SystemExit('%s: model sha256 differs from the dev manifest' % clf)

    C = load_cands(a.tables, a.tag, spec, [])
    ds = devtrain.build_dataset(C, spec)
    te = (ds['keys'].split == 'test').to_numpy()
    keys = ds['keys'][te].reset_index(drop=True); X = ds['X'][te]; y = ds['y'][te]
    stored = pd.read_parquet(os.path.join(mdir, 'margins_test.parquet'))
    same_rows = keys[devtrain.ROW_KEY + ['split', 'cls']].equals(stored[devtrain.ROW_KEY + ['split', 'cls']].reset_index(drop=True))
    if not same_rows:
        raise SystemExit('%s: rebuilt test rows differ from the stored development test rows' % clf)
    bst = xgb.Booster(); bst.load_model(mjson)
    d = xgb.DMatrix(X, feature_names=cols)
    m = bst.predict(d, output_margin=True)
    if float(np.abs(m - stored.margin.to_numpy()).max()) != 0.0:
        raise SystemExit('%s: recomputed margins differ from the stored ones' % clf)

    out_dir = os.path.join(a.out_root, short)
    info = dict(SpecId=spec['spec_id'], SpecVersion=str(spec['spec_version']), Campaign=spec['campaign'],
                Deployable=str(spec['deployable']).lower(),
                TrainingCommit=man['post_training_provenance']['training_code_content_commit'])
    rec = export_tmva.export(mjson, fl, out_dir, model_name, info=info)
    order = rec['node_order']
    forest = tmva_grad.GradForest(rec['paths']['xml'], expected_names=fl.names)
    trees = json.load(open(mjson))['learner']['gradient_booster']['model']['trees']

    raw = forest.raw(X); v = forest.evaluate_mva(X); s_xml = tmva_grad.log10_odds(v)
    m64 = m.astype(np.float64); s_nat = K * m64
    dm = np.abs(raw - m64); dv = np.abs(v - np.tanh(m64)); ds_ = np.abs(s_xml - s_nat)
    lx, eq_hits = export_tmva.forest_leaves(forest, X)
    lx = export_tmva.xml_leaf_to_xgb_node(forest, order, lx)
    ln = bst.predict(d, pred_leaf=True).astype(np.int64).reshape(len(X), -1)
    leaf_mismatch = int((lx != ln).sum())
    # the native leaves summed two ways: double in tree order (= TMVA's arithmetic) and float32 in tree order
    lv = [np.asarray(t['split_conditions'], np.float32) for t in trees]
    leaf_vals = np.stack([lv[t][ln[:, t]] for t in range(len(trees))], axis=1)
    sum_double = np.zeros(len(X), np.float64); sum_f32 = np.zeros(len(X), np.float32)
    for t in range(len(trees)):
        sum_double += leaf_vals[:, t].astype(np.float64); sum_f32 = (sum_f32 + leaf_vals[:, t]).astype(np.float32)
    rel_bound = 1e-5 * np.maximum(1.0, np.abs(m64))

    # fixture thresholds: the legacy cut, and score quantiles placed MIDWAY between adjacent distinct native scores
    # (how a threshold is placed); plus one adversarial cut ON a row's native score (diagnostic, flips allowed)
    u = np.unique(s_nat)
    mid = [('score_quantile_%g_midpoint' % q, float(0.5 * (u[int(q * (len(u) - 1))] + u[int(q * (len(u) - 1)) + 1]))) for q in QUANTILES]
    cuts = [('fixture_legacy_cut', FIXTURE_CUT[clf])] + mid
    adv_c = float(np.quantile(s_nat, 0.5, method='lower'))
    adversarial = dict(label='adversarial_cut_equal_to_a_native_score (median row)', cut_log10_odds=adv_c,
                       flips_score=int(((s_nat > adv_c) != (s_xml > adv_c)).sum()),
                       rows_with_native_score_equal_cut=int((s_nat == adv_c).sum()),
                       note='a cut placed exactly on a row score can flip that row: float32 (XGBoost) vs double (TMVA) sums')
    thr = []
    for lab, c in cuts:
        pn = s_nat > c; px = s_xml > c
        tm = c / K
        thr.append(dict(label=lab, cut_log10_odds=c, flips_score=int((pn != px).sum()),
                        flips_raw_margin=int(((m64 > tm) != (raw > tm)).sum()),
                        min_abs_distance_native_score_to_cut=float(np.abs(s_nat - c).min()),
                        rows_within_2em5_of_cut=int((np.abs(s_nat - c) < 2e-5).sum()),
                        closest_20=closest_rows(keys, s_nat, s_xml, c)))

    rng = np.random.default_rng(SEED)
    eqt = equality_test(bst, xgb, forest, order, trees, X, cols, rng)

    # extreme finite values
    n_ext = min(400, len(X))
    ri = rng.choice(len(X), size=n_ext, replace=False); fi = rng.integers(0, X.shape[1], size=n_ext)
    Xe = X[ri].copy(); big = np.finfo(np.float32).max
    Xe[np.arange(n_ext), fi] = np.where(rng.random(n_ext) < 0.5, -big, big).astype(np.float32)
    le, _ = export_tmva.forest_leaves(forest, Xe); le = export_tmva.xml_leaf_to_xgb_node(forest, order, le)
    lne = bst.predict(xgb.DMatrix(Xe, feature_names=cols), pred_leaf=True).astype(np.int64).reshape(n_ext, -1)
    me = bst.predict(xgb.DMatrix(Xe, feature_names=cols), output_margin=True).astype(np.float64)

    # NaN behaviour: synthetic (root feature of tree 0 set to NaN) and the real excluded non-finite rows
    j0 = int(forest.ivar[forest.roots[0]])
    Xn = X[:50].copy(); Xn[:, j0] = np.nan
    mn = bst.predict(xgb.DMatrix(Xn, feature_names=cols), output_margin=True)
    vn = forest.evaluate_mva(Xn); sn = tmva_grad.log10_odds(vn)
    nf = ds['nonfinite']
    real_nf = dict(rows=int(len(nf)))
    if len(nf):
        Xr = nf[devtrain.ROW_KEY].merge(C, on=devtrain.ROW_KEY, how='left')[cols].to_numpy(np.float64).astype(np.float32)
        mr = bst.predict(xgb.DMatrix(Xr, feature_names=cols), output_margin=True); vr = forest.evaluate_mva(Xr)
        real_nf.update(xgboost_margin_finite=int(np.isfinite(mr).sum()), tmva_minus999=int((vr == -999.0).sum()),
                       features=sorted(set(';'.join(nf.features).split(';'))))

    # order guard: swap the first two variable names in the exported XML
    txt = open(rec['paths']['xml']).read()
    n0, n1 = fl.names[0], fl.names[1]
    sw = txt.replace('Expression="%s"' % n0, 'Expression="@@0"', 1).replace('Expression="%s"' % n1, 'Expression="%s"' % n0, 1).replace('Expression="@@0"', 'Expression="%s"' % n1, 1)
    sw_path = os.path.join(out_dir, 'order_guard_swapped.xml'); open(sw_path, 'w').write(sw)
    try:
        tmva_grad.GradForest(sw_path, expected_names=fl.names); order_refused = False
    except ValueError:
        order_refused = True

    # base-margin semantics on the real fixture: the same trees with base_score 0.5 (temporary copy, outside git)
    mj = json.load(open(mjson)); mj2 = copy.deepcopy(mj); mj2['learner']['learner_model_param']['base_score'] = '[5E-1]'
    tmp = os.path.join(out_dir, 'base_score_0p5_copy.json'); json.dump(mj2, open(tmp, 'w'))
    b2 = xgb.Booster(); b2.load_model(tmp); m2 = b2.predict(d, output_margin=True).astype(np.float64)
    try:
        export_tmva.export(tmp, fl, os.path.join(out_dir, 'fold_test'), 'base_0p5_unfolded'); unfolded_refused = False
    except export_tmva.ExportError:
        unfolded_refused = True
    rf = export_tmva.export(tmp, fl, os.path.join(out_dir, 'fold_test'), 'base_0p5_folded', fold_base_margin=True)
    ff = tmva_grad.GradForest(rf['paths']['xml'], expected_names=fl.names)
    obj_refused = False
    mj3 = copy.deepcopy(mj); mj3['learner']['objective']['name'] = 'binary:logistic'
    try:
        export_tmva.to_tmva_xml(mj3, fl.names, cols)
    except export_tmva.ExportError:
        obj_refused = True

    pd.DataFrame(dict(margin_native=m64, raw_xml=raw, v_xml=v, score_native=s_nat, score_xml=s_xml)).join(keys).to_parquet(
        os.path.join(out_dir, 'rows_test.parquet'))
    big_s = np.abs(s_nat) > 8
    return dict(
        classifier=clf, model_json=mjson, model_sha256=model_sha, spec=os.path.relpath(spec_path, os.path.dirname(ROUND2)),
        export=dict(dir=out_dir, xml_sha256=rec['sha256']['xml'], json_sha256=rec['sha256']['json'],
                    features_sha256=rec['sha256']['features'], ntrees=rec['ntrees_xml'], nodes=rec['nodes'],
                    var_type=rec['var_type'], base_margin=rec['base_margin']),
        structure=dict(xml_names_equal_feature_list=forest.names == fl.names, trees=forest.ntrees,
                       expected_trees=int(spec['xgboost']['n_estimators']), max_depth=lc.max_depth(forest),
                       expected_max_depth=int(spec['xgboost']['max_depth'])),
        rows=dict(test=int(len(X)), positive=int((y == 1).sum()), negative=int((y == 0).sum()),
                  rebuilt_equal_stored=bool(same_rows)),
        equivalence=dict(max_abs_margin_minus_xml_raw=float(dm.max()), mean_abs_margin_minus_xml_raw=float(dm.mean()),
                         max_abs_tanh_margin_minus_tmva_response=float(dv.max()),
                         max_abs_score_native_minus_score_xml=float(ds_.max()),
                         max_abs_score_diff_where_abs_score_le_8=float(ds_[~big_s].max()) if (~big_s).any() else None,
                         rows_abs_score_gt_8=int(big_s.sum()), max_abs_native_margin=float(np.abs(m64).max()),
                         rows_abs_margin_diff_gt_1em5=int((dm > 1e-5).sum()),
                         min_abs_margin_of_rows_gt_1em5=float(np.abs(m64[dm > 1e-5]).min()) if (dm > 1e-5).any() else None,
                         max_rel_margin_diff=float((dm / np.maximum(1.0, np.abs(m64))).max()),
                         rows_beyond_1em5_x_max_1_absmargin=int((dm > rel_bound).sum()),
                         exporter_exactness_max_abs_xml_raw_minus_double_native_leaf_sum=float(np.abs(raw - sum_double).max()),
                         float32_tree_order_leaf_sum_minus_xgboost_margin_max_abs=float(np.abs(sum_f32.astype(np.float64) - m64).max()),
                         tree_leaf_mismatches=leaf_mismatch, tree_leaf_comparisons=int(lx.size),
                         real_data_visited_splits_with_x_equal_cut=int(eq_hits)),
        thresholds=thr, adversarial_threshold=adversarial,
        equality_boundary=eqt,
        extreme_values=dict(rows=n_ext, value='+-FLT_MAX in one random input', tree_leaf_mismatches=int((le != lne).sum()),
                            max_abs_margin_minus_xml_raw=float(np.abs(forest.raw(Xe) - me).max())),
        nan_behaviour=dict(synthetic_rows=50, feature=fl.names[j0], xgboost_margin_finite=int(np.isfinite(mn).sum()),
                           tmva_response_minus999=int((vn == -999.0).sum()), production_score_of_minus999=float(sn.min()),
                           real_excluded_nonfinite=real_nf,
                           policy='non-finite rows are excluded from training and offline scoring; production -999 -> minimum score (rejected)'),
        order_guard=dict(swapped=[n0, n1], refused_by_GradForest=order_refused),
        base_margin=dict(xgboost_margin_shift_with_base_score_0p5=float(np.abs((m2 - m64) - 0.5).max()),
                         unfolded_export_refused=unfolded_refused,
                         folded_trees=ff.ntrees, folded_max_abs_raw_minus_margin=float(np.abs(ff.raw(X) - m2).max()),
                         folded_exactness_max_abs_raw_minus_double_leaf_sum_plus_0p5=float(np.abs(ff.raw(X) - (sum_double + 0.5)).max()),
                         folded_rows_beyond_1em5_x_max_1_absmargin=int((np.abs(ff.raw(X) - m2) > 1e-5 * np.maximum(1.0, np.abs(m2))).sum()),
                         objective_logistic_refused=obj_refused),
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    for k in ('--tables', '--tag', '--dev-models', '--out-root', '--summary-out'):
        ap.add_argument(k, required=True)
    ap.add_argument('--models', nargs='+', default=['numu', 'ncpi0'])
    a = ap.parse_args()
    import xgboost as xgb
    res = dict(label=LABEL, exporter=export_tmva.EXPORTER, exporter_version=export_tmva.EXPORTER_VERSION,
               evaluator='sp_retrain.tmva_grad.GradForest', packages=devtrain.package_versions(), models={})
    for s in a.models:
        r = run_model(s, a, xgb)
        res['models'][r['classifier']] = r
        e = r['equivalence']
        print('%s: rows %d  max|m-raw| %.3g  max|ds| %.3g  leaf mismatches %d  flips %s  eq %s' % (
            r['classifier'], r['rows']['test'], e['max_abs_margin_minus_xml_raw'], e['max_abs_score_native_minus_score_xml'],
            e['tree_leaf_mismatches'], [t['flips_score'] for t in r['thresholds']], r['equality_boundary']))
        print('   exact(double leaf sum vs xml) %.3g  f32 tree-order sum vs xgb margin %.3g  rows>1e-5 %d (min|m| %s)  adversarial flips %d' % (
            e['exporter_exactness_max_abs_xml_raw_minus_double_native_leaf_sum'], e['float32_tree_order_leaf_sum_minus_xgboost_margin_max_abs'],
            e['rows_abs_margin_diff_gt_1em5'], e['min_abs_margin_of_rows_gt_1em5'], r['adversarial_threshold']['flips_score']))
    res['all_pass'] = all(
        r['equivalence']['exporter_exactness_max_abs_xml_raw_minus_double_native_leaf_sum'] == 0.0
        and r['equivalence']['rows_beyond_1em5_x_max_1_absmargin'] == 0 and r['equivalence']['tree_leaf_mismatches'] == 0
        and all(t['flips_score'] == 0 and t['flips_raw_margin'] == 0 for t in r['thresholds'])
        and r['equality_boundary']['rows_all_trees_identical'] == r['equality_boundary']['rows_exercised']
        and r['equality_boundary']['rows_routed_right_at_equality_both'] == r['equality_boundary']['rows_exercised']
        and r['extreme_values']['tree_leaf_mismatches'] == 0 and r['order_guard']['refused_by_GradForest']
        and r['base_margin']['unfolded_export_refused'] and r['base_margin']['objective_logistic_refused']
        and r['base_margin']['folded_exactness_max_abs_raw_minus_double_leaf_sum_plus_0p5'] == 0.0
        and r['base_margin']['folded_rows_beyond_1em5_x_max_1_absmargin'] == 0
        and r['nan_behaviour']['tmva_response_minus999'] == r['nan_behaviour']['synthetic_rows']
        for r in res['models'].values())
    os.makedirs(os.path.dirname(os.path.abspath(a.summary_out)), exist_ok=True)
    with open(a.summary_out, 'w') as f:
        json.dump(res, f, indent=1)
    print('all_pass', res['all_pass'])


if __name__ == '__main__':
    main()
