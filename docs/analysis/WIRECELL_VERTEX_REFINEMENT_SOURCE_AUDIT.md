# How the final candidate vertex is formed: every step that can move the Wire-Cell main vertex between the traditional vertexing and `T_tagger` / `T_kine` / `shw_sp_*`

Date: 2026-11-11. Branch `analysis/ncdelta-shower-attachment-vertex-provenance-20261111`. Audit only. Tags: **SOURCE** (producer commit `4b6853d4`, `git show 4b6853d4:<path>`), **MEASURED** (`tables/vertex_provenance_audit/`), **NOT AUDITED**. Knob defaults are the source defaults; the production configuration is not public (the producer's flow note lists the SBND production values it surveyed: `nu_per_bundle`, `fit_exclusion`, `dl_vtx_rerank`, `dl_vtx_top_k = 5`, `dl_vtx_dual_chain` in snap mode).

## 1. The chain per candidate  (SOURCE: `sbnd-dl-vertex-flow.md`, `TaggerCheckNeutrino.cxx:3641-4348`)

| stage | what | can it move the main vertex? |
|---|---|---|
| OFF pass | an exclusion-free copy of A-D on its own fitter; its final vertex is the *hint* | only the hint (a snap target within 2 cm) |
| **A** main cluster, traditional PR | `find_proto_vertex` (segment breaking, structure examination), `separate_track_shower`, `determine_direction`, `shower_determining_in_main_cluster`, **`determine_main_vertex`** (candidate scoring by `compare_main_vertices_all_showers` + `improve_vertex`) | **yes: this creates the traditional vertex `V_trad`** |
| **B** other clusters of the bundle | the same per cluster, then deghosting | adds graph vertices (candidates for the DL step) |
| **C** DL vertex | `determine_overall_main_vertex_DL`; if it changes nothing, the traditional `determine_overall_main_vertex` | **yes: selects `V_DL` among snapped graph vertices** (`DL_VERTEX_SOURCE_AUDIT.md`) |
| **D** refinement | `snap_main_vertex_to_kink` (knob `vertex_kink_snap`, **off**), `snap_main_vertex_to_junction` (knob `vertex_junction_snap`, **off**), **`improve_vertex`** (refits the vertex position with its segments, `fit_vertex`), `main_vertex_graph_audit`, `stitch_disconnected_main_cluster` | `improve_vertex`: sub-cm to cm refits; the audits: graph edits, rarely a switch |
| **E** final PR with the neutrino vertex | `clustering_points`, `examine_direction`, `demote_cross_cluster_straight_stems`, `orphan_dup_audit`, **`shower_clustering_with_nv`** (shower ownership, section 3 of `SHOWER_ATTACHMENT_SOURCE_AUDIT.md`), `reconcile_particle_flags`, `calculate_shower_kinematics` | `shower_clustering_with_nv` contains two sites that **overwrite the main vertex position**: `id_pi0_backproject_vertex` (`main_vertex->fit().point = best_x`, NSC:7117; only with `m_pi0_bp_miss > 0`, **off**) and `id_pi0_without_vertex` (`main_vertex->fit().point = vtx_point`, NSC:8741, labelled "hack" in the source: when a displaced-vertex pi0 pair is accepted the main vertex is set to the pi0 decay point and the members are re-seated at it with connection type 2) |
| F taggers + kinematics | cosmic, numu, ssm, nue, single-photon taggers, `fill_kine_tree` | read the vertex; `kine_nu_*_corr` and the tagger vertex are the main vertex's fit point |

`fit_vertex` / `improve_vertex` use the vertex's own segments only (a local least-squares of the vertex position); no truth and no detector boundary enter. The two `snap_*` steps would move the vertex to a kink or junction but are off by default (NOT AUDITED in production).

## 2. What is the "final vertex"

`final_*` of `T_dlvtx_call` is the candidate's main vertex **after stage E** and equals `kine_nu_*_corr` of `T_kine` in all 11,754 production calls (max difference 1.8e-5 cm) and the vertex that `shw_sp_*` distances are measured from (with the tagger's optional SCE correction, a knob of the single-photon tagger, NOT AUDITED). So **`V_final` is the vertex every downstream quantity sees**.

## 3. MEASURED movement of the vertex through the chain (signal-matched candidate, official Gen2 NC-Delta; 5 cm anchoring tolerance)

| step | median movement | fraction moving > 5 cm |
|---|---|---|
| traditional -> DL-stage vertex | 0.0 cm (the DL keeps or re-selects the same graph vertex) | **38.7 %** (DL toward the true vertex in 22.9 %, away from it in 14.4 %) |
| DL-stage -> **final** (steps D + E) | **0.21 cm** | **3.8 %** (> 1 cm: 20.7 %) |

After the DL stage the vertex moves **along the photon by more than 5 cm in 1.4 %** of the separable events and against it in 2.4 %. The refinement therefore changes the vertex by a fraction of a centimetre in most events and by more than 5 cm in a few percent: it does not create or remove a 20-30 cm displacement.

## 4. What is established

* The vertex is created by the traditional PR (A), selected by the DL/geometry rerank (C) among existing graph vertices, and refit locally (D); only the pi0 displaced-vertex finder in E can relocate it by a large step.
* No stage after C moves a typical event's vertex by more than a fraction of a centimetre.

## 5. What is not

* Which of the 3.8 % large post-DL moves are `main_vertex_graph_audit` edits, a without-vertex pi0 acceptance, or a main-cluster switch: the stages are not separately recorded (the final vertex is recorded once).
* The production values of `vertex_kink_snap`, `vertex_junction_snap`, `m_pi0_bp_miss`.
