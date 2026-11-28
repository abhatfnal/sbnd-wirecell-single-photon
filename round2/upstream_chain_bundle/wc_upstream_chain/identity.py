"""Candidate-identity conventions and checked translation between the sites' keys.

  XN_KEY        Xuyang's table builder (tables/build_tables.py) and the Aurora extractor tools/extract_upstream_inputs.py:
                (file_id, run, subrun, event, cand); events with wc.valid == 1; one row per wc.T_tagger.nu_index entry,
                cand = nu_index (NOT the position in the vector). file_id = CAF basename by default (--file-id-from basename);
                'dirname' = the parent folder, 'unit' = two levels up (aurora-r2 unit folders). Within one table the rule is fixed.
  AURORA_SP_KEY the Aurora SP development tables: ('sample',) + XN_KEY with file_id = CAF basename.
  EAF_KEY       EAF analysis tables: (file_index, ev, run, subrun, evt, nu_index); file_index -> CAF path through EAF's
                files table, evt = art event number (= XN 'event'), nu_index = XN 'cand', ev = entry within the file.

A translation is a 1:1 join through an explicit mapping table; anything unmapped, duplicated or ambiguous raises.
"""
import os

import numpy as np
import pandas as pd

XN_KEY = ['file_id', 'run', 'subrun', 'event', 'cand']
AURORA_SP_KEY = ['sample'] + XN_KEY
EAF_KEY = ['file_index', 'ev', 'run', 'subrun', 'evt', 'nu_index']
FILE_ID_RULES = {'basename': lambda p: os.path.basename(p),
                 'dirname': lambda p: os.path.basename(os.path.dirname(p.rstrip('/'))),
                 'unit': lambda p: os.path.basename(os.path.dirname(os.path.dirname(p.rstrip('/'))))}


class IdentityError(ValueError):
    pass


def file_id(path, rule='basename'):
    return FILE_ID_RULES[rule](path)


def placeholder_mask(cands):
    """The builder's placeholder rule: kine_reco_Enu == 0 and neutrino_type == 0 and nu_x == nu_y == nu_z == 0.
    The chain SCORES placeholder candidates like any other (their stored scores are closed bit-exact); the Aurora SP
    preselection drops them (labels.preselection: is_placeholder == 0)."""
    c = cands
    return ((c['kine_reco_Enu'].to_numpy() == 0) & (c['neutrino_type'].to_numpy() == 0) & (c['nu_x'].to_numpy() == 0)
            & (c['nu_y'].to_numpy() == 0) & (c['nu_z'].to_numpy() == 0))


def check_unique(df, key, what='table'):
    d = df.duplicated(key)
    if d.any():
        raise IdentityError('%s: %d duplicate identities on %s' % (what, int(d.sum()), key))


def translate(df, mapping, from_key, to_key, rename=None):
    """Attach to_key to df through `mapping` (a table carrying both from_key and to_key, one row per identity).
    Raises on a duplicate in either key of the mapping, on a df row without a mapping row, and on a row-count change."""
    check_unique(df, from_key, 'input')
    check_unique(mapping, from_key, 'mapping (from)')
    check_unique(mapping, to_key, 'mapping (to)')
    cols = list(dict.fromkeys(from_key + to_key))
    m = df.merge(mapping[cols], on=from_key, how='left', indicator=True, validate='one_to_one')
    miss = int((m['_merge'] != 'both').sum())
    if miss or len(m) != len(df):
        raise IdentityError('%d rows have no identity mapping' % miss)
    m = m.drop(columns='_merge')
    return m.rename(columns=rename) if rename else m


def join_exact(left, right, key, check_columns=()):
    """1:1 join on the full key; raises on duplicates, missing or extra rows; `check_columns` present in both must agree
    bit for bit (float32, NaN == NaN) -- e.g. kine_reco_Enu or a stored score copied at scoring time."""
    check_unique(left, key, 'left'); check_unique(right, key, 'right')
    m = left[key].merge(right[key], on=key, how='outer', indicator=True)
    miss, extra = int((m['_merge'] == 'left_only').sum()), int((m['_merge'] == 'right_only').sum())
    if miss or extra:
        raise IdentityError('join mismatch: %d left rows without a right row, %d right rows without a left row' % (miss, extra))
    out = left.merge(right, on=key, how='left', validate='one_to_one', suffixes=('', '__r'))
    for c in check_columns:
        a = np.asarray(out[c], np.float64).astype(np.float32); b = np.asarray(out[c + '__r'], np.float64).astype(np.float32)
        bad = ~((a == b) | (np.isnan(a) & np.isnan(b)))
        if bad.any():
            raise IdentityError('identity check %s differs on %d rows' % (c, int(bad.sum())))
    return out.drop(columns=[c + '__r' for c in check_columns])
