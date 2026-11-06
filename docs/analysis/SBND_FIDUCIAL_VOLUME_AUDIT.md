# SBND fiducial-volume / active-volume / containment audit (read-only; NO FV is applied in the baseline)

Method: read-only search of CVMFS (`sbnana v10_14_02_01`, `sbncode v10_31_00`, `sbndcode v10_26_00`) and of analysis checkouts under `/exp/sbnd/app/users/*`, done by a delegated search agent. Entries #2, #4 and the ICARUS default of `InFV` (#5/#7) were re-checked by hand against the files; the other rows are as reported by the search and have not each been re-read. CVMFS items are release tarballs (no commit hash); git checkouts carry hashes below. Units cm, x = drift. Strict inequalities.

**Finding: there is no single production-used SBND FV.** Every definition belongs to a specific analysis and they conflict.

| # | type | boundaries | source | context |
|---|---|---|---|---|
| 1 | active volume | \|x\|<200, \|y\|<200, 0<z<500 (`avnd`) | sbnana v10_14_02_01 `SBNAna/Cuts/VolumeDefinitions.h` L32 (comment: April 2020) | CAFAna plotting |
| 2 | FV | 1.5<\|x\|<175, \|y\|<175, 30<z<450 (`fvndAbs`) | same file L23; `kFiducialVolumeND` | legacy nue (2020) |
| 3 | containment | track end \|x\|<190, \|y\|<190, 10<z<490 (`fvndExit`) | same file L37; `NumuCutsSBND202106.cxx` | numu SBND 2021 |
| 4 | FV | x∈(-189.15,189.15), y∈(-190,190), z∈(10,450) | `NumuCutsSBND202106.cxx` L10-12 `kInFV` | numu CC 2021 |
| 5 | FV | x,y∈(-190,190), z∈(10,450) | mharriso/cafpyana `makedf/util.py` `InFV(det="SBND")` (ad2bc21a, 2025-10-30) | nueCC, cc2p |
| 6 | cut-AV | \|x\|<195, \|y\|<195, 5<z<495 | cafpyana `makedf/util.py` `InAV` | helper |
| 7 | FV | 10<\|x\|<190, \|y\|<190, 10<z<450 | mharriso/cafpyana `pyanalib/cc2p_reco_var.py` L32 | cc2p |
| 8 | containment | start & end \|x\|<190, \|y\|<190, 10<z<490 | same file `InFV_trk` | cc2p |
| 9 | FV | 10<\|x\|<190, 10<z<450; z<250: \|y\|<190, z>250: -190<y<100 | `analysis_village/cohpi/makedf/make_cohpidf_v2.py` | coherent π |
| 10 | FV | boxes x±200 (margin 10), y -200..200 (z<250) / -200..100 (z>250), margins inx=iny=inzfront=10, inzback=50 | `analysis_village/gump/gump_cuts.py` | gump |
| 11 | FV | \|x\|,\|y\|<190, 10<z<490 | syebes/sbnd-lambda-preselection `cuts.py` (049ffc56, 2026-05-14) | lambda |
| 12 | containment | PFP end \|x\|,\|y\|<195, 5<z<495 | same, `pfp_exits_tpc` | lambda |
| 13 | FV | SPINE `is_fiducial`: ~25 cm x,y; 30 upstream / 50 downstream z (from a code comment only) plus an extra carve-out | spine_anaplot_tools `cafana/include/cuts.h` (0de2c4fb, 2025-03-09) | SPINE muon2024 |
| 14 | containment | within 5 cm of edges (SPINE `is_contained`) | same | SPINE |
| 15 | truth FV | margins 10 (x,y,z-min), 100 (z-max) | sbncode v10_31_00 `CAFMaker/FillTrue.cxx` L920-927 | fake-reco truth |
| 16/17 | FV | inset 10 (z-max 50) / 15 (z-max 50) as fcl parameters | sbncode `run_numueff.fcl`, `run_vertexcharge_sbnd.fcl` | numu eff, vertex charge |
| 18 | generation box | -210..210, -210..210, -10..510 | sbndcode `set_genie_tpc.fcl` | generator, NOT an analysis cut |

Nominal active volume from the geometry (sbndcode v10_26_00 `sbnd_v02_06_base.gdml`, `boxTPCActive`) is about \|x\|<201, \|y\|<204, 0<z<501 (derived from gdml constants, not a runtime dump); the round ±200/0–500 box is used as the AV by #1 and by `truth.ActiveVolume`.

## Conflicts / caveats
- z upper edge: 450 (#2,4,5,7,9), 490 (#3,8,11), 495 (#6,12). z lower edge: 5, 10 or 30. x,y edge: 175, 190, 195.
- x is applied either as \|x\| with a cathode exclusion (#2,7,9) or as a plain interval (#4,5,11).
- #9 and #10 both carve out high-y at z>250; #13's carve-out has x>210, outside the ±200 AV, so it looks ICARUS-like; its 25/50/30 numbers rest on a comment.
- `1mu1p0pi/makedf/makedf.py` calls `InFV(df.vertex, 50)` without `det=`; the default is `det="ICARUS"`: do not reuse blindly.
- The sbnana 2020 values predate the current geometry.
- Not searched: sbnd_data, sbnalg, cafanacore, sbnutil, sbnobj, many other user areas (a recursive grep of the cafpyana trees timed out). Absence of a hit is not evidence of absence. The SinglePhotonAnalysis `fiducial_volume.h` is referenced but absent from the install.
- All these are cuts on RECONSTRUCTED or TRUE vertices of other reconstructions. None was designed for the Wire-Cell `kine_nu_*_corr` vertex.

## Recommendation (NOT a decision)
1. Apply **no FV** in the baseline (unchanged). Report the baseline cut-flow with the vertex-position distribution (`wc.T_kine.kine_nu_{x,y,z}_corr`) so any FV can be applied later as an extra cut.
2. When one is needed, candidates that are at least maintained by current analyses are #5 (cafpyana SBND `InFV`, x,y ±190, z 10–450) and #4/#7 variants; the choice among them is a physics decision (z-max 450 vs 490 and the high-y carve-out matter for a single-photon selection), not an engineering one. Do not mix an SBND box with the MicroBooNE x-FV.
3. For the truth taxonomy, the provisional ±200 / 0–500 box stays *taxonomy only*.

## To confirm with Haiwang / Hanyu
- Is there an SBND-collaboration-approved FV for Wire-Cell-reconstructed vertices, and is it applied to `kine_nu_*_corr` (SCE-corrected) or the raw vertex?
- Should the baseline FV include the high-y/z>250 exclusion?
- Is a cathode (|x|≈0) exclusion wanted, given that the Wire-Cell candidates are built per drift volume?

Checkout hashes: spine_anaplot_tools 0de2c4fb…, mharriso/cafpyana ad2bc21a…, bharris/cafpyana eb1376ab… (2026-05-05, same `util.py`), syebes/sbnd-lambda-preselection 049ffc56…
