# Round-2: the questions that existing evidence does not answer

Date: 2026-11-17. Updated the same evening after the audit of Haiwang's active production
(`HAIWANG_ROUND2_ACTIVE_PRODUCTION_TRACKER.md`; `ROUND2_COLLABORATOR_QUESTION_CLOSURE_AUDIT.md` §10). Draft, **not sent**.
Nobody is to be contacted in this phase.

## Questions still required for Xuyang / Matteo

> **ANSWERED by the release, 2026-11-28 (no question needed).** `numu_round3af` retrains numu_1, numu_2 and cosmict_10
> together with the final model; numu_tagger3 stays shipped. The new level-1 models are TMVA **Grad** files without
> input transformations, so the offline route needs no AdaBoost-with-transforms evaluator. The shipped level-1 models
> are closed with ROOT TMVA itself. See `SP_BDT_UPSTREAM_R4_INTEGRATION_AUDIT.md`. The question below is kept for the
> record.

1. **νμ level-1 models.** When you retrain the νμ CC tagger, will the four νμ level-1 models stay as shipped, with only
   the final `numu_score` model retrained? The level-1 models are `numu_tagger1`, `numu_tagger2`, `numu_tagger3` and
   `cos_tagger_10`; their scores are `numu_1_score`, `numu_2_score`, `numu_3_score` and `cosmict_10_score`.

   *Why it matters.* SP numu and SP other read `numu_score` and `numu_1_score`. We recompute the final `numu_score`
   offline, bit-identical on 320,228 aurora-r2 and 148 refreshed candidates. A changed level-1 model needs its stored
   per-object inputs re-scored through an AdaBoost-with-transforms evaluator, which does not exist yet, or a toolkit
   rerun.

   *Searched first:* `xning/bdt-comm@42236ad`, `Ningclover/sbnd-wirecell-bdt@e0ea617`, Xuyang's Aurora area, and the
   project directory list (Matteo has no Aurora area). There is no νμ spec, code or model, so it cannot be determined
   from files.

## Membership questions (2026-11-28; drafts, NOT sent; Avinay decides whether and when)

From the training-membership manifest (`SP_BDT_UPSTREAM_R4_FOLLOWUP.md` section 3). Each question is something the
accessible sources do not settle.

**Snehadri (DL vertex, DV2-MAX `aurora_space`).** The bundle README says the model was trained on aurora-r2 BNB and intrinsic
νe CC events: fold 1 has 477,997 training events, and fold 0 is a 15,000-event hold-out. Those are the same production units as
our Aurora BNB and νe CC samples. The per-event fold table lives under
`/lus/eagle/projects/neutrinoGPU/snehadri/sbnd-vertexer/` (`cache_info.json`, id signature `70ab2b2bd5e9`), and Eagle is not
mounted on Aurora.
1. Please send the per-event fold table, `(sample, unit or file_id, run, subrun, event, fold)`, and the fold rule, or grant read
   access.
2. Which events did the ranker use? The README says "folds != 0".
3. Was any NC Δ event used?

*Why it matters.* The vertex every SP feature depends on was trained on part of our SP training and holdout events.

**Xuyang.** His row counts are reproduced from his code (νμ to 256 rows, νe to 2 rows; the difference is his 25 PARTIAL files).
4. Are the released `numu_round3af` and `nue_round4_ruleA_v2` meant to be the train-split fits? The code freezes the
   early-stopped fits on the train rows only, with no 100 % retrain, which `spec_v1.md:82` contradicts.
5. Should the 25 PARTIAL files (14 BNB, 11 νe CC) be in training? He used them; our tables exclude them.
6. Should the 109 `r8` beam-off files be in training?

*Why it matters.* Upstream-overlap bookkeeping, and the EAF disjointness check.

**Haiwang.**
7. What is the status of the PARTIAL units? Is the stored `wct_version` "48" in Xuyang's tables his builder's byte-decoding of
   the string (our extractor reads `0.38.0`)? Why does the νe list have 61,249 files against 61,252 pairs?

**Avinay (production policy, not a collaborator question).** 134 groups of generator-identical BNB events (59 subrun pairs)
share the GEN `generator` engine seed under the default `random` policy. Chance alone would give about 2 such pairs in this
sample, so the seed source is not uniform. Any further BNB production should use an explicit seed policy, as configL's
`linearMapping` does.

## Questions still required for Haiwang

**None now.** The earlier question, whether the refresh could include the beam-off training half, is answered by his
production: `wcl1116-fg-beamoff` reprocesses the whole fg1 beam-off with the Round-2 chain.

These need no question today; raise them only when final SP training is ready to start:
- the training-side split of `wcl1116-fg-beamoff`, i.e. its odd-run half, and a copy of those merged CAFs to Aurora.
  The catalogue note already says to split it "the same way";
- which of the two vertex trees (`recTreeWireCell` = `dv2_split_move`, `recTreeWireCell_dv2snap` = `dv2_snap`) Round-2
  production uses.

Nothing else is needed from anyone now. In particular, no new cosmic generation and no deployment-route question until
the models are final. A possible NC π⁰-enriched sample is not to be requested yet: the learning curve says SOME BENEFIT
LIKELY, which is Avinay's call (`SP_BDT_ROUND2_FREEZE_ORDER.md` §11).
