#!/usr/bin/env python3
"""Statistical comparison of the joint four-cut SP selection across upstream domains A/B/C/D, from the ALREADY TRAINED
development models of tools/upstream_domain_study.py (no training, no tuning, no threshold chosen). DEVELOPMENT ONLY.

Rows: every preselected row of the four training-side samples (spo.joint_frame) in NESTED VALIDATION (where all choices of
the development study were made) and in the existing DEVELOPMENT HOLDOUT (odd subruns / beam-off run % 4 == 1; reported
separately; never used for a choice). Scores per domain and model: the inherited XML (legacy), the domain-A development model
(fixed), the model retrained in the domain (RETRAINED_* boosters saved by the domain study). Domain A must reproduce the
domain-study numbers bit for bit (checked against its JSON).

Three comparisons, kept apart because they answer different questions:
  P1 presentation       A: inherited XMLs at the historical cuts vs development models at point A      (27.1 % vs 44.0 %)
  P2 matched per-model  A vs D, each SP model retrained in its domain at the domain-A per-model signal efficiency (44.0 vs 42.1 %)
  P3 optimized front    A vs D, best NC Delta efficiency of the 9^4 grid at BNB acceptance <= 0.78 %, <= 0.778 % (the audit table's
                        cap: 48.0 vs 48.7 %) and <= 0.70 %
P1 and P2 thresholds are set on NESTED VALIDATION per model (matched signal efficiency: no joint optimization). P3 points are
the maximum over 6,561 vectors on the same NESTED VALIDATION rows: OPTIMIZATION DIAGNOSTICS, not unbiased performance. The
holdout numbers at the same thresholds are free of that selection (but the holdout is NOT upstream-independent: Xuyang's models
were fitted on most of those rows).

Statistics: paired pass/fail tables, exact McNemar tests on discordant rows, (sample, run, subrun)-clustered Poisson bootstrap
intervals of paired differences (the nested_v1 / split unit), a selection-aware bootstrap of the P3 front (the grid maximum is
re-taken in every replicate; out-of-bag optimism), Clopper-Pearson intervals for small counts.

  python tools/upstream_joint_comparison.py --mode M --tables T --tag dev --bundle-root LEGACY --studies-dir S --overlay-dir O \
      --topology-dir TOPO --domain-json validation/upstream_r4/upstream_domain_study_M.json --retrained-dir $U/domain/M \
      [--membership $U/membership/membership_M.parquet] --out-json OUT --work-out WORK [--bootstrap 2000]
"""
import argparse, itertools, json, os, sys, time

import numpy as np
import pandas as pd

ROUND2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROUND2); sys.path.insert(0, os.path.join(ROUND2, 'tools'))
from sp_retrain import devstudy as dv, devtrain, features, firewall, legacy_control as lc, upstream_overlay as uo  # noqa: E402
import sp_operating_points as spo  # noqa: E402

ORDER = spo.ORDER
CAPS = (0.0078, 0.00778, 0.0070)   # 0.778 %: the cap the 2026-11-28 audit table used (just below domain A's own 50/6424 = 0.7783 %)
DOMAINS = ('A', 'B', 'C', 'D')
ALLOWED_OUTPUT = ['/lus/flare/projects/neutrinoGPU/abhat/sbnd']
LABEL = 'UPSTREAM-DOMAIN JOINT-SELECTION COMPARISON (WCL1116) -- DEVELOPMENT ONLY, NOTHING CHOSEN OR FROZEN, NOT ROUND2'


def model_domain(m, d):
    if m in ('numu', 'other'):
        return 'B' if d in ('B', 'D') else 'A'
    if m == 'ncpi0':
        return 'C' if d in ('C', 'D') else 'A'
    return 'A'


def cp(k, n, cl=0.6827):
    from scipy.stats import beta
    if n == 0:
        return [None, None]
    a = (1 - cl) / 2
    lo = 0.0 if k == 0 else float(beta.ppf(a, k, n - k + 1))
    hi = 1.0 if k == n else float(beta.ppf(1 - a, k + 1, n - k))
    return [lo, hi]


def rate(p, q):
    n = int(q.sum()); k = int(p[q].sum())
    return dict(n=n, k=k, rate=(k / n if n else None), cp68=cp(k, n), cp95=cp(k, n, 0.95))


