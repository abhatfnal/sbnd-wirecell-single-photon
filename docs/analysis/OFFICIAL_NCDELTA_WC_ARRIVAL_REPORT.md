# Official Gen2 NC Delta -> N gamma Wire-Cell production: arrival report and first high-statistics baseline

Date 2026-11-10. Branch `analysis/ncdelta-official-signal-baseline-20261110` (from the pushed readiness checkpoint `56043c5`). Everything below is MEASURED from
the production files, Haiwang's published lists and live SAM, unless marked *(reported)* or *(inferred)*. Frozen baseline only: `configs/baseline_selection.yaml`
(sha256 asserted by the provenance gate), candidate policy `any` (comparison `first`), proton threshold 35 MeV (**provisional**), truth region = parameter
(**not a fiducial volume**). Nothing was tuned, retrained or re-cut. "Efficiency" below always means *official Gen2 NC-Delta baseline efficiency for the stated truth
region and the provisional proton threshold*; it is **not** a final-analysis efficiency. Uncertainties are exact Clopper-Pearson 68.3 % intervals unless stated.

## 1. Production inventory

| item | value | status |
|---|---|---|
| catalogue entry | `ncdr`, MC NC Delta-radiative (all of the SAM sample), config `fg1`, FermiGrid prod #6 (issue HaiwangYu/sbnd-wirecell-production#6), date 2026-11-10, status `available` | *(reported)*, read from `docs/productions.js` |
| inputs | SAM `..._EX_ncdeltarad_v10_14_02_05_reco1_sbnd` (16,505 files) and `..._flat_caf_sbnd` (15,777 files) | **live SAM re-queried 2026-11-10: counts and file lists identical to our 2026-11-06 snapshot** |
| pairs | 15,776 = 9,150 OK + 6,626 EMPTY + 0 PARTIAL | list files: 15,776 rows; status file 9,150 OK / 6,626 EMPTY |
| reco1 without a pair | 729 listed (`pairs-mc-ncdr.skipped.tsv`) | 728 genuinely have no flatCAF; **1 is a bookkeeping miss, section 3** |
| merged CAFs | 9,150 non-empty files, 32.4 GB, `/pnfs/sbnd/persistent/users/yuhw/prod-fermigrid/ncdr/mc-ncdr/<id>/` | all 9,150 opened over XRootD, 0 read errors |
| events | 13,772 stored, **13,772 wc.valid == 1**, 0 wc.invalid | matches the website exactly |
| 6,626 EMPTY pairs | flatCAF files with no events -> no merged CAF by design | consistent: the truth census has 6,626 zero-event flatCAFs |
| README / lists | `ncdr/README.md`, `ncdr/lists/{pairs,pairs.skipped,status,events,merged-caf,...}` | read; sha256 and line counts in `tables/official_signal/production_record.json` |
| events per file | 1-7 (mean 1.5) | |

The registration tool was run on Haiwang's own `mc-ncdr.merged-caf.txt` (a plain list; no manifest was hand-made). Representative files (first, three middle,
last, smallest and largest event count) were inspected first: all consistent (recTree and recTreeWireCell aligned, run/subrun/event aligned, wc.valid present,
T_match/T_overlap/T_truth_{nu,pf,track} present, GenieEvtRecTree preserved) before the full scan.

## 2. Software provenance (gate: OPEN)

`configs/official_signal_provenance_gate.yaml`, 29 checks: **all REQUIRED pass; 1 EXPECTED not passing (`no_missing_events`, the single missing event of section 3); nothing UNKNOWN.**

