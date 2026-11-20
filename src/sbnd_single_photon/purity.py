"""Exposure normalisation, expected purity and stage-wise yields of the exclusive NC-Delta -> N gamma selection (MC evaluation; nothing here selects or tunes).

Purity (the ONLY definition used):   P = S / (S + sum_i B_i),   every term an EXPECTED yield at one COMMON exposure (POT_target):
    S   = N_sel(dedicated NC-Delta sample) * POT_target / POT(dedicated)
    B_i = N_sel(generic-BNB CV, events WITHOUT an in-region natural NC-Delta interaction) * POT_target / POT(CV)
A raw fraction of a filtered sample is never called purity. The natural NC-Delta events of the generic CV that lie in the signal region are REMOVED from the background
(the dedicated sample supplies the signal expectation): no double counting. Stat. error: weighted-Poisson, sum(w^2).
"""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np, pandas as pd

STAGES = ["candidate", "n20mev", "bdt_evaluable", "numu", "other", "ncpi0", "nue", "n20br1"]
STAGE_LABEL = {"candidate": "candidate", "n20mev": ">0 shower >20 MeV", "bdt_evaluable": "BDT evaluable", "numu": "SP-numu", "other": "SP-other", "ncpi0": "SP-ncpi0", "nue": "SP-nue", "n20br1": "n20br1 == 1 (final)"}
MODELS = ("numu", "other", "ncpi0", "nue")
CHANNELS = {0: "1g0p", 1: "1g1p", 2: "ge2p"}
FROZEN_R1 = {"numu": 0.4, "other": 0.2, "ncpi0": -0.05, "nue": -1.0}


@dataclass(frozen=True)
class ScoreSource:
    """Which scores/thresholds define the cut chain. Only a FROZEN source may enter an evaluation (``require_frozen``). Round-2 hook: register the final frozen
    SBND scores as columns of the candidate table (``columns``) with their frozen thresholds; nothing else in the package changes."""
    name: str
    columns: dict
    thresholds: dict
    frozen: bool
    provenance: str
    dev_models: bool = False


FROZEN_LEGACY_R1 = ScoreSource("frozen_legacy_r1_source_faithful", {m: f"c_score_{m}" for m in MODELS}, dict(FROZEN_R1), True,
                               "four legacy MicroBooNE XMLs, log10((1+v)/(1-v)) once, kine_pio_flag=0 for ncpi0; cuts unchanged since Round 1")


def require_frozen(src: ScoreSource) -> None:
    if src.dev_models or not src.frozen or "DEV_DO_NOT_DEPLOY" in src.name or "DEV_DO_NOT_DEPLOY" in src.provenance:
        raise ValueError(f"score source {src.name!r} is a development / non-frozen model chain and cannot be used on an evaluation sample")


def stage_masks(c: pd.DataFrame, src: ScoreSource = FROZEN_LEGACY_R1, n20_col="c_shw_sp_n_20mev_showers", n20br1_col="c_shw_sp_n_20br1_showers") -> dict:
    """Candidate-level CUMULATIVE stage masks. Definitions follow ``wcl1116_replay_common.ev_stage_flags`` (BDT-evaluable = n20 cut AND evaluable flag, informational);
    score cuts are strict '>' on the source columns, NaN fails."""
    require_frozen(src)
    cand = c["cum_candidate_in_valid_event"].to_numpy(bool)
    n20 = cand & (c[n20_col].to_numpy(float) > 0)
    m = {"candidate": cand, "n20mev": n20, "bdt_evaluable": n20 & c["bdt_evaluable"].to_numpy(bool)}
    cur = n20
    for mod in MODELS:
        cur = cur & (c[src.columns[mod]].to_numpy(float) > src.thresholds[mod]); m[mod] = cur
    m["n20br1"] = cur & (c[n20br1_col].to_numpy(float) == 1)
    return m


def reco_channel_of(cat: pd.Series) -> str:
    """Event reconstructed-proton channel from the proton categories of its passing candidates (0,1,2): a single value -> its label, otherwise 'mixed'."""
    u = pd.unique(cat.dropna().astype(int))
    return "mixed" if len(u) > 1 else (CHANNELS.get(int(u[0]), "unknown") if len(u) else "unknown")


def event_stage_table(c: pd.DataFrame, keys: list, src: ScoreSource = FROZEN_LEGACY_R1, proton_col="reco_proton_cat") -> pd.DataFrame:
    """One row per event with candidates: bool column per stage (ANY candidate reaches it, the Round-1 'any' policy) and ``ch_<stage>`` = reco channel of the passing candidates."""
    m = stage_masks(c, src); out = None
    for s in STAGES:
        sub = c.loc[m[s], keys + [proton_col]]
        g = sub.groupby(keys)[proton_col].agg(lambda x: reco_channel_of(x)).rename("ch_" + s)
        g = g.to_frame(); g[s] = True
        out = g if out is None else out.join(g, how="outer")
    out = out.reset_index()
    for s in STAGES:
        out[s] = out[s].fillna(False).astype(bool); out["ch_" + s] = out["ch_" + s].fillna("")
    return out


@dataclass
class Yield:
    n: int
    w: float            # per-event weight (all events of one component share it)

    @property
    def value(self): return self.n * self.w
    @property
    def err(self): return float(np.sqrt(self.n) * self.w)


def weight(pot_target: float, pot_sample: float) -> float:
    assert pot_sample > 0 and pot_target > 0
    return pot_target / pot_sample


def purity(S: float, sigS: float, B: float, sigB: float):
    """P = S/(S+B) and its error from independent S and B (first-order propagation). Returns (nan, nan) when S+B == 0."""
    t = S + B
    if t <= 0:
        return float("nan"), float("nan")
    return S / t, float(np.sqrt((B * sigS) ** 2 + (S * sigB) ** 2) / t ** 2)


def remove_in_region_natural_signal(cv_events: pd.DataFrame, sig_in_region_keys: pd.DataFrame, keys=("file_index", "ev")) -> pd.Series:
    """Boolean mask over ``cv_events``: True = event CONTAINS an in-region natural NC-Delta->N-gamma interaction -> must be excluded from the background
    expectation (the dedicated sample supplies the signal). Selection-independent, so the removal is identical at every stage."""
    k = list(keys)
    s = sig_in_region_keys[k].drop_duplicates().assign(_sig=True)
    return cv_events[k].merge(s, on=k, how="left")["_sig"].fillna(False).astype(bool).set_axis(cv_events.index)


def topology_channels(df: pd.DataFrame, stage: str) -> pd.Series:
    """Reco channel at a stage of an ``event_stage_table`` row (only events that reach the stage)."""
    return df.loc[df[stage], "ch_" + stage]


def merge_Np(ch: pd.Series) -> pd.Series:
    """1gNp = 1g1p + ge2p ('mixed' stays separate and is reported)."""
    return ch.replace({"1g1p": "1gNp", "ge2p": "1gNp"})
