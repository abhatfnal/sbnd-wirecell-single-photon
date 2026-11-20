"""WCL1116 FULL-DEVELOPMENT study library (campaign development_wcl1116_v1; branch
round2/sp-bdt-wcl1116-full-development-20261120). Every rule here was fixed BEFORE any variant was fitted
(docs/SP_BDT_WCL1116_FULL_DEVELOPMENT_PLAN.md).

Roles of a classed row:
  EXISTING DEVELOPMENT HOLDOUT ('test')  the outer split, unchanged: MC odd subrun; EXT run % 4 == 1
  FIT ('fit') / NESTED VALIDATION ('nval') a deterministic split of the existing TRAINING side only (nested_v1 below)
None of these is an independent evaluation (AURORA_UMBRELLA_MODEL_TRAINING_AND_EVALUATION_POLICY.md).

nested_v1: unit = (sample, run, subrun), the unit of the outer split (all candidates of an event, all events of a
subrun, stay together; EXT files carry art subrun 1, so an EXT unit is a run). u = first 8 hex digits of
sha256("nested_v1|<sample>|<run>|<subrun>") / 2**32; NESTED VALIDATION if u < 0.20, else FIT. It depends only on the
unit, so it is identical in split-move and snap and cannot depend on any score; it touches no outer-holdout row.
"""
import hashlib
import json
import os

import numpy as np
import pandas as pd

from . import devtrain, features, labels, legacy_control as lc

NESTED_RULE = 'nested_v1'
NESTED_VALIDATION_FRACTION = 0.20
ROLE_FIT, ROLE_NVAL, ROLE_TEST = 'fit', 'nval', 'test'
UNIT = ['sample', 'run', 'subrun']

# ------------------------------------------------------------------ nested split
def nested_u(sample, run, subrun):
    h = hashlib.sha256(('%s|%s|%d|%d' % (NESTED_RULE, sample, int(run), int(subrun))).encode()).hexdigest()
    return int(h[:8], 16) / 2.0 ** 32


def nested_roles(keys):
    """'fit' / 'nval' for rows of the existing training side, 'test' for the existing holdout (keys.split from
    devtrain.build_dataset). Vectorised over the distinct units."""
    k = keys[UNIT].astype({'run': np.int64, 'subrun': np.int64})
    u = k.drop_duplicates().copy()
    u['u'] = [nested_u(s, r, sr) for s, r, sr in zip(u['sample'].astype(str), u.run, u.subrun)]
    uu = k.merge(u, on=UNIT, how='left')['u'].to_numpy()
    out = np.where(uu < NESTED_VALIDATION_FRACTION, ROLE_NVAL, ROLE_FIT).astype(object)
    return np.where(keys.split.to_numpy() == 'test', ROLE_TEST, out).astype(object)


def nested_unit_table(keys, roles):
    t = keys[UNIT].assign(role=roles).drop_duplicates().sort_values(UNIT).reset_index(drop=True)
    if t.duplicated(UNIT).any():
        raise ValueError('a unit carries two roles')
    return t


# ------------------------------------------------------------------ weighting (SP nue study)
WEIGHTINGS = {
    'UNWEIGHTED_BASELINE': None,          # every row weight 1 (the WCL1116 development convention)
    'THESIS_PRIOR_APPROX': 4.0,           # total negative weight : total positive weight = 4 : 1 (thesis 100,958 : 24,936 = 4.05)
    'BALANCED_STRESS_TEST': 1.0,          # equal total positive and negative weight
}


def class_weights(y, neg_to_pos):
    """Per-row weights with sum(w | neg) / sum(w | pos) = neg_to_pos and mean weight 1 (sum = N), so XGBoost's
    absolute regularisation scale (min_child_weight, gamma) is that of the unweighted fit. None -> all ones."""
    y = np.asarray(y)
    if neg_to_pos is None:
        return np.ones(len(y))
    npos, nneg, n = (y == 1).sum(), (y == 0).sum(), len(y)
    wpos = n / (npos * (1.0 + neg_to_pos)); wneg = n * neg_to_pos / (nneg * (1.0 + neg_to_pos))
    return np.where(y == 1, wpos, wneg)


# ------------------------------------------------------------------ audited feature families
def feature_meta(model):
    d = json.load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'features',
                                    'single_photon_%s_inputs_v0.json' % model)))
    return d['inputs']


