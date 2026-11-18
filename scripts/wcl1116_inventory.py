#!/usr/bin/env python
"""Sample inventory + production provenance of WCLocal2026Nov16-FermiGrid (reads the published lists and the built tables; no dCache writes).

    source env/setup_eaf.sh && python scripts/wcl1116_inventory.py
-> tables/wcl1116_nov16_replay/{sample_inventory.csv, production_provenance.csv, inventory_summary.json}
"""
import gzip, json, os, sys
from pathlib import Path
import pandas as pd
REPO = Path(__file__).resolve().parents[1]; SPD = Path(os.environ["SP_DATA"]); L = SPD / "wcl1116_nov16" / "lists"; NEW = SPD / "wcl1116_nov16" / "analysis_tables_new"
OUT = REPO / "tables" / "wcl1116_nov16_replay"; OUT.mkdir(parents=True, exist_ok=True)
BASE = "/pnfs/sbnd/persistent/users/yuhw/prod-fermigrid/WCLocal2026Nov16"
MAP = {"mc-cv": ("bnb_cv", "BNB CV MC"), "mc-nuecc": ("nuecc", "intrinsic nueCC MC"), "mc-ncdr": ("official_gen2_ncdelta", "dedicated NC-Delta radiative MC"),
       "beam-off": ("beam_off", "beam-off data"), "run3bnb": ("run3bnb", "Run-3 BNB beam-on data"), "opendata": ("beam_on_open", "open BNB data (runs 18255/18259)")}
SAM = {"mc-cv": "aurora_SBND2026A_gen2_BNBLight_..._CV_v10_14_02_03_reco1_sbnd", "mc-nuecc": "aurora_SBND2026A_gen2_BNBLight_..._EX_nuecc_v10_14_02_05_reco1_sbnd",
       "mc-ncdr": "aurora_SBND2026A_gen2_BNBLight_..._EX_ncdeltarad_v10_14_02_05_reco1_sbnd", "beam-off": "data_SBND2026A_gen2_InTime-Run1_v10_14_02_02_reco1_sbnd",
       "run3bnb": "data_SBND2026A_Gen2_Run3_BeamLight_Fixed_Dev_Data_v10_14_02_08_reco1_sbnd", "opendata": "data_MCP2025C_Fall25-Run1_BNB_FixedDev_bnblight_v10_14_02_reco1_sbnd (Respin CAF)"}
rows = []
for d, (reg, what) in MAP.items():
    st = pd.read_csv(L / f"status-{d}.tsv", sep="\t"); st.columns = [c.lstrip("#") for c in st.columns]
    ev = pd.read_csv(L / f"events-{d}.tsv.gz", sep="\t"); ev.columns = [c.lstrip("#") for c in ev.columns]
    vc = st.status.value_counts().to_dict(); caf = [l for l in open(L / f"{d}.merged-caf.txt") if l.strip()]
    r = dict(folder=d, registry=reg, what=what, path=f"{BASE}/{d}/", input_reco1_sam=SAM[d], pairs=len(st), pairs_OK=int(vc.get("OK", 0)), pairs_PARTIAL=int(vc.get("PARTIAL", 0)),
             pairs_EMPTY=int(vc.get("EMPTY", 0)), pairs_FAIL=int(sum(v for k, v in vc.items() if k not in ("OK", "PARTIAL", "EMPTY"))), merged_cafs=len(caf),
             caf_events=int(st.caf_events.sum()), wc_valid_split=int(st.wc_split.sum()), wc_valid_snap=int(st.wc_snap.sum()), events_listed=len(ev),
             tree_default="recTreeWireCell (dv2_split_move, schema af9c87c8)", tree_alternate="recTreeWireCell_dv2snap (dv2_snap, schema d4396a34; provenance only)",
             wct="0.38.0 c935e30d", larwirecell="sbnd-wc-flatcaf ad5d9421", wire_cell_data="99c6497f (dv2max/sbnd/aurora_space bundle) + uboone BDT weights", sbndcode="v10_14_02_03 e26:prof")
    t = NEW / reg / "files.parquet"
    if t.exists():
        f = pd.read_parquet(t); r["built_files"] = len(f); r["built_events"] = int(f.n_events.sum()); r["built_schema_md5"] = ",".join(sorted(f.schema_md5.astype(str).str[:8].unique()))
        r["TotalPOT"] = float(f.total_pot.sum())
    rows.append(r)
inv = pd.DataFrame(rows); inv.to_csv(OUT / "sample_inventory.csv", index=False)
prov = [  # source: Haiwang's READMEs (fg1, ncdr, run3bnb, WCLocal2026Nov16) and ai-helper issue 48; 'not stated' is recorded, never filled in
 ("wire-cell-toolkit", "4b6853d4 (fg1, ncdr, run3bnb); f6fd2209 (open data)", "0.38.0, c935e30d (= master 647b2733 + version.txt)", "CHANGED"),
 ("larwirecell", "sbnd-wc-flatcaf ad5d9421 (fg1/run3bnb/ncdr); 3b54651 (open data)", "sbnd-wc-flatcaf ad5d9421", "same (fg1/ncdr/run3bnb)"),
 ("wire-cell-data", "9e2f4b8 (run3bnb README); fg1/ncdr: not stated", "99c6497f (master with dv2max/sbnd/aurora_space) + XGB/SCN weights", "CHANGED"),
 ("DL vertex model / bundle", "not stated", "DV2-MAX aurora_space, dv2max/sbnd/aurora_space/bundle.json (sha256 51588842...)", "CHANGED or unknown (old not stated)"),
 ("DL vertex mode of recTreeWireCell", "not named", "dv2_split_move (default); a second tree uses dv2_snap", "unknown (old not named)"),
 ("step 1 (imaging/clustering/matching)", "fg1 / ncdr / run3bnb step-1 tars", "the same tars reused (array-by-array identical on 25/25 files, issue 48 P2)", "unchanged"),
 ("step 2 chain", "wct-pr.jsonnet, dual chain in the old 'original' step 2", "wct-pr.jsonnet, single chain per mode", "CHANGED"),
 ("flat-tree schema md5 of recTreeWireCell", "d4396a3490ea (2,401 branches)", "af9c87c8 (2,416 branches; adds the DL-vertex space dump)", "CHANGED (extra branches)"),
 ("booked numu / nue BDT weights", "not stated", "not stated (uboone BDT weights listed)", "not established"),
 ("cosmic boundary configuration", "box boundary (stated for Nov16 by Haiwang)", "box boundary (current treatment)", "same as stated; not independently verified"),
 ("SCE policy", "not stated", "no SCE-back correction (stated by Haiwang)", "not established for old"),
 ("sbndcode", "v10_14_02_03 e26:prof", "v10_14_02_03 e26:prof", "same"),
 ("input reco1 / CAF files", "fg1 / ncdr SAM selections", "the same SAM selections (NC-Delta-rad: every pair; same 13,772 events)", "same input events"),
]
pd.DataFrame(prov, columns=["item", "old production (fg1 / ncdr)", "WCLocal2026Nov16", "status"]).to_csv(OUT / "production_provenance.csv", index=False)
json.dump(dict(samples=inv.set_index("registry")[["pairs", "pairs_OK", "pairs_PARTIAL", "pairs_EMPTY", "merged_cafs", "caf_events", "wc_valid_split"]].to_dict("index")), open(OUT / "inventory_summary.json", "w"), indent=1)
print(inv[["folder", "pairs", "pairs_OK", "pairs_PARTIAL", "pairs_EMPTY", "merged_cafs", "caf_events", "wc_valid_split", "wc_valid_snap"]].to_string())
