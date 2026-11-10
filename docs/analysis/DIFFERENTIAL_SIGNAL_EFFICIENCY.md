# Differential efficiency of the frozen baseline on the official NC-Delta signal

Date: 2026-11-10. Branch `analysis/ncdelta-differential-efficiency-20261110` (from 1075016). **Characterisation only: nothing was tuned, no cut/threshold/policy/region was changed, no recommendation is made.**
Every number is a *baseline* efficiency of the frozen MicroBooNE-derived BDT chain against a loose generator-level signal definition, not a final-analysis efficiency.

Reproduce: `python scripts/differential_truth_scan.py scan && ... merge` (truth extras, once), `python scripts/differential_natural_cv_truth.py`, `python scripts/differential_efficiency.py`.
Numerical tables (bin edges, numerators, denominators, efficiencies, uncertainties, first-failure accounting): `$SP_DATA/differential_efficiency/official_ncdelta/tables/` (outside Git) with `metadata.json` (git commit, manifest hash, truth-master hash, region config, threshold, policy, schema version).
Small committed summary: `tables/differential_efficiency/summary.json`. Figures: `plots/differential_efficiency/`. Bin edges (fixed a priori, never tuned): `configs/differential_bins.yaml`.

## 1. Scope

* Sample: official Gen2 `EX_ncdeltarad`, fg1-compatible Wire-Cell merged CAFs. Policy `any` (`first` quoted for the final stage only). Proton threshold 35 MeV (provisional). No FV.
* Three quantities are always kept apart (formal definitions in `src/sbnd_single_photon/differential.py`):
  **cumulative efficiency** = N(pass every stage up to s) / N(truth denominator);
  **conditional survival** = N(pass s) / N(reached s);
  **first-failure fraction** = N(first failing stage is r) / N(truth denominator), summing to 1 over the 11 mutually exclusive categories including `selected`.
* Plots do not draw bins with fewer than 10 events in the (reaching-stage) denominator; every bin remains in the tables. Error bars are exact Clopper-Pearson 68 % intervals. No data, beam-off, normalisation or systematics appear anywhere in this phase.
* Plot style/layout infrastructure for later data/MC figures (upper panel, optional ratio panel, reserved hatched systematic band, provenance line, fixed colour per stage/group): `src/sbnd_single_photon/plotstyle.py` (infrastructure only).

## 2. Official signal denominator

| | events |
|---|---|
| filter box (generator phase space) | 13,773 (production-represented 13,772; one missing: run 317 / subrun 41 / event 6753) |
| provisional TPC box (working region) | **12,427**: truth 0p 5,863 / 1p 5,557 / >=2p 1,007; Delta0 6,846 / Delta+ 5,581 |
| selected (policy any) | 1,153 = 9.28 % ; policy first 1,101 = 8.86 % |
| by truth class (final any) | 0p 476 (8.12 %), 1p 594 (10.69 %), >=2p 83 (8.24 %) |

The missing event is in the denominator and fails every numerator (first failure `missing_from_merged_caf`). The exclusive first-failure categories for the 12,427 events (integrated):
no candidate 1,095 (8.8 %); no >20 MeV shower 3,251 (26.2 %); BDT not evaluable 46 (0.4 %); fail numu 3,030 (24.4 %); fail other 2,226 (17.9 %); fail ncpi0 1,465 (11.8 %); fail nue 0 (the cut is inactive); fail n_20br1 160 (1.3 %); selected 1,153 (9.3 %); missing 1; wc.invalid 0. These are the same stage counts as the validated baseline (12,427 -> 11,331 -> 8,080 -> 8,034 -> 5,007 -> 2,781 -> 1,313 -> 1,153).

## 3. Variable definitions

