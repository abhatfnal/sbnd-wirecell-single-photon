# NC Delta -> N gamma, frozen Wire-Cell first look: presentation outline

Prepared for Avinay (2026-11-11). **No PPTX yet.** Audience: SBND collaborators, Haiwang / Hanyu, Seokju, Nate, Wire-Cell and reconstruction analysts. Register: **first-look baseline, not a final analysis result.**

How to use this file: every slide below gives the central message, the asset (ready in `presentation_assets/ncdelta_baseline/`, original in `plots/`), the headline numbers, 2-4 slide bullets, a callout, a 30-60 s speaker note and the caveat that must stay visible on the slide. **Every number on a slide must be a row of `NCDELTA_BASELINE_SLIDE_NUMBERS.md`** (generated from `tables/baseline_consolidation/summary.json` and the consolidated baseline text; the Phase-19 value wins over any earlier phase report). Asset roles, crops and provenance: `NCDELTA_BASELINE_SLIDE_ASSETS.csv`.

**Wording rules for every slide**
* Always write **truth 0p / 1p / >= 2p** (generator topology) and **reco 1g0p / 1g1p / >= 2p** (Wire-Cell channel) in full; never "0p" alone where it could mean either.
* The three conventions (candidate policy `any`, provisional TPC truth box, 35 MeV truth proton threshold) are **characterisation conventions, not approved analysis definitions**; there is no analysis FV.
* Numbers are **baseline** efficiencies of the frozen chain against a truth-region denominator; no optimisation has been done and none is claimed.
* Never show 29.8 % (the superseded Phase-18 share); the corrected number is **numu failures = 26.9 % of the total baseline loss** (11,274 events lost).
* No S/B, no purity, no significance, no Wire-Cell-vs-SPINE statement, no domain-shift claim.
* Delta0 / Delta+ efficiencies (7.61 % / 11.32 %) are not a clean charge effect (charge, proton origin and topology are entangled); show them only in backup, with that sentence.

Common footer for every main slide (suggested text): *official Gen2 NC-Delta | frozen production fg1 Wire-Cell + inherited single-photon BDT chain | policy any, provisional TPC box, 35 MeV | first-look baseline*.

---

## MAIN DECK (12 slides, full technical talk ~15-20 min)

### Slide 1 | NC Delta -> N gamma in SBND: a frozen Wire-Cell first look
* **Central message:** we ran the unmodified production reconstruction and the inherited MicroBooNE-derived single-photon chain on the official NC-Delta signal, and characterised it; nothing has been optimised or retrained.
* **Plot:** none (text + definition box). **Path:** n/a.
* **Headline numbers:** official Gen2 `EX_ncdeltarad`: 13,773 generated events, **12,427** in the provisional TPC box; thresholds numu > 0.4, other > 0.2, ncpi0 > -0.05 (frozen).
* **Bullets:**
  * Exclusive reco 1g0p and 1g1p single-photon final states from NC Delta -> N gamma.
  * Sample: official Gen2 signal; reconstruction: production fg1-compatible Wire-Cell, stored as produced.
  * Selection: inherited frozen BDT chain (candidate, > 20 MeV shower, numu, other, ncpi0, nue, n_20br1); no retraining, no optimisation, no DV2-MAX, no Fix2.
  * Question: how well does it do out of the box, where does it lose signal and why?
* **Callout (definition box, visible):** candidate policy `any` | truth region = provisional TPC box | 35 MeV truth proton threshold | no analysis FV. **CHARACTERISATION CONVENTIONS, NOT APPROVED ANALYSIS DEFINITIONS.**
* **Speaker note (45 s):** "This is a first-look baseline of the exclusive NC Delta radiative search in SBND. We did not change anything: it is the production Wire-Cell reconstruction and the single-photon BDT chain inherited from MicroBooNE, run on the official Gen2 signal. To measure efficiency we need a denominator, so we use the provisional TPC box of the generator truth, a 35 MeV proton threshold for truth topology and, because events can carry several candidates, an event-level 'any' policy. These are conventions to make numbers possible; none is an approved analysis definition, and I will flag the open decisions at the end. The goal today is to explain what the baseline does and why, so we can decide the next step."
* **Caveat to keep visible:** the definition box with the "not approved" label.

