#!/usr/bin/env python3
"""Re-score the upstream Wire-Cell nu_mu / nu_e tagger BDTs of every candidate of one extracted table set
(tools/extract_upstream_inputs.py) with the toolkit-0.38.0 chain emulation (sp_retrain/upstream_chain.py), three times:

  ship_*      the SHIPPED FINAL models the production ran (wire-cell-data 99c6497f), fed the STORED small-model
              values: must reproduce the STORED numu_score / nue_score (closure of every scalar input and of the final
              conventions). The shipped SMALL models are TMVA AdaBoost with VarTransform D,P,U,G,D,N, which the numpy
              evaluator does not implement; they are closed separately with ROOT TMVA (tools/shipped_l1_closure);
  r3af_*      nu_mu numu_round3af chain files, with the simulation dQ/dx scale on simulated samples only (--sim-scale,
              forced to 1 for data); r3af_noscale_* on simulation is a diagnostic only (what an UNPATCHED chain would store);
  nueA2_*     nu_e nue_round4_ruleA_v2 main chain files (no scale; the nu_e scorer is not patched).

Every file is resolved WIRECELL_PATH-style: release folder first, shipped folder after (so numu_tagger3 and every
non-released model resolve to the shipped file, exactly as the README's step 3 sets up the chain).

  python tools/upstream_rescore.py TABLE_DIR SAMPLE OUT_DIR --kind mc|data --shipped DIR --numu-release DIR \
         --nue-release DIR [--sim-scale 1.071] [--tag T] [--nue-final]
"""
import argparse, json, os, sys, time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from sp_retrain import upstream_chain as uc  # noqa: E402

KEYS = ['sample'] + uc.KEY


def load(table_dir, sample, tag):
    sfx = ('_' + tag) if tag else ''
    C = pd.read_parquet(os.path.join(table_dir, 'cands_%s%s.parquet' % (sample, sfx)))
    O = {}
    for m in uc.L1_ALL:
        p = os.path.join(table_dir, 'objs_%s_%s%s.parquet' % (m, sample, sfx))
        O[m] = pd.read_parquet(p) if os.path.exists(p) else None
    return C, O


def closure(stored, emul, name):
    s = np.asarray(stored, np.float64); e = np.asarray(emul, np.float32).astype(np.float64)
    both_nan = np.isnan(s) & np.isnan(e)
    d = np.abs(s - e); d[both_nan] = 0.0
    nan_mismatch = int((np.isnan(s) ^ np.isnan(e)).sum())
    return dict(score=name, n=int(len(s)), exact=int(((s == e) | both_nan).sum()), over_1e6=int((d > 1e-6).sum()),
                over_1e4=int((d > 1e-4).sum()), max_abs=float(np.nanmax(d)) if len(d) else 0.0, nan_mismatch=nan_mismatch)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('table_dir'); ap.add_argument('sample'); ap.add_argument('out_dir')
    ap.add_argument('--kind', required=True, choices=['mc', 'data'])
    ap.add_argument('--shipped', required=True); ap.add_argument('--numu-release', required=True); ap.add_argument('--nue-release', required=True)
    ap.add_argument('--sim-scale', type=float, default=1.071); ap.add_argument('--tag', default='')
    ap.add_argument('--nue-final', action='store_true', help='also score the nu_e final model (shipped file is 199 MB)')
    a = ap.parse_args()
    t0 = time.time()
    C, O = load(a.table_dir, a.sample, a.tag)
    k = a.sim_scale if a.kind == 'mc' else 1.0
    numu_models = uc.L1_NUMU + ['numu_final']
    nue_models = list(uc.L1_NUE) + (['nue_final'] if a.nue_final else [])
    ship = uc.ChainScorer([a.shipped], ['numu_final'] + (['nue_final'] if a.nue_final else []))
    r3af = uc.ChainScorer([a.numu_release, a.shipped], numu_models)
    nue2 = uc.ChainScorer([a.nue_release, a.shipped], nue_models)
    out = C[KEYS + ['is_placeholder', 'br_filled', 'numu_cc_flag']].copy()
    summ = dict(sample=a.sample, kind=a.kind, sim_scale_applied=k, candidates=len(C), table_dir=os.path.abspath(a.table_dir), tag=a.tag,
                key_unique=bool(not C.duplicated(KEYS).any()),
                weights=dict(shipped=ship.provenance(), numu_round3af=r3af.provenance(), nue_round4_ruleA_v2=nue2.provenance()))
    # stored
    for s in uc.STORED_SCORES:
        out['stored_' + s] = C[s].to_numpy(np.float64).astype(np.float32)
    # shipped closure
    sn = ship.numu(C, O, 1.0, stored_l1=True)
    clos = []
    out['ship_numu_score'] = sn['numu_score']; clos.append(closure(C['numu_score'], sn['numu_score'], 'numu_score'))
    if a.nue_final:
        se = ship.nue(C, O, final=True, stored_l1=True)
        out['ship_nue_score'] = se['nue_score']; clos.append(closure(C['nue_score'], se['nue_score'], 'nue_score'))
    summ['closure_shipped_final_models'] = clos
    # released nu_mu (scaled on MC) and the unscaled diagnostic
    rn = r3af.numu(C, O, k)
    for s in uc.NUMU_SCORES:
        out['r3af_' + s] = rn[s]
    out['r3af_numu_cc_flag_bdt'] = rn['numu_cc_flag_bdt']
    summ['nan_objects_r3af'] = rn['nan_objects']
    summ['numu_cc_flag_bdt_turned_off'] = int(((C['numu_cc_flag'].to_numpy() == 1) & (rn['numu_cc_flag_bdt'] != 1)).sum())
    if a.kind == 'mc':
        r0 = r3af.numu(C, O, 1.0)
        for s in uc.NUMU_SCORES:
            out['r3af_noscale_' + s] = r0[s]
    # released nu_e
    re_ = nue2.nue(C, O, final=a.nue_final)
    for s in uc.NUE_L1_SCORES + (['nue_score'] if a.nue_final else []):
        out['nueA2_' + s] = re_[s]
    summ['nan_objects_nueA2'] = re_['nan_objects']
    os.makedirs(a.out_dir, exist_ok=True)
    sfx = ('_' + a.tag) if a.tag else ''
    out.to_parquet(os.path.join(a.out_dir, 'rescore_%s%s.parquet' % (a.sample, sfx)))
    summ['wall_s'] = round(time.time() - t0, 1)
    summ['module_sha256'] = uc.sha256(uc.__file__); summ['tool_sha256'] = uc.sha256(os.path.abspath(__file__))
    json.dump(summ, open(os.path.join(a.out_dir, 'rescore_%s%s.json' % (a.sample, sfx)), 'w'), indent=1)
    bad = [c for c in clos if c['over_1e6'] or c['nan_mismatch']]
    print(json.dumps(dict(sample=a.sample, candidates=len(C), closure_failures=bad, wall_s=summ['wall_s'])))


if __name__ == '__main__':
    main()
