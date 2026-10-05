# SBND Single-Photon Selection: Baseline v0 Report

**Status**: IN PROGRESS — framework established; awaiting 50-event NC Delta sample reconstruction

**Baseline**: Faithful MicroBooNE→SBND Wire-Cell port
- WCT: `251ff143`
- larwirecell: `9295e2a3`
- sbndcode: `v10_14_02_04`

**Full provenance**: [BASELINE_PROVENANCE.md](BASELINE_PROVENANCE.md)

**Obstacle log**: [SBND_1GAMMA_OBSTACLE_LOG.md](SBND_1GAMMA_OBSTACLE_LOG.md)

---

## Executive summary

> *To be filled once Phase E analysis is complete.*

Preliminary finding from the 3-event engineering sample:
- None of the 3 reconstructable signal events produced `photon_flag=1` from the inherited single-photon tagger.
- Event 0 (E_gamma ≈ 555 MeV): photon shower reconstructed substantially but in companion clusters,
  inaccessible to `singlephoton_tagger()` via `map_vertex_to_shower[main_vertex]` (OBS-001).
- Event 1 (E_gamma ≈ 308 MeV): photon shower severely under-reconstructed (~48% of true deposited energy) (OBS-002).
- Event 2 (E_gamma ≈ 683 MeV): geometric acceptance loss — vertex at extreme TPC corner, only ~12 MeV in active volume.

---

## 1. Has the MicroBooNE-derived Wire-Cell selection been implemented faithfully on SBND?

**Answer**: Yes, based on the engineering sample.

The frozen reconstruction chain (WCT `251ff143`, larwirecell `9295e2a3`, sbndcode `v10_14_02_04`)
produces valid Wire-Cell output structures including:
- `tracking-pr.root` with `T_tagger`, `T_kine`, `T_bundle` trees
- `nugraph.h5` with imaging output
- All inherited MicroBooNE tagger branches present (numu_score, nue_score, photon_flag, etc.)

The frozen SBND implementation faithfully reproduces the currently ported Wire-Cell configuration
and tagger execution path; equivalence of its physics performance to the original MicroBooNE analysis
is not assumed. This project is explicitly measuring where that physics portability succeeds or fails.

---

## 2. Fraction of reconstructable NC Delta photons reaching each stage

> *To be filled from Phase E tables once 50-event sample is complete.*

| Stage | Engineering sample (3 evt) | 50-event sample |
|-------|---------------------------|-----------------|
| Any WireCell neutrino candidate | 2/2 reconstructable (100%) | TBD |
| T_tagger present | 2/2 (100%) | TBD |
| shw_sp_filled=1 | 0/2 (0%) | TBD |
| photon_flag=1 (legacy tagger response) | 0/2 (0%) | TBD |
| Valid nue BDT (nue_score ≠ −15) | 0/2 (0%) | TBD |

*Note: Event 2 excluded from denominator (geometric acceptance loss).*

---

## 3. Legacy `photon_flag` vs photon energy and conversion gap

> *To be filled from Phase E tables.*

**Terminology**: `photon_flag=1` is the **legacy MicroBooNE photon-tagger response**, not the SBND
single-photon efficiency. Treating it as such would conflate three distinct failure modes:
(a) geometric acceptance loss, (b) imaging/reconstruction inefficiency, (c) algorithm inaccessibility.

---

## 4. Photons reconstructed in companion vs main clusters

From engineering sample: Event 0 (E_gamma ≈ 555 MeV) — photon shower in companion clusters.

> *Systematic rate to be quantified from 50-event sample.*

---

## 5. Truth single photon creating reconstructed pi0 hypothesis

From engineering sample: Events 0 and 1 both have `kine_pio_flag=1`.

Event 0: `kine_pio_energy_1 ≈ 158.8 MeV`, `kine_pio_energy_2 ≈ 33.1 MeV`, `kine_pio_angle ≈ 15.1°`

`kine_pio_flag` is a reconstructed two-shower pi0 hypothesis. It is NOT pi0 truth.
A fragmented single photon shower can satisfy the two-shower hypothesis.

> *Systematic rate to be quantified from 50-event sample.*

---

## 6. How often is nue BDT unevaluable (nue_score = −15)?

From engineering sample: Events 0 and 1 both have `nue_score=-15`.

`nue_score=-15` is the sentinel from `UbooneNueBDTScorer` when `br_filled=0`.
It indicates the prerequisite chain broke before BDT scoring — not that the event
is strongly non-nue-like.

Root cause: `shw_sp_filled=0` → `br_filled=0` → `nue_score=-15` sentinel.

