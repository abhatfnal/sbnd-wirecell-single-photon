"""Event-safe train / validation / test split.

Scheme 'subrun_parity_valhash_v1':
  * odd subrun  -> 'test'   (the same half Xuyang's spec_v1 keeps out of training, so the two retrainings share it)
  * even subrun -> 'validation' when a seeded hash of (sample, run, subrun) is below val_fraction, else 'train'

The unit is the subrun, so every candidate of an event, and every event of a subrun, lands on one side, whichever
file holds it. The split is recomputed from (sample, run, subrun) every time; nothing is stored once and copied.
The 'test' half is the internal development test set. It is NOT the independent evaluation: that is the official
fg1 samples on EAF / FermiGrid, which this package never reads.
"""
import hashlib

import numpy as np

SCHEME = 'subrun_parity_valhash_v1'
DEFAULT_SEED = 20261117
DEFAULT_VAL_FRACTION = 0.25


def _u01(seed, sample, run, subrun):
    h = hashlib.blake2b(('%d|%s|%d|%d' % (seed, sample, run, subrun)).encode(), digest_size=8).digest()
    return int.from_bytes(h, 'little') / 2.0 ** 64


def assign(sample, run, subrun, seed=DEFAULT_SEED, val_fraction=DEFAULT_VAL_FRACTION):
    """Split label per row. sample, run, subrun: equal-length sequences."""
    sample = np.asarray(sample, dtype=object)
    run = np.asarray(run, dtype=np.int64)
    subrun = np.asarray(subrun, dtype=np.int64)
    out = np.empty(len(run), dtype=object)
    cache = {}
    for k in range(len(run)):
        key = (sample[k], int(run[k]), int(subrun[k]))
        lab = cache.get(key)
        if lab is None:
            if key[2] % 2 == 1:
                lab = 'test'
            else:
                lab = 'validation' if _u01(seed, *key) < val_fraction else 'train'
            cache[key] = lab
        out[k] = lab
    return out


def check_event_safe(frame, split_col='split', event_key=('sample', 'file_id', 'run', 'subrun', 'event'),
                     subrun_key=('sample', 'run', 'subrun')):
    """Raise if any event or subrun has rows on more than one side. Returns (n_events, n_subruns) checked."""
    for key in (list(event_key), list(subrun_key)):
        n = frame.groupby(key)[split_col].nunique()
        if (n > 1).any():
            raise AssertionError('%d groups of %s straddle the split' % (int((n > 1).sum()), key))
    return (frame[list(event_key)].drop_duplicates().shape[0], frame[list(subrun_key)].drop_duplicates().shape[0])
