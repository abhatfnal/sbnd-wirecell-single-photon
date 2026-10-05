# Part E: Final Validated Physics Numbers

**Date**: 2026-10-05
**Sample**: 59 NC Delta radiative events, SBND `baseline_v0` (frozen reconstruction)
**Scorer**: `score_microboone_bdts.py` with tanh-corrected BDT evaluation
**Cross-validation**: 132/132 PASS vs ROOT TMVA (max |diff| = 4.94e-7)

All numbers below are **validated**. Frozen files are not modified. No thresholds tuned.
No truth quantities substituted for reconstruction quantities.

---

## 1. Sample composition

| Category | N | Fraction |
|----------|---|---------|
| Total events | 59 | 100% |
| 0p (no reco proton > 35 MeV KE) | 27 | 45.8% |
| Np (≥1 reco proton > 35 MeV KE) | 30 | 50.8% |
| UNCLASSIFIABLE_NO_KINE | 2 | 3.4% |

*Proton threshold: T_kine branch `kine_particle_type == 2212` AND `kine_energy_particle > 35 MeV`.*

---

## 2. Neutrino candidate reconstruction rate

| Outcome | N |
|---------|---|
| Neutrino candidate found (T_tagger present) | 57 / 59 |
| No neutrino candidate (T_tagger absent) | 2 / 59 |

Events without a neutrino candidate: **evt_0039, evt_0052** (also have no T_kine → UNCLASSIFIABLE).

---

## 3. Photon shower accessibility

Of the 57 events with a neutrino candidate:

| Shower accessibility | N |
|---------------------|---|
| `shw_sp_filled = 1` (shower features available) | 33 |
| `shw_sp_filled = 0` (shower inaccessible at main vertex) | 24 |

The 33-event evaluable set is mechanically determined by `shw_sp_filled`. All 33 are evaluable
for all 4 BDTs simultaneously.

---

## 4. BDT score ranges (tanh-transformed, all in [-1, 1])

| BDT | Score range | Mean |
|-----|-------------|------|
| `single_photon_numu` | [−0.999, +0.999] | +0.103 |
| `single_photon_other` | [−0.989, +0.988] | −0.236 |
| `single_photon_ncpi0` | [−0.985, +0.709] | −0.216 |
| `single_photon_nue` | [−0.997, +0.877] | −0.492 |

Scores are in `[-1, 1]` (range of `tanh`). The nue threshold `−1.0` is the mathematical
minimum and passes all events.

---

## 5. Cut flow (MicroBooNE nominal, PRE-FV)

FV cut (`5 < reco_nuvtxX < 250 cm`) is not applied — SBND FV not defined for `baseline_v0`.

| Cut step | N | 0p | Np |
|----------|---|----|----|
| Total events | 59 | 27 | 30 |
| Has neutrino candidate | 57 | 27 | 30 |
| `shw_sp_n_20mev_showers > 0` | 33 | 18 | 15 |
| All 4 BDTs evaluable | 33 | 18 | 15 |
| `numu_score > 0.4` | 13 | 10 | 3 |
| `other_score > 0.2` | 7 | 5 | 2 |
| `ncpi0_score > -0.05` | 4 | 3 | 1 |
| `nue_score > -1.0` | 4 | 3 | 1 |
| `shw_sp_n_20br1_showers == 1` | **3** | **2** | **1** |

---

## 6. Final selected events (3/59)

| Event | cat | numu | other | ncpi0 | nue | shw_energy (MeV) |
|-------|-----|------|-------|-------|-----|-----------------|
| evt_0005 (run=40, evt=142) | 0p | 0.9735 | 0.5941 | 0.2430 | 0.7248 | 344.0 |
| evt_0015 (run=50, evt=458) | Np | 0.9966 | 0.9876 | 0.3121 | −0.3523 | 496.4 |
| evt_0036 (run=80, evt=399) | 0p | 0.4639 | 0.5262 | 0.3938 | −0.9967 | 210.5 |

**Selection efficiency (pre-FV): 3/59 = 5.1%** (2 0p + 1 Np).

Note on evt_0036: `nue_score = -0.9967` passes the cut (`nue > -1.0`) with 0.3% margin.
This is physically valid — tanh(x) = -0.9967 corresponds to raw sum x ≈ -3.06, which is within
the observed raw score range.

---

## 7. Shower reconstruction failure breakdown (24 events with shw_sp_filled=0)

| Failure mode | N | Implication |
|-------------|---|-------------|
| COMPANION_CLUSTER_SHOWER_INACCESSIBLE | 10 | Fix: extend tagger to companion clusters |
| SHOWER_RECONSTRUCTED_ELSEWHERE_UNASSOCIATED | 4 | Fix: vertex-shower map population issue |
| SEVERE_IMAGING_UNDERRECO | 10 | No fix: shower not reconstructed at all |

---

## 8. Software vs reconstruction reach

| Metric | Value |
|--------|-------|
| Events with scorer output (all 4 BDTs) | 33/59 |
| Software loss | 0 (every event with shw_sp_filled=1 is scored) |
| Reconstruction limit (shw_sp_filled=0) | 24/59 events; irrecoverable by offline scorer |
| Recoverable by companion-cluster fix | ≤10 events (10/24 confirmed companion cluster) |

---

## 9. ROOT/TMVA cross-validation

| Metric | Value |
|--------|-------|
| Events validated | 33 (all evaluable) |
| Models validated | 4 (numu, other, ncpi0, nue) |
| Total score comparisons | 132 |
| PASS (|diff| < 1e-4) | 132 / 132 |
| Maximum absolute difference | 4.94e-7 |
| Mean absolute difference | ~1.5e-7 |
| Critical finding | tanh transform applied by TMVA; nue threshold -1.0 is a no-cut |

---

## Recommendation

**Investigate the 4 `SHOWER_RECONSTRUCTED_ELSEWHERE_UNASSOCIATED` events first.**

These have large EM showers (53–449 MeV) in the main cluster (`kine_energy_included=1`)
that NeutrinoKinematics reconstructed but singlephoton_tagger did not route to the
vertex-shower map. This is likely a vertex-shower map population issue — narrower scope
than the companion cluster extension and could recover 4 additional events.

Do NOT implement any fix in `baseline_v0`. All reconstruction changes require a new WireCell
run. The companion cluster extension (10 events) remains the larger-impact path but is a
more complex code change.

Do NOT tune cut thresholds. The MicroBooNE thresholds are frozen and calibrated on
MicroBooNE data. Any SBND optimization requires a separate SBND signal/background study.
