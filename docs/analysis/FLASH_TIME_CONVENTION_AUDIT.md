# Flash-time data/MC offset audit (read-only; nothing corrected)

**Verdict: unresolved — ask Haiwang.** The offset is real and its likely origin is an optical-timing reference convention, but no document or configuration accessible from EAF states that the offset is expected.

## 1. What the data show (`wc.T_tagger.flash_time_us` of the in-window candidates, `wc.valid` events, all files)

| sample | candidates | min | 5 % | median | 95 % | max | shape |
|---|---|---|---|---|---|---|---|
| bnb_cv | 241,845 | 0.200 | 0.279 | 0.966 | 1.660 | 2.198 | flat from 0.2 to ≈1.7 µs, sharp drop after 1.7 (5.7k in 1.7–1.8 bin, ~60 per 0.1 µs above) |
| nuecc | 98,576 | 0.200 | 0.281 | 0.970 | 1.658 | 2.148 | same as CV |
| beam_on_open | 42,316 | 0.201 | 0.599 | 1.289 | 1.984 | 2.197 | flat from ≈0.5 to ≈2.0 µs, ~85 per 0.1 µs below 0.5 and above 2.1 |
| beam_off | 4,733 | 0.200 | 0.300 | 1.180 | 2.096 | 2.200 | broad, no sharp edges (cosmics) |
| final selected CV / beam-on / beam-off | 649 / 77 / 6 | 0.203 / 0.512 / 0.469 | | 1.02 / 1.28 / 1.12 | | 1.73 / 2.10 / 2.11 | follows its sample |

The beam spill is 1.6 µs wide. In both CV and beam-on the flat (neutrino/beam) plateau is ≈1.5 µs wide; it is shifted by **≈ +0.3 to +0.35 µs in beam-on relative to CV**. The MC plateau runs right up to the lower window edge (0.2 µs), i.e. MC is not seen to turn on before the window edge.

## 2. Configuration found

- Wire-Cell beam window (same jsonnet for data and MC): `sbnd-pr-stage.jsonnet` `beam_window: [0.2 µs, 2.2 µs]` on the matched flash time, also `clus.jsonnet` `beam_window_low/high = 0.2/2.2 µs` (PR #543 tree, `/exp/sbnd/app/users/yuhw/wct-pr543/cfg/pgrapher/experiment/sbnd/`). This explains the hard 0.2 / 2.2 limits of the distributions; it does not explain the shift of the plateau.
- Data chain: step 1 runs `wcls-img-clus-matching-data.fcl` on **FrameShift**-processed reco1 (`run_frameshift.fcl`, `frameshift_sbnd_data.fcl` of `sbndcode v10_14_02_04`): `RawTSCorrection 367000` (367 µs), `ShiftRWM2Gate 1738` (ns), **`ShiftData2MC: 0`**, timing references from `pmtdecoder`/`crtstrips`/`tdcdecoder`/`ptbdecoder`, beam gate HLT 26 / off-beam gate HLT 27. The flashes are read through `wclsOpHitSource/wclsOpFlashSource` "exactly as" the frameshift product defines. So the data optical time is referenced to the trigger/RWM and a data→MC shift parameter exists but is set to 0 in this release.
- MC generation window (filter) is [−0.2, 1.9] µs on the G4 time (`simenergydepfaketriggerfilter.fcl`): the MC time origin is the spill start; the data origin is the DAQ timing reference.
- Both stored flash definitions are the same branch (`flash_time_us`, `T_tagger`; `T_bundle`/`T_flash` carry the same quantity per bundle), so a different stored-branch definition is not indicated.

## 3. Candidate explanations (none established)

- different time reference between data (DAQ/RWM/trigger, FrameShift) and MC (generator spill time): plausible, since `ShiftData2MC = 0` means no alignment is applied;
- real neutrino time-of-flight/beam-structure offsets in data: the offset is of the order of hundreds of ns, which is too large to be a pure beam-structure effect without a documented convention;
- data/MC optical timing differences (PMT transit/electronics), not examined.

## 4. Consequence (not quantified, nothing changed)

Both samples go through the same 0.2–2.2 µs window and the same candidate selection. Because the MC plateau reaches the lower edge, MC beam events at <0.2 µs (if any) would be lost while the data plateau is fully inside the window; the size of any resulting acceptance difference is not known. Flash time is not a baseline cut variable, so the baseline counts are unchanged; a data/MC comparison near the window edges should not be made until the convention is clarified.

## 5. End

**unresolved — ask Haiwang:** is the ≈+0.3 µs beam-on vs MC offset of `flash_time_us` an expected consequence of the FrameShift reference (RWM/trigger) and `ShiftData2MC = 0`; is the MC spill truncated by the 0.2 µs window edge; should the data be shifted before comparing?
