# Beam-off / beam-on exposure normalisation audit

## 0. Update 2026-11-09: source audit of the gate counters (read this first; supersedes the statements it contradicts below)

**No scale factor is computed, assumed or stored. The two quotients that could be formed from the counters below are deliberately NOT formed.**

**What `rec.hdr.noffbeambnb` is (SOURCE: sbncode `CAFMaker_module.cc` lines 948, 1009, 2876; `SBNDBNBEXTRetriever_module.cc`; sbnanaobj `SRHeader.h:51`; commits in `WIRECELL_SOURCE_CONVENTIONS_AUDIT.md` section 7).** `SBNDBNBEXTRetriever::produce` reads the PTB container fragment of every off-beam event and takes `PTBInfo.GateCounter` (`extractPTBInfo(..., 4)`): the number of BNB gates counted **since the previous trigger**; it keeps `TotalEXTCounts += GateCounter` and writes one `sbn::EXTCountInfo{gates_since_last_trigger}` per event into the **sub-run**. `CAFMaker` sums `spill.gates_since_last_trigger` over the sub-run (`fOffbeamBNBGates`) and writes it into `rec.hdr.noffbeambnb` of the **first event of the sub-run** (`if (fFirstInSubRun)`), together with `rec.hdr.pot`. So it is **the number of off-beam BNB gates of the sub-run, counted by the PTB between the EXT triggers, before any software filtering; neither raw triggers nor post-filter events.** [measured: 1,058 files, one non-zero entry per file, sum 2,542,847.]

**The beam-on counterpart EXISTS in the CAF (the earlier version of this note was wrong to say it does not): `rec.hdr.nbnbinfo`.** `CAFMaker` writes `rec.hdr.nbnbinfo = fBNBInfo.size()` (the number of `BNBSpillInfo` entries of the sub-run; `FillExposure.cxx`: one entry per spill, `subRunPOT += info.POT()`) on the same first event, and `rec.hdr.pot` is the sum of those spills' POT. `SBNDBNBRetriever` (beam-on) counts `TotalBeamSpills += number_of_gates_since_previous_event` (the same PTB `GateCounter`, via `extractPTBInfo(..., 2)`) but only logs it (`LogDebug`); the stored product is one `BNBSpillInfo` per spill matched to the beam database (`matchMultiWireData`), and the retriever logs `"WRONG"` at debug level when the matched count differs from the PTB gate count. [measured: 1,817 beam-on files, exactly one non-zero `nbnbinfo` per file, **Σ nbnbinfo = 960,047** spills, Σ `rec.hdr.pot` = 4.62125260e18 = Σ `TotalPOT` (agrees to 1.5e-9), `noffbeambnb` = 0; `tables/pot/gate_counters_summary.json`.]

| quantity | beam-on open (runs 18255, 18259) | beam-off (InTime-Run1) |
|---|---|---|
| files / events in the CAFs | 1,817 / 89,946 | 1,058 / 49,970 |
| gate counter | Σ `nbnbinfo` = 960,047 (matched BNB spills) | Σ `noffbeambnb` = 2,542,847 (PTB off-beam BNB gates) |
| events recorded per counted gate | 9.4 % | 2.0 % |
| runs | 2 (18255: 1,329 files; 18259: 488) | 156 (18250-18592); **no file in run 18255**, 4 in 18259 |

**SAM (read-only, `env/sam_eaf.sh`).** The reco1 and raw-parent file metadata carry run, stream (`bnblight` / `offbeamlight`), trigger menu (`configuration.name`: `opsFullTriggerMenuP3_ExtraMTCA5-5-00002` on, `caenPUSHbnbZeroBias5-00003` off), `sbn_dm.event_count` (the raw-file trigger count; `0` for many off-beam raw files; SAM cannot sum it over the definitions: "Event count: None"), parentage, production tags. **No SAM key holds a gate count, livetime or exposure.** Definition totals (reco1): beam-off 49,020 files / 2,233,625 events (the fg1 beam-off list is a 1,096-file random subset, 1,058 of whose CAFs hold events); beam-on 1,820 files.

