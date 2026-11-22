# First-pass neutrino-systematic band for the frozen NC-Delta selection (PRELIMINARY, MC only)

Status: **preliminary; do not quote as an uncertainty on a result.** Scope: the FINAL frozen selection (`n20br1` stage), old fg1-era reconstruction and WCLocal2026Nov16, expected yields per 1e20 POT, event level. No data, no Aurora DEV BDT, no `imp_weight`. Reproduce: `scripts/ncdelta_syst_extract.py owners|extract|audit`, `scripts/ncdelta_syst_diagnostics.py`, `scripts/ncdelta_syst_covariance.py` (tables `tables/ncdelta_purity_datamc/syst_*.csv`, `syst_cov_*.npz`; figure `plots/ncdelta_purity_datamc/E_syst_first_pass_*.png`).

## 1. Checks that had to close first (all closed)

| Check | Result |
|---|---|
| **recTree <-> recTreeWireCell mapping** (`syst_identity_proof.csv`) | Not assumed from equal entry counts: for **every entry of every file read** (3,548 files, 17,553 entries) run/subrun/event are identical **and in the same order** in both trees, unique in each, and each selected event is joined **by id** (never by entry number); the joined recTree entry equals the table's entry and the Wire-Cell id at that entry equals the table's id for 100 % of events. The signal master records index the *original flatCAFs* (their `(file_index, ev)` agrees with the analysis tables for 0.016 % of rows), so the signal owner is joined on run/subrun/event only. |
| **Owner interaction** | Background: the exact `mnu_k` of the truth scan (`light.parquet`, link distance <= 6e-5 cm, i.e. exact) for the passing candidate(s). Signal: `signal_nu_index` of the official master records. For every owner the `rec.mc.nu[k]` vertex equals the expected vertex (signal records / Wire-Cell truth vertex; max offset 2.7e-5 cm) and the PDG code matches, and the weight layout (neutrino-major, then function, then universe; `univ..length` = nuniv repeated per neutrino) holds, for 100 % of events. The dominant-neutrino approximation is not used. |
| **No invented owner** | An event has an owner only if every passing candidate has a production-matched neutrino interaction (not `COSMIC_OR_UNMATCHED`/`MULTI_OR_AMBIGUOUS`, finite `mnu_k`, one matched interaction) and all passing candidates share the same `mnu_k`. Otherwise it is **unresolved** and is held at the nominal weight in every universe (its neutrino systematics are unresolved and outside the band). No SBND/CAF convention for cosmic- or ambiguity-owned events was found in the installed source (sbnanaobj, sbncode `SBNEventWeight`), so none is invented. |
| **Counting unit** | Event level (any candidate passes; event once), as in the purity tables. The histogram variable of an event is the shower energy of its lowest-index passing candidate (deterministic; the owner does not depend on it). At the final stage **no** selected event has more than one passing candidate (S and B, both productions), so the rule has no effect here; for preselection/sidebands it must be re-checked (`n_events_whose_candidates_differ_in_energy_bin` in `syst_join_diagnostics.csv`). |
| **Unit-weight reproduction** (`syst_unit_weight_reproduction.csv`) | With all universe weights = 1 the attached events give exactly the committed S, B and purity for inclusive, 1g0p and 1gNp, both productions (6 of 6 exact; S 29.346 / 68.275, B 1040.670 / 2526.291 per 1e20; P 2.743 % / 2.631 %). |

## 2. Association quality (`syst_join_diagnostics.csv`)

| | old fg1 | Nov16 |
|---|---|---|
| selected signal events with a unique owner | 833 / 833 (100 %) | 1938 / 1938 (100 %) |
| selected background events with a unique owner | 267 / 283 (94.3 %) | 657 / 687 (95.6 %) |
| unresolved background (events: reason) | 13 cosmic/unmatched, 3 multi/ambiguous | 25 cosmic/unmatched, 5 multi/ambiguous |
| unresolved background yield per 1e20 POT (share of S+B) | 58.8 (5.5 %) | 110.3 (4.3 %) |

## 3. Sources, types and prescriptions (`syst_function_table.csv`, `syst_source_feasibility.csv`)

Types come from `caf::ReweightType_t` in the installed `SREnums.h` (0 multisim, 1 pm-n-sigma, 2 fixed, 3 multisigma), and the sigma value of every multisigma universe is read from `globalTree: global/wgts/wgts.map` (uproot cannot decode it; the raw basket is parsed with validated byte counts). Not every function is a 1,000-universe multisim:

| Component | Functions / universes | Prescription | In generic band |
|---|---|---|---|
| flux | 13 / 13,000 (multisim) | sample covariance about the nominal, 1/N, families independent | yes |
| beamline G4 reinteraction | 6 / 6,000 (multisim) | same | yes |
| GENIE cross section | 27 / 2,700 (multisim, 100 universes) | same | yes |
| GENIE FSI | 2 / 200 (multisim: `FSI_pi`, `FSI_N`) | same | yes |
| cross-section extras | 3 single-universe GENIE shape dials (sigma = +1, no multisim counterpart) + 28 +-sigma-grid sets (4 MINERvA 2p2h, 2 C12-to-Ar40 scaling, 22 NOvA non-resonant pion) = 31 functions / 171 universes | one-sided shift (single) / (N(+1 sigma)-N(-1 sigma))/2 (grid), each independent | yes |
| **NC-Delta signal-model systematics** | 2 / 101: `multisim_RDecBR1gamma` (Delta -> N gamma radiative branching ratio, 100 universes) and `multisigma_ThetaDelta2NRad` (photon angular distribution of the radiative Delta decay, 1 universe) | multisim covariance / one-sided shift, each computed and **shown separately** | **no - shown separately, not included in the generic neutrino band** (how to combine them into the final signal-model covariance is decided later) |
| GENIE multisigma duplicates | 48 / 288 | +-1 sigma response, diagnostic only | no (same knobs as the multisim sets: adding both would double count) |
| non-sigma dials | 5 (`Mnv2p2hGaussEnhancement`, `nuenuebar`/`nuenumu` ratios, `SPPLowQ2Suppression`, `NR_nu_np_CC_1Pi`) | none | no (universes are not a +-sigma grid and no convention is documented) |

