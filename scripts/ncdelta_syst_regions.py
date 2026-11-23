#!/usr/bin/env python
"""Neutrino-systematic data/MC comparison in the control regions (open data; FINAL selection stays blocked). PRELIMINARY, event level.

    source env/setup_eaf.sh && export BEARER_TOKEN_FILE=... && python scripts/ncdelta_syst_regions.py plan|extract|analyze [--regions SB_ncpi0 SB_other ...] [--workers 24]

Unit = the EVENT (any region-passing candidate; event once), for data, S and B alike. B owner: all region-passing candidates of the event must share one production-matched interaction (`mnu_k`);
otherwise the event is unresolved and NOT varied (held at nominal weight). S owner: the dedicated-sample signal interaction. Histogram value of an event = its lowest-index region-passing candidate.
Per-universe bin yields are accumulated on the fly (no per-event storage). The prediction is S + B (MC only; the cosmic-only/beam-off component is NOT included: scale blocked), at the open-data POT.
Covariance = sum of independent sources (flux, beamline G4, GENIE xsec, xsec extras, GENIE FSI) from the in-band weight functions; S and B vary with the same universe index. Data statistics enter
as the Pearson (expected) variance in the chi-square (Neyman shown as a cross-check). NOT in the covariance: detector, cosmic/beam-off, dirt, POT, NC-Delta signal model, imp_weight, unresolved-owner events.
"""
import argparse, json, multiprocessing as mp, pickle
from scipy import stats
from ncdelta_syst_common import *
from sbnd_single_photon import samples as S, syst_weights as SW
import ncdelta_syst_covariance as CV            # component definitions + function table + plot style

TAB = REPO / "tables" / "ncdelta_purity_datamc"; REG_ALL = ["SB_ncpi0", "SB_other", "SB_nue", "SB_numu", "preselection"]
VIEWS = ["all", "energy", "topo2"]; VNB = [1, 8, 2]; EB = len(E_BINS) - 1
KIND = {"preselection": "preselection", "SB_numu": "sideband", "SB_other": "sideband", "SB_ncpi0": "sideband", "SB_nue": "sideband"}
COMPS = CV.COMP; U = NU_TOT


def urls(prod, sample):
    return S.manifest_urls(S.load_samples()[sample]) if prod == "old_fg1" else [r["url"] for r in S.read_manifest(REPO / "manifests" / "wcl1116" / f"{sample}.tsv.gz")]


def rep_events(c, mask):
    """Per event: representative (lowest c_nu_index) region-passing candidate -> energy bin (tails merged, 8 bins) and topology bin (1g0p / 1gNp)."""
    t0 = RG.topology_mask(c, "1g0p")
    sub = c.loc[mask, KEY + RUN + ["c_nu_index", "c_shw_sp_energy"]].assign(t0=np.asarray(t0)[np.asarray(mask)]).sort_values(KEY + ["c_nu_index"])
    g = sub.groupby(KEY); f = g.first().join(g.size().rename("n_pass")).reset_index()
    f["binE"] = np.clip(np.digitize(f.c_shw_sp_energy.to_numpy(float), E_BINS), 1, EB) - 1; f["binT"] = np.where(f.t0, 0, 1)
    return f