### Slide 2 | The frozen baseline selects 9.3 % of official NC-Delta signal
* **Central message:** out of the box, 1,153 of 12,427 truth events are selected.
* **Plot:** `presentation_assets/ncdelta_baseline/02_cutflow.png` (original `plots/baseline_consolidation/fig_cutflow_loss_budget.png`, left panel redrawn).
* **Headline numbers:** **1,153 / 12,427 = 9.28 %** (68 % interval 9.02-9.55); policy `first` 1,101 = 8.86 %; truth 0p 8.12 %, truth 1p 10.69 %, truth >= 2p 8.24 %.
* **Bullets:**
  * Efficiency 9.28 % with policy `any` (8.86 % with `first`; `any` adds 52 real signal events).
  * By truth topology: 0p 8.12 %, 1p 10.69 %, >= 2p 8.24 %.
  * Cumulative: 11,331 candidates -> 8,080 with a > 20 MeV shower -> 5,007 after numu -> 2,781 after other -> 1,313 after ncpi0 -> 1,153.
* **Callout:** big "9.28 %" next to the final bar; small table for the three truth classes.
* **Speaker note (45 s):** "The answer to 'what does the frozen selection do out of the box' is 9.3 percent of the official signal in the TPC box: 1,153 of 12,427 events. With the stricter first-candidate policy it is 8.9 percent. Truth topology matters: events with one true proton above 35 MeV are selected more often than events with none, 10.7 against 8.1 percent. The bars show the cumulative survival through the chain; by far the biggest drops are the shower stage, numu and other, which is the subject of the next slides."
* **Caveat to keep visible:** "truth region = provisional TPC box; policy any; baseline, not optimised".

### Slide 3 | Most of the loss comes from photon reconstruction and the inherited BDT stages
* **Central message:** where the 12,427 go; the dominant losses are reconstruction-state and classifier effects, not a photon-energy threshold.
* **Plot:** `presentation_assets/ncdelta_baseline/03_loss_budget.png` (right panel of the same figure, redrawn).
* **Headline numbers (first failures, % of 12,427):** candidate **8.8**, > 20 MeV shower **26.2**, numu **24.4**, other **17.9**, ncpi0 **11.8**, n_20br1 **1.3**, nue 0, selected 9.3. numu failures are **26.9 %** of the total loss (11,274 lost).
* **Bullets:**
  * No usable photon shower (26.2 %) and numu (24.4 %) are the two largest losses; other (17.9 %) and ncpi0 (11.8 %) follow.
  * Only 1.2 % of the shower-stage failures are genuinely below 20 MeV.
  * Each stage mostly reflects how the photon or vertex was reconstructed, not the photon energy.
* **Callout:** annotate the two largest bars "reconstruction of the photon" and the three BDT bars "inherited classifiers".
* **Speaker note (45 s):** "Here is the exclusive accounting of where each truth event first fails; the fractions add up to 100 percent. A quarter of all events have no usable photon shower, a quarter fail numu, 18 percent fail other and 12 percent fail ncpi0. In terms of the total loss, the numu stage is 26.9 percent. The key message is the next three slides: these are not mostly low-energy photons falling below a threshold; only about one percent of the shower failures are really below 20 MeV. They are reconstruction states, which the inherited classifiers then amplify."
* **Caveat to keep visible:** fractions are of the 12,427 truth events (exclusive); 26.9 % is the share of the total loss, not of the truth denominator.

### Slide 4 | The photon is often mis-typed, fragmented, or owned by a hadron-typed object
* **Central message:** the shower-stage loss is typing, fragmentation and ownership, not the 20 MeV threshold.
* **Plot:** `presentation_assets/ncdelta_baseline/04_photon_taxonomy.png` (original `plots/shower_vertex_audit/taxonomy_all_0p_1p.png`). Optional second panel: `05_numu_compactness.png` (fragmented / compact objects).
* **Headline numbers:** **27.6 %** of signal photons have a track-typed dominant object; fragmented photons have a median of **3** pieces; **567** events contain a good energetic electron shower outside the main-vertex shower set (17.4 % of the shower-stage failures); typed muon / pion / proton is 29.6 % of those failures.
* **Bullets:**
  * 27.6 % of signal photons are track-typed (muon, pion or proton-like); typing is a pattern-recognition decision on the start segment.
  * Fragmentation: the photon is split over a median of 3 pieces, often across clusters of the same candidate.
  * 567 events: a good electron shower (median 212 MeV) hangs below a hadron-typed object about 20 cm away and is not counted in the main-vertex shower set.
