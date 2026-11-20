#!/usr/bin/env python3
"""VALIDATION-ONLY operating-point machinery for the four SP BDTs, and the JOINT four-cut evaluator (WCL1116 development;
NESTED VALIDATION rows only; no threshold is chosen or frozen; no FermiGrid product).

  python sp_operating_points.py --mode MODE --tables DIR --tag dev --bundle-root LEGACY --studies-dir $SP_WORK/wcl1116_full_dev/studies/MODE \
      --topology-dir $SP_WORK/wcl1116_full_dev/truth_topology --out-json validation/sp_operating_points_MODE.json \
      --tables-out validation/op_tables --work-out $SP_WORK/wcl1116_full_dev/op/MODE

Per model (FIT_BASELINE model; its own classes; NESTED VALIDATION rows):
  legacy historical cut; new model at equal legacy signal efficiency (A) and at equal legacy background acceptance (B);
  thinned ROC and precision-recall curves; monotonic threshold table with component acceptances; signal efficiency by
  truth topology (0p / 1p / >=2p, post-FSI primary protons > 35 MeV) and by Delta charge.
Joint evaluator (every preselected NESTED-VALIDATION row of NC Delta, BNB, nu_e CC and the EXT training half):
  cuts applied in production order numu -> other -> ncpi0 -> nue; a row with a non-finite input of a model fails that
  model's cut (TMVA reader: -999); per model, thresholds at its own pooled-signal efficiency 0.50 ... 0.98 / no cut (9^4
  vectors; 0.50-0.70 added after the first run, see LEVELS); NC Delta signal efficiency (total and by topology), BNB background acceptance and its
  components, EXT and nu_e CC acceptance; the Pareto front (NC Delta efficiency vs BNB background acceptance); two
  reference points: LEGACY_HISTORICAL (legacy XMLs at 0.4 / 0.2 / -0.05 / -1.0) and DEV_ROC_EQUIVALENT (each development
  model at its point A). DEVELOPMENT ROC-EQUIVALENT DIAGNOSTIC -- NOT ROUND2 CUT. Rates are per candidate row of each
  sample; samples are never mixed with exposure weights (none are available for the filtered samples).
"""
import argparse
import itertools
import json
import os
import sys

import numpy as np
import pandas as pd

ROUND2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROUND2); sys.path.insert(0, os.path.join(ROUND2, 'tools'))
from sp_retrain import devstudy as dv, devtrain, features, firewall, labels, legacy_control as lc, provenance  # noqa: E402

ORDER = ('numu', 'other', 'ncpi0', 'nue')           # production selection order
CLF = {m: 'single_photon_' + m for m in ORDER}
# 0.80-0.98 / no cut were pre-declared; 0.50 / 0.60 / 0.70 were ADDED after the first run because the pre-declared grid
# never reached the legacy joint BNB background acceptance (reporting coverage only; no threshold is chosen)
LEVELS = (0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 0.95, 0.98, None)
ALLOWED_OUTPUT = ['/lus/flare/projects/neutrinoGPU/abhat/sbnd']
NCDR, BNB, NUECC, EXT = 'wcl1116-aurora-ncdr', 'wcl1116-aurora-bnb', 'wcl1116-aurora-nuecc', 'wcl1116-fg-beamoff-train'


def spec_of(model, mode):
    return labels.load_spec(os.path.join(ROUND2, 'specs', 'single_photon_%s_training_spec_dev_wcl1116_%s.yaml' % (model, mode)))


def thin(x, y, t, n=200):
    idx = np.unique(np.linspace(0, len(x) - 1, min(n, len(x))).astype(int))
    return pd.DataFrame(dict(x=np.asarray(x)[idx], y=np.asarray(y)[idx], threshold=np.asarray(t)[idx]))


def load_topology(d):
    return pd.concat([pd.read_parquet(os.path.join(d, 'topology_%s.parquet' % s)) for s in (NCDR, BNB)], ignore_index=True)


def by_topology(R, passed):
    out = {}
    for name, q in (('0p', R.topology == 0), ('1p', R.topology == 1), ('>=2p', R.topology >= 2), ('Delta0', R.delta_charge == 'Delta0'),
                    ('Delta+', R.delta_charge == 'Delta+'), ('unmatched', R.topology < 0)):
        q = q.to_numpy()
        out[name] = dict(rows=int(q.sum()), efficiency=float(np.asarray(passed)[q].mean()) if q.any() else None)
    return out


