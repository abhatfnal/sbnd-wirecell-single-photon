"""Signal-truth reader for NC Delta -> N gamma that needs ONLY ``recTree`` (no ``recTreeWireCell``).

It operates on any official flatCAF (e.g. the Gen2 ``EX_ncdeltarad`` reco2 flatCAF) and on the recTree of the merged CAFs.
Design rules (see docs/analysis/NCDELTA_GENERATOR_FILTER_AUDIT.md and TRUTH_PROTON_DEFINITION_AUDIT.md):

* The generator filter (sbncode ``NCDeltaRadiative``) tests the GENIE record: an exiting status-1 photon whose mother is a
  Delta0 (2114) / Delta+ (2214), directly or through an in-nucleus photon. The CAF does NOT store that mother
  (``rec.mc.nu.prim`` holds only the Geant4 primaries; ``prim.gstatus`` is -1 and ``prim.parent`` a sentinel;
  there is no ``prefsi`` collection). Therefore the CAF cannot re-derive the process exactly. The reader therefore keeps three
  things apart and never invents the rest:

  - ``is_ncdelta_radiative`` : tri-state int8. ``1`` ONLY when the caller declares that the file is the output stream of the
    rare-signal filter (``from_filter_stream=True``): then the event passed the filter by construction. ``-1`` = unknown.
    It is never ``0``: a CAF that is not a filter stream cannot prove an event is NOT signal.
  - ``is_ncdelta_rad_proxy`` : a CAF-only PROXY (NC, GENIE resonant mode, resnum == Delta(1232), >= 1 primary photon above
    ``photon_proxy_mev``). It is a diagnostic, not the process definition; on the filtered stream the fraction of stream
    events it recovers measures its efficiency (``proxy_recovers_stream``).
  - ``delta_pdg``, ``delta_charge``, ``decay_nucleon_pdg`` : NOT AVAILABLE from the CAF -> 0 (0 is not a PDG code) and listed in
    :data:`UNAVAILABLE_FROM_CAF`; never filled by guessing.

* Truth proton category: GENIE-handoff primaries (``rec.mc.nu.prim``, ``start_process == kG4primary``) of the signal neutrino with
  ``pdg == 2212`` and kinetic energy ``genE - m_p > threshold`` (strict, default 35 MeV, configurable, NOT optimised). ``genE`` is
  total energy in GeV (``startE`` is a -9999 sentinel for ~70 % of primaries and is not used). No containment requirement and
  no Geant4 secondaries (they are not in ``prim``).
"""
from __future__ import annotations

import awkward as ak
import numpy as np

from .truth import ActiveVolume

PROTON_MASS_GEV = 0.938272088
DEFAULT_PROTON_KE_MEV = 35.0
DEFAULT_PHOTON_PROXY_MEV = 20.0        # PROXY ONLY: above the few-MeV nuclear de-excitation lines seen in NC primaries
GENIE_MODE_RES = 1                     # simb::kResonant
GENIE_RES_P33_1232 = 0                 # genie::kP33_1232
FILTER_BOX = ActiveVolume(x=(-210.0, 210.0), y=(-210.0, 210.0), z=(-1.0, 510.0))   # hard-coded in NCDeltaRadiative (parent vertex); NOT an analysis FV
UNAVAILABLE_FROM_CAF = ("delta_pdg", "delta_charge", "decay_nucleon_pdg")
PROTON_CATEGORIES = ("0p", "1p", "ge2p")

TRUTH_BRANCHES = ["rec.mc.nu.pdg", "rec.mc.nu.isnc", "rec.mc.nu.iscc", "rec.mc.nu.genie_mode", "rec.mc.nu.resnum",
                  "rec.mc.nu.E", "rec.mc.nu.position.x", "rec.mc.nu.position.y", "rec.mc.nu.position.z",
                  "rec.mc.nu.nprim", "rec.mc.nu.prim.pdg", "rec.mc.nu.prim.genE"]


