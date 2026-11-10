# SPINE-compatible truth definition on the official Gen2 NC-Delta sample: harmonization report

Date: 2026-11-10. Branch `analysis/ncdelta-spine-harmonized-definition-20261110` (from the pushed differential-efficiency branch, 7a47eee).

> **This is NOT a Wire-Cell vs SPINE performance comparison.** It asks only: *how much does the efficiency of OUR frozen Wire-Cell baseline change when the truth denominator and the proton-topology definition are replaced by (the closest reproducible version of) the SPINE analysis's own?* The Wire-Cell reconstruction and selection are exactly the validated frozen baseline (policy `any` and `first`); only the truth events that make up the denominator change.
> No cut, threshold, policy or Wire-Cell decision was changed, and the SPINE headline efficiencies are deliberately **not** used anywhere in this document.

Provenance of the SPINE definition: `SPINE_SIGNAL_DEFINITION_SOURCE_AUDIT.md` (medulla fork `seokjuchung/medulla`, branch `feature/schung_NCDelta`, commit `4048f93`).
Implementation: `src/sbnd_single_photon/spine_def.py`, `configs/spine_signal_definition.yaml`, `scripts/spine_truth_scan.py`, `scripts/spine_harmonization.py`, `scripts/spine_reco_included_sensitivity.py`.
Detailed outputs (per-event flags, all tables): `$SP_DATA/spine_harmonization/official_ncdelta/` with `metadata.json` (git commit, manifest hash, truth-master hash, differential and SPINE truth-scan hashes, definition schema). Compact tables: `tables/spine_harmonization/`; figures: `plots/spine_harmonization/`.

## 1. Why the original headline efficiencies were incomparable

Our 8.12 % (truth 0p) and 10.69 % (truth 1p) are baseline efficiencies of the frozen MicroBooNE-derived BDT chain against a deliberately loose generator-level signal (Delta -> N gamma ancestry in the provisional TPC box, 35 MeV proton threshold, no containment, no photon-count or charged-particle requirement, categories 0p / 1p / >=2p). The SPINE analysis defines a different, much tighter signal (FV, containment, exactly one photon above 25 MeV, vetoes, 50 MeV proton threshold, channels 0p / Np) and a different reconstruction and selection. Dividing selected events by *different* truth sets makes the numbers measure different things even before any reconstruction difference. This report removes the denominator part of that difference for our chain only.

## 2. Technote definition (as given)

NC; Delta(1232); one true photon above 25 MeV; no true e, mu, charged pi above 25 MeV; GENIE final state of nucleons plus one photon; true-vertex FV |x|,|y| <= 180 cm, 10 <= z <= 450 cm; all final-state endpoints at least 5 cm inside the active volume; proton threshold 50 MeV; 1g0p / 1gNp.

## 3. Source implementation audit (summary)

Found: the public medulla branch above. Key facts (details and exact expressions in the audit document):
* The class "NC Delta -> N gamma" (`mc_category == 0`) and the event cut `has_nc_delta_ng_interaction` are defined on **`rec.mc.nu.prim`**, the same collection we have: `isnc`, a Delta-type `resnum` in {0, 6, 7, 9, 12, 13, 14, 15}, **exactly one photon above 25 MeV and every above-threshold primary a photon or a nucleon** (`mc_topology::only_photons_and_nucleons`; neutrons, pi0 at any energy and other species count as above threshold; sub-threshold e/mu/pi+-/p are ignored).
* "GENIE final state contains only nucleons and a single photon" is therefore **implemented as this thresholded rule on the post-FSI primaries**, not as a literal restriction of the GENIE record. The technote's threshold language and its final-state statement are two consequences of one source rule.
* FV, containment and the `neutrino2026_veto` are cuts on SPINE truth interactions/particles (including secondaries), not available in the flatCAF.

## 4. Active-volume and containment semantics

* **GDML (authoritative geometry, `sbndcode` `sbnd_v02_06.gdml`)**: two active TPC volumes (negative-x "East", positive-x "West" in the GDML naming), each 201.3 cm (x) x 407.46 cm (y) x 501.0 cm (z), meeting at the cathode x = 0: active x in [-201.3, 201.3], y in [-203.73, 203.73], z in [0, 501.0] cm. (This is why the CAF end points of exiting particles can reach 201.3 / 203.7 / 501.0.)
* **SPINE geometry (`sbnd_v2-6_geometry.yaml`)**: TPC boxes 201.4 x 400.015 x 501.315 cm, both TPCs in one *module*, i.e. in `module` mode the containment volume is the **detector outer box** x in [-201.6, 201.6], y in [-200.0075, 200.0075], z in [-0.1575, 501.1575]; the cathode is not an interior boundary unless a `cathode_margin` is set (production value not found).
* medulla's own constants (`GORE_WALL_*`): |x|, |y| = 200, z in [0, 500]; explicit fiducial distances 20/20/20/20/50/10 -> |x|,|y| < 180, 10 < z < 450.
* **Our containment ("flatCAF-primary containment approximation", never called SPINE containment)**: every non-neutrino primary that has visible deposits has its start and end point at least 5 cm inside the SPINE detector box. Because secondaries and spacepoints are not in the flatCAF, this is an approximation; four variants are quantified in section 9.

