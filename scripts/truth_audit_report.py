#!/usr/bin/env python
"""Tables + plots for the reco-proton audit and the candidate-policy audit (MC truth used ONLY to evaluate).

    python scripts/truth_audit_report.py bnb_cv
Reads $SP_DATA/truth_match/<sample> (scripts/truth_match_scan.py) and $SP_DATA/baseline_scan/<sample>.
Writes tables/proton_audit/*.csv, plots/proton_audit/*.png, tables/candidate_policy/*.csv.
"""
from __future__ import annotations
import glob, json, os, sys
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src"))
from sbnd_single_photon import scanio as X, selection as SEL  # noqa: E402

sample = sys.argv[1] if len(sys.argv) > 1 else "bnb_cv"
SPD = os.environ["SP_DATA"]
TP, CP = REPO / "tables" / "proton_audit", REPO / "tables" / "candidate_policy"
PP = REPO / "plots" / "proton_audit"
for d in (TP, CP, PP):
    d.mkdir(parents=True, exist_ok=True)


def load_truth():
    R, C, T = [], [], []
    for p in sorted(glob.glob(f"{SPD}/truth_match/{sample}/*.npz"), key=lambda p: int(Path(p).stem)):
        z = np.load(p); fi = int(Path(p).stem)
        for lst, pre in ((R, "row_"), (C, "cand_"), (T, "tp_")):
            df = pd.DataFrame({k[len(pre):]: z[k] for k in z.files if k.startswith(pre)}); df.insert(0, "file", fi); lst.append(df)
    return pd.concat(R, ignore_index=True), pd.concat(C, ignore_index=True), pd.concat(T, ignore_index=True), len(R)


R, C, T, nfiles = load_truth()
R = R[R.valid]; C = C[C.valid]; T = T[T.valid]
MP = {2212: "proton", 13: "mu", 211: "pi", 11: "e", 22: "gamma", 2112: "neutron"}
def pdgname(x):
    return "unmatched" if pd.isna(x) else MP.get(abs(int(x)), "other")
R["tname"] = R.mpdg.map(pdgname)
R["nu_origin"] = R.mnu >= 0
meta = dict(sample=sample, truth_files=nfiles, valid_rows=int(len(R)), valid_candidates=int(len(C)))

# ============ proton audit ============
P = R[R.typ == 2212].copy()
P["ke35"] = P.ke > 35
def fr(df):
    n = len(df)
    return dict(n_rows=n, unmatched=float((df.tname == "unmatched").mean()) if n else None,
                truth_proton=float((df.tname == "proton").mean()) if n else None,
                truth_gamma=float((df.tname == "gamma").mean()) if n else None,
                truth_mu_pi=float(df.tname.isin(["mu", "pi"]).mean()) if n else None,
                truth_other=float((~df.tname.isin(["proton", "gamma", "mu", "pi", "unmatched"])).mean()) if n else None,
                nu_origin=float(df.nu_origin.mean()) if n else None,
                proton_and_nu_origin=float(((df.tname == "proton") & df.nu_origin).mean()) if n else None)
rows = []
for lab, sub in (("all reco type==2212", P), ("KE>35", P[P.ke35]), ("KE<=35", P[~P.ke35]),
                 ("KE>35 & included==1", P[P.ke35 & (P.inc == 1)]), ("KE>35 & included!=1", P[P.ke35 & (P.inc != 1)])):
    rows.append(dict(selection=lab, **fr(sub)))
for pool in sorted(P.pool.unique()):
    rows.append(dict(selection=f"KE>35 & pool=={int(pool)}", **fr(P[P.ke35 & (P.pool == pool)])))
