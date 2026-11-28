"""Offline emulation of the Wire-Cell toolkit 0.38.0 upstream tagger scoring (UbooneNumuBDTScorer, UbooneNueBDTScorer),
for re-scoring stored WCL1116 candidates with another set of weight files, exactly as a genuine production would.

Reference code: wire-cell-toolkit c935e30d (tag 0.38.0) root/src/UbooneNumuBDTScorer.cxx, UbooneNueBDTScorer.cxx,
TmvaGradForest.cxx; the numu simulation-charge patch of Xuyang Ning's release (Ningclover/sbnd-wirecell-bdt @ 0f13988d,
releases/numu_round3af/wirecell/patches/wct-0.38.0-numu_sim_dqdx_scale.patch). What the chain does, and this module does:

  numu small models (no candidate gate; the chain runs them on every candidate):
    numu_1     per numu_cc_1 segment, inputs float32; numu_cc_1_dQ_dx_cut = +-inf -> 10; with the sim scale k != 1 the
               medium_dQ_dx copy handed to the BDT is float32(double(q) * k) where q is finite and > 0;
               value = max over segments of float32(EvaluateMVA); no segment -> -0.4
    numu_2     max over numu_cc_2 objects; none -> -0.1
    cosmict_10 min over cosmict_10 objects; cosmict_10_angle_beam NaN -> 0; none -> 0.7
  numu final (numu_scalars_scores_0923.xml, 74 inputs, the order of config/upstream/numu_l2_inputs_74.txt):
    the three pooled values above replace the stored ones; with k != 1 the six cosmict_{2,3,7}_dQ_dx_{end,front}
    copies are scaled where cosmict_N_filled == 1, and the numu_cc_flag copy becomes 0 when some numu_1 segment had
    flag 1, none keeps it with the scaled dQ/dx below its numu_cc_1_dQ_dx_cut, no numu_cc_2 flag is 1 and
    numu_cc_flag_3 != 1; NaN -> 0 on cosmict_4_angle_beam, cosmict_7_angle_beam, cosmict_7_theta, cosmict_7_phi;
    numu_score = float32(log10((1 + v) / (1 - v))), v = EvaluateMVA (degenerate v saturated as bdt_log_odds_score).
    The STORED cosmict_* / numu_cc_flag values stay raw (only the BDT copies change).
  nue small models (15; no br_filled gate): min over the model's objects of float32(EvaluateMVA); none -> the model's
    constant; pio_2 runs only when pio_filled == 1 and pio_flag_pio == 0 (else its constant).
  nue final (XGB_nue_seed2_0923.xml, 258 inputs): protections mip_min_dis, mip_quality_shortest_length capped at 1000,
    mip_quality_shortest_angle NaN -> 0, stem_dir_ratio NaN -> 1; br_filled == 1 -> float32(log10 odds), else -15.
  EvaluateMVA (TMVA::Reader / TmvaGradForest): v = 2 / (1 + exp(-2 sum)) - 1, sum over trees of float32 leaf responses,
    nodes compared in float32; ANY NaN input -> -999 (so a NaN object wins a min and loses a max).

The tables are those of tools/extract_upstream_inputs.py (Xuyang's cands_ / objs_ schema).
"""
import hashlib
import importlib.util
import os

import numpy as np

from sp_retrain.tmva_grad import GradForest, log10_odds

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = os.path.join(os.path.dirname(HERE), 'config', 'upstream')


def _lines(name):
    return [l.strip() for l in open(os.path.join(CFG, name)) if l.strip()]


