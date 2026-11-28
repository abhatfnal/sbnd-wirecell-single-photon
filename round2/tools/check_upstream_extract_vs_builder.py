#!/usr/bin/env python3
"""Column-for-column equivalence of tools/extract_upstream_inputs.py against Xuyang Ning's spec_v1 table builder
(Ningclover/sbnd-wirecell-bdt tables/build_tables.py, run unmodified except for the Wire-Cell tree name) on the same files.

Compares, on the candidate key: every candidate column both tables hold (the upstream-tagger scalars, the stored
scores, kine_reco_Enu, is_placeholder, n_obj_<model>), and every column of every objs_<model> table. Equality is exact
(NaN == NaN). Our side is restricted to the files Xuyang's table holds (the builder runs on a file subset). Exit
status 1 on any difference.

  python tools/check_upstream_extract_vs_builder.py OURS_DIR OURS_SAMPLE_TAG XNING_DIR XNING_SAMPLE_TAG OUT.json
"""
import json, os, sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from sp_retrain import upstream_chain as uc  # noqa: E402

K = ['file_id', 'run', 'subrun', 'event', 'cand']


def eq(a, b):
    a = pd.to_numeric(a, errors='coerce').to_numpy(np.float64); b = pd.to_numeric(b, errors='coerce').to_numpy(np.float64)
    return (a == b) | (np.isnan(a) & np.isnan(b))


def main():
    od, ot, xd, xt, out = sys.argv[1:6]
    rep = dict(ours=os.path.abspath(od), ours_tag=ot, xning=os.path.abspath(xd), xning_tag=xt, cands={}, objs={})
    A = pd.read_parquet(os.path.join(od, 'cands_%s.parquet' % ot)); B = pd.read_parquet(os.path.join(xd, 'cands_%s.parquet' % xt))
    FB = pd.read_parquet(os.path.join(xd, 'files_%s.parquet' % xt))
    files = set(FB.file_id); rep['xning_files'] = len(files); rep['xning_file_errors'] = int((FB.error != '').sum())
    A = A[A.file_id.isin(files)]
    cols = [c for c in A.columns if c in B.columns and c not in K + ['sample']]
    M = A[K + cols].merge(B[K + cols], on=K, how='outer', suffixes=('_o', '_x'), indicator=True)
    rep['cands'] = dict(ours=len(A), xning=len(B), only_ours=int((M._merge == 'left_only').sum()), only_xning=int((M._merge == 'right_only').sum()),
                        compared_columns=len(cols), ours_columns_not_in_xning=sorted(set(A.columns) - set(B.columns)))
    both = M[M._merge == 'both']
    rep['cands']['differing_columns'] = {c: int((~eq(both[c + '_o'], both[c + '_x'])).sum()) for c in cols if (~eq(both[c + '_o'], both[c + '_x'])).any()}
    for m in uc.L1_ALL:
        pa, pb = os.path.join(od, 'objs_%s_%s.parquet' % (m, ot)), os.path.join(xd, 'objs_%s_%s.parquet' % (m, xt))
        if not (os.path.exists(pa) and os.path.exists(pb)):
            rep['objs'][m] = dict(missing=[p for p in (pa, pb) if not os.path.exists(p)]); continue
        a, b = pd.read_parquet(pa), pd.read_parquet(pb)
        a = a[a.file_id.isin(files)]
        oc = [c for c in a.columns if c in b.columns and c not in K + ['sample', 'index']]
        if len(a) == 0 and len(b) == 0:
            rep['objs'][m] = dict(ours=0, xning=0); continue
        mm = a[K + ['index'] + oc].merge(b[K + ['index'] + oc], on=K + ['index'], how='outer', suffixes=('_o', '_x'), indicator=True)
        bb = mm[mm._merge == 'both']
        rep['objs'][m] = dict(ours=len(a), xning=len(b), only_ours=int((mm._merge == 'left_only').sum()), only_xning=int((mm._merge == 'right_only').sum()),
                              compared_columns=len(oc), differing_columns={c: int((~eq(bb[c + '_o'], bb[c + '_x'])).sum()) for c in oc if (~eq(bb[c + '_o'], bb[c + '_x'])).any()},
                              columns_not_in_other=sorted(set(a.columns) ^ set(b.columns)))
    ok = (rep['cands']['only_ours'] == 0 and rep['cands']['only_xning'] == 0 and not rep['cands']['differing_columns'] and
          all(not v.get('missing') and v.get('only_ours', 0) == 0 and v.get('only_xning', 0) == 0 and not v.get('differing_columns') for v in rep['objs'].values()))
    rep['verdict'] = 'IDENTICAL' if ok else 'DIFFERENT'
    json.dump(rep, open(out, 'w'), indent=1)
    print(json.dumps(dict(verdict=rep['verdict'], cands=rep['cands']['ours'], compared_columns=rep['cands']['compared_columns'],
                          object_rows={m: v.get('ours') for m, v in rep['objs'].items()})))
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
