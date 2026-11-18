#!/usr/bin/env python3
"""SP nue class census on the WCL1116 development tables, per vertex mode (reads tables only; no training).

  python sp_nue_census.py --spec-template specs/single_photon_nue_training_spec_dev_wcl1116_%s.yaml --tag dev \
      --tables-template $SP_WORK/wcl1116_dev_tables/%s --out-json OUT.json

Per sample: events (build summary), non-placeholder candidates, events with >= 1 candidate / >= 1 preselected
candidate / >= 1 nu_e CC negative row, preselected rows, positive and negative rows (sp_retrain.labels.development_classes,
the training definition), the truth class of the preselected rows that are excluded, and non-finite classed rows.
The split is the training split (odd subrun -> development holdout).
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

ROUND2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROUND2)
from sp_retrain import devtrain, features, labels  # noqa: E402

MODES = ('dv2_split_move', 'dv2_snap')
THESIS = dict(negative_events=100958, positive_events=24936, source='Yandel thesis p.133 (training counts of the nu_e CC BDT)')


def census(C, spec, nfeat):
    cls, pre = labels.development_classes(C, spec)
    X = C[nfeat].to_numpy(np.float64)
    fin = np.isfinite(X).all(1)
    sp = np.where(C.subrun.to_numpy() % 2 == 1, 'holdout', 'train')
    ev = C[devtrain.EV].astype(str).agg('|'.join, axis=1).to_numpy()
    use = (cls >= 0) & fin
    out = {}
    for sid in sorted(C['sample'].astype(str).unique()):
        s = (C['sample'].astype(str) == sid).to_numpy()
        ph = s & (C.is_placeholder.to_numpy() == 0)
        exc = s & pre & (cls < 0)
        bkg = C.loc[exc, 'm_sp_bkg'].astype(str).where(C.loc[exc, 'partner_kind'].astype(str) == 'neutrino', 'partner_' + C.loc[exc, 'partner_kind'].astype(str))
        out[sid] = dict(
            candidates=int(ph.sum()), events_with_candidate=int(pd.unique(ev[ph]).size),
            preselected=int((s & pre).sum()), events_with_preselected=int(pd.unique(ev[s & pre]).size),
            positive=dict(rows=int((s & use & (cls == 1)).sum()), train=int((s & use & (cls == 1) & (sp == 'train')).sum()),
                          holdout=int((s & use & (cls == 1) & (sp == 'holdout')).sum()), events=int(pd.unique(ev[s & use & (cls == 1)]).size)),
            negative=dict(rows=int((s & use & (cls == 0)).sum()), train=int((s & use & (cls == 0) & (sp == 'train')).sum()),
                          holdout=int((s & use & (cls == 0) & (sp == 'holdout')).sum()), events=int(pd.unique(ev[s & use & (cls == 0)]).size)),
            excluded_preselected_by_truth={k: int(v) for k, v in bkg.value_counts().items()},
            nonfinite_classed_rows=int((s & (cls >= 0) & ~fin).sum()))
    return out, int(((cls >= 0) & ~fin).sum())


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    for k in ('--spec-template', '--tag', '--tables-template', '--out-json'):
        ap.add_argument(k, required=True)
    a = ap.parse_args()
    nfeat = features.load('single_photon_nue').columns
    res = dict(label='SP nue CENSUS (WCL1116 development tables; no training)', thesis_reference=THESIS, modes={})
    for mode in MODES:
        spec = labels.load_spec(os.path.join(ROUND2, a.spec_template % mode))
        tables = a.tables_template % mode
        ids = [s['id'] for s in spec['samples']['development']]
        C = pd.concat([pd.read_parquet(os.path.join(tables, 'cands_%s_%s.parquet' % (sid, a.tag))) for sid in ids], ignore_index=True)
        events = {sid: json.load(open(os.path.join(tables, 'build_%s_%s.json' % (sid, a.tag))))['events'] for sid in ids}
        per, nonfin = census(C, spec, nfeat)
        for sid in per:
            per[sid]['events'] = events[sid]
            per[sid]['fraction_events_with_negative_row'] = per[sid]['negative']['events'] / events[sid] if events[sid] else None
        tot = lambda cl, k: sum(per[s][cl][k] for s in per)
        res['modes'][mode] = dict(spec_status=spec['status'], samples=ids, per_sample=per, nonfinite_classed_rows=nonfin,
                                  positive=dict(rows=tot('positive', 'rows'), train=tot('positive', 'train'), holdout=tot('positive', 'holdout')),
                                  negative=dict(rows=tot('negative', 'rows'), train=tot('negative', 'train'), holdout=tot('negative', 'holdout')))
        print(mode, json.dumps({k: res['modes'][mode][k] for k in ('positive', 'negative', 'nonfinite_classed_rows')}))
    json.dump(res, open(a.out_json, 'w'), indent=1)


if __name__ == '__main__':
    main()
