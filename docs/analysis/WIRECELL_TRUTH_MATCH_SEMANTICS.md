# Wire-Cell reco <-> truth matching: semantics established from SOURCE (T_match, T_overlap, T_truth_*), and what it changed in Phase 4

Status 2026-11-09. Everything marked **[source]** was read in code or in the matcher's own design document, with commits below; everything marked **[measured]** was checked on the BNB CV files; nothing is inferred where source exists. Phase 4 had inferred these semantics from data; the audit confirms the structure and corrects **one** rule (the top-partner ordering, section 4).

## 1. Sources and commits

| what | where | commit / sha | note |
|---|---|---|---|
| fg1 production chain (declared) | Haiwang's `fg1/README.md` (`/pnfs/.../yuhw/prod-fermigrid/fg1/README.md`, read over XRootD) | file sha256 `96bd2025…fe9d9` | chain r8: step 1 `lar wcls-img-clus-matching`, step 2 `wire-cell wct-pr.jsonnet`, step 3 merge into the CAF |
| matcher C++ (pure computation) | `HaiwangYu/wire-cell-toolkit`, branch `sbnd-wc-flatcaf`, `clus/inc/WireCellClus/TruthMatch.h` | **`4b6853d4`** (the fg1 pin; read at that commit) | `TruthMatch.h` is byte-identical at the branch tip `b6278234` |
| matcher driver, tree writers | same repo, `root/src/SbndPrTruthMatch.cxx`, `root/src/SbndPrMagnifyTrackingVisitor.cxx` (`write_truth_match`, `write_truth`) | read at `4b6853d4` and at tip `b6278234` | the 4 later commits touching these files change only per-event file naming, a `warn` instead of `debug` when `truth_track` is absent, and which shower a *shared shower segment* belongs to (`particle_id`/`kine_index`, a level-1 / `in_pf` edge case) |
| step-1 labeler (`T_truth_track`, `truth_attach`) | `HaiwangYu/larwirecell`, branch `sbnd-wc-flatcaf` | tip **`ad5d942`** = the fg1 pin (`git ls-remote`); not read line by line | its tables are documented in the design document (section 8.1) |
| matcher design / tree reference | `HaiwangYu/wire-cell-toolkit-ai-helper`, `issues/41-sbnd-reco-truth-matching/41-sbnd-reco-truth-matching.md` (sections 0.5, 2, 3.2, 8) | repo `main` `aaf9e752`; file sha256 `b3148b7d…ef125ae`; last touched in commit `0898fb8a` (2026-11-05) | the authors' own spec, consistent with the code above |
| upstream toolkit (truth tables, tagger/kine headers) | `WireCell/wire-cell-toolkit` | `2ce0940a` (HEAD 2026-11-09); `cfg/pgrapher/experiment/sbnd/docs/sbnd-2step-workflow.md` | used for `T_truth_nu`/`T_truth_pf` and for the conventions of `WIRECELL_SOURCE_CONVENTIONS_AUDIT.md` |

Not found anywhere public: the *production job configuration*; nothing here depends on it.

## 2. What a `T_match` row is  **[source: design doc 8.2, `SbndPrTruthMatch.cxx`]**

**One row = ONE object (not a pair) at one level, with up to 3 partners on the other side.** Fields:

| field | meaning |
|---|---|
| `level` | 0 cluster; 1 particle; 2 candidate defined by the `T_kine` energy-walk segments (`in_enu`); **3 candidate defined by the particle-flow-tree segments (`in_pf`)** (Matteo's definition). Phase 4 used level 3. |
| `side` | 0 = reco object, 1 = truth object |
| `obj` | index of the object within (event, level, side); partner lists name the partner's `obj` |
| `nu_index` | reco side, levels 1-3: the candidate (`T_tagger`/`T_kine` row). −1 for a cluster object and for every truth object |
| `cluster_id`, `kine_index` | reco cluster of a cluster / rest-of-cluster object; `T_kine` vector element at level 1 |
| `truth_nu_idx` | truth side: the interaction (`T_truth_nu.nu_idx`, the generator MCTruth index; also set for a prong); **−1 for a non-neutrino (cosmic) object**; −1 on the reco side |
| `truth_trackid` | truth, levels 0/2/3: −1 for an interaction, the **`bee_trackid`** of a non-neutrino object (a Michel electron is merged into its muon); level 1: the `prong_trackid` |
| `size_n`, `size_q` | the object's imaging points and charge. A reco object **counts its unlabeled points** (ghosts); a truth object counts only its *labeled reco points* (truth deposits that made no blob are absent) |
| `match_obj`, `match_iou_n`, `match_iou_q`, `match_shared_n`, `match_shared_q` | partner lists (≤ 3 = `truth_match_topk`), IoU and shared size in points (`_n`) and in charge (`_q`) |
| `nmatch`, `mutual` | partners stored; 1 if the best partner's best partner is this object |

IoU = |r∩t| / (|r| + |t| − |r∩t|). The "points" are the imaging points of the clusters (default scope), the charge is the mean wire charge over the non-dead planes of the point (reco electrons). The truth label of a point is the **dominant G4 track of its blob** (`blob.trackid`); a point whose blob has no label, or whose track has no `T_truth_track` row, is unlabeled (`trackid −1`).

Granularity per level: level 0 = whole clusters, level 1 = reco particles (a shower is the union of its segments) against truth prongs, levels 2/3 = whole reconstructed candidates against whole truth interactions or non-neutrino objects. Everything is **point- and charge-based on imaging points with blob-level truth labels**; no cluster- or shower-level shortcut exists at levels 2/3.

## 3. The answers to the questions that were open

* **How is the top match selected?** [source `TruthMatch::match`] Partners are sorted by **decreasing point IoU (`iou_n`)**, ties by decreasing `iou_q`, then by the lower partner index; at most 3 are kept; a partner needs IoU > 0 (`min_overlap = 0`, i.e. any shared point). The stored order IS the ranking: **the top match is `match_obj[0]`**. [measured on the 645 files with a selected candidate: partner order non-increasing in `match_iou_n` in every file (0 order violations over all level-3 rows of those files, which hold 4,549 level-3 candidate objects); `nmatch` equals the stored list length everywhere; maximum 3; `mutual` equals the definition in every file.]
* **Can one candidate map to several neutrinos?** Yes: the candidate's points can be labeled to several truth objects; all (up to 3) are listed. [measured: 47 of 4,549 level-3 candidates in those files overlap ≥ 2 distinct truth neutrinos.] No threshold decides which is "the" neutrino; the structural flag is kept as the MULTI_OR_AMBIGUOUS category.
* **Can one truth interaction map to several candidates?** Yes: each truth object has its own partner list. Within one candidate, points are disjoint (a point claimed by two candidates goes to the first `nu_index`; the source counts `n_claim_dup`). [measured: 6 of 4,362 claimed truth interactions are the top partner of more than one candidate of the same event.]
* **`T_match` vs `T_overlap`.** `T_overlap` rows are the *sufficient statistics*: one row per (reco piece × dominant truth track): `nu_index`, `cluster_id`, `segment_id`, `particle_id`, `kine_index`, `in_enu`, `in_pf`, `trackid` (−1 unlabeled), `nu_idx` (the track's interaction; −1 non-neutrino, −2 unlabeled), `n_points`, `q`, `n_pure`, `q_pure`. `T_match` is **computed from** `T_overlap` + `T_truth_track` by `TruthMatch::match`. The Phase-3 table's `dom_nu` (dominant shared-**charge** neutrino of the `in_enu` segments) is therefore a different object (level-2 candidate) with a different criterion (shared charge, ignoring the truth object's size) than `T_match` level 3 (`in_pf` segments, point IoU).
* **Unmatched candidate.** `nmatch == 0`: the candidate's points share no labeled point with any truth object (all its points unlabeled: ghost or labeler miss). Neutrino interactions with no reco point are written as truth rows with `nmatch == 0` (missed).
* **Truth tables.** `T_truth_nu` (one row per true neutrino interaction: `nu_idx, pdg, ccnc, mode, int_type, flavor, E, vtx_xyz, t, edep`; `edep > 0` ⇔ it has charge in `T_truth_track`). `T_truth_pf`: G4 particles from a beam neutrino with KE > 10 MeV whether or not they deposit charge (this is why π⁰ → γγ chains exist without charge). `T_truth_track`: every G4 particle of any origin with charge in the readout or dominating a blob (`nu_idx −1` cosmic), with `bee_trackid`, `ancestor_trackid`, `prong_trackid`, `q_readout`, `q_in_blobs`. [source: sbnd-2step-workflow.md section 3; design doc 8.1.]

## 4. What changed in Phase 4 and why

Phase 4 ranked the stored partners by the **largest charge IoU** (`match_iou_q`). The source ranks by the **point IoU** (`match_iou_n`); the stored partner order is that ranking. The helper `background_truth.candidate_association` now takes the first stored partner (`rule="source"`, default) and keeps the old rule as `rule="iou_q"` for comparison.

Effect on the 649 selected BNB CV candidates (`tables/background_mechanisms/t_match_source_revalidation*.csv|json`): the top partner differs for **2** candidates; the category changes for **1**:
* (file 32366, run 8060, subrun 80, evt 5): OTHER_NC → COSMIC_OR_UNMATCHED (1γ1p). Both partners are poor: charge IoU 0.096 for the old neutrino partner, point IoU 0.054 for the cosmic object that ranks first by points.
* (file 16677, run 6702, subrun 12, evt 42): the top partner changes (nu 0 → nu 1) but the candidate overlaps two distinct neutrinos either way: MULTI_OR_AMBIGUOUS before and after.

All Phase-4 totals are unchanged (649 = 14 + 635 + 0; 310 / 230 / 95); the composition moves OTHER_NC 21 → 20 and COSMIC_OR_UNMATCHED 15 → 16 (1γ1p 7 → 6 and 0 → 1); the taxonomy change count is 62 (was 61); proton migration of 1γ1p/truth-1p 157 → 156. The Phase-4 documents on this branch carry the revalidated numbers; the pushed Phase-4 branch keeps the original ones.

## 5. T_match (level 3, point IoU) versus T_overlap (dominant charge): the 3 disagreements, explained by the semantics

Same count as before: 646 of 649 passing candidates agree on the neutrino identity (`tables/background_mechanisms/association_disagreements_Tmatch_vs_Toverlap.csv`). The three disagreements are **candidates that contain two truth objects of comparable size**, where the two criteria rank them differently [measured; partner sizes read from `T_match`]:

| candidate | T_match top (point IoU) | the other partner | dominant shared charge |
|---|---|---|---|
| file 16677 ev 11 | truth nu 1: IoU_n 0.618, 998 points, shared q 4.97e6 | nu 0: IoU_n 0.353, 573 points, shared q **8.83e6** | nu 0 (charge-dominant, fewer points) |
| file 24997 ev 11 | cosmic object: IoU_n 0.567, 7,087 points | nu 0: IoU_n 0.232, 2,723 points, shared q 2.62e7 | nu 0 is a minority by points |
| file 26430 ev 4 | truth nu 1: IoU_n 0.467, 982 points | nu 0: IoU_n 0.306, 2,067 points, shared q 6.32e6 (> 5.68e6) | nu 0 by charge |

Point IoU weights every imaging point equally and penalises a truth object that is large outside the candidate; shared-charge ranking weights by charge and ignores the truth object's size (the design document states this sampling-density difference explicitly, "point counts as the weight" vs "charge too"). Both are legitimate; neither is wrong. The analysis label uses the production ranking (`T_match`, level 3), and the structural ambiguity flag (≥ 2 distinct truth neutrinos) catches two of the three as MULTI_OR_AMBIGUOUS; the third (24997) is a cosmic-vs-neutrino merge.

## 6. Shower association: `shw_sp_energy` and the T_kine row  **[source: `clus/src/NeutrinoTaggerSinglePhoton.cxx` at `4b6853d4`]**

`ti.shw_sp_energy = Eshower / MeV` is filled in the second pass **for `max_shower` only** (line 1611), where `Eshower = shower_energy(shower) = kine_best (kine_charge if kine_best == 0)` (lines 100-103). `max_shower` is the shower with the largest such energy among those with **`en20 && badreco1 && badreco3 && badreco4`** ("good"), and only if no shower is good, among those with `en20 && badreco1` ("ok") (lines 2473-2505). Consequences: (i) the selected shower is the highest-energy shower **among the ones passing the bad-reconstruction flags**, not necessarily the highest-energy shower of the candidate; this is exactly why Phase 4 measured the leading `T_kine` shower to be the `shw_sp` shower in 96.4 % (623/646) and not 100 %, and the energy-equality row mapping used in `SELECTED_SHOWER_TRUTH_MATCH_AUDIT.md` is the correct mapping; (ii) `shw_sp_20mev_showers` / `shw_sp_br1_showers` are per-shower 0/1 flags in loop order, not indices (lines 2473-2482), as Phase 4 found; (iii) `shw_sp_n_20mev_showers` and `shw_sp_n_20br1_showers` count `en20` and `en20 && badreco1` over all showers of the candidate. The 3 candidates without an energy-equal row remain unexplained by this reading and stay flagged (see `QUESTIONS_FOR_HAIWANG_HANYU.md`).

## 7. Interpretations checked and found right / still analysis joins

* Right: level 3 + side 0 = whole reconstructed candidate (PF-tree definition); `truth_nu_idx ≥ 0` interaction; `−1` with `truth_trackid > 0` cosmic/non-neutrino object; `mutual`; `nmatch` ≤ 3; the stored partner order.
* Wrong: the *ranking* of partners by charge IoU (fixed, section 4).
* Analysis joins that are **not** source facts: the link `T_truth_nu.nu_idx → rec.mc.nu` index is done by nearest vertex (max distance 2.7e-5 cm, none unlinked); the source only says `nu_idx` is "the generator MCTruth index". It is a validated join, not a documented identity.
* Edge case not exercised: at later commits a shared shower segment's `particle_id` is settled by its `T_kine` row (affects level-1 particle matching and the `in_pf` flag of a few shared segments); the fg1 files predate that commit. The candidate-level association is unaffected except possibly for such shared-segment points.
