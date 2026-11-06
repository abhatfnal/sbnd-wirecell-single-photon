import pytest
from sbnd_single_photon import xrd


def test_short_to_full_and_url():
    p = "/pnfs/sbnd/persistent/users/yuhw/prod-fermigrid/fg1/mc-cv/a/b.root"
    assert xrd.to_full_pnfs(p) == "/pnfs/fnal.gov/usr/sbnd/persistent/users/yuhw/prod-fermigrid/fg1/mc-cv/a/b.root"
    assert xrd.to_xrootd_url(p) == "root://fndcadoor.fnal.gov//pnfs/fnal.gov/usr/sbnd/persistent/users/yuhw/prod-fermigrid/fg1/mc-cv/a/b.root"


def test_idempotent_and_roundtrip():
    p = "/pnfs/sbnd/persistent/x.root"
    full = xrd.to_full_pnfs(p)
    assert xrd.to_full_pnfs(full) == full
    assert xrd.to_short_pnfs(full) == p
    u = xrd.to_xrootd_url(p)
    assert xrd.to_xrootd_url(u) == u


def test_resolve_local_and_errors():
    assert xrd.resolve("/exp/sbnd/data/x.root") == "/exp/sbnd/data/x.root"
    with pytest.raises(ValueError):
        xrd.to_full_pnfs("/exp/sbnd/x")


def test_tls_door():
    assert xrd.to_xrootd_url("/pnfs/sbnd/a", xrd.DOOR_TLS).startswith("xroots://fndcadoor.fnal.gov:1094//pnfs/fnal.gov/usr/sbnd/")
