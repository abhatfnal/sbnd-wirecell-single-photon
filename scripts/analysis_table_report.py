#!/usr/bin/env python
"""Baseline plot suite + 1g0p/1g1p background characterisation from the DERIVED TABLE ONLY (no CAF is opened). PROVISIONAL.

    python scripts/analysis_table_report.py bnb_cv [--tables-dir tables/analysis_table] [--plots-dir plots/analysis_table]

Normalisation: entries are weighted by 1e20 / sum(TotalPOT) = "per 1e20 generated POT" of the official FILTERED Gen2 CV
(neutrino-induced backgrounds ONLY; cosmic-only backgrounds are not represented and must come from beam-off; docs/analysis/POT_EXPOSURE_AUDIT.md).
No data/MC stack. Nothing here is optimised; cut lines are the frozen baseline thresholds. Reco-0p = 1g0p, reco-1p = 1g1p; >=2p is diagnostic.
Poisson errors are on raw counts only (no weights, no systematics).
"""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src"))
from sbnd_single_photon import truth as T, selection as SEL  # noqa: E402

BANNER = ("PROVISIONAL | neutrino-induced backgrounds of the official filtered Gen2 CV, per 1e20 generated POT | "
          "cosmic-only backgrounds NOT included | no data/MC stack | no FV")
ORDER = ["NC_PI0", "NUE_CC", "CC_PI0", "DIRT_NO_ACTIVE", "MULTI_ACTIVE", "OTHER_NC", "NUMU_CC", "OTHER_CC", "OTHER", "COSMIC_NO_NU"]
COLORS = dict(NC_PI0="#0072B2", NUE_CC="#D55E00", CC_PI0="#009E73", DIRT_NO_ACTIVE="#999999", MULTI_ACTIVE="#CC79A7",
              OTHER_NC="#56B4E9", NUMU_CC="#E69F00", OTHER_CC="#F0E442", OTHER="#000000", COSMIC_NO_NU="#7F3C8D")
CH = {0: "1g0p (reco 0p)", 1: "1g1p (reco 1p)", 2: "diagnostic: reco >=2p"}
VMAX = 50.0     # DISPLAY ONLY: dQ/dx columns carry sentinels (100 for lowest_dQ_dx, 6.25e9 for vec_dQ_dx_0); values >= VMAX are not drawn. No table value or cut is changed.
CUTS = {"c_score_numu": 0.4, "c_score_other": 0.2, "c_score_ncpi0": -0.05}
VARS = [  # label, column, bins (None -> percentile-auto), filled-only
    ("numu BDT score", "c_score_numu", np.linspace(-1, 1, 41)), ("other BDT score", "c_score_other", np.linspace(-1, 1, 41)),
    ("ncpi0 BDT score", "c_score_ncpi0", np.linspace(-1, 1, 41)), ("nue BDT score", "c_score_nue", np.linspace(-1, 1, 41)),
    ("n 20 MeV showers", "c_shw_sp_n_20mev_showers", np.arange(-.5, 7.5, 1)), ("n 20br1 showers", "c_shw_sp_n_20br1_showers", np.arange(-.5, 7.5, 1)),
    ("reco vertex x [cm]", "c_kine_nu_x_corr", np.linspace(-250, 250, 41)), ("reco vertex y [cm]", "c_kine_nu_y_corr", np.linspace(-250, 250, 41)),
    ("reco vertex z [cm]", "c_kine_nu_z_corr", np.linspace(-50, 550, 41)),
    ("main shower energy shw_sp_energy [MeV]", "c_shw_sp_energy", np.linspace(0, 1500, 41)),
    ("shower-vertex distance shw_sp_shw_vtx_dis [cm]", "c_shw_sp_shw_vtx_dis", np.linspace(0, 100, 41)),
    ("shw_sp_lowest_dQ_dx", "c_shw_sp_lowest_dQ_dx", None), ("shw_sp_medium_dQ_dx", "c_shw_sp_medium_dQ_dx", None),
    ("shw_sp_vec_dQ_dx_0 (first segment)", "c_shw_sp_vec_dQ_dx_0", None),
    ("reco protons (KE>35 MeV) per candidate", "c_np35", np.arange(-.5, 6.5, 1)),
    ("leading reco proton KE [MeV]", "c_lead_proton_ke_mev", np.linspace(35, 635, 41)),
    ("matched flash time [us]", "c_flash_time_us", np.linspace(-1, 4, 41)), ("reco E_nu kine_reco_Enu [MeV]", "c_kine_reco_Enu", np.linspace(0, 3000, 41)),
]


