#!/usr/bin/env python
"""Candidate-associated background mechanisms of the selected BNB CV events (frozen baseline, policy any). MC evaluation only; no cut changes.

    python scripts/background_mechanisms_report.py            # needs scan stages `deep` (and the derived analysis table)
Writes tables/background_mechanisms/*, plots/background_mechanisms/*, and the compact derived table + metadata under
$SP_DATA/background_mechanisms/bnb_cv/ (outside Git).
"""
from __future__ import annotations
import glob, hashlib, json, os, subprocess, sys, warnings
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sbnd_single_photon import background_mechanisms as BM, background_truth as BT, natural_signal as NS, truth as T

SPD = Path(os.environ["SP_DATA"]); R = SPD / "background_mechanisms" / "bnb_cv"; TB = SPD / "analysis_tables" / "bnb_cv"
OUT = REPO / "tables" / "background_mechanisms"; PL = REPO / "plots" / "background_mechanisms"; OUT.mkdir(parents=True, exist_ok=True); PL.mkdir(parents=True, exist_ok=True)
js = {}
meta_tab = json.load(open(TB / "metadata.json")); POT = float(meta_tab["sum_TotalPOT"]) if "sum_TotalPOT" in meta_tab else float(pd.read_parquet(TB / "files.parquet").total_pot.sum())

cands = pd.read_parquet(TB / "candidates.parquet"); events = pd.read_parquet(TB / "events.parquet")
sig = pd.read_parquet(SPD / "natural_ncdelta_bnb_cv" / "signal_neutrinos.parquet")
deep = pd.concat([pd.read_parquet(p) for p in sorted(glob.glob(str(R / "deep_pieces" / "*.parquet")))], ignore_index=True)
deep = BM.add_categories(deep, sig)
passing = cands[cands.pass_final.values].rename(columns={"c_nu_index": "nu_index"})
sel = passing.merge(deep.drop(columns=[c for c in deep.columns if c in passing.columns and c not in BM.CKEY]), on=BM.CKEY, how="left", validate="one_to_one")
assert len(sel) == len(passing) == len(deep), (len(sel), len(passing), len(deep))
assert sel.tm_top_nu.notna().all(), "passing candidates without association"
sig_ev = NS.classify_selected_events(passing.rename(columns={"nu_index": "c_nu_index"}), sig.rename(columns={"k": "nu_k"}))
ev = BM.event_level(sel, sig_ev)
acc = BM.accounting(ev); js["accounting"] = acc
js["validation"] = dict(total_649=acc["total"] == 649, signal_like_14=acc["signal_like"] == 14, background_635=acc["background"] == 635, mixed_0=acc["mixed"] == 0,
                        T_match_signal_candidates=int((sel.cand_category == "SIGNAL_NCDELTA").sum()), event_signal_like_equals_T_match_signal=bool(
                            set(map(tuple, ev[ev.event_class == "signal_like"][BM.KEY].values)) == set(map(tuple, sel[sel.cand_category == "SIGNAL_NCDELTA"][BM.KEY].values))))
print(json.dumps(js["validation"]))

# ---- Task 1: association audit numbers
a1 = dict(n_passing=len(sel), n_events=sel[BM.KEY].drop_duplicates().shape[0], multi_passing_events=int((ev.n_pass > 1).sum()),
          tm_n_matches_quantiles=sel.tm_n.quantile([0, .5, .9, 1]).tolist(), top_iou_quantiles=sel.tm_top_iou.quantile([0, .05, .25, .5, .75, .95, 1]).round(4).tolist(),
          mutual_top=int((sel.tm_mutual == 1).sum()), not_mutual=int((sel.tm_mutual != 1).sum()),
          neutrino_top=int((sel.tm_top_nu >= 0).sum()), cosmic_or_unmatched_top=int((sel.tm_top_nu < 0).sum()), ambiguous_ge2_nu=int((sel.tm_n_distinct_nu >= 2).sum()),
          with_cosmic_object_also_matched=int(((sel.tm_n_cosmic > 0) & (sel.tm_top_nu >= 0)).sum()),
          agree_with_overlap_dominant=int((sel.dom_nu == sel.tm_top_nu).sum()),
          disagree_with_overlap_dominant=int((sel.dom_nu != sel.tm_top_nu).sum()),
          link_to_recmcnu_dist_max_cm=float(sel.mnu_link_dist_cm.max()), unlinked_neutrino_matches=int(((sel.tm_top_nu >= 0) & sel.mnu_k.isna()).sum()))
