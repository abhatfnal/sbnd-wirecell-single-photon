#!/usr/bin/env python3
"""Compact summary of the WCL1116 development campaign from its validation JSONs (no training, no new numbers).

  python summarize_wcl1116_dev.py --out validation/wcl1116_dev_summary.json [--markdown OUT.md]
"""
import argparse
import json
import os

ROUND2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V = os.path.join(ROUND2, 'validation')
M = os.path.join(ROUND2, 'manifests', 'wcl1116_dev_v1')
MODES = ('dv2_split_move', 'dv2_snap')


def j(path):
    return json.load(open(path)) if os.path.exists(path) else None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--out', required=True); ap.add_argument('--markdown', default=None)
    a = ap.parse_args()
    out = dict(campaign='development_wcl1116_v1', label='WCL1116 DEVELOPMENT HOLDOUT -- DEV_DO_NOT_DEPLOY; not independent end-to-end', models=[], ceilings={})
    rows = []
    for m in ('numu', 'ncpi0'):
        mc = j(os.path.join(V, 'wcl1116_mode_compare_%s.json' % m))
        for mode in MODES:
            man = j(os.path.join(M, 'single_photon_%s_%s_dev_manifest.json' % (m, mode)))
            if not man or not mc:
                continue
            b = mc['modes'][mode]
            r = dict(model='SP ' + m, vertex_mode=mode, train_pos=b['train_rows']['pos'], train_neg=b['train_rows']['neg'],
                     holdout_pos=b['holdout_rows']['pos'], holdout_neg=b['holdout_rows']['neg'], legacy_auc=b['legacy_holdout_auc'],
                     dev_auc=b['holdout_auc'], train_auc=b['train_auc'], gap=b['train_holdout_gap'], model_sha256=man['model']['sha256'],
                     status='DEV_DO_NOT_DEPLOY; UPSTREAM_NUMU=%s' % (man.get('upstream_numu') or '-'))
            rows.append(r)
        if mc:
            out.setdefault('matched_common_population', {})[m] = mc['matched_common_population']
            out.setdefault('feature_sanity', {})[m] = {mode: mc['modes'][mode]['feature_sanity'] for mode in MODES}
    out['models'] = rows
    mig = j(os.path.join(V, 'wcl1116_migration_study.json'))
    if mig:
        for s, S in mig['samples'].items():
            out['ceilings'][s] = {d: dict(truth_signal=S['reconstruction'][d]['ceiling']['truth_signal_neutrinos'],
                                          with_preselected=S['reconstruction'][d]['ceiling']['with_preselected_frac'],
                                          with_candidate=S['reconstruction'][d]['ceiling']['with_candidate_frac'],
                                          best_dist_lt_1cm=S['reconstruction'][d]['ceiling']['preselected_best_dist_lt_1cm_frac'],
                                          preselected=S['reconstruction'][d]['preselected'])
                                  for d in ('old', 'split', 'snap')}
    for mode in MODES:
        e = j(os.path.join(V, 'wcl1116_export_equivalence_%s.json' % mode))
        if e:
            out.setdefault('export', {})[mode] = dict(all_pass=e.get('all_pass'), models={k: dict(
                max_abs_margin_minus_xml=v['equivalence']['max_abs_margin_minus_xml_raw'],
                exactness=v['equivalence']['exporter_exactness_max_abs_xml_raw_minus_double_native_leaf_sum'],
                flips=[t['flips_score'] for t in v['thresholds']]) for k, v in e['models'].items()})
        lcj = j(os.path.join(V, 'ncpi0_negative_learning_curve_wcl1116_%s.json' % mode))
        if lcj:
            out.setdefault('ncpi0_learning_curve', {})[mode] = dict(result=lcj['result'], reproduces=lcj['reproduces_development_model'],
                                                                   per_fraction=[(p['fraction'], p['neg_rows_mean'], round(p['test_auc_mean'], 4)) for p in lcj['per_fraction']])
    json.dump(out, open(a.out, 'w'), indent=1, default=str)
    if a.markdown:
        L = ['| model | vertex mode | train rows +/- | holdout rows +/- | legacy AUC | dev AUC | status |', '|---|---|---:|---:|---:|---:|---|']
        for r in rows:
            L.append('| %s | %s | %d / %d | %d / %d | %.4f | %.4f | %s |' % (r['model'], r['vertex_mode'], r['train_pos'], r['train_neg'], r['holdout_pos'],
                                                                         r['holdout_neg'], r['legacy_auc'], r['dev_auc'], r['status']))
        open(a.markdown, 'w').write('\n'.join(L) + '\n')
    print(json.dumps(out, indent=1, default=str)[:6000])


if __name__ == '__main__':
    main()
