# Generic BNB Sample Inventory

**Purpose**: Phase F reconnaissance — read-only search for existing BNB neutrino MC before
deciding whether to generate new samples.

**Search date**: 2026-10-04  
**Directories searched**:
- `/lus/eagle/projects/neutrinoGPU/abhat/sbnd/`
- `/lus/eagle/projects/neutrinoGPU/yuhw/` (ALCF username for Yuhang Wang / haiwang)
- `/lus/grand/projects/neutrinoGPU/` (software and inputs only; no artROOT MC)

**Constraint**: Read-only. No files moved, renamed, or modified.

---

## Deliverable answers

**Q1. Does a compatible local BNB sample exist at v10_14_02_04?**  
Yes. `fresh-50evt-integrated-20260909` (50 events, all stages including WireCell) and
`clean-fresh-10evt-integrated-20260910` (10 events, all stages including WireCell) both use
sbndcode v10_14_02_04 with the BNB+CORSIKA production FCL.

**Q2. What is the exact version and FCL?**  
sbndcode v10_14_02_04, GENIE v3_06_02_sbn2.  
Generator FCL: `prodgenie_corsika_proton_nu_spill_tpc_sbnd_av.fcl`  
DetSim FCL: `standard_detsim_sbnd_bothrois_keep_priorSCE.fcl`  
Reco1 FCL: `standard_reco1_sbnd_keep_priorSCE.fcl`

**Q3. Has WireCell already been run?**  
Yes, on both TIER-1 local samples. Output files `reco_wirecell_integration_*.root`, `nugraph.h5`
present. The frozen WCT commit used for those runs must be verified against `251ff143` before
treating that output as baseline-compatible. **Do not assume the WireCell output is from the frozen baseline without SHA verification.**

**Q4. Are the reco1 FCLs compatible with the WireCell input requirements?**  
The local samples use `standard_reco1_sbnd_keep_priorSCE.fcl` (not the plain `standard_reco1_sbnd.fcl`).
This retains an additional SCE product. Standard reco outputs (gaushit, opflashtpc0/1, CRT reco)
should be present. Verify by inspecting the product list in reco1_out.root before assuming
full downstream compatibility.

**Q5. Is there a large-scale FNAL production available?**  
Yes. Two SAM datasets on PNFS:  
- `aurora_SBND2026A_gen2_BNBLight_prodgenie_corsika_proton_rockbox0p1_sbnd_CV_v10_14_02_03_reco1_sbnd` — 749,339 files (v10_14_02_03)  
- `mc_MCP2025C_FallProduction_prodgenie_corsika_proton_rockbox0p1_sbnd_CV_v10_14_02_reco1_sbnd` — 99,978 files (v10_14_02 base)  
These are on FNAL dCache only; not locally cached on ALCF except 1 file from MCP2025C.

**Q6. Is there a version-compatible path from FNAL if local is insufficient?**  
v10_14_02_03 (one patch before target) has a full path list at  
`/lus/eagle/projects/neutrinoGPU/yuhw/sbnd-gen2-data/round2-patrec/mc_paths-v10_14_02_03-full.lst`.
Do not use based on version name alone; inspect product content in a sample file before streaming.

**Q7. Are there any INCOMPATIBLE BNB samples?**  
Yes. Two must not be used:  
- `/lus/eagle/projects/neutrinoGPU/nrowe/spack_test_May3/` — sbndcode v10_04_07 (too old)  
- `/lus/eagle/projects/neutrinoGPU/abhat/sbnd/sample_generation_port/work/smoke_general/` — sbndcode v10_06_03 (too old, 1 event only)

**Q8. Is nue CC expected to be sparsely populated in these samples?**  
Yes. Standard BNB+CORSIKA production (`prodgenie_corsika_proton_nu_spill_tpc_sbnd_av.fcl`) does not
filter by interaction type. At BNB energies the nue CC fraction is ~1% of all neutrino interactions.
The 50-event local sample is statistically insufficient for nue CC studies; even the 749,339-file
FNAL dataset would be needed for statistically meaningful nue CC backgrounds.

**Q9. What is the recommended path for Phase F?**  
Use `fresh-50evt-integrated-20260909` as the immediate test bed — verify product lists and WireCell
SHA, then run the Phase D/E table-building pipeline on it. If the 50 events prove insufficient for
background rate estimates, evaluate streaming from the v10_14_02_03 FNAL dataset.

