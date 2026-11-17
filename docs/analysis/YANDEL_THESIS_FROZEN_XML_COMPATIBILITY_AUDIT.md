# Yandel thesis vs the frozen single-photon XMLs: compatibility audit

Date: 2026-11-17. Branch `analysis/sp-bdt-thesis-xml-compatibility-20261117` (from `daf95442515b601eecda41c6c586931a5ae38c54`).
**Source/provenance audit only.** Nothing was trained; no XML, threshold, sample or Round-1 result was touched. Script: `scripts/sp_bdt_xml_audit.py`; outputs: `tables/sp_bdt_xml_audit/` (`summary.json`, `{numu,other,ncpi0,nue}_variable_splits.csv`, `upstream_score_and_flag_usage.csv`).

Tags: **SOURCE** (read in the XML or repository), **THESIS-AS-REPORTED** (the Aurora audit's numbers, taken as given; the thesis PDF itself was not readable on EAF, see section 9), **INFERENCE**, **NOT CHECKABLE**.

## 1. The exact frozen XMLs

Directory (read-only, the one the EAF scorer loads, `src/sbnd_single_photon/bdt.py:22`): `/exp/uboone/app/users/uboonepro/bbogart/wcp-uboone-bdt/weights/`. Recorded hashes: `provenance/software_versions.yaml` (`microboone_reference`), `provenance/microboone_reference_SHA256SUMS.txt`, `baseline_v0/docs/MICROBOONE_SINGLE_PHOTON_REFERENCE_PROVENANCE.md`. Recomputed on 2026-11-17: **all four match**.

| file | size (B) | sha256 (recorded = recomputed) | match |
|---|---:|---|---|
| `single_photon_numu_bdt_final.xml` | 2,216,404 | `5886affbdb3a4499a4515ecc8d354eb1449e7c204d32f1cc54c1ec8868ead961` | yes |
| `single_photon_other_bdt_final.xml` | 1,673,588 | `8c0ac375e957f5b332bc35339e4ebcbfef35bb778fb73315b06a814e600dbb16` | yes |
| `single_photon_ncpi0_bdt_final.xml` | 4,925,594 | `983a0d829aafdb4cb10afa273287cacab1cc27223bd46d3df5a2ebac1b3217c3` | yes |
| `single_photon_nue_bdt_final.xml` | 2,250,668 | `8580ba04b4a9e3c7aefbb4d5da5006cff2a131804a7b594843461a7cd6f3758a` | yes |

MicroBooNE source tree: remote `brb-rightback/wcp-uboone-bdt-eyandel`, head `0100d4b62193ef3ccdb7d759ce53eb9c1b4bb541` (the XMLs are not tracked in git; see `NUMU_TRAINING_DOMAIN_SOURCE_AUDIT.md`).

## 2. Tree counts (`<BinaryTree>` elements; equals the `NTrees` attribute)

| model | actual trees | thesis trees | match? |
|---|---:|---:|---|
| SP numu | **300** | 300 (older internal note) | yes (thesis value for numu not yet obtained, see section 8) |
| SP other | **215** | 215 | **yes** |
| SP ncpi0 | **400** | 400 | **yes** |
| SP nue | **300** | 300 (older internal note) | yes (same caveat) |

The older internal note "300 trees in all four" is **wrong for two models**: `other` has 215 and `ncpi0` has 400. It is right for `numu` and `nue`. All trees carry `boostWeight = 1.0`.

## 3. Tree depth

**Convention.** The XML `Node@depth` is 0 at the root. "Depth" below = number of split levels on the longest root-to-leaf path = (largest `depth` of a split node) + 1, which is XGBoost's `max_depth` (a stump has depth 1). Leaves sit one level below the deepest split. The convention was checked on a stump-level count: the deepest splits of `ncpi0` have `Node@depth = 5` and the leaves `6`.

| model | max depth (split levels) | depth distribution over trees | thesis | match |
|---|---:|---|---:|---|
| SP numu | 5 | 300 / 300 trees at 5 | n/a | consistent with earlier audit |
| SP other | **5** | 215 / 215 at 5 | 5 | **yes** |
| SP ncpi0 | **6** | 400 / 400 at 6 | 6 | **yes** |
| SP nue | 5 | 300 / 300 at 5 | n/a | |

Every tree reaches the maximum depth (no tree is shallower), as expected for trees grown to `max_depth` on large samples. Leaf counts: numu 8,403; other 6,251; ncpi0 18,622; nue 8,536.

## 4. Input lists

SOURCE: XML `Variables`. Counts agree with `EXPECTED_NVARS` in `bdt.py` and with the reference provenance table: numu 73, **other 146, ncpi0 45**, nue 56. For all four: no duplicate names, `Expression == Label == Internal == Title` for every variable (**no aliases**), all `Type = D`, **no `_calc` names**, no `Transformations`, no `Classes` element. The EAF scorer's variable list is read from the XML (`TmvaBdt.var_names`) and equals it exactly, in order, for all four (checked in this audit), so the production-model ordering is the XML ordering by construction. Full ordered lists with indices: `tables/sp_bdt_xml_audit/<model>_variable_splits.csv`.

`ncpi0` (45), in XML order: indices 0-17 are `shw_sp_*` (pio_1 mass/type/energies/distances, `pio_mip_id`, `pio_flag_pio`, n_20br1 / br1 / br2 / br3 / br4 shower counts, `E_indirect_max_energy`, `lol_3_vtx_n_segs`, `hol_*`); 18-32 are the 15 tagger scores `tro_5/4/2/1, stw_4/3/2, sig_2/1, pio_2, lol_2/1, br3_6/5/3 _score`; **33-44 are the twelve `kine_pio_*`**: `mass`(33), **`flag`(34)**, `vtx_dis`(35), `energy_1`(36), `theta_1`(37), `phi_1`(38), `dis_1`(39), `energy_2`(40), `theta_2`(41), `phi_2`(42), `dis_2`(43), `angle`(44).

`other` (146): includes the upstream scores `numu_1_score`(142), `numu_2_score`, `numu_score`(144), `cosmict_10_score`, and `reco_nuvtxY`(145); **`kine_pio_flag` is not an input of `other`** (nor of numu / nue).

**Comparison with the thesis Appendix E lists: NOT CHECKABLE on EAF.** The Aurora-recovered Appendix E text is not in this repository and the thesis PDF was not retrievable from the EAF shell (no network; the 10 MB PDF exceeds the fetch limit). What is established: the XML counts equal the thesis counts (45 and 146), and the XML ordered lists are in the CSVs for a direct name-by-name diff on Aurora. **Required Aurora step:** diff Appendix E against `ncpi0_variable_splits.csv` / `other_variable_splits.csv` (columns `var_index`, `name`); any missing / extra / renamed variable is a gate failure.

## 5. Split counts and `kine_pio_flag`

Splits per variable (a split = a non-leaf node). For XGBoost, F-score with `importance_type = "weight"` **is** the split count, so **if Appendix E reports F-scores of that type, they must equal these counts exactly for the same model** (the converter keeps every node). If Appendix E reports `gain` / `cover` / `total_gain`, they are not comparable to counts (not encoded in the XML).

| model | total splits | variables used / listed |
|---|---:|---|
| numu | 8,103 | 73 / 73 |
| other | 6,036 | 133 / 146 (13 `cosmict_*` flags never split) |
| ncpi0 | 18,222 | 45 / 45 |
| nue | 8,236 | 56 / 56 |

**`ncpi0` and `kine_pio_flag`.** `kine_pio_flag` (index 34) **is used**: **23 splits in 20 of 400 trees (0.13 % of splits), rank 44 of 45 by split count.** Cuts 0.5 (2x) and 1.5 (21x), i.e. the flag is not purely 0/1. Split depth distribution (node depth, root = 0): 1 at the root, 1 at 2, 3 at 3, 6 at 4, 12 at 5. Only `shw_sp_pio_flag_pio` (5 splits) is used less.
Comparison with the thesis: the thesis reportedly gives `kine_pio_flag` a **non-zero F-score**: **consistent** (23 > 0). It reportedly places the flag at about 10th of 45 **by gain**: **not checkable** from the XML (gain is not encoded), and **not inconsistent** with rank 44 by count, because count and gain are different metrics; a binary flag split rarely but near a root (one split is at the root, one at depth 2 of their trees) can carry a large per-split gain. This is a plausibility statement, not a confirmation.

Top of the `ncpi0` split-count ranking: `shw_sp_E_indirect_max_energy` 750, `kine_pio_phi_2` 708, `kine_pio_phi_1` 700, `kine_pio_angle` 698, `tro_1_score` 685, `kine_pio_mass` 660, `kine_pio_theta_1` 647, `kine_pio_energy_1` 645, `kine_pio_theta_2` 644, `kine_pio_dis_2` 642. The ten `kine_pio_*` kinematic inputs other than `flag` and `vtx_dis` all lie in the top 25; the pattern (pi0 kinematics plus the inherited taggers) is what a pi0-versus-single-photon discriminator is expected to look like. The 15 tagger `_score` inputs hold **40.6 %** of all `ncpi0` splits (see section 8 for why that matters).

`other` top: `numu_score` 281 (4.7 %), `shw_sp_E_indirect_max_energy` 224, `reco_nuvtxY` 221, `numu_1_score` 194, `shw_sp_lem_e_charge` 174. Cosmic-tagger inputs are spread thin and 13 are never used; the dominance of the upstream numu scores plus vertex position and shower-energy terms is **qualitatively compatible** with a classifier whose negatives include NC no-pi0, dirt, out-of-FV, cosmic overlay and off-beam; it is not a confirmation of that composition.

## 6. XML training metadata

The XML is a **`xgboost2TMVA` conversion**. It encodes: `Creator = xgboost2TMVA`, `AnalysisType = Classification`, `BoostType = Grad` (TMVA label), `NodePurityLimit = 0.5` (TMVA field with no XGBoost meaning), `NTrees`, all `boostWeight = 1`, per-node `IVar`, `Cut`, `res` (leaf value), `depth`. It does **not** encode learning rate, objective, subsample, colsample, gamma, seed, sample, class names, event counts or importance tables (confirmed in `NUMU_TRAINING_DOMAIN_SOURCE_AUDIT.md` for numu and re-checked for all four here).

| thesis parameter | `ncpi0` | `other` | classification |
|---|---|---|---|
| number of trees (400 / 215) | 400 | 215 | **XML CONFIRMS** |
| max depth (6 / 5) | 6 | 5 | **XML CONFIRMS** |
| number of inputs (45 / 146) | 45 | 146 | **XML CONFIRMS** |
| gradient boosting | `BoostType = Grad` | same | **XML COMPATIBLE BUT NOT ENCODED** (label set by the converter) |
| `kine_pio_flag` an input of ncpi0 only | present, 23 splits | absent | **XML CONFIRMS** (usage non-zero) |
| legacy cut (-0.05 / 0.2) | not in XML; `cuts.h:8899-8906` via `legacy_scorer.FROZEN_THRESHOLDS` | same | **CONFIRMED BY SOURCE, not XML** |
| learning rate 0.1 | tree-0 leaf range [-0.197, +0.140]; the first-tree bound `|leaf| <= 2 eta = 0.2` (base score 0.5, any weights) holds | tree-0 leaf range [-0.248, +0.085] exceeds 0.2 | **NOT CHECKABLE** (see note) |
| objective `binary:logitraw` | the `score = log10((1+v)/(1-v))` convention is `(2/ln 10) x` the summed leaf value if `v = tanh(sum)`: margin-like, compatible | same | **XML COMPATIBLE BUT NOT ENCODED** (inference from the scorer, not read in the XML) |
| colsample 1 / 0.5 / 0.5 | all 45 inputs used | 133 of 146 used | **NOT CHECKABLE** (usage is not diagnostic) |
| subsample 0.8, gamma 0.2, seed 1 | - | - | **NOT CHECKABLE** |
| training counts 24,936 / 37,205 and 24,936 / 27,377 | - | - | **NOT CHECKABLE** (no event counts in the file) |
| positive / negative classes | - | - | **NOT CHECKABLE** (no `Classes` element) |
| training-sample composition | - | - | **NOT CHECKABLE** |

Note on learning rate. The `other` first-tree leaf of -0.248 is above the 0.2 bound that holds for a unit-learning-rate-0.1 first tree with `base_score = 0.5`. This **does not contradict** the thesis value: the bound changes if `base_score` is not 0.5 (a weighted class prior is a typical XGBoost 2.x default), and the converter may fold a base offset into the first tree. The XML cannot distinguish these. It is recorded so Aurora can check `eta` and `base_score` against Erin Yandel's actual configuration or the thesis text instead of assuming.

Inference record: the `other` tree-0 negative skew (mean leaf -0.12, extremes -0.248 / +0.085) differs from `ncpi0` tree 0 (mean -0.03, [-0.197, +0.140]); consistent with different class balance or weighting in the two trainings, not proven.

## 7. Gate decisions

### `ncpi0`: THESIS/XML PLAUSIBLY SAME MODEL — MINOR UNCHECKABLE DETAILS

Evidence: **400 trees (match), depth 6 (match), 45 inputs including `kine_pio_flag` (match), `kine_pio_flag` used with non-zero split count (consistent with non-zero F-score), legacy cut -0.05 confirmed in source.** Not checkable: learning rate, objective, sampling, gamma, seed, training counts, classes, Appendix E ordering / importance. No evidence of a version mismatch. The structural identifiers that a different model version would change (tree count, depth, input count and set) all agree. The status becomes MATCH after Aurora's exact diff of Appendix E F-scores (if `weight`-type) against `ncpi0_variable_splits.csv`.

### `other`: THESIS/XML PLAUSIBLY SAME MODEL — MINOR UNCHECKABLE DETAILS

Evidence: **215 trees (match), depth 5 (match), 146 inputs (match), legacy cut 0.2 confirmed in source.** The thesis' 215-tree figure, which is unusual for a round-number setup, is exactly what the frozen XML holds; this is the strongest single identifier in the audit. Not checkable: same list as above, plus the training composition (the thesis negatives include EXT off-beam data and overlay cosmics; the XML cannot show the sample). One observation is kept open: the tree-0 leaf magnitude (section 6 note).

Neither model is BLOCKED. **The retraining target definitions from the thesis can be adopted for ncpi0 and other**, with the two required Aurora diffs above as final confirmation.

Two retraining-design points that surface here (decisions for the Aurora session, not made here):
1. **`kine_pio_flag`.** The thesis model was trained with a non-zero flag importance, i.e. the flag was real in training, while the production path (commit `47b1f0c`) forces it to 0 at evaluation. The XML therefore contains 23 splits that production never exercises with the real value. The SBND retrain must decide explicitly whether to include the flag, and Round-2 baseline comparisons must use the source-faithful convention (flag 0) for `R1-source-faithful`.
2. **Upstream tagger scores.** `ncpi0` takes 15 inherited tagger scores (40.6 % of its splits); `other` takes four (`numu_score`, `numu_1_score`, `numu_2_score`, `cosmict_10_score`). Their definition and any change in the SBND chain belong in the freeze list of Round 2.

## 8. SP numu and the upstream `numu_score` domain shift

**Frozen XML (SOURCE).** `numu` has 73 inputs, 300 trees, depth 5, 8,403 leaves. Two inputs are upstream scores produced by the `UbooneNumuBDTScorer` chain: `numu_score` (index 72) and `numu_1_score` (71).

| model | `numu_score` splits (rank) | `numu_1_score` splits (rank) | pair share of all splits | trees using `numu_score` / `numu_1_score` |
|---|---|---|---:|---|
| SP numu | 623 (**1st**, 7.7 %) | 311 (3rd, 3.8 %) | **11.5 %** | 193 / 300 and 149 / 300 |
| SP other | 281 (**1st**, 4.7 %) | 194 (4th, 3.2 %) | **7.9 %** | 121 / 215 and 94 / 215 |
| SP ncpi0 | not an input | not an input | 0 | - |
| SP nue | not an input | not an input | 0 | - |

Placement: in SP numu, `numu_score` is the split variable at the **root of 41 trees** and at depth 1 of 62; `numu_1_score` at the root of 23 and depth 1 of 23. In SP other, `numu_score` is at the root of 15 trees and depth 1 of 34. These are heavy uses, not rare ones; they agree with the earlier attribution result that `numu_score` is the single largest input of the numu stage (`NUMU_TRAINING_DOMAIN_SOURCE_AUDIT.md`, TreeSHAP).

**Consequence.** Round 2 will change the upstream numu chain (Xuyang). Both inherited models that consume it, **SP numu and SP other**, would then be evaluated on an input distribution that was never seen in their MicroBooNE training. The size of the effect cannot be measured without a new `numu_score` distribution; there is also no MicroBooNE training distribution of any input to compare with (stated in the earlier audit).

**Thesis information for SP numu: NOT OBTAINED.** The thesis text was not accessible from EAF, and the public collaboration paper (arXiv:2502.06064) states only that four XGBoost BDTs target numu-CC, NC pi0, "other" (cosmics, out-of-TPC neutrinos) and nue-CC backgrounds, that the nue BDT separates electron-shower CC from single-photon signal, and defers the rest to the thesis; it gives no class definitions, counts, input numbers, trees or depth for the numu BDT. Still needed from the Aurora recovery (Appendix E / the BDT chapter): the SP-numu positive and negative classes, the training event counts, the sample composition, the hyperparameters (is it 300 trees, depth 5, 73 inputs as in the XML?), and **how the input `numu_score` / `numu_1_score` were produced for the training events** (the same upstream chain as production?). Do not guess these.

Round-2 decision table:

| option | scientific cleanliness | work | recommendation |
|---|---|---|---|
| keep inherited SP-numu with the new upstream numu | **lowest.** The model's two heaviest inputs change distribution with no retraining and no way to quantify the shift; and SP other, which shares the same two inputs, could not then be retrained consistently (its training would see the new `numu_score` while SP numu would not) | smallest | **not for the final selection.** Acceptable only as a clearly labelled diagnostic |
| retrain SP-numu on the refreshed Aurora sample | **highest**, if SP numu and SP other are both trained on the frozen new upstream chain, so every SP input comes from the same frozen chain. It needs the thesis SP-numu target definition | largest: recover the target, refresh the training sample with the new chain, train, freeze; the same refresh is already required for `ncpi0` and `other` | **recommended for the final Round-2 model**, conditional on recovering the SP-numu target definition (section 8, needed information). Decide it together with the SP-other retrain, not separately |
| preserve the legacy upstream numu only for SP-numu | **intermediate.** It keeps SP-numu in-domain with respect to its training inputs, but it runs the old MicroBooNE-trained chain on SBND objects (an out-of-domain evaluation already present in R1), keeps two upstream numu chains alive, and leaves SP other (same inputs) in the same question | moderate: a dual-chain production and bookkeeping | **diagnostic control only**: it would also give the Round-2 report a way to separate the effect of the new upstream chain from the effect of retraining. Not recommended as the final configuration |

Not decided here. The recommendation is conditional on the missing SP-numu thesis information; if that cannot be recovered, SP numu retraining has no source-defined target and the decision must come back to the analysis group. All three options leave the Round-1 source-faithful baseline unchanged.

## 9. What was not done / limits

- The Yandel thesis PDF itself (public: `https://escholarship.org/uc/item/6rq082dr`) could not be read on EAF (shell has no network; the PDF is above the 10 MB fetch limit). All thesis numbers in this document are the Aurora audit's, as supplied.
- Appendix E feature lists and F-score tables were not available; section 4 and 5 give the XML side for an exact diff on Aurora.
- No MicroBooNE stored scores exist on EAF; this audit makes no claim that the EAF scorer reproduces them (unchanged from the scorer-correction audit).
- No training, XML edit, threshold change or sample change occurred; the Round-1 baseline (833 / 12,427 = 6.70 %) is untouched.
