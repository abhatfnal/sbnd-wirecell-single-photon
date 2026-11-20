# Expected purity of the FROZEN legacy selection: old fg1-era reconstruction vs WCLocal2026Nov16

**Diagnostic. MC-only expected purity = an upper bound (no cosmic-only component; beam-off scale blocked). Statistical uncertainty only. Not a Round-2 result.** The selection is the corrected, source-faithful Round-1 chain, unchanged (numu > 0.4, other > 0.2, ncpi0 > -0.05, nue > -1.0, n20br1 == 1, no analysis FV, candidate policy `any`). No Aurora development BDT was evaluated. Definition and ledger: `NCDELTA_PURITY_DEFINITION_AND_NORMALIZATION.md`. Tables: `tables/ncdelta_purity_datamc/`. Figures: `plots/ncdelta_purity_datamc/` (`A_`...`D_`).

## 1. Headline (final frozen selection, expected yields per 1e20 POT)

| production | efficiency | S | B | **purity P = S/(S+B)** | S/B |
|---|---|---|---|---|---|
| old fg1-era (corrected R1) | **6.70 %** (833 / 12,427) | 29.3 +- 1.0 | 1040.7 +- 61.9 | **2.74 +- 0.18 %** | 0.028 |
| WCLocal2026Nov16 | **15.60 %** (1,938 / 12,427) | 68.3 +- 1.6 | 2526.3 +- 96.4 | **2.63 +- 0.11 %** | 0.027 |

(Errors: weighted Poisson. Efficiencies are the established Round-1 / replay values and are reproduced exactly by this package.)
**Reading:** moving the same frozen selection to Nov16 raises the expected signal by x2.33 and the expected background by x2.43, so the purity is unchanged within errors (2.74 -> 2.63 %). This is the purity counterpart of "background rises too". The absolute value is low because the legacy chain was never tuned for SBND; it should not be read as the Round-2 purity.

## 2. Stage-wise (cumulative; `cumulative_efficiency_purity.csv`, figure A)

| stage | old eff % | old P % | Nov16 eff % | Nov16 P % |
|---|---|---|---|---|
| candidate | 91.18 | 0.046 | 91.18 | 0.046 |
| >0 shower >20 MeV | 65.02 | 0.147 | 63.07 | 0.142 |
| BDT evaluable | 64.65 | 0.152 | 62.43 | 0.148 |
| SP-numu | 39.78 | 0.40 | 51.46 | 0.43 |
| SP-other | 21.86 | 0.69 | 34.52 | 0.73 |
| SP-ncpi0 | 10.50 | 1.36 | 19.74 | 1.58 |
| SP-nue | 7.19 | 2.41 | 16.11 | 2.41 |
| n20br1 (final) | 6.70 | 2.74 | 15.60 | 2.63 |

The purity rises by ~60x over the chain in both productions; the Nov16 chain keeps more signal at every BDT stage with an equal or slightly larger background.

## 3. Reconstructed topology (final selection; `topology_purity.csv`, figure B)

| production | channel | S (/1e20) | B (/1e20) | P % |
|---|---|---|---|---|
| old | 1g0p | 14.4 | 555.3 | 2.52 +- 0.23 |
| old | 1g1p | 13.3 | 342.0 | 3.74 +- 0.42 |
| old | >=2p (diag.) | 1.7 | 143.4 | 1.17 +- 0.25 |
| old | **1gNp** | 15.0 | 485.4 | **2.99 +- 0.29** |
| Nov16 | 1g0p | 39.6 | 1673.2 | 2.31 +- 0.13 |
| Nov16 | 1g1p | 25.5 | 654.6 | 3.75 +- 0.30 |
| Nov16 | >=2p (diag.) | 3.1 | 198.6 | 1.55 +- 0.26 |
| Nov16 | **1gNp** | 28.6 | 853.1 | **3.25 +- 0.23** |

The 1gNp channel is somewhat purer than 1g0p in both productions; no event has a "mixed" reconstructed channel at the final stage. (Reco proton multiplicity, not truth topology.)

## 4. Composition (figure D; production-matched categories at the final selection, per 1e20 POT)

Old: NC pi0 427, outside-TPC 228, CC pi0 221, numu CC 51, other NC 48, cosmic/unmatched 48, ambiguous 11, nue CC 4. Nov16: NC pi0 1162, outside-TPC 721, CC pi0 346, cosmic/unmatched 92, other NC 81, numu CC 55, nue CC 44, ambiguous 18. **Authoritative truth classification of every candidate (added 2026-11-20).** The candidate-associated truth ("light" table: production match `tm_*`, matched interaction, `BM.add_categories`) was run for **all** candidates of both generic-CV productions (old: 241,845 candidates in 37,742 files; Nov16: 241,882 in 37,742 files; `scripts/ncdelta_purity_light_scan_nov16.py run [--production old]`, file coverage and row counts equal the candidate tables exactly; the 50-51 files where no truth object overlaps any candidate originally crashed the association with an empty aggregate and now return `tm_n = 0` = `COSMIC_OR_UNMATCHED`, `background_truth.candidate_association` and a unit test). The stage-wise composition (`background_composition_by_stage.csv`, figure D, control-region tables, data/MC stacks) now uses this classification for both productions; the earlier dominant-neutrino approximation is kept as `cat_approx` and compared with it:

