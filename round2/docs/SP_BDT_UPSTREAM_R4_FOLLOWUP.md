# Upstream releases r4: follow-up (common scorer, fixture, membership, statistics, final-domain readiness)

Date: 2026-11-28. Branch `round2/sp-bdt-wcl1116-upstream-r4-integration-20261128`. This follows
[`SP_BDT_UPSTREAM_R4_INTEGRATION_AUDIT.md`](SP_BDT_UPSTREAM_R4_INTEGRATION_AUDIT.md).

**Everything here is DEVELOPMENT ONLY.**
- No official FermiGrid evaluation event, beam-on event, even-run beam-off, Run-3 BNB or open-data event was read.
- No model, threshold or vertex mode was chosen or frozen. No large production was launched.
- Every SP model trained here is `DEV_DO_NOT_DEPLOY`.

**Decisions recorded (Avinay, 2026-11-28):**
1. **Domain D** is the current WCL1116 development domain: `numu_round3af` + `nue_round4_ruleA_v2` main, from
   `Ningclover/sbnd-wirecell-bdt` @ `0f13988db44423a227789e151b0a374e25771abd`.
   - Domain A and all its models, thresholds and results are immutable.
   - SP nue keeps its current development model in D.
   - All four SP models are retrained once the final reconstruction domain exists.
2. **Patched toolkit stamp.** `numu-sim-dqdx-scale-0.38.0-1-gccb19cf` is approved for **development validation only**. It is
   recorded exactly (§1.2); the final campaign refuses it.
3. **Common numerical reference.** The toolkit-equivalent implementation is the common reference of Aurora and EAF (§2).

## 0. Summary

1. **Repository.**
   - `c10ef2d` and `a66c25d` pass the hygiene review: no credentials, no e-mail addresses, no heavy outputs, largest file 85 KB.
   - The internal paths they contain are of a kind already public on this repository.
   - Code checkpoint `8178610`; results and documents follow in the next commit. The branch is pushed only with Avinay's
     credentials (§7).
2. **Common scorer.** `round2/upstream_chain_bundle` (`wc_upstream_chain` 1.0.0; numpy and pandas only).
   - It is **bit-identical** to the validated Aurora chain module on every candidate of the four development samples, both trees:
     20 released outputs, the flag copy, the MC no-scale diagnostic, and the shipped closure against the stored scores.
   - It equals the patched in-chain test on the 18 fixture units.
   - Bundle fingerprint `97661441…`.
   - **One bug was found and fixed** during this check: the simulation factor must follow the νμ weights.
3. **Inventory.**
   - Aurora's 61 checks and EAF's 57 are the same 57 files; Aurora counted 4 chain XMLs twice.
   - Common canonical fingerprint `1d48baed…`; EAF's table gives the same value.
4. **Fixture.**
   - `upstream_r4_dev_fixture_v1`: 3,542 candidates, both trees, MC plus the restricted beam-off part, 18 in-chain CAF pairs,
     development SP models; 334 MB.
   - `check-fixture` gives ok on all 8 cases.
   - Packaged for FNAL with sha256. Avinay runs the commands in §4.1.
5. **Membership.** Manifest of all 593,723 candidates (per tree), 924,444 events and 91,274 files.
   - Xuyang's pools are reproduced from his own code, to within his 25 PARTIAL files.
   - **Every simulated SP holdout row inside an upstream pool was fitted by the released models.** The odd-subrun holdout is not
     upstream-independent.
   - Found: 134 groups of generator-identical BNB events (a GEN seed collision under the `random` policy).
   - Found: the DL vertex was trained on the same BNB / νe CC production units; its per-event folds must be requested from
     Snehadri.
6. **Science**, no tuning:
   - The presentation gain (27.1 % → 44.0 %) is robust: **+15.7 points on the holdout at lower background**.
   - The upstream releases do **not** improve the joint SP selection:
     - matched per-model points: D is −0.9 points on the holdout (−1.9 on nested validation);
     - matched holdout background: D is −0.6 to −1.3 points in both trees, driven by the νμ release;
     - the nested-validation front gain, 48.0 % → 48.7 %, is a selection diagnostic: +0.4 points, 95 % interval [−3.3, +3.9];
     - the earlier "≤ 0.78 %" column used a 0.778 % cap.
7. **Final-domain readiness.**
   - Haiwang has no production newer than WCLocal2026Nov16, boundary code is planned only, and the releases are not booked.
   - The contract now accepts R1 / R2, with fingerprints, toolkit provenance and machine-checked simulation-only evidence. The
     log census closes the "simulation job silently at k = 1" gap. The development stamp is refused.
   - The template carries no assumed value.


## 1. Repository and integration checkpoint

### 1.1 Review of `c10ef2d` and `a66c25d`

| check | result |
|---|---|
| files | 47 changed. The largest committed file is 85 KB (`validation/upstream_r4/offline_rescoring_summary.json`); the rest are code, docs and compact JSON/CSV. No parquet, ROOT, booster or weight file |
| credentials | none: no PAT, token, key or kerberos material; `git diff` scanned for `ghp_`, `github_pat`, `token`, `passw`, `secret`, private keys, `krb`, `x509`, `.pem` |
| e-mail addresses | none. The commit object of the patched toolkit (outside git) carries Xuyang's e-mail; it is not copied into the repository |
| internal paths | `chain_test_units.tsv` and several JSONs name Aurora paths, including `yuhw` and `xning` project folders. The same class of paths is already public on this repository (50 files of the pushed full-development branch name `yuhw`, 22 name `xning`). No new kind of exposure |
| heavy outputs | none committed. Tables, overlays, boosters (`RETRAINED_*`, `DEV_DO_NOT_DEPLOY_*`), CAFs and the toolkit build stay in `$SP_WORK/upstream_r4_20261128/` |
| labels | the development boosters are named `RETRAINED_<model>_<mode>_<domain>.json` in the work area. In the fixture they are copied as `DEV_DO_NOT_DEPLOY_*` |

The repository is public (the unauthenticated GitHub API answers 200), so the fixture and the membership tables are never committed;
only their manifests and summaries are.

