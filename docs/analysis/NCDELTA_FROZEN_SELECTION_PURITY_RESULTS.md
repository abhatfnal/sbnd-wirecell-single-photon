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

Old: NC pi0 427, outside-TPC 228, CC pi0 221, numu CC 51, other NC 48, cosmic/unmatched 48, ambiguous 11, nue CC 4. Nov16: NC pi0 1162, outside-TPC 721, CC pi0 346, cosmic/unmatched 92, other NC 81, numu CC 55, nue CC 44, ambiguous 18. The stage-wise composition uses a dominant-neutrino taxonomy computed from stored candidate columns; it agrees with the production-matched category in **96.5 % (old) / 97.4 % (Nov16)** of the final-selection background events (`taxonomy_validation.csv`).

## 5. Efficiency vs purity per score (figure C, `efficiency_vs_purity_single_score_scan.csv`)

One score varied over [-3, 3] with the other three scores, n20 and n20br1 at their frozen values; stars = frozen operating points. Descriptive only: points with fewer than 10 background events are not drawn and **no threshold is chosen or recommended from the official evaluation samples**. Qualitatively, moving a single legacy threshold by +-0.5 around its frozen value changes the expected purity by only ~0.1-0.7 percentage points (e.g. Nov16 SP-other: 2.23 % at -0.3, 2.63 % at 0.2, 3.08 % at 0.7) while the efficiency changes by up to a factor ~2: the legacy scores trade efficiency for purity slowly, and no single score offers a large purity gain at fixed efficiency.

## 6. Systematics status

Available: none applied. Unit MC weights; no GENIE, flux, G4 or detector reweighting. The signal flatCAF was produced with `cafmakerjob_sbnd_sce_systtools_and_fluxwgt_and_g4rw.fcl` (SAM metadata), i.e. systematic-weight branches *may* be present, but they were **not inspected** in the Wire-Cell merged CAFs (needs XRootD; see TODO). Missing: flux, cross section, FSI/G4, detector, cosmic normalisation (blocked by the beam-off scale), dirt normalisation (dirt is inside the CV with no independent handle), POT, MC statistics beyond Poisson, signal-model (radiative branching ratio: forced or natural is not determined). Every figure is labelled `statistical uncertainty only`.

## 7. What this does and does not support

Supports: the frozen legacy chain's expected signal/background yields and an *upper-bound* purity, the equal-purity result between productions, the 1gNp vs 1g0p comparison, and the exact reproduction of 6.70 % and 15.60 %. Does not support: a final purity, any S/B with cosmics, any threshold choice, or any Round-2 statement.