dis = sel[sel.dom_nu != sel.tm_top_nu][BM.KEY + ["nu_index", "dom_nu", "tm_top_nu", "tm_top_iou", "tm_n_distinct_nu", "cand_category", "dom_q", "dom_q_cand"]]
dis.to_csv(OUT / "association_disagreements_Tmatch_vs_Toverlap.csv", index=False)
js["association_audit"] = a1

# ---- Task 2: taxonomy + comparison with the old event-level category
old_names = np.array(T.CATEGORIES)
sel = sel.merge(events[BM.KEY + ["t_code"]], on=BM.KEY, how="left"); sel["old_event_category"] = old_names[sel.t_code.astype(int).values]
sel = sel.merge(ev[BM.KEY + ["event_class", "n_pass", "event_cand_category", "reco_channel"]], on=BM.KEY, how="left")
MAP = {"NC_PI0": "NC_PI0", "CC_PI0": "CC_PI0", "NUE_CC": "NUE_CC", "NUMU_CC": "NUMU_CC", "OTHER_NC": "OTHER_NC", "OTHER_CC": "OTHER_CC", "DIRT_NO_ACTIVE": "OUTSIDE_TPC_NU", "COSMIC_NO_NU": "COSMIC_OR_UNMATCHED"}
sel["old_mapped"] = sel.old_event_category.map(MAP).fillna("(no equivalent: " + sel.old_event_category + ")")
sel["changed_interpretation"] = (sel.old_mapped != sel.cand_category)
bgm = sel[sel.event_class == "background"]
xt = pd.crosstab(bgm.old_event_category, bgm.cand_category); xt.to_csv(OUT / "old_event_vs_candidate_associated_crosstab_635.csv")
xt_all = pd.crosstab(sel.old_event_category, sel.cand_category); xt_all.to_csv(OUT / "old_event_vs_candidate_associated_crosstab_649.csv")
ex = bgm[bgm.changed_interpretation].groupby(["old_event_category", "cand_category"]).size().sort_values(ascending=False)
js["taxonomy_change"] = dict(n_background=len(bgm), n_changed=int(bgm.changed_interpretation.sum()), n_unchanged=int((~bgm.changed_interpretation).sum()),
                             n_changed_excluding_multi_active=int(bgm[bgm.old_event_category != "MULTI_ACTIVE"].changed_interpretation.sum()),
                             transitions={f"{a}->{b}": int(n) for (a, b), n in ex.items()},
                             examples=bgm[bgm.changed_interpretation].sort_values(["old_event_category", "cand_category"]).groupby(["old_event_category", "cand_category"]).head(2)[
                                 ["file_index", "ev", "nu_index", "old_event_category", "cand_category", "tm_top_iou", "mnu_pdg", "mnu_ccnc", "mnu_x", "mnu_y", "mnu_z"]].round(2).to_dict("records"))
cols = ["file_index", "ev", "run", "subrun", "evt", "nu_index", "event_class", "reco_channel", "n_pass", "old_event_category", "cand_category", "changed_interpretation",
        "tm_top_nu", "tm_top_iou", "tm_second_iou", "tm_n", "tm_n_distinct_nu", "tm_n_cosmic", "tm_mutual", "mnu_k", "mnu_pdg", "mnu_ccnc", "mnu_mode", "mnu_x", "mnu_y", "mnu_z", "in_tpc", "out_dist_cm",
        "k_n_pi0", "k_n_p35", "dom_nu", "sh_origin", "sh_frac", "sh_primary"]
