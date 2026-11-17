# Request to Haiwang: a training-only Aurora refresh before the final ncpi0 / other freeze

Draft, 2026-11-17. Not sent. This is **not** the official Round-2 evaluation campaign: it touches only the Aurora
training/development samples, and no official fg1 / FermiGrid sample is involved.

## Why it is needed

All 45 ncpi0 inputs and all 146 other inputs are computed relative to the reconstructed neutrino vertex and its shower
assignment, including `shw_sp_filled` itself. "other" also reads `numu_score`.
`SP_BDT_DEPENDENCY_AND_TARGET_AUDIT.md` §6 lists every input that a Round-2 change moves. A model trained on today's
aurora-r2 CAFs would be deployed outside its training domain.

## The sequence

```
old Aurora CAFs (aurora-r2, Round-1 reconstruction)
  -> development pipeline ready                   DONE 2026-11-17 (builder, specs, firewall, scorer bit-check)
  -> new vertex / upstream models frozen           Snehadri (DL vertex); Xuyang (nu_mu, nu_e); targets recovered
  -> Aurora TRAINING refresh                      Haiwang, this request
  -> final ncpi0 / other training                 Avinay, on the refresh only
  -> production model handoff                     Avinay -> Haiwang (export + equivalence test)
  -> official Round-2 generation                  Haiwang, official samples
  -> independent EAF evaluation                   EAF session; Round-1 vs Round-2 on official samples
```

**One rerun can serve everyone.** The rerun carries the frozen vertex and any other Round-2 reconstruction change.
- Xuyang trains νμ and νe on it.
- For SP "other", the new `numu_score` is then computed **offline** on the same CAFs with Xuyang's frozen νμ model.
  That model reads only inputs stored in the CAF. `sp_retrain.tmva_grad` is bit-identical to the toolkit, checked on
  423 νe candidates; the same check must pass for the frozen νμ model.
- A second rerun is needed only if Round-2 changes the νμ or νe *level-1* models, or anything upstream of the scores
  that cannot be recomputed from stored inputs.

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

| sample | today (aurora-r2) | refresh | why |
|---|---|---|---|
| NC Δ-radiative, configL (signal) | 17,603 units, 26,744 events, 16,534 filled candidates | **all** | signal-limited |
| BNB CV | 11,888 units, 627,205 events, 63,581 filled candidates | **all** | the NC π⁰, cosmic-matched and out-of-volume negatives come from here |
| CC νe, configL | 61,248 units, 268,839 events | all if Xuyang retrains νe on it; otherwise a fixed subset, e.g. the first quarter of the list | not a class of ncpi0 / other |

A subset of BNB would cut the negative classes in proportion. Both targets are still unknown, so full statistics are
the safe default.

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

- Toolkit commit **as built**. The `wct_version` stamp must equal the commit; today the files say `a2785870` while the
  catalogue says `55177882`.
- Dirty flag, larwirecell commit and wire-cell-data commit.
- sha256 of every booked weight file and of the DL vertex checkpoint.
- The compiled config, with its hash.
- Schema md5, the per-unit `merge.json`, and the sha256 of the input reco1 / flatcaf lists and the output lists.
- Job ids and dates.
- **Production POT per unit for the filtered samples.** The recTree header POT undercounts νe CC by ×12 and NC Δ by ×112.
