"""PROVISIONAL reconstructed-proton categories (0p / 1p / >=2p).

Source: ``wc.T_kine`` per-particle rows (see docs/analysis/RECO_PROTON_DEFINITION_AUDIT.md):
  * ``kine_particle_type``   : PDG code of the row's particle (unsigned; 0 = unknown). Tracks come from the
                               segment's particle_info(), showers from the shower PDG. 2212 = proton.
  * ``kine_energy_particle`` : KINETIC energy in MeV (track rows: particle_info()->kinetic_energy()).
  * ``kine_energy_included`` : 1 = row counted in the reco-Enu sum; other values flag excluded/extra rows.
  * ``kine_particle_pool``   : which collection step produced the row.
This is the SAME rule the earlier 59-event study used (type == 2212 and KE > 35 MeV). The 35 MeV threshold is a
planning value, NOT a frozen analysis convention: it stays a parameter and must not be tuned.
"""
from __future__ import annotations

from typing import Optional

import awkward as ak
import numpy as np

PROTON_PDG = 2212
DEFAULT_THRESHOLD_MEV = 35.0
ZERO_P, ONE_P, GE2_P = 0, 1, 2
LABELS = ("0p", "1p", "ge2p")


def count_reco_protons(pdg, ke_mev, *, threshold_mev: float = DEFAULT_THRESHOLD_MEV,
                       included=None, require_included: bool = False):
    """Number of proton rows with KE > threshold, reduced over the LAST axis (particles).

    ``pdg`` and ``ke_mev`` must have identical structure (e.g. [event][candidate][particle]).
    ``require_included=True`` additionally demands ``kine_energy_included == 1`` (variant, not default).
    """
    pdg = ak.Array(pdg)
    ke = ak.Array(ke_mev)
    mask = (pdg == PROTON_PDG) & (ke > threshold_mev)
    if require_included:
        if included is None:
            raise ValueError("require_included=True needs the kine_energy_included array")
        mask = mask & (ak.Array(included) == 1)
    return ak.sum(mask, axis=-1)


def classify_counts(n) -> "np.ndarray | int":
    """Counts -> integer category code (0: 0p, 1: 1p, 2: >=2p). Works on scalars, numpy and awkward."""
    if isinstance(n, (int, np.integer)):
        return int(min(max(n, 0), 2))
    if isinstance(n, ak.Array):
        return ak.values_astype(ak.where(n >= 2, 2, ak.where(n >= 1, 1, 0)), np.int8)
    return np.clip(np.asarray(n), 0, 2).astype(np.int8)


def classify_reco_protons(pdg, ke_mev, threshold_mev: float = DEFAULT_THRESHOLD_MEV, *,
                          included=None, require_included: bool = False):
    """Integer category per candidate: ``0`` = 0p, ``1`` = 1p, ``2`` = >=2p (labels in :data:`LABELS`).

    Codes (not strings) are returned because awkward cannot broadcast strings; use
    ``LABELS[code]`` or :func:`label` for display.
    """
    n = count_reco_protons(pdg, ke_mev, threshold_mev=threshold_mev, included=included,
                           require_included=require_included)
    return classify_counts(n)


def label(code: int) -> str:
    return LABELS[int(code)]
