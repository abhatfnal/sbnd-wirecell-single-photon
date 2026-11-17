# Round-2: the questions that existing evidence does not answer

Date: 2026-11-17. Updated the same evening after the audit of Haiwang's active production
(`HAIWANG_ROUND2_ACTIVE_PRODUCTION_TRACKER.md`; `ROUND2_COLLABORATOR_QUESTION_CLOSURE_AUDIT.md` §10). Draft, **not sent**.
Nobody is to be contacted in this phase.

## Questions still required for Xuyang / Matteo

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
