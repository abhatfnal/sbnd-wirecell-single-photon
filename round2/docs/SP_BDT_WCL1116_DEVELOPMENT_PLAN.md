# SP BDT development on the WCL1116 vertex refresh: plan

Date: 2026-11-17. Campaign **`development_wcl1116_v1`**. Branch `round2/sp-bdt-wcl1116-development-20261117`, from
`6247137`.

This is active model **development** in the current SBND development domain, the counterpart of Xuyang and Matteo's
νμ / νe development. It is **not** final Round-2 training. Every model is `…_DEV_DO_NOT_DEPLOY`, and no threshold is
chosen. Statistical policy: `AURORA_UMBRELLA_MODEL_TRAINING_AND_EVALUATION_POLICY.md`. The odd-subrun half is a
**DEVELOPMENT HOLDOUT**.

## 1. Ownership and scope

| model | owner | this campaign |
|---|---|---|
| SP numu | Avinay | develop on both vertex modes; `UPSTREAM_NUMU = SHIPPED_CONTROL` |
| SP ncpi0 | Avinay | develop on both vertex modes; Policy B (`kine_pio_flag` as stored); legacy control with flag 0 |
| SP other | Avinay | develop **only if** the refreshed odd-run beam-off half is readable on Aurora; otherwise prepare everything and mark `SP-OTHER DEVELOPMENT BLOCKED ONLY ON DATA ACCESS/STAGING` |
| SP nue | Avinay | **no training**: domain-shift study only (aurora-r2 vs split-move vs snap) and a recommendation |
| νμ / νe taggers (`numu_score`, `nue_score`) | Xuyang + Matteo | not touched here. Retraining them does **not** replace SP numu / SP nue |

## 2. Inputs (Aurora training side only)

Production WCLocal2026Nov16-Aurora:
- WCT 0.38.0 `c935e30d`, wire-cell-data `99c6497f`, larwirecell `ad5d9421` (step 1 of aurora-r1, reused), sbndcode
  v10_14_02_03;
- DV2-MAX `aurora_space` bundle `51588842…`.

| sample | id | list rule | manifest |
|---|---|---|---|
| NC Δ radiative configL | `wcl1116-aurora-ncdr` | units with status OK, both validations PASS and both trees merged | `manifests/wcl1116_dev_v1/manifest_wcl1116-aurora-ncdr.tsv.gz` |
| BNB CV | `wcl1116-aurora-bnb` | the same rule. The 14 PARTIAL units are **excluded and recorded**, with their events | `…/manifest_wcl1116-aurora-bnb.tsv.gz` |
| beam-off training half | `wcl1116-fg-beamoff-train` | the frozen `fg1-beamoff-train` membership (572 pairs → 558 after the 14 hold-out files), all runs odd | `…/beamoff_train_membership.{json,tsv.gz}`. Location: FermiGrid dCache only |
| νe CC | `wcl1116-aurora-nuecc` | not used now: production still completing. Needed only for the SP nue negative class | — |

- Lists and manifests are written by `tools/make_refresh_list.py`, read-only on Haiwang's area, in a PBS job on
  compute nodes.
- Every row records the sample, production, unit, role, status, both validations, the trees present, CAF / Wire-Cell
  events per tree, size, mtime and path.
- No official evaluation path can enter: the firewall runs on every file and test.

## 3. Two parallel table sets from the same files

| domain | tree | tables |
|---|---|---|
| `wcl1116_dv2_split_move_dev` | `recTreeWireCell` (`vertex_method = dv2_split_move`, the 0.38.0 default) | `$SP_WORK/wcl1116_dev_tables/dv2_split_move/` |
| `wcl1116_dv2_snap_dev` | `recTreeWireCell_dv2snap` (`dv2_snap`) | `$SP_WORK/wcl1116_dev_tables/dv2_snap/` |

- Built by `sp_retrain.build_tables --wc-tree`. The tree is recorded in every files row and in the build summary, and
  the trainer refuses a mismatch.
- Both sets use the same list, split, labels, feature lists and hyperparameters. The specs are generated
  (`tools/make_wcl1116_dev_specs.py`) and differ only in the reconstruction block and the model name.
- **Mode is not chosen here.** Xuyang compares the upstream BDTs, and Matteo checks downstream compatibility, under both
  modes. We do the same for the SP classifiers.

## 4. Split

- MC: even subrun = train, odd subrun = development holdout (`subrun_parity_v1`).
- Beam-off: run % 4 == 1 = holdout, as established for the training half.
- The split depends only on event identity, so a matched event sits on the same side in both modes. Checks: zero
  train/holdout event overlap, zero duplicate rows, zero multi-file events.

## 5. Studies, in order

1. **Reconstruction migration before any fit** (`tools/wcl1116_migration_study.py`). Split-move vs snap, and each vs
   aurora-r2, on matched files, events and candidates:
   - events, candidates, `shw_sp_filled`, preselection, multiplicity, class populations per SP model, one-mode-only
     candidates, vertex displacement, shower-count and main-shower-energy changes, non-finite inputs;
   - the truth-signal candidate-formation ceiling, kept separate from any classifier metric.
2. **Old → refreshed domain shift** per SP feature set (73 / 45 / 146 / 56):
   - standardized mean and median shifts, KS, Wasserstein;
   - per input family: vertex, shower start / dQ/dx, topology, track–shower, π⁰, νμ / cosmic tagging;
   - candidate availability; legacy-score migration.
3. **Legacy MicroBooNE controls in both modes:** exact XMLs, log10-odds once, ncpi0 with flag 0, no threshold tuning.
4. **Fixed-spec development models** (thesis Appendix E settings, `base_score` 0, seed 1, no weights, no tuning):
   - SP numu (5 / 300) and SP ncpi0 (6 / 400) for each mode;
   - SP other (5 / 215) only if the beam-off half is available.
5. **Snap vs split-move as a BDT input domain:**
   - ceilings and class populations first;
   - then legacy and new-model AUC on the development holdout;
   - then a **matched common population** (candidates present and classed identically in both modes) for a fair
     classifier-only comparison.
6. **Legacy vs new ROC diagnostics** on common held-out rows. Points: the legacy historical cut; the new model at the
   same signal efficiency; the new model at the same background acceptance. Label: "DEVELOPMENT ROC-EQUIVALENT
   DIAGNOSTIC — NOT ROUND2 CUT".
7. **Feature sanity** against the legacy fingerprints. Bookkeeping identifiers must never gain importance; they are not
   inputs.
8. **NC π⁰ negative statistics:** is the learning-curve conclusion still SOME BENEFIT LIKELY on WCL1116?
9. **Cosmic-tagger-boundary dependence** of every SP input, from the toolkit code.
10. **Export** of every development model; Python equivalence; C++ (`TMVA::Reader` + toolkit `TmvaGradForest`) if the SL7
    container can run on a compute node.

## 6. Not done here

- No final models, thresholds, joint optimisation or mode choice.
- No FermiGrid evaluation product, not even its performance numbers.
- No SP nue training.
- No enriched-sample request.
- No push and no messages.