79 of 134 functions (22,071 universes) enter the generic band. Independence between functions/families is the standard assumption, not something verified here; 100-universe sets carry sampling noise of order 7 % on each variance.

## 4. Pathological-weight audit (`syst_weight_audit.csv`; nothing clipped)

* **Non-finite:** none in any function, any sample. **Negative:** only in GENIE multisigma *diagnostic* sets (e.g. `FrCEx_N`, down to -0.52, from the -3 sigma extrapolation); **none in any in-band function**. **Zeros:** present (e.g. `FSI_pi`: 999 zero entries among the selected Nov16 background; 22-27 in-band functions have zeros for the selected background), kept: a zero weight is a legitimate response.
* **Tails:** in-band maxima up to 398 (`reinteractions_neutron_Geant4`, selected Nov16 background; 515 in the random-file sample), 30.0 exactly for `piplus_Flux` (looks like a cap inside the weight calculator; not altered), 16-26 for the GENIE `ZExpA`/`FSI_pi` sets. No SBN prescription for clipping was found, so none is applied.
* **Applicability:** 59-60 of the 80 in-band functions are inert (exactly 1 for every event) for the selected NC-Delta signal (CC dials); 23-29 are inert for the selected background.
* **Single-event dominance** (`syst_single_event_dominance.csv`): sigma of the total yield without its single most influential event / with it, per multisim function; flag if < 0.8. Most flagged functions simply respond in one or two selected events (thin response). The one that matters is Nov16 `reinteractions_neutron_Geant4`: ratio 0.30 for the background (one event of weight up to 398 carries the effect). Totals are therefore given with and without the flagged functions.

## 5. First-pass band (`syst_band_by_component.csv`; S and B varied coherently, same universe index; unresolved events not varied)

Coherence is supported empirically: the S-B correlation across universes is 0.999 for the NC-resonance function and 0.8-0.95 for the flux families (independent draws would give ~0), consistent with the generator seeding the universes identically in both samples (fixed `random_seed` in the fcl). For each universe P_u = S_u/(S_u+B_u) is formed first and only then the spread is taken.

| Final selection, per 1e20 POT (generic neutrino band, signal-model dials excluded) | old fg1 | Nov16 |
|---|---|---|
| S, B (nominal) | 29.3, 1040.7 | 68.3, 2526.3 |
| sigma(S) / S | 24.0 % | 24.0 % |
| sigma(B) / B | 19.9 % | 22.6 % (18.9 % without the single-event-dominated function) |
| sigma(S+B) / (S+B) | 19.9 % | 22.4 % (18.9 %) |
| **sigma(P) / P, coherent per-universe** | **17.5 %** | **20.3 % (17.7 %)** |
| sigma(P) / P, naive independent S and B | 30.4 % | 32.1 % |
| MC statistical sigma(P)/P (not in the band) | 6.7 % | 4.3 % |

How to communicate it: *WCL1116 frozen legacy chain: MC-only expected purity 2.63 %, with a preliminary +-20 % relative neutrino-model uncertainty (20.3 %) from the currently available flux/xsec/FSI/G4 weights. Detector, cosmic/beam-off normalisation, dirt, POT, the NC-Delta radiative-decay signal model, `imp_weight` and unresolved-owner events are not included.* It is not a final uncertainty on the purity (available sources only).

sigma(P)/P by component (old / Nov16, per-universe coherent): flux 3.1 / 2.2 %, beamline G4 5.9 / 9.9 %, GENIE cross section 13.7 / 14.2 %, cross-section extras 3.2 / 3.5 %, GENIE FSI 8.0 / 9.7 %. Dominant: GENIE cross section, driven by `NCRESVariationResponse` (S 23 %, B 12 %, highly correlated). By topology (total available, old / Nov16): 1g0p 16.6 / 22.9 % (18.9 % without the flagged function), 1gNp 19.5 / 16.2 %. Energy histogram (`syst_cov_energy_*.npz`; 8 bins, 20-3000 MeV): total sigma/(S+B) 22-26 % (old, 6 bins with > 20 events) and 22-36 % (Nov16, 7 bins), larger than the MC statistical error in the well-populated bins (statistical 6-10 %) and smaller in the sparsely populated edge bins (statistical up to ~30 %). The very large fractional uncertainties of the nearly empty low-energy bins of the old reconstruction are not an alarm: those bins have essentially no constraining statistics. Covariances by component for S, B, S+B and purity are stored per view (all, topo2, channel3, energy).

### NC-Delta signal-model systematics - shown separately, not included in the generic neutrino band

