# Legacy MicroBooNE single-photon scorer: source audit vs the EAF first-look scorer

Date: 2026-11-17. Branch `analysis/ncdelta-source-faithful-legacy-scorer-20261117`, base commit `4873c76fca8a112718326afe90e9f08186bb12da`. Nothing was trained; no XML, threshold or truth convention was changed.

Labels: **SOURCE FACT** (read in the MicroBooNE source tree on EAF, quoted with file and line), **CURRENT EAF IMPLEMENTATION** (read in this repository), **DIFFERENCE**. The Aurora report was not relied on: every statement below was re-read from source.

Source tree: `/exp/uboone/app/users/uboonepro/bbogart/wcp-uboone-bdt` (repository HEAD `8ef26da7`; the `kine_pio_flag` commit `47b1f0c`, "break pi0 flag for sp only", Erin Yandel, 2024-02-26, is an ancestor of HEAD, verified with `git merge-base --is-ancestor`). The four weight files are the ones the EAF scorer loads (sha256 prefixes `5886affb` numu, `8c0ac375` other, `983a0d82` ncpi0, `8580ba04` nue; full hashes in `provenance/microboone_reference_SHA256SUMS.txt`).

## A. Transformation from `EvaluateMVA` to the stored / cut score

- **SOURCE FACT.** `inc/WCPLEEANA/bdt.h:232-262`, the four functions `cal_single_photon_{numu,other,ncpi0,nue}_bdts_xgboost` are identical:
  ```cpp
  float val = -20;
  double val1 = reader.EvaluateMVA("MyBDT");
  val = TMath::Log10( (1+val1)/(1-val1) );
  return val;
  ```
  The result is stored (as `float`) in `tagger.single_photon_<m>_score` (`apps/bdt_convert.cxx:3960-3963`), which is what `T_BDTvars` holds and what the selection reads (`inc/WCPLEEANA/cuts.h:1077-1084`).
- **CURRENT EAF IMPLEMENTATION.** `src/sbnd_single_photon/bdt.py:112` returns `np.tanh(raw)`, i.e. the bare TMVA GradBoost response `v` (`2/(1+exp(-2 raw))-1`); `src/sbnd_single_photon/baseline.py:43-45` stores it as `derived.single_photon_<m>_score`; the cuts in `configs/baseline_selection.yaml` are applied to it.
- **DIFFERENCE.** The EAF scorer stops at `v` and never applies `log10((1+v)/(1-v))`. Note `log10((1+v)/(1-v)) = 2 raw / ln 10 = 0.8686 raw = 0.8686 atanh(v)`. The numerical consequence is that the frozen thresholds were applied on the wrong scale:

| model | frozen cut (score space) | as-run cut on `v` | equivalent cut on `v` (correct) | note |
|---|---|---|---|---|
| numu | > 0.4 | v > 0.4 | v > 0.4305 | as-run is LOOSER |
| other | > 0.2 | v > 0.2 | v > 0.2263 | as-run is LOOSER |
| ncpi0 | > -0.05 | v > -0.05 | v > -0.0575 | as-run is STRICTER |
| nue | > -1.0 | v > -1.0 (vacuous: v > -1 always) | v > -0.8182 | as-run is VACUOUS, corrected is a REAL cut |

(`v = (10^s - 1)/(10^s + 1)`.) Saturation: `v` rounds to exactly -1.0 / +1.0 for |raw| above ~18.7; the source then returns -inf / +inf (no clamp; `-inf` fails and `+inf` passes every `>` cut, which the source-faithful scorer reproduces). The stored value is cast to `float`; the comparison to the double literal is done on the widened float (`float(0.4) = 0.4000000059604645 > 0.4`); the new scorer reproduces this too.

## B. Frozen thresholds

