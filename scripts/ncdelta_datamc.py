#!/usr/bin/env python
"""Data-vs-MC plots + control-region composition of the frozen legacy chain (old fg1-era and Nov16). Statistical uncertainty only. Every beam-on request passes the data-policy gate.

    source env/setup_eaf.sh && python scripts/ncdelta_datamc.py [--productions old_fg1 nov16]
MC stack at the DATA exposure (open beam-on POT): dedicated NC-Delta sample (signal) + generic BNB CV categories (in-region natural NC-Delta events removed). Beam-off appears only as COUNTS in the control-region table (not drawn, never added to the stack: its scale is blocked, blocker G). Signal-region (final frozen) beam-on data are NOT shown unless the policy allows it.
"""
from ncdelta_purity_common import *
import argparse, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from sbnd_single_photon import plotstyle as PS
PS.apply_style()

VARS = [("c_shw_sp_energy", "selected-shower energy [MeV]", np.geomspace(20, 3000, 25), True), ("c_shw_sp_angle_beam", "shower angle to beam [deg]", np.linspace(0, 180, 19), False),
        ("c_shw_sp_shw_vtx_dis", "shower-to-vertex distance [cm]", np.linspace(0, 100, 21), False), ("c_kine_nu_x_corr", "reco vertex x [cm]", np.linspace(-220, 220, 23), False),
        ("c_kine_nu_y_corr", "reco vertex y [cm]", np.linspace(-220, 220, 23), False), ("c_kine_nu_z_corr", "reco vertex z [cm]", np.linspace(0, 520, 27), False),
        ("c_kine_reco_Enu", "reco neutrino energy [MeV]", np.linspace(0, 2500, 26), False), ("c_np35", "reco protons (>35 MeV)", np.arange(-0.5, 6.6, 1.0), False),
        ("c_lead_proton_ke_mev", "leading-proton KE [MeV]", np.linspace(35, 800, 18), False), ("c_flash_time_us", "matched flash time [us]", np.linspace(0.2, 2.2, 21), False),
        ("c_score_numu", "SP-numu score", np.linspace(-6, 4, 21), False), ("c_score_other", "SP-other score", np.linspace(-6, 4, 21), False),
        ("c_score_ncpi0", "SP-ncpi0 score", np.linspace(-4, 3, 22), False), ("c_score_nue", "SP-nue score", np.linspace(-6, 3, 19), False),
        ("c_shw_sp_min_dis", "min. shower-to-other-object distance [cm]", np.linspace(0, 200, 21), False)]
COL = {"SIGNAL_NCDELTA": "#F0E442", "NC_PI0": "#0072B2", "CC_PI0": "#56B4E9", "NUE_CC": "#009E73", "NUMU_CC": "#999999", "OTHER_NC": "#E69F00", "OTHER_CC": "#8C564B",
       "OUTSIDE_TPC_NU": "#CC79A7", "COSMIC_OR_UNMATCHED": "#444444", "MULTI_OR_AMBIGUOUS": "#CCCCCC"}
POT_DATA = {}
KIND = {"preselection": "preselection", "SB_numu": "sideband", "SB_other": "sideband", "SB_ncpi0": "sideband", "SB_nue": "sideband", "final_frozen": "signal_region"}
TOPOS = ("inclusive", "1g0p", "1gNp")


def collect(prod, cfg):
    sev, sc = load_signal(prod, cfg); cev, cc, cf = load_cv(prod, cfg); sig, nat = natural_signal_in_region()
    st_c = PU.event_stage_table(cc, KEY); rm = PU.remove_in_region_natural_signal(st_c, nat[KEY], KEY)
    rmk = set(map(tuple, st_c.loc[rm, KEY].to_numpy())); cc["cat"] = approx_category(cc, cev)
    cc["removed"] = [(a, b) in rmk for a, b in zip(cc.file_index.to_numpy(), cc.ev.to_numpy())]
    sk = set(map(tuple, sev[KEY].to_numpy())); sc["in_region"] = [(a, b) in sk for a, b in zip(sc.file_index.to_numpy(), sc.ev.to_numpy())]
    D = {}
    for s in ("beam_on_open", "beam_off"):
        e, c, f = load_data(prod, s, cfg); D[s] = (e, c, f)
    pot_data = float(D["beam_on_open"][2].total_pot.sum())
    return dict(sc=sc, cc=cc, D=D, pot_cv=float(cf.total_pot.sum()), pot_data=pot_data)