**Remaining blocker: ONE precise question for the data-quality / run-database owners.** *Is the approved beam-off scale for the open beam-on data (runs 18255, 18259) built from the stream gate counters, `Σ rec.hdr.nbnbinfo (beam-on) / Σ rec.hdr.noffbeambnb (beam-off)`, or from recorded-trigger counts (pre-filter events of the `bnblight` and `offbeamlight` streams) — given that the two streams record 9.4 % and 2.0 % of their counted gates respectively, so the two choices differ by a factor of ~4.8 — and is using the InTime-Run1 beam-off sample, which has no run-18255 files, for those runs acceptable?* Everything else (the exact meaning and filling of both counters, the files used, their sums, the stream/trigger-menu identities, parentage) is established above and in `tables/pot/`. Until it is answered, beam-off remains **shape only** and `prediction.B_COSMIC` stays UNRESOLVED (the prediction object refuses totals, purity, S/B and significance).


**No scale factor is computed or assumed here.** This note records what the merged CAFs contain, what is missing, and the commands to obtain the rest (SAM from EAF via `env/sam_eaf.sh`; run database separately).
Numbers come from `scripts/exposure_scan.py` (read-only over all listed files; per-file rows in `$SP_DATA/exposure_scan/*.jsonl`).

## 1. What the merged CAFs contain

`recTree` `rec.hdr.*` (identical branch set in both data samples):

| field | beam-on (open) | beam-off |
|---|---|---|
| `rec.hdr.pot` | non-zero on the first event of each file (`first_in_subrun == first_in_file == 1`, exactly one per file); float32 | 0 |
| `TotalPOT` (TH1D, float64) | ≈ file POT (agrees with `rec.hdr.pot` to < 6e-8 relative in all 1,817 files) | 0 |
| `rec.hdr.noffbeambnb` | 0 | **non-zero on the first event of each file** (e.g. 2407 in the first file for a 50-event file): the PTB off-beam BNB gate count of the sub-run (section 0); exactly one non-zero per file in all 1,058 files (see §3). Beam-on analogue: `rec.hdr.nbnbinfo` (non-zero on the first event of each of the 1,817 files) |
| `TotalEvents` | = events in the file (1,817 / 1,817 files) | = events in the file |
| `rec.hdr.triggerinfo.*`, `rec.hdr.bnbinfo.*`, `spillbnbinfo.*` | per-event, mostly default/sentinel values after the CAF filtering (e.g. `passed_trigger = 0`, trigger times set for beam-on only) | sentinel (4294967295) |
| `metadata/metatree` | empty | empty |

Run/sub-run facts that matter:
- **Beam-on (open, runs 18255 and 18259):** 1,817 files, 89,946 events (median 50 events/file), `subrun == 1` for every file, so (run, subrun) is **not** a unique exposure unit; each file carries its own POT. Σ`TotalPOT` over the 1,817 listed files = **4.62125e18 POT** (file POT between 4.8e10 and 3.7e15). Run 18255: 1,329 files; run 18259: 488 files.
- **Beam-off (InTime-Run1):** 1,058 files, 49,970 events, **156 different runs spanning 18250 – 18592**, `subrun == 1`.
- **Run overlap beam-on vs beam-off is essentially nil:** the beam-off subset has **zero files in run 18255** (73 % of the beam-on files) and only 4 files / 200 events in run 18259. A run-by-run matched normalisation is therefore not possible with this beam-off subset.

## 2. What is missing (must come from outside the CAFs)

| needed | why | status |
|---|---|---|
| **beam-on trigger / spill (gate) count** for exactly the beam-on files (or runs) used | the standard beam-off scaling is (number of beam-on triggers) / (number of off-beam gates) | **in the CAF as `rec.hdr.nbnbinfo`** (Σ 960,047 over the 1,817 files; section 0); which counter pair is approved is the one open question |
| beam-off gate count for exactly the files used | denominator of the scaling | `Σ rec.hdr.noffbeambnb` = 2,542,847; **meaning established from source (section 0): PTB off-beam BNB gates of the sub-run, before filtering** |
| **livetime / run list quality** | runs 18255/18259 vs 18250–18592 may have different conditions (CRT/trigger/light-yield, DAQ configuration) | run database |
| fraction of the beam-on stream that is in the open sample | the open data is a subset (1,817 of 1,820 reco1 files; runs 18255/18259 only); POT of the *whole* run vs of the listed files | SAM |
| whether `TotalPOT` of a *filtered* file equals the POT of the raw events it came from | per-file POT is only meaningful if no file was split/merged | SAM + Haiwang |
| trigger-type / hardware prescale differences between the beam-on (`bnblight`) and off-beam (`offbeamlight`) streams | the scale factor must be for matched streams | run DB / DAQ |