| fact | measured in the files | website / README |
|---|---|---|
| schema md5 | `d4396a3490ea5aec4b02f0c34fa9db33` in all 9,150 files (1 distinct) = fg1 | `d4396a3490ea` |
| `recTreeWireCell` branches | 2,401 (24 top-level names = 20 trees + run/subrun/evt/valid) | 2,401 branches, 20 trees |
| SCN vertex weights (`Trun.dl_weights`) | `uboone/scn_vtx/t48k-m16-l5-lr5d-res0.5-CP24.pth`, 1 distinct | fg1 SCN |
| `Trun.wct_version` | `sbnd-dlvtx-35-pre-master-merge-2026-09-02-424-g78f81c64` (identical to the fg1 BNB CV files) | toolkit `sbnd-wc-flatcaf 4b6853d4` |
| BDT weights (`Trun.bdt_weights_dir`) | `uboone/weights` (frozen MicroBooNE-derived) | no alternative training |
| selection config | sha256 equals the frozen baseline | |
| larwirecell `ad5d942`, sbndcode `v10_14_02_03`, cfg `88cb05aa`, wire-cell-data `9e2f4b8` | **not recorded in the files** | *(reported)* by the README/catalogue |
| DV2-MAX / Fix2 / alternative BDT | **no field in the files** | *(inferred)* from "same configuration as fg1"; the declaration file says so explicitly |

Honest limit: the commits of larwirecell, sbndcode, cfg and wire-cell-data and the absence of DV2-MAX/Fix2 are the producer's declaration, not independently
verifiable from the files. The measured facts (identical schema, identical `wct_version` string, SCN weights, MicroBooNE BDT directory) are all consistent with fg1.
The three "declared_*" negatives are in `QUESTIONS_FOR_HAIWANG_HANYU.md` for an explicit confirmation.
`TotalPOT` per file matches the SAM unit `mc.pot` to 2.8e-6 (relative) for all 9,150 files; `TotalGenEvents` is 125 per file versus 12,500 generated events per unit in SAM
(the documented factor 100): generated events are taken from SAM, never from the CAF header, and are not used as an efficiency denominator.

## 3. 13,773 vs 13,772: resolution

**The missing event is run 317 / subrun 41 / event 6753**, the only truth event that is not in the production.

| | |
|---|---|
| flatCAF | `reco2-reco1-detsim-g4-filter-gen-2483-4161-1955-eda8_ncdeltarad.flat.caf.root` (SAM id 62721695, content status `good`, 1 event, adler32 `a799f26d`, 2,827,667 B, parent = the reco1 unit) |
| reco1 unit | `reco1-detsim-g4-filter-gen-2483-4161-1955-eda8_ncdeltarad.root` |
| signal | neutrino index 0, **Delta0 -> n gamma** (Delta charge 0), nu E 1.2345 GeV, photon 177.7 MeV, 1 true proton above 35 MeV -> **truth 1p**, 1 charged pion |
| vertex (cm) | (-56.9, 49.3, 40.1): inside the filter box **and** the provisional TPC box |
| unit | POT 1.80329e17, 12,500 generated events |

Hypotheses of the task: **A (SAM changed): rejected**, the live definitions are file-for-file identical to our saved snapshot (16,505 / 15,777). **D (different snapshot):
rejected**: 728 of Haiwang's 729 skipped reco1 files are exactly our 728 `no_flatcaf_child` units, and all 15,776 pair CAF paths are SAM locations in our snapshot.
**B (CAF removed): rejected**, the file is in SAM and on dCache now. **C (deliberate exclusion of a problematic pair): not supported**: nothing in the README, lists
or status files marks it as a problem, and the file is `good`. **E (other): this is it.** The skipped list gives the derived path
`.../ncdeltarad/caf/000011/000116/reco2-...2483-4161-1955-eda8...flat.caf.root` with reason `no CAF`; that directory does not exist. SAM registers this single CAF under an
anomalous layout, `.../ncdeltarad/000011/caf/subrun_011641/`, while the other 15,776 sit under `.../ncdeltarad/caf/<NNNNNN>/<NNNNNN>/`. The pair builder evidently derives the CAF path
from the reco1 directory pattern *(mechanism inferred; to be confirmed by the producer)* and so classified the unit as "no CAF" (the 729th). Therefore it was lost **before
Wire-Cell processing for a production-bookkeeping reason, not because the sample excludes it.**

**Decision (default principle, applied explicitly, not silently): the event stays in the denominator** (13,773 filter-box, 12,427 TPC-box; its unit POT stays in the
POT) and counts as a production inefficiency (`first_fail = missing_from_merged_caf`). It is not a validated-sample exclusion. Sensitivity if one instead removed the whole unit:
N = 13,772 / 12,426 and POT -6.4e-5 (relative); the TPC total efficiency moves from 1153/12427 = 9.278 % to 1153/12426 = 9.279 %, i.e. no physical effect. The master truth table
was **not modified**. A one-pair rerun by the producer would close this exactly (request in the questions file; not requested by us on dCache).

