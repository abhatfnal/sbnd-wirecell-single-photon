"""Common NC-Delta reconstructed observables: pure helpers (no I/O).

Characterisation only: nothing here changes a selection flag, threshold or policy.  Conventions
(`docs/analysis/NCDELTA_RECO_OBSERVABLE_SEMANTICS.md`): energies MeV, lengths cm, directions are unit vectors (x drift, y vertical, z beam), the reco photon direction is the `T_pf` shower
chord (start point -> farthest trajectory vertex), the reco proton direction is the `T_pf` track chord.
"""
from __future__ import annotations
import numpy as np, pandas as pd

M_PROTON_MEV = 938.27208816          # PDG 2022 proton mass [MeV] (hence also the PDG mass used for E_p = T_p + m_p)
M_NEUTRON_MEV = 939.56542052
PROTON_POLICIES = {                  # POLICY SENSITIVITIES, not alternative selections
    "baseline_35": dict(threshold_mev=35.0, exclude_included3=False),
    "35_excl_included3": dict(threshold_mev=35.0, exclude_included3=True),
    "50": dict(threshold_mev=50.0, exclude_included3=False),
}
MASS_STATUS = ("ok", "no_photon_row", "no_photon_direction", "no_proton_direction", "mass2_nonpositive", "not_1g1p")


def unit(v) -> np.ndarray:
    """Unit vector; NaN vector for a zero / non-finite input (never silently replaced)."""
    v = np.asarray(v, float)
    n = np.linalg.norm(v)
    return v / n if np.isfinite(n) and n > 0 else np.full(3, np.nan)


def cos_between(a, b) -> float:
    a = np.asarray(a, float); b = np.asarray(b, float)
    return float(np.clip(np.dot(a, b), -1.0, 1.0)) if np.isfinite(a).all() and np.isfinite(b).all() else np.nan


def delta_mass2(e_gamma_mev, ke_proton_mev, cos_gp, m_p_mev: float = M_PROTON_MEV):
    """M_Delta^2 [MeV^2] = m_p^2 + 2 E_gamma (E_p - p_p cos theta_gamma,p), E_p = T_p + m_p, p_p = sqrt(E_p^2 - m_p^2).  Vectorised; NaN when an input is NaN."""
    e_gamma = np.asarray(e_gamma_mev, float); ke = np.asarray(ke_proton_mev, float); c = np.asarray(cos_gp, float)
    ep = ke + m_p_mev; pp = np.sqrt(np.maximum(ep ** 2 - m_p_mev ** 2, 0.0))
    return m_p_mev ** 2 + 2.0 * e_gamma * (ep - pp * c)


def delta_mass(e_gamma_mev, ke_proton_mev, cos_gp, m_p_mev: float = M_PROTON_MEV):
    """(mass [MeV], valid) with the square root taken ONLY where M^2 > 0 (invalid entries are NaN, never clipped to zero)."""
    m2 = delta_mass2(e_gamma_mev, ke_proton_mev, cos_gp, m_p_mev)
    ok = np.isfinite(m2) & (m2 > 0)
    return np.where(ok, np.sqrt(np.where(ok, m2, 1.0)), np.nan), ok


def invariant_mass(p4_a, p4_b) -> float:
    """Invariant mass of two four-vectors (px, py, pz, E) in one common unit."""
    s = np.asarray(p4_a, float) + np.asarray(p4_b, float)
    return float(np.sqrt(max(s[3] ** 2 - s[0] ** 2 - s[1] ** 2 - s[2] ** 2, 0.0)))


def proton_rows(rows: pd.DataFrame, policy: dict) -> pd.DataFrame:
    """The reco proton rows of ONE candidate under a proton policy: type 2212, KE > threshold, optionally without ``kine_energy_included == 3`` rows."""
    m = (rows.kine_particle_type == 2212) & (rows.kine_energy_particle > policy["threshold_mev"])
    if policy["exclude_included3"]:
        m &= rows.kine_energy_included != 3
    return rows[m]


def leading_proton_row(prows: pd.DataFrame):
    """Deterministic choice: the highest reco-KE row; ties go to the lowest row index.  NEVER truth-selected.  ``None`` if there is no row."""
    if len(prows) == 0:
        return None
    return prows.sort_values(["kine_energy_particle", "row"], ascending=[False, True]).iloc[0]


