#!/usr/bin/env python3
"""Validate sp_retrain.build_tables output against the feature lists and against an independent reference build.

  python validate_smoke_tables.py --tables DIR --tag smoke --reference-dir REF_DIR --out result.json

Checks per sample:
  1. every input column of the ncpi0 / other feature lists exists in cands_<sample>_<tag>.parquet;
  2. value-by-value agreement with a reference build of the same files (read-only; e.g. Xuyang's spec_v1 tables):
     key columns joined on (file_id, run, subrun, event, cand); every shared numeric column compared exactly
     (NaN == NaN), partner_kind compared as strings;
  3. the split (sp_retrain.split) is event- and subrun-safe;
  4. truth-ingredient census (pi0 / photon counts) per sample.
"""
import argparse, json, os, sys

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sp_retrain import features, split  # noqa: E402

KEY = ['file_id', 'run', 'subrun', 'event', 'cand']


def compare(ours, ref_path, file_ids):
    schema = pq.read_schema(ref_path)
    shared = [c for c in ours.columns if c in schema.names and c not in KEY + ['sample']]
    ref = pq.read_table(ref_path, columns=KEY + shared, filters=[('file_id', 'in', sorted(file_ids))]).to_pandas()
    for k in ('run', 'subrun', 'event', 'cand'):
        ref[k] = ref[k].astype('int64'); ours = ours.assign(**{k: ours[k].astype('int64')})
    j = ours[KEY + shared].merge(ref, on=KEY, how='outer', suffixes=('', '_ref'), indicator=True)
    out = dict(rows_ours=int(len(ours)), rows_ref=int(len(ref)), matched=int((j._merge == 'both').sum()),
               only_ours=int((j._merge == 'left_only').sum()), only_ref=int((j._merge == 'right_only').sum()),
               shared_columns=len(shared), differing_columns={})
    b = j[j._merge == 'both']
    for c in shared:
        x, y = b[c], b[c + '_ref']
        if not (pd.api.types.is_numeric_dtype(x) and pd.api.types.is_numeric_dtype(y)):
            diff = int((x.astype(str) != y.astype(str)).sum())
        else:
            xv, yv = x.to_numpy(np.float64), y.to_numpy(np.float64)
            diff = int((~((xv == yv) | (np.isnan(xv) & np.isnan(yv)))).sum())
        if diff:
            out['differing_columns'][c] = diff
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--tables', required=True); ap.add_argument('--tag', default='smoke')
    ap.add_argument('--reference-dir', default=None); ap.add_argument('--out', required=True)
    ap.add_argument('--samples', nargs='+', default=['aurora-r2-ncdr', 'aurora-r2-bnb', 'aurora-r2-nuecc'])
    a = ap.parse_args()
    need = {m: features.load(m).columns for m in ('single_photon_ncpi0', 'single_photon_other')}
    res = {}
    for s in a.samples:
        C = pd.read_parquet(os.path.join(a.tables, 'cands_%s_%s.parquet' % (s, a.tag)))
        T = pd.read_parquet(os.path.join(a.tables, 'truth_%s_%s.parquet' % (s, a.tag)))
        r = dict(candidates=int(len(C)), placeholders=int(C.is_placeholder.sum()), truth_rows=int(len(T)))
        r['missing_input_columns'] = {m: [c for c in cols if c not in C.columns] for m, cols in need.items()}
        C['split'] = split.assign(C['sample'], C.run, C.subrun)
        r['split_counts'] = C.split.value_counts().to_dict()
        r['events_subruns_checked'] = list(split.check_event_safe(C))
        r['partner_kind'] = C.partner_kind.value_counts().to_dict()
        r['truth_census'] = dict(nc=int((T.ccnc == 1).sum()), cc=int((T.ccnc == 0).sum()),
                                 n_prim_pi0=T.n_prim_pi0.value_counts().sort_index().to_dict(),
                                 n_prim_gamma=T.n_prim_gamma.value_counts().sort_index().to_dict(),
                                 nc_with_prim_gamma_no_pi0=int(((T.ccnc == 1) & (T.n_prim_gamma >= 1) & (T.n_pi0_all == 0)).sum()))
        if a.reference_dir:
            ref = os.path.join(a.reference_dir, 'cands_%s.parquet' % s)
            if os.path.exists(ref):
                r['reference'] = dict(path=ref, **compare(C.drop(columns=['split']), ref, set(C.file_id)))
        res[s] = r
        print(s, json.dumps({k: v for k, v in r.items() if k not in ('truth_census',)}, default=str)[:900])
    json.dump(res, open(a.out, 'w'), indent=1, default=str)


if __name__ == '__main__':
    main()
