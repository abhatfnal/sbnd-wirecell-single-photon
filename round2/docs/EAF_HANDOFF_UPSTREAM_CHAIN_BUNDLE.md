# Handoff to EAF Claude: the common upstream-score reference, fixture and membership manifest

From Aurora Claude, 2026-11-28, on Avinay's instruction. The Aurora repository and branch are
`abhatfnal/sbnd-wirecell-single-photon`, `round2/sp-bdt-wcl1116-upstream-r4-integration-20261128`. The bundle sits under
`round2/upstream_chain_bundle/`.

**Authorization and limits.** These stay exactly as in your readiness report, and nothing here changes them:
- no official FermiGrid evaluation access and no blinded data;
- no large production;
- no model or threshold freeze;
- `evaluation_guard` stays empty;
- Xuyang's 3.06 / 0.985 cuts are never used.

## 1. The decision: one numerical reference

Avinay decided that the **toolkit-equivalent** implementation is the common numerical reference of Aurora and EAF for the 20
upstream outputs. Those outputs are the four νμ values, the 15 νe level-1 values and `nue_score`.

Your `src/sbnd_single_photon/upstream_scores.py` reproduces Xuyang's standalone xgboost scripts. Those scripts differ from what
the chain stores on about 1 % of candidates, by up to about 0.4. The Aurora implementation equals the chain bit for bit:
- the patched in-chain rerun: 18 units, both trees, all 20 outputs, max |Δ| = 0;
- the shipped final models on every stored score of 593,723 development candidates;
- the Aurora module on every candidate of both trees (`validation/upstream_r4/bundle_equivalence/*.json`).

**Adopt the portable bundle `wc_upstream_chain` 1.0.0 as the scoring core**:
- dependencies: numpy and pandas only;
- no ROOT, no xgboost, no Aurora framework;
- read `round2/upstream_chain_bundle/README.md` and `CONVENTIONS.md`.

Keep your guards: the evaluation guard, write-once overlays, the provenance sidecar, `join_overlay` and raw-feature
protection. Replace only the numbers they wrap.

## 2. What to change in your layer

| your current behaviour | chain behaviour, to adopt | consequence |
|---|---|---|
| xgboost JSON trees (`l1/*.json`, `l2/*.json`) | TMVA-XML chain files (`wirecell/main/uboone/weights/*`, `numu_round3af/wirecell/uboone/weights/*`), float32 cuts, `EvaluateMVA = 2/(1+exp(−2·sum))−1` | last-bit split crossings disappear |
| νe scored only for `br_filled == 1` and non-placeholders; others NaN / status | the chain scores **every** candidate: the level-1 models are not gated by `br_filled`, and placeholders are scored | your `apply_to_sp_inputs(on_unscored='error')` would refuse the SP ncpi0 rows with `br_filled == 0` (17,289 of 27,127 on Aurora). Their chain values are the empty constants, and they are part of SP training |
| a NaN input goes down xgboost's missing branch; status `input_nan` | an object with a NaN evaluates to −999 (it wins a min and loses a max); a final model with a NaN input gives −16.2556 | values differ on those candidates. The bundle flags them in `diag_*` and keeps the chain value |
| level-1 value `float32(tanh(scale·margin + offset))` from the xgboost margin | `float32(EvaluateMVA)` of the converted XML, whose leaves encode the transform | equal up to split crossings |
| `nue_score` −15 / −16.2556 applied afterwards by `to_chain_convention` | produced directly | – |
| the correction is tied to `is_simulation` | in the bundle, k follows the **resolved νμ weights**: 1.071 for `numu_round3af`, 1.0 for the shipped files (they ran unpatched), explicit otherwise | a shipped-weight closure on simulation must not be corrected; the first bundle draft did this and failed the closure on 7,112 / 24,031 NC Δ candidates before the fix |
| νμ: no `cosmict_flag_1` gate | same; the chain has none either | – |
| simulation correction on marked copies | identical semantics (copies only; flag copy only switched off); `kind='mc'/'data'` is mandatory | – |

Suggested change. Vendor `round2/upstream_chain_bundle/` into your repository, as `third_party/wc_upstream_chain/` or via
`pip install`. Then:
1. Verify the copy: `python -m wc_upstream_chain bundle-fingerprint` must print
   **`976614411c847041139eacd50ca8ffba54d50eb1083359fe73167e8fe4ad0c9e`**. This is version 1.0.0 as committed in Aurora `8178610`;
   PBS 9138971 recorded the same value.
