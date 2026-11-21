#!/usr/bin/env python
"""DIAGNOSTIC analysis of the NC-pi0 sideband (SB_ncpi0) reco-topology discrepancy using the CAF extraction `ncdelta_ncpi0_topology_extract.py`. NO tuning, NO correction.

    source env/setup_eaf.sh && python scripts/ncdelta_ncpi0_topology_analyze.py

Statistical errors only (data Poisson + MC weights). ABSENT: detector systematics (prominent for proton reconstruction), proton-reconstruction systematics, cosmic-only MC, dirt, POT, imp_weight,
neutrino-weight covariance (a ~20 % mostly-normalisation mode, section 7). Truth quantities exist for MC only (resolved background owners + signal-sample events); data has no truth.
"""
import pickle
from scipy import stats
from ncdelta_syst_common import *
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

R = "SB_ncpi0"; TAB = REPO / "tables" / "ncdelta_purity_datamc"; PLT = REPO / "plots" / "ncdelta_purity_datamc"; TOPO = ["1g0p", "1g1p", ">=2p"]; TOPOD = SPD / "ncdelta_purity_datamc" / "topo"


def load(prod):
    t = pd.read_parquet(TOPOD / f"topo_{prod}.parquet"); plan = pickle.load(open(SYST / f"regions_plan_{prod}.pkl", "rb"))
    w = dict(S=plan["pot_data"] / POT_SIGNAL, B=plan["pot_data"] / plan["pot_cv"], D=1.0); t["w"] = t.kind.map(w); t["topo"] = np.clip(t.n_p35.to_numpy(int), 0, 2)
    for k in "BSD":                                              # identity / completeness against the plan and the analysis-table row
        p = plan[k][R]; q = t[t.kind == k]; assert len(q) == len(p), (prod, k, len(q), len(p))
        m = q.merge(p[KEY + ["binT", "c_nu_index"] + (["cat", "resolved"] if k == "B" else [])], on=KEY + ["c_nu_index"], validate="one_to_one"); assert len(m) == len(p)
        assert (np.clip(m.n_p35, 0, 1) == m.binT).all(), "extracted proton count disagrees with the analysis-table topology"; assert (m.id_dE == 0).all()
        if k == "B": t.loc[t.kind == "B", "cat"] = m.set_index(KEY).reindex(t[t.kind == "B"].set_index(KEY).index).cat.to_numpy()
    rid = pd.concat([plan[k][R][KEY + RUN].assign(kind=k) for k in "BSD"]); t = t.merge(rid, on=KEY + ["kind"], how="left", validate="many_to_one"); assert t.run.notna().all()
    t["pio_E_lead"] = np.where(t.pio_flag == 1, np.maximum(t.pio_energy_1, t.pio_energy_2), np.nan); t["pio_E_sub"] = np.where(t.pio_flag == 1, np.minimum(t.pio_energy_1, t.pio_energy_2), np.nan)
    t["pio_asym"] = np.where(t.pio_flag == 1, np.abs(t.pio_energy_1 - t.pio_energy_2) / (t.pio_energy_1 + t.pio_energy_2), np.nan)
    t["pio_gap_min"] = np.where(t.pio_flag == 1, np.minimum(t.pio_dis_1, t.pio_dis_2), np.nan); t["pio_gap_max"] = np.where(t.pio_flag == 1, np.maximum(t.pio_dis_1, t.pio_dis_2), np.nan)
    for c in ("pio_mass", "pio_angle", "pio_vtx_dis"): t[c] = np.where(t.pio_flag == 1, t[c], np.nan)
    t["pio_found"] = (t.pio_flag == 1).astype(float); t["prod"] = prod
    return t


def cmp(t, col, edges, sel=None):
    """data, MC, MC-stat variance per bin (tails merged); NaN values dropped (observable undefined)."""
    out = {}
    for k in "DMC":
        pass
    def h(mask):
        x = t.loc[mask, col].to_numpy(float); w = t.loc[mask, "w"].to_numpy(float); ok = np.isfinite(x); x, w = np.clip(x[ok], edges[0] + 1e-9, edges[-1] - 1e-9), w[ok]
        return np.histogram(x, edges, weights=w)[0], np.histogram(x, edges, weights=w ** 2)[0]
    nd = h(t.kind == "D")[0]; mc, var = (a + b for a, b in zip(h(t.kind == "S"), h(t.kind == "B"))); return nd, mc, var


