#!/usr/bin/env python3
"""Level-1 closure with ROOT TMVA itself (development check of offline sufficiency).

prepare  per level-1 model, the per-object inputs of the extracted tables (tools/extract_upstream_inputs.py) of the given
         samples, in the XML variable order, with the chain's protections (numu_1 dQ_dx_cut +-inf -> 10, cosmict_10
         angle_beam NaN -> 0; NaN otherwise kept so TMVA returns -999), pio_2 restricted to its gate, as float32 binaries,
         for two weight sets: SHIPPED (wire-cell-data 99c6497f) and RELEASE (numu_round3af / nue_round4_ruleA_v2 main;
         numu_1 unscaled). Writes jobs.tsv for the C++ program round2/cpp/upstream_l1_tmva_eval.cxx (run in the SL7
         container).
compare  SHIPPED: pool the TMVA values as the chain does (float32, max / min, empty constants, pio_2 gate) and compare
         with the STORED level-1 scores of EVERY candidate (placeholders, br_filled == 0 and empty lists included).
         RELEASE: per object, TMVA::Reader against the numpy chain evaluator (sp_retrain.tmva_grad.GradForest).

  python tools/upstream_l1_tmva_closure.py prepare --tables T --samples S1 S2 --shipped DIR --numu-release DIR --nue-release DIR --work W
  python tools/upstream_l1_tmva_closure.py compare --tables T --samples S1 S2 --work W --out OUT.json
"""
import argparse, json, os, re, sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from sp_retrain import upstream_chain as uc  # noqa: E402
from sp_retrain.tmva_grad import GradForest  # noqa: E402


def xml_names(path):
    head = open(path, 'rb').read(400000)
    v = sorted((int(i), e.decode()) for i, e in re.findall(rb'<Variable VarIndex="(\d+)" Expression="([^"]*)"', head))
    if not v:   # attribute order differs between writers (as in sp_retrain.tmva_grad)
        v = [(k, e.decode()) for k, e in enumerate(re.findall(rb'<Variable [^>]*Expression="([^"]*)"', head))]
    return [e for _, e in v]


def load(tables, samples):
    C = pd.concat([pd.read_parquet(os.path.join(tables, 'cands_%s.parquet' % s)) for s in samples], ignore_index=True)
    O = {}
    for m in uc.L1_ALL:
        parts = [pd.read_parquet(os.path.join(tables, 'objs_%s_%s.parquet' % (m, s))) for s in samples]
        O[m] = pd.concat([p for p in parts if len(p)], ignore_index=True) if any(len(p) for p in parts) else parts[0]
    return C, O