2. In `score_nue` / `score_numu`, call `wuc.UpstreamChain([...]).score(cands, objs, kind)` on tables from the pinned
   `tables/build_tables.py --objs` (same schema). Map the outputs to your `up_*` names.
3. Keep the xgboost route only as a labelled cross-check, `release_standalone`, never as an SP input.

## 3. Inventory reconciliation (your 57 vs Aurora's 61)

They are the same 57 files. Aurora counted the 4 νμ chain XMLs twice, because `numu_round3af/wirecell/chain_weights.json` lists
them again. Details:
- the canonical inventory is the 57 unique paths named by the two manifests;
- fingerprint **`1d48baed0b3d386b3848c20829099b736f42d6020456f4ea60dd4dbbf60c1f9f`**: the sha256 of the sorted `releases/<path>
  <sha256>\n` lines;
- your committed `tables/upstream_release/release_file_hashes.csv` gives the same fingerprint (checked in
  `upstream_chain_bundle/wc_upstream_chain/data/release_inventory.json`, `eaf_cross_check`);
- distinct contents: 42, since the nogap level-1 XMLs equal the main ones;
- auxiliary files (manifests, correction, patches, README): 8, fingerprint `7757db60…`.

Chain fingerprints, for the final-domain contract:

| | numu | νe level-1 |
|---|---|---|
| release | `0b8485a8…` | `36ec972f…` |
| shipped | `595a9963…` | `17a8e17e…` |

## 4. The development fixture (V3–V5)

`upstream_r4_dev_fixture_v1`. It is authorized by Avinay as a **development** fixture, drawn from the Aurora development samples
and the permitted odd-run beam-off training half. It is not an evaluation sample. You may register its name in
`configs/upstream_release.yaml: fixtures`, with this authorization text: "Aurora development fixture authorized by Avinay
2026-11-28". Never commit its content.

It comes in two parts:
- `mc/` (transferable; simulation only);
- `beamoff_restricted/`: beam-off training-half rows. These are experimental data, subject to the existing training-half
  restrictions: FNAL only, never public, never used for evaluation.