def do_plan(regions):
    cfg = load_cfg(); sigN, nat_in = natural_signal_in_region(); DP.check("beam_on_open", "sideband")
    for prod in PRODUCTIONS:
        t, cc, j, masks, cf = background_owners(prod, cfg, sigN, nat_in); cev, _, _ = load_cv(prod, cfg)
        s_own, _ = signal_owners(prod, cfg); sev, sc = load_signal(prod, cfg); sk = set(map(tuple, sev[KEY].dropna().astype(int).to_numpy()))
        sc["in_region"] = [(a, b) in sk for a, b in zip(sc.file_index.to_numpy(), sc.ev.to_numpy())]
        de, dc, df = load_data(prod, "beam_on_open", cfg); bo_e, bo_c, bo_f = load_data(prod, "beam_off", cfg)
        plan = dict(pot_data=float(df.total_pot.sum()), pot_cv=float(cf.total_pot.sum()), B={}, S={}, D={}, OFF={})
        for r in regions:
            DP.check("beam_on_open", KIND[r])
            m = RG.region_mask(cc, r); ev = rep_events(cc, m)
            sub = j[m].copy(); sub["cand_ok"] = sub.cand_category.isin(NU_CATS) & sub.mnu_k.notna() & (sub.tm_n_distinct_nu <= 1) & (sub.tm_n >= 1)
            own = sub.groupby(KEY).agg(all_ok=("cand_ok", "all"), nk=("mnu_k", lambda x: x.dropna().nunique()), k=("mnu_k", "min"), cat=("cand_category", "first"), ncat=("cand_category", "nunique"),
                                       ex=("mnu_x", "first"), ey=("mnu_y", "first"), ez=("mnu_z", "first"), epdg=("mnu_pdg", "first"), anyc=("cand_category", lambda x: (x == "COSMIC_OR_UNMATCHED").any()),
                                       anym=("cand_category", lambda x: (x == "MULTI_OR_AMBIGUOUS").any())).reset_index()
            own["resolved"] = own.all_ok & (own.nk == 1); own["owner_k"] = np.where(own.resolved, own.k, -1).astype(int)
            own["reason"] = np.select([own.resolved, own.anyc, own.anym], ["unique", "cosmic_or_unmatched", "multi_or_ambiguous"], "disagree_or_no_unique")
            b = ev.merge(own.drop(columns=["all_ok", "nk", "k"]), on=KEY, how="left", validate="one_to_one")
            b = b.merge(removed_flags(t), on=KEY, how="left"); b["removed"] = b.removed.fillna(False).astype(bool)
            plan["B"][r] = b[~b.removed].reset_index(drop=True)                                  # in-region natural NC-Delta events are not background (as in the purity tables)
            ms = RG.region_mask(sc, r) & sc.in_region.to_numpy(bool); e = rep_events(sc, ms)
            e = e.merge(s_own[RUN + ["owner_k", "vtx_x", "vtx_y", "vtx_z", "nu_pdg"]], on=RUN, how="left", validate="one_to_one"); assert e.owner_k.notna().all()
            plan["S"][r] = e.rename(columns={"vtx_x": "ex", "vtx_y": "ey", "vtx_z": "ez", "nu_pdg": "epdg"}).assign(resolved=True, owner_k=lambda d: d.owner_k.astype(int))
            plan["D"][r] = rep_events(dc, RG.region_mask(dc, r)); plan["OFF"][r] = rep_events(bo_c, RG.region_mask(bo_c, r))
            print(prod, r, "B ev", len(plan["B"][r]), "resolved", int(plan["B"][r].resolved.sum()), "S ev", len(plan["S"][r]), "data ev", len(plan["D"][r]), "beam-off ev (unscaled)", len(plan["OFF"][r]), flush=True)
        pickle.dump(plan, open(SYST / f"regions_plan_{prod}.pkl", "wb"))


def removed_flags(t):
    return t[KEY + ["removed_in_region_natural_signal"]].rename(columns={"removed_in_region_natural_signal": "removed"})


def jobs_for(prod, regions, chunk=120):
    plan = pickle.load(open(SYST / f"regions_plan_{prod}.pkl", "rb")); jobs = []
    for tag, sample in (("B", "bnb_cv"), ("S", "official_gen2_ncdelta")):
        u = urls(prod, sample); rows = {}
        for ri, r in enumerate(regions):
            d = plan[tag][r]; d = d[d.resolved]
            for x in d.itertuples():
                key = (int(x.file_index), int(x.run), int(x.subrun), int(x.evt), int(x.owner_k))
                it = rows.setdefault(key, dict(run=key[1], subrun=key[2], evt=key[3], ev=int(x.ev), k=key[4], ex=float(x.ex), ey=float(x.ey), ez=float(x.ez), epdg=int(x.epdg), items=[]))
                for vi, b in enumerate((0, int(x.binE), int(x.binT))):
                    it["items"].append((ri * 3 + vi, b))
        byfile = {}
        for key, v in rows.items():
            byfile.setdefault(key[0], []).append(v)
        fl = [(fi, u[fi], rs) for fi, rs in sorted(byfile.items())]
        for i in range(0, len(fl), chunk):
            jobs.append(dict(tag=tag, slot_nb=VNB * len(regions), files=fl[i: i + chunk]))
    return jobs