def per_model(model, mode, a, topo, xgb):
    from sklearn.metrics import precision_recall_curve, roc_curve
    spec = spec_of(model, mode); clf = CLF[model]; cols = features.load(clf).columns
    C, ds, roles = dv.load_dataset(spec, a.tables, a.tag)
    keys, X, y = ds['keys'], ds['X'], ds['y']
    nv = roles == dv.ROLE_NVAL
    bst = xgb.Booster(); bst.load_model(os.path.join(a.studies_dir, model, 'FIT_BASELINE_%s_%s.json' % (model, mode)))
    m = dv.margin(xgb, bst, X[nv], cols); leg = dv.legacy_scores(a.bundle_root, clf, X[nv], cols); yy = y[nv]
    R = dv.row_truth(C, keys[nv].reset_index(drop=True))
    comp = np.where(yy == 1, 'signal', np.where(R.partner_kind.astype(str) != 'neutrino', 'partner_' + R.partner_kind.astype(str), R.m_sp_bkg.astype(str)))
    comp = np.where(R['sample'].astype(str).isin(labels.ext_sample_ids(spec)), 'beam_off_ext', comp)
    comps = tuple(sorted(set(comp[yy == 0])))
    cut = lc.LEGACY_CUT[clf]
    op = dv.op_points(yy, m, leg, cut)
    tt = dv.threshold_table(yy, m, comp, comps)
    fpr, tpr, thr = roc_curve(yy, m); pr, rc, pthr = precision_recall_curve(yy, m)
    os.makedirs(a.tables_out, exist_ok=True)
    tt.to_csv(os.path.join(a.tables_out, 'threshold_table_%s_%s.csv' % (model, mode)), index=False, float_format='%.6g')
    thin(fpr, tpr, thr).rename(columns=dict(x='background_acceptance', y='signal_efficiency')).to_csv(
        os.path.join(a.tables_out, 'roc_%s_%s.csv' % (model, mode)), index=False, float_format='%.6g')
    thin(rc[:-1], pr[:-1], pthr).rename(columns=dict(x='recall', y='precision')).to_csv(
        os.path.join(a.tables_out, 'pr_%s_%s.csv' % (model, mode)), index=False, float_format='%.6g')
    S = dv.attach_topology(R[yy == 1].reset_index(drop=True), topo) if model else None
    ncdr = (S['sample'] == NCDR).to_numpy()
    tA, tB = op['A_equal_signal_efficiency']['cut'], op['B_equal_background_acceptance']['cut']
    ms, ls = m[yy == 1], leg[yy == 1]
    topo_res = dict(legacy_at_historical_cut=by_topology(S[ncdr], (ls > cut)[ncdr]), dev_at_A=by_topology(S[ncdr], (ms > tA)[ncdr]),
                    dev_at_B=by_topology(S[ncdr], (ms > tB)[ncdr]), note='NC Delta sample signal rows (NESTED VALIDATION)')
    return dict(model=clf, rows=dict(pos=int((yy == 1).sum()), neg=int((yy == 0).sum())), roc_pr=dv.roc_pr(yy, m), legacy_roc_pr=dv.roc_pr(yy, leg),
                op=op, components_at_A=dv.component_acceptance(comp, m > tA, comps), components_legacy=dv.component_acceptance(comp, leg > cut, comps),
                threshold_table_monotonic=dv.is_monotonic(tt), topology=topo_res,
                tables=['threshold_table_%s_%s.csv' % (model, mode), 'roc_%s_%s.csv' % (model, mode), 'pr_%s_%s.csv' % (model, mode)]), tA


