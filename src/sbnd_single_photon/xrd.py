"""dCache path <-> XRootD URL conversion for the Fermilab SBND dCache.

Haiwang's prepared lists store the short form ``/pnfs/sbnd/...``. The XRootD door
needs ``/pnfs/fnal.gov/usr/sbnd/...``. This conversion is deterministic and idempotent.
"""
from __future__ import annotations

import os

DOOR = "root://fndcadoor.fnal.gov"
DOOR_TLS = "xroots://fndcadoor.fnal.gov:1094"
_FULL_PREFIX = "/pnfs/fnal.gov/usr/"


def is_url(path: str) -> bool:
    return "://" in path


def to_full_pnfs(path: str) -> str:
    """``/pnfs/sbnd/x`` -> ``/pnfs/fnal.gov/usr/sbnd/x``. Already-full paths pass through."""
    if path.startswith(_FULL_PREFIX):
        return path
    if path.startswith("/pnfs/"):
        return _FULL_PREFIX + path[len("/pnfs/"):]
    raise ValueError(f"not a /pnfs path: {path!r}")


def to_short_pnfs(path: str) -> str:
    """Inverse of :func:`to_full_pnfs`."""
    if path.startswith(_FULL_PREFIX):
        return "/pnfs/" + path[len(_FULL_PREFIX):]
    if path.startswith("/pnfs/"):
        return path
    raise ValueError(f"not a /pnfs path: {path!r}")


def to_xrootd_url(path: str, door: str = DOOR) -> str:
    """Return the XRootD URL for a /pnfs path. URLs are returned unchanged."""
    if is_url(path):
        return path
    return f"{door}/{to_full_pnfs(path)}"  # door + '/' + '/pnfs/...' -> 'door//pnfs/...'


def resolve(path: str, door: str = DOOR) -> str:
    """Local paths are returned as-is, /pnfs paths become URLs, URLs pass through."""
    if is_url(path):
        return path
    if path.startswith("/pnfs/"):
        return to_xrootd_url(path, door)
    return os.fspath(path)
