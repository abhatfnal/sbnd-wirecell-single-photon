# NC Delta -> N gamma rare-signal filter audit (official Gen2 `EX_ncdeltarad`)

Status: **source-level audit; the official flatCAFs were NOT accessible from EAF** (§1), so nothing below was verified on the official sample itself. Statements are labelled **[source]** (read in the file named), **[CV data]** (measured on the BNB CV recTree, same CAFMaker code line), **[doc]** (a production tracking document) or **[not determined]**. Nothing is inferred beyond that.

## 1. Can the official flatCAF be located from EAF?  No.

| attempt | result |
|---|---|
| `samweb` / `ifdh` on EAF | not installed (not installed on purpose) |
| `/pnfs` | not mounted on EAF |
| published file lists / metadata for `aurora_SBND2026A_gen2_BNBLight_prodgenie_corsika_proton_rockbox0p1_sbnd_EX_ncdeltarad_v10_14_02_05_flat_caf_sbnd` | none found in the accessible repos/docs (searched `/exp/sbnd/app/users/yuhw/sbnd-wirecell-production/aurora/docs`; a recursive grep of the wider area timed out and was not repeated) |
| dCache namespaces | no path is known without guessing; no crawl was done |

The one hit for "ncdeltarad" in Haiwang's tree, `aurora/docs/aurora-rare-nuecc-ncdr-production.md`, is the **Aurora** NC-delta-radiative *training* sample (Flare path, 26,745 validated events, 5.487e21 POT, Wire-Cell merged CAFs already produced there). That is the `aurora_ncdelta_training` sample (`may_train: true`), **not** the official SAM definition, and it lives on Flare, not on EAF. It was not touched. The gpVM commands to obtain the official file list are in §9.

## 2. The filter chain (sources)

* Release: sbndcode **v10_14_02_05**, sbncode **v10_14_02_05** (`/cvmfs/sbnd.opensciencegrid.org/products/sbnd/{sbndcode,sbncode}/v10_14_02_05`).
* **[source]** `sbndcode/fcl/run_sbnd_gen2_rare_signal_filter.fcl` (author T. Wester): "Select events for Gen2 exclusive cross section samples from **single unfiltered input file** (gen, g4, etc.). Save passing events to separate file streams". Seven independent trigger paths (`ccpi0, ncpi0, eta, nuecc, kaon, ccdeltarad, ncdeltarad`), each with its own `RootOutput` stream (`SelectEvents: [<path>]`). **An event can therefore be written to several streams.** The `ncdeltarad` path is `[NCDeltaRadFilter]` (`module_type: "NCDeltaRadiative"`) and writes `output_ncdeltarad.root`.
* **[source]** the module is **not** in sbndcode: `sbncode/source/sbncode/SinglePhotonAnalysis/NCDeltaRadiative_module.cc` (header: generated 2017 by R. Murrells; library `libNCDeltaRadiative_module.so`). `CCDeltaRadiative_module.cc` is a separate module/stream ("requires NCNC == 0 ... checks all four Delta charge states (1114, 2114, 2214, 2224)").
* **[doc]** (`aurora-rare-nuecc-ncdr-production.md`, Aurora training sample): chain = `prodgenie_corsika_proton_rockbox0p1_sbnd` gen + `run_sbnd_gen2_rare_signal_filter.fcl` + rockbox g4 + detsim/reco1/reco2 + `cafmakerjob_sbnd_sce_systtools_and_fluxwgt_and_g4rw.fcl`, sbndcode v10_14_02_05; file names `reco1-detsim-g4-filter-gen-<id>`. **[not determined]** whether the *official* Gen2 production used exactly this chain; the SAM definition name carries the same release (v10_14_02_05) and the `EX_ncdeltarad` tag only.

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
5. **Before/after FSI.** The filter reads the GENIE record before Geant4 and detector simulation. The record carries intermediate and final-state particles; the photon must be status 1 (stable at generator output), i.e. it is a post-intranuclear-cascade exiting photon. Whether GENIE performs the Delta decay before or after its own FSI step is a property of GENIE, **[not determined]** from this source.
6. **Weights.** The module is an `EDFilter`; it does not touch any weight. A filter-passing event is an *unweighted* member of the unfiltered generated sample.
7. **Radiative branching ratio: forced or natural?** **[not determined]** with certainty. What was inspected: the generator configuration `sbn_genie_BNB_base` (`sbncode/fcl/genie_beam_settings.fcl`): `EventGeneratorList: "Default"`, `FiducialCut: "none"`, `POTPerSpill: 5e12`, tune left to the `GENIE_XSEC_TUNE` environment variable (**not in the fcl**); rockbox overrides in `sbndcode/fcl/genie_sbnd.fcl` (`sbnd_genie_simple_rockbox`: `FiducialCut: "rockbox:(-210,-210,-10)(210,210,510),0,500,0.00425,1.3"`); `prodgenie_corsika_proton_rockbox0p1_sbnd.fcl` only changes `dirtfilter.EnergyDeposit` to 0.1 MeV. **Nothing in these fcl forces the Delta radiative decay.** A forced/enhanced branching would have to be inside GENIE's own configuration, which this audit cannot see. Consistency check (order of magnitude only, Aurora numbers from [doc], CV from this repo): the Aurora training sample has 26,745 events / 5.487e21 POT = 4.9e-18 events/POT; the CV has 6.9e-14 generated events/POT (Σ`TotalGenEvents` 1,887,100 over 2.7194e19 POT), so the pass fraction is ~7e-5 per generated event. That is the size expected of a rare *natural* radiative decay (O(10^-3) branching times the NC-resonant-Delta fraction in the box), not of a forced one (which would give a fraction closer to the NC-Delta fraction itself, ~1e-2). This supports "natural, unweighted" but does not prove it.
8. **A trap, not used here:** `sbncode/fcl/prodgenie_nu_singleinteraction_tpc_NCDeltaRadiative_filtered_sbnd.fcl` (older single-interaction config) overrides `EventGeneratorList: "NCRES"` and contains the comment "THIS DOES NOT WORK, CHECK!". It is a different workflow from the Gen2 rare-signal filter; the Gen2 chain above does not include it. If the official sample were made with it, the rate and the dirt content would differ; confirm the production fcl with the producers.

