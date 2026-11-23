# NC-Delta -> N gamma: collaboration presentation handoff, EAF side (frozen legacy chain: purity, data/MC, control regions)

Audience: Presentation Claude (to be combined with the Aurora handoff). No PowerPoint here, no new physics.
Repo: `/home/abhat/Single-photon/sbnd-wirecell-single-photon`.

## Provenance (read first)

| item | value |
|---|---|
| branch | `analysis/ncdelta-purity-datamc-20261120` |
| authoritative pushed HEAD | `b0cbd4e9a06f2bd98e8f5a5b61733ff64c167ecd` (local = `origin/...`, verified when this file was written) |
| later unpushed *result* commits | **none.** The control-region/systematics work, the neutron-G4 audit and the wording cleanup (`3551afa`, `07bf747`, `96245c5`, `ee6117f`, `98b3a5e`, `b0cbd4e`) are all inside the pushed HEAD |
| this handoff | a documentation-only commit **on top of** `b0cbd4e`, **local, not pushed** until Avinay approves. Every number below comes from files that are in the pushed HEAD |
| source documents | `docs/analysis/NCDELTA_FROZEN_SELECTION_PURITY_RESULTS.md`, `NCDELTA_SYSTEMATIC_WEIGHTS_FIRST_PASS.md` (sections 7-11), `NCDELTA_CONTROL_REGION_COLLABORATION_HANDOFF.md`, `QUESTIONS_FOR_HAIWANG_HANYU.md` |
| tables | `tables/ncdelta_purity_datamc/` (names given per number below) |
| figures | `plots/ncdelta_purity_datamc/` (**PNG only; there are no PDFs** anywhere in `plots/`; regenerating vector versions means re-running the scripts, and the numbers must then be re-read from the CSVs) |

Terminology for the whole talk:
- **MC-only expected purity - upper bound.** Never just "purity".
- **baseline available covariance (excluding unresolved reinteractions_neutron_Geant4 tail)** and **including unresolved neutron-G4 tail diagnostic**. The word "validated" must not appear (internal artifact keys `TOTAL_validated_excl_nG4` / `unvalidated_nG4` keep their historical names; ignore them in slides).
- "old" = old fg1-era reconstruction (legacy); "WCL1116" = WCLocal2026Nov16 (code/key `nov16`).

---

# Executive summary

1. Frozen, source-faithful MicroBooNE-BDT chain, in the TPC-box denominator of 12,427 signal events: efficiency **6.70% -> 15.60%** (old -> WCL1116).
2. MC-only expected purity is essentially unchanged: **2.74 +- 0.18% -> 2.63 +- 0.11%** (stat). Signal x2.33, background x2.43. Upper bound, because the beam-off component has no approved normalization.
3. Open-data control regions (runs 18255/18259, 4.62e18 POT) have integrated Data/MC near 1 in preselection, nu-mu-, other- and nu-e-rich samples; the NC-pi0-rich sideband sits at 0.76 / 0.74 (old / WCL1116), which is about -1.6 / -1.8 sigma with the baseline available covariance. Not a significant rate deficit *within the available neutrino-model uncertainty*, with detector, cosmic, POT, `imp_weight` etc. all still missing.
4. The reconstructed Np/0p ratio is about 20% lower in data than in MC in several populated open control samples (0.80-0.82 in preselection and nu-mu-rich; 0.67-0.75 NC-pi0-rich; 0.79-0.91 other-rich). WCL1116 does not remove it. It is not NC-pi0-specific. Reconstruction vs hadronic modeling cannot be separated with the samples available.
5. The weight function `reinteractions_neutron_Geant4` is heavy-tailed (max weight 223,065 on one event) and is shown separately. Excluding it is **our diagnostic choice, not an approved SBN prescription**.
6. Final physical purity needs: beam-off normalization, detector systematics, final retrained/frozen scores. None of that is in this package.

# Physics story

Improved WCL1116 reconstruction recovers signal (more events reach and pass the frozen chain) but the inherited, MicroBooNE-trained BDTs do not discriminate better against the enlarged background (NC-pi0 background grows 427 -> 1162 per 1e20 POT). Open data show the MC description of the background is broadly adequate in rate, with one persistent topology (Np/0p) mismatch that survives the reconstruction update. This motivates (Aurora side) SBND-specific retraining and, on the EAF side, a re-run of this whole package on final frozen scores.

# Purity

Normalization: dedicated NC-Delta sample as signal S, generic BNB CV as background B (natural in-region NC-Delta events removed from B), expected yields per 1e20 POT, unit MC weights (`imp_weight` NOT applied), denominator 12,427 (provisional TPC box, candidate policy `any`). Cuts: numu > 0.4, other > 0.2, ncpi0 > -0.05, nue > -1.0 (frozen).
Source tables: `overall_purity.csv`, `cumulative_efficiency_purity.csv`, `topology_purity.csv`.

| | efficiency | S / 1e20 POT | B / 1e20 POT | MC-only expected purity (upper bound) |
|---|---|---|---|---|
| old | **6.70%** (833 / 12,427) | 29.3 +- 1.0 | 1040.7 +- 61.9 | **2.74 +- 0.18%** (stat) |
| WCL1116 | **15.60%** (1,938 / 12,427) | 68.3 +- 1.6 | 2526.3 +- 96.4 | **2.63 +- 0.11%** (stat) |

No systematic "+-" is attached to the central purity values. The error bars are statistical (MC) only.

**Topology purity (RECONSTRUCTED proton topology of the selected candidate, protons > 35 MeV; `topology_purity.csv`):**

