"""Two EXPLICIT scorer modes for the frozen MicroBooNE single-photon BDT chain (NO training; the XMLs and the four thresholds are unchanged).

``legacy_as_run``           what the Round-1 first look actually did: the bare TMVA response ``v = tanh(raw)`` is cut at the frozen numbers, and the
                            ncpi0 BDT sees the real ``kine_pio_flag``.
``legacy_source_faithful``  what MicroBooNE's ``bdt_convert`` does (source audit: docs/analysis/LEGACY_SINGLE_PHOTON_SCORER_SOURCE_AUDIT.md):
                            score = (float) log10((1+v)/(1-v)) for all four BDTs, ``kine_pio_flag = 0`` in the ncpi0 input (commit 47b1f0c).

``decompose`` modes (Task 6): ``A_old`` (as-run), ``B_score_only``, ``C_pio_only``, ``D_full`` = ``legacy_source_faithful``.
Nothing here reads a sample; it works on arrays of ``v`` and of ncpi0 inputs.
"""
from __future__ import annotations

import numpy as np

MODELS = ("numu", "other", "ncpi0", "nue")
FROZEN_THRESHOLDS = {"numu": 0.4, "other": 0.2, "ncpi0": -0.05, "nue": -1.0}      # unchanged, source numbers (cuts.h:8899-8906)
MODES = {"legacy_as_run": dict(log_odds=False, pio_flag="real"),
         "legacy_source_faithful": dict(log_odds=True, pio_flag="zero")}
CONFIGS = {"A_old": dict(log_odds=False, pio_flag="real"), "B_score_only": dict(log_odds=True, pio_flag="real"),
           "C_pio_only": dict(log_odds=False, pio_flag="zero"), "D_full": dict(log_odds=True, pio_flag="zero")}


def log_odds_score(v):
    """``float(TMath::Log10((1+v)/(1-v)))`` exactly as ``bdt.h:232-262``: no clamp, ``v=-1 -> -inf``, ``v=+1 -> +inf``; the result is stored as float32."""
    v = np.asarray(v, dtype=np.float64)
    with np.errstate(divide="ignore", invalid="ignore"):
        s = np.log10((1.0 + v) / (1.0 - v))
    return s.astype(np.float32)


def response_from_score(s):
    """Inverse: the TMVA response ``v`` that sits exactly at a log-odds score ``s`` (threshold translation, used in the audit table)."""
    s = np.asarray(s, dtype=np.float64)
    return (10.0 ** s - 1.0) / (10.0 ** s + 1.0)


def score(v, log_odds: bool):
    """The quantity the cut is applied to."""
    return log_odds_score(v) if log_odds else np.asarray(v, dtype=np.float64)


def passes(v, model: str, log_odds: bool, thresholds: dict | None = None):
    """``score > threshold`` with NaN failing. The float32 score is widened to double before comparing with the double literal, as in C++."""
    thr = (thresholds or FROZEN_THRESHOLDS)[model]
    s = np.asarray(score(v, log_odds), dtype=np.float64)
    with np.errstate(invalid="ignore"):
        return np.isfinite(s) & (s > thr) | (s == np.inf)


def ncpi0_input_matrix(X, var_names, pio_flag: str):
    """Copy of the ncpi0 input matrix with ``kine_pio_flag`` replaced as the mode says: ``real`` leaves it, ``zero`` sets it to 0 (``bdt_convert.cxx:3958``)."""
    if pio_flag not in ("real", "zero"):
        raise ValueError(pio_flag)
    X = np.array(X, dtype=np.float64, copy=True)
    if pio_flag == "zero":
        X[:, list(var_names).index("kine_pio_flag")] = 0.0
    return X