All from truth, all with no containment requirement.
* **True photon energy**: energy of the signal neutrino's primary photon of maximum energy (= the Delta-radiative GENIE-record photon; the only primary photon above 20 MeV in all 12,427 events). Median 273 MeV, mean 294 MeV; 0-50 MeV bin holds 4 events.
* **cos(theta_gamma, beam)**: photon `genp` direction against the +z axis. The true neutrino direction is within about 0.06 rad of +z in this sample (z-component >= 0.998 for every event); |cos(gamma, +z) - cos(gamma, true nu direction)| <= 0.049 for every event, so the choice is immaterial for the trends below.
* **True neutrino energy**, **true vertex** (x, y, z), **Delta charge** (2114 = Delta0, 2214 = Delta+), **truth proton class** 0p / 1p / >=2p (post-FSI `prim` protons with KE > 35 MeV; no containment).
* **Leading / subleading truth proton KE**, number of protons above 35 MeV and in total, highest KE below 35 MeV (all stored in `truth_extra.parquet`).
* **True conversion distance**: `docs/analysis/PHOTON_CONVERSION_DISTANCE_DEFINITION.md` (defined for 11,512 events = 92.6 % of the TPC box; the rest is reported as `other_interaction` 220 / `left_volume` 695).
* **Detector sides**: labelled **negative-x side** (x < 0) and **positive-x side** (x >= 0) of the detector coordinate system. They are **not** called TPC0/TPC1: that mapping is not established from source in this work.

## 4. Photon-energy dependence (`eff_*_vs_photon_energy_mev.png`, `survival_vs_photon_energy_mev.png`, `firstfail_vs_photon_energy_mev.png`)

* **Observation:** the final efficiency rises monotonically from 2.4 % (50-100 MeV) to about 15 % above 400 MeV (4.4 % at 150-200, 9.2 % at 250-300, 12.3 % at 300-400, 14.7 % at 400-500, 15.0 % above 700 MeV); the 0-50 MeV bin has 4 events (0 selected).
* The >=1-candidate cumulative efficiency is almost flat: 87 % (50-100 MeV), about 91 % from 100 MeV, 93 % above 700 MeV.
* The **>20 MeV shower** stage is where the energy dependence starts: cumulative 47 % (50-100), 58 % (150-200), 65 % (250-300), 72 % (400-500), ~76 % (> 500 MeV). It never exceeds ~76 % even at high energy, i.e. there is an energy-independent loss of roughly a quarter of the events at this stage in addition to the low-energy loss.
* The numu stage has an essentially flat conditional survival (about 0.55-0.67 across 100-600 MeV); the **`other`** stage has a strongly energy-dependent conditional survival (all signal: from about 0.2-0.4 at 100-200 MeV to 0.76-0.8 at 500 MeV and above, see section 11).
* First-failure map (fractions of the denominator): `no >20 MeV shower` falls from 40 % (50-100 MeV) to 17-18 % (> 500 MeV); `fail other` peaks at 21-23 % for 100-250 MeV and falls to 9 % above 500 MeV; `fail numu` rises slowly from 21 % to 32-34 % above 500 MeV and is then the largest category; `fail ncpi0` rises from 6-7 % (< 200 MeV) to 16-17 % (400-700 MeV); `fail n_20br1` rises from < 1 % (< 200 MeV) to 4-7 % (> 500 MeV); `no candidate` is 9 % (13 % at 50-100 MeV). The selected fraction saturates at about 15 %.
* No dependence is claimed to be causal: the stage at which the efficiency changes is a descriptive statement (section 15).

## 5. Photon-angle dependence (`*_vs_cos_theta_beam.png`)

