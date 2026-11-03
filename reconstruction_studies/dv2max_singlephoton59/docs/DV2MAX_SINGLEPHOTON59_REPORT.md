# DV2-MAX neutrino vertexer × single-photon 59-event test

Date: 2026-11-02 · Work area W = `single_photon/development/dv2max_singlephoton59_20261102/` · Owner: Avinay Bhat
Nothing in this study is committed or pushed. Snehadri's branch, our frozen SP tree
(`fix2_vertex_shower_onehop_20261005/wct-dev`, HEAD cd7e7b39, `git status` clean) and the frozen Fix2-v2 library
(md5 9cff76d0d81a4b6c45a88908e78e73e4, re-checked after the runs) are unchanged. No existing 59-event output was
overwritten. No BDT, selection threshold, A5 setting, dQ/dx guard or DV2 setting was changed, and nothing was retrained.
No backgrounds were run.

**What was tested.** WireCell/wire-cell-toolkit PR #543 (`dsnehadri:dv2-max-vertexer`) is the
*DV2-MAX neutrino vertexer*, a learned **main-neutrino-vertex placement method**. It is **not** a clustering change and is
not "DL clustering". We asked one question: if *only* the main-ν-vertex determination is replaced by DV2-MAX, keeping
all validated single-photon (SP) changes, does NC-Δ radiative become more reconstructable?

Truth is used only in the analysis scripts, as a diagnostic. It is never used in reconstruction.

> **Correction carried from `final_history_dl_status`:** the old uBooNE SCN DL-vertex inference never ran in our SBND
> builds; it was compiled out because `HAVE_PYTHON_INC` was not defined. No earlier study measured a DL vertex
> "acceptance" on this sample. This test is the first run of any learned vertexer on it.

> **The PR's numbers are not ours.** The PR's validation figures (<1 cm: 0.581 / 0.661 / 0.801 / 0.847) come from
> Snehadri's own sample and environment. Every number below was measured on our 59-event NC-Δ sample.

---------------------------------------------------------------------------------------------------------------------

## 1. Software

| | value |
|---|---|
| DV2 PR branch | `dsnehadri/dv2-max-vertexer` (= `origin/pr543`) |
| DV2 head | **feb3ddeb6fea35f42e13c416d65520f22b5b0cbf** |
| DV2 base / master | merge-base **b7bd2a1a5ca829c178706675223b3961024cc276** (master 2026-10-07; = origin/master at fetch) |
| PR commits present | 43660339 DV2-MAX engine · eb7636ae Python inference + r7_cloud bundle · b87ae37d `vertex_method` · feb3ddeb SBND default `dv2_split_move` — **all 4, nothing else** |
| SP reference head | `feature/sbnd-singlephoton-onehop-20261005` **cd7e7b39** (parent 8dddba5b; base 51b5a1fc) |
| integration strategy | PR head + semantic port of our SP algorithm and provenance changes. Uncommitted git worktree `W/source/wct-int`, detached at feb3ddeb. Diff = `W/source/PATCH.diff` (554 lines, md5 4472ebe0…) |
| ported from SP branch | `NeutrinoTaggerSinglePhoton.cxx` (Fix2-v2 net diff, applied verbatim at +5 lines); `MultiAlgBlobClustering.{h,cxx}`, `clustering_switch_scope.cxx`, `doctest_matching_bundle_provenance.cxx` (251ff143 provenance, verbatim); 8 lines of `cfg/.../sbnd/clus.jsonnet` (`stamp_matching_bundle_id`, placed by hand because the `pr()` signature moved) |
| diagnostic-only code ported | **NO**. The cd7e7b39 `fix2_diag` BFS probe was not ported, and gate G3 confirms 0 `fix2_diag:` strings in the library |
| semantic conflict in main-vertex code | **none**. PR #543 and our SP branch touch disjoint files (`docs/INTEGRATION_MAP.md` §2) |
| build environment | same as the frozen runs: slf7.sif + larsoft v10_14_02 + sbndcode v10_14_02_04. WCT built with `--with-python-*` against larsoft python v3_9_15. larwirecell rebuilt from the same source against the new WCT headers, because master adds `Facade::Grouping::m_dead_region`; no ABI patching |
| Python stack | torch 2.5.1+cpu, numpy 2.0.2, scipy 1.13.1, lightgbm 4.6.0 (lib rebuilt in-container), cp39. Snehadri uses torch 2.9.1 / numpy 2.5.3 / scipy 1.18.1 / lightgbm 4.7.0, which need glibc ≥ 2.28; the container has 2.17 |
| runtime edits (both arms) | `LD_PRELOAD` larsoft libpython3.9; larsoft `libtorch/v2_1_1b/lib` removed from `LD_LIBRARY_PATH`, because it shadowed the torch wheel. The lar job never loads it (LD_DEBUG) |
| library | `libWireCellClus.so` md5 927a1834af1e44dfef3467dcc6e53976 (full hashes in `tables/build_provenance.csv`) |

