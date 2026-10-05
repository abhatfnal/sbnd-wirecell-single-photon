# Baseline v0 Provenance Record

**Purpose**: Immutable record of all software and configuration inputs to `baseline_v0`.
Any future comparison baseline must record equivalent information.

**Created**: 2026-10-04

---

## Reconstruction software

| Component | Commit / Version | Notes |
|-----------|-----------------|-------|
| Wire-Cell Toolkit (WCT) | `251ff143` | "clus: preserve matching bundle provenance for NuGraph4" |
| larwirecell | `9295e2a3` | "feat(aiml): stream EventGraph over IPC without HDF5 handoff" |
| sbndcode | `v10_14_02_04` | LArSoft/SBND production release |
| Candidate build root | `/lus/eagle/projects/neutrinoGPU/abhat/sbnd/sample_generation_port/work/latest_wct_master_migration_candidate_20260930` | |
| WCT installed libs | `$CAND/install/wct-clean/lib` | |
| larwirecell installed libs | `$CAND/build/lwc-install-clean/lib` | |

## Frozen MC Wire-Cell configuration

| Item | Value |
|------|-------|
| Entry-point FCL | `wcls-img-clus-matching-xin-prod.fcl` |
| FCL SHA-256 | `f7cab672247827a81967ef7c4e966ffcfe39f78477c70446983939b9350bcdb9` |
| FCL source path | `/lus/eagle/projects/neutrinoGPU/abhat/sbnd/sample_generation_port/work/haiwang-current/integration-2026-09-08/reco-bundle-id-fix-validation-20260916/config-final/wcls-img-clus-matching-xin-prod.fcl` |
| Frozen config directory | `/lus/eagle/projects/neutrinoGPU/abhat/sbnd/sample_generation_port/work/haiwang-current/integration-2026-09-08/reco-bundle-id-fix-validation-20260916/config-final/` |
| Self-contained runtime snapshot | `/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/runtime/wire-cell-data` |

Config-final contains:
- `wcls-img-clus-matching-xin-prod.fcl` (entry point)
- `wcls-img-clus-matching-xin.jsonnet`
- `pr-operating-point.jsonnet`
- `particle_dataset.jsonnet`

## Simulation software

| Item | Value |
|------|-------|
| Generator FCL | `prodgenie_ncdelta_sbnd.fcl` |
| Generator FCL path | `/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/signal_mc/ncdelta/fcl/prodgenie_ncdelta_sbnd.fcl` |
| NC Delta filter (reference) | `NCDeltaRadiative_module.cc` |
| Reference source SHA-256 | `f8574e5fdf6d3f0d8794143aed31d2167ba592498fc50d61e2ff7e11e3f0c3e6` |
| Reference source path | `/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/signal_mc/ncdelta/src/NCDeltaRadiative_module.cc` |
| NC Delta filter (runtime) | Installed sbndcode v10_14_02_04 module (compilation of reference failed) |
| G4 FCL | `standard_g4_sbnd.fcl` |
| DetSim FCL | `standard_detsim_sbnd_bothrois.fcl` |
| Reco1 FCL | `reco1_nosupera_sbnd.fcl` (from ncdelta/fcl/) |

## NC Delta filter: reference vs runtime

The reference filter source (SHA `f8574e5f...`) failed to compile in the PBS container because
`TDirectory.h` is not reachable from the `art_root_io/TFileDirectory.h` include chain in the
sbndcode v10_14_02_04 environment. The ROOT_INCLUDE_PATH expansion produced empty tokens
that were passed as bare linker arguments, causing the build to fail.

As a fallback, the PBS script uses the filter as installed in sbndcode v10_14_02_04. This is
a DIFFERENT compiled object from the reference source. Known differences:

1. **FillTree() PDG argument**: The installed version passes the particle PDG code as the
   particle index in the ancestry loop, affecting which particle is recorded as the photon
   ancestor in the diagnostic output tree. This affects the recorded ancestor PDG, NOT the
   pass/fail selection logic.

2. **exit() in two error paths**: The installed version retains `exit()` calls in two error
   paths rather than the reference's `return false`. If these paths fire, the job would abort
   without completing the event. All 12 batches processed event 1000 as the last event
   (confirmed from TrigReport), so no exit() path fired.

3. **Selection predicate**: The truth selection logic (CCNC check, resonant mode check, photon
   in final state, Delta ancestry) is IDENTICAL between the installed and reference versions.
   The filter's pass/fail decision for each event is unchanged.

