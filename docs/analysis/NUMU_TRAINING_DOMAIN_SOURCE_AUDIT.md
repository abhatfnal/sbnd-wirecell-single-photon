# What is documented about the training domain of the frozen `numu` BDT? Source audit

Date: 2026-11-11. Branch `analysis/ncdelta-numu-training-domain-audit-20261111`. **Characterisation only**: no weight, threshold, selection, FV, policy, reconstruction or training was touched. Roadmap item **Z**, Task 1. Companion: `NUMU_COMPACT_SHOWER_TRAINING_DOMAIN_AUDIT.md` (the measurement). Earlier source audits this builds on: `FROZEN_NUMU_BDT_SOURCE_AUDIT.md`, `FROZEN_BDT_DEPENDENCY_GRAPH.md`.

Tags: **SOURCE** (read in a file), **MEASURED** (from the official SBND files), **INFERENCE** (reasoned from SOURCE, not stated anywhere), **NOT ESTABLISHED** (no document found). Nothing below fills in a missing training detail.

## 1. Pins

| item | pin | tag |
|---|---|---|
| model file | `single_photon_numu_bdt_final.xml`, sha256 `5886affbdb3a4499a4515ecc8d354eb1449e7c204d32f1cc54c1ec8868ead961` (identical to `provenance/microboone_reference_SHA256SUMS.txt` line 7 and to the file in the MicroBooNE tree) | MEASURED |
| MicroBooNE reference tree | `/exp/uboone/app/users/uboonepro/bbogart/wcp-uboone-bdt`; remote `https://github.com/brb-rightback/wcp-uboone-bdt-eyandel.git`; head `0100d4b62193ef3ccdb7d759ce53eb9c1b4bb541` (`provenance/reference_bundle/source_git_head.txt`, `source_git_remote.txt`) | SOURCE |
| first appearance of the single-photon BDT code | commit `bf9d7113c952054b592a7b57be8041812212a714`, 2022-09-21, author `eyandel` (`provenance/reference_bundle/weights_source.txt`, `single_photon_model_bookings.txt`). The four single-photon XMLs were **not tracked** in the Lee `wc_postprocessing` repository | SOURCE |
| SBND producer | `HaiwangYu/wire-cell-toolkit`, branch `sbnd-wc-flatcaf`, commit `4b6853d4` (producer-declared fg1 pin): `NeutrinoTaggerSinglePhoton.cxx`, `NeutrinoTaggerNuMu.cxx`, `UbooneNumuBDTScorer.cxx` | SOURCE |
| evaluation code | `inc/WCPLEEANA/bdt.h`, `cal_single_photon_numu_bdts_xgboost`: `reader.EvaluateMVA("MyBDT")`, returns `log10((1+val)/(1-val))` (comment `//Erin`) | SOURCE |
| SBND evaluation | `src/sbnd_single_photon/bdt.py` (`score = tanh(sum leaf)`), reproduced here to 2.6e-9 with 0 decision flips on all 8,038 stage events (`tables/numu_compact_shower_audit/summary.json`) | MEASURED |

## 2. What the model file says

* **SOURCE** (XML `GeneralInfo` and `Options`): `Creator = xgboost2TMVA`, `AnalysisType = Classification`, `BoostType = Grad`, `NodePurityLimit`, 300 trees, depth 5, 8,403 leaves, 73 inputs. The file carries **no date, no sample name, no class names or labels, no number of training events, no cross-validation or hyper-parameter record and no variable-importance table**. The file has **no `Classes` element at all** (checked in the XML text): not even a `Signal` / `Background` label, so which class the score favours is only fixed by the use in the code (a high score is rejected as background-like).
* **SOURCE**: the model is a converted XGBoost model; the XGBoost training script, learning rate, objective, sample weights and the train/test split are not in the file.

## 3. What the MicroBooNE tree documents

Searched: the whole tree (`README.md`, `apps/`, `inc/`, `src/`, `weights/`, `docs`-like files, git history of the single-photon files).

* **SOURCE**: `README.md` contains build and tutorial links only. There is **no training script, configuration, ntuple list or log for any of the four single-photon BDTs** (`numu`, `other`, `ncpi0`, `nue`). `apps/gen_training_list.cxx` is a generic list writer and does not mention the single-photon BDTs.
* **SOURCE**: the evaluation code and the tagger structure (`tagger.h`: `single_photon_*_score` default -20) show how the score is *used*, not how it was trained.
* **SOURCE**: truth branches that relate to the single-photon topology exist in `pfeval.h` (`truth_single_photon`, `truth_NCDelta`, `truth_photon_angle`, `truth_photon_dis`). They show that the MicroBooNE analysis chain carries single-photon truth labels; they do not state which events labelled the four BDTs.
* **SOURCE**: sample lists exist in the tree for MCC9.10 BNB neutrino overlay, intrinsic nue overlay and NC pi0 overlay (runs 4a-5). They are **not documented as the inputs of this model**; naming them as its training sample would be an inference.

