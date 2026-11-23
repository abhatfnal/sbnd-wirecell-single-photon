# NC Δ → N γ: collaboration-presentation handoff (Aurora side)

**For a separate Presentation Claude** building Avinay's SBND collaboration-meeting slides on the exclusive NC Δ → N γ
single-photon analysis. It is combined with the separate EAF purity / data-MC handoff (branch
`analysis/ncdelta-purity-datamc-20261120`).

Written 2026-11-23 on Aurora. Every number below was checked against a committed file named in the source column or
the asset table; no new analysis was run.

Authoritative branches (all pushed to `origin`):

| layer | branch | head | key report |
|---|---|---|---|
| A. scorer correction (9.28 → 6.70 %) | `analysis/ncdelta-source-faithful-legacy-scorer-20261117`; slide assets on `analysis/ncdelta-corrected-presentation-20261117` | `daf9544` (contained in the replay branch) | `docs/analysis/LEGACY_SCORER_CORRECTION_IMPACT.md` |
| B. WCL1116 replay (6.70 → 15.60 %) | `analysis/wcl1116-nov16-frozen-r1-replay-20261118` | `409f382` | `docs/analysis/WCL1116_NOV16_FROZEN_R1_SELECTION_REPLAY.md` |
| C. SBND retraining (27.1 → 44.0 %) | `round2/sp-bdt-wcl1116-full-development-20261120` | `bfac596` | `round2/docs/SP_BDT_FULL_DEVELOPMENT_SUMMARY.md` |

---

# Executive story

**One sentence:** *improved vertexing recovers the NC Δ signal; SBND-specific BDT retraining restores the
discrimination.*

Three layers, each answering a different question. **They are not three successive steps on one denominator.**

1. **Layer A: source-faithful correction (analysis fix, not reconstruction).**
   - The historical first-look 9.28 % used the wrong reading of the inherited MicroBooNE TMVA score: the cuts were
     applied to the raw response `v`.
   - The MicroBooNE code cuts on `s = log10((1+v)/(1-v))`, with `v` the TMVA `EvaluateMVA` response, no clamping.
     Restoring that, and `kine_pio_flag = 0` in the legacy ncpi0 input, gives the authoritative old-reconstruction
     baseline: **833 / 12,427 = 6.70 %**.
2. **Layer B: improved WCL1116 reconstruction, same frozen selection.**
   - The corrected inherited chain, replayed unchanged on Haiwang's WCLocal2026Nov16 reconstruction with Snehadri's
     DL vertex: **6.70 % → 15.60 %** (×2.33). The median vertex distance falls from 18.9 to 1.5 cm.
   - But selected generic-BNB non-signal rises **282 → 685** (×2.43).
   - **The reconstruction recovers the signal, but the inherited classifiers also admit more background.**
3. **Layer C: SBND-specific retraining (Aurora development).**
   - On Aurora training-side nested validation, the four retrained SP BDTs in production order keep **44.0 %** of the
     NC Δ signal rows where the inherited XMLs keep **27.1 %**, at essentially the same BNB background acceptance
     (**0.78 % vs 0.75 %**): about **1.6×** the signal.
   - The gain is in every proton topology, largest in absolute terms for 0p.
   - This is **development**, not final Round-2 performance.

**Status:** the BDT development study is complete. The final retraining waits for the final reconstruction domain
(effective boundary), the collaboration-frozen upstream νμ outputs, and the beam-off training half reprocessed in that
domain. No model, threshold or vertex mode is frozen. The retrained models have **not** been evaluated on FermiGrid.

---

# Exact numerical results

## Layer A: scorer correction (official Gen2 NC Δ sample; truth denominator 12,427, provisional TPC box)

| configuration | selected | efficiency | role |
|---|---:|---:|---|
| A: as run (cuts on raw `v`) | 1,153 / 12,427 | **9.28 %** | **HISTORICAL AS-RUN, never the baseline** |
| B: score convention only | 831 | 6.69 % | decomposition |
| C: `kine_pio_flag` only | 1,161 | 9.34 % | decomposition |
| D: full source-faithful | **833 / 12,427** | **6.70 %** (68 % interval 6.48–6.94 %) | **authoritative corrected Round-1 baseline** |

- Frozen cuts (score space): numu > 0.4, other > 0.2, ncpi0 > −0.05, nue > −1.0. In response space these are
  v > 0.4305 / 0.2263 / −0.0575 / −0.8182, so **as run, the nue cut was vacuous**.
- Change: −320 events, −2.58 points (−27.7 % relative). Almost all of it is the score convention; `kine_pio_flag` alone
  is +8 events.
- Generic BNB-CV: selected events 649 → 291; selected non-signal 635 → **282**. The intrinsic νe CC category among the
  selected non-signal goes 175 → 1.
- Corrected baseline by truth topology: 0p 373 / 5,863 = 6.36 %; 1p 416 / 5,557 = 7.49 %; ≥ 2p 44 / 1,007 = 4.37 %.
- Source: `docs/analysis/LEGACY_SCORER_CORRECTION_IMPACT.md`, `tables/legacy_scorer_correction/impact_configurations.csv`.

## Layer B: same corrected frozen selection, old vs WCLocal2026Nov16 (official sample; same 12,427 denominator)

