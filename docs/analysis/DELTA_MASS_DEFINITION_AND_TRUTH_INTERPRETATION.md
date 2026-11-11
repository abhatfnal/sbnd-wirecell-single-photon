# Reconstructed Delta mass: definition, generator-level validation, and what it means for each Delta charge and proton origin

Date: 2026-11-11. Branch `analysis/ncdelta-common-observables-20261111`. Characterization only: **no mass cut, no selection, no yield fit**. Code: `src/sbnd_single_photon/observables.py` (`delta_mass`, `pair_class`), `scripts/common_observables_audit.py`, `scripts/common_observables_genie_scan.py`. Reco inputs: `NCDELTA_RECO_OBSERVABLE_SEMANTICS.md`; proton/photon truth association: Phase 9 and Phase 10 documents.

## 1. Definition of the reconstructed mass

For a final-selected event whose selected candidate has exactly one reco proton row under the proton policy (reco 1gamma1p):

```
E_p   = T_p + m_p                        T_p  = kine_energy_particle of the proton row [MeV]
p_p   = sqrt(E_p^2 - m_p^2)
M^2   = m_p^2 + 2 E_gamma (E_p - p_p cos(theta_gamma,p))
M     = sqrt(M^2)   only where M^2 > 0     (never clipped to zero)
```

* `m_p = 938.27208816 MeV` (PDG 2022), `E_gamma = shw_sp_energy` of the selected shower [MeV] (`NCDELTA_RECO_OBSERVABLE_SEMANTICS.md`), `cos(theta_gamma,p)` = dot product of the unit `T_pf` chord of the selected shower and the unit `T_pf` chord of the proton row. The photon mass and its energy-momentum relation (`p_gamma = E_gamma`) are used; the photon energy is the **shower** energy (a fragment of the photon if the photon is split, Phase 9).
* **Object choice is deterministic and never truth-selected.** The photon row is the electron-typed shower row whose KE equals `shw_sp_energy` (0.1 %). The proton is the unique typed-proton row above the threshold of the proton policy; for >= 2 rows (outside this mass) the rule would be the highest reco KE with the lowest row index as tie-break (`leading_proton_row`; carried in the object table but not used for a headline mass).
* **Status of every selected event is explicit** (`selected_object_table.parquet`, column `<policy>__mass_status`): for the baseline proton policy 554 `ok`, 2 `no_photon_row` (the selected shower has `shw_sp_filled == 0` or no row of equal energy), 597 `not_1g1p` (527 reco 1gamma0p + 70 reco >= 2p); `mass2_nonpositive` and `no_*_direction` occur 0 times. Under "35 MeV excluding `included == 3`": 503 / 2 / 648; under 50 MeV: 538 / 2 / 613.
* The proton policy (35 MeV with the existing `included` convention) is the **primary** convention; excluding `included == 3` rows and the 50 MeV threshold are **policy sensitivities** (`PROTON_RECONSTRUCTION_TRUTH_ASSOCIATION.md`, roadmap item E): no policy is frozen here.

## 2. Three different masses: do not confuse them

| symbol | built from | what it is |
|---|---|---|
| **A: `M_true_decay`** | the GENIE record: the decay photon (`pdg 22`, mother = the Delta) and the decay nucleon (`status 14`, mother = the Delta; the nucleon **before final-state interactions**) | the invariant mass of the actual Delta decay pair = the Delta record mass |
| **B: `M_finalstate_truth`** | the signal photon (true momentum) and the **post-FSI** primary proton matched to the reco proton row (`T_truth_pf` momentum, `E = T + m_p`) | the mass of "signal photon + the post-FSI proton": **not** the Delta mass if FSI changed the nucleon |
| **C: `M_reco`** | the reco photon shower and the reco proton row | what is measured |

**A is the physical Delta mass; B and C are only equal to it when the proton in the final state is the Delta decay proton and was not changed by FSI.** For **Delta0** events the decay nucleon is a **neutron** (6,845 of 6,845 Delta0 events, 100 %; the Delta+ decay nucleon is a proton in 5,581 of 5,581), so a reco proton in a Delta0 event can never be the decay nucleon: it is a proton produced after the decay (charge exchange of the neutron, knock-out, or a Geant4 secondary of the decay neutron). **The reconstructed `M_reco` of a Delta0 event is not a Delta invariant mass**; it is the mass of the photon with a proton that descends from, or is produced by, the decay neutron.

