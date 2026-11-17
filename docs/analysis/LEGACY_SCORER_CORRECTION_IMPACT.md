# Legacy single-photon scorer correction: impact on the Round-1 NC-Delta baseline

Date: 2026-11-17. Branch `analysis/ncdelta-source-faithful-legacy-scorer-20261117`, base commit `4873c76fca8a112718326afe90e9f08186bb12da` (the presentation-prep branch, which contains the consolidated-baseline machinery of `4cffd9c`). **Nothing was trained.** No XML, no threshold (0.4 / 0.2 / -0.05 / -1.0), no candidate policy, no truth region (provisional TPC box, 12,427 events), no 35 MeV proton convention and no cut order was changed. Source evidence: `LEGACY_SINGLE_PHOTON_SCORER_SOURCE_AUDIT.md`. Machinery: `src/sbnd_single_photon/legacy_scorer.py` (modes `legacy_as_run`, `legacy_source_faithful`).

## 0. Verdict

**MATERIAL. The as-run Round-1 numbers are a HISTORICAL AS-RUN BASELINE; the source-faithful result is the authoritative corrected Round-1 baseline.** The old 9.28 % cannot be retained with a footnote: the corrected efficiency is **833 / 12,427 = 6.70 %** (68 % interval 6.48-6.94), i.e. **-320 events, -2.58 percentage points (-27.7 % relative)**, and the selected non-signal BNB-CV events fall from 635 to 282 (-353, -55.6 %).

Pre-stated materiality rule (fixed before looking at the decomposition, not chosen subjectively): a configuration is material if the change in the total efficiency exceeds the old 68 % statistical half-width (0.27 pp), or if the change in a headline selected count exceeds its Poisson sqrt(N). Results: efficiency change -2.58 pp = 9.7 half-widths; BNB-CV selected events 649 -> 291 = -358 against sqrt(649) = 25 (14 sigma); natural CV 13 -> 8. Both criteria are exceeded by a large factor.

The cause is the **score convention** (the `nue` cut, which was vacuous as run, becomes a real cut, and `numu` / `other` become slightly stricter); the `kine_pio_flag` override alone is negligible (+8 events).

## 1. The two differences (verified in source, see the audit)

1. Score: MicroBooNE cuts on `log10((1+v)/(1-v))` (`bdt.h:232-262`); the first look cut on the bare TMVA response `v`. In response space the frozen cuts are v > 0.4305 (numu), v > 0.2263 (other), v > -0.0575 (ncpi0), v > -0.8182 (nue): the as-run cuts were looser for numu / other, stricter for ncpi0, and **vacuous for nue** (`v > -1`).
2. `kine_pio_flag`: forced to 0 in the single-photon `ncpi0` input (`bdt_convert.cxx:3957-3958`, commit `47b1f0c`); the first look fed the real CAF value. Only the `ncpi0` BDT has this input.
No other input override or preprocessing was found; the single policy difference (non-finite inputs score NaN here, TMVA would still score them; 5 candidates in the official sample) is NOT corrected here and is labelled.

## 2. Impact scan, decomposition (Tasks 5-6)

Method: the existing derived candidate tables (official Gen2 signal, fg1 BNB CV, natural NC-Delta in the BNB CV) were re-scored with only the scorer convention changed; ROOT was read only for the one missing input, the 45 `ncpi0` inputs of the 3,924 BNB-CV events whose as-run chain reaches the `ncpi0` stage (every configuration is at least as strict as as-run at numu and other, so the corrected selected set is a subset of those; asserted for every configuration). The as-run configuration A reproduces the stored cut flags of both candidate tables exactly (asserted), and the rebuilt A products reproduce every committed Phase-5/19 table (`official_active_tpc`, `background_rate_model.json`, composition, natural comparison, SPINE-harmonised efficiencies) exactly.

| config | NC-Delta selected (any) | efficiency | selected (first) | BNB-CV selected events | of which signal-like | natural CV selected (of 117) | reco 1g0p | reco 1g1p | reco >=2p |
|---|---|---|---|---|---|---|---|---|---|
| A OLD (as run) | 1153 | 9.28 % | 1101 | 649 | 14 | 13 | 527 | 556 | 70 |
| B SCORE ONLY | 831 | 6.69 % | 793 | 286 | 9 | 8 | 406 | 378 | 47 |
| C PIO FLAG ONLY | 1161 | 9.34 % | 1109 | 656 | 14 | 13 | 531 | 560 | 70 |
| D FULL source-faithful | 833 | 6.7 % | 795 | 291 | 9 | 8 | 408 | 377 | 48 |

Decomposition: **score convention alone -322 events (831)**, kine_pio_flag alone **+8 (1,161)**, both -320 (833); the two do not add exactly (interplay +2). The flag is below the 0.27 pp materiality scale; the score convention is not. (BNB columns for B and C contain 3 and 10 selected events without a stored truth label, the 8 for D were labelled by running the unchanged Phase-4 `deep` stage on them: all 8 are background.)

