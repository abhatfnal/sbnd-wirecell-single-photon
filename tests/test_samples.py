import gzip
import pytest
from sbnd_single_photon import samples as S, xrd


def test_registry_parsing():
    reg = S.load_samples()
    assert set(reg) == {"bnb_cv", "nuecc", "beam_off", "beam_on_open",
                       "official_gen2_ncdelta", "aurora_ncdelta_training"}
    cv = reg["bnb_cv"]
    assert cv.available and cv.is_mc and cv.n_files_listed == 37742 and cv.n_wc_valid_events == 499899
    assert reg["beam_on_open"].schema_md5.startswith("c845fe94fbe5") and reg["beam_on_open"].is_mc is False
    assert reg["beam_off"].n_caf_events == 49970


def test_signal_registry_entries_record_only_verified_data():
    reg = S.load_samples()
    tr = reg["aurora_ncdelta_training"]
    assert not tr.available and tr.manifest is None and tr.n_caf_events is None and tr.n_files_listed is None and tr.status == "remains_on_aurora"
    with pytest.raises(ValueError):
        S.manifest_urls(tr)
    og = reg["official_gen2_ncdelta"]                                                      # registered 2026-11-10 after the provenance gate opened
    assert og.status == "available" and og.available and og.is_mc and og.n_files_listed == 9150
    assert og.n_caf_events == og.n_wc_valid_events == 13772
    assert og.extra["official_flatcaf_status"] == "available" and og.extra["wirecell_merged_status"] == "available"
    assert og.extra["sam"]["flat_caf"]["files"] == 15777 and og.extra["sam"]["flat_caf"]["events"] == 13773   # SAM census (one event never processed)
    assert og.extra["flatcaf_census"]["stored_events"] == 13773
    assert len(S.manifest_urls(og)) == 9150


def test_train_evaluation_separation():
    reg = S.load_samples()
    assert reg["official_gen2_ncdelta"].role == "signal_evaluation" and reg["official_gen2_ncdelta"].may_train is False
    assert reg["aurora_ncdelta_training"].may_train is True and reg["aurora_ncdelta_training"].may_evaluate is False
    for n in ("bnb_cv", "nuecc", "beam_off", "beam_on_open"):
        assert reg[n].may_train is False and reg[n].available


def test_manifest_roundtrip(tmp_path):
    p = tmp_path / "m.tsv.gz"
    with gzip.open(p, "wt") as fh:
        fh.write("# sample: x\nindex\tpnfs_path\txrootd_url\n")
        for i, q in enumerate(["/pnfs/sbnd/persistent/b.root", "/pnfs/sbnd/persistent/a.root"]):
            fh.write(f"{i}\t{q}\t{xrd.to_xrootd_url(q)}\n")
    rows = S.read_manifest(p)
    assert [r["pnfs_path"] for r in rows] == ["/pnfs/sbnd/persistent/b.root", "/pnfs/sbnd/persistent/a.root"]  # order kept
    assert rows[0]["url"].startswith("root://fndcadoor.fnal.gov//pnfs/fnal.gov/usr/sbnd/")


def test_committed_manifests_consistent_with_registry():
    for name, s in S.load_samples().items():
        if not s.available:
            continue
        rows = S.read_manifest(s.manifest)
        assert len(rows) == s.n_files_listed, name
        assert len({r["pnfs_path"] for r in rows}) == len(rows)
        assert all(r["url"] == xrd.to_xrootd_url(r["pnfs_path"]) for r in rows[:50])
