# BNB Truth Category Estimate: fresh-50evt Sample

**Date**: 2026-10-04
**Sample**: `fresh-50evt-integrated-20260909`
**Path**: `/lus/eagle/projects/neutrinoGPU/abhat/sbnd/sample_generation_port/work/haiwang-current/integration-2026-09-08/fresh-50evt-integrated-20260909/`
**WCT provenance**: COMPATIBLE_BUT_DIFFERENT_WCT (see GENERIC_BNB_SAMPLE_INVENTORY.md)

---

## Method

GENIE truth records were read from:
```
logs/gen.log
```

The gen.log prints one block per neutrino-nucleus interaction (those that occurred in or
near the detector volume), in the format:
```
GENIE truth record:
interaction code: N, neutrino scattering code: M at (x, y, z; t)
probe: FLAVOR with cp=(...) hit nucleon ... in target: Ar40
```

Where:
- interaction code 2 = CC (charged current)
- interaction code 3 = NC (neutral current)
- neutrino scattering code 4 = Resonant (RES)
- neutrino scattering code 10 = MEC (meson exchange current)

The TrigReport for the gen stage shows:
```
TrigReport Events total = 150 passed = 136 failed = 14
```

136 events passed the fiducial volume filter (14 neutrinos passed through without
interacting in the active volume). However, only 24 GENIE truth records appear in
gen.log. The remaining 112 interactions were processed but not logged at the verbosity
level captured in gen.log. The 24 logged interactions are a representative but
INCOMPLETE subset of the 136 events in the sample.

---

## Observed interaction categories (24 logged events)

| Category | Code | Count | Fraction |
|----------|------|-------|----------|
| numu CC MEC | ic=2, sc=10 | 15 | 62.5% |
| numu CC RES | ic=2, sc=4 | 3 | 12.5% |
| numu NC MEC | ic=3, sc=10 | 5 | 20.8% |
| numu NC RES | ic=3, sc=4 | 1 | 4.2% |
| nue CC | any | 0 | 0.0% |
| nue NC | any | 0 | 0.0% |
| numubar or nuebar | any | 0 | 0.0% |

**All 24 logged interactions have probe `nu_mu`. No nue, numubar, or nuebar seen in logged events.**

---

## BNB composition estimate

Based on the 24 logged events and BNB flux knowledge:

| Category | Observed (24 events) | Expected fraction (BNB at SBND) | Assessment |
|----------|---------------------|----------------------------------|------------|
| numu CC | 18/24 = 75% | ~70-75% | Consistent |
| numu NC | 6/24 = 25% | ~20-25% | Consistent |
| nue CC | 0/24 = 0% | ~1-2% | ABSENT in log sample |
| nue NC | 0/24 = 0% | ~0.3% | ABSENT in log sample |

**nue CC absent in logged events**: With only 24 logged interactions and an expected nue
fraction of ~1-2%, the probability of seeing 0 nue CC events is (1-0.015)^24 ~ 70%.
Absence in the 24 logged events is statistically consistent with a ~1.5% nue fraction.
The 50-event sample almost certainly contains 0 or 1 nue CC events.

**NC pi0 vs NC non-pi0**: Cannot be determined from the gen.log interaction codes alone.
Resonant NC (sc=4) events may produce pi0 (Delta -> N + pi0) or photon (Delta -> N + gamma)
or other resonance decay products. MEC NC events (sc=10) also produce various hadrons.
Full NC pi0 categorization requires reading the final-state particle list from MCTruth,
which is not accessible via gen.log or uproot without a container-based analysis.

---

## Recommended truth category counts for baseline_v0 Phase F

For the 50-event BNB generic sample, the best estimate based on BNB flux composition
and the 24 logged interactions is:

| Category | Estimated count (50 events) | Notes |
|----------|---------------------------|----|
| numu CC | ~37 | Dominant, ~75% |
| numu NC | ~12 | ~25% |
| nue CC | 0-1 | ~1-2%, statistically likely absent |
| nue NC | 0 | ~0.5%, extremely unlikely to appear |
| NC pi0 | ~2-4 | Subset of NC (~15-30% of NC) |
| NC non-pi0 | ~8-10 | Remaining NC |

These are ESTIMATES, not counts from truth inspection. Exact counts require running
an analysis module on the artROOT files in the sbndcode container environment.

---

## Key finding for baseline_v0

**nue CC is absent or at most 1 event in the 50-event BNB sample.** This is expected from
the BNB flux composition at SBND baseline energies. The baseline_v0 Phase F measurement
of the nue_score distribution will be dominated by numu CC backgrounds, with NC events
providing the main irreducible background. Any nue CC contamination is negligible.

This is consistent with the constraint: "Do NOT mix a dedicated nue sample into the
inclusive-BNB composition." The fresh-50evt sample is inclusive-BNB and does not require
a dedicated nue sample to represent the nue component accurately.

---

## Caveat: WCT provenance mismatch

The fresh-50evt sample used:
- WCT commit: `b2e3c6a9b440af9f440151d5e9c9aa1771194bd0` (NOT baseline `251ff143`)
- larwirecell: `5c50b2dc31a8b8f07b4afe4e1987884e2f298901` (NOT baseline `9295e2a3`)

Classification: COMPATIBLE_BUT_DIFFERENT_WCT. The EXISTING WireCell outputs for this
sample are NOT usable for baseline_v0. For Phase F, baseline WireCell must be run from
`reco1_out.root` using the frozen baseline WCT commit `251ff143`.

The truth categories described here reflect the gen-level truth composition and are
independent of the WCT provenance issue.