* **Callout:** point to the orange 'shower not in main vertex set', pink 'shower typed non-electron' and brown 'fragmented' bands; note on the figure that its bars are fractions of the 11,331 events with a candidate (not of 12,427).
* **Speaker note (60 s):** "Looking at the signal photon itself: among the shower-stage failures the largest classes are photons whose start segment was typed as a muon, pion or proton, fragmented photons, and showers owned by another object. 27.6 percent of signal photons have a track-typed dominant object. The 567-event class is striking: a good electron shower, 212 MeV on average, correctly reconstructed, but attached through an indirect connection to a hadron-typed object across the conversion gap, so the tagger never sees it. None of this is a 20 MeV threshold problem. The causes of the cluster split and of the typing are reconstruction-side; the producer-side PID inputs are not stored, so we can describe but not fully diagnose them."
* **Caveat to keep visible:** denominator of the plot is the events with a candidate; the causes are association, not proven causation.

### Slide 5 | The inherited BDTs respond strongly to reconstruction state
* **Central message:** we understand why the frozen chain rejects these events; we cannot say it is a MicroBooNE-to-SBND domain shift.
* **Plot:** `presentation_assets/ncdelta_baseline/05_numu_compactness.png` (original `plots/numu_compact_shower_audit/fig1_survival_vs_segments_length.png`); optional second panel `05b_other_vertex_class_survival.png`.
* **Headline numbers:** numu survival **29 %** for total shower length < 20 cm vs **74 %** above (25 % vs 73 % for < 5 vs >= 5 segments); clean electron shower 76 %, fragmented 36 %, muon-/pion-typed 22-25 %; other: anchored vertex 65-79 % vs not anchored 33-46 %; ncpi0: 94.2 % of the rejected events carry a pair flag, 88.0 % a pair containing the signal photon.
* **Bullets:**
  * **numu** rejects compact, few-segment photon objects: 29 % survive under 20 cm of shower vs 74 % above; clean showers 76 %, fragments 36 %.
  * **other** follows vertex anchoring: 65-79 % survive with an anchored vertex, 33-46 % without.
  * **ncpi0** rejects single photons for which the reconstruction forms a shower pair that need not be a pi0.
  * Training domain: no training sample, class labels or input distributions are available, so a quantitative MicroBooNE-to-SBND test is impossible.
* **Callout:** on the figure, mark the < 20 cm and < 5 segment bins; add a text box "association remains after control: 25-32 pp".
* **Speaker note (60 s):** "The three inherited classifiers respond to the reconstruction state of the photon and vertex. numu keeps extended showers and rejects compact few-segment objects: under 20 cm of shower survival is 29 percent, above that 74 percent. About 44 percent of that difference is shared with the photon's reconstruction class, and a 25 to 32 point association remains after controlling for class, anchoring, topology, energy and angle. other follows whether the vertex is anchored. ncpi0 rejects single photons because the reconstruction builds a shower pair, without any true pi0. Whether this is intended behaviour of the MicroBooNE training is not something we can say: the model file and the MicroBooNE tree contain no training sample, class labels or distributions. So we explain why the chain rejects these events, but we do not claim a domain shift."
* **Caveat to keep visible:** "No quantitative domain-shift claim possible: training distributions / class definitions unavailable."

### Slide 6 | The truth-0p vertex follows the photon; a reconstructed proton anchors the interaction
* **Central message:** the 0p / 1p difference in the vertex is established before the final refinement.
* **Plot:** `presentation_assets/ncdelta_baseline/06_vertex_provenance.png` (original `plots/vertex_provenance_audit/fig2_vertex_provenance_by_topology.png`).
* **Headline numbers:** |V_reco - V_true| median **0.93 cm** (truth 1p) vs **11.6 cm** (truth 0p); truth-0p photon-line displacement **+25.8 cm** (traditional vertex), **+36 cm** (raw network), **+24.5 cm** (DL stage); the final refinement moves the vertex by a median **0.25 cm**; the DL stage anchors the vertex 42 % -> 67.5 % when a true proton is reco-typed.
* **Bullets:**
  * With a reconstructed proton the interaction vertex is anchored (truth 1p: 0.93 cm from truth); in truth-0p events the vertex sits along the photon (11.6 cm).
  * The displacement is already present in the traditional and deep-learning vertex choices (+25.8 cm, +24.5 cm along the photon).
  * Late refinement is negligible (median 0.25 cm): the 0p/1p vertex difference is not introduced by it.
* **Callout:** orange (DL displaced along the photon, final stays there) dominates truth 0p; green (anchored) is large once a proton exists.
* **Speaker note (60 s):** "This slide explains why truth-0p and truth-1p events behave differently downstream. For truth-1p events the vertex lands within a centimetre of the true interaction point, because a reconstructed proton anchors it. For truth-0p events there is no proton, and the vertex is placed along the photon line, about 25 cm from the interaction. We tracked where this happens: it is already in the traditional vertex and in the raw network output, it persists at the DL stage, and the late refinement moves the vertex by only a quarter of a centimetre. So the vertexing choice, not the final refinement, sets the 0p/1p difference, and it feeds directly into the other-stage survival. Why the vertexing prefers the photon in the 0p case is still open."
* **Caveat to keep visible:** "truth 0p / 1p; association; why the vertexing places the vertex along the photon is open."

