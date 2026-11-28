#!/usr/bin/env python3
"""Summarize the in-chain test (tools/chain_test_compare.sh outputs) into one committed JSON.

Per arm: units, events and candidates compared; the union of differing branches per tree (expected: the version
stamp for every arm built from our patched toolkit; the released upstream scores for new / noscale / gate); score parity
(chain vs emulation of the same inputs) per tree and sample; the shipped final-model closure on the ctl / prodbuild
outputs; the SP-level comparison of the new arm.

  python tools/summarize_chain_test.py COMPARE_DIR UNITS.tsv OUT.json
"""
import glob, json, os, re, sys
from collections import defaultdict


def main():
    d, units_tsv, out = sys.argv[1:4]
    units = {l.split('\t')[1]: l.split('\t')[0] for l in open(units_tsv) if l.strip() and not l.startswith('#')}
    rep = dict(compare_dir=d, arms={})
    for f in sorted(glob.glob(os.path.join(d, 'branches_*.json'))):
        arm, uid = re.match(r'branches_([a-z]+)_(.+)\.json', os.path.basename(f)).groups()
        r = json.load(open(f))
        a = rep['arms'].setdefault(arm, dict(units=0, units_by_sample=defaultdict(int), verdicts=defaultdict(int), differing_union={}, changed_scores_union={},
                                             entries={}, branches_compared={}, identical_branches_min={}))
        a['units'] += 1; a['units_by_sample'][units.get(uid, '?')] += 1; a['verdicts'][r['verdict']] += 1
        for t, tr in r['trees'].items():
            a['differing_union'].setdefault(t, set()).update(tr.get('differing', {}).keys())
            a['entries'][t] = a['entries'].get(t, 0) + tr.get('entries', {}).get('test', 0)
            a['branches_compared'][t] = max(a['branches_compared'].get(t, 0), tr.get('branches_compared', 0))
            a['identical_branches_min'][t] = min(a['identical_branches_min'].get(t, 10 ** 9), tr.get('identical', 0))
        for t, s in r['changed_scores'].items():
            a['changed_scores_union'].setdefault(t, set()).update(s)
    for a in rep['arms'].values():
        a['units_by_sample'] = dict(a['units_by_sample']); a['verdicts'] = dict(a['verdicts'])
        a['differing_union'] = {t: sorted(v) for t, v in a['differing_union'].items()}
        a['changed_scores_union'] = {t: sorted(v) for t, v in a['changed_scores_union'].items()}
        a['differing_outside_tagger_scores'] = {t: [b for b in v if not (b.startswith('wc.T_tagger.') and b.endswith('_score'))] for t, v in a['differing_union'].items()}
    rep['score_parity'] = {}
    for f in sorted(glob.glob(os.path.join(d, 'scores_*.json'))):
        arm, mode, s = re.match(r'scores_([a-z]+)_(dv2_[a-z_]+?)_(ncdr|bnb|nuecc)\.json', os.path.basename(f)).groups()
        r = json.load(open(f))
        rep['score_parity']['%s %s %s' % (arm, mode, s)] = dict(candidates=r['candidates'], worst=r['worst'],
                                                               numu_score=r['numu']['numu_score'], nue_score=r['nue'].get('nue_score'),
                                                               numu_exact={k: '%d/%d' % (v['exact'], v['n']) for k, v in r['numu'].items()},
                                                               nue_l1_over_1e6=sum(v['over_1e6'] for k, v in r['nue'].items() if k != 'nue_score'))
    rep['shipped_final_closure_on_rerun'] = {}
    for f in sorted(glob.glob(os.path.join(d, 'tables_*', 'rescore_*.json'))):
        arm_mode = os.path.basename(os.path.dirname(f))[len('tables_'):]
        r = json.load(open(f))
        rep['shipped_final_closure_on_rerun']['%s %s' % (arm_mode, r['sample'])] = {c['score']: '%d/%d exact' % (c['exact'], c['n']) for c in r['closure_shipped_final_models']}
    p = os.path.join(d, 'sp_predictions_new.json')
    if os.path.exists(p):
        rep['sp_level_new_arm'] = json.load(open(p))
    json.dump(rep, open(out, 'w'), indent=1, default=lambda o: sorted(o) if isinstance(o, set) else str(o))
    for arm, a in rep['arms'].items():
        print(arm, a['units'], a['units_by_sample'], a['verdicts'], 'outside-tagger-scores:', a['differing_outside_tagger_scores'], 'changed:', {t: len(v) for t, v in a['changed_scores_union'].items()})
    for k, v in rep['score_parity'].items():
        print(k, v['candidates'], 'worst', v['worst'], 'numu pass dis', v['numu_score'].get('pass_disagree'), 'nue pass dis', (v['nue_score'] or {}).get('pass_disagree'))


if __name__ == '__main__':
    main()
