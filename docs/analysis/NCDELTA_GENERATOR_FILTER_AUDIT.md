# NC Delta -> N gamma rare-signal filter audit (official Gen2 `EX_ncdeltarad`)

Status (2026-11-06): source audit **plus direct measurement on the official sample** (SAM metadata and all 15,777 official flatCAFs, read from EAF). Labels: **[source]** (read in the file named), **[measured]** (official flatCAF/SAM), **[doc]** (production tracking document), **[not determined]**.

## 1. Access from EAF (all read-only; nothing installed, conda environment untouched)

* `source /cvmfs/sbnd.opensciencegrid.org/products/sbnd/setup_sbnd.sh; setup sam_web_client; samweb -e sbnd ...` works. In a **clean** shell the `setup` function must come from the Fermilab bootstrap first (`source /cvmfs/fermilab.opensciencegrid.org/products/common/etc/setups.sh`), otherwise `setup: command not found`; `setup_sbnd.sh` prints a harmless "Product 'mrb' has no current chain". `env/sam_eaf.sh` wraps this in an `env -i` subshell. A Kerberos ticket (`kinit abhat@FNAL.GOV`) authenticates; `server-info` reports `Authenticated username: abhat`, samweb v3_6.
* The definitions evaluate: reco1 16,505 files / 14,442 events / 421.9 GB; flatCAF 15,777 files / 13,773 events / 39.9 GB (`list-definition-files --summary`). Definition id (flatCAF) 177787, created 2026-05-26 by `sbndpro`. Nothing was created or modified in SAM.
* **Locations** (`locate-file` / `list-file-locations --dim`): every file has one `enstore:` location under `/pnfs/sbn/data_add/sbn_nd/aurora/mc/v10_14_02_05/prodgenie_corsika_proton_rockbox0p1_sbnd/Gen2_Exclusive_2026/ncdeltarad/...` (note **`/pnfs/sbn/`**, not `/pnfs/sbnd/`). `xrd.to_xrootd_url` maps it cleanly to `root://fndcadoor.fnal.gov//pnfs/fnal.gov/usr/sbn/...`, identical to `samweb get-file-access-url --schema=root` apart from the port. Files are tape-backed (enstore) but all 15,777 were read over XRootD with no staging delay (1,059 s for the whole census with 24 workers, 0 errors).
* Per-file SAM metadata (all 15,777 flatCAF and 16,505 reco1): `sbnd_project.version v10_14_02_05`, `application art sbndcode v10_14_02_05`, `fcl.name` `cafmakerjob_sbnd_sce_systtools_and_fluxwgt_and_g4rw.fcl` (flatCAF) and `standard_reco1_sbnd.fcl` (reco1), `production.name Exclusive`, `production.type aurora`, `sbnd_project.name SBND2026A_gen2_BNBLight`, `content_status good`, created 2026-05-25/26, `mc.pot` on both stages and **`mc.generated_event_count` = 12,500 on every reco1 file**. Lineage: flatCAF → one reco1 parent (all 15,777 matched); the reco1 file declares no parents (the filter/gen stage is not in SAM lineage).

## 2. The filter chain (sources)

