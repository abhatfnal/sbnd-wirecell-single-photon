#!/usr/bin/env python
"""Manifests of the WCLocal2026Nov16-FermiGrid merged CAFs (read from Haiwang's published lists; nothing is written to dCache).

    source env/setup_eaf.sh && python scripts/wcl1116_make_manifests.py

Lists live in $SP_DATA/wcl1116_nov16/lists (fetched with xrdcp from .../prod-fermigrid/WCLocal2026Nov16/lists). Manifest rows: ``index  pnfs_path  xrootd_url`` in list order.
Registry name <- Nov16 folder:  bnb_cv<-mc-cv, nuecc<-mc-nuecc, beam_off<-beam-off, beam_on_open<-opendata, official_gen2_ncdelta<-mc-ncdr, run3bnb<-run3bnb.
"""
import gzip, os, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src"))
from sbnd_single_photon import xrd
MAP = {"bnb_cv": "mc-cv", "nuecc": "mc-nuecc", "beam_off": "beam-off", "beam_on_open": "opendata", "official_gen2_ncdelta": "mc-ncdr", "run3bnb": "run3bnb"}
L = Path(os.environ["SP_DATA"]) / "wcl1116_nov16" / "lists"
for reg, d in MAP.items():
    paths = [l.strip() for l in open(L / f"{d}.merged-caf.txt") if l.strip()]
    assert all("/WCLocal2026Nov16/" in p for p in paths), d
    out = REPO / "manifests" / "wcl1116" / f"{reg}.tsv.gz"
    with gzip.open(out, "wt") as fh:
        fh.write("index\tpnfs_path\txrootd_url\n")
        for i, p in enumerate(paths):
            fh.write(f"{i}\t{p}\t{xrd.to_xrootd_url(p)}\n")
    print(reg, d, len(paths), out.name)