| Dial | effect on S (all) | on S (1g0p / 1gNp) | on P (all) | on B |
|---|---|---|---|---|
| `RDecBR1gamma` (radiative branching ratio) | 44.9 % (S-B correlation 1) | 44.9 / 44.9 % | 43.6 % (old), 43.7 % (Nov16) | 0.2 % |
| `ThetaDelta2NRad` (radiative-decay photon angle; one-sided, sigma = +1) | 6.2 % (old), 3.4 % (Nov16) | old 7.0 / 18.9 %, Nov16 6.3 / 16.8 % | 5.8 % (old), 3.3 % (Nov16) | 0.2 % |

If the radiative-decay model is to be in the final band, `RDecBR1gamma` dominates everything else on S and P; the two must be combined into one signal-model covariance later (they are not independent knobs of the same kind: one is a rate, the other an angular distribution).

## 6. What the band covers and what is missing

* **Coverage of the prediction:** neutrino systematics are varied for **94.5 % (old) / 95.7 % (Nov16)** of the expected S+B yield (S 100 %, background by yield 94.3 % / 95.6 %); **5.5 % / 4.3 % is unvaried** (cosmic/unmatched and ambiguous owners).
* **Within the varied part, the band covers:** flux, beamline G4 reinteraction, GENIE cross-section and FSI multisim sets and 31 extras. It does not include the 5 non-sigma dials, the GENIE multisigma duplicates (by design), or functions that are inert for these events.
* **Missing / outside:** detector variations (no weights in these files; separate productions needed), beam-off / cosmic normalisation (blocked), dirt normalisation (dirt is inside the CV with no handle), POT, the NC-Delta signal-model dials `RDecBR1gamma` and `ThetaDelta2NRad` (shown separately), `imp_weight` (unresolved, see the results note section 6; hypothetical effect only), MC statistics beyond Poisson (shown separately), the neutrino systematics of unresolved-owner events, and the preselection/sideband extension (the NC-pi0 sideband excess cannot yet be compared with a band).

## 7. Control regions: open-data Data/MC with the available covariance (`syst_sideband_datamc_chi2_*.csv`, figures F and G)

Same machinery, extended to the sidebands (`scripts/ncdelta_syst_regions.py plan|extract|analyze`; per-universe bin yields accumulated on the fly; the signal region stays blocked, only the open-data policy stages `sideband`/`preselection` are used). Event level for data, S and B alike (events with more than one region-passing candidate are < 0.5 % and none in the NC-pi0 sideband for the old reconstruction, so event and candidate counts coincide: 585 / 755 data events as before). For B the owner must be unique over all region-passing candidates of the event, otherwise the event is not varied. The prediction is S + B scaled to the open-data POT (4.62e18); **it does not contain the cosmic-only (beam-off) component** (scale blocked): adding it would raise the prediction and lower every Data/MC below. Independent identity/layout/vertex/PDG checks passed for all 28,251 accumulated events (13,517 old, 14,734 Nov16) with zero failures.

Covariance = flux + beamline G4 + GENIE cross section + cross-section extras + GENIE FSI (79 functions, S and B with the same universe index); data statistics enter the chi-square as the Pearson (expected-count) variance, Neyman is in the table as a cross-check. **Not in the covariance: detector, cosmic/beam-off, dirt, POT, NC-Delta signal model, `imp_weight`, unresolved-owner events (resolved owners: NC-pi0 sideband 96.9 % old / 97.2 % Nov16 of events; `SB_other` ~82 %).** The effect of the omitted categories on the final tension is not determined: additional uncertainty sources would generally reduce the chi-square (so the present chi-square/significance is, if anything, an upper bound on the tension at fixed nominal prediction), whereas the missing cosmic-only contribution would shift the nominal prediction upward and could increase the observed rate deficit.

### NC-pi0-rich sideband (the ~25 % deficit)

| | old fg1 | Nov16 |
|---|---|---|
| data events / prediction (S+B) | 585 / 765.8 | 755 / 1020.5 |
| **Data/MC (integrated)** | **0.764 +- 0.158** | **0.740 +- 0.154** |
| uncertainty: data stat / MC stat / available syst | 3.2 % / 1.5 % / 20.4 % | 2.7 % / 1.3 % / 20.6 % |
| syst by component (xsec GENIE / FSI / G4 / flux / extras) | 15.1 / 9.2 / 7.3 / 6.5 / 3.1 % | 15.2 / 9.6 / 6.9 / 6.4 / 3.7 % |
| deviation from 1: stat+MC only -> with available syst | -8.9 sigma -> **-1.5 sigma** | -11.8 sigma -> **-1.7 sigma** |
| rate-only chi2/ndof (p) | 1.29 / 1 (0.26) | 1.55 / 1 (0.21) |
| rate+shape, shower energy (8 bins) chi2/ndof (p) | 6.0 / 8 (0.65) | 8.4 / 8 (0.40) |
| shape-only, shower energy (8 bins) chi2/ndof (p) | 6.0 / 7 (0.54) | 9.7 / 7 (0.21) |
| rate+shape, reco topology (1g0p, 1gNp) chi2/ndof (p) | 8.5 / 2 (0.015) | 5.1 / 2 (0.080) |
| **shape-only, reco topology chi2/ndof (p)** | **12.3 / 1 (0.0005)** | **7.2 / 1 (0.0072)** |

