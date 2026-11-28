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
Verdicts (VERDICTS): CONFIRMED_IDENTICAL_FILE; CONFIRMED_SHARED_GENERATOR_ANCESTRY (same production job id); CONFIRMED_GENERATOR_IDENTICAL_EVENTS (only from delivered evidence, e.g. Aurora's duplicate groups);
SHARED_SEED_REQUIRES_VERIFICATION; NUMERICAL_COLLISION_NO_ANCESTRY (same run/subrun/event numbers, no shared ancestry: a coincidence of distinct productions); ESTABLISHED_DISJOINT (data files with no file in common,
or a documented distinct seed namespace); UNDETERMINED_INDEPENDENCE. Different job ids alone never establish independence.
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


VERDICTS = ["CONFIRMED_IDENTICAL_FILE", "CONFIRMED_SHARED_GENERATOR_ANCESTRY", "CONFIRMED_GENERATOR_IDENTICAL_EVENTS", "SHARED_SEED_REQUIRES_VERIFICATION", "NUMERICAL_COLLISION_NO_ANCESTRY", "ESTABLISHED_DISJOINT", "UNDETERMINED_INDEPENDENCE"]
# Official sample -> documented generator seed namespace. EMPTY on purpose: neither SAM nor the production files record the generator seeds / NuRandomService offsets of the official productions, so
# "different job ids and different run numbers" can never by itself establish independence. A sample is added here only with a written reference (production fcl / logs).
OFFICIAL_SEED_NAMESPACE_DOCUMENTED: dict = {}


def classify(official: pd.DataFrame, member: pd.DataFrame, official_seed_documented: dict | None = None) -> pd.DataFrame:
    """official: columns sample, file_name, gen_id, [run, subrun, event]; member: the delivered manifest (see module docstring). One row per (official sample, member set, member sample).
    Different production job ids or different run numbers are NOT sufficient: Aurora found generator-identical events under repeated GEN seeds with different subruns, so independence is
    ESTABLISHED_DISJOINT only for data files (no generator) or when the official seed namespace is documented and distinct from the member's."""
    documented = OFFICIAL_SEED_NAMESPACE_DOCUMENTED if official_seed_documented is None else official_seed_documented; out = []
    for (sset, msample), m in member.groupby(["set", "sample"]):
        mn = set(m["file_name"].dropna()) if "file_name" in m else set(); mg = set(m["gen_id"].dropna()) if "gen_id" in m else set()
        if "file_name" in m: mg |= {gen_id(n) for n in mn if gen_id(n)}
        has_ev = all(c in m for c in ("run", "subrun", "event")); mev = set(map(tuple, m[["run", "subrun", "event"]].dropna().astype(int).values)) if has_ev else set()
        is_data = bool(m["is_data"].astype(bool).all()) if "is_data" in m else False
        mseed = set(m["seed"].dropna().astype(np.int64)) if "seed" in m else set()
        for osamp, o in official.groupby("sample"):
            of = o.drop_duplicates("file_name"); f_overlap = int(of.file_name.isin(mn).sum()); g_overlap = int((of.gen_id.isin(mg) & ~of.file_name.isin(mn)).sum())
            coll = len(set(map(tuple, o[["run", "subrun", "event"]].dropna().astype(int).values)) & mev) if has_ev and {"run", "subrun", "event"} <= set(o.columns) else 0
            oseed = set(o["seed"].dropna().astype(np.int64)) if "seed" in o else set(); s_overlap = len(oseed & mseed)
            decidable = bool(mn or mg); reason = ""
            if f_overlap: v = "CONFIRMED_IDENTICAL_FILE"
            elif g_overlap: v = "CONFIRMED_SHARED_GENERATOR_ANCESTRY"
            elif s_overlap: v = "SHARED_SEED_REQUIRES_VERIFICATION"
            elif coll: v = "NUMERICAL_COLLISION_NO_ANCESTRY"
            elif not decidable: v, reason = "UNDETERMINED_INDEPENDENCE", "manifest has no file name / job id"
            elif is_data: v, reason = "ESTABLISHED_DISJOINT", "data files: no generator; no file in common"
            elif documented.get(osamp) == "distinct_namespace": v, reason = "ESTABLISHED_DISJOINT", "official seed namespace documented and distinct"
            else: v, reason = "UNDETERMINED_INDEPENDENCE", "no file / job-id / run-number overlap, but the generator seed namespace of the official production is not documented"
            out.append(dict(official_sample=osamp, member_set=sset, member_sample=msample, n_official_files=len(of), n_member_rows=len(m), files_same_name=f_overlap, files_same_genjob=g_overlap, run_subrun_event_coincidences=coll, shared_seeds=s_overlap, verdict=v, reason=reason))
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
    elif cmd == "aurora":
        M = Path(sys.argv[2]); Ev = pd.read_parquet(M / "membership_events.parquet", columns=["sample", "file_id", "run", "subrun", "event"]).rename(columns={"file_id": "file_name"}); Ev["set"] = "aurora_membership_events"; Ev["is_data"] = Ev["sample"].str.contains("beamoff")
        off = official_table(); names = {s_: [u.rstrip("/").split("/")[-1] for u in urls("nov16", s_)] for s_ in SAMPLES}; rows = []
        for s_ in ("bnb_cv", "nuecc", "official_gen2_ncdelta", "beam_off"):
            e = pd.read_parquet(SPD / "wcl1116_nov16" / "analysis_tables_new" / s_ / "events.parquet", columns=["file_index", "run", "subrun", "evt"]).rename(columns={"evt": "event"})
            e["file_name"] = e.file_index.map(dict(enumerate(names[s_]))); e["gen_id"] = e.file_name.map(gen_id); e["sample"] = s_; rows.append(e.drop(columns="file_index"))
        O = pd.concat(rows, ignore_index=True)
        PAIRS = {"official_gen2_ncdelta": "wcl1116-aurora-ncdr", "bnb_cv": "wcl1116-aurora-bnb", "nuecc": "wcl1116-aurora-nuecc", "beam_off": "wcl1116-fg-beamoff-train"}
        res = pd.concat([classify(O[O["sample"] == o_], Ev[Ev["sample"] == a_]) for o_, a_ in PAIRS.items()], ignore_index=True)
        res.to_csv(OUT / "official_vs_aurora_membership.csv", index=False); print(res.to_string())
    else:
        mem = pd.concat([pd.read_parquet(p) if p.endswith(".parquet") else pd.read_csv(p) for p in sys.argv[2:]], ignore_index=True); r = classify(official_table(), mem); r.to_csv(OUT / "membership_audit_result.csv", index=False); print(r.to_string())


if __name__ == "__main__":
    main()
