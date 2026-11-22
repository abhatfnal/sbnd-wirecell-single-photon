#!/usr/bin/env python
"""EVENT-LEVEL audit of the `reinteractions_neutron_Geant4` multisim function (1000 universes). NO clipping, nothing removed: a diagnosis of how concentrated / physical / mis-associated the variance is.

    source env/setup_eaf.sh && python scripts/ncdelta_neutron_g4_audit.py final|regions|summary

Per quantity g (yield of a bin, double ratio, purity) the function's covariance contribution is Var_g = (1/N) sum_u g_u^2 with g_u = sum_e g_eu, g_eu = a_e (W_eu - 1) (a_e = event weight; unresolved events carry no
variation). Exact decomposition Var_g = sum_e s_e, s_e = (1/N) sum_u g_eu G_u (G_u = sum_e g_eu). Events needed for 50 / 90 / 99 % of Var_g: sort s_e descending, cumulative share. Leave-one-out: sigma ratio sqrt(Var_{-e} / Var).
"""
import sys, pickle, json
from ncdelta_syst_common import *
import ncdelta_syst_covariance as CV

FN = "reinteractions_neutron_Geant4"; FT = CV.FT.set_index("name"); LO, HI = int(FT.loc[FN, "start"]), int(FT.loc[FN, "stop"]); NU = 1000
AUD = SPD / "ncdelta_purity_datamc" / "audit_neutron_g4"; AUD.mkdir(parents=True, exist_ok=True); TAB = REPO / "tables" / "ncdelta_purity_datamc"


def decompose(G):
    """G: (n_events, N) per-event deltas of ONE derived quantity. Returns dict with variance, shares s_e, counts for 50/90/99 %, LOO ratios."""
    N = G.shape[1]; tot = G.sum(0); var = float((tot ** 2).sum() / N); s = (G * tot).sum(1) / N; order = np.argsort(-s); cs = np.cumsum(s[order]) / var if var > 0 else np.zeros(len(s))
    n_at = {f: int(np.searchsorted(cs, f) + 1) if var > 0 else 0 for f in (0.5, 0.9, 0.99)}
    loo = np.sqrt(np.maximum(((tot[None, :] - G) ** 2).sum(1) / N, 0) / var) if var > 0 else np.ones(len(s))
    return dict(var=var, sigma=np.sqrt(var), s=s, order=order, n50=n_at[0.5], n90=n_at[0.9], n99=n_at[0.99], loo=loo, top_share=float(s[order[0]] / var) if var > 0 else 0.0, diag=(G ** 2).sum(1) / N)


INFL = []


def record(prod, region, qn, tag, ids, d):
    """Per-event influence rows (share of the variance, leave-one-out sigma ratio, rank) for the top-event tables and the old/Nov16 cross-match."""
    rank = np.empty(len(d["s"]), int); rank[d["order"]] = np.arange(1, len(d["s"]) + 1)
    INFL.append(pd.DataFrame(dict(production=prod, region=region, quantity=qn, tag=tag, run=ids[0], subrun=ids[1], evt=ids[2], share_of_variance=d["s"] / d["var"] if d["var"] else np.nan, loo_sigma_ratio=d["loo"], rank=rank, event_variance_diag=d["diag"])))


def population(Wev, label):
    """Per-event weight statistics of the function: broad vs concentrated."""
    mx, mn = Wev.max(1), Wev.min(1); dev = np.abs(Wev - 1).max(1)
    return dict(label=label, n_events=len(Wev), frac_max_gt_1p5=float((mx > 1.5).mean()), frac_max_gt_3=float((mx > 3).mean()), frac_max_gt_10=float((mx > 10).mean()), frac_max_gt_30=float((mx > 30).mean()),
                frac_max_gt_100=float((mx > 100).mean()), frac_weight_exactly_1=float((dev < 1e-6).mean()), max_weight=float(mx.max()), min_weight=float(mn.min()), median_event_max=float(np.median(mx)))


