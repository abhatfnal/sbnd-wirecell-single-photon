"""Exclusive (truth 0p / 1p / >=2p) characterisation of the FROZEN baseline on a signal population. EVALUATION ONLY.

Sample-agnostic: everything works on three plain tables, so the same code runs on the natural-CV rehearsal population now and on
the official Wire-Cell merged NC-Delta sample later (same schema, see docs/analysis/OFFICIAL_SIGNAL_WC_ARRIVAL_RUNBOOK.md):

  * ``sig``   : one row per truth signal EVENT (file_index, ev, x, y, z, truth_cat 0/1/2, delta_pdg, nucleon_pdg, photon_mev, E, ...)
  * ``events``: derived analysis table, one row per CAF event (file_index, ev, wc_valid)
  * ``cands`` : derived analysis table, one row per Wire-Cell candidate (cut flags, reco_proton_cat, dom_nu_v{x,y,z}, dom_q ...)

Two views are always kept apart (nothing here changes any cut or threshold, and truth never decides whether an event passes):
  A  ACTUAL selection: an event passes a stage if ANY candidate (policy ``any``) / the policy-first candidate (``first``) does;
     reconstruction only.
  B  DIAGNOSTIC truth-matched view: only candidates whose dominant truth neutrino vertex lies within ``tol_cm`` of the signal
     vertex are considered (they are the "signal candidates"); used to ask where the signal interaction itself is lost.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

KEY = ["file_index", "ev"]
CAT_LABEL = {0: "0p", 1: "1p", 2: ">=2p"}
REASONS_A = ["wc_invalid", "no_candidate", "no_20mev_shower", "bdt_not_evaluable", "fail_numu", "fail_other", "fail_ncpi0",
             "fail_nue", "fail_n20br1", "selected"]
REASONS_B = ["wc_invalid", "no_candidate", "no_truth_matched_candidate", "no_20mev_shower", "bdt_not_evaluable", "fail_numu",
             "fail_other", "fail_ncpi0", "fail_nue", "fail_n20br1", "selected"]


def stage_defs(cfg) -> list[tuple[str, str]]:
    """Ordered (stage name, candidate column) of the frozen chain, from the baseline config (n_20mev, [evaluable], numu, other, ncpi0, nue, n20br1)."""
    cuts = ["cum_" + c["name"] for c in cfg["cuts"]]
    names = ["n20mev", "numu", "other", "ncpi0", "nue", "n20br1"]
    assert len(cuts) == len(names), "baseline config changed: update exclusive_signal.stage_defs"
    out = [("candidate", "cum_candidate_in_valid_event"), (names[0], cuts[0]), ("bdt_evaluable", "_bdt_eval")]
    out += list(zip(names[1:], cuts[1:]))
    out.append(("final", "pass_final"))
    return out


def match_candidates(cands: pd.DataFrame, sig: pd.DataFrame, tol_cm: float = 5.0) -> pd.Series:
    """Boolean per candidate row: the candidate's dominant truth neutrino vertex is within tol_cm of the event's signal vertex (truth, evaluation only)."""
    c = cands[KEY + ["dom_nu_vx", "dom_nu_vy", "dom_nu_vz"]].copy()
    c["_i"] = np.arange(len(c))
    m = c.merge(sig[KEY + ["x", "y", "z"]], on=KEY, how="inner")
    d = np.sqrt((m.dom_nu_vx - m.x) ** 2 + (m.dom_nu_vy - m.y) ** 2 + (m.dom_nu_vz - m.z) ** 2)
    ok = np.zeros(len(c), bool)
    ok[m["_i"].values[(d < tol_cm).values]] = True
    return pd.Series(ok, index=cands.index)


def signal_event_table(sig: pd.DataFrame, events: pd.DataFrame, cands: pd.DataFrame, cfg, *, policy: str = "any",
                       tol_cm: float = 5.0) -> pd.DataFrame:
    """One row per truth signal event with view-A and view-B stage flags, first-failure reasons and the reco categories.

    Columns added: wc_valid; A_<stage>; B_<stage> (B adds ``matched``); first_fail_A/B; n_pass; sel_reco_cat (the ANALYSIS candidate:
    lowest nu_index among passing candidates, -1 if none); match_reco_cat (DIAGNOSTIC: the signal-matched candidate with the largest
    dominant charge, ties to the lowest nu_index, -1 if none); match_cand_nu, match_passes_final, sel_is_matched, n_matched.
    """
    if policy not in ("any", "first"):
        raise ValueError(policy)
    stages = stage_defs(cfg)
    c = cands.copy()
    c["_bdt_eval"] = c[stages[1][1]] & c["bdt_evaluable"]
    c["_matched"] = match_candidates(c, sig, tol_cm)
    if policy == "first":
        c = c[c.policy_first.values]
    e = sig.merge(events[KEY + ["wc_valid"]], on=KEY, how="left", validate="one_to_one")
    if e.wc_valid.isna().any():
        raise ValueError("signal events missing from the events table: %d" % int(e.wc_valid.isna().sum()))
    e["wc_valid"] = e.wc_valid.astype(bool)
    cs = c.merge(sig[KEY], on=KEY, how="inner")
    names = [s for s, _ in stages]
    cols = dict(stages)
    for view, sub in (("A", cs), ("B", cs[cs._matched.values])):
        g = sub.groupby(KEY)
        for s in names:
            agg = g[cols[s]].any().rename(f"{view}_{s}")
            e = e.merge(agg.reset_index(), on=KEY, how="left")
            e[f"{view}_{s}"] = e[f"{view}_{s}"].fillna(False).astype(bool)
    nm = cs[cs._matched.values].groupby(KEY).size().rename("n_matched").reset_index()
    e = e.merge(nm, on=KEY, how="left"); e["n_matched"] = e.n_matched.fillna(0).astype(int)
    e["A_matched"] = e.n_matched > 0
    # first-failure, view A (reconstruction only) and view B (truth-matched candidate path)
    e["first_fail_A"] = _ff(e, "A", False)
    e["first_fail_B"] = _ff(e, "B", True)
    # analysis-selected candidate (lowest nu_index among passing) and diagnostic matched candidate
    p = cs[cs.pass_final.values].sort_values(KEY + ["c_nu_index"])
    npass = p.groupby(KEY).size().rename("n_pass")
    first_p = p.drop_duplicates(KEY)[KEY + ["reco_proton_cat", "_matched", "c_nu_index"]].rename(
        columns={"reco_proton_cat": "sel_reco_cat", "_matched": "sel_is_matched", "c_nu_index": "sel_nu_index"})
    m = cs[cs._matched.values].sort_values(KEY + ["dom_q", "c_nu_index"], ascending=[True, True, False, True]).drop_duplicates(KEY)
    m = m[KEY + ["reco_proton_cat", "c_nu_index", "pass_final", "bdt_evaluable", "dom_q", "dom_q_cand"]].rename(
        columns={"reco_proton_cat": "match_reco_cat", "c_nu_index": "match_cand_nu", "pass_final": "match_passes_final",
                 "bdt_evaluable": "match_bdt_evaluable"})
    e = e.merge(npass.reset_index(), on=KEY, how="left").merge(first_p, on=KEY, how="left").merge(m, on=KEY, how="left")
    e["n_pass"] = e.n_pass.fillna(0).astype(int)
    for k in ("sel_reco_cat", "match_reco_cat"):
        e[k] = e[k].fillna(-1).astype(int)
    e["sel_is_matched"] = e.sel_is_matched.fillna(False).astype(bool)
    e["match_passes_final"] = e.match_passes_final.fillna(False).astype(bool)
    e["match_bdt_evaluable"] = e.match_bdt_evaluable.fillna(False).astype(bool)
    e["policy"] = policy
    return e


def _ff(e, view, with_match):
    """First-failure reason per event. Order: wc_invalid, no_candidate, [no_truth_matched_candidate], then the chain stages."""
    seq = [("wc_invalid", e.wc_valid.values), ("no_candidate", e[f"{view}_candidate"].values if view == "A" else e["A_candidate"].values)]
    if with_match:
        seq.append(("no_truth_matched_candidate", e["A_matched"].values))
    chain = [("no_20mev_shower", "n20mev"), ("bdt_not_evaluable", "bdt_evaluable"), ("fail_numu", "numu"), ("fail_other", "other"),
             ("fail_ncpi0", "ncpi0"), ("fail_nue", "nue"), ("fail_n20br1", "n20br1")]
    for r, s in chain:
        seq.append((r, e[f"{view}_{s}"].values))
    out = np.array(["selected"] * len(e), dtype=object)
    done = np.zeros(len(e), bool)
    for r, ok in seq:
        hit = (~ok) & (~done)
        out[hit] = r
        done |= hit
    # the final flag must agree with 'selected' (the frozen chain ends in n20br1)
    assert ((out == "selected") == e[f"{view}_final"].values).all() or view == "B", "final flag disagrees with first-failure walk"
    return pd.Series(out, index=e.index)


def binom_ci(k: int, n: int, level: float = 0.683) -> tuple[float, float, float]:
    """(fraction, lo, hi): exact Clopper-Pearson interval (default 68.3 %). n == 0 -> NaNs."""
    if n == 0:
        return (np.nan, np.nan, np.nan)
    ci = stats.binomtest(int(k), int(n)).proportion_ci(confidence_level=level, method="exact")
    return (k / n, ci.low, ci.high)


def cutflow_by_truth(tab: pd.DataFrame, view: str, stage_names: list[str], cat_col: str = "truth_cat") -> pd.DataFrame:
    """Rows = stages (first is the truth denominator, then wc_valid, ...), columns = total + each truth category, entries N, fraction of denominator, 68 % exact interval."""
    rows = []
    groups = {"all": tab, **{CAT_LABEL[k]: tab[tab[cat_col] == k] for k in (0, 1, 2)}}
    stage_cols = [("truth_denominator", None), ("wc_valid", "wc_valid")] + [(s, f"{view}_{s}") for s in stage_names]
    if view == "B":
        stage_cols.insert(3, ("truth_matched_candidate", "B_matched" if "B_matched" in tab else "A_matched"))
    for s, col in stage_cols:
        for gname, g in groups.items():
            n0 = len(g)
            k = n0 if col is None else int(g[col].sum())
            f, lo, hi = binom_ci(k, n0)
            rows.append(dict(stage=s, group=gname, N=k, denominator=n0, fraction=f, lo68=lo, hi68=hi))
    return pd.DataFrame(rows)


def first_failure_table(tab: pd.DataFrame, col: str, reasons: list[str], by: str = "truth_cat") -> pd.DataFrame:
    """Counts of the mutually exclusive first-failure reason per group (``by``: truth_cat code or delta_pdg), rows = reasons, with a total column."""
    rows = []
    keys = sorted(tab[by].unique())
    for r in reasons:
        row = {"reason": r, "all": int((tab[col] == r).sum())}
        for k in keys:
            row[CAT_LABEL.get(k, str(k)) if by == "truth_cat" else str(k)] = int(((tab[col] == r) & (tab[by] == k)).sum())
        rows.append(row)
    return pd.DataFrame(rows)


def migration_matrix(truth: np.ndarray, reco: np.ndarray, normalize: bool = False) -> pd.DataFrame:
    """Truth (0,1,2) x reco (0,1,2, -1 = no candidate / unreconstructed). Row totals always equal the number of truth events."""
    truth = np.asarray(truth); reco = np.asarray(reco)
    m = np.zeros((3, 4), float)
    for t in (0, 1, 2):
        for j, r in enumerate((0, 1, 2, -1)):
            m[t, j] = int(((truth == t) & (reco == r)).sum())
    df = pd.DataFrame(m, index=[f"truth {CAT_LABEL[k]}" for k in (0, 1, 2)], columns=["reco 0p", "reco 1p", "reco >=2p", "no candidate/unreco"])
    df["row_total"] = df.sum(axis=1)
    if normalize:
        tot = df.pop("row_total").replace(0, np.nan)
        df = df.div(tot, axis=0)
    return df


def migration_checkpoints(tab: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """The four requested checkpoints. A-C use the DIAGNOSTIC signal-matched candidate's reco category; D shows both the
    analysis-selected candidate (reconstruction-only selection) and the matched candidate among final events."""
    t, mr = tab.truth_cat.values, tab.match_reco_cat.values
    out = {"A_all_truth_events__matched_candidate": migration_matrix(t, mr)}
    has = tab.A_matched.values
    out["B_events_with_matched_candidate"] = migration_matrix(t[has], mr[has])
    ev = tab.match_bdt_evaluable.values & has
    out["C_matched_candidate_bdt_evaluable"] = migration_matrix(t[ev], mr[ev])
    fin = tab.A_final.values
    out["D_final_events__analysis_selected_candidate"] = migration_matrix(t[fin], tab.sel_reco_cat.values[fin])
    out["D_final_events__matched_candidate"] = migration_matrix(t[fin], mr[fin])
    return out


def efficiency_table(tab_any: pd.DataFrame, tab_first: pd.DataFrame, level: float = 0.683) -> pd.DataFrame:
    """Natural-CV baseline efficiency CROSS-CHECK (not a final signal efficiency): selected / truth events per truth class, exact binomial interval."""
    rows = []
    for pol, tab in (("any", tab_any), ("first", tab_first)):
        for name, g in (("total", tab), *[(CAT_LABEL[k], tab[tab.truth_cat == k]) for k in (0, 1, 2)]):
            k, n = int(g.A_final.sum()), len(g)
            f, lo, hi = binom_ci(k, n, level)
            rows.append(dict(policy=pol, truth_class=name, selected=k, truth=n, efficiency=f, lo68=lo, hi68=hi))
    return pd.DataFrame(rows)


def delta_topology(tab: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Delta charge (delta_pdg 2114 = Delta0 -> n gamma, 2214 = Delta+ -> p gamma) against truth and reco proton category.
    Reco categories: matched-candidate category at the candidate stage, analysis-selected candidate category at the final stage."""
    out = {}
    lab = {2114: "Delta0 -> n gamma", 2214: "Delta+ -> p gamma"}
    rec = {"truth_all_events": ("truth_cat", np.ones(len(tab), bool)),
           "reco_matched_candidate_stage": ("match_reco_cat", tab.A_matched.values),
           "reco_final_selected_stage": ("sel_reco_cat", tab.A_final.values)}
    for name, (col, mask) in rec.items():
        rows = {}
        for d, l in lab.items():
            g = tab[mask & (tab.delta_pdg == d).values]
            rows[l] = [int((g[col] == k).sum()) for k in (0, 1, 2)] + [len(g)]
        out[name] = pd.DataFrame(rows, index=["0p", "1p", ">=2p", "total"]).T
    return out