### 1.2 Patched-toolkit stamp: development-only approval record

`sp_retrain/provenance.py: UPSTREAM_R4_DEV_TOOLKIT` and `validation/upstream_r4/patched_toolkit_dev_approval.json`.

| item | value |
|---|---|
| observed stamp | `numu-sim-dqdx-scale-0.38.0-1-gccb19cf`: `wc.Trun.wct_version` of every patched-build CAF of PBS 9137793 |
| full commit | `ccb19cfbdc7f35958f1817391ab924e6c9da156c` (tree `ae25293c…`), branch `numu-sim-dqdx-scale` |
| base commit | `c935e30d44a09bf208f6de2c2968171b01efd63d` (tag 0.38.0, WCLocal2026Nov16) |
| toolkit patch | `releases/numu_round3af/wirecell/patches/wct-0.38.0-numu_sim_dqdx_scale.patch`, sha256 `3162b22f…846f`. `git patch-id` `58c8bb03…` equals the patch-id of `c935e30d..ccb19cf`. The diff sha256 is `f8a2bd2a…26b7`. 5 files: 3 jsonnet, 2 C++ |
| workflow patch | `step2-numu_sim_dqdx_scale.patch`, sha256 `bc83b90b…a0a`, patch-id `47131847…`, which equals `swp-wclocal` `d05cf47..eaaa02f` |
| build | `$SP_WORK/upstream_r4_20261128/chain/opt-0.38.0-numu-sim` on x4418c4s6b0n0, started 2026-11-28T03:30:07Z, `waf -k` rc 0. The configured version is the stamp above. `bin/wire-cell` `e536fc4a…`, `libWireCellRoot.so` `2aa4f7a0…`, `libWireCellUtil.so` `3bd316f2…` |
| policy | exact string AND purpose `development_validation` (`upstream_r4_dev_stamp_ok`). It is **not** in `WCL1116_STAMPS`. `final_domain_campaign.py check` refuses it in a final campaign. No pattern matching. Tests: `tests/test_upstream_chain_bundle.py` |

## 2. Common Aurora/EAF scoring implementation: `wc_upstream_chain` 1.0.0

Path: `round2/upstream_chain_bundle/`: [README](../upstream_chain_bundle/README.md), [CONVENTIONS](../upstream_chain_bundle/CONVENTIONS.md),
`tests/`.

The bundle is a standalone package (numpy, pandas; no ROOT, xgboost or Aurora framework). It gives the 20 values a toolkit 0.38.0
step-2 job stores, for any weight set. It is built from the validated `sp_retrain/upstream_chain.py`:
- the TMVA evaluator is byte-identical (tested);
- the feature specifications are carried as data files, byte-identical to `config/upstream/` (tested).

Interface:
- `UpstreamChain(weights_path).score(cands, objs, kind)`;
- `verify_release`, `chain_fingerprints`, `identify_route`, `bundle_fingerprint`;
- `identity.translate` / `join_exact`;
- `sp.replace_upstream_inputs`;
- CLI `verify | fingerprint | bundle-fingerprint | score | check-fixture`.

### 2.1 Equivalence

`tools/check_upstream_chain_bundle.py` gives `validation/upstream_r4/bundle_equivalence/<tree>_<sample>.json` (PBS 9138971, after
the fix below). Every candidate is compared exactly as float32:
- the 20 released outputs and the flag copy, against the Aurora module's rescore tables (which equal the in-chain test);
- the MC no-scale diagnostic;
- the shipped final models on stored level-1 values, against both the rescore tables and the stored CAF scores.

| sample | candidates per tree | split-move | snap | flag copy switched off (split / snap) | placeholders | `br_filled != 1` |
|---|---:|---|---|---:|---:|---:|
| NC Δ | 24,031 | BIT_IDENTICAL | BIT_IDENTICAL | 151 / 154 | 49 | 17,721 / 17,889 |
| BNB | 301,830 | BIT_IDENTICAL | BIT_IDENTICAL | 1,639 / 1,816 | 5,421 | 281,416 / 281,728 |
| νe CC | 265,367 | BIT_IDENTICAL | BIT_IDENTICAL | 2,127 / 2,222 | 427 | 74,422 / 76,363 |
| beam-off (data, k = 1) | 2,495 | BIT_IDENTICAL | BIT_IDENTICAL | 0 / 0 | 968 | 2,369 / 2,381 |

In total, 1,187,446 candidate rows over both trees are identical in every block. The bundle's TMVA evaluator is byte-identical to
`sp_retrain/tmva_grad.py`.

In-chain and fixture evidence:
- The fixture check is ok on all 8 cases (§4).
- The patched chain's stored values equal the fixture expectation on 128 / 128 candidates per tree, for all 20 outputs.
- The bundle's own synthetic test suite passes without data: 11 tests, plus 1 optional fixture test, which passed on Aurora.


### 2.2 What is documented (CONVENTIONS.md)

Each item asked for has a section:
- model resolution in `WIRECELL_PATH` order, with checksums and fingerprints;
- ordered feature lists (74 / 258 / level-1 `lists + scalars`; forests refuse a different order);
- float32 inputs and cuts, the right-if-`x >= cut` rule, double sums of float32 leaves, `EvaluateMVA = 2/(1+exp(−2s))−1`;
- the log10-odds score with saturation;
- max / min pooling and the 18 empty constants;
- the only chain gate (`pio_2`) and the absence of `br_filled` / `cosmict_flag_1` gates;
- NaN → −999 per object and −16.2556 per final model, −15 when `br_filled != 1`, and the input protections;
- placeholders (scored by the chain, dropped by the SP preselection);
- the simulation-only ×1.071 copies and the flag copy, with `kind` mandatory;
- raw versus corrected features (`RAW_MUST_STAY_RAW`);
- the candidate key (`cand = nu_index`; `file_id` rules) and translation;
- dependencies;
- a determinism caveat for other numpy/libm builds, answered by the fixture check.

