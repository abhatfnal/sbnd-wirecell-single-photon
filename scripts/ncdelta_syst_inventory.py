#!/usr/bin/env python
"""Inventory of the systematic-weight branches present in the merged Wire-Cell CAFs (read-only metadata; nothing is applied).

The weights live in the standard `recTree` (rec.mc.nu.wgt.univ, names in globalTree global/wgts/*), NOT in `recTreeWireCell`.
Detector-variation samples are separate productions and are not in these files.

    source env/setup_eaf.sh && export BEARER_TOKEN_FILE=... && python scripts/ncdelta_syst_inventory.py
"""
from __future__ import annotations
import collections, os, re, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src"))
OUT = REPO / "tables" / "ncdelta_purity_datamc"


def family(n: str) -> tuple[str, str]:
    if n.endswith("_Flux"): return "flux (beam hadron production / focusing / attenuation)", "flux"
    if n.startswith("reinteractions_"): return "flux (hadron re-interaction in beamline, Geant4)", "flux"
    if n.startswith("GENIEReWeight"): return "GENIE cross-section / hadronisation / FSI model knobs", "xsec_fsi"
    if n.startswith(("MINERvA", "MiscInteraction", "NOvAStyle")): return "SBN cross-section tune extras (2p2h, non-resonant pion, misc)", "xsec_fsi"
    return "other", "other"


def main():
    import pandas as pd, uproot
    from sbnd_single_photon import samples as S
    rows = []
    for name, m in (("bnb_cv", "manifests/wcl1116/bnb_cv.tsv.gz"), ("official_gen2_ncdelta", "manifests/wcl1116/official_gen2_ncdelta.tsv.gz")):
        f = uproot.open(S.read_manifest(REPO / m)[0]["url"]); g = f["globalTree"]
        nm = [str(x) for x in g["global/wgts/wgts.name"].array(library="ak")[0]]; nu = g["global/wgts/wgts.nuniv"].array(library="ak")[0].tolist(); ty = g["global/wgts/wgts.type"].array(library="ak")[0].tolist()
        t = f["recTree"]; wc = f["recTreeWireCell"]
        for n, k, y in zip(nm, nu, ty):
            d, c = family(n); rows.append(dict(sample=name, weight=n, n_universes=k, type_code=y, family=d, category=c))
        print(name, "recTree has wgt.univ:", "rec.mc.nu.wgt.univ" in t.keys(), "| recTreeWireCell weight-like branches:",
              len([b for b in wc.keys() if re.search(r"wgt|univ|syst", b, re.I) and "bdt_weights" not in b and "dl_weights" not in b]), "| entries recTree/WC", t.num_entries, wc.num_entries)
    df = pd.DataFrame(rows); OUT.mkdir(parents=True, exist_ok=True); df.to_csv(OUT / "systematic_weights_inventory.csv", index=False)
    a = df[df["sample"] == "bnb_cv"]
    summ = a.groupby("category").agg(n_functions=("weight", "size"), total_universes=("n_universes", "sum")).reset_index()
    summ["detector_variations"] = "not in these files (separate detvar productions required)"
    summ.to_csv(OUT / "systematic_weights_summary.csv", index=False); print(summ.to_string(index=False))
    same = set(zip(df[df["sample"] == "bnb_cv"].weight, df[df["sample"] == "bnb_cv"].n_universes)) == set(zip(df[df["sample"] != "bnb_cv"].weight, df[df["sample"] != "bnb_cv"].n_universes))
    print("identical weight set in CV and dedicated NC-Delta:", same)


if __name__ == "__main__":
    main()