**Python / DV2 hard gate (§13): PASS.**
- **Build gates (job 200904), 6/6:** G1 `HAVE_PYTHON_INC`, G2 `WCPPyUtil::DV2_Vertex` exported, G3 DV2 + Fix2-v2 + provenance strings present and the library links WCPPyUtil, G4 lightgbm loads under glibc 2.17, G5 pure-Python bundle inference, G6 C++ bridge returns a point.
- **Single-event smoke (job 200905, ARM D, evt 18), `DV2_STRICT=1`:**
  - 1 hook call and 1 prediction; placement INFO line present; 0 fallback or exception lines.
  - LD_DEBUG shows only the torch-wheel libraries initialised.
  - The PR's `configure()` raises if a `dv2_*` method is requested without Python support, so DV2 cannot have been silently compiled out.
  - DV2 exceptions are *caught* by the existing DL-step `catch` and become a WARN plus the traditional fallback. The strict gate is therefore "0 `DL vertex failed`, 0 `no DV2-MAX prediction`, 1 placement line, 1 hook record per candidate". It passed on all 57 candidate events (§4).
- **Repeatability:** the evt 18 DV2 prediction is bit-identical between the smoke run and the main run: point (-103.41218, -27.18644, 170.16609), raw score 0.0453502.

## 2. Arms and control

| arm | `vertex_method` | other DV2 keys | `dl_weights` | `main_vertex_swap_apply` |
|---|---|---|---|---|
| **O** | `original` | — | `''` | absent → false |
| **D** | `dv2_split_move` | `dv2_bundle` = PR r7_cloud | `''` | absent → false |

**Configuration (`docs/config_semantic_diff.txt`).**
- Compiled config O vs D differs in exactly `TCN.vertex_method`, `TCN.dv2_bundle` and the provenance string. **Config diff clean: YES.**
- Frozen vs O differs in `dl_weights` (deliberate, see below) and `UbooneTaggerOutputVisitor.nu_particle_links=true`. The latter is master output booking only.
- There are 0 `main_vertex_swap*` keys anywhere.

**Why `dl_weights=''` in both arms.** The frozen build had SCN compiled out. The new build embeds Python, so a non-empty `dl_weights` would run the uBooNE SCN net in ARM O, which the reference never did. With `''` the dual-chain OFF pass is also skipped. The owner's code states that pass cannot change any output when there are no weights.

**ARM O control vs frozen Fix2-v2, all 59 events (`tables/diagnostic_control_original.csv`): 57 MATCH, 2 MATCH_EXCEPT_KNOWN_NOISE, 0 DIFFERENT.**
- Every event matches on candidate, final main cluster, ν vertex (max shift 0.0000 cm), accessibility class, `shw_sp_filled`, n20, n20br1, BDT evaluability and proton category.
- BDT scores match except in evts 46 and 47. There, `shw_sp_proton_{length,dqdx,energy}_2` and the numu/nue scores (46: |Δ|≤0.008; 47: nue |Δ|=0.085) move by exactly the branches that the **same-binary** determinism rerun recorded (`main_vertex_swap_ab59_20261014/.../determinism_ab59_vs_offrerun`).
- T_tagger value differences in 26 events are permutation-only. The schema additions are the 4 T_tagger branches (`match_isFC`, `act_n_seg*`, `act_in_enu`) and 6 T_kine columns, as predicted from the master drift.
- ARM O cutflow is **identical** to Fix2-v2: 59/57/38/38/15/8/5/5/4, selected 0005, 0015, 0020, 0036.
- **Unexplained control differences: none.** Software-stack drift (50 master commits, embedded Python, rebuilt larwirecell, `LD_LIBRARY_PATH` edit) has no measurable effect on any quantity used here. Every O→D difference below is therefore a **VERTEX_METHOD EFFECT**, plus run-to-run noise at the 46/47 level.
- DV2's own numerics under torch 2.5.1 vs Snehadri's torch 2.9.1 could not be compared, because we have no outputs from her environment for these events. That is recorded as DV2-internal software drift, not measured.

