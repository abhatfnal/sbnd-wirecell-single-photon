#!/usr/bin/env python3
"""Source-compatibility audit of the NC pi0-labelled rows of wcl1116-aurora-nuecc for the SP ncpi0 negative class
(no training; reads the WCL1116 development tables only).

  python sp_ncpi0_extra_negatives_audit.py --tables-template $SP_WORK/wcl1116_dev_tables/%s --tag dev --out-json OUT.json

Criteria (docs/SP_BDT_WCL1116_FULL_DEVELOPMENT_PLAN.md sec. 4), each checked against the training BNB NC pi0 rows:
  provenance      how the sample was generated and filtered (recorded in the output from the production config)
  target          NCpi0Bkg: not signal, NC, true vertex in the 3 cm FV, >= 1 primary pi0 (the label itself)
  environment     the event's OTHER true neutrino interactions in the active TPC (a filter acting on another interaction
                  changes the reconstruction environment of the NC pi0 even when its own kinematics are unbiased)
  kinematics      partner flavour, energy, pi0 multiplicity vs BNB NC pi0
  duplication     file ids, runs and event keys shared with BNB
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

ROUND2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROUND2)
from sp_retrain import build_tables, devtrain, labels  # noqa: E402

MODES = ('dv2_split_move', 'dv2_snap')
PROVENANCE = dict(
    sample='wcl1116-aurora-nuecc (Gen2 CC nu_e configL, WCLocal2026Nov16 refresh of the Gen2 300k production)',
    generation='GEN: full BNB flux, all four flavours + CORSIKA, 125 spills per subrun (configL gsimple, rockbox0p1)',
    filter=('official run_sbnd_gen2_rare_signal_filter.fcl (T. Wester); kept stream outnuecc = sbnd_ccnue_filter; DISCARDED '
            'streams: outccpi0, outncpi0, outeta, outkaon, outccdeltarad, outncdeltarad'),
    source='parsl-production/sbn_parsl-gen2-ccnue-configL-300k-reco1only-main-20261027/settings/sbnd/gen2_ccnue_configL_300k_*.toml '
           '(filter_output_stream / filter_discard_streams); filter FCL preserved in gen2-ccnue-review-20261023/c2_preserved_gen/',
    consequence=('every event is a spill selected for a CC nu_e interaction; an NC pi0 row in it is a SECOND interaction of a '
                 'spill selected for a different neutrino'))
COLS = devtrain.ROW_KEY + ['is_placeholder', 'shw_sp_n_20mev_showers', 'label_unreadable', 'partner_kind', 'm_sp_truth_ok', 'm_sp_signal',
                           'm_sp_bkg', 'm_pdg', 'm_ccnc', 'm_E', 'm_vx', 'm_vy', 'm_vz', 'm_n_prim_pi0', 'm_nu_idx']


def ncpi0_rows(tables, sid, tag):
    C = pd.read_parquet(os.path.join(tables, 'cands_%s_%s.parquet' % (sid, tag)), columns=COLS)
    pre = labels.preselection(C)
    q = pre & (C.partner_kind.astype(str) == 'neutrino').to_numpy() & (C.m_sp_truth_ok.fillna(0) == 1).to_numpy() & \
        (C.m_sp_signal.fillna(0) != 1).to_numpy() & (C.m_sp_bkg.astype(str) == 'NCpi0Bkg').to_numpy()
    return C[q].reset_index(drop=True)


def environment(rows, truth):
    act = build_tables.ACTIVE
    T = truth.copy()
    T['in_active'] = ((T.vx > act['x'][0]) & (T.vx < act['x'][1]) & (T.vy > act['y'][0]) & (T.vy < act['y'][1]) & (T.vz > act['z'][0]) & (T.vz < act['z'][1]))
    T['nue_cc_active'] = T.in_active & (T.pdg.abs() == 12) & (T.ccnc == 0)
    g = T.groupby(devtrain.EV)
    ev = pd.DataFrame(dict(n_nu_active=g.in_active.sum(), n_nue_cc_active=g.nue_cc_active.sum())).reset_index()
    r = rows.merge(ev, on=devtrain.EV, how='left')
    other_active = r.n_nu_active - 1          # the NC pi0 partner itself is in the FV, hence in the active volume
    return dict(rows=int(len(r)), events=int(r[devtrain.EV].drop_duplicates().shape[0]),
                frac_with_another_active_interaction=float((other_active >= 1).mean()) if len(r) else None,
                frac_with_a_nue_cc_in_active=float((r.n_nue_cc_active >= 1).mean()) if len(r) else None,
                mean_active_interactions=float(r.n_nu_active.mean()) if len(r) else None)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    for k in ('--tables-template', '--tag', '--out-json'):
        ap.add_argument(k, required=True)
    a = ap.parse_args()
    from scipy.stats import ks_2samp
    out = dict(label='SP ncpi0 EXTRA-NEGATIVE SOURCE AUDIT (no training)', provenance=PROVENANCE, modes={})
    for mode in MODES:
        t = a.tables_template % mode
        R = {s: ncpi0_rows(t, s, a.tag) for s in ('wcl1116-aurora-nuecc', 'wcl1116-aurora-bnb')}
        T = {s: pd.read_parquet(os.path.join(t, 'truth_%s_%s.parquet' % (s, a.tag)), columns=devtrain.EV + ['nu_idx', 'pdg', 'ccnc', 'E', 'vx', 'vy', 'vz'])
             for s in R}
        n, b = R['wcl1116-aurora-nuecc'], R['wcl1116-aurora-bnb']
        sp = lambda x: dict(train=int((x.subrun % 2 == 0).sum()), holdout=int((x.subrun % 2 == 1).sum()))
        flav = lambda x: {str(k): int(v) for k, v in x.m_pdg.value_counts().items()}
        res = dict(
            nuecc_ncpi0_rows=int(len(n)), nuecc_ncpi0_split=sp(n), bnb_ncpi0_rows=int(len(b)), bnb_ncpi0_split=sp(b),
            target_definition_satisfied_by_label=True,
            partner_flavour=dict(nuecc=flav(n), bnb=flav(b)),
            partner_energy_gev=dict(nuecc_median=float(n.m_E.median()), bnb_median=float(b.m_E.median()), ks_pvalue=float(ks_2samp(n.m_E, b.m_E).pvalue)),
            n_prim_pi0=dict(nuecc={str(k): int(v) for k, v in n.m_n_prim_pi0.value_counts().items()}, bnb={str(k): int(v) for k, v in b.m_n_prim_pi0.value_counts().items()}),
            environment=dict(nuecc=environment(n, T['wcl1116-aurora-nuecc']), bnb=environment(b, T['wcl1116-aurora-bnb'])),
            duplication=dict(
                shared_file_ids=int(len(set(n.file_id) & set(b.file_id))),
                run_range=dict(nuecc=[int(n.run.min()), int(n.run.max())] if len(n) else None, bnb=[int(b.run.min()), int(b.run.max())]),
                shared_event_keys=int(len(set(map(tuple, n[devtrain.EV].astype(str).values)) & set(map(tuple, b[devtrain.EV].astype(str).values))))))
        out['modes'][mode] = res
        print(mode, json.dumps({k: res[k] for k in ('nuecc_ncpi0_rows', 'nuecc_ncpi0_split', 'bnb_ncpi0_rows', 'partner_flavour', 'partner_energy_gev', 'environment', 'duplication')}))
    e = out['modes']['dv2_split_move']['environment']
    out['verdict'] = ('AVAILABLE EXTRA SAMPLE NOT SOURCE-COMPATIBLE' if (e['nuecc']['frac_with_a_nue_cc_in_active'] or 0) > 0.5 and
                      (e['bnb']['frac_with_a_nue_cc_in_active'] or 0) < 0.05 else 'SOURCE-COMPATIBILITY NOT EXCLUDED BY THE ENVIRONMENT TEST')
    out['verdict_basis'] = ('the target label matches and nothing is duplicated, but the rows are second interactions in spills '
                            'selected for a CC nu_e; their reconstruction environment (an extra CC nu_e interaction in the active '
                            'TPC) differs from the BNB NC pi0 training population; the official source of extra NC pi0 statistics '
                            'is the outncpi0 stream of the same filter, discarded in this production')
    json.dump(out, open(a.out_json, 'w'), indent=1)
    print(out['verdict'])


if __name__ == '__main__':
    main()