sel[cols].round(4).to_csv(OUT / "candidate_truth_category.csv", index=False)

# ---- Task 3: composition by reco channel
comp = BM.composition(bgm, POT); comp.round(5).to_csv(OUT / "background_composition_by_channel.csv", index=False)
js["background_channels"] = acc["background_by_channel"]; js["pot"] = POT
order = [c for c in BM.CLASS_ORDER if c in set(bgm.event_cand_category)]
fig, ax = plt.subplots(1, 3, figsize=(15, 4.6))
cm = plt.get_cmap("tab10")
for axi, ch in zip(ax, ["1g0p", "1g1p", "ge2p_diag"]):
    c = comp[(comp.channel == ch) & (comp.category != "TOTAL")].set_index("category").reindex(order).fillna(0)
    bottom = 0
    for i, cat in enumerate(order):
        v = c.loc[cat, "rate_per_1e20"]; axi.bar([0], [v], bottom=bottom, color=cm(i), label=f"{cat} ({int(c.loc[cat,'count'])})"); bottom += v
    axi.set_title(f"{ch}: {int(c['count'].sum())} selected non-signal events", fontsize=10); axi.set_ylabel("neutrino-induced selected events / 1e20 POT"); axi.set_xticks([])
    axi.legend(fontsize=7, loc="upper right")
fig.suptitle("candidate-associated composition of the selected non-signal BNB CV events (frozen baseline, `any`; no cosmic-only component; stat. only)", fontsize=10)
fig.tight_layout(); fig.savefig(PL / "background_composition_by_channel.png", dpi=110); plt.close(fig)

# ---- Task 4: selected-shower truth origin
b = bgm.copy()
b["sh_origin"] = b.sh_origin.fillna("no_matching_shower_row")
so = pd.crosstab(b.sh_origin, b.reco_channel); so["all"] = so.sum(axis=1); so.to_csv(OUT / "selected_shower_origin_by_channel.csv")
so2 = pd.crosstab(b.cand_category, b.sh_origin); so2.to_csv(OUT / "selected_shower_origin_by_category.csv")
mp = dict(n_candidates=len(sel), unique_energy_row_match=int((sel.sel_n_row_hits == 1).sum()), no_row_match=int((sel.sel_n_row_hits == 0).sum()),
          selected_shower_is_max_ke_shower=int((sel.sel_shower_is_max_ke_shower == True).sum()), selected_shower_not_max_ke_shower=int((sel.sel_shower_is_max_ke_shower == False).sum()),
          row_type_counts=sel.sel_row_type.value_counts().to_dict(), row_included_counts=sel.sel_row_included.value_counts().to_dict())
fr = b.sh_frac.dropna()
js["shower_origin"] = dict(mapping=mp, origin_by_channel=so.to_dict("index"), dominant_charge_fraction_quantiles=fr.quantile([0, .05, .25, .5, .75, 1]).round(4).tolist(),
                           primary_fraction=float(b.sh_primary.fillna(False).mean()),
                           photon_ancestor_pdg=b[b.sh_origin.isin(["photon"])].sh_ancestor_pdg.value_counts().to_dict(),
                           electron_ancestor_pdg=b[b.sh_origin == "electron_positron"].sh_ancestor_pdg.value_counts().to_dict())

# ---- Task 5: pi0
p0 = b[b.cand_category.isin(["NC_PI0", "CC_PI0"])].copy()
for j in (1, 2):
    for c in ("E",):
        pass
