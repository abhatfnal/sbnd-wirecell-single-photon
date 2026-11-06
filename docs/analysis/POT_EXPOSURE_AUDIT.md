# POT / exposure audit of the listed merged CAFs

Scope: exactly the files in `manifests/bnb_cv.tsv.gz` (37,742) and `manifests/nuecc.tsv.gz` (11,441); data samples at the end.
Method: `scripts/exposure_scan.py` read **every listed file** (a few header branches + `TotalPOT`, `TotalEvents`, `TotalGenEvents`; nothing copied; 0 read errors).
Per-file rows: `/exp/sbnd/data/users/abhat/single_photon_ncdelta/exposure_scan/<sample>.jsonl`; summaries: `tables/pot/<sample>_summary.json`.
This is a *different production* from the earlier 10,002-event Sophia study; nothing is extrapolated from it. **No analysis weights are computed.**

## 1. How exposure is stored

| quantity | where | type / granularity |
|---|---|---|
| `rec.hdr.pot` | `recTree`, per event | float32; **non-zero only on the event with `first_in_subrun == 1`**, i.e. a per-file (per-subrun) number stored once |
| `TotalPOT` | TH1D in the file, bin 1 | float64; POT of the same unit (agrees with `rec.hdr.pot` to ~1e-10 relative summed over the whole CV sample) |
| `TotalGenEvents` | TH1D | number of **generated** events behind the file (50 per CV file, 125 per nueCC file; 0 for data) — includes events that did not survive into the CAF |
| `TotalEvents` | TH1D | events in the CAF (equals `recTree` entries) |
| `rec.hdr.ngenevt` | per event | same generated-event count (50 / 125) |
| `globalTree` / `metadata/metatree` | | systematics-weight definitions; `metatree` is empty here — carries no exposure |

Each CV file is exactly one (run, subrun): `rec.hdr.pot` has exactly one non-zero entry per file in **all 37,742 files**.

## 2. Results over the listed files

