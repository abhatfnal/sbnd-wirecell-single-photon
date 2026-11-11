# What forms the pi0-like pair that rejects genuine single-photon events at ncpi0? Pair recovery, member truth, and what is (not) established

Date: 2026-11-11. Branch `analysis/ncdelta-pi0-pair-fragmentation-audit-20261111`. **Characterisation only**: no cut, threshold, BDT, FV, proton-policy or candidate-policy change; nothing is optimised. Roadmap item **Y**. Companion documents: `PI0_PAIR_CONSTRUCTION_SOURCE_AUDIT.md` (source), `SIGNAL_PHOTON_FRAGMENTATION_CLOSURE.md` (roadmap U). Tables: `tables/pi0_pair_fragmentation_audit/`; figures `plots/pi0_pair_fragmentation_audit/fig1-fig10`; row-level products in `$SP_DATA/pi0_pair_fragmentation_audit/official_ncdelta/` (outside Git).

Tags: **SOURCE** (read in code), **MEASURED** (this phase), **POLICY** (a choice of this audit, not a fact).

## 1. Scope and fixed convention

Official Gen2 NC-Delta, provisional TPC truth box, frozen BDT thresholds, candidate policy `any` (the **controlling candidate** of an event is the Phase-12 one: for the 2,781 events it is the single reaching candidate in all but 2 events), no analysis FV, frozen reconstruction as produced. No Phase-13 FV / proton / candidate policy enters. Truth association is the **source-ranked `T_match` partner** of each reconstructed particle row (point IoU, then charge IoU, then object index; the stored `match_obj[0]`); no charge-IoU ranking. Truth classes use `rec.mc` through `T_match` / `T_truth_nu` only; no e+/e- conversion ancestry is invented.

## 2. ncpi0 population accounting  (MEASURED)

| | events |
|---|---|
| entering ncpi0 | **2,781** |
| passing | **1,313** |
| rejected | 1,468 |
| rejected, finite score | **1,465** (the population of the SHAP study) |
| rejected, non-finite score | **3** |
| passing, non-finite | 0 |
| closure | 2,781 = 1,313 + 1,465 + 3 (exact) |

The three non-finite events (files 2443 ev 1, 4666 ev 0, 5633 ev 0) are all **kine-pair events (flag 1) with `kine_pio_angle = NaN`**; the other eleven pair inputs are finite, so the BDT score is non-finite and the event fails the `> -0.05` comparison (the known non-finite `kine_pio` case; `BDT_EVALUABILITY_AUDIT.md`). Files: `ncpi0_population.csv`, `ncpi0_nonfinite_events.csv`.

## 3. Pair builders  (SOURCE; full detail in `PI0_PAIR_CONSTRUCTION_SOURCE_AUDIT.md`)

* **`kine_pio_*`** = the shower pair with the **largest `E1 + E2`** among all pairs of the candidate's pool, **no mass requirement** (flag 1; flag 2 = overridden by the without-vertex finder). Pool: shower objects, `abs(pdg) != 13`, at least one member detached (not both attached at the vertex).
* **`shw_sp_pio_*`** = the accepted **mass-window pair** (100-160 MeV with-vertex, 65-185 MeV without-vertex) that contains the tagger's selected electron shower.
* Neither stores the pair members. The two pairs are **overlapping in inputs but different objects**.

## 4. Pair recovery and validation  (MEASURED)

**Method (POLICY, forced by what is stored).** Not stored per row: the shower direction and `get_kine_charge()`. Stored per row: `kine_best` (equal to the charge energy exactly when `kine_energy_info == 2`). So a member is identified as follows:
1. **Energy signature:** a stored pair energy equals a shower row's energy (relative tolerance **1e-5**, the float32 round trip). Of 3,261 exactly matched members, 3,258 have `kine_energy_info == 2`, as the source predicts.
2. **Elimination:** a member with no matching row must be a shower row with `info != 2` (its charge energy differs from the stored `kine_best`).
3. **At-least-one-detached-member rule** (pool-2 row), a source rule that is *checked*, not assumed: of the 1,580 pairs identified purely by energy, **0** violate it. It resolves 52 kine events that would otherwise be ambiguous and removes the only configuration of 6 kine events (they become `unresolved`).
4. **Stored-distance geometry:** the particle-flow start points of the members must reproduce `dis_1`, `dis_2` (exactly when one member sits at the vertex, `dis = 0`; otherwise the triangle inequality). Configurations that contradict the stored distances are removed; if all contradict, all are kept and the event is flagged.

