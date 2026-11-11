"""Proton-origin categories and transparent stratified standardisation (Phase 17).  Pure functions, no I/O.

DESCRIPTIVE ONLY: nothing here changes a cut, a threshold or a policy; the standardiser is a descriptive adjustment, not a causal model.

Origin chain (GENIE record, ``StdHepPdg`` / ``StdHepStatus`` / ``StdHepFm``; rules of ``scripts/proton_truth_origin_scan.py``): the decay nucleon N is the status-14 nucleon whose first mother is the Delta; a stable
(status 1) proton P above 10 MeV is classified from its mother chain.  Mapping to the Phase-17 categories: see ``ORIGIN_CATEGORIES``.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

ORIGIN_CATEGORIES = ["A decay proton", "B1 Delta0: proton from the neutron decay nucleon (FSI-created)", "B2 Delta+: decay-nucleon chain contains a non-proton (charge exchange)", "C proton not descended from the decay nucleon",
                     "D ambiguous chain (several stable proton descendants of the decay nucleon)", "E other / unresolved"]
ORIGIN_GROUP = {ORIGIN_CATEGORIES[0]: "decay proton", ORIGIN_CATEGORIES[1]: "FSI-like", ORIGIN_CATEGORIES[2]: "FSI-like", ORIGIN_CATEGORIES[3]: "FSI-like", ORIGIN_CATEGORIES[4]: "ambiguous", ORIGIN_CATEGORIES[5]: "other / unresolved"}


def origin_category(origin_class, delta_label) -> str:
    """Exclusive category of one truth-1p proton from the stored GENIE chain class and the Delta charge.  ``decay_proton`` -> A; ``fsi_created`` -> B1 if the Delta is neutral (the decay nucleon is a neutron in every
    Delta0 event: a proton can only arise through rescattering) else B2 (Delta+: the chain holds a non-proton); ``not_from_decay`` -> C; ``ambiguous`` -> D; anything else -> E."""
    if origin_class == "decay_proton":
        return ORIGIN_CATEGORIES[0]
    if origin_class == "fsi_created":
        return ORIGIN_CATEGORIES[1] if delta_label == "Delta0" else ORIGIN_CATEGORIES[2]
    if origin_class == "not_from_decay":
        return ORIGIN_CATEGORIES[3]
    if origin_class == "ambiguous":
        return ORIGIN_CATEGORIES[4]
    return ORIGIN_CATEGORIES[5]


def collapse_reco_state(proton_class: str) -> str:
    """Five-way proton reconstruction state used for stratification."""
    return {"proton-typed": "proton-typed", "mu-typed": "mu/pi-typed", "pi-typed": "mu/pi-typed", "e-shower-typed": "e-shower-typed", "e-track-typed": "e-shower-typed", "other-typed": "e-shower-typed",
            "merged / subdominant partner": "merged"}.get(proton_class, "no row / no candidate")


def stratify(df: pd.DataFrame, cols) -> pd.Series:
    """String stratum key from the columns (NaN is its own level)."""
    if not cols:
        return pd.Series("all", index=df.index)
    return df[list(cols)].astype(str).agg("|".join, axis=1)


def _codes(df: pd.DataFrame, strata_cols):
    key = stratify(df, strata_cols); codes, uniq = pd.factorize(key, sort=False); return codes, len(uniq)


def _std_arrays(code, ngrp, is_hi, is_lo, y, min_count, weights):
    """Core of the standardisation on integer arrays."""
    nh = np.bincount(code[is_hi], minlength=ngrp).astype(float); nl = np.bincount(code[is_lo], minlength=ngrp).astype(float)
    sh = np.bincount(code[is_hi], weights=y[is_hi], minlength=ngrp); sl = np.bincount(code[is_lo], weights=y[is_lo], minlength=ngrp)
    nhi, nlo = is_hi.sum(), is_lo.sum(); raw = float(y[is_hi].mean() - y[is_lo].mean()) if nhi and nlo else np.nan
    ok = (nh >= min_count) & (nl >= min_count)
    if not ok.any():
        return dict(raw=raw, raw_on_support=np.nan, adjusted=np.nan, support_fraction=0.0, n_strata=0, n_hi=int(nhi), n_lo=int(nlo))
    mh = np.where(ok, sh / np.maximum(nh, 1), 0.0); ml = np.where(ok, sl / np.maximum(nl, 1), 0.0); w = (nh if weights == "hi" else nl) * ok; tot = nhi if weights == "hi" else nlo
    raw_sup = float(sh[ok].sum() / nh[ok].sum() - sl[ok].sum() / nl[ok].sum())
    return dict(raw=raw, raw_on_support=raw_sup, adjusted=float((w / w.sum() * (mh - ml)).sum()), support_fraction=float(w.sum() / tot), n_strata=int(ok.sum()), n_hi=int(nhi), n_lo=int(nlo))


def standardise(df: pd.DataFrame, group_col: str, g_hi, g_lo, outcome_col: str, strata_cols, min_count: int = 3, weights: str = "hi") -> dict:
    """Direct standardisation of ``outcome(g_hi) - outcome(g_lo)`` over strata of ``strata_cols`` (outcome is 0/1).

    Weights are the distribution of the ``weights`` group (``"hi"`` or ``"lo"``) over the strata that contain at least ``min_count`` events of BOTH groups (the common support).  Returns the raw difference, the raw difference
    restricted to the same support (so that support and adjustment are separated), the standardised difference, the fraction of the weighting group retained and the number of strata."""
    code, n = _codes(df, strata_cols); g = df[group_col].values
    return _std_arrays(code, n, g == g_hi, g == g_lo, df[outcome_col].astype(float).values, min_count, weights)


def bootstrap_standardise(df: pd.DataFrame, group_col: str, g_hi, g_lo, outcome_col: str, strata_cols, n_boot: int = 300, seed: int = 20261111, min_count: int = 3, weights: str = "hi") -> dict:
    """Point estimate plus 68 % bootstrap interval (event resampling, fixed seed) of the standardised difference and of the support-restricted raw difference."""
    rng = np.random.default_rng(seed); code, n = _codes(df, strata_cols); g = df[group_col].values; y = df[outcome_col].astype(float).values; hi = g == g_hi; lo = g == g_lo
    est = _std_arrays(code, n, hi, lo, y, min_count, weights); N = len(df); adj, rs = [], []
    for _ in range(n_boot):
        i = rng.integers(0, N, N); r = _std_arrays(code[i], n, hi[i], lo[i], y[i], min_count, weights); adj.append(r["adjusted"]); rs.append(r["raw_on_support"])
    adj = np.array(adj, float); rs = np.array(rs, float)
    est.update(adjusted_lo68=float(np.nanpercentile(adj, 16)), adjusted_hi68=float(np.nanpercentile(adj, 84)), raw_on_support_lo68=float(np.nanpercentile(rs, 16)), raw_on_support_hi68=float(np.nanpercentile(rs, 84)))
    return est


def fraction_explained(raw: float, adjusted: float) -> float:
    """Share of the raw difference removed by the adjustment (NaN if the raw difference is ~0)."""
    return float((raw - adjusted) / raw) if raw and abs(raw) > 1e-9 else float("nan")
