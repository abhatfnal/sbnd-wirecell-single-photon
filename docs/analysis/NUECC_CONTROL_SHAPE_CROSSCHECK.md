# nueCC control sample: unit-area shape cross-check against intrinsic ν_e CC in the BNB CV

**Shapes only.** The official dedicated nueCC sample stays a *control*: it is **not** added to the CV, **no POT normalisation and no rate comparison** is made (`NUECC_CONTROL_SAMPLE.md`). Question: do the BDT-evaluable and selected NUE_CC-like candidates of the nueCC sample look like the intrinsic ν_e CC candidates found inside the ordinary CV? Script `scripts/nuecc_control_shapes.py`; numbers `tables/background_mechanisms/nuecc_control_shape_crosscheck.json`; plots `plots/background_mechanisms/nuecc_control_shapes_{bdt_evaluable,selected_final}.png`. The derived analysis table of the nueCC sample was built with the same code as the CV (`build_analysis_table.py nuecc`, 11,441 files, 0 errors; its counts reproduce the earlier scan exactly: 100,003 events, 99,946 `wc.valid`, 98,576 candidates, 15,886 events passing `any`, reco 0p/1p/≥2p of passing candidates 5,262 / 7,434 / 3,191).

## Definition
NUE_CC-like candidate, **identical in both samples**: the dominant-charge truth neutrino of the candidate (`wc.T_overlap`, derived table `dom_nu*`) is an electron-flavour (|PDG| 12) **CC** interaction with the vertex in the provisional TPC box (not an FV). This does **not** split off π⁰ (the background taxonomy puts CC π⁰ ν_e into CC_PI0 first), so the CV count here is 183 selected candidates instead of the 175 NUE_CC of the taxonomy. The shower-origin results for the CV NUE_CC are in `EXCLUSIVE_BACKGROUND_MECHANISMS.md` §8.

## Populations
| population | CV intrinsic | nueCC control |
|---|---|---|
| BDT-evaluable NUE_CC-like candidates | 1,023 | 78,061 |
| … reco 0p / 1p / ≥2p | 428 / 399 / 196 (42 / 39 / 19 %) | 31,564 / 31,734 / 14,763 (40 / 41 / 19 %) |
| selected (final) NUE_CC-like candidates | 183 | 15,813 |
| … reco 0p / 1p / ≥2p | 57 / 89 / 37 (31 / 49 / 20 %) | 5,218 / 7,411 / 3,184 (33 / 47 / 20 %) |

## Shape comparison (unit area, KS distance D; nothing normalised)
BDT-evaluable candidates: all 17 compared variables have D ≤ 0.044 (BDT numu 0.025, other 0.031, ncpi0 0.036, nue 0.032; main shower energy 0.028, reco E_ν 0.038, reco proton multiplicity 0.014, leading-proton KE 0.029, reco vertex x/y/z 0.018/0.042/0.035, `shw_vtx_dis` 0.012, `shw_min_dis` 0.024, `angle_beam` 0.041, lowest/medium/highest dQ/dx 0.021/0.032/0.044); KS p-values are > 0.04 everywhere (smallest: highest dQ/dx 0.040, reco y 0.058, `angle_beam` 0.066, E_ν 0.097) with 1,023 CV candidates, so differences at the percent level are not resolvable. Selected candidates (183 CV): D ≤ 0.095 for all variables (BDT ncpi0 0.095, p = 0.07; leading-proton KE 0.089, p = 0.26; the rest ≤ 0.075), medians nearly identical (e.g. shower energy 1030 vs 1024 MeV, BDT numu 0.931 vs 0.927, BDT other 0.840 vs 0.863).

**Reading (descriptive):** within the available CV statistics the nueCC control sample reproduces the shapes of the intrinsic ν_e CC candidates, both before and after the frozen cuts, for the BDT scores, shower energy, reco E_ν, proton multiplicity/leading-proton KE, vertex and the shower variables. It therefore behaves as a faithful *shape* surrogate with roughly 75–85× the statistics. This says nothing about its normalisation.

## Caveats
* **Provenance:** the nueCC sample is a Gen2 rare-xsec filtered production with unresolved POT/weighting convention (2,218 (run, subrun) pairs recur in two files; 131 files have `rec.hdr.pot ≠ TotalPOT`; `POT_EXPOSURE_AUDIT.md`). Its neutrino-energy spectrum is whatever the filter keeps and is not weighted; the agreement above shows that the *reconstructed* shapes of the selected population nevertheless match, but a different energy spectrum would only show up if it affected these variables.
* The CV intrinsic ν_e sample is small (183 selected), so only gross shape differences could be excluded; the test is one-sided in that sense.
* NUE_CC-like uses the `T_overlap` dominant-charge association and the provisional box, consistently in both samples; the CV rows are not the same candidates as the `T_match`-based taxonomy (183 vs 175).
* The reco-category fractions agree within a few points; no interpretation of the 0p/1p split beyond that is made here.
