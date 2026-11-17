# Haiwang's active Round-2 production (WCLocal2026Nov16): tracker for the single-photon BDT retraining

**LIVE SNAPSHOT, 2026-11-17 19:46 UTC.** Read-only audit of Haiwang Yu's area. Nothing there was modified and no one
was contacted. Paths, job states and counts will change; re-check before relying on them.

This replaces `HAIWANG_AURORA_TRAINING_REFRESH_REQUEST.md` (kept, marked SUPERSEDED): Haiwang already started the
refresh, with Snehadri's new DL vertex, for the training and the evaluation samples.

Sources:
- productions catalogue `yuhw/sbnd-wirecell-production` `main` `f4f2f93` (`docs/productions.js`, 2026-11-17 19:07Z);
- ai-helper issue 48 (`yuhw/wire-cell-toolkit-ai-helper/issues/48-wclocal-2026nov16-productions/`, `e75e403`), its §1
  pins and §10 status;
- the run directory `yuhw/production-prep/WCLocal2026Nov16/`: `jobs.txt`, `scripts/p5-full.pbs`, tallies, logs, per-unit
  `status` / `validate*.json`;
- `qstat`.

Compact provenance: `manifests/wcl1116_aurora_v0/production_provenance.json`. Registry:
`config/samples/round2_training_samples.yaml`.

## 1. Production