pd.DataFrame(rows).to_csv(TP / f"{sample}_proton_row_purity.csv", index=False)
# truth identity of ALL reco rows by reco type (does type 2212 mislabel?)
(R.assign(ke35=R.ke > 35).groupby(["typ", "tname"]).size().unstack(fill_value=0)).to_csv(TP / f"{sample}_reco_type_vs_truth_pdg.csv")
# included flag content
(R.groupby(["inc", "pool", "typ"]).size().rename("n_rows").reset_index()).to_csv(TP / f"{sample}_included_pool_type_counts.csv", index=False)
# KE response for reco proton rows matched to truth protons
Q = P[(P.tname == "proton") & (P.mke > 0)].copy()
Q["pur"] = Q.q_best / Q.q_row
Q["ratio"] = Q.ke / Q.mke
bins = [0, 35, 60, 100, 150, 250, 400, 700, 2000]
Q["tbin"] = pd.cut(Q.mke, bins)
def resp(df):
    r = df.ratio
    return pd.Series(dict(n=len(df), median_reco_over_true=r.median(), p16=r.quantile(.16), p84=r.quantile(.84),
                          frac_within_20pct=float(((r > .8) & (r < 1.2)).mean())))
resp_t = Q.groupby("tbin", observed=True).apply(resp, include_groups=False)
resp_t.to_csv(TP / f"{sample}_proton_ke_response_by_true_ke.csv")
cmp = dict(median_reco_over_true_KE=float(Q.ratio.median()), median_reco_over_true_total_E=float((Q.ke / (Q.mke + 938.272)).median()),
           n=int(len(Q)), pearson_log=float(np.corrcoef(np.log(Q.ke.clip(1e-3)), np.log(Q.mke.clip(1e-3)))[0, 1]))
for lab, sub in (("included==1", Q[Q.inc == 1]), ("included!=1", Q[Q.inc != 1])):
    cmp["median_ratio_" + lab] = float(sub.ratio.median()) if len(sub) else None; cmp["n_" + lab] = int(len(sub))
fig, ax = plt.subplots(1, 2, figsize=(10, 4.2))
ax[0].hist2d(Q.mke, Q.ke, bins=[np.logspace(0, 3.3, 50)] * 2, norm=matplotlib.colors.LogNorm(), cmap="viridis")
ax[0].plot([1, 2000], [1, 2000], "r--", lw=1); ax[0].axhline(35, color="w", lw=.6)
ax[0].set(xscale="log", yscale="log", xlabel="matched true proton KE [MeV]", ylabel="reco kine_energy_particle [MeV]",
          title=f"reco proton rows, truth-matched protons (n={len(Q)})")
for lab, sub in (("included==1", Q[Q.inc == 1]), ("included!=1", Q[Q.inc != 1])):
    ax[1].hist(sub.ratio.clip(0, 3), bins=60, histtype="step", label=f"{lab} (n={len(sub)})", density=True)
ax[1].axvline(1, color="k", lw=.6); ax[1].set(xlabel="reco KE / true KE (clipped at 3)", ylabel="density"); ax[1].legend()
fig.tight_layout(); fig.savefig(PP / f"{sample}_proton_ke_response.png", dpi=110); plt.close(fig)
# 0p/1p/2p sensitivity of the definition: per candidate, rows of type 2212 (reco) vs rows that are TRUE neutrino protons
def counts(df):
    return df.groupby(["file", "ev", "nu"]).size().rename("n")
