# NC-Delta control regions: collaboration handoff (development note, PRELIMINARY)

> **Wording and status of the "baseline available covariance".** It means the flux + GENIE cross-section + cross-section-extras + GENIE FSI + beamline-G4 functions *excluding* the unresolved `reinteractions_neutron_Geant4` tail function; the alternative is called the *including unresolved neutron-G4 tail diagnostic*. Excluding that function is **an analysis diagnostic choice, not an established or collaboration-approved SBN prescription** (none was found; see section 11 of `NCDELTA_SYSTEMATIC_WEIGHTS_FIRST_PASS.md`). "Baseline" does not mean validated or approved. Internal identifiers (`TOTAL_validated_excl_nG4`, `unvalidated_nG4` in `syst_band_by_component.csv` and the covariance files) keep their historical names; they mean the same thing. The purity band is a *preliminary available-neutrino-model relative uncertainty*, not "the systematic uncertainty on purity".

Status: EAF development package closed for review. Local commits only, **not pushed** (waiting for Avinay's review). Everything is MC-only and open-data-only; detector, beam-off, POT, `imp_weight` and the NC-Delta signal model are not in any uncertainty. Details: `NCDELTA_SYSTEMATIC_WEIGHTS_FIRST_PASS.md` (sections 7-11), `NCDELTA_FROZEN_SELECTION_PURITY_RESULTS.md`.

## A. Selection / reconstruction context
Frozen legacy MicroBooNE chain (numu > 0.4, other > 0.2, ncpi0 > -0.05, nue > -1.0, candidate policy `any`; provisional TPC-box denominator 12,427 truth events), no retraining, no Aurora DEV model.

| | efficiency | MC-only expected purity (stat) | 1g0p / 1gNp purity |
|---|---|---|---|
| old fg1-era reconstruction | 6.70 % (833 / 12,427) | 2.74 +- 0.18 % | 2.52 % / 2.99 % |
| WCLocal2026Nov16 (WCL1116) | 15.60 % (1,938 / 12,427) | 2.63 +- 0.11 % | 2.31 % / 3.25 % |

These purities are **MC-only expected purities, upper bounds**: the pure-cosmic (beam-off) component is missing because its normalization is unresolved. The preliminary neutrino-model study gives a relative band of 16.5 % (old) / 17.8 % (Nov16) on the purity from the baseline available covariance (excluding the unresolved reinteractions_neutron_Geant4 tail) (17.5 % / 20.3 % if the unresolved neutron-G4 function is included); this is **not** attached to the central values as a "+-" and is not a final uncertainty. Detector, cosmic/beam-off normalization, POT, NC-Delta radiative-decay model, `imp_weight` and unresolved-owner events are not included.

## B. Data/MC normalization (open control regions, beam-on open data 4.62e18 POT)
Integrated rates are broadly consistent with 1 in preselection (0.98 / 0.97), nu-mu-rich (1.00 / 1.01), other-rich (1.05 / 1.03) and nu-e-rich (0.99 / 0.92, statistically weak). The NC-pi0-rich sideband has Data/MC 0.76 (old) / 0.74 (Nov16), a ~25 % deficit that is only **-1.6 / -1.8 sigma** (-1.5 / -1.7 including the unresolved function) once the available flux + GENIE + FSI + G4 covariance (~19-20 %, almost a pure normalization mode) is included; the shower-energy shape is consistent (rate+shape chi2/ndof 6.2/8 and 9.9/8).
Shape caveats (energy, baseline available covariance): Nov16 preselection 22.4/8 (p = 0.004) and `SB_numu` 16.4/8 (p = 0.04), old preselection 17.9/8 (p = 0.02) are in tension (they are 10.3/8, 9.2/8, 15.8/8 if the unresolved function is kept); Nov16 `SB_other` 25.1/8 (p = 0.0015) is driven by sparse high-energy bins in a cosmic-rich sample where the MC has no cosmic-only component (hypothesis, not demonstrated).

### Authoritative control-region table (baseline available covariance; "incl." = also with `reinteractions_neutron_Geant4`)
| region | reco | data | MC (S+B) | Data/MC | data stat | MC stat | avail. syst, baseline (incl. nG4) | Np/0p data/MC +- (stat+MC+syst baseline; incl. nG4) | energy rate+shape chi2/ndof, baseline (incl.) | energy shape-only chi2/ndof, baseline (incl.) | dominant MC truth | flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| preselection | old | 8480 | 8622 | 0.98 | 1.1% | 0.4% | 15.1% (23.8%) | 0.82 +- 0.05 (0.28) | 17.9/8 (15.8) | 16.1/7 (14.3) | NUMU_CC 33%; CC_PI0 26% |  |
| SB_numu | old | 6301 | 6294 | 1.00 | 1.3% | 0.5% | 16.2% (29.6%) | 0.81 +- 0.06 (0.35) | 12.1/8 (10.5) | 9.8/7 (8.7) | NUMU_CC 42%; CC_PI0 31% |  |
| SB_other | old | 1271 | 1206 | 1.05 | 3.0% | 1.2% | 12.7% (14.1%) | 0.91 +- 0.08 (0.11) | 10.3/8 (7.9) | 9.1/7 (7.3) | OUTSIDE_TPC_NU 37%; NC_PI0 19% |  |
| SB_ncpi0 | old | 585 | 766 | 0.76 | 3.2% | 1.5% | 19.1% (20.4%) | 0.67 +- 0.07 (0.08) | 6.2/8 (6.0) | 6.0/7 (6.0) | NC_PI0 56%; CC_PI0 18% |  |
| SB_nue | old | 55 | 55 | 0.99 | 13.4% | 5.5% | 15.1% (17.1%) | 1.07 +- 0.37 (0.38) | 1.9/5 (1.8) | 1.9/4 (1.7) | NUE_CC 71%; NC_PI0 10% | **STAT-WEAK: n_data<100;Np or 0p bin <50 events** |
| preselection | Nov16 | 8321 | 8547 | 0.97 | 1.1% | 0.4% | 15.5% (24.7%) | 0.80 +- 0.05 (0.29) | 22.4/8 (10.3) | 21.2/7 (10.1) | NUMU_CC 31%; CC_PI0 27% |  |
| SB_numu | Nov16 | 5871 | 5799 | 1.01 | 1.3% | 0.5% | 16.9% (32.5%) | 0.80 +- 0.05 (0.40) | 16.4/8 (9.2) | 12.6/7 (7.9) | NUMU_CC 43%; CC_PI0 34% |  |
| SB_other | Nov16 | 1262 | 1227 | 1.03 | 2.9% | 1.2% | 12.6% (14.0%) | 0.79 +- 0.07 (0.08) | 25.1/8 (25.0) | 23.1/7 (22.9) | OUTSIDE_TPC_NU 40%; NC_PI0 17% |  |
| SB_ncpi0 | Nov16 | 755 | 1020 | 0.74 | 2.7% | 1.3% | 19.4% (20.6%) | 0.75 +- 0.08 (0.08) | 9.9/8 (8.4) | 10.6/7 (9.7) | NC_PI0 61%; CC_PI0 16% |  |
| SB_nue | Nov16 | 63 | 69 | 0.92 | 11.5% | 5.0% | 16.5% (17.8%) | 0.54 +- 0.16 (0.16) | 6.1/5 (5.7) | 6.5/4 (6.0) | NUE_CC 78%; CC_PI0 7% | **STAT-WEAK: n_data<100;Np or 0p bin <50 events** |

`data` = open beam-on events, `MC` = S + B at the data POT (no cosmic-only component), syst = flux + GENIE + FSI + beamline G4 (+ extras), event level, S and B varied coherently. Not in any column: detector / proton reconstruction, cosmic/beam-off, POT, dirt-specific, `imp_weight`, signal-model dials, unresolved-owner events. Statistically weak regions are flagged.

## C. Proton multiplicity
The MC predicts a larger reconstructed Np/0p ratio than data across several regions: data/MC double ratio 0.82 / 0.80 (preselection, old / Nov16), 0.81 / 0.80 (`SB_numu`), 0.67 / 0.75 (NC-pi0), 0.91 / 0.79 (`SB_other`), nu-e-rich low statistics. It is a general ~20 % effect, somewhat larger in the NC-pi0 sideband (not an NC-pi0-only discrepancy). It is not localized in the available observables: not in pi0 kinematics or pair finding (mass, opening angle, energies, asymmetry, conversion gaps), not in proton KE or length shapes, not at the TPC edge, not in low-KE threshold behaviour. WCL1116 does **not** remove it. Truth->reco migration (MC): reco 0p is truth-impure, P(truth >= 1 proton > 35 MeV | reco 0p) = 0.525 (old) / 0.446 (Nov16), and WCL1116 improves proton finding in MC (same events: true 1p -> reco 0p 31 % -> 26 %, true >= 2p -> reco >= 2p 41 % -> 48 %), yet the data/MC mismatch persists.
With statistics only the double ratio is 8-11 sigma below 1 in preselection and `SB_numu`; with the baseline available covariance 3.3-4.2 sigma; including the unresolved neutron-G4 function only 0.5-0.7 sigma. The significance depends on that function; **quote the ratios, not the sigmas**.

## D. Interpretation (conservative)
Open control data indicate that MC tends to predict a larger reconstructed Np/0p ratio than data across several regions. Improved WCL1116 reconstruction does not remove the discrepancy. Current information cannot distinguish a generic hadronic / proton-multiplicity modeling effect from proton reconstruction / detector modeling; detector-variation samples or alternative generator / model comparisons are needed. Proton-reconstruction inefficiency has not been demonstrated.

## E. Missing pieces
- Detector variations (proton reconstruction / calibration / recombination); alternative generator or hadronic-model comparison.
- Beam-off (cosmic-only) normalization convention; the missing component would raise every MC prediction.
- `rec.mc.nu.imp_weight` convention (not applied; sample means ~0.1-0.2).
- Final 2 cm / effective-boundary reconstruction production (all results use the frozen legacy chain on the old fg1-era and WCLocal2026Nov16 productions).
- Final Round-2 BDTs (the legacy MicroBooNE BDTs are used unchanged).
- An approved SBN treatment of the `reinteractions_neutron_Geant4` weight tail (none found; see below).
- Signal-region approval (the final selection on beam-on data remains blocked).

### Systematic categories (kept distinct)
- **Generic neutrino-model covariance (baseline available, preliminary):** flux, beamline G4 (without the neutron function), GENIE cross section, GENIE FSI, cross-section extras.
- **Unresolved neutron-G4 tail diagnostic, shown separately:** `reinteractions_neutron_Geant4`. Event-level audit: in Np-rich selections and the Nov16 final selection a handful of events carry 87-100 % of its variance (top event: run 8011 / subrun 91 / evt 3, a nu-mu NC RES, NC_PI0, max weight 223,065, the same MC event in both productions); the 0p yield and the old final selection are broad. Not an association error (same tail in an unselected random sample); it is a heavy-tailed property of the weights. The sbncode fcl declares `max_weight: 100`, the flux calculators clamp at 30, `cafpyana` omits the neutron function, but **no approved treatment was found** and none was invented; excluding it is our diagnostic choice. Every figure and table states whether the error bar includes it, excludes it, or shows both; neither is a "final systematic uncertainty".
- **NC-Delta signal-model (separate, not in the generic band):** `RDecBR1gamma`, `ThetaDelta2NRad`.
- **Not yet included:** detector / proton reconstruction, cosmic/beam-off normalization, POT, unresolved `imp_weight`, unresolved-owner events (~4-5 % of the final-selection prediction, 3-18 % in the control regions), dirt-specific uncertainty, other detector/model categories not in these CAF weights.

## F. Firewall
No Aurora DEV model was evaluated on FermiGrid or on any official evaluation sample. No signal-region (final-selection) beam-on data were opened: only the preselection / sideband open data allowed by `configs/data_policy.yaml` were read; `run3bnb` is not used. Nothing is pushed.

## Figures (main tier: three; everything else is backup)
1. `plots/ncdelta_purity_datamc/F_ncpi0_sideband_datamc_with_systematics.png`: "The ~25 % NC-pi0 rate deficit is not significant with the available neutrino-model covariance" (baseline available covariance; the including-nG4 version is `F_..._incl_nG4.png`). Caveat on the figure: detector / cosmic / POT / `imp_weight` not included.
2. `plots/ncdelta_purity_datamc/K_np_over_0p_double_ratio_by_region.png`: "MC predicts a higher reconstructed Np/0p ratio than data across several control samples" (thick = data + MC statistics, thin = + baseline available covariance, dashed = including the unresolved tail function).
3. `plots/ncdelta_purity_datamc/J_ncpi0_truth_reco_topology_migration.png`: "Reconstructed 0p/Np is migration-heavy; WCL1116 improves proton finding in MC" (backup tier if the room is crowded).
Backup only: `H_ncpi0_topology_variables.png`, `I_ncpi0_topology_reco_observables.png` (92 panels), `E_syst_first_pass_*.png`, `G_sideband_integrated_ratio_*.png`.

## Questions for Haiwang / Hanyu
Top priority (five items) at the top of `QUESTIONS_FOR_HAIWANG_HANYU.md`: beam-off normalization; `imp_weight` convention; effective-boundary / final production status; detector-variation samples for proton-multiplicity validation; approved SBN treatment of extreme `reinteractions_neutron_Geant4` weights.

## Reproduce
`ncdelta_syst_extract.py`, `ncdelta_syst_covariance.py`, `ncdelta_syst_regions.py plan|extract|analyze [--exclude-functions reinteractions_neutron_Geant4]`, `ncdelta_neutron_g4_extract.py` + `_audit.py final|regions` + `_topevents.py`, `ncdelta_ncpi0_topology_extract.py` + `_analyze.py`, `ncdelta_np_over_0p_summary.py`, `ncdelta_control_region_summary.py`; tests: `python -m pytest tests -q`.
