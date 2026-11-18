#!/usr/bin/env python
"""Frozen corrected-Round-1 selection on the Nov16 nueCC MC control and the data controls (beam-off, open data, Run-3 BNB). DIAGNOSTIC; no truth interpretation for data,
no new sideband, no normalisation beyond what Round 1 defined (beam-off normalisation is the open blocker G: only per-event rates are given).

    source env/setup_eaf.sh && python scripts/wcl1116_replay_controls.py

OLD = the SAME builder + scorer run on the fg1 / open-data merged CAFs (tables in analysis_tables_old). Run-3 BNB has no Round-1 counterpart.
"""
from wcl1116_replay_common import *
import json

SAMPLES = [("nuecc", "intrinsic nueCC MC (control)", True), ("beam_off", "beam-off data", True), ("beam_on_open", "open BNB data (older production for OLD)", True),
           ("run3bnb", "Run-3 BNB beam-on data", False)]


def tab_for(root, s, cfg):
    ev, c_raw, files = read_tables(root, s)
    return ev, to_D(c_raw, ev, cfg), files


def stage_counts(ev, c):
    f = ev_stage_flags(c)
    d = {"events_in_tables": int(len(ev)), "usable_events_wc_valid": int(ev.wc_valid.sum()), "candidates": int(len(c))}
    for s in STAGES:
        d[f"events_{s}"] = int(f[s].sum())
    d["selected_events"] = d["events_n20br1"]; d["selected_candidates"] = int(c.pass_final.sum())
    d["selected_per_1000_usable_events"] = 1000 * d["selected_events"] / max(d["usable_events_wc_valid"], 1)
    return d, f


def main():
    cfg = load_cfg(); rows = []; mig_rows = []; shift_rows = []; stage_rows = []
    for s, what, has_old in SAMPLES:
        ev_n, c_n, files_n = tab_for(NEW, s, cfg)
        dn, fn = stage_counts(ev_n, c_n); dn.update(sample=s, what=what, production="nov16", total_pot=float(files_n.total_pot.sum())); rows.append(dn)
        if not (OLD / s / "candidates.parquet").exists():
            print(s, "no OLD table"); continue
        ev_o, c_o, files_o = tab_for(OLD, s, cfg)
        do, fo = stage_counts(ev_o, c_o); do.update(sample=s, what=what, production="old (fg1 / open-data production)", total_pot=float(files_o.total_pot.sum())); rows.append(do)
        ix = fo.index.union(fn.index); a, b = fo.reindex(ix, fill_value=False), fn.reindex(ix, fill_value=False)
        po, pn = a.n20br1.values, b.n20br1.values
        mv = np.select([po & pn, po & ~pn, ~po & pn], ["old pass -> new pass", "old pass -> new fail", "old fail -> new pass"], "old fail -> new fail")
        fcs = first_changed_stage(a, b)
        M = pd.DataFrame(dict(movement=mv, first_changed=fcs.values), index=ix)
        # events present in only one production's tables (the union index above only contains events with >=1 candidate)
        ko, kn = set(map(tuple, ev_o[RSE].values)), set(map(tuple, ev_n[RSE].values))
        mig_rows.append(dict(sample=s, events_old=len(ko), events_new=len(kn), matched_events=len(ko & kn), only_old=len(ko - kn), only_new=len(kn - ko),
                             old_pass_new_pass=int(((mv == "old pass -> new pass")).sum()), old_pass_new_fail=int((mv == "old pass -> new fail").sum()),
                             old_fail_new_pass=int((mv == "old fail -> new pass").sum())))
        for (m, f), g in M[M.movement != "old fail -> new fail"].groupby(["movement", "first_changed"]):
            if m != "old pass -> new pass":
                stage_rows.append(dict(sample=s, movement=m, first_changed_stage=f, N=len(g)))
        # candidate multiplicity / evaluable / filled migration (matched events)
        mo = ev_o[RSE + ["wc_valid", "ncand"]].merge(ev_n[RSE + ["wc_valid", "ncand"]], on=RSE, suffixes=("_old", "_new"))
        mig_rows[-1].update(wc_valid_lost=int(((mo.wc_valid_old == 1) & (mo.wc_valid_new == 0)).sum()), wc_valid_gained=int(((mo.wc_valid_old == 0) & (mo.wc_valid_new == 1)).sum()),
                            ncand_more=int((mo.ncand_new > mo.ncand_old).sum()), ncand_fewer=int((mo.ncand_new < mo.ncand_old).sum()), ncand_same=int((mo.ncand_new == mo.ncand_old).sum()),
                            cand_present_to_absent=int(((mo.ncand_old > 0) & (mo.ncand_new == 0)).sum()), cand_absent_to_present=int(((mo.ncand_old == 0) & (mo.ncand_new > 0)).sum()))
        # score shifts, matched candidates
        cols = ["c_nu_index"] + [f"c_score_{m}" for m in L.MODELS] + ["c_shw_sp_n_20mev_showers", "c_shw_sp_n_20br1_showers", "c_shw_sp_filled"]
        j = c_o[RSE + cols].merge(c_n[RSE + cols], on=RSE + ["c_nu_index"], suffixes=("_old", "_new"))
        for m in L.MODELS:
            o, n = j[f"c_score_{m}_old"].to_numpy(float), j[f"c_score_{m}_new"].to_numpy(float); ok = np.isfinite(o) & np.isfinite(n); d = (n - o)[ok]
            shift_rows.append(dict(sample=s, model=m, n_matched_candidates=int(ok.sum()), median_shift=float(np.median(d)) if ok.any() else np.nan,
                                   frac_cross_up=float(((o[ok] <= FROZEN[m]) & (n[ok] > FROZEN[m])).mean()) if ok.any() else np.nan,
                                   frac_cross_down=float(((o[ok] > FROZEN[m]) & (n[ok] <= FROZEN[m])).mean()) if ok.any() else np.nan))
        for k in ("c_shw_sp_n_20mev_showers", "c_shw_sp_n_20br1_showers", "c_shw_sp_filled"):
            shift_rows.append(dict(sample=s, model=k, n_matched_candidates=len(j), median_shift=float((j[k + "_new"] - j[k + "_old"]).median()),
                                   frac_cross_up=float((j[k + "_new"] > j[k + "_old"]).mean()), frac_cross_down=float((j[k + "_new"] < j[k + "_old"]).mean())))
        M.reset_index().to_parquet(DER / f"controls_movement_{s}.parquet", index=False)
    cs = pd.DataFrame(rows); cs.to_csv(OUT / "controls_selection_counts.csv", index=False)
    pd.DataFrame(mig_rows).to_csv(OUT / "controls_old_vs_new_migration.csv", index=False)
    pd.DataFrame(stage_rows).to_csv(OUT / "controls_first_changed_stage.csv", index=False)
    pd.DataFrame(shift_rows).to_csv(OUT / "controls_score_shifts.csv", index=False)
    keep = ["sample", "production", "usable_events_wc_valid", "candidates"] + [f"events_{s}" for s in STAGES] + ["selected_candidates", "selected_per_1000_usable_events"]
    print(cs[keep].round(3).to_string(index=False)); print(pd.DataFrame(mig_rows).T.to_string())


if __name__ == "__main__":
    main()