| | 1g0p | 1g1p | >=2p (diagnostic) | 1gNp (= 1g1p + >=2p) |
|---|---|---|---|---|
| old | 2.52 +- 0.23% | 3.74 +- 0.42% | 1.17 +- 0.25% | **2.99 +- 0.29%** |
| WCL1116 | 2.31 +- 0.13% | 3.75 +- 0.30% | 1.55 +- 0.26% | **3.25 +- 0.23%** |

Reconstructed-topology purity is not truth-topology efficiency. Truth topology (used elsewhere in the repo, and for the migration figure) = post-FSI primary protons with KE > 35 MeV. Delta charge is not proton topology.

**Stage-wise cumulative (`cumulative_efficiency_purity.csv`; efficiency % of 12,427; purity %):**

| stage | old eff | old purity | WCL1116 eff | WCL1116 purity |
|---|---:|---:|---:|---:|
| candidate | 91.18 | 0.046 | 91.18 | 0.046 |
| >20 MeV shower | 65.02 | 0.147 | 63.07 | 0.142 |
| BDT evaluable | 64.65 | 0.152 | 62.43 | 0.148 |
| numu | 39.78 | 0.40 | 51.46 | 0.43 |
| other | 21.86 | 0.69 | 34.52 | 0.73 |
| ncpi0 | 10.50 | 1.36 | 19.74 | 1.58 |
| nue | 7.19 | 2.41 | 16.11 | 2.41 |
| final | 6.70 | 2.74 | 15.60 | 2.63 |

(All of these were verified bit-for-bit against the table.)

**Final background composition, per 1e20 POT (`background_composition_final_production_matched.csv`; authoritative candidate-level production-matched truth, now covering the full candidate sample):**

| category | old | WCL1116 |
|---|---:|---:|
| NC pi0 | 426.6 | 1162.0 |
| outside-TPC neutrino | 228.0 | 720.7 |
| CC pi0 | 220.6 | 345.7 |
| cosmic/unmatched (from BNB CV MC, **not** beam-off) | 47.8 | 91.9 |
| other NC | 47.8 | 80.9 |
| nu-mu CC | 51.5 | 55.2 |
| nu-e CC | 3.7 | 44.1 |
| ambiguous | 11.0 | 18.4 |
| natural NC-Delta outside the TPC box, kept in B by definition | 3.7 | 7.4 |

(The last row is not a separate bar in the composition figure: it is already counted inside B; counting it as signal would change purity by +0.01 percentage points.)

# Control-region Data/MC

Regions (open `beam_on_open` only; MC scaled to 4.62e18 POT; **no beam-off in the stack**):
Definitions (from `src/sbnd_single_photon/regions.py`; BDT scores are the frozen MicroBooNE scores, no new cuts):
- `preselection`: candidate in a `wc.valid` event, > 0 showers above 20 MeV, BDT evaluable (no score cut).
- `SB_numu` (nu-mu-CC-rich): SP-numu score < 0.1.
- `SB_other` (other-rich): numu > 0.1 and SP-other score < -0.4.
- `SB_ncpi0` (NC-pi0-rich): numu > 0.1, other > -0.4, SP-ncpi0 score < -0.4.
- `SB_nue` (nu-e-rich): numu > 0.1, other > -0.4, ncpi0 > -0.4, SP-nue score < -3.0, n20br1 == 1.
  (all lower scores bounded by -20). "nu-mu-rich" etc. also describes the dominant MC truth.
- Final frozen selection: BLOCKED for data (see Data policy).

Authoritative table: `tables/ncdelta_purity_datamc/control_region_summary_final.csv` / `.md`. Relative systematic = the "available" band (see Systematics status). "incl." = including the unresolved neutron-G4 tail diagnostic.

| region | reco | data | MC (S+B) | Data/MC | data stat | MC stat | avail. syst, baseline (incl.) | energy rate+shape chi2/ndof, baseline (incl.) | dominant MC truth |
|---|---|---:|---:|---:|---|---|---|---|---|
| preselection | old | 8480 | 8622 | 0.98 | 1.1% | 0.4% | 15.1% (23.8%) | 17.9/8 (15.8) | NUMU_CC 33%; CC_PI0 26% |
| preselection | WCL1116 | 8321 | 8547 | 0.97 | 1.1% | 0.4% | 15.5% (24.7%) | 22.4/8 (10.3) | NUMU_CC 31%; CC_PI0 27% |
| SB_numu | old | 6301 | 6294 | 1.00 | 1.3% | 0.5% | 16.2% (29.6%) | 12.1/8 (10.5) | NUMU_CC 42%; CC_PI0 31% |
| SB_numu | WCL1116 | 5871 | 5799 | 1.01 | 1.3% | 0.5% | 16.9% (32.5%) | 16.4/8 (9.2) | NUMU_CC 43%; CC_PI0 34% |
| SB_other | old | 1271 | 1206 | 1.05 | 3.0% | 1.2% | 12.7% (14.1%) | 10.3/8 (7.9) | OUTSIDE_TPC_NU 37%; NC_PI0 19% |
| SB_other | WCL1116 | 1262 | 1227 | 1.03 | 2.9% | 1.2% | 12.6% (14.0%) | 25.1/8 (25.0) | OUTSIDE_TPC_NU 40%; NC_PI0 17% |
| SB_ncpi0 | old | 585 | 766 | 0.76 | 3.2% | 1.5% | 19.1% (20.4%) | 6.2/8 (6.0) | NC_PI0 56%; CC_PI0 18% |
| SB_ncpi0 | WCL1116 | 755 | 1020 | 0.74 | 2.7% | 1.3% | 19.4% (20.6%) | 9.9/8 (8.4) | NC_PI0 61%; CC_PI0 16% |
| SB_nue | old | 55 | 55 | 0.99 | 13.4% | 5.5% | 15.1% (17.1%) | 1.9/5 (1.8) | NUE_CC 71%; NC_PI0 10% |
| SB_nue | WCL1116 | 63 | 69 | 0.92 | 11.5% | 5.0% | 16.5% (17.8%) | 6.1/5 (5.7) | NUE_CC 78%; CC_PI0 7% |

