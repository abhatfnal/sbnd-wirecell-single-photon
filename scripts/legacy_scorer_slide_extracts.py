#!/usr/bin/env python
"""Small committed extracts for the corrected presentation (no new analysis; definitions unchanged; no ROOT).

    source env/setup_eaf.sh && python scripts/legacy_scorer_slide_extracts.py
Writes into tables/legacy_scorer_correction/:
  vertex_resolution_subset.csv   |V_reco - V_true| of the objects still selected under the source-faithful scorer (restriction of the stored Phase-11 selected-object table; the as-run restriction
                                 reproduces the committed 2.02 / 11.57 / 0.929 cm exactly, which is asserted)
  delta_mass_residuals.csv       M_reco - M_true_decay of the decay pairs of both configurations (the 251 corrected values; as-run 348), for the histogram
  source_faithful/differential_efficiency/slide_extract.csv   final efficiency per bin (photon energy, cos theta, vtx z) + interior / edge, from the rebuilt differential tables
"""
import os, sys, warnings
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
SPD = Path(os.environ["SP_DATA"]); SPC = SPD / "legacy_scorer_correction"; OUT = REPO / "tables" / "legacy_scorer_correction"
d = pd.read_parquet(SPD / "common_observables" / "official_ncdelta" / "selected_object_table.parquet")
arr = pd.read_parquet(SPD / "official_signal_baseline" / "signal_joined_active_tpc.parquet")[["file_index", "ev", "x", "y", "z", "truth_cat"]]
m = d.merge(arr, on=["file_index", "ev"], how="inner"); assert len(m) == len(d) == 1153
m["dv"] = np.sqrt((m.vtx_x - m.x) ** 2 + (m.vtx_y - m.y) ** 2 + (m.vtx_z - m.z) ** 2)
rows = []
for cfg in ("A_old", "D_full"):
    c = pd.read_parquet(SPC / f"official_candidates_{cfg}.parquet", columns=["file_index", "ev", "c_nu_index", "pass_final"]); c = c[c.pass_final].rename(columns={"c_nu_index": "cand"})
    s = m.merge(c[["file_index", "ev", "cand"]].assign(_s=True), on=["file_index", "ev", "cand"], how="left"); s = s[s._s.fillna(False).astype(bool)]
    for lab, mk in (("all", np.ones(len(s), bool)), ("truth 0p", (s.truth_cat == 0).values), ("truth 1p", (s.truth_cat == 1).values), ("truth >=2p", (s.truth_cat == 2).values)):
        v = s.dv.to_numpy()[mk]; rows.append(dict(config=cfg, group=lab, n=int(mk.sum()), median_cm=float(np.median(v)), p16_cm=float(np.percentile(v, 16)), p84_cm=float(np.percentile(v, 84)), frac_within_5cm=float((v < 5).mean())))
V = pd.DataFrame(rows); V.to_csv(OUT / "vertex_resolution_subset.csv", index=False)
a = V[V.config == "A_old"].set_index("group"); assert (a.loc["all", "n"], round(a.loc["all", "median_cm"], 2), round(a.loc["truth 0p", "median_cm"], 2), round(a.loc["truth 1p", "median_cm"], 3)) == (1153, 2.02, 11.57, 0.929)
print(V.round(3).to_string())
# Delta-mass residuals
dm = pd.read_parquet(SPD / "common_observables" / "official_ncdelta" / "delta_mass_table.parquet"); dm = dm[dm.policy == "any"]
out = []
for cfg in ("A_old", "D_full"):
    c = pd.read_parquet(SPC / f"official_candidates_{cfg}.parquet", columns=["file_index", "ev", "c_nu_index", "pass_final"]); c = c[c.pass_final].rename(columns={"c_nu_index": "cand"})
    s = dm.merge(c[["file_index", "ev", "cand"]].assign(_s=True), on=["file_index", "ev", "cand"], how="left"); s = s[s._s.fillna(False).astype(bool)]
    s = s[(s["baseline_35__mass_status"] == "ok") & (s["baseline_35__pair_class"] == "decay_pair")]
    out.append(pd.DataFrame(dict(config=cfg, residual_mev=(s["baseline_35__m_delta"] - s["m_true_decay"]).to_numpy(float))))
R = pd.concat(out); R.to_csv(OUT / "delta_mass_residuals.csv", index=False); print(R.groupby("config").residual_mev.agg(["count", "median"]))
# differential extract
T = lambda tag: pd.read_csv(SPD / tag / "official_ncdelta" / "tables" / "efficiency_differential.csv")
n = T("differential_efficiency_source_faithful"); o = T("differential_efficiency")
rows = []
for cfg, t in (("A_old", o), ("D_full", n)):
    for v in ("photon_energy_mev", "cos_theta_beam", "vtx_z"):
        g = t[(t.variable == v) & (t.group == "all") & (t.stage == "final")]
        for r in g.itertuples():
            rows.append(dict(config=cfg, variable=v, bin=int(r.bin), lo=r.lo, hi=r.hi, denominator=int(r.denominator), selected=int(r.numerator), efficiency=r.efficiency, lo68=r.lo68, hi68=r.hi68))
    ie = pd.read_csv(SPD / ("differential_efficiency" if cfg == "A_old" else "differential_efficiency_source_faithful") / "official_ncdelta" / "tables" / "efficiency_interior_vs_edge.csv"); ie = ie[(ie.group == "all") & (ie.stage == "final")]
    for r in ie.itertuples():
        rows.append(dict(config=cfg, variable=r.region, bin=-1, lo=np.nan, hi=np.nan, denominator=int(r.denominator), selected=int(r.numerator), efficiency=r.efficiency, lo68=r.lo68, hi68=r.hi68))
(OUT / "source_faithful" / "differential_efficiency").mkdir(parents=True, exist_ok=True); pd.DataFrame(rows).to_csv(OUT / "source_faithful" / "differential_efficiency" / "slide_extract.csv", index=False)
