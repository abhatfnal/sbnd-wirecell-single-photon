# NCPI0 / OTHER retraining: do the Aurora merged CAFs carry everything needed?

Date: 2026-11-17. Training/development samples only: Haiwang's aurora-r2 merged CAFs of Avinay's gen2 MC. No official
fg1 / FermiGrid sample was read. Per-input detail: [tables/READINESS_PER_INPUT.md](tables/READINESS_PER_INPUT.md)
(generated). Measurements: `round2/sp_retrain/readiness.py`. Full statistics come from Xuyang's spec_v1 tables, read
only; the 13 `T_kine` inputs, which those tables do not carry, come from the own-builder smoke slices.

## 1. Answer

**Inputs.** Every one of the 191 inputs (ncpi0 45, other 146) is a branch of the aurora-r2 merged CAF.
- Schema `recTreeWireCell-dlvtx-space.schema.json`, md5 `af9c87c8…`, 2,416 branches.
- 190 are `Float_t`; `kine_pio_flag` is `Int_t`. All are per-candidate vectors (one value per `T_tagger` row).
- Xuyang's existing tables already hold 178 of them.
- Missing there: the 12 `kine_pio_*` (ncpi0) and `kine_nu_y_corr`, which stands in for `reco_nuvtxY` (other). All 13
  live in `T_kine`, which her builder reads only partly.
- The new builder `round2/sp_retrain/build_tables.py` carries all 191. In the smoke check it matched Xuyang's tables
  on every row (558/558) and every shared column (1,057), apart from one encoding difference for non-neutrino partners
  (§6).

**Truth.** The truth needed for an NC π⁰ label is in the files:
- `T_truth_nu`: CC/NC, pdg, GENIE mode, int_type, vertex, deposited energy.
- `T_truth_pf`: primary π⁰ (`parent_trackid == 0`), their decay photons (`parent_trackid == mother_trackid == π⁰
  trackid`), photon KE and conversion points, primary leptons.
- `T_match` (level-2 partner per candidate) and `T_dlvtx_call` (space-charge-shifted true vertex).
- A second, independent route: `recTree` StandardRecord truth (`rec.mc.nu.isnc`, `genie_mode`, `npizero`, `prim.pdg`,
  `prim.start*`).

**What the CAFs cannot provide.**
- MicroBooNE-specific truth summaries (`truth_single_photon`, `truth_showerMother`, `match_completeness_energy`). Since
  the thesis audit, `sp_retrain/sp_truth.py` rebuilds the single-photon categories from `T_truth_nu` / `T_truth_pf`
  under assumptions A1–A7 (`YANDEL_THESIS_SP_BDT_TRAINING_SOURCE_AUDIT.md` §8). The shower end point is not stored.
- A cosmic-only (in-time cosmic, EXT-like) sample, part of the "other" negative class (thesis p.129). The aurora-r2
  MC cannot provide it; the fg1 beam-off training half can (`ROUND2_COLLABORATOR_QUESTION_CLOSURE_AUDIT.md` §2).

## 2. Sample size and the single-photon gate (full aurora-r2, placeholders dropped)

| sample | candidates | `shw_sp_filled == 1` | of which ≥1 shower > 20 MeV | `br_filled == 1` |
|---|---:|---:|---:|---:|
| aurora-r2-ncdr (NC Δ-rad, configL) | 23,965 | 16,534 (69.0 %) | 16,534 | 8,071 |
| aurora-r2-bnb (BNB CV) | 296,263 | 63,581 (21.5 %) | 63,581 | 19,943 |
| aurora-r2-nuecc (CC νe, configL) | 264,844 | 217,481 (82.1 %) | 217,481 | 183,762 |

- `shw_sp_filled == 1` is the condition for the single-photon block to hold computed values; baseline_v0 used it as its
  "evaluable" criterion.
