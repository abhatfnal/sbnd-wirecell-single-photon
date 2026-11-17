"""Single-photon truth classes of one true neutrino interaction, SBND mapping.

Source definitions:
  * signal: E. H. Yandel, PhD thesis, UC Santa Barbara 2024 (escholarship 6rq082dr), sec. 5.1.2 (printed p.121):
    exactly one true photon with true KE > 20 MeV and true shower start (first pair production) and end (last visible
    charge) more than 3 cm from the TPC walls, or exactly two true photons from the same source with < 20 deg opening
    angle together fitting those requirements; no electrons; no muon with KE > 100 MeV. Categories NC pi0 1g, NC Delta
    1g, NC other 1g, numu CC 1g, out-of-FV 1g (pp.121-122).
  * backgrounds: MicroBooNE wcp-uboone-bdt-eyandel @ 0100d4b6 inc/WCPLEEANA/cuts.h:2842-2856 (SP*Bkg flags), which use
    the thesis's grouping (pp.127-132): NC pi0 = not signal, NC, vertex in the 3 cm FV, truth_Npi0 > 0.

SBND mapping choices (A1-A7; recorded in the training spec, to be signed off):
  A1 a "true photon" is a pdg-22 T_truth_pf row of this neutrino whose parent is the interaction (parent_trackid == 0)
     or a primary meson / baryon that decays to photons (pi0, eta, eta', omega, Sigma0); photons from secondary
     interactions in argon do not count. Variant A1b (any photon whose parent is any pi0) is also reported.
  A2 shower START = the photon's end point (conversion) in T_truth_pf; shower END ("last visible charge") is not in the
     CAF and is NOT applied.
  A3 "no electrons" = no primary e+-; "no muons above 100 MeV" = no primary mu+- with KE > 100 MeV.
  A4 a candidate belongs to a neutrino when its T_match level-2 partner is that neutrino (MicroBooNE used
     match_completeness_energy > 0.1 truth_energyInside).
  A5 NC Delta 1g = NC, GENIE mode 1 (RES), and the counted photon is primary (MicroBooNE flag truth_NCDelta).
  A6 truth_Npi0 = number of primary pi0 (parent_trackid == 0). Variant: all pi0 of this neutrino.
  A7 FV = SBND TPC active volume (x +-201.3, y +-203.73, z 0-501 cm) shrunk by 3 cm ("Wire-Cell's 3 cm FV").
"""
import math

import numpy as np

ACTIVE = dict(x=(-201.3, 201.3), y=(-203.73, 203.73), z=(0.0, 501.0))
FV_MARGIN_CM = 3.0
PHOTON_KE_MIN_GEV = 0.020
OVERLAP_DEG = 20.0
MUON_KE_MAX_GEV = 0.100
PHOTON_PARENTS = (111, 221, 331, 223, 3212)   # pi0, eta, eta', omega, Sigma0 (A1)

SIGNAL_CATEGORIES = ('NCpi0_1g', 'NCDelta_1g', 'NCother_1g', 'numuCC_1g', 'outFV_1g', 'other_1g')
BACKGROUND_CATEGORIES = ('NCpi0Bkg', 'NCBkg', 'numuCCBkg', 'numuCCpi0Bkg', 'nueCCBkg', 'outFVBkg', 'otherBkg')


def in_fv3(x, y, z, margin=FV_MARGIN_CM):
    return (ACTIVE['x'][0] + margin <= x <= ACTIVE['x'][1] - margin and ACTIVE['y'][0] + margin <= y <= ACTIVE['y'][1] - margin
            and ACTIVE['z'][0] + margin <= z <= ACTIVE['z'][1] - margin)


def _angle_deg(a, b):
    na = math.sqrt(sum(c * c for c in a)); nb = math.sqrt(sum(c * c for c in b))
    if na == 0 or nb == 0:
        return float('nan')
    return math.degrees(math.acos(max(-1.0, min(1.0, sum(x * y for x, y in zip(a, b)) / (na * nb)))))


def _count_fitting(photons):
    """photons: [(parent_trackid, (px, py, pz))] of photons that fit the KE / start requirements.
    Two photons from the same parent with < 20 deg opening angle count as one (thesis sec. 5.1.2 clause 2)."""
    n = len(photons)
    if n == 2 and photons[0][0] == photons[1][0] and photons[0][0] != 0 and _angle_deg(photons[0][1], photons[1][1]) < OVERLAP_DEG:
        return 1, True
    return n, False