## 4. Event completeness

| expected (truth census) | incoming rows | represented | wc.valid | wc.invalid | missing | duplicate rows | unexpected rows | unit mismatch | schema mismatch |
|---|---|---|---|---|---|---|---|---|---|
| 13,773 | 13,772 | 13,772 | 13,772 | 0 | **1** | 0 | 0 | 0 | 0 files |

Accounting identities (`signal_pipeline.validate_accounting`) hold for both regions and both policies: rows = truth denominator; arrived + missing = denominator;
first-failure reasons partition the events; cumulative stage counts are non-increasing.

## 5. wc.valid

12,426 of 12,427 TPC-box and 13,772 of 13,773 filter-box truth events are wc.valid; the deficit is exactly the missing event (no wc.invalid event exists in this sample).

## 6. Frozen cutflow (TPC box, policy `any`; cumulative, all truth events in the denominator)

| stage | all | truth 0p | truth 1p | truth >=2p |
|---|---|---|---|---|
| truth denominator | 12,427 | 5,863 | 5,557 | 1,007 |
| wc.valid | 12,426 | 5,863 | 5,556 | 1,007 |
| >=1 candidate | 11,331 (91.2 %) | 5,210 | 5,170 | 951 |
| >20 MeV shower | 8,080 (65.0 %) | 3,956 | 3,468 | 656 |
| BDT evaluable | 8,034 (64.6 %) | 3,936 | 3,447 | 651 |
| numu BDT | 5,007 (40.3 %) | 2,446 | 2,174 | 387 |
| other BDT | 2,781 (22.4 %) | 1,157 | 1,373 | 251 |
| ncpi0 BDT | 1,313 (10.6 %) | 574 | 647 | 92 |
| nue BDT | 1,313 | 574 | 647 | 92 |
| n_20br1 | **1,153 (9.28 %)** | 476 | 594 | 83 |
| final `any` | 1,153 | 476 | 594 | 83 |
| final `first` | 1,101 | 453 | 566 | 82 |

Filter box (13,773): wc.valid 13,772; candidate 11,938; >20 MeV 8,452; BDT evaluable 8,400; numu 5,225; other 2,827; ncpi0 1,336; nue 1,336; n_20br1 / final `any` 1,172, `first` 1,120.
Signal-matched candidate diagnostic (candidate within 5 cm of the true vertex): TPC box 4,926 / 4,978 / 927 of truth 0p / 1p / >=2p (84.0 / 89.6 / 92.1 %); bounds in
`official_active_tpc/migration_any_B_*.csv`. Exact binomial intervals for every stage are in `official_*/cutflow_A_{any,first}.csv`. 25 of 9,150 files (27 signal events) needed a
tolerant reader for the `T_overlap` embedded-basket header (section 14), which only affects this matched-candidate diagnostic, never a cut.

## 7. Baseline efficiency (selected / N_signal_truth)

| region | policy | total | truth 0p | truth 1p | truth >=2p | Delta0 | Delta+ |
|---|---|---|---|---|---|---|---|
| **TPC box (provisional)** | any | **9.28 % [9.02, 9.55]** (1153/12427) | 8.12 % [7.76, 8.49] | 10.69 % [10.27, 11.12] | 8.24 % [7.37, 9.20] | 7.61 % [7.29, 7.94] | 11.32 % [10.90, 11.76] |
| | first | 8.86 % [8.60, 9.12] (1101) | 7.73 % [7.38, 8.09] | 10.19 % [9.78, 10.61] | 8.14 % [7.27, 9.10] | 7.25 % [6.93, 7.57] | 10.84 % [10.42, 11.27] |
| **filter box** | any | **8.51 % [8.27, 8.75]** (1172/13773) | 7.45 % [7.12, 7.79] | 9.79 % [9.41, 10.18] | 7.64 % [6.84, 8.53] | 7.00 % [6.71, 7.31] | 10.37 % [9.98, 10.77] |
| | first | 8.13 % [7.90, 8.37] (1120) | 7.09 % [6.77, 7.42] | 9.33 % [8.96, 9.72] | 7.55 % [6.76, 8.43] | 6.67 % [6.38, 6.97] | 9.93 % [9.55, 10.32] |

