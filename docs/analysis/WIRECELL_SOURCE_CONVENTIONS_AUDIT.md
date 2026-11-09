# Source audit of the technical conventions the baseline inherits (source fact vs analysis-policy decision)

Date 2026-11-09. Nothing here changes an analysis choice. Each convention is split into **SOURCE FACT** (code or the authors' document, with commit), **MEASURED** (checked in the files), and **POLICY** (what this analysis decides; not settled by source). Commits: fg1 production `HaiwangYu/wire-cell-toolkit` branch `sbnd-wc-flatcaf` **`4b6853d4`** (read at that commit unless stated), larwirecell `ad5d942`, sbndcode `v10_14_02_03`; upstream `WireCell/wire-cell-toolkit` `2ce0940a` and `SBNSoftware/sbncode` `62ab1658`, `sbnanaobj` `0537d227`, `sbndcode` `cf4a58ff` (HEAD, 2026-11-09) for items not in the fork. Companion: `WIRECELL_TRUTH_MATCH_SEMANTICS.md`.

## 1. `nu_index` candidate ordering
* **Source** (`clus/src/TaggerCheckNeutrino.cxx` lines 2776-2790, 3018, 4186 at `4b6853d4`): the candidates are the in-window flash bundles that survive the cosmic vetoes (`nu_per_bundle`, no hard cap). They are **sorted by the length of the bundle's selected activity, longest first, ties by lower flash `gid`** (`std::stable_sort`), and `nu_index` is the position after the sort. The comment states the intent: slot 0 holds the same candidate the pre-`pr/94` single-candidate selector would have chosen, so `nu_index == 0` means "primary". It is a **length ordering, not a score or neutrino-likeness ordering**.
* **Measured:** policy `first` (nu_index 0) selects 626 events vs 649 for `any` on the BNB CV (`CANDIDATE_POLICY_AUDIT.md`).
* **Policy (ours, unchanged):** `any` (an event passes if any candidate passes) is the baseline; `first` is the comparison. Which of the two the collaboration wants is a policy decision.

## 2. `nu_dedup_flash_group`
* **Source:** C++ default `false` (`TaggerCheckNeutrino.h:801`); the jsonnet knob `nu_dedup_flash_group = false` ("built, measured and left OFF; flipping it is a separate owner decision", `cfg/.../wct-pr-perevt.jsonnet`). When on, candidates sharing a `flash_group` (one physical flash seen by both drift volumes, `Bundle::flash_group` = min gid of the group, `NuBundleCensus.h`) collapse to the longest after the sort above, and the dropped bundle keeps a census row with reason `kDedupFlashGroup = 6`. A separate rev-4 knob `nu_bundle_flash_group` merges bundles that touch at the cathode.
* **Measured:** in the first 120 BNB CV files no `T_bundle` has reason 6 (reasons 0/1/2/3 = 813/25/408/168): the dedup was OFF (`tables/official_signal/dedup_flash_group_check.json`).
* **Policy:** the table carries `policy_dedup_keep` / `dedup_any` as an **offline diagnostic** reproducing what the knob would do; the baseline does not use it.

## 3. `kine_energy_included == 3`
* **Source** (`clus/src/NeutrinoKinematics.cxx:655` and the comment `PRShower.cxx:585` "only type 3 is penalized"): for a **shower row**, `included = (vtx_type != 3 ? 1 : vtx_type)`, i.e. 3 exactly when the shower's start-vertex connection type is 3 (a detached / weakly connected, "leftover" shower; rows with type > 3 are skipped unless in `conn4_keep_showers`). Track rows pass `include_flag = 1` at every call site. The header (`NeutrinoTaggerInfo.h:59-63`) states the key fact: **rows flagged `!= 1` ARE inside `kine_reco_Enu`**, because both the toolkit and the prototype sum `kine_energy_particle` unconditionally "despite the flag's name"; `kine_energy_flagged` is their sum.
* **Policy:** whether a row with `included == 3` counts in the exclusive reco proton multiplicity is an analysis choice, not settled by source. The frozen baseline counts it as the row it is; the effect is measured (`tp_*`/`rp_leftover_inc3` in the Phase-4 migration tables: 7 of the 14 truth-0p → reco-1p cases).

## 4. Reco proton-row construction
* **Source** (`NeutrinoKinematics.cxx`, `fill_kine_tree`): one `T_kine` row per object reached by the energy walk. Track rows (`push_segment_kine`, pools 0 main walk, 1 walk continuation, 3 orphan track, 4 guard-freed track, 5 near cross-cluster track) take `pdg = seg->particle_info()->pdg()` and `KE = particle_info()->kinetic_energy()`; shower rows (pool 2) take `shower_kine_pdg(shower)` and the shower's `kine_best`; `kine_energy_info` is 0 dQ/dx, 1 range, 2 charge. The PDG of a row is **the particle-ID assigned by the pattern recognition itself**; there is no separate classifier, and a "proton" can be a track or a nucleon-typed (leftover) shower (binding-energy correction for proton showers > 5 cm).
* **Policy:** "reco proton" = a row of type 2212 with KE > 35 MeV (provisional).

## 5. Shower selection for the BDT inputs (`shw_sp_*`)
* **Source** (`NeutrinoTaggerSinglePhoton.cxx` at `4b6853d4`, lines 100-103, 1611, 2473-2505): `shw_sp_energy` is the energy of **`max_shower` only**: the highest-`kine_best` shower among those with `en20 && badreco1 && badreco3 && badreco4`, falling back to the highest among `en20 && badreco1`. `shw_sp_20mev_showers` / `shw_sp_br1_showers` are per-shower 0/1 flags; `shw_sp_n_20mev_showers`, `shw_sp_n_20br1_showers` count them. See `WIRECELL_TRUTH_MATCH_SEMANTICS.md` section 6.
* **Policy:** none; the frozen cut `shw_sp_n_20br1_showers <= 1` is inherited.

## 6. Flash time / `FrameShift`
* **Source:** the data chain runs `FrameShift` first (`run_frameshift.fcl`, fg1 README). In step 1, `FlashTensorToOpticalPCs` adds the tensor-set metadata `frame_apply_at_caf` (ns) to every flash/light time when `correct_flash_time` (default true) is set (`aux/src/FlashTensorToOpticalPCs.cxx:90-99`, upstream `2ce0940a`); MC has no such frame offset. The beam window `[0.2, 2.2] µs` is applied to the matched flash time (`Trun.beam_window_low/high_us`); `T_tagger.flash_time_us` is in µs. `ShiftData2MC` is 0 in this release (`FLASH_TIME_CONVENTION_AUDIT.md`).
* **Measured:** the beam-on plateau sits ≈ +0.3 µs above the MC plateau (`FLASH_TIME_CONVENTION_AUDIT.md`).
* **Open (production question, not answerable from source):** is the data-vs-MC optical timing reference supposed to agree to better than 0.3 µs at this stage, or is the offset an expected property of the unshifted data timing?

## 7. `rec.hdr.noffbeambnb` and its beam-on counterpart
Fully in `DATA_EXPOSURE_NORMALIZATION.md` section 0 (sources: `sbncode CAFMaker_module.cc` 948/1009/2876, `FillExposure.cxx`, `SBNDBNBEXTRetriever_module.cc`, `SBNDBNBRetriever_module.cc`; sbnanaobj `SRHeader.h:51`). Caveat for all `sbncode`/`sbnanaobj` citations: they are repository HEAD on 2026-11-09, not the tag used by the production release (`sbncode v10_31_00` per `POT_EXPOSURE_AUDIT.md`); the field semantics are long-standing but the exact line numbers may differ at the tag.

## 8. What is left as true policy or production questions
See the refreshed `QUESTIONS_FOR_HAIWANG_HANYU.md`: candidate policy (`any` vs `first`), `included == 3` rows in the proton multiplicity, flash-time reference, the beam-off scale definition, the 3 candidates with no energy-equal shower row, the 728 units without a flatCAF, the CAF `TotalGenEvents`.
