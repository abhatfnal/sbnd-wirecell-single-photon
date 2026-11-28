#!/usr/bin/env python3
"""Matched-background comparison of upstream domains on the DEVELOPMENT HOLDOUT, from the per-row scores saved by
tools/upstream_joint_comparison.py (no model is trained or re-scored; DEVELOPMENT ONLY).

For each domain and BNB-acceptance cap the grid vector with the highest HOLDOUT NC Delta efficiency at holdout acceptance <=
cap is taken (the same 9^4 grid, thresholds per level set on NESTED VALIDATION signal rows exactly as in the domain study).
This is an optimization on the holdout, done identically for every domain, so it compares the domains' attainable fronts at
matched background on 5x the nested-validation rows; it is a diagnostic, not a performance estimate. Reported: counts, truth
topology efficiencies, background composition, Xuyang split / upstream-role breakdown, and paired A-vs-domain tables (exact
McNemar, (sample, run, subrun)-clustered Poisson bootstrap) on the holdout rows.

  python tools/upstream_joint_holdout_matched.py --mode M --rows $U/joint/M/joint_rows_scores_M.parquet \
      --comparison validation/upstream_r4/upstream_joint_comparison_M.json --membership $U/membership/M/membership_candidates_M.parquet --out-json OUT
"""
import argparse, itertools, json, os, sys

import numpy as np
import pandas as pd

ROUND2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROUND2); sys.path.insert(0, os.path.join(ROUND2, 'tools'))
from sp_retrain import devstudy as dv, devtrain, legacy_control as lc  # noqa: E402
import sp_operating_points as spo  # noqa: E402
from upstream_joint_comparison import Boot, paired, rate  # noqa: E402

