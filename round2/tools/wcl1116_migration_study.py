#!/usr/bin/env python3
"""Reconstruction migration and domain shift: aurora-r2 vs WCL1116 dv2_split_move vs WCL1116 dv2_snap (no training).

  python wcl1116_migration_study.py --old-tables DIR --old-tag dev --split-tables DIR --snap-tables DIR --tag dev \
      --bundle-root LEGACY_BUNDLE --out-json SUMMARY.json [--out-dir DIR]

Aurora TRAINING-side tables only (aurora-r2 and WCLocal2026Nov16-Aurora NC Delta + BNB). No FermiGrid product.
Rows are matched across domains on (file_id, run, subrun, event, cand); the same unit has the same merged-CAF name in
aurora-r2 and WCL1116, and both WCL1116 trees come from the same file. Per sample and domain:
  reconstruction   events, candidates, shw_sp_filled, SP preselection, candidate multiplicity, class populations of
                   SP numu / ncpi0 / other (MC components) / nue, non-finite inputs per model
  ceiling          truth single-photon signal neutrinos (truth table sp_signal) with >= 1 candidate whose T_match partner
                   is that neutrino, >= 1 filled, >= 1 preselected: the candidate-formation ceiling, kept apart from any
                   candidate-level classifier metric; neutrino-partner preselected candidates within 1 / 3 cm of the
                   SCE-shifted true vertex (vertex quality)
  migration        candidates only in one domain; cluster_id agreement; |delta vertex| on matched candidates;
                   shw_sp_filled flips; shower-count / main-shower-energy changes
  feature shift    per SP feature set (numu 73, ncpi0 45, other 146, nue 56) on preselected rows: standardized mean shift,
                   median shift / IQR, KS statistic, Wasserstein / sd (all on the marginal distributions), fraction of
                   matched preselected rows whose value changed; per input family
  legacy score     the exact legacy MicroBooNE XMLs (ncpi0 with kine_pio_flag = 0), log10-odds once; pass rates at the
                   historical cut by class and matched pass/fail migration; legacy AUC per class pair (diagnostic)
No threshold is chosen; the historical cuts are diagnostics.
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

ROUND2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROUND2)
from sp_retrain import devtrain, features, labels, legacy_control as lc  # noqa: E402

MODELS = ('single_photon_numu', 'single_photon_ncpi0', 'single_photon_other', 'single_photon_nue')
HIST_CUT = {'single_photon_numu': 0.4, 'single_photon_other': 0.2, 'single_photon_ncpi0': -0.05, 'single_photon_nue': -1.0}
NEG = {'single_photon_numu': ('numuCCBkg', 'numuCCpi0Bkg'), 'single_photon_ncpi0': ('NCpi0Bkg',),
       'single_photon_other': ('NCBkg', 'outFVBkg'), 'single_photon_nue': ('nueCCBkg',)}
KEY = ['file_id', 'run', 'subrun', 'event', 'cand']
EV = ['file_id', 'run', 'subrun', 'event']
FAMILIES = [('pi0', ('kine_pio', 'shw_sp_pio')), ('numu_cosmic_tagging', ('numu_', 'cosmict_', 'cosmic_')),
            ('upstream_scores', ('_score',)), ('vertex_distance', ('vtx', '_dis', 'nuvtx')),
            ('shower_start_dQdx', ('dQ_dx', 'dqdx', 'dq_dx')),
            ('track_shower_relation', ('_br', 'track', 'length', 'muon', 'stem', 'lol', 'tro', 'stw', 'sig', 'mip'))]
SAMPLES = (('ncdr', 'aurora-r2-ncdr', 'wcl1116-aurora-ncdr'), ('bnb', 'aurora-r2-bnb', 'wcl1116-aurora-bnb'))


def family(name):
    for fam, pats in FAMILIES:
        if any(p in name for p in pats):
            return fam
    return 'shower_topology_energy'


def load(tables, sid, tag, cols):
    c = pd.read_parquet(os.path.join(tables, 'cands_%s_%s.parquet' % (sid, tag)))
    t = pd.read_parquet(os.path.join(tables, 'truth_%s_%s.parquet' % (sid, tag)))
    f = pd.read_parquet(os.path.join(tables, 'files_%s_%s.parquet' % (sid, tag)))
    return c[[x for x in c.columns if x in cols]].copy(), t, f


def classes(c, clf):
    """Development classes (sp_retrain.labels) with an in-memory READY spec: a CENSUS, not a training spec."""
    if clf == 'single_photon_nue':
        pre = labels.preselection(c)
        pk = c.partner_kind.astype(str).to_numpy()
        nu = (pk == 'neutrino') & (c.m_sp_truth_ok.fillna(0).to_numpy() == 1)
        cls = np.full(len(c), -1, np.int8)
        cls[nu & (c.m_sp_signal.fillna(0).to_numpy() == 1)] = 1
        cls[nu & np.isin(c.m_sp_bkg.astype(str).to_numpy(), NEG[clf])] = 0
        cls[~pre] = -1
        return cls, pre
    spec = dict(spec_id='census', status='READY_FOR_DEVELOPMENT_TRAINING', classifier=dict(name=clf),
                label=dict(definition=dict(implementation='census')), samples=dict(development=[]))
    return labels.development_classes(c, spec)


def shift_stats(a, b):
    from scipy.stats import ks_2samp, wasserstein_distance
    a = a[np.isfinite(a)]; b = b[np.isfinite(b)]
    if len(a) < 10 or len(b) < 10:
        return None
    sd = float(a.std()) or 1.0
    q1, q3 = np.quantile(a, [0.25, 0.75]); iqr = float(q3 - q1) or sd
    return dict(std_mean_shift=float((b.mean() - a.mean()) / sd), median_shift_over_iqr=float((np.median(b) - np.median(a)) / iqr),
                ks=float(ks_2samp(a, b).statistic), wasserstein_over_sd=float(wasserstein_distance(a, b) / sd))


def ceiling(c, t, pre):
    sig = t[(t.sp_truth_ok == 1) & (t.sp_signal == 1)][EV + ['nu_idx', 'sp_category']]
    cc = c.assign(pre=pre)[EV + ['m_nu_idx', 'shw_sp_filled', 'pre', 'partner_kind', 'dist_sce_cm']]
    cc = cc[cc.partner_kind.astype(str) == 'neutrino']
    g = cc.groupby(EV + ['m_nu_idx']).agg(any_cand=('pre', 'size'), filled=('shw_sp_filled', lambda x: int((x == 1).any())),
                                         pre=('pre', 'max'), best_dist=('dist_sce_cm', 'min')).reset_index()
    m = sig.merge(g, left_on=EV + ['nu_idx'], right_on=EV + ['m_nu_idx'], how='left')
    n = len(m)
    out = dict(truth_signal_neutrinos=n, with_candidate=int(m.any_cand.notna().sum()), with_filled=int((m.filled == 1).sum()),
               with_preselected=int((m.pre == True).sum()))  # noqa: E712
    for k in ('with_candidate', 'with_filled', 'with_preselected'):
        out[k + '_frac'] = out[k] / n if n else float('nan')
    p = m[m.pre == True]  # noqa: E712
    out['preselected_best_dist_lt_1cm_frac'] = float((p.best_dist < 1).mean()) if len(p) else float('nan')
    out['preselected_best_dist_lt_3cm_frac'] = float((p.best_dist < 3).mean()) if len(p) else float('nan')
    out['by_category_with_preselected_frac'] = {str(k): float((g2.pre == True).mean()) for k, g2 in m.groupby('sp_category')}  # noqa: E712
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    for k in ('--old-tables', '--old-tag', '--split-tables', '--snap-tables', '--tag', '--bundle-root', '--out-json'):
        ap.add_argument(k, required=True)
    ap.add_argument('--out-dir', default=None)
    a = ap.parse_args()
    from sklearn.metrics import roc_auc_score
    lc.verify_bundle(a.bundle_root)
    fls = {m: features.load(m) for m in MODELS}
    forests = {m: lc.load_control(a.bundle_root, m, fls[m].names) for m in MODELS}
    need = set(sum((fl.columns for fl in fls.values()), [])) | set(KEY) | {
        'sample', 'is_placeholder', 'shw_sp_filled', 'shw_sp_n_20mev_showers', 'label_unreadable', 'partner_kind', 'm_sp_truth_ok',
        'm_sp_signal', 'm_sp_bkg', 'm_sp_category', 'm_nu_idx', 'dist_sce_cm', 'nu_x', 'nu_y', 'nu_z', 'cluster_id', 'shw_sp_energy',
        'shw_sp_n_good_showers', 'shw_sp_n_showers', 'm_sp_n_prim_pi0'}
    res = dict(label='AURORA TRAINING-SIDE DEVELOPMENT STUDY (aurora-r2 vs WCL1116); no FermiGrid product; historical cuts are diagnostics',
               domains=dict(old='aurora-r2 (Round-1 reconstruction)', split='WCL1116 recTreeWireCell (dv2_split_move)',
                            snap='WCL1116 recTreeWireCell_dv2snap (dv2_snap)'), samples={})
    for short, old_id, new_id in SAMPLES:
        D = {}
        for lab, tab, sid, tag in (('old', a.old_tables, old_id, a.old_tag), ('split', a.split_tables, new_id, a.tag),
                                   ('snap', a.snap_tables, new_id, a.tag)):
            c, t, f = load(tab, sid, tag, need)
            c = c[c.is_placeholder == 0].reset_index(drop=True)
            D[lab] = dict(c=c, t=t, f=f)
        # restrict to files present in all three domains (the same units)
        common = set(D['old']['f'].file_id) & set(D['split']['f'].file_id) & set(D['snap']['f'].file_id)
        S = dict(files=dict(old=int(len(D['old']['f'])), split=int(len(D['split']['f'])), snap=int(len(D['snap']['f'])), common=len(common)))
        for lab in D:
            D[lab]['c'] = D[lab]['c'][D[lab]['c'].file_id.isin(common)].reset_index(drop=True)
            D[lab]['t'] = D[lab]['t'][D[lab]['t'].file_id.isin(common)]
            D[lab]['f'] = D[lab]['f'][D[lab]['f'].file_id.isin(common)]
        rec = {}
        for lab, d in D.items():
            c, t = d['c'], d['t']
            pre = labels.preselection(c)
            d['pre'] = pre
            mult = c.groupby(EV).size()
            r = dict(events=int(d['f'].events.sum()), wc_events=int(d['f'].wc_events.sum()), candidates=int(len(c)),
                     filled=int((c.shw_sp_filled == 1).sum()), preselected=int(pre.sum()),
                     events_with_candidate=int(len(mult)), cands_per_event_mean=float(mult.mean()), events_with_2plus=int((mult >= 2).sum()),
                     classes={}, nonfinite_preselected={}, ceiling=ceiling(c, t, pre))
            nu = c[(c.partner_kind.astype(str) == 'neutrino') & pre]
            r['preselected_nu_partner_dist_lt_1cm'] = float((nu.dist_sce_cm < 1).mean()) if len(nu) else float('nan')
            for m in MODELS:
                cls, _ = classes(c, m)
                d.setdefault('cls', {})[m] = cls
                X = c[fls[m].columns].to_numpy(np.float64)
                fin = np.isfinite(X).all(1)
                r['classes'][m] = dict(positive=int((cls == 1).sum()), negative=int((cls == 0).sum()),
                                       positive_finite=int(((cls == 1) & fin).sum()), negative_finite=int(((cls == 0) & fin).sum()))
                r['nonfinite_preselected'][m] = int((pre & ~fin).sum())
            rec[lab] = r
        S['reconstruction'] = rec
        # matched-candidate migration, old -> split, old -> snap, split -> snap
        mig = {}
        for x, y in (('old', 'split'), ('old', 'snap'), ('split', 'snap')):
            cx, cy = D[x]['c'].assign(pre=D[x]['pre']), D[y]['c'].assign(pre=D[y]['pre'])
            m = cx.merge(cy, on=KEY, suffixes=('_x', '_y'), how='outer', indicator=True)
            both = m[m._merge == 'both']
            dv = np.sqrt(sum((both['nu_%s_x' % q] - both['nu_%s_y' % q]) ** 2 for q in 'xyz')).to_numpy()
            fb = both[(both.shw_sp_filled_x == 1) & (both.shw_sp_filled_y == 1)]
            ev_x = set(map(tuple, cx[EV].drop_duplicates().to_numpy().tolist())); ev_y = set(map(tuple, cy[EV].drop_duplicates().to_numpy().tolist()))
            mig['%s_to_%s' % (x, y)] = dict(
                matched=int(len(both)), only_in_first=int((m._merge == 'left_only').sum()), only_in_second=int((m._merge == 'right_only').sum()),
                events_with_candidates_only_in_first=len(ev_x - ev_y), events_with_candidates_only_in_second=len(ev_y - ev_x),
                cluster_id_same_frac=float((both.cluster_id_x == both.cluster_id_y).mean()) if len(both) else float('nan'),
                vertex_shift_median_cm=float(np.median(dv)) if len(dv) else float('nan'),
                vertex_shift_gt=dict((str(k), float((dv > k).mean())) for k in (0.1, 1.0, 3.0, 10.0)) if len(dv) else {},
                filled_flip_0_to_1=int(((both.shw_sp_filled_x != 1) & (both.shw_sp_filled_y == 1)).sum()),
                filled_flip_1_to_0=int(((both.shw_sp_filled_x == 1) & (both.shw_sp_filled_y != 1)).sum()),
                preselection_flip_in=int(((~both.pre_x.astype(bool)) & both.pre_y.astype(bool)).sum()),
                preselection_flip_out=int((both.pre_x.astype(bool) & ~both.pre_y.astype(bool)).sum()),
                filled_both=int(len(fb)),
                n20mev_showers_changed_frac=float((fb.shw_sp_n_20mev_showers_x != fb.shw_sp_n_20mev_showers_y).mean()) if len(fb) else float('nan'),
                main_shower_energy_changed_gt1pct_frac=(float((np.abs(fb.shw_sp_energy_y - fb.shw_sp_energy_x) > 0.01 * np.abs(fb.shw_sp_energy_x).clip(1e-9)).mean())
                                                        if len(fb) and 'shw_sp_energy_x' in fb else float('nan')))
        S['migration'] = mig
        # feature shifts and legacy-score migration
        fs, lg = {}, {}
        for m in MODELS:
            cols, names = fls[m].columns, fls[m].names
            fs[m], lg[m] = {}, {}
            for x, y in (('old', 'split'), ('old', 'snap'), ('split', 'snap')):
                px, py = D[x]['pre'], D[y]['pre']
                A, B = D[x]['c'][px], D[y]['c'][py]
                mm = A[KEY + cols].merge(B[KEY + cols], on=KEY, suffixes=('_x', '_y'))
                per = {}
                for col in cols:
                    st = shift_stats(A[col].to_numpy(np.float64), B[col].to_numpy(np.float64))
                    if st is None:
                        continue
                    st['matched_changed_frac'] = float((~np.isclose(mm[col + '_x'].to_numpy(np.float64), mm[col + '_y'].to_numpy(np.float64),
                                                                    rtol=0, atol=0, equal_nan=True)).mean()) if len(mm) else float('nan')
                    st['family'] = family(col)
                    per[col] = st
                ks = np.array([v['ks'] for v in per.values()])
                fam = {}
                for f_ in sorted(set(v['family'] for v in per.values())):
                    k2 = np.array([v['ks'] for v in per.values() if v['family'] == f_])
                    fam[f_] = dict(n=int(len(k2)), median_ks=float(np.median(k2)), max_ks=float(k2.max()))
                top = sorted(per.items(), key=lambda kv: -kv[1]['ks'])[:10]
                fs[m]['%s_to_%s' % (x, y)] = dict(features=len(per), median_ks=float(np.median(ks)), max_ks=float(ks.max()),
                                                  frac_ks_gt_0p1=float((ks > 0.1).mean()), median_abs_std_mean_shift=float(np.median(np.abs([v['std_mean_shift'] for v in per.values()]))),
                                                  median_matched_changed_frac=float(np.median([v['matched_changed_frac'] for v in per.values()])),
                                                  by_family=fam, top10_by_ks={k: {kk: round(vv, 4) if isinstance(vv, float) else vv for kk, vv in v.items()} for k, v in top})
            # legacy score per domain
            sc = {}
            for lab in D:
                c = D[lab]['c']; pre = D[lab]['pre']; cls = D[lab]['cls'][m]
                X = c[cols].to_numpy(np.float64).astype(np.float32)
                fin = np.isfinite(X).all(1)
                s = np.full(len(c), np.nan)
                ok = pre & fin
                s[ok] = lc.legacy_score(forests[m], lc.legacy_matrix(X[ok], names, m))[1]
                sc[lab] = s
                pos, neg = ok & (cls == 1), ok & (cls == 0)
                r = dict(scored=int(ok.sum()), positive=int(pos.sum()), negative=int(neg.sum()),
                         pass_rate_positive=float((s[pos] > HIST_CUT[m]).mean()) if pos.any() else float('nan'),
                         pass_rate_negative=float((s[neg] > HIST_CUT[m]).mean()) if neg.any() else float('nan'),
                         score_quantiles_positive=[float(q) for q in np.quantile(s[pos], [0.1, 0.5, 0.9])] if pos.any() else [],
                         auc=float(roc_auc_score(np.r_[np.ones(pos.sum()), np.zeros(neg.sum())], np.r_[s[pos], s[neg]])) if pos.sum() > 10 and neg.sum() > 10 else float('nan'))
                lg[m][lab] = r
            for x, y in (('old', 'split'), ('old', 'snap'), ('split', 'snap')):
                kx = D[x]['c'][KEY].assign(s=sc[x], cls=D[x]['cls'][m]); ky = D[y]['c'][KEY].assign(s=sc[y])
                mm = kx.merge(ky, on=KEY, suffixes=('_x', '_y')).dropna(subset=['s_x', 's_y'])
                px, py = mm.s_x > HIST_CUT[m], mm.s_y > HIST_CUT[m]
                lg[m]['migration_%s_to_%s' % (x, y)] = dict(
                    matched_scored=int(len(mm)), pass_to_fail=int((px & ~py).sum()), fail_to_pass=int((~px & py).sum()),
                    positive_pass_to_fail=int((px & ~py & (mm.cls == 1)).sum()), positive_fail_to_pass=int((~px & py & (mm.cls == 1)).sum()),
                    spearman=float(mm[['s_x', 's_y']].corr(method='spearman').iloc[0, 1]) if len(mm) > 2 else float('nan'))
        S['feature_shift'] = fs
        S['legacy'] = lg
        res['samples'][short] = S
        print(short, json.dumps(dict(files=S['files'], pre={k: v['preselected'] for k, v in rec.items()},
                                     ceiling={k: round(v['ceiling']['with_preselected_frac'], 4) for k, v in rec.items()}), default=str), flush=True)
    json.dump(res, open(a.out_json, 'w'), indent=1, default=str)


if __name__ == '__main__':
    main()