def final_audit():
    cfg = load_cfg(); sigN, nat_in = natural_signal_in_region(); rows, pops, tops = [], [], []
    for prod in PRODUCTIONS:
        A = assemble(prod, cfg, sigN, nat_in); res = {}
        for tag in ("S", "B"):
            ev, W, w = A[tag]["ev"], A[tag]["W"], A[tag]["w"]; r = ev.resolved.to_numpy(bool)
            Wn = np.asarray(W[:, LO:HI], np.float64); G = np.where(r[:, None], w * (Wn - 1.0), 0.0); res[tag] = (ev, Wn, w, G, r)
            pops.append(dict(population(Wn[r], f"final/{tag}/{prod}"), production=prod, region="final", tag=tag))
        S0 = res["S"][2] * len(res["S"][0]); B0 = res["B"][2] * int(res["B"][4].sum()) + res["B"][2] * int((~res["B"][4]).sum())      # nominal yields (events x weight)
        GS, GB = res["S"][3], res["B"][3]
        quants = {"S_yield": (GS, None), "B_yield": (None, GB), "purity": None}
        for qn in ("S_yield", "B_yield", "purity"):
            if qn == "S_yield": parts = [("S", GS)]
            elif qn == "B_yield": parts = [("B", GB)]
            else: parts = [("S", GS * (B0) / (S0 + B0) ** 2), ("B", -GB * S0 / (S0 + B0) ** 2)]
            for tag, G in parts:
                d = decompose(G); ev_ = res[tag][0]; record(prod, "final", qn, tag, (ev_.run.to_numpy(), ev_.subrun.to_numpy(), ev_.evt.to_numpy()), d); rows.append(dict(production=prod, region="final", quantity=qn, tag=tag, n_events=len(G), n_resolved=int(res[tag][4].sum()), sigma_abs=d["sigma"], var=d["var"], n50=d["n50"], n90=d["n90"], n99=d["n99"], top_event_share=d["top_share"],
                                                  min_loo_ratio=float(d["loo"].min())))
                if qn in ("B_yield", "S_yield", "purity") and tag == ("S" if qn == "S_yield" else "B"):
                    ev = res[tag][0]; Wn = res[tag][1]; top = d["order"][:10]
                    for rk, i in enumerate(top):
                        tops.append(dict(production=prod, region="final", quantity=qn, tag=tag, rank=rk + 1, share_of_variance=d["s"][i] / d["var"] if d["var"] else np.nan, loo_sigma_ratio=d["loo"][i], run=int(ev.run.iloc[i]), subrun=int(ev.subrun.iloc[i]), evt=int(ev.evt.iloc[i]),
                                         file_index=int(ev.file_index.iloc[i]), ev_table=int(ev.ev.iloc[i]), owner_k=int(ev.owner_k.iloc[i]) if "owner_k" in ev else -1, max_w=float(Wn[i].max()), min_w=float(Wn[i].min()), resolved=bool(res[tag][4][i])))
        # relative-purity sigma from this function alone
        print(prod, "final purity sigma (this function alone) =", [r_ for r_ in rows if r_["production"] == prod and r_["quantity"] == "purity"])
    return rows, pops, tops