`SB_nue` is statistically weak (n_data < 100; Np or 0p bin < 50 events).

**NC-pi0 sideband rate, precise (from `syst_sideband_datamc_chi2_SB_ncpi0-SB_other-SB_nue_excl.csv` = baseline and `..._nue.csv` = including the tail function):**

| | Data/MC | +- baseline (total = stat+MC+available syst) | deviation from 1, baseline | +- incl. tail diagnostic | deviation, incl. |
|---|---|---|---|---|---|
| old | 0.764 | 0.148 (19.4%) | **-1.6 sigma** | 0.158 (20.7%) | -1.5 sigma |
| WCL1116 | 0.740 | 0.146 (19.7%) | **-1.8 sigma** | 0.154 (20.8%) | -1.7 sigma |

**Brief-vs-repo note:** the numbers "0.764 +- 0.158 / 0.740 +- 0.154, -1.5 / -1.7 sigma" in the request are the *including-tail-diagnostic* values. The baseline values (what figure F displays) are 0.76 +- 0.15 / 0.74 +- 0.15 at -1.6 / -1.8 sigma. Quote whichever the slide's bar represents; say "about -1.5 to -1.8 sigma" if both are shown.

Shower-energy rate+shape for NC-pi0: 6.2/8 (old), 9.9/8 (WCL1116), consistent. **Caveat for Q&A, not for the slide:** the 2-bin 0p/Np topology rate+shape is *not* consistent (baseline old 8.8/2, p=0.012; WCL1116 5.2/2, p=0.076), which is the Np/0p mismatch below. And with the baseline covariance the energy shapes in the muon-rich samples are in tension (WCL1116 preselection 22.4/8, p=0.004; `SB_numu` 16.4/8, p=0.04; old preselection 17.9/8; WCL1116 `SB_other` 25.1/8, p=0.0015, cosmic-rich, hypothesis only). These chi2 values change strongly with the neutron-G4 treatment (e.g. 10.3/8 and 9.2/8 including it). **Recommendation: keep them in the technical note, not in the talk.** Do not claim "the sidebands agree in shape".

# Proton multiplicity result

**Reconstructed Np/0p Data/MC double ratio** = (Np/0p)_data / (Np/0p)_MC, open data, event level (`np_over_0p_double_ratio_with_covariance.csv`, `control_region_summary_final.csv`). +- = stat + MC stat + baseline available covariance; in parentheses the including-tail-diagnostic uncertainty.

| region | old | WCL1116 |
|---|---|---|
| preselection | 0.82 +- 0.05 (0.28) | 0.80 +- 0.05 (0.29) |
| SB_numu | 0.81 +- 0.06 (0.35) | 0.80 +- 0.05 (0.40) |
| SB_ncpi0 | 0.67 +- 0.07 (0.08) | 0.75 +- 0.08 (0.08) |
| SB_other | 0.91 +- 0.08 (0.11) | 0.79 +- 0.07 (0.08) |
| SB_nue | 1.07 +- 0.37 (0.38) **stat-weak** | 0.54 +- 0.16 (0.16) **stat-weak** |

Counts behind it (data 0p / Np; MC 0p / Np): preselection old 4702 / 3778; 4355 / 4267. WCL1116 4568 / 3753; 4209 / 4338 (`np_over_0p_double_ratio_all_regions.txt`).

Interpretation (the whole claim): **MC predicts a larger reconstructed Np/0p than the open data across several populated control samples. WCL1116 does not remove it. It is not specific to NC-pi0 (preselection and the nu-mu-rich sample are CC-dominated and show ~0.8). It cannot yet be assigned to hadronic/proton-multiplicity modeling vs proton reconstruction/detector modeling, because no detector-variation samples are available.**

Significance: statistics only, the double ratio is 8-11 sigma below 1 in preselection/`SB_numu`; with the baseline covariance 3.3-4.2 sigma; with the neutron-G4 tail function included only 0.5-0.7 sigma. Because the answer depends on the unresolved function and detector/proton-reconstruction systematics are absent, **do not quote a significance**; quote the ratios and "about 20%".

**Truth -> reco migration (MC; `ncpi0_truth_reco_migration_{old_fg1,nov16}_all_resolved.csv`; all resolved MC (S+B) in the NC-pi0 sideband, row-normalised, truth = post-FSI primary protons > 35 MeV):**

| truth \ reco | old 0p / 1p / >=2p | WCL1116 0p / 1p / >=2p |
|---|---|---|
| truth 0p | 0.77 / 0.20 / 0.03 | 0.80 / 0.18 / 0.03 |
| truth 1p | 0.42 / 0.50 / 0.08 | 0.34 / 0.58 / 0.09 |
| truth >=2p | 0.34 / 0.34 / 0.33 | 0.28 / 0.35 / 0.38 |

Same MC events, old vs WCL1116 (`..._old_vs_nov16_same_events.csv`): truth 1p -> reco 0p 31% -> 26%; truth >=2p -> reco >=2p 41% -> 48%.