## 5. Official Gen2 implementation (our reproduction)

Named, separate boolean masks per event (`spine_def.masks`): `nc_delta_ancestry`, `spine_fv`, `spine_containment`, `spine_one_photon_25`, `spine_no_e_25`, `spine_no_mu_25`, `spine_no_charged_pi_25`, `spine_genie_final_state` (the source rule), `spine_genie_record_strict` (literal GENIE record), `spine_truth_signal`, `spine_truth_0p50`, `spine_truth_Np50`; variants `spine_technote_threshold` (A), `spine_technote_strict` (B, = headline), `spine_technote_strict_record` (B'), `spine_source_signal`, `spine_source_signal_veto2026`.
**Headline `spine_truth_signal` = B** = Delta ancestry & SPINE FV & containment (approx.) & one photon > 25 MeV & no e/mu/pi+- > 25 MeV & `only_photons_and_nucleons`. The source-only extras (Delta-type resnum set, neutrino2026 veto) and the literal-record variant are separate masks and are reported as variants; **nothing was silently chosen**.
Checks: the proton counts of the new scan equal the signal master for all 13,773 events; 9,151 flatCAFs, 0 read errors; the Delta ancestry is true for all events (our generator filter); the SPINE FV lies entirely inside the provisional TPC box; the one production-missing event is retained in every denominator it satisfies (it fails every numerator).

## 6. Denominator ladder (all 13,773 official events)

Cumulative (`denominator_ladder.csv`):

| step | events | fraction | 0p50 | Np50 | Delta0 | Delta+ |
|---|---|---|---|---|---|---|
| all official signal (filter box) | 13,773 | 1.000 | 7,375 | 6,398 | 7,599 | 6,174 |
| + NC Delta ancestry | 13,773 | 1.000 | 7,375 | 6,398 | 7,599 | 6,174 |
| + SPINE FV | 9,206 | 0.668 | 4,929 | 4,277 | 5,094 | 4,112 |
| + containment (flatCAF-primary approximation) | 8,945 | 0.650 | 4,834 | 4,111 | 4,970 | 3,975 |
| + exactly one photon > 25 MeV | 8,945 | 0.650 | 4,834 | 4,111 | 4,970 | 3,975 |
| + no e / mu / charged pi > 25 MeV | 8,771 | 0.637 | 4,794 | 3,977 | 4,883 | 3,888 |
| + only photons/nucleons above threshold (source rule) = **harmonized signal** | **8,668** | **0.629** | **4,764** | **3,904** | 4,823 | 3,845 |
| (source extra) + Delta-type resnum set | 8,634 | 0.627 | 4,761 | 3,873 | 4,801 | 3,833 |
| (source extra) + neutrino2026 veto (approx.) | 7,679 | 0.558 | 4,247 | 3,432 | 4,289 | 3,390 |

Each requirement alone (overlaps visible; the kept fraction of 13,773): SPINE FV 66.8 %; containment 79.9 % (literal all-primaries-incl.-neutrons 58.9 %; flatCAF `contained` flag 64.9 %; GDML box 81.2 %); **exactly one photon > 25 MeV 100 %, no e > 25 MeV 100 %, no mu > 25 MeV 100 %** (the sample is Delta-radiative filtered: a single hard photon and no leptons are automatic); no charged pion > 25 MeV 98.0 %; source rule `only_photons_and_nucleons` 96.9 %; literal GENIE-record final state (one status-1 photon, no pions) 83.9 %; `resnum == 0` 97.7 %; Delta-type resnum set 98.8 %; neutrino2026 veto 89.2 %; TPC box 90.2 %.
**Which definition changes matter numerically:** only the **FV** (-33 % of events) is large; containment (approximation) removes a further 261 events (-2.8 % of the FV sample), the charged-pion veto 174, the source final-state rule 103. The photon-count and lepton requirements remove nothing here. The literal GENIE-record reading would remove far more (1,835 records have two stable-final-state photons, 177 contain a pi0, 287 a charged pion) than the source's thresholded rule, which is why the choice was made explicit (B vs B').

**Strict vs threshold:** A (`spine_technote_threshold`) 8,771 events; B (`spine_technote_strict`, source rule) 8,668 (-103); B' (literal GENIE record) 7,554 (-1,114 relative to B). All three give frozen efficiencies within 10.8-11.0 % (section 9).