* Release: sbndcode **v10_14_02_05**, sbncode **v10_14_02_05** (`/cvmfs/sbnd.opensciencegrid.org/products/sbnd/{sbndcode,sbncode}/v10_14_02_05`).
* **[source]** `sbndcode/fcl/run_sbnd_gen2_rare_signal_filter.fcl` (author T. Wester): "Select events for Gen2 exclusive cross section samples from **single unfiltered input file** (gen, g4, etc.). Save passing events to separate file streams". Seven independent trigger paths (`ccpi0, ncpi0, eta, nuecc, kaon, ccdeltarad, ncdeltarad`), each with its own `RootOutput` stream (`SelectEvents: [<path>]`). **An event can therefore be written to several streams.** The `ncdeltarad` path is `[NCDeltaRadFilter]` (`module_type: "NCDeltaRadiative"`) and writes `output_ncdeltarad.root`.
* **[source]** the module is **not** in sbndcode: `sbncode/source/sbncode/SinglePhotonAnalysis/NCDeltaRadiative_module.cc` (header: generated 2017 by R. Murrells; library `libNCDeltaRadiative_module.so`). `CCDeltaRadiative_module.cc` is a separate module/stream ("requires NCNC == 0 ... checks all four Delta charge states (1114, 2114, 2214, 2224)").
* **[doc]** (`aurora-rare-nuecc-ncdr-production.md`, Aurora training sample): chain = `prodgenie_corsika_proton_rockbox0p1_sbnd` gen + `run_sbnd_gen2_rare_signal_filter.fcl` + rockbox g4 + detsim/reco1/reco2 + `cafmakerjob_sbnd_sce_systtools_and_fluxwgt_and_g4rw.fcl`, sbndcode v10_14_02_05; file names `reco1-detsim-g4-filter-gen-<id>`. **[measured, consistent]** the official SAM metadata carries the same release (v10_14_02_05), the file names are `reco2-reco1-detsim-g4-filter-gen-<id>_ncdeltarad` (filter before g4, as in this chain) and production name `Exclusive`; the exact fcl chain/GENIE tune of the official production is still **[not determined]** (SAM exposes only the reco1 and CAF fcl names).

## 3. Exact algorithm of `NCDeltaRadiative::filter` (read from the source)

Input: `std::vector<simb::MCTruth>` labelled `"generator"` (the GENIE record as written by GENIEGen; one MCTruth per interaction in the event, including rock interactions).

```
for each MCTruth mct (index i):
    if mct.GetNeutrino().CCNC() != 1:  continue                  # keep NC only (simb::kNC == 1)
    collect  exiting_photon_parents = Mother() of every particle with StatusCode()==1 && PdgCode()==22
    (error: if particle.TrackId() != its index -> print ERROR, return false)
    for each such parent s:
        if |Vx(s)|>210 || |Vy(s)|>210 || Vz(s)>510 || Vz(s)<-1:  return false   # hard-coded box, EVENT-LEVEL veto
        if |PDG(s)| == 2114 or 2214:   (Delta0 / Delta+)   -> fill diagnostics tree; return true
        elif PDG(s) == 22:  remember Mother(s)             # "in-nucleus photon" chain
    for each remembered grandparent s:
        if |PDG(s)| == 2114 or 2214:                         -> fill diagnostics tree; return true
fill diagnostics tree (not signal); return false
```

Consequences (all **[source]**):