Reading (preliminary): **once the available flux+GENIE+FSI+G4 covariance is included, the ~25 % rate deficit is within about 1.5-1.7 sigma** and the shower-energy shape is fully consistent; the deficit is flat in energy (the data/MC ratio is 0.6-0.8 in every populated bin) and the systematic covariance is almost a pure normalisation mode (96.7 % of its variance in one eigenmode), which is why the energy shape tests are unremarkable. **The topology split is not consistent, however:** the data/MC ratio is 0.91 (old) / 0.85 (Nov16) for reconstructed 1g0p but 0.61 / 0.64 for 1gNp (corr. of the systematic between the two ~0.95), i.e. the 1gNp fraction in the data is lower than predicted, a shape tension of p = 5e-4 / 7e-3 that no available neutrino systematic reproduces. Detector and proton-reconstruction modelling, which are absent from this band, are the obvious suspects. Neither statement is a conclusion about the physics: the rate result depends on the excluded categories above.

### Other regions (rate and shape; `syst_sideband_datamc_chi2_*.csv`)

| Region | Data/MC old (available unc.) | Data/MC Nov16 (available unc.) | energy rate+shape chi2/ndof old / Nov16 | note |
|---|---|---|---|---|
| `SB_other` | 1.054 +- 0.152 | 1.028 +- 0.148 | 7.9/8 (0.44) / **25.0/8 (0.0015)** | the Nov16 energy-shape chi2 is driven by two sparsely populated high-energy bins (1 observed vs 8.3 predicted, then 8 vs 2.2); this is the cosmic-rich, outside-TPC-like sideband where the MC has no cosmic-only component, so the excess in the last bin is the pattern the missing component would give (hypothesis, not demonstrated) |
| `SB_nue` | 0.993 +- 0.223 | 0.917 +- 0.200 | 1.8/5 (0.88) / 5.7/5 (0.34) | consistent; 3 empty-prediction energy bins dropped (ndof reduced) |
| `SB_numu` | 1.001 +- 0.297 | 1.012 +- 0.325 | 10.5/8 (0.23) / 9.2/8 (0.32) | numu-rich control close to 1; syst dominated by beamline G4 (25-28 %) |
| `preselection` | 0.984 +- 0.239 | 0.974 +- 0.247 | 15.8/8 (0.046) / 10.3/8 (0.25) | close to 1; old-reco energy shape mildly high (p = 0.046, shape-only 14.3/7), not significant given 6 regions examined |

Topology (2-bin 0p/Np) shape-only chi2/ndof in the nu-mu-rich and preselection regions is 2.6-3.2/1 (p = 0.07-0.11) for both productions, i.e. the 1g0p/1gNp split is much more significant in the NC-pi0 sideband (7.2-12.3/1) than here *with the available covariance*. CORRECTION (section 9): with statistics only the Np/0p double ratio is also ~0.80-0.82 in these two regions, so the effect is not specific to the NC-pi0 sideband; the available neutrino covariance simply absorbs most of it in the numu-rich and preselection regions.

Limitations specific to this section: the Pearson variance underestimates the variance of nearly empty bins (the Neyman column is the cross-check); 100-universe GENIE sets carry ~7 % sampling noise on each variance; shape-only chi-squares drop one bin (the sum is fixed); bins with zero prediction are dropped from the chi-square and the number of dropped bins is recorded.


## 8. NC-pi0 sideband: reco-topology diagnosis (1g0p / 1g1p / >=2p; `scripts/ncdelta_ncpi0_topology_diag.py`; DIAGNOSIS ONLY)

No selection, threshold or data-driven correction changed. Event level, S+B nominal at the open-data POT, **statistical uncertainties only** (data + MC); the neutrino covariance is a ~20 % mostly-normalisation mode and is not applied per bin here; **detector and proton-reconstruction systematics are absent, cosmic-only MC is absent, `imp_weight` unresolved.** Tables `ncpi0_topology_*.csv`, figure `H_ncpi0_topology_variables.png`.

| | old fg1 | Nov16 |
|---|---|---|
| data / MC, 1g0p | 360 / 396.9 = 0.91 +- 0.05 | 420 / 493.3 = 0.85 +- 0.04 |
| data / MC, 1g1p | 176 / 280.4 = 0.63 | 253 / 403.7 = 0.63 |
| data / MC, >=2p | 49 / 88.6 = 0.55 | 82 / 123.4 = 0.66 |
| normalisation-free double ratio (Np/0p)data/(Np/0p)MC | 0.67 +- 0.06 (5.4 sigma) | 0.75 +- 0.06 (4.3 sigma) |
| composition shape-only chi2/ndof (stat) | 17.6/2 (p = 2e-4) | 14.0/2 (p = 9e-4) |

Findings (preliminary):
- The deficit is **in the number of events with reconstructed protons, not a uniform rate deficit**: 1g1p and >=2p are both low; the 1g0p deficit is mild. WCL1116 moves the >=2p ratio from 0.55 to 0.66 and the double ratio from 0.67 to 0.75 (both within ~1 sigma of the old value, so no demonstrated improvement).
- **Not localised in the quantities available in the tables** (shape-only, stat-only chi2, MC scaled to data in each panel; all p > 0.05): leading-proton KE (including near the 35 MeV threshold), sum of proton KE, number of protons at any KE, shower energy, shower-vertex distance, shower angle, vertex x/y/z. The Np deficit is similar near and far from the TPC faces (0.63 / 0.60 old, 0.56 / 0.66 Nov16 for d_edge < / >= 25 cm), so it is not an edge effect. Reco-0p events with and without a sub-threshold proton have the same ratio (0.90 / 0.92 old, 0.85 / 0.85 Nov16): no sign of a threshold-migration pile-up. The MC Np events are ~60-65 % truth NC-pi0 (`ncpi0_topology_mc_truth_composition_*.csv`).
- **0p<->Np migration old -> Nov16** (same events reprocessed, `ncpi0_topology_migration_*.csv`): of 331 data events in the region in both productions 56 (17 %) change topology, 31 from 0p to Np and 12 the other way; MC (2607 events) 15 %, 182 0p->Np vs 93 Np->0p. Nov16 therefore moves both data and MC toward more Np (Np share: data 38 -> 44 %, MC 48 -> 52 %), leaving the data/MC gap similar.
- Interpretation (hypothesis only): a flat-in-all-variables Np deficit of ~35-40 % looks more like a proton-multiplicity / hadronic-model or proton-reconstruction-efficiency effect than a kinematic or boundary effect; the available GENIE FSI/xsec weights do not reproduce it (section 7). Not tested.