## 7. FV effect: current TPC box vs SPINE FV

| region | events | frozen WC final efficiency (any) | candidate efficiency |
|---|---|---|---|
| in both (TPC box and SPINE FV) | 9,206 | 10.57 % (973) | 96.0 % |
| current-only (TPC box, outside SPINE FV) | 3,221 | 5.59 % (180) | 77.5 % |
| SPINE-only | **0** (the SPINE FV is a subset of the TPC box) | -- | -- |
| neither (filter box, outside both) | 1,346 | 1.41 % (19) | 45.1 % |

This is descriptive only; no FV choice is proposed. (`first`: 10.06 % / 5.43 % / 1.41 %.)

## 8. 35 vs 50 MeV proton topology (harmonized denominator, 8,668 events)

| | 0p50 | Np50 | row total |
|---|---|---|---|
| 35-MeV truth 0p | 4,185 | 0 | 4,185 |
| 35-MeV truth 1p | 500 | 3,294 | 3,794 |
| 35-MeV truth >=2p | 79 | 610 | 689 |

500 of 3,794 truth-1p events (13.2 %) become 0p50, and of the 689 >=2p events 79 become 0p50 and 199 have exactly one proton above 50 MeV (411 keep >= 2). Topology fractions: 35 MeV: 0p 48.3 %, 1p 43.8 %, >=2p 7.9 %; 50 MeV: 0p50 55.0 %, Np50 45.0 %. (Truth 0p at 35 MeV is always 0p50.) The leading-proton-KE distribution around 35-75 MeV is `plots/spine_harmonization/leading_proton_ke_35_75.png`. This is a threshold-migration view, not an optimisation.

## 9. Frozen Wire-Cell efficiency on the harmonized signal

**Same Wire-Cell reconstruction and selection; different truth denominator.** (exact Clopper-Pearson 68 %)

| denominator | N | final `any` | `first` |
|---|---|---|---|
| loose official, filter box | 13,773 | 8.51 % [8.27, 8.75] | 8.13 % |
| **loose official, provisional TPC box (current baseline)** | 12,427 | **9.28 %** [9.02, 9.55] | 8.86 % |
| SPINE FV only | 9,206 | 10.57 % [10.25, 10.90] | 10.06 % |
| A: technote threshold topology | 8,771 | 10.82 % [10.49, 11.16] | 10.28 % |
| **B: HARMONIZED ALL** | 8,668 | **10.93 %** [10.59, 11.27] | 10.38 % |
| **harmonized 0p50** | 4,764 | **9.38 %** [8.96, 9.83] | 8.77 % |
| **harmonized Np50** | 3,904 | **12.81 %** [12.27, 13.37] | 12.35 % |

Context (loose TPC box, 35-MeV classes): truth 0p 8.12 %, truth 1p 10.69 %, truth >=2p 8.24 % (`any`).
Region x proton-class matrix (`any`; `region_x_protonclass_efficiency.csv`):

| class | loose TPC box | harmonized |
|---|---|---|
| 35 MeV: 0p / 1p / >=2p | 8.12 / 10.69 / 8.24 % | 9.58 / 12.68 / 9.43 % |
| 50 MeV: 0p50 / Np50 | 7.91 / 10.86 % | 9.38 / 12.81 % |

So the **region/definition change moves each class by about +1.2 to +2.0 pp, whereas moving the proton threshold from 35 to 50 MeV changes a class's efficiency by only about -0.2 to +0.2 pp** (e.g. loose 0p 8.12 -> 7.91, harmonized 9.58 -> 9.38).
**Sensitivity of the headline to each ambiguous piece** (`sensitivity_variants.csv`; each variant changes one piece of the harmonized mask; all / `any`): containment literal (all primaries incl. neutrons) 11.44 %; containment by the flatCAF `contained` flag 11.34 %; GDML active box 10.91 %; no containment 10.78 %; FV with the medulla docstring margins 11.15 %; `resnum == 0` 10.94 %; Delta-type set 10.92 %; literal GENIE record 11.04 %; with the neutrino2026 veto 11.01 %; without any final-state restriction 10.82 %. **Every variant lies within 10.8-11.4 %**, so the harmonized efficiency is robust against the unresolved pieces of the definition to about +-0.3 pp.

## 10. 0p50 / Np50 truth-to-reco migration (frozen selection, 50-MeV reco projection)

Reco 0p50 / Np50 is a mechanical **SPINE-comparison reco projection** of the existing frozen selection (the single-photon cuts do not use proton multiplicity): reco Np50 if the candidate's leading proton row has KE > 50 MeV. It does not replace the 35-MeV categories and is not a new selection. Baseline row convention (every proton row counts, `kine_energy_included` ignored).