def regions_audit():
    rows, pops, tops = [], [], []
    for prod in PRODUCTIONS:
        if not (SYST / f"neutron_g4_events_{prod}.parquet").exists():
            print("skipping", prod, "(event extraction not available)"); continue
        t = pd.read_parquet(SYST / f"neutron_g4_events_{prod}.parquet"); Wn = np.load(SYST / f"neutron_g4_events_{prod}.npy").astype(np.float64); plan = pickle.load(open(SYST / f"regions_plan_{prod}.pkl", "rb"))
        w = dict(S=plan["pot_data"] / POT_SIGNAL, B=plan["pot_data"] / plan["pot_cv"]); a = t.tag.map(w).to_numpy()
        for reg in ("SB_numu", "preselection"):
            m = t["in_" + reg].to_numpy(bool); tt = t[m].reset_index(drop=True); WW = Wn[m]; aa = a[m]; bt = tt["binT_" + reg].to_numpy()
            pops.append(dict(population(WW, f"{reg}/{prod}"), production=prod, region=reg, tag="S+B"))
            for tag in ("S", "B"): pops.append(dict(population(WW[tt.tag.to_numpy() == tag], f"{reg}/{tag}/{prod}"), production=prod, region=reg, tag=tag))
            G0 = aa[:, None] * (WW - 1.0) * (bt[:, None] == 0); G1 = aa[:, None] * (WW - 1.0) * (bt[:, None] == 1)
            # nominal yields of the regions (resolved+unresolved) from the plan
            P0 = sum(w[k] * ((plan[k][reg].binT == 0).sum()) for k in "SB"); P1 = sum(w[k] * ((plan[k][reg].binT == 1).sum()) for k in "SB")
            qs = {"total_yield": G0 + G1, "yield_0p": G0, "yield_Np": G1, "ln_ratio_Np_over_0p": G1 / P1 - G0 / P0}
            for qn, G in qs.items():
                d = decompose(G); record(prod, reg, qn, "S+B", (tt.run.to_numpy(), tt.subrun.to_numpy(), tt.evt.to_numpy()), d); rows.append(dict(production=prod, region=reg, quantity=qn, tag="S+B", n_events=len(G), n_resolved=len(G), sigma_abs=d["sigma"], var=d["var"], n50=d["n50"], n90=d["n90"], n99=d["n99"], top_event_share=d["top_share"],
                                                  min_loo_ratio=float(d["loo"].min()), rel_sigma=d["sigma"] / (P0 + P1) if qn == "total_yield" else (d["sigma"] / P0 if qn == "yield_0p" else (d["sigma"] / P1 if qn == "yield_Np" else d["sigma"]))))
                if qn in ("total_yield", "ln_ratio_Np_over_0p"):
                    for rk, i in enumerate(d["order"][:10]):
                        r_ = tt.iloc[i]; tops.append(dict(production=prod, region=reg, quantity=qn, tag=r_.tag, rank=rk + 1, share_of_variance=d["s"][i] / d["var"] if d["var"] else np.nan, loo_sigma_ratio=d["loo"][i], run=int(r_.run), subrun=int(r_.subrun), evt=int(r_.evt),
                                                         file_index=int(r_.file_index), ev_table=int(r_.ev), owner_k=int(r_.k), nu_pdg=int(r_.nu_pdg), iscc=int(r_.iscc), mode=int(r_["mode"]), Enu_GeV=float(r_.Enu_GeV), true_np35=int(r_.t_np35), true_nneutron=int(r_.t_nneutron),
                                                         reco_topology="0p" if bt[i] == 0 else "Np", max_w=float(WW[i].max()), min_w=float(WW[i].min()), max_w_other_interactions=float(r_.max_w_all_interactions)))
    return rows, pops, tops


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "final":
        rows, pops, tops = final_audit()
        pd.DataFrame(rows).to_csv(TAB / "audit_neutron_g4_variance_concentration_final.csv", index=False); pd.DataFrame(pops).to_csv(TAB / "audit_neutron_g4_weight_population_final.csv", index=False); pd.DataFrame(tops).to_csv(AUD / "tops_final.csv", index=False)
        pd.concat(INFL).to_parquet(AUD / "influence_final.parquet", index=False); print(pd.DataFrame(rows).round(4).to_string())
    elif mode == "regions":
        rows, pops, tops = regions_audit()
        pd.DataFrame(rows).to_csv(TAB / "audit_neutron_g4_variance_concentration_regions.csv", index=False); pd.DataFrame(pops).to_csv(TAB / "audit_neutron_g4_weight_population_regions.csv", index=False); pd.DataFrame(tops).to_csv(AUD / "tops_regions.csv", index=False)
        pd.concat(INFL).to_parquet(AUD / "influence_regions.parquet", index=False); print(pd.DataFrame(rows).round(4).to_string()); print(pd.DataFrame(pops).round(4).to_string())
