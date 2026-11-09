"""Table-level logic of the exclusive single-photon BACKGROUND-mechanism study (MC evaluation only; nothing changes any cut).

Inputs are plain tables: the derived analysis table (candidates, events), the per-candidate association/interaction table of
``background_truth`` ("light") and the per-selected-candidate deep table ("deep"). See docs/analysis/EXCLUSIVE_BACKGROUND_MECHANISMS.md.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import background_truth as BT
from .truth import ActiveVolume

KEY = ["file_index", "ev"]
CKEY = ["file_index", "ev", "nu_index"]
CLASS_ORDER = ["NC_PI0", "CC_PI0", "NUE_CC", "NUMU_CC", "OTHER_NC", "OTHER_CC", "OUTSIDE_TPC_NU", "COSMIC_OR_UNMATCHED", "MULTI_OR_AMBIGUOUS"]
OTHER_NU = ("NUMU_CC", "OTHER_NC", "OTHER_CC")
CH_LABEL = {0: "1g0p", 1: "1g1p", 2: "ge2p_diag"}


def outside_distance(x, y, z, box: ActiveVolume | None = None):
    """Euclidean distance (cm) from the provisional box to a point outside it (0 inside). The box is descriptive, not an FV."""
    b = box or ActiveVolume()
    d = lambda v, lo_hi: np.maximum(np.maximum(lo_hi[0] - v, v - lo_hi[1]), 0.0)
    return np.sqrt(d(np.asarray(x, float), b.x) ** 2 + d(np.asarray(y, float), b.y) ** 2 + d(np.asarray(z, float), b.z) ** 2)


def add_categories(light: pd.DataFrame, sig: pd.DataFrame, box: ActiveVolume | None = None) -> pd.DataFrame:
    """Add ``in_tpc``, ``out_dist_cm``, ``is_signal`` and the candidate-associated category ``cand_category`` to a light/deep-like table.

    ``sig``: natural-signal neutrinos (file_index, ev, k). A candidate is signal if its production-matched interaction (linked to rec.mc.nu index
    ``mnu_k``) is a qualifying NC Delta -> N gamma neutrino. Flavour/CC-NC come from the matched interaction (T_truth_nu ccnc: 0 = CC), pi0 from the
    rec.mc.nu GENIE primaries of that interaction."""
    d = light.copy()
    d["in_tpc"] = (ActiveVolume() if box is None else box).contains(d.mnu_x, d.mnu_y, d.mnu_z).fillna(False).astype(bool) if "mnu_x" in d else False
    d["out_dist_cm"] = outside_distance(d.mnu_x.fillna(0), d.mnu_y.fillna(0), d.mnu_z.fillna(0), box)
    s = sig[KEY + ["k"]].rename(columns={"k": "mnu_k"}).assign(_sig=True)
    d = d.merge(s, on=KEY + ["mnu_k"], how="left")
    d["is_signal"] = d._sig.fillna(False).astype(bool); d = d.drop(columns="_sig")
    n_pi0 = d.get("k_n_pi0", pd.Series(0, index=d.index)).fillna(0).values
    iscc = (d.mnu_ccnc.values == 0)
    d["cand_category"] = [BT.classify_candidate(t, nd, n, p, c, np0, bool(it), bool(sg)) for t, nd, n, p, c, np0, it, sg in
                          zip(d.tm_top_nu.values, d.tm_n_distinct_nu.values, d.tm_n.values, d.mnu_pdg.fillna(0).values, iscc, n_pi0, d.in_tpc.values, d.is_signal.values)]
    return d


def event_level(selected: pd.DataFrame, sig_event_class: pd.DataFrame) -> pd.DataFrame:
    """One row per selected event: number of passing candidates, candidate-associated category (``MULTI_OR_AMBIGUOUS`` if the passing candidates
    carry different categories), reco channel(s), and the signal/background/mixed class from ``exclusive``-style classification.

    ``selected``: passing candidates with ``cand_category`` and ``reco_proton_cat``; ``sig_event_class``: output of
    ``natural_signal.classify_selected_events`` (event_class signal_like / background / mixed)."""
    g = selected.groupby(KEY)
    ev = g.agg(n_pass=("nu_index", "size"), n_cat=("cand_category", "nunique"), cat=("cand_category", "first"),
               reco_cat=("reco_proton_cat", "first"), n_reco_cat=("reco_proton_cat", "nunique")).reset_index()
    ev["event_cand_category"] = np.where(ev.n_cat > 1, "MULTI_OR_AMBIGUOUS", ev.cat)
    ev["reco_channel"] = np.where(ev.n_reco_cat > 1, "mixed", ev.reco_cat.map(CH_LABEL))
    return ev.merge(sig_event_class[KEY + ["event_class"]], on=KEY, how="left", validate="one_to_one")


def accounting(ev: pd.DataFrame) -> dict:
    """Exact decomposition of the selected events: signal_like + background + mixed, background by reco channel and by category. Raises if anything is lost."""
    tot = len(ev)
    cls = ev.event_class.value_counts().to_dict()
    sl, bg, mx = cls.get("signal_like", 0), cls.get("background", 0), cls.get("mixed", 0)
    assert sl + bg + mx == tot, "events lost in the signal/background split"
    b = ev[ev.event_class == "background"]
    by_ch = b.reco_channel.value_counts().to_dict()
    by_cat = b.event_cand_category.value_counts().to_dict()
    assert sum(by_ch.values()) == bg and sum(by_cat.values()) == bg, "background events lost across channel/category"
    xt = pd.crosstab(b.event_cand_category, b.reco_channel)
    assert int(xt.values.sum()) == bg
    return dict(total=tot, signal_like=sl, background=bg, mixed=mx, background_by_channel=by_ch, background_by_category=by_cat,
                crosstab=xt.to_dict("index"))


def composition(b: pd.DataFrame, pot: float, cat_col: str = "event_cand_category", ch_col: str = "reco_channel") -> pd.DataFrame:
    """Counts, fractions and POT-normalised neutrino-induced rates (per 1e20, Poisson error on the raw count) per reco channel x category."""
    rows = []
    for ch, g in b.groupby(ch_col):
        n = len(g)
        for cat, c in g.groupby(cat_col):
            k = len(c)
            rows.append(dict(channel=ch, category=cat, count=k, fraction=k / n, rate_per_1e20=k / pot * 1e20, rate_err=np.sqrt(k) / pot * 1e20))
        rows.append(dict(channel=ch, category="TOTAL", count=n, fraction=1.0, rate_per_1e20=n / pot * 1e20, rate_err=np.sqrt(n) / pot * 1e20))
    return pd.DataFrame(rows)


def migration_by_class(sel: pd.DataFrame, truth_col: str = "k_n_p35", reco_col: str = "reco_proton_cat", cat_col: str = "cand_category") -> dict[str, pd.DataFrame]:
    """truth (0p/1p/>=2p) x reco (0p/1p/>=2p) for each class that has a matched neutrino; classes without one (cosmic/unmatched/ambiguous) go to a
    separate 'no truth category' table (reco counts only). Row sums equal the number of candidates of the class with a truth category."""
    out = {}
    for cat, g in sel.groupby(cat_col):
        has = g[truth_col].notna() & (g.tm_top_nu >= 0) & (g.tm_n_distinct_nu < 2)
        gg = g[has]
        t = np.minimum(gg[truth_col].astype(int).values, 2); r = gg[reco_col].astype(int).values
        m = np.zeros((3, 3), int)
        for a, b in zip(t, r):
            m[a, b] += 1
        df = pd.DataFrame(m, index=["truth 0p", "truth 1p", "truth >=2p"], columns=["reco 0p", "reco 1p", "reco >=2p"])
        df["no_truth_category"] = 0
        df.loc["no truth category (reco counts)", :] = 0
        nt = g[~has][reco_col].astype(int).value_counts()
        for r_, n_ in nt.items():
            df.loc["no truth category (reco counts)", f"reco {['0p','1p','>=2p'][r_]}"] = n_
        out[cat] = df.fillna(0).astype(int)
    return out


def mechanism_counts(g: pd.DataFrame) -> dict:
    """Number of candidates (events) with each overlapping migration-mechanism flag (any > 0)."""
    flags = ["rp_primary_signal", "rp_secondary_proton", "rp_other_pdg_same_nu", "rp_other_neutrino", "rp_unmatched", "rp_leftover_inc3", "rp_truth_ke_below_thr",
             "tp_found", "tp_row_below_thr", "tp_row_other_pid", "tp_no_row", "tp_only_other_cand"]
    return {f: int((g[f].fillna(0) > 0).sum()) for f in flags if f in g}


def cutflow_by_class(c: pd.DataFrame, stages: list[tuple[str, str]], cat_col: str = "cand_category", by_reco: bool = False) -> pd.DataFrame:
    """Candidate counts passing each (cumulative) stage, per category (and optionally per the candidate's own reco proton category)."""
    rows = []
    groups = [(cat, g) for cat, g in c.groupby(cat_col)]
    for cat, g in groups:
        splits = [("all", g)] + ([(CH_LABEL[k], g[g.reco_proton_cat == k]) for k in (0, 1, 2)] if by_reco else [])
        for sp, h in splits:
            row = dict(category=cat, split=sp, candidates=len(h))
            for s, col in stages:
                row[s] = int(h[col].sum())
            rows.append(row)
    return pd.DataFrame(rows)
