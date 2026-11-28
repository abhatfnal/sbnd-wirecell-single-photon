#!/usr/bin/env python3
"""Targeted units for the in-chain test, from the offline re-scoring (dv2_split_move): per simulated sample, the first unit
(sorted by file name) holding a candidate on each rare path:
  flagoff   the simulation correction switches the numu_cc_flag BDT copy off (r3af numu_cc_flag_bdt 0, stored 1)
  nan999    a NaN-input object makes a released level-1 value -999 (nu_mu or nu_e)
  nobr      br_filled == 0 but at least one nu_e level-1 value differs from its empty constant (the nu_e level-1 models run
            without the br_filled gate, which the official standalone scorer does not cover)
Writes sample <TAB> unit id <TAB> reason, for tools/pick_chain_test_units.py --targeted.

  python tools/find_targeted_chain_units.py RESCORE_DIR LISTS_DIR OUT.tsv
"""
import os, sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from sp_retrain import upstream_chain as uc  # noqa: E402

S = {'ncdr': 'wcl1116-aurora-ncdr', 'bnb': 'wcl1116-aurora-bnb', 'nuecc': 'wcl1116-aurora-nuecc'}


def main():
    rs, lists, out = sys.argv[1:4]
    rows = []
    for s, sid in S.items():
        unit = {}
        for p in open(os.path.join(lists, sid + '.txt')):
            p = p.strip()
            if p:
                unit[os.path.basename(p)] = os.path.basename(os.path.dirname(os.path.dirname(p)))
        R = pd.read_parquet(os.path.join(rs, 'rescore_%s.parquet' % sid))
        R = R[R.is_placeholder == 0]
        nue = ['nueA2_%s_score' % m for m in uc.L1_NUE]
        masks = dict(flagoff=(R.numu_cc_flag == 1) & (R.r3af_numu_cc_flag_bdt != 1),
                     nan999=(R[['r3af_numu_1_score', 'r3af_numu_2_score', 'r3af_cosmict_10_score'] + nue] == np.float32(-999)).any(axis=1),
                     nobr=(R.br_filled != 1) & np.column_stack([R['nueA2_%s_score' % m] != np.float32(uc.L1_SPEC[m]['empty']) for m in uc.L1_NUE]).any(1))
        for why, q in masks.items():
            f = sorted(R[q].file_id.unique())
            if f:
                rows.append((s, unit[f[0]], '%s (%d candidates in the sample)' % (why, int(q.sum()))))
            print(s, why, int(q.sum()))
    with open(out, 'w') as o:
        o.write('#sample\tunit\treason\n')
        for r in rows:
            o.write('\t'.join(r) + '\n')


if __name__ == '__main__':
    main()
