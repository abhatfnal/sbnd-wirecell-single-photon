#!/usr/bin/env python
"""Expected purity / efficiency tables of the FROZEN legacy selection on the old fg1-era reconstruction and on WCLocal2026Nov16. MC evaluation only; nothing tuned.

    source env/setup_eaf.sh && python scripts/ncdelta_purity_tables.py
Normalisation: every component scaled to POT_TARGET (1e20); signal from the dedicated sample, background from the generic CV with in-region natural NC-Delta EVENTS removed.
"""
from ncdelta_purity_common import *
import json

cfg = load_cfg(); ST = PU.STAGES; EFFN = 12427
sigN, nat_in = natural_signal_in_region()
nat_keys = nat_in[KEY]
res = {}; led = {}
for prod in PRODUCTIONS:
    sev, sc = load_signal(prod, cfg); st_s = sev[KEY].merge(PU.event_stage_table(sc, KEY), on=KEY, how="left")
    for s in ST:
        st_s[s] = st_s[s].fillna(False).astype(bool); st_s["ch_" + s] = st_s["ch_" + s].fillna("")
    cev, cc, cfiles = load_cv(prod, cfg); pot_cv = float(cfiles.total_pot.sum())
    st_c = PU.event_stage_table(cc, KEY)
    rm = PU.remove_in_region_natural_signal(st_c, nat_keys, KEY)
    cc["cat_approx"] = approx_category(cc, cev); cc["cat"] = cc["cat_approx"]
    auth_all = authoritative_category(prod, cc, sigN)                 # None until the full-candidate truth scan exists
    if auth_all is not None:
        cc["cat"] = auth_all
    cat_source = "authoritative (production-matched, all candidates)" if auth_all is not None else "dominant-neutrino approximation"
    res[prod] = dict(sig=st_s, cv=st_c, cv_removed=rm, cc=cc, cev=cev, pot_cv=pot_cv)
    led[prod] = dict(category_source=cat_source, w_sig=PU.weight(POT_TARGET, POT_SIGNAL), w_cv=PU.weight(POT_TARGET, pot_cv), pot_cv=pot_cv, n_removed_events=int(rm.sum()), n_removed_selected_final=int((rm & st_c.n20br1).sum()))
assert abs(res["old_fg1"]["pot_cv"] - res["nov16"]["pot_cv"]) / res["nov16"]["pot_cv"] < 1e-9
json.dump(led, open(TAB / "normalisation_numbers.json", "w"), indent=1, default=float)

# ---- 1. cumulative efficiency + purity per stage ------------------------------------------------
rows = []
for prod in PRODUCTIONS:
    R = res[prod]; ws, wc = led[prod]["w_sig"], led[prod]["w_cv"]
    for s in ST:
        ns = int(R["sig"][s].sum()); nb_all = int(R["cv"][s].sum()); nb = int((R["cv"][s] & ~R["cv_removed"]).sum())
        S, sS = ns * ws, np.sqrt(ns) * ws; B, sB = nb * wc, np.sqrt(nb) * wc; P, sP = PU.purity(S, sS, B, sB)
        e, lo, hi = binom(ns, EFFN)
        rows.append(dict(production=prod, stage=s, N_sig=ns, N_cv_selected_raw=nb_all, N_cv_background=nb, S_per_1e20=S, S_err=sS, B_per_1e20=B, B_err=sB, purity=P, purity_err=sP,
                         efficiency_pct=100 * e, eff_lo68_pct=100 * lo, eff_hi68_pct=100 * hi, S_over_B=S / B if B > 0 else np.nan))
cum = pd.DataFrame(rows); cum.to_csv(TAB / "cumulative_efficiency_purity.csv", index=False)
ov = cum[cum.stage == "n20br1"].drop(columns="stage"); ov.to_csv(TAB / "overall_purity.csv", index=False)

