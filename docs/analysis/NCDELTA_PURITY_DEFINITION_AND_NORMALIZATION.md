# Expected purity: definition, normalisation ledger, double-counting resolution

Code: `src/sbnd_single_photon/purity.py`; tables `tables/ncdelta_purity_datamc/normalization_ledger.csv`, `normalization_closure_checks.csv`, `normalisation_numbers.json`; scripts `scripts/ncdelta_purity_tables.py`, `scripts/ncdelta_normalization_ledger.py`. Everything is MC evaluation of the **frozen** legacy chain; nothing is tuned, no Aurora development BDT is used.

## 1. Definition

> **P = S / (S + sum_i B_i)**, every term an **expected yield at one common exposure** (`POT_target`, 1e20 by default; the open-data POT 4.62125e18 for data/MC).

* `S = N_sel(dedicated NC-Delta) x POT_target / POT(dedicated)`, `B_i = N_sel,i(generic-BNB CV, without in-region natural NC-Delta events) x POT_target / POT(CV)`.
* A raw fraction of a filtered or exclusive sample is **never** called purity (e.g. "signal-like / selected" within the CV is a bookkeeping number, not P).
* Error: weighted Poisson, `sigma_S = sqrt(N_s) w_s`, `sigma_B = sqrt(N_b) w_b`, `sigma_P` by first-order propagation of independent S and B (`purity.purity`). **Statistical only.**
* Efficiency is unchanged: events with *any* passing candidate / 12,427 truth signal events in the provisional TPC box (exact binomial 68 % intervals).
* **Truth vs reconstructed topology.** Purity by topology uses the **reconstructed** proton multiplicity of the passing candidate (`reco_proton_cat`: 0, 1, >=2 protons above 35 MeV): `1g0p`, `1g1p`, `ge2p`, and `1gNp = 1g1p + ge2p`. The truth convention (post-FSI primary protons handed to Geant4 with KE > 35 MeV) is used only for the efficiency denominators (`signal_topology_efficiency.csv`). Delta0 is not 0p and Delta+ is not 1p.

## 2. Normalisation ledger (exact provenance in `normalization_ledger.csv`)

| sample | role | exposure | weight at 1e20 POT | cosmics | notes |
|---|---|---|---|---|---|
| `official_gen2_ncdelta` | **signal expectation** | 2.83853e21 POT = sum `TotalPOT` of all 15,777 flatCAFs (= SAM `mc.pot`; zero-event units carry POT) | 0.035229 per event (12,427 -> 437.8 per 1e20) | overlaid (CORSIKA) | filter acceptance implicit in the POT; `TotalGenEvents` (125/file) deliberately not used; 1 of 13,773 events never processed by Wire-Cell |
| `bnb_cv` | **background (generic BNB)** | 2.71940e19 POT = sum `TotalPOT` of the 37,742 listed files (same files for old and Nov16) | 3.6773 per event | overlaid | **contains** natural NC-Delta (416 events; 117 in the TPC box), dirt/rock interactions (`OUTSIDE_TPC_NU`) and intrinsic nue |
| `nuecc` | **control only** | n/a | **not used** | | exclusive production, not a BNB mixture |
| `beam_on_open` | data | 4.62125e18 POT (1,817 files) | 1 | n/a | runs 18255, 18259 |
| `beam_off` | cosmic **shape only** | none (TotalPOT = 0); gate counters 2,542,847 vs 960,047 | **no scale** | n/a | scale blocked (blocker G) |

## 3. Double counting: resolved

* **NC-Delta.** The generic CV contains natural NC-Delta -> N gamma (GENIE-record ancestry: 416 events, 117 with the vertex in the signal region). Every CV event that contains an **in-region** natural NC-Delta interaction is removed from the background (`remove_in_region_natural_signal`, selection-independent, so the same at every stage); the dedicated sample alone supplies S. The out-of-region natural NC-Delta events (11 padding, 288 rock) are real photon backgrounds and stay in B as `OUTSIDE_TPC_NU`. Consistency of the two normalisations: dedicated in-region rate 437.8 vs natural-CV 430.2 +- 39.8 per 1e20 POT (ratio 0.983).
  * Removed: 105 CV events that have a candidate; 8 (old) / 17 (Nov16) of them would have been selected at the final stage.
  * Convention note: Round 1 labelled 9 of the 291 selected old CV events "signal-like" by candidate truth-matching; here the removal is by event content, which is the symmetric counterpart of the efficiency numerator (any passing candidate). The two differ by 1 event (283 vs 282 old).
* **Intrinsic nue.** Included once, inside the generic CV (the BNB flux mixture). The nueCC exclusive sample is control only and contributes nothing.
* **Dirt.** Inside the generic CV (rockbox generator); no separate dirt sample and no addition.
* **Cosmics.** CORSIKA cosmics are overlaid in all MC samples; cosmic-matched candidates appear as `COSMIC_OR_UNMATCHED` and are **already in B**.

## 4. Ledger closure

CLOSED: exposure arithmetic, signal/CV rate consistency, no double counting (NC-Delta, nue, dirt), cosmic overlay, numerator definition. **The background category labels are now authoritative** (production-matched truth for all 241,845 old / 241,882 Nov16 candidates, 2026-11-20); the in-region natural-NC-Delta removal rule was checked against it: every selected candidate classified `SIGNAL_NCDELTA` is a natural NC-Delta event, the in-region ones (8 old / 17 Nov16) are exactly the removed events, and the remaining 1 / 2 are outside the provisional box and stay in B by definition (P changes by < 0.01 percentage points either way).
**OPEN (explicit):**
1. **Cosmic-only component.** The CV generator keeps only events with an in-TPC neutrino or a neutrino-induced deposit (`POT_EXPOSURE_AUDIT.md`): there are **no pure-cosmic (no-neutrino) events** in the MC, so the part of the real background that comes from cosmic activity in a beam spill with no neutrino interaction is missing. Beam-off data would supply it, but its scale (gate counters vs trigger counts, livetime, run overlap) is the unanswered blocker G. **Every purity here is therefore an upper bound ("MC-only").** `cosmic_only_headroom.csv` states how large an unknown cosmic-only expectation per 1e20 POT would lower P by 10/25/50 % (old: 119/357/1070 events; Nov16: 288/865/2595 events); the beam-off sample shows 4 (old) / 6 (Nov16) frozen-selection events in 49,970 events, with no approved scale to convert them.
2. **Systematics** (section 6 of the results note): none applied. The CAFs do carry 134 flux/GENIE/FSI weight functions in `recTree` (none detector-related); they are inventoried, not yet used. **`rec.mc.nu.imp_weight` is not 1** (mean ~0.17-0.19) and no event weight is applied; whether `TotalPOT` already accounts for it is undocumented (a normalisation question for the production owners; S/B would move by ~9 % relative if it applied).
3. **Provisional TPC box** as signal region; the analysis FV is not frozen.

Because item 1 is open, results are labelled **"MC-only expected purity (upper bound; statistical errors only)"** everywhere, as the request's rule "no purity result until the ledger closes" cannot be met for the cosmic-only row; all other rows are closed.

## 5. Reuse with the final Round-2 chain

`purity.ScoreSource` names the four score columns and frozen thresholds; `require_frozen` refuses development chains (`dev_models`, `DEV_DO_NOT_DEPLOY`, non-frozen). Nothing else in this document changes when the final scores arrive.
