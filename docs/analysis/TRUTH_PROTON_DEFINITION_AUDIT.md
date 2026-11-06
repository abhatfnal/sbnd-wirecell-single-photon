# Truth proton definition audit (provisional; the 35 MeV threshold is NOT frozen or optimised)

Purpose: an analysis-grade truth 0p / 1p / >=2p that corresponds to the reconstructed rule (`kine_particle_type == 2212` and `kine_energy_particle > 35 MeV`, see `RECO_PROTON_DEFINITION_AUDIT.md`). Evidence is from the BNB CV recTree and, since 2026-11-06, **directly from the official Gen2 NC-Delta flatCAFs** (all 15,777 files, `NCDELTA_GENERATOR_FILTER_AUDIT.md` §5; the field behaviour is the same in both). Code: `src/sbnd_single_photon/truth_signal.py`.

## 1. Which collection, and why

| candidate collection | verdict |
|---|---|
| **`rec.mc.nu.prim`** (Geant4 primaries of the interaction, `start_process == kG4primary`, `FillTrue.cxx` L482) | **USED.** These are the GENIE status-1 particles handed to Geant4, i.e. the generator final state **after** GENIE's intranuclear cascade (FSI). |
| `rec.mc.nu.prefsi` | does not exist in these CAFs |
| `prim.gstatus` | never assigned in `FillTrue.cxx` v10_14_02_05 (-1 for all 1,548 sampled CV primaries and for all 139,376 primaries of the official sample): cannot be used to separate pre/post-FSI or intermediate states. The pre-FSI information is instead in **`GenieEvtRecTree`** (StdHep status 14 = hadron in nucleus, 1 = final state), which is available in the official flatCAF |
| `rec.mc.nu.{nproton,npiplus,npizero,nneutron}` (GTruth) | pre-FSI exclusive-tag counts, almost always 0 (CV: `nproton` 0 for 1,014/1,014 neutrinos, `npizero` >0 for 4; official sample: `nproton` 0 for 25,608/25,608, `npizero` >0 for 11): **not usable** |
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
* **Origin from the Delta decay: not used for the category, but now measurable.** The official flatCAF carries the GENIE record (`GenieEvtRecTree`), so the Delta, its charge and the decay nucleon are known (`NCDELTA_GENERATOR_FILTER_AUDIT.md` §5): the Delta decays **before** FSI (decay nucleon `status 14` in all 13,773 events) and the nucleon then goes through GENIE FSI. Truth 0p/1p/>=2p is the **post-FSI final-state multiplicity** and is kept separate from the decay channel (Delta0 -> n gamma vs Delta+ -> p gamma): Delta0 events are 70 % truth-0p / 24 % 1p / 6 % >=2p, Delta+ events 19 % / 70 % / 10 %.
* **Threshold:** a configurable parameter (`proton_ke_mev`, default 35.0), mirroring the reco rule. It is not scanned or tuned; the reco side has the same provisional status.

## 3. Evidence on the BNB CV

* **Primaries vs secondaries among true protons** (300 files of the truth-match scan, beam-neutrino true protons with start_E-based KE > 35 MeV): 2,260 have Geant4 mother 0 (primary), 980 (30 %) have a non-zero mother (secondary). So roughly 3/10 of proton *tracks* above threshold are not generator-level protons; the reco rule can count them. This is the reason truth 0p/1p/>=2p (generator final state) and "what the detector can see" will not agree event by event and why the truth-reco migration matrix is needed, **not** a reason to change the definition.
* **True proton multiplicity of active-volume neutrinos** (primary, KE > 35 MeV; 408 neutrinos; inclusive BNB, **not** signal): 0p 108, 1p 206, >=2p 94. Descriptive only.
* **Reco side:** the reco KE tracks the true proton KE (median reco/true 0.99 for 60-400 MeV, `RECO_PROTON_DEFINITION_AUDIT.md` §5) and above 35 MeV 95.7 % of type-2212 rows are truth protons.

## 3b. Official NC-Delta signal sample, truth proton multiplicity (measured; 13,773 events, signal neutrino chosen from the GENIE record, KE > 35 MeV, truth only, no efficiency)

| truth category | events | fraction |
|---|---|---|
| 0p | 6,501 | 47.2 % |
| 1p | 6,160 | 44.7 % |
| >=2p | 1,112 | 8.1 % (2p 711, 3p 245, 4p 111, 5p 29, 6p+ 16) |

Primary pi0 in 1.3 % and primary charged pion in 2.1 % of the signal neutrinos. By Delta type: Delta0 -> n gamma 5,311 / 1,809 / 479 (0p / 1p / >=2p); Delta+ -> p gamma 1,190 / 4,351 / 633 (`tables/official_ncdelta/truth_protons_by_delta.csv`). Because 0p and 1p are almost equally populated, the exclusive 1g0p and 1g1p channels are both genuine signal topologies of this process; the >=2p category stays diagnostic.

## 4. What remains a decision (not taken here)

1. The threshold value and whether truth and reco share it (kept 35 MeV for both, provisional).
2. Whether to also report a "visible truth" category (primaries + secondaries, containment-aware) as a systematic cross-check next to the generator-level category.
3. Whether neutrons / charged pions (excluded from `n_true_protons`) enter the exclusive topology definition `1 gamma + Np`: counts `n_primary_pi0`, `n_primary_pi_charged`, `n_primary_neutrons`, `n_primary_photons_hard` are stored so the choice can be made later without re-reading CAFs.

## 5. Interface

`truth_signal.signal_truth(...)` returns, per event and for the proxy-selected signal neutrino: `n_true_protons` (KE > threshold), `n_true_protons_all_ke`, `true_proton_category` (0/1/2, -1 = no signal neutrino), `photon_energy_mev`, `n_primary_{photons,pi0,pi_charged,neutrons}`, vertex, `neutrino_energy_gev`, `genie_mode`, `resnum`. `delta_pdg`, `delta_charge`, `decay_nucleon_pdg` are filled from the GENIE record when it is supplied (official flatCAF), and are returned as 0 = unavailable from `recTree` alone. Unit tests: `tests/test_truth_signal.py`.
