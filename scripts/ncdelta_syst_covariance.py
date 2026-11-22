#!/usr/bin/env python
"""FIRST-PASS neutrino-systematic covariance products for the frozen final selection (MC only; PRELIMINARY; nothing is clipped, no data, no imp_weight).

    source env/setup_eaf.sh && python scripts/ncdelta_syst_covariance.py        (needs scripts/ncdelta_syst_extract.py extract and ncdelta_syst_diagnostics.py to have closed)

Event-level throughout (any candidate passes, event counted once). S = dedicated NC-Delta sample (owner = signal interaction), B = generic BNB CV (owner = production-matched interaction
`mnu_k`; events without a unique owner are held at the NOMINAL weight in every universe = their neutrino systematics are UNRESOLVED and outside the band).
Common-universe coherence: for each source and universe index u the SAME u is applied to S and B, P_u = S_u / (S_u + B_u) is formed, and only then the spread is taken.
Components (independent sources, each with its documented prescription): flux (13 families), beamline G4 reinteraction (6), GENIE cross section (multisim), cross-section extras
(single-sigma GENIE shapes + unisim +-1 sigma 2p2h/misc/non-resonant-pion sets), GENIE FSI (multisim). OUTSIDE the band: detector, beam-off/cosmic normalisation, dirt, POT,
the NC-Delta signal-model dials (RDecBR1gamma, ThetaDelta2NRad; shown separately), imp_weight, MC statistics (shown separately), and neutrino systematics of unresolved events.
"""
from ncdelta_syst_common import *
from sbnd_single_photon import syst_weights as SW
import matplotlib.pyplot as plt
from sbnd_single_photon import plotstyle as PS
PS.apply_style()

TAB = REPO / "tables" / "ncdelta_purity_datamc"; FT = pd.read_csv(TAB / "syst_function_table.csv", keep_default_na=False)
COMP = {"flux": ["flux_multisim"], "beamline_g4_reint": ["beamline_g4_reint_multisim"], "xsec_genie": ["xsec_genie_multisim"], "xsec_extras": ["xsec_genie_unisim_extra", "xsec_extra_multisigma"], "fsi_genie": ["fsi_genie_multisim"]}
CORDER = list(COMP); OUTSIDE = {"ncdelta_model_RDecBR1gamma_OUTSIDE_band": "multisim_RDecBR1gamma", "ncdelta_model_ThetaDelta2NRad_OUTSIDE_band": "multisigma_ThetaDelta2NRad"}      # NC-Delta signal-model dials: shown separately
TAG = "PRELIMINARY first-pass: MC only; neutrino flux/xsec/FSI/G4 only. NOT in band: detector, cosmic/beam-off, dirt, POT, NC-Delta signal model (radiative decay), imp_weight, unresolved-owner events"


def view_bins(ev, view):
    if view == "energy":
        return np.clip(np.digitize(ev.c_shw_sp_energy.to_numpy(float), E_BINS), 0, len(E_BINS)).astype(int), len(E_BINS) + 1, ["<20"] + [f"{a:.0f}-{b:.0f}" for a, b in zip(E_BINS[:-1], E_BINS[1:])] + [">3000"]
    if view == "channel3":
        m = {c: i for i, c in enumerate(CH_BINS)}; return ev.ch.map(m).fillna(-1).astype(int).to_numpy(), 3, CH_BINS
    if view == "topo2":
        return np.where(ev.ch == "1g0p", 0, np.where(ev.ch.isin(["1g1p", "ge2p"]), 1, -1)), 2, ["1g0p", "1gNp"]
    return np.zeros(len(ev), int), 1, ["all"]


