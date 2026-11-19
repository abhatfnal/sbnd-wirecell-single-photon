# SP other on WCL1116: development report

Dates: 2026-11-17 (preparation), 2026-11-19 (staging verified, models developed). Campaign `development_wcl1116_v1`;
branch `round2/sp-other-nue-wcl1116-development-20261117`.

**Status: DEVELOPED (both vertex modes, `…_DEV_DO_NOT_DEPLOY`, `UPSTREAM_NUMU = SHIPPED_CONTROL`). Retraining verdict:
RETRAINING CLEARLY BENEFICIAL.**
- Every number is an Aurora **DEVELOPMENT HOLDOUT** result, not an independent end-to-end measurement
  (`AURORA_UMBRELLA_MODEL_TRAINING_AND_EVALUATION_POLICY.md`).
- No FermiGrid evaluation product was read. The only FermiGrid-derived input is the pre-designated odd-run beam-off
  TRAINING partition, under the approved exception.
- **SP other MUST be retrained again in the final reconstruction domain** (§9).

## 1. Staging the beam-off training partition

- **Route.** Xuyang's established one (`xning/bdt-comm/PLAN.md:83`):
  1. `rsync` over ssh, pushed from a Fermilab gpvm in Avinay's ALCF session;
  2. `--copy-links` through a links directory;
  3. dCache ADLER32 recorded on the gpvm.

  Scripts: `tools/beamoff_staging/`.
- **Transfer (Avinay, 2026-11-18).**
  - 558 / 558 selected files, 4,679,220,283 bytes sent, `missing.txt` empty;
  - destination `$SP_WORK/wcl1116_beamoff_train/`.
- **Verification** (`tools/verify_staged_beamoff.py` → `manifests/wcl1116_dev_v1/beamoff_train_staging.{json,tsv.gz}`):

| check | result |
|---|---|
| expected / staged / verified | **558 / 558 / 558** |
| missing / duplicate / unknown / hold-out / even-run | 0 / 0 / 0 / 0 / 0 |
| size and dCache ADLER32 vs the gpvm source manifest (sha256 recorded) | 0 failures |
| both Wire-Cell trees present; `ismc == 0`; header run = name run = membership run (odd) | 558 / 558 |
| `wct_version` (both trees) | `HEAD-0.38.0` in 558 / 558, the same in both trees |
| `dl_weights` exactly `<mode>:dv2max/sbnd/aurora_space/bundle.json@sha256:51588842…` per tree | 558 / 558 |
| reconstruction / checksum / data-MC failures | 0 / 0 / 0 |
| training list | `$SP_WORK/wcl1116_dev/lists/wcl1116-fg-beamoff-train.txt`, 558 lines, sha256 **`8f2ea601…`**, made read-only |

- **Toolkit provenance** (`WCL1116_TOOLKIT_PROVENANCE_NOTE.md`, `sp_retrain/provenance.py`).
  - The first verification (2026-11-18) stopped on one condition only: the FermiGrid files stamp `HEAD-0.38.0`,
    where the Aurora files stamp `0.38.0`.
  - Avinay then checked the gpVM build: its `TARBALL-PROVENANCE.txt` records `WIRECELL_VERSION "HEAD-0.38.0"` and
    `wire-cell-toolkit c935e30d 0.38.0 0 dirty cfg files`.
  - He approved treating **exactly** these two strings as the same build of `c935e30d44a09bf208f6de2c2968171b01efd63d`
    for this campaign. This is a closed list, not a version parser; post-tag, branch and unknown stamps are rejected
    in tests.
  - Each file stores only the string. The SHA comes from the campaign-level build record.
- **Stricter in the same change:**
  - `dl_weights` is compared exactly, per tree;
  - the two trees of a file must agree, and the sample must carry one stamp;
  - approved firewall path prefixes stop at a directory boundary (`wcl1116_beamoff_train_x/` is refused).

## 2. Target and spec (frozen 2026-11-17, unchanged)