Contents (all values are float32 bit patterns; compare them exactly):
- `cases/<sample>/<mode>/`:
  - inputs: `cands.parquet`, `objs_<model>.parquet` (Xuyang's schema);
  - `expected_upstream.parquet`:
    - stored (shipped) values;
    - the shipped closure;
    - chain-equivalent released values (`kind` per sample);
    - the MC no-scale diagnostic;
    - the release's standalone xgboost values (`official_xgb_*`), so you can see the split crossings;
    - `diag_*`;
    - `fixture_tags`;
  - SP rows, SP feature vectors in domains A and D, and SP predictions.
- Edge-case tags: empty lists, `br_filled == 0`, pio_2 gate passes and blocks, NaN objects, NaN final inputs, the final-input
  caps and NaN protections, placeholders, flag switched off, scale moving `numu_score`, split crossings (top 15 per output),
  multi-candidate events, and all candidates of the in-chain units.
- `mc/caf/<unit>/{production,released_chain}/`: the 18 in-chain test units (7 NC Δ, 4 BNB, 7 νe CC).
  - `units.tsv` (sha256);
  - `identity_map.parquet`: tree, entry, position, `nu_index`, both trees;
  - `expected_released_chain_scores.parquet`: the values the patched chain stored.
- `mc/models/DEV_DO_NOT_DEPLOY_*.json`: the development SP boosters behind the predictions. Never deploy them; they exist only to
  reproduce the fixture predictions.

The checks to run on EAF:
1. `python -m wc_upstream_chain verify --releases <clone>/releases --head 0f13988db44423a227789e151b0a374e25771abd`.
2. **Scoring (V1 on real candidates).** `python -m wc_upstream_chain check-fixture <fixture> --releases <clone>/releases --shipped
   <wire-cell-data 99c6497f> --part mc`. Expect `ok: true`. Run the same with `--part beamoff_restricted` where that part is
   present.
3. **Reader (V3).** Run the pinned `tables/build_tables.py --objs --file-id-from basename` on `mc/caf/*/production/*.root`. The
   result must equal the fixture `cands`/`objs` of those files column for column (`fixture_tags` contains `in_chain_unit`).
4. **Stored-score closure (V4).** Score your reader's output with the bundle:
   - release route: compare with `expected_released_chain_scores.parquet`. These are values a genuine patched step 2 stored, not
     an emulation;
   - shipped route, with `stored_l1=True`: compare with the stored `numu_score` / `nue_score` of the production CAFs.
5. **Identity (V5).** Translate to your key `(file_index, ev, run, subrun, evt, nu_index)` with `identity_map.parquet`
   (`ev` = `entry`), and confirm the overlay key set equals your candidate set after the placeholder rule.
6. **SP chain.** Rebuild `sp_features_D` from the fixture's domain-A features and your overlay, using
   `wuc.sp.replace_upstream_inputs`. Score them with your SP scorer and the `DEV_DO_NOT_DEPLOY` models. Compare with
   `sp_predictions.parquet`.

Transfer: `round2/docs/SP_BDT_UPSTREAM_R4_FOLLOWUP.md` section 4 gives the commands, which Avinay runs with his own credentials,
and the checksums.

## 5. Answers to your open questions (readiness report §9)

- **Q5: νe level-1 values when `br_filled == 0`.** The chain runs the level-1 models without a `br_filled` gate. On all 593,723
  development candidates, no νe level-1 object exists when `br_filled != 1`. Those candidates therefore store the empty constants
  (`pio_2` 0.2, `br3_3` 0.3, …), with `nue_score = −15`. The SP ncpi0 model sees these constants in training, in both domains.
- **Q6: placeholders.** The chain scores them; their stored values close bit-exact. The Aurora SP preselection drops them
  (`is_placeholder == 0`).
- **Q3: trees.**
  - Xuyang trained on `recTreeWireCell` (split-move) only.
  - Aurora computed the release scores for both trees, and the in-chain test covered both. The snap scores are what a patched
    production would store.
  - Whether the models are *appropriate* for snap is a collaboration question; the final vertex mode is not frozen.
- **Q4: beam-off training half.** 558 files and 80 runs, all odd:
  - Xuyang's 572-pair list minus 14 hold-out files;
  - 109 of the 558 are `r8` files.

  The file list with sha256 is `round2/manifests/wcl1116_dev_v1/beamoff_train_staging.tsv.gz`; per file it is also in the
  membership manifest. Evaluate beam-off with even-run files only, as you planned.
- **Q2: event-level membership.** See section 6.

## 6. Training membership (V7)

Files are in `$SP_WORK/upstream_r4_20261128/membership/`, transferred with the fixture; the summaries are committed as
`round2/validation/upstream_r4/training_membership_*.json`.
- **`membership_candidates_<mode>.parquet`**, one row per candidate:
  - SP roles: `sp_split` (outer holdout), `sp_nested_role`, `in_<model>` / `cls_<model>`;
  - Xuyang's slice: `xn_split_v11`;
  - upstream pool and role: `up_numu_role` and `up_nue_role`, each `fit` / `early_stop` / `ineligible`;
  - `gen_duplicate_group`;
  - `dlvtx_training_status`.
- **`membership_events.parquet`**: every event's `(sample, file_id, run, subrun, event)`, its roles, the generator job and log,
  and the computed seeds for the configL samples (NC Δ, νe CC; formula checked on logs).
- **`membership_files.parquet`**: every CAF.

Facts for the disjointness test:
- (run, subrun, event) is unique across the three Aurora MC samples. Run ranges:
  - BNB: 2100001–2110757 and 5000001–5000813;
  - νe CC: 6700001–6734897;
  - NC Δ: 7000005–7030038.

  The FermiGrid samples are separate productions. Comparing by bookkeeping metadata is yours to do, under Avinay's approval; do
  not read evaluation events.
- **Duplicates.** 134 groups of generator-identical BNB events (59 subrun pairs, a GEN `generator`-seed collision under the
  `random` policy) exist inside the Aurora BNB sample.
- **The Aurora odd-subrun outer holdout is NOT upstream-independent.** Xuyang fitted his released models on most of those rows
  (`up_*_role == 'fit'`).
- **DL vertex.** The DL-vertex model was trained on aurora-r2 BNB and νe CC units, the same production units as our BNB and νe CC
  samples. The per-event fold list is not on Aurora; it has been requested from Snehadri.

## 7. What Aurora would like back

- The `check-fixture` report from EAF (environment: numpy, pandas and Python versions). A non-`ok` result on a new platform means
  the float64 `exp`/`log10` of that build differs. Report it before using any score.
- Results of V3–V5 on the fixture.
- Confirmation that your overlay now carries chain values for every candidate, with no NaN for `br_filled == 0` or placeholders.
- No result on any official sample.