## 3. Execution

- **Sentinels** (job 200906; evts 18, 0, 2, 58, 20; both arms; `DV2_STRICT=1`): all lar exit 0, and O matched frozen 5/5. These runs are part of the `main` runset.
- **Full runs:** jobs 200907, 200908 and 200909, each 18 events × {O, D}, sequential, with no `/lus/flare` bind.
  - 200907 and 200908 received **SIGTERM** (Exit_status 143) at 19:18 UTC, the instant co-resident job 200909 on the same node (sophia-gpu-09) finished. This was an infrastructure kill, not a lar failure.
  - The partial D-53 and D-55 outputs were moved, not deleted, to `W/scratch/killed_sigterm_200907_200908/`.
  - Job 200928 reran the 4 unfinished runs (D:53, D:55, O:56, D:56).
- **Final: 59/59 lar exit 0 in both arms.**
- **Outputs:** `W/runs/main/arm{O,D}/wirecell/evt_NNNN/`. Logs: `W/logs/main/arm{O,D}/`. Analysis log: `W/logs/analysis_full59.log`.

## 4. DV2 placement (ARM D, 57 neutrino candidates; evts 39 and 52 have no candidate in either arm)

| quantity | value |
|---|---|
| DV2 calls / predictions (hook log) | **57 / 57** |
| placement = nearest PR-graph vertex ("snap") | **53** |
| placement = segment split at an interior fit point ("split") | **4** (evts 3, 25, 34, 38) |
| `split_move`: vertex moved onto the DV2 point | **43** (41 snap + 2 split); 14 already at the point. Median move 0.275 cm; 56/57 moves < 1 cm, all < 3 cm |
| main cluster switched by DV2 (full `swap_main_cluster`) | **24** |
| fallback: `no DV2-MAX prediction` | **0** |
| failures: `DL vertex failed` / Python error / placement declined | **0 / 0 / 0** |
| traditional main-vertex-swap (`mvsa`) lines in ARM D | **0**. With DV2 accepted, `determine_overall_main_vertex` (`examine_main_vertices`, `check_switch_main_cluster`, `compare_main_vertices_global`) is not executed |
| DV2 P(<1 cm) output | median 0.440 |

**Vertex truth distance** (57 candidates). "True" = T_tagger ν vertex vs the generator vertex. "SCE" = vs the generator vertex shifted by the local SCE offset, the frame the reconstruction lives in.

| | ARM O | ARM D |
|---|---|---|
| median, true frame | 28.27 cm | **2.67 cm** |
| median, SCE frame | 28.20 cm | **1.93 cm** |
| < 1 cm (true / SCE) | 12 / 16 | **19 / 26** |
| < 3 cm (true) | 15 | 29 |
| > 20 cm (true) | 37 | 23 |
| final main cluster contains the true vertex (of 40 events where the true vertex lies in a reco cluster) | 11 | **30** (swap-ON diagnostic: 18) |

The DV2 point itself (before placement) has a median of 3.72 cm (true) / 2.17 cm (SCE) and is < 1 cm in 19 / 26 events.

## 5. Shower accessibility and BDT evaluability

| | ARM O (= Fix2-v2) | ARM D | Δ |
|---|---|---|---|
| `shw_sp_filled` | 38 | **41** | **+3** |
| all 4 BDTs evaluable | 38 | 41 | +3 |
| DIRECT / ONE_HOP / INACCESSIBLE / no candidate | 33 / 5 / 19 / 2 | 36 / 5 / 16 / 2 | |

The +3 is a net of **10 gains and 7 losses** (`tables/dv2_access_changes.csv`):
- **Gains (O → D):** 0, 2, 21, 31, 32, 37, 42, 54, 56, 58. Each one moves the main cluster or vertex onto the true-vertex cluster, at 0.28–2.5 cm from truth.
- **Losses (new under DV2):** 7, 11, 12, 14, 18, 46, 57. None of them was selected in ARM O.