Efficiency by group (selected / truth):

| group | A OLD | B SCORE ONLY | C PIO ONLY | D FULL | N truth |
|---|---|---|---|---|---|
| total | 1153 | 831 | 1161 | 833 | 12427 |
| 0p | 476 | 373 | 479 | 373 | 5863 |
| 1p | 594 | 415 | 599 | 416 | 5557 |
| >=2p | 83 | 43 | 83 | 44 | 1007 |
| Delta0 | 521 | 395 | 524 | 394 | 6846 |
| Delta+ | 632 | 436 | 637 | 439 | 5581 |

### Cumulative cutflow per configuration

Official signal (events surviving each cumulative stage; denominators 12,427):

| stage | A OLD | B SCORE ONLY | C PIO ONLY | D FULL |
|---|---|---|---|---|
| truth_denominator | 12427 | 12427 | 12427 | 12427 |
| wc_valid | 12426 | 12426 | 12426 | 12426 |
| candidate | 11331 | 11331 | 11331 | 11331 |
| n20mev | 8080 | 8080 | 8080 | 8080 |
| bdt_evaluable | 8034 | 8034 | 8034 | 8034 |
| numu | 5007 | 4943 | 5007 | 4943 |
| other | 2781 | 2717 | 2781 | 2717 |
| ncpi0 | 1313 | 1302 | 1319 | 1305 |
| nue | 1313 | 891 | 1319 | 893 |
| n20br1 | 1153 | 831 | 1161 | 833 |
| final | 1153 | 831 | 1161 | 833 |

fg1 BNB CV (events with any candidate reaching the stage; candidate and `n20mev` rows are inclusive of all candidates of all events):

| stage (events with any candidate reaching it) | A OLD | B SCORE ONLY | C PIO ONLY | D FULL |
|---|---|---|---|---|
| candidate | 237460 | 237460 | 237460 | 237460 |
| n20mev | 52663 | 52663 | 52663 | 52663 |
| numu | 11933 | 11718 | 11933 | 11718 |
| other | 3924 | 3756 | 3924 | 3756 |
| ncpi0 | 936 | 920 | 937 | 917 |
| nue | 936 | 348 | 937 | 354 |
| n20br1 | 649 | 286 | 656 | 291 |
| FINAL | 649 | 286 | 656 | 291 |

Natural NC-Delta in the BNB CV (117 events in the provisional TPC box):

| stage | A OLD | B SCORE ONLY | C PIO ONLY | D FULL |
|---|---|---|---|---|
| truth_denominator | 117 | 117 | 117 | 117 |
| wc_valid | 117 | 117 | 117 | 117 |
| candidate | 105 | 105 | 105 | 105 |
| n20mev | 70 | 70 | 70 | 70 |
| bdt_evaluable | 70 | 70 | 70 | 70 |
| numu | 47 | 46 | 47 | 46 |
| other | 31 | 31 | 31 | 31 |
| ncpi0 | 13 | 13 | 13 | 13 |
| nue | 13 | 8 | 13 | 8 |
| n20br1 | 13 | 8 | 13 | 8 |
| final | 13 | 8 | 13 | 8 |

First-failure (exclusive) of the corrected baseline, fractions of the 12,427: no candidate 8.8 %, no usable > 20 MeV shower 26.2 %, BDT not evaluable 0.4 %, numu 24.9 % (3,094), other 17.9 %, ncpi0 11.3 %, **nue 3.3 % (412)**, n_20br1 0.5 %, selected 6.7 % (as run: numu 24.4, other 17.9, ncpi0 11.8, nue 0, n_20br1 1.3, selected 9.3). The documented 3-event bookkeeping difference between exclusive first-failure and cumulative survival at numu / ncpi0 is unchanged (+3 / -3).

## 3. Event-by-event flips, policy `any` (Task 7; `tables/legacy_scorer_correction/event_flips.csv`, `flip_summary.csv`)

Full source-faithful (D) against as run (A):

| sample | old pass -> new fail | old fail -> new pass | unchanged pass | unchanged fail |
|---|---|---|---|---|
| official signal (12,427) | 335 | 15 | 818 | 11,259 |
| BNB CV (selected events) | 366 | 8 | 283 | (not enumerated) |

First stage whose decision changes (new first failure for pass -> fail, old first failure for fail -> pass): signal pass -> fail: **nue 312**, other 14, numu 5, ncpi0 4; signal fail -> pass: ncpi0 15 (kine_pio_flag and the -0.0575 threshold). BNB pass -> fail: nue 348, other 10, numu 7, ncpi0 1; fail -> pass: ncpi0 8.