Exact inverse conditional (`ncpi0_P_truth_Np_given_reco.csv`): P(truth >=1 proton > 35 MeV | reco 0p) = **0.525 +- 0.011** (old), **0.446 +- 0.009** (WCL1116). I.e. nearly half of reco-0p events contain a >35 MeV proton, so reco topology is strongly migration-dominated; WCL1116 improves proton finding in MC but the data/MC mismatch persists.

Dense diagnostics (figures H, I): tested proton KE, proton track/first-segment length, number of segments, selected-shower energy, shower-vertex distance, detector position, pi0-pair mass, opening angle, energy asymmetry, leading/subleading shower energies, conversion gaps, shower dE/dx and dQ/dx, etc., per reco topology. **Conclusion: no stable kinematic shape discrepancy that explains the Np/0p normalization difference; not pi0 kinematics, not pair finding, not low-proton-KE edge.** (Per-panel statistics only, MC scaled to data per panel.)

# Systematics status

**Central values** (purity, efficiency) are unit-weight, POT-normalized. **No systematic "+-" is attached.** The weight study is a *preliminary available-neutrino-model relative uncertainty*, not "the systematic uncertainty".

Included in the **baseline available covariance (excluding unresolved reinteractions_neutron_Geant4 tail)**: flux; beamline Geant4 reinteractions (except the neutron function); GENIE cross section; GENIE FSI; cross-section extras. Coherent S/B universes, event-level, owner-interaction matching (unresolved-owner events held at nominal weight).

Shown **separately, outside the generic band**: NC-Delta signal-model dials `RDecBR1gamma`, `ThetaDelta2NRad`.

**Preliminary relative uncertainty on MC-only expected purity** (`syst_band_by_component.csv`, coherent per-universe; `TOTAL_*` views "all"):

| | baseline available covariance (excluding unresolved neutron-G4 tail) | including unresolved neutron-G4 tail diagnostic | the neutron function alone |
|---|---|---|---|
| old | **16.5%** | 17.5% | 5.9% |
| WCL1116 | **17.8%** | 20.3% | 9.8% |

Suggested wording: "Preliminary available-neutrino-model relative uncertainty on purity: 16.5% (old) / 17.8% (WCL1116) excluding the unresolved neutron-G4 tail; 17.5% / 20.3% when it is included diagnostically." (The older docs, e.g. `NCDELTA_FROZEN_SELECTION_PURITY_RESULTS.md`, phrase "+-20%" from 20.3%; that is the including-tail value for WCL1116 only.)

**Still missing (every one must be on the slide, or in a footer, whenever an uncertainty band is shown):** detector and proton-reconstruction variations; pure-cosmic / beam-off normalization (and a cosmic-only MC component in the control regions); POT; `rec.mc.nu.imp_weight`; unresolved-owner events (about 4-5% of the final-selection prediction, 3-18% of control-region predictions, held at nominal weight); dirt-specific uncertainty; the NC-Delta signal-model dials (separate).

**Neutron-G4 weight pathology** (`audit_neutron_g4_*.csv`, section 11 of `NCDELTA_SYSTEMATIC_WEIGHTS_FIRST_PASS.md`):
- `reinteractions_neutron_Geant4` is a 1000-universe multisim, heavy-tailed and event-dominated. Nothing was clipped or removed.
- Leading event: run 8011 / subrun 91 / evt 3, nu-mu NC RES, truth category NC_PI0, reco Np, 2 true neutrons; max weight **223,065**; weight > 100 in 161 / 1000 universes. It is the leading event in both productions (top-10 lists overlap by 6-7 events).
- Np-yield variance in preselection / `SB_numu`: 94-100% from one event (events for 50% and 90% of the variance: 1). 0p-yield variance is broad (hundreds of events).
- WCL1116 final-selection background yield variance: two events carry it (events for 50/90/99%: 1/2/2, top share 76%). Old final selection is broad (14/31/36).
- Not an association mistake: identity/vertex/PDG checks pass, and an unselected random sample of 3,586 generic BNB interactions has the same tail (1.0% above weight 10, 0.14% above 100).
- Prescription search: **no approved SBN treatment found.** A config declares `max_weight: 100`, but no source-established code path applying it to these CAF weights was found, and the CAFs contain weights up to 2.2e5. Excluding the function is **our analysis diagnostic choice, not an approved prescription and not an official rejection.** Question #5 to Haiwang/Hanyu.

**How to read the bars in the figures:**
- Figure F: *grey histogram* = MC prediction (S+B). *Black I-bar* = MC statistical only. *Orange bar* = MC statistical + baseline available covariance (the figure shows the baseline). The shaded band in the lower panel = the same (MC stat + baseline available covariance) as a data/MC band around 1; the black points = data/MC with data statistical bars. The "-1.6 sigma" text is the baseline; the "incl. unresolved neutron-G4 fn: -1.5 sigma" line is the diagnostic.
- Figure K: *thick bar* = data + MC statistics; *thin solid bar* = thick + baseline available covariance; *dashed bar* = including the unresolved neutron-G4 tail diagnostic. (Verified against the figure footer and `scripts/ncdelta_np_over_0p_summary.py`.)
- Figure G: *thick* = data + MC statistics; *thin* = + available neutrino systematics. **Its caption does not state which covariance** (the unsuffixed file is the baseline; `_incl_nG4` includes the tail function). Add that wording if G is shown.

# Data policy

