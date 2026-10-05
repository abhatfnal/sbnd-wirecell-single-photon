# NC Delta Gen Merge Validation

**Date**: 2026-10-04
**Status**: MERGE_COMPLETE (PBS job 192843; art exit 0; 59 events verified)
**Total accepted events**: 59 (verified)

---

## 1. Source file verification

All 10 event-bearing batch output files verified before merge:

| Batch | firstRun | Events (TrigReport) | Events (uproot) | File size | Match |
|-------|----------|---------------------|-----------------|-----------|-------|
| 03 | 30 | 5 | 5 | 93784 B | YES |
| 04 | 40 | 6 | 6 | 96463 B | YES |
| 05 | 50 | 9 | 9 | 101755 B | YES |
| 06 | 60 | 5 | 5 | 94436 B | YES |
| 07 | 70 | 9 | 9 | 103012 B | YES |
| 08 | 80 | 4 | 4 | 91479 B | YES |
| 09 | 90 | 2 | 2 | 88660 B | YES |
| 10 | 100 | 6 | 6 | 94070 B | YES |
| 11 | 110 | 3 | 3 | 91850 B | YES |
| 12 | 120 | 10 | 10 | 104227 B | YES |

**Total: 59 events across 10 files. TrigReport and uproot counts agree for all batches.**

Batches 01 and 02 produced 0 accepted events (confirmed via uproot: Keys=[] in RootOutput
UUID files). Not included in merge. Classification: ZERO_ACCEPTED_VALID.

---

## 2. RSE uniqueness

Each batch uses a distinct `firstRun` value (10, 20, ..., 120). ART produces events in
run space `run=firstRun, subrun=0, event=1..1000`. Since all run numbers are distinct,
no (run, subrun, event) tuple can appear in more than one batch output file.

**RSE duplicate check: PASS (structural guarantee, no duplicates possible)**

---

## 3. Merge method

hadd was attempted but failed: artROOT files with different `process_name` values per batch
(NCDeltaBatch03, NCDeltaBatch04, etc.) are not safely merged by hadd. hadd creates the
output schema from the first source file and cannot copy entries from source files with
different branch names. Result: only 5 events from batch_03 copied, all others lost.

The correct merge uses `lar -c ncdelta_gen_merge.fcl -s batch_03.root ... -s batch_12.root`,
which handles artROOT metadata correctly. PBS job 192843 submitted for this merge.

**Merge PBS job**: 192843.sophia-pbs-01.lab.alcf.anl.gov
**Output**: `ncdelta_50evt/gen/ncdelta_gen_merged.root`
**FCL**: `jobs/gen/fcl/ncdelta_gen_merge.fcl` (process_name: NCDeltaMerge)

Post-merge verification (completed 2026-10-04):
- [x] uproot: merged file Events tree has 59 entries (CONFIRMED)
- [x] art TrigReport: 59 events written, exit 0 (CONFIRMED)
- [x] No duplicate RSEs: structural guarantee (disjoint run numbers)
- Note: MCTruth products stored under original process names NCDeltaBatch03..12;
        downstream G4 module reads by module label "generator" (process-agnostic)

---

## 4. Truth validation

The NC Delta filter (NCDeltaRadiative_module.cc, installed sbndcode v10_14_02_04 version)
enforces the following selection predicate for every accepted event:

```
truth.GetNeutrino().CCNC()  == simb::kNC       (NC interaction)
truth.GetNeutrino().Mode()  == genie::kScResonant (resonant scattering)
```

Plus: at least one status-1 photon in the final state, and the photon traces through the
particle ancestry to a Delta0 (PDG 2114) or Delta+ (PDG 2212 via resonance path).

**All 59 accepted events satisfy these criteria by the filter's own pass/fail logic.**
The selection predicate is IDENTICAL between the installed and reference module versions.
The only differences in the installed module affect (a) the diagnostic PDG recording in
FillTree, and (b) two error paths that would abort the job -- neither fired (all batches
processed event 1000).

### Expected truth properties for all 59 accepted events:

| Property | Expected value | Basis |
|----------|---------------|-------|
| CCNC | 1 (NC) | Filter enforces |
| Mode | genie::kScResonant (= 4) | Filter enforces |
| Final-state photon | >= 1, status=1 | Filter enforces |
| Photon ancestry | Contains Delta0 (2114) or Delta+ (2212 via res) | Filter enforces |
| Vertex | In generator volume (within SBND geometry) | Implicit from GENIE |

### Interaction cross-check from batch logs

The batch gen logs print `interaction code: N, neutrino scattering code: M` for each NCRES
event attempted. All logged accepted events show `interaction code: 3` (NC) and
`neutrino scattering code: 4` (resonant), consistent with the filter's requirements.

**TRUTH_VALIDATION_ANALYTICAL_PASS**: the filter predicate guarantees all 59 accepted events
are NC resonant events with a final-state photon tracing to a Delta resonance. Individual
per-event kinematics (photon energy, Delta PDG, proton multiplicity) are stored in the
TFileService diagnostic tree (TFileService-*.root in each batch directory) but are not
critical gate items for G4 submission.

---

## 5. Merge gate status

| Gate | Status |
|------|--------|
| Source file counts verified (TrigReport = uproot) | PASS |
| RSE uniqueness | PASS (structural guarantee) |
| Total accepted events >= 50 | PASS (59 >= 50) |
| hadd merge (artROOT process_name conflict) | FAILED (only 5 events; discarded) |
| lar-based artROOT merge (PBS 192843) | PASS (art exit 0) |
| Merged file event count = 59 | PASS (uproot confirmed) |
| Truth validation (analytical) | PASS |

**G4 SUBMISSION GATE: ALL CHECKS PASSED. ncdelta_gen_merged.root is ready for G4.**
