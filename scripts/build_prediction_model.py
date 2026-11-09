#!/usr/bin/env python
"""Machine-readable background-rate model and the status of the formal prediction (no result is claimed).

    source env/setup_eaf.sh && python scripts/build_prediction_model.py

B_BNB_NEUTRINO: selected NON-signal BNB CV events from the validated Phase-4 table (the natural NC Delta signal-like events are removed). Rate = N / POT_CV.
B_COSMIC: beam-off SHAPE (raw selected counts) only; absolute scale unresolved. DATA: open beam-on raw counts. S_NCDELTA: pending the official Wire-Cell sample.
Writes tables/official_signal/{background_rate_model.json, prediction_status.json}. The prediction object refuses totals/purity/S:B/significance.
"""
from __future__ import annotations
import json, os, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(REPO / "src"))
import pandas as pd
from sbnd_single_photon import prediction as P

SPD = Path(os.environ["SP_DATA"]); TAB = REPO / "tables" / "official_signal"; TAB.mkdir(parents=True, exist_ok=True)
tab = pd.read_parquet(SPD / "background_mechanisms" / "bnb_cv" / "background_mechanism_table.parquet")
pot_cv = float(pd.read_parquet(SPD / "analysis_tables" / "bnb_cv" / "files.parquet").total_pot.sum())
sel = tab.assign(reco_channel=tab.reco_channel.replace({"ge2p_diag": "ge2p"}))
cls = sel.event_class.value_counts().to_dict()
assert cls == {"background": 635, "signal_like": 14}, cls            # exact Phase-4 accounting, 649 = 14 + 635 + 0
comp = P.bnb_background_component(sel, pot_cv, 1e20)
cnt = {ch: int((sel[sel.event_class == "background"].reco_channel == ch).sum()) for ch in P.CHANNELS}
assert cnt == {"1g0p": 310, "1g1p": 230, "ge2p": 95}, cnt
rate = {ch: dict(count=cnt[ch], rate_per_1e20_POT=comp.values[ch], stat_unc_per_1e20_POT=comp.stat_unc[ch]) for ch in P.CHANNELS}
model = dict(component="B_BNB_NEUTRINO", sample="bnb_cv", pot_cv=pot_cv, event_classes_in_table=cls, signal_like_removed=int(cls["signal_like"]),
             background_events=int(cls["background"]), by_reco_channel=rate, uncertainty="statistical (Poisson) only; no cosmic-only component, no flux/xsec/detector systematics",
             nueCC_dedicated_sample="NOT included (control sample only)", note="rate of selected non-signal CV events per 1e20 POT; the natural NC-Delta signal-like events are excluded")
(TAB / "background_rate_model.json").write_text(json.dumps(model, indent=1))
dsh = json.load(open(REPO / "tables" / "background_mechanisms" / "data_shape_sanity.json"))
off = dict(zip(P.CHANNELS, dsh["beam_off"]["reco_0p_1p_ge2p"])); on = dict(zip(P.CHANNELS, dsh["beam_on_open"]["reco_0p_1p_ge2p"]))
pred = P.Prediction(1e20, P.pending_signal(), comp, P.cosmic_shape_only(off), P.open_data(on, dsh["beam_on_open"]["sum_TotalPOT_not_used"]), region="active_tpc")
refusals = {}
for name in ("total_background", "purity", "s_over_b", "significance"):
    try:
        getattr(pred, name)(); refusals[name] = "NOT REFUSED (bug)"
    except P.UnresolvedNormalizationError as e:
        refusals[name] = "refused: " + str(e)[:160]
(TAB / "prediction_status.json").write_text(json.dumps(dict(status=pred.status_table(), refusals=refusals, B_COSMIC_shape_counts_beam_off_selected=off,
                                                          DATA_open_beam_on_selected_raw=on), indent=1))
print(json.dumps({k: (v["count"], round(v["rate_per_1e20_POT"], 1), round(v["stat_unc_per_1e20_POT"], 1)) for k, v in rate.items()}), refusals["significance"][:90])
