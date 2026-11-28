"""wc_upstream_chain: portable, toolkit-equivalent scoring of the upstream SBND Wire-Cell nu_mu / nu_e tagger BDTs.

The common numerical reference of Aurora and EAF for the upstream scores (Avinay, 2026-11-28). Dependencies: numpy, pandas
(pyarrow for the parquet CLI). No ROOT, no xgboost. DEVELOPMENT ONLY: it selects no model, threshold or vertex mode.

    from wc_upstream_chain import UpstreamChain, verify_release
    verify_release('<clone>/releases')['ok']
    uc = UpstreamChain(['<clone>/releases/nue_round4_ruleA_v2/wirecell/main', '<clone>/releases/numu_round3af/wirecell', '<wire-cell-data>'])
    scores = uc.score(cands, objs, kind='mc')

See README.md (interface) and CONVENTIONS.md (every numerical convention).
"""
__version__ = '1.0.0'

from .chain import (DEFAULT_KEY, NUE_NOT_RUN, SATURATED_LOW, ChainScorer, InputError, UpstreamChain, compare_exact,  # noqa: F401
                    resolve, scaled_dqdx)
from .inventory import bundle_fingerprint, chain_fingerprints, identify_route, release_inventory, shipped_inventory, verify_release  # noqa: F401
from . import identity, sp, spec  # noqa: F401