| | old (fg1-era), corrected R1 | WCL1116 (Nov16, `recTreeWireCell` = split-move) |
|---|---:|---:|
| **NC Δ efficiency** | 833 = **6.70 %** (6.48–6.94) | 1,938 = **15.60 %** (15.27–15.93) |
| truth 0p (N = 5,863) | 373 = 6.36 % | 1,071 = **18.27 %** |
| truth 1p (N = 5,557) | 416 = 7.49 % | 794 = **14.29 %** |
| truth ≥ 2p (N = 1,007) | 44 = 4.37 % | 73 = **7.25 %** |
| Δ0 / Δ+ (descriptive; Δ charge is not proton topology) | 5.76 / 7.87 % | 15.83 / 15.30 % |
| median nearest reco → true vertex distance (all) | **18.89 cm** | **1.55 cm** |
| … truth 0p / truth 1p | 29.3 / 5.9 cm | 11.9 / 0.8 cm |
| fraction of events within 5 cm | 33 % | 65 % (0p 12 → 36 %; 1p 49 → 88 %) |
| **generic BNB-CV selected non-signal** | **282** | **685** (×2.43) |
| … reco 1γ0p / 1γ1p / ≥ 2p | 150 / 93 / 39 | 453 / 178 / 54 |
| … NC π⁰ / outside-TPC ν / CC π⁰ / νe CC | 116 / 62 / 60 / 1 | 316 / 196 / 94 / 12 |
| … cosmic-unmatched / other NC / νμ CC / ambiguous | 13 / 13 / 14 / 3 | 25 / 22 / 15 / 5 |

Signal factor ×2.33, background factor ×2.43.

**Cumulative signal cutflow, old → Nov16** (of 12,427):

| stage | old → Nov16 |
|---|---|
| candidate | 11,331 → 11,331 |
| > 20 MeV shower | 8,080 → 7,838 |
| BDT-evaluable | 8,034 → 7,758 |
| numu | 4,943 → 6,395 |
| other | 2,717 → 4,290 |
| ncpi0 | 1,305 → 2,453 |
| nue | 893 → 2,002 |
| `n_20br1` / final | 833 → 1,938 |

- The reconstruction ceiling does not improve (candidates are identical; the shower ceiling is slightly lower). **The
  gain appears at the BDT stages**, which is why retraining is the next step.
- Matched signal migration: pass → pass 628; fail → pass 1,310; **pass → fail 205**.
- Attribution: **vertex + other reconstruction changes**, not vertex-only. The toolkit, wire-cell-data, DL bundle and
  schema all differ; step 1 is identical.
- Source: `docs/analysis/WCL1116_NOV16_FROZEN_R1_SELECTION_REPLAY.md` §§1, 5–8, `tables/wcl1116_nov16_replay/*.csv`.

## Layer C: SBND development retraining (Aurora, training side)

**Definitions (essential).**
- **Sample:** the Aurora WCL1116 *training* productions, split-move tree (`recTreeWireCell`): the NC Δ training sample
  (Gen2 configL NC Δ-radiative, generated on Aurora; **not** the official 12,427 sample), the generic BNB, the νe CC
  sample and the 558-file beam-off training half.
- **Rows:** preselected candidate rows: a non-placeholder candidate with ≥ 1 shower > 20 MeV and a readable label.
- **Signal:** the inclusive single-photon signal class of the candidate's truth-matched partner neutrino (thesis
  definition, shared by all four BDTs), in the NC Δ sample.
- **Partition:** NESTED VALIDATION. A deterministic 20 % split, unit (sample, run, subrun), of the training side,
  never used to fit the models it evaluates.
- **Cascade:** the four BDT cuts in production order numu → other → ncpi0 → nue. **No `n_20br1` cut.**
- **Operating point:** each SBND model sits at the threshold that gives its legacy-equal per-model signal efficiency
  on its own validation classes. This is a ROC-equivalent diagnostic; **it is not a chosen cut**.

**Headline (split-move):**

| | inherited MicroBooNE XMLs at historical cuts | SBND development models |
|---|---:|---:|
| **NC Δ signal efficiency** | 405 / 1,494 = **27.1 ± 1.2 %** | 657 / 1,494 = **44.0 ± 1.3 %** |
| **BNB background acceptance** | 48 / 6,424 = **0.75 ± 0.11 %** | 50 / 6,424 = **0.78 ± 0.11 %** |
| truth 0p (681 rows) | 205 = 30.1 % | 349 = **51.2 %** (51.25 %) |
| truth 1p (689 rows) | 187 = 27.1 % | 275 = **39.9 %** |
| truth ≥ 2p (124 rows) | 13 = 10.5 % | 33 = **26.6 %** |
| νe CC-sample νe CC background acceptance (21,079 rows) | 1.08 % | 0.93 % |

- Uncertainties are binomial on the validation rows. The background difference, 0.03 ± 0.15 points, is consistent with
  zero.
- **About 1.6× the NC Δ signal (44.0 / 27.1 = 1.62) at essentially the same BNB background acceptance.**
- Snap: legacy 26.4 % → SBND 41.2 % at 0.65 % → 0.68 %.

**Cascade, cumulative, split-move** (NC Δ signal efficiency / BNB background acceptance after each cut):

| after | inherited | SBND development |
|---|---|---|
| numu | 85.8 % / 25.4 % | 87.2 % / 18.6 % |
| other | 56.9 % / 9.3 % | 62.5 % / **2.7 %** |
| ncpi0 | 33.3 % / 1.7 % | 46.1 % / 1.0 % |
| nue | **27.1 % / 0.75 %** | **44.0 % / 0.78 %** |

