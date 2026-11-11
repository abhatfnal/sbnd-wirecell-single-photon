# What the persisted truth says about the origin of the truth-1p proton: source audit of the proton-origin categories

Date: 2026-11-11. Branch `analysis/ncdelta-proton-origin-survival-20261111`. Audit only: nothing is re-selected or tuned. Tags: **SOURCE** (code / stored fields), **MEASURED** (`tables/proton_origin_survival_audit/`), **NOT STORED** (an ancestry the truth does not contain).

## 1. Fields that carry the origin  (SOURCE: `truth_signal.py:47`, `scripts/proton_truth_origin_scan.py`, `scripts/proton_truth_audit.py:162-185`)

* **GENIE record** (`GenieEvtRecTree` of the flatCAF, one record per neutrino interaction, reached through `rec.mc.nu.genie_evtrec_idx` of the signal interaction): `StdHepPdg`, `StdHepStatus`, `StdHepFm` (first mother, -1 = none), `StdHepFd` / `StdHepLd` (first / last daughter), `StdHepP4`, `IntType`. Status codes used: **1** = stable final-state particle, **14** = hadron inside the nucleus before the final-state interactions, which is how the **decay nucleon N** is identified: the status-14 nucleon whose first mother is the Delta (|pdg| 2114 / 2214).
* **Chain rules** (`classify_each_proton`, one class per stable proton above 10 MeV): the mother chain of the final-state proton P is walked through `StdHepFm`; `nuc in chain(P)` decides descent from N; `chain_has_nonproton` is true if any particle between P and N is not a proton; `n_decay_nucleon_proton_descendants` counts the stable proton descendants of N.
* **Join to the Geant4 primaries:** the GENIE final-state protons are matched one-to-one to the signal primary protons of the Geant4 truth (`rec.mc.nu.prim`, post-FSI) by event and nearest kinetic energy. **MEASURED: the matching difference is at most 1e-4 MeV for all 5,170 truth-1p protons** (tolerance 0.5 MeV; `origin_dke`), so the association is unambiguous here.
* **Not stored:** the individual intranuclear interactions (which rescattering happened: charge exchange, elastic, absorption), the GENIE hadron-transport process name, and any ancestry for the Geant4 secondaries (not needed: the truth-1p proton is a post-FSI primary). `IntType` is the interaction type of the neutrino interaction, not of the rescattering. So **"FSI-created" means "the mother chain contains a non-proton or starts from a neutron decay nucleon"**, an inference from the mother chain, not a recorded interaction.

## 2. Categories  (exclusive; mapping to the stored class in `origin_audit.origin_category`)

| category | stored class | definition (chain) | support |
|---|---|---|---|
| **A decay proton** | `decay_proton` | N is a proton, P descends from N through protons only, and P is the only stable proton descendant of N | status 14 / first-mother chain |
| **B1 Delta0: proton from the neutron decay nucleon (FSI-created)** | `fsi_created` with Delta0 | the decay nucleon of a Delta0 is a **neutron** in all 1,497 Delta0 events (MEASURED), so a proton can only arise through rescattering of N | `delta_pdg`, status-14 pdg |
| **B2 Delta+: decay-nucleon chain contains a non-proton (charge exchange)** | `fsi_created` with Delta+ | N is a proton but a non-proton (a neutron, by charge exchange) lies between N and P | `chain_has_nonproton` |
| **C proton not descended from the decay nucleon** | `not_from_decay` | N exists, P does not descend from it (a struck-nucleon or other knocked-out proton) | chain without N |
| **D ambiguous chain** | `ambiguous` | N is a proton, protons only, but N has several stable proton descendants (the proton above 35 MeV cannot be assigned uniquely to N) | `n_decay_nucleon_proton_descendants > 1` |
| **E other / unresolved** | `unknown` | no Delta or no decay nucleon in the record | none occurs (0 events) |

**Consequence that matters for every later comparison:** in a Delta0 event the decay nucleon is a neutron, so **no Delta0 event can be category A**: the origin category and the Delta charge are *structurally entangled* (Delta0 = B1 or C only; A is Delta+ only). The clean same-charge comparison is A versus B2 inside Delta+.

## 3. Reproduction of the earlier counts  (MEASURED; `origin_reproduction_phase8_*.csv`, `origin_composition.csv`)

Truth-1p events: **5,170** (Delta+ 3,673, Delta0 1,497), one post-FSI primary proton above 35 MeV each. They are the truth-1p events **with a Wire-Cell candidate** (the Phase-9 `event_taxonomy` population): the full truth-1p sample has 5,556 events, 386 of which have no candidate and so no frozen-chain record; every table of this phase uses the 5,170.

| category | Delta+ | Delta0 | all |
|---|---|---|---|
| A decay proton | 3,301 | 0 | 3,301 |
| B1 Delta0 FSI-created | 0 | 1,476 | 1,476 |
| B2 Delta+ charge-exchange | 294 | 0 | 294 |
| C not from decay | 5 | 21 | 26 |
| D ambiguous | 73 | 0 | 73 |
| E | 0 | 0 | 0 |

Events reaching `other` (**2,174**): the earlier Phase-8 numbers reproduce exactly: Delta+ decay proton **1,367 at 67.1 %**, Delta+ FSI-created **137 at 54.0 %**, Delta+ ambiguous **35 at 51.4 %**, Delta+ 1,541 at 65.5 %, Delta0 **633 at 57.3 %** (documented 57.4 %: rounding of 0.5734). **Label mapping:** the old "decay proton" is A; the old "FSI-created" is B2 inside Delta+ and **B1 inside Delta0**; "ambiguous" is D; "not from decay" is C. The old Delta+ comparison "67 % versus 54 %" is therefore **A versus B2**.

## 4. What is established / not

* Established: the chain classification is reproducible, the GENIE-to-Geant4 join is exact, and origin and Delta charge are structurally entangled (A only Delta+, B1 only Delta0).
* Not established: which rescattering created the proton (not stored); whether the neutron in a B1 / B2 chain also produced other hadronic activity: this is measured indirectly in the survival audit through the neutron-mother photons of the Geant4 truth.
