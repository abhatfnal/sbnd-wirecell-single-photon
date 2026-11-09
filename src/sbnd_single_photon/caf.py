"""Reader for the merged flat CAF: ``recTree`` + ``recTreeWireCell`` (aligned by run/subrun/event).

Design rules (see docs/analysis/NCDELTA_BASELINE_ANALYSIS_DESIGN.md):
  * only the branches the caller asks for are ever read (the CAF has ~2,660 + ~2,400 branches);
  * a missing required branch is a hard, explicit error (``MissingBranchError``), never a silent NaN;
  * ``wc.valid == 1`` marks a usable Wire-Cell reconstruction; it is exposed, never applied implicitly;
  * the open beam-on data use an older strict-subset schema, so data/MC code must request only common branches
    (``common_branches``).

Jagged layout of ``recTreeWireCell`` (verified on fg1 MC):
  * every ``T_kine`` / ``T_tagger`` / ... scalar column is ``var[event][candidate]`` (one entry per neutrino
    candidate; 0, 1 or 2+ candidates per event, ``nu_index`` identifies them);
  * a per-particle column such as ``wc.T_kine.kine_particle_type`` is stored FLAT per event with two helper
    branches ``<name>..length`` (length per candidate) and ``<name>..idx`` (start offsets).
    Use :func:`per_candidate` / :meth:`MergedCaf.read_nested` to get ``var[event][candidate][particle]``.
"""
from __future__ import annotations

import warnings
from typing import Iterable, Optional, Sequence

import awkward as ak
import numpy as np

from . import xrd

WC_PREFIX = "wc."
REC_ID = ["rec.hdr.run", "rec.hdr.subrun", "rec.hdr.evt"]
WC_ID = ["wc.run", "wc.subrun", "wc.evt"]
WC_VALID = "wc.valid"
SUFFIXES = ("..length", "..idx", "..totarraysize")


class CafError(RuntimeError):
    pass


class MissingBranchError(CafError):
    def __init__(self, where: str, missing: Sequence[str], path: str = ""):
        self.missing = list(missing)
        super().__init__(f"{where}: {len(self.missing)} required branch(es) missing"
                         f"{' in ' + path if path else ''}: {self.missing[:12]}"
                         f"{' ...' if len(self.missing) > 12 else ''}")


class AlignmentError(CafError):
    pass


def is_helper_branch(name: str) -> bool:
    return name.endswith(SUFFIXES)


def per_candidate(flat: ak.Array, length: ak.Array) -> ak.Array:
    """Regroup a flat per-event list into ``[event][candidate][item]`` using the ``..length`` branch.

    ``flat``   : var * T   (all candidates concatenated)
    ``length`` : var * int (items per candidate)
    """
    counts = ak.num(length, axis=1)
    tot = ak.to_numpy(ak.sum(length, axis=1)) if len(length) else np.zeros(0, dtype=int)
    have = ak.to_numpy(ak.num(flat, axis=1)) if len(flat) else np.zeros(0, dtype=int)
    if not np.array_equal(np.asarray(tot, dtype=np.int64), np.asarray(have, dtype=np.int64)):
        bad = int(np.sum(np.asarray(tot) != np.asarray(have)))
        raise CafError(f"nested branch inconsistent with its ..length in {bad} event(s)")
    inner = ak.unflatten(ak.flatten(flat, axis=1), ak.flatten(length, axis=1))
    return ak.unflatten(inner, counts)