**Per-model ROC AUC** (existing outer development holdout, odd subruns; each model's own signal vs background class):

| model | inherited XML split / snap | SBND development split / snap | gain (split) |
|---|---|---|---:|
| SP numu | 0.958 / 0.954 | **0.976** / 0.974 | +0.018 |
| SP ncpi0 | **0.848** / 0.847 | **0.899** / 0.897 | +0.051 |
| SP other | 0.840 / 0.836 | **0.915** / 0.912 | +0.076 |
| SP nue | 0.918 / 0.914 | **0.959** / 0.952 | +0.041 |

SP ncpi0 legacy is exactly 0.84847, so **0.848**; not 0.849.

**Development design conclusions (nested validation, split-move):**
- **SP nue:** unweighted preferred. AUC unweighted 0.9624 / 4 : 1 thesis prior 0.9620 / balanced 0.9618. Weighting
  only rescales the score, and the Brier score worsens (0.034 → 0.040 → 0.068).
- **SP ncpi0:** the current sample is adequate under the pre-registered rule. The learning curve gains +0.0066 per
  doubling but is not resolved at the required 3 σ in split-move.
  - The 374 extra NC π⁰ rows of the νe CC sample are **not source-compatible**: 99.7 % share their spill with a CC νe,
    against 0.02 % in BNB.
  - The compatible route, if more statistics are wanted, is the `outncpi0` stream of the same official Gen2 filter.
- **SP numu:** only mild dependence on the upstream νμ scores. Removing `numu_score` or the upstream family costs about
  0.0015–0.003 AUC. It must still be retrained on the collaboration-frozen upstream outputs.
- **SP other:** the strongest boundary / upstream sensitivity. Full model 0.916; without the cosmic-tagger family
  0.907; without the upstream νμ family 0.907; without both 0.890, which doubles dirt acceptance. It **must** be
  retrained in the final effective-boundary domain.

**Vertex mode:** split-move is **development-preferred** in every study: joint efficiency 44.0 % vs 41.2 %; matched AUC
snap − split numu −0.0015, ncpi0 −0.0010, other −0.0029, nue −0.0059. **No vertex mode is frozen.**

Sources:
- `round2/validation/sp_operating_points_dv2_split_move.json`, `round2/presentation/wcl1116_collab_20261120/figure_values.json`;
- `round2/validation/wcl1116_mode_compare_<model>.json`, `round2/validation/wcl1116_full_dev_<model>_<mode>.json`;
- `round2/docs/SP_BDT_FULL_DEVELOPMENT_SUMMARY.md`, `SP_BDT_VALIDATION_OPERATING_POINTS.md`.

---

# Plot inventory

**Paths.**
- Paths on `round2/sp-bdt-wcl1116-full-development-20261120` are in the working tree at
  `/lus/flare/projects/neutrinoGPU/abhat/sbnd/sbnd-wirecell-single-photon/`.
- Figures on other branches can be extracted without checking them out:
  `git show origin/<branch>:<path> > <file>.png`.

**COLOUR WARNING: the two figure sets use opposite colour meanings.**
- Replay / scorer figures (Okabe-Ito): **blue `#0072B2` = OLD reconstruction**, vermillion `#D55E00` = WCL1116 (Nov16).
- Aurora retraining figures: **orange `#eb6834` = inherited MicroBooNE XMLs**, **blue `#2a78d6` = SBND development
  models**.

So blue means "old" on the replay slides and "new SBND" on the retraining slides. Every slide must keep its legend
visible; never put a figure from each set side by side without legends.

## joint_selection_legacy_vs_sbnd_dev

Path: `round2/presentation/wcl1116_collab_20261120/joint_selection_legacy_vs_sbnd_dev.png` (1800×920 px, aspect 1.96);
PDF `…/joint_selection_legacy_vs_sbnd_dev.pdf`. Branch `round2/sp-bdt-wcl1116-full-development-20261120`.

Use: **MAIN** (the strongest single retraining result).

What it shows:
- two panels with **independent y-axes**: left, NC Δ signal efficiency (0–60 %); right, BNB background acceptance
  (0–1.2 %);
- inherited (orange) vs SBND development (blue), with binomial error bars;
- banner "Aurora nested validation — DEVELOPMENT ONLY"; headline "1.6× the NC Δ signal at essentially the same BNB
  background"; footnote "not an independent evaluation; no threshold, model or vertex mode frozen; FermiGrid evaluation
  not used".

Exact values: 27.1 ± 1.2 % → 44.0 ± 1.3 % signal; 0.75 ± 0.11 % → 0.78 ± 0.11 % BNB acceptance.

Suggested slide title: **SBND retraining keeps ~1.6× more NC Δ signal at the same BNB background**

Suggested caption: "Four SP BDTs in production order (numu → other → ncpi0 → nue), Aurora WCL1116 training-side nested
validation, split-move. SBND models at their legacy-equal per-model signal efficiency; no threshold frozen. DEVELOPMENT
ONLY."

Suggested speaker message: "On training-side validation rows, with the four classifiers applied in production order,
the inherited MicroBooNE XMLs keep 27 % of the NC Δ signal. The SBND-retrained models keep 44 %, while the BNB
background acceptance stays at three-quarters of a percent within the validation statistics. That is about 1.6 times
the signal at essentially the same background. This is a development result on the training side, with no threshold
frozen; the independent FermiGrid evaluation comes after the final reconstruction."

Required caveats: DEVELOPMENT ONLY; nested validation, not independent evaluation; per-candidate-row rates; the two
panels have separate axes; not comparable to 15.60 % (see "What not to say").

## joint_selection_topology_efficiency

Path: `round2/presentation/wcl1116_collab_20261120/joint_selection_topology_efficiency.png` (1680×920 px, 1.83); PDF
alongside.

Use: **MAIN** if there are ≥ 5 Aurora/replay slides; otherwise a strong **BACKUP** or a right-hand inset next to the
joint figure.

What it shows: grouped bars per truth topology (post-FSI primary protons, KE > 35 MeV), inherited vs SBND, with
binomial errors and row counts under each group.

Exact values (validation rows):

| topology | inherited | SBND |
|---|---|---|
| 0p | 205 / 681 = 30.1 % | 349 / 681 = **51.2 %** |
| 1p | 187 / 689 = 27.1 % | 275 / 689 = **39.9 %** |
| ≥ 2p | 13 / 124 = 10.5 % | 33 / 124 = **26.6 %** |

Suggested slide title: **The retraining gain holds in every exclusive topology**

Suggested caption: "NC Δ signal efficiency of the four-BDT cascade by truth proton multiplicity (post-FSI primary
protons > 35 MeV). Aurora nested validation, split-move. DEVELOPMENT ONLY."

