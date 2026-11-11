# The deep-learning (DL) vertex in the SBND Wire-Cell pattern recognition: source audit of `T_dlvtx_call` / `T_dlvtx_cloud`

Date: 2026-11-11. Branch `analysis/ncdelta-shower-attachment-vertex-provenance-20261111`. Audit only. Tags: **SOURCE** (read in code / the producer's own design note), **MEASURED** (this phase, `tables/vertex_provenance_audit/`), **NOT AUDITED**.

**Source:** `HaiwangYu/wire-cell-toolkit`, `sbnd-wc-flatcaf`, **commit `4b6853d4`**, files read with `git show 4b6853d4:<path>`: `cfg/pgrapher/experiment/sbnd/docs/sbnd-dl-vertex-flow.md` (the producer's flow note), `clus/inc/WireCellClus/PRDlVtxDump.h` (the recorded struct), `clus/src/NeutrinoVertexFinder.cxx:4703-5400` (`determine_overall_main_vertex_DL`), `clus/src/TaggerCheckNeutrino.cxx:3641-3885` (the call sites), `root/src/SbndPrMagnifyTrackingVisitor.cxx:333-541` (the writer). The production configuration is not public; the flow note states the SBND production operating point (below), which is the only configuration evidence.

## 1. What the DL vertex is  (SOURCE)

* **One network call per candidate per chain.** `TaggerCheckNeutrino::visit` loops over the beam-window flash candidates (`nu_per_bundle`, one candidate = main cluster plus the clusters sharing its matched flash). For each candidate there are **two calls**: the **dual-chain OFF pass** (an exclusion-free copy of the whole vertexing with its own fitter, `fit_exclusion = false`, called first) and the **production pass** (`pass = 0`); the OFF pass's final vertex becomes the *hint* given to the production call. In `T_dlvtx_call`: `pass` 1 = OFF, 0 = production; `call_index` 0 = OFF, 1 = production (MEASURED: 11,754 production and 11,754 OFF calls for 11,754 candidates; no other pass code).
* **Network input.** `vec_xyzq` (cm): every PR-graph vertex's fit point (`q` = fit dQ) and every segment's interior fit points; `q = dQ x q_scale + q_offset`. It is built from the **graph after the traditional PR of all clusters of the candidate** (stage B), with trajectory-fit exclusion; the OFF pass builds the same cloud from its exclusion-free fit. `T_dlvtx_cloud` stores that cloud point by point (not read in this phase: it is the network input, not a vertex).
* **Network.** `WCPPyUtil::SCN_Vertex` (`pyutil/python/SCN_Vertex.py`): a sparse-convolution network on 0.5 cm voxels (weights `uboone/scn_vtx/t48k-m16-l5-lr5d-res0.5-CP24.pth`, a **MicroBooNE-trained** network applied to SBND), returning the **top-5 voxels `(x, y, z, score)`** (`dl_vtx_top_k = 5`; the recorded `payload`, 20 floats). The network does not know the vertex of the neutrino interaction; it scores voxels of the cloud.
* **From voxels to a vertex (rerank, NVF:5083-5400).** Each of the 5 voxels is **snapped to the nearest PR-graph vertex**; duplicates keep the higher score; each snapped vertex is scored by **fixed geometric weights plus the DL score**: host cluster is the main cluster (+2.0), saturating bonus for long host clusters (+2.0, saturating at 60 cm), penalty for a short isolated non-main cluster (-2.0), inside the fiducial volume (+0.5), soft snap-distance penalty (up to -2.0, 5 cm scale), a vestigial forward-z tiebreaker (<= 0.25). The source comment: *the three geometric signals dominate when the DL score is uncertain (~0.005), the DL dominates when confident (> 0.1)*. A candidate is accepted if the score passes `dl_vtx_min_accept_score = 10` on the scale `dl_vtx_score_scale = 1000`.
* **Dual-chain snap (production call).** The OFF pass's final vertex is snapped to the nearest production candidate vertex the cluster gate admits; **if within 2 cm it replaces the rerank's choice** (`dual_chain_mode = snap`, `dual_chain_transfer_max = 2`). A protected two-end-break vertex can veto the DL choice (`two_end_veto`).
* **Consequence for what "the DL vertex" is:** the accepted DL vertex is **always a vertex that already exists in the traditional PR graph** (a snapped graph vertex), chosen mostly by geometry unless the network is confident. If it changes nothing the traditional `determine_overall_main_vertex` result stands.

**MEASURED confidence of the network:** the top-1 score has median **0.0055**; **85 %** of the events have a top-1 score below 0.02 and **8 %** above 0.1 (truth 0p: 94 % below 0.02; truth 1p 81 %; truth >= 2p 61 %). So for most signal events the source's own rule says the geometric terms decide.

## 2. What is recorded per call  (`PRDlVtxDump.h`; MEASURED field checks)

`trad_*` (the traditional main vertex of the main cluster before the DL), `rerank_*` (this call's own pick before the dual-chain snap), `dl_*` (the accepted vertex after snap and veto; `accepted`), `hint_*` (the OFF-pass vertex given to production), `final_*` (the candidate's **final main vertex**), `payload` (top-5), `n_points` / `n_vertex_rows`, `status`, and on MC the truth: `truth_all_*` (every interaction of the event) with `truth_all_reco_*` = the truth vertex **shifted into the cloud's frame by the TrueFwd space-charge map**.

* **Coordinate convention:** every vertex of the table is in the **raw reconstruction frame, cm**; the truth vertex is shifted into that frame (`truth_sce_applied == 1` in all 11,754 production calls; MEASURED magnitude of the shift: median 0.83 cm, 84 % below 1.54 cm, 99 % below 3.5 cm, maximum 5.0 cm, so it is small against the 5 cm anchoring tolerance and the 20-30 cm displacements studied). Displacements between these vertices are therefore frame-consistent. **`final_*` equals `kine_nu_*_corr` of `T_kine` for all 11,754 candidates (max difference 1.8e-5 cm)**: the `_corr` suffix does not mean a further SCE correction relative to `final_*`.
* **Candidate association:** `nu_index` is the candidate (the `T_kine` / `T_tagger` row). MEASURED mapping: **11,331 events requested, 11,309 with a DL record (22 without), 11,783 candidates of the Phase-9 table, 11,754 with a production call (29 without), 0 duplicated (event, candidate, call) records, 0 candidates with more than one production call, 23,508 / 23,508 records whose run / subrun / event equal Phase 9**, 0 calls with `status != 0`.
* **Sentinels:** a not-accepted call has `dl_x = dl_y = dl_z = 0` (1,002 of 1,002 production calls with `accepted == 0`); the analysis therefore never uses `dl_*` of a not-accepted call (it uses the traditional vertex, `dl_kind = traditional_kept`). Accepted DL vertices (10,752) and valid final vertices (11,748 of 11,750) all lie inside a generous box around the active volume.
* **Truth in the record** is the signal interaction chosen by the Phase-9 `signal_nu_idx` among `truth_all_*` (the writer's own `truth_x` is the max-edep interaction, which can be another interaction): 11,754 of 11,754 production calls contain it.

## 3. Which DL point seeds the later reconstruction  (SOURCE)

The accepted DL vertex becomes the main vertex (switching the main cluster if needed) and is then refined by step D (`improve_vertex` etc.) and used by stage E (`shower_clustering_with_nv`, `examine_direction`) and the taggers; see `WIRECELL_VERTEX_REFINEMENT_SOURCE_AUDIT.md`. **The raw top-1 voxel is never used directly**: only the snapped graph vertex is.

## 4. What is established

* The DL vertex is a snapped **graph** vertex chosen by a geometric-plus-DL score in which the DL term is small for most signal events.
* Both the traditional vertex and the DL candidates come from the same PR graph; the DL step can select among, not create, vertices.

## 5. What is not

* The network's training domain (MicroBooNE) versus SBND signal; the exact `dl_vtx_*` values of the production job (the flow note is the evidence).
* `T_dlvtx_cloud` was not read; the cloud's content is described, not analysed.
