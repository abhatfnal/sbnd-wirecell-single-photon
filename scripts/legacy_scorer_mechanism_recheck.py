#!/usr/bin/env python
"""Does each earlier mechanism conclusion survive the scorer correction? Re-reads only stored products (no ROOT, no training).

    source env/setup_eaf.sh && python scripts/legacy_scorer_mechanism_recheck.py
Writes tables/legacy_scorer_correction/mechanism_recheck.csv: the numu compact / not-compact survival at the as-run and the corrected numu cut (Phase-12 stored stage inputs, official sample), and the conditional survival of every stage
by truth topology under both scorers (cutflows of the committed as-run and of the rebuilt source-faithful products).
"""
import os, sys, warnings
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from sbnd_single_photon import legacy_scorer as L
SPD = Path(os.environ["SP_DATA"]); OUT = REPO / "tables" / "legacy_scorer_correction"
rows = []
# numu: compactness (length_total < 20 cm), object level, as the Phase-18 audit
I = pd.read_parquet(SPD / "remaining_stage_audit" / "official_ncdelta" / "numu_stage_inputs.parquet", columns=["stage_score", "in_shw_sp_length_total", "in_shw_sp_br3_1_n_shower_segments"])
v = I.stage_score.to_numpy(float); vt = float(L.response_from_score(0.4))
for lab, m in (("compact (length < 20 cm)", I.in_shw_sp_length_total < 20), ("not compact (>= 20 cm)", I.in_shw_sp_length_total >= 20), ("few-segment (< 5)", I.in_shw_sp_br3_1_n_shower_segments < 5), ("not few-segment", I.in_shw_sp_br3_1_n_shower_segments >= 5)):
    for nm, thr in (("as_run_v>0.4", 0.4), ("corrected_score>0.4 (v>%.4f)" % vt, vt)):
        rows.append(dict(item="numu_survival", group=lab, scorer=nm, n=int(m.sum()), passing=int((v[m.to_numpy()] > thr).sum()), value=float((v[m.to_numpy()] > thr).mean())))
# conditional stage survival by truth topology
A = pd.read_csv(REPO / "tables" / "official_signal" / "official_active_tpc" / "cutflow_A_any.csv"); D = pd.read_csv(REPO / "tables" / "legacy_scorer_correction" / "source_faithful" / "official_signal" / "official_active_tpc" / "cutflow_A_any.csv")
for nm, cf in (("as_run", A), ("source_faithful", D)):
    st = list(dict.fromkeys(cf.stage))
    for g in ("all", "0p", "1p", ">=2p"):
        prev = None
        for s in st:
            n = int(cf[(cf.stage == s) & (cf.group == g)].N.iloc[0])
            if prev is not None and s in ("numu", "other", "ncpi0", "nue", "n20br1"):
                rows.append(dict(item="stage_conditional_survival", group=f"{s} | truth {g}", scorer=nm, n=prev, passing=n, value=n / prev))
            prev = n
R = pd.DataFrame(rows); R.to_csv(OUT / "mechanism_recheck.csv", index=False); print(R.round(3).to_string())
