# SPINE / medulla NC-Delta signal definition: source audit

Date: 2026-11-10. Branch `analysis/ncdelta-spine-harmonized-definition-20261110`. Read-only audit of public code; nothing was executed from it (the downloaded sources were only read as text).
Every statement below is labelled **TECHNOTE TEXT** (as given to us in the task description; we have not re-read the technote PDF), **SOURCE IMPLEMENTATION** (read from code), or **OUR REPRODUCTION**.

## 1. Provenance (found)

| item | value |
|---|---|
| repository | `github.com/seokjuchung/medulla` (fork of `github.com/justinjmueller/medulla`, the SBND/ICARUS SPINE analysis layer) |
| branch | `feature/schung_NCDelta` |
| commit audited | `4048f930aa7679cebbcf9f9b11aa33f21f350f05` (2026-06-17, "Enhance NC delta resonance identification by expanding resnum conditions and add higher_resonances.toml configuration file"); branch HEAD at the time of reading; previous: `4fa31b1d1e` (2026-05-26, "Add neutrino2026_veto branch to simulation and signal trees in gORe_main.toml") |
| main selection config | `selection/toml/gORe_main.toml` (others: `gORe_fiducial.toml`, `gORe_template.toml`, `gORe_nocut.toml`, `higher_resonances.toml`) |
| source files | `selection/include/gOre/{core_gOre.h, cuts_gOre.h, event_cuts_gOre.h, vars_gOre.h, utils_gOre.h}`, `selection/include/{cuts.h, particle_cuts.h, particle_variables.h}` |
| SPINE geometry / post-processors | `github.com/DeepLearnPhysics/spine` : `src/spine/geo/config/sbnd/sbnd_v2-6_geometry.yaml`, `src/spine/post/reco/geometry.py` (`ContainmentProcessor`, `FiducialProcessor`) |
| local copies | read in a scratch directory outside the repository (not committed) |

**Caveat that cannot be removed from here:** we do not know which branch commit the technote's numbers were produced with, nor whether the technote text was written before or after `neutrino2026_veto` (2026-05-26) and the Delta-resonance expansion (2026-06-17) were added. The code below is the **source of truth we could read**; where it differs from the technote text we show both and quantify the difference rather than choosing silently. The ROOT/`.toml` that Seokju ran (`output = /exp/sbnd/data/users/sc5303/NCDelta/...`) is on his area and was not visible.

## 2. TECHNOTE TEXT (as given)

FV x, y in [-180, 180] cm and z in [10, 450] cm (true vertex); all final-state particle endpoints contained, minimum 5 cm margin from the active-volume boundary; exactly one true photon with KE > 25 MeV and no true electron / charged pion / muon above 25 MeV; NC, Delta(1232) resonance, GENIE final state after nuclear transport containing "nucleons plus a single photon"; proton threshold 50 MeV; 1gamma0p = no protons above 50 MeV, 1gammaNp = one or more.

## 3. SOURCE IMPLEMENTATION (`gORe_main.toml`, commit 4048f93)

Parameters: `gOre_threshold = muon_threshold = pion_threshold = 25` MeV, `proton_threshold = 50` MeV, `fiducial_{x,y}dist_{pos,neg} = 20` cm, `fiducial_zdist_pos = 50`, `fiducial_zdist_neg = 10` (these override the `GORE_MIN_*` header defaults 50/25/25/25).

**Truth signal trees** (`[[tree]] name = "signal_1g0p"` / `"signal_1gNp"`, `mode = "true"`, `sim_only = true`): a SPINE *true interaction* is a signal if
```
fiducial_cut (true)  &  containment_cut (true)  &  neutrino2026_veto (true)
& single_photon(25)  &  no_electrons(25)  &  no_muons(25)  &  no_charged_pions(25)
& no_protons(50)  [1g0p]   |   nonzeroproton(50)  [1gNp]
& event cut  has_nc_delta_ng_interaction   (decrements_exposure = false)
```
(`signal_1gNp` has the same list with `nonzeroproton` in place of `no_protons`.)