## 3. Generator-level validation (`generator_delta_decay_mass.csv`, `generator_decay_mass_vs_nominal_bw.csv`; all 12,426 signal events with a record)

| sample | n | mode | median | 16-84 % | range |
|---|---|---|---|---|---|
| all signal events | 12,426 | 1232.5 MeV | 1209.4 | 1154.9 - 1259.8 | 1074 - 1711 |
| Delta+ | 5,581 | 1232.5 | 1209.4 | 1156.5 - 1260.9 | 1074 - 1711 |
| Delta0 | 6,845 | 1232.5 | 1209.5 | 1153.7 - 1258.9 | 1074 - 1634 |
| final selected (`any`) | 1,153 | ~1198 (coarse 5 MeV bins) | 1216.4 | 1165.9 - 1270.2 | 1075 - 1554 |

* The invariant mass of (decay photon + decay nucleon) **equals the Delta record mass to better than 1 keV in 100 % of the events** (`delta_record_equals_decay_pair`), and the Delta+ and Delta0 distributions are identical: the generator produces the Delta(1232) with the decay nucleon charge fixed by the Delta charge.
* The shape peaks at **1232 MeV (mode)**, is **asymmetric** (median 1209, long low-mass side to the 1074 MeV kinematic edge, falling faster than a nominal relativistic Breit-Wigner above the peak). Compared with the nominal Breit-Wigner (M = 1232, Gamma = 117 MeV, **not fitted**, area-scaled): at 1150-1170 MeV the generator has 837 events against 648 for the scaled Breit-Wigner, at 1330 MeV 91 against 211. So the generator reproduces a **Delta(1232)-like peak** but not a plain Breit-Wigner line shape; the origin of the extra asymmetry (resonance model, cross-section and flux weighting, the W-dependent width) was **not investigated**. **No line shape is adopted for a yield fit.**
* **Delta+ events where the decay proton can be traced to the final state** (Phase 10 per-proton origin: `decay_proton` = the post-FSI primary descends from the decay proton only and is its only descendant): 3,537 of the 8,132 primary protons above 35 MeV; they are the "decay pairs" below.

## 4. Verification of the truth-level construction

For the 348 selected Delta+ decay pairs (photon truth-correct, reco proton row = the true post-FSI primary that descends from the decay proton), the final-state-truth mass B minus the generator decay mass A has **median 0.000 MeV and 16th = 84th percentile = 0.000**: for the majority of events (the protons that were not changed by FSI) B reproduces A to floating-point precision. This validates the formula, the units (GeV to MeV), the use of `E = T + m_p` with the PDG mass and the photon/proton momentum conventions. In the remaining events (17.8 % beyond three half-widths; RMS 28 MeV) the proton rescattered, which is exactly what makes B differ from A. (`delta_mass_resolution_decay_pairs.csv`.)

## 5. Reconstructed mass of the selected signal (`delta_mass_signal_subsets.csv`, `delta_mass_pair_class_by_delta_charge.csv`, `delta_mass_signal_decomposition.png`)

Pair classes of the 554 reco 1gamma1p events with a mass (baseline policy; `pair_class`): **decay pair 348** (62.8 %; Delta+, reco proton = the decay proton), **FSI-created / other signal primary 143**, **Geant4 secondary 35**, **fake / non-proton / other 28**, photon not the signal photon **0** (all 554 selected photons are the signal photon).