class Boot:
    """(sample, run, subrun)-clustered Poisson bootstrap weights, fixed seed."""

    def __init__(self, J, B, seed=20261128):
        u = J['sample'].astype(str) + '|' + J['run'].astype(str) + '|' + J['subrun'].astype(str)
        codes, uniq = pd.factorize(u)
        self.codes = codes; self.B = B
        rng = np.random.default_rng(seed)
        self.W = rng.poisson(1.0, size=(len(uniq), B)).astype(np.float32)     # cluster x replicate

    def rows(self, q):
        return self.W[self.codes[q]]                                           # rows(q) x B


def paired(pa, pb, q, boot):
    """A vs B on the same rows q: table, McNemar exact p, clustered bootstrap of rate(B) - rate(A)."""
    from scipy.stats import binomtest
    a, b = pa[q], pb[q]
    n = int(q.sum()); both = int((a & b).sum()); oa = int((a & ~b).sum()); ob = int((~a & b).sum())
    out = dict(n=n, pass_A=int(a.sum()), pass_B=int(b.sum()), both=both, only_A=oa, only_B=ob, neither=n - both - oa - ob,
               rate_A=(a.mean() if n else None), rate_B=(b.mean() if n else None), diff=(b.mean() - a.mean() if n else None))
    out['mcnemar_exact_p'] = float(binomtest(min(oa, ob), oa + ob, 0.5).pvalue) if oa + ob else 1.0
    if n and boot is not None:
        W = boot.rows(q); s = W.sum(0)
        d = (W * b[:, None]).sum(0) / s - (W * a[:, None]).sum(0) / s
        out['boot_diff_ci68'] = np.quantile(d, [0.1587, 0.8413]).tolist(); out['boot_diff_ci95'] = np.quantile(d, [0.025, 0.975]).tolist()
        out['boot_diff_sd'] = float(d.std())
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    for k in ('--mode', '--tables', '--tag', '--bundle-root', '--studies-dir', '--overlay-dir', '--topology-dir', '--domain-json', '--retrained-dir', '--out-json', '--work-out'):
        ap.add_argument(k, required=True)
    ap.add_argument('--membership'); ap.add_argument('--bootstrap', type=int, default=2000)
    a = ap.parse_args()
    import xgboost as xgb
    t0 = time.time()
    firewall.check_output_path(a.work_out, ALLOWED_OUTPUT); os.makedirs(a.work_out, exist_ok=True)
    ref = json.load(open(a.domain_json))
    topo = spo.load_topology(a.topology_dir)
    J0 = spo.joint_frame(a.mode, a, topo, roles=(dv.ROLE_NVAL, dv.ROLE_TEST)).reset_index(drop=True)
    sig = J0.signal.to_numpy(); smp = J0['sample'].to_numpy(); role = J0.role.to_numpy()
    nv, te = role == dv.ROLE_NVAL, role == dv.ROLE_TEST
    ncdr_sig = sig & (smp == spo.NCDR); bnb_bkg = (~sig) & (smp == spo.BNB)
    ext = smp == spo.EXT; nue_bkg = (smp == spo.NUECC) & (J0.bkg_class.to_numpy() == 'nueCCBkg')
    topo_t = J0.topology.to_numpy(); bkgc = J0.bkg_class.to_numpy()
    xn = uo.xn_split_v11(J0['sample'], J0['run'], J0['subrun'])
    mem = None
    if a.membership:
        M = pd.read_parquet(a.membership, columns=devtrain.ROW_KEY + ['up_numu_role', 'up_nue_role'])
        k = J0[devtrain.ROW_KEY].copy()
        for c in ('run', 'subrun', 'event', 'cand'):
            k[c] = k[c].astype(np.int64); M[c] = M[c].astype(np.int64)
        mem = k.merge(M, on=devtrain.ROW_KEY, how='left', validate='one_to_one')
        if mem.up_numu_role.isna().any():
            raise SystemExit('%d joint rows without a membership row' % int(mem.up_numu_role.isna().sum()))
    # ---------------- scores per domain (already trained models only)
    tA = {m: ref['models'][m]['point_A_threshold'] for m in ORDER}
    tR = {d: {m: ref['models'][m]['domains'][model_domain(m, d)]['nval']['retrained_at_eps']['threshold'] for m in ORDER} for d in DOMAINS}
    S = {}
    rows_out = J0[devtrain.ROW_KEY + ['role', 'signal', 'bkg_class', 'topology']].copy(); rows_out['xn_split_v11'] = xn
    for d in DOMAINS:
        Jd = J0 if d == 'A' else uo.apply(J0, d, a.overlay_dir)
        S[d] = dict(L={}, F={}, R={})
        for m in ORDER:
            clf = spo.CLF[m]; cols = features.load(clf).columns
            X64 = Jd[cols].to_numpy(np.float64); fin = np.isfinite(X64).all(1) & np.isfinite(X64.astype(np.float32)).all(1)
            X = np.nan_to_num(X64, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
            b0 = xgb.Booster(); b0.load_model(os.path.join(a.studies_dir, m, 'FIT_BASELINE_%s_%s.json' % (m, a.mode)))
            br = xgb.Booster(); br.load_model(os.path.join(a.retrained_dir, 'RETRAINED_%s_%s_%s.json' % (m, a.mode, model_domain(m, d))))
            S[d]['L'][m] = np.where(fin, dv.legacy_scores(a.bundle_root, clf, X, cols), -999.0)
            S[d]['F'][m] = np.where(fin, dv.margin(xgb, b0, X, cols), -np.inf)
            S[d]['R'][m] = np.where(fin, dv.margin(xgb, br, X, cols), -np.inf)
            for kind in 'LFR':
                rows_out['%s_%s_%s' % (kind, m, d)] = S[d][kind][m].astype(np.float32)
    rows_out.to_parquet(os.path.join(a.work_out, 'joint_rows_scores_%s.parquet' % a.mode))

    def cascade(cuts, sc):
        p = np.ones(len(J0), bool)
        for m in ORDER:
            p &= sc[m] > cuts[m]
        return p
    P = {}
    for d in DOMAINS:
        P[(d, 'L')] = cascade({m: lc.LEGACY_CUT[spo.CLF[m]] for m in ORDER}, S[d]['L'])
        P[(d, 'F')] = cascade(tA, S[d]['F'])
        P[(d, 'R')] = cascade(tR[d], S[d]['R'])
    # ---------------- reproduction of the domain study (NESTED VALIDATION)
    repro = {}
    for d in DOMAINS:
        for kind, name in (('L', 'LEGACY_HISTORICAL'), ('F', 'DEV_FIXED'), ('R', 'DEV_RETRAINED')):
            r = ref['joint'][d][name]
            got = (float(P[(d, kind)][nv & ncdr_sig].mean()), float(P[(d, kind)][nv & bnb_bkg].mean()))
            repro['%s_%s' % (d, name)] = dict(reference=(r['ncdr_signal_eff'], r['bnb_bkg_acc']), reproduced=got,
                                              exact=abs(got[0] - r['ncdr_signal_eff']) < 1e-12 and abs(got[1] - r['bnb_bkg_acc']) < 1e-12)
    if not all(v['exact'] for v in repro.values()):
        raise SystemExit('domain-study numbers NOT reproduced: %s' % json.dumps({k: v for k, v in repro.items() if not v['exact']}))
    print('reproduced', len(repro), 'reference points', flush=True)
    # ---------------- 9^4 grid per domain (thresholds from NESTED-VALIDATION signal rows, as the domain study)
    combos = list(itertools.product(range(len(spo.LEVELS)), repeat=4))
    C = np.array(combos, np.int8)
    grid, passbits = {}, {}
    for d in DOMAINS:
        thr = {m: [lc.threshold_for_rate(S[d]['R'][m][sig & nv], lev) if lev is not None else -np.inf for lev in spo.LEVELS] for m in ORDER}
        lv = {m: np.stack([S[d]['R'][m] > t for t in thr[m]]) for m in ORDER}          # level x rows
        cols = dict(nv_sig=nv & ncdr_sig, nv_bkg=nv & bnb_bkg, te_sig=te & ncdr_sig, te_bkg=te & bnb_bkg, nv_ext=nv & ext, te_ext=te & ext,
                    nv_nue=nv & nue_bkg, te_nue=te & nue_bkg)
        cnt = {k: np.zeros(len(combos), np.int32) for k in cols}
        for i, cb in enumerate(combos):
            p = lv['numu'][cb[0]] & lv['other'][cb[1]] & lv['ncpi0'][cb[2]] & lv['nue'][cb[3]]
            for k, q in cols.items():
                cnt[k][i] = int(p[q].sum())
        G = pd.DataFrame({'level_' + m: [spo.LEVELS[c[j]] if spo.LEVELS[c[j]] is not None else 'none' for c in combos] for j, m in enumerate(ORDER)})
        for k, v in cnt.items():
            G[k] = v
        G['nv_eff'] = G.nv_sig / int(cols['nv_sig'].sum()); G['nv_acc'] = G.nv_bkg / int(cols['nv_bkg'].sum())
        G['te_eff'] = G.te_sig / int(cols['te_sig'].sum()); G['te_acc'] = G.te_bkg / int(cols['te_bkg'].sum())
        o = G.sort_values(['nv_acc', 'nv_eff'], ascending=[True, False]); best, front = -1.0, []
        for i, r in o.iterrows():
            if r.nv_eff > best + 1e-12:
                front.append(i); best = r.nv_eff
        G['pareto_nval'] = G.index.isin(front)
        grid[d] = dict(G=G, thr=thr, lv=lv)
        G.to_csv(os.path.join(a.work_out, 'joint_grid_full_%s_%s.csv' % (a.mode, d)), index=False, float_format='%.6g')
    # operating points: max NESTED-VALIDATION efficiency at acceptance <= cap (ties: lower acceptance, then grid order)
    op = {}
    for d in DOMAINS:
        G = grid[d]['G']
        for cap in CAPS:
            c = G[G.nv_acc <= cap + 1e-12].sort_values(['nv_eff', 'nv_acc'], ascending=[False, True], kind='mergesort')
            i = int(c.index[0]); cb = combos[i]
            p = (grid[d]['lv']['numu'][cb[0]] & grid[d]['lv']['other'][cb[1]] & grid[d]['lv']['ncpi0'][cb[2]] & grid[d]['lv']['nue'][cb[3]])
            P[(d, 'front%.5f' % cap)] = p
            op[(d, cap)] = dict(grid_index=i, levels={m: spo.LEVELS[cb[j]] for j, m in enumerate(ORDER)},
                                thresholds={m: float(grid[d]['thr'][m][cb[j]]) for j, m in enumerate(ORDER)})
            # symmetric diagnostic: the same maximum taken on the HOLDOUT itself (5x the rows; still an optimization)
            h = G[G.te_acc <= cap + 1e-12].sort_values(['te_eff', 'te_acc'], ascending=[False, True], kind='mergesort')
            hi = int(h.index[0]); hb = combos[hi]
            op[(d, cap)]['holdout_optimized_front'] = dict(
                levels={m: spo.LEVELS[hb[j]] for j, m in enumerate(ORDER)}, signal_pass=int(G.te_sig[hi]), signal_rows=int(cols['te_sig'].sum()),
                eff=float(G.te_eff[hi]), background_pass=int(G.te_bkg[hi]), background_rows=int(cols['te_bkg'].sum()), acc=float(G.te_acc[hi]),
                note='maximum over the grid on the HOLDOUT (same thresholds per level, set on NESTED VALIDATION): an optimization diagnostic, symmetric across domains')

    # ---------------- summaries
    def summary(p):
        out = {}
        for rn, rq in (('nval', nv), ('holdout', te)):
            r = dict(ncdr_signal=rate(p, rq & ncdr_sig), bnb_background=rate(p, rq & bnb_bkg), ext=rate(p, rq & ext), nuecc_nueCCBkg=rate(p, rq & nue_bkg))
            r['topology'] = {t: rate(p, rq & ncdr_sig & q) for t, q in (('0p', topo_t == 0), ('1p', topo_t == 1), ('>=2p', topo_t >= 2), ('unmatched', topo_t < 0))}
            sel = p & rq & bnb_bkg
            r['background_composition'] = {c: dict(selected=int((sel & (bkgc == c)).sum()), rows=int((rq & bnb_bkg & (bkgc == c)).sum()))
                                           for c in sorted(set(bkgc[rq & bnb_bkg]))}
            r['by_xn_split_v11'] = {g: dict(ncdr_signal=rate(p, rq & ncdr_sig & (xn == g)), bnb_background=rate(p, rq & bnb_bkg & (xn == g))) for g in ('dev', 'train')}
            if mem is not None:
                for col in ('up_numu_role', 'up_nue_role'):
                    v = mem[col].to_numpy().astype(str)
                    r['by_' + col] = {g: dict(ncdr_signal=rate(p, rq & ncdr_sig & (v == g)), bnb_background=rate(p, rq & bnb_bkg & (v == g)))
                                      for g in sorted(set(v[rq & (ncdr_sig | bnb_bkg)]))}
            out[rn] = r
        return out
    boot = Boot(J0, a.bootstrap)

    def compare(ka, kb):
        pa, pb = P[ka], P[kb]
        out = {}
        for rn, rq in (('nval', nv), ('holdout', te)):
            out[rn] = dict(ncdr_signal=paired(pa, pb, rq & ncdr_sig, boot), bnb_background=paired(pa, pb, rq & bnb_bkg, boot),
                           ext=paired(pa, pb, rq & ext, None), nuecc_nueCCBkg=paired(pa, pb, rq & nue_bkg, None))
            out[rn]['signal_migration_by_topology'] = {t: dict(gained=int((~pa & pb & rq & ncdr_sig & q).sum()), lost=int((pa & ~pb & rq & ncdr_sig & q).sum()))
                                                       for t, q in (('0p', topo_t == 0), ('1p', topo_t == 1), ('>=2p', topo_t >= 2), ('unmatched', topo_t < 0))}
            out[rn]['background_migration_by_class'] = {c: dict(gained=int((~pa & pb & rq & bnb_bkg & (bkgc == c)).sum()), lost=int((pa & ~pb & rq & bnb_bkg & (bkgc == c)).sum()))
                                                        for c in sorted(set(bkgc[rq & bnb_bkg]))}
            out[rn]['by_xn_split_v11'] = {g: dict(ncdr_signal=paired(pa, pb, rq & ncdr_sig & (xn == g), boot),
                                                  bnb_background=paired(pa, pb, rq & bnb_bkg & (xn == g), boot)) for g in ('dev', 'train')}
        return out

    points = {'%s_%s' % (d, n): summary(P[(d, k)]) for d in DOMAINS for k, n in (('L', 'LEGACY_HISTORICAL'), ('F', 'DEV_FIXED'), ('R', 'DEV_RETRAINED_MATCHED'))}
    for d in DOMAINS:
        for cap in CAPS:
            points['%s_FRONT_%.3fpct' % (d, cap * 100)] = dict(summary(P[(d, 'front%.5f' % cap)]), **op[(d, cap)])
    comparisons = dict(
        P1_presentation_A_legacy_vs_A_dev=dict(selection='per-model thresholds at legacy-equal signal efficiency on NESTED VALIDATION (no joint optimization)',
                                               **compare(('A', 'L'), ('A', 'R'))),
        P2_matched_per_model_A_vs_D=dict(selection='per-model thresholds at the domain-A per-model signal efficiencies on NESTED VALIDATION (no joint optimization)',
                                         **compare(('A', 'R'), ('D', 'R'))),
        P2_matched_per_model_A_vs_B=dict(selection='as P2', **compare(('A', 'R'), ('B', 'R'))),
        P2_matched_per_model_A_vs_C=dict(selection='as P2', **compare(('A', 'R'), ('C', 'R'))))
    for cap in CAPS:
        for d in ('B', 'C', 'D'):
            comparisons['P3_optimized_front_%.3fpct_A_vs_%s' % (cap * 100, d)] = dict(
                selection=('maximum over 6,561 threshold vectors on NESTED VALIDATION, separately per domain: OPTIMIZATION DIAGNOSTIC (nval); '
                           'the holdout block evaluates the same vectors on rows that took no part in the choice'),
                **compare(('A', 'front%.5f' % cap), (d, 'front%.5f' % cap)))
    # ---------------- selection-aware bootstrap of the front maximum (NESTED VALIDATION)
    sa = {}
    qs, qb = nv & ncdr_sig, nv & bnb_bkg
    Ws, Wb = boot.rows(qs), boot.rows(qb)
    for d in DOMAINS:
        lv = grid[d]['lv']
        Ps = np.zeros((len(combos), int(qs.sum())), np.float32); Pb = np.zeros((len(combos), int(qb.sum())), np.float32)
        for i, cb in enumerate(combos):
            p = lv['numu'][cb[0]] & lv['other'][cb[1]] & lv['ncpi0'][cb[2]] & lv['nue'][cb[3]]
            Ps[i] = p[qs]; Pb[i] = p[qb]
        eff = (Ps @ Ws) / Ws.sum(0); acc = (Pb @ Wb) / Wb.sum(0)                         # combos x B
        Wso, Wbo = (Ws == 0).astype(np.float32), (Wb == 0).astype(np.float32)          # out-of-bag clusters
        effo = (Ps @ Wso) / np.maximum(Wso.sum(0), 1)
        sa[d] = {}
        for cap in CAPS:
            ok = acc <= cap + 1e-12
            e = np.where(ok, eff, -1.0); j = e.argmax(0); best = e[j, np.arange(a.bootstrap)]
            sa[d][cap] = dict(best=best, oob=effo[j, np.arange(a.bootstrap)])
    selboot = {}
    for cap in CAPS:
        blk = {}
        for d in DOMAINS:
            b, o = sa[d][cap]['best'], sa[d][cap]['oob']
            blk[d] = dict(front_max_mean=float(b.mean()), front_max_ci68=np.quantile(b, [0.1587, 0.8413]).tolist(),
                          out_of_bag_eff_of_selected_mean=float(o.mean()), optimism_mean=float((b - o).mean()))
        for d in ('B', 'C', 'D'):
            dd = sa[d][cap]['best'] - sa['A'][cap]['best']
            blk['diff_%s_minus_A' % d] = dict(mean=float(dd.mean()), ci68=np.quantile(dd, [0.1587, 0.8413]).tolist(),
                                              ci95=np.quantile(dd, [0.025, 0.975]).tolist(), fraction_le_0=float((dd <= 0).mean()))
        selboot['cap_%.3fpct' % (cap * 100)] = blk
    out = dict(label=LABEL, mode=a.mode, bootstrap=dict(replicates=a.bootstrap, cluster='(sample, run, subrun)', seed=20261128, kind='Poisson'),
               rows=dict(nval=dict(ncdr_signal=int((nv & ncdr_sig).sum()), bnb_background=int((nv & bnb_bkg).sum()), ext=int((nv & ext).sum()), nuecc_nueCCBkg=int((nv & nue_bkg).sum())),
                         holdout=dict(ncdr_signal=int((te & ncdr_sig).sum()), bnb_background=int((te & bnb_bkg).sum()), ext=int((te & ext).sum()), nuecc_nueCCBkg=int((te & nue_bkg).sum())),
                         clusters=int(boot.W.shape[0])),
               reproduction_of_domain_study=repro, caps=list(CAPS), levels=[l if l is not None else 'none' for l in spo.LEVELS],
               points=points, comparisons=comparisons, selection_aware_bootstrap_front=selboot,
               pareto_fronts={d: grid[d]['G'][grid[d]['G'].pareto_nval].sort_values('nv_acc')[
                   ['level_' + m for m in ORDER] + ['nv_sig', 'nv_bkg', 'nv_eff', 'nv_acc', 'te_sig', 'te_bkg', 'te_eff', 'te_acc']].to_dict('records') for d in DOMAINS},
               membership=a.membership, wall_s=round(time.time() - t0, 1))
    json.dump(out, open(a.out_json, 'w'), indent=1, default=lambda o: o.item() if isinstance(o, (np.floating, np.integer, np.bool_)) else (None if o is None else str(o)))
    print(json.dumps({k: (v['nval']['ncdr_signal']['rate'], v['nval']['bnb_background']['rate']) for k, v in points.items()}), flush=True)


if __name__ == '__main__':
    main()
