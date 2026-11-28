#!/usr/bin/env python3
"""SP-level in-chain check: the downstream single-photon feature vectors and BDT predictions built from the in-chain
test CAFs (arm 'new': released upstream weights, simulation correction in the chain) against the same candidates built
from the PRODUCTION tables plus the offline domain-D overlay.

For each test unit and tree, sp_retrain.build_tables.extract reads the test merged CAF (all SP inputs as stored by the
chain); the production side is the SP development table row of the same candidate with domain D applied
(sp_retrain.upstream_overlay). Per SP model: rows matched, rows whose feature vector differs (and which inputs), max
|difference| of the prediction of (a) the domain-D retrained development model and (b) the domain-A fixed development
model and the inherited XML (both on domain-D inputs), and pass/fail changes at the domain-A point A / historical cut.

  python tools/compare_chain_sp_predictions.py --units UNITS.tsv --runs RUNS_DIR --arm new --tables DEV_TABLES_ROOT --tag dev \
      --overlay-root OVL --domain-root DOMAIN --studies-root STUDIES --bundle-root LEGACY --out OUT.json
"""
import argparse, glob, json, os, sys

import numpy as np
import pandas as pd

ROUND2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROUND2); sys.path.insert(0, os.path.join(ROUND2, 'tools'))
from sp_retrain import build_tables as bt, devstudy as dv, features, legacy_control as lc, upstream_overlay as uo  # noqa: E402

SID = {'ncdr': 'wcl1116-aurora-ncdr', 'bnb': 'wcl1116-aurora-bnb', 'nuecc': 'wcl1116-aurora-nuecc'}
TREES = {'dv2_split_move': 'recTreeWireCell', 'dv2_snap': 'recTreeWireCell_dv2snap'}
MODELS = ['numu', 'other', 'ncpi0', 'nue']
KEY = ['sample', 'file_id', 'run', 'subrun', 'event', 'cand']


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    for k in ('--units', '--runs', '--arm', '--tables', '--tag', '--overlay-root', '--domain-root', '--studies-root', '--bundle-root', '--out'):
        ap.add_argument(k, required=True)
    a = ap.parse_args()
    import xgboost as xgb
    units = [l.rstrip('\n').split('\t') for l in open(a.units) if l.strip() and not l.startswith('#')]
    rep = dict(arm=a.arm, modes={})
    for mode, tree in TREES.items():
        test_rows, prod_rows = [], []
        for u in units:
            s, uid = u[0], u[1]
            arms = u[7].split() if len(u) > 7 else []
            if a.arm not in arms:
                continue
            files = glob.glob(os.path.join(a.runs, a.arm, uid, 'merged', '*.wc.flat.caf.root'))
            if not files:
                rep.setdefault('missing_units', []).append(uid); continue
            info, cands, _ = bt.extract(files[0], SID[s], os.path.basename(files[0]), False, tree)
            test_rows += cands
        T = pd.DataFrame(test_rows)
        R = {}
        if not len(T):
            rep['modes'][mode] = dict(error='no test rows'); continue
        for sid in sorted(set(T['sample'])):
            P = pd.read_parquet(os.path.join(a.tables, mode, 'cands_%s_%s.parquet' % (sid, a.tag)))
            P = P[P.file_id.isin(set(T[T['sample'] == sid].file_id))]
            prod_rows.append(uo.apply(P, 'D', os.path.join(a.overlay_root, mode)))
        P = pd.concat(prod_rows, ignore_index=True)
        M = T.merge(P, on=KEY, how='inner', suffixes=('_t', '_p'))
        R['rows'] = dict(test=len(T), production=len(P), matched=len(M))
        for m in MODELS:
            clf = 'single_photon_' + m; cols = features.load(clf).columns
            Xt = M[[c + '_t' for c in cols]].to_numpy(np.float64).astype(np.float32)
            Xp = M[[c + '_p' for c in cols]].to_numpy(np.float64).astype(np.float32)
            fin = np.isfinite(Xt).all(1) & np.isfinite(Xp).all(1)
            diff = ~((Xt == Xp) | (np.isnan(Xt) & np.isnan(Xp)))
            r = dict(rows=int(len(M)), finite_rows=int(fin.sum()), rows_feature_vector_differs=int(diff.any(1).sum()),
                     inputs_differing={cols[j]: int(diff[:, j].sum()) for j in np.flatnonzero(diff.any(0))})
            dom = 'B' if m in ('numu', 'other') else ('C' if m == 'ncpi0' else 'A')
            for name, path in (('retrained_domainD', os.path.join(a.domain_root, mode, 'RETRAINED_%s_%s_%s.json' % (m, mode, dom))),
                               ('fixed_domainA', os.path.join(a.studies_root, mode, m, 'FIT_BASELINE_%s_%s.json' % (m, mode)))):
                b = xgb.Booster(); b.load_model(path)
                st, sp = dv.margin(xgb, b, Xt[fin], cols), dv.margin(xgb, b, Xp[fin], cols)
                r[name] = dict(max_abs=float(np.abs(st - sp).max()) if fin.any() else 0.0, exact=int((st == sp).sum()))
            lt, lp = dv.legacy_scores(a.bundle_root, clf, Xt[fin], cols), dv.legacy_scores(a.bundle_root, clf, Xp[fin], cols)
            cut = lc.LEGACY_CUT[clf]
            r['legacy_xml'] = dict(max_abs=float(np.abs(lt - lp).max()) if fin.any() else 0.0, pass_changes=int(((lt > cut) != (lp > cut)).sum()))
            R[m] = r
        rep['modes'][mode] = R
        print(mode, json.dumps({k: (v if k == 'rows' else {x: v[x] for x in ('rows_feature_vector_differs', 'retrained_domainD', 'legacy_xml')}) for k, v in R.items()}))
    json.dump(rep, open(a.out, 'w'), indent=1)


if __name__ == '__main__':
    main()
