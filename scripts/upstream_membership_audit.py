#!/usr/bin/env python
"""V7 membership audit, BOOKKEEPING ONLY: file names, production-job (generator) ids, SAM parents, run/subrun/event identifiers and run parity. Reads committed manifests, the saved SAM metadata
(`$SP_DATA/sam/*meta.csv.gz`) and, for the beam-off ledger, file names. NO classifier score, kinematic distribution, selection output, truth content or blinded data is read.

  python scripts/upstream_membership_audit.py ledger            # beam-off membership ledger + official id-space summary (always possible)
  python scripts/upstream_membership_audit.py audit MANIFEST... # compare official MC membership with delivered training/dev membership manifests (Aurora, Xuyang, Snehadri)

Membership manifest (CSV/parquet), one row per file (or per event if known):
  set        : upstream_fit | upstream_dev | sp_fit | sp_nested_val | sp_outer_holdout | dlvertex_train | ...   (free text, required)
  sample     : e.g. aurora_bnb_cv, aurora_ncdr, aurora_nuecc, aurora_beam_off  (required)
  file_name  : the CAF / reco file name WITHOUT directory (preferred)            gen_id : production job id as in `filter-gen-<4>-<4>-<4>-<4>` or `Gen2_2026-<4>-<4>-<4>-<4>` (if file_name absent)
  run, subrun, event : optional event-level identifiers                          ancestry : free text, e.g. SAM parent chain / production name (needed to separate collisions from overlaps)
Classes: TRUE_OVERLAP_FILE (same file name), TRUE_OVERLAP_GENJOB (same production job id: same generated events), ID_COLLISION (same run/subrun/event numbers, different job id and ancestry:
a numerical coincidence between distinct productions, NOT an overlap), DISJOINT (all identifiers present and none match), UNDETERMINED (the manifest lacks the identifier needed to decide).
"""
import re, sys
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from sbnd_single_photon import samples as S

REPO = Path(__file__).resolve().parents[1]; OUT = REPO / "tables" / "upstream_release"; SPD = Path("/exp/sbnd/data/users/abhat/single_photon_ncdelta")
GENID = re.compile(r"((?:Gen2_2026-)?[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}(?:-[0-9a-f]{4})?)")
SAMPLES = ["bnb_cv", "nuecc", "official_gen2_ncdelta", "beam_off", "beam_on_open", "run3bnb"]


def urls(prod, sample):
    return S.manifest_urls(S.load_samples()[sample]) if prod == "old_fg1" else [r["url"] for r in S.read_manifest(REPO / "manifests" / "wcl1116" / f"{sample}.tsv.gz")]


def gen_id(name: str):
    m = GENID.search(name); return m.group(1) if m else None


def beam_off_ledger(prod="nov16") -> pd.DataFrame:
    u = urls(prod, "beam_off"); rows = []
    for i, url in enumerate(u):
        name = url.rstrip("/").split("/")[-1]; m = re.search(r"run(\d+)_(\d+)_strm", name); run = int(m.group(1)) if m else -1
        rows.append(dict(file_index=i, name=name, run=run, subrun_token=int(m.group(2)) if m else -1, parity="odd" if run % 2 == 1 else "even"))
    L = pd.DataFrame(rows)
    L["policy_class"] = np.where(L.run < 0, "UNPARSEABLE_EXCLUDE", np.where(L.parity == "odd", "UPSTREAM_TRAINING_HALF_EXCLUDE", "EVALUATION_ELIGIBLE_EVEN_RUN"))
    staged = Path("/exp/sbnd/data/users/abhat/wcl1116_beamoff_train_stage/files.txt")      # the 558 files staged for SP `other` training (EAF copy of the Aurora staging list; bookkeeping names only)
    if staged.exists():
        st = {l.strip().split("/")[-1] for l in staged.read_text().splitlines() if l.strip()}; L["in_sp_other_staged_558"] = L.name.isin(st)    # NEVER used to relax the odd-run exclusion
    else: L["in_sp_other_staged_558"] = pd.NA
    L["in_upstream_training_list"] = pd.NA         # to be filled from Xuyang's list (558 files); the whole odd-run half is excluded regardless
    return L


