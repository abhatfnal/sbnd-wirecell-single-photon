# Requirements for a comparison with the SPINE NC-Delta analysis

Status (2026-11-10, updated on branch `analysis/ncdelta-spine-harmonized-definition-20261110`): the **truth side is now harmonized as far as the flatCAF allows**
(`SPINE_SIGNAL_DEFINITION_SOURCE_AUDIT.md`, `SPINE_SIGNAL_DEFINITION_HARMONIZATION.md`). **The reconstruction side is not**, and no Wire-Cell number may be quoted against a SPINE number yet.
This document replaces the earlier version of the requirements; items that were resolved are replaced by what was found.

## A. Now harmonized (truth side, same official Gen2 events)

| item | what is now in place | exactness |
|---|---|---|
| signal categories | masks `spine_truth_signal` (= `spine_technote_strict`), `spine_truth_0p50`, `spine_truth_Np50`, plus the named variants; per-event flags stored outside Git | topology rule **exact** (same collection `rec.mc.nu.prim`, same thresholds as medulla's `mc_topology`); containment and veto **approximate** (see below) |
| FV | true vertex |x|,|y| < 180 cm, 10 < z < 450 cm (strict inequalities) -> 9,206 of 13,773 official events | exact for the technote/`gOre_fiducial_cut` values; the production SPINE `FiducialProcessor` margins were **not** found (the medulla docstring quotes 25/25/30/50 cm; sensitivity table provided) |
| containment | 5 cm margin on a flatCAF-**primary** approximation | **approximation only**: SPINE containment uses all particles incl. secondaries and all spacepoints; four variants quantified |
| proton threshold and channels | 50 MeV post-FSI primary protons; 0p50 / Np50; 35->50 MeV cross-tab | exact for the primary-proton definition |
| photon / lepton / pion topology | exactly one photon > 25 MeV; no e/mu/pi+- > 25 MeV; every above-threshold primary a photon or nucleon (the source rule) | exact |
| Delta identification | ancestry (our filter) with `resnum` variants: `resnum == 0` and the Delta-type set of the source | both quantified; the effect is below 0.1 pp in efficiency |
| sample truth keys | `(run, subrun, evt)` of all 13,773 official events, with the harmonization flags | exact |
| frozen Wire-Cell numerator on the harmonized denominator | `any` and `first`, all / 0p50 / Np50 | done, no cut changed |
| 50-MeV reco projection of the Wire-Cell selection | reco 0p50 / Np50 from the leading reco proton-row KE (> 50 MeV), baseline row convention; `included == 3` handling as a sensitivity | done (policy sensitivity only) |

## B. Differences that remain and are NOT resolved here

1. **Which SPINE commit/TOML produced the technote numbers**, and whether it included `neutrino2026_veto` and the expanded Delta-resonance set (added 2026-05-26 and 2026-06-17). We quantify both with/without; the choice must come from the technote author.
2. **Production SPINE containment/fiducial settings** (`mode` tpc/module/detector, margins, cathode margin) are not in the public repositories we could read.
3. **SPINE truth particles are not in the flatCAF.** Particle-level cuts of the signal tree (single_photon, no_electrons, ...) act on SPINE truth particles (primary-classified, deposit-based `energy_init`); we use the exact `mc_topology` rule on `rec.mc.nu.prim` instead. The two agree only if SPINE `energy_init` equals `genE` for the same particles (unverified).
4. **Efficiency definition of the SPINE quote** (denominator = which truth set? numerator = after the full chain, including cosmic rejection/flash matching and the channel-specific BDT working point?). Must be obtained from the author.

## C. Future requirements for a real Wire-Cell vs SPINE comparison

* Run the **same Gen2 events** through SPINE (or obtain SPINE outputs keyed by `(run, subrun, evt)`), so both chains see the same truth events; the harmonization flags are the join table.
* SPINE reconstruction outputs and the **exact interaction/candidate policy** (our `any` / `first` have no SPINE analogue yet).
* The **SPINE final selection working point** and the channel-specific BDT outputs.
* **Reconstruction-stage semantic mapping** between the Wire-Cell stages (candidate, > 20 MeV shower, BDT evaluable, numu, other, ncpi0, n_20br1) and the SPINE cut flow.
* **Cosmic / flash treatment** of both chains on the same footing (neither is final here).
* **Systematic uncertainties** on both sides (none in this phase).
* A common handling of the **proton row definition** (our `included == 3` convention changes 58 of 1,172 selected events between reco 0p50 and Np50).

## D. Rule until C is done

Do **not** quote the Wire-Cell efficiencies (8.12 % / 10.69 % in the loose TPC box, or 9.38 % / 12.81 % on the harmonized 0p50 / Np50 denominator) against the SPINE ~19 % / ~40 % as reconstruction-quality numbers. The harmonization shows how much of OUR number depends on the definition; it does not explain the difference to SPINE.
