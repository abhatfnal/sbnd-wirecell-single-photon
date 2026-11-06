"""Baseline single-photon selection (configs/baseline_selection.yaml) evaluated on candidate-level arrays.

Inputs are ``[event][candidate]`` awkward arrays keyed by CAF branch name (``wc.T_tagger...``) or by
``derived.<name>`` for the four offline-BDT scores. A candidate that lacks a finite value FAILS the cut.
No fiducial-volume cut is applied (the SBND FV is pending; the MicroBooNE FV must NOT be used).

Event-level policy for events with several neutrino candidates (UNRESOLVED, see the design note):
  ``any``   : the event passes if at least one candidate passes the full chain   (default, cut-flow only)
  ``first`` : only the candidate with nu_index == 0 is considered
"""
from __future__ import annotations

import operator
from pathlib import Path

import awkward as ak
import numpy as np
import yaml

from .samples import REPO_ROOT

DEFAULT_CFG = REPO_ROOT / "configs" / "baseline_selection.yaml"
OPS = {">": operator.gt, ">=": operator.ge, "<": operator.lt, "<=": operator.le, "==": operator.eq, "!=": operator.ne}


def load_config(path: Path | str = DEFAULT_CFG) -> dict:
    with open(path) as fh:
        return yaml.safe_load(fh)


def required_branches(cfg: dict) -> dict:
    """{'wc': [...direct branches...], 'derived': [...]} needed by the cut chain."""
    wc, derived = [], []
    for c in cfg["cuts"]:
        (derived if c.get("derived") else wc).append(c["branch"])
    return {"wc": list(dict.fromkeys(wc)), "derived": list(dict.fromkeys(derived))}


def evaluate_cut(arrays: dict, cut: dict):
    if cut["branch"] not in arrays:
        raise KeyError(f"cut {cut['name']!r}: branch {cut['branch']!r} not provided")
    x = ak.Array(arrays[cut["branch"]])
    # NaN compares False for > >= < <= ==; a NaN candidate therefore fails the cut ("!=" is not used by the baseline)
    return ak.fill_none(OPS[cut["op"]](x, cut["threshold"]), False)


def candidate_chain(arrays: dict, cfg: dict) -> dict:
    """Cumulative per-candidate pass flags: {'candidate_exists', cut1, cut1+cut2, ...} as [event][cand] bool."""
    out = {}
    cur = None
    for c in cfg["cuts"]:
        p = evaluate_cut(arrays, c)
        cur = p if cur is None else (cur & p)
        out[c["name"]] = cur
    return out


def event_pass(cand_flags, policy: str = "any", nu_index=None):
    if policy == "any":
        return ak.to_numpy(ak.any(cand_flags, axis=1))
    if policy == "first":
        if nu_index is None:
            raise ValueError("policy 'first' needs nu_index")
        return ak.to_numpy(ak.any(cand_flags & (ak.Array(nu_index) == 0), axis=1))
    raise ValueError(f"unknown candidate policy {policy!r}")


def cutflow(arrays: dict, cfg: dict, valid, policy: str = "any") -> list[dict]:
    """Event counts after each cumulative cut (raw counts, UNWEIGHTED; software validation only)."""
    valid = np.asarray(valid, dtype=bool)
    nu_index = arrays.get("wc.T_tagger.nu_index")
    n_cand = ak.to_numpy(ak.num(arrays[cfg["cuts"][0]["branch"]], axis=1))
    rows = [{"cut": "all_events", "n_events": int(len(valid))},
            {"cut": "wc_valid", "n_events": int(valid.sum())},
            {"cut": "has_neutrino_candidate", "n_events": int((valid & (n_cand > 0)).sum())}]
    chain = candidate_chain(arrays, cfg)
    for name, flags in chain.items():
        rows.append({"cut": "cum:" + name,
                     "n_events": int((valid & event_pass(flags, policy, nu_index)).sum())})
    return rows