So: **trigger count, livetime/run-database, spill count and SAM metadata are all needed; none can be derived from the merged CAFs alone.** The combination of non-overlapping runs and stream differences also means the beam-off sample can describe the *shape* of the cosmic background but its absolute scale needs a documented procedure agreed with the collaboration. Do not approximate it.

## 3. Result of the full scan (all listed files)

- **Beam-off:** Σ`rec.hdr.noffbeambnb` = **2,542,847** over 1,058 files; **exactly one non-zero entry in every file** (on the first event) → it is a per-file counter, mean ~2,400 gates per 50-event file. What it counts (off-beam gates in the raw file before the light-filter?) must be confirmed.
- **Beam-on:** Σ`TotalPOT` = **4.62125e18** over 1,817 files, one non-zero `rec.hdr.pot` per file; `noffbeambnb` = 0 everywhere.
- Both `tables/pot/beam_off_summary.json` and `tables/pot/beam_on_open_summary.json` record these numbers.

## 4. Commands (SAM part runs from EAF with `env/sam_eaf.sh`; the run database / DAQ logbook is a separate matter)

> **Update 2026-11-06:** the `samweb` commands below do not need a gpVM; run them from EAF through `env/sam_eaf.sh <subcommand>` (`EAF_QUICKSTART.md` §10). The trigger/gate counts and livetime still come from the run database, which is not SAM.

The reco1 and CAF SAM definitions are in `fg1/README.md` and `opendata-fixeddev/DATASET.md`. From EAF (`env/sam_eaf.sh <subcommand>`, `EAF_QUICKSTART.md` §10) or any machine with SBND software:

```bash
# on EAF use env/sam_eaf.sh instead of `samweb`; elsewhere set up your usual SBND environment (anything that provides samweb)
export SAM_EXPERIMENT=sbnd

# --- the four datasets (names exactly as in Haiwang's READMEs) -------------------------------------------------
BEAMOFF_CAF=data_SBND2026A_gen2_InTime-Run1_v10_14_02_02_flatcaf_sbnd
BEAMON_CAF=data_SBND2026A_SBND2026A_gen2_run1_BNBLight_Data_FixedDev_Respin_v10_14_02_04_flatcaf_sbnd
BEAMON_RECO1=data_MCP2025C_Fall25-Run1_BNB_FixedDev_bnblight_v10_14_02_reco1_sbnd

# 1) summary (files, events, size) of each definition
for d in $BEAMOFF_CAF $BEAMON_CAF $BEAMON_RECO1; do echo "== $d"; samweb count-definition-files $d; samweb list-definition-files --summary $d; done

# 2) run list of the beam-on open data and of the beam-off sample
samweb list-files --summary "defname: $BEAMON_CAF"
samweb list-files "defname: $BEAMON_CAF" --fileinfo | awk '{print $1}' > beamon_caf_files.txt     # then per-file metadata below
samweb get-metadata $(head -1 beamon_caf_files.txt) --json | python -m json.tool | head -60       # look for run, event_count, POT/gate/livetime keys

# 3) per-run event counts and any exposure keys (fill in the key names found in step 2)
samweb list-files "defname: $BEAMOFF_CAF" --fileinfo | wc -l
samweb list-definition-files $BEAMON_CAF | xargs -n50 samweb get-metadata --json > beamon_caf_meta.json
samweb list-definition-files $BEAMOFF_CAF | xargs -n50 samweb get-metadata --json > beamoff_caf_meta.json
```

Then, from the same machine (or the SBND run database / DAQ logbook (ask the data-quality group which tool is authoritative)), obtain **for runs 18255, 18259 (beam-on) and for the beam-off runs listed in `$SP_DATA/exposure_scan/beam_off.jsonl`**:

1. number of BNB beam-on triggers (gates) and number of off-beam BNB triggers (EXT gates) per run;
2. run livetime / good-run flags and DAQ configuration (`opsFullTriggerMenuP3_ExtraMTCA5-5-00002` appears in the beam-on CAF metadata);
3. the total POT of the runs vs the 4.62125e18 POT carried by the listed beam-on files (completeness of the open sample).

Report these back and only then define the scale factor (and write down its source in `configs/`). Until then data/MC plots show shapes only.