# ----------------------------------------------------------------------------------------------------------------------------
# Drop-in adapters for the official dedicated sample (no physics code differs from the natural-CV rehearsal)
# ----------------------------------------------------------------------------------------------------------------------------
def signal_truth_from_official_events(ev: pd.DataFrame) -> pd.DataFrame:
    """``$SP_DATA/official_gen2_ncdelta_truth/events.parquet`` (flatCAF truth census, one row per stored event) -> the ``sig`` schema.

    The flatCAF (file_index, ev) is NOT the Wire-Cell merged-CAF key; use :func:`attach_event_key` to map (run, subrun, evt) onto the
    merged-CAF derived table before running the characterisation."""
    s = pd.DataFrame(dict(run=ev.run.values, subrun=ev.subrun.values, evt=ev.evt.values, x=ev.true_vertex_x.values, y=ev.true_vertex_y.values,
                          z=ev.true_vertex_z.values, truth_cat=ev.true_proton_category.astype(int).values, delta_pdg=ev.delta_pdg.values,
                          nucleon_pdg=ev.decay_nucleon_pdg.values, photon_mev=ev.photon_energy_mev.values, E=ev.neutrino_energy_gev.values,
                          in_region=ev.vtx_in_active_tpc.astype(bool).values, n_p35=ev.n_true_protons.values))
    return s


def attach_event_key(sig: pd.DataFrame, events: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Map a truth table keyed by (run, subrun, evt) onto the derived analysis table's (file_index, ev). Returns (sig with the key, n signal events
    without a match in the table). Unmatched events are dropped from the join but their number MUST be reported (they stay in the truth denominator
    for an efficiency: an event lost in Wire-Cell production is an inefficiency, not a missing event)."""
    k = ["run", "subrun", "evt"]
    if events.duplicated(k).any():
        raise ValueError("(run, subrun, evt) is not unique in the derived events table")
    m = sig.merge(events[k + KEY], on=k, how="left")
    n_missing = int(m.file_index.isna().sum())
    m = m[m.file_index.notna()].copy()
    m[["file_index", "ev"]] = m[["file_index", "ev"]].astype(int)
    return m.reset_index(drop=True), n_missing
