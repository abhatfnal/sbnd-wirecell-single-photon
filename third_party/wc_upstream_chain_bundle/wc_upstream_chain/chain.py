"""Toolkit-equivalent scoring of the upstream Wire-Cell nu_mu / nu_e taggers: the values a wire-cell-toolkit 0.38.0 step-2
job STORES in wc.T_tagger, computed offline from the stored tagger inputs with any set of weight files.

Reference implementation: wire-cell-toolkit c935e30d (tag 0.38.0) root/src/UbooneNumuBDTScorer.cxx, UbooneNueBDTScorer.cxx,
TmvaGradForest.cxx, plus the simulation-charge patch of the numu_round3af release (wct-0.38.0-numu_sim_dqdx_scale.patch,
sha256 3162b22f...). Validated on Aurora (round2/docs/SP_BDT_UPSTREAM_R4_INTEGRATION_AUDIT.md):
  * the patched in-chain test (18 units, both trees): chain-stored == this code, max |diff| 0 on all 20 outputs;
  * the shipped final models reproduce every stored numu_score / nue_score on 593,723 candidates (stored_l1=True).
This is the COMMON NUMERICAL REFERENCE for Aurora and EAF. It deliberately differs from the release's standalone xgboost
scripts (release/score_release.py, training/numu/score_numu_release.py) on ~1 % of candidates by up to ~0.4 in the final
scores: xgboost evaluates the JSON trees, the chain evaluates the converted TMVA XML trees with float32 cuts; a value
that sits on a split boundary falls on different sides. CONVENTIONS.md lists every convention.
"""
import hashlib
import os

import numpy as np
import pandas as pd

from . import spec as S
from .tmva_grad import SENTINEL_NAN, GradForest, log10_odds

DEFAULT_KEY = ['file_id', 'run', 'subrun', 'event', 'cand']          # Xuyang's table builder (tables/build_tables.py)
NUE_NOT_RUN = np.float32(-15.0)                                      # nue_score when br_filled != 1
SATURATED_LOW = np.float32(log10_odds([SENTINEL_NAN])[0])            # -16.2556: a final model saw a NaN input (EvaluateMVA -999)
KINDS = ('mc', 'data')


class InputError(ValueError):
    pass


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def resolve(dirs, name):
    """WIRECELL_PATH lookup: the first directory (in order) holding uboone/weights/<name>, or holding <name> itself."""
    for d in dirs:
        for p in (os.path.join(d, 'uboone', 'weights', name), os.path.join(d, name)):
            if os.path.isfile(p):
                return p
    raise FileNotFoundError('%s not found along %s' % (name, list(dirs)))


def split_path(weights_path):
    if isinstance(weights_path, str):
        return [d for d in weights_path.split(':') if d]
    return list(weights_path)


def scaled_dqdx(q, k):
    """UbooneNumuBDTScorer::scaled_dqdx (patch): float32(double(q) * k) where q is finite and > 0; unchanged elsewhere."""
    q = np.asarray(q, np.float32)
    if k == 1.0:
        return q
    ok = np.isfinite(q) & (q > 0)
    return np.where(ok, (q.astype(np.float64) * k).astype(np.float32), q).astype(np.float32)


def _f32(x):
    return np.asarray(x, np.float64).astype(np.float32)


def _cand_index(C, O, key):
    ci = pd.MultiIndex.from_frame(C[key])
    if not ci.is_unique:
        raise InputError('candidate key %s is not unique' % key)
    idx = ci.get_indexer(pd.MultiIndex.from_frame(O[key]))
    return idx


def _pool(n, idx, v, how, empty):
    """Chain pooling of float32 object values per candidate (max or min); a candidate without objects gets `empty`."""
    v = v.astype(np.float32)
    if how == 'max':
        out = np.full(n, -np.inf, np.float32); np.maximum.at(out, idx, v)
    else:
        out = np.full(n, np.inf, np.float32); np.minimum.at(out, idx, v)
    has = np.zeros(n, bool); has[idx] = True
    return np.where(has, out, empty).astype(np.float32), has