Superseded by section 9 (CAF extraction). Previously not done: pair-level pi0 observables (two-shower mass, opening angle, energy asymmetry, leading/subleading energy, conversion gap, dE/dx; (an earlier statement that `c_shw_sp_medium_dQ_dx` is zero in these tables was WRONG: values are ~0.1-1.4 and fell in one bin of my coarse binning; dQ/dx is used in section 9)), proton track length and start distance, and the truth->reco topology migration matrix for NC-pi0 (no truth proton count stored for generic-BNB background). These require a new CAF extraction/truth scan of the NC-pi0 sideband events.


## 9. NC-pi0 sideband topology: CAF extraction, truth->reco migration (DIAGNOSIS ONLY; `ncdelta_ncpi0_topology_extract.py`, `..._analyze.py`)

No cut, threshold or correction changed. **Statistical errors only. ABSENT: detector systematics (prominent for proton reconstruction), proton-reconstruction systematics, cosmic-only MC, dirt, POT, `imp_weight`, and the neutrino-weight covariance.** Same event set as section 7/8 (identity check against the analysis-table row: shower energy exact, extracted proton count equals the table topology for every event; 0 extraction errors; old 6,601 and Nov16 events). Truth exists only for MC (resolved background owners, 97 % of the weight, and signal-sample events); data has no truth. Truth topology = post-FSI primary protons of the owner interaction with KE > 35 MeV (`rec.mc.nu.prim.*` is stored flat per event and sliced by `nprim`; a first attempt that indexed it per interaction was wrong and was discarded and re-extracted). Tables `ncpi0_*.csv`, figures I (reco observables) and J (migration).

**Truth -> reco migration (MC, row-normalised: where truth topologies are reconstructed):**

| truth \ reco (all resolved MC) | old 0p / 1p / >=2p | Nov16 0p / 1p / >=2p |
|---|---|---|
| truth 0p | 0.77 / 0.20 / 0.03 | 0.80 / 0.18 / 0.03 |
| truth 1p | 0.42 / 0.50 / 0.08 | 0.34 / 0.58 / 0.09 |
| truth >=2p | 0.34 / 0.34 / 0.33 | 0.28 / 0.35 / 0.38 |

- The reco topology is a poor proxy for truth: ~45-55 % of reco-1g0p MC events have a true proton above 35 MeV, and only ~1/3 of true >=2p events are reconstructed as >=2p. At fixed truth (same MC events in both productions) WCL1116 reconstructs more protons: true-1p -> reco-0p 31 % -> 26 %, true->=2p -> reco->=2p 41 % -> 48 % (`ncpi0_truth_reco_migration_old_vs_nov16_same_events.csv`). Yet the data/MC Np ratios barely change (1gNp 0.63 -> 0.63; >=2p 0.55 -> 0.66), as expected if data and MC are both shifted.
- The proton-finding efficiency in MC is non-monotonic in true leading-proton KE (`ncpi0_true_proton_ke_reco_efficiency.csv`): reco-Np fraction 0.38-0.46 at 35-50 MeV, 0.73-0.77 at 100-400 MeV, and again only 0.55 above 400 MeV (old and Nov16).
- The reco-Np MC population is ~83-85 % truth-Np; the reco-0p MC population is ~45-55 % truth-0p. The MC reco-Np events are ~88-92 % events with a truth pi0.

**Observables (data/MC normalization and shape-only chi2, stat only; `ncpi0_topology_cafobs_datamc.csv`, `..._old_vs_nov16.csv`)**, separately for reco 0p / 1p / >=2p, old and Nov16: pair-found fraction, two-shower mass, opening angle, leading/subleading shower energy, energy asymmetry, conversion gaps (nearer/farther), candidate-shower dE/dx and dQ/dx, shower-vertex distance, leading proton KE, leading-proton first-segment length, number of protons, track/shower rows.
- The normalization ratios of every sub-sample equal the topology ratios (0.55-0.91): the deficit is the same for events with and without a found pi0 pair and in every mass/energy/gap bin, i.e. it is **not associated with pi0 kinematics or pair finding**.
- Shape-only chi2: of 92 comparisons only a handful have p < 0.05 (e.g. dQ/dx 1g0p old p = 0.001, track rows >=2p old p < 0.001) and none of them reproduces in the other production. With ~92 tests ~1 at p < 0.01 is expected. No observable shows a consistent shape discrepancy.
- Reco proton KE and length shapes in 1gNp/>=2p are consistent with MC (p = 0.1-0.9): the deficit is not concentrated at low proton KE, short tracks or near the 35 MeV threshold, which a threshold-type reconstruction loss would produce.
- Not available in the CAF in a usable form: proton start distance from the vertex (T_pf is empty, no segment vertex coordinates; the segment lengths used are the first segment of the particle, nseg is recorded), true pi0 momentum is present but pi0 itself is not a primary (median ~200-300 MeV/c of the pi0 as listed in prim; used only descriptively).