`any` vs `first`: `any` selects 52 (TPC) / 52 (filter) more events (+4.7 % / +4.6 % relative), the known candidate-policy systematic (`first` is the comparison policy only). The filter-box
efficiency is lower, consistent with truth vertices outside the TPC box less often giving an analysable candidate (not separately studied).

## 8. Truth -> reco proton migration (TPC box, policy `any`)

Final selection against the **full** truth denominator (counts; row fractions in %; uncertainties: binomial, e.g. 425/5863 = 7.25 [7.0, 7.5] %):

| | reco 1g0p | reco 1g1p | reco >=2p | not selected / unreconstructed / missing | N truth |
|---|---|---|---|---|---|
| truth 0p | 425 (7.25) | 50 (0.85) | 1 (0.02) | 5,387 (91.88) | 5,863 |
| truth 1p | 93 (1.67) | 471 (8.48) | 30 (0.54) | 4,963 (89.31) | 5,557 |
| truth >=2p | 9 (0.89) | 35 (3.48) | 39 (3.87) | 924 (91.76) | 1,007 |

Conditional on final selection (rows normalised to the selected events): truth 0p -> 89.3 / 10.5 / 0.2 %; truth 1p -> 15.7 / 79.3 / 5.1 %; truth >=2p -> 10.8 / 42.2 / 47.0 %.
The three earlier checkpoints (all denominator events, signal-matched candidate, BDT-evaluable matched candidate), raw and row-normalised with exact errors, for both
policies and both regions: `tables/official_signal/official_baseline/<region>/migration_{any,first}_{A,B,C,D}_*.csv`. For example, all denominator events, reco category of the signal-matched candidate:
truth 0p -> 65.4 / 16.0 / 2.6 / 16.0 (no matched candidate), truth 1p -> 31.3 / 47.6 / 10.7 / 10.4. **This high-statistics matrix replaces the 117-event rehearsal as the primary migration measurement.**

## 9. Expected signal and yields per 1e20 POT (MC expectation, not a data measurement)

Signal sample POT 2.83853154e21 (SAM `mc.pot` of the 15,777 flatCAF units; includes the missing unit). Migration-aware yield N(r) = P * sum_t R_t * eps(t -> r); multinomial covariance; stat only.

| | TPC box (provisional) | filter box |
|---|---|---|
| signal rate before reconstruction | 437.8 / 1e20 POT (0p 206.6, 1p 195.8, >=2p 35.5) | 485.2 (0p 229.0, 1p 217.0, >=2p 39.2) |
| selected, reco 1g0p | **18.57 +- 0.78** | 19.06 +- 0.80 |
| selected, reco 1g1p | **19.59 +- 0.80** | 19.76 +- 0.81 |
| selected, reco >=2p | 2.47 +- 0.29 | 2.47 +- 0.29 |
| selected, total | 40.62 +- 1.14 | 41.29 +- 1.15 |

These use the NC Delta -> N gamma cross-section and flux of the generator exactly as simulated (no reweighting, no systematic uncertainty).

## 10. Signal and beam-neutrino background rates (per 1e20 POT) -- quoted independently, NOT an analysis S/B

**Signal** (official NC Delta, truth vertex in the provisional TPC box, policy `any`, MC expectation): reco 1g0p **18.57 +- 0.78**; reco 1g1p **19.59 +- 0.80** (section 9).

**Beam-neutrino background** B_BNB_NEUTRINO, read from `tables/official_signal/background_rate_model.json` (validated Phase-4 non-signal BNB CV events, 635 selected, POT 2.7194e19; natural
NC-Delta signal-like events excluded): reco 1g0p **~1140 +- 65** (310 events); reco 1g1p **~846 +- 56** (230 events); reco >=2p ~349 +- 36 (95 events). Statistical only.

