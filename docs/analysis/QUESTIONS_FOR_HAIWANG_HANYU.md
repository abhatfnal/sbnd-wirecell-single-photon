# Questions for Haiwang / Hanyu (prioritised)

Evidence for each item is in the linked audit. Nothing below has been assumed in the baseline.

## A. Block physical normalisation

1. ~~500k stored vs 1.887M generated~~ **Resolved.** The official Gen2 BNB CV request uses `prodgenie_corsika_proton_rockbox0p1_sbnd.fcl` (`v10_14_02_03`, expected filter efficiency 25 %); the observed 26.5 % is the intended generator-level filter. selected/ΣTotalPOT is the POT-normalised neutrino-induced rate of the filtered sample; cosmic-only backgrounds come from beam-off (`POT_EXPOSURE_AUDIT.md` §7).
2. **nueCC normalisation.** It belongs to the Gen2 rare-xsec filtered production. `ΣTotalPOT / generated` is ~100× the CV value and the release fcl adds a `ccnuefilter` (7 % of generated events survive). What are the filter / POT weighting conventions and what exposure should be assigned (`NUECC_CONTROL_SAMPLE.md`)? Also: 131 files with `rec.hdr.pot ≠ TotalPOT`, 2,218 reused (run, subrun) pairs.
3. **Beam-off scale (ONE precise question; everything else is established, `DATA_EXPOSURE_NORMALIZATION.md` section 0).** Is the approved beam-off scale for the open data (runs 18255, 18259) `Σ rec.hdr.nbnbinfo (beam-on, 960,047) / Σ rec.hdr.noffbeambnb (beam-off, 2,542,847)` (gate counters, pre-filter), or built from recorded-trigger counts of the `bnblight` and `offbeamlight` streams (they record 9.4 % and 2.0 % of their gates, so the two differ by ~4.8×)? And is the InTime-Run1 beam-off sample, which has no run-18255 file, acceptable for those runs?

## B. Block freezing the selection definition

4. **Candidate policy (policy, not source).** The source is now read (`WIRECELL_SOURCE_CONVENTIONS_AUDIT.md` sections 1-2): `nu_index` is a longest-selected-activity ordering and `nu_dedup_flash_group` is OFF in the fg1 files (measured: no `kDedupFlashGroup` bundle). Remaining: should the baseline keep `any` (analysis) with `first` as comparison, and should an event with two interactions count once or twice? (`CANDIDATE_POLICY_AUDIT.md`)
5. **Fiducial volume.** Is there a preferred SBND FV for the Wire-Cell vertex `kine_nu_*_corr` (SCE-corrected or raw), including any high-y / cathode treatment? No authoritative one was found among 19 conflicting definitions (`SBND_FIDUCIAL_VOLUME_AUDIT.md`).
6. **Proton threshold.** Is 35 MeV the intended KE threshold for the 0p/1p split? (`RECO_PROTON_DEFINITION_AUDIT.md` §5: rows of type 2212 above it are 95.7 % true protons.)
7. **Leftover-shower proton rows (policy).** Source fact settled: `kine_energy_included == 3` marks a shower row whose start vertex has connection type 3 (detached 'leftover' shower); such rows ARE summed in `kine_reco_Enu` despite the flag's name (`WIRECELL_SOURCE_CONVENTIONS_AUDIT.md` section 3). Remaining policy question: should they count in the reco proton multiplicity? They are 89 % true protons, but about half have a much too low energy (reco/true ≈ 0.25). The baseline counts them.
8. **Flash-time convention** (production question; `FLASH_TIME_CONVENTION_AUDIT.md`, `WIRECELL_SOURCE_CONVENTIONS_AUDIT.md` section 6): the source shows data flash times carry a per-frame `frame_apply_at_caf` offset and MC none, `ShiftData2MC = 0`. Is the ≈ +0.3 µs beam-on offset relative to MC expected, does the 0.2 µs window edge truncate the MC spill, and should data be shifted before comparing?

