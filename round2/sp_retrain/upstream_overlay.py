"""Upstream-classifier domains for the SP BDT development tables: derived score OVERLAYS on immutable raw tables.

Domains (docs/SP_BDT_UPSTREAM_R4_INTEGRATION_AUDIT.md):
  A  the stored WCL1116 values (shipped MicroBooNE upstream weights on the WCL1116 reconstruction)  -- the baseline
  B  nu_mu numu_round3af: numu_1_score, numu_2_score, cosmict_10_score, numu_score replaced (simulation: dQ/dx x 1.071
     and the numu_cc_flag BDT copy, as the patched chain; data: no correction)
  C  nu_e nue_round4_ruleA_v2 (main): the 15 nu_e level-1 scores replaced (chain-stored transformed values)
  D  B and C together
Only the columns a genuine production with the releases would change are replaced. The raw cosmict_* dQ/dx values and
numu_cc_flag stay as stored (the patched chain scales / flips only the copies handed to the nu_mu BDTs); nue_score is
replaced in the overlay file but is not an input of any SP model.

The overlay rows come from tools/upstream_rescore.py (chain emulation, validated in tools/compare_upstream_official.py
and the in-chain test) joined by tools/build_upstream_overlay.py on the full candidate key; apply() re-checks, row by
row, that the stored values in the table being modified equal the stored values the overlay was computed from.
"""
import os

import numpy as np
import pandas as pd

NUMU_SCORES = ['numu_1_score', 'numu_2_score', 'cosmict_10_score', 'numu_score']
NUE_L1_SCORES = ['br3_3_score', 'br3_5_score', 'br3_6_score', 'pio_2_score', 'stw_2_score', 'stw_3_score', 'stw_4_score', 'sig_1_score',
                 'sig_2_score', 'lol_1_score', 'lol_2_score', 'tro_1_score', 'tro_2_score', 'tro_4_score', 'tro_5_score']
DOMAINS = {'A': [], 'B': NUMU_SCORES, 'C': NUE_L1_SCORES, 'D': NUMU_SCORES + NUE_L1_SCORES}
DOMAIN_LABEL = {'A': 'A_stored_WCL1116_shipped_upstream', 'B': 'B_numu_round3af', 'C': 'C_nue_round4_ruleA_v2_main', 'D': 'D_numu_round3af_and_nue_A_v2'}
KEY = ['sample', 'file_id', 'run', 'subrun', 'event', 'cand']
OVL_PREFIX = 'ovl_'
STORED_PREFIX = 'stored_'


def overlay_path(overlay_dir, sample):
    return os.path.join(overlay_dir, 'overlay_%s.parquet' % sample)


def xn_split_v11(sample_ids, run, subrun):
    """Xuyang's spec_v1.split_v11 role of a row in the upstream training ('dev' = development slice, used only for early
    stopping; 'train' = fitted). MC: subrun % 10 == 0 -> dev. Beam-off training half: run % 10 == 1 -> dev. Our beam-off
    id (wcl1116-fg-beamoff-train) is his wcl1116-beam-off-train (the same 558 odd-run files)."""
    s = np.asarray(sample_ids, dtype=str); run = np.asarray(run, int); subrun = np.asarray(subrun, int)
    bo = np.char.find(s, 'beamoff-train') >= 0
    bo |= np.char.find(s, 'beam-off-train') >= 0
    return np.where(bo, np.where(run % 10 == 1, 'dev', 'train'), np.where(subrun % 10 == 0, 'dev', 'train')).astype(object)


def _eq32(a, b):
    a = np.asarray(a, np.float64).astype(np.float32); b = np.asarray(b, np.float64).astype(np.float32)
    return (a == b) | (np.isnan(a) & np.isnan(b))


def apply(C, domain, overlay_dir, samples=None):
    """Copy of C with the domain's columns replaced from the overlay. Every row of C must have exactly one overlay row,
    and C's stored values of the replaced columns must equal the overlay's stored copies (float32, NaN == NaN)."""
    cols = DOMAINS[domain]
    if not cols:
        return C.copy()
    out = C.copy()
    samples = sorted(set(out['sample'].astype(str))) if samples is None else samples
    parts = []
    for s in samples:
        p = overlay_path(overlay_dir, s)
        if not os.path.exists(p):
            raise FileNotFoundError('no overlay for %s (%s)' % (s, p))
        O = pd.read_parquet(p, columns=KEY + [STORED_PREFIX + c for c in cols] + [OVL_PREFIX + c for c in cols])
        parts.append(O)
    O = pd.concat(parts, ignore_index=True)
    if O.duplicated(KEY).any():
        raise ValueError('overlay key not unique')
    keyc = out[KEY].copy()
    for k in ('run', 'subrun', 'event', 'cand'):
        keyc[k] = keyc[k].astype(np.int64); O[k] = O[k].astype(np.int64)
    keyc['sample'] = keyc['sample'].astype(str); keyc['file_id'] = keyc['file_id'].astype(str)
    O['sample'] = O['sample'].astype(str); O['file_id'] = O['file_id'].astype(str)
    M = keyc.reset_index(drop=True).merge(O, on=KEY, how='left', indicator=True)
    if len(M) != len(out):
        raise ValueError('overlay join changed the row count')
    miss = int((M['_merge'] != 'both').sum())
    if miss:
        raise ValueError('%d rows of the table have no overlay row (domain %s)' % (miss, domain))
    for c in cols:
        ok = _eq32(out[c].to_numpy(), M[STORED_PREFIX + c].to_numpy())
        if not ok.all():
            raise ValueError('stored %s differs from the overlay stored copy on %d rows: wrong join' % (c, int((~ok).sum())))
        out[c] = M[OVL_PREFIX + c].to_numpy(np.float64).astype(np.float32).astype(np.float64)
    return out