### Slide 7 | 0p/1p migration is dominated by proton reconstruction, not the 35 MeV threshold
* **Central message:** protons are often not typed as protons; the threshold is a minor cause.
* **Plot:** `presentation_assets/ncdelta_baseline/07_proton_reco_vs_ke.png` (original `plots/particle_pid_audit/fig2_true_proton_reco_type_vs_ke.png`); second panel `07b_migration_reasons.png` (original `plots/proton_truth_association/migration_1p_to_0p_and_0p_to_1p.png`).
* **Headline numbers:** proton typing **46 %** above 35 MeV, **67 %** at 200-300 MeV, **22 %** above 500 MeV; 17 % of protons above 35 MeV have a row typed muon / pion / electron-shower; truth 1p -> reco 0p: **883 -> 37** events with a non-proton-typed matched row (matched candidate -> final selected); truth 0p -> reco 1p: **468 -> 11** photon typed as proton, 319 -> 26 Geant4 secondary protons.
* **Bullets:**
  * Truth 1p -> reco 0p: the proton is mis-typed, merged into another object or has no row; the KE threshold is a minor (5-10 %) cause.
  * Low-KE protons merge into other objects; high-KE protons become muon / pion typed (22 % proton-typed above 500 MeV).
  * Truth 0p -> reco 1p: mostly the photon typed as a proton and neutron-induced secondary protons.
* **Callout:** blue (proton-typed) bar: 67 % at 200-300 MeV, 22 % above 500 MeV; left panel of 07b: "non-proton type" is the largest slice.
* **Speaker note (60 s):** "Topology migration is a proton reconstruction story. Typing efficiency for true signal protons peaks at 67 percent for 200 to 300 MeV and collapses to 22 percent above 500 MeV, where muon and pion typing take over. Low-energy protons are merged into the photon or a neighbouring object. When a truth-1p event ends up as reco 0p, the proton was mis-typed, merged or had no row; falling below the 35 MeV reco threshold is only 5 to 10 percent of the cases. In the opposite direction, a truth-0p event becomes reco 1p mainly because the photon itself is typed as a proton, or because a neutron-induced secondary proton appears. The dQ/dx template scores that would let us dig deeper are not stored."
* **Caveat to keep visible:** truth vs reco labels spelled out; "35 MeV is a provisional convention (decision open)".

### Slide 8 | Final truth -> reco topology: 425 / 471 / 39 on the diagonal
* **Central message:** the clean final migration matrix of the selected events.
* **Plot:** `presentation_assets/ncdelta_baseline/08_migration_matrix.png` (drawn from `tables/baseline_consolidation/summary.json`; the Phase-10 plot shows migration reasons, not the matrix).
* **Headline numbers:** truth 0p -> reco 0p / 1p / >= 2p **425 / 50 / 1**; truth 1p **93 / 471 / 30**; truth >= 2p **9 / 35 / 39**; reco totals **1g0p 527, 1g1p 556, >= 2p 70**; selected 476 / 594 / 83.
* **Bullets:**
  * Most selected events land in the matching reco channel (425 + 471 + 39).
  * Off-diagonal: 93 truth-1p events are reco 1g0p; 50 truth-0p events are reco 1g1p.
  * Reco 1g0p = 527, 1g1p = 556, >= 2p = 70: the reco channels are not the truth classes.
* **Callout:** label rows "truth (generator, 35 MeV)" and columns "reco (Wire-Cell channel)".
* **Speaker note (45 s):** "For the 1,153 selected events this is the truth-to-reco topology matrix. The diagonal carries 425, 471 and 39 events. The off-diagonal terms are the mechanisms from the last slide: 93 truth-1p events are reco 1g0p, 50 truth-0p events are reco 1g1p. The reco channel totals, 527, 556 and 70, are what an analysis would call 1g0p and 1g1p; they are not the same populations as the truth classes, so any prediction in a reco channel has to use the full migration."
* **Caveat to keep visible:** "35 MeV, existing `included` convention (policy decision open)".

