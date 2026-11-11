"""Wire-Cell particle typing: source-rule helpers, truth/reco type taxonomies and proton bookkeeping (Phase 15).  Pure functions, no I/O.

DESCRIPTIVE ONLY: nothing here changes a cut, a threshold, the PID or a reconstructed type.

The SOURCE_RULES table records the decisions read in ``HaiwangYu/wire-cell-toolkit`` commit ``4b6853d4`` (``git show 4b6853d4:<path>``); the small predicate functions re-state the decision logic so that
it can be unit-tested and compared with the persisted ``T_segment`` / ``T_kine`` products.  ``dQ/dx`` vectors, template scores (``particle_score``), ``start_n`` / ``end_n`` and ``dirsign`` before the
final stage are NOT all persisted: see ``NOT_PERSISTED``.
"""
from __future__ import annotations
import numpy as np

SOURCE_COMMIT = "4b6853d4"
MIP_FALLBACK = dict(proton_above=1.75, muon_below=1.2, muon_short_below=1.5, short_len_cm=4.0)          # PRSegmentFunctions.cxx:3053-3061 (median dQ/dx over MIP, only if the template PID returned pdg 0)
ELECTRON_TEMPLATE_MAX_LEN_CM = 20.0                                                                     # PRSegmentFunctions.cxx:2743 / 2755: the electron template competes only for segments shorter than 20 cm
BAD_SCORE_SHOWER = dict(min_len_cm=10.0, min_score=1.0, max_score=100.0)                                # PRSegmentFunctions.cxx:3096: length > 10 cm and 1 < score < 100 -> pdg 11, dirsign 0
VERTEX_ACTIVITY_MAX_LEN_CM = 1.5                                                                        # PRSegmentFunctions.cxx:3077-3093: length < 1.5 cm at a vertex with another >= 3 segments: 2212 (> 1.75 MIP) or 211 (< 1.2 MIP)
TEMPLATE_RANGES_CM = (35.0, 15.0)                                                                       # compare ranges tried in order (PRSegmentFunctions.cxx:2987-3015)
TWO_VERTEX_END_MIN_POINTS = 15                                                                          # start_n == 1 && end_n == 1 && npoints >= 15: forced decision (flag_force = true)

