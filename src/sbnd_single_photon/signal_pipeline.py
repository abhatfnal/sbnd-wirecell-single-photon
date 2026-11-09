"""Drop-in signal baseline pipeline: truth master x derived merged-CAF table -> denominators, cutflow, efficiencies, migration, yields (no ROOT).

The SAME physics code serves the natural-BNB rehearsal and the future official Wire-Cell signal sample: only the two inputs change (a region
truth table and the derived analysis table of the same sample). Events that never arrive in the merged CAFs STAY in the denominator and fail every
numerator (``missing_from_merged_caf``); wc.valid == 0 events likewise. Nothing is selected or tuned here.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import exclusive_signal as X
from . import signal_master as SM

KEY = ["file_index", "ev"]
MISSING_REASON = "missing_from_merged_caf"
RSE = ["run", "subrun", "evt"]


def region_truth(records: pd.DataFrame, box, label: str) -> pd.DataFrame:
    """Official master records of region V -> the characterisation's ``sig`` schema (one row per event; keyed by run/subrun/evt)."""
    rr = SM.region_records(records, box)
    return pd.DataFrame(dict(run=rr.run.values, subrun=rr.subrun.values, evt=rr.evt.values, reco1_unit=rr.reco1_unit.values, x=rr.vtx_x.values,
                             y=rr.vtx_y.values, z=rr.vtx_z.values, truth_cat=rr.truth_cat.astype(int).values, delta_pdg=rr.delta_pdg.values,
                             nucleon_pdg=rr.decay_nucleon_pdg.values, photon_mev=rr.photon_energy_mev.values, E=rr.nu_energy_gev.values,
                             in_region=True, n_p35=rr.n_true_protons.values, region=label, n_in_region=rr.n_in_region.values))


