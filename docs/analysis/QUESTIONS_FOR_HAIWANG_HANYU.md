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

## C. Can wait for the Wire-Cell merged CAFs of the official Gen2 NC-Δ sample

9. The official Gen2 NC-Δ radiative sample already exists (`…_EX_ncdeltarad_v10_14_02_05_{reco1,flat_caf}_sbnd`). **When will its Wire-Cell merged-CAF production be done?** With it please provide: the filter efficiency and generator/filter semantics (what `TotalGenEvents` / `TotalPOT` mean), the representation of the Δ → Nγ truth decay, and confirmation that it carries the same baseline SCN vertexer (`Trun.dl_weights`) as the other official samples (checklist in the design note §7).

## Minor (no action unless convenient)

- The `(0,0,0)` vertex is the default of a candidate with `has_vertex == 0`; confirm that is the intended "no main vertex" flag (`VERTEX_SENTINEL_AUDIT.md`).