def products(prod, X, view, tail):
    eS, eB = X["S"]["ev"], X["B"]["ev"]; wS, wB = X["S"]["w"], X["B"]["w"]
    iS, nb, labels = view_bins(eS, view); iB, _, _ = view_bins(eB, view)
    WS = X["S"]["W"]; WB = X["B"]["W"]                                           # unresolved B rows are ones (nominal in every universe)
    YS, YB = SW.universe_yields(WS, wS, iS, nb), SW.universe_yields(WB, wB, iB, nb)
    one = lambda i, w, n: np.bincount(i[i >= 0], minlength=n) * w
    Sn, Bn = one(iS, wS, nb), one(iB, wB, nb)
    Qn = np.concatenate([Sn, Bn]); pred = lambda Q: Q[:nb] + Q[nb:]; pur = lambda Q: Q[:nb] / (Q[:nb] + Q[nb:])
    nS, nBn = np.bincount(iS[iS >= 0], minlength=nb), np.bincount(iB[iB >= 0], minlength=nb)
    out = dict(labels=labels, nb=nb, Sn=Sn, Bn=Bn, statS=np.sqrt(nS) * wS, statB=np.sqrt(nBn) * wB, comp={}, per_fn=[])
    for c in CORDER + list(OUTSIDE) + ["single_event_dominated", "unvalidated_nG4"]:
        out["comp"][c] = dict(Q=np.zeros((2 * nb, 2 * nb)), pred=np.zeros((nb, nb)), pur=np.zeros((nb, nb)))
    for fn in FT.to_dict("records"):
        sl = slice(fn["start"], fn["stop"]); Qu = np.vstack([YS[:, sl], YB[:, sl]])
        try:
            D, sc = SW.function_deltas(fn, Qu, Qn); Dp, _ = SW.function_deltas(fn, Qu, Qn, pur); Dpred, _ = SW.function_deltas(fn, Qu, Qn, pred)
        except ValueError:
            out["per_fn"].append(dict(name=fn["name"], group=fn["group"], in_band=fn["in_band"], computed=False)); continue
        if view == "all":
            rS = float(np.sqrt(sc * (D[0] ** 2).sum()) / Sn[0]) if Sn[0] > 0 else np.nan; rB = float(np.sqrt(sc * (D[1] ** 2).sum()) / Bn[0]); rP = float(np.sqrt(sc * (Dp[0] ** 2).sum()) / pur(Qn)[0])
            rho = float(sc * (D[0] * D[1]).sum() / np.sqrt(sc * (D[0] ** 2).sum() * sc * (D[1] ** 2).sum())) if (D[0] ** 2).sum() > 0 and (D[1] ** 2).sum() > 0 else np.nan
            def loo(W, w, sl):                                  # multisim only: sigma of the total yield without the single most influential event / with it (single-event-dominance diagnostic; nothing is clipped)
                d = W[:, sl].astype(np.float64) - 1.0; dN = w * d.sum(0); top = int(np.argmax((d ** 2).sum(1))); dN2 = dN - w * d[top]
                return float(np.sqrt((dN2 ** 2).mean()) / np.sqrt((dN ** 2).mean())) if (dN ** 2).sum() > 0 else np.nan
            lS = loo(WS, wS, sl) if fn["type_code"] == SW.KMULTISIM else np.nan; lB = loo(WB, wB, sl) if fn["type_code"] == SW.KMULTISIM else np.nan
            out["per_fn"].append(dict(name=fn["name"], group=fn["group"], in_band=fn["in_band"], computed=True, rel_S=rS, rel_B=rB, rel_P=rP, corr_S_B=rho, sigma_ratio_without_top_event_S=lS, sigma_ratio_without_top_event_B=lB))
        for c, gs in {**(COMP if fn["in_band"] else {}), **{k: [v] for k, v in OUTSIDE.items()}}.items():
            if (fn["group"] in gs) if c in COMP else fn["name"].endswith(gs[0]):
                out["comp"][c]["Q"] += sc * D @ D.T; out["comp"][c]["pur"] += sc * Dp @ Dp.T; out["comp"][c]["pred"] += sc * Dpred @ Dpred.T
                if fn["in_band"] and fn["name"] == "reinteractions_neutron_Geant4":      # unvalidated weight-tail function (event-level audit): tracked separately; the 'validated' total excludes only this function
                    out["comp"]["unvalidated_nG4"]["Q"] += sc * D @ D.T; out["comp"]["unvalidated_nG4"]["pur"] += sc * Dp @ Dp.T; out["comp"]["unvalidated_nG4"]["pred"] += sc * Dpred @ Dpred.T
                if fn["in_band"] and tail.get(fn["name"], False):
                    out["comp"]["single_event_dominated"]["Q"] += sc * D @ D.T; out["comp"]["single_event_dominated"]["pur"] += sc * Dp @ Dp.T; out["comp"]["single_event_dominated"]["pred"] += sc * Dpred @ Dpred.T
    tot = dict(Q=sum(out["comp"][c]["Q"] for c in CORDER), pred=sum(out["comp"][c]["pred"] for c in CORDER), pur=sum(out["comp"][c]["pur"] for c in CORDER)); out["comp"]["TOTAL_available"] = tot
    out["comp"]["TOTAL_excluding_single_event_dominated"] = {k: tot[k] - out["comp"]["single_event_dominated"][k] for k in tot}
    out["comp"]["TOTAL_validated_excl_nG4"] = {k: tot[k] - out["comp"]["unvalidated_nG4"][k] for k in tot}
    return out