### Slide 9 | Once the right objects are reconstructed, the Delta observables work
* **Central message:** for truth-matched decay pairs the reconstructed Delta mass and photon energy are promising.
* **Plot:** `presentation_assets/ncdelta_baseline/09_delta_mass_residual.png` (left panel of `plots/common_observables/delta_mass_resolution.png`).
* **Headline numbers:** 348 truth-matched Delta+ decay pairs: **M_reco - M_true median +2.8 MeV, 68 % interval [-44, +34] MeV**; photon E_reco / E_true **1.034**, **12.7 %** half-width (1,148 truth-correct selected photons); the width is set by the photon energy (10.4 %) and opening angle, not the proton KE (3 %).
* **Bullets:**
  * Delta mass for truth-matched decay pairs: median +2.8 MeV, 68 % [-44, +34] MeV.
  * Photon energy response: 1.034 +/- 12.7 %.
  * The width comes from the photon energy and the photon-proton opening angle, not from the proton KE.
* **Callout:** "truth-matched Delta+ decay pairs only; wrong-pair tails excluded from the resolution".
* **Speaker note (45 s):** "When the reconstructed photon and proton are the true decay pair, the reconstructed Delta mass is centred within 3 MeV of the true decay mass, with a 68 percent interval of minus 44 to plus 34 MeV. The photon energy is reconstructed to 1.03 with a 12.7 percent half-width. Replacing individual ingredients by truth shows the width is set by the photon energy and the opening angle, not the proton energy. The headline excludes the policy-dependent wrong-pair tails, which are a reconstruction-and-policy issue, not a resolution. The message: the physics observables are promising once the objects are right."
* **Caveat to keep visible:** "348 truth-matched Delta+ decay pairs; not the full selected sample; Delta0 events have a neutron decay nucleon, so the reco proton cannot be the decay nucleon".

### Slide 10 | The two exclusive channels have different surviving backgrounds
* **Central message:** reco 1g0p and 1g1p are populated by different neutrino backgrounds.
* **Plot:** `presentation_assets/ncdelta_baseline/10b_backgrounds_clean_redraw.png` (recommended; the unedited copy `10_backgrounds.png` of `plots/background_mechanisms/background_composition_by_channel.png` has legends over the bars; crop it to the 1g0p and 1g1p panels if used).
* **Headline numbers:** **635** selected non-signal BNB-CV events: reco **1g0p 310, 1g1p 230, >= 2p 95**; 1g0p: NC pi0 ~33 %, outside-TPC neutrinos ~24 %, nue CC ~17 %; 1g1p: nue CC ~37 %, NC pi0 ~30 %, CC pi0 ~18 %.
* **Bullets:**
  * 635 selected non-signal BNB-CV events: 310 reco 1g0p, 230 reco 1g1p, 95 >= 2p.
  * 1g0p: NC pi0 ~33 %, outside-TPC neutrinos ~24 %, nue CC ~17 %.
  * 1g1p: nue CC ~37 % (the electron is the selected shower in all of them), NC pi0 ~30 %, CC pi0 ~18 %.
* **Callout:** "BNB CV, candidate-associated truth; no cosmic-only component; no nueCC special sample".
* **Speaker note (45 s):** "Of the 649 events the baseline selects in the beam CV, 14 are natural signal-like and 635 are backgrounds. They split 310, 230 and 95 across reco 1g0p, 1g1p and 2-plus protons. The channels differ: in 1g0p NC pi0 dominates, then neutrinos interacting outside the TPC and electron-neutrino CC; in 1g1p electron-neutrino CC is the largest, where the primary electron is the selected shower, then NC and CC pi0. So a single background model will not do; the two exclusive channels need their own."
* **Caveat to keep visible:** "no cosmic-only (beam-off) component; no nueCC special-sample rate; statistical counts".

### Slide 11 | Signal and beam-neutrino background scale: this is NOT an S/B
* **Central message:** the two rates are quoted independently because no common volume and no beam-off normalisation exist.
* **Plot:** `presentation_assets/ncdelta_baseline/11_rates.png` (original `plots/baseline_consolidation/fig_signal_vs_background_rates.png`).
* **Headline numbers:** signal **40.6** per 1e20 POT (total; 18.57 / 19.59 / 2.47 for reco 1g0p / 1g1p / >= 2p); beam-neutrino background **1,140 / 846 / 349** per 1e20 POT (reco 1g0p / 1g1p / >= 2p); statistical errors only.
* **Bullets:**
  * Signal rate (provisional TPC box, policy `any`): 40.6 per 1e20 POT.
  * Selected beam-neutrino background: 1,140 / 846 / 349 per 1e20 POT in reco 1g0p / 1g1p / >= 2p.
  * **THIS IS NOT S/B:** the signal uses a truth-box denominator, the background has no common volume, and the cosmic-only beam-off normalisation is unresolved.
