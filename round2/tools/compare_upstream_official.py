#!/usr/bin/env python3
"""Chain emulation (tools/upstream_rescore.py: the released TMVA XML files evaluated as wire-cell-toolkit 0.38.0 does)
against Xuyang Ning's OFFICIAL standalone release scorers run unmodified on the same tables:
  nu_mu: training/numu/make_corrected_tables.py --update-flag1 (simulation only) + training/numu/score_numu_release.py
         (l1_<model>, d6_f0 = margin; numu_score = 2/ln10 * d6_f0)
  nu_e : release/score_release.py releases/nue_round4_ruleA_v2 (l1_<model> chain-transformed, score = raw margin;
         candidates with is_placeholder == 0 and br_filled == 1 only)
Reports per score: rows joined, max |diff|, rows over 1e-6 / 1e-5, and pass / fail disagreements at the release
operating points (numu_score > 0.985, nue_score > 3.06; quoted for context only, never an SP threshold).

  python tools/compare_upstream_official.py RESCORE.parquet NUMU_OFFICIAL.parquet NUE_OFFICIAL.parquet OUT.json
"""
import json, math, sys

import numpy as np
import pandas as pd

K = ['file_id', 'run', 'subrun', 'event', 'cand']
NUE_L1 = ['br3_3', 'br3_5', 'br3_6', 'pio_2', 'stw_2', 'stw_3', 'stw_4', 'sig_1', 'sig_2', 'lol_1', 'lol_2', 'tro_1', 'tro_2', 'tro_4', 'tro_5']


def diff(a, b):
    a = np.asarray(a, np.float64); b = np.asarray(b, np.float64)
    d = np.abs(a - b)
    return dict(n=int(len(d)), max_abs=float(d.max()) if len(d) else 0.0, over_1e6=int((d > 1e-6).sum()), over_1e5=int((d > 1e-5).sum()),
                exact=int((d == 0).sum()))


def main():
    rs, nm, ne, out = sys.argv[1:5]
    E = pd.read_parquet(rs)
    rep = dict(rescore=rs, numu_official=nm, nue_official=ne)
    N = pd.read_parquet(nm)
    M = E.merge(N, on=['sample'] + K, how='inner')
    rep['numu_rows'] = dict(emulated=len(E), official=len(N), joined=len(M))
    for m in ['numu_1', 'numu_2', 'cosmict_10']:
        rep['numu_' + m] = diff(M['r3af_%s_score' % m], M['l1_' + m])
    off = (2 / math.log(10) * M['d6_f0'].to_numpy(np.float64)).astype(np.float32)
    rep['numu_score'] = diff(M['r3af_numu_score'], off)
    pe, po = M['r3af_numu_score'].to_numpy() > 0.985, off > 0.985
    rep['numu_score'].update(pass_emulated=int(pe.sum()), pass_official=int(po.sum()), pass_disagree=int((pe != po).sum()))
    V = pd.read_parquet(ne)
    M2 = E.merge(V, on=K, how='inner')
    rep['nue_rows'] = dict(official_br_filled=len(V), joined=len(M2), emulated_br_filled_nonplaceholder=int(((E.br_filled == 1) & (E.is_placeholder == 0)).sum()))
    for m in NUE_L1:
        rep['nue_' + m] = diff(M2['nueA2_%s_score' % m], M2['l1_' + m])
    if 'nueA2_nue_score' in M2:
        rep['nue_score'] = diff(M2['nueA2_nue_score'], M2['score'])
        pe, po = M2['nueA2_nue_score'].to_numpy() > 3.06, M2['score'].to_numpy() > 3.06
        rep['nue_score'].update(pass_emulated=int(pe.sum()), pass_official=int(po.sum()), pass_disagree=int((pe != po).sum()))
    rep['nue_l1_worst'] = max(rep['nue_' + m]['max_abs'] for m in NUE_L1)
    json.dump(rep, open(out, 'w'), indent=1)
    print(json.dumps(dict(numu_rows=rep['numu_rows'], numu_score=rep['numu_score'], nue_rows=rep['nue_rows'], nue_l1_worst=rep['nue_l1_worst'],
                          nue_score=rep.get('nue_score'))))


if __name__ == '__main__':
    main()