All consistent configurations are kept and **nothing is chosen among those that remain**; a truth property that differs between configurations is reported `indeterminate`.

| pair | present | unique by energy (both members) | unique by elimination (+ geometry) | unique by geometry | ambiguous | unresolved |
|---|---|---|---|---|---|---|
| `kine_pio` | 1,952 | **1,318 (67.5 %)** | 308 -> 312 | 99 | 294 -> **191 (9.8 %)** | **32 (1.6 %)** |
| tagger-side | 271 | **262 (96.7 %)** | 2 | 1 | 7 -> **6 (2.2 %)** | 0 |

"Unresolved" = a member is not a stored shower row (or has `info == 2` but no energy match); "ambiguous" = several admissible leftover rows.

**Validation, separated into what is independent and what is not (`pair_recovery_validation.csv`):**
* The energies are reproduced exactly **by construction**: they are the identification criterion, not a validation.
* **Independent checks that pass:** (i) distances: of 1,220 kine and 264 tagger pairs whose geometry is testable, **1,198 / 1,220 (98.2 %) and 263 / 264** reproduce the stored distance to **< 1e-3 cm** (median residual 1e-6 cm); the rest are 22 and 1 events with a different vertex convention (31 kine events are flagged `geometry_inconsistent`; the largest residual is 273 cm); (ii) the tagger-selected electron shower is a member in **262 / 262**; (iii) the detached-member rule 1,580 / 1,580; (iv) the 168 type-1 tagger masses lie in 100.2-159.4 MeV (source window 100-160).
* **Not reproducible:** theta, phi, the opening angle and the pair mass **cannot be recomputed** (they need shower directions that are not stored). The stored mass differs from `sqrt(4 E1 E2 sin^2(angle/2))` by < 1 MeV for 1,293 of 1,946 kine events (median 0.004 MeV), the rest by more because the stored mass uses the earlier directions (source section 3). **The maximum stored-vs-recomputed discrepancy of the mass relation is 549 MeV; of the distances 273 cm.**
* **Row-level object map** (`ncpi0_row_truth_class.parquet`, 13,991 rows of the controlling candidates): T_kine row (type, pool, `included`, energy, cluster, nseg), PF node (depth, start point; 66.8 % of the rows have one), source-ranked partner and truth class, dominant-photon flag, pair membership. Shower direction is not available.

## 5. Does the pair contain the signal photon?  (MEASURED; `pair_membership.csv`)

A reconstructed row is **a signal-photon row** if its source-ranked `T_match` partner is the signal photon's prong (the labeler merges the conversion daughters into it); it is the **dominant** one if it is the Phase-9 dominant reconstructed photon object, else a **fragment**.

| `kine_pio` pair | all (2,781) | ncpi0 accepted (1,313) | ncpi0 rejected (1,468) |
|---|---|---|---|
| contains the dominant photon object (+ a non-photon object) | 1,121 (40.3 %) | 337 | 784 |
| contains a fragment but not the dominant object | 43 | 4 | 39 |
| contains two signal-photon pieces (dominant and/or fragments) | 635 (22.8 %) | 236 | 399 |
| contains neither | 31 | 4 | 27 |
| indeterminate (ambiguous recovery, differing truth) | 90 | 34 | 56 |
| unresolved | 32 | 13 | 19 |
| no pair (flag 0) | 829 | 685 | 144 |

| tagger-side pair | all | accepted | rejected |
|---|---|---|---|
| contains the dominant photon object | 135 | 17 | 118 |
| contains a fragment but not the dominant | 9 | 0 | 9 |
| contains two signal-photon pieces | 107 | 6 | 101 |
| contains neither | 19 | 2 | 17 |
| indeterminate | 1 | 0 | 1 |
| no pair | 2,510 | 1,288 | 1,222 |

**The statement "the reconstruction pairs the signal photon with a second object" is TRUE for a subset and needs qualification.** Of the **1,468 rejected** events: **1,383 (94.2 %)** have a pair flag; in **1,292 (88.0 %)** a pair (either) contains the signal photon (dominant object or a piece of it); only **85 (5.8 %)** have no pair flag at all. But a "pi0-like" pair exists only for the tagger-side pair (246 rejected events, 16.8 % of the rejected): the **kinematics-tree pair is an energy-sum pair, not a mass-window pair** (section 8).

