#!/usr/bin/env python3
"""Does the thesis Fig. E.4 F-score vector equal the split counts of a prefix of the frozen SP-nue XML? (no training)

  python nue_prefix_test.py --xml single_photon_nue_bdt_final.xml --transcription fig_E4_nue_fscore_transcription.csv --out OUT.json

For N = 1 ... NTrees, the per-variable split counts of the first N trees are compared with the thesis vector (the XGBoost
'weight' = number of splits, thesis caption). The two _calc names are aliases of the stored branches.
"""
import argparse
import csv
import json
import os
import sys

import numpy as np

ROUND2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROUND2)
from sp_retrain import features, tmva_grad  # noqa: E402

ALIAS = {'shw_sp_n_20br1_showers_calc': 'shw_sp_n_20br1_showers', 'shw_sp_vec_mean_dedx_calc': 'shw_sp_vec_mean_dedx'}


def split_counts_per_tree(f):
    M = np.zeros((f.ntrees, len(f.names)), int)
    for t, r in enumerate(f.roots):
        st = [int(r)]
        while st:
            k = st.pop()
            if not f.leaf[k]:
                M[t, f.ivar[k]] += 1
                st += [int(f.left[k]), int(f.right[k])]
    return M


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--xml', required=True); ap.add_argument('--transcription', required=True); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    names = features.load('single_photon_nue').names
    f = tmva_grad.GradForest(a.xml, expected_names=names)
    cum = np.cumsum(split_counts_per_tree(f), 0)
    th = np.zeros(len(names), int)
    for r in csv.DictReader(open(a.transcription)):
        th[names.index(ALIAS.get(r['thesis_name'], r['thesis_name']))] = int(r['thesis_fscore'])
    dist = np.abs(cum - th).sum(1)
    exact = [int(n) + 1 for n in np.flatnonzero(dist == 0)]
    res = dict(xml=os.path.basename(a.xml), trees=f.ntrees, inputs=len(names), thesis_total=int(th.sum()), xml_total=int(cum[-1].sum()),
               best_prefix_N=int(dist.argmin()) + 1, best_l1_distance=int(dist.min()), exact_prefixes=exact,
               l1_distance_at_300=int(dist[-1]))
    json.dump(res, open(a.out, 'w'), indent=1)
    print(json.dumps(res))


if __name__ == '__main__':
    main()
