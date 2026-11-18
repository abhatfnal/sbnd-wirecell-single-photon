# SP other on WCL1116: development report

Date: 2026-11-17. Campaign `development_wcl1116_v1`; branch `round2/sp-other-nue-wcl1116-development-20261117`.

**Status: SP-OTHER BLOCKED ONLY ON TRANSFER EXECUTION.**
- Everything else is ready: the target audit, the specs, the narrowly scoped exception, the MC census, the staging
  commands, the staging verifier and the build / train / control / export path.
- No SP other model was trained. A model without its EXT component would not be the source-established target, and no
  evaluation beam-off was substituted.
- Policy: `AURORA_UMBRELLA_MODEL_TRAINING_AND_EVALUATION_POLICY.md`. Every number here is development-side.

## 1. Staging the beam-off training partition (Task 1–2)

- **Supported route (found, not invented).** Xuyang staged the same partition from the old fg1 reconstruction on
  2026-11-10 (`xning/bdt-comm/PLAN.md:83`; `inbox/updates-1828.md` §4):
  1. `rsync` over ssh, pushed from a Fermilab gpvm, in a session the user opens (ALCF one-time passcode);
  2. `--copy-links` through a links directory;
  3. per-file sizes and dCache ADLER32 committed on the gpvm (`data/fg1-beam-off-train.sizes-adler32.tsv`) and
     compared on Aurora.
- **Rejected:** pulling with `xrdcp` / `gfal-copy` from Aurora, because it would put a Fermilab token on Aurora, which
  Xuyang deliberately avoided. Globus is untested.
- **Why it was not executed here.** Aurora has no `/pnfs`, and Haiwang has published no WCL1116 training-side split or
  links directory (catalogue `main` `f4f2f93`; ai-helper issue 48 `e75e403`). The push needs Avinay's gpvm login and
  ALCF passcode.
- **Prepared** (`tools/beamoff_staging/`):
  - `gpvm_stage_wcl1116_beamoff_train.sh` reads the 558 frozen ids. For each it requires exactly one merged CAF, records
    the size and dCache ADLER32 (`.(get)(file)(checksum)`), and reports a missing pair instead of substituting one. It
    then makes the links directory and pushes with one ssh master connection to
    `$SP_WORK/wcl1116_beamoff_train/`, which is in Avinay's area.
  - `README.md` gives the step-by-step.
- **Verifier** (`tools/verify_staged_beamoff.py`):
  - membership: one of the 558, no hold-out id, no unknown or duplicate id;
  - run: odd, in the name and in the header, equal to the membership run;
  - checksums: size and ADLER32 equal the gpvm record; sha256 recorded;
  - reconstruction: WCL1116, i.e. both trees, `wct_version` `0.38.0` and the `aurora_space` bundle hash;
  - data: `ismc == 0`.

  It writes a training list only if every file passes and none is missing.
- **Self-test** (`validation/beamoff_staging_verifier_selftest_old_fg1.json`), on Xuyang's OLD fg1 copy, 6 files:
  - membership, odd runs and dCache ADLER32 pass (0 checksum failures);
  - all 6 are **rejected** as not WCL1116: no `recTreeWireCell_dv2snap`, `wct_version …-g78f81c64`.

  The old and refreshed reconstructions therefore cannot mix.

| staging item | value |
|---|---|
| files expected | 558 (572 frozen odd-run pairs − 14 hold-out files; 80 runs, all odd) |
| files staged | 0 |
| evaluation-half / hold-out / unknown files | 0 / 0 / 0 (nothing staged; the membership manifest itself has none) |
| status | **BLOCKED ONLY ON TRANSFER EXECUTION** |

## 2. Target and spec audit (Task 4)

Read: `YANDEL_THESIS_SP_BDT_TRAINING_SOURCE_AUDIT.md` §4, `SP_BDT_DEPENDENCY_AND_TARGET_AUDIT.md`,
`specs/single_photon_other_training_spec_v0.2.yaml` (v0.2.3) and `config/features/single_photon_other_inputs_v0.json`
(146 inputs, sha256 `0c3d3083…`).

