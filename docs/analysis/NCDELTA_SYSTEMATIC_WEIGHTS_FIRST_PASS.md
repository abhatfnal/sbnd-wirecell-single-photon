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

| Component | Functions / universes | Prescription | In band |
|---|---|---|---|
| flux | 13 / 13,000 (multisim) | sample covariance about the nominal, 1/N, families independent | yes |
| beamline G4 reinteraction | 6 / 6,000 (multisim) | same | yes |
| GENIE cross section | 27 / 2,700 (multisim, 100 universes) | same | yes |
| GENIE FSI | 2 / 200 (multisim: `FSI_pi`, `FSI_N`) | same | yes |
| cross-section extras | 4 single-universe GENIE shape dials (sigma = +1, no multisim counterpart) + 28 +-sigma-grid sets (4 MINERvA 2p2h, 2 C12-to-Ar40 scaling, 22 NOvA non-resonant pion) = 32 functions / 172 universes | one-sided shift (single) / (N(+1 sigma)-N(-1 sigma))/2 (grid), each independent | yes |
| GENIE multisigma duplicates | 48 / 288 | +-1 sigma response, diagnostic only | **no** (same knobs as the multisim sets: adding both would double count) |
| signal radiative BR | 1 / 100 (`multisim_RDecBR1gamma`) | computed and shown separately | **no** (outside the band by instruction) |
| non-sigma dials | 5 (`Mnv2p2hGaussEnhancement`, `nuenuebar`/`nuenumu` ratios, `SPPLowQ2Suppression`, `NR_nu_np_CC_1Pi`) | none | **no** (universes are not a +-sigma grid and no convention is documented) |

80 of 134 functions (22,072 universes) enter the band. Independence between functions/families is the standard assumption, not something verified here; 100-universe sets carry sampling noise of order 7 % on each variance.

## 4. Pathological-weight audit (`syst_weight_audit.csv`; nothing clipped)

* **Non-finite:** none in any function, any sample. **Negative:** only in GENIE multisigma *diagnostic* sets (e.g. `FrCEx_N`, down to -0.52, from the -3 sigma extrapolation); **none in any in-band function**. **Zeros:** present (e.g. `FSI_pi`: 999 zero entries among the selected Nov16 background; 22-27 in-band functions have zeros for the selected background), kept: a zero weight is a legitimate response.
* **Tails:** in-band maxima up to 398 (`reinteractions_neutron_Geant4`, selected Nov16 background; 515 in the random-file sample), 30.0 exactly for `piplus_Flux` (looks like a cap inside the weight calculator; not altered), 16-26 for the GENIE `ZExpA`/`FSI_pi` sets. No SBN prescription for clipping was found, so none is applied.
* **Applicability:** 59-60 of the 80 in-band functions are inert (exactly 1 for every event) for the selected NC-Delta signal (CC dials); 23-29 are inert for the selected background.
* **Single-event dominance** (`syst_single_event_dominance.csv`): sigma of the total yield without its single most influential event / with it, per multisim function; flag if < 0.8. Most flagged functions simply respond in one or two selected events (thin response). The one that matters is Nov16 `reinteractions_neutron_Geant4`: ratio 0.30 for the background (one event of weight up to 398 carries the effect). Totals are therefore given with and without the flagged functions.

## 5. First-pass band (`syst_band_by_component.csv`; S and B varied coherently, same universe index; unresolved events not varied)

Coherence is supported empirically: the S-B correlation across universes is 0.999 for the NC-resonance function and 0.8-0.95 for the flux families (independent draws would give ~0), consistent with the generator seeding the universes identically in both samples (fixed `random_seed` in the fcl). For each universe P_u = S_u/(S_u+B_u) is formed first and only then the spread is taken.

| Final selection, per 1e20 POT | old fg1 | Nov16 |
|---|---|---|
| S, B (nominal) | 29.3, 1040.7 | 68.3, 2526.3 |
| sigma(S) / S, total available | 24.8 % | 24.2 % |
| sigma(B) / B, total available | 19.9 % | 22.6 % (18.9 % without single-event-dominated functions) |
| sigma(S+B) / (S+B) | 19.9 % | 22.4 % (18.9 %) |
| **sigma(P) / P, coherent per-universe** | **18.5 %** | **20.6 % (18.0 %)** |
| sigma(P) / P, naive independent S and B | 30.9 % | 32.3 % |
| MC statistical sigma(P)/P (not in the band) | 6.7 % | 4.3 % |

sigma(P)/P by component (old / Nov16, per-universe coherent): flux 3.1 / 2.2 %, beamline G4 6.0 / 9.9 %, GENIE cross section 13.7 / 14.2 %, cross-section extras 6.7 / 4.8 %, GENIE FSI 8.0 / 9.7 %. Dominant: GENIE cross section, driven by `NCRESVariationResponse` (S 23 %, B 12 %, highly correlated). By topology (total available, old / Nov16): 1g0p 18.1 / 23.7 % (19.9 % without the flagged function), 1gNp 26.8 / 23.0 %. Energy histogram (`syst_cov_energy_*.npz`; 8 bins, 20-3000 MeV): total sigma/(S+B) 22-26 % (old, 6 bins with > 20 events) and 22-36 % (Nov16, 7 bins), larger than the MC statistical error in the well-populated bins (statistical 6-10 %) and smaller in the sparsely populated edge bins (statistical up to ~30 %). Covariances by component for S, B, S+B and purity are stored per view (all, topo2, channel3, energy).

**Outside the band, shown separately:** signal radiative-BR dial `multisim_RDecBR1gamma` moves S by 44.9 % (S-B correlation 1; B 0.2 %) and P by 43.6 / 43.7 %; if the radiative-BR model is wanted in the band this dominates everything else. `ThetaDelta2NRad` (photon angular distribution of the radiative decay, single universe) stays in the band as a one-sided shift and is a signal-decay-model dial: it alone gives 18.9 % (old) / 16.8 % (Nov16) on the 1gNp signal, i.e. the whole "cross-section extras" signal effect in 1gNp (1g0p: 7.0 / 6.3 %). Whether it belongs in the band or with the radiative-BR model outside it is a decision for the analysers; moving it out removes the 17-19 % extras effect on the 1gNp signal.

## 6. What the band covers and what is missing

* **Coverage of the prediction:** neutrino systematics are varied for **94.5 % (old) / 95.7 % (Nov16)** of the expected S+B yield (S 100 %, background by yield 94.3 % / 95.6 %); **5.5 % / 4.3 % is unvaried** (cosmic/unmatched and ambiguous owners).
* **Within the varied part, the band covers:** flux, beamline G4 reinteraction, GENIE cross-section and FSI multisim sets and 32 extras. It does not include the 5 non-sigma dials, the GENIE multisigma duplicates (by design), or functions that are inert for these events.
* **Missing / outside:** detector variations (no weights in these files; separate productions needed), beam-off / cosmic normalisation (blocked), dirt normalisation (dirt is inside the CV with no handle), POT, the signal radiative-BR model (shown separately), `imp_weight` (unresolved, see the results note section 6; hypothetical effect only), MC statistics beyond Poisson (shown separately), the neutrino systematics of unresolved-owner events, and the preselection/sideband extension (the NC-pi0 sideband excess cannot yet be compared with a band).