## 4. Generated-event and POT accounting

| quantity | what the source says |
|---|---|
| events in `output_ncdeltarad.root` | exactly the events that returned `true` |
| events tested | the unfiltered input file(s); **not recorded in the filter output** except as rows of the `NCDeltaRadiativeFilter` tree in `hists_filter.root` (missing for the early-return branches) |
| POT | `RootOutput` copies the SubRun-level `sumdata::POTSummary` of the unfiltered input. **[not verified]** for the official files. Hypothesis to confirm on the first file: `TotalPOT` per flatCAF is the unfiltered generator POT of the input file the passing events came from, so that Σ`TotalPOT` is the exposure of the *whole unfiltered generation*, not of the passing events. The Aurora training sample's 26,745 events carry 5.487e21 POT, which is only meaningful under this reading. |
| `TotalGenEvents` | in the BNB CV it is Σ generator `source.maxEvents` (50 per file) **[CV data / earlier audit]**; for a filtered stream it would count generated events of the unfiltered input, if the same bookkeeping is used. **[not verified]** |

Because many unfiltered files contribute no passing event (the Aurora doc: 39 % of NC files hold 0 events), per-file POT must be summed over **all** unfiltered inputs including those that produced empty output; a CAF-only sum over stored files can undercount POT. This is the main open item for the denominator (`SIGNAL_DENOMINATOR` in `TRUTH_PROTON_DEFINITION_AUDIT.md` §6).

## 5. Can the official CAF identify NC Delta -> N gamma by itself?  Not robustly.

Measured on the BNB CV recTree (sbncode CAFMaker; the official Gen2 flatCAF uses the same `cafmakerjob_sbnd_sce_systtools_and_fluxwgt_and_g4rw.fcl` line **[doc]**; **[to verify on the first official file]** with `scripts/inspect_official_ncdelta_caf.py`):

| needed for an exact definition | in the CAF? | evidence |
|---|---|---|
| Delta mother of the photon | **No** | `rec.mc.nu.prim` contains only Geant4 primaries (`start_process == kG4primary`, `FillTrue.cxx` L482). `prim.gstatus` is declared in `SRTrueParticle.h` ("status of the particle as generated by genie") but **never assigned** in `FillTrue.cxx` v10_14_02_05: it is -1 for all 1,548 sampled primaries. `prim.parent` is the Geant4 mother (a sentinel for primaries); there is no `prefsi` branch in `rec.mc.nu`. |
| Delta charge / decay nucleon | **No** | no intermediate-state particles are stored |
| resonance id | partly | `rec.mc.nu.resnum` = `gtruth.fResNum` (GENIE resonance enum; Delta(1232) = 0) and `genie_mode` (RES = 1) exist, but they say *Delta(1232) was excited*, not *it decayed radiatively*: 19 of 23 NC resonant CV neutrinos in a 12-file sample have `resnum == 0`, and NC primary photons also occur in 17 of 33 NC quasi-elastic neutrinos (mode 0) as 0.1-7 MeV nuclear de-excitation lines |
| photon from the Delta | partly | primary photons (pdg 22) are kept with `genE` (total energy at generation, GeV); de-excitation lines are few-MeV, so a hard-photon cut separates them, but a cut is a proxy, not a definition |
| GENIE-level counters | **No** | `rec.mc.nu.npizero/nproton/npiplus/nneutron` are GENIE exclusive-tag counts *before FSI*: `nproton` 0 for all 1,014 sampled neutrinos and always below the primary proton count; `npizero > 0` for only 4 of 1,014 (all four also have a primary pi0, but 136 neutrinos have one, i.e. the field misses 97 %). **Correction to earlier docs:** "always 0" should read "almost always 0 (4/1014)". |
| generator weight | **No** | `rec.mc.nu.genweight` (= `nu.Nu().Weight()`) is 0 for every one of the 1,014 sampled neutrinos (unfilled) and cannot be used |
| true vertex, energies, interaction mode, primaries | **Yes** | `position`, `E`, `genie_mode`, `isnc`, `prim.{pdg,genE,genp}` |

