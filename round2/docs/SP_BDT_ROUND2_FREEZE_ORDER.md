# Single-photon BDTs in Round 2: ownership, dependency graph, freeze order and the final model set

Date: 2026-11-17 (Aurora). Decision document for Avinay. Updated the same evening after the read-only audit of Haiwang's
**active** Round-2 production (`HAIWANG_ROUND2_ACTIVE_PRODUCTION_TRACKER.md`). No model was trained for deployment,
nothing was submitted, and no one was contacted.

Sources:
- the XML input lists (`config/features/single_photon_*_inputs_v0.json`);
- the EAF XML audit (`analysis/sp-bdt-thesis-xml-compatibility-20261117` @ `0148e879`);
- the Yandel thesis audits (`YANDEL_THESIS_SP_BDT_TRAINING_SOURCE_AUDIT.md`, `SP_NUMU_TRAINING_SOURCE_AUDIT.md`);
- the SBND toolkit (`SP_BDT_DEPENDENCY_AND_TARGET_AUDIT.md` §1), now WCT 0.38.0 `c935e30d` in the refresh;
- Xuyang's plan (`xning/bdt-comm@42236ad`, public `Ningclover/sbnd-wirecell-bdt@e0ea617`, read-only);
- Haiwang's catalogue `f4f2f93` and ai-helper issue 48.

## 1. Who trains what

| role | person | models |
|---|---|---|
| refreshed reconstruction, training **and** evaluation CAFs | **Haiwang** | WCLocal2026Nov16 (Aurora: training; FermiGrid: evaluation), WCT 0.38.0 + Snehadri's DV2-MAX `aurora_space` DL vertex |
| DL vertex | **Snehadri** | `dv2max/sbnd/aurora_space` (bundle `51588842…`) |
| upstream / general Wire-Cell classifiers | **Xuyang + Matteo** | the **νμ tagger** (final `numu_score`; level-1 `numu_1/2/3_score`, `cosmict_10_score` if changed) and the **νe tagger** (final `nue_score`) |
| **single-photon BDTs** (NC Δ / single-photon analysis) | **Avinay (owner)** | **SP numu, SP other, SP ncpi0**; SP nue a separate decision |

**Do not confuse the two families.** These are different models with different inputs and owners:
- Xuyang/Matteo's νμ model (`numu_score`) is **not** SP numu (`single_photon_numu`).
- Xuyang/Matteo's νe model (`nue_score`) is **not** SP nue (`single_photon_nue`).

The SP models are downstream single-photon classifiers. SP numu and SP other **read** `numu_score`. SP ncpi0 reads the
15 νe level-1 scores. No SP model reads `nue_score`.

## 2. What each model consumes

| model | classifier outputs it reads (XML index) | share of its XML splits | other inputs | thesis / XML fingerprint |
|---|---|---:|---|---|
| νμ level-1 (`numu_tagger1/2/3`, `cos_tagger_10`) | none | — | reco | shipped, not audited here |
| νμ final → `numu_score` (`numu_scalars_scores_0923.xml`) | `cosmict_10_score`, `numu_1_score`, `numu_2_score` (final-model inputs 71–73; `UbooneNumuBDTScorer.cxx:259-261, 473-476`) | — | reco | — |
| νe level-1 (15 models `br3_3 … tro_5`) | none | — | reco | shipped |
| νe final → `nue_score` (258 inputs) | the 15 νe level-1 scores | — | reco | Xuyang/Matteo retrain it |
| **SP numu** (73) | `numu_score` (72), `numu_1_score` (71) | **11.5 %** (`numu_score` 7.7 %: rank 1, root of 41 / 300 trees) | 71 `T_tagger` reco (`numu_cc_3_*`, `numu_cc_flag_3`, `shw_sp_*`) | **EXACT** |
| **SP other** (146) | `numu_score` (144), `numu_1_score` (142), `numu_2_score`, `cosmict_10_score` | **8.7 %** (νμ pair 7.9 %; `numu_score` rank 1, root of 15 / 215 trees) | 142 reco: cosmic taggers, `numu_cc_flag`, `shw_sp_*`, `reco_nuvtxY` = `kine_nu_y_corr` | **EXACT** |
| **SP ncpi0** (45) | the 15 νe level-1 scores (18–32); **not** `nue_score` | **40.6 %** | 18 `shw_sp_*`, 12 `kine_pio_*` (`kine_pio_flag` 0.13 %) | **EXACT** |
| **SP nue** (56) | none | 0 | 56 `shw_sp_*` | **EXACT 200-tree prefix** (§5) |