def upstream_family(model, families=None):
    """Inputs the audited feature list marks kind == 'upstream_score' (optionally restricted to upstream.family values)."""
    out = []
    for f in feature_meta(model):
        if f['kind'] == 'upstream_score' and (families is None or (f.get('upstream') or {}).get('family') in families):
            out.append(f['table_column'] or f['name'])
    return out


def cosmic_tagger_direct(model):
    """Reco inputs written by PatternAlgorithms::cosmic_tagger(): every cosmict_* / cosmic_* field
    (SP_BDT_WCL1116_DEVELOPMENT_RESULTS.md sec. 11, toolkit source audit); upstream classifier outputs excluded."""
    return [(f['table_column'] or f['name']) for f in feature_meta(model)
            if f['kind'] == 'reco' and f['name'].startswith(('cosmict_', 'cosmic_'))]


def ablations(model):
    """Predefined DIAGNOSTIC ablations (never candidate models)."""
    if model == 'numu':
        return {'A_FULL': [], 'B_NO_FINAL_NUMU_SCORE': ['numu_score'],
                'C_NO_UPSTREAM_NUMU_FAMILY': upstream_family('numu')}
    if model == 'other':
        cos, up = cosmic_tagger_direct('other'), upstream_family('other')
        return {'A_FULL': [], 'B_NO_COSMIC_TAGGER_DIRECT': cos, 'C_NO_UPSTREAM_NUMU_FAMILY': up, 'D_NO_COSMIC_NO_UPSTREAM': cos + up}
    raise ValueError(model)


BOOKKEEPING = {'run', 'subrun', 'event', 'cand', 'file_id', 'sample', 'cluster_id', 'nu_index', 'eventNo', 'runNo', 'subRunNo', 'split', 'role'}


# ------------------------------------------------------------------ fitting
def fit(xgb, params, rounds, X, y, names, w=None):
    d = xgb.DMatrix(X, label=y, weight=w, feature_names=list(names))
    return xgb.train(params, d, num_boost_round=rounds, verbose_eval=False)


def margin(xgb, bst, X, names):
    return bst.predict(xgb.DMatrix(X, feature_names=list(names)), output_margin=True)


def importance(bst, names):
    w = bst.get_score(importance_type='weight'); g = bst.get_score(importance_type='total_gain')
    t = pd.DataFrame(dict(feature=list(names), splits=[float(w.get(n, 0.0)) for n in names], total_gain=[float(g.get(n, 0.0)) for n in names]))
    t['gain_share'] = t.total_gain / max(t.total_gain.sum(), 1e-30)
    t['rank_splits'] = t.splits.rank(ascending=False, method='first').astype(int)
    t['rank_gain'] = t.total_gain.rank(ascending=False, method='first').astype(int)
    return t


# ------------------------------------------------------------------ metrics
def roc_pr(y, s):
    from sklearn.metrics import average_precision_score, roc_auc_score
    return dict(roc_auc=float(roc_auc_score(y, s)), pr_auc=float(average_precision_score(y, s)))


def op_points(y, s, legacy_s, legacy_cut):
    """Legacy at its historical cut; the new score at equal signal efficiency (A) and equal background acceptance (B).
    DEVELOPMENT ROC-EQUIVALENT DIAGNOSTIC -- NOT ROUND2 CUT."""
    y = np.asarray(y); s = np.asarray(s, np.float64)
    leg = lc.operating_point(y, legacy_s, legacy_cut)
    tA = lc.threshold_for_rate(s[y == 1], leg['signal_efficiency']); A = lc.operating_point(y, s, tA)
    tB = lc.threshold_for_rate(s[y == 0], leg['background_acceptance']); B = lc.operating_point(y, s, tB)
    return dict(legacy=leg, A_equal_signal_efficiency=A, B_equal_background_acceptance=B)


def component_acceptance(comp, passed, components):
    comp = np.asarray(comp); passed = np.asarray(passed, bool)
    return {c: (dict(rows=int((comp == c).sum()), acceptance=float(passed[comp == c].mean())) if (comp == c).any() else dict(rows=0, acceptance=None))
            for c in components}


