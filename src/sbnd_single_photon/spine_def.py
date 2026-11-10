"""SPINE / medulla NC-Delta truth-definition masks on the official Gen2 flatCAF truth (COMPARISON MODE; never replaces the repository's own signal definition).

Everything is a separate boolean mask (see docs/analysis/SPINE_SIGNAL_DEFINITION_SOURCE_AUDIT.md for the source of each rule):

* ``mc_category == 0`` of medulla (``vars::gOre::mc_category``) and the event cut ``ecuts::gOre::has_nc_delta_ng_interaction`` use EXACTLY the collection we have:
  ``rec.mc.nu.prim`` (``caf::SRTrueParticle``): isnc, a Delta-type ``resnum`` (0, 6, 7, 9, 12, 13, 14, 15), exactly ONE photon with E > 25 MeV, and every
  above-threshold primary is a photon or a nucleon (``mc_topology::only_photons_and_nucleons``). These are reproduced exactly.
* The true-interaction cuts of the signal tree (``fiducial_cut``, ``containment_cut``, ``neutrino2026_veto``) act on SPINE truth interactions / particles (clustered
  deposits, including secondaries), which are NOT in the flatCAF. They are reproduced only as clearly-labelled flatCAF-primary APPROXIMATIONS.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

M_E, M_MU, M_P, M_PIC = 0.51099895e-3, 0.1056583755, 0.938272088, 0.13957039      # GeV
DELTA_RESNUM = (0, 6, 7, 9, 12, 13, 14, 15)       # genie::EResonance Delta-type states used by medulla (P33_1232, S31_1620, D33_1700, P33_1600, P31_1910, P33_1920, F35_1905, F37_1950)
THRESH = dict(gamma=25.0, electron=25.0, muon=25.0, pion=25.0, proton=50.0)       # MeV (gORe_main.toml [parameters])
# explicit gOre fiducial thresholds (distance from the hard-coded detector walls) of gORe_main.toml / core_gOre.h
WALLS = dict(x=(-200.0, 200.0), y=(-200.0, 200.0), z=(0.0, 500.0))                 # GORE_WALL_* (core_gOre.h)
FID_DIST = dict(x=(20.0, 20.0), y=(20.0, 20.0), z=(10.0, 50.0))
FID_DIST_DOCSTRING = dict(x=(25.0, 25.0), y=(25.0, 25.0), z=(30.0, 50.0))        # margins quoted in the medulla ``cuts::fiducial_cut`` docstring (SPINE post-processor); conflicts with the technote -> sensitivity only                      # (low-side, high-side) cm: x,y 20; z upstream 10, downstream 50
# SPINE sbnd_v2-6 geometry (src/spine/geo/config/sbnd/sbnd_v2-6_geometry.yaml): tpc dimensions [201.4, 400.015, 501.315], centres x = -/+100.9, z = 250.5; module_ids [0, 0]
SPINE_BOX = dict(x=(-201.6, 201.6), y=(-200.0075, 200.0075), z=(-0.1575, 501.1575))
SPINE_MARGIN_CM = 5.0                                                              # "within 5 cm of the detector edges" (medulla cuts.h; ContainmentProcessor margin)
GDML_ACTIVE_BOX = dict(x=(-201.3, 201.3), y=(-203.7323, 203.7323), z=(0.0, 501.0))   # sbnd_v02_06.gdml boxTPCActive 2013 x 4074.645 x 5010 mm (two volumes meeting at x = 0)
NU_PDG = (12, 14, 16)


def fiducial(x, y, z, walls=WALLS, dist=FID_DIST) -> np.ndarray:
    """medulla ``mc_topo_particle::is_fiducial``: strict inequalities, wall - v > d_pos and v - wall > d_neg on each axis (|x|,|y| < 180, 10 < z < 450 for the defaults)."""
    x, y, z = (np.asarray(v, float) for v in (x, y, z))
    return ((walls["x"][1] - x > dist["x"][1]) & (x - walls["x"][0] > dist["x"][0]) & (walls["y"][1] - y > dist["y"][1]) & (y - walls["y"][0] > dist["y"][0])
            & (walls["z"][1] - z > dist["z"][1]) & (z - walls["z"][0] > dist["z"][0]))


def above_threshold(pdg: np.ndarray, gen_e_gev: np.ndarray, thr=THRESH) -> np.ndarray:
    """medulla ``mc_topo_particle::is_above_threshold`` (energies at generation): neutrinos never; photon E > gamma; e: E - m > gamma(25); mu: E - m > muon; proton: E - m > proton;
    charged pion: E - m > pion; EVERYTHING ELSE (neutrons, pi0, kaons, fragments, ...) counts as above threshold."""
    pdg = np.asarray(pdg); a = np.abs(pdg); e = np.asarray(gen_e_gev, float) * 1000.0
    out = np.ones(len(pdg), bool)
    out[np.isin(a, NU_PDG)] = False
    out = np.where(a == 22, e > thr["gamma"], out)
    out = np.where(a == 11, e - M_E * 1000 > thr["electron"], out)
    out = np.where(a == 13, e - M_MU * 1000 > thr["muon"], out)
    out = np.where(a == 2212, e - M_P * 1000 > thr["proton"], out)
    out = np.where(a == 211, e - M_PIC * 1000 > thr["pion"], out)
    return out


def counts(pdg, gen_e_gev, thr=THRESH) -> dict:
    """Per-event particle counts above the SPINE thresholds + the exact medulla ``only_photons_and_nucleons`` flag."""
    pdg = np.asarray(pdg); a = np.abs(pdg); e = np.asarray(gen_e_gev, float) * 1000.0
    ab = above_threshold(pdg, gen_e_gev, thr)
    return dict(n_gamma=int(((a == 22) & ab).sum()), n_electron=int(((a == 11) & ab).sum()), n_muon=int(((a == 13) & ab).sum()), n_charged_pion=int(((a == 211) & ab).sum()),
                n_proton=int(((a == 2212) & ab).sum()), n_pi0=int(((pdg == 111) & ab).sum()), n_neutron=int(((pdg == 2112) & ab).sum()),
                only_photons_and_nucleons=bool(all(p in (22, 2112, 2212) for p in pdg[ab])), n_other_species=int((~np.isin(pdg[ab], (22, 2112, 2212))).sum()))


def proton_count(pdg, gen_e_gev, threshold_mev: float) -> int:
    """Primary protons with kinetic energy (genE - m_p) strictly above ``threshold_mev``."""
    pdg = np.asarray(pdg); e = np.asarray(gen_e_gev, float) * 1000.0
    return int(((np.abs(pdg) == 2212) & (e - M_P * 1000 > threshold_mev)).sum())


def _inside(v, lo, hi, margin):
    v = np.asarray(v, float)
    return np.isfinite(v) & (v > lo + margin) & (v < hi - margin)


def containment_margin(pdg, sx, sy, sz, ex, ey, ez, vis, *, box=SPINE_BOX, margin=SPINE_MARGIN_CM, require_deposit=True, include_neutrons=False) -> bool:
    """flatCAF-primary APPROXIMATION of SPINE ``is_contained``: every considered primary has its start AND end point at least ``margin`` cm inside ``box`` (SPINE 'module' mode:
    the detector outer box, the cathode is not a boundary). Considered particles: non-neutrinos; by default only those with visible deposits (SPINE truth particles exist only
    where energy was deposited; neutrons normally have none) -- ``require_deposit=False, include_neutrons=True`` is the literal 'all final-state endpoints' variant.
    Points that are non-finite (sentinels) are treated as 'never entered the volume' and fail containment."""
    pdg = np.asarray(pdg); sel = ~np.isin(np.abs(pdg), NU_PDG)
    if require_deposit:
        sel &= np.asarray(vis, float) > 0
    if not include_neutrons:
        sel &= np.abs(pdg) != 2112
    for lo_hi, s, e in ((box["x"], sx, ex), (box["y"], sy, ey), (box["z"], sz, ez)):
        s, e = np.asarray(s, float)[sel], np.asarray(e, float)[sel]
        bad_s = np.where(s <= -9000, np.nan, s); bad_e = np.where(e <= -9000, np.nan, e)
        if not (_inside(bad_s, *lo_hi, margin).all() and _inside(bad_e, *lo_hi, margin).all()):
            return False
    return True


def containment_flag(pdg, gen_e_gev, contained, thr=THRESH) -> bool:
    """Zero-margin variant that mirrors ``mc_topology::is_contained`` (flatCAF ``contained`` flag of every above-threshold primary, neutrons included): NOT used by the signal tree."""
    ab = above_threshold(pdg, gen_e_gev, thr)
    return bool(np.asarray(contained)[ab].all()) if ab.any() else True


def neutrino2026_veto(vtx_x, pdg, sx, sy, sz, ex, ey, ez, vis, require_deposit=True) -> bool:
    """flatCAF-primary APPROXIMATION of medulla ``neutrino2026_veto`` (SBND): |vertex x| > 5 cm (cathode fiducialisation) AND no particle starts or ends in (x > 0, y > 100, z > 250)
    AND no particle crosses the cathode (start_x * end_x < 0). The real cut loops over all SPINE truth particles including secondaries."""
    if not abs(float(vtx_x)) > 5.0:
        return False
    pdg = np.asarray(pdg); sel = ~np.isin(np.abs(pdg), NU_PDG)
    if require_deposit:
        sel &= np.asarray(vis, float) > 0
    f = lambda v: np.where(np.asarray(v, float) <= -9000, np.nan, np.asarray(v, float))[sel]
    sx, sy, sz, ex, ey, ez = map(f, (sx, sy, sz, ex, ey, ez))
    with np.errstate(invalid="ignore"):
        highy = ((sy > 100) & (sz > 250) & (sx > 0)) | ((ey > 100) & (ez > 250) & (ex > 0))
        cross = np.isfinite(sx) & np.isfinite(ex) & (sx * ex < 0)
    return not (highy.any() or cross.any())


def genie_record_strict(row) -> bool:
    """LITERAL technote wording on the GENIE record: the stable final state (status 1) is exactly nucleons + neutrino(s) + ONE photon (no pions, leptons, other particles)."""
    return bool(row["g1_n_photon"] == 1 and row["g1_n_pi0"] == 0 and row["g1_n_pic"] == 0 and row["g1_n_lepton"] == 0 and row["g1_n_other"] == 0)


def build_flags(st: pd.DataFrame, thr=THRESH) -> pd.DataFrame:
    """Per-event flag table from the merged truth (list columns p_* of the spine truth scan + the signal master columns). Returns one row per event with the named masks."""
    rows = []
    for r in st.itertuples(index=False):
        c = counts(r.p_pdg, r.p_genE, thr)
        n_p35 = proton_count(r.p_pdg, r.p_genE, 35.0); n_p50 = proton_count(r.p_pdg, r.p_genE, 50.0)
        pk = np.sort(np.asarray(r.p_genE)[np.abs(np.asarray(r.p_pdg)) == 2212] * 1000.0 - M_P * 1000.0)[::-1]
        args = (r.p_pdg, r.p_sx, r.p_sy, r.p_sz, r.p_ex, r.p_ey, r.p_ez, r.p_vis)
        rows.append(dict(run=r.run, subrun=r.subrun, evt=r.evt, n_gamma25=c["n_gamma"], n_e25=c["n_electron"], n_mu25=c["n_muon"], n_pic25=c["n_charged_pion"], n_pi0_any=c["n_pi0"],
                         n_other_species=c["n_other_species"], only_phot_nuc=c["only_photons_and_nucleons"], n_p35_prim=n_p35, n_p50=n_p50,
                         lead_p_ke=float(pk[0]) if len(pk) else np.nan, sub_p_ke=float(pk[1]) if len(pk) > 1 else np.nan, n_p_all=int(len(pk)),
                         cont_main=containment_margin(*args), cont_literal=containment_margin(*args, require_deposit=False, include_neutrons=True),
                         cont_gdml=containment_margin(*args, box=GDML_ACTIVE_BOX), cont_flag=containment_flag(r.p_pdg, r.p_genE, r.p_contained, thr),
                         veto2026=neutrino2026_veto(r.vtx_x, *args)))
    return pd.DataFrame(rows)


def masks(tab: pd.DataFrame) -> pd.DataFrame:
    """Named boolean masks from the merged per-event table (master columns + flags). Returns a copy with the mask columns added; ``tab`` must have vtx_x/y/z, nu_isnc, nu_resnum,
    delta_pdg and the build_flags columns plus the g1_* GENIE counts."""
    t = tab.copy()
    t["nc_delta_ancestry"] = t.delta_pdg.isin([2114, 2214]) & (t.nu_isnc == 1)
    t["spine_resnum_1232"] = t.nu_resnum == 0
    t["spine_resnum_delta"] = t.nu_resnum.isin(DELTA_RESNUM)
    t["spine_fv"] = fiducial(t.vtx_x, t.vtx_y, t.vtx_z)
    t["spine_fv_docstring"] = fiducial(t.vtx_x, t.vtx_y, t.vtx_z, dist=FID_DIST_DOCSTRING)
    t["spine_containment"] = t.cont_main
    t["spine_one_photon_25"] = t.n_gamma25 == 1
    t["spine_no_e_25"] = t.n_e25 == 0
    t["spine_no_mu_25"] = t.n_mu25 == 0
    t["spine_no_charged_pi_25"] = t.n_pic25 == 0
    t["spine_genie_final_state"] = t.only_phot_nuc                     # SOURCE implementation (above-threshold primaries only photons/nucleons)
    t["spine_genie_record_strict"] = (t.g1_n_photon == 1) & (t.g1_n_pi0 == 0) & (t.g1_n_pic == 0) & (t.g1_n_lepton == 0) & (t.g1_n_other == 0)
    thr_topology = t.spine_one_photon_25 & t.spine_no_e_25 & t.spine_no_mu_25 & t.spine_no_charged_pi_25
    t["spine_technote_threshold"] = t.nc_delta_ancestry & t.spine_fv & t.spine_containment & thr_topology
    t["spine_technote_strict"] = t.spine_technote_threshold & t.spine_genie_final_state
    t["spine_technote_strict_record"] = t.spine_technote_threshold & t.spine_genie_record_strict
    t["spine_source_signal"] = t.nc_delta_ancestry & t.spine_resnum_delta & t.spine_fv & t.spine_containment & thr_topology & t.spine_genie_final_state
    t["spine_source_signal_veto2026"] = t.spine_source_signal & t.veto2026
    t["spine_truth_signal"] = t.spine_technote_strict            # HEADLINE harmonized signal (technote text + the exact medulla topology rule; Delta identified by ancestry)
    t["spine_truth_0p50"] = t.spine_truth_signal & (t.n_p50 == 0)
    t["spine_truth_Np50"] = t.spine_truth_signal & (t.n_p50 >= 1)
    return t


# ---------------------------------------------------------------------------------------------------------------- ladder / projections / cross-tabs (pure, tested)
def denominator_ladder(t: pd.DataFrame) -> pd.DataFrame:
    """Cumulative ladder from all official signal, every requirement on its own (overlapping losses visible) and the named ambiguity variants. ``t`` = masks() output (+ truth35, n_p50)."""
    steps = [("all official signal (filter box)", np.ones(len(t), bool)), ("+ NC Delta ancestry (nc_delta_ancestry)", t.nc_delta_ancestry), ("+ SPINE FV", t.spine_fv),
             ("+ containment (flatCAF-primary 5 cm approximation)", t.spine_containment), ("+ exactly one photon > 25 MeV", t.spine_one_photon_25),
             ("+ no e / mu / charged pi > 25 MeV", t.spine_no_e_25 & t.spine_no_mu_25 & t.spine_no_charged_pi_25),
             ("+ above-threshold primaries only photons/nucleons (medulla only_photons_and_nucleons) = spine_technote_strict", t.spine_genie_final_state),
             ("+ Delta-type resnum (source extra) = spine_source_signal", t.spine_resnum_delta), ("+ neutrino2026 veto (source extra, approximate) = spine_source_signal_veto2026", t.veto2026)]
    cum = np.ones(len(t), bool); rows = []; n0 = len(t)
    for name, m in steps:
        cum = cum & np.asarray(m, bool)
        rows.append(dict(step=name, kind="cumulative", n=int(cum.sum()), fraction=cum.mean(), n_0p50=int((cum & (t.n_p50 == 0)).sum()), n_Np50=int((cum & (t.n_p50 >= 1)).sum()),
                         n_Delta0=int((cum & (t.delta_pdg == 2114)).sum()), n_DeltaPlus=int((cum & (t.delta_pdg == 2214)).sum()), n_truth35_0p=int((cum & (t.truth35 == 0)).sum()),
                         n_truth35_1p=int((cum & (t.truth35 == 1)).sum()), n_truth35_ge2p=int((cum & (t.truth35 == 2)).sum())))
    ind = [("SPINE FV alone", t.spine_fv), ("SPINE FV with the margins of the medulla fiducial_cut docstring (25/25/30/50 cm) alone", t.spine_fv_docstring), ("containment alone (main approximation)", t.spine_containment), ("containment alone (literal: all non-nu primaries incl. neutrons)", t.cont_literal),
           ("containment alone (GDML active box instead of SPINE box)", t.cont_gdml), ("containment alone (flatCAF contained flag, zero margin, above-threshold primaries)", t.cont_flag),
           ("exactly one photon > 25 MeV alone", t.spine_one_photon_25), ("no electron > 25 MeV alone", t.spine_no_e_25), ("no muon > 25 MeV alone", t.spine_no_mu_25),
           ("no charged pion > 25 MeV alone", t.spine_no_charged_pi_25), ("only photons+nucleons above threshold (source) alone", t.spine_genie_final_state),
           ("GENIE record stable final state = nucleons + nu + ONE photon (literal) alone", t.spine_genie_record_strict), ("resnum == 0 alone", t.spine_resnum_1232),
           ("resnum in Delta-type set alone", t.spine_resnum_delta), ("neutrino2026 veto alone (approx)", t.veto2026), ("TPC box (current working region) alone", t.tpc_box)]
    for name, m in ind:
        m = np.asarray(m, bool)
        rows.append(dict(step=name, kind="independent", n=int(m.sum()), fraction=m.mean(), n_0p50=int((m & (t.n_p50 == 0)).sum()), n_Np50=int((m & (t.n_p50 >= 1)).sum()),
                         n_Delta0=int((m & (t.delta_pdg == 2114)).sum()), n_DeltaPlus=int((m & (t.delta_pdg == 2214)).sum()), n_truth35_0p=int((m & (t.truth35 == 0)).sum()),
                         n_truth35_1p=int((m & (t.truth35 == 1)).sum()), n_truth35_ge2p=int((m & (t.truth35 == 2)).sum())))
    # the ambiguity variants named in the task
    for name, m in (("A spine_technote_threshold (no GENIE-final-state requirement)", t.spine_technote_threshold), ("B spine_technote_strict (source rule: only photons/nucleons above threshold)", t.spine_technote_strict),
                    ("B' spine_technote_strict_record (literal GENIE stable final state)", t.spine_technote_strict_record), ("spine_source_signal", t.spine_source_signal), ("spine_source_signal_veto2026", t.spine_source_signal_veto2026)):
        m = np.asarray(m, bool)
        rows.append(dict(step=name, kind="variant", n=int(m.sum()), fraction=m.mean(), n_0p50=int((m & (t.n_p50 == 0)).sum()), n_Np50=int((m & (t.n_p50 >= 1)).sum()), n_Delta0=int((m & (t.delta_pdg == 2114)).sum()),
                         n_DeltaPlus=int((m & (t.delta_pdg == 2214)).sum()), n_truth35_0p=int((m & (t.truth35 == 0)).sum()), n_truth35_1p=int((m & (t.truth35 == 1)).sum()), n_truth35_ge2p=int((m & (t.truth35 == 2)).sum())))
    return pd.DataFrame(rows)




def reco50_category(lead_proton_ke_mev, selected) -> np.ndarray:
    """SPINE-comparison reco projection (NOT a new selection): for events that have a selected / matched candidate, reco Np50 if the candidate's leading reco proton row has KE > 50 MeV
    (baseline row convention: every proton row counts, included flag ignored; the stored leading KE is already restricted to rows above 35 MeV), else 0p50; 'none' without a candidate."""
    ke = np.asarray(lead_proton_ke_mev, float); sel = np.asarray(selected, bool)
    return np.where(sel, np.where(ke > 50.0, "Np50", "0p50"), "none")


def crosstab_35_50(truth35, n_p50, mask=None) -> pd.DataFrame:
    """Rows: 35-MeV truth class (0p, 1p, >=2p); columns: 0p50 / Np50. Totals always equal the number of events in ``mask``."""
    t35 = np.asarray(truth35); n50 = np.minimum(np.asarray(n_p50), 1)
    m = np.ones(len(t35), bool) if mask is None else np.asarray(mask, bool)
    x = np.zeros((3, 2), int)
    for i in range(3):
        for j in range(2):
            x[i, j] = int((m & (t35 == i) & (n50 == j)).sum())
    return pd.DataFrame(x, index=["35: 0p", "35: 1p", "35: >=2p"], columns=["50: 0p50", "50: Np50"])


def migration_50(n_p50, mask, reco_cat) -> pd.DataFrame:
    """Truth (0p50 / Np50) x reco (0p50 / Np50 / none) counts; row totals equal the truth counts of ``mask``."""
    n50 = np.asarray(n_p50); m = np.asarray(mask, bool); r = np.asarray(reco_cat)
    rows = {}
    for nm, tm in (("truth 0p50", n50 == 0), ("truth Np50", n50 >= 1)):
        rows[nm] = [int((m & tm & (r == c)).sum()) for c in ("0p50", "Np50", "none")]
    return pd.DataFrame(rows, index=["reco 0p50", "reco Np50", "no selected/matched candidate"]).T