* **Callout (large, red):** "NOT S/B - no purity, no significance".
* **Speaker note (45 s):** "These are the two rates we can quote today, independently. The signal rate is the selected number per 1e20 POT in the provisional TPC box; the background is the selected beam-neutrino rate in the generated volume. They look as if one could divide them, and we deliberately do not: the volumes differ, the cosmic-only beam-off component is not normalised, and the nueCC special sample is not included. Until a common analysis volume and the beam-off normalisation exist, the framework refuses to produce a purity, an S over B or a significance."
* **Caveat to keep visible:** "NOT S/B; no common volume; no beam-off normalisation".

### Slide 12 | Established, open, blocked: and what comes next
* **Central message:** the take-home table.
* **Plot:** none (build a four-column status table from `NCDELTA_FROZEN_WIRECELL_BASELINE.md` sections 14, 15, 17).
* **Headline numbers:** DONE A B C O P Q T U V Y; largely done M N S X Z; open decisions D E F; blocked G H (J external SPINE); queued I; waiting for SPINE J K W; deferred L.
* **Content (table):**
  * **ESTABLISHED:** official signal baseline (9.28 %); cutflow and loss mechanisms; differential efficiency; truth-reco migration; photon, proton and vertex reconstruction; common Delta observables; BNB-CV background mechanisms; SPINE truth-definition harmonisation.
  * **OPEN ANALYSIS DECISIONS:** fiducial volume; proton threshold (35 vs 50 MeV) and `included == 3` rows; candidate policy.
  * **EXTERNAL:** beam-off normalisation; flash-time reference; same-event SPINE output and exact SPINE efficiency definition.
  * **NEXT:** decisions -> common-volume data/MC validation -> same-event Wire-Cell vs SPINE -> dedicated NC-Delta optimisation / retraining (only after the above).
* **Callout:** "no option is preferred for its efficiency; decision support exists".
* **Speaker note (60 s):** "To sum up: we have an established baseline of 9.3 percent, an exclusive loss budget, and explanations for the main losses in photon, proton and vertex reconstruction, plus the first Delta observables and the background mechanisms. Three analysis decisions are open, the fiducial volume, the proton threshold with the treatment of leftover-shower rows, and the candidate policy; decision support exists but nothing is chosen. The beam-off normalisation and the flash-time reference are externally blocked, and a real comparison with SPINE needs the same-event SPINE output and the exact efficiency definition. Only after those do data/MC validation and then dedicated optimisation or retraining make sense."
* **Caveat to keep visible:** "decisions D, E, F are OPEN; nothing in this talk is an approved definition".

---

## OPTIONAL MAIN-OR-BACKUP SLIDES

### Slide O1 | Efficiency is strongly kinematic and position dependent  (main in the full talk if time allows, else backup)
* **Plots:** `13a_eff_vs_photon_energy.png`, `13b_eff_vs_photon_angle.png`, `13c_vertex_z.png` (originals `plots/differential_efficiency/eff_stages_vs_photon_energy_mev.png`, `eff_stages_vs_cos_theta_beam.png`, `eff_groups_vs_vtx_z.png`).
* **Headline numbers:** photon energy **2.4 %** (50-100 MeV) -> **~15 %** above ~400 MeV; photon angle **3.0 %** (backward) -> **12.8 %** (forward); **4.4 %** at z = 450-500 cm; interior box 11.4 % vs 7.3 % outside (not a proposed FV).
* **Bullets:** final efficiency rises with photon energy; and with forward angle, persisting after energy stratification; falls strongly at the detector edge; the dependence is introduced at the shower stage and later conditional survival.
* **Note on the energy / angle panels:** colours (selection stages): numu yellow, other dark orange, ncpi0 pink, final black.
* **Speaker note (45 s):** "The efficiency is far from flat. It rises from 2 percent for the lowest photon energies to 15 percent above 400 MeV, and from 3 percent for backward photons to 13 percent for forward ones; the angular trend survives inside energy bins. Position matters too: the efficiency is flat in the interior and falls at the edges, to 4.4 percent in the last 50 cm in z. The 'interior box' is a diagnostic, not a proposed fiducial volume."
* **Caveat:** "energy and angle are correlated (Spearman 0.72); descriptive; no FV proposed".

