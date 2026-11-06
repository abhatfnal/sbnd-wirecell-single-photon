"""First-pass truth categories for the BNB MC (background composition). NOT a signal definition.

Event-level, from the CAF's official truth ``rec.mc.nu.*`` (one entry per true neutrino of the event; the
generator also stores rock/dirt neutrinos, so most events have several entries).

Precedence (documented, not tuned):
  1. no true neutrino at all                         -> COSMIC_NO_NU   (extra category: cosmic-only event)
  2. no neutrino vertex inside the active volume     -> DIRT_NO_ACTIVE
  3. more than one neutrino vertex inside the AV     -> MULTI_ACTIVE
  4. exactly one active-volume neutrino, by its interaction:
       NC and n_pi0 >= 1 -> NC_PI0        CC and n_pi0 >= 1 -> CC_PI0   (n_pi0 = pi0 among the GENIE G4 primaries)
       nu_e / nu_ebar CC   -> NUE_CC        nu_mu / nu_mubar CC -> NUMU_CC
       other NC            -> OTHER_NC      other CC            -> OTHER_CC
       anything else       -> OTHER
pi0 categories take precedence over the flavour categories, so NUMU_CC / NUE_CC mean "no final-state pi0".

Known limitations (see the design note):
  * ``rec.mc.nu.isvtxcont`` is not filled (always 0) and ``rec.mc.nu.vtx.*`` is NaN in these CAFs, so
    "active volume" is a box test on ``rec.mc.nu.position`` with PROVISIONAL SBND TPC dimensions. This is NOT a
    fiducial volume; the SBND FV is a pending collaboration decision.
  * the pi0 count is computed from the GENIE primaries (``prim.pdg == 111``): the CAF field ``rec.mc.nu.npizero`` is
    always 0 in these files, so using it would silently turn every NC_PI0/CC_PI0 event into OTHER_NC/flavour categories.
  * The categories are per EVENT, not per reconstructed candidate; candidate-to-truth matching (``wc.T_match``)
    is a later step.
  * NC Delta -> N gamma signal is deliberately NOT defined here: it comes from the official Gen2 NC-Delta evaluation sample (official sample exists; its Wire-Cell merged-CAF production is pending).
"""
from __future__ import annotations

from dataclasses import dataclass

import awkward as ak
import numpy as np

CATEGORIES = ("NUMU_CC", "NUE_CC", "NC_PI0", "CC_PI0", "OTHER_NC", "OTHER_CC",
              "DIRT_NO_ACTIVE", "MULTI_ACTIVE", "COSMIC_NO_NU", "OTHER")
CODE = {name: i for i, name in enumerate(CATEGORIES)}


@dataclass(frozen=True)
class ActiveVolume:
    """Axis-aligned box in cm. PROVISIONAL nominal SBND TPC extent; confirm against the geometry."""
    x: tuple = (-200.0, 200.0)
    y: tuple = (-200.0, 200.0)
    z: tuple = (0.0, 500.0)

    def contains(self, x, y, z):
        return ((x > self.x[0]) & (x < self.x[1]) & (y > self.y[0]) & (y < self.y[1])
                & (z > self.z[0]) & (z < self.z[1]))


def _first_active(arr, inside, default=0):
    return ak.to_numpy(ak.fill_none(ak.firsts(arr[inside], axis=1), default))


def truth_summary(pdg, iscc, isnc, npizero, x, y, z, av: ActiveVolume = ActiveVolume()) -> dict:
    """Per-event numpy arrays behind the category: ``code``, ``n_nu``, ``n_act`` and the first active neutrino's
    ``a_pdg`` (|PDG|), ``a_cc``, ``a_nc``, ``a_pi0`` (npizero>=1) and position ``a_x/a_y/a_z`` (NaN if none).
    Inputs are ``[event][nu]`` jagged. ``npizero`` must be the number of final-state pi0 per neutrino: take it from the
    GENIE primaries (``rec.mc.nu.prim.pdg == 111``); the stored ``rec.mc.nu.npizero`` field is always 0 in these CAFs."""
    pdg, iscc, isnc, npizero = (ak.Array(a) for a in (pdg, iscc, isnc, npizero))
    x, y, z = (ak.Array(a) for a in (x, y, z))
    inside = av.contains(x, y, z)
    inside = ak.fill_none(inside, False)               # NaN positions compare False already
    n_nu = ak.to_numpy(ak.num(pdg, axis=1))
    n_act = ak.to_numpy(ak.sum(inside, axis=1))

    a_pdg = np.abs(_first_active(pdg, inside))
    a_cc = _first_active(iscc, inside) == 1
    a_nc = _first_active(isnc, inside) == 1
    a_pi0 = _first_active(npizero, inside) >= 1

    code = np.full(len(n_nu), CODE["OTHER"], dtype=np.int8)
    single = n_act == 1
    conds = [
        n_nu == 0,
        (n_nu > 0) & (n_act == 0),
        n_act > 1,
        single & a_nc & a_pi0,
        single & a_cc & a_pi0,
        single & a_cc & (a_pdg == 12),
        single & a_cc & (a_pdg == 14),
        single & a_nc,
        single & a_cc,
    ]
    choices = [CODE["COSMIC_NO_NU"], CODE["DIRT_NO_ACTIVE"], CODE["MULTI_ACTIVE"], CODE["NC_PI0"],
               CODE["CC_PI0"], CODE["NUE_CC"], CODE["NUMU_CC"], CODE["OTHER_NC"], CODE["OTHER_CC"]]
    return dict(code=np.select(conds, choices, default=code).astype(np.int8), n_nu=n_nu, n_act=n_act,
                a_pdg=a_pdg, a_cc=a_cc, a_nc=a_nc, a_pi0=a_pi0,
                a_x=_first_active(x, inside, np.nan), a_y=_first_active(y, inside, np.nan),
                a_z=_first_active(z, inside, np.nan))


def classify_events(pdg, iscc, isnc, npizero, x, y, z, av: ActiveVolume = ActiveVolume()) -> np.ndarray:
    """Per-event category code (index into :data:`CATEGORIES`). All inputs are ``[event][nu]`` jagged."""
    return truth_summary(pdg, iscc, isnc, npizero, x, y, z, av)["code"]


def category_names(codes) -> np.ndarray:
    return np.array(CATEGORIES)[np.asarray(codes, dtype=int)]