| evt | O | D | mechanism of the loss (read from the D log; truth is diagnostic) |
|---|---|---|---|
| 0007 | DIRECT, cl1, 1.66 cm | INACCESSIBLE, cl1, 2.00 cm (SCE 0.32) | same cluster; DV2 moves the vertex 1.0 cm, and **A5 then retypes the 115 MeV photon shower → pdg 211** (start segment 2.7 cm, growth 0.41; in O the same shower had growth 1.24, verdict 0) |
| 0018 | DIRECT, cl2, 42 cm | INACCESSIBLE, cl12, 88.7 cm | **DV2 prediction miss**, then **A5 → 211** (see §8) |
| 0011 | DIRECT, cl2 (photon cluster), 25 cm | INACCESSIBLE, cl9 = true-vertex cluster, **0.28 cm** | vertex now correct; the photon (98 % of its charge in cl2) is not attached to it; the only >20 MeV object within one hop is a 195 MeV pdg-13 track |
| 0014 | ONE_HOP, cl1 (photon cluster), 59 cm | INACCESSIBLE, cl15 = true-vertex cluster, **1.48 cm** | vertex now correct; the photon (94 % in cl1) is not attached; leading object is a 53 MeV pdg-13 |
| 0057 | DIRECT, cl4, 53 cm | INACCESSIBLE, cl7 = true-vertex cluster, **0.49 cm** | vertex now correct; nothing >20 MeV within one hop. No primary-photon charge was found in any PR cluster, so O's three "showers" at 53 cm were not the photon |
| 0012 | ONE_HOP, cl1, 20.5 cm | INACCESSIBLE, cl6, 16.4 cm | true vertex lies in no reco cluster (nearest 15.7 cm); DV2 picks cl6; leading object 307 MeV pdg-13 |
| 0046 | DIRECT, cl3, 45.6 cm | INACCESSIBLE, cl3, 42.6 cm | same (wrong) cluster, different graph vertex; leading object 101 MeV typed muon by the long-muon cleanup |

The losses fall into three groups:
- **Earlier accessibility came from a vertex wrongly placed on the photon side; the correct vertex does not reach the detached photon** (evts 11, 14, 57). This is a shower-to-vertex association limit that DV2 exposes, not a vertexing error.
- **Port-only A5 retype** after the DV2 placement (evts 7, 18).
- **DV2 picks a wrong vertex, or a different wrong vertex, and the leading object is track-typed** (evts 12, 46).

A5 is strongly vertex-dependent. It retypes a shower in the selected candidate in 8 events under O (0, 9, 11, 21, 22, 38, 46, 51) and in 10 under D (1, 3, 7, 8, 9, 18, 25, 34, 40, 55). Only evt 9 is in both lists.

## 6. Pre-FV cutflow (counts, not efficiency; `tables/cutflow_original_vs_dv2.csv`)

| step | ARM O | ARM D | D gained vs O | D lost vs O | frozen Fix2-v2 | swap-ON (diag, not adopted) |
|---|---|---|---|---|---|---|
| total | 59 | 59 | | | 59 | 59 |
| neutrino candidate | 57 | 57 | | | 57 | 57 |
| >20 MeV shower (`shw_sp_n_20mev_showers>0`) | 38 | **41** | 0 2 21 31 32 37 42 54 56 58 | 7 11 12 14 18 46 57 | 38 | 45 |
| all 4 BDTs evaluable | 38 | **41** | (same) | (same) | 38 | 45 |
| numu BDT > 0.4 | 15 | **29** | 0 2 4 16 21 22 24 29 31 32 37 38 41 42 45 47 48 51 56 58 | 1 3 12 18 34 36 | 15 | 22 |
| other BDT > 0.2 | 8 | **19** | 0 2 4 16 21 22 23 29 31 32 37 38 42 45 56 | 1 18 20 36 | 8 | 14 |
| ncpi0 BDT > −0.05 | 5 | **10** | 2 22 32 35 42 45 56 | 20 36 | 5 | 9 |
| nue BDT > −1.0 | 5 | **10** | (same) | 20 36 | 5 | 9 |
| exactly one shower (`n_20br1 == 1`) | **4** | **10** | 2 22 32 35 42 45 49 56 | 20 36 | 4 | 8 |

0p/Np at the last step: O 2/2, D 4/6.

- **ARM O selected:** 0005, 0015, 0020, 0036.
- **ARM D selected:** 0002, 0005, 0015, 0022, 0032, 0035, 0042, 0045, 0049, 0056.
- **Gained (8):** 0002, 0022, 0032, 0035, 0042, 0045, 0049, 0056. **Lost (2):** 0020, 0036.

