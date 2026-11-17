# Single-photon BDTs in Round 2: dependency graph, freeze order and which models to retrain

Date: 2026-11-17 (Aurora). This is a decision document for Avinay. Nothing was trained, submitted or sent.

Sources:
- the XML input lists (`config/features/single_photon_*_inputs_v0.json`);
- the EAF XML audit (`analysis/sp-bdt-thesis-xml-compatibility-20261117` @ `0148e879`: split counts, root splits,
  upstream shares);
- the Yandel thesis (`YANDEL_THESIS_SP_BDT_TRAINING_SOURCE_AUDIT.md`, `SP_NUMU_TRAINING_SOURCE_AUDIT.md`);
- the SBND toolkit at `a2785870` (`SP_BDT_DEPENDENCY_AND_TARGET_AUDIT.md` §1);
- Xuyang's plan (`xning/bdt-comm@2c499b9`, read-only).

## 1. What each model consumes

| model | classifier outputs it reads (XML index) | share of its XML splits | other inputs | thesis / XML fingerprint |
|---|---|---:|---|---|
| νμ level-1 (`numu_tagger1/2/3`, `cos_tagger_10`) | none | — | reco | shipped, not audited here |
| νμ final → `numu_score` (`numu_scalars_scores_0923.xml`) | `cosmict_10_score`, `numu_1_score`, `numu_2_score` (final-model inputs 71–73; `UbooneNumuBDTScorer.cxx:259-261, 473-476`) | — | reco | — |
| νe level-1 (15 models `br3_3 … tro_5`) | none | — | reco | shipped |
| νe final → `nue_score` (258 inputs) | the 15 νe level-1 scores | — | reco | Xuyang retrains it |
| **SP numu** (73) | `numu_score` (72), `numu_1_score` (71) | **11.5 %** (`numu_score` 7.7 %: rank 1, root of 41 / 300 trees) | 71 `T_tagger` reco (`numu_cc_3_*`, `numu_cc_flag_3`, `shw_sp_*`) | **EXACT** |
| **SP other** (146) | `numu_score` (144), `numu_1_score` (142), `numu_2_score`, `cosmict_10_score` | **8.7 %** (νμ pair 7.9 %; `numu_score` rank 1, root of 15 / 215 trees) | 142 reco: cosmic taggers, `numu_cc_flag`, `shw_sp_*`, `reco_nuvtxY` = `kine_nu_y_corr` | **EXACT** |
| **SP ncpi0** (45) | the 15 νe level-1 scores (18–32); **not** `nue_score` | **40.6 %** | 18 `shw_sp_*`, 12 `kine_pio_*` (`kine_pio_flag` 0.13 %) | **EXACT** |
| **SP nue** (56) | none | 0 | 56 `shw_sp_*` | **MISMATCH** (§4) |

No SP model reads another SP score, and none reads `nue_score`. The SP cut order `numu → other → ncpi0 → nue` is the order
in which the cuts are applied, **not** a training dependency. The four SP models are siblings, each trained on the same
signal sample against its own background (thesis p.127).

## 2. Dependency graph

```
 reconstruction: imaging / clustering / Q-L match / DL vertex / pattern recognition / taggers
 (Snehadri's DL vertex, shower and candidate changes, toolkit pin)
   |
   +--> nu_mu level-1: numu_1/2/3_score, cosmict_10_score --> nu_mu final: numu_score    [Xuyang: nu_mu CC "after nu_e"]
   |        |                                                   |
   |        +-- numu_1_score ------------+----------------------+--> SP numu   (+71 reco)
   |        +-- numu_1/2, cosmict_10 ----+----------------------+--> SP other  (+142 reco)  <- also an in-time-cosmic sample
   |
   +--> nu_e level-1: 15 scores (br3_3 ... tro_5) ---------------> nu_e final: nue_score   [Xuyang: retrained; read by no SP model]
   |        |
   |        +---------------------------------------------------------> SP ncpi0 (+18 shw_sp, +12 kine_pio)
   |
   +---------------------------------------------------------------> SP nue   (56 shw_sp only)
```

Every SP input is computed from the reconstruction. A vertex or reconstruction change therefore moves all four SP
models, even where the upstream classifier weights stay the same: the level-1 scores are recomputed from new inputs.

## 3. Freeze order

1. **Reconstruction freeze:** the DL vertex, any shower or candidate change (for example the Fix2-v2 fallback), and the
   toolkit commit.
2. **Upstream classifier freeze.**
   - The νμ chain (Xuyang): `numu_score`, and whether the νμ level-1 models change, which her plan does not state.
   - The 15 νe level-1 models stay as shipped: her training uses "the 15 small-model scores as STORED in the file"
     (`steps/step3_spec/spec_v1.md:67`). Re-confirm at the freeze.
   - `nue_score` is not needed by any SP model.
3. **Aurora training refresh** (Haiwang; `HAIWANG_AURORA_TRAINING_REFRESH_REQUEST.md`). If only the νμ *final* model
   changes after the refresh, `numu_score` can be recomputed offline from stored inputs. That needs the same bit check
   that `tmva_grad` passed for νe. A νμ level-1 change needs a second rerun.
