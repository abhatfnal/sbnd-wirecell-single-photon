# Generic BNB Sample — Phase F Plan

**Purpose**: Small truth-labeled generic BNB MC sample for comparing WireCell tagger
behavior across truth interaction categories.

**Working area**: `baseline_v0/generic_bnb/`

**Compatibility requirement**: Must be compatible with:
- sbndcode v10_14_02_04
- Current G4/detsim assumptions
- Frozen WireCell reconstruction (WCT 251ff143, larwirecell 9295e2a3)

---

## Phase F Step 1: Search for existing suitable BNB MC

Before generating anything, search these project areas for already-reconstructed BNB MC:

```
/lus/eagle/projects/neutrinoGPU/haiwang/       (READ-ONLY)
/lus/eagle/projects/neutrinoGPU/abhat/sbnd/
/lus/grand/projects/neutrinoGPU/
```

Check for:
1. Generator (GENIE) artROOT with compatible sbndcode version
2. Detsim output with compatible Wire-Cell inputs (bothrois)
3. Reco1 output compatible with wcls-img-clus-matching-xin-prod.fcl

If suitable reco1 output exists → skip to WireCell reconstruction stage.
If suitable detsim exists → skip to reco1 stage.
If suitable gen or g4 exists → start from appropriate stage.

**DO NOT use unrelated old production just because it exists.**
Check version compatibility before using any found sample.

---

## Truth category definitions

Categories must be defined mechanically from generator truth.
Convention: **post-GENIE FSI, final-state particles** (what GENIE reports after FSI).
Do NOT mix with pre-FSI or Geant4-level truth.

### numu CC
- Interaction mode: CC (charged-current)
- Incoming neutrino flavor: muon neutrino (PDG 14 or -14)

### nue CC
- Interaction mode: CC
- Incoming neutrino flavor: electron neutrino (PDG 12 or -12)

### NC pi0
- Interaction mode: NC (neutral-current)
- At least one pi0 (PDG 111) in GENIE final state after FSI

### NC non-pi0
- Interaction mode: NC
- No pi0 in GENIE final state after FSI

**Document explicitly**: Whether pi0 definition includes secondary pi0 from FSI rescattering,
or only the primary vertex pi0. For baseline_v0: count any pi0 in GENIE final state after FSI.

---

## Target statistics

Diagnostic sample, not analysis production:
- ~20–50 reconstructed candidates per category if easily available
- Do not chase exact balance; NC non-pi0 will be naturally largest

If existing sample is insufficient or incompatible:
- Generate O(500) BNB neutrino interactions per category using standard SBND FCLs
- Truth-categorize post-generation

---

## Key comparison variables

For each truth category, report:
- Number of truth events
- Number reaching WireCell candidate stage
- Number with evaluated photon tagger (shw_sp_filled=1)
- Number with photon_flag=1 (legacy tagger response)
- Number with valid nue score (≠ -15)
- Number with reconstructed pi0 hypothesis (kine_pio_flag=1)

---

## Output table

`generic_bnb/tables/generic_bnb_wirecell_baseline.csv`

Include the same WireCell branches as `ncdelta_wirecell_baseline.csv` plus truth category column.

---

## Status

[ ] Search for existing compatible BNB MC sample
[ ] Assess version compatibility
[ ] If found: map WireCell reconstruction
[ ] If not found: generate minimal diagnostic sample
[ ] Extract truth categories
[ ] Run WireCell reconstruction (per-event for tracking-pr.root integrity)
[ ] Build generic_bnb_wirecell_baseline.csv
[ ] Compare with NC Delta signal sample (Phase E)