**Cross-region control (stat only, `np_over_0p_double_ratio_all_regions.txt`):** the same Np/0p data/MC double ratio is 0.82 / 0.80 (old / Nov16) in preselection and 0.81 / 0.80 in `SB_numu`, 0.91 / 0.79 in `SB_other`, 0.67 / 0.75 in the NC-pi0 sideband, 1.07 / 0.54 in `SB_nue` (few events). **The MC overpredicts the reco-Np/0p ratio by ~20 % in all populated regions; the NC-pi0 sideband is only moderately lower.** With the available neutrino covariance the shape-only topology chi2 is p = 0.07-0.11 in the numu/preselection regions but p = 5e-4 / 7e-3 in the NC-pi0 sideband (section 7), so the neutrino covariance covers much more of the general ~20 % effect than of the larger NC-pi0 one.

**Answer to the key question (what the data support, not proven):** (i) not pi0 kinematics, not pair finding, not edge, not low proton KE; (ii) the effect is general (~0.8 in preselection and the nu-mu-rich region, which are CC-dominated and have a different hadronic final state), which points to something common to all events - proton reconstruction/topology migration in MC, or the generic hadronic (FSI/proton-multiplicity) model - rather than to NC-pi0 physics; (iii) the data cannot separate the two: data has no truth, and because the MC migration is large (true-Np -> reco-0p 30-40 %), a lower reco-Np fraction in data can come from fewer true protons or from a different reconstruction efficiency; the available GENIE FSI/xsec weights do not reproduce the NC-pi0 shape tension. **Detector systematics (proton reconstruction, calibration, recombination) are absent and are the most likely missing piece**; an independent test needs detector-variation samples or an alternative generator, neither of which is available here. The extra NC-pi0 deficit above the general ~0.8 (double ratio 0.67-0.75) is ~1-1.5 sigma stat-only relative to the general value.


## 10. Np/0p double ratio with the available covariance; exact P(truth Np | reco topology) (`ncdelta_np_over_0p_summary.py`, figure K)

**Weight-tail finding that affects earlier numbers.** Propagating the saved topo2 covariance to the Np/0p double ratio gave an implausible 34-50 % uncertainty in preselection and `SB_numu`, entirely from `reinteractions_neutron_Geant4`: in the Np bin its universes have a resolved mean event weight up to 13.7 (0p bin: 0.85-1.14), which over ~18,600 events needs a total excess weight of O(10^5), i.e. a handful of events with enormous weights, not a smooth reweighting. This is the same function that is already flagged `single_event_dominated` for Nov16 in the final-selection table (sigma ratio 0.30 without the top event). It is **not clipped** (standing rule); here it is reported both ways. Consequences: (a) the beamline-G4 contribution quoted for `SB_numu` ("25-28 %") and the 24-30 % total available uncertainty on the preselection/`SB_numu` integrated Data/MC rates in section 7 are inflated by this one weight-tail function; (b) the topology shape-only chi2 p = 0.07-0.11 quoted for those two regions in section 7 is likewise too lenient; (c) the NC-pi0 sideband and `SB_other` are not affected (no tail function; NC-pi0 integrated 20.4 / 20.6 % unchanged); `SB_nue` has one mild tail function (`NCRES`) with negligible effect. A per-event leave-one-out audit for the control regions was not done (the extraction stores per-universe sums); this should be done before the integrated numbers for preselection/`SB_numu` are quoted.

**Np/0p double ratio (data/MC), available neutrino covariance via delta method on S+B with coherent universes; detector and proton-reconstruction systematics ABSENT:**

| region | old | Nov16 | rel. unc. available (stat+MC+syst, tail functions excluded; incl.) |
|---|---|---|---|
| preselection | 0.820 | 0.797 | 6.6 % (33.8 %) / 6.1 % (36.7 %) |
| `SB_numu` | 0.813 | 0.798 | 7.0 % (42.6 %) / 6.4 % (50.0 %) |
| `SB_ncpi0` | 0.672 | 0.746 | 11.3 % / 10.9 % |
| `SB_other` | 0.905 | 0.785 | 12.5 % / 10.2 % |
| `SB_nue` | 1.07 | 0.54 | 36 % / 30 % |

Deviation from 1 with the available covariance (tail functions excluded / included): preselection -3.4 sigma / -0.6 (old), -4.2 / -0.7 (Nov16); `SB_numu` -3.3 / -0.5, -4.0 / -0.5; `SB_ncpi0` -4.3, -3.1; `SB_other` -0.8, -2.7; `SB_nue` +0.2, -2.8. Statistics only: -9.3 / -10.7 (preselection), -8.5 / -8.9 (`SB_numu`), -5.4 / -4.4 (`SB_ncpi0`). So the ~20 % MC excess of reconstructed Np/0p in preselection and the nu-mu-rich region is significant if the single weight-tail function is excluded and not significant if it is kept at face value; the ordering of regions is unchanged. The NC-pi0 sideband is lower than the control regions by ~0.1-0.15 in the ratio, ~1 sigma of its available uncertainty. The significance depends on a weight-tail decision that has to be audited at event level; do not quote the sigmas prominently.

**Exact weighted inverse conditional fractions (MC, resolved owners, S+B weights at open-data POT, stat error only; `ncpi0_P_truth_Np_given_reco.csv`):**

