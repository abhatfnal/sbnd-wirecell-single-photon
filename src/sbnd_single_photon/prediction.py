"""Formal signal + background prediction object (S_NCDELTA, B_BNB_NEUTRINO, B_COSMIC, DATA). Refuses what is not yet knowable; NEVER substitutes zero.

Status of each component today:
  S_NCDELTA        truth production rate known; reconstruction efficiency PENDING the official Wire-Cell sample
  B_BNB_NEUTRINO   known: selected NON-signal BNB CV events (the natural NC Delta signal-like events are NOT in it); stat. uncertainty only
  B_COSMIC         SHAPE known from beam-off; absolute SCALE UNRESOLVED (needs the beam-on gate count, see DATA_EXPOSURE_NORMALIZATION.md)
  DATA             open beam-on raw counts and exposure known; no comparison is made until B_COSMIC is normalised
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

CHANNELS = ("1g0p", "1g1p", "ge2p")


class UnresolvedNormalizationError(RuntimeError):
    """Raised instead of returning a number that would silently assume an unresolved component is zero."""


@dataclass
class Component:
    name: str
    status: str                                   # "known" | "pending" | "unresolved"
    values: Optional[dict] = None                 # channel -> expectation (at the stated exposure)
    stat_unc: Optional[dict] = None
    shape_counts: Optional[dict] = None           # raw shape-only counts (B_COSMIC)
    note: str = ""

    def require_known(self, what: str):
        if self.status != "known" or self.values is None:
            raise UnresolvedNormalizationError(f"{what}: component {self.name} is {self.status.upper()} ({self.note or 'no normalisation'}); refusing to proceed")
        return self.values


@dataclass
class Prediction:
    exposure_pot: float
    S_NCDELTA: Component
    B_BNB_NEUTRINO: Component
    B_COSMIC: Component
    DATA: Component
    region: str = "unspecified"

    def _need_all(self, what: str):
        s = self.S_NCDELTA.require_known(what); b = self.B_BNB_NEUTRINO.require_known(what); c = self.B_COSMIC.require_known(what)
        return s, b, c

    def total_background(self) -> dict:
        _, b, c = self._need_all("total predicted background")
        return {ch: b[ch] + c[ch] for ch in CHANNELS}

    def purity(self) -> dict:
        s, b, c = self._need_all("purity")
        return {ch: s[ch] / (s[ch] + b[ch] + c[ch]) for ch in CHANNELS}

    def s_over_b(self) -> dict:
        s, b, c = self._need_all("S/B")
        return {ch: s[ch] / (b[ch] + c[ch]) for ch in CHANNELS}

    def significance(self) -> dict:
        s, b, c = self._need_all("significance")
        return {ch: s[ch] / np.sqrt(b[ch] + c[ch]) if b[ch] + c[ch] > 0 else float("inf") for ch in CHANNELS}      # simple s/sqrt(b): a diagnostic, not a result

    def status_table(self) -> dict:
        return {c.name: dict(status=c.status, note=c.note) for c in (self.S_NCDELTA, self.B_BNB_NEUTRINO, self.B_COSMIC, self.DATA)}


def bnb_background_component(selected_events, pot_cv: float, exposure_pot: float, *, channel_col="reco_channel", class_col="event_class",
                             exclude_class="signal_like") -> Component:
    """B_BNB_NEUTRINO from the selected BNB CV events with the natural signal-like events REMOVED (they are signal, not background).

    ``selected_events``: one row per selected event (the validated Phase-4 table). Rate = N / pot_cv; the expectation at ``exposure_pot`` is rate * exposure."""
    d = selected_events[selected_events[class_col] != exclude_class]
    if (d[class_col] == "mixed").any():
        raise ValueError("mixed events are not background nor signal: classify them first")
    counts = {ch: int((d[channel_col] == ch).sum()) for ch in CHANNELS}
    scale = exposure_pot / pot_cv
    return Component("B_BNB_NEUTRINO", "known", {ch: counts[ch] * scale for ch in CHANNELS}, {ch: np.sqrt(counts[ch]) * scale for ch in CHANNELS},
                     note=f"selected non-signal CV events (counts {counts}); POT_CV {pot_cv:.6g}; statistical only; no cosmic-only component; "
                          "natural signal-like events excluded")


def pending_signal(rate_known: Optional[dict] = None) -> Component:
    return Component("S_NCDELTA", "pending", None, None, note="truth rate known; reconstruction efficiency pending the official Wire-Cell sample"
                     + (f"; truth rates {rate_known}" if rate_known else ""))


def cosmic_shape_only(beam_off_counts: dict) -> Component:
    return Component("B_COSMIC", "unresolved", None, None, shape_counts=dict(beam_off_counts),
                     note="beam-off SHAPE only; absolute scale unresolved (beam-on gate count / livetime not available)")


def open_data(counts: dict, pot: float) -> Component:
    return Component("DATA", "known", dict(counts), None, note=f"open beam-on raw counts at {pot:.6g} POT; not compared until B_COSMIC is normalised")