**Fix made during this follow-up.** The first version applied k = 1.071 whenever `kind='mc'`, which also hit the **shipped** νμ
weights. The shipped closure then failed on 7,112 of 24,031 NC Δ candidates; the released values were unaffected. The correction
is part of the `numu_round3af` model, so k now follows the resolved νμ files:
- release fingerprint: 1.071;
- shipped fingerprint: 1.0;
- anything else: explicit `sim_dqdx_scale` required.

The full-table equivalence (§2.1) was rerun after the fix.

### 2.3 Inventory reconciliation: 57 vs 61

| count | what |
|---|---|
| **57** | the canonical inventory: unique repository paths named by the two manifests. 49 νe (15 level-1 JSON, 2 level-2 JSON, 16 main + 16 nogap chain XMLs) + 8 νμ (3 level-1 JSON, 1 level-2 JSON, 4 chain XMLs) |
| 61 | the Aurora audit: the 57, plus the 4 νμ chain XMLs listed again in `numu_round3af/wirecell/chain_weights.json` (checked twice; same files) |
| 57 | the EAF audit: the same 57 paths and hashes (`release_file_hashes.csv`) |
| 42 | distinct contents: the 15 nogap level-1 XMLs equal the main ones byte for byte |
| 8 | auxiliary files: README, 2 manifests, `correction.json`, 2 `chain_weights.json`, 2 patches |

- **Canonical fingerprint** (sha256 of the sorted `releases/<path> <sha256>` lines): **`1d48baed0b3d386b3848c20829099b736f42d6020456f4ea60dd4dbbf60c1f9f`**.
  EAF's committed table yields the same value (`data/release_inventory.json: eaf_cross_check`).
- **Auxiliary fingerprint:** `7757db60…`.
- **Chain fingerprints:**

  | | numu | νe level-1 | νe level-1 + final |
  |---|---|---|---|
  | release | `0b8485a8…` | `36ec972f…` | `3526cdea…` |
  | shipped | `595a9963…` | `17a8e17e…` | `655fb390…` |

### 2.4 Where EAF's current layer differs

See `EAF_HANDOFF_UPSTREAM_CHAIN_BUNDLE.md` §2.
- xgboost JSON instead of TMVA XML: split crossings.
- NaN handling.
- No νe values for `br_filled == 0`: 17,289 of the 27,127 SP ncpi0 rows are such candidates, and they carry the empty constants
  in training.
- Placeholders.

## 3. Training / evaluation membership

Tool: `tools/build_training_membership_manifest.py`. Outputs are in `$SP_WORK/upstream_r4_20261128/membership/` (not in git;
transferred with the fixture). Summaries with the sha256 of every table: `validation/upstream_r4/training_membership_{dv2_split_move,dv2_snap}.json`.
No official FermiGrid event was read; EAF compares with approved bookkeeping metadata.

| table | rows | content |
|---|---:|---|
| `membership_candidates_<mode>.parquet` (one per tree) | 593,723 | identity `(sample, file_id, run, subrun, event, cand)`; `sp_preselected`; `sp_split` (outer holdout); `sp_nested_role` (fit / nval / test); `in_<model>`, `cls_<model>` per SP model; `xn_split_v11`; `up_numu_role`, `up_nue_role` (`fit` / `early_stop` / `ineligible`), `up_numu_l1_pool`, `up_nue_bnb_filtered_spill_dropped`; `gen_duplicate_group`; `dlvtx_training_status` |
| `membership_events.parquet` | 924,444 | every MC event (truth ∪ candidates) and every beam-off event with a candidate: roles, generator production, instance, group, log location, seeds |
| `membership_files.parquet` | 91,274 | every CAF: path, size, events, candidates, stored stamp |

### 3.1 Upstream training roles (Xuyang, repository 0f13988d)

The pools are reconstructed from his training code, applied with his own `spec/spec_v1.py` functions (`in_fv`, `pool_mask`,
`filtered_spills`, `split_v11`) on our tables:

| model | pool | fitted (`fit`) | early stopping (`early_stop`) | his logs |
|---|---|---:|---:|---:|
| `numu_round3af` (`training/numu/train_numu_l2.py`) | BNB, NC Δ NC-partner rows (`partner_kind == 'neutrino'`, `iou_n > 0`, `m_ccnc == 1`), beam-off; placeholder 0, label readable, reco vertex in the νe FV | 209,060 | 23,373 | 209,294 / 23,395 |
| `nue_round4_ruleA_v2` (`training/round2/train_l2.py`) | νe CC, BNB, NC Δ, beam-off; placeholder 0, label readable, `br_filled == 1`, reco vertex in FV; BNB spills holding a νe CC vertex in the filter volume dropped (1,605 spills) | 153,310 | 17,185 | 153,347 / 17,191 |

Notes on the reconstruction:
- **νμ.** The difference is exactly the 256 νμ-pool rows of the 14 PARTIAL BNB files that he included and our tables exclude.
- **νe.** The reconstruction is within 2 rows once his 45 PARTIAL-file pool rows are added.
- **Which rows were fitted.** The released models are the early-stopped fits on the `train` rows only. There is no 100 %
  retrain (`training/numu/freeze_numu_l2.py`; νe chain_v2 f0.5). `early_stop` rows influenced only the number of trees.
- **Small models.** The νμ small models also require `cosmict_flag_1 == 0` and rule A on objects (`up_numu_l1_pool`).
- **Snap tree.** In the snap manifest the same rule is applied to snap candidates. He trained on split-move only.

**Our odd-subrun outer holdout is NOT an upstream-independent holdout.**
- Simulated rows: the holdout (`subrun` odd) and his early-stopping slice (`subrun % 10 == 0`) are disjoint by construction. So
  **every simulated holdout row inside an upstream pool was fitted by the released models.**
- Preselected holdout rows fitted upstream (split-move):

  | sample | νμ | νe |
  |---|---|---|
  | NC Δ | 6,218 of 8,159 | 2,482 |
  | BNB | 23,086 of 32,778 | 6,796 |
  | νe CC | — | 75,923 of 110,366 |
  | beam-off (holdout = run % 4 == 1) | 101 fitted, 25 early-stop, 98 outside, of 224 | — |

