# Why is a true signal proton not a proton-typed row? Reconstructed-type confusion, KE dependence, high-KE mis-typing and low-KE merging

Date: 2026-11-11. Branch `analysis/ncdelta-particle-pid-audit-20261111`. **Characterisation only**: no selection, BDT threshold, proton-threshold optimisation, FV, PID or reconstructed-type change. Roadmap item **X** (with the photon side in `SIGNAL_PHOTON_PID_FAILURE_AUDIT.md`). Companions: `WIRECELL_PARTICLE_PID_SOURCE_AUDIT.md`, `PROTON_RECONSTRUCTION_TRUTH_ASSOCIATION.md` (Phase 10, bookkeeping reused unchanged). Tables: `tables/particle_pid_audit/proton_*.csv`, `high_ke_*.csv`, `cross_confusion.csv`; figures fig2, fig4, fig5, fig7, fig8, fig10; row-level products in `$SP_DATA/particle_pid_audit/official_ncdelta/` (outside Git).

Tags: **SOURCE**, **MEASURED**, **NOT AVAILABLE**.

## 1. Scope

Official Gen2 NC-Delta, provisional TPC box, frozen chain, no FV, no proton threshold *choice* (the KE bins below are reporting bins, not a selection). The truth association is the source-ranked `T_match` level-1 partner (Phase-10 `row_matches`).

## 2. Proton truth denominator  (MEASURED; `proton_denominator.csv`)

| | protons |
|---|---|
| signal primary protons, all KE (post-FSI, official Gen2 NC-Delta) | 20,023 |
| **KE > 35 MeV (the Phase-10 denominator, unchanged)** | **8,132** |
| of which with a signal-matched candidate | 7,347 |
| KE <= 35 MeV | 11,891 |

**Class of a true proton** (Phase-10 bookkeeping, signal-matched candidate): *proton-typed* (a row typed 2212 whose top partner is this proton; a proton-typed row wins if there are several), otherwise the type of the top row (*mu / pi / e-shower / e-track / other typed*), *merged / subdominant partner* (the proton is only the 2nd or 3rd partner of some row), *no row*, *no signal-matched candidate*. **Reproduction of Phase 10 at KE > 35 MeV is exact**: proton-typed 3,765 (= 3,558 single + 207 multiple), merged 1,320, non-proton top row 1,406 (778 e-shower + 441 mu + 186 pi + 1 e-track), no row 856 (= 854 + 2 other-candidate-only), no signal-matched candidate 785.

## 3. Reco-type confusion  (MEASURED; `proton_confusion.csv`, fig2)

KE > 35 MeV (8,132): **proton-typed 46.3 %**, merged / subdominant 16.2 %, e-shower-typed 9.6 %, no row 10.5 %, no signal-matched candidate 9.7 %, mu-typed 5.4 %, pi-typed 2.3 %.

| true KE [MeV] | n | proton-typed | mu | pi | e-shower | merged | no row | no sig. cand. |
|---|---|---|---|---|---|---|---|---|
| 0-35 | 11,889 (two protons with KE = 0 fall outside the bins) | 5.3 % | 0.3 | 0.3 | 3.1 | 7.7 | **67.9** | 15.5 |
| 35-50 | 1,502 | 23.2 | 3.6 | 1.7 | 7.3 | **33.8** | 17.2 | 13.2 |
| 50-100 | 2,375 | 44.3 | 3.7 | 2.1 | 12.3 | 18.5 | 7.6 | 11.5 |
| 100-200 | 1,992 | 54.9 | 1.7 | 0.9 | 12.4 | 9.5 | 12.1 | 8.5 |
| 200-300 | 1,003 | **67.3** | 3.4 | 1.7 | 5.3 | 6.4 | 9.6 | 6.4 |
| 300-500 | 887 | 57.8 | **13.4** | 2.4 | 5.7 | 7.7 | 6.4 | 6.4 |
| > 500 | 373 | **22.0** | **30.0** | **14.7** | 6.4 | 14.2 | 6.4 | 6.2 |

The efficiency to be proton-typed rises to a **maximum of 67 % at 200-300 MeV** and collapses above 300 MeV; 0-35 MeV protons are mostly not reconstructed as rows (68 % no row), and the 35-50 MeV bin loses a third to merging.

