# Truth proton definition audit (provisional; the 35 MeV threshold is NOT frozen or optimised)

Purpose: an analysis-grade truth 0p / 1p / >=2p that corresponds to the reconstructed rule (`kine_particle_type == 2212` and `kine_energy_particle > 35 MeV`, see `RECO_PROTON_DEFINITION_AUDIT.md`). Evidence is from the BNB CV recTree (same CAFMaker truth code as the official Gen2 flatCAF; to be re-checked on the first official file with `scripts/inspect_official_ncdelta_caf.py`). Code: `src/sbnd_single_photon/truth_signal.py`.

## 1. Which collection, and why

| candidate collection | verdict |
|---|---|
| **`rec.mc.nu.prim`** (Geant4 primaries of the interaction, `start_process == kG4primary`, `FillTrue.cxx` L482) | **USED.** These are the GENIE status-1 particles handed to Geant4, i.e. the generator final state **after** GENIE's intranuclear cascade (FSI). |
| `rec.mc.nu.prefsi` | does not exist in these CAFs |
| `prim.gstatus` | never assigned in `FillTrue.cxx` v10_14_02_05 (-1 for all 1,548 sampled primaries): cannot be used to separate pre/post-FSI or intermediate states |
| `rec.mc.nu.{nproton,npiplus,npizero,nneutron}` (GTruth) | pre-FSI exclusive-tag counts, almost always 0 (`nproton` 0 for 1,014/1,014 neutrinos; `npizero` >0 for 4/1,014): **not usable** |
| `wc.T_truth_track` (all Geant4 tracks with charge in blobs) | not used for the category: it includes secondaries (see §3) and is Wire-Cell-dependent (the reader must work on a plain flatCAF) |

## 2. Definition

```
n_true_p(nu, T) = #{ p in rec.mc.nu[nu].prim : p.pdg == 2212  AND  (p.genE - 0.938272 GeV) * 1000 > T }      # strict >, T = 35 MeV default
true_proton_category = 0p if n == 0, 1p if n == 1, >=2p otherwise
```

* **Proton KE** = `genE` (total energy at the generation point, GeV, `SRTrueParticle.h`) minus the proton mass. The mass check holds numerically: sqrt(genE^2 - |genp|^2) has median 0.938272 GeV over all primary protons. `startE` is **not** used: it is the energy at entry into the active volume and is the sentinel -9999 whenever the particle never enters it (70 % of the primaries in the sample).
* **Post-FSI:** yes (see §1).
* **Secondary Geant4 protons: not counted.** The category is a *generator-level* final-state definition (what the neutrino interaction emitted). Secondaries are produced later by hadronic re-interaction in argon and cannot be attributed to the interaction without a detector model. They matter for the *reco-truth migration* and are quantified separately (§3).
* **Containment: not part of the definition.** Whether a proton exits the active volume is a detector effect that belongs in the migration matrix, not in the truth category. The CAF provides `prim.contained` / `prim.cont_tpc` to study it: 96.5 % of primary protons with KE > 35 MeV from active-volume neutrinos (60 files, 408 neutrinos, 430 protons) are contained in one active volume; the definition is insensitive to it at that level, so it is reported as a diagnostic, not applied.
* **Origin from the Delta decay: not used.** The Delta mother and the nucleon it decays to are not stored (`NCDELTA_GENERATOR_FILTER_AUDIT.md` §5). For Delta0 -> n gamma the nucleon is a neutron, so any truth proton comes from the nuclear remnant/FSI; for Delta+ -> p gamma the proton may or may not be the visible proton. Truth 0p/1p/>=2p is **final-state multiplicity**, kept separate from the decay channel (Delta0 -> n gamma vs Delta+ -> p gamma, which the CAF cannot give).
* **Threshold:** a configurable parameter (`proton_ke_mev`, default 35.0), mirroring the reco rule. It is not scanned or tuned; the reco side has the same provisional status.

## 3. Evidence on the BNB CV

* **Primaries vs secondaries among true protons** (300 files of the truth-match scan, beam-neutrino true protons with start_E-based KE > 35 MeV): 2,260 have Geant4 mother 0 (primary), 980 (30 %) have a non-zero mother (secondary). So roughly 3/10 of proton *tracks* above threshold are not generator-level protons; the reco rule can count them. This is the reason truth 0p/1p/>=2p (generator final state) and "what the detector can see" will not agree event by event and why the truth-reco migration matrix is needed, **not** a reason to change the definition.
* **True proton multiplicity of active-volume neutrinos** (primary, KE > 35 MeV; 408 neutrinos; inclusive BNB, **not** signal): 0p 108, 1p 206, >=2p 94. Descriptive only.
* **Reco side:** the reco KE tracks the true proton KE (median reco/true 0.99 for 60-400 MeV, `RECO_PROTON_DEFINITION_AUDIT.md` §5) and above 35 MeV 95.7 % of type-2212 rows are truth protons.

## 4. What remains a decision (not taken here)

1. The threshold value and whether truth and reco share it (kept 35 MeV for both, provisional).
2. Whether to also report a "visible truth" category (primaries + secondaries, containment-aware) as a systematic cross-check next to the generator-level category.
3. Whether neutrons / charged pions (excluded from `n_true_protons`) enter the exclusive topology definition `1 gamma + Np`: counts `n_primary_pi0`, `n_primary_pi_charged`, `n_primary_neutrons`, `n_primary_photons_hard` are stored so the choice can be made later without re-reading CAFs.

## 5. Interface

`truth_signal.signal_truth(...)` returns, per event and for the proxy-selected signal neutrino: `n_true_protons` (KE > threshold), `n_true_protons_all_ke`, `true_proton_category` (0/1/2, -1 = no signal neutrino), `photon_energy_mev`, `n_primary_{photons,pi0,pi_charged,neutrons}`, vertex, `neutrino_energy_gev`, `genie_mode`, `resnum`. `delta_pdg`, `delta_charge`, `decay_nucleon_pdg` are returned as 0 = unavailable. Unit tests: `tests/test_truth_signal.py`.
