# Handoff: 5-slide NC-Delta -> N gamma update for the SBND Wire-Cell meeting (2026-11-19)

For a **separate presentation-building Claude**. Do not create anything except the 5 slides (and at most the 2 optional backups at the end). This document is self-contained: every number is verified against a repository table or report named in section 8. Written 2026-11-18 on the Fermilab EAF.

Audience: SBND Wire-Cell experts. Style: technical, minimal text, large numerical callouts, existing figures, explicit "diagnostic" labels, no neutrino introduction, no decorative graphics. Total talk about 5 minutes (about 60 s per slide). Plain text `NC-Delta -> N gamma`, `1gamma0p`, `1gamma1p / 1gammaNp` is fine if symbol rendering is unreliable.

## 0. The one thing the audience must get right

Three numbers, **three different things**. They are not three successive optimisations of one analysis.

| number | count | what it is | label to put on it |
|---|---|---|---|
| **9.28 %** | 1,153 / 12,427 | first-look, as run, with the **wrong reading of the inherited MicroBooNE TMVA score** (cuts applied to the raw TMVA response `v`; the real code cuts on `log10((1+v)/(1-v))`) | **HISTORICAL AS-RUN - not the authoritative baseline** |
| **6.70 %** | 833 / 12,427 | corrected, source-faithful Round-1 baseline on the **old reconstruction** (exact legacy XMLs; log10-odds score; `kine_pio_flag = 0` for the legacy ncpi0; cuts numu > 0.4, other > 0.2, ncpi0 > -0.05, nue > -1.0; same candidate policy, denominator, truth topology, 35 MeV post-FSI proton threshold) | **authoritative old-reconstruction baseline** |
| **15.60 %** | 1,938 / 12,427 | the **same corrected, frozen** selection replayed unchanged on Haiwang's `WCLocal2026Nov16` reconstruction (with Snehadri's improved vertexing) | **Nov16 DIAGNOSTIC - not a Round-2 result** |

