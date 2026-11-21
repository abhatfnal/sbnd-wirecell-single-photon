#!/usr/bin/env python
"""Np/0p (reconstructed proton multiplicity) data/MC double ratio per control region, old vs WCL1116, with data stat, MC stat and the AVAILABLE neutrino covariance (delta method on the saved topo2
covariance of S+B, coherent universes). ABSENT: detector / proton-reconstruction systematics, cosmic-only MC, dirt, POT, imp_weight. Also the exact weighted P(truth Np | reco topology) (MC, resolved owners).

    source env/setup_eaf.sh && python scripts/ncdelta_np_over_0p_summary.py
"""
import pickle
from ncdelta_syst_common import *
import ncdelta_syst_covariance as CV
from sbnd_single_photon import syst_weights as SW
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sbnd_single_photon import plotstyle as PS
TAB = REPO / "tables" / "ncdelta_purity_datamc"; PLT = REPO / "plots" / "ncdelta_purity_datamc"
REG = ["preselection", "SB_numu", "SB_ncpi0", "SB_other", "SB_nue"]; TAGS = ["SB_ncpi0-SB_other-SB_nue", "SB_numu-preselection"]


TAIL_LO, TAIL_HI = 0.3, 2.0       # a function is a weight-tail function in a region if any universe has a resolved mean weight outside [0.3, 2.0] in a topology bin (S or B)


def topo2_cov(prod, r, tag, plan, acc, ri, P):
    """Recompute the topo2 (0p, Np) covariance from the per-universe yields; returns (C_all, C_without_tail_functions, list of tail functions)."""
    w = dict(S=plan["pot_data"] / POT_SIGNAL, B=plan["pot_data"] / plan["pot_cv"]); Q = 0; tail = set()
    for t in ("S", "B"):
        d = plan[t][r]; un = np.bincount(d[~d.resolved].binT.to_numpy(), minlength=2); a = acc[t]["acc"][ri * 3 + 2]; cnt = acc[t]["cnt"][ri * 3 + 2]; Q = Q + w[t] * (a + un[:, None])
        mw = a / np.maximum(cnt, 1)[:, None]
        for fn in CV.FT[CV.FT.in_band].to_dict("records"):
            x = mw[:, fn["start"]:fn["stop"]]
            if (cnt > 0).all() and ((x > TAIL_HI).any() or (x < TAIL_LO).any()): tail.add(fn["name"])
    Call = np.zeros((2, 2)); Cno = np.zeros((2, 2))
    for fn in CV.FT[CV.FT.in_band].to_dict("records"):
        Dd, sc = SW.function_deltas(fn, Q[:, fn["start"]:fn["stop"]], P); Cf = sc * Dd @ Dd.T; Call += Cf
        if fn["name"] not in tail: Cno += Cf
    return Call, Cno, sorted(tail)