| item | frozen as |
|---|---|
| positive | `T_match` partner neutrino with `sp_signal`, all 5 categories (p.127; Fig. 5.8) |
| negative | NC without π⁰ (`NCBkg`); `outFVBkg`, split into dirt (true vertex outside the active TPC) and in-TPC out-of-FV; `T_match` partner cosmic or none (assumption A4); every preselected EXT row (p.129). Signal takes precedence; EXT is never positive |
| inputs | 146, XML order (`0c3d3083…`): 59 direct cosmic-tagger outputs, `cosmict_10_score`, `numu_score` / `numu_1_score` / `numu_2_score` (shipped upstream: **SHIPPED_CONTROL**), 81 `shw_sp_*`, `numu_cc_flag`, `kine_nu_y_corr` |
| XGBoost | depth 5, 215 trees, eta 0.1, `binary:logitraw`, colsample 1 / 0.5 / 0.5, subsample 0.8, gamma 0.2, seed 1, `base_score` 0; no weights, no tuning |
| split | MC: odd subrun → holdout; EXT: run % 4 == 1 → holdout (every off-beam file has art subrun 1) |
| legacy control | `single_photon_other_bdt_final.xml` sha256 `8c0ac375e957f5b3…` (146 / 215 / depth 5), score log10((1+v)/(1−v)), historical cut 0.2 |

Specs: `specs/single_photon_other_training_spec_dev_wcl1116_{dv2_split_move,dv2_snap}.yaml`, now
`READY_FOR_DEVELOPMENT_TRAINING`. The EXT entry carries the verified list hash, `wct_version_stamp: HEAD-0.38.0`
and the toolkit commit. The two specs differ only in their reconstruction block.

## 3. Sample census (`validation/sp_other_census_wcl1116.json`)

EXT tables: PBS 9102859, `neutrinoGPU::WireCell_aurora`, about 30 s per tree. 558 files, 0 errors, 26,418 events,
2,495 candidates per tree, stamp `HEAD-0.38.0`. NC Δ and BNB tables are reused unchanged.

| | split-move | snap |
|---|---:|---:|
| **positive** rows (events) | 17,582 (17,577) | 17,412 (17,407) |
| positive train / holdout | 8,761 / 8,821 | 8,667 / 8,745 |
| **negative** rows (events) | 15,629 (15,613) | 15,696 (15,677) |
| negative train / holdout | 7,881 / 7,748 | 7,939 / 7,757 |
| NC without π⁰ | 3,822 | 3,849 |
| dirt | 7,263 | 7,298 |
| out-of-FV inside the TPC | 843 | 846 |
| cosmic-matched MC | 3,192 | 3,195 |
| **refreshed EXT / beam-off** rows (train / holdout) | **509** (285 / 224) | **508** (283 / 225) |
| EXT fraction of the negatives | **3.26 %** | 3.24 % |
| non-finite classed rows | 0 | 0 |
| events with > 1 classed candidate / > 1 component | 62 / 48 | 66 / 50 |
| files dropped by the stamp filter (any sample) | 0 | 0 |

- **EXT yield vs the old reconstruction:** 481 usable rows (train 267 / holdout 214) on the same 558 files, against
  509 / 508 now (+5.8 % / +5.6 %).
  - The number of events (26,418) and candidates (2,495 vs 2,494) is the same.
  - The difference is in how many candidates pass the preselection after the refresh. It was not forced.
- The MC components are unchanged from the 2026-11-17 MC-only census (`validation/sp_other_census_wcl1116_mc_only.json`).
  The positives equal the SP numu development positives (the shared signal sample).

## 4. Development models

| | split-move | snap |
|---|---:|---:|
| model | `single_photon_other_sbnd_wcl1116_dv2_split_move_DEV_DO_NOT_DEPLOY` | `…_dv2_snap_DEV_DO_NOT_DEPLOY` |
| train rows +/− | 8,761 / 7,881 | 8,667 / 7,939 |
| holdout rows +/− | 8,821 / 7,748 | 8,745 / 7,757 |
| train AUC | 0.9687 | 0.9670 |
| **holdout AUC** | **0.9153** | **0.9121** |
| train / holdout gap | 0.053 | 0.055 |
| model sha256 / exported XML sha256 | `144638a5…` / `857e9d60…` | `81fbc1e0…` / `d814252e…` |
| leakage (overlapping events, duplicate rows, multi-file events) | 0 / 0 / 0 | 0 / 0 / 0 |
| repeat | byte-identical JSON | byte-identical JSON |

- Manifests: `manifests/wcl1116_dev_v1/single_photon_other_<mode>_dev_manifest.json`. They carry the input list
  hashes, including the EXT list `8f2ea601…`, the expected stamp per sample, the table, spec, feature and code
  hashes, and the counts.
