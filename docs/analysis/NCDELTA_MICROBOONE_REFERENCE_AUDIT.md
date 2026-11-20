# Audit of the MicroBooNE reference material consulted (file-level)

Companion of `MICROBOONE_NCDELTA_DATAMC_PURITY_REFERENCE.md` (procedures). This note is the search record.

| source | path | used for | read |
|---|---|---|---|
| Bogart `cuts.h` | `/exp/uboone/app/users/uboonepro/bbogart/wcp-uboone-bdt/inc/WCPLEEANA/cuts.h` | selection (8899-8915), sideband selections (8936-8979), far/near sideband (8779-8800), truth signal/background flags (2618-2666), weights/EXT scale (261-340), proton 35 MeV (356-375) | yes |
| Bogart `plot_hist.cxx` | `.../apps/plot_hist.cxx` | stack category mapping, EXT/dirt/POT handling | yes (lines 85-130, 940-1075) |
| Bogart `sideband_filter.cxx` | `.../apps/sideband_filter.cxx` | blinding filter levels | yes (1-60) |
| Hagaman 0pNp configs | `/exp/uboone/app/users/lhagaman/LEEana/configurations/0pNp/{cv_input_bnb,file_ch_bnb,cov_input}.txt` | per-file POT, `ext_pot`, dirt/EXT file types, far-sideband-first file list | yes |
| Hagaman BDT notebooks | `/exp/uboone/app/users/lhagaman/bdt_training/numu_plots_technote_v2.ipynb` | BDT-level efficiency/purity, weights, POT scaling | cells 3-12 |
| Yandel | commit history and `bdt.h` already audited; thesis PDF **not fetchable** | scorer (log-odds), XML provenance | previous audits |
| Seokju | `SPINE_SIGNAL_DEFINITION_SOURCE_AUDIT.md` | SPINE truth definitions | previous audit; technote purity/data-MC text **not obtained** |

Searched and **not found**: any file defining an analysis-level single-photon purity; a 1gamma0p/1gammaNp data/MC figure configuration; any slide deck or thesis text of the four authors on EAF (`find` over `/exp/uboone/{app,data}/users/{lhagaman,uboonepro/bbogart}` and the repository). **Action for Avinay:** ask the four for (a) their purity/data-MC definition, (b) the SP data/MC variable list, (c) the SP blinding sequence.