def stack(ax, df, col, bins, w, log=False):
    bot = np.zeros(len(bins) - 1)
    for cat in ORDER:
        v = df.loc[df.cat == cat, col].values; v = v[np.isfinite(v)]
        if "dQ_dx" in col: v = v[v < VMAX]
        if not len(v): continue
        h, _ = np.histogram(v, bins=bins); h = h * w
        ax.stairs(bot + h, bins, baseline=bot, fill=True, color=COLORS[cat], label=f"{cat} ({int((df.cat == cat).sum())})", lw=0)
        bot = bot + h
    ax.set_ylabel("per 1e20 gen. POT / bin", fontsize=7); ax.tick_params(labelsize=7)
    if log:
        ax.set_yscale("log"); ax.set_ylim(bottom=0.5 * w)


def auto_bins(series, n=40):
    v = series.values[np.isfinite(series.values)]
    if "dQ_dx" in str(series.name): v = v[v < VMAX]
    lo, hi = (np.percentile(v, [1, 99]) if len(v) > 10 else (0, 1))
    return np.linspace(lo, hi if hi > lo else lo + 1, n + 1)


def grid(df, w, title, path, log=False, sub=None):
    fig, axs = plt.subplots(5, 4, figsize=(19, 15)); axs = axs.ravel()
    for ax, (lab, col, bins) in zip(axs, VARS):
        d = df if sub is None else df[sub]
        if col not in d or not np.isfinite(d[col].values).any():
            ax.set_visible(False); continue
        b = bins if bins is not None else auto_bins(d[col])
        stack(ax, d, col, b, w, log)
        ax.set_xlabel(lab + (f"  [values >= {VMAX:g} are sentinels, not drawn]" if "dQ_dx" in col else ""), fontsize=8)
        if col in CUTS: ax.axvline(CUTS[col], color="k", ls="--", lw=.8)
    for ax in axs[len(VARS):]: ax.set_visible(False)
    h, l = axs[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower right", ncol=2, fontsize=9, title="event truth category (raw counts)")
    fig.suptitle(f"{title}\n{BANNER}", fontsize=10, color="firebrick"); fig.tight_layout(rect=(0, 0, 1, .95))
    fig.savefig(path, dpi=70); plt.close(fig)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("sample")
    ap.add_argument("--root", default=os.path.join(os.environ.get("SP_DATA", "/tmp"), "analysis_tables"))
    ap.add_argument("--tables-dir", default=str(REPO / "tables" / "analysis_table")); ap.add_argument("--plots-dir", default=str(REPO / "plots" / "analysis_table"))
    a = ap.parse_args()
    d = Path(a.root) / a.sample
    c, e, fl = (pd.read_parquet(d / f"{n}.parquet") for n in ("candidates", "events", "files"))
    cfg = SEL.load_config(); first_cut = "cum_" + cfg["cuts"][0]["name"]
    pot = float(fl.total_pot.sum()); w = 1e20 / pot
    c["cat"] = np.array(T.CATEGORIES)[e.t_code.values[c.gev.values].astype(int)]
    tdir, pdir = Path(a.tables_dir), Path(a.plots_dir); tdir.mkdir(parents=True, exist_ok=True); pdir.mkdir(parents=True, exist_ok=True)
    pre = c[c[first_cut]]; fin = c[c.pass_final]
    out = {"pot_total": pot, "per": "1e20 generated POT"}
    # ---------------- plots (derived table only)
    grid(c[c.cum_candidate_in_valid_event], w, f"{a.sample}: all candidates of wc.valid events", pdir / f"{a.sample}_valid_candidates.png", log=True)
    grid(pre, w, f"{a.sample}: preselection (>=1 shower above 20 MeV; frozen first cut)", pdir / f"{a.sample}_preselection.png", log=True)
    grid(fin, w, f"{a.sample}: final selection (frozen baseline chain, policy any)", pdir / f"{a.sample}_final_all_proton.png")
    for k, nm in ((0, "1g0p"), (1, "1g1p")):
        grid(fin, w, f"{a.sample}: final selection, {CH[k]}", pdir / f"{a.sample}_final_{nm}.png", sub=(fin.reco_proton_cat == k).values)
    grid(fin, w, f"{a.sample}: final selection, {CH[2]}", pdir / f"{a.sample}_final_ge2p_diag.png", sub=(fin.reco_proton_cat == 2).values)
    # ---------------- channel summaries (both policies)
    rows, comp, qrows = [], [], []
    for pol in ("any", "first"):
        s = fin if pol == "any" else fin[fin.policy_first.values]
        s = s.sort_values(["gev", "c_nu_index"]).drop_duplicates("gev")          # one candidate per event (lowest nu_index passing)
        for k in (0, 1, 2):
            g = s[s.reco_proton_cat == k]; n = len(g)
            rows.append(dict(policy=pol, channel=CH[k], n_selected_events=n, per_1e20_genPOT=n * w, err_per_1e20_genPOT=np.sqrt(n) * w))
            for cat in ORDER:
                m = int((g.cat == cat).sum())
                if m: comp.append(dict(policy=pol, channel=CH[k], category=cat, n=m, fraction=m / n, per_1e20_genPOT=m * w, err_per_1e20_genPOT=np.sqrt(m) * w))
            for lab, col, _ in VARS:
                v = g[col].values.astype(float); v = v[np.isfinite(v)]
                if "dQ_dx" in col: v = v[v < VMAX]
                if len(v):
                    q = np.percentile(v, [5, 25, 50, 75, 95])
                    qrows.append(dict(policy=pol, channel=CH[k], variable=col, n=len(v), mean=v.mean(), q05=q[0], q25=q[1], q50=q[2], q75=q[3], q95=q[4]))
            # vertex position relative to the PROVISIONAL TPC box (descriptive; NOT a fiducial volume)
            x, y, z = g.c_kine_nu_x_corr.values, g.c_kine_nu_y_corr.values, g.c_kine_nu_z_corr.values
            has_v = ~((x == 0) & (y == 0) & (z == 0))
            out.setdefault("vertex_diag", {})[f"{pol}/{CH[k]}"] = dict(n=n, default_000_vertex=int((~has_v).sum()),
                outside_provisional_tpc_box=int((has_v & ~((abs(x) < 200) & (abs(y) < 200) & (z > 0) & (z < 500))).sum()))
            out.setdefault("proton_diag", {})[f"{pol}/{CH[k]}"] = dict(np35_hist=np.bincount(np.clip(g.c_np35.values.astype(int), 0, 6), minlength=7).tolist(),
                n_with_lead_proton=int(np.isfinite(g.c_lead_proton_ke_mev.values).sum()))
    pd.DataFrame(rows).to_csv(tdir / f"{a.sample}_channel_summary.csv", index=False)
    pd.DataFrame(comp).to_csv(tdir / f"{a.sample}_channel_composition.csv", index=False)
    pd.DataFrame(qrows).to_csv(tdir / f"{a.sample}_channel_variable_quantiles.csv", index=False)
    (tdir / f"{a.sample}_channel_diagnostics.json").write_text(json.dumps(out, indent=1))
    print(pd.DataFrame(rows).to_string())
    cdf = pd.DataFrame(comp)
    if len(cdf): print(cdf[cdf.policy == "any"][["channel", "category", "n", "fraction"]].to_string())


if __name__ == "__main__":
    main()