**Event cut** `ecuts::gOre::has_nc_delta_ng_interaction` (event_cuts_gOre.h): loop over `sr.mc.nu`; true if some neutrino has
`isnc && resnum in {0, 6, 7, 9, 12, 13, 14, 15} && mc_topology(interaction.prim).single_photon() && mc_topology(interaction.prim).only_photons_and_nucleons()`.

**Truth category** `vars::gOre::mc_category` (vars_gOre.h; the "NC Delta -> N gamma" class 0 of the MC-truth plots): the same expression, `is_nc_delta_res && single_photon_topology`, with the comment *"The fiducialization is being a pain, so focus on FSI topology and mode/interaction type"* — **no FV and no containment in this category**.

`mc_topology` (core_gOre.h) is built from `obj.prim`, i.e. `caf::SRTrueParticle` primaries — **exactly the collection `rec.mc.nu.prim` of our flatCAF**. Its rules:
* a particle enters the topology only if `is_above_threshold`: neutrinos never; photon `genE > 25 MeV`; electron `genE - m_e > 25`; muon `genE - m_mu > 25`; proton `genE - m_p > 50`; charged pion `genE - m_pi > 25`; **everything else (neutrons, pi0, kaons, nuclear fragments, ...) counts as above threshold**;
* `single_photon()` = exactly one photon in that set; `only_photons_and_nucleons()` = every particle in that set has pdg 22, 2112 or 2212 (so a pi0 at any energy, or any other species, breaks it, while sub-threshold e / mu / pi+- / protons are ignored).

So the **"GENIE final state contains only nucleons and a single photon" of the technote is implemented as a thresholded rule on the post-FSI primaries** (`only_photons_and_nucleons` over above-threshold primaries), **not** as a literal restriction of the GENIE record. The threshold topology (no e/mu/pi+- above 25 MeV) is therefore *implied* by it (and extended to forbid any pi0 and any other species); the two statements in the technote are overlapping consequences of one rule.

**True-interaction cuts** (generic, `cuts.h`, `particle_cuts.h`; SPINE truth interaction = clustered deposits **including secondaries**):
* `single_photon / no_electrons / no_muons / no_charged_pions / no_protons / nonzeroproton` : count SPINE truth particles that are **primary** (SPINE primary classification), of the given SPINE species (photon 0, electron 1, muon 2, pion 3, proton 4) with `KE >= threshold`, `KE = energy_init - mass`. Neutrons are not a SPINE species and are not counted.
* `fiducial_cut` : `obj.is_fiducial && !(vertex_x > 210.215 && ...)` (the second term is inert for SBND); `is_fiducial` is set upstream by SPINE's `FiducialProcessor` (`mode`, margin from detector walls, strict inequalities). The medulla docstring describes the border as 25 cm (x, y), 50 cm downstream, 30 cm upstream, which **conflicts with the technote** (20/20/10/50). The production margins live in the SPINE post-processor configuration, which is not in medulla and was not found. The explicit 20/20/10/50 cm thresholds appear only in `gOre_fiducial_cut` and in the `mc_category`/branch parameters.
* `containment_cut` : `obj.is_contained`, set by SPINE's `ContainmentProcessor`: "all particles and all spacepoints within 5 cm of the detector edges, and no spacepoints reconstructed in a TPC that did not create them" (docstring in `cuts.h`).
* `neutrino2026_veto` (SBND): `fiducialize_cathode` (|vertex x| > 5 cm) **&** `veto_sbnd_highy_highz` (no particle starting or ending in x > 0, y > 100 cm, z > 250 cm) **&** `!cathode_crosser` (no particle with start_x * end_x < 0). This veto is in the **signal trees of `gORe_main.toml` only** (not in `gORe_fiducial.toml` / `gORe_template.toml`) and is **not mentioned in the technote text we were given**.

## 4. Where technote text and source differ