**Implication**: All 59 accepted events were correctly selected as NC resonant events with
a photon tracing to a Delta0 or Delta+. The diagnostic tree quantities (photon ancestor PDG)
may differ from what the reference version would have recorded, but the event selection is
unaffected. Do NOT claim the reference module generated the batch events. Do NOT regenerate
the batches solely because the installed module was used -- the selection predicate is
identical.

## Container and UPS environment

| Item | Value |
|------|-------|
| Container | `/lus/grand/projects/neutrinoGPU/software/containers/slf7.sif` |
| LArSoft squashfs | `/lus/eagle/projects/neutrinoGPU/larsoft_hpc/images/larsoft-v10_14_02.squashfs` |
| sbndcode squashfs | `/lus/eagle/projects/neutrinoGPU/larsoft_hpc/images/sbnd-v10_14_02_04_delta.squashfs` |
| sbndcode env | `/lus/eagle/projects/neutrinoGPU/larsoft_hpc/envs/sbndcode-v10_14_02_04.env` |
| BNB flux files | `/lus/grand/projects/neutrinoGPU/simulation_inputs/FluxFiles/gsimple_april07_baseline_*_redecay_wkaonwgh.root` |

## PBS allocation

| Item | Value |
|------|-------|
| Queue | `by-gpu` |
| Account | `neutrinoGPU::wirecell_2026` |

## NC Delta signal sample — batch generation design

| Parameter | Value |
|-----------|-------|
| Batches | 10 |
| NCRES attempts per batch | 1000 |
| Total NCRES attempts | 10,000 |
| Expected acceptance | ~0.6% |
| Expected accepted events | ~60 |
| Target accepted events | ~50 |
| firstRun per batch | batch_id × 10 (batch 1 → run 10, batch 2 → run 20, ...) |
| Output location | `ncdelta_50evt/gen/batch_NN/ncdelta_gen_batch_NN.root` |

## NC Delta truth category definitions

For truth preselection (Phase B), categories are defined as follows (generator-level truth,
post-GENIE FSI, before Geant4):

### Containment classes (applied to leading photon)

All boundaries refer to the SBND active volume, which is nominally:
`−200 < x < 200 cm`, `−200 < y < 200 cm`, `0 < z < 500 cm`

- **Clearly contained**: conversion point and shower axis (projected ≥40 cm from conversion)
  both within active volume
- **Partially contained**: conversion point within active volume, but shower projects near
  a boundary (within 20 cm in at least one dimension) OR active deposited energy < 50% of
  photon energy
- **Boundary/corner loss**: conversion point within 5 cm of any boundary, OR photon vertex
  within 10 cm of boundary with very short conversion gap (< 5 cm)
- **Not in TPC**: photon vertex and/or conversion point outside active volume entirely

These definitions are fixed for baseline_v0 and must not be adjusted to improve any
efficiency metric.

## Engineering reference sample

The 3-event engineering sample established truth/reco correspondence for the chain:

| Location | `/lus/eagle/projects/neutrinoGPU/abhat/sbnd/single_photon/signal_mc/ncdelta/end_to_end_3evt/` |
|----------|------|
| Gen output | `test/gen/ncdelta_gen_test.root` (DO NOT OVERWRITE) |
| Event 0 ART event | run=1 subrun=0 event=7 |
| Event 1 ART event | run=1 subrun=0 event=215 |
| Event 2 ART event | run=1 subrun=0 event=244 |

## Flag semantics (immutable for this baseline)

These definitions must be used consistently in all tables and reports:

| Flag | Correct interpretation |
|------|----------------------|
| `cosmic_flag=1, cosmic_filled=0` | Default/unfilled state; NOT cosmic rejection |
| `cosmict_flag` | 0 in current sample; cosmic BDT not evaluated |
| `photon_flag` | Legacy MicroBooNE photon-tagger response (binary) |
| `nue_score=-15` | Sentinel: `br_filled=0` (upstream chain broke); NOT a physical BDT score |
| `kine_pio_flag` | Reconstructed two-shower pi0 hypothesis; NOT pi0 truth |

## PBS job IDs

