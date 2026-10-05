# NC Delta G4 Validation

**Stage**: standard_g4_sbnd.fcl (sbndcode v10_14_02_04)
**Input**: `g4/ncdelta_g4_merged.root` (91 MB, merged from 10 per-batch G4 outputs)
**Validated**: 2026-10-04

---

## Summary: PASS

| Check | Result |
|-------|--------|
| G4 per-batch completion | 10/10 batches PASS |
| Event preservation | 59/59 |
| MCTruth branches present | YES (31 branches across 10 process names) |
| GTruth branches present | YES (20 branches) |
| MCParticle (largeant__G4) branch | YES |
| SimPhoton branches | YES (pdfastsim + pdfastsimout) |
| SimEnergyDeposit branches | YES (11 detector-volume branches) |
| Duplicate RSEs | NONE |

---

## Per-batch G4 status

| Batch | PBS job | Events | Exit | Notes |
|-------|---------|--------|------|-------|
| 03 | 192936[3] | 5 | 0 | GATE PASS |
| 04 | 192936[4] | 6 | 134 | GATE PASS (destructor crash, valid output) |
| 05 | 192936[5] | 9 | 134 | GATE PASS |
| 06 | 192936[6] | 6 | 134 | GATE PASS |
| 07 | 192936[7] | 9 | 134 | GATE PASS |
| 08 | 192936[8] | 4 | 134 | GATE PASS |
| 09 | 192936[9] | 2 | 134 | GATE PASS |
| 10 | 192939[10] | 6 | 134 | GATE PASS (first attempt 192936[10] killed by node event on sophia-gpu-02) |
| 11 | 192939[11] | 3 | 0 | GATE PASS |
| 12 | 192936[12] | 10 | 134 | GATE PASS |

Exit 134 = SIGABRT in destructor. Known pattern for sbndcode v10_14_02_04 G4 jobs;
output file is complete and valid (all events written before destructor runs).

---

## G4 merge

| PBS job | Input | Exit | Output size | Events |
|---------|-------|------|-------------|--------|
| 192940 | 10 batch files (batch_03..12) | 0 | 91 MB | 59 |

Merge FCL: `jobs/g4/fcl/ncdelta_g4_merge.fcl` (process_name: NCDeltaG4Merge)

---

## Branch inventory (merged file)

| Category | Count | Example branch |
|----------|-------|----------------|
| Total top-level | 116 | |
| MCTruth | 31 | `simb::MCTruths_generator__NCDeltaBatch03.` |
| GTruth | 20 | `simb::GTruths_generator__NCDeltaBatch03.` |
| MCParticle | 4 | `simb::MCParticles_largeant__G4.` |
| SimPhoton | 4 | `sim::SimPhotonsLites_pdfastsim_Reflected_G4.`, `sim::SimPhotonsLites_pdfastsimout__G4.` |
| SimEnergyDeposit | 11 | `sim::SimEnergyDeposits_largeant_LArG4DetectorServicevolTPCActive_G4.` |

Each batch contributes its own MCTruth/GTruth branch (by process_name), so 31 MCTruth
branches = 20 Gen + 11 Assns entries across NCDeltaBatch03..12.

---

## RSE inventory (59 events)

See `tables/g4_event_inventory.csv` for per-event run/subrun/event numbers.
Run assignments: batch_NN uses run = NN*10 (batch_03 -> run=30, ..., batch_12 -> run=120).
All subrun = 0. Event numbers are GENIE event indices within each batch's 1000 attempts.

---

## Truth quantities (9-item report)

Extracted via gallery C++ macro (`jobs/truth/extract_ncdelta_truth.C`, PBS 192965).
Source: `tables/ncdelta_truth.csv` (59 rows). All quantities are generator-level (MCTruth)
except conv_gap which uses MCParticle EndX/Y/Z (G4 photon termination point).

### 1. G4 stage: PASS (59/59 events)

### 2. Event preservation: 59/59

### 3. Truth-clean event count
- All 59/59 events: NC (is_NC=1), nu_mu (PDG=14), resonant mode (mode=1) — clean sample.
- **Anomalous**: 1/59 events (Batch07/run=70/evt=746) shows n_photons_fs=0 in MCTruth
  (StatusCode==1 filter) but has a photon in MCParticle (conv_gap=60.4 cm, conv outside AV).
  Root cause: GENIE StatusCode != 1 for the NC Delta photon in this event; photon exists
  but escaped AV before conversion. Event was accepted by the NC Delta filter — not regenerated.

### 4. Photon energy range
| Statistic | Value |
|-----------|-------|
| Minimum | 0.0 MeV (anomalous event above; 3.6 MeV for next lowest) |
| Maximum | 512.0 MeV |
| Median (58 events with photon) | 270.5 MeV |
| Range (58 events) | 3.6 – 512.0 MeV |

Expected for NC Δ → N + γ: ~50–500 MeV from Δ(1232) radiative decay.

### 5. Conversion-gap summary
- Valid gaps: 59/59 (all events; EndX/Y/Z always defined in MCParticle)
- Range: 0.2 – 91.9 cm
- Median: 20.0 cm
- Expected radiation length in LAr: ~14 cm; mean free path for pair production ~18 cm

### 6. Containment counts (of 59 events)
| Class | Count | Definition |
|-------|-------|-----------|
| clearly_contained | 44 | Conv point in AV, >20 cm from boundary |
| partially_contained | 6 | Conv point in AV, ≤20 cm from boundary |
| boundary_corner | 3 | Conv point within 5 cm of boundary |
| outside_av | 6 | Photon vertex or conv point outside AV |

Vertex in active volume: 55/59. Conversion in active volume: 55/59.

### 7. Pi0-containing events
1/59 (Batch05/run=50/evt=449): n_pi0_fs=1, n_photons_fs=2, nu_E=1.61 GeV.
NC resonant event with both Δ radiative photon and pi0 in final state from FSI.

### 8. Multi-photon events
- 2-photon events: 5/59 (Batch05/evt=449, Batch07/evt=55 plus 3 others)
- 1-photon events: 53/59
- 0-photon events: 1/59 (anomalous StatusCode case above)

### 9. Proton multiplicity distribution
| n_protons | Count | Notes |
|-----------|-------|-------|
| 0 | 18 | |
| 1 | 28 | |
| 2 | 2 | |
| 3 | 3 | |
| 4 | 2 | |
| 5 | 2 | |
| 8 | 1 | GENIE FSI intranuclear cascade |
| 10 | 2 | GENIE FSI intranuclear cascade |
| 16 | 1 | GENIE FSI intranuclear cascade (Ar-40 nuclear breakup) |

High multiplicity (≥5 protons): 4/59 events. These are GENIE FSI artifacts where the residual
Ar-40 nucleus undergoes intranuclear cascade after the primary interaction. Accepted as valid
NC Delta events since the filter selection predicate (photon + Delta ancestry) is satisfied.
