"""Numpy evaluator for TMVA "BDT::BDT" weight files with BoostType=Grad (no ROOT).

Arithmetic, as in TMVA MethodBDT / DecisionTreeNode and the Wire-Cell TmvaGradForest:
  * inputs and node cuts are float32; at a node go RIGHT when (x >= cut), inverted when cType == 0; stop at nType != 0
  * raw = sum over trees of the leaf response (double)          -- Grad boosting ignores boostWeight (it is 1)
  * EvaluateMVA = tanh(raw) = 2 / (1 + exp(-2 raw)) - 1;  any NaN input -> -999 (TMVA::Reader)
  * stored score = log10((1 + v) / (1 - v)) = (2 / ln 10) * raw, |v| >= 1 pulled to +-nextafter(1, 0)
    -- the convention of MicroBooNE's cal_single_photon_*_bdts_xgboost (wcp-uboone-bdt inc/WCPLEEANA/bdt.h) and of
       the SBND toolkit's nue_score / numu_score. The frozen single-photon thresholds (0.4, 0.2, -0.05, -1.0;
       inc/WCPLEEANA/cuts.h is_singlephoton_sel) are cuts on THIS score.

Refused, as in the C++ fast reader: input transformations, BoostType != Grad, preselection, Fisher-cut nodes,
regression-incompatible leaves, a variable list that differs from the caller's.
"""
import math
import re

import numpy as np

_TAG = re.compile(rb'<(/?)(BinaryTree|Node)\b([^>]*?)(/?)>')
_ATTR = re.compile(rb'(\w+)="([^"]*)"')
SENTINEL_NAN = -999.0


def _bool(s):
    return s.strip() not in (b'0', b'false')


