"""AUDIT tools for the FROZEN ``single_photon_other_bdt_final.xml`` (no retraining, no tuning, no surrogate model).

* :func:`scores_tmva_float32`  independent evaluator that follows the TMVA ``DecisionTreeNode::GoesRight`` rule (right iff ``float(x) >= float(cut)`` for cutType 1; float32 values/cuts,
  float32 leaf responses summed in double, response ``2/(1+exp(-2 sum)) - 1``). It is separate from the frozen scorer in :mod:`bdt` (which compares ``x <= cut`` in float64).
* :func:`tree_contributions`   the exact additive decomposition ``margin = sum_t boostWeight_t * leaf_t`` (score = tanh(margin)).
* :func:`interventional_shap`  EXACT interventional TreeSHAP of the margin of this very ensemble against an explicit background sample (the model is evaluated as-is; the only choice is the
  background, which is part of the question: 'explain the difference between two event classes'). Validated by additivity and by brute-force Shapley values on a toy ensemble (tests).
"""
from __future__ import annotations

import math

import numpy as np

from .bdt import TmvaBdt


def _f32(a):
    return np.asarray(a, dtype=np.float32)


def leaf_values_f32(model: TmvaBdt, X: np.ndarray) -> np.ndarray:
    """(n, n_trees) leaf responses (float32 values, float32 cuts, TMVA GoesRight rule: right iff x >= cut)."""
    X32 = _f32(X); n = len(X32); out = np.zeros((n, len(model.trees)))
    for ti, t in enumerate(model.trees):
        cut32 = _f32(t.cut); res32 = _f32(t.res); node = np.zeros(n, dtype=np.int64)
        for _ in range(256):
            iv = t.ivar[node]; internal = iv >= 0
            if not internal.any():
                break
            xv = X32[np.arange(n), np.where(internal, iv, 0)]
            right = xv >= cut32[node]
            node = np.where(internal, np.where(right, t.right[node], t.left[node]), node)
        out[:, ti] = res32[node].astype(np.float64)
    return out


def tree_contributions(model: TmvaBdt, X: np.ndarray) -> np.ndarray:
    """(n, n_trees): ``boostWeight_t * leaf_t`` so that ``tanh(row sum)`` is the score (TMVA semantics)."""
    return leaf_values_f32(model, X) * model.boost[None, :]


def scores_tmva_float32(model: TmvaBdt, X: np.ndarray) -> np.ndarray:
    """Independent TMVA-semantics scores; rows with any non-finite input are NaN (the repository's 'not evaluable' convention)."""
    X = np.asarray(X, dtype=np.float64); ok = np.isfinite(X).all(axis=1); out = np.full(len(X), np.nan)
    if ok.any():
        m = tree_contributions(model, X[ok]).sum(axis=1)
        out[ok] = 2.0 / (1.0 + np.exp(-2.0 * m)) - 1.0
    return out


def scalar_score_tmva(xml_path, x) -> float:
    """Slow, transparent per-event scalar implementation straight from the XML (used to check the vectorised evaluators on a subset)."""
    import xml.etree.ElementTree as ET
    root = ET.parse(xml_path).getroot(); xs = [np.float32(v) for v in x]; s = 0.0
    for bt in root.find("Weights").findall("BinaryTree"):
        node = bt.find("Node")
        while True:
            kids = [c for c in node if c.tag == "Node"]
            if not kids:
                s += float(np.float32(node.get("res"))) * float(bt.get("boostWeight")); break
            l = next(c for c in kids if c.get("pos") == "l"); r = next(c for c in kids if c.get("pos") == "r")
            node = r if xs[int(node.get("IVar"))] >= np.float32(node.get("Cut")) else l
    return 2.0 / (1.0 + math.exp(-2.0 * s)) - 1.0


def leaf_paths(model: TmvaBdt) -> list[tuple[int, float, dict]]:
    """For every leaf: (tree index, boost*res, {feature: (lo, hi)}) with the path conditions merged per feature: a value passes iff ``lo <= x < hi`` (TMVA: left iff x < cut)."""
    out = []
    for ti, t in enumerate(model.trees):
        def walk(node, cond):
            if t.ivar[node] < 0:
                out.append((ti, float(model.boost[ti] * np.float32(t.res[node])), dict(cond))); return
            f, c = int(t.ivar[node]), float(np.float32(t.cut[node])); lo, hi = cond.get(f, (-np.inf, np.inf))
            left = dict(cond); left[f] = (lo, min(hi, c)); walk(t.left[node], left)              # left: x < cut
            right = dict(cond); right[f] = (max(lo, c), hi); walk(t.right[node], right)         # right: x >= cut
        walk(0, {})
    return out


def interventional_shap(model: TmvaBdt, Xf: np.ndarray, Xb: np.ndarray, paths=None) -> dict:
    """Exact interventional Shapley values of the ensemble margin: ``phi[i, f]`` = contribution of variable f to ``margin(Xf[i]) - mean_b margin(Xb)``, with the coalition game
    ``v(S) = mean_b margin(x_S, b_not-S)``. Additivity: ``margin(Xf[i]) = base + sum_f phi[i, f]`` with ``base = mean_b margin(Xb)`` (checked by the caller). Rows must be finite.
    Per leaf the path features split into those only x satisfies (A), only the background row satisfies (B), both (irrelevant) and neither (leaf unreachable); then
    phi_i = +leaf (|A|-1)! |B|! / (|A|+|B|)!  for i in A and -leaf |A|! (|B|-1)! / (|A|+|B|)!  for i in B."""
    paths = paths or leaf_paths(model); Xf = _f32(Xf); Xb = _f32(Xb); nf, nb, nv = len(Xf), len(Xb), Xf.shape[1]
    fact = [math.factorial(i) for i in range(2 * nv + 2)]
    phi = np.zeros((nf, nv))
    for _, val, cond in paths:
        if not cond or val == 0.0:
            continue
        feats = list(cond); lo = np.array([cond[f][0] for f in feats], dtype=np.float32); hi = np.array([cond[f][1] for f in feats], dtype=np.float32)
        px = ((Xf[:, feats] >= lo) & (Xf[:, feats] < hi)).astype(np.float64); pb = ((Xb[:, feats] >= lo) & (Xb[:, feats] < hi)).astype(np.float64)
        A = px @ (1 - pb).T; B = (1 - px) @ pb.T; D = (1 - px) @ (1 - pb).T
        reach = D == 0
        wA = np.zeros_like(A); wB = np.zeros_like(A)
        ia = reach & (A > 0)
        if ia.any():
            wA[ia] = [fact[int(a) - 1] * fact[int(b)] / fact[int(a) + int(b)] for a, b in zip(A[ia], B[ia])]
        ib = reach & (B > 0)
        if ib.any():
            wB[ib] = [fact[int(a)] * fact[int(b) - 1] / fact[int(a) + int(b)] for a, b in zip(A[ib], B[ib])]
        ca = px * (wA @ (1 - pb))                  # features where x passes and the background row fails
        cb = (1 - px) * (wB @ pb)                  # features where the background row passes and x fails
        phi[:, feats] += val * (ca - cb) / nb
    base_margin = float(tree_contributions(model, np.asarray(Xb, dtype=np.float64)).sum(axis=1).mean())
    return dict(phi=phi, base=base_margin)
