# NC-Delta -> N gamma data/MC plan and first results (frozen legacy chain)

Code: `src/sbnd_single_photon/{datamc,regions,datapolicy,purity}.py`, `scripts/ncdelta_datamc.py`; policy `configs/data_policy.yaml`; tables `tables/ncdelta_purity_datamc/control_region_composition_{old_fg1,nov16}.csv`; plots `plots/ncdelta_purity_datamc/datamc_<production>_<region>_<topology>.png` (2 productions x 6 regions x 3 topologies = 36). **Statistical uncertainty only.**

## 1. Data policy (enforced in code)

No collaboration-approved SBND unblinding procedure for this analysis exists in the repository. The gate (`datapolicy.check`) encodes the conservative reading and raises on violation:

| sample | may be shown at | note |
|---|---|---|
| `beam_on_open` (runs 18255/18259, 4.62e18 POT, designated open) | **preselection, sidebands** | signal region (final frozen selection) **blocked** until `signal_region.approved_by` AND `approved_date` are filled by a named person AND the stage kind is listed (two locks) |
| `run3bnb` (Nov16 only) | nothing | not designated open anywhere in the repository |
| `beam_off` | every stage, **counts only** (control tables; not drawn on the plots yet) | never stacked; scale blocked (blocker G) |

Consequence: the final-selection panels show MC only ("data not shown (policy)"). One caveat on history: an earlier shape-only note (`DATA_MC_SHAPES.md`) already displayed area-normalised beam-on shapes of the final selection (77 events); no policy existed at the time, and it should not be reused without approval.

## 2. Control / sideband regions (SBND analogues, source-defined, nothing tuned)

Definitions are the MicroBooNE single-photon sequential inversions (`cuts.h:8936-8979`, 'eff' thresholds) on the source-faithful log-odds scale; the MicroBooNE 5-250 cm X cut is dropped (no SBND FV). Contamination = S/(S+B) at equal exposure from the dedicated signal sample.

| region | definition | dominant MC (Nov16 / old) | signal contamination (Nov16 / old) | data exposure | purpose |
|---|---|---|---|---|---|
| `preselection` | candidate in a valid event, >0 showers above 20 MeV, BDT evaluable | numu CC (32 % / 34 %) | 0.15 % / 0.15 % | 4.62e18 POT, 8,321 / 8,480 events | loose-SP shapes, reco-vs-data sanity |
| `SB_numu` (numuCC-rich) | SP-numu < 0.1 (>-20) | numu CC (44 % / 44 %) | 0.03 % / 0.07 % | 5,871 / 6,301 | muon-like / numuCC modelling |
| `SB_other` | numu > 0.1, SP-other < -0.4 | outside-TPC (40 % / 37 %) | 0.15 % / 0.19 % | 1,262 / 1,271 | out-of-volume / dirt-like |
| `SB_ncpi0` (NCpi0-rich) | numu > 0.1, other > -0.4, SP-ncpi0 < -0.4 | NC pi0 (60 % / 55 %) | 0.22 % / 0.32 % | 755 / 585 | NC pi0 modelling |
| `SB_nue` | ... ncpi0 > -0.4, SP-nue < -3.0, n20br1 == 1 | nue CC (79 % / 72 %) | 0.11 % / 0.26 % | 63 / 55 | intrinsic nue |
| cosmic / beam-off control | beam-off data counts in each region, plus the MC cosmic-matched fraction | n/a | n/a | beam-off 872 / 820 events at preselection (no scale) | cosmic shape; **normalisation blocked** |
| `final_frozen` | all four scores above frozen cuts, n20br1 == 1 | NC pi0 (45 % / 40 %) | 2.6 % / 2.7 % | **blocked** | signal region |

None of these becomes an official control region by appearing here: they are proposals for Avinay's approval, and none was chosen by looking at signal-region data.

## 3. What the first data/MC comparison shows (open data, statistics only; counts from the control tables)

| region (inclusive) | Nov16 data / MC | old data / MC |
|---|---|---|
| preselection | 8,321 / 8,547 (0.97) | 8,480 / 8,622 (0.98) |
| SB_numu | 5,871 / 5,799 (1.01) | 6,301 / 6,294 (1.00) |
| SB_other | 1,262 / 1,227 (1.03) | 1,271 / 1,206 (1.05) |
| **SB_ncpi0** | **755 / 1,020 (0.74)** | **585 / 766 (0.76)** |
| SB_nue | 63 / 68.7 (0.92) | 55 / 55.4 (0.99) |