- Outputs: `$SP_WORK/wcl1116_dev_models/<mode>/other/`.
- The gap (0.053) lies between SP numu / nue (0.02) and SP ncpi0 (0.09), with 16.6k training rows.

## 5. Legacy control and ROC-equivalent diagnostics

On **identical** holdout rows: 16,569 / 16,502, 0 excluded, rebuilt rows equal to the stored ones.

**DEVELOPMENT ROC-EQUIVALENT DIAGNOSTIC — NOT ROUND2 CUT.** The legacy cut is never carried onto the native margin.

| | split-move | snap |
|---|---|---|
| legacy AUC | 0.8398 | 0.8360 |
| SBND-dev AUC | **0.9153** | **0.9121** |
| gain (± bootstrap sd, 200 event resamples) | **+0.0755 ± 0.0025** | **+0.0761 ± 0.0028** |
| Spearman dev vs legacy score: all / signal / background | 0.777 / 0.594 / 0.599 | 0.773 / 0.599 / 0.601 |
| legacy at 0.2: signal efficiency / background acceptance | 57.4 % / 11.4 % | 57.2 % / 11.8 % |
| dev, background acceptance at equal signal efficiency | **3.28 %** (× 0.29) | **3.27 %** (× 0.28) |
| dev, signal efficiency at equal background acceptance | **78.8 %** (+21.4 points) | **79.2 %** (+22.0 points) |

**By negative component, split-move** (`validation/sp_other_component_acceptance_wcl1116.json`). Holdout acceptance,
legacy at 0.2 → dev at equal signal efficiency:
- NC without π⁰: 11.7 % → 3.7 %;
- dirt: 13.3 % → 3.5 %;
- out-of-FV in the TPC: 18.2 % → 5.7 %;
- cosmic-matched MC: 5.4 % → 1.9 %;
- EXT: 5.4 % → 0.9 % (224 rows).

Every component drops, and snap behaves the same.

## 6. Retraining-benefit verdict: RETRAINING CLEARLY BENEFICIAL

The rule was pre-registered in `tools/wcl1116_mode_compare.py` (2026-11-17, before any SP nue / SP other fit) and is
unchanged:
- BENEFICIAL: both modes gain ≥ 0.010 and > 3 σ;
- COMPETITIVE: both modes gain ≤ 0.002;
- otherwise NEUTRAL / NOT RESOLVED.

SP other gains +0.076 in both modes, at 30 σ and 27 σ. This is the largest gain of the four SP models
(`validation/wcl1116_mode_compare_other.json`).

## 7. Feature sanity (`validation/sp_other_feature_sanity_wcl1116.json`)

| family (inputs) | legacy split share | dev split share: split / snap | dev gain share: split / snap |
|---|---:|---:|---:|
| upstream scores (4): `numu_score`, `numu_1_score`, `numu_2_score`, `cosmict_10_score` | 8.7 % | 7.7 % / 8.0 % | 9.8 % / 9.7 % |
| direct cosmic tagger (59) | 10.3 % | 9.8 % / 9.2 % | 11.1 % / 10.8 % |
| shower `shw_sp_*` (81) | 76.6 % | 79.5 % / 80.0 % | 76.7 % / 77.4 % |
| vertex `kine_nu_y_corr` (1) | 3.7 % | 2.7 % / 2.4 % | 1.4 % / 1.4 % |
| `numu_cc_flag` (1) | 0.7 % | 0.2 % / 0.3 % | 0.9 % / 0.8 % |

- **Upstream νμ.** `numu_score` is split rank 3 / 2 (legacy rank 1); `numu_1_score` is rank 2 / 1 (legacy 4).
  `cosmict_10_score` is gain rank 6 / 7, against split rank 69 in the legacy model. `numu_2_score` is rarely used, as
  in legacy (rank 92).
- **Top 20 by splits (split-move):** `shw_sp_E_indirect_max_energy`, `numu_1_score`, `numu_score`, `kine_nu_y_corr`,
  `shw_sp_shw_vtx_dis`, `shw_sp_medium_dQ_dx`, `shw_sp_vec_dQ_dx_0`, `shw_sp_max_shw_dis`, `shw_sp_stem_length`,
  `shw_sp_br4_1_shower_total_length`, … These are the shower-energy, upstream-νμ, vertex-position, conversion-distance
  and dQ/dx inputs. **17 / 20** are in the legacy top 20 (snap 16 / 20).
  - Spearman of all split counts vs legacy: 0.933 / 0.931.