def _regroup(flat, nprim):
    """flat per-event primary column -> ``[event][nu][prim]`` using ``nprim`` ([event][nu])."""
    flat, nprim = ak.Array(flat), ak.Array(nprim)
    inner = ak.unflatten(ak.flatten(flat, axis=1), ak.flatten(nprim, axis=1))
    return ak.unflatten(inner, ak.num(nprim, axis=1))


def _fill(a, default):
    return ak.to_numpy(ak.fill_none(a, default))


def proton_category(n_protons) -> np.ndarray:
    """0/1/2 (2 = >=2) from a proton count; -1 stays -1 (no signal neutrino)."""
    n = np.asarray(n_protons)
    return np.where(n < 0, -1, np.minimum(n, 2)).astype(np.int8)


def signal_truth(pdg, isnc, genie_mode, resnum, enu_gev, x, y, z, prim_pdg, prim_gen_e_gev, nprim=None, *,
                 from_filter_stream: bool = False, proton_ke_mev: float = DEFAULT_PROTON_KE_MEV,
                 photon_proxy_mev: float = DEFAULT_PHOTON_PROXY_MEV, av: ActiveVolume = ActiveVolume()) -> dict:
    """Per-event numpy fields. Neutrino-level inputs are ``[event][nu]``; ``prim_*`` are either ``[event][nu][prim]``
    or flat per event together with ``nprim`` (as stored in the CAF).

    The 'signal neutrino' of an event is the first neutrino that satisfies the PROXY (see module docstring). Events with
    no such neutrino get ``signal_nu_index = -1`` and all dependent fields NaN / -1 (also when ``from_filter_stream`` is
    set: the failure of the proxy on a filter-passing event is information, not something to hide)."""
    pdg, isnc, mode, resnum, enu, x, y, z = (ak.Array(a) for a in (pdg, isnc, genie_mode, resnum, enu_gev, x, y, z))
    if nprim is not None:
        prim_pdg, prim_gen_e_gev = _regroup(prim_pdg, nprim), _regroup(prim_gen_e_gev, nprim)
    prim_pdg, prim_e = ak.Array(prim_pdg), ak.Array(prim_gen_e_gev)

    is_ph = prim_pdg == 22
    ph_e_mev = prim_e * 1000.0
    n_ph_hard = ak.sum(is_ph & (ph_e_mev > photon_proxy_mev), axis=-1)
    n_ph = ak.sum(is_ph, axis=-1)
    max_ph = ak.max(ph_e_mev[is_ph], axis=-1)                                   # None when no photon
    ke_mev = (prim_e - PROTON_MASS_GEV) * 1000.0
    n_p = ak.sum((prim_pdg == 2212) & (ke_mev > proton_ke_mev), axis=-1)
    n_p_all = ak.sum(prim_pdg == 2212, axis=-1)
    n_pi0 = ak.sum(prim_pdg == 111, axis=-1)
    n_pic = ak.sum(np.abs(prim_pdg) == 211, axis=-1)
    n_n = ak.sum(prim_pdg == 2112, axis=-1)

    proxy = (isnc == 1) & (mode == GENIE_MODE_RES) & (resnum == GENIE_RES_P33_1232) & (n_ph_hard >= 1)
    proxy = ak.fill_none(proxy, False)
    n_cand = ak.to_numpy(ak.sum(proxy, axis=1))
    found = n_cand > 0
    nev = len(found)
    pick = ak.argmax(ak.values_astype(proxy, np.int8), axis=1, keepdims=True)    # first True (or 0 when none)

    def sel(a, default):
        out = _fill(ak.firsts(a[pick], axis=1), default)
        return np.where(found, out, default)

    in_box = FILTER_BOX.contains(x, y, z)
    in_av = av.contains(x, y, z)
    nu_index = np.where(found, _fill(ak.firsts(pick, axis=1), -1), -1).astype(np.int32)
    n_p_sel = sel(n_p, -1).astype(np.int32)
    out = dict(
        is_ncdelta_radiative=np.full(nev, 1 if from_filter_stream else -1, dtype=np.int8),
        is_ncdelta_rad_proxy=found,
        proxy_recovers_stream=found if from_filter_stream else np.zeros(nev, dtype=bool),
        n_signal_nu_candidates=n_cand.astype(np.int16),
        signal_nu_index=nu_index,
        delta_pdg=np.zeros(nev, dtype=np.int32), delta_charge=np.zeros(nev, dtype=np.int8),
        decay_nucleon_pdg=np.zeros(nev, dtype=np.int32),
        photon_energy_mev=sel(max_ph, np.nan).astype(np.float64),
        n_primary_photons=sel(n_ph, -1).astype(np.int16),
        n_primary_photons_hard=sel(n_ph_hard, -1).astype(np.int16),
        n_true_protons=n_p_sel,                                         # KE > proton_ke_mev
        n_true_protons_all_ke=sel(n_p_all, -1).astype(np.int32),
        true_proton_category=proton_category(n_p_sel),
        n_primary_pi0=sel(n_pi0, -1).astype(np.int16), n_primary_pi_charged=sel(n_pic, -1).astype(np.int16),
        n_primary_neutrons=sel(n_n, -1).astype(np.int16),
        true_vertex_x=sel(x, np.nan).astype(np.float64), true_vertex_y=sel(y, np.nan).astype(np.float64),
        true_vertex_z=sel(z, np.nan).astype(np.float64),
        vtx_in_filter_box=sel(in_box, False).astype(bool), vtx_in_active_tpc=sel(in_av, False).astype(bool),
        neutrino_energy_gev=sel(enu, np.nan).astype(np.float64),
        genie_mode=sel(mode, -999).astype(np.int16), resnum=sel(resnum, -999).astype(np.int16),
        nu_pdg=sel(pdg, 0).astype(np.int32),
    )
    return out