Code gate: `configs/data_policy.yaml` + `src/sbnd_single_photon/datapolicy.py` (tests enforce it).
- `beam_on_open` (runs 18255, 18259; sum TotalPOT 4.62125e18): may be shown at **preselection and sidebands only**.
- **Final signal-region beam-on data: BLOCKED** until `signal_region.approved_by` carries a named approver and date (currently empty). Nothing in the final selection was opened for data in this work. The `datamc_*_final_frozen_*` plots print "data not shown (policy)" and are MC only.
- `run3bnb` (Run-3 beam-on): not designated open anywhere in the repo; blocked at every stage.
- Beam-off: may be shown as a shape, **never added to the stack**, because its scale is unresolved. Counts/control only.
- A historical shape note elsewhere in the repo (`docs/analysis/DATA_MC_SHAPES.md`) displayed 77 final-selection events from before the policy existed. **Do not reuse it.**
- **`rec.mc.nu.imp_weight`:** not 1 in the CAFs (mean ~0.185 in generic BNB CV, ~0.169 in the dedicated NC-Delta sample). It is **not applied** here. Unresolved whether it must multiply the event weight or is already covered by TotalPOT/sample-production conventions. The earlier ~9% S/B estimate was withdrawn; the hypothetical-weighted purity (`syst_imp_weight_hypothetical.csv`) is HYPOTHETICAL ONLY: do not show it as an alternative result. Not a main-slide item; footnote only.
- **Beam-off:** the main blocker to a physical purity. The question to the collaboration: should open-data beam-off be scaled by gate counters or recorded-trigger counts, and is the available run coverage appropriate? This is why every purity carries "MC-only expected purity - upper bound".
- No Aurora development BDT was evaluated on EAF or FermiGrid, on any sample, in this work.

# Plot inventory

All paths relative to the repo root, under `plots/ncdelta_purity_datamc/`. All are PNG; no PDFs exist. "Data" = MC only unless stated. Status key: MAIN / OPTIONAL / BACKUP / DO NOT USE.

| filename | what it is | data/MC | old / Nov16 | topology | uncertainty | data policy | status | slide | caveats |
|---|---|---|---|---|---|---|---|---|---|
| `A_cumulative_efficiency_purity_vs_stage.png` | efficiency, purity, yields vs stage (3 panels) | MC | both | inclusive | stat only | no data | **MAIN** (slide 1) | EAF-1 | x-label "n20br1 == 1 (final)" is jargon; footer says upper bound |
| `B_topology_purity.png` | purity by reco topology (1g0p/1g1p/>=2p) + stacked yields | MC | both | reco topology | stat only | no data | OPTIONAL | EAF-1 (or backup) | reco topology, not truth; ">=2p" is diagnostic; bin labels overlap the error bars |
| `C_efficiency_vs_purity_single_score.png` | one score varied at a time, others frozen | MC | both | inclusive | stat only | no data | BACKUP | - | descriptive, **not a threshold study**; do not present as optimization |
| `D_signal_background_composition.png` | stacked final composition | MC | both | inclusive | none | no data | OPTIONAL (strong for the "background grew" message) | EAF-1 | cosmic/unmatched here is BNB-CV MC, not beam-off; labelled purity 2.74/2.63% |
| `E_syst_first_pass_nov16.png`, `E_syst_first_pass_old_fg1.png` | first-pass per-function systematic breakdown (yield, per-bin fractional, purity bars) | MC | one each | inclusive + 0p/Np | "total (available)" **includes the neutron-G4 tail function** (not relabelled) | no data | **DO NOT USE** - superseded by the baseline/incl. numbers in this handoff (no replacement figure; use the table above) | - | its purity bars (e.g. 1g0p 22.8%) correspond to the including-tail total; wording predates the baseline/incl. split |
| `F_ncpi0_sideband_datamc_with_systematics.png` | NC-pi0-rich sideband, shower-energy data/MC, old and WCL1116 | **open beam-on data + MC** | both | inclusive | MC stat; baseline available covariance (excl. unresolved neutron-G4 tail) | sideband, allowed | **MAIN** (slide 2) | EAF-2 | see section below; figure text is small and carries internal names (`reinteractions_neutron_Geant4`); fine for a technical slide, consider cropping the title |
| `F_ncpi0_sideband_datamc_with_systematics_incl_nG4.png` | same, including the tail function | open data + MC | both | inclusive | incl. unresolved neutron-G4 tail diagnostic | allowed | BACKUP (for the neutron-G4 backup slide or Q&A) | - | wider error bars |
| `G_sideband_integrated_ratio_SB_ncpi0-SB_other-SB_nue.png` | integrated data/MC, 3 sidebands | open data + MC | both | inclusive | stat; baseline available syst | allowed | OPTIONAL / BACKUP | EAF-2 backup | caption does not say baseline; add wording; MC excludes cosmic-only |
| `G_sideband_integrated_ratio_SB_numu-preselection.png` | same for `SB_numu`, preselection | open data + MC | both | inclusive | same | allowed | BACKUP | - | same |
| `G_..._incl_nG4.png` (two) | including-tail versions | open data + MC | both | inclusive | incl. diagnostic | allowed | BACKUP | - | |
| `H_ncpi0_topology_variables.png` | analysis-table observables per reco topology, NC-pi0 sideband, shape-only | open data + MC | both | 0p / 1p / >=2p | stat only, MC scaled to data per panel | allowed | BACKUP only | - | dense; no detector/proton-reco systematics |
| `I_ncpi0_topology_reco_observables.png` | CAF-extracted observables (pi0 pair mass, opening angle, asymmetry, leading/subleading energies, conversion gaps, dE/dx, proton length/start, ...), 92 panels | open data + MC | both | 0p / 1p / >=2p | stat only | allowed | BACKUP only | - | dense; do not put on a main slide |
| `J_ncpi0_truth_reco_topology_migration.png` | row-normalised truth -> reco migration (all resolved MC, and truth-NC-pi0), old and WCL1116 | MC only | both | truth vs reco | stat only (weighted counts shown) | no data | BACKUP | EAF-4 / backup | truth = post-FSI primary protons > 35 MeV; the title quotes the same-event improvement (31% -> 26%, 41% -> 48%) |
| `K_np_over_0p_double_ratio_by_region.png` | Np/0p data/MC double ratio per region | **open data + MC** | both | Np/0p | thick: data+MC stat; thin: + baseline available covariance; dashed: incl. unresolved neutron-G4 tail | allowed | **MAIN** (slide 3) | EAF-3 | stat-weak `SB_nue`; detector/proton-reco and cosmic MC absent (footer says so) |
| `datamc_{old_fg1,nov16}_{preselection,SB_numu,SB_other,SB_ncpi0,SB_nue}_{inclusive,1g0p,1gNp}.png` (30 files) | 16-panel candidate-level data/MC stacks per region and topology | open data + MC | one each | per name | statistical only | allowed (index: `datamc_plot_index.csv`) | BACKUP | - | MC scaled to 4.62e18 POT; no beam-off stack; candidate-level (all region-passing candidates), not event-level; **no systematics** |
| `datamc_{old_fg1,nov16}_final_frozen_{inclusive,1g0p,1gNp}.png` (6 files) | same at the final selection | **MC only: "data not shown (policy)"** | one each | per name | stat only | signal region BLOCKED | **DO NOT USE** in the talk (MC-only shapes at the blocked stage; no new message) | - | never imply data were looked at |

