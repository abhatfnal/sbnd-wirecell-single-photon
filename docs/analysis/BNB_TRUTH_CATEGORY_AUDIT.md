# BNB truth-category audit (first-pass taxonomy, background composition only)

Sample: official BNB CV, all 37,742 files. Taxonomy code: `src/sbnd_single_photon/truth.py` (`truth_summary`, `classify_events`). Counts: `tables/baseline/bnb_cv_truth_cutflow.csv`, `bnb_cv_final_composition.csv`, `bnb_cv_truth_taxonomy_audit.json`, `bnb_cv_truth_single_active_interactions.csv`. **No signal purity is given.** The "active volume" below is the *provisional* nominal TPC box (|x|<200, |y|<200, 0<z<500 cm) used only to separate dirt from active-volume neutrinos; it is **not an analysis fiducial volume** and no FV is applied anywhere.

## 1. A bug found and fixed during this audit

`rec.mc.nu.npizero` (and `npiplus`, `npiminus`, `nproton`, `nneutron`) are **almost always 0** in these CAFs: in the first 30 files 0 of 738 true neutrinos had `npizero > 0` (a later 40-file check of 1,014 neutrinos found 4 with `npizero > 0`, all with a primary π⁰, against 136 neutrinos that have one; `nproton` was 0 for all 1,014 and `genweight` is unfilled, 0), while 112 (15 %) had a π⁰ among their primaries (`rec.mc.nu.prim.pdg == 111`; 74 of them CC). The first version of the classifier used the field and therefore could never produce `CC_PI0` (it gave 0 `CC_PI0` and 76 `NC_PI0` in the first 170k events). The π⁰ count is now derived from the GENIE primaries (primary columns are flat per event and are regrouped per neutrino with `nprim`); `tests/test_truth.py::test_pi0_count_must_come_from_primaries` guards it. All numbers here come from the fixed classifier; the older smoke-test truth table (1000 events) predated the fix; it was removed from `tables/smoke/` (the smoke script now uses the primaries and regenerates it).

## 1a. Truth-level definition of the π⁰ categories (source-checked)

- **What `prim` is.** `sbncode v10_31_00 CAFMaker/FillTrue.cxx` L478–492: `rec.mc.nu.prim` = the `SRTrueParticle`s of this interaction whose `start_process == kG4primary`, i.e. the **GENIE final-state particles that were handed to Geant4** (status-1 stable final state). `nprim` is their number (the CAF stores the per-particle columns flat per event, regrouped here with `nprim`). A π⁰ in this list is a π⁰ that **left the struck nucleus after GENIE's intranuclear cascade** — it is **post-FSI** under the standard GENIE→LArSoft convention that only status-1 final-state particles go to Geant4 (not separately verified in the files) (a π⁰ absorbed or charge-exchanged inside the nucleus is not there; a π⁰ made by FSI is). The π⁰ decays in Geant4, so its photons are non-primary and π⁰'s produced later by secondary hadronic interactions in the argon are not counted.
- **Why `npizero` is 0.** `rec.mc.nu.npizero` is `gtruth.fNumPi0` (L541), which `nugen` GENIE2ART fills from GENIE's **exclusive tag** (`exclTag.NPi0()`): per `GTruth.h` "number of pi0 after reaction, **before FSI**", and (per the nugen comment) most events have none of these counts set. It is a pre-FSI, exclusive-channel-only tag, so it is zero for almost all inclusive BNB events here; it cannot be used for a final-state taxonomy. (`npiplus`, `nproton`, … have the same origin.)
- **Resulting meaning of the categories.** `NC_PI0` = exactly one neutrino vertex in the provisional box, neutral-current, and ≥1 post-FSI π⁰ among its G4 primaries; `CC_PI0` = the same for charged current (the flavour of the CC lepton is not distinguished within it). `NUMU_CC` / `NUE_CC` / `OTHER_NC` therefore mean "no post-FSI primary π⁰". The categories describe the true final state of the *event*, not which particle faked a photon in the reconstruction (a π⁰ that was not the source of the selected shower is still `NC_PI0`).
- **Is the interpretation right for this taxonomy?** It matches the purpose (background composition by whether a π⁰ is in the final state seen by the detector); nothing demonstrates it wrong, so the taxonomy is unchanged. Not examined: whether a photon-producing non-π⁰ final state (e.g. Δ → Nγ, η, radiative decays) deserves its own category — it would show up as `OTHER_NC`/flavour categories.

## 2. Precedence (as implemented; documented, not tuned)

1. no true neutrino → `COSMIC_NO_NU` (0 events in CV: every event has ≥1 generated neutrino);
2. no neutrino vertex in the box → `DIRT_NO_ACTIVE`;
3. >1 vertex in the box → `MULTI_ACTIVE`;
4. exactly one in the box: NC & π⁰ → `NC_PI0`; CC & π⁰ → `CC_PI0`; then ν_e CC → `NUE_CC`; ν_μ CC → `NUMU_CC`; other NC → `OTHER_NC`; other CC → `OTHER_CC`; else `OTHER`.