## 6. Identity of the second pair member  (MEASURED; `second_member.csv`, fig1/fig2)

For pairs containing the signal photon (second member = the other one; `same-photon fragment` includes a minor charge piece):

| second member | kine, clean photon, ncpi0 fail (n = 1,083) | kine, fragmented, fail (109) | tagger, clean, fail (197) | tagger, fragmented, fail (26) |
|---|---|---|---|---|
| same signal-photon fragment | **325 (30.0 %)** | **58 (53.2 %)** | **84 (42.6 %)** | 15 |
| other EM from the signal interaction | **349 (32.2 %)** | 8 | 11 (5.6 %) | 1 |
| signal proton / hadronic object | **214 (19.8 %)** | 23 | **70 (35.5 %)** | 7 |
| cosmic | 81 (7.5 %) | 2 | 18 | 0 |
| other-neutrino EM / hadronic, dirt | 9 | 1 | 1 | 0 |
| ambiguous / mixed, unmatched, indeterminate | 105 | 17 | 13 | 3 |

* **"Other EM from the signal interaction" is neutron-capture-like low-energy photons**, not a pi0 partner: 3,355 of the 3,372 such rows are photons whose mother is a neutron (2,899) or proton; median true KE 2.5 MeV, median reconstructed energy 1.5 MeV (the Geant4 process code is 15; **its name was not audited**, so "neutron-capture-like" is the description by mother pdg and energy). The kine pair then has a median second-member energy of 4.5 MeV.
* **Other-neutrino and cosmic second members are minor** (kine ~8 % of clean failures, tagger ~10 %). Dirt: 4 events. There is no evidence in these samples that unrelated interactions form the fake pair.
* **Signal protons / hadrons** are the second member in 19.8 % (kine) and 35.5 % (tagger) of clean-photon failures: a shower-typed proton row (the pair pool admits any `abs(pdg) != 13` shower object) pairs with the photon.
* **Same-photon pieces** (a crumb or a fragment of the same photon) are the largest single source of tagger-side fake pairs (84 of 197 clean failures); they are *not* fully captured by the Phase-9 `fragmented` flag, because most of them are crumbs below the 50 % dominance threshold (section 9).

## 7. kine pair versus tagger pair  (MEASURED; `kine_vs_tagger.csv`, fig3)

| class | events | ncpi0 survival |
|---|---|---|
| neither pair flag | 767 | 88.9 % |
| kine pair only | **1,743** | 34.8 % |
| tagger pair only | 62 | 4.8 % |
| both, same pair | 125 | 14.4 % |
| both, share one member | 57 | 7.0 % |
| both, different pairs | 20 | 0.0 % |
| both, unresolved | 7 | 0.0 % |

The largest rejected population (kine only, 1,137 rejected = 77.5 %) is the energy-sum pair; its survival does not depend on whether the stored mass is in the window: **34.2 % (120 events with 100-170 MeV) vs 34.8 %** (outside).

## 8. Fake pi0 mass by pair origin  (MEASURED; `fake_pi0_mass_by_origin.csv`, fig4/fig5)

`kine_pio` pair, median stored mass and window fractions:

| origin | n | survival | median mass [MeV] | in 100-170 MeV | median E1 / E2 [MeV] |
|---|---|---|---|---|---|
| two signal-photon pieces | 635 | 37.2 % | **26.8** | 7 % | 160 / 56 |
| signal photon + signal proton / hadron | 375 | 36.0 % | 143.5 | 30 % | 144 / 111 |
| signal photon + other signal EM | 466 | 21.9 % | **40.7** | 3 % | 245 / 4.5 |
| signal photon + non-signal object | 280 | 28.6 % | 64.4 | 17 % | 192 / 47 |
| pair without the signal photon | 31 | 12.9 % | 108.4 | 35 % | 87 / 98 |
| indeterminate | 165 | 43.0 % | 116.7 | 12 % | |