def reco_channel(n_protons: int) -> str:
    return "1g0p" if n_protons == 0 else ("1g1p" if n_protons == 1 else "1gNp")


def select_photon_row(rows: pd.DataFrame, shw_sp_energy: float, filled: float):
    """The T_kine shower row of the selected single-photon shower: electron-typed shower row whose KE equals ``shw_sp_energy`` (0.1 %).  ``None`` if the shower is not filled or no row matches
    (``shw_sp_energy`` is `kine_best`/`kine_charge` of the same shower, so the equality is exact up to float32)."""
    if not (filled > 0):
        return None
    s = rows[(rows.kine_particle_is_shower == 1) & (rows.kine_particle_type == 11)]
    s = s[np.abs(s.kine_energy_particle - shw_sp_energy) <= 1e-3 * max(shw_sp_energy, 1e-9)]
    return None if len(s) == 0 else s.sort_values("row").iloc[0]


def pf_chord(pf: pd.DataFrame, row: int):
    """Start, end and unit direction of the non-pseudo ``T_pf`` node of T_kine row ``row`` (None if absent)."""
    n = pf[(pf.kine_index == row) & (pf.is_pseudo == 0)]
    if len(n) == 0:
        return None
    n = n.sort_values("depth").iloc[0]
    s = np.array([n.start_x, n.start_y, n.start_z], float); e = np.array([n.end_x, n.end_y, n.end_z], float)
    return s, e, unit(e - s), float(np.linalg.norm(e - s))


def orient_from_vertex(start, end, vertex):
    """Reco-only orientation rule (no truth): the chord is oriented away from the reco vertex, i.e. start is the endpoint nearer to ``vertex``."""
    start = np.asarray(start, float); end = np.asarray(end, float); v = np.asarray(vertex, float)
    if np.linalg.norm(end - v) < np.linalg.norm(start - v):
        start, end = end, start
    return start, end, unit(end - start)


def pair_class(photon_correct: bool, proton_origin: str, proton_truth_class: str, delta_pdg: int, origin_class: str) -> str:
    """Exclusive classification of the (reco photon, reco proton) pair of a 1gamma1p event.

    decay_pair             Delta+ event, photon is the signal photon, proton row is the post-FSI primary that descends from the Delta-decay proton (`origin_class == decay_proton`)
    fsi_or_other_primary   photon correct, proton row is a signal primary proton of another origin (FSI-created, ambiguous, not from the decay; also every Delta0 primary proton)
    secondary_proton       proton row is a Geant4 secondary proton of the signal interaction
    fake_or_other          proton row is not a signal proton (non-proton signal particle, other neutrino, cosmic, unmatched, ambiguous truth)
    photon_wrong           the selected shower is not the signal photon
    """
    if not photon_correct:
        return "photon_wrong"
    if proton_truth_class == "true_primary_signal_proton":
        return "decay_pair" if (delta_pdg == 2214 and origin_class == "decay_proton") else "fsi_or_other_primary"
    if proton_truth_class == "geant4_secondary_proton":
        return "secondary_proton"
    return "fake_or_other"


PAIR_CLASSES = ("decay_pair", "fsi_or_other_primary", "secondary_proton", "fake_or_other", "photon_wrong")


def resolution_stats(x) -> dict:
    """Median, 16/84 percentiles, half-width of the 68 % interval, mean, RMS and the fraction beyond 3 half-widths of a quantity (NaN-aware)."""
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) == 0:
        return dict(n=0, median=np.nan, p16=np.nan, p84=np.nan, half68=np.nan, mean=np.nan, rms=np.nan, tail3=np.nan)
    p16, med, p84 = np.percentile(x, [16, 50, 84]); h = (p84 - p16) / 2
    return dict(n=len(x), median=float(med), p16=float(p16), p84=float(p84), half68=float(h), mean=float(x.mean()), rms=float(np.sqrt(np.mean((x - x.mean()) ** 2))), tail3=float((np.abs(x - med) > 3 * h).mean()) if h > 0 else np.nan)