| Stage | Batch | PBS job ID | Submitted | Status |
|-------|-------|-----------|-----------|--------|
| gen | 01 | 192796 | 2026-10-04 | ZERO_ACCEPTED_VALID (0 events, exit 134) |
| gen | 02 | 192797 | 2026-10-04 | ZERO_ACCEPTED_VALID (0 events, exit 134) |
| gen | 03 | 192798 | 2026-10-04 | PASS (5 events, exit 134) |
| gen | 04 | 192799 | 2026-10-04 | PASS (6 events, exit 134) |
| gen | 05 | 192800 | 2026-10-04 | PASS (9 events, exit 134) |
| gen | 06 | 192801 | 2026-10-04 | PASS (5 events, exit 134) |
| gen | 07 | 192802 | 2026-10-04 | PASS (9 events, exit 134) |
| gen | 08 | 192803 | 2026-10-04 | PASS (4 events, exit 134) |
| gen | 09 | 192804 | 2026-10-04 | PASS (2 events, exit 134) |
| gen | 10 | 192805 | 2026-10-04 | PASS (6 events, exit 134) |
| gen | 11 (top-up) | 192839 | 2026-10-04 | PASS (3 events, exit 134) |
| gen | 12 (top-up) | 192840 | 2026-10-04 | PASS (10 events, exit 134) |
| gen-merge | — | 192843 | 2026-10-04 | PASS (59 events, art exit 0, 369K) |
| g4 (attempt 1) | all | 192930 | 2026-10-04 | FAIL: G4 crash at event 1 (ProcessManager NULL for proton, PDG 2212) — see G4_CRASH note |
| g4 (diag) | batch_03 | 192934 | 2026-10-04 | PASS: batch_03 alone exit 0, 5 events, 7.9 MB, 0 Run0201 warnings |
| g4 (per-batch) | batches 03-09,12 | 192936[3..9,12] | 2026-10-04 | PASS (8/10 elements; 5+6+9+5+9+4+2+10=50 events) |
| g4 (per-batch) | batch_10,11 | 192936[10,11] | 2026-10-04 | FAIL exit 143 (SIGTERM): PBS packed both onto sophia-gpu-02; node-level kill at 14:34:45 after 4 min; G4 was processing events (see node-kill note) |
| g4 (per-batch retry) | batch_10,11 | 192939[] (-J 10-11) | 2026-10-04 | PASS: batch_10 exit 134 (6 events, nEvts=6 from TimeTracker); batch_11 exit 0 (3 events, GATE PASS) |
| g4-merge | all | 192937 | 2026-10-04 | ABORTED by PBS server (dependency afterok:192936 without [] suffix not resolved for array job; resubmit manually after validating all 10 batch outputs) |
| g4-merge (retry) | all | 192940 | 2026-10-04 | PASS (exit 0, 91 MB, 59 events, 40 sec; GATE PASS) |
| truth extract (attempt 1) | all | 192943 | 2026-10-04 | FAIL: PyROOT TBranchElement::GetAddress() TypeError; abandoned PyROOT |
| truth extract (attempt 2) | all | 192952 | 2026-10-04 | FAIL: gallery C++ but MCParticle tag missing process name ("G4"); conv_gap=-1 all events |
| truth extract (attempt 3) | all | 192956 | 2026-10-04 | FAIL: gallery C++ with Process()=="primary" photon search; conv_gap=-1 (daughters not kept) |
| truth extract (attempt 4) | all | 192960 | 2026-10-04 | FAIL: gallery C++ with Mother()==0 + daughter search; daughters not present in kept list |
| truth extract (attempt 5) | all | 192965 | 2026-10-04 | PASS: gallery C++ with Mother()==0 + EndX/Y/Z (photon conv point); 59/59 rows; ncdelta_truth.csv |
| detsim (attempt 1) | all | 192942 | 2026-10-04 | FAIL exit 143 (SIGTERM after 9 sec; sophia-gpu-02 node kill, same root cause as batch_10/11) |
| detsim (retry) | all | 192961 | 2026-10-04 | PASS (exit 0, 182 MB, 59/59 events, walltime 3:58:59) |
| reco1 | all | 193043 | 2026-10-04 | PASS (exit 0, 87 MB, 59/59 events, walltime 0:01:44) |
| wirecell | evt 0-4 | 193057[] | 2026-10-04 | FAIL exit 24 (all 5 elements): bash -lc heredoc quoting bug passed empty INFILE to lar; cascade aborted 193058-193060 |
| wirecell | evt 0 (test) | 193063 | 2026-10-04 | PASS exit 0 (rewritten script: inner script to file, FHICL_FILE_PATH fixed): tracking-pr.root 260K, nugraph.h5 139K, walltime 0:00:40 |
| wirecell | evt 1-5 | 193064[] | 2026-10-04 | PASS exit 0 |
| wirecell | evt 6-10 | 193065[] | 2026-10-04 | PASS exit 0 |
| wirecell | evt 11-15 | 193066[] | 2026-10-04 | PASS exit 0 |
| wirecell | evt 16-20 | 193067[] | 2026-10-04 | PASS exit 0 |
| wirecell | evt 21-25 | 193068[] | 2026-10-04 | PASS exit 0 |
| wirecell | evt 26-30 | 193069[] | 2026-10-04 | PASS exit 0 |
| wirecell | evt 31-35 | 193070[] | 2026-10-04 | PASS exit 0 |
| wirecell | evt 36-40 | 193071[] | 2026-10-04 | PASS exit 0 |
| wirecell | evt 41-45 | 193072[] | 2026-10-04 | PASS exit 0 |
| wirecell | evt 46-50 | 193073[] | 2026-10-04 | PASS exit 0 |
| wirecell | evt 51-55 | 193074[] | 2026-10-04 | PARTIAL: elements 52-55 PASS; element 51 FAIL exit 143 (sophia-gpu-02 node kill after 26 sec) |
| wirecell | evt 56-58 | 193075[] | 2026-10-04 | PASS exit 0 |
| wirecell | evt 51 (retry) | 193076 | 2026-10-04 | PASS exit 0 (walltime 34 sec, sophia-gpu-02; tracking-pr.root 257K, nugraph.h5 126K) |

