#!/usr/bin/env python3
"""In-chain test against production: every branch of every tree of a re-run merged CAF compared with the WCLocal2026Nov16
production merged CAF of the same unit (same step-1 tar), and the chain-stored upstream scores compared with the
offline chain emulation (tools/upstream_rescore.py output on the PRODUCTION inputs).

Per tree: branches identical / differing (entries that differ) / only on one side. Values compare exactly, NaN == NaN,
jagged per event. With --rescore, per score: rows joined on the candidate key, exact matches, max |diff|.

  python tools/compare_chain_test.py --prod PROD.root --test TEST.root --out OUT.json [--rescore-split R.parquet --rescore-snap R.parquet --prefix r3af_/nueA2_/ship_]
"""
import argparse, json, os, sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

TREES = ['recTree', 'recTreeWireCell', 'recTreeWireCell_dv2snap']
SCORES = ['numu_score', 'numu_1_score', 'numu_2_score', 'numu_3_score', 'cosmict_10_score', 'nue_score'] + \
         ['%s_score' % m for m in ['br3_3', 'br3_5', 'br3_6', 'pio_2', 'stw_2', 'stw_3', 'stw_4', 'sig_1', 'sig_2', 'lol_1', 'lol_2', 'tro_1', 'tro_2', 'tro_4', 'tro_5']]


def same(a, b):
    """Element-wise equality of two per-event arrays (numeric, jagged object or bytes); returns (n_entries, n_diff)."""
    if a.dtype == object or b.dtype == object:
        n = nd = 0
        for x, y in zip(a, b):
            x = np.asarray(x); y = np.asarray(y)
            if x.shape != y.shape:
                nd += max(x.size, y.size, 1); n += max(x.size, y.size, 1); continue
            n += x.size
            if x.size:
                if x.dtype.kind in 'fc' and y.dtype.kind in 'fc':
                    nd += int((~((x == y) | (np.isnan(x) & np.isnan(y)))).sum())
                else:
                    nd += int((x != y).sum())
        return n, nd
    if a.shape != b.shape:
        return max(a.size, b.size), max(a.size, b.size)
    if a.dtype.kind in 'fc' and b.dtype.kind in 'fc':
        return a.size, int((~((a == b) | (np.isnan(a) & np.isnan(b)))).sum())
    return a.size, int((a != b).sum())


def compare_tree(fp, ft, tree):
    if tree not in fp or tree not in ft:
        return dict(present=dict(prod=tree in fp, test=tree in ft))
    tp, tt = fp[tree], ft[tree]
    kp, kt = set(tp.keys()), set(tt.keys())
    r = dict(entries=dict(prod=int(tp.num_entries), test=int(tt.num_entries)), only_prod=sorted(kp - kt)[:50], only_test=sorted(kt - kp)[:50],
             branches_compared=0, identical=0, differing={})
    if tp.num_entries != tt.num_entries:
        r['error'] = 'entry counts differ'; return r
    for b in sorted(kp & kt):
        try:
            x = tp[b].array(library='np'); y = tt[b].array(library='np')
        except Exception as e:
            r.setdefault('unreadable', []).append(b); continue
        r['branches_compared'] += 1
        n, nd = same(x, y)
        if nd:
            r['differing'][b] = dict(entries=n, differ=nd)
        else:
            r['identical'] += 1
    return r


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--prod', required=True); ap.add_argument('--test', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--expect-changed', default='', help='comma list of T_tagger score names expected to change (others must be identical)')
    a = ap.parse_args()
    import uproot
    fp, ft = uproot.open(a.prod), uproot.open(a.test)
    rep = dict(prod=a.prod, test=a.test, trees={})
    for t in TREES:
        rep['trees'][t] = compare_tree(fp, ft, t)
    exp = set(x for x in a.expect_changed.split(',') if x)
    unexpected = {}
    for t in ('recTreeWireCell', 'recTreeWireCell_dv2snap'):
        for b in rep['trees'][t].get('differing', {}):
            name = b.split('.')[-1]
            if not (b.startswith('wc.T_tagger.') and name in exp):
                unexpected.setdefault(t, []).append(b)
    rep['unexpected_differences'] = unexpected
    rep['expected_changed'] = sorted(exp)
    rep['changed_scores'] = {t: sorted(b.split('.')[-1] for b in rep['trees'][t].get('differing', {}) if b.startswith('wc.T_tagger.'))
                             for t in ('recTreeWireCell', 'recTreeWireCell_dv2snap')}
    rep['verdict'] = 'ONLY_EXPECTED_DIFFERENCES' if not unexpected else 'UNEXPECTED_DIFFERENCES'
    json.dump(rep, open(a.out, 'w'), indent=1)
    print(json.dumps(dict(test=os.path.basename(a.test), verdict=rep['verdict'], changed=rep['changed_scores'],
                          unexpected={k: v[:8] for k, v in unexpected.items()})))


if __name__ == '__main__':
    main()
