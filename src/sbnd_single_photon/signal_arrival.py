"""Ingestion of the official NC Delta Wire-Cell merged CAFs: file inspection, event-key reconciliation, provenance gate (read-only).

Nothing here guesses a path; the discovery script (scripts/register_official_ncdelta_wc.py) feeds it a manifest/directory/SAM definition/file list.
Nothing is silently discarded: every expected event ends in exactly one of {represented (wc.valid 1), represented (wc.valid 0), missing} and every
incoming event in exactly one of {expected, duplicate of an expected one, unexpected}.
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

RSE = ["run", "subrun", "evt"]
REQUIRED_TREES = ("T_match", "T_overlap", "T_truth_nu", "T_truth_pf", "T_truth_track")
REPO_ROOT = Path(__file__).resolve().parents[2]
GATE_YAML = REPO_ROOT / "configs" / "official_signal_provenance_gate.yaml"


def normalize_unit_name(name: str) -> str:
    """File name (any of: reco1 unit, flatCAF, merged CAF ``*.wc.flat.caf.root``) -> the common generation-unit token."""
    n = Path(str(name)).name
    for suf in (".wc.flat.caf.root", ".flat.caf.root", ".caf.root", ".root"):
        if n.endswith(suf):
            n = n[: -len(suf)]
            break
    return re.sub(r"^reco2-", "", n)


def reconcile_event_keys(expected: pd.DataFrame, incoming: pd.DataFrame) -> dict:
    """Account every expected and every incoming event.

    ``expected``: official truth events, columns run, subrun, evt (+ optional reco1_unit). ``incoming``: events found in the merged CAFs, columns run,
    subrun, evt, wc_valid (+ optional file, unit). The key is (run, subrun, evt); the expected key must be unique (checked, never assumed).
    Returns counts and the offending rows (``missing``, ``duplicates``, ``unexpected``, ``unit_mismatch``)."""
    if expected.duplicated(RSE).any():
        raise ValueError("expected (run, subrun, evt) is not unique: extend the key with the generation unit")
    inc = incoming.copy()
    inc["_dup"] = inc.duplicated(RSE, keep=False)
    first = inc.drop_duplicates(RSE, keep="first")
    ek = expected.set_index(RSE).index; ik = first.set_index(RSE).index
    in_exp = ik.isin(ek)
    represented = first[in_exp]
    unexpected = inc[~inc.set_index(RSE).index.isin(ek)]
    missing = expected[~ek.isin(ik)]
    dups = inc[inc._dup].sort_values(RSE)
    n_valid = int((represented.wc_valid == 1).sum())
    out = dict(expected_events=int(len(expected)), incoming_rows=int(len(incoming)), represented=int(len(represented)),
               represented_wc_valid=n_valid, represented_wc_invalid=int(len(represented) - n_valid), missing=int(len(missing)),
               duplicate_keys=int(dups.drop_duplicates(RSE).shape[0]), duplicate_rows=int(len(dups)),
               unexpected_rows=int(len(unexpected)), unit_mismatch=0)
    if "unit" in incoming.columns and "reco1_unit" in expected.columns:
        m = represented.merge(expected[RSE + ["reco1_unit"]], on=RSE)
        bad = m[m.unit.map(normalize_unit_name) != m.reco1_unit.map(normalize_unit_name)]
        out["unit_mismatch"] = int(len(bad)); out["_unit_mismatch_rows"] = bad
    # accounting identities: nothing lost
    assert out["represented"] + out["missing"] == out["expected_events"]
    out["_missing_rows"], out["_duplicate_rows"], out["_unexpected_rows"] = missing, dups, unexpected
    out["complete"] = bool(out["missing"] == 0 and out["duplicate_rows"] == 0 and out["unexpected_rows"] == 0 and out["unit_mismatch"] == 0)
    return out


BASELINE_EXTRA = (["wc.run", "wc.subrun", "wc.evt", "wc.valid", "wc.T_tagger.nu_index", "wc.T_tagger.shw_sp_filled", "wc.T_tagger.flash_group",
                   "wc.T_tagger.shw_sp_energy", "wc.T_kine.kine_particle_type", "wc.T_kine.kine_energy_particle", "wc.T_kine.kine_energy_included",
                   "wc.T_kine.kine_nu_x_corr", "wc.T_kine.kine_nu_y_corr", "wc.T_kine.kine_nu_z_corr", "wc.T_kine.kine_reco_Enu"]
                  + [f"wc.T_match.{c}" for c in ("level", "side", "obj", "nu_index", "truth_nu_idx", "truth_trackid", "nmatch", "mutual", "match_obj",
                                                  "match_iou_n", "match_iou_q", "match_shared_n", "match_shared_q")]
                  + [f"wc.T_overlap.{c}" for c in ("nu_index", "in_enu", "trackid", "q")]
                  + [f"wc.T_truth_track.{c}" for c in ("trackid", "nu_idx")]
                  + [f"wc.T_truth_nu.{c}" for c in ("pdg", "ccnc", "vtx_x", "vtx_y", "vtx_z", "nu_idx", "edep")])


def required_wc_branches(cfg: dict) -> list[str]:
    """Every ``recTreeWireCell`` branch the frozen baseline and the evaluation read (cut chain + builder + truth association)."""
    from . import selection as SEL
    return list(dict.fromkeys(SEL.required_branches(cfg)["wc"] + list(BASELINE_EXTRA)))


def inspect_merged_caf(path: str, *, read_events: bool = True, required: list[str] | None = None) -> dict:
    """One merged CAF -> a plain dict of checks (read-only). Errors become fields, never exceptions: nothing is silently discarded."""
    from . import caf as C
    rec = dict(path=str(path), opened=False, error=None)
    try:
        with C.MergedCaf(path) as f:
            rec.update(opened=True, has_recTree=True, has_recTreeWireCell=True, entries=int(f.num_entries), entries_aligned=True,
                       has_wc_valid=f.has_wc(C.WC_VALID), n_wc_branches=int(f.n_wc_branches), schema_md5=f.schema_md5(),
                       dl_weights=f.trun("dl_weights"), wct_version=f.trun("wct_version"), trun_input_file=f.trun("input_file"), bdt_weights_dir=f.trun("bdt_weights_dir"),
                       has_geniegevtrec=("GenieEvtRecTree" in f._f))
            if required is not None:
                rec["missing_baseline_branches"] = [b for b in required if b not in f.wc_branches]
            for t in REQUIRED_TREES:
                rec["has_" + t] = any(k.startswith(f"wc.{t}.") for k in f.wc_branches)
            try:
                ids = f.read_ids(); rec["ids_aligned"] = True
                if read_events:
                    rec["events"] = pd.DataFrame(dict(run=np.asarray(ids["run"], np.int64), subrun=np.asarray(ids["subrun"], np.int64),
                                                      evt=np.asarray(ids["evt"], np.int64),
                                                      wc_valid=f.read_valid().astype(np.int8) if rec["has_wc_valid"] else -1))
            except C.CafError as e:
                rec.update(ids_aligned=False, error="ids: " + str(e)[:200])
    except C.MissingBranchError as e:
        rec.update(error="missing: " + str(e)[:200], has_recTree=None, has_recTreeWireCell=None)
    except C.AlignmentError as e:
        rec.update(opened=True, entries_aligned=False, error="alignment: " + str(e)[:200])
    except Exception as e:  # noqa: BLE001
        rec["error"] = repr(e)[:200]
    return rec


# ---------------------------------------------------------------------------------------------------- provenance gate
def load_gate(path=GATE_YAML) -> dict:
    return yaml.safe_load(open(path))


def evaluate_gate(gate: dict, facts: dict) -> dict:
    """Evaluate the machine-readable gate against measured ``facts`` (a flat dict). Each check has a ``level`` REQUIRED / EXPECTED / INFORMATIONAL
    and a ``rule`` (``equals``, ``in``, ``true``, ``false``, ``present``, ``min``). A check whose fact is absent is UNKNOWN (never a pass).
    The gate is OPEN only if every REQUIRED check passes; EXPECTED failures are reported as warnings; INFORMATIONAL never block."""
    rows = []
    for c in gate["checks"]:
        fact = c["fact"]; v = facts.get(fact, "__absent__"); rule = c["rule"]; ref = c.get("value")
        if isinstance(v, str) and v == "__absent__":
            status = "UNKNOWN"
        elif rule == "true":
            status = "PASS" if v is True else "FAIL"
        elif rule == "false":
            status = "PASS" if v is False else "FAIL"
        elif rule == "equals":
            status = "PASS" if v == ref else "FAIL"
        elif rule == "in":
            status = "PASS" if v in ref else "FAIL"
        elif rule == "present":
            status = "PASS" if v not in (None, "", [], {}) else "FAIL"
        elif rule == "min":
            status = "PASS" if v is not None and v >= ref else "FAIL"
        else:
            raise ValueError(f"unknown rule {rule!r} in check {c['id']}")
        rows.append(dict(id=c["id"], level=c["level"], fact=fact, rule=rule, value=ref, observed=v if status != "UNKNOWN" else None, status=status,
                         why=c.get("why", "")))
    df = pd.DataFrame(rows)
    req = df[df.level == "REQUIRED"]
    gate_open = bool((req.status == "PASS").all())
    return dict(open=gate_open, required_failed=req[req.status == "FAIL"].id.tolist(), required_unknown=req[req.status == "UNKNOWN"].id.tolist(),
                expected_not_passing=df[(df.level == "EXPECTED") & (df.status != "PASS")].id.tolist(), table=df)