**Q10. Has Haiwang's area been checked?**  
Yes. The yuhw area (`/lus/eagle/projects/neutrinoGPU/yuhw/`) contains the SAM path lists for the
FNAL datasets but no locally cached artROOT MC of interest beyond the single MCP2025C reference file.
No writes were made to any file in that area.

---

## TIER 1 — COMPATIBLE (v10_14_02_04, local artROOT)

### 1a. fresh-50evt-integrated-20260909 — **50 events, ALL STAGES + WireCell**

| Field | Value |
|-------|-------|
| Path | `/lus/eagle/projects/neutrinoGPU/abhat/sbnd/sample_generation_port/work/haiwang-current/integration-2026-09-08/fresh-50evt-integrated-20260909/run/` |
| sbndcode | v10_14_02_04 |
| GENIE | v3_06_02_sbn2 |
| Generator FCL | `prodgenie_corsika_proton_nu_spill_tpc_sbnd_av.fcl` |
| Detector sim FCL | `standard_detsim_sbnd_bothrois_keep_priorSCE.fcl` |
| Reco1 FCL | `standard_reco1_sbnd_keep_priorSCE.fcl` |
| Events | ~50 |
| Stages present | gen, g4, detsim, reco1, WireCell |
| Key files | `gen_out.root` (2.7 MB), `g4_out.root` (3.1 GB), `detsim_out.root` (2.2 GB), `reco1_out.root` (1.4 GB), `reco_wirecell_integration_fresh50evt.root` (1.4 GB), `nugraph.h5` (71 MB), `tf-default.root` (7.2 KB) |
| WCT commit | **UNVERIFIED** — must check against `251ff143` before using WireCell output |
| Nearby docs | `FRESH_50EVENT_END_TO_END_VALIDATION_2026-09-09.md`, `FRESH_50EVENT_PRE_SUBMISSION_AUDIT_2026-09-09.md` |

### 1b. clean-fresh-10evt-integrated-20260910 — **10 events, ALL STAGES + WireCell**

| Field | Value |
|-------|-------|
| Path | `/lus/eagle/projects/neutrinoGPU/abhat/sbnd/sample_generation_port/work/haiwang-current/integration-2026-09-08/clean-fresh-10evt-integrated-20260910/run/` |
| sbndcode | v10_14_02_04 |
| Stages present | gen, g4, detsim, reco1, WireCell |
| Key files | `gen_out.root` (646 KB), `g4_out.root` (663 MB), `detsim_out.root` (441 MB), `reco1_out.root` (273 MB), `reco_wirecell_integration_clean10evt.root` (272 MB), `nugraph.h5` (15 MB) |
| WCT commit | **UNVERIFIED** — must check against `251ff143` before using WireCell output |

### 1c. sim-e2e-20evt-20260914 — **20 events, through reco1**

| Field | Value |
|-------|-------|
| Path | `/lus/eagle/projects/neutrinoGPU/abhat/sbnd/sample_generation_port/work/haiwang-current/integration-2026-09-08/sim-e2e-20evt-20260914/` |
| sbndcode | v10_14_02_04 |
| Generator FCL | `prodgenie_corsika_proton_nu_spill_tpc_sbnd_av_alcf.fcl` |
| Reco1 FCL | `standard_reco1_sbnd_keep_priorSCE.fcl` |
| Stages present | gen, g4, detsim, reco1 (no WireCell) |
| Key files | `gen/gen_out.root` (1.2 MB), `detsim/detsim_out.root` (1.8 GB), `reco1/reco1_out.root` (1.1 GB), `reco1/larcv_mc_*.root` (315 MB, LArCV format) |
| Note | WireCell would need to be run on reco1_out.root using the frozen config |

### 1d. Smaller integration runs (1–5 events)

| Sample | Events | Path (relative to integration-2026-09-08/) | Stages |
|--------|--------|--------------------------------------------|--------|
| sim-e2e-1evt-20260912 | 1 | `sim-e2e-1evt-20260912/reco1/reco1_out.root` (32 MB) | reco1 |
| sim-e2e-5evt-20260914 | ~5 | `sim-e2e-5evt-20260914/reco1/reco1_out.root` (217 MB) | reco1 |
| clean-fresh-5evt-20260910 | ~5 | `clean-fresh-5evt-integrated-20260910/run/reco1_out.root` | reco1 |

Useful for pipeline testing; too few events for statistical use.

---

