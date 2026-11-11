# The frozen Wire-Cell NC-Delta baseline: single source of truth

Date: 2026-11-11. Branch `analysis/ncdelta-frozen-baseline-consolidation-20261111` (cut from the pushed Phase-18 head `a3e2ee52`). **Consolidation only**: no new analysis, optimisation, threshold change, retraining, reconstruction or policy decision. Every number below is read from a committed table of an earlier phase (`tables/baseline_consolidation/summary.json` collects them; `scripts/baseline_consolidation.py` rebuilds that file from the committed tables, with no ROOT access). Companions: `NCDELTA_FROZEN_BASELINE_EXECUTIVE_SUMMARY.md` (one page), `BASELINE_FIGURE_MANIFEST.md` (15 figures), `NCDELTA_BASELINE_TECHNICAL_INDEX.md` (phase map).

Four categories are kept apart throughout and tagged: **[A] ESTABLISHED BASELINE RESULT**, **[B] PROVISIONAL CONVENTION**, **[C] EXTERNALLY BLOCKED**, **[D] FUTURE WORK / OPTIMISATION**.

## 0. Definition of the baseline  [B for the conventions, A for the facts]

| item | value |
|---|---|
| sample | official Gen2 `EX_ncdeltarad` signal (13,773 generated events in the filter box; 12,427 in the provisional TPC box) |
| reconstruction | production fg1-compatible Wire-Cell (`HaiwangYu/wire-cell-toolkit` `sbnd-wc-flatcaf` `4b6853d4`), stored reconstruction exactly as produced |
| selection | inherited frozen single-photon BDT chain: candidate, > 20 MeV shower, BDT evaluable, `numu` > 0.4, `other` > 0.2, `ncpi0` > -0.05, `nue` > -1 (vacuous), `n_20br1`; weights and thresholds unchanged (`configs/baseline_selection.yaml` sha256 `f3251b78...`, `numu` XML sha256 `5886affb...`) |
| candidate policy | `any` (an event passes if any candidate passes; counted once); `first` quoted alongside |
| truth region for the headline efficiency | provisional TPC box, \|x\|, \|y\| < 200 cm, 0 < z < 500 cm |
| truth proton threshold | 35 MeV (post-FSI primary protons), provisional |
| analysis FV | **none** |
| not used | no retraining, no optimisation, no DV2-MAX, no Fix2 |

**`any`, the TPC box and 35 MeV are characterisation conventions. They are NOT collaboration-approved analysis definitions** (section 14).

## 1. Official signal [A]  (`tables/official_signal/official_active_tpc/`, `tables/baseline_consolidation/official_signal_headline.csv`)

| | selected | truth | efficiency (Wilson 68 %) |
|---|---|---|---|
| **total, `any`** | **1,153** | **12,427** | **9.28 %** [9.02, 9.55] |
| truth 0p | 476 | 5,863 | 8.12 % [7.76, 8.49] |
| truth 1p | 594 | 5,557 | 10.69 % [10.27, 11.12] |
| truth >= 2p | 83 | 1,007 | 8.24 % [7.37, 9.20] |
| **total, `first`** | **1,101** | 12,427 | **8.86 %** [8.60, 9.12] |
| `first` 0p / 1p / >= 2p | 453 / 566 / 82 | | 7.73 / 10.19 / 8.14 % |
| Delta0 -> n gamma | 521 | 6,846 | 7.61 % [7.30, 7.94] |
| Delta+ -> p gamma | 632 | 5,581 | 11.32 % [10.91, 11.76] |

`any` minus `first` is 52 events, all real NC-Delta signal whose candidate 0 belongs to another interaction (Phase 13). The Delta0 / Delta+ difference is **not a clean charge effect**: the decay nucleon of every Delta0 is a neutron (so Delta0 has no decay proton and only FSI-created protons) and that of every Delta+ is a proton, so Delta charge, proton origin, proton kinetic energy and truth topology are structurally entangled (Phase 17). The old 67 % vs 54 % decay-proton vs FSI-created difference at the `other` stage is composition (+12.7 pp falls to +0.7 pp with proton KE alone, -1.8 pp [-6.8, +6.5] after anchoring and proton reconstruction). A real residual remains in the final efficiency (decay minus FSI-created +3.8 pp; Delta+ minus Delta0 +5.0 pp, +5.2 pp after adjustment); it arises at `ncpi0` and is associated with neutron-mother low-energy photon rows that create the kinematics-tree pair (removing them: +3.8 to 0.0, +5.2 to +1.6 pp). The process behind those photons is an exploratory mediator, not established.