rows = []
for _, r in p0.iterrows():
    d = r.to_dict()
    e1, e2 = r.get("ph1_E", np.nan), r.get("ph2_E", np.nan)
    ks = BT.pi0_photon_summary(e1, e2) if np.isfinite(e1) and np.isfinite(e2) else dict(lead_mev=np.nan, sub_mev=np.nan, asymmetry=np.nan, opening_angle_deg=np.nan)
    rank = int(r.selected_photon_rank) if pd.notna(r.get("selected_photon_rank")) else 0
    other = 2 if rank == 1 else (1 if rank == 2 else 0)
    labs = BT.photon_fate_labels(d, f"ph{other}_") if other else ["selected_shower_not_a_pi0_daughter"]
    rows.append(dict(file_index=r.file_index, ev=r.ev, category=r.cand_category, channel=r.reco_channel, pf_n_pi0=r.get("pf_n_pi0"), pi0_E_mev=r.get("pi0_E") * 1000 if pd.notna(r.get("pi0_E")) else np.nan,
                     pi0_p_mev=r.get("pi0_p") * 1000 if pd.notna(r.get("pi0_p")) else np.nan, n_daughters=r.get("pi0_n_daughter_photons"), pi0_vtx_in_tpc=r.get("pi0_vtx_in_tpc"),
                     matched_vertex_in_tpc=r.in_tpc, selected_photon_rank=rank, selected_origin=r.sh_origin, selected_ancestor_pdg=r.get("sh_ancestor_pdg"),
                     truth_protons=r.k_n_p35, **ks, other_photon_E_mev=(r.get(f"ph{other}_E") * 1000 if other else np.nan), other_labels=";".join(labs)))
P = pd.DataFrame(rows); P.round(3).to_csv(OUT / "pi0_candidates.csv", index=False)
def lab_counts(df):
    from collections import Counter
    c = Counter(l for s in df.other_labels for l in s.split(";")); return dict(c)
pis = {}
for (cat, ch), g in P.groupby(["category", "channel"]):
    pis[f"{cat}|{ch}"] = dict(n=len(g), n_pi0_pf=g.pf_n_pi0.value_counts().to_dict(), selected_matches_daughter=int((g.selected_photon_rank > 0).sum()),
                                 selected_is_lead=int((g.selected_photon_rank == 1).sum()), selected_is_sub=int((g.selected_photon_rank == 2).sum()),
                                 pi0_E_q=g.pi0_E_mev.quantile([.05, .5, .95]).round(0).tolist(), lead_q=g.lead_mev.quantile([.05, .5, .95]).round(0).tolist(), sub_q=g.sub_mev.quantile([.05, .5, .95]).round(0).tolist(),
                                 asym_q=g.asymmetry.quantile([.05, .5, .95]).round(3).tolist(), opening_q=g.opening_angle_deg.quantile([.05, .5, .95]).round(1).tolist(),
                                 pi0_vtx_in_tpc=int((g.pi0_vtx_in_tpc == True).sum()), truth_protons=g.truth_protons.value_counts().to_dict(),
                                 other_photon_labels=lab_counts(g), selected_origin=g.selected_origin.value_counts().to_dict())
js["pi0"] = pis

# ---- Task 6: nue CC
nu = b[b.cand_category == "NUE_CC"].copy()
nue = {}
for ch, g in nu.groupby("reco_channel"):
    nue[ch] = dict(n=len(g), origin=g.sh_origin.value_counts().to_dict(), primary_lepton=int(g.sel_is_primary_nue_lepton.fillna(False).sum()),
                   photon_ancestor_pdg=g[g.sh_origin == "photon"].sh_ancestor_pdg.value_counts().to_dict(), electron_ancestor_pdg=g[g.sh_origin == "electron_positron"].sh_ancestor_pdg.value_counts().to_dict(),
                   shower_primary=int(g.sh_primary.fillna(False).sum()))