| reco topology | P(truth >= 1 proton above 35 MeV \| reco), old | Nov16 | resolved weight fraction |
|---|---|---|---|
| reco 0p | 0.525 +- 0.011 | 0.446 +- 0.009 | 0.957 / 0.960 |
| reco 1p | 0.831 +- 0.009 | 0.854 +- 0.007 | 0.983 / 0.984 |
| reco >=2p | 0.909 +- 0.013 | 0.928 +- 0.010 | 0.975 / 0.981 |

So "about half of reco-0p MC events have a true proton above 35 MeV" is 52.5 % (old) and 44.6 % (Nov16), computed directly from the weighted sample (not from the row-normalised migration matrix, which gives P(reco | truth)). The previous statement of "45-55 %" was read from the column-normalised table, which is the same quantity.

Figure `K_np_over_0p_double_ratio_by_region.png` is the single collaboration plot (thick: data+MC stat; thin: + available covariance excluding the weight-tail function; dashed: including it). Message: a general reconstructed-proton-multiplicity mismatch (MC Np/0p too high by ~20 %) is present in every populated control region and not unique to NC-pi0; WCL1116 improves truth->reco proton finding in MC but the data/MC mismatch remains; reconstruction vs hadronic modelling cannot yet be separated (detector-variation samples or an alternative generator are needed). Detector and proton-reconstruction systematics are absent.


## 11. Event-level audit of `reinteractions_neutron_Geant4`, search for a prescription, and the band policy (`ncdelta_neutron_g4_extract.py`, `_audit.py`, `_topevents.py`; closes section 10)

Section 10 only had per-universe sums for the control regions, so the leave-one-out audit at event level had NOT been done; it is done here. A per-event extraction of the function's 1000 universe weights of the owner interaction (+ owner truth) was run for all resolved S and B events of preselection and `SB_numu` (old 55,249 events, Nov16 54,883; 0 identity / layout / vertex / PDG failures), and the stored final-selection blocks were used for the final frozen selection. Nothing is clipped or removed. Exact decomposition of each quantity's variance into per-event shares (`Var = sum_e s_e`; events needed for 50/90/99 % of it), plus leave-one-out sigma ratios (`audit_neutron_g4_*.csv`, `audit_neutron_g4_top_events.csv`).

**Concentration (total variance contributed by this function; N events for 50 / 90 / 99 % of the variance; top-event share; minimum leave-one-out sigma ratio):**

| selection | quantity | rel. sigma from this function | N50 / N90 / N99 | top share | min LOO ratio |
|---|---|---|---|---|---|
| preselection old | total yield | 18.4 % | 1 / 1 / 8 | 0.91 | 0.31 |
| preselection old | Np yield | 34.8 % | 1 / 1 / 1 | 1.00 | 0.20 |
| preselection old | 0p yield | 5.4 % | 168 / 635 / 783 | 0.05 | 0.97 |
| preselection Nov16 | total yield | 19.3 % | 1 / 2 / 9 | 0.87 | 0.32 |
| preselection Nov16 | Np yield | 36.7 % | 1 / 1 / 2 | 0.94 | 0.18 |
| preselection Nov16 | 0p yield | 5.7 % | 327 / 872 / 1028 | 0.01 | 0.99 |
| `SB_numu` old | total / Np / 0p | 24.8 / 43.7 / 5.4 % | 1/1/4 ; 1/1/1 ; 19/236/317 | 0.94 / 1.00 / 0.14 | 0.23 / 0.16 / 0.93 |
| `SB_numu` Nov16 | total / Np / 0p | 27.7 / 49.1 / 6.1 % | 1/1/3 ; 1/1/2 ; 224/580/681 | 0.92 / 0.94 / 0.01 | 0.23 / 0.15 / 0.99 |
| final selection old, B yield | B yield | 8.1 % | 14 / 31 / 36 | 0.10 | 0.91 |
| final selection old, S yield | S yield | 3.1 % | 35 / 70 / 79 | 0.02 | 0.98 |
| final selection Nov16, B yield | B yield | 12.3 % | **1 / 2 / 2** | 0.76 (two events carry > 100 % jointly; the rest are negative) | **0.30** |
| final selection Nov16, S yield | S yield | 2.7 % | 46 / 94 / 106 | 0.01 | 0.99 |

**Top events** (`audit_neutron_g4_top_events.csv`, top 10 per production/region/quantity with run/subrun/event, sample, reco topology, authoritative truth category, owner `mnu_k`, PDG, CC/NC, mode, true Enu, true protons > 35 MeV, true neutrons, max/min weight, scores, stage membership, old/Nov16 cross-match). The leading event in preselection and `SB_numu` is the same physical MC event in both productions: run 8011 / subrun 91 / evt 3, a nu-mu NC RES (Enu 1.41 GeV, 2 true neutrons, true proton count 0), authoritative category NC_PI0, reco Np, maximum universe weight **223,065**; in 161 of its 1000 universes the weight exceeds 100 and in 331 it exceeds 10 (median 1.09, 99th percentile 1.9e4). It is not in the final selection (`SB_numu`: numu score -0.94). The next events have weights 13,428 (4582/90/37, CC RES, truth OUTSIDE_TPC_NU), 3,276 and 3,240, 2,299, 1,642, 1,452 ... (the tail is continuous, not a single freak). Six to seven of the top-10 events are shared between old and Nov16 because the generic BNB CV events are the same MC interactions with the same flux/generator weights; reconstruction only changes whether they enter. In the final selection, the Nov16 leaders (4531/62/32: nu-mu CC DIS, truth OUTSIDE_TPC_NU, max weight 350; 2741/72/22: nu-mu CC RES, truth OUTSIDE_TPC_NU, max weight 398; true neutrons 0 and 2) are not in the old final selection; the old final selection has no dominant event (largest max weight 36).

