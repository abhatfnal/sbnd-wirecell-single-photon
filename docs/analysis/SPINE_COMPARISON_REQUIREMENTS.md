# Requirements for a future comparison with the SPINE NC-Delta technote (NOT implemented)

Status: **requirements only.** No SPINE number is compared with any Wire-Cell baseline number anywhere in this repository, and none must be until every item below is harmonized.
Date: 2026-11-10. Branch: `analysis/ncdelta-differential-efficiency-20261110`.

The SPINE technote (Seokju) is a *dedicated* NC-Delta selection with its own signal definition and channel-specific BDTs. The Wire-Cell numbers of this repository are
**baseline efficiencies of the frozen MicroBooNE-derived BDT chain against a deliberately loose, generator-level signal definition**. The quoted totals
(SPINE ~19 % for 0p and ~40 % for Np, as given in the request; ours 8.12 % for truth 0p and 10.69 % for truth 1p) therefore do **not** measure the same thing and are **not** a statement
about the relative reconstruction quality of the two chains. The list below is the full set of differences known to us (from the task description of the technote's definition);
anything we have not seen in the technote itself is flagged "to confirm".

## 1. Differences in the signal / denominator definition

| # | Item | SPINE technote | This repository (frozen baseline) | What the harmonization needs | Data available here? |
|---|---|---|---|---|---|
| 1 | Fiducial volume | x, y in [-180, 180] cm, z in [10, 450] cm | provisional TPC box: abs(x), abs(y) < 200 cm, 0 < z < 500 cm (no approved FV) | recompute the denominator and numerator inside the SPINE FV (vertex = true neutrino vertex) | yes: true vertex is in the event table |
| 2 | Truth containment | all final-state endpoints at least 5 cm from the active-volume boundary | none (explicitly not imposed) | per-event minimum over the signal neutrino's final-state primaries of the distance of the **end point** to the boundary | partly: `rec.mc.nu.prim.end.{x,y,z}` and `contained` are in the flatCAF; **not yet extracted per event** (only the signal photon's end point is). A new truth scan is required. Geant4 secondaries are not stored in `prim`. |
| 3 | True photon multiplicity | exactly one true photon with KE > 25 MeV | no photon-energy requirement; the generator filter only requires one status-1 photon from a Delta (resnum == 0 holds for only 97.66 % of events); `photon_n_gt20` (20 MeV) is stored | count primary photons with KE > 25 MeV (not 20) per event | partly: energies of all primary photons are in the flatCAF; only the 20 MeV count and the maximum are stored |
| 4 | Other charged leptons / pions | no true electron, charged pion or muon above 25 MeV | not required; `n_primary_pi_charged` (any energy) is stored, no electron/muon information | per-primary KE of e, mu, pi+- | extractable from the same primary arrays; needs a truth scan |
| 5 | Proton threshold | 50 MeV | 35 MeV (**provisional**, never optimized) | recompute the proton multiplicity with the SPINE threshold on **post-FSI primary protons** (same primary collection) | partly: the stored table has the leading/sub-leading KE and counts above 35, 20, 10 MeV; **no count above 50 MeV** (derivable only for multiplicity 0 and 1 vs >= 2 through the two leading KEs) |
| 6 | Topology channels | 0p and Np (N >= 1) | 0p / 1p / >= 2p (and reco 1g0p / 1g1p) | merge our 1p and >= 2p into Np for the comparison; the reco-side channel definition also differs (see 2.2) | yes |
| 7 | Denominator sample | to confirm (dedicated sample? which generator configuration? is their denominator pre-filtered?) | official Gen2 EX_ncdeltarad, filter box 13,773 events, TPC box 12,427; POT 2.84e21 | same truth events (or an explicit statement of the difference in generator and filter) | yes (ours) |
| 8 | Event selection of the denominator (neutrino choice) | to confirm | provisional rule: neutrino whose vertex is in the filter box, then lowest index (6 multi-signal events) | same convention | yes (ours) |

## 2. Differences in the reconstruction / selection side

1. **Reconstruction chain.** SPINE = ML (deep-learning) reconstruction with channel-specific BDTs trained for this analysis. This repository = production Wire-Cell
   (SCN vertexer, fg1) with the frozen MicroBooNE-derived BDTs (numu, other, ncpi0, nue). The frozen BDTs were never retrained and are not tuned to the SBND NC-Delta signal.
2. **Reco channel definition.** Wire-Cell reco proton rows are derived from `kine_particle_type` rows with a 35 MeV kinetic-energy rule (provisional);
   the SPINE proton threshold and its particle-ID definition may differ. Reco 1g0p / 1g1p here are analysis categories, not truth.
3. **Efficiency definition.** To confirm with the author: is the quoted efficiency (a) after the full selection including cosmic rejection/flash matching, (b) per channel BDT or the final working point,
   (c) normalised to the signal in the FV with the containment and one-photon requirements above, or to a looser set? Our efficiency is normalised to **all** truth events in the region
   (so the containment/one-photon/no-lepton requirements, which remove signal events from SPINE's denominator, are *inefficiencies* here).
4. **Candidate policy.** Our `any` policy counts an event as selected if any Wire-Cell candidate passes; `first` uses the policy-first candidate. SPINE's interaction choice is to be confirmed.
5. **Cosmic / flash handling.** Wire-Cell: the frozen chain uses the matched-flash information only through its BDT inputs; the cosmic normalisation and flash-time reference are unresolved here.
   SPINE: to confirm.

## 3. The procedure that would make the comparison meaningful (to run later)

1. Add the missing truth variables to the existing resumable truth scan (per-primary end-point distances for containment, photon counts above 25 MeV, e/mu/pi KE, proton counts above 50 MeV).
2. Build the **SPINE-harmonized denominator** from the official events: FV, containment, exactly one photon above 25 MeV, no e/pi+-/mu above 25 MeV, proton threshold 50 MeV, channels 0p / Np.
3. Re-evaluate the **same frozen Wire-Cell baseline** numerator on that denominator (the numerator needs no new reconstruction).
4. Report the Wire-Cell efficiency on the harmonized denominator next to the SPINE value, **clearly labelled as two different reconstructions on the same signal definition**,
   with the Wire-Cell frozen-baseline caveat (not retrained, not optimized).
5. Obtain from the technote's author: the exact efficiency definition, the sample, the cut flow, and the channel-specific BDT working points; treat any difference remaining after steps 1-3 as a physics/reconstruction statement only then.

Until then: **do not** quote 8.12 % / 10.69 % against ~19 % / ~40 %.
