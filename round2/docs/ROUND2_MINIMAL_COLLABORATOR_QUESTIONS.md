# Round-2: the questions that existing evidence does not answer

Date: 2026-11-17. Draft, **not sent**. Everything else was closed from existing sources
(`ROUND2_COLLABORATOR_QUESTION_CLOSURE_AUDIT.md`).

## Questions still required for Xuyang

1. **νμ level-1 models.** When you retrain the νμ CC BDT (after νe, `PLAN.md:86`), will the four νμ level-1 models stay
   as shipped, with only the final `numu_score` model retrained?
   - The level-1 models are `numu_tagger1`, `numu_tagger2`, `numu_tagger3` and `cos_tagger_10`. Their stored scores
     are `numu_1_score`, `numu_2_score`, `numu_3_score` and `cosmict_10_score`.
   - The final model is `numu_scalars_scores_0923.xml`, with 74 inputs.

   *Why it matters.* We have shown that the final `numu_score` can be recomputed offline, bit-identical on 320k aurora-r2
   candidates. A changed level-1 model would need its per-object inputs re-scored through an AdaBoost evaluator with
   input transforms, or a second WCT rerun.

## Questions still required for Haiwang

1. **Beam-off in the training refresh.** Can the Round-2 training refresh also reprocess the `fg1-beamoff-train` half
   (572 odd-run pairs, InTime Run 1) with the same toolkit and configuration as the MC refresh?
   - That would be step 2 on its qlpctrees, which were on dCache scratch on 2026-11-09, or step 1+2 from the reco1.
   - The aim is to keep the EXT component of SP "other" in the training domain. Today those files carry the fg1 stamp
     `…-g78f81c64`, not aurora-r2's.
   - Optional: is there any further SBND off-beam data that could be added to the training side? The half gives only
     481 usable SP-other rows.

Nothing else is needed from either of them now. In particular, no new cosmic generation, no NC π⁰ production (first an
internal learning curve), and no question about the deployment route until the models are final.
