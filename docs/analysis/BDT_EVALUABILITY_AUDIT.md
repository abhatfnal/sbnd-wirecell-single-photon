# BDT-evaluability audit

Question: the 1000-event smoke test found only ~15–21 % of ordinary CV/data candidates BDT-evaluable (82 % in nueCC). Is that the "main-vertex shower inaccessible" failure of the old 59-event study? That was a hypothesis; this note tests what the data support. **No reconstruction fix, no retuning.** Tables: `tables/bdt_evaluability/bdt_evaluability_by_sample.{csv,json}`; script `scripts/bdt_evaluability_report.py`; all files of each sample.

Definition: a candidate (of a `wc.valid` event) is evaluable iff `shw_sp_filled != 0` and all inputs of all four original MicroBooNE BDTs are finite. Reasons below are mutually exclusive, in the order (1) `shw_sp_filled == 0`, (2) filled but ≥1 non-finite input, (3) evaluable.

## Counts (candidates of `wc.valid` events)

| sample | candidates | (1) `shw_sp_filled == 0` | (2) filled, non-finite input | (3) evaluable | filled0 **and** n20mev == 0 | filled0 and n20mev > 0 | filled and n20mev == 0 |
|---|---|---|---|---|---|---|---|
| bnb_cv | 241,845 | 190,832 (78.9 %) | 44 (0.02 %) | 50,969 (21.1 %) | 188,919 | 1,913 | 0 |
| nuecc | 98,576 | 17,799 (18.1 %) | 43 (0.04 %) | 80,734 (81.9 %) | 17,043 | 756 | 0 |
| beam_off | 4,733 | 3,911 (82.6 %) | 1 | 821 (17.3 %) | 3,833 | 78 | 0 |
| beam_on_open | 42,316 | 33,807 (79.9 %) | 9 (0.02 %) | 8,500 (20.1 %) | 33,357 | 450 | 0 |

## Findings

1. **The dominant reason is `shw_sp_filled == 0`, in every sample.** Non-finite inputs are negligible (≤44 candidates per sample); they are all in the π⁰ block (`kine_pio_angle`, `kine_pio_theta_1/2`). Missing or sentinel *feature families* are not the cause: all inputs exist in all four schemas (verified earlier), and the "sentinel" values cannot be told apart from physical ones in this audit (not examined).
2. **`shw_sp_filled == 0` is almost the same condition as "no shower above 20 MeV".** `filled ⇒ n_20mev_showers > 0` in 100 % of candidates (0 exceptions), and 99.0 % of unfilled CV candidates have `n_20mev_showers == 0` (95.8 % nueCC, 98.0 % beam-off, 98.7 % beam-on). The baseline chain's first cut (`n_20mev > 0`) therefore already removes almost everything that the BDT-evaluability condition removes; the 1–2 % that have n20 > 0 but are unfilled (1,913 in CV) are real losses at the BDT stage and carry no shower classification.
3. Source (`NeutrinoTaggerSinglePhoton.cxx`, PR #543 tree): `shw_sp_filled = 1` is only set inside `mip_identification_sp`, reached for showers attached to the **main vertex** (`map_vertex_to_shower.find(main_vertex)`) whose start segment has PDG 11. So "unfilled" means no electron-type shower is attached to the main vertex.
4. **Is it the old "main-vertex shower inaccessible" mechanism?** Only partly, and it cannot be settled here. Evidence for *physics* rather than inaccessibility: by truth category in CV, the unfilled fraction is 88 % for NUMU_CC and 89 % for OTHER_NC (topologies with no EM shower, expected), but only 19–21 % for NC_PI0, CC_PI0 and NUE_CC (topologies with EM showers). Evidence for *reconstruction loss*: those 19–21 % of EM-shower categories, and 17 % of nueCC `NUE_CC` events, are unfilled although truth has an electron/photon; and a T_kine probe on 200 files shows 83 % (CV) / 86 % (beam-on) of unfilled candidates **do** have an electron-PDG shower row in `T_kine`, i.e. the shower exists in the candidate but is not attached at the main vertex or is below 20 MeV (versus 99 % electron rows for filled candidates; beam-off unfilled candidates mostly have no rows at all, median 0, 41 % electron rows). The mix of "no shower expected", "shower not at main vertex" and "empty candidate" cannot be separated without per-event graph information (`T_pf`, `T_segment`), not done here.
5. Per sample the picture is the same in CV, beam-on (79.9 % unfilled) and beam-off (82.6 %); nueCC is higher (82 % evaluable) because it is an exclusive ν_e-CC production (electron-rich events); the reconstruction was not shown to differ.

## Consequences

- Report "BDT-evaluable fraction" together with `n_20mev_showers > 0`; they are nearly the same cut. The 22 % evaluable fraction in CV is mostly a statement about topology.
- The reconstruction-level losses of interest for a single-photon search are the 1–2 % of candidates with n20 > 0 but unfilled, plus electron-bearing events whose shower is not attached to the main vertex. Quantifying them for **signal** needs the official Gen2 NC-Δ sample.

## Not examined

Which of the 320 inputs carry reconstruction sentinels (e.g. −1, 0, 1e3) among filled candidates; the `T_pf`/`T_segment` graph reason for unattached showers; the PR #543 vs production build difference.