| item | value |
|---|---|
| name | **WCLocal2026Nov16**: `WCLocal2026Nov16-Aurora` (catalogue side **training**) and `WCLocal2026Nov16-FermiGrid` (side **evaluation**); catalogue ids `wcl1116-aurora-*`, `wcl1116-fg-*` |
| requested | Haiwang, 2026-11-16 (issue 48 §0). Do not delete aurora-r1, aurora-r2 or fg1 |
| toolkit | WCT **0.38.0**, tag → `c935e30d44a09bf208f6de2c2968171b01efd63d` (= master `647b2733` + `version.txt`; contains #544, #547, #548). Worktree clean. `git describe` = `0.38.0`. Stored `Trun.wct_version` = `"0.38.0"`. 0.38.1 is test-only; the productions stay on 0.38.0 |
| wire-cell-data | `99c6497fad6ba55ecbf53f4c205c5720dba10140` (wire-cell-data #8, `dsnehadri/dv2max-sbnd-aurora-space`), plus the site-added `XGB_nue_seed2_0923.xml` (untracked, byte-identical to aurora-r2's) |
| larwirecell | `sbnd-wc-flatcaf` `ad5d9421`. On Aurora step 1 was **not rerun**: aurora-r1's step-1 tars were hardlinked, and 0.38.0 step 1 reproduced 22/22 test units array by array |
| sbndcode / container | v10_14_02_03 e26:prof, SL7 image as in aurora-r2 / fg1 |
| workflow | `sbnd-wirecell-production` branch `wclocal-nov16`: `d05cf47` (Aurora), `53a90eb` + `f452d76` (FermiGrid) |
| chain | step 2 (`wct-pr.jsonnet`) **twice** per unit, then one merged CAF with **two Wire-Cell trees** |
| config md5 (compiled, normalised) | sim: split-move `fa3745b3…`, snap `91e79e85…`, default = split-move. data: split-move `5da14b64…`, snap `5556ac04…` |
| schemas | `recTreeWireCell` `af9c87c8…` (= aurora-r2, 2,416 branches); `recTreeWireCell_dv2snap` `d4396a34…` (production schema, 2,401 = the same minus the 15 `T_dlvtx_space` branches) |

## 2. Snehadri's DL vertex as run

| item | value |
|---|---|
| model | **DV2-MAX `aurora_space`** (WireCell PR #547; wire-cell-data #8), format `dv2max-bundle-v2`, created 2026-11-14 |
| bundle | `dv2max/sbnd/aurora_space/bundle.json`, sha256 **`51588842984919b5d8146f007287a5e7841be6bbc709263b10cdb39046ff8a74`** |
| files (sha256) | `pass1.pt` `193ef28d…`, `pass2.pt` `bd42b0c3…`, `ranker_fold0.txt` (LightGBM) `e5368502…`, `isotonic_fold0.json` `0ad6bd7f…` (`SHA256SUMS` 5/5 OK per Haiwang; recomputed here for the bundle) |
| stored in every CAF | `Trun.dl_weights` = `dv2_split_move:` or `dv2_snap:` + `dv2max/sbnd/aurora_space/bundle.json@sha256:51588842…`. aurora-r2 had `uboone/scn_vtx/t48k-m16-l5-lr5d-res0.5-CP24.pth` |
| two vertexing passes | `recTreeWireCell` = **`dv2_split_move`**, the 0.38.0 default (sim default md5 = split-move), with the space dump. `recTreeWireCell_dv2snap` = **`dv2_snap`**: the same model, snapped to the nearest PR-graph vertex |
| trained on | aurora-r2 BNB + intrinsic νe CC with `T_dlvtx_space`, fold 1, 477,997 events. The 15,000-event hold-out fold 0 gives 0.929 of events with a vertex within 1 cm |
| is it the expected update? | It is Snehadri's DL-vertex model merged into wire-cell-data and the toolkit on 2026-11-16. The production uses exactly that bundle, by hash. I did not look at Snehadri's private area |

**Open for SP training.**
- **Which tree?** Both passes are "kept side by side" (issue 48 §0). The audit found no record of which one is the
  Round-2 vertex. `recTreeWireCell` (split-move) is the toolkit default and the name existing readers use, so the
  registry takes it **provisionally** (`training_tree_confirmed: false`). The SP models must be trained on the vertex
  that Round-2 production uses.
- **DL training overlap.** The vertex network was trained on fold 1 of the same aurora-r2 BNB and νe CC events the SP
  training uses. NC Δ and the official evaluation samples were never in it. Vertex quality on the BNB and νe training
  events may be better than on unseen events, which would shift SP inputs between training and evaluation. Check
  planned, read-only, when the tables exist:
  - compare vertex resolution and SP input distributions between refreshed NC Δ and BNB signal-like rows;
  - compare DL fold 0 with fold 1 on BNB, if the fold rule becomes available from the bundle documentation. It is not
    in `bundle.json`.

## 3. Jobs (Aurora, project WireCell_aurora, queue capacity)

| PBS id | what | submitted (UTC) | ran (UTC) | end state |
|---|---|---|---|---|
| 9096966 | P4 pilot, 8 nodes × 2 h, 908 units / 9,214 events | 11-17 01:43 | 01:54 → 02:15 | F, exit 0 (908/908) |
| 9097095 | P5 **BNB**, 8 × 6 h | 02:30 | 06:20 → 10:44 | F, exit 0 |
| 9097098 | P5 **NC Δ**, 8 × 3 h (afterany 9097095) | 02:31 | 10:57 → 13:58 | F, walltime (exit −29); resumed |
| 9097992 | P5 NC Δ resume, `WC_TASKS_PER_UNIT=75` | 13:05 | 15:04 → 17:04 | F, exit 0 |
| 9097132 | P5 **νe CC**, 8 × 10 h | 02:43 | 07:35 → 17:36 | F, walltime (exit −29); resumed |
| 9097990 | P5 νe CC resume, 8 × 7 h, `WC_TASKS_PER_UNIT=75` | 13:05 | 19:34 → (running) | **R** at 19:46 |

FermiGrid (`porting_sbndbuild03`): P5 done 2026-11-17 for 840,808 of 840,912 events (99.988 %). There are 54,264 merged
CAFs on dCache persistent, ADLER32-checked, plus 2 timeout reruns (`72823730`, `31002649`). Five deterministic step-2
segfaults are not rerun; that is Haiwang's decision.

## 4. Samples

### Training (Aurora; catalogue side "training")

| sample | catalogue id | input (unit list) | output | status | events |
|---|---|---|---|---|---|
| NC Δ-radiative configL | `wcl1116-aurora-ncdr` | `WCLocal2026Nov16/full/ncdr-pairs.tsv`: 17,604 units, the same reco1 as aurora-r2 (aurora-r2 list: 17,603 files) | `full/ncdr/node<k>/<unit>/merged/<unit>.wc.flat.caf.root` | **COMPLETE**: 17,604 / 17,604 OK, both validations PASS | 26,745 / 26,745 in each pass |
| BNB CV | `wcl1116-aurora-bnb` | `full/bnb-pairs.tsv`: 11,888 units (= aurora-r2) | `full/bnb/node<k>/<unit>/merged/…` | **COMPLETE**: 11,874 OK + 14 PARTIAL (13 aurora-r1 step-1 skips + 1 deterministic segfault, as in aurora-r2); validations PASS 11,888 / 11,888 | 627,170 of 627,205 good in each pass |
| CC νe configL | `wcl1116-aurora-nuecc` | `full/nuecc-pairs.tsv`: 61,252 units (aurora-r2 list: 61,248 files) | `full/nuecc/node<k>/<unit>/merged/…` | **IN PROGRESS**. After 9097132: 39,310 OK, 9 PARTIAL, 2 FAIL (pool logs, 17:36Z). Resume 9097990 running | 268,865 expected |
| beam-off, training half | (no own entry yet) | odd runs of fg1 InTime Run 1: inside `wcl1116-fg-beamoff` (1,096 pairs, both halves) | FermiGrid `/pnfs/sbnd/persistent/users/yuhw/prod-fermigrid/WCLocal2026Nov16/beam-off/<id>/`, **not on Aurora** | **REPROCESSED ON FERMIGRID, NOT YET SPLIT** (§5) | full sample 49,414 of 49,466 with Wire-Cell output, + pilot |

No refreshed **list** exists yet (aurora-r2 had `dlspace/lists/<s>-merged-cafs.txt`). `tools/make_refresh_list.py`
builds one read-only from the per-unit status and validations. It refuses while any listed unit has no final status.

### Evaluation only (FermiGrid; catalogue side "evaluation")

| sample | catalogue id | input | output | status |
|---|---|---|---|---|
| official MC BNB CV 500k | `wcl1116-fg-cv` | the fg1 CV pairs (37,742) | `/pnfs/…/WCLocal2026Nov16/mc-cv/<id>/` | main pass done: 494,981 of 495,013 P5 events (+ pilot) |
| official MC νe CC 100k | `wcl1116-fg-nuecc` | fg1 νe CC pairs (11,445) | `/pnfs/…/mc-nuecc/<id>/` | main pass done: 98,997 of 99,015; 1 timeout pair rerunning |
| fg1 beam-off (both halves) | `wcl1116-fg-beamoff` | fg1 beam-off pairs (1,096) | `/pnfs/…/beam-off/<id>/` | main pass done: 49,414 of 49,466; 1 timeout pair rerunning. Catalogue: "do not use the full sample for ML; split it the same way" |
| Run 3 BNB data | `wcl1116-fg-run3bnb` | 2,208 pairs | `/pnfs/…/run3bnb/<id>/` | main pass done: 108,384 of 108,386 |
| Run 1 open FixedDev data | `wcl1116-fg-opendata` | 1,817 pairs | `/pnfs/…/opendata/<id>/` | main pass done: 89,032 of 89,032 |
| **official NC Δ (SAM `EX_ncdeltarad`)** | — | — | — | **NOT INCLUDED.** Only the fg1 production `ncdr` (13,772 events, 2026-11-10) exists |
| selected data (`sel-nuecc-r2`, `sel-ncsb-r2`) | — | — | — | **NOT INCLUDED** (aurora-r2-data only) |

Every entry is still shown as "running" until both sites finish (owner, 2026-11-17).

## 5. The beam-off training half

**Verdict: INCLUDED. It was reprocessed with the Round-2 chain inside `wcl1116-fg-beamoff`, but it is not yet available
on the training side.**
- The FermiGrid beam-off rerun covers all 1,096 fg1 beam-off pairs with the same toolkit, DL bundle and two passes as the
  Aurora MC. Step 1 is reused from the fg1 tars, and 0.38.0 step 1 reproduced 25/25 test pairs.
- The old domain mismatch (`…g78f81c64` vs aurora-r2 `…ga2785870`) is therefore gone: training MC and beam-off now share
  step 2.
- Pair ids keep the fg1 form `data_filtered_decoded_reco1-<uuid>`. They match `fg1-beam-off-train.list.tsv` by id: 3 of
  the 42 from-reco1 pairs and 9 of the 11 pilot pairs are training-side ids. The training half is the odd-run subset,
  and the 572 known ids are its core. Pairs newly recovered from reco1 must be assigned by run parity.
- **Still missing:**
  - a training-side catalogue entry or list for the odd-run half (the owner's note asks for the split);
  - a copy of those merged CAFs on Aurora (the old half was copied to `xning/data/fg1-beam-off-train/`);
  - Avinay's `approved_exceptions` entry in the SP other final spec (the firewall refuses `/pnfs/`, `prod-fermigrid`
    and `beam-off` paths without it).
- These are logistics, not physics. They are the **only missing sample requirement for final SP other**. No message has
  been sent.

## 6. Upstream scores in the refresh

- **Booked BDT weights.** All 36 files `clus.jsonnet` names in `uboone/weights` are the **shipped MicroBooNE-trained**
  files, byte-identical to aurora-r2's: `numu_scalars_scores_0923.xml` `426e670c…`, `XGB_nue_seed2_0923.xml` `6199d202…`,
  the 4 νμ and 15 νe level-1 XMLs, and the rest.
  - The stored `numu_score`, `numu_*_score`, `cosmict_10_score`, `nue_score` and the 15 νe L1 scores are therefore
    **not** the Round-2 upstream scores. They are the shipped models applied to the new reconstruction.
  - No single-photon scorer is booked.
- **Offline rescoring is possible on the new schema.** The recTreeWireCell branch list equals aurora-r2's, and the snap
  tree lacks only the 15 `T_dlvtx_space` branches. In the smoke (§7):
  - all 74 νμ-final, 73 SP numu, 146 SP other, 45 SP ncpi0 and 56 SP nue inputs are present in both trees;
  - the stored `numu_score` re-scores bit for bit offline (148 / 148 candidates);
  - the νμ level-1 per-object inputs (`numu_cc_1_*` 7, `numu_cc_2_*` 4, `cosmict_10_*`) and the 15 νe L1 scores are
    stored;
  - Xuyang's 258-input νe final model reads only `T_tagger` branches that both schemas carry.

## 7. Smoke comparison with aurora-r2 (read-only)

`tools/refresh_smoke_check.py`, `validation/refresh_smoke_wcl1116_aurora.json`. Sample: 5 BNB units (250 events) and 20
NC Δ units (31 events), the first OK units of node0, each against the same unit in aurora-r2. This is a smoke test, not a
vertex study.

| check | BNB | NC Δ |
|---|---|---|
| trees `recTree`, `recTreeWireCell`, `recTreeWireCell_dv2snap` | present | present |
| branches new = aurora-r2; snap = split − 15 space branches | yes | yes |
| (run, subrun, event) identical in recTree, both trees and aurora-r2 | yes | yes |
| `wct_version`; `dl_weights` | `0.38.0`; aurora_space `51588842…` | same |
| table builder (`build_tables.extract`) on old / split / snap | 0 errors | 0 errors (1 unit with no candidate skipped) |
| candidate vertex moved > 0.1 cm (matched candidates) | split 89 %, snap 74 % (122) | split 100 %, snap 73 % (26) |
| neutrino-partner candidates within 1 cm of the SCE true vertex | 0.52 → split 0.72, snap 0.55 | 0.20 → split 0.48, snap 0.40 |
| SP inputs changed on matched filled rows | nearly all rows, all four models | same |
| `numu_score` offline rescoring | 122 / 122 bit-identical | 26 / 26 |

The 1 cm numbers come from a handful of events, and the BNB events include DL-training events (§2). No full table build
was run, as the task prescribes.

## 7a. Unit counts

The counts in §4 come from Haiwang's own tallies (`p5-bnb-tally.txt`, `p5-ncdr-tally.txt`) and the νe CC pool logs.
`tools/make_refresh_list.py --census-out` checks the same thing independently: per unit it reads the status and both
validations, and it writes no list.
- A single-threaded run on the login node was stopped after 17 min still inside NC Δ (17.6k units). It is metadata-bound
  on Lustre, and the run left no output.
- The tool now uses `scandir` and has `--threads`. Run it on a compute node when the lists are actually built.
- Unit test: `test_make_refresh_list_census_and_refusal`.

## 7b. Update, 2026-11-17 night: development lists

`tools/make_refresh_list.py` ran on compute nodes (PBS 9099500).
- Development lists and manifests for `wcl1116-aurora-ncdr` (17,604 / 17,604 OK) and `wcl1116-aurora-bnb` (11,874 OK;
  14 PARTIAL excluded, 729 Wire-Cell events) are in `manifests/wcl1116_dev_v1/`.
- They serve the WCL1116 **development** campaign (`SP_BDT_WCL1116_DEVELOPMENT_RESULTS.md`). The final-training
  registry stays on aurora-r2 until §8 holds.

## 8. Handoff conditions: when Avinay's pipeline switches to the refresh

The registry `config/samples/round2_training_samples.yaml` keeps `active_training_domain: aurora-r2` until all of these
hold:
1. Lists from complete samples, written by `tools/make_refresh_list.py`, then hashed, manifested and committed. NC Δ and
   BNB are complete today. νe CC is needed by Xuyang/Matteo and by SP nue only if SP nue is retrained.
2. The Round-2 vertex tree is confirmed (split-move or snap).
3. The νμ chain is frozen by Xuyang/Matteo, and `numu_score` (plus the L1 scores if changed) is recomputed on the
   refreshed training CAFs. This gates SP numu and SP other.
4. The νe L1 models are still fixed. This gates SP ncpi0.
5. The beam-off odd-run half is on the training side, with `approved_by` filled. This gates SP other.
6. Round-2 production uses this configuration (toolkit `c935e30d`, bundle `51588842…`, config md5s above). Otherwise the
   SP models are retrained on the matching refresh.

Then `tools/train_dev_model.py`'s successor reads the new tables unchanged. Only the registry entry, the list hashes and
`wct_version_stamp: "0.38.0"` (with its commit beside it) change.
