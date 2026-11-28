#!/usr/bin/env python3
"""Controlled DEVELOPMENT comparison of upstream-classifier domains for the four downstream SP BDTs (one vertex mode).

Domains (sp_retrain/upstream_overlay.py): A stored WCL1116 (shipped upstream weights), B nu_mu numu_round3af,
C nu_e nue_round4_ruleA_v2 (main), D both. Per SP model only the domains that change its inputs are distinct:
SP numu / SP other: A, B (= D); SP ncpi0: A, C (= D); SP nue: A only (no upstream input).

Per model and domain, on IDENTICAL rows (same preselection, classes, nested_v1 roles; checked):
  legacy    the inherited MicroBooNE XML on the domain's inputs, at its historical cut
  fixed     the domain-A development model (FIT_BASELINE of the WCL1116 full-development study, trained on FIT) applied
            unchanged to the domain's inputs, at its domain-A point A (legacy-equal signal efficiency)
  retrained the same frozen development spec (features, hyperparameters, seed) refitted on FIT of the domain
Reported on NESTED VALIDATION (choices) and the existing DEVELOPMENT HOLDOUT (reported separately): ROC AUC, score shifts,
pass/fail migration at fixed thresholds, background acceptance at the domain-A per-model signal efficiency, and the
NESTED-VALIDATION AUC split by Xuyang's upstream training role (split_v11 'dev' slice vs 'train').
Joint four-cut cascade per domain (production order numu -> other -> ncpi0 -> nue, NESTED VALIDATION of all four samples):
  LEGACY_HISTORICAL, DEV_FIXED (domain-A models and thresholds), DEV_RETRAINED (domain models at the domain-A per-model
  signal efficiencies), plus the retrained-model grid / Pareto front. Domain A must reproduce the WCL1116 reference.
DEVELOPMENT ONLY: no FermiGrid product, no threshold / model / mode frozen, Xuyang's CC working points never used.

  python tools/upstream_domain_study.py --mode M --tables T --tag dev --bundle-root LEGACY --studies-dir S --overlay-dir O \
      --topology-dir TOPO --reference-json validation/sp_operating_points_M.json --out-json OUT --work-out WORK
"""
import argparse, itertools, json, os, sys

import numpy as np
import pandas as pd

ROUND2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROUND2); sys.path.insert(0, os.path.join(ROUND2, 'tools'))
from sp_retrain import devstudy as dv, devtrain, features, firewall, labels, legacy_control as lc, upstream_overlay as uo  # noqa: E402
import sp_operating_points as spo  # noqa: E402
from legacy_control_compare import load_cands  # noqa: E402

ORDER = spo.ORDER
MODEL_DOMAINS = {'numu': ['A', 'B'], 'other': ['A', 'B'], 'ncpi0': ['A', 'C'], 'nue': ['A']}
ALLOWED_OUTPUT = ['/lus/flare/projects/neutrinoGPU/abhat/sbnd']


def model_domain(m, d):
    """The per-model domain a joint domain d implies."""
    if m in ('numu', 'other'):
        return 'B' if d in ('B', 'D') else 'A'
    if m == 'ncpi0':
        return 'C' if d in ('C', 'D') else 'A'
    return 'A'


def flips(a, b):
    a = np.asarray(a, bool); b = np.asarray(b, bool)
    return dict(n=int(len(a)), pass_A=int(a.sum()), pass_d=int(b.sum()), lost=int((a & ~b).sum()), gained=int((~a & b).sum()))


def shift(x0, x1):
    d = np.asarray(x1, np.float64) - np.asarray(x0, np.float64)
    ad = np.abs(d)
    return dict(n=int(len(d)), changed=int((ad > 0).sum()), mean=float(d.mean()) if len(d) else 0.0, median_abs=float(np.median(ad)) if len(d) else 0.0,
                p95_abs=float(np.quantile(ad, 0.95)) if len(d) else 0.0, max_abs=float(ad.max()) if len(d) else 0.0)


