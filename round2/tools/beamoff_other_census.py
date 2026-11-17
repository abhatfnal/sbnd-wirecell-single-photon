#!/usr/bin/env python3
"""SP-other readiness census of a beam-off (EXT-like) sample: CENSUS ONLY, nothing is trained, no training table is written.

  python beamoff_other_census.py --list LIST.tsv --root DIR --out census.json --nproc N --approved-by TEXT

Reads each merged CAF with sp_retrain.build_tables.extract (the same per-candidate extraction as the training tables)
and writes AGGREGATES only. The training firewall (sp_retrain.firewall) is deliberately not applied: the input is the
fg1 beam-off training half in Xuyang's area, an official-production sample that the Round-2 rule keeps out of
training unless a spec approves it. --approved-by records who asked for this read-only census.

Every candidate of genuine beam-off data is background (Yandel p.129: EXT is always background). Split: run % 4 == 1
is the test quarter, the rest train (Xuyang spec_v1 sec. 6; every beam-off file has subrun 1).
"""
import argparse
import hashlib
import json
import os
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

ROUND2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROUND2)
from sp_retrain import build_tables, features, labels  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--list', required=True); ap.add_argument('--root', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--nproc', type=int, default=8); ap.add_argument('--approved-by', required=True)
    ap.add_argument('--sample', default='fg1-beam-off-train')
    a = ap.parse_args()
    L = pd.read_csv(a.list, sep='\t', comment='#')
    hold = (L.holdout.astype(int) == 1) | (L.holdout_file.astype(int) == 1) | (L.holdout_events.astype(int) > 0)   # Xin's hold-out (14 files)
    use = L[~hold]
    jobs = [(os.path.join(a.root, c), a.sample, fid, 0) for c, fid in zip(use.caf, use.file_id)]
    with Pool(a.nproc) as p:
        res = p.map(build_tables._worker, jobs, chunksize=4)
    F = pd.DataFrame([r[0] for r in res])
    C = pd.DataFrame([c for r in res for c in r[1]])
    names = features.load('single_photon_other').columns
    pre = labels.preselection(C) if len(C) else np.zeros(0, bool)
    have = [n for n in names if n in C.columns]
    X = C[have].to_numpy(np.float64) if len(C) else np.zeros((0, len(have)))
    finite = np.isfinite(X).all(1)
    split = np.where(C.run.to_numpy() % 4 == 1, 'test', 'train') if len(C) else np.array([])
    usable = pre & finite & (len(have) == len(names))
    runs = sorted(set(L.run.astype(int)))
    out = dict(
        label='CENSUS ONLY (no training): SP-other readiness of a beam-off sample', approved_by=a.approved_by,
        firewall_note='training firewall not applied: read-only census of the fg1 beam-off TRAINING half; no training table written',
        list=os.path.abspath(a.list), list_sha256=hashlib.sha256(open(a.list, 'rb').read()).hexdigest(), root=os.path.abspath(a.root),
        list_files=int(len(L)), holdout_files_dropped=int(hold.sum()), files_used=int(len(use)),
        runs=dict(n=len(runs), min=min(runs), max=max(runs), all_odd=all(r % 2 == 1 for r in runs)),
        files_read=int((F.get('error', pd.Series([''] * len(F))).fillna('') == '').sum()),
        file_errors=F[F.get('error', pd.Series([''] * len(F))).fillna('') != ''][['file_id', 'error']].to_dict('records'),
        wct_versions=sorted(F.wct_version.fillna('').unique().tolist()), ismc=sorted(F.ismc.dropna().astype(int).unique().tolist()),
        events=int(F.events.sum()), wc_events=int(F.wc_events.sum()), candidates=int(len(C)),
        placeholders=int(C.is_placeholder.sum()) if len(C) else 0,
        non_placeholder=int((C.is_placeholder == 0).sum()) if len(C) else 0,
        br_filled_1=int((C.get('br_filled', pd.Series(dtype=float)) == 1).sum()),
        shw_sp_filled_1=int((C.get('shw_sp_filled', pd.Series(dtype=float)) == 1).sum()),
        shw_sp_n_20mev_showers_gt0=int((C.get('shw_sp_n_20mev_showers', pd.Series(dtype=float)) > 0).sum()),
        preselected=int(pre.sum()), other_inputs_expected=len(names), other_inputs_present=len(have),
        other_inputs_missing=[n for n in names if n not in C.columns],
        preselected_with_all_inputs_finite=int(usable.sum()),
        preselected_with_nonfinite=int((pre & ~finite).sum()),
        nonfinite_by_input={have[j]: int((pre & ~np.isfinite(X[:, j])).sum()) for j in range(len(have)) if (pre & ~np.isfinite(X[:, j])).any()},
        usable_ext_negative_rows=dict(total=int(usable.sum()), train=int((usable & (split == 'train')).sum()), test=int((usable & (split == 'test')).sum())),
        usable_events=int(C[usable][['run', 'subrun', 'event']].drop_duplicates().shape[0]) if usable.any() else 0,
        partner_kinds=C.partner_kind.value_counts().to_dict() if len(C) else {},
    )
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(out, open(a.out, 'w'), indent=1, default=str)
    print(json.dumps({k: out[k] for k in ('files_used', 'files_read', 'events', 'candidates', 'non_placeholder', 'br_filled_1', 'shw_sp_filled_1',
                                          'preselected', 'other_inputs_present', 'preselected_with_all_inputs_finite', 'usable_ext_negative_rows',
                                          'wct_versions')}))


if __name__ == '__main__':
    main()