## 2. Truth to reco topology migration [A]  (`final_truth_to_reco_migration.csv`; Phase 10 / 13 / 15)

Final selected events (reco channel by the 35 MeV, existing `included` convention):

| | reco 0p | reco 1p | reco >= 2p | selected | not selected |
|---|---|---|---|---|---|
| truth 0p | **425** | 50 | 1 | 476 | 5,387 |
| truth 1p | 93 | **471** | 30 | 594 | 4,963 |
| truth >= 2p | 9 | 35 | **39** | 83 | 924 |

(Reco 1g0p / 1g1p / >= 2p totals: 527 / 556 / 70.) At the matched-candidate stage (before the BDT chain; `matched_candidate_truth_to_reco_migration.csv`): truth 0p 3,836 / 940 / 150, truth 1p 1,739 / 2,643 / 596, truth >= 2p 256 / 358 / 313.

Mechanisms (Phase 10 exact accounting; mutually exclusive, matched-candidate stage -> final selected):
* **truth 1p -> reco 0p** (1,739 -> 93): a row has the proton as top partner but no row is typed proton (883 -> 37; shower-typed electron, muon, pion); the proton is only a subdominant partner, i.e. merged (387 -> 15); the proton has no row although it deposited charge (370 -> 27); a typed-proton row exists below the 35 MeV reco threshold (89 -> 9); no readout charge (9 -> 4). The KE threshold is a minor (5-10 %) cause.
* **truth 0p -> reco 1p** (940 -> 50): the row is another signal particle, mostly the **signal photon typed proton** (468 -> 11); a **Geant4 secondary proton**, mainly neutron-induced from Delta0 decays (319 -> 26); a true primary proton **below the 35 MeV truth threshold** promoted by reco (121 -> 11); other-neutrino and cosmic rows (about 20 -> 1). About 28 % of the matched 0p -> 1p rows are `included == 3` leftover-shower rows.

## 3. Where the signal efficiency is lost [A]  (`loss_budget.csv`, `fig_cutflow_loss_budget.png`)

All fractions are of the 12,427 truth events. "First failure" is exclusive (sums to 12,427).

| stage | cumulative surviving | cumulative efficiency | first-failure count | first-failure fraction |
|---|---|---|---|---|
| truth denominator | 12,427 | 100 % | | |
| wc.valid | 12,426 | 99.99 % | 1 (missing from merged CAF; 0 invalid) | 0.01 % |
| candidate | 11,331 | 91.18 % | 1,095 | 8.81 % |
| > 20 MeV shower | 8,080 | 65.02 % | 3,251 | 26.16 % |
| BDT evaluable | 8,034 | 64.65 % | 46 | 0.37 % |
| numu | 5,007 | 40.29 % | 3,030 | 24.38 % |
| other | 2,781 | 22.38 % | 2,226 | 17.91 % |
| ncpi0 | 1,313 | 10.57 % | 1,465 | 11.79 % |
| nue | 1,313 | 10.57 % | 0 | 0 % |
| n_20br1 | 1,153 | 9.28 % | 160 | 1.29 % |
| **final (selected)** | **1,153** | **9.28 %** | 1,153 | 9.28 % |

Bookkeeping note: the exclusive first-failure counts differ from the differences of the cumulative counts by +3 at `numu` (3,030 vs 3,027) and -3 at `ncpi0` (1,465 vs 1,468). This is inherited from the validated Phase-5 / Phase-12 event-level flags (three events pass the `numu` flag without the evaluability flag, `FROZEN_SELECTION_CHAIN_SUMMARY.md`) and is not re-derived here; the model-level `numu` population is 8,038 events, the baseline's evaluable population 8,034.