class MergedCaf:
    """One merged CAF (local path, ``/pnfs`` path or XRootD URL)."""

    def __init__(self, path: str, *, door: str = xrd.DOOR, check_alignment: bool = True):
        self.path = path
        self.url = xrd.resolve(path, door)
        self.check_alignment = check_alignment
        self._f = None
        self._rt = None
        self._wt = None
        self._rec_keys: Optional[frozenset] = None
        self._wc_keys: Optional[frozenset] = None

    # -- lifecycle ---------------------------------------------------------------------------
    def open(self) -> "MergedCaf":
        import uproot
        warnings.filterwarnings("ignore", category=FutureWarning)
        self._f = uproot.open(self.url)
        for name in ("recTree", "recTreeWireCell"):
            if name not in self._f:
                raise MissingBranchError("file", [name], self.url)
        self._rt, self._wt = self._f["recTree"], self._f["recTreeWireCell"]
        self._rec_keys = frozenset(self._rt.keys())
        self._wc_keys = frozenset(self._wt.keys())
        if self._rt.num_entries != self._wt.num_entries:
            raise AlignmentError(f"recTree has {self._rt.num_entries} entries, recTreeWireCell "
                                 f"{self._wt.num_entries} in {self.url}")
        return self

    def close(self) -> None:
        if self._f is not None:
            self._f.close()
            self._f = None

    def __enter__(self):
        return self.open()

    def __exit__(self, *exc):
        self.close()

    # -- schema ------------------------------------------------------------------------------
    @property
    def num_entries(self) -> int:
        return self._wt.num_entries

    @property
    def rec_branches(self) -> frozenset:
        return self._rec_keys

    @property
    def wc_branches(self) -> frozenset:
        return self._wc_keys

    @property
    def n_wc_branches(self) -> int:
        return len(self._wc_keys)

    def has_wc(self, name: str) -> bool:
        return name in self._wc_keys

    def has_rec(self, name: str) -> bool:
        return name in self._rec_keys

    @property
    def has_truth_matching(self) -> bool:
        """MC schema (2,401 branches) has the truth + matching trees; the old beam-on schema does not."""
        return any(k.startswith("wc.T_match.") for k in self._wc_keys)

    def schema_md5(self) -> Optional[str]:
        import json
        try:
            return json.loads(self._f["recTreeWireCell_info"].member("fTitle")).get("schema_md5")
        except Exception:
            return None

    def trun(self, name: str, default=None):
        """First-entry string/number of a ``wc.Trun.*`` branch (provenance, e.g. dl_weights)."""
        key = WC_PREFIX + "Trun." + name
        if key not in self._wc_keys:
            return default
        v = self._wt[key].array(entry_stop=1)[0]
        v = ak.to_list(v)
        if isinstance(v, list) and v and isinstance(v[0], int) and name in ("dl_weights", "wct_version", "input_file", "bdt_weights_dir"):
            return bytes(v).decode("latin1")
        return v

    # -- requirements ------------------------------------------------------------------------
    def require(self, wc: Iterable[str] = (), rec: Iterable[str] = ()) -> None:
        mw = [b for b in wc if b not in self._wc_keys]
        mr = [b for b in rec if b not in self._rec_keys]
        if mw:
            raise MissingBranchError("recTreeWireCell", mw, self.url)
        if mr:
            raise MissingBranchError("recTree", mr, self.url)

    # -- reading -----------------------------------------------------------------------------
    def read_ids(self, start: int = 0, stop: Optional[int] = None, *, verify: Optional[bool] = None) -> dict:
        """run/subrun/event from BOTH trees; raises AlignmentError if they disagree."""
        verify = self.check_alignment if verify is None else verify
        self.require(WC_ID + [WC_VALID], REC_ID)
        w = self._wt.arrays(WC_ID, entry_start=start, entry_stop=stop, library="np")
        r = self._rt.arrays(REC_ID, entry_start=start, entry_stop=stop, library="np")
        ids = {"run": r["rec.hdr.run"], "subrun": r["rec.hdr.subrun"], "evt": r["rec.hdr.evt"]}
        if verify:
            for a, b, n in (("rec.hdr.run", "wc.run", "run"), ("rec.hdr.subrun", "wc.subrun", "subrun"),
                            ("rec.hdr.evt", "wc.evt", "evt")):
                if not np.array_equal(np.asarray(r[a], dtype=np.int64), np.asarray(w[b], dtype=np.int64)):
                    raise AlignmentError(f"{n} differs between recTree and recTreeWireCell in {self.url}")
        return ids

    def read_valid(self, start: int = 0, stop: Optional[int] = None) -> np.ndarray:
        """``wc.valid == 1`` mask (bool)."""
        self.require([WC_VALID])
        return self._wt[WC_VALID].array(entry_start=start, entry_stop=stop, library="np") == 1

    def read(self, wc: Sequence[str] = (), rec: Sequence[str] = (), start: int = 0,
             stop: Optional[int] = None, *, with_ids: bool = True) -> dict:
        """Read ONLY the requested branches. Returns ``{branch_name: ak.Array}`` plus ``ids`` and ``wc.valid``.

        Nested per-particle branches must be read through :meth:`read_nested`.
        """
        wc, rec = list(dict.fromkeys(wc)), list(dict.fromkeys(rec))
        self.require(wc, rec)
        out: dict = {}
        if wc:
            out.update(self._wt.arrays(wc, entry_start=start, entry_stop=stop, library="ak", how=dict))
        if rec:
            out.update(self._rt.arrays(rec, entry_start=start, entry_stop=stop, library="ak", how=dict))
        out[WC_VALID] = self._wt[WC_VALID].array(entry_start=start, entry_stop=stop, library="ak")
        if with_ids:
            out["ids"] = self.read_ids(start, stop)
        return out

    def read_nested(self, name: str, start: int = 0, stop: Optional[int] = None) -> ak.Array:
        """``var[event][candidate][particle]`` for a nested ``wc.<Tree>.<branch>`` column."""
        self.require([name, name + "..length"])
        flat = self._wt[name].array(entry_start=start, entry_stop=stop, library="ak")
        length = self._wt[name + "..length"].array(entry_start=start, entry_stop=stop, library="ak")
        return per_candidate(flat, length)


def common_branches(*cafs: MergedCaf, tree: str = "wc") -> list[str]:
    """Branches present in ALL given files (use this for data/MC comparisons)."""
    sets = [c.wc_branches if tree == "wc" else c.rec_branches for c in cafs]
    return sorted(frozenset.intersection(*sets))