* **Observation:** the final efficiency rises from 3.0 % (cos in [-1,-0.75]) to 12.8 % (cos in [0.75,1]); >20 MeV shower cumulative from 57 % to 71 %; the candidate efficiency is flat (88-92 %).
* **Confound checked:** photon energy and angle are strongly correlated (Spearman 0.72; 0p median cos 0.56, 1p 0.46). In 3 x 3 bins (energy: <200, 200-300, >300 MeV; cos: <0, 0-0.5, >0.5) the final efficiency still increases with cos inside each energy band (energy <200: 2.9 % -> 5.9 % -> 6.9 %; 200-300: 5.9 -> 8.7 -> 9.1 %; >300: 7.2 -> 11.3 -> 13.7 %; the backward >300 MeV cell has only 83 events), and increases with energy inside each angular band. So the two one-dimensional trends are not simply a copy of each other; they are not separated into independent causes either.
* **Not interpreted as detector acceptance.** The vertex dependence (section 7) shows an edge effect, but the angular trend is also present in an interior diagnostic box (|x|,|y| < 150 cm, 50 < z < 450 cm; final efficiency by cos bin 5.0 % / 10.6 % / 14.9 %). That box is a descriptive device and is not a proposed FV.

## 6. Conversion-distance dependence (`*_vs_conv_distance_cm.png`, `eff_by_photon_end_class.png`, `reco_gap_and_true_conversion.png`)

True conversion distance is defined from the Geant4 end point of the primary photon (document above). Results for the 11,512 converted photons:
* **Observation:** candidate efficiency is flat at about 93-94 % up to 75 cm (91 % at 100-150 cm; <= 10 events beyond). The final efficiency is 9.8 / 12.0 / 9.7 / 9.5 / 9.9 % in bins [0,5), [5,10), [10,20), [20,30), [30,50) cm, then 6.9 % (50-75, 639 events), 10.4 % (75-100, 183) and 4.6 % (100-150, 65): approximately flat to 50 cm with a lower, statistically weak tail beyond. BDT-evaluable cumulative: 69.5 % (< 5 cm) -> 67 % (50-75) -> 60 % (100-150).
* By Geant4 fate of the photon (all signal): `conv` candidate 93.7 %, final 9.9 % (1,145 / 11,512); `other_interaction` (phot / photonNuclear) candidate 93.2 %, final 3.6 % (8 / 220); **`left_volume` candidate 48.9 %, final 0 / 695**. Exact TPC-box accounting of the signal-photon fate (N = 12,427): 11,512 (92.6 %) undergo an in-volume pair conversion; 695 (5.6 %) leave the active volume and **none** of those 695 events pass the final frozen selection; 220 (1.8 %) terminate through another contained interaction (photoelectric or photonuclear) and 8 of those 220 pass. The combined 915 events (7.4 %) are *events without an in-volume pair conversion*; only the 695 are photons that leave the volume.
* Reco shower-to-vertex distance (`shw_sp_shw_vtx_dis`; a reco diagnostic, **not** truth): for signal-matched candidates (n = 7,790, shower filled) the median is 0 cm, the 84 % quantile 25.8 cm and 36 % exceed 5 cm; for the final selected candidates (n = 1,153) median 0, 84 % quantile 21.9 cm, 44 % above 5 cm. Its rank correlation with the true conversion distance is only 0.14 (matched candidates of converted photons): the reco gap is not a measurement of the true conversion distance.

## 7. Vertex dependence (`*_vs_vtx_{x,y,z}.png`, `detector_sides.csv`, `efficiency_interior_vs_edge.csv`)

