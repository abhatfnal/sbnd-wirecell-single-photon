# MicroBooNE references for purity and data/MC: what the source files establish, and what SBND must adapt

Read on 2026-11-20 from the files on EAF (no memory summaries). **What was and was not available matters for how far this can be trusted**, so it is stated first.

## 0. What was actually read (and what was not)

| person | what exists on EAF and was read | what was NOT found / obtained |
|---|---|---|
| **Ben Bogart** | `/exp/uboone/app/users/uboonepro/bbogart/wcp-uboone-bdt/` (the `wcp-uboone-bdt` tree already used as the frozen-BDT reference): `inc/WCPLEEANA/cuts.h` (selection, sidebands, truth flags, weights, EXT scaling), `apps/plot_hist.cxx` (stack categories, EXT, dirt, POT scaling), `apps/sideband_filter.cxx` (filter levels), `config.txt` | no write-up of an analysis-level purity definition |
| **Lee Hagaman** | `/exp/uboone/app/users/lhagaman/`: `LEEana/configurations/0pNp/*` (input lists with per-file POT, `ext_pot`, dirt and EXT file types, weight names), `bdt_training/numu_plots_technote_v2.ipynb` (efficiency/purity of a BDT, weights, POT scaling) | no slides / thesis text; no 1gamma0p/1gammaNp *data/MC figure* configuration found (the 0pNp configs are the nue 0p/Np channels) |
| **Erin Yandel** | authorship of the single-photon BDT code (`bdt.h`, commit history already audited in `NUMU_TRAINING_DOMAIN_SOURCE_AUDIT.md`); the thesis numbers carried in `YANDEL_THESIS_FROZEN_XML_COMPATIBILITY_AUDIT.md` | the thesis PDF itself could not be fetched; her thesis' purity / data-MC conventions were therefore **not read** |
| **Seokju** | already audited: `SPINE_SIGNAL_DEFINITION_SOURCE_AUDIT.md` (medulla fork `seokjuchung/medulla`), `NCDELTA_COMMON_RECO_OBSERVABLES.md` | the NC-Delta technote's purity / data-MC section was not obtainable here |

**Consequence:** the procedures below come from MicroBooNE **code and configuration**, not from the people's written conventions. Where a definition (notably "analysis purity") is not in any file, it is marked *not established by source* and SBND's own definition is stated in `NCDELTA_PURITY_DEFINITION_AND_NORMALIZATION.md`. Please confirm with the four of them where marked.

## 1. Source-established procedure