c35 = counts(P[P.ke35]).rename("n_reco35")
c35i = counts(P[P.ke35 & (P.inc == 1)]).rename("n_reco35_inc")
c35t = counts(P[P.ke35 & (P.tname == "proton") & P.nu_origin]).rename("n_reco35_trueproton_nu")
allc = R.groupby(["file", "ev", "nu"]).size().rename("nrows").to_frame()
allc = allc.join([c35, c35i, c35t]).fillna(0)
cat = lambda s: np.clip(s, 0, 2).astype(int)
mig = pd.crosstab(cat(allc.n_reco35), cat(allc.n_reco35_inc)); mig.index = ["0p", "1p", "ge2p"][: len(mig)]; mig.columns = ["0p", "1p", "ge2p"][: mig.shape[1]]
mig.to_csv(TP / f"{sample}_category_migration_all_vs_included_only.csv")
mig2 = pd.crosstab(cat(allc.n_reco35), cat(allc.n_reco35_trueproton_nu)); mig2.to_csv(TP / f"{sample}_category_reco35_vs_reco_rows_that_are_true_nu_protons.csv")
# finding efficiency of beam-nu truth protons that reached a candidate dominated by that nu
Cd = C[["file", "ev", "nu", "dom_nu"]].rename(columns={"dom_nu": "mnu"})
T2 = T.merge(Cd.groupby(["file", "ev", "mnu"]).size().rename("has_cand").reset_index(), how="left", on=["file", "ev", "mnu"])
T2["in_cand"] = T2.has_cand.notna()
T2["found35"] = T2.reco_ke_best > 35; T2["found_any"] = T2.reco_ke_best.notna()
T2["tbin"] = pd.cut(T2.tke, [35, 60, 100, 150, 250, 400, 700, 2000])
eff = []
for lab, sub in (("all truth nu-protons KE>35", T2[T2.tke > 35]), ("... with q_in_blobs>0", T2[(T2.tke > 35) & (T2.mqblobs > 0)]),
                 ("... in a candidate dominated by their nu", T2[(T2.tke > 35) & T2.in_cand]),
                 ("... in such a candidate and q_in_blobs>0", T2[(T2.tke > 35) & T2.in_cand & (T2.mqblobs > 0)])):
    eff.append(dict(denominator=lab, n=len(sub), found_as_reco_proton_ke35=float(sub.found35.mean()) if len(sub) else None,
                    found_as_any_reco_proton_row=float(sub.found_any.mean()) if len(sub) else None))
pd.DataFrame(eff).to_csv(TP / f"{sample}_proton_finding_fraction.csv", index=False)
sub = T2[(T2.tke > 35) & T2.in_cand & (T2.mqblobs > 0)]
sub.groupby("tbin", observed=True).agg(n=("found35", "size"), found_ke35=("found35", "mean")).to_csv(TP / f"{sample}_proton_finding_fraction_by_true_ke.csv")
json.dump(dict(meta=meta, ke_comparison=cmp), open(TP / f"{sample}_proton_audit_summary.json", "w"), indent=1)

# ============ candidate-policy audit ============
cfg = SEL.load_config(); tab = X.load_scan(f"{SPD}/baseline_scan", sample)
fidx = tab["file"]["file_index"][tab["ev_file"][tab["c_gev"]]]
cdf = pd.DataFrame(dict(file=fidx, ev=tab["c_gev"] - np.searchsorted(np.cumsum([0] + [0]), 0), nu=tab["c_nu_index"].astype(int)))
cdf["ev"] = tab["c_ev"]
cdf["flash_group"] = tab["c_flash_group"]; cdf["flash_tpc"] = tab["c_flash_tpc"]; cdf["flash_pe"] = tab["c_flash_pe"]
cdf["flash_time"] = tab["c_flash_time_us"]; cdf["gev"] = tab["c_gev"]
chain = X.candidate_chain(tab, cfg); stages = {"candidate": chain["candidate_in_valid_event"], "final": chain[cfg["cuts"][-1]["name"]]}
cdf["valid_cand"] = chain["candidate_in_valid_event"]; cdf["final"] = stages["final"]
cdf["keep_dedup"] = X.dedup_keep(tab)
# 1) frequencies over the FULL sample
valid_ev = tab["ev_valid"]; nc = np.bincount(tab["c_gev"][cdf.valid_cand.values], minlength=len(valid_ev))
freq = pd.Series(nc[valid_ev]).value_counts().sort_index().rename("n_valid_events").to_frame()
freq["fraction"] = freq.n_valid_events / freq.n_valid_events.sum(); freq.to_csv(CP / f"{sample}_candidate_multiplicity_full.csv")
fin_n = np.bincount(tab["c_gev"][cdf.final.values], minlength=len(valid_ev))
pol = {}
for p in ("first", "any", "dedup_any"):
    pol[p] = int(X.event_pass(tab, stages["final"], p).sum())