* **Observation:** the final efficiency is roughly flat in the interior and falls at the edges. x: 8.5 / 9.7 / 9.3 / 8.8 / 10.1 / 11.2 / 9.5 / 6.4 % for the eight 50 cm bins from -200 to +200; y: 5.4 / 7.8 / 12.0 / 11.5 / 10.8 / 9.9 / 9.7 / 5.7 %; z (ten 50 cm bins): 9.3, 10.9, 8.6, 9.3, 9.6, 10.2, 9.8, 11.6, 8.8 and **4.4 % in 450-500 cm**.
* The edge loss starts at the candidate stage: candidate efficiency 82-86 % in the outermost x and y bins (vs ~94 %) and 71 % in z 450-500 cm; the >20 MeV shower stage follows (55 % in the outer x bins vs ~69 % in the interior).
* Interior diagnostic box (|x|,|y| < 150 cm, 50 < z < 450 cm; 6,032 events) vs the complement (6,395 events): candidate 97.1 % vs 85.6 %, final 11.41 % (688) vs 7.27 % (465). In the interior the truth classes are 0p 9.95 %, 1p 13.41 %, >=2p 8.87 %.
* Photons that leave the active volume (section 6) are concentrated at the edges; this is a plausible contributor to the edge loss but its share was not quantified.
* **Detector sides:** negative-x side 632 / 6,948 = 9.10 %, positive-x side 521 / 5,479 = 9.51 % (Fisher p = 0.44). The count asymmetry (632 vs 521 selected) mirrors the asymmetry of the denominator (6,948 vs 5,479 generated events), not an efficiency asymmetry. Truth-1p efficiency: 10.07 % (negative-x) vs 11.49 % (positive-x), about 1.9 sigma; truth-0p 8.43 % vs 7.74 %.

## 8. Neutrino-energy dependence (`*_vs_nu_energy_gev.png`)

* **Observation:** a mild dependence. Final efficiency (all signal): 6.2 % (0.25-0.5 GeV), 8.3, 9.8, 10.0 % (1-1.5 GeV), 8.3 % (1.5-2 GeV), 11.6 % (2-3 GeV), 5.9 % (3-5 GeV, 203 events). Truth 1p is above truth 0p in almost every bin (e.g. 12.6 % vs 7.6 % at 0.75-1 GeV; 11.0 vs 9.4 % at 1-1.5 GeV). The candidate efficiency rises slightly from 87 % (0.25-0.5 GeV) to 92 %.
* This is a descriptive plot of the standard kind; it must not be numerically compared with numuCC / nueCC efficiencies (different signal definitions).

## 9. Proton-KE dependence and 0p / 1p migration (`eff_*_vs_lead_proton_ke_mev.png`, `migration_truth1p_vs_lead_proton_ke.png`, `migration_truth0p_vs_sub35_proton_ke.png`)

Truth-1p events, versus the leading truth proton KE (bins from the provisional 35 MeV threshold; the threshold is shown as a reference only):
* Final efficiency of truth-1p events: 6.6 % (35-50 MeV), 7.2 % (50-75), 11.5 % (75-100), 11.1 % (100-150), 13.5 % (150-200), 16.0 % (200-300), 10.0 % (300-500), 6.1 % (>=500 MeV). **For protons just above the threshold the efficiency (6.6-7.2 %) is below the truth-0p average (8.12 %).** The candidate efficiency follows the same low-KE deficit (88 % at 35-75 MeV vs 94-96 % above); the >20 MeV shower survival decreases for KE > 200 MeV (about 62-68 % -> 55 %).
* Reco category of the **signal-matched candidate** (fraction of truth-1p events; the remainder is no matched candidate): reco 0p 47 % at 35-50 MeV, falling to 19 % at 200-300 MeV, rising again to 37 % above 500 MeV; reco 1p 30 % (35-50), 38 % (50-75), 50-58 % at 75-500 MeV, 32 % above 500 MeV; reco >=2p 5-8 % up to 200 MeV, 16-18 % at 200-500 MeV, 25 % above 500 MeV; no matched candidate 16-17 % at low KE, about 7 % above 150 MeV.
* At the **final** stage (fractions of all truth-1p events): selected as reco 1p 3.2 % (35-50 MeV), 5.0 %, 10.1 %, 9.0 %, 12.6 %, 13.5 % (200-300), 7.6 % (300-500), 3.8 % (>500 MeV); selected as reco 0p only 0.3-3.4 % in all bins (truth 1p -> reco 0p is highest, 3.4 %, in the lowest-KE bin).
* **Truth-0p versus the highest sub-threshold truth proton KE:** at the matched-candidate stage the reco-1p fraction is 15.8 % for truth-0p events with **no** true proton at all, and 14.1 / 12.4 / 12.3 / 13.9 / 16.6 / 19.4 / 25.4 % in the bins 0-5 ... 30-35 MeV of the highest true sub-threshold proton KE. Reco-1p creation therefore is present at ~13-16 % without any true proton and rises only in the top bin (30-35 MeV, 25 %, n = 327). At the final stage selected-as-reco-1p is 0.3-1.8 % in all bins.
* **Where migration develops:** truth 1p -> reco 0p is large at the candidate stage for the lowest-KE protons (consistent with a reco proton-row threshold close to the truth threshold) and also for protons above 500 MeV; truth 0p -> reco 1p exists independently of a sub-threshold proton. Only correlations are shown; the proton-row association is not available (section 13).