No SP model reads another SP score, and none reads `nue_score`. The SP cut order `numu → other → ncpi0 → nue` is the order
in which the cuts are applied, **not** a training dependency. The four SP models are siblings, each trained on the same
signal sample against its own background (thesis p.127).

## 3. Final training dependency graph

```text
Haiwang refreshed reconstruction
(Snehadri DL vertex DV2-MAX aurora_space + WCT 0.38.0; WCLocal2026Nov16-Aurora)
             |
             +--> refreshed training CAFs (NC Delta, BNB, nue CC; beam-off odd-run half on FermiGrid)
                      |
                      +--> Xuyang/Matteo nu_mu training
                      |       |
                      |       +--> frozen final numu_score (+ L1 numu_1/2/3, cosmict_10 if changed)
                      |                |   recomputed OFFLINE on the refreshed CAFs (bit-identical rescoring shown)
                      |                +--> Avinay SP-numu
                      |                +--> Avinay SP-other   (+ EXT: beam-off odd-run half)
                      |
                      +--> Xuyang/Matteo nu_e training
                      |       |
                      |       +--> final nue_score            (read by NO SP model)
                      |
                      |   [15 nu_e L1 scores remain stored/fixed unless evidence changes]
                      |                |
                      |                +--> Avinay SP-ncpi0
                      |
                      +--> Avinay SP signal/background labels (truth in the same CAFs)
                              |
                              +--> SP-numu
                              +--> SP-other
                              +--> SP-ncpi0
                              (+ SP-nue only if the domain-shift test says retrain)
```

- SP ncpi0 does **not** depend on the final `nue_score`. It depends heavily on the 15 νe L1 scores, which carry 40.6 % of
  its legacy splits.
- SP other and SP numu depend on the νμ chain.
- Every SP input is computed from the reconstruction, so the new vertex moves all four SP models even where no upstream
  weight changes. The smoke shows the vertex moved for 89 % of matched BNB candidates (tracker §7).
- In the refresh the booked νμ / νe weights are the **shipped** ones. The stored upstream scores are therefore not the
  Round-2 scores until Xuyang/Matteo freeze theirs and they are recomputed.

## 4. Freeze order

1. **Reconstruction: running now.** Haiwang's WCLocal2026Nov16. Aurora NC Δ and BNB are complete; νe CC is resuming.
   Open: which of the two stored vertex trees is the Round-2 vertex (tracker §2). The registry provisionally takes the
   default `recTreeWireCell` (`dv2_split_move`).
2. **Upstream classifiers** (Xuyang/Matteo), trained on the refreshed CAFs.
   - The νμ final model can be recomputed **offline**: bit-identical on 320,228 / 320,228 aurora-r2 and 148 / 148
     refreshed candidates.
   - Whether the νμ L1 models change is still not stated anywhere. That is the one remaining Xuyang/Matteo question.
     The per-object L1 inputs are stored, but no offline AdaBoost/transform evaluator exists yet.
   - The 15 νe L1 models stay as stored (`spec_v1.md:67`).
3. **Avinay's final SP training** on the refreshed training CAFs:
   - SP ncpi0 needs step 1 only;
   - SP numu and SP other need steps 1 and 2, trained together on the same frozen `numu_score`;
   - SP other also needs the beam-off odd-run half on the training side.
4. **Freeze** the SP models, then the **validation-only** joint threshold selection (§7).
5. Export (exporter built, `SP_BDT_EXPORT_EQUIVALENCE_STATUS.md`), equivalence test, handoff to Haiwang, Round-2
   generation with frozen models if needed, then the independent EAF evaluation.

## 5. Avinay's final model set