| | BNB CV | nueCC |
|---|---|---|
| files listed / scanned OK | 37,742 / 37,742 | 11,441 / 11,441 |
| CAF events (matches Haiwang's number) | 500,000 | 100,003 |
| `wc.valid == 1` events (matches) | 499,899 | 99,946 |
| zero-`TotalPOT` files | 0 | 0 |
| **Σ `TotalPOT`** | **2.71940e19** | **2.05827e21** |
| Σ `rec.hdr.pot` | 2.719402147e19 (equal to 1e-10) | 2.05657e21 (−0.08 %) |
| Σ `TotalGenEvents` | 1,887,100 (= 37,742 × 50) | 1,430,125 (= 11,441 × 125) |
| distinct (run, subrun) pairs | 37,742 (no duplicates) | 9,312 (**2,218 pairs appear in 2 files**) |
| files with `rec.hdr.pot` non-zero ≠ 1 times | 0 | 89 (two sub-runs inside one file; their `hdr.pot` sum matches `TotalPOT`) |
| files where `rec.hdr.pot` ≠ `TotalPOT` by >0.1 % | 0 | 131 (all with one sub-run; `hdr.pot` is 83–99 % of `TotalPOT`) |

### Duplicates and repeated entries
- **BNB CV:** no duplicated (run, subrun); no repeated POT entries.
- **nueCC:** the 2,218 shared (run, subrun) pairs are **not duplicate exposure**: the two files of each pair have *different* `TotalPOT` and different events (checked: 0 of 2,218 pairs have equal POT). They are independent generation jobs that reuse sub-run numbers. **Do not de-duplicate by (run, subrun)** and do not use (run, subrun, event) as a global key for MC; use (file, run, subrun, event).
- Events are never duplicated within a file; `recTree` and `recTreeWireCell` entries agree.

### `rec.hdr.pot` vs `TotalPOT`
Identical for CV. For nueCC they differ in 131 single-sub-run files (`hdr.pot` smaller by up to 17 %), Σ difference 0.08 % of the total. Cause not determined from the files (the histogram probably accounts for all input sub-run records, `rec.hdr.pot` only for the first stored event). The effect on a total is negligible, but a per-file weight would differ.

## 3. Recommendation

1. **Exposure of a set of listed MC files = Σ over the files of `TotalPOT` (bin 1 of the TH1D).** Read it per file and sum in float64. Do **not** sum `rec.hdr.pot` over events of a subset of events: a file truncated by an event cut loses its POT because it lives on `first_in_subrun`.
2. **Never de-duplicate by (run, subrun)** for MC. Treat each file as independent.
3. **Always carry per-file `TotalPOT` with the file**, so any subset of files (smoke tests, `--limit`, k-fold) gets its own exposure; for partial reads of a file, weight by the whole-file POT only if the whole file is used.
4. **Efficiency denominators/generated rates** use `TotalGenEvents` (all generated events, including those not in the CAF), not `TotalEvents`.
5. Keep `wc.valid == 0` events inside both numerator-failure and denominator accounting; they have a CAF entry and belong to the file's POT.
6. Write the exposure table to a small file alongside the manifest (`$SP_DATA/exposure_scan/<sample>.jsonl` already has it) and cite its provenance; assign weights only when the normalisation conventions below are settled.

## 4. Things to confirm with Haiwang / Hanyu (not blocking the framework)

- **nueCC normalisation is not CV-like:** Σ`TotalPOT`/Σ`TotalGenEvents` = 1.44e13 POT per generated event for CV but 1.44e15 for nueCC (exactly a factor ~100). The nueCC sample is an exclusive, filtered production. What `TotalPOT` means for it (flux-equivalent POT of the unfiltered generation vs. of the stored jobs) must be confirmed **before** adding nueCC to a composition with CV. It is currently used only as an MC shape/availability sample.
- Whether the 131 nueCC files with `hdr.pot ≠ TotalPOT` should use `TotalPOT` (recommended) or `hdr.pot`.
- The fg1 files are a seeded random subset of the SAM definitions, so these exposures describe the listed files, **not** the whole production.
- A BNB sample generated with cosmics overlaid: the POT of the neutrino sample vs the cosmic exposure of the MC (CORSIKA) should be documented before comparing with beam-off.

## 5. Data samples (summary; details in `DATA_EXPOSURE_NORMALIZATION.md`)

| | beam-on (open) | beam-off |
|---|---|---|
| files / events / `wc.valid` | 1,817 / 89,946 / 89,921 (all match Haiwang) | 1,058 / 49,970 / 49,917 (all match) |
| runs | 2 (18255, 18259); subrun id always 1 | 156 (18250–18592); subrun id always 1 |
| exposure information in the CAF | Σ`TotalPOT` = **4.62125e18 POT** (file POT 4.8e10–3.7e15; one non-zero `rec.hdr.pot` per file) | **Σ`rec.hdr.noffbeambnb` = 2,542,847** off-beam gates, exactly one non-zero entry per file; POT = 0 |
| missing | beam-on gate/trigger count, livetime | the matching beam-on gate count, run-matching |

The beam-off sample has no file in run 18255 and 4 files (200 events) in run 18259, so no run-matched scaling is possible; see the normalisation note.

## 6. nueCC stays control-only
See `NUECC_CONTROL_SAMPLE.md`: no rate is written for it by default.

## 7. Why 500,000 CAF events but 1,887,100 generated events? (read-only provenance investigation)

Sources read: Haiwang's `fg1/README.md` and `lists/pairs-mc-cv.tsv` (over XRootD), the CAFMaker source (`sbncode v10_31_00`), and the production fcl of the release used (`sbndcode v10_14_02_03` on CVMFS). The actual job configuration of the grid jobs is **not** accessible from EAF; the fcl below is the release default for the sample name `prodgenie_corsika_proton_rockbox0p1_sbnd`.

**1. What `TotalGenEvents` means.** `CAFMaker_module.cc` L876–885: for every process in the input file's history whose source is `EmptyEvent` (the generator job), it adds that job's `source.maxEvents`. So it is the number of events **requested at generation** (50 per file), not a count of events stored anywhere. `TotalPOT` (the `TotalPOT` histogram) is for MC the sum of `sumdata::POTSummary::totgoodpot` of the generator label (L1018–1021).

**2/3. Where the events are lost.** `lists/pairs-mc-cv.tsv` records the number of events in each **reco1** input file. For all 37,742 listed pairs the reco1 event count equals the CAF event count (Σ = 500,000; every file equal), so no event is lost in reco1→CAF or in the Wire-Cell merge. Per-file reco1 events range 3–26 (median 13) out of 50 generated. The reduction therefore happens in the **generation / neutrino-G4 job**, before detector simulation.

**4. The filter.** `prodgenie_corsika_proton_rockbox_sbnd.fcl` defines two trigger paths and the output (`prodgenie_rockbox_sbnd.fcl`: `SelectEvents: [simulatetpc, simulatedirt]`) keeps an event if it passes **either**:
- `simulatetpc`: `tpcfilter` = `GenNuFilter` with `VtxInTPC: true`: a generated neutrino vertex inside the TPC (`RecoUtils::IsInsideTPC`);
- `simulatedirt`: `!tpcfilter` and `dirtfilter` = `SimEnergyDepFakeTriggerFilter` on `largeantnu:…volTPCActive`: total energy deposited **in the TPC active volume by the neutrino-induced particles** inside the beam window (`BeamTimeMin −0.2 µs`, `BeamTimeMax 1.9 µs`) above `EnergyDeposit`, set to **0.1 MeV** by `prodgenie_corsika_proton_rockbox0p1_sbnd.fcl` (the "0p1" of the sample name).
Events with no in-TPC neutrino vertex and ≤0.1 MeV neutrino-induced active-volume deposit are never written. (For comparison the nueCC production, `…_ccnue_sbnd.fcl`, adds `ccnuefilter` = CC ν_e/ν̄_e with the vertex in the TPC: 7.0 % of generated events survive; this chain explains why that sample is so different, but what its `TotalPOT` then means was not established.)

**5. Does it only reject events that cannot pass the single-photon selection?** For neutrino-induced candidates: essentially yes. A rejected event has no in-TPC neutrino vertex and ≤0.1 MeV neutrino-induced deposit in the active volume in the beam window, so it cannot contain a neutrino-induced ≥20 MeV shower. It is **not** guaranteed for cosmic-induced candidates: the cosmic (CORSIKA) overlay is added after the filter (`corsika` comes after `tpcfilter`/`dirtfilter` in the paths), so cosmic-only spills are absent from the MC and a cosmic-driven candidate in such a spill is not represented. That component is the job of the beam-off sample. Evidence consistent with this: in the stored sample 54 % of events have no active-volume neutrino (`DIRT_NO_ACTIVE`), as expected from the dirt path.

**6. What `TotalPOT` corresponds to.** The POT of **all generated events**, not of the stored ones. Evidence from the files (all 37,742): POT per file is nearly constant (mean 7.21e14, σ/μ 9 %) and **uncorrelated with the number of stored events** (correlation 0.003), whereas POT per stored event varies by 29 %; POT per generated event = 1.441e13 with σ/μ 9 %. This matches the CAFMaker source (generator `POTSummary`).

**7. Is selected / TotalPOT a valid physical BNB rate?** Yes, as a **POT-normalised neutrino-induced background rate from the official filtered Gen2 CV sample**, with the cosmic caveat below.

*Confirmation from the official production (information supplied by the analyser from the official SBND Gen2 BNB CV production request):* the request explicitly uses `prodgenie_corsika_proton_rockbox0p1_sbnd.fcl`, `v10_14_02_03`, with an **expected filter efficiency of 25 %**. This is exactly the fcl identified above, and the observed 500,000 / 1,887,100 = **26.5 %** is consistent with it: the reduction is the intended generator-level filtering, **not an unexplained loss**. (The grid-job fcl itself still cannot be inspected from EAF; the match rests on the request.)

- What the number is: selected events of the filtered MC / ΣTotalPOT, where `TotalPOT` is the POT of all generated events. Because the filter removes only throws with no in-TPC neutrino vertex and ≤0.1 MeV neutrino-induced active-volume deposit, no neutrino-induced selectable activity is lost, and the rate is a rate of neutrino-induced background.
- **Caveat — cosmic-only backgrounds are not represented.** The cosmic (CORSIKA) overlay is added *after* the neutrino-activity filter, so the rejected generator throws carry no cosmic-driven candidates in the MC. A cosmic-driven candidate in a spill without neutrino activity is therefore absent from this rate; **the cosmic component must be supplied by beam-off data** (whose scale is unresolved, `DATA_EXPOSURE_NORMALIZATION.md`). The rate must not be quoted as a total background prediction.
- Still unestablished: the exact meaning of `TotalPOT` weighting for filtered *dedicated* samples (nueCC; see `NUECC_CONTROL_SAMPLE.md`); the Poisson errors are on the raw count only (no systematics).

**Remaining question for Haiwang (nueCC only):** the nueCC sample belongs to the Gen2 rare-xsec filtered production; what is the filter / POT weighting convention (the CV question is closed).
