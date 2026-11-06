"""Load the per-file candidate tables written by scripts/baseline_scan.py and evaluate the baseline chain on them.

Two bookkeeping levels are kept apart everywhere:
  * CANDIDATE level: one row per Wire-Cell neutrino candidate (0, 1 or 2+ per event);
  * EVENT level: one row per CAF event. An event passes under a candidate POLICY:
        ``any``   - at least one candidate passes the full chain;
        ``first`` - the candidate with nu_index == 0 (WCT: the longest selected activity) passes;
    ``dedup_any`` - candidates are first reduced to the lowest-nu_index (= longest) candidate of each flash group,
                    mirroring WCT's own ``nu_dedup_flash_group`` rule (which is OFF by default), then ``any``.
    Both policies are PROVISIONAL (docs/analysis/CANDIDATE_POLICY_AUDIT.md).
Exposure is the sum of per-file ``TotalPOT`` over the files actually loaded (never de-duplicated by run/subrun).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from .selection import OPS

MODELS = ("numu", "other", "ncpi0", "nue")
PER_FILE_SCALARS = ("pot", "gen", "n_events")


def column_for_branch(branch: str) -> str:
    """configs/baseline_selection.yaml branch -> candidate-table column."""
    if branch.startswith("derived.single_photon_"):
        return "c_score_" + branch[len("derived.single_photon_"):-len("_score")]
    return "c_" + branch.split(".")[-1]


def load_scan(directory, sample: str | None = None) -> dict:
    """Concatenate every ``*.npz`` of ``directory`` (or ``directory/sample``) in numeric file order."""
    d = Path(directory) / sample if sample else Path(directory)
    files = sorted((p for p in d.glob("*.npz") if not p.name.endswith(".tmp.npz")), key=lambda p: int(p.stem))   # skip half-written files
    if not files:
        raise FileNotFoundError(f"no scan files in {d}")
    parts, per_file = [], {"file_index": [], "pot": [], "gen": [], "n_events": [], "md5": [], "dlw": []}
    for p in files:
        z = np.load(p, allow_pickle=False)
        parts.append({k: z[k] for k in z.files if k not in ("md5", "dlw")})
        per_file["file_index"].append(int(p.stem))
        for k in PER_FILE_SCALARS:
            per_file[k].append(float(z[k]))
        per_file["md5"].append(str(z["md5"])); per_file["dlw"].append(str(z["dlw"]))
    tab: dict = {}
    keys = set().union(*[set(x) for x in parts]) - set(PER_FILE_SCALARS)
    offs = np.cumsum([0] + [len(x["ev_valid"]) for x in parts])
    for k in sorted(keys):
        if k.startswith("featnf_"):
            tab[k] = np.sum([x[k] for x in parts if k in x], axis=0)
        elif all(k in x for x in parts):
            tab[k] = np.concatenate([x[k] for x in parts])
        else:                                                      # column absent in some files: refuse silently-wrong data
            raise KeyError(f"column {k!r} missing from {sum(k not in x for x in parts)} of {len(parts)} files")
    tab["c_gev"] = np.concatenate([x["c_ev"].astype(np.int64) + o for x, o in zip(parts, offs[:-1])])
    tab["ev_file"] = np.repeat(np.arange(len(parts)), np.diff(offs))
    tab["file"] = {k: np.asarray(v) for k, v in per_file.items()}
    tab["n_files"] = len(parts)
    tab["pot_total"] = float(np.sum(per_file["pot"], dtype=np.float64))
    tab["gen_total"] = float(np.sum(per_file["gen"], dtype=np.float64))
    return tab


def candidate_chain(tab: dict, cfg: dict) -> dict:
    """Cumulative per-candidate flags {stage: bool[ncand]}. Candidates of wc.valid != 1 events never pass.
    A NaN (non-evaluable) value fails its cut by construction."""
    valid_c = tab["ev_valid"][tab["c_gev"]]
    out = {"candidate_in_valid_event": valid_c}
    cur = valid_c
    for c in cfg["cuts"]:
        x = tab[column_for_branch(c["branch"])]
        cur = cur & OPS[c["op"]](x, c["threshold"])
        out[c["name"]] = cur
    return out


def bdt_evaluable(tab: dict) -> np.ndarray:
    ok = tab["c_shw_sp_filled"] != 0
    for m in MODELS:
        ok = ok & np.isfinite(tab[f"c_score_{m}"])
    return ok


def dedup_keep(tab: dict) -> np.ndarray:
    """Bool per candidate: lowest nu_index of its (event, flash_group). Needs ``c_flash_group``."""
    key = tab["c_gev"].astype(np.int64) * 4_000_000_000 + (tab["c_flash_group"].astype(np.int64) + 2_000_000_000)
    order = np.lexsort((tab["c_nu_index"], key))
    first = np.ones(len(order), bool)
    first[1:] = key[order][1:] != key[order][:-1]
    keep = np.zeros(len(order), bool); keep[order[first]] = True
    return keep


def policy_mask(tab: dict, policy: str) -> np.ndarray:
    if policy == "any":
        return np.ones(len(tab["c_gev"]), bool)
    if policy == "first":
        return tab["c_nu_index"] == 0
    if policy == "dedup_any":
        return dedup_keep(tab)
    raise ValueError(f"unknown candidate policy {policy!r}")


def event_pass(tab: dict, flags: np.ndarray, policy: str) -> np.ndarray:
    """Event-level bool [n_events] for candidate-level ``flags``."""
    n = len(tab["ev_valid"])
    flags = flags & policy_mask(tab, policy)
    out = np.zeros(n, dtype=bool)
    out[tab["c_gev"][flags]] = True
    return out


def chosen_candidate(tab: dict, flags: np.ndarray, policy: str) -> np.ndarray:
    """Row index of the selected candidate for each passing event (-1 if none). ``any`` -> lowest nu_index passing."""
    n = len(tab["ev_valid"]); idx = np.full(n, -1, dtype=np.int64)
    f = flags & policy_mask(tab, policy)
    rows = np.flatnonzero(f)
    order = rows[np.argsort(-tab["c_nu_index"][rows], kind="stable")]      # later writes (lower nu_index) win
    idx[tab["c_gev"][order]] = order
    return idx


def rate(n: float, pot: float, per: float = 1e20) -> tuple[float, float]:
    """(N/POT*per, sqrt(N)/POT*per): count per ``per`` generated POT of the filtered sample, Poisson error on the raw count only (no weights).
    For the official filtered Gen2 CV this is the POT-normalised neutrino-induced rate (cosmic-only backgrounds come from beam-off); see docs/analysis/POT_EXPOSURE_AUDIT.md."""
    if not pot:
        return float("nan"), float("nan")
    return n / pot * per, np.sqrt(max(n, 0.0)) / pot * per


def proton_code(n_p: np.ndarray) -> np.ndarray:
    return np.clip(n_p, 0, 2).astype(np.int8)


def cutflow_rows(tab: dict, cfg: dict) -> list[dict]:
    """Stage table (candidate- and event-level counts side by side) with 'selected events per 1e20 generated POT' columns."""
    pot = tab["pot_total"]; nev = len(tab["ev_valid"]); valid = tab["ev_valid"]
    chain = candidate_chain(tab, cfg)
    rows = []

    def add(stage, n_cand, n_any, n_first, note=""):
        r = {"stage": stage, "n_candidates": n_cand, "n_events_any": n_any, "n_events_first": n_first, "note": note}
        for p, n in (("any", n_any), ("first", n_first)):
            if n is not None:
                r[f"stored_per_1e20_genPOT_{p}"], r[f"stored_err_per_1e20_genPOT_{p}"] = rate(n, pot)
        rows.append(r)

    add("all_events", int(len(tab["c_gev"])), nev, nev, "all CAF events; candidates counted over all events")
    add("wc_valid_fail", int((~valid[tab["c_gev"]]).sum()), int((~valid).sum()), int((~valid).sum()), "events with wc.valid != 1 (excluded)")
    add("wc_valid", int(chain["candidate_in_valid_event"].sum()), int(valid.sum()), int(valid.sum()), "usable reconstruction")
    nc = np.bincount(tab["c_gev"][chain["candidate_in_valid_event"]], minlength=nev)
    first_exists = np.zeros(nev, bool); first_exists[tab["c_gev"][chain["candidate_in_valid_event"] & (tab["c_nu_index"] == 0)]] = True
    add("candidate_exists", int(chain["candidate_in_valid_event"].sum()), int((nc > 0).sum()), int(first_exists.sum()),
        "valid events with >=1 candidate")
    ev = chain["candidate_in_valid_event"] & bdt_evaluable(tab)
    add("(info) bdt_evaluable_candidates", int(ev.sum()), int(event_pass(tab, ev, "any").sum()), int(event_pass(tab, ev, "first").sum()),
        "shw_sp_filled != 0 and all four scores finite; NOT a cut")
    for c in cfg["cuts"]:
        f = chain[c["name"]]
        add("cum:" + c["name"], int(f.sum()), int(event_pass(tab, f, "any").sum()), int(event_pass(tab, f, "first").sum()))
    return rows


def completeness(tab: dict, expected_files: int | None, expected_events: int | None = None) -> dict:
    """Compare what was loaded with the manifest/registry. A scan with missing files must never be reported as the full sample."""
    out = dict(files_loaded=int(tab["n_files"]), files_expected=expected_files,
               events_loaded=int(len(tab["ev_valid"])), events_expected=expected_events)
    out["complete"] = (expected_files is None or out["files_loaded"] == expected_files) and \
                      (expected_events is None or out["events_loaded"] == expected_events)
    return out
