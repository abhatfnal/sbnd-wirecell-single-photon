# NC Δ → Nγ (1γ0p / 1γ1p) baseline analysis: design note

Branch: `analysis/ncdelta-1g0p-1g1p-baseline-20261105` (from `main` @ `615fe56`). Status: framework development; **no physics result is claimed here**.

## 1. Scope and ground rules

- **Process:** exclusive NC Δ → Nγ, split into **1γ0p** and **1γ1p**. (The inclusive single-photon analysis belongs to Nathaniel. Signal definitions are kept separate and must not be merged.)
- **Baseline = the stored production reconstruction, exactly as-is.** All four Fermilab merged-CAF samples carry `Trun.dl_weights = uboone/scn_vtx/t48k-m16-l5-lr5d-res0.5-CP24.pth` (the uboone SCN DL vertexer, verified in the first file of each sample by `tests/test_remote_smoke.py` / the smoke test). This is **not** DV2-MAX (`vertex_method = dv2_split_move`, `dv2max/r7_cloud/bundle.json`, WCT PR #543) and **not** Fix2. DV2-MAX/Fix2 remain later controlled comparisons on identical events.
- **Not done in this stage:** no DV2/Fix2/A5 changes, no BDT retraining, no threshold tuning, no optimisation, no replacement signal MC, and no transfer of the Aurora NC-Δ sample (it is training/development material, see §1b).
- **Input:** merged flat CAF = `recTree` + `recTreeWireCell`, read over XRootD from Fermilab dCache. A usable Wire-Cell reconstruction requires `wc.valid == 1`. For any later efficiency, `wc.valid == 0` signal events stay in the TRUTH denominator and count as failures.
- **The 59-event NC-Δ sample** is a development sample. `selected / 59` is never an efficiency.

## 1a. What can and cannot be established before the signal exists

The official Gen2 NC-Δ radiative sample **exists at reco1 and flatCAF level and has been measured directly** (SAM definitions `…_EX_ncdeltarad_v10_14_02_05_{reco1,flat_caf}_sbnd`: 16,505 / 15,777 files, 14,442 / 13,773 events; all flatCAFs readable from EAF; `NCDELTA_GENERATOR_FILTER_AUDIT.md`). What is **missing is its Wire-Cell processing / `recTreeWireCell` merged-CAF production** (Haiwang). It does **not** block the background framework, and the truth side of the signal (denominator, topology, Δ ancestry) is already established without Wire-Cell.

| can be completed now (official BNB CV, nueCC as control, beam-on/off shapes) | cannot be established until the official Gen2 NC-Δ Wire-Cell merged CAF exists |
|---|---|
| full BNB baseline cut-flow (candidate- and event-level) | NC-Δ signal efficiency |
| reconstruction acceptance (`wc.valid`, candidate present) | truth 0p / 1p signal ↔ reco 0p / 1p migration |
| BDT-evaluable fraction and its causes | physical signal yield |
| reco 0p / 1p / ≥2p categories of the selected background | final signal purity S/(S+B) |
| background truth composition (first-pass taxonomy) | any signal-region optimisation |
| BDT score and control-variable distributions | |
| POT-normalised BNB CV rates | |
| nueCC shape / classifier-response control behaviour (not added to CV) | |
| beam-on and beam-off shapes (not exposure-normalised) | |
| candidate-multiplicity behaviour and candidate-policy study | |

## 1b. Dataset roles and train/evaluation separation

Per Haiwang: official Gen2 samples on Fermilab are for **evaluation**; the isolated Aurora samples are for **training/development**.

| sample family | location | purpose | may train on? | may evaluate on? |
|---|---|---|---|---|
| Aurora isolated MC (incl. ~26.7k NC-Δ merged CAFs, 59-event study) | Aurora (stays there) | training / development / reconstruction studies | YES | NO (never the evaluation denominator) |
| official Gen2 MC (`bnb_cv`, `nuecc`) | Fermilab dCache | physics evaluation (background) | NO | YES |
| official Gen2 NC-Δ radiative MC (`official_gen2_ncdelta`) | official flatCAF available; Wire-Cell merged CAFs pending | physics evaluation (signal) | NO | YES (reco side once its Wire-Cell merged CAFs exist; truth side available now) |
| official / open data (`beam_on_open`, `beam_off`) | Fermilab dCache | validation | NO | YES (shape validation now) |

Nothing is stated here about a future blinding policy beyond what is known. The registry records these roles (`configs/samples.yaml`: `role`, `may_train`, `may_evaluate`); no code path reads the Aurora sample.

## 2. What the repository already contains (inspected before writing code)

| existing item | what it is | decision |
|---|---|---|
| `selection/microboone_single_photon_selection.yaml` | frozen reference thresholds (20 MeV showers, 4 BDT cuts, `n_20br1 == 1`), proton KE 35 MeV, MicroBooNE FV marked "reference only" | **Reused as the source of truth** for `configs/baseline_selection.yaml` (values copied unchanged, sources recorded). MicroBooNE FV deliberately NOT applied. |
| `analysis/microboone_1gamma_v0/score_microboone_bdts.py` | pure-Python TMVA GradBDT scorer, validated 132/132 against ROOT/TMVA (`docs/TMVA_VALIDATION.md`) | **Algorithm reused**, not re-derived. The script itself runs on import, hard-codes Eagle paths and reads per-event `tracking-pr.root`, so it cannot be imported for the merged CAF. `src/sbnd_single_photon/bdt.py` re-implements the *same tree walk* vectorised over numpy and is unit-tested against a scalar copy of that walk (`tests/test_bdt.py`). The original script is untouched. |
| BDT XMLs | not in the repo (by design). Frozen copies recorded in `provenance/microboone_reference_SHA256SUMS.txt` | The four `single_photon_*_bdt_final.xml` at `/exp/uboone/app/users/uboonepro/bbogart/wcp-uboone-bdt/weights/` are **sha256-identical** to the frozen reference bundle (checked), and readable from EAF. They are referenced, not copied. |
| `baseline_v0/tables/microboone_to_sbnd_bdt_input_mapping.csv` | MicroBooNE BDT input → SBND `T_tagger` branch mapping (59-event study) | **Reused conceptually**: input names are the XML names; verified here against the merged-CAF schema: all inputs of all four models exist in MC, beam-off AND the older beam-on schema (`reco_nuvtxY` → `wc.T_kine.kine_nu_y_corr`, `kine_pio_*` → `wc.T_kine`). |
| 0p/Np rule in `baseline_v0/docs/MICROBOONE_TO_SBND_SINGLE_PHOTON_COMPATIBILITY.md` | `kine_particle_type == 2212` and `kine_energy_particle > 35 MeV` | **Reused** in `proton.py`, now audited against the source (`RECO_PROTON_DEFINITION_AUDIT.md`) and made configurable. |
| `baseline_v0/generic_bnb/docs/bnb_truth_categories.md` | a GENIE-log *estimate* for a 50-event sample (no final-state information) | **Not reusable** as a classifier; the new `truth.py` uses the CAF's official `rec.mc.nu.*` instead. |
| `jobs/`, `*.pbs`, `provenance/wct_*`, `reconstruction_studies/fix2_v2/` | Aurora/Sophia PBS jobs and the Fix2-v2 R&D | **Untouched.** Historical results are not rewritten. |
| existing CAF readers / truth helpers | **none** (everything earlier read per-event `tracking-pr.root`) | new `caf.py`, `truth.py` |
| a natural home for production analysis code | none (`analysis/` is the 59-event study) | new top-level `src/sbnd_single_photon/`, `configs/`, `manifests/`, `scripts/`, `tests/`, `env/`, `docs/analysis/`, `tables/smoke|pot`, `plots/smoke`, with no path collisions |

The remote branch `sbnd-singlephoton-dv2-integration-20261102` (DV2 validation, not merged to `main`) was not used and is unaffected.

## 3. Architecture

```
configs/samples.yaml            sample registry (known counts, schema md5, status)
manifests/<sample>.tsv.gz       Haiwang's lists, original order, /pnfs path + XRootD URL
src/sbnd_single_photon/
  xrd.py        /pnfs/sbnd/...  <->  root://fndcadoor.fnal.gov//pnfs/fnal.gov/usr/sbnd/...
  samples.py    registry + manifest readers (signal placeholders carry no paths/counts; see section 7)
  caf.py        MergedCaf: open (local/XRootD), recTree/recTreeWireCell alignment, wc.valid, requested-branch
                reads only, nested [event][candidate][particle] regrouping, explicit MissingBranchError
  bdt.py        offline original-MicroBooNE TMVA scorer (no training)
  baseline.py   reads cut inputs + BDT inputs, attaches derived.single_photon_*_score
  selection.py  configs/baseline_selection.yaml evaluation, cut-flow (raw counts), candidate policy
  proton.py     provisional reco 0p / 1p / >=2p, threshold configurable
  truth.py      first-pass BNB truth categories (background composition only)
  exposure.py   per-file POT / generated-event / run bookkeeping (no weights)
  plots.py      configurable shape-only control plots (configs/control_plots.yaml)
  scanio.py     loads per-file candidate tables; cut chain, candidate policies (first / any / dedup_any), cut-flow
scripts/        make_manifests, exposure_scan, smoke_test (software validation)
                baseline_scan / baseline_report (full-sample candidate tables and cut-flow)
                truth_match_scan / truth_audit_report / truth_taxonomy_audit (MC truth, evaluation only)
                bdt_evaluability_report, vertex_sentinel_report, shape_plots
tests/          63 tests (mocked arrays, synthetic local ROOT, candidate-policy bookkeeping; the tiny remote read is skipped without a valid token)
```

### CAF facts this design relies on (verified on EAF)

- `recTree` and `recTreeWireCell` have equal entry counts and aligned `run/subrun/event`; `wc.valid` is an int per event.
- `T_kine`, `T_tagger`, `T_bundle`, ... are `var[event][candidate]` (one row per neutrino candidate; 0, 1 or 2+ per event). Per-particle `T_kine` columns are stored **flat per event** with `<name>..length` (per candidate) and `<name>..idx`; `MergedCaf.read_nested` regroups them and raises if lengths are inconsistent.
- The 4 single-photon BDT scores are **not stored** in the CAF (no `single_photon_*` branch). They must be computed offline from the XMLs (§2).
- The beam-on open data (2,283 branches) is a strict subset of the MC/beam-off schema (2,401). Data/MC comparisons use `caf.common_branches` only.

## 4. Baseline chain implemented (no tuning)

`wc.valid == 1` → candidate exists → `shw_sp_n_20mev_showers > 0` → `single_photon_numu_score > 0.4` → `single_photon_other_score > 0.2` → `single_photon_ncpi0_score > -0.05` → `single_photon_nue_score > -1.0` → `shw_sp_n_20br1_showers == 1`. A candidate with `shw_sp_filled == 0` or any non-finite BDT input is not BDT-evaluable and fails the BDT cuts. **No fiducial-volume cut.** Exact CAF branch per cut: `configs/baseline_selection.yaml`.

Full-sample result (all four samples scanned): only ~21 % (CV), ~82 % (nueCC), ~17 % (beam-off) and ~20 % (beam-on) of candidates are BDT-evaluable. The cause is almost entirely `shw_sp_filled == 0`, which coincides with "no shower above 20 MeV" (see `BDT_EVALUABILITY_AUDIT.md`); whether that is the old "main-vertex shower inaccessible" mechanism is only partly supported and is NOT assumed. Not something to fix here.

## 5. Unresolved questions (must be settled before freezing)

1. **Which candidate is "the" neutrino candidate when an event carries several.** Audited in `CANDIDATE_POLICY_AUDIT.md`: 0.87 % of CV events have 2 candidates, mostly independent true interactions; no event has two passing candidates; provisional recommendation `any`, always reported with `first`; **not final**. Needs Haiwang/Hanyu.
2. **Fiducial volume:** none authoritative exists in accessible code (19 conflicting definitions, `SBND_FIDUCIAL_VOLUME_AUDIT.md`); SBND FV pending collaboration decision. `truth.ActiveVolume` is a *provisional nominal TPC box* used only to separate "dirt" from "active-volume" neutrinos; it is not an analysis FV.
3. **Proton threshold 35 MeV:** planning value, to be confirmed against current SBND convention; kept configurable. MC-truth validation done (`RECO_PROTON_DEFINITION_AUDIT.md` §5): reco KE behaves like proton KE; rows of type 2212 with KE>35 MeV are 95.7 % true protons.
4. **Which proton rows count:** `kine_energy_included != 1` marks leftover-shower rows that ARE summed into reco E_ν and are 89 % true protons; the inherited rule counts them. Reported as a sensitivity, not tuned.
5. **Truth taxonomy details:** pi0 precedence over flavour (`BNB_TRUTH_CATEGORY_AUDIT.md`); `rec.mc.nu.isvtxcont` is unfilled and `vtx.*` is NaN in these CAFs, so the active-volume test uses `position.*`; `rec.mc.nu.npizero` is almost always 0 (4/1,014 neutrinos), so π⁰ is counted from the primaries.
6. **Exposure:** see `POT_EXPOSURE_AUDIT.md` and `DATA_EXPOSURE_NORMALIZATION.md`.

## 6. Future analysis sequence (after the official Gen2 NC-Δ evaluation sample exists)

```
true NC Δ -> N γ
    |
    +--> truth 0p
    +--> truth 1p
    +--> truth >=2p
              |
   production Wire-Cell baseline (stored SCN vertexer, wc.valid==1)
              |
   baseline 1γ selection (configs/baseline_selection.yaml, no FV until confirmed)
              |
    +--> reco 0p
    +--> reco 1p
    +--> reco >=2p
```

Required outputs, in order:
1. signal cut-flow (denominator = **all generated true NC Δ→Nγ events** passing the agreed truth definition; `wc.valid==0` events stay in it);
2. total signal efficiency, and truth-category (0p / 1p / ≥2p) efficiencies;
3. truth ↔ reco proton migration matrix (3×3 plus an "unselected / invalid" bin); Δ⁰→nγ is not assumed ≡ 0p and Δ⁺→pγ is not assumed ≡ 1p, because of FSI and thresholds;
4. 1γ0p and 1γ1p purities;
5. POT-normalised background rates (BNB CV, nueCC under a defined normalisation) and the beam-off contribution;
6. beam-on vs (MC + beam-off) validation;
7. later: DV2-MAX/Fix2 **O/D comparison** on identical events (separate study).

Explicitly for this baseline: **the stored production SCN vertexer is used; no DV2-MAX; no Fix2 modification; no BDT retraining; no threshold optimisation.**

## 7. Checklist for the official Gen2 NC-Δ sample (`official_gen2_ncdelta`; flatCAF available, Wire-Cell merged CAF pending)

The Aurora sample (`aurora_ncdelta_training`) is never a substitute. Add a merged-CAF path to `configs/samples.yaml` only when the merged files exist and each Wire-Cell item below is verified from the files or the producer.

**Established directly (SAM, source, official flatCAFs; 2026-11-06):**

- [x] official SAM definitions (reco1, flat CAF): 16,505 / 15,777 files, 14,442 / 13,773 events, `v10_14_02_05`, readable over XRootD from EAF;
- [x] official flatCAF availability, locations (`/pnfs/sbn/data_add/...`) and per-file SAM metadata;
- [x] truth trees: `recTree` truth and **`GenieEvtRecTree`** (full GENIE record, linked by `rec.mc.nu.genie_evtrec_idx`);
- [x] generated-event / stored-event / POT accounting: SAM reco1 `mc.generated_event_count` 12,500 per unit, `mc.pot`; CAF `TotalGenEvents` (125 per file) is not the generated count; zero-survivor units exist as files; 728 units without flatCAF (`NCDELTA_GENERATOR_FILTER_AUDIT.md` §4);
- [x] `NCDeltaRadiative` filter definition (sbncode v10_14_02_05 source);
- [x] Δ ancestry and decay representation: Δ⁰ → nγ 7,599, Δ⁺ → pγ 6,174; decay before FSI (nucleon status 14); 13,773 / 13,773 events verified;
- [x] signal truth proton census (35 MeV, provisional): 0p 6,501 / 1p 6,160 / ≥2p 1,112; vertex 100 % in the filter box, 90.2 % in the provisional TPC box;
- [x] `(run, subrun, event)` unique over all stored events.

**Pending, Wire-Cell specific (cannot be known before the merged production exists):**

- [ ] exact merged manifest (and ADLER32 if files are copied anywhere);
- [ ] `recTreeWireCell` schema md5 (`d4396a3490ea…` if produced like fg1) and branch count;
- [ ] WCT / toolkit commit and `Trun.wct_version`;
- [ ] **`Trun.dl_weights`** per file and the stored vertexer (same uboone SCN `.pth` as the other official samples; otherwise flag the reconstruction mismatch before use) and the SCN weights;
- [ ] `wc.valid` accounting and per-file PARTIAL/EMPTY counts (the 6,626 empty flatCAFs need no processing);
- [ ] `T_match` / `T_overlap` / `T_truth_nu/pf/track` / `T_pf` present and filled in the merged production;
- [ ] the merged events keep the unique `(run, subrun, event)` identity.

## Phase 2 status (current facts)

* Official Gen2 NC-Δ generator/filter semantics, SAM access from EAF (`env/sam_eaf.sh`, `EAF_QUICKSTART.md` §10), direct measurements on all 15,777 flatCAFs, accounting: `NCDELTA_GENERATOR_FILTER_AUDIT.md`. `scripts/official_ncdelta_truth_scan.py`, `scripts/official_ncdelta_census_report.py`, `scripts/inspect_official_ncdelta_caf.py`.
* Truth proton categories (post-FSI primaries, KE > 35 MeV provisional): `TRUTH_PROTON_DEFINITION_AUDIT.md`; signal truth object and efficiency denominator: `SIGNAL_TRUTH_AND_DENOMINATOR.md`; code `src/sbnd_single_photon/truth_signal.py` (works on a plain flatCAF, no Wire-Cell tree).
* The flatCAF (and the BNB CV merged CAFs) carry `GenieEvtRecTree`; Δ ancestry is verified for all 13,773 stored events and the signal neutrino is identified through the record. `resnum == 0` holds for only 97.66 % and is not a definition. `rec.mc.nu.npizero` is almost always 0 (11 of 25,608 neutrinos), so π⁰ is counted from the primaries.
* Denominator accounting uses SAM `mc.pot` / `mc.generated_event_count`, not the CAF `TotalGenEvents`; see `SIGNAL_TRUTH_AND_DENOMINATOR.md`.
* Derived BNB analysis table (outside Git) and its exact validation: `ANALYSIS_TABLE_VALIDATION.md`; baseline plots and 1γ0p/1γ1p background characterisation: `BASELINE_1G0P_1G1P_BACKGROUND.md`.

## Signal/background bookkeeping (no double counting)

The inclusive BNB CV contains **naturally generated NC Δ → Nγ events** (identified exactly with the GENIE record; `NATURAL_NCDELTA_CV_CROSSCHECK.md`). When the dedicated official NC-Δ sample is later used to obtain the high-statistics signal efficiency and the expected signal yield, **do not simply add "dedicated NC-Δ signal + full BNB CV"**: that counts the NC-Δ component already present in the CV twice.

The future physical prediction must use a consistent scheme, for example:

* **S** = the dedicated NC-Δ sample normalised to the physical POT (N_signal_truth / POT_dedicated × POT_data, `SIGNAL_TRUTH_AND_DENOMINATOR.md`);
* **B** = the BNB CV **with its true NC Δ → Nγ interactions removed** (event key `(file_index/source_file, run, subrun, evt)`; the natural-signal event list is `tables/natural_ncdelta/natural_signal_events_bnb_cv.csv`), plus beam-off for cosmic-only backgrounds;

or an equivalent, statistically correct scheme. Care is needed with events that contain a natural signal neutrino **and** other interactions (60 % of CV events have several neutrinos): the removal is per signal *interaction*, so a CV event whose selected candidate belongs to a different neutrino still counts as background for that candidate. Candidate-to-neutrino matching (`wc.T_overlap` / `T_match`) will be required to do this properly, and is evaluation-only, never used to choose candidates. **No final weighting is implemented here.** The natural-CV count is also an independent normalisation cross-check of the dedicated sample (rate per POT of signal in the TPC).