def read_truth_arrays(path: str, start: int = 0, stop=None, *, tree: str = "recTree") -> dict:
    """Read the :data:`TRUTH_BRANCHES` of ``recTree`` with plain uproot (no Wire-Cell tree needed). ``path`` may be a root:// URL.
    Raises a clear error if a needed branch is missing instead of returning partial truth."""
    import uproot
    with uproot.open(path) as f:
        t = f[tree]
        have = set(t.keys())
        missing = [b for b in TRUTH_BRANCHES if b not in have]
        if missing:
            raise KeyError(f"{path}: recTree lacks truth branches {missing}")
        d = t.arrays(TRUTH_BRANCHES, entry_start=start, entry_stop=stop, library="ak", how=dict)
        ids = t.arrays(["rec.hdr.run", "rec.hdr.subrun", "rec.hdr.evt"], entry_start=start, entry_stop=stop, library="np")
        pot = float(f["TotalPOT"].values()[0]) if "TotalPOT" in f else float("nan")
        gen = float(f["TotalGenEvents"].values()[0]) if "TotalGenEvents" in f else float("nan")
    d["ids"] = dict(run=ids["rec.hdr.run"], subrun=ids["rec.hdr.subrun"], evt=ids["rec.hdr.evt"])
    d["TotalPOT"], d["TotalGenEvents"] = pot, gen
    return d


def signal_truth_from_arrays(d: dict, **kw) -> dict:
    """Convenience wrapper for the dict returned by :func:`read_truth_arrays`."""
    g = lambda n: d["rec.mc.nu." + n]
    return signal_truth(g("pdg"), g("isnc"), g("genie_mode"), g("resnum"), g("E"), g("position.x"), g("position.y"),
                        g("position.z"), d["rec.mc.nu.prim.pdg"], d["rec.mc.nu.prim.genE"], nprim=g("nprim"), **kw)
