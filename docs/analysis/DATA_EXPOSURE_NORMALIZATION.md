# Beam-off / beam-on exposure normalisation audit

**No scale factor is computed or assumed here.** This note records what the merged CAFs contain, what is missing, and the exact gpVM commands to obtain the rest.
Numbers come from `scripts/exposure_scan.py` (read-only over all listed files; per-file rows in `$SP_DATA/exposure_scan/*.jsonl`).

## 1. What the merged CAFs contain

`recTree` `rec.hdr.*` (identical branch set in both data samples):

| field | beam-on (open) | beam-off |
|---|---|---|
| `rec.hdr.pot` | non-zero on the first event of each file (`first_in_subrun == first_in_file == 1`, exactly one per file); float32 | 0 |
| `TotalPOT` (TH1D, float64) | ≈ file POT (agrees with `rec.hdr.pot` to < 6e-8 relative in all 1,817 files) | 0 |
| `rec.hdr.noffbeambnb` | 0 | **non-zero on the first event of each file** (e.g. 2407 in the first file for a 50-event file): the off-beam BNB gate count; exactly one non-zero per file in all 1,058 files (see §3) |
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
| **beam-on trigger / spill (gate) count** for exactly the beam-on files (or runs) used | the standard beam-off scaling is (number of beam-on triggers) / (number of off-beam gates) | **not in the CAF**: the beam-on CAF stores POT but no gate counter (`noffbeambnb = 0`) |
| beam-off gate count for exactly the files used | denominator of the scaling | probably `Σ rec.hdr.noffbeambnb` (see §3); **its meaning (per file? per raw file before filtering?) must be confirmed** |
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

The reco1 and CAF SAM definitions are in `fg1/README.md` and `opendata-fixeddev/DATASET.md`. On a gpVM with SBND software and a token:

```bash
# set up your usual SBND environment on the gpVM (anything that provides samweb); the exact setup line was not verified from EAF
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
