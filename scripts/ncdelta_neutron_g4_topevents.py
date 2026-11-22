#!/usr/bin/env python
"""Top-10 most influential events of `reinteractions_neutron_Geant4` per production / region / quantity, with identity, topology, authoritative truth category, owner interaction, truth content,
weight range, candidate scores / stage membership, and the old <-> Nov16 cross-match (same run/subrun/evt). Diagnosis only: nothing is clipped or removed.

    source env/setup_eaf.sh && python scripts/ncdelta_neutron_g4_topevents.py     (after ncdelta_neutron_g4_audit.py final|regions)
"""
import pickle
from ncdelta_syst_common import *
AUD = SPD / "ncdelta_purity_datamc" / "audit_neutron_g4"; TAB = REPO / "tables" / "ncdelta_purity_datamc"
QUANT = [("final", "B_yield"), ("final", "S_yield"), ("SB_numu", "total_yield"), ("SB_numu", "ln_ratio_Np_over_0p"), ("preselection", "total_yield"), ("preselection", "ln_ratio_Np_over_0p")]
MODE = {0: "QE", 1: "RES", 2: "DIS", 3: "COH", 10: "MEC"}


def main():
    cfg = load_cfg(); infl = pd.concat([pd.read_parquet(AUD / "influence_final.parquet"), pd.read_parquet(AUD / "influence_regions.parquet")], ignore_index=True)
    rows = []; sigN, nat_in = natural_signal_in_region()
    for prod in PRODUCTIONS:
        if not (SYST / f"neutron_g4_events_{prod}.parquet").exists():
            print("skipping", prod, "(no event extraction)"); continue
        ev = pd.read_parquet(SYST / f"neutron_g4_events_{prod}.parquet"); W = np.load(SYST / f"neutron_g4_events_{prod}.npy", mmap_mode="r"); ev["row"] = np.arange(len(ev))
        plan = pickle.load(open(SYST / f"regions_plan_{prod}.pkl", "rb"))
        cev, cc, cf = load_cv(prod, cfg); sev, sc = load_signal(prod, cfg); own = pd.read_parquet(SYST / f"owners_B_{prod}.parquet")[["file_index", "ev", "cat", "resolved", "owner_k", "n_pass", "ncat", "n20br1", "removed_in_region_natural_signal"]]; ownS = pd.read_parquet(SYST / f"owners_S_{prod}.parquet")[["file_index", "ev", "n20br1"]]
        cats = pd.concat([plan["B"][r][["file_index", "ev", "cat"]] for r in ("SB_numu", "preselection")]).drop_duplicates(["file_index", "ev"])
        masks = {r: RG.region_mask(cc, r) for r in ("preselection", "SB_numu", "SB_other", "SB_ncpi0", "SB_nue")}
        for reg, qn in QUANT:
            x = infl[(infl.production == prod) & (infl.region == reg) & (infl.quantity == qn)]
            x = x[x.tag.isin(["B", "S+B"] if qn != "S_yield" else ["S"])].sort_values("rank").head(10)
            for r in x.itertuples():
                e = ev[(ev.run == r.run) & (ev.subrun == r.subrun) & (ev.evt == r.evt) & (ev.tag == ("S" if qn == "S_yield" else ev.tag.iloc[0]))]
                e = e[e.tag == "S"] if qn == "S_yield" else e[e.tag == "B"]
                assert len(e) >= 1, (prod, reg, qn, r.run, r.subrun, r.evt); e = e.iloc[0]
                w = np.asarray(W[int(e.row)]); out = dict(production=prod, region=reg, quantity=qn, rank=r.rank, share_of_variance=r.share_of_variance, loo_sigma_ratio=r.loo_sigma_ratio, run=r.run, subrun=r.subrun, evt=r.evt, sample=e.tag,
                                                         file_index=int(e.file_index), ev_table=int(e.ev), owner_k=int(e.k), n_interactions_in_event=int(e.n_nu), nu_pdg=int(e.nu_pdg), cc_nc="CC" if e.iscc == 1 else "NC", mode=MODE.get(int(e["mode"]), str(int(e["mode"]))),
                                                         true_Enu_GeV=round(float(e.Enu_GeV), 3), true_protons_gt35MeV=int(e.t_np35), true_neutrons=int(e.t_nneutron), max_weight=float(w.max()), min_weight=float(w.min()), n_univ_w_gt_10=int((w > 10).sum()),
                                                         n_univ_w_gt_100=int((w > 100).sum()), max_weight_any_interaction_in_event=float(e.max_w_all_interactions))
                if e.tag == "B":
                    o = own[(own.file_index == e.file_index) & (own.ev == e.ev)]; c_ = cats[(cats.file_index == e.file_index) & (cats.ev == e.ev)]
                    out["truth_category_authoritative"] = (c_.cat.iloc[0] if len(c_) else (o.cat.iloc[0] if len(o) else "n/a")); out["in_final_selection"] = bool(len(o) and bool(o.n20br1.iloc[0]) and not bool(o.removed_in_region_natural_signal.iloc[0]))
                else:
                    out["truth_category_authoritative"] = "SIGNAL_SAMPLE_NCDELTA"; oS = ownS[(ownS.file_index == e.file_index) & (ownS.ev == e.ev)]; out["in_final_selection"] = bool(len(oS) and bool(oS.n20br1.iloc[0]))
                c_all = (cc if e.tag == "B" else sc); c_ev = c_all[(c_all.file_index == e.file_index) & (c_all.ev == e.ev)]
                pf = c_ev[c_ev.pass_final.to_numpy(bool)] if "pass_final" in c_ev else c_ev.iloc[:0]; cand = (pf if len(pf) else c_ev.sort_values("c_nu_index")).iloc[:1]
                if len(cand):
                    c0 = cand.iloc[0]; g = lambda *ns: next((float(c0[n]) for n in ns if n in c0.index and pd.notna(c0[n])), np.nan); np35 = g("c_np35", "reco_proton_cat"); out.update(reco_np35=int(np35) if np.isfinite(np35) else -1, reco_topology=("0p" if np35 == 0 else "Np") if np.isfinite(np35) else "n/a", score_numu=g("v_numu", "c_score_numu"), score_other=g("v_other", "c_score_other"), score_ncpi0=g("v_ncpi0", "c_score_ncpi0"), score_nue=g("v_nue", "c_score_nue"),
                                                  shower_energy_MeV=g("c_shw_sp_energy"))
                    if e.tag == "B":
                        for rg, m in masks.items(): out["in_" + rg] = bool(m[(cc.file_index == e.file_index).to_numpy() & (cc.ev == e.ev).to_numpy()].any())
                rows.append(out)
    df = pd.DataFrame(rows)
    # old <-> Nov16 cross-match by run/subrun/evt: is the same physical event influential in both productions?
    key = ["run", "subrun", "evt"]
    for (reg, qn), g in df.groupby(["region", "quantity"]):
        o = infl[(infl.region == reg) & (infl.quantity == qn)]
        for prod, other in (("old_fg1", "nov16"), ("nov16", "old_fg1")):
            gi = df[(df.region == reg) & (df.quantity == qn) & (df.production == prod)]
            for i, r in gi.iterrows():
                m = o[(o.production == other) & (o.run == r.run) & (o.subrun == r.subrun) & (o.evt == r.evt)]
                df.loc[i, "rank_in_other_production"] = float(m["rank"].min()) if len(m) else np.nan; df.loc[i, "in_other_production_top10"] = bool(len(m) and m["rank"].min() <= 10)
    df.to_csv(TAB / "audit_neutron_g4_top_events.csv", index=False)
    pd.set_option("display.width", 300); pd.set_option("display.max_columns", 50)
    print(df[["production", "region", "quantity", "rank", "share_of_variance", "run", "subrun", "evt", "sample", "reco_topology", "truth_category_authoritative", "nu_pdg", "cc_nc", "mode", "true_Enu_GeV", "true_protons_gt35MeV", "true_neutrons", "max_weight", "min_weight", "in_final_selection", "in_other_production_top10"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
