# SP BDTs: WCL1116 full-development summary

Date: 2026-11-20. Branch `round2/sp-bdt-wcl1116-full-development-20261120`, base `92a1b17`. Pre-registered plan:
`SP_BDT_WCL1116_FULL_DEVELOPMENT_PLAN.md` (179cc58).
- Every number is Aurora training-side DEVELOPMENT, on FIT / NESTED VALIDATION / the existing holdout. None is
  independent evaluation.
- **FermiGrid evaluation performance: not used.**
- No model is final. No threshold, weighting or vertex mode is frozen. Xuyang/Matteo's upstream classifiers were not
  retrained.

**The frozen WCL1116 development reference is unchanged:**

| model | split legacy / dev | snap legacy / dev |
|---|---|---|
| numu | 0.958 / 0.976 | 0.954 / 0.974 |
| ncpi0 | 0.849 / 0.899 | 0.847 / 0.897 |
| other | 0.840 / 0.915 | 0.836 / 0.912 |
| nue | 0.918 / 0.959 | 0.914 / 0.952 |

## 1. Nested validation (`nested_v1`)

- **Rule:** the unit is (sample, run, subrun), the unit of the outer split. `sha256("nested_v1|sample|run|subrun")`;
  < 0.20 is NESTED VALIDATION. Only the existing training side is split, and the existing holdout is untouched.
- **Rows (split-move):** FIT / NESTED VALIDATION / holdout:
  - numu: 22,245 / 5,696 / 27,887;
  - ncpi0: 10,799 / 2,718 / 13,610;
  - other: 13,369 / 3,273 / 16,569;
  - nue: 92,480 / 22,962 / 115,679.
- **Leakage:** 0 events shared between any two roles, in every model and mode. Units are identical in both modes.
- EXT units are runs, so only 2 of 29 training-side EXT runs (20 rows) are in nested validation. EXT acceptance is also
  shown on the holdout (224 rows), as a diagnostic.

## 2. Studies

| study | result | verdict |
|---|---|---|
| SP nue weighting (`SP_NUE_WEIGHTING_STUDY.md`) | nested-validation AUC unweighted / 1:4 / 1:1: 0.9624 / 0.9620 / 0.9618 (split-move), 0.9574 / 0.9566 / 0.9558 (snap); weighting re-scales the score (worse Brier) and slightly widens the FIT − validation gap | **WCL1116 DEVELOPMENT WEIGHTING RECOMMENDATION: UNWEIGHTED_BASELINE** |
| SP ncpi0 statistics (`SP_NCPI0_NEGATIVE_STATISTICS_STUDY.md`) | gain per doubling +0.0066 (1.4 sd) / +0.0074 (5.0 sd); the 374 νe CC-sample NC π⁰ rows sit 99.7 % in two-interaction events (BNB 0.02 %) | **CURRENT SAMPLE ADEQUATE** (pre-registered rule); the extra sample is **NOT SOURCE-COMPATIBLE**; the compatible route is the discarded `outncpi0` stream |
| SP numu upstream (`SP_NUMU_UPSTREAM_ROBUSTNESS_STUDY.md`) | full 0.979; without `numu_score` 0.976; without the upstream family 0.976 (snap: 0.975 / 0.973 / 0.972) | mild dependence (−0.0015 to −0.003); the muon-track inputs carry much of it |
| SP other boundary / upstream (`SP_OTHER_BOUNDARY_UPSTREAM_ROBUSTNESS_STUDY.md`) | full 0.916; without the cosmic tagger 0.907; without upstream νμ 0.907; without both 0.890 (snap: 0.912 / 0.904 / 0.904 / 0.888); without both, dirt acceptance doubles; EXT stays about 1 % (holdout) | substantial dependence that partly overlaps; SP other **must** be retrained in the final domain |

## 3. Operating points and the joint selection (`SP_BDT_VALIDATION_OPERATING_POINTS.md`)

In production order, on nested validation (split-move):

| | legacy XMLs at their historical cuts | development models, each at its legacy-equal efficiency |
|---|---|---|
| NC Δ signal efficiency | 27.1 ± 1.2 % | **44.0 ± 1.3 %** |
| BNB background acceptance | 0.75 ± 0.11 % | 0.78 ± 0.11 % |
| 0p / 1p / ≥ 2p | 30.1 / 27.1 / 10.5 % | **51.3 / 39.9 / 26.6 %** |

Snap: 26.4 → 41.2 %. **The retrained set keeps about 1.6× the NC Δ signal at the same BNB background**, with the
largest absolute gain in 0p. No threshold is chosen.

## 4. Vertex modes

| evidence (development only) | split-move vs snap |
|---|---|
| matched-candidate dev AUC, snap − split (92a1b17) | numu −0.0015, ncpi0 −0.0010, other −0.0029, nue −0.0059 |
| nested-validation AUC, every weighting variant (nue) | split-move higher in all three (0.962 vs 0.957) |
| nested-validation AUC, every ablation (numu, other) | split-move higher or equal in all seven |
| joint selection, NC Δ efficiency at the dev ROC-equivalent point | 44.0 % vs 41.2 % (legacy 27.1 % vs 26.4 %) |