def main():
    mats = {}
    for t in TAGS: mats.update(pickle.load(open(SYST / f"regions_mats_{t}.pkl", "rb")))
    rows = []
    for p in PRODUCTIONS:
        plan = pickle.load(open(SYST / f"regions_plan_{p}.pkl", "rb")); accs = {t: pickle.load(open(SYST / f"regions_acc_{p}_{t}.pkl", "rb")) for t in TAGS}
        for r in REG:
            M = mats[p, r, "topo2"]; P, D, vmc, C = M["P"], M["D"], M["var_mc"], M["Csyst"]
            tg = TAGS[0] if r in ("SB_ncpi0", "SB_other", "SB_nue") else TAGS[1]; ri = tg.split("-").index(r) if False else [x for x in tg.replace("SB_", "SB_").split("-")].index(r)
            Cc_all, C, tail = topo2_cov(p, r, tg, plan, accs[tg], ri, P); assert np.allclose(Cc_all, M["Csyst"], rtol=1e-6, atol=1e-9), "recomputed covariance differs from the saved one"; C_with = Cc_all
            Rd = (D[1] / D[0]) / (P[1] / P[0]); J = np.array([-1 / P[0], 1 / P[1]])                       # d ln(P1/P0)
            rel_syst = float(np.sqrt(J @ C @ J)); rel_syst_with_tail = float(np.sqrt(J @ C_with @ J)); rel_mc = float(np.sqrt(J ** 2 @ vmc)); rel_dat = float(np.sqrt(1 / D[0] + 1 / D[1]))
            pass
            sm = np.hypot(rel_dat, rel_mc); tot = np.hypot(sm, rel_syst); tot_with = np.hypot(sm, rel_syst_with_tail)
            rows.append(dict(production=p, region=r, data_0p=int(D[0]), data_Np=int(D[1]), mc_0p=P[0], mc_Np=P[1], double_ratio=Rd, rel_data=rel_dat, rel_mc=rel_mc, rel_syst_available=rel_syst, rel_syst_incl_weight_tail_functions=rel_syst_with_tail, weight_tail_functions=";".join(tail), n_sigma_with_tail_functions=(Rd - 1) / (Rd * tot_with), rel_stat_mc=sm, rel_total_available=tot,
                             n_sigma_stat_only=(Rd - 1) / (Rd * sm), n_sigma_with_available_syst=(Rd - 1) / (Rd * tot), ))
    df = pd.DataFrame(rows); df.to_csv(TAB / "np_over_0p_double_ratio_with_covariance.csv", index=False); print(df.round(3).drop(columns=["weight_tail_functions"]).to_string(index=False))
    # ---- exact weighted inverse conditional fractions ----
    out = []
    for p in PRODUCTIONS:
        t = pd.read_parquet(SPD / "ncdelta_purity_datamc/topo" / f"topo_{p}.parquet"); plan = pickle.load(open(SYST / f"regions_plan_{p}.pkl", "rb"))
        w = dict(S=plan["pot_data"] / POT_SIGNAL, B=plan["pot_data"] / plan["pot_cv"]); m = t[(t.kind != "D")].copy(); m["w"] = m.kind.map(w); m["topo"] = np.clip(m.n_p35.astype(int), 0, 2)
        allw = m.groupby("topo").w.sum(); m = m[m.t_np35.notna()]
        for ti, lab in enumerate(["reco 0p", "reco 1p", "reco >=2p"]):
            q = m[m.topo == ti]; W = q.w.sum(); k = (q.t_np35 >= 1); f = q.w[k].sum() / W; err = np.sqrt((q.w ** 2 * ((k - f) ** 2)).sum()) / W
            out.append(dict(production=p, reco=lab, n_mc_events=len(q), weighted=W, resolved_weight_fraction=W / allw[ti], P_truth_ge1p_given_reco=f, err_stat=err,
                            P_truth_0p_given_reco=1 - f, P_truth_ge2p_given_reco=q.w[q.t_np35 >= 2].sum() / W))
    o = pd.DataFrame(out); o.to_csv(TAB / "ncpi0_P_truth_Np_given_reco.csv", index=False); print(o.round(3).to_string(index=False))
    # ---- figure ----
    PS.apply_style(); CO, CN = "#0072B2", "#D55E00"; fig, ax = plt.subplots(figsize=(7.6, 4.2)); xs = np.arange(len(REG))
    for k, (p, c, name) in enumerate((("old_fg1", CO, "old fg1-era reconstruction"), ("nov16", CN, "WCLocal2026Nov16"))):
        y = df[df.production == p].set_index("region").loc[REG]; x = xs + (k - 0.5) * 0.2
        ax.errorbar(x, y.double_ratio, yerr=y.double_ratio * y.rel_total_available, fmt="none", ecolor=c, lw=1.2, capsize=3)
        dif = y.rel_syst_incl_weight_tail_functions > y.rel_syst_available + 1e-6
        for xi, (_, rw) in zip(x, y.iterrows()):
            if rw.rel_syst_incl_weight_tail_functions > rw.rel_syst_available + 1e-6:
                tt = rw.double_ratio * np.hypot(rw.rel_stat_mc, rw.rel_syst_incl_weight_tail_functions); ax.plot([xi + 0.035] * 2, [rw.double_ratio - tt, rw.double_ratio + tt], color=c, lw=1.0, ls=(0, (2, 2)), alpha=0.8); ax.plot([xi + 0.035] * 2, [max(rw.double_ratio - tt, 0.02)] * 2, "_", color=c, ms=6)
        ax.errorbar(x, y.double_ratio, yerr=y.double_ratio * y.rel_stat_mc, fmt="o", color=c, lw=4, alpha=0.9, ms=6, label=name)
        for xi, (_, rw) in zip(x, y.iterrows()): ax.text(xi, rw.double_ratio * (1 + rw.rel_total_available) + 0.03, f"{rw.double_ratio:.2f}", ha="center", fontsize=7, color="#333")
    ax.axhline(1, color="k", lw=0.7); ax.set_xticks(xs); ax.set_xticklabels(["preselection", "SB nu-mu-rich", "SB NC-pi0-rich", "SB other-rich", "SB nu-e-rich"], fontsize=8)
    ax.set_ylabel("(Np / 0p)$_{data}$ / (Np / 0p)$_{MC}$"); ax.set_ylim(0, 1.9); ax.legend(loc="upper right", fontsize=8)
    ax.set_title("Reconstructed proton multiplicity: data/MC Np/0p ratio by control region (open data, event level)", fontsize=9)
    fig.text(0.01, 0.045, "PRELIMINARY. Thick bar: data + MC statistics. Thin solid bar: + available flux/GENIE/FSI/G4 covariance, excluding weight-tail functions (preselection, nu-mu: reinteractions_neutron_Geant4);", fontsize=5.8, color="#555")
    fig.text(0.01, 0.015, "dashed: including them (a single-weight-tail artifact, see text). NOT included: detector and proton-reconstruction systematics, cosmic-only MC, dirt, POT, imp_weight.", fontsize=5.8, color="#555")
    fig.tight_layout(rect=(0, 0.07, 1, 1)); fig.savefig(PLT / "K_np_over_0p_double_ratio_by_region.png", dpi=150); plt.close(fig)


if __name__ == "__main__":
    main()