## G4 crash analysis (2026-10-04)

PBS 192930 ran `standard_g4_sbnd.fcl` on `ncdelta_gen_merged.root` (59 events) and crashed
before writing any events. Fatal exception:

```
G4SteppingManager::GetProcessNumber()
ProcessManager is NULL for particle = proton, PDG_code = 2212
G4Track: track ID = 3, parent ID = 0, proton, 405 MeV, inside volTPCActive_PV
```

**Crash characterizes**:
- Output file has no Events tree (0 events written)
- Crash is deterministic (same track/position in both container lar runs)
- Same `standard_g4_sbnd.fcl` and sbndcode v10_14_02_04 worked correctly for fresh-50evt
  BNB events (which did NOT show Run0201 warnings)

**Root cause hypothesis**:
NC Delta MCTruth events contain 13-29 particles per event (high FSI particle counts from
GENIE), including excited Delta resonances (Delta+(1700), Delta0(1700), etc.). artg4++ in
sbndcode v10_14_02_04 encountered particles not in the QGSP_BERT_HP particle table and
attempted `G4VModularPhysicsList::RegisterPhysics()` 9 times after the Geant4 kernel
had left PreInit state. These registrations were correctly rejected (Run0201 warnings),
but the registration attempts corrupted the proton's ProcessManager, leaving it NULL at
tracking time.

**Evidence**:
- fresh-50evt G4 log: 0 Run0201 warnings, 50 events, art exit 0 (success)
- NC Delta G4 log: 9 Run0201 warnings, 0 events, SIGABRT at event 1

**Diagnostic result** (PBS 192934, 2026-10-04):
G4 on batch_03.root alone: EXIT 0, 5 events, 7.9 MB output, ZERO Run0201 warnings.
CONCLUSION: The crash is MERGE-SPECIFIC. Individual batch files run G4 correctly.
The merged file's 10 MCTruth branch names (one per process_name NCDeltaBatch03..12)
cause artg4++ to attempt 9 extra RegisterPhysics calls (one per extra branch), which
corrupts the proton's ProcessManager. The fix is to run G4 on individual batches and
merge the G4 outputs separately.

**What is demonstrated** (not claimed as a fully-traced internal mechanism):
G4 on the multi-process merged GEN file fails with the proton ProcessManager error.
G4 on the constituent single-process batch input (batch_03 alone) succeeds: exit 0,
5 events, 7.9 MB, zero Run0201 warnings. The exact internal artg4++ mechanism is
unconfirmed; the per-batch approach is the empirically validated workaround.

**Fix**: Per-batch G4 array (PBS 192936[]) runs G4 on each of the 10 accepted batches.
Merge job 192937 was ABORTED (dependency syntax issue; to be resubmitted manually
after all 10 batch outputs are validated). DetSim then runs on the merged G4 file.

## Node-level kill: batch_10 and batch_11 (2026-10-04)

PBS 192936[] elements 10 and 11 both failed with exit 143 (SIGTERM) after 4 minutes.
Diagnosis from `qstat -xf`:
- Both ran on the SAME node: `sophia-gpu-02` (PBS packed them together)
- Both killed at the same wallclock moment (~14:34:45 UTC)
- Memory used: ~2.5 GB each (well within 120GB allocation)
- G4 was actively processing events: messages.log shows event processing and photon
  library loading in progress at time of kill
- Root cause: node-level administrative kill (not a G4 or physics bug)
- Fix: resubmitted as 192939[] (-J 10-11); 8 already-complete batches will be skipped
  by the >10MB output guard in the PBS script

**Constraints**: Cannot modify the frozen Wire-Cell reconstruction. standard_g4_sbnd.fcl
is from sbndcode v10_14_02_04 (not the frozen WCT FCL); a G4-level workaround does not
violate the WCT freeze.

