# How Wire-Cell assigns a reconstructed particle type: source audit of the track / shower / PDG / shower-set decisions

Date: 2026-11-11. Branch `analysis/ncdelta-particle-pid-audit-20261111`. Audit only: no PID, selection, threshold or type is changed. Tags: **SOURCE** (read in code), **MEASURED** (persisted products, `tables/particle_pid_audit/`), **NOT AVAILABLE** (a source input that is not persisted: stated, never approximated).

**Source:** `HaiwangYu/wire-cell-toolkit`, branch `sbnd-wc-flatcaf`, **commit `4b6853d4`**, every file read with `git show 4b6853d4:clus/src/<file>` (not the checked-out review tree). Files: `PRSegmentFunctions.cxx` (PSF), `NeutrinoTrackShowerSep.cxx` (NTSS), `NeutrinoVertexFinder.cxx` (NVF), `NeutrinoPatternBase.cxx` (NPB), `NeutrinoShowerClustering.cxx` (NSC), `NeutrinoKinematics.cxx` (NK), `NeutrinoTaggerSinglePhoton.cxx` (NTSP); the tree writer `UbooneTaggerOutputVisitor.cxx:211-300` for `T_segment`. The production job configuration is **not public and not audited**: every knob-gated rule below is described with its source default (off), and the data are the only evidence of what ran.

## 1. Three different things (kept separate throughout)

| | what it is | where decided | persisted as |
|---|---|---|---|
| **A. track vs shower (segment level)** | a PR-graph *segment* is flagged shower-trajectory or shower-topology | `segment_is_shower_trajectory` (PSF:2219: length <= 50 cm, per-10-cm sections with `0.11 x median dQ/dx/MIP + 2 x straightness < 2.03`, `median < 2 MIP`, `straightness < 0.95`, ...) and `segment_is_shower_topology` (PSF:4126: transverse RMS of the associated-point cloud, `max_spread` / `large_spread_length` cuts, 0.4-1.0 cm) | `T_segment.flag_shower` |
| **B. PDG / type** | the particle information of the segment (`pdg`) | track segments: `segment_determine_dir_track` (PSF:2923); shower-topology segments: unconditional 11 (NTSS:296-322); shower-trajectory segments: 11 unless the track PID says electron (PSF:3195) ; then the re-typing rules of section 3 | `T_segment.pdg`, `T_kine.kine_particle_type` |
| **C. entry into the single-photon shower set** | the `Shower` object (a cluster of segments around a start segment) is in the main vertex's shower set, typed electron, E > 20 MeV | `NTSP:2395-2505` (`en20 && electron && main-vertex set`) | `T_tagger.shw_sp_*` |

* **A is not B.** MEASURED: of 68,351 shower rows (`kine_particle_is_shower == 1`, all candidates) **57,450 (84 %) have a key segment that is NOT flagged shower**. A `T_kine` shower row is a `Shower` *object* built by the shower clustering around a *start segment*; the row's type is that start segment's PDG (`shower_kine_pdg`, NK:214-222; cached type unless `kine_shower_pdg_live`). So **13,047 shower rows are typed muon / pion / proton** and 55,303 electron: a "shower" with a track-typed start segment.
* **B is not C.** An electron-typed object can sit outside the main-vertex shower set (the Phase-9 state `photon_shower_not_in_main_vertex_set`), and a muon/pion-typed shower never enters it (the tagger examines only `pdg == 11` showers, NTSP:2418).
* The row type agrees with the key segment's persisted PDG in 82,969 of 83,097 rows (99.85 %; the 128 others are rows whose segment has no particle info: `pdg` 4).

## 2. The track PDG decision (SOURCE; PSF:2582-3100)

For a track segment the PID input is the **dQ/dx vector along the fitted segment** (internal units), the segment length, the vertex degrees `start_n` / `end_n` (number of segments at each end in the PR graph) and the fit-point count:

1. **Template competition** (`segment_do_track_pid`, PSF:2704-2887; `do_track_comp`, PSF:2582): the last 35 cm and, if that abstains, 15 cm of dQ/dx are compared, in the forward **and** backward direction, with the muon, proton (and, only if `length < 20 cm`, electron) dE/dx templates and with a constant MIP, by a KS-like distance plus a sum ratio. **Muon is the default**; proton wins if its score is strictly smaller; electron only if strictly smaller still and the segment is shorter than 20 cm (PSF:2737-2758). The direction metric (muon-vs-flat) decides forward / backward; if both fail and `flag_force` is false the function abstains.
2. **When it is called**: if `npoints >= 2`; with both ends free (`start_n == 1 && end_n == 1`) and `npoints >= 15` the decision is **forced** (`flag_force`), otherwise it may abstain (PSF:2982-3023). Knob-gated extras (endpoint trim retry, proton direction vote) are off by default.
3. **Fallback** if the template PID returned pdg 0: median dQ/dx > 1.75 MIP -> proton; < 1.2 MIP -> muon; < 1.5 MIP and length < 4 cm -> muon (PSF:3053-3061).
4. **Electron rules** (PSF:3064-3071): an electron-typed track with both ends occupied, or a direction pointing into an occupied end, gets `dir_weak` and `dirsign 0`, and **becomes a muon if its score < 0.15**.
5. **Short vertex segments** (PSF:3077-3093): length < 1.5 cm with one free end and the other end of degree > 2 -> proton (> 1.75 MIP) or **pion** (< 1.2 MIP).
6. **Bad score -> shower** (PSF:3096-3100): length > 10 cm and 1 < score < 100 -> electron, score 200, `dirsign 0`.
7. **Kinetic energy** (`segment_cal_4mom`): range-based (`cal_kine_range` with the range function of the *assigned* type) for a track >= 4 cm, dQ/dx-integrated otherwise (`RECO_PROTON_ROW_SEMANTICS.md`). **A type error therefore changes the energy**: a proton typed muon gets the muon range energy.

