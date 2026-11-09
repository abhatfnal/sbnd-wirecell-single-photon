"""Expected NC Delta -> N gamma yield plumbing: production rate (truth) x reconstruction efficiency (truth class -> reco channel migration).

NO final number is claimed: the migration counts come only from the future official Wire-Cell signal sample (or, for tests, the natural rehearsal).

    R_t(V)        = N_truth(V, t) / POT_signal                      truth-class production rate, t in {0p, 1p, >=2p}
    eps(t -> r)   = N_selected(V, t -> r) / N_truth(V, t)           selected AND reconstructed in reco channel r (r in {1g0p, 1g1p, >=2p})
    N(r; P)       = P * sum_t R_t(V) * eps(t -> r)  = (P / POT_signal) * sum_t N_selected(V, t -> r)

Truth class and reco channel are NOT the same variable (measured proton migration is large): never multiply truth-0p by reco-0p only. Uncertainty:
n_t is a fixed truth count; the selected counts of one truth class are multinomial over (r, not selected), giving
    Cov[N(r), N(r')] = (P/POT_signal)^2 * sum_t n_t * (delta_rr' eps_tr - eps_tr eps_tr')      (statistics of the signal sample only).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

TRUTH_CLASSES = ("0p", "1p", "ge2p")
RECO_CHANNELS = ("1g0p", "1g1p", "ge2p")


@dataclass(frozen=True)
class SignalEfficiencyInputs:
    region: str
    pot_signal: float                  # POT of the SAME units as n_truth (the exposure of the truth sample)
    n_truth: tuple                     # N_signal_truth(V, t) per truth class (0p, 1p, >=2p): events, wc.invalid and missing INCLUDED
    selected: tuple                    # selected[t][r]: events of truth class t selected and reconstructed in reco channel r
    policy: str = "any"

    def __post_init__(self):
        n = np.asarray(self.n_truth, float); k = np.asarray(self.selected, float)
        if n.shape != (3,) or k.shape != (3, 3):
            raise ValueError("n_truth must have 3 entries and selected must be 3x3 (truth class x reco channel)")
        if (k.sum(axis=1) > n + 1e-9).any():
            raise ValueError("more selected than truth events in a truth class: numerator and denominator are not the same set of events")
        if self.pot_signal <= 0:
            raise ValueError("pot_signal must be positive")

    @property
    def eps(self) -> np.ndarray:        # eps[t][r]
        n = np.asarray(self.n_truth, float)[:, None]
        return np.divide(np.asarray(self.selected, float), n, out=np.zeros((3, 3)), where=n > 0)

    @property
    def rate_per_pot(self) -> np.ndarray:    # R_t
        return np.asarray(self.n_truth, float) / self.pot_signal


def expected_yield(inp: SignalEfficiencyInputs, exposure_pot: float) -> dict:
    """Expected selected signal at ``exposure_pot`` in region V: total, per truth class, per reco channel (full migration), with covariance."""
    if exposure_pot < 0:
        raise ValueError("negative exposure")
    n = np.asarray(inp.n_truth, float); eps = inp.eps; R = inp.rate_per_pot
    by_truth_to_reco = exposure_pot * R[:, None] * eps                       # [t][r]
    by_reco = by_truth_to_reco.sum(axis=0)
    by_truth = by_truth_to_reco.sum(axis=1)
    scale = exposure_pot / inp.pot_signal
    cov = np.zeros((3, 3))
    for t in range(3):
        cov += scale ** 2 * n[t] * (np.diag(eps[t]) - np.outer(eps[t], eps[t]))
    var_tot = float(cov.sum())
    out = dict(region=inp.region, policy=inp.policy, exposure_pot=float(exposure_pot), pot_signal_sample=float(inp.pot_signal),
               total=float(by_reco.sum()), total_stat_unc=float(np.sqrt(max(var_tot, 0.0))),
               by_truth_class={c: float(v) for c, v in zip(TRUTH_CLASSES, by_truth)},
               by_reco_channel={c: float(v) for c, v in zip(RECO_CHANNELS, by_reco)},
               by_reco_channel_stat_unc={c: float(np.sqrt(max(cov[i, i], 0.0))) for i, c in enumerate(RECO_CHANNELS)},
               truth_to_reco={f"{TRUTH_CLASSES[t]}->{RECO_CHANNELS[r]}": float(by_truth_to_reco[t, r]) for t in range(3) for r in range(3)},
               covariance_reco=cov.tolist(), N_signal_truth_by_class={c: int(v) for c, v in zip(TRUTH_CLASSES, n)},
               R_signal_total_per_POT=float(R.sum()))
    # identities: the model is self-consistent
    assert abs(out["total"] - sum(out["by_reco_channel"].values())) < 1e-6 * max(1.0, out["total"])
    assert abs(out["total"] - scale * float(np.asarray(inp.selected, float).sum())) < 1e-6 * max(1.0, out["total"])
    return out


def naive_diagonal_yield(inp: SignalEfficiencyInputs, exposure_pot: float) -> list:
    """The WRONG shortcut (truth class t paired with reco channel t only), exposed so tests can show it differs from the migration calculation."""
    R = inp.rate_per_pot; eps = inp.eps
    return [float(exposure_pot * R[i] * eps[i, i]) for i in range(3)]


def inputs_from_event_table(tab, n_truth_by_class, pot_signal: float, region: str, *, policy_col: str = "pass_any", truth_col="truth_cat",
                            reco_col="reco_cat_any") -> SignalEfficiencyInputs:
    """Build the inputs from a per-event signal table of region V (columns truth class 0/1/2, a selected flag, reco channel 0/1/2 or -1).

    The truth denominators come from the MASTER table, never from this table (events lost in Wire-Cell stay in n_truth and fail the numerator)."""
    k = np.zeros((3, 3), int)
    sel = tab[tab[policy_col].astype(bool)]
    for t in range(3):
        for r in range(3):
            k[t, r] = int(((sel[truth_col] == t) & (sel[reco_col] == r)).sum())
    return SignalEfficiencyInputs(region, float(pot_signal), tuple(int(x) for x in n_truth_by_class), tuple(map(tuple, k.tolist())), policy_col)