1. **Process/decay-chain definition on the generator record.** The test is "an exiting (status 1) photon whose mother is a Delta0 or Delta+, directly or via one in-nucleus photon", inside an NC interaction. It is **not** topology-defined: there is no cut on proton/neutron/pion multiplicity, on photon energy, on the GENIE interaction mode or on `resnum`. `mode` and `ccnc` are only written to the diagnostics tree.
2. **Neutral and charged Delta.** Delta0 (2114) and Delta+ (2214) both pass. Delta- (1114) and Delta++ (2224) are not tested in the NC module. Charged-current radiative Delta is the separate `ccdeltarad` stream, not part of `EX_ncdeltarad`.
3. **Geometry is in the filter.** The photon's *mother* vertex must lie in `|x|<=210, |y|<=210, -1<=z<=510` cm (the code comment says "hardcode, TPC filter"). This is the rockbox/TPC-with-10-cm-padding box, **not** an analysis fiducial volume. A photon-parent outside the box makes the whole event fail immediately (`return false`), irrespective of other neutrinos later in the record.
4. **Event-level pass.** The filter passes an event if any one neutrino of the event qualifies. Events can contain more than one neutrino (rock/dirt); **the signal neutrino inside a stored event is not tagged by the filter output** (only the diagnostics tree `NCDeltaRadiativeFilter`, written to `hists_filter.root`, records `nu_pdg, ccnc, mode, is_nc_delta_radiative, parent_status_code, parent_pdg` per tested event, and not for the early-`return false` branches).
5. **Before/after FSI.** The filter reads the GENIE record before Geant4 and detector simulation; the photon must be status 1 (stable at generator output), i.e. an exiting photon. **[measured]** On the official sample the Delta decays *before* FSI: in all 13,773 events the decay nucleon is still `status 14` (hadron in nucleus) when it is produced, and only the nucleon is then propagated by GENIE FSI (see §5).
6. **Weights.** The module is an `EDFilter`; it does not touch any weight. A filter-passing event is an *unweighted* member of the unfiltered generated sample.
7. **Radiative branching ratio: forced or natural?** **[not determined]** with certainty. What was inspected: the generator configuration `sbn_genie_BNB_base` (`sbncode/fcl/genie_beam_settings.fcl`): `EventGeneratorList: "Default"`, `FiducialCut: "none"`, `POTPerSpill: 5e12`, tune left to the `GENIE_XSEC_TUNE` environment variable (**not in the fcl**); rockbox overrides in `sbndcode/fcl/genie_sbnd.fcl` (`sbnd_genie_simple_rockbox`: `FiducialCut: "rockbox:(-210,-210,-10)(210,210,510),0,500,0.00425,1.3"`); `prodgenie_corsika_proton_rockbox0p1_sbnd.fcl` only changes `dirtfilter.EnergyDeposit` to 0.1 MeV. **Nothing in these fcl forces the Delta radiative decay.** A forced/enhanced branching would have to be inside GENIE's own configuration, which this audit cannot see. Consistency check (order of magnitude only, Aurora numbers from [doc], CV from this repo): the Aurora training sample has 26,745 events / 5.487e21 POT = 4.9e-18 events/POT; the CV has 6.9e-14 generated events/POT (Σ`TotalGenEvents` 1,887,100 over 2.7194e19 POT), so the pass fraction is ~7e-5 per generated event. That is the size expected of a rare *natural* radiative decay (O(10^-3) branching times the NC-resonant-Delta fraction in the box), not of a forced one (which would give a fraction closer to the NC-Delta fraction itself, ~1e-2). This supports "natural, unweighted" but does not prove it.
8. **A trap, not used here:** `sbncode/fcl/prodgenie_nu_singleinteraction_tpc_NCDeltaRadiative_filtered_sbnd.fcl` (older single-interaction config) overrides `EventGeneratorList: "NCRES"` and contains the comment "THIS DOES NOT WORK, CHECK!". It is a different workflow from the Gen2 rare-signal filter; the Gen2 chain above does not include it. If the official sample were made with it, the rate and the dirt content would differ; confirm the production fcl with the producers.

## 4. Generated-event and POT accounting [measured]

| quantity | value | comment |
|---|---|---|
| reco1 units | 16,505 | each with `mc.generated_event_count` = **12,500** (constant) and its own `mc.pot` |
| Σ generated events (reco1) | 206,312,500 | |
| Σ `mc.pot` (reco1) | 2.96970e21 | 1.4394e13 POT per generated event; the BNB CV has 1.4411e13 (2.71940e19 / 1,887,100), so the SAM numbers are mutually consistent |
| surviving events (reco1) | 14,442 | pass fraction **7.0001e-5** per generated event (as inferred in §3.7) |
| zero-survivor units | 6,923 of 16,505 **do have a reco1 file** (0 events) and 6,626 of 15,777 **have a flatCAF** with `TotalEvents = 0` and a non-zero `TotalPOT` | zero-survivor generation units are **not** missing from the dataset |
| flatCAF units | 15,777 | Σ`TotalPOT` = **2.83853e21** = Σ SAM `mc.pot` (equal file by file, 15,777/15,777); events 13,773 (= SAM and = `TotalEvents`, file by file); generated events behind them (from the reco1 parents) 197,212,500 |
| reco1 units **without a flatCAF child** | **728** (297 with 0 events, 431 with 669 events) | 1.3117e20 POT, 9.1e6 generated events: 4.4 % of POT and 4.6 % of the surviving events are not in the flatCAF dataset |
| CAF `TotalGenEvents` | **125 in every one of the 15,777 files**; Σ = 1,972,125 | **100 times smaller** than the 12,500 generated events per unit that SAM records, and constant: it is **not** the generated-event count of the filtered unit. **Do not use Σ`TotalGenEvents` of these files as a denominator or in a POT/gen-events ratio.** (Interpretation, not determined: it looks like one 125-event generation job of the 100 merged into a unit.) |
| `rec.hdr.pot` | non-zero in 9,233 of 13,773 events | not one-per-file here; not usable for exposure. Use `TotalPOT` (= SAM `mc.pot`). |

