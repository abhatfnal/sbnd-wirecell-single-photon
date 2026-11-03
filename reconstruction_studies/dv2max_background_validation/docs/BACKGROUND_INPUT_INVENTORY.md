# Background input inventory and truth definitions

Work area W = `single_photon/development/dv2max_background_validation_20261102/`. Full table: `tables/background_input_inventory.csv`.

## Chosen sample: Stage-A 10k BNB + CORSIKA (one sample, two truth classes)

- **Path:** `single_photon/development/nugraph-light-model-v0-20261013/training/stageA_production/stageA10k_fullchain_canary/inputs/reco1/`
  - 3628 reco1 files; 10,000 unique-RSE events (runs 150001–150040), listed in `.../manifests/stageA10k_events.csv`.
- **Owner:** Avinay. This is your own Aurora production `gen2-wct0319-bnb-fullchain-canary-512x8-timeoutfix-20261011T2231Z`, transferred to Eagle with sha 3628/3628 verified.
  - It was used read-only here, as it was for Stage-A NuGraph training. This test does not use any NuGraph sample or NuGraph reconstruction; only the Reco1 art files are read.
- **Software:**
  - sbndcode v10_14_02_03; project `prodgenie_corsika_proton_rockbox0p1_sbnd`; production MCP2023Blike; `standard_reco1_sbnd.fcl`.
  - Processes: GenieGen → G4 → DetSim → Reco1.
- **Why it is chosen:** it is the largest truth-complete Reco1 sample on Sophia. It carries exactly the products the signal-study fcl reads: `recob::Wires simtpc2d:dnnsp`, `opflashtpc0/1` and `simtpc2d:badmasks`. Every other candidate is smaller, owner-private, without truth, or not mounted (see the table).

**Comparability caveat with the NC-Δ signal sample.**
- The signal file has **no cosmic overlay**. It was our own NC-Δ production with no CORSIKA, run under the v10_14_02_04 environment.
- The background sample is **BNB + CORSIKA**, a rockbox production, so up to several neutrino interactions per spill, plus cosmics.
- The same Wire-Cell stack therefore also performs cosmic rejection and flash matching here. "Neutrino candidate" counts are not directly comparable to the signal ones.
- The O-vs-D comparison *within* a sample is unaffected, because the events are identical. No other compatible no-cosmic BNB sample exists on Sophia, and no new MC was generated.

## Truth predicates (generator truth only; nothing reconstructed is used)

**Census** (`scripts/truth_census.py`, login node, read-only):
- **Products decoded:** `simb::MCTruth` (label `generator`, all n ≥ 1 interactions per event, with the full GENIE particle list), `simb::GTruth` and `simb::MCFlux`.
- **Decoder:** the validated memberwise decoders (`mixed_sample_v1_20261012/scripts/decode_generator_truth.py`, exec'd verbatim), extended in `scripts/partlist_decoder.py` to the full particle list.
  - Byte-exact end-of-buffer assertions pass on all 10,000 events.
  - MCTruth, GTruth and MCFlux agree on ν PDG and CC/NC for **18,066 / 18,066** interactions.
- **Interaction vertex:** MCTruth fNu trajectory start (world cm).
- **Active-LAr test:** inside an SBND `volTPCActive` placement, using the same sbnd_v02_06 GDML boxes as the binding NUECC definition: x ∈ [−201.3, 0] ∪ [0, 201.3], |y| ≤ 203.73, z ∈ [0, 501] cm.

**Class predicates:**
- **ν_μ CC interaction:** |ν PDG| = 14, CC (`fCCNC = 0`, cross-checked GTruth `fGint = 2`), vertex in active LAr.
- **NC π0 interaction:** NC (`fCCNC = 1`, GTruth `fGint = 3`), ≥ 1 **status-1 (GENIE stable final state, after FSI) π0** (PDG 111), vertex in active LAr, any flavour.
  - GENIE leaves the π0 undecayed; G4 decays it.
  - GTruth's exclusive-channel `fNumPi0` is **not** used: it is non-zero for only 3 of the 223 NC events that have a final-state π0.
- **Event class:** the event contains a qualifying interaction **and exactly one interaction in active LAr** ("clean"), so the truth vertex is unambiguous. Out-of-LAr rockbox interactions and cosmics are allowed.

**Census of the 10,000 events:**
- Active-LAr interaction multiplicity per event: 0: 5246 / 1: 4586 / 2: 161 / 3: 7.
- ν_μ CC: 3423 events (3264 clean).
- NC π0: 223 events (214 clean; 202 single-π0, 10 with 2 π0, 2 with 3 π0).
- No event is in both clean classes.

## Event lists (fixed before any reconstruction; `scripts/make_event_lists.py`)

| list | content | order |
|---|---|---|
| `inputs/numucc_events.csv` | the **first 400** clean ν_μ CC events | census (`selection_index`) order, i.e. file order |
| `inputs/ncpi0_events.csv` | **all 214** clean NC π0 events | census order |

- `evt_idx` = row number, which is also the run directory `evt_NNNN`. Each event is run with `--nskip <entry> -n 1` on its own source file.
- **Diagnostic topology columns:**
  - from GENIE: mode, E_ν, lepton E, counts of π0, π±, p (KE > 35 MeV), γ;
  - from G4 `largeant`: muon energy, straight length and end-in-active; leading π0 energy; its two decay photons (energy, conversion distance from the π0 start = photon track end) and the energy asymmetry.

**Stage 1 pilot:** evt_idx 0–29 of each list.

**Sentinels:** chosen from the pilot on truth topology only, never on BDT score (`inputs/sentinels.csv`).

| role | runset / evt | truth |
|---|---|---|
| long muon | numucc 27 | QE, contained μ, 180 cm |
| multiprong | numucc 13 | RES, 1 π±, 2 p |
| EM shower | numucc 3 | CC π0; γ 150 + 84 MeV; one converts at 31.5 cm |
| contained 2γ | ncpi0 8 | vertex 92 cm from the active boundary; γ 387 + 139 MeV, both convert in active |
| asymmetric | ncpi0 2 | A = 0.63; γ 354 + 80 MeV |
| detached conversion | ncpi0 0 | γ2 converts 47 cm from the vertex |
