#!/usr/bin/env python
"""Truth -> reco proton MIGRATION MECHANISMS for the signal-matched candidates (evaluation only; truth never picks a selected candidate).

    source env/setup_eaf.sh
    python scripts/exclusive_signal_mechanisms.py [--label natural_bnb_cv] [--sample bnb_cv] [--workers 16]

Reuses the row-level truth matching of scripts/truth_match_scan.py (T_kine rows <-> T_overlap <-> T_truth_track), run ONLY on the files that
hold in-region signal events (cached in $SP_DATA/truth_match/<sample>). Needs the output of exclusive_signal_characterize.py.
For each signal event with a signal-matched candidate the reco proton rows (type 2212, KE > 35 MeV) and the truth primary protons of the
signal interaction are classified. Matching can be ambiguous, so the flags are NOT mutually exclusive and no unique cause is forced.
Caveat: T_truth_track holds only Geant4 tracks with charge in the blobs, so a primary proton that deposited no charge is absent from it.
"""
from __future__ import annotations
import argparse, os, sys, warnings
import multiprocessing as mp
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); sys.path.insert(0, str(REPO / "scripts")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd

ap = argparse.ArgumentParser(); ap.add_argument("--label", default="natural_bnb_cv"); ap.add_argument("--sample", default="bnb_cv")
ap.add_argument("--workers", type=int, default=16); ap.add_argument("--thr", type=float, default=35.0)
a = ap.parse_args()
OUT = REPO / "tables" / "exclusive_signal" / a.label
tab = pd.read_parquet(Path(os.environ["SP_DATA"]) / "exclusive_signal" / a.label / "signal_event_table_any.parquet")


def main():
    from sbnd_single_photon import samples as S
    import truth_match_scan as TM
    s = S.load_samples()[a.sample]; urls = S.manifest_urls(s)
    tmdir = Path(os.environ["SP_DATA"]) / "truth_match" / a.sample; tmdir.mkdir(parents=True, exist_ok=True)
    files = sorted(tab.file_index.unique())
    jobs = [(int(i), urls[int(i)], str(tmdir)) for i in files]
    bad = []
    with mp.get_context("spawn").Pool(a.workers) as p:
        for i, st in p.imap_unordered(TM.work, jobs, chunksize=1):
            if st.startswith("ERR") or st == "no truth":
                bad.append((i, st))
    print(f"truth-match npz ready for {len(files)} files, {len(bad)} bad: {bad[:5]}")
    thr = a.thr
    ev_rows, reco_lists = [], {}
    for fi, g in tab.groupby("file_index"):
        npz = tmdir / f"{int(fi)}.npz"
        if not npz.exists():
            continue
        z = np.load(npz)
        rows = pd.DataFrame({k[4:]: z[k] for k in z.files if k.startswith("row_")})
        cand = pd.DataFrame({k[5:]: z[k] for k in z.files if k.startswith("cand_")})
        tp = pd.DataFrame({k[3:]: z[k] for k in z.files if k.startswith("tp_")})
        for _, r in g.iterrows():
            rec = dict(file_index=int(fi), ev=int(r.ev), truth_cat=int(r.truth_cat), delta_pdg=int(r.delta_pdg),
                       match_reco_cat=int(r.match_reco_cat), has_matched=bool(r.A_matched), selected=bool(r.A_final))
            if not r.A_matched:
                ev_rows.append(rec); continue
            nu = int(r.match_cand_nu)
            cd = cand[(cand.ev == r.ev) & (cand.nu == nu)]
            if len(cd) == 0 or not np.isfinite(cd.dom_nu.iloc[0]):
                rec["no_truth_rows"] = True; ev_rows.append(rec); continue
            s_nu = int(cd.dom_nu.iloc[0])
            R = rows[(rows.ev == r.ev) & (rows.nu == nu)]
            Rp = R[(R.typ == 2212) & (R.ke > thr)]
            mt = Rp.mtrack.notna() & (Rp.mnu == s_nu)
            prim = (Rp.mpdg == 2212) & (Rp.mmother == 0)
            rec.update(
                n_reco_rows=len(R), n_reco_p35=len(Rp),
                rp_primary_signal=int((mt & prim).sum()), rp_secondary_signal=int((mt & (Rp.mpdg == 2212) & (Rp.mmother != 0)).sum()),
                rp_signal_other_pdg=int((mt & (Rp.mpdg != 2212)).sum()), rp_other_neutrino=int((Rp.mtrack.notna() & (Rp.mnu != s_nu) & (Rp.mnu >= 0)).sum()),
                rp_unmatched=int((Rp.mtrack.isna() | (Rp.mnu < 0)).sum()), rp_leftover_shower_inc3=int((Rp.inc == 3).sum()),
                rp_truth_ke_below_thr=int((mt & prim & (Rp.mke < thr)).sum()))
            T = tp[(tp.ev == r.ev) & (tp.mnu == s_nu) & (tp.mmother == 0) & (tp.tke > thr)]
            fate = dict(tp_found_proton=0, tp_row_proton_below_thr=0, tp_row_other_pid=0, tp_no_row=0)
            for tr in T.mtrack:
                rr = R[R.mtrack == tr]
                if ((rr.typ == 2212) & (rr.ke > thr)).any(): fate["tp_found_proton"] += 1
                elif (rr.typ == 2212).any(): fate["tp_row_proton_below_thr"] += 1
                elif len(rr): fate["tp_row_other_pid"] += 1
                else: fate["tp_no_row"] += 1
            rec.update(fate); rec["n_truth_primary_p35_wc_tracks"] = len(T)
            lowT = tp[(tp.ev == r.ev) & (tp.mnu == s_nu) & (tp.mmother == 0) & (tp.tke <= thr) & (tp.tke > 0)]
            rec["n_truth_primary_below_thr_wc_tracks"] = len(lowT)
            ev_rows.append(rec)
            reco_lists[(int(fi), int(r.ev))] = ";".join(f"{k:.0f}" for k in sorted(Rp.ke.values, reverse=True))
    E = pd.DataFrame(ev_rows)
    E["reco_proton_ke_list"] = [reco_lists.get((a_, b_), "") for a_, b_ in zip(E.file_index, E.ev)]
    E["wc_truth_count_matches_caf"] = E.get("n_truth_primary_p35_wc_tracks", np.nan) == E.truth_cat.clip(upper=2)
    E.to_csv(OUT / "mechanisms_events.csv", index=False)
    # per migration cell: number of events with each (non-exclusive) flag
    flags = ["rp_primary_signal", "rp_secondary_signal", "rp_signal_other_pdg", "rp_other_neutrino", "rp_unmatched", "rp_leftover_shower_inc3", "rp_truth_ke_below_thr",
             "tp_found_proton", "tp_row_proton_below_thr", "tp_row_other_pid", "tp_no_row"]
    cells = []
    lab = {0: "0p", 1: "1p", 2: ">=2p", -1: "no candidate"}
    for (t_, r_), g in E.groupby(["truth_cat", "match_reco_cat"]):
        row = dict(truth=lab[t_], reco=lab[r_], events=len(g))
        if r_ == -1:
            row["note"] = "signal candidate absent (no candidate or none truth-matched)"
        else:
            for f in flags:
                row[f + "_events"] = int((g[f] > 0).sum()); row[f + "_rows"] = int(g[f].sum())
        cells.append(row)
    pd.DataFrame(cells).to_csv(OUT / "mechanisms_by_migration_cell.csv", index=False)
    print(pd.DataFrame(cells).T.to_string())
    # attach the reco proton KE list to the selected-event table
    sel = pd.read_csv(OUT / "selected_signal_events_any.csv")
    if "reco_proton_ke_list_mev" not in sel:
        sel = sel.merge(E[["file_index", "ev", "reco_proton_ke_list"]].rename(columns={"reco_proton_ke_list": "reco_proton_ke_list_mev"}), on=["file_index", "ev"], how="left")
        sel.to_csv(OUT / "selected_signal_events_any.csv", index=False)


if __name__ == "__main__":
    main()