Signal flips by truth class: pass -> fail 0p 109, 1p 185, >=2p 41; fail -> pass 0p 6, 1p 7, >=2p 2. By Delta charge (entangled with topology and proton origin, descriptive): pass -> fail Delta0 136, Delta+ 199; fail -> pass Delta0 9, Delta+ 6.

BNB (pass -> fail, 366 events) by candidate-associated category: **NUE_CC 174 (of the 175 selected as run)**, NC_PI0 78, CC_PI0 49, OUTSIDE_TPC_NU 35, NUMU_CC 10, OTHER_NC 7, SIGNAL_NCDELTA 5, MULTI_OR_AMBIGUOUS 4, COSMIC_OR_UNMATCHED 4; by reco channel 1g0p 164, 1g1p 143, >=2p 59. The `nue` cut removes essentially the whole intrinsic nue-CC background.

## 4. Corrected headline against the historical as-run baseline

| quantity | HISTORICAL AS-RUN | CORRECTED (source-faithful) |
|---|---|---|
| selected / truth, policy any | 1,153 / 12,427 = 9.28 % | **833 / 12,427 = 6.70 %** (6.48-6.94) |
| policy first | 1,101 = 8.86 % | 795 = 6.40 % |
| truth 0p / 1p / >=2p | 8.12 % / 10.69 % / 8.24 % | **6.36 % / 7.49 % / 4.37 %** |
| Delta0 / Delta+ (entangled) | 7.61 % / 11.32 % | 5.76 % / 7.87 % |
| final truth -> reco (0p row; 1p row; >=2p row) | 425/50/1; 93/471/30; 9/35/39 | **342/30/1; 61/336/19; 5/11/28** |
| reco 1g0p / 1g1p / >=2p totals | 527 / 556 / 70 | 408 / 377 / 48 |
| first failure: nue | 0 | **412 (3.3 %)** |
| selected non-signal BNB-CV (1g0p / 1g1p / >=2p) | 635 (310 / 230 / 95) | **282 (150 / 93 / 39)** |
| non-signal rate per 1e20 POT (stat. only) | 1,140 / 846 / 349 (total 2,335) | 552 / 342 / 143 (total 1,037) |
| signal rate per 1e20 POT (provisional TPC box) | 40.6 (18.6 / 19.6 / 2.5) | 29.3 (14.4 / 13.3 / 1.7) |
| natural NC-Delta in the CV (117 in box) | 13 (11.1 %), p = 0.52 | 8 (6.8 %), p = 0.85 |
| SPINE-harmonised denominator (8,668) | 947 = 10.93 % | 685 = 7.90 % |

These are rates and counts quoted independently, as before; their ratio is not an S/B, and no purity or significance is claimed. Source of the corrected values: `tables/legacy_scorer_correction/source_faithful/baseline_consolidation/summary.json` (the same `scripts/baseline_consolidation.py` run with `SP_TABLES_OVERLAY`). The as-run products under `tables/` are untouched.

## 5. What was rebuilt, and what was not (Task 9)

Rebuilt for the corrected scorer (outputs under `tables/legacy_scorer_correction/source_faithful/` and `plots/legacy_scorer_correction/`): official signal cutflow, overall / truth-class / Delta efficiency, first-failure accounting, final migration, expected signal rate; natural-CV rehearsal and its cutflow comparison; selected BNB-CV background (counts, composition by channel and category, rates); SPINE-harmonised efficiencies; the consolidated summary and the two consolidation figures; **differential efficiency** (`SP_LEGACY_CONFIG=D_full`, 49 figures); the Delta-mass response of the decay pairs (restricted recompute, below); the old-vs-corrected slide-number table (`docs/presentation/ROUND1_CORRECTED_SLIDE_NUMBERS.md`).

Not rebuilt, with reason: BDT-independent products (truth-only scans, candidate / shower-stage taxonomy, PID audits, vertex provenance, shower attachment, proton-truth association at the matched candidate) are unaffected because their populations are defined before the BDT stages; products that mix a selected-sample subset with text-only numbers (photon-energy response of the 1,148 selected photons, anchoring splits at `other`, the `ncpi0` pair-flag percentages, the matched-candidate -> final migration counts, the BNB variable shapes, the `any` minus `first` background counts, the FV / included == 3 decision-support efficiencies) keep their as-run values in the historical documents and are flagged REVIEW in the slide-number table; they were not regenerated because the full common-observable object scan and the Phase-12 attribution tables would have to be re-run, which exceeds an impact-and-rebuild pass.

Delta mass (restriction of the stored Phase-11 object table to objects still selected; as-run restriction reproduces 348 / +2.77 MeV / [-44.1, +33.7] MeV exactly): corrected **251 decay pairs, median -0.1 MeV, 68 % interval [-44.5, +23.4] MeV (half-width 34 vs 39 MeV), RMS 63 vs 65 MeV**. Events selected only under the corrected scorer (a few ncpi0 flips) have no stored object row and are not included.

