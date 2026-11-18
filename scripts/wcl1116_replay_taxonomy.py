#!/usr/bin/env python
"""Photon-reconstruction taxonomy of the signal photon (Round-1 code, unchanged) on the Nov16 dedicated NC-Delta sample versus the fg1-era reconstruction.

    source env/setup_eaf.sh
    python scripts/wcl1116_replay_taxonomy.py scan --workers 24     # Round-1 shower_vertex_scan.work on the NEW files (events: TPC-box signal with >= 1 candidate in NEW)
    python scripts/wcl1116_replay_taxonomy.py report                # classify with shower_audit.classify_failure (unchanged hierarchy and thresholds) + regression of OLD

OLD tables: the stored Round-1 scan ($SP_DATA/shower_vertex_audit/official_ncdelta/raw; reconstruction-only, unaffected by the scorer correction). The classes are not redefined.
The taxonomy is a reconstruction-stage classification of the signal photon; it is evaluated on events with at least one candidate (the Round-1 population of 11,331).
"""
from wcl1116_replay_common import *
import argparse, importlib
import multiprocessing as mp
from sbnd_single_photon import shower_audit as SA, shower_tables as ST

K = ["file_index", "ev"]
RAWN = DER / "taxonomy_new_raw"; RAWO = SPD / "shower_vertex_audit" / "official_ncdelta" / "raw"
TRUTH_LABEL = {0: "truth 0p", 1: "truth 1p", 2: "truth >=2p"}


def scan(a):
    sv = importlib.import_module("shower_vertex_scan")
    ta = pd.read_parquet(DER / "signal_event_table_new_any.parquet")
    ev = ta[ta.A_candidate.astype(bool) & ta.arrived.astype(bool)].dropna(subset=["file_index"])
    urls = [l.rstrip("\n").split("\t")[2] for l in open_manifest()]
    jobs = [(int(fi), urls[int(fi)], [(int(r.ev), float(r.x), float(r.y), float(r.z), float(r.photon_mev)) for r in g.itertuples()]) for fi, g in ev.groupby("file_index")]
    print("events", sum(len(j[2]) for j in jobs), "files", len(jobs), flush=True); RAWN.mkdir(parents=True, exist_ok=True)
    with mp.get_context("spawn").Pool(min(a.workers, 24)) as p:
        res = list(p.imap_unordered(sv.work, jobs, chunksize=1))
    bad = [r for r in res if r[2]]; print("read errors", len(bad), [(r[0], r[2][:80]) for r in bad[:5]], flush=True)
    for k in ("cand", "kine", "pf", "seg", "shlist", "pho_ov", "ov_all", "truth"):
        d = pd.concat([r[1][k] for r in res if r[1] is not None and len(r[1][k])], ignore_index=True); d.to_parquet(RAWN / f"{k}.parquet", index=False); print(k, d.shape, flush=True)


def open_manifest():
    import gzip
    return list(gzip.open(REPO / "manifests" / "wcl1116" / "official_gen2_ncdelta.tsv.gz", "rt"))[1:]


def classify(raw, ta):
    """Same hierarchy as shower_vertex_audit.main(): exclusive outcome of the signal photon for the candidate-stage events."""
    assoc = ST.photon_association(raw)
    cand = raw["cand"].copy(); cand["nu_index"] = cand.nu_index.astype(int)
    E = ta[ta.A_candidate.astype(bool)].copy(); E["pass_n20"] = E.A_n20mev.astype(bool)
    E = E.merge(assoc, on=K, how="inner", validate="one_to_one")
    mx = cand.groupby(K).shw_sp_n_20mev_showers.max().rename("max_n20").reset_index(); E = E.merge(mx, on=K, how="left")
    assert ((E.max_n20 > 0) == E.pass_n20).all(), "A_n20mev disagrees with the per-candidate tagger field"
    E["dom_is_sig"] = [None if not bool(m) else (bool(int(d) == int(mc)) if pd.notna(d) else None) for m, d, mc in zip(E.A_matched, E.dom_nu, E.match_cand_nu)]
    dn = cand[K + ["nu_index", "shw_sp_n_20mev_showers"]].rename(columns={"nu_index": "dom_nu", "shw_sp_n_20mev_showers": "dom_cand_n20"})
    E = E.merge(dn, on=K + ["dom_nu"], how="left")
    ftype = lambda r: int(r.kine_particle_type) if pd.notna(r.kine_particle_type) else 0
    out = []
    for r in E.itertuples():
        is_sh = bool(r.kine_particle_is_shower == 1); pdg = ftype(r); en = float(r.kine_energy_particle) if pd.notna(r.kine_energy_particle) else 0.0
        if r.pass_n20:
            via = (r.has_kine_row and is_sh and pdg == 11 and en > 20 and pd.notna(r.dom_cand_n20) and r.dom_cand_n20 > 0 and r.dominant_fraction >= SA.DOMINANT_FRAC_MIN)
            out.append("pass_photon_shower_in_passing_candidate" if via else "pass_not_via_signal_photon_shower")
        else:
            out.append(SA.classify_failure(r.q_total, r.q_in_cands, r.dominant_fraction, r.dom_is_sig, bool(r.has_kine_row), is_sh, pdg, en))
    E["outcome"] = out
    return E