### Slide O2 | The natural NC-Delta in the BNB CV agrees within low statistics
* **Plot:** `14_natural_cv.png` (original `plots/natural_ncdelta/natural_vs_dedicated.png`; optional crop: bottom-right rate panel + top-left energy panel).
* **Headline numbers:** 416 natural events, 128 in the filter box, **117** in the TPC box, **13** selected = **11.1 %** vs **9.28 %** for the dedicated sample (binomial p = 0.52); rate ratio 0.98 (95 % interval 0.81-1.18).
* **Bullets:** natural events reproduce the dedicated sample's kinematics; selected fraction consistent; low statistics only exclude gross disagreement.
* **Speaker note (30 s):** "As a cross-check, the natural NC Delta events in the beam CV, 117 in the TPC box, behave like the dedicated sample. 13 are selected, 11 percent, against 9.3 percent; the rate ratio is consistent with one. With these statistics this only excludes gross disagreement."
* **Caveat:** "13 events: excludes gross disagreement only".

### Slide O3 | SPINE comparison: truth side harmonised, reco comparison not yet possible  (backup by default)
* **Plot:** `15_spine_denominator.png` (original `plots/spine_harmonization/denominator_definition_effect.png`).
* **Headline numbers:** loose TPC-box denominator **9.28 %**; SPINE-harmonised denominator **947 / 8,668 = 10.93 %** (0p50 9.38 %, Np50 12.81 %).
* **Bullets:** the same frozen Wire-Cell numerator on different truth denominators; shows how much of OUR number is definition; **THIS IS NOT A WIRE-CELL VS SPINE PERFORMANCE COMPARISON**; needed from Seokju: same-event SPINE output, exact reco-side 0p/Np definition, exact working point and efficiency denominator, common observable definitions.
* **Speaker note (45 s):** "The truth side of a SPINE comparison is harmonised: FV, containment, one photon above 25 MeV, charged-particle veto, 50 MeV proton threshold, 0p and Np topology. On that denominator the same frozen Wire-Cell selection gives 10.9 percent instead of 9.3. This only shows the denominator-definition effect. It is not a comparison with SPINE: we have no same-event SPINE output and not the exact selection definition."
* **Caveat:** "NOT a Wire-Cell vs SPINE performance comparison".
* **Why backup by default:** its numbers are denominator effects and are easily misread as a comparison; slide 12 carries the SPINE status. Promote it to main for a SPINE-focused audience.

---

## BACKUP SLIDES (15)

Each is one figure or table; numbers are rows of `NCDELTA_BASELINE_SLIDE_NUMBERS.md` (slide ids B01-B15). Deeper provenance: `NCDELTA_BASELINE_TECHNICAL_INDEX.md`.