- **9.28 -> 6.70 is an analysis/scorer correction. It is NOT a reconstruction loss.**
- **6.70 -> 15.60 is a reconstruction-domain change** under the *same* frozen selection. Nothing was retrained, retuned, threshold-scanned or optimised.
- 15.60 % is a **dedicated-signal efficiency**. It is **not** a purity and not an S/B. The generic-BNB selected background rises by a similar factor (slide 4).
- Wording to preserve (use it, nearly verbatim, in slide 1's notes):

> Our first-look number was 9.28 %, but a source audit showed that we had interpreted the inherited TMVA score incorrectly. The corrected old-reconstruction baseline is 6.70 %. Replaying that exact frozen selection on the Nov16 reconstruction raises the dedicated NC-Delta efficiency to 15.60 %.

**Never write or say:** "efficiency improved 9.28 % -> 15.60 %", "the new vertexer gives +6 points over 9 %", "Round-2 efficiency is 15.6 %", "the vertexer alone doubles the efficiency", "purity improved", "S/B". Never show 9.28 % without the HISTORICAL label.

Attribution caveat (say it once, on slide 3): the old-vs-Nov16 comparison is **vertex + other reconstruction changes**, not vertex-only. The toolkit commit, wire-cell-data bundle, DL-vertex bundle and flat-tree schema all differ, and the old vertex mode / DL model are not stated in the production documentation. Step 1 (imaging, clustering, matching) is reused and identical; the candidate set is unchanged.

---

## Slide 1 - The story in one picture

**Exact title:** `NC Delta -> N gamma: 9.3% -> 6.7% -> 15.6% - what changed?`

**Purpose:** explain the three efficiencies at a glance and pre-empt the misreading "9.3 % improved to 15.6 %".

**Key messages (max 3):**
1. 9.28 % -> 6.70 %: **score-convention correction** (analysis), not reconstruction.
2. 6.70 % -> 15.60 %: **same frozen selection**, Nov16 reconstruction.
3. Nov16 is a diagnostic, not final Round 2.

**Numbers to show (exact):** `1153 / 12427 = 9.28 %`, `833 / 12427 = 6.70 %`, `1938 / 12427 = 15.60 %`.

**Figure:** none exists; build one simple graphic: three large boxes left to right joined by arrows.
- Box 1 (grey, dashed border): `9.28 %` / "historical as-run (raw TMVA response)" / `1153 / 12427`.
- Arrow 1 label: **analysis / scorer correction** (not a reconstruction loss).
- Box 2 (blue = the old-reco colour of the replay figures, `#0072B2`): `6.70 %` / "source-faithful corrected baseline (old reconstruction)" / `833 / 12427`.
- Arrow 2 label: **reconstruction-domain change**, same frozen selection.
- Box 3 (vermillion `#D55E00`): `15.60 %` / "same frozen selection + Nov16 reconstruction" / `1938 / 12427`.
- Small footer annotation: `Nov16 diagnostic - not final Round 2`. Footer line: "dedicated NC-Delta radiative MC, truth denominator 12,427 (provisional TPC box)".

**Layout:** full-width three-box progression, big numerals (>= 60 pt), nothing else.

**Speaker notes (about 60 s):** "Three numbers have been circulating, and they are not three optimisation steps. Our first-look efficiency was 9.3 % [1153 of 12427]. A source audit of the MicroBooNE single-photon code showed that their cuts are applied to log10((1+v)/(1-v)) of the TMVA response, not to the response itself, and that the legacy ncpi0 scorer forces one input, kine_pio_flag, to zero. With that corrected, the authoritative old-reconstruction baseline is 6.7 % [833 of 12427]. That change is entirely our analysis, not a reconstruction effect. Then we replayed exactly that corrected, frozen selection, with no retraining and no tuning, on Haiwang's Nov16 production with Snehadri's improved vertexing, and the dedicated NC-Delta efficiency is 15.6 % [1938 of 12427]. This last one is a diagnostic, not the final Round-2 result."

**Caveats / do not say:** see section 0. Do not say "we improved from 9 % to 15.6 %".

**Transition:** "First, why the 9.28 became 6.70."

---

## Slide 2 - Why 9.28 % became 6.70 %

**Exact title:** `Source audit corrected the inherited MicroBooNE score convention`

**Purpose:** show briefly that 9.28 % is historical only, and that the correction made the baseline more source-faithful.

**Key messages (max 4):**
1. TMVA gives a response `v`; the MicroBooNE single-photon code cuts on `score = log10((1+v)/(1-v))`, not on `v`.
2. The frozen cuts (numu > 0.4, other > 0.2, ncpi0 > -0.05, nue > -1.0) are therefore materially different in response space (equivalents `v` > 0.4305, 0.2263, -0.0575, -0.8182); as run, the SP-nue cut was effectively vacuous and becomes a real rejection.
3. Corrected signal: **1,153 -> 833** events, **9.28 % -> 6.70 %**. The score convention explains almost all of it (alone: 831); the `kine_pio_flag = 0` correction alone is +8 events.
4. Generic BNB: as-run **649** selected; corrected **291** selected, **282** non-signal.

**Numbers to show (exact):**
- Decomposition of the signal selection (of 12,427): A as-run **1,153 (9.28 %)**; B score convention only **831 (6.69 %)**; C `kine_pio_flag` only **1,161 (9.34 %)**; D full source-faithful **833 (6.70 %)**.
- Equation: `score = log10((1+v)/(1-v))`, `v` = TMVA response.
- BNB: 649 -> 291 selected; non-signal 282; intrinsic-nueCC category among the selected non-signal events 175 -> 1.

**Figure:** `B01_scorer_correction.png` (4-bar decomposition A/B/C/D, exact counts and percentages printed on the bars). It lives on the pushed branch `analysis/ncdelta-corrected-presentation-20261117`, not in the working tree of this branch; see the asset table for the command to extract it. Alternative: a clean two-column comparison with the one equation.

**Layout:** left 60 % the bar figure; right 40 % a short "as run vs corrected" list with the equation on top. Keep it uncluttered.

**Speaker notes (about 60 s):** "TMVA returns a response v between -1 and 1. In MicroBooNE's code the single-photon BDT scores are stored as log10 of (1+v) over (1-v), and the frozen cuts of 0.4, 0.2, minus 0.05 and minus 1 are on that scale. Our first look had applied them to v directly. In response space that makes the real cuts v above 0.43, 0.23, minus 0.06 and minus 0.82, so numu and other are stricter than we ran, and the nue cut, which as run removed nothing, becomes a real rejection. The result: 1153 signal events become 833, 9.28 percent becomes 6.70. The score convention alone gives 831; forcing kine_pio_flag to zero for the legacy ncpi0 changes only eight events. In generic BNB the selected events drop from 649 to 291, and nearly all the intrinsic nue-CC background, 175 events, goes away. So the corrected baseline is cleaner and more faithful to the MicroBooNE implementation - not a worse reconstruction."

**Caveats / do not say:** do not imply the old reconstruction got physically worse. Do not claim the scorer was validated against stored MicroBooNE scores (none exist on EAF; the correction is a source-code audit). Do not discuss `kine_pio_flag` beyond one sentence (it applies to the **legacy** ncpi0 control only, not to any new SBND ncpi0 model).

**Transition:** "With the corrected selection frozen, here is what the Nov16 reconstruction does."

---

## Slide 3 - Nov16 reconstruction recovers much more signal

**Exact title:** `With the corrected selection frozen, Nov16 raises NC-Delta efficiency to 15.6%`

**Purpose:** show the effect of WCLocal2026Nov16 / Snehadri's improved vertexing on the frozen analysis.

**Key messages (max 4):**
1. **833 / 12427 = 6.70 % -> 1938 / 12427 = 15.60 %** (factor 2.33), same frozen selection, nothing retuned.
2. Gains in every truth topology; truth 0p is now the highest (18.27 %).
3. Vertex proximity improves a lot: median nearest reco-to-true vertex distance **18.9 cm -> 1.5 cm**; within 5 cm **33 % -> 65 %** of events (truth 1p 49 % -> 88 %; truth 0p 12 % -> 36 %).
4. The efficiency gain appears in the BDT stages, not in the reconstruction ceiling (candidates unchanged, >20 MeV shower ceiling slightly lower).

**Numbers to show (exact):**

| | all | truth 0p | truth 1p | truth >=2p |
|---|---|---|---|---|
| old corrected Round 1 | 6.70 % | 6.36 % | 7.49 % | 4.37 % |
| WCL1116 (Nov16) | 15.60 % | 18.27 % | 14.29 % | 7.25 % |

Counts: all 833 -> 1,938; 0p 373 -> 1,071 (of 5,863); 1p 416 -> 794 (of 5,557); >=2p 44 -> 73 (of 1,007). Binomial 68 % intervals: all 6.48-6.94 % -> 15.27-15.93 %. Optional descriptive line: Delta0 15.83 %, Delta+ 15.30 % (old 5.76 %, 7.87 %); **Delta charge is not reco or truth proton topology** - say it if you show it.

**Figures:** primary `fig_topology_efficiency_old_vs_nov16.png` with a large `6.70 % -> 15.60 %` callout; optional `fig_vertex_distance_old_vs_nov16.png`. If only one fits, use the topology figure. (`fig_cutflow_old_vs_nov16.png` is the natural backup.)

**Layout:** topology figure ~65 % width, big callout on the right ("x2.33", the two counts), vertex numbers as a small two-line box below the callout (or the vertex figure as a thin strip).

**Speaker notes (about 60 s):** "With nothing changed in the selection, the dedicated NC-Delta efficiency goes from 6.7 percent to 15.6 percent, a factor 2.3: 833 to 1938 events out of 12427. Every topology gains, and 0p, where the old vertex sat along the photon line, gains the most: 6.4 to 18.3 percent. The reconstruction clearly improved where it should: the median distance from the nearest candidate vertex to the true vertex goes from nineteen centimetres to one and a half, and the fraction within five centimetres doubles from a third to two thirds. But be careful with the cutflow: the number of events with a candidate is identical, the greater than 20 MeV shower ceiling is actually slightly lower, and the gain appears at the BDT stages, once the inherited classifiers see the new reconstruction. The events whose vertex moved closer are where the selection changes, but this production also differs in toolkit and DL bundle, so I am not attributing it to the vertexer alone."

**Caveats / do not say:** not "the vertexer alone doubles the efficiency"; not "Round-2 efficiency"; Nov16 is a diagnostic. State that this comparison is vertex **plus other** reconstruction changes. Do not show or compare against 9.28 % on this slide.

**Transition:** "That 15.6 % is not the whole story."

---

## Slide 4 - The catch: background rises too

**Exact title:** `The frozen legacy BDTs accept more signal - and more background`

**Purpose:** prevent 15.6 % from being read as an improved selection and motivate SBND-specific retraining.

**Key messages (max 3):**
1. Dedicated-signal efficiency x2.33, generic-BNB selected non-signal **x2.43**: the gain comes with a comparable background increase.
2. The jump appears only at the BDT stages: the inherited MicroBooNE-trained classifiers are evaluating a shifted feature domain (their SP scores shift; the BDT inputs change in a large fraction of matched candidates).
3. This motivates SBND-specific SP-BDT retraining rather than reusing inherited models/cuts.

**Numbers to show (exact):**
- Signal efficiency `6.70 % -> 15.60 %` (x2.33). Generic-BNB non-signal selected `282 -> 685` (x2.43).
- Reco topology (non-signal): **1gamma0p 150 -> 453 (x3.02)**; **1gamma1p 93 -> 178 (x1.91)**; **>=2p 39 -> 54 (x1.38)**.
- Truth categories (old -> Nov16): NC pi0 116 -> 316; outside-TPC nu 62 -> 196; CC pi0 60 -> 94; intrinsic nueCC 1 -> 12 (others: cosmic/unmatched 13 -> 25, other NC 13 -> 22, numuCC 14 -> 15, ambiguous 3 -> 5).
- Cumulative signal cutflow (old -> Nov16): candidate 11,331 -> 11,331; >20 MeV shower 8,080 -> 7,838; BDT evaluable 8,034 -> 7,758; **then** numu 4,943 -> 6,395; other 2,717 -> 4,290; ncpi0 1,305 -> 2,453; nue 893 -> 2,002; final 833 -> 1,938.
- Context line (same sample, same files): 1,938 is a dedicated-signal efficiency; do **not** convert to purity or S/B.

**Figures:** main `fig_bnb_background_old_vs_nov16.png`. Optional second (if the layout allows): `fig_sp_scores_old_vs_nov16.png` (the four frozen SP scores, identical binning, cuts dashed; axes clipped at +-3 - state this if shown). The cumulative cutflow can go in a small table or as `fig_cutflow_old_vs_nov16.png` in backup.

**Layout:** left the category bar figure; right a 3-row mini table for 1gamma0p / 1gamma1p / >=2p (old, Nov16, factor) with the two factors (x2.33 signal, x2.43 background) as large callouts at the top.

**Speaker notes (about 60 s):** "The same corrected selection that accepts 2.3 times more signal accepts 2.4 times more generic-BNB non-signal: 282 selected non-signal events become 685. The increase is largest in 1gamma0p, 150 to 453, and the categories that grow are NC pi0, from 116 to 316, outside-TPC neutrinos, from 62 to 196, and CC pi0; the intrinsic nue-CC category goes from 1 to 12. Look at the cutflow: the candidates and the shower ceiling are not better, the gain starts at the numu stage and continues through the other BDTs. The inherited MicroBooNE classifiers are seeing a shifted feature domain - the SP score distributions move, and their inputs change in many matched candidates. That is the argument for SBND-specific SP-BDT retraining. And to be clear, 15.6 percent is a dedicated-signal efficiency; I am not quoting a purity or S/B, which are not defined until the beam-off normalisation is settled."

**Caveats / do not say:** do not call 15.6 % a purity improvement; do not quote S/B or a significance; BNB numbers are statistical (Poisson) only, generic MC, no cosmic-only component. Do not predict what retraining will do. Do not attribute the background rise to a specific cause; outside-TPC and nue-sensitive categories may change again with the Nov23 boundary - no direction is predicted.

**Transition:** "So where does Round 2 go?"

---

## Slide 5 - Where Round 2 is going

**Exact title:** `Round 2: keep the reconstruction gain, retrain the classifiers in the SBND domain`

**Purpose:** current development status and the production/analysis plan.

**Key messages (max 3):**
1. SBND-trained SP-BDT development models beat the legacy models on the Aurora development holdout (numu, ncpi0, nue); SP-other is not yet trained.
2. The final reconstruction domain is not frozen: Haiwang's next production brings a new boundary and possibly a new upstream BDT (target ~Nov 23).
3. Our plan: freeze the domain, train, set thresholds on training/validation only, then an independent FermiGrid evaluation.

**Numbers to show (exact; development-holdout AUC, `split_move / snap`):**

| model | legacy | SBND dev |
|---|---|---|
| SP-numu | 0.958 / 0.954 | **0.976 / 0.974** |
| SP-ncpi0 | 0.849 / 0.847 | **0.899 / 0.897** |
| SP-nue | 0.918 / 0.914 | **0.959 / 0.952** |
| SP-other | - | **not trained**: blocked only on final beam-off provenance verification / transfer validation |

Mandatory footnote on the table: `Aurora DEVELOPMENT HOLDOUT - not independent end-to-end evaluation`. Mark the SBND dev models `DEV_DO_NOT_DEPLOY`. **These AUCs were supplied with the request from the Aurora development summary (`SP_BDT_WCL1116_FOUR_MODEL_DEVELOPMENT_SUMMARY.md`), which is not on EAF; they could not be verified against a source document here. Confirm them with Avinay before the meeting.**

**Roadmap (Haiwang's current plan, as communicated):** (1) implement/validate the non-box effective boundary; (2) no SCE back-correction for data or MC; (3) Xuyang's updated upstream BDT expected; (4) full production rerun, target ~Nov 23; (5) analyzers rerun data/MC comparisons. Source for items 1, 2: `HaiwangYu/wire-cell-toolkit-ai-helper/issues/50-sbnd-effective-boundary/plan.md` (it states no date and does not name Xuyang; the ~Nov 23 target and Xuyang's BDT come from the collaboration context given to us).
**Our analysis path:** freeze final reconstruction domain -> freeze upstream numu chain -> train final SBND SP BDTs -> set thresholds using training/validation only -> export / equivalence checks -> only then independent FermiGrid evaluation.

**Figure:** a simple four-step arrow: `better vertexing` -> `final boundary / upstream chain` -> `SBND SP-BDT retraining` -> `independent final evaluation`, with the AUC table beside it. No existing figure; build it.

**Layout:** left AUC table (with footnote), right four-step arrow; bottom one-line takeaway in bold.

**One-line takeaway (end the talk on it):** **Nov16 shows that SBND reconstruction can recover much more NC-Delta signal; the next job is to recover that efficiency without the comparable background increase.**

**Speaker notes (about 60 s):** "On the Aurora development holdout, SBND-trained SP BDTs already beat the legacy ones on the same Nov16 reconstruction: for example numu 0.958 to 0.976, ncpi0 0.849 to 0.899, nue 0.918 to 0.959. These are development-holdout numbers, not an independent evaluation, and SP-other is not yet trained - it is waiting on the final beam-off provenance verification. The reconstruction domain is also not final: Haiwang's next production, targeted around the 23rd, is expected to bring the measured effective boundary, no SCE back-correction, and possibly Xuyang's updated upstream BDT. So the plan is to freeze that domain, train the final SBND SP BDTs, set thresholds on training and validation only, and only then evaluate independently on FermiGrid. The takeaway: Nov16 shows the reconstruction can recover much more NC-Delta signal; the next job is to recover that efficiency without the comparable background increase."

**Caveats / do not say:** do not imply SP-other is trained; do not present the AUCs as the final performance; do not quote a Round-2 efficiency; do not claim any retraining result beyond development AUC. Nov16 results must **not** be used to tune Nov23 choices.

---

## 6. Optional backup material (at most two slides, not part of the 5)

1. **Detailed old-vs-Nov16 cumulative cutflow:** `fig_cutflow_old_vs_nov16.png` plus the table in section 5 of the replay report (including policy `first`: 795 old; Nov16 value in `signal_topology_efficiency.csv`).
2. **SP-score migration / BDT development matrix:** `fig_sp_scores_old_vs_nov16.png` plus `signal_score_migration.csv` (median shifts: numu +0.29, other +0.09, ncpi0 +0.03, nue +0.04 in score units for matched candidates) and the AUC table from slide 5 with its development-holdout label.

## 7. Facts for Q&A (all verified, see section 8)

- Signal selection migration (matched events): pass->pass 628; **pass->fail 205**; **fail->pass 1,310**. So 205 events that passed before do not pass now.
- Candidate formation is unchanged: 11,331 events with a candidate in both; 12,409 candidates in both.
- Photon taxonomy (events with a candidate): signal photon's shower in a passing candidate 47.9 % -> 59.2 %; fragmented 4.3 -> 2.3 %; photon-as-track 3.7 -> 1.8 %; outside main-vertex set 5.0 -> 3.8 %; **worse:** shower typed non-electron 8.5 -> 15.0 %, particle row missing 1.4 -> 2.3 %.
- Association (not causation): events whose vertex moved >1 cm closer are 2.0 % -> 17.8 % selected; unchanged-vertex events 15.5 % -> 17.9 %.
- nueCC dedicated sample: selected 381 -> 680 (of about 100k usable events). Beam-off 4 -> 6 (of 49,968; counts only, not normalised); open data 26 -> 81 (old open-data production is older and different); Run-3 BNB 96 of 109,485.
- Rates (Round-1 definitions, statistical only; not S/B): selected signal rate per 1e20 POT 29.3 -> 68.3; selected non-signal BNB 1,037 -> 2,519 per 1e20 POT; generic-BNB truth signal fraction 9/291 = 3.09 % -> 19/704 = 2.70 % (a truth fraction, not a purity). **Purity / S/B are not defined in Round 1 and are not computed.**
- The alternate vertex tree (`dv2_snap`) was not read; no vertex mode was chosen or compared in this replay.

## 8. Asset inventory (exact paths)

Paths are relative to `/home/abhat/Single-photon/sbnd-wirecell-single-photon`. **Status of git:** the replay branch `analysis/wcl1116-nov16-frozen-r1-replay-20261118` (commit `eceefe2`) is committed locally and **not pushed**; this handoff file itself is **uncommitted**; the files exist in that working tree. The scorer-correction assets are on pushed branches.

| slide | recommended asset | exact path | use |
|---|---|---|---|
| 1 | none (build the 3-box graphic) | - | central graphic; numbers from section 0 |
| 2 | scorer-correction decomposition bar chart | `presentation_assets/ncdelta_source_faithful/backup/B01_scorer_correction.png` on branch `analysis/ncdelta-corrected-presentation-20261117` (pushed; **not** in this working tree). Extract: `git show origin/analysis/ncdelta-corrected-presentation-20261117:presentation_assets/ncdelta_source_faithful/backup/B01_scorer_correction.png > B01.png` | main figure of slide 2 |
| 2 | corrected cutflow / loss budget (optional) | `plots/legacy_scorer_correction/baseline_consolidation_source_faithful/fig_cutflow_loss_budget.png` (exists; in git on the scorer-correction branch and in this working tree) | optional alternative |
| 3 | topology efficiency old vs Nov16 | `plots/wcl1116_nov16_replay/fig_topology_efficiency_old_vs_nov16.png` | main figure |
| 3 | reco-vertex distance | `plots/wcl1116_nov16_replay/fig_vertex_distance_old_vs_nov16.png` | optional |
| 3 / backup | cumulative cutflow | `plots/wcl1116_nov16_replay/fig_cutflow_old_vs_nov16.png` | backup 1 |
| 4 | selected BNB non-signal by category | `plots/wcl1116_nov16_replay/fig_bnb_background_old_vs_nov16.png` | main figure |
| 4 / backup | four frozen SP scores | `plots/wcl1116_nov16_replay/fig_sp_scores_old_vs_nov16.png` | optional / backup 2 |
| 5 | none (build the AUC table + 4-step arrow) | - | numbers from slide 5 above |

Figures are produced with the repo's Okabe-Ito colours: old = blue `#0072B2`, Nov16 = vermillion `#D55E00`; keep that mapping in anything you add. Figures carry a small "DIAGNOSTIC" footer; leave it.

**Not found / not on EAF:** `SP_BDT_WCL1116_FOUR_MODEL_DEVELOPMENT_SUMMARY.md` (Aurora-side; the slide-5 AUCs are unverified here) and a machine-readable Round-2 production tracker. The roadmap on slide 5 relies on Haiwang's published plan and the context supplied with this request.

## 9. Source documents holding every headline number

| number(s) | document / table |
|---|---|
| 1,153 / 9.28 %, 831, 1,161, 833; BNB 649 / 291 / 282; nueCC 175 -> 1; the log10-odds convention; response-space cuts | `docs/analysis/LEGACY_SCORER_CORRECTION_IMPACT.md`; `tables/legacy_scorer_correction/impact_configurations.csv`; `docs/analysis/LEGACY_SINGLE_PHOTON_SCORER_SOURCE_AUDIT.md` |
| 833 / 12,427 = 6.70 %, 0p/1p/>=2p 6.36/7.49/4.37 %, 282 = 150/93/39 | `tables/legacy_scorer_correction/source_faithful/baseline_consolidation/summary.json`; `docs/presentation/NCDELTA_SOURCE_FAITHFUL_ROUND1_SLIDE_NUMBERS.md` (branch `analysis/ncdelta-corrected-presentation-20261117`) |
| 1,938 / 12,427 = 15.60 %, topology, cutflow, migration, vertex distances, taxonomy | `docs/analysis/WCL1116_NOV16_FROZEN_R1_SELECTION_REPLAY.md`; `tables/wcl1116_nov16_replay/{signal_topology_efficiency,signal_cutflow_old_vs_nov16,signal_vertex_distance,signal_migration_summary,signal_photon_taxonomy_old_vs_nov16}.csv` |
| BNB 282 -> 685, categories, 1g0p/1g1p/>=2p 150/93/39 -> 453/178/54 | `tables/wcl1116_nov16_replay/{bnb_selected_totals,bnb_category_old_vs_new,bnb_nonsignal_by_reco_channel}.csv` |
| rates per 1e20 POT, truth signal fraction | `tables/wcl1116_nov16_replay/signal_summary.json`, `bnb_selected_totals.csv`; replay report section 11 |
| SP-BDT development AUCs | supplied with this request; source `SP_BDT_WCL1116_FOUR_MODEL_DEVELOPMENT_SUMMARY.md` is Aurora-side and unverified here |
| Nov23 boundary plan | `HaiwangYu/wire-cell-toolkit-ai-helper/issues/50-sbnd-effective-boundary/plan.md` (public); Nov16 production: `.../issues/48-wclocal-2026nov16-productions` |
| Round-1 definitions (no purity / S/B) | `docs/analysis/ROUND2_EVALUATION_CONTRACT_SCORER_BASELINES.md` |

## 10. Verification log

Every number in sections 0-7 marked "exact" was checked on 2026-11-18 against the tables above (script-assisted for the replay numbers, which are generated into the report from the CSVs). The slide-5 AUCs are the only unverified numbers; they are marked as such where they appear.
