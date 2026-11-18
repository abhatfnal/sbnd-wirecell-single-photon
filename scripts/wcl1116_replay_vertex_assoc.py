#!/usr/bin/env python
"""Association (not causation) between the per-event vertex change and the frozen-selection change, dedicated NC-Delta sample, Nov16 vs old. Truth is used for evaluation only.

    source env/setup_eaf.sh && python scripts/wcl1116_replay_vertex_assoc.py
Classes use the nearest-candidate reco-to-true vertex distance in each production: improved (> 1 cm closer), unchanged (within 1 cm), worsened (> 1 cm farther); events lacking a valid vertex in either production are 'no vertex'.
"""
from wcl1116_replay_common import *

CLS = {0: "0p", 1: "1p", 2: ">=2p"}
vo, vn = pd.read_parquet(DER / "signal_vtx_old.parquet"), pd.read_parquet(DER / "signal_vtx_new.parquet")
near = lambda v: v.dropna(subset=["dist"]).groupby(RSE).dist.min().rename("d")
d = pd.concat([near(vo).rename("d_old"), near(vn).rename("d_new")], axis=1).reset_index()
M = pd.read_parquet(DER / "signal_migration_events.parquet").merge(d, on=RSE, how="left")
delta = M.d_old - M.d_new
M["vertex_change"] = np.select([M.d_old.isna() | M.d_new.isna(), delta > 1, delta < -1], ["no valid vertex in one production", "improved (>1 cm closer)", "worsened (>1 cm farther)"], "unchanged (within 1 cm)")
M["new_within_5cm"] = np.where(M.d_new.isna(), "no vertex", np.where(M.d_new < 5, "new vertex < 5 cm", "new vertex >= 5 cm"))
rows = []
for col in ("vertex_change", "new_within_5cm"):
    for g, t in M.groupby(col):
        po = t.migration.str.startswith("old pass"); pn = t.migration.str.endswith("new pass")
        rows.append(dict(split=col, cls=g, n_events=len(t), old_selected=int(po.sum()), new_selected=int(pn.sum()), old_eff_pct=100 * po.mean(), new_eff_pct=100 * pn.mean(),
                         old_pass_new_fail=int((t.migration == "old pass -> new fail").sum()), old_fail_new_pass=int((t.migration == "old fail -> new pass").sum())))
T = pd.DataFrame(rows); T.to_csv(OUT / "signal_vertex_change_vs_selection.csv", index=False); print(T.round(2).to_string(index=False))
# by topology within the 'improved' class
rows = []
for k, nm in CLS.items():
    t = M[M.truth_cat == k]
    for g, tt in t.groupby("vertex_change"):
        rows.append(dict(topology=nm, vertex_change=g, n_events=len(tt), old_eff_pct=100 * tt.migration.str.startswith("old pass").mean(), new_eff_pct=100 * tt.migration.str.endswith("new pass").mean()))
pd.DataFrame(rows).to_csv(OUT / "signal_vertex_change_vs_selection_by_topology.csv", index=False)