| topic | what the source says | where |
|---|---|---|
| **single-photon selection** | `shw_sp_n_20mev_showers>0`, reco vertex X in (5,250) cm, `single_photon_numu_score>0.4`, `other>0.2`, `ncpi0>-0.05`, `nue>-1.0`, `shw_sp_n_20br1_showers==1`. Looser **'eff'** selection: 0.1, -0.4, -0.4, -3.0 | `cuts.h:8899-8915` |
| **BDT sidebands** | the sidebands ARE the sequential inversions at the 'eff' thresholds: numu-rich `numu<0.1` (>-20); other-rich `numu>0.1 & other<-0.4`; NCpi0-rich `numu>0.1 & other>-0.4 & ncpi0<-0.4`; nue-rich `... & ncpi0>-0.4 & nue<-3.0 & n20br1==1`; lower bound -20 removes sentinel scores | `cuts.h:8936-8979` |
| **signal categories (truth)** | `SPNCDeltaSig`, `SPNCPi0Sig`, `SPNCOtherSig`, `SPNumuCCSig`, `SPOutFVSig`, all requiring `match_completeness_energy>0.1*truth_energyInside`, `truth_single_photon==1`; NC-Delta: `truth_isCC==0 && truth_NCDelta==1 && truth_vtxInside==1` (with `...NoFV` variants) | `cuts.h:2618-2650` |
| **background categories** | everything that is not a signal category: `SPnumuCCBkg` (numuCC in FV, no pi0), `SPnumuCCpi0Bkg`, `SPNCBkg` (NC, no pi0), `SPNCpi0Bkg`, `nueCCinFV`, `SPoutFVBkg` (vertex outside FV), `SPdirtBkg`, plus `ext` and `badmatch` | `cuts.h:2653-2666`, `plot_hist.cxx:1020-1075` |
| **MC weight** | `weight_cv * weight_spline` (+ beam/EXT time-dependent scale per run period, `ext_rej`) | `cuts.h:261-340` |
| **cosmic / beam-off** | EXTBNB is a **separate data file type with its own `ext_pot`** (Run-1 1.7758e20, Run-3 3.03121e20) and is stacked as `ext` ("data-driven cosmic") | `0pNp/cv_input_bnb.txt`, `plot_hist.cxx:1060` |
| **dirt** | a separate DIRT MC file type, with a 0.5 normalisation uncertainty column | `0pNp/cv_input_bnb.txt` and `cov_input.txt` |
| **POT normalisation** | each file carries its POT; MC is scaled to the data POT; `numu_plots_technote_v2` scales validation MC to 5e19 | `cv_input*.txt`, `bdt_training/numu_plots_technote_v2.ipynb` |
| **blinding order** | far sideband data first (`checkout_data_bnb_run*_far_sideband_*`), then a few-1e19 sample (`..._5e19`, `..._1e19`), then full; `sideband_filter` has levels: 1 numuCC, 2 far sideband, 3 far+near, 4 far+near+signal region | `0pNp/file_ch_bnb.txt`, `apps/sideband_filter.cxx:42-48` |
| **0p / Np** | channels `*_fc_0p` / `*_fc_Np` in the nue analysis; the truth proton threshold used in the pi0 reweighting is **35 MeV KE** (matches SBND's established truth convention) | `0pNp/cov_input.txt`, `cuts.h:356-375` |
| **BDT-level purity** | in the BDT validation notebooks, "purity" = weighted fraction of signal among events above a score cut on a *validation set*, plotted against signal efficiency | `numu_plots_technote_v2.ipynb` cells 10-12 |

## 2. Not established by any file read

* an **analysis-level definition of single-photon expected purity** (no `purity` in `plot_hist.cxx`, `cuts.h`, or the LEEana configs);
* which variables the single-photon data/MC figures show (the machinery is generic; variable lists in the configs are nue-oriented: reco Enu, vertex);
* 1gamma0p vs 1gammaNp presentation for the single-photon analysis (only the nue 0p/Np channels exist in the configs read);
* whether single-photon signal-region data were blinded and how (the generic far-sideband-first order exists for the nue analysis).

## 3. What must be adapted for SBND (not copied)

| MicroBooNE | SBND adaptation | why |
|---|---|---|
| reco X in (5,250) cm | **dropped**; no analysis FV exists (provisional TPC box only for truth/categories) | MicroBooNE geometry; FV decision is open (`FIDUCIAL_VOLUME_DECISION_AUDIT.md`) |
| numu/other/ncpi0/nue sideband thresholds (eff) | kept **unchanged** on the same log-odds scale (source-faithful scorer) | frozen legacy chain; not retuned |
| EXT stacked with `ext_pot` scale | **not stacked**: beam-off scale unresolved (blocker G); beam-off shown as shape only | `DATA_EXPOSURE_NORMALIZATION.md` |
| separate dirt MC | **no separate sample**: dirt/rock interactions are inside the generic CV (rockbox generator) and appear as OUTSIDE_TPC | `POT_EXPOSURE_AUDIT.md` |
| `weight_cv*weight_spline`, beam/EXT scale | **unit MC weight** only; no GENIE/flux reweighting applied | no validated SBND weights wired in |
| signal by `truth_NCDelta` flag | signal = **dedicated NC-Delta sample** + GENIE-record ancestry (Delta0/Delta+ mother of a status-1 photon) for the natural events in the CV | SBND has the dedicated sample |
| far sideband first | SBND analogue: open data at preselection/sidebands only; signal region blocked until a named approval (`configs/data_policy.yaml`) | no SBND blinding procedure written yet |