# ---- 2. reconstructed-topology purity (final and every stage) -----------------------------------
rows = []
for prod in PRODUCTIONS:
    R = res[prod]; ws, wc = led[prod]["w_sig"], led[prod]["w_cv"]
    for s in ST:
        chs = PU.merge_Np(R["sig"].loc[R["sig"][s], "ch_" + s]); chb = PU.merge_Np(R["cv"].loc[R["cv"][s] & ~R["cv_removed"], "ch_" + s])
        chs_f = R["sig"].loc[R["sig"][s], "ch_" + s]; chb_f = R["cv"].loc[R["cv"][s] & ~R["cv_removed"], "ch_" + s]
        for lab, a, b in (("1g0p", chs_f, chb_f), ("1g1p", chs_f, chb_f), ("ge2p", chs_f, chb_f), ("1gNp", chs, chb), ("mixed", chs_f, chb_f)):
            ns = int((a == lab).sum()); nb = int((b == lab).sum()); S, sS, B, sB = ns * ws, np.sqrt(ns) * ws, nb * wc, np.sqrt(nb) * wc; P, sP = PU.purity(S, sS, B, sB)
            rows.append(dict(production=prod, stage=s, reco_channel=lab, N_sig=ns, N_cv_background=nb, S_per_1e20=S, S_err=sS, B_per_1e20=B, B_err=sB, purity=P, purity_err=sP))
top = pd.DataFrame(rows); top.to_csv(TAB / "topology_purity_by_stage.csv", index=False); top[top.stage == "n20br1"].to_csv(TAB / "topology_purity.csv", index=False)

# ---- 3. background composition (approximate dominant-neutrino taxonomy; final stage cross-checked below) ----
rows = []
for prod in PRODUCTIONS:
    R = res[prod]; wc = led[prod]["w_cv"]; cc = R["cc"]; masks = PU.stage_masks(cc); rm = R["cv_removed"]
    rm_key = pd.concat([R["cv"][KEY], rm.rename("rm")], axis=1)
    cc2 = cc[KEY + ["cat", "reco_proton_cat"]].merge(rm_key, on=KEY, how="left")
    for s in ST:
        sub = cc2[masks[s] & ~cc2.rm.fillna(False).to_numpy(bool)]
        ev_cat = sub.groupby(KEY).cat.agg(lambda x: x.iloc[0] if x.nunique() == 1 else "MULTI_OR_AMBIGUOUS")
        for cat, n in ev_cat.value_counts().items():
            rows.append(dict(production=prod, stage=s, category=cat, N=int(n), expected_per_1e20=n * wc, err=np.sqrt(n) * wc))
comp = pd.DataFrame(rows); comp.to_csv(TAB / "background_composition_by_stage.csv", index=False); comp[comp.stage == "n20br1"].to_csv(TAB / "background_composition.csv", index=False)

# ---- 4. taxonomy validation vs the production-matched (authoritative) categories at the final selection ------------
auth = {}
old_cls = pd.read_csv(SF / "background_mechanisms" / "selected_event_classes.csv"); auth["old_fg1"] = old_cls[old_cls.event_class == "background"].set_index(KEY).event_cand_category
import wcl1116_replay_bnb as RB1
deep = pd.read_parquet(DER / "bnb_new_deep.parquet"); ev_n, c_n, _ = RB1.selected_new(cfg)
new_cls = RB1.classify(c_n, deep, sigN); auth["nov16"] = new_cls[new_cls.event_class == "background"].set_index(KEY).event_cand_category
rows = []
for prod in PRODUCTIONS:
    R = res[prod]; cc = R["cc"]; m = PU.stage_masks(cc)["n20br1"]; sub = cc[m]
    ap = sub.groupby(KEY).cat_approx.agg(lambda x: x.iloc[0] if x.nunique() == 1 else "MULTI_OR_AMBIGUOUS")
    j = pd.concat([auth[prod].rename("authoritative"), ap.rename("approx")], axis=1, join="inner")
    ct = pd.crosstab(j.authoritative, j.approx); ct.insert(0, "production", prod); ct.to_csv(TAB / f"taxonomy_validation_crosstab_{prod}.csv")
    rows.append(dict(production=prod, n_background_events=len(j), agree=int((j.authoritative == j.approx).sum()), agree_frac=float((j.authoritative == j.approx).mean())))
pd.DataFrame(rows).to_csv(TAB / "taxonomy_validation.csv", index=False)