class GradForest:
    def __init__(self, path, expected_names=None):
        doc = open(path, 'rb').read()
        ms = doc.find(b'<MethodSetup')
        if ms < 0 or b'Method="BDT::BDT"' not in doc[ms:ms + 300]:
            raise ValueError('not a TMVA BDT::BDT weight file: %s' % path)
        head_end = doc.find(b'<Weights', ms)
        head = doc[ms:head_end]
        nvar = int(re.search(rb'<Variables NVar="(\d+)"', head).group(1))
        names = [(int(i), e.decode()) for i, e in re.findall(rb'<Variable VarIndex="(\d+)" Expression="([^"]*)"', head)]
        if not names:   # attribute order differs between TMVA versions
            names = [(k, e.decode()) for k, e in enumerate(re.findall(rb'<Variable [^>]*Expression="([^"]*)"', head))]
        names.sort()
        self.names = [e for _, e in names][:nvar]
        if len(self.names) != nvar:
            raise ValueError('fewer <Variable> elements than NVar')
        if expected_names is not None and list(expected_names) != self.names:
            raise ValueError('variable list differs from the caller (names or order)')
        m = re.search(rb'<Transformations NTransformations="(\d+)"', head)
        if m and int(m.group(1)) != 0:
            raise ValueError('input-variable transformations present')
        self.options = {k.decode(): v.decode().strip() for k, v in
                        re.findall(rb'<Option [^>]*?name="(\w+)"[^>]*>([^<]*)</Option>', head)}
        if self.options.get('BoostType', '').lower() != 'grad':
            raise ValueError('BoostType %r is not Grad' % self.options.get('BoostType'))
        if self.options.get('DoPreselection', 'false').lower() not in ('false', '0'):
            raise ValueError('DoPreselection is on')
        self.info = dict((k.decode(), v.decode()) for k, v in re.findall(rb'<Info name="([^"]+)" value="([^"]*)"', head))
        wtag = doc[head_end:doc.find(b'>', head_end)]
        if b'PreselectionLowBkgVar0' in wtag:
            raise ValueError('preselection cuts present')
        ntrees = int(dict(_ATTR.findall(wtag))[b'NTrees'])
        wend = doc.find(b'</Weights>', head_end)
        cut, res, ivar, leaf, ctype, left, right, roots, bw = [], [], [], [], [], [], [], [], []
        stack = []
        for t in _TAG.finditer(doc, head_end, wend):
            close, kind, attrs, selfclose = t.groups()
            if kind == b'BinaryTree':
                if not close:
                    roots.append(-1)
                    bw.append(float(dict(_ATTR.findall(attrs)).get(b'boostWeight', b'1')))
                elif stack:
                    raise ValueError('unclosed <Node> at </BinaryTree>')
                continue
            if close:
                stack.pop()
                continue
            a = dict(_ATTR.findall(attrs))
            if int(a.get(b'NCoef', b'0')) != 0:
                raise ValueError('Fisher-cut node')
            k = len(cut)
            cut.append(float(a[b'Cut']))
            res.append(float(a.get(b'res', b'-99')))
            ivar.append(int(a[b'IVar']))
            leaf.append(int(a[b'nType']) != 0)
            ctype.append(_bool(a[b'cType']))
            left.append(-1)
            right.append(-1)
            if not stack:
                if roots[-1] >= 0:
                    raise ValueError('two root nodes in one tree')
                roots[-1] = k
            elif a[b'pos'] == b'l':
                left[stack[-1]] = k
            elif a[b'pos'] == b'r':
                right[stack[-1]] = k
            else:
                raise ValueError('child node with pos neither l nor r')
            if not selfclose:
                stack.append(k)
        if len(roots) != ntrees:
            raise ValueError('NTrees=%d but %d trees found' % (ntrees, len(roots)))
        self.boost_weights = np.array(bw)
        self.cut = np.array(cut, np.float64).astype(np.float32)
        self.res = np.array(res, np.float64).astype(np.float32)
        self.ivar = np.array(ivar, np.int32)
        self.leaf = np.array(leaf, bool)
        self.ctype = np.array(ctype, bool)
        self.left = np.array(left, np.int32)
        self.right = np.array(right, np.int32)
        self.roots = np.array(roots, np.int32)
        inner = ~self.leaf
        if (self.left[inner] < 0).any() or (self.right[inner] < 0).any():
            raise ValueError('intermediate node missing a child')
        if (self.ivar[inner] >= nvar).any():
            raise ValueError('node selects a variable beyond NVar')
        self.ivar[self.leaf] = 0

    @property
    def ntrees(self):
        return len(self.roots)

    def raw(self, X):
        """Sum of leaf responses per row of X (n, nvar); NaN rows give NaN."""
        X = np.ascontiguousarray(X, dtype=np.float32)
        if X.ndim != 2 or X.shape[1] != len(self.names):
            raise ValueError('X must be (n, %d)' % len(self.names))
        rows = np.arange(len(X))
        total = np.zeros(len(X), np.float64)
        for r in self.roots:
            cur = np.full(len(X), r, np.int32)
            live = ~self.leaf[cur]
            while live.any():
                c = cur[live]
                go_right = X[rows[live], self.ivar[c]] >= self.cut[c]
                go_right = np.where(self.ctype[c], go_right, ~go_right)
                cur[live] = np.where(go_right, self.right[c], self.left[c])
                live = ~self.leaf[cur]
            total += self.res[cur].astype(np.float64)
        total[np.isnan(X).any(axis=1)] = np.nan
        return total

    def evaluate_mva(self, X):
        """TMVA::Reader::EvaluateMVA: tanh(raw), -999 where any input is NaN."""
        r = self.raw(X)
        v = 2.0 / (1.0 + np.exp(-2.0 * r)) - 1.0
        v[np.isnan(r)] = SENTINEL_NAN
        return v


def log10_odds(v):
    """MicroBooNE / Wire-Cell stored score from an EvaluateMVA value."""
    v = np.array(v, np.float64)
    sat = math.nextafter(1.0, 0.0)
    bad = ~np.isfinite(v) | (np.abs(v) >= 1.0)
    v[bad] = np.where(np.isfinite(v[bad]) & (v[bad] > 0), sat, -sat)
    return np.log10((1.0 + v) / (1.0 - v))


def threshold_in_tanh_space(log_odds_cut):
    """The EvaluateMVA value that a log10-odds cut corresponds to: v = (10^c - 1) / (10^c + 1)."""
    t = 10.0 ** log_odds_cut
    return (t - 1.0) / (t + 1.0)