def auc(y, s):
    return dv.roc_pr(y, s)['roc_auc'] if len(set(np.asarray(y).tolist())) == 2 else None


def threshold_at_eff(s_sig, eff):
    return lc.threshold_for_rate(np.asarray(s_sig), eff)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    for k in ('--mode', '--tables', '--tag', '--bundle-root', '--studies-dir', '--overlay-dir', '--topology-dir', '--reference-json', '--out-json', '--work-out'):
        ap.add_argument(k, required=True)
    a = ap.parse_args()
    import xgboost as xgb
    firewall.check_output_path(a.work_out, ALLOWED_OUTPUT); os.makedirs(a.work_out, exist_ok=True)
    ref = json.load(open(a.reference_json))
    topo = spo.load_topology(a.topology_dir)
    out = dict(label='UPSTREAM-DOMAIN DEVELOPMENT COMPARISON (WCL1116, NESTED VALIDATION; holdout reported separately) -- DEVELOPMENT ONLY, '
                     'NOTHING FROZEN, NOT ROUND2', mode=a.mode, domains=uo.DOMAIN_LABEL, model_domains=MODEL_DOMAINS, models={})
    boosters, tA, eps, legacy_cut = {}, {}, {}, {}
    for m in ORDER:
        spec = spo.spec_of(m, a.mode); clf = spo.CLF[m]; cols = features.load(clf).columns
        params, rounds = devtrain.xgb_params(spec)
        C0 = load_cands(a.tables, a.tag, spec, [])
        dsA = devtrain.build_dataset(C0, spec)
        keys, y = dsA['keys'], dsA['y']
        roles = dv.nested_roles(keys)
        fit, nv, te = roles == dv.ROLE_FIT, roles == dv.ROLE_NVAL, roles == dv.ROLE_TEST
        xn = uo.xn_split_v11(keys['sample'], keys['run'], keys['subrun'])
        b0 = xgb.Booster(); b0.load_model(os.path.join(a.studies_dir, m, 'FIT_BASELINE_%s_%s.json' % (m, a.mode)))
        cut = lc.LEGACY_CUT[clf]; legacy_cut[m] = cut
        legA = dv.legacy_scores(a.bundle_root, clf, dsA['X'], cols); fixA = dv.margin(xgb, b0, dsA['X'], cols)
        opA = dv.op_points(y[nv], fixA[nv], legA[nv], cut)
        tA[m] = opA['A_equal_signal_efficiency']['cut']
        eps[m] = float((legA[nv][y[nv] == 1] > cut).mean())
        refauc = ref['models'][m]['roc_pr']['roc_auc']
        R = dict(model=clf, rows={r: dict(pos=int(((roles == r) & (y == 1)).sum()), neg=int(((roles == r) & (y == 0)).sum())) for r in (dv.ROLE_FIT, dv.ROLE_NVAL, dv.ROLE_TEST)},
                 reference_nval_auc=refauc, reproduced_nval_auc=auc(y[nv], fixA[nv]), point_A_threshold=tA[m], legacy_signal_eff_nval_A=eps[m],
                 xn_split_v11_nval=dict(pd.Series(xn[nv]).value_counts()), domains={})
        scores = keys[devtrain.ROW_KEY].assign(role=roles, y=y, xn_split=xn, legacy_A=legA, fixed_A=fixA)
        for d in MODEL_DOMAINS[m]:
            Cd = C0 if d == 'A' else uo.apply(C0, d, a.overlay_dir)
            ds = devtrain.build_dataset(Cd, spec)
            same = len(ds['keys']) == len(keys) and (ds['keys'][devtrain.ROW_KEY].reset_index(drop=True).equals(keys[devtrain.ROW_KEY].reset_index(drop=True))) and (ds['y'] == y).all()
            if not same:
                raise SystemExit('%s domain %s: rows differ from domain A (preselection / non-finite exclusion changed)' % (m, d))
            X = ds['X']
            leg = legA if d == 'A' else dv.legacy_scores(a.bundle_root, clf, X, cols)
            fix = fixA if d == 'A' else dv.margin(xgb, b0, X, cols)
            br = dv.fit(xgb, params, rounds, X[fit], y[fit], cols, None)
            ret = dv.margin(xgb, br, X, cols)
            br.save_model(os.path.join(a.work_out, 'RETRAINED_%s_%s_%s.json' % (m, a.mode, d)))
            boosters[(m, d)] = br
            replaced = uo.DOMAINS[d] and [c for c in uo.DOMAINS[d] if c in cols]
            ch_rows = int((np.abs(X[:, [cols.index(c) for c in replaced]] - dsA['X'][:, [cols.index(c) for c in replaced]]) > 0).any(1).sum()) if replaced else 0
            D = dict(replaced_inputs=replaced or [], rows_with_changed_inputs=ch_rows, rows_total=int(len(y)))
            if replaced:
                from scipy.stats import ks_2samp
                qs = [0.05, 0.25, 0.5, 0.75, 0.95]
                fs = {}
                for c in replaced:
                    j = cols.index(c); x0, x1 = dsA['X'][:, j].astype(np.float64), X[:, j].astype(np.float64)
                    fs[c] = dict(changed_rows=int((x0 != x1).sum()))
                    for cls, q in (('signal', y == 1), ('background', y == 0)):
                        fs[c][cls] = dict(q_stored=np.quantile(x0[q], qs).round(5).tolist(), q_new=np.quantile(x1[q], qs).round(5).tolist(),
                                          ks=float(ks_2samp(x0[q], x1[q]).statistic), changed=int((x0[q] != x1[q]).sum()), rows=int(q.sum()))
                D['feature_shift'] = fs
            if d == 'A':
                D['retrained_vs_fixed_max_abs'] = float(np.abs(ret - fixA).max())
            tR = threshold_at_eff(ret[nv][y[nv] == 1], eps[m])
            for role, q in (('nval', nv), ('holdout', te)):
                yy = y[q]
                blk = dict(auc=dict(legacy=auc(yy, leg[q]), fixed=auc(yy, fix[q]), retrained=auc(yy, ret[q])),
                           shift_fixed=shift(fixA[q], fix[q]), shift_legacy=shift(legA[q], leg[q]),
                           migration_legacy_at_cut=dict(signal=flips(legA[q][yy == 1] > cut, leg[q][yy == 1] > cut), background=flips(legA[q][yy == 0] > cut, leg[q][yy == 0] > cut)),
                           migration_fixed_at_A=dict(signal=flips(fixA[q][yy == 1] > tA[m], fix[q][yy == 1] > tA[m]), background=flips(fixA[q][yy == 0] > tA[m], fix[q][yy == 0] > tA[m])),
                           fixed_at_A=dict(signal_eff=float((fix[q][yy == 1] > tA[m]).mean()), background_acc=float((fix[q][yy == 0] > tA[m]).mean())),
                           retrained_at_eps=dict(threshold=tR, signal_eff=float((ret[q][yy == 1] > tR).mean()), background_acc=float((ret[q][yy == 0] > tR).mean())),
                           legacy_at_cut=dict(signal_eff=float((leg[q][yy == 1] > cut).mean()), background_acc=float((leg[q][yy == 0] > cut).mean())))
                if role == 'nval':
                    blk['by_xn_split_v11'] = {g: dict(rows=int((xn[q] == g).sum()), auc_fixed=auc(yy[xn[q] == g], fix[q][xn[q] == g]),
                                                      auc_retrained=auc(yy[xn[q] == g], ret[q][xn[q] == g]), auc_legacy=auc(yy[xn[q] == g], leg[q][xn[q] == g]))
                                              for g in ('dev', 'train')}
                D[role] = blk
            R['domains'][d] = D
            scores['legacy_' + d] = leg; scores['fixed_' + d] = fix; scores['retrained_' + d] = ret
            print(m, d, json.dumps({'auc_nval': D['nval']['auc'], 'changed_rows': ch_rows, 'fixed_at_A': D['nval']['fixed_at_A'], 'retrained_at_eps': D['nval']['retrained_at_eps']}), flush=True)
        scores.to_parquet(os.path.join(a.work_out, 'scores_%s_%s.parquet' % (m, a.mode)))
        out['models'][m] = R
    # ---------------- joint cascade per domain
    J0 = spo.joint_frame(a.mode, a, topo)
    sig = J0.signal.to_numpy(); smp = J0['sample'].to_numpy()
    ncdr_sig = sig & (smp == spo.NCDR); bnb_bkg = (~sig) & (smp == spo.BNB)
    xnJ = uo.xn_split_v11(J0['sample'], J0['run'], J0['subrun'])
    bkg_classes = sorted(set(J0.bkg_class[bnb_bkg]))

    def summarize(p):
        r = dict(ncdr_signal_eff=float(p[ncdr_sig].mean()), ncdr_signal_pass=int(p[ncdr_sig].sum()), bnb_bkg_acc=float(p[bnb_bkg].mean()), bnb_bkg_pass=int(p[bnb_bkg].sum()),
                 ext_acc=float(p[smp == spo.EXT].mean()) if (smp == spo.EXT).any() else None,
                 nuecc_nueccbkg_acc=float(p[(smp == spo.NUECC) & (J0.bkg_class.to_numpy() == 'nueCCBkg')].mean()))
        for t, q in (('0p', J0.topology.to_numpy() == 0), ('1p', J0.topology.to_numpy() == 1), ('>=2p', J0.topology.to_numpy() >= 2)):
            q = q & ncdr_sig; r['ncdr_eff_' + t] = float(p[q].mean()) if q.any() else None
        for g in ('dev', 'train'):
            q = ncdr_sig & (xnJ == g); r['ncdr_eff_xn_' + g] = float(p[q].mean()) if q.any() else None
            q = bnb_bkg & (xnJ == g); r['bnb_acc_xn_' + g] = float(p[q].mean()) if q.any() else None
        for c in bkg_classes:
            q = bnb_bkg & (J0.bkg_class.to_numpy() == c); r['bnb_acc_' + c] = float(p[q].mean()) if q.any() else None
        return r

    def cascade(cuts, scores):
        p = np.ones(len(J0), bool); steps = []
        for m in ORDER:
            p = p & (scores[m] > cuts[m]); steps.append(dict(after=m, ncdr_signal_eff=float(p[ncdr_sig].mean()), bnb_bkg_acc=float(p[bnb_bkg].mean())))
        return p, steps

    joint, passes = {}, {}
    for d in ('A', 'B', 'C', 'D'):
        Jd = J0 if d == 'A' else uo.apply(J0, d, a.overlay_dir)
        leg, fix, ret, tRj = {}, {}, {}, {}
        for m in ORDER:
            clf = spo.CLF[m]; cols = features.load(clf).columns
            X64 = Jd[cols].to_numpy(np.float64); fin = np.isfinite(X64).all(1) & np.isfinite(X64.astype(np.float32)).all(1)
            X = np.nan_to_num(X64, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
            b0 = xgb.Booster(); b0.load_model(os.path.join(a.studies_dir, m, 'FIT_BASELINE_%s_%s.json' % (m, a.mode)))
            leg[m] = np.where(fin, dv.legacy_scores(a.bundle_root, clf, X, cols), -999.0)
            fix[m] = np.where(fin, dv.margin(xgb, b0, X, cols), -np.inf)
            ret[m] = np.where(fin, dv.margin(xgb, boosters[(m, model_domain(m, d))], X, cols), -np.inf)
            tRj[m] = out['models'][m]['domains'][model_domain(m, d)]['nval']['retrained_at_eps']['threshold']
        pL, sL = cascade(legacy_cut, leg); pF, sF = cascade(tA, fix); pR, sR = cascade(tRj, ret)
        passes[d] = dict(L=pL, F=pF, R=pR)
        thr = {m: {lev: (lc.threshold_for_rate(ret[m][sig], lev) if lev is not None else -np.inf) for lev in spo.LEVELS} for m in ORDER}
        rows = []
        for combo in itertools.product(spo.LEVELS, repeat=4):
            p, _ = cascade({m: thr[m][lev] for m, lev in zip(ORDER, combo)}, ret)
            rows.append(dict({'level_' + m: (lev if lev is not None else 'none') for m, lev in zip(ORDER, combo)}, ncdr_signal_eff=float(p[ncdr_sig].mean()), bnb_bkg_acc=float(p[bnb_bkg].mean())))
        G = pd.DataFrame(rows).sort_values(['bnb_bkg_acc', 'ncdr_signal_eff'], ascending=[True, False])
        best, front = -1.0, []
        for i, r in G.iterrows():
            if r.ncdr_signal_eff > best + 1e-12:
                front.append(i); best = r.ncdr_signal_eff
        G['pareto'] = G.index.isin(front)
        G.to_csv(os.path.join(a.work_out, 'joint_grid_%s_%s.csv' % (a.mode, d)), index=False, float_format='%.6g')
        joint[d] = dict(LEGACY_HISTORICAL=dict(cascade=sL, **summarize(pL)), DEV_FIXED=dict(thresholds=tA, cascade=sF, **summarize(pF)),
                        DEV_RETRAINED=dict(thresholds=tRj, cascade=sR, **summarize(pR)), pareto_points=int(G.pareto.sum()))
        print('joint', d, {k: (round(joint[d][k]['ncdr_signal_eff'], 4), round(joint[d][k]['bnb_bkg_acc'], 5)) for k in ('LEGACY_HISTORICAL', 'DEV_FIXED', 'DEV_RETRAINED')}, flush=True)
    for d in ('B', 'C', 'D'):
        joint[d]['paired_vs_A'] = {k: dict(ncdr_signal=flips(passes['A'][k][ncdr_sig], passes[d][k][ncdr_sig]), bnb_background=flips(passes['A'][k][bnb_bkg], passes[d][k][bnb_bkg]))
                                   for k in ('L', 'F', 'R')}
    rA = ref['joint']
    joint['reference_check'] = dict(
        legacy_ncdr=dict(reference=rA['LEGACY_HISTORICAL']['ncdr_signal_eff'], reproduced=joint['A']['LEGACY_HISTORICAL']['ncdr_signal_eff']),
        legacy_bnb=dict(reference=rA['LEGACY_HISTORICAL']['bnb_bkg_acc'], reproduced=joint['A']['LEGACY_HISTORICAL']['bnb_bkg_acc']),
        dev_ncdr=dict(reference=rA['DEV_ROC_EQUIVALENT']['ncdr_signal_eff'], reproduced=joint['A']['DEV_RETRAINED']['ncdr_signal_eff']),
        dev_bnb=dict(reference=rA['DEV_ROC_EQUIVALENT']['bnb_bkg_acc'], reproduced=joint['A']['DEV_RETRAINED']['bnb_bkg_acc']))
    joint['reference_check']['verdict'] = 'REPRODUCED' if all(abs(v['reference'] - v['reproduced']) < 1e-12 for v in joint['reference_check'].values()) else 'NOT_REPRODUCED'
    joint['rows'] = dict(ncdr_signal=int(ncdr_sig.sum()), bnb_background=int(bnb_bkg.sum()), ext=int((smp == spo.EXT).sum()))
    out['joint'] = joint
    json.dump(out, open(a.out_json, 'w'), indent=1, default=lambda o: o.item() if isinstance(o, (np.floating, np.integer)) else str(o))
    print('reference_check', json.dumps(joint['reference_check']))


if __name__ == '__main__':
    main()