| subset | n | median | 16-84 % | mode (50 MeV bins) | fraction 1100-1400 |
|---|---|---|---|---|---|
| all selected reco 1gamma1p | 554 | 1220.8 | 1136 - 1316 | 1225 | 87.2 % |
| photon and proton truth-correct | 491 | 1220.5 | 1138 - 1310 | 1225 | 88.8 % |
| reco proton = Delta+ decay proton | 348 | 1211.9 | 1137 - 1285 | 1225 | 88.2 % |
| FSI-created / other signal primary | 143 | 1240.5 | 1144 - 1346 | 1275 | 90.2 % |
| Geant4 secondary proton | 35 | 1215.4 | 1102 - 1309 | 1225 | 68.6 % |
| fake / non-proton / other | 28 | 1265.6 | 1120 - 1392 | 1125 | 82.1 % |
| truth 0p / 1p / >=2p | 50 / 469 / 35 | 1228 / 1216 / 1262 | 1119-1367 / 1137-1296 / 1169-1385 | 1125 / 1225 / 1275 | 74 % / 88.5 % / 88.6 % |
| Delta+ / Delta0 | 423 / 131 | 1217.7 / 1232.3 | 1139-1304 / 1122-1343 | 1225 / 1175 | 87.7 % / 85.5 % |

**When does a recognisable Delta(1232)-like mass structure appear?** (descriptive; no fit)
* A single peak at about 1225 MeV with a 68 % interval of about +-75 MeV appears for the **whole selected 1gamma1p signal**, and it is already present for the Delta+ decay pairs (median 1212, 68 % interval 1137-1285 MeV). It is **narrower and cleaner when the proton is a true signal primary** (truth-1p events: 88.5 % between 1100 and 1400 MeV) than for the other subsets: truth-0p events (the proton row is a secondary or a promoted sub-threshold proton) have a low mode (1125 MeV, 14 % below 1100 MeV), truth->=2p events and the fake/non-proton rows are shifted and extended to high mass (median 1262-1266, 11-14 % above 1400 MeV), secondaries have a long low tail (17 % below 1100).
* A peak of nearly the same position appears for **Delta0 events** (median 1232, 68 % interval 1122-1343; the mode of the coarse 50 MeV histogram is 1175 MeV, 1125 MeV for the truth-correct subset, i.e. the peak position is not stable at this statistic; 131 events, 93 truth-correct). This **cannot** be the Delta decay-pair mass (section 2): the reco proton is not the decay nucleon. It reflects that the photon and a proton descended from (or kicked by) the decay neutron carry most of the Delta momentum. The peak is therefore **not an exclusive signature of the Delta+ decay pair**; interpretation of the mass in terms of the Delta requires the Delta charge, which is not a reconstructed observable.
* Because the mass is dominated by the photon energy and the opening angle (`NCDELTA_COMMON_RECO_OBSERVABLES.md` section 7), the shape of the selected backgrounds at fixed object definition is the relevant comparison (section 15 of that document), not the position of the peak alone.

## 6. Resolution of the decay-pair mass (`delta_mass_resolution_decay_pairs.csv`, `delta_mass_substitution_study.csv`, `delta_mass_component_residuals.csv`)

348 decay pairs. `M_reco - M_true_decay`: median **+2.8 MeV (+0.2 %)**, 68 % interval **[-44, +34] MeV** (half-width 39 MeV), RMS 65 MeV (non-Gaussian: 7.8 % of the events beyond three half-widths). Split: the FSI effect (B - A) is exactly zero for most events with RMS 28 MeV from the rescattered minority; the **reconstruction effect (C - B)** has median +2.3 MeV and half-width 36.5 MeV, RMS 60 MeV.

Descriptive substitution study (one reco ingredient replaced by its truth value, residual against B; the effects are **not additive**; this is a test of which ingredient limits the width, not a proof of independent causal contributions): all reco 36.5 MeV; **E_gamma true 20.0**; photon direction true 28.5; both directions true (opening angle) 26.1; proton direction true 34.9; **proton KE true 36.1** (no effect); photon energy and opening angle true together **1.0 MeV**; all ingredients true 0.0 (closure). Component residuals: E_gamma fractional median +3.4 %, half-width 10.4 %; proton KE half-width 3.0 %; photon-direction cos median 0.987; proton-direction cos median 0.999; opening-angle cosine residual half-width 0.14. A reco-only alternative photon direction (vertex -> shower start for detached showers) reduces the half-width from 36.5 to 29.1 MeV and moves the median residual from +2.3 to +8.1 MeV.
