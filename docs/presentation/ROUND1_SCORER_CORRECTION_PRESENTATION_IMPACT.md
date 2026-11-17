# Presentation impact of the legacy-scorer correction (urgent)

Date: 2026-11-17. For: the first-look deck being prepared / presented by Avinay. **The PPTX is NOT touched by this package.** Basis: `docs/analysis/LEGACY_SCORER_CORRECTION_IMPACT.md` (verdict: MATERIAL), `docs/presentation/ROUND1_CORRECTED_SLIDE_NUMBERS.md` (every JSON-sourced number, old vs corrected, with the 55 text-sourced numbers flagged REVIEW).

**One-sentence message to carry until the deck is updated:** the Round-1 selection was run with the inherited cuts applied on the wrong score scale (and with the real `kine_pio_flag`); with the MicroBooNE convention (cuts on `log10((1+v)/(1-v))`, flag forced to 0) the official NC-Delta efficiency is **6.70 %, not 9.28 %**, the selected beam-neutrino background halves, and the intrinsic nue-CC component disappears; the as-run numbers are kept only as a HISTORICAL AS-RUN BASELINE.

Corrected headline numbers to use (all from `tables/legacy_scorer_correction/source_faithful/baseline_consolidation/summary.json`): efficiency 833 / 12,427 = **6.70 %** (68 % interval 6.48-6.94; policy first 795 = 6.40 %); truth 0p / 1p / >=2p **6.36 / 7.49 / 4.37 %**; Delta0 / Delta+ 5.76 / 7.87 % (entangled, backup only); first failures: candidate 8.8, shower 26.2, numu 24.9, other 17.9, ncpi0 11.3, **nue 3.3**, n_20br1 0.5 %; final migration truth 0p 342 / 30 / 1, truth 1p 61 / 336 / 19, truth >=2p 5 / 11 / 28 (reco totals 408 / 377 / 48); selected non-signal BNB-CV **282** (150 / 93 / 39), rates 552 / 342 / 143 per 1e20 POT (stat. only); signal rate **29.3** per 1e20 POT (14.4 / 13.3 / 1.7); natural CV **8 / 117** (6.8 %, p = 0.85); SPINE-harmonised **685 / 8,668 = 7.90 %**.

Legend: **no change** | **number** (text numbers only) | **plot** (figure must be regenerated or replaced) | **wording** | **removal**.

## Main slides

| # | current title | needs | what to change |
|---|---|---|---|
| 1 | NC Δ→Nγ in SBND: a frozen Wire-Cell first look | wording | add to the definition box: "inherited chain with the MicroBooNE score convention (log-odds), kine_pio_flag = 0; an earlier as-run scorer is a historical diagnostic". No numbers |
| 2 | The frozen baseline selects 9.3 % of official NC-Δ signal | **number + plot + title** | title -> "... selects 6.7 % ..."; 833 / 12,427; interval 6.5-6.9 %; truth classes 6.4 / 7.5 / 4.4 %; replace `02_cutflow` (redraw from the corrected `loss_budget.csv`; the corrected consolidation figure is `plots/legacy_scorer_correction/baseline_consolidation_source_faithful/fig_cutflow_loss_budget.png`); the `nue` stage is no longer "vacuous" |
| 3 | Most of the loss comes from photon reconstruction and the inherited BDT stages | number + plot | title still holds (candidate + shower 35 %; numu + other + ncpi0 + nue 57.4 %); new first-failure percentages above, **add nue 3.3 %**, numu failures 26.7 % of the total loss (3,094 of 11,594; the old 26.9 % / 29.8 % are retired); replace `03_loss_budget` |
| 4 | The photon is often mis-typed, fragmented, or owned by a hadron-typed object | **no change** | populations defined before the BDT stages (11,331 candidate-stage events, 8,080 with a > 20 MeV shower, identical); all taxonomy percentages unchanged |
| 5 | The inherited BDTs respond strongly to reconstruction state | number (+ plot caveat) | numu survival 29 % vs 74 % -> **28 % vs 73 %** (length < 20 cm vs above), 25 % vs 73 % -> 24 % vs 72 % (< 5 vs >= 5 segments); the figure was drawn with the as-run cut (shift about 1 pp): footnote or redraw; the `other` anchoring split (65-79 % vs 33-46 %) and the ncpi0 pair-flag percentages were NOT recomputed: say "as run, ~1 pp-scale shifts expected" or drop the numbers; the "survival given other" by topology is 0p 46.8 % vs 1p 62.7 % |
| 6 | The truth-0p vertex follows the photon; a reconstructed proton anchors the interaction | number (REVIEW) | the median vertex distances 0.93 cm vs 11.6 cm and the anchoring 42 -> 67.5 % are defined on the as-run final-selected / DL-stage samples and were not recomputed; keep with the footnote "as-run selected sample; mechanism is BDT-independent (vertex placed before the final refinement)" |
| 7 | 0p/1p migration is dominated by proton reconstruction, not the 35 MeV threshold | number | proton typing efficiencies (46 / 67 / 22 %) and the matched-candidate counts (883, 468 / 319) are BDT-independent and stand; the "-> final" counts (37, 11 / 26) are as-run and become 61 (truth 1p -> reco 0p) and 30 (truth 0p -> reco 1p) in the corrected final selection |
| 8 | Final truth→reco topology: 425 / 471 / 39 on the diagonal | **number + plot + title** | title -> "**342 / 336 / 28** on the diagonal"; diagonal fractions 91.7 / 80.8 / 63.6 %; redraw the matrix from `migration_final` of the corrected summary |
| 9 | Once the right objects are reconstructed, the Delta observables work | number + plot | decay pairs **251** (not 348): median **-0.1 MeV**, 68 % [**-44.5, +23.4**] MeV (restricted recompute, `delta_mass_subset.csv`); photon-energy response 1.034 +/- 12.7 % (1,148 selected photons) was not recomputed: footnote "as-run sample"; replace the residual plot or footnote it |
| 10 | The two exclusive channels have different surviving backgrounds | **number + plot + wording** | composition changes completely: 282 events (150 / 93 / 39); **nue CC 175 -> 1**; 1g0p: NC pi0 37 %, outside-TPC 35 %, CC pi0 13 %; 1g1p: NC pi0 49 %, CC pi0 26 %, outside-TPC 10 %; redraw (`10b`) from the corrected composition CSV; the "nue CC 37 % of 1g1p" bullet must go |
| 11 | Signal and beam-neutrino background scale: this is NOT an S/B | **number + plot** | signal 29.3 per 1e20 (14.4 / 13.3 / 1.7); non-signal 552 / 342 / 143 per 1e20 (total 1,037); replace `11_rates` with the corrected consolidation figure; the caveat (not an S/B, no beam-off normalisation, no cosmic-only component) is unchanged |
| 12 | Established, open, blocked: and what comes next | wording | add to "established": the scorer-convention and `kine_pio_flag` source audit and the corrected baseline; remove "nue vacuous"; efficiency 6.7 %; add "Round-1 as-run kept as a diagnostic; Round-2 compares to the source-faithful scorer"; blockers (G, H, J) and open decisions (D, E, F) are unchanged |

