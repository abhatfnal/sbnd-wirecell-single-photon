#!/usr/bin/env python3
"""Join the chain-emulated upstream re-scoring (tools/upstream_rescore.py) to the SP development tables of one vertex mode
on the full candidate key, and write one overlay per sample (sp_retrain/upstream_overlay.py reads them). The raw tables
are never modified.

Checks (any failure exits non-zero and writes nothing for that sample):
  * key uniqueness on both sides; every development-table row has exactly one re-scored row, and vice versa (counts
    reported);
  * row alignment: the stored upstream values of the development table (19 SP inputs + numu_3_score + nue_score) equal
    the stored values the re-scoring read, float32-exact;
  * value census per new column: NaN, the -999 NaN-input sentinel, the empty-list constants, nue_score -15 / -16.2556;
  * Xuyang's upstream training role of every row (split_v11: 'dev' slice or 'train').

  python tools/build_upstream_overlay.py --mode dv2_split_move --rescore-dir RS --tables DEV_TABLES --tag dev --out-dir OVL
"""
import argparse, json, os, sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from sp_retrain import upstream_chain as uc, upstream_overlay as uo  # noqa: E402

SAMPLES = ['wcl1116-aurora-ncdr', 'wcl1116-aurora-bnb', 'wcl1116-aurora-nuecc', 'wcl1116-fg-beamoff-train']
CHECK = uo.NUMU_SCORES + uo.NUE_L1_SCORES + ['numu_3_score', 'nue_score']
EMPTY = {'numu_1_score': -0.4, 'numu_2_score': -0.1, 'cosmict_10_score': 0.7}
EMPTY.update({m + '_score': uc.L1_SPEC[m]['empty'] for m in uc.L1_NUE})


def census(x, empty=None):
    x = np.asarray(x, np.float32)
    r = dict(n=int(len(x)), nan=int(np.isnan(x).sum()), minus999=int((x == np.float32(-999)).sum()),
             min=float(np.nanmin(x)) if len(x) else None, max=float(np.nanmax(x)) if len(x) else None)
    if empty is not None:
        r['empty_constant'] = int((x == np.float32(empty)).sum())
    return r


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--mode', required=True); ap.add_argument('--rescore-dir', required=True); ap.add_argument('--tables', required=True)
    ap.add_argument('--tag', default='dev'); ap.add_argument('--out-dir', required=True)
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    rep = dict(mode=a.mode, rescore_dir=os.path.abspath(a.rescore_dir), tables=os.path.abspath(a.tables), tag=a.tag, samples={})
    ok_all = True
    for s in SAMPLES:
        R = pd.read_parquet(os.path.join(a.rescore_dir, 'rescore_%s.parquet' % s))
        D = pd.read_parquet(os.path.join(a.tables, 'cands_%s_%s.parquet' % (s, a.tag)), columns=uo.KEY + CHECK + ['is_placeholder'])
        for X in (R, D):
            for k in ('run', 'subrun', 'event', 'cand'):
                X[k] = X[k].astype(np.int64)
            X['sample'] = X['sample'].astype(str); X['file_id'] = X['file_id'].astype(str)
        r = dict(dev_rows=len(D), rescored_rows=len(R), dev_key_unique=bool(not D.duplicated(uo.KEY).any()),
                 rescored_key_unique=bool(not R.duplicated(uo.KEY).any()))
        M = D.merge(R, on=uo.KEY, how='outer', suffixes=('', '_r'), indicator=True)
        r['dev_only'] = int((M._merge == 'left_only').sum()); r['rescored_only'] = int((M._merge == 'right_only').sum())
        B = M[M._merge == 'both']
        r['joined'] = len(B)
        r['alignment_mismatch'] = {c: int((~uo._eq32(B[c], B['stored_' + c])).sum()) for c in CHECK}
        good = r['dev_key_unique'] and r['rescored_key_unique'] and r['dev_only'] == 0 and not any(r['alignment_mismatch'].values())
        r['verdict'] = 'ALIGNED' if good else 'NOT_ALIGNED'
        ok_all &= good
        if good:
            O = B[uo.KEY].copy()
            for c in uo.NUMU_SCORES:
                O['stored_' + c] = B['stored_' + c].to_numpy(np.float32); O['ovl_' + c] = B['r3af_' + c].to_numpy(np.float32)
            for c in uo.NUE_L1_SCORES:
                O['stored_' + c] = B['stored_' + c].to_numpy(np.float32); O['ovl_' + c] = B['nueA2_' + c].to_numpy(np.float32)
            O['stored_nue_score'] = B['stored_nue_score'].to_numpy(np.float32)
            if 'nueA2_nue_score' in B:
                O['ovl_nue_score'] = B['nueA2_nue_score'].to_numpy(np.float32)
            O['numu_cc_flag_stored'] = B['numu_cc_flag'].to_numpy(np.float32)
            O['numu_cc_flag_bdt_r3af'] = B['r3af_numu_cc_flag_bdt'].to_numpy(np.float32)
            if 'r3af_noscale_numu_score' in B:
                for c in uo.NUMU_SCORES:
                    O['diag_noscale_' + c] = B['r3af_noscale_' + c].to_numpy(np.float32)
            O['xn_split_v11'] = uo.xn_split_v11(O['sample'], O['run'], O['subrun'])
            O.to_parquet(uo.overlay_path(a.out_dir, s))
            r['census_new'] = {c: census(O['ovl_' + c], EMPTY.get(c)) for c in uo.NUMU_SCORES + uo.NUE_L1_SCORES}
            r['census_stored'] = {c: census(O['stored_' + c], EMPTY.get(c)) for c in uo.NUMU_SCORES + uo.NUE_L1_SCORES}
            r['changed_rows'] = {c: int((~uo._eq32(O['ovl_' + c], O['stored_' + c])).sum()) for c in uo.NUMU_SCORES + uo.NUE_L1_SCORES}
            r['numu_cc_flag_bdt_turned_off'] = int(((O.numu_cc_flag_stored == 1) & (O.numu_cc_flag_bdt_r3af != 1)).sum())
            r['xn_split_v11'] = O['xn_split_v11'].value_counts().to_dict()
            if 'ovl_nue_score' in O:
                r['nue_score'] = dict(stored_minus15=int((O.stored_nue_score == -15).sum()), new_minus15=int((O.ovl_nue_score == -15).sum()),
                                      new_minus16p2556=int(np.isclose(O.ovl_nue_score, -16.2556, atol=1e-3).sum()))
        rep['samples'][s] = r
        print(s, json.dumps({k: r[k] for k in ('dev_rows', 'rescored_rows', 'joined', 'dev_only', 'rescored_only', 'verdict')}))
    rep['verdict'] = 'ALL_ALIGNED' if ok_all else 'NOT_ALIGNED'
    json.dump(rep, open(os.path.join(a.out_dir, 'overlay_build_%s.json' % a.mode), 'w'), indent=1, default=str)
    sys.exit(0 if ok_all else 1)


if __name__ == '__main__':
    main()