def objects(m, C, O):
    d = uc.L1_SPEC[m]; names = d['lists'] + d['scalars']
    X = O[m][names].to_numpy(np.float64).astype(np.float32) if len(O[m]) else np.zeros((0, len(names)), np.float32)
    for col, (kind, val) in d.get('protect', {}).items():
        j = names.index(col); bad = np.isinf(X[:, j]) if kind == 'inf' else np.isnan(X[:, j]); X[bad, j] = val
    idx = uc.cand_index(C, O[m]) if len(O[m]) else np.zeros(0, int)
    keep = np.ones(len(X), bool)
    if m == 'pio_2' and len(X):
        gate = ((C['pio_filled'].to_numpy() == 1) & (C['pio_flag_pio'].to_numpy() == 0))
        keep = gate[idx]
    return np.ascontiguousarray(X[keep]), idx[keep], names


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('cmd', choices=['prepare', 'compare'])
    ap.add_argument('--tables', required=True); ap.add_argument('--samples', nargs='+', required=True); ap.add_argument('--work', required=True)
    ap.add_argument('--shipped'); ap.add_argument('--numu-release'); ap.add_argument('--nue-release'); ap.add_argument('--out')
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    C, O = load(a.tables, a.samples)
    if C.duplicated(['sample'] + uc.KEY).any():
        sys.exit('candidate key not unique across samples')
    C = C.reset_index(drop=True)
    if a.cmd == 'prepare':
        jobs = []
        for m in uc.L1_ALL:
            X, idx, names = objects(m, C, O)
            X.tofile(os.path.join(a.work, 'X_%s.f32' % m)); np.save(os.path.join(a.work, 'idx_%s.npy' % m), idx)
            for wset, dirs in (('shipped', [a.shipped]), ('release', [a.numu_release if m in uc.L1_NUMU else a.nue_release, a.shipped])):
                xml = uc.resolve(dirs, uc.FILES[m])
                if xml_names(xml) != names:
                    sys.exit('%s %s: XML variables %s differ from the reader order %s' % (wset, m, xml_names(xml), names))
                open(os.path.join(a.work, 'names_%s.txt' % m), 'w').write('\n'.join(names) + '\n')
                jobs.append([xml, os.path.join(a.work, 'names_%s.txt' % m), os.path.join(a.work, 'X_%s.f32' % m), str(len(X)),
                             os.path.join(a.work, 'out_%s_%s.f64' % (wset, m)), wset, m, uc.sha256(xml)])
        with open(os.path.join(a.work, 'jobs.tsv'), 'w') as f:
            for j in jobs:
                f.write('\t'.join(j) + '\n')
        print('prepared %d jobs, %d candidates, objects %s' % (len(jobs), len(C), {m: int(np.fromfile(os.path.join(a.work, 'X_%s.f32' % m), np.float32).size // len(uc.L1_SPEC[m]['lists'] + uc.L1_SPEC[m]['scalars'])) for m in uc.L1_ALL}))
        return
    rep = dict(samples=a.samples, candidates=len(C), shipped={}, release={})
    jobs = [l.rstrip('\n').split('\t') for l in open(os.path.join(a.work, 'jobs.tsv'))]
    sha = {(j[5], j[6]): j[7] for j in jobs}
    for m in uc.L1_ALL:
        idx = np.load(os.path.join(a.work, 'idx_%s.npy' % m))
        X = np.fromfile(os.path.join(a.work, 'X_%s.f32' % m), np.float32).reshape(len(idx), -1) if len(idx) else np.zeros((0, 1), np.float32)
        vs = np.fromfile(os.path.join(a.work, 'out_shipped_%s.f64' % m), np.float64)
        pooled, has = uc._pool(len(C), idx, vs.astype(np.float32), uc.L1_SPEC[m]['pool'], uc.EMPTY[m])
        stored = C[uc.L1_SPEC[m]['score']].to_numpy(np.float64).astype(np.float32)
        d = np.abs(pooled.astype(np.float64) - stored.astype(np.float64))
        rep['shipped'][m] = dict(xml_sha256=sha[('shipped', m)], objects=int(len(idx)), candidates=len(C), candidates_with_objects=int(has.sum()),
                                 exact=int((d == 0).sum()), over_1e6=int((d > 1e-6).sum()), max_abs=float(d.max()),
                                 nan_objects=int((vs == -999).sum()), empty_constant_candidates=int((~has).sum()))
        vr = np.fromfile(os.path.join(a.work, 'out_release_%s.f64' % m), np.float64)
        xml_rel = [j[0] for j in jobs if j[5] == 'release' and j[6] == m][0]
        gf = GradForest(xml_rel, expected_names=uc.L1_SPEC[m]['lists'] + uc.L1_SPEC[m]['scalars'])
        vn = gf.evaluate_mva(X) if len(X) else np.zeros(0)
        dd = np.abs(vr.astype(np.float32).astype(np.float64) - vn.astype(np.float32).astype(np.float64))
        rep['release'][m] = dict(xml_sha256=sha[('release', m)], objects=int(len(idx)), exact_float32=int((dd == 0).sum()), max_abs=float(dd.max()) if len(dd) else 0.0,
                                 over_1e6=int((dd > 1e-6).sum()), nan_objects_tmva=int((vr == -999).sum()), nan_objects_numpy=int((vn == -999).sum()))
        print(m, 'shipped', {k: rep['shipped'][m][k] for k in ('objects', 'exact', 'over_1e6', 'max_abs')}, 'release', {k: rep['release'][m][k] for k in ('exact_float32', 'max_abs')}, flush=True)
    rep['verdict_shipped'] = 'CLOSED' if all(v['over_1e6'] == 0 for v in rep['shipped'].values()) else 'NOT_CLOSED'
    rep['verdict_release'] = 'AGREE' if all(v['over_1e6'] == 0 for v in rep['release'].values()) else 'DIFFER'
    json.dump(rep, open(a.out, 'w'), indent=1)
    print(json.dumps({k: rep[k] for k in ('candidates', 'verdict_shipped', 'verdict_release')}))


if __name__ == '__main__':
    main()
