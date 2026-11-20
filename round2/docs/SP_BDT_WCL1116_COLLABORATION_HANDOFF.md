# SBND single-photon BDTs on WCL1116: collaboration handoff

2026-11-20. Branch `round2/sp-bdt-wcl1116-full-development-20261120`. **DEVELOPMENT results on Aurora training-side
rows. They are not an independent evaluation. No model, threshold or vertex mode is frozen. FermiGrid evaluation
performance was not used.**

## Headline

**The improved vertex reconstruction recovered signal; SBND-specific BDT retraining restores the discrimination.**

## EAF context (context only, not a training input)

The frozen inherited MicroBooNE chain, on the official reconstruction:
- NC Δ efficiency went from **6.70 %** (corrected old reconstruction) to **15.60 %** under WCL1116 (833 → 1938 of
  12427);
- but selected generic-BNB non-signal also rose, from **282 to 685**.

No EAF event, number or selection was used to train, tune or select anything below.

## Aurora answer

The production-order four-BDT cascade (numu → other → ncpi0 → nue), split-move, on nested validation of the training
side:

| | inherited MicroBooNE XMLs | SBND development models |
|---|---:|---:|
| NC Δ signal efficiency | 27.1 ± 1.2 % | **44.0 ± 1.3 %** |
| BNB background acceptance | 0.75 ± 0.11 % | 0.78 ± 0.11 % |

**The retrained four-model chain keeps about 1.6× the NC Δ signal at essentially the same BNB background
acceptance.**
- The development models are each set at their legacy-equal per-model signal efficiency. That is a diagnostic
  operating point, not a chosen cut.
- Snap gives 26.4 → 41.2 %.

## Topology (truth: post-FSI primary protons with KE > 35 MeV)

| | inherited | SBND development |
|---|---:|---:|
| 0p (681 rows) | 30.1 % | **51.2 %** |
| 1p (689 rows) | 27.1 % | **39.9 %** |
| ≥ 2p (124 rows) | 10.5 % | **26.6 %** |

The largest absolute gain is in 0p, where the WCL1116 reconstruction recovers signal.

## Per-model result (existing development holdout, split-move ROC AUC)

| model | inherited XML | SBND development |
|---|---:|---:|
| SP numu | 0.958 | 0.976 |
| SP ncpi0 | 0.848 | 0.899 |
| SP other | 0.840 | 0.915 |
| SP nue | 0.918 | 0.959 |

## Development design conclusions

- **SP nue:** remains unweighted for development. A 1:4 thesis prior and 1:1 balancing do not improve
  nested-validation AUC; they only rescale the score.
- **SP ncpi0:** the current NC π⁰ sample is adequate by the pre-registered rule. The NC π⁰ rows of the νe CC sample are
  not source-compatible: 99.7 % share their spill with a CC νe.
- **SP numu:** only mild direct dependence on the upstream νμ scores (−0.003 AUC without them). The final model still
  needs the collaboration-frozen upstream values.
- **SP other:** strongly sensitive to the cosmic-tagger / boundary and upstream νμ families: −0.009 each, −0.026
  together; they govern its dirt and out-of-FV rejection. It **must** be retrained in the effective-boundary domain,
  with the beam-off training half reprocessed and re-verified.

## Final-domain status

The rerun machinery is ready.
- `config/campaigns/round2_final_reco_candidate.yaml` and `tools/final_domain_campaign.py` refuse to run until every
  provenance field of the next production is supplied.
- They then regenerate the four frozen specs and the ten-step rerun from tested tools: tables, training, nested
  validation, operating points, export, and Python and C++ equivalence.

**No model, threshold or vertex mode is frozen.** Split-move remains the development-preferred mode in every study.

## Figures (`round2/presentation/wcl1116_collab_20261120/`, PNG + PDF)

`joint_selection_legacy_vs_sbnd_dev`, `joint_selection_topology_efficiency`, `four_sp_bdt_auc_legacy_vs_sbnd`,
`joint_selection_cascade`. They are made by `tools/make_wcl1116_collab_figures.py` from the committed validation
JSONs; the plotted values are in `figure_values.json`.

## Technical caveats (kept visible)

1. **Topology extraction bug, fixed before use.** The first truth-topology extraction indexed the flat-CAF proton
   arrays per neutrino instead of through `rec.mc.nu.prim..idx` / `..length`. It was caught by impossible proton
   multiplicities and fixed before any topology result was accepted; the corrected implementation and results are
   authoritative.
2. **Joint grid extended after the first run.** The pre-declared reporting grid used per-model signal-efficiency
   levels ≥ 80 %, which never reached the legacy joint-background region. 0.50 / 0.60 / 0.70 levels were added only to
   widen reporting coverage. The two reference points above do not depend on the grid, and no model or threshold was
   chosen from the extension.
3. **Rounding.** 0p is 349 / 681 = 51.25 %, shown as 51.2 %. The SP ncpi0 legacy AUC is 0.84847, shown as 0.848.
   Earlier reports showed 51.3 % and 0.849, from double rounding; the underlying values are unchanged.
4. No threshold is frozen. 5. No vertex mode is frozen. 6. No model is final. 7. FermiGrid evaluation performance has
   not been used.

Details: `SP_BDT_FULL_DEVELOPMENT_SUMMARY.md` (summary), `SP_BDT_VALIDATION_OPERATING_POINTS.md` (cascade),
`SP_BDT_FINAL_DOMAIN_RERUN_CONTRACT.md` (rerun).