4. **SP training, final:**
   - **ncpi0** after steps 1 and 3;
   - **numu and other together** after steps 1, 2 (νμ) and 3. "other" also needs the in-time-cosmic sample.
   - Training numu and other on the same frozen `numu_score` keeps every SP input in one domain.
5. Export, equivalence test, handoff, official Round-2 generation, then the independent EAF evaluation.

## 4. Retrain decision per model

**SP numu: RETRAIN FOR ROUND 2.** The legacy XML is kept as a control only.
- Its heaviest input, `numu_score`, will be retrained by Xuyang (`PLAN.md:86`). The two νμ scores carry 11.5 % of the
  splits and sit at the root of 64 of 300 trees.
- Without retraining, SP numu would be evaluated on a `numu_score` distribution it was never trained on, by an
  unmeasurable amount.
- SP other reads the same two scores. Retraining one but not the other would leave the two νμ-reading siblings in
  different domains.
- The target is source-established, the thesis model is the frozen XML (exact fingerprint), and aurora-r2 holds both
  classes (≈ 39k νμ CC negatives on the full lists). No extra sample is needed.

**SP other: RETRAIN FOR ROUND 2,** after the in-time-cosmic sample exists and the νμ chain is frozen. The legacy XML is
kept as a control.
- Same νμ argument as SP numu (7.9 % of splits).
- The target is source-established with an exact fingerprint, but EXT is part of its negative class (thesis p.129).

**SP ncpi0: RETRAIN FOR ROUND 2.** The legacy XML is kept as a control.
- It is in the Round-2 plan from the start.
- At the pure working point it is the strongest purity step of the four: it takes 14.2 % → 26.7 % purity, against
  17.9 % → 10.8 % efficiency (thesis Table 5.5).
- Its 15 νe level-1 inputs (40.6 % of its splits) **stay as shipped** in Xuyang's plan, so ncpi0 does **not** wait for
  her. If she alters any of the 15 level-1 models, ncpi0 must wait for them too.
- It waits for the reconstruction freeze, the refresh, and Avinay's `kine_pio_flag` policy (§5).

**SP nue: DECISION BLOCKED.** Until the decision is made, the legacy model stays in use. Reasons:
- It reads no classifier output, so neither of Xuyang's changes affects it.
- All 56 inputs are vertex-relative shower variables (`shw_vtx_dis`, `min_dis`, the dQ/dx vector from the shower start,
  …). The DL vertex moves them by construction, but by an amount that cannot be measured before the refresh exists.
  The same is true of every MicroBooNE model applied to SBND reconstruction in Round 1.
- **Thesis/XML fingerprint MISMATCH.** Trees, depth and inputs agree (300 / 5 / 56), and the printed labels agree with
  the bar lengths. But every one of the 56 Fig. E.4 F scores is lower than the frozen-XML split count: 5,721 against
  8,236 in total, for example `shw_sp_length_total` 324 against 424.
  - The thesis's νe BDT is therefore not exactly the frozen `single_photon_nue_bdt_final.xml`.
  - One hypothesis fits: an earlier prefix of the same forest. That is testable on EAF by counting splits per variable
    over the first N trees, for N = 1 … 300, against the Fig. E.4 vector.
  - Until then, the thesis target for SP nue (νe CC background, 100,958 events, p.133) is source-established for the
    *thesis* model only.

What would unblock SP nue:
1. Measure, on the refresh, how far its 56 inputs and its cut decision move relative to aurora-r2.
2. Run the EAF prefix test.
3. Get an analysis-group decision on whether Round 2 includes it. If retrained, `aurora-r2-nuecc` (or its refresh)
   provides the negatives.

## 5. `kine_pio_flag` (ncpi0): decision support

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

**Development training of ncpi0 waits for Avinay's choice.** The spec records `policy: UNDECIDED`.

## 6. Development-training readiness

| classifier | target known? | data available? | upstream frozen? | development training now? | final training now? |
|---|---|---|---|---|---|
| SP numu | **yes**: thesis + exact fingerprint (`SP_NUMU_TRAINING_SOURCE_AUDIT.md`) | **yes**: BNB νμ CC (≈ 39k rows on the full lists) + signal | **no**: `numu_score` / `numu_1_score` from Xuyang's νμ chain (development uses the shipped models) | **yes, after Avinay's review** (spec v0.1.0) | no |
| SP other | **yes**: thesis + exact fingerprint | **no**: no EXT / in-time-cosmic sample | **no**: νμ chain | **no** | no |
| SP ncpi0 | **yes**: thesis + exact fingerprint | **yes** | νe level-1 unchanged in Xuyang's plan (re-confirm); reconstruction not frozen | **yes, after Avinay's review and his `kine_pio_flag` choice** (spec v0.2.1) | no |
| SP nue | thesis target known for the thesis model; frozen XML fingerprint MISMATCH | yes (`aurora-r2-nuecc`, BNB νe) | no upstream classifier | **not proposed** (decision blocked, §4) | no |

**Development model:** trained on aurora-r2 only, to validate the machinery (splits, labels, export and equivalence).
It is never deployed.

**Final Round-2 model:** trained on the refreshed training sample, after the DL vertex and reconstruction freeze, after
the required Xuyang models are frozen, and once Haiwang's training-only refresh exists.