def chi2_shape(nd, mc, var):
    if nd.sum() == 0 or mc.sum() == 0: return np.nan, 0, np.nan
    r = nd.sum() / mc.sum(); m = mc * r; v = var * r ** 2; ok = m > 0; c = float((((nd - m) ** 2) / (m + v))[ok].sum()); n = int(ok.sum() - 1)
    return c, n, (stats.chi2.sf(c, n) if n > 0 else np.nan)


OBS = {"pio_found": ("pi0 pair found (kine_pio_flag)", np.array([-0.5, 0.5, 1.5])), "pio_mass": ("two-shower invariant mass [MeV]", np.array([0, 60, 100, 135, 170, 220, 300, 600.])),
       "pio_angle": ("pair opening angle [deg]", np.array([0, 20, 40, 60, 90, 130, 180.])), "pio_E_lead": ("leading shower energy [MeV]", np.array([0, 100, 200, 300, 450, 700, 1500., 5000])),
       "pio_E_sub": ("subleading shower energy [MeV]", np.array([0, 30, 60, 100, 150, 250, 500, 5000.])), "pio_asym": ("energy asymmetry", np.linspace(0, 1, 6)),
       "pio_gap_min": ("conversion gap, nearer shower [cm]", np.array([0, 1, 3, 6, 12, 25, 60, 400.])), "pio_gap_max": ("conversion gap, farther shower [cm]", np.array([0, 3, 8, 15, 30, 60, 120, 400.])),
       "shw_sp_vec_median_dedx": ("candidate-shower median dE/dx", np.array([0, 1, 1.5, 2, 2.5, 3.5, 5, 10, 100.])), "shw_sp_medium_dQ_dx": ("candidate-shower medium dQ/dx", np.array([0, .3, .5, .7, .9, 1.1, 1.4, 2, 10.])),
       "shw_sp_shw_vtx_dis": ("shower-vertex distance [cm]", np.array([0, 2, 5, 10, 20, 40, 80, 400.])), "lead_p_ke": ("leading reco proton KE [MeV]", np.array([35, 70, 105, 140, 200, 300, 450, 1500.])),
       "lead_p_len_first_seg": ("leading proton first-segment length [cm]", np.array([0, 2, 4, 6, 9, 14, 25, 100.])), "n_p_any": ("# reco protons at any KE", np.arange(0, 7) - 0.5),
       "n_track_rows": ("# track-like particle rows", np.arange(0, 6) - 0.5), "n_shower_rows": ("# shower-like particle rows", np.arange(0, 12) - 0.5)}