| topic | technote text | source implementation |
|---|---|---|
| Delta identification | Delta(1232) | GENIE `resnum in {0, 6, 7, 9, 12, 13, 14, 15}` (all Delta-type resonances); 171 of our 13,773 events (1.2 %) have a non-Delta `resnum`, 151 have a Delta-type `resnum != 0` |
| GENIE final-state statement | "nucleons plus a single photon" | thresholded `only_photons_and_nucleons` on above-threshold primaries (pi0 of any energy excluded; sub-threshold e/mu/pi+-/p ignored) |
| FV | x,y +-180, z 10-450 | truth tree uses SPINE `is_fiducial` (production margins not found); docstring margins 25/25/30/50 |
| containment | endpoints >= 5 cm from the boundary | SPINE `is_contained` over all particles and spacepoints incl. secondaries, margin configured upstream |
| extra cuts | none listed | `neutrino2026_veto` (cathode +-5 cm, high-y/high-z region, cathode crossers) in the signal trees |
| event vs interaction | one signal per event | event cut loops over all neutrinos; interaction cuts apply per interaction |

## 5. OUR REPRODUCTION (what the flatCAF allows)

| rule | status | implementation (`src/sbnd_single_photon/spine_def.py`) |
|---|---|---|
| NC, Delta-type resnum, one photon > 25 MeV, only photons/nucleons above threshold | **exact** (same collection `rec.mc.nu.prim`, same thresholds and `genE`-based energies) | `above_threshold`, `counts`, masks `spine_resnum_delta`, `spine_one_photon_25`, `spine_genie_final_state`, `spine_no_e_25`, ... |
| proton threshold 50 MeV | exact for the primary-proton definition (`genE - m_p > 50`) | `proton_count` |
| FV (20/20/20/20/50/10 cm from walls +-200, +-200, 0-500) | **exact for the technote values** (strict inequalities); production SPINE margins unverified | `fiducial` |
| containment | **flatCAF-primary approximation**, not SPINE containment: start AND end point of every non-neutrino primary that has visible deposits (the SPINE-particle proxy) at least 5 cm inside the SPINE sbnd_v2-6 detector box; variants: literal all-primaries-incl.-neutrons, GDML box, zero-margin `contained` flag | `containment_margin`, `containment_flag` |
| SPINE particle-level topology cuts (primary SPINE particles with deposit-based `energy_init`) | **not reproducible** (SPINE truth particles are not in the flatCAF); the exact `mc_topology` rule above is used instead | -- |
| `neutrino2026_veto` | **flatCAF-primary approximation** (primaries instead of all SPINE particles) | `neutrino2026_veto` (kept as a separate variant; **not** in the headline mask) |
| GENIE record literal restriction | extra variant (status-1 stable final state = nucleons + neutrino + ONE photon) | `genie_record_strict` |

Naming: the **headline harmonized mask `spine_truth_signal`** equals `spine_technote_strict` = Delta ancestry & SPINE FV & containment (approximation) & exactly one photon > 25 MeV & no e/mu/pi+- > 25 MeV & `only_photons_and_nucleons`. The source-only extras (`resnum` Delta set, `neutrino2026_veto`) and the literal-record variant are separate masks (`spine_source_signal`, `spine_source_signal_veto2026`, `spine_technote_strict_record`) and are quantified in the ladder; they were **not** silently included.

## 6. Which particle collection does "all final-state particle endpoints" use?

SOURCE: containment is SPINE's `is_contained` of the **SPINE truth interaction**: all its particles (including secondaries such as the e+/e- of the photon conversion and Compton electrons) and all spacepoints. The flatCAF has `rec.mc.nu.prim` only (Geant4 hand-off primaries; secondaries are not stored), so **exact SPINE containment cannot be reproduced**. Our choice is a **flatCAF-primary containment approximation**: it uses start/end points of primaries, not of secondaries and not of every spacepoint; contained secondaries of an uncontained photon are therefore not checked, while the photon's own end (conversion point) is. It is labelled that way everywhere and is never called SPINE containment.

## 7. Unresolved after this audit

1. The exact commit/TOML of the technote run and whether it contained `neutrino2026_veto`.
2. The production SPINE `FiducialProcessor` / `ContainmentProcessor` margins and mode (`tpc` / `module` / `detector`, `cathode_margin`) for the SBND production used.
3. Whether the technote's "Delta(1232)" means `resnum == 0` or the Delta-type set of the code.
4. Whether SPINE `energy_init` (generation energy of the SPINE truth particle) equals our `genE` for all primaries.