**Erratum to the Phase-18 loss shares (Phase 18 is pushed and unchanged).** `NUMU_COMPACT_SHOWER_TRAINING_DOMAIN_AUDIT.md` quoted its shares of the total baseline loss against 11,331 events (the events with a candidate, 10,178 lost), omitting the 1,096 truth events that never reach a candidate. The counts there are correct; the correct denominator is the 12,427-event truth region with 11,274 events lost: numu failures are **26.9 %** of the total loss (not 29.8 %); compact objects (length < 20 cm, 1,445) **12.8 %** (not 14.2 %); compact or few-segment 15.4 % (not 17.0 %); non-clean photon objects 15.6 % (not 17.2 %); muon/pion-like controlling objects 4.3 %. Table `phase18_loss_share_correction.csv`. The Phase-18 conclusions are unchanged.

## 4. Mechanism by stage [A; association language]

* **Candidate (8.8 % lost).** Vertexing / candidate formation: 1,096 events have no candidate; a near-face deficit (29 % of the no-candidate events lie within 10 cm of a face) and photons leaving the volume (78 % of those have no reconstructed charge). Flat at 91-93 % in photon energy.
* **> 20 MeV shower (26.2 % lost).** The missing usable photon shower is mostly pattern recognition, typing and attachment, not a true-photon-energy threshold: typed muon / pion / proton 29.6 % of the failures, shower not in the main vertex's set 17.4 %, fragmented 15.1 %, track 13.0 %; only 1.2 % are genuinely below 20 MeV. About a quarter of the events are lost here even at high photon energy.
* **numu (24.4 % lost).** The frozen BDT preferentially rejects compact, few-segment reconstructed photon objects (survival 29 % for total shower length < 20 cm vs 74 % above; 25 % for < 5 segments vs 73 %); clean extended showers survive well (clean electron shower 76 %, fragmented 36 %, muon-/pion-typed 22-25 %). About 44 % of the raw difference is shared with the photon reconstruction class and a 25-32 pp association remains after control. No quantitative MicroBooNE-to-SBND domain-shift claim is possible: no training sample, class labels or input distributions exist (`NUMU_TRAINING_DOMAIN_SOURCE_AUDIT.md`).
* **other (17.9 % lost).** Dominated by vertex anchoring and connectivity: events whose vertex is anchored survive 65-79 %, not anchored 33-46 %. A reco-typed proton anchors the deep-learning-stage vertex (42 % to 67.5 %). In truth-0p events the photon-line vertex displacement (median +24.5 cm along the photon) is already present before the final refinement.
* **ncpi0 (11.8 % lost).** The reconstruction forms a kinematics-tree shower pair (largest-E1+E2 pair, no mass requirement) or a mass-window tagger pair for a single true photon. The pair need not be a physical pi0: 94.2 % of the rejected have a pair flag and 88.0 % a pair containing the signal photon; the second member is other signal EM activity, a piece of the same photon, or a hadronic object. Neutron-mother low-energy photons explain much of the proton-origin / Delta-charge residual.
* **nue (0 lost).** Effectively vacuous at the current threshold (the cut > -1 cannot fail for a tanh score).
* **n_20br1 (1.3 % lost).** A reconstructed shower-multiplicity veto; many failures contain another reconstructed piece of the signal photon (126 of 160 split single photons).

## 5. Differential performance [A]  (Phase 6, `DIFFERENTIAL_SIGNAL_EFFICIENCY.md`, `tables/differential_efficiency/summary.json`)