Earlier plot directories: the pre-existing baseline presentation assets are listed in `docs/presentation/NCDELTA_BASELINE_SLIDE_ASSETS.csv` and `NCDELTA_BASELINE_PRESENTATION_OUTLINE.md` (from the earlier baseline/Round-1 work, not part of this package); I did not re-audit them here. Prefer this package for purity and data/MC.

## A_cumulative_efficiency_purity_vs_stage.png

Path: `plots/ncdelta_purity_datamc/A_cumulative_efficiency_purity_vs_stage.png`
**MAIN**
What it shows: left, cumulative signal efficiency (% of 12,427) per stage; middle, MC-only expected purity per stage (log); right, expected S and B yields per 1e20 POT. Old (blue) vs WCL1116 (orange).
Exact numerical takeaway: efficiency 6.70% -> 15.60%; purity 2.74% -> 2.63%; WCL1116 gains the most at the numu, other and ncpi0 stages (the stage table above).
Uncertainty shown: MC statistical only (no systematics).
Suggested slide title: "Efficiency improved, but the inherited purity did not."
Suggested caption: "Frozen MicroBooNE-BDT chain applied to old and WCL1116 reconstruction. MC-only expected purity (upper bound: no beam-off), statistical errors, per 1e20 POT, efficiency denominator 12,427 (TPC box)."
Speaker message: "The new reconstruction recovers more than twice the signal, but background grows by the same factor, so the inherited BDTs do not improve the purity."
Required caveats: MC-only upper bound; not a Round-2 result; statistical errors only.

## F_ncpi0_sideband_datamc_with_systematics.png

Path: `plots/ncdelta_purity_datamc/F_ncpi0_sideband_datamc_with_systematics.png`
**MAIN**
What it shows: NC-pi0-rich sideband (open beam-on data, frozen legacy chain, event level). Left old, right WCL1116. Top: selected-shower-energy distribution; grey = MC (S+B), black points = open data, black I-bar = MC statistical, orange bar = MC statistical + baseline available covariance. Bottom: data/MC with the combined band.
Exact numerical takeaway: Data/MC 0.76 (old) / 0.74 (WCL1116), 585 / 755 data vs 766 / 1020 MC; integrated deviation -1.6 / -1.8 sigma with the baseline covariance (-1.5 / -1.7 including the tail diagnostic); rate+shape chi2/ndof 6.2/8 and 9.9/8.
Uncertainty shown: MC statistical; baseline available covariance (excluding the unresolved neutron-G4 tail). The "incl." sigma is in the text box.
Suggested slide title: "The NC-pi0 rate deficit is within the available neutrino-model uncertainty."
Suggested caption: "Open-data NC-pi0-rich sideband, old and WCL1116. Band: MC statistics plus baseline available covariance (flux, GENIE cross section/FSI, beamline G4; excluding the unresolved neutron-G4 tail). Detector, cosmic/beam-off, dirt, POT and `imp_weight` are not included. PRELIMINARY."
Speaker message: "Data are about 25% below MC in the NC-pi0-rich sideband, but the available neutrino-model uncertainty alone is about 19%, so this is not a significant rate deficit - and the uncertainty budget is still incomplete."
Required caveats: the band must never be called "total systematic uncertainty"; list what is missing; do not call it resolved agreement; the energy bins show data/MC systematically below 1 at 0.6-0.8 within the band.

## K_np_over_0p_double_ratio_by_region.png