def table(E, label):
    outcomes = ["pass_photon_shower_in_passing_candidate", "pass_not_via_signal_photon_shower"] + SA.FAIL_CLASSES; rows = []
    for g, m in [("all", np.ones(len(E), bool))] + [(TRUTH_LABEL[k], (E.truth_cat == k).to_numpy()) for k in (0, 1, 2)]:
        n = int(m.sum())
        for o in outcomes:
            k = int((m & (E.outcome == o).to_numpy()).sum()); v, lo, hi = binom(k, n)
            rows.append(dict(production=label, group=g, outcome=o, n=k, n_candidate_stage=n, pct=100 * v, lo68=100 * lo, hi68=100 * hi))
    return rows


def report(a):
    to, tn = pd.read_parquet(DER / "signal_event_table_old_any.parquet"), pd.read_parquet(DER / "signal_event_table_new_any.parquet")
    kk = ("cand", "kine", "pf", "seg", "shlist", "pho_ov", "ov_all", "truth")
    Eo = classify({k: pd.read_parquet(RAWO / f"{k}.parquet") for k in kk}, to)
    # regression: the Round-1 taxonomy table must be reproduced for OLD
    ref = pd.read_csv(REPO / "tables" / "shower_vertex_audit" / "taxonomy.csv"); ref = ref[ref.group == "all"].set_index("outcome").n
    got = Eo.outcome.value_counts()
    assert len(Eo) == 11331 and all(int(got.get(o, 0)) == int(ref[o]) for o in ref.index), "OLD taxonomy does not reproduce the Round-1 table"
    En = classify({k: pd.read_parquet(RAWN / f"{k}.parquet") for k in kk}, tn)
    T = pd.DataFrame(table(Eo, "old_fg1") + table(En, "nov16")); T.to_csv(OUT / "signal_photon_taxonomy_old_vs_nov16.csv", index=False)
    # matched event migration of the outcome
    j = Eo[RSE + ["outcome", "truth_cat"]].merge(En[RSE + ["outcome"]], on=RSE, how="inner", suffixes=("_old", "_new"))
    mig = j.groupby(["outcome_old", "outcome_new"]).size().rename("N").reset_index(); mig.to_csv(OUT / "signal_photon_taxonomy_migration.csv", index=False)
    only = pd.DataFrame(dict(only_old=[len(set(map(tuple, Eo[RSE].values)) - set(map(tuple, En[RSE].values)))], only_new=[len(set(map(tuple, En[RSE].values)) - set(map(tuple, Eo[RSE].values)))], matched=[len(j)]))
    only.to_csv(OUT / "signal_photon_taxonomy_population.csv", index=False)
    Eo.to_parquet(DER / "taxonomy_old_events.parquet", index=False); En.to_parquet(DER / "taxonomy_new_events.parquet", index=False)
    pv = T[T.group == "all"].pivot_table(index="outcome", columns="production", values=["n", "pct"]); print(pv.round(2).to_string()); print(only.to_string(index=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("stage", choices=["scan", "report"]); ap.add_argument("--workers", type=int, default=24); a = ap.parse_args()
    (scan if a.stage == "scan" else report)(a)