| stage | truth | reco 0p50 | reco Np50 | no selected/matched candidate |
|---|---|---|---|---|
| signal-matched candidate | 0p50 (4,764) | 3,385 (71.1 %) | 978 (20.5 %) | 401 (8.4 %) |
| signal-matched candidate | Np50 (3,904) | 1,219 (31.2 %) | 2,479 (63.5 %) | 206 (5.3 %) |
| final frozen selection (any) | 0p50 | 387 (8.12 %) | 60 (1.26 %) | 4,317 (90.6 %) |
| final frozen selection (any) | Np50 | 66 (1.69 %) | 434 (11.12 %) | 3,404 (87.2 %) |

Among the selected events: truth 0p50 -> reco 0p50 387 / 447 = 86.6 %, reco Np50 13.4 %; truth Np50 -> reco Np50 434 / 500 = 86.8 %, reco 0p50 13.2 %. Qualitatively this matches the 35-MeV matrix on the same denominator (truth 0p -> reco 0p 8.48 %, 1p -> reco 1p 10.12 %, 1p -> reco 0p 1.98 %, 0p -> reco 1p 1.08 %, exact counts in `migration_35mev_on_same_denominators.csv`): moving to 50 MeV does not change the picture, only the labels.
**`included == 3` policy sensitivity (not a policy choice):** counting only `kine_energy_included == 1` proton rows moves 58 of the 1,172 selected events between reco 0p50 and Np50 (truth 0p50 -> reco 0p50 415 instead of 387; truth Np50 -> reco Np50 411 instead of 434).

## 11. Differential comparison (`differential_loose_vs_harmonized.png`)

On the same figure: loose TPC box vs harmonized (and its 0p50 / Np50 subsets) for photon energy, photon angle, vertex z and (Np50) leading proton KE.
* **The strong energy and angular trends are intrinsic to the frozen selection, not produced by the loose denominator.** Harmonized efficiency vs photon energy rises from 2.7 % (50-100 MeV) to 17.6-17.8 % (> 400 MeV) (loose: 2.4 % to 14-15 %), vs cos(theta) from 3.2 % to 15.5 % (loose 3.0 % to 12.8 %); the last-to-first bin ratio is 6.4 (loose 6.2) for energy and 4.9 (loose 4.3) for angle.
* The harmonized selection is higher by about 10-25 % (relative) for photon energies above 200 MeV and forward angles, essentially unchanged below 150 MeV; the visible differences come from removing the detector edges (SPINE FV).
* **Vertex z:** the loose sample shows the drop in the last bin (4.4 % at 450-500 cm); inside the SPINE FV (z < 450) the efficiency is flat (9-13 %), consistent with the edge effect of the previous study.
* **Np50 vs leading proton KE:** 8.0 % (50-75 MeV), 12.5 % (75-100), 12.2 % (100-150), 15.8 % (150-200), **18.6 % (200-300)**, 12.5 % (300-500), 7.4 % (> 500 MeV): the same rise-then-fall shape as for the 35-MeV truth-1p events.

## 12. What is now comparable

The truth signal definition (topology exactly, FV exactly for the technote values, proton threshold and channels exactly, containment approximately), the 50-MeV channel projection of our selection, the sample truth event keys, and our own definition-only efficiency effects: the Wire-Cell frozen efficiency on the harmonized denominator is 10.93 % (any), 0p50 9.38 %, Np50 12.81 %, i.e. **+1.65 pp relative to the loose TPC-box baseline and +2.4 pp relative to the loose filter-box sample, from the denominator definition alone** (FV +1.3 pp, containment +0.15, charged-particle veto +0.1, strict final state +0.1).

## 13. What is still NOT comparable

* The reconstruction, the interaction/candidate policy, the final selection working point, the channel-specific BDTs and the cosmic/flash treatment of the SPINE chain (we have none of their outputs).
* The exact SPINE truth containment (secondaries, spacepoints, production margins), the SPINE `neutrino2026_veto` (only approximated here), and whether the technote's numbers include it.
* The efficiency definition of the SPINE quote itself.
* The remaining difference between our harmonized numbers and any SPINE number cannot be attributed to reconstruction quality from this study; **this study does not explain the full Wire-Cell / SPINE difference**.

## 14. Requirements for the same-event SPINE benchmark

See `SPINE_COMPARISON_REQUIREMENTS.md` (section C): the same Gen2 events through SPINE keyed by `(run, subrun, evt)` (the per-event harmonization flags are the join table), SPINE outputs and policy, the SPINE working point, a stage mapping, a common cosmic/flash treatment, systematics, and the proton-row convention. Open questions for the technote author: which medulla commit and TOML (with or without `neutrino2026_veto`, Delta(1232) vs the Delta-type set), the production containment/fiducial settings, and the efficiency definition.