**Diagnosis.**
- **A (a tiny number of events with enormous weights): yes for Np-rich selections and for the Nov16 final selection**; the 0p yield and the old final selection are broad (hundreds of events), i.e. benign.
- **B (broad coherent large weights): no.** 17-34 % of events have exactly unit weight in every universe, the median event maximum is 1.1, 1-1.6 % of events exceed 10, 0.1 % exceed 100 (preselection, `SB_numu`), consistently for S and B.
- **C (association/indexing mistake): not supported.** Every event passed the id / layout / owner-vertex (1e-3 cm) / owner-PDG checks; the leading weights are the owner interaction's own (the maximum over all interactions of the event equals the owner's for all top-10 events; in multi-interaction events another interaction has the larger weight in 11 % of cases, only 15 of 33,010 above 100); and the same heavy tail exists in an unselected random sample of 3,586 generic BNB-CV interactions (1.03 % above 10, 0.14 % above 100, max 515) with no selection or owner involved.
- **D (something else): yes.** The function is a heavy-tailed property of the weights themselves (a product of per-track weights, floored at 0 and uncapped in `Geant4WeightCalc`; no relation to the interaction's own final-state neutrons: weight > 300 occurs with 0 true neutrons). Whether the large values are physical is not established.

**Prescription search (source-established vs ours).** Searched: the sbncode SBNEventWeight source and fcl on CVMFS (v10_26_00 and the local copies of v10_14/15 fcl), the local user repositories (`cafpyana`, ICARUS `pyana`/`sbnana` weights notebooks), this repository, and the web. Found: (1) `sbn_eventweight_geant4` (`eventweight_geant4_sbn.fcl`) declares `min_weight: 0.0` and `max_weight: 100` for the Geant4 reinteraction calculators, but I found no code in SBNEventWeight that reads those parameters, and the CAF weights we use contain values up to 2.2e5, so no cap of 100 is evident in these samples (which sbncode version produced them is unknown); `Geant4WeightCalc` floors each track weight at 0 only. (2) The BNB flux calculators (PrimaryHadron*, Unisim) clamp weights at 30; these belong to the `*_Flux` functions, not `reinteractions_*_Geant4`. (3) `cafpyana`'s `makedf/g4syst.py` (and an ICARUS notebook) lists only the pi-, pi+ and proton Geant4 reinteraction functions, i.e. the neutron and kaon functions are not used there; no reason is documented. **No approved or documented SBN treatment (clip, universe rejection, event rejection, covariance rule) of extreme `reinteractions_neutron_Geant4` weights was found.** None is invented here: excluding the function is our diagnostic choice, not a source-established prescription (question 5 of the top-priority list for Haiwang/Hanyu).

**Band policy for this development note.**
1. Nominal central prediction: unchanged (unit weights; no clipping).
2. **"Validated available neutrino covariance"** = flux + GENIE cross section + cross-section extras + GENIE FSI + beamline-G4 functions **except `reinteractions_neutron_Geant4`** (applied identically in all regions and both productions). Single-event / thin-response flags of other functions are unchanged and listed in `syst_single_event_dominance.csv` (their effect is small; no function other than the neutron one has a weight tail in the control regions, `NCRES` in `SB_nue` is mild).
3. **Unvalidated weight-tail diagnostic**: `reinteractions_neutron_Geant4` shown separately (dashed in the figures, "incl. nG4" columns, `unvalidated_nG4` component). Every figure and table states whether the error bar includes it, excludes it, or shows both. Neither choice is a final systematic uncertainty. Detector / proton-reconstruction uncertainties are missing in all of them.

**Consequences for earlier numbers (validated / including nG4):**
- NC-pi0 sideband Data/MC deviation from 1: -1.6 / -1.5 sigma (old), -1.8 / -1.7 sigma (Nov16); the headline "not significant with the available covariance" holds under either choice.
- Final frozen selection purity relative band (coherent S/B universes): old 16.5 % / 17.5 %, Nov16 17.8 % / 20.3 % (the function alone: 5.9 % / 9.8 % relative, driven by two events in Nov16). Central purity values are unchanged (2.74 % and 2.63 %, MC-only upper bound); no "+-" is attached to them.
- Control-region integrated rate uncertainty of preselection / `SB_numu`: 15-17 % validated vs 24-33 % including the function.
- **The energy-shape tests get worse, not better, with the validated covariance in the muon-rich samples:** Nov16 preselection rate+shape chi2/ndof 22.4/8 (p = 0.004; 10.3/8 including the function), `SB_numu` 16.4/8 (p = 0.04; 9.2/8), old preselection 17.9/8 (p = 0.02). The function's single-event tail had been absorbing a shape disagreement; nothing about it is validated, so these two numbers bracket the result.
- Np/0p double ratio deviation from 1: preselection -3.4 / -0.6 sigma (old), -4.2 / -0.7 (Nov16); `SB_numu` -3.3 / -0.5, -4.0 / -0.5 (validated / including); NC-pi0 -4.4 / -4.3 (old), -3.2 / -3.1 (Nov16). The Np/0p excess of the MC is a significant effect in the validated covariance in preselection and `SB_numu` and not significant if the tail function is kept at face value; do not quote the sigmas prominently.