js["nue"] = nue
VARS = [("c_shw_sp_energy", "main shower E [MeV]"), ("c_shw_sp_shw_vtx_dis", "shw_vtx_dis"), ("c_shw_sp_min_dis", "shw min_dis"), ("c_shw_sp_lowest_dQ_dx", "lowest dQ/dx"), ("c_shw_sp_medium_dQ_dx", "medium dQ/dx"),
        ("c_shw_sp_highest_dQ_dx", "highest dQ/dx"), ("c_score_numu", "BDT numu"), ("c_score_other", "BDT other"), ("c_score_ncpi0", "BDT ncpi0"), ("c_score_nue", "BDT nue"), ("c_np35", "reco protons >35 MeV"),
        ("c_lead_proton_ke_mev", "leading proton KE"), ("c_kine_reco_Enu", "reco E_nu [MeV]")]
def qtab(df, label):
    rows = []
    for ch, g in df.groupby("reco_channel"):
        for v, n in VARS:
            x = g[v].astype(float); x = x[np.isfinite(x)]
            if "dQ_dx" in v: x = x[x < 50]
            if len(x): rows.append(dict(group=label, channel=ch, variable=v, n=len(x), q05=x.quantile(.05), q25=x.quantile(.25), q50=x.quantile(.5), q75=x.quantile(.75), q95=x.quantile(.95)))
    return pd.DataFrame(rows)
qt = pd.concat([qtab(nu, "NUE_CC"), qtab(p0[p0.category == "NC_PI0"] if False else b[b.cand_category == "NC_PI0"], "NC_PI0"), qtab(b[b.cand_category == "CC_PI0"], "CC_PI0")]); qt.round(3).to_csv(OUT / "variable_quantiles_by_class_channel.csv", index=False)

# ---- Task 7: outside TPC / cosmic
out = b[b.cand_category == "OUTSIDE_TPC_NU"]
out[["file_index", "ev", "reco_channel", "mnu_pdg", "mnu_ccnc", "mnu_mode", "mnu_x", "mnu_y", "mnu_z", "out_dist_cm", "mnu_edep", "mnu_E", "sh_origin", "sh_frac", "old_event_category", "tm_top_iou"]].round(3).to_csv(OUT / "outside_tpc_candidates.csv", index=False)
cos = b[b.cand_category.isin(["COSMIC_OR_UNMATCHED", "MULTI_OR_AMBIGUOUS"])]
cos[["file_index", "ev", "reco_channel", "cand_category", "tm_n", "tm_top_nu", "tm_n_distinct_nu", "tm_top_iou", "ovl_cand_pdg", "ovl_cand_nu_idx", "ovl_cand_frac", "ovl_cand_mother_pdg", "sh_origin", "old_event_category"]].round(3).to_csv(OUT / "cosmic_or_ambiguous_candidates.csv", index=False)
js["outside_cosmic"] = dict(n_outside=len(out), outside_by_channel=out.reco_channel.value_counts().to_dict(),
                            dist_cm_quantiles=out.out_dist_cm.quantile([0, .25, .5, .75, 1]).round(1).tolist(), edep_gt0=int((out.mnu_edep > 0).sum()), edep_quantiles=out.mnu_edep.quantile([.05, .5, .95]).round(4).tolist(),
                            flavour=out.mnu_pdg.value_counts().to_dict(), ccnc=out.mnu_ccnc.value_counts().to_dict(), mode=out["mnu_mode"].value_counts().to_dict(), origin=out.sh_origin.value_counts().to_dict(),
                            old_category=out.old_event_category.value_counts().to_dict(),
                            vertex_x_range=[float(out.mnu_x.min()), float(out.mnu_x.max())], vertex_y_range=[float(out.mnu_y.min()), float(out.mnu_y.max())], vertex_z_range=[float(out.mnu_z.min()), float(out.mnu_z.max())],
                            n_cosmic_or_unmatched=int((cos.cand_category == "COSMIC_OR_UNMATCHED").sum()), n_ambiguous=int((cos.cand_category == "MULTI_OR_AMBIGUOUS").sum()),
                            cosmic_dom_pdg=cos[cos.cand_category == "COSMIC_OR_UNMATCHED"].ovl_cand_pdg.value_counts().to_dict(), cosmic_by_channel=cos.groupby("cand_category").reco_channel.value_counts().to_dict() if False else
                            {k: v for k, v in cos.groupby(["cand_category", "reco_channel"]).size().astype(int).items() for k, v in [(f"{k[0]}|{k[1]}", v)]} if False else {f"{k[0]}|{k[1]}": int(v) for k, v in cos.groupby(["cand_category", "reco_channel"]).size().items()})

