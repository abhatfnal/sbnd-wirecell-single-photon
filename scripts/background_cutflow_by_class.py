#!/usr/bin/env python
"""Frozen-baseline cutflow by candidate-associated truth class for ALL 241,845 BNB CV candidates (characterisation of the inherited cuts only).

    python scripts/background_mechanisms_scan.py recnu --workers 40   # per-interaction truth (pdg, CC/NC, pi0, vertex) for every file
    python scripts/background_cutflow_by_class.py

For the full candidate list the association is the DOMINANT-CHARGE truth neutrino of ``wc.T_overlap`` already stored in the derived table
(``dom_nu``); the production ``T_match`` association was only evaluated for the 649 selected candidates (deep scan) and a subset of files (light scan),
and the two are compared below. The category is that of the neutrino interaction matched to the candidate, never the event content.
"""
from __future__ import annotations
import glob, json, os, sys, warnings
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sbnd_single_photon import background_mechanisms as BM, background_truth as BT, exclusive_signal as X, selection as SEL
from sbnd_single_photon.truth import ActiveVolume

SPD = Path(os.environ["SP_DATA"]); R = SPD / "background_mechanisms" / "bnb_cv"; TB = SPD / "analysis_tables" / "bnb_cv"
OUT = REPO / "tables" / "background_mechanisms"; PL = REPO / "plots" / "background_mechanisms"
cfg = SEL.load_config(); stages = X.stage_defs(cfg)
c = pd.read_parquet(TB / "candidates.parquet")
rn = pd.concat([pd.read_parquet(p) for p in sorted(glob.glob(str(R / "recnu_pieces" / "*.parquet")))], ignore_index=True)
assert rn.file_index.nunique() == 37742, f"recnu incomplete: {rn.file_index.nunique()} files"
sig = pd.read_parquet(SPD / "natural_ncdelta_bnb_cv" / "signal_neutrinos.parquet")
c["_bdt_eval"] = c[stages[1][1]] & c["bdt_evaluable"]
has = c.dom_nu.notna() & (c.dom_nu >= 0) & c.dom_ok.fillna(False).astype(bool)
cn = c[has][BM.KEY + ["c_nu_index", "dom_nu_vx", "dom_nu_vy", "dom_nu_vz"]].reset_index().rename(columns={"index": "_i"})
m = cn.merge(rn[BM.KEY + ["k", "x", "y", "z", "n_pi0", "pdg", "iscc"]], on=BM.KEY, how="left")
m["dist"] = np.sqrt((m.dom_nu_vx - m.x) ** 2 + (m.dom_nu_vy - m.y) ** 2 + (m.dom_nu_vz - m.z) ** 2)
m = m.sort_values(["_i", "dist"]).drop_duplicates("_i").set_index("_i")
c["link_k"] = np.nan; c["k_n_pi0"] = np.nan
c.loc[m.index, "link_k"] = np.where(m.dist < 1.0, m.k, np.nan); c.loc[m.index, "k_n_pi0"] = np.where(m.dist < 1.0, m.n_pi0, np.nan)
unl = int((has & c.link_k.isna()).sum())
s = sig[BM.KEY + ["k"]].rename(columns={"k": "link_k"}).assign(_sig=True)
c = c.merge(s, on=BM.KEY + ["link_k"], how="left"); c["is_signal"] = c._sig.fillna(False).astype(bool)
in_tpc = ActiveVolume().contains(c.dom_nu_vx, c.dom_nu_vy, c.dom_nu_vz).fillna(False).values
top = np.where(has, c.dom_nu.fillna(-9), BT.UNMATCHED).astype(int)
c["cand_category_overlap"] = [BT.classify_candidate(t, 1, 1 if h else 0, p, cc == 0, n, it, sg) for t, h, p, cc, n, it, sg in
                              zip(top, has.values, c.dom_nu_pdg.fillna(0).values, c.dom_nu_ccnc.fillna(1).values, c.k_n_pi0.fillna(0).values, in_tpc, c.is_signal.values)]
c["cand_class"] = c.cand_category_overlap.replace({k: "OTHER_NU" for k in BM.OTHER_NU})
js = dict(n_candidates=len(c), n_neutrino_dominant=int(has.sum()), neutrino_dominant_unlinked_to_recmcnu=unl, categories=c.cand_category_overlap.value_counts().to_dict())
st = [(s_, col) for s_, col in stages]
cf = BM.cutflow_by_class(c, st, cat_col="cand_class", by_reco=True)
cf.to_csv(OUT / "cutflow_by_class_all_candidates.csv", index=False)
cf2 = BM.cutflow_by_class(c, st, cat_col="cand_category_overlap", by_reco=True); cf2.to_csv(OUT / "cutflow_by_class_all_candidates_detailed.csv", index=False)
assert (cf[cf.split == "all"].candidates.sum() == len(c)) and (cf[cf.split == "all"].final.sum() == int(c.pass_final.sum()))
js["final_total"] = int(c.pass_final.sum()); js["final_by_class"] = cf[cf.split == "all"].set_index("category").final.to_dict()
# agreement T_match (light scan subset) vs T_overlap (all)
lp = sorted(glob.glob(str(R / "light_pieces" / "*.parquet")))
if lp:
    L = pd.concat([pd.read_parquet(p) for p in lp], ignore_index=True)
    sg = sig[BM.KEY + ["k"]]
    L = BM.add_categories(L.rename(columns={}), sg)
    j = L.rename(columns={"nu_index": "c_nu_index"}).merge(c[BM.KEY + ["c_nu_index", "cand_category_overlap"]], on=BM.KEY + ["c_nu_index"], how="inner")
    js["tmatch_vs_overlap"] = dict(files=len(lp), n_candidates=len(j), agree=int((j.cand_category == j.cand_category_overlap).sum()), agree_fraction=float((j.cand_category == j.cand_category_overlap).mean()))
    pd.crosstab(j.cand_category, j.cand_category_overlap).to_csv(OUT / "tmatch_vs_toverlap_category_crosstab_subset.csv")
json.dump(js, open(OUT / "cutflow_by_class_summary.json", "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
# plot
a = cf[cf.split == "all"].set_index("category"); names = [s_ for s_, _ in st]
fig, ax = plt.subplots(1, 3, figsize=(17, 5))
for axi, sp in zip(ax, ["all", "1g0p", "1g1p"]):
    d = cf[cf.split == sp].set_index("category")
    for cat in d.index:
        v = d.loc[cat, names].values.astype(float)
        if d.loc[cat, "candidates"] > 0:
            axi.plot(range(len(names)), v / d.loc[cat, "candidates"], "o-", label=f"{cat} ({int(d.loc[cat,'candidates'])})")
    axi.set_yscale("log"); axi.set_xticks(range(len(names))); axi.set_xticklabels(names, rotation=60, ha="right", fontsize=8); axi.set_title(f"candidates of reco proton category: {sp}", fontsize=10); axi.set_ylabel("fraction of the class' candidates")
ax[0].legend(fontsize=7)
fig.suptitle("frozen-baseline cutflow by candidate-associated class (T_overlap dominant neutrino; inherited cuts, characterisation only)", fontsize=10); fig.tight_layout(); fig.savefig(PL / "cutflow_by_class.png", dpi=105); plt.close(fig)
print(json.dumps(js, default=str)[:2000]); print(cf[cf.split == "all"].to_string())
