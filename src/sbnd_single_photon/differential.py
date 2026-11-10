"""Differential (phase-space) characterisation of the FROZEN baseline efficiency on the official NC-Delta signal. CHARACTERISATION ONLY.

Nothing here changes a cut, a threshold or a policy. Three different quantities are kept strictly apart (they are NOT interchangeable):

* cumulative efficiency   eps_cum(s)  = N(pass every stage up to and including s) / N(truth denominator)
* conditional survival    surv(s)     = N(pass stage s)                          / N(reached stage s, i.e. passed the previous stage)
* first-failure fraction  ff(r)       = N(first failing stage is r)               / N(truth denominator)      (sums to 1 over r, incl. 'selected')

Every table is keyed by (variable, group, stage, bin) and carries the integer numerator/denominator so the accounting can be re-closed exactly.
The denominator of every bin and every curve is the SAME truth population (all events of the truth region, including the production-missing
event and wc.invalid events): events that are not represented fail every numerator.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import yaml

from . import exclusive_signal as X
from . import signal_pipeline as SP
from .samples import REPO_ROOT

BINS_YAML = REPO_ROOT / "configs" / "differential_bins.yaml"
SCHEMA_VERSION = "differential-efficiency-1.0"
KEY = ["file_index", "ev"]
RSE = ["run", "subrun", "evt"]
MISSING = SP.MISSING_REASON

# ordered ``(name, boolean column)``; each is cumulative (an event passes stage s only if it passed all previous ones)
STAGES = [("represented", "arrived"), ("wc_valid", "wc_valid"), ("candidate", "A_candidate"), ("n20mev", "A_n20mev"), ("bdt_evaluable", "A_bdt_evaluable"),
          ("numu", "A_numu"), ("other", "A_other"), ("ncpi0", "A_ncpi0"), ("nue", "A_nue"), ("n20br1", "A_n20br1"), ("final", "A_final")]
# first-failure categories (exactly one per denominator event) in cut order
FIRST_FAIL = [MISSING, "wc_invalid", "no_candidate", "no_20mev_shower", "bdt_not_evaluable", "fail_numu", "fail_other", "fail_ncpi0", "fail_nue", "fail_n20br1", "selected"]
FIRST_FAIL_LABEL = {MISSING: "missing from merged CAF", "wc_invalid": "wc.invalid", "no_candidate": "no candidate", "no_20mev_shower": "no >20 MeV shower",
                    "bdt_not_evaluable": "BDT not evaluable", "fail_numu": "fail numu", "fail_other": "fail other", "fail_ncpi0": "fail ncpi0", "fail_nue": "fail nue",
                    "fail_n20br1": "fail n_20br1", "selected": "selected"}
# conditional survival is defined for these (stage, previous stage) pairs
SURVIVAL_PAIRS = [("candidate", "wc_valid"), ("n20mev", "candidate"), ("bdt_evaluable", "n20mev"), ("numu", "bdt_evaluable"), ("other", "numu"), ("ncpi0", "other"),
                  ("nue", "ncpi0"), ("n20br1", "nue")]
# process codes of caf::g4_process_ (sbnanaobj/StandardRecord/SREnums.h), the only ones used here
G4_PROCESS = {36: "conv", 37: "phot", 47: "photonNuclear", 51: "compt", 60: "Transportation", 5: "neutronInelastic", 54: "hIoni", 63: "LegacyUNKNOWN", 1024: "UNKNOWN"}
BEAM_AXIS = np.array([0.0, 0.0, 1.0])     # +z in SBND detector coordinates (the BNB direction is within ~0.02 rad of it: checked against rec.mc.nu.momentum)


def load_bins(path=BINS_YAML) -> dict:
    d = yaml.safe_load(open(path))
    assert d["schema_version"] == SCHEMA_VERSION
    return d


# ----------------------------------------------------------------------------------------------------------------------- truth variables
def photon_truth_variables(te: pd.DataFrame) -> pd.DataFrame:
    """Derived truth columns from the ``truth_extra`` scan (one row per event): photon direction, cos to the beam axis, conversion distance and class."""
    p = te[["photon_px", "photon_py", "photon_pz"]].to_numpy(float)
    pm = np.linalg.norm(p, axis=1)
    out = pd.DataFrame(index=te.index)
    out["cos_theta_beam"] = (p @ BEAM_AXIS) / pm
    nuv = te[["nu_dir_x", "nu_dir_y", "nu_dir_z"]].to_numpy(float)
    out["cos_theta_nu"] = np.einsum("ij,ij->i", p, nuv) / pm
    s = te[["photon_sx", "photon_sy", "photon_sz"]].to_numpy(float); e = te[["photon_ex", "photon_ey", "photon_ez"]].to_numpy(float)
    d = e - s
    out["d_end_3d"] = np.linalg.norm(d, axis=1)
    for i, c in enumerate("xyz"):
        out["d_end_" + c] = d[:, i]
    return out


def classify_photon_end(te: pd.DataFrame) -> pd.Series:
    """Conversion class of the primary signal photon from the Geant4 end process of its track (see PHOTON_CONVERSION_DISTANCE_DEFINITION.md).
    'conv' = kG4conv and the end point inside the TPC volume; 'other_interaction' = compt/phot/photonNuclear/other with the end point inside;
    'left_volume' = the track end is outside the TPC volume (contained == 0): the photon did not interact inside the volume; 'no_photon' = no primary photon."""
    ep = te.photon_end_process.to_numpy(); ct = te.photon_contained.to_numpy()
    cls = np.full(len(te), "other_interaction", dtype=object)
    cls[(ep == 36) & (ct == 1)] = "conv"
    cls[ct == 0] = "left_volume"
    cls[ep == -1] = "no_photon"
    return pd.Series(cls, index=te.index)


def conv_distance(te: pd.DataFrame) -> pd.Series:
    """True conversion distance [cm]: |end of the primary signal photon's track - true neutrino vertex| when the photon ends by pair conversion
    inside the TPC volume (class 'conv'), else NaN. Never derived from a reconstructed shower."""
    v = photon_truth_variables(te).d_end_3d
    return v.where(classify_photon_end(te) == "conv")


# ----------------------------------------------------------------------------------------------------------------------- event table
def build_event_table(arrived: pd.DataFrame, missing: pd.DataFrame, events: pd.DataFrame, cands: pd.DataFrame, cfg, truth_extra: pd.DataFrame | None = None,
                      policy: str = "any", tol_cm: float = 5.0) -> pd.DataFrame:
    """One row per truth-denominator event (arrived + missing): the validated stage flags and first-failure reason of the baseline pipeline (the SAME code
    as the official baseline run) joined with the extra truth variables and the reco quantities of the analysis-selected and signal-matched candidates."""
    t = X.signal_event_table(arrived, events, cands, cfg, policy=policy, tol_cm=tol_cm)
    t = SP.with_missing_rows(t, missing, policy)
    t["A_final_flag"] = t.A_final.astype(bool)
    for _, col in STAGES:
        t[col] = t[col].fillna(False).astype(bool)
    t["first_fail"] = t.first_fail_A.astype(str)
    if truth_extra is not None:
        te = truth_extra.copy()
        pv = photon_truth_variables(te)
        te = pd.concat([te.rename(columns={"n_p35": "scan_n_p35"}), pv], axis=1)
        te["photon_end_class"] = classify_photon_end(te).values
        te["conv_distance_cm"] = conv_distance(te).values
        t = t.merge(te.drop(columns=["ev", "flatcaf"], errors="ignore"), on=RSE, how="left", validate="one_to_one")
        t["lead_proton_ke_mev"] = t.p_ke_lead
        t["max_sub35_proton_ke_mev"] = t.p_ke_max_below35
    t["nu_energy_gev"] = t["E"]
    t["vtx_x"], t["vtx_y"], t["vtx_z"] = t["x"], t["y"], t["z"]
    t["photon_energy_mev"] = t["photon_mev"]
    t["delta_label"] = np.where(t.delta_pdg == 2114, "Delta0", np.where(t.delta_pdg == 2214, "Delta+", "other"))
    t["truth_class"] = t.truth_cat.map(X.CAT_LABEL)
    # reco information of the analysis-selected (final) candidate and of the signal-matched candidate
    keep = ["file_index", "ev", "c_nu_index", "c_shw_sp_energy", "c_shw_sp_shw_vtx_dis", "c_kine_nu_x_corr", "c_kine_nu_y_corr", "c_kine_nu_z_corr", "c_lead_proton_ke_mev",
            "c_np35", "c_shw_sp_filled"]
    cc = cands[keep]
    for tag, nucol in (("sel", "sel_nu_index"), ("match", "match_cand_nu")):
        m = cc.rename(columns={k: f"{tag}_{k[2:]}" for k in keep if k.startswith("c_") and k != "c_nu_index"}).rename(columns={"c_nu_index": nucol})
        t = t.merge(m, on=KEY + [nucol], how="left")
    return t


# ----------------------------------------------------------------------------------------------------------------------- binning
def assign_bins(values: np.ndarray, edges) -> np.ndarray:
    """-1 = underflow, len(edges)-1 = overflow, NaN -> -2 (no value). Bin i covers [edges[i], edges[i+1]); the last in-range bin is closed on the right."""
    v = np.asarray(values, float); e = np.asarray(edges, float)
    idx = np.searchsorted(e, v, side="right") - 1
    idx = np.where(v == e[-1], len(e) - 2, idx)
    idx = np.where(v < e[0], -1, idx)
    idx = np.where(v > e[-1], len(e) - 1, idx)
    return np.where(np.isfinite(v), idx, -2).astype(int)


def group_masks(tab: pd.DataFrame, groups: list[str]) -> dict[str, np.ndarray]:
    g = {"all": np.ones(len(tab), bool)}
    for k, l in ((0, "0p"), (1, "1p"), (2, "ge2p")):
        g[f"truth_{l}"] = (tab.truth_cat == k).to_numpy()
    g["Delta0"] = (tab.delta_pdg == 2114).to_numpy(); g["Delta+"] = (tab.delta_pdg == 2214).to_numpy()
    return {k: g[k] for k in groups}


def efficiency_in_bins(tab: pd.DataFrame, var: str, edges, groups: list[str], stages: list[tuple[str, str]], extra_mask: np.ndarray | None = None) -> pd.DataFrame:
    """Long table: one row per (group, stage, bin) with cumulative efficiency AND conditional survival AND the integer counts. In-range bins plus the
    underflow/overflow/no-value rows so that the sum over rows of each (group, stage) denominator equals the group size exactly."""
    b = assign_bins(tab[var].to_numpy(), edges)
    nb = len(edges) - 1
    gm = group_masks(tab, groups)
    rows = []
    prev_of = dict((s, p) for s, p in SURVIVAL_PAIRS)
    flags = {s: tab[c].to_numpy(bool) for s, c in stages}
    all_flags = {s: tab[c].to_numpy(bool) for s, c in STAGES}
    for g, gmask in gm.items():
        if extra_mask is not None:
            gmask = gmask & extra_mask
        for bi in list(range(-2, nb + 1)):
            m = gmask & (b == bi)
            n_den = int(m.sum())
            if bi in (-2, -1, nb) and n_den == 0:
                continue
            kind = "bin" if 0 <= bi < nb else {-2: "novalue", -1: "underflow", nb: "overflow"}[bi]
            lo, hi = (edges[bi], edges[bi + 1]) if 0 <= bi < nb else (np.nan, np.nan)
            for s, _ in stages:
                k = int((m & flags[s]).sum())
                f, l, h = X.binom_ci(k, n_den)
                row = dict(variable=var, group=g, stage=s, kind=kind, bin=bi, lo=lo, hi=hi, denominator=n_den, numerator=k, efficiency=f, lo68=l, hi68=h)
                if s in prev_of:
                    n_reach = int((m & all_flags[prev_of[s]]).sum())
                    fs, ls, hs = X.binom_ci(k, n_reach)
                    row.update(n_reach=n_reach, survival=fs, surv_lo68=ls, surv_hi68=hs)
                rows.append(row)
    return pd.DataFrame(rows)


def first_failure_in_bins(tab: pd.DataFrame, var: str, edges, groups: list[str], extra_mask: np.ndarray | None = None) -> pd.DataFrame:
    """Counts and fractions (of the ORIGINAL denominator in the bin) of each mutually exclusive first-failure category; closes exactly per bin."""
    b = assign_bins(tab[var].to_numpy(), edges); nb = len(edges) - 1
    gm = group_masks(tab, groups); ff = tab.first_fail.to_numpy()
    rows = []
    for g, gmask in gm.items():
        if extra_mask is not None:
            gmask = gmask & extra_mask
        for bi in range(-2, nb + 1):
            m = gmask & (b == bi); n = int(m.sum())
            if bi in (-2, -1, nb) and n == 0:
                continue
            kind = "bin" if 0 <= bi < nb else {-2: "novalue", -1: "underflow", nb: "overflow"}[bi]
            lo, hi = (edges[bi], edges[bi + 1]) if 0 <= bi < nb else (np.nan, np.nan)
            tot = 0
            for r in FIRST_FAIL:
                k = int((m & (ff == r)).sum()); tot += k
                f, l, h = X.binom_ci(k, n)
                rows.append(dict(variable=var, group=g, reason=r, kind=kind, bin=bi, lo=lo, hi=hi, denominator=n, count=k, fraction=f, lo68=l, hi68=h))
            assert tot == n, f"first-failure accounting does not close in {var}/{g}/bin {bi}: {tot} vs {n}"
    return pd.DataFrame(rows)


def check_closure(eff: pd.DataFrame) -> bool:
    """For every (variable, group, stage): sum of bin denominators (incl. under/overflow/no-value) is the same for all stages and numerator <= denominator."""
    assert (eff.numerator <= eff.denominator).all()
    s = eff.groupby(["variable", "group", "stage"]).denominator.sum().unstack("stage")
    assert (s.nunique(axis=1) == 1).all()
    return True


# ----------------------------------------------------------------------------------------------------------------------- reweighting / standardisation
def standardised_difference(tab: pd.DataFrame, var: str, edges, a: str, b: str, stage_col: str = "A_final") -> dict:
    """Direct standardisation: efficiency of group ``a`` (e.g. truth_0p) re-weighted to the ``b`` group's distribution of ``var`` and vice versa. Pure bookkeeping:
    expresses how much of the integrated a-b efficiency difference is accounted for by a different distribution of ``var`` (an observed correlation, not a mechanism)."""
    bi = assign_bins(tab[var].to_numpy(), edges)
    gm = group_masks(tab, [a, b]); ok = (bi >= -1) & (bi <= len(edges) - 1)
    res = {}
    eff = {g: {} for g in (a, b)}; w = {g: {} for g in (a, b)}
    st = tab[stage_col].to_numpy(bool)
    for g, m in gm.items():
        m = m & ok
        for k in np.unique(bi[m]):
            mm = m & (bi == k)
            eff[g][k] = st[mm].mean(); w[g][k] = mm.sum() / m.sum()
    bins = sorted(set(eff[a]) & set(eff[b]))
    cover = lambda g: sum(w[g][k] for k in bins)
    obs_a = st[gm[a]].mean(); obs_b = st[gm[b]].mean()
    a_at_b = sum(eff[a][k] * w[b][k] for k in bins) / cover(b)
    b_at_a = sum(eff[b][k] * w[a][k] for k in bins) / cover(a)
    res.update(variable=var, eff_a=float(obs_a), eff_b=float(obs_b), diff_obs=float(obs_b - obs_a), a_reweighted_to_b_distribution=float(a_at_b), b_reweighted_to_a_distribution=float(b_at_a),
               diff_within_bins_b_weights=float(sum((eff[b][k] - eff[a][k]) * w[b][k] for k in bins) / cover(b)),
               diff_within_bins_a_weights=float(sum((eff[b][k] - eff[a][k]) * w[a][k] for k in bins) / cover(a)), coverage_a=float(cover(a)), coverage_b=float(cover(b)))
    return res


# ----------------------------------------------------------------------------------------------------------------------- stage decomposition / adjusted comparison
def stage_decomposition(tab: pd.DataFrame, a: str, b: str, n_boot: int = 400, seed: int = 20261110) -> pd.DataFrame:
    """Per stage: cumulative efficiency and conditional survival of groups a and b, the survival ratio and its share of ln(eps_b/eps_a).
    ln(eps_cum,final) = sum_s ln(surv_s) (telescoping product), so the per-stage ln-ratios add up exactly to the log ratio of final efficiencies. Bootstrap 68 % intervals
    (resampling events within each group). A decomposition of OBSERVED rates, not a causal attribution."""
    gm = group_masks(tab, [a, b])
    chain = ["represented", "wc_valid"] + [s for s, _ in SURVIVAL_PAIRS]
    col = dict(STAGES)
    F = {g: np.column_stack([tab[col[s]].to_numpy(bool)[gm[g]] for s in ["represented", "wc_valid"] + [s for s, _ in SURVIVAL_PAIRS]]).astype(float) for g in (a, b)}

    def stats(Fg):
        cum = Fg.mean(axis=0)
        surv = np.concatenate([[cum[0]], cum[1:] / np.where(cum[:-1] > 0, cum[:-1], np.nan)])
        return cum, surv

    rng = np.random.default_rng(seed)
    cum = {g: stats(F[g]) for g in (a, b)}
    boots = []
    for _ in range(n_boot):
        r = {g: stats(F[g][rng.integers(0, len(F[g]), len(F[g]))]) for g in (a, b)}
        boots.append(np.log(r[b][1] / r[a][1]))
    boots = np.array(boots)
    lr = np.log(cum[b][1] / cum[a][1])
    rows = []
    for i, s in enumerate(chain):
        rows.append(dict(stage=s, cum_a=cum[a][0][i], cum_b=cum[b][0][i], surv_a=cum[a][1][i], surv_b=cum[b][1][i], ln_ratio_surv=lr[i], ln_lo68=np.nanpercentile(boots[:, i], 15.87),
                         ln_hi68=np.nanpercentile(boots[:, i], 84.13), share_of_total_ln_ratio=lr[i] / lr.sum() if lr.sum() else np.nan))
    d = pd.DataFrame(rows); d.attrs.update(group_a=a, group_b=b, total_ln_ratio=float(lr.sum()))
    return d


def logit_fit(X: np.ndarray, y: np.ndarray, n_iter: int = 50, ridge: float = 1e-8) -> np.ndarray:
    """Plain IRLS logistic regression (X includes the intercept column). Returns the coefficient vector."""
    beta = np.zeros(X.shape[1])
    for _ in range(n_iter):
        eta = np.clip(X @ beta, -30, 30); p = 1 / (1 + np.exp(-eta)); w = p * (1 - p) + 1e-9
        H = (X * w[:, None]).T @ X + ridge * np.eye(X.shape[1]); g = X.T @ (y - p)
        step = np.linalg.solve(H, g); beta = beta + step
        if np.max(np.abs(step)) < 1e-8:
            break
    return beta


def design_matrix(tab: pd.DataFrame, features: list[str]) -> tuple[np.ndarray, list[str]]:
    """Standardised linear + quadratic terms of each feature (truth kinematics only)."""
    cols, names = [], []
    for f in features:
        v = tab[f].to_numpy(float); z = (v - np.nanmean(v)) / np.nanstd(v)
        cols += [z, z ** 2]; names += [f, f + "^2"]
    return np.column_stack(cols), names


def adjusted_difference(tab: pd.DataFrame, a: str, b: str, features: list[str], stage_col: str = "A_final", n_boot: int = 200, seed: int = 20261110) -> dict:
    """Efficiency difference (b - a) before and after adjusting for the given truth features by logistic regression + g-computation (average over the pooled sample of
    p(y | x, group=b) - p(y | x, group=a)). Observed-association bookkeeping only; a feature that is itself caused by the group (e.g. proton content) is not 'confounding'."""
    gm = group_masks(tab, [a, b]); m = gm[a] | gm[b]
    d = tab[m]; ind = gm[b][m].astype(float); y = d[stage_col].to_numpy(float)
    Xf, _ = design_matrix(d, features)

    def fit(Xf, ind, y):
        X = np.column_stack([np.ones(len(y)), ind, Xf]); beta = logit_fit(X, y)
        X1 = X.copy(); X1[:, 1] = 1; X0 = X.copy(); X0[:, 1] = 0
        p = lambda XX: 1 / (1 + np.exp(-(XX @ beta)))
        return float((p(X1) - p(X0)).mean()), float(beta[1])

    raw = float(y[ind == 1].mean() - y[ind == 0].mean()); adj, coef = fit(Xf, ind, y)
    rng = np.random.default_rng(seed); bs = []
    for _ in range(n_boot):
        i = rng.integers(0, len(y), len(y)); bs.append(fit(Xf[i], ind[i], y[i])[0])
    return dict(a=a, b=b, features=features, raw_difference=raw, adjusted_difference=adj, adjusted_lo68=float(np.percentile(bs, 15.87)), adjusted_hi68=float(np.percentile(bs, 84.13)),
                group_log_odds_coef=coef, n=int(m.sum()))