| id | title | asset (under `presentation_assets/ncdelta_baseline/backup/`) | key content | note |
|---|---|---|---|---|
| B01 | Production provenance and the official signal sample | `B01_official_sample_census.png` | fg1 chain pin (wire-cell-toolkit `sbnd-wc-flatcaf` `4b6853d4`), official Gen2 sample 13,773 events, 12,427 in the TPC box; 1 event missing from the merged CAF | production bookkeeping items are non-blocking |
| B02 | Complete cutflow table | `B02_cutflow_combined_original.png` + table from `tables/baseline_consolidation/loss_budget.csv` | cumulative and first-failure per stage; 3-event bookkeeping difference at numu / ncpi0 (3,030 vs 3,027; 1,465 vs 1,468) | numu failures = 26.9 % of the total loss (corrected) |
| B03 | `first` vs `any` candidate policy | `B03_candidate_policy.png` | 1,101 vs 1,153; `any` adds 52 real signal events and 22 background events | decision F open |
| B04 | Fiducial-volume decision support | `B04_fv_comparison.png` (+ `B04b_fv_edge_stability.png`) | 9.28 % with none; 10.1-10.6 % for the 175-190 cm families; 9.92 % with the high-y carve-out; no knee | decision D open; no recommendation; no option preferred for its efficiency |
| B05 | 35 vs 50 MeV proton policy and `included == 3` | `B05_proton_policy.png` | 63 events 1g1p -> 1g0p without `included == 3`; 1,072 truth events change category; 84.7 -> 89.7 % truth-1p composition of reco 1g1p | decision E open |
| B06 | Photon conversion-distance definition | `B06_conversion_distance.png` | true conversion distance = Geant4 end point of the primary photon (11,512 events); the reco shower gap is a different quantity (Spearman 0.975 only for detached showers with anchored vertices) | keep source vs reco distinct |
| B07 | Detailed photon reconstruction taxonomy | `B07_photon_taxonomy_vs_energy.png` (+ `B07b_photon_type_vs_energy.png`) | fragmented 15.1 %, track 13.0 %, typed muon / pion / proton 29.6 % of shower-stage failures | association |
| B08 | numu compactness and attribution | `B08_numu_shap_families.png` (+ `B08b_numu_survival_vs_energy_by_compactness.png`) | compact rejections come from the shower-quality inputs, extended rejections through the upstream numu score; at fixed shape survival falls with energy while the marginal is flat | no domain-shift claim; see `NUMU_COMPACT_SHOWER_TRAINING_DOMAIN_AUDIT.md` |
| B09 | ncpi0 pair-origin result | `B09_ncpi0_pair_origin.png` | 94.2 % of rejected events have a pair flag, 88.0 % a pair with the signal photon; second member: same-photon piece, other signal EM, hadronic object | the pair need not be a pi0 |
| B10 | Shower attachment: PF ancestry of the 567 events | `B10_shower_attachment_parents.png` | parent a true signal proton 62 %, mis-typed photon piece 15 %, pi0 pair 6 % | ownership, not vertexing |
| B11 | Proton origin and Delta charge | `B11_proton_origin_delta.png` (+ `B11b_proton_origin_stage_survival.png`) | +12.7 pp falls to +0.7 pp with proton KE alone; residual +3.8 pp (decay minus FSI-created) and +5.2 pp (Delta+ minus Delta0) in the final efficiency, arising at ncpi0 | origin, charge, topology entangled; Delta0 7.61 % vs Delta+ 11.32 % is not a clean charge effect |
| B12 | Proton PID failure modes | `B12_proton_pid_high_ke.png` (+ `B12b_proton_low_ke_merge.png`) | 182 of 362 protons above 500 MeV mistyped; mistyped protons 55-66 cm vs 122 cm; low-KE merge into the signal photon (65 %) | dQ/dx template scores and true end process not stored |
| B13 | Natural-CV validation (cutflow) | `B13_natural_cv_cutflow.png` | stage-by-stage natural vs official (13 / 117 final) | low statistics |
| B14 | SPINE harmonisation requirements | `B14_spine_harmonized_differential.png` | 9,206 of 13,773 in the SPINE FV; checklist for Seokju: same-event output keyed by (run, subrun, evt), commit / TOML, containment and FV settings, efficiency definition, interaction policy, stage mapping, cosmic / flash treatment | no direct comparison until then |
| B15 | Analysis roadmap and blockers | table (baseline section 17 and 15) | DONE A B C O P Q T U V Y; largely done M N S X Z; open D E F; blocked G H; queued I; SPINE J K W; deferred L; R bookkeeping | blockers: beam-off normalisation, flash time, SPINE output |

---

## TWO DECK LENGTHS

**A. SHORT COLLABORATION UPDATE: 8 main slides, ~8-10 min.** Keep slides **1, 2, 4, 6, 8, 9, 11, 12**. **Drop from the full outline: 3, 5, 7, 10** (and the optional slides O1-O3).
* Slide 2 uses the combined original `backup/B02_cutflow_combined_original.png` (both panels) so that it carries the first-failure numbers of the dropped slide 3 (26.2 %, 24.4 %, 17.9 %, 11.8 % and the sentence "reconstruction state, not photon energy").
* Slide 4 gets one extra bullet absorbing slide 5: "the inherited BDTs then reject what the reconstruction mangled (numu: 29 % survive under 20 cm of shower vs 74 % above); no domain-shift claim possible".
* Slide 8 (matrix) gets one extra bullet absorbing slide 7: "truth 1p -> reco 0p is mainly proton mis-typing, merging or missing rows, not the 35 MeV threshold".
* Slide 11 gets one extra bullet absorbing slide 10: "backgrounds differ by channel (1g0p NC pi0 / outside-TPC; 1g1p nue CC / NC pi0)".

**B. FULL TECHNICAL FIRST-LOOK TALK: 12 main slides, ~15-20 min**, all of slides 1-12; add O1 if there is time (it takes the place of nothing; ~2 min); O2 and O3 stay in backup unless asked.

---

## Quality-control checklist (applied to this outline)
* Stale numbers: every number is a row of the slide-numbers table; the corrected 26.9 % is used; the superseded 29.8 % appears only in the line above that forbids it.
* No S/B, purity or significance claim: S/B appears only as "NOT S/B"; no purity number anywhere (B05 quotes a truth-composition fraction of a reco channel, labelled as such).
* No approved-FV wording; no optimisation wording beyond "no optimisation" and the deferred step; no SPINE comparison claim; truth and reco topology labels spelled out; Delta0 / Delta+ only in backup with the entanglement caveat.
