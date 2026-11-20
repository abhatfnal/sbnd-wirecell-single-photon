"""Data-vs-MC histogramming for the NC-Delta package: weighted MC stack at a common exposure, data points with Poisson errors, Data/Prediction ratio.
Statistical uncertainty ONLY (no systematic band exists yet). Every plot request goes through the data-policy gate."""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np, pandas as pd
from . import datapolicy as DP

SYSTEMATICS_STATUS = "statistical uncertainty only"
CATEGORY_ORDER = ["SIGNAL_NCDELTA", "NC_PI0", "CC_PI0", "NUE_CC", "NUMU_CC", "OTHER_NC", "OTHER_CC", "OUTSIDE_TPC_NU", "COSMIC_OR_UNMATCHED", "MULTI_OR_AMBIGUOUS"]


def hist(values, weights, bins):
    """Weighted histogram: (sum w, sqrt(sum w^2)) per bin. Under/overflow are NOT dropped silently: they go to the returned dict."""
    v = np.asarray(values, float); w = np.asarray(weights, float); ok = np.isfinite(v)
    h, _ = np.histogram(v[ok], bins, weights=w[ok]); h2, _ = np.histogram(v[ok], bins, weights=w[ok] ** 2)
    out = dict(under=float(w[ok & (v < bins[0])].sum()), over=float(w[ok & (v >= bins[-1])].sum()), nonfinite=int((~ok).sum()))
    return h, np.sqrt(h2), out


def poisson_interval(n, cl=0.6827):
    """Central Garwood interval for an observed count (data points)."""
    from scipy.stats import chi2
    n = np.asarray(n, float); a = 1 - cl
    lo = np.where(n > 0, 0.5 * chi2.ppf(a / 2, 2 * np.maximum(n, 1)), 0.0); hi = 0.5 * chi2.ppf(1 - a / 2, 2 * (n + 1))
    return lo, hi


def ratio(data, pred, pred_err):
    """Data / prediction with the data Garwood interval and the MC stat error combined; NaN where pred == 0 (not statistically meaningful)."""
    d = np.asarray(data, float); p = np.asarray(pred, float); lo, hi = poisson_interval(d)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.where(p > 0, d / p, np.nan); rlo = np.where(p > 0, (d - lo) / p, np.nan); rhi = np.where(p > 0, (hi - d) / p, np.nan)
        mc = np.where(p > 0, np.asarray(pred_err, float) / p, np.nan)
    return r, rlo, rhi, mc


@dataclass
class Component:
    name: str                  # category label for MC, 'data' for data
    values: np.ndarray
    weights: np.ndarray


@dataclass
class DataMCRequest:
    variable: str
    bins: np.ndarray
    stage: str
    stage_kind: str            # preselection | sideband | signal_region
    topology: str              # inclusive | 1g0p | 1gNp
    score_source: str
    pot_target: float
    data_sample: str | None = "beam_on_open"


def build_stack(mc: dict, bins) -> dict:
    """mc: {category: Component}. Returns per-category (h, err) plus total prediction and its stat error (quadrature over components)."""
    cats = [c for c in CATEGORY_ORDER if c in mc] + [c for c in mc if c not in CATEGORY_ORDER]
    parts = {c: hist(mc[c].values, mc[c].weights, bins)[:2] for c in cats}
    tot = sum(p[0] for p in parts.values()); err = np.sqrt(sum(p[1] ** 2 for p in parts.values()))
    return dict(parts=parts, total=tot, err=err, order=cats)


def check_request(req: DataMCRequest, policy: dict | None = None) -> None:
    if req.data_sample:
        DP.check(req.data_sample, req.stage_kind, policy)


def normalisation_check(stack: dict, expected_total: float, rtol=1e-6, in_range_only=False) -> None:
    """The stack integral must equal the expected yield (all in-range + under/overflow supplied by the caller) at the common exposure."""
    got = float(np.sum(stack["total"]))
    if not np.isclose(got, expected_total, rtol=rtol):
        raise AssertionError(f"stack integral {got} != expected yield {expected_total}")
