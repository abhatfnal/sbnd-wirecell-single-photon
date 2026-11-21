#!/usr/bin/env python
"""DIAGNOSIS ONLY (no selection change, no tuning, no data-driven correction): NC-pi0-rich sideband, reconstructed 1g0p / 1g1p / >=2p Data/MC, old reconstruction vs WCLocal2026Nov16.

    source env/setup_eaf.sh && python scripts/ncdelta_ncpi0_topology_diag.py

Unit = event (lowest-index region-passing candidate; same event set and owner/removal logic as the weight extraction: regions_plan_{prod}.pkl). Prediction = S + B at the open-data POT,
nominal weights, MC only (NO cosmic-only component). Uncertainties here are data + MC statistics ONLY. Detector, proton-reconstruction, cosmic/beam-off, dirt, POT, imp_weight and the
neutrino-weight covariance are NOT in these per-topology comparisons (the neutrino covariance is a ~20 % mostly-normalisation mode: see the double ratio, which cancels it to first order).
Only variables stored in the analysis tables are used; pair-level pi0 observables need a new CAF extraction (not done here).
"""
import pickle, json
from scipy import stats
from ncdelta_syst_common import *
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

R = "SB_ncpi0"; TAB = REPO / "tables" / "ncdelta_purity_datamc"; PLT = REPO / "plots" / "ncdelta_purity_datamc"
TOPO = ["1g0p", "1g1p", ">=2p"]; AV = dict(x=(-200., 200.), y=(-200., 200.), z=(0., 500.))
COLS = ["c_nu_index", "c_shw_sp_energy", "c_shw_sp_shw_vtx_dis", "c_shw_sp_min_dis", "c_shw_sp_angle_beam", "c_shw_sp_medium_dQ_dx", "c_kine_nu_x_corr", "c_kine_nu_y_corr", "c_kine_nu_z_corr",
        "c_np35", "c_np_any_ke", "c_lead_proton_ke_mev", "c_sum_proton_ke_mev", "c_score_ncpi0", "c_score_numu", "c_score_other", "c_flash_pe"]


def rep(c, mask, keep_keys):
    """Representative candidate per event (lowest c_nu_index among region-passing), restricted to keep_keys."""
    s = c.loc[mask, KEY + RUN + COLS].sort_values(KEY + ["c_nu_index"]).groupby(KEY).first().reset_index()
    s = s.merge(keep_keys, on=KEY, how="inner", validate="one_to_one")
    s["topo"] = np.clip(s.c_np35.to_numpy(int), 0, 2)
    x, y, z = s.c_kine_nu_x_corr.to_numpy(float), s.c_kine_nu_y_corr.to_numpy(float), s.c_kine_nu_z_corr.to_numpy(float)
    s["d_edge"] = np.min([x - AV["x"][0], AV["x"][1] - x, y - AV["y"][0], AV["y"][1] - y, z - AV["z"][0], AV["z"][1] - z], axis=0)       # signed distance to the TPC box faces (cm); < 0 = outside
    return s


def load(prod):
    cfg = load_cfg(); plan = pickle.load(open(SYST / f"regions_plan_{prod}.pkl", "rb")); out = {}
    cev, cc, _ = load_cv(prod, cfg); sev, sc = load_signal(prod, cfg); de, dc, _ = load_data(prod, "beam_on_open", cfg)
    sk = set(map(tuple, sev[KEY].dropna().astype(int).to_numpy())); sc["in_region"] = [(a, b) in sk for a, b in zip(sc.file_index.to_numpy(), sc.ev.to_numpy())]
    out["B"] = rep(cc, RG.region_mask(cc, R), plan["B"][R][KEY + ["cat", "resolved"]])
    out["S"] = rep(sc, RG.region_mask(sc, R) & sc.in_region.to_numpy(bool), plan["S"][R][KEY])
    out["D"] = rep(dc, RG.region_mask(dc, R), plan["D"][R][KEY])
    assert len(out["B"]) == len(plan["B"][R]) and len(out["S"]) == len(plan["S"][R]) and len(out["D"]) == len(plan["D"][R])
    out["wS"], out["wB"] = plan["pot_data"] / POT_SIGNAL, plan["pot_data"] / plan["pot_cv"]
    return out