Representative curves (figures in the manifest, rows 4-6 and 2):
* **Photon energy.** Final efficiency rises monotonically from 2.4 % (50-100 MeV) to about 15 % above 400 MeV (9.2 % at 250-300, 12.3 % at 300-400). The dependence is introduced mainly at the shower stage and in the later conditional survival (the `other` stage, strongly energy-dependent; ncpi0 and n_20br1 rise with energy), while the candidate stage is flat; `numu` is marginally flat (but see the Phase-18 note: at fixed shower shape survival falls with energy).
* **Photon angle.** The final efficiency rises from 3.0 % (cos in [-1,-0.75]) to 12.8 % ([0.75, 1]). The trend **persists after energy stratification** (3 x 3 bins: energy < 200 MeV 2.9 -> 5.9 -> 6.9 %; 200-300 5.9 -> 8.7 -> 9.1 %; > 300 7.2 -> 11.3 -> 13.7 %), and also in an interior diagnostic box; energy and angle are correlated (Spearman 0.72) and not separated into independent causes.
* **Vertex position.** Flat in the interior, degraded near the boundaries: z bins 9.3-11.6 % but **4.4 % at 450-500 cm**; x edge bins 6.4-8.5 %; y edge bins 5.4-5.7 %; interior diagnostic box (not a proposed FV) 11.4 % vs 7.3 % outside; candidate efficiency 97 % vs 86 %. The detector-side asymmetry reflects the denominator, not the efficiency. There is no knee that singles out a boundary.
* **Neutrino energy.** Mild dependence (6.2 % at 0.25-0.5 GeV to about 10 % at 1-1.5 GeV, 5.9 % above 3 GeV); not to be compared numerically with numuCC / nueCC efficiencies.
* **Proton KE and 0p vs 1p.** The truth-1p efficiency (10.69 %) exceeds truth-0p (8.12 %), +2.57 pp; the difference is not explained by the kinematic or positional distributions and develops in the `other` conditional survival (47 % vs 63 %), mostly through the fraction with an anchored vertex. Near-threshold protons do worse: truth-1p efficiency is 6.6 % (35-50 MeV) and 7.2 % (50-75), below the truth-0p average, peaks at 16.0 % (200-300 MeV) and falls to 6.1 % above 500 MeV; the reco-0p fraction is 47 % at 35-50 MeV (19 % at 200-300, 37 % above 500) and truth-1p -> reco 0p is highest (3.4 %) in the lowest-KE bin.

## 6. Photon reconstruction [A]  (Phases 9, 11, 14, 15, 16)

* **Energy response.** For the 1,148 truth-correct selected photons: E_reco/E_true median **1.034**, 68 % half-width 12.7 % (11-15 % at every energy and conversion distance; truth 0p 14.1 %, truth 1p 11.8 %). A clean electron shower of the signal photon has median E_reco/E_true 0.90 at the numu stage (all events reaching it), a fragmented object 0.37.
* **Conversion-distance definition.** Source: the true conversion distance is the distance from the true vertex to the Geant4 end point of the primary photon (`PHOTON_CONVERSION_DISTANCE_DEFINITION.md`); it is defined for 11,512 events (92.6 % of the box; 695 photons leave the volume, 220 end in another interaction). The **reco shower-to-vertex gap is a different quantity**: it is a conversion-distance estimator only for a detached shower with an anchored vertex (Spearman 0.975); elsewhere it is a vertex-anchoring / topology observable. True conversion distance up to about 50 cm has little effect on the final efficiency.
* **Shower-to-vertex behaviour.** 50.6 % of in-volume signal photons have the shower attached at the vertex (gap 0); anchored vertices 24 % attached, not anchored 94 %.
* **Fragmentation.** The signal photon is reconstructed as several pieces (median 3, 79 % across several clusters of the same candidate). The 1,622 events whose `> 20 MeV` shower is carried by fragments survive 1,622 -> 582 -> 150 -> 24 -> 14 through numu, other, ncpi0, n_20br1; the cause of the cluster split stays open.
* **PID mis-typing.** 27.6 % of signal photons have a track-typed dominant object (muon, pion or proton-like); the dominant confusion is muon and pion typing (the source defaults to muon and the main-vertex arbitration turns every non-longest muon candidate into a pion); flat in conversion distance, falling with energy, E_reco/E_true about 0.5. The per-segment PID inputs are not stored (section 8).
* **Shower not in the main vertex's set.** 567 events (17.4 % of the shower-stage failures): correctly reconstructed electron showers (median 212 MeV, E_reco/E_true about 0.95) owned by an indirect connection to a hadron-typed object about 20 cm away across the conversion gap (parent a true signal proton 62 %, a mis-typed piece of the photon 15 %, a pi0 pair 6 %); failure rate 4.6 % (0p) -> 13 % (1p) -> 14.7 % (>= 2p).