def classify(q, pf, nu):
    """Single-photon truth class of the neutrino in T_truth_nu row q.
    pf: this event's T_truth_pf arrays (nu_row, trackid, parent_trackid, pdg, KE, start_px/py/pz, end_x/y/z), or None
    when T_truth_pf is unreadable. nu: dict(ccnc, pdg, mode, vx, vy, vz) of that neutrino."""
    out = dict(sp_truth_ok=0, sp_vtx_in_fv3=int(in_fv3(nu['vx'], nu['vy'], nu['vz'])), sp_n_photon_fit=-1,
               sp_n_photon_fit_a1b=-1, sp_pair_merged=0, sp_photon_parent_pdg=0, sp_n_prim_pi0=-1, sp_n_pi0_all=-1,
               sp_n_prim_e=-1, sp_max_prim_mu_ke_mev=float('nan'), sp_signal=0, sp_signal_a1b=0, sp_category='',
               sp_bkg='', sp_shower_end_checked=0)
    if pf is None:
        return out
    row, pdg, par, tid = pf['nu_row'], pf['pdg'], pf['parent_trackid'], pf['trackid']
    sel = np.where(row == q)[0]
    by_tid = {int(tid[j]): j for j in sel}
    fit, fit_b = [], []
    n_e, mu_max = 0, 0.0
    for j in sel:
        p = int(pdg[j])
        if abs(p) == 11 and par[j] == 0:
            n_e += 1
        elif abs(p) == 13 and par[j] == 0:
            mu_max = max(mu_max, float(pf['KE'][j]))
        if p != 22:
            continue
        ke = float(pf['KE'][j])
        start_ok = in_fv3(float(pf['end_x'][j]), float(pf['end_y'][j]), float(pf['end_z'][j]))
        if ke <= PHOTON_KE_MIN_GEV or not start_ok:
            continue
        mom = (float(pf['start_px'][j]), float(pf['start_py'][j]), float(pf['start_pz'][j]))
        parent = int(par[j])
        pj = by_tid.get(parent)
        parent_pdg = 0 if parent == 0 else (int(pdg[pj]) if pj is not None else -1)
        parent_is_primary = parent != 0 and pj is not None and int(par[pj]) == 0
        if parent == 0 or (parent_is_primary and abs(parent_pdg) in PHOTON_PARENTS):
            fit.append((parent, mom, parent_pdg))
        if parent == 0 or abs(parent_pdg) == 111:
            fit_b.append((parent, mom, parent_pdg))
    n_fit, merged = _count_fitting([(a, m) for a, m, _ in fit])
    n_fit_b, _ = _count_fitting([(a, m) for a, m, _ in fit_b])
    n_prim_pi0 = int(sum(1 for j in sel if pdg[j] == 111 and par[j] == 0))
    n_pi0_all = int(sum(1 for j in sel if pdg[j] == 111))
    leptons_ok = n_e == 0 and mu_max <= MUON_KE_MAX_GEV
    signal = n_fit == 1 and leptons_ok
    out.update(sp_truth_ok=1, sp_n_photon_fit=n_fit, sp_n_photon_fit_a1b=n_fit_b, sp_pair_merged=int(merged),
               sp_photon_parent_pdg=(fit[0][2] if fit else 0), sp_n_prim_pi0=n_prim_pi0, sp_n_pi0_all=n_pi0_all,
               sp_n_prim_e=n_e, sp_max_prim_mu_ke_mev=1000.0 * mu_max, sp_signal=int(signal),
               sp_signal_a1b=int(n_fit_b == 1 and leptons_ok))
    nc = int(nu['ccnc']) == 1
    apdg = abs(int(nu['pdg']))
    infv = bool(out['sp_vtx_in_fv3'])
    if signal:
        if not infv:
            cat = 'outFV_1g'
        elif nc:
            ppdg = abs(fit[0][2])
            if ppdg == 111:
                cat = 'NCpi0_1g'
            elif int(nu.get('mode', -1)) == 1 and fit[0][0] == 0:
                cat = 'NCDelta_1g'
            else:
                cat = 'NCother_1g'
        elif apdg == 14:
            cat = 'numuCC_1g'
        else:
            cat = 'other_1g'
        out['sp_category'] = cat
    else:
        if not infv:
            bkg = 'outFVBkg'
        elif nc:
            bkg = 'NCpi0Bkg' if n_prim_pi0 > 0 else 'NCBkg'
        elif apdg == 14:
            bkg = 'numuCCpi0Bkg' if n_prim_pi0 > 0 else 'numuCCBkg'
        elif apdg == 12:
            bkg = 'nueCCBkg'
        else:
            bkg = 'otherBkg'
        out['sp_bkg'] = bkg
    return out