def main():
    T = {p: load(p) for p in PRODUCTIONS}; rows = []
    # ---------------- reco observables: per production, per reco topology ----------------
    fig, axs = plt.subplots(len(OBS), 6, figsize=(21, 2.2 * len(OBS)))
    for oi, (col, (lab, edges)) in enumerate(OBS.items()):
        for pi, p in enumerate(PRODUCTIONS):
            for ti in range(3):
                t = T[p][T[p].topo == ti]; nd, mc, var = cmp(t, col, edges)
                if nd.sum() == 0: axs[oi, pi * 3 + ti].axis("off"); continue
                c, n, pv = chi2_shape(nd, mc, var); ratio = nd.sum() / mc.sum(); rerr = ratio * np.sqrt(1 / max(nd.sum(), 1) + var.sum() / mc.sum() ** 2)
                rows.append(dict(observable=col, production=p, topology=TOPO[ti], n_data=int(nd.sum()), n_mc=mc.sum(), norm_ratio=ratio, norm_err=rerr, shape_chi2_stat=c, ndof=n, p=pv,
                                 bin_ratios=";".join(f"{a:.2f}" for a in (nd / np.where(mc > 0, mc, np.nan) / ratio))))
                ax = axs[oi, pi * 3 + ti]; xs = np.arange(len(nd)); r = nd.sum() / mc.sum()
                ax.bar(xs, mc * r, width=0.9, color="#bbb"); ax.errorbar(xs, nd, yerr=np.sqrt(nd), fmt="ko", ms=2.5)
                ax.set_xticks(xs); ax.set_xticklabels([f"{e:.3g}" for e in edges[:-1]], fontsize=5, rotation=60); ax.set_title(f"{p} {TOPO[ti]}: {lab}\nnorm {r:.2f}, shape p={pv:.2g}", fontsize=6)
    fig.text(0.01, 0.001, "DIAGNOSTIC / PRELIMINARY - NC-pi0 sideband, MC scaled to data per panel (shape), stat errors only; NO detector / proton-reconstruction systematics; no cosmic-only MC", fontsize=7, color="#555")
    fig.tight_layout(rect=(0, 0.005, 1, 1)); fig.savefig(PLT / "I_ncpi0_topology_reco_observables.png", dpi=95); plt.close(fig)
    R_ = pd.DataFrame(rows); R_.to_csv(TAB / "ncpi0_topology_cafobs_datamc.csv", index=False)
    piv = R_.pivot_table(index=["observable", "topology"], columns="production", values=["norm_ratio", "shape_chi2_stat", "ndof", "p"], aggfunc="first"); piv.to_csv(TAB / "ncpi0_topology_cafobs_old_vs_nov16.csv")
    print(R_.assign(chi2=lambda d: d.shape_chi2_stat.round(1), p=lambda d: d.p.round(3), nr=lambda d: d.norm_ratio.round(2))[["observable", "production", "topology", "n_data", "nr", "chi2", "ndof", "p"]].to_string())
    # ---------------- pair-found fraction and mass window ----------------
    # ---------------- truth: composition and truth->reco migration (MC only) ----------------
    mig = {}
    for p, t in T.items():
        m = t[(t.kind != "D") & t.t_np35.notna()].copy(); m["tt"] = np.clip(m.t_np35.astype(int), 0, 2)
        resolved_frac = float(m.w.sum() / t[t.kind != "D"].w.sum())
        for lab, sel in (("all resolved MC", np.ones(len(m), bool)), ("truth NC_PI0 background + none", (m.kind == "B") & (m.cat == "NC_PI0")), ("background only", m.kind == "B"), ("signal-sample (NC-Delta) only", m.kind == "S")):
            q = m[sel]; M = pd.crosstab(q.tt, q.topo, values=q.w, aggfunc="sum").reindex(index=range(3), columns=range(3)).fillna(0.0); M.index = ["truth 0p", "truth 1p", "truth >=2p"]; M.columns = TOPO
            M.to_csv(TAB / f"ncpi0_truth_reco_migration_{p}_{lab.split()[0]}_{lab.split()[1] if len(lab.split())>1 else ''}.csv".replace(" .", "."))
            mig[p, lab] = M
        print(p, "resolved MC weight fraction", round(resolved_frac, 3))
        M = mig[p, "all resolved MC"]; print(p, "truth->reco (weighted events)\n", M.round(1)); print("row-normalised\n", (M.div(M.sum(1), axis=0)).round(3)); print("column composition (truth of reco bins)\n", (M.div(M.sum(0), axis=1)).round(3))
        Mn = mig[p, "truth NC_PI0 background + none"]; print(p, "NC_PI0 background only: row-normalised\n", Mn.div(Mn.sum(1), axis=0).round(3))
    # old -> Nov16 event-wise change of reco topology at FIXED truth topology (same MC events present in both)
    rows2 = []
    a, b = T["old_fg1"], T["nov16"]
    for kind in ("B",):
        qa = a[(a.kind == kind) & a.t_np35.notna()].set_index(RUN); qb = b[(b.kind == kind) & b.t_np35.notna()].set_index(RUN); qa = qa[~qa.index.duplicated()]; qb = qb[~qb.index.duplicated()]
        j = qa[["topo", "t_np35"]].join(qb[["topo", "t_np35"]], lsuffix="_old", rsuffix="_new", how="inner"); j = j[j.t_np35_old == j.t_np35_new]; j["tt"] = np.clip(j.t_np35_old.astype(int), 0, 2)
        for tt in range(3):
            x = j[j.tt == tt]; rows2.append(dict(truth=["0p", "1p", ">=2p"][tt], n=len(x), old_reco0=(x.topo_old == 0).mean(), old_reco1=(x.topo_old == 1).mean(), old_reco2=(x.topo_old == 2).mean(),
                                                  new_reco0=(x.topo_new == 0).mean(), new_reco1=(x.topo_new == 1).mean(), new_reco2=(x.topo_new == 2).mean()))
    pd.DataFrame(rows2).to_csv(TAB / "ncpi0_truth_reco_migration_old_vs_nov16_same_events.csv", index=False); print(pd.DataFrame(rows2).round(3).to_string())
    # ---------------- truth kinematics of the reco-Np MC population (what the MC Np events are) ----------------
    out = []
    for p, t in T.items():
        m = t[(t.kind != "D") & t.t_np35.notna()]
        for ti in range(3):
            q = m[m.topo == ti]; W = q.w.sum()
            out.append(dict(production=p, reco_topology=TOPO[ti], mc_weight=W, frac_truth0p=q.w[q.t_np35 == 0].sum() / W, frac_truth1p=q.w[q.t_np35 == 1].sum() / W, frac_truth_ge2p=q.w[q.t_np35 >= 2].sum() / W,
                            frac_truth_pi0=q.w[q.t_n_pi0 >= 1].sum() / W, frac_truth_leadp_lt60=q.w[(q.t_lead_p_ke < 60)].sum() / W, median_truth_pi0_p=np.nanmedian(q.t_pi0_p) if q.t_pi0_p.notna().any() else np.nan,
                            median_truth_lead_p_ke=np.nanmedian(q.t_lead_p_ke) if q.t_lead_p_ke.notna().any() else np.nan))
    pd.DataFrame(out).to_csv(TAB / "ncpi0_reco_topology_truth_content.csv", index=False); print(pd.DataFrame(out).round(3).to_string())
    # truth proton-KE spectrum of MC true-Np events with reco 0p vs Np (where do true protons get lost?)
    o2 = []
    for p, t in T.items():
        m = t[(t.kind != "D") & (t.t_np35 >= 1)].copy(); edges = np.array([35, 50, 75, 100, 150, 250, 400, 2000.]); m["bin"] = np.clip(np.digitize(m.t_lead_p_ke, edges) - 1, 0, len(edges) - 2)
        for bi in range(len(edges) - 1):
            q = m[m.bin == bi]; W = q.w.sum(); o2.append(dict(production=p, true_lead_p_ke_lo=edges[bi], true_lead_p_ke_hi=edges[bi + 1], mc_weight=W, frac_reco0p=q.w[q.topo == 0].sum() / W if W else np.nan, frac_reco_Np=q.w[q.topo >= 1].sum() / W if W else np.nan))
    pd.DataFrame(o2).to_csv(TAB / "ncpi0_true_proton_ke_reco_efficiency.csv", index=False); print(pd.DataFrame(o2).round(3).to_string())
    # figure: migration matrices
    fig, ax = plt.subplots(1, 4, figsize=(15, 3.4))
    for a_, (p, lab) in zip(ax, [(p, l) for p in PRODUCTIONS for l in ("all resolved MC", "truth NC_PI0 background + none")]):
        M = mig[p, lab]; Mn = M.div(M.sum(1), axis=0); a_.imshow(Mn.values, vmin=0, vmax=1, cmap="Blues")
        for i in range(3):
            for j in range(3): a_.text(j, i, f"{Mn.values[i, j]:.2f}\n({M.values[i, j]:.0f})", ha="center", va="center", fontsize=8)
        a_.set_xticks(range(3)); a_.set_xticklabels(TOPO); a_.set_yticks(range(3)); a_.set_yticklabels(["truth 0p", "truth 1p", "truth >=2p"]); a_.set_title(f"{p}: {lab}\nrow-normalised (weighted events)", fontsize=8)
    fig.text(0.01, 0.005, "DIAGNOSTIC: MC only (resolved owners), NC-pi0 sideband; truth = post-FSI primary protons with KE > 35 MeV; stat only; no detector systematics", fontsize=7, color="#555")
    fig.tight_layout(rect=(0, 0.03, 1, 1)); fig.savefig(PLT / "J_ncpi0_truth_reco_topology_migration.png", dpi=110); plt.close(fig)


if __name__ == "__main__":
    main()
