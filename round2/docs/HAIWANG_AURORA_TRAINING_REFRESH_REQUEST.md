# Request to Haiwang: a training-only Aurora refresh before the final single-photon BDT freeze

Draft, 2026-11-17. Not sent. This is **not** the official Round-2 evaluation campaign: it touches only the Aurora
training/development samples. No official evaluation sample is involved; the only fg1 product is the beam-off half that
the productions catalogue designates as training side (`fg1-beamoff-train`).

Updated the same day after the thesis audit (`YANDEL_THESIS_SP_BDT_TRAINING_SOURCE_AUDIT.md`) and again after the EAF
XML fingerprint. The training targets of SP numu, other and ncpi0 are now known, and SP numu is proposed to join
(`SP_BDT_ROUND2_FREEZE_ORDER.md` §4). SP nue is undecided. The sample table follows the complete model set.

Revised after the evidence audit (`ROUND2_COLLABORATOR_QUESTION_CLOSURE_AUDIT.md` §8):
- No new cosmic generation is needed. The existing `fg1-beamoff-train` half should be reprocessed instead.
- The final `numu_score` is proven recomputable offline.
- The only open question for Haiwang is in `ROUND2_MINIMAL_COLLABORATOR_QUESTIONS.md`.

## Why it is needed

All SP inputs (numu 73, other 146, ncpi0 45, nue 56) are computed relative to the reconstructed neutrino vertex and its
shower assignment, including `shw_sp_filled` itself. SP numu and other also read `numu_score` and `numu_1_score`.
`SP_BDT_DEPENDENCY_AND_TARGET_AUDIT.md` §6 lists every input that a Round-2 change moves. A model trained on today's
aurora-r2 CAFs would be deployed outside its training domain.

## The sequence

```
old Aurora CAFs (aurora-r2, Round-1 reconstruction)
  -> development pipeline ready                   DONE 2026-11-17 (builder, specs, firewall, scorer bit-check)
  -> new vertex / upstream models frozen           Snehadri (DL vertex); Xuyang (nu_mu, nu_e)
                                                  (targets recovered 2026-11-17 from the thesis)
  -> Aurora TRAINING refresh                      Haiwang, this request
  -> final SP numu / other / ncpi0 training       Avinay, on the refresh only
  -> production model handoff                     Avinay -> Haiwang (export + equivalence test)
  -> official Round-2 generation                  Haiwang, official samples
  -> independent EAF evaluation                   EAF session; Round-1 vs Round-2 on official samples
```

**One rerun can serve everyone.** The rerun carries the frozen vertex and any other Round-2 reconstruction change.
- Xuyang trains νμ and νe on it.
- For SP numu and other, the new `numu_score` is then computed **offline** on the same CAFs with Xuyang's frozen νμ
  model.
  That model reads only inputs stored in the CAF. `sp_retrain.tmva_grad` is bit-identical to the toolkit: on 423 νe
  candidates, and on 320,228 / 320,228 aurora-r2 candidates for the shipped final νμ model
  (`validation/numu_score_offline_bitcheck_aurora_r2.json`).
- A second rerun is needed only if Round-2 changes the νμ *level-1* models, which is still to be confirmed with Xuyang.
  The νe level-1 models are used as stored (Xuyang `spec_v1.md:67`).

## What to rerun

- Wire-Cell **step 2**: pattern recognition, DL vertex, taggers, BDT scorers, truth match and flat tree, then the merge
  into the existing flat CAFs. This is the same pattern as aurora-r2, which reused aurora-r1's step-1 qlpctrees.
- Step 1 (imaging, clustering, Q/L matching) only if a Round-2 change touches it.

## Configuration that must be active

1. Snehadri's frozen DL vertex model and config, with checkpoint sha256.
2. The exact toolkit build that Round-2 will use, tagger code included. Any single-photon shower change, such as the
   Fix2-v2 graph-adjacent fallback studied in this repo, must be decided and in place.
3. The νμ / νe scorer weights exactly as Round-2 will book them. If Xuyang's models are not yet frozen, the shipped ones
   are acceptable, because the new scores can be recomputed offline as above.
4. The same truth-match (`T_match`) rule and the same flat-tree schema family, with the new schema md5 recorded.