## C. The one thing only the Wire-Cell team can do

9. ~~**Please process the EXISTING official Gen2 NC-Δ evaluation sample through the same fg1-compatible Wire-Cell merged-CAF workflow.** Everything else about this sample has been determined from SAM, the source and the files themselves (`NCDELTA_GENERATOR_FILTER_AUDIT.md`): 15,777 flatCAFs (`…_EX_ncdeltarad_v10_14_02_05_flat_caf_sbnd`) / 16,505 reco1 files, 13,773 / 14,442 signal events, 6,626 flatCAFs with zero events, Σ`TotalPOT` 2.83853e21, run/subrun/event unique over the whole set, all files readable over XRootD. Useful sizing: ~9,150 non-empty units, 1-5 events each (like the Aurora NC-Δ units, ~900 non-empty units per node-hour); the 6,626 empty units need nothing. Please keep the same SCN vertexer (`Trun.dl_weights`) and `T_truth_*` / `T_overlap` / `T_match` trees as the other official samples.~~ **Done 2026-11-10 (prod #6, `ncdr`): 9,150 merged CAFs, 13,772 events, all wc.valid; verified in `OFFICIAL_NCDELTA_WC_ARRIVAL_REPORT.md`.**

9a. **Please confirm three declarations we only inferred from "same configuration as fg1"** (the files carry no field for them): no DV2-MAX, no Fix2, no alternative BDT training; and the larwirecell / sbndcode / cfg / wire-cell-data commits in the `ncdr` README.
9b. **(LOW PRIORITY, not a blocker.) One official NC-Delta flatCAF was missed by the production pair builder because it lives in an anomalous SAM directory layout. Could you rerun this one pair when convenient?** One unit was not run: `reco1-detsim-g4-filter-gen-2483-4161-1955-eda8_ncdeltarad` (run 317 / subrun 41 / event 6753, 1 signal event).** Its flatCAF is in SAM and on dCache (content `good`) but under an anomalous layout, `.../ncdeltarad/000011/caf/subrun_011641/`, instead of `.../ncdeltarad/caf/000011/000116/`; the pair list classified it as "no CAF" (the 729th skipped file; our census has 728). Was it excluded deliberately, or is it a path-derivation miss? If the latter, could this one pair be run? We keep the event in the denominator in the meantime (`OFFICIAL_NCDELTA_WC_ARRIVAL_REPORT.md` section 3).

## C2. Small production questions that SAM/CAF cannot answer (low priority; not blocking)

(The GENIE branching question was answered as far as the data allow: the dedicated sample agrees with the natural NC Δ → Nγ population in the CV, `NATURAL_NCDELTA_CV_CROSSCHECK.md`.)

10. **728 of the 16,505 reco1 units have no flatCAF child** (Haiwang's skipped list has 729: the extra one is 9b) (669 signal events, 4.4 % of POT): failed or still-pending CAF jobs? Should the Wire-Cell production include them once a flatCAF exists?
11. **CAF `TotalGenEvents` is 125 in every file**, while SAM's reco1 `mc.generated_event_count` is 12,500 per unit. Which is the intended generated count (our denominator uses SAM `mc.pot` / `mc.generated_event_count`)?

12. **`shw_sp_energy` rows (small).** `wc.T_match` and the shower selection are now settled from source (`WIRECELL_TRUTH_MATCH_SEMANTICS.md` sections 2-6; the one rule corrected was the partner ranking). Left: for 3 of 649 selected candidates no `T_kine` shower row has the energy `shw_sp_energy` reports; the source says it is `shower_energy(max_shower) = kine_best (kine_charge if kine_best == 0)`, so a difference between that and the `kine_energy_particle` of the row (binding-energy or leftover-shower correction after the tagger?) is the suspected cause. Please confirm.

## Minor (no action unless convenient)

- The `(0,0,0)` vertex is the default of a candidate with `has_vertex == 0`; confirm that is the intended "no main vertex" flag (`VERTEX_SENTINEL_AUDIT.md`).