def split_arrived(sig_region: pd.DataFrame, events_table: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(arrived rows with the derived table's (file_index, ev); missing rows). Both together are exactly ``sig_region``."""
    arrived, n_missing = X.attach_event_key(sig_region, events_table)
    miss = sig_region.merge(arrived[RSE], on=RSE, how="left", indicator=True)
    miss = miss[miss._merge == "left_only"].drop(columns="_merge")
    assert len(arrived) + len(miss) == len(sig_region) and len(miss) == n_missing
    return arrived, miss.reset_index(drop=True)


def with_missing_rows(tab: pd.DataFrame, missing: pd.DataFrame, policy: str) -> pd.DataFrame:
    """Append the never-arrived events to a ``signal_event_table`` as all-failing rows (they remain in the denominator)."""
    t = tab.copy(); t["arrived"] = True
    if len(missing) == 0:
        return t
    m = missing.copy(); m["arrived"] = False
    for c in t.columns:
        if c in m.columns:
            continue
        if c.startswith(("A_", "B_")) or c in ("wc_valid", "sel_is_matched", "match_passes_final", "match_bdt_evaluable"):
            m[c] = False
        elif c in ("n_pass", "n_matched"):
            m[c] = 0
        elif c in ("sel_reco_cat", "match_reco_cat", "sel_nu_index", "match_cand_nu"):
            m[c] = -1
        elif c.startswith("first_fail"):
            m[c] = MISSING_REASON
        elif c == "policy":
            m[c] = policy
        else:
            m[c] = np.nan
    return pd.concat([t, m[t.columns]], ignore_index=True)


def validate_accounting(n_truth_expected: int, tab_any: pd.DataFrame, tab_first: pd.DataFrame, stage_names: list[str]) -> dict:
    """Exact accounting identities; raises AssertionError if anything is lost, double counted or non-monotone."""
    out = {}
    for p, t in (("any", tab_any), ("first", tab_first)):
        n = len(t)
        assert n == n_truth_expected, f"{p}: {n} rows but the truth denominator is {n_truth_expected}"
        k_ = RSE if set(RSE) <= set(t.columns) else KEY
        assert not t.duplicated(k_).any(), f"{p}: duplicated event"
        n_arr = int(t.arrived.sum()); n_valid = int(t.wc_valid.sum())
        assert n_arr + int((~t.arrived).sum()) == n
        assert (t.first_fail_A == MISSING_REASON).sum() == (~t.arrived).sum()
        ff = t.first_fail_A.value_counts()
        assert int(ff.sum()) == n, f"{p}: first-failure reasons do not partition the events"
        assert n_valid <= n_arr
        counts = [int(t[f"A_{s_}"].sum()) for s_ in stage_names]
        assert counts[0] <= n_valid + 0 or counts[0] <= n_arr, f"{p}: candidates exceed arrived events"
        assert all(x >= y for x, y in zip(counts, counts[1:])), f"{p}: cumulative stage counts are not non-increasing: {counts}"
        assert int(t.A_final.sum()) == int((t.first_fail_A == "selected").sum())
        out[p] = dict(rows=n, arrived=n_arr, missing=n - n_arr, wc_valid=n_valid, wc_invalid_arrived=n_arr - n_valid, final=int(t.A_final.sum()))
    assert out["first"]["final"] <= out["any"]["final"]
    out["ok"] = True
    return out


def signal_report(tab_any: pd.DataFrame, tab_first: pd.DataFrame, cfg, *, label: str, region: str, pot_signal: float | None = None,
                  exposure_pot: float | None = None) -> dict:
    """All tables of the signal baseline as plain Python objects (the runner writes them). Binomial uncertainties are exact Clopper-Pearson (68.3 %)."""
    stage_names = [s for s, _ in X.stage_defs(cfg)]
    rep = dict(label=label, region=region, n_truth=int(len(tab_any)), truth_class={X.CAT_LABEL[k]: int((tab_any.truth_cat == k).sum()) for k in (0, 1, 2)},
               delta={n: int((tab_any.delta_pdg == p).sum()) for n, p in (("Delta0", 2114), ("Delta+", 2214))},
               arrived=int(tab_any.arrived.sum()), missing=int((~tab_any.arrived).sum()), wc_valid=int(tab_any.wc_valid.sum()),
               wc_invalid_arrived=int((tab_any.arrived & ~tab_any.wc_valid).sum()))
    for p, t in (("any", tab_any), ("first", tab_first)):
        cf = X.cutflow_by_truth(t, "A", stage_names)
        rep[f"cutflow_{p}"] = cf
        rep[f"first_failure_{p}"] = X.first_failure_table(t, "first_fail_A", X.REASONS_A + [MISSING_REASON], "truth_cat")
        rep[f"migration_{p}"] = X.migration_checkpoints(t)
        rep[f"final_{p}"] = dict(total=int(t.A_final.sum()), reco_channel={X.CAT_LABEL[k]: int(((t.sel_reco_cat == k) & t.A_final).sum()) for k in (0, 1, 2)},
                                 by_truth={X.CAT_LABEL[k]: int(t[t.truth_cat == k].A_final.sum()) for k in (0, 1, 2)})
        rep[f"delta_topology_{p}"] = X.delta_topology(t)
    rep["efficiency"] = X.efficiency_table(tab_any, tab_first)
    # truth class -> reco channel counts of the analysis-selected candidate (policy any), against the FULL truth denominator
    k = np.zeros((3, 3), int)
    for tc in range(3):
        for rc in range(3):
            k[tc, rc] = int(((tab_any.truth_cat == tc) & tab_any.A_final & (tab_any.sel_reco_cat == rc)).sum())
    rep["selected_truth_to_reco"] = k
    if pot_signal:
        from . import signal_yield as Y
        inp = Y.SignalEfficiencyInputs(region, float(pot_signal), tuple(rep["truth_class"][X.CAT_LABEL[c]] for c in (0, 1, 2)), tuple(map(tuple, k.tolist())), "any")
        rep["yield_inputs"] = inp
        if exposure_pot:
            rep["expected_yield"] = Y.expected_yield(inp, float(exposure_pot))
    return rep


# ---------------------------------------------------------------------------------------------------- report rendering
def markdown_table(df: pd.DataFrame, index: bool = False, floatfmt: str = "{:.4g}") -> str:
    d = df.reset_index() if index else df
    cols = [str(c) for c in d.columns]
    fmt = lambda v: floatfmt.format(v) if isinstance(v, (float, np.floating)) else str(v)
    rows = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    rows += ["| " + " | ".join(fmt(v) for v in r) + " |" for r in d.itertuples(index=False)]
    return "\n".join(rows)


def render_template(text: str, values: dict) -> str:
    """Replace ``{{KEY}}`` placeholders. A placeholder without a value raises (a report must never silently drop a section)."""
    import re
    keys = set(re.findall(r"\{\{([A-Z0-9_]+)\}\}", text))
    missing = keys - set(values)
    if missing:
        raise KeyError(f"no value for template placeholders: {sorted(missing)}")
    for k in keys:
        text = text.replace("{{" + k + "}}", str(values[k]))
    return text


def efficiency_rows(tab_any: pd.DataFrame, tab_first: pd.DataFrame) -> pd.DataFrame:
    """Selected / N_signal_truth per truth class, both policies, exact binomial interval (the denominator includes missing and wc.invalid events)."""
    return X.efficiency_table(tab_any, tab_first)