class ChainScorer:
    """Low-level scorer. Weight files are resolved along `weights_path` (WIRECELL_PATH order: release folders first, the
    shipped wire-cell-data folder last); forests are parsed lazily. Every forest checks its variable list against the spec."""

    def __init__(self, weights_path, models):
        self.dirs = split_path(weights_path)
        self.paths = {m: resolve(self.dirs, S.CHAIN_FILES[m]) for m in models}
        self._f = {}

    def forest(self, m):
        if m not in self._f:
            expect = S.NUMU_FINAL_INPUTS if m == 'numu_final' else S.NUE_FINAL_INPUTS if m == 'nue_final' else S.L1[m]['lists'] + S.L1[m]['scalars']
            self._f[m] = GradForest(self.paths[m], expected_names=expect)
        return self._f[m]

    def provenance(self):
        return {m: dict(file=S.CHAIN_FILES[m], path=p, sha256=sha256(p)) for m, p in sorted(self.paths.items())}

    # ---- level 1 ---------------------------------------------------------------------------------------------------------
    def l1(self, m, C, O, key, k=1.0):
        """(pooled value per candidate, has-object mask, per-candidate 'an object evaluated to -999' mask)."""
        d = S.L1[m]; n = len(C)
        if O is None or len(O) == 0:
            return np.full(n, S.EMPTY[m], np.float32), np.zeros(n, bool), np.zeros(n, bool)
        idx = _cand_index(C, O, key)
        if (idx < 0).any():
            raise InputError('%s: %d object rows without a candidate row' % (m, int((idx < 0).sum())))
        names = d['lists'] + d['scalars']
        missing = [c for c in names if c not in O.columns]
        if missing:
            extra = [c for c in missing if c in C.columns]          # per-candidate scalars (pio_mip_id) copied to every object
            if len(extra) != len(missing):
                raise InputError('%s: object table lacks %s' % (m, sorted(set(missing) - set(extra))))
            O = O.copy()
            for c in extra:
                O[c] = C[c].to_numpy()[idx]
        X = _f32(O[names].to_numpy(np.float64))
        for col, (kind, val) in d['protect'].items():
            j = names.index(col)
            bad = np.isinf(X[:, j]) if kind == 'inf' else np.isnan(X[:, j])
            X[bad, j] = val
        if m == S.SIM_DQDX_L1[0] and k != 1.0:
            j = names.index(S.SIM_DQDX_L1[1]); X[:, j] = scaled_dqdx(X[:, j], k)
        if m == 'pio_2':
            gate = (C[S.PIO_2_GATE[0]].to_numpy() == 1) & (C[S.PIO_2_GATE[1]].to_numpy() == 0)
            keep = gate[idx]; X, idx = X[keep], idx[keep]
        v = self.forest(m).evaluate_mva(X).astype(np.float32)          # float32(EvaluateMVA)
        nan_obj = np.zeros(n, bool); np.logical_or.at(nan_obj, idx, v == np.float32(SENTINEL_NAN))
        pooled, has = _pool(n, idx, v, d['pool'], S.EMPTY[m])
        return pooled, has, nan_obj

    # ---- nu_mu -----------------------------------------------------------------------------------------------------------
    def numu(self, C, O, key, k=1.0, stored_l1=False):
        out, diag = {}, {}
        for m in S.L1_NUMU:
            sc = S.L1[m]['score']
            if stored_l1:
                out[sc] = _f32(C[sc]); diag['nan_obj_' + m] = np.zeros(len(C), bool)
            else:
                out[sc], _, diag['nan_obj_' + m] = self.l1(m, C, O.get(m), key, k if m == S.SIM_DQDX_L1[0] else 1.0)
        X = {nm: (out[nm] if nm in out else _f32(C[nm])) for nm in S.NUMU_FINAL_INPUTS}
        flag = X['numu_cc_flag'].copy(); off = np.zeros(len(C), bool)
        if k != 1.0:
            for fill, col in S.SIM_DQDX_FINAL:
                f = C[fill].to_numpy() == 1
                X[col] = np.where(f, scaled_dqdx(X[col], k), X[col]).astype(np.float32)
            n = len(C); any1_old = np.zeros(n, bool); any1_new = np.zeros(n, bool); any2 = np.zeros(n, bool)
            O1, O2 = O.get('numu_1'), O.get('numu_2')
            if O1 is not None and len(O1):
                i1 = _cand_index(C, O1, key); f1 = O1['flag'].to_numpy() == 1
                q = scaled_dqdx(_f32(O1['numu_cc_1_medium_dQ_dx']), k); cut = _f32(O1['numu_cc_1_dQ_dx_cut'])
                np.logical_or.at(any1_old, i1, f1); np.logical_or.at(any1_new, i1, f1 & (q < cut))
            if O2 is not None and len(O2):
                i2 = _cand_index(C, O2, key); np.logical_or.at(any2, i2, O2['flag'].to_numpy() == 1)
            off = any1_old & ~any1_new & ~any2 & ~(C['numu_cc_flag_3'].to_numpy() == 1)
            flag = np.where(off, np.float32(0), flag).astype(np.float32)
            X['numu_cc_flag'] = flag
        for nm in S.NUMU_NAN_TO_0:
            X[nm] = np.where(np.isnan(X[nm]), np.float32(0), X[nm]).astype(np.float32)
        M = np.column_stack([X[nm] for nm in S.NUMU_FINAL_INPUTS]).astype(np.float32)
        v = self.forest('numu_final').evaluate_mva(M)
        out['numu_score'] = log10_odds(v).astype(np.float32)
        diag.update(numu_cc_flag_bdt=flag, numu_cc_flag_switched_off=off & (C['numu_cc_flag'].to_numpy() == 1),
                    numu_final_nan_input=np.isnan(M).any(1))
        return out, diag

    # ---- nu_e ------------------------------------------------------------------------------------------------------------
    def nue(self, C, O, key, final=True, stored_l1=False):
        out, diag = {}, {}
        for m in S.L1_NUE:
            if stored_l1:
                out[m + '_score'] = _f32(C[m + '_score']); diag['nan_obj_' + m] = np.zeros(len(C), bool)
            else:
                out[m + '_score'], _, diag['nan_obj_' + m] = self.l1(m, C, O.get(m), key)
        if final:
            X = {nm: (out[nm] if nm in out else _f32(C[nm])) for nm in S.NUE_FINAL_INPUTS}
            for col, kind, val in S.NUE_FINAL_PROTECT:
                bad = (X[col] > val) if kind == 'cap' else np.isnan(X[col])
                X[col] = np.where(bad, np.float32(val), X[col]).astype(np.float32)
            M = np.column_stack([X[nm] for nm in S.NUE_FINAL_INPUTS]).astype(np.float32)
            v = self.forest('nue_final').evaluate_mva(M)
            s = log10_odds(v).astype(np.float32)
            run = C[S.NUE_RUN_GATE].to_numpy() == 1
            out['nue_score'] = np.where(run, s, NUE_NOT_RUN).astype(np.float32)
            diag['nue_final_nan_input'] = np.isnan(M).any(1) & run
        return out, diag


