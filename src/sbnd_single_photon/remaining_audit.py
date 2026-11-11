"""AUDIT helpers for the remaining frozen single-photon stages (numu, ncpi0, nue BDTs and ``n_20br1 == 1``): pure functions, no I/O.

Characterisation only: nothing here changes a selection flag, threshold or policy.  The scoring / SHAP machinery is the Phase-8 one (:mod:`other_audit`, model-generic);
this module adds the tie-convention counter, the physics-family map, the controlling-candidate rule and the exclusive ``n_20br1`` failure taxonomy.
"""
from __future__ import annotations
import re
import numpy as np
import pandas as pd

from .bdt import TmvaBdt

FROZEN_THRESHOLDS = {"numu": 0.4, "other": 0.2, "ncpi0": -0.05, "nue": -1.0}      # configs/baseline_selection.yaml; never scanned
FAMILIES = ("upstream BDT scores", "cosmic tagger", "numuCC tagger inputs", "shower quality (br/lem/hol/lol)", "calorimetry (dQ/dx, dE/dx)", "track / hadron activity", "vertex / gap geometry", "multiplicity", "pi0 topology")
_UP = re.compile(r"^(numu(_\d)?|cosmict_10|tro_\d|stw_\d|sig_\d|pio_2|lol_\d|br3_\d)_score$")


def family_of(name: str) -> str:
    """Physics family of one BDT input (by name; the fill code of every input was read, `tables/remaining_stage_audit/input_source_table_*.csv`)."""
    if _UP.match(name):
        return "upstream BDT scores"
    if name.startswith("cosmict_") or name.startswith("cosmic_"):
        return "cosmic tagger"
    if name.startswith("numu_cc_"):
        return "numuCC tagger inputs"
    if name.startswith("shw_sp_pio_") or name.startswith("kine_pio_"):
        return "pi0 topology"
    if re.match(r"shw_sp_(br\d|lem_|hol_|lol_)", name):
        return "shower quality (br/lem/hol/lol)"
    if re.match(r"shw_sp_(vec_dQ_dx_|vec_mean_dedx|vec_median_dedx|max_dQ_dx_sample|n_below|n_lowest|n_highest|lowest_dQ|highest_dQ|medium_dQ|min_dQ)", name):
        return "calorimetry (dQ/dx, dE/dx)"
    if re.match(r"shw_sp_(proton_|num_protons|num_muons|num_mip_tracks|n_good_tracks)", name):
        return "track / hadron activity"
    if re.match(r"shw_sp_(n_good_showers|n_br\d_showers|n_20br1_showers|n_20mev_showers)", name):
        return "multiplicity"
    if name == "reco_nuvtxY" or re.match(r"shw_sp_(shw_vtx_dis|max_shw_dis|min_dis|stem_length|length_|n_vertex|n_other_vertex|n_stem_size|E_indirect|flag_all_above)", name):
        return "vertex / gap geometry"
    raise ValueError(f"no family for input {name!r}")


def n_tie_cases(model: TmvaBdt, X: np.ndarray) -> int:
    """Number of rows (candidates) for which AT LEAST ONE visited split compares a float32 input exactly equal to its float32 cut: the only inputs on which the frozen scorer
    (left iff ``x <= cut``) and the TMVA/production rule (right iff ``x >= cut``) can differ.  Rows with a non-finite input are skipped."""
    X = np.asarray(X, dtype=np.float64); ok = np.isfinite(X).all(axis=1); X32 = X[ok].astype(np.float32); n = len(X32); tie = np.zeros(n, bool)
    for t in model.trees:
        cut32 = t.cut.astype(np.float32); node = np.zeros(n, dtype=np.int64)
        for _ in range(256):
            iv = t.ivar[node]; internal = iv >= 0
            if not internal.any():
                break
            xv = X32[np.arange(n), np.where(internal, iv, 0)]; c = cut32[node]
            tie |= internal & (xv == c)
            node = np.where(internal, np.where(xv >= c, t.right[node], t.left[node]), node)
    return int(tie.sum())