**The new studies do not change the qualitative result:** the development evidence favours split-move. **No mode is
frozen**; that is a collaboration decision.

## 5. Feature stability (the 92a1b17 models; `validation/sp_feature_stability_wcl1116.json`, families in `sp_feature_families_wcl1116.csv`)

Family definitions:
- **upstream:** `kind == upstream_score`;
- **cosmic / boundary:** the `cosmic_tagger()` outputs plus `numu_score` and `cosmict_10_score`; `numu_2_score` is
  ambiguous;
- **vertex-sensitive, measured:** the stored value changes between split-move and snap on ≥ 10 % of 77,586 matched
  candidates; 1–10 % is ambiguous.

| model (inputs) | top 5 by gain (split-move) | gain in top 5 / top 10 | top-20 overlap with MicroBooNE (split / snap) | split vs snap: top-20 gain overlap, gain Spearman | gain share: upstream / cosmic-boundary / vertex-sensitive (+ ambiguous) |
|---|---|---|---|---|---|
| numu (73) | `numu_score`, `numu_cc_3_max_muon_length`, `shw_sp_br1_1_vtx_n_segs`, `numu_cc_3_track_length`, `numu_1_score` | 54 % / 73 % | 17 / 18 | 18, 0.97 | 23 % / 18 % / 85 % (+15 %) |
| ncpi0 (45) | `shw_sp_E_indirect_max_energy`, `kine_pio_energy_2`, `shw_sp_pio_1_energy_2`, `kine_pio_mass`, `kine_pio_angle` | 39 % / 61 % | 17 / 16 | 18, 0.85 | 15 % / 0 / 84 % (+16 %) |
| other (146) | `shw_sp_lem_e_charge`, `shw_sp_length_total`, `cosmict_flag`, `shw_sp_E_indirect_max_energy`, `shw_sp_br4_1_shower_total_length` | 38 % / 54 % | 17 / 16 | 19, 0.97 | 10 % / 18 % / 79 % (+21 %) |
| nue (56) | `shw_sp_shw_vtx_dis`, `shw_sp_length_total`, `shw_sp_E_indirect_max_energy`, `shw_sp_n_vertex`, `shw_sp_length_main` | 43 % / 61 % | 15 / 17 | 18, 0.90 | 0 / 0 / 82 % (+18 %) |

- Rankings are stable between vertex modes, and close to the inherited fingerprints.
- **Almost all the gain sits on vertex-sensitive inputs.** This is why the improved vertex mattered, and why every
  model must be retrained in the final reconstruction.
- Cosmic / boundary exposure is concentrated in SP other (18 % of the gain) and in SP numu through `numu_score`.

## 5a. Final-domain rerun (`SP_BDT_FINAL_DOMAIN_RERUN_CONTRACT.md`)

- `config/campaigns/round2_final_reco_candidate.yaml` and `tools/final_domain_campaign.py check / specs / plan`.
- They refuse until every provenance field is supplied:
  - production tag, toolkit commit, exact stamps, DL bundle, vertex mode, effective boundary;
  - upstream fingerprints;
  - the four training lists;
  - the beam-off staging record and verifier hash;
  - a re-approved EXT exception.
- They then regenerate the four frozen specs and the 10-step rerun from existing, tested tools.
- **Ready to consume the new production once its values are supplied.**

## 6. Conclusions

1. **SBND retraining restores background rejection while keeping the recovered signal**, on training-side validation.
   - The joint four-cut selection keeps about 1.6× the NC Δ signal of the inherited XMLs at the same BNB background
     (44.0 vs 27.1 %).
   - The gain is largest in absolute terms for 0p (30 → 51 %) and in relative terms for ≥ 2p.
   - This is the development-domain answer to the question raised by the EAF replay. That replay is context, not
     input.
2. **The remaining design questions are answered for development:**
   - SP nue stays unweighted.
   - SP ncpi0's current negatives are adequate by the pre-registered rule, the νe CC NC π⁰ rows are not
     source-compatible, and the `outncpi0` stream is the compatible route if more are wanted.
   - The SP numu ablations show only mild dependence on the upstream νμ chain.
3. **SP other is the boundary-sensitive model.**
   - Its cosmic-tagger and upstream families each carry about 0.009 AUC and together 0.026; they govern its dirt and
     out-of-FV rejection.
   - It **must be retrained** in the effective-boundary domain, with the beam-off training half reprocessed and
     re-verified.
4. **The final-domain retraining is now a validated rerun.** Provenance gate, frozen specs, training, nested
   validation, operating points, export and Python and C++ equivalence are all in place and tested.
   - Split-move remains the development-preferred vertex mode in every study.
   - Nothing is frozen.