**Which mechanisms populate the pi0 mass region?** In the kinematics-tree pair almost nothing does: **74.5 %** of kine-only pairs are below 100 MeV (median 47.7 MeV) and the energy-sum pair of a photon with a low-energy crumb or capture-like photon has a small mass. The only kine-pair mechanism with a sizeable in-window fraction is **signal photon + signal proton/hadron (30 %)**. In the **tagger-side** pair the window is imposed, and the pairs inside it are: **two signal-photon pieces 107 (39 %)**, **signal photon + signal proton/hadron 82 (30 %)**, signal photon + other non-signal object 47 (17 %), pair without the signal photon 19 (7 %), signal photon + other signal EM 15 (6 %). Their survival is 5-6 % for the first two and 11-21 % for the rest. No mass cut is derived or suggested.

## 9. Clean-photon failures  (MEASURED; `clean_photon_failures*.csv`, `clean_photon_second_member.csv`, fig8/fig9)

"Clean" = the Phase-9 state of the controlling event: the dominant reconstructed object is a clean energetic electron shower (2,556 events, **ncpi0 survival 50.1 %**, 1,276 rejected). Clean does **not** mean single-piece: **23.7 % of clean photons have >= 2 significant pieces (>= 10 % of the photon charge)**, and those survive at **32 %** against **55.7 %** for single-piece photons; clean multi-cluster photons survive at 27.5 % vs 54.2 %.

For the 1,276 clean-photon rejections: **89.4 %** have a `kine` pair, **16.1 %** a tagger pair, **6.0 %** neither; **90.3 %** have a pair that contains the signal photon. The `kine` pair's second member: other signal EM 32.2 %, same-photon piece 30.0 %, signal proton/hadron 19.8 %, cosmic 7.5 %; the tagger pair's: same-photon piece 42.6 %, signal proton/hadron 35.5 %, cosmic 9.1 %. Candidate multiplicity is irrelevant (4.2 % multi-candidate; median 1), the vertex anchoring is the same as for accepted clean events (54.3 % vs 58.6 % within 5 cm), other-neutrino or cosmic activity above 5 MeV is present in 8.2 % (3.6 % for accepted), a second truth neutrino in the window in 60.3 % (58.9 %), the truth topology 0p / 1p / >= 2p is 37.8 / 50.9 / 11.3 % (43.9 / 48.9 / 7.2 % accepted).

**Answer to "why does an apparently clean single photon acquire a pi0-like companion?"** (descriptive, not causal): (1) the kinematics-tree pair is made from *any* detached shower row, and the commonest companions of a clean photon are **neutron-capture-like low-energy photons and minor pieces/crumbs of the same photon**; (2) the tagger-side mass-window pair is formed from **two pieces of the same photon (43 %)** or from the **photon plus a shower-typed proton (36 %)**; (3) unrelated-interaction objects are a minor share. Which of these a BDT penalises is a property of the frozen model, not of the truth: for kine-only pairs the survival is 34.8 % regardless of the second member's mass.

## 10. Truth topology dependence  (MEASURED; `topology.csv`, `delta_and_proton_origin.csv`)

| truth topology | events | survival | kine pair present | tagger pair present | second = signal proton/hadron (kine, of pairs with the photon) | second = other signal EM | survival with / without a kine pair |
|---|---|---|---|---|---|---|---|
| 0p | 1,157 | 49.6 % | 69.0 % | 10.3 % | 165 / 734 (22 %) | 138 (19 %) | 37.2 % / 77.2 % |
| 1p | 1,373 | 47.1 % | 68.4 % | 9.3 % | 174 / 868 (20 %) | 249 (29 %) | 28.4 % / 87.6 % |
| >= 2p | 251 | **36.7 %** | **85.7 %** | 9.6 % | 36 / 197 (18 %) | **79 (40 %)** | 29.8 % / 77.8 % |

**Is the lower ncpi0 survival of >= 2p related to extra hadronic objects becoming fake pair members?** Not through the proton share: the fraction of pairs whose second member is a signal proton/hadron does not rise with proton multiplicity (22 -> 20 -> 18 %). What differs is that a **kine pair exists far more often (85.7 % vs ~69 %)** and its second member is more often **other signal EM (40 % vs 19-29 %)**; survival without a pair is similar (77-88 %). Truth-1p survival is 52.7 % for Delta-decay protons and 35.3 % for FSI-created protons; the tagger pair is present in 7.7 % vs 12.5 % and the kine pair in 64.7 % vs 77.1 %. **Delta0 vs Delta+**: survival 44.8 % vs 49.6 %, tagger pair present 11.4 % vs 8.1 %. Only descriptive: the proton-origin and Delta-charge subgroups are too small to interpret beyond this (the 1p subgroups have 5-18 events in the minor categories); roadmap item P is not started here.