def tail_flags(X):
    """Tail-dominance of every in-band multisim function: sigma of the total yield without / with its single most influential event (S and B). Flags, never clips. A ratio near 0 usually means only one selected event responds to that dial (thin response), not a weight tail."""
    rows, flag = [], {}
    for fn in FT[FT.in_band & (FT.type_code == SW.KMULTISIM)].to_dict("records"):
        sl = slice(fn["start"], fn["stop"]); r = {}
        for tag in ("S", "B"):
            W, w = X[tag]["W"], X[tag]["w"]; d = W[:, sl].astype(np.float64) - 1.0; dN = w * d.sum(0); top = int(np.argmax((d ** 2).sum(1))); dN2 = dN - w * d[top]
            r[tag] = float(np.sqrt((dN2 ** 2).mean()) / np.sqrt((dN ** 2).mean())) if (dN ** 2).sum() > 0 else np.nan
        flag[fn["name"]] = bool(min(v for v in r.values() if np.isfinite(v)) < SW.SINGLE_EVENT_RATIO_THRESHOLD) if any(np.isfinite(v) for v in r.values()) else False
        rows.append(dict(name=fn["name"], group=fn["group"], sigma_ratio_without_top_event_S=r["S"], sigma_ratio_without_top_event_B=r["B"], single_event_dominated=flag[fn["name"]], threshold=SW.SINGLE_EVENT_RATIO_THRESHOLD))
    return dict(rows=rows, flag=flag)