SOURCE_RULES = [
    dict(step=1, stage="track vs shower", what="segment flagged shower trajectory (segment_is_shower_trajectory) or shower topology (segment_is_shower_topology)", where="PRSegmentFunctions.cxx:2219, 4126; NeutrinoTrackShowerSep.cxx:210-238",
         inputs="fit-point geometry, associated-point cloud RMS, median dQ/dx / MIP per 10 cm section, straightness, length (trajectory only <= 50 cm)", persisted="T_segment.flag_shower, length_cm, n_fit (not the RMS / dQ/dx)"),
    dict(step=2, stage="PDG of a track segment", what="dQ/dx-template competition (segment_do_track_pid): forward and backward KS-like score against muon, proton (and electron if length < 20 cm) templates, constant MIP; muon is the default",
         where="PRSegmentFunctions.cxx:2582-2887", inputs="dQ/dx vector along the segment (internal units), compare range 35 then 15 cm, segment length, start_n / end_n (vertex degrees), npoints", persisted="T_segment.pdg (live, final), length_cm, n_fit; NOT the dQ/dx vector, the template scores or particle_score"),
    dict(step=3, stage="PDG fallback", what="if the template PID returned 0: median dQ/dx > 1.75 MIP -> proton; < 1.2 MIP -> muon; < 1.5 MIP and length < 4 cm -> muon", where="PRSegmentFunctions.cxx:3053-3061", inputs="median dQ/dx / MIP, length", persisted="not the median dQ/dx"),
    dict(step=4, stage="short-segment vertex activity", what="length < 1.5 cm and one end free: with the other end of degree > 2: proton (median > 1.75 MIP) or PION (median < 1.2 MIP), dirsign set toward the free end", where="PRSegmentFunctions.cxx:3077-3093", inputs="length, vertex degrees, median dQ/dx", persisted="length_cm, T_segment vertex ids (degrees derivable)"),
    dict(step=5, stage="bad template score -> shower", what="length > 10 cm and 1.0 < particle_score < 100 -> pdg 11 (electron), score 200, dirsign 0", where="PRSegmentFunctions.cxx:3096-3100", inputs="particle_score, length", persisted="length_cm; NOT particle_score"),
    dict(step=6, stage="electron weak-direction rule", what="an electron-typed track with both ends occupied (start_n > 1 and end_n > 1), or a direction pointing into an occupied end, gets dir_weak and dirsign 0; if score < 0.15 the type becomes MUON", where="PRSegmentFunctions.cxx:3064-3071", inputs="start_n, end_n, dirsign, score", persisted="dirsign (final)"),
    dict(step=7, stage="shower segments", what="a shower-topology segment gets pdg 11 unconditionally; a shower-trajectory segment is forced to pdg 11 unless the track PID is electron", where="NeutrinoTrackShowerSep.cxx:296-322; PRSegmentFunctions.cxx:3195-3242", inputs="segment flags", persisted="T_segment.flag_shower, pdg"),
    dict(step=8, stage="main-vertex muon / pion arbitration", what="among the pdg-13 segments at the main vertex only the LONGEST whose far end has no proton neighbour stays muon; EVERY OTHER pdg-13 segment at that vertex is re-typed pion (211)", where="NeutrinoVertexFinder.cxx:1956-2102",
         inputs="segment length, far-vertex neighbours' pdg, segments_in_long_muon", persisted="T_segment.pdg, length_cm, vertex ids"),
    dict(step=9, stage="proton-neighbour re-typing", what="a pdg-0 segment whose far vertex carries a proton: median dQ/dx / MIP > 1.3 -> proton, else pion; a proton-typed segment with an electron-like in-shower daughter is re-examined (ratio 1.3 / 1.4)", where="NeutrinoVertexFinder.cxx:1820-1862, 2038-2066", inputs="median dQ/dx, neighbours", persisted="not the median dQ/dx"),
    dict(step=10, stage="topology re-typing (knob-gated)", what="proton-daughter pion (m_shower_proton_daughter_pion), muon at a multi-proton vertex -> pion (m_muon_multi_proton_pion), A5 hadronic shower tag -> pion (m_shower_hadronic_tag)", where="NeutrinoPatternBase.cxx:342-470; NeutrinoShowerClustering.cxx:9772-9981", inputs="topology, dQ/dx growth", persisted="T_segment.pdg only; knob values of the production job NOT AUDITED (source defaults: off)"),
    dict(step=11, stage="pi0 incoming-track stamp", what="a track-typed member of a pi0 pair search window is stamped pion 211", where="NeutrinoShowerClustering.cxx:8176", inputs="pi0 pair topology", persisted="T_segment.pdg"),
    dict(step=12, stage="shower PDG published in T_kine", what="a shower row's type = the shower's cached particle_type (or the live start-segment pdg if kine_shower_pdg_live); a shower whose start segment is track-typed is a 'shower' row typed muon/pion/proton", where="NeutrinoKinematics.cxx:214-222", inputs="Shower::get_particle_type / start-segment pdg", persisted="T_kine.kine_particle_type, T_kine.kine_particle_is_shower"),
    dict(step=13, stage="entry into the single-photon shower set", what="only electron-typed (pdg 11) showers of the main vertex's shower set with E > 20 MeV are counted (shw_sp_n_20mev_showers); typing is necessary, not sufficient", where="NeutrinoTaggerSinglePhoton.cxx:2395-2505", inputs="shower pdg, energy, vertex membership", persisted="T_tagger.shw_sp_*"),
]
NOT_PERSISTED = ["per-segment dQ/dx vector and its median", "template scores (muon / proton / electron) and particle_score", "start_n / end_n at PID time (derivable from persisted vertex ids only for the final graph)", "dirsign at PID time (final value persisted)",
                 "shower direction and get_kine_charge", "production values of the knob-gated PID options"]


