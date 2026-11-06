# Questions for Haiwang / Hanyu (prioritised)

Evidence for each item is in the linked audit. Nothing below has been assumed in the baseline.

## A. Block physical normalisation

1. ~~500k stored vs 1.887M generated~~ **Resolved.** The official Gen2 BNB CV request uses `prodgenie_corsika_proton_rockbox0p1_sbnd.fcl` (`v10_14_02_03`, expected filter efficiency 25 %); the observed 26.5 % is the intended generator-level filter. selected/ΣTotalPOT is the POT-normalised neutrino-induced rate of the filtered sample; cosmic-only backgrounds come from beam-off (`POT_EXPOSURE_AUDIT.md` §7).
2. **nueCC normalisation.** It belongs to the Gen2 rare-xsec filtered production. `ΣTotalPOT / generated` is ~100× the CV value and the release fcl adds a `ccnuefilter` (7 % of generated events survive). What are the filter / POT weighting conventions and what exposure should be assigned (`NUECC_CONTROL_SAMPLE.md`)? Also: 131 files with `rec.hdr.pot ≠ TotalPOT`, 2,218 reused (run, subrun) pairs.
3. **Beam-off scaling for the open data.** What is the approved procedure and the beam-on gate count / livetime for runs 18255/18259? The beam-off subset has no file in run 18255 and 4 files in run 18259 (`DATA_EXPOSURE_NORMALIZATION.md`).

## B. Block freezing the selection definition

4. **Candidates.** Is the production `nu_index` ordering (longest selected activity first; 0 = "primary") and the dedup knob `nu_dedup_flash_group` (default off) identical to the PR #543 source inspected? Is more than one in-window flash per spill expected in the CV overlay, and should an event with two interactions count once or twice? (`CANDIDATE_POLICY_AUDIT.md`)
5. **Fiducial volume.** Is there a preferred SBND FV for the Wire-Cell vertex `kine_nu_*_corr` (SCE-corrected or raw), including any high-y / cathode treatment? No authoritative one was found among 19 conflicting definitions (`SBND_FIDUCIAL_VOLUME_AUDIT.md`).
6. **Proton threshold.** Is 35 MeV the intended KE threshold for the 0p/1p split? (`RECO_PROTON_DEFINITION_AUDIT.md` §5: rows of type 2212 above it are 95.7 % true protons.)
7. **Leftover-shower proton rows.** Should rows with `kine_energy_included == 3` (all pool 2) count in the reco proton multiplicity? They are summed into reco E_ν, are 89 % true protons, but about half have a much too low energy (reco/true ≈ 0.25). The baseline counts them.
8. **Flash-time convention** (unresolved, `FLASH_TIME_CONVENTION_AUDIT.md`): is the ≈ +0.3 µs offset of beam-on relative to MC in `flash_time_us` expected from FrameShift (`ShiftData2MC = 0`, RWM/trigger reference); does the 0.2 µs window edge truncate the MC spill; should data be shifted before comparing?

## C. The one thing only the Wire-Cell team can do

9. **Please process the EXISTING official Gen2 NC-Δ evaluation sample through the same fg1-compatible Wire-Cell merged-CAF workflow.** Everything else about this sample has been determined from SAM, the source and the files themselves (`NCDELTA_GENERATOR_FILTER_AUDIT.md`): 15,777 flatCAFs (`…_EX_ncdeltarad_v10_14_02_05_flat_caf_sbnd`) / 16,505 reco1 files, 13,773 / 14,442 signal events, 6,626 flatCAFs with zero events, Σ`TotalPOT` 2.83853e21, run/subrun/event unique over the whole set, all files readable over XRootD. Useful sizing: ~9,150 non-empty units, 1-5 events each (like the Aurora NC-Δ units, ~900 non-empty units per node-hour); the 6,626 empty units need nothing. Please keep the same SCN vertexer (`Trun.dl_weights`) and `T_truth_*` / `T_overlap` / `T_match` trees as the other official samples.

## C2. Small production questions that SAM/CAF cannot answer (low priority; not blocking)

10. **728 of the 16,505 reco1 units have no flatCAF child** (669 signal events, 4.4 % of POT): failed or still-pending CAF jobs? Should the Wire-Cell production include them once a flatCAF exists?
11. **CAF `TotalGenEvents` is 125 in every file**, while SAM's reco1 `mc.generated_event_count` is 12,500 per unit. Which is the intended generated count (our denominator uses SAM `mc.pot` / `mc.generated_event_count`)?
12. **GENIE tune / branching.** The pass fraction (7.0e-5) and the 55 % / 45 % Δ⁰ / Δ⁺ split look like a natural, unweighted radiative decay, but `genweight` and `prim.gstatus` are unfilled in the CAF. Please confirm the radiative branching is natural and no event weight is needed.

## Minor (no action unless convenient)

- The `(0,0,0)` vertex is the default of a candidate with `has_vertex == 0`; confirm that is the intended "no main vertex" flag (`VERTEX_SENTINEL_AUDIT.md`).
