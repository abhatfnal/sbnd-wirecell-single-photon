# Reconstructed proton definition audit (provisional; NOT frozen)

> Section 5 (added) validates the rule against MC truth on BNB CV. **The baseline rule is unchanged; the 35 MeV threshold was not optimised.** No signal conclusion is drawn.

Goal: define reco **0p / 1p / ≥2p** per neutrino candidate from the production merged CAF, without tuning.
Planning threshold: proton kinetic energy **> 35 MeV** (to be confirmed against current SBND convention before freezing).

## 1. What the columns are (from the Wire-Cell source and from data)

Sources: `NeutrinoKinematics.cxx` and `NeutrinoTaggerInfo.h` in `/exp/sbnd/app/users/yuhw/wct-pr543/clus/` (same `fill_kine_tree` as production
`sbnd-wc-flatcaf`; the file was read only, the PR #543 build is not production), plus the smoke-test sample (1000 events × 4 samples).

| column (`wc.T_kine.`) | meaning | evidence |
|---|---|---|
| `kine_particle_type` | **PDG code**, unsigned in practice (`2212` proton, `13` μ, `211` π, `11` e/shower default, `0` unknown). Tracks: `seg->particle_info()->pdg()`; showers: `shower_kine_pdg`. | source lines ~237/297; observed values `{11, 13, 211, 2212, 0}` in 10 CV files, no negative codes |
| `kine_energy_particle` | **kinetic energy in MeV** (`NeutrinoTaggerInfo.h`: "kinetic energy [MeV]"; tracks use `particle_info()->kinetic_energy()`; showers use `get_kine_best()`) | source + header comment. **Not yet validated numerically against truth KE** (needs `T_match`/`T_truth_track`; listed in §4) |
| `kine_energy_info` | how the energy was priced: 0 = dQ/dx, 1 = range, 2 = charge | header |
| `kine_energy_included` | `1` = counted in the reco-Eν sum; other values flag rows not summed (observed `{1, 3}`) | header + source |
| `kine_particle_pool` | which collection step produced the row (observed `0, 1, 2, 3`; source also has 4 = guard-freed track, 5 = near cross-cluster track; 3 = orphan track) | source |
| `kine_particle_is_shower`, `kine_particle_id`, `kine_particle_cluster_id`, `kine_particle_nseg` | per-row particle bookkeeping | source |
| units | energies MeV; vertex `kine_nu_*_corr` cm (raw vertex if no geometry helper; SCE-corrected otherwise) | source |

**Layout:** all per-particle columns are flat per event with `..length` / `..idx` per candidate. Candidate `i` of an event owns the rows
`[idx_i, idx_i + length_i)`. Therefore the particles of a candidate are exactly the rows in its slice; there is no cross-candidate mixing as long as
`MergedCaf.read_nested` is used (it errors if `sum(length) != len(flat)`). `T_tagger.ssm_kine_*` is a separate (SSM) copy and is not used.

## 2. Provisional rule (implemented in `proton.py`)

```
n_p(candidate) = #{ rows : kine_particle_type == 2212  AND  kine_energy_particle > threshold_mev }      # strict >
code = 0 (0p) if n_p == 0 ; 1 (1p) if n_p == 1 ; 2 (>=2p) otherwise
classify_reco_protons(pdg, ke_mev, threshold_mev=35.0, *, included=None, require_included=False)
```

- Identical to the rule of the earlier 59-event study (`type == 2212 and KE > 35 MeV`), so results stay comparable; **ignores `kine_energy_included` and pool** by default.
- Returns integer codes (`proton.LABELS = ("0p", "1p", "ge2p")`) because awkward cannot broadcast strings.
- `threshold_mev` is a parameter. It must not be scanned/tuned in the baseline.
- Variant `require_included=True` (row must have `kine_energy_included == 1`) exists only as a sensitivity.

## 3. Smoke-test observation (software validation only, raw candidate counts; not physics)

Candidates of `wc.valid == 1` events, first 1000 events per sample, all candidates, **no selection applied**:

| sample | rule | 0p | 1p | ≥2p |
|---|---|---|---|---|
| bnb_cv | KE>35 | 213 | 215 | 69 |
| bnb_cv | KE>35 & included==1 | 222 | 216 | 59 |
| nuecc | KE>35 | 378 | 396 | 209 |
| nuecc | KE>35 & included==1 | 418 | 383 | 182 |
| beam_off | KE>35 | 94 | 7 | 0 |
| beam_on_open | KE>35 | 215 | 215 | 59 |
| beam_on_open | KE>35 & included==1 | 232 | 208 | 49 |

The `included` requirement moves ~4 % of candidates between categories. This is a systematic of the *definition*, to be decided, not a tuning knob.

## 4. Unresolved questions (before freezing)

1. **Threshold:** is 35 MeV the current SBND convention? (planning value only.)
2. **Is `kine_energy_particle` really KE for protons?** Source says yes; confirm numerically against truth KE of the matched true proton (`wc.T_match` / `T_truth_track`, MC only) on a small sample. Not done in this stage.
3. **Which rows belong to the neutrino:** the inherited rule counts every proton row of the candidate, including rows from late pools (orphan / guard-freed / cross-cluster) and rows with `included != 1`. Should those count?
4. **PID quality:** `kine_particle_type` is an algorithmic PID guess; a mis-ID μ/π as p (or the reverse) feeds directly into migration. Quantify with truth once the official Gen2 NC-Delta sample is available.
5. **Candidate choice:** when an event has >1 candidate, which candidate's protons define the event category (see design note §5).
6. **Shower-PDG caching:** the source logs cached-vs-live shower PDG mismatches (`kine_shower_pdg_live`); whether this affects proton rows is not examined.
7. **Reco vs truth proton definition:** the truth proton KE definition (threshold, FSI-level, containment) must be matched to the reco one for the migration matrix; to be specified with the official Gen2 NC-Delta sample.

## 5. Validation against MC truth (BNB CV; evaluation only)

Method: `scripts/truth_match_scan.py` (11,999 of the first 12,000 listed CV files; file 8398 cannot be read by this script) + `scripts/truth_audit_report.py`. All rows are `wc.valid == 1` events, every candidate (cosmic-dominated ones included), no selection applied: 541k T_kine rows, 96,518 of them with `kine_particle_type == 2212`.
Matching: each T_kine row is linked through `T_overlap` (`particle_id == kine_particle_id`, same `nu_index`, `in_enu == 1`) to the truth track with the most shared charge `q` (`T_truth_track`: pdg, `start_E`, neutrino index). Truth KE = `start_E`·1000 − mass. Outputs: `tables/proton_audit/`, `plots/proton_audit/bnb_cv_proton_ke_response.png`.
Caveats: "matched" means dominant-charge truth track, not exclusive ownership; true KE is the initial KE and does not account for exits or secondary interactions; the sample includes cosmic-dominated candidates.

**Q1. Does `kine_energy_particle` behave like proton KE?** Yes. For rows of type 2212 matched to a true proton (n = 62,469), median reco/true KE = **0.99**; against true total energy (KE + 938 MeV) the median would be 0.11, which is not what the data show. Response by true KE (median reco/true; fraction within ±20 %):

| true KE (MeV) | n | median | within ±20 % |
|---|---|---|---|
| 35–60 | 5,904 | 1.15 | 23 % |
| 60–100 | 14,605 | 0.99 | 73 % |
| 100–150 | 13,100 | 0.99 | 85 % |
| 150–250 | 14,329 | 1.00 | 81 % |
| 250–400 | 7,646 | 0.99 | 71 % |
| 400–700 | 2,534 | 0.86 | 54 % |
| >700 | 99 | 0.73 | 47 % |

Near threshold the reco KE is poor (broad, biased high) and above ~400 MeV it falls low (containment/range). Below 35 MeV true KE the reco is a factor ~4 low (median 0.23).

**Q2. How reliable is `kine_particle_type == 2212`?** Purity = fraction of rows whose dominant truth track is a proton:

| rows | n | true proton | true photon | true μ/π | unmatched | from a neutrino (not cosmic) |
|---|---|---|---|---|---|---|
| all type 2212 | 96,518 | 64.7 % | 26.7 % | 3.5 % | 1.4 % | 94.0 % |
| **KE > 35 MeV** | 58,222 | **95.7 %** | 1.1 % | 2.0 % | 0.4 % | 98.6 % |
| KE ≤ 35 MeV | 38,296 | 17.7 % | 65.7 % | 5.9 % | 2.9 % | 87.0 % |

So the type-2212 rows below 35 MeV are mostly photon-origin; the inherited 35 MeV cut removes them without being tuned here (a descriptive observation, not an optimisation). Conversely, of all reco rows with a true-proton match, many carry another type (shower 12,747, π 8,172, μ 4,747 vs 62,469 as 2212): proton finding through the PID label is incomplete (see Q5).

**Q3. What are the rows with `kine_energy_included != 1`?** Source (`NeutrinoTaggerInfo.h`, `NeutrinoKinematics.cxx`): the flag is a misnomer. The header states that rows flagged ≠ 1 **are** inside `kine_reco_Enu` (the energy sum is unconditional). Data: `included` takes only the values 1 and 3; all 321,478 rows with value 3 are **pool 2 (leftover showers)** (value 3 = `vtx_type == 3`), and no track row has it. Of proton-typed rows with KE > 35 MeV, 5,141 have `included != 1` (8.8 %): 88.9 % of them are true protons (vs 96.3 % for `included == 1`), median reco/true KE 0.82 (0.99 for `included == 1`), and 3.6 % are unmatched. The median hides a **bimodal** response (`plots/proton_audit/bnb_cv_proton_ke_response.png`, right): one peak at reco/true ≈ 1 and a second, comparable one at ≈ 0.25, i.e. protons reconstructed as leftover showers often carry a much too small energy; `included == 1` rows are a single peak at 1 with a tail.

**Q4. Count them or not?** The evidence favours the current rule (count them): the rows are overwhelmingly real protons, and the reconstruction itself sums them into reco E_ν. Excluding them would move 4,208 of 75,149 candidates (5.6 %; candidate-level, no selection) into lower categories: 1p→0p 2,607, ≥2p→1p 1,487, ≥2p→0p 114. Their energy is much less accurate in about half of the cases (the ≈0.25 population). This is an evidence summary, **not a decision**: the definition stays "count all rows". Pool dependence: pool 0 (main-vertex edge) 96.8 % proton, pool 1 (BFS) 93.8 %, pool 2 (leftover shower) 87.0 %, pool 3 95.6 %; pools 4/5 have 25/10 rows (not interpretable).

**Q5. Finding fraction (not an efficiency).** Of beam-neutrino true protons with KE > 35 MeV (128,018), **41.8 %** are the dominant match of some reco proton row with reco KE > 35 MeV (43.4 % as any proton-typed row); restricting to a candidate dominated by that same neutrino gives 48.5 % (n = 109,883). By true KE: 16 % (35–60), 52 % (60–100), 65 % (100–150), 69 % (150–250), 65 % (250–400), 47 % (400–700), 6 % (>700 MeV). This denominator includes protons that exit, rescatter, or sit in events with no candidate for their neutrino, so it is a descriptive finding fraction, **not** a proton reconstruction efficiency and it must not be quoted as one. A meaningful efficiency needs the official signal sample and a signal-level truth definition.

**Consequence for categories.** Of 31,209 reco-1p candidates, 1,444 (4.6 %) contain no proton-typed row (KE>35) that is a true neutrino proton; of 11,659 reco-≥2p candidates, 1,012 (8.7 %) have fewer than two such rows. The reco 0p/1p/≥2p split therefore carries a PID-contamination systematic that needs the truth↔reco migration matrix of the signal sample. Not quantified further here.

Still open: threshold convention (35 MeV), candidate choice, shower-PDG caching (§4 items 1, 5, 6), and the truth proton definition for the signal migration matrix (§4 item 7).
