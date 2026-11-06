# Official BNB CV baseline cut-flow (frozen chain, no FV, no tuning)

**Status: provisional, software baseline. No signal efficiency, no purity, no data/MC comparison.** Nothing was tuned, no classifier retrained, no FV applied (`configs/baseline_selection.yaml`).

Input: all **37,742** listed BNB CV merged CAFs, read once over XRootD with `scripts/baseline_scan.py` (0 read errors) and aggregated by `scripts/baseline_report.py`. 500,000 CAF events, 499,899 with `wc.valid == 1` (101 failures), schema md5 `d4396a34…` in every file, `Trun.dl_weights` = uboone SCN `t48k-m16-l5-lr5d-res0.5-CP24.pth` (4 tiny files, 46 events, have an empty field). **Σ TotalPOT = 2.71940e+19** over exactly these files (no de-duplication by run/subrun); Σ TotalGenEvents = 1,887,100.

Bookkeeping: *candidates* = Wire-Cell neutrino candidates (rows of `T_tagger`) of `wc.valid` events; *events* are counted under two **provisional** candidate policies (`any`: ≥1 candidate passes; `first`: `nu_index == 0` passes; see `CANDIDATE_POLICY_AUDIT.md`). The last two columns are **selected events per 1e20 generated POT** = events / ΣTotalPOT × 1e20 with the Poisson error on the raw count only (no weights, no systematics). They are the POT-normalised neutrino-induced rate of the filtered sample, without the cosmic-only component (see below). `wc.valid == 0` events never pass.

| stage | candidates | events (any) | events (first) | per 1e20 generated POT (any) | per 1e20 generated POT (first) |
|---|---|---|---|---|---|
| all_events | 241,845 | 500,000 | 500,000 | 1,838,639 ± 2,600 | 1,838,639 ± 2,600 |
| wc_valid_fail | 0 | 101 | 101 | 371 ± 37 | 371 ± 37 |
| wc_valid | 241,845 | 499,899 | 499,899 | 1,838,268 ± 2,600 | 1,838,268 ± 2,600 |
| candidate_exists | 241,845 | 237,460 | 237,460 | 873,207 ± 1,792 | 873,207 ± 1,792 |
| (info) bdt_evaluable_candidates | 50,969 | 50,729 | 49,805 | 186,545 ± 828 | 183,147 ± 821 |
| cum:n_20mev_showers_gt0 | 52,926 | 52,663 | 51,708 | 193,657 ± 844 | 190,145 ± 836 |
| cum:single_photon_numu_score_gt_0p4 | 11,945 | 11,933 | 11,590 | 43,881 ± 402 | 42,620 ± 396 |
| cum:single_photon_other_score_gt_0p2 | 3,926 | 3,924 | 3,803 | 14,430 ± 230 | 13,985 ± 227 |
| cum:single_photon_ncpi0_score_gt_m0p05 | 937 | 936 | 906 | 3,442 ± 113 | 3,332 ± 111 |
| cum:single_photon_nue_score_gt_m1 | 937 | 936 | 906 | 3,442 ± 113 | 3,332 ± 111 |
| cum:n_20br1_showers_eq1 | 649 | 649 | 626 | 2,387 ± 94 | 2,302 ± 92 |

