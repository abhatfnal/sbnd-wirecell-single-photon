"""Helpers of the Phase-18 numu compact-shower audit.  Pure functions, no I/O.

DESCRIPTIVE ONLY: nothing here changes a threshold, a weight, a cut or a policy.  The compactness bins are fixed in advance (they are not scanned and not tuned to the outcome).
"""
from __future__ import annotations
import math
import numpy as np
import pandas as pd

# ---- pre-set coarse bins (declared before looking at the outcome; the Phase-12 pass-vs-fail medians were 5 segments and 21 cm)
SEG_EDGES = [0, 5, 11, 18, np.inf]                       # n shower segments (br3_1_n_shower_segments): <=4, 5-10, 11-17, >=18
SEG_LABELS = ["1-4", "5-10", "11-17", ">=18"]
LEN_EDGES = [0, 20, 40, 80, np.inf]                      # total shower length (cm) of the tagger shower
LEN_LABELS = ["<20", "20-40", "40-80", ">=80"]
COMPACT_LENGTH_CM = 20.0                                 # "compact" = total shower length below 20 cm (the lowest pre-set bin)
COMPACT_NSEG = 5                                         # "few-segment" = fewer than 5 shower segments (the lowest pre-set bin edge)

OBJECT_CLASS = {   # Phase-15 pid_class -> controlling photon object class of Phase 18
    "A clean electron shower": "clean e-shower",
    "G fragmented (Phase 9), mixed types": "fragmented",
    "C muon-like dominant object": "muon-like",
    "D pion-like dominant object": "pion-like",
    "E proton-like dominant object": "proton-like",
    "F electron-track / other track": "track (e-track / other)",
    "B electron shower, not usable by the single-photon stage": "e-shower not usable",
    "H no particle row": "no relevant photon row",
    "I no reconstructed charge": "no relevant photon row",
    "J charge outside candidates / other candidate": "no relevant photon row",
}
OBJECT_ORDER = ["clean e-shower", "fragmented", "muon-like", "pion-like", "proton-like", "track (e-track / other)", "e-shower not usable", "no relevant photon row"]


def wilson(k, n, z: float = 1.0):
    """Wilson score interval (default 68 %: z = 1).  Returns (p, lo, hi); NaNs for n == 0."""
    if n <= 0:
        return float("nan"), float("nan"), float("nan")
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(c - h, 0.0), min(c + h, 1.0)


def survival_table(df: pd.DataFrame, group_cols, flag: str = "survive") -> pd.DataFrame:
    """n, passes and Wilson-68 survival of ``flag`` per group (NaN is its own level)."""
    g = df.assign(_s=df[flag].astype(float)).groupby(list(group_cols), dropna=False, observed=True)["_s"].agg(["size", "sum"]).reset_index()
    g.columns = list(group_cols) + ["n", "n_pass"]
    w = [wilson(k, n) for k, n in zip(g.n_pass, g.n)]
    g["survival"] = [x[0] for x in w]; g["lo68"] = [x[1] for x in w]; g["hi68"] = [x[2] for x in w]
    return g


def bin_labels(x, edges, labels) -> pd.Series:
    """Left-closed bins; NaN stays NaN."""
    return pd.cut(pd.Series(x), bins=edges, labels=labels, right=False)


def compact_flag(length_total, n_seg) -> pd.Series:
    """Pre-set binary compactness: total shower length < 20 cm (fewer than 5 segments is reported separately, not combined)."""
    return pd.Series(np.asarray(length_total, float) < COMPACT_LENGTH_CM)


def object_class(pid_class) -> str:
    return OBJECT_CLASS.get(pid_class, "no relevant photon row")


def bernoulli_deviance(y, p) -> float:
    """-2 log-likelihood of 0/1 outcomes ``y`` under probabilities ``p`` (clipped away from 0 and 1)."""
    y = np.asarray(y, float); p = np.clip(np.asarray(p, float), 1e-9, 1 - 1e-9)
    return float(-2.0 * np.sum(y * np.log(p) + (1 - y) * np.log(1 - p)))


def grouped_deviance_table(df: pd.DataFrame, y: str, groups: dict) -> pd.DataFrame:
    """Descriptive association bookkeeping: logistic (unpenalised, one-hot of the binned columns) deviance explained by each GROUP of factors alone (McFadden pseudo-R2) and the loss when the group is dropped
    from the model of all groups.  Not a causal model."""
    from sklearn.linear_model import LogisticRegression
    yy = df[y].astype(float).values; p0 = np.full(len(df), yy.mean()); d0 = bernoulli_deviance(yy, p0)

    def fit(cols):
        if not cols:
            return d0
        X = pd.get_dummies(df[cols].astype(str), drop_first=True).astype(float).values
        m = LogisticRegression(penalty=None, max_iter=2000).fit(X, yy)
        return bernoulli_deviance(yy, m.predict_proba(X)[:, 1])

    allc = [c for cs in groups.values() for c in cs]; dfull = fit(allc); rows = []
    for g, cs in groups.items():
        dalone = fit(cs); dwo = fit([c for c in allc if c not in cs])
        rows.append(dict(group=g, columns="+".join(cs), pseudo_r2_alone=1 - dalone / d0, pseudo_r2_full=1 - dfull / d0, deviance_increase_if_dropped=dwo - dfull, share_of_full_deviance_drop=(dwo - dfull) / (d0 - dfull) if d0 > dfull else float("nan")))
    return pd.DataFrame(rows)


def auc(score, y) -> float:
    """Mann-Whitney AUC of ``score`` for y == 1 (ties count 1/2)."""
    s = np.asarray(score, float); y = np.asarray(y, bool); ok = np.isfinite(s); s = s[ok]; y = y[ok]
    n1 = y.sum(); n0 = (~y).sum()
    if n1 == 0 or n0 == 0:
        return float("nan")
    r = pd.Series(s).rank().values
    return float((r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))