| model | owner | status | waits for |
|---|---|---|---|
| **SP numu** | Avinay | **FINAL TRAINING WAITS FOR REFRESH + FROZEN UPSTREAM NUMU** | refreshed training lists; Xuyang/Matteo's frozen νμ, recomputed on them |
| **SP other** | Avinay | **FINAL TRAINING WAITS FOR REFRESH + FROZEN UPSTREAM NUMU + TRAINING BEAM-OFF** | as SP numu, plus the odd-run beam-off half from `wcl1116-fg-beamoff` on the training side with an approved exception |
| **SP ncpi0** | Avinay | **FINAL TRAINING WAITS FOR REFRESH** | refreshed training lists. The 15 νe L1 scores stay fixed, or are frozen first. **Policy B** (`kine_pio_flag` as stored) stays the SBND policy unless changed explicitly |
| **SP nue** | Avinay (**not** Xuyang/Matteo) | **DECISION PENDING** | the domain-shift test (§6) on the refreshed CAFs |

**Why Avinay still retrains SP numu** even though Xuyang/Matteo retrain the upstream νμ tagger:
- The frozen SP numu XML relies heavily on the upstream νμ outputs:
  - `numu_score` is legacy rank 1 and `numu_1_score` legacy rank 3;
  - together they make 11.5 % of the legacy splits;
  - `numu_score` is the root split of 41 / 300 trees.
- The SBND development SP numu learned the same pattern: `numu_score` rank 1 (335 splits) and `numu_1_score` rank 2
  (321).
- Once the upstream νμ model is replaced, the legacy SP numu would run outside its training domain.
- Sequence: Xuyang/Matteo freeze νμ → recompute the upstream scores on the refreshed training CAFs → Avinay trains the
  final SP numu. The same applies to SP other (νμ pair 7.9 % of its splits).

**SP nue: the thesis/XML question is resolved.** The open question is the domain shift.
- **Thesis/XML: same model (resolved 2026-11-17).** The Fig. E.4 F scores equal **exactly** the split counts of the
  **first 200 trees** of the frozen `single_photon_nue_bdt_final.xml`: all 56 inputs, 5,721 = 5,721, and no other N
  (`tools/nue_prefix_test.py`, `validation/nue_appendixE_prefix_test.json`).
  - The thesis plot was drawn at round 200 of the same forest, and the XML holds all 300 trees.
  - The thesis target (νe CC background, 100,958 events, p.133) therefore applies to the frozen model.
- It reads no classifier output, so neither upstream retraining affects it.
- All 56 inputs are vertex-relative shower variables, so the new DL vertex moves them by construction.

## 6. SP nue domain-shift test (planned; run only on the refreshed CAFs)

The decision is not made before the refreshed CAFs exist and the test has run. The NC Δ and BNB refresh is complete, so
the test can run as soon as Avinay asks for the table build. Plan:

1. **Rows.** Old aurora-r2 vs new WCLocal2026Nov16-Aurora on **matched** events, i.e. the same `(file_id, run, subrun,
   event)`; the pair lists are identical by unit.
   - Candidates match on `(…, cand)` where both exist. Unmatched candidates are counted as migration.
   - The rows are SP nue's training classes and the single-photon preselection.
   - Use the vertex tree chosen for Round 2. Run the other tree as a variant.
2. **Per input (56).**
   - Distributions: quantiles and histograms.
   - Standardized shift: (mean_new − mean_old) / sd_old, and the same with medians and IQR.
   - KS statistic and 1-D Wasserstein distance (in sd_old units).
   - Fraction of matched rows that changed, and the fraction at default or sentinel values.
3. **Candidate availability and migration.** Rows gained or lost by `shw_sp_filled`, by the preselection
   (`shw_sp_n_20mev_showers > 0`) and by the candidate hierarchy (main candidate changed), per truth class.
4. **Legacy SP nue score migration.**
   - The legacy XML score on both domains for the matched rows.
   - The 2-D migration at the frozen −1.0 cut: pass→fail, fail→pass.
   - Efficiency and rejection at that cut, per class.
   - ROC AUC of the legacy model, old vs new.
5. **Emphasis.** Inputs tied to the vertex (`shw_vtx_dis`, `min_dis`, the dQ/dx vector from the shower start), the
   shower assignment and the candidate hierarchy.
6. **Decision, made afterwards by Avinay.**
   - **KEEP LEGACY SP NUE** if the legacy model's AUC and cut efficiency / rejection on the new domain stay within the
     old values by an agreed tolerance, and no vertex-tied input shifts beyond it.
   - **RETRAIN SP NUE** otherwise.
   - The tolerance is fixed before the run, in the analysis note, not after looking.