## 7. Vertex reconstruction [A]  (Phase 16, `NCDELTA_VERTEX_PROVENANCE_AUDIT.md`)

Final-selected signal: |V_reco - V_true| median 2.0 cm; **truth 1p 0.93 cm (86 % within 5 cm), truth 0p 11.6 cm (28 %)**, displaced about +11 cm along the photon line. Provenance for truth-0p events (targeted `T_dlvtx_call` scan of 11,331 events, 0 errors): the median photon-line displacement is **+25.8 cm in the traditional vertex, +36 cm in the raw network output and +24.5 cm at the DL-stage vertex**; the late refinement moves the vertex by a median 0.25 cm (3.8 % large post-DL moves; class "introduced after DL" = 1 event). The DL stage anchors the vertex when a true proton is reco-typed (42 % to 67.5 %); 60-83 % of the 0p / 1p `other`-stage gap is the anchored fraction set at DL time. **The 0p / 1p vertex difference is established before the final vertex refinement.** Open: why the traditional vertexing and the (MicroBooNE-trained) network place the vertex along the photon in 0p events.

## 8. Proton reconstruction [A]  (Phases 10, 15)

* **Row-level truth association** (`T_match` level 1, source-ranked): reproduced exactly in Phases 15 and 17. Proton typing efficiency above 35 MeV is 46 % overall, 67 % at 200-300 MeV and 22 % above 500 MeV.
* **Low-KE merging.** 16 % of signal protons are only a subdominant partner of another object (507 of 1,502 below 50 MeV); 65 % of the merged truth-1p protons are merged into the signal photon.
* **High-KE mu/pi mis-typing.** 17 % of the protons above 35 MeV have a row typed muon / pion / electron-shower (half of those above 500 MeV: 182 of 362); muon (30 %) and pion (15 %) typing dominate above 500 MeV, the mistyped protons are short (55-66 cm vs 122 cm) with no stopping peak and E_reco/E_true about 0.2.
* **Effect on migration.** Section 2 (the leading cause of truth-1p -> reco 0p is a non-proton-typed or merged proton, about three quarters of the matched events, not the 35 MeV threshold).
* **Unavailable producer-side information:** the per-segment dQ/dx vector (or its median), the PID template scores / `particle_score`, `start_n` / `end_n` and direction sign at PID time, the production values of the knob-gated PID options, other PID-time graph quantities, and the **true end process of the protons**.

## 9. Delta reconstruction and common observables [A]  (Phase 11)

* **Delta mass** (`M^2 = m_p^2 + 2 E_gamma (E_p - p_p cos theta)`): for the 348 selected **Delta+ decay pairs** (truth-matched photon and decay proton; the source-audited headline) `M_reco - M_true_decay` has median **+2.8 MeV, 68 % interval [-44, +34] MeV**, RMS 65 MeV; the width is set by the photon energy (half-width 10.4 %) and the photon-proton opening angle, not by the proton KE (3 %). Policy-dependent wrong-pair tails (FSI-created, Geant4 secondary, fake-proton pairs) are **not** in this resolution; for context, all 554 usable events give a median 1220.8 MeV (68 % interval 1136-1316), and the generator decay mass peaks at 1232 MeV (the Delta0 reco peak is not the decay-pair mass).
* **Photon energy:** E_reco/E_true 1.034 +/- 12.7 %. **Direction:** median angle 10.2 deg, 68 % within 15.8 deg, 3.0 % negative cosine (the stored chord is shower start to the farthest vertex).
* **Shower-to-vertex gap and dQ/dx:** see section 6; median shower-start dE/dx 3.9 / 3.6 MeV/cm (reco 1g0p / 1g1p), nueCC primary electron 2.1 (MIP).
* **Proton kinematics:** reco/true KE median 0.996, half-width 4.4 % for truth-correct primaries (493); reco proton KE median 160 MeV.

## 10. Backgrounds [A]  (BNB CV, Phase 4)