How to read the gains and losses:
- **Vertex-driven gains (4):** 2, 32, 42, 56 are graph-disconnected recoveries, with the vertex < 1 cm (SCE) from truth.
- **BDT-response gains on events already accessible in O (4):**
  - 45: numu 0.05 → 0.95, `n_20br1` 2 → 1; vertex 3.7 cm, unchanged.
  - 49: other 0.32 → 0.96, `n_20br1` 2 → 1; vertex 4.9 cm, unchanged.
  - **22**: all four BDTs flip to pass with the vertex **88.5 cm** from truth.
  - **35**: ncpi0 −0.42 → +0.28 with the vertex 18.9 cm from truth.
- **Losses:** both events stay accessible, so these are BDT-response changes.
  - 20: vertex improves 5.3 → 1.3 cm, but other BDT 0.28 → 0.04.
  - 36: vertex unchanged at 36.5 cm, DIRECT → ONE_HOP, numu 0.46 → −0.09.
- The numu-BDT step goes from 15 to 29. DV2 changes the topology seen by the MicroBooNE BDTs even when the vertex barely moves, because the DV2 path skips kink/junction snap, `improve_vertex`, the graph audit and the conn3 stitch, then moves and refits. On signal only, a higher pass rate **cannot** be interpreted without the corresponding background response.

## 7. The seven old graph-disconnected events (`tables/graph7_dv2_outcome.csv`)

| evt | O / frozen | swap-ON (diag) | **DV2** | DV2 truth dist (true / SCE) | DV2 main = true-vertex cluster | shw_sp_filled | BDT eval | selected |
|---|---|---|---|---|---|---|---|---|
| 0002 | INACCESSIBLE, cl1 | DIRECT, cl4 | **DIRECT**, cl4 | 0.63 / 0.49 | yes (cl4) | 1 | yes | **yes** |
| 0031 | INACCESSIBLE, cl1 | DIRECT, cl17 | **DIRECT**, cl17 | 0.52 / 0.60 | yes (cl17) | 1 | yes | no |
| 0032 | INACCESSIBLE, cl1 | DIRECT, cl25 | **DIRECT**, cl25 | 0.70 / 0.29 | yes (cl25) | 1 | yes | **yes** |
| 0037 | INACCESSIBLE, cl1 | DIRECT, cl2 | **DIRECT**, cl2 | 0.82 / 0.35 | yes (cl2) | 1 | yes | no |
| 0042 | INACCESSIBLE, cl1 | DIRECT, cl7 | **DIRECT**, cl7 | 1.78 / 0.26 | yes (cl7) | 1 | yes | **yes** |
| 0056 | INACCESSIBLE, cl1 | DIRECT, cl6 | **DIRECT**, cl6 | 0.28 / 0.35 | yes (cl6) | 1 | yes | **yes** |
| 0058 | INACCESSIBLE, cl2 | DIRECT, cl45 | **DIRECT**, cl45 | 0.57 / 0.29 | yes (cl45) | 1 | yes | no |

**DV2 resolves 7/7.** All seven are accessible DIRECT, with the final main cluster equal to the true-vertex cluster, all 4 BDTs evaluable, and 4/7 selected (swap-ON diagnostic: 3/7). Fix2 one-hop is not needed for any of them.

DV2 chooses **the same cluster as the fully applied traditional swap in all 7 events**. The mechanism is the same: the DL tail calls `swap_main_cluster` with `main_cluster` passed by reference, so the swap is fully applied rather than half applied. DV2 gets there without `main_vertex_swap_apply` and without executing `compare_main_vertices_global`.

## 8. evt0018 and evt0000 (the two bad traditional swaps)