## 3. Re-typing after the segment PID (SOURCE)

* **Main-vertex muon / pion arbitration (NVF:1956-2102), unconditional:** among the pdg-13 segments at the main vertex, only the **longest whose far end has no proton neighbour** stays muon; **every other pdg-13 segment at that vertex is re-typed pion (211)**. This is a topological label, independent of dQ/dx. MEASURED: of 11,110 candidates with a non-shower segment at the main vertex, **6,427 have no muon-typed segment, 4,663 exactly one and only 20 two or more** (the long-muon chain exception), while **4,551 pion-typed segments sit at the main vertex** (57 % of all 7,949 pion-typed non-shower segments); 2,540 of them (56 %) have a muon-typed sibling there, 2,080 (46 %) a muon sibling at least as long. So arbitration explains a large share of pion typing at the vertex but **not all**: the rest comes from the proton-neighbour rules or the short-segment rule (only 869 pion-typed segments, 11 %, are shorter than 1.5 cm).
* **Proton-neighbour re-typing (NVF:1820-1862, 2038-2066):** a pdg-0 segment whose far vertex carries a proton: median dQ/dx / MIP > 1.3 -> proton, else pion; an in-shower daughter next to a proton-typed segment is re-examined (ratios 1.3 / 1.4).
* **Topology rules, knob-gated (default off, production values NOT AUDITED):** proton-daughter pion and muon-at-multi-proton-vertex pion (NPB:342-470), the A5 hadronic shower tag that stamps a shower's start segment pion (NSC:9772-9981), the pi0 incoming-track stamp (NSC:8176).
* **Electron force-typing sites** (NSC:1037, 1335, 1812, 4493, 5103): showers accepted by the shower clustering have their start segment written pdg 11, with knob-gated guards that decline the write for confident proton/muon template scores.

## 4. The single-photon shower set (SOURCE; NTSP:2395-2505)

Only `Shower` objects whose start segment is **electron-typed** are counted; `shw_sp_n_20mev_showers` additionally needs `E > 20 MeV` and membership of the main vertex's shower set; the selected shower is the highest-`kine_best` shower among those passing the 20 MeV, br1, br3, br4 conditions (`PI0_PAIR_CONSTRUCTION_SOURCE_AUDIT.md` section 4).

## 5. What is persisted, what is not  (MEASURED / NOT AVAILABLE)

| PID input | persisted? |
|---|---|
| segment `pdg` (live, final), `flag_shower`, `length_cm` (fit path), `n_fit`, `dirsign` (FINAL), `ke_mev`, start / end vertex ids (vertex degree derivable), `shower_id` | **yes** (`T_segment`; `n_fit` and `dirsign` read by the targeted Phase-15 scan, 256,295 rows, matching Phase 9 exactly) |
| row type, shower flag, pool, energy, number of segments, cluster | yes (`T_kine`) |
| per-segment **dQ/dx vector** and its median | **NOT AVAILABLE** (only tagger-level dQ/dx of the *selected electron shower* and the MIP-track quantities exist, so no dQ/dx exists for a muon / pion / proton typed object) |
| template scores (muon / proton / electron), `particle_score` | **NOT AVAILABLE** |
| `start_n` / `end_n` *at PID time*, `dirsign` at PID time | not available; the final graph's degrees are derived, and the **final `dirsign` is non-zero for 99.97 % of non-shower segments**, so it carries no information about a PID abstention |
| shower direction, `get_kine_charge` | NOT AVAILABLE |
| production values of the knob-gated PID options | NOT AUDITED |

**Consequence:** the decisive PID observable (dQ/dx along the segment) is not in the flatCAF. Everything below that follows the source *logic* (length, vertex attachment, arbitration, range-energy dependence on the assigned type) is checked against persisted inputs; the dQ/dx-template outcome itself cannot be reproduced or examined. A producer-side addition (per-segment median dQ/dx, the three template scores, `start_n` / `end_n` and the dQ/dx-template direction flag of `T_segment`) would close roadmap items S and X completely.

## 6. Source-versus-data checks  (`tables/particle_pid_audit/source_vs_data_checks.csv`)

* One muon per main vertex (above): holds (20 of 11,110 exceptions).
* The pion rule is mostly topological: 79-100 % of pion-typed objects of every kind (photon pieces, true protons) sit at the main vertex; the pion-like dominant photon objects have a median key-segment length of 15 cm and a median of 8 segments (they are shower objects around a pion-typed start segment, not short vertex stubs).
* Muon-typed objects at the main vertex never have a muon-typed sibling there (0.00 in every proton KE bin): they are the arbitration *winners*.
* Template electron needs `length < 20 cm`; electron-typed non-shower segments have a final dirsign of 0 in only 0.03 % of cases (the weak-direction rule's effect is overwritten by the later direction stages).

## 7. What is established

* The type of a track object is decided in four layers: dQ/dx template (muon default) -> median fallback -> short-segment vertex rule -> main-vertex **topological** muon/pion arbitration; a shower object inherits its start segment's type; the single-photon stage then needs an electron-typed object in the main-vertex shower set.
* "Muon-like" and "pion-like" are not both dQ/dx statements: **pion is mostly the label of a non-longest muon candidate at the main vertex**.

## 8. What is not

* The dQ/dx / template-score level (not persisted); the production knob values; whether a given mis-typed object lost the template competition or was re-typed afterwards, when no persisted input separates the two.