**Why these are not combined into an S/B or purity.** The signal is restricted to events whose *truth* vertex lies in the provisional TPC box, whereas B is *all* selected non-signal BNB CV events with
no corresponding analysis-volume (FV / reconstructed-vertex) requirement. The two populations therefore do **not** share a phase-space convention, and the cosmic-only background is absent
(beam-off normalisation unresolved). A ratio of the two numbers is a scale comparison only. The headline S/B and purity are therefore **suppressed**.

Reference table (diagnostic only):

| reco channel | S | B (beam neutrino) | raw signal/background rate ratio **before a common FV convention** |
|---|---|---|---|
| 1g0p | 18.57 +- 0.78 | 1140 +- 65 | 0.0163 +- 0.0012 |
| 1g1p | 19.59 +- 0.80 | 846 +- 56 | 0.0232 +- 0.0018 |

**This is NOT the analysis S/B and not a purity.** The final S/B requires **both** (i) a common signal/background analysis volume (the same FV / reconstructed-vertex requirement applied to S and B) **and**
(ii) the cosmic normalisation. **COSMIC NORMALIZATION: UNRESOLVED. Total purity, total S/B and significance are not quoted;** the prediction object continues to refuse `total_background`, `purity`,
`s_over_b` and `significance` (re-verified in `official_baseline/summary.json`, all four refused). No systematic uncertainty is included.

## 11. Natural-CV rehearsal comparison (TPC box)

| quantity | rehearsal | official | p (exact binomial of the rehearsal count given the official rate) |
|---|---|---|---|
| overall final `any` | 13/117 = 11.1 % | 1153/12427 = 9.28 % | 0.52 (Fisher 0.52) |
| truth 0p | 4/59 | 476/5863 | 1.0 |
| truth 1p | 8/46 | 594/5557 | 0.15 |
| truth >=2p | 1/12 | 83/1007 | 1.0 |
| Delta0 fraction | 65/117 | 6846/12427 | 1.0 |
| truth-class mix (0p/1p/>=2p) | 59/46/12 | 5863/5557/1007 | 0.43 (chi-square goodness of fit) |
| every cumulative stage (11 stages) | | | min p = 0.25 (n20mev); candidate 0.52, numu 1.0, ncpi0 0.77 |
| selected truth -> reco | 0p: 4/4 reco 0p; 1p: 6 reco 1p, 2 reco 0p; >=2p: 1 reco 0p | 89 / 79 / 11 % diagonal | 13 events: descriptive only |

The rehearsal is statistically consistent with the official sample in every quantity tested; no discrepancy was found and nothing was tuned. The rehearsal was Phase-3's 117 natural
events; with 13 selected events its relative uncertainty is ~28 %, so it can only exclude gross inconsistencies.

## 12. First high-statistics physics diagnostics (descriptive only, TPC box, policy `any`; no optimisation)

1. **Truth-1p efficiency is higher than truth-0p: yes.** 10.69 % [10.27, 11.12] vs 8.12 % [7.76, 8.49], difference +2.57 +- 0.56 pp (chi-square p = 2.9e-6). Delta+ (11.3 %) > Delta0 (7.6 %).
   It comes from the candidate stage (93.0 vs 88.9 %), the `other` BDT (63.2 vs 47.3 % survival) and n_20br1 (91.8 vs 82.9 %), partly offset by the 20 MeV shower requirement (67.1 vs 75.9 %).
2. **Cross-migration.** Signal-matched candidate: truth 0p -> reco 1p 19.1 % (940/4,926), truth 1p -> reco 0p 34.9 % (1,739/4,978). Final selection: truth 0p -> reco 1p 10.5 % (50/476),
   truth 1p -> reco 0p 15.7 % (93/594). Against the full denominator 16.0 % and 31.3 %. The reco proton count is a weak proxy for the true proton count; the migration matrix must be used, not a diagonal.