**Conclusion.** The official CAF can *carry* signal events (every event in the `ncdeltarad` stream passed the filter) but it cannot re-derive the process from truth. The signal definition for evaluation is therefore: **"event stored in the official `EX_ncdeltarad` stream"** (process defined by the generator filter of §3), with the signal *neutrino* inside the event located by a documented CAF proxy (NC, GENIE resonant, `resnum == 0`, >=1 primary photon above a configurable energy), whose recovery of the stream is itself a measurable diagnostic (`proxy_recovers_stream`). `truth_signal.py` implements exactly this and returns `delta_pdg`, `delta_charge`, `decay_nucleon_pdg` as unavailable (0), never as guesses.

## 6. Open points to settle with the producers (not guessed here)

1. The production fcl chain of the *official* `EX_ncdeltarad` definition (is it the chain in §2?).
2. Whether the radiative branching ratio is the natural GENIE one, and the GENIE tune/version (`GENIE_XSEC_TUNE`).
3. How `TotalPOT` / `TotalGenEvents` are set in the filtered flatCAF (§4), and the unfiltered-input accounting including empty outputs; ideally the `hists_filter.root` totals.
4. Which neutrino of a multi-neutrino stored event satisfied the filter (diagnostics tree) if the proxy fails.
5. Whether `ccdeltarad` and `ncdeltarad` events can overlap in stored files (separate streams from the same unfiltered input).

## 7. Natural population in the BNB CV (Task 12)

**Skipped by design.** The CAF cannot robustly identify NC Delta -> N gamma (§5). A proxy count in the ordinary BNB CV would be dominated by the proxy's own definition and would not be a signal denominator or a validation of one; the instruction was to skip when the process cannot be identified robustly. The proxy remains available in `truth_signal.py` for use **on the official stream**, where its efficiency against the filter is measurable.

## 8. Reproducing the numbers in §5

The CV statistics come from the recTree of 12 files (264 neutrinos; `scratchpad` exploration) and 40 files (1,014 neutrinos); they are descriptive checks of schema semantics, not physics results. The source citations are line-level in `sbncode/source/sbncode/CAFMaker/FillTrue.cxx` and `.../SinglePhotonAnalysis/NCDeltaRadiative_module.cc` of v10_14_02_05.

## 9. gpVM commands (run on sbndgpvm04, where `samweb` and `/pnfs` exist)

```bash
# 0) environment: your usual SBND setup + a token for samweb/xrootd
D=aurora_SBND2026A_gen2_BNBLight_prodgenie_corsika_proton_rockbox0p1_sbnd_EX_ncdeltarad_v10_14_02_05_flat_caf_sbnd
R=aurora_SBND2026A_gen2_BNBLight_prodgenie_corsika_proton_rockbox0p1_sbnd_EX_ncdeltarad_v10_14_02_05_reco1_sbnd

# 1) sizes
for d in $D $R; do echo "== $d"; samweb count-definition-files $d; samweb list-definition-files --summary $d; done

# 2) the file list (paths -> xrootd URLs), plus per-file metadata (event_count, parents, POT-like keys)
samweb list-definition-files $D > ncdeltarad_flatcaf_names.txt
samweb get-file-access-url --schema=root $(head -1 ncdeltarad_flatcaf_names.txt)          # one example URL
samweb list-files "defname: $D" --fileinfo > ncdeltarad_flatcaf_fileinfo.txt                # name, id, size
head -50 ncdeltarad_flatcaf_names.txt | xargs -n1 samweb get-metadata --json > ncdeltarad_meta_first50.json

# 3) full URL manifest for EAF (a plain text file is enough: one root:// URL per line)
for f in $(cat ncdeltarad_flatcaf_names.txt); do samweb get-file-access-url --schema=root $f | head -1; done > ncdeltarad_flatcaf_urls.txt
wc -l ncdeltarad_flatcaf_urls.txt

# 4) filter accounting: ask the producers for hists_filter.root totals or the filter-job logs of this campaign
#    (events tested vs passed per unfiltered input) and the production fcl/GENIE tune used for this definition.
```

Copy `ncdeltarad_flatcaf_urls.txt` (and the first-50 metadata JSON) to a path readable from EAF. Then, on EAF:

```bash
python scripts/inspect_official_ncdelta_caf.py <first-url> [<second-url> ...]
```
