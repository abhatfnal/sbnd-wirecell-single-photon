# BNB Reco1 Baseline Compatibility

**Date**: 2026-10-04
**Sample**: `fresh-50evt-integrated-20260909`
**Input path**: `/lus/eagle/projects/neutrinoGPU/abhat/sbnd/sample_generation_port/work/haiwang-current/integration-2026-09-08/fresh-50evt-integrated-20260909/run/reco1_out.root`
**File size**: 1.4 GB
**Events**: 50

---

## sbndcode provenance

Confirmed from reco1.log:
```
sbndcode v10_14_02_04
GDML: /lus/flare/projects/neutrinoGPU/scisoft/larsoft/sbndcode/v10_14_02_04/gdml/sbnd_v02_06.gdml
```

Process names carried in reco1_out.root: GenieGen, G4, DetSim, Reco1

**sbndcode version matches baseline_v0 frozen reconstruction: v10_14_02_04** CONFIRMED

---

## Sample composition

The fresh-50evt sample uses CORSIKA cosmic ray overlay:
- `simb::MCTruths_generator__GenieGen` -- BNB neutrino truth (GENIE)
- `simb::MCTruths_corsika__GenieGen` -- CORSIKA cosmic ray truth

This is the standard SBND inclusive-BNB MC format. The 50 reco1 events are
a subset of 136 gen events that passed the active-volume fiducial filter.

---

## Required products for frozen WCT FCL

Frozen FCL: `wcls-img-clus-matching-xin-prod.fcl` (SHA f7cab672...)
Frozen FCL path: `reco-bundle-id-fix-validation-20260916/config-final/`

| Product | Tag | Status |
|---------|-----|--------|
| recob::Wire | simtpc2d:dnnsp | PRESENT (DetSim process) |
| recob::Wire | simtpc2d:wienersummary | ABSENT from reco1_out; present in detsim as `doubles` type; original WCT run succeeded without it -- ACCEPTABLE |
| ints (mask) | simtpc2d:badmasks | PRESENT (DetSim process) |
| recob::OpFlash | opflashtpc0 | PRESENT (Reco1 process) |
| recob::OpFlash | opflashtpc1 | PRESENT (Reco1 process) |
| simb::MCTruth | generator (GenieGen) | PRESENT |
| simb::MCParticle | largeant (G4) | PRESENT |
| sim::SimEnergyDeposit | ionandscint:priorSCE (G4) | PRESENT |
| sim::SimChannel | simtpc2d:simpleSC (DetSim) | PRESENT |

**All hard-required products are PRESENT. wienersummary absence confirmed non-blocking
by successful original WCT run from the same file.**

---

## MCTruth and MCParticle presence

Both `simb::MCTruth` and `simb::MCParticle` are present and required by the WCT FCL
for the wclsTensorSetLabeler truth labeling step. These are present from GenieGen and G4.

| Product | Process | Present |
|---------|---------|---------|
| simb::MCTruths_generator__GenieGen | GenieGen | YES |
| simb::MCTruths_corsika__GenieGen | GenieGen | YES |
| simb::MCParticles_largeant__G4 | G4 | YES |
| simb::MCParticles_largeant_droppedMCParticles_G4 | G4 | YES |

---

## hadd / artROOT merge note

hadd does NOT work across artROOT files with different process_name per batch.
This sample is a SINGLE artROOT file (not a multi-batch merge), so hadd is not needed.

---

## Whether exact frozen WCT can run directly from this file

**YES. The exact frozen WCT baseline (WCT 251ff143, larwirecell 9295e2a3, sbndcode v10_14_02_04)
can run directly from `reco1_out.root`.** All required input products are present.

Output area: `baseline_v0/generic_bnb/wirecell_exact_baseline/`
FCL to use: frozen `wcls-img-clus-matching-xin-prod.fcl`
Run per-event (PBS -J array) to preserve tracking-pr.root integrity.

**Do NOT mix with existing WCT output from fresh-50evt** (which used WCT b2e3c6a9b440, different commit).

---

## RSE list (uproot Events count)

50 events in reco1_out.root. FileIndex has 52 entries (50 event + 2 run/subrun boundaries).

Exact RSE list requires container-based reading (uproot cannot deserialize EventAuxiliary).
PBS truth-extraction job will produce the per-event RSE table.

---

## BNB truth categories (all 50 events, mechanically extracted 2026-10-04)

Source: PyROOT inside sbndcode v10_14_02_04 container (PBS 192933), reading
simb::MCTruths_generator__GenieGen from reco1_out.root.

| Category | Count |
|----------|-------|
| numu_CC | 31 |
| numu_NC_non_pi0 | 18 |
| numu_NC_pi0 (itype=1006, NC RES pi0) | 1 |
| nue_CC | 0 |
| **Total** | **50** |

NC event breakdown:
- NC QE (mode=0, itype=1002): 8
- NC pi0 resonant (mode=1, itype=1006): 1
- NC pi+ resonant (mode=1, itype=1007): 1
- NC pi- resonant (mode=1, itype=1008): 3
- NC multi-pi (mode=1, itype=1009): 1
- NC MEC (mode=10, itype=1000): 3
- NC DIS (mode=2, itype=1092): 2

Full table: `generic_bnb/tables/bnb_truth_categories.csv` (50 rows)
RSE columns: -1,-1,-1 (EventAuxiliary PyROOT access pending; RSE fix PBS 192935)

---

## Action gate

- [x] Input path verified: reco1_out.root (1.4 GB, 50 events)
- [x] sbndcode v10_14_02_04 confirmed
- [x] Required WCT input products present (all except optional wienersummary)
- [x] MCTruth present (simb::MCTruths_generator__GenieGen)
- [x] MCParticle present (simb::MCParticles_largeant__G4)
- [x] BNB truth categories from all 50 events (PBS 192933 complete; 31 CC, 18 NC, 1 NC-pi0)
- [ ] RSE fix (PBS 192935 pending; non-blocking for WCT gate)
- [ ] Exact frozen WCT run submitted (script ready; submit when authorized)

**WCT RUN GATE: ALL CONDITIONS MET.**
**Script**: `generic_bnb/jobs/wct/pbs_bnb_wct_baseline_array.pbs`
**Submit**: `qsub -J 0-49 ... pbs_bnb_wct_baseline_array.pbs`
**IMPORTANT**: Do NOT submit until explicitly authorized.
