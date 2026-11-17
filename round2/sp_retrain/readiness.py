#!/usr/bin/env python3
"""Measure whether the Aurora merged-CAF tables carry every input of the single-photon ncpi0 / other BDTs, and how.

  python -m sp_retrain.readiness --tables DIR [--tables-tag TAG] --out-dir OUT --samples s1 s2 ...

Per sample and per input: rows, rows with the single-photon block filled (shw_sp_filled == 1), non-finite fraction
(all rows, filled rows), the modal value on UNFILLED rows (the tagger's default) and its share, and how often a FILLED
row still holds that default. Read-only: only the needed columns are read (pyarrow), placeholders dropped.
Writes readiness_<sample>.csv (one row per model input) and readiness_summary.json.
"""
import argparse, json, os, sys

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sp_retrain import features  # noqa: E402

MODELS = ('single_photon_ncpi0', 'single_photon_other')
GATES = ['shw_sp_filled', 'br_filled', 'is_placeholder', 'shw_sp_n_20mev_showers']


def modal(x):
    x = x[np.isfinite(x)]
    if not len(x):
        return np.nan, 0.0
    v, c = np.unique(x, return_counts=True)
    k = int(np.argmax(c))
    return float(v[k]), float(c[k] / len(x))


def measure(path, inputs):
    have = set(pq.read_schema(path).names)
    cols = sorted({c for c in [i['table_column'] for i in inputs] + GATES if c in have})
    df = pq.read_table(path, columns=cols).to_pandas()
    df = df[df.is_placeholder == 0] if 'is_placeholder' in df else df
    filled = (df.shw_sp_filled == 1).to_numpy()
    gate = dict(rows=int(len(df)), shw_sp_filled=int(filled.sum()),
                shw_sp_filled_and_20mev=int((filled & (df.shw_sp_n_20mev_showers > 0).to_numpy()).sum()),
                br_filled=int((df.br_filled == 1).sum()) if 'br_filled' in df else None)
    rows = []
    for i in inputs:
        c = i['table_column']
        r = dict(model=i['model'], index=i['index'], name=i['name'], table_column=c, caf_branch=i['caf_branch'],
                 caf_type=i['caf_type'], kind=i['kind'], present=c in df)
        if c in df:
            x = df[c].to_numpy(np.float64)
            d, dshare = modal(x[~filled])
            r.update(nonfinite_all=float(np.mean(~np.isfinite(x))) if len(x) else np.nan,
                     nonfinite_filled=float(np.mean(~np.isfinite(x[filled]))) if filled.any() else np.nan,
                     unfilled_modal_value=d, unfilled_modal_share=dshare,
                     filled_equal_to_unfilled_modal=float(np.mean(x[filled] == d)) if filled.any() and np.isfinite(d) else np.nan,
                     filled_min=float(np.nanmin(x[filled])) if filled.any() else np.nan,
                     filled_max=float(np.nanmax(x[filled])) if filled.any() else np.nan)
        rows.append(r)
    return gate, rows


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--tables', required=True, help='directory with cands_<sample>[_<tag>].parquet (read-only)')
    ap.add_argument('--tables-tag', default='')
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--samples', nargs='+', required=True)
    ap.add_argument('--label', default='', help='free text recorded in the summary (e.g. which build the tables are)')
    a = ap.parse_args()
    inputs = []
    for m in MODELS:
        for i in features.load(m).inputs:
            inputs.append(dict(i, model=m))
    os.makedirs(a.out_dir, exist_ok=True)
    summary = dict(label=a.label, tables=os.path.abspath(a.tables), tag=a.tables_tag, samples={})
    for s in a.samples:
        path = os.path.join(a.tables, 'cands_%s%s.parquet' % (s, ('_' + a.tables_tag) if a.tables_tag else ''))
        gate, rows = measure(path, inputs)
        pd.DataFrame(rows).to_csv(os.path.join(a.out_dir, 'readiness_%s.csv' % s), index=False)
        pres = pd.DataFrame(rows)
        gate['inputs_present'] = {m: int(pres[(pres.model == m) & pres.present].shape[0]) for m in MODELS}
        gate['inputs_absent'] = {m: pres[(pres.model == m) & ~pres.present].name.tolist() for m in MODELS}
        gate['max_nonfinite_filled'] = {m: float(pres[(pres.model == m) & pres.present].nonfinite_filled.max()) for m in MODELS}
        summary['samples'][s] = gate
        print(s, json.dumps(gate)[:600])
    json.dump(summary, open(os.path.join(a.out_dir, 'readiness_summary.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