# ------------------------------------------------------------------------------------------------------------------------------ source decision predicates (unit-tested)
def median_fallback_type(median_over_mip: float, length_cm: float) -> int:
    """Type given by the median-dQ/dx fallback (step 3) when the template PID returned 0; 0 = still undetermined."""
    if median_over_mip > MIP_FALLBACK["proton_above"]:
        return 2212
    if median_over_mip < MIP_FALLBACK["muon_below"]:
        return 13
    if median_over_mip < MIP_FALLBACK["muon_short_below"] and length_cm < MIP_FALLBACK["short_len_cm"]:
        return 13
    return 0


def template_type(score_mu: float, score_p: float, score_e: float, length_cm: float) -> int:
    """Type of one orientation of the template competition: muon by default, proton if its score is strictly smaller, electron only if strictly smaller still AND the segment is shorter than 20 cm."""
    t, v = 13, score_mu
    if score_p < v:
        t, v = 2212, score_p
    if score_e < v and length_cm < ELECTRON_TEMPLATE_MAX_LEN_CM:
        t = 11
    return t


def bad_score_becomes_shower(length_cm: float, score: float) -> bool:
    return length_cm > BAD_SCORE_SHOWER["min_len_cm"] and BAD_SCORE_SHOWER["min_score"] < score < BAD_SCORE_SHOWER["max_score"]


def vertex_activity_type(length_cm: float, median_over_mip: float, other_end_degree: int):
    """Step 4: for a segment < 1.5 cm with one free end and the other end of degree > 2: proton if the median > 1.75 MIP, pion if < 1.2 MIP, else None (type unchanged)."""
    if length_cm < VERTEX_ACTIVITY_MAX_LEN_CM and other_end_degree > 2:
        if median_over_mip > MIP_FALLBACK["proton_above"]:
            return 2212
        if median_over_mip < MIP_FALLBACK["muon_below"]:
            return 211
    return None


def muon_pion_arbitration(candidates):
    """Step 8: ``candidates`` = ``[(segment, length_cm, far_end_has_proton), ...]`` of the pdg-13 segments at the main vertex.  The longest candidate whose far end has no proton neighbour keeps the muon type
    (strictly longer replaces the running best, so a tie keeps the first); EVERY other candidate becomes a pion.  Returns ``(muon_segment_or_None, [pion_segments])``."""
    muon, mlen = None, 0.0
    for sg, ln, prot in candidates:
        if ln > mlen and not prot:
            muon, mlen = sg, ln
    return muon, [sg for sg, _, _ in candidates if sg != muon]


# ------------------------------------------------------------------------------------------------------------------------------ taxonomies
TYPE_CLASSES = ["e-shower", "e-track", "mu-like", "pi-like", "proton-like", "other"]


def reco_type_class(pdg, is_shower) -> str:
    """Reconstructed type class of a T_kine row: the row's PDG assignment and its shower flag."""
    if pdg is None or (isinstance(pdg, float) and not np.isfinite(pdg)):
        return "no row"
    a = int(abs(pdg))
    if a == 11:
        return "e-shower" if is_shower else "e-track"
    return {13: "mu-like", 211: "pi-like", 2212: "proton-like"}.get(a, "other")


PHOTON_CLASSES = ["A clean electron shower", "B electron shower, not usable by the single-photon stage", "C muon-like dominant object", "D pion-like dominant object", "E proton-like dominant object",
                  "F electron-track / other track", "G fragmented (Phase 9), mixed types", "H no particle row", "I no reconstructed charge", "J charge outside candidates / other candidate"]