def do_extract(regions, workers, prods=None):
    for prod in (prods or PRODUCTIONS):
        js = jobs_for(prod, regions); nf = sum(len(j["files"]) for j in js); print(prod, "jobs", len(js), "files", nf, flush=True)
        with mp.get_context("spawn").Pool(workers) as p:
            res = list(p.imap_unordered(SW.region_accum_worker, js))
        out = {}
        for tag in ("B", "S"):
            rr = [r for r in res if r["tag"] == tag]
            if not rr:
                continue
            acc = {s: sum(r["acc"][s] for r in rr) for s in rr[0]["acc"]}; cnt = {s: sum(r["cnt"][s] for r in rr) for s in rr[0]["cnt"]}
            cs = {k: sum(r["counters"][k] for r in rr) for k in rr[0]["counters"] if k != "errs"}; cs["errs"] = [e for r in rr for e in r["counters"]["errs"]][:3]
            out[tag] = dict(acc=acc, cnt=cnt, counters=cs); print(" ", tag, cs, flush=True)
            bad = {k: v for k, v in cs.items() if k not in ("files", "events", "errs") and v}
            assert not bad, f"extraction checks failed: {bad}"
        pickle.dump(dict(regions=regions, **out), open(SYST / f"regions_acc_{prod}_{'-'.join(regions)}.pkl", "wb"))


# --------------------------------------------------------------------------------------------------------------------------------------------------------------
def shape_norm(Dtot):
    return lambda Q: Q * (Dtot / np.where(Q.sum(0, keepdims=True) == 0, np.nan, Q.sum(0, keepdims=True)))


def chi2_pearson(D, P, C, var_stat):
    r = D - P; Ct = C + np.diag(var_stat); return float(r @ np.linalg.solve(Ct, r))