def rows(c, region, topo):
    return RG.region_mask(c, region) & RG.topology_mask(c, topo)


def comps(Z, region, topo, pot_target):
    sc, cc = Z["sc"], Z["cc"]; ms = rows(sc, region, topo) & sc.in_region.to_numpy(bool); mb = rows(cc, region, topo) & ~cc.removed.to_numpy(bool)
    out = {"SIGNAL_NCDELTA": (sc[ms], np.full(int(ms.sum()), pot_target / POT_SIGNAL))}
    b = cc[mb]
    for cat, g in b.groupby("cat"):
        out[cat] = (g, np.full(len(g), pot_target / Z["pot_cv"]))
    return out


def plot(prod, region, topo, Z, pot_data, outdir):
    kind = KIND[region]; show_data = DP.allowed("beam_on_open", kind)
    cm = comps(Z, region, topo, pot_data)
    dat = None
    if show_data:
        e, c, f = Z["D"]["beam_on_open"]; dat = c[rows(c, region, topo)]
    e, c, f = Z["D"]["beam_off"]; off = c[rows(c, region, topo)] if DP.allowed("beam_off", kind) else None
    fig = plt.figure(figsize=(17, 12)); gs = GridSpec(4, 4, figure=fig, hspace=0.55, wspace=0.28)
    tot_n = {}
    for k, (var, lab, bins, logx) in enumerate(VARS):
        sub = gs[k // 4, k % 4].subgridspec(2, 1, height_ratios=[3, 1], hspace=0.05); ax = fig.add_subplot(sub[0]); rx = fig.add_subplot(sub[1], sharex=ax)
        mc = {}
        for cat, (g, w) in cm.items():
            v = g[var].to_numpy(float)
            if var.startswith("c_kine_nu_") or var == "c_kine_reco_Enu":
                v = np.where((g.c_kine_nu_x_corr == 0) & (g.c_kine_nu_y_corr == 0) & (g.c_kine_nu_z_corr == 0), np.nan, v)      # (0,0,0) = no-vertex sentinel
            mc[cat] = DM.Component(cat, v, w)
        st = DM.build_stack(mc, bins); ctr = 0.5 * (bins[1:] + bins[:-1]); wd = np.diff(bins); bot = np.zeros(len(ctr))
        for cat in reversed(st["order"]):
            h = st["parts"][cat][0]; ax.bar(bins[:-1], h, wd, bottom=bot, align="edge", color=COL.get(cat, "#aaaaaa"), edgecolor="k" if cat == "SIGNAL_NCDELTA" else "none", lw=0.4, label=cat if k == 0 else None); bot += h
        ax.errorbar(ctr, st["total"], yerr=st["err"], fmt="none", ecolor="#222222", lw=0.6, capsize=0)
        if logx: ax.set_xscale("log")
        if dat is not None:
            dv = dat[var].to_numpy(float)
            if var.startswith("c_kine_nu_") or var == "c_kine_reco_Enu":
                dv = np.where((dat.c_kine_nu_x_corr == 0) & (dat.c_kine_nu_y_corr == 0) & (dat.c_kine_nu_z_corr == 0), np.nan, dv)
            n, _ = np.histogram(dv[np.isfinite(dv)], bins); lo, hi = DM.poisson_interval(n)
            ax.errorbar(ctr, n, yerr=[n - lo, hi - n], fmt="ko", ms=3, lw=0.8, label="open beam-on data" if k == 0 else None)
            r, rlo, rhi, mce = DM.ratio(n, st["total"], st["err"])
            rx.errorbar(ctr, r, yerr=[rlo, rhi], fmt="ko", ms=3, lw=0.8); rx.fill_between(bins.repeat(2)[1:-1], (1 - np.repeat(mce, 2)), (1 + np.repeat(mce, 2)), color="#888888", alpha=0.3, step=None)
            rx.axhline(1, color="k", lw=0.5); rx.set_ylim(0, 2.5); rx.set_ylabel("data/pred", fontsize=7)
            tot_n[var] = int(n.sum())
        else:
            rx.text(0.5, 0.5, "data not shown (policy)", transform=rx.transAxes, ha="center", fontsize=7, color="#a00"); rx.set_yticks([])
        ax.set_ylabel("candidates", fontsize=7); rx.set_xlabel(lab, fontsize=8); plt.setp(ax.get_xticklabels(), visible=False); ax.tick_params(labelsize=7); rx.tick_params(labelsize=7)
    h, l = fig.axes[0].get_legend_handles_labels(); fig.legend(h, l, loc="upper center", ncol=6, fontsize=8, frameon=False, bbox_to_anchor=(0.5, 0.955))
    pdat = f"{pot_data:.3g} POT" ; tit = {"old_fg1": "old fg1-era reconstruction", "nov16": "WCLocal2026Nov16"}[prod]
    fig.suptitle(f"{tit} | frozen legacy chain | region: {region} | reco topology: {topo} | MC scaled to open-data exposure {pdat} | statistical uncertainty only", fontsize=10, y=0.985)
    fig.text(0.01, 0.005, "candidate-level, all region-passing candidates; signal = dedicated NC-Delta sample; background = generic BNB CV (in-region natural NC-Delta events removed); NO cosmic-only (beam-off) component stacked; "
             "beam-off scale blocked. DIAGNOSTIC, not a Round-2 result.", fontsize=6.5, color="#555")
    name = f"datamc_{prod}_{region}_{topo}.png"; fig.savefig(outdir / name, dpi=110, bbox_inches="tight"); plt.close(fig); return name, tot_n


def control_table(prod, Z, pot_data):
    rows_ = []
    for region in ("preselection", "SB_numu", "SB_other", "SB_ncpi0", "SB_nue", "final_frozen"):
        kind = KIND[region]
        for topo in TOPOS:
            sc, cc = Z["sc"], Z["cc"]; ms = rows(sc, region, topo) & sc.in_region.to_numpy(bool); mb = rows(cc, region, topo) & ~cc.removed.to_numpy(bool)
            ns = sc[ms].groupby(KEY).ngroups; ev_b = cc[mb].groupby(KEY).cat.agg(lambda x: x.iloc[0] if x.nunique() == 1 else "MULTI_OR_AMBIGUOUS")
            wsig, wcv = POT_TARGET / POT_SIGNAL, POT_TARGET / Z["pot_cv"]; S = ns * wsig; B = len(ev_b) * wcv; top = ev_b.value_counts()
            row = dict(production=prod, region=region, region_kind=kind, topology=topo, N_signal_events=ns, S_per_1e20=S, N_cv_bkg_events=len(ev_b), B_per_1e20=B,
                       signal_contamination_S_over_SplusB=S / (S + B) if S + B > 0 else np.nan, dominant_bkg_category=(top.index[0] if len(top) else ""),
                       dominant_bkg_fraction=(float(top.iloc[0] / top.sum()) if len(top) else np.nan),
                       data_pot=pot_data, MC_pred_at_data_pot=(S + B) * pot_data / POT_TARGET)
            for cat in COL:
                if cat != "SIGNAL_NCDELTA":
                    row["B_" + cat + "_per_1e20"] = float(top.get(cat, 0) * wcv)
            for s_ in ("beam_on_open", "beam_off"):
                e, c, f = Z["D"][s_]; if_ok = DP.allowed(s_, kind)
                row[f"N_{s_}_events"] = (c[rows(c, region, topo)].groupby(RSE).ngroups if if_ok else "BLOCKED (data policy)")
            rows_.append(row)
    return pd.DataFrame(rows_)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--productions", nargs="+", default=list(PRODUCTIONS)); ap.add_argument("--regions", nargs="+", default=list(KIND)); a = ap.parse_args()
    cfg = load_cfg(); logs = []
    for prod in a.productions:
        Z = collect(prod, cfg); pot = Z["pot_data"]; POT_DATA[prod] = pot
        ct = control_table(prod, Z, pot); ct.to_csv(TAB / f"control_region_composition_{prod}.csv", index=False)
        for region in a.regions:
            for topo in TOPOS:
                name, n = plot(prod, region, topo, Z, pot, PLT); logs.append(dict(production=prod, region=region, topology=topo, file=name, data_candidates_first_var=next(iter(n.values()), None)))
                print(name, flush=True)
    pd.DataFrame(logs).to_csv(TAB / "datamc_plot_index.csv", index=False)
