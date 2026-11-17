#!/usr/bin/env python3
"""Re-score the stored T_tagger.numu_score offline from the stored CAF inputs (no training).

  python check_numu_score_offline.py --xml numu_scalars_scores_0923.xml --tables DIR --tag TAG --samples s1 s2 --out OUT.json

The shipped nu_mu final model (TMVA BDT, BoostType Grad, 74 inputs) is evaluated with sp_retrain.tmva_grad on every
non-placeholder candidate of the candidate tables; score = log10((1+v)/(1-v)) cast to float32, compared bit for bit
with the stored numu_score. A full match shows that a final numu_score can be recomputed offline on refreshed CAFs, as
long as its upstream level-1 scores (numu_1/2_score, cosmict_10_score) are the stored ones.
"""
import argparse
import hashlib
import json
import os
import sys

import numpy as np
import pandas as pd

ROUND2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROUND2)
from sp_retrain import tmva_grad  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--xml', required=True); ap.add_argument('--tables', required=True); ap.add_argument('--tag', required=True)
    ap.add_argument('--samples', nargs='+', required=True); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    f = tmva_grad.GradForest(a.xml)          # the XML's own <Variables> order
    names = f.names
    res = dict(model=os.path.basename(a.xml), sha256=hashlib.sha256(open(a.xml, 'rb').read()).hexdigest(), inputs=len(names),
               trees=f.ntrees, upstream_score_inputs=[n for n in names if n.endswith('_score')], evaluator='sp_retrain.tmva_grad', samples={})
    for s in a.samples:
        cols = list(dict.fromkeys(names + ['numu_score', 'is_placeholder']))
        C = pd.read_parquet(os.path.join(a.tables, 'cands_%s_%s.parquet' % (s, a.tag)), columns=cols)
        C = C[C.is_placeholder == 0]
        new = tmva_grad.log10_odds(f.evaluate_mva(C[names].to_numpy(np.float64).astype(np.float32))).astype(np.float32)
        old = C.numu_score.to_numpy(np.float64).astype(np.float32)
        same = new == old
        res['samples'][s] = dict(non_placeholder_candidates=int(len(C)), bit_identical=int(same.sum()),
                                 max_abs_diff=float(np.abs(new.astype(np.float64) - old).max()) if len(C) else 0.0)
        print(s, res['samples'][s])
    json.dump(res, open(a.out, 'w'), indent=1)


if __name__ == '__main__':
    main()