# ---- Task 8: truth -> reco proton migration by class
mig = BM.migration_by_class(b)
for cat, m in mig.items():
    m.to_csv(OUT / f"proton_migration_{cat}.csv")
intpc = b[b.cand_category.isin(["NC_PI0", "CC_PI0", "NUE_CC", "NUMU_CC", "OTHER_NC", "OTHER_CC"])]
allm = BM.migration_by_class(intpc.assign(cand_category="IN_TPC_NU"))["IN_TPC_NU"]; allm.to_csv(OUT / "proton_migration_ALL_IN_TPC_NEUTRINO_CLASSES.csv")
js["migration"] = {k: v.to_dict("index") for k, v in mig.items()}; js["migration_all_in_tpc"] = allm.to_dict("index")
mech = {}
for cat, g in b.groupby("cand_category"):
    has = g[g.k_n_p35.notna() & (g.tm_top_nu >= 0) & (g.tm_n_distinct_nu < 2)].copy()
    has["t"] = np.minimum(has.k_n_p35.astype(int), 2)
    for name, mask in (("truth0p_reco1p", (has.t == 0) & (has.reco_proton_cat == 1)), ("truth1p_reco0p", (has.t == 1) & (has.reco_proton_cat == 0)),
                       ("truth0p_reco0p", (has.t == 0) & (has.reco_proton_cat == 0)), ("truth1p_reco1p", (has.t == 1) & (has.reco_proton_cat == 1)),
                       ("truth_ge2p_reco0p", (has.t == 2) & (has.reco_proton_cat == 0)), ("truth_ge2p_reco1p", (has.t == 2) & (has.reco_proton_cat == 1))):
        gg = has[mask]
        if len(gg): mech[f"{cat}|{name}"] = dict(n=len(gg), **BM.mechanism_counts(gg))
hasall = intpc[intpc.k_n_p35.notna()].copy(); hasall["t"] = np.minimum(hasall.k_n_p35.astype(int), 2)
for name, mask in (("truth0p_reco1p", (hasall.t == 0) & (hasall.reco_proton_cat == 1)), ("truth1p_reco0p", (hasall.t == 1) & (hasall.reco_proton_cat == 0))):
    gg = hasall[mask]; mech[f"ALL_IN_TPC_NU|{name}"] = dict(n=len(gg), **BM.mechanism_counts(gg))
pd.DataFrame(mech).T.fillna(0).astype(int).to_csv(OUT / "proton_migration_mechanisms.csv")
def types(g):
    s = g.get("tp_other_pid_types", pd.Series(dtype=object)).dropna().astype(str)
    return pd.Series([x for v in s for x in v.split(";") if x]).value_counts().to_dict()
js["other_pid_row_types"] = {"truth1p_reco0p_in_tpc_nu": types(hasall[(hasall.t == 1) & (hasall.reco_proton_cat == 0)]), "truth0p_reco0p_ge1_truth_p": {},
                             "truth1p_reco1p_in_tpc_nu": types(hasall[(hasall.t == 1) & (hasall.reco_proton_cat == 1)]), "truth_ge2p_reco_any": types(hasall[hasall.t == 2])}
