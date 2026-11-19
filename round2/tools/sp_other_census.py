#!/usr/bin/env python3
"""SP other class census on the WCL1116 development tables, per vertex mode (no training).

  python sp_other_census.py --spec-template specs/single_photon_other_training_spec_dev_wcl1116_%s.yaml --tag dev \
      --tables-template $SP_WORK/wcl1116_dev_tables/%s --out-json OUT.json [--old-ext-rows 481]

Classes from sp_retrain.labels.development_classes (single_photon_other). Negatives are split by component:
  NC no pi0            NCBkg (partner neutrino: NC, no primary pi0, in the 3 cm FV, not signal)
  dirt                 outFVBkg with the partner's true vertex outside the TPC active volume
  out-of-FV (in TPC)   outFVBkg with the true vertex inside the active volume but outside the 3 cm FV
  cosmic-matched MC    T_match partner is a cosmic, or there is no partner (assumption A4: no completeness cut)
  beam-off / EXT       every preselected row of an ext_beam_off sample (only if its tables exist)
Rows with a non-finite input are counted and excluded, as in training; so are rows of files without the sample's expected
wct_version stamp (sp_retrain.provenance). The split is the training split (odd subrun ->
development holdout; EXT: run % 4 == 1). If the EXT tables are absent the census is MC-only and says so.
"""
import argparse
import copy
import json
import os
import sys

import numpy as np
import pandas as pd

ROUND2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROUND2)
from sp_retrain import build_tables, devtrain, features, labels, provenance  # noqa: E402

MODES = ('dv2_split_move', 'dv2_snap')


def component(c, cls, ext):
    act = build_tables.ACTIVE
    inside = ((c.m_vx > act['x'][0]) & (c.m_vx < act['x'][1]) & (c.m_vy > act['y'][0]) & (c.m_vy < act['y'][1]) &
              (c.m_vz > act['z'][0]) & (c.m_vz < act['z'][1])).to_numpy()
    pk = c.partner_kind.astype(str).to_numpy(); bkg = c.m_sp_bkg.astype(str).to_numpy()
    comp = np.full(len(c), '', object)
    comp[cls == 1] = 'signal'
    neg = cls == 0
    comp[neg & ext] = 'beam_off_ext'
    comp[neg & ~ext & np.isin(pk, ('cosmic', 'none'))] = 'cosmic_matched_mc'
    comp[neg & ~ext & (pk == 'neutrino') & (bkg == 'NCBkg')] = 'nc_no_pi0'
    comp[neg & ~ext & (pk == 'neutrino') & (bkg == 'outFVBkg') & ~inside] = 'dirt'
    comp[neg & ~ext & (pk == 'neutrino') & (bkg == 'outFVBkg') & inside] = 'out_of_fv_in_tpc'
    return comp


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    for k in ('--spec-template', '--tag', '--tables-template', '--out-json'):
        ap.add_argument(k, required=True)
    ap.add_argument('--old-ext-rows', type=int, default=481)
    a = ap.parse_args()
    out = dict(label='SP other CENSUS (development tables; no training)', modes={})
    for mode in MODES:
        spec = labels.load_spec(os.path.join(ROUND2, a.spec_template % mode))
        s2 = copy.deepcopy(spec)
        tables = a.tables_template % mode
        present, missing = [], []
        for s in spec['samples']['development']:
            (present if os.path.exists(os.path.join(tables, 'cands_%s_%s.parquet' % (s['id'], a.tag))) else missing).append(s['id'])
        s2['samples']['development'] = [s for s in spec['samples']['development'] if s['id'] in present]
        s2['status'] = 'READY_FOR_DEVELOPMENT_TRAINING'     # CENSUS ONLY, in memory; the on-disk spec status is unchanged
        stamp = json.load(open(os.path.join(os.path.dirname(ROUND2), spec['samples']['input_manifest'])))['reconstruction']['wct_version_stamp']
        parts, dropped = [], {}
        for s in s2['samples']['development']:      # rows only from files with the sample's expected stamp, as in training
            st = provenance.expected_sample_stamp(s, stamp)
            F = pd.read_parquet(os.path.join(tables, 'files_%s_%s.parquet' % (s['id'], a.tag)))
            cs = pd.read_parquet(os.path.join(tables, 'cands_%s_%s.parquet' % (s['id'], a.tag)))
            off = set(F[F.wct_version.fillna('') != st].file_id)
            dropped[s['id']] = dict(expected_wct_version_stamp=st, files_without_stamp=len(off), candidates_dropped=int(cs.file_id.isin(off).sum()))
            parts.append(cs[~cs.file_id.isin(off)])
        C = pd.concat(parts, ignore_index=True)
        C = C[C.is_placeholder == 0].reset_index(drop=True)
        cls, pre = labels.development_classes(C, s2)
        ext = C['sample'].astype(str).isin(labels.ext_sample_ids(s2)).to_numpy()
        X = C[features.load('single_photon_other').columns].to_numpy(np.float64)
        fin = np.isfinite(X).all(1)
        comp = component(C, cls, ext)
        sp = np.where(C.subrun.to_numpy() % 2 == 1, 'holdout', 'train')
        sp = np.where(ext, np.where(C.run.to_numpy() % 4 == 1, 'holdout', 'train'), sp)
        use = (cls >= 0) & fin
        ev = C[devtrain.EV].astype(str).agg('|'.join, axis=1)
        k = pd.DataFrame(dict(ev=ev, comp=comp, use=use, sp=sp, sample=C['sample'].astype(str)))
        ku = k[k.use]
        per = {}
        for cc in ('signal', 'nc_no_pi0', 'dirt', 'out_of_fv_in_tpc', 'cosmic_matched_mc', 'beam_off_ext'):
            q = ku[ku.comp == cc]
            per[cc] = dict(rows=int(len(q)), events=int(q.ev.nunique()), train=int((q.sp == 'train').sum()), holdout=int((q.sp == 'holdout').sum()),
                           by_sample={s: int(v) for s, v in q['sample'].value_counts().items()})
        negs = ku[ku.comp != 'signal']
        mult = ku.groupby('ev').size()
        cats = ku.groupby('ev').comp.nunique()
        out['modes'][mode] = dict(
            samples_present=present, samples_missing=missing, mc_only=bool(missing), stamp_filter=dropped,
            candidates=int(len(C)), preselected=int(pre.sum()), classed=int((cls >= 0).sum()),
            nonfinite_classed_rows=int(((cls >= 0) & ~fin).sum()),
            positive=dict(rows=per['signal']['rows'], events=per['signal']['events'], train=per['signal']['train'], holdout=per['signal']['holdout']),
            negative=dict(rows=int(len(negs)), events=int(negs.ev.nunique()), train=int((negs.sp == 'train').sum()), holdout=int((negs.sp == 'holdout').sum())),
            negative_by_component={cc: per[cc] for cc in per if cc != 'signal'},
            beam_off_fraction_of_negatives=(per['beam_off_ext']['rows'] / len(negs)) if len(negs) else None,
            events_with_multiple_classed_candidates=int((mult > 1).sum()),
            events_with_more_than_one_component=int((cats > 1).sum()),
            old_reconstruction_ext_rows_reference=a.old_ext_rows)
        print(mode, json.dumps({kk: out['modes'][mode][kk] for kk in ('samples_missing', 'positive', 'negative', 'nonfinite_classed_rows')}),
              {cc: per[cc]['rows'] for cc in per})
    json.dump(out, open(a.out_json, 'w'), indent=1)


if __name__ == '__main__':
    main()