* **The purity, efficiency and topology numbers did not change** (all of `cumulative_efficiency_purity.csv`, `overall_purity.csv`, `topology_purity*.csv`, the single-score scan and the production-matched final composition are bit-identical to the previous commit): purity uses the selected-event counts and the in-region natural-signal removal, which do not depend on the category labels. Data/MC totals per bin are unchanged; only the stack split and the control-region category columns changed.
* Agreement of the approximation with the authoritative classification: candidate level 97.6 % (old) / 97.4 % (Nov16) over all candidates, falling to 93.5 % / 94.7 % at the final stage; event level (background events, per stage) 96.1-97.8 % (old) and 96.5-97.6 % (Nov16). At the final selection the event-level agreement with the production-matched table is 96.5 % (old) / 97.4 % (Nov16). The approximation never produced `MULTI_OR_AMBIGUOUS` (final stage now: old 3 events, Nov16 5) and mislabelled mostly `OTHER_NC` (-6 old / -9 Nov16 events vs authoritative), `NC_PI0` (+4 / +6) and `OUTSIDE_TPC_NU` (-2 / -4).
* Final-selection background events by authoritative category, per 1e20 POT (old / Nov16): NC pi0 426.6 / 1162.0, outside-TPC 228.0 / 720.7, CC pi0 220.6 / 345.7, numu CC 51.5 / 55.2, other NC 47.8 / 80.9, cosmic/unmatched 47.8 / 91.9, ambiguous 11.0 / 18.4, nue CC 3.7 / 44.1, **natural NC-Delta outside the provisional TPC box 3.7 / 7.4** (1 / 2 events, kept in B by definition because the signal denominator is the in-region sample; the 8 / 17 in-region natural NC-Delta events that pass are removed from B). Counting those 1 / 2 events as signal-like would move P by +0.01 percentage points (old 2.743 -> 2.752 %, Nov16 2.631 -> 2.639 %), i.e. nothing.

## 5. Efficiency vs purity per score (figure C, `efficiency_vs_purity_single_score_scan.csv`)

One score varied over [-3, 3] with the other three scores, n20 and n20br1 at their frozen values; stars = frozen operating points. Descriptive only: points with fewer than 10 background events are not drawn and **no threshold is chosen or recommended from the official evaluation samples**. Qualitatively, moving a single legacy threshold by +-0.5 around its frozen value changes the expected purity by only ~0.1-0.7 percentage points (e.g. Nov16 SP-other: 2.23 % at -0.3, 2.63 % at 0.2, 3.08 % at 0.7) while the efficiency changes by up to a factor ~2: the legacy scores trade efficiency for purity slowly, and no single score offers a large purity gain at fixed efficiency.

## 6. Systematics status

**Applied: none.** Every yield uses unit MC weights and every figure is labelled `statistical uncertainty only`.

**Available in the files (inspected 2026-11-20; `systematic_weights_inventory.csv`, `systematic_weights_summary.csv`, `scripts/ncdelta_syst_inventory.py`).** The Nov16 merged CAFs carry the standard SBN systematic-universe weights in `recTree` (`rec.mc.nu.wgt.univ`, one set per `rec.mc.nu` interaction; names, universe counts and types in `globalTree: global/wgts/*`). They are **not** in `recTreeWireCell`, the tree the analysis tables are built from, but the two trees have the same number of entries per file, so the weights can be attached event by event (the interaction-level link is the `mnu_k` index of the truth scan). The dedicated NC-Delta sample and the generic CV carry the **identical** set of 134 weight functions:

| Category | Functions | Universes | Content |
|---|---|---|---|
| flux | 19 | 19,000 | 13 beam hadron-production/focusing families (`expskin`, `horncurrent`, `kplus`, `kminus`, `kzero`, `piplus`, `piminus`, nucleon/pion total/quasi-elastic/inelastic cross-section scalings), 1,000 universes each, plus 6 Geant4 beamline hadron-reinteraction weights (`reinteractions_*`, 1,000 each) |
| cross section / FSI | 115 | 3,485 | 82 `GENIEReWeight_SBN_v1_*` knobs (multisigma and multisim, including CCQE form factors, RPA, resonance, NC/CC DIS, hadronisation and FSI/hA parameters), 4 MINERvA 2p2h, 1 q0q3 2p2h enhancement, 5 misc interaction (C12-to-Ar40 2p2h scaling, nue/numu xsec ratio, SPP low-Q2), 23 NOvA-style non-resonant-pion normalisations |

**Not available:** detector-variation weights (they need separate detector-variation productions, none of which is in these files), dirt normalisation, cosmic normalisation (blocked by the beam-off scale), MC statistics beyond Poisson, and the signal-model radiative branching ratio (forced or natural is not determined). A reweighted covariance has not been built: the weights were inspected, not applied.

**Open normalisation question (not resolved here).** `rec.mc.nu.imp_weight` is not 1: over a random sample of files its mean is 0.185 for the generic CV (954 neutrinos) and 0.169 for the dedicated sample (431 neutrinos); only ~3-5 % of neutrinos have weight 1 (`imp_weight_survey.json`). No event weight was applied anywhere in this package (the exposure normalisation uses `TotalPOT` only), and nothing in the repository documents whether `TotalPOT` already accounts for this weight or whether it must be applied per event. If it had to be applied, absolute rates would change by a large factor, while S/B would move by only ~9 % in relative terms (the two means differ by that much); the question belongs to the production owners and is added to the list of questions in `QUESTIONS_FOR_HAIWANG_HANYU.md`.

## 7. What this does and does not support

Supports: the frozen legacy chain's expected signal/background yields and an *upper-bound* purity, the equal-purity result between productions, the 1gNp vs 1g0p comparison, and the exact reproduction of 6.70 % and 15.60 %. Does not support: a final purity, any S/B with cosmics, any threshold choice, or any Round-2 statement.