## 4. Persisted PID inputs of the top rows  (`proton_pid_inputs.csv`, fig4, fig5)

Per KE bin and reconstructed type: key-segment length, fit points, segment count, vertex attachment, shower-row fraction, `E_reco / E_true`. Source-relevant facts (SOURCE: a track's KE is the range energy of the assigned type for >= 4 cm, so the type fixes the energy):

* **e-shower-typed true protons** (9.6 %) are shower *objects* (100 % shower rows), short (median key segment 8 cm at 300-500 MeV), `E_reco / E_true` 0.13 / 0.06 (300-500 / > 500 MeV); only 47 % at the main vertex.
* **mu / pi-typed protons** are single track segments at the main vertex (mu 85-91 %, pi 79-100 %).

## 5. High-KE mis-typing (> 500 MeV)  (MEASURED; `high_ke_*.csv`, fig8)

373 protons: **proton-typed 82 (22.0 %), mu-typed 112 (30.0 %), pi-typed 55 (14.7 %), e-shower 24 (6.4 %), merged 53 (14.2 %), no row 24, no signal-matched candidate 23.** Among the 273 that have a typed top row, the proton type is chosen for **30 %**, muon **41 %**, pion **20 %**, electron shower **9 %**.

| > 500 MeV, top row typed | rows | key-segment length (median, cm) | fit points | true straight-line path (median, cm) | `E_reco / E_true` | at main vertex | true end within 10 cm of a face | >= 2 top rows |
|---|---|---|---|---|---|---|---|---|
| proton | 84 | **123** | **206** | **122** | **0.93** | 96 % | 10 % | 16 % |
| muon | 119 | 47 | 80 | 66 | **0.21** | 91 % | **32 %** | 12 % |
| pion | 67 | 50 | 84 | 55 | **0.19** | 93 % | 5 % | 4 % |
| e-shower | 38 | 8 | 15 | 21 | 0.06 | 47 % | 46 % | 0 % |

(true KE medians 565 / 640 / 708 / 625 MeV for proton / muon / pion / e-shower: all above 500 MeV.)

**What distinguishes them in the persisted inputs:** a correctly typed > 500 MeV proton is a long object (123 cm, 206 fit points) whose type came out proton; the muon / pion typed ones are **objects 2-2.5x shorter** (47-50 cm, 80-84 fit points) *with the same true KE*, and the reconstructed length matches the *true* straight-line extent of the proton (reco-to-true path ratio median 1.0-1.02 in every class): **these protons really are short tracks**. A high-KE proton with a short true track does not stop in the object: it either **leaves the active volume** (32 % of the muon-typed end within 10 cm of a face, against 10 % of the proton-typed) or **ends inside the volume** (68 % of the muon-typed end more than 10 cm from a face, 95 % of the pion-typed; consistent with an inelastic hadronic interaction, but the end process is not persisted, so this is the consistent reading, not a measured fact). Either way **the object contains no stopping Bragg peak**, and the dQ/dx-template competition of the source (last 35 / 15 cm, muon default, proton wins only on a strictly smaller score) has nothing to select the proton template with: it is the muon default or a MIP-like flat dQ/dx. This is a source-logic reading supported by the persisted lengths; **the dQ/dx vectors themselves are not persisted**, so the template scores cannot be checked.

* **MIP-like dQ/dx**: plausible and consistent, **not measurable** (NOT AVAILABLE).
* **Secondary interactions break the object**: partially: 12 % of the muon-typed have >= 2 reconstructed rows with the proton as top partner (16 % of the correctly typed) — the splitting rate is *not* higher for the mistyped ones.
* **Pion label**: 93 % of the pion-typed are at the main vertex, 27 % have a muon-typed sibling there (16 % a longer one): the arbitration rule (every non-longest muon candidate becomes a pion) accounts for part of them, not all.
* **Consequence:** the reconstructed energy of the mistyped ones is **0.2 of the true KE** (the range energy of a short muon/pion track), which also explains their *below-threshold* reconstructed energies in the Phase-10 migration.

## 6. Low-KE merging  (MEASURED; `proton_merge_*.csv`, fig7)

2,236 protons (all KE) are only a subdominant (2nd / 3rd) partner of a reconstructed row. What they merge into = the truth of that row's dominant partner:

| true KE [MeV] | n | another signal proton | signal photon | other |
|---|---|---|---|---|
| 0-35 | 915 | 58.6 % | 38.8 % | 2.6 % |
| 35-50 | 507 | **67.5 %** | 30.6 % | 1.9 % |
| 50-100 | 439 | 49.2 % | **47.8 %** | 3.0 % |
| 100-200 | 189 | 34.4 % | **60.8 %** | 4.8 % |
| 200-300 | 64 | 65.6 % | 28.1 % | 6.3 % |
| 300-500 | 68 | 76.5 % | 17.6 % | 5.9 % |
| > 500 | 53 | 69.8 % | 17.0 % | 13.2 % |

Dominant row types of the merged protons: proton-typed 42 %, e-shower 40 %, pion 11 %, muon 7 %; median overlap (point IoU of the dominant partner) 0.62 [0.36, 0.85], median distance of the dominant object's start from the true vertex 2.7 cm [0.7, 36] cm, median dominant energy 117 MeV, key segment 7.8 cm.

**What the low-KE 1p -> 0p migration is** (KE > 35 MeV, truth-1p events: 554 merged protons): they merge into the **signal photon in 361 (65 %)**, into "another signal proton" in 156 (28 %; for a truth-1p event another proton can only be a Geant4 secondary or a sub-threshold primary), into a non-proton signal hadron in 22, other signal EM in 14, a cosmic / other-neutrino object in 1. For truth >= 2p: another proton 598 of 766 (78 %), photon 158 (21 %). So **the lost low-KE proton of a 1p event is a proton whose charge sits inside the photon's reconstructed object** (and, at 35-50 MeV, whose points are shared with a neighbouring proton row), not a proton typed as something else; this refines Phase 10 (which saw "subdominant" without the destination). Merged protons are close to the vertex (median 2.7 cm), as expected for a proton emerging at the interaction point next to a vertex-attached photon shower.

## 7. dQ/dx / length dependence  (fig5)

dQ/dx axes are **NOT AVAILABLE**. fig5 shows the available axes (key-segment length against reconstructed row energy) with only the **source length thresholds** that exist (1.5, 4, 10, 20 cm). For tracks >= 4 cm the reconstructed energy is a pure function of length and assigned type (the lines in the figure): a proton typed muon lands on the muon-range curve, a factor ~3-5 below the proton curve at the same length. No new threshold is derived.

## 8. Effect on the topology migration and the frozen selection

By truth topology (KE > 35 MeV; `proton_pid_by_topology.csv`): proton-typed **50.4 %** (truth 1p) vs **37.4 %** (>= 2p), merged 10.0 % vs **29.7 %**, e-shower-typed 11.6 % vs 5.2 %, mu / pi 8.5 % vs 6.0 %; Delta0 vs Delta+: proton-typed 41.9 % vs 48.6 %, merged 20.6 % vs 14.0 %. The >= 2p loss is dominated by **merging into a neighbouring proton** (a second proton overlapping the first at the vertex), the 1p loss by the **e-shower typing (11.6 %), no row (9.1 %) and no signal-matched candidate (10.4 %)**, the high-KE tail by mu / pi typing. These are the reco-0p/1p/>=2p migration reasons of Phase 10, now with their reconstruction mechanism.

## 9. What is established

* Proton-typing efficiency is **46 % above 35 MeV, 67 % at its best (200-300 MeV) and 22 % above 500 MeV**; above 500 MeV the dominant mistakes are muon (30 %) and pion (15 %) typing.
* The high-KE mistyped protons are **short objects** (true and reconstructed extent 55-66 cm against 122 cm for the correct ones) with no stopping peak inside: the source's template competition defaults to muon, and the typed energy is 0.2 of the truth.
* The low-KE loss is **merging into the signal photon (65 % for truth-1p) or a neighbouring proton**, not mis-typing.

## 10. Open questions

* The dQ/dx vector, template scores and `start_n` / `end_n` are **not persisted**: the claim "no Bragg peak, so muon default" is a source-logic reading supported by lengths, not a reproduced template decision. Producer-side per-segment dQ/dx median and the three template scores would settle it.
* The true end process of the protons (inelastic interaction vs exit) is not in the derived tables.
* The production values of the knob-gated PID options (not audited).
