#!/usr/bin/env python3
"""Dry-run class census for the single_photon_ncpi0 development target. No model is trained.

  python ncpi0_class_census.py --tables DIR --tag TAG --samples s1 s2 ... --spec SPEC.yaml --out census.json

Per sample: preselected candidate rows by class (sp_retrain.labels.ncpi0_development_classes), events per class and with
both classes, candidate multiplicity, truth composition of each class, the truth-level reach (true signal / NC pi0
neutrinos that own a preselected candidate), missing-input rates on the 45 inputs, counts per split fold, and the
sensitivity of the classes to the SBND mapping choices (photon origin A1b, all-pi0 A6b, an illustrative |x| cut).
"""
import argparse, hashlib, json, os, sys

import numpy as np
import pandas as pd

ROUND2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROUND2)
from sp_retrain import features, labels, split  # noqa: E402

EV = ['sample', 'file_id', 'run', 'subrun', 'event']


def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def vc(s):
    return {str(k): int(v) for k, v in s.value_counts().sort_index().items()}


def census(C, T, F, spec, names):
    cls, pre = labels.ncpi0_development_classes(C, spec)
    C = C.assign(cls=cls, pre=pre, split=split.assign(C['sample'], C.run, C.subrun))
    P = C[C.pre]
    out = dict(files=int(len(F)), events=int(F.events.sum()), wc_events=int(F.wc_events.sum()), candidates=int(len(C)),
               preselected=int(len(P)), positive=int((P.cls == 1).sum()), negative=int((P.cls == 0).sum()),
               excluded=int((P.cls == -1).sum()))
    ex = P[P.cls == -1]
    reason = np.where(ex.partner_kind.astype(str) != 'neutrino', 'partner_' + ex.partner_kind.astype(str),
                      np.where(ex.m_sp_truth_ok.fillna(0) != 1, 'truth_unreadable', 'bkg_' + ex.m_sp_bkg.astype(str)))
    out['excluded_by_reason'] = vc(pd.Series(reason))
    g = P.groupby(EV)
    ev = pd.DataFrame(dict(n=g.size(), npos=g.cls.apply(lambda s: int((s == 1).sum())), nneg=g.cls.apply(lambda s: int((s == 0).sum()))))
    out['events_with_preselected_candidate'] = int(len(ev))
    out['events_with_positive'] = int((ev.npos > 0).sum()); out['events_with_negative'] = int((ev.nneg > 0).sum())
    out['events_with_both'] = int(((ev.npos > 0) & (ev.nneg > 0)).sum())
    out['events_with_two_or_more_positive'] = int((ev.npos > 1).sum())
    mult = ev.n.clip(upper=4).map({1: '1', 2: '2', 3: '3', 4: '4+'})
    out['multiplicity_all'] = vc(mult); out['multiplicity_positive_events'] = vc(mult[ev.npos > 0]); out['multiplicity_negative_events'] = vc(mult[ev.nneg > 0])
    out['positive_by_category'] = vc(P[P.cls == 1].m_sp_category.astype(str))
    out['negative_by_n_prim_pi0'] = vc(P[P.cls == 0].m_sp_n_prim_pi0.astype(int).clip(upper=3).astype(str).replace({'3': '3+'}))
    out['negative_pair_merged_never'] = int((P[P.cls == 0].m_sp_pair_merged == 1).sum())
    out['by_split'] = {k: dict(positive=int(((P.cls == 1) & (P.split == k)).sum()), negative=int(((P.cls == 0) & (P.split == k)).sum()))
                       for k in ('train', 'validation', 'test')}
    X = P[names].to_numpy(np.float64)
    bad = ~np.isfinite(X)
    for c, lab in ((1, 'positive'), (0, 'negative')):
        m = (P.cls == c).to_numpy()
        out['missing_inputs_%s' % lab] = dict(rows_with_any_nonfinite=int(bad[m].any(1).sum()),
                                              by_input={names[j]: int(bad[m, j].sum()) for j in range(len(names)) if bad[m, j].any()})
    out['shw_sp_filled_share'] = {lab: float(P[P.cls == c].shw_sp_filled.mean()) if (P.cls == c).any() else None for c, lab in ((1, 'positive'), (0, 'negative'))}
    # truth level: who owns a preselected candidate
    Tk = T[T.sp_truth_ok == 1]
    own = set(map(tuple, P[P.partner_kind.astype(str) == 'neutrino'][EV + ['m_nu_idx']].astype({'m_nu_idx': int}).to_numpy().tolist()))
    tkey = [tuple(r) for r in Tk[EV + ['nu_idx']].to_numpy().tolist()]
    reach = np.array([k in own for k in tkey], bool)
    sig = (Tk.sp_signal == 1).to_numpy(); negt = (Tk.sp_bkg.astype(str) == 'NCpi0Bkg').to_numpy()
    out['truth'] = dict(neutrinos=int(len(Tk)), truth_unreadable=int((T.sp_truth_ok != 1).sum()),
                        signal=int(sig.sum()), signal_by_category=vc(Tk[sig].sp_category.astype(str)),
                        signal_with_preselected_candidate=int((sig & reach).sum()),
                        ncpi0_background=int(negt.sum()), ncpi0_background_with_preselected_candidate=int((negt & reach).sum()))
    # sensitivity to the mapping choices
    nu = (P.partner_kind.astype(str) == 'neutrino') & (P.m_sp_truth_ok.fillna(0) == 1)
    pos_a1b = nu & (P.m_sp_signal_a1b.fillna(0) == 1)
    out['sensitivity'] = dict(
        a1b_positive=int(pos_a1b.sum()), a1b_changes_positive=int((pos_a1b != (P.cls == 1)).sum()),
        a6b_all_pi0_negative=int((nu & (P.m_sp_signal.fillna(0) == 0) & (P.m_sp_vtx_in_fv3 == 1) & (P.m_sp_n_pi0_all.fillna(0) > 0)
                                  & (P.m_ccnc == 1)).sum()))
    xcls, xpre = labels.ncpi0_development_classes(C, spec, x_cut=(5.0, 196.3))
    out['sensitivity']['xcut_5_196p3'] = dict(preselected=int(xpre.sum()), positive=int((xcls == 1).sum()), negative=int((xcls == 0).sum()))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--tables', required=True); ap.add_argument('--tag', default='census'); ap.add_argument('--samples', nargs='+', required=True)
    ap.add_argument('--spec', required=True); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    spec = labels.load_spec(a.spec)
    names = features.load('single_photon_ncpi0').columns
    res = dict(spec=os.path.relpath(a.spec, ROUND2), spec_sha256=sha(a.spec), spec_version=spec['spec_version'],
               code_sha256={f: sha(os.path.join(ROUND2, f)) for f in ('sp_retrain/sp_truth.py', 'sp_retrain/labels.py', 'sp_retrain/build_tables.py', 'sp_retrain/split.py', 'tools/ncpi0_class_census.py')},
               tables=os.path.abspath(a.tables), samples={})
    for s in a.samples:
        p = lambda t: os.path.join(a.tables, '%s_%s_%s.parquet' % (t, s, a.tag))
        C, T, F = pd.read_parquet(p('cands')), pd.read_parquet(p('truth')), pd.read_parquet(p('files'))
        b = json.load(open(os.path.join(a.tables, 'build_%s_%s.json' % (s, a.tag))))
        r = census(C, T, F, spec, names); r['build'] = dict(slice=b['slice'], list_sha256=b['list_sha256'], errors=b['errors'], code=b['code'])
        res['samples'][s] = r
        print(s, json.dumps({k: r[k] for k in ('files', 'preselected', 'positive', 'negative', 'excluded', 'events_with_both')}))
    json.dump(res, open(a.out, 'w'), indent=1)


if __name__ == '__main__':
    main()