def main():
    cfg = load_cfg(); sigN, nat_in = natural_signal_in_region(); rows, fnrows, covrows, cover, tailrows = [], [], [], [], []
    res = {}
    for prod in PRODUCTIONS:
        X = assemble(prod, cfg, sigN, nat_in); res[prod] = {}; tail = tail_flags(X); tailrows.extend(dict(production=prod, **v) for v in tail["rows"]); tail = tail["flag"]
        eB = X["B"]["ev"]; wB = X["B"]["w"]; wS = X["S"]["w"]; S_tot = len(X["S"]["ev"]) * wS; B_tot = len(eB) * wB; B_res = int(eB.resolved.sum()) * wB
        for view in ("all", "topo2", "channel3", "energy"):
            P = products(prod, X, view, tail); res[prod][view] = P; nb = P["nb"]
            Sn, Bn = P["Sn"], P["Bn"]; pn = Sn / (Sn + Bn)
            for c in CORDER + ["TOTAL_available", "TOTAL_excluding_single_event_dominated", "TOTAL_validated_excl_nG4", "unvalidated_nG4", "single_event_dominated"] + list(OUTSIDE):
                C = P["comp"][c]; CSS, CBB, CSB = C["Q"][:nb, :nb], C["Q"][nb:, nb:], C["Q"][:nb, nb:]
                for b in range(nb):
                    sS, sB = np.sqrt(CSS[b, b]), np.sqrt(CBB[b, b]); sP = np.sqrt(C["pur"][b, b]); spred = np.sqrt(C["pred"][b, b])
                    # naive: independent S and B (drop the S-B covariance) propagated linearly
                    dPdS, dPdB = Bn[b] / (Sn[b] + Bn[b]) ** 2, -Sn[b] / (Sn[b] + Bn[b]) ** 2
                    naive = np.sqrt((dPdS * sS) ** 2 + (dPdB * sB) ** 2); lin_coh = np.sqrt(max((dPdS * sS) ** 2 + (dPdB * sB) ** 2 + 2 * dPdS * dPdB * CSB[b, b], 0))
                    rows.append(dict(production=prod, view=view, bin=P["labels"][b], component=c, S=Sn[b], B=Bn[b], S_plus_B=Sn[b] + Bn[b], purity=pn[b], sigma_S=sS, sigma_B=sB, sigma_pred=spred,
                                     rel_S=sS / Sn[b] if Sn[b] > 0 else np.nan, rel_B=sB / Bn[b] if Bn[b] > 0 else np.nan, rel_pred=spred / (Sn[b] + Bn[b]), corr_S_B=CSB[b, b] / (sS * sB) if sS * sB > 0 else np.nan,
                                     sigma_purity_coherent_per_universe=sP, sigma_purity_coherent_linear=lin_coh, sigma_purity_naive_independent_SB=naive, mc_stat_S=P["statS"][b], mc_stat_B=P["statB"][b],
                                     mc_stat_purity=np.sqrt((dPdS * P["statS"][b]) ** 2 + (dPdB * P["statB"][b]) ** 2)))
            if view == "all":
                for r in P["per_fn"]:
                    fnrows.append(dict(production=prod, **r))
            np.savez(TAB / f"syst_cov_{view}_{prod}.npz", labels=np.array(P["labels"]), S=Sn, B=Bn, **{f"{c}__{k}": P["comp"][c][k] for c in P["comp"] for k in ("Q", "pred", "pur")})
        cover.append(dict(production=prod, S_per_1e20=S_tot, B_per_1e20=B_tot, B_unresolved_per_1e20=B_tot - B_res, frac_prediction_with_varied_neutrino_systematics=(S_tot + B_res) / (S_tot + B_tot),
                          frac_prediction_unvaried_unresolved_owner=(B_tot - B_res) / (S_tot + B_tot)))
    pd.DataFrame(rows).to_csv(TAB / "syst_band_by_component.csv", index=False); pd.DataFrame(fnrows).to_csv(TAB / "syst_function_effects_total.csv", index=False); pd.DataFrame(cover).to_csv(TAB / "syst_band_coverage.csv", index=False); pd.DataFrame(tailrows).to_csv(TAB / "syst_single_event_dominance.csv", index=False)
    plots(res)