## 11. Upstream sub-BDT correlation  (MEASURED; `upstream_by_pair_group.csv`, `upstream_by_origin.csv`)

Descriptive only (not a repeat of the Phase-12 SHAP study). Each of the 15 nueCC-chain sub-scores has a producer default (the most frequent value); "evaluated" = differs from it, "background-like" = score < 0.

| pair group | ncpi0 | n | median ncpi0 score | mean # sub-scores evaluated | mean # background-like | events with any background-like |
|---|---|---|---|---|---|---|
| kine pair only | pass | 606 | +0.33 | 7.6 | 0.86 | 44.7 % |
| kine pair only | fail | 1,137 | -0.47 | 4.8 | 0.60 | 29.4 % |
| no pair flag | pass | 682 | +0.30 | 5.5 | 0.33 | 26.2 % |
| no pair flag | fail | **85** | -0.49 | **12.0** | **1.06** | **67.1 %** |
| tagger pair | pass | 25 | +0.25 | 5.8 | 0.56 | 32.0 % |
| tagger pair | fail | 246 | -0.83 | 6.6 | 1.07 | 46.7 % |

**After pair origin is known**: for the rejected kine-pair-only events the upstream sub-BDTs do **not** carry more background-like evidence than for the accepted ones (0.60 vs 0.86): the rejection of those events comes from the pair inputs themselves, i.e. the upstream scores do **not reinforce** it. The 85 rejected events **with no pair flag** are the opposite: 12 sub-scores evaluated and 67 % with background-like evidence: an **independent** upstream rejection mechanism, small (5.8 % of the rejected). For the tagger pair the rejected events have about twice the background-like evidence of the accepted (1.07 vs 0.56): mildly reinforcing. No attribution method beyond these conditional counts is applied.

## 12. Natural-CV check  (MEASURED; `natural_cv_check.csv`)

Only candidate-level inputs exist for the natural NC-Delta CV events (no `T_kine` rows and no `T_match` are stored), so the **pair-member taxonomy and the fragmentation are "not available from stored products"** (no new BNB scan was made). Pair-present fractions among shower-stage candidates: natural CV (71 candidates) **kine pair 73.2 %, tagger pair 15.5 %**; official (8,112) **78.8 % and 15.0 %**. Consistent, at low statistics.

## 13. What is established

* Population closure 2,781 = 1,313 + 1,465 + 3; the three non-finite events are kine-pair events with `kine_pio_angle = NaN`.
* The kine pair is the **largest-`E1 + E2`** shower pair with **no mass requirement**; it is **not a pi0 candidate**: 74.5 % of kine-only pairs are below 100 MeV, 6.9 % in 100-170 MeV, and its survival is independent of the mass window.
* The tagger pair is a mass-window pair that always contains the selected shower (262 / 262); it is the strongest single rejection (survival 5-6 % for the two commonest origins) and arises from **two pieces of the same photon (39 %)** or **the photon plus a shower-typed signal proton/hadron (30 %)**.
* 94.2 % of the ncpi0-rejected events have a pair flag and 88.0 % a pair that contains the signal photon; 5.8 % have no pair flag and are rejected by the upstream sub-scores.
* The commonest kine-pair companions of a clean photon are neutron-capture-like low-energy photons (32 %) and pieces of the same photon (30 %); unrelated interactions are minor.

## 14. What remains unresolved

* The pair is **not recovered uniquely for 9.8 % + 1.6 % of kine events** (191 ambiguous, 32 unresolved) and 2.2 % of tagger events; their truth is `indeterminate` and is kept separate. A full recovery needs the shower direction and `get_kine_charge`, which the flatCAF does not store (a producer-side change).
* The `m_pi0_*` knob values of the production job; the name of Geant4 process code 15.
* Whether a pi0-like mass for a **same-photon** pair is a pure geometric artifact (the opening angle of two pieces) cannot be separated from the truth here; it is a property of the pair finder's mass formula (source section 2).
* The kine-pair `same-photon fragment` share includes tiny crumbs; whether a small crumb that changes `kine_pio_*` is what the BDT penalises is a model question (not studied: no BDT or SHAP re-run).