- **SOURCE FACT.** `inc/WCPLEEANA/cuts.h:8899-8906` (`is_singlephoton_sel`): `shw_sp_n_20mev_showers > 0`, `reco_nuvtxX` in (5, 250) (MicroBooNE fiducial cut, not an SBND cut), `single_photon_numu_score > 0.4`, `single_photon_other_score > 0.2`, `single_photon_ncpi0_score > -0.05`, `single_photon_nue_score > -1.0`, `shw_sp_n_20br1_showers == 1`. A looser "efficiency" selection (0.1 / -0.4 / -0.4 / -3.0) also exists (`:8908-8916`) and is NOT used by the baseline.
- **CURRENT EAF IMPLEMENTATION.** `configs/baseline_selection.yaml:31,40,49,58` and `selection/microboone_single_photon_selection.yaml:8-11`: the same four numbers 0.4 / 0.2 / -0.05 / -1.0 (the reco-vertex fiducial window is deliberately not applied).
- **DIFFERENCE.** None in the numbers. The numbers are right and the scale they were applied on was wrong.

## C. Do all four single-photon BDTs use the transformed score?

- **SOURCE FACT.** Yes: all four functions at `bdt.h:232-262` apply the identical transform, and all four are consumed by `is_singlephoton_sel`.
- **CURRENT EAF IMPLEMENTATION.** None of the four is transformed.
- **DIFFERENCE.** Applies to all four (numu, other, ncpi0, nue).

## D. Treatment of `kine_pio_flag`

- **SOURCE FACT.** In `apps/bdt_convert.cxx` the single-photon `ncpi0` reader binds its 45 inputs at `:2723-2768`; the input `kine_pio_flag` is bound to the scratch variable `temp_kine_pio_flag` (`:2757`; the line binding it to `kine.kine_pio_flag` is commented out at `:2758`). In the event loop `temp_kine_pio_flag = kine.kine_pio_flag;` is set at `:3858`, and then, immediately before the four single-photon scores are computed, overwritten (`:3957-3958`):
  ```cpp
  //uncomment to match old files
  temp_kine_pio_flag = 0;
  ```
  Commit `47b1f0c` (2024-02-26) added exactly this override and removed an earlier `temp_kine_pio_flag = -1;` ("uncomment to match old files"). The production scores therefore see `kine_pio_flag = 0` for every event.
- **CURRENT EAF IMPLEMENTATION.** `src/sbnd_single_photon/bdt.py:25-41`: `kine_pio_flag` is read from `wc.T_kine.kine_pio_flag`, the real CAF value, and fed to the `ncpi0` BDT.
- **DIFFERENCE.** Real flag in EAF, 0 in the source.

## E. Scope of the `kine_pio_flag = 0` override

- **SOURCE FACT.** Only the single-photon `ncpi0` reader has `kine_pio_flag` as an input (`bdt_convert.cxx:2757`; the XML `single_photon_{numu,other,nue}_bdt_final.xml` do not list it; checked by the 73 / 146 / 56 variable counts of the readers, none of which name it). The override is placed after every non-single-photon BDT (the legacy NC pi0 BDT `reader_nc_pi0` also uses `temp_kine_pio_flag`, `:2476`, and is evaluated earlier in the same iteration with the real flag), and `kdar` uses `ssm_kine_pio_flag`. So: **only the single-photon `ncpi0` score, in the production path of `bdt_convert`**; every event, MC and data (no condition). The scalar is `temp_kine_pio_flag`, shared with the NC pi0 reader, but the NC pi0 score is computed before the override.
- **CURRENT EAF IMPLEMENTATION.** Real flag in the single-photon `ncpi0` input.
- **DIFFERENCE.** Affects only `ncpi0`, via 1 of 45 inputs.

## F. Other overrides / preprocessing (all single-photon readers)

Each of the 73 / 146 / 45 / 56 `reader_single_photon_*.AddVariable` calls (`bdt_convert.cxx:2498-2829`) was parsed and the bound field compared with the XML variable name:

| item | SOURCE FACT | CURRENT EAF IMPLEMENTATION | DIFFERENCE |
|---|---|---|---|
| feature order | `AddVariable` order; TMVA maps by name to XML `VarIndex` (XML has 73 / 146 / 45 / 56 variables) | `TmvaBdt.var_list` sorted by `VarIndex`; counts checked (`EXPECTED_NVARS`) | none |
| name vs field | all 320 variables bind the field of the same name except `numu_cc_3_track_length` -> `tagger.numu_cc_3_acc_track_length` and `kine_pio_flag` -> scratch variable | CAF branch is written as `numu_cc_3_track_length` from the same field (`tagger.h:5174`), so the CAF value is the same quantity | none (the flag is item D) |
| `em_charge_scale` | `float em_charge_scale = 1.0;` (the data scaling `0.95` is commented out, `:3932-3933`); applied to the `shw_sp_vec_dQ_dx_*` / median / mean dE/dx inputs | not applied (equivalent to 1.0) | none |
| NaN replacement | explicit `isnan -> 0` only for `cosmict_4/7_*` (`:3902-3905`, inputs of the non-single-photon numu chain, not inputs of the four SP models) and for `ssm_*` (after the SP scoring, `:3965-`) | a candidate with any non-finite SP input is marked NOT evaluable and fails every BDT cut (`bdt_evaluable`) | **difference in policy**, not corrected here: TMVA would score the candidate (a NaN compares false, `cType=1`, so goes to the left child). It affects 5 non-evaluable-by-NaN candidates in the 12,409-candidate official sample (`bdt_reason == nonfinite_input`; the other 3,927 `shw_sp_filled == 0` rows are unscored in the source too, their inputs are sentinels). Kept as is and labelled |
| inputs that are other BDT outputs | the `other` BDT takes `numu_score`, `numu_1_score`, `numu_2_score`, `cosmict_10_score`, already log-odds in the production CAF (documented in `FROZEN_OTHER_BDT_SOURCE_AUDIT.md`) | read from the CAF (production) | none |
| float width | TMVA `DecisionTreeNode` cut and leaf `res` are `Float_t`; inputs are `Float_t` | float64 parse of the XML decimal text | previously audited (`other_audit.n_tie_cases`, `remaining_audit.py`); expected effect below the 1e-6 level on `v` |
| candidate / event logic | `is_singlephoton_sel` is evaluated per tagger entry (one per neutrino candidate) | `candidate_policy: any`, `first`, `dedup_any` over candidates | none to do with the scorer (policy is an analysis convention) |

No other input override, default value or preprocessing in the single-photon scoring path was found.

## Impact on the EAF scorer: the exact lines

1. `src/sbnd_single_photon/bdt.py:112` (`np.tanh(raw[rows])` is returned as the score; the missing `log10((1+v)/(1-v))` step).
2. `src/sbnd_single_photon/bdt.py:27-41` (`KINE_INPUTS_NCPI0` includes `kine_pio_flag`, which is fed from `wc.T_kine.kine_pio_flag`; the source feeds 0).
3. `src/sbnd_single_photon/baseline.py:43-45` and `scripts/build_analysis_table.py:205-206` (the stored `c_score_*` columns are therefore `v`; cum_ flags are cut on `v`).
4. `configs/baseline_selection.yaml:31-58` (thresholds are source numbers but applied on `v`; with `v`, the `nue > -1.0` cut is vacuous).

## Validation reference available (Task 4)

The production CAFs do not store the single-photon scores (`configs/baseline_selection.yaml` header). The prior TMVA validation (`analysis/microboone_1gamma_v0/docs/TMVA_VALIDATION.md`, 132 / 132 candidates against PyROOT `EvaluateMVA`) validates `v` only. PyROOT is not installed on this machine. There is therefore NO stored-score or live-TMVA reference for the post-transform score or for `kine_pio_flag = 0` here: the source-faithful scorer is validated by (i) exact algebra against hand-computed values, (ii) reproducing the as-run stored scores from the stored inputs bit-for-bit (as-run mode), and (iii) the independent source reading above. Exact reproduction of the MicroBooNE production scores is NOT claimed.
