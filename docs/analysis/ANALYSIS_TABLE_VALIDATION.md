# Derived BNB analysis table: construction and exact validation

Scope: the BNB CV baseline only (`bnb_cv`, 37,742 files). The table lives **outside Git**: `/exp/sbnd/data/users/abhat/single_photon_ncdelta/analysis_tables/bnb_cv/` (candidates 28 MB, events 6.6 MB, files 0.9 MB, zstd Parquet; the 113k per-file build pieces, 1.7 GB, are under `pieces/` and are not needed after the merge). Small derived outputs are in Git: `tables/analysis_table/` (validation JSON, metadata copy, channel tables) and `plots/analysis_table/`.

## 1. How it was built

`scripts/build_analysis_table.py bnb_cv --workers 28` re-read every CAF **once** (2,799 s, 0 errors) with the same code paths as the baseline scan (`baseline.read_baseline_arrays`, offline BDT scoring from the original MicroBooNE XMLs: scoring, no training), adding the variables the plot suite and the 1γ0p/1γ1p study need, then `--merge` concatenated the pieces and derived the cut flags **from the stored cut inputs** with `configs/baseline_selection.yaml` (one definition of the chain, `scanio.candidate_chain`). A re-read rather than a conversion of the old npz files was necessary because the old scan stored neither the shower/dQ/dx/E_ν variables nor the proton KE; it also makes the validation below an independent recomputation, not a copy.

Three tables (a single table cannot carry events with zero candidates, which the 500,000 / 499,899 counts need):

| table | grain | rows |
|---|---|---|
| `files` | one source CAF | 37,742 (`source_file`, `TotalPOT`, `TotalGenEvents`, `n_events`, `schema_md5`) |
| `events` | one CAF event (also wc.valid == 0 and zero-candidate events) | 500,000 (run, subrun, evt, `wc_valid`, `ncand`, event truth category `t_code` and details) |
| `candidates` | one Wire-Cell candidate | 241,845 (64 columns) |

Provenance key of every candidate: `(file_index / source_file, run, subrun, evt, c_nu_index)`; unique (checked). The per-file POT bookkeeping identifier is `file_index` → `files.total_pot`.

`candidates` columns (all documented in `metadata.json` → `tables_columns`): `wc.valid` flag (`cum_candidate_in_valid_event`); candidate fields (`c_nu_index`, `c_flash_group`, `c_matched_flash_gid`, `c_flash_time_us`, `c_flash_pe`, `c_flash_tpc`); every baseline cut input (`c_shw_sp_filled`, `c_shw_sp_n_20mev_showers`, `c_shw_sp_n_20br1_showers`) and the four offline scores (`c_score_{numu,other,ncpi0,nue}`); `bdt_evaluable`, `bdt_reason` (`evaluable` / `shw_sp_filled==0` / `nonfinite_input`) and `c_bdt_n_nonfinite_inputs`; cumulative cut flags `cum_<stage>` and `pass_final`; policy flags `policy_first`, `policy_dedup_keep`; reco vertex (`c_kine_nu_{x,y,z}_corr`); shower variables (`c_shw_sp_energy`, `_shw_vtx_dis`, `_min_dis`, `_max_shw_dis`, `_angle_beam`, `_{lowest,medium,highest}_dQ_dx`, `_vec_dQ_dx_{0,1,2}`); `c_kine_reco_Enu`; reco protons (`c_np35`, `reco_proton_cat` 0/1/2, `c_np_any_ke`, `c_lead_proton_ke_mev`, `c_sum_proton_ke_mev`, `c_nrows`); MC truth for evaluation only (`dom_nu`, `dom_q`, `dom_q_cand`, `dom_q_nu`, `dom_nu_pdg`, `dom_nu_ccnc`, `dom_nu_vx/vy/vz`, `dom_ok`; event category in `events.t_code`). The 2,400 CAF branches and the BDT input features are not copied (training-only features are excluded).

Metadata sidecar `metadata.json` (copy in `tables/analysis_table/bnb_cv_metadata.json`): schema version 1.0, git commit (parent `a2bcaa3`; the build ran from the tree that became the Phase-2 commit, so the code is pinned by `code_sha256` of the build script and the library modules), manifest sha256, sha256 of `baseline_selection.yaml` and `samples.yaml`, sha256 of all 48 files in the BDT weight directory, input files 37,742, events 500,000, candidates 241,845, ΣTotalPOT 2.71940e19, ΣTotalGenEvents 1,887,100, UTC timestamp.