| | **evt0018** (50/0/725) | **evt0000** (30/0/160) |
|---|---|---|
| truth (true / SCE est.) | (-101.59, 11.52, 249.97) / (-100.79, 11.50, 249.96); true-vertex cluster **cl13** (proton); photon charge 59 % cl2, 19 % cl14, 13 % cl12 | (-115.81, -0.73, 373.63) / (-115.17, -0.73, 373.45); true-vertex cluster **cl40** (proton); photon 66 % cl6, 23 % cl4 |
| original (ARM O = frozen) vertex | (-96.54, -12.13, 215.61), cl2, 42.0 cm; DIRECT; not selected (fails ncpi0, −0.38) | (-199.92, 16.40, 330.14), cl4, 96.2 cm; INACCESSIBLE (A5 retypes shower id0, 3.8 cm → 211) |
| traditional swap-ON (diag) | → cl12 (-103.42, -27.73, 169.84), 89.2 cm; INACCESSIBLE (A5 id2 → 211) | → cl6 (-199.58, 16.15, 330.33), 95.8 cm; DIRECT on the photon cluster (wrong vertex) |
| DV2 prediction | (-103.41, -27.19, 170.17), P(<1 cm) 0.400; **88.7 cm** from truth | (-115.35, -0.46, 373.67), P(<1 cm) 0.354; **0.52 cm** (SCE 0.39) |
| DV2 final vertex | graph vertex 0.000 cm from the point (no move): (-103.41, -27.19, 170.17) | cl40 graph vertex 0.897 cm away, moved onto the point: (-115.35, -0.46, 373.67) |
| truth distance (true / SCE) | 88.71 / 88.72 cm | 0.53 / 0.39 cm |
| main cluster | cl2 → **cl12** (≠ true cl13; cl13 had a PR graph, so its vertices were in DV2's candidate cloud) | cl4 → **cl40** = true-vertex cluster |
| photon accessibility | **INACCESSIBLE** (Fix2 fallback added 1 neighbour, no usable object) | **ONE_HOP** (Fix2 neighbour, 219.5 MeV pdg 11) |
| A5 outcome | **retype**: shower id14, start 4.8 cm, growth 0.37, bragg 3.69 → pdg 211; the 201 MeV leading object becomes 211 | **no A5 retype** in ARM D |
| BDT evaluable | no | yes (numu 0.959, other 0.408, ncpi0 −0.408, nue −0.090) |
| selected | no (O: no) | no; fails ncpi0 > −0.05 (O: no) |
| **does DV2 avoid the bad traditional swap?** | **NO.** DV2 independently picks the same cl12 vertex (0.6 cm from the swap-ON vertex), and the same A5 retype follows. This is a DV2 ranking miss, not a placement or fallback effect | **YES.** DV2 avoids the photon-cluster swap (cl6), places the vertex at the true vertex, and A5 no longer fires; the photon is reached by Fix2 one-hop |

## 9. Fix2 under DV2 (`tables/fix2_under_dv2.csv`; Fix2 code unchanged in both arms)

The five original Fix2-v2 recoveries:

| evt | O | D | role |
|---|---|---|---|
| 0012 | ONE_HOP | INACCESSIBLE (cl6, 16 cm, leading object pdg 13) | **NO_LONGER_SUFFICIENT** |
| 0014 | ONE_HOP | INACCESSIBLE (correct vertex cl15, photon not attached) | **NO_LONGER_SUFFICIENT** |
| 0016 | ONE_HOP | DIRECT (same cl1; vertex 24.5 → 66.7 cm) | **MADE_REDUNDANT** (vertex not better) |
| 0020 | ONE_HOP | DIRECT (same cl3; vertex 5.3 → 1.3 cm) | **MADE_REDUNDANT**; no longer selected (other BDT) |
| 0026 | ONE_HOP | ONE_HOP (3 neighbours) | **STILL_NEEDED** |

**New Fix2 one-hop recoveries under DV2:** evts **0, 54** (O INACCESSIBLE → D ONE_HOP, both at the true vertex, 0.53 and 0.35 cm) and **36, 41** (O DIRECT → D ONE_HOP).

ARM D has 5 ONE_HOP events (0, 26, 36, 41, 54), the same count as O. Without the one-hop fallback those 5 would have no usable >20 MeV object (`direct_has_usable=false`).

**Conclusion: Fix2 still matters under DV2.** It is redundant for 2 of its original 5 and insufficient for 2 more, but it is what makes the DV2 recoveries of evt0000 and evt0054 accessible. **Do not remove Fix2.**

## 10. Remaining-19 under DV2 (`tables/remaining19_under_dv2.csv`)

| class | events | n |
|---|---|---|
| RESOLVED_DIRECT | 2, 21, 31, 32, 37, 42, 56, 58 | 8 |
| RESOLVED_ONE_HOP | 0, 54 | 2 |
| STILL_INACCESSIBLE_VERTEX | 9 (17.5 cm), 13 (41 cm), 27 (35 cm), 55 (23 cm) wrong vertex; 50 vertex correct (0.28 cm) but nothing >20 MeV within one hop | 5 |
| STILL_TRACK_DOMINATED | 44 (vertex 0.31 cm; leading object 90 MeV pdg 13) | 1 |
| PID_DOWNSTREAM | — | 0 |
| NOT_RECONSTRUCTABLE | 6, 10, 30 (signal photon never deposits in the TPC) | 3 |
| OTHER | — | 0 |

**Resolved by DV2: 10/19:**
- all 7 GRAPH_DISCONNECTED;
- 3 of the 5 WRONG_PDG (0, 21, 54). In O, events 0 and 21 had A5 retypes on wrong-cluster vertices.

Of the 10, 4 are selected (2, 32, 42, 56). None of the 7 BELOW_20MEV events is resolved.

## 11. Answers

**Did DV2 introduce new losses?** Yes: 7 accessibility losses (§5) and 2 selection losses (20, 36, both through BDT response). Three of the accessibility losses (11, 14, 57) put the vertex at the truth but lose the detached photon. Two (7, 18) go through the port-only A5 retype.

**Does DV2 reduce the need to modify `compare_main_vertices_global`?** In the DV2 path, yes. When DV2 accepts a point (57/57 here), the traditional comparator, `examine_main_vertices`, `check_switch_main_cluster` and the `main_vertex_swap_apply`-gated swap are **not executed**. The DL tail applies `swap_main_cluster` fully, which resolves all 7 half-applied-swap (graph-disconnected) events without editing the comparator.

DV2 does **not** make the comparator correct; it bypasses it. The comparator is still the `original` path and the fallback path for any no-prediction event. evt0018 also shows DV2 can choose the same wrong cluster the comparator chose. So the owner questions on the traditional path stay open; they are just not on the DV2 critical path.

**Optional DV2-only arm (§27):** not run. The questions above are answered unambiguously by O vs D, and Fix2's role is read directly from the ONE_HOP classification.

**Verdict.** **PARTLY** what we were waiting for.

What it delivers:
- it does the main-cluster/vertex job the traditional chain could not do cleanly: 7/7 graph-disconnected events resolved, evt0000 fixed;
- the main cluster contains the true vertex in 30/40 events instead of 11/40;
- median vertex distance falls from 28 cm to 2.7 cm;
- all of this with no fallbacks, no exceptions and a clean control.

Where it falls short:
- it repeats the evt0018 mistake;
- it causes 7 new accessibility losses, from detached photons at a correct vertex and from A5;
- about half of its selection gain (22, 35, 45, 49) is a change in MicroBooNE-BDT response rather than a vertex fix.

The strongest allowed conclusion holds: **promising enough to move to background validation.**

**Not done now:**
- `main_vertex_swap_apply` is not changed; it stays separate until owner review;
- Fix2 is not removed;
- the BDTs are not tuned;
- nothing about DV2 is tuned.

**Next recommended step.** Run the same O/D pair (same build, configs and `DV2_STRICT=1`, same scripts) on an Avinay-owned background reco1 sample, starting with BNB νμ CC and NC π0. Compare the identical pre-FV cutflow, especially the numu-BDT and other-BDT pass rates that jumped on signal. In parallel, prepare owner questions (not sent) on:
- the evt0018 DV2 ranking miss (cl12 ranked over cl13);
- the A5 retype's sensitivity to vertex placement (7, 18);
- attaching detached photons to a correct vertex (11, 14, 57).

## 12. Deliverables

- **Docs:** `docs/DV2MAX_SINGLEPHOTON59_REPORT.md` (this file), `docs/INTEGRATION_MAP.md`, `docs/config_semantic_diff.txt`.
- **Source:** `source/PATCH.diff`.
- **Tables:** `tables/` holds `single_photon_patch_map`, `build_provenance`, `diagnostic_control_original`, `dv2_event_diagnostics`, `event59_original_vs_dv2`, `cutflow_original_vs_dv2`, `graph7_dv2_outcome`, `fix2_under_dv2`, `remaining19_under_dv2`, plus `dv2_access_changes` (gain/loss mechanisms) and `summary.json`.
- **Analysis code:** `scripts/analysis/run_dv2.py`. It reuses `derive()`, `diff_tree()`, the scorer and `CUTS_PRE_FV` verbatim (exec of the source) from the swap-A/B and Fix2 studies; cluster truth comes from the remaining-19 forensics building blocks.
- **Mirrored** (files only, no git) to `single_photon/repos/sbnd-wirecell-single-photon/reconstruction_studies/dv2max_singlephoton59/`, with `MANIFEST.sha256`.