def analyze(regions, tag_name, exclude=()):
    """exclude = names of weight functions left OUT of the covariance (diagnostic variant; default: all in-band functions). The excluded variant writes *_excl_<n>fn files and no figures."""
    rows, mats = [], {}; sfx = "" if not exclude else "_excl"; exclude = set(exclude)
    assert exclude <= set(CV.FT.name), f"unknown functions {exclude - set(CV.FT.name)}"
    FTd = CV.FT.to_dict("records"); inb = [f for f in FTd if f["in_band"]]
    for prod in PRODUCTIONS:
        plan = pickle.load(open(SYST / f"regions_plan_{prod}.pkl", "rb")); acc = pickle.load(open(SYST / f"regions_acc_{prod}_{tag_name}.pkl", "rb"))
        pot = plan["pot_data"]; w = dict(S=pot / POT_SIGNAL, B=pot / plan["pot_cv"])
        for ri, r in enumerate(regions):
            Y, Yn, nraw = {}, {}, {}
            for tag in ("S", "B"):
                d = plan[tag][r]; res = d[d.resolved]; un = d[~d.resolved]; per_view = []
                for vi, nb in enumerate(VNB):
                    col = {0: np.zeros(len(d), int), 1: d.binE.to_numpy(), 2: d.binT.to_numpy()}[vi]; colu = {0: np.zeros(len(un), int), 1: un.binE.to_numpy(), 2: un.binT.to_numpy()}[vi]
                    colr = {0: np.zeros(len(res), int), 1: res.binE.to_numpy(), 2: res.binT.to_numpy()}[vi]
                    n_all, n_un, n_res = (np.bincount(x, minlength=nb) for x in (col, colu, colr))
                    assert np.array_equal(acc[tag]["cnt"][ri * 3 + vi], n_res), f"accumulated counts differ from the plan: {prod} {r} {tag} view {vi}"
                    Y[tag, vi] = w[tag] * (acc[tag]["acc"][ri * 3 + vi] + n_un[:, None]); Yn[tag, vi] = w[tag] * n_all; nraw[tag, vi] = n_all
                per_view.append(None)
            D = {vi: np.bincount({0: np.zeros(len(plan["D"][r]), int), 1: plan["D"][r].binE.to_numpy(), 2: plan["D"][r].binT.to_numpy()}[vi], minlength=nb) for vi, nb in enumerate(VNB)}
            for vi, (view, nb) in enumerate(zip(VIEWS, VNB)):
                P = Yn["S", vi] + Yn["B", vi]; Dv = D[vi].astype(float); Dtot = Dv.sum(); var_mc = nraw["S", vi] * w["S"] ** 2 + nraw["B", vi] * w["B"] ** 2
                Qu = Y["S", vi] + Y["B", vi]; Cc = {}; Cs = {}
                for c in COMPS:
                    Cc[c] = np.zeros((nb, nb)); Cs[c] = np.zeros((nb, nb))
                for fn in inb:
                    if fn["name"] in exclude:
                        continue
                    sl = slice(fn["start"], fn["stop"])
                    for c, gs in COMPS.items():
                        if fn["group"] in gs:
                            Dd, sc = SW.function_deltas(fn, Qu[:, sl], P); Cc[c] += sc * Dd @ Dd.T
                            if nb > 1 and Dtot > 0:
                                Ds, ss = SW.function_deltas(fn, Qu[:, sl], P, shape_norm(Dtot)); Ds = np.nan_to_num(Ds); Cs[c] += ss * Ds @ Ds.T
                Csyst = sum(Cc.values()); mats[prod, r, view] = dict(P=P, D=Dv, var_mc=var_mc, Csyst=Csyst, comps=Cc)
                Ptot = P.sum(); vsyst_tot = float(Csyst.sum()); vmc_tot = float(var_mc.sum())
                if view == "all":
                    R = Dtot / Ptot; dd, dm, ds_ = np.sqrt(Dtot) / Ptot, np.sqrt(vmc_tot) / Ptot, np.sqrt(vsyst_tot) / Ptot; tot = np.hypot(np.hypot(dd, dm), ds_)
                    cr = {c: float(np.sqrt(Cc[c].sum()) / Ptot) for c in COMPS}
                    chi_p = chi2_pearson(Dv, P, Csyst, P + var_mc * 0 + var_mc) if False else float((Dv[0] - P[0]) ** 2 / (vsyst_tot + vmc_tot + P[0])); chi_n = float((Dv[0] - P[0]) ** 2 / (vsyst_tot + vmc_tot + max(Dv[0], 1.0)))
                    rows.append(dict(production=prod, region=r, test="rate_only (integrated)", n_data=int(Dtot), prediction=Ptot, S=Yn["S", vi].sum(), B=Yn["B", vi].sum(), ratio=R, rel_data_stat=dd, rel_mc_stat=dm, rel_syst=ds_, rel_total=tot,
                                     **{f"rel_syst_{c}": v for c, v in cr.items()}, chi2=chi_p, ndof=1, p_value=float(stats.chi2.sf(chi_p, 1)), chi2_neyman=chi_n, n_sigma_from_unity_total=(R - 1) / (R * tot), n_sigma_from_unity_stat_mc_only=(R - 1) / (R * np.hypot(dd, dm))))
                else:
                    idx = np.where(P > 0)[0]; nk = len(idx); dropped = nb - nk                         # bins with zero prediction carry no information and make the covariance singular
                    Dk, Pk, Ck, vk = Dv[idx], P[idx], Csyst[np.ix_(idx, idx)], var_mc[idx]; Dt, Pt = Dk.sum(), Pk.sum()
                    cp = chi2_pearson(Dk, Pk, Ck, vk + Pk); cn = chi2_pearson(Dk, Pk, Ck, vk + np.maximum(Dk, 1.0))
                    rows.append(dict(production=prod, region=r, test=f"rate+shape ({view}, {nk} bins)", n_data=int(Dt), prediction=Pt, ratio=Dt / Pt, chi2=cp, ndof=nk, p_value=float(stats.chi2.sf(cp, nk)), chi2_neyman=cn, bins_dropped_zero_prediction=dropped))
                    if Dt > 0 and nk > 1:                                                  # shape-only: prediction normalised to the data total, universes renormalised too; last bin dropped (sum fixed)
                        Ps = Pk * Dt / Pt; J = Dt * (np.eye(nk) * Pt - Pk[:, None]) / Pt ** 2; Cmc = J @ np.diag(vk) @ J.T
                        Cst = sum(c[np.ix_(idx, idx)] for c in Cs.values()); Cst = Cst * 0 if Dtot == 0 else Cst
                        Cdat = np.diag(Ps) - np.outer(Ps, Ps) / Dt; Ct = (Cst + Cmc + Cdat)[: nk - 1, : nk - 1]; rr_ = (Dk - Ps)[: nk - 1]
                        cs_ = float(rr_ @ np.linalg.solve(Ct, rr_)); Cdn = np.diag(np.maximum(Dk, 1.0)) - np.outer(Dk, Dk) / Dt; Ctn = (Cst + Cmc + Cdn)[: nk - 1, : nk - 1]; cs_n = float(rr_ @ np.linalg.solve(Ctn, rr_))
                        rows.append(dict(production=prod, region=r, test=f"shape-only ({view}, {nk} bins)", n_data=int(Dt), prediction=Pt, ratio=Dt / Pt, chi2=cs_, ndof=nk - 1, p_value=float(stats.chi2.sf(cs_, nk - 1)), chi2_neyman=cs_n, bins_dropped_zero_prediction=dropped))
    df = pd.DataFrame(rows); df.to_csv(TAB / f"syst_sideband_datamc_chi2_{tag_name}{sfx}.csv", index=False); print(df.round(4).to_string(index=False))
    pickle.dump(mats, open(SYST / f"regions_mats_{tag_name}{sfx}.pkl", "wb"))
    other = None if exclude else None
    if exclude:
        other = pd.read_csv(TAB / f"syst_sideband_datamc_chi2_{tag_name}.csv")
    figures(regions, mats, df, tag_name, sfx="" if exclude else "_incl_nG4", other=other)