> *Systematic rate to be quantified from 50-event sample.*

---

## 7. Dominant genuine-photon failure modes

Based on engineering sample:

1. **OBS-001** (observed): Photon shower in companion cluster, inaccessible to `singlephoton_tagger()`.
2. **OBS-002** (observed): Imaging/reconstruction severely underestimates shower deposited energy.
3. Geometric acceptance loss (Event 2): vertex at TPC corner, shower exits boundaries.

> *Rank ordering and frequency to be quantified from 50-event sample.*

---

## 8. numu CC, nue CC, NC pi0, NC non-pi0 population of key variables

> *To be filled from Phase F (generic BNB sample) analysis.*

Status: Generic BNB sample search/generation not yet started.
Working area: `baseline_v0/generic_bnb/`

---

## 9. Which pieces of Lee's/MicroBooNE selection appear portable to SBND?

> *To be filled after Phases E and F are complete.*

Preliminary assessment (engineering sample only):
- The Wire-Cell imaging chain runs on SBND data without code modifications.
- The neutrino candidate reconstruction appears to function (2/2 reconstructable events produce candidates).
- The BDT score infrastructure is intact (numu_score is a real score for Events 0 and 1).
- Flash-match appears to operate.

---

## 10. Which pieces clearly require SBND adaptation?

> *To be filled after Phases E and F are complete.*

Preliminary (engineering sample only):
- `singlephoton_tagger()` cluster access map (`map_vertex_to_shower[main_vertex]`) may need extension for companion clusters.
- `nue_score` BDT prerequisites (`br_filled`) depend on the shower-feature filling chain, which never fires in the engineering sample.

---

## 11. Top 3–5 concrete questions for the Wire-Cell team

> *To be finalized after 50-event sample and generic BNB sample are analyzed.*

Draft questions based on engineering sample:

1. **Companion-cluster shower access**: `singlephoton_tagger()` uses `map_vertex_to_shower[main_vertex]`.
   In MicroBooNE NC Delta events, what fraction of signal photon showers appear as companion vs main clusters?
   Is there a reason the companion path is not evaluated?

2. **Imaging efficiency for moderate-energy photons**: Event 1 (E_gamma ≈ 308 MeV, fully contained)
   produced only 110 SP and ≈94 MeV reco energy. What Wire-Cell imaging parameters control the
   minimum cluster size / threshold? Are these tuned for SBND noise levels?

3. **kine_pio_flag behavior for true single photons**: Both Events 0 and 1 produced `kine_pio_flag=1`.
   Was this studied in MicroBooNE NC Delta samples? Is there a recommended way to distinguish
   true pi0 from fragmented single-photon kine_pio?

4. **Companion-cluster topology source**: Is there a documented path to evaluate the inherited photon
   score for companion-cluster showers without retraining the nue BDT?

5. **Bundle provenance in NuGraph4 context**: With NuGraph4 topology (`251ff143` "preserve matching
   bundle provenance"), how is the cluster-to-bundle mapping expected to interact with the
   inherited single-photon tagger? Is the tagger expected to change behavior with NuGraph4 topology?

---

## 12. What should the first SBND-specific modification be?

> **NOT IMPLEMENTED** in baseline_v0. Documented here for future discussion only.

Based on the engineering sample, the most impactful first modification would be:

**Extend companion-cluster photon access in `singlephoton_tagger()`**

This would allow photon showers that are reconstructed as companion clusters (not the main cluster)
to be evaluated by the tagger. OBS-001 shows this is the dominant failure mode for at least one
engineering event.

Implementation approach (to be discussed with Wire-Cell team before implementing):
- Iterate over all clusters associated with the selected neutrino candidate, not just those
  reachable via `map_vertex_to_shower[main_vertex]`
- Define a companion-cluster photon score branch (separate from the current `photon_flag`)
- Run both paths and report both scores before designing any cut

This modification requires understanding the MicroBooNE design intent behind the current
cluster access pattern before changing it.

---

## Appendix: Engineering sample reference

The 3-event engineering sample established the truth-to-reconstruction chain and revealed
the first three failure modes. It remains the human-audited reference for the 50-event analysis.

Key files:
- `signal_mc/ncdelta/end_to_end_3evt/docs/ncdelta_wirecell_candidates.csv`
- `signal_mc/ncdelta/end_to_end_3evt/docs/photon_truth_containment.csv`
- `signal_mc/ncdelta/end_to_end_3evt/docs/wirecell_flag_semantics.md`
- `signal_mc/ncdelta/end_to_end_3evt/docs/ncdelta_wirecell_characterization.md`