- In every sample, each filled candidate also has `shw_sp_n_20mev_showers > 0`.
- `br_filled` gates the νe score, not the single-photon block; it is not needed here.

## 3. Fill and default semantics (measured)

| input family | when `shw_sp_filled == 0` | on filled rows |
|---|---|---|
| `shw_sp_*` (ncpi0: 18; other: ~80) | 0 on essentially every row | many legitimately stay 0. Example: `shw_sp_pio_1_*` is 0 on 85 % of filled NC Δ rows, where no π⁰ pair was reconstructed |
| 15 νe level-1 scores (ncpi0 18–32) | the toolkit's empty-list default on 99 % of rows (`tro_5` 0.5, `br3_3` 0.3, …) | still at the default on 52–86 % of filled NC Δ rows |
| `kine_pio_*` (ncpi0 33–44, smoke) | 0 when no π⁰ pair was formed; `kine_pio_flag` ∈ {0, 1, 2}, modal 1 | MicroBooNE's scorer forces `kine_pio_flag = 0` (see the audit) |
| `cosmict_*`, `cosmic_*`, `numu_cc_flag` (other) | flags and values at defaults | several are constant in SBND (e.g. `cosmict_flag_5`, `_6`, `_8` ≈ 100 % 0): little information |
| νμ scores (other 141–144) | `numu_1_score` −0.4, `numu_2_score` −0.1, `cosmict_10_score` 0.7 when the list is empty; `numu_score` continuous | n/a |
| `reco_nuvtxY` → `kine_nu_y_corr` (smoke) | continuous vertex coordinate | SBND y frame, not the MicroBooNE one |

**Non-finite values.** On filled rows only one input is ever non-finite: `shw_sp_pio_1_mass`.

| sample | filled rows with NaN `shw_sp_pio_1_mass` |
|---|---:|
| ncdr | 3 of 16,534 |
| bnb | 4 of 63,581 |
| nuecc | 19 of 217,481 |

All 145 "other" inputs in the tables are finite on every filled row. Missing-value policy for training and scoring:
these rows are not scored. TMVA's −999 and XGBoost's "missing" branch disagree, so an equivalence test must not depend
on them.

## 4. Reconstruction-derived versus upstream-classifier inputs

- **ncpi0:**
  - 30 reco inputs: 18 `shw_sp_*` and 12 `kine_pio_*`.
  - 15 upstream inputs: the νe level-1 TMVA scores computed by `UbooneNueBDTScorer` from the shipped
    `uboone/weights/*_BDT.weights.xml`.
- **other:**
  - 142 reco inputs.
  - 4 upstream inputs: `numu_1_score`, `numu_2_score` and `cosmict_10_score` (νμ level-1) and `numu_score` (νμ final),
    all from `UbooneNumuBDTScorer`.

The producer of each input is recorded in `round2/config/features/single_photon_*_inputs_v0.json`.

## 5. Truth fields for labels

