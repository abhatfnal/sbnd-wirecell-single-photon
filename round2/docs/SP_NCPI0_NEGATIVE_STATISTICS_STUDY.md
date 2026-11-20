# SP ncpi0: negative-statistics study (WCL1116 development)

Date: 2026-11-20. Rules: `SP_BDT_WCL1116_FULL_DEVELOPMENT_PLAN.md` §4. Results:
`validation/wcl1116_full_dev_ncpi0_{dv2_split_move,dv2_snap}.json`, `validation/sp_ncpi0_extra_negatives_audit_wcl1116.json`.

## 1. Training-side sources of NC π⁰ negatives

| source | NC π⁰ negative rows (split-move) | status |
|---|---:|---|
| `wcl1116-aurora-bnb` | 9,267 (train 4,757; of which FIT 3,800) | the training source |
| `wcl1116-aurora-ncdr` | 285 (NC Δ filter) | already in the training class |
| `wcl1116-aurora-nuecc` | **374** (180 training side) | audited below |
| EXT | 0 (data, no truth) | — |

**Audit of the νe CC rows (`tools/sp_ncpi0_extra_negatives_audit.py`):**

| criterion | finding |
|---|---|
| provenance | `outnuecc` stream of the official Gen2 rare-signal filter (`run_sbnd_gen2_rare_signal_filter.fcl`), applied to full-flux spills (all four flavours + CORSIKA, 125 spills / subrun). The same filter has an **`outncpi0`** stream, which this production **discarded** (`filter_discard_streams`) |
| target definition | satisfied by the label: not signal, NC, true vertex in the 3 cm FV, ≥ 1 primary π⁰ |
| kinematics | like BNB NC π⁰: partner νμ 98 % (BNB 98 %); median E 1.12 vs 1.14 GeV, KS p = 0.50 |
| **environment** | **99.7 %** of these rows are in events that also hold a **CC νe interaction in the active TPC**, against **0.02 %** of BNB NC π⁰ (BNB: 5.8 % with any second active interaction). Mean active interactions 2.03 vs 1.06 |
| duplication | 0 shared files, runs (6.70–6.73 M vs 2.1–5.0 M) or event keys |

**Verdict: `AVAILABLE EXTRA SAMPLE NOT SOURCE-COMPATIBLE`.**
- The NC π⁰ interactions are unbiased in their own kinematics.
- But they are, by construction, the *second* interaction of spills selected for a CC νe. Their reconstruction
  environment (overlapping CC νe activity) is one the BNB training population almost never has.
- Adding them would train on an environment-selected sample.
- They would add only 180 training rows (+4.7 % of the FIT negatives) in any case. Per the learning curve, that is
  worth about 0.0005 AUC.
- So no augmented fit was run.

## 2. Learning curve on NESTED VALIDATION

The FIT negatives are subsampled by event (all positives kept); f = 1 is `FIT_BASELINE`. Nested validation has 1,761
positive / 957 negative rows (split-move).

| f (FIT negatives) | split-move AUC (seed sd) | snap AUC (seed sd) |
|---|---:|---:|
| 1/8 (475) | 0.8699 (0.0048) | 0.8647 (0.0052) |
| 1/4 (950) | 0.8814 (0.0056) | 0.8825 (0.0051) |
| 1/2 (1,900) | 0.8868 (0.0047) | 0.8870 (0.0015) |
| 1 (3,800) | 0.8934 | 0.8943 |
| **gain from 1/2 to 1** | **+0.0066** (1.4 seed sd) | **+0.0074** (5.0 seed sd) |

- The curve still rises, by +0.007 per doubling.
- It agrees with the earlier outer-holdout curve (+0.0069 ± 0.0017; `SP_BDT_WCL1116_DEVELOPMENT_RESULTS.md` §13).
- The legacy XML on the same rows: 0.853 / 0.850.

**Pre-registered rule:** WORTH REQUESTING if the gain is ≥ 0.004 **and** more than 3 seed sd in both modes. Split-move
is only 1.4 sd: its f = 1/2 points scatter by 0.0047 with 957 validation negatives.

## 3. Recommendation

- **By the pre-registered rule: `CURRENT SAMPLE ADEQUATE`.**
- The extra νe CC rows are **`AVAILABLE EXTRA SAMPLE NOT SOURCE-COMPATIBLE`**.

**Context, not a change of rule.**
- The gain is positive in both modes. Doubling the NC π⁰ negatives would be expected to add about 0.007 AUC: modest,
  about a seventh of what SBND retraining already gives (+0.051).
- If more statistics are wanted for the final domain, the source-compatible route exists already: the **`outncpi0`
  stream of the same official Gen2 filter**, kept instead of discarded, or BNB-like NC π⁰ production. It is not the νe
  CC sample.
- No feature or hyperparameter was changed.
