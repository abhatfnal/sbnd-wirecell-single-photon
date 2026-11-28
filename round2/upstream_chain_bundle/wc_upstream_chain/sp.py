"""Which downstream single-photon (SP) BDT inputs are upstream-tagger outputs, and a checked replacement of exactly those.

Domains (as on Aurora, sp_retrain/upstream_overlay.py):
  A  stored values (shipped upstream weights)        B  numu_round3af nu_mu outputs replaced
  C  nue_round4_ruleA_v2 nu_e level-1 replaced       D  B and C (the approved WCL1116 development domain, 2026-11-28)
SP inputs never replaced: the raw cosmict_{2,3,7}_dQ_dx_{end,front} and numu_cc_flag (the chain scales / switches only the copies it
hands the nu_mu BDTs) and nue_score (read by no SP model). An SP model trained in one domain must never score another domain.
"""
import numpy as np

from . import spec as S
from .identity import join_exact

SP_UPSTREAM_INPUTS = {
    'single_photon_numu': ['numu_1_score', 'numu_score'],
    'single_photon_other': ['cosmict_10_score', 'numu_1_score', 'numu_2_score', 'numu_score'],
    'single_photon_ncpi0': list(S.NUE_L1_SCORES),
    'single_photon_nue': [],
}
DOMAINS = {'A': [], 'B': list(S.NUMU_SCORES), 'C': list(S.NUE_L1_SCORES), 'D': list(S.NUMU_SCORES) + list(S.NUE_L1_SCORES)}
DOMAIN_LABEL = {'A': 'A_stored_shipped_upstream', 'B': 'B_numu_round3af', 'C': 'C_nue_round4_ruleA_v2_main', 'D': 'D_numu_round3af_and_nue_A_v2'}


def replaced_inputs(sp_model, domain):
    return [c for c in SP_UPSTREAM_INPUTS[sp_model] if c in DOMAINS[domain]]


def replace_upstream_inputs(frame, scores, key, domain, check_columns=()):
    """Copy of `frame` (any table carrying SP inputs and `key`) with the domain's upstream columns taken from `scores`
    (an UpstreamChain.score result for the SAME candidates, same kind). 1:1 full-key join (raises on missing/extra/duplicate
    rows); every column outside the domain, in particular spec.RAW_MUST_STAY_RAW, is asserted unchanged."""
    cols = [c for c in DOMAINS[domain] if c in frame.columns]
    out = frame.reset_index(drop=True).copy()
    if not cols:
        return out
    chk = [c for c in check_columns if c in frame.columns and c in scores.columns]
    J = join_exact(out[key + chk], scores[key + cols + chk].reset_index(drop=True), key, check_columns=chk)   # keeps the frame's row order
    for c in cols:
        v = np.asarray(J[c], np.float64).astype(np.float32)
        out[c] = v.astype(out[c].dtype) if out[c].dtype.kind == 'f' else v
    for c in S.RAW_MUST_STAY_RAW:
        if c in frame.columns and not np.array_equal(out[c].to_numpy(), frame[c].reset_index(drop=True).to_numpy(), equal_nan=True):
            raise AssertionError('raw feature %s changed' % c)
    return out
