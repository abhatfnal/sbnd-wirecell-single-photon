# INTEGRATION MAP — DV2-MAX vertexer (PR #543) × single-photon branch

Work area: `single_photon/development/dv2max_singlephoton59_20261102/` (W). Everything below is
uncommitted, inside W, and leaves Snehadri's remote/branch and our frozen SP tree untouched.

## 1. The three trees compared

| | ref | what it is |
|---|---|---|
| **A** PR branch | `dsnehadri/dv2-max-vertexer` = `origin/pr543` = **feb3ddeb** | master **b7bd2a1a** (2026-10-07) + exactly the 4 listed commits: 43660339 DV2-MAX engine, eb7636ae Python inference + r7_cloud bundle, b87ae37d `vertex_method`, feb3ddeb SBND default `dv2_split_move`. No newer commits. |
| **B** our SP source | `feature/sbnd-singlephoton-onehop-20261005` = **cd7e7b39** (parent 8dddba5b) | master **51b5a1fc** (2026-10-01) + 251ff143 (bundle provenance) + d2ed2069, e302f5ff, 8dddba5b (Fix2 → Fix2-v2) + cd7e7b39 (diagnostic probe). The frozen Fix2-v2 library (md5 9cff76d0…) = CAND objects of 251ff143 + the Fix2 NTSP object. |
| **C** common ancestry | merge-base(A, B) = **51b5a1fc** | B's base. A is 50 non-merge master commits ahead of it (`git log 51b5a1fc..b7bd2a1a`) plus the 4 DV2 commits. |

## 2. What PR #543 changes (read from `git diff b7bd2a1a feb3ddeb`)

* `NeutrinoPatternBase.h`: `VertexMethod {original, dv2_snap, dv2_split, dv2_split_move}`, `kDv2MoveReuseDistCm = 1.5`,
  per-event `m_dv2_target{_valid}`, `dv2_place_main_vertex()`.
* `NeutrinoVertexFinder.cxx :: determine_overall_main_vertex_DL` — new `if (dv2)` branch, **inside `#ifdef HAVE_PYTHON_INC`**:
  same DL cloud (PR-graph vertex rows first, then segment-interior fit points of every cluster) → `WCPPyUtil::DV2_Vertex` →
  point P + P(<1 cm). Placement: nearest PR-graph vertex; for `dv2_split_move` if that vertex is > 1.5 cm from P, the nearest
  segment-interior fit point if nearer (`break_segment` there, `kProtectedBreak`, long-muon sets updated). Then the **shared
  DL tail**: if the pick is in another cluster → `swap_main_cluster(...)` with `main_cluster` passed **by reference**
  (a fully applied swap), `examine_direction`, the short-proton tag, long-muon cleanup.
  No re-rank, composite score, two-end-break veto, dual-chain transfer.
* `TaggerCheckNeutrino.cxx :: visit` — for `dv2_*`: the dual-chain OFF pass is skipped; the DL step is called with the bundle;
  **if it accepts a point, `determine_overall_main_vertex` (examine_main_vertices / check_switch_main_cluster /
  compare_main_vertices_global / the `main_vertex_swap_apply`-gated swap) is NOT called**; kink/junction snap,
  improve_vertex, main-vertex graph audit and conn3 stitch are skipped; `dv2_split_move` then moves the vertex onto P
  (MyFCN::UpdateInfo + cluster refit). No prediction → WARN + the traditional path with its original refinement.
* Exceptions inside the DL step (including a Python error raised under `DV2_STRICT=1`) are **caught** by the existing
  `catch` → WARN "DL vertex failed" → traditional fallback. So `DV2_STRICT=1` does not abort the job; the hard gate is
  therefore "0 'DL vertex failed', 0 'no DV2-MAX prediction', ≥1 placement INFO line per candidate, hook-log record".
* `configure()`: `vertex_method` validated; `dv2_*` without `HAVE_PYTHON_INC` → `raise` (cannot silently run compiled out);
  bundle must exist on WIRECELL_PATH.
* `pyutil/`: `DV2_Vertex.{h,cxx}` (embedded-Python bridge, same pattern as SCN_Vertex), `python/DV2_Vertex.py`,
  `python/dv2max_vertexer/` (torch CPU + LightGBM ranker); `cfg/dv2max/r7_cloud/` bundle (sha256 in build_provenance.csv).
* `cfg/pgrapher/experiment/sbnd/clus.jsonnet :: pr()` — `vertex_method='dv2_split_move'`, `dv2_bundle=…` arguments;
  keys emitted only when ≠ `original`.

**Semantic conflict check (§12 STOP condition): none.** PR #543 touches no file our SP branch touches
(NTSP, MABC, clustering_switch_scope). Fix2-v2 acts downstream in `singlephoton_tagger` on whatever main vertex /
`map_vertex_to_shower` the vertex step produced, so it composes with either vertex method without code change.

## 3. Our SP changes → disposition (full table: `tables/single_photon_patch_map.csv`)