## Optional slides

| # | title | needs | what to change |
|---|---|---|---|
| O1 | Efficiency is strongly kinematic and position dependent | number + plot | rebuilt: `plots/legacy_scorer_correction/differential_efficiency_source_faithful/` (49 figures); energy 1.8 % -> 9 % maximum (as run 2.4 % -> 15 %), cos(theta) 2.8 -> 8.4 %, last 50 cm in z 3.4 %, interior 8.4 % vs outside 5.1 %; the qualitative statement stands |
| O2 | The natural NC-Δ in the BNB CV agrees within low statistics | number + plot | 8 / 117 = 6.8 % vs 6.70 %, p = 0.85 (was 13 / 117, p = 0.52); regenerate `14_natural_cv` |
| O3 | SPINE: truth side harmonised, reco comparison not yet possible | number + plot | 685 / 8,668 = 7.90 % (0p50 7.18 %, Np50 8.79 %) on the harmonised denominator; still a denominator-definition effect, not a Wire-Cell-vs-SPINE comparison |

## Backup slides

| # | topic | needs | what to change |
|---|---|---|---|
| B01 | production provenance and official sample | no change | |
| B02 | complete cutflow table | **number + plot** | corrected `loss_budget.csv`; 3-event numu / ncpi0 bookkeeping difference unchanged (+3 / -3) |
| B03 | `first` vs `any` | number | 795 vs 833 (as run 1,101 vs 1,153); the "52 real signal events / 22 background events" were not recomputed (REVIEW) |
| B04 | FV decision support | number (REVIEW) | efficiencies 9.28 / 10.1-10.6 / 9.92 % are as-run; not recomputed; the decision remains open: mark "as run" or drop the numbers |
| B05 | 35 vs 50 MeV and `included == 3` | number (REVIEW) | truth-only counts (1,072) unchanged; reco-dependent ones (63 events; 84.7 -> 89.7 %) are as-run and were not recomputed |
| B06 | conversion-distance definition | no change | truth / reco-geometry only (11,512 events; Spearman 0.975) |
| B07 | photon reconstruction taxonomy | **no change** | BDT-independent |
| B08 | numu compactness and attribution | wording | SHAP / attribution figures are properties of the frozen XML and unchanged; survival numbers shift by about 1 pp |
| B09 | ncpi0 pair origin | number (REVIEW) | 94.2 % / 88.0 % are as-run (rejected-event set changes slightly with kine_pio_flag = 0); not recomputed |
| B10 | shower attachment (567 events) | no change | BDT-independent |
| B11 | proton origin and Delta charge | number (REVIEW) | the pp differences are as-run; the Delta0 / Delta+ efficiencies are 5.76 / 7.87 % (entangled) |
| B12 | proton PID failure modes | no change | BDT-independent |
| B13 | natural-CV cutflow | number + plot | corrected `natural_cv_cutflow.csv` (8 / 117 final) |
| B14 | SPINE harmonisation requirements | number | 9,206 of 13,773 (truth FV) unchanged; WC efficiency values on the harmonised sets updated (`wc_efficiency_on_harmonized.csv`) |
| B15 | analysis roadmap and blockers | wording | add the scorer correction as completed; G, H, J unchanged |

## New backup slide recommended

"Scorer-convention audit": the table of the four cuts in score and response space, the decomposition (A OLD 1,153 / B SCORE ONLY 831 / C PIO FLAG ONLY 1,161 / D FULL 833), and the flip summary (nue removes 312 signal and 348 BNB events). Sources: `tables/legacy_scorer_correction/{impact_configurations,threshold_translation,flip_summary}.csv`.

## Removal / retire list

Retire everywhere: 9.28 %, 8.12 / 10.69 / 8.24 %, 7.61 / 11.32 %, 425 / 471 / 39, 635 and 310 / 230 / 95, 1,140 / 846 / 349, 40.6 per 1e20, "nue vacuous", "nue CC 17 % / 37 %", 13 / 117 (as the corrected value). The as-run values may only be shown labelled "historical as-run (scorer-convention diagnostic)".
