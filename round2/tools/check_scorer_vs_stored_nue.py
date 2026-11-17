#!/usr/bin/env python3
"""Scorer-equivalence check of sp_retrain.tmva_grad against the Wire-Cell toolkit, on real merged CAFs.

Re-scores the shipped nu_e final model (XGB_nue_seed2_0923.xml, TMVA BDT XML BoostType=Grad, 258 inputs) from the
merged-CAF branches with sp_retrain.tmva_grad (float32 inputs, TMVA routing, tanh, log10-odds, float32 store, -15 when
br_filled == 0) and compares with the nue_score the toolkit wrote (UbooneNueBDTScorer). Bit-identical agreement on
every candidate is the pass criterion. It validates the production-side arithmetic that the single-photon models use.

  python check_scorer_vs_stored_nue.py --xml XGB_nue_seed2_0923.xml --out result.json caf1.root [caf2.root ...]
"""
import argparse, json, os, sys, time

import numpy as np
import uproot

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sp_retrain import tmva_grad  # noqa: E402


def flat(a):
    return np.concatenate([np.asarray(x) for x in a]) if len(a) else np.array([])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--xml', required=True); ap.add_argument('--out', required=True); ap.add_argument('files', nargs='+')
    a = ap.parse_args()
    t0 = time.time()
    forest = tmva_grad.GradForest(a.xml)
    parse_s = time.time() - t0
    per_file, Xs, brs, stored = [], [], [], []
    for p in a.files:
        t = uproot.open(p)['recTreeWireCell']
        want = {n: ('wc.T_kine.' if n == 'kine_reco_Enu' else 'wc.T_tagger.') + n for n in forest.names}
        arr = t.arrays(list(want.values()) + ['wc.T_tagger.br_filled', 'wc.T_tagger.nue_score'], library='np')
        X = np.column_stack([flat(arr[want[n]]).astype(np.float32) for n in forest.names])
        b = flat(arr['wc.T_tagger.br_filled']).astype(int); s = flat(arr['wc.T_tagger.nue_score']).astype(np.float32)
        Xs.append(X); brs.append(b); stored.append(s)
        per_file.append(dict(file=os.path.basename(p), candidates=int(len(b)), br_filled=int((b == 1).sum())))
    X = np.concatenate(Xs); br = np.concatenate(brs); s = np.concatenate(stored)
    ours = tmva_grad.log10_odds(forest.evaluate_mva(X)).astype(np.float32)
    ours = np.where(br == 1, ours, np.float32(-15.0)).astype(np.float32)
    same = ours == s
    res = dict(xml=os.path.abspath(a.xml), xml_creator=forest.info.get('Creator'), ntrees=forest.ntrees, nvars=len(forest.names),
               boost_weights_all_one=bool(np.all(forest.boost_weights == 1.0)), parse_seconds=round(parse_s, 1),
               files=len(a.files), candidates=int(len(s)), br_filled=int((br == 1).sum()), bit_identical=int(same.sum()),
               max_abs_diff=float(np.max(np.abs(ours.astype(np.float64) - s))) if len(s) else 0.0,
               rows_with_nan_input=int(np.isnan(X).any(axis=1).sum()), per_file=per_file)
    res['pass'] = bool(len(s) > 0 and same.all())
    json.dump(res, open(a.out, 'w'), indent=1)
    print(json.dumps({k: v for k, v in res.items() if k != 'per_file'}))
    return 0 if res['pass'] else 1


if __name__ == '__main__':
    sys.exit(main())