## TIER 2 — LIKELY_COMPATIBLE (v10_14_02_03, FNAL dCache only)

### 2a. SBND2026A Gen2 Aurora BNBLight — 749,339 reco1 files

| Field | Value |
|-------|-------|
| SAM definition | `aurora_SBND2026A_gen2_BNBLight_prodgenie_corsika_proton_rockbox0p1_sbnd_CV_v10_14_02_03_reco1_sbnd` |
| PNFS template | `/pnfs/sbn/data_add/sbn_nd/aurora/mc/v10_14_02_03/prodgenie_corsika_proton_rockbox0p1_sbnd/Gen2_2026/CV/reco1/XXXXXX/reco1-detsim-g4-gen-Gen2_2026-*.root` |
| Local path list | `/lus/eagle/projects/neutrinoGPU/yuhw/sbnd-gen2-data/round2-patrec/mc_paths-v10_14_02_03-full.lst` (749,339 lines) |
| 100-file subset | `/lus/eagle/projects/neutrinoGPU/yuhw/sbnd-gen2-data/round2-patrec/mc_paths-v10_14_02_03-100files.lst` |
| sbndcode | v10_14_02_03 (one patch before v10_14_02_04) |
| Local copies | None (all FNAL dCache) |
| Status | LIKELY_COMPATIBLE — inspect product list in sample file before streaming |

### 2b. MCP2025C FallProduction — 99,978 reco1 files

| Field | Value |
|-------|-------|
| SAM definition | `mc_MCP2025C_FallProduction_prodgenie_corsika_proton_rockbox0p1_sbnd_CV_v10_14_02_reco1_sbnd` |
| PNFS template | `/pnfs/sbn/data_add/sbn_nd/poms_production/mc/MCP2025C_FallProduction/v10_14_02/prodgenie_corsika_proton_rockbox0p1_sbnd/CV/reco1/XX/gen_g4_detsim_reco1-*.root` |
| Local path list | `/lus/eagle/projects/neutrinoGPU/yuhw/sbnd-gen2-data/round1-qlmatch/mc.lst` (99,978 lines) |
| Local sample | `/lus/eagle/projects/neutrinoGPU/yuhw/sbnd-gen2-data/round1-qlmatch/gen_g4_detsim_reco1-a0e0308f-0212-beba-4625-a3380029b0cb.root` (324 MB, run 228 subrun 1 event 2) |
| sbndcode | v10_14_02 (4 patches before v10_14_02_04) |
| Status | LIKELY_COMPATIBLE — verify product list before use; version gap is larger |

---

## TIER 3 — INCOMPATIBLE (wrong sbndcode version)

| Sample | Path | sbndcode | Reason |
|--------|------|----------|--------|
| nrowe/spack_test_May3 | `/lus/eagle/projects/neutrinoGPU/nrowe/spack_test_May3/` | v10_04_07 | Too old |
| smoke_general | `.../sample_generation_port/work/smoke_general/` | v10_06_03 | Too old, 1 event |

---

## TIER 4 — EXCLUDED (wrong format or not BNB neutrino MC)

- `/lus/eagle/projects/neutrinoGPU/sbnd/mc/larcv/` — LArCV format, not artROOT
- NC Delta signal MC in `signal_mc/ncdelta/` — this is the signal sample
- Real data files in `yuhw/sbnd-gen2-data/` (run 18431 SBND2026A data)
- `/lus/eagle/projects/neutrinoGPU/dnn_roi/training/samples/` — pre-v10, 2024 G4 file
- `/lus/grand/projects/neutrinoGPU/` — software, weights, and simulation inputs only

---

## Verification checklist before using TIER-1 WireCell output

Before running Phase F analysis on `fresh-50evt` or `clean-fresh-10evt` WireCell output:

- [ ] Check WCT commit SHA in run logs: must be `251ff143`
- [ ] Inspect product list: `T_tagger`, `T_kine`, `T_bundle` trees must be present in tracking-pr.root
- [ ] Verify reco1 FCL (`_keep_priorSCE` variant) does not remove standard gaushit/opflash products
- [ ] Confirm cosmic tags (cosmic_filled, cosmic_flag) match behavior expected for CORSIKA-overlay MC

If WCT commit differs from `251ff143`: do NOT use the existing WireCell output; run frozen WireCell on the reco1 artROOT instead.

---

*This inventory covers the state of these directories as of 2026-10-04. Do not modify any file in the inventoried directories.*