- **Top by gain:**
  - `shw_sp_lem_e_charge` 13.8 %;
  - `shw_sp_length_total` 6.8 %;
  - `cosmict_flag` 6.7 %: the summary cosmic-tag decision is the single largest cosmic-tagger lever;
  - `shw_sp_E_indirect_max_energy` 5.9 %;
  - `shw_sp_br4_1_shower_total_length` 5.0 %;
  - `cosmict_10_score` 3.7 %;
  - `numu_score` 3.4 %.
- **Aggregate νμ + cosmic dependence:** about 21 % of the gain comes from the upstream scores plus the direct
  cosmic-tagger outputs.
- No bookkeeping identifier is an input.
- Inputs never split: 18 (split-move) / 20 (snap), against 13 in the legacy forest. They are almost all cosmic-tagger
  sub-blocks 3 / 5 / 6 / 7 / 8 (`*_filled`, `*_flag_*`), which are rarely filled in SBND.

## 8. Snap vs split-move (development evidence only)

| level | split-move | snap |
|---|---|---|
| positives / negatives (rows) | 17,582 / 15,629 | 17,412 / 15,696 |
| EXT rows | 509 | 508 |
| legacy AUC | 0.8398 | 0.8360 |
| dev AUC | 0.9153 | 0.9121 |

**Matched candidates** (same key, same class, finite in both):
- 15,901 rows (8,541 + / 7,360 −); 4 class disagreements; 664 rows only in split-move, 597 only in snap;
- dev AUC 0.9155 vs 0.9125: **snap − split = −0.0029 ± 0.0010**;
- legacy: −0.0036 ± 0.0012;
- Spearman of the dev margins split vs snap: 0.957.

**Reading:** SP other's development evidence **favours split-move**, by a small amount resolved at about 3 σ. That
matches the sign seen for SP numu (−0.0015), ncpi0 (−0.0010) and nue (−0.0059). It is not a vertex-mode decision.

## 9. Export, equivalence, and what final training needs

- **Python** (`validation/wcl1116_export_equivalence_other_<mode>.json`): **all pass** in both modes.
  - 215 trees, depth 5, XML names = feature list;
  - max |native margin − XML forest sum| 5.4e-6 / 5.9e-6;
  - equality routing 1,200 / 1,200;
  - ±FLT_MAX: 0 leaf mismatches;
  - NaN → −999 (50 / 50);
  - order guard refuses;
  - 0 flips at the fixture cut 0.2 and at 5 quantile midpoints.
- **C++: VERIFIED.** TMVA::Reader and the toolkit `TmvaGradForest`, run in Haiwang's SL7 WCT 0.38.0 environment on a
  compute node: PBS 9102928, `neutrinoGPU::WireCell_aurora`. Summaries:
  `validation/cpp_export_equivalence_wcl1116_<mode>_other.json`. Each mode has 3,310 fixture rows: 3,000 holdout, 300
  on exact split thresholds, 5 NaN and 5 ±FLT_MAX.
  - Reader == forest bit-identical on 3,310 / 3,310 rows in both modes.
  - C++ vs Python `tmva_grad` ≤ 4.4e-16, and bit-identical on 3,278 / 3,283 of 3,305 finite rows.
  - tanh(native margin) vs C++ ≤ 6.6e-7.
  - NaN → −999 in both readers; the swapped order is refused; 0 flips at the fixture cut and 5 quantile midpoints.

**SP other MUST be retrained again in the final reconstruction domain.**
- Haiwang's next production is expected to bring the measured non-box / effective boundary into `cosmic_tagger()`.
- 59 of SP other's 146 inputs are direct cosmic-tagger outputs; with `cosmict_10_score`, 60 are cosmic-tagger based.
  Its leading upstream input, `numu_score`, is itself built mostly from cosmic-tagger outputs (61 / 74).
- It also waits for Xuyang/Matteo's frozen upstream νμ, and for the refreshed beam-off training half reprocessed in
  that domain, through the same staging route and verifier.

**What this development result is for.** It establishes the complete four-classifier SBND baseline on WCL1116, and
validates the target, sample, staging, firewall, export and C++ machinery end to end. It also shows, before the final
production, that SBND retraining of SP other is clearly beneficial (+0.076 AUC, every negative component reduced). The
final retraining is then a re-run of a validated pipeline, not new development.