Suggested speaker message: "Split by the true number of protons above 35 MeV, the retrained chain gains in every
topology. 0p, where the improved vertexing recovered the most signal, goes from 30 to 51 %. 1p goes from 27 to 40 %.
≥ 2p, the smallest sample, goes from 11 to 27 %."

Required caveats: ≥ 2p has only 124 rows (±4 points); these are row-level efficiencies of preselected candidates, not
the 5,863 / 5,557 / 1,007 truth denominators of the replay; DEVELOPMENT ONLY.

## four_sp_bdt_auc_legacy_vs_sbnd

Path: `round2/presentation/wcl1116_collab_20261120/four_sp_bdt_auc_legacy_vs_sbnd.png` (1680×880 px, 1.91); PDF
alongside.

Use: **BACKUP**, or a small inset on the retraining slide.

What it shows: a dot plot per model of the inherited-XML AUC (orange) → SBND development AUC (blue), with the gain
printed at the right; banner "Aurora existing development holdout — DEVELOPMENT ONLY".

Exact values: numu 0.958 → 0.976 (+0.018); ncpi0 0.848 → 0.899 (+0.051); other 0.840 → 0.915 (+0.076); nue 0.918 →
0.959 (+0.041).

Suggested slide title: **All four SP classifiers improve with SBND retraining**

Suggested caption: "ROC AUC of each SP BDT on its own signal vs background classes, Aurora existing development
holdout (odd subruns), split-move. DEVELOPMENT ONLY."

Suggested speaker message: "The gain is not one classifier carrying the others: each of the four BDTs improves. SP
other, which separates out-of-fiducial, dirt, cosmic and beam-off backgrounds, gains the most."

Required caveats: an AUC is a ranking metric, not an efficiency; each model is evaluated on its own class rows; this
holdout is the outer development holdout, a different partition from the nested validation of the joint figure.

## joint_selection_cascade

Path: `round2/presentation/wcl1116_collab_20261120/joint_selection_cascade.png` (1920×920 px, 2.09); PDF alongside.

Use: **BACKUP** for a general collaboration talk; OPTIONAL main slide for an expert audience.

What it shows: two aligned panels over the production-order steps (after numu / other / ncpi0 / nue). Left: NC Δ signal
efficiency, linear. Right: BNB background acceptance, **log scale**. Inherited vs SBND.

Exact values: see the cascade table above (inherited 85.8 / 25.4 → 56.9 / 9.3 → 33.3 / 1.7 → 27.1 / 0.75; SBND
87.2 / 18.6 → 62.5 / 2.7 → 46.1 / 1.0 → 44.0 / 0.78).

Suggested slide title: **Where the rejection is recovered: SP other and SP ncpi0**

Suggested caption: "Cumulative NC Δ signal efficiency and BNB background acceptance after each SP BDT in production
order. Aurora nested validation, split-move. DEVELOPMENT ONLY."

Suggested speaker message: "Step by step, the retrained SP other is where most of the background is removed: after it,
the background is 2.7 % instead of 9.3 % while more signal is kept. SP ncpi0 then keeps 46 % of the signal against
33 % for the inherited model. By the last cut both chains sit at the same background, and the retrained one keeps far
more signal."

Required caveats: the right panel is log-scale; cumulative values; DEVELOPMENT ONLY.

## fig_topology_efficiency_old_vs_nov16 (replay)

Path: `plots/wcl1116_nov16_replay/fig_topology_efficiency_old_vs_nov16.png` on `analysis/wcl1116-nov16-frozen-r1-replay-20261118`
(927×491 px, 1.89; PNG only). Extract:
`git show origin/analysis/wcl1116-nov16-frozen-r1-replay-20261118:plots/wcl1116_nov16_replay/fig_topology_efficiency_old_vs_nov16.png > fig_topology_efficiency_old_vs_nov16.png`.

Use: **MAIN** (the Layer B slide).

What it shows: final efficiency with exact binomial 68 % intervals for all / truth 0p / 1p / ≥ 2p / Δ0 / Δ+
(descriptive), old fg1-era (blue) vs WCLocal2026Nov16 (vermillion), with values printed. Footer "DIAGNOSTIC: frozen
Round-1 selection replayed on WCLocal2026Nov16; not a Round-2 result".