3. **Selected reco 1g1p (556) is dominated by truth 1p and Delta+**: truth 1p 471 (84.7 %), 0p 50 (9.0 %), >=2p 35 (6.3 %); Delta+ 424 (76.3 %), Delta0 132 (23.7 %).
4. **Selected reco 1g0p (527)**: truth 0p 425 (80.6 %), 1p 93 (17.6 %), >=2p 9 (1.7 %), i.e. 19.4 % are not truth 0p; Delta0 368 (69.8 %), Delta+ 159 (30.2 %). Only 336 (63.8 %) are truth 0p *and* Delta0.
5. **Largest signal-removing cut (first failure, order dependent)**: all 3,251 (26.2 %) no >20 MeV shower, then numu 3,030 (24.4 %), other 2,226, ncpi0 1,465, no candidate 1,095, n_20br1 160.
   Truth 0p: numu 1,490 (25.4 %) > other 1,289 (22.0 %) > 20 MeV 1,254 (21.4 %). Truth 1p: 20 MeV 1,702 (30.6 %) > numu 1,276 > ncpi0 723. Delta0: numu 1,740 (25.4 %) > 20 MeV 1,607 (23.5 %);
   Delta+: 20 MeV 1,644 (29.5 %) > numu 1,290 (23.1 %).
6. **20 MeV shower**: the largest *early* loss and the largest overall first-failure for truth 1p, >=2p and Delta+ (conditional survival 71.3 % of candidates overall). For truth 0p / Delta0 it is second to the numu BDT.
7. **Does the numu BDT disproportionately reject truth 0p? No.** Conditional survival 62.1 % [61.4, 62.9] (0p), 63.1 % [62.2, 63.9] (1p), 59.4 % (>=2p). The class-dependent rejection is in the `other` BDT (0p 47.3 % vs 1p 63.2 %)
   and n_20br1 (0p 82.9 % vs 1p 91.8 %). Conditional survival tables: `official_baseline/active_tpc/conditional_survival_any.csv`.

## 13. Unresolved analysis conventions

Fiducial volume (the TPC box is a provisional truth region); proton threshold 35 MeV and reco/true proton definitions; candidate policy `any` vs `first` (+4.7 %); the treatment of the missing production
event (kept); cosmic and beam-off normalisation (blocks any total purity / S/B / significance); a common signal/background analysis volume (also required for any S/B); the NC Delta -> N gamma cross-section and flux systematic uncertainties and the flux-weighted
statement of the S/B; whether the pi0/nueCC-like backgrounds of the BNB CV should be vertex-restricted like the signal. See `QUESTIONS_FOR_HAIWANG_HANYU.md`.

## 14. Exact limitations

* Statistical errors only; no systematic uncertainty of any kind. No S/B or purity is quoted: signal and background do not yet share an analysis volume, and there is no cosmic component.
* DV2-MAX / Fix2 / alternative-BDT negatives and the larwirecell/sbndcode/cfg/wire-cell-data commits are the producer's declaration.
* The missing-event mechanism (path derivation) is inferred from the lists and SAM locations, not confirmed by the producer.
* 25 of 9,150 merged CAFs (27 signal events) have `wc.T_overlap.*` branches with an 8-byte trailing mismatch in the embedded-basket header that stock uproot refuses (`expected 1245 bytes but cursor moved by 1237`). A scoped fallback
  (`caf.tolerant_embedded_basket_read`) skips only that byte-count check; recovered values were checked against the run/event numbers stored in the same tree and the matched-candidate diagnostic then has no missing file.
  It never touches a cut input (cuts use `recTreeWireCell` tagger/kine branches, which read normally in all 9,150 files).
* The signal-matched candidate (5 cm vertex tolerance) is a diagnostic; the final selection is not truth-based.
* TPC-box numbers are provisional; the filter-box numbers describe the generator filter region, not an analysis volume.
* The yield uses the generator cross-section and flux as simulated and the SAM POT of the 15,777 flatCAF units.

Reproduce: `source env/setup_eaf.sh; python scripts/register_official_ncdelta_wc.py --file-list <ncdr>/lists/mc-ncdr.merged-caf.txt --provenance <declaration.yaml>`;
`python scripts/build_official_signal_analysis_table.py`; `python scripts/run_official_signal_baseline.py official --skip-register --skip-build --region {active_tpc,filter_box} --exposure-pot 1e20`;
`python scripts/analyze_official_signal_baseline.py`. Auto-generated per-region reports (template fill): `tables/official_signal/official_{active_tpc,filter_box}/ARRIVAL_REPORT.md`.
