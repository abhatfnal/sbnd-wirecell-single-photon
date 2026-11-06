# nueCC sample: control only (not added to the BNB CV prediction)

**The 100k nueCC sample is used for branch availability, BDT/electron-background shape studies and classifier-response behaviour. It is NOT added numerically to the BNB CV as a physical POT-normalised component** until Haiwang explains its normalisation.

Provenance: the official nueCC sample (`…_EX_nuecc_v10_14_02_05_{reco1,flat_caf}_sbnd`) belongs to the **Gen2 rare-xsec filtered production**, i.e. a dedicated, filtered sample, not an unbiased BNB spill sample. The filter and the POT weighting convention for such samples have not been established, so its normalisation stays unresolved and it is not added to CV.

Why: Σ TotalPOT = 2.05827e21 over 11,441 files, 1,430,125 generated events: 1.44e15 POT per generated event, ~100× the CV value (1.44e13). It is an exclusive/filtered production, so its `TotalPOT` is not obviously the flux-equivalent exposure of its events; 2,218 (run, subrun) pairs recur in two independent files; 131 files have `rec.hdr.pot ≠ TotalPOT` (`POT_EXPOSURE_AUDIT.md`).

What the code does: `scripts/baseline_report.py nuecc` writes all rates as empty (None) unless `--allow-rates` is given deliberately; shape plots never overlay nueCC with CV.

Raw, sample-conditional numbers (`tables/baseline/nuecc_cutflow.csv`; **fractions of this exclusive sample, not rates**): 100,003 events, 99,946 `wc.valid`; 98,576 candidates; 80,734 (81.9 %) BDT-evaluable; events passing the full chain: 15,886 (`any`) / 15,531 (`first`) = 15.9 % / 15.5 % of valid events; reco 0p/1p/≥2p of the selected events (`any`): 5,261 / 7,434 / 3,191. One event has two passing candidates. These are properties of the nueCC sample, not a ν_e background yield for BNB.

Needed before it can be combined: the rare-xsec filter definition (the 7 % survival of the CC ν_e filter chain seen in the release fcl) and the POT weighting convention for that production; an intrinsic-ν_e flux-equivalent exposure (or a defined cross-check against the 1,016 intrinsic-ν_e events already present in the CV sample).
