"""Event-level bookkeeping of naturally generated NC Delta -> N gamma interactions (truth) and their join to the derived analysis table.

Everything here is EVALUATION bookkeeping: truth is never used to choose a reconstructed candidate (candidate policies are the
provisional ``any`` and ``first`` of the baseline; the join is by the full event key). No cut, threshold or FV is defined here.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .truth import ActiveVolume
from .truth_signal import FILTER_BOX

KEY = ["file_index", "ev"]          # (source file, event position) == (source file, run, subrun, evt): run/subrun/evt are carried alongside


def in_box(df: pd.DataFrame, box=FILTER_BOX, x="x", y="y", z="z") -> np.ndarray:
    return np.asarray(box.contains(df[x].values, df[y].values, df[z].values))


def select_signal_neutrino(q: pd.DataFrame, *, k="nu_k", x="x", y="y", z="z") -> pd.DataFrame:
    """One row per event from a table of QUALIFYING neutrinos (one row per neutrino; columns file_index, ev, nu_k, x, y, z, ...).

    Provisional deterministic rule (SIGNAL_TRUTH_AND_DENOMINATOR.md §5): prefer the neutrino inside the filter box, then the lowest
    rec.mc.nu index. Adds ``n_signal_nu`` (all qualifying), ``n_signal_nu_in_box`` and ``selected_in_box``."""
    q = q.copy()
    q["_inbox"] = in_box(q, x=x, y=y, z=z)
    q["n_signal_nu"] = q.groupby(KEY)[k].transform("size")
    q["n_signal_nu_in_box"] = q.groupby(KEY)["_inbox"].transform("sum")
    out = q.sort_values(KEY + ["_inbox", k], ascending=[True, True, False, True]).drop_duplicates(KEY)
    return out.rename(columns={"_inbox": "selected_in_box"}).reset_index(drop=True)


def stage_columns(cfg) -> list[str]:
    return ["cum_candidate_in_valid_event"] + ["cum_" + c["name"] for c in cfg["cuts"]]


def stage_counts(sig_events: pd.DataFrame, events: pd.DataFrame, cands: pd.DataFrame, cfg) -> dict:
    """Frozen-baseline cutflow of the natural-signal EVENTS, by the full event key (file_index, ev) into the derived analysis table.

    ``any``: an event passes a stage if any of its candidates does; ``first``: only the nu_index == 0 candidate counts.
    Returns counts plus the reco proton split of the finally selected events (candidate with the lowest nu_index passing)."""
    e = sig_events[KEY].drop_duplicates().merge(events[KEY + ["wc_valid"]], on=KEY, how="left", validate="one_to_one", indicator=True)
    missing = int((e["_merge"] != "both").sum())
    c = cands.merge(e[KEY], on=KEY, how="inner")
    out = {"n_signal_events": int(len(e)), "events_not_found_in_table": missing, "wc_valid": int(e.wc_valid.fillna(False).sum())}
    stages = stage_columns(cfg)
    ev_index = {k: i for i, k in enumerate(map(tuple, e[KEY].values))}
    for pol in ("any", "first"):
        cc = c if pol == "any" else c[c.policy_first.values]
        out[pol] = {}
        for st in stages:
            f = cc[cc[st].values]
            out[pol][st] = int(f.groupby(KEY).ngroups)
        ev_ = cc[cc.cum_candidate_in_valid_event.values & cc.bdt_evaluable.values]
        out[pol]["bdt_evaluable"] = int(ev_.groupby(KEY).ngroups)
        fin = cc[cc.pass_final.values].sort_values(KEY + ["c_nu_index"]).drop_duplicates(KEY)
        out[pol]["reco_0p_1p_ge2p"] = [int((fin.reco_proton_cat == k).sum()) for k in (0, 1, 2)]
    return out