Exact values: all 6.70 → 15.60; 0p 6.36 → 18.27; 1p 7.49 → 14.29; ≥ 2p 4.37 → 7.25; Δ0 5.76 → 15.83; Δ+ 7.87 → 15.30 %.

Suggested slide title: **Improved vertexing recovers NC Δ signal: 6.7 % → 15.6 % with the same frozen selection**

Suggested caption: "Official Gen2 NC Δ sample, truth denominator 12,427. The corrected Round-1 selection is applied
unchanged to the old and the WCLocal2026Nov16 reconstruction. DIAGNOSTIC."

Suggested speaker message: "With nothing in the selection changed, the dedicated NC Δ efficiency goes from 6.7 to
15.6 %, a factor 2.3. It gains in every topology, and 0p now has the highest efficiency."

Required caveats: diagnostic, not Round 2; vertex plus other reconstruction changes, not vertex-only; Δ charge is not
proton topology.

## fig_vertex_distance_old_vs_nov16 (replay)

Path: `plots/wcl1116_nov16_replay/fig_vertex_distance_old_vs_nov16.png` (same branch; 1409×570 px, 2.47).

Use: **OPTIONAL** on the Layer B slide (a thin strip), else BACKUP.

What it shows: distributions of the nearest reco → true vertex distance (log x, 0.1–300 cm) in three panels (all,
truth 0p, truth 1p); old (blue) vs Nov16 (vermillion), with N and medians in the legends. There is no ≥ 2p panel.

Exact values: all median 18.9 → 1.5 cm (N 11,306 / 11,309); 0p 29.3 → 11.9 cm; 1p 5.9 → 0.8 cm; within 5 cm 33 → 65 %.

Suggested slide title (if standalone): **The DL vertex moves the candidate vertex onto the true vertex**

Suggested caption: "Nearest candidate vertex to the true neutrino vertex, official NC Δ sample. DIAGNOSTIC."

Suggested speaker message: "The median distance from the nearest candidate vertex to the true vertex drops from about
19 cm to 1.5 cm; the fraction within 5 cm doubles, from a third to two thirds."

Required caveats: evaluation diagnostic (truth used only for evaluation). The y-axis label overlaps the footer at the
lower left; crop or shrink if needed.

## fig_bnb_background_old_vs_nov16 (replay)

Path: `plots/wcl1116_nov16_replay/fig_bnb_background_old_vs_nov16.png` (same branch; 958×500 px, 1.92).

Use: **MAIN** (the "but the background rises" slide).

What it shows: selected generic-BNB-CV non-signal events by candidate-associated truth category, old (blue) vs Nov16
(vermillion), with counts printed.

Exact values: CC π⁰ 60 → 94; cosmic / unmatched 13 → 25; multi / ambiguous 3 → 5; NC π⁰ 116 → 316; νe CC 1 → 12; νμ CC
14 → 15; other NC 13 → 22; outside-TPC ν 62 → 196. Total 282 → 685.

Suggested slide title: **But the inherited classifiers also admit more background: 282 → 685 selected BNB non-signal**

Suggested caption: "Generic BNB CV (FermiGrid), same frozen selection, selected non-signal events by truth category.
DIAGNOSTIC; counts, no purity."

Suggested speaker message: "The same selection that accepts 2.3 times more signal accepts 2.4 times more generic-BNB
non-signal, mostly NC π⁰ and outside-TPC neutrinos. The inherited MicroBooNE classifiers are seeing a shifted input
domain, and that is the argument for retraining them for SBND."

Required caveats: these are counts; no purity or S/B is defined here (that belongs to the EAF purity handoff); outside-
TPC and boundary-sensitive categories can change with the effective-boundary production.

## fig_cutflow_old_vs_nov16 (replay)

Path: `plots/wcl1116_nov16_replay/fig_cutflow_old_vs_nov16.png` (same branch; 933×537 px, 1.74).

Use: **BACKUP** (Q&A: "where does the gain come from?").

What it shows: the cumulative signal cutflow as % of 12,427, old vs Nov16, with counts on the bars.

Exact values: see the Layer B cutflow table.

Suggested slide title: **The gain appears at the BDT stages, not in the reconstruction ceiling**

Suggested caption: "Cumulative signal cutflow, frozen selection, any-candidate policy. DIAGNOSTIC."

Suggested speaker message: "The candidates are identical and the shower ceiling is slightly lower; the jump starts at
SP numu and continues through every BDT."

Required caveats: diagnostic.

## fig_sp_scores_old_vs_nov16 (replay)

Path: `plots/wcl1116_nov16_replay/fig_sp_scores_old_vs_nov16.png` (same branch; 1679×449 px, 3.74: a very wide strip).

Use: **BACKUP**.

What it shows: the four frozen SP-score distributions of signal events (maximum over candidates), old vs Nov16, with
identical binning, **clipped at ±3** (overflow piles up at the edges), and the cuts dashed.

Exact values: median matched-candidate shifts numu +0.29, other +0.09, ncpi0 +0.03, nue +0.04 (score units;
`tables/wcl1116_nov16_replay/signal_score_migration.csv`).

Suggested slide title: **The inherited SP scores shift in the new reconstruction**

Suggested caption: "Frozen SP BDT scores of NC Δ signal, old vs WCLocal2026Nov16, clipped at ±3. DIAGNOSTIC."

Suggested speaker message: "The frozen classifiers' scores move: their inputs changed, so they evaluate a domain they
were not trained in."

Required caveats: clipping at ±3 explains the edge spikes; this is a signal-only view.

## B01_scorer_correction (Layer A)