- The remaining holdout rows are outside the pools: CC-partner NC Δ rows, rows outside the FV, `br_filled == 0`, and the
  νe CC sample for νμ.
- Only the official evaluation samples are independent of the upstream fits.

### 3.2 SP roles

- `sp_split` is the outer holdout: MC odd subrun; beam-off `run % 4 == 1`.
- `sp_nested_role` is nested_v1 within the training side: sha256 of `(sample, run, subrun)`, 20 % nested validation.
- `in_<model>` marks the exact rows of each SP model's development dataset: stamp-checked files, preselection, classes, finite
  inputs. Rows in split-move:

  | model | NC Δ | BNB | νe CC | beam-off |
  |---|---:|---:|---:|---:|
  | numu | 15,295 | 40,533 | – | – |
  | other | 15,592 | 17,110 | – | 509 |
  | ncpi0 | 15,255 | 11,872 | – | – |
  | nue | 14,985 | 3,849 | 212,287 | – |

### 3.3 Generator ancestry and seeds

- **Identity.** (run, subrun, event) is unique within and across the three MC samples. The run ranges are disjoint:
  - BNB: 2100001–2110757 and 5000001–5000813;
  - νe CC: 6700001–6734897;
  - NC Δ: 7000005–7030038.
- **Generator job.** `inst = (run − first_run − 1)·100 + subrun`.
  - BNB: restartable shards 01–03 and capacity batches 01–09 (`first_run` per production); one GEN subrun per instance, 10
    events.
  - NC Δ and νe CC (configL): `group = inst // 100` and `inst // 51` respectively; 125 events per GEN subrun.
- **Original generator identifiers.** None exists beyond art (run, subrun, event). `genie_evtrec_idx` and `GENIEEntry` are
  local counters.
- **Seeds, configL.** NuRandomService `linearMapping`, seed = 10·(offset + job) + k. The GEN job is the instance; the later
  stages use the group. Offsets: NC Δ 75M / 87M / 88M / 89M, νe 0 / 4M / 5M / 6M. The events table carries the computed seeds.
  They match the logged generator seed exactly on 3 + 3 sampled subruns, read from the group tarballs.
- **Seeds, BNB.** Default `random` policy. Seeds exist only in the per-subrun logs; the events table gives each log location
  (50/50 sampled found).
- **Generator-identical BNB events: 134 groups** (268 events, 125 candidates, 59 subrun pairs). Each group has the same event
  number and identical neutrino lists. Every group shares the GEN `generator` engine seed, while 97 share the master seed as
  well.
  - Straddling: 60 groups cross our outer holdout, 69 cross some SP role, and 27 cross Xuyang's dev/train slice.
  - 0.04 % of BNB events: negligible for the results, but it is a leak path and a production-policy finding. A uniform random
    seed would give about 2 such pairs in about 62,600 subruns.
  - Any further BNB production should use an explicit seed policy, like configL.
  - NC Δ and νe CC have none.
- **DL vertex** (DV2-MAX `aurora_space`, both trees). Per its bundle README it was trained on aurora-r2 BNB and intrinsic νe CC:
  fold 1 has 477,997 training events, and fold 0 is a 15,000-event hold-out. Those are the same production units as our BNB and
  νe CC samples. NC Δ and beam-off are not listed. The per-event fold table is on Eagle (not mounted on Aurora). The manifest
  records the unit-level fact in `dlvtx_training_status`.
- **Beam-off training half.** 558 files and 80 runs, all odd; 26,418 events; file sha256 in
  `manifests/wcl1116_dev_v1/beamoff_train_staging.tsv.gz`. It is Xuyang's 572-pair list minus 14 hold-out files; 109 files are
  `r8`. EAF must evaluate beam-off with even-run files only.

### 3.4 What must be requested (drafted in `ROUND2_MINIMAL_COLLABORATOR_QUESTIONS.md`, not sent)

- **Snehadri:** the per-event DL-vertex fold table and fold rule, and the ranker's training calls (or read access to the Eagle
  area).
- **Xuyang:** confirm that the releases are the train-split fits; whether the 25 PARTIAL files and the 109 `r8` beam-off files
  belong in training.
- **Haiwang:** the meaning of the PARTIAL units and of the `48` stamp in Xuyang's tables; the νe list count.


## 4. Development fixture and transfer

Tool: `tools/build_upstream_fixture.py`. Fixture `upstream_r4_dev_fixture_v1` is in `$SP_WORK/upstream_r4_20261128/fixtures/`,
not in git. Summary: `validation/upstream_r4/fixture_v1_summary.json`. The authorization text is in the manifest.