def plots(res):
    PLT_ = REPO / "plots" / "ncdelta_purity_datamc"; col = {"flux": "#0072B2", "beamline_g4_reint": "#56B4E9", "xsec_genie": "#D55E00", "xsec_extras": "#E69F00", "fsi_genie": "#009E73", "TOTAL_available": "#000000"}
    lab = {"flux": "flux", "beamline_g4_reint": "beamline G4 reint.", "xsec_genie": "GENIE xsec (multisim)", "xsec_extras": "xsec extras (unisim)", "fsi_genie": "GENIE FSI", "TOTAL_available": "total (available)"}
    for prod in PRODUCTIONS:
        P = res[prod]["energy"]; nb = P["nb"]; fig, ax = plt.subplots(1, 3, figsize=(15, 4.3))
        x = np.arange(nb); S, B = P["Sn"], P["Bn"]; tot = S + B
        ax[0].bar(x, B, color="#999999", label="background (generic BNB CV)"); ax[0].bar(x, S, bottom=B, color="#F0E442", edgecolor="k", lw=0.4, label="signal (dedicated NC Delta)")
        sy = np.sqrt(np.diag(P["comp"]["TOTAL_available"]["pred"])); st = np.sqrt(P["statS"] ** 2 + P["statB"] ** 2)
        ax[0].errorbar(x, tot, yerr=st, fmt="none", ecolor="#222222", lw=1.6, capsize=2, label="MC statistical"); ax[0].errorbar(x + 0.12, tot, yerr=sy, fmt="none", ecolor="#D55E00", lw=1.6, capsize=2, label="available neutrino systematics")
        ax[0].set_xticks(x); ax[0].set_xticklabels(P["labels"], rotation=40, ha="right", fontsize=7); ax[0].set_xlabel("selected-shower energy [MeV] (event: lowest-index passing candidate)", fontsize=8); ax[0].set_ylabel("expected events / 1e20 POT"); ax[0].legend(fontsize=6.5)
        for c in CORDER + ["TOTAL_available"]:
            r = np.sqrt(np.diag(P["comp"][c]["pred"])) / np.where(tot > 0, tot, np.nan); ax[1].plot(x, 100 * r, "o-" if c != "TOTAL_available" else "s-", color=col[c], lw=2.2 if c == "TOTAL_available" else 1.1, ms=3.5, label=lab[c])
        ax[1].plot(x, 100 * np.sqrt(np.diag(P["comp"]["TOTAL_excluding_single_event_dominated"]["pred"])) / np.where(tot > 0, tot, np.nan), "s--", color="#777777", lw=1.2, ms=3, label="total excl. single-event-dominated fns")
        ax[1].plot(x, 100 * st / np.where(tot > 0, tot, np.nan), "k--", lw=1, label="MC statistical"); ax[1].set_xticks(x); ax[1].set_xticklabels(P["labels"], rotation=40, ha="right", fontsize=7)
        ax[1].set_ylabel("fractional uncertainty on S+B [%]"); ax[1].legend(fontsize=6.5); ax[1].set_title("prediction S+B per bin", fontsize=9)
        T = res[prod]["topo2"]; xs = np.arange(2)
        for k, c in enumerate(CORDER + ["TOTAL_available"]):
            ax[2].bar(xs + (k - 2.5) * 0.12, 100 * np.sqrt(np.diag(T["comp"][c]["pur"])) / (T["Sn"] / (T["Sn"] + T["Bn"])), 0.12, color=col[c], label=lab[c])
        ax[2].set_xticks(xs); ax[2].set_xticklabels([f"{l}: P={100 * s / (s + b):.2f}%" for l, s, b in zip(T["labels"], T["Sn"], T["Bn"])]); ax[2].set_ylabel("relative uncertainty on purity [%]\n(coherent per-universe P_u = S_u/(S_u+B_u))", fontsize=8); ax[2].legend(fontsize=6.5)
        fig.suptitle(f"{ {'old_fg1': 'old fg1-era reconstruction', 'nov16': 'WCLocal2026Nov16'}[prod]} | frozen legacy chain, final selection | event level", fontsize=10); fig.text(0.01, 0.005, TAG, fontsize=6.5, color="#a00")
        fig.tight_layout(rect=(0, 0.025, 1, 0.95)); fig.savefig(PLT_ / f"E_syst_first_pass_{prod}.png", dpi=120, bbox_inches="tight"); plt.close(fig); print("wrote", f"E_syst_first_pass_{prod}.png")


if __name__ == "__main__":
    main()