## Samples and statistics (Aurora training/development only)

| sample | today (aurora-r2) | refresh | needed by |
|---|---|---|---|
| NC Δ-radiative, configL | 17,603 units, 26,744 events, 16,534 filled candidates | **all** | the single-photon signal (positive class) of SP numu, other and ncpi0, and SP nue if retrained: about 86 % of the positives |
| BNB CV | 11,888 units, 627,205 events, 63,581 filled candidates | **all** | **SP numu**: νμ CC negatives (≈ 39k rows), no enriched νμ sample needed. **SP ncpi0**: ≈ 97 % of the NC π⁰ negatives (≈ 9.2k). **SP other**: NC without π⁰, dirt, out of FV, cosmic-matched. All three: NC π⁰ → 1γ and out-of-FV signal. **Xuyang**: νμ CC / νe background as in her spec |
| CC νe, configL | 61,248 units, 268,839 events | all if Xuyang retrains νe on it; otherwise a fixed subset, e.g. the first quarter of the list | **Xuyang** νe. SP nue negatives only if SP nue is retrained (undecided). Not a class of SP numu / other / ncpi0 |
| **beam-off, training half `fg1-beamoff-train` (reprocess, required for SP other)** | exists: 572 odd-run pairs of fg1 InTime Run 1 (558 after the hold-out), on Aurora in Xuyang's area, training side in the productions catalogue; reconstructed with the fg1 chain (`…-g78f81c64`); 481 usable SP-other rows | reprocess with **the same toolkit and configuration** as the MC refresh: step 2 on its qlpctrees (on dCache scratch on 2026-11-09), or step 1+2 from reco1. Keep the run split; never the even-run evaluation half | the EXT component of the "other" negatives (thesis p.129). Optional: more SBND off-beam data, since 481 rows is only 3 % of the "other" negatives |
| NC π⁰-enriched MC (optional) | none exists on Aurora | only if an internal negative-statistics learning curve shows the final ncpi0 model gains from more negatives | the full BNB gives ≈ 9.2k NC π⁰ negatives (≈ 4.5k on the training side); MicroBooNE trained on 37,205 |

**Required:** NC Δ (all), BNB CV (all), CC νe (as Xuyang needs), `fg1-beamoff-train` reprocessed.
**Optional:** more off-beam data; NC π⁰-enriched MC, only if justified.
**Not needed:** an enriched νμ CC sample; any new cosmic generation.

A subset of BNB would cut the negative classes in proportion. The ncpi0 negatives are already the limiting class, so
the full BNB list is needed.

## Output wanted

- Merged CAFs with the aurora-r2 layout (`recTree` + `recTreeWireCell`) and the same file naming, so the table builders
  run unchanged.
- New lists under a new name, e.g. `dlspace-<tag>/lists/{bnb,nuecc,ncdr}-merged-cafs.txt`. aurora-r2 must not be
  overwritten.

## Branches to persist

- Everything in today's schema: `T_tagger` (all `shw_sp_*`, every level-1 score, `numu_score`, `nue_score`), `T_kine`
  (`kine_pio_*`, `kine_nu_*_corr`), `T_match`, `T_overlap`, `T_truth_nu`, `T_truth_pf`, `T_dlvtx_call` (incl.
  `truth_all_*`) and `Trun`.
- If a toolkit single-photon scorer exists by then: the four inherited single-photon scores as a legacy control.
- Optional: the legacy `numu_score` beside the new one, so the domain shift can be measured.

## Provenance to store with the refresh

- Toolkit commit **as built**, as a hash. The `wct_version` stamp is a `git describe --tags` string that depends on the
  checkout's tags (`aurora-r8-chain.md:155`), so the hash should be recorded beside it.
- Dirty flag, larwirecell commit and wire-cell-data commit.
- sha256 of every booked weight file and of the DL vertex checkpoint. `Trun` stores only their names and paths.
- The compiled config, with its hash.
- Schema md5, the per-unit `merge.json`, and the sha256 of the input reco1 / flatcaf lists and the output lists.
- Job ids and dates.
- **Production POT per unit for the filtered samples.** The recTree header POT undercounts νe CC by ×12 and NC Δ by ×112.