ORDER = spo.ORDER
CAPS = (0.0078, 0.0070)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    for k in ('--mode', '--rows', '--comparison', '--membership', '--out-json'):
        ap.add_argument(k, required=True)
    ap.add_argument('--bootstrap', type=int, default=2000)
    a = ap.parse_args()
    R = pd.read_parquet(a.rows).reset_index(drop=True)
    ref = json.load(open(a.comparison))
    M = pd.read_parquet(a.membership, columns=devtrain.ROW_KEY + ['up_numu_role', 'up_nue_role'])
    k = R[devtrain.ROW_KEY].copy()
    for c in ('run', 'subrun', 'event', 'cand'):
        k[c] = k[c].astype(np.int64); M[c] = M[c].astype(np.int64)
    mem = k.merge(M, on=devtrain.ROW_KEY, how='left', validate='one_to_one')
    role = R.role.to_numpy(); nv, te = role == dv.ROLE_NVAL, role == dv.ROLE_TEST
    sig = R.signal.to_numpy(); smp = R['sample'].to_numpy()
    ncdr = sig & (smp == spo.NCDR); bnb = (~sig) & (smp == spo.BNB)
    topo = R.topology.to_numpy(); bkgc = R.bkg_class.to_numpy(); xn = R.xn_split_v11.to_numpy()
    combos = list(itertools.product(range(len(spo.LEVELS)), repeat=4))
    passes, info = {}, {}
    for d in ('A', 'B', 'C', 'D'):
        sc = {m: R['R_%s_%s' % (m, d)].to_numpy(np.float64) for m in ORDER}
        thr = {m: [lc.threshold_for_rate(sc[m][sig & nv], lev) if lev is not None else -np.inf for lev in spo.LEVELS] for m in ORDER}
        lv = {m: np.stack([sc[m] > t for t in thr[m]]) for m in ORDER}
        ts, tb = np.zeros(len(combos), np.int32), np.zeros(len(combos), np.int32)
        for i, cb in enumerate(combos):
            p = lv['numu'][cb[0]] & lv['other'][cb[1]] & lv['ncpi0'][cb[2]] & lv['nue'][cb[3]]
            ts[i] = int((p & te & ncdr).sum()); tb[i] = int((p & te & bnb).sum())
        ns, nb = int((te & ncdr).sum()), int((te & bnb).sum())
        for cap in CAPS:
            ok = tb / nb <= cap + 1e-12
            order = np.lexsort((tb, -ts))                      # max signal, then min background, then grid order
            i = int([j for j in order if ok[j]][0]); cb = combos[i]
            exp = ref['points']['%s_FRONT_%.3fpct' % (d, cap * 100)]['holdout_optimized_front']
            assert exp['signal_pass'] == ts[i] and exp['background_pass'] == tb[i], 'does not reproduce the comparison JSON'
            p = lv['numu'][cb[0]] & lv['other'][cb[1]] & lv['ncpi0'][cb[2]] & lv['nue'][cb[3]]
            passes[(d, cap)] = p
            q = te
            info['%s_%.2fpct' % (d, cap * 100)] = dict(
                levels={m: spo.LEVELS[cb[j]] for j, m in enumerate(ORDER)}, ncdr_signal=rate(p, q & ncdr), bnb_background=rate(p, q & bnb),
                ext=rate(p, q & (smp == spo.EXT)), nuecc_nueCCBkg=rate(p, q & (smp == spo.NUECC) & (bkgc == 'nueCCBkg')),
                topology={t: rate(p, q & ncdr & qq) for t, qq in (('0p', topo == 0), ('1p', topo == 1), ('>=2p', topo >= 2))},
                background_composition={c: int((p & q & bnb & (bkgc == c)).sum()) for c in sorted(set(bkgc[q & bnb]))},
                by_xn_split_v11={g: dict(ncdr_signal=rate(p, q & ncdr & (xn == g)), bnb_background=rate(p, q & bnb & (xn == g))) for g in ('dev', 'train')},
                by_up_numu_role={g: dict(ncdr_signal=rate(p, q & ncdr & (mem.up_numu_role.to_numpy() == g)), bnb_background=rate(p, q & bnb & (mem.up_numu_role.to_numpy() == g)))
                                 for g in ('fit', 'early_stop', 'ineligible')},
                by_up_nue_role={g: dict(ncdr_signal=rate(p, q & ncdr & (mem.up_nue_role.to_numpy() == g)), bnb_background=rate(p, q & bnb & (mem.up_nue_role.to_numpy() == g)))
                                for g in ('fit', 'early_stop', 'ineligible')})
    boot = Boot(R, a.bootstrap)
    comp = {}
    for cap in CAPS:
        for d in ('B', 'C', 'D'):
            pa, pb = passes[('A', cap)], passes[(d, cap)]
            comp['A_vs_%s_%.2fpct' % (d, cap * 100)] = dict(
                ncdr_signal=paired(pa, pb, te & ncdr, boot), bnb_background=paired(pa, pb, te & bnb, boot),
                signal_migration_by_topology={t: dict(gained=int((~pa & pb & te & ncdr & qq).sum()), lost=int((pa & ~pb & te & ncdr & qq).sum()))
                                              for t, qq in (('0p', topo == 0), ('1p', topo == 1), ('>=2p', topo >= 2))},
                background_migration_by_class={c: dict(gained=int((~pa & pb & te & bnb & (bkgc == c)).sum()), lost=int((pa & ~pb & te & bnb & (bkgc == c)).sum()))
                                               for c in sorted(set(bkgc[te & bnb]))},
                by_xn_split_v11={g: paired(pa, pb, te & ncdr & (xn == g), boot) for g in ('dev', 'train')})
    out = dict(label='HOLDOUT MATCHED-BACKGROUND DIAGNOSTIC (grid maximum taken on the development holdout for every domain) -- DEVELOPMENT ONLY, NOT A PERFORMANCE ESTIMATE',
               mode=a.mode, holdout_rows=dict(ncdr_signal=int((te & ncdr).sum()), bnb_background=int((te & bnb).sum())), caps=list(CAPS),
               points=info, paired=comp, bootstrap=dict(replicates=a.bootstrap, cluster='(sample, run, subrun)', seed=20261128))
    json.dump(out, open(a.out_json, 'w'), indent=1, default=lambda o: o.item() if hasattr(o, 'item') else str(o))
    print(json.dumps({k: (v['ncdr_signal']['rate'], v['bnb_background']['rate']) for k, v in info.items()}))


if __name__ == '__main__':
    main()