js["migration_mechanisms"] = mech
# truth proton content of the reco channels (topology vs migration question)
tc = pd.crosstab(hasall.reco_proton_cat.map(BM.CH_LABEL), hasall.t.map({0: "truth 0p", 1: "truth 1p", 2: "truth >=2p"})); tc.to_csv(OUT / "reco_channel_vs_truth_protons_in_tpc_nu.csv"); js["reco_channel_vs_truth"] = tc.to_dict("index")
for cat in ["NC_PI0", "CC_PI0", "NUE_CC"]:
    g = hasall[hasall.cand_category == cat]
    js[f"truth_vs_reco_{cat}"] = pd.crosstab(g.reco_proton_cat.map(BM.CH_LABEL), g.t.map({0: "truth 0p", 1: "truth 1p", 2: "truth >=2p"})).to_dict("index")

# ---- Task 12: compact derived table (outside Git)
dcols = ["file_index", "source_file", "run", "subrun", "evt", "nu_index", "reco_channel", "old_event_category", "cand_category", "event_class", "mnu_k", "tm_top_nu", "tm_top_iou", "tm_second_iou", "tm_n",
         "tm_n_distinct_nu", "tm_mutual", "sh_origin", "sh_pdg", "sh_frac", "sh_primary", "sh_ancestor_pdg", "k_n_p35", "reco_proton_cat", "pf_n_pi0", "pi0_E", "ph1_E", "ph2_E", "selected_photon_rank",
         "sel_is_primary_nue_lepton", "in_tpc", "out_dist_cm", "mnu_pdg", "mnu_ccnc", "mnu_mode", "mnu_x", "mnu_y", "mnu_z", "mnu_edep", "c_shw_sp_energy", "c_shw_sp_shw_vtx_dis", "c_shw_sp_min_dis",
         "c_shw_sp_lowest_dQ_dx", "c_shw_sp_medium_dQ_dx", "c_shw_sp_highest_dQ_dx", "c_score_numu", "c_score_other", "c_score_ncpi0", "c_score_nue", "c_np35", "c_lead_proton_ke_mev", "c_kine_reco_Enu",
         "rp_primary_signal", "rp_secondary_proton", "rp_other_pdg_same_nu", "rp_leftover_inc3", "tp_found", "tp_row_below_thr", "tp_row_other_pid", "tp_no_row"]
dcols = [c for c in dcols if c in sel.columns]
dt = sel[dcols].copy(); dt.to_parquet(R / "background_mechanism_table.parquet", index=False)
def sha(p): return hashlib.sha256(open(p, "rb").read()).hexdigest()
try: commit = subprocess.check_output(["git", "-C", str(REPO), "rev-parse", "HEAD"], text=True).strip()
except Exception: commit = "unknown"
meta = dict(schema_version="1.0", git_commit_at_build=commit, parent_commit="b9878cb0cdbb7beb3662e6a3e5a302c19e0c8777", source_bnb_table_metadata_sha256=sha(TB / "metadata.json"),
            source_candidates_sha256_prefix=sha(TB / "candidates.parquet")[:16], manifest_sha256=meta_tab.get("manifest_sha256"), classification_schema="candidate_taxonomy_v1: T_match level3 top IoU; signal>outside_TPC>pi0>flavour",
            categories=list(BT.CATEGORIES), events=int(len(ev)), passing_candidates=int(len(sel)), key=["source_file", "run", "subrun", "evt", "nu_index"], columns=dcols,
            provisional=dict(tpc_box_cm=dict(x=[-200, 200], y=[-200, 200], z=[0, 500]), proton_threshold_mev=35.0, candidate_policy="any", fiducial_volume=None))
json.dump(meta, open(R / "background_mechanism_table.metadata.json", "w"), indent=1)
js["derived_table"] = dict(rows=len(dt), columns=len(dcols), path=str(R / "background_mechanism_table.parquet"))
json.dump(js, open(OUT / "summary.json", "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
print(json.dumps({k: js[k] for k in ("accounting", "taxonomy_change")}, default=str)[:3000])