def figures(regions, mats, df, tag_name, sfx="", other=None):
    """sfx '' = baseline available covariance (WITHOUT reinteractions_neutron_Geant4; main figures); '_incl_nG4' = all in-band functions (backup)."""
    import matplotlib.pyplot as plt
    from sbnd_single_photon import plotstyle as PS; PS.apply_style(); PLT_ = REPO / "plots" / "ncdelta_purity_datamc"
    ttl = {"old_fg1": "old fg1-era reconstruction", "nov16": "WCLocal2026Nov16"}
    for r in regions:
        if r != "SB_ncpi0":
            continue
        fig, ax = plt.subplots(2, 2, figsize=(11, 6.2), gridspec_kw=dict(height_ratios=[3, 1.2], hspace=0.08)); x = np.arange(EB); lab = [f"{a:.0f}" for a in E_BINS[:-1]]
        for ci, prod in enumerate(PRODUCTIONS):
            M = mats[prod, r, "energy"]; P, Dv = M["P"], M["D"]; syst = np.sqrt(np.diag(M["Csyst"])); mc = np.sqrt(M["var_mc"]); tot = np.hypot(syst, mc); a0, a1 = ax[0, ci], ax[1, ci]
            a0.bar(x, P, 0.9, color="#D9D9D9", edgecolor="#777777", lw=0.6, label="MC prediction (S+B)"); a0.errorbar(x, P, yerr=tot, fmt="none", ecolor="#D55E00", lw=3, label="syst. (available) + MC stat."); a0.errorbar(x, P, yerr=mc, fmt="none", ecolor="#333333", lw=1.2, capsize=2, label="MC stat. only")
            a0.errorbar(x, Dv, yerr=np.sqrt(np.maximum(Dv, 1)), fmt="ko", ms=4, label="open beam-on data"); a0.set_ylim(0, 1.55 * float((P + tot).max())); a0.set_ylabel("events"); a0.set_xticks(x); a0.set_xticklabels([]); a0.set_title(ttl[prod], fontsize=10)
            ra = df[(df.production == prod) & (df.region == r) & (df.test.str.startswith("rate_only"))].iloc[0]; rs = df[(df.production == prod) & (df.region == r) & (df.test.str.startswith("rate+shape (energy"))].iloc[0]; sh = df[(df.production == prod) & (df.region == r) & (df.test.str.startswith("shape-only (energy"))].iloc[0]
            oth = "" if other is None else f"\nincl. unresolved neutron-G4 fn: {(other[(other.production == prod) & (other.region == r) & other.test.str.startswith('rate_only')].iloc[0].n_sigma_from_unity_total):+.1f} sigma"
            a0.text(0.97, 0.95, f"Data/MC = {ra.ratio:.2f} +- {ra.rel_total * ra.ratio:.2f}\n(data {100 * ra.rel_data_stat:.1f}%, MC stat {100 * ra.rel_mc_stat:.1f}%, syst {100 * ra.rel_syst:.1f}%)\ndeviation from 1: {ra.n_sigma_from_unity_total:+.1f} sigma{oth}\nrate+shape chi2/ndof = {rs.chi2:.1f}/{rs.ndof:.0f}\nshape-only chi2/ndof = {sh.chi2:.1f}/{sh.ndof:.0f}", transform=a0.transAxes, ha="right", va="top", fontsize=7.5)
            if ci == 0:
                a0.legend(fontsize=6.5, loc="upper left")
            rr = Dv / P; a1.fill_between(np.r_[x - 0.45, x[-1] + 0.45], 1 - np.r_[tot / P, (tot / P)[-1]], 1 + np.r_[tot / P, (tot / P)[-1]], color="#D55E00", alpha=0.25, step="post", lw=0)
            a1.errorbar(x, rr, yerr=np.sqrt(np.maximum(Dv, 1)) / P, fmt="ko", ms=4); a1.axhline(1, color="k", lw=0.6); a1.set_ylim(0, 2); a1.set_ylabel("data / MC"); a1.set_xticks(x); a1.set_xticklabels(lab, fontsize=7); a1.set_xlabel("selected-shower energy, lower bin edge [MeV]", fontsize=8)
        fig.suptitle("NC-pi0-rich sideband (open data) | frozen legacy chain | event level\nPRELIMINARY: " + ("baseline available covariance (flux+GENIE+FSI+G4 WITHOUT the unresolved reinteractions_neutron_Geant4 weight-tail function)" if sfx == "" else "all in-band functions INCLUDING the unresolved reinteractions_neutron_Geant4 weight-tail function") + "\nNOT included: detector, cosmic/beam-off, dirt, POT, signal-model, imp_weight", fontsize=8)
        fig.savefig(PLT_ / f"F_ncpi0_sideband_datamc_with_systematics{sfx}.png", dpi=130, bbox_inches="tight"); plt.close(fig); print("wrote F_ncpi0_sideband_datamc_with_systematics" + sfx + ".png")
    d = df[df.test.str.startswith("rate_only")]; fig, ax = plt.subplots(figsize=(8, 3.8)); xs = np.arange(len(regions))
    for k, prod in enumerate(PRODUCTIONS):
        y = d[d.production == prod].set_index("region").loc[regions]; ax.errorbar(xs + (k - 0.5) * 0.18, y.ratio, yerr=y.ratio * y.rel_total, fmt="o", color=["#0072B2", "#D55E00"][k], capsize=3, label=ttl[prod] + " (total)")
        ax.errorbar(xs + (k - 0.5) * 0.18, y.ratio, yerr=y.ratio * np.hypot(y.rel_data_stat, y.rel_mc_stat), fmt="none", ecolor=["#0072B2", "#D55E00"][k], lw=4, alpha=0.35)
    ax.axhline(1, color="k", lw=0.6); ax.set_xticks(xs); ax.set_xticklabels(regions); ax.set_ylabel("integrated data / MC (event level)"); ax.legend(fontsize=7); ax.set_title("thick: data+MC statistics; thin: + available neutrino systematics. MC excludes cosmic-only (beam-off) component", fontsize=8)
    fig.savefig(PLT_ / f"G_sideband_integrated_ratio_{tag_name}{sfx}.png", dpi=130, bbox_inches="tight"); plt.close(fig); print("wrote G_sideband_integrated_ratio_" + tag_name + sfx + ".png")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("stage", choices=["plan", "extract", "analyze"]); ap.add_argument("--regions", nargs="+", default=["SB_ncpi0", "SB_other", "SB_nue"]); ap.add_argument("--workers", type=int, default=24); ap.add_argument("--productions", nargs="+", default=None); ap.add_argument("--exclude-functions", nargs="*", default=[])
    a = ap.parse_args(); assert all(r in REG_ALL for r in a.regions)
    {"plan": lambda: do_plan(a.regions), "extract": lambda: do_extract(a.regions, a.workers, a.productions), "analyze": lambda: analyze(a.regions, "-".join(a.regions), a.exclude_functions)}[a.stage]()