## 6. Re-check of the earlier conclusions (Task 10)

| conclusion | classification | evidence |
|---|---|---|
| photon reconstruction taxonomy (candidate / shower stage, PID typing, fragmentation, attachment) | **UNCHANGED** | populations defined before numu: candidate 11,331, > 20 MeV shower 8,080 and BDT-evaluable 8,034 are identical; first failure 8.8 % / 26.2 % unchanged |
| numu compactness (compact objects rejected) | NUMERICALLY CHANGED, QUALITATIVELY SAME | survival 29.3 -> 28.3 % (length < 20 cm) vs 73.5 -> 72.8 %; < 5 segments 24.8 -> 24.0 % vs 73.1 -> 72.3 % (`mechanism_recheck.csv`); numu failures = 3,094 of the 11,594 lost = 26.7 % (as run: 26.9 % of 11,274; the Phase-18 29.8 % remains superseded) |
| other / vertex anchoring | NUMERICALLY CHANGED, QUALITATIVELY SAME | `other` survival given numu: truth 0p 47.3 -> 46.8 %, truth 1p 63.2 -> 62.7 %; the anchored-vs-unanchored splits were not recomputed (threshold shift 0.2 -> v 0.2263) |
| ncpi0 fake-pair interpretation | NUMERICALLY CHANGED, QUALITATIVELY SAME | survival given other 47.2 -> 48.0 %; flag effect +8 events; the pair-flag percentages were not recomputed |
| n_20br1 multiplicity | NUMERICALLY CHANGED, QUALITATIVELY SAME | first failure 1.3 -> 0.5 % (the nue cut removes many multi-shower candidates first); conditional survival 87.8 -> 93.3 % |
| **nue stage** | **QUALITATIVELY CHANGED** | vacuous as run (0 events) -> a real cut: 412 events (3.3 % of the truth denominator), survival given ncpi0 68 % (truth 0p 72 %, 1p 67.5 %, >=2p 52 %) |
| proton topology migration | NUMERICALLY CHANGED, QUALITATIVELY SAME | diagonal 0p 91.7 % (was 89.3 %), 1p 80.8 % (79.3 %), >=2p 63.6 % (47.0 %); truth 0p -> reco 1p 8.0 % (10.5 %), truth 1p -> reco 0p 14.7 % (15.7 %); the 0p / 1p conclusions stand, the proton-reconstruction mechanism numbers are text-sourced and unchanged |
| truth-class efficiency ordering | **QUALITATIVELY CHANGED (>=2p)** | 0p 6.36 %, 1p 7.49 %, >=2p 4.37 %: as run >=2p (8.24 %) was equal to 0p; corrected >=2p is the lowest (nue survival 52 %) |
| Delta mass | NUMERICALLY CHANGED, QUALITATIVELY SAME | unbiased, ~35 MeV half-width (restricted recompute, 251 pairs) |
| background composition | **QUALITATIVELY CHANGED** | nue CC 175 -> 1 (it was 17 % of 1g0p and 37 % of 1g1p); corrected 282: NC pi0 116 (41 %), outside-TPC 62 (22 %), CC pi0 60 (21 %), NUMU_CC 14, OTHER_NC 13, cosmic / unmatched 13, ambiguous 3; 1g1p is now NC pi0 49 %, CC pi0 26 % |
| differential efficiency | NUMERICALLY CHANGED, QUALITATIVELY SAME | rises with photon energy (1.8 % in the lowest populated bin to a 9 % maximum; as run 2.4 % to 15 %) and toward forward angles (2.8 -> 8.4 %); interior box 8.4 % vs 5.1 % outside (11.4 / 7.3 % as run); last 50 cm in z 3.4 % (4.4 %) |
| natural-CV consistency | UNCHANGED (consistent; counts changed) | 8 / 117 = 6.8 % vs 6.70 % official, p = 0.85 (as run 13 / 117 vs 9.28 %, p = 0.52) |

## 7. Limitations of this correction

- No stored single-photon score and no live TMVA exist on this machine (PyROOT is absent), so exact reproduction of MicroBooNE's production scores is NOT claimed; validity rests on the source reading, exact algebra, and bit-for-bit reproduction of the as-run scores from the stored inputs.
- The float32 widths of TMVA cuts / leaves and the non-finite-input policy (5 candidates) are documented in the audit and not applied.
- The BNB-CV `deep` truth association was run only for the 8 candidates newly selected under D; B and C configurations still have 3 and 10 unlabelled selected events (only D is authoritative).
- The corrected background has no cosmic-only component, no nue CC special-sample rate and statistical errors only, exactly like the as-run one.
- Text-sourced numbers that depend on the selected sample are listed for review, not regenerated (section 5).
