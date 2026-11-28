#!/usr/bin/env python3
"""Pick the production units of the small in-chain test (pre-registered rule, written before any in-chain result):
  * per sample, the units of the development list in increasing sha256("upstream_r4_chain_test|<sample>|<unit id>"),
    keeping the first N with a complete production unit (status OK, both merged trees validated, kept step-1 tars);
  * plus targeted units (--targeted FILE: unit ids chosen from the offline re-scoring because they exercise a rare path:
    a numu_cc_flag copy switched off by the simulation correction, a NaN-input object (-999), a pio_2 gate);
  * per arm list: ctl and new for every unit; noscale for the first unit of each sample; gate (reality=data) and
    prodbuild for the first NC Delta unit, prodbuild also for the first BNB unit.
Writes units.tsv for chain_test_node.sh: sample id reality reco1 caf nev produnitdir arms.

  python tools/pick_chain_test_units.py --lists DIR --pairs-root PROD --n ncdr=3 bnb=2 nuecc=3 [--targeted F] --out units.tsv
"""
import argparse, hashlib, json, os

SAMPLE_IDS = {'ncdr': 'wcl1116-aurora-ncdr', 'bnb': 'wcl1116-aurora-bnb', 'nuecc': 'wcl1116-aurora-nuecc'}


def h(s, u):
    return hashlib.sha256(('upstream_r4_chain_test|%s|%s' % (s, u)).encode()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--lists', required=True); ap.add_argument('--pairs-root', required=True)
    ap.add_argument('--n', nargs='+', default=['ncdr=3', 'bnb=2', 'nuecc=3']); ap.add_argument('--targeted'); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    n = {k: int(v) for k, v in (x.split('=') for x in a.n)}
    targeted = {}
    if a.targeted:
        for l in open(a.targeted):
            if l.strip() and not l.startswith('#'):
                s, u, why = l.rstrip('\n').split('\t')[:3]; targeted[(s, u)] = why
    rows, log = [], dict(rule='sha256("upstream_r4_chain_test|<sample>|<unit>") ascending, first N complete units', n=n, picked={}, targeted={})
    for s, sid in SAMPLE_IDS.items():
        pairs = {}
        for l in open(os.path.join(a.pairs_root, '%s-pairs.tsv' % s)):
            if l.startswith('#') or not l.strip():
                continue
            f = l.rstrip('\n').split('\t'); pairs[f[0]] = f
        units = {}
        for p in open(os.path.join(a.lists, '%s.txt' % sid)):
            p = p.strip()
            if p:
                d = os.path.dirname(os.path.dirname(p)); units[os.path.basename(d)] = d
        order = sorted(units, key=lambda u: h(s, u))
        chosen = []
        for u in order:
            d = units[u]
            ok = (open(os.path.join(d, 'status')).read().strip() == 'OK' and os.path.exists(os.path.join(d, 'validate.json')) and
                  os.path.exists(os.path.join(d, 'validate-pr-dv2snap.json')) and any(os.path.exists(os.path.join(d, 'ql', t, 'qlpctree.tar.gz')) for t in os.listdir(os.path.join(d, 'ql'))))
            if ok and u in pairs:
                chosen.append(u)
            if len(chosen) >= n.get(s, 0):
                break
        extra = [u for (ss, u) in targeted if ss == s and u in units and u not in chosen]
        log['picked'][s] = chosen; log['targeted'][s] = {u: targeted[(s, u)] for u in extra}
        for i, u in enumerate(chosen + extra):
            arms = ['ctl', 'new']
            if i == 0:
                arms.append('noscale')
                if s == 'ncdr':
                    arms += ['gate', 'prodbuild']
                if s == 'bnb':
                    arms.append('prodbuild')
            f = pairs[u]
            rows.append([s, u, f[1], f[2], f[3], f[4] if len(f) > 4 else '', units[u], ' '.join(arms)])
    with open(a.out, 'w') as o:
        o.write('#sample\tid\treality\treco1\tcaf\tnev\tprodunitdir\tarms\n')
        for r in rows:
            o.write('\t'.join(r) + '\n')
    json.dump(log, open(a.out + '.json', 'w'), indent=1)
    print(json.dumps(log['picked']), json.dumps(log['targeted']))


if __name__ == '__main__':
    main()
