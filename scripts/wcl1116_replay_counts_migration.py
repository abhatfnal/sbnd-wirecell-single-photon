#!/usr/bin/env python
"""Transitions of the shower-stage counters between the old and Nov16 reconstruction for MATCHED candidates (same file, event, nu_index): shw_sp_filled, the >20 MeV shower count and the n_20br1 count,
plus candidate multiplicity per matched event. Descriptive; nothing is selected or tuned.

    source env/setup_eaf.sh && python scripts/wcl1116_replay_counts_migration.py
"""
from wcl1116_replay_common import *


def tables(s):
    if s == "official_gen2_ncdelta":
        ev_o, c_o = pd.read_parquet(SPD / "analysis_tables" / s / "events.parquet"), pd.read_parquet(SPC / "official_candidates_D_full.parquet")
        ev_n, c_n, _ = read_tables(NEW, s); return c_o, c_n, ev_o, ev_n
    if s == "bnb_cv":
        ev_o, c_o = pd.read_parquet(SPD / "analysis_tables" / s / "events.parquet"), pd.read_parquet(SPC / "bnb_candidates_D_full.parquet")
        ev_n, c_n, _ = read_tables(NEW, s); return c_o, c_n, ev_o, ev_n
    ev_o, c_o, _ = read_tables(OLD, s); ev_n, c_n, _ = read_tables(NEW, s); return c_o, c_n, ev_o, ev_n


def state(x, kind):
    x = np.asarray(x, float)
    if kind == "filled":
        return np.where(~np.isfinite(x), "nan", np.where(x > 0, "filled", "not filled"))
    return np.where(~np.isfinite(x), "nan", np.where(x >= 2, "2+", x.astype(int).astype(str)))


rows = []; mult = []
for s in ("official_gen2_ncdelta", "nuecc", "bnb_cv", "beam_off", "beam_on_open"):
    try:
        c_o, c_n, ev_o, ev_n = tables(s)
    except FileNotFoundError:
        print("skip", s); continue
    cols = ["c_nu_index", "c_shw_sp_filled", "c_shw_sp_n_20mev_showers", "c_shw_sp_n_20br1_showers"]
    j = c_o[RSE + cols].merge(c_n[RSE + cols], on=RSE + ["c_nu_index"], suffixes=("_o", "_n"))
    for col, kind, nm in (("c_shw_sp_filled", "filled", "shw_sp_filled"), ("c_shw_sp_n_20mev_showers", "n", ">20 MeV shower count"), ("c_shw_sp_n_20br1_showers", "n", "n_20br1 count")):
        so, sn = state(j[col + "_o"], kind), state(j[col + "_n"], kind)
        for (a, b), g in pd.DataFrame(dict(a=so, b=sn)).groupby(["a", "b"]):
            rows.append(dict(sample=s, variable=nm, old=a, new=b, N=len(g), n_matched_candidates=len(j)))
    m = ev_o[RSE + ["ncand"]].merge(ev_n[RSE + ["ncand"]], on=RSE, suffixes=("_old", "_new"))
    mult.append(dict(sample=s, matched_events=len(m), same=int((m.ncand_old == m.ncand_new).sum()), more_in_new=int((m.ncand_new > m.ncand_old).sum()), fewer_in_new=int((m.ncand_new < m.ncand_old).sum()),
                     only_old=len(set(map(tuple, ev_o[RSE].values)) - set(map(tuple, ev_n[RSE].values))), only_new=len(set(map(tuple, ev_n[RSE].values)) - set(map(tuple, ev_o[RSE].values))),
                     total_candidates_old=int(len(c_o)), total_candidates_new=int(len(c_n))))
    print(s, "done", flush=True)
pd.DataFrame(rows).to_csv(OUT / "counts_migration_matched_candidates.csv", index=False); pd.DataFrame(mult).to_csv(OUT / "candidate_multiplicity_matched_events.csv", index=False)
print(pd.DataFrame(mult).to_string(index=False))