## 10. First-failure maps (`firstfail_vs_*.png`, `first_failure_differential.csv`)

Fractions of the original denominator, exactly closing in every bin (asserted per bin in the code and in `tests/test_differential.py`).
* The dominant exclusive first-failure mechanisms integrated over the sample are: no >20 MeV shower (26.2 %), fail numu (24.4 %), fail other (17.9 %), fail ncpi0 (11.8 %), no candidate (8.8 %).
* Phase-space dependence: `no >20 MeV shower` falls with photon energy (40 % -> 17 %) and with forward angle (36 % at cos -0.75..-0.5 -> 20 % at cos > 0.75); `fail other` is largest for backward photons (26 % at cos < -0.75 vs 15 % at cos > 0.75) and at 100-250 MeV; `fail ncpi0` and `fail n_20br1` grow with energy and forward angle (ncpi0 8 % -> 16 %, n_20br1 0 % -> 2 % across cos); `fail numu` is nearly flat (19-26 %) in angle and position. At the downstream edge (z 450-500 cm) `no candidate` jumps from 5-9 % to 29 %. Photons that leave the volume fail at `no candidate` (51 %) or `no >20 MeV shower` (43 %); for converted photons the largest categories are numu (26 %), no >20 MeV shower (25 %) and other (19 %). In the conversion-distance bins `no >20 MeV shower` is flat at 24-26 % up to 100 cm.
* The first-failure fractions are order-dependent (a stage's loss is counted only for events that passed all earlier stages); use the conditional survival (section 11) when comparing stages.

## 11. 0p versus 1p (`decomposition_0p_vs_1p.png`, `standardisation_0p_vs_1p.csv`, `adjusted_0p_vs_1p.csv`, `distributions_0p_vs_1p.csv`)

Integrated: truth 0p 8.12 %, truth 1p 10.69 %: difference +2.57 +- 0.56 percentage points; ln(eps_1p / eps_0p) = 0.275.

**Stage decomposition (observed; exactly additive in the log):** cumulative and conditional rates (0p / 1p):

| stage | cumulative 0p / 1p | conditional survival 0p / 1p | contribution to ln(eps_1p/eps_0p) (68 % bootstrap) | share |
|---|---|---|---|---|
| >=1 candidate | 0.889 / 0.930 | 0.889 / 0.930 | +0.046 (0.040, 0.052) | 17 % |
| >20 MeV shower | 0.675 / 0.624 | 0.759 / 0.671 | **-0.124** (-0.136, -0.110) | -45 % |
| BDT evaluable | 0.671 / 0.620 | 0.995 / 0.994 | -0.001 | 0 % |
| numu | 0.417 / 0.391 | 0.621 / 0.631 | +0.015 (-0.004, 0.031) | 5 % |
| **other** | 0.197 / 0.247 | **0.473 / 0.632** | **+0.289** (0.261, 0.319) | **105 %** |
| ncpi0 | 0.098 / 0.116 | 0.496 / 0.471 | -0.052 (-0.087, -0.013) | -19 % |
| n_20br1 | 0.081 / 0.107 | 0.829 / 0.918 | +0.102 (0.082, 0.124) | 37 % |

* The integrated difference **develops at the `other` stage** (conditional survival 47.3 % vs 63.2 %); `n_20br1` adds a smaller positive contribution and the candidate stage a small one. The **numu** stage contributes essentially nothing (consistent with the earlier finding). Truth 1p loses *more* at the >20 MeV shower stage (67.1 % vs 75.9 % survival), a negative contribution that partially offsets the positive ones.
* The `other` conditional survival, by photon energy (bins from 50-100 MeV; truth 0p vs truth 1p): 23 vs 41 %, 10 vs 42 %, 22 vs 45 %, 34 vs 60 %, 46 vs 60 %, 58 vs 70 %, 66 vs 79 %, 76 vs 81 %, 73 vs 83 %. The gap is large at low and intermediate energies and shrinks above ~500 MeV.
* **Kinematics does not explain it.** The 0p photons are on average slightly harder (mean 300 vs 291 MeV) and more forward (median cos 0.56 vs 0.46), which should favour truth 0p; the vertex-position and conversion-distance distributions are identical (KS p = 0.65, 0.49, 0.52, 0.72 for x, y, z, conversion distance); the conversion-class composition is similar (left volume 5.2 % vs 6.2 %). Re-weighting truth 0p to the 1p distribution of photon energy changes its efficiency from 8.12 % to 7.63 % (to 7.54 % for cos, 8.12-8.13 % for nu energy and vertex); logistic-regression adjustment for photon energy, cos, nu energy and the vertex leaves the 1p - 0p difference at +3.0 to +3.2 pp (68 % interval about +-0.5 pp), larger than the raw 2.57 pp.
* **Observed correlation, not a demonstrated mechanism.** What is established: the efficiency difference between truth classes is not due to different distributions of photon energy, angle, neutrino energy, vertex, or conversion distance, and is concentrated in the `other` score's conditional survival at all but the highest photon energies. What is **not** established: why the `other` BDT scores events with a true proton differently. That would need an input-level study (which BDT input variables differ for truth 0p and 1p), which is out of scope here. Conditional survivals are order-dependent.

## 12. Delta0 versus Delta+ (`delta_by_truth_class.csv`, `adjusted_delta0_vs_deltaplus.csv`, `decomposition_delta0_vs_deltaplus.csv`, `eff_delta_vs_*.png`)

Integrated: Delta0 7.61 % (521 / 6,846), Delta+ 11.32 % (632 / 5,581): +3.71 pp. Composition: Delta0 is 70 % truth-0p / 24 % 1p / 6 % >=2p; Delta+ is 19 % / 70 % / 10 %. The charge is **not** equal to the proton class (30 % of Delta0 events have a truth proton; 19 % of Delta+ events have none).

| | truth 0p | truth 1p | truth >=2p |
|---|---|---|---|
| Delta0 final | 375 / 4,783 = 7.84 % | 119 / 1,626 = 7.32 % | 27 / 437 = 6.18 % |
| Delta+ final | 101 / 1,080 = 9.35 % | 475 / 3,931 = 12.08 % | 56 / 570 = 9.82 % |

* **Within truth 0p** the Delta+ - Delta0 difference is +1.5 pp (raw); adjusted for photon energy, angle, nu energy and vertex it is +0.4 pp (68 % interval -0.4 to +1.3 pp): consistent with zero.
* **Within truth 1p** it is +4.8 pp and **persists** after the same adjustment (+4.8 pp, interval +3.95 to +5.5). Over the whole sample adjusting for the kinematics leaves +3.7 pp (68 % interval +3.2 to +4.1; photon energy alone: +3.6 pp); adding the proton count as a covariate reduces it to +3.1 pp (+2.6 to +3.7).
* The kinematic distributions of Delta0 and Delta+ are statistically similar (KS p = 0.08 for photon energy, 0.47 cos, 0.13 nu energy, 0.48 z).
* Per-stage decomposition (Delta+ / Delta0): `other` +0.222 (56 % of the log ratio), ncpi0 +0.104 (26 %), n_20br1 +0.076 (19 %), numu +0.035 (9 %), candidate +0.038 (10 %), >20 MeV shower -0.077 (-19 %).
* **Interpretation limits:** the integrated Delta difference is mainly (not entirely) the proton-class composition, plus a remaining Delta-dependent difference *inside the truth-1p class*. Truth 1p with a Delta+ and truth 1p with a Delta0 differ in their origin of the proton (the decay nucleon vs a final-state-interaction proton); that origin was not tested here, so this is an observed correlation only.

## 13. Reconstruction resolution (`resolution_energy_vertex.png`, `resolution_vertex_components.png`, `proton_ke_reco_vs_true_indicative.png`, `resolution_shower_energy.csv`)

Only signal-matched candidates are used (candidate vertex of the dominant truth neutrino within 5 cm of the true signal vertex); efficiency losses are not mixed in. Two populations are always shown separately because selection changes them strongly: **matched candidates** (n = 7,790 with a filled shower) and **final-selected candidates that are also matched** (n = 1,151).

* **Shower energy** (`shw_sp_energy` / true photon energy): matched candidates: median 0.68, 68 % interval 0.20-1.05 (half-width over median 0.62); final-selected: **median 1.034, interval 0.845-1.099, half-width over median 12 %**, nearly flat in photon energy (1.03-1.05 for 100 MeV-1.2 GeV). The very broad matched-candidate distribution contains candidates whose leading shower is not the signal photon shower (no row-level truth match of the shower is stored in the derived table); the final-selected population is strongly selected.
* **Vertex** (`kine_nu_{x,y,z}_corr` minus true vertex): final-selected-and-matched: component medians dx -0.04, dy +0.03, dz +0.88 cm; 68 % intervals dx [-2.3, +2.1], dy [-1.9, +3.1], dz [0.03, 13.4] cm; 3D median 2.0 cm, 68 % quantile 8.4 cm, 90 % quantile 33 cm; 38 % above 5 cm and 19 % above 20 cm. Matched candidates (before the selection): 3D median 18.5 cm, 48 % above 20 cm, dz median +3.1 cm with an upper 84 % quantile of +28.5 cm.
* **Relation to the true conversion distance (observed):** projecting (reco vertex - true vertex) on the true photon direction, the matched candidates have median projection +16.5 cm (median true conversion distance 13.4 cm, rank correlation 0.37, median perpendicular offset 1.0 cm); for the final-selected candidates the projection is +1.0 cm (rank correlation 0.25, perpendicular offset 0.6 cm). So among candidates of converted photons the reco vertex is displaced mostly **along the photon direction**, by an amount of the order of the true conversion distance, but this displacement is largely absent in the final selected sample. This is a correlation observed in the matched candidates; whether the selection preferentially keeps events whose vertex was placed at the true vertex was not tested.
* **Reco proton KE vs true leading proton KE:** the derived table has the leading RECO proton row and the leading TRUE proton of the event but no truth link between individual proton rows. A robust, row-associated comparison is therefore **not possible**; the event-level comparison (n = 4,289 matched candidates with both; rank correlation 0.76; median reco/true 0.99) is shown for orientation only and is labelled "NOT row-associated".
* **Reco shower-to-vertex vs true conversion distance:** weakly correlated (rank 0.14, section 6).

## 14. Natural-CV cross-check (`natural_cv_crosscheck.png`, `natural_cv_crosscheck.csv`)

The 117 natural NC-Delta events in the TPC box (13 selected) against the dedicated official sample, three broad bins per variable (no tuning):
* Photon energy [0,150) / [150,300) / [300,1200) MeV: natural 0/10, 4/63, 9/44 selected vs official 3.3 %, 7.0 %, 13.3 %.
* cos(theta) [-1,0) / [0,0.5) / [0.5,1]: natural 0/29, 1/26, 12/62 vs official 4.0 %, 8.7 %, 12.2 %.
* Smallest per-bin Fisher p-value 0.11 (cos > 0.5: 19.4 % vs 12.2 %); chi-square of the natural-CV counts against the official efficiencies: p = 0.50 (energy), p = 0.17 (angle). The truth distributions agree (KS p = 0.86 for photon energy, 0.30 for cos). At the candidate stage no bin differs (Fisher p >= 0.26).
* **No evidence of gross disagreement.** The natural sample's trends (rising with energy and with forward angle) have the same shape as the official sample's. With 13 selected events the comparison has little power.

## 15. Main descriptive conclusions (observations only)

1. The baseline final efficiency rises steeply with true photon energy (2.4 % at 50-100 MeV to about 15 % above 400 MeV) and with forward angle (3 % to 13 %); the two are correlated (rank 0.72) but each trend persists inside bins of the other.
2. The losses are spread over several stages: no candidate 8.8 %, no >20 MeV shower 26.2 %, numu 24.4 %, other 17.9 %, ncpi0 11.8 % of the denominator. The energy dependence is introduced mostly by the >20 MeV shower and `other` stages; the candidate stage is flat at ~91-93 %.
3. About a quarter of the signal events are lost at the >20 MeV shower stage even at high photon energy.
4. Efficiency is flat in the detector interior and lower at the edges (final 11.4 % interior vs 7.3 % edge in the diagnostic box; candidate efficiency 97 % vs 86 %). The detector-side asymmetry in selected counts reflects the denominator, not the efficiency.
5. 92.6 % of the signal photons undergo an in-volume pair conversion. The 5.6 % that leave the active volume (695 events) contribute no selected events, and the 1.8 % that end in another contained interaction (photoelectric/photonuclear; 220 events) contribute 8 (together: 7.4 % of events without an in-volume pair conversion); true conversion distance up to ~50 cm has little effect on the final efficiency (with weak statistics beyond).
6. The truth 0p / 1p efficiency difference (+2.57 pp) is not explained by the kinematic or positional distributions; it develops predominantly in the `other` stage's conditional survival (47 % vs 63 %), not in numu. Truth 1p events with protons just above 35 MeV are *less* efficient than truth 0p events.
7. The Delta+ / Delta0 difference is mostly a composition effect (proton class) with a remaining difference inside the truth-1p class.
8. Reconstruction (final-selected, matched): shower-energy ratio median 1.03 with ~12 % half-width; vertex 3D median 2 cm but with a tail (19 % above 20 cm).
9. The natural-CV rehearsal shows no gross disagreement with the dedicated official sample in broad bins.

## 16. Open questions

* Why does the `other` BDT discriminate truth 1p from truth 0p (which input variables)? An input-level study of the frozen BDTs is needed.
* What is the physical nature of the energy-independent ~25 % loss at the >20 MeV shower stage?
* What fraction of the edge loss is due to photons leaving the volume versus reconstruction near the boundary?
* Does the Delta-charge dependence inside truth 1p arise from the proton's origin (decay nucleon vs FSI)? Not tested.
* Row-level association between reco proton rows and truth protons is not in the derived table; it would need a re-read of `T_match` for the signal sample.
* The TPC0/TPC1 identification of the detector sides is not established from source here.
* The 5 cm signal-candidate matching and the matched-candidate population of the resolution study should be revalidated against the Wire-Cell truth-match tables before any resolution number is quoted externally.
* All numbers depend on the provisional 35 MeV proton threshold, the TPC-box truth region, the `any` policy and the absence of an approved FV.

*Observations only; no cut recommendations.*