class UpstreamChain:
    """High-level interface (the one EAF should use).

        uc = UpstreamChain([nue_release_main_dir, numu_release_wirecell_dir, shipped_wire_cell_data_dir])
        res = uc.score(cands, objs, kind='mc')        # or kind='data'

    cands: one row per candidate: `key` + spec.candidate_inputs() columns (Xuyang's cands_ schema; extra columns ignored).
    objs:  {model: DataFrame} for the 18 level-1 models (spec.L1_ALL): `key` + spec.object_inputs(model) columns, one row per
           object (Xuyang's objs_<model>_ schema). A missing or empty table = no objects for any candidate.
    kind:  'mc' applies the simulation dQ/dx correction to the nu_mu BDT input COPIES; 'data' never does. There is no default:
           the caller must state it. k follows the nu_mu weights (sim_dqdx_scale=None): 1.071 for the numu_round3af release,
           1.0 for the shipped weights (they ran unpatched); any other weight set requires an explicit sim_dqdx_scale.
    Returns one row per input candidate, in input order: `key`, the 20 upstream outputs under their CAF names
    (spec.UPSTREAM_OUTPUTS) and diag_* columns. Values follow the chain convention for EVERY candidate (placeholders,
    br_filled == 0 and NaN inputs included); nothing is replaced by NaN. res.attrs['provenance'] records files and settings.
    """

    def __init__(self, weights_path, sim_dqdx_scale=None, numu=True, nue=True, nue_final=True):
        models = (S.L1_NUMU + ['numu_final'] if numu else []) + (S.L1_NUE + (['nue_final'] if nue_final else []) if nue else [])
        self.do_numu, self.do_nue, self.do_nue_final = numu, nue, nue and nue_final
        self.scorer = ChainScorer(weights_path, models)
        # The simulation dQ/dx correction belongs to the nu_mu MODEL (numu_round3af was trained with it); the shipped nu_mu
        # weights ran in an unpatched chain. Default k therefore follows the resolved nu_mu files: release -> 1.071,
        # shipped -> 1.0; any other weight set needs an explicit sim_dqdx_scale.
        self.numu_route = None
        if numu:
            from .inventory import identify_route
            try:
                self.numu_route = identify_route(self.scorer.dirs)[0]['numu_model_fingerprint']
            except FileNotFoundError:
                self.numu_route = 'unknown'
        if sim_dqdx_scale is None:
            if not numu:
                sim_dqdx_scale = 1.0
            elif self.numu_route == 'release':
                sim_dqdx_scale = S.SIM_DQDX_SCALE
            elif self.numu_route == 'shipped':
                sim_dqdx_scale = 1.0
            else:
                raise InputError('nu_mu weights are neither the pinned release nor the shipped files: pass sim_dqdx_scale explicitly')
        self.k_sim = float(sim_dqdx_scale)

    def check_inputs(self, cands, objs, key, kind):
        if kind not in KINDS:
            raise InputError('kind must be one of %s (no default: simulation and data are scored differently)' % (KINDS,))
        need = [c for c in key if c not in cands.columns]
        need += [c for c in S.candidate_inputs(self.do_numu, self.do_nue) if c not in cands.columns]
        if need:
            raise InputError('candidate table lacks %d columns, e.g. %s' % (len(need), need[:8]))
        if cands.duplicated(key).any():
            raise InputError('candidate key %s is not unique' % key)
        models = (S.L1_NUMU if self.do_numu else []) + (S.L1_NUE if self.do_nue else [])
        for m in models:
            O = objs.get(m)
            if O is None or len(O) == 0:
                continue
            req = key + [c for c in S.object_inputs(m, sim_correction=(kind == 'mc' and self.k_sim != 1.0)) if c not in S.L1[m]['scalars']]
            miss = [c for c in req if c not in O.columns]
            if miss:
                raise InputError('object table %s lacks %s' % (m, miss))

    def score(self, cands, objs, kind, key=None, stored_l1=False, apply_sim_correction=True):
        """See the class docstring. stored_l1=True feeds the final models the STORED level-1 values (closure of the
        shipped final models; the shipped level-1 XMLs are AdaBoost + VarTransform and are refused by the evaluator).
        apply_sim_correction=False on kind='mc' is a DIAGNOSTIC only (what an unpatched chain would store)."""
        key = list(key or DEFAULT_KEY)
        objs = objs or {}
        self.check_inputs(cands, objs, key, kind)
        C = cands.reset_index(drop=True)
        k = self.k_sim if (kind == 'mc' and apply_sim_correction) else 1.0
        res = C[key].copy()
        diag = {}
        if self.do_numu:
            o, d = self.scorer.numu(C, objs, key, k, stored_l1=stored_l1)
            for s in S.NUMU_SCORES:
                res[s] = o[s]
            diag.update(d)
        if self.do_nue:
            o, d = self.scorer.nue(C, objs, key, final=self.do_nue_final, stored_l1=stored_l1)
            for s in S.NUE_L1_SCORES + (['nue_score'] if self.do_nue_final else []):
                res[s] = o[s]
            diag.update(d)
        if 'is_placeholder' in C.columns:
            res['diag_is_placeholder'] = C['is_placeholder'].to_numpy()
        if self.do_nue:
            res['diag_br_filled'] = C['br_filled'].to_numpy()
        if self.do_numu:
            res['diag_numu_cc_flag_bdt'] = diag['numu_cc_flag_bdt']
            res['diag_numu_cc_flag_switched_off'] = diag['numu_cc_flag_switched_off']
            res['diag_numu_final_nan_input'] = diag['numu_final_nan_input']
        if self.do_nue_final:
            res['diag_nue_final_nan_input'] = diag['nue_final_nan_input']
        nan_models = [m for m in S.L1_ALL if 'nan_obj_' + m in diag]
        res['diag_l1_models_with_nan_object'] = np.sum([diag['nan_obj_' + m] for m in nan_models], axis=0).astype(np.int16) if nan_models else 0
        res['diag_sim_dqdx_scale'] = np.float64(k)
        from . import __version__
        res.attrs['provenance'] = dict(bundle='wc_upstream_chain', bundle_version=__version__, kind=kind, sim_dqdx_scale_applied=k,
                                       numu_route=self.numu_route,
                                       stored_l1=bool(stored_l1), key=key, weights_path=self.scorer.dirs, files=self.scorer.provenance(),
                                       n_candidates=int(len(C)))
        return res


def compare_exact(a, b, columns, key=None):
    """Bit-level comparison of two score tables (float32, NaN == NaN). Returns {column: dict(n, exact, max_abs)}."""
    if key is not None:
        b = a[key].merge(b, on=key, how='left', validate='one_to_one')
    out = {}
    for c in columns:
        x, y = _f32(a[c]), _f32(b[c])
        same = (x == y) | (np.isnan(x) & np.isnan(y))
        d = np.abs(x.astype(np.float64) - y.astype(np.float64)); d[same] = 0
        out[c] = dict(n=int(len(x)), exact=int(same.sum()), max_abs=float(np.nanmax(d)) if len(d) else 0.0)
    return out
