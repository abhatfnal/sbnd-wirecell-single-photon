# Shower-to-vertex ownership: what must be true for a reconstructed electron shower to enter `shw_sp_n_20mev_showers`, and how a good shower can miss the main-vertex shower set

Date: 2026-11-11. Branch `analysis/ncdelta-shower-attachment-vertex-provenance-20261111`. Audit only. Tags: **SOURCE** (commit `4b6853d4`, `git show 4b6853d4:clus/src/<file>`), **MEASURED**, **NOT AUDITED**. Files: `NeutrinoShowerClustering.cxx` (NSC), `NeutrinoTaggerSinglePhoton.cxx` (NTSP), `MultiAlgBlobClustering.cxx` (MABC, PF-tree writer), `PRShower.h`.

## 1. What a shower is and what "start vertex" means  (SOURCE)

A `Shower` is a set of PR-graph segments around a **start segment**, with a **start vertex** and a **connection type** (`PRShower.h:57`): **1 = direct connection, 2 = indirect connection with a gap, 3 = association (another cluster, nearest candidate vertex <= 80 cm), 4 = not clearly connected (> 80 cm)**. `update_shower_maps` (NSC:403-446) builds the **vertex -> shower map `map_vertex_to_shower[start_vertex]`**: a shower is keyed under its **start vertex**, nothing else.

## 2. The condition for `shw_sp_n_20mev_showers`  (SOURCE: NTSP:2353-2505)

The single-photon tagger loops over **`map_vertex_to_shower[main_vertex]`** only (`mv_it->second`; if the main vertex has no entry the tagger returns false). For each shower:

1. its **start vertex is the main vertex** (by construction of the loop; a shower whose start vertex is any other vertex is never examined);
2. its **start segment is electron-typed** (`pdg == 11`; `if (pdg != 11) continue;`, NTSP:2418);
3. its energy `kine_best` (or `kine_charge` if zero) is **> 20 MeV** (`en20`).

`shw_sp_n_20mev_showers` counts showers satisfying 1-3; the selected shower additionally passes the br1 / br3 / br4 conditions. So **a perfectly reconstructed electron shower of 200 MeV is invisible to the tagger if its start vertex is not the main vertex.**

## 3. How a shower gets its start vertex  (SOURCE: `shower_clustering_with_nv`, NSC:8810-10376)

Stage order: `shower_clustering_with_nv_in_main_cluster`, `shower_clustering_connecting_to_main_vertex`, `shower_clustering_with_nv_from_main_cluster`, `shower_clustering_with_nv_from_vertices`, `calculate_shower_kinematics`, `examine_merge_showers`, `shower_clustering_in_other_clusters`, `calculate_shower_kinematics`, `examine_showers`, then (knob-gated) `em_collinear_merge`, `em_start_backext`, `shower_split`, then **the two pi0 finders** (`id_pi0_with_vertex`, `id_pi0_without_vertex`; `PI0_PAIR_CONSTRUCTION_SOURCE_AUDIT.md`).

* **Breadth-first builder from the main vertex** (NSC:880-900): starting at a vertex, every adjacent segment that is shower-like (**`kShowerTrajectory` or `kShowerTopology` or `abs(pdg) == 11`**) or in the long-muon chain seeds a `Shower` with `set_start_vertex(parent_vtx, 1)` where **`parent_vtx` is the end of that segment away from the vertex being walked**. The shower is directly connected (type 1) to the vertex at its **upstream end**, which is the main vertex only if the shower segment touches it; a shower whose upstream end is the far end of a (proton / muon / pion typed) track is owned by *that* vertex. Type-1 sites at the main vertex itself: NSC:1196, 4243, 5058.
* **Other clusters** (NSC:2205-2236, 3780-4114): a shower in another cluster is created at the nearest candidate vertex with **type 2** (a gap), or **type 3 / 4** (association; 4 beyond 80 cm).
* **Pi0 pairs** (NSC:7998-8009, 8763): both members of an accepted pair are **re-seated at the pair vertex with type 2**; if the pair vertex is not the main vertex the members leave the main-vertex set.

## 4. How the PF tree shows it  (SOURCE: MABC:1885-2500)

The PF tree writer attaches each shower to its parent (track segment, other shower, or root): **type 1 = a shower leaf nested directly under the parent**; **type 2 / 3 = a pseudo-gamma node inserted between parent and shower**; a pi0 pair is rendered as a pseudo-pi0 node with pseudo-gamma children (`MABC:2374-2500`). So **a pseudo-photon wrapper above a shower marks an indirect (type 2/3) connection**, and the *real* ancestor is the object whose end the shower hangs from. Phase-9's `pf_state` was validated against the tagger's `shw_sp_shw_vtx_dis` on this basis; this phase uses the same persisted structure (`T_pf`).

`T_kine`'s pool and `included` give a second persisted marker: pool-2 rows are leftover showers (connection type <= 3), `kine_energy_included == 3` exactly when the connection type is 3.

## 5. Why an otherwise good shower can fail main-vertex membership  (SOURCE, summarised)

1. **Ownership by the upstream vertex** (builder): the shower attaches to the vertex at its upstream end; if a hadron-typed track lies between the main vertex and the shower, the shower belongs to the track's far vertex.
2. **Indirect connection** (type 2 / 3): a gap between the shower and the graph; the shower is anchored to the *nearest candidate vertex*, not necessarily the main vertex.
3. **Pi0-pair membership**: the pair vertex becomes the start vertex.
4. **Object-type inheritance**: the start segment's type decides the type of the whole shower (`WIRECELL_PARTICLE_PID_SOURCE_AUDIT.md`), so a photon piece with a proton-typed start segment is a proton-typed "shower" and a hadron-like parent in the PF tree even though its truth is a photon piece.
5. **Different candidate / cluster**: only the main vertex's own set is read.

Which of these happens in the signal sample is measured in `SIGNAL_PHOTON_SHOWER_ATTACHMENT_AUDIT.md`.

## 6. What is not established

The production values of the knob-gated EM merge / split / back-extension steps; the connection type of a given shower is not persisted (the PF structure, pool and `included` are proxies).