Answers to the denominator questions:

* **Does the complete flatCAF dataset alone reconstruct the total signal denominator and POT?** For the units it contains, **yes**, provided one uses `TotalPOT` (it is carried by the zero-event files too) and the number of stored events, **not** `TotalGenEvents`. The generated-event count (12,500 per unit) is only in SAM (reco1 `mc.generated_event_count`), not in the flatCAF. And the flatCAF set is **not complete relative to reco1**: 728 reco1 units have no flatCAF (669 surviving events, 4.6 %).
* **Consistency of the incomplete part:** the pass fraction of the flatCAF units, 13,773 / 197,212,500 = 6.984e-5, agrees with the all-reco1 value 7.000e-5 within the Poisson error (0.85 %), and 59 % of the unmatched reco1 files have events vs 58 % overall: the 728 look like random unit losses, not a content-dependent selection. That supports defining numerator **and** denominator over the same set of units (those with a flatCAF), but it is an inference; whether the 728 are failed or still-pending flatCAF jobs is a production question (kept in the questions list).
* **Are filter-stage files required?** Not for the numbers above, because SAM's reco1 metadata carries the pre-filter generated count and POT per unit. They would only be needed to audit whether any generated unit has no reco1 at all (no SAM record exists for such a unit; the original request size is not visible here).
* **Event identity:** (run, subrun, event) is unique over all 13,773 stored events (0 duplicates), so the Wire-Cell per-event directory collision seen in the Aurora campaign does not arise for this sample as a whole.

## 5. Can the official CAF identify NC Delta -> N gamma?  Yes, with the GENIE record; not from `recTree` alone [measured]

The official flatCAF (like the BNB CV merged CAFs) contains **`GenieEvtRecTree`**: the full GENIE StdHep record of every neutrino (`StdHepPdg/Status/Fm/Lm/Fd/Ld/P4`), linked to `rec.mc.nu` by `rec.mc.nu.genie_evtrec_idx` (verified 1:1: number of record entries = number of `rec.mc.nu` entries in every file, 25,608 neutrinos in total). `truth_signal.genie_record_ancestry` re-applies the filter's own mother test on it. Results over **all 13,773 stored events**:

| check | result |
|---|---|
| NC interaction with a status-1 photon whose mother is Delta0 (2114) or Delta+ (2214) | **13,773 of 13,773** (0 events without it) |
| Delta0 -> n gamma / Delta+ -> p gamma | **7,599 (55.2 %) / 6,174 (44.8 %)**; decay nucleon is a neutron / a proton accordingly (100 % consistent) |
| path | always **direct** (photon's mother is the Delta); none through an in-nucleus photon |
| decay nucleon status at decay | **14 (hadron in nucleus) for all 13,773**: the Delta decays **before** FSI; the nucleon then goes through GENIE FSI, which is why truth protons are not tied to the decay channel |
| GENIE mode | resonant (1) for 100 %; `IntType` = 3 (weak NC) for 100 % |
| **`resnum == 0` (Delta(1232))** | **only 97.66 %**: 322 events (2.3 %) have `resnum` 1-16 other than 0. **`resnum` is not a valid process definition** (as warned), and a proxy requiring `resnum == 0` loses those events |
| >= 1 primary photon / hardest primary photon > 20 MeV | 100 % / 100 % (5/25/50/75/95 % quantiles 134 / 204 / 272 / 359 / 528 MeV; identical to the record photon energy); 13.3 % of events have a second primary photon |
| neutrino flavour of the signal interaction | nu_mu 13,516, anti-nu_mu 165, nu_e 91, anti-nu_e 1 |
| vertex in the filter box / in the provisional active-TPC box | **100 % / 90.2 %** (12,427 events): 9.8 % of the generated signal lies in the padding between the TPC and the filter box |
| events with more than one neutrino | 8,356 (60.7 %); the other 11,835 neutrinos are 72 % CC, 28 % NC; only 8.8 % lie in the active-TPC box; **6 events contain a second NC Delta-radiative neutrino** |
| uniquely identified signal neutrino | 13,767 events (99.96 %) have exactly one record-qualifying neutrino; the 6 others have two (both genuine) |
| surprises | none: no event lacks the Delta ancestry, none is non-resonant, none lacks a photon, none has the signal vertex outside the filter box |

What this establishes, and what it does not: **process membership is certified by provenance / filter membership** (the stored events are the output of the `ncdeltarad` stream). The GENIE record then **independently verifies** the Delta ancestry of every stored event (100 %), identifies the signal neutrino uniquely in 99.96 % of events, and gives the Delta charge and decay nucleon. It does **not** verify the filter's hard-coded geometry veto on the mother vertex (the neutrino vertex is in the box for 100 %, which is consistent but not the same test), nor the production chain or GENIE tune. The CAF-only proxy (NC, resonant, `resnum == 0`, photon > 20 MeV) recovers 13,451 of 13,773 events (97.66 %); with the record it is not needed, and it must not be promoted to the definition.

Field behaviour, identical to the BNB CV [measured, 25,608 neutrinos / 139,376 primaries]: `prim.gstatus` = -1 for all; `genweight` = 0 for all; `nproton` = 0 for all; `npizero` > 0 for only 11 of 25,608 neutrinos (so "almost always 0" holds here too); `prim.startE` is the -9999 sentinel for 41.5 % of primaries.

## 6. Open points that remain (not answerable from SAM/CAF/source)

1. Why 728 reco1 units have no flatCAF child (failed or pending CAF jobs), and whether more units failed earlier (no SAM record would exist).
2. What CAF `TotalGenEvents` = 125 counts (SAM says 12,500 generated per unit).
3. The GENIE tune and branching configuration itself: the dedicated sample's absolute rate, Δ⁰/Δ⁺ split and shapes agree with the natural CV population (§7), so no enhancement above roughly 20 % is present, but agreement does not identify the configuration; `genweight` is unfilled.
4. The Wire-Cell merged-CAF production of this existing sample (the highest-value request).

## 7. Natural population in the BNB CV [measured]

The CV merged CAFs also carry `GenieEvtRecTree`, so the same ancestry test identifies natural NC Δ → Nγ there: **416 events** in the 500,000 stored CV events (242 Δ⁰ → nγ, 174 Δ⁺ → pγ), of which 117 have the vertex in the provisional TPC box. The like-for-like (TPC-box) rate is 430 ± 40 per 1e20 POT against 437.8 for the dedicated sample (ratio 0.98, 95 % CI 0.81–1.18, p = 0.89); shapes and fractions agree. See `NATURAL_NCDELTA_CV_CROSSCHECK.md`. This supports, but does not prove, that the dedicated sample is an unweighted filtered subset of the natural generation.

## 8. Reproducing the numbers


```bash
env/sam_eaf.sh list-definition-files <definition> --summary
env/sam_eaf.sh list-file-locations --dim "defname: <flatcaf definition>"      # dir, file, size per file
env/sam_eaf.sh get-metadata --json <file> [<file> ...]                          # mc.pot, mc.generated_event_count, parents, fcl, version
env/sam_eaf.sh file-lineage parents <file>
python scripts/official_ncdelta_truth_scan.py scan --workers 24 && python scripts/official_ncdelta_truth_scan.py merge
python scripts/official_ncdelta_census_report.py                                 # tables/official_ncdelta, plots/official_ncdelta
python scripts/inspect_official_ncdelta_caf.py <root-url>                        # single-file inspection
```