def controlling_candidate(c: pd.DataFrame, reach: str, score: str, key=("file_index", "ev")) -> pd.DataFrame:
    """Per event, among the candidates that REACH a stage (``c[reach]``), the one with the largest score of that stage (ties: lowest ``c_nu_index``).  Returns one row per event with
    ``n_reaching`` and ``n_candidates_total``.  The event passes the stage iff this score exceeds the FIXED threshold (event-level ``any`` logic)."""
    key = list(key); r = c[c[reach]].sort_values(key + [score, "c_nu_index"], ascending=[True] * len(key) + [False, True])
    ctrl = r.drop_duplicates(key, keep="first").copy()
    ctrl = ctrl.merge(r.groupby(key).size().rename("n_reaching").reset_index(), on=key).merge(c.groupby(key).size().rename("n_candidates_total").reset_index(), on=key)
    return ctrl


N20BR1_CLASSES = (
    "no_br1_shower__clean_photon_shower_fails_br1",      # n_20br1 == 0 while the signal photon is a clean energetic electron shower (it is among the shower set and fails badreco1 or is not counted as br1-good)
    "no_br1_shower__photon_object_not_clean",            # n_20br1 == 0 and the signal photon is fragmented / typed non-electron / a track / not at the main vertex
    "multiple_br1_showers__extra_signal_photon_piece",   # n_20br1 >= 2 and the extra energetic shower rows are pieces of the signal photon
    "multiple_br1_showers__extra_other_signal_particle", # >= 2 and the extra shower rows are other signal-interaction particles (hadron-typed showers, secondary electrons, ...)
    "multiple_br1_showers__extra_other_interaction",     # >= 2 and the extra shower rows belong to another neutrino interaction or a cosmic object
    "multiple_br1_showers__unattributed",                # >= 2 and no extra energetic shower row can be attributed
)


def classify_n20br1(n20br1: int, photon_clean: bool, extra_signal_photon: int, extra_other_signal: int, extra_other_interaction: int) -> str:
    """Exclusive class of an event that reaches the ``n_20br1`` stage and fails it, from the controlling candidate: ``n20br1`` = ``shw_sp_n_20br1_showers`` (0 or >= 2 for a failing event) and the number
    of T_kine electron-typed shower rows above 20 MeV in that candidate other than the dominant signal-photon object, by truth origin (hierarchy: signal photon piece, other signal particle, other interaction)."""
    if n20br1 == 1:
        raise ValueError("an event with n_20br1 == 1 does not fail the stage")
    if n20br1 == 0:
        return N20BR1_CLASSES[0] if photon_clean else N20BR1_CLASSES[1]
    if extra_signal_photon > 0:
        return N20BR1_CLASSES[2]
    if extra_other_signal > 0:
        return N20BR1_CLASSES[3]
    if extra_other_interaction > 0:
        return N20BR1_CLASSES[4]
    return N20BR1_CLASSES[5]


def clean_label(outcome: str) -> str:
    """Photon-cleanliness label of an event that passes the shower stage (Phase 9 ``outcome``): ``clean`` = the signal photon is a clean energetic electron shower of a passing candidate;
    every other passing event is ``non_clean``.  The label is a fixed property of the event, so the same events are followed through the cutflow."""
    if outcome == "pass_photon_shower_in_passing_candidate":
        return "clean"
    if outcome == "pass_not_via_signal_photon_shower":
        return "non_clean"
    return "fails_shower_stage"


def default_fraction(values: np.ndarray, default: float) -> float:
    """Fraction of finite values exactly equal to the declared default (float32 comparison, as the tagger stores float32)."""
    v = np.asarray(values, float); v = v[np.isfinite(v)]
    return float((v.astype(np.float32) == np.float32(default)).mean()) if len(v) and np.isfinite(default) else np.nan