def id_space_summary() -> pd.DataFrame:
    rows = []
    for prod in ("old_fg1", "nov16"):
        for s in SAMPLES:
            if prod == "old_fg1" and s == "run3bnb": continue
            u = urls(prod, s); names = [x.rstrip("/").split("/")[-1] for x in u]; ids = [gen_id(n) for n in names]
            rows.append(dict(production=prod, sample=s, n_files=len(u), n_with_gen_id=sum(i is not None for i in ids), n_unique_gen_id=len(set(i for i in ids if i)), n_unique_file_names=len(set(names))))
    A = pd.DataFrame(rows)
    ev = []
    for prod, d in (("nov16", SPD / "wcl1116_nov16" / "analysis_tables_new"), ("old_fg1", SPD / "wcl1116_nov16" / "analysis_tables_old")):
        for s in SAMPLES:
            p = d / s / "events.parquet"
            if p.exists():
                e = pd.read_parquet(p, columns=["file_index", "run", "subrun", "evt"]); ev.append(dict(production=prod, sample=s, n_events=len(e), run_min=int(e.run.min()), run_max=int(e.run.max()), n_distinct_runs=int(e.run.nunique()),
                                                                                                      subrun_min=int(e.subrun.min()), subrun_max=int(e.subrun.max()), n_run_subrun_evt_triples_not_unique_across_files=int(e.duplicated(["run", "subrun", "evt"]).sum())))
    return A.merge(pd.DataFrame(ev), on=["production", "sample"], how="left")


def classify(official: pd.DataFrame, member: pd.DataFrame) -> pd.DataFrame:
    """official: columns sample, file_name, gen_id, [run, subrun, event]; member: the delivered manifest. One row per (official sample, member set) with counts of each class."""
    out = []
    for (sset, msample), m in member.groupby(["set", "sample"]):
        mn = set(m["file_name"].dropna()) if "file_name" in m else set(); mg = set(m["gen_id"].dropna()) if "gen_id" in m else set()
        if "file_name" in m: mg |= {gen_id(n) for n in mn if gen_id(n)}
        has_ev = all(c in m for c in ("run", "subrun", "event")); mev = set(map(tuple, m[["run", "subrun", "event"]].dropna().astype(int).values)) if has_ev else set()
        for osamp, o in official.groupby("sample"):
            f_overlap = int(o.file_name.isin(mn).sum()); g_overlap = int((o.gen_id.isin(mg) & ~o.file_name.isin(mn)).sum())
            coll = 0
            if has_ev and {"run", "subrun", "event"} <= set(o.columns):
                oe = set(map(tuple, o[["run", "subrun", "event"]].dropna().astype(int).values)); coll = len(oe & mev) if not (f_overlap or g_overlap) else 0
            decidable = bool(mn or mg)
            cls = "TRUE_OVERLAP_FILE" if f_overlap else ("TRUE_OVERLAP_GENJOB" if g_overlap else ("ID_COLLISION" if coll else ("DISJOINT" if decidable else "UNDETERMINED")))
            out.append(dict(official_sample=osamp, member_set=sset, member_sample=msample, n_official_files=len(o), n_member_rows=len(m), files_same_name=f_overlap, files_same_genjob=g_overlap, run_subrun_event_coincidences=coll, verdict=cls))
    return pd.DataFrame(out)


def official_table(prod="nov16") -> pd.DataFrame:
    rows = []
    for s in SAMPLES:
        for n in (u.rstrip("/").split("/")[-1] for u in urls(prod, s)): rows.append(dict(sample=s, file_name=n, gen_id=gen_id(n)))
    return pd.DataFrame(rows)


def main():
    cmd = sys.argv[1]
    if cmd == "ledger":
        L = beam_off_ledger(); L.to_csv(OUT / "beam_off_membership_ledger.csv", index=False); g = id_space_summary(); g.to_csv(OUT / "official_id_space_summary.csv", index=False)
        print(L.groupby(["parity", "policy_class"]).size()); print(g.to_string())
        old = beam_off_ledger("old_fg1"); print("old and Nov16 beam-off name sets identical:", set(old.name) == set(L.name))
    else:
        mem = pd.concat([pd.read_parquet(p) if p.endswith(".parquet") else pd.read_csv(p) for p in sys.argv[2:]], ignore_index=True); r = classify(official_table(), mem); r.to_csv(OUT / "membership_audit_result.csv", index=False); print(r.to_string())


if __name__ == "__main__":
    main()