## Comparison target

This baseline (baseline_v0) is the fixed reference point for future comparison against:
- `SBND-adapted photon selection v1` (not yet developed)
- Any SBND-specific Wire-Cell reconfiguration

All comparison must use the same truth category definitions and the same flag semantics.

## Gen batch submission (2026-10-04T00:33:27Z)

- gen batch 01: 192766.sophia-pbs-01.lab.alcf.anl.gov
- gen batch 02: 192767.sophia-pbs-01.lab.alcf.anl.gov
- gen batch 03: 192768.sophia-pbs-01.lab.alcf.anl.gov
- gen batch 04: 192769.sophia-pbs-01.lab.alcf.anl.gov
- gen batch 05: 192770.sophia-pbs-01.lab.alcf.anl.gov
- gen batch 06: 192771.sophia-pbs-01.lab.alcf.anl.gov
- gen batch 07: 192772.sophia-pbs-01.lab.alcf.anl.gov
- gen batch 08: 192773.sophia-pbs-01.lab.alcf.anl.gov
- gen batch 09: 192774.sophia-pbs-01.lab.alcf.anl.gov
- gen batch 10: 192775.sophia-pbs-01.lab.alcf.anl.gov

## Gen batch RE-SUBMISSION after compile fallback fix (2026-10-04T00:38:06Z)

- gen batch 01 (retry): 192776.sophia-pbs-01.lab.alcf.anl.gov
- gen batch 02 (retry): 192777.sophia-pbs-01.lab.alcf.anl.gov
- gen batch 03 (retry): 192778.sophia-pbs-01.lab.alcf.anl.gov
- gen batch 04 (retry): 192779.sophia-pbs-01.lab.alcf.anl.gov
- gen batch 05 (retry): 192780.sophia-pbs-01.lab.alcf.anl.gov
- gen batch 06 (retry): 192781.sophia-pbs-01.lab.alcf.anl.gov
- gen batch 07 (retry): 192782.sophia-pbs-01.lab.alcf.anl.gov
- gen batch 08 (retry): 192783.sophia-pbs-01.lab.alcf.anl.gov
- gen batch 09 (retry): 192784.sophia-pbs-01.lab.alcf.anl.gov
- gen batch 10 (retry): 192785.sophia-pbs-01.lab.alcf.anl.gov

## Gen batch submission (2026-10-04T00:46:51Z)

- gen batch 01: 192786.sophia-pbs-01.lab.alcf.anl.gov
- gen batch 02: 192787.sophia-pbs-01.lab.alcf.anl.gov
- gen batch 03: 192788.sophia-pbs-01.lab.alcf.anl.gov
- gen batch 04: 192789.sophia-pbs-01.lab.alcf.anl.gov
- gen batch 05: 192790.sophia-pbs-01.lab.alcf.anl.gov
- gen batch 06: 192791.sophia-pbs-01.lab.alcf.anl.gov
- gen batch 07: 192792.sophia-pbs-01.lab.alcf.anl.gov
- gen batch 08: 192793.sophia-pbs-01.lab.alcf.anl.gov
- gen batch 09: 192794.sophia-pbs-01.lab.alcf.anl.gov
- gen batch 10: 192795.sophia-pbs-01.lab.alcf.anl.gov

## Gen batch submission (2026-10-04T00:50:11Z)

- gen batch 01: 192796.sophia-pbs-01.lab.alcf.anl.gov
- gen batch 02: 192797.sophia-pbs-01.lab.alcf.anl.gov
- gen batch 03: 192798.sophia-pbs-01.lab.alcf.anl.gov
- gen batch 04: 192799.sophia-pbs-01.lab.alcf.anl.gov
- gen batch 05: 192800.sophia-pbs-01.lab.alcf.anl.gov
- gen batch 06: 192801.sophia-pbs-01.lab.alcf.anl.gov
- gen batch 07: 192802.sophia-pbs-01.lab.alcf.anl.gov
- gen batch 08: 192803.sophia-pbs-01.lab.alcf.anl.gov
- gen batch 09: 192804.sophia-pbs-01.lab.alcf.anl.gov
- gen batch 10: 192805.sophia-pbs-01.lab.alcf.anl.gov

## Gen batch top-up submission (2026-10-04T03:59:33Z)

- gen batch 11 (top-up, firstRun=110): 192839.sophia-pbs-01.lab.alcf.anl.gov

## Gen batch top-up batch 12 (2026-10-04T04:05:02Z)

- gen batch 12 (top-up, firstRun=120): 192840.sophia-pbs-01.lab.alcf.anl.gov