Path: `plots/ncdelta_purity_datamc/K_np_over_0p_double_ratio_by_region.png`
**MAIN**
What it shows: (Np/0p)_data / (Np/0p)_MC by control region, old (blue) and WCL1116 (orange). Labels on the points are the ratios.
Exact numerical takeaway: preselection 0.82 / 0.80; nu-mu-rich 0.81 / 0.80; NC-pi0-rich 0.67 / 0.75; other-rich 0.91 / 0.79; nu-e-rich 1.07 / 0.54 (stat-weak).
Uncertainty shown: thick bar = data + MC statistics; thin solid = + baseline available covariance (excluding unresolved neutron-G4 tail); dashed = including the unresolved neutron-G4 tail diagnostic (huge in preselection/nu-mu-rich because one event carries the Np variance).
Suggested slide title: "A reconstructed proton-multiplicity mismatch appears across several open control samples."
Suggested caption: "Data/MC double ratio of the reconstructed Np/0p ratio. PRELIMINARY. Detector and proton-reconstruction systematics, cosmic-only MC, dirt, POT and `imp_weight` not included."
Speaker message: "MC predicts systematically more reconstructed Np relative to 0p than the open data, about 20%. The effect survives the new reconstruction, but we cannot yet distinguish hadronic/proton-multiplicity modeling from proton reconstruction because detector variations are not available."
Required caveats: not NC-pi0-specific; no significance claim; `SB_nue` stat-weak; do not say "proton reconstruction is wrong" or "NC-pi0 has a proton problem".

## J_ncpi0_truth_reco_topology_migration.png

Path: `plots/ncdelta_purity_datamc/J_ncpi0_truth_reco_topology_migration.png`
**BACKUP**
What it shows: row-normalised truth (0p, 1p, >=2p post-FSI protons > 35 MeV) -> reco (1g0p, 1g1p, >=2p) matrices in the NC-pi0 sideband MC; four panels (old all-resolved MC, old truth-NC-pi0, WCL1116 all-resolved, WCL1116 truth-NC-pi0); numbers in parentheses are weighted counts.
Exact numerical takeaway: the all-resolved matrices and P(truth >=1p | reco 0p) = 0.525 +- 0.011 / 0.446 +- 0.009 (see above). Same-event improvement true 1p -> reco 0p 31% -> 26%.
Uncertainty shown: none beyond weighted counts; MC only.
Suggested slide title: "Reconstructed proton topology is migration-dominated."
Suggested caption: "MC truth -> reconstructed proton multiplicity, NC-pi0-rich sideband; truth = post-FSI primary protons > 35 MeV. Diagnostic; no detector systematics."
Speaker message: "Reco 0p/Np is strongly migration-dominated; WCL1116 improves proton finding in MC but does not eliminate the data/MC topology mismatch."
Required caveats: MC only; resolved owners only; do not claim that proton reconstruction inefficiency is demonstrated.

## Other recommended assets

- `D_signal_background_composition.png` (OPTIONAL, EAF-1): final composition stack. Takeaway: NC-pi0 background 427 -> 1162, outside-TPC 228 -> 721, CC-pi0 221 -> 346; signal 29 -> 68 per 1e20 POT. Caveat: "cosmic/unmatched" is BNB-CV MC.
- `B_topology_purity.png` (OPTIONAL): 1gNp 2.99% / 3.25% vs 1g0p 2.52% / 2.31%. Caveat: reconstructed topology.
- `G_*` (OPTIONAL/BACKUP) and `H`, `I`, `C` (BACKUP), as in the table.

# Suggested combined Aurora + EAF slide sequence

Short version (recommended), EAF slides follow the Aurora retraining slides:
1. **Aurora:** retraining result (development, nested validation: signal 27.1 -> 44.0% at essentially the same ~0.8% BNB acceptance; numbers from the Aurora handoff, not re-verified here).
2. **EAF-1** (merge with the Aurora summary or the reconstruction slide): "Efficiency improved, but inherited purity did not" - figure A (+ optionally D). 6.70 -> 15.60%; 2.74 -> 2.63% MC-only upper bound.
3. **EAF-2:** "Open-data controls constrain the background picture" - figure F. 0.76 / 0.74, within available neutrino-model uncertainty, with the missing list.
4. **EAF-3:** "A proton-multiplicity modeling discrepancy remains" - figure K.
5. **Backup:** J migration matrix; H/I diagnostics; F incl.; G; neutron-G4 audit numbers; topology purity B; C.
6. **Roadmap slide:** effective-boundary production -> final retraining -> freeze -> independent FermiGrid evaluation -> rerun this EAF package.

If time is very short: keep **F and K** (two slides) and put A's numbers in the text of the Aurora summary slide; merge Aurora retraining with A in one slide ("Reconstruction recovers the signal; SBND-specific retraining restores discrimination").

Transition wording: EAF frozen legacy chain: 6.70 -> 15.60% efficiency, purity ~unchanged at 2.6-2.7%. Aurora development retraining: 27.1 -> 44.0% signal at ~0.8% BNB acceptance. **These are different denominators and different questions: never compare 15.60% to 44.0% directly.** The link: improved reconstruction recovers the signal; SBND-specific retraining restores discrimination. The final purity after the retrained Round-2 models is still unknown.

# What not to say

- Do not call 2.63% (or 2.74%) the final Round-2 purity; do not say it includes beam-off.
- Do not call the available covariance "the systematic uncertainty" / "total systematic uncertainty"; do not call it "validated" or collaboration-approved; do not attach a "+-" systematic to the central purity.
- Do not say the neutron-G4 function was officially rejected; it is shown separately because no approved prescription was found.
- Do not say the NC-pi0 rate discrepancy is significant after systematics, and do not call it resolved either.
- Do not say the Np/0p discrepancy proves proton reconstruction inefficiency, or that it is specific to NC-pi0.
- Do not quote sigma values for the Np/0p double ratio.
- Do not show blocked signal-region beam-on data (or the `final_frozen` data/MC plots as if data were involved); do not reuse the old 77-event shape note.
- Do not show the hypothetical `imp_weight`-weighted purity.
- Do not imply Aurora DEV BDTs were evaluated on EAF/FermiGrid.
- Do not present figure C as threshold optimization; do not compare 15.60% with 44.0%.
- Do not feature the Nov16 preselection/`SB_numu` energy-shape chi2 (22.4/8, 16.4/8) in the talk.