def _load_l1_spec():
    spec = importlib.util.spec_from_file_location('l1_models_xning_0f13988d', os.path.join(CFG, 'l1_models_xning_0f13988d.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.L1_MODELS, mod.NUE_L1


NUMU_FINAL_INPUTS = _lines('numu_l2_inputs_74.txt')
NUE_FINAL_INPUTS = _lines('nue_l2_inputs_258.txt')
L1_SPEC, L1_NUE = _load_l1_spec()
L1_NUMU = ['numu_1', 'numu_2', 'cosmict_10']
L1_ALL = L1_NUMU + list(L1_NUE)
NUMU_SCORES = ['numu_1_score', 'numu_2_score', 'cosmict_10_score', 'numu_score']
NUE_L1_SCORES = [m + '_score' for m in L1_NUE]
STORED_SCORES = ['numu_score', 'numu_1_score', 'numu_2_score', 'numu_3_score', 'cosmict_10_score', 'nue_score'] + NUE_L1_SCORES
GATES = ['br_filled', 'pio_filled', 'pio_flag_pio', 'pio_mip_id', 'numu_cc_flag_3', 'cosmict_flag_1', 'numu_cc_flag',
         'neutrino_type', 'nu_x', 'nu_y', 'nu_z', 'cosmict_2_filled', 'cosmict_3_filled', 'cosmict_7_filled',
         'mip_min_dis', 'mip_quality_shortest_length', 'mip_quality_shortest_angle', 'stem_dir_ratio']
_NOT_TAGGER = {'kine_reco_Enu'} | set(NUMU_SCORES) | set(NUE_L1_SCORES)
CAND_SCALARS = list(dict.fromkeys([n for n in NUMU_FINAL_INPUTS + NUE_FINAL_INPUTS if n not in _NOT_TAGGER] + GATES + STORED_SCORES))

FILES = dict(numu_1='numu_tagger1.weights.xml', numu_2='numu_tagger2.weights.xml', cosmict_10='cos_tagger_10.weights.xml',
             numu_final='numu_scalars_scores_0923.xml', nue_final='XGB_nue_seed2_0923.xml')
FILES.update({m: '%s_BDT.weights.xml' % m for m in L1_NUE})
EMPTY = {m: np.float32(L1_SPEC[m]['empty']) for m in L1_ALL}
SIM_DQDX_FINAL = [('cosmict_2_filled', 'cosmict_2_dQ_dx_end'), ('cosmict_2_filled', 'cosmict_2_dQ_dx_front'),
                  ('cosmict_3_filled', 'cosmict_3_dQ_dx_end'), ('cosmict_3_filled', 'cosmict_3_dQ_dx_front'),
                  ('cosmict_7_filled', 'cosmict_7_dQ_dx_end'), ('cosmict_7_filled', 'cosmict_7_dQ_dx_front')]
NUMU_NAN_TO_0 = ['cosmict_4_angle_beam', 'cosmict_7_angle_beam', 'cosmict_7_theta', 'cosmict_7_phi']
KEY = ['file_id', 'run', 'subrun', 'event', 'cand']


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
    raise FileNotFoundError('%s not found along %s' % (name, dirs))


def empty_objs(model):
    import pandas as pd
    d = L1_SPEC[model]
    cols = {'sample': 'object', 'file_id': 'object', 'run': 'int64', 'subrun': 'int64', 'event': 'int64', 'cand': 'int64', 'index': 'int64'}
    for n in d['lists'] + d['scalars'] + ['flag']:
        cols[n] = 'float64'
    return pd.DataFrame({c: pd.Series(dtype=t) for c, t in cols.items()})


def scaled_dqdx(q, k):
    """UbooneNumuBDTScorer::scaled_dqdx: float32(double(q) * k) where q is finite and > 0 (k != 1)."""
    q = np.asarray(q, np.float32)
    if k == 1.0:
        return q
    ok = np.isfinite(q) & (q > 0)
    return np.where(ok, (q.astype(np.float64) * k).astype(np.float32), q).astype(np.float32)


def cand_index(C, O):
    """Row of C for every row of O (on KEY); -1 when absent. C's KEY must be unique."""
    import pandas as pd
    ci = pd.MultiIndex.from_frame(C[KEY])
    if not ci.is_unique:
        raise ValueError('candidate key is not unique')
    return ci.get_indexer(pd.MultiIndex.from_frame(O[KEY]))


def _pool(n, idx, v, how, empty):
    """Chain pooling of float32 object values per candidate; candidates without objects get the constant."""
    v = v.astype(np.float32)
    if how == 'max':
        out = np.full(n, -np.inf, np.float32); np.maximum.at(out, idx, v)
    else:
        out = np.full(n, np.inf, np.float32); np.minimum.at(out, idx, v)
    has = np.zeros(n, bool); has[idx] = True
    return np.where(has, out, empty).astype(np.float32), has


class ChainScorer:
    """Weight files resolved along `dirs` (WIRECELL_PATH order); forests parsed on first use."""

    def __init__(self, dirs, models):
        self.dirs = list(dirs)
        self.paths = {m: resolve(self.dirs, FILES[m]) for m in models}
        self._f = {}

    def forest(self, m):
        if m not in self._f:
            expect = None
            if m == 'numu_final':
                expect = NUMU_FINAL_INPUTS
            elif m == 'nue_final':
                expect = NUE_FINAL_INPUTS
            elif m in L1_SPEC:
                expect = L1_SPEC[m]['lists'] + L1_SPEC[m]['scalars']
            self._f[m] = GradForest(self.paths[m], expected_names=expect)
        return self._f[m]

    def provenance(self):
        return {m: dict(path=p, sha256=sha256(p)) for m, p in self.paths.items()}

    # ---- level 1 -------------------------------------------------------------------------------------------------
    def l1(self, m, C, O, k=1.0):
        d = L1_SPEC[m]
        n = len(C)
        if O is None or len(O) == 0:
            return np.full(n, EMPTY[m], np.float32), np.zeros(n, bool), 0
        idx = cand_index(C, O)
        if (idx < 0).any():
            raise ValueError('%s: %d objects without a candidate row' % (m, int((idx < 0).sum())))
        names = d['lists'] + d['scalars']
        X = O[names].to_numpy(np.float64).astype(np.float32)
        for col, (kind, val) in d.get('protect', {}).items():
            j = names.index(col)
            bad = np.isinf(X[:, j]) if kind == 'inf' else np.isnan(X[:, j])
            X[bad, j] = val
        if m == 'numu_1' and k != 1.0:
            j = names.index('numu_cc_1_medium_dQ_dx'); X[:, j] = scaled_dqdx(X[:, j], k)
        if m == 'pio_2':
            gate = ((C['pio_filled'].to_numpy() == 1) & (C['pio_flag_pio'].to_numpy() == 0))
            keep = gate[idx]
            X, idx = X[keep], idx[keep]
        v = self.forest(m).evaluate_mva(X).astype(np.float32)
        n_nan_obj = int((v == np.float32(-999.0)).sum())
        pooled, has = _pool(n, idx, v, d['pool'], EMPTY[m])
        return pooled, has, n_nan_obj

    # ---- nu_mu -----------------------------------------------------------------------------------------------------
    def numu(self, C, O, k=1.0, stored_l1=False):
        """dict(numu_1_score, numu_2_score, cosmict_10_score, numu_score, numu_cc_flag_bdt, nan_objects).
        stored_l1: feed the final model the STORED small-model values (closure of the shipped final model, whose small
        models are TMVA AdaBoost with input transformations that this evaluator does not implement)."""
        out, nan_obj = {}, {}
        for m in L1_NUMU:
            if stored_l1:
                out[L1_SPEC[m]['score']] = C[L1_SPEC[m]['score']].to_numpy(np.float64).astype(np.float32)
            else:
                out[L1_SPEC[m]['score']], _, nan_obj[m] = self.l1(m, C, O.get(m), k if m == 'numu_1' else 1.0)
        X = {}
        for name in NUMU_FINAL_INPUTS:
            X[name] = out[name] if name in out else C[name].to_numpy(np.float64).astype(np.float32)
        flag = X['numu_cc_flag'].copy()
        if k != 1.0:
            for fill, col in SIM_DQDX_FINAL:
                f = C[fill].to_numpy() == 1
                X[col] = np.where(f, scaled_dqdx(X[col], k), X[col]).astype(np.float32)
            n = len(C)
            any1_old = np.zeros(n, bool); any1_new = np.zeros(n, bool); any2 = np.zeros(n, bool)
            O1, O2 = O.get('numu_1'), O.get('numu_2')
            if O1 is not None and len(O1):
                i1 = cand_index(C, O1)
                f1 = O1['flag'].to_numpy() == 1
                q = scaled_dqdx(O1['numu_cc_1_medium_dQ_dx'].to_numpy(np.float64).astype(np.float32), k)
                cut = O1['numu_cc_1_dQ_dx_cut'].to_numpy(np.float64).astype(np.float32)
                np.logical_or.at(any1_old, i1, f1)
                np.logical_or.at(any1_new, i1, f1 & (q < cut))
            if O2 is not None and len(O2):
                i2 = cand_index(C, O2)
                np.logical_or.at(any2, i2, O2['flag'].to_numpy() == 1)
            f3 = C['numu_cc_flag_3'].to_numpy() == 1
            off = any1_old & ~any1_new & ~any2 & ~f3
            flag = np.where(off, np.float32(0), flag).astype(np.float32)
            X['numu_cc_flag'] = flag
        for name in NUMU_NAN_TO_0:
            X[name] = np.where(np.isnan(X[name]), np.float32(0), X[name]).astype(np.float32)
        M = np.column_stack([X[nm] for nm in NUMU_FINAL_INPUTS]).astype(np.float32)
        v = self.forest('numu_final').evaluate_mva(M)
        out['numu_score'] = log10_odds(v).astype(np.float32)
        out['numu_cc_flag_bdt'] = flag
        out['nan_objects'] = nan_obj
        return out

    # ---- nu_e ------------------------------------------------------------------------------------------------------
    def nue(self, C, O, final=True, stored_l1=False):
        """dict(<15 L1>_score, nue_score (if final), nan_objects); stored_l1 as in numu()."""
        out, nan_obj = {}, {}
        for m in L1_NUE:
            if stored_l1:
                out[m + '_score'] = C[m + '_score'].to_numpy(np.float64).astype(np.float32)
            else:
                out[m + '_score'], _, nan_obj[m] = self.l1(m, C, O.get(m))
        if final:
            X = {}
            for name in NUE_FINAL_INPUTS:
                X[name] = out[name] if name in out else C[name].to_numpy(np.float64).astype(np.float32)
            X['mip_min_dis'] = np.where(X['mip_min_dis'] > 1000, np.float32(1000), X['mip_min_dis']).astype(np.float32)
            X['mip_quality_shortest_length'] = np.where(X['mip_quality_shortest_length'] > 1000, np.float32(1000),
                                                        X['mip_quality_shortest_length']).astype(np.float32)
            X['mip_quality_shortest_angle'] = np.where(np.isnan(X['mip_quality_shortest_angle']), np.float32(0),
                                                       X['mip_quality_shortest_angle']).astype(np.float32)
            X['stem_dir_ratio'] = np.where(np.isnan(X['stem_dir_ratio']), np.float32(1), X['stem_dir_ratio']).astype(np.float32)
            M = np.column_stack([X[nm] for nm in NUE_FINAL_INPUTS]).astype(np.float32)
            v = self.forest('nue_final').evaluate_mva(M)
            s = log10_odds(v).astype(np.float32)
            out['nue_score'] = np.where(C['br_filled'].to_numpy() == 1, s, np.float32(-15.0)).astype(np.float32)
        out['nan_objects'] = nan_obj
        return out


NUMU_FINGERPRINT_MODELS = ['numu_1', 'numu_2', 'numu_3', 'cosmict_10', 'numu_final']
FILES['numu_3'] = 'numu_tagger3.weights.xml'


def fingerprint(dirs, models):
    """64-hex upstream fingerprint of the final-domain contract (SP_BDT_FINAL_DOMAIN_RERUN_CONTRACT.md): sha256 over the
    sorted lines '<file name> <sha256>' of the weight files the chain would resolve along `dirs` (WIRECELL_PATH order).
    numu_model_fingerprint: NUMU_FINGERPRINT_MODELS (final + all four level-1 files, numu_tagger3 included);
    nue_l1_fingerprints: the 15 nu_e level-1 files (L1_NUE)."""
    lines = sorted('%s %s' % (FILES[m], sha256(resolve(dirs, FILES[m]))) for m in models)
    return hashlib.sha256(('\n'.join(lines) + '\n').encode()).hexdigest(), lines
