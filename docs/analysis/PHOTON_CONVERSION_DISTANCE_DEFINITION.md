# True photon conversion distance: source audit and definition

Date: 2026-11-10. Branch `analysis/ncdelta-differential-efficiency-20261110`. Sample: official Gen2 `EX_ncdeltarad` flatCAFs (13,773 denominator events; 12,427 in the provisional TPC box).
Code: `src/sbnd_single_photon/differential.py` (`photon_truth_variables`, `classify_photon_end`, `conv_distance`); extraction `scripts/differential_truth_scan.py`.
Raw checks: `tables/differential_efficiency/conversion_definition_checks.json`, `tables/differential_efficiency/summary.json` (key `conversion`).

**Verdict: a true conversion distance CAN be defined robustly for the signal photon, and it is defined here from truth only. It is never derived from the reconstructed shower.**
The reconstructed shower-to-vertex distance (`shw_sp_shw_vtx_dis`) is kept as a separate reco diagnostic (see `DIFFERENTIAL_SIGNAL_EFFICIENCY.md` section 6).

## 1. What the flatCAF provides (source audit)

Per-primary information in `rec.mc.nu.prim.*` (type `caf::SRTrueParticle`; checked against `sbnanaobj/StandardRecord/SRTrueParticle.h` in the SBND cvmfs installation, v09_16_04, and the process enum `SREnums.h`):

| field | meaning (from the header comments) | used |
|---|---|---|
| `pdg`, `genE` | PDG code; total energy at generation [GeV] | yes (identify the primary photon, KE) |
| `genp.{x,y,z}` | momentum at the generation point [GeV/c] | yes (photon direction) |
| `start.{x,y,z}` | first point of the trajectory **in the active TPC volume** [cm] | yes (check only) |
| `end.{x,y,z}` | end position in the active TPC volume [cm] | **yes: the conversion point** |
| `end_process` | Geant4 process that ended the particle (`caf::g4_process_`) | **yes: kG4conv = 36, kG4phot = 37, kG4compt = 51, kG4photonNuclear = 47, kG4Transportation = 60** |
| `length` | trajectory length in the active volume the particle first enters [cm] | yes (consistency check) |
| `contained`, `cont_tpc` | contained in a single active volume / single TPC | yes (`contained == 0`: the track does not end inside the active volume) |

**Limitation (important).** `rec.mc.nu.prim` holds only the Geant4 **primaries** (the GENIE hand-off particles). Geant4 secondaries (the e+/e- of the conversion, Compton electrons) are **not stored** in the flatCAF (`daughters` carries IDs of secondaries that are not in `prim`).
So the e+/e- daughters themselves cannot be inspected; the conversion point is read from where the **photon's own trajectory ends**.

## 2. Adopted definition

* **Parent photon.** Among the primaries of the signal neutrino (the neutrino chosen by the signal master), the primary with `pdg == 22` of maximum energy. Check: its energy equals the energy of the Delta-radiative photon of the GENIE record in all 12,427 TPC-box events (maximum difference 0.0 MeV in float32; the signal master's stored photon energy agrees to about 1e-5 MeV for all 13,773 events). In the TPC box the signal neutrino has exactly **one** primary photon above 20 MeV in all 12,427 events (additional primary photons are low-energy nuclear de-excitation lines).
* **Conversion point.** `prim.end` of that photon, valid when `end_process == kG4conv` **and** `contained == 1` (the track ends inside the active volume).
* **Distance.** `d_conversion_3D = | prim.end - true neutrino vertex |` [cm] (the photon starts at the vertex: `prim.start == vertex` exactly in all 12,427 TPC-box events). Components `d_end_{x,y,z}` = end - start are stored.
* **Geometry check.** For converted photons `length` equals the 3D displacement to float precision (99 % quantile of the difference: 2.6e-5 cm) and the displacement direction equals the `genp` direction (median angle 2.5e-5 degrees, 90 % quantile 2e-4 degrees): the photon travels a straight line to its end point, as expected for a neutral particle.
* **Event classes** (`photon_end_class`; every event in exactly one):

| class | definition | TPC box (N = 12,427) |
|---|---|---|
| `conv` | end process kG4conv, `contained == 1`: **true conversion distance defined** | 11,512 (92.6 %) |
| `other_interaction` | `contained == 1` and the end process is not conv (phot or photonNuclear): no pair conversion, no conversion distance. (All TPC-box end processes: conv 12,179, phot 179, photonNuclear 69; 695 of these 12,427 are uncontained, i.e. 667 conv + 28 others, leaving 220 contained non-conv) | 220 (1.8 %) |
| `left_volume` | `contained == 0`: the photon track does not end inside the active volume (it leaves it, or the conversion happened outside it). Includes 667 events whose end process is conv but outside the active volume | 695 (5.6 %) |
| `no_photon` | no primary photon | 0 |

Distribution of the defined distance (11,512 events): quantiles 10 / 25 / 50 / 75 / 90 % = 2.0 / 5.6 / 13.6 / 27.3 / 44.9 cm.

## 3. Alternatives that were considered and compared

| alternative | result | decision |
|---|---|---|
| A (adopted) end of the primary photon track, kG4conv and contained | n = 11,665 over all 13,773 events (11,512 in the TPC box); median 13.5 cm | adopted: unambiguous physical meaning (the pair-conversion point) |
| B end point of the track for **any** end process, contained | n = 11,889; median 13.7 cm; differs from A only by adding the 224 phot / photonNuclear terminations | rejected as "conversion distance" (a photoelectric or photonuclear end is not a conversion); these events are kept as the `other_interaction` class instead |
| C track length `length` | identical to A (see geometry check) | used only as a check |
| D first interaction point (Compton scatter before the conversion) | **not available**: a Compton-scattered primary photon continues as the same Geant4 track; the scatter point is not stored (secondaries are absent) | impossible; limitation documented |
| E reconstructed shower start | **not used** | never substituted for a truth quantity |

Caveats of definition A:
1. If the photon Compton-scatters before it converts, `end` is the final conversion point, not the first interaction; the number of such events cannot be determined from the CAF.
2. `contained == 0` photons have no defined conversion distance; they are a physical category (photon leaves or converts outside the active volume) and are reported, not dropped (`left_volume`).
3. Outside the TPC box (filter-box events with the vertex outside the active volume) `start`/`end` can be the sentinel -9999 (57 % of such events); every conversion-distance result here is restricted to the TPC-box denominator, where the sentinel never occurs.
4. The distance is the distance from the **neutrino interaction vertex**. The photon originates at the Delta decay inside the nucleus; no Delta-decay displacement is modelled (Geant4 starts the photon at the vertex).

## 4. Where it is used

* Efficiency vs `conv_distance_cm` (events of class `conv` only; the other classes appear as 'no value' rows and in `eff_by_photon_end_class.png`, so the denominator accounting always closes).
* Reco shower-to-vertex vs true conversion distance (matched candidates only), and the vertex-offset-along-the-photon-direction vs true conversion distance check (`DIFFERENTIAL_SIGNAL_EFFICIENCY.md` sections 6 and 13).