| part | content |
|---|---|
| `mc/cases/<sample>/<tree>/` | NC Δ (451), BNB (555), νe CC (488 / 487) candidates per tree, both trees. Each case has inputs (`cands`, 18 `objs_<model>`), `expected_upstream` (stored, shipped closure, chain-equivalent released, MC no-scale, the release's standalone xgboost values, `diag_*`, tags), `sp_rows`, `sp_features_A`, `sp_features_D`, `sp_predictions` |
| `beamoff_restricted/cases/…` | beam-off training half: 281 / 274 candidates. Same files; restricted handling |
| `mc/caf/` | the 18 in-chain units (7 NC Δ, 4 BNB, 7 νe CC): production CAF and patched-chain CAF with sha256; `identity_map.parquet` (tree, entry, position, `nu_index`); `expected_released_chain_scores.parquet` (the values the patched chain stored; 128 candidates per tree) |
| `mc/models/` | 16 development SP boosters, `DEV_DO_NOT_DEPLOY_<model>_<tree>_dev{A,D}.json`, and the ordered SP feature lists |

Totals: 3,542 candidates, 2,124 SP-preselected rows, 252 files, 334 MB.

**Edge cases present** (tag totals over cases):

| tag | candidates |
|---|---:|
| `br_filled == 0` | 2,227 |
| some νe list empty | 1,187 |
| `pio_2` objects with the gate passing | 1,101 |
| placeholder | 348 |
| internal muon flag switched off | 167 |
| scale moves `numu_score` by > 0.1 | 1,433 |
| split crossing, νμ final (top 15 per case) | 120 |
| split crossing, νe final | 118 |
| split crossing, νe level-1 | 120 |
| multi-candidate events | 138 |
| NaN final νe input (−16.2556 in the chain) | 1 |
| in-chain candidates | 256 |

**Edge cases absent from every development sample:**
- NaN objects;
- the `mip_*` caps and the NaN protections;
- a `pio_2` gate blocking existing objects;
- NaN final νμ inputs;
- νμ level-1 split crossings above 1e-6.

The bundle's synthetic tests cover each of these.

**Checks on Aurora.**
- `python -m wc_upstream_chain check-fixture` gives **ok on all 8 cases**: released values and shipped closure, both trees, MC and
  beam-off.
- The values the patched chain stored in the 18 test CAFs equal the fixture's expected values on **128 / 128 candidates per tree,
  all 20 outputs**.
- The identity-map keys equal the fixture keys. `nu_index` equals the vector position everywhere in these units.

### 4.1 Transfer procedure (ALCF → FNAL; Avinay authenticates)

Packaged in `/lus/flare/projects/neutrinoGPU/abhat/sbnd/sp-bdt-round2-work-20261117/upstream_r4_20261128/transfer/`:

| file | bytes | sha256 | handling |
|---|---:|---|---|
| `upstream_r4_dev_fixture_v1_mc.tar` | 500,285,440 | `0c7f6fe185419fbbb1b1ad1559e9bcaf3110f0ee4f1190f8bdba2fda092a7d72` | simulation; FNAL |
| `upstream_r4_dev_fixture_v1_beamoff_restricted.tar` | 2,641,920 | `dfe679be897468e2ae19b08412e750f5c47e02a31d389026ddade3134da5d3c4` | beam-off training half: restricted, FNAL only, never public, never evaluation |
| `upstream_r4_membership_v1.tar` | 47,308,800 | `673b97baa2c4542e7fbbc0752f94e0500ed8e915bdc6ee2a1c6ab03fadd5a796` | bookkeeping (identities and roles) |
| `SHA256SUMS.transfer` | | | the three lines above |

Avinay runs the following from an SBND GPVM, where `/exp/sbnd/data` is mounted and visible to EAF. Each `scp` asks for the ALCF
MobilePASS+ passcode. Nothing here uses or stores a credential on Aurora.

```bash
DEST=/exp/sbnd/data/users/abhat/single_photon_ncdelta/aurora_fixtures
mkdir -p $DEST && cd $DEST
SRC=abhat@aurora.alcf.anl.gov:/lus/flare/projects/neutrinoGPU/abhat/sbnd/sp-bdt-round2-work-20261117/upstream_r4_20261128/transfer
scp "$SRC/SHA256SUMS.transfer" "$SRC/upstream_r4_dev_fixture_v1_mc.tar" "$SRC/upstream_r4_membership_v1.tar" .
scp "$SRC/upstream_r4_dev_fixture_v1_beamoff_restricted.tar" .      # only if the beam-off part may go to this area
sha256sum -c --ignore-missing SHA256SUMS.transfer
for t in upstream_r4_*.tar; do tar -xf "$t"; done
(cd upstream_r4_dev_fixture_v1 && sha256sum -c --ignore-missing --quiet SHA256SUMS && echo FIXTURE_FILES_OK)
chmod -R go-rwx upstream_r4_dev_fixture_v1/beamoff_restricted 2>/dev/null || true
```

- **Alternative:** a Globus transfer from the ALCF Flare collection to a personal FNAL endpoint, with the same checksum steps.
- **Do not copy any of this into a Git repository.** On EAF, register the fixture name in `configs/upstream_release.yaml:
  fixtures` with the authorization text above.


## 5. Scientific comparison (no additional tuning)

**Inputs.** Only the development models already trained by the domain study: inherited XMLs, the domain-A models (`FIT_BASELINE`),
and the `RETRAINED_*` boosters per domain. No hyperparameter, model or threshold was tuned or chosen.

**Tools.**
- `tools/upstream_joint_comparison.py` gives the per-row scores of every domain on nested validation and on the development
  holdout. It reproduces all 12 domain-study reference points bit for bit.
- `tools/upstream_joint_holdout_matched.py` gives the matched-background points on the holdout.

**Outputs:** `validation/upstream_r4/upstream_joint_comparison_{dv2_split_move,dv2_snap}.json` and
`upstream_joint_holdout_matched_{…}.json`. The per-row scores and full grids are in `$SP_WORK/upstream_r4_20261128/joint/`.

**Statistics.**
- Paired pass/fail tables with exact McNemar tests on the discordant rows.
- 95 % intervals from a 2,000-replicate Poisson bootstrap clustered on (sample, run, subrun), the unit of every split.
- A **selection-aware bootstrap**: the grid maximum is re-taken in every replicate, with out-of-bag optimism.
- Clopper-Pearson intervals for small counts.

Rows, split-move:

| | NC Δ signal | BNB background | νe CC `nueCCBkg` | beam-off |
|---|---:|---:|---:|---:|
| nested validation | 1,494 | 6,424 | 21,079 | 20 |
| holdout | 7,507 | 31,464 | 106,187 | 224 |

Snap is alike (1,484 / 6,477 and 7,437 / 31,620).

**Which numbers are optimization diagnostics.**

| comparison | thresholds chosen on | status |
|---|---|---|
| **P1 presentation** (inherited XMLs at historical cuts vs development models at point A) | nested validation, per model, at legacy-equal **signal** efficiency; no joint optimization | mild selection; the holdout column is free of it |
| **P2 matched per-model** (each model retrained in its domain, at the domain-A per-model signal efficiencies) | nested validation, per model; no joint optimization | mild selection; the holdout column is free of it |
| **P3 optimized front** (maximum of 6,561 threshold vectors at BNB ≤ cap) | nested validation: **the maximum is taken on the rows it is reported on** | **optimization diagnostic**; the holdout column evaluates the same vectors, but their background then differs between domains |
| **H holdout-matched front** (maximum of the same grid at holdout BNB ≤ cap, in every domain) | the holdout itself, symmetrically | optimization diagnostic on 5× the rows; the fairest *relative* comparison available in development |

None of these is an unbiased estimate of final performance. That comes only from frozen models on the independent evaluation
samples. **The holdout is not upstream-independent** (§3.1).

### 5.1 The three comparisons the presentation numbers come from (split-move; counts are pass / rows)

| | nested validation: NC Δ / BNB | holdout: NC Δ / BNB |
|---|---|---|
| **P1** A, inherited XMLs, historical cuts | 405/1494 = **27.1 %** / 48/6424 = 0.75 % | 2036/7507 = 27.1 % / 314/31464 = 1.00 % |
| **P1** A, development models at point A | 657/1494 = **44.0 %** / 50/6424 = 0.78 % | 3217/7507 = 42.9 % / 262/31464 = 0.83 % |
| **P2** D, retrained, domain-A per-model efficiencies | 629/1494 = **42.1 %** / 45/6424 = 0.70 % | 3152/7507 = 42.0 % / 262/31464 = 0.83 % |
| **P3** A, front at BNB ≤ 0.778 % (the audit's column) | 717/1494 = **48.0 %** / 49/6424 = 0.763 % | 3515/7507 = 46.8 % / 243/31464 = 0.77 % |
| **P3** D, front at BNB ≤ 0.778 % | 728/1494 = **48.7 %** / 49/6424 = 0.763 % | 3614/7507 = 48.1 % / 280/31464 = 0.89 % |
| **P3** A, front at BNB ≤ 0.78 % (literal) | 720/1494 = 48.2 % / 50/6424 = 0.778 % | 3530/7507 = 47.0 % / 253/31464 = 0.80 % |
| **P3** A / D, front at BNB ≤ 0.70 % | 679 = 45.4 % / 708 = 47.4 %, at 44 / 43 BNB rows | 3267 = 43.5 % / 3476 = 46.3 %, at 219 / 257 BNB rows |

**Note on the 48.0 % in the earlier audit.** Its "≤ 0.78 %" column used a cap of 0.778 %. That excludes the vectors at exactly
50/6424 = 0.7783 %, domain A's own matched acceptance. At the literal 0.78 % cap, A is 48.2 % and D is 48.7 %. One BNB row,
0.016 %, moves the cap across that boundary, which shows how fragile a front maximum is.

**Paired comparisons, A vs D (difference D − A, 95 % clustered interval, McNemar p):**

| | nested-validation NC Δ | nested-validation BNB | holdout NC Δ | holdout BNB |
|---|---|---|---|---|
| P1 (development vs inherited, A) | +16.9 [+14.1, +19.7] pts, p = 2e-29 | +0.03 % (34 vs 32 discordant) | **+15.7 [+14.5, +17.0] pts, p = 7e-124** | **−0.17 [−0.29, −0.04] %** |
| P2 (D vs A, matched per model) | −1.9 [−3.2, −0.6] pts, p = 0.007 (64 lost, 36 gained) | −0.08 % (17 lost, 12 gained) | **−0.9 [−1.5, −0.2] pts, p = 0.01** (343 lost, 278 gained) | 0.00 (262 vs 262) |
| P3 ≤ 0.778 % | +0.7 [−0.8, +2.3] pts, p = 0.39 | 0 | +1.3 [+0.6, +2.1] pts | **+0.12 [+0.05, +0.19] %** (243 → 280 rows) |
| P3 ≤ 0.70 % | +1.9 [+0.5, +3.4] pts, p = 0.016 | −0.02 % | +2.8 [+2.1, +3.5] pts | **+0.12 [+0.06, +0.19] %** (219 → 257 rows) |

**Selection-aware bootstrap of the front maximum** (nested validation, the maximum re-taken in every replicate):

| cap | D − A, mean | 95 % interval | P(D ≤ A) | optimism per domain (selected vs out of bag) |
|---|---|---|---|---|
| ≤ 0.778 % | +0.4 pts | [−3.3, +3.9] | 0.42 | about 0.5 pts |
| ≤ 0.70 % | +0.9 pts | [−3.0, +4.6] | 0.32 | about 0.5 pts |

### 5.2 Matched background on the holdout (H)

The grid maximum is taken on the holdout, in every domain. Counts are pass / 7,507 NC Δ (split-move) or 7,437 (snap).

| tree | cap | A | B (νμ release) | C (νe release) | D (both) | paired D − A |
|---|---|---|---|---|---|---|
| split-move | ≤ 0.78 % | 3515 = 46.8 % (243 BNB) | 3443 = 45.9 % (242) | 3504 = 46.7 % (243) | 3418 = **45.5 %** (244) | **−1.3 [−2.0, −0.6] pts, p = 4e-4**; BNB +0.00 % |
| split-move | ≤ 0.70 % | 3369 = 44.9 % (218) | 3251 = 43.3 % (215) | 3419 = 45.5 % (220) | 3327 = **44.3 %** (220) | −0.6 [−1.3, +0.2] pts, p = 0.16 |
| snap | ≤ 0.78 % | 3446 = 46.3 % (244) | 3370 = 45.3 % (240) | 3451 = 46.4 % (244) | 3376 = **45.4 %** (239) | **−0.9 [−1.6, −0.3] pts, p = 0.008** |
| snap | ≤ 0.70 % | 3315 = 44.6 % (221) | 3232 = 43.5 % (218) | 3270 = 44.0 % (218) | 3236 = **43.5 %** (221) | **−1.1 [−1.9, −0.3] pts, p = 0.01** |

By release:
- **B, the νμ release, is −1.0 to −1.6 points** against A at matched background. All four cells are significant (p ≤ 0.014).
- **C, the νe release, is −0.6 to +0.7 points**, consistent with zero.
- D follows B.

### 5.3 Interpretation (no tuning; nothing chosen)

- **The presentation comparison is robust.** The development models gain about 16 NC Δ points over the inherited XMLs at equal or
  lower BNB acceptance. This holds on the holdout and in both trees.
- **The upstream releases do not improve the joint SP selection on WCL1116.**
  - At matched per-model points (P2), D is 0.9 points (holdout) to 1.9 points (nested validation) lower at the same background.
    Snap: −2.3 points on the holdout.
  - At matched holdout background (H), D is 0.6–1.3 points lower in both trees.
  - The nested-validation front gain, 48.0 % → 48.7 %, is not significant (selection-aware P(D ≤ A) = 0.42). On the holdout it
    turns into higher background at the nested-validation vectors, and into a ~1-point loss at matched background.
- **The loss sits in the νμ release** (domain B), which carries the simulation-only dQ/dx correction. The νe release is neutral.
- **The upstream overlap would favour D, not A.** On the holdout, D's upstream scores are in-sample for 80 % of the NC Δ signal
  rows (`up_numu_role == 'fit'`). Even so, D is not better: for the fitted and the outside rows alike, D's efficiency is lower
  (split-move ≤ 0.78 %: fitted 47.8 % vs 49.0 %, outside 36.2 % vs 38.1 %).
- **Not estimated:** the seed-to-seed spread of the retrained SP models. Each domain has one training with the frozen seed, so
  part of a 1-point difference can be training noise. Running repeated seeds would be extra training, so it was not done.
- **Consequences, for Avinay to decide.**
  - Domain D stays the approved development domain, because it is what a production with the releases would store.
  - The development evidence does not support expecting a gain from the releases.
  - The final choice of upstream models is the collaboration's, on their own merits (CC νμ / νe selection). The SP models are
    retrained in whatever domain is booked.

### 5.4 Topology, migrations, background composition (holdout, matched background, split-move)

| | A ≤ 0.78 % | D ≤ 0.78 % | A ≤ 0.70 % | D ≤ 0.70 % |
|---|---|---|---|---|
| 0p | 1709/3623 = 47.2 % | 1684 = 46.5 % | 1651 = 45.6 % | 1644 = 45.4 % |
| 1p | 1665/3356 = 49.6 % | 1595 = 47.5 % | 1567 = 46.7 % | 1550 = 46.2 % |
| ≥ 2p | 141/528 = 26.7 % | 139 = 26.3 % | 151 = 28.6 % | 133 = 25.2 % |

Snap ≤ 0.78 %: A 46.1 / 49.2 / 30.1 %, D 44.9 / 48.5 / 28.7 %.

Signal migrations, A → D at ≤ 0.78 %:

| topology | gained | lost |
|---|---:|---:|
| 0p | 162 | 187 |
| 1p | 127 | 197 |
| ≥ 2p | 28 | 30 |

The net loss is concentrated in 1p.

Background composition of the selected BNB rows (A → D at ≤ 0.78 %, 243 → 244 rows):

| class | A | D |
|---|---:|---:|
| NC π⁰ | 130 | 117 |
| out-of-FV | 51 | 55 |
| NC | 22 | 22 |
| νμ CC π⁰ | 18 | 17 |
| cosmic partner | 11 | 11 |
| νμ CC | 6 | 7 |
| νe CC | 5 | 15 |

D's ≤ 0.78 % holdout point has **no SP nue cut** (`nue` level none). This shows up in the dedicated νe CC sample: `nueCCBkg`
acceptance is 4.3 % against 1.3 % for A. At ≤ 0.70 %: A 0.98 %, D 0.73 %.

**By Xuyang's role.**
- On the holdout, every simulated row is in his `train` slice (§3.1).
- On nested validation, the per-model AUC table of the audit (§8.4) stands. In the joint selection, the gap between his
  `dev`-slice and `train`-slice rows is no larger in D than in A.
- All splits by `xn_split_v11`, `up_numu_role` and `up_nue_role` are in the JSONs (`by_*` blocks).

### 5.5 Limited-statistics samples

| | nested validation | holdout (matched, ≤ 0.78 %) |
|---|---|---|
| beam-off (EXT) training half | 0/20 pass in every domain and point | A 1/224, D 1/224 (split-move); snap A 1/225, D 0/225. Clopper-Pearson 68 %: [0.08, 1.0] % for 1/224 |
| νe CC `nueCCBkg` (dedicated sample) | A 0.93 %, D 0.93 % at the matched per-model points | A 1.30 %, D 4.29 % (D's vector without an SP nue cut); at ≤ 0.70 % A 0.98 %, D 0.73 % |

The beam-off counts cannot distinguish the domains. The νe CC acceptance depends on whether the vector includes an SP nue cut,
which is a property of the chosen point, not of the domain.

**SP nue** is not retrained for domain D. Its current development model is kept (its inputs do not change). All four models are
retrained in the final reconstruction domain.


## 6. Final-domain readiness

### 6.1 Haiwang's production and boundary: read-only recheck, 2026-11-28 13:00Z

Haiwang's local clones were last fetched on 11-16 (toolkit), 11-18 (ai-helper) and 11-20 (catalogue); later remote work would
not show.

| item | status | evidence |
|---|---|---|
| production newer than WCLocal2026Nov16 | **none**. Since 11-20 there are only HDF5 conversions of WCL1116 CAFs and blob dumps (not reconstruction). The production build is unchanged (`wct-0.38.0` clean, `0.38.0`) | `yuhw/production-prep/{sim-h5-wcl1116, h5-0.6}` (PBS 9110541, 9122899/9123716) |
| WCL1116 νe CC | complete: 61,238 OK, 11 PARTIAL, 3 FAIL of 61,252. Lists: BNB 11,888, NC Δ 17,604, νe CC 61,249 | `WCLocal2026Nov16/p5-nuecc-tally.txt`, `lists/` |
| effective boundary | **plan only**: "no WCT code was changed". To be implemented with PolyFiducial / CompositeFiducial and a default-off knob in `sbnd/clus.jsonnet`. No SBND code in any branch | `wire-cell-toolkit-ai-helper/issues/50-sbnd-effective-boundary/plan.md` (11-17) |
| Xuyang's releases booked? | **no**. No `numu_round3af`, `nue_round4`, `NUMU_SIM_DQDX_SCALE` in his workflow, cfg, run scripts or install | `swp-wclocal@d05cf47` (clean) |
| beam-off in the catalogue | `wcl1116-fg-beamoff-train` available (572 pairs: 570 OK, 2 PARTIAL); `wcl1116-fg-ncdr` available. Nothing after 11-18 | catalogue `b4b9bba` |
| jobs | none running or queued (user yuhw) | `qstat`, 13:01Z |

So the §10 blockers of the audit stand: no boundary production, no vertex-mode freeze, no beam-off half in a final domain, no
booked upstream models. Domain D on WCL1116 remains a development domain.

### 6.2 Contract and workflow

Updated: [`SP_BDT_FINAL_DOMAIN_RERUN_CONTRACT.md`](SP_BDT_FINAL_DOMAIN_RERUN_CONTRACT.md) §1a,
`config/campaigns/round2_final_reco_candidate.yaml` and `tools/final_domain_campaign.py`.
- **R1, preferred**: the production books the collaboration-selected models in the chain.
- **R2**: a validated score-only overlay on shipped-weight CAFs, accepted only with a CLOSED closure record of *that* production.
- Both routes require:
  - the release commit and the canonical inventory fingerprint;
  - all three chain fingerprints;
  - toolkit provenance (exact stamps with evidence; patch hashes for R1);
  - vertex mode and tree;
  - the boundary profile and its sha256;
  - `sim_dqdx_scale` with machine-checked **simulation-only evidence**.
- The development-only stamp is refused.
- `plan` writes the route's upstream step into step 1.
- The template carries no assumed value (tested).

The simulation-only evidence for R1 is `tools/verify_sim_dqdx_logs.py`. It counts the toolkit's own log line in every step-2
log against the unit's reality. On the in-chain test it gives 36/36 simulation logs scaled and 0/2 data logs, and it flags the
`noscale` arm.

The census is required because the enforcement chain has one gate only (contract §1a):
- the workflow passes k whenever the variable is set;
- the toolkit jsonnet forces 1.0 unless `reality == 'sim'`;
- the C++ does not re-check;
- the reverse gap is real: some drivers and the FermiGrid `submit.sh` never forward the variable, so a simulation job could
  silently stay at k = 1.

### 6.3 Readiness checklist (final SP training)

| # | item | state |
|---|---|---|
| 1 | effective-boundary production (Haiwang) | NOT STARTED (plan only) |
| 2 | vertex mode frozen (collaboration) | open; development favours split-move |
| 3 | beam-off training half reprocessed in the final domain, staged and verified, exception re-approved | open (the WCL1116 half is verified, 558/558) |
| 4 | upstream models selected and route chosen (R1 / R2) | open; the releases are recommended, D is the development domain |
| 5 | toolkit build with exact, approved stamp(s) for the final production | open; the dev stamp is refused by design |
| 6 | simulation-only correction evidence (log census over every training-sample job, R1; overlay record, R2) | tool ready, tested |
| 7 | upstream fingerprints in the campaign spec | function ready; values not filled |
| 8 | common scorer at EAF (bundle adopted, fixture `ok`) | handed over; EAF to run |
| 9 | membership facts outside Aurora: DL-vertex folds (Snehadri); Xuyang's train-split intent, PARTIAL and r8 files | drafted questions, not sent |
| 10 | SP training of all four models in the final domain, then validation-only thresholds, then freeze, then EAF evaluation | after 1–5 |


## 7. Not done, and limits

- **No beam-off in-chain check.** There is no permitted beam-off step-1 output on Aurora. The data path is covered offline
  (k forced to 1) and by the data-gate test.
- **DL-vertex training membership per event is unknown** until Snehadri provides the fold table. The manifest records the
  unit-level fact (`dlvtx_training_status`).
- **Snap-tree upstream roles.** Xuyang trained on split-move candidates only. In the snap-tree manifest, the pool rule is applied
  to snap candidates. Event-level overlap, which is what matters for independence, is the same in both trees.
- **The statistics in §5 are development diagnostics.** No number there is an unbiased final-performance estimate. The only
  unbiased estimate will come from the frozen models on the independent evaluation samples.
- **Push requires Avinay's credentials.** A credential problem in this shell stops the push; nothing is worked around.


## 8. Files

| file | content |
|---|---|
| [`upstream_chain_bundle/`](../upstream_chain_bundle/) | the common scorer `wc_upstream_chain` 1.0.0 ([README](../upstream_chain_bundle/README.md), [CONVENTIONS](../upstream_chain_bundle/CONVENTIONS.md), tests) |
| [`EAF_HANDOFF_UPSTREAM_CHAIN_BUNDLE.md`](EAF_HANDOFF_UPSTREAM_CHAIN_BUNDLE.md) | handoff to EAF Claude |
| [`SP_BDT_FINAL_DOMAIN_RERUN_CONTRACT.md`](SP_BDT_FINAL_DOMAIN_RERUN_CONTRACT.md) | §1a: routes R1 / R2, enforcement chain |
| `validation/upstream_r4/bundle_equivalence/*.json` | bundle == Aurora chain module, 8 samples × trees |
| `validation/upstream_r4/training_membership_{dv2_split_move,dv2_snap}.json` | membership summaries, with the sha256 of the tables |
| `validation/upstream_r4/fixture_v1_summary.json` | fixture contents, checks, transfer checksums |
| `validation/upstream_r4/upstream_joint_comparison_{…}.json`, `upstream_joint_holdout_matched_{…}.json` | §5 statistics |
| `validation/upstream_r4/patched_toolkit_dev_approval.json` | the development-only stamp record |
| `validation/upstream_r4/sim_dqdx_log_census_chain_test.json` | simulation-only log census of the in-chain test |
| tools | `build_upstream_chain_bundle_data.py`, `check_upstream_chain_bundle.py`, `build_upstream_fixture.py`, `build_training_membership_manifest.py`, `upstream_joint_comparison.py`, `upstream_joint_holdout_matched.py`, `verify_sim_dqdx_logs.py`; `final_domain_campaign.py` (R1 / R2) |
| work area, not in git | `$SP_WORK/upstream_r4_20261128/{fixtures, transfer, membership, joint, bundle_check}`; logs of PBS 9138954 and 9138971 |