The same machinery serves the SP numu, other and ncpi0 domain checks. `tools/refresh_smoke_check.py` already runs the
matching and the builder on both trees.

## 7. Threshold policy

- **No final SP threshold is chosen now.**
- The final threshold optimisation happens only after all of these:
  - the upstream νμ / νe models are frozen;
  - the final SP model set is frozen;
  - the training refresh is complete;
  - a validation partition is defined. It is disjoint from both the training rows and the test fold.
- It uses **training/validation rows only**, never the official Round-2 evaluation samples (tracker §4).
- From the export work: place thresholds **between** distinct validation scores, never on one. The handoff must list
  rows within 1e-4 of each cut (`SP_BDT_EXPORT_EQUIVALENCE_STATUS.md`).
- The source-faithful Round-1 cuts (log10-odds 0.4 / 0.2 / −0.05 / −1.0; thesis Table 5.5 = `cuts.h`) remain the
  **baseline / reference only**.

## 8. Training / evaluation firewall in Round 2

| side | samples |
|---|---|
| **TRAINING** | refreshed Aurora NC Δ (`wcl1116-aurora-ncdr`); refreshed Aurora BNB (`wcl1116-aurora-bnb`); refreshed Aurora νe CC (`wcl1116-aurora-nuecc`) as appropriate; the **odd-run** beam-off half of `wcl1116-fg-beamoff`, only as an approved exception named in the SP other spec |
| **EVALUATION ONLY** | every official fg1 / Gen2 sample and its WCLocal2026Nov16-FermiGrid rerun (`wcl1116-fg-cv`, `-nuecc`, `-run3bnb`, `-opendata`); the official NC Δ (`ncdr`, SAM `EX_ncdeltarad`); the **even-run** beam-off evaluation half, and the full beam-off as a whole; all beam-on data; selected data; any official Round-2 inference outputs |

No model fitting, early stopping, feature choice or threshold choice may touch an evaluation output.
`sp_retrain.firewall` refuses `/pnfs/`, `prod-fermigrid`, `beam-off`, `run3bnb`, `opendata`, and since this update also
`wcl1116-fg` and `WCLocal2026Nov16-FermiGrid` (tests in `tests/test_sp_retrain.py`).

## 9. `kine_pio_flag` (ncpi0): decision support

**Facts:**
- The thesis ncpi0 model splits on `kine_pio_flag`. Its 23 F-score splits equal the XML's 23 splits (21 at 1.5, 2 at
  0.5). Its mean gain is 9.19, 10th of 45 by gain (Fig. E.3).
- MicroBooNE scoring reads the real value (`bdt_convert.cxx:4067`), then forces 0 before the SP scores (lines 4166–4167,
  eyandel `47b1f0c`, "uncomment to match old files").
- In SBND aurora-r2 (census, 9,583 preselected rows), the flag takes 0, 1 and 2.
  - Every flag-0 row has `kine_pio_mass` = `kine_pio_energy_2` = 0 (1,617 / 1,617). Only 14 of 5,749 BNB flag-1/2 rows
    also have mass 0.
  - Flag 1 is set on 77–82 % of positive and 89–90 % of negative rows; flag 2 on 0–3 %.

| option | what it means | for | against |
|---|---|---|---|
| **A** train with the real flag, score with 0 | MicroBooNE's historical behaviour | reproduces the frozen model's production use exactly; the EAF Round-1 baseline already does this for the legacy XML | for a new model it builds a known inconsistency into production. 77–90 % of SBND rows would be scored as flag 0 with filled π⁰ kinematics, a combination absent from training (flag 0 ⇒ mass 0), and every flag split would be routed one way |
| **B** train and score with the real flag | consistent | training as in the thesis; no off-distribution input; uses the information the thesis model found useful | departs from the historical scoring. The scorer must pass `T_kine.kine_pio_flag`, which is in the CAF |
| **C** 0 in training and scoring | the input is kept but constant, never split | consistent; keeps the 45-input interface and order | departs from the thesis training. It loses the flag 1 vs 2 distinction (0–3 % of rows); the 0 vs ≥ 1 information survives in `kine_pio_mass` / `kine_pio_energy_2` |
| **D** remove the input | 44 inputs | consistent, and no dead input | as C, plus a new feature list, exporter variable list and reader change |