## 4. What the inputs say (INFERENCE from SOURCE)

* **SOURCE**: the 73 inputs fall in seven families (`FROZEN_NUMU_BDT_SOURCE_AUDIT.md` section 6): shower quality br1/br3/lem 29, vertex/gap geometry 11, calorimetry 10, numuCC flag-3 inputs 8, track/hadron activity 7, multiplicity 6, and two upstream BDT scores (`numu_1_score`, `numu_score`).
* **SOURCE**: the br1 inputs are the sub-checks of `bad_reconstruction_sp` (stem topology, longest muon-like track inside the shower, straight track near the stem far end); br3 of `bad_reconstruction_2_sp`; `lem_*` of `low_energy_michel_sp` ("rejects showers that look like michel electrons"). `numu_cc_3_*` come from the numuCC flag-3 check (indirect long muon-like track). `numu_score` is the log-odds of the xgboost numu BDT of `UbooneNumuBDTScorer`; `numu_1_score` is its flag-1 sub-BDT. The header comment of the br / lem inputs is "(none in source)" for the segment-count and length variables: **the source does not say what physical quantity "number of shower segments" or "total length" is meant to discriminate**.
* **INFERENCE (not stated anywhere)**: the stage is named `numu` and consumes muon-like object descriptors and two numu-tagger scores, so the intended **background class is most plausibly muon-neutrino charged-current events (a muon track, possibly with a Michel electron or delta rays, mimicking a single shower)**. Whether other classes (cosmic, NC pi0, intrinsic nue) were also in the background is NOT ESTABLISHED.
* **INFERENCE**: the shower-quality checks are inherited from the nueCC "bad reconstruction" / Michel taggers, whose purpose is to flag shower objects that are really tracks or track-plus-Michel topologies. That makes **compact, few-segment shower objects a plausible muon / Michel-like pattern in the training**. The code does not say that compactness was *chosen* as a muon discriminator; it is one of the inputs the gradient-boosting fit was free to use.

## 5. What can and cannot be established

| question | answer | tag |
|---|---|---|
| intended background class(es) | muon-neutrino CC (muon-like tracks) is the only class the inputs point to; the class list itself is not documented | INFERENCE |
| intended meaning of compact / few-segment shower variables | not documented (no comment in source); plausible reading above | NOT ESTABLISHED / INFERENCE |
| was compactness intentionally a muon / track discriminator | cannot be stated; the model is a gradient-boosted fit on 73 inputs and there is no importance record | NOT ESTABLISHED |
| training sample | not in the XML, the MicroBooNE tree or the history of the single-photon files | NOT ESTABLISHED |
| MicroBooNE-only training | the weights file lives in a MicroBooNE tree and the code is the MicroBooNE WCP-LEE code, so it is **presumably** MicroBooNE; there is no statement and no SBND-trained alternative in the repository | INFERENCE |
| which variables dominate | for the **SBND signal sample** (this repository): `numu_score` (single largest), the br1 / br3 / lem segment and charge inputs, then vertex geometry (`FROZEN_NUMU_BDT_SOURCE_AUDIT.md`, this phase's TreeSHAP). For the **training sample** nothing is documented | MEASURED / NOT ESTABLISHED |
| upstream BDTs | `numu_score` and `numu_1_score` come from `UbooneNumuBDTScorer` (a separate xgboost / TMVA chain; its own training is also not documented here) | SOURCE |

## 6. Consequence for the audit

No MicroBooNE training distribution of any input exists in the available material. A **quantitative MicroBooNE-to-SBND domain-shift test is therefore impossible** (nothing to compare the SBND values with), and this audit does not claim a shift. What can be measured is the SBND behaviour of the frozen model and its association with reconstruction state (`NUMU_COMPACT_SHOWER_TRAINING_DOMAIN_AUDIT.md`).

What would settle the question (not available): the training ntuples or the training script with the class definitions; the per-class distributions of the 73 inputs (at least the segment count, total shower length and `numu_score`) for the MicroBooNE training and validation samples; the XGBoost training log with the importance table.
