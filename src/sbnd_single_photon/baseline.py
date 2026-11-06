"""Glue: read the baseline-selection inputs from a MergedCaf and attach the offline BDT scores."""
from __future__ import annotations

from typing import Optional

import awkward as ak
import numpy as np

from . import bdt as B
from .caf import MergedCaf

TAGGER_FILLED = "wc.T_tagger.shw_sp_filled"
NU_INDEX = "wc.T_tagger.nu_index"


def bdt_input_map(models: dict) -> dict:
    """{model: [(xml_var_name, caf_branch), ...]} in XML VarIndex order."""
    return {m: [(v, B.input_branch(m, v)) for v in mdl.var_names] for m, mdl in models.items()}


def all_bdt_branches(models: dict) -> list[str]:
    return sorted({b for pairs in bdt_input_map(models).values() for _, b in pairs})


def bdt_availability(caf: MergedCaf, models: dict) -> dict:
    """{model: {'n_inputs':N,'n_present':n,'missing':[...]}} for THIS file's schema."""
    out = {}
    for m, pairs in bdt_input_map(models).items():
        miss = [b for _, b in pairs if not caf.has_wc(b)]
        out[m] = {"n_inputs": len(pairs), "n_present": len(pairs) - len(miss), "missing": miss}
    return out


def score_candidates(arrays: dict, models: dict) -> dict:
    """Offline BDT scores as ``derived.single_photon_<model>_score`` ([event][candidate], NaN if not evaluable)."""
    filled = arrays[TAGGER_FILLED]
    counts = ak.num(filled, axis=1)
    ok_filled = ak.to_numpy(ak.flatten(filled, axis=1)) != 0
    out = {}
    for m, pairs in bdt_input_map(models).items():
        cols = [ak.to_numpy(ak.flatten(arrays[b], axis=1)).astype(np.float64) for _, b in pairs]
        X = np.column_stack(cols) if cols and len(cols[0]) else np.zeros((0, len(pairs)))
        s = models[m].decision(X) if len(X) else np.zeros(0)
        s = np.where(ok_filled, s, np.nan)
        out[f"derived.single_photon_{m}_score"] = ak.unflatten(s, counts)
    return out


def read_baseline_arrays(caf: MergedCaf, models: dict, extra_wc=(), extra_rec=(), start=0, stop=None,
                         cut_branches=()) -> dict:
    """Read cut inputs + BDT inputs (+extras) for [start, stop) and add the derived scores."""
    wc = list(dict.fromkeys(list(cut_branches) + all_bdt_branches(models) + [TAGGER_FILLED, NU_INDEX] + list(extra_wc)))
    d = caf.read(wc=wc, rec=list(extra_rec), start=start, stop=stop)
    d.update(score_candidates(d, models))
    return d