635 non-signal selected BNB-CV events (649 selected `any` = 14 signal-like + 635; POT 2.7194e19; statistical errors only): **reco 1g0p 310, 1g1p 230, >= 2p 95**; rates per 1e20 POT (neutrino-induced) **1,140 +/- 65, 846 +/- 56, 349 +/- 36** (total 2,335).
* **1g0p:** NC pi0 102 (32.9 %), outside-TPC neutrinos 75 (24.2 %), nue CC 53 (17.1 %), CC pi0 43 (13.9 %), cosmic/unmatched 14.
* **1g1p:** nue CC 86 (37.4 %; the primary electron is the selected shower in all 86), NC pi0 68 (29.6 %), CC pi0 42 (18.3 %), outside-TPC 17 (7.4 %).
No nueCC special-sample rate is added; no cosmic-only (beam-off) normalisation is included.

## 11. Signal and background rates [A for the numbers, C for any ratio]

Signal (official, provisional TPC box, policy `any`, per 1e20 POT, statistical): **40.62 +/- 1.14**; by reco channel 1g0p 18.57 +/- 0.78, 1g1p 19.59 +/- 0.80, >= 2p 2.47 +/- 0.29. Beam-neutrino background (above, whole generated volume): 1,140 / 846 / 349. They are quoted independently (`signal_and_bnb_background_rates.csv`, figure row 14). **They are not an S/B**: the signal uses a truth-box denominator and the background has no common volume; the existing refusals stand (no total purity, no total S/B, no significance) until a **common analysis volume and the beam-off normalisation** exist.

## 12. Natural NC-Delta cross-check [A]  (Phase 3 / 5, `NATURAL_NCDELTA_CV_CROSSCHECK.md`)

416 natural NC-Delta events in the BNB CV, 128 in the filter box, **117 in the provisional TPC box**, **13 selected under policy `any`** (11.1 % against 9.28 % for the dedicated official sample, binomial p = 0.52). The TPC-box rate per 1e20 POT is 430 against 438 (ratio 0.98, 95 % interval 0.81-1.18). **Low statistics only exclude gross disagreement**; the check does not validate the efficiency at the percent level.

## 13. Cross-analysis lessons [A as documented in the project notes]

| person | what the project notes record | how it changed the strategy |
|---|---|---|
| **Prabhjot** | data/MC figure style (upper panel, ratio, hatched systematic band, provenance line; `plotstyle.py`), cutflow / efficiency presentation, the beam-off gate normalisation question (roadmap items G, I; `DATA_EXPOSURE_NORMALIZATION.md`) | every figure carries a provenance line; data/MC and systematics are queued behind the decisions D-F and the normalisation G / H; the cosmic-only component is not normalised |
| **Matteo** | efficiency-loss decomposition and truth/reco failure-mode method from the nueCC work (roadmap A, K; `T_match` level 3 is "Matteo's definition", `WIRECELL_TRUTH_MATCH_SEMANTICS.md`) | the first-failure accounting, the stage-by-stage reconstruction-failure taxonomy (Phases 9, 14-17) and event-level diagnostics common to signal and background |
| **Haiwang / Hanyu** | official fg1 baseline production, merged CAF semantics, truth matching (`TruthMatch.h`), candidate ordering, production provenance (`fg1/README.md`), frozen-selection implementation; open questions in `QUESTIONS_FOR_HAIWANG_HANYU.md` | the baseline is the unmodified production chain; the provenance gate, source audits at the producer pin `4b6853d4`, and the externally owned questions (flash time, `included == 3`, candidate policy) |
| **Seokju** | SPINE NC-Delta technote signal definition, FV, 50 MeV proton threshold, 0p/Np topology, common observables (`SPINE_SIGNAL_DEFINITION_SOURCE_AUDIT.md`; roadmap B, D, J, K) | the harmonised denominator ladder, the common observable set, and the rule that no Wire-Cell-vs-SPINE efficiency is quoted without the same events and the exact definition |

No result is attributed to a person beyond what these notes state.

## 14. Analysis-definition decisions [B; all OPEN]  (Phase 13)