**No source makes one option unambiguously required.**
- The thesis fixes the training: the real flag, i.e. A or B.
- MicroBooNE's scoring contradicts its own training.

**Recommended default: B.** It is the only option faithful to the thesis training and consistent between training and
scoring. Keep A only for the legacy XML control, and run C as a development ablation to measure what the flag adds.

**Decided by Avinay on 2026-11-17, before the development training: Policy B.** It is recorded in
`specs/single_photon_ncpi0_training_spec_dev_round1_domain_v1.yaml`. The legacy XML control keeps 0, and the two
conventions are not mixed.


## 10. Round-2 roadmap

```text
DONE:
  source-faithful Round-1 baseline
  legacy source audit
  Yandel training definitions
  XML fingerprints (numu / other / ncpi0 exact; nue = exact 200-tree prefix)
  development SP-numu / SP-ncpi0 (ROUND1_DOMAIN_DEVELOPMENT_DO_NOT_DEPLOY)
  legacy-control comparison
  collaborator-question evidence closure
  SP ncpi0 negative-statistics learning curve (diagnostic): SOME BENEFIT LIKELY
  XGBoost JSON -> TMVA Grad XML exporter + Python equivalence on the dev fixtures

IN PROGRESS:
  Haiwang reconstruction refresh with Snehadri's DL vertex (WCLocal2026Nov16; Aurora NC Delta + BNB complete)
  Xuyang/Matteo upstream nu_mu / nu_e retraining

AVINAY NEXT (Avinay owns the downstream SP training campaign):
  1. monitor / validate the refreshed CAFs (tracker; smoke done; lists when complete)
  2. finish export / equivalence infrastructure (C++ TMVA::Reader + toolkit TmvaGradForest check)
  3. decide SP-nue from the refreshed-domain shift (section 6)
  4. final SP-numu / SP-other / SP-ncpi0 training
  5. freeze SP models
  6. validation-only joint threshold selection
  7. production handoff to Haiwang
  8. official Round-2 generation with frozen models if necessary
  9. independent EAF evaluation
```

Avinay is not waiting passively. Steps 1–3 run now and in parallel with the upstream retraining. Final SP training starts
the moment its gate (§5) opens.

## 11. Readiness

| classifier | target known? | refreshed data | upstream frozen? | development model | final training now? |
|---|---|---|---|---|---|
| SP numu | yes: thesis + exact fingerprint | NC Δ + BNB **complete** (lists not yet written) | **no**: νμ (Xuyang/Matteo) | DONE, DO NOT DEPLOY (test AUC 0.959; legacy 0.926) | **no** |
| SP other | yes: thesis + exact fingerprint | MC complete; beam-off odd-run half **reprocessed on FermiGrid, not yet on the training side** | **no**: νμ | not trained (needs the exception) | **no** |
| SP ncpi0 | yes: thesis + exact fingerprint | NC Δ + BNB **complete** | νe L1 fixed (stored) | DONE, Policy B, DO NOT DEPLOY (test AUC 0.817; legacy 0.754) | **no**: waits for lists and the vertex-tree confirmation |
| SP nue | yes: frozen XML = thesis forest (200-tree prefix) | yes | none needed | — | **DECISION PENDING** (§6) |

**SP ncpi0 negative statistics** (`tools/ncpi0_negative_learning_curve.py`,
`validation/ncpi0_negative_learning_curve_dev.json`; diagnostic, development domain).
- Setup: all 8,915 positive training rows kept; negative training events subsampled at 1/8 … 1 with seeds 1–3; fixed
  test fold.
- Test AUC rises 0.776 → 0.795 → 0.807 → 0.813 → 0.818. That is +0.010 per doubling from 1/2 to 1, against a seed
  spread of 0.0014, with no plateau at the full 4,457 negatives.
- f = 1 with the spec seed reproduces the development model exactly.
- **SOME BENEFIT LIKELY** from more NC π⁰ negatives. The refreshed BNB has the same events, so it adds none.

Development results: `SP_BDT_DEVELOPMENT_TRAINING_SUMMARY.md`.