* Preselection, numuCC-rich, other-rich and nue-rich regions agree within a few percent (about 1.5-3 sigma data statistics where applicable), in both productions.
* **The NC pi0-rich sideband shows a ~25 % MC excess over the data in both productions** (event-level Data/MC 0.764 old / 0.740 Nov16; data statistical error ~3 %, MC statistical error ~1.5 %). **Update 2026-11-21:** with the available flux + GENIE + FSI + beamline-G4 covariance (`NCDELTA_SYSTEMATIC_WEIGHTS_FIRST_PASS.md` section 7: total relative uncertainty ~21 %, S and B coherent) the deficit is only **-1.5 sigma (old) / -1.7 sigma (Nov16)**, rate-only chi2/ndof 1.3/1 and 1.5/1, and the shower-energy shape is consistent (rate+shape 6.0/8 and 8.4/8, shape-only 6.0/7 and 9.7/7). The deficit is flat in energy and the systematic covariance is almost a pure normalisation mode, so the rate result is a statement about the normalisation uncertainty of the NC pi0 prediction; the missing cosmic-only component would make the prediction larger, not smaller, and detector/dirt/POT/signal-model/`imp_weight` and unresolved-owner events are not in that covariance. **The reco topology split is not consistent**: Data/MC is 0.91 / 0.85 for 1g0p but 0.61 / 0.64 for 1gNp, a shape-only tension p = 5e-4 (old) / 7e-3 (Nov16) that the available systematics do not reproduce; proton-reconstruction/detector modelling is the first thing to examine. MicroBooNE treats NC pi0 as a data-constrained background; the same is indicated here.
* **Flash time:** open data populate 1.7-2.2 us where the MC beam window ends at ~1.7 us (known offset, `FLASH_TIME_CONVENTION_AUDIT.md`, unresolved); it affects only that variable.
* Variables shown: selected-shower energy, shower angle to beam, shower-to-vertex distance, reco vertex x/y/z (the (0,0,0) no-vertex sentinel is masked), reco neutrino energy, reco proton multiplicity, leading-proton KE, matched flash time, the four SP-BDT scores, minimum shower distance to other objects. The set follows the common observables of `NCDELTA_COMMON_RECO_OBSERVABLES.md` and the MicroBooNE stack variables (shower energy, angle to beam, reco Enu, vertex, scores). **Not yet shown** (not in the derived table; needs the pair-level CAF read): pi0-sensitive kinematics (pair mass, opening angle, asymmetry), shower dE/dx and conversion gap, track-level numu/cosmic quantities beyond flash time/PE.

## 4. Remaining blockers and TODO

1. **Beam-off scale** (blocker G, question to Haiwang/Hanyu already filed in `QUESTIONS_FOR_HAIWANG_HANYU.md`): needed for the cosmic-only component of every stack and for a closed purity.
2. **Signal-region approval** (named approver): required before any final-selection beam-on plot.
3. **Systematics.** First pass done for the FINAL selection only (`NCDELTA_SYSTEMATIC_WEIGHTS_FIRST_PASS.md`): the weights (134 functions, 22,485 universes per interaction, in `recTree`, not `recTreeWireCell`) are attached event by event through an explicit run/subrun/event join (identity proof: every file read has identical ids in identical order in both trees), the owner interaction being the production-matched `mnu_k` (background) or the signal interaction (signal); events with no unique owner are not varied and are reported. Still to do: (a) extend the attachment to the preselection and the four sidebands (volume: ~35k background events in SB_numu alone; accumulate per-universe bin yields on the fly instead of storing blocks) and therefore a data/MC band for the NC pi0 sideband excess; (b) detector variations (separate productions needed); (c) cosmic normalisation (blocked by the beam-off scale), dirt, POT, the NC-Delta signal-model systematics (the multisim `RDecBR1gamma` dial moves the signal by 45 %, `ThetaDelta2NRad` by up to 19 % in 1gNp: both shown separately, not in the generic neutrino band), MC statistics beyond Poisson; (d) the treatment of the unresolved-owner events (cosmic/ambiguous, 4-6 % of the final-selection background) is open; (e) `imp_weight` (not 1; convention question to Haiwang/Hanyu).
4. Pair-level pi0 observables and dE/dx variables (CAF read).
5. ~~Candidate-level truth association for ALL candidates of the Nov16 and old CVs~~ **DONE 2026-11-20** (old 241,845 and Nov16 241,882 candidates; stage-wise composition, control-region tables and data/MC stacks now use it; the dominant-neutrino approximation agrees with it for 93.5-97.8 % depending on level/stage, see the results note section 4; purity unchanged).
6. Run the same package on Round-2 frozen scores: provide a `purity.ScoreSource` + frozen thresholds (see section 5).

## 5. Final-BDT hook

```python
from sbnd_single_photon import purity as PU
src = PU.ScoreSource("round2_final_frozen", {"numu": "r2_score_numu", "other": "r2_score_other", "ncpi0": "r2_score_ncpi0", "nue": "r2_score_nue"},
                     {"numu": ..., "other": ..., "ncpi0": ..., "nue": ...}, frozen=True, provenance="<commit / XML hashes / freeze date>")
masks = PU.stage_masks(candidates, src)          # drives purity, topology, sidebands (regions.region_mask(score=...)), data/MC
```
Add the four score columns to the candidate tables with the same builder, pass the source, rerun `ncdelta_purity_tables.py` / `ncdelta_datamc.py` (they currently hard-wire the legacy source: change one argument). A development chain is refused by `require_frozen`.