| item | source | frozen in the dev spec as |
|---|---|---|
| positive | the inclusive single-photon signal shared by the four BDTs (p.127; Fig. 5.8 caption) | `T_match` partner neutrino with `sp_signal`, all 5 categories |
| negative components | p.129: NC without π⁰, dirt, out-of-FV (cryostat, outside the 3 cm FV), cosmic (overlay: a cosmic flash-cluster pair chosen as the candidate; EXT: off-beam data); Fig. 5.8 "NC, out of FV, dirt, cosmic, and extbnb" | `NCBkg`; `outFVBkg` (split into dirt = true vertex outside the active TPC, and in-TPC out-of-FV); `T_match` partner cosmic or none; every preselected EXT row |
| signal override | p.129: rows of the first three components that fit the signal are signal; EXT is always background | positive takes precedence; EXT rows are never positive |
| rows / preselection | p.127, p.134: after preselection | as ncpi0 / numu |
| inputs | 146, XML order (EAF fingerprint: Fig. E.2 = XML split counts) | feature list `0c3d3083…`; `reco_nuvtxY` ← `kine_nu_y_corr` |
| XGBoost | App. E.2: depth 5, 215 trees, eta 0.1, `binary:logitraw`, colsample 1 / 0.5 / 0.5, subsample 0.8, gamma 0.2, seed 1 | the same; `base_score` 0 (development convention, as for all SP models) |
| legacy control | `single_photon_other_bdt_final.xml` sha256 `8c0ac375…`, historical cut 0.2 | `legacy_control` (verified bundle) |

**Not stated by the source, and documented, not guessed:**
- *Component proportions and weights* (27,377 total, split not given). We use natural proportions and no weights, the
  same development convention as the siblings.
- *The truth expression for "cosmic".* MicroBooNE's `badmatch` is `match_completeness_energy ≤ 0.1·truth_energyInside`.
  We use the thesis description, "a cosmic … selected as the neutrino candidate", under assumption A4: the `T_match`
  partner is a cosmic, or there is none, with no completeness cut. This is the same matching assumption as SP numu /
  ncpi0.
- *The two `_calc` names* in Fig. E.2. The model is the XML, and the XML names are used.

**Verdict:** the target is source-established and frozen in
`specs/single_photon_other_training_spec_dev_wcl1116_{dv2_split_move,dv2_snap}.yaml`, which differ only in their
reconstruction block. There is no field ambiguity that would stop a fit; the only gap is data access.

## 3. Census of the available components (Task 5, MC only; `validation/sp_other_census_wcl1116_mc_only.json`)

| | split-move | snap |
|---|---:|---:|
| non-placeholder candidates (NC Δ + BNB) | 320,391 | 320,391 |
| preselected | 82,005 | 82,279 |
| classed rows (finite) | 32,702 | 32,600 |
| non-finite classed rows | 0 | 0 |
| **positive** rows (events) | 17,582 (17,577) | 17,412 (17,407) |
| positive train / holdout | 8,761 / 8,821 | 8,667 / 8,745 |
| **negative** rows (events), MC only | 15,120 (15,104) | 15,188 (15,169) |
| negative train / holdout | 7,596 / 7,524 | 7,656 / 7,532 |
| NC no π⁰ | 3,822 (BNB 3,691, NC Δ 131) | 3,849 |
| dirt (true vertex outside the active TPC) | 7,263 (BNB 7,007) | 7,298 |
| out-of-FV inside the TPC | 843 | 846 |
| cosmic-matched MC | 3,192 (BNB 3,033) | 3,195 |
| beam-off / EXT | **0 (not staged)** | **0 (not staged)** |
| events with > 1 classed candidate | 62 | 66 |
| events with > 1 component | 48 | 50 |

- The positive rows equal the SP numu development positives in each mode (8,761 + 8,821 for split-move), because the
  same signal sample is shared.
- The MC negatives are 6.5 % below the aurora-r2 count (15,281).
- **Beam-off contribution.** It is not measurable until staging.
  - On the old fg1 reconstruction the training half gave 481 usable rows, 3.1 % of the "other" negatives.
  - If the refresh gives a similar yield, EXT will be about 3 % of the negative class. The thesis gives no figure for
    the EXT share of its 27,377.

## 4. What runs the moment the files are verified

1. `tools/make_wcl1116_dev_specs.py --only other` turns the specs `READY_FOR_DEVELOPMENT_TRAINING`, with the verified
   list hash.
2. Build `wcl1116-fg-beamoff-train` tables for both trees (`--approved-exceptions-spec`; 558 small files).
3. Run `sp_other_census.py` again, now with EXT.
4. Train one fixed-spec model per mode: `single_photon_other_sbnd_wcl1116_<mode>_DEV_DO_NOT_DEPLOY`,
   `UPSTREAM_NUMU = SHIPPED_CONTROL`.
5. Legacy XML control (cut 0.2) on identical holdout rows, ROC-equivalent diagnostics, mode comparison with the
   pre-registered retraining verdict, export, then Python and C++ equivalence.

This is a development model only. SP other must be retrained again after the frozen upstream νμ, the cosmic-boundary
production (60 direct cosmic-tagger inputs plus `numu_score`) and the final reconstruction choice.