## 3. Findings (all 500,000 events)

| category | all events | `wc.valid` events |
|---|---|---|
| NUMU_CC | 140,680 | 140,650 |
| NUE_CC | 1,016 | 1,014 |
| NC_PI0 | 10,212 | 10,210 |
| CC_PI0 | 16,068 | 16,063 |
| OTHER_NC | 52,286 | 52,279 |
| OTHER_CC / OTHER / COSMIC_NO_NU | 0 | 0 |
| DIRT_NO_ACTIVE | 271,433 | 271,380 |
| MULTI_ACTIVE | 8,305 | 8,303 |

- **π⁰ precedence:** 26,280 single-active events (16,068 CC + 10,212 NC) are assigned to π⁰ categories. Under flavour-first precedence the CC_PI0 events would be 15,874 ν_μ and 194 ν_e CC (the latter would otherwise inflate `NUE_CC` by 19 %: 1,016 → 1,210). π⁰-first is kept because π⁰ is a major 1γ-like background topology and keeps the intrinsic-ν_e category free of π⁰ events; this is a convention, to be confirmed.
- **Ambiguous/unclassified:** none. Every single-active event is exactly one of CC/NC and has |PDG| 12 or 14, so `OTHER` and `OTHER_CC` are empty (no ν_τ, no events with both flags).
- **Multi-active:** 8,305 events (1.7 %) have ≥2 neutrino vertices in the box (8,164 with two, 141 with three); they are assigned to `MULTI_ACTIVE` regardless of interaction type, so an NC π⁰ next to a CC interaction is not counted as NC π⁰. Their share of the final selection is larger (41 of 649) than their share of events: they are a real feature of the overlay (several in-time interactions), not a bookkeeping error.
- **Dirt/no-active:** 54.3 % of events. Generated neutrinos include a rock box; 1–7 neutrinos per event (mean ≈1.8). 104 of the 649 selected events are `DIRT_NO_ACTIVE`: possible reasons (not separated here): a cosmic- or dirt-driven candidate, or a neutrino just outside the provisional box.
- **Box sensitivity (taxonomy only):** 12 % of single-active vertices lie within 10 cm of a box face (6 % within 5 cm, 2.5 % within 2 cm). Any change of the box moves events between `DIRT_NO_ACTIVE`, the single categories and `MULTI_ACTIVE` at that level; the box is therefore adequate for a background-composition overview but not for an efficiency-grade definition. `rec.mc.nu.isvtxcont` is unfilled in these CAFs and `vtx.*` is NaN, so position is used.
- Categories are per event, not per candidate. Candidate-level truth (charge-weighted dominant neutrino) is in `CANDIDATE_POLICY_AUDIT.md`.

## 4. Counts through the chain (policy `any`, raw events)

| category | wc.valid | candidate | n20mev>0 | numu>0.4 | other>0.2 | ncpi0>−0.05 | nue>−1 | n20br1==1 |
|---|---|---|---|---|---|---|---|---|
| NUMU_CC | 140,650 | 132,216 | 17,431 | 901 | 118 | 36 | 36 | **27** |
| NUE_CC | 1,014 | 972 | 803 | 421 | 283 | 219 | 219 | **165** |
| NC_PI0 | 10,210 | 9,572 | 7,672 | 3,869 | 1,954 | 256 | 256 | **178** |
| CC_PI0 | 16,063 | 15,542 | 12,753 | 1,186 | 668 | 165 | 165 | **101** |
| OTHER_NC | 52,279 | 30,914 | 3,431 | 943 | 152 | 41 | 41 | **33** |
| DIRT_NO_ACTIVE | 271,380 | 40,210 | 7,904 | 4,210 | 565 | 163 | 163 | **104** |
| MULTI_ACTIVE | 8,303 | 8,034 | 2,669 | 403 | 184 | 56 | 56 | **41** |

(`first`-policy and stored-per-generated-POT columns: `bnb_cv_truth_cutflow.csv`; reco 0p/1p/≥2p of the final events per category: `bnb_cv_final_composition.csv`, summarised in `BNB_CV_BASELINE.md`.)

## 5. Open points

- π⁰-first vs flavour-first, and the MULTI_ACTIVE treatment, are conventions to confirm.
- The box (and an SBND FV, see `SBND_FIDUCIAL_VOLUME_AUDIT.md`) must be fixed before any efficiency-grade truth definition.
- The CAF contains 26.5 % of the generated events; the 73.5 % removed by the generator-level filter (no in-TPC neutrino, ≤0.1 MeV neutrino-induced active-volume deposit) are not in these files.