def photon_pid_class(state: str, outcome: str, dom_type: str) -> str:
    """Exclusive population of a signal photon from the Phase-9 state/outcome (unchanged) and the dominant object's reconstructed type.  Fragmented events are class G whatever their dominant type (the dominant
    type is kept as a separate label)."""
    if state == "photon_no_reco_charge":
        return PHOTON_CLASSES[8]
    if state in ("photon_charge_outside_candidates", "photon_in_other_candidate"):
        return PHOTON_CLASSES[9]
    if state == "photon_fragmented":
        return PHOTON_CLASSES[6]
    if state == "photon_particle_row_missing" or dom_type == "no row":
        return PHOTON_CLASSES[7]
    if dom_type == "e-shower":
        return PHOTON_CLASSES[0] if outcome == "pass_photon_shower_in_passing_candidate" else PHOTON_CLASSES[1]
    return {"mu-like": PHOTON_CLASSES[2], "pi-like": PHOTON_CLASSES[3], "proton-like": PHOTON_CLASSES[4]}.get(dom_type, PHOTON_CLASSES[5])


PROTON_CLASSES = ["proton-typed", "mu-typed", "pi-typed", "e-shower-typed", "e-track-typed", "other-typed", "no row", "merged / subdominant partner", "no signal-matched candidate"]
PROTON_KE_BINS = [0.0, 35.0, 50.0, 100.0, 200.0, 300.0, 500.0, np.inf]


def proton_reco_class(top_rows, sub_rows, in_signal_candidate: bool) -> str:
    """Class of ONE true signal primary proton from the rows of the signal-matched candidate (Phase-10 bookkeeping): ``top_rows`` = the reco type classes of the rows whose top source-ranked partner is this proton,
    ``sub_rows`` = rows for which it is only the 2nd / 3rd partner.  A proton-typed top row wins if there is one (Phase 10: proton_row_single / multiple); otherwise the type of the top row; a proton that is
    only a subdominant partner is ``merged / subdominant partner``; no row at all is ``no row``."""
    if not in_signal_candidate:
        return PROTON_CLASSES[8]
    if top_rows:
        for k, c in (("proton-like", PROTON_CLASSES[0]), ("mu-like", PROTON_CLASSES[1]), ("pi-like", PROTON_CLASSES[2]), ("e-shower", PROTON_CLASSES[3]), ("e-track", PROTON_CLASSES[4])):
            if k in top_rows:
                return c
        return PROTON_CLASSES[5]
    return PROTON_CLASSES[7] if sub_rows else PROTON_CLASSES[6]


MERGE_DESTINATIONS = ["signal photon", "another signal proton", "non-proton signal hadron (pion / muon / neutron-like)", "other signal EM", "other-neutrino or cosmic object", "unmatched / ambiguous"]


def merge_destination(dom_tclass_pdg, dom_nu, sig_nu, dom_is_signal_photon: bool, dom_pdg) -> str:
    """What the subdominant proton merged into: the TRUTH of the reconstructed object that is dominant on those points (its source-ranked top partner)."""
    if dom_pdg is None or not np.isfinite(dom_pdg) or dom_nu is None or not np.isfinite(dom_nu):
        return MERGE_DESTINATIONS[5]
    if dom_nu != sig_nu:
        return MERGE_DESTINATIONS[4]
    if dom_is_signal_photon:
        return MERGE_DESTINATIONS[0]
    a = int(abs(dom_pdg))
    if a == 2212:
        return MERGE_DESTINATIONS[1]
    if a in (11, 22):
        return MERGE_DESTINATIONS[3]
    return MERGE_DESTINATIONS[2]


def row_normalise(counts):
    """Row-normalised fractions of a counts matrix (rows with zero total stay zero)."""
    c = np.asarray(counts, float); s = c.sum(axis=1, keepdims=True)
    return np.divide(c, s, out=np.zeros_like(c), where=s > 0)