# Current blockers

1. Beam-off normalization (gate counters vs recorded-trigger counts; run coverage).
2. `imp_weight` convention.
3. Effective-boundary / final reconstruction production status.
4. Detector-variation (or alternative-generator) samples for proton-multiplicity validation.
5. Approved SBN treatment of extreme `reinteractions_neutron_Geant4` weights.
6. Named approval for any signal-region data access (`signal_region.approved_by`).
7. Final collaboration-frozen upstream numu outputs and the reprocessed odd-run beam-off training half (Aurora side).

(Items 1-5 are the top-priority section of `docs/analysis/QUESTIONS_FOR_HAIWANG_HANYU.md`.)

# Final Round-2 sequence

1. Final effective/non-box-boundary reconstruction; collaboration-frozen upstream numu outputs; reprocessed/reverified odd-run beam-off training half.
2. Aurora: retrain all four BDTs -> nested validation -> freeze model, vertex choice, thresholds.
3. FermiGrid/EAF: apply the final frozen scores once -> efficiency -> purity -> 1g0p/1gNp -> backgrounds -> control regions -> data/MC -> final collaboration result (with beam-off scale, detector systematics and the neutron-G4 treatment resolved or explicitly carried).

# COPY/PASTE FACT SHEET

Safe to reproduce verbatim. Scope: frozen legacy chain, TPC-box denominator 12,427, per 1e20 POT unless stated.

- Efficiency: old **6.70%** (833/12,427); WCL1116 **15.60%** (1,938/12,427).
- Expected signal / 1e20 POT: 29.3 (old), 68.3 (WCL1116). Expected MC background: 1040.7, 2526.3.
- MC-only expected purity (upper bound): old **2.74 +- 0.18%** (stat); WCL1116 **2.63 +- 0.11%** (stat).
- Reco-topology purity: old 1g0p 2.52 +- 0.23%, 1g1p 3.74 +- 0.42%, >=2p 1.17 +- 0.25%, 1gNp 2.99 +- 0.29%; WCL1116 1g0p 2.31 +- 0.13%, 1g1p 3.75 +- 0.30%, >=2p 1.55 +- 0.26%, 1gNp 3.25 +- 0.23%.
- Final background (old / WCL1116): NC pi0 427 / 1162; outside-TPC neutrino 228 / 721; CC pi0 221 / 346; cosmic/unmatched (BNB MC) 48 / 92; other NC 48 / 81; nu-mu CC 52 / 55; nu-e CC 4 / 44; ambiguous 11 / 18.
- Open data: runs 18255/18259, 4.62e18 POT. Integrated Data/MC (old / WCL1116): preselection 0.98 / 0.97; `SB_numu` 1.00 / 1.01; `SB_other` 1.05 / 1.03; `SB_ncpi0` 0.76 / 0.74; `SB_nue` 0.99 / 0.92 (statistically weak).
- NC-pi0 sideband: 585 / 755 data vs 766 / 1020 MC; Data/MC 0.764 +- 0.148 / 0.740 +- 0.146 (baseline available covariance), -1.6 / -1.8 sigma; 0.764 +- 0.158 / 0.740 +- 0.154, -1.5 / -1.7 sigma including the unresolved neutron-G4 tail diagnostic. Shower-energy rate+shape chi2/ndof 6.2/8 and 9.9/8.
- Available (neutrino-model) relative rate uncertainty in the NC-pi0 sideband: 19.1% / 19.4% (baseline); 20.4% / 20.6% (incl.).
- Preliminary available-neutrino-model relative uncertainty on purity: **16.5% (old) / 17.8% (WCL1116)** excluding the unresolved neutron-G4 tail; **17.5% / 20.3%** including it diagnostically.
- Np/0p Data/MC double ratio (old / WCL1116): preselection 0.82 / 0.80; `SB_numu` 0.81 / 0.80; `SB_ncpi0` 0.67 / 0.75; `SB_other` 0.91 / 0.79; `SB_nue` 1.07 / 0.54 (stat-weak). "About 20% lower in data" (not NC-pi0-specific).
- P(truth >=1 proton > 35 MeV | reco 0p): 0.525 +- 0.011 (old); 0.446 +- 0.009 (WCL1116).
- Truth -> reco (all resolved MC, NC-pi0 sideband), rows truth 0p / 1p / >=2p, columns reco 0p / 1p / >=2p: old 0.77 0.20 0.03 / 0.42 0.50 0.08 / 0.34 0.34 0.33; WCL1116 0.80 0.18 0.03 / 0.34 0.58 0.09 / 0.28 0.35 0.38. Same MC events: true 1p -> reco 0p 31% -> 26%; true >=2p -> reco >=2p 41% -> 48%.
- `reinteractions_neutron_Geant4`: leading event run 8011 / subrun 91 / evt 3, max weight 223,065 (> 100 in 161 of 1000 universes); no approved SBN prescription found.
- Missing: detector/proton-reconstruction systematics, beam-off normalization, POT, `imp_weight`, unresolved-owner treatment, dirt, signal-model dials (separate).
- Aurora (from Avinay's brief; verify against the Aurora handoff): 27.1 -> 44.0% signal at ~0.8% BNB acceptance, nested validation, different denominator.
- Data policy: signal-region beam-on data not opened; `run3bnb` blocked; no Aurora development BDT evaluated on EAF/FermiGrid.