def joint_frame(mode, a, topo):
    """Every preselected NESTED-VALIDATION row of the four training-side samples, with all four input sets."""
    other, nue = spec_of('other', mode), spec_of('nue', mode)
    entries = {s['id']: s for s in other['samples']['development'] + nue['samples']['development']}
    stamp = json.load(open(os.path.join(os.path.dirname(ROUND2), other['samples']['input_manifest'])))['reconstruction']['wct_version_stamp']
    need = sorted(set(sum((features.load(CLF[m]).columns for m in ORDER), [])))
    truth = ['partner_kind', 'm_sp_truth_ok', 'm_sp_signal', 'm_sp_bkg', 'm_pdg', 'm_E', 'm_vx', 'm_vy', 'm_vz', 'm_sp_category', 'is_placeholder',
             'shw_sp_n_20mev_showers', 'label_unreadable']
    parts = []
    for sid in (NCDR, BNB, NUECC, EXT):
        F = pd.read_parquet(os.path.join(a.tables, 'files_%s_%s.parquet' % (sid, a.tag)))
        st = provenance.expected_sample_stamp(entries[sid], stamp)
        path = os.path.join(a.tables, 'cands_%s_%s.parquet' % (sid, a.tag))
        import pyarrow.parquet as pq
        have = set(pq.read_schema(path).names)
        want = devtrain.ROW_KEY + sorted(set(need + truth) - set(devtrain.ROW_KEY))
        if not set(need) <= have:
            raise SystemExit('%s lacks model inputs %s' % (sid, sorted(set(need) - have)[:5]))
        cs = pd.read_parquet(path, columns=[c for c in want if c in have])
        for c in truth:                       # off-beam data carry no truth: no partner, no class
            if c not in cs.columns:
                cs[c] = {'partner_kind': 'none', 'm_sp_bkg': ''}.get(c, np.nan)
        cs = cs[~cs.file_id.isin(set(F[F.wct_version.fillna('') != st].file_id))]
        pre = labels.preselection(cs, ext_ids=(EXT,))
        cs = cs[pre].reset_index(drop=True)
        cs['split'] = np.where(cs['sample'] == EXT, np.where(cs.run % 4 == 1, 'test', 'train'), np.where(cs.subrun % 2 == 1, 'test', 'train'))
        cs['role'] = dv.nested_roles(cs)
        parts.append(cs[cs.role == dv.ROLE_NVAL])
    J = pd.concat(parts, ignore_index=True)
    sig = ((J.partner_kind.astype(str) == 'neutrino') & (J.m_sp_truth_ok.fillna(0) == 1) & (J.m_sp_signal.fillna(0) == 1) & (J['sample'] != EXT)).to_numpy()
    J['signal'] = sig
    J['bkg_class'] = np.where(J['sample'] == EXT, 'beam_off_ext', np.where(J.partner_kind.astype(str) != 'neutrino', 'partner_' + J.partner_kind.astype(str),
                                                                        np.where(J.m_sp_bkg.astype(str) == '', 'unclassified', J.m_sp_bkg.astype(str))))
    J.loc[sig, 'bkg_class'] = 'signal'
    T = dv.attach_topology(J[sig][devtrain.ROW_KEY + ['m_pdg', 'm_E', 'm_vx', 'm_vy', 'm_vz']].reset_index(drop=True), topo)
    J['topology'] = -1; J['delta_charge'] = ''
    J.loc[np.flatnonzero(sig), 'topology'] = T.topology.to_numpy(); J.loc[np.flatnonzero(sig), 'delta_charge'] = T.delta_charge.to_numpy()
    return J


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    for k in ('--mode', '--tables', '--tag', '--bundle-root', '--studies-dir', '--topology-dir', '--out-json', '--tables-out', '--work-out'):
        ap.add_argument(k, required=True)
    a = ap.parse_args()
    import xgboost as xgb
    firewall.check_output_path(a.work_out, ALLOWED_OUTPUT); os.makedirs(a.work_out, exist_ok=True)
    topo = load_topology(a.topology_dir)
    out = dict(label='VALIDATION-ONLY OPERATING POINTS (WCL1116 development, NESTED VALIDATION) -- DEVELOPMENT ROC-EQUIVALENT DIAGNOSTIC, NOT ROUND2 CUT; NO THRESHOLD FROZEN',
               mode=a.mode, models={})
    pointA = {}
    for m in ORDER:
        out['models'][m], pointA[m] = per_model(m, a.mode, a, topo, xgb)
        print(m, json.dumps({k: out['models'][m][k] for k in ('rows', 'roc_pr', 'legacy_roc_pr')}), 'A', round(out['models'][m]['op']['A_equal_signal_efficiency']['background_acceptance'], 4))
    # ---------------- joint four-cut evaluator
    J = joint_frame(a.mode, a, topo)
    dev, leg = {}, {}
    for m in ORDER:
        cols = features.load(CLF[m]).columns
        X64 = J[cols].to_numpy(np.float64); fin = np.isfinite(X64).all(1) & np.isfinite(X64.astype(np.float32)).all(1)
        X = np.nan_to_num(X64, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
        bst = xgb.Booster(); bst.load_model(os.path.join(a.studies_dir, m, 'FIT_BASELINE_%s_%s.json' % (m, a.mode)))
        dev[m] = np.where(fin, dv.margin(xgb, bst, X, cols), -np.inf)
        leg[m] = np.where(fin, dv.legacy_scores(a.bundle_root, CLF[m], X, cols), -999.0)
    sig = J.signal.to_numpy(); smp = J['sample'].to_numpy()
    ncdr_sig = sig & (smp == NCDR); bnb_bkg = (~sig) & (smp == BNB)
    thr = {m: {lev: (lc.threshold_for_rate(dev[m][sig], lev) if lev is not None else -np.inf) for lev in LEVELS} for m in ORDER}
    bkg_classes = sorted(set(J.bkg_class[bnb_bkg]))

    def summarize(passed):
        r = dict(ncdr_signal_eff=float(passed[ncdr_sig].mean()), all_signal_eff=float(passed[sig].mean()),
                 bnb_bkg_acc=float(passed[bnb_bkg].mean()), ext_acc=float(passed[(smp == EXT)].mean()) if (smp == EXT).any() else None,
                 nuecc_nueccbkg_acc=float(passed[(smp == NUECC) & (J.bkg_class.to_numpy() == 'nueCCBkg')].mean()))
        for t, q in (('0p', J.topology.to_numpy() == 0), ('1p', J.topology.to_numpy() == 1), ('>=2p', J.topology.to_numpy() >= 2)):
            q = q & ncdr_sig; r['ncdr_eff_' + t] = float(passed[q].mean()) if q.any() else None
        for c in bkg_classes:
            q = bnb_bkg & (J.bkg_class.to_numpy() == c); r['bnb_acc_' + c] = float(passed[q].mean()) if q.any() else None
        return r

    def cascade(cuts, scores):
        p = np.ones(len(J), bool); steps = []
        for m in ORDER:                                  # production order
            p = p & (scores[m] > cuts[m]); steps.append(dict(after=m, ncdr_signal_eff=float(p[ncdr_sig].mean()), bnb_bkg_acc=float(p[bnb_bkg].mean())))
        return p, steps

    rows = []
    for combo in itertools.product(LEVELS, repeat=4):
        cuts = {m: thr[m][lev] for m, lev in zip(ORDER, combo)}
        p, _ = cascade(cuts, dev)
        rows.append(dict({'level_' + m: (lev if lev is not None else 'none') for m, lev in zip(ORDER, combo)}, **summarize(p)))
    G = pd.DataFrame(rows)
    order = G.sort_values(['bnb_bkg_acc', 'ncdr_signal_eff'], ascending=[True, False])
    best = -1.0; front = []
    for i, r in order.iterrows():
        if r.ncdr_signal_eff > best + 1e-12:
            front.append(i); best = r.ncdr_signal_eff
    G['pareto'] = G.index.isin(front)
    G.to_csv(os.path.join(a.work_out, 'joint_grid_%s.csv' % a.mode), index=False, float_format='%.6g')
    G[G.pareto].sort_values('bnb_bkg_acc').to_csv(os.path.join(a.tables_out, 'joint_pareto_%s.csv' % a.mode), index=False, float_format='%.6g')
    pL, sL = cascade({m: lc.LEGACY_CUT[CLF[m]] for m in ORDER}, leg)
    pA, sA = cascade(pointA, dev)
    refL, refA = summarize(pL), summarize(pA)
    # the development front at the legacy joint background acceptance (diagnostic, not a choice)
    cand = G[G.bnb_bkg_acc <= refL['bnb_bkg_acc'] + 1e-12].sort_values('ncdr_signal_eff', ascending=False)
    out['joint'] = dict(
        order=list(ORDER), levels=[l if l is not None else 'none' for l in LEVELS], vectors=int(len(G)), pareto_points=int(G.pareto.sum()),
        rows=dict(ncdr_signal=int(ncdr_sig.sum()), all_signal=int(sig.sum()), bnb_background=int(bnb_bkg.sum()), ext=int((smp == EXT).sum()),
                  nuecc_nueccbkg=int(((smp == NUECC) & (J.bkg_class.to_numpy() == 'nueCCBkg')).sum()),
                  ncdr_signal_by_topology={t: int((ncdr_sig & q).sum()) for t, q in (('0p', J.topology.to_numpy() == 0), ('1p', J.topology.to_numpy() == 1), ('>=2p', J.topology.to_numpy() >= 2))},
                  events_with_multiple_preselected_candidates=int(J.groupby(devtrain.EV).size().gt(1).sum())),
        LEGACY_HISTORICAL=dict(cuts={m: lc.LEGACY_CUT[CLF[m]] for m in ORDER}, cascade=sL, **refL),
        DEV_ROC_EQUIVALENT=dict(cuts=pointA, cascade=sA, **refA),
        DEV_FRONT_AT_LEGACY_BNB_ACCEPTANCE=(dict(cand.iloc[0].to_dict()) if len(cand) else None),
        pareto_csv='joint_pareto_%s.csv' % a.mode, grid_csv=os.path.join(a.work_out, 'joint_grid_%s.csv' % a.mode),
        note='per-row rates per sample; no exposure weighting; no threshold vector chosen')
    json.dump(out, open(a.out_json, 'w'), indent=1, default=lambda o: o if not isinstance(o, (np.floating, np.integer)) else o.item())
    print('joint', json.dumps({k: out['joint'][k] for k in ('vectors', 'pareto_points', 'rows')}))
    for k in ('LEGACY_HISTORICAL', 'DEV_ROC_EQUIVALENT', 'DEV_FRONT_AT_LEGACY_BNB_ACCEPTANCE'):
        r = out['joint'][k] or {}
        print(k, {x: (round(r[x], 4) if isinstance(r.get(x), float) else r.get(x)) for x in ('ncdr_signal_eff', 'bnb_bkg_acc', 'ncdr_eff_0p', 'ncdr_eff_1p', 'ncdr_eff_>=2p', 'ext_acc', 'nuecc_nueccbkg_acc')})


if __name__ == '__main__':
    main()
