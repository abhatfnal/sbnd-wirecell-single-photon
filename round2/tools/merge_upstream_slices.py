#!/usr/bin/env python3
"""Concatenate the slice outputs of tools/extract_upstream_inputs.py (cands_ / objs_ / files_<sample>_<tag>.parquet) into
cands_<sample>.parquet etc., the names the release scorers read. Refuses on a duplicated candidate key or a missing slice.

  python tools/merge_upstream_slices.py DIR SAMPLE TAG [TAG ...]
"""
import json, os, sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from sp_retrain import upstream_chain as uc  # noqa: E402


def main():
    d, sample, tags = sys.argv[1], sys.argv[2], sys.argv[3:]
    rep = dict(sample=sample, tags=tags, slices=[])
    for kind in ['files', 'cands'] + ['objs_%s' % m for m in uc.L1_ALL]:
        parts = []
        for t in tags:
            p = os.path.join(d, '%s_%s_%s.parquet' % (kind, sample, t))
            if not os.path.exists(p):
                sys.exit('missing slice %s' % p)
            parts.append(pd.read_parquet(p))
        X = pd.concat([x for x in parts if len(x)], ignore_index=True) if any(len(x) for x in parts) else parts[0]
        if kind == 'cands' and X.duplicated(['sample'] + uc.KEY).any():
            sys.exit('duplicated candidate key in %s' % sample)
        X.to_parquet(os.path.join(d, '%s_%s.parquet' % (kind, sample)))
        rep['slices'].append(dict(kind=kind, rows=len(X)))
    for t in tags:
        rep.setdefault('extract', []).append(json.load(open(os.path.join(d, 'extract_%s_%s.json' % (sample, t)))))
    F = pd.read_parquet(os.path.join(d, 'files_%s.parquet' % sample))
    rep['files'] = len(F); rep['errors'] = int((F.error != '').sum()); rep['wct_versions'] = sorted(set(F.wct_version.dropna()))
    json.dump(rep, open(os.path.join(d, 'merge_%s.json' % sample), 'w'), indent=1)
    print(json.dumps({k: rep[k] for k in ('sample', 'files', 'errors', 'wct_versions')} | {'rows': rep['slices'][:2]}))


if __name__ == '__main__':
    main()
