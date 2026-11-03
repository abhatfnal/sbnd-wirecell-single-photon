# DV2-MAX neutrino vertexer × single-photon: background validation (ν_μ CC and NC π0)

Date: 2026-11-03 · Work area W = `single_photon/development/dv2max_background_validation_20261102/` · Owner: Avinay Bhat
Signal-study area (read-only here): SIGW = `single_photon/development/dv2max_singlephoton59_20261102/`.

Nothing in this study is committed or pushed. Nothing was tuned, retrained or rebuilt. The DV2 model and bundle,
`vertex_method` definitions, Fix2-v2, A5, the dQ/dx guards, MIP constants, z-prior, BDT weights and thresholds,
`main_vertex_swap_apply`, the shower and proton thresholds, the selection logic, the software and Python stack and the
runtime environment are **byte-identical to the signal study** (§1). No signal output was modified. No new MC was generated
and `/lus/flare` was not bound. No final SBND FV (and no MicroBooNE FV) is applied anywhere: every count is the
**pre-FV** study cutflow.

**What was tested.** The signal study (`SIGW/docs/DV2MAX_SINGLEPHOTON59_REPORT.md`) found that replacing only the
main-ν-vertex determination by DV2-MAX (`vertex_method = dv2_split_move`, PR #543) raised the NC-Δ radiative pre-FV
selection from 4/59 to 10/59, with about half of the gain coming through a changed MicroBooNE-BDT response. Here the
same O/D pair runs on the two most important single-photon backgrounds, **BNB ν_μ CC** and **NC π0**, to test whether
the gain is signal-specific or a generic BDT-response shift.

**Normalization.** None. Every fraction is per processed truth-class event, with a binomial error. The background
samples are fixed-size truth-class lists from one BNB + CORSIKA production, the signal is a separate 59-event
NC-Δ sample without cosmics, and no POT / flux / exposure weighting relates them. **No sensitivity, significance or
purity is computed.** Signal/background ratios in §15 are labelled "not normalized" and are shape indicators only.

Truth is used only in the analysis scripts, as a diagnostic. It is never used in reconstruction.

> **Result in brief** (details §8–§16).
> - **Execution:** same binaries (0 DIFFERENT), control 59 MATCH + 1 known-noise, 1 by-design fallback in 552 DV2 calls.
> - **Vertex:** DV2 improves it on both backgrounds as on signal. Medians 28 → 2.7 cm (signal), 22 → 1.7 cm (NC π0), 1.1 → 0.8 cm (ν_μ CC).
> - **ν_μ CC:** 0 → 0 selected of 400; the numu BDT is unchanged.
> - **NC π0:** 4 → 7 selected of 214 (signal 4 → 10 of 59). Five gains, all audited: 2 BDT response at a good vertex, 1 correct-vertex detached photon, 1 A5, 1 DV2 wrong vertex; none via Fix2.
> - **BDT response:** the numu, other and nue score distributions and their inputs shift together for signal and NC π0 (input-shift correlation r = 0.79). The ncpi0 BDT rejects NC π0 *better* under DV2.
> - **Classification: PROMISING BUT BDT RETRAINING CLEARLY NEEDED.**

---------------------------------------------------------------------------------------------------------------------

## 1. Software identity (signal-study build reused, not rebuilt)

`tables/build_provenance.csv` (130 rows) re-hashes every artifact against the signal study:
**66 IDENTICAL, 0 DIFFERENT**. The other 64 rows are informational: inputs, PBS jobs, BDT weight hashes, exec'd scripts and this study's own script hashes.

| | value |
|---|---|
| ARM O/D library | SIGW `build/install/wct/lib/libWireCellClus.so`, md5 **927a1834af1e44dfef3467dcc6e53976** (sha256 59670bd7…; IDENTICAL) — used read-only from SIGW; every run's template refuses to start unless the md5 matches, and all 1228 O/D runs logged this md5 |
| DV2 head | PR #543 `dsnehadri/dv2-max-vertexer` **feb3ddeb6fea35f42e13c416d65520f22b5b0cbf**, integration worktree `SIGW/source/wct-int` (PATCH.diff = PR head + SP port, unchanged) |
| DV2 bundle | `r7_cloud` (bundle.json, pass1.pt, pass2.pt, isotonic_fold0.json, ranker_fold0.txt): all sha256 IDENTICAL |
| Fix2-v2 | present in ARM O/D (ported verbatim in the signal study; `NeutrinoTaggerSinglePhoton.cxx` sha256 IDENTICAL); ARM F = frozen Fix2-v2 library md5 **9cff76d0d81a4b6c45a88908e78e73e4** + CAND stack + config-final (IDENTICAL) |
| configs | `W/configs` = byte copies of the signal-study configs (md5 IDENTICAL); compiled `armO.json` 5dd42fbe…, `armD.json` 9ca6613e… **IDENTICAL to the signal study's compiled configs** |
| Python stack | torch 2.5.1+cpu, numpy 2.0.2, scipy 1.13.1, lightgbm 4.6.0 (in-container lib, sha256 IDENTICAL), cp39 — 13 wheel hashes IDENTICAL |
| runtime | slf7.sif + larsoft v10_14_02 + sbndcode v10_14_02_04 squashfs overlays; `DV2_STRICT=1`; `LD_PRELOAD` larsoft libpython3.9; same `lar --nskip N -n 1 -c wcls-img-clus-matching-xin-prod.fcl` command as the signal study |
| scorer / cutflow | MicroBooNE SP scorer `score_microboone_bdts.py` (md5 2508298c…, IDENTICAL; only `N_EVENTS`/`BASEDIR`/`OUTDIR` substituted, as in the signal study) and `CUTS_PRE_FV` + `apply_cutflow` exec'd verbatim from the frozen `generate_bdt_comparison.py` |
| BDT weights | the four frozen MicroBooNE TMVA XMLs (`single_photon_{numu,other,ncpi0,nue}_bdt_final.xml`); thresholds numu > 0.4, other > 0.2, ncpi0 > −0.05, nue > −1.0, then `shw_sp_n_20br1_showers == 1` |
| analysis | `scripts/analysis/run_bg.py` execs the signal study's `run_dv2.py` (up to `main()`, plus `control_rows`) **verbatim**: `load_arm`, `derive`, `summarize_event`, `bdt_view`, `access_class`, `main_contains`, `cluster_truth`. Only the background-specific tables (migration, A5, Fix2, audits) are new code |

**Physics configuration changed? NO.**

## 2. Background inputs and truth definitions (`docs/BACKGROUND_INPUT_INVENTORY.md`, `tables/background_input_inventory.csv`)

| | value |
|---|---|
| path | `single_photon/development/nugraph-light-model-v0-20261013/training/stageA_production/stageA10k_fullchain_canary/inputs/reco1/` (3628 Reco1 files, 10,000 unique-RSE events, runs 150001–150040) |
| provenance | Avinay's own Aurora production `gen2-wct0319-bnb-fullchain-canary-512x8-timeoutfix-20261011T2231Z` (transferred to Eagle, sha 3628/3628 verified); sbndcode v10_14_02_03, `prodgenie_corsika_proton_rockbox0p1_sbnd`, MCP2023Blike, GenieGen → G4 → DetSim → `standard_reco1_sbnd.fcl`. Read-only. Only the Reco1 art files are read: **no NuGraph sample, H5 or NuGraph reconstruction is used** |
| products used | exactly the signal-study fcl's inputs: `recob::Wires simtpc2d:dnnsp`, `opflashtpc0/1`, `simtpc2d:badmasks` |
| ν_μ CC list | `inputs/numucc_events.csv`: the **first 400** (file order) of 3264 clean ν_μ CC events — 400 events from 275 files |
| NC π0 list | `inputs/ncpi0_events.csv`: **all 214** clean NC π0 events — from 208 files |

**Truth predicates** (generator truth only; validated memberwise MCTruth / GTruth / MCFlux decoders, byte-exact on all 10,000 events; ν PDG and CC/NC agree for 18,066 / 18,066 interactions):
- **ν_μ CC:** |ν PDG| = 14, `fCCNC = 0` (GTruth `fGint = 2`), vertex in SBND `volTPCActive`.
- **NC π0:** `fCCNC = 1` (`fGint = 3`), ≥ 1 status-1 (post-FSI) π0, vertex in active LAr, any flavour.
- **Clean event:** exactly one interaction in active LAr (so the truth vertex is unambiguous). Rockbox interactions outside the LAr and cosmics are allowed.

**Event lists were fixed before any reconstruction** (census order; nothing chosen on BDT score). Sentinels were picked from evt 0–29 on truth topology only (`inputs/sentinels.csv`).

**Comparability caveat.** The signal sample has **no cosmic overlay**; this background sample is BNB + CORSIKA with
rockbox interactions, so the same Wire-Cell stack also does cosmic rejection and flash matching here. "Neutrino
candidate" and downstream fractions are therefore not directly comparable between signal and background. The O-vs-D
comparison *within* each sample is unaffected (identical events, identical inputs).

## 3. Arms and configuration control (`docs/config_semantic_diff.txt`)

| arm | `vertex_method` | other DV2 keys | `dl_weights` | `main_vertex_swap_apply` | library |
|---|---|---|---|---|---|
| **O** | `original` | — | `''` | absent → false | 927a1834… |
| **D** | `dv2_split_move` | `dv2_bundle` = r7_cloud | `''` | absent → false | 927a1834… |
| **F** (control only) | frozen Fix2-v2 | — | SCN path (compiled out → no effect) | absent | 9cff76d0… |

- Compiled O vs D: exactly `TaggerCheckNeutrino.vertex_method`, `TaggerCheckNeutrino.dv2_bundle` and the provenance string. **Config diff clean: YES.**
- Compiled F vs O: the SCN `dl_weights` path (DL compiled out in the frozen build, so no effect) and `UbooneTaggerOutputVisitor.nu_particle_links = true` (output booking only). The same two differences as in the signal study.
- Each run's template additionally checks the main jsonnet, the operating point, `vertex_method` and the absence of `swap_apply` before calling `lar` (guard exit 3/4 → stop). No guard fired.

## 4. Control: ARM O vs frozen Fix2-v2 on backgrounds (`tables/control_validation.csv`)

Stage 1 ran F, O and D on evt 0–29 of each class (60 events). The control verdict logic is the signal study's
`control_rows` exec'd verbatim (with the signal-only noise list emptied).

**60 events: 59 MATCH, 1 MATCH_EXCEPT_KNOWN_NOISE, 0 DIFFERENT.**
- Every event matches on candidate, final main cluster, ν vertex (max shift 0.0000 cm), accessibility class, `shw_sp_filled`, n20, n20br1, BDT evaluability, all four BDT scores and proton category.
- The one non-MATCH is **numucc evt 18** (INACCESSIBLE in both arms → no BDT scores at all). Only `shw_sp_proton_{length,dqdx,energy}_2` differ: F has no second proton (−1), O has a 0.21 cm / 0.45 MeV stub. This is **F's own run-to-run nondeterminism**: the F run of the same event in job 201013 gave exactly O's values (0.2079 cm, 2.153, 0.4475 MeV). It is the same branch family as the signal study's known noise (evts 46/47). (That 201013 run is in the quarantined set, §5; its values are used only for this comparison.)
- T_tagger schema additions (4 branches) and 6 T_kine columns are the master-drift additions already seen in the signal study.

**ARM O passes configuration consistency.** Every O→D difference below is a **vertex-method effect**, plus run-to-run noise at the level measured in §6.

## 5. Execution, the infrastructure incident and the reruns

All runs are one `lar` per (arm, class, event) in its own `apptainer exec`, exactly as in the signal study, driven by `scripts/run_bg_batch.pbs` (queue by-gpu, account neutrinoGPU::wirecell_2026, one PBS job per stage, parallel lanes inside the job).

| PBS job | content | outcome |
|---|---|---|
| 200949 | sentinels: 6 truth-topology events × F, O, D (LANES 6) | 18/18 CLEAN |
| 201013 | Stage 1: evt 0–29 × F, O, D (LANES 12) | **killed (qdel)** — infrastructure failure, below |
| 201062 | Stage 1 rerun (LANES 5, hardened script) | 162/162 CLEAN, 38 min, max pids 460 / 1024 |
| 201131 | Stage 2: numucc evt 30–399 and ncpi0 evt 30–213 × O, D (LANES 5, 12 h walltime) | **1108/1108 CLEAN**, 5 h 01 min, max pids 482 / 1024, 0 timeouts, 0 resource messages |

**Job 201013 (infrastructure, not reconstruction).** Sophia by-gpu jobs run in a pids cgroup with
`pids.max = 1024`. Twelve concurrent lanes (lar 64–130 threads each plus ~40 apptainer/squashfuse processes per run)
exhausted it (`pids.events` max = 8926): `pthread_create failed: Resource temporarily unavailable`, `fork: retry`,
lar exit 134/139/129 at finalization, and four ARM D lar processes deadlocked in `futex_wait`. The batch-level container
exit was still 0, because the run template exits 0 after printing the real lar exit, so the failures were initially hidden.
- The job was deleted. **All 117 started runs were moved, not deleted**, to `W/scratch/infra_pids_limit_201013/` with a README and a per-run classification (`runs_classified.csv`): 59 COMPROMISED, 58 CLEAN. The 58 CLEAN runs were also moved out (`clean_but_same_job/`), so the whole Stage 1 sample comes from healthy jobs only; they are kept as a reproducibility reference (§6).
- The batch script was hardened (infrastructure only — template, environment and lar command unchanged): dynamic shared queue, launch throttle on `pids.current`, per-run `timeout`, a post-run scan that prints the **real** lar exit and any resource message (`INFRA_SUSPECT`), and a pids monitor log. The analysis (`ab_lib.parse_container_log`) also refuses any run with a non-zero real lar exit or a resource message.
- Stage 1 was rerun in full (201062). The Stage 1 sample used below = the 18 sentinel runs (200949) + the 162 runs of 201062; every Stage 2 run comes from 201131 (`tables/_work/stage2_201131_classified_dryrun.csv`: 1108/1108 CLEAN).

**Final: 400/400 (ν_μ CC) and 214/214 (NC π0) lar exit 0 in both O and D; all 1228 O/D runs on library md5 927a1834…; no run failure of any kind, so none is reconstruction-dependent.**

## 6. Run-to-run reproducibility (`tables/reproducibility_rerun.csv`)

The 58 CLEAN runs of the killed job were compared with their 201062 reruns (same binaries, inputs, template) on every
T_tagger / T_kine branch and the T_segment / T_cluster entry counts:

| arm | IDENTICAL | PERMUTATION_ONLY | DIFFERENT |
|---|---|---|---|
| F | 19 | 14 | 0 |
| O | 18 | 5 | 0 |
| D | 2 | 0 | 0 |

PERMUTATION_ONLY = only the per-shower flag vectors (`shw_sp_20mev_showers`, `shw_sp_br{2,3,4}_showers`) change element
order. Together with the F control event above, run-to-run noise exists only at the level of a sub-cm second-proton
stub; no decision branch differed in any pair.

## 7. DV2 execution gate (ARM D)

Gate definition = the signal study's (`run_dv2.py`/`run_bg.dv2_gate`): every DV2 call yields a prediction and a
placement, with 0 `DL vertex failed`, 0 Python errors and 0 exceptions; a no-prediction is a traditional fallback.

| | ν_μ CC | NC π0 |
|---|---|---|
| neutrino candidates (D) | 356 | 196 |
| DV2 calls / predictions | **355 / 355** | **197 / 196** |
| events with 2 calls | 1 (evt 221: two flash-matched bundles, `nu_per_bundle` ROW 0/1; by design) | 1 (evt 68, same) |
| no-prediction → traditional fallback | 0 | **1** (evt 24: 4 cloud points; WARN, no exception) |
| DV2 exceptions / Python errors / `DL vertex failed` | 0 / 0 / 0 | 0 / 0 / 0 |
| placement: graph vertex / split | 330 / 24 events | 184 / 11 events |
| candidates where the main-vertex step never runs (either arm) | 2 (evts 202, 219) | 0 |
| median runtime O / D | 69 s / 74 s | 73.5 s / 80 s |

- **Fallback rate: 1 of 552 DV2 calls (0.18 %)**, by design. No systematic Python or model failure.
- **Evts 202 and 219 are not DV2 failures.** In both arms the selected "candidate" is a degenerate ≤ 1 cm cluster (the `nu_per_bundle` legacy winner, exempt from the 15 cm floor, 0 associated activities). The main-vertex step returns in 0.03 ms with vertex (0, 0, 0) and E_ν = 0 in O *and* D, so DV2 is never reached. The outcome (INACCESSIBLE, NO_CHANGE) is identical in both arms.
- The numpy `longdouble` UserWarning printed at the first DV2 import is benign; it is in 58/60 signal-study D logs too.
- **DV2 actually runs: YES.** No stop condition is triggered.

## 8. Vertex quality: does the improvement generalize? (`tables/vertex_comparison.csv`)

Candidates in each arm; distance from the reconstructed ν vertex to the generator vertex (true frame), and to the SCE-mapped truth (the signal study's SCE machinery, unchanged).

| sample | frame | arm | n cand | median [cm] | 68% [cm] | <1 cm | <3 cm | <5 cm | >20 cm |
|---|---|---|---|---|---|---|---|---|---|
| NC-Δ signal (59) | true | O | 57 | 28.27 | 45.8 | 0.21 | 0.26 | 0.30 | 0.65 |
| NC-Δ signal (59) | true | D | 57 | 2.67 | 27.0 | 0.33 | 0.51 | 0.54 | 0.40 |
| NC-Δ signal (59) | sce | O | 57 | 28.20 | 44.5 | 0.28 | 0.28 | 0.32 | 0.65 |
| NC-Δ signal (59) | sce | D | 57 | 1.93 | 26.9 | 0.46 | 0.53 | 0.54 | 0.40 |
| ν_μ CC (400) | true | O | 356 | 1.11 | 2.1 | 0.45 | 0.75 | 0.83 | 0.08 |
| ν_μ CC (400) | true | D | 356 | 0.81 | 1.2 | 0.61 | 0.90 | 0.94 | 0.03 |
| ν_μ CC (400) | sce | O | 356 | 0.53 | 1.3 | 0.65 | 0.76 | 0.82 | 0.08 |
| ν_μ CC (400) | sce | D | 356 | 0.40 | 0.5 | 0.85 | 0.92 | 0.94 | 0.03 |
| NC π0 (214) | true | O | 196 | 21.84 | 32.4 | 0.14 | 0.25 | 0.30 | 0.53 |
| NC π0 (214) | true | D | 196 | 1.66 | 5.6 | 0.35 | 0.59 | 0.66 | 0.18 |
| NC π0 (214) | sce | O | 196 | 21.92 | 32.1 | 0.22 | 0.26 | 0.30 | 0.53 |
| NC π0 (214) | sce | D | 196 | 0.89 | 5.6 | 0.53 | 0.62 | 0.67 | 0.18 |

**Yes, it generalizes.**
- **NC π0** behaves like the signal: the traditional vertex is usually on the wrong object (median 22 cm, 53 % > 20 cm), and DV2 brings it to 1.7 cm (0.9 cm SCE), with 18 % > 20 cm.
- **ν_μ CC** already has a good traditional vertex, because the muon makes it easy (median 1.1 cm). DV2 still improves every quantile: < 3 cm 75 → 90 %, > 20 cm 7.9 → 3.1 %, 68 % containment 2.1 → 1.2 cm.
- The two degenerate (0, 0, 0) candidates (§7) sit in the > 20 cm tail of both ν_μ CC arms.

Figures: `docs/figures/crosssample_vertex_and_bdt_inputs.png` (vertex panels), `docs/figures/{numucc,ncpi0}_O_vs_D.png`.

## 9. Main-cluster truth diagnostics (truth used only here)

| sample | true-vertex cluster defined | O main ∋ tv | D main ∋ tv | DV2 switches | correct | wrong | undet. | fix O | break O | same-cluster moves |
|---|---|---|---|---|---|---|---|---|---|---|
| ν_μ CC (400) | 352 | 322 | 343 | 27 | 22 | 3 | 2 | 22 | 1 | 324 |
| NC π0 (214) | 158 | 57 | 124 | 97 | 68 | 16 | 13 | 68 | 1 | 90 |

For comparison, the signal had 11/40 → 30/40.
- A "switch" means DV2 placed the vertex in a cluster other than the traditional selection's.
- "fix O" and "break O" count switches that turn a wrong main cluster into one containing the true vertex, and the reverse.
- DV2 breaks a correct traditional main cluster once in each background.
- **The 16 wrong NC π0 switches** are DV2 ranking misses of the evt0018 kind (signal study §8): the point lands on a cluster that does not contain the true vertex. Only one of them reaches the final selection (evt 92, §13).

## 10. Accessibility, Fix2 and A5 (`tables/{numucc,ncpi0}_access_changes.csv`, `fix2_background_comparison.csv`, `a5_background_comparison.csv`)

| sample | arm | candidates | DIRECT | ONE_HOP | INACCESSIBLE | shw_sp_filled | BDT evaluable | A5 fires |
|---|---|---|---|---|---|---|---|---|
| ν_μ CC (400) | O | 356 | 72 | 33 | 251 | 105 | 105 | 15 |
| ν_μ CC (400) | D | 356 | 78 | 23 | 255 | 101 | 101 | 15 |
| NC π0 (214) | O | 196 | 138 | 23 | 35 | 161 | 160 | 38 |
| NC π0 (214) | D | 196 | 167 | 12 | 17 | 179 | 178 | 16 |

**Access-change mechanisms** (the signal-study vocabulary):

| sample | direction | mechanism | n | events |
|---|---|---|---|---|
| ν_μ CC | GAIN | A5_RETYPE_GAIN | 1 | 35 |
| ν_μ CC | GAIN | FIX2_GAIN | 1 | 124 |
| ν_μ CC | GAIN | OTHER | 6 | 32, 55, 170, 271, 308, 333 |
| ν_μ CC | LOSS | A5_RETYPE_LOSS | 2 | 63, 289 |
| ν_μ CC | LOSS | DV2_WRONG_VERTEX | 1 | 93 |
| ν_μ CC | LOSS | FIX2_LOSS | 3 | 2, 149, 280 |
| ν_μ CC | LOSS | OTHER | 6 | 158, 212, 233, 262, 325, 384 |
| NC π0 | GAIN | A5_RETYPE_GAIN | 3 | 16, 20, 61 |
| NC π0 | GAIN | VERTEX_CORRECTION_GAIN | 2 | 88, 161 |
| NC π0 | GAIN | WRONG_VERTEX_GAIN | 9 | 17, 74, 84, 92, 123, 133, 144, 179, 197 |
| NC π0 | GAIN | OTHER | 11 | 13, 28, 86, 87, 109, 132, 189, 200, 203, 211, 213 |
| NC π0 | LOSS | A5_RETYPE_LOSS | 2 | 42, 210 |
| NC π0 | LOSS | DV2_WRONG_VERTEX | 3 | 90, 120, 168 |
| NC π0 | LOSS | FIX2_LOSS | 2 | 102, 159 |

- **ν_μ CC: DV2 slightly *reduces* shower accessibility** (8 gains, 12 losses; BDT-evaluable 105 → 101). No ν_μ CC access change reaches the final selection.
- **NC π0: DV2 opens the shower path for 25 events and closes it for 7** (BDT-evaluable 160 → 178). This is the expected consequence of putting the vertex where the π0 photons come from.
  - 11 of the gains are OTHER: both vertices within about 1–2 cm, but downstream pattern recognition differs.
  - 9 gains occur with a D vertex that is neither within 3 cm of the SCE-frame truth nor in the true-vertex cluster (WRONG_VERTEX_GAIN). One of these reaches the final selection (evt 92).
  - `VERTEX_CORRECTION_DETACHED_SHOWER_LOSS`, the signal's detached-photon loss at a correct vertex, does not occur in either background.
- **Fix2 (unchanged code) is needed *less* under DV2:**
  - ONE_HOP falls 33 → 23 (ν_μ CC) and 23 → 12 (NC π0).
  - **No ONE_HOP event is selected in any arm**; only one (ν_μ CC O-280) even passes the numu BDT.
  - Plausibility (a coarse test: whether the interaction has any > 20 MeV γ/e± in truth): NC π0 is 23/23 (O) and 12/12 (D) with truth EM. ν_μ CC has 4 (O: 12, 56, 300, 368) and 2 (D: 12, 368) one-hop associations **without** truth EM, i.e. accidental. All six stop at the numu BDT.
  - So under DV2 the one-hop recovery does **not** increase background leakage.
- **A5 (unchanged) is strongly vertex-dependent on NC π0 and neutral on ν_μ CC:**

| sample | A5 fires O | A5 fires D | both | O only | D only | differs & changes outcome |
|---|---|---|---|---|---|---|
| ν_μ CC | 15 | 15 | 9 | 6 | 6 | 3 (170, 271, 289) |
| NC π0 | 38 | 16 | 8 | 30 | 8 | 22 |

  On NC π0 the traditional vertex often sits on a photon shower. A5 then retypes that shower's start (a "track" leaving the vertex) to π±. With the DV2 vertex this happens 2.4× less often. One A5 change reaches the final selection in each direction (190 gained, 114 lost; §13–14). Per-event A5 detail (vertex O/D, shower id, start-segment length, growth, Bragg ratio, new PDG, accessibility, the four scores, stage, selection) is in `tables/a5_background_comparison.csv`.

## 11. Pre-FV cutflows (counts; % of total ± binomial; % of previous step) (`tables/{numucc,ncpi0}_cutflow.csv`)

These are **not** background efficiencies (no FV, no normalization). "gained/lost" counts events passing the step in D but not O, and the reverse.

**ν_μ CC (400 events)**

| step | O | O % of total | O % of prev | D | D % of total | D % of prev | D−O | gained/lost |
|---|---|---|---|---|---|---|---|---|
| 1. total | 400 | 100.0 ± 0.0 | 100.0 | 400 | 100.0 ± 0.0 | 100.0 | 0 | +0/−0 |
| 2. neutrino candidate | 356 | 89.0 ± 1.6 | 89.0 | 356 | 89.0 ± 1.6 | 89.0 | 0 | +0/−0 |
| 3. >20 MeV SP shower | 109 | 27.3 ± 2.2 | 30.6 | 106 | 26.5 ± 2.2 | 29.8 | −3 | +7/−10 |
| 4. all 4 BDTs evaluable | 105 | 26.2 ± 2.2 | 96.3 | 101 | 25.2 ± 2.2 | 95.3 | −4 | +8/−12 |
| 5. numu > 0.4 | 6 | 1.5 ± 0.6 | 5.7 | 5 | 1.2 ± 0.6 | 5.0 | −1 | +1/−2 |
| 6. other > 0.2 | 1 | 0.2 ± 0.2 | 16.7 | 1 | 0.2 ± 0.2 | 20.0 | 0 | +0/−0 |
| 7. ncpi0 > −0.05 | 0 | 0.0 | 0.0 | 0 | 0.0 | 0.0 | 0 | +0/−0 |
| 8. nue > −1.0 | 0 | 0.0 | – | 0 | 0.0 | – | 0 | +0/−0 |
| 9. n_20br1 == 1 | **0** | 0.0 | – | **0** | 0.0 | – | 0 | +0/−0 |

The furthest-reaching ν_μ CC events are CC π0 (real photons):
- evt 142 passes numu and other in both arms; the ncpi0 BDT rejects it (−0.96 / −0.74).
- evt 3 crosses numu upward under D: the vertex moves 65 → 33 cm and numu goes −0.58 → 0.94. It then fails other.

0/400 selected in both arms means < 0.75 % per processed clean ν_μ CC event (95 % CL, rule of three) in each arm. Nothing finer can be said from this sample.

**NC π0 (214 events)**

| step | O | O % of total | O % of prev | D | D % of total | D % of prev | D−O | gained/lost |
|---|---|---|---|---|---|---|---|---|
| 1. total | 214 | 100.0 ± 0.0 | 100.0 | 214 | 100.0 ± 0.0 | 100.0 | 0 | +0/−0 |
| 2. neutrino candidate | 196 | 91.6 ± 1.9 | 91.6 | 196 | 91.6 ± 1.9 | 91.6 | 0 | +0/−0 |
| 3. >20 MeV SP shower | 160 | 74.8 ± 3.0 | 81.6 | 178 | 83.2 ± 2.6 | 90.8 | +18 | +25/−7 |
| 4. all 4 BDTs evaluable | 160 | 74.8 ± 3.0 | 100.0 | 178 | 83.2 ± 2.6 | 100.0 | +18 | +25/−7 |
| 5. numu > 0.4 | 85 | 39.7 ± 3.3 | 53.1 | 120 | 56.1 ± 3.4 | 67.4 | +35 | +57/−22 |
| 6. other > 0.2 | 39 | 18.2 ± 2.6 | 45.9 | 70 | 32.7 ± 3.2 | 58.3 | +31 | +44/−13 |
| 7. ncpi0 > −0.05 | 7 | 3.3 ± 1.2 | **17.9** | 8 | 3.7 ± 1.3 | **11.4** | +1 | +5/−4 |
| 8. nue > −1.0 | 7 | 3.3 ± 1.2 | 100.0 | 8 | 3.7 ± 1.3 | 100.0 | +1 | +5/−4 |
| 9. n_20br1 == 1 | **4** | 1.9 ± 0.9 | 57.1 | **7** | 3.3 ± 1.2 | 87.5 | +3 | +5/−2 |

For reference, the signal cutflow (SIGW) is O 59/57/38/38/15/8/5/5/**4** and D 59/57/41/41/29/19/10/10/**10**.

The nue > −1.0 cut is inert in every sample and arm (it passes every evaluable event).

## 12. BDT leakage: score shifts and BDT-input shifts

**Score shifts.**
- "pass" means score > cut among BDT-evaluable events, **not** cumulative.
- "cross up" means O ≤ cut < D on events evaluable in both arms.
- The signal numbers use the same definitions, applied to `SIGW/tables/event59_original_vs_dv2.csv`.

| BDT | sample | n both eval. | O median | D median | median Δ | O pass | D pass | cross up | cross down |
|---|---|---|---|---|---|---|---|---|---|
| numu (> 0.4) | NC-Δ signal | 31 | +0.001 | +0.953 | +0.021 | 15 / 38 | 29 / 41 | 11 | 4 |
| numu (> 0.4) | ν_μ CC | 93 | −1.000 | −0.999 | +0.000 | 6 / 105 | 5 / 101 | 1 | 1 |
| numu (> 0.4) | NC π0 | 153 | +0.440 | +0.816 | +0.033 | 85 / 160 | 120 / 178 | 38 | 16 |
| other (> 0.2) | NC-Δ signal | 31 | −0.608 | +0.192 | +0.015 | 12 / 38 | 20 / 41 | 5 | 3 |
| other (> 0.2) | ν_μ CC | 93 | −0.947 | −0.927 | +0.000 | 16 / 105 | 18 / 101 | 8 | 5 |
| other (> 0.2) | NC π0 | 153 | −0.121 | +0.351 | +0.107 | 61 / 160 | 100 / 178 | 36 | 10 |
| ncpi0 (> −0.05) | NC-Δ signal | 31 | −0.288 | −0.322 | +0.000 | 13 / 38 | 16 / 41 | 5 | 5 |
| ncpi0 (> −0.05) | ν_μ CC | 93 | −0.198 | −0.207 | +0.000 | 42 / 105 | 45 / 101 | 9 | 4 |
| ncpi0 (> −0.05) | NC π0 | 153 | −0.699 | −0.897 | −0.016 | 30 / 160 | 22 / 178 | 7 | 14 |
| nue (> −1.0) | NC-Δ signal | 31 | −0.799 | −0.199 | +0.029 | 38 / 38 | 41 / 41 | 0 | 0 |
| nue (> −1.0) | ν_μ CC | 93 | −0.624 | −0.500 | +0.000 | 105 / 105 | 101 / 101 | 0 | 0 |
| nue (> −1.0) | NC π0 | 153 | −0.571 | +0.050 | +0.063 | 160 / 160 | 178 / 178 | 0 | 0 |

**ν_μ CC: the numu BDT is unchanged.** It keeps ν_μ CC at −1: pass 6 → 5, one event up (3) and one down (267). The large signal numu gain (15 → 29) is **not** accompanied by a ν_μ CC gain.

**NC π0: the numu, other and nue distributions move like the signal's.**
- numu median +0.44 → +0.82, other −0.12 → +0.35, nue −0.57 → +0.05.
- NC π0 events pass numu and other far more often under D (cumulative ×1.41 and ×1.79, against ×1.93 and ×2.38 for signal).

**The ncpi0 BDT is the exception, and moves the other way.**
- On NC π0 it becomes *more* rejecting under D: median −0.70 → −0.90, pass 30/160 → 22/178, 14 events down and 7 up. It piles up at −1, the strongly π0-like end (see `ncpi0_O_vs_D.png`).
- On signal its pass rate is roughly stable (13/38 → 16/41).
- **DV2 does not make NC π0 more signal-like for the BDT built to reject it.** It makes NC π0 look more like "not ν_μ CC" and "not other", which the signal also does.

**BDT inputs** (`tables/bdt_input_shift{,_crosssample}.csv`; `scripts/analysis/bdt_input_shift.py`).
- **Method.** All 217 distinct input variables of the four TMVA models were read through the scorer's own `read_event`/`collect_inputs`, exec'd verbatim. Evaluability is the scorer's rule (candidate, `shw_sp_filled != 0`, all inputs finite).
- **Statistic.** For each input, the paired net direction P(D > O) − P(D < O) on events evaluable in both arms. A robust statistic is needed because some inputs carry standing sentinels (`min_dis = 1e8`, a 6.25e9 dQ/dx sample on near-zero-length segments) in both arms.

| sample | inputs with abs(net) ≥ 0.2 (of 217) | median abs(net) |
|---|---|---|
| NC-Δ signal (n=31) | 79 | 0.129 |
| ν_μ CC (n=93) | 6 | 0.043 |
| NC π0 (n=153) | 56 | 0.085 |

| corr of net direction | signal | ν_μ CC | NC π0 |
|---|---|---|---|
| NC-Δ signal | 1.00 | 0.62 | 0.79 |
| ν_μ CC | 0.62 | 1.00 | 0.60 |
| NC π0 | 0.79 | 0.60 | 1.00 |

Largest signal movers, with the same inputs in the backgrounds (median O→D in parentheses):

| input | BDTs | signal net | ν_μ CC net | NC π0 net |
|---|---|---|---|---|
| `shw_sp_lem_shower_num_main_segs` (and `br1_3`/`br3_8`/`br4_1` main-seg counts) | numu+other | +0.55 (1→3) | +0.08 (1→2) | +0.28 (2→3) |
| `shw_sp_stem_length` (= `br1_1`/`br3_1_sg_length`) | numu+other+nue | −0.52 (16.9→8.2 cm) | −0.15 (9.8→7.8) | −0.12 (8.8→8.2) |
| `shw_sp_n_stem_size` | numu+other+nue | −0.52 (29→15) | −0.18 (17→14) | −0.10 (16→14) |
| `shw_sp_vec_dQ_dx_2` | other+nue | +0.52 (0.95→1.99) | +0.03 (1.19→1.35) | +0.18 (1.24→1.61) |
| `numu_1_score` (WCPID ν_μ CC tagger) | numu+other | −0.48 (−0.12→−0.43) | −0.13 (0.085→0.078) | −0.35 (−0.16→−0.36) |
| `shw_sp_n_br3_showers` | numu+other+ncpi0 | −0.45 (2→1) | −0.03 (1→1) | −0.18 (2→1) |
| `cosmict_2_valid_tracks`, `cosmict_{2,4}_angle_beam`, `cosmict_2_filled` | other | −0.39…−0.45 | −0.12…−0.38 | −0.28…−0.43 |
| `shw_sp_vec_mean_dedx` | numu+other+nue | +0.39 (2.32→3.22) | +0.18 (2.48→2.81) | +0.19 (2.48→3.02) |

**Reading.**
- With the DV2 vertex at the true interaction point, the selected shower's stem from the vertex gets shorter, more main segments are attributed to the shower, and the first dQ/dx bins rise.
- The WCPID ν_μ CC tagger and the cosmic-tagger sub-flags fall in every sample.
- These are **reconstruction-wide topology changes, not signal-specific ones.** The direction pattern is the same in signal and NC π0 (r = 0.79) and in ν_μ CC (r = 0.60–0.62).
- Their size tracks how far the vertex moved: O median 28 cm (signal), 22 cm (NC π0), 1.1 cm (ν_μ CC).
- The MicroBooNE BDTs were trained on MicroBooNE reconstruction. These inputs now have SBND-DV2 distributions for every class, signal and background alike.

Figure: `docs/figures/crosssample_vertex_and_bdt_inputs.png` (right panels).

## 13. Newly selected backgrounds: deep audit (`tables/newly_selected_backgrounds.csv`)

**ν_μ CC: none** (0 selected in either arm). **NC π0: 5** (87, 92, 135, 145, 190).

| evt (RSE) | truth | vertex–truth O → D [cm] | main ∋ tv O/D | access O → D | Fix2 / A5 | scores O (numu, other, ncpi0, nue) | scores D | n20 / n20br1 O → D | why it entered | class |
|---|---|---|---|---|---|---|---|---|---|---|
| 87 (150001:78:6) | RES, E_ν 0.67 GeV, 1p; γ 317 MeV converts 11.8 cm, γ 46 MeV at 45.5 cm | 0.39 → 0.23 | no / yes (cl 5 → 33) | INACC → DIRECT | none | – (inaccessible) | 0.99, 0.68, 0.27, −0.93 | 0/0 → 1/1 | correct vertex. The leading π0 photon, in its own cluster, is attached to the vertex; the 46 MeV photon is not reconstructed as a > 20 MeV shower, so the event looks like 1γ + 1p. Physically correct association; only the ncpi0 BDT could reject it (0.27 > −0.05) | DETACHED_EM_ASSOCIATION |
| 92 (150013:61:6) | RES, E_ν 0.89 GeV, 1p; γ 183 MeV at 31.8 cm, γ 39 MeV at 86.8 cm | 62.8 → 32.4 | no / no (cl 7, moved) | INACC → DIRECT | none | – | 0.95, 0.50, 0.87, 0.96 | 0/0 → 1/1 | DV2 moves the vertex within the same wrong cluster; a shower becomes direct and scores signal-like on all four BDTs | WRONG_VERTEX |
| 135 (150025:50:2) | RES, E_ν 1.11 GeV, 1p; γ 200 MeV at 2.6 cm, γ 198 MeV at 23.1 cm | 0.67 → 0.35 | yes / yes | DIRECT → DIRECT | none | 1.00, 0.69, −0.128, 0.77 | 1.00, 0.73, −0.015, 0.77 | 1/1 → 1/1 | both vertices good; the ncpi0 score crosses −0.05 by 0.035 | GOOD_RECONSTRUCTION_BUT_BDT_LEAKAGE |
| 145 (150025:77:9) | RES, E_ν 4.27 GeV, 1p; γ 523 MeV at 2.1 cm, γ 235 MeV at 19.7 cm | 1.69 → 1.24 | yes / yes | DIRECT → DIRECT | none | 0.42, 0.89, 0.80, −1.00 | 0.92, 0.92, 0.77, −0.92 | 2/2 → 1/1 | both vertices good; the D shower multiplicity drops 2 → 1, so it passes n_20br1 == 1 (O failed only that cut) | MULTIPLICITY_CHANGE |
| 190 (150022:5:10) | RES, E_ν 1.38 GeV, 0p; γ 479 MeV at 14.5 cm, γ 258 MeV at 3.0 cm | 28.3 → 2.6 | undetermined | ONE_HOP → DIRECT | O: A5 retyped both showers to π± (14.7 cm, g 0.04, Bragg 0.88; 5.2 cm, g 0.12, Bragg 0.92); D: no A5 | −0.80, −0.70, −0.27, 0.13 | 0.97, 0.95, 0.93, −0.67 | 1/1 → 1/1 | vertex corrected; A5 no longer fires; the shower scores signal-like | A5_EFFECT |

- **Summary of the five gains:**
  - 2 are good reconstruction with a BDT-response gain (135 marginal, 145 multiplicity);
  - 1 is a correct-vertex detached real π0 photon with the partner lost (87);
  - 1 is a DV2 wrong vertex (92);
  - 1 comes through A5 (190);
  - **none goes through Fix2.**
- Four of the five sit within 2.6 cm of truth under D. Apart from 92 (a DV2 wrong vertex), none is a reconstruction defect.
- 87, 135, 145 and 190 are the "π0 with one photon lost or merged" topology that the ncpi0 BDT is meant to remove. Under D, all five pass it: four clearly (ncpi0 0.27–0.93) and 135 marginally (−0.015).

## 14. Backgrounds rejected by DV2 (`tables/backgrounds_rejected_by_dv2.csv`)

**ν_μ CC: none. NC π0: 2.**

| evt (RSE) | truth | vertex–truth O → D [cm] | access O → D | A5 | scores O | scores D | mechanism |
|---|---|---|---|---|---|---|---|
| 90 (150020:53:10) | DIS, E_ν 1.29 GeV, 0p; γ 245 MeV at 76.8 cm, γ 23 MeV at 7.4 cm | 80.2 → 12.7 | DIRECT → INACCESSIBLE | none | 0.99, 0.78, 0.24, −0.87 | – | ACCESSIBILITY_LOSS. DV2 moves the vertex much closer but into a different wrong cluster (cl 12 → 32), and the shower is no longer reached |
| 114 (150025:25:5) | RES, E_ν 1.21 GeV, 1p, 2 π0 (4 γ: 197, 171, 67, 25 MeV) | 62.0 → 0.64 | DIRECT → DIRECT | O: A5 retyped shower id0 (16.9 cm, g 0.43, Bragg 1.04) | 0.92, 0.52, 0.43, 0.69 | 0.81, −0.16, −0.97, 0.45 | VERTEX_CORRECTED_BDT_REJECTS. At the correct vertex (cl 19 → 72), n20 1 → 2; the other BDT rejects it and the ncpi0 BDT would too (−0.97) |

The final NC π0 change is therefore **+5 / −2**. For signal it is **+8 / −2** (gained 2, 22, 32, 35, 42, 45, 49, 56; lost 20, 36).

## 15. Signal vs background (no normalization; `tables/signal_background_summary.csv`)

Cumulative pre-FV counts; percentages are per processed event ± binomial.

| step | signal O | signal D | sig D/O | ν_μ CC O | ν_μ CC D | ν_μ CC D/O | NC π0 O | NC π0 D | NC π0 D/O |
|---|---|---|---|---|---|---|---|---|---|
| candidate | 57 (96.6 ± 2.4) | 57 (96.6 ± 2.4) | 1.00 | 356 (89.0 ± 1.6) | 356 (89.0 ± 1.6) | 1.00 | 196 (91.6 ± 1.9) | 196 (91.6 ± 1.9) | 1.00 |
| BDT evaluable | 38 (64.4 ± 6.2) | 41 (69.5 ± 6.0) | 1.08 | 105 (26.2 ± 2.2) | 101 (25.2 ± 2.2) | 0.96 | 160 (74.8 ± 3.0) | 178 (83.2 ± 2.6) | 1.11 |
| numu pass | 15 (25.4 ± 5.7) | 29 (49.2 ± 6.5) | 1.93 | 6 (1.5 ± 0.6) | 5 (1.2 ± 0.6) | 0.83 | 85 (39.7 ± 3.3) | 120 (56.1 ± 3.4) | 1.41 |
| other pass | 8 (13.6 ± 4.5) | 19 (32.2 ± 6.1) | 2.38 | 1 (0.2 ± 0.2) | 1 (0.2 ± 0.2) | 1.00 | 39 (18.2 ± 2.6) | 70 (32.7 ± 3.2) | 1.79 |
| ncpi0 pass | 5 (8.5 ± 3.6) | 10 (16.9 ± 4.9) | 2.00 | 0 | 0 | – | 7 (3.3 ± 1.2) | 8 (3.7 ± 1.3) | 1.14 |
| nue pass | 5 (8.5 ± 3.6) | 10 (16.9 ± 4.9) | 2.00 | 0 | 0 | – | 7 (3.3 ± 1.2) | 8 (3.7 ± 1.3) | 1.14 |
| exactly one (selected) | **4 (6.8 ± 3.3)** | **10 (16.9 ± 4.9)** | **2.50** | **0** | **0** | – | **4 (1.9 ± 0.9)** | **7 (3.3 ± 1.2)** | **1.75** |

The final-fraction ratio signal / NC π0 is 3.6 (O) and 5.2 (D). It is **per processed event and NOT normalized**: different samples, cosmics in the background only, and no POT or flux. It indicates direction only.

**Neither change is statistically significant at these sizes.** The paired gained/lost counts give a two-sided sign-test p of 0.11 for signal (8 vs 2) and 0.45 for NC π0 (5 vs 2).

**Answer to the key question.**
- **Relative to ν_μ CC:** the signal gain is not accompanied by any leakage (0 → 0; numu BDT unchanged).
- **Relative to NC π0:** the signal gain is larger (×2.5 vs ×1.75), but **qualitatively the same mechanism acts on both up to the ncpi0 BDT.** The numu and other steps admit NC π0 almost as much more often as they admit signal. Only the ncpi0 BDT discriminates better under DV2 (NC π0 pass-of-previous 17.9 → 11.4 %, signal 62.5 → 52.6 %).

## 16. Interpretation and classification

1. **DV2 is a better SBND vertex method on all three samples.**
   - The vertex improves on every quantile for NC π0 and ν_μ CC as well as for signal.
   - The main cluster contains the true vertex more often: ν_μ CC 322 → 343 / 352, NC π0 57 → 124 / 158.
   - The execution is clean: 1 by-design fallback in 552 calls, 0 failures, a clean control and identical binaries.
2. **ν_μ CC leakage does not increase.**
   - 0 → 0 selected; numu BDT pass 6 → 5.
   - Shower accessibility slightly decreases; Fix2 one-hop usage falls; the A5 rate is unchanged.
3. **NC π0 leakage increases somewhat, less than the signal gain, through understandable events.**
   - 4 → 7, with 5 gains of which four are within 2.6 cm of truth; none through Fix2.
   - Fix2 one-hop and A5 both fire *less* under DV2. The extra accessibility is mostly the physical consequence of a correct vertex for an event with real photons.
   - So this is **not** a reconstruction-interface tradeoff in the sense of outcome C.
4. **The MicroBooNE BDT response shifts for signal *and* NC π0 together.**
   - numu, other and nue score medians move strongly upward in both.
   - Their 217 inputs shift in correlated directions (r = 0.79), with magnitudes that track the vertex correction.
   - The signal-side numu gain is not ν_μ CC-specific encouragement; it is a generic response to "shower at the correct vertex", which NC π0 shares.
   - The one BDT designed for the dominant photon background (ncpi0) separates *better* under DV2.
   - This is the hypothesis of task §27, now tested: **DV2 is the better SBND reconstruction, but the MicroBooNE BDT operating point (trained on MicroBooNE reconstruction) is not a stable analysis-level discriminator for it.**

**CLASSIFICATION: PROMISING BUT BDT RETRAINING CLEARLY NEEDED.**
- **Not A:** NC π0 leakage is not flat (4 → 7), and the numu/other score distributions are not stable.
- **Not C:** Fix2 and A5 involvement *decrease*, and only 1 of 5 NC π0 gains is a wrong-vertex association.
- **Not D:** there are no unexplained leaks and no reconstruction regressions.

**Not done, and not to be done now:**
- no change to DV2 (no reconstruction bug found; evt 92 and the 16 wrong NC π0 switches are ranking misses of the evt0018 kind, owner questions only);
- no change to Fix2 or A5;
- no BDT retuning or retraining in this study;
- no FV;
- no sensitivity.

**Next recommended step.**
- Run the same O/D pair on a **general BNB + cosmic sample with known POT**, plus an off-beam / cosmic-only sample (no off-beam art Reco1 is on Sophia), at a size that bounds ν_μ CC below the current < 0.75 % per event.
- Then define an SBND-DV2 photon-classifier retraining or retuning plan. Do not use the current MicroBooNE pass rates as SBND efficiencies.

## 17. Caveats

- **Samples differ.** Signal: 59 NC-Δ events, no cosmics, v10_14_02_04 production. Backgrounds: BNB + CORSIKA rockbox, v10_14_02_03 production. Compare O→D changes, not absolute fractions across samples.
- **Small numbers.** 31 signal events are evaluable in both arms, and 4–10 events are selected. All per-event classes (§13–14) are individual audits, not rates.
- **Clean-event definition.** Only events with exactly one active-LAr interaction are used (an unambiguous truth vertex). The 168 multi-interaction events of the census are excluded.
- **ν_μ CC list.** It is the first 400 of 3264 clean events in file order, fixed before reconstruction (not BDT-selected).
- **Pre-FV, MicroBooNE thresholds.** The nue > −1.0 cut is inert. No MicroBooNE FV and no SBND FV are applied.
- **Fix2 plausibility is coarse.** It records whether the interaction has truth EM above 20 MeV, not a per-shower truth match.
- **DV2 numerics.** DV2 runs under torch 2.5.1 / numpy 2.0.2 (container glibc 2.17), as in the signal study, not the PR author's torch 2.9.1. Any DV2-internal drift is unmeasured.
- **Run-to-run noise** exists at the sub-cm second-proton level (F control evt 18, §4) and as permutation-only flag-vector order (§6). Neither touches a decision branch.

## 18. Deliverables

- **Docs:**
  - `docs/DV2MAX_SINGLEPHOTON_BACKGROUND_VALIDATION.md` (this file);
  - `docs/BACKGROUND_INPUT_INVENTORY.md`;
  - `docs/config_semantic_diff.txt`;
  - `docs/figures/{numucc,ncpi0}_O_vs_D.png` (vertex true/SCE, n20, n20br1 and the four BDT scores; identical binning);
  - `docs/figures/crosssample_vertex_and_bdt_inputs.png`;
  - `scratch/infra_pids_limit_201013/README.md` (incident).
- **Required tables (`tables/`):**
  - `background_input_inventory`, `build_provenance`, `control_validation`;
  - `numucc_cutflow`, `ncpi0_cutflow`, `numucc_score_migration`, `ncpi0_score_migration`, `numucc_access_changes`, `ncpi0_access_changes`;
  - `a5_background_comparison`, `fix2_background_comparison`;
  - `newly_selected_backgrounds`, `backgrounds_rejected_by_dv2`, `signal_background_summary`;
  - `summary.json`.
- **Additional tables:**
  - `vertex_comparison`, `bdt_input_shift`, `bdt_input_shift_crosssample`, `reproducibility_rerun`;
  - per-class `{rs}_run_gate`, `{rs}_a5`, `{rs}_fix2`, `{rs}_newly_selected`, `{rs}_rejected_by_dv2`, `{rs}_summary.json`.
- **Scripts:**
  - `scripts/run_bg_template.sh` and `scripts/run_bg_batch.pbs` (runs);
  - `scripts/analysis/run_bg.py` (execs the signal-study analysis verbatim);
  - `build_final_tables.py`, `bdt_input_shift.py`, `make_report_tables.py`, `plots_bg.py`, `reproducibility_201013.py`;
  - `prefill_em_cache.py` (speed-up only: identical cache entries);
  - `scripts/make_provenance_bg.py`, `scripts/quarantine_infra.py`, `scripts/mirror_to_repo.sh`.
- **Outputs:**
  - `W/runs/{numucc,ncpi0}/arm{O,D,F}/wirecell/evt_NNNN/`;
  - logs `W/logs/{numucc,ncpi0}/arm{O,D,F}/`, PBS logs `W/logs/pbs/`.
- **Mirrored** (files only, no git) to `single_photon/repos/sbnd-wirecell-single-photon/reconstruction_studies/dv2max_background_validation/`, with `MANIFEST.sha256`.