pol["events_with_>1_final_passing_candidate"] = int((fin_n > 1).sum())
pol["events_with_>1_candidate_valid"] = int((nc > 1).sum())
fg = cdf[cdf.valid_cand].groupby("gev").flash_group.nunique()
cs = cdf[cdf.valid_cand].groupby("gev").size()
pol["multi_cand_events_all_same_flash_group"] = int(((cs > 1) & (fg == 1)).sum().item() if hasattr(((cs > 1) & (fg == 1)).sum(), "item") else 0)
json.dump(pol, open(CP / f"{sample}_policy_event_counts_full.json", "w"), indent=1)
# 2) truth diagnostics on the files with truth matching
M = cdf.merge(C[["file", "ev", "nu", "dom_nu", "q_cand", "q_nu", "q_dom", "n_nu_in_cand", "nu_pdg", "nu_ccnc", "nvx", "nvy", "nvz"]], how="inner", on=["file", "ev", "nu"])
M = M[M.valid_cand]
M["nu_frac"] = M.q_nu / M.q_cand
from sbnd_single_photon import truth as TR   # PROVISIONAL taxonomy box: used only to separate dirt from active-volume neutrinos
M["in_box"] = TR.ActiveVolume().contains(M.nvx.values, M.nvy.values, M.nvz.values)
M["kind"] = np.where(M.nu_frac < 0.5, "cosmic", np.where(M.in_box, "nu_active", "nu_dirt"))
cnt = M.groupby(["file", "ev"]).size().rename("ncand")
M = M.join(cnt, on=["file", "ev"])
multi = M[M.ncand >= 2].sort_values(["file", "ev", "nu"])
def pair_class(g):
    a, b = g.iloc[0], g.iloc[1]
    same_fg = a.flash_group == b.flash_group
    ka, kb = a.kind, b.kind
    if ka.startswith("nu") and kb.startswith("nu") and a.dom_nu == b.dom_nu:
        c = "same_interaction_split(" + ka + ")"
    else:
        c = "+".join(sorted([ka, kb]))
    return pd.Series(dict(cls=c, same_flash_group=bool(same_fg), same_flash_tpc=bool(a.flash_tpc == b.flash_tpc), n=len(g),
                          first_kind=ka, second_kind=kb, ncand=len(g)))


if len(multi):
    pc = multi.groupby(["file", "ev"]).apply(pair_class, include_groups=False)
    pc.groupby(["cls", "same_flash_group", "same_flash_tpc"]).size().rename("n_events").reset_index().to_csv(CP / f"{sample}_multicand_truth_classes.csv", index=False)
    pc.groupby(["first_kind", "second_kind"]).size().rename("n_events").reset_index().to_csv(CP / f"{sample}_multicand_kind_of_index0_vs_index1.csv", index=False)
    pol["multi_cand_events_truth_matched"] = int(len(pc)); pol["pair_class"] = pc.cls.value_counts().to_dict()
# 3) which candidate each policy picks when the event passes (truth purity of the SELECTED candidate)
out = []
for p in ("first", "any", "dedup_any"):
    idx = X.chosen_candidate(tab, stages["final"], p); idx = idx[idx >= 0]
    sel = pd.DataFrame(dict(file=fidx[idx], ev=tab["c_ev"][idx], nu=tab["c_nu_index"][idx].astype(int)))
    s = sel.merge(C[["file", "ev", "nu", "q_nu", "q_cand", "nvx", "nvy", "nvz"]], how="inner", on=["file", "ev", "nu"])
    s["in_box"] = TR.ActiveVolume().contains(s.nvx.values, s.nvy.values, s.nvz.values)
    out.append(dict(policy=p, n_selected_events_truth_matched=len(s),
                    n_selected_candidate_neutrino_dominated=int((s.q_nu / s.q_cand >= .5).sum()),
                    frac_neutrino_dominated=float((s.q_nu / s.q_cand >= .5).mean()) if len(s) else None,
                    n_selected_candidate_active_nu_dominated=int(((s.q_nu / s.q_cand >= .5) & s.in_box).sum()),
                    frac_active_nu_dominated=float(((s.q_nu / s.q_cand >= .5) & s.in_box).mean()) if len(s) else None))
pd.DataFrame(out).to_csv(CP / f"{sample}_selected_candidate_truth_purity_by_policy.csv", index=False)
json.dump(pol, open(CP / f"{sample}_policy_event_counts_full.json", "w"), indent=1, default=str)
print(json.dumps(dict(meta=meta, ke=cmp, policy=pol), indent=1, default=str))