Path: `presentation_assets/ncdelta_source_faithful/backup/B01_scorer_correction.png` on
`analysis/ncdelta-corrected-presentation-20261117` (1153×711 px, 1.62; PNG only). Extract:
`git show origin/analysis/ncdelta-corrected-presentation-20261117:presentation_assets/ncdelta_source_faithful/backup/B01_scorer_correction.png > B01_scorer_correction.png`.

Use: **MAIN** for the Layer A slide.

What it shows: four bars of NC Δ selected events (of 12,427) for configurations A as run (grey) / B score convention
only / C `kine_pio_flag` only / D full source-faithful, with counts and percentages printed. Footer: "score =
log10((1+v)/(1−v)), v = TMVA response | kine_pio_flag forced to 0 in the single-photon ncpi0 input | thresholds
unchanged".

Exact values: 1,153 (9.28 %) / 831 (6.69 %) / 1,161 (9.34 %) / 833 (6.70 %).

Suggested slide title: **Why the baseline changed: 9.28 % was not the source-faithful scorer**

Suggested caption: "Official Gen2 NC Δ sample, denominator 12,427. Same XMLs, thresholds and selection; only the score
convention (and the legacy ncpi0 `kine_pio_flag`) changes."

Suggested speaker message: "Our first-look 9.28 % applied the MicroBooNE cuts to the raw TMVA response. The MicroBooNE
code cuts on log10 of (1+v) over (1−v), and with that the as-run nue cut, which removed nothing, becomes a real cut.
The authoritative corrected baseline is 833 of 12,427, 6.70 %. This is an analysis correction, not a reconstruction
loss."

Required caveats: label 9.28 % HISTORICAL everywhere it appears; the correction comes from a source-code audit, and no
stored MicroBooNE scores were compared.

## Other available figures (not recommended for the main talk)

| figure | path (branch) | use |
|---|---|---|
| corrected cutflow / loss budget | `plots/legacy_scorer_correction/baseline_consolidation_source_faithful/fig_cutflow_loss_budget.png` (replay and scorer branches; 1505×648) | BACKUP for Layer A |
| corrected signal vs background rates | `…/baseline_consolidation_source_faithful/fig_signal_vs_background_rates.png` (998×621) | BACKUP; rates, **not** purity |
| differential efficiencies (photon energy, angle, vertex, conversion distance, proton KE) | `plots/legacy_scorer_correction/differential_efficiency_source_faithful/*.png` | BACKUP / Q&A only |
| source-faithful Round-1 deck assets | `presentation_assets/ncdelta_source_faithful/*.png` and `backup/B02–B13` (`analysis/ncdelta-corrected-presentation-20261117`) | Round-1 baseline detail; BACKUP |

**Not available, so do not invent:**
- a ≥ 2p panel of the vertex-distance figure;
- a figure of the replay BNB background by reco channel (the numbers are in the Layer B table);
- any FermiGrid evaluation of the retrained models;
- any purity / S/B figure on the Aurora side (that is the EAF handoff).

**Not existing as a figure; build it if wanted:** the three-number "9.28 → 6.70 → 15.60, what changed?" box graphic
(specification in `docs/presentation/WIRECELL_20261119_5SLIDE_UPDATE_HANDOFF.md`, slide 1, replay branch).

---

# Recommended slide sequence

| # | title | figure | key numbers | Use |
|---|---|---|---|---|
| A | **Why the baseline changed: 9.28 % was not the source-faithful scorer** | `B01_scorer_correction.png` | 9.28 % (historical) → 6.70 % = 833 / 12,427 | MAIN (can merge into B as a one-line box) |
| B | **Improved vertexing recovers NC Δ signal** | `fig_topology_efficiency_old_vs_nov16.png` (+ optional strip `fig_vertex_distance_old_vs_nov16.png`) | 6.70 → 15.60 % (×2.33); vertex 18.9 → 1.5 cm | MAIN |
| C | **But the inherited classifiers also admit more background** | `fig_bnb_background_old_vs_nov16.png` | 282 → 685 (×2.43); NC π⁰ 116 → 316, outside-TPC 62 → 196 | MAIN |
| D | **SBND-specific retraining restores rejection** | `joint_selection_legacy_vs_sbnd_dev.png` | 27.1 → 44.0 % at 0.75 → 0.78 % BNB | MAIN |
| E | **Exclusive topology gains** | `joint_selection_topology_efficiency.png` (+ optional AUC inset) | 0p 30.1 → 51.2; 1p 27.1 → 39.9; ≥ 2p 10.5 → 26.6 % | MAIN or BACKUP |
| F | **Next: the final reconstruction domain** | none (text / simple arrow) | dependency chain below | MAIN (short) |

Then hand over to the EAF purity / data-MC slides. Backups: `four_sp_bdt_auc_legacy_vs_sbnd`, `joint_selection_cascade`,
`fig_cutflow_old_vs_nov16`, `fig_sp_scores_old_vs_nov16`, the design-conclusions table and the technical caveats.

**Alternatives:**
- **Tight slot (3 slides):**
  1. A + B as one "three numbers" slide (9.28 historical → 6.70 → 15.60) with the replay topology figure;
  2. C;
  3. D with E as an inset.
- **Expert audience:** add `joint_selection_cascade` after D (where the rejection is recovered) and the AUC dot plot.
- Put a clear **transition line** between C and D: *"Vertexing recovers the signal; retraining restores
  discrimination."* State on D that the sample and denominator change (Aurora training-side validation rows, not the
  12,427 official sample).