## 2. Validation (`scripts/validate_analysis_table.py bnb_cv --elementwise`): **72 exact checks, 0 failed**

Counts below are recomputed from the Parquet table alone and compared with the earlier full-scan tables (`tables/baseline/bnb_cv_cutflow.csv`, `bnb_cv_final_composition.csv`) and with the numbers you specified. Every comparison is exact integer equality.

| quantity | table | expected | match |
|---|---|---|---|
| events | 500,000 | 500,000 | yes |
| `wc.valid == 1` | 499,899 | 499,899 | yes |
| files | 37,742 | 37,742 | yes |
| candidates | 241,845 | 241,845 | yes |
| events with ≥ 1 candidate | 237,460 | 237,460 | yes |
| final events, policy `any` | 649 | 649 | yes |
| final events, policy `first` | 626 | 626 | yes |
| reco 0p / 1p / ≥2p, `any` | 318 / 236 / 95 | 318 / 236 / 95 | yes |
| reco 0p / 1p / ≥2p, `first` | 307 / 226 / 93 | 307 / 226 / 93 | yes |
| every cutflow stage, candidates / events `any` / events `first` (7 stages) | identical | | yes |
| final truth composition, both policies, every category with its 0p/1p/≥2p split (20 rows) | identical | | yes |
| ΣTotalPOT, ΣTotalGenEvents | 2.719402147414874e19, 1,887,100 | same | yes |
| candidate key and event key uniqueness | 0 duplicates | 0 | yes |

Element-wise comparison with the raw per-file scan (all 241,845 candidates and 500,000 events): the `(file, run, subrun, evt, nu_index)` rows align in order; the four BDT scores, the reco vertex, flash time and PE, `n_20mev`, `n_20br1`, `shw_sp_filled`, `c_np35` are identical (NaN-aware); the event `wc.valid` flag, event truth code and `bdt_evaluable` are identical. Final `any` truth composition: NC_PI0 178, NUE_CC 165, DIRT_NO_ACTIVE 104, CC_PI0 101, MULTI_ACTIVE 41, OTHER_NC 33, NUMU_CC 27.

One apparent failure in the first run of the validator was a bug in the *check*, not the data: the reference row `wc_valid` counts events with `wc.valid == 1` (499,899) while the table's stage `candidate_in_valid_event` counts events with at least one candidate (237,460, the reference row `candidate_exists`). The mapping was corrected; no table value or reference was changed.

## 3. Facts recorded while building (not tuning)

* **BDT evaluability** of the 241,845 candidates: 50,969 evaluable; 190,832 `shw_sp_filled == 0`; 44 with a non-finite input (matches `BDT_EVALUABILITY_AUDIT.md`).
* **Candidate-level dominant-truth matching** (MC, `wc.T_overlap` ↔ `T_truth_track`) is available for 241,830 of 241,845 candidates. It could not be computed for **two files, 8398 and 30698** (ROOT `DeserializationError` in the Wire-Cell truth trees; 15 candidates; `dom_ok = False`, columns NaN); all other columns of those files are present. 4,566 other candidates have no overlap rows (no dominant match). Of the 649 final events 97.7 % have a neutrino-dominated candidate (`dom_nu ≥ 0`); the median fraction of candidate charge in the dominant neutrino is 0.94.
* Truth is evaluation-only: nothing in the table's selection flags depends on it.
* `c_shw_sp_shw_vtx_dis` ("conversion distance" candidate), the dQ/dx columns and the flash variables carry sentinels (`lowest_dQ_dx` = 100, `vec_dQ_dx_0` = 6.25e9, `shw_vtx_dis` 0/−1); their units and meaning are not confirmed, so the plot suite only masks the sentinels for display.

## 4. Reproduce

```bash
source env/setup_eaf.sh
python scripts/build_analysis_table.py bnb_cv --workers 28       # ~47 min, resumable
python scripts/build_analysis_table.py bnb_cv --merge            # refuses if pieces are missing
python scripts/validate_analysis_table.py bnb_cv --elementwise --out tables/analysis_table/bnb_cv_validation.json
python scripts/analysis_table_report.py bnb_cv                   # plots + 1g0p/1g1p tables from the table only
```
