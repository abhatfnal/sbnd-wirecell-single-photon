"""Preselection and control/sideband regions of the NC-Delta package, built ONLY from the already-frozen discriminants.

Source (MicroBooNE, `wcp-uboone-bdt/inc/WCPLEEANA/cuts.h` L8936-8979: is_singlephoton_{numu,other,ncpi0,nue}_sel): the single-photon BDT sidebands are the INVERSIONS of the
sequential BDT chain at the looser 'eff' thresholds (numu 0.1, other -0.4, ncpi0 -0.4, nue -3.0), each with its own lower bound -20 to drop sentinel scores. They are
reproduced unchanged on the log-odds scale of the source-faithful scorer. DROPPED on purpose: the MicroBooNE reco_nuvtxX 5-250 cm cut (no SBND analysis FV exists).
Nothing here is tuned; a region is a validation tool only after Avinay approves it (docs/analysis/NCDELTA_DATAMC_PLAN.md)."""
from __future__ import annotations
import numpy as np, pandas as pd

LOOSE = {"numu": 0.1, "other": -0.4, "ncpi0": -0.4, "nue": -3.0}
LOW = -20.0

REGIONS = {
    "preselection": dict(kind="preselection", doc="candidate in a wc.valid event, >0 showers above 20 MeV, BDT evaluable (no score cut)"),
    "SB_numu": dict(kind="sideband", doc="numuCC-rich: SP-numu score < 0.1 (> -20) [source is_singlephoton_numu_sel, 'eff' variant]"),
    "SB_other": dict(kind="sideband", doc="other-rich: numu > 0.1 and SP-other score < -0.4 (> -20) [is_singlephoton_other_sel]"),
    "SB_ncpi0": dict(kind="sideband", doc="NCpi0-rich: numu > 0.1, other > -0.4, SP-ncpi0 score < -0.4 (> -20) [is_singlephoton_ncpi0_sel]"),
    "SB_nue": dict(kind="sideband", doc="nue-rich: numu > 0.1, other > -0.4, ncpi0 > -0.4, SP-nue score < -3.0 (> -20), n20br1 == 1 [is_singlephoton_nue_sel]"),
    "final_frozen": dict(kind="signal_region", doc="the frozen cut chain (all four scores above their frozen thresholds, n20br1 == 1)"),
}


def region_mask(c: pd.DataFrame, region: str, score=None) -> np.ndarray:
    """Candidate-level boolean mask. ``score`` = {model: column} (default the source-faithful legacy columns); final_frozen uses purity.stage_masks."""
    from . import purity as P
    cols = score or {m: f"c_score_{m}" for m in P.MODELS}
    base = c["cum_candidate_in_valid_event"].to_numpy(bool) & (c["c_shw_sp_n_20mev_showers"].to_numpy(float) > 0) & c["bdt_evaluable"].to_numpy(bool)
    s = {m: c[cols[m]].to_numpy(float) for m in P.MODELS}
    if region == "preselection":
        return base
    if region == "final_frozen":
        return P.stage_masks(c)["n20br1"]
    if region == "SB_numu":
        return base & (s["numu"] < LOOSE["numu"]) & (s["numu"] > LOW)
    if region == "SB_other":
        return base & (s["numu"] > LOOSE["numu"]) & (s["other"] < LOOSE["other"]) & (s["other"] > LOW)
    if region == "SB_ncpi0":
        return base & (s["numu"] > LOOSE["numu"]) & (s["other"] > LOOSE["other"]) & (s["ncpi0"] < LOOSE["ncpi0"]) & (s["ncpi0"] > LOW)
    if region == "SB_nue":
        return (base & (s["numu"] > LOOSE["numu"]) & (s["other"] > LOOSE["other"]) & (s["ncpi0"] > LOOSE["ncpi0"]) & (s["nue"] < LOOSE["nue"]) & (s["nue"] > LOW)
                & (c["c_shw_sp_n_20br1_showers"].to_numpy(float) == 1))
    raise KeyError(region)


def topology_mask(c: pd.DataFrame, topology: str, proton_col="reco_proton_cat") -> np.ndarray:
    """Reconstructed-proton topology of the candidate (NOT the truth topology): inclusive | 1g0p (0 reco protons) | 1gNp (>= 1)."""
    p = c[proton_col].to_numpy(float)
    return {"inclusive": np.ones(len(c), bool), "1g0p": p == 0, "1gNp": p >= 1, "1g1p": p == 1, "ge2p": p >= 2}[topology]