def hist(d, col, edges, sel=None):
    """Return data counts, MC prediction, MC stat variance, S prediction, B prediction on `edges` (tails merged)."""
    def one(t, w):
        v = d[t]; v = v if sel is None else v[sel(v)]
        x = np.clip(v[col].to_numpy(float), edges[0] + 1e-9, edges[-1] - 1e-9); n = np.histogram(x, edges)[0].astype(float); return n, n * w, n * w * w
    nd = one("D", 1.0)[0]; ns, ps, vs = one("S", d["wS"]); nb, pb, vb = one("B", d["wB"])
    return nd, ps + pb, vs + vb, ps, pb


def ratio_row(nd, mc, var):
    r = nd / mc; e = r * np.sqrt(1 / np.maximum(nd, 1) + var / mc ** 2); return r, e


def main():
    D = {p: load(p) for p in PRODUCTIONS}; rows = []; mig_rows = []
    # ---------- 1. topology composition (0p / 1p / >=2p) ----------
    for p, d in D.items():
        nd, mc, var, ps, pb = hist(d, "topo", np.arange(4) - 0.5)
        r, e = ratio_row(nd, mc, var)
        for i, t in enumerate(TOPO):
            rows.append(dict(production=p, view="topology", bin=t, data=int(nd[i]), mc=mc[i], mc_S=ps[i], mc_B=pb[i], ratio=r[i], err_data_mc_stat=e[i], frac_data=nd[i] / nd.sum(), frac_mc=mc[i] / mc.sum()))
        # shape-only (composition) chi2: MC normalised to data total; multinomial data covariance + MC stat; drop last bin
        Pn = mc / mc.sum(); Dn = nd.sum(); C = Dn * (np.diag(Pn) - np.outer(Pn, Pn)); C = C + np.diag((Dn / mc.sum()) ** 2 * var)       # (approximate) MC-stat on the normalised prediction
        dv = (nd - Dn * Pn)[:-1]; chi2 = float(dv @ np.linalg.solve(C[:-1, :-1], dv)); ndof = 2
        # double ratio Np/0p and 1p/0p, 2p/0p (normalisation-free)
        dr = {}
        for k, lab in ((1, "1p/0p"), (2, ">=2p/0p")):
            Rd = nd[k] / nd[0]; Rm = mc[k] / mc[0]; err = (Rd / Rm) * np.sqrt(1 / nd[k] + 1 / nd[0] + var[k] / mc[k] ** 2 + var[0] / mc[0] ** 2); dr[lab] = (Rd / Rm, err)
        Nd, Nm = nd[1:].sum(), mc[1:].sum(); vNm = var[1:].sum(); Rd = Nd / nd[0]; Rm = Nm / mc[0]
        dr["Np/0p"] = (Rd / Rm, (Rd / Rm) * np.sqrt(1 / Nd + 1 / nd[0] + vNm / Nm ** 2 + var[0] / mc[0] ** 2))
        for k, (v, er) in dr.items(): rows.append(dict(production=p, view="double_ratio_data/MC", bin=k, ratio=v, err_data_mc_stat=er, n_sigma_from_1=(v - 1) / er))
        rows.append(dict(production=p, view="topology_shape_only_chi2", bin="3 bins", ratio=chi2, err_data_mc_stat=ndof, n_sigma_from_1=stats.chi2.sf(chi2, ndof)))   # ratio=chi2, err=ndof, n_sigma=p (see CSV note)
        print(p, "topology data", nd.astype(int), "MC", np.round(mc, 1), "ratio", np.round(r, 3), "shape chi2/ndof %.2f/2 p=%.4f" % (chi2, stats.chi2.sf(chi2, 2)), {k: tuple(np.round(v, 3)) for k, v in dr.items()})
    # ---------- 2. truth composition (MC categories) of each reco topology ----------
        b = d["B"]; cat = b.assign(cat2=np.where(b.cat.isin(["NC_PI0"]), "NC_PI0", np.where(b.cat.isin(["CC_PI0"]), "CC_PI0", np.where(b.cat.isin(["OUTSIDE_TPC_NU"]), "OUTSIDE_TPC_NU", "other")))).groupby(["topo", "cat2"]).size().unstack(fill_value=0) * d["wB"]
        cat.index = TOPO; cat.to_csv(TAB / f"ncpi0_topology_mc_truth_composition_{p}.csv"); print(p, "B truth composition by reco topology (weighted):\n", cat.round(1))
    # ---------- 3. 0p <-> Np migration old -> Nov16 (same events reprocessed) ----------
    for kind in ("D", "B"):
        a, b = D["old_fg1"][kind], D["nov16"][kind]
        # events can enter/leave the region; migration over events present in both, with 'not in region' as its own row/col
        ka = a.set_index(RUN).topo; kb = b.set_index(RUN).topo
        ka = ka[~ka.index.duplicated()]; kb = kb[~kb.index.duplicated()]
        al = pd.concat([ka.rename("old"), kb.rename("nov16")], axis=1)
        lab = {0: "0p", 1: "1p", 2: ">=2p"}; M = pd.crosstab(al.old.map(lab).fillna("not in region"), al.nov16.map(lab).fillna("not in region"))
        M.to_csv(TAB / f"ncpi0_topology_migration_old_to_nov16_{kind}.csv"); print("migration old->Nov16 (", kind, "; rows old, cols Nov16)\n", M)
        both = al.dropna(); tot = len(both); mv = (both.old != both.nov16).sum()
        mig_rows.append(dict(sample=kind, n_in_both=tot, n_topology_changed=int(mv), frac_changed=mv / max(tot, 1), n_np_to_0p=int(((both.old >= 1) & (both.nov16 == 0)).sum()), n_0p_to_np=int(((both.old == 0) & (both.nov16 >= 1)).sum())))
    pd.DataFrame(mig_rows).to_csv(TAB / "ncpi0_topology_migration_summary.csv", index=False); print(pd.DataFrame(mig_rows))
    # ---------- 4. variables, per topology; shape comparisons (stat only) ----------
    VAR = {"c_shw_sp_energy": ("shower energy [MeV]", np.geomspace(20, 3000, 9)), "c_lead_proton_ke_mev": ("leading proton KE [MeV] (>=35 MeV)", np.array([35, 70, 105, 140, 200, 300, 450, 1500.])),
           "c_sum_proton_ke_mev": ("sum of proton KE [MeV]", np.array([0, 1e-6, 50, 100, 200, 300, 500, 1500.])), "c_np_any_ke": ("# protons at any KE", np.arange(0, 6) - 0.5),
           "c_shw_sp_shw_vtx_dis": ("shower-vertex distance [cm]", np.array([0, 2, 5, 10, 20, 40, 80, 400.])), "d_edge": ("distance to TPC box face [cm]", np.array([-400, 0, 10, 25, 50, 100, 200, 500.])),
           "c_shw_sp_angle_beam": ("shower angle to beam [deg]", np.linspace(0, 180, 7)),
           "c_kine_nu_z_corr": ("vertex z [cm]", np.linspace(0, 500, 6)), "c_kine_nu_x_corr": ("vertex x [cm]", np.linspace(-200, 200, 6)), "c_kine_nu_y_corr": ("vertex y [cm]", np.linspace(-200, 200, 6))}
    out = []; fig, axs = plt.subplots(len(VAR), 4, figsize=(15, 2.5 * len(VAR)))
    for vi, (col, (lab, edges)) in enumerate(VAR.items()):
        for ti, (p, sel_name) in enumerate([(p, s) for p in PRODUCTIONS for s in ("0p", "Np")]):
            d = D[p]; sel = (lambda v: v.topo == 0) if sel_name == "0p" else (lambda v: v.topo >= 1)
            if col in ("c_lead_proton_ke_mev", "c_sum_proton_ke_mev") and sel_name == "0p": axs[vi, ti].axis("off"); continue
            nd, mc, var, ps, pb = hist(d, col, edges, sel)
            tot_r = nd.sum() / mc.sum(); mcn = mc * tot_r; varn = var * tot_r ** 2          # shape-only: MC scaled to data total
            ok = mcn > 0; chi2 = float((((nd - mcn) ** 2) / (mcn + varn))[ok].sum()); ndof = int(ok.sum() - 1)
            out.append(dict(production=p, topology=sel_name, variable=col, data=int(nd.sum()), mc=mc.sum(), norm_ratio=tot_r, shape_chi2_stat_only=chi2, ndof=ndof, p=stats.chi2.sf(chi2, ndof) if ndof > 0 else np.nan))
            ax = axs[vi, ti]; xs = np.arange(len(nd)); ax.bar(xs, mcn, width=0.9, color="#bbbbbb", label="MC (S+B), scaled to data"); ax.errorbar(xs, nd, yerr=np.sqrt(nd), fmt="ko", ms=3, label="data")
            ax.set_xticks(xs); ax.set_xticklabels([f"{edges[i]:.3g}" for i in range(len(nd))], fontsize=6, rotation=45); ax.set_title(f"{p} 1g{sel_name}: {lab}  (norm {tot_r:.2f}, shape p={out[-1]['p']:.2g})", fontsize=7)
    axs[0, 0].legend(fontsize=6); fig.text(0.01, 0.002, "DIAGNOSTIC / PRELIMINARY: NC-pi0 sideband, MC scaled to data per panel (shape only), stat errors only; no detector/proton-reco systematics; no cosmic-only MC", fontsize=7, color="#555")
    fig.tight_layout(rect=(0, 0.01, 1, 1)); fig.savefig(PLT / "H_ncpi0_topology_variables.png", dpi=110); plt.close(fig)
    pd.DataFrame(out).to_csv(TAB / "ncpi0_topology_variable_shapes.csv", index=False); print(pd.DataFrame(out).round(3).to_string())
    pd.DataFrame(rows).to_csv(TAB / "ncpi0_topology_datamc.csv", index=False)
    # ---------- 5. sub-threshold proton content of reco-0p events and data/MC ratio vs distance to edge ----------
    sub = []
    for p, d in D.items():
        for lab, sel in (("0p, no proton at any KE", lambda v: (v.topo == 0) & (v.c_np_any_ke == 0)), ("0p, >=1 sub-threshold proton", lambda v: (v.topo == 0) & (v.c_np_any_ke > 0)), ("Np", lambda v: v.topo >= 1)):
            nd = sel(d["D"]).sum(); mc = sel(d["S"]).sum() * d["wS"] + sel(d["B"]).sum() * d["wB"]; var = sel(d["S"]).sum() * d["wS"] ** 2 + sel(d["B"]).sum() * d["wB"] ** 2
            sub.append(dict(production=p, subset=lab, data=int(nd), mc=mc, ratio=nd / mc, err=nd / mc * np.sqrt(1 / max(nd, 1) + var / mc ** 2)))
        for lab, sel in (("d_edge<25 cm", lambda v: v.d_edge < 25), ("d_edge>=25 cm", lambda v: v.d_edge >= 25)):
            for tn, ts in (("0p", lambda v: v.topo == 0), ("Np", lambda v: v.topo >= 1)):
                f = lambda v: sel(v) & ts(v); nd = f(d["D"]).sum(); mc = f(d["S"]).sum() * d["wS"] + f(d["B"]).sum() * d["wB"]; var = f(d["S"]).sum() * d["wS"] ** 2 + f(d["B"]).sum() * d["wB"] ** 2
                sub.append(dict(production=p, subset=f"{tn}, {lab}", data=int(nd), mc=mc, ratio=nd / mc, err=nd / mc * np.sqrt(1 / max(nd, 1) + var / mc ** 2)))
    pd.DataFrame(sub).to_csv(TAB / "ncpi0_topology_subsets.csv", index=False); print(pd.DataFrame(sub).round(3).to_string())


if __name__ == "__main__":
    main()