| our change | class | action |
|---|---|---|
| Fix2-v2 one-hop fallback (net d2ed2069+e302f5ff+8dddba5b, NTSP only) | **ALGORITHM NEEDED** | ported verbatim (applies at +5 lines) |
| cd7e7b39 `fix2_diag` BFS probe | DIAGNOSTIC-ONLY | **not ported** |
| 251ff143 bundle-provenance stamp (MABC, switch_scope, `pr(stamp_matching_bundle_id)`) | OUTPUT/PROVENANCE (needed for the frozen top-level config to compile) | ported; C++ verbatim, 8 jsonnet lines hand-placed (signature moved) |
| SBND operating point (`pr-operating-point.jsonnet`, incl. A5, dQ/dx guards, sp_* PID, z prior 100) | frozen physics config | copied unchanged; + `vertex_method`, `dl_weights=''` |
| `main_vertex_swap_apply=true` | DIAGNOSTIC A/B only | **not used** (absent → C++ false, both arms) |

## 4. Master drift A vs B (50 commits) — what can act on ARM O

* Config-visible (compiled leaf diff, `docs/config_semantic_diff.txt`): frozen vs ARM O differ only in
  `dl_weights` (deliberate, §5) and `UbooneTaggerOutputVisitor.nu_particle_links=true` (19e6d39a, output booking only).
* C++-default changes that could act without a config key: none found for this job.
  `af696a11` (sigproc default flip) and `4afd5cac` (SBNDOpFlashFinder) act on components **not instantiated** here
  (input = Reco1 `simtpc2d:dnnsp` wires; flashes from LArSoft `opflashtpc{0,1}`). The rest are default-off knobs,
  other detectors (FD-HD/FD-VD/PDVD/ICARUS), log-only probes (kine_overlap_probe, mvsa_probe), dl_vtx_dump (off), or
  stated result-neutral refactors (ClusterArrays in-place bodge, ClusteringIsolated bbox pre-check, sep_family fill only on
  inputs that used to throw).
* Output schema additions expected in ARM O/D vs frozen: T_segment tree, T_kine row-identity columns,
  T_tagger `act_n_seg*`/`match_isFC` (0bb05b3c under nu_provenance). Observation only; excluded from the control verdict.
* The ARM O control run is the empirical test of this reading (§18).

## 5. Control design consequences

* The frozen build had the SCN inference compiled out. The integration build embeds Python (required by DV2), so a
  non-empty `dl_weights` would make ARM O run the uBooNE SCN net — something the reference never did. Both arms therefore
  use `dl_weights=''`: ARM O = the original method on the geometric vertex (the owner's identity-gate convention, cfg
  comment "'' restores the geometric-only vertex"); `dv2_*` does not read `dl_weights`.
* With `dl_weights=''` the dual-chain OFF pass is skipped (owner code: "the OFF pass cannot change any output" without
  weights). In the frozen runs it ran but its hint could never be consumed (the consumer is inside the compiled-out block).
* O vs D compiled-config difference = `vertex_method`, `dv2_bundle`, and the provenance string. Nothing else.

## 6. Environment (minimum change, §14)

| item | frozen Fix2-v2 | integration | why |
|---|---|---|---|
| container / larsoft / sbndcode | slf7.sif + larsoft v10_14_02 + sbndcode v10_14_02_04 | **same** | — |
| WCT | CAND 251ff143 (+Fix2 NTSP object), no Python | PR head feb3ddeb + SP port, **with Python** (`--with-python-*` = larsoft python v3_9_15) | DV2 needs embedded Python |
| larwirecell | CAND build of 9295e2a3 source | **same source**, rebuilt against the new WCT headers | master adds `Facade::Grouping::m_dead_region` (class layout change in a header larwirecell includes) — no ABI patching |
| Python stack | — | torch 2.5.1+cpu, numpy 2.0.2, scipy 1.13.1, lightgbm 4.6.0 (lib rebuilt in-container from the PyPI sdist), cp39 | the PR's pyenv-dl (py3.14, torch 2.9.1) needs glibc ≥ 2.28; the container has 2.17. torch 2.5.1 is the last glibc-2.17 CPU build; DV2 code needs torch ≥ 2.1 (`mmap=`, `assign=`) |
| libpython | — | `LD_PRELOAD` larsoft libpython3.9 (both arms) | extension modules need global Py symbols (PR cfg comment) |
| LD_LIBRARY_PATH | sbndcode env | sbndcode env **minus** `scisoft/larsoft/libtorch/v2_1_1b/lib` (both arms) | that directory beats the torch wheel's RUNPATH `$ORIGIN` → `libtorch_python.so: undefined symbol` (gate G5/G6 FAIL in job 200903). The lar job never initializes larsoft libtorch (CAND LD_DEBUG; smoke LD_DEBUG: 0 inits), so dropping it from the search path changes nothing else |

The Python-stack versions differ from Snehadri's validation env (torch 2.9.1 / numpy 2.5.3 / scipy 1.18.1 / lightgbm 4.7.0):
fp32 CNN outputs may differ at the 1e-6 level; the LightGBM model is a plain v4 tree text (no linear trees), so ranking is
version-stable. This is SOFTWARE-STACK DRIFT for DV2 itself, not a vertex-method effect, and is recorded as such.
