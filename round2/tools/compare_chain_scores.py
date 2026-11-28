#!/usr/bin/env python3
"""Chain-stored upstream scores of an in-chain test arm against the offline chain emulation of the SAME inputs.

Input: tools/upstream_rescore.py run on the TEST arm's own merged CAFs (stored_* = what the patched chain stored;
r3af_* / r3af_noscale_* / nueA2_* = the emulation of those inputs). The arm fixes which emulation is the expectation:
  new      nu_mu r3af_* (simulation: x1.071 + flag copy), nu_e nueA2_*
  noscale  nu_mu r3af_noscale_*, nu_e nueA2_*
  gate     nu_mu r3af_* of a --kind data re-scoring (scale forced to 1), nu_e nueA2_*
Per score: rows, exact, max |diff|, rows over 1e-6 / 1e-5, and pass/fail disagreements at the release operating points
(numu_score 0.985, nue_score 3.06; context only).

  python tools/compare_chain_scores.py RESCORE.parquet ARM OUT.json
"""
import json, sys

import numpy as np
import pandas as pd

NUMU = ['numu_1_score', 'numu_2_score', 'cosmict_10_score', 'numu_score']
NUE = ['%s_score' % m for m in ['br3_3', 'br3_5', 'br3_6', 'pio_2', 'stw_2', 'stw_3', 'stw_4', 'sig_1', 'sig_2', 'lol_1', 'lol_2', 'tro_1', 'tro_2', 'tro_4', 'tro_5']] + ['nue_score']


def cmp(s, e):
    s = np.asarray(s, np.float64); e = np.asarray(e, np.float64); d = np.abs(s - e)
    return dict(n=int(len(d)), exact=int((d == 0).sum()), max_abs=float(d.max()) if len(d) else 0.0, over_1e6=int((d > 1e-6).sum()), over_1e5=int((d > 1e-5).sum()))


def main():
    rs, arm, out = sys.argv[1:4]
    R = pd.read_parquet(rs)
    pre = dict(new='r3af_', noscale='r3af_noscale_', gate='r3af_')[arm]
    rep = dict(rescore=rs, arm=arm, candidates=len(R), numu={}, nue={})
    for c in NUMU:
        rep['numu'][c] = cmp(R['stored_' + c], R[pre + c])
    for c in NUE:
        if 'nueA2_' + c in R:
            rep['nue'][c] = cmp(R['stored_' + c], R['nueA2_' + c])
    s, e = R['stored_numu_score'].to_numpy(), R[pre + 'numu_score'].to_numpy()
    rep['numu']['numu_score'].update(pass_chain=int((s > 0.985).sum()), pass_emulated=int((e > 0.985).sum()), pass_disagree=int(((s > 0.985) != (e > 0.985)).sum()))
    if 'nueA2_nue_score' in R:
        s, e = R['stored_nue_score'].to_numpy(), R['nueA2_nue_score'].to_numpy()
        rep['nue']['nue_score'].update(pass_chain=int((s > 3.06).sum()), pass_emulated=int((e > 3.06).sum()), pass_disagree=int(((s > 3.06) != (e > 3.06)).sum()))
    rep['worst'] = dict(numu=max(v['max_abs'] for v in rep['numu'].values()), nue_l1=max(v['max_abs'] for k, v in rep['nue'].items() if k != 'nue_score'),
                        nue_score=rep['nue'].get('nue_score', {}).get('max_abs'))
    json.dump(rep, open(out, 'w'), indent=1)
    print(json.dumps(dict(arm=arm, candidates=len(R), worst=rep['worst'], numu_score=rep['numu']['numu_score'], nue_score=rep['nue'].get('nue_score'))))


if __name__ == '__main__':
    main()