| decision | current characterisation convention | decision support | status |
|---|---|---|---|
| **D: fiducial volume** | provisional TPC box for the truth denominator; no reco FV | `FIDUCIAL_VOLUME_DECISION_AUDIT.md`, `ANALYSIS_DEFINITION_DECISION_MATRIX.md` section D: seven candidate volumes (efficiency 9.28 % with none, 10.1-10.6 % for the 175-190 cm families, 9.92 % with the high-y carve-out; background 635 -> 394-485); no knee in the edge behaviour; **no recommendation** | **OPEN ANALYSIS DECISION** |
| **E1: proton threshold** | 35 MeV | 35 vs 50 MeV: class efficiencies move about 0.2 pp, 18 events change reco category, 1,072 truth events change truth category; M_Delta mode 1225 MeV in all; **no recommendation** | **OPEN ANALYSIS DECISION** |
| **E2: `included == 3`** | **counted** in the headline numbers (the inherited rule); the decision support prefers **excluding** them on source semantics (pool-2 leftover showers, not vertex-attached) | excluding changes 63 events 1g1p -> 1g0p; truth-1p purity of 1g1p 84.7 -> 89.7 % | **OPEN ANALYSIS DECISION**; not silently promoted |
| **F: candidate policy** | `any` (`first` quoted) | `any` supported by source semantics (candidate index = activity length) and event counting; `first` loses 52 real signal events; adds 22 background events | **OPEN ANALYSIS DECISION** |

## 15. Externally blocked items [C]

* **G:** the approved beam-off normalisation (`noffbeambnb` vs `nbnbinfo` recording fractions differ by about 4.8x; the scale factor is a collaboration decision).
* **H:** the flash-time reference (the beam-on flash time peaks about +0.3 us later than in MC; no document states that it is expected; no D / E / F option depends on it).
* **J:** official same-event SPINE output and the exact SPINE efficiency definition.
Non-blocking production bookkeeping (NOT blockers): one signal event missing from the merged CAF (run 317, subrun 41, event 6753); 728 historical reco1 units without a flatCAF child; `TotalGenEvents` 125 vs SAM 12,500.

## 16. SPINE comparison readiness [A for the machinery, C for any comparison]  (Phase 7)

Completed: the SPINE truth FV (|x|, |y| < 180 cm, 10 < z < 450 cm; 9,206 of 13,773 events), containment (5 cm approximation on flatCAF primaries), exactly one photon > 25 MeV, no e / mu / charged pi > 25 MeV, the 50 MeV proton threshold, 0p / Np topology, common observables, and the Wire-Cell efficiency on the harmonised denominator: **947 / 8,668 = 10.93 % (`any`)**; 0p50 9.38 %, Np50 12.81 %. The loose-box number (9.28 %) is not comparable with a SPINE number.

**There is NO direct Wire-Cell-vs-SPINE performance claim** until same-event SPINE output and the exact selection definition arrive. **Checklist for Seokju:** (1) SPINE outputs keyed by `(run, subrun, evt)` for the same 13,773 Gen2 events; (2) the SPINE commit / TOML that produced the technote numbers and whether it included `neutrino2026_veto` and the expanded Delta-resonance set; (3) the production SPINE containment and fiducial settings; (4) the exact efficiency definition (denominator truth set; numerator after cosmic rejection / flash matching and the channel BDT working point); (5) the interaction / candidate policy; (6) the reconstruction-stage mapping to the Wire-Cell stages; (7) cosmic / flash treatment and systematics on both sides; (8) SPINE truth particles (energy_init vs genE) for the particle-level cuts.

## 17. Roadmap status matrix (verified against `NCDELTA_ANALYSIS_ROADMAP.md`)

| status | items |
|---|---|
| DONE | **A B C O P Q T U V Y** |
| LARGELY DONE to the information limit | **M N S X Z** |
| OPEN ANALYSIS DECISIONS | **D E F** |
| EXTERNALLY BLOCKED | **G H** |
| QUEUED after blockers | **I** |
| WAITING FOR SPINE | **J K W** |
| DEFERRED optimisation | **L** |
| bookkeeping | **R** (tie-convention note; no score changed, max 3e-9) |

Prerequisites before optimisation (L): decisions D, E, F recorded; G and H resolved; the same-event SPINE comparison (J, K) for context; the open reconstruction questions named in sections 6-8.