| need | field(s) in the merged CAF | verified |
|---|---|---|
| interaction identity | `wc.T_truth_nu.{pdg, ccnc, mode, int_type, E, edep, vtx_x/y/z}`; `rec.mc.nu.{iscc, isnc, pdg, genie_mode, genie_inttype}` | branch lists read from one file per sample |
| primary π⁰ | `wc.T_truth_pf` rows with `pdg == 111`, `parent_trackid == 0`, `process == 0`, linked to the neutrino by `nu_row`; secondary π⁰ have `process == 20` | inspected on one BNB file: the 5 π⁰ printed (3 primary, 2 secondary) each had two photon children |
| π⁰ daughters and photons | `pdg == 22` with `parent_trackid == mother_trackid == π⁰ trackid`; `KE` in GeV; `end_x/y/z` = conversion point; `start_px/py/pz` | builder columns `n_gamma_from_prim_pi0`, `n_gamma_ke20_conv_in3cm`, `pi0_gamma_min_open_deg` |
| photon multiplicity | `n_prim_gamma`, `n_gamma_ke20`, `n_gamma_ke20_conv_in3cm` (KE > 20 MeV, conversion ≥ 3 cm inside the active volume) | smoke census: NC Δ slice has 90 NC interactions with a primary photon and no π⁰; BNB slice has 147 with one primary π⁰ and 15 with two |
| candidate truth matching | `wc.T_match` level 2: candidate → best partner by point IoU; truth → best candidate (`nu_ct_*`) | builder reproduces spec_v1 partners on 558/558 smoke rows |
| shower start/end containment (MicroBooNE signal clause) | conversion point: yes; "last visible charge": not in `T_truth_pf` (needs daughter energy deposits; `T_truth_track` / `T_overlap` may help, not checked) | open |
| cosmic / dirt (for "other", if its definition is recovered) | cosmic partner: `T_match` partner with `truth_nu_idx < 0` (cosmic) or no partner; dirt / out-of-TPC: partner neutrino vertex outside the active volume (`T_truth_nu.vtx` vs x ±201.3, y ±203.73, z 0–501); match IoU per candidate | columns exist; no cosmic-only sample on the Aurora side |

## 6. Builder validation

**Comparison with Xuyang's tables** (`round2/validation/smoke_tables_validation_vs_spec_v1.json`).
- Own-builder smoke slices (ncdr 60 files, bnb 15, nuecc 20) against Xuyang's tables for the same files: 86 + 382 + 90
  candidates matched on `(file_id, run, subrun, event, cand)`, with none on only one side.
- 1,057 shared columns are identical value by value, except `m_pdg` / `m_ccnc` on exactly the non-neutrino partner rows.
  Here the builder writes NaN where spec_v1 writes 0 / −1 (4 + 25 + 2 rows = the cosmic + none partners).
- The split is event- and subrun-safe on all three slices.

**Scorer arithmetic.** `sp_retrain.tmva_grad` re-scored the shipped νe final XML from merged-CAF branches and
reproduced the toolkit's stored `nue_score` bit for bit on 423 of 423 candidates, 174 of them real scores
(`round2/validation/nue_xml_vs_stored_*.json`). The production-side scorer that the single-photon models need is
therefore verified on real data.

## 7. Firewall and hold-out checks

- **Development samples:** only `aurora-r2-ncdr`, `aurora-r2-bnb` and `aurora-r2-nuecc`.
- **Manifests** (`round2/manifests/aurora_r2_v0/`):

  | list | files | size | list sha256 |
  |---|---:|---:|---|
  | ncdr | 17,603 | 59.7 GB | `8895a65e…` |
  | bnb | 11,888 | 421.0 GB | `dfbb5240…` |
  | nuecc | 61,248 | 374.9 GB | `4d53f0b3…` |

  0 missing, 0 duplicate file ids.
- **Xin's hold-out lists:** 54 runs, 31–18587. They do not overlap any aurora-r2 run (ncdr 7,000,005–7,030,038; bnb
  2,100,001–5,000,813; nuecc 6,700,001–6,734,897).
- **Firewall:** `sp_retrain.firewall` refuses any path or sample id carrying an official marker (`/pnfs/`,
  `prod-fermigrid`, `fg1`, `beam-off`, `run3bnb`, `open-run1`, `strmOffBeam`, …) and any output inside `xning/` or `yuhw/`.
  The fg1 beam-off "train" half used by Xuyang is refused unless a spec names it as an approved exception.
- **Xuyang's 14-file discrepancy:** her spec says the 14 beam-off files holding Xin's hold-out events are dropped, but
  the implementation trains on them. That is resolved here by not using fg1 beam-off at all. If an exception is ever
  approved, `--holdout-file-ids` flags those files and the training step must refuse flagged files.
- **POT:** the recTree header POT is stored only as `hdr_pot_sum_not_exposure`. For the filtered samples it is 12×
  (νe CC) and 112× (NC Δ) below the production POT.
