#!/usr/bin/env python3
"""Full-table equivalence of the portable bundle (round2/upstream_chain_bundle, wc_upstream_chain) with the validated Aurora
chain emulation (sp_retrain/upstream_chain.py, whose outputs are the rescore tables of tools/upstream_rescore.py and were shown
equal to the patched in-chain test). Every candidate of one extracted sample, one vertex mode:

  release   bundle UpstreamChain(release dirs + shipped).score(kind)          vs  rescore r3af_* (4 nu_mu) and nueA2_* (15 + nue_score)
  noscale   bundle ... score(kind='mc', apply_sim_correction=False)           vs  rescore r3af_noscale_* (simulation only)
  shipped   bundle UpstreamChain(shipped).score(stored_l1=True)               vs  rescore ship_numu_score / ship_nue_score and the stored values
  flag      bundle diag_numu_cc_flag_bdt                                      vs  rescore r3af_numu_cc_flag_bdt

  python tools/check_upstream_chain_bundle.py --tables T --rescore R --sample S --kind mc|data --releases CLONE/releases --shipped WCD --out JSON [--save P]
"""
import argparse, json, os, sys, time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROUND2 = os.path.dirname(HERE)
sys.path.insert(0, ROUND2); sys.path.insert(0, os.path.join(ROUND2, 'upstream_chain_bundle'))
import wc_upstream_chain as wuc  # noqa: E402
from wc_upstream_chain.cli import release_dirs  # noqa: E402
from upstream_rescore import load  # noqa: E402

KEY = ['sample'] + wuc.DEFAULT_KEY


def main():
    import pandas as pd
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    for k in ('--tables', '--rescore', '--sample', '--releases', '--shipped', '--out'):
        ap.add_argument(k, required=True)
    ap.add_argument('--kind', required=True, choices=['mc', 'data'])
    ap.add_argument('--save', help='write the bundle release score table (with diag_*) to this parquet (work area)')
    a = ap.parse_args()
    t0 = time.time()
    C, O = load(a.tables, a.sample, '')
    R = pd.read_parquet(os.path.join(a.rescore, 'rescore_%s.parquet' % a.sample))
    rel = wuc.UpstreamChain(release_dirs(a.releases, a.shipped))
    shp = wuc.UpstreamChain([a.shipped])
    out = dict(sample=a.sample, kind=a.kind, candidates=int(len(C)), bundle_version=wuc.__version__,
               bundle_tmva_grad_identical_to_sp_retrain=open(os.path.join(ROUND2, 'sp_retrain', 'tmva_grad.py'), 'rb').read() ==
               open(os.path.join(ROUND2, 'upstream_chain_bundle', 'wc_upstream_chain', 'tmva_grad.py'), 'rb').read())
    r = rel.score(C, O, kind=a.kind, key=KEY)
    ren = {('r3af_' + s): s for s in wuc.spec.NUMU_SCORES}
    ren.update({('nueA2_' + s): s for s in wuc.spec.NUE_L1_SCORES + ['nue_score']})
    E = R[KEY + list(ren)].rename(columns=ren)
    out['release'] = wuc.compare_exact(r, E, wuc.spec.UPSTREAM_OUTPUTS, key=KEY)
    out['release_flag_copy'] = wuc.compare_exact(r.rename(columns={'diag_numu_cc_flag_bdt': 'f'}),
                                                 R[KEY + ['r3af_numu_cc_flag_bdt']].rename(columns={'r3af_numu_cc_flag_bdt': 'f'}), ['f'], key=KEY)['f']
    out['release_diag'] = dict(numu_cc_flag_switched_off=int(r.diag_numu_cc_flag_switched_off.sum()),
                               numu_final_nan_input=int(r.diag_numu_final_nan_input.sum()), nue_final_nan_input=int(r.diag_nue_final_nan_input.sum()),
                               candidates_with_nan_object=int((r.diag_l1_models_with_nan_object > 0).sum()),
                               placeholders=int(r.diag_is_placeholder.sum()), br_filled_not_1=int((r.diag_br_filled != 1).sum()),
                               sim_dqdx_scale_applied=float(r.diag_sim_dqdx_scale.iloc[0]) if len(r) else None)
    if a.kind == 'mc':
        n = rel.score(C, O, kind='mc', key=KEY, apply_sim_correction=False)
        E0 = R[KEY + ['r3af_noscale_' + s for s in wuc.spec.NUMU_SCORES]].rename(columns={'r3af_noscale_' + s: s for s in wuc.spec.NUMU_SCORES})
        out['noscale'] = wuc.compare_exact(n, E0, wuc.spec.NUMU_SCORES, key=KEY)
    s = shp.score(C, O, kind=a.kind, key=KEY, stored_l1=True)
    out['shipped_vs_rescore'] = wuc.compare_exact(s, R[KEY + ['ship_numu_score', 'ship_nue_score']].rename(
        columns={'ship_numu_score': 'numu_score', 'ship_nue_score': 'nue_score'}), ['numu_score', 'nue_score'], key=KEY)
    out['shipped_vs_stored'] = wuc.compare_exact(s, C[KEY + ['numu_score', 'nue_score']], ['numu_score', 'nue_score'], key=KEY)
    blocks = [out['release'], out['shipped_vs_rescore'], out['shipped_vs_stored'], {'flag': out['release_flag_copy']}] + ([out['noscale']] if 'noscale' in out else [])
    out['verdict'] = 'BIT_IDENTICAL' if all(v['exact'] == v['n'] for b in blocks for v in b.values()) else 'DIFFERS'
    out['provenance'] = r.attrs['provenance']['files']
    if a.save:
        r.attrs = {}
        r.to_parquet(a.save, index=False)
    out['wall_s'] = round(time.time() - t0, 1)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(out, open(a.out, 'w'), indent=1, default=lambda o: o.item() if hasattr(o, 'item') else str(o))
    print(json.dumps(dict(sample=a.sample, verdict=out['verdict'], wall_s=out['wall_s'])))
    sys.exit(0 if out['verdict'] == 'BIT_IDENTICAL' else 1)


if __name__ == '__main__':
    main()