def threshold_table(y, s, comp=None, components=(), effs=None):
    """Monotonic threshold table: thresholds at a fixed grid of signal efficiencies (descending threshold)."""
    y = np.asarray(y); s = np.asarray(s, np.float64)
    effs = effs if effs is not None else [0.99, 0.98, 0.95, 0.90, 0.85, 0.80, 0.75, 0.70, 0.60, 0.50, 0.40, 0.30, 0.20, 0.10]
    rows = []
    for e in effs:
        t = lc.threshold_for_rate(s[y == 1], e); p = s > t
        r = dict(target_signal_efficiency=e, threshold=float(t), signal_efficiency=float(p[y == 1].mean()), background_acceptance=float(p[y == 0].mean()))
        if comp is not None:
            for c in components:
                q = np.asarray(comp) == c
                r['acc_' + c] = float(p[q].mean()) if q.any() else float('nan')
        rows.append(r)
    t = pd.DataFrame(rows).sort_values('threshold', ascending=False).reset_index(drop=True)
    return t


def is_monotonic(t):
    """Signal efficiency and background acceptance never decrease as the threshold decreases."""
    t = t.sort_values('threshold', ascending=False)
    return bool((np.diff(t.signal_efficiency.to_numpy()) >= -1e-12).all() and (np.diff(t.background_acceptance.to_numpy()) >= -1e-12).all())


def calibration(y, s, nbins=10):
    """Reliability of sigmoid(margin) on these rows (natural prevalence), Brier score, per-class margin quantiles."""
    y = np.asarray(y); p = 1.0 / (1.0 + np.exp(-np.asarray(s, np.float64)))
    edges = np.linspace(0, 1, nbins + 1); b = np.clip(np.digitize(p, edges) - 1, 0, nbins - 1)
    rel = [dict(bin=int(i), mean_pred=float(p[b == i].mean()), frac_pos=float(y[b == i].mean()), n=int((b == i).sum()))
           for i in range(nbins) if (b == i).any()]
    q = lambda v: [float(x) for x in np.quantile(v, [0.1, 0.5, 0.9])] if len(v) else None
    return dict(brier=float(((p - y) ** 2).mean()), mean_pred_pos=float(p[y == 1].mean()), mean_pred_neg=float(p[y == 0].mean()),
                margin_q10_50_90_pos=q(np.asarray(s)[y == 1]), margin_q10_50_90_neg=q(np.asarray(s)[y == 0]), reliability=rel)


# ------------------------------------------------------------------ data
def load_dataset(spec, tables, tag):
    """(C, ds, roles) for a WCL1116 development spec: rows exactly as in training (stamp filter, preselection,
    classes, non-finite exclusion), plus the nested roles."""
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools'))
    from legacy_control_compare import load_cands
    C = load_cands(tables, tag, spec, [])
    ds = devtrain.build_dataset(C, spec)
    return C, ds, nested_roles(ds['keys'])


def legacy_scores(bundle_root, clf, X, cols):
    forest = lc.load_control(bundle_root, clf, features.load(clf).names)
    return lc.legacy_score(forest, lc.legacy_matrix(X, cols, clf))[1]


def row_truth(C, keys, cols=('m_sp_bkg', 'partner_kind', 'm_vx', 'm_vy', 'm_vz', 'm_pdg', 'm_E', 'm_sp_category', 'm_nu_idx')):
    return keys[devtrain.ROW_KEY].merge(C[devtrain.ROW_KEY + [c for c in cols if c in C.columns]].drop_duplicates(devtrain.ROW_KEY),
                                        on=devtrain.ROW_KEY, how='left')


def attach_topology(R, topo, tol_e=1e-4, tol_v=0.05):
    """Truth topology of each row's T_match partner neutrino: match the partner (m_pdg, m_E, m_v*) to one rec.mc.nu of
    the same event (same pdg, |dE| < tol_e GeV, |dv| < tol_v cm on every axis). Unmatched rows get topology -1."""
    m = R.reset_index().merge(topo, on=devtrain.EV, how='left', suffixes=('', '_t'))
    ok = ((m.pdg == m.m_pdg) & ((m.E - m.m_E).abs() < tol_e) & ((m.vx - m.m_vx).abs() < tol_v) &
          ((m.vy - m.m_vy).abs() < tol_v) & ((m.vz - m.m_vz).abs() < tol_v))
    m = m[ok].drop_duplicates('index')
    out = R.copy()
    for c, d in (('topology', -1), ('n_p35', -1), ('hitnuc', 0), ('isnc', -1), ('genie_mode', -1), ('resnum', -99)):
        out[c] = d
        out.loc[m['index'].to_numpy(), c] = m[c].to_numpy()
    out['delta_charge'] = np.where((out.isnc == 1) & (out.genie_mode == 1) & (out.resnum == 0),
                                   np.where(out.hitnuc == 2212, 'Delta+', np.where(out.hitnuc == 2112, 'Delta0', 'other')), 'not_NC_Delta')
    return out