# ---- 4b. approximation vs authoritative truth classification at EVERY stage (candidate level and event level), needs the full-candidate scan ------
rows = []; allct = []
for prod in PRODUCTIONS:
    R = res[prod]; cc = R["cc"]
    if led[prod]["category_source"].startswith("dominant"):
        continue
    masks = PU.stage_masks(cc); rm_key = pd.concat([R["cv"][KEY], R["cv_removed"].rename("rm")], axis=1); cc2 = cc[KEY + ["cat", "cat_approx"]].merge(rm_key, on=KEY, how="left")
    for st in ST:
        m = masks[st]; sub = cc2[m]
        cand_agree = float((sub.cat == sub.cat_approx).mean()) if len(sub) else np.nan
        sub = sub[~sub.rm.fillna(False).to_numpy(bool)]
        ea = sub.groupby(KEY).cat.agg(lambda x: x.iloc[0] if x.nunique() == 1 else "MULTI_OR_AMBIGUOUS"); eb = sub.groupby(KEY).cat_approx.agg(lambda x: x.iloc[0] if x.nunique() == 1 else "MULTI_OR_AMBIGUOUS")
        rows.append(dict(production=prod, stage=st, n_candidates=int(m.sum()), candidate_agree_frac=cand_agree, n_background_events=len(ea), event_agree_frac=float((ea == eb).mean()) if len(ea) else np.nan))
        if st in ("numu", "n20br1"):
            ct = pd.crosstab(ea.rename("authoritative"), eb.rename("approx")); ct.insert(0, "stage", st); ct.insert(0, "production", prod); allct.append(ct.reset_index())
pd.DataFrame(rows).to_csv(TAB / "taxonomy_validation_by_stage.csv", index=False)
if allct:
    pd.concat(allct).to_csv(TAB / "taxonomy_validation_by_stage_crosstabs.csv", index=False)
# authoritative final-stage composition (production-matched)
rows = []
for prod in PRODUCTIONS:
    wc = led[prod]["w_cv"]
    for cat, n in auth[prod].value_counts().items():
        rows.append(dict(production=prod, category=cat, N=int(n), expected_per_1e20=n * wc, err=np.sqrt(n) * wc))
pd.DataFrame(rows).to_csv(TAB / "background_composition_final_production_matched.csv", index=False)

# ---- 5. efficiency-vs-purity: one score varied, all other frozen cuts fixed (descriptive reference, NOT a threshold choice) -------
def event_any(c, mask, keys):
    return set(map(tuple, c.loc[mask, keys].drop_duplicates().to_numpy()))

rows = []
for prod in PRODUCTIONS:
    R = res[prod]; ws, wc = led[prod]["w_sig"], led[prod]["w_cv"]; sev, sc = load_signal(prod, cfg); cc = R["cc"]
    rm_set = set(map(tuple, R["cv"].loc[R["cv_removed"], KEY].to_numpy()))
    for mod in PU.MODELS:
        grid = np.unique(np.round(np.append(np.linspace(-3, 3, 61), PU.FROZEN_R1[mod]), 3))      # the exact frozen threshold is always a grid point
        for tag, c in (("sig", sc), ("cv", cc)):
            n20 = c["cum_n_20mev_showers_gt0"].to_numpy(bool) & c.bdt_evaluable.to_numpy(bool); br1 = (c.c_shw_sp_n_20br1_showers.to_numpy(float) == 1)
            others = n20 & br1
            for o in PU.MODELS:
                if o != mod:
                    others = others & (c[f"c_score_{o}"].to_numpy(float) > PU.FROZEN_R1[o])
            c.attrs[f"{mod}_others"] = others
        for t in grid:
            ms = sc.attrs[f"{mod}_others"] & (sc[f"c_score_{mod}"].to_numpy(float) > t); mb = cc.attrs[f"{mod}_others"] & (cc[f"c_score_{mod}"].to_numpy(float) > t)
            ns = len(event_any(sc, ms, KEY) & set(map(tuple, sev[KEY].to_numpy()))); eb = event_any(cc, mb, KEY); nb = len(eb - rm_set)
            S, sS, B, sB = ns * ws, np.sqrt(ns) * ws, nb * wc, np.sqrt(nb) * wc; P, sP = PU.purity(S, sS, B, sB)
            rows.append(dict(production=prod, model=mod, threshold=float(t), N_sig=ns, N_cv_background=nb, efficiency_pct=100 * ns / EFFN, purity=P, purity_err=sP, S_per_1e20=S, B_per_1e20=B,
                             frozen_point=bool(np.isclose(t, PU.FROZEN_R1[mod]))))
pd.DataFrame(rows).to_csv(TAB / "efficiency_vs_purity_single_score_scan.csv", index=False)
import pickle; pickle.dump({p: dict(led=led[p]) for p in PRODUCTIONS}, open(DER / "purity_led.pkl", "wb"))
print(cum[["production", "stage", "N_sig", "N_cv_background", "S_per_1e20", "B_per_1e20", "purity", "purity_err", "efficiency_pct"]].round(4).to_string(index=False))
print(top[top.stage == "n20br1"].round(4).to_string(index=False)); print(pd.read_csv(TAB / "taxonomy_validation.csv")); print(json.dumps(led, indent=1, default=float))
