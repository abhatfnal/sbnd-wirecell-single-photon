# Selected-shower truth-match audit (which particle is the single-photon-candidate shower?)

MC evaluation only; frozen baseline, `any`, 649 passing candidates (635 non-signal in the tables below unless stated). Code: `scripts/background_deep.py`, `background_truth.origin_class`; table `tables/background_mechanisms/candidate_truth_category.csv` (`sh_*` columns), `selected_shower_origin_by_{channel,category}.csv`.

## 1. How `shw_sp_*` relates to the particle rows (established from data, not assumed)
Checked on the 649 passing candidates and on earlier probes of the schema:
* `wc.T_tagger.shw_sp_*` are candidate-level scalars; the lists `shw_sp_20mev_showers` / `shw_sp_br1_showers` … hold **per-shower 0/1 flags** (e.g. `[1, 0, 0]`), **not** indices into `T_kine`.
* `shw_sp_energy` equals the `kine_energy_particle` of **exactly one** shower row (`kine_particle_is_shower == 1`) of the same candidate: **646 of 649** candidates have exactly one such row (relative tolerance 1e-4); **3** have none (they are kept and flagged `no_matching_shower_row`). In all 646 the row type is 11 (the shower PDG label), `kine_energy_included` is 1 (637) or 3 (9, a leftover-shower row).
* That row is **not always the highest-KE shower row**: it is the maximum-KE shower in 623 of 646 (96.4 %) and a lower-energy one in 23. So "the leading `T_kine` shower is the `shw_sp` shower" is **false in 3.6 % of cases** and is not used; the energy-equality mapping is used instead (helper logic in `background_deep.deep_work`).
* `T_pf` was not needed: the reco side of the origin question is the `T_kine` row (`kine_particle_id` ↔ `T_overlap.particle_id`).

## 2. Truth origin of the selected shower
For the matched row, the truth track is the one with the largest **shared charge** among that row's `T_overlap` rows (sum of `q` per `trackid`), looked up in `T_truth_track` (pdg, `nu_idx`, `mother_pdg`, `process`, `ancestor_trackid`, `prong_trackid`). The origin class is the PDG of that track (`photon`, `electron_positron`, `proton`, `muon`, `charged_pion`, `neutron_or_hadronic`, `other`), or `cosmic_or_unmatched` when no neutrino-owned track dominates. Kept per candidate: the **dominant shared-charge fraction** `sh_frac` (dominant track charge / total overlap charge of the row), primary-vs-secondary (`mother_pdg == 0` and `process == 0`: Geant4 primary), the ancestor PDG (the top-level G4 primary the track descends from, looked up in `T_truth_pf`/`T_truth_track`) and the matched neutrino index (`tm_top_nu`, `mnu_k`).

Non-signal selected candidates (635), by reco channel:

| shower truth origin | 1γ0p | 1γ1p | ≥2p diag | all |
|---|---|---|---|---|
| photon | 223 | 131 | 55 | 409 |
| electron/positron | 67 | 93 | 37 | 197 |
| cosmic or unmatched | 14 | 1 | 0 | 15 |
| proton | 5 | 1 | 0 | 6 |
| muon | 0 | 3 | 2 | 5 |
| no matching shower row | 1 | 1 | 1 | 3 |
| charged pion / neutron / other | 0 | 0 | 0 | 0 |

By candidate-associated category (non-signal): NUE_CC 175/175 electron-origin; NC_PI0 187 photon, 3 proton, 1 electron, 1 no row; CC_PI0 101 photon, 4 electron, 1 proton; OUTSIDE_TPC_NU 84 photon, 10 electron, 1 muon; NUMU_CC 18 photon, 4 muon, 1 proton, 1 no row; OTHER_NC 16 photon, 2 electron, 1 proton, 1 no row; COSMIC_OR_UNMATCHED 15 cosmic + 1 electron; MULTI_OR_AMBIGUOUS 4 electron, 3 photon (`selected_shower_origin_by_category.csv`).

Match quality and ancestry: the dominant shared-charge fraction of the selected row has quantiles (0, 5, 25, 50, 75, 100 %) = 0.22, 0.50, 0.83, 0.92, 0.96, 1.00. **Photon-origin showers** (409): ancestor π⁰ in 356 (87 %), an original primary photon in 26, a charged pion in 18 (π⁺ 15, π⁻ 3), a proton in 6, a neutron in 2, unknown in 1; only 26 of the 409 photon tracks are Geant4 primaries (the rest are π⁰-decay or secondary photons). **Electron-origin showers** (197): 175 are ν_e CC (`NUE_CC`) and in **all 175** the dominant track is the Geant4-primary electron/positron of the interaction (ancestor = itself); the other 22 are 10 OUTSIDE_TPC_NU, 4 CC_PI0, 4 MULTI_OR_AMBIGUOUS, 2 OTHER_NC, 1 NC_PI0 and 1 COSMIC_OR_UNMATCHED. By ancestor: e⁻/e⁺ in 194, π⁺ in 2, π⁰ in 1.

## 3. What this does and does not establish
* The selected shower is overwhelmingly either a **photon (mostly from a π⁰)** or the **primary electron** of a ν_e CC interaction; hadron-origin (proton/muon) showers are 11 of 635 and cosmic/unmatched 15.
* The origin is the dominant *charge* contributor of one reconstructed row; a row can be a merger (fractions down to 0.22), so the label is "dominant origin", not "pure".
* For the 3 candidates without an energy-equality row, no origin is assigned.
* The truth tracks come from `T_truth_track` (tracks with charge in blobs); photons that deposit no charge cannot appear as a dominant origin, by construction.
