#!/usr/bin/env python
"""Delta-mass response of the decay pairs, recomputed on the objects that are still selected under the source-faithful scorer (restriction of the stored Phase-11 table; no ROOT).

    source env/setup_eaf.sh && python scripts/legacy_scorer_delta_mass_subset.py
The Phase-11 object table holds only objects selected as run. Objects selected ONLY under the corrected scorer (a few events whose ncpi0 score changed with kine_pio_flag = 0) have no row;
their number is reported. Validation: with the as-run candidate table the restriction reproduces the committed 348 decay pairs / median +2.77 MeV / [-44.1, +33.7] MeV exactly.
Writes tables/legacy_scorer_correction/delta_mass_subset.csv.
"""
import os, sys, warnings
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src")); warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
SPD = Path(os.environ["SP_DATA"]); SPC = SPD / "legacy_scorer_correction"; OUT = REPO / "tables" / "legacy_scorer_correction"
d = pd.read_parquet(SPD / "common_observables" / "official_ncdelta" / "delta_mass_table.parquet")
d = d[d.policy == "any"] if "policy" in d else d
rows = []
for cfg in ("A_old", "D_full"):
    c = pd.read_parquet(SPC / f"official_candidates_{cfg}.parquet", columns=["file_index", "ev", "c_nu_index", "pass_final"]); c = c[c.pass_final].rename(columns={"c_nu_index": "cand"})
    m = d.merge(c[["file_index", "ev", "cand"]].assign(_s=True), on=["file_index", "ev", "cand"], how="left"); s = m[m._s.fillna(False).astype(bool)]
    ok = s[(s["baseline_35__mass_status"] == "ok")]; dec = ok[ok["baseline_35__pair_class"] == "decay_pair"]
    r = (dec["baseline_35__m_delta"] - dec["m_true_decay"]).to_numpy(float)
    n_new_events = int(len(c.drop_duplicates(["file_index", "ev"])) - len(c.drop_duplicates(["file_index", "ev"]).merge(d[["file_index", "ev"]].drop_duplicates(), on=["file_index", "ev"])))
    rows.append(dict(config=cfg, selected_objects_with_row=int(len(s)), selected_reco_1g1p_with_mass=int(len(ok)), decay_pairs=int(len(dec)), median_mev=float(np.median(r)), p16_mev=float(np.percentile(r, 16)), p84_mev=float(np.percentile(r, 84)),
                     half68_mev=float((np.percentile(r, 84) - np.percentile(r, 16)) / 2), rms_mev=float(np.sqrt(np.mean(r ** 2))), frac_decay_pair=float(len(dec) / max(len(ok), 1)),
                     selected_events_without_row=n_new_events))
R = pd.DataFrame(rows); R.to_csv(OUT / "delta_mass_subset.csv", index=False); print(R.round(3).to_string())
