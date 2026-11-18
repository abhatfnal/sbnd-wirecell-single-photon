"""Shared library of the NOV16_FROZEN_R1_SELECTION_REPLAY (diagnostic; NOTHING here is tuned).

The selection is the FROZEN corrected Round-1 chain, unchanged:
    shw_sp_n_20mev_showers > 0, numu > 0.4, other > 0.2, ncpi0 > -0.05, nue > -1.0, shw_sp_n_20br1_showers == 1 (no analysis FV)
with the four legacy MicroBooNE XMLs, score = log10((1+v)/(1-v)) applied exactly once to the TMVA response v, and temp_kine_pio_flag = 0 for the ncpi0 control.
The scorer, thresholds and cut chain are imported from the corrected Round-1 library (``legacy_scorer``, ``selection``, ``scanio``): this module only wires tables to them.
"""
from __future__ import annotations
import os, sys, warnings
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src")); sys.path.insert(0, str(REPO / "scripts")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from sbnd_single_photon import legacy_scorer as L, scanio as SIO, selection as SEL

SPD = Path(os.environ.get("SP_DATA", "/tmp"))
W = SPD / "wcl1116_nov16"; NEW = W / "analysis_tables_new"; OLD = W / "analysis_tables_old"; DER = W / "derived"; DER.mkdir(parents=True, exist_ok=True)
OUT = REPO / "tables" / "wcl1116_nov16_replay"; OUT.mkdir(parents=True, exist_ok=True)
PLOTS = REPO / "plots" / "wcl1116_nov16_replay"; PLOTS.mkdir(parents=True, exist_ok=True)
SPC = SPD / "legacy_scorer_correction"
RSE = ["run", "subrun", "evt"]
FROZEN = {"numu": 0.4, "other": 0.2, "ncpi0": -0.05, "nue": -1.0}
STAGES = ["candidate", "n20mev", "bdt_evaluable", "numu", "other", "ncpi0", "nue", "n20br1"]


def load_cfg():
    cfg = SEL.load_config()
    assert [c["threshold"] for c in cfg["cuts"] if "score" in c["name"]] == [0.4, 0.2, -0.05, -1.0], "frozen thresholds must be unchanged"
    assert L.FROZEN_THRESHOLDS == FROZEN
    return cfg


def to_D(cands: pd.DataFrame, events: pd.DataFrame, cfg) -> pd.DataFrame:
    """Source-faithful scoring of a candidate table built by ``build_analysis_table.py``: v (stored) -> log10((1+v)/(1-v)) ONCE; ncpi0 from the stored flag-zero response
    ``c_score_ncpi0_pio0``; the cum_* chain is recomputed with the UNCHANGED thresholds. Raw responses are kept as ``v_<model>``."""
    assert "c_score_ncpi0_pio0" in cands.columns, "table lacks the flag-zero ncpi0 response (built without the Nov16 builder?)"
    c = cands.copy()
    v = {m: c[f"c_score_{m}"].to_numpy(float).copy() for m in L.MODELS}
    v["ncpi0"] = c["c_score_ncpi0_pio0"].to_numpy(float).copy()
    for m in L.MODELS:
        c[f"v_{m}"] = v[m]
        c[f"c_score_{m}"] = np.asarray(L.score(v[m], True), dtype=np.float64)       # exactly one application of the log-odds transform
    tab = {"ev_valid": events.wc_valid.values, "c_gev": c.gev.values.astype(np.int64)}
    for col in c.columns:
        if col.startswith("c_"):
            tab[col] = c[col].values
    chain = SIO.candidate_chain(tab, cfg)
    for name, flag in chain.items():
        c["cum_" + name] = flag
    c["pass_final"] = chain[cfg["cuts"][-1]["name"]]
    return c


def ev_stage_flags(c: pd.DataFrame) -> pd.DataFrame:
    """Per event (keyed run/subrun/evt): did ANY candidate reach each cumulative stage (the 'any' policy of Round 1)? Stage definitions follow ``exclusive_signal.stage_defs``
    (the BDT-evaluable stage is the n20 cut AND the evaluable flag)."""
    t = c[RSE].copy()
    t["candidate"] = c["cum_candidate_in_valid_event"].values
    t["n20mev"] = c["cum_n_20mev_showers_gt0"].values
    t["bdt_evaluable"] = (c["cum_n_20mev_showers_gt0"] & c["bdt_evaluable"]).values
    t["numu"] = c["cum_single_photon_numu_score_gt_0p4"].values
    t["other"] = c["cum_single_photon_other_score_gt_0p2"].values
    t["ncpi0"] = c["cum_single_photon_ncpi0_score_gt_m0p05"].values
    t["nue"] = c["cum_single_photon_nue_score_gt_m1"].values
    t["n20br1"] = c["cum_n_20br1_showers_eq1"].values
    return t.groupby(RSE)[STAGES].any()


def first_changed_stage(old: pd.DataFrame, new: pd.DataFrame) -> pd.Series:
    """First stage (in cut order) at which the cumulative any-candidate state differs between old and new; '' if none. Inputs: boolean frames with the STAGES columns, same index."""
    diff = (old[STAGES].to_numpy(bool) != new[STAGES].to_numpy(bool))
    first = np.where(diff.any(axis=1), diff.argmax(axis=1), -1)
    return pd.Series([STAGES[i] if i >= 0 else "" for i in first], index=old.index)


def binom(k, n):
    from sbnd_single_photon import exclusive_signal as X
    v, lo, hi = X.binom_ci(int(k), int(n))
    return float(v), float(lo), float(hi)


def read_tables(root: Path, sample: str):
    d = root / sample
    return pd.read_parquet(d / "events.parquet"), pd.read_parquet(d / "candidates.parquet"), pd.read_parquet(d / "files.parquet")