---

# What not to say

**Never compare these directly:**

| do not compare | why |
|---|---|
| **15.60 % with 44.0 %** (or "15.6 % → 44 %") | Different questions, samples and denominators. 15.60 % is the official Gen2 NC Δ sample, whole frozen chain including the pre-BDT stages and `n_20br1`, over all 12,427 truth events. 44.0 % is Aurora training-side preselected candidate rows (already past the > 20 MeV-shower stage), four BDT cuts only, nested validation. They are not sequential efficiencies. |
| **27.1 % with 6.70 % or 15.60 %** | 27.1 % is the inherited chain on Aurora validation rows *after* preselection and without `n_20br1`; 6.70 / 15.60 % are fractions of the full truth denominator on the official sample. |
| **0.75 / 0.78 % with 282 / 685** | An acceptance of preselected BNB candidate rows on Aurora, against a count of selected events in the 500k-event FermiGrid BNB CV. |
| **Aurora topology (30.1 → 51.2 % 0p) with replay topology (6.36 → 18.27 % 0p)** | Different denominators: 681 validation rows vs 5,863 truth events; different stages. |
| **"×1.6" with "×2.33" (as ×3.8 overall)** | They do not multiply: different samples and stages. |
| **an AUC with an efficiency** | An AUC ranks a model on its own classes; it is not a selection efficiency. |
| **the nested-validation joint numbers with the outer-holdout AUCs** | Different partitions (nested validation vs existing holdout). |
| **9.28 % with anything** | It is historical; never show it without the HISTORICAL label, and never as "improved from 9.28 %". |
| **replay colours with Aurora colours** | Blue = old (replay) vs blue = SBND (Aurora); keep the legends. |

**Never say:**
- "Our final efficiency is 44 %" or "Round-2 efficiency is 44 % / 15.6 %."
- "The new BDTs have been validated on FermiGrid" (they have not been evaluated there).
- "Split-move is final" (say *split-move is development-preferred*).
- "The background is unchanged" (say *essentially the same BNB background acceptance, within the nested-validation
  statistical precision*: 0.75 ± 0.11 vs 0.78 ± 0.11 %).
- "Efficiency improved from 9.28 % to 15.6 %."
- "The vertexer alone doubles the efficiency" (replay attribution: vertex + other reconstruction changes).
- "Purity improved" or any S/B from the Aurora numbers.
- "SP other is not trained" (outdated: it is trained, 0.840 → 0.915).
- "0p 51.3 %" or "ncpi0 legacy 0.849": double-rounded; use 51.2 % and 0.848.

---

# Final-domain dependency chain

We are **not** waiting on the BDT development study: it is complete. We are waiting on the **final reconstruction
domain**:

1. Haiwang / Snehadri's **effective (non-box) boundary production**. Per the collaboration context supplied with this
   request, it is expected around the 2 cm interior-boundary convention. It changes the cosmic-tagger and containment
   inputs, which are 60 of SP other's 146 inputs.
2. The **collaboration-frozen upstream νμ outputs** (Xuyang / Matteo; `numu_score`, `numu_1_score`), needed by SP numu
   and SP other.
3. The **beam-off odd-run TRAINING half reprocessed** in that same final domain and **re-verified** with the same strict
   staging verifier (membership, checksums, exact version stamps).

Then:

```text
final reconstruction
  -> rebuild the training tables
  -> retrain all four SP BDTs (frozen specs; development choice: SP nue unweighted)
  -> nested validation
  -> choose and freeze thresholds on validation only
  -> Python + C++ (TMVA::Reader / TmvaGradForest) equivalence
  -> freeze model / vertex mode / thresholds
  -> ONE independent FermiGrid evaluation
  -> rerun the EAF purity / data-MC package
```

The rerun machinery already exists and is tested:
- `round2/config/campaigns/round2_final_reco_candidate.yaml` and `round2/tools/final_domain_campaign.py`;
- it refuses to run until every provenance field is supplied (`round2/docs/SP_BDT_FINAL_DOMAIN_RERUN_CONTRACT.md`).

---

# Aurora vs EAF/FermiGrid firewall

- **Aurora = development / training.** Every Layer C number comes from Aurora training-side tables: FIT, NESTED
  VALIDATION or the existing development holdout.
- **FermiGrid official samples = independent evaluation.** Layers A and B used them only with the frozen inherited
  chain; nothing was trained or tuned on them.
- The retrained WCL1116 models have **not** been evaluated on the official FermiGrid evaluation sample.
- **No final threshold, no final model, no final vertex mode is frozen.**
- No Aurora development result may be called final Round-2 performance.
- The EAF replay results were context only; they were never inputs to the Aurora training or model choices.

---

# Backup technical details

- **Topology indexing bug, fixed before use.** The first flat-CAF truth-proton extraction indexed the per-event flat
  arrays per neutrino. It was caught because it produced impossible multiplicities: at most one proton per neutrino,
  even in BNB. It was fixed (`rec.mc.nu.prim..idx` / `..length` offsets) before any topology result was accepted. The
  corrected NC Δ split is 47.5 % 0p / 44.2 % 1p / 8.3 % ≥ 2p; Δ+ is mostly 1p, Δ0 mostly 0p. The corrected values are
  authoritative.
- **Joint-grid extension.** The pre-registered reporting grid used per-model signal-efficiency levels ≥ 80 %, which did
  not reach the legacy-background region. 0.50 / 0.60 / 0.70 levels were added after the first run, solely to widen
  reporting coverage. The two reference points of the main figure (legacy at historical cuts; SBND at legacy-equal
  per-model efficiency) do not depend on the grid, and no model or threshold was chosen from it.