Notes on the stages:
- `candidate_exists`: 47.5 % of valid events have ≥1 candidate; `(info) bdt_evaluable_candidates` is not a cut (a candidate is evaluable when `shw_sp_filled != 0` and all inputs of all four BDTs are finite: 50,969 of 241,845 = 21.1 %; see `BDT_EVALUABILITY_AUDIT.md`).
- **The `nue score > -1` cut removes nothing** (937 → 937 candidates): no candidate that survives the earlier cuts has a nue score ≤ −1 (the score is a tanh response, bounded below by −1). It is part of the inherited chain and was not changed or removed.
- No event has more than one candidate passing the full chain, so the final selection is 649 candidates = 649 events under `any`; `first` gives 626.
- **What the per-POT column means (`POT_EXPOSURE_AUDIT.md` §7):** it is the **POT-normalised neutrino-induced background rate from the official filtered Gen2 CV sample**. Only 500,000 of the 1,887,100 generated events (26.5 %) are in the CAFs; this is the intended generator-level filtering of `prodgenie_corsika_proton_rockbox0p1_sbnd.fcl` (`v10_14_02_03`, expected filter efficiency 25 % in the official production request), not an unexplained loss. An event is kept only if a neutrino vertex is in the TPC or neutrino-induced particles deposit >0.1 MeV in the active volume within [−0.2, 1.9] µs; `TotalPOT` is the POT of **all** generated events. **Caveat:** cosmic-only backgrounds are not represented by the rejected generator throws (the cosmic overlay is added after the neutrino-activity filter); the cosmic component must be supplied by beam-off data. Errors are Poisson on the raw count only. The CSV/JSON columns keep the name `stored_per_1e20_genPOT` (events per 1e20 *generated* POT).

## Reco proton category of the final selection (provisional rule: type 2212 and KE > 35 MeV)

| policy | 0p | 1p | ≥2p |
|---|---|---|---|
| first | 307 | 226 | 93 |
| any | 318 | 236 | 95 |
| first, rows with `included == 1` only (sensitivity) | 334 | 209 | 83 |
| any, rows with `included == 1` only (sensitivity) | 347 | 218 | 84 |

For events passing under `any` the category is that of the lowest-`nu_index` passing candidate. These are background-sample counts: they say nothing about 1γ0p/1γ1p signal.

## Final selection by truth category (first-pass taxonomy; `BNB_TRUTH_CATEGORY_AUDIT.md`)

Policy `any` (raw events; per-POT column = POT-normalised neutrino-induced rate, no cosmic-only component):

| category | final events | reco 0p | reco 1p | reco ≥2p | per 1e20 generated POT |
|---|---|---|---|---|---|
| NUMU_CC | 27 | 16 | 6 | 5 | 99 ± 19 |
| NUE_CC | 165 | 52 | 78 | 35 | 607 ± 47 |
| NC_PI0 | 178 | 93 | 63 | 22 | 655 ± 49 |
| CC_PI0 | 101 | 42 | 41 | 18 | 371 ± 37 |
| OTHER_NC | 33 | 17 | 12 | 4 | 121 ± 21 |
| DIRT_NO_ACTIVE | 104 | 84 | 16 | 4 | 382 ± 38 |
| MULTI_ACTIVE | 41 | 14 | 20 | 7 | 151 ± 24 |

Policy `first`:

| category | final events | reco 0p | reco 1p | reco ≥2p | per 1e20 generated POT |
|---|---|---|---|---|---|
| NUMU_CC | 23 | 13 | 5 | 5 | 85 ± 18 |
| NUE_CC | 165 | 52 | 78 | 35 | 607 ± 47 |
| NC_PI0 | 178 | 93 | 63 | 22 | 655 ± 49 |
| CC_PI0 | 101 | 42 | 41 | 18 | 371 ± 37 |
| OTHER_NC | 33 | 17 | 12 | 4 | 121 ± 21 |
| DIRT_NO_ACTIVE | 103 | 84 | 16 | 3 | 379 ± 37 |
| MULTI_ACTIVE | 23 | 6 | 11 | 6 | 85 ± 18 |

The full per-stage truth cut-flow is `tables/baseline/bnb_cv_truth_cutflow.csv`; the selection is dominated by NC π⁰, intrinsic-ν_e CC, CC π⁰ and dirt/no-active-volume events. No signal purity is given (no signal sample).

## Outputs

`tables/baseline/bnb_cv_cutflow.{csv,json}`, `bnb_cv_truth_cutflow.csv`, `bnb_cv_final_composition.csv`; per-file candidate tables (derived data, outside the repo): `$SP_DATA/baseline_scan/bnb_cv/*.npz`. Reproduce: `python scripts/baseline_scan.py bnb_cv --workers 24 && python scripts/baseline_report.py bnb_cv` (~36 min with 28 workers).
