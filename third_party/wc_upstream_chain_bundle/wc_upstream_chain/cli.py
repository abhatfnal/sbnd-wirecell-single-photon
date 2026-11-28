"""Command line: python -m wc_upstream_chain {verify, fingerprint, score, check-fixture} ...

  verify        --releases <clone>/releases [--head COMMIT]
  fingerprint   --weights-path DIR[:DIR...]
  bundle-fingerprint   (sha256 over the package files: compare with the published value)
  score         --cands C.parquet --objs 'D/objs_{model}_S.parquet' --kind mc|data --weights-path P --out OUT.parquet [--key k1,k2,..]
  check-fixture FIXTURE_DIR --releases <clone>/releases --shipped <wire-cell-data> [--part mc|beamoff_restricted|all]
"""
import argparse
import json
import os
import sys

import numpy as np

from . import spec as S
from .chain import DEFAULT_KEY, UpstreamChain, compare_exact
from .inventory import bundle_fingerprint, chain_fingerprints, identify_route, verify_release


def _read_objs(pattern, models):
    import pandas as pd
    out = {}
    for m in models:
        p = pattern.format(model=m)
        out[m] = pd.read_parquet(p) if os.path.exists(p) else None
    return out


def release_dirs(releases, shipped):
    return [os.path.join(releases, 'nue_round4_ruleA_v2', 'wirecell', 'main'), os.path.join(releases, 'numu_round3af', 'wirecell'), shipped]


def check_fixture(fixture, releases, shipped, part='all'):
    """Re-score every fixture case with this bundle and compare bit for bit with the fixture's expected values:
    chain_release_* (released weights, kind from the case), ship_* (shipped final models on stored level-1 values) and the
    stored CAF values the shipped closure must reproduce. Returns a report dict; 'ok' is True only if every value matches."""
    import pandas as pd
    man = json.load(open(os.path.join(fixture, 'FIXTURE_MANIFEST.json')))
    rel = UpstreamChain(release_dirs(releases, shipped))
    shp = UpstreamChain([shipped])
    rep = dict(fixture=man.get('name'), bundle_expected=man.get('bundle_version'), cases=[], ok=True)
    for case in man['cases']:
        if part != 'all' and case['part'] != part:
            continue
        d = os.path.join(fixture, case['dir'])
        if not os.path.isdir(d):                        # the restricted beam-off part is transferred separately
            rep['cases'].append(dict(case=case['dir'], absent=True)); continue
        C = pd.read_parquet(os.path.join(d, 'cands.parquet'))
        O = _read_objs(os.path.join(d, 'objs_{model}.parquet'), S.L1_ALL)
        E = pd.read_parquet(os.path.join(d, 'expected_upstream.parquet'))
        key = case['key']
        r = rel.score(C, O, kind=case['kind'], key=key)
        cmp_rel = compare_exact(r.rename(columns={c: 'chain_release_' + c for c in S.UPSTREAM_OUTPUTS}), E,
                                ['chain_release_' + c for c in S.UPSTREAM_OUTPUTS], key=key)
        s = shp.score(C, O, kind=case['kind'], key=key, stored_l1=True)
        cmp_ship = compare_exact(s.rename(columns={'numu_score': 'ship_numu_score', 'nue_score': 'ship_nue_score'}), E,
                                 ['ship_numu_score', 'ship_nue_score'], key=key)
        stored = compare_exact(s.rename(columns={'numu_score': 'stored_numu_score', 'nue_score': 'stored_nue_score'}), E,
                               ['stored_numu_score', 'stored_nue_score'], key=key)
        ok = all(v['exact'] == v['n'] for blk in (cmp_rel, cmp_ship, stored) for v in blk.values())
        rep['cases'].append(dict(case=case['dir'], kind=case['kind'], candidates=int(len(C)), ok=ok,
                                 release_mismatching=[k for k, v in cmp_rel.items() if v['exact'] != v['n']],
                                 shipped_closure_mismatching=[k for k, v in {**cmp_ship, **stored}.items() if v['exact'] != v['n']]))
        rep['ok'] &= ok
    return rep


def main(argv=None):
    ap = argparse.ArgumentParser(prog='python -m wc_upstream_chain', description='toolkit-equivalent upstream tagger scoring')
    sub = ap.add_subparsers(dest='cmd', required=True)
    v = sub.add_parser('verify'); v.add_argument('--releases', required=True); v.add_argument('--head')
    f = sub.add_parser('fingerprint'); f.add_argument('--weights-path', required=True)
    sub.add_parser('bundle-fingerprint')
    s = sub.add_parser('score')
    s.add_argument('--cands', required=True); s.add_argument('--objs', required=True, help="pattern with {model}")
    s.add_argument('--kind', required=True, choices=['mc', 'data']); s.add_argument('--weights-path', required=True)
    s.add_argument('--out', required=True); s.add_argument('--key', default=','.join(DEFAULT_KEY))
    s.add_argument('--no-nue-final', action='store_true'); s.add_argument('--stored-l1', action='store_true')
    c = sub.add_parser('check-fixture'); c.add_argument('fixture'); c.add_argument('--releases', required=True)
    c.add_argument('--shipped', required=True); c.add_argument('--part', default='all', choices=['all', 'mc', 'beamoff_restricted'])
    a = ap.parse_args(argv)
    if a.cmd == 'verify':
        r = verify_release(a.releases, a.head)
        print(json.dumps(r, indent=1)); return 0 if r['ok'] else 1
    if a.cmd == 'fingerprint':
        route, fp = identify_route(a.weights_path)
        print(json.dumps(dict(route=route, fingerprints=fp, lines={k: v[1] for k, v in chain_fingerprints(a.weights_path).items()}), indent=1))
        return 0
    if a.cmd == 'bundle-fingerprint':
        from . import __version__
        fp, lines = bundle_fingerprint()
        print(json.dumps(dict(version=__version__, bundle_fingerprint=fp, files=lines), indent=1)); return 0
    if a.cmd == 'score':
        import pandas as pd
        if os.path.exists(a.out):
            print('refusing to overwrite %s' % a.out, file=sys.stderr); return 2
        C = pd.read_parquet(a.cands); O = _read_objs(a.objs, S.L1_ALL)
        uc = UpstreamChain(a.weights_path, nue_final=not a.no_nue_final)
        r = uc.score(C, O, kind=a.kind, key=a.key.split(','), stored_l1=a.stored_l1)
        prov = r.attrs.pop('provenance')
        r.to_parquet(a.out, index=False)
        json.dump(prov, open(a.out + '.provenance.json', 'w'), indent=1)
        print(json.dumps(dict(out=a.out, candidates=len(r), sim_dqdx_scale_applied=prov['sim_dqdx_scale_applied']))); return 0
    if a.cmd == 'check-fixture':
        r = check_fixture(a.fixture, a.releases, a.shipped, a.part)
        print(json.dumps(r, indent=1)); return 0 if r['ok'] else 1
    return 2


if __name__ == '__main__':
    sys.exit(main())