- **Rounding corrections.** 0p = 349 / 681 = 51.25 % → **51.2 %** (not 51.3 %); SP ncpi0 legacy AUC = 0.84847 →
  **0.848** (not 0.849). The earlier values were double-rounded; nothing underlying changed.
- **Pre-registration.** The nested split, weighting variants, ablation families and recommendation rules were committed
  (`179cc58`) before any variant was fitted.
- **Statistics.** The joint BNB acceptance rests on about 50 accepted rows (±0.11 points). EXT beam-off appears in nested
  validation with only 20 rows; its acceptance is quoted on the existing holdout instead (SBND about 1 % vs legacy 5.4 %).
- **Exporter.** All eight development models (4 × 2 vertex modes) pass the Python and C++ equivalence checks:
  TMVA::Reader == toolkit `TmvaGradForest`, bit-identical; 0 decision flips.
- **Per-model ROC-equivalent points** (outer holdout, split-move; legacy at its cut → SBND background at equal signal
  efficiency):
  - numu 82.4 % / 6.27 % → 2.91 %;
  - ncpi0 51.7 % / 10.4 % → 5.0 %;
  - other 57.4 % / 11.4 % → 3.28 %;
  - nue 78.4 % / 13.4 % → 5.4 %.

---

## COPY/PASTE FACT SHEET

Every number the presentation may put on slides, with its mandatory label.

**Layer A — scorer correction (official Gen2 NC Δ, denominator 12,427)**
- HISTORICAL as-run: 1,153 / 12,427 = 9.28 % (wrong score convention; never the baseline)
- Corrected (authoritative) old-reconstruction baseline: 833 / 12,427 = 6.70 % (68 %: 6.48–6.94 %)
- Score: `s = log10((1+v)/(1-v))`, v = TMVA EvaluateMVA, no clamping; cuts numu > 0.4, other > 0.2, ncpi0 > −0.05,
  nue > −1.0
- Decomposition: score convention only 831 (6.69 %); `kine_pio_flag` only 1,161 (9.34 %)
- BNB-CV selected non-signal: 635 (as run) → 282 (corrected)

**Layer B — same frozen selection, WCL1116 reconstruction (DIAGNOSTIC, not Round 2)**
- NC Δ efficiency: 833 / 12,427 = 6.70 % → 1,938 / 12,427 = 15.60 % (×2.33; 68 % 15.27–15.93 %)
- Truth 0p 6.36 → 18.27 %; 1p 7.49 → 14.29 %; ≥ 2p 4.37 → 7.25 %
- Median nearest reco → true vertex: 18.9 cm → 1.5 cm; within 5 cm 33 % → 65 %
- Generic BNB-CV selected non-signal: 282 → 685 (×2.43); 1γ0p 150 → 453, 1γ1p 93 → 178, ≥ 2p 39 → 54
- NC π⁰ 116 → 316; outside-TPC ν 62 → 196; CC π⁰ 60 → 94; νe CC 1 → 12
- Attribution: vertex + other reconstruction changes

**Layer C — SBND retraining (Aurora nested validation, DEVELOPMENT ONLY, split-move)**
- NC Δ signal efficiency: 27.1 ± 1.2 % (inherited) → 44.0 ± 1.3 % (SBND) [405 → 657 of 1,494 rows]
- BNB background acceptance: 0.75 ± 0.11 % → 0.78 ± 0.11 % [48 → 50 of 6,424 rows]
- ≈ 1.6× the NC Δ signal at essentially the same BNB background acceptance
- Topology: 0p 30.1 → 51.2 %; 1p 27.1 → 39.9 %; ≥ 2p 10.5 → 26.6 % [681 / 689 / 124 rows]
- Cascade (signal / BNB after each cut):
  - inherited: numu 85.8 / 25.4, other 56.9 / 9.3, ncpi0 33.3 / 1.7, nue 27.1 / 0.75 %;
  - SBND: 87.2 / 18.6, 62.5 / 2.7, 46.1 / 1.0, 44.0 / 0.78 %
- Snap: 26.4 → 41.2 % at 0.65 → 0.68 %

**Per-model ROC AUC (Aurora existing development holdout, split-move; DEVELOPMENT ONLY)**
- SP numu 0.958 → 0.976
- SP ncpi0 0.848 → 0.899
- SP other 0.840 → 0.915
- SP nue 0.918 → 0.959

**Development conclusions**
- SP nue: unweighted (AUC 0.9624 vs 0.9620 thesis 4:1 vs 0.9618 balanced)
- SP ncpi0: current sample adequate (pre-registered rule); νe CC-sample NC π⁰ not source-compatible; compatible route
  `outncpi0`
- SP numu: mild upstream dependence (−0.0015 to −0.003 AUC); needs the frozen upstream νμ
- SP other: full 0.916 / no cosmic 0.907 / no upstream 0.907 / no both 0.890; must be retrained in the effective-
  boundary domain
- Vertex mode: split-move development-preferred (44.0 vs 41.2 %); NOT frozen

**Mandatory labels:**
- "Aurora nested validation — DEVELOPMENT ONLY" (Layer C);
- "DIAGNOSTIC, not a Round-2 result" (Layer B);
- "HISTORICAL as-run" (9.28 %);
- "No threshold / model / vertex mode frozen; retrained models not yet evaluated on FermiGrid."
