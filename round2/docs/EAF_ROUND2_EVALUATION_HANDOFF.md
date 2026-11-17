# Round-2 single-photon evaluation on EAF / FermiGrid: instructions for the evaluating session

For: the Claude Code session on EAF that evaluates Haiwang's Round-2 official merged CAFs, run after Round-2 exists.
Written 2026-11-17 on Aurora. Nothing here has been run.

## 0. Rules

1. **Official samples are evaluation only.**
   - Nothing is trained, tuned or re-thresholded on them.
   - Operating thresholds come from the model handoff record (`NCPI0_OTHER_ROUND2_PRODUCTION_HANDOFF_REQUIREMENTS.md`).
     They were fixed on Aurora development samples.
2. **Same definitions in both rounds.** Round-1 (frozen baseline) and Round-2 are evaluated with the same code, the same
   definitions and the same event lists.
   - Copy every definition in §3 **from the Round-1 EAF record**, verbatim, before computing anything Round-2.
   - Where the Round-1 record lacks one, stop and ask; do not invent it.
3. **No final purity / S/B** until the common analysis volume and the cosmic-only (beam-off) normalization are resolved.
   Report counts, efficiencies, composition and rates relative to Round-1.
4. Every number comes from a script that was run; name the script beside it.

## 1. Inputs

| input | where it comes from | note |
|---|---|---|
| Round-1 merged CAFs | the frozen-baseline official production, as used by the Round-1 EAF study | unchanged |
| Round-2 merged CAFs | Haiwang's Round-2 regeneration of the **same** official samples | record toolkit commit, schema md5 and lists |
| model handoff record | `NCPI0_OTHER_ROUND2_PRODUCTION_HANDOFF_REQUIREMENTS.md`, filled | file names, sha256, feature lists, thresholds, deployment route |
| scorer | the toolkit-stored scores (route A) or the offline scorer of the handoff (route B) | in route B, score both rounds offline with the **same** scorer version |
| legacy single-photon XMLs | the inherited four `*_bdt_final.xml` (sha256 in `provenance/software_versions.yaml`) | the Round-1 control scores |

**Score convention.** Every single-photon score is `log10((1+v)/(1−v))`, with v = TMVA `EvaluateMVA`. The legacy cuts
(numu > 0.4, other > 0.2, ncpi0 > −0.05, nue > −1.0) are on that scale, and the νe cut is a real cut.
- If the Round-1 study scored in tanh space (`baseline_v0` scorer), re-score Round-1 with the corrected convention
  before comparing. Report both, so the change of convention is visible on its own. See
  `SP_BDT_DEPENDENCY_AND_TARGET_AUDIT.md` §5.
- Also replicate MicroBooNE's `kine_pio_flag = 0` for legacy scores, as the handoff specifies.

## 2. Samples

| sample | role | constraint |
|---|---|---|
| official Gen2 NC Δ-radiative MC (fg1 `prod-fermigrid/ncdr/mc-ncdr`, and the official SAM `EX_ncdeltarad` if part of Round-2) | signal efficiency | **not** the Aurora configL NC Δ training sample |
| fg1 BNB CV MC (500k) | background counts, rates, composition; natural-CV consistency | hold-out files flagged as in Round-1 |
| fg1 νe CC MC (100k) | diagnostics only | filtered sample: no physical exposure from its header |
| fg1 beam-off | cosmic-only control | **even-run evaluation half only**: Xuyang trained νe on the odd half. Normalization unresolved |
| open beam-on (Run 1 FixedDev; Run 3 unblinded) | data/MC shape checks only | subject to the normalization constraints; blinded data never |

## 3. Held constant between rounds (copy from the Round-1 record)

1. **Truth signal definition.** Single photon; NC Δ subtypes Δ⁰ / Δ⁺; proton topology 0p / 1p / ≥ 2p with the Round-1
   KE threshold.
2. **Analysis volume.** The approved or provisional convention, applied identically to truth and reco.
3. **Candidate policy.** Which candidate represents an event, and how multi-candidate events are treated.
4. **Truth matching.** The candidate ↔ neutrino rule; `T_match` level 2 if that is what Round-1 used.
5. **Background taxonomy and category order.**
6. **POT and rate conventions.** MC weight = POT_data / POT_MC. Beam-off = (1−f)·G_on/G_off, with f as in Round-1
   (MicroBooNE note: default 0.08 until measured).
7. **Binning, plotting and the event keys.** Key = `(sample, file_id, run, subrun, event)`; `(run, subrun, event)` alone
   is not unique in fg1 νe CC.

## 4. Required comparisons, Round-1 vs Round-2

- **Efficiency.** Overall NC Δ efficiency, split by truth 0p / 1p / ≥ 2p and by Δ⁰ / Δ⁺.
- **Differential efficiency.** Against photon energy, photon angle, true vertex x/y/z, photon conversion distance,
  neutrino energy and leading-proton KE.
- **Cutflows.** First-failure cutflow per event: the first cut it fails in each round, and the migration matrix between
  rounds.
- **Reconstruction.**
  - Photon reconstruction taxonomy: no candidate; shower not at the main vertex (`shw_sp_filled == 0`); shower
    under-reconstructed; and so on, as in Round-1.
  - Vertex behaviour: reco − true vertex distance, and the DL-vertex acceptance.
  - Proton-topology migration between reco and truth.
- **Backgrounds.** BNB CV background counts, rates and composition at each cut, plus natural-CV consistency. Beam-off
  counts in the even half, unnormalized until normalization is resolved.
- **Event-by-event.** Recovered (fail → pass) and lost (pass → fail) events, with run/subrun/event lists and their
  failure classes.
- **Scores.** Old vs new single-photon BDT scores per event, on the same events. Legacy XMLs on Round-2 inputs and new
  models on Round-2 inputs, so model and reconstruction changes can be separated.
- **Pathologies and new backgrounds.** Which known Round-1 pathologies are recovered, by category, and which new
  background categories or events are admitted.

## 5. Provenance to record

- Toolkit and larwirecell commits of both rounds.
- Model files and sha256 (legacy and Round-2).
- Scorer version, schema md5s, sample lists with sha256, hold-out handling, and every script path and commit.
